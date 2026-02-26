# services/cosmetic_manager.py
"""
Cosmetic Manager Service
Handles cosmetic unlocks, purchases, and application to cards
"""

import sqlite3
from typing import List, Dict, Optional
from database import DatabaseManager


class CosmeticManager:
    """Manages card cosmetics and user unlocks"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._initialize_default_cosmetics()
    
    def _initialize_default_cosmetics(self):
        """Initialize default cosmetics in the catalog"""
        default_cosmetics = [
            # Frames
            {'cosmetic_id': 'frame_holographic', 'cosmetic_type': 'frame', 'name': 'Holographic Frame', 
             'description': 'Rainbow holographic effect', 'rarity': 'epic', 'unlock_method': 'gold', 
             'price_gold': 1000, 'price_tickets': None, 'image_url': None},
            {'cosmetic_id': 'frame_vintage', 'cosmetic_type': 'frame', 'name': 'Vintage Frame',
             'description': 'Classic brown sepia tones', 'rarity': 'rare', 'unlock_method': 'gold',
             'price_gold': 500, 'price_tickets': None, 'image_url': None},
            {'cosmetic_id': 'frame_neon', 'cosmetic_type': 'frame', 'name': 'Neon Frame',
             'description': 'Bright neon colors', 'rarity': 'epic', 'unlock_method': 'gold',
             'price_gold': 1000, 'price_tickets': None, 'image_url': None},
            {'cosmetic_id': 'frame_crystal', 'cosmetic_type': 'frame', 'name': 'Crystal Frame',
             'description': 'Crystal ice effect', 'rarity': 'legendary', 'unlock_method': 'tickets',
             'price_gold': None, 'price_tickets': 50, 'image_url': None},
            
            # Foil effects
            {'cosmetic_id': 'foil_rainbow', 'cosmetic_type': 'effect', 'name': 'Rainbow Foil',
             'description': 'Rainbow gradient overlay', 'rarity': 'epic', 'unlock_method': 'gold',
             'price_gold': 750, 'price_tickets': None, 'image_url': None},
            {'cosmetic_id': 'foil_prismatic', 'cosmetic_type': 'effect', 'name': 'Prismatic Foil',
             'description': 'Prismatic shine effect', 'rarity': 'epic', 'unlock_method': 'gold',
             'price_gold': 750, 'price_tickets': None, 'image_url': None},
            {'cosmetic_id': 'foil_galaxy', 'cosmetic_type': 'effect', 'name': 'Galaxy Foil',
             'description': 'Space and stars effect', 'rarity': 'legendary', 'unlock_method': 'vip_only',
             'price_gold': None, 'price_tickets': None, 'image_url': None},
        ]
        
        for cosmetic in default_cosmetics:
            self.db.add_cosmetic_to_catalog(cosmetic)
    
    def get_user_cosmetics(self, user_id: str, cosmetic_type: str = None) -> List[Dict]:
        """Get all cosmetics unlocked by user"""
        return self.db.get_user_cosmetics(user_id, cosmetic_type)
    
    def unlock_cosmetic(self, user_id: str, cosmetic_id: str, source: str = 'purchase') -> bool:
        """Unlock a cosmetic for a user"""
        return self.db.unlock_cosmetic_for_user(user_id, cosmetic_id, source)
    
    def apply_cosmetic_to_card(self, user_id: str, card_id: str, cosmetic: Dict) -> bool:
        """Apply cosmetic to specific card"""
        return self.db.apply_cosmetic_to_card(user_id, card_id, cosmetic)
    
    def check_unlock_requirements(self, user_id: str, cosmetic_id: str) -> tuple[bool, str]:
        """Check if user meets requirements to unlock cosmetic"""
        # Get cosmetic from catalog
        available = self.db.get_available_cosmetics()
        cosmetic = next((c for c in available if c['cosmetic_id'] == cosmetic_id), None)
        
        if not cosmetic:
            return False, "Cosmetic not found"
        
        # Check if already unlocked
        user_cosmetics = self.db.get_user_cosmetics(user_id)
        if any(c['cosmetic_id'] == cosmetic_id for c in user_cosmetics):
            return False, "Already unlocked"
        
        # Check unlock method
        unlock_method = cosmetic['unlock_method']
        
        if unlock_method == 'vip_only':
            # Check VIP status (would need VIP integration)
            return False, "VIP only cosmetic"
        
        if unlock_method == 'gold' and cosmetic['price_gold']:
            # Check user's gold balance
            economy = self.db.get_user_economy(user_id)
            if economy['gold'] < cosmetic['price_gold']:
                return False, f"Not enough gold (need {cosmetic['price_gold']}, have {economy['gold']})"
            return True, "Can purchase with gold"
        
        if unlock_method == 'tickets' and cosmetic['price_tickets']:
            # Check user's ticket balance
            economy = self.db.get_user_economy(user_id)
            if economy['tickets'] < cosmetic['price_tickets']:
                return False, f"Not enough tickets (need {cosmetic['price_tickets']}, have {economy['tickets']})"
            return True, "Can purchase with tickets"
        
        return False, "Unknown unlock method"
    
    def purchase_cosmetic(self, user_id: str, cosmetic_id: str) -> tuple[bool, str]:
        """Purchase a cosmetic"""
        # Check requirements
        can_unlock, message = self.check_unlock_requirements(user_id, cosmetic_id)
        
        if not can_unlock:
            return False, message
        
        # Get cosmetic details
        available = self.db.get_available_cosmetics()
        cosmetic = next((c for c in available if c['cosmetic_id'] == cosmetic_id), None)
        
        if not cosmetic:
            return False, "Cosmetic not found"
        
        # Deduct currency
        if cosmetic['price_gold']:
            success = self.db.modify_user_gold(user_id, -cosmetic['price_gold'])
            if not success:
                return False, "Failed to deduct gold"
        
        if cosmetic['price_tickets']:
            success = self.db.modify_user_tickets(user_id, -cosmetic['price_tickets'])
            if not success:
                return False, "Failed to deduct tickets"
        
        # Unlock cosmetic
        success = self.db.unlock_cosmetic_for_user(user_id, cosmetic_id, 'purchase')
        
        if success:
            return True, f"Successfully unlocked {cosmetic['name']}!"
        else:
            return False, "Failed to unlock cosmetic"
    
    def get_available_cosmetics(self, user_id: str = None, filter_unlocked: bool = False) -> List[Dict]:
        """Get available cosmetics, optionally filtered"""
        all_cosmetics = self.db.get_available_cosmetics()
        
        if not user_id or not filter_unlocked:
            return all_cosmetics
        
        # Filter out already unlocked
        user_cosmetics = self.db.get_user_cosmetics(user_id)
        unlocked_ids = {c['cosmetic_id'] for c in user_cosmetics}
        
        return [c for c in all_cosmetics if c['cosmetic_id'] not in unlocked_ids]
    
    def get_card_cosmetics(self, user_id: str, card_id: str) -> Optional[Dict]:
        """Get cosmetics applied to a card"""
        return self.db.get_card_cosmetics(user_id, card_id)
    
    def unlock_vip_cosmetics(self, user_id: str):
        """Unlock all VIP cosmetics for a user"""
        vip_cosmetics = [c for c in self.db.get_available_cosmetics() if c['unlock_method'] == 'vip_only']
        
        for cosmetic in vip_cosmetics:
            self.db.unlock_cosmetic_for_user(user_id, cosmetic['cosmetic_id'], 'vip')
        
        return len(vip_cosmetics)


# Global instance
cosmetic_manager = None

def get_cosmetic_manager(db: DatabaseManager = None) -> CosmeticManager:
    """Get or create global cosmetic manager instance"""
    global cosmetic_manager
    if cosmetic_manager is None:
        if db is None:
            from database import db as default_db
            db = default_db
        cosmetic_manager = CosmeticManager(db)
    return cosmetic_manager
