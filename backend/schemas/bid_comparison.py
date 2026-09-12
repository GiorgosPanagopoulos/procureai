from typing import List

from pydantic import BaseModel, Field


class RankedBid(BaseModel):
    """One bid as ranked by the model, cheapest and fastest first."""

    supplier_id: str = Field(description="MongoDB id of the supplier that submitted the bid")
    total_price_usd: float = Field(description="Bid total converted to US dollars")
    total_price_eur: float = Field(description="Bid total in euros, as stored")
    delivery_days: int = Field(description="Promised delivery time in days")
    status: str = Field(description="Bid status: pending, accepted or rejected")


class BidComparisonResult(BaseModel):
    """Structured observation returned by the bid_comparison tool."""

    bids: List[RankedBid] = Field(description="Bids ordered best-value first")
    recommendation: str = Field(description="Which bid to award and why, in two or three sentences")
