"""Music Legends — Telegram Mini App FastAPI backend.
Serves /api/* routes AND the built React frontend at /.
"""
import sys, os, hmac, hashlib, urllib.parse
# Make repo root importable so database.py, config/, battle_engine.py all resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from tma.api.routers import users, cards, packs, economy, battle, marketplace, trade, dust, battle_pass, vip, user_packs # noqa: E402

app = FastAPI(title="Music Legends TMA", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Telegram WebView origin is unpredictable
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "tma-api"}


@app.get("/api/debug")
def debug(request: Request):
    """No-auth endpoint to diagnose token/auth configuration."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    auth_header = request.headers.get("authorization", "")
    result = {
        "token_set": bool(token),
        "token_length": len(token),
        "token_preview": token[:8] + "..." if len(token) > 8 else "(empty)",
        "auth_header_present": bool(auth_header),
        "database_url_set": bool(os.environ.get("DATABASE_URL", "")),
        "tma_url": os.environ.get("TMA_URL", "(not set)"),
    }
    if auth_header.startswith("tma ") and token:
        try:
            raw = auth_header[4:]
            params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
            received_hash = params.pop("hash", "")
            check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
            secret_key = hmac.new(b"WebAppData", token.strip().encode(), hashlib.sha256).digest()
            expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
            result["auth_valid"] = hmac.compare_digest(received_hash, expected)
            result["hash_match"] = received_hash[:12] + "..." if received_hash else "(no hash)"
            result["user_data"] = params.get("user", "(none)")[:100]
        except Exception as e:
            result["auth_error"] = str(e)
    return result


# ── Routers ───────────────────────────────────────────────────────
app.include_router(users.router)
app.include_router(cards.router)
app.include_router(packs.router)
app.include_router(economy.router)
app.include_router(battle.router)
app.include_router(marketplace.router)
app.include_router(trade.router)
app.include_router(dust.router)
app.include_router(battle_pass.router)
app.include_router(vip.router)
app.include_router(user_packs.router)

# ── Telegram Bot webhook ───────────────────────────────────────────
from tma.api.bot.handlers import setup_webhook_route  # noqa: E402
setup_webhook_route(app)

# ── Serve built React app (only if dist/ exists) ──────────────────
_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
