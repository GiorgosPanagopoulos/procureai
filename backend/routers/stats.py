from typing import Optional

from core.rbac import require_viewer
from db import db
from fastapi import APIRouter, Depends, Request
from middleware.rate_limit import limiter
from pydantic import BaseModel

router = APIRouter()


class StatsRead(BaseModel):
    suppliers: int
    bids: int
    total_value_eur: float
    avg_delivery_days: Optional[float]


_BIDS_PIPELINE = [
    {
        "$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total_value": {"$sum": "$total_price"},
            "avg_delivery": {"$avg": "$delivery_days"},
        }
    }
]


@router.get("/stats", response_model=StatsRead)
@limiter.limit("30/minute")
async def get_stats(request: Request, current_user: dict = Depends(require_viewer)) -> StatsRead:
    suppliers = await db.suppliers.count_documents({})
    rows = await db.bids.aggregate(_BIDS_PIPELINE).to_list(length=1)
    agg = rows[0] if rows else {}
    avg_delivery = agg.get("avg_delivery")
    return StatsRead(
        suppliers=suppliers,
        bids=agg.get("count", 0),
        total_value_eur=round(float(agg.get("total_value", 0) or 0), 2),
        avg_delivery_days=round(float(avg_delivery), 1) if avg_delivery is not None else None,
    )
