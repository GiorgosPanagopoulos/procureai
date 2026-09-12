from typing import List

from pydantic import BaseModel, Field


class RankedBid(BaseModel):
    """One bid as ranked by the model, cheapest and fastest first."""

    supplier_id: str = Field(description="MongoDB id of the supplier that submitted the bid")
    total_price_eur: float = Field(description="Bid total in euros, as stored")
    delivery_days: int = Field(description="Promised delivery time in days")
    status: str = Field(description="Bid status: pending, accepted or rejected")


class BidComparisonResult(BaseModel):
    """Structured observation returned by the bid_comparison tool."""

    bids: List[RankedBid] = Field(description="Bids ordered best-value first")
    recommendation: str = Field(description="Which bid to award and why, in two or three sentences")
    total_matched: int = Field(
        description="Number of bids in the database that matched the filter, "
        "which can exceed the number of bids listed"
    )
    truncated: bool = Field(
        description="True when fewer bids are listed than matched, i.e. the ranking "
        "covers a sample and the answer must say so (e.g. 'showing 10 of 16 matching bids')"
    )
