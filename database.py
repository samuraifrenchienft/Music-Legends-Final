"""Database access helpers used by TMA routers."""

from __future__ import annotations

import json
import os
import random
import sqlite3
import string
import hashlib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional


class _PgConnectionWrapper:
    """Minimal wrapper to keep legacy imports working."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()
        return False


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None, test_database_url: Optional[str] = None, **_: object):
        if test_database_url and test_database_url.startswith("sqlite:///"):
            raw = test_database_url.replace("sqlite:///", "")
            self._db_path = ":memory:" if raw == ":memory:" else raw
        else:
            if db_path:
                self._db_path = db_path
            else:
                self._db_path = os.environ.get("DB_PATH", "music_legends.db")
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    telegram_id INTEGER UNIQUE,
                    last_active TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    total_battles INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_claims (
                    user_id INTEGER PRIMARY KEY,
                    last_claim_date TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS tma_link_codes (
                    user_id INTEGER PRIMARY KEY,
                    code TEXT UNIQUE,
                    expires_at TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS creator_packs (
                    pack_id TEXT PRIMARY KEY,
                    pack_name TEXT,
                    pack_tier TEXT DEFAULT 'community',
                    status TEXT DEFAULT 'LIVE',
                    cards_data TEXT DEFAULT '[]'
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS pack_purchases (
                    user_id INTEGER,
                    pack_id TEXT,
                    purchased_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_tma_battles (
                    battle_id TEXT PRIMARY KEY,
                    challenger_id INTEGER NOT NULL,
                    opponent_id INTEGER NOT NULL,
                    challenger_pack TEXT NOT NULL,
                    opponent_pack TEXT,
                    wager_tier TEXT DEFAULT 'casual',
                    status TEXT DEFAULT 'waiting',
                    expires_at TEXT,
                    result_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    waiting_pair_key TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS api_idempotency (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    status_code INTEGER,
                    response_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
                """
            )
            self._ensure_column(conn, "users", "telegram_id", "INTEGER")
            self._ensure_column(conn, "users", "last_active", "TEXT")
            self._ensure_column(conn, "users", "total_battles", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "wins", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "users", "losses", "INTEGER DEFAULT 0")

            self._ensure_column(conn, "user_inventory", "xp", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "user_inventory", "level", "INTEGER DEFAULT 1")

            self._ensure_column(conn, "creator_packs", "pack_name", "TEXT")
            self._ensure_column(conn, "creator_packs", "pack_tier", "TEXT DEFAULT 'community'")
            self._ensure_column(conn, "creator_packs", "status", "TEXT DEFAULT 'LIVE'")
            self._ensure_column(conn, "creator_packs", "cards_data", "TEXT DEFAULT '[]'")
            self._ensure_column(conn, "pack_purchases", "purchased_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

            self._ensure_column(conn, "pending_tma_battles", "battle_id", "TEXT")
            self._ensure_column(conn, "pending_tma_battles", "challenger_id", "INTEGER")
            self._ensure_column(conn, "pending_tma_battles", "opponent_id", "INTEGER")
            self._ensure_column(conn, "pending_tma_battles", "challenger_pack", "TEXT")
            self._ensure_column(conn, "pending_tma_battles", "opponent_pack", "TEXT")
            self._ensure_column(conn, "pending_tma_battles", "wager_tier", "TEXT DEFAULT 'casual'")
            self._ensure_column(conn, "pending_tma_battles", "status", "TEXT DEFAULT 'waiting'")
            self._ensure_column(conn, "pending_tma_battles", "expires_at", "TEXT")
            self._ensure_column(conn, "pending_tma_battles", "result_json", "TEXT")
            self._ensure_column(conn, "pending_tma_battles", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
            self._ensure_column(conn, "pending_tma_battles", "waiting_pair_key", "TEXT")
            self._ensure_column(conn, "api_idempotency", "status_code", "INTEGER")
            self._ensure_column(conn, "api_idempotency", "response_json", "TEXT")
            self._ensure_column(conn, "api_idempotency", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
            self._ensure_column(conn, "api_idempotency", "updated_at", "TEXT")

            # Ensure legacy waiting rows have a stable pair key before creating uniqueness.
            self._normalize_waiting_pair_uniqueness(conn)
            self._ensure_indexes(conn)
            conn.commit()

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str):
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in c.fetchall()}
        if column not in existing:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def _ensure_indexes(self, conn: sqlite3.Connection):
        c = conn.cursor()
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_tma_waiting_pair_key "
            "ON pending_tma_battles(waiting_pair_key)"
        )
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_api_idempotency_user_action_key "
            "ON api_idempotency(user_id, action, idempotency_key)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_tma_status_expires "
            "ON pending_tma_battles(status, expires_at)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_tma_challenger_status "
            "ON pending_tma_battles(challenger_id, status)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_tma_opponent_status "
            "ON pending_tma_battles(opponent_id, status)"
        )

    def _normalize_waiting_pair_uniqueness(self, conn: sqlite3.Connection):
        c = conn.cursor()
        # Keep newest waiting row per pair and expire older duplicates.
        c.execute(
            """
            SELECT challenger_id, opponent_id
            FROM pending_tma_battles
            WHERE status='waiting'
            GROUP BY challenger_id, opponent_id
            HAVING COUNT(*) > 1
            """
        )
        duplicate_pairs = c.fetchall()
        for pair in duplicate_pairs:
            challenger_id = pair["challenger_id"]
            opponent_id = pair["opponent_id"]
            c.execute(
                """
                SELECT battle_id
                FROM pending_tma_battles
                WHERE challenger_id=? AND opponent_id=? AND status='waiting'
                ORDER BY COALESCE(created_at, expires_at) DESC, rowid DESC
                """,
                (challenger_id, opponent_id),
            )
            rows = c.fetchall()
            keep_battle_id = rows[0]["battle_id"] if rows else None
            for row in rows[1:]:
                c.execute(
                    "UPDATE pending_tma_battles "
                    "SET status='expired', waiting_pair_key=NULL "
                    "WHERE battle_id=?",
                    (row["battle_id"],),
                )
            if keep_battle_id:
                c.execute(
                    "UPDATE pending_tma_battles "
                    "SET waiting_pair_key=? "
                    "WHERE battle_id=?",
                    (f"{challenger_id}:{opponent_id}", keep_battle_id),
                )

        c.execute(
            """
            UPDATE pending_tma_battles
            SET waiting_pair_key = CAST(challenger_id AS TEXT) || ':' || CAST(opponent_id AS TEXT)
            WHERE status='waiting' AND (waiting_pair_key IS NULL OR waiting_pair_key='')
            """
        )
        c.execute(
            "UPDATE pending_tma_battles "
            "SET waiting_pair_key=NULL "
            "WHERE status!='waiting' AND waiting_pair_key IS NOT NULL"
        )

    def get_or_create_telegram_user(self, telegram_id: int, telegram_username: str = "", first_name: str = ""):
        now = datetime.utcnow().isoformat()
        username = telegram_username or first_name or f"tg_{telegram_id}"
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, username FROM users WHERE telegram_id = ?", (telegram_id,))
            row = c.fetchone()
            if row:
                c.execute(
                    "UPDATE users SET username = ?, last_active = ? WHERE telegram_id = ?",
                    (username, now, telegram_id),
                )
                conn.commit()
                return {"user_id": row["user_id"], "username": username, "is_new": False}

            user_id = int(telegram_id)
            c.execute(
                "INSERT INTO users (user_id, username, telegram_id, last_active, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, telegram_id, now, now),
            )
            c.execute("INSERT OR IGNORE INTO user_inventory (user_id, gold, xp, level) VALUES (?, 0, 0, 1)", (user_id,))
            conn.commit()
            return {"user_id": user_id, "username": username, "is_new": True}

    def get_user_purchased_packs(self, user_id: int, limit: int = 50):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT cp.pack_id, cp.pack_name, cp.pack_tier, cp.cards_data
                FROM pack_purchases pp
                JOIN creator_packs cp ON cp.pack_id = pp.pack_id
                WHERE pp.user_id = ?
                ORDER BY pp.purchased_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = c.fetchall()
        packs = []
        for r in rows:
            cards = json.loads(r["cards_data"] or "[]")
            packs.append(
                {
                    "pack_id": r["pack_id"],
                    "pack_name": r["pack_name"],
                    "pack_tier": r["pack_tier"],
                    "cards": cards,
                }
            )
        return packs

    def update_user_economy(self, user_id: int, gold_change: int = 0, xp_change: int = 0):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO user_inventory (user_id, gold, xp, level) VALUES (?, 0, 0, 1)", (user_id,))
            c.execute(
                "UPDATE user_inventory SET gold = COALESCE(gold, 0) + ?, xp = COALESCE(xp, 0) + ? WHERE user_id = ?",
                (gold_change, xp_change, user_id),
            )
            conn.commit()

    def get_user_economy(self, user_id: int):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT gold, xp, level FROM user_inventory WHERE user_id = ?", (user_id,))
            row = c.fetchone()
        if not row:
            return {"gold": 0, "xp": 0, "level": 1}
        return {"gold": row["gold"] or 0, "xp": row["xp"] or 0, "level": row["level"] or 1}

    def claim_daily_reward(self, user_id: int):
        today = datetime.utcnow().date().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT last_claim_date FROM daily_claims WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row and row["last_claim_date"] == today:
                return {"success": False, "message": "Already claimed today"}
            c.execute(
                "INSERT OR REPLACE INTO daily_claims (user_id, last_claim_date) VALUES (?, ?)",
                (user_id, today),
            )
            c.execute("INSERT OR IGNORE INTO user_inventory (user_id, gold, xp, level) VALUES (?, 0, 0, 1)", (user_id,))
            c.execute("UPDATE user_inventory SET gold = COALESCE(gold, 0) + 500 WHERE user_id = ?", (user_id,))
            conn.commit()
        return {"success": True, "gold_reward": 500}

    def get_user_stats(self, user_id: int):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT total_battles, wins, losses FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
        if not row:
            return {"total_battles": 0, "wins": 0, "losses": 0}
        return {
            "total_battles": row["total_battles"] or 0,
            "wins": row["wins"] or 0,
            "losses": row["losses"] or 0,
        }

    def generate_tma_link_code(self, user_id: int) -> str:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        expires_at = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO tma_link_codes (user_id, code, expires_at) VALUES (?, ?, ?)",
                (user_id, code, expires_at),
            )
            conn.commit()
        return code

    # Convenience methods used by other routers
    def get_user_collection(self, user_id: int):
        return []

    def get_live_packs(self, limit: int = 20):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT pack_id, pack_name, pack_tier, cards_data FROM creator_packs WHERE status = 'LIVE' LIMIT ?",
                (limit,),
            )
            rows = c.fetchall()
        return [
            {
                "pack_id": r["pack_id"],
                "pack_name": r["pack_name"],
                "pack_tier": r["pack_tier"],
                "cards": json.loads(r["cards_data"] or "[]"),
            }
            for r in rows
        ]

    def open_pack_for_drop(self, pack_id: str, user_id: int):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO pack_purchases (user_id, pack_id) VALUES (?, ?)", (user_id, pack_id))
            conn.commit()
        return {"success": True, "pack_id": pack_id}

    def get_leaderboard(self, metric: str = "wins", limit: int = 50):
        allowed = {"wins", "total_battles", "gold", "xp"}
        field = metric if metric in allowed else "wins"
        with self._get_connection() as conn:
            c = conn.cursor()
            if field in {"gold", "xp"}:
                c.execute(
                    f"SELECT u.user_id, u.username, i.{field} as value FROM users u LEFT JOIN user_inventory i ON i.user_id=u.user_id ORDER BY value DESC LIMIT ?",
                    (limit,),
                )
            else:
                c.execute(
                    f"SELECT user_id, username, {field} as value FROM users ORDER BY value DESC LIMIT ?",
                    (limit,),
                )
            rows = c.fetchall()
        return [{"user_id": r["user_id"], "username": r["username"], "value": r["value"] or 0} for r in rows]

    def get_battle_pass_status(self, user_id: int, season_id: str):
        return {"season_id": season_id, "current_tier": 0, "claimed_tiers": []}

    def claim_battle_pass_tier(self, user_id: int, season_id: str, tier: int):
        return True, "Tier claimed"

    def get_vip_status(self, user_id: int):
        return {"is_vip": False, "tier": 0, "expires_at": None}

    def set_vip_status(self, user_id: int, is_vip: bool, tier: int, expiration_date: str):
        return True

    def create_user_pack(self, pack_id: str, name: str, user_id: int, card_ids):
        cards_data = json.dumps([{"card_id": cid} for cid in card_ids])
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO creator_packs (pack_id, pack_name, pack_tier, status, cards_data) VALUES (?, ?, 'custom', 'LIVE', ?)",
                (pack_id, name, cards_data),
            )
            c.execute("INSERT INTO pack_purchases (user_id, pack_id) VALUES (?, ?)", (user_id, pack_id))
            conn.commit()
        return pack_id

    def get_user_pack(self, pack_id: str):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT pack_id, pack_name, cards_data FROM creator_packs WHERE pack_id = ?", (pack_id,))
            row = c.fetchone()
        if not row:
            return None
        return {"pack_id": row["pack_id"], "name": row["pack_name"], "cards": json.loads(row["cards_data"] or "[]")}

    def reserve_idempotency_key(self, user_id: int, action: str, idempotency_key: str, request_payload) -> dict:
        request_hash = hashlib.sha256(
            json.dumps(request_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                """
                SELECT request_hash, status_code, response_json
                FROM api_idempotency
                WHERE user_id=? AND action=? AND idempotency_key=?
                """,
                (user_id, action, idempotency_key),
            )
            existing = c.fetchone()
            if existing:
                conn.commit()
                if existing["request_hash"] != request_hash:
                    return {"state": "payload_conflict"}
                if existing["response_json"] is None:
                    return {"state": "in_progress"}
                return {
                    "state": "replay",
                    "status_code": existing["status_code"] or 200,
                    "response": json.loads(existing["response_json"]),
                }
            c.execute(
                """
                INSERT INTO api_idempotency (user_id, action, idempotency_key, request_hash, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, action, idempotency_key, request_hash, now),
            )
            conn.commit()
        return {"state": "reserved"}

    def finalize_idempotency_key(
        self, user_id: int, action: str, idempotency_key: str, status_code: int, response_payload
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                UPDATE api_idempotency
                SET status_code=?, response_json=?, updated_at=?
                WHERE user_id=? AND action=? AND idempotency_key=?
                """,
                (status_code, json.dumps(response_payload), now, user_id, action, idempotency_key),
            )
            conn.commit()

    def release_idempotency_key(self, user_id: int, action: str, idempotency_key: str) -> None:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM api_idempotency WHERE user_id=? AND action=? AND idempotency_key=? AND response_json IS NULL",
                (user_id, action, idempotency_key),
            )
            conn.commit()


Database = DatabaseManager
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
