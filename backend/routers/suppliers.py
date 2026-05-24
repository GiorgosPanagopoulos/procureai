from typing import List

from core.rbac import require_viewer
from db import db
from fastapi import APIRouter, Depends, Request
from middleware.rate_limit import limiter
from models import Bid, Supplier

router = APIRouter()


@router.get("/suppliers", response_model=List[Supplier])
@limiter.limit("30/minute")
async def get_suppliers(request: Request, current_user: dict = Depends(require_viewer)):
    suppliers = []
    async for supplier in db.suppliers.find():
        suppliers.append(Supplier(**supplier))
    return suppliers


@router.get("/bids", response_model=List[Bid])
@limiter.limit("30/minute")
async def get_bids(request: Request, current_user: dict = Depends(require_viewer)):
    bids = []
    async for bid in db.bids.find():
        bids.append(Bid(**bid))
    return bids
