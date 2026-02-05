# season_supply.py
"""
Season 1 Supply Cap Management
Tracks global supply limits for each tier
"""
import sqlite3
from typing import Dict, Optional
from datetime import datetime

class SeasonSupply:
    """Manages Season 1 supply caps"""
    
    # Season 1 Total Supply: ~250,000 cards
    SEASON_1_CAPS = {
        'community': 180000,   # 72%
        'gold': 50000,         # 20%
        'platinum': 15000,     # 6%
        'legendary': 5000      # 2%
    }
    
    # Per-artist caps
    LEGENDARY_PER_ARTIST = 100
    PLATINUM_PER_ARTIST = 300
    
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self.init_supply_tracking()
    
    def init_supply_tracking(self):
        """Initialize supply tracking table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Global supply tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_supply (
                    season INTEGER,
                    tier TEXT,
                    minted INTEGER DEFAULT 0,
                    cap INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (season, tier)
                )
            """)
            
            # Artist-specific supply tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artist_supply (
                    season INTEGER,
                    artist_id TEXT,
                    tier TEXT,
                    minted INTEGER DEFAULT 0,
                    cap INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (season, artist_id, tier)
                )
            """)
            
            # Initialize Season 1 caps if not exists
            for tier, cap in self.SEASON_1_CAPS.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO season_supply (season, tier, minted, cap)
                    VALUES (1, ?, 0, ?)
                """, (tier, cap))
            
            conn.commit()
    
    def can_mint(self, tier: str, artist_id: Optional[str] = None, season: int = 1) -> Dict:
        """Check if a card can be minted within supply caps"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check global cap
            cursor.execute("""
                SELECT minted, cap FROM season_supply
                WHERE season = ? AND tier = ?
            """, (season, tier))
            
            result = cursor.fetchone()
            if not result:
                return {'can_mint': False, 'reason': 'Invalid tier or season'}
            
            minted, cap = result
            if minted >= cap:
                return {
                    'can_mint': False,
                    'reason': f'Global {tier} cap reached ({minted}/{cap})'
                }
            
            # Check artist-specific cap for Legendary/Platinum
            if artist_id and tier in ['legendary', 'platinum']:
                artist_cap = self.LEGENDARY_PER_ARTIST if tier == 'legendary' else self.PLATINUM_PER_ARTIST
                
                cursor.execute("""
                    SELECT minted FROM artist_supply
                    WHERE season = ? AND artist_id = ? AND tier = ?
                """, (season, artist_id, tier))
                
                artist_result = cursor.fetchone()
                artist_minted = artist_result[0] if artist_result else 0
                
                if artist_minted >= artist_cap:
                    return {
                        'can_mint': False,
                        'reason': f'Artist {tier} cap reached ({artist_minted}/{artist_cap})'
                    }
            
            return {
                'can_mint': True,
                'global_remaining': cap - minted,
                'global_minted': minted,
                'global_cap': cap
            }
    
    def record_mint(self, tier: str, artist_id: Optional[str] = None, season: int = 1) -> bool:
        """Record a card mint with atomic cap check to prevent oversupply"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            try:
                # Check global cap inside transaction
                cursor.execute("""
                    SELECT minted, cap FROM season_supply
                    WHERE season = ? AND tier = ?
                """, (season, tier))
                row = cursor.fetchone()
                if row and row[0] >= row[1]:
                    conn.rollback()
                    return False  # Cap reached

                # Update global supply
                cursor.execute("""
                    UPDATE season_supply
                    SET minted = minted + 1, last_updated = CURRENT_TIMESTAMP
                    WHERE season = ? AND tier = ?
                """, (season, tier))

                # Update artist supply for Legendary/Platinum
                if artist_id and tier in ['legendary', 'platinum']:
                    artist_cap = self.LEGENDARY_PER_ARTIST if tier == 'legendary' else self.PLATINUM_PER_ARTIST

                    # Check artist cap inside transaction
                    cursor.execute("""
                        SELECT minted FROM artist_supply
                        WHERE season = ? AND artist_id = ? AND tier = ?
                    """, (season, artist_id, tier))
                    artist_row = cursor.fetchone()
                    if artist_row and artist_row[0] >= artist_cap:
                        conn.rollback()
                        return False  # Artist cap reached

                    cursor.execute("""
                        INSERT INTO artist_supply (season, artist_id, tier, minted, cap)
                        VALUES (?, ?, ?, 1, ?)
                        ON CONFLICT(season, artist_id, tier)
                        DO UPDATE SET minted = minted + 1, last_updated = CURRENT_TIMESTAMP
                    """, (season, artist_id, tier, artist_cap))

                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise
    
    def get_supply_status(self, season: int = 1) -> Dict:
        """Get current supply status for a season"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT tier, minted, cap
                FROM season_supply
                WHERE season = ?
                ORDER BY 
                    CASE tier
                        WHEN 'legendary' THEN 1
                        WHEN 'platinum' THEN 2
                        WHEN 'gold' THEN 3
                        WHEN 'community' THEN 4
                    END
            """, (season,))
            
            supply_data = {}
            total_minted = 0
            total_cap = 0
            
            for tier, minted, cap in cursor.fetchall():
                supply_data[tier] = {
                    'minted': minted,
                    'cap': cap,
                    'remaining': cap - minted,
                    'percentage': (minted / cap * 100) if cap > 0 else 0
                }
                total_minted += minted
                total_cap += cap
            
            return {
                'season': season,
                'tiers': supply_data,
                'total_minted': total_minted,
                'total_cap': total_cap,
                'total_remaining': total_cap - total_minted
            }

# Global instance
season_supply = SeasonSupply()
