"""
discord_cards.py - Card display classes for Music Legends
Handles card creation, formatting, and display
"""

import discord
from typing import Dict, Optional, List
from datetime import datetime
from services.image_cache import safe_image

class ArtistCard:
    """
    Represents a music artist card
    """
    
    def __init__(
        self,
        card_id: str,
        artist: str,
        song: str,
        youtube_url: str,
        youtube_id: str,
        view_count: int,
        thumbnail: str,
        rarity: str = "common",
        is_hero: bool = False,
        pack_id: Optional[str] = None
    ):
        self.card_id = card_id
        self.artist = artist
        self.song = song
        self.youtube_url = youtube_url
        self.youtube_id = youtube_id
        self.view_count = view_count
        self.thumbnail = thumbnail
        self.rarity = rarity.lower()
        self.is_hero = is_hero
        self.pack_id = pack_id
        
        # Calculate stats
        self.power = self._calculate_power()
        self.tier = self._calculate_tier()
    
    def _calculate_power(self) -> int:
        """
        Calculate card power from view count and rarity
        
        Base power from views (0-70):
        - 1B+ views = 70
        - 500M+ = 60
        - 100M+ = 50
        - 50M+ = 40
        - 10M+ = 30
        - <10M = 20
        
        Rarity bonus:
        - Common: +0
        - Rare: +10
        - Epic: +20
        - Legendary: +30
        - Mythic: +40
        """
        # Base power from views
        if self.view_count >= 1_000_000_000:  # 1B+
            base = 70
        elif self.view_count >= 500_000_000:  # 500M+
            base = 60
        elif self.view_count >= 100_000_000:  # 100M+
            base = 50
        elif self.view_count >= 50_000_000:   # 50M+
            base = 40
        elif self.view_count >= 10_000_000:   # 10M+
            base = 30
        else:
            base = 20
        
        # Rarity bonus
        rarity_bonuses = {
            "common": 0,
            "rare": 10,
            "epic": 20,
            "legendary": 30,
            "mythic": 40,
            "ultra_mythic": 50,
        }
        
        bonus = rarity_bonuses.get(self.rarity, 0)
        
        return base + bonus
    
    def _calculate_tier(self) -> str:
        """Calculate tier letter (S, A, B, C, D)"""
        if self.power >= 90:
            return "S"
        elif self.power >= 75:
            return "A"
        elif self.power >= 60:
            return "B"
        elif self.power >= 45:
            return "C"
        else:
            return "D"
    
    def get_rarity_color(self) -> int:
        """Get Discord embed color for rarity"""
        colors = {
            "common": 0x95a5a6,      # Gray
            "rare": 0x3498db,        # Blue
            "epic": 0x9b59b6,        # Purple
            "legendary": 0xf39c12,   # Gold
            "mythic": 0xe74c3c,      # Red
            "ultra_mythic": 0xff1493, # Deep Pink
        }
        return colors.get(self.rarity, 0x95a5a6)
    
    def get_rarity_emoji(self) -> str:
        """Get emoji for rarity"""
        emojis = {
            "common": "⚪",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡",
            "mythic": "🔴",
            "ultra_mythic": "💎",
        }
        return emojis.get(self.rarity, "⚪")
    
    def to_embed(self, show_stats: bool = True, show_variants: bool = True) -> discord.Embed:
        """
        Create Discord embed for this card
        
        Args:
            show_stats: Whether to show power/tier stats
            show_variants: Whether to show variant information
        
        Returns:
            discord.Embed ready to send
        """
        # Add visual indicators for special variants
        title_prefix = ""
        if hasattr(self, 'foil') and self.foil:
            title_prefix = "✨ "
        if hasattr(self, 'frame_style'):
            if self.frame_style == "holographic":
                title_prefix = "🌈 "
            elif self.frame_style == "crystal":
                title_prefix = "💎 "
            elif self.frame_style == "neon":
                title_prefix = "⚡ "
            elif self.frame_style == "vintage":
                title_prefix = "📜 "
        
        embed = discord.Embed(
            title=f"{title_prefix}{self.get_rarity_emoji()} {self.artist} - {self.song}",
            description=f"**Rarity:** {self.rarity.title()}",
            color=self.get_rarity_color(),
            url=self.youtube_url
        )
        
        # Add stats if requested
        if show_stats:
            embed.add_field(
                name="⚡ Power",
                value=f"**{self.power}** (Tier {self.tier})",
                inline=True
            )
        
        # Add view count
        embed.add_field(
            name="👁️ Views",
            value=f"{self.view_count:,}",
            inline=True
        )
        
        # Hero badge
        if self.is_hero:
            embed.add_field(
                name="🌟 Status",
                value="**HERO CARD**",
                inline=True
            )
        
        # Show variant info
        if show_variants and hasattr(self, 'frame_style') and self.frame_style and self.frame_style != "lux_black":
            embed.add_field(
                name="🎨 Variant",
                value=f"**{self.frame_style.replace('_', ' ').title()}** Frame",
                inline=True
            )
        
        if show_variants and hasattr(self, 'foil_effect') and self.foil_effect and self.foil_effect not in ['none', 'standard']:
            embed.add_field(
                name="✨ Effect",
                value=f"**{self.foil_effect.title()}** Foil",
                inline=True
            )
        
        # Thumbnail
        if self.thumbnail:
            safe_thumbnail = safe_image(self.thumbnail)
            if safe_thumbnail != self.thumbnail:
                print(f"🖼️ Using fallback image for card {self.card_id}: {self.thumbnail[:50]}...")
            embed.set_thumbnail(url=safe_thumbnail)
        
        # Footer with logo
        # Note: Logo URL would need to be hosted online for Discord to display
        # For now, we add a text footer with logo reference
        embed.set_footer(text=f"🎵 Music Legends • Card ID: {self.card_id}")
        
        return embed
    
    def to_dict(self) -> Dict:
        """Convert card to dictionary for database storage"""
        return {
            "card_id": self.card_id,
            "artist": self.artist,
            "song": self.song,
            "youtube_url": self.youtube_url,
            "youtube_id": self.youtube_id,
            "view_count": self.view_count,
            "thumbnail": self.thumbnail,
            "rarity": self.rarity,
            "power": self.power,
            "tier": self.tier,
            "is_hero": self.is_hero,
            "pack_id": self.pack_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ArtistCard':
        """Create card from dictionary"""
        return cls(
            card_id=data["card_id"],
            artist=data["artist"],
            song=data["song"],
            youtube_url=data["youtube_url"],
            youtube_id=data["youtube_id"],
            view_count=data["view_count"],
            thumbnail=data["thumbnail"],
            rarity=data.get("rarity", "common"),
            is_hero=data.get("is_hero", False),
            pack_id=data.get("pack_id"),
        )
    
    def __repr__(self):
        return f"<ArtistCard: {self.artist} - {self.song} ({self.rarity}, {self.power} PWR)>"


class Pack:
    """
    Represents a pack of cards
    """
    
    def __init__(
        self,
        pack_id: str,
        pack_type: str,  # "community" or "gold"
        creator_id: str,
        cards: List[ArtistCard],
        buy_price: float,
        created_at: Optional[datetime] = None
    ):
        self.pack_id = pack_id
        self.pack_type = pack_type
        self.creator_id = creator_id
        self.cards = cards
        self.buy_price = buy_price
        self.created_at = created_at or datetime.now()
        
        # Get hero card
        self.hero_card = next((c for c in cards if c.is_hero), cards[0] if cards else None)
    
    def to_embed(self) -> discord.Embed:
        """Create Discord embed for pack preview"""
        
        color = 0x3498db if self.pack_type == "community" else 0xFFD700
        
        embed = discord.Embed(
            title=f"{'📦' if self.pack_type == 'community' else '💎'} {self.pack_type.title()} Pack",
            description=f"**Hero:** {self.hero_card.artist} - {self.hero_card.song}" if self.hero_card else "5 Random Cards",
            color=color
        )
        
        # Show all cards
        for i, card in enumerate(self.cards, 1):
            hero_tag = " 🌟" if card.is_hero else ""
            embed.add_field(
                name=f"Card {i}{hero_tag}",
                value=f"{card.get_rarity_emoji()} {card.artist} - {card.song}\n"
                      f"**{card.rarity.title()}** • {card.power} PWR",
                inline=True
            )
        
        # Pack info
        embed.add_field(
            name="💰 Price",
            value=f"${self.buy_price:.2f}",
            inline=False
        )
        
        # Thumbnail from hero card
        if self.hero_card and self.hero_card.thumbnail:
            embed.set_thumbnail(url=self.hero_card.thumbnail)
        
        embed.set_footer(text=f"Pack ID: {self.pack_id} | Created: {self.created_at.strftime('%Y-%m-%d')}")
        
        return embed
    
    def to_dict(self) -> Dict:
        """Convert pack to dictionary"""
        return {
            "pack_id": self.pack_id,
            "pack_type": self.pack_type,
            "creator_id": self.creator_id,
            "cards": [card.to_dict() for card in self.cards],
            "buy_price": self.buy_price,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Pack':
        """Create pack from dictionary"""
        cards = [ArtistCard.from_dict(c) for c in data["cards"]]
        return cls(
            pack_id=data["pack_id"],
            pack_type=data["pack_type"],
            creator_id=data["creator_id"],
            cards=cards,
            buy_price=data["buy_price"],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
        )
    
    def __repr__(self):
        return f"<Pack: {self.pack_type} ({len(self.cards)} cards, ${self.buy_price})>"


class CardCollection:
    """
    Represents a user's card collection
    """
    
    def __init__(self, user_id: str, cards: Optional[List[ArtistCard]] = None):
        self.user_id = user_id
        self.cards = cards or []
    
    def add_card(self, card: ArtistCard):
        """Add card to collection"""
        self.cards.append(card)
    
    def remove_card(self, card_id: str) -> Optional[ArtistCard]:
        """Remove card from collection"""
        for i, card in enumerate(self.cards):
            if card.card_id == card_id:
                return self.cards.pop(i)
        return None
    
    def get_card(self, card_id: str) -> Optional[ArtistCard]:
        """Get card by ID"""
        return next((c for c in self.cards if c.card_id == card_id), None)
    
    def get_best_card(self) -> Optional[ArtistCard]:
        """Get highest power card"""
        if not self.cards:
            return None
        return max(self.cards, key=lambda c: c.power)
    
    def get_cards_by_rarity(self, rarity: str) -> List[ArtistCard]:
        """Get all cards of specific rarity"""
        return [c for c in self.cards if c.rarity == rarity.lower()]
    
    def get_cards_by_artist(self, artist: str) -> List[ArtistCard]:
        """Get all cards by specific artist"""
        return [c for c in self.cards if c.artist.lower() == artist.lower()]
    
    def total_cards(self) -> int:
        """Get total card count"""
        return len(self.cards)
    
    def rarity_breakdown(self) -> Dict[str, int]:
        """Get count of each rarity"""
        breakdown = {}
        for card in self.cards:
            breakdown[card.rarity] = breakdown.get(card.rarity, 0) + 1
        return breakdown
    
    def to_embed(self, page: int = 1, per_page: int = 10) -> discord.Embed:
        """Create Discord embed showing collection"""
        
        total_pages = (len(self.cards) - 1) // per_page + 1 if self.cards else 1
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        page_cards = self.cards[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🎴 Card Collection",
            description=f"**Total Cards:** {len(self.cards)}\n**Page:** {page}/{total_pages}",
            color=0x9b59b6
        )
        
        # Show rarity breakdown
        breakdown = self.rarity_breakdown()
        breakdown_text = "\n".join([
            f"{ArtistCard(None, None, None, None, None, 0, None, rarity=r).get_rarity_emoji()} {r.title()}: {count}"
            for r, count in breakdown.items()
        ])
        
        if breakdown_text:
            embed.add_field(
                name="📊 Rarity Breakdown",
                value=breakdown_text,
                inline=False
            )
        
        # Show cards on this page
        if page_cards:
            for i, card in enumerate(page_cards, start=start_idx + 1):
                embed.add_field(
                    name=f"{i}. {card.get_rarity_emoji()} {card.artist}",
                    value=f"{card.song}\n{card.power} PWR",
                    inline=True
                )
        else:
            embed.add_field(
                name="No Cards",
                value="Buy packs from the shop to start your collection!",
                inline=False
            )
        
        return embed
    
    def __repr__(self):
        return f"<CardCollection: {self.user_id} ({len(self.cards)} cards)>"
