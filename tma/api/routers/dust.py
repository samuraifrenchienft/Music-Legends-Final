"""Dust and crafting router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api/dust", tags=["dust"])

class DustCardsRequest(BaseModel):
    card_ids: List[str]

class CraftCardRequest(BaseModel):
    card_id: str

@router.get("")
def get_dust_balance(tg: dict = Depends(get_tg_user)):
    """Get user's dust balance."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    dust_balance = db.get_dust_balance(user["user_id"])
    return {"dust": dust_balance}

@router.post("/dust_cards")
def dust_cards(body: DustCardsRequest, tg: dict = Depends(get_tg_user)):
    """Convert cards into dust."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    success, message = db.dust_cards(user["user_id"], body.card_ids)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/craft_card")
def craft_card(body: CraftCardRequest, tg: dict = Depends(get_tg_user)):
    """Craft a card using dust."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    success, message = db.craft_card(user["user_id"], body.card_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}
