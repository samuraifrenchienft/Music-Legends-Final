"""Trade router — manage player-to-player trades."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api/trades", tags=["trades"])

class CreateTradeRequest(BaseModel):
    partner_id: int
    offered_card_ids: List[str]
    requested_card_ids: List[str]
    offered_gold: int = 0
    requested_gold: int = 0

@router.post("")
def create_trade(body: CreateTradeRequest, tg: dict = Depends(get_tg_user)):
    """Create a new trade."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.create_trade(
        initiator_id=user["user_id"],
        partner_id=body.partner_id,
        offered_cards=body.offered_card_ids,
        requested_cards=body.requested_card_ids,
        offered_gold=body.offered_gold,
        requested_gold=body.requested_gold
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to create trade."))
    return result

@router.post("/{trade_id}/accept")
def accept_trade(trade_id: str, tg: dict = Depends(get_tg_user)):
    """Accept a trade."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.accept_trade(trade_id, user["user_id"])
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to accept trade."))
    return result

@router.post("/{trade_id}/cancel")
def cancel_trade(trade_id: str, tg: dict = Depends(get_tg_user)):
    """Cancel a trade."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.cancel_trade(trade_id, user["user_id"])
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to cancel trade."))
    return result

@router.get("")
def get_trades(tg: dict = Depends(get_tg_user)):
    """Get user's trade history."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    trades = db.get_user_trades(user["user_id"])
    return {"trades": trades}
