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


def _synthetic_dev_user(x_forwarded_for: str = "", user_agent: str = "") -> dict:
    """
    Build a deterministic synthetic user for dev mode when initData is missing.
    This prevents all browser sessions collapsing into user id=1.
    """
    seed = (x_forwarded_for or "").strip() or (user_agent or "").strip() or "dev"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    # Keep synthetic IDs away from typical Telegram ids.
    synthetic_id = 8_000_000_000 + (int(digest[:8], 16) % 999_999_999)
    return {
        "id": synthetic_id,
        "username": f"dev_{digest[:8]}",
        "first_name": "Dev",
    }


def _parse_user_from_raw(
    raw: str,
    x_forwarded_for: str = "",
    user_agent: str = "",
    allow_synthetic: bool = True,
) -> dict:
    """Extract user from initData WITHOUT verifying the HMAC. Dev only."""
    params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    user_raw = params.get("user", "{}")
    user = json.loads(user_raw) if user_raw else {}
    if not user.get("id"):
        if not allow_synthetic:
            raise ValueError("DEV_MODE_NO_INIT_DATA: missing Telegram user context in initData")
        # No user in initData at all — create deterministic synthetic dev user.
        fallback = _synthetic_dev_user(x_forwarded_for=x_forwarded_for, user_agent=user_agent)
        print(
            f"[AUTH] DEV_MODE synthetic user_id={fallback['id']} "
            f"seed={'xff' if x_forwarded_for else 'ua' if user_agent else 'default'}"
        )
        return fallback
    print(f"[AUTH] DEV_MODE skip_hmac user_id={user.get('id')} username={user.get('username')}")
    return user


def get_tg_user(
    authorization: str = Header(default=""),
    x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data"),
    referer: str = Header(default="", alias="Referer"),
    x_forwarded_for: str = Header(default="", alias="X-Forwarded-For"),
    user_agent: str = Header(default="", alias="User-Agent"),
) -> dict:
    """FastAPI dependency. Returns Telegram user dict."""
    skip_hmac = os.environ.get("TMA_SKIP_HMAC", "").lower() == "true"
    allow_synth = os.environ.get("TMA_ALLOW_SYNTHETIC_DEV_USER", "").lower() == "true"

    def _extract_raw_init_data() -> str:
        """Support multiple header styles used by clients/proxies."""
        auth = (authorization or "").strip()
        if auth:
            lower = auth.lower()
            if lower.startswith("tma "):
                return auth[4:].strip()
            if lower.startswith("bearer "):
                token = auth[7:].strip()
                if token.lower().startswith("tma "):
                    return token[4:].strip()
                return token
            # Some clients send raw initData directly in Authorization.
            if "user=" in auth or "hash=" in auth:
                return auth
        x_tg = (x_telegram_init_data or "").strip()
        if x_tg:
            return x_tg
        # Telegram WebView often includes initData as tgWebAppData in page URL.
        ref = (referer or "").strip()
        if ref:
            try:
                q = urllib.parse.urlparse(ref).query
                qs = urllib.parse.parse_qs(q, keep_blank_values=True)
                ref_data = (qs.get("tgWebAppData", [""])[0] or "").strip()
                if ref_data:
                    return ref_data
            except Exception:
                pass
        return ""

    raw = _extract_raw_init_data()

    # Dev bypass: skip HMAC, just parse user from initData
    if skip_hmac:
        try:
            # When initData is empty, we must allow synthetic or the app cannot load.
            use_synthetic = allow_synth or not raw.strip()
            return _parse_user_from_raw(
                raw,
                x_forwarded_for=x_forwarded_for,
                user_agent=user_agent,
                allow_synthetic=use_synthetic,
            )
        except ValueError as e:
            raise HTTPException(401, str(e))

    if not raw:
        raise HTTPException(
            401,
            "Missing Telegram initData. Send 'Authorization: tma <initData>' "
            "or 'X-Telegram-Init-Data: <initData>'.",
        )
    try:
        return validate_init_data(raw)
    except ValueError as e:
        raise HTTPException(401, str(e))
