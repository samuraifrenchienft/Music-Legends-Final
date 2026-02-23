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
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()


def validate_init_data(raw: str) -> dict:
    """Validate Telegram initData and return the user dict.
    Raises ValueError on invalid or missing hash."""
    params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    received_hash = params.pop("hash", "")
    if not received_hash:
        raise ValueError("Missing hash in initData")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    expected = hmac.new(
        _get_secret_key(), check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(received_hash, expected):
        raise ValueError("initData signature invalid")
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
