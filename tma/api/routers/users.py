"""Users router — identity, profile, account linking."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from tma.api.auth import get_tg_user
from database import get_db
from models import User

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me")
def get_me(tg: dict = Depends(get_tg_user)):
    """Return current user profile + economy. Creates account on first call.
    New users automatically receive a welcome daily claim (starter cards + gold)."""
    db = get_db()
    user = db.get_or_create_telegram_user(
        telegram_id=tg["id"],
        telegram_username=tg.get("username", ""),
        first_name=tg.get("first_name", ""),
    )

    # Auto-grant first daily claim for brand-new accounts so they have cards
    if user.get("is_new"):
        try:
            result = db.claim_daily_reward(user["user_id"])
            print(f"[USERS] Welcome pack granted to new user {user['user_id']}: {result.get('success')}")
        except Exception as e:
            print(f"[USERS] Welcome pack failed for {user['user_id']}: {e}")

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


@router.get("/players/search")
def search_players(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=25),
    tg: dict = Depends(get_tg_user),
):
    """Search recently active Telegram users by username or Telegram ID."""
    db = get_db()
    db.get_or_create_telegram_user(
        telegram_id=tg["id"],
        telegram_username=tg.get("username", ""),
        first_name=tg.get("first_name", ""),
    )

    term = (q or "").strip()
    if not term:
        return {"players": []}

    cutoff = datetime.utcnow() - timedelta(days=30)
    is_id_lookup = term.isdigit()

    session = db.get_session()
    try:
        q_users = session.query(User).filter(User.user_id.isnot(None))
        q_users = q_users.filter(User.last_active >= cutoff)
        # Telegram internal ids are offset by 9_000_000_000
        q_users = q_users.filter(User.user_id >= str(db._TG_OFFSET))
        q_users = q_users.filter(User.user_id < str(db._TG_OFFSET + 10_000_000_000))

        if is_id_lookup:
            target_user_id = str(db._TG_OFFSET + int(term))
            q_users = q_users.filter(User.user_id == target_user_id)
        else:
            q_users = q_users.filter(User.username.ilike(f"%{term}%"))

        rows = q_users.order_by(User.last_active.desc()).limit(limit).all()
        players = []
        for u in rows:
            if str(u.user_id) == str(db._TG_OFFSET + tg["id"]):
                continue
            try:
                telegram_id = int(str(u.user_id)) - db._TG_OFFSET
            except Exception:
                continue
            players.append(
                {
                    "user_id": str(u.user_id),
                    "username": u.username or f"user_{telegram_id}",
                    "telegram_id": telegram_id,
                    "active_at": u.last_active.isoformat() if u.last_active else None,
                }
            )
        return {"players": players}
    finally:
        session.close()
