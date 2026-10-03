from contextvars import ContextVar
from typing import Any, Optional

_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)

# Owner of the bundled PDFs (backend/data/pdfs), readable by every user.
SYSTEM_USER_ID = "system"


def get_search_filter(user_id: str) -> Any:
    """$vectorSearch pre-filter: the user's own chunks plus the shared system documents."""
    return {"user_id": {"$in": [user_id, SYSTEM_USER_ID]}}


def build_metadata(user_id: str, source: str, **kwargs) -> dict:
    return {"user_id": user_id, "source": source, **kwargs}


def get_active_user_id() -> Optional[str]:
    return _current_user_id.get()
