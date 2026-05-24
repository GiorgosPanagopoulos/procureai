from core.rbac import require_viewer
from fastapi import APIRouter, Depends, Request
from middleware.rate_limit import limiter

router = APIRouter()


@router.get("/reports")
@limiter.limit("30/minute")
async def get_reports(request: Request, current_user: dict = Depends(require_viewer)):
    return {"reports": []}
