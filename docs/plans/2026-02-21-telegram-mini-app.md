# Telegram Mini App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port Music Legends to a Telegram Mini App using the existing Railway PostgreSQL database, so Telegram users can collect cards, open packs, battle, and claim daily rewards without needing Discord.

**Architecture:** FastAPI backend in `tma/api/` imports `database.py` directly (zero DB rewrite). React + Vite frontend in `tma/frontend/` uses `@telegram-apps/sdk` for auth. A `python-telegram-bot` webhook handler sends notifications and handles `/start`. Everything runs as a single Railway service (FastAPI serves the built React static files).

**Tech Stack:** Python FastAPI, python-telegram-bot 21+, React 18 + Vite + TypeScript, @telegram-apps/sdk, Railway PostgreSQL (shared with Discord bot).

**Research:** See `docs/research/2026-02-21-tma-research.md` for full TMA architecture notes.

---

## Phase 1 — Database Schema + FastAPI Skeleton

**Goal:** FastAPI server running on Railway, initData auth working, /me endpoint returns user data.

---

### Task 1: Add Telegram columns to database

**Files:**
- Modify: `database.py` — add migration in `init_database()` / `_init_postgresql()`

**Step 1: Add the ALTER TABLE migration**

Find the ALTER TABLE block in `_init_postgresql()` (around line 1300+) and add:

```python
# Telegram Mini App user linking
try:
    cursor.execute("ALTER TABLE users ADD COLUMN telegram_user_id BIGINT")
except Exception:
    pass
try:
    cursor.execute("ALTER TABLE users ADD COLUMN telegram_username TEXT")
except Exception:
    pass
try:
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_user_id)")
except Exception:
    pass
```

And mirror it in the SQLite `init_database()` ALTER block:
```python
for col_def in [
    ("telegram_user_id", "INTEGER"),
    ("telegram_username", "TEXT"),
]:
    col, typ = col_def
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(users)")
        existing = [r[1] for r in cursor.fetchall()]
        if col not in existing:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
```

**Step 2: Add get_or_create_telegram_user() to DatabaseManager**

```python
def get_or_create_telegram_user(self, telegram_user_id: int, telegram_username: str, first_name: str = "") -> Dict:
    """Find or create a user record for a Telegram Mini App user."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, gold FROM users u "
            "JOIN user_inventory ui ON u.user_id = ui.user_id "
            "WHERE u.telegram_user_id = ?",
            (telegram_user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"user_id": row[0], "username": row[1], "gold": row[2], "is_new": False}

        # New user — use negative telegram_user_id as user_id to avoid collisions
        # with Discord IDs (Discord IDs are 17-18 digits; tg IDs are 9-10 digits,
        # so prefix with 9_000_000_000 to guarantee no overlap)
        synthetic_id = 9_000_000_000 + telegram_user_id
        display_name = telegram_username or first_name or f"tg_{telegram_user_id}"

        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, telegram_user_id, telegram_username) "
            "VALUES (?, ?, ?, ?)",
            (synthetic_id, display_name, telegram_user_id, telegram_username)
        )
        cursor.execute(
            "INSERT OR IGNORE INTO user_inventory (user_id, gold) VALUES (?, 500)",
            (synthetic_id,)
        )
        conn.commit()
        return {"user_id": synthetic_id, "username": display_name, "gold": 500, "is_new": True}
```

**Step 3: Run tests**

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends
python -m pytest tests/test_bot_core.py -v --noconftest
```

Expected: all 40 tests pass (no changes to tested paths).

**Step 4: Commit**

```bash
git add database.py
git commit -m "feat(tma): add telegram_user_id column + get_or_create_telegram_user()"
```

---

### Task 2: Create FastAPI backend skeleton

**Files:**
- Create: `tma/api/__init__.py`
- Create: `tma/api/auth.py`
- Create: `tma/api/main.py`
- Create: `tma/__init__.py`

**Step 1: Write the auth dependency**

Create `tma/api/auth.py`:

```python
"""Telegram initData validation — FastAPI dependency."""
import hmac
import hashlib
import json
import urllib.parse
import os
from fastapi import Header, HTTPException

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


