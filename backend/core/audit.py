from datetime import datetime
from typing import List, Optional

import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger()


class AuditEntry(BaseModel):
    user_id: str
    user_role: str
    action: str  # "chat", "doc_qa", "upload", "delete_document"
    query: Optional[str] = None
    response_summary: Optional[str] = None  # first 500 chars of AI response
    sources_used: List[str] = []
    endpoint: str  # "/chat", "/doc_qa", etc.
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


async def log_audit(db, entry: AuditEntry) -> None:
    """Insert an audit entry; swallows all errors so it never crashes the caller."""
    try:
        await db.audit_logs.insert_one(entry.model_dump())
    except Exception as exc:
        log.error("audit_log_failed", error=str(exc), action=entry.action, user_id=entry.user_id)


async def get_audit_logs(
    db,
    user_id: Optional[str],
    action: Optional[str],
    skip: int,
    limit: int,
) -> List[dict]:
    query: dict = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action
    cursor = db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)
