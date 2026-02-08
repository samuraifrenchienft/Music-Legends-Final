# cogs/gameplay.py
import discord
import asyncio
import time
import sqlite3
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Interaction, app_commands, ui
from typing import Dict, List
import random
from card_economy import CardEconomyManager
from database import DatabaseManager



class CardDropView(discord.ui.View):
    """Button view for card drops — first click claims the card."""

    TIER_COLORS = {
        "community": discord.Color.light_gray(),
        "gold": discord.Color.gold(),
        "platinum": discord.Color.purple(),
    }
    RARITY_EMOJI = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "🌟"}
    TIER_EMOJI = {"community": "⚪", "gold": "🟡", "platinum": "🟣"}

    def __init__(self, card: dict, db, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.card = card
        self.db = db
        self.claimed_by = None
        self.message = None

    @discord.ui.button(label="🎴 Claim Card!", style=discord.ButtonStyle.success)
    async def claim_button(self, interaction: Interaction, button: discord.ui.Button):
        if self.claimed_by is not None:
            await interaction.response.send_message("Already claimed!", ephemeral=True)
            return

        self.claimed_by = interaction.user.id
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}!"
        button.style = discord.ButtonStyle.secondary

        awarded = self.db.award_drop_card(interaction.user.id, self.card["card_id"])

        rarity_emoji = self.RARITY_EMOJI.get(self.card["rarity"], "⚪")
        tier_emoji = self.TIER_EMOJI.get(self.card["tier"], "⚪")

        embed = discord.Embed(
            title=f"{tier_emoji} Card Claimed! {tier_emoji}",
            description=f"{interaction.user.mention} grabbed **{self.card['artist_name']}**!",
            color=self.TIER_COLORS.get(self.card["tier"], discord.Color.green())
        )
        embed.add_field(name="Artist", value=self.card["artist_name"], inline=True)
        embed.add_field(name="Rarity", value=f"{rarity_emoji} {self.card['rarity'].title()}", inline=True)
        embed.add_field(name="Tier", value=self.card["tier"].title(), inline=True)
        if self.card.get("image_url"):
            embed.set_thumbnail(url=self.card["image_url"])
        embed.set_footer(text="Check /collection to see your cards!")

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        if self.claimed_by is None and self.message:
            for child in self.children:
                child.disabled = True
                child.label = "Expired"
                child.style = discord.ButtonStyle.secondary
            try:
                await self.message.edit(content="⏰ Drop expired — nobody claimed it.", view=self)
            except Exception:
                pass


