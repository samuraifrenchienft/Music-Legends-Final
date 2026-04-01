"""Trade router — manage player-to-player trades."""
import json
import os
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List
from tma.api.auth import get_tg_user
from tma.api.telegram_identity import extract_telegram_id_from_user
from database import get_db
from sqlalchemy import desc
from models import User

router = APIRouter(prefix="/api/trades", tags=["trades"])

def _lookup_telegram_user_live(query: str) -> dict | None:
    """
    Best-effort live Telegram lookup by @username using Bot API getChat.
    Returns {telegram_id, username} or None when unavailable/unresolvable.
    """
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    username = (query or "").strip().lstrip("@")
    if not token or not username:
        return None
    if any(ch.isspace() for ch in username):
        return None
    try:
        url = f"https://api.telegram.org/bot{token}/getChat?chat_id=%40{quote_plus(username)}"
        req = Request(url, method="GET")
        with urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore") or "{}")
        if not payload.get("ok"):
            return None
        result = payload.get("result") or {}
        tg_id = result.get("id")
        if not isinstance(tg_id, int):
            return None
        out_username = (result.get("username") or username).strip()
        return {"telegram_id": tg_id, "username": out_username or f"user_{tg_id}"}
    except Exception:
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
    if int(body.partner_id) == int(tg["id"]):
        raise HTTPException(400, "You can't trade with yourself")
    result = db.create_trade(
        initiator_id=user["user_id"],
        partner_id=body.partner_id,
        offered_cards=body.offered_card_ids,
        requested_cards=body.requested_card_ids,
        offered_gold=body.offered_gold,
        requested_gold=body.requested_gold
    )
    if not result.get("success"):
        print(
            f"[TRADE] create failed tg={tg['id']} partner={body.partner_id} "
            f"error={result.get('error', 'unknown')}"
        )
        raise HTTPException(400, result.get("error", "Failed to create trade."))
    return result

@router.post("/{trade_id}/accept")
def accept_trade(trade_id: str, tg: dict = Depends(get_tg_user)):
    """Accept a trade."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.accept_trade(trade_id, user["user_id"])
    if not result.get("success"):
        print(f"[TRADE] accept failed tg={tg['id']} trade_id={trade_id} error={result.get('error', 'unknown')}")
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
            tg_id_int = extract_telegram_id_from_user(db, u)
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

        if q:
            # Prioritize exact username/id matches at the top.
            exact = []
            partial = []
            for p in out:
                u = str(p.get("username") or "").lower()
                tid = str(p.get("telegram_id") or "")
                if u == q or tid == q:
                    exact.append(p)
                else:
                    partial.append(p)
            out = exact + partial

        # Live Telegram lookup fallback for typed @username queries.
        # This helps when the target user isn't yet in local DB search results.
        if q and not q.isdigit():
            live = _lookup_telegram_user_live(q)
            if live and str(live["telegram_id"]) != str(tg["id"]):
                if all(int(p.get("telegram_id", 0)) != int(live["telegram_id"]) for p in out):
                    out.insert(0, live)

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
