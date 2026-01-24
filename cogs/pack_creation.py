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
import uuid
import json
import random

# Try to import stripe_manager, but don't fail if it doesn't work
try:
    from stripe_payments import stripe_manager
except ImportError as e:
    print(f"⚠️ Could not import stripe_manager: {e}")
    stripe_manager = None

DEV_USER_IDS = [int(uid.strip()) for uid in os.getenv("DEV_USER_IDS", "").split(",") if uid.strip()]

if DEV_USER_IDS:
    print(f"✅ DEV_USER_IDS loaded: {DEV_USER_IDS}")
else:
    print("⚠️ No DEV_USER_IDS configured - all users will be charged")

class PackCreation(commands.Cog):
    """URL-based pack creation system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None  # Initialize later to prevent hanging
        self.youtube = None
    
    async def cog_load(self):
        """Initialize YouTube API and database when cog loads"""
        print("🔥 PackCreation cog is loading!")
        
        try:
            self.db = DatabaseManager()
            print("✅ Database initialized for pack creation")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            self.db = None
        
        try:
            youtube_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")
            if youtube_key:
                self.youtube = build("youtube", "v3", developerKey=youtube_key)
                print(f"✅ YouTube API initialized for pack creation: {youtube_key[:10]}...")
            else:
                print("❌ No YouTube API key found in environment")
                self.youtube = None
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
                print(f"🔍 Fetching YouTube video details for ID: {video_id}")
                request = self.youtube.videos().list(
                    part="snippet,statistics",
                    id=video_id
                )
                result = request.execute()
                print(f"✅ YouTube API response received: {len(result.get('items', []))} items")
                return result
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                print(f"❌ Error type: {type(e).__name__}")
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
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
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
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
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
    
    async def generate_additional_cards(self, video_data: Dict) -> List[Dict]:
        """Generate 4 additional cards with specified rarity distribution"""
        # 4.1 Generate additional cards with rarity distribution:
        # 1 Legendary, 2 Epic, 1 Rare
        
        # Get related videos from same channel
        related_videos = await self.get_channel_videos(
            video_data["channel_id"],
            exclude_ids=[video_data["video_id"]],
            max_results=50
        )
        
        if len(related_videos) < 4:
            # Fallback to random generation if not enough related videos
            return self._generate_fallback_cards(video_data)
        
        # Get previously generated IDs to avoid duplicates
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT generated_youtube_id FROM card_generation_log
                WHERE hero_artist = ? AND hero_song = ?
            """, (video_data["artist"], video_data["title"]))
            previously_generated = [row[0] for row in cursor.fetchall()]
        
        # Filter out duplicates
        available_videos = [v for v in related_videos if v["video_id"] not in previously_generated]
        
        if len(available_videos) < 4:
            available_videos = related_videos  # Allow duplicates if needed
        
        # Random select 4 videos
        random.shuffle(available_videos)
        selected_videos = available_videos[:4]
        
        # Get stats for selected videos
        video_ids = [v["video_id"] for v in selected_videos]
        stats_map = await self.get_video_stats_batch(video_ids)
        
        # Create cards with specified rarities
        additional_cards = []
        rarity_distribution = ["Legendary", "Epic", "Epic", "Rare"]
        
        for i, (video, target_rarity) in enumerate(zip(selected_videos, rarity_distribution)):
            stats = stats_map.get(video["video_id"], {"views": 0, "likes": 0})
            card = self.create_card(video, stats)
            
            # Override rarity to match distribution
            card["rarity"] = target_rarity
            additional_cards.append(card)
        
        return additional_cards
    
    def _generate_fallback_cards(self, video_data: Dict) -> List[Dict]:
        """Generate fallback cards when YouTube API fails"""
        # Create deterministic cards based on hero video
        base_name = video_data["title"]
        additional_cards = []
        
        rarity_distribution = ["Legendary", "Epic", "Epic", "Rare"]
        suffixes = ["Remix", "Live", "Acoustic", "Instrumental"]
        
        for rarity, suffix in zip(rarity_distribution, suffixes):
            card = {
                "name": f"{base_name} ({suffix})",
                "artist": video_data["artist"],
                "rarity": rarity,
                "youtube_video_id": f"fallback_{video_data['video_id']}_{suffix.lower()}",
                "youtube_url": video_data.get("youtube_url", ""),
                "image_url": video_data.get("thumbnail", ""),
                "card_type": "song",
                "era": "Modern",
                "impact": 80 if rarity == "Legendary" else 70 if rarity == "Epic" else 60,
                "skill": 80 if rarity == "Legendary" else 70 if rarity == "Epic" else 60,
                "longevity": 80 if rarity == "Legendary" else 70 if rarity == "Epic" else 60,
                "culture": 80 if rarity == "Legendary" else 70 if rarity == "Epic" else 60,
                "hype": 80 if rarity == "Legendary" else 70 if rarity == "Epic" else 60,
                "views": video_data.get("views", 1000000) // (2 if rarity == "Legendary" else 3 if rarity == "Epic" else 4),
                "likes": video_data.get("likes", 50000) // (2 if rarity == "Legendary" else 3 if rarity == "Epic" else 4)
            }
            additional_cards.append(card)
        
        return additional_cards
    
    async def finalize_gold_pack(self, user_id: int, hero_card: Dict, additional_cards: List[Dict], youtube_url: str) -> str:
        """6.1 Finalize Pack & Store"""
        
        # Combine all cards
        all_cards = [hero_card] + additional_cards
        
        # Database transaction
        pack_id = f"gold_pack_{uuid.uuid4().hex[:8]}"
        cards_json = json.dumps(all_cards)
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # 6.1 Save the pack contents in the database
                cursor.execute("""
                    INSERT INTO creator_packs (
                        pack_id, creator_id, name, description, pack_size, 
                        status, cards_data, price, pack_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    user_id,
                    f"{hero_card['name']} Gold Pack",
                    f"Featured: {hero_card['name']} + 4 additional cards",
                    5,
                    "live",  # 6.1 status: live
                    cards_json,
                    9.99,   # Gold pack price
                    "gold"
                ))
                
                # 6.2 Publish the pack entry into marketplace subsystem
                cursor.execute("""
                    INSERT INTO marketplace (pack_id, price, stock, visibility, filters)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    9.99,
                    "unlimited",
                    "public",  # 6.2 Visibility flags
                    json.dumps({
                        "rarity": "gold",
                        "video_attributes": {
                            "hero_title": hero_card["name"],
                            "hero_artist": hero_card["artist"]
                        }
                    })  # 6.2 Filters
                ))
                
                # Add to creator's inventory
                cursor.execute("""
                    INSERT INTO user_packs (user_id, pack_id, acquired_at)
                    VALUES (?, ?, datetime('now'))
                """, (user_id, pack_id))
                
                # Log generation for duplicate prevention
                for card in additional_cards:
                    if card.get("youtube_video_id") and not card["youtube_video_id"].startswith("fallback"):
                        cursor.execute("""
                            INSERT INTO card_generation_log (hero_artist, hero_song, generated_youtube_id)
                            VALUES (?, ?, ?)
                        """, (hero_card["artist"], hero_card["name"], card["youtube_video_id"]))
                
                conn.commit()
                print(f"✅ Gold pack {pack_id} finalized and stored")
                
        except Exception as e:
            print(f"❌ Database error finalizing pack: {e}")
            raise e
        
        return pack_id

    @app_commands.command(name="test_pack", description="Test if pack creation cog is loaded")
    async def test_pack(self, interaction: Interaction):
        """Test command to verify cog is loaded"""
        await interaction.response.send_message("✅ Pack creation cog is working!", ephemeral=True)
    
    @app_commands.command(name="debug_commands", description="Debug - show all commands in this cog")
    async def debug_commands(self, interaction: Interaction):
        """Debug command to show all commands"""
        commands = []
        for cmd in self.bot.tree.walk_commands():
            if cmd.cog and cmd.cog.__class__.__name__ == "PackCreation":
                commands.append(cmd.name)
        
        await interaction.response.send_message(f"PackCreation commands: {commands}", ephemeral=True)
    
    @app_commands.command(name="test_url", description="Test YouTube URL parsing")
    @app_commands.describe(url="YouTube URL to test")
    async def test_url(self, interaction: Interaction, url: str):
        """Test URL parsing"""
        video_id = self.parse_youtube_url(url)
        
        if not video_id:
            await interaction.response.send_message(f"❌ Invalid YouTube URL: {url}", ephemeral=True)
            return
        
        await interaction.response.send_message(f"✅ Extracted video ID: {video_id}", ephemeral=True)
        
        # Try to get video details
        if self.youtube:
            try:
                details = await self.get_video_details(video_id)
                if details:
                    await interaction.followup.send(
                        f"🎵 Found: {details['title']} by {details['artist']}\n"
                        f"👁️ {details['views']:,} views",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send("❌ Could not fetch video details", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error fetching details: {e}", ephemeral=True)
        else:
            await interaction.followup.send("❌ YouTube API not initialized", ephemeral=True)
    
    @app_commands.command(name="ping_pack", description="Test if pack creation cog is loaded")
    async def ping_pack(self, interaction: Interaction):
        """Simple test command"""
        await interaction.response.send_message("✅ Pack creation cog is working!", ephemeral=True)


async def setup(bot):
    cog = PackCreation(bot)
    await bot.add_cog(cog)
    print(f"🔥 PackCreation cog added with {len([cmd for cmd in cog.walk_commands()])} commands")
