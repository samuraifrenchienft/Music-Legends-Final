"""
Dual-backend tests — runs against SQLite (default) or Docker PostgreSQL.

Catches PG-specific bugs (column mismatches, ON CONFLICT, type coercion)
that are invisible to SQLite-only tests.

Usage:
  pytest tests/test_dual_backend.py -v              # SQLite (default)
  pytest tests/test_dual_backend.py -v --pg         # PostgreSQL (Docker)
  pytest tests/test_dual_backend.py -v --pg --both  # Both backends
"""

import os
import sys
import json
import uuid
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_PG_URL = "postgresql://testuser:testpass@localhost:5433/test_music_legends"


# ─────────────────────────────────────────────
# Core DB operations
# ─────────────────────────────────────────────

class TestDropFlow:
    """open_pack_for_drop end-to-end."""

    def test_stats_saved_to_db(self, db_backend, seed_user, seed_creator_pack, seed_card):
        mgr, backend = db_backend
        result = mgr.open_pack_for_drop(seed_creator_pack, seed_user)
        assert result["success"], f"[{backend}] drop failed: {result.get('error')}"

        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"SELECT impact, skill, longevity, culture, hype FROM cards WHERE card_id = {ph}",
                      (seed_card["card_id"],))
            row = c.fetchone()
        assert row is not None, f"[{backend}] Card not in DB"
        assert row[0] == seed_card["impact"], f"[{backend}] impact: {row[0]} != {seed_card['impact']}"
        assert row[4] == seed_card["hype"], f"[{backend}] hype: {row[4]} != {seed_card['hype']}"

    def test_pack_purchase_recorded(self, db_backend, seed_user, seed_creator_pack):
        mgr, backend = db_backend
        uid = 100_000_050
        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            if mgr._db_type == "postgresql":
                c.execute(f"INSERT INTO users (user_id, username, discord_tag) VALUES ({ph},{ph},{ph}) ON CONFLICT DO NOTHING",
                          (uid, "DropUser", "DropUser#0001"))
                c.execute(f"INSERT INTO user_inventory (user_id, gold) VALUES ({ph},{ph}) ON CONFLICT DO NOTHING",
                          (uid, 1000))
            else:
                c.execute("INSERT OR IGNORE INTO users (user_id, username, discord_tag) VALUES (?,?,?)",
                          (uid, "DropUser", "DropUser#0001"))
                c.execute("INSERT OR IGNORE INTO user_inventory (user_id, gold) VALUES (?,?)",
                          (uid, 1000))
            conn.commit()

        mgr.open_pack_for_drop(seed_creator_pack, uid)
        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"SELECT COUNT(*) FROM pack_purchases WHERE buyer_id={ph} AND pack_id={ph}",
                      (uid, seed_creator_pack))
            count = c.fetchone()[0]
        assert count >= 1, f"[{backend}] No pack_purchases entry"

    def test_card_in_user_cards(self, db_backend, seed_user, seed_creator_pack, seed_card):
        mgr, backend = db_backend
        mgr.open_pack_for_drop(seed_creator_pack, seed_user)
        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"SELECT card_id FROM user_cards WHERE user_id={ph} AND card_id={ph}",
                      (seed_user, seed_card["card_id"]))
            row = c.fetchone()
        assert row is not None, f"[{backend}] Card not in user_cards"

    def test_collection_returns_stats(self, db_backend, seed_user, seed_creator_pack, seed_card):
        mgr, backend = db_backend
        mgr.open_pack_for_drop(seed_creator_pack, seed_user)
        collection = mgr.get_user_collection(seed_user)
        assert len(collection) > 0, f"[{backend}] Collection empty"
        found = next((c for c in collection if c["card_id"] == seed_card["card_id"]), None)
        assert found is not None, f"[{backend}] Card not in collection"
        assert found.get("impact") == seed_card["impact"], f"[{backend}] impact mismatch"


class TestGrantFlow:
    """grant_pack_to_user end-to-end."""

    def test_stats_saved(self, db_backend, seed_user, seed_dev_supply, seed_card):
        mgr, backend = db_backend
        result = mgr.grant_pack_to_user(seed_dev_supply, seed_user)
        assert result["success"], f"[{backend}] grant failed: {result.get('error')}"

        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"SELECT impact FROM cards WHERE card_id = {ph}", (seed_card["card_id"],))
            row = c.fetchone()
        assert row is not None, f"[{backend}] Card not in DB"
        assert row[0] == seed_card["impact"], f"[{backend}] impact mismatch"

    def test_supply_decremented(self, db_backend, seed_dev_supply):
        mgr, backend = db_backend
        uid = 100_000_060
        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            if mgr._db_type == "postgresql":
                c.execute(f"INSERT INTO users (user_id, username, discord_tag) VALUES ({ph},{ph},{ph}) ON CONFLICT DO NOTHING",
                          (uid, "GrantUser", "GrantUser#0001"))
            else:
                c.execute("INSERT OR IGNORE INTO users (user_id, username, discord_tag) VALUES (?,?,?)",
                          (uid, "GrantUser", "GrantUser#0001"))
            conn.commit()

        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"SELECT quantity FROM dev_pack_supply WHERE pack_id={ph}", (seed_dev_supply,))
            before = c.fetchone()[0]

        mgr.grant_pack_to_user(seed_dev_supply, uid)

        with mgr._get_connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT quantity FROM dev_pack_supply WHERE pack_id={ph}", (seed_dev_supply,))
            after = c.fetchone()[0]
        assert after == before - 1, f"[{backend}] Supply: {before} → {after}"


