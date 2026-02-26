"""
Pack Opening Finite State Machine (Canonical)

This is game design + UX law. Code must obey this flow.

States: INIT → SEALED → REVEAL_QUEUE → CARD_REVEAL[n] → LEGENDARY_PAUSE? → SUMMARY → COMPLETE
No skipping. No shortcuts.
"""

import asyncio
import discord
from typing import Dict, Any, Optional, List
from discord import Embed, Color, Button, View, Interaction, User
from enum import Enum
from schemas.card_canonical import CanonicalCard, CardTier
from schemas.pack_definition import PackDefinition
from services.card_rendering_system import create_card_embed
import logging
import time

logger = logging.getLogger(__name__)

class PackOpeningState(Enum):
    """Finite state machine states for pack opening"""
    INIT = "init"
    SEALED = "sealed"
    REVEAL_QUEUE = "reveal_queue"
    CARD_REVEAL = "card_reveal"
    LEGENDARY_PAUSE = "legendary_pause"
    SUMMARY = "summary"
    COMPLETE = "complete"

class PackOpeningFSM:
    """
    Canonical pack opening finite state machine.
    Enforces exact flow with no shortcuts.
    """
    
    def __init__(self, user: User, pack_def: PackDefinition, cards: List[CanonicalCard]):
        self.user = user
        self.pack_def = pack_def
        self.cards = cards
        self.current_state = PackOpeningState.INIT
        self.current_card_index = 0
        self.message = None
        self.view = None
        self.start_time = time.time()
        
        # Track legendary cards for special handling
        self.legendary_cards = [card for card in cards if card.rarity["tier"] == CardTier.LEGENDARY.value]
        self.legendary_triggered = False
        
        logger.info(f"Pack opening FSM initialized for {user.id} with {len(cards)} cards")
    
    async def start_opening(self, channel) -> bool:
        """Start the pack opening process"""
        try:
            # STATE 1: INIT (Command Acknowledgement)
            await self._handle_init(channel)
            return True
        except Exception as e:
            logger.error(f"Failed to start pack opening: {e}")
            return False
    
    async def _handle_init(self, channel):
        """STATE 1: INIT (Command Acknowledgement)"""
        logger.info(f"STATE 1: INIT - User {self.user.id}")
        
        # Ephemeral response
        embed = Embed(
            title="🎁 Pack Opening Initiated",
            description=f"Opening {self.pack_def.display_name}…",
            color=Color.blue()
        )
        
        embed.add_field(
            name="🔒 Queue Status",
            value="Your position in queue: 1\nEstimated wait: 0 seconds",
            inline=False
        )
        
        embed.set_footer(text=f"Pack owned by {self.user.display_name}")
        
        self.message = await channel.send(embed=embed)
        
        # Auto-transition to SEALED after pack open delay (1.5s)
        await asyncio.sleep(1.5)  # Pack open delay
        await self._transition_to_sealed()
    
    async def _transition_to_sealed(self):
        """Transition to SEALED state"""
        self.current_state = PackOpeningState.SEALED
        await self._handle_sealed()
    
    async def _handle_sealed(self):
        """STATE 2: SEALED PACK (HYPE MOMENT)"""
        logger.info(f"STATE 2: SEALED - User {self.user.id}")
        
        # Create sealed pack embed
        embed = Embed(
            title=f"🎴 {self.pack_def.display_name}",
            description="You open a Black Pack…",
            color=self._get_pack_color()
        )
        
        # Large pack image placeholder
        embed.set_image(url="https://example.com/sealed_black_pack.png")
        
        # Pack details
        embed.add_field(
            name="📦 Pack Details",
            value=f"**Type:** {self.pack_def.display_name}\n"
                  f"**Cards:** {self.pack_def.cards_per_pack}\n"
                  f"**Hero Slot:** {'✅' if self.pack_def.has_hero_slot() else '❌'}",
            inline=False
        )
        
        # Odds information
        odds_text = []
        for tier, probability in self.pack_def.odds.items():
            emoji = self._get_tier_emoji(CardTier(tier))
            odds_text.append(f"{emoji} {tier.title()}: {probability*100:.1f}%")
        
        embed.add_field(
            name="🎯 Drop Rates",
            value="\n".join(odds_text),
            inline=False
        )
        
        # Create view with Open Pack button
        self.view = SealedPackView(self)
        
        await self.message.edit(embed=embed, view=self.view)
    
    async def handle_sealed_button_click(self, interaction: Interaction):
        """Handle Open Pack button click"""
        await interaction.response.defer()
        
        # Transition to REVEAL_QUEUE
        self.current_state = PackOpeningState.REVEAL_QUEUE
        await self._handle_reveal_queue(interaction)
    
    async def _handle_reveal_queue(self, interaction: Interaction):
        """STATE 3: REVEAL_QUEUE (SERVER DRAMA)"""
        logger.info(f"STATE 3: REVEAL_QUEUE - User {self.user.id}")
        
        # Update embed to show shuffling
        embed = self.message.embeds[0]
        embed.title = "🔀 Shuffling Cards…"
        embed.description = "The universe is deciding your fate…"
        embed.color = Color.orange()
        
        # Remove image and add shuffling animation
        embed.set_image(url="https://example.com/shuffling_cards.gif")
        
        # Clear previous fields
        embed.clear_fields()
        
        embed.add_field(
            name="⏳ Processing",
            value="Locking in your results…\nThis cannot be changed.",
            inline=False
        )
        
        await self.message.edit(embed=embed, view=None)
        
        # Card reveal timing (0.8s)
        await asyncio.sleep(0.8)  # Card reveal delay
        
        # Transition to first card reveal
        self.current_card_index = 0
        await self._transition_to_card_reveal()
    
    async def _transition_to_card_reveal(self):
        """Transition to CARD_REVEAL state"""
        self.current_state = PackOpeningState.CARD_REVEAL
        await self._handle_card_reveal()
    
    async def _handle_card_reveal(self):
        """STATE 4: CARD_REVEAL (ONE AT A TIME)"""
        logger.info(f"STATE 4: CARD_REVEAL - User {self.user.id}, Card {self.current_card_index + 1}")
        
        if self.current_card_index >= len(self.cards):
            # All cards revealed, move to summary
            await self._transition_to_summary()
            return
        
        # Get current card
        card = self.cards[self.current_card_index]
        card_number = self.current_card_index + 1
        total_cards = len(self.cards)
        
        # Check for legendary interruption
        if card.rarity["tier"] == CardTier.LEGENDARY.value and not self.legendary_triggered:
            self.legendary_triggered = True
            await self._handle_legendary_interruption(card)
            return
        
        # Create card reveal embed
        embed = self._create_card_reveal_embed(card, card_number, total_cards)
        
        # Create view with Next Card button
        self.view = CardRevealView(self)
        
        await self.message.edit(embed=embed, view=self.view)
    
    async def _handle_legendary_interruption(self, card: CanonicalCard):
        """STATE 5: LEGENDARY_PAUSE (MANDATORY)"""
        logger.info(f"STATE 5: LEGENDARY_PAUSE - User {self.user.id}")
        
        # Create legendary interruption embed
        embed = Embed(
            title="⚠️ LEGENDARY PULLED ⚠️",
            description=f"**{card.artist['name']}** has been chosen by the universe!",
            color=Color.dark_gold()
        )
        
        # Large card image with glow effect
        embed.set_image(url="https://example.com/legendary_card_glow.gif")
        
        # Emphasized card details
        embed.add_field(
            name="👑 LEGENDARY CARD",
            value=f"**Artist:** {card.artist['name']}\n"
                  f"**Genre:** {card.artist['primary_genre']}\n"
                  f"**Source:** {card.artist['source'].title()}",
            inline=False
        )
        
        embed.add_field(
            name="🔢 SERIAL INFORMATION",
            value=f"**Serial:** {card.identity['serial']}\n"
                  f"**Print:** {card.get_print_display()}\n"
                  f"**Scarcity:** One of only {card.rarity['print_cap']} ever!",
            inline=False
        )
        
        # Special footer
        embed.set_footer(text=f"Legendary cards are extremely rare! • Card {self.current_card_index + 1} of {len(self.cards)}")
        
        # No buttons - mandatory pause
        await self.message.edit(embed=embed, view=None)
        
        # Mandatory legendary pause (3.0s) with no skip
        await asyncio.sleep(3.0)  # Legendary pause
        
        # Continue with next card after pause
        self.current_card_index += 1
        await self._transition_to_card_reveal()
    
    async def handle_card_reveal_button_click(self, interaction: Interaction):
        """Handle Next Card button click"""
        await interaction.response.defer()
        
        # Move to next card
        self.current_card_index += 1
        
        if self.current_card_index >= len(self.cards):
            # All cards revealed, move to summary
            await self._transition_to_summary()
        else:
            # Reveal next card
            await self._handle_card_reveal()
    
    async def _transition_to_summary(self):
        """Transition to SUMMARY state"""
        self.current_state = PackOpeningState.SUMMARY
        await self._handle_summary()
    
    async def _handle_summary(self):
        """STATE 6: SUMMARY (Reinforces Value)"""
        logger.info(f"STATE 6: SUMMARY - User {self.user.id}")
        
        # Create summary embed with full card details
        embed = Embed(
            title=f"🎉 {self.pack_def.display_name} Summary",
            description=f"Your pack revealed {len(self.cards)} amazing cards!",
            color=self._get_pack_color()
        )
        
        # Full card list with tiers and serials
        card_list = []
        for i, card in enumerate(self.cards, 1):
            tier_emoji = self._get_tier_emoji(CardTier(card.rarity["tier"]))
            hero_star = "⭐" if card.is_hero_card() else ""
            card_list.append(f"{i}. {tier_emoji} {card.artist['name']} ({card.identity['serial']}){hero_star}")
        
        embed.add_field(
            name="📋 Cards Received",
            value="\n".join(card_list),
            inline=False
        )
        
        # Tier summary
        tier_counts = {}
        for card in self.cards:
            tier = card.rarity["tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        summary_lines = []
        for tier in ["community", "gold", "platinum", "legendary"]:
            count = tier_counts.get(tier, 0)
            if count > 0:
                emoji = self._get_tier_emoji(CardTier(tier))
                summary_lines.append(f"{emoji} {tier.title()}: {count}")
        
        embed.add_field(
            name="📊 Tier Breakdown",
            value="\n".join(summary_lines),
            inline=True
        )
        
        # Legendary highlights
        if self.legendary_cards:
            legendary_text = "\n".join([
                f"👑 {card.artist['name']} ({card.identity['serial']}) - {card.get_print_display()}"
                for card in self.legendary_cards
            ])
            embed.add_field(
                name="👑 Legendary Cards",
                value=legendary_text,
                inline=True
            )
        
        # Value reinforcement
        embed.add_field(
            name="💎 Pack Value",
            value=f"**Hero Slot:** {'✅' if self.pack_def.has_hero_slot() else '❌'}\n"
                  f"**Legendary Pulls:** {len(self.legendary_cards)}\n"
                  f"**Total Value:** {self._calculate_pack_value()}",
            inline=False
        )
        
        embed.set_footer(text=f"Pack opened by {self.user.display_name} • Choose your next action")
        
        # Create view with three action buttons
        self.view = SummaryView(self)
        
        await self.message.edit(embed=embed, view=self.view)
        
        # Set timer for auto-complete (10 seconds)
        asyncio.create_task(self._summary_timeout())
    
    async def handle_summary_button_click(self, interaction: Interaction):
        """Handle Complete button click"""
        await interaction.response.defer()
        
        # Transition to COMPLETE
        self.current_state = PackOpeningState.COMPLETE
        await self._handle_complete()
    
    async def _handle_complete(self):
        """STATE 7: COMPLETE (View expires after timeout)"""
        logger.info(f"STATE 7: COMPLETE - User {self.user.id}")
        
        # Create completion embed
        embed = Embed(
            title="✅ Pack Opening Complete",
            description=f"Your {self.pack_def.display_name} cards have been added to your collection!",
            color=Color.green()
        )
        
        # Final confirmation
        embed.add_field(
            name="🎯 Collection Updated",
            value=f"**Cards Added:** {len(self.cards)}\n"
                  f"**Legendary Cards:** {len(self.legendary_cards)}\n"
                  f"**Total Opening Time:** {int(time.time() - self.start_time)} seconds",
            inline=False
        )
        
        embed.set_footer(text="Thank you for opening a pack! • View your collection anytime")
        
        # Remove view - state expires
        await self.message.edit(embed=embed, view=None)
        
        # Remove from active registry (simulates Redis cleanup)
        complete_opening(str(self.user.id))
        
        # Audit already written during payment processing
        logger.info(f"Pack opening completed and cleaned up for user {self.user.id}")
    
    async def _summary_timeout(self):
        """Auto-complete summary after 10 seconds"""
        await asyncio.sleep(10.0)  # Summary display time
        
        if self.current_state == PackOpeningState.SUMMARY:
            logger.info(f"Summary timeout for user {self.user.id}")
            await self._transition_to_complete()
    
    async def _transition_to_complete(self):
        """Transition to COMPLETE state"""
        self.current_state = PackOpeningState.COMPLETE
        await self._handle_complete()
    
    def _calculate_pack_value(self) -> str:
        """Calculate pack value for display"""
        # Simple value calculation based on tiers
        tier_values = {
            "community": 10,
            "gold": 50,
            "platinum": 200,
            "legendary": 1000
        }
        
        total_value = 0
        for card in self.cards:
            tier = card.rarity["tier"]
            total_value += tier_values.get(tier, 10)
        
        # Add hero slot bonus
        if self.pack_def.has_hero_slot():
            total_value += 100
        
        # Add legendary bonus
        total_value += len(self.legendary_cards) * 500
        
        return f"{total_value:,} points"
    
    def _create_card_reveal_embed(self, card: CanonicalCard, card_number: int, total_cards: int) -> Embed:
        """Create embed for individual card reveal"""
        tier = CardTier(card.rarity["tier"])
        color = self._get_tier_color(tier)
        
        embed = Embed(
            title=f"🎴 Card #{card_number} of {total_cards}",
            description=f"**{card.artist['name']}** - {card.get_rarity_display()}",
            color=color
        )
        
        # Card image (hero crop)
        embed.set_image(url="https://example.com/card_hero_crop.png")
        
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
            badge_text = " ".join([self._get_badge_emoji(badge) for badge in card.presentation["badge_icons"]])
            embed.add_field(name="🏆 Badges", value=badge_text, inline=False)
        
        # Hero card indicator
        if card.is_hero_card():
            embed.add_field(
                name="⭐ HERO CARD",
                value="Selected for premium hero slot with boosted artist selection!",
                inline=False
            )
        
        # Foil indicator
        if card.presentation.get("foil", False):
            embed.add_field(
                name="✨ Foil Card",
                value="This card has a special foil finish!",
                inline=False
            )
        
        embed.set_footer(text=f"Card {card_number} of {total_cards} • Serial: {card.identity['serial']}")
        
        return embed
    
    def _create_summary_embed(self) -> Embed:
        """Create summary embed"""
        embed = Embed(
            title=f"🎉 {self.pack_def.display_name} Summary",
            description=f"Your pack revealed {len(self.cards)} amazing cards!",
            color=self._get_pack_color()
        )
        
        # Card summary by tier
        tier_counts = {}
        for card in self.cards:
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
        
        # Highlight legendary cards
        if self.legendary_cards:
            legendary_text = "\n".join([
                f"👑 {card.artist['name']} ({card.identity['serial']})"
                for card in self.legendary_cards
            ])
            embed.add_field(
                name="👑 Legendary Cards",
                value=legendary_text,
                inline=False
            )
        
        # Hero card highlight
        hero_cards = [c for c in self.cards if c.is_hero_card()]
        if hero_cards:
            hero_card = hero_cards[0]
            embed.add_field(
                name="⭐ Hero Card",
                value=f"**{hero_card.artist['name']}**\n"
                      f"Selected for premium hero slot!",
                inline=False
            )
        
        embed.set_footer(text=f"Pack opened by {self.user.display_name} • Click Complete to finish")
        
        return embed
    
    def _get_pack_color(self) -> Color:
        """Get color based on pack type"""
        pack_colors = {
            "starter": Color.light_grey(),
            "silver": Color.from_rgb(192, 192, 192),
            "gold": Color.gold(),
            "black": Color.dark_grey(),
            "founder_gold": Color.gold(),
            "founder_black": Color.dark_grey()
        }
        return pack_colors.get(self.pack_def.key, Color.blue())
    
    def _get_tier_color(self, tier: CardTier) -> Color:
        """Get color based on card tier"""
        tier_colors = {
            CardTier.COMMUNITY: Color.light_grey(),
            CardTier.GOLD: Color.gold(),
            CardTier.PLATINUM: Color.from_rgb(192, 192, 192),
            CardTier.LEGENDARY: Color.dark_gold()
        }
        return tier_colors.get(tier, Color.blue())
    
    def _get_tier_emoji(self, tier: CardTier) -> str:
        """Get emoji for card tier"""
        tier_emojis = {
            CardTier.COMMUNITY: "⚪",
            CardTier.GOLD: "🟡",
            CardTier.PLATINUM: "💎",
            CardTier.LEGENDARY: "👑"
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

class SealedPackView(View):
    """View for sealed pack state"""
    
    def __init__(self, fsm: PackOpeningFSM):
        super().__init__(timeout=300)  # 5 minute timeout
        self.fsm = fsm
    
    @discord.ui.button(label="▶ Open Pack", style=discord.ButtonStyle.primary, custom_id="open_pack")
    async def open_pack_button(self, interaction: Interaction, button: Button):
        """Handle Open Pack button click"""
        # Verify user
        if interaction.user.id != self.fsm.user.id:
            await interaction.response.send_message("This is not your pack!", ephemeral=True)
            return
        
        await self.fsm.handle_sealed_button_click(interaction)
    
    async def on_timeout(self):
        """Handle view timeout"""
        logger.info(f"Pack opening view timed out for user {self.fsm.user.id}")

class CardRevealView(View):
    """View for card reveal state"""
    
    def __init__(self, fsm: PackOpeningFSM):
        super().__init__(timeout=300)  # 5 minute timeout
        self.fsm = fsm
    
    @discord.ui.button(label="▶ Next Card", style=discord.ButtonStyle.primary, custom_id="next_card")
    async def next_card_button(self, interaction: Interaction, button: Button):
        """Handle Next Card button click"""
        # Verify user
        if interaction.user.id != self.fsm.user.id:
            await interaction.response.send_message("This is not your pack!", ephemeral=True)
            return
        
        await self.fsm.handle_card_reveal_button_click(interaction)
    
    async def on_timeout(self):
        """Handle view timeout"""
        logger.info(f"Card reveal view timed out for user {self.fsm.user.id}")

class SummaryView(View):
    """View for summary state with three action buttons"""
    
    def __init__(self, fsm: PackOpeningFSM):
        super().__init__(timeout=300)  # 5 minute timeout
        self.fsm = fsm
        self.last_interaction = time.time()
    
    @discord.ui.button(label="📦 View Collection", style=discord.ButtonStyle.secondary, custom_id="view_collection")
    async def view_collection_button(self, interaction: Interaction, button: Button):
        """Handle View Collection button click"""
        # Verify user
        if interaction.user.id != self.fsm.user.id:
            await interaction.response.send_message("This is not your pack!", ephemeral=True)
            return
        
        # Update last interaction
        self.last_interaction = time.time()
        
        await interaction.response.send_message(
            f"📦 Your collection has been updated with {len(self.fsm.cards)} new cards!\n"
            f"Use `/collection` to view all your cards.",
            ephemeral=True
        )
    
    @discord.ui.button(label="🔁 Open Another", style=discord.ButtonStyle.primary, custom_id="open_another")
    async def open_another_button(self, interaction: Interaction, button: Button):
        """Handle Open Another button click"""
        # Verify user
        if interaction.user.id != self.fsm.user.id:
            await interaction.response.send_message("This is not your pack!", ephemeral=True)
            return
        
        # Update last interaction
        self.last_interaction = time.time()
        
        await interaction.response.send_message(
            f"🔁 Ready to open another pack!\n"
            f"Use `/open pack:black` to open another Black Pack.",
            ephemeral=True
        )
    
    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.danger, custom_id="close")
    async def close_button(self, interaction: Interaction, button: Button):
        """Handle Close button click"""
        # Verify user
        if interaction.user.id != self.fsm.user.id:
            await interaction.response.send_message("This is not your pack!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Transition to COMPLETE
        self.fsm.current_state = PackOpeningState.COMPLETE
        await self.fsm._handle_complete()
    
    async def on_timeout(self):
        """Handle view timeout - auto complete"""
        logger.info(f"Summary view timed out for user {self.fsm.user.id}")
        
        # Auto-transition to complete
        if self.fsm.current_state == PackOpeningState.SUMMARY:
            await self.fsm._transition_to_complete()

# Global FSM registry for tracking active openings
active_openings: Dict[str, PackOpeningFSM] = {}

async def start_pack_opening(user: User, pack_def: PackDefinition, cards: List[CanonicalCard], channel) -> Optional[PackOpeningFSM]:
    """Start a new pack opening FSM"""
    # Check for existing active opening
    if str(user.id) in active_openings:
        existing_fsm = active_openings[str(user.id)]
        if existing_fsm.current_state != PackOpeningState.COMPLETE:
            return None  # User already has active opening
    
    # Create new FSM
    fsm = PackOpeningFSM(user, pack_def, cards)
    active_openings[str(user.id)] = fsm
    
    # Start opening
    success = await fsm.start_opening(channel)
    
    if not success:
        # Remove from registry if failed
        del active_openings[str(user.id)]
        return None
    
    return fsm

def get_active_opening(user_id: str) -> Optional[PackOpeningFSM]:
    """Get active opening for user"""
    return active_openings.get(user_id)

def complete_opening(user_id: str):
    """Mark opening as complete and remove from registry"""
    if user_id in active_openings:
        fsm = active_openings[user_id]
        if fsm.current_state == PackOpeningState.COMPLETE:
            del active_openings[user_id]
