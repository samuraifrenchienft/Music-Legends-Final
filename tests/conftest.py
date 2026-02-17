# -*- coding: utf-8 -*-
"""
Pytest Configuration for Game Tests

Sets up test environment, databases, and fixtures for all test suites.
Ensures consistent test execution across CI and local environments.
"""

import os
import sys
import pytest
from unittest.mock import Mock

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set test environment variables
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["DATABASE_URL"] = "postgres://game:game@localhost:5432/game"
os.environ["ENVIRONMENT"] = "test"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_dummy"
os.environ["DISCORD_BOT_TOKEN"] = "test_bot_token"

# Disable logging during tests for cleaner output
import logging
logging.getLogger().setLevel(logging.CRITICAL)

try:
    import redis as _redis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

try:
    import psycopg2 as _psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and before performing collection
    and entering the run test loop.

    Sets up test databases and seeds initial data.
    """
    print("\nInitializing test environment...")
    setup_test_database()
    setup_test_redis()
    seed_test_data()
    print("Test environment ready")

def pytest_sessionfinish(session, exitstatus):
    """
    Called after the whole test run finished, right before returning the exit status.

    Cleans up test data and connections.
    """
    print("\nCleaning up test environment...")
    cleanup_test_data()
    print("Cleanup complete")

def pytest_configure(config):
    """
    Called after command line options have been parsed and all plugins have been loaded.

    Registers custom markers and configuration.
    """
    config.addinivalue_line(
        "markers", "smoke: Mark test as smoke test (critical for launch)"
    )
    config.addinivalue_line(
        "markers", "integration: Mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: Mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: Mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """
    Called after collection has been performed, may filter or re-order the items in-place.

    Adds appropriate markers to tests based on their location and name.
    """
    for item in items:
        if "smoke.py" in str(item.fspath) or "smoke" in item.name.lower():
            item.add_marker(pytest.mark.smoke)
        if "integration" in str(item.fspath).lower():
            item.add_marker(pytest.mark.integration)
        if "unit" in str(item.fspath).lower():
            item.add_marker(pytest.mark.unit)

# ---------- Database Setup ----------

def setup_test_database():
    """Setup test database connection and schema."""
    if not _PSYCOPG2_AVAILABLE:
        print("psycopg2 not available, skipping database setup")
        return
    try:
        conn = _psycopg2.connect(
            host="localhost", port=5432, database="game", user="game", password="game"
        )
        conn.close()
        print("Database connection successful")
    except Exception as e:
        print(f"Database setup failed: {e}")
        print("Make sure PostgreSQL is running with test database")

def setup_test_redis():
    """Setup test Redis connection."""
    if not _REDIS_AVAILABLE:
        print("redis not available, skipping Redis setup")
        return
    try:
        r = _redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("Redis connection successful")
    except Exception as e:
        print(f"Redis setup failed: {e}")
        print("Make sure Redis is running")

# ---------- Test Data Seeding ----------

def seed_test_data():
    """Seed minimal test data required for smoke tests."""
    try:
        seed_test_artists()
        seed_test_packs()
        print("Test data seeded")
    except Exception as e:
        print(f"Test data seeding failed: {e}")

def seed_test_artists():
    """Seed minimal test artists."""
    try:
        from models.artist import Artist

        if Artist.count() > 0:
            print(f"Artists already exist: {Artist.count()}")
            return

        test_artists = [
            {
                'name': 'Test Artist Alpha',
                'image_url': 'https://picsum.photos/200/200?random=1',
                'bio': 'Test artist for smoke tests',
                'social_media': {'twitter': '@testalpha'},
                'current_legendary': 0, 'current_platinum': 0, 'current_gold': 0
            },
            {
                'name': 'Test Artist Beta',
                'image_url': 'https://picsum.photos/200/200?random=2',
                'bio': 'Another test artist',
                'social_media': {'instagram': '@testbeta'},
                'current_legendary': 0, 'current_platinum': 0, 'current_gold': 0
            },
            {
                'name': 'Test Artist Gamma',
                'image_url': 'https://picsum.photos/200/200?random=3',
                'bio': 'Third test artist',
                'social_media': {'tiktok': '@testgamma'},
                'current_legendary': 0, 'current_platinum': 0, 'current_gold': 0
            }
        ]

        created_artists = []
        for artist_data in test_artists:
            try:
                artist = Artist.create(**artist_data)
                created_artists.append(artist)
            except Exception as e:
                print(f"Failed to create artist {artist_data['name']}: {e}")

        print(f"Created {len(created_artists)} test artists")

    except ImportError:
        print("Artist model not available, skipping artist seeding")
    except Exception as e:
        print(f"Artist seeding failed: {e}")

def seed_test_packs():
    """Seed minimal test pack configurations."""
    try:
        pass  # Smoke tests create their own pack data
    except Exception as e:
        print(f"Pack seeding failed: {e}")

# ---------- Cleanup Functions ----------

def cleanup_test_data():
    """Clean up test data created during tests."""
    try:
        cleanup_test_purchases()
        cleanup_test_cards()
        cleanup_test_trades()
        cleanup_test_redis()
    except Exception as e:
        print(f"Cleanup failed: {e}")

def cleanup_test_purchases():
    """Clean up test purchases."""
    try:
        from models.purchase import Purchase
        test_purchases = Purchase.where("payment_id LIKE ?", ("SMOKE_TEST_%",))
        for purchase in test_purchases:
            purchase.delete()
    except ImportError:
        pass
    except Exception as e:
        print(f"Purchase cleanup failed: {e}")

def cleanup_test_cards():
    """Clean up test cards."""
    try:
        from models.card import Card
        test_cards = Card.where("purchase_id LIKE ?", ("SMOKE_TEST_%",))
        for card in test_cards:
            card.delete()
    except ImportError:
        pass
    except Exception as e:
        print(f"Card cleanup failed: {e}")

def cleanup_test_trades():
    """Clean up test trades."""
    try:
        from models.trade import Trade
        test_trades = Trade.where("initiator_id >= ?", (999999,))
        for trade in test_trades:
            trade.delete()
    except ImportError:
        pass
    except Exception as e:
        print(f"Trade cleanup failed: {e}")

def cleanup_test_redis():
    """Clean up test Redis data."""
    if not _REDIS_AVAILABLE:
        return
    try:
        r = _redis.Redis(host='localhost', port=6379, db=0)
        test_keys = r.keys("pack:999999*")
        if test_keys:
            r.delete(*test_keys)
    except Exception as e:
        print(f"Redis cleanup failed: {e}")

# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def test_db():
    """Fixture providing test database connection."""
    pass

@pytest.fixture(scope="session")
def test_redis():
    """Fixture providing test Redis connection."""
    if not _REDIS_AVAILABLE:
        yield None
        return
    try:
        r = _redis.Redis(host='localhost', port=6379, db=0)
        yield r
    except Exception as e:
        print(f"Redis fixture failed: {e}")
        yield None

@pytest.fixture
def sample_user():
    """Fixture providing a sample test user."""
    return {
        'id': 999999,
        'name': 'Test User',
        'discriminator': '0001',
        'avatar': None
    }

@pytest.fixture
def sample_payment():
    """Fixture providing a sample payment ID."""
    return "SMOKE_TEST_PAYMENT_123"

# ---------- Mock Services ----------

@pytest.fixture(autouse=True)
def mock_discord():
    """Mock Discord.py to avoid needing actual bot connection."""
    mock_bot = Mock()
    mock_bot.user = Mock()
    mock_bot.user.id = 12345
    with pytest.MonkeyPatch().context() as m:
        yield mock_bot

# ---------- Test Utilities ----------

@pytest.fixture
def test_artist():
    """Create or get a test artist."""
    try:
        from models.artist import Artist
        artist = Artist.first()
        if not artist:
            artist = Artist.create(
                name='Smoke Test Artist',
                image_url='https://picsum.photos/200/200?random=999',
                bio='Artist for smoke tests',
                current_legendary=0,
                current_platinum=0,
                current_gold=0
            )
        return artist
    except Exception:
        return None

def pytest_assertion_pass(item, lineno, orig, expl):
    pass

def pytest_assertion_fail(item, lineno, orig, expl):
    pass
