# cogs/simple_pack_creation.py - Simple artist name-based pack creation
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3
from database import DatabaseManager
import uuid
import random

class SimplePackCreation(commands.Cog):
    """Simple pack creation using artist names - no YouTube API required"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
    
    async def cog_load(self):
        """Initialize database when cog loads"""
        print("🔥 SimplePackCreation cog is loading!")
        
        try:
            self.db = DatabaseManager()
            print("✅ Database initialized for simple pack creation")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            self.db = None
    
    @app_commands.command(name="create_pack", description="Create a pack using artist name")
    @app_commands.describe(artist_name="Name of the main artist", pack_type="Type of pack to create")
    @app_commands.choices(pack_type=[
        discord.app_commands.Choice(name="Community Pack", value="community"),
        discord.app_commands.Choice(name="Gold Pack", value="gold"),
        discord.app_commands.Choice(name="Platinum Pack", value="platinum")
    ])
    async def create_pack(self, interaction: Interaction, artist_name: str, pack_type: str = "community"):
        """Create a pack using just the artist name"""
        
        await interaction.response.defer(ephemeral=True)
        
        if not self.db:
            await interaction.followup.send("❌ Database not available", ephemeral=True)
            return
        
        # Check permissions for different pack types
        is_dev = self.is_dev(interaction.user.id)
        
        if pack_type == "platinum" and not is_dev:
            await interaction.followup.send("❌ Platinum packs are developer only!", ephemeral=True)
            return
        
        # Create the pack
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        
        # Generate cards based on artist
        cards = self.generate_cards_from_artist(artist_name, pack_type)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert pack
                price = {"community": 0, "gold": 9.99, "platinum": 19.99}[pack_type]
                
                cursor.execute("""
                    INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    interaction.user.id,
                    f"{artist_name.title()} {pack_type.title()} Pack",
                    f"Featured: {artist_name.title()} + {len(cards)-1} related cards",
                    len(cards),
                    "live",
                    str(cards),  # Store as Python dict string
                    price
                ))
                
                # Add to user inventory
                cursor.execute("""
                    INSERT INTO user_packs (user_id, pack_id, acquired_at)
                    VALUES (?, ?, datetime('now'))
                """, (interaction.user.id, pack_id))
                
                # List in marketplace if paid pack
                if price > 0:
                    cursor.execute("""
                        INSERT INTO marketplace (pack_id, price, stock)
                        VALUES (?, ?, ?)
                    """, (pack_id, price, "unlimited"))
                
                conn.commit()
                print(f"✅ {pack_type.title()} pack {pack_id} created for {artist_name}")
        
        except Exception as e:
            print(f"❌ Database error: {e}")
            await interaction.followup.send(f"❌ Database error: {e}", ephemeral=True)
            return
        
        # Send confirmation
        embed = discord.Embed(
            title=f"✅ {pack_type.title()} Pack Created!",
            description=f"**{artist_name.title()}** pack has been created.",
            color=discord.Color.green()
        )
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        embed.add_field(name="Cards", value=f"{len(cards)} cards", inline=False)
        embed.add_field(name="Price", value=f"${price}" if price > 0 else "Free", inline=False)
        
        # Show card preview
        rarity_emojis = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}
        for i, card in enumerate(cards[:3], 1):  # Show first 3 cards
            rarity = card.get('rarity', 'community')
            emoji = rarity_emojis.get(rarity, "🎴")
            embed.add_field(
                name=f"{emoji} Card {i}",
                value=f"{card.get('name', 'Unknown')}\nRarity: {rarity.title()}",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def generate_cards_from_artist(self, artist_name: str, pack_type: str) -> list:
        """Generate cards based on artist name and pack type"""
        cards = []
        
        # Main artist card (always highest rarity for pack type)
        main_rarity = {"community": "gold", "gold": "platinum", "platinum": "legendary"}[pack_type]
        cards.append({
            "name": artist_name,
            "rarity": main_rarity,
            "impact": random.randint(70, 95),
            "skill": random.randint(70, 95),
            "longevity": random.randint(70, 95),
            "culture": random.randint(70, 95),
            "hype": random.randint(70, 95)
        })
        
        # Generate supporting cards
        supporting_rarities = {
            "community": ["community", "community", "community", "community"],
            "gold": ["gold", "community", "community", "community"],
            "platinum": ["platinum", "gold", "gold", "community"]
        }
        
        for rarity in supporting_rarities[pack_type]:
            # Generate related artist names
            related_names = [
                f"{artist_name} Remix",
                f"{artist_name} Collab",
                f"{artist_name} Live",
                f"{artist_name} Acoustic"
            ]
            
            cards.append({
                "name": random.choice(related_names),
                "rarity": rarity,
                "impact": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "skill": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "longevity": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "culture": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "hype": random.randint(50, 80) if rarity == "community" else random.randint(60, 85)
            })
        
        return cards
    
    def is_dev(self, user_id: int) -> bool:
        """Check if user is a developer"""
        dev_ids = os.getenv("DEV_USER_IDS", "").split(",") if os.getenv("DEV_USER_IDS") else []
        return str(user_id) in dev_ids or user_id == 123456789  # Add your Discord ID here

async def setup(bot):
    cog = SimplePackCreation(bot)
    await bot.add_cog(cog)
    print(f"🔥 SimplePackCreation cog loaded with create_pack command")
