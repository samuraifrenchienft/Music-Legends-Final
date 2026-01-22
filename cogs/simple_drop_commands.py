"""
Simple Drop Commands

Clean approach: Admin places cards, game logic handles the rest.
Special dev drops for testing before Season 1 is ready.
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
import asyncio
import random
from datetime import datetime, timedelta
import logging

from services.season_supply_system import can_mint_card, mint_card, get_serial_value_tier
from services.payment_service import generate_canonical_cards, get_pack_definition
from models.card import Card

logger = logging.getLogger(__name__)

class SimpleDropCommands(commands.Cog):
    """Simple drop commands for admins"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_drops = {}  # Track active drops
    
    def _is_admin(self, interaction: Interaction) -> bool:
        """Check if user is admin"""
        if not interaction.guild:
            return False
        
        return interaction.user.guild_permissions.administrator or \
               interaction.user.guild_permissions.manage_guild
    
    @app_commands.command(
        name="place_cards",
        description="Place cards in channel for community to claim (Admin only)"
    )
    @app_commands.describe(
        channel="Channel to place cards in (default: current)",
        card_count="Number of cards to place (1-5)"
    )
    async def place_cards(
        self,
        interaction: Interaction,
        channel: discord.TextChannel = None,
        card_count: int = 3
    ):
        """Place cards in channel - game logic handles the rest"""
        
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ Only administrators can place cards!",
                ephemeral=True
            )
            return
        
        if not 1 <= card_count <= 5:
            await interaction.response.send_message(
                "❌ Card count must be between 1 and 5!",
                ephemeral=True
            )
            return
        
        channel = channel or interaction.channel
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Generate cards for placement
            cards = await self._generate_cards_for_placement(card_count)
            
            if not cards:
                await interaction.followup.send(
                    "❌ Unable to generate cards. Supply constraints may prevent this.",
                    ephemeral=True
                )
                return
            
            # Create drop message
            drop_message = await self._create_drop_message(channel, cards)
            
            # Add reaction for claiming
            await drop_message.add_reaction("🎁")
            
            # Start drop monitoring (game logic takes over)
            asyncio.create_task(self._monitor_drop(drop_message, cards))
            
            await interaction.followup.send(
                f"✅ Cards placed in {channel.mention}!\n"
                f"**Cards:** {len(cards)}\n"
                f"Users can react with 🎁 to claim!",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error placing cards: {e}")
            await interaction.followup.send(
                "❌ Failed to place cards. Check logs for details.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="dev_drop",
        description="Special dev drop for testing (Dev only)"
    )
    @app_commands.describe(
        channel="Channel to drop in (default: current)",
        tier="Card tier to drop",
        card_count="Number of cards to drop (1-3)"
    )
    @app_commands.choices(
        tier=[
            app_commands.Choice(name="Community", value="community"),
            app_commands.Choice(name="Gold", value="gold"),
            app_commands.Choice(name="Platinum", value="platinum"),
            app_commands.Choice(name="Legendary", value="legendary")
        ]
    )
    async def dev_drop(
        self,
        interaction: Interaction,
        channel: discord.TextChannel = None,
        tier: str = "community",
        card_count: int = 1
    ):
        """Special dev drop for testing"""
        
        # Check if user is dev (you can customize this check)
        if not self._is_dev(interaction):
            await interaction.response.send_message(
                "❌ Only developers can use dev drops!",
                ephemeral=True
            )
            return
        
        if not 1 <= card_count <= 3:
            await interaction.response.send_message(
                "❌ Card count must be between 1 and 3!",
                ephemeral=True
            )
            return
        
        channel = channel or interaction.channel
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Generate specific tier cards
            cards = await self._generate_dev_cards(tier, card_count)
            
            if not cards:
                await interaction.followup.send(
                    "❌ Unable to generate dev cards.",
                    ephemeral=True
                )
                return
            
            # Create dev drop message
            drop_message = await self._create_dev_drop_message(channel, cards, tier)
            
            # Add reaction for claiming
            await drop_message.add_reaction("🚀")
            
            # Start drop monitoring
            asyncio.create_task(self._monitor_drop(drop_message, cards))
            
            await interaction.followup.send(
                f"🚀 Dev drop created in {channel.mention}!\n"
                f"**Tier:** {tier.title()}\n"
                f"**Cards:** {len(cards)}",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating dev drop: {e}")
            await interaction.followup.send(
                "❌ Failed to create dev drop.",
                ephemeral=True
            )
    
    async def _generate_cards_for_placement(self, card_count: int) -> list:
        """Generate cards for regular placement"""
        try:
            # Use starter pack definition
            pack_def = get_pack_definition("starter")
            if not pack_def:
                return []
            
            # Generate canonical cards
            user_id = 0  # System user
            payment_id = f"place_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            cards = generate_canonical_cards(pack_def, user_id, payment_id)
            
            # Return requested number
            return cards[:card_count]
            
        except Exception as e:
            logger.error(f"Error generating placement cards: {e}")
            return []
    
    async def _generate_dev_cards(self, tier: str, card_count: int) -> list:
        """Generate specific tier cards for dev drops"""
        try:
            # For dev drops, we can bypass some restrictions
            # but still respect basic supply constraints
            
            cards = []
            
            for i in range(card_count):
                # Check if we can mint this tier
                mint_check = can_mint_card(tier, f"dev_artist_{i}", "dev_drops")
                
                if not mint_check["can_mint"]:
                    logger.warning(f"Cannot mint {tier} dev card: {mint_check['reason']}")
                    continue
                
                # Record the mint
                mint_result = mint_card(tier, f"dev_artist_{i}", "dev_drops")
                
                if not mint_result["success"]:
                    logger.error(f"Failed to mint dev card: {mint_result}")
                    continue
                
                # Create a simple dev card
                card_data = {
                    "card_id": f"dev_{tier}_{i}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "artist": {
                        "artist_id": f"dev_artist_{i}",
                        "name": f"Dev Artist {i+1}",
                        "primary_genre": "Electronic",
                        "image_url": "https://via.placeholder.com/300x300/000000/FFFFFF?text=DEV"
                    },
                    "rarity": {
                        "tier": tier,
                        "print_cap": 1000 if tier == "community" else 100
                    },
                    "identity": {
                        "serial": f"DEV-S1-{tier[0].upper()}-{mint_result['serial_number']:04d}",
                        "season": 1,
                        "card_id": f"dev_{tier}_{i}"
                    }
                }
                
                cards.append(card_data)
            
            return cards
            
        except Exception as e:
            logger.error(f"Error generating dev cards: {e}")
            return []
    
    async def _create_drop_message(self, channel: discord.TextChannel, cards: list) -> discord.Message:
        """Create regular drop message"""
        
        embed = discord.Embed(
            title="🎁 Cards Available!",
            description=f"React with 🎁 to claim a card!\n"
                      f"**Cards Available:** {len(cards)}",
            color=discord.Color.purple()
        )
        
        # Show card preview
        preview_text = []
        for i, card in enumerate(cards):
            tier_emoji = self._get_tier_emoji(card.rarity["tier"])
            preview_text.append(f"{i+1}. {tier_emoji} {card.artist['name']}")
        
        embed.add_field(
            name="🎴 Available Cards",
            value="\n".join(preview_text),
            inline=False
        )
        
        embed.add_field(
            name="📋 How to Claim",
            value="React with 🎁 to claim a card!\n"
                  "First come, first served!",
            inline=False
        )
        
        embed.set_footer(text="React with 🎁 to claim!")
        
        return await channel.send(embed=embed)
    
    async def _create_dev_drop_message(self, channel: discord.TextChannel, cards: list, tier: str) -> discord.Message:
        """Create dev drop message"""
        
        embed = discord.Embed(
            title="🚀 Dev Drop! 🚀",
            description=f"Special dev drop for testing!\n"
                      f"**Tier:** {tier.title()}\n"
                      f"**Cards:** {len(cards)}",
            color=discord.Color.orange()
        )
        
        # Show card preview
        preview_text = []
        for i, card in enumerate(cards):
            tier_emoji = self._get_tier_emoji(card.rarity["tier"])
            preview_text.append(f"{i+1}. {tier_emoji} {card.artist['name']}")
        
        embed.add_field(
            name="🎴 Dev Cards",
            value="\n".join(preview_text),
            inline=False
        )
        
        embed.add_field(
            name="🧪 Testing Info",
            value="This is a developer drop for testing purposes.\n"
                  "React with 🚀 to claim!",
            inline=False
        )
        
        embed.set_footer(text="🚀 React with 🚀 to claim!")
        
        return await channel.send(embed=embed)
    
    async def _monitor_drop(self, message: discord.Message, cards: list):
        """Monitor drop and handle claims - game logic takes over"""
        try:
            # Wait for reactions
            await asyncio.sleep(30)
            
            # Get message and reactions
            try:
                message = await message.channel.fetch_message(message.id)
            except discord.NotFound:
                return
            
            # Find the right reaction
            reaction = None
            for r in message.reactions:
                if r.emoji in ["🎁", "🚀"]:
                    reaction = r
                    break
            
            if not reaction:
                await self._handle_no_claims(message)
                return
            
            # Get reactors (excluding bots)
            reactors = []
            async for user in reaction.users():
                if not user.bot:
                    reactors.append(user.id)
            
            if not reactors:
                await self._handle_no_claims(message)
                return
            
            # Award cards (first come, first served)
            awarded_cards = []
            for i, winner_id in enumerate(reactors):
                if i < len(cards):
                    card = cards[i]
                    
                    try:
                        # Create card record for winner
                        card_record = Card.create(
                            user_id=winner_id,
                            artist_id=card.artist_id,
                            tier=card.rarity["tier"],
                            serial=card.identity["serial"],
                            purchase_id=f"drop_{message.id}"
                        )
                        awarded_cards.append((winner_id, card))
                    except Exception as e:
                        logger.error(f"Error awarding card to {winner_id}: {e}")
            
            # Send results
            await self._send_claim_results(message, awarded_cards)
            
        except Exception as e:
            logger.error(f"Error monitoring drop: {e}")
    
    async def _handle_no_claims(self, message: discord.Message):
        """Handle drop with no claims"""
        embed = discord.Embed(
            title="⏰ No Claims",
            description="No one claimed the cards!",
            color=discord.Color.red()
        )
        
        await message.reply(embed=embed)
    
    async def _send_claim_results(self, message: discord.Message, awarded_cards: list):
        """Send claim results"""
        
        if not awarded_cards:
            return
        
        embed = discord.Embed(
            title="🎉 Cards Claimed!",
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
            name="🏆 Claimed By",
            value="\n".join(results_text),
            inline=False
        )
        
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
    
    def _is_dev(self, interaction: Interaction) -> bool:
        """Check if user is developer (customize this)"""
        # You can customize this check based on your needs
        # For now, just check if they're admin
        return self._is_admin(interaction)
        
        # Or check specific user IDs:
        # dev_ids = [123456789, 987654321]  # Your Discord user IDs
        # return interaction.user.id in dev_ids

async def setup(bot):
    """Setup simple drop commands"""
    await bot.add_cog(SimpleDropCommands(bot))
