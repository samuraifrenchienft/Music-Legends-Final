# packs/founder_packs_v2.py
import random
import sqlite3
from datetime import datetime
from queue.locks import user_lock
from database import DatabaseManager
from card_economy import CardEconomyManager

# -------- ODDS TABLES --------

BLACK_GUARANTEE = {
    "gold": 75,
    "platinum": 22,
    "legendary": 3
}

BLACK_STANDARD = {
    "community": 65,
    "gold": 25,
    "platinum": 8,
    "legendary": 2
}

SILVER_ODDS = {
    "community": 75,
    "gold": 20,
    "platinum": 4,
    "legendary": 1
}

PACK_BLACK = "founder_black"
PACK_SILVER = "founder_silver"

class FounderPacksV2:
    """Founder Packs with your specified structure"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
    
    def roll_tier(self, odds: dict) -> str:
        """Roll tier based on odds"""
        r = random.uniform(0, 100)
        cumulative = 0
        for tier, chance in odds.items():
            cumulative += chance
            if r <= cumulative:
                return tier
        return "community"
    
    def next_serial(self, artist_name: str, tier: str) -> int:
        """Get next serial number for artist/tier"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM cards 
                WHERE name = ? AND rarity = ?
            """, (artist_name, self._tier_to_rarity(tier)))
            
            result = cursor.fetchone()
            return (result[0] if result else 0) + 1
    
    def _tier_to_rarity(self, tier: str) -> str:
        """Convert tier to rarity for database"""
        rarity_mapping = {
            'community': 'Common',
            'gold': 'Rare', 
            'platinum': 'Epic',
            'legendary': 'Legendary'
        }
        return rarity_mapping.get(tier, 'Common')
    
    def assert_cap(self, artist_name: str, tier: str) -> str:
        """Downgrade if cap reached"""
        # This would integrate with your season system
        # For now, just return the tier (no caps enforced)
        return tier
    
    def create_card(self, artist_name: str, tier: str, source: str) -> dict:
        """Create a card with proper structure"""
        tier = self.assert_cap(artist_name, tier)
        
        serial = self.next_serial(artist_name, tier)
        serial_number = f"ML-SF-{serial:04d}"
        
        # Create card data
        card_data = {
            'card_id': f"card_{serial_number}",
            'type': 'artist',
            'name': artist_name,
            'genre': 'Unknown',  # Would get from artist data
            'rarity': self._tier_to_rarity(tier),
            'tier': tier,
            'serial_number': serial_number,
            'print_number': serial,
            'quality': 'standard',
            'acquisition_source': source,
            'spotify_artist_id': None,
            'stats': '{}'
        }
        
        # Save to database
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Add card to database
            cursor.execute("""
                INSERT INTO cards 
                (card_id, type, name, rarity, spotify_artist_id, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                card_data['card_id'], card_data['type'], card_data['name'], 
                card_data['rarity'], card_data.get('spotify_artist_id'), 0
            ))
            
            conn.commit()
        
        return card_data
    
    def random_artist(self, genre: str = None) -> str:
        """Get random artist"""
        # This would get from your artist database
        # For now, return a default
        artists = ["Artist A", "Artist B", "Artist C", "Artist D", "Artist E"]
        return random.choice(artists)
    
    def open_pack(self, user_id: str, pack_type: str, genre: str = None):
        """Main entry called from queue task"""
        with user_lock(user_id):
            with sqlite3.connect(self.db.db_path) as conn:
                try:
                    conn.execute("BEGIN TRANSACTION")
                    
                    if pack_type == PACK_BLACK:
                        cards = self._open_black(user_id, genre)
                    elif pack_type == PACK_SILVER:
                        cards = self._open_silver(user_id, genre)
                    else:
                        raise ValueError("Unknown pack type")
                    
                    # Award cards to user
                    for card in cards:
                        self.economy._award_card_to_user(user_id, card)
                    
                    # Record audit log
                    self._record_audit_log(user_id, pack_type, cards)
                    
                    conn.commit()
                    return cards
                    
                except Exception as e:
                    conn.rollback()
                    raise e
    
    def _open_black(self, user_id: str, genre: str = None):
        """Open Black Pack"""
        cards = []
        
        # Slot 1 – Gold+ guarantee
        tier1 = self.roll_tier(BLACK_GUARANTEE)
        artist = self.random_artist(genre)
        cards.append(self.create_card(artist, tier1, PACK_BLACK))
        
        # Slots 2–5 – boosted odds
        for _ in range(4):
            tier = self.roll_tier(BLACK_STANDARD)
            artist = self.random_artist(genre)
            cards.append(self.create_card(artist, tier, PACK_BLACK))
        
        # Final safety check
        assert any(c['tier'] in ["gold", "platinum", "legendary"] for c in cards), \
            "Black pack must contain Gold+"
        
        return cards
    
    def _open_silver(self, user_id: str, genre: str = None):
        """Open Silver Pack"""
        cards = []
        
        for _ in range(5):
            tier = self.roll_tier(SILVER_ODDS)
            artist = self.random_artist(genre)
            cards.append(self.create_card(artist, tier, PACK_SILVER))
        
        return cards
    
    def _record_audit_log(self, user_id: str, pack_type: str, cards: list):
        """Record pack opening audit log"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Create audit log table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT,
                    user_id TEXT,
                    pack_type TEXT,
                    cards TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Record the pack opening
            cursor.execute("""
                INSERT INTO audit_log 
                (event, user_id, pack_type, cards)
                VALUES (?, ?, ?, ?)
            """, (
                "pack_open",
                user_id,
                pack_type,
                str([c['serial_number'] for c in cards])
            ))
            
            conn.commit()

# Global instance
founder_packs_v2 = FounderPacksV2()
