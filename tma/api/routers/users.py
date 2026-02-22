"""Users router — identity, profile, account linking."""
from fastapi import APIRouter, Depends
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me")
def get_me(tg: dict = Depends(get_tg_user)):
    """Return current user profile + economy. Creates account on first call."""
    db = get_db()
    user = db.get_or_create_telegram_user(
        telegram_id=tg["id"],
        telegram_username=tg.get("username", ""),
        first_name=tg.get("first_name", ""),
    )
    economy = db.get_user_economy(user["user_id"]) or {}
    stats = db.get_user_stats(user["user_id"]) or {}
    return {
        "user_id":       user["user_id"],
        "username":      user["username"],
        "telegram_id":   tg["id"],
        "is_new":        user.get("is_new", False),
        "gold":          economy.get("gold", 0),
        "xp":            economy.get("xp", 0),
        "level":         economy.get("level", 1),
        "total_battles": stats.get("total_battles", 0),
        "wins":          stats.get("wins", 0),
        "losses":        stats.get("losses", 0),
    }


@router.post("/link/generate")
def generate_link_code(tg: dict = Depends(get_tg_user)):
    """Generate a 6-char code. Player enters this in Discord /link_telegram.
    Code valid 10 minutes then expires."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    code = db.generate_tma_link_code(user["user_id"])
    return {
        "code": code,
        "message": "Enter /link_telegram " + code + " in Discord to merge accounts.",
        "expires_minutes": 10,
    }
