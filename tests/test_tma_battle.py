"""Tests for TMA battle router."""
import sys, os
import sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient
import database as db_mod
from database import DatabaseManager

TG_USER_A = {"id": 1001, "username": "playerA", "first_name": "A"}
TG_USER_B = {"id": 1002, "username": "playerB", "first_name": "B"}


@pytest.fixture
def battle_env(tmp_path):
    db_path = tmp_path / "tma_battle_test.db"
    mgr = DatabaseManager(db_path=str(db_path))
    db_mod._db_instance = mgr

    from tma.api.main import app
    from tma.api.auth import get_tg_user
    current_user = dict(TG_USER_A)
    app.dependency_overrides[get_tg_user] = lambda: current_user
    yield TestClient(app), mgr, current_user
    app.dependency_overrides.clear()
    db_mod._db_instance = None


def _set_user(current_user: dict, user: dict):
    current_user.clear()
    current_user.update(user)


def _seed_telegram_user(mgr: DatabaseManager, tg_user: dict):
    mgr.get_or_create_telegram_user(tg_user["id"], tg_user.get("username", ""), tg_user.get("first_name", ""))


def _seed_pack_and_purchase(mgr: DatabaseManager, user_id: int, pack_id: str):
    cards = '[{"card_id":"c1","name":"Artist 1","title":"Track 1","rarity":"common","impact":70,"skill":70,"longevity":70,"culture":70,"hype":70}]'
    with mgr._get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO creator_packs (pack_id, pack_name, pack_tier, status, cards_data) VALUES (?, ?, ?, 'LIVE', ?)",
            (pack_id, f"Pack {pack_id}", "community", cards),
        )
        c.execute(
            "INSERT INTO pack_purchases (user_id, pack_id) VALUES (?, ?)",
            (user_id, pack_id),
        )
        conn.commit()


def test_challenge_missing_pack_returns_403(battle_env):
    client, mgr, current_user = battle_env
    _set_user(current_user, TG_USER_A)
    _seed_telegram_user(mgr, TG_USER_B)
    resp = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": 1002, "pack_id": "nonexistent", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    assert resp.status_code == 403


def test_get_nonexistent_battle_returns_404(battle_env):
    client, _, _ = battle_env
    resp = client.get("/api/battle/XXXXXX", headers={"Authorization": "tma fake"})
    assert resp.status_code == 404


