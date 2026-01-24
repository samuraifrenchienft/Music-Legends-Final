"""
Essential Game Commands - No Duplicates
Only the core commands needed for gameplay
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3
from database import DatabaseManager
from card_economy import CardEconomyManager
from stripe_payments import StripePaymentManager

class EssentialCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        from card_economy import get_economy_manager
        self.economy = get_economy_manager()
        self.economy.initialize_economy_tables()  # Initialize drop tables
        self.stripe = StripePaymentManager()
    
    @app_commands.command(name="collection", description="View your card collection")
    async def collection(self, interaction: Interaction):
        """View your card collection"""
        await interaction.response.send_message("📦 Collection feature coming soon!", ephemeral=True)
    
    @app_commands.command(name="drop", description="Create a card drop in this channel")
    async def drop(self, interaction: Interaction):
        """Create a card drop"""
        try:
            drop_result = self.economy.create_drop(
                interaction.channel_id,
                interaction.guild.id,
                interaction.user.id
            )
            
            if not drop_result['success']:
                await interaction.response.send_message(f"❌ {drop_result['error']}", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎴 CARD DROP! 🎴",
                description="React quickly to grab cards!",
                color=discord.Color.gold()
            )
            
            cards = drop_result['cards']
            for i, card in enumerate(cards, 1):
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card.get('tier', 'community'), "⚪")
                embed.add_field(
                    name=f"{tier_emoji} Card {i}",
                    value=f"{card.get('name', 'Unknown')}\nTier: {card.get('tier', 'community').title()}",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating drop: {e}", ephemeral=True)
    
    @app_commands.command(name="battle", description="Challenge someone to a card battle")
    async def battle(self, interaction: Interaction, opponent: discord.User):
        """Challenge someone to a battle"""
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't battle yourself!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="Status", value="⏳ Waiting for opponent to accept...")
        
        await interaction.response.send_message(embed=embed)
    
    
    @app_commands.command(name="start_game", description="🎮 Start Music Legends in this server!")
    async def start_game(self, interaction: Interaction):
        """Initialize Music Legends with starter artist cards"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔒 Only server administrators can start the game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Create starter cards directly without YouTube API
        starter_artists = [
            {"name": "Taylor Swift", "tier": "legendary", "genre": "Pop", "power": 95},
            {"name": "Drake", "tier": "legendary", "genre": "Hip-Hop", "power": 94},
            {"name": "Bad Bunny", "tier": "legendary", "genre": "Latin", "power": 93},
            {"name": "The Weeknd", "tier": "platinum", "genre": "R&B", "power": 88},
            {"name": "Ariana Grande", "tier": "platinum", "genre": "Pop", "power": 87},
            {"name": "Ed Sheeran", "tier": "platinum", "genre": "Pop", "power": 86},
            {"name": "Billie Eilish", "tier": "platinum", "genre": "Alternative", "power": 85},
            {"name": "Post Malone", "tier": "gold", "genre": "Hip-Hop", "power": 78},
            {"name": "Dua Lipa", "tier": "gold", "genre": "Pop", "power": 77},
            {"name": "Olivia Rodrigo", "tier": "gold", "genre": "Pop", "power": 76},
            {"name": "Doja Cat", "tier": "gold", "genre": "Pop", "power": 75},
            {"name": "Harry Styles", "tier": "gold", "genre": "Pop", "power": 74},
            {"name": "Bruno Mars", "tier": "platinum", "genre": "Pop", "power": 89},
            {"name": "Adele", "tier": "legendary", "genre": "Pop", "power": 92},
            {"name": "Justin Bieber", "tier": "platinum", "genre": "Pop", "power": 84},
            {"name": "Kendrick Lamar", "tier": "legendary", "genre": "Hip-Hop", "power": 96},
            {"name": "Rihanna", "tier": "legendary", "genre": "Pop", "power": 91},
            {"name": "Eminem", "tier": "legendary", "genre": "Hip-Hop", "power": 97},
            {"name": "Kanye West", "tier": "platinum", "genre": "Hip-Hop", "power": 90},
            {"name": "Beyoncé", "tier": "legendary", "genre": "R&B", "power": 98}
        ]
        
        created_count = 0
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            for artist in starter_artists:
                try:
                    card_id = f"starter_{artist['name'].lower().replace(' ', '_')}"
                    
                    # Calculate stats from power level
                    base_stat = artist['power'] // 5
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO cards 
                        (card_id, name, rarity, card_type, era, impact, skill, longevity, culture, hype, type)
                        VALUES (?, ?, ?, 'artist', 'Modern', ?, ?, ?, ?, ?, 'artist')
                    """, (
                        card_id, 
                        artist['name'], 
                        artist['tier'],
                        base_stat,
                        base_stat,
                        base_stat,
                        base_stat,
                        base_stat
                    ))
                    
                    if cursor.rowcount > 0:
                        created_count += 1
                        
                except Exception as e:
                    print(f"Error creating card for {artist['name']}: {e}")
            
            conn.commit()
        
        if created_count > 0:
            success_embed = discord.Embed(
                title="✅ Game Successfully Started!",
                description=f"""
🎉 **Music Legends is ready to play!**

📊 **Cards Created:** {created_count} starter artist cards
⭐ **Tiers:** Community, Gold, Platinum, Legendary

🎮 **Try these commands:**
• `/drop` - Create a community drop
• `/collection` - View your cards
• `/battle @friend` - Start a card battle
• `/pack_add_artist_smart` - Add more artists from YouTube
                """,
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed)
            
            try:
                drop_result = self.economy.create_drop(
                    interaction.channel_id,
                    interaction.guild.id, 
                    interaction.user.id
                )
                
                if drop_result['success']:
                    drop_embed = discord.Embed(
                        title="🎁 WELCOME DROP! 🎁",
                        description="First card drop created! React quickly to grab cards!",
                        color=discord.Color.gold()
                    )
                    
                    cards = drop_result['cards']
                    for i, card in enumerate(cards, 1):
                        tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card.get('tier', 'community'), "⚪")
                        drop_embed.add_field(
                            name=f"{tier_emoji} Card {i}",
                            value=f"{card.get('name', 'Unknown')}\nTier: {card.get('tier', 'community').title()}",
                            inline=True
                        )
                    
                    await interaction.followup.send(embed=drop_embed)
                    
            except Exception as e:
                print(f"Error creating welcome drop: {e}")
        else:
            error_embed = discord.Embed(
                title="❌ Game Start Failed",
                description="Could not create any starter cards. Please try again or contact support.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

async def setup(bot):
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(EssentialCommandsCog(bot))
    else:
        await bot.add_cog(
            EssentialCommandsCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
