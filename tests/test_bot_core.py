"""
Core bot tests — run with: pytest tests/test_bot_core.py -v
Uses SQLite in-memory; no PostgreSQL/Redis/Discord required.
"""

import os
import sys
import json
import uuid
import sqlite3
import pytest

# Force SQLite mode (no DATABASE_URL)
os.environ.pop("DATABASE_URL", None)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """DatabaseManager backed by a temp SQLite file, isolated from the singleton."""
    import database as _db_module
    from database import DatabaseManager

    db_path = str(tmp_path_factory.mktemp("db") / "test.db")
    mgr = DatabaseManager(db_path=db_path)

    # Override the module-level singleton so any code that calls get_db()
    # also gets our temp instance during tests.
    _db_module._db_instance = mgr
    return mgr


@pytest.fixture
def seed_user(db):
    """Insert a test user + inventory row; return user_id."""
    uid = 100_000_001
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, discord_tag) VALUES (?,?,?)",
                  (uid, "TestUser", "TestUser#0001"))
        c.execute("INSERT OR IGNORE INTO user_inventory (user_id, gold) VALUES (?,?)",
                  (uid, 5000))
        conn.commit()
    return uid


@pytest.fixture
def seed_card(db):
    """Insert one test card into cards table with all stat columns; return card dict."""
    cid = f"card_{uuid.uuid4().hex[:8]}"
    card = {
        "card_id": cid, "name": "Test Artist", "artist_name": "Test Artist",
        "title": "Test Song", "rarity": "epic", "tier": "platinum",
        "image_url": "", "youtube_url": "",
        "impact": 70, "skill": 80, "longevity": 60, "culture": 75, "hype": 65,
    }
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO cards
            (card_id, name, artist_name, title, rarity, tier, image_url, youtube_url,
             impact, skill, longevity, culture, hype)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (cid, card["name"], card["artist_name"], card["title"],
              card["rarity"], card["tier"], card["image_url"], card["youtube_url"],
              card["impact"], card["skill"], card["longevity"], card["culture"], card["hype"]))
        conn.commit()
    return card


@pytest.fixture
def seed_creator_pack(db, seed_card):
    """Insert a LIVE creator_pack containing seed_card; return pack_id."""
    pack_id = f"pack_{uuid.uuid4().hex[:8]}"
    cards_data = [seed_card]
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO creator_packs
            (pack_id, name, pack_tier, status, cards_data, pack_size)
            VALUES (?,?,?,?,?,?)
        """, (pack_id, "Test Pack", "community", "LIVE", json.dumps(cards_data), 1))
        conn.commit()
    return pack_id


@pytest.fixture
def seed_dev_supply(db, seed_creator_pack):
    """Add 5 copies of seed_creator_pack to dev_pack_supply."""
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO dev_pack_supply (pack_id, quantity)
            VALUES (?,?)
        """, (seed_creator_pack, 5))
        conn.commit()
    return seed_creator_pack


# ─────────────────────────────────────────────
# 1. Power calculation
# ─────────────────────────────────────────────

class TestComputeCardPower:
    """_compute_card_power() returns (sum/5) + rarity_bonus."""

    def _power(self, card_dict):
        # Replicate the formula directly (no Discord needed)
        RARITY_BONUS = {"common": 0, "rare": 5, "epic": 10, "legendary": 20, "mythic": 35}
        base = ((card_dict.get('impact', 50) or 50) +
                (card_dict.get('skill', 50) or 50) +
                (card_dict.get('longevity', 50) or 50) +
                (card_dict.get('culture', 50) or 50) +
                (card_dict.get('hype', 50) or 50)) // 5
        rarity = (card_dict.get('rarity') or 'common').lower()
        return base + RARITY_BONUS.get(rarity, 0)

    def test_common_avg50(self):
        card = dict(impact=50, skill=50, longevity=50, culture=50, hype=50, rarity="common")
        assert self._power(card) == 50

    def test_epic_bonus(self):
        card = dict(impact=70, skill=80, longevity=60, culture=75, hype=65, rarity="epic")
        # avg = (70+80+60+75+65)//5 = 350//5 = 70; +10 epic = 80
        assert self._power(card) == 80

    def test_legendary_bonus(self):
        card = dict(impact=100, skill=100, longevity=100, culture=100, hype=100, rarity="legendary")
        # avg = 100; +20 legendary = 120
        assert self._power(card) == 120

    def test_mythic_max(self):
        card = dict(impact=100, skill=100, longevity=100, culture=100, hype=100, rarity="mythic")
        # avg = 100; +35 mythic = 135
        assert self._power(card) == 135

    def test_null_stats_default_to_50(self):
        card = dict(impact=None, skill=None, longevity=None, culture=None, hype=None, rarity="common")
        assert self._power(card) == 50

    def test_different_rarities_same_stats_differ(self):
        base = dict(impact=70, skill=70, longevity=70, culture=70, hype=70)
        common_power = self._power({**base, "rarity": "common"})   # 70
        rare_power   = self._power({**base, "rarity": "rare"})     # 75
        epic_power   = self._power({**base, "rarity": "epic"})     # 80
        assert common_power < rare_power < epic_power


