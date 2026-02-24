"""Telegram initData HMAC validation — FastAPI dependency.
Every API request must include: Authorization: tma <raw_init_data>
"""
import hmac
import hashlib
import json
import os
import urllib.parse
from fastapi import Header, HTTPException


def _get_secret_key() -> bytes:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()


def validate_init_data(raw: str) -> dict:
    """Validate Telegram initData and return the user dict.
    Raises ValueError on invalid or missing hash."""
    if not raw or raw.strip() == "":
        raise ValueError("EMPTY_INIT_DATA: open the app from your Telegram bot, not a browser")
    params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    received_hash = params.pop("hash", "")
    if not received_hash:
        raise ValueError("NO_HASH: initData has no hash field — not a valid Telegram launch")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("SERVER_CONFIG: TELEGRAM_BOT_TOKEN not set on server")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    print(f"[AUTH] token_len={len(token)} hash_ok={hmac.compare_digest(received_hash, expected)} user={params.get('user','')[:60]}")
    if not hmac.compare_digest(received_hash, expected):
        raise ValueError("BAD_SIGNATURE: HMAC mismatch — TELEGRAM_BOT_TOKEN in Railway may be wrong")
    user_raw = params.get("user", "{}")
    return json.loads(user_raw)  # {"id": int, "username": str, "first_name": str, ...}


def get_tg_user(authorization: str = Header(...)) -> dict:
    """FastAPI dependency. Usage: tg: dict = Depends(get_tg_user)
    Returns Telegram user dict with at minimum: id (int), username (str)."""
    if not authorization.startswith("tma "):
        raise HTTPException(401, "Authorization must start with 'tma '")
    try:
        return validate_init_data(authorization[4:])
    except ValueError as e:
        raise HTTPException(401, str(e))
