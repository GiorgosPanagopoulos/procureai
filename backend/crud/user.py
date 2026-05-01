from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth.security import get_password_hash, verify_password
from schemas.user import UserCreate


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[dict]:
    return await db.users.find_one({"email": email})


async def create_user(db: AsyncIOMotorDatabase, user_in: UserCreate) -> Optional[dict]:
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        return None
    user_doc = {
        "_id": str(ObjectId()),
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)
    return user_doc


async def authenticate_user(db: AsyncIOMotorDatabase, email: str, password: str) -> Optional[dict]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


async def update_user(db: AsyncIOMotorDatabase, email: str, update_data: dict) -> Optional[dict]:
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    if not update_data:
        return await get_user_by_email(db, email)
    await db.users.update_one({"email": email}, {"$set": update_data})
    return await get_user_by_email(db, email)
