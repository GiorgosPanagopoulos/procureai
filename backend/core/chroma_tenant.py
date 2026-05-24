from contextvars import ContextVar
from typing import Optional

from chromadb.types import Where

_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)


def get_user_filter(user_id: str) -> Where:
    return {"user_id": user_id}  # type: ignore[return-value]


def build_metadata(user_id: str, source: str, **kwargs) -> dict:
    return {"user_id": user_id, "source": source, **kwargs}


def get_active_user_id() -> Optional[str]:
    return _current_user_id.get()
