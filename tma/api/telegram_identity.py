"""Shared Telegram identity helpers for TMA routers."""
from models import User


def extract_telegram_id_from_user(db, user: User | None) -> int | None:
    """Best-effort Telegram ID extraction across legacy/new schemas."""
    if not user:
        return None

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
