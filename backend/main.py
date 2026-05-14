import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import sentry_sdk
import structlog
from agent.executor import run_agent
from agent.tools import document_qa
from api.routes.auth import router as auth_router
from auth.dependencies import get_current_user
from config import settings
from core.sentry import init_sentry
from db import db
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from middleware.correlation import CorrelationIDMiddleware
from middleware.cors import setup_cors
from middleware.rate_limit import limiter, setup_rate_limit
from models import Bid, Supplier
from pydantic import BaseModel
from rag.ingest import ingest_pdf, ingest_pdf_file, is_vectorstore_empty

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
                {"$set": {"is_superuser": True}},
            )
            log.info("superuser_created", email=settings.FIRST_SUPERUSER_EMAIL)
    else:
        log.info("superuser_exists", email=settings.FIRST_SUPERUSER_EMAIL)
    yield


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="ProcureAI API", version="4.0.0", lifespan=lifespan)
setup_rate_limit(app)
app.add_middleware(CorrelationIDMiddleware)
setup_cors(app)

app.include_router(auth_router)

# ── Request / response models ─────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# ── FastAPI endpoints ─────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {"message": "ProcureAI API ready", "version": "4.0.0"}


@app.get("/suppliers", response_model=List[Supplier])
@limiter.limit("30/minute")
async def get_suppliers(request: Request, current_user: dict = Depends(get_current_user)):
    suppliers = []
    async for supplier in db.suppliers.find():
        suppliers.append(Supplier(**supplier))
    return suppliers


@app.get("/bids", response_model=List[Bid])
@limiter.limit("30/minute")
async def get_bids(request: Request, current_user: dict = Depends(get_current_user)):
    bids = []
    async for bid in db.bids.find():
        bids.append(Bid(**bid))
    return bids


@app.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    cid = payload.conversation_id or str(uuid.uuid4())
    result = await run_agent(payload.message, cid)
    if not result.get("response"):
        raise HTTPException(status_code=500, detail="Agent returned empty response")
    return {
        "response": result["response"],
        "tool_used": result.get("tool_used"),
        "conversation_id": cid,
        "usage": result.get("usage"),
        "trace": result.get("trace"),
    }


@app.post("/upload")
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
    content = await file.read()
    try:
        chunks = ingest_pdf(file.filename or "uploaded.pdf", content)
    except Exception as e:
        sentry_sdk.set_context(
            "document",
            {
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(content),
            },
        )
        sentry_sdk.capture_exception(e)
        raise
    if chunks == 0:
        raise HTTPException(status_code=400, detail="PDF had no extractable text")
    log.info("pdf_uploaded", file=file.filename, chunks=chunks)
    return {
        "message": "PDF ingested successfully",
        "chunks": chunks,
        "file": file.filename,
    }


@app.post("/doc_qa")
@limiter.limit("30/minute")
async def qna(request: Request, question: str, current_user: dict = Depends(get_current_user)):
    return {"answer": document_qa.invoke(question), "question": question}


@app.get("/conversations/{conversation_id}/trace")
async def get_trace(conversation_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.conversations.find_one({"conversation_id": conversation_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "trace": doc.get("trace", [])}


@app.get("/reports")
@limiter.limit("30/minute")
async def get_reports(request: Request, current_user: dict = Depends(get_current_user)):
    return {"reports": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
