from contextvars import ContextVar
from typing import Any, Optional

_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)


def get_user_filter(user_id: str) -> Any:
    return {"user_id": user_id}


def build_metadata(user_id: str, source: str, **kwargs) -> dict:
    return {"user_id": user_id, "source": source, **kwargs}


def get_active_user_id() -> Optional[str]:
    return _current_user_id.get()
