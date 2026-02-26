'''
import aiosqlite
import psycopg2
import psycopg2.extras
import json
import os
from contextlib import contextmanager
from typing import Optional, Tuple, List, Dict, Any

class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_type: str = "sqlite", dsn: Optional[str] = None):
        if hasattr(self, 'conn') and self.conn:
            return

        self.db_type = db_type
        if db_type == "sqlite":
            self.db_name = dsn or "music_legends.db"
            self._init_db_sqlite()
        elif db_type == "postgres":
            if dsn is None:
                raise ValueError("DSN is required for PostgreSQL connection")
            self.dsn = dsn
            self._init_db_postgres()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @contextmanager
    def _get_connection(self):
        """Provides a database connection."""
        if self.db_type == "sqlite":
            conn = aiosqlite.connect(self.db_name)
            try:
                yield conn
            finally:
                conn.close()
        else: # postgres
            conn = psycopg2.connect(self.dsn)
            try:
                yield conn
            finally:
                conn.close()

    def _init_db_sqlite(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    gold INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    telegram_id BIGINT UNIQUE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    artist TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id INTEGER,
                    card_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, card_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packs (
                    pack_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_packs (
                    user_id INTEGER,
                    pack_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, pack_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id BIGINT NOT NULL,
                    user2_id BIGINT NOT NULL,
                    user1_cards TEXT,
                    user2_cards TEXT,
                    user1_gold INTEGER DEFAULT 0,
                    user2_gold INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (user1_id) REFERENCES users(user_id),
                    FOREIGN KEY (user2_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_listings (
                    listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_id BIGINT NOT NULL,
                    card_id TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    listed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (seller_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_tma_battles (
                    user_id BIGINT PRIMARY KEY,
                    deck TEXT NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_progress (
                    user_id BIGINT NOT NULL,
                    season_id INTEGER NOT NULL,
                    xp INTEGER DEFAULT 0,
                    tier INTEGER DEFAULT 1,
                    premium_purchased BOOLEAN DEFAULT FALSE,
                    claimed_tiers TEXT,
                    PRIMARY KEY (user_id, season_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vip_status (
                    user_id BIGINT PRIMARY KEY,
                    is_vip BOOLEAN DEFAULT FALSE,
                    vip_tier INTEGER DEFAULT 0,
                    expiration_date DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_created_packs (
                    pack_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    cards TEXT NOT NULL,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            """)
            conn.commit()

    def _init_db_postgres(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGSERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    gold INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    telegram_id BIGINT UNIQUE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    artist TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id BIGINT,
                    card_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, card_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packs (
                    pack_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_packs (
                    user_id BIGINT,
                    pack_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, pack_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id SERIAL PRIMARY KEY,
                    user1_id BIGINT NOT NULL,
                    user2_id BIGINT NOT NULL,
                    user1_cards JSONB,
                    user2_cards JSONB,
                    user1_gold INTEGER DEFAULT 0,
                    user2_gold INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (user1_id) REFERENCES users(user_id),
                    FOREIGN KEY (user2_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    history_id SERIAL PRIMARY KEY,
                    trade_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_listings (
                    listing_id SERIAL PRIMARY KEY,
                    seller_id BIGINT NOT NULL,
                    card_id TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (seller_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_tma_battles (
                    user_id BIGINT PRIMARY KEY,
                    deck JSONB NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_progress (
                    user_id BIGINT NOT NULL,
                    season_id INTEGER NOT NULL,
                    xp INTEGER DEFAULT 0,
                    tier INTEGER DEFAULT 1,
                    premium_purchased BOOLEAN DEFAULT FALSE,
                    claimed_tiers JSONB,
                    PRIMARY KEY (user_id, season_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vip_status (
                    user_id BIGINT PRIMARY KEY,
                    is_vip BOOLEAN DEFAULT FALSE,
                    vip_tier INTEGER DEFAULT 0,
                    expiration_date TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_created_packs (
                    pack_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    cards JSONB NOT NULL,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            """)
            conn.commit()

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            self.conn = None

    def get_or_create_user(self, user_id: int, username: str) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return dict(user)
            else:
                cursor.execute(
                    "INSERT INTO users (user_id, username) VALUES (%s, %s) RETURNING *",
                    (user_id, username)
                )
                user = cursor.fetchone()
                conn.commit()
                return dict(user)

    def get_or_create_telegram_user(self, telegram_id: int, username: str) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
            user = cursor.fetchone()
            if user:
                return dict(user)
            else:
                cursor.execute(
                    "INSERT INTO users (username, telegram_id) VALUES (%s, %s) RETURNING *",
                    (username, telegram_id)
                )
                user = cursor.fetchone()
                conn.commit()
                return dict(user)

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
            user = cursor.fetchone()
            return dict(user) if user else None

    def update_user_gold(self, user_id: int, amount: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET gold = gold + %s WHERE user_id = %s", (amount, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_user_inventory(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT card_id, quantity FROM user_inventory WHERE user_id = %s", (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def add_card_to_inventory(self, user_id: int, card_id: str, quantity: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_inventory (user_id, card_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, card_id)
                DO UPDATE SET quantity = user_inventory.quantity + EXCLUDED.quantity;
            """, (user_id, card_id, quantity))
            conn.commit()

    def remove_card_from_inventory(self, user_id: int, card_id: str, quantity: int = 1) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = %s AND card_id = %s", (user_id, card_id))
            current_quantity = cursor.fetchone()
            if not current_quantity or current_quantity[0] < quantity:
                return False # Not enough cards

            if current_quantity[0] == quantity:
                cursor.execute("DELETE FROM user_inventory WHERE user_id = %s AND card_id = %s", (user_id, card_id))
            else:
                cursor.execute("UPDATE user_inventory SET quantity = quantity - %s WHERE user_id = %s AND card_id = %s", (quantity, user_id, card_id))
            conn.commit()
            return True

    def get_pack_by_id(self, pack_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM packs WHERE pack_id = %s", (pack_id,))
            pack = cursor.fetchone()
            return dict(pack) if pack else None

    def get_user_packs(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT pack_id, quantity FROM user_packs WHERE user_id = %s", (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def add_pack_to_user(self, user_id: int, pack_id: str, quantity: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_packs (user_id, pack_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, pack_id)
                DO UPDATE SET quantity = user_packs.quantity + EXCLUDED.quantity;
            """, (user_id, pack_id, quantity))
            conn.commit()

    def remove_pack_from_user(self, user_id: int, pack_id: str, quantity: int = 1) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM user_packs WHERE user_id = %s AND pack_id = %s", (user_id, pack_id))
            current_quantity = cursor.fetchone()
            if not current_quantity or current_quantity[0] < quantity:
                return False

            if current_quantity[0] == quantity:
                cursor.execute("DELETE FROM user_packs WHERE user_id = %s AND pack_id = %s", (user_id, pack_id))
            else:
                cursor.execute("UPDATE user_packs SET quantity = quantity - %s WHERE user_id = %s AND pack_id = %s", (quantity, user_id, pack_id))
            conn.commit()
            return True

    def create_trade(self, user1_id: int, user2_id: int, user1_cards: List[str], user2_cards: List[str], user1_gold: int, user2_gold: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            user1_cards_json = json.dumps(user1_cards)
            user2_cards_json = json.dumps(user2_cards)
            cursor.execute(
                "INSERT INTO trades (user1_id, user2_id, user1_cards, user2_cards, user1_gold, user2_gold) VALUES (%s, %s, %s, %s, %s, %s) RETURNING trade_id",
                (user1_id, user2_id, user1_cards_json, user2_cards_json, user1_gold, user2_gold)
            )
            trade_id = cursor.fetchone()[0]
            conn.commit()
            return trade_id

    def get_user_trades(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM trades WHERE (user1_id = %s OR user2_id = %s) AND status = 'pending'", (user_id, user_id))
            return [dict(row) for row in cursor.fetchall()]

    def accept_trade(self, trade_id: int, accepting_user_id: int) -> Tuple[bool, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM trades WHERE trade_id = %s AND status = 'pending'", (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "Trade not found or not pending."
            if trade['user2_id'] != accepting_user_id:
                return False, "You are not authorized to accept this trade."

            # Process the trade
            # This should be a transaction
            try:
                # Gold transfer
                self.update_user_gold(trade['user1_id'], trade['user2_gold'] - trade['user1_gold'])
                self.update_user_gold(trade['user2_id'], trade['user1_gold'] - trade['user2_gold'])

                # Card transfers
                user1_cards = json.loads(trade['user1_cards'])
                user2_cards = json.loads(trade['user2_cards'])

                for card_id in user1_cards:
                    if not self.remove_card_from_inventory(trade['user1_id'], card_id):
                        raise Exception(f"User {trade['user1_id']} does not have card {card_id}")
                    self.add_card_to_inventory(trade['user2_id'], card_id)

                for card_id in user2_cards:
                    if not self.remove_card_from_inventory(trade['user2_id'], card_id):
                        raise Exception(f"User {trade['user2_id']} does not have card {card_id}")
                    self.add_card_to_inventory(trade['user1_id'], card_id)

                cursor.execute("UPDATE trades SET status = 'accepted' WHERE trade_id = %s", (trade_id,))
                conn.commit()
                return True, "Trade accepted successfully."
            except Exception as e:
                conn.rollback()
                return False, f"An error occurred: {e}"

    def cancel_trade(self, trade_id: int, cancelling_user_id: int) -> Tuple[bool, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM trades WHERE trade_id = %s AND status = 'pending'", (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "Trade not found or not pending."
            if trade['user1_id'] != cancelling_user_id and trade['user2_id'] != cancelling_user_id:
                return False, "You are not part of this trade."

            cursor.execute("UPDATE trades SET status = 'cancelled' WHERE trade_id = %s", (trade_id,))
            conn.commit()
            return True, "Trade cancelled."

    def get_marketplace_listings(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM marketplace_listings WHERE status = 'active'")
            return [dict(row) for row in cursor.fetchall()]

    def create_marketplace_listing(self, seller_id: int, card_id: str, price: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # First, check if the user has the card
            if not self.remove_card_from_inventory(seller_id, card_id):
                raise ValueError("Seller does not own this card or has insufficient quantity.")

            cursor.execute(
                "INSERT INTO marketplace_listings (seller_id, card_id, price) VALUES (%s, %s, %s) RETURNING listing_id",
                (seller_id, card_id, price)
            )
            listing_id = cursor.fetchone()[0]
            conn.commit()
            return listing_id

    def purchase_marketplace_listing(self, listing_id: int, buyer_id: int) -> Tuple[bool, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM marketplace_listings WHERE listing_id = %s AND status = 'active'", (listing_id,))
            listing = cursor.fetchone()

            if not listing:
                return False, "Listing not found or not active."

            buyer = self.get_user_by_id(buyer_id)
            if not buyer or buyer['gold'] < listing['price']:
                return False, "Insufficient gold."

            try:
                self.update_user_gold(buyer_id, -listing['price'])
                self.update_user_gold(listing['seller_id'], listing['price'])
                self.add_card_to_inventory(buyer_id, listing['card_id'])

                cursor.execute("UPDATE marketplace_listings SET status = 'sold' WHERE listing_id = %s", (listing_id,))
                conn.commit()
                return True, "Purchase successful."
            except Exception as e:
                conn.rollback()
                return False, f"An error occurred: {e}"

    def get_pending_tma_battle(self, user_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM pending_tma_battles WHERE user_id = %s", (user_id,))
            battle = cursor.fetchone()
            if battle:
                battle_dict = dict(battle)
                battle_dict['deck'] = json.loads(battle_dict['deck'])
                return battle_dict
            return None

    def create_pending_tma_battle(self, user_id: int, deck: List[str], bet_amount: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            deck_json = json.dumps(deck)
            cursor.execute(
                "INSERT INTO pending_tma_battles (user_id, deck, bet_amount) VALUES (%s, %s, %s)",
                (user_id, deck_json, bet_amount)
            )
            conn.commit()

    def delete_pending_tma_battle(self, user_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pending_tma_battles WHERE user_id = %s", (user_id,))
            conn.commit()

    def get_battle_pass_status(self, user_id: int, season_id: int) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM season_progress WHERE user_id = %s AND season_id = %s", (user_id, season_id))
            status = cursor.fetchone()
            if status:
                status_dict = dict(status)
                status_dict['claimed_tiers'] = json.loads(status_dict['claimed_tiers']) if status_dict['claimed_tiers'] else []
                return status_dict
            else:
                # Create a new entry if it doesn't exist
                cursor.execute(
                    "INSERT INTO season_progress (user_id, season_id, claimed_tiers) VALUES (%s, %s, %s)",
                    (user_id, season_id, json.dumps([]))
                )
                conn.commit()
                return {
                    "user_id": user_id,
                    "season_id": season_id,
                    "xp": 0,
                    "tier": 1,
                    "premium_purchased": False,
                    "claimed_tiers": []
                }

    def claim_battle_pass_tier(self, user_id: int, season_id: int, tier: int) -> Tuple[bool, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            status = self.get_battle_pass_status(user_id, season_id)

            if tier > status['tier']:
                return False, "You have not reached this tier yet."
            if tier in status['claimed_tiers']:
                return False, "You have already claimed this tier."

            new_claimed_tiers = status['claimed_tiers'] + [tier]
            cursor.execute(
                "UPDATE season_progress SET claimed_tiers = %s WHERE user_id = %s AND season_id = %s",
                (json.dumps(new_claimed_tiers), user_id, season_id)
            )
            conn.commit()
            return True, f"Tier {tier} claimed successfully."

    def get_dust_balance(self, user_id: int) -> int:
        # This is a mock implementation. In a real scenario, you'd have a 'dust' column in the 'users' table.
        # For now, we'll calculate it based on inventory, which is inefficient.
        inventory = self.get_user_inventory(user_id)
        # Let's assume a simple dust value based on rarity, which we don't have here.
        # So, for now, let's just return a fixed value.
        return 100 # Mock value

    def dust_cards(self, user_id: int, card_ids: List[str]) -> Tuple[bool, str]:
        # Mock implementation
        dust_gained = 0
        for card_id in card_ids:
            if self.remove_card_from_inventory(user_id, card_id):
                dust_gained += 10 # Mock value
            else:
                return False, f"Card {card_id} not in inventory."
        # Here you would update the user's dust balance.
        return True, f"Gained {dust_gained} dust."

    def craft_card(self, user_id: int, card_id: str) -> Tuple[bool, str]:
        # Mock implementation
        crafting_cost = 50 # Mock value
        # Here you would check if the user has enough dust.
        # Then you would subtract the dust and add the card.
        self.add_card_to_inventory(user_id, card_id)
        return True, f"Card {card_id} crafted successfully."

    def get_vip_status(self, user_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM vip_status WHERE user_id = %s", (user_id,))
            vip_status = cursor.fetchone()
            return dict(vip_status) if vip_status else None

    def set_vip_status(self, user_id: int, is_vip: bool, vip_tier: int, expiration_date: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vip_status (user_id, is_vip, vip_tier, expiration_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET is_vip = EXCLUDED.is_vip, vip_tier = EXCLUDED.vip_tier, expiration_date = EXCLUDED.expiration_date;
            """, (user_id, is_vip, vip_tier, expiration_date))
            conn.commit()

    def create_user_pack(self, pack_id: str, name: str, creator_id: int, card_ids: List[str]) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cards_json = json.dumps(card_ids)
            cursor.execute(
                "INSERT INTO user_created_packs (pack_id, name, creator_id, cards) VALUES (%s, %s, %s, %s) RETURNING pack_id",
                (pack_id, name, creator_id, cards_json)
            )
            pack_id = cursor.fetchone()[0]
            conn.commit()
            return pack_id

    def get_user_pack(self, pack_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if self.db_type == "postgres" else None)
            cursor.execute("SELECT * FROM user_created_packs WHERE pack_id = %s", (pack_id,))
            pack = cursor.fetchone()
            if pack:
                pack_dict = dict(pack)
                pack_dict['cards'] = json.loads(pack_dict['cards'])
                return pack_dict
            return None

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        db_type = os.getenv("DB_TYPE", "sqlite")
        dsn = os.getenv("DATABASE_URL")
        _db_instance = Database(db_type=db_type, dsn=dsn)
    return _db_instance
''