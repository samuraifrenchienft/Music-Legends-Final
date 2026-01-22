# card_economy.py
import sqlite3
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import DatabaseManager

class CardEconomyManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.drop_cooldowns = {}  # server_id -> last_drop_time
        self.active_drops = {}    # channel_id -> drop_data
        
        # Import season manager (lazy import to avoid circular import)
        self.season_manager = None
        
        # Drop rates (percentages)
        self.pack_odds = {
            'genre_pack': {
                'guaranteed_gold_plus': {'gold': 75, 'platinum': 22, 'legendary': 3},
                'other_slots': {'community': 70, 'gold': 25, 'platinum': 5}
            },
            'hero_pack': {
                'hero_slot': {'platinum': 80, 'legendary': 20},
                'support_slots': {'community': 60, 'gold': 30, 'platinum': 10}
            }
        }
        
        # Currency values
        self.tier_values = {
            'community': {'dust_value': 1, 'gold_value': 0},
            'gold': {'dust_value': 5, 'gold_value': 1},
            'platinum': {'dust_value': 25, 'gold_value': 5},
            'legendary': {'dust_value': 100, 'gold_value': 20}
        }
        
        # Upgrade costs
        self.upgrade_costs = {
            'community_to_gold': 5,      # 5 community -> 1 gold
            'gold_to_platinum': 5,       # 5 gold -> 1 platinum  
            'platinum_to_legendary': 3    # 3 platinum + dust -> legendary chance
        }

    def initialize_economy_tables(self):
        """Create economy-related database tables"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Enhanced cards table with economy metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    artist_name TEXT NOT NULL,
                    genre TEXT,
                    tier TEXT NOT NULL CHECK (tier IN ('community', 'gold', 'platinum', 'legendary')),
                    serial_number TEXT UNIQUE,
                    print_number INTEGER,
                    quality TEXT DEFAULT 'standard',
                    acquisition_source TEXT,
                    owner_user_id INTEGER,
                    acquisition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    owner_history TEXT, -- JSON array of previous owners
                    spotify_id TEXT,
                    stats TEXT, -- JSON object with card stats
                    FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
                )
            """)
            
            # User inventory and currency
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 0,
                    dust INTEGER DEFAULT 0,
                    tickets INTEGER DEFAULT 0,
                    gems INTEGER DEFAULT 0,
                    keys INTEGER DEFAULT 0,
                    total_cards_obtained INTEGER DEFAULT 0,
                    unique_artists TEXT, -- JSON array of unique artists collected
                    collection_value INTEGER DEFAULT 0,
                    last_daily TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Active drops
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_drops (
                    drop_id TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    server_id INTEGER,
                    initiator_user_id INTEGER,
                    cards TEXT, -- JSON array of card data
                    drop_type TEXT DEFAULT 'standard',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    claimed_by INTEGER,
                    claimed_at TIMESTAMP,
                    FOREIGN KEY (initiator_user_id) REFERENCES users(user_id)
                )
            """)
            
            # Drop cooldowns per server
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_drop_cooldowns (
                    server_id INTEGER PRIMARY KEY,
                    last_drop_time TIMESTAMP,
                    drop_count_today INTEGER DEFAULT 0,
                    activity_level INTEGER DEFAULT 1, -- 1-5 scale
                    last_activity_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Market listings
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

    def generate_serial_number(self, artist_name: str, tier: str, print_number: int) -> str:
        """Generate unique serial number for card"""
        # Format: ML-ARTIST-TIER-#### (e.g., ML-TSWIFT-GOLD-0001)
        artist_code = artist_name[:6].upper().replace(' ', '')
        tier_code = tier.upper()[:3]
        return f"ML-{artist_code}-{tier_code}-{print_number:04d}"

    def create_card(self, artist_data: Dict, tier: str = None, acquisition_source: str = 'drop') -> Dict:
        """Create a new card with given artist data and tier"""
        if tier is None:
            # Random tier based on drop rates
            tier = self._random_tier_from_drop()
        
        # Map tier to rarity for existing system
        rarity_mapping = {
            'community': 'Common',
            'gold': 'Rare', 
            'platinum': 'Epic',
            'legendary': 'Legendary'
        }
        rarity = rarity_mapping.get(tier, 'Common')
        
        # Check season caps if season manager is available
        if self.season_manager:
            cap_check = self.season_manager.check_card_cap(artist_data['name'], tier)
            if not cap_check['can_print']:
                # Fallback to lower tier if cap reached
                if tier == 'legendary':
                    tier = 'platinum'
                elif tier == 'platinum':
                    tier = 'gold'
                elif tier == 'gold':
                    tier = 'community'
                
                # Check again
                cap_check = self.season_manager.check_card_cap(artist_data['name'], tier)
                if not cap_check['can_print']:
                    # If still can't print, return None
                    return None
        
        # Generate card ID based on existing system
        import uuid
        card_id = str(uuid.uuid4())
        
        # Generate serial number
        print_number = self._get_next_print_number(artist_data['name'], tier)
        serial_number = self.generate_serial_number(artist_data['name'], tier, print_number)
        
        # Map to existing card structure
        card_data = {
            'card_id': card_id,
            'type': 'artist',
            'name': artist_data['name'],
            'rarity': rarity,
            'tier': tier,
            'serial_number': serial_number,
            'print_number': print_number,
            'quality': random.choice(['standard', 'foil', 'etched'])[0] if random.random() < 0.1 else 'standard',
            'acquisition_source': acquisition_source,
            'spotify_artist_id': artist_data.get('spotify_id'),
            'stats': json.dumps(artist_data.get('stats', {}))
        }
        
        # Increment season print count
        if self.season_manager:
            self.season_manager.increment_card_print(artist_data['name'], tier)
        
        return card_data

    def _random_tier_from_drop(self, pack_type: str = 'standard') -> str:
        """Generate random tier based on drop rates"""
        if pack_type == 'genre_pack':
            # Genre pack rates
            roll = random.random() * 100
            if roll < 3:
                return 'legendary'
            elif roll < 25:
                return 'platinum'
            elif roll < 75:
                return 'gold'
            else:
                return 'community'
        elif pack_type == 'hero_pack':
            # Hero pack rates  
            roll = random.random() * 100
            if roll < 20:
                return 'legendary'
            elif roll < 80:
                return 'platinum'
            else:
                return 'gold'
        else:
            # Standard drop rates
            roll = random.random() * 100
            if roll < 2:
                return 'legendary'
            elif roll < 12:
                return 'platinum'
            elif roll < 37:
                return 'gold'
            else:
                return 'community'

    def _get_next_print_number(self, artist_name: str, tier: str) -> int:
        """Get next print number for artist/tier combination"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(print_number) FROM cards 
                WHERE artist_name = ? AND tier = ?
            """, (artist_name, tier))
            result = cursor.fetchone()
            return (result[0] or 0) + 1

    def create_drop(self, channel_id: int, server_id: int, initiator_id: int, drop_type: str = 'standard') -> Dict:
        """Create a new card drop in a channel"""
        # Check cooldown
        if not self._can_drop(server_id):
            return {'success': False, 'error': 'Drop on cooldown'}
        
        # Generate cards for drop
        cards = []
        if drop_type == 'standard':
            # Standard 3-card drop
            for _ in range(3):
                # Get random artist from database
                artists = self.db.get_all_artists(limit=100)
                if artists:
                    artist = random.choice(artists)
                    card = self.create_card(artist, acquisition_source='drop')
                    cards.append(card)
        
        # Create drop record
        drop_id = f"drop_{channel_id}_{int(time.time())}"
        expires_at = datetime.now() + timedelta(minutes=5)  # 5 minute expiry
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO active_drops 
                (drop_id, channel_id, server_id, initiator_user_id, cards, drop_type, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (drop_id, channel_id, server_id, initiator_id, json.dumps(cards), drop_type, expires_at))
            
            # Update server cooldown
            self._update_server_cooldown(server_id)
            conn.commit()
        
        # Store in active drops for quick access
        self.active_drops[channel_id] = {
            'drop_id': drop_id,
            'cards': cards,
            'initiator_id': initiator_id,
            'expires_at': expires_at
        }
        
        return {
            'success': True,
            'drop_id': drop_id,
            'cards': cards,
            'expires_at': expires_at
        }

    def _can_drop(self, server_id: int) -> bool:
        """Check if server can drop based on cooldown and activity"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_drop_time, activity_level FROM server_drop_cooldowns 
                WHERE server_id = ?
            """, (server_id,))
            result = cursor.fetchone()
            
            if not result:
                return True  # First drop
            
            last_drop, activity_level = result
            if not last_drop:
                return True
            
            # Cooldown based on activity level (1-5)
            cooldown_minutes = max(1, 30 - (activity_level * 6))  # 30 min to 1 min
            cooldown_time = datetime.now() - timedelta(minutes=cooldown_minutes)
            
            return datetime.fromisoformat(last_drop) < cooldown_time

    def _update_server_cooldown(self, server_id: int):
        """Update server drop cooldown and activity"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO server_drop_cooldowns 
                (server_id, last_drop_time, drop_count_today, last_activity_update)
                VALUES (?, CURRENT_TIMESTAMP, 
                    COALESCE((SELECT drop_count_today FROM server_drop_cooldowns WHERE server_id = ?), 0) + 1,
                    CURRENT_TIMESTAMP)
            """, (server_id, server_id))
            conn.commit()

    def claim_drop(self, channel_id: int, user_id: int, reaction_number: int) -> Dict:
        """Claim a card from an active drop"""
        if channel_id not in self.active_drops:
            return {'success': False, 'error': 'No active drop'}
        
        drop = self.active_drops[channel_id]
        
        # Check if expired
        if datetime.now() > drop['expires_at']:
            del self.active_drops[channel_id]
            return {'success': False, 'error': 'Drop expired'}
        
        # Check if valid reaction number
        if reaction_number < 1 or reaction_number > len(drop['cards']):
            return {'success': False, 'error': 'Invalid card number'}
        
        # Get the card
        card = drop['cards'][reaction_number - 1]
        
        # Award card to user
        self._award_card_to_user(user_id, card)
        
        # Update drop as claimed
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE active_drops 
                SET claimed_by = ?, claimed_at = CURRENT_TIMESTAMP
                WHERE drop_id = ?
            """, (user_id, drop['drop_id']))
            conn.commit()
        
        # Remove from active drops
        del self.active_drops[channel_id]
        
        return {
            'success': True,
            'card': card,
            'drop_id': drop['drop_id']
        }

    def _award_card_to_user(self, user_id: int, card_data: Dict):
        """Award a card to a user's inventory"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Add card to existing cards table
            cursor.execute("""
                INSERT INTO cards 
                (card_id, type, name, rarity, spotify_artist_id, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                card_data['card_id'], card_data['type'], card_data['name'], 
                card_data['rarity'], card_data.get('spotify_artist_id'), user_id
            ))
            
            # Add to user_cards table (existing ownership system)
            cursor.execute("""
                INSERT INTO user_cards 
                (user_id, card_id, acquisition_date, acquisition_source)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, (user_id, card_data['card_id'], card_data['acquisition_source']))
            
            # Update user inventory (new system)
            cursor.execute("""
                INSERT OR REPLACE INTO user_inventory 
                (user_id, total_cards_obtained, collection_value)
                VALUES (?, 
                    COALESCE((SELECT total_cards_obtained FROM user_inventory WHERE user_id = ?), 0) + 1,
                    COALESCE((SELECT collection_value FROM user_inventory WHERE user_id = ?), 0) + ?
                )
            """, (user_id, user_id, user_id, self.tier_values[card_data['tier']]['gold_value']))
            
            conn.commit()
        
        # Update season progress
        if self.season_manager:
            self.season_manager.update_player_progress(user_id, 'card_collected', 1)
            
            # Check if this is a unique artist for the user
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM cards c
                    JOIN user_cards uc ON c.card_id = uc.card_id
                    WHERE uc.user_id = ? AND c.name = ?
                """, (user_id, card_data['name']))
                
                if cursor.fetchone()[0] == 1:  # First card of this artist
                    self.season_manager.update_player_progress(user_id, 'unique_artist', 1)

    def get_user_collection(self, user_id: int) -> Dict:
        """Get user's card collection and inventory"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get user inventory
            cursor.execute("SELECT * FROM user_inventory WHERE user_id = ?", (user_id,))
            inventory = cursor.fetchone()
            
            # Get user's cards
            cursor.execute("""
                SELECT * FROM cards WHERE owner_user_id = ? 
                ORDER BY tier DESC, acquisition_date DESC
            """, (user_id,))
            cards = cursor.fetchall()
            
            return {
                'inventory': inventory,
                'cards': cards,
                'total_cards': len(cards)
            }

    def burn_card_for_dust(self, user_id: int, card_id: str) -> Dict:
        """Burn a card to get dust"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get card details
            cursor.execute("SELECT * FROM cards WHERE card_id = ? AND owner_user_id = ?", (card_id, user_id))
            card = cursor.fetchone()
            
            if not card:
                return {'success': False, 'error': 'Card not found'}
            
            # Get dust value
            dust_value = self.tier_values[card[3]]['dust_value']  # tier is at index 3
            
            # Delete card
            cursor.execute("DELETE FROM cards WHERE card_id = ?", (card_id,))
            
            # Add dust to user inventory
            cursor.execute("""
                INSERT OR REPLACE INTO user_inventory 
                (user_id, dust)
                VALUES (?, 
                    COALESCE((SELECT dust FROM user_inventory WHERE user_id = ?), 0) + ?
                )
            """, (user_id, user_id, dust_value))
            
            conn.commit()
            
            return {
                'success': True,
                'dust_earned': dust_value,
                'card_burned': card_id
            }

    def upgrade_cards(self, user_id: int, upgrade_type: str, card_ids: List[str] = None) -> Dict:
        """Upgrade cards to higher tier"""
        if upgrade_type == 'community_to_gold':
            required_cards = 5
            target_tier = 'gold'
        elif upgrade_type == 'gold_to_platinum':
            required_cards = 5
            target_tier = 'platinum'
        elif upgrade_type == 'platinum_to_legendary':
            required_cards = 3
            target_tier = 'legendary'
        else:
            return {'success': False, 'error': 'Invalid upgrade type'}
        
        if not card_ids or len(card_ids) < required_cards:
            return {'success': False, 'error': f'Need {required_cards} cards for upgrade'}
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Verify user owns all cards and they're correct tier
            source_tier = upgrade_type.split('_to_')[0]
            cursor.execute("""
                SELECT card_id FROM cards 
                WHERE card_id IN ({}) AND owner_user_id = ? AND tier = ?
            """.format(','.join(['?'] * len(card_ids))), card_ids + [user_id, source_tier])
            
            owned_cards = cursor.fetchall()
            
            if len(owned_cards) < required_cards:
                return {'success': False, 'error': 'Not enough valid cards for upgrade'}
            
            # Delete source cards
            for card_id in card_ids[:required_cards]:
                cursor.execute("DELETE FROM cards WHERE card_id = ?", (card_id,))
            
            # Create new upgraded card
            # For simplicity, create a random artist card of target tier
            artists = self.db.get_all_artists(limit=50)
            if artists:
                artist = random.choice(artists)
                new_card = self.create_card(artist, target_tier, 'upgrade')
                self._award_card_to_user(user_id, new_card)
                
                conn.commit()
                
                return {
                    'success': True,
                    'new_card': new_card,
                    'cards_used': card_ids[:required_cards]
                }
        
        return {'success': False, 'error': 'Failed to create upgraded card'}

# Global economy manager instance
economy_manager = None
