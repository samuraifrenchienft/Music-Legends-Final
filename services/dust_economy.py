# services/dust_economy.py
"""
Hybrid Dust Economy System
Supports crafting, pack purchase, stat boosting, and cosmetics
"""

import sqlite3
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import random


class DustEconomy:
    """Manages dust economy - crafting, boosting, packs, cosmetics"""
    
    # Dust earning rates (from duplicates)
    DUST_REWARDS = {
        'common': 10,
        'rare': 25,
        'epic': 50,
        'legendary': 100,
        'mythic': 250
    }
    
    # Card crafting costs
    CRAFT_COSTS = {
        'common': 50,
        'rare': 100,
        'epic': 200,
        'legendary': 500,
        'mythic': 1000
    }
    
    # Pack purchase costs
    PACK_COSTS = {
        'community': 500,
        'gold': 1000,
        'premium': 2000
    }
    
    # Stat boosting costs
    BOOST_COSTS = {
        'small': 100,   # +5 to one stat
        'medium': 250,  # +10 to one stat
        'large': 500,   # +15 to one stat
        'reroll': 150   # Reroll all stats
    }
    
    # Cosmetic costs
    COSMETIC_COSTS = {
        'animated_border': 200,
        'holographic': 500,
        'custom_frame': 1000,
        'signature': 2000,
        'foil': 300
    }
    
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
    
    def get_dust_balance(self, user_id: int) -> int:
        """Get user's current dust balance"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dust_amount FROM user_dust WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def spend_dust(
        self,
        user_id: int,
        amount: int,
        transaction_type: str,
        item_id: str = None
    ) -> bool:
        """
        Spend dust from user's account
        
        Returns:
            True if successful, False if insufficient dust
        """
        current_balance = self.get_dust_balance(user_id)
        
        if current_balance < amount:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Deduct dust
            cursor.execute("""
                UPDATE user_dust
                SET dust_amount = dust_amount - ?,
                    total_dust_spent = total_dust_spent + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (amount, amount, user_id))
            
            # Log transaction
            cursor.execute("""
                INSERT INTO dust_transactions (user_id, amount, transaction_type, card_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, -amount, transaction_type, item_id))
            
            conn.commit()
            return True
    
    def craft_card(
        self,
        user_id: int,
        card_id: str,
        card_rarity: str,
        card_data: Dict
    ) -> Tuple[bool, str]:
        """
        Craft a specific card using dust
        
        Returns:
            (success, message)
        """
        cost = self.CRAFT_COSTS.get(card_rarity.lower(), 100)
        
        # Check if user already has this card
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT quantity FROM user_cards
                WHERE user_id = ? AND card_id = ?
            """, (user_id, card_id))
            existing = cursor.fetchone()
        
        if existing:
            return (False, f"❌ You already own this card (x{existing[0]}). You can't craft duplicates.")
        
        # Check dust balance
        if not self.spend_dust(user_id, cost, 'spent_craft', card_id):
            current = self.get_dust_balance(user_id)
            return (False, f"❌ Insufficient dust! Need {cost}, you have {current}")
        
        # Add card to collection
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Add to master cards if doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO cards (
                    card_id, name, title, rarity, image_url, youtube_url,
                    impact, skill, longevity, culture, hype
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                card_data.get('name', 'Unknown'),
                card_data.get('title', 'Crafted Card'),
                card_rarity,
                card_data.get('image_url', ''),
                card_data.get('youtube_url', ''),
                card_data.get('impact', 50),
                card_data.get('skill', 50),
                card_data.get('longevity', 50),
                card_data.get('culture', 50),
                card_data.get('hype', 50)
            ))
            
            # Add to user collection
            cursor.execute("""
                INSERT INTO user_cards (user_id, card_id, quantity, acquired_from)
                VALUES (?, ?, 1, 'crafted')
            """, (user_id, card_id))
            
            conn.commit()
        
        return (True, f"✅ Crafted **{card_data.get('name')}** for {cost} dust!")
    
    def buy_pack_with_dust(
        self,
        user_id: int,
        pack_type: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Purchase a pack using dust
        
        Returns:
            (success, message, pack_id)
        """
        cost = self.PACK_COSTS.get(pack_type.lower(), 500)
        
        # Check dust balance and spend
        if not self.spend_dust(user_id, cost, 'spent_pack_purchase', pack_type):
            current = self.get_dust_balance(user_id)
            return (False, f"❌ Insufficient dust! Need {cost}, you have {current}", None)
        
        # Create pack purchase record
        pack_id = f"dust_pack_{user_id}_{int(datetime.now().timestamp())}"
        
        return (True, f"✅ Purchased {pack_type.title()} Pack for {cost} dust!", pack_id)
    
    def boost_card_stat(
        self,
        user_id: int,
        card_id: str,
        stat_name: str,
        boost_level: str = 'small'
    ) -> Tuple[bool, str]:
        """
        Boost a card's stat using dust
        
        Args:
            boost_level: 'small' (+5), 'medium' (+10), 'large' (+15)
        """
        cost = self.BOOST_COSTS.get(boost_level, 100)
        boost_amount = {'small': 5, 'medium': 10, 'large': 15}.get(boost_level, 5)
        
        # Check if user owns the card
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT uc.id FROM user_cards uc
                WHERE uc.user_id = ? AND uc.card_id = ?
            """, (user_id, card_id))
            
            if not cursor.fetchone():
                return (False, "❌ You don't own this card!")
        
        # Check dust and spend
        if not self.spend_dust(user_id, cost, 'spent_boost', card_id):
            current = self.get_dust_balance(user_id)
            return (False, f"❌ Insufficient dust! Need {cost}, you have {current}")
        
        # Boost the stat
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current stat value
            cursor.execute(f"""
                SELECT {stat_name} FROM cards WHERE card_id = ?
            """, (card_id,))
            current_stat = cursor.fetchone()[0]
            new_stat = min(99, current_stat + boost_amount)  # Cap at 99
            
            # Update stat
            cursor.execute(f"""
                UPDATE cards SET {stat_name} = ? WHERE card_id = ?
            """, (new_stat, card_id))
            
            conn.commit()
        
        return (True, f"✅ Boosted {stat_name} by +{boost_amount} (now {new_stat}) for {cost} dust!")
    
    def reroll_card_stats(
        self,
        user_id: int,
        card_id: str,
        card_rarity: str
    ) -> Tuple[bool, str, Dict]:
        """
        Reroll all stats on a card
        
        Returns:
            (success, message, new_stats)
        """
        cost = self.BOOST_COSTS['reroll']
        
        # Check ownership
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT uc.id FROM user_cards uc
                WHERE uc.user_id = ? AND uc.card_id = ?
            """, (user_id, card_id))
            
            if not cursor.fetchone():
                return (False, "❌ You don't own this card!", {})
        
        # Check dust and spend
        if not self.spend_dust(user_id, cost, 'spent_reroll', card_id):
            current = self.get_dust_balance(user_id)
            return (False, f"❌ Insufficient dust! Need {cost}, you have {current}", {})
        
        # Generate new stats based on rarity
        stat_ranges = {
            'common': (40, 60),
            'rare': (50, 70),
            'epic': (60, 80),
            'legendary': (70, 90),
            'mythic': (80, 95)
        }
        
        min_stat, max_stat = stat_ranges.get(card_rarity.lower(), (50, 70))
        
        new_stats = {
            'impact': random.randint(min_stat, max_stat),
            'skill': random.randint(min_stat, max_stat),
            'longevity': random.randint(min_stat, max_stat),
            'culture': random.randint(min_stat, max_stat),
            'hype': random.randint(min_stat, max_stat)
        }
        
        # Update card stats
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cards
                SET impact = ?, skill = ?, longevity = ?, culture = ?, hype = ?
                WHERE card_id = ?
            """, (
                new_stats['impact'],
                new_stats['skill'],
                new_stats['longevity'],
                new_stats['culture'],
                new_stats['hype'],
                card_id
            ))
            conn.commit()
        
        avg = sum(new_stats.values()) // 5
        return (True, f"✅ Rerolled stats for {cost} dust! New average: {avg}", new_stats)
    
    def add_cosmetic(
        self,
        user_id: int,
        card_id: str,
        cosmetic_type: str
    ) -> Tuple[bool, str]:
        """
        Add cosmetic upgrade to a card
        """
        cost = self.COSMETIC_COSTS.get(cosmetic_type, 200)
        
        # Check ownership
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT uc.id FROM user_cards uc
                WHERE uc.user_id = ? AND uc.card_id = ?
            """, (user_id, card_id))
            
            if not cursor.fetchone():
                return (False, "❌ You don't own this card!")
        
        # Check dust and spend
        if not self.spend_dust(user_id, cost, 'spent_cosmetic', card_id):
            current = self.get_dust_balance(user_id)
            return (False, f"❌ Insufficient dust! Need {cost}, you have {current}")
        
        # Add cosmetic (would need cosmetics table in real implementation)
        # For now, just track the purchase
        
        cosmetic_names = {
            'animated_border': 'Animated Border',
            'holographic': 'Holographic Effect',
            'custom_frame': 'Custom Frame',
            'signature': 'Signature Edition',
            'foil': 'Foil Finish'
        }
        
        name = cosmetic_names.get(cosmetic_type, cosmetic_type)
        return (True, f"✅ Added {name} to your card for {cost} dust!")
    
    def get_dust_stats(self, user_id: int) -> Dict:
        """Get comprehensive dust statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get dust balance
            cursor.execute("""
                SELECT dust_amount, total_dust_earned, total_dust_spent
                FROM user_dust WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return {
                    'current': 0,
                    'total_earned': 0,
                    'total_spent': 0,
                    'net_earned': 0
                }
            
            current, earned, spent = result
            
            return {
                'current': current,
                'total_earned': earned,
                'total_spent': spent,
                'net_earned': earned - spent
            }


# Global instance
dust_economy = DustEconomy()
