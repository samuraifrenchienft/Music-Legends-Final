# Music Legends — Telegram Mini App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Telegram Mini App that runs the full Music Legends card game — collection, pack opening with animations, share-link battles, and daily claim — sharing the existing Railway PostgreSQL database with the Discord bot.

**Architecture:** New `tma/` directory in existing repo. FastAPI backend imports `database.py`, `battle_engine.py`, and `config/cards.py` directly (zero duplication). React + Vite TMA frontend uses `@telegram-apps/sdk-react` for native Telegram controls. One new Railway service; Discord bot unchanged.

**Tech Stack:** Python FastAPI + python-telegram-bot 21+ (backend), React 18 + Vite + TypeScript + @telegram-apps/sdk-react (frontend), Railway PostgreSQL (shared).

**Design doc:** `docs/plans/2026-02-21-telegram-mini-app-design.md`
**Research notes:** `docs/research/2026-02-21-tma-research.md`

---

## Phase 1 — Database Layer

---

### Task 1: Schema migration — platform-agnostic identity + battle table

**Files:**
- Modify: `database.py` — add migrations in both `_init_postgresql()` and `init_database()`

**Step 1: Add columns to PostgreSQL migration block**

In `database.py`, find `_init_postgresql()`. Add after the existing ALTER TABLE block:

```python
# Platform-agnostic identity — TMA support
_tma_alters = [
    "ALTER TABLE users ADD COLUMN discord_id BIGINT",
    "ALTER TABLE users ADD COLUMN telegram_id BIGINT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
    "UPDATE users SET discord_id = user_id WHERE discord_id IS NULL",
]
for stmt in _tma_alters:
    try:
        cursor.execute(stmt)
        conn.commit()
    except Exception:
        conn.rollback()

# Pending TMA battles table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_tma_battles (
        battle_id       TEXT PRIMARY KEY,
        challenger_id   INTEGER NOT NULL,
        opponent_id     INTEGER,
        challenger_pack TEXT NOT NULL,
        opponent_pack   TEXT,
        wager_tier      TEXT DEFAULT 'casual',
        status          TEXT DEFAULT 'waiting',
        result_json     TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at      TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
    )
""")
conn.commit()
```

**Step 2: Mirror in SQLite `init_database()` block**

Find the SQLite ALTER TABLE guard block. Add:

```python
# TMA identity columns
tma_cols = [("discord_id", "INTEGER"), ("telegram_id", "INTEGER")]
for col, typ in tma_cols:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(users)")
        if col not in [r[1] for r in cursor.fetchall()]:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")

cursor.execute("UPDATE users SET discord_id = user_id WHERE discord_id IS NULL")

# Pending TMA battles (SQLite — no INTERVAL syntax)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_tma_battles (
        battle_id       TEXT PRIMARY KEY,
        challenger_id   INTEGER NOT NULL,
        opponent_id     INTEGER,
        challenger_pack TEXT NOT NULL,
        opponent_pack   TEXT,
        wager_tier      TEXT DEFAULT 'casual',
        status          TEXT DEFAULT 'waiting',
        result_json     TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at      TIMESTAMP
    )
""")
```

**Step 3: Run tests to confirm nothing broke**

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends
python -m pytest tests/test_bot_core.py -v --noconftest
```

Expected: 40 tests pass.

**Step 4: Commit**

```bash
git add database.py
git commit -m "feat(tma): add discord_id/telegram_id columns + pending_tma_battles table"
```

---

### Task 2: New DatabaseManager methods for TMA

**Files:**
- Modify: `database.py` — add 3 new methods near the bottom before `get_db()`
- Create: `tests/test_tma_db.py`

**Step 1: Write the failing tests first**

Create `tests/test_tma_db.py`:

```python
"""Tests for TMA-specific database methods."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from database import DatabaseManager

@pytest.fixture
def db(tmp_path):
    d = DatabaseManager(db_path=str(tmp_path / "test.db"))
    d.init_database()
    return d

def test_get_or_create_telegram_user_new(db):
    """New Telegram user gets created with synthetic user_id."""
    result = db.get_or_create_telegram_user(
        telegram_id=123456, telegram_username="testuser", first_name="Test"
    )
    assert result["telegram_id"] == 123456
    assert result["username"] == "testuser"
    assert result["is_new"] is True
    assert result["user_id"] == 9_000_000_000 + 123456

def test_get_or_create_telegram_user_existing(db):
    """Existing Telegram user is retrieved, not duplicated."""
    db.get_or_create_telegram_user(123456, "testuser")
    result = db.get_or_create_telegram_user(123456, "testuser_renamed")
    assert result["is_new"] is False

def test_generate_link_code(db):
    """Link code is 6 chars, stored, retrievable."""
    # First create a telegram user to link from
    user = db.get_or_create_telegram_user(111, "linker")
    code = db.generate_tma_link_code(user["user_id"])
    assert len(code) == 6
    assert code.isalnum()

def test_consume_link_code(db):
    """Consuming a valid code merges discord_id into telegram user's row."""
    # Create telegram user
    tg_user = db.get_or_create_telegram_user(222, "tguser")
    code = db.generate_tma_link_code(tg_user["user_id"])
    # Consume with a discord_id
    result = db.consume_tma_link_code(code, discord_id=9876543210)
    assert result["success"] is True
    assert result["user_id"] == tg_user["user_id"]

def test_consume_link_code_expired(db):
    """Expired codes fail gracefully."""
    result = db.consume_tma_link_code("XXXXXX", discord_id=999)
    assert result["success"] is False
```

**Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_tma_db.py -v --noconftest
```

Expected: FAIL — `get_or_create_telegram_user` not defined.

**Step 3: Add the three methods to `database.py`**

Add before `def get_db():` at the bottom of `database.py`:

```python
def get_or_create_telegram_user(self, telegram_id: int, telegram_username: str = "", first_name: str = "") -> Dict:
    """Find or create a user record for a Telegram Mini App user.
    Returns dict with user_id, username, telegram_id, is_new."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"user_id": row[0], "username": row[1],
                    "telegram_id": telegram_id, "is_new": False}

        # Synthetic user_id: 9B + telegram_id avoids Discord snowflake collisions
        synthetic_id = 9_000_000_000 + telegram_id
        display = telegram_username or first_name or f"tg_{telegram_id}"
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, telegram_id) VALUES (?, ?, ?)",
            (synthetic_id, display, telegram_id)
        )
        cursor.execute(
            "INSERT OR IGNORE INTO user_inventory (user_id, gold) VALUES (?, 500)",
            (synthetic_id,)
        )
        conn.commit()
        return {"user_id": synthetic_id, "username": display,
                "telegram_id": telegram_id, "is_new": True}

def generate_tma_link_code(self, user_id: int) -> str:
    """Generate a 6-char one-time code so user can link their Discord account.
    Code expires in 10 minutes. Stored in a simple JSON column on users table."""
    import secrets, json
    from datetime import datetime, timedelta
    code = secrets.token_hex(3).upper()  # 6 hex chars
    expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    payload = json.dumps({"code": code, "expires": expires, "user_id": user_id})
    with self._get_connection() as conn:
        cursor = conn.cursor()
        # Re-use an existing spare column or add one — store as JSON in a temp table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tma_link_codes (
                code TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        cursor.execute(
            "INSERT OR REPLACE INTO tma_link_codes (code, user_id, expires_at) VALUES (?, ?, ?)",
            (code, user_id, expires)
        )
        conn.commit()
    return code

def consume_tma_link_code(self, code: str, discord_id: int) -> Dict:
    """Validate and consume a TMA link code, writing discord_id to the TMA user's row.
    Returns {"success": True, "user_id": ...} or {"success": False, "error": ...}"""
    from datetime import datetime
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, expires_at FROM tma_link_codes WHERE code = ?",
            (code.upper(),)
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Invalid or already used code"}
        user_id, expires_at = row
        if datetime.utcnow().isoformat() > expires_at:
            cursor.execute("DELETE FROM tma_link_codes WHERE code = ?", (code,))
            conn.commit()
            return {"success": False, "error": "Code expired"}
        cursor.execute(
            "UPDATE users SET discord_id = ? WHERE user_id = ?",
            (discord_id, user_id)
        )
        cursor.execute("DELETE FROM tma_link_codes WHERE code = ?", (code,))
        conn.commit()
    return {"success": True, "user_id": user_id}
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_tma_db.py tests/test_bot_core.py -v --noconftest
```

Expected: All 45 tests pass (5 new + 40 existing).

**Step 5: Commit**

