"""Guards for public demo accounts (users with is_demo=True).

Demo users get a small daily budget of LLM-backed requests and are blocked
from anything that writes data, whatever their role.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from auth.dependencies import get_current_user
from config import settings
from db import db
from exceptions import DemoQuotaExceededError
from fastapi import Depends, HTTPException
from pymongo import ReturnDocument

from core.rbac import UserRole

log = structlog.get_logger()

# Counters only matter for the current UTC day; keep a day of slack before Mongo reaps them.
DEMO_USAGE_TTL_SECONDS = 48 * 60 * 60
# Visitors share the demo login, so their conversations shouldn't outlive the visit.
DEMO_CONVERSATION_TTL = timedelta(hours=24)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_demo_user(user: dict) -> bool:
    return bool(user.get("is_demo", False))


async def ensure_demo_indexes() -> None:
    # create_index is a no-op when an identical index already exists.
    await db.demo_usage.create_index("created_at", expireAfterSeconds=DEMO_USAGE_TTL_SECONDS)
    # Expires each document at its own expires_at; only demo conversations set it.
    await db.conversations.create_index("expires_at", expireAfterSeconds=0)


def conversation_expiry(user: dict) -> Optional[datetime]:
    """When a conversation written by this user should be deleted, or None to keep it."""
    return _utc_now() + DEMO_CONVERSATION_TTL if is_demo_user(user) else None


async def enforce_demo_quota(current_user: dict = Depends(get_current_user)) -> None:
    if not is_demo_user(current_user):
        return
    now = _utc_now()
    user_id = str(current_user["_id"])
    day = now.strftime("%Y-%m-%d")
    # Upsert on _id is atomic: concurrent first-of-day requests can't create two counters.
    doc = await db.demo_usage.find_one_and_update(
        {"_id": f"{user_id}:{day}"},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"user_id": user_id, "day": day, "created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if doc["count"] > settings.DEMO_DAILY_LIMIT:
        log.info("demo_quota_exceeded", user_id=user_id, day=day, count=doc["count"])
        raise DemoQuotaExceededError()


async def forbid_demo(current_user: dict = Depends(get_current_user)) -> dict:
    if is_demo_user(current_user):
        raise HTTPException(status_code=403, detail="Not available on the demo account")
    return current_user


async def require_chat_access(current_user: dict = Depends(get_current_user)) -> dict:
    """Procurement officers and admins, plus demo accounts (which are viewers)."""
    role = current_user.get("role", UserRole.VIEWER)
    if role in (UserRole.ADMIN, UserRole.PROCUREMENT_OFFICER) or is_demo_user(current_user):
        return current_user
    raise HTTPException(status_code=403, detail="Procurement officer access required")