def _validate_init_data(init_data: str) -> dict:
    """Validate Telegram initData HMAC and return user dict. Raises ValueError on failure."""
    params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", "")
    if not received_hash:
        raise ValueError("Missing hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise ValueError("Invalid hash")
    user_str = params.get("user", "{}")
    return json.loads(user_str)


def get_telegram_user(authorization: str = Header(...)) -> dict:
    """FastAPI dependency: validates initData from Authorization header.
    Returns dict with keys: id, username, first_name.
    Usage: user: dict = Depends(get_telegram_user)
    """
    # Header format: "tma <initData>"
    if not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Invalid auth format")
    init_data = authorization[4:]
    try:
        return _validate_init_data(init_data)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {e}")
```

**Step 2: Write main FastAPI app**

Create `tma/api/main.py`:

```python
"""Music Legends Telegram Mini App — FastAPI Backend."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))  # repo root

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .auth import get_telegram_user
from database import get_db

app = FastAPI(title="Music Legends TMA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram WebView can come from any origin
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "tma-api"}

@app.get("/api/me")
def get_me(tg_user: dict = Depends(get_telegram_user)):
    """Return current user profile + inventory."""
    db = get_db()
    user = db.get_or_create_telegram_user(
        telegram_user_id=tg_user["id"],
        telegram_username=tg_user.get("username", ""),
        first_name=tg_user.get("first_name", ""),
    )
    economy = db.get_user_economy(user["user_id"])
    stats = db.get_user_stats(user["user_id"])
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "is_new": user.get("is_new", False),
        "gold": economy.get("gold", 0),
        "xp": economy.get("xp", 0),
        "level": economy.get("level", 1),
        "total_battles": stats.get("total_battles", 0),
        "wins": stats.get("wins", 0),
    }

# Mount frontend static files (built React app)
_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
```

**Step 3: Write empty routers (stubs for now)**

Create `tma/api/routers/__init__.py` (empty).

**Step 4: Test locally**

```bash
pip install fastapi uvicorn[standard]
cd C:/Users/AbuBa/Desktop/Music-Legends
TELEGRAM_BOT_TOKEN=dummy uvicorn tma.api.main:app --reload --port 8001
```

Expected: GET http://localhost:8001/health → `{"status": "ok"}`

**Step 5: Commit**

```bash
git add tma/
git commit -m "feat(tma): FastAPI skeleton with initData auth + /api/me endpoint"
```

---

### Task 3: Railway deployment config for TMA service

**Files:**
- Create: `tma/Dockerfile`
- Create: `tma/railway.toml` (or update root `railway.toml` to add service)

**Step 1: Write Dockerfile**

Create `tma/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Python deps from root requirements + TMA extras
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    fastapi uvicorn[standard] python-telegram-bot[webhooks] telegram-webapp-auth

# Copy entire repo (needed for database.py, config/, etc.)
COPY . .

EXPOSE 8080
CMD ["uvicorn", "tma.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 2: Set Railway env vars** (do this in Railway dashboard, not code)

```
TELEGRAM_BOT_TOKEN=<get from @BotFather>
DATABASE_URL=<same as existing bot>
PORT=8080
```

**Step 3: Commit**

```bash
git add tma/Dockerfile
git commit -m "feat(tma): Railway Dockerfile for TMA API service"
```

---

## Phase 2 — Core API Endpoints

**Goal:** All game data readable via REST API. Collection, packs, economy, leaderboard all working.

---

### Task 4: Cards + Collection endpoints

**Files:**
- Create: `tma/api/routers/cards.py`
- Modify: `tma/api/main.py` — include router

**Step 1: Write cards router**

```python
# tma/api/routers/cards.py
from fastapi import APIRouter, Depends
from ..auth import get_telegram_user
from database import get_db

router = APIRouter(prefix="/api/cards", tags=["cards"])

@router.get("")
def list_collection(tg_user: dict = Depends(get_telegram_user)):
    db = get_db()
    user = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))
    cards = db.get_user_collection(user["user_id"])
    # Attach computed power to each card
    from config.cards import compute_card_power, RARITY_EMOJI
    for c in cards:
        c["power"] = compute_card_power(c)
        c["rarity_emoji"] = RARITY_EMOJI.get(c.get("rarity", "common"), "⚪")
    return {"cards": cards, "total": len(cards)}

@router.get("/{card_id}")
def get_card(card_id: str, tg_user: dict = Depends(get_telegram_user)):
    db = get_db()
    user = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))
    cards = db.get_user_collection(user["user_id"])
    card = next((c for c in cards if c.get("card_id") == card_id), None)
    if not card:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Card not found")
    from config.cards import compute_card_power
    card["power"] = compute_card_power(card)
    return card
```

**Step 2: Wire up in main.py**

```python
from tma.api.routers import cards
app.include_router(cards.router)
```

**Step 3: Test**

```bash
# First get a real initData from the browser (or use a test stub for local dev)
curl http://localhost:8001/api/cards \
  -H "Authorization: tma <your_init_data>"
```

**Step 4: Commit**

```bash
git add tma/api/routers/cards.py tma/api/main.py
git commit -m "feat(tma): GET /api/cards collection endpoint"
```

---

### Task 5: Packs endpoints (view + open)

**Files:**
- Create: `tma/api/routers/packs.py`
- Modify: `tma/api/main.py`

**Step 1: Write packs router**

```python
# tma/api/routers/packs.py
from fastapi import APIRouter, Depends, HTTPException
from ..auth import get_telegram_user
from database import get_db

router = APIRouter(prefix="/api/packs", tags=["packs"])

@router.get("")
def list_packs(tg_user: dict = Depends(get_telegram_user)):
    """Return all packs the user has acquired."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))
    packs = db.get_user_purchased_packs(user["user_id"])
    return {"packs": packs, "total": len(packs)}

@router.post("/{pack_id}/open")
def open_pack(pack_id: str, tg_user: dict = Depends(get_telegram_user)):
    """Open a pack the user owns. Returns the cards received."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))
    # Verify ownership
    packs = db.get_user_purchased_packs(user["user_id"])
    owned_ids = {str(p.get("pack_id")) for p in packs}
    if pack_id not in owned_ids:
        raise HTTPException(status_code=403, detail="Pack not owned")
    result = db.open_pack_for_drop(pack_id, user["user_id"])
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to open pack"))
    from config.cards import compute_card_power
    cards = result.get("cards", [])
    for c in cards:
        c["power"] = compute_card_power(c)
    return {"cards": cards, "pack_id": pack_id}

@router.get("/store")
def get_store(tg_user: dict = Depends(get_telegram_user)):
    """Return available packs for purchase (live packs)."""
    db = get_db()
    packs = db.get_live_packs(limit=20)
    return {"packs": packs}
```

**Step 2: Wire up in main.py**

```python
from tma.api.routers import packs
app.include_router(packs.router)
```

**Step 3: Test**

```bash
curl -X POST http://localhost:8001/api/packs/PACK_ID/open \
  -H "Authorization: tma <init_data>"
```

**Step 4: Commit**

```bash
git add tma/api/routers/packs.py tma/api/main.py
git commit -m "feat(tma): GET /api/packs + POST /api/packs/{id}/open"
```

---

### Task 6: Economy endpoints (gold, daily claim)

**Files:**
- Create: `tma/api/routers/economy.py`
- Modify: `tma/api/main.py`

**Step 1: Write economy router**

```python
# tma/api/routers/economy.py
from fastapi import APIRouter, Depends, HTTPException
from ..auth import get_telegram_user
from database import get_db

router = APIRouter(prefix="/api/economy", tags=["economy"])

@router.get("")
def get_economy(tg_user: dict = Depends(get_telegram_user)):
    db = get_db()
    user = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))
    return db.get_user_economy(user["user_id"])

@router.post("/daily")
def claim_daily(tg_user: dict = Depends(get_telegram_user)):
    """Claim daily reward. Returns cards + gold, or error if already claimed."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))
    result = db.claim_daily_reward(user["user_id"])
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Already claimed today"))
    from config.cards import compute_card_power
    for c in result.get("cards", []):
        c["power"] = compute_card_power(c)
    return result
```

**Step 2: Wire up and commit**

```bash
git add tma/api/routers/economy.py tma/api/main.py
git commit -m "feat(tma): GET /api/economy + POST /api/economy/daily"
```

---

### Task 7: Leaderboard endpoint

**Files:**
- Create: `tma/api/routers/leaderboard.py`

```python
# tma/api/routers/leaderboard.py
from fastapi import APIRouter, Depends, Query
from ..auth import get_telegram_user
from database import get_db

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

@router.get("")
def get_leaderboard(
    metric: str = Query("wins", enum=["wins", "gold", "total_battles"]),
    limit: int = Query(10, le=50),
    tg_user: dict = Depends(get_telegram_user),
):
    db = get_db()
    return {"entries": db.get_leaderboard(metric=metric, limit=limit)}
```

**Commit:**

```bash
git add tma/api/routers/leaderboard.py tma/api/main.py
git commit -m "feat(tma): GET /api/leaderboard"
```

---

## Phase 3 — Battle System API

**Goal:** PvP battles work via TMA. Player 1 challenges, Player 2 gets bot notification, both select packs, battle executes.

---

### Task 8: Battle router — challenge + execute

**Files:**
- Create: `tma/api/routers/battle.py`
- Modify: `tma/api/main.py`

**Step 1: Add pending_tma_battles table to database.py**

In the ALTER TABLE block of `_init_postgresql()`:

```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_tma_battles (
        battle_id TEXT PRIMARY KEY,
        challenger_user_id INTEGER NOT NULL,
        opponent_telegram_id BIGINT,
        opponent_user_id INTEGER,
        challenger_pack_id TEXT,
        opponent_pack_id TEXT,
        wager_tier TEXT DEFAULT 'casual',
        status TEXT DEFAULT 'waiting',  -- waiting | both_selected | complete | cancelled
        result_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '10 minutes')
    )
