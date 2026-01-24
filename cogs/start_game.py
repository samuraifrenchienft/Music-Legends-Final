"""
Start Game Command - Initialize Music Legends with real artist cards
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
from typing import Optional

class StartGameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from database import db
        from card_economy import get_economy_manager
        self.db = db
        self.economy = get_economy_manager()
    
    @app_commands.command(name="start_game", description="🎮 Start Music Legends in this server!")
    async def start_game(self, interaction: Interaction):
        """Initialize Music Legends with real artist cards from YouTube"""
        
        # Check if user is admin/owner
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔒 Only server administrators can start the game!", ephemeral=True)
            return
        
        await interaction.response.defer()  # This might take a moment
        
        # Create epic announcement embed
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
• `/market` - Browse the card marketplace

*Creating starter cards from YouTube... Please wait!*
            """,
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎯 Current Status",
            value="🔄 **Initializing Game Database...**\nAdding real artist cards from YouTube!",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        # Create real artist cards using YouTube
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
                # Create artist from YouTube
                artist_data = await game_integration.create_artist_from_youtube(artist_name)
                
                if artist_data:
                    # Add to database as master card
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
                    
                    # Store in database
                    import sqlite3
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
        
        # Create success/failure update
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

{f'⚠️ Some artists failed to load: {", ".join(failed_artists[:5])}' if failed_artists else ''}
                """,
                color=discord.Color.green()
            )
            
            # Show sample cards
            sample_cards = created_cards[:6]
            for card in sample_cards:
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['rarity'], "⚪")
                total_power = card['impact'] + card['skill'] + card['longevity'] + card['culture'] + card['hype']
                success_embed.add_field(
                    name=f"{tier_emoji} {card['name']}",
                    value=f"Tier: {card['rarity'].title()}\nPower: {total_power}",
                    inline=True
                )
            
            await interaction.followup.send(embed=success_embed)
            
            # Create first drop automatically
            try:
                drop_result = self.economy.create_drop(
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
                    
                    # Add cards to embed
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
    # Check if we should sync globally or to test server
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(StartGameCog(bot))
    else:
        await bot.add_cog(
            StartGameCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
