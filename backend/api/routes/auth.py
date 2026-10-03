from auth.dependencies import get_current_user
from auth.security import (
    clear_auth_cookie,
    create_access_token,
    set_auth_cookie,
)
from core.rbac import require_admin
from crud.user import authenticate_user, create_user
from db import db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(body: LoginRequest) -> JSONResponse:
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Inactive account")
    token = create_access_token(subject=user["email"], role=user.get("role", "viewer"))
    response = JSONResponse(
        content={
            "message": "Login successful",
            "user": UserRead(**user).model_dump(mode="json", by_alias=True),
            "access_token": token,
            "token_type": "bearer",
        }
    )
    set_auth_cookie(response, token)
    return response


@router.post("/register", status_code=201)
async def register(user_in: UserCreate, _admin: dict = Depends(require_admin)) -> JSONResponse:
    user = await create_user(db, user_in)
    if user is None:
        raise HTTPException(status_code=400, detail="Email already registered")
    # No auth cookie here: the caller is the admin, not the new user.
    return JSONResponse(
        status_code=201, content=UserRead(**user).model_dump(mode="json", by_alias=True)
    )


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"message": "Logged out"})
    clear_auth_cookie(response)
    return response


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> JSONResponse:
    return JSONResponse(content=UserRead(**user).model_dump(mode="json", by_alias=True))