""")
```

**Step 2: Write battle router**

```python
# tma/api/routers/battle.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import get_telegram_user
from database import get_db

router = APIRouter(prefix="/api/battle", tags=["battle"])

class ChallengeRequest(BaseModel):
    opponent_telegram_id: int
    pack_id: str
    wager_tier: str = "casual"

class PackSelectRequest(BaseModel):
    pack_id: str

@router.post("/challenge")
def create_challenge(body: ChallengeRequest, tg_user: dict = Depends(get_telegram_user)):
    db = get_db()
    challenger = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))

    # Verify challenger owns the pack
    packs = db.get_user_purchased_packs(challenger["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(status_code=403, detail="Pack not owned")

    battle_id = str(uuid.uuid4())[:8].upper()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pending_tma_battles (battle_id, challenger_user_id, opponent_telegram_id, "
            "challenger_pack_id, wager_tier) VALUES (?, ?, ?, ?, ?)",
            (battle_id, challenger["user_id"], body.opponent_telegram_id, body.pack_id, body.wager_tier)
        )
        conn.commit()

    # Notify opponent via bot (non-blocking — fire and forget)
    import asyncio
    asyncio.create_task(_notify_opponent(body.opponent_telegram_id, tg_user, battle_id, body.wager_tier))

    return {"battle_id": battle_id, "status": "waiting_for_opponent"}


@router.post("/{battle_id}/accept")
def accept_challenge(battle_id: str, body: PackSelectRequest, tg_user: dict = Depends(get_telegram_user)):
    """Opponent selects their pack to accept and enter the battle."""
    db = get_db()
    opponent = db.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""))

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_tma_battles WHERE battle_id = ?", (battle_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Battle not found")

    desc = [d[0] for d in cursor.description]
    battle = dict(zip(desc, row))

    if battle["status"] != "waiting":
        raise HTTPException(status_code=400, detail=f"Battle is {battle['status']}")
    if battle["opponent_telegram_id"] != tg_user["id"]:
        raise HTTPException(status_code=403, detail="Not your battle")

    # Verify pack ownership
    packs = db.get_user_purchased_packs(opponent["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(status_code=403, detail="Pack not owned")

    # Both packs selected — execute battle
    c_packs = db.get_user_purchased_packs(battle["challenger_user_id"])
    c_pack = next((p for p in c_packs if str(p.get("pack_id")) == battle["challenger_pack_id"]), None)
    o_pack = next((p for p in packs if str(p.get("pack_id")) == body.pack_id), None)

    result = _execute_tma_battle(db, battle, c_pack, o_pack, opponent["user_id"])

    # Save result
    import json
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_tma_battles SET status='complete', opponent_user_id=?, "
            "opponent_pack_id=?, result_json=? WHERE battle_id=?",
            (opponent["user_id"], body.pack_id, json.dumps(result), battle_id)
        )
        conn.commit()

    return {"battle_id": battle_id, "result": result}


@router.get("/{battle_id}")
def get_battle(battle_id: str, tg_user: dict = Depends(get_telegram_user)):
    """Poll for battle result."""
    db = get_db()
    import json
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, result_json FROM pending_tma_battles WHERE battle_id = ?", (battle_id,))
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Battle not found")
    status, result_json = row
    return {
        "battle_id": battle_id,
        "status": status,
        "result": json.loads(result_json) if result_json else None,
    }


def _execute_tma_battle(db, battle: dict, c_pack: dict, o_pack: dict, opponent_user_id: int) -> dict:
    """Run battle engine, distribute rewards, return result dict."""
    from config.cards import compute_card_power, compute_team_power, RARITY_EMOJI
    from battle_engine import BattleEngine
    from discord_cards import ArtistCard

    c_cards = sorted(c_pack.get("cards", []), key=compute_card_power, reverse=True)
    o_cards = sorted(o_pack.get("cards", []), key=compute_card_power, reverse=True)

    if not c_cards or not o_cards:
        return {"winner": 0, "error": "Empty pack"}

    c_champ = c_cards[0]
    o_champ = o_cards[0]
    c_power = compute_team_power(compute_card_power(c_champ), [compute_card_power(c) for c in c_cards[1:5]])
    o_power = compute_team_power(compute_card_power(o_champ), [compute_card_power(c) for c in o_cards[1:5]])

    result = BattleEngine.execute_battle(
        ArtistCard(name=c_champ.get("name","?"), power=c_power, rarity=c_champ.get("rarity","common")),
        ArtistCard(name=o_champ.get("name","?"), power=o_power, rarity=o_champ.get("rarity","common")),
        battle.get("wager_tier", "casual"),
        p1_override=c_power, p2_override=o_power,
    )

    # Distribute rewards
    p1 = result["player1"]
    p2 = result["player2"]
    db.update_user_economy(battle["challenger_user_id"], gold_change=p1["gold_reward"])
    db.update_user_economy(opponent_user_id, gold_change=p2["gold_reward"])

    return {
        "winner": result["winner"],
        "challenger": {"name": c_champ.get("name"), "power": c_power, "gold_reward": p1["gold_reward"]},
        "opponent": {"name": o_champ.get("name"), "power": o_power, "gold_reward": p2["gold_reward"]},
        "is_critical": result.get("is_critical", False),
    }


async def _notify_opponent(telegram_id: int, challenger_tg: dict, battle_id: str, tier: str):
    """Send Telegram bot message to opponent notifying them of the challenge."""
    import os
    try:
        from telegram import Bot
        bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
        mini_app_url = os.environ.get("TMA_URL", "https://t.me/your_bot/app")
        challenger_name = challenger_tg.get("username") or challenger_tg.get("first_name", "Someone")
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                f"⚔️ **{challenger_name}** challenged you to a Music Legends battle!\n"
                f"Tier: {tier.upper()} | Battle ID: `{battle_id}`\n\n"
                f"[🎴 Accept the challenge]({mini_app_url}?startapp=battle_{battle_id})"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[TMA] Failed to notify opponent {telegram_id}: {e}")
```

**Step 3: Commit**

```bash
git add tma/api/routers/battle.py database.py tma/api/main.py
git commit -m "feat(tma): battle API — challenge, accept, poll result"
```

---

## Phase 4 — Telegram Bot Setup

**Goal:** `/start` command opens the Mini App. Bot sends challenge notifications.

---

### Task 9: Telegram Bot webhook handler

**Files:**
- Create: `tma/api/bot/handlers.py`
- Create: `tma/api/bot/__init__.py`
- Modify: `tma/api/main.py` — add /webhook route

**Step 1: Register a new bot with @BotFather**

In Telegram:
1. Message @BotFather → `/newbot`
2. Name: "Music Legends"
3. Username: `@MusicLegendsBot` (or whatever is available)
4. Copy the token to Railway env as `TELEGRAM_BOT_TOKEN`
5. `/newapp` → create Mini App, set URL to your Railway TMA service URL

**Step 2: Write bot handlers**

```python
# tma/api/bot/handlers.py
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

TMA_URL = os.environ.get("TMA_URL", "https://t.me/your_bot/app")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — show a button to open the Mini App."""
    # Check if deep link param (e.g. battle_XXXXX)
    args = context.args or []
    start_param = args[0] if args else ""

    url = f"{TMA_URL}?startapp={start_param}" if start_param else TMA_URL

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎴 Play Music Legends", web_app=WebAppInfo(url=url))
    ]])
    await update.message.reply_text(
        "🎵 **Music Legends** — collect artist cards, battle friends, win gold!\n\n"
        "Tap below to open the game:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


def build_app() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    return app
```

**Step 3: Add webhook route to main.py**

```python
# In tma/api/main.py — add after existing routes
import json as _json
from telegram import Update

_tg_app = None

@app.on_event("startup")
async def startup():
    global _tg_app
    from tma.api.bot.handlers import build_app
    _tg_app = build_app()
    await _tg_app.initialize()
    # Set webhook
    webhook_url = os.environ.get("TMA_URL", "") + "/webhook"
    if webhook_url.startswith("https"):
        await _tg_app.bot.set_webhook(webhook_url)

@app.post("/webhook")
async def telegram_webhook(request):
    data = await request.json()
    update = Update.de_json(data, _tg_app.bot)
    await _tg_app.process_update(update)
    return {"ok": True}
```

**Step 4: Commit**

```bash
git add tma/api/bot/
git commit -m "feat(tma): Telegram bot webhook + /start → Mini App button"
```

---

## Phase 5 — React Frontend

**Goal:** Working UI that a user can open in Telegram and play the full game.

---

### Task 10: React + Vite TMA scaffold

**Files:**
- Create: `tma/frontend/` (entire React project)

**Step 1: Scaffold using official TMA template**

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends/tma
npm create @telegram-apps/mini-app@latest frontend -- --template react-ts
cd frontend
npm install axios react-router-dom
```

**Step 2: Configure Vite base URL**

Edit `tma/frontend/vite.config.ts`:
```typescript
export default defineConfig({
  plugins: [react()],
  base: '/',
  build: { outDir: 'dist' },
  server: { port: 5173 }
})
```

**Step 3: Create API client with initData auth**

Create `tma/frontend/src/api/client.ts`:

```typescript
import axios from 'axios';
import { retrieveLaunchParams } from '@telegram-apps/sdk';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  try {
    const { initDataRaw } = retrieveLaunchParams();
    if (initDataRaw) {
      config.headers['Authorization'] = `tma ${initDataRaw}`;
    }
  } catch (e) {
    // Running outside Telegram (dev mode)
  }
  return config;
});

export default api;
export const getMe = () => api.get('/api/me');
export const getCards = () => api.get('/api/cards');
export const getPacks = () => api.get('/api/packs');
export const openPack = (packId: string) => api.post(`/api/packs/${packId}/open`);
export const getEconomy = () => api.get('/api/economy');
export const claimDaily = () => api.post('/api/economy/daily');
export const getLeaderboard = (metric = 'wins') => api.get(`/api/leaderboard?metric=${metric}`);
export const challengeBattle = (body: object) => api.post('/api/battle/challenge', body);
export const acceptBattle = (battleId: string, body: object) => api.post(`/api/battle/${battleId}/accept`, body);
export const getBattle = (battleId: string) => api.get(`/api/battle/${battleId}`);
```

**Step 4: Commit**

```bash
git add tma/frontend/
git commit -m "feat(tma): React+Vite frontend scaffold with API client"
```

---

### Task 11: Home page + Navigation

**Files:**
- Modify: `tma/frontend/src/App.tsx`
- Create: `tma/frontend/src/components/NavBar.tsx`
- Create: `tma/frontend/src/pages/Home.tsx`

**Step 1: App.tsx with routing**

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import NavBar from './components/NavBar';
import Home from './pages/Home';
import Collection from './pages/Collection';
import Packs from './pages/Packs';
import Battle from './pages/Battle';
import Daily from './pages/Daily';

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ maxWidth: 480, margin: '0 auto', minHeight: '100vh', backgroundColor: '#0D0B2E', color: '#fff' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/collection" element={<Collection />} />
          <Route path="/packs" element={<Packs />} />
          <Route path="/battle" element={<Battle />} />
          <Route path="/daily" element={<Daily />} />
        </Routes>
        <NavBar />
      </div>
    </BrowserRouter>
  );
}
```

**Step 2: NavBar**

```tsx
// src/components/NavBar.tsx
import { Link, useLocation } from 'react-router-dom';

