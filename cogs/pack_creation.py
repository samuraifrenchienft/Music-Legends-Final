# cogs/pack_creation.py
"""
URL-Based Pack Creation System
- /create_community_pack [youtube_url] - Dev only, free, $4.99 marketplace
- /create_gold_pack [youtube_url] - Anyone, $9.99 or dev bypass, $6.99 marketplace
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from discord import Interaction
import asyncio
import re
from typing import Optional, Dict, List, Any
from googleapiclient.discovery import build
from database import DatabaseManager
from stripe_payments import stripe_manager
import uuid
import json
import random

YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")
DEV_USER_IDS = [int(uid.strip()) for uid in os.getenv("DEV_USER_IDS", "").split(",") if uid.strip()]

if DEV_USER_IDS:
    print(f"✅ DEV_USER_IDS loaded: {DEV_USER_IDS}")
else:
    print("⚠️ No DEV_USER_IDS configured - all users will be charged")

class PackCreation(commands.Cog):
    """URL-based pack creation system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.youtube = None
    
    async def cog_load(self):
        """Initialize YouTube API when cog loads"""
        print("🔥 PackCreation cog is loading!")
        try:
            self.youtube = build("youtube", "v3", developerKey=YOUTUBE_KEY)
            print("✅ YouTube API initialized for pack creation")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            self.youtube = None
    
    def is_dev(self, user_id: int) -> bool:
        """Check if user is a dev"""
        is_dev_user = user_id in DEV_USER_IDS
        if is_dev_user:
            print(f"✅ Dev bypass activated for user {user_id}")
        return is_dev_user
    
    def parse_youtube_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=)([^&]+)',
            r'(?:youtu\.be/)([^?]+)',
            r'(?:youtube\.com/embed/)([^?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video details from YouTube"""
        if not self.youtube:
            return None
        
        loop = asyncio.get_running_loop()
        
        def _get_details():
            try:
                request = self.youtube.videos().list(
                    part="snippet,statistics",
                    id=video_id
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _get_details)
        
        if not result or not result.get("items"):
            return None
        
        item = result["items"][0]
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        
        return {
            "video_id": video_id,
            "title": snippet["title"],
            "artist": snippet["channelTitle"],
            "channel_id": snippet["channelId"],
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0))
        }
    
    async def get_channel_videos(self, channel_id: str, exclude_ids: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """Get videos from same channel"""
        if not self.youtube:
            return []
        
        loop = asyncio.get_running_loop()
        
        def _get_videos():
            try:
                request = self.youtube.search().list(
                    channelId=channel_id,
                    part="snippet",
                    type="video",
                    order="viewCount",
                    maxResults=max_results
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _get_videos)
        
        if not result or not result.get("items"):
            return []
        
        videos = []
        for item in result["items"]:
            vid_id = item["id"]["videoId"]
            if vid_id not in exclude_ids:
                snippet = item["snippet"]
                videos.append({
                    "video_id": vid_id,
                    "title": snippet["title"],
                    "artist": snippet["channelTitle"],
                    "thumbnail": snippet["thumbnails"]["high"]["url"]
                })
        
        return videos
    
    async def get_video_stats_batch(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get statistics for multiple videos"""
        if not self.youtube or not video_ids:
            return {}
        
        loop = asyncio.get_running_loop()
        
        def _get_stats():
            try:
                request = self.youtube.videos().list(
                    part="statistics",
                    id=",".join(video_ids[:50])
                )
                return request.execute()
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        result = await loop.run_in_executor(None, _get_stats)
        
        if not result or not result.get("items"):
            return {}
        
        stats_map = {}
        for item in result["items"]:
            vid_id = item["id"]
            stats = item.get("statistics", {})
            stats_map[vid_id] = {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0))
            }
        
        return stats_map
    
    def calculate_tier(self, views: int, likes: int) -> str:
        """Calculate card tier"""
        if views >= 1_000_000_000 or likes >= 10_000_000:
            return "legendary"
        elif views >= 100_000_000 or likes >= 1_000_000:
            return "platinum"
        elif views >= 10_000_000 or likes >= 100_000:
            return "gold"
        else:
            return "community"
    
    def create_card(self, video: Dict, stats: Dict) -> Dict:
        """Create card from video data"""
        tier = self.calculate_tier(stats["views"], stats["likes"])
        base_stat = min(92, max(20, int(20 + (stats["views"] / 10_000_000))))
        
        return {
            "name": video["title"],
            "artist": video["artist"],
            "rarity": tier,
            "youtube_video_id": video["video_id"],
            "youtube_url": f"https://youtube.com/watch?v={video['video_id']}",
            "image_url": video["thumbnail"],
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
    
    async def create_pack(self, youtube_url: str, pack_type: str, user_id: int, bypass_payment: bool) -> Dict:
        """Shared pack creation logic"""
        
        # Parse URL
        video_id = self.parse_youtube_url(youtube_url)
        if not video_id:
            return {"success": False, "error": "Invalid YouTube URL"}
        
        print(f"🎬 Creating {pack_type} pack from video: {video_id}")
        
        # Get hero video details
        hero_video = await self.get_video_details(video_id)
        if not hero_video:
            return {"success": False, "error": "Could not fetch video details"}
        
        print(f"🎵 Hero: {hero_video['title']} by {hero_video['artist']}")
        
        # Create hero card
        hero_card = self.create_card(hero_video, {"views": hero_video["views"], "likes": hero_video["likes"]})
        hero_card["is_hero"] = True
        
        # Get related videos from same channel
        related_videos = await self.get_channel_videos(
            hero_video["channel_id"],
            exclude_ids=[video_id],
            max_results=50
        )
        
        if len(related_videos) < 4:
            return {"success": False, "error": f"Not enough related videos (found {len(related_videos)}, need 4)"}
        
        print(f"✅ Found {len(related_videos)} related videos")
        
        # Get previously generated IDs
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT generated_youtube_id FROM card_generation_log
                WHERE hero_artist = ? AND hero_song = ?
            """, (hero_video["artist"], hero_video["title"]))
            previously_generated = [row[0] for row in cursor.fetchall()]
        
        # Filter out duplicates
        available_videos = [v for v in related_videos if v["video_id"] not in previously_generated]
        
        if len(available_videos) < 4:
            print(f"⚠️ Only {len(available_videos)} unique videos, allowing duplicates")
            available_videos = related_videos
        
        # Random select 4
        random.shuffle(available_videos)
        selected_videos = available_videos[:4]
        
        # Get stats for selected videos
        video_ids = [v["video_id"] for v in selected_videos]
        stats_map = await self.get_video_stats_batch(video_ids)
        
        # Create cards
        cards = [hero_card]
        for video in selected_videos:
            stats = stats_map.get(video["video_id"], {"views": 0, "likes": 0})
            card = self.create_card(video, stats)
            cards.append(card)
        
        # Database transaction
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        cards_json = json.dumps(cards)
        
        marketplace_price = 4.99 if pack_type == "community" else 6.99
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert pack
                cursor.execute("""
                    INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    user_id,  # Always use actual user_id (dev or regular user)
                    f"{hero_video['title']} Pack",
                    f"Featured: {hero_video['title']} + 4 related songs",
                    5,
                    "live",
                    cards_json,
                    marketplace_price
                ))
                
                # Add to inventory (both pack types now)
                cursor.execute("""
                    INSERT INTO user_packs (user_id, pack_id, acquired_at)
                    VALUES (?, ?, datetime('now'))
                """, (user_id, pack_id))
                
                # List in marketplace
                cursor.execute("""
                    INSERT INTO marketplace (pack_id, price, stock)
                    VALUES (?, ?, ?)
                """, (pack_id, marketplace_price, "unlimited"))
                
                # Log generated cards
                for card in cards[1:]:
                    cursor.execute("""
                        INSERT INTO card_generation_log (hero_artist, hero_song, generated_youtube_id)
                        VALUES (?, ?, ?)
                    """, (hero_video["artist"], hero_video["title"], card["youtube_video_id"]))
                
                conn.commit()
                print(f"✅ Pack {pack_id} created successfully")
        
        except Exception as e:
            print(f"❌ Database error: {e}")
            return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "pack_id": pack_id,
            "pack_type": pack_type,
            "hero_card": hero_card,
            "cards": cards,
            "marketplace_price": marketplace_price,
            "added_to_inventory": True  # Both pack types now add to inventory
        }
    
    @app_commands.command(name="create_community_pack", description="[DEV ONLY] Create a community pack from YouTube URL")
    @app_commands.describe(youtube_url="YouTube video URL (e.g., https://youtube.com/watch?v=...)")
    async def create_community_pack(self, interaction: Interaction, youtube_url: str):
        """Create community pack - dev only"""
        
        # Permission check
        if not self.is_dev(interaction.user.id):
            await interaction.response.send_message("❌ This command is dev-only", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create pack
        result = await self.create_pack(youtube_url, "community", interaction.user.id, bypass_payment=True)
        
        if not result["success"]:
            await interaction.followup.send(f"❌ {result['error']}")
            return
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Community Pack Created!",
            description=f"**Added to your inventory**\nNow available in marketplace for $4.99",
            color=discord.Color.blue()
        )
        embed.add_field(name="Pack ID", value=result["pack_id"], inline=False)
        embed.add_field(name="🌟 Hero Song", value=f"{result['hero_card']['name']}\n👁️ {result['hero_card']['views']:,} views", inline=False)
        
        for i, card in enumerate(result["cards"][1:], 1):
            embed.add_field(name=f"{i}. {card['name']}", value=f"👁️ {card['views']:,} views", inline=False)
        
        embed.add_field(
            name="💡 Use Cases",
            value="• Open it to seed your server's card economy\n• Gift cards to users with `/give_card`\n• Run contests/giveaways\n• Test features with real cards",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="create_gold_pack", description="Create a gold pack from YouTube URL ($9.99 or dev bypass)")
    @app_commands.describe(youtube_url="YouTube video URL (e.g., https://youtube.com/watch?v=...)")
    async def create_gold_pack(self, interaction: Interaction, youtube_url: str):
        """Create gold pack - anyone with payment"""
        
        is_dev = self.is_dev(interaction.user.id)
        
        if not is_dev:
            # Charge $9.99
            await interaction.response.defer(ephemeral=True)
            
            checkout = stripe_manager.create_pack_creation_checkout(
                creator_id=interaction.user.id,
                song_query=youtube_url
            )
            
            if not checkout['success']:
                await interaction.followup.send(f"❌ Payment error: {checkout['error']}")
                return
            
            embed = discord.Embed(
                title="💳 Pack Creation Payment",
                description=f"**Price:** $9.99\n\nClick below to complete payment.",
                color=discord.Color.blue()
            )
            embed.add_field(name="What you get:", value="• 1 hero song card\n• 4 related song cards\n• Pack in your inventory\n• Listed in marketplace for $6.99", inline=False)
            
            await interaction.followup.send(
                embed=embed,
                view=discord.ui.View().add_item(
                    discord.ui.Button(label="Pay $9.99", url=checkout['checkout_url'], style=discord.ButtonStyle.link)
                )
            )
            return
        
        # Dev bypass
        await interaction.response.defer(ephemeral=True)
        
        result = await self.create_pack(youtube_url, "gold", interaction.user.id, bypass_payment=True)
        
        if not result["success"]:
            await interaction.followup.send(f"❌ {result['error']}")
            return
        
        # Send confirmation
        embed = discord.Embed(
            title="🎵 Gold Pack Created!",
            description=f"Added to your inventory and listed in marketplace for $6.99",
            color=discord.Color.gold()
        )
        embed.set_footer(text="✨ Dev: Payment bypassed")
        embed.add_field(name="Pack ID", value=result["pack_id"], inline=False)
        embed.add_field(name="🌟 Hero Song", value=f"{result['hero_card']['name']}\n👁️ {result['hero_card']['views']:,} views", inline=False)
        
        for i, card in enumerate(result["cards"][1:], 1):
            embed.add_field(name=f"{i}. {card['name']}", value=f"👁️ {card['views']:,} views", inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="test_pack", description="Test if pack creation cog is loaded")
    async def test_pack(self, interaction: Interaction):
        """Test command to verify cog is loaded"""
        await interaction.response.send_message("✅ Pack creation cog is working!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PackCreation(bot))
