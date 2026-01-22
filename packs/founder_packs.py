# packs/founder_packs.py
from dataclasses import dataclass
from typing import Dict, List, Optional
import json

@dataclass
class PackConfig:
    name: str
    identifier: str
    price_cents: int
    card_count: int
    primary_label: str
    subtitle: str
    description: str
    odds: Dict[str, Dict[str, int]]
    guarantee: Optional[str] = None
    boost: Optional[str] = None

class FounderPacks:
    """Founder Packs Configuration"""
    
    PACK_BLACK = "founder_black"
    PACK_SILVER = "founder_silver"
    
    def __init__(self):
        self.packs = {
            self.PACK_BLACK: PackConfig(
                name="Black Pack",
                identifier=self.PACK_BLACK,
                price_cents=999,  # $9.99
                card_count=5,
                primary_label="Gold Guaranteed",
                subtitle="5 Cards • 1 Gold+ Minimum",
                description="Premium pack with a guaranteed Gold Tier card and boosted chances at Platinum and Legendary.",
                odds={
                    "guaranteed_slot": {
                        "community": 0,
                        "gold": 75,
                        "platinum": 22,
                        "legendary": 3
                    },
                    "regular_slots": {
                        "community": 65,
                        "gold": 25,
                        "platinum": 8,
                        "legendary": 2
                    }
                },
                guarantee="gold+",
                boost="platinum+"
            ),
            self.PACK_SILVER: PackConfig(
                name="Silver Pack",
                identifier=self.PACK_SILVER,
                price_cents=699,  # $6.99
                card_count=5,
                primary_label="Gold Possible",
                subtitle="5 Cards • Standard Odds",
                description="Standard pack with balanced odds and a chance at Gold or higher.",
                odds={
                    "all_slots": {
                        "community": 75,
                        "gold": 20,
                        "platinum": 4,
                        "legendary": 1
                    }
                }
            )
        }
    
    def get_pack_config(self, pack_id: str) -> Optional[PackConfig]:
        """Get pack configuration by ID"""
        return self.packs.get(pack_id)
    
    def get_all_packs(self) -> Dict[str, PackConfig]:
        """Get all pack configurations"""
        return self.packs
    
    def validate_pack_opening(self, pack_id: str, cards: List[Dict]) -> Dict:
        """Validate pack opening results"""
        pack_config = self.get_pack_config(pack_id)
        if not pack_config:
            return {"valid": False, "error": "Invalid pack ID"}
        
        # Check card count
        if len(cards) != pack_config.card_count:
            return {"valid": False, "error": f"Expected {pack_config.card_count} cards, got {len(cards)}"}
        
        # Check guarantee (Black Pack)
        if pack_id == self.PACK_BLACK and pack_config.guarantee == "gold+":
            gold_plus_count = sum(1 for card in cards if card.get('tier') in ['gold', 'platinum', 'legendary'])
            if gold_plus_count < 1:
                return {"valid": False, "error": "Black Pack must return at least 1 Gold+ card"}
        
        # Check tier caps (would need season system)
        # This would validate against current season caps
        
        return {"valid": True, "pack_id": pack_id, "card_count": len(cards)}
    
    def generate_pack_cards(self, pack_id: str) -> List[Dict]:
        """Generate cards for a pack"""
        pack_config = self.get_pack_config(pack_id)
        if not pack_config:
            raise ValueError(f"Invalid pack ID: {pack_id}")
        
        cards = []
        
        if pack_id == self.PACK_BLACK:
            # Black Pack: 1 guaranteed slot + 4 regular slots
            guaranteed_card = self._generate_card_from_odds(pack_config.odds["guaranteed_slot"])
            cards.append(guaranteed_card)
            
            # Generate 4 regular cards
            for _ in range(4):
                regular_card = self._generate_card_from_odds(pack_config.odds["regular_slots"])
                cards.append(regular_card)
                
        elif pack_id == self.PACK_SILVER:
            # Silver Pack: 5 regular slots
            for _ in range(5):
                regular_card = self._generate_card_from_odds(pack_config.odds["all_slots"])
                cards.append(regular_card)
        
        return cards
    
    def _generate_card_from_odds(self, odds: Dict[str, int]) -> Dict:
        """Generate a single card based on odds"""
        import random
        
        # Calculate total weight
        total_weight = sum(odds.values())
        
        # Generate random number
        roll = random.randint(1, total_weight)
        
        # Find tier based on roll
        current_weight = 0
        for tier, weight in odds.items():
            current_weight += weight
            if roll <= current_weight:
                return {
                    "tier": tier,
                    "generated_from_odds": odds[tier],
                    "roll": roll
                }
        
        # Fallback (shouldn't happen)
        return {
            "tier": "community",
            "generated_from_odds": odds.get("community", 0),
            "roll": roll
        }
    
    def get_pack_display_data(self, pack_id: str) -> Optional[Dict]:
        """Get pack data for display"""
        pack_config = self.get_pack_config(pack_id)
        if not pack_config:
            return None
        
        return {
            "name": pack_config.name,
            "identifier": pack_config.identifier,
            "price": f"${pack_config.price_cents / 100:.2f}",
            "primary_label": pack_config.primary_label,
            "subtitle": pack_config.subtitle,
            "description": pack_config.description,
            "card_count": pack_config.card_count,
            "guarantee": pack_config.guarantee,
            "boost": pack_config.boost,
            "odds": pack_config.odds
        }

# Global instance
founder_packs = FounderPacks()