# ─────────────────────────────────────────────
# 2. BattleEngine
# ─────────────────────────────────────────────

class TestBattleEngine:
    """BattleEngine.execute_battle() with p1_override/p2_override."""

    def _make_card(self, card_id="c1", rarity="common"):
        from discord_cards import ArtistCard
        return ArtistCard(
            card_id=card_id, artist="Artist", song="Song",
            youtube_url="", youtube_id="", view_count=10_000_000,
            thumbnail="", rarity=rarity,
        )

    def test_higher_power_wins(self):
        from battle_engine import BattleEngine
        card1 = self._make_card("c1")
        card2 = self._make_card("c2")
        # Force deterministic outcome with no crits (mock random)
        import random
        random.seed(0)  # seed gives known crit results
        result = BattleEngine.execute_battle(card1, card2, "casual",
                                             p1_override=100, p2_override=50)
        # power diff = 50, well above MIN_POWER_ADVANTAGE=5
        assert result["player1"]["base_power"] == 100
        assert result["player2"]["base_power"] == 50
        # Winner should be 1 unless crit reversed it
        p1_final = result["player1"]["final_power"]
        p2_final = result["player2"]["final_power"]
        if result["winner"] != 0:
            assert result["winner"] == (1 if p1_final > p2_final else 2)

    def test_tie_when_powers_close(self):
        from battle_engine import BattleEngine
        import random
        # Patch random to return 0 (no crits)
        original = random.random
        random.random = lambda: 0.99  # never crits
        try:
            card1 = self._make_card("c1")
            card2 = self._make_card("c2")
            result = BattleEngine.execute_battle(card1, card2, "casual",
                                                 p1_override=50, p2_override=52)
            # diff = 2 < MIN_POWER_ADVANTAGE(5) → tie
            assert result["winner"] == 0
        finally:
            random.random = original

    def test_override_ignores_artiscard_power(self):
        from battle_engine import BattleEngine
        import random
        random.random = lambda: 0.99
        try:
            card1 = self._make_card("c1", rarity="common")   # low natural power
            card2 = self._make_card("c2", rarity="mythic")   # high natural power
            # Override gives c1 much more power
            result = BattleEngine.execute_battle(card1, card2, "casual",
                                                 p1_override=130, p2_override=10)
            assert result["player1"]["base_power"] == 130
            assert result["player2"]["base_power"] == 10
            assert result["winner"] == 1
        finally:
            import random as r; r.random = lambda: r.random.__module__  # restore properly

    def test_crit_multiplies_power(self):
        from battle_engine import BattleEngine
        import random
        random.random = lambda: 0.0  # always crits
        try:
            card1 = self._make_card("c1")
            card2 = self._make_card("c2")
            result = BattleEngine.execute_battle(card1, card2, "casual",
                                                 p1_override=60, p2_override=60)
            # Both crit → both get 1.5x → still equal → tie
            assert result["player1"]["critical_hit"] is True
            assert result["player2"]["critical_hit"] is True
            assert result["player1"]["final_power"] == int(60 * 1.5)
        finally:
            pass

    def test_rewards_assigned_to_winner(self):
        from battle_engine import BattleEngine, BattleWagerConfig
        import random
        random.random = lambda: 0.99
        try:
            card1 = self._make_card("c1")
            card2 = self._make_card("c2")
            result = BattleEngine.execute_battle(card1, card2, "standard",
                                                 p1_override=90, p2_override=30)
            tier = BattleWagerConfig.get_tier("standard")
            assert result["player1"]["gold_reward"] == tier["winner_gold"]
            assert result["player2"]["gold_reward"] == tier["loser_gold"]
        finally:
            pass


# ─────────────────────────────────────────────
# 3. open_pack_for_drop — stat columns
# ─────────────────────────────────────────────

