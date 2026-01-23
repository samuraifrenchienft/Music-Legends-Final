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
        """Add a card to the master card list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO cards 
                    (card_id, name, title, rarity, era, variant, impact, skill, 
                     longevity, culture, hype, image_url, spotify_url, youtube_url, card_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        card_data['card_id'], card_data['name'], card_data.get('title'),
                        card_data['rarity'], card_data.get('era'), card_data.get('variant'),
                        card_data.get('impact', 0), card_data.get('skill', 0),
                        card_data.get('longevity', 0), card_data.get('culture', 0),
                        card_data.get('hype', 0), card_data.get('image_url'),
                        card_data.get('spotify_url'), card_data.get('youtube_url'),
                        card_data.get('card_type', 'artist')
                    )
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error adding card: {e}")
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
                SELECT p.*, u.username as creator_name
                FROM creator_packs p
                JOIN users u ON p.creator_id = u.user_id
                WHERE p.status = 'LIVE'
                ORDER BY p.published_at DESC
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
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
    
    def close(self):
        """Close database connection"""
        pass  # SQLite connections are closed automatically
