from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str = ""


class UserRead(BaseModel):
    id: str = Field(alias="_id")
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