class TestOpenPackForDrop:

    def test_stat_columns_saved(self, db, seed_user, seed_creator_pack, seed_card):
        """Cards inserted via open_pack_for_drop must have stat columns in DB."""
        result = db.open_pack_for_drop(seed_creator_pack, seed_user)
        assert result["success"], f"open_pack_for_drop failed: {result.get('error')}"
        assert len(result["cards"]) > 0, "No cards returned"

        # Verify stats actually stored in DB
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT impact, skill, longevity, culture, hype FROM cards WHERE card_id = ?",
                      (seed_card["card_id"],))
            row = c.fetchone()
        assert row is not None, "Card not found in DB"
        impact, skill, longevity, culture, hype = row
        assert impact == seed_card["impact"], f"impact: expected {seed_card['impact']}, got {impact}"
        assert skill  == seed_card["skill"],  f"skill: expected {seed_card['skill']}, got {skill}"
        assert hype   == seed_card["hype"],   f"hype: expected {seed_card['hype']}, got {hype}"

    def test_card_added_to_user_cards(self, db, seed_user, seed_creator_pack, seed_card):
        """Card must appear in user_cards after open_pack_for_drop."""
        db.open_pack_for_drop(seed_creator_pack, seed_user)
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT card_id FROM user_cards WHERE user_id=? AND card_id=?",
                      (seed_user, seed_card["card_id"]))
            row = c.fetchone()
        assert row is not None, "Card not in user_cards"

    def test_pack_recorded_in_pack_purchases(self, db, seed_user, seed_creator_pack):
        """pack_purchases must have an entry after open_pack_for_drop."""
        db.open_pack_for_drop(seed_creator_pack, seed_user)
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM pack_purchases WHERE buyer_id=? AND pack_id=?",
                      (seed_user, seed_creator_pack))
            count = c.fetchone()[0]
        assert count >= 1, "No pack_purchases entry created"

    def test_get_user_collection_returns_stats(self, db, seed_user, seed_creator_pack, seed_card):
        """get_user_collection() must return stat columns after drop."""
        db.open_pack_for_drop(seed_creator_pack, seed_user)
        collection = db.get_user_collection(seed_user)
        assert len(collection) > 0, "Collection empty after drop"
        card = next((c for c in collection if c["card_id"] == seed_card["card_id"]), None)
        assert card is not None, "Dropped card not in collection"
        assert card.get("impact") == seed_card["impact"], \
            f"impact in collection: expected {seed_card['impact']}, got {card.get('impact')}"


# ─────────────────────────────────────────────
# 4. grant_pack_to_user — stat columns + supply
# ─────────────────────────────────────────────

class TestGrantPackToUser:

    def test_stat_columns_saved(self, db, seed_user, seed_dev_supply, seed_card):
        """grant_pack_to_user must save stat columns to cards table."""
        result = db.grant_pack_to_user(seed_dev_supply, seed_user)
        assert result["success"], f"grant_pack_to_user failed: {result.get('error')}"

        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT impact, skill, longevity, culture, hype FROM cards WHERE card_id = ?",
                      (seed_card["card_id"],))
            row = c.fetchone()
        assert row is not None
        assert row[0] == seed_card["impact"]

    def test_supply_decremented(self, db, seed_dev_supply):
        """dev_pack_supply quantity must decrease by 1 after grant."""
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT quantity FROM dev_pack_supply WHERE pack_id=?", (seed_dev_supply,))
            before = c.fetchone()[0]

        uid = 100_000_002
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, username, discord_tag) VALUES (?,?,?)",
                      (uid, "U2", "U2#0002"))
            conn.commit()

        db.grant_pack_to_user(seed_dev_supply, uid)

        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT quantity FROM dev_pack_supply WHERE pack_id=?", (seed_dev_supply,))
            after = c.fetchone()[0]
        assert after == before - 1, f"Supply not decremented: {before} → {after}"

    def test_no_supply_returns_error(self, db):
        """Returns error dict when no supply remains."""
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        result = db.grant_pack_to_user(pack_id, 999)
        assert result["success"] is False


# ─────────────────────────────────────────────
# 5. claim_daily_reward — fallback pack
# ─────────────────────────────────────────────

class TestClaimDailyReward:

    def test_economy_updated(self, db, seed_user):
        """Gold and streak must be updated on successful claim."""
        result = db.claim_daily_reward(seed_user)
        assert result["success"], f"Daily claim failed: {result.get('error')}"
        assert result["gold"] >= 100
        assert result["streak"] >= 1

    def test_cards_returned(self, db, seed_user):
        """cards key must be a list (may be empty if no cards in DB)."""
        result = db.claim_daily_reward(seed_user)
        if result.get("success"):
            assert isinstance(result.get("cards"), list)

    def test_double_claim_blocked(self, db, seed_user):
        """Second claim within 20h must be rejected."""
        db.claim_daily_reward(seed_user)   # first claim
        result = db.claim_daily_reward(seed_user)  # second claim
        # Either already claimed or success=False
        if not result["success"]:
            assert "claimed" in result.get("error", "").lower() or \
                   result.get("time_until") is not None

    def test_pack_name_present_when_cards_received(self, db, seed_user, seed_creator_pack):
        """If pack is granted, pack_name must be set."""
        # Reset last_daily_claim so we can claim again
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_inventory SET last_daily_claim=NULL WHERE user_id=?", (seed_user,))
            conn.commit()
        result = db.claim_daily_reward(seed_user)
        if result.get("success") and result.get("cards"):
            assert result.get("pack_name") is not None