class GameplayCommands(commands.Cog):
    """Main gameplay commands - drops, collection, viewing, trading"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager()
        self.economy.initialize_economy_tables()
        
    def _get_power_tier(self, power: int) -> str:
        """Get power tier description based on power level"""
        if power >= 90:
            return "🔥 **GOD TIER** - Untouchable!"
        elif power >= 80:
            return "⭐ **LEGENDARY** - Elite Status!"
        elif power >= 70:
            return "🟣 **EPIC** - Powerful Force!"
        elif power >= 60:
            return "🔵 **RARE** - Above Average!"
        elif power >= 50:
            return "⚪ **COMMON** - Standard Power!"
        else:
            return "🌱 **ROOKIE** - Growing Potential!"

    @app_commands.command(name="drop", description="[DEV] Drop a random card in this channel")
    @app_commands.describe(tier="Card tier to drop")
    @app_commands.choices(tier=[
        app_commands.Choice(name="Community (Common/Rare)", value="community"),
        app_commands.Choice(name="Gold (Rare/Epic)", value="gold"),
        app_commands.Choice(name="Platinum (Epic/Legendary)", value="platinum"),
    ])
    async def drop_command(self, interaction: Interaction, tier: str = "community"):
        """Dev-only: drop a random card from LIVE packs into this channel."""
        import os
        dev_ids = os.getenv("DEV_USER_IDS", "").split(",")
        if str(interaction.user.id) not in [uid.strip() for uid in dev_ids if uid.strip()]:
            await interaction.response.send_message("❌ Dev only.", ephemeral=True)
            return

        card = self.db.get_random_card_from_tier(tier)
        if not card:
            await interaction.response.send_message(
                f"❌ No cards found for tier **{tier}**. Make sure LIVE packs exist.",
                ephemeral=True
            )
            return

        tier_colors = {
            "community": discord.Color.light_gray(),
            "gold": discord.Color.gold(),
            "platinum": discord.Color.purple()
        }
        tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣"}.get(tier, "⚪")
        rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "🌟"}.get(card["rarity"], "⚪")

        embed = discord.Embed(
            title=f"{tier_emoji} CARD DROP! {tier_emoji}",
            description="First to click claims it!",
            color=tier_colors.get(tier, discord.Color.gold())
        )
        embed.add_field(name="Artist", value=card["artist_name"], inline=True)
        embed.add_field(name="Rarity", value=f"{rarity_emoji} {card['rarity'].title()}", inline=True)
        embed.add_field(name="Tier", value=tier.title(), inline=True)
        if card.get("image_url"):
            embed.set_thumbnail(url=card["image_url"])
        embed.set_footer(text=f"Dropped by {interaction.user.display_name} • Expires in 5 min")

        view = CardDropView(card=card, db=self.db, timeout=300)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="collection", description="View your card collection")
    async def collection_command(self, interaction: Interaction, user: discord.User = None):
        """View user's card collection with card IDs for viewing"""
        target_user = user or interaction.user
        
        # Get collection using database method that returns dicts
        cards = self.db.get_user_collection(target_user.id)
        
        # Get inventory separately
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_inventory WHERE user_id = ?", (target_user.id,))
            inventory = cursor.fetchone()
        
        embed = discord.Embed(
            title=f"🎴 {target_user.display_name}'s Collection",
            description=f"**Total Cards:** {len(cards)}\nUse `/view <card_id>` to see full card details",
            color=discord.Color.blue()
        )
        
        if inventory:
            embed.add_field(
                name="💰 Currency",
                value=f"Gold: {inventory[1] or 0:,}\n"
                      f"Dust: {inventory[2] or 0}\n"
                      f"Tickets: {inventory[3] or 0}\n"
                      f"Gems: {inventory[4] or 0}",
                inline=True
            )
        
        # Group cards by rarity
        rarity_counts = {"common": 0, "rare": 0, "epic": 0, "legendary": 0, "mythic": 0}
        for card in cards:
            rarity = (card.get('rarity') or 'common').lower()
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1
        
        embed.add_field(
            name="📊 By Rarity",
            value=f"⚪ Common: {rarity_counts['common']}\n"
                  f"� Rare: {rarity_counts['rare']}\n"
                  f"⭐ Legendary: {rarity_counts['legendary']}\n"
                  f"🔴 Mythic: {rarity_counts['mythic']}",
            inline=True
        )
        
        # Show cards with interactive buttons (up to 12)
        if cards:
            # Create view with card selection buttons
            view = discord.ui.View(timeout=180)
            
            # Add buttons for first 12 cards
            for i, card in enumerate(cards[:12]):
                rarity = (card.get('rarity') or 'common').lower()
                rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}.get(rarity, "⚪")
                card_name = card.get('name', 'Unknown')
                card_title = card.get('title', '')
                card_id = card.get('card_id', '')
                
                # Truncate long names for button
                display = f"{card_name}"
                if card_title:
                    display += f" - {card_title}"
                if len(display) > 25:
                    display = display[:22] + "..."
                
                button_label = f"{rarity_emoji} {display}"
                
                # Create button
                button = discord.ui.Button(
                    label=button_label,
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"view_card_{card_id}"
                )
                
                # Add click handler
                async def button_callback(interaction: Interaction, card_id=card_id):
                    try:
                        await self.view_command(interaction, card_id)
                    except Exception as e:
                        print(f"❌ Button callback error: {e}")
                        # Use followup.send after defer, not response.send_message
                        await interaction.followup.send("❌ Could not load card details. Please try again.", ephemeral=True)
                
                button.callback = button_callback
                view.add_item(button)
            
            # Create card list text
            card_list = ""
            for card in cards[:12]:
                rarity = (card.get('rarity') or 'common').lower()
                rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}.get(rarity, "⚪")
                card_name = card.get('name', 'Unknown')
                card_id = card.get('card_id', '')
                card_list += f"{rarity_emoji} **{card_name}** - `{card_id}`\n"
            
            if len(cards) > 12:
                card_list += f"\n*...and {len(cards) - 12} more cards (use `/view <card_id>` for others)*"
            
            embed.add_field(
                name="🎴 Click a card to view:",
                value=card_list or "No cards yet!",
                inline=False
            )
            
            embed.set_footer(text="Click any card button above to see the full card design!")
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        else:
            embed.add_field(
                name="🎴 Your Cards",
                value="No cards yet! Use `/drop` or open packs to get cards.",
                inline=False
            )
        
        embed.set_footer(text="Tip: Use /view <card_id> to see full card with image")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="view", description="View details of a specific card")
    @app_commands.describe(card_identifier="Card ID or serial number to view")
    async def view_command(self, interaction: Interaction, card_identifier: str):
        """View detailed information about a specific card with full visual display"""
        # Find card by card_id or serial_number in user's collection
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            # Get column names for proper dict conversion
            cursor.execute("""
                SELECT c.*, uc.acquired_at, uc.acquired_from, uc.is_favorite
                FROM cards c
                JOIN user_cards uc ON c.card_id = uc.card_id
                WHERE (c.card_id = ? OR c.serial_number = ? OR c.name LIKE ?) AND uc.user_id = ?
            """, (card_identifier, card_identifier, f"%{card_identifier}%", interaction.user.id))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                card = dict(zip(columns, row))
            else:
                card = None
        
        if not card:
            await interaction.response.send_message("❌ Card not found in your collection! Use `/collection` to see your cards.", ephemeral=True)
            return
        
        # Extract card data with safe defaults
        card_id = card.get('card_id', 'Unknown')
        card_name = card.get('name', 'Unknown Artist')
        card_title = card.get('title', '')
        rarity = card.get('rarity', 'Common')
        image_url = card.get('image_url', '')
        youtube_url = card.get('youtube_url', '')
        variant = card.get('variant', 'Classic')
        era = card.get('era', '')
        
        # Stats
        impact = card.get('impact', 50) or 50
        skill = card.get('skill', 50) or 50
        longevity = card.get('longevity', 50) or 50
        culture = card.get('culture', 50) or 50
        hype = card.get('hype', 50) or 50
        total_power = impact + skill + longevity + culture + hype
        
        # Acquisition info
        acquired_at = card.get('acquired_at', '')
        acquired_from = card.get('acquired_from', 'Unknown')
        is_favorite = card.get('is_favorite', False)
        
        # Rarity styling
        RARITY_COLORS = {
            "Common": discord.Color.light_grey(),
            "common": discord.Color.light_grey(),
            "Rare": discord.Color.blue(),
            "rare": discord.Color.blue(),
            "Epic": discord.Color.purple(),
            "epic": discord.Color.purple(),
            "Legendary": discord.Color.gold(),
            "legendary": discord.Color.gold(),
            "Mythic": discord.Color.red(),
            "mythic": discord.Color.red(),
        }
        
        RARITY_EMOJI = {
            "Common": "⚪", "common": "⚪",
            "Rare": "�", "rare": "🔵",
            "Epic": "🟣", "epic": "🟣",
            "Legendary": "⭐", "legendary": "⭐",
            "Mythic": "🔴", "mythic": "🔴",
        }
        
        rarity_emoji = RARITY_EMOJI.get(rarity, "🎴")
        rarity_color = RARITY_COLORS.get(rarity, discord.Color.blurple())
        
        # Build the card embed
        display_title = f"{card_name} — \"{card_title}\"" if card_title else card_name
        
        # Create clean, professional card design
        rarity_display = {
            "common": "⚪ COMMON",
            "rare": "🔵 RARE", 
            "epic": "🟣 EPIC",
            "legendary": "⭐ LEGENDARY",
            "mythic": "🔴 MYTHIC"
        }.get(rarity.lower(), "⚪ COMMON")
        
        embed = discord.Embed(
            title=f"{rarity_display} CARD",
            description=f"**{display_title}**",
            color=rarity_color
        )
        
        # Clean separator
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="**� ARTIST STATS** �",
            inline=False
        )
        
        # Card info with branding
        info_value = f"**🆔 Card ID:** `{card_id}`\n"
        if variant and variant != 'Classic':
            info_value += f"**🎨 Variant:** {variant}\n"
        if era:
            info_value += f"**⏰ Era:** {era}\n"
        info_value += f"**⭐ Favorite:** {'⭐ Yes' if is_favorite else 'No'}"
        
        embed.add_field(
            name="📋 **CARD DETAILS**",
            value=info_value,
            inline=True
        )
        
        # Stats with visual design
        stats_value = f"⚔️ **Impact:** `{impact:02d}`\n"
        stats_value += f"🛡️ **Skill:** `{skill:02d}`\n"
        stats_value += f"⚡ **Longevity:** `{longevity:02d}`\n"
        stats_value += f"🎭 **Culture:** `{culture:02d}`\n"
        stats_value += f"🔥 **Hype:** `{hype:02d}`"
        
        embed.add_field(
            name="📊 **BATTLE STATS**",
            value=stats_value,
            inline=True
        )
        
        # Power rating with enhanced visual
        total_power = (impact + skill + longevity + culture + hype) // 5
        power_bar = "██████████"[:total_power // 10] + "░░░░░░░░░░"[total_power // 10:]
        
        embed.add_field(
            name="💪 **POWER LEVEL**",
            value=f"```{power_bar}```\n**{total_power}** / 100 **POWER**\n{self._get_power_tier(total_power)}",
            inline=False
        )
        
        # Clean footer
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="**Music Legends** • Artist Battle Game",
            inline=False
        )
        
        # Links
        links = []
        if youtube_url:
            links.append(f"[▶️ YouTube]({youtube_url})")
        if links:
            embed.add_field(name="🔗 **STREAMING LINKS**", value=" • ".join(links), inline=False)
        
        # Acquisition info
        acq_date = acquired_at[:10] if acquired_at and len(acquired_at) >= 10 else 'Unknown'
        serial = card.get('serial_number') or card.get('card_id', 'Unknown')
        embed.add_field(
            name="📅 **ACQUISITION**",
            value=f"**Date:** {acq_date}\n**Source:** {acquired_from.replace('_', ' ').title()}\n**Serial:** {serial}",
            inline=False
        )
        
        # Set card image (thumbnail for small, image for large display)
        if image_url:
            embed.set_image(url=image_url)  # Large image display
        
        embed.set_footer(text="Music Legends • Use /collection to see all your cards")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="card", description="Preview any card in the database")
    @app_commands.describe(card_id="Card ID to preview")
    async def card_preview_command(self, interaction: Interaction, card_id: str):
        """Preview any card in the database (not just owned ones)"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                card = dict(zip(columns, row))
            else:
                card = None
            
            # Check if user owns this card
            cursor.execute("""
                SELECT acquired_at, acquired_from FROM user_cards 
                WHERE card_id = ? AND user_id = ?
            """, (card_id, interaction.user.id))
            ownership = cursor.fetchone()
        
        if not card:
            await interaction.response.send_message("❌ Card not found in database!", ephemeral=True)
            return
        
        # Extract card data
        card_name = card.get('name', 'Unknown Artist')
        card_title = card.get('title', '')
        rarity = card.get('rarity', 'Common')
        image_url = card.get('image_url', '')
        youtube_url = card.get('youtube_url', '')
        variant = card.get('variant', 'Classic')
        era = card.get('era', '')
        
        # Stats
        impact = card.get('impact', 50) or 50
        skill = card.get('skill', 50) or 50
        longevity = card.get('longevity', 50) or 50
        culture = card.get('culture', 50) or 50
        hype = card.get('hype', 50) or 50
        total_power = impact + skill + longevity + culture + hype
        
        # Rarity styling
        RARITY_COLORS = {
            "Common": discord.Color.light_grey(), "common": discord.Color.light_grey(),
            "Rare": discord.Color.blue(), "rare": discord.Color.blue(),
            "Epic": discord.Color.purple(), "epic": discord.Color.purple(),
            "Legendary": discord.Color.gold(), "legendary": discord.Color.gold(),
            "Mythic": discord.Color.red(), "mythic": discord.Color.red(),
        }
        RARITY_EMOJI = {
            "Common": "⚪", "common": "⚪", "Rare": "🔵", "rare": "🔵",
            "Epic": "🟣", "epic": "🟣", "Legendary": "⭐", "legendary": "⭐",
            "Mythic": "🔴", "mythic": "🔴",
        }
        
        rarity_emoji = RARITY_EMOJI.get(rarity, "🎴")
        rarity_color = RARITY_COLORS.get(rarity, discord.Color.blurple())
        
        # Build embed
        display_title = f"{card_name} — \"{card_title}\"" if card_title else card_name
        
        embed = discord.Embed(
            title=f"{rarity_emoji} {rarity.upper()} — ARTIST CARD",
            description=f"**{display_title}**\n`ID: {card_id}`",
            color=rarity_color
        )
        
        # Stats
        stats_text = (
            f"**Impact:** {impact}\n"
            f"**Skill:** {skill}\n"
            f"**Longevity:** {longevity}\n"
            f"**Culture:** {culture}\n"
            f"**Hype:** {hype}\n"
            f"───────────\n"
            f"**Total Power:** {total_power}"
        )
        embed.add_field(name="📊 Battle Stats", value=stats_text, inline=True)
        
        # Ownership status
        if ownership:
            owned_text = f"✅ **You own this card!**\nAcquired: {ownership[0][:10] if ownership[0] else 'Unknown'}"
        else:
            owned_text = "❌ You don't own this card"
        embed.add_field(name="📋 Ownership", value=owned_text, inline=True)
        
        # Links
        links = []
        if youtube_url:
            links.append(f"[▶️ YouTube]({youtube_url})")
        if links:
            embed.add_field(name="🔗 Links", value=" • ".join(links), inline=False)
        
        # Image
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_footer(text="Music Legends • Card Preview")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lookup", description="Lookup cards by artist name")
    async def lookup_command(self, interaction: Interaction, artist_name: str):
        """Lookup all cards for a specific artist in the database"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            # Search in both name and artist_name columns (with safe defaults for missing columns)
            cursor.execute("""
                SELECT c.card_id, c.name, c.rarity,
                       COALESCE(c.tier, CASE
                           WHEN LOWER(c.rarity) = 'common' THEN 'community'
                           WHEN LOWER(c.rarity) = 'rare' THEN 'gold'
                           WHEN LOWER(c.rarity) = 'epic' THEN 'platinum'
                           ELSE 'legendary'
                       END) as tier,
                       COALESCE(c.serial_number, c.card_id) as serial_number,
                       COALESCE(c.print_number, 1) as print_number,
                       COALESCE(c.quality, 'standard') as quality,
                       COALESCE(c.artist_name, c.name) as artist_name,
                       CASE WHEN uc.user_id = ? THEN 1 ELSE 0 END as owned
                FROM cards c
                LEFT JOIN user_cards uc ON c.card_id = uc.card_id AND uc.user_id = ?
                WHERE c.name LIKE ? OR c.artist_name LIKE ?
                ORDER BY tier DESC, print_number ASC
                LIMIT 50
            """, (interaction.user.id, interaction.user.id, f"%{artist_name}%", f"%{artist_name}%"))
            cards = cursor.fetchall()
        
        if not cards:
            await interaction.response.send_message(f"❌ No cards found for '{artist_name}'!", ephemeral=True)
            return
        
        # Create embed showing all cards
        owned_count = sum(1 for card in cards if card[8] == 1)
        embed = discord.Embed(
            title=f"🔍 Cards for '{artist_name}'",
            description=f"Found {len(cards)} card(s) | You own: {owned_count}",
            color=discord.Color.blue()
        )
        
        # Group by tier
        tier_groups = {}
        for card in cards:
            tier = card[3] if card[3] else 'community'
            if tier not in tier_groups:
                tier_groups[tier] = []
            tier_groups[tier].append(card)
        
        # Display by tier
        tier_order = ['legendary', 'platinum', 'gold', 'community']
        for tier in tier_order:
            if tier in tier_groups:
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(tier, "⚪")
                cards_text = ""
                for card in tier_groups[tier][:5]:  # Limit to 5 per tier
                    owned_marker = "✅" if card[8] == 1 else "⬜"
                    serial = card[4] if card[4] else 'N/A'
                    print_num = card[5] if card[5] else 0
                    quality = card[6] if card[6] else 'standard'
                    cards_text += f"{owned_marker} {tier_emoji} `{serial}` - Print #{print_num} ({quality})\n"
                
                if len(tier_groups[tier]) > 5:
                    cards_text += f"... and {len(tier_groups[tier]) - 5} more\n"
                
                embed.add_field(
                    name=f"{tier.title()} Cards ({len(tier_groups[tier])})",
                    value=cards_text or "None",
                    inline=False
                )
        
        embed.set_footer(text="✅ = Owned | ⬜ = Not owned")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="burn", description="Burn a card for dust")
    async def burn_command(self, interaction: Interaction, serial_number: str):
        """Burn a card to receive dust"""
        result = self.economy.burn_card_for_dust(interaction.user.id, serial_number)
        
        if result['success']:
            embed = discord.Embed(
                title="🔥 Card Burned!",
                description=f"You burned {serial_number} and received {result['dust_earned']} dust!",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="💰 New Dust Total",
                value=f"Check your collection with `/collection`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)

    @app_commands.command(name="upgrade", description="Upgrade cards to higher tiers")
    async def upgrade_command(self, interaction: Interaction, upgrade_type: str):
        """Upgrade cards to higher tier"""
        valid_types = ['community_to_gold', 'gold_to_platinum', 'platinum_to_legendary']
        
        if upgrade_type not in valid_types:
            await interaction.response.send_message("❌ Invalid upgrade type!", ephemeral=True)
            return
        
        # Create upgrade view for card selection
        view = CardUpgradeView(self.economy, interaction.user.id, upgrade_type, db=self.db)
        
        embed = discord.Embed(
            title="⬆️ Card Upgrade",
            description=f"Select {self.economy.upgrade_costs[upgrade_type]} cards to upgrade",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="daily", description="Claim daily rewards")
    async def daily_command(self, interaction: Interaction):
        """Claim daily rewards with streak bonuses, free card, and audio feedback"""
        from pathlib import Path

        # Defer immediately — DB + card lookup can exceed 3s interaction timeout
        await interaction.response.defer(ephemeral=True)

        # Use the new database method that includes free card
        result = self.db.claim_daily_reward(interaction.user.id)

        if not result.get('success'):
            await interaction.followup.send(
                f"❌ {result.get('error', 'Already claimed today!')}",
                ephemeral=True
            )
            return

        gold_reward = result.get('gold', 0)
        ticket_reward = result.get('tickets', 0)
        current_streak = result.get('streak', 1)
        daily_card = result.get('card')
        
        # Check for audio file
        audio_path = Path('assets/sounds/daily_claim.mp3')
        audio_file = None
        if audio_path.exists():
            audio_file = discord.File(str(audio_path), filename='daily_claim.mp3')
        
        # Create reward embed
        is_milestone = current_streak in [3, 7, 14, 30]
        
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!" if not is_milestone else f"🎉 DAY {current_streak} MILESTONE! 🎉",
            description=f"**Day {current_streak} Streak!** {'🔥' * min(current_streak, 10)}",
            color=discord.Color.gold()
        )
        
        # Add GIF for milestones
        if is_milestone:
            celebration_gif = 'https://media.tenor.com/Cvx2qeKmAOEAAAAC/fireworks-celebration.gif'
            embed.set_image(url=celebration_gif)
        
        rewards_text = f"💰 Gold: +{gold_reward}"
        if ticket_reward > 0:
            rewards_text += f"\n🎫 Tickets: +{ticket_reward}"

        embed.add_field(
            name="Today's Rewards",
            value=rewards_text,
            inline=False
        )

        # Display daily free card if received
        if daily_card:
            rarity_emoji = {
                'common': '⚪',
                'rare': '🔵',
                'epic': '🟣',
                'legendary': '🟡'
            }.get(daily_card.get('rarity', 'common'), '⚪')

            embed.add_field(
                name="🎴 Daily Card",
                value=f"{rarity_emoji} **{daily_card.get('name', 'Unknown')}** ({daily_card.get('rarity', 'common').title()})",
                inline=False
            )
        
        # Show next milestone
        next_milestones = {3: "Day 3: 150 gold", 7: "Day 7: 300 gold + 1 ticket", 
                          14: "Day 14: 600 gold + 2 tickets", 30: "Day 30: 1,100 gold + 5 tickets"}
        
        next_milestone = None
        for day, reward in next_milestones.items():
            if current_streak < day:
                next_milestone = reward
                days_until = day - current_streak
                break
        
        if next_milestone:
            embed.add_field(
                name="🎯 Next Milestone",
                value=f"{next_milestone}\n({days_until} day{'s' if days_until > 1 else ''} away)",
                inline=False
            )
        
        embed.set_footer(text="Come back tomorrow to keep your streak!")
        
        # Send with audio if available (use followup since we deferred)
        if audio_file:
            await interaction.followup.send(embed=embed, file=audio_file, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="rank", description="View your rank and XP progress")
    async def rank_command(self, interaction: Interaction, user: discord.User = None):
        """View rank and XP progression"""
        from config.economy import RANKS, get_rank, get_next_rank
        
        target_user = user or interaction.user
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT xp, gold, tickets FROM user_inventory WHERE user_id = ?
            """, (target_user.id,))
            inv_row = cursor.fetchone()
            
            cursor.execute("""
                SELECT wins, total_battles FROM users WHERE user_id = ?
            """, (target_user.id,))
            stats_row = cursor.fetchone()
        
        xp = inv_row[0] if inv_row and inv_row[0] else 0
        gold = inv_row[1] if inv_row and inv_row[1] else 0
        tickets = inv_row[2] if inv_row and inv_row[2] else 0
        wins = stats_row[0] if stats_row and stats_row[0] else 0
        total_battles = stats_row[1] if stats_row and stats_row[1] else 0
        
        # Calculate rank
        current_rank = get_rank(xp, wins)
        rank_info = RANKS[current_rank]
        next_rank_info = get_next_rank(current_rank)
        
        embed = discord.Embed(
            title=f"{rank_info['emoji']} {target_user.display_name}'s Profile",
            color=rank_info['color']
        )
        
        embed.add_field(
            name="🏅 Rank",
            value=f"**{current_rank}** {rank_info['emoji']}",
            inline=True
        )
        
        embed.add_field(
            name="⭐ XP",
            value=f"{xp:,}",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Battle Record",
            value=f"Wins: {wins}\nTotal: {total_battles}",
            inline=True
        )
        
        embed.add_field(
            name="💰 Currency",
            value=f"Gold: {gold:,}\nTickets: {tickets}",
            inline=True
        )
        
        # Progress to next rank
        if next_rank_info:
            xp_progress = min(xp / next_rank_info['xp_required'] * 100, 100) if next_rank_info['xp_required'] > 0 else 100
            wins_progress = min(wins / next_rank_info['wins_required'] * 100, 100) if next_rank_info['wins_required'] > 0 else 100
            
            progress_bar_xp = "█" * int(xp_progress / 10) + "░" * (10 - int(xp_progress / 10))
            progress_bar_wins = "█" * int(wins_progress / 10) + "░" * (10 - int(wins_progress / 10))
            
            embed.add_field(
                name=f"📈 Progress to {next_rank_info['name']}",
                value=f"XP: {xp}/{next_rank_info['xp_required']} [{progress_bar_xp}]\n"
                      f"Wins: {wins}/{next_rank_info['wins_required']} [{progress_bar_wins}]",
                inline=False
            )
        else:
            embed.add_field(
                name="👑 Max Rank Achieved!",
                value="You've reached the highest rank: Legend!",
                inline=False
            )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quicksell", description="Instantly sell a card for gold")
    async def quicksell_command(self, interaction: Interaction, serial_number: str):
        """Instantly sell a card for gold (marketplace /sell lists for other players)"""
        from config.economy import get_card_sell_price, CARD_SELL_PRICES
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Find the card in user's collection (match by serial_number or card_id)
            cursor.execute("""
                SELECT c.card_id, c.name, c.rarity, uc.user_id
                FROM cards c
                JOIN user_cards uc ON c.card_id = uc.card_id
                WHERE (c.serial_number = ? OR c.card_id = ?) AND uc.user_id = ?
            """, (serial_number, serial_number, interaction.user.id))
            card = cursor.fetchone()
            
            if not card:
                await interaction.response.send_message("❌ Card not found in your collection!", ephemeral=True)
                return
            
            card_id, card_name, rarity, owner_id = card
            
            # Check if user has duplicate of this card (same name)
            cursor.execute("""
                SELECT COUNT(*) FROM user_cards uc
                JOIN cards c ON uc.card_id = c.card_id
                WHERE uc.user_id = ? AND c.name = ?
            """, (interaction.user.id, card_name))
            count = cursor.fetchone()[0]
            is_duplicate = count > 1
            
            # Calculate sell price
            sell_price = get_card_sell_price(rarity, is_duplicate)
            
            # Remove card from collection
            cursor.execute("""
                DELETE FROM user_cards WHERE user_id = ? AND card_id = ?
            """, (interaction.user.id, card_id))
            
            # Add gold to user
            cursor.execute("""
                INSERT INTO user_inventory (user_id, gold)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET gold = gold + ?
            """, (interaction.user.id, sell_price, sell_price))
            
            conn.commit()
        
        # Create embed
        embed = discord.Embed(
            title="💰 Card Sold!",
            description=f"You sold **{card_name}** ({rarity})",
            color=discord.Color.gold()
        )
        
        price_text = f"+{sell_price} gold"
        if is_duplicate:
            base_price = CARD_SELL_PRICES.get(rarity, 10)
            price_text += f" (includes +50% duplicate bonus!)"
        
        embed.add_field(name="💵 Earned", value=price_text, inline=False)
        embed.set_footer(text=f"Serial: {serial_number}")
        
        await interaction.response.send_message(embed=embed)


class CardUpgradeView(ui.View):
    """View that lets users select cards to upgrade to the next tier."""

    # Map upgrade_type -> (source rarity, target rarity)
    RARITY_MAP = {
        'community_to_gold': ('common', 'rare'),
        'gold_to_platinum': ('rare', 'epic'),
        'platinum_to_legendary': ('epic', 'legendary'),
    }

    def __init__(self, economy_manager: CardEconomyManager, user_id: int, upgrade_type: str, db: DatabaseManager = None):
        super().__init__(timeout=180)
        self.economy = economy_manager
        self.db = db
        self.user_id = user_id
        self.upgrade_type = upgrade_type
        self.selected_cards = []
        self.required = economy_manager.upgrade_costs.get(upgrade_type, 3)
        self.source_rarity, self.target_rarity = self.RARITY_MAP.get(
            upgrade_type, ('common', 'rare'))

        # Load eligible cards from DB
        self._eligible_cards = self._load_eligible_cards()

        # Card select dropdown
        if self._eligible_cards:
            options = []
            for card in self._eligible_cards[:25]:
                name = card.get('name', 'Unknown')
                cid = card.get('card_id', '')
                label = f"{name}" if len(name) <= 50 else name[:47] + "..."
                options.append(discord.SelectOption(label=label, value=cid))

            select = ui.Select(
                placeholder=f"Select {self.required} {self.source_rarity} cards...",
                options=options,
                min_values=self.required,
                max_values=min(self.required, len(options)),
                custom_id="upgrade_card_select",
            )
            select.callback = self._on_select
            self.add_item(select)

        # Upgrade button (starts disabled)
        self.upgrade_btn = ui.Button(
            label=f"Upgrade (0/{self.required} selected)",
            style=discord.ButtonStyle.primary,
            disabled=True,
            custom_id="upgrade_button",
        )
        self.upgrade_btn.callback = self._on_upgrade
        self.add_item(self.upgrade_btn)

    def _load_eligible_cards(self) -> list:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.card_id, c.name, c.rarity
                    FROM cards c
                    JOIN user_cards uc ON c.card_id = uc.card_id
                    WHERE uc.user_id = ? AND LOWER(c.rarity) = ?
                """, (self.user_id, self.source_rarity))
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception:
            return []

    async def _on_select(self, interaction: Interaction):
        self.selected_cards = interaction.data.get('values', [])
        count = len(self.selected_cards)
        self.upgrade_btn.label = f"Upgrade ({count}/{self.required} selected)"
        self.upgrade_btn.disabled = count < self.required
        await interaction.response.edit_message(view=self)

    async def _on_upgrade(self, interaction: Interaction):
        if len(self.selected_cards) < self.required:
            return await interaction.response.send_message(
                f"Select {self.required} cards first.", ephemeral=True)

        # Remove consumed cards
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            for cid in self.selected_cards:
                cursor.execute(
                    "DELETE FROM user_cards WHERE user_id = ? AND card_id = ?",
                    (self.user_id, cid))

            # Award one card of the target rarity (random from DB)
            cursor.execute(
                "SELECT card_id, name FROM cards WHERE LOWER(rarity) = ? ORDER BY RANDOM() LIMIT 1",
                (self.target_rarity,))
            new_card = cursor.fetchone()
            if new_card:
                cursor.execute(
                    "INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from) VALUES (?, ?, 'upgrade')",
                    (self.user_id, new_card[0]))
            conn.commit()

        if new_card:
            embed = discord.Embed(
                title="⬆️ Upgrade Successful!",
                description=f"You sacrificed {self.required} {self.source_rarity} cards and received:\n"
                            f"**{new_card[1]}** ({self.target_rarity.title()})",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="⬆️ Upgrade Failed",
                description=f"No {self.target_rarity} cards available in the database.",
                color=discord.Color.red(),
            )

        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id

async def setup(bot):
    await bot.add_cog(GameplayCommands(bot))
