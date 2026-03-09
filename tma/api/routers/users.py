"""Users router — identity, profile, account linking."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from tma.api.auth import get_tg_user
from database import get_db

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
    """Search active Telegram users by username or Telegram ID."""
    db = get_db()
    db.get_or_create_telegram_user(
        telegram_id=tg["id"],
        telegram_username=tg.get("username", ""),
        first_name=tg.get("first_name", ""),
    )

    term = (q or "").strip()
    if not term:
        return {"players": []}

    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    is_id_lookup = term.isdigit()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        if is_id_lookup:
            cursor.execute(
                """
                SELECT user_id, username, telegram_id, COALESCE(last_active, created_at) AS active_at
                FROM users
                WHERE CAST(telegram_id AS TEXT) = ?
                  AND CAST(telegram_id AS TEXT) != ?
                  AND telegram_id IS NOT NULL
                  AND COALESCE(last_active, created_at) >= ?
                LIMIT ?
                """,
                (term, str(tg["id"]), cutoff, limit),
            )
        else:
            cursor.execute(
                """
                SELECT user_id, username, telegram_id, COALESCE(last_active, created_at) AS active_at
                FROM users
                WHERE LOWER(COALESCE(username, '')) LIKE LOWER(?)
                  AND CAST(telegram_id AS TEXT) != ?
                  AND telegram_id IS NOT NULL
                  AND COALESCE(last_active, created_at) >= ?
                ORDER BY COALESCE(last_active, created_at) DESC
                LIMIT ?
                """,
                (f"%{term}%", str(tg["id"]), cutoff, limit),
            )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []

    players = []
    for row in rows:
        item = dict(zip(cols, row))
        players.append(
            {
                "user_id": item.get("user_id"),
                "username": item.get("username") or f"tg_{item.get('telegram_id')}",
                "telegram_id": int(item.get("telegram_id")),
                "active_at": item.get("active_at"),
            }
        )
    return {"players": players}
