"""
Essential Game Commands - No Duplicates
Only the core commands needed for gameplay
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3
from database import DatabaseManager, db
from card_economy import CardEconomyManager, economy_manager

class EssentialCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
    
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
    
    @app_commands.command(name="pack_add_artist_smart", description="Add artist card with YouTube integration")
    async def pack_add_artist_smart(self, interaction: Interaction, artist_name: str):
        """Add an artist card using YouTube data"""
        await interaction.response.defer()
        
        try:
            from services.game_integration import game_integration
            
            # Create artist from YouTube
            artist_data = await game_integration.create_artist_from_youtube(artist_name)
            
            if not artist_data:
                await interaction.followup.send(f"❌ Could not find artist '{artist_name}' on YouTube", ephemeral=True)
                return
            
            # Add to database
            card_data = {
                'card_id': f"artist_{artist_data['id']}",
                'name': artist_data['name'],
                'rarity': artist_data['tier'],
                'image_url': artist_data.get('image', ''),
                'spotify_url': f"https://youtube.com/channel/{artist_data['youtube_channel_id']}",
                'card_type': 'artist',
                'era': 'Modern',
                'impact': artist_data['game_data']['power_level'] // 5,
                'skill': artist_data['game_data']['power_level'] // 5,
                'longevity': artist_data['game_data']['power_level'] // 5,
                'culture': artist_data['game_data']['power_level'] // 5,
                'hype': artist_data['game_data']['power_level'] // 5
            }
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO cards 
                    (card_id, name, rarity, image_url, spotify_url, card_type, era, impact, skill, longevity, culture, hype)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    card_data['card_id'], card_data['name'], card_data['rarity'],
                    card_data['image_url'], card_data['spotify_url'], card_data['card_type'],
                    card_data['era'], card_data['impact'], card_data['skill'],
                    card_data['longevity'], card_data['culture'], card_data['hype']
                ))
                conn.commit()
            
            embed = discord.Embed(
                title="✅ Artist Card Created!",
                description=f"**{artist_data['name']}** has been added from YouTube",
                color=discord.Color.green()
            )
            embed.add_field(name="Tier", value=artist_data['tier'].title())
            embed.add_field(name="Power Level", value=artist_data['game_data']['power_level'])
            embed.set_thumbnail(url=artist_data.get('image', ''))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating artist card: {e}", ephemeral=True)
    
    @app_commands.command(name="start_game", description="🎮 Start Music Legends in this server!")
    async def start_game(self, interaction: Interaction):
        """Initialize Music Legends with real artist cards from YouTube"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔒 Only server administrators can start the game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🎵🎮 MUSIC LEGENDS IS NOW LIVE! 🎮🎵",
            description="""
**Welcome to Music Legends - The Ultimate Card Battle Game!**

🎴 **Collect cards** of your favorite music artists
⚔️ **Battle friends** with strategic card decks  
🎁 **Open daily packs** for rare cards
💰 **Trade & sell** cards in the marketplace

🚀 **Getting Started:**
• `/drop` - Create a card drop for the community
• `/collection` - View your card collection
• `/battle @friend` - Challenge someone to a card battle
• `/pack_add_artist_smart` - Add artists from YouTube

*Creating starter cards from YouTube... Please wait!*
            """,
            color=discord.Color.purple()
        )
        
        await interaction.followup.send(embed=embed)
        
        starter_artists = [
            "Taylor Swift", "Drake", "Bad Bunny", "The Weeknd", 
            "Ariana Grande", "Ed Sheeran", "Billie Eilish", "Post Malone",
            "Dua Lipa", "Olivia Rodrigo", "Doja Cat", "Harry Styles",
            "Bruno Mars", "Adele", "Justin Bieber", "Kendrick Lamar",
            "Rihanna", "Maroon 5", "Coldplay", "Imagine Dragons",
            "BTS", "Blackpink", "Travis Scott", "Cardi B",
            "Eminem", "Kanye West", "Lady Gaga", "Beyoncé"
        ]
        
        created_cards = []
        failed_artists = []
        
        from services.game_integration import game_integration
        
        for artist_name in starter_artists:
            try:
                artist_data = await game_integration.create_artist_from_youtube(artist_name)
                
                if artist_data:
                    card_data = {
                        'card_id': f"artist_{artist_data['id']}",
                        'name': artist_data['name'],
                        'rarity': artist_data['tier'],
                        'image_url': artist_data.get('image', ''),
                        'spotify_url': f"https://youtube.com/channel/{artist_data['youtube_channel_id']}",
                        'card_type': 'artist',
                        'era': 'Modern',
                        'impact': artist_data['game_data']['power_level'] // 5,
                        'skill': artist_data['game_data']['power_level'] // 5,
                        'longevity': artist_data['game_data']['power_level'] // 5,
                        'culture': artist_data['game_data']['power_level'] // 5,
                        'hype': artist_data['game_data']['power_level'] // 5
                    }
                    
                    with sqlite3.connect(self.db.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR IGNORE INTO cards 
                            (card_id, name, rarity, image_url, spotify_url, card_type, era, impact, skill, longevity, culture, hype)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            card_data['card_id'], card_data['name'], card_data['rarity'],
                            card_data['image_url'], card_data['spotify_url'], card_data['card_type'],
                            card_data['era'], card_data['impact'], card_data['skill'],
                            card_data['longevity'], card_data['culture'], card_data['hype']
                        ))
                        conn.commit()
                    
                    created_cards.append(card_data)
                else:
                    failed_artists.append(artist_name)
                    
            except Exception as e:
                print(f"Error creating card for {artist_name}: {e}")
                failed_artists.append(artist_name)
        
        if created_cards:
            success_embed = discord.Embed(
                title="✅ Game Successfully Started!",
                description=f"""
🎉 **Music Legends is ready to play!**

📊 **Cards Created:** {len(created_cards)} real artist cards
🎵 **Source:** YouTube music channels
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
                drop_result = economy_manager.create_drop(
                    interaction.channel_id,
                    interaction.guild.id, 
                    interaction.user.id
                )
                
                if drop_result['success']:
                    drop_embed = discord.Embed(
                        title="🎴 WELCOME DROP! 🎴",
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
                description="Could not create artist cards. Please check YouTube API configuration in .env.txt",
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
