"""Music Legends — Telegram Mini App FastAPI backend.
Serves /api/* routes AND the built React frontend at /.
"""
import sys, os
# Make repo root importable so database.py, config/, battle_engine.py all resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# ── Routers ───────────────────────────────────────────────────────
from tma.api.routers import users, cards, packs, economy, battle  # noqa: E402
app.include_router(users.router)
app.include_router(cards.router)
app.include_router(packs.router)
app.include_router(economy.router)
app.include_router(battle.router)

# ── Telegram Bot webhook ───────────────────────────────────────────
from tma.api.bot.handlers import setup_webhook_route  # noqa: E402
setup_webhook_route(app)

# ── Serve built React app (only if dist/ exists) ──────────────────
_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