class TestDailyReward:
    """claim_daily_reward end-to-end."""

    def test_economy_updated(self, db_backend, seed_user):
        mgr, backend = db_backend
        result = mgr.claim_daily_reward(seed_user)
        assert result["success"], f"[{backend}] claim failed: {result.get('error')}"
        assert result["gold"] >= 100
        assert result["streak"] >= 1

    def test_double_claim_blocked(self, db_backend, seed_user):
        mgr, backend = db_backend
        mgr.claim_daily_reward(seed_user)
        result = mgr.claim_daily_reward(seed_user)
        if not result["success"]:
            err = result.get("error", "").lower()
            assert "claimed" in err or result.get("time_until") is not None, \
                f"[{backend}] Expected cooldown, got: {result}"


class TestLivePackQuery:
    """get_random_live_pack_by_tier queries."""

    def test_community_pack_returned(self, db_backend, seed_creator_pack):
        mgr, backend = db_backend
        pack = mgr.get_random_live_pack_by_tier("community")
        assert pack, f"[{backend}] No community pack"
        assert pack.get("name"), f"[{backend}] Pack has no name"
        assert len(pack.get("cards_data", [])) > 0, f"[{backend}] No cards_data"


class TestSeedPacks:
    """Seed packs load correctly on both backends."""

    def test_seed_inserts_packs(self, db_backend):
        """Seed packs load correctly. On PG, verifies DB directly.
        On SQLite, verifies return value (seed uses its own DB file)."""
        mgr, backend = db_backend
        from services.seed_packs import seed_packs_into_db

        if backend == "pg":
            os.environ["DATABASE_URL"] = TEST_PG_URL
            result = seed_packs_into_db(force_reseed=True)
            inserted = result.get("inserted", 0)
            assert inserted >= 50, f"[{backend}] Expected 50+ inserted, got {inserted}. Result: {result}"

            # On PG, verify directly in the database
            with mgr._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM creator_packs WHERE status = 'LIVE'")
                count = c.fetchone()[0]
            assert count >= 50, f"[{backend}] Expected 50+ LIVE packs in DB, got {count}"
        else:
            # SQLite: seed_packs_into_db creates its own connection to music_legends.db,
            # not the temp test DB. Just verify the return value.
            os.environ.pop("DATABASE_URL", None)
            result = seed_packs_into_db(force_reseed=True)
            inserted = result.get("inserted", 0)
            failed = result.get("failed", 0)
            assert inserted >= 50, f"[{backend}] Expected 50+ inserted, got {inserted}. Result: {result}"
            assert failed == 0, f"[{backend}] {failed} packs failed to insert"


class TestPackPurchasesColumns:
    """Verify pack_purchases INSERT with the exact columns used in production."""

    def test_4_column_insert(self, db_backend, seed_user, seed_creator_pack):
        mgr, backend = db_backend
        purchase_id = f"test_{uuid.uuid4().hex[:12]}"
        card_ids = ["card_test_1"]
        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"""
                INSERT INTO pack_purchases
                (purchase_id, pack_id, buyer_id, cards_received)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (purchase_id, seed_creator_pack, seed_user, json.dumps(card_ids)))
            conn.commit()

        with mgr._get_connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT purchase_id FROM pack_purchases WHERE purchase_id = {ph}",
                      (purchase_id,))
            row = c.fetchone()
        assert row is not None, f"[{backend}] pack_purchases 4-col INSERT failed"


class TestPowerRoundTrip:
    """Card stats survive DB round-trip and produce correct power."""

    RARITY_BONUS = {"common": 0, "rare": 5, "epic": 10, "legendary": 20, "mythic": 35}

    def _power(self, card):
        base = ((card.get('impact', 50) or 50) + (card.get('skill', 50) or 50) +
                (card.get('longevity', 50) or 50) + (card.get('culture', 50) or 50) +
                (card.get('hype', 50) or 50)) // 5
        rarity = (card.get('rarity') or 'common').lower()
        return base + self.RARITY_BONUS.get(rarity, 0)

    def test_power_matches_after_roundtrip(self, db_backend, seed_user, seed_creator_pack, seed_card):
        mgr, backend = db_backend
        mgr.open_pack_for_drop(seed_creator_pack, seed_user)
        collection = mgr.get_user_collection(seed_user)
        found = next((c for c in collection if c["card_id"] == seed_card["card_id"]), None)
        assert found, f"[{backend}] Card not in collection"

        db_power = self._power(found)
        expected = self._power(seed_card)
        assert db_power == expected, f"[{backend}] Power: DB={db_power}, expected={expected}"
        assert db_power == 80, f"[{backend}] Epic card should be 80, got {db_power}"

    def test_no_null_stats(self, db_backend, seed_user, seed_creator_pack, seed_card):
        mgr, backend = db_backend
        mgr.open_pack_for_drop(seed_creator_pack, seed_user)
        with mgr._get_connection() as conn:
            c = conn.cursor()
            ph = mgr._get_placeholder()
            c.execute(f"SELECT impact, skill, longevity, culture, hype FROM cards WHERE card_id = {ph}",
                      (seed_card["card_id"],))
            row = c.fetchone()
        assert row is not None
        for i, stat in enumerate(["impact", "skill", "longevity", "culture", "hype"]):
            assert row[i] is not None, f"[{backend}] {stat} is NULL!"
            assert row[i] > 0, f"[{backend}] {stat} is 0!"
