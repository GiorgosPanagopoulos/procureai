from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: Literal["viewer"] = "viewer"


class UserRead(BaseModel):
    id: str = Field(alias="_id")
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    role: str = "viewer"
    created_at: datetime

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
