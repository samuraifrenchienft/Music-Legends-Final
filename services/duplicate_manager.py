# services/duplicate_manager.py
"""
Duplicate Protection and Quantity Tracking System
Handles card duplicates, quantity tracking, and dust rewards
"""

import sqlite3
from typing import Dict, Optional, Tuple
from datetime import datetime


class DuplicateManager:
    """Manages card duplicates and quantity tracking"""
    
    # Dust rewards for duplicate cards by rarity
    DUST_REWARDS = {
        'common': 10,
        'rare': 25,
        'epic': 50,
        'legendary': 100,
        'mythic': 250
    }
    
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure duplicate protection schema exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if quantity column exists
                cursor.execute("PRAGMA table_info(user_cards)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'quantity' not in columns:
                    try:
                        cursor.execute("ALTER TABLE user_cards ADD COLUMN quantity INTEGER DEFAULT 1")
                    except sqlite3.OperationalError as e:
                        print(f"⚠️ Could not add quantity column: {e}")
                
                if 'first_acquired_at' not in columns:
                    try:
                        cursor.execute("ALTER TABLE user_cards ADD COLUMN first_acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    except sqlite3.OperationalError as e:
                        print(f"⚠️ Could not add first_acquired_at column: {e}")
                
                # Update existing records
                try:
                    cursor.execute("UPDATE user_cards SET quantity = 1 WHERE quantity IS NULL")
                except sqlite3.OperationalError:
                    pass
                
                # Create dust table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_dust (
                        user_id INTEGER PRIMARY KEY,
                        dust_amount INTEGER DEFAULT 0,
                        total_dust_earned INTEGER DEFAULT 0,
                        total_dust_spent INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Create dust transactions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dust_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount INTEGER,
                        transaction_type TEXT,
                        card_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Create index (skip if already exists)
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_user_cards_lookup 
                        ON user_cards(user_id, card_id)
                    """)
                except sqlite3.OperationalError:
                    # Index or constraint already exists, skip
                    pass
                
                conn.commit()
        except Exception as e:
            print(f"⚠️ Error ensuring duplicate protection schema: {e}")
    
    def check_duplicate(self, user_id: int, card_id: str) -> Tuple[bool, int]:
        """
        Check if user already has this card
        
        Args:
            user_id: Discord user ID
            card_id: Card ID to check
        
        Returns:
            Tuple of (is_duplicate, current_quantity)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT quantity FROM user_cards
                WHERE user_id = ? AND card_id = ?
            """, (user_id, card_id))
            
            result = cursor.fetchone()
            
            if result:
                return (True, result[0])
            else:
                return (False, 0)
    
    def add_card_with_duplicate_check(
        self,
        user_id: int,
        card_id: str,
        card_rarity: str,
        acquired_from: str = 'pack'
    ) -> Dict:
        """
        Add card to user's collection with duplicate detection
        
        Args:
            user_id: Discord user ID
            card_id: Card ID
            card_rarity: Card rarity (for dust calculation)
            acquired_from: Source of card
        
        Returns:
            Dict with duplicate info and dust earned
        """
        is_duplicate, current_quantity = self.check_duplicate(user_id, card_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if is_duplicate:
                # Increment quantity
                new_quantity = current_quantity + 1
                cursor.execute("""
                    UPDATE user_cards
                    SET quantity = ?, acquired_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND card_id = ?
                """, (new_quantity, user_id, card_id))
                
                # Award dust for duplicate
                dust_earned = self.DUST_REWARDS.get(card_rarity.lower(), 10)
                self._add_dust(user_id, dust_earned, 'earned_duplicate', card_id)
                
                conn.commit()
                
                return {
                    'is_duplicate': True,
                    'quantity': new_quantity,
                    'dust_earned': dust_earned,
                    'is_new': False
                }
            else:
                # Add new card
                cursor.execute("""
                    INSERT INTO user_cards (user_id, card_id, quantity, acquired_from, first_acquired_at)
                    VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                """, (user_id, card_id, acquired_from))
                
                conn.commit()
                
                return {
                    'is_duplicate': False,
                    'quantity': 1,
                    'dust_earned': 0,
                    'is_new': True
                }
    
    def _add_dust(self, user_id: int, amount: int, transaction_type: str, card_id: str = None):
        """Add dust to user's account"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create dust account if doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO user_dust (user_id, dust_amount, total_dust_earned)
                VALUES (?, 0, 0)
            """, (user_id,))
            
            # Add dust
            cursor.execute("""
                UPDATE user_dust
                SET dust_amount = dust_amount + ?,
                    total_dust_earned = total_dust_earned + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (amount, amount, user_id))
            
            # Log transaction
            cursor.execute("""
                INSERT INTO dust_transactions (user_id, amount, transaction_type, card_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, amount, transaction_type, card_id))
            
            conn.commit()
    
    def get_user_dust(self, user_id: int) -> Dict:
        """Get user's dust balance"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dust_amount, total_dust_earned, total_dust_spent
                FROM user_dust
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'current': result[0],
                    'total_earned': result[1],
                    'total_spent': result[2]
                }
            else:
                return {
                    'current': 0,
                    'total_earned': 0,
                    'total_spent': 0
                }
    
    def get_card_quantity(self, user_id: int, card_id: str) -> int:
        """Get quantity of a specific card user owns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT quantity FROM user_cards
                WHERE user_id = ? AND card_id = ?
            """, (user_id, card_id))
            
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_duplicate_stats(self, user_id: int) -> Dict:
        """Get user's duplicate statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total unique cards
            cursor.execute("""
                SELECT COUNT(*) FROM user_cards WHERE user_id = ?
            """, (user_id,))
            unique_cards = cursor.fetchone()[0]
            
            # Total cards including duplicates
            cursor.execute("""
                SELECT SUM(quantity) FROM user_cards WHERE user_id = ?
            """, (user_id,))
            total_cards = cursor.fetchone()[0] or 0
            
            # Cards with duplicates
            cursor.execute("""
                SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND quantity > 1
            """, (user_id,))
            cards_with_dupes = cursor.fetchone()[0]
            
            return {
                'unique_cards': unique_cards,
                'total_cards': total_cards,
                'cards_with_duplicates': cards_with_dupes,
                'duplicate_count': total_cards - unique_cards
            }


# Global instance
duplicate_manager = DuplicateManager()
