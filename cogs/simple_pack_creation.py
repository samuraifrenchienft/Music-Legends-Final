"""
Simple Pack Creation - No YouTube API Required
Creates packs using existing cards in database
"""
import discord
import os
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3
import random
import uuid
from database import DatabaseManager

class SimplePackCreation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    def is_dev(self, user_id: int) -> bool:
        """Check if user is a developer"""
        dev_ids = [int(uid.strip()) for uid in (os.getenv("DEV_USER_IDS", "").split(",") if os.getenv("DEV_USER_IDS") else "")]
        return user_id in dev_ids if dev_ids else True  # Allow everyone if no dev IDs set
    
    @app_commands.command(name="create_simple_pack", description="Create a pack using existing cards (No YouTube required)")
    @app_commands.describe(pack_name="Name for your pack", pack_type="Type of pack: basic, premium, or legendary")
    async def create_simple_pack(self, interaction: Interaction, pack_name: str, pack_type: str = "basic"):
        """Create a simple pack using existing database cards"""
        
        await interaction.response.defer()
        
        try:
            # Get existing cards from database
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT card_id, name, rarity FROM cards ORDER BY RANDOM() LIMIT 50")
                available_cards = cursor.fetchall()
            
            if not available_cards:
                await interaction.followup.send("❌ No cards found in database!", ephemeral=True)
                return
            
            # Define pack configurations
            pack_configs = {
                "basic": {"size": 5, "rarities": {"Common": 3, "Rare": 2}},
                "premium": {"size": 10, "rarities": {"Common": 4, "Rare": 4, "Epic": 2}},
                "legendary": {"size": 15, "rarities": {"Common": 6, "Rare": 5, "Epic": 3, "Legendary": 1}}
            }
            
            if pack_type not in pack_configs:
                await interaction.followup.send("❌ Invalid pack type! Use: basic, premium, or legendary", ephemeral=True)
                return
            
            config = pack_configs[pack_type]
            
            # Filter cards by required rarities
            pack_cards = []
            for rarity, count in config["rarities"].items():
                rarity_cards = [card for card in available_cards if card[2] == rarity]
                if len(rarity_cards) < count:
                    await interaction.followup.send(f"❌ Not enough {rarity} cards available!", ephemeral=True)
                    return
                selected = random.sample(rarity_cards, count)
                pack_cards.extend(selected)
            
            # Create pack record
            pack_id = str(uuid.uuid4())[:8]
            cards_data = []
            
            for card_id, name, rarity in pack_cards:
                cards_data.append({
                    "card_id": card_id,
                    "name": name,
                    "rarity": rarity
                })
            
            # Store pack in database (using creator_packs table as temporary storage)
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO creator_packs 
                    (pack_id, creator_id, name, description, pack_size, cards_data, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    pack_id,
                    interaction.user.id,
                    pack_name,
                    f"Simple {pack_type} pack with {config['size']} cards",
                    config["size"],
                    str(cards_data),  # Store as JSON string
                    "live"
                ))
                conn.commit()
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Simple Pack Created!",
                description=f"Pack **{pack_name}** has been created successfully!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Pack Details",
                value=f"• ID: `{pack_id}`\n"
                      f"• Type: {pack_type.title()}\n"
                      f"• Size: {config['size']} cards\n"
                      f"• Status: Live",
                inline=False
            )
            
            # Show card breakdown
            rarity_emoji = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐"}
            card_list = []
            for card_id, name, rarity in pack_cards:
                emoji = rarity_emoji.get(rarity, "🎴")
                card_list.append(f"{emoji} **{name}** ({rarity})")
            
            embed.add_field(
                name="Cards in Pack",
                value="\n".join(card_list[:10]) + ("\n... and more" if len(card_list) > 10 else ""),
                inline=False
            )
            
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating pack: {e}", ephemeral=True)
    
    @app_commands.command(name="test_cards", description="Test if cards are available in database")
    async def test_cards(self, interaction: Interaction):
        """Test command to check available cards"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM cards")
                total_cards = cursor.fetchone()[0]
                
                cursor.execute("SELECT rarity, COUNT(*) FROM cards GROUP BY rarity")
                rarity_counts = cursor.fetchall()
            
            embed = discord.Embed(
                title="📊 Database Card Status",
                description=f"Total cards in database: {total_cards}",
                color=discord.Color.blue()
            )
            
            rarity_emoji = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐"}
            
            for rarity, count in rarity_counts:
                emoji = rarity_emoji.get(rarity, "🎴")
                embed.add_field(name=f"{emoji} {rarity}", value=f"{count} cards", inline=True)
            
            embed.set_footer(text="Cards are available for pack creation")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error checking cards: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SimplePackCreation(bot))
    print("✅ SimplePackCreation cog loaded - no YouTube API required")
