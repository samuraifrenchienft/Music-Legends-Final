"""
Canonical Card Schema

This is the authoritative definition of a card.
All rendering reads from this structure.
This structure never changes casually.
"""

from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime
from enum import Enum

class CardTier(str, Enum):
    COMMUNITY = "community"
    GOLD = "gold"
    PLATINUM = "platinum"
    LEGENDARY = "legendary"

class ArtistSource(str, Enum):
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"

class FrameStyle(str, Enum):
    LUX_BLACK = "lux_black"
    LUX_WHITE = "lux_white"
    CREATOR = "creator"
    SYSTEM = "system"

class CanonicalCard:
    """
    The authoritative card model.
    This structure never changes casually.
    """
    
    def __init__(
        self,
        artist_id: str,
        artist_name: str,
        primary_genre: str,
        artist_image_url: str,
        artist_source: ArtistSource,
        tier: CardTier,
        print_number: int,
        print_cap: int,
        season: int,
        pack_key: str,
        opened_by: str,
        frame_style: FrameStyle = FrameStyle.LUX_BLACK,
        foil: bool = True,
        badge_icons: Optional[List[str]] = None,
        accent_color: str = "#D4AF37"
    ):
        self.card_id = str(uuid4())
        self.mint_timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Artist Information
        self.artist = {
            "id": artist_id,
            "name": artist_name,
            "primary_genre": primary_genre,
            "image_url": artist_image_url,
            "source": artist_source.value
        }
        
        # Rarity Information
        self.rarity = {
            "tier": tier.value,
            "print_number": print_number,
            "print_cap": print_cap
        }
        
        # Identity Information
        self.identity = {
            "season": season,
            "serial": self._generate_serial(tier, season, print_number),
            "mint_timestamp": self.mint_timestamp
        }
        
        # Origin Information
        self.origin = {
            "pack_key": pack_key,
            "opened_by": opened_by,
            "opened_at": self.mint_timestamp
        }
        
        # Presentation Information
        self.presentation = {
            "frame_style": frame_style.value,
            "foil": foil,
            "badge_icons": badge_icons or self._default_badges(tier),
            "accent_color": accent_color
        }
    
    def _generate_serial(self, tier: CardTier, season: int, print_number: int) -> str:
        """Generate investor-grade serial number: ML-S{season}-{tier_letter}-{print_number}"""
        tier_letters = {
            CardTier.COMMUNITY: "C",
            CardTier.GOLD: "G", 
            CardTier.PLATINUM: "P",
            CardTier.LEGENDARY: "L"
        }
        
        tier_letter = tier_letters[tier]
        return f"ML-S{season}-{tier_letter}-{print_number:04d}"
    
    def _default_badges(self, tier: CardTier) -> List[str]:
        """Get default badge icons based on tier"""
        badges = [tier.value]
        
        # First print badge for low print numbers
        if self.rarity["print_number"] <= 10:
            badges.append("first_print")
        
        # Special badges for high tiers
        if tier == CardTier.LEGENDARY:
            badges.append("legendary")
        elif tier == CardTier.PLATINUM:
            badges.append("platinum")
            
        return badges
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to canonical dictionary representation"""
        return {
            "card_id": self.card_id,
            "artist": self.artist,
            "rarity": self.rarity,
            "identity": self.identity,
            "origin": self.origin,
            "presentation": self.presentation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanonicalCard':
        """Create card from dictionary (for loading from storage)"""
        card = cls.__new__(cls)
        card.card_id = data["card_id"]
        card.artist = data["artist"]
        card.rarity = data["rarity"]
        card.identity = data["identity"]
        card.origin = data["origin"]
        card.presentation = data["presentation"]
        card.mint_timestamp = data["identity"]["mint_timestamp"]
        return card
    
    def is_hero_card(self) -> bool:
        """Check if this is a hero slot card"""
        # Hero cards are high-tier with popular artists
        hero_tiers = {CardTier.PLATINUM, CardTier.LEGENDARY}
        return self.rarity["tier"] in hero_tiers
    
    def get_rarity_display(self) -> str:
        """Get display name for rarity tier"""
        tier_names = {
            CardTier.COMMUNITY: "Community",
            CardTier.GOLD: "Gold",
            CardTier.PLATINUM: "Platinum", 
            CardTier.LEGENDARY: "Legendary"
        }
        return tier_names.get(CardTier(self.rarity["tier"]), "Unknown")
    
    def get_print_display(self) -> str:
        """Get print number display for UI"""
        return f"{self.rarity['print_number']}/{self.rarity['print_cap']}"