def test_prevent_duplicate_open_challenge_for_same_pair(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")

    _set_user(current_user, TG_USER_A)
    first = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    assert first.status_code == 200
    first_id = first.json()["battle_id"]

    second = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    assert second.status_code == 200
    data = second.json()
    assert data["battle_id"] == first_id
    assert data["status"] == "waiting"
    assert data.get("duplicate_prevented") is True


def test_opponent_can_decline_and_status_is_persisted(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")

    _set_user(current_user, TG_USER_A)
    create = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    battle_id = create.json()["battle_id"]

    _set_user(current_user, TG_USER_B)
    decline = client.post(f"/api/battle/{battle_id}/decline", headers={"Authorization": "tma fake"})
    assert decline.status_code == 200
    assert decline.json()["status"] == "declined"

    _set_user(current_user, TG_USER_A)
    status = client.get(f"/api/battle/{battle_id}", headers={"Authorization": "tma fake"})
    assert status.status_code == 200
    assert status.json()["status"] == "declined"


def test_only_challenger_can_cancel(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")

    _set_user(current_user, TG_USER_A)
    create = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    battle_id = create.json()["battle_id"]

    _set_user(current_user, TG_USER_B)
    forbidden = client.post(f"/api/battle/{battle_id}/cancel", headers={"Authorization": "tma fake"})
    assert forbidden.status_code == 403

    _set_user(current_user, TG_USER_A)
    cancel = client.post(f"/api/battle/{battle_id}/cancel", headers={"Authorization": "tma fake"})
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


def test_lazy_expiry_updates_status_and_blocks_accept(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    user_b = mgr.get_or_create_telegram_user(TG_USER_B["id"], TG_USER_B["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")
    _seed_pack_and_purchase(mgr, user_b["user_id"], "pack_b")

    _set_user(current_user, TG_USER_A)
    create = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    battle_id = create.json()["battle_id"]

    with mgr._get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE pending_tma_battles SET expires_at=? WHERE battle_id=?",
            ("2000-01-01T00:00:00", battle_id),
        )
        conn.commit()

    status = client.get(f"/api/battle/{battle_id}", headers={"Authorization": "tma fake"})
    assert status.status_code == 200
    assert status.json()["status"] == "expired"

    _set_user(current_user, TG_USER_B)
    accept = client.post(
        f"/api/battle/{battle_id}/accept",
        json={"pack_id": "pack_b"},
        headers={"Authorization": "tma fake"},
    )
    assert accept.status_code == 400
    assert "expired" in accept.text.lower()


def test_db_unique_waiting_pair_key_blocks_duplicate_waiting_rows(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    user_b = mgr.get_or_create_telegram_user(TG_USER_B["id"], TG_USER_B["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")

    _set_user(current_user, TG_USER_A)
    create = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    assert create.status_code == 200

    with mgr._get_connection() as conn:
        c = conn.cursor()
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                "INSERT INTO pending_tma_battles "
                "(battle_id, challenger_id, opponent_id, challenger_pack, wager_tier, status, expires_at, created_at, waiting_pair_key) "
                "VALUES (?, ?, ?, ?, ?, 'waiting', ?, ?, ?)",
                (
                    "DUP123",
                    user_a["user_id"],
                    user_b["user_id"],
                    "pack_a",
                    "casual",
                    "2099-01-01T00:00:00",
                    "2099-01-01T00:00:00",
                    f"{user_a['user_id']}:{user_b['user_id']}",
                ),
            )


def test_challenge_create_idempotency_replays_response(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")

    _set_user(current_user, TG_USER_A)
    headers = {"Authorization": "tma fake", "Idempotency-Key": "create-1"}
    payload = {"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"}
    first = client.post("/api/battle/challenge", json=payload, headers=headers)
    second = client.post("/api/battle/challenge", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_challenge_create_idempotency_payload_conflict_returns_409(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a_alt")

    _set_user(current_user, TG_USER_A)
    headers = {"Authorization": "tma fake", "Idempotency-Key": "create-conflict"}
    first = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers=headers,
    )
    assert first.status_code == 200
    second = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a_alt", "wager_tier": "casual"},
        headers=headers,
    )
    assert second.status_code == 409


def test_accept_decline_cancel_idempotency_replay(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    user_b = mgr.get_or_create_telegram_user(TG_USER_B["id"], TG_USER_B["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")
    _seed_pack_and_purchase(mgr, user_b["user_id"], "pack_b")

    # accept replay
    _set_user(current_user, TG_USER_A)
    create_accept = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    battle_accept = create_accept.json()["battle_id"]
    _set_user(current_user, TG_USER_B)
    accept_headers = {"Authorization": "tma fake", "Idempotency-Key": "accept-1"}
    first_accept = client.post(
        f"/api/battle/{battle_accept}/accept",
        json={"pack_id": "pack_b"},
        headers=accept_headers,
    )
    second_accept = client.post(
        f"/api/battle/{battle_accept}/accept",
        json={"pack_id": "pack_b"},
        headers=accept_headers,
    )
    assert first_accept.status_code == 200
    assert second_accept.status_code == 200
    assert second_accept.json() == first_accept.json()

    # decline replay
    _set_user(current_user, TG_USER_A)
    create_decline = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    battle_decline = create_decline.json()["battle_id"]
    _set_user(current_user, TG_USER_B)
    decline_headers = {"Authorization": "tma fake", "Idempotency-Key": "decline-1"}
    first_decline = client.post(f"/api/battle/{battle_decline}/decline", headers=decline_headers)
    second_decline = client.post(f"/api/battle/{battle_decline}/decline", headers=decline_headers)
    assert first_decline.status_code == 200
    assert second_decline.status_code == 200
    assert second_decline.json() == first_decline.json()

    # cancel replay
    _set_user(current_user, TG_USER_A)
    create_cancel = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    battle_cancel = create_cancel.json()["battle_id"]
    cancel_headers = {"Authorization": "tma fake", "Idempotency-Key": "cancel-1"}
    first_cancel = client.post(f"/api/battle/{battle_cancel}/cancel", headers=cancel_headers)
    second_cancel = client.post(f"/api/battle/{battle_cancel}/cancel", headers=cancel_headers)
    assert first_cancel.status_code == 200
    assert second_cancel.status_code == 200
    assert second_cancel.json() == first_cancel.json()


def test_inbox_returns_incoming_outgoing_waiting_and_recent(battle_env):
    client, mgr, current_user = battle_env
    _seed_telegram_user(mgr, TG_USER_B)
    user_a = mgr.get_or_create_telegram_user(TG_USER_A["id"], TG_USER_A["username"])
    user_b = mgr.get_or_create_telegram_user(TG_USER_B["id"], TG_USER_B["username"])
    _seed_pack_and_purchase(mgr, user_a["user_id"], "pack_a")
    _seed_pack_and_purchase(mgr, user_b["user_id"], "pack_b")

    # A -> B waiting
    _set_user(current_user, TG_USER_A)
    waiting_outgoing = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_B["id"], "pack_id": "pack_a", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    assert waiting_outgoing.status_code == 200
    waiting_battle = waiting_outgoing.json()["battle_id"]

    # B -> A then A declines (terminal incoming for B, outgoing for A)
    _set_user(current_user, TG_USER_B)
    terminal_create = client.post(
        "/api/battle/challenge",
        json={"opponent_telegram_id": TG_USER_A["id"], "pack_id": "pack_b", "wager_tier": "casual"},
        headers={"Authorization": "tma fake"},
    )
    terminal_battle = terminal_create.json()["battle_id"]
    _set_user(current_user, TG_USER_A)
    decline = client.post(f"/api/battle/{terminal_battle}/decline", headers={"Authorization": "tma fake"})
    assert decline.status_code == 200

    # Verify inbox shape and counterpart fields for A
    inbox_a = client.get("/api/battle/inbox", headers={"Authorization": "tma fake"})
    assert inbox_a.status_code == 200
    body_a = inbox_a.json()
    assert {"incoming_waiting", "outgoing_waiting", "incoming_recent", "outgoing_recent"} <= set(body_a.keys())
    assert any(item["battle_id"] == waiting_battle for item in body_a["outgoing_waiting"])
    assert any(item["battle_id"] == terminal_battle for item in body_a["incoming_recent"])
    sample = body_a["outgoing_waiting"][0]
    assert "counterpart" in sample and "telegram_id" in sample["counterpart"]

    # Verify B also receives corresponding sections
    _set_user(current_user, TG_USER_B)
    inbox_b = client.get("/api/battle/inbox", headers={"Authorization": "tma fake"})
    assert inbox_b.status_code == 200
    body_b = inbox_b.json()
    assert any(item["battle_id"] == waiting_battle for item in body_b["incoming_waiting"])
    assert any(item["battle_id"] == terminal_battle for item in body_b["outgoing_recent"])
