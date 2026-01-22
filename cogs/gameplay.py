# cogs/gameplay.py
import discord
import asyncio
import time
from discord.ext import commands
from discord import Interaction, app_commands, ui
from typing import Dict, List
import random
from card_economy import CardEconomyManager
from database import DatabaseManager

class GameplayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
        self.economy.initialize_economy_tables()
        
        # Store active drop messages for reaction handling
        self.active_drop_messages = {}  # message_id -> drop_data

    @app_commands.command(name="drop", description="Spawn a card drop in this channel")
    async def drop_command(self, interaction: Interaction):
        """Create a card drop in the current channel"""
        # Check if user can drop (cooldown)
        if not self.economy._can_drop(interaction.guild.id):
            await interaction.response.send_message("⏰ Drop is on cooldown for this server!", ephemeral=True)
            return
        
        # Create the drop
        drop_result = self.economy.create_drop(
            interaction.channel.id, 
            interaction.guild.id, 
            interaction.user.id
        )
        
        if not drop_result['success']:
            await interaction.response.send_message(f"❌ {drop_result['error']}", ephemeral=True)
            return
        
        # Create drop embed
        embed = discord.Embed(
            title="🎴 CARD DROP! 🎴",
            description=f"React with the number to grab the card you want!\n\nDrop expires in 5 minutes!",
            color=discord.Color.gold()
        )
        
        # Add cards to embed
        cards = drop_result['cards']
        for i, card in enumerate(cards, 1):
            tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['tier'], "⚪")
            embed.add_field(
                name=f"{tier_emoji} Card {i}: {card['artist_name']}",
                value=f"Tier: {card['tier'].title()}\nSerial: {card['serial_number']}\nReact with {i} to grab!",
                inline=False
            )
        
        embed.set_footer(text=f"Drop initiated by {interaction.user.display_name}")
        embed.set_thumbnail(url="https://i.imgur.com/your_drop_icon.png")
        
        # Send drop message
        message = await interaction.channel.send(embed=embed)
        
        # Add reactions
        for i in range(1, len(cards) + 1):
            await message.add_reaction(f"{i}\u20e3")  # 1️⃣, 2️⃣, 3️⃣
        
        # Store for reaction handling
        self.active_drop_messages[message.id] = {
            'drop_id': drop_result['drop_id'],
            'channel_id': interaction.channel.id,
            'cards': cards,
            'expires_at': drop_result['expires_at']
        }
        
        await interaction.response.send_message("✨ Drop created! React quickly to grab a card!", ephemeral=True)

    @app_commands.command(name="grab", description="Attempt to grab a card from an active drop")
    async def grab_command(self, interaction: Interaction, card_number: int):
        """Manual grab command (backup for reactions)"""
        result = self.economy.claim_drop(interaction.channel.id, interaction.user.id, card_number)
        
        if result['success']:
            card = result['card']
            tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['tier'], "⚪")
            
            embed = discord.Embed(
                title=f"{tier_emoji} CARD GRABBED! {tier_emoji}",
                description=f"You successfully grabbed {card['artist_name']}!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Card Details",
                value=f"Artist: {card['artist_name']}\n"
                      f"Tier: {card['tier'].title()}\n"
                      f"Serial: {card['serial_number']}\n"
                      f"Quality: {card['quality'].title()}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)

    @app_commands.command(name="my_collection", description="View your card collection")
    async def my_collection_command(self, interaction: Interaction, user: discord.User = None):
        """View user's card collection"""
        target_user = user or interaction.user
        
        collection = self.economy.get_user_collection(target_user.id)
        
        embed = discord.Embed(
            title=f"🎴 {target_user.display_name}'s Collection",
            description=f"Total Cards: {collection['total_cards']}",
            color=discord.Color.blue()
        )
        
        if collection['inventory']:
            inventory = collection['inventory']
            embed.add_field(
                name="💰 Currency",
                value=f"Gold: {inventory[1] or 0}\n"
                      f"Dust: {inventory[2] or 0}\n"
                      f"Tickets: {inventory[3] or 0}\n"
                      f"Gems: {inventory[4] or 0}",
                inline=True
            )
        
        # Group cards by tier
        tier_counts = {"community": 0, "gold": 0, "platinum": 0, "legendary": 0}
        for card in collection['cards']:
            tier_counts[card[3]] += 1  # tier is at index 3
        
        embed.add_field(
            name="📊 Collection by Tier",
            value=f"⚪ Community: {tier_counts['community']}\n"
                  f"🟡 Gold: {tier_counts['gold']}\n"
                  f"🟣 Platinum: {tier_counts['platinum']}\n"
                  f"🔴 Legendary: {tier_counts['legendary']}",
            inline=True
        )
        
        # Show recent cards (up to 10)
        if collection['cards']:
            recent_text = ""
            for card in collection['cards'][:10]:
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
                recent_text += f"{tier_emoji} {card[2]} ({card[3]})\n"  # artist_name, tier
            
            embed.add_field(
                name="🆕 Recent Cards",
                value=recent_text,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="view", description="View details of a specific card")
    async def view_command(self, interaction: Interaction, serial_number: str):
        """View detailed information about a specific card"""
        # Find card by serial number
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cards WHERE serial_number = ? AND owner_user_id = ?
            """, (serial_number, interaction.user.id))
            card = cursor.fetchone()
        
        if not card:
            await interaction.response.send_message("❌ Card not found in your collection!", ephemeral=True)
            return
        
        # Create detailed card embed
        tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
        tier_color = {"community": discord.Color.light_grey, "gold": discord.Color.gold(), 
                     "platinum": discord.Color.purple(), "legendary": discord.Color.red()}.get(card[3], discord.Color.blue())
        
        embed = discord.Embed(
            title=f"{tier_emoji} {card[2]} - {card[3].title()} Card",
            description=f"Serial Number: {card[4]}",
            color=tier_color
        )
        
        embed.add_field(
            name="📋 Card Information",
            value=f"Artist: {card[2]}\n"
                  f"Genre: {card[5] or 'Unknown'}\n"
                  f"Tier: {card[3].title()}\n"
                  f"Print #: {card[6]}\n"
                  f"Quality: {card[7].title()}\n"
                  f"Source: {card[8]}",
            inline=False
        )
        
        embed.add_field(
            name="📅 Acquisition",
            value=f"Date: {card[10][:10]}\n"  # acquisition_date
                  f"Owner History: {card[9] or 'None'}",
            inline=False
        )
        
        # Add card stats if available
        if card[12]:  # stats
            stats = json.loads(card[12])
            if stats:
                stats_text = ""
                for stat, value in stats.items():
                    stats_text += f"{stat.replace('_', ' ').title()}: {value}\n"
                embed.add_field(name="📊 Stats", value=stats_text, inline=False)
        
        embed.set_thumbnail(url=f"https://i.imgur.com/card_{card[3]}.png")
        embed.set_footer(text=f"Card ID: {card[0]}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lookup", description="Lookup cards by artist name")
    async def lookup_command(self, interaction: Interaction, artist_name: str):
        """Lookup all cards for a specific artist"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cards WHERE artist_name LIKE ? 
                ORDER BY tier DESC, print_number ASC
            """, (f"%{artist_name}%",))
            cards = cursor.fetchall()
        
        if not cards:
            await interaction.response.send_message(f"❌ No cards found for '{artist_name}'", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🔍 Artist Lookup: {artist_name}",
            description=f"Found {len(cards)} cards",
            color=discord.Color.blue()
        )
        
        # Group by tier
        tier_groups = {"community": [], "gold": [], "platinum": [], "legendary": []}
        for card in cards:
            tier_groups[card[3]].append(card)
        
        for tier, tier_cards in tier_groups.items():
            if tier_cards:
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(tier, "⚪")
                card_list = ""
                for card in tier_cards[:10]:  # Limit to 10 per tier
                    owner = f"<@{card[9]}>" if card[9] else "Unclaimed"
                    card_list += f"#{card[6]} - {owner}\n"
                
                if len(tier_cards) > 10:
                    card_list += f"... and {len(tier_cards) - 10} more"
                
                embed.add_field(
                    name=f"{tier_emoji} {tier.title()} ({len(tier_cards)})",
                    value=card_list or "None",
                    inline=False
                )
        
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
        view = CardUpgradeView(self.economy, interaction.user.id, upgrade_type)
        
        embed = discord.Embed(
            title="⬆️ Card Upgrade",
            description=f"Select {self.economy.upgrade_costs[upgrade_type]} cards to upgrade",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="daily", description="Claim daily rewards")
    async def daily_command(self, interaction: Interaction):
        """Claim daily rewards"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_daily FROM user_inventory WHERE user_id = ?
            """, (interaction.user.id,))
            result = cursor.fetchone()
            
            today = datetime.now().date()
            
            if result and result[0]:
                last_daily = datetime.fromisoformat(result[0]).date()
                if last_daily >= today:
                    await interaction.response.send_message("⏰ You already claimed your daily reward!", ephemeral=True)
                    return
            
            # Give daily rewards
            gold_reward = random.randint(10, 50)
            dust_reward = random.randint(5, 25)
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_inventory 
                (user_id, gold, dust, last_daily)
                VALUES (?, 
                    COALESCE((SELECT gold FROM user_inventory WHERE user_id = ?), 0) + ?,
                    COALESCE((SELECT dust FROM user_inventory WHERE user_id = ?), 0) + ?,
                    CURRENT_TIMESTAMP
                )
            """, (interaction.user.id, interaction.user.id, gold_reward, interaction.user.id, dust_reward))
            
            conn.commit()
        
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"Here are your daily rewards:",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Rewards",
            value=f"Gold: {gold_reward}\nDust: {dust_reward}",
            inline=False
        )
        
        embed.set_footer(text="Come back tomorrow for more rewards!")
        
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reactions for card drops"""
        # Check if this is a reaction to a drop message
        if payload.message_id not in self.active_drop_messages:
            return
        
        # Only handle number reactions (1️⃣, 2️⃣, 3️⃣)
        if payload.emoji.name not in ['1️⃣', '2️⃣', '3️⃣']:
            return
        
        drop_data = self.active_drop_messages[payload.message_id]
        
        # Convert emoji to number
        card_number = int(payload.emoji.name[0])
        
        # Try to claim the card
        result = self.economy.claim_drop(drop_data['channel_id'], payload.user_id, card_number)
        
        if result['success']:
            card = result['card']
            tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['tier'], "⚪")
            
            # Send success message
            channel = self.bot.get_channel(drop_data['channel_id'])
            if channel:
                embed = discord.Embed(
                    title=f"{tier_emoji} CARD GRABBED! {tier_emoji}",
                    description=f"<@{payload.user_id}> successfully grabbed {card['artist_name']}!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Card Details",
                    value=f"Artist: {card['artist_name']}\n"
                          f"Tier: {card['tier'].title()}\n"
                          f"Serial: {card['serial_number']}",
                    inline=False
                )
                
                await channel.send(embed=embed)
            
            # Remove from active drops
            del self.active_drop_messages[payload.message_id]
        
        # Remove the reaction
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji, payload.user)

class CardUpgradeView(ui.View):
    def __init__(self, economy_manager: CardEconomyManager, user_id: int, upgrade_type: str):
        super().__init__(timeout=180)  # 3 minutes
        self.economy = economy_manager
        self.user_id = user_id
        self.upgrade_type = upgrade_type
        self.selected_cards = []
        
        required = economy_manager.upgrade_costs[upgrade_type]
        self.add_item(ui.Button(
            label=f"Upgrade ({required}/{required} selected)",
            style=discord.ButtonStyle.primary,
            disabled=True,
            custom_id="upgrade_button"
        ))
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id

# Import sqlite3 for the view command
import sqlite3
import json
from datetime import datetime

async def setup(bot):
    await bot.add_cog(GameplayCog(bot))
