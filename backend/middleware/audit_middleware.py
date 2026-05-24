import asyncio

import structlog
from core.audit import AuditEntry, log_audit

log = structlog.get_logger()


def audit_interaction(db, entry: AuditEntry) -> None:
    """Schedule audit logging as a fire-and-forget background task.

    Uses asyncio.create_task so the main response is never blocked.
    log_audit internally swallows all DB errors, so this call never raises.
    """
    try:
        asyncio.create_task(log_audit(db, entry))
    except RuntimeError:
        # No running event loop (e.g. synchronous test contexts) — skip silently.
        log.warning("audit_no_event_loop", action=entry.action, user_id=entry.user_id)
