# cogs/simple_pack_creation.py
"""
Simple pack creation using YouTube Data API v3
Based on production-style implementation
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from discord import Interaction
import asyncio
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from database import DatabaseManager
import uuid
import json

YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")

class SimplePackCreation(commands.Cog):
    """Simple pack creation with YouTube integration"""
    
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
    
    async def search_youtube_channel(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for YouTube channel - async safe with executor"""
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
                    type="channel",
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
        return {
            "channel_id": item["snippet"]["channelId"],
            "title": item["snippet"]["title"],
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
            "description": item["snippet"]["description"]
        }
    
    async def get_channel_stats(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel statistics - async safe with executor"""
        if not self.youtube:
            return None
        
        loop = asyncio.get_running_loop()
        
        def _get_stats():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.channels().list(
                    part="statistics,snippet",
                    id=channel_id
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _get_stats)
        
        if not result or not result.get("items"):
            return None
        
        item = result["items"][0]
        stats = item.get("statistics", {})
        
        return {
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0))
        }
    
    async def create_pack_backend(self, artist_name: str, channel_id: str, image_url: str, stats: Dict) -> str:
        """Create pack in database with artist card"""
        await asyncio.sleep(0.1)
        
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        
        # Calculate tier based on subscribers
        subscribers = stats.get("subscribers", 0)
        views = stats.get("views", 0)
        
        if subscribers >= 10_000_000 or views >= 1_000_000_000:
            tier = "legendary"
        elif subscribers >= 1_000_000 or views >= 100_000_000:
            tier = "platinum"
        elif subscribers >= 100_000 or views >= 10_000_000:
            tier = "gold"
        else:
            tier = "community"
        
        # Create artist card
        card_data = {
            "name": artist_name,
            "rarity": tier,
            "youtube_channel_id": channel_id,
            "youtube_url": f"https://youtube.com/channel/{channel_id}",
            "image_url": image_url,
            "card_type": "artist",
            "era": "Modern",
            "impact": 75,
            "skill": 75,
            "longevity": 75,
            "culture": 75,
            "hype": 75,
            "subscribers": subscribers,
            "total_views": views
        }
        
        # Create pack with 1 card
        cards_json = json.dumps([card_data])
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pack_id,
                0,  # System created
                f"{artist_name} Pack",
                f"Artist pack featuring {artist_name}",
                1,
                "live",
                cards_json,
                0.0
            ))
            conn.commit()
        
        return pack_id
    
    @app_commands.command(name="createpack", description="Create a new artist pack using YouTube")
    async def createpack(self, interaction: Interaction, artist: str):
        """
        Create a pack from a YouTube artist
        
        Parameters:
        -----------
        artist: str
            Artist name to search on YouTube
        """
        
        # STEP 1 — IMMEDIATE DEFER (CRITICAL)
        await interaction.response.defer(ephemeral=True)
        
        # STEP 2 — YOUTUBE LOOKUP
        yt_data = await self.search_youtube_channel(artist)
        
        if not yt_data:
            await interaction.followup.send(
                f"❌ No YouTube channel found for **{artist}**."
            )
            return
        
        # STEP 3 — GET CHANNEL STATS
        stats = await self.get_channel_stats(yt_data["channel_id"])
        
        if not stats:
            stats = {"subscribers": 0, "views": 0, "videos": 0}
        
        # STEP 4 — BACKEND INGESTION
        pack_id = await self.create_pack_backend(
            artist_name=yt_data["title"],
            channel_id=yt_data["channel_id"],
            image_url=yt_data["thumbnail"],
            stats=stats
        )
        
        # STEP 5 — CONFIRMATION EMBED
        embed = discord.Embed(
            title="✅ Pack Created",
            description=f"Artist pack created for **{yt_data['title']}**",
            color=0x00FF00
        )
        embed.set_thumbnail(url=yt_data["thumbnail"])
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        embed.add_field(name="Source", value="YouTube", inline=True)
        embed.add_field(name="Subscribers", value=f"{stats['subscribers']:,}", inline=True)
        embed.add_field(name="Views", value=f"{stats['views']:,}", inline=True)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SimplePackCreation(bot))
