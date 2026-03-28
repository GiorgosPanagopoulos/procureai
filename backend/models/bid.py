from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from bson import ObjectId
from enum import Enum

class BidStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class BidItem(BaseModel):
    name: str
    quantity: int
    unit_price: float

class Bid(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    supplier_id: str
    items: List[BidItem]
    total_price: float
    delivery_days: int
    terms: str
    status: BidStatus = BidStatus.PENDING

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}