```bash
git add database.py tests/test_tma_db.py
git commit -m "feat(tma): get_or_create_telegram_user + link code methods, 5 new tests"
```

---

## Phase 2 — FastAPI Backend

---

### Task 3: FastAPI skeleton + initData auth

**Files:**
- Create: `tma/__init__.py`
- Create: `tma/api/__init__.py`
- Create: `tma/api/auth.py`
- Create: `tma/api/main.py`
- Create: `tma/api/routers/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p tma/api/routers tma/api/bot tma/frontend
touch tma/__init__.py tma/api/__init__.py tma/api/routers/__init__.py tma/api/bot/__init__.py
```

**Step 2: Write `tma/api/auth.py`**

```python
"""Telegram initData HMAC validation — FastAPI dependency.
Every API request must include: Authorization: tma <raw_init_data>
"""
import hmac
import hashlib
import json
import os
import urllib.parse
from fastapi import Header, HTTPException

_BOT_TOKEN: str = ""  # set at startup from env


def _get_secret_key() -> bytes:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", _BOT_TOKEN)
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
```

**Step 3: Write `tma/api/main.py`**

```python
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

# ── Routers (imported after app created to avoid circular issues) ──
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
```

**Step 4: Test the skeleton runs**

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends
pip install fastapi uvicorn[standard]
TELEGRAM_BOT_TOKEN=dummy uvicorn tma.api.main:app --reload --port 8001
```

Open http://localhost:8001/health → Expected: `{"status":"ok","service":"tma-api"}`

**Step 5: Commit**

```bash
git add tma/
git commit -m "feat(tma): FastAPI skeleton + initData auth dependency"
```

---

### Task 4: Users router — `/api/me` and `/api/link`

**Files:**
- Create: `tma/api/routers/users.py`
- Create: `tests/test_tma_users.py`

**Step 1: Write failing tests**

Create `tests/test_tma_users.py`:

```python
"""Tests for TMA users router."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    # Patch auth so we don't need real Telegram tokens
    with patch("tma.api.auth.validate_init_data") as mock_auth:
        mock_auth.return_value = {"id": 111, "username": "testplayer", "first_name": "Test"}
        from tma.api.main import app
        return TestClient(app)


def test_get_me_returns_user(client):
    resp = client.get("/api/me", headers={"Authorization": "tma fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "gold" in data
    assert data["username"] == "testplayer"


def test_get_me_401_without_auth(client):
    resp = client.get("/api/me")
    assert resp.status_code == 422  # FastAPI missing header


def test_link_generate(client):
    resp = client.post("/api/link/generate", headers={"Authorization": "tma fake"})
    assert resp.status_code == 200
    assert "code" in resp.json()
    assert len(resp.json()["code"]) == 6
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_tma_users.py -v --noconftest
```

Expected: ImportError or 404 — router not yet created.

**Step 3: Create `tma/api/routers/users.py`**

```python
"""Users router — identity, profile, account linking."""
from fastapi import APIRouter, Depends
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me")
def get_me(tg: dict = Depends(get_tg_user)):
    """Return current user profile + economy. Creates account on first call."""
    db = get_db()
    user = db.get_or_create_telegram_user(
        telegram_id=tg["id"],
        telegram_username=tg.get("username", ""),
        first_name=tg.get("first_name", ""),
    )
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
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_tma_users.py -v --noconftest
```

Expected: All 3 pass.

**Step 5: Commit**

```bash
git add tma/api/routers/users.py tests/test_tma_users.py
git commit -m "feat(tma): /api/me + /api/link/generate endpoints"
```

---

### Task 5: Cards router

**Files:**
- Create: `tma/api/routers/cards.py`

```python
"""Cards router — user collection."""
from fastapi import APIRouter, Depends, HTTPException
from tma.api.auth import get_tg_user
from database import get_db
from config.cards import compute_card_power, RARITY_EMOJI

router = APIRouter(prefix="/api/cards", tags=["cards"])

def _enrich(card: dict) -> dict:
    """Add computed power + rarity emoji to a card dict."""
    card["power"] = compute_card_power(card)
    card["rarity_emoji"] = RARITY_EMOJI.get((card.get("rarity") or "common").lower(), "⚪")
    return card


@router.get("")
def list_collection(tg: dict = Depends(get_tg_user)):
    """Return all cards the user owns, sorted by power descending."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    cards = db.get_user_collection(user["user_id"])
    cards = [_enrich(c) for c in cards]
    cards.sort(key=lambda c: c["power"], reverse=True)
    return {"cards": cards, "total": len(cards)}


@router.get("/{card_id}")
def get_card(card_id: str, tg: dict = Depends(get_tg_user)):
    """Return a single card from the user's collection."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    cards = db.get_user_collection(user["user_id"])
    card = next((c for c in cards if c.get("card_id") == card_id), None)
    if not card:
        raise HTTPException(404, "Card not found in your collection")
    return _enrich(card)
```

**Test + commit:**

```bash
git add tma/api/routers/cards.py
git commit -m "feat(tma): /api/cards collection endpoint"
```

---

### Task 6: Packs router

**Files:**
- Create: `tma/api/routers/packs.py`

```python
"""Packs router — view acquired packs + open them."""
from fastapi import APIRouter, Depends, HTTPException
from tma.api.auth import get_tg_user
from database import get_db
from config.cards import compute_card_power, RARITY_EMOJI

router = APIRouter(prefix="/api/packs", tags=["packs"])


@router.get("")
def list_packs(tg: dict = Depends(get_tg_user)):
    """Return all packs the user has acquired."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    packs = db.get_user_purchased_packs(user["user_id"])
    return {"packs": packs, "total": len(packs)}


@router.post("/{pack_id}/open")
def open_pack(pack_id: str, tg: dict = Depends(get_tg_user)):
    """Open a pack the user owns. Returns enriched cards."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    # Verify ownership before opening
    packs = db.get_user_purchased_packs(user["user_id"])
    owned = {str(p.get("pack_id")) for p in packs}
    if pack_id not in owned:
        raise HTTPException(403, "You don't own this pack")

    result = db.open_pack_for_drop(pack_id, user["user_id"])
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to open pack"))

    cards = result.get("cards", [])
    for c in cards:
        c["power"] = compute_card_power(c)
        c["rarity_emoji"] = RARITY_EMOJI.get((c.get("rarity") or "common").lower(), "⚪")

    return {"cards": cards, "pack_id": pack_id}


@router.get("/store")
def get_store(tg: dict = Depends(get_tg_user)):
    """Return live packs available in the store."""
    db = get_db()
    return {"packs": db.get_live_packs(limit=20)}
```

**Commit:**

```bash
git add tma/api/routers/packs.py
git commit -m "feat(tma): /api/packs list + open endpoints"
```

---

### Task 7: Economy router

**Files:**
- Create: `tma/api/routers/economy.py`

```python
"""Economy router — gold/XP/daily claim/leaderboard."""
from fastapi import APIRouter, Depends, HTTPException, Query
from tma.api.auth import get_tg_user
from database import get_db
from config.cards import compute_card_power

router = APIRouter(prefix="/api", tags=["economy"])


@router.get("/economy")
def get_economy(tg: dict = Depends(get_tg_user)):
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    return db.get_user_economy(user["user_id"]) or {}


@router.post("/economy/daily")
def claim_daily(tg: dict = Depends(get_tg_user)):
    """Claim daily reward. Returns cards + gold or error if already claimed today."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.claim_daily_reward(user["user_id"])
    if not result.get("success"):
        raise HTTPException(400, result.get("message", "Already claimed today"))
    for c in result.get("cards", []):
        c["power"] = compute_card_power(c)
    return result


@router.get("/leaderboard")
def get_leaderboard(
    metric: str = Query("wins", enum=["wins", "gold", "total_battles"]),
    limit: int = Query(10, ge=1, le=50),
    tg: dict = Depends(get_tg_user),
):
    db = get_db()
    return {"entries": db.get_leaderboard(metric=metric, limit=limit)}
