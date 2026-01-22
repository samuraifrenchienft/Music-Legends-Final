"""
Pack Definition Schema

No code is allowed to invent pack behavior outside this file.
All pack logic must read from these definitions.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import json
import os

class PackTier(str, Enum):
    STARTER = "starter"
    STANDARD = "standard"
    PREMIUM = "premium"
    FOUNDER = "founder"

class PackStyle(str, Enum):
    BASIC = "basic"
    MODERN = "modern"
    LUXURY = "luxury"
    CREATOR = "creator"

class PackDefinition:
    """
    Formalized pack definition.
    All pack behavior comes from these definitions.
    """
    
    def __init__(
        self,
        key: str,
        display_name: str,
        tier: PackTier,
        cards_per_pack: int,
        guarantees: Dict[str, Any],
        odds: Dict[str, float],
        visuals: Dict[str, str],
        price_cents: int,
        description: Optional[str] = None
    ):
        self.key = key
        self.display_name = display_name
        self.tier = tier
        self.cards_per_pack = cards_per_pack
        self.guarantees = guarantees
        self.odds = odds
        self.visuals = visuals
        self.price_cents = price_cents
        self.description = description
    
    def has_hero_slot(self) -> bool:
        """Check if pack has hero slot guarantee"""
        return self.guarantees.get("hero_slot", False)
    
    def get_min_rarity(self) -> str:
        """Get minimum guaranteed rarity"""
        return self.guarantees.get("min_rarity", "community")
    
    def get_odds_list(self) -> List[tuple]:
        """Get (tier, probability) tuples for weighted selection"""
        return list(self.odds.items())
    
    def validate_odds(self) -> bool:
        """Validate that odds sum to 1.0"""
        total = sum(self.odds.values())
        return abs(total - 1.0) < 0.01
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "key": self.key,
            "display_name": self.display_name,
            "tier": self.tier.value,
            "cards_per_pack": self.cards_per_pack,
            "guarantees": self.guarantees,
            "odds": self.odds,
            "visuals": self.visuals,
            "price_cents": self.price_cents,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackDefinition':
        """Create pack from dictionary"""
        return cls(
            key=data["key"],
            display_name=data["display_name"],
            tier=PackTier(data["tier"]),
            cards_per_pack=data["cards_per_pack"],
            guarantees=data["guarantees"],
            odds=data["odds"],
            visuals=data["visuals"],
            price_cents=data["price_cents"],
            description=data.get("description")
        )

# Pack Definitions Registry
PACK_DEFINITIONS: Dict[str, PackDefinition] = {
    "starter": PackDefinition(
        key="starter",
        display_name="Starter Pack",
        tier=PackTier.STARTER,
        cards_per_pack=3,
        guarantees={
            "min_rarity": "community",
            "hero_slot": False
        },
        odds={
            "community": 0.80,
            "gold": 0.20
        },
        visuals={
            "pack_color": "#E8E8E8",
            "accent": "#C0C0C0",
            "style": "basic"
        },
        price_cents=299,
        description="Perfect starting point for new collectors"
    ),
    
    "silver": PackDefinition(
        key="silver",
        display_name="Silver Pack",
        tier=PackTier.STANDARD,
        cards_per_pack=4,
        guarantees={
            "min_rarity": "gold",
            "hero_slot": False
        },
        odds={
            "community": 0.60,
            "gold": 0.30,
            "rare": 0.10
        },
        visuals={
            "pack_color": "#C0C0C0",
            "accent": "#808080",
            "style": "modern"
        },
        price_cents=499,
        description="Solid value with guaranteed gold cards"
    ),
    
    "gold": PackDefinition(
        key="gold",
        display_name="Gold Pack",
        tier=PackTier.STANDARD,
        cards_per_pack=5,
        guarantees={
            "min_rarity": "gold",
            "hero_slot": False
        },
        odds={
            "community": 0.40,
            "gold": 0.30,
            "rare": 0.20,
            "epic": 0.10
        },
        visuals={
            "pack_color": "#FFD700",
            "accent": "#B8860B",
            "style": "modern"
        },
        price_cents=699,
        description="Premium experience with epic chances"
    ),
    
    "black": PackDefinition(
        key="black",
        display_name="Black Pack",
        tier=PackTier.PREMIUM,
        cards_per_pack=5,
        guarantees={
            "min_rarity": "gold",
            "hero_slot": True
        },
        odds={
            "community": 0.55,
            "gold": 0.30,
            "platinum": 0.12,
            "legendary": 0.03
        },
        visuals={
            "pack_color": "#0B0B0B",
            "accent": "#D4AF37",
            "style": "luxury"
        },
        price_cents=999,
        description="Ultimate premium pack with hero slot guarantee"
    ),
    
    "founder_gold": PackDefinition(
        key="founder_gold",
        display_name="Founder Gold Pack",
        tier=PackTier.FOUNDER,
        cards_per_pack=7,
        guarantees={
            "min_rarity": "epic",
            "hero_slot": True
        },
        odds={
            "community": 0.30,
            "gold": 0.20,
            "platinum": 0.25,
            "legendary": 0.20,
            "diamond": 0.05
        },
        visuals={
            "pack_color": "#FFD700",
            "accent": "#FFFFFF",
            "style": "luxury"
        },
        price_cents=1999,
        description="Exclusive founder pack with guaranteed epics"
    ),
    
    "founder_black": PackDefinition(
        key="founder_black",
        display_name="Founder Black Pack",
        tier=PackTier.FOUNDER,
        cards_per_pack=8,
        guarantees={
            "min_rarity": "platinum",
            "hero_slot": True
        },
        odds={
            "community": 0.20,
            "gold": 0.15,
            "platinum": 0.30,
            "legendary": 0.25,
            "diamond": 0.10
        },
        visuals={
            "pack_color": "#000000",
            "accent": "#FFD700",
            "style": "luxury"
        },
        price_cents=2999,
        description="Most prestigious pack with platinum guarantees"
    )
}

def get_pack_definition(pack_key: str) -> Optional[PackDefinition]:
    """Get pack definition by key"""
    return PACK_DEFINITIONS.get(pack_key)

def get_all_packs() -> Dict[str, PackDefinition]:
    """Get all pack definitions"""
    return PACK_DEFINITIONS.copy()

def get_packs_by_tier(tier: PackTier) -> List[PackDefinition]:
    """Get all packs of a specific tier"""
    return [pack for pack in PACK_DEFINITIONS.values() if pack.tier == tier]

def validate_all_packs() -> List[str]:
    """Validate all pack definitions and return errors"""
    errors = []
    
    for key, pack in PACK_DEFINITIONS.items():
        if not pack.validate_odds():
            errors.append(f"Pack {key}: Odds don't sum to 1.0")
        
        if pack.cards_per_pack <= 0:
            errors.append(f"Pack {key}: Invalid cards_per_pack")
        
        if pack.price_cents <= 0:
            errors.append(f"Pack {key}: Invalid price")
    
    return errors

# Load custom pack definitions from file if exists
def load_custom_packs():
    """Load additional pack definitions from JSON file"""
    custom_packs_file = "pack_definitions.json"
    if os.path.exists(custom_packs_file):
        try:
            with open(custom_packs_file, 'r') as f:
                custom_data = json.load(f)
                for pack_data in custom_data.get("packs", []):
                    pack = PackDefinition.from_dict(pack_data)
                    PACK_DEFINITIONS[pack.key] = pack
        except Exception as e:
            print(f"Error loading custom packs: {e}")

# Initialize custom packs
load_custom_packs()
