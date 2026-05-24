from enum import Enum

from auth.dependencies import get_current_user
from fastapi import Depends, HTTPException


class UserRole(str, Enum):
    ADMIN = "admin"
    PROCUREMENT_OFFICER = "procurement_officer"
    VIEWER = "viewer"


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role", UserRole.VIEWER)
    if role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_procurement_officer(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role", UserRole.VIEWER)
    if role not in (UserRole.ADMIN, UserRole.PROCUREMENT_OFFICER):
        raise HTTPException(status_code=403, detail="Procurement officer access required")
    return current_user


async def require_viewer(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user
