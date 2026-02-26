"""Tests for TMA users router."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from tma.api.main import app
    from tma.api.auth import get_tg_user

    # FastAPI dependency_overrides keeps the mock alive for the full test
    app.dependency_overrides[get_tg_user] = lambda: {"id": 111, "username": "testplayer", "first_name": "Test"}
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
