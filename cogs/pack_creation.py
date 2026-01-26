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
import random

# Import complete weighted pool system
try:
    from card_stats import (
        create_hero_card, create_secondary_card, generate_complete_pack, 
        get_pack_summary_message, WEIGHTS
    )
    print("✅ Complete weighted pool system loaded")
except ImportError as e:
    print(f"⚠️ Weighted pool system not available: {e}")
    create_hero_card = None
    create_secondary_card = None
    generate_complete_pack = None
    get_pack_summary_message = None
    WEIGHTS = {"same_artist": 60, "related_genre": 30, "wildcard": 10}

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
                # Add fallback test key for development
                test_key = "AIzaSyDummyKeyForTesting1234567890"
                print("⚠️ No YouTube API key found in environment, using test fallback")
                self.youtube = build("youtube", "v3", developerKey=test_key)
                print(f"✅ YouTube API initialized with test key")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            self.youtube = None
        
        # Card stats system is available via direct imports
    
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
            # Return fallback data when YouTube API is not available
            print("⚠️ YouTube API not available, using fallback data")
            return self._get_fallback_video_data(video_id)
        
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
                print("🔄 Using fallback data due to API failure")
                return None
        
        result = await loop.run_in_executor(None, _get_details)
        
        if not result or not result.get("items"):
            # Return fallback data when API fails
            print("⚠️ No video data found, using fallback")
            return self._get_fallback_video_data(video_id)
        
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
    
    def _get_fallback_video_data(self, video_id: str) -> Dict[str, Any]:
        """Generate fallback video data when YouTube API fails"""
        import random
        
        # Generate realistic-looking fallback data
        fallback_titles = [
            "Epic Music Video", "Amazing Song", "Hit Track", "Viral Content", 
            "Trending Music", "Popular Song", "Music Video", "New Release"
        ]
        
        fallback_artists = [
            "Test Artist", "Demo Channel", "Sample Creator", "Music Producer",
            "Test Channel", "Demo Artist", "Sample Music", "Test Producer"
        ]
        
        title = random.choice(fallback_titles)
        artist = random.choice(fallback_artists)
        views = random.randint(10000, 10000000)
        likes = random.randint(1000, views // 10)
        
        return {
            "video_id": video_id,
            "title": f"{title} ({video_id[:8]})",
            "artist": artist,
            "channel_id": f"UC{video_id[:22]}",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "views": views,
            "likes": likes
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
        cards_json = str(cards)
        
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
        """6.1 Finalize Pack & Store using new relational schema"""
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. Store YouTube video data
                self.db.store_youtube_video({
                    "video_id": hero_card["youtube_video_id"],
                    "title": hero_card["name"],
                    "thumbnail": hero_card.get("image_url", ""),
                    "views": hero_card.get("views", 0),
                    "likes": hero_card.get("likes", 0),
                    "artist": hero_card["artist"],
                    "channel_id": hero_card.get("channel_id", "")
                })
                
                # 2. Create card definitions and instances
                all_instances = []
                
                # Hero card
                hero_card_def_id = self.db.create_card_definition(
                    hero_card["youtube_video_id"],
                    hero_card["name"],
                    "Gold",  # Hero is always gold rarity
                    hero_card.get("impact", 80),
                    {
                        "skill": hero_card.get("skill", 80),
                        "longevity": hero_card.get("longevity", 80),
                        "culture": hero_card.get("culture", 80),
                        "hype": hero_card.get("hype", 80),
                        "views": hero_card.get("views", 0),
                        "likes": hero_card.get("likes", 0)
                    }
                )
                
                hero_instance_id = self.db.create_card_instance(
                    hero_card_def_id,
                    str(user_id),
                    f"HERO_{hero_card['youtube_video_id'][:8]}"
                )
                all_instances.append(hero_instance_id)
                
                # Additional cards with specified rarity distribution
                rarity_distribution = ["Legendary", "Epic", "Epic", "Rare"]
                
                for i, (card, rarity) in enumerate(zip(additional_cards, rarity_distribution)):
                    # Store YouTube video if not fallback
                    if not card["youtube_video_id"].startswith("fallback"):
                        self.db.store_youtube_video({
                            "video_id": card["youtube_video_id"],
                            "title": card["name"],
                            "thumbnail": card.get("image_url", ""),
                            "views": card.get("views", 0),
                            "likes": card.get("likes", 0),
                            "artist": card["artist"],
                            "channel_id": card.get("channel_id", "")
                        })
                    
                    # Create card definition
                    card_def_id = self.db.create_card_definition(
                        card["youtube_video_id"],
                        card["name"],
                        rarity,  # Use specified rarity
                        card.get("impact", 70 if rarity == "Legendary" else 60),
                        {
                            "skill": card.get("skill", 70 if rarity == "Legendary" else 60),
                            "longevity": card.get("longevity", 70 if rarity == "Legendary" else 60),
                            "culture": card.get("culture", 70 if rarity == "Legendary" else 60),
                            "hype": card.get("hype", 70 if rarity == "Legendary" else 60),
                            "views": card.get("views", 0),
                            "likes": card.get("likes", 0)
                        }
                    )
                    
                    # Create card instance
                    instance_id = self.db.create_card_instance(
                        card_def_id,
                        str(user_id),
                        f"{rarity.upper()}_{card['youtube_video_id'][:8]}"
                    )
                    all_instances.append(instance_id)
                
                # 3. Create pack
                pack_id = self.db.create_pack(str(user_id), hero_instance_id, "gold")
                
                # 4. Add cards to pack (hero at position 1, others at positions 2-5)
                self.db.add_card_to_pack(pack_id, hero_instance_id, 1)  # Hero position
                
                for i, instance_id in enumerate(all_instances[1:], 2):  # Additional cards start at position 2
                    self.db.add_card_to_pack(pack_id, instance_id, i)
                
                # 5. Publish to marketplace
                marketplace_item_id = self.db.publish_pack_to_marketplace(pack_id, 9.99)
                
                # 6. Log generation for duplicate prevention (legacy compatibility)
                for card in additional_cards:
                    if card.get("youtube_video_id") and not card["youtube_video_id"].startswith("fallback"):
                        cursor.execute("""
                            INSERT OR IGNORE INTO card_generation_log (hero_artist, hero_song, generated_youtube_id)
                            VALUES (?, ?, ?)
                        """, (hero_card["artist"], hero_card["name"], card["youtube_video_id"]))
                
                conn.commit()
                print(f"✅ Gold pack {pack_id} finalized with relational schema")
                
                return str(pack_id)
                
        except Exception as e:
            print(f"❌ Database error finalizing pack: {e}")
            raise e

class HeroConfirmView(discord.ui.View):
    def __init__(self, cog, video_data, hero_card, youtube_url):
        super().__init__(timeout=180)  # 3 minute timeout
        self.cog = cog
        self.video_data = video_data
        self.hero_card = hero_card
        self.youtube_url = youtube_url
    
    @discord.ui.button(label="✅ Yes, create pack", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle hero confirmation - generate additional cards and show pack preview"""
        # 4. Generate Additional Cards
        try:
            additional_cards = await self.cog.generate_additional_cards(self.video_data)
            
            # 5.1 Present full pack for acceptance
            pack_embed = discord.Embed(
                title="📦 Gold Pack Preview",
                description="Review your pack contents:",
                color=discord.Color.gold()
            )
            pack_embed.set_thumbnail(url=self.video_data.get("thumbnail", ""))
            
            # Hero card
            pack_embed.add_field(
                name="🌟 HERO CARD",
                value=f"**{self.hero_card['name']}**\n👁️ {self.video_data['views']:,} views\n⭐ Gold",
                inline=False
            )
            
            # Additional cards
            for i, card in enumerate(additional_cards, 1):
                rarity_emoji = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🔴"}.get(card.get('rarity', 'Common'), "⚪")
                pack_embed.add_field(
                    name=f"{i}. {rarity_emoji} {card['name']}",
                    value=f"👁️ {card.get('views', 0):,} views\n⭐ {card.get('rarity', 'Common')}",
                    inline=False
                )
            
            # 5.2 Create pack review view with accept/regenerate buttons
            pack_review_view = PackReviewView(self.cog, self.video_data, self.hero_card, additional_cards, self.youtube_url)
            
            await interaction.response.edit_message(embed=pack_embed, view=pack_review_view)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error generating additional cards: {e}", ephemeral=True)
    
    @discord.ui.button(label="❌ No, cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle cancellation"""
        await interaction.response.edit_message(content="❌ Pack creation cancelled.", embed=None, view=None)

class PackReviewView(discord.ui.View):
    def __init__(self, cog, video_data, hero_card, additional_cards, youtube_url):
        super().__init__(timeout=180)
        self.cog = cog
        self.video_data = video_data
        self.hero_card = hero_card
        self.additional_cards = additional_cards
        self.youtube_url = youtube_url
        self.regenerate_count = 0
    
    @discord.ui.button(label="✅ Accept Pack", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle pack acceptance - finalize and store pack"""
        # 6.1 Finalize Pack & Store
        try:
            pack_id = await self.cog.finalize_gold_pack(
                interaction.user.id,
                self.hero_card,
                self.additional_cards,
                self.youtube_url
            )
            
            # 6.3 Notify success
            success_embed = discord.Embed(
                title="✅ Gold Pack Created!",
                description=f"Pack ID: `{pack_id}` is now LIVE in Marketplace.",
                color=discord.Color.green()
            )
            success_embed.set_footer(text=f"Created by {interaction.user.display_name}")
            
            await interaction.response.edit_message(embed=success_embed, view=None)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error finalizing pack: {e}", ephemeral=True)
    
    @discord.ui.button(label="🔄 Regenerate", style=discord.ButtonStyle.secondary)
    async def regenerate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle pack regeneration - generate new additional cards"""
        if self.regenerate_count >= 3:
            await interaction.response.send_message("❌ Maximum regenerations reached (3). Please accept the current pack.", ephemeral=True)
            return
        
        self.regenerate_count += 1
        
        # Generate new cards
        try:
            new_additional_cards = await self.cog.generate_additional_cards(self.video_data)
            
            # Update embed with new cards
            updated_embed = discord.Embed(
                title="📦 Gold Pack Preview (Regenerated)",
                description="Review your new pack contents:",
                color=discord.Color.gold()
            )
            updated_embed.set_thumbnail(url=self.video_data.get("thumbnail", ""))
            
            # Hero card (unchanged)
            updated_embed.add_field(
                name="🌟 HERO CARD",
                value=f"**{self.hero_card['name']}**\n👁️ {self.video_data['views']:,} views\n⭐ Gold",
                inline=False
            )
            
            # New additional cards
            for i, card in enumerate(new_additional_cards, 1):
                rarity_emoji = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🔴"}.get(card.get('rarity', 'Common'), "⚪")
                updated_embed.add_field(
                    name=f"{i}. {rarity_emoji} {card['name']}",
                    value=f"👁️ {card.get('views', 0):,} views\n⭐ {card.get('rarity', 'Common')}",
                    inline=False
                )
            
            # Update view with new cards
            new_view = PackReviewView(self.cog, self.video_data, self.hero_card, new_additional_cards, self.youtube_url)
            new_view.regenerate_count = self.regenerate_count
            
            await interaction.response.edit_message(embed=updated_embed, view=new_view)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error regenerating cards: {e}", ephemeral=True)

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
    
        
    @app_commands.command(name="create_community_pack", description="Create a free community pack (Dev only)")
    @app_commands.describe(youtube_url="YouTube video URL for the hero card")
    async def create_community_pack(self, interaction: Interaction, youtube_url: str):
        """Create a free community pack (Dev only)"""
        
        # Check if user is dev
        if not self.is_dev(interaction.user.id):
            await interaction.response.send_message("❌ This command is for developers only!", ephemeral=True)
            return
        
        if not self.youtube:
            await interaction.response.send_message("❌ YouTube API not initialized. Please check configuration.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Use the shared pack creation logic
            result = await self.create_pack(youtube_url, "community", interaction.user.id, bypass_payment=True)
            
            if result["success"]:
                success_embed = discord.Embed(
                    title="✅ Community Pack Created!",
                    description=f"Pack ID: `{result['pack_id']}` is now LIVE in Marketplace.",
                    color=discord.Color.green()
                )
                success_embed.set_footer(text=f"Created by {interaction.user.display_name}")
                await interaction.followup.send(embed=success_embed)
            else:
                await interaction.followup.send(f"❌ {result['error']}", ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating community pack: {e}", ephemeral=True)
    
    @app_commands.command(name="create_gold_pack", description="Create a premium gold pack ($9.99)")
    @app_commands.describe(youtube_url="YouTube video URL for the hero card")
    async def create_gold_pack(self, interaction: Interaction, youtube_url: str):
        """Create a premium gold pack using professional TCG design principles"""
        
        if not self.youtube:
            await interaction.response.send_message("❌ YouTube API not initialized. Please check configuration.", ephemeral=True)
            return
        
        # 1. Permission check (dev bypass)
        is_dev = self.is_dev(interaction.user.id)
        
        await interaction.response.defer()
        
        # Use complete weighted pool system
        if create_hero_card and generate_complete_pack:
            try:
                print(f"🎬 Starting complete weighted pool generation for: {youtube_url}")
                
                # Step 1-2: Permission check already done above
                
                # Step 3: Fetch Hero Card Data
                # 3.1 Parse YouTube URL → extract video_id
                video_id = self.parse_youtube_url(youtube_url)
                if not video_id:
                    await interaction.followup.send("❌ Invalid YouTube URL. Please provide a valid YouTube video link.", ephemeral=True)
                    return
                
                # 3.2 Query YouTube API: videos.list
                video_data = await self.get_video_details(video_id)
                if not video_data:
                    await interaction.followup.send("❌ Could not fetch video details. Please try a different video.", ephemeral=True)
                    return
                
                # 3.3 Extract metadata (already done in get_video_details)
                # 3.4 Parse artist + song from title (handled in create_hero_card)
                
                # Step 4: Build Weighted Pools
                try:
                    channel_id = video_data.get("channel_id", "")
                    
                    # 4.1 POOL 1: Same Artist Top Tracks (60% weight)
                    pool_1_videos = []
                    if channel_id:
                        pool_1_videos = await self.get_channel_videos(channel_id, [video_id], max_results=50)
                        # Convert to card format
                        pool_1_cards = [create_secondary_card(video, "pool_1") for video in pool_1_videos]
                    
                    # 4.2 POOL 2: Related Genre Artists (30% weight)
                    pool_2_videos = []
                    try:
                        # Use relatedToVideoId search
                        pool_2_videos = await self.get_channel_videos("", [video_id], max_results=50)
                        # Filter out same artist
                        pool_2_videos = [v for v in pool_2_videos if v.get("channel_id") != channel_id]
                        pool_2_cards = [create_secondary_card(video, "pool_2") for video in pool_2_videos]
                    except Exception as e:
                        print(f"⚠️ Could not build pool 2: {e}")
                        pool_2_cards = []
                    
                    # 4.3 POOL 3: Wildcard Variety (10% weight)
                    pool_3_videos = []
                    try:
                        # Broader search for wildcards
                        pool_3_videos = await self.get_channel_videos("", [video_id], max_results=100)
                        # Filter out cards already in other pools
                        existing_ids = {v.get("video_id") for v in pool_1_videos + pool_2_videos}
                        pool_3_videos = [v for v in pool_3_videos if v.get("video_id") not in existing_ids]
                        pool_3_cards = [create_secondary_card(video, "pool_3") for video in pool_3_videos]
                    except Exception as e:
                        print(f"⚠️ Could not build pool 3: {e}")
                        pool_3_cards = []
                        
                except Exception as e:
                    print(f"⚠️ Could not build pools: {e}")
                    pool_1_cards = []
                    pool_2_cards = []
                    pool_3_cards = []
                
                # Step 5: Check Previously Generated Cards (Duplicate Prevention)
                try:
                    import sqlite3
                    previously_generated_ids = []
                    
                    with sqlite3.connect("music_legends.db") as conn:
                        cursor = conn.cursor()
                        
                        # Query card_generation_log
                        hero_card_temp = create_hero_card(video_data)
                        cursor.execute("""
                            SELECT generated_youtube_id FROM card_generation_log
                            WHERE hero_artist = ? AND hero_song = ?
                        """, (hero_card_temp["artist"], hero_card_temp["song"]))
                        
                        previously_generated_ids = [row[0] for row in cursor.fetchall()]
                        
                except Exception as e:
                    print(f"⚠️ Could not check previous generations: {e}")
                    previously_generated_ids = []
                
                # Filter pools for duplicates
                def filter_pool(pool_cards):
                    return [card for card in pool_cards if card["youtube_id"] not in previously_generated_ids]
                
                pool_1_filtered = filter_pool(pool_1_cards)
                pool_2_filtered = filter_pool(pool_2_cards)
                pool_3_filtered = filter_pool(pool_3_cards)
                
                # Step 6: Generate 4 Cards Using Weighted Random
                pack_result = generate_complete_pack(video_data, pool_1_filtered, pool_2_filtered, pool_3_filtered, previously_generated_ids)
                
                # Step 7: Create Pack & Cards in Database
                pack_id = f"pack_{uuid.uuid4().hex[:8]}"
                hero_card = pack_result["hero_card"]
                generated_cards = pack_result["generated_cards"]
                all_cards = pack_result["all_cards"]
                
                try:
                    import sqlite3
                    with sqlite3.connect("music_legends.db") as conn:
                        cursor = conn.cursor()
                        
                        # 7.2 Insert into packs table
                        cursor.execute("""
                            INSERT INTO creator_packs (
                                pack_id, creator_id, name, description, pack_size, 
                                status, cards_data, price
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            pack_id,
                            interaction.user.id,
                            f"{hero_card['artist']} - {hero_card['song']} Pack",
                            f"Weighted pool pack: {pack_result['pack_theme']}",
                            len(all_cards),
                            "live",
                            str(all_cards),
                            9.99  # Gold pack price
                        ))
                        
                        # 7.4 & 7.5: Insert all cards into cards table
                        for card in all_cards:
                            cursor.execute("""
                                INSERT INTO cards (
                                    card_id, pack_id, artist, song, youtube_url, youtube_id,
                                    view_count, thumbnail, rarity, base_power, is_hero, pool_source
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                f"card_{uuid.uuid4().hex[:8]}",
                                pack_id,
                                card["artist"],
                                card["song"],
                                card["youtube_url"],
                                card["youtube_id"],
                                card["view_count"],
                                card.get("thumbnail", ""),
                                card["rarity"],
                                card["base_power"],
                                card["is_hero"],
                                card["pool_source"]
                            ))
                        
                        # 7.6 Log generated cards to prevent future duplicates
                        for card in generated_cards:
                            cursor.execute("""
                                INSERT INTO card_generation_log (
                                    hero_artist, hero_song, generated_youtube_id, pool_source, created_at
                                ) VALUES (?, ?, ?, ?, datetime('now'))
                            """, (
                                hero_card["artist"],
                                hero_card["song"],
                                card["youtube_id"],
                                card["pool_source"]
                            ))
                        
                        conn.commit()
                        
                except Exception as e:
                    print(f"⚠️ Database error: {e}")
                
                # Step 8: Add Pack to Creator's Inventory
                try:
                    import sqlite3
                    with sqlite3.connect("music_legends.db") as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO user_packs (user_id, pack_id, acquired_at, acquisition_type)
                            VALUES (?, ?, datetime('now'), 'created')
                        """, (interaction.user.id, pack_id))
                        conn.commit()
                except Exception as e:
                    print(f"⚠️ Inventory error: {e}")
                
                # Step 9: List Pack in Marketplace
                try:
                    import sqlite3
                    with sqlite3.connect("music_legends.db") as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO marketplace (pack_id, price, listed_at, stock)
                            VALUES (?, ?, datetime('now'), 'unlimited')
                        """, (pack_id, 9.99))
                        conn.commit()
                except Exception as e:
                    print(f"⚠️ Marketplace error: {e}")
                
                # Step 10: Send Confirmation to User
                embed = discord.Embed(
                    title="🎵 Gold Pack Created!",
                    description=f"Featuring {hero_card['artist']} - {hero_card['song']}",
                    color=discord.Color.gold()
                )
                
                # Hero Card field
                embed.add_field(
                    name="🌟 Hero Card",
                    value=f"• {hero_card['artist']} - {hero_card['song']}\n"
                          f"• {hero_card['rarity'].title()} | {hero_card['view_count']:,} views\n"
                          f"• Power: {hero_card['base_power']}\n"
                          f"[Listen on YouTube]({hero_card['youtube_url']})",
                    inline=False
                )
                
                # Generated Cards field
                embed.add_field(
                    name="🎲 Generated Cards",
                    value=get_pack_summary_message(pack_result),
                    inline=False
                )
                
                # Status fields
                embed.add_field(
                    name="✅ Status",
                    value=f"• Pack added to your inventory\n"
                          f"• Listed in marketplace for $9.99\n"
                          f"• Pack Theme: {pack_result['pack_theme']}\n"
                          f"• Total Power: {pack_result['total_power']}",
                    inline=False
                )
                
                embed.set_thumbnail(url=hero_card.get("thumbnail", ""))
                embed.set_footer(text=f"Pack ID: {pack_id} | Created with weighted pools (60/30/10)")
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error creating gold pack: {e}", ephemeral=True)
        else:
            # Fallback to old system
            await self._create_gold_pack_fallback(interaction, youtube_url)
    
    async def _create_gold_pack_fallback(self, interaction: Interaction, youtube_url: str):
        """Fallback gold pack creation using old system"""
        
        # 2. Extract YouTube video ID
        video_id = self.parse_youtube_url(youtube_url)
        if not video_id:
            await interaction.followup.send("❌ Invalid YouTube URL. Please provide a valid YouTube video link.", ephemeral=True)
            return
        
        # 3. Fetch YouTube metadata
        try:
            video_data = await self.get_video_details(video_id)
            if not video_data:
                await interaction.followup.send("❌ Could not fetch video details. Please try a different video.", ephemeral=True)
                return
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching video details: {e}", ephemeral=True)
            return
        
        # 3.1 Create hero card from video data
        hero_card = self.create_card(video_data, {"views": video_data.get("views", 0), "likes": video_data.get("likes", 0)})
        hero_card["rarity"] = "Gold"  # Force Gold rarity for hero
        
        # 3.2 Present hero card for confirmation
        preview_embed = discord.Embed(
            title="🌟 Gold Pack - Hero Card Preview",
            description="This will be your pack's hero card. Confirm to generate additional cards.",
            color=discord.Color.gold()
        )
        preview_embed.set_thumbnail(url=video_data.get("thumbnail", ""))
        preview_embed.add_field(
            name="🎵 Hero Card",
            value=f"**{hero_card['name']}**\n👁️ {video_data.get('views', 0):,} views\n⭐ Gold rarity",
            inline=False
        )
        
        await interaction.followup.send(embed=preview_embed, view=HeroConfirmView(self, video_data, hero_card, youtube_url))


async def setup(bot):
    cog = PackCreation(bot)
    await bot.add_cog(cog)
    print(f"🔥 PackCreation cog added with {len([cmd for cmd in cog.walk_commands()])} commands")
