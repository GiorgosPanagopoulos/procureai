from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

class Supplier(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    category: str
    contact: str  # email or phone
    rating: float = Field(ge=0.0, le=5.0)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}