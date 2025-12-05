"""Dutch auction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.marketplace import BuyNowRequest, DutchAuctionState
from app.services.marketplace.dutch_engine import (
    execute_atomic_purchase,
    get_live_price,
)

router = APIRouter(prefix="/dutch", tags=["dutch-auctions"])


@router.get("/{listing_id}/price", response_model=DutchAuctionState)
async def get_price(listing_id: str) -> DutchAuctionState:
    try:
        price = await get_live_price(listing_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing_not_found")
    return DutchAuctionState(
        listing_id=listing_id,
        current_price=price,
        next_drop_at=None,
        is_active=True,
    )


@router.post("/{listing_id}/buy", response_model=DutchAuctionState)
async def buy_now(listing_id: str, payload: BuyNowRequest) -> DutchAuctionState:
    try:
        price = await execute_atomic_purchase(listing_id, payload.buyer_wallet)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if price > payload.max_acceptable_price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="price_above_limit")
    return DutchAuctionState(
        listing_id=listing_id,
        current_price=price,
        next_drop_at=None,
        is_active=False,
    )
