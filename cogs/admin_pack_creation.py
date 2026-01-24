# cogs/admin_pack_creation.py
"""
Pack creation system - Users create packs with song-based cards
Creator pays $9.99, gets pack, pack listed for $6.99 in marketplace
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
from stripe_payments import stripe_manager
import uuid
import json

YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")
DEV_USER_IDS = [int(uid.strip()) for uid in os.getenv("DEV_USER_IDS", "").split(",") if uid.strip()]

# Log dev IDs on startup
if DEV_USER_IDS:
    print(f"✅ DEV_USER_IDS loaded: {DEV_USER_IDS}")
else:
    print("⚠️ No DEV_USER_IDS configured - all users will be charged")

class AdminPackCreation(commands.Cog):
    """Pack creation system for users"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        
        # Initialize YouTube client
        try:
            self.youtube = build("youtube", "v3", developerKey=YOUTUBE_KEY)
            print("✅ YouTube API initialized for pack creation")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            self.youtube = None
    
    def is_dev(self, user_id: int) -> bool:
        """Check if user is a dev (bypasses payment)"""
        is_dev_user = user_id in DEV_USER_IDS
        if is_dev_user:
            print(f"✅ Dev bypass activated for user {user_id}")
        return is_dev_user
    
    async def search_specific_song(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a specific song on YouTube - async safe"""
        if not self.youtube:
            print("❌ YouTube API not available")
            return None
        
        loop = asyncio.get_running_loop()
        
        def _search():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.search().list(
                    q=query,
                    part="snippet",
                    type="video",
                    videoCategoryId="10",
                    maxResults=1
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _search)
        
        if not result or not result.get("items"):
            return None
        
        item = result["items"][0]
        snippet = item["snippet"]
        return {
            "video_id": item["id"]["videoId"],
            "title": snippet["title"],
            "artist": snippet["channelTitle"],
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "description": snippet.get("description", "")[:200]
        }
    
    async def get_related_videos(self, video_id: str, exclude_ids: List[str], max_results: int = 4) -> List[Dict[str, Any]]:
        """Get related videos - async safe"""
        if not self.youtube:
            return []
        
        loop = asyncio.get_running_loop()
        
        def _get_related():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.search().list(
                    relatedToVideoId=video_id,
                    part="snippet",
                    type="video",
                    maxResults=max_results + len(exclude_ids)
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _get_related)
        
        if not result or not result.get("items"):
            return []
        
        related = []
        for item in result["items"]:
            vid_id = item["id"]["videoId"]
            if vid_id not in exclude_ids and len(related) < max_results:
                snippet = item["snippet"]
                related.append({
                    "video_id": vid_id,
                    "title": snippet["title"],
                    "artist": snippet["channelTitle"],
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "description": snippet.get("description", "")[:200]
                })
        
        return related
    
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
    
    @app_commands.command(name="createpack", description="Create a pack with a featured song + 4 related songs")
    @app_commands.describe(song_query="Song to search (e.g., 'Drake - Hotline Bling')")
    async def createpack(self, interaction: Interaction, song_query: str):
        """Create a pack - charges $9.99 (or free for devs)"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if dev (bypass payment)
        is_dev = self.is_dev(interaction.user.id)
        
        if not is_dev:
            # Create Stripe checkout for $9.99
            checkout = stripe_manager.create_pack_creation_checkout(
                creator_id=interaction.user.id,
                song_query=song_query
            )
            
            if not checkout['success']:
                await interaction.followup.send(f"❌ Payment error: {checkout['error']}")
                return
            
            # Send payment link
            embed = discord.Embed(
                title="💳 Pack Creation Payment",
                description=f"**Song:** {song_query}\n**Price:** $9.99\n\nClick the link below to complete payment.",
                color=discord.Color.blue()
            )
            embed.add_field(name="What you get:", value="• 1 featured song card\n• 4 related song cards\n• Pack added to your inventory\n• Pack listed in marketplace for $6.99", inline=False)
            
            await interaction.followup.send(
                embed=embed,
                view=discord.ui.View().add_item(
                    discord.ui.Button(label="Pay $9.99", url=checkout['checkout_url'], style=discord.ButtonStyle.link)
                )
            )
            return
        
        # Dev bypass - create pack immediately
        await self._create_pack_for_user(interaction, song_query)
    
    async def _create_pack_for_user(self, interaction: Interaction, song_query: str):
        """Internal method to create pack after payment or dev bypass"""
        
        # Search for specific song
        hero_song = await self.search_specific_song(song_query)
        
        if not hero_song:
            await interaction.followup.send(f"❌ Could not find song: {song_query}")
            return
        
        # Get hero song stats
        hero_stats = await self.get_video_stats(hero_song["video_id"])
        if not hero_stats:
            hero_stats = {"views": 0, "likes": 0, "comments": 0}
        
        # Create hero card
        hero_card = await self.create_song_card(hero_song, hero_stats)
        hero_card["is_hero"] = True
        
        # Get 4 related videos
        related_songs = await self.get_related_videos(
            hero_song["video_id"],
            exclude_ids=[hero_song["video_id"]],
            max_results=4
        )
        
        # Create cards for related songs
        cards = [hero_card]
        for song in related_songs:
            stats = await self.get_video_stats(song["video_id"])
            if not stats:
                stats = {"views": 0, "likes": 0, "comments": 0}
            
            card = await self.create_song_card(song, stats)
            cards.append(card)
        
        # Create pack in database
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        cards_json = json.dumps(cards)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert pack
            cursor.execute("""
                INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pack_id,
                interaction.user.id,
                f"{hero_song['title']} Pack",
                f"Featured: {hero_song['title']} + 4 related songs",
                5,
                "live",
                cards_json,
                6.99
            ))
            
            # Add pack to creator's inventory
            cursor.execute("""
                INSERT INTO user_packs (user_id, pack_id, acquired_at)
                VALUES (?, ?, datetime('now'))
            """, (interaction.user.id, pack_id))
            
            conn.commit()
        
        # Return pack preview
        embed = discord.Embed(
            title="✅ Pack Created Successfully",
            description=f"**{hero_song['title']} Pack**\n\nPack added to your inventory and listed in marketplace for $6.99",
            color=discord.Color.green()
        )
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        embed.add_field(
            name="🌟 Featured Song",
            value=f"{hero_card['name']}\n👁️ {hero_card['views']:,} views | {hero_card['rarity'].title()}",
            inline=False
        )
        
        for i, card in enumerate(cards[1:], 1):
            embed.add_field(
                name=f"{i}. {card['name']}",
                value=f"👁️ {card['views']:,} views | {card['rarity'].title()}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)


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
