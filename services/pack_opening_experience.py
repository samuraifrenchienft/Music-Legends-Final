"""
Pack Opening Experience (UX Rules)

When a pack opens in Discord:
- Pack animation embed
- Cards revealed one by one
- Legendary pauses the reveal
- Summary embed at end

This is not optional for top-tier feel.
"""

import asyncio
import discord
from typing import List, Dict, Optional, Tuple
from discord import Embed, Color, User
from schemas.card_canonical import CanonicalCard, CardTier
from schemas.pack_definition import PackDefinition
from ui.receipts import delivery_embed
import logging

logger = logging.getLogger(__name__)

class PackOpeningExperience:
    """
    Manages the premium pack opening experience in Discord.
    Creates suspense and excitement through staged reveals.
    """
    
    def __init__(self):
        self.pack_colors = {
            "starter": Color.light_grey(),
            "silver": Color.from_rgb(192, 192, 192),
            "gold": Color.gold(),
            "black": Color.dark_grey(),
            "founder_gold": Color.gold(),
            "founder_black": Color.dark_grey()
        }
        
        self.tier_colors = {
            CardTier.COMMUNITY: Color.light_grey(),
            CardTier.GOLD: Color.gold(),
            CardTier.PLATINUM: Color.from_rgb(192, 192, 192),
            CardTier.LEGENDARY: Color.purple()
        }
    
    async def open_pack(self, user: User, pack_def: PackDefinition, cards: List[CanonicalCard]) -> bool:
        """
        Execute complete pack opening experience.
        Returns True if successful, False if interrupted.
        """
        try:
            # Step 1: Pack animation embed
            await self._show_pack_animation(user, pack_def)
            await asyncio.sleep(2)  # Animation pause
            
            # Step 2: Reveal cards one by one
            revealed_cards = await self._reveal_cards_sequentially(user, cards)
            
            # Step 3: Summary embed
            await self._show_summary_embed(user, pack_def, revealed_cards)
            
            return True
            
        except Exception as e:
            logger.error(f"Pack opening experience failed: {e}")
            return False
    
    async def _show_pack_animation(self, user: User, pack_def: PackDefinition):
        """Show pack opening animation embed"""
        embed = Embed(
            title=f"🎁 Opening {pack_def.display_name}!",
            description=f"Get ready for {pack_def.cards_per_pack} amazing cards...",
            color=self.pack_colors.get(pack_def.key, Color.blue())
        )
        
        # Add pack visual information
        embed.add_field(
            name="Pack Details",
            value=f"**Type:** {pack_def.display_name}\n"
                  f"**Cards:** {pack_def.cards_per_pack}\n"
                  f"**Hero Slot:** {'✅' if pack_def.has_hero_slot() else '❌'}",
            inline=False
        )
        
        # Add odds information
        odds_text = []
        for tier, probability in pack_def.odds.items():
            emoji = self._get_tier_emoji(CardTier(tier))
            odds_text.append(f"{emoji} {tier.title()}: {probability*100:.1f}%")
        
        embed.add_field(
            name="Drop Rates",
            value="\n".join(odds_text),
            inline=False
        )
        
        embed.set_thumbnail(url="https://example.com/pack_animation.gif")
        embed.set_footer(text=f"Pack opened by {user.display_name}")
        
        await user.send(embed=embed)
    
    async def _reveal_cards_sequentially(self, user: User, cards: List[CanonicalCard]) -> List[CanonicalCard]:
        """Reveal cards one by one with dramatic pauses"""
        revealed_cards = []
        
        for i, card in enumerate(cards):
            # Check if this is a legendary card (special pause)
            is_legendary = card.rarity["tier"] == CardTier.LEGENDARY.value
            
            # Reveal the card
            await self._reveal_single_card(user, card, i + 1, len(cards))
            revealed_cards.append(card)
            
            # Pause timing based on rarity
            if is_legendary:
                await asyncio.sleep(3)  # Longer pause for legendary
            elif card.rarity["tier"] in [CardTier.PLATINUM.value, CardTier.LEGENDARY.value]:
                await asyncio.sleep(2)  # Medium pause for high tiers
            else:
                await asyncio.sleep(1.5)  # Standard pause
        
        return revealed_cards
    
    async def _reveal_single_card(self, user: User, card: CanonicalCard, card_number: int, total_cards: int):
        """Reveal a single card with dramatic effect"""
        tier = CardTier(card.rarity["tier"])
        color = self.tier_colors.get(tier, Color.blue())
        
        # Create card reveal embed
        embed = Embed(
            title=f"🎴 Card #{card_number}/{total_cards} Revealed!",
            description=f"**{card.artist['name']}** - {card.get_rarity_display()}",
            color=color
        )
        
        # Card details
        embed.add_field(
            name="🎨 Artist",
            value=f"**Name:** {card.artist['name']}\n"
                  f"**Genre:** {card.artist['primary_genre']}\n"
                  f"**Source:** {card.artist['source'].title()}",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Rarity",
            value=f"**Tier:** {card.get_rarity_display()}\n"
                  f"**Serial:** {card.identity['serial']}\n"
                  f"**Print:** {card.get_print_display()}",
            inline=True
        )
        
        # Special badges
        if card.presentation["badge_icons"]:
            badges = " ".join([self._get_badge_emoji(badge) for badge in card.presentation["badge_icons"]])
            embed.add_field(name="🏆 Badges", value=badges, inline=False)
        
        # Hero card special treatment
        if card.is_hero_card():
            embed.add_field(
                name="⭐ HERO CARD ⭐",
                value="This card was selected for the hero slot with boosted artist selection!",
                inline=False
            )
        
        # Visual elements
        embed.set_thumbnail(url=card.artist["image_url"])
        embed.set_image(url="https://example.com/card_frame.png")
        
        # Footer with card serial
        embed.set_footer(text=f"Serial: {card.identity['serial']} | Card ID: {card.card_id[:8]}...")
        
        await user.send(embed=embed)
    
    async def _show_summary_embed(self, user: User, pack_def: PackDefinition, cards: List[CanonicalCard]):
        """Show final summary of all cards"""
        embed = Embed(
            title=f"🎉 Pack Opening Complete!",
            description=f"Your {pack_def.display_name} revealed {len(cards)} amazing cards!",
            color=self.pack_colors.get(pack_def.key, Color.blue())
        )
        
        # Card summary by tier
        tier_counts = {}
        for card in cards:
            tier = card.rarity["tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        summary_lines = []
        for tier in ["community", "gold", "platinum", "legendary"]:
            count = tier_counts.get(tier, 0)
            if count > 0:
                emoji = self._get_tier_emoji(CardTier(tier))
                summary_lines.append(f"{emoji} {tier.title()}: {count}")
        
        embed.add_field(
            name="📊 Pack Summary",
            value="\n".join(summary_lines),
            inline=False
        )
        
        # Highlight best cards
        legendary_cards = [c for c in cards if c.rarity["tier"] == CardTier.LEGENDARY.value]
        platinum_cards = [c for c in cards if c.rarity["tier"] == CardTier.PLATINUM.value]
        
        if legendary_cards:
            best_card = legendary_cards[0]
            embed.add_field(
                name="👑 Legendary Pull!",
                value=f"**{best_card.artist['name']}**\n"
                      f"Serial: {best_card.identity['serial']}\n"
                      f"Print: {best_card.get_print_display()}",
                inline=False
            )
        elif platinum_cards:
            best_card = platinum_cards[0]
            embed.add_field(
                name="💎 Best Pull",
                value=f"**{best_card.artist['name']}** - Platinum\n"
                      f"Serial: {best_card.identity['serial']}",
                inline=False
            )
        
        # Hero card highlight
        hero_cards = [c for c in cards if c.is_hero_card()]
        if hero_cards:
            hero_card = hero_cards[0]
            embed.add_field(
                name="⭐ Hero Card",
                value=f"**{hero_card.artist['name']}**\n"
                      f"Selected for premium hero slot!",
                inline=False
            )
        
        embed.set_thumbnail(url="https://example.com/pack_complete.png")
        embed.set_footer(text=f"Pack opened by {user.display_name} | Total cards: {len(cards)}")
        
        await user.send(embed=embed)
    
    def _get_tier_emoji(self, tier: CardTier) -> str:
        """Get emoji for card tier"""
        tier_emojis = {
            CardTier.COMMUNITY: "⚪",
            CardTier.GOLD: "🟡",
            CardTier.PLATINUM: "⚪",
            CardTier.LEGENDARY: "🟣"
        }
        return tier_emojis.get(tier, "⚪")
    
    def _get_badge_emoji(self, badge: str) -> str:
        """Get emoji for badge"""
        badge_emojis = {
            "community": "⚪",
            "gold": "🟡",
            "platinum": "💎",
            "legendary": "👑",
            "first_print": "🆕",
            "hero": "⭐"
        }
        return badge_emojis.get(badge, "🏷️")
    
    async def create_quick_summary(self, user: User, pack_def: PackDefinition, cards: List[CanonicalCard]) -> Embed:
        """Create quick summary for delivery receipt"""
        embed = Embed(
            title=f"🎁 {pack_def.display_name} Delivered!",
            description=f"Your pack contains {len(cards)} cards",
            color=self.pack_colors.get(pack_def.key, Color.blue())
        )
        
        # Quick card list
        card_lines = []
        for i, card in enumerate(cards[:5], 1):  # Show max 5 cards
            tier_emoji = self._get_tier_emoji(CardTier(card.rarity["tier"]))
            hero_star = "⭐" if card.is_hero_card() else ""
            card_lines.append(f"{i}. {tier_emoji} {card.artist['name']} {hero_star}")
        
        if len(cards) > 5:
            card_lines.append(f"... and {len(cards) - 5} more cards")
        
        embed.add_field(
            name="📋 Cards Received",
            value="\n".join(card_lines),
            inline=False
        )
        
        return embed

# Global pack opening experience instance
pack_experience = PackOpeningExperience()

async def open_pack_experience(user: User, pack_def: PackDefinition, cards: List[CanonicalCard]) -> bool:
    """Execute pack opening experience"""
    return await pack_experience.open_pack(user, pack_def, cards)

async def create_pack_summary(user: User, pack_def: PackDefinition, cards: List[CanonicalCard]) -> Embed:
    """Create pack summary embed"""
    return await pack_experience.create_quick_summary(user, pack_def, cards)