```

**Commit:**

```bash
git add tma/api/routers/economy.py
git commit -m "feat(tma): /api/economy, /api/economy/daily, /api/leaderboard"
```

---

### Task 8: Battle router — challenge + accept + poll

**Files:**
- Create: `tma/api/routers/battle.py`
- Create: `tests/test_tma_battle.py`

**Step 1: Write failing tests**

Create `tests/test_tma_battle.py`:

```python
"""Tests for TMA battle router."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

TG_USER_A = {"id": 1001, "username": "playerA", "first_name": "A"}
TG_USER_B = {"id": 1002, "username": "playerB", "first_name": "B"}


@pytest.fixture
def client_a():
    with patch("tma.api.auth.validate_init_data", return_value=TG_USER_A):
        from tma.api.main import app
        return TestClient(app)


def test_challenge_missing_pack_returns_403(client_a):
    resp = client_a.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": 1002, "pack_id": "nonexistent", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    assert resp.status_code == 403


def test_get_nonexistent_battle_returns_404(client_a):
    resp = client_a.get("/api/battle/XXXXXX", headers={"Authorization": "tma fake"})
    assert resp.status_code == 404
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_tma_battle.py -v --noconftest
```

**Step 3: Create `tma/api/routers/battle.py`**

```python
"""Battle router — share-link PvP battles."""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from tma.api.auth import get_tg_user
from database import get_db
from config.cards import compute_card_power, compute_team_power
from battle_engine import BattleEngine
from discord_cards import ArtistCard

router = APIRouter(prefix="/api/battle", tags=["battle"])


class ChallengeRequest(BaseModel):
    opponent_telegram_id: int
    pack_id: str
    wager_tier: str = "casual"


class AcceptRequest(BaseModel):
    pack_id: str


def _make_battle_id() -> str:
    """6-character uppercase alphanumeric ID."""
    return secrets.token_hex(3).upper()


def _run_battle(db, challenger_id: int, opponent_id: int,
                c_pack: dict, o_pack: dict, wager_tier: str) -> dict:
    """Execute battle engine and distribute rewards. Returns result dict.
    CRITICAL: Rewards distributed before return so they are never orphaned."""
    c_cards = sorted(c_pack.get("cards", []), key=compute_card_power, reverse=True)
    o_cards = sorted(o_pack.get("cards", []), key=compute_card_power, reverse=True)

    if not c_cards or not o_cards:
        return {"error": "Empty pack", "winner": 0}

    c_champ, o_champ = c_cards[0], o_cards[0]
    c_power = compute_team_power(
        compute_card_power(c_champ), [compute_card_power(c) for c in c_cards[1:5]]
    )
    o_power = compute_team_power(
        compute_card_power(o_champ), [compute_card_power(c) for c in o_cards[1:5]]
    )

    result = BattleEngine.execute_battle(
        ArtistCard(name=c_champ.get("name", "?"), power=c_power,
                   rarity=c_champ.get("rarity", "common")),
        ArtistCard(name=o_champ.get("name", "?"), power=o_power,
                   rarity=o_champ.get("rarity", "common")),
        wager_tier,
        p1_override=c_power, p2_override=o_power,
    )

    p1, p2 = result["player1"], result["player2"]

    # Distribute BEFORE returning — gold must not be orphaned
    db.update_user_economy(challenger_id, gold_change=p1["gold_reward"])
    db.update_user_economy(opponent_id, gold_change=p2["gold_reward"])

    return {
        "winner":     result["winner"],
        "is_critical": result.get("is_critical", False),
        "challenger": {
            "name": c_champ.get("name"), "power": c_power,
            "gold_reward": p1["gold_reward"], "xp_reward": p1.get("xp_reward", 0),
            "image_url": c_champ.get("image_url"), "rarity": c_champ.get("rarity"),
        },
        "opponent": {
            "name": o_champ.get("name"), "power": o_power,
            "gold_reward": p2["gold_reward"], "xp_reward": p2.get("xp_reward", 0),
            "image_url": o_champ.get("image_url"), "rarity": o_champ.get("rarity"),
        },
    }


@router.post("/challenge")
async def create_challenge(body: ChallengeRequest, tg: dict = Depends(get_tg_user)):
    """Challenger picks pack and creates a pending battle. Returns sharable link."""
    db = get_db()
    challenger = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    # Verify pack ownership
    packs = db.get_user_purchased_packs(challenger["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(403, "You don't own that pack")

    battle_id = _make_battle_id()
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO pending_tma_battles
               (battle_id, challenger_id, opponent_id, challenger_pack,
                wager_tier, status, expires_at)
               VALUES (?, ?, ?, ?, ?, 'waiting', ?)""",
            (battle_id, challenger["user_id"], body.opponent_telegram_id,
             body.pack_id, body.wager_tier, expires)
        )
        conn.commit()

    import os
    tma_url = os.environ.get("TMA_URL", "https://t.me/MusicLegendsBot/app")
    link = f"{tma_url}?startapp=battle_{battle_id}"

    # Notify opponent via bot (best-effort, non-blocking)
    try:
        from tma.api.bot.handlers import notify_battle_challenge
        await notify_battle_challenge(
            opponent_telegram_id=body.opponent_telegram_id,
            challenger_name=tg.get("username") or tg.get("first_name", "Someone"),
            battle_id=battle_id,
            wager_tier=body.wager_tier,
            link=link,
        )
    except Exception as e:
        print(f"[BATTLE] Notification failed (non-critical): {e}")

    return {"battle_id": battle_id, "link": link, "status": "waiting"}


@router.post("/{battle_id}/accept")
async def accept_challenge(battle_id: str, body: AcceptRequest,
                           tg: dict = Depends(get_tg_user)):
    """Opponent selects pack and battle executes immediately."""
    db = get_db()
    opponent = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_tma_battles WHERE battle_id = ?",
                       (battle_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Battle not found")
        cols = [d[0] for d in cursor.description]
        battle = dict(zip(cols, row))

    if battle["status"] != "waiting":
        raise HTTPException(400, f"Battle is already {battle['status']}")
    if datetime.utcnow().isoformat() > (battle.get("expires_at") or "9999"):
        raise HTTPException(400, "Battle link has expired")

    # Verify pack ownership
    packs = db.get_user_purchased_packs(opponent["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(403, "You don't own that pack")

    # Get both packs
    c_packs = db.get_user_purchased_packs(battle["challenger_id"])
    c_pack = next((p for p in c_packs if str(p.get("pack_id")) == battle["challenger_pack"]), None)
    o_pack = next((p for p in packs if str(p.get("pack_id")) == body.pack_id), None)

    if not c_pack or not o_pack:
        raise HTTPException(400, "Could not resolve packs for battle")

    result = _run_battle(db, battle["challenger_id"], opponent["user_id"],
                         c_pack, o_pack, battle["wager_tier"])

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE pending_tma_battles
               SET status='complete', opponent_id=?, opponent_pack=?, result_json=?
               WHERE battle_id=?""",
            (opponent["user_id"], body.pack_id, json.dumps(result), battle_id)
        )
        conn.commit()

    # Notify challenger of result (best-effort)
    try:
        from tma.api.bot.handlers import notify_battle_result
        await notify_battle_result(
            challenger_id=battle["challenger_id"],
            result=result,
            opponent_name=tg.get("username") or tg.get("first_name", "Opponent"),
            battle_id=battle_id,
        )
    except Exception as e:
        print(f"[BATTLE] Result notification failed (non-critical): {e}")

    return {"battle_id": battle_id, "result": result}


@router.get("/{battle_id}")
def get_battle(battle_id: str, tg: dict = Depends(get_tg_user)):
    """Poll for battle status/result."""
    db = get_db()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, result_json FROM pending_tma_battles WHERE battle_id = ?",
            (battle_id,)
        )
        row = cursor.fetchone()
    if not row:
        raise HTTPException(404, "Battle not found")
    status, result_json = row
    return {
        "battle_id": battle_id,
        "status": status,
        "result": json.loads(result_json) if result_json else None,
    }
```

**Step 4: Run all tests**

```bash
python -m pytest tests/test_tma_battle.py tests/test_tma_db.py tests/test_bot_core.py -v --noconftest
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add tma/api/routers/battle.py tests/test_tma_battle.py
git commit -m "feat(tma): battle router — challenge, accept, poll with reward distribution"
```

---

## Phase 3 — Telegram Bot

---

### Task 9: Bot handlers + webhook route

**Files:**
- Create: `tma/api/bot/handlers.py`
- Modify: `tma/api/main.py` — add startup/webhook route

**Step 1: Create `tma/api/bot/handlers.py`**

```python
"""Telegram bot handlers.
Runs inside FastAPI process via webhook (no polling).
Handles: /start, /link, outbound battle notifications.
"""
import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

_app: Application | None = None
_bot: Bot | None = None


def _tma_url() -> str:
    return os.environ.get("TMA_URL", "https://t.me/MusicLegendsBot/app")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/start [battle_XXXXX] — Open TMA, optionally at a specific deep link."""
    args = ctx.args or []
    start_param = args[0] if args else ""
    url = f"{_tma_url()}?startapp={start_param}" if start_param else _tma_url()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎴 Play Music Legends", web_app=WebAppInfo(url=url))
    ]])
    await update.message.reply_text(
        "🎵 *Music Legends* — collect artist cards, battle friends, win gold!\n\n"
        "Tap below to open the game:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def cmd_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/link — Generate a code to link this Telegram account with Discord."""
    from database import get_db
    tg_id = update.effective_user.id
    tg_username = update.effective_user.username or ""
    db = get_db()
    user = db.get_or_create_telegram_user(tg_id, tg_username)
    code = db.generate_tma_link_code(user["user_id"])
    await update.message.reply_text(
        f"🔗 Your link code: `{code}`\n\n"
        f"Run this in Discord:\n`/link_telegram {code}`\n\n"
        f"_Code expires in 10 minutes._",
        parse_mode="Markdown",
    )


def build_application() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("link", cmd_link))
    return application


