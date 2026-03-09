"""Trade router — manage player-to-player trades."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List
from tma.api.auth import get_tg_user
from database import get_db
from sqlalchemy import desc
from models import User

router = APIRouter(prefix="/api/trades", tags=["trades"])


def _extract_telegram_id(db, user: User) -> int | None:
    """Best-effort Telegram ID extraction across legacy/new schemas."""
    tag = (user.discord_tag or "").strip()
    if tag.startswith("telegram:"):
        try:
            return int(tag.split(":", 1)[1])
        except Exception:
            return None

    try:
        uid = int(str(user.user_id))
    except Exception:
        return None

    # New schema: offset id.
    if uid >= db._TG_OFFSET:
        return uid - db._TG_OFFSET

    # Legacy Telegram IDs are much smaller than Discord snowflakes.
    if 1_000_000 <= uid <= 9_999_999_999:
        return uid

    return None

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


@router.get("/partners")
def search_trade_partners(
    query: str = Query(default="", max_length=64),
    tg: dict = Depends(get_tg_user),
):
    """Search Telegram users to trade with by username or Telegram ID."""
    db = get_db()
    me = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    me_user_id = str(me["user_id"])
    q = (query or "").strip().lower().lstrip("@")

    session = db.get_session()
    try:
        rows = (
            session.query(User)
            .order_by(desc(User.last_active))
            .limit(500)
            .all()
        )
        out = []
        for u in rows:
            if str(u.user_id) == me_user_id:
                continue
            tg_id_int = _extract_telegram_id(db, u)
            if not tg_id_int:
                continue
            tg_id = str(tg_id_int)
            if not tg_id:
                continue

            username = (u.username or "").strip()
            if q:
                hit = (
                    q in username.lower()
                    or q in str(tg_id)
                )
                if not hit:
                    continue
            out.append({
                "telegram_id": tg_id_int,
                "username": username or f"user_{tg_id}",
            })

        return {"partners": out[:25]}
    finally:
        session.close()


@router.get("/partners/{partner_telegram_id}/cards")
def get_partner_cards(partner_telegram_id: int, tg: dict = Depends(get_tg_user)):
    """Return visible card list for a selected trade partner."""
    db = get_db()
    # Ensure caller exists/authenticated
    db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    partner = db.get_telegram_user_by_id(int(partner_telegram_id))
    partner_user_id = str(partner["user_id"]) if partner else str(db._TG_OFFSET + int(partner_telegram_id))
    cards = db.get_user_collection(partner_user_id)
    if not cards and not partner:
        # Legacy fallback in case the row uses raw telegram id.
        cards = db.get_user_collection(str(partner_telegram_id))
    return {"cards": cards[:100], "total": len(cards)}
