from auth.dependencies import get_current_user
from fastapi import APIRouter, Depends, Request
from middleware.rate_limit import limiter

router = APIRouter()


@router.get("/reports")
@limiter.limit("30/minute")
async def get_reports(request: Request, current_user: dict = Depends(get_current_user)):
    return {"reports": []}
