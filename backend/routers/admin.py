from typing import Optional

import structlog
from core.audit import AuditEntry, get_audit_logs
from core.prompt_loader import LoadedPrompt, prompt_loader
from core.rbac import require_admin
from db import db
from exceptions import NotFoundError
from fastapi import APIRouter, Depends, Query, Request
from middleware.audit_middleware import audit_interaction

log = structlog.get_logger()

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


@router.get("/prompts")
async def list_prompts(
    request: Request,
    current_user: dict = Depends(require_admin),
):
    use_cases = prompt_loader.list_use_cases()
    result = []
    for uc in use_cases:
        versions = prompt_loader.list_versions(uc)
        entry: dict = {"use_case": uc, "versions": versions, "metadata": {}}
        for v in versions:
            loaded = prompt_loader.get_with_metadata(uc, v)
            entry["metadata"][v] = loaded.metadata.model_dump()
        result.append(entry)

    audit_interaction(
        db,
        AuditEntry(
            user_id=str(current_user["_id"]),
            user_role=str(current_user.get("role", "admin")),
            action="view_prompt",
            query="list_all",
            endpoint="/admin/prompts",
            ip_address=request.client.host if request.client else None,
        ),
    )
    return {"prompts": result}


@router.get("/prompts/{use_case}/{version}", response_model=LoadedPrompt)
async def get_prompt(
    use_case: str,
    version: str,
    request: Request,
    current_user: dict = Depends(require_admin),
):
    try:
        loaded = prompt_loader.get_with_metadata(use_case, version)
    except ValueError as exc:
        raise NotFoundError(str(exc))

    audit_interaction(
        db,
        AuditEntry(
            user_id=str(current_user["_id"]),
            user_role=str(current_user.get("role", "admin")),
            action="view_prompt",
            query=f"{use_case}/{version}",
            endpoint=f"/admin/prompts/{use_case}/{version}",
            ip_address=request.client.host if request.client else None,
        ),
    )
    return loaded
