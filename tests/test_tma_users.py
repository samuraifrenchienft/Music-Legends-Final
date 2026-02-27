"""Tests for TMA users router."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from database import get_db, DatabaseManager
from models import Base


@pytest.fixture
def db_override():
    # Setup for in-memory SQLite database for testing
    test_db = DatabaseManager(test_database_url="sqlite:///:memory:")
    Base.metadata.create_all(test_db.engine)  # Create tables
    print("DEBUG: Tables created in test_tma_users.py fixture")
    yield test_db  # Provide the test database instance
    print("DEBUG: Tables dropped in test_tma_users.py fixture")
    Base.metadata.drop_all(test_db.engine)  # Drop tables after test

@pytest.fixture
def client(db_override): # Inject the db_override fixture
    from tma.api.main import app
    from tma.api.auth import get_tg_user

    # FastAPI dependency_overrides keeps the mock alive for the full test
    app.dependency_overrides[get_tg_user] = lambda: {"id": 111, "username": "testplayer", "first_name": "Test"}
    app.dependency_overrides[get_db] = lambda: db_override # Override get_db to return our test db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def raw_client():
    """Client with no auth overrides — tests real header validation."""
    from tma.api.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_get_me_returns_user(client):
    resp = client.get("/api/me", headers={"Authorization": "tma fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "gold" in data
    assert data["username"] == "testplayer"


def test_get_me_422_without_auth(raw_client):
    resp = raw_client.get("/api/me")
    assert resp.status_code == 422  # FastAPI: required header missing


def test_link_generate(client):
    resp = client.post("/api/link/generate", headers={"Authorization": "tma fake"})
    assert resp.status_code == 200
    assert "code" in resp.json()
    assert len(resp.json()["code"]) == 6
