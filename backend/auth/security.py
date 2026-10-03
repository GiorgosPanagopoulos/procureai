from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from config import settings
from fastapi import Response
from jose import JWTError, jwt
from passlib.context import CryptContext
from schemas.auth import TokenPayload

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, role: str = "viewer") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "role": role}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenPayload]:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(sub=data["sub"], exp=data.get("exp"), role=data.get("role", "viewer"))
    except (JWTError, KeyError):
        return None


def _cookie_policy() -> tuple[bool, Literal["lax", "none"]]:
    # Frontend and backend are on different sites outside local dev.
    if settings.is_local:
        return False, "lax"
    return True, "none"


def set_auth_cookie(response: Response, token: str) -> None:
    secure, samesite = _cookie_policy()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    secure, samesite = _cookie_policy()
    response.delete_cookie(
        key="access_token", path="/", httponly=True, secure=secure, samesite=samesite
    )
