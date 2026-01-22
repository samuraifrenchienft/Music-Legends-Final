# cogs/packs.py
import discord
import random
from discord.ext import commands
from discord import Interaction, app_commands, ui
from typing import Dict, List
import json
import sqlite3
from card_economy import CardEconomyManager
from database import DatabaseManager

class PacksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)

    @app_commands.command(name="open_pack", description="Open a card pack")
    async def pack_command(self, interaction: Interaction, pack_type: str = "genre"):
        """Open a card pack"""
        valid_types = ["genre", "hero"]
        
        if pack_type not in valid_types:
            await interaction.response.send_message("❌ Invalid pack type! Use 'genre' or 'hero'", ephemeral=True)
            return
        
        # Check if user has enough currency (for now, make it free for testing)
        # Later: Add currency checks
        
        # Generate pack contents
        cards = self._generate_pack_cards(pack_type)
        
        # Create pack opening embed
        embed = discord.Embed(
            title=f"🎁 {pack_type.title()} Pack Opening!",
            description="Here's what you got:",
            color=discord.Color.gold()
        )
        
        # Add cards to embed
        for i, card in enumerate(cards, 1):
            tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['tier'], "⚪")
            embed.add_field(
                name=f"{tier_emoji} Card {i}: {card['artist_name']}",
                value=f"Tier: {card['tier'].title()}\nSerial: {card['serial_number']}\nGenre: {card['genre']}",
                inline=False
            )
        
        # Award cards to user
        for card in cards:
            self.economy._award_card_to_user(interaction.user.id, card)
        
        embed.set_footer(text="All cards have been added to your collection!")
        
        await interaction.response.send_message(embed=embed)

    def _generate_pack_cards(self, pack_type: str) -> List[Dict]:
        """Generate cards for a pack based on type"""
        cards = []
        artists = self.db.get_all_artists(limit=200)  # Get diverse artist pool
        
        if not artists:
            # Fallback: create mock artists
            artists = [
                {'name': 'Test Artist 1', 'genre': 'Pop', 'spotify_id': None},
                {'name': 'Test Artist 2', 'genre': 'Rock', 'spotify_id': None},
                {'name': 'Test Artist 3', 'genre': 'Hip-Hop', 'spotify_id': None},
            ]
        
        if pack_type == "genre":
            # Genre Pack: 5 cards, 1 guaranteed Gold+
            # Generate 4 random cards first
            for _ in range(4):
                artist = random.choice(artists)
                tier = self._roll_genre_pack_slot('other')
                card = self.economy.create_card(artist, tier, 'genre_pack')
                cards.append(card)
            
            # Generate guaranteed Gold+ card
            artist = random.choice(artists)
            tier = self._roll_genre_pack_slot('guaranteed')
            card = self.economy.create_card(artist, tier, 'genre_pack')
            cards.append(card)
            
        elif pack_type == "hero":
            # Hero Pack: 5 cards, 1 Hero slot (Platinum or Legendary)
            # Generate 4 supporting cards
            for _ in range(4):
                artist = random.choice(artists)
                tier = self._roll_hero_pack_slot('support')
                card = self.economy.create_card(artist, tier, 'hero_pack')
                cards.append(card)
            
            # Generate hero card
            artist = random.choice(artists)
            tier = self._roll_hero_pack_slot('hero')
            card = self.economy.create_card(artist, tier, 'hero_pack')
            cards.append(card)
        
        return cards

    def _roll_genre_pack_slot(self, slot_type: str) -> str:
        """Roll for a card tier in genre pack"""
        odds = self.economy.pack_odds['genre_pack']
        
        if slot_type == 'guaranteed':
            # Gold+ guaranteed: Gold 75%, Platinum 22%, Legendary 3%
            roll = random.random() * 100
            if roll < 3:
                return 'legendary'
            elif roll < 25:
                return 'platinum'
            else:
                return 'gold'
        else:
            # Other slots: Community 70%, Gold 25%, Platinum 5%
            roll = random.random() * 100
            if roll < 5:
                return 'platinum'
            elif roll < 30:
                return 'gold'
            else:
                return 'community'

    def _roll_hero_pack_slot(self, slot_type: str) -> str:
        """Roll for a card tier in hero pack"""
        odds = self.economy.pack_odds['hero_pack']
        
        if slot_type == 'hero':
            # Hero slot: Platinum 80%, Legendary 20%
            roll = random.random() * 100
            if roll < 20:
                return 'legendary'
            else:
                return 'platinum'
        else:
            # Support slots: Community 60%, Gold 30%, Platinum 10%
            roll = random.random() * 100
            if roll < 10:
                return 'platinum'
            elif roll < 40:
                return 'gold'
            else:
                return 'community'

    @app_commands.command(name="pack_info", description="View available pack types and odds")
    async def packs_info_command(self, interaction: Interaction):
        """Show information about available pack types"""
        embed = discord.Embed(
            title="🎁 Card Pack Information",
            description="Available pack types and their contents:",
            color=discord.Color.blue()
        )
        
        # Genre Pack Info
        genre_odds = self.economy.pack_odds['genre_pack']
        embed.add_field(
            name="🎵 Genre Pack",
            value="**Contents:** 5 cards from chosen genre\n"
                  "**Guaranteed:** 1 Gold+ card\n"
                  "**Gold+ Odds:**\n"
                  f"🟡 Gold: {genre_odds['guaranteed_gold_plus']['gold']}%\n"
                  f"🟣 Platinum: {genre_odds['guaranteed_gold_plus']['platinum']}%\n"
                  f"🔴 Legendary: {genre_odds['guaranteed_gold_plus']['legendary']}%\n\n"
                  "**Other Slots:**\n"
                  f"⚪ Community: {genre_odds['other_slots']['community']}%\n"
                  f"🟡 Gold: {genre_odds['other_slots']['gold']}%\n"
                  f"🟣 Platinum: {genre_odds['other_slots']['platinum']}%",
            inline=False
        )
        
        # Hero Pack Info
        hero_odds = self.economy.pack_odds['hero_pack']
        embed.add_field(
            name="🦸 Hero Pack",
            value="**Contents:** 5 cards with 1 Hero slot\n"
                  "**Hero Slot:**\n"
                  f"🟣 Platinum: {hero_odds['hero_slot']['platinum']}%\n"
                  f"🔴 Legendary: {hero_odds['hero_slot']['legendary']}%\n\n"
                  "**Support Slots:**\n"
                  f"⚪ Community: {hero_odds['support_slots']['community']}%\n"
                  f"🟡 Gold: {hero_odds['support_slots']['gold']}%\n"
                  f"🟣 Platinum: {hero_odds['support_slots']['platinum']}%",
            inline=False
        )
        
        embed.add_field(
            name="📋 How to Use",
            value="`/pack genre` - Open a Genre Pack\n"
                  "`/pack hero` - Open a Hero Pack\n"
                  "`/packs` - View this information",
            inline=False
        )
        
        embed.set_footer(text="Pack opening is free during testing phase!")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="open_multiple", description="Open multiple packs at once")
    async def open_multiple_command(self, interaction: Interaction, pack_type: str, quantity: int = 1):
        """Open multiple packs at once"""
        if quantity < 1 or quantity > 10:
            await interaction.response.send_message("❌ Quantity must be between 1 and 10!", ephemeral=True)
            return
        
        if pack_type not in ["genre", "hero"]:
            await interaction.response.send_message("❌ Invalid pack type! Use 'genre' or 'hero'", ephemeral=True)
            return
        
        # Generate all cards
        all_cards = []
        for _ in range(quantity):
            cards = self._generate_pack_cards(pack_type)
            all_cards.extend(cards)
        
        # Award all cards to user
        for card in all_cards:
            self.economy._award_card_to_user(interaction.user.id, card)
        
        # Create summary embed
        embed = discord.Embed(
            title=f"🎁 {quantity}x {pack_type.title()} Packs Opened!",
            description=f"You received {len(all_cards)} cards total:",
            color=discord.Color.gold()
        )
        
        # Count cards by tier
        tier_counts = {"community": 0, "gold": 0, "platinum": 0, "legendary": 0}
        for card in all_cards:
            tier_counts[card['tier']] += 1
        
        embed.add_field(
            name="📊 Summary",
            value=f"⚪ Community: {tier_counts['community']}\n"
                  f"🟡 Gold: {tier_counts['gold']}\n"
                  f"🟣 Platinum: {tier_counts['platinum']}\n"
                  f"🔴 Legendary: {tier_counts['legendary']}",
            inline=False
        )
        
        # Show notable cards (Gold+)
        notable_cards = [card for card in all_cards if card['tier'] in ['gold', 'platinum', 'legendary']]
        if notable_cards:
            notable_text = ""
            for card in notable_cards[:10]:  # Show up to 10 notable cards
                tier_emoji = {"gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['tier'], "⚪")
                notable_text += f"{tier_emoji} {card['artist_name']} ({card['serial_number']})\n"
            
            if len(notable_cards) > 10:
                notable_text += f"... and {len(notable_cards) - 10} more"
            
            embed.add_field(
                name="⭐ Notable Cards",
                value=notable_text,
                inline=False
            )
        
        embed.set_footer(text="All cards have been added to your collection!")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PacksCog(bot))