const tabs = [
  { path: '/', label: '🏠', title: 'Home' },
  { path: '/collection', label: '🃏', title: 'Cards' },
  { path: '/packs', label: '📦', title: 'Packs' },
  { path: '/battle', label: '⚔️', title: 'Battle' },
  { path: '/daily', label: '🎁', title: 'Daily' },
];

export default function NavBar() {
  const { pathname } = useLocation();
  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
      width: '100%', maxWidth: 480, display: 'flex', backgroundColor: '#1a1740',
      borderTop: '1px solid #6B2EBE', paddingBottom: 'env(safe-area-inset-bottom)',
    }}>
      {tabs.map(tab => (
        <Link key={tab.path} to={tab.path} style={{
          flex: 1, textAlign: 'center', padding: '10px 0', fontSize: 22,
          color: pathname === tab.path ? '#F4A800' : '#8888aa',
          textDecoration: 'none',
        }}>
          {tab.label}
          <div style={{ fontSize: 10, marginTop: 2 }}>{tab.title}</div>
        </Link>
      ))}
    </nav>
  );
}
```

**Step 3: Home page with user stats**

```tsx
// src/pages/Home.tsx
import { useEffect, useState } from 'react';
import { getMe } from '../api/client';

export default function Home() {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    getMe().then(r => setUser(r.data)).catch(console.error);
  }, []);

  if (!user) return <div style={{ padding: 20, textAlign: 'center' }}>Loading...</div>;

  return (
    <div style={{ padding: 20, paddingBottom: 80 }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <img src="https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeiehxk5zhdxidab4qtuxg6lblrasxcxb2bkj6a3ipyjue5f7pzo3qi"
          alt="Music Legends" style={{ width: 80, borderRadius: '50%' }} />
        <h2 style={{ color: '#F4A800', marginTop: 8 }}>Music Legends</h2>
        <p style={{ color: '#ccc' }}>Welcome, {user.username}!</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {[
          { label: '💰 Gold', value: user.gold },
          { label: '⭐ XP', value: user.xp },
          { label: '⚔️ Battles', value: user.total_battles },
          { label: '🏆 Wins', value: user.wins },
        ].map(stat => (
          <div key={stat.label} style={{
            background: '#1a1740', borderRadius: 12, padding: 16, textAlign: 'center',
            border: '1px solid #6B2EBE',
          }}>
            <div style={{ fontSize: 24 }}>{stat.value}</div>
            <div style={{ color: '#8888aa', fontSize: 13, marginTop: 4 }}>{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add tma/frontend/src/
git commit -m "feat(tma): Home page + NavBar with routing"
```

---

### Task 12: Collection page

**Files:**
- Create: `tma/frontend/src/pages/Collection.tsx`
- Create: `tma/frontend/src/components/CardComponent.tsx`

**Step 1: Card component**

```tsx
// src/components/CardComponent.tsx
const RARITY_COLORS: Record<string, string> = {
  common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE', legendary: '#F4A800', mythic: '#E74C3C',
};

export default function CardComponent({ card, onClick }: { card: any; onClick?: () => void }) {
  const rarity = card.rarity || 'common';
  const power = card.power || 0;
  const pct = Math.round((power / 135) * 100);

  return (
    <div onClick={onClick} style={{
      background: '#1a1740', borderRadius: 12, padding: 12,
      border: `1px solid ${RARITY_COLORS[rarity]}`,
      cursor: onClick ? 'pointer' : 'default',
    }}>
      {card.image_url && (
        <img src={card.image_url} alt={card.name}
          style={{ width: '100%', borderRadius: 8, aspectRatio: '16/9', objectFit: 'cover' }} />
      )}
      <div style={{ marginTop: 8, fontWeight: 'bold', fontSize: 14 }}>{card.name}</div>
      {card.title && <div style={{ color: '#aaa', fontSize: 12 }}>{card.title}</div>}
      <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ flex: 1, height: 4, background: '#333', borderRadius: 2 }}>
          <div style={{ width: `${pct}%`, height: '100%', background: RARITY_COLORS[rarity], borderRadius: 2 }} />
        </div>
        <span style={{ fontSize: 11, color: RARITY_COLORS[rarity] }}>{power}</span>
      </div>
    </div>
  );
}
```

**Step 2: Collection page**

```tsx
// src/pages/Collection.tsx
import { useEffect, useState } from 'react';
import { getCards } from '../api/client';
import CardComponent from '../components/CardComponent';

export default function Collection() {
  const [cards, setCards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCards().then(r => { setCards(r.data.cards); setLoading(false); });
  }, []);

  if (loading) return <div style={{ padding: 20, textAlign: 'center' }}>Loading collection...</div>;

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h3 style={{ color: '#F4A800', marginBottom: 16 }}>🃏 My Collection ({cards.length})</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {cards.map(card => <CardComponent key={card.card_id} card={card} />)}
      </div>
      {cards.length === 0 && (
        <div style={{ textAlign: 'center', color: '#888', marginTop: 40 }}>
          <p>No cards yet! Open a pack to get started.</p>
        </div>
      )}
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add tma/frontend/src/
git commit -m "feat(tma): Collection page with card grid"
```

---

### Task 13: Pack opening page

**Files:**
- Create: `tma/frontend/src/pages/Packs.tsx`

```tsx
// src/pages/Packs.tsx
import { useEffect, useState } from 'react';
import { getPacks, openPack } from '../api/client';
import CardComponent from '../components/CardComponent';

export default function Packs() {
  const [packs, setPacks] = useState<any[]>([]);
  const [openedCards, setOpenedCards] = useState<any[] | null>(null);
  const [opening, setOpening] = useState(false);

  useEffect(() => { getPacks().then(r => setPacks(r.data.packs)); }, []);

  const handleOpen = async (packId: string) => {
    setOpening(true);
    setOpenedCards(null);
    try {
      const r = await openPack(packId);
      setOpenedCards(r.data.cards);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to open pack');
    } finally {
      setOpening(false);
    }
  };

  if (openedCards) return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h3 style={{ color: '#F4A800' }}>🎉 Pack Opened!</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
        {openedCards.map((card, i) => <CardComponent key={i} card={card} />)}
      </div>
      <button onClick={() => setOpenedCards(null)} style={{
        marginTop: 16, width: '100%', padding: 14, background: '#6B2EBE',
        color: '#fff', border: 'none', borderRadius: 10, fontSize: 16, cursor: 'pointer',
      }}>Back to Packs</button>
    </div>
  );

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h3 style={{ color: '#F4A800', marginBottom: 16 }}>📦 My Packs ({packs.length})</h3>
      {packs.map(pack => (
        <div key={pack.pack_id} style={{
          background: '#1a1740', borderRadius: 12, padding: 14, marginBottom: 10,
          border: '1px solid #6B2EBE',
        }}>
          <div style={{ fontWeight: 'bold' }}>{pack.pack_name}</div>
          <div style={{ color: '#aaa', fontSize: 12, marginTop: 2 }}>
            {pack.pack_tier?.toUpperCase()} • {(pack.cards || []).length} cards
          </div>
          <button onClick={() => handleOpen(pack.pack_id)} disabled={opening} style={{
            marginTop: 10, width: '100%', padding: 10, background: opening ? '#333' : '#F4A800',
            color: '#000', border: 'none', borderRadius: 8, fontWeight: 'bold', cursor: 'pointer',
          }}>
            {opening ? 'Opening...' : '🎴 Open Pack'}
          </button>
        </div>
      ))}
      {packs.length === 0 && (
        <p style={{ textAlign: 'center', color: '#888', marginTop: 40 }}>No packs yet. Check the store!</p>
      )}
    </div>
  );
}
```

**Commit:**

```bash
git add tma/frontend/src/pages/Packs.tsx
git commit -m "feat(tma): Pack opening page"
```

---

### Task 14: Daily claim + Battle pages

**Files:**
- Create: `tma/frontend/src/pages/Daily.tsx`
- Create: `tma/frontend/src/pages/Battle.tsx`

These follow the same pattern as Packs — call API, show result. See `Daily.tsx` for `claimDaily()` and `Battle.tsx` for `challengeBattle()` / `getBattle()` polling.

(Implement following same pattern as Task 13 — call API, handle error, show result cards.)

---

## Phase 6 — Build, Deploy, Test

---

### Task 15: Multi-stage Dockerfile + Railway deploy

**Files:**
- Modify: `tma/Dockerfile`

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY tma/frontend/package*.json ./
RUN npm ci
COPY tma/frontend/ .
RUN npm run build

# Stage 2: Python FastAPI with built frontend
FROM python:3.11-slim
WORKDIR /app

# Install deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    fastapi uvicorn[standard] "python-telegram-bot[webhooks]>=21.0"

# Copy entire repo
COPY . .

# Copy built frontend into tma/frontend/dist
COPY --from=frontend-builder /frontend/dist tma/frontend/dist

EXPOSE 8080
CMD ["uvicorn", "tma.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 1: Test build locally**

```bash
docker build -f tma/Dockerfile -t music-legends-tma .
docker run -e TELEGRAM_BOT_TOKEN=xxx -e DATABASE_URL=xxx -p 8080:8080 music-legends-tma
```

Expected: http://localhost:8080/ → React app; http://localhost:8080/api/me → 401 (no auth)

**Step 2: Deploy to Railway**

1. Railway dashboard → "New Service" → "GitHub Repo"
2. Root directory: `/` (not `/tma/`)
3. Dockerfile path: `tma/Dockerfile`
4. Set env vars: `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `TMA_URL`
5. Generate domain → set as `TMA_URL`

**Step 3: Register webhook with BotFather**

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR_RAILWAY_URL/webhook"
```

**Step 4: Test end-to-end in Telegram**

1. Open Telegram → message your bot → `/start`
2. Should see "Play Music Legends" button
3. Tap → Mini App opens → Home page shows your stats
4. Navigate to Collection, Packs, Daily

**Step 5: Commit + tag**

```bash
git add tma/Dockerfile
git commit -m "feat(tma): production Dockerfile + Railway deploy config"
git tag v2.0.0-tma-launch
```

---

## Out of Scope (Phase 2+)

- Telegram Stars payment integration (pack store purchases)
- Creator pack creation flow
- Battle pass / quests
- Trade system
- Cosmetics
- Discord ↔ Telegram account linking
- Push notifications for drops

---

## Quick Reference

| Command | Purpose |
|---|---|
| `uvicorn tma.api.main:app --reload --port 8001` | Run API locally |
| `cd tma/frontend && npm run dev` | Run frontend locally |
| `python -m pytest tests/test_bot_core.py --noconftest` | Run test suite |
| `git tag v2.0.0-tma-launch` | Tag TMA release |
