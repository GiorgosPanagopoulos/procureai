from datetime import datetime
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class User(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: str
    hashed_password: str
    full_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    role: Literal["admin", "procurement_officer", "viewer"] = "viewer"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
