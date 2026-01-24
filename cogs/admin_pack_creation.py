# cogs/admin_pack_creation.py
"""
Admin pack creation system - Community and Gold packs with song-based cards
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from discord import Interaction, ui
import asyncio
from typing import Optional, Dict, List, Any
from googleapiclient.discovery import build
from database import DatabaseManager
import uuid
import json

YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")

class AdminPackCreation(commands.Cog):
    """Admin commands for creating community and gold packs"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        
        # Initialize YouTube client
        try:
            self.youtube = build("youtube", "v3", developerKey=YOUTUBE_KEY)
            print("✅ YouTube API initialized for admin pack creation")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            self.youtube = None
    
    async def search_youtube_songs(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for songs (videos) on YouTube - async safe"""
        if not self.youtube:
            print("❌ YouTube API not available")
            return []
        
        loop = asyncio.get_running_loop()
        
        def _search():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.search().list(
                    q=query,
                    part="snippet",
                    type="video",
                    videoCategoryId="10",  # Music category
                    maxResults=max_results
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _search)
        
        if not result or not result.get("items"):
            return []
        
        songs = []
        for item in result["items"]:
            snippet = item["snippet"]
            songs.append({
                "video_id": item["id"]["videoId"],
                "title": snippet["title"],
                "artist": snippet["channelTitle"],
                "thumbnail": snippet["thumbnails"]["high"]["url"],
                "description": snippet.get("description", "")[:200]
            })
        
        return songs
    
    async def get_video_stats(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video statistics - async safe"""
        if not self.youtube:
            return None
        
        loop = asyncio.get_running_loop()
        
        def _get_stats():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.videos().list(
                    part="statistics",
                    id=video_id
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _get_stats)
        
        if not result or not result.get("items"):
            return None
        
        stats = result["items"][0].get("statistics", {})
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0))
        }
    
    def calculate_song_tier(self, views: int, likes: int) -> str:
        """Calculate card tier based on song metrics"""
        if views >= 1_000_000_000 or likes >= 10_000_000:
            return "legendary"
        elif views >= 100_000_000 or likes >= 1_000_000:
            return "platinum"
        elif views >= 10_000_000 or likes >= 100_000:
            return "gold"
        else:
            return "community"
    
    async def create_song_card(self, song_data: Dict, stats: Dict) -> Dict[str, Any]:
        """Create a card from song data"""
        tier = self.calculate_song_tier(stats["views"], stats["likes"])
        
        # Generate stats from song metrics
        base_stat = min(92, max(20, int(20 + (stats["views"] / 10_000_000))))
        
        return {
            "name": song_data["title"],
            "artist": song_data["artist"],
            "rarity": tier,
            "youtube_video_id": song_data["video_id"],
            "youtube_url": f"https://youtube.com/watch?v={song_data['video_id']}",
            "image_url": song_data["thumbnail"],
            "card_type": "song",
            "era": "Modern",
            "impact": base_stat,
            "skill": base_stat,
            "longevity": base_stat,
            "culture": base_stat,
            "hype": base_stat,
            "views": stats["views"],
            "likes": stats["likes"]
        }
    
    @app_commands.command(name="admin_create_community_pack", description="[ADMIN] Create a community pack with random songs")
    @app_commands.describe(artist="Artist name to search for songs")
    async def admin_create_community_pack(self, interaction: Interaction, artist: str):
        """Create a community pack with 5 random songs"""
        
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only command", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Search for songs
        songs = await self.search_youtube_songs(f"{artist} official music video", max_results=5)
        
        if not songs or len(songs) < 5:
            await interaction.followup.send(f"❌ Could not find enough songs for {artist}")
            return
        
        # Create cards from songs
        cards = []
        for song in songs[:5]:
            stats = await self.get_video_stats(song["video_id"])
            if not stats:
                stats = {"views": 0, "likes": 0, "comments": 0}
            
            card = await self.create_song_card(song, stats)
            cards.append(card)
        
        # Create pack in database
        pack_id = f"community_{uuid.uuid4().hex[:8]}"
        cards_json = json.dumps(cards)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pack_id,
                0,
                f"{artist} Community Pack",
                f"5 random {artist} songs",
                5,
                "live",
                cards_json,
                0.0
            ))
            conn.commit()
        
        # Confirmation embed
        embed = discord.Embed(
            title="✅ Community Pack Created",
            description=f"**{artist} Community Pack**\n5 random songs",
            color=discord.Color.blue()
        )
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        
        for i, card in enumerate(cards, 1):
            embed.add_field(
                name=f"{i}. {card['name']}",
                value=f"👁️ {card['views']:,} views | {card['rarity'].title()}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="admin_create_gold_pack", description="[ADMIN] Create a gold pack with hero song selection")
    @app_commands.describe(artist="Artist name for hero song")
    async def admin_create_gold_pack(self, interaction: Interaction, artist: str):
        """Create a gold pack - user picks hero song, bot picks 4 featuring songs"""
        
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only command", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Search for hero songs
        songs = await self.search_youtube_songs(f"{artist} official music video", max_results=10)
        
        if not songs:
            await interaction.followup.send(f"❌ No songs found for {artist}")
            return
        
        # Show song selection UI
        view = SongSelectionView(songs, artist, self)
        
        embed = discord.Embed(
            title=f"🎵 Select Hero Song for {artist} Gold Pack",
            description="Choose ONE song to be the featured hero card.\nBot will auto-select 4 other songs featuring this artist.",
            color=discord.Color.gold()
        )
        
        for i, song in enumerate(songs[:5], 1):
            embed.add_field(
                name=f"{i}. {song['title']}",
                value=f"By: {song['artist']}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, view=view)


class SongSelectionView(ui.View):
    """UI for selecting hero song"""
    
    def __init__(self, songs: List[Dict], artist: str, cog):
        super().__init__(timeout=180)
        self.songs = songs
        self.artist = artist
        self.cog = cog
        
        # Add buttons for top 5 songs
        for i, song in enumerate(songs[:5]):
            button = ui.Button(
                label=f"{i+1}. {song['title'][:40]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"select_song_{i}"
            )
            button.callback = self.create_callback(song, i)
            self.add_item(button)
    
    def create_callback(self, hero_song: Dict, index: int):
        async def callback(interaction: Interaction):
            await interaction.response.defer()
            
            # Get hero song stats
            hero_stats = await self.cog.get_video_stats(hero_song["video_id"])
            if not hero_stats:
                hero_stats = {"views": 0, "likes": 0, "comments": 0}
            
            # Create hero card
            hero_card = await self.cog.create_song_card(hero_song, hero_stats)
            hero_card["is_hero"] = True
            
            # Search for featuring songs
            featuring_songs = await self.cog.search_youtube_songs(
                f"{self.artist} ft featuring", 
                max_results=4
            )
            
            # Create cards for featuring songs
            cards = [hero_card]
            for song in featuring_songs[:4]:
                stats = await self.cog.get_video_stats(song["video_id"])
                if not stats:
                    stats = {"views": 0, "likes": 0, "comments": 0}
                
                card = await self.cog.create_song_card(song, stats)
                cards.append(card)
            
            # Create pack in database
            pack_id = f"gold_{uuid.uuid4().hex[:8]}"
            cards_json = json.dumps(cards)
            
            with self.cog.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    0,
                    f"{self.artist} Gold Pack",
                    f"Hero: {hero_song['title']} + 4 featuring songs",
                    5,
                    "live",
                    cards_json,
                    5.0
                ))
                conn.commit()
            
            # Confirmation embed
            embed = discord.Embed(
                title="✅ Gold Pack Created",
                description=f"**{self.artist} Gold Pack**",
                color=discord.Color.gold()
            )
            embed.add_field(name="Pack ID", value=pack_id, inline=False)
            embed.add_field(
                name="🌟 Hero Song",
                value=f"{hero_card['name']}\n👁️ {hero_card['views']:,} views",
                inline=False
            )
            
            for i, card in enumerate(cards[1:], 1):
                embed.add_field(
                    name=f"{i}. {card['name']}",
                    value=f"👁️ {card['views']:,} views",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        
        return callback


async def setup(bot):
    await bot.add_cog(AdminPackCreation(bot))
