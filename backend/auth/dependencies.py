import sentry_sdk
from crud.user import get_user_by_email
from fastapi import HTTPException, Request

from auth.security import decode_access_token


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        sentry_sdk.set_user(None)
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if payload is None:
        sentry_sdk.set_user(None)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    from config import settings
    from motor.motor_asyncio import AsyncIOMotorClient

    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client.procureai
    user = await get_user_by_email(db, payload.sub)
    if user is None:
        sentry_sdk.set_user(None)
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Inactive account")
    sentry_sdk.set_user({"id": str(user.get("_id", ""))})
    return user
