"""Main API file for the Telegram Mini App."""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tma.api.routers import users, cards, packs, economy, battle, marketplace, trade, dust, battle_pass, vip, user_packs # noqa: E402

app = FastAPI()

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
