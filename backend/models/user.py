from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime


class User(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: str
    hashed_password: str
    full_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
