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
    user = db.get_or_create_telegram_user(111, "linker")
    code = db.generate_tma_link_code(user["user_id"])
    assert len(code) == 6
    assert code.isalnum()


def test_consume_link_code(db):
    """Consuming a valid code merges discord_id into telegram user's row."""
    tg_user = db.get_or_create_telegram_user(222, "tguser")
    code = db.generate_tma_link_code(tg_user["user_id"])
    result = db.consume_tma_link_code(code, discord_id=9876543210)
    assert result["success"] is True
    assert result["user_id"] == tg_user["user_id"]


def test_consume_link_code_expired(db):
    """Invalid codes fail gracefully."""
    result = db.consume_tma_link_code("XXXXXX", discord_id=999)
    assert result["success"] is False
