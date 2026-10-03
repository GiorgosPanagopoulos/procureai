from db import db
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "ProcureAI API ready", "version": "4.0.0"}


@router.get("/health")
async def health():
    # Liveness: no I/O, must stay fast on cold start.
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    checks: dict[str, str] = {}
    try:
        await db.command("ping")
        checks["mongo"] = "ok"
    except Exception as exc:
        checks["mongo"] = f"error: {type(exc).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )
