"""
Drop Management Commands

Fair drop system for admins to seed channels with cards.
Integrated with Season 1 supply system and server cooldowns.
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
import asyncio
import random
from datetime import datetime, timedelta
import logging

from services.drop_service import resolve_drop
from services.season_supply_system import can_mint_card, mint_card
from services.payment_service import generate_canonical_cards, get_pack_definition
from services.pack_opening_fsm import start_pack_opening
from models.drop import Drop, DropSQLite
from models.card import Card

logger = logging.getLogger(__name__)

class DropCommands(commands.Cog):
    """Drop management commands for admins"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DropSQLite()
        self.active_drops = {}  # Track active drops by message_id
    
    def _is_admin(self, interaction: Interaction) -> bool:
        """Check if user is admin"""
        if not interaction.guild:
            return False
        
        return interaction.user.guild_permissions.administrator or \
               interaction.user.guild_permissions.manage_guild
    
    @app_commands.command(
        name="drop_create",
        description="Create a card drop in a channel (Admin only)"
    )
    @app_commands.describe(
        channel="Channel to create drop in (default: current)",
        card_count="Number of cards to drop (1-10)",
        drop_type="Type of drop: fair_random, weighted_rarity, first_come"
    )
    @app_commands.choices(
        drop_type=[
            app_commands.Choice(name="Fair Random", value="fair_random"),
            app_commands.Choice(name="Weighted Rarity", value="weighted_rarity"),
            app_commands.Choice(name="First Come First Served", value="first_come")
        ]
    )
    async def drop_create(
        self,
        interaction: Interaction,
        channel: discord.TextChannel = None,
        card_count: int = 3,
        drop_type: str = "fair_random"
    ):
        """Create a fair card drop"""
        
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ Only administrators can create drops!",
                ephemeral=True
            )
            return
        
        if not 1 <= card_count <= 10:
            await interaction.response.send_message(
                "❌ Card count must be between 1 and 10!",
                ephemeral=True
            )
            return
        
        channel = channel or interaction.channel
        
        # Check if channel allows drops
        if not self._can_drop_in_channel(interaction.guild.id, channel.id):
            await interaction.response.send_message(
                f"❌ Drops not allowed in {channel.mention}! Server cooldown active.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Generate cards for drop
            cards = await self._generate_drop_cards(card_count, drop_type)
            
            if not cards:
                await interaction.followup.send(
                    "❌ Failed to generate cards for drop. Supply constraints may prevent this drop.",
                    ephemeral=True
                )
                return
            
            # Create drop message
            drop_message = await self._create_drop_message(channel, cards, drop_type)
            
            # Store drop in database
            drop_id = self._store_drop(
                guild_id=interaction.guild.id,
                channel_id=channel.id,
                message_id=drop_message.id,
                cards=cards,
                drop_type=drop_type,
                created_by=interaction.user.id
            )
            
            # Add reaction for claiming
            await drop_message.add_reaction("🎁")
            
            # Start drop monitoring
            asyncio.create_task(self._monitor_drop(drop_id, drop_message, cards, drop_type))
            
            await interaction.followup.send(
                f"✅ Drop created in {channel.mention}!\n"
                f"**Drop ID:** {drop_id}\n"
                f"**Cards:** {len(cards)}\n"
                f"**Type:** {drop_type.replace('_', ' ').title()}\n"
                f"Users can react with 🎁 to claim!",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating drop: {e}")
            await interaction.followup.send(
                "❌ Failed to create drop. Check logs for details.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="drop_status",
        description="Check drop status and server cooldowns (Admin only)"
    )
    async def drop_status(self, interaction: Interaction):
        """Check drop system status"""
        
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ Only administrators can check drop status!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get server drop info
            server_info = self._get_server_drop_info(interaction.guild.id)
            
            # Get active drops
            active_drops = self._get_active_drops(interaction.guild.id)
            
            # Get supply status
            from services.season_supply_system import get_supply_status
            supply_status = get_supply_status()
            
            embed = discord.Embed(
                title=f"🎁 Drop Status - {interaction.guild.name}",
                color=discord.Color.blue()
            )
            
            # Server cooldown info
            if server_info['last_drop_time']:
                last_drop = datetime.fromisoformat(server_info['last_drop_time'])
                cooldown_end = last_drop + timedelta(minutes=server_info['cooldown_minutes'])
                time_until = cooldown_end - datetime.utcnow()
                
                if time_until.total_seconds() > 0:
                    cooldown_status = f"⏰ **Active** - {time_until.seconds//60}m {time_until.seconds%60}s remaining"
                else:
                    cooldown_status = "✅ **Ready** - No cooldown"
            else:
                cooldown_status = "✅ **Ready** - No drops yet"
            
            embed.add_field(
                name="🔄 Server Cooldown",
                value=cooldown_status,
                inline=False
            )
            
            embed.add_field(
                name="📊 Server Activity",
                value=f"Level: {server_info['activity_level']}/5\n"
                      f"Cooldown: {server_info['cooldown_minutes']} minutes",
                inline=True
            )
            
            embed.add_field(
                name="🎁 Active Drops",
                value=f"{len(active_drops)} drops running",
                inline=True
            )
            
            # Supply info
            drops_minted = supply_status['pack_contributions'].get('drops', 0)
            drops_remaining = supply_status['tier_status'].get('community', {}).get('remaining', 0)
            
            embed.add_field(
                name="📦 Season 1 Supply",
                value=f"Drops minted: {drops_minted:,}\n"
                      f"Community remaining: {drops_remaining:,}",
                inline=False
            )
            
            # Active drops list
            if active_drops:
                drop_list = []
                for drop in active_drops[:5]:  # Show max 5
                    drop_list.append(f"ID: {drop['drop_id'][:8]}... - {drop['card_count']} cards")
                
                embed.add_field(
                    name="🎁 Recent Drops",
                    value="\n".join(drop_list),
                    inline=False
                )
            
            embed.set_footer(text="Use /drop_create to create new drops")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error checking drop status: {e}")
            await interaction.followup.send(
                "❌ Failed to get drop status.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="drop_configure",
        description="Configure drop settings (Admin only)"
    )
    @app_commands.describe(
        cooldown_minutes="Cooldown between drops (5-60 minutes)",
        activity_level="Server activity level (1-5, affects cooldown)"
    )
    async def drop_configure(
        self,
        interaction: Interaction,
        cooldown_minutes: int = None,
        activity_level: int = None
    ):
        """Configure drop settings"""
        
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ Only administrators can configure drops!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            updates = []
            
            if cooldown_minutes is not None:
                if not 5 <= cooldown_minutes <= 60:
                    await interaction.followup.send(
                        "❌ Cooldown must be between 5 and 60 minutes!",
                        ephemeral=True
                    )
                    return
                
                self._update_server_cooldown(interaction.guild.id, cooldown_minutes)
                updates.append(f"Cooldown: {cooldown_minutes} minutes")
            
            if activity_level is not None:
                if not 1 <= activity_level <= 5:
                    await interaction.followup.send(
                        "❌ Activity level must be between 1 and 5!",
                        ephemeral=True
                    )
                    return
                
                self._update_server_activity(interaction.guild.id, activity_level)
                updates.append(f"Activity level: {activity_level}/5")
            
            if not updates:
                await interaction.followup.send(
                    "❌ No changes specified!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="⚙️ Drop Settings Updated",
                description="\n".join(updates),
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Current Settings",
                value=f"Cooldown: {self._get_server_cooldown(interaction.guild.id)} minutes\n"
                      f"Activity: {self._get_server_activity(interaction.guild.id)}/5",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error configuring drops: {e}")
            await interaction.followup.send(
                "❌ Failed to configure drops.",
                ephemeral=True
            )
    
    async def _generate_drop_cards(self, card_count: int, drop_type: str) -> list:
        """Generate cards for drop based on type"""
        try:
            # Use starter pack definition for drops (free-to-play)
            pack_def = get_pack_definition("starter")
            if not pack_def:
                return []
            
            # Generate canonical cards
            user_id = 0  # System user for drops
            payment_id = f"drop_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            cards = generate_canonical_cards(pack_def, user_id, payment_id)
            
            # Apply drop type logic
            if drop_type == "fair_random":
                # Return random cards from generated
                return random.sample(cards, min(card_count, len(cards)))
            
            elif drop_type == "weighted_rarity":
                # Try to get better rarity distribution
                rarity_weights = {
                    "community": 0.7,
                    "gold": 0.25,
                    "platinum": 0.04,
                    "legendary": 0.01
                }
                
                # Filter and select by weight
                filtered_cards = []
                for card in cards:
                    tier = card.rarity["tier"]
                    if random.random() < rarity_weights.get(tier, 0.7):
                        filtered_cards.append(card)
                
                return filtered_cards[:card_count] if filtered_cards else cards[:card_count]
            
            elif drop_type == "first_come":
                # Give best cards to first claimers
                # Sort by rarity (legendary first)
                tier_order = {"legendary": 0, "platinum": 1, "gold": 2, "community": 3}
                sorted_cards = sorted(cards, key=lambda c: tier_order.get(c.rarity["tier"], 3))
                return sorted_cards[:card_count]
            
            return cards[:card_count]
            
        except Exception as e:
            logger.error(f"Error generating drop cards: {e}")
            return []
    
    async def _create_drop_message(self, channel: discord.TextChannel, cards: list, drop_type: str) -> discord.Message:
        """Create drop message"""
        
        # Create embed
        embed = discord.Embed(
            title="🎁 CARD DROP! 🎁",
            description=f"React with 🎁 to claim a card!\n"
                      f"**Drop Type:** {drop_type.replace('_', ' ').title()}\n"
                      f"**Cards Available:** {len(cards)}",
            color=discord.Color.purple()
        )
        
        # Show card preview (first 3 cards)
        preview_text = []
        for i, card in enumerate(cards[:3]):
            tier_emoji = self._get_tier_emoji(card.rarity["tier"])
            preview_text.append(f"{i+1}. {tier_emoji} {card.artist['name']}")
        
        if len(cards) > 3:
            preview_text.append(f"... and {len(cards) - 3} more cards!")
        
        embed.add_field(
            name="🎴 Card Preview",
            value="\n".join(preview_text),
            inline=False
        )
        
        # Drop rules
        rules = []
        if drop_type == "fair_random":
            rules.append("🎲 Random winner from all reactors")
        elif drop_type == "weighted_rarity":
            rules.append("⚖️ Weighted rarity distribution")
        elif drop_type == "first_come":
            rules.append("⚡ First reaction gets best card")
        
        rules.extend([
            "⏰ 30 second claim window",
            "🎯 One card per person",
            "🔄 Server cooldown applies after drop"
        ])
        
        embed.add_field(
            name="📋 Drop Rules",
            value="\n".join(rules),
            inline=False
        )
        
        embed.set_footer(text="React with 🎁 to claim! • Drop ends in 30 seconds")
        embed.set_thumbnail(url="https://example.com/drop_animation.gif")
        
        return await channel.send(embed=embed)
    
    def _store_drop(self, guild_id: int, channel_id: int, message_id: int, cards: list, drop_type: str, created_by: int) -> str:
        """Store drop in database"""
        drop_id = f"drop_{guild_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        drop_data = {
            'drop_id': drop_id,
            'guild_id': guild_id,
            'channel_id': channel_id,
            'message_id': message_id,
            'card_count': len(cards),
            'cards_remaining': len(cards),
            'drop_type': drop_type,
            'created_by': created_by,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(seconds=30)).isoformat(),
            'status': 'active'
        }
        
        self.db.create_drop(drop_data)
        return drop_id
    
    async def _monitor_drop(self, drop_id: str, message: discord.Message, cards: list, drop_type: str):
        """Monitor drop and handle claims"""
        try:
            # Wait for claim window
            await asyncio.sleep(30)
            
            # Get message and reactions
            try:
                message = await message.channel.fetch_message(message.id)
            except discord.NotFound:
                logger.warning(f"Drop message not found: {message.id}")
                return
            
            # Get 🎁 reactions
            reaction = None
            for r in message.reactions:
                if r.emoji == "🎁":
                    reaction = r
                    break
            
            if not reaction:
                await self._handle_no_claims(drop_id, message)
                return
            
            # Get reactors (excluding bots)
            reactors = []
            async for user in reaction.users():
                if not user.bot:
                    reactors.append(user.id)
            
            if not reactors:
                await self._handle_no_claims(drop_id, message)
                return
            
            # Process claims based on drop type
            await self._process_claims(drop_id, message, reactors, cards, drop_type)
            
        except Exception as e:
            logger.error(f"Error monitoring drop {drop_id}: {e}")
    
    async def _process_claims(self, drop_id: str, message: discord.Message, reactors: list, cards: list, drop_type: str):
        """Process drop claims"""
        
        if drop_type == "first_come":
            # First come first served
            winners = reactors[:len(cards)]
        else:
            # Random selection
            winners = random.sample(reactors, min(len(cards), len(reactors)))
        
        # Award cards to winners
        awarded_cards = []
        for i, winner_id in enumerate(winners):
            if i < len(cards):
                card = cards[i]
                
                # Create card record for winner
                try:
                    card_record = Card.create(
                        user_id=winner_id,
                        artist_id=card.artist_id,
                        tier=card.rarity["tier"],
                        serial=card.identity["serial"],
                        purchase_id=drop_id
                    )
                    awarded_cards.append((winner_id, card))
                except Exception as e:
                    logger.error(f"Error awarding card to {winner_id}: {e}")
        
        # Update drop status
        self.db.update_drop_status(drop_id, 'completed', len(awarded_cards))
        
        # Update server cooldown
        guild_id = message.guild.id
        self._update_server_last_drop(guild_id)
        
        # Send results
        await self._send_drop_results(message, awarded_cards, drop_type)
    
    async def _handle_no_claims(self, drop_id: str, message: discord.Message):
        """Handle drop with no claims"""
        self.db.update_drop_status(drop_id, 'expired', 0)
        
        embed = discord.Embed(
            title="⏰ Drop Expired",
            description="No one claimed the drop! Cards returned to the void.",
            color=discord.Color.red()
        )
        
        await message.reply(embed=embed)
    
    async def _send_drop_results(self, message: discord.Message, awarded_cards: list, drop_type: str):
        """Send drop results"""
        
        if not awarded_cards:
            return
        
        embed = discord.Embed(
            title="🎉 Drop Complete!",
            description=f"**{len(awarded_cards)}** cards claimed!",
            color=discord.Color.green()
        )
        
        results_text = []
        for winner_id, card in awarded_cards:
            try:
                winner = message.guild.get_member(winner_id)
                winner_name = winner.display_name if winner else f"User {winner_id}"
                
                tier_emoji = self._get_tier_emoji(card.rarity["tier"])
                results_text.append(f"🎁 {tier_emoji} {card.artist['name']} → {winner_name}")
            except:
                results_text.append(f"🎁 Card awarded to User {winner_id}")
        
        embed.add_field(
            name="🏆 Winners",
            value="\n".join(results_text),
            inline=False
        )
        
        embed.set_footer(text="Server cooldown now active")
        
        await message.reply(embed=embed)
    
    def _get_tier_emoji(self, tier: str) -> str:
        """Get emoji for card tier"""
        tier_emojis = {
            "community": "⚪",
            "gold": "🟡",
            "platinum": "💎",
            "legendary": "👑"
        }
        return tier_emojis.get(tier, "⚪")
    
    def _can_drop_in_channel(self, guild_id: int, channel_id: int) -> bool:
        """Check if drop is allowed in channel"""
        # Check server cooldown
        server_info = self._get_server_drop_info(guild_id)
        
        if server_info['last_drop_time']:
            last_drop = datetime.fromisoformat(server_info['last_drop_time'])
            cooldown_end = last_drop + timedelta(minutes=server_info['cooldown_minutes'])
            
            if datetime.utcnow() < cooldown_end:
                return False
        
        return True
    
    def _get_server_drop_info(self, guild_id: int) -> dict:
        """Get server drop information"""
        return self.db.get_server_info(guild_id) or {
            'last_drop_time': None,
            'cooldown_minutes': 30,
            'activity_level': 3
        }
    
    def _update_server_cooldown(self, guild_id: int, cooldown_minutes: int):
        """Update server cooldown"""
        self.db.update_server_cooldown(guild_id, cooldown_minutes)
    
    def _update_server_activity(self, guild_id: int, activity_level: int):
        """Update server activity level"""
        self.db.update_server_activity(guild_id, activity_level)
    
    def _update_server_last_drop(self, guild_id: int):
        """Update server last drop time"""
        self.db.update_server_last_drop(guild_id, datetime.utcnow().isoformat())
    
    def _get_server_cooldown(self, guild_id: int) -> int:
        """Get server cooldown minutes"""
        server_info = self._get_server_drop_info(guild_id)
        return server_info.get('cooldown_minutes', 30)
    
    def _get_server_activity(self, guild_id: int) -> int:
        """Get server activity level"""
        server_info = self._get_server_drop_info(guild_id)
        return server_info.get('activity_level', 3)
    
    def _get_active_drops(self, guild_id: int) -> list:
        """Get active drops for server"""
        return self.db.get_active_drops(guild_id)

async def setup(bot):
    """Setup drop commands"""
    await bot.add_cog(DropCommands(bot))
