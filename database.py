# database.py
import sqlite3
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path


class _PgCursorWrapper:
    """Wraps a psycopg2 cursor to translate ? placeholders to %s."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        # Translate SQLite syntax to PostgreSQL
        query = query.replace('?', '%s')

        # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
        if 'INSERT OR IGNORE' in query:
            query = query.replace('INSERT OR IGNORE', 'INSERT')
            if 'ON CONFLICT' not in query:
                # Append ON CONFLICT DO NOTHING before any trailing whitespace
                query = query.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'

        # INSERT OR REPLACE → just INSERT (caller should use ON CONFLICT DO UPDATE)
        if 'INSERT OR REPLACE' in query:
            query = query.replace('INSERT OR REPLACE', 'INSERT')

        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description


class _PgConnectionWrapper:
    """Wraps a psycopg2 connection so existing SQLite code works unchanged.

    - cursor() returns a _PgCursorWrapper (auto-translates ? to %s)
    - Context manager commits on success, rolls back on error (matches SQLite)
    - execute() is forwarded through the wrapper
    """

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _PgCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()
        return False


class DatabaseManager:
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self._database_url = os.getenv("DATABASE_URL")
        self._db_type = "postgresql" if self._database_url else "sqlite"
        self.init_database()

    def _get_connection(self):
        """Get database connection - PostgreSQL if DATABASE_URL set, else SQLite.

        PostgreSQL connections are wrapped so that ? placeholders are
        automatically translated to %s and the context-manager commits
        on success (matching SQLite behaviour).
        """
        if self._database_url:
            import psycopg2
            url = self._database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return _PgConnectionWrapper(psycopg2.connect(url))
        else:
            return sqlite3.connect(self.db_path)

    def _get_placeholder(self):
        """Get placeholder for queries - %s for PostgreSQL, ? for SQLite."""
        return "%s" if self._database_url else "?"
    
    def init_database(self):
        """Initialize all database tables"""
        if self._database_url:
            self._init_postgresql()
            return

        with self._get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    discord_tag TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_battles INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    packs_opened INTEGER DEFAULT 0,
                    victory_tokens INTEGER DEFAULT 0
                )
            """)
            
            # Cards table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL DEFAULT 'artist', -- 'artist' or 'song'
                    name TEXT NOT NULL,
                    artist_name TEXT,           -- alias for display (maps to name)
                    title TEXT,
                    image_url TEXT,
                    youtube_url TEXT,
                    rarity TEXT NOT NULL,
                    tier TEXT,                  -- mapped from rarity (community/gold/platinum/legendary)
                    variant TEXT DEFAULT 'Classic',
                    era TEXT,
                    impact INTEGER,
                    skill INTEGER,
                    longevity INTEGER,
                    culture INTEGER,
                    hype INTEGER,
                    serial_number TEXT,         -- unique instance ID (defaults to card_id)
                    print_number INTEGER DEFAULT 1, -- print sequence
                    quality TEXT DEFAULT 'standard', -- card quality
                    effect_type TEXT, -- for song cards
                    effect_value TEXT, -- for song cards
                    pack_id TEXT,
                    created_by_user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
                    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id)
                )
            """)

            # Lightweight migrations for existing databases
            cursor.execute("PRAGMA table_info(cards)")
            card_columns = {row[1] for row in cursor.fetchall()}
            if "era" not in card_columns:
                cursor.execute("ALTER TABLE cards ADD COLUMN era TEXT")
            if "artist_name" not in card_columns:
                cursor.execute("ALTER TABLE cards ADD COLUMN artist_name TEXT")
            if "tier" not in card_columns:
                cursor.execute("ALTER TABLE cards ADD COLUMN tier TEXT")
            if "serial_number" not in card_columns:
                cursor.execute("ALTER TABLE cards ADD COLUMN serial_number TEXT")
            if "print_number" not in card_columns:
                cursor.execute("ALTER TABLE cards ADD COLUMN print_number INTEGER DEFAULT 1")
            if "quality" not in card_columns:
                cursor.execute("ALTER TABLE cards ADD COLUMN quality TEXT DEFAULT 'standard'")
            
            # Server activity tracking (for auto-drops)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activity_type TEXT DEFAULT 'message'
                )
            """)
            
            # Create index for server_activity
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_server_activity_lookup 
                ON server_activity(server_id, timestamp)
            """)
            
            # User cosmetics table - track unlocked cosmetics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_cosmetics (
                    user_id TEXT NOT NULL,
                    cosmetic_id TEXT NOT NULL,
                    cosmetic_type TEXT NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    PRIMARY KEY (user_id, cosmetic_id)
                )
            """)
            
            # Cosmetics catalog - available cosmetics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cosmetics_catalog (
                    cosmetic_id TEXT PRIMARY KEY,
                    cosmetic_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    rarity TEXT,
                    unlock_method TEXT,
                    price_gold INTEGER,
                    price_tickets INTEGER,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Card cosmetic assignments - per-card customization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_cosmetics (
                    user_id TEXT NOT NULL,
                    card_id TEXT NOT NULL,
                    frame_style TEXT,
                    foil_effect TEXT,
                    badge_override TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, card_id)
                )
            """)
            
            # User collections (card ownership)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    card_id TEXT,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acquired_from TEXT, -- 'pack', 'trade', 'reward'
                    is_favorite BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id),
                    UNIQUE(user_id, card_id)
                )
            """)
            
            # Card generation log (duplicate prevention)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_generation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hero_artist TEXT NOT NULL,
                    hero_song TEXT NOT NULL,
                    generated_youtube_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for fast duplicate lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_generation_lookup 
                ON card_generation_log(hero_artist, hero_song)
            """)
            
            # Marketplace table (pack listings)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pack_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stock TEXT DEFAULT 'unlimited',
                    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id)
                )
            """)
            
            # Match history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    player_a_id INTEGER,
                    player_b_id INTEGER,
                    winner_id INTEGER,
                    final_score_a INTEGER,
                    final_score_b INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    match_type TEXT DEFAULT 'casual',
                    FOREIGN KEY (player_a_id) REFERENCES users(user_id),
                    FOREIGN KEY (player_b_id) REFERENCES users(user_id),
                    FOREIGN KEY (winner_id) REFERENCES users(user_id)
                )
            """)
            
            # Match rounds (detailed round data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT,
                    round_number INTEGER,
                    player_a_card_id TEXT,
                    player_b_card_id TEXT,
                    category TEXT,
                    winner TEXT, -- 'A' or 'B'
                    player_a_power INTEGER,
                    player_b_power INTEGER,
                    player_a_hype_bonus INTEGER,
                    player_b_hype_bonus INTEGER,
                    tiebreak_method TEXT,
                    FOREIGN KEY (match_id) REFERENCES matches(match_id)
                )
            """)
            
            # Pack openings history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_openings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    pack_type TEXT,
                    cards_received TEXT, -- JSON array of card IDs
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cost_tokens INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Creator packs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_packs (
                    pack_id TEXT PRIMARY KEY,
                    creator_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    pack_type TEXT DEFAULT 'creator', -- 'official' or 'creator'
                    pack_size INTEGER DEFAULT 10, -- 5, 10, 15
                    status TEXT DEFAULT 'DRAFT', -- DRAFT, LIVE, ARCHIVED
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    stripe_payment_id TEXT,
                    price_cents INTEGER DEFAULT 500, -- $5.00 default
                    total_purchases INTEGER DEFAULT 0,
                    cards_data TEXT, -- JSON array of card definitions
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            """)
            
            # Creator pack limits tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_pack_limits (
                    creator_id INTEGER PRIMARY KEY,
                    current_live_pack_id TEXT,
                    last_pack_published TIMESTAMP,
                    packs_published INTEGER DEFAULT 0,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id),
                    FOREIGN KEY (current_live_pack_id) REFERENCES creator_packs(pack_id)
                )
            """)
            
            # Marketplace daily stats tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_daily_stats (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    packs_added INTEGER DEFAULT 0,
                    packs_sold INTEGER DEFAULT 0,
                    total_revenue_cents INTEGER DEFAULT 0,
                    new_creators INTEGER DEFAULT 0,
                    top_pack_id TEXT,
                    top_pack_sales INTEGER DEFAULT 0,
                    top_creator_id INTEGER,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (top_pack_id) REFERENCES creator_packs(pack_id),
                    FOREIGN KEY (top_creator_id) REFERENCES users(user_id)
                )
            """)
            
            # ===== NEW RELATIONAL SCHEMA =====
            
            # 1. YouTubeVideos - Stores raw metadata from YouTube
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS youtube_videos (
                    video_id VARCHAR PRIMARY KEY,
                    title VARCHAR,
                    thumbnail_url VARCHAR,
                    view_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    channel_title VARCHAR,
                    channel_id VARCHAR,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. CardDefinitions - Template for cards derived from YouTube
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_definitions (
                    card_def_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_video_id VARCHAR,
                    card_name VARCHAR NOT NULL,
                    rarity VARCHAR DEFAULT 'Common',
                    power INTEGER DEFAULT 50,
                    attributes TEXT, -- JSON for flexible stats
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_video_id) REFERENCES youtube_videos(video_id)
                )
            """)
            
            # 3. CardInstances - Specific owned cards in user collections
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_instances (
                    instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_def_id INTEGER,
                    owner_user_id VARCHAR,
                    serial_number VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (card_def_id) REFERENCES card_definitions(card_def_id),
                    FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
                )
            """)
            
            # 4. Packs - Represents created packs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packs (
                    pack_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id VARCHAR,
                    main_hero_instance_id INTEGER,
                    pack_type VARCHAR DEFAULT 'gold',
                    status VARCHAR DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id),
                    FOREIGN KEY (main_hero_instance_id) REFERENCES card_instances(instance_id)
                )
            """)
            
            # 5. PackContents - Associates cards with packs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_contents (
                    pack_id INTEGER,
                    instance_id INTEGER,
                    position INTEGER, -- 1 for hero, 2-5 for additional cards
                    PRIMARY KEY (pack_id, instance_id),
                    FOREIGN KEY (pack_id) REFERENCES packs(pack_id),
                    FOREIGN KEY (instance_id) REFERENCES card_instances(instance_id)
                )
            """)
            
            # 6. MarketplaceItems - Published packs in marketplace
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pack_id INTEGER,
                    price DECIMAL(10,2) DEFAULT 9.99,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    stock VARCHAR DEFAULT 'unlimited',
                    FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
                )
            """)
            
            # 7. Transactions - Track marketplace transactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    buyer_id VARCHAR,
                    seller_id VARCHAR,
                    tx_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    price DECIMAL(10,2),
                    FOREIGN KEY (item_id) REFERENCES marketplace_items(item_id),
                    FOREIGN KEY (buyer_id) REFERENCES users(user_id),
                    FOREIGN KEY (seller_id) REFERENCES users(user_id)
                )
            """)
            
            # Add indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_card_instances_owner ON card_instances(owner_user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_contents_pack ON pack_contents(pack_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_active ON marketplace_items(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON transactions(buyer_id)")
            
            # Pack purchases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_purchases (
                    purchase_id TEXT PRIMARY KEY,
                    pack_id TEXT,
                    buyer_id INTEGER,
                    purchase_amount_cents INTEGER,
                    platform_revenue_cents INTEGER,
                    creator_revenue_cents INTEGER,
                    stripe_payment_id TEXT,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cards_received TEXT, -- JSON array of card IDs
                    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
                    FOREIGN KEY (buyer_id) REFERENCES users(user_id)
                )
            """)
            
            # Creator revenue tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_revenue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER,
                    pack_id TEXT,
                    purchase_id TEXT,
                    revenue_type TEXT, -- 'pack_publish' or 'pack_purchase'
                    gross_amount_cents INTEGER,
                    net_amount_cents INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id),
                    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
                    FOREIGN KEY (purchase_id) REFERENCES pack_purchases(purchase_id)
                )
            """)
            
            # Revenue Ledger - Source of truth for all money events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revenue_ledger (
                    ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL, -- PACK_PURCHASE, TRADE_FEE, REFUND, CHARGEBACK, PAYOUT
                    pack_id TEXT,
                    creator_user_id INTEGER,
                    buyer_user_id INTEGER,
                    amount_gross_cents INTEGER,
                    platform_amount_cents INTEGER,
                    creator_amount_cents INTEGER,
                    currency TEXT DEFAULT 'USD',
                    status TEXT DEFAULT 'pending', -- pending, completed, refunded, failed
                    stripe_payment_intent_id TEXT,
                    stripe_transfer_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (buyer_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id)
                )
            """)
            
            # Creator Balance Tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_balances (
                    creator_user_id INTEGER PRIMARY KEY,
                    available_balance_cents INTEGER DEFAULT 0,
                    pending_balance_cents INTEGER DEFAULT 0,
                    lifetime_earned_cents INTEGER DEFAULT 0,
                    last_payout_requested TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_user_id) REFERENCES users(user_id)
                )
            """)
            
            # Creator Stripe Connect accounts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_stripe_accounts (
                    creator_user_id INTEGER PRIMARY KEY,
                    stripe_account_id TEXT,
                    stripe_account_status TEXT DEFAULT 'pending', -- pending, verified, rejected
                    onboarding_completed TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_user_id) REFERENCES users(user_id)
                )
            """)
            
            # Server management and subscriptions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    server_id INTEGER PRIMARY KEY,
                    server_name TEXT,
                    server_owner_id INTEGER,
                    subscription_tier TEXT DEFAULT 'free', -- free, premium
                    subscription_status TEXT DEFAULT 'active', -- active, cancelled, expired
                    subscription_id TEXT, -- Stripe subscription ID
                    subscription_started TIMESTAMP,
                    subscription_ends TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_owner_id) REFERENCES users(user_id)
                )
            """)
            
            # Server usage analytics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER,
                    metric_type TEXT, -- packs_created, battles_fought, users_active
                    metric_value INTEGER,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(server_id)
                )
            """)
            
            # Market listings for trading
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_listings (
                    listing_id TEXT PRIMARY KEY,
                    seller_user_id INTEGER,
                    card_id TEXT,
                    asking_gold INTEGER,
                    asking_dust INTEGER,
                    status TEXT DEFAULT 'active', -- active, sold, cancelled
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    buyer_user_id INTEGER,
                    sold_at TIMESTAMP,
                    FOREIGN KEY (seller_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (buyer_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id)
                )
            """)
            
            # Active trades table (for pending trades)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    initiator_user_id INTEGER,
                    receiver_user_id INTEGER,
                    initiator_cards TEXT, -- JSON array
                    receiver_cards TEXT, -- JSON array
                    gold_from_initiator INTEGER DEFAULT 0,
                    gold_from_receiver INTEGER DEFAULT 0,
                    dust_from_initiator INTEGER DEFAULT 0,
                    dust_from_receiver INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending', -- pending, completed, expired, cancelled
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    expired_at TIMESTAMP,
                    FOREIGN KEY (initiator_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (receiver_user_id) REFERENCES users(user_id)
                )
            """)
            
            # Trade history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    trade_id TEXT PRIMARY KEY,
                    initiator_user_id INTEGER,
                    receiver_user_id INTEGER,
                    initiator_cards TEXT, -- JSON array
                    receiver_cards TEXT, -- JSON array
                    gold_from_initiator INTEGER DEFAULT 0,
                    gold_from_receiver INTEGER DEFAULT 0,
                    dust_from_initiator INTEGER DEFAULT 0,
                    dust_from_receiver INTEGER DEFAULT 0,
                    trade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (initiator_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (receiver_user_id) REFERENCES users(user_id)
                )
            """)
            
            # ===== ECONOMY SYSTEM =====

            # NOTE: user_economy table REMOVED - all economy data consolidated into user_inventory
            # user_inventory table is created below in the "MISSING TABLES" section
            
            # Battle history - track all battles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battle_history (
                    battle_id TEXT PRIMARY KEY,
                    player1_id INTEGER,
                    player2_id INTEGER,
                    player1_card_id TEXT,
                    player2_card_id TEXT,
                    winner INTEGER, -- 0=tie, 1=player1, 2=player2
                    player1_power INTEGER,
                    player2_power INTEGER,
                    player1_critical BOOLEAN DEFAULT 0,
                    player2_critical BOOLEAN DEFAULT 0,
                    wager_tier TEXT DEFAULT 'casual',
                    wager_amount INTEGER DEFAULT 50,
                    player1_gold_reward INTEGER,
                    player2_gold_reward INTEGER,
                    player1_xp_reward INTEGER,
                    player2_xp_reward INTEGER,
                    battle_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player1_id) REFERENCES users(user_id),
                    FOREIGN KEY (player2_id) REFERENCES users(user_id)
                )
            """)
            
            # Daily quests - track quest progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_quests (
                    quest_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    quest_type TEXT, -- 'win_3_battles', 'open_pack', etc.
                    progress INTEGER DEFAULT 0,
                    requirement INTEGER DEFAULT 1,
                    completed BOOLEAN DEFAULT 0,
                    gold_reward INTEGER DEFAULT 0,
                    xp_reward INTEGER DEFAULT 0,
                    quest_date DATE DEFAULT CURRENT_DATE,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Battle stats - aggregate user battle statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_battle_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_battles INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    ties INTEGER DEFAULT 0,
                    total_gold_won INTEGER DEFAULT 0,
                    total_gold_lost INTEGER DEFAULT 0,
                    total_xp_earned INTEGER DEFAULT 0,
                    current_win_streak INTEGER DEFAULT 0,
                    best_win_streak INTEGER DEFAULT 0,
                    last_battle_date TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # ===== MISSING TABLES (required by cogs) =====

            # Battle pass progress - used by menu_system.py
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battle_pass_progress (
                    user_id INTEGER PRIMARY KEY,
                    battle_pass_xp INTEGER DEFAULT 0,
                    current_tier INTEGER DEFAULT 1,
                    has_premium INTEGER DEFAULT 0,
                    claimed_free_tiers TEXT DEFAULT '[]',
                    claimed_premium_tiers TEXT DEFAULT '[]',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Server drop cooldowns - used by drop_system.py
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_drop_cooldowns (
                    server_id INTEGER PRIMARY KEY,
                    last_drop_time TIMESTAMP,
                    activity_level INTEGER DEFAULT 1,
                    drop_count_today INTEGER DEFAULT 0,
                    last_activity_update TIMESTAMP
                )
            """)

            # User inventory - used by card_economy.py, battlepass, gameplay
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 500,
                    dust INTEGER DEFAULT 0,
                    tickets INTEGER DEFAULT 0,
                    gems INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TEXT,
                    last_daily_claim TEXT,
                    premium_expires TEXT
                )
            """)

            # Season progress - used by battlepass_commands.py
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_progress (
                    user_id INTEGER PRIMARY KEY,
                    claimed_tiers TEXT DEFAULT '[]',
                    quest_progress TEXT DEFAULT '{}',
                    last_quest_reset TEXT
                )
            """)

            # Add indexes for economy tables
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_inventory_gold ON user_inventory(gold)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_players ON battle_history(player1_id, player2_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_date ON battle_history(battle_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_user ON user_quests(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_date ON user_quests(quest_date)")
            
            conn.commit()
    
    def _init_postgresql(self):
        """Initialize all tables in PostgreSQL."""
        print("🗄️ [DATABASE] Creating PostgreSQL tables...")
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # -- Core tables --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    discord_tag TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_battles INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    packs_opened INTEGER DEFAULT 0,
                    victory_tokens INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_packs (
                    pack_id TEXT PRIMARY KEY,
                    creator_id BIGINT,
                    name TEXT NOT NULL,
                    description TEXT,
                    pack_type TEXT DEFAULT 'creator',
                    pack_size INTEGER DEFAULT 10,
                    status TEXT DEFAULT 'DRAFT',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    stripe_payment_id TEXT,
                    price_cents INTEGER DEFAULT 500,
                    total_purchases INTEGER DEFAULT 0,
                    cards_data TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL DEFAULT 'artist',
                    name TEXT NOT NULL,
                    artist_name TEXT,
                    title TEXT,
                    image_url TEXT,
                    youtube_url TEXT,
                    rarity TEXT NOT NULL,
                    tier TEXT,
                    variant TEXT DEFAULT 'Classic',
                    era TEXT,
                    impact INTEGER,
                    skill INTEGER,
                    longevity INTEGER,
                    culture INTEGER,
                    hype INTEGER,
                    serial_number TEXT,
                    print_number INTEGER DEFAULT 1,
                    quality TEXT DEFAULT 'standard',
                    effect_type TEXT,
                    effect_value TEXT,
                    pack_id TEXT,
                    created_by_user_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_cards (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    card_id TEXT,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acquired_from TEXT,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    UNIQUE(user_id, card_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id BIGINT PRIMARY KEY,
                    gold INTEGER DEFAULT 500,
                    dust INTEGER DEFAULT 0,
                    tickets INTEGER DEFAULT 0,
                    gems INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TEXT,
                    last_daily_claim TEXT,
                    premium_expires TEXT
                )
            """)

            # -- Battle system --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battle_history (
                    battle_id TEXT PRIMARY KEY,
                    player1_id BIGINT,
                    player2_id BIGINT,
                    player1_card_id TEXT,
                    player2_card_id TEXT,
                    winner INTEGER,
                    player1_power INTEGER,
                    player2_power INTEGER,
                    player1_critical BOOLEAN DEFAULT FALSE,
                    player2_critical BOOLEAN DEFAULT FALSE,
                    wager_tier TEXT DEFAULT 'casual',
                    wager_amount INTEGER DEFAULT 50,
                    player1_gold_reward INTEGER,
                    player2_gold_reward INTEGER,
                    player1_xp_reward INTEGER,
                    player2_xp_reward INTEGER,
                    battle_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_battle_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_battles INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    ties INTEGER DEFAULT 0,
                    total_gold_won INTEGER DEFAULT 0,
                    total_gold_lost INTEGER DEFAULT 0,
                    total_xp_earned INTEGER DEFAULT 0,
                    current_win_streak INTEGER DEFAULT 0,
                    best_win_streak INTEGER DEFAULT 0,
                    last_battle_date TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    player_a_id BIGINT,
                    player_b_id BIGINT,
                    winner_id BIGINT,
                    final_score_a INTEGER,
                    final_score_b INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    match_type TEXT DEFAULT 'casual'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_rounds (
                    id SERIAL PRIMARY KEY,
                    match_id TEXT,
                    round_number INTEGER,
                    player_a_card_id TEXT,
                    player_b_card_id TEXT,
                    category TEXT,
                    winner TEXT,
                    player_a_power INTEGER,
                    player_b_power INTEGER,
                    player_a_hype_bonus INTEGER,
                    player_b_hype_bonus INTEGER,
                    tiebreak_method TEXT
                )
            """)

            # -- Battle pass --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battle_pass_progress (
                    user_id BIGINT PRIMARY KEY,
                    battle_pass_xp INTEGER DEFAULT 0,
                    current_tier INTEGER DEFAULT 1,
                    has_premium INTEGER DEFAULT 0,
                    claimed_free_tiers TEXT DEFAULT '[]',
                    claimed_premium_tiers TEXT DEFAULT '[]',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_progress (
                    user_id BIGINT PRIMARY KEY,
                    claimed_tiers TEXT DEFAULT '[]',
                    quest_progress TEXT DEFAULT '{}',
                    last_quest_reset TEXT
                )
            """)

            # -- Economy / marketplace --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_purchases (
                    purchase_id TEXT PRIMARY KEY,
                    pack_id TEXT,
                    buyer_id BIGINT,
                    purchase_amount_cents INTEGER,
                    platform_revenue_cents INTEGER,
                    creator_revenue_cents INTEGER,
                    stripe_payment_id TEXT,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cards_received TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_openings (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    pack_type TEXT,
                    cards_received TEXT,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cost_tokens INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace (
                    id SERIAL PRIMARY KEY,
                    pack_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stock TEXT DEFAULT 'unlimited'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_listings (
                    listing_id TEXT PRIMARY KEY,
                    seller_user_id BIGINT,
                    card_id TEXT,
                    asking_gold INTEGER,
                    asking_dust INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    buyer_user_id BIGINT,
                    sold_at TIMESTAMP
                )
            """)

            # -- Trading --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    initiator_user_id BIGINT,
                    receiver_user_id BIGINT,
                    initiator_cards TEXT,
                    receiver_cards TEXT,
                    gold_from_initiator INTEGER DEFAULT 0,
                    gold_from_receiver INTEGER DEFAULT 0,
                    dust_from_initiator INTEGER DEFAULT 0,
                    dust_from_receiver INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    expired_at TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    trade_id TEXT PRIMARY KEY,
                    initiator_user_id BIGINT,
                    receiver_user_id BIGINT,
                    initiator_cards TEXT,
                    receiver_cards TEXT,
                    gold_from_initiator INTEGER DEFAULT 0,
                    gold_from_receiver INTEGER DEFAULT 0,
                    dust_from_initiator INTEGER DEFAULT 0,
                    dust_from_receiver INTEGER DEFAULT 0,
                    trade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -- Revenue / creator --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_revenue (
                    id SERIAL PRIMARY KEY,
                    creator_id BIGINT,
                    pack_id TEXT,
                    purchase_id TEXT,
                    revenue_type TEXT,
                    gross_amount_cents INTEGER,
                    net_amount_cents INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revenue_ledger (
                    ledger_id SERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    pack_id TEXT,
                    creator_user_id BIGINT,
                    buyer_user_id BIGINT,
                    amount_gross_cents INTEGER,
                    platform_amount_cents INTEGER,
                    creator_amount_cents INTEGER,
                    currency TEXT DEFAULT 'USD',
                    status TEXT DEFAULT 'pending',
                    stripe_payment_intent_id TEXT,
                    stripe_transfer_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_balances (
                    creator_user_id BIGINT PRIMARY KEY,
                    available_balance_cents INTEGER DEFAULT 0,
                    pending_balance_cents INTEGER DEFAULT 0,
                    lifetime_earned_cents INTEGER DEFAULT 0,
                    last_payout_requested TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_stripe_accounts (
                    creator_user_id BIGINT PRIMARY KEY,
                    stripe_account_id TEXT,
                    stripe_account_status TEXT DEFAULT 'pending',
                    onboarding_completed TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_pack_limits (
                    creator_id BIGINT PRIMARY KEY,
                    current_live_pack_id TEXT,
                    last_pack_published TIMESTAMP,
                    packs_published INTEGER DEFAULT 0
                )
            """)

            # -- Server / analytics --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    server_id BIGINT PRIMARY KEY,
                    server_name TEXT,
                    server_owner_id BIGINT,
                    subscription_tier TEXT DEFAULT 'free',
                    subscription_status TEXT DEFAULT 'active',
                    subscription_id TEXT,
                    subscription_started TIMESTAMP,
                    subscription_ends TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_usage (
                    usage_id SERIAL PRIMARY KEY,
                    server_id BIGINT,
                    metric_type TEXT,
                    metric_value INTEGER,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_activity (
                    id SERIAL PRIMARY KEY,
                    server_id BIGINT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activity_type TEXT DEFAULT 'message'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_drop_cooldowns (
                    server_id BIGINT PRIMARY KEY,
                    last_drop_time TIMESTAMP,
                    activity_level INTEGER DEFAULT 1,
                    drop_count_today INTEGER DEFAULT 0,
                    last_activity_update TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_daily_stats (
                    stat_id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    packs_added INTEGER DEFAULT 0,
                    packs_sold INTEGER DEFAULT 0,
                    total_revenue_cents INTEGER DEFAULT 0,
                    new_creators INTEGER DEFAULT 0,
                    top_pack_id TEXT,
                    top_pack_sales INTEGER DEFAULT 0,
                    top_creator_id BIGINT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -- Quests --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_quests (
                    quest_id TEXT PRIMARY KEY,
                    user_id BIGINT,
                    quest_type TEXT,
                    progress INTEGER DEFAULT 0,
                    requirement INTEGER DEFAULT 1,
                    completed BOOLEAN DEFAULT FALSE,
                    gold_reward INTEGER DEFAULT 0,
                    xp_reward INTEGER DEFAULT 0,
                    quest_date DATE DEFAULT CURRENT_DATE,
                    completed_at TIMESTAMP
                )
            """)

            # -- Cosmetics --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_cosmetics (
                    user_id TEXT NOT NULL,
                    cosmetic_id TEXT NOT NULL,
                    cosmetic_type TEXT NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    PRIMARY KEY (user_id, cosmetic_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cosmetics_catalog (
                    cosmetic_id TEXT PRIMARY KEY,
                    cosmetic_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    rarity TEXT,
                    unlock_method TEXT,
                    price_gold INTEGER,
                    price_tickets INTEGER,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_cosmetics (
                    user_id TEXT NOT NULL,
                    card_id TEXT NOT NULL,
                    frame_style TEXT,
                    foil_effect TEXT,
                    badge_override TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, card_id)
                )
            """)

            # -- Relational schema --
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS youtube_videos (
                    video_id VARCHAR PRIMARY KEY,
                    title VARCHAR,
                    thumbnail_url VARCHAR,
                    view_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    channel_title VARCHAR,
                    channel_id VARCHAR,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_definitions (
                    card_def_id SERIAL PRIMARY KEY,
                    source_video_id VARCHAR,
                    card_name VARCHAR NOT NULL,
                    rarity VARCHAR DEFAULT 'Common',
                    power INTEGER DEFAULT 50,
                    attributes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_instances (
                    instance_id SERIAL PRIMARY KEY,
                    card_def_id INTEGER,
                    owner_user_id VARCHAR,
                    serial_number VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packs (
                    pack_id SERIAL PRIMARY KEY,
                    creator_id VARCHAR,
                    main_hero_instance_id INTEGER,
                    pack_type VARCHAR DEFAULT 'gold',
                    status VARCHAR DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_contents (
                    pack_id INTEGER,
                    instance_id INTEGER,
                    position INTEGER,
                    PRIMARY KEY (pack_id, instance_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_items (
                    item_id SERIAL PRIMARY KEY,
                    pack_id INTEGER,
                    price DECIMAL(10,2) DEFAULT 9.99,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    stock VARCHAR DEFAULT 'unlimited'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id SERIAL PRIMARY KEY,
                    item_id INTEGER,
                    buyer_id VARCHAR,
                    seller_id VARCHAR,
                    tx_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    price DECIMAL(10,2)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_generation_log (
                    id SERIAL PRIMARY KEY,
                    hero_artist TEXT NOT NULL,
                    hero_song TEXT NOT NULL,
                    generated_youtube_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -- Indexes --
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_server_activity_lookup ON server_activity(server_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_card_instances_owner ON card_instances(owner_user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_contents_pack ON pack_contents(pack_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_active ON marketplace_items(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON transactions(buyer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_inventory_gold ON user_inventory(gold)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_players ON battle_history(player1_id, player2_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_date ON battle_history(battle_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_user ON user_quests(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_date ON user_quests(quest_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_card_generation_lookup ON card_generation_log(hero_artist, hero_song)")

            conn.commit()
            print("✅ [DATABASE] All PostgreSQL tables created successfully")
        except Exception as e:
            print(f"❌ [DATABASE] PostgreSQL table creation error: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
        finally:
            conn.close()

    def check_database_integrity(self) -> Dict[str, any]:
        """
        Check database integrity and validate critical data

        Returns:
            Dict with integrity check results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "tables_checked": 0,
            "json_validated": 0
        }

        try:
            # PostgreSQL integrity check
            if self._database_url:
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    critical_tables = ['users', 'cards', 'creator_packs', 'user_cards']
                    for table in critical_tables:
                        results["tables_checked"] += 1
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables
                                WHERE table_name = %s
                            )
                        """, (table,))
                        if not cursor.fetchone()[0]:
                            results["valid"] = False
                            results["errors"].append(f"Critical table missing: {table}")

                    # Validate JSON in creator_packs if table exists
                    if results["valid"]:
                        cursor.execute("SELECT pack_id, cards_data FROM creator_packs WHERE cards_data IS NOT NULL")
                        for pack_id, cards_data_json in cursor.fetchall():
                            try:
                                cards = json.loads(cards_data_json)
                                if isinstance(cards, list):
                                    results["json_validated"] += 1
                            except json.JSONDecodeError as e:
                                results["valid"] = False
                                results["errors"].append(f"Pack {pack_id}: Invalid JSON - {e}")
                finally:
                    conn.close()
                return results

            # SQLite integrity check
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check database file integrity
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                if integrity_result[0] != 'ok':
                    results["valid"] = False
                    results["errors"].append(f"Database integrity check failed: {integrity_result[0]}")
                    return results

                # Check critical tables exist
                critical_tables = ['users', 'cards', 'creator_packs', 'user_cards']
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN (?, ?, ?, ?)
                """, critical_tables)
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                for table in critical_tables:
                    results["tables_checked"] += 1
                    if table not in existing_tables:
                        results["valid"] = False
                        results["errors"].append(f"Critical table missing: {table}")
                
                # Validate JSON in creator_packs.cards_data
                cursor.execute("SELECT pack_id, cards_data FROM creator_packs WHERE cards_data IS NOT NULL")
                packs = cursor.fetchall()
                
                for pack_id, cards_data_json in packs:
                    try:
                        cards = json.loads(cards_data_json)
                        if not isinstance(cards, list):
                            results["warnings"].append(f"Pack {pack_id}: cards_data is not a list")
                        else:
                            results["json_validated"] += 1
                    except json.JSONDecodeError as e:
                        results["valid"] = False
                        results["errors"].append(f"Pack {pack_id}: Invalid JSON in cards_data - {e}")
                
                # Check foreign key integrity
                cursor.execute("PRAGMA foreign_key_check")
                fk_errors = cursor.fetchall()
                if fk_errors:
                    results["warnings"].append(f"Found {len(fk_errors)} foreign key constraint issues")
                    for error in fk_errors[:5]:  # Show first 5
                        results["warnings"].append(f"FK error: {error}")
                
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Integrity check failed: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def get_or_create_user(self, user_id: int, username: str, discord_tag: str) -> Dict:
        """Get existing user or create new one"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Try to get existing user
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

            if user:
                # Get columns before UPDATE (which clears cursor.description)
                columns = [desc[0] for desc in cursor.description]

                # Update last active
                cursor.execute(
                    "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                return dict(zip(columns, user))
            else:
                # Create new user
                cursor.execute(
                    """
                    INSERT INTO users (user_id, username, discord_tag)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, username, discord_tag)
                )
                
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, user))
    
    def add_card_to_master(self, card_data: Dict) -> bool:
        """Add a card to the master card list with flexible field mapping"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Generate default battle stats if not provided
                # If 'power' is provided but not individual stats, derive them
                if 'power' in card_data and not card_data.get('impact'):
                    base_stat = card_data['power'] // 4  # Distribute power across 4 stats
                    card_data['impact'] = base_stat
                    card_data['skill'] = base_stat
                    card_data['longevity'] = base_stat
                    card_data['culture'] = base_stat

                # Default hype to average of other stats if not provided
                if not card_data.get('hype'):
                    avg_stat = (
                        card_data.get('impact', 0) +
                        card_data.get('skill', 0) +
                        card_data.get('longevity', 0) +
                        card_data.get('culture', 0)
                    ) // 4
                    card_data['hype'] = avg_stat

                # Map rarity to tier if not provided
                rarity = card_data.get('rarity', 'common').lower()
                if not card_data.get('tier'):
                    tier_map = {'common': 'community', 'rare': 'gold', 'epic': 'platinum',
                                'legendary': 'legendary', 'mythic': 'legendary'}
                    card_data['tier'] = tier_map.get(rarity, 'community')

                # Set serial_number to card_id if not provided
                if not card_data.get('serial_number'):
                    card_data['serial_number'] = card_data['card_id']

                # Set artist_name to name if not provided
                if not card_data.get('artist_name'):
                    card_data['artist_name'] = card_data['name']

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO cards
                    (card_id, name, artist_name, title, rarity, tier, serial_number, print_number,
                     quality, era, variant, impact, skill, longevity, culture, hype,
                     image_url, youtube_url, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        card_data['card_id'],
                        card_data['name'],
                        card_data.get('artist_name', card_data['name']),
                        card_data.get('title', ''),
                        card_data['rarity'],
                        card_data.get('tier'),
                        card_data.get('serial_number', card_data['card_id']),
                        card_data.get('print_number', 1),
                        card_data.get('quality', 'standard'),
                        card_data.get('era'),
                        card_data.get('variant'),
                        card_data.get('impact', 0),
                        card_data.get('skill', 0),
                        card_data.get('longevity', 0),
                        card_data.get('culture', 0),
                        card_data.get('hype', 0),
                        card_data.get('image_url'),
                        card_data.get('youtube_url'),
                        card_data.get('type', card_data.get('card_type', 'artist'))
                    )
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"❌ Error adding card to master: {e}")
            print(f"   Card data: {card_data.get('card_id', 'unknown')} - {card_data.get('name', 'unknown')}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_card_to_collection(self, user_id: int, card_id: str, acquired_from: str = 'pack') -> bool:
        """Add a card to user's collection"""
        conn = self._get_connection()
        ph = self._get_placeholder()
        try:
            cursor = conn.cursor()
            if self._database_url:
                # PostgreSQL - use ON CONFLICT
                cursor.execute(
                    f"""
                    INSERT INTO user_cards (user_id, card_id, acquired_from)
                    VALUES ({ph}, {ph}, {ph})
                    ON CONFLICT (user_id, card_id) DO NOTHING
                    """,
                    (user_id, card_id, acquired_from)
                )
            else:
                # SQLite
                cursor.execute(
                    f"""
                    INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from)
                    VALUES ({ph}, {ph}, {ph})
                    """,
                    (user_id, card_id, acquired_from)
                )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding card to collection: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_collection(self, user_id: int) -> List[Dict]:
        """Get all cards owned by a user"""
        conn = self._get_connection()
        ph = self._get_placeholder()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT c.*, uc.acquired_at, uc.acquired_from, uc.is_favorite
                FROM cards c
                JOIN user_cards uc ON c.card_id = uc.card_id
                WHERE uc.user_id = {ph}
                ORDER BY c.rarity DESC, c.name
                """,
                (user_id,)
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_user_deck(self, user_id: int, limit: int = 3) -> List[Dict]:
        """Get user's deck (first N cards from collection)"""
        collection = self.get_user_collection(user_id)
        return collection[:limit]
    
    def record_match(self, match_data: Dict) -> bool:
        """Record a completed match"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert match
                cursor.execute(
                    """
                    INSERT INTO matches 
                    (match_id, player_a_id, player_b_id, winner_id, 
                     final_score_a, final_score_b, completed_at, match_type)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """,
                    (
                        match_data['match_id'], match_data['player_a_id'],
                        match_data['player_b_id'], match_data['winner_id'],
                        match_data['final_score_a'], match_data['final_score_b'],
                        match_data.get('match_type', 'casual')
                    )
                )
                
                # Update user stats
                cursor.execute(
                    "UPDATE users SET total_battles = total_battles + 1, wins = wins + 1 WHERE user_id = ?",
                    (match_data['winner_id'],)
                )
                loser_id = (match_data['player_a_id'] if match_data['winner_id'] == match_data['player_b_id'] 
                           else match_data['player_b_id'])
                cursor.execute(
                    "UPDATE users SET total_battles = total_battles + 1, losses = losses + 1 WHERE user_id = ?",
                    (loser_id,)
                )
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error recording match: {e}")
            return False
    
    def record_pack_opening(self, user_id: int, pack_type: str, cards_received: List[str], cost_tokens: int = 0) -> bool:
        """Record a pack opening"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Record pack opening
                cursor.execute(
                    """
                    INSERT INTO pack_openings (user_id, pack_type, cards_received, cost_tokens)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, pack_type, json.dumps(cards_received), cost_tokens)
                )
                
                # Update user stats
                cursor.execute(
                    "UPDATE users SET packs_opened = packs_opened + 1 WHERE user_id = ?",
                    (user_id,)
                )
                
                # Add cards to collection
                for card_id in cards_received:
                    self.add_card_to_collection(user_id, card_id, 'pack')
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error recording pack opening: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get comprehensive user statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.*, COUNT(uc.card_id) as total_cards
                FROM users u
                LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                WHERE u.user_id = ?
                GROUP BY u.user_id
                """,
                (user_id,)
            )
            user = cursor.fetchone()
            
            if user:
                columns = [desc[0] for desc in cursor.description]
                stats = dict(zip(columns, user))
                
                # Calculate win rate
                if stats['total_battles'] > 0:
                    stats['win_rate'] = (stats['wins'] / stats['total_battles']) * 100
                else:
                    stats['win_rate'] = 0
                
                return stats
            return None
    
    def get_leaderboard(self, metric: str = 'wins', limit: int = 10) -> List[Dict]:
        """Get leaderboard by different metrics"""
        valid_metrics = ['wins', 'total_battles', 'win_rate', 'total_cards', 'packs_opened']
        if metric not in valid_metrics:
            metric = 'wins'
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if metric == 'win_rate':
                cursor.execute(
                    """
                    SELECT user_id, username, wins, total_battles,
                           CASE WHEN total_battles > 0 THEN (wins * 100.0 / total_battles) ELSE 0 END as win_rate
                    FROM users 
                    WHERE total_battles >= 5
                    ORDER BY win_rate DESC, total_battles DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            elif metric == 'total_cards':
                cursor.execute(
                    """
                    SELECT u.user_id, u.username, COUNT(uc.card_id) as total_cards
                    FROM users u
                    LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                    GROUP BY u.user_id, u.username
                    ORDER BY total_cards DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            else:
                cursor.execute(
                    f"SELECT user_id, username, {metric} FROM users ORDER BY {metric} DESC LIMIT ?",
                    (limit,)
                )
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Pack Management Methods
    def create_creator_pack(self, creator_id: int, name: str, description: str = "", pack_size: int = 10) -> str:
        """Create a new creator pack in DRAFT status"""
        import uuid
        pack_id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO creator_packs 
                (pack_id, creator_id, name, description, pack_size, status, cards_data)
                VALUES (?, ?, ?, ?, ?, 'DRAFT', '[]')
            """, (pack_id, creator_id, name, description, pack_size))
            
            # Initialize creator limits if first time
            cursor.execute("""
                INSERT OR IGNORE INTO creator_pack_limits (creator_id)
                VALUES (?)
            """, (creator_id,))
            
            conn.commit()
        return pack_id
    
    def get_creator_draft_pack(self, creator_id: int) -> Optional[Dict]:
        """Get current draft pack for creator"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM creator_packs 
                WHERE creator_id = ? AND status = 'DRAFT'
                ORDER BY created_at DESC
                LIMIT 1
            """, (creator_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def add_card_to_pack(self, pack_id: str, card_data: Dict) -> bool:
        """Add a card to pack's cards_data JSON"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current cards
            cursor.execute("SELECT cards_data, pack_size FROM creator_packs WHERE pack_id = ?", (pack_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            cards_data = json.loads(result[0])
            pack_size = result[1]
            
            # Check pack size limit
            if len(cards_data) >= pack_size:
                return False
            
            # Add new card
            cards_data.append(card_data)
            cursor.execute("""
                UPDATE creator_packs 
                SET cards_data = ? 
                WHERE pack_id = ?
            """, (json.dumps(cards_data), pack_id))
            
            conn.commit()
            return True
    
    def validate_pack_rules(self, pack_id: str) -> Dict:
        """Validate pack against creation rules"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, c.last_pack_published, c.packs_published
                FROM creator_packs p
                LEFT JOIN creator_pack_limits c ON p.creator_id = c.creator_id
                WHERE p.pack_id = ?
            """, (pack_id,))
            
            result = cursor.fetchone()
            if not result:
                return {"valid": False, "errors": ["Pack not found"]}
            
            columns = [desc[0] for desc in cursor.description]
            pack = dict(zip(columns, result))
            
            errors = []
            warnings = []
            
            # Load cards data
            cards = json.loads(pack['cards_data'])
            
            # Check pack size
            if len(cards) != pack['pack_size']:
                errors.append(f"Pack must have exactly {pack['pack_size']} cards (has {len(cards)})")
            
            # Check cooldown (7 days = 7 * 24 * 3600 seconds)
            if pack['last_pack_published']:
                import time
                time_since = time.time() - pack['last_pack_published']
                if time_since < 7 * 24 * 3600:
                    errors.append("Must wait 7 days between pack publications")
            
            # Check rarity distribution
            rarity_counts = {}
            for card in cards:
                rarity = card.get('rarity', 'Common')
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
            
            # No Mythic rarity for creator packs (rule)
            if rarity_counts.get('Mythic', 0) > 0:
                errors.append("Creator packs cannot contain Mythic rarity cards")
            
            # Check stat ceiling (92 max for creator packs)
            for card in cards:
                for stat in ['impact', 'skill', 'longevity', 'culture', 'hype']:
                    if card.get(stat, 0) > 92:
                        errors.append(f"Card '{card.get('name', 'Unknown')}' has {stat} > 92")
            
            # Check required fields
            for i, card in enumerate(cards):
                if not card.get('name'):
                    errors.append(f"Card {i+1} missing name")
                if not card.get('rarity'):
                    errors.append(f"Card {i+1} missing rarity")
                if not card.get('youtube_url'):
                    warnings.append(f"Card {i+1} missing YouTube link")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "pack_info": pack
            }
    
    def publish_pack(self, pack_id: str, stripe_payment_id: str) -> bool:
        """Publish pack after payment confirmation"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Update pack status
            cursor.execute("""
                UPDATE creator_packs 
                SET status = 'LIVE', published_at = CURRENT_TIMESTAMP, stripe_payment_id = ?
                WHERE pack_id = ?
            """, (stripe_payment_id, pack_id))
            
            # Update creator limits
            cursor.execute("""
                UPDATE creator_pack_limits 
                SET current_live_pack_id = ?, 
                    last_pack_published = CURRENT_TIMESTAMP,
                    packs_published = packs_published + 1
                WHERE creator_id = (SELECT creator_id FROM creator_packs WHERE pack_id = ?)
            """, (pack_id, pack_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_live_packs(self, limit: int = 20) -> List[Dict]:
        """Get all live packs for browsing"""
        conn = self._get_connection()
        ph = self._get_placeholder()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT p.*, COALESCE(u.username, 'System') as creator_name
                FROM creator_packs p
                LEFT JOIN users u ON p.creator_id = u.user_id
                WHERE p.status = 'LIVE'
                ORDER BY p.published_at DESC
                LIMIT {ph}
            """, (limit,))

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def bulk_create_packs(self, packs_data: List[Dict]) -> Dict[str, List]:
        """Bulk insert multiple packs at once (optimized for admin imports)
        
        Args:
            packs_data: List of pack dictionaries with structure:
                {
                    'pack_id': str,
                    'creator_id': int,
                    'name': str,
                    'description': str,
                    'pack_size': int,
                    'price_cents': int,
                    'cards': List[Dict]
                }
        
        Returns:
            Dictionary with 'success' and 'failed' pack IDs
        """
        results = {'success': [], 'failed': []}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for pack in packs_data:
                try:
                    pack_id = pack['pack_id']
                    
                    # Initialize creator if needed
                    cursor.execute("""
                        INSERT OR IGNORE INTO creator_pack_limits (creator_id)
                        VALUES (?)
                    """, (pack['creator_id'],))
                    
                    # Insert pack
                    cards_json = json.dumps(pack['cards'])
                    cursor.execute("""
                        INSERT INTO creator_packs 
                        (pack_id, creator_id, name, description, pack_size, status, cards_data, 
                         published_at, price_cents, stripe_payment_id)
                        VALUES (?, ?, ?, ?, ?, 'LIVE', ?, CURRENT_TIMESTAMP, ?, 'ADMIN_IMPORT')
                    """, (
                        pack_id,
                        pack['creator_id'],
                        pack['name'],
                        pack.get('description', ''),
                        pack.get('pack_size', 5),
                        cards_json,
                        pack.get('price_cents', 699)
                    ))
                    
                    # Insert cards
                    for card in pack['cards']:
                        if 'pack_id' not in card:
                            card['pack_id'] = pack_id
                        self.add_card_to_master(card)
                    
                    # Update creator stats
                    cursor.execute("""
                        UPDATE creator_pack_limits 
                        SET packs_published = packs_published + 1,
                            last_pack_published = strftime('%s', 'now')
                        WHERE creator_id = ?
                    """, (pack['creator_id'],))
                    
                    results['success'].append(pack_id)
                    
                except Exception as e:
                    results['failed'].append({
                        'pack_id': pack.get('pack_id', 'unknown'),
                        'error': str(e)
                    })
            
            conn.commit()
        
        return results
    
    def purchase_pack(self, pack_id: str, buyer_id: int, payment_id: str, amount_cents: int) -> str:
        """Process pack purchase and generate cards with proper revenue tracking"""
        import uuid
        from stripe_payments import stripe_manager
        
        purchase_id = str(uuid.uuid4())
        
        # Calculate revenue split
        revenue_split = stripe_manager.calculate_revenue_split(amount_cents)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get pack data and creator
            cursor.execute("""
                SELECT cards_data, creator_id, name FROM creator_packs 
                WHERE pack_id = ? AND status = 'LIVE'
            """, (pack_id,))
            result = cursor.fetchone()
            if not result:
                return None
            
            cards_json, creator_id, pack_name = result[0], result[1], result[2]

            # Parse cards JSON if it's a string
            if isinstance(cards_json, str):
                cards_data = json.loads(cards_json)
            else:
                cards_data = cards_json or []

            # Generate cards for buyer (add to their collection)
            received_cards = []
            for card_data in cards_data:
                card_id = self.add_card_to_master_list(card_data)
                self.add_card_to_collection(buyer_id, card_id, 'pack')
                received_cards.append(card_id)
            
            # Record purchase with revenue split
            cursor.execute("""
                INSERT INTO pack_purchases 
                (purchase_id, pack_id, buyer_id, purchase_amount_cents, 
                 platform_revenue_cents, creator_revenue_cents, stripe_payment_id, cards_received)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (purchase_id, pack_id, buyer_id, amount_cents, 
                  revenue_split['platform_cents'], revenue_split['creator_cents'], 
                  payment_id, json.dumps(received_cards)))
            
            # Update pack purchase count
            cursor.execute("UPDATE creator_packs SET total_purchases = total_purchases + 1 WHERE pack_id = ?", (pack_id,))
            
            # Create ledger entry (source of truth)
            cursor.execute("""
                INSERT INTO revenue_ledger 
                (event_type, pack_id, creator_user_id, buyer_user_id, amount_gross_cents,
                 platform_amount_cents, creator_amount_cents, stripe_payment_intent_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ('PACK_PURCHASE', pack_id, creator_id, buyer_id, amount_cents,
                  revenue_split['platform_cents'], revenue_split['creator_cents'], 
                  payment_id, 'completed'))
            
            # Update creator balance (pending until refund window passes)
            self._update_creator_balance(creator_id, revenue_split['creator_cents'], 'pending')
            
            # Record creator revenue (legacy table for compatibility)
            cursor.execute("""
                INSERT INTO creator_revenue 
                (creator_id, pack_id, purchase_id, revenue_type, gross_amount_cents, net_amount_cents)
                VALUES (?, ?, ?, 'pack_purchase', ?, ?)
            """, (creator_id, pack_id, purchase_id, amount_cents, revenue_split['creator_cents']))
            
            conn.commit()
            return purchase_id
    
    def _update_creator_balance(self, creator_id: int, amount_cents: int, balance_type: str):
        """Update creator balance (pending or available)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current balance or create new record
            cursor.execute("SELECT * FROM creator_balances WHERE creator_user_id = ?", (creator_id,))
            balance = cursor.fetchone()
            
            if balance:
                # Update existing balance
                if balance_type == 'pending':
                    cursor.execute("""
                        UPDATE creator_balances 
                        SET pending_balance_cents = pending_balance_cents + ?,
                            lifetime_earned_cents = lifetime_earned_cents + ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE creator_user_id = ?
                    """, (amount_cents, amount_cents, creator_id))
                elif balance_type == 'available':
                    cursor.execute("""
                        UPDATE creator_balances 
                        SET available_balance_cents = available_balance_cents + ?,
                            pending_balance_cents = pending_balance_cents - ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE creator_user_id = ?
                    """, (amount_cents, amount_cents, creator_id))
            else:
                # Create new balance record
                if balance_type == 'pending':
                    cursor.execute("""
                        INSERT INTO creator_balances 
                        (creator_user_id, pending_balance_cents, lifetime_earned_cents)
                        VALUES (?, ?, ?)
                    """, (creator_id, amount_cents, amount_cents))
                elif balance_type == 'available':
                    cursor.execute("""
                        INSERT INTO creator_balances 
                        (creator_user_id, available_balance_cents, lifetime_earned_cents)
                        VALUES (?, ?, ?)
                    """, (creator_id, amount_cents, amount_cents))
            
            conn.commit()
    
    def get_creator_balance(self, creator_id: int) -> Dict:
        """Get creator balance information"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM creator_balances WHERE creator_user_id = ?", (creator_id,))
            balance = cursor.fetchone()
            
            if balance:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, balance))
            else:
                return {
                    'creator_user_id': creator_id,
                    'available_balance_cents': 0,
                    'pending_balance_cents': 0,
                    'lifetime_earned_cents': 0,
                    'last_payout_requested': None,
                    'updated_at': None
                }
    
    def get_creator_earnings(self, creator_id: int) -> Dict:
        """Get detailed creator earnings from ledger"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total earnings
            cursor.execute("""
                SELECT 
                    SUM(amount_gross_cents) as total_gross,
                    SUM(platform_amount_cents) as total_platform,
                    SUM(creator_amount_cents) as total_creator,
                    COUNT(*) as transaction_count
                FROM revenue_ledger 
                WHERE creator_user_id = ? AND event_type = 'PACK_PURCHASE' AND status = 'completed'
            """, (creator_id,))
            
            earnings = cursor.fetchone()
            columns = [desc[0] for desc in cursor.description]
            earnings_dict = dict(zip(columns, earnings))
            
            # Get recent transactions
            cursor.execute("""
                SELECT pack_id, amount_gross_cents, creator_amount_cents, created_at
                FROM revenue_ledger 
                WHERE creator_user_id = ? AND event_type = 'PACK_PURCHASE' AND status = 'completed'
                ORDER BY created_at DESC
                LIMIT 10
            """, (creator_id,))
            
            recent = cursor.fetchall()
            recent_columns = [desc[0] for desc in cursor.description]
            recent_transactions = [dict(zip(recent_columns, row)) for row in recent]
            
            return {
                'total_earnings': earnings_dict,
                'recent_transactions': recent_transactions
            }
    
    def store_creator_stripe_account(self, creator_id: int, stripe_account_id: str):
        """Store creator's Stripe Connect account ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO creator_stripe_accounts 
                (creator_user_id, stripe_account_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (creator_id, stripe_account_id))
            conn.commit()
    
    def get_creator_stripe_account(self, creator_id: int) -> Dict:
        """Get creator's Stripe Connect account info"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM creator_stripe_accounts WHERE creator_user_id = ?", (creator_id,))
            account = cursor.fetchone()
            
            if account:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, account))
            else:
                return None
    
    def register_server(self, server_id: int, server_name: str, owner_id: int):
        """Register a new server that added the bot"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO servers 
                (server_id, server_name, server_owner_id, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (server_id, server_name, owner_id))
            conn.commit()
    
    def get_server_info(self, server_id: int) -> Dict:
        """Get server subscription and usage info"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM servers WHERE server_id = ?", (server_id,))
            server = cursor.fetchone()
            
            if server:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, server))
            else:
                return None
    
    def update_server_subscription(self, server_id: int, subscription_id: str, tier: str):
        """Update server subscription info"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servers 
                SET subscription_id = ?, subscription_tier = ?, subscription_status = 'active',
                    subscription_started = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE server_id = ?
            """, (subscription_id, tier, server_id))
            conn.commit()
    
    def cancel_server_subscription(self, server_id: int):
        """Cancel server subscription"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servers 
                SET subscription_status = 'cancelled', subscription_ends = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE server_id = ?
            """, (server_id,))
            conn.commit()
    
    def is_server_premium(self, server_id: int) -> bool:
        """Check if server has premium subscription"""
        server = self.get_server_info(server_id)
        if not server:
            return False
        
        return (server['subscription_tier'] == 'premium' and 
                server['subscription_status'] == 'active')
    
    def record_server_usage(self, server_id: int, metric_type: str, value: int):
        """Record server usage metrics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO server_usage (server_id, metric_type, metric_value)
                VALUES (?, ?, ?)
            """, (server_id, metric_type, value))
            conn.commit()
    
    def get_server_analytics(self, server_id: int, days: int = 30) -> Dict:
        """Get server usage analytics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get usage stats for the last N days
            cursor.execute("""
                SELECT metric_type, SUM(metric_value) as total
                FROM server_usage 
                WHERE server_id = ? AND recorded_at >= date('now', '-{} days')
                GROUP BY metric_type
            """.format(days), (server_id,))
            
            usage_data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            usage_dict = dict(zip(columns, usage_data[0])) if usage_data else {}
            
            return {
                'period_days': days,
                'metrics': usage_dict
            }
    
    def add_card_to_master_list(self, card_data: Dict) -> str:
        """Add card to master cards table with minimal storage"""
        # Use existing card_id if provided, otherwise generate one
        card_id = card_data.get('card_id') or f"{card_data['name'].lower().replace(' ', '_')}_{card_data.get('rarity', 'Common').lower()}"

        # Map rarity to tier if not provided
        rarity = card_data.get('rarity', 'Common').lower()
        tier_map = {'common': 'community', 'rare': 'gold', 'epic': 'platinum',
                    'legendary': 'legendary', 'mythic': 'legendary'}
        tier = card_data.get('tier') or tier_map.get(rarity, 'community')

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO cards
                (card_id, type, name, artist_name, title, image_url,
                 youtube_url, rarity, tier, variant, impact, skill, longevity, culture, hype,
                 serial_number, print_number, quality,
                 effect_type, effect_value, pack_id, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                card_data.get('type', 'artist'),
                card_data.get('name'),
                card_data.get('artist_name', card_data.get('name')),
                card_data.get('title', ''),
                card_data.get('image_url', ''),
                card_data.get('youtube_url', ''),
                card_data.get('rarity', 'Common'),
                tier,
                card_data.get('variant', 'Classic'),
                card_data.get('impact', 50),
                card_data.get('skill', 50),
                card_data.get('longevity', 50),
                card_data.get('culture', 50),
                card_data.get('hype', 50),
                card_data.get('serial_number', card_id),
                card_data.get('print_number', 1),
                card_data.get('quality', 'standard'),
                card_data.get('effect_type'),
                card_data.get('effect_value'),
                card_data.get('pack_id'),
                card_data.get('created_by_user_id')
            ))

            conn.commit()
            return card_id
    
    def get_all_artists(self, limit: int = 100) -> List[Dict]:
        """Get all unique artists from the cards table"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT name, image_url
                FROM cards
                WHERE name IS NOT NULL AND name != ''
                LIMIT ?
            """, (limit,))

            artists = []
            for row in cursor.fetchall():
                artists.append({
                    'name': row[0],
                    'image_url': row[1],
                    'stats': {}
                })

            # If no artists in database, return some defaults
            if not artists:
                default_artists = [
                    "Taylor Swift", "Drake", "Bad Bunny", "The Weeknd",
                    "Ariana Grande", "Ed Sheeran", "Billie Eilish", "Post Malone"
                ]
                for name in default_artists[:limit]:
                    artists.append({
                        'name': name,
                        'image_url': '',
                        'stats': {}
                    })
            
            return artists
    
    # ===== ECONOMY METHODS =====
    
    def get_user_economy(self, user_id: int) -> Dict:
        """Get user's economy data (gold, tickets, daily streak) - uses user_inventory table"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, gold, tickets, last_daily_claim, daily_streak
                FROM user_inventory
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            if not result:
                # Create new economy record for user
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, gold, tickets, dust, gems, xp, level, daily_streak)
                    VALUES (?, 500, 0, 0, 0, 0, 1, 0)
                """, (user_id,))
                conn.commit()

                cursor.execute("""
                    SELECT user_id, gold, tickets, last_daily_claim, daily_streak
                    FROM user_inventory
                    WHERE user_id = ?
                """, (user_id,))
                result = cursor.fetchone()

            columns = ['user_id', 'gold', 'tickets', 'last_daily_claim', 'daily_streak']
            return dict(zip(columns, result)) if result else {'user_id': user_id, 'gold': 500, 'tickets': 0, 'last_daily_claim': None, 'daily_streak': 0}
    
    def update_user_economy(self, user_id: int, gold_change: int = 0, tickets_change: int = 0) -> bool:
        """Update user's gold and tickets - uses user_inventory table"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Ensure user exists first
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, gold, tickets)
                    VALUES (?, 500, 0)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id,))
                cursor.execute("""
                    UPDATE user_inventory
                    SET gold = COALESCE(gold, 0) + ?, tickets = COALESCE(tickets, 0) + ?
                    WHERE user_id = ?
                """, (gold_change, tickets_change, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating user economy: {e}")
            return False
    
    def claim_daily_reward(self, user_id: int) -> Dict:
        """Process daily reward claim - NOW WITH FREE CARD!"""
        from datetime import datetime, timedelta
        import random

        economy = self.get_user_economy(user_id)

        # Check if can claim
        if economy['last_daily_claim']:
            last_claim = datetime.fromisoformat(economy['last_daily_claim'])
            time_since = datetime.now() - last_claim
            if time_since < timedelta(hours=20):
                return {
                    "success": False,
                    "error": "Already claimed today",
                    "time_until": timedelta(hours=24) - time_since
                }

        # Calculate streak
        if economy['last_daily_claim']:
            time_since_claim = datetime.now() - last_claim
            if time_since_claim <= timedelta(hours=48):
                new_streak = economy['daily_streak'] + 1
            else:
                new_streak = 1
        else:
            new_streak = 1

        # Calculate rewards
        base_gold = 100
        bonus_gold = 0
        tickets = 0

        streak_bonuses = {
            3: {"gold": 50, "tickets": 0},
            7: {"gold": 200, "tickets": 1},
            14: {"gold": 500, "tickets": 2},
            30: {"gold": 1000, "tickets": 5},
        }

        if new_streak in streak_bonuses:
            bonus = streak_bonuses[new_streak]
            bonus_gold = bonus["gold"]
            tickets = bonus["tickets"]

        total_gold = base_gold + bonus_gold

        # === NEW: DAILY FREE CARD ===
        # Rarity weights: 70% common, 25% rare, 5% epic
        daily_card = self._get_random_daily_card()

        if daily_card:
            # Add card to user's collection
            self.add_card_to_collection(
                user_id=user_id,
                card_id=daily_card['card_id'],
                acquired_from='daily_claim'
            )
            print(f"[DAILY] User {user_id} received {daily_card['rarity']} card: {daily_card['name']}")

        # Update economy - uses user_inventory table
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_inventory
                SET gold = COALESCE(gold, 0) + ?, tickets = COALESCE(tickets, 0) + ?,
                    last_daily_claim = CURRENT_TIMESTAMP, daily_streak = ?
                WHERE user_id = ?
            """, (total_gold, tickets, new_streak, user_id))
            conn.commit()

        return {
            "success": True,
            "gold": total_gold,
            "base_gold": base_gold,
            "bonus_gold": bonus_gold,
            "tickets": tickets,
            "streak": new_streak,
            "card": daily_card  # NEW: Include card in response
        }

    def _get_random_daily_card(self) -> Optional[Dict]:
        """
        Get a random card for daily claim using rarity-weighted selection.

        Rarity Distribution:
        - 70% Common (most frequent, encourages trading)
        - 25% Rare (nice bonus)
        - 5% Epic (exciting when you get it)
        - 0% Legendary (too valuable for free daily)

        Returns random card or None if no cards available.
        """
        import random

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Determine rarity based on weighted random
            rand = random.random()
            if rand < 0.70:
                rarity = 'common'
            elif rand < 0.95:
                rarity = 'rare'
            else:
                rarity = 'epic'

            # Get all cards of this rarity
            cursor.execute(
                "SELECT * FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1",
                (rarity,)
            )
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                card = dict(zip(columns, row))
                return card

            # Fallback: get any card if specific rarity not found
            cursor.execute("SELECT * FROM cards ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            return None

        except Exception as e:
            print(f"Error getting random daily card: {e}")
            return None
        finally:
            conn.close()
    
    def record_battle(self, battle_data: Dict) -> bool:
        """Record battle result and update stats"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert battle record
                cursor.execute("""
                    INSERT INTO battle_history (
                        battle_id, player1_id, player2_id, player1_card_id, player2_card_id,
                        winner, player1_power, player2_power, player1_critical, player2_critical,
                        wager_tier, wager_amount, player1_gold_reward, player2_gold_reward,
                        player1_xp_reward, player2_xp_reward
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    battle_data['battle_id'], battle_data['player1_id'], battle_data['player2_id'],
                    battle_data['player1_card_id'], battle_data['player2_card_id'],
                    battle_data['winner'], battle_data['player1_power'], battle_data['player2_power'],
                    battle_data.get('player1_critical', False), battle_data.get('player2_critical', False),
                    battle_data['wager_tier'], battle_data['wager_amount'],
                    battle_data['player1_gold_reward'], battle_data['player2_gold_reward'],
                    battle_data['player1_xp_reward'], battle_data['player2_xp_reward']
                ))
                
                # Update player 1 stats
                cursor.execute("""
                    INSERT INTO user_battle_stats (user_id, total_battles, wins, losses, ties, 
                                                   total_gold_won, total_gold_lost, total_xp_earned,
                                                   current_win_streak, best_win_streak, last_battle_date)
                    VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        total_battles = total_battles + 1,
                        wins = wins + ?,
                        losses = losses + ?,
                        ties = ties + ?,
                        total_gold_won = total_gold_won + ?,
                        total_gold_lost = total_gold_lost + ?,
                        total_xp_earned = total_xp_earned + ?,
                        current_win_streak = CASE 
                            WHEN ? = 1 THEN current_win_streak + 1 
                            ELSE 0 
                        END,
                        best_win_streak = MAX(best_win_streak, 
                            CASE WHEN ? = 1 THEN current_win_streak + 1 ELSE 0 END),
                        last_battle_date = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    battle_data['player1_id'],
                    1 if battle_data['winner'] == 1 else 0,
                    1 if battle_data['winner'] == 2 else 0,
                    1 if battle_data['winner'] == 0 else 0,
                    battle_data['player1_gold_reward'],
                    battle_data['player1_gold_reward'] if battle_data['winner'] != 1 else 0,
                    battle_data['player1_xp_reward'],
                    1 if battle_data['winner'] == 1 else 0,
                    1 if battle_data['winner'] == 1 else 0
                ))
                
                # Update player 2 stats (similar logic)
                cursor.execute("""
                    INSERT INTO user_battle_stats (user_id, total_battles, wins, losses, ties,
                                                   total_gold_won, total_gold_lost, total_xp_earned,
                                                   current_win_streak, best_win_streak, last_battle_date)
                    VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        total_battles = total_battles + 1,
                        wins = wins + ?,
                        losses = losses + ?,
                        ties = ties + ?,
                        total_gold_won = total_gold_won + ?,
                        total_gold_lost = total_gold_lost + ?,
                        total_xp_earned = total_xp_earned + ?,
                        current_win_streak = CASE 
                            WHEN ? = 2 THEN current_win_streak + 1 
                            ELSE 0 
                        END,
                        best_win_streak = MAX(best_win_streak,
                            CASE WHEN ? = 2 THEN current_win_streak + 1 ELSE 0 END),
                        last_battle_date = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    battle_data['player2_id'],
                    1 if battle_data['winner'] == 2 else 0,
                    1 if battle_data['winner'] == 1 else 0,
                    1 if battle_data['winner'] == 0 else 0,
                    battle_data['player2_gold_reward'],
                    battle_data['player2_gold_reward'] if battle_data['winner'] != 2 else 0,
                    battle_data['player2_xp_reward'],
                    1 if battle_data['winner'] == 2 else 0,
                    1 if battle_data['winner'] == 2 else 0
                ))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error recording battle: {e}")
            return False
    
    def get_user_battle_stats(self, user_id: int) -> Dict:
        """Get user's battle statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT total_battles, wins, losses, ties, total_gold_won, total_gold_lost,
                       total_xp_earned, current_win_streak, best_win_streak, last_battle_date
                FROM user_battle_stats 
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return {
                    'total_battles': 0, 'wins': 0, 'losses': 0, 'ties': 0,
                    'total_gold_won': 0, 'total_gold_lost': 0, 'total_xp_earned': 0,
                    'current_win_streak': 0, 'best_win_streak': 0, 'last_battle_date': None
                }
            
            columns = ['total_battles', 'wins', 'losses', 'ties', 'total_gold_won', 
                      'total_gold_lost', 'total_xp_earned', 'current_win_streak', 
                      'best_win_streak', 'last_battle_date']
            stats = dict(zip(columns, result))
            
            # Calculate win rate
            total = stats['wins'] + stats['losses']
            stats['win_rate'] = (stats['wins'] / total * 100) if total > 0 else 0
            
            return stats
    
    # Cosmetic System Methods
    def add_cosmetic_to_catalog(self, cosmetic_data: Dict) -> bool:
        """Add a cosmetic to the catalog"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cosmetics_catalog
                    (cosmetic_id, cosmetic_type, name, description, rarity, 
                     unlock_method, price_gold, price_tickets, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cosmetic_data['cosmetic_id'],
                    cosmetic_data['cosmetic_type'],
                    cosmetic_data['name'],
                    cosmetic_data.get('description'),
                    cosmetic_data.get('rarity'),
                    cosmetic_data.get('unlock_method'),
                    cosmetic_data.get('price_gold'),
                    cosmetic_data.get('price_tickets'),
                    cosmetic_data.get('image_url')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding cosmetic to catalog: {e}")
            return False
    
    def unlock_cosmetic_for_user(self, user_id: str, cosmetic_id: str, source: str = 'purchase') -> bool:
        """Unlock a cosmetic for a user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get cosmetic type from catalog
                cursor.execute("SELECT cosmetic_type FROM cosmetics_catalog WHERE cosmetic_id = ?", (cosmetic_id,))
                result = cursor.fetchone()
                if not result:
                    print(f"Cosmetic {cosmetic_id} not found in catalog")
                    return False
                
                cosmetic_type = result[0]
                
                cursor.execute("""
                    INSERT OR IGNORE INTO user_cosmetics
                    (user_id, cosmetic_id, cosmetic_type, source)
                    VALUES (?, ?, ?, ?)
                """, (user_id, cosmetic_id, cosmetic_type, source))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error unlocking cosmetic: {e}")
            return False
    
    def get_user_cosmetics(self, user_id: str, cosmetic_type: str = None) -> List[Dict]:
        """Get all cosmetics unlocked by a user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if cosmetic_type:
                    cursor.execute("""
                        SELECT uc.*, cc.name, cc.description, cc.rarity
                        FROM user_cosmetics uc
                        JOIN cosmetics_catalog cc ON uc.cosmetic_id = cc.cosmetic_id
                        WHERE uc.user_id = ? AND uc.cosmetic_type = ?
                    """, (user_id, cosmetic_type))
                else:
                    cursor.execute("""
                        SELECT uc.*, cc.name, cc.description, cc.rarity
                        FROM user_cosmetics uc
                        JOIN cosmetics_catalog cc ON uc.cosmetic_id = cc.cosmetic_id
                        WHERE uc.user_id = ?
                    """, (user_id,))
                
                rows = cursor.fetchall()
                return [
                    {
                        'user_id': row[0],
                        'cosmetic_id': row[1],
                        'cosmetic_type': row[2],
                        'unlocked_at': row[3],
                        'source': row[4],
                        'name': row[5],
                        'description': row[6],
                        'rarity': row[7]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"Error getting user cosmetics: {e}")
            return []
    
    def apply_cosmetic_to_card(self, user_id: str, card_id: str, cosmetic_data: Dict) -> bool:
        """Apply cosmetics to a specific card"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO card_cosmetics
                    (user_id, card_id, frame_style, foil_effect, badge_override, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_id,
                    card_id,
                    cosmetic_data.get('frame_style'),
                    cosmetic_data.get('foil_effect'),
                    cosmetic_data.get('badge_override')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error applying cosmetic to card: {e}")
            return False
    
    async def backup_database(self, backup_type: str = "periodic") -> Optional[str]:
        """
        Create a backup of the database using BackupService
        
        Args:
            backup_type: Type of backup (periodic, critical, shutdown, daily)
            
        Returns:
            Path to backup file if successful, None otherwise
        """
        try:
            from services.backup_service import backup_service
            
            # Update backup service with correct path
            backup_service.db_path = self.db_path
            
            # Create backup
            backup_path = await backup_service.backup_to_local(backup_type)
            
            if backup_path:
                print(f"💾 Database backup created: {backup_path}")
                return backup_path
            else:
                print("⚠️ Backup creation returned None")
                return None
                
        except ImportError:
            print("⚠️ BackupService not available")
            return None
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_card_cosmetics(self, user_id: str, card_id: str) -> Optional[Dict]:
        """Get cosmetics applied to a specific card"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT frame_style, foil_effect, badge_override
                    FROM card_cosmetics
                    WHERE user_id = ? AND card_id = ?
                """, (user_id, card_id))
                row = cursor.fetchone()
                if row:
                    return {
                        'frame_style': row[0],
                        'foil_effect': row[1],
                        'badge_override': row[2]
                    }
                return None
        except Exception as e:
            print(f"Error getting card cosmetics: {e}")
            return None
    
    def get_available_cosmetics(self, unlock_method: str = None) -> List[Dict]:
        """Get cosmetics from catalog"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if unlock_method:
                    cursor.execute("""
                        SELECT * FROM cosmetics_catalog
                        WHERE unlock_method = ?
                    """, (unlock_method,))
                else:
                    cursor.execute("SELECT * FROM cosmetics_catalog")
                
                rows = cursor.fetchall()
                return [
                    {
                        'cosmetic_id': row[0],
                        'cosmetic_type': row[1],
                        'name': row[2],
                        'description': row[3],
                        'rarity': row[4],
                        'unlock_method': row[5],
                        'price_gold': row[6],
                        'price_tickets': row[7],
                        'image_url': row[8]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"Error getting available cosmetics: {e}")
            return []
    
    # ===== TRADE SYSTEM METHODS =====

    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get trade by ID"""
        conn = self._get_connection()
        ph = self._get_placeholder()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM trades WHERE trade_id = {ph}",
                (trade_id,)
            )
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            conn.close()

    def remove_card_from_collection(self, user_id: int, card_id: str) -> bool:
        """Remove card from user's collection (for trades)"""
        conn = self._get_connection()
        ph = self._get_placeholder()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM user_cards WHERE user_id = {ph} AND card_id = {ph}",
                (user_id, card_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing card from collection: {e}")
            return False
        finally:
            conn.close()

    def complete_trade(self, trade_id: str) -> bool:
        """
        Complete a trade by transferring cards and gold between users.
        This is an ATOMIC operation - either all transfers succeed or none do.
        """
        conn = self._get_connection()
        ph = self._get_placeholder()

        try:
            cursor = conn.cursor()

            # Get trade details
            cursor.execute(
                f"SELECT * FROM trades WHERE trade_id = {ph}",
                (trade_id,)
            )
            trade_row = cursor.fetchone()

            if not trade_row:
                print(f"Trade {trade_id} not found")
                return False

            # Parse trade data
            columns = [desc[0] for desc in cursor.description]
            trade = dict(zip(columns, trade_row))

            # Verify trade is pending
            if trade['status'] != 'pending':
                print(f"Trade {trade_id} is not pending (status: {trade['status']})")
                return False

            # Parse card lists from JSON
            initiator_cards = json.loads(trade['initiator_cards']) if trade['initiator_cards'] else []
            receiver_cards = json.loads(trade['receiver_cards']) if trade['receiver_cards'] else []

            print(f"🔄 [TRADE] Executing trade {trade_id}")
            print(f"   Initiator ({trade['initiator_user_id']}) → Receiver ({trade['receiver_user_id']})")
            print(f"   Cards from initiator: {len(initiator_cards)}")
            print(f"   Cards from receiver: {len(receiver_cards)}")
            print(f"   Gold from initiator: {trade['gold_from_initiator']}")
            print(f"   Gold from receiver: {trade['gold_from_receiver']}")

            # ---- ATOMIC SWAP ----

            # 1. Transfer cards from initiator to receiver
            for card_id in initiator_cards:
                # Remove from initiator
                cursor.execute(
                    f"DELETE FROM user_cards WHERE user_id = {ph} AND card_id = {ph}",
                    (trade['initiator_user_id'], card_id)
                )
                # Add to receiver
                cursor.execute(
                    f"""INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from, acquired_at)
                        VALUES ({ph}, {ph}, 'trade', CURRENT_TIMESTAMP)""",
                    (trade['receiver_user_id'], card_id)
                )
                print(f"   ✓ Card {card_id} → User {trade['receiver_user_id']}")

            # 2. Transfer cards from receiver to initiator
            for card_id in receiver_cards:
                # Remove from receiver
                cursor.execute(
                    f"DELETE FROM user_cards WHERE user_id = {ph} AND card_id = {ph}",
                    (trade['receiver_user_id'], card_id)
                )
                # Add to initiator
                cursor.execute(
                    f"""INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from, acquired_at)
                        VALUES ({ph}, {ph}, 'trade', CURRENT_TIMESTAMP)""",
                    (trade['initiator_user_id'], card_id)
                )
                print(f"   ✓ Card {card_id} → User {trade['initiator_user_id']}")

            # 3. Transfer gold from initiator to receiver
            if trade['gold_from_initiator'] > 0:
                # Deduct from initiator
                cursor.execute(
                    f"""UPDATE user_inventory
                        SET gold = COALESCE(gold, 0) - {ph}
                        WHERE user_id = {ph}""",
                    (trade['gold_from_initiator'], trade['initiator_user_id'])
                )
                # Add to receiver
                cursor.execute(
                    f"""INSERT INTO user_inventory (user_id, gold)
                        VALUES ({ph}, {ph})
                        ON CONFLICT(user_id) DO UPDATE SET gold = COALESCE(gold, 0) + {ph}""",
                    (trade['receiver_user_id'], trade['gold_from_initiator'], trade['gold_from_initiator'])
                )
                print(f"   ✓ {trade['gold_from_initiator']} gold → User {trade['receiver_user_id']}")

            # 4. Transfer gold from receiver to initiator
            if trade['gold_from_receiver'] > 0:
                # Deduct from receiver
                cursor.execute(
                    f"""UPDATE user_inventory
                        SET gold = COALESCE(gold, 0) - {ph}
                        WHERE user_id = {ph}""",
                    (trade['gold_from_receiver'], trade['receiver_user_id'])
                )
                # Add to initiator
                cursor.execute(
                    f"""INSERT INTO user_inventory (user_id, gold)
                        VALUES ({ph}, {ph})
                        ON CONFLICT(user_id) DO UPDATE SET gold = COALESCE(gold, 0) + {ph}""",
                    (trade['initiator_user_id'], trade['gold_from_receiver'], trade['gold_from_receiver'])
                )
                print(f"   ✓ {trade['gold_from_receiver']} gold → User {trade['initiator_user_id']}")

            # 5. Update trade status to completed
            cursor.execute(
                f"""UPDATE trades
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE trade_id = {ph}""",
                (trade_id,)
            )

            # 6. Insert into trade_history for permanent record
            cursor.execute(
                f"""INSERT INTO trade_history
                    (trade_id, initiator_user_id, receiver_user_id, initiator_cards, receiver_cards,
                     gold_from_initiator, gold_from_receiver, trade_date)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP)""",
                (trade_id, trade['initiator_user_id'], trade['receiver_user_id'],
                 trade['initiator_cards'], trade['receiver_cards'],
                 trade['gold_from_initiator'], trade['gold_from_receiver'])
            )

            # Commit all changes atomically
            conn.commit()

            print(f"✅ [TRADE] Trade {trade_id} completed successfully!")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ [TRADE] Error completing trade {trade_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()

    def cancel_trade(self, trade_id: str, reason: str = "cancelled") -> bool:
        """Cancel a pending trade"""
        conn = self._get_connection()
        ph = self._get_placeholder()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""UPDATE trades
                    SET status = 'cancelled', expired_at = CURRENT_TIMESTAMP
                    WHERE trade_id = {ph} AND status = 'pending'""",
                (trade_id,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                print(f"🚫 [TRADE] Trade {trade_id} cancelled: {reason}")
                return True
            return False
        except Exception as e:
            print(f"Error cancelling trade: {e}")
            return False
        finally:
            conn.close()

    def expire_old_trades(self) -> int:
        """Expire all pending trades that are past their expiration time"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades
                SET status = 'expired', expired_at = CURRENT_TIMESTAMP
                WHERE status = 'pending' AND created_at < datetime('now', '-5 minutes')
            """)
            conn.commit()
            count = cursor.rowcount
            if count > 0:
                print(f"⏰ [TRADE] Expired {count} old trades")
            return count
        except Exception as e:
            print(f"Error expiring trades: {e}")
            return 0
        finally:
            conn.close()

    def close(self):
        """Close database connection"""
        pass  # SQLite connections are closed automatically

# Global database instance for imports
db = DatabaseManager()
