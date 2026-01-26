"""
Card Creation Commands
Provides user-facing commands to create individual cards
"""
import discord
import os
from discord.ext import commands
from discord import app_commands, Interaction
import random
from database import DatabaseManager

class CardCreation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    @app_commands.command(name="create_card", description="Create a new card")
    @app_commands.describe(
        card_name="Name of the card (artist name)",
        rarity="Rarity tier: Common, Rare, Epic, or Legendary"
    )
    async def create_card(self, interaction: Interaction, card_name: str, rarity: str = "Common"):
        """Create a new card with specified name and rarity"""
        
        await interaction.response.defer()
        
        try:
            # Validate rarity
            valid_rarities = ["Common", "Rare", "Epic", "Legendary"]
            if rarity not in valid_rarities:
                await interaction.followup.send(
                    f"❌ Invalid rarity! Choose from: {', '.join(valid_rarities)}",
                    ephemeral=True
                )
                return
            
            # Generate card ID
            import uuid
            card_id = str(uuid.uuid4())[:8].upper()
            
            # Generate stats based on rarity
            rarity_stats = {
                "Common": {"impact": 20, "skill": 20, "longevity": 20, "culture": 20, "hype": 20},
                "Rare": {"impact": 40, "skill": 40, "longevity": 40, "culture": 40, "hype": 40},
                "Epic": {"impact": 60, "skill": 60, "longevity": 60, "culture": 60, "hype": 60},
                "Legendary": {"impact": 80, "skill": 80, "longevity": 80, "culture": 80, "hype": 80}
            }
            
            stats = rarity_stats[rarity]
            
            # Create card data
            card_data = {
                "card_id": f"ART-{card_id}",
                "name": card_name,
                "title": "Artist",
                "rarity": rarity,
                "era": "2024",
                "variant": "Classic",
                "impact": stats["impact"],
                "skill": stats["skill"], 
                "longevity": stats["longevity"],
                "culture": stats["culture"],
                "hype": stats["hype"],
                "image_url": None,
                "spotify_url": None,
                "youtube_url": None,
                "type": "artist"
            }
            
            # Store card in database
            self.db.add_card_to_master(card_data)
            
            # Create embed for the new card
            rarity_colors = {
                "Common": discord.Color.grey(),
                "Rare": discord.Color.blue(),
                "Epic": discord.Color.purple(),
                "Legendary": discord.Color.gold()
            }
            
            rarity_emoji = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐"}
            
            embed = discord.Embed(
                title=f"✅ Card Created!",
                description=f"Successfully created **{card_name}** card",
                color=rarity_colors[rarity]
            )
            
            embed.add_field(
                name="Card Details",
                value=f"• **ID**: {card_data['card_id']}\n"
                      f"• **Name**: {card_name}\n"
                      f"• **Rarity**: {rarity_emoji[rarity]} {rarity}\n"
                      f"• **Type**: Artist Card\n"
                      f"• **Era**: 2024",
                inline=False
            )
            
            embed.add_field(
                name="Stats",
                value=f"💪 Impact: {stats['impact']}\n"
                      f"🎯 Skill: {stats['skill']}\n"
                      f"⏱️ Longevity: {stats['longevity']}\n"
                      f"🌍 Culture: {stats['culture']}\n"
                      f"🔥 Hype: {stats['hype']}",
                inline=True
            )
            
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating card: {e}", ephemeral=True)
    
    @app_commands.command(name="create_random_card", description="Create a random card")
    async def create_random_card(self, interaction: Interaction):
        """Create a random card with random attributes"""
        
        await interaction.response.defer()
        
        try:
            # Random artist names
            artist_names = [
                "Kendrick Lamar", "Drake", "Taylor Swift", "The Weeknd", "Billie Eilish",
                "Travis Scott", "Ariana Grande", "Post Malone", "Doja Cat", "Bad Bunny",
                "Tyler, The Creator", "Frank Ocean", "J. Cole", "SZA", "Bruno Mars"
            ]
            
            # Random rarities with weighted chances
            rarities = ["Common"] * 50 + ["Rare"] * 30 + ["Epic"] * 15 + ["Legendary"] * 5
            rarity = random.choice(rarities)
            card_name = random.choice(artist_names)
            
            # Generate card ID
            import uuid
            card_id = str(uuid.uuid4())[:8].upper()
            
            # Generate stats based on rarity with some randomness
            base_stats = {
                "Common": 20, "Rare": 40, "Epic": 60, "Legendary": 80
            }
            
            base = base_stats[rarity]
            stats = {
                "impact": base + random.randint(-5, 10),
                "skill": base + random.randint(-5, 10),
                "longevity": base + random.randint(-5, 10),
                "culture": base + random.randint(-5, 10),
                "hype": base + random.randint(-5, 10)
            }
            
            # Create card data
            card_data = {
                "card_id": f"ART-{card_id}",
                "name": card_name,
                "title": "Artist",
                "rarity": rarity,
                "era": "2024",
                "variant": "Classic",
                "impact": max(1, stats["impact"]),
                "skill": max(1, stats["skill"]),
                "longevity": max(1, stats["longevity"]),
                "culture": max(1, stats["culture"]),
                "hype": max(1, stats["hype"]),
                "image_url": None,
                "spotify_url": None,
                "youtube_url": None,
                "type": "artist"
            }
            
            # Store card in database
            self.db.add_card_to_master(card_data)
            
            # Create embed
            rarity_colors = {
                "Common": discord.Color.grey(),
                "Rare": discord.Color.blue(),
                "Epic": discord.Color.purple(),
                "Legendary": discord.Color.gold()
            }
            
            rarity_emoji = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐"}
            
            embed = discord.Embed(
                title=f"🎲 Random Card Created!",
                description=f"Randomly created **{card_name}** card",
                color=rarity_colors[rarity]
            )
            
            embed.add_field(
                name="Card Details",
                value=f"• **ID**: {card_data['card_id']}\n"
                      f"• **Name**: {card_name}\n"
                      f"• **Rarity**: {rarity_emoji[rarity]} {rarity}\n"
                      f"• **Type**: Artist Card",
                inline=False
            )
            
            embed.add_field(
                name="Stats",
                value=f"💪 Impact: {max(1, stats['impact'])}\n"
                      f"🎯 Skill: {max(1, stats['skill'])}\n"
                      f"⏱️ Longevity: {max(1, stats['longevity'])}\n"
                      f"🌍 Culture: {max(1, stats['culture'])}\n"
                      f"🔥 Hype: {max(1, stats['hype'])}",
                inline=True
            )
            
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating random card: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CardCreation(bot))
    print("✅ CardCreation cog loaded - /create_card and /create_random_card available")
