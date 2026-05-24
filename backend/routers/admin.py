from typing import Optional

from core.audit import get_audit_logs
from core.rbac import require_admin
from db import db
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs")
async def audit_logs(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _current_user: dict = Depends(require_admin),
):
    logs = await get_audit_logs(db, user_id=user_id, action=action, skip=skip, limit=limit)
    return {"logs": logs, "count": len(logs)}
