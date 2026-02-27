"""
Pytest configuration — supports SQLite (default) and Docker PostgreSQL.

Usage:
  pytest tests/ -v                      # SQLite only (fast, no Docker)
  pytest tests/ -v --pg                 # PostgreSQL via Docker (port 5433)
  pytest tests/ -v --pg --both          # Both backends side by side

Docker setup:
  docker compose -f docker-compose.test.yml up -d
  docker compose -f docker-compose.test.yml down
"""

import os
import sys
import json
import uuid
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Docker PG test connection (matches docker-compose.test.yml)
TEST_PG_URL = "postgresql://testuser:testpass@localhost:5433/test_music_legends"


def pytest_addoption(parser):
    parser.addoption("--pg", action="store_true", default=False,
                     help="Run tests against Docker PostgreSQL (port 5433)")
    parser.addoption("--both", action="store_true", default=False,
                     help="Run tests against BOTH SQLite and PostgreSQL")


def pytest_configure(config):
    config.addinivalue_line("markers", "pg: PostgreSQL-specific test")
    config.addinivalue_line("markers", "sqlite: SQLite-specific test")


def _pg_available() -> bool:
    """Check if Docker PostgreSQL is reachable."""
    try:
        import psycopg2
        conn = psycopg2.connect(TEST_PG_URL, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# Backend factories
# ─────────────────────────────────────────────

def _make_pg_db():
    """Create DatabaseManager connected to Docker PostgreSQL, clean all tables."""
    import database as _db_mod
    from database import DatabaseManager

    os.environ["DATABASE_URL"] = TEST_PG_URL
    _db_mod._db_instance = None
    mgr = DatabaseManager()

    # Truncate all tables for clean state
    with mgr._get_connection() as conn:
        cursor = conn.cursor()
        for table in [
            "user_cards", "pack_purchases", "dev_pack_supply",
            "user_inventory", "transaction_audit_log", "active_battles",
            "users", "cards", "creator_packs",
        ]:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                except Exception:
                    pass
        conn.commit()

    _db_mod._db_instance = mgr
    return mgr


def _make_sqlite_db(tmp_path_factory):
    """Create DatabaseManager connected to temp SQLite file."""
    import database as _db_mod
    from database import DatabaseManager

    os.environ.pop("DATABASE_URL", None)
    _db_mod._db_instance = None
    db_path = str(tmp_path_factory.mktemp("db") / "test.db")
    mgr = DatabaseManager(test_database_url="sqlite:///:memory:")
    mgr.init_database()
    _db_mod._db_instance = mgr
    return mgr


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

def _get_backends(config):
    """Determine which backends to test."""
    use_pg = config.getoption("--pg", default=False)
    use_both = config.getoption("--both", default=False)
    if use_both:
        return ["sqlite", "pg"]
    elif use_pg:
        return ["pg"]
    else:
        return ["sqlite"]


@pytest.fixture(scope="module")
def db_backend(request, tmp_path_factory):
    """DatabaseManager fixture for dual-backend tests.

    Returns (db_manager, backend_name) tuple.
    Default: SQLite. With --pg: PostgreSQL. With --both: both.

    NOTE: test_bot_core.py defines its OWN `db` fixture (SQLite-only).
    New dual-backend tests should use `db_backend` instead.
    """
    backends = _get_backends(request.config)

    for backend_name in backends:
        if backend_name == "pg":
            if not _pg_available():
                pytest.skip("Docker PostgreSQL not available at localhost:5433. "
                            "Run: docker compose -f docker-compose.test.yml up -d")
            mgr = _make_pg_db()
        else:
            mgr = _make_sqlite_db(tmp_path_factory)

        yield mgr, backend_name

    # Cleanup
    os.environ.pop("DATABASE_URL", None)


@pytest.fixture
def seed_user(db_backend):
    """Insert a test user + inventory; return user_id."""
    from database import SessionLocal
    from models import User

    mgr, _ = db_backend
    uid = str(100_000_001)  # Ensure user_id is a string
    with SessionLocal() as session:
        user = User(user_id=uid, username="TestUser", discord_tag="TestUser#0001")
        session.add(user)
        session.commit()
        session.refresh(user)
    return uid


@pytest.fixture
def seed_card(db_backend):
    """Insert one test card with all stat columns; return card dict."""
    from database import SessionLocal
    from models import Card

    mgr, _ = db_backend
    cid = f"card_{uuid.uuid4().hex[:8]}"
    card_data = {
        "card_id": cid, "name": "Test Artist", "artist_name": "Test Artist",
        "title": "Test Song", "rarity": "epic", "tier": "platinum",
        "image_url": "", "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "impact": 70, "skill": 80, "longevity": 60, "culture": 75, "hype": 65,
    }
    with SessionLocal() as session:
        card = Card(**card_data)
        session.add(card)
        session.commit()
        session.refresh(card)
    return card_data


@pytest.fixture
def seed_creator_pack(db_backend, seed_card):
    """Insert a LIVE creator pack containing seed_card; return pack_id."""
    mgr, _ = db_backend
    pack_id = f"pack_{uuid.uuid4().hex[:8]}"
    cards_data = [seed_card]
    with mgr._get_connection() as conn:
        c = conn.cursor()
        ph = mgr._get_placeholder()
        if mgr._db_type == "postgresql":
            c.execute(f"""
                INSERT INTO creator_packs (pack_id, name, pack_tier, status, cards_data, pack_size)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph})
                ON CONFLICT DO NOTHING
            """, (pack_id, "Test Pack", "community", "LIVE", json.dumps(cards_data), 1))
        else:
            c.execute("""
                INSERT OR IGNORE INTO creator_packs (pack_id, name, pack_tier, status, cards_data, pack_size)
                VALUES (?,?,?,?,?,?)
            """, (pack_id, "Test Pack", "community", "LIVE", json.dumps(cards_data), 1))
        conn.commit()
    return pack_id


@pytest.fixture
def seed_dev_supply(db_backend, seed_creator_pack):
    """Add 5 copies of seed_creator_pack to dev_pack_supply."""
    mgr, _ = db_backend
    with mgr._get_connection() as conn:
        c = conn.cursor()
        ph = mgr._get_placeholder()
        if mgr._db_type == "postgresql":
            c.execute(f"INSERT INTO dev_pack_supply (pack_id, quantity) VALUES ({ph},{ph}) ON CONFLICT DO NOTHING",
                      (seed_creator_pack, 5))
        else:
            c.execute("INSERT OR IGNORE INTO dev_pack_supply (pack_id, quantity) VALUES (?,?)",
                      (seed_creator_pack, 5))
        conn.commit()
    return seed_creator_pack
