"""Telegram initData HMAC validation — FastAPI dependency.
Every API request must include: Authorization: tma <raw_init_data>

Set TMA_SKIP_HMAC=true in Railway to bypass signature check (dev only).
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
    """Validate Telegram initData and return the user dict."""
    if not raw or not raw.strip():
        raise ValueError("EMPTY_INIT_DATA: open from your Telegram bot, not a browser")
    params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    received_hash = params.pop("hash", "")
    if not received_hash:
        raise ValueError("NO_HASH: initData missing hash — not a valid Telegram launch")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("SERVER_CONFIG: TELEGRAM_BOT_TOKEN not set")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    match = hmac.compare_digest(received_hash, expected)
    print(f"[AUTH] token_len={len(token)} hmac_ok={match} user={params.get('user','')[:60]}")
    if not match:
        raise ValueError("BAD_SIGNATURE: HMAC mismatch — check TELEGRAM_BOT_TOKEN in Railway")
    user_raw = params.get("user", "{}")
    return json.loads(user_raw)


def _parse_user_from_raw(raw: str) -> dict:
    """Extract user from initData WITHOUT verifying the HMAC. Dev only."""
    params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    user_raw = params.get("user", "{}")
    user = json.loads(user_raw) if user_raw else {}
    if not user.get("id"):
        # No user in initData at all — create a synthetic dev user
        return {"id": 1, "username": "dev_user", "first_name": "Dev"}
    print(f"[AUTH] DEV_MODE skip_hmac user_id={user.get('id')} username={user.get('username')}")
    return user


def get_tg_user(authorization: str = Header(default="")) -> dict:
    """FastAPI dependency. Returns Telegram user dict."""
    skip_hmac = os.environ.get("TMA_SKIP_HMAC", "").lower() == "true"

    # Dev bypass: skip HMAC, just parse user from initData
    if skip_hmac:
        raw = authorization[4:] if authorization.startswith("tma ") else authorization
        return _parse_user_from_raw(raw)

    if not authorization.startswith("tma "):
        raise HTTPException(401, "Authorization must start with 'tma '")
    try:
        return validate_init_data(authorization[4:])
    except ValueError as e:
        raise HTTPException(401, str(e))
