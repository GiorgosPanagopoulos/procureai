from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from crud.user import create_user, authenticate_user, get_user_by_email
from auth.security import create_access_token, set_auth_cookie, clear_auth_cookie, decode_access_token
from schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_db():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client.procureai


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(body: LoginRequest) -> JSONResponse:
    db = _get_db()
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Inactive account")
    token = create_access_token(subject=user["email"])
    response = JSONResponse(content={
        "message": "Login successful",
        "user": UserRead(**user).model_dump(by_alias=True),
    })
    set_auth_cookie(response, token)
    return response


@router.post("/register")
async def register(user_in: UserCreate) -> JSONResponse:
    db = _get_db()
    user = await create_user(db, user_in)
    if user is None:
        raise HTTPException(status_code=400, detail="Email already registered")
    token = create_access_token(subject=user["email"])
    response = JSONResponse(content=UserRead(**user).model_dump(by_alias=True))
    set_auth_cookie(response, token)
    return response


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"message": "Logged out"})
    clear_auth_cookie(response)
    return response


@router.get("/me")
async def me(request: Request) -> JSONResponse:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    db = _get_db()
    user = await get_user_by_email(db, payload.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return JSONResponse(content=UserRead(**user).model_dump(by_alias=True))
