from fastapi import HTTPException, Request

from auth.security import decode_access_token
from crud.user import get_user_by_email


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    from motor.motor_asyncio import AsyncIOMotorClient
    from config import settings
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client.procureai
    user = await get_user_by_email(db, payload.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Inactive account")
    return user