def setup_webhook_route(app) -> None:
    """Register /webhook POST route and startup/shutdown events on the FastAPI app."""
    from fastapi import Request

    @app.on_event("startup")
    async def _startup():
        global _app, _bot
        _app = build_application()
        await _app.initialize()
        _bot = _app.bot
        webhook_url = os.environ.get("TMA_URL", "")
        if webhook_url.startswith("https://"):
            try:
                await _bot.set_webhook(f"{webhook_url}/webhook")
                print(f"[BOT] Webhook set: {webhook_url}/webhook")
            except Exception as e:
                print(f"[BOT] Webhook setup failed: {e}")

    @app.on_event("shutdown")
    async def _shutdown():
        if _app:
            await _app.shutdown()

    @app.post("/webhook")
    async def _webhook(request: Request):
        data = await request.json()
        update = Update.de_json(data, _bot)
        await _app.process_update(update)
        return {"ok": True}


# ── Outbound notifications ────────────────────────────────────────

async def notify_battle_challenge(
    opponent_telegram_id: int, challenger_name: str,
    battle_id: str, wager_tier: str, link: str,
) -> None:
    """Send battle challenge notification to opponent."""
    if not _bot:
        return
    try:
        await _bot.send_message(
            chat_id=opponent_telegram_id,
            text=(
                f"⚔️ *{challenger_name}* challenged you to a battle!\n"
                f"Tier: *{wager_tier.upper()}*\n\n"
                f"[🎴 Accept the challenge]({link})"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[BOT] Challenge notify failed for {opponent_telegram_id}: {e}")


async def notify_battle_result(
    challenger_id: int, result: dict,
    opponent_name: str, battle_id: str,
) -> None:
    """Notify challenger of battle result. challenger_id is our user_id — look up telegram_id."""
    if not _bot:
        return
    from database import get_db
    db = get_db()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users WHERE user_id = ?", (challenger_id,))
        row = cursor.fetchone()
    if not row or not row[0]:
        return

    winner = result.get("winner", 0)
    c = result.get("challenger", {})
    gold = c.get("gold_reward", 0)
    outcome = "🏆 You *WON*" if winner == 1 else ("😔 You *lost*" if winner == 2 else "🤝 *Draw*")

    try:
        await _bot.send_message(
            chat_id=row[0],
            text=(
                f"⚔️ Battle result vs *{opponent_name}*!\n\n"
                f"{outcome}\n"
                f"Your card: *{c.get('name', '?')}* (power {c.get('power', 0)})\n"
                f"Gold earned: *+{gold}* 💰"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[BOT] Result notify failed: {e}")
```

**Step 2: Run health check**

```bash
TELEGRAM_BOT_TOKEN=dummy uvicorn tma.api.main:app --reload --port 8001
```

Expected: Server starts, `/health` returns 200, no import errors.

**Step 3: Run full test suite**

```bash
python -m pytest tests/test_tma_db.py tests/test_tma_users.py tests/test_tma_battle.py tests/test_bot_core.py -v --noconftest
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add tma/api/bot/handlers.py
git commit -m "feat(tma): Telegram bot — /start, /link, webhook, battle notifications"
```

---

## Phase 4 — React Frontend Foundation

---

### Task 10: Vite scaffold + TMA SDK setup

**Files:**
- Create: `tma/frontend/` (entire React project)

**Step 1: Scaffold from official TMA template**

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends/tma
npm create @telegram-apps/mini-app@latest frontend -- --template react-ts
cd frontend
npm install axios react-router-dom
```

**Step 2: Update `tma/frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: { outDir: 'dist' },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8001',
      '/webhook': 'http://localhost:8001',
    }
  }
})
```

**Step 3: Verify dev server runs**

```bash
cd tma/frontend && npm run dev
```

Expected: http://localhost:5173 opens with TMA template default screen.

**Step 4: Commit**

```bash
git add tma/frontend/
git commit -m "feat(tma): React+Vite TMA frontend scaffold"
```

---

### Task 11: TMA initialization + API client

**Files:**
- Create: `tma/frontend/src/api/client.ts`
- Modify: `tma/frontend/src/main.tsx` — TMA SDK init

**Step 1: Rewrite `tma/frontend/src/main.tsx`**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { init, expandViewport, mountViewport, bindViewportCssVars } from '@telegram-apps/sdk'
import App from './App'
import './index.css'

// Initialise TMA SDK
try {
  init()
  if (expandViewport.isAvailable())    expandViewport()
  if (mountViewport.isAvailable())     mountViewport()
  if (bindViewportCssVars.isAvailable()) bindViewportCssVars()
} catch {
  // Running in browser outside Telegram — dev mode, continue normally
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

**Step 2: Create `tma/frontend/src/api/client.ts`**

```typescript
import axios from 'axios'
import { retrieveLaunchParams } from '@telegram-apps/sdk'

// In production FastAPI serves both API and frontend on same origin.
// In dev, Vite proxy forwards /api to localhost:8001.
const api = axios.create({ baseURL: '' })

api.interceptors.request.use(config => {
  try {
    const { initDataRaw } = retrieveLaunchParams()
    if (initDataRaw) config.headers['Authorization'] = `tma ${initDataRaw}`
  } catch {
    // Outside Telegram — dev mode, requests will 401 without real initData
    if (import.meta.env.DEV) {
      config.headers['Authorization'] = `tma ${import.meta.env.VITE_DEV_INIT_DATA || 'dev'}`
    }
  }
  return config
})

export default api

// Typed endpoint helpers
export const getMe          = ()                         => api.get('/api/me')
export const getCards       = ()                         => api.get('/api/cards')
export const getCard        = (id: string)               => api.get(`/api/cards/${id}`)
export const getPacks       = ()                         => api.get('/api/packs')
export const openPack       = (id: string)               => api.post(`/api/packs/${id}/open`)
export const getEconomy     = ()                         => api.get('/api/economy')
export const claimDaily     = ()                         => api.post('/api/economy/daily')
export const getLeaderboard = (metric = 'wins')          => api.get(`/api/leaderboard?metric=${metric}`)
export const createChallenge= (body: object)             => api.post('/api/battle/challenge', body)
export const acceptBattle   = (id: string, body: object) => api.post(`/api/battle/${id}/accept`, body)
export const getBattle      = (id: string)               => api.get(`/api/battle/${id}`)
export const generateLink   = ()                         => api.post('/api/link/generate')
```

**Step 3: Commit**

```bash
git add tma/frontend/src/
git commit -m "feat(tma): TMA SDK init + typed API client with initData auth"
```

---

### Task 12: App.tsx routing + theme + NavBar with BackButton

**Files:**
- Modify: `tma/frontend/src/App.tsx`
- Create: `tma/frontend/src/components/NavBar.tsx`
- Modify: `tma/frontend/src/index.css`

**Step 1: Rewrite `App.tsx`**

```typescript
import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { useLaunchParams, backButton, mountThemeParamsSync, useSignal, themeParamsState } from '@telegram-apps/sdk-react'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Collection from './pages/Collection'
import Pack from './pages/Pack'
import Battle from './pages/Battle'
import Daily from './pages/Daily'

function Inner() {
  const location = useLocation()
  const navigate = useNavigate()
  const params = useLaunchParams()
  const theme = useSignal(themeParamsState)

  // Mount theme so Telegram colors flow into CSS vars
  useEffect(() => {
    if (mountThemeParamsSync.isAvailable()) mountThemeParamsSync()
  }, [])

  // Handle BackButton — show on all non-root pages
  useEffect(() => {
    const isRoot = location.pathname === '/'
    if (backButton.show.isAvailable() && backButton.hide.isAvailable()) {
      isRoot ? backButton.hide() : backButton.show()
    }
    if (backButton.onClick.isAvailable()) {
      const off = backButton.onClick(() => navigate(-1))
      return off
    }
  }, [location.pathname, navigate])

  // Handle deep link startParam — e.g. battle_X9K2QR
  useEffect(() => {
    const sp = params.tgWebAppStartParam || ''
    if (sp.startsWith('battle_')) {
      navigate(`/battle?id=${sp.replace('battle_', '')}`)
    }
  }, [])

  return (
    <div style={{
      minHeight: 'var(--tg-viewport-height, 100vh)',
      backgroundColor: theme?.bg_color || '#0D0B2E',
      color: theme?.text_color || '#ffffff',
      maxWidth: 480, margin: '0 auto',
    }}>
      <Routes>
        <Route path="/"           element={<Home />} />
        <Route path="/collection" element={<Collection />} />
        <Route path="/packs"      element={<Pack />} />
        <Route path="/battle"     element={<Battle />} />
        <Route path="/daily"      element={<Daily />} />
      </Routes>
      <NavBar />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Inner />
    </BrowserRouter>
  )
}
```

**Step 2: Create `tma/frontend/src/components/NavBar.tsx`**

```typescript
import { Link, useLocation } from 'react-router-dom'

const TABS = [
  { path: '/',           icon: '🏠', label: 'Home' },
  { path: '/collection', icon: '🃏', label: 'Cards' },
  { path: '/packs',      icon: '📦', label: 'Packs' },
  { path: '/battle',     icon: '⚔️',  label: 'Battle' },
  { path: '/daily',      icon: '🎁', label: 'Daily' },
]

export default function NavBar() {
  const { pathname } = useLocation()
  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
      width: '100%', maxWidth: 480, display: 'flex',
      backgroundColor: '#1a1740', borderTop: '1px solid #6B2EBE',
      paddingBottom: 'env(safe-area-inset-bottom)',
      zIndex: 100,
    }}>
      {TABS.map(tab => (
        <Link key={tab.path} to={tab.path} style={{
          flex: 1, textAlign: 'center', padding: '8px 0',
          color: pathname === tab.path ? '#F4A800' : '#8888aa',
          textDecoration: 'none', fontSize: 11,
        }}>
          <div style={{ fontSize: 22 }}>{tab.icon}</div>
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}
```

**Step 3: Commit**

```bash
git add tma/frontend/src/
git commit -m "feat(tma): App routing + theme + NavBar + BackButton integration"
```

---

## Phase 5 — Pages + Animations

---

### Task 13: Animated card component

**Files:**
- Create: `tma/frontend/src/components/AnimatedCard.tsx`
- Create: `tma/frontend/src/components/AnimatedCard.css`

**Step 1: Create `AnimatedCard.css`**

```css
/* 3D card flip */
.card-scene {
  perspective: 800px;
  width: 100%;
  aspect-ratio: 3/4;
}
.card-flip {
  width: 100%; height: 100%;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.7s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}
.card-flip.flipped { transform: rotateY(180deg); }

.card-face {
  position: absolute; width: 100%; height: 100%;
  backface-visibility: hidden;
  border-radius: 14px;
  overflow: hidden;
}
.card-back {
  background: linear-gradient(135deg, #1a1740 0%, #6B2EBE 50%, #1a1740 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 48px;
}
.card-front { transform: rotateY(180deg); }

/* Rarity glow animation */
.glow-common    { box-shadow: 0 0 0 2px #95A5A6; }
.glow-rare      { box-shadow: 0 0 16px 4px #4488FF; animation: pulse-rare 2s infinite; }
.glow-epic      { box-shadow: 0 0 20px 6px #6B2EBE; animation: pulse-epic 1.8s infinite; }
.glow-legendary { box-shadow: 0 0 28px 8px #F4A800; animation: pulse-legendary 1.5s infinite; }
.glow-mythic    { box-shadow: 0 0 36px 12px #E74C3C; animation: pulse-mythic 1.2s infinite; }

@keyframes pulse-rare      { 0%,100% { box-shadow: 0 0 16px 4px #4488FF } 50% { box-shadow: 0 0 24px 8px #4488FFAA } }
@keyframes pulse-epic      { 0%,100% { box-shadow: 0 0 20px 6px #6B2EBE } 50% { box-shadow: 0 0 30px 10px #6B2EBEAA } }
@keyframes pulse-legendary { 0%,100% { box-shadow: 0 0 28px 8px #F4A800 } 50% { box-shadow: 0 0 40px 14px #F4A800AA } }
@keyframes pulse-mythic    { 0%,100% { box-shadow: 0 0 36px 12px #E74C3C } 50% { box-shadow: 0 0 52px 18px #FF4E9A } }

/* Mythic overlay */
.mythic-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.85);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; animation: fadeIn 0.3s ease;
}
.mythic-spotlight {
  width: 260px; height: 360px;
  filter: drop-shadow(0 0 60px #E74C3C);
  animation: mythicSlam 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97);
}
@keyframes mythicSlam {
  0% { transform: scale(2) translateY(-80px); opacity: 0 }
  60% { transform: scale(0.95) translateY(4px) }
  100% { transform: scale(1) translateY(0); opacity: 1 }
}
@keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }

/* Screen shake */
@keyframes shake {
  0%,100% { transform: translate(0,0) rotate(0deg) }
  20% { transform: translate(-6px, 4px) rotate(-1deg) }
  40% { transform: translate(6px, -4px) rotate(1deg) }
  60% { transform: translate(-4px, 6px) rotate(-0.5deg) }
  80% { transform: translate(4px, -4px) rotate(0.5deg) }
}
.shake { animation: shake 0.4s ease; }
```

**Step 2: Create `AnimatedCard.tsx`**

```typescript
import { useState } from 'react'
import './AnimatedCard.css'

const RARITY_COLORS: Record<string, string> = {
  common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE',
  legendary: '#F4A800', mythic: '#E74C3C',
}

interface Props {
  card: any
  revealOnMount?: boolean   // true during pack opening
  delay?: number            // stagger delay in ms
  onClick?: () => void
}

export default function AnimatedCard({ card, revealOnMount = false, delay = 0, onClick }: Props) {
  const [flipped, setFlipped] = useState(revealOnMount ? false : true)
  const [revealed, setRevealed] = useState(!revealOnMount)
  const rarity = (card.rarity || 'common').toLowerCase()
  const isMythic = rarity === 'mythic'
  const power = card.power || 0

  const handleReveal = () => {
    if (flipped) { onClick?.(); return }
    setTimeout(() => {
      setFlipped(true)
      setRevealed(true)
    }, delay)
  }

  const pct = Math.round((power / 135) * 100)

  return (
    <>
      {isMythic && flipped && (
        <div className="mythic-overlay" onClick={() => {}}>
          <div className="mythic-spotlight">
            <div className={`card-face card-front glow-mythic`} style={{ position: 'relative', width: 260, height: 360, borderRadius: 14 }}>
              {card.image_url && <img src={card.image_url} alt={card.name} style={{ width: '100%', height: '75%', objectFit: 'cover' }} />}
              <div style={{ padding: '8px 12px', background: '#0D0B2E' }}>
                <div style={{ fontWeight: 'bold', color: '#FF4E9A' }}>{card.name}</div>
                <div style={{ fontSize: 12, color: '#E74C3C' }}>🔴 MYTHIC</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card-scene" onClick={handleReveal}>
        <div className={`card-flip ${flipped ? 'flipped' : ''}`}>
          {/* Back face — shown before reveal */}
          <div className="card-face card-back">🎵</div>

          {/* Front face — revealed card */}
          <div className={`card-face card-front glow-${rarity}`}>
            {card.image_url && (
              <img src={card.image_url} alt={card.name}
                style={{ width: '100%', height: '60%', objectFit: 'cover' }} />
            )}
            <div style={{ padding: '8px 10px', flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: '#fff' }}>{card.name}</div>
              {card.title && <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>{card.title}</div>}
              <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ flex: 1, height: 4, background: '#333', borderRadius: 2 }}>
                  <div style={{
                    width: revealed ? `${pct}%` : '0%',
                    height: '100%',
                    background: RARITY_COLORS[rarity],
                    borderRadius: 2,
                    transition: 'width 0.8s ease 0.3s',
                  }} />
                </div>
                <span style={{ fontSize: 11, color: RARITY_COLORS[rarity], fontWeight: 700 }}>{power}</span>
              </div>
              <div style={{ marginTop: 4, fontSize: 10, color: '#8888aa' }}>
                {card.rarity_emoji} {(rarity).charAt(0).toUpperCase() + rarity.slice(1)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
```

**Step 3: Commit**

```bash
git add tma/frontend/src/components/AnimatedCard.tsx tma/frontend/src/components/AnimatedCard.css
git commit -m "feat(tma): AnimatedCard with 3D flip, rarity glow, mythic overlay"
```

---

### Task 14: Home page with MainButton

**Files:**
- Create: `tma/frontend/src/pages/Home.tsx`

```typescript
import { useEffect, useState } from 'react'
import { useLaunchParams } from '@telegram-apps/sdk-react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton } from '@telegram-apps/sdk'
import { useNavigate } from 'react-router-dom'
import { getMe } from '../api/client'

export default function Home() {
  const [user, setUser] = useState<any>(null)
  const params = useLaunchParams()
  const navigate = useNavigate()

  useEffect(() => {
    getMe().then(r => setUser(r.data)).catch(console.error)
  }, [])

  // MainButton → "Open Packs"
  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    setMainButtonParams({ text: '📦 Open Packs', isEnabled: true, isVisible: true, backgroundColor: '#F4A800', textColor: '#000000' })
    const off = onMainButtonClick(() => navigate('/packs'))
    return () => { off(); unmountMainButton() }
  }, [navigate])

  if (!user) return (
    <div style={{ padding: 24, textAlign: 'center', paddingBottom: 80 }}>
      <div style={{ color: '#8888aa' }}>Loading...</div>
    </div>
  )

  const LOGO = 'https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeiehxk5zhdxidab4qtuxg6lblrasxcxb2bkj6a3ipyjue5f7pzo3qi'

  return (
    <div style={{ padding: '20px 16px', paddingBottom: 100 }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <img src={LOGO} alt="Music Legends" style={{ width: 72, height: 72, borderRadius: '50%', border: '2px solid #F4A800' }} />
        <h2 style={{ color: '#F4A800', margin: '10px 0 4px' }}>Music Legends</h2>
        <p style={{ color: '#8888aa', margin: 0, fontSize: 13 }}>
          Welcome back, {user.username}!{user.is_new ? ' 🎉 New player!' : ''}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
        {[
          { label: '💰 Gold',    value: user.gold?.toLocaleString() },
          { label: '⭐ XP',      value: user.xp?.toLocaleString() },
          { label: '⚔️ Battles', value: user.total_battles },
          { label: '🏆 Wins',    value: user.wins },
        ].map(s => (
          <div key={s.label} style={{
            background: '#1a1740', borderRadius: 12, padding: '14px 12px',
            textAlign: 'center', border: '1px solid #2a2760',
          }}>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{s.value ?? '—'}</div>
            <div style={{ color: '#8888aa', fontSize: 12, marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Commit:**

```bash
git add tma/frontend/src/pages/Home.tsx
git commit -m "feat(tma): Home page with stats grid + MainButton"
```

---

### Task 15: Collection page

**Files:**
- Create: `tma/frontend/src/pages/Collection.tsx`

```typescript
import { useEffect, useState, useCallback } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedback } from '@telegram-apps/sdk'
import { useNavigate } from 'react-router-dom'
import AnimatedCard from '../components/AnimatedCard'
import { getCards } from '../api/client'

export default function Collection() {
  const [cards, setCards] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)
  const navigate = useNavigate()

  const load = useCallback(() => {
    setLoading(true)
    getCards().then(r => { setCards(r.data.cards); setLoading(false) })
  }, [])

  useEffect(() => { load() }, [load])

  // MainButton → "⚔️ Battle" when a card is selected
  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    if (selected) {
      setMainButtonParams({ text: '⚔️ Battle with this card', isEnabled: true, isVisible: true, backgroundColor: '#E74C3C' })
      const off = onMainButtonClick(() => navigate('/battle'))
      return () => { off(); unmountMainButton() }
    } else {
      setMainButtonParams({ isVisible: false })
      return () => { unmountMainButton() }
    }
  }, [selected, navigate])

  if (loading) return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h3 style={{ color: '#F4A800' }}>🃏 My Collection</h3>
      {/* Skeleton loading */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {[...Array(6)].map((_, i) => (
          <div key={i} style={{ background: '#1a1740', borderRadius: 14, height: 200,
            animation: 'pulse 1.5s ease-in-out infinite', opacity: 0.6 }} />
        ))}
      </div>
    </div>
  )

  return (
    <div style={{ padding: '16px 16px 80px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <h3 style={{ color: '#F4A800', margin: 0 }}>🃏 My Collection ({cards.length})</h3>
        <button onClick={load} style={{ background: 'none', border: 'none', color: '#8888aa', fontSize: 18, cursor: 'pointer' }}>↻</button>
      </div>

      {cards.length === 0 && (
        <p style={{ textAlign: 'center', color: '#888', marginTop: 40 }}>
          No cards yet! Claim your daily or open a pack.
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {cards.map(card => (
          <AnimatedCard
            key={card.card_id}
            card={card}
            onClick={() => {
              hapticFeedback.selectionChanged?.()
              setSelected(card.card_id === selected ? null : card.card_id)
            }}
          />
        ))}
      </div>
    </div>
  )
}
```

**Commit:**

```bash
git add tma/frontend/src/pages/Collection.tsx
git commit -m "feat(tma): Collection page with animated cards + skeleton loading"
```

---

### Task 16: Pack opening page with full animation sequence

**Files:**
- Create: `tma/frontend/src/pages/Pack.tsx`

```typescript
import { useEffect, useState } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedback, showPopup } from '@telegram-apps/sdk'
import AnimatedCard from '../components/AnimatedCard'
import { getPacks, openPack } from '../api/client'

type Phase = 'list' | 'revealing' | 'results'

export default function Pack() {
  const [packs, setPacks] = useState<any[]>([])
  const [phase, setPhase] = useState<Phase>('list')
  const [pendingPack, setPendingPack] = useState<any>(null)
  const [revealedCards, setRevealedCards] = useState<any[]>([])
  const [revealIndex, setRevealIndex] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPacks().then(r => { setPacks(r.data.packs); setLoading(false) })
  }, [])

  const handleOpenPack = async (pack: any) => {
    // Native Telegram confirmation dialog
    if (showPopup.isAvailable()) {
      const btn = await showPopup({
        title: `Open ${pack.pack_name}?`,
        message: `This will open your ${pack.pack_tier?.toUpperCase() || ''} pack.`,
        buttons: [
          { id: 'open', type: 'ok', text: 'Open It!' },
          { id: 'cancel', type: 'cancel' },
        ],
      })
      if (btn !== 'open') return
    }

    setPendingPack(pack)
    setPhase('revealing')
    setRevealedCards([])
    setRevealIndex(0)

    try {
      const r = await openPack(pack.pack_id)
      setRevealedCards(r.data.cards)
    } catch (e: any) {
      setPhase('list')
      alert(e.response?.data?.detail || 'Failed to open pack')
    }
  }

  // Staggered card reveal — one every 0.8s
  useEffect(() => {
    if (phase !== 'revealing' || revealedCards.length === 0) return
    if (revealIndex >= revealedCards.length) {
      setTimeout(() => setPhase('results'), 600)
      return
    }
    const t = setTimeout(() => {
      hapticFeedback.notificationOccurred?.(
        (revealedCards[revealIndex]?.rarity || 'common') === 'mythic' ? 'success' : 'warning'
      )
      setRevealIndex(i => i + 1)
    }, 800)
    return () => clearTimeout(t)
  }, [revealIndex, revealedCards, phase])

  // MainButton on results screen → "Back to Packs"
  useEffect(() => {
    if (phase !== 'results') return
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    hapticFeedback.notificationOccurred?.('success')
    setMainButtonParams({ text: '✅ Done', isEnabled: true, isVisible: true, backgroundColor: '#2ECC71' })
    const off = onMainButtonClick(() => {
      getPacks().then(r => setPacks(r.data.packs))
      setPhase('list')
    })
    return () => { off(); unmountMainButton() }
  }, [phase])

  if (loading) return <div style={{ padding: 16, paddingBottom: 80, color: '#8888aa' }}>Loading packs...</div>

  // PACK LIST
  if (phase === 'list') return (
    <div style={{ padding: '16px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 14 }}>📦 My Packs ({packs.length})</h3>
      {packs.length === 0 && (
        <p style={{ textAlign: 'center', color: '#888', marginTop: 40 }}>
          No packs yet. Claim your daily reward to get started!
        </p>
      )}
      {packs.map(pack => (
        <div key={pack.pack_id} style={{
          background: '#1a1740', borderRadius: 12, padding: 14, marginBottom: 10,
          border: '1px solid #2a2760',
        }}>
          <div style={{ fontWeight: 700 }}>{pack.pack_name}</div>
          <div style={{ color: '#8888aa', fontSize: 12, marginTop: 2 }}>
            {pack.pack_tier?.toUpperCase()} • {(pack.cards || []).length} cards
          </div>
          <button onClick={() => handleOpenPack(pack)} style={{
            marginTop: 10, width: '100%', padding: '10px 0',
            background: '#6B2EBE', color: '#fff', border: 'none',
            borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: 'pointer',
          }}>
            🎴 Open Pack
          </button>
        </div>
      ))}
    </div>
  )

  // REVEALING — show cards one by one face down then flip
  if (phase === 'revealing') return (
    <div style={{ padding: '16px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', textAlign: 'center' }}>Opening {pendingPack?.pack_name}...</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 16 }}>
        {revealedCards.slice(0, revealIndex).map((card, i) => (
          <AnimatedCard key={i} card={card} revealOnMount delay={i * 100} />
        ))}
      </div>
    </div>
  )

  // RESULTS — all cards revealed
  return (
    <div style={{ padding: '16px 16px 100px' }}>
      <h3 style={{ color: '#F4A800', textAlign: 'center', marginBottom: 16 }}>🎉 Pack Opened!</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {revealedCards.map((card, i) => (
          <AnimatedCard key={i} card={card} />
        ))}
      </div>
    </div>
  )
}
```

**Commit:**

```bash
git add tma/frontend/src/pages/Pack.tsx
git commit -m "feat(tma): Pack opening page with staggered card flip animation + haptics"
```

---

### Task 17: Battle page — challenge + accept flow

**Files:**
- Create: `tma/frontend/src/pages/Battle.tsx`

```typescript
import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedback, openTelegramLink, showPopup } from '@telegram-apps/sdk'
import { getPacks, createChallenge, acceptBattle, getBattle } from '../api/client'

type Phase = 'select-pack' | 'challenge-sent' | 'accept' | 'result'

export default function Battle() {
  const [searchParams] = useSearchParams()
  const battleIdParam = searchParams.get('id')
  const [phase, setPhase] = useState<Phase>(battleIdParam ? 'accept' : 'select-pack')
  const [packs, setPacks] = useState<any[]>([])
  const [selectedPackId, setSelectedPackId] = useState<string>('')
  const [battleId, setBattleId] = useState(battleIdParam || '')
  const [battleLink, setBattleLink] = useState('')
  const [result, setResult] = useState<any>(null)
  const [polling, setPolling] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval>>()

  useEffect(() => {
    getPacks().then(r => setPacks(r.data.packs))
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleChallenge = async () => {
    if (!selectedPackId) return
    try {
      const r = await createChallenge({ pack_id: selectedPackId, opponent_telegram_id: 0, wager_tier: 'casual' })
      setBattleId(r.data.battle_id)
      setBattleLink(r.data.link)
      setPhase('challenge-sent')
      hapticFeedback.notificationOccurred?.('success')
      // Start polling for result
      pollRef.current = setInterval(async () => {
        const poll = await getBattle(r.data.battle_id)
        if (poll.data.status === 'complete') {
          clearInterval(pollRef.current)
          setResult(poll.data.result)
          setPhase('result')
          hapticFeedback.notificationOccurred?.(poll.data.result?.winner === 1 ? 'success' : 'error')
        }
      }, 3000)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to create challenge')
    }
  }

  const handleAccept = async () => {
    if (!selectedPackId || !battleId) return
    try {
      const r = await acceptBattle(battleId, { pack_id: selectedPackId })
      setResult(r.data.result)
      setPhase('result')
      hapticFeedback.notificationOccurred?.(r.data.result?.winner === 2 ? 'success' : 'error')
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to accept battle')
    }
  }

  // MainButton varies by phase
  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    if (phase === 'select-pack') {
      setMainButtonParams({ text: selectedPackId ? '⚔️ Create Challenge' : 'Select a Pack First', isEnabled: !!selectedPackId, isVisible: true, backgroundColor: '#E74C3C' })
      const off = onMainButtonClick(handleChallenge)
      return () => { off(); unmountMainButton() }
    }
    if (phase === 'accept') {
      setMainButtonParams({ text: selectedPackId ? '⚔️ Accept Battle!' : 'Select Your Pack', isEnabled: !!selectedPackId, isVisible: true, backgroundColor: '#E74C3C' })
      const off = onMainButtonClick(handleAccept)
      return () => { off(); unmountMainButton() }
    }
    if (phase === 'challenge-sent') {
      setMainButtonParams({ text: '📤 Share Challenge Link', isEnabled: true, isVisible: true, backgroundColor: '#6B2EBE' })
      const off = onMainButtonClick(() => openTelegramLink.ifAvailable?.(battleLink))
      return () => { off(); unmountMainButton() }
    }
    unmountMainButton()
  }, [phase, selectedPackId, battleLink])

  const RARITY_COLORS: Record<string, string> = {
    common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE', legendary: '#F4A800', mythic: '#E74C3C',
  }

  if (phase === 'result' && result) {
    const c = result.challenger, o = result.opponent
    const winner = result.winner
    const [shaking, setShaking] = useState(result.is_critical)
    return (
      <div className={shaking ? 'shake' : ''} style={{ padding: '20px 16px 80px', textAlign: 'center' }}>
        <h3 style={{ color: '#F4A800', fontSize: 22 }}>
          {winner === 1 ? '🏆 You Won!' : winner === 2 ? '😔 You Lost' : '🤝 Draw!'}
        </h3>
        {result.is_critical && <p style={{ color: '#FF4E9A', fontWeight: 700 }}>⚡ CRITICAL HIT!</p>}

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', margin: '20px 0' }}>
          {[c, o].map((player, i) => (
            <div key={i} style={{
              flex: 1, background: '#1a1740', borderRadius: 12, padding: 12,
              border: `2px solid ${RARITY_COLORS[player.rarity || 'common']}`,
              opacity: (i === 0 ? winner !== 2 : winner !== 1) ? 1 : 0.5,
            }}>
              {player.image_url && <img src={player.image_url} alt={player.name} style={{ width: '100%', borderRadius: 8, aspectRatio: '16/9', objectFit: 'cover' }} />}
              <div style={{ fontWeight: 700, marginTop: 6, fontSize: 12 }}>{player.name}</div>
              <div style={{ color: RARITY_COLORS[player.rarity || 'common'], fontSize: 18, fontWeight: 700 }}>{player.power}</div>
              <div style={{ color: '#2ECC71', fontSize: 12 }}>+{player.gold_reward} 💰</div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '16px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>
        {phase === 'accept' ? '⚔️ Battle Challenge!' : '⚔️ Battle'}
      </h3>
      {phase === 'accept' && (
        <p style={{ color: '#F4A800', fontSize: 13, marginBottom: 12 }}>
          Someone challenged you! Pick your best pack.
        </p>
      )}
      {phase === 'challenge-sent' && (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <div style={{ fontSize: 40 }}>✅</div>
          <p style={{ color: '#2ECC71', marginTop: 8 }}>Challenge created!</p>
          <p style={{ color: '#8888aa', fontSize: 12 }}>Share the link with your opponent. Waiting for them to accept...</p>
          <div style={{ marginTop: 12, padding: '8px 12px', background: '#1a1740', borderRadius: 8, fontSize: 12, color: '#F4A800', wordBreak: 'break-all' }}>
            {battleLink}
          </div>
        </div>
      )}
      {(phase === 'select-pack' || phase === 'accept') && (
        <>
          <p style={{ color: '#8888aa', fontSize: 13, marginBottom: 14 }}>Choose your pack:</p>
          {packs.map(pack => (
            <div key={pack.pack_id} onClick={() => setSelectedPackId(pack.pack_id)} style={{
              background: selectedPackId === pack.pack_id ? '#2a1760' : '#1a1740',
              border: `2px solid ${selectedPackId === pack.pack_id ? '#F4A800' : '#2a2760'}`,
              borderRadius: 10, padding: 12, marginBottom: 8, cursor: 'pointer',
            }}>
              <div style={{ fontWeight: 700 }}>{pack.pack_name}</div>
              <div style={{ fontSize: 12, color: '#8888aa' }}>
                {pack.pack_tier?.toUpperCase()} • {(pack.cards || []).length} cards
              </div>
            </div>
          ))}
          {packs.length === 0 && (
            <p style={{ color: '#888', textAlign: 'center', marginTop: 40 }}>
              You need packs to battle! Claim your daily reward first.
            </p>
          )}
        </>
      )}
    </div>
  )
}
```

**Commit:**

```bash
git add tma/frontend/src/pages/Battle.tsx
git commit -m "feat(tma): Battle page — challenge flow, startParam accept, result screen with shake"
```

---

### Task 18: Daily claim page with countdown

**Files:**
- Create: `tma/frontend/src/pages/Daily.tsx`

```typescript
import { useEffect, useState, useCallback } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedback } from '@telegram-apps/sdk'
import AnimatedCard from '../components/AnimatedCard'
import { getEconomy, claimDaily } from '../api/client'

export default function Daily() {
  const [economy, setEconomy] = useState<any>(null)
  const [claiming, setClaiming] = useState(false)
  const [claimed, setClaimed] = useState(false)
  const [cards, setCards] = useState<any[]>([])
  const [timeLeft, setTimeLeft] = useState('')
  const [canClaim, setCanClaim] = useState(false)

  const loadEconomy = useCallback(() => {
    getEconomy().then(r => {
      setEconomy(r.data)
      const last = r.data.last_daily_claim
      if (!last) { setCanClaim(true); return }
      const next = new Date(last)
      next.setHours(next.getHours() + 24)
      const diff = next.getTime() - Date.now()
      setCanClaim(diff <= 0)
    })
  }, [])

  useEffect(() => { loadEconomy() }, [loadEconomy])

  // Live countdown
  useEffect(() => {
    const tick = () => {
      if (!economy?.last_daily_claim) return
      const next = new Date(economy.last_daily_claim)
      next.setHours(next.getHours() + 24)
      const diff = next.getTime() - Date.now()
      if (diff <= 0) { setCanClaim(true); setTimeLeft(''); return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${h}h ${m}m ${s}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [economy])

  const handleClaim = async () => {
    setClaiming(true)
    try {
      const r = await claimDaily()
      setCards(r.data.cards || [])
      setClaimed(true)
      setCanClaim(false)
      hapticFeedback.notificationOccurred?.('success')
      loadEconomy()
    } catch (e: any) {
      hapticFeedback.notificationOccurred?.('error')
      alert(e.response?.data?.detail || 'Already claimed today')
    } finally {
      setClaiming(false)
    }
  }

  // MainButton
  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    if (canClaim && !claimed) {
      setMainButtonParams({ text: '🎁 Claim Daily Reward', isEnabled: !claiming, isVisible: true, backgroundColor: '#2ECC71', textColor: '#000' })
      const off = onMainButtonClick(handleClaim)
      return () => { off(); unmountMainButton() }
    }
    setMainButtonParams({ isVisible: false })
    return () => { unmountMainButton() }
  }, [canClaim, claimed, claiming])

  return (
    <div style={{ padding: '20px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>🎁 Daily Reward</h3>

      {/* Streak counter */}
      {economy && (
        <div style={{
          background: '#1a1740', borderRadius: 12, padding: '12px 16px',
          marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>
              {'🔥'.repeat(Math.min(economy.daily_streak || 0, 7))} {economy.daily_streak || 0} day streak
            </div>
            <div style={{ color: '#8888aa', fontSize: 12 }}>
              💰 {economy.gold?.toLocaleString()} gold
            </div>
          </div>
          <div style={{ fontSize: 32 }}>{economy.daily_streak >= 7 ? '🔥' : '📅'}</div>
        </div>
      )}

      {/* Countdown / claim status */}
      {!canClaim && !claimed && timeLeft && (
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          <div style={{ color: '#8888aa', fontSize: 14 }}>Next reward in</div>
          <div style={{ color: '#F4A800', fontSize: 32, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
            {timeLeft}
          </div>
        </div>
      )}

      {/* Results after claim */}
      {claimed && cards.length > 0 && (
        <>
          <p style={{ color: '#2ECC71', textAlign: 'center', marginBottom: 12 }}>
            ✅ Claimed! Here are your cards:
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {cards.map((card, i) => (
              <AnimatedCard key={i} card={card} revealOnMount delay={i * 200} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

**Commit:**

```bash
git add tma/frontend/src/pages/Daily.tsx
git commit -m "feat(tma): Daily page with live countdown + claim animation + streak display"
```

---

## Phase 6 — Deployment

---

### Task 19: Multi-stage Dockerfile

**Files:**
- Create: `tma/Dockerfile`

```dockerfile
# ── Stage 1: Build React frontend ────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

COPY tma/frontend/package*.json ./
RUN npm ci --prefer-offline

COPY tma/frontend/ .
RUN npm run build

# ── Stage 2: Python FastAPI with built frontend ───────────────────
FROM python:3.11-slim
WORKDIR /app

# System deps (for psycopg2)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Python deps — base requirements + TMA extras
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
    fastapi>=0.110.0 \
    "uvicorn[standard]>=0.29.0" \
    "python-telegram-bot[webhooks]>=21.0"

# Copy entire repo (needed for database.py, config/, battle_engine.py)
COPY . .

# Copy built React app from Stage 1
COPY --from=frontend-builder /frontend/dist tma/frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "tma.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 1: Test Docker build locally**

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends
docker build -f tma/Dockerfile -t music-legends-tma .
docker run -e TELEGRAM_BOT_TOKEN=dummy -e DATABASE_URL=sqlite:///test.db -p 8080:8080 music-legends-tma
```

Expected: http://localhost:8080/health → `{"status":"ok"}` — and the React app at http://localhost:8080/

**Step 2: Commit**

```bash
git add tma/Dockerfile
git commit -m "feat(tma): multi-stage Dockerfile — npm build + FastAPI serve"
```

---

### Task 20: Railway service setup (human steps)

**This task requires manual actions in Railway dashboard. No code changes.**

**Step 1: Register bot with @BotFather in Telegram**

1. Message `@BotFather` → `/newbot`
2. Name: `Music Legends`
3. Username: choose an available `@...Bot`
4. Copy the token — this is `TELEGRAM_BOT_TOKEN`
5. `/newapp` → name it, set the URL to your Railway TMA service domain (configure after deploy)

**Step 2: Create Railway service**

1. Railway dashboard → New Service → GitHub Repo → Music-Legends
2. Set root directory: `/` (not `/tma/`)
3. Set Dockerfile path: `tma/Dockerfile`
4. Set env vars:

```
TELEGRAM_BOT_TOKEN=<from BotFather>
DATABASE_URL=<same value as Discord bot service>
TMA_URL=https://<your-railway-domain>.up.railway.app
PORT=8080
```

5. Deploy

**Step 3: Set webhook**

After first successful deploy:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-domain>/webhook"
```

Expected response: `{"ok":true,"description":"Webhook was set"}`

**Step 4: Update BotFather Mini App URL**

`@BotFather` → `/myapps` → select your app → Edit Web App URL → paste Railway domain.

**Step 5: End-to-end test**

1. Telegram → message your bot → `/start`
2. Should see "Play Music Legends" button
3. Tap → TMA opens full-screen → Home page loads your stats
4. Navigate through all 5 tabs — no blank screens
5. Open a pack → card flip animations play
6. Daily page → countdown shows OR claim works
7. Battle tab → pick pack → create challenge → link generated → share to yourself → accept → result screen

---

## Run All Tests Before Final Commit

```bash
cd C:/Users/AbuBa/Desktop/Music-Legends
python -m pytest tests/test_bot_core.py tests/test_tma_db.py tests/test_tma_users.py tests/test_tma_battle.py -v --noconftest
```

Expected: All tests pass.

```bash
git tag v2.0.0-tma-launch
git push origin main --tags
```

---

## Quick Reference

| Command | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN=dummy uvicorn tma.api.main:app --reload --port 8001` | Run API locally |
| `cd tma/frontend && npm run dev` | Run TMA frontend locally (proxies to :8001) |
| `python -m pytest tests/test_tma_*.py tests/test_bot_core.py --noconftest` | Run all tests |
| `docker build -f tma/Dockerfile -t ml-tma . && docker run -p 8080:8080 ml-tma` | Test production build |

## Deferred (Phase 2)

- Telegram Stars pack purchases (`sendInvoice` with `currency: "XTR"`)
- Live WebSocket battles
- Telegram channel drops (`@MusicLegendsDrops`)
- Discord `/link_telegram <code>` command (mirrors `consume_tma_link_code`)
- Creator pack creation in TMA
