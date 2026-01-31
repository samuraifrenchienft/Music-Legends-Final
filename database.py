# database.py
import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize all database tables"""
        with sqlite3.connect(self.db_path) as conn:
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
            
            # Cards table (minimal storage - Spotify canonical)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL DEFAULT 'artist', -- 'artist' or 'song'
                    spotify_artist_id TEXT,
                    spotify_track_id TEXT,
                    name TEXT NOT NULL,
                    title TEXT,
                    image_url TEXT,
                    spotify_url TEXT,
                    youtube_url TEXT,
                    rarity TEXT NOT NULL,
                    variant TEXT DEFAULT 'Classic',
                    era TEXT,
                    impact INTEGER,
                    skill INTEGER,
                    longevity INTEGER,
                    culture INTEGER,
                    hype INTEGER,
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
            
            # User economy - gold, tickets, daily claims
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_economy (
                    user_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 500,
                    tickets INTEGER DEFAULT 0,
                    last_daily_claim TIMESTAMP,
                    daily_streak INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
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
            
            # Add indexes for economy tables
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_economy_gold ON user_economy(gold)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_players ON battle_history(player1_id, player2_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_date ON battle_history(battle_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_user ON user_quests(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_date ON user_quests(quest_date)")
            
            conn.commit()
    
    def get_or_create_user(self, user_id: int, username: str, discord_tag: str) -> Dict:
        """Get existing user or create new one"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to get existing user
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user:
                # Update last active
                cursor.execute(
                    "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                columns = [desc[0] for desc in cursor.description]
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
            with sqlite3.connect(self.db_path) as conn:
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
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO cards 
                    (card_id, name, title, rarity, era, variant, impact, skill, 
                     longevity, culture, hype, image_url, spotify_url, youtube_url, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        card_data['card_id'], 
                        card_data['name'], 
                        card_data.get('title', ''),
                        card_data['rarity'], 
                        card_data.get('era'), 
                        card_data.get('variant'),
                        card_data.get('impact', 0), 
                        card_data.get('skill', 0),
                        card_data.get('longevity', 0), 
                        card_data.get('culture', 0),
                        card_data.get('hype', 0), 
                        card_data.get('image_url'),
                        card_data.get('spotify_url'), 
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
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, card_id, acquired_from)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error adding card to collection: {e}")
            return False
    
    def get_user_collection(self, user_id: int) -> List[Dict]:
        """Get all cards owned by a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.*, uc.acquired_at, uc.acquired_from, uc.is_favorite
                FROM cards c
                JOIN user_cards uc ON c.card_id = uc.card_id
                WHERE uc.user_id = ?
                ORDER BY c.rarity DESC, c.name
                """,
                (user_id,)
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_user_deck(self, user_id: int, limit: int = 3) -> List[Dict]:
        """Get user's deck (first N cards from collection)"""
        collection = self.get_user_collection(user_id)
        return collection[:limit]
    
    def record_match(self, match_data: Dict) -> bool:
        """Record a completed match"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        
        with sqlite3.connect(self.db_path) as conn:
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
        
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
                if not card.get('spotify_url'):
                    warnings.append(f"Card {i+1} missing Spotify link")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "pack_info": pack
            }
    
    def publish_pack(self, pack_id: str, stripe_payment_id: str) -> bool:
        """Publish pack after payment confirmation"""
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, COALESCE(u.username, 'System') as creator_name
                FROM creator_packs p
                LEFT JOIN users u ON p.creator_id = u.user_id
                WHERE p.status = 'LIVE'
                ORDER BY p.published_at DESC
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
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
        
        with sqlite3.connect(self.db_path) as conn:
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
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get pack data and creator
            cursor.execute("""
                SELECT cards_data, creator_id, name FROM creator_packs 
                WHERE pack_id = ? AND status = 'LIVE'
            """, (pack_id,))
            result = cursor.fetchone()
            if not result:
                return None
            
            cards_data, creator_id, pack_name = result[0], result[1], result[2]
            
            # Generate cards for buyer (add to their collection)
            received_cards = []
            for card_data in cards_data:
                card_id = self.add_card_to_master_list(card_data)
                self.add_card_to_user_collection(buyer_id, card_id, 'pack')
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO creator_stripe_accounts 
                (creator_user_id, stripe_account_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (creator_id, stripe_account_id))
            conn.commit()
    
    def get_creator_stripe_account(self, creator_id: int) -> Dict:
        """Get creator's Stripe Connect account info"""
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO servers 
                (server_id, server_name, server_owner_id, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (server_id, server_name, owner_id))
            conn.commit()
    
    def get_server_info(self, server_id: int) -> Dict:
        """Get server subscription and usage info"""
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO server_usage (server_id, metric_type, metric_value)
                VALUES (?, ?, ?)
            """, (server_id, metric_type, value))
            conn.commit()
    
    def get_server_analytics(self, server_id: int, days: int = 30) -> Dict:
        """Get server usage analytics"""
        with sqlite3.connect(self.db_path) as conn:
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
        # Generate card_id based on Spotify data
        if card_data.get('spotify_id'):
            card_id = f"spotify_{card_data['spotify_id']}"
        else:
            card_id = f"{card_data['name'].lower().replace(' ', '_')}_{card_data.get('rarity', 'Common').lower()}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO cards 
                (card_id, type, spotify_artist_id, spotify_track_id, name, title, image_url, 
                 spotify_url, youtube_url, rarity, variant, impact, skill, longevity, culture, hype,
                 effect_type, effect_value, pack_id, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                card_data.get('type', 'artist'),
                card_data.get('spotify_id'),
                card_data.get('spotify_track_id'),
                card_data.get('name'),
                card_data.get('title', ''),
                card_data.get('image_url', ''),
                card_data.get('spotify_url', ''),
                card_data.get('youtube_url', ''),
                card_data.get('rarity', 'Common'),
                card_data.get('variant', 'Classic'),
                card_data.get('impact', 50),
                card_data.get('skill', 50),
                card_data.get('longevity', 50),
                card_data.get('culture', 50),
                card_data.get('hype', 50),
                card_data.get('effect_type'),
                card_data.get('effect_value'),
                card_data.get('pack_id'),
                card_data.get('created_by_user_id')
            ))
            
            conn.commit()
            return card_id
    
    def get_all_artists(self, limit: int = 100) -> List[Dict]:
        """Get all unique artists from the cards table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT name, image_url, spotify_url
                FROM cards 
                WHERE name IS NOT NULL AND name != ''
                LIMIT ?
            """, (limit,))
            
            artists = []
            for row in cursor.fetchall():
                artists.append({
                    'name': row[0],
                    'image_url': row[1],
                    'spotify_url': row[2],
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
                        'spotify_url': '',
                        'stats': {}
                    })
            
            return artists
    
    # ===== ECONOMY METHODS =====
    
    def get_user_economy(self, user_id: int) -> Dict:
        """Get user's economy data (gold, tickets, daily streak)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, gold, tickets, last_daily_claim, daily_streak, created_at, updated_at
                FROM user_economy 
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                # Create new economy record for user
                cursor.execute("""
                    INSERT INTO user_economy (user_id, gold, tickets)
                    VALUES (?, 500, 0)
                """, (user_id,))
                conn.commit()
                
                cursor.execute("""
                    SELECT user_id, gold, tickets, last_daily_claim, daily_streak, created_at, updated_at
                    FROM user_economy 
                    WHERE user_id = ?
                """, (user_id,))
                result = cursor.fetchone()
            
            columns = ['user_id', 'gold', 'tickets', 'last_daily_claim', 'daily_streak', 'created_at', 'updated_at']
            return dict(zip(columns, result))
    
    def update_user_economy(self, user_id: int, gold_change: int = 0, tickets_change: int = 0) -> bool:
        """Update user's gold and tickets"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_economy 
                    SET gold = gold + ?, tickets = tickets + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (gold_change, tickets_change, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating user economy: {e}")
            return False
    
    def claim_daily_reward(self, user_id: int) -> Dict:
        """Process daily reward claim"""
        from datetime import datetime, timedelta
        
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
        
        # Update economy
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_economy 
                SET gold = gold + ?, tickets = tickets + ?, 
                    last_daily_claim = CURRENT_TIMESTAMP, daily_streak = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (total_gold, tickets, new_streak, user_id))
            conn.commit()
        
        return {
            "success": True,
            "gold": total_gold,
            "base_gold": base_gold,
            "bonus_gold": bonus_gold,
            "tickets": tickets,
            "streak": new_streak
        }
    
    def record_battle(self, battle_data: Dict) -> bool:
        """Record battle result and update stats"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
    
    def get_card_cosmetics(self, user_id: str, card_id: str) -> Optional[Dict]:
        """Get cosmetics applied to a specific card"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
    
    def close(self):
        """Close database connection"""
        pass  # SQLite connections are closed automatically

# Global database instance for imports
db = DatabaseManager()
