import asyncio
from typing import Set

import structlog
from core.audit import AuditEntry, log_audit

log = structlog.get_logger()

# Strong references to in-flight audit tasks so the event loop's weak
# references don't allow GC before completion.
_background_tasks: Set[asyncio.Task] = set()


def audit_interaction(db, entry: AuditEntry) -> None:
    """Schedule audit logging as a fire-and-forget background task.

    Holds a strong reference until the task completes. log_audit swallows all
    DB errors internally, so this call never raises.
    """
    try:
        task = asyncio.create_task(log_audit(db, entry))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        # No running event loop (e.g. synchronous test contexts) — skip silently.
        log.warning("audit_no_event_loop", action=entry.action, user_id=entry.user_id)
