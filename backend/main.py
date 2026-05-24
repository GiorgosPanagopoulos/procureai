import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from api.routes.auth import router as auth_router
from config import settings
from core.sentry import init_sentry
from db import db
from exceptions import ProcureAIException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from middleware.correlation import CorrelationIDMiddleware
from middleware.cors import setup_cors
from middleware.rate_limit import setup_rate_limit
from rag.ingest import ingest_pdf_file, is_vectorstore_empty
from routers.admin import router as admin_router
from routers.chat import router as chat_router
from routers.health import router as health_router
from routers.reports import router as reports_router
from routers.suppliers import router as suppliers_router

init_sentry(settings.SENTRY_DSN, settings.SENTRY_ENVIRONMENT, settings.APP_VERSION)

# ── Logging ──────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()

# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        log.info("langsmith_enabled", project=settings.LANGCHAIN_PROJECT)
    else:
        log.info("langsmith_disabled")

    # Audit log indexes: compound (user_id, timestamp) for fast user queries.
    # TTL index (90-day expiry) can be enabled by uncommenting the second line:
    await db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
    # await db.audit_logs.create_index("timestamp", expireAfterSeconds=90*24*60*60)

    if is_vectorstore_empty():
        pdf_dir = Path(settings.CHROMA_PATH).parent / "data" / "pdfs"
        if pdf_dir.exists():
            for pdf_path in pdf_dir.glob("*.pdf"):
                try:
                    result = ingest_pdf_file(pdf_path)
                    log.info("pdf_ingested", file=result["file"], chunks=result["chunks"])
                except Exception as exc:
                    log.error("pdf_ingest_failed", file=pdf_path.name, error=str(exc))
    # --- Superuser seed ---
    from crud.user import create_user, get_user_by_email
    from schemas.user import UserCreate

    existing = await get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
    if not existing:
        superuser_in = UserCreate(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            full_name="Admin",
        )
        user_doc = await create_user(db, superuser_in)
        if user_doc:
            await db.users.update_one(
                {"email": settings.FIRST_SUPERUSER_EMAIL},
                {"$set": {"is_superuser": True, "role": "admin"}},
            )
            log.info("superuser_created", email=settings.FIRST_SUPERUSER_EMAIL)
    else:
        log.info("superuser_exists", email=settings.FIRST_SUPERUSER_EMAIL)
    yield


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="ProcureAI API", version="4.0.0", lifespan=lifespan)


@app.exception_handler(ProcureAIException)
async def procureai_exception_handler(request: Request, exc: ProcureAIException) -> JSONResponse:
    structlog.get_logger().warning(
        "handled_error",
        status=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": type(exc).__name__},
    )


setup_rate_limit(app)
app.add_middleware(CorrelationIDMiddleware)
setup_cors(app)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(suppliers_router)
app.include_router(reports_router)
app.include_router(admin_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
