"""Economy router — gold/XP/daily claim/leaderboard."""
from fastapi import APIRouter, Depends, HTTPException, Query
from tma.api.auth import get_tg_user
from database import get_db
from cards_config import compute_card_power

router = APIRouter(prefix="/api", tags=["economy"])


@router.get("/economy")
def get_economy(tg: dict = Depends(get_tg_user)):
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    return db.get_user_economy(user["user_id"]) or {}


@router.post("/economy/daily")
def claim_daily(tg: dict = Depends(get_tg_user)):
    """Claim daily reward. Returns cards + gold or error if already claimed today."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.claim_daily_reward(user["user_id"])
    if not result.get("success"):
        raise HTTPException(400, result.get("message", "Already claimed today"))
    for c in result.get("cards", []):
        c["power"] = compute_card_power(c)
    return result


@router.get("/leaderboard")
def get_leaderboard(
    metric: str = Query("wins", enum=["wins", "gold", "total_battles"]),
    limit: int = Query(10, ge=1, le=50),
    tg: dict = Depends(get_tg_user),
):
    db = get_db()
    return {"entries": db.get_leaderboard(metric=metric, limit=limit)}
