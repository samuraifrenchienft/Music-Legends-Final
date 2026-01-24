# cogs/pack_creation_simple.py - Simple pack creation without YouTube API dependency
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3
from database import DatabaseManager
import uuid
import json

class PackCreationSimple(commands.Cog):
    """Simple pack creation system - no YouTube API required"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
    
    async def cog_load(self):
        """Initialize database when cog loads"""
        print("🔥 PackCreationSimple cog is loading!")
        
        try:
            self.db = DatabaseManager()
            print("✅ Database initialized for simple pack creation")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            print("⚠️ Pack creation will be disabled but bot will continue running")
            self.db = None
    
    @app_commands.command(name="create_simple_pack", description="Create a simple test pack")
    @app_commands.describe(pack_name="Name for your pack")
    async def create_simple_pack(self, interaction: Interaction, pack_name: str):
        """Create a simple test pack"""
        
        await interaction.response.defer(ephemeral=True)
        
        if not self.db:
            await interaction.followup.send("❌ Database not available - pack creation temporarily disabled", ephemeral=True)
            return
        
        # Create simple test cards
        cards = [
            {
                "name": "Test Card 1",
                "rarity": "Common",
                "impact": 50,
                "skill": 50,
                "longevity": 50,
                "culture": 50,
                "hype": 50
            },
            {
                "name": "Test Card 2", 
                "rarity": "Rare",
                "impact": 60,
                "skill": 60,
                "longevity": 60,
                "culture": 60,
                "hype": 60
            },
            {
                "name": "Test Card 3",
                "rarity": "Epic",
                "impact": 70,
                "skill": 70,
                "longevity": 70,
                "culture": 70,
                "hype": 70
            }
        ]
        
        # Database transaction
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        cards_json = json.dumps(cards)
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert pack
                cursor.execute("""
                    INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    interaction.user.id,
                    pack_name,
                    "Simple test pack",
                    len(cards),
                    "live",
                    cards_json,
                    4.99
                ))
                
                # Add to inventory
                cursor.execute("""
                    INSERT INTO user_packs (user_id, pack_id, acquired_at)
                    VALUES (?, ?, datetime('now'))
                """, (interaction.user.id, pack_id))
                
                # List in marketplace
                cursor.execute("""
                    INSERT INTO marketplace (pack_id, price, stock)
                    VALUES (?, ?, ?)
                """, (pack_id, 4.99, "unlimited"))
                
                conn.commit()
                print(f"✅ Simple pack {pack_id} created successfully")
        
        except Exception as e:
            print(f"❌ Database error: {e}")
            await interaction.followup.send(f"❌ Database error: {e}", ephemeral=True)
            return
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Simple Pack Created!",
            description=f"**{pack_name}** has been created and added to your inventory.",
            color=discord.Color.green()
        )
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        embed.add_field(name="Cards", value=f"{len(cards)} test cards", inline=False)
        embed.add_field(name="Price", value="$4.99", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="ping_simple", description="Test if simple pack creation cog is loaded")
    async def ping_simple(self, interaction: Interaction):
        """Simple test command"""
        await interaction.response.send_message("✅ Simple pack creation cog is working!", ephemeral=True)

async def setup(bot):
    cog = PackCreationSimple(bot)
    await bot.add_cog(cog)
    print(f"🔥 PackCreationSimple cog added with {len([cmd for cmd in cog.walk_commands()])} commands")
