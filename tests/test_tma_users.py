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
    """In-memory SQLite instance that hijacks the singleton so routers use it."""
    from database import Database
    test_db = DatabaseManager(test_database_url="sqlite:///:memory:")
    Base.metadata.create_all(test_db.engine)
    old_instance = Database._instance
    Database._instance = test_db   # redirect get_db() direct calls to test db
    yield test_db
    Database._instance = old_instance
    Base.metadata.drop_all(test_db.engine)

@pytest.fixture
def client(db_override):
    from tma.api.main import app
    from tma.api.auth import get_tg_user

    app.dependency_overrides[get_tg_user] = lambda: {"id": 111, "username": "testplayer", "first_name": "Test"}
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def raw_client(db_override):
    """Client with real auth enforcement (no dependency_overrides)."""
    from tma.api.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_get_me_returns_user(client):
    resp = client.get("/api/me", headers={"Authorization": "tma fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "gold" in data
    assert data["username"] == "testplayer"


def test_get_me_401_without_auth(raw_client):
    """No Authorization header → 401."""
    resp = raw_client.get("/api/me")
    assert resp.status_code == 401


def test_get_me_skip_hmac(db_override):
    """TMA_SKIP_HMAC=true lets any 'tma ...' auth through (dev mode)."""
    import os
    os.environ["TMA_SKIP_HMAC"] = "true"
    try:
        from tma.api.main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/me", headers={"Authorization": "tma dev"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "user_id" in resp.json()
    finally:
        os.environ.pop("TMA_SKIP_HMAC", None)


def test_link_generate(client):
    resp = client.post("/api/link/generate", headers={"Authorization": "tma fake"})
    assert resp.status_code == 200
    assert "code" in resp.json()
    assert len(resp.json()["code"]) == 6
