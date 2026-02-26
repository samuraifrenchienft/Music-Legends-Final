# database.py
import sqlite3
import json
import os
import urllib.parse
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager


def _parse_db_url(url: str) -> dict:
    """Parse a DATABASE_URL into psycopg2 keyword arguments.

    Handles passwords with special characters that break naive URL parsing.
    Adds sslmode=require for Railway external proxy connections.
    """
    parsed = urllib.parse.urlparse(url)
    params = {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'dbname': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': urllib.parse.unquote(parsed.password or ''),
        'sslmode': 'require',
    }
    return params


class _PgCursorWrapper:
    """Wraps a psycopg2 cursor to translate ? placeholders to %s."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        # Translate SQLite syntax to PostgreSQL
        query = query.replace('?', '%s')

        # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
        if 'INSERT OR IGNORE' in query:
            query = query.replace('INSERT OR IGNORE', 'INSERT')
            if 'ON CONFLICT' not in query:
                # Append ON CONFLICT DO NOTHING before any trailing whitespace
                query = query.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'

        # INSERT OR REPLACE → INSERT ... ON CONFLICT DO NOTHING
        if 'INSERT OR REPLACE' in query:
            query = query.replace('INSERT OR REPLACE', 'INSERT')
            if 'ON CONFLICT' not in query:
                query = query.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'

        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description


class _PgConnectionWrapper:
    """Wraps a psycopg2 connection so existing SQLite code works unchanged.

    - cursor() returns a _PgCursorWrapper (auto-translates ? to %s)
    - Context manager commits on success, rolls back on error (matches SQLite)
    - execute() is forwarded through the wrapper
    """

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _PgCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()
        return False


class PooledConnectionWrapper:
    """Wrapper for pooled connections that returns to pool on close.

    This wrapper behaves like _PgConnectionWrapper but returns the connection
    to the pool instead of closing it.
    """

    def __init__(self, conn, pool, is_overflow: bool = False):
        self._conn = conn
        self._pool = pool
        self._is_overflow = is_overflow

    def cursor(self):
        return _PgCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        """Return connection to pool instead of closing."""
        if self._is_overflow:
            # Overflow connection - close it and decrement counter
            with self._pool._lock:
                self._pool._overflow_count -= 1
            try:
                self._conn.close()
            except:
                pass
        else:
            # Regular pool connection - return to pool
            try:
                self._conn.rollback()  # Clear any uncommitted transaction
                wrapped = _PgConnectionWrapper(self._conn)
                self._pool._pool.put(wrapped, block=False)
            except:
                # Pool full (shouldn't happen) - close connection
                try:
                    self._conn.close()
                except:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self.close()  # Return to pool
        return False


class ConnectionPool:
    """Thread-safe connection pool for PostgreSQL using psycopg2.

    Maintains a pool of persistent connections to avoid the overhead of
    creating new connections for every query (~50ms per connection).

    Pool configuration:
    - pool_size: 10 persistent connections
    - max_overflow: 5 additional connections during spikes
    - Total max: 15 concurrent connections
    """

    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 5):
        import psycopg2
        from queue import Queue, Empty
        import threading

        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool = Queue(maxsize=pool_size)
        self._overflow_count = 0
        self._lock = threading.Lock()

        # Pre-populate pool with connections (keepalives keep idle sockets healthy)
        self._conn_params = {
            **_parse_db_url(database_url),
            'keepalives': 1,
            'keepalives_idle': 60,
            'keepalives_interval': 10,
            'keepalives_count': 3,
        }
        for _ in range(pool_size):
            try:
                conn = psycopg2.connect(**self._conn_params)
                self._pool.put(_PgConnectionWrapper(conn))
            except Exception as e:
                print(f"[POOL] Error creating initial connection: {e}")
                # Continue - pool will create on-demand if needed

    def get_connection(self, timeout: float = 30.0):
        """Get a connection from the pool.

        Args:
            timeout: Seconds to wait for available connection

        Returns:
            PooledConnectionWrapper: Database connection that returns to pool on close

        Raises:
            Exception: If no connection available within timeout
        """
        from queue import Empty
        import psycopg2

        # Try to get from pool first
        try:
            conn = self._pool.get(block=True, timeout=timeout)
            # Verify connection is still alive
            try:
                conn._conn.isolation_level  # Simple check
                return PooledConnectionWrapper(conn._conn, self, is_overflow=False)
            except:
                # Connection dead, create new one
                conn = psycopg2.connect(**self._conn_params)
                return PooledConnectionWrapper(conn, self, is_overflow=False)
        except Empty:
            # Pool exhausted, check if we can create overflow connection
            with self._lock:
                if self._overflow_count < self.max_overflow:
                    self._overflow_count += 1
                    try:
                        conn = psycopg2.connect(**self._conn_params)
                        return PooledConnectionWrapper(conn, self, is_overflow=True)
                    except Exception as e:
                        self._overflow_count -= 1
                        raise Exception(f"Failed to create overflow connection: {e}")
                else:
                    raise Exception(
                        f"Connection pool exhausted (pool_size={self.pool_size}, "
                        f"max_overflow={self.max_overflow}, timeout={timeout}s)"
                    )

    def return_connection(self, conn):
        """Return a connection to the pool.

        Args:
            conn: _PgConnectionWrapper to return
        """
        if hasattr(conn, '_is_overflow') and conn._is_overflow:
            # Overflow connection - close it
            with self._lock:
                self._overflow_count -= 1
            try:
                conn._conn.close()
            except:
                pass
        else:
            # Regular pool connection - return to pool
            try:
                # Reset connection state
                conn._conn.rollback()  # Clear any uncommitted transaction
                self._pool.put(conn, block=False)
            except:
                # Pool full (shouldn't happen) - close connection
                try:
                    conn._conn.close()
                except:
                    pass

    def close_all(self):
        """Close all connections in the pool. Call on shutdown."""
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn._conn.close()
            except:
                pass


class DatabaseManager:
    _instance = None
    _pool: Optional[ConnectionPool] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, database_url: str = "sqlite:///music_legends.db"):
        if hasattr(self, 'database_url') and self.database_url == database_url:
            return

        self.database_url = database_url
        self.is_postgres = database_url.startswith('postgres')

        if self.is_postgres:
            if not self.__class__._pool:
                self.__class__._pool = ConnectionPool(database_url)
        else:
            # For SQLite, ensure the database file exists
            db_path = database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        if self.is_postgres:
            if not self._pool:
                raise Exception("Connection pool not initialized.")
            conn = self._pool.get_connection()
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.database_url.replace("sqlite:///", ""))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if not self.is_postgres:
                # Enable foreign keys for SQLite
                cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Schema is now managed by Alembic.
            # This method can be used for any initial data seeding if required.
            print("✅ [DATABASE] Initialized (Alembic handles schema)")

    def execute(self, query: str, params: tuple = (), *, commit: bool = False) -> sqlite3.Cursor:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_user(self, user_id: int) -> Optional[dict]:
        query = "SELECT * FROM users WHERE user_id = ?"
        row = self.fetchone(query, (user_id,))
        return dict(row) if row else None

    def create_user(self, user_id: int, username: str, telegram_id: Optional[int] = None) -> None:
        query = "INSERT OR IGNORE INTO users (user_id, username, telegram_id) VALUES (?, ?, ?)"
        self.execute(query, (user_id, username, telegram_id), commit=True)

    def get_card_by_id(self, card_id: str) -> Optional[dict]:
        query = "SELECT * FROM cards WHERE card_id = ?"
        row = self.fetchone(query, (card_id,))
        return dict(row) if row else None

    def get_user_inventory(self, user_id: int) -> List[dict]:
        query = """
            SELECT c.card_id, c.name, c.rarity, c.artist, inv.quantity
            FROM user_inventory inv
            JOIN cards c ON inv.card_id = c.card_id
            WHERE inv.user_id = ?
        """
        rows = self.fetchall(query, (user_id,))
        return [dict(row) for row in rows]

    def add_card_to_inventory(self, user_id: int, card_id: str, quantity: int = 1) -> None:
        query = """
            INSERT INTO user_inventory (user_id, card_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, card_id) DO UPDATE SET quantity = quantity + excluded.quantity
        """
        self.execute(query, (user_id, card_id, quantity), commit=True)

    def remove_card_from_inventory(self, user_id: int, card_id: str, quantity: int = 1) -> bool:
        # Check current quantity
        current_quantity_row = self.fetchone("SELECT quantity FROM user_inventory WHERE user_id = ? AND card_id = ?", (user_id, card_id))
        if not current_quantity_row or current_quantity_row['quantity'] < quantity:
            return False

        if current_quantity_row['quantity'] == quantity:
            # Remove row if quantity becomes zero
            self.execute("DELETE FROM user_inventory WHERE user_id = ? AND card_id = ?", (user_id, card_id), commit=True)
        else:
            # Decrement quantity
            self.execute("UPDATE user_inventory SET quantity = quantity - ? WHERE user_id = ? AND card_id = ?", (quantity, user_id, card_id), commit=True)
        return True

    def get_pack(self, pack_id: str) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM packs WHERE pack_id = ?", (pack_id,))
        return dict(row) if row else None

    def get_user_packs(self, user_id: int) -> List[dict]:
        rows = self.fetchall("SELECT p.pack_id, p.name, up.quantity FROM user_packs up JOIN packs p ON up.pack_id = p.pack_id WHERE up.user_id = ?", (user_id,))
        return [dict(row) for row in rows]

    def add_pack_to_user(self, user_id: int, pack_id: str, quantity: int = 1) -> None:
        query = """
            INSERT INTO user_packs (user_id, pack_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, pack_id) DO UPDATE SET quantity = quantity + excluded.quantity
        """
        self.execute(query, (user_id, pack_id, quantity), commit=True)

    def use_user_pack(self, user_id: int, pack_id: str) -> bool:
        # Check current quantity
        current_quantity_row = self.fetchone("SELECT quantity FROM user_packs WHERE user_id = ? AND pack_id = ?", (user_id, pack_id))
        if not current_quantity_row or current_quantity_row['quantity'] < 1:
            return False

        if current_quantity_row['quantity'] == 1:
            self.execute("DELETE FROM user_packs WHERE user_id = ? AND pack_id = ?", (user_id, pack_id), commit=True)
        else:
            self.execute("UPDATE user_packs SET quantity = quantity - 1 WHERE user_id = ? AND pack_id = ?", (user_id, pack_id), commit=True)
        return True

    def create_trade(self, user1_id: int, user2_id: int, user1_cards: List[str], user2_cards: List[str], user1_gold: int, user2_gold: int) -> int:
        query = """
            INSERT INTO trades (user1_id, user2_id, user1_cards, user2_cards, user1_gold, user2_gold)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = self.execute(query, (user1_id, user2_id, json.dumps(user1_cards), json.dumps(user2_cards), user1_gold, user2_gold), commit=True)
        return cursor.lastrowid

    def get_trade(self, trade_id: int) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        return dict(row) if row else None

    def update_trade_status(self, trade_id: int, status: str) -> None:
        self.execute("UPDATE trades SET status = ? WHERE trade_id = ?", (status, trade_id), commit=True)

    def get_marketplace_listings(self) -> List[dict]:
        rows = self.fetchall("SELECT * FROM marketplace_listings WHERE status = 'active'")
        return [dict(row) for row in rows]

    def create_marketplace_listing(self, seller_id: int, card_id: str, price: int) -> int:
        cursor = self.execute("INSERT INTO marketplace_listings (seller_id, card_id, price) VALUES (?, ?, ?)", (seller_id, card_id, price), commit=True)
        return cursor.lastrowid

    def get_listing(self, listing_id: int) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM marketplace_listings WHERE listing_id = ?", (listing_id,))
        return dict(row) if row else None

    def update_listing_status(self, listing_id: int, status: str) -> None:
        self.execute("UPDATE marketplace_listings SET status = ? WHERE listing_id = ?", (status, listing_id), commit=True)

    def get_pending_tma_battle(self, user_id: int) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM pending_tma_battles WHERE user_id = ?", (user_id,))
        return dict(row) if row else None

    def create_pending_tma_battle(self, user_id: int, deck: List[str], bet_amount: int) -> None:
        self.execute("INSERT OR REPLACE INTO pending_tma_battles (user_id, deck, bet_amount) VALUES (?, ?, ?)", (user_id, json.dumps(deck), bet_amount), commit=True)

    def delete_pending_tma_battle(self, user_id: int) -> None:
        self.execute("DELETE FROM pending_tma_battles WHERE user_id = ?", (user_id,), commit=True)

    def get_season_progress(self, user_id: int, season_id: int) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM season_progress WHERE user_id = ? AND season_id = ?", (user_id, season_id))
        return dict(row) if row else None

    def update_season_progress(self, user_id: int, season_id: int, xp: int, tier: int, claimed_tiers: List[int]) -> None:
        query = """
            INSERT INTO season_progress (user_id, season_id, xp, tier, claimed_tiers)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, season_id) DO UPDATE SET
                xp = excluded.xp,
                tier = excluded.tier,
                claimed_tiers = excluded.claimed_tiers
        """
        self.execute(query, (user_id, season_id, xp, tier, json.dumps(claimed_tiers)), commit=True)

    def get_vip_status(self, user_id: int) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM vip_status WHERE user_id = ?", (user_id,))
        return dict(row) if row else None

    def update_vip_status(self, user_id: int, is_vip: bool, vip_tier: int, expiration_date: Optional[datetime]) -> None:
        query = """
            INSERT INTO vip_status (user_id, is_vip, vip_tier, expiration_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                is_vip = excluded.is_vip,
                vip_tier = excluded.vip_tier,
                expiration_date = excluded.expiration_date
        """
        self.execute(query, (user_id, is_vip, vip_tier, expiration_date), commit=True)

    def create_user_pack(self, pack_id: str, name: str, creator_id: int, cards: List[str]) -> None:
        self.execute("INSERT INTO user_created_packs (pack_id, name, creator_id, cards) VALUES (?, ?, ?, ?)", (pack_id, name, creator_id, json.dumps(cards)), commit=True)

    def get_user_created_pack(self, pack_id: str) -> Optional[dict]:
        row = self.fetchone("SELECT * FROM user_created_packs WHERE pack_id = ?", (pack_id,))
        return dict(row) if row else None

    def get_all_user_created_packs(self) -> List[dict]:
        rows = self.fetchall("SELECT * FROM user_created_packs")
        return [dict(row) for row in rows]
