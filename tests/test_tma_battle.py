"""Tests for TMA battle router."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient
from database import get_db, DatabaseManager
from models import Base

TG_USER_A = {"id": 1001, "username": "playerA", "first_name": "A"}


@pytest.fixture
def db_override():
    # Setup for in-memory SQLite database for testing
    test_db = DatabaseManager(test_database_url="sqlite:///:memory:")
    Base.metadata.create_all(test_db.engine)  # Create tables
    print("DEBUG: Tables created in test_tma_battle.py fixture")
    yield test_db  # Provide the test database instance
    print("DEBUG: Tables dropped in test_tma_battle.py fixture")
    Base.metadata.drop_all(test_db.engine)  # Drop tables after test

@pytest.fixture
def client_a(db_override): # Inject the db_override fixture
    from tma.api.main import app
    from tma.api.auth import get_tg_user
    app.dependency_overrides[get_tg_user] = lambda: TG_USER_A
    app.dependency_overrides[get_db] = lambda: db_override # Override get_db to return our test db
    yield TestClient(app)
    app.dependency_overrides.clear()


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
