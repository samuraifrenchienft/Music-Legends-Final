"""Marketplace router — buy/sell cards and packs."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

class SellRequest(BaseModel):
    card_id: str
    price: int

@router.get("")
def get_listings(tg: dict = Depends(get_tg_user)):
    """Get all active marketplace listings."""
    db = get_db()
    listings = db.get_marketplace_listings()
    return {"listings": listings}

@router.post("/sell")
def sell_card(body: SellRequest, tg: dict = Depends(get_tg_user)):
    """List a card for sale on the marketplace."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    
    # Verify ownership
    cards = db.get_user_collection(user["user_id"])
    if not any(c.get("card_id") == body.card_id for c in cards):
        raise HTTPException(403, "You don't own this card.")

    result = db.create_marketplace_listing(user["user_id"], body.card_id, body.price)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to list card."))
    
    return result

@router.post("/buy/{listing_id}")
def buy_card(listing_id: int, tg: dict = Depends(get_tg_user)):
    """Buy a card from the marketplace."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    
    result = db.purchase_marketplace_listing(user["user_id"], listing_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to purchase card."))
    
    return result
