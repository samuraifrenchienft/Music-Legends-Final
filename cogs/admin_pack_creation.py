# cogs/admin_pack_creation.py
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
        """Get video details from YouTube video ID - async safe"""
        if not self.youtube:
            print("❌ YouTube API not available")
            return None
        
        loop = asyncio.get_running_loop()
        
        def _get_details():
            """Blocking YouTube API call"""
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
            "description": snippet.get("description", "")[:200],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0))
        }
    
    async def get_related_videos(self, channel_id: str, artist_name: str, exclude_ids: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """Get related videos from same channel - async safe"""
        if not self.youtube:
            return []
        
        loop = asyncio.get_running_loop()
        
        def _get_channel_videos():
            """Blocking YouTube API call - search channel's videos"""
            try:
                # Search for videos from the same channel
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
        
        result = await loop.run_in_executor(None, _get_channel_videos)
        
        if not result or not result.get("items"):
            print(f"⚠️ No videos found for channel {channel_id}")
            return []
        
        related = []
        for item in result["items"]:
            vid_id = item["id"]["videoId"]
            if vid_id not in exclude_ids:
                snippet = item["snippet"]
                related.append({
                    "video_id": vid_id,
                    "title": snippet["title"],
                    "artist": snippet["channelTitle"],
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "description": snippet.get("description", "")[:200]
                })
        
        print(f"✅ Found {len(related)} related videos from {artist_name}'s channel")
        return related
    
    def get_previously_generated_ids(self, hero_artist: str, hero_song: str) -> List[str]:
        """Get list of previously generated YouTube IDs for this hero to prevent duplicates"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT generated_youtube_id FROM card_generation_log
                WHERE hero_artist = ? AND hero_song = ?
            """, (hero_artist, hero_song))
            return [row[0] for row in cursor.fetchall()]
    
    def log_generated_cards(self, hero_artist: str, hero_song: str, youtube_ids: List[str]):
        """Log generated cards to prevent future duplicates"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for youtube_id in youtube_ids:
                cursor.execute("""
                    INSERT INTO card_generation_log (hero_artist, hero_song, generated_youtube_id)
                    VALUES (?, ?, ?)
                """, (hero_artist, hero_song, youtube_id))
            conn.commit()
    
    def select_random_unique_cards(self, available_pool: List[Dict], count: int = 4) -> List[Dict]:
        """Select random unique cards from available pool"""
        import random
        
        if len(available_pool) < count:
            print(f"⚠️ Only {len(available_pool)} cards available, need {count}")
            return available_pool
        
        # Shuffle pool
        shuffled = available_pool.copy()
        random.shuffle(shuffled)
        
        # Select first 4 unique cards
        selected = []
        seen_ids = set()
        
        for card in shuffled:
            if card["video_id"] not in seen_ids:
                selected.append(card)
                seen_ids.add(card["video_id"])
                
                if len(selected) == count:
                    break
        
        return selected
    
    async def get_video_stats_batch(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get statistics for multiple videos - async safe"""
        if not self.youtube or not video_ids:
            return {}
        
        loop = asyncio.get_running_loop()
        
        def _get_stats():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.videos().list(
                    part="statistics",
                    id=",".join(video_ids[:50])  # API limit
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
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0))
            }
        
        return stats_map
    
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
        
        print(f"🎵 Creating card for: {song_data.get('title', 'Unknown')} by {song_data.get('artist', 'Unknown')}")
        
        card = {
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
            "likes": stats["likes"],
            "video_id": song_data["video_id"]  # Add both field names for compatibility
        }
        
        print(f"✅ Card created: {card['name']} ({card['rarity']}) - {card['views']:,} views")
        return card
    
    @app_commands.command(name="pack_create", description="Create a new pack with YouTube songs")
    async def pack_create(self, interaction: Interaction):
        """Open modal to start pack creation"""
        modal = ArtistSearchModal(self)
        await interaction.response.send_modal(modal)
    
    async def search_youtube_songs(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for songs on YouTube - async safe"""
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
                    videoCategoryId="10",
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
    
    async def _create_pack_from_hero(self, interaction: Interaction, hero_song: Dict, artist: str):
        """Create pack from selected hero song"""
        
        try:
            hero_artist = artist
            hero_song_name = hero_song["title"]
            
            # Get hero song stats
            hero_stats = await self.get_video_stats(hero_song["video_id"])
            if not hero_stats:
                hero_stats = {"views": 0, "likes": 0, "comments": 0}
            
            # Create hero card
            hero_card = await self.create_song_card(hero_song, hero_stats)
            hero_card["is_hero"] = True
            
            # STEP 3: Get related videos pool (50 videos)
            related_pool = await self.get_related_videos(
                hero_song["video_id"],
                exclude_ids=[hero_song["video_id"]],
                max_results=50
            )
            
            if len(related_pool) < 4:
                await interaction.followup.send(
                    f"❌ Could not find enough related videos (found {len(related_pool)}, need 4)"
                )
                return
            
            # STEP 4: Check previously generated cards
            previously_generated = self.get_previously_generated_ids(hero_artist, hero_song_name)
            
            # Filter out previously generated
            available_pool = [
                card for card in related_pool 
                if card["video_id"] not in previously_generated
            ]
            
            # If not enough unique cards, allow duplicates with warning
            if len(available_pool) < 4:
                print(f"⚠️ Only {len(available_pool)} unique cards, allowing duplicates")
                available_pool = related_pool
            
            # STEP 5: Select 4 random unique cards
            selected_cards = self.select_random_unique_cards(available_pool, count=4)
            
            if len(selected_cards) < 4:
                await interaction.followup.send(
                    f"❌ Could not select 4 unique cards (only found {len(selected_cards)})"
                )
                return
            
            # Get stats for selected cards
            cards = [hero_card]
            for song in selected_cards:
                stats = await self.get_video_stats(song["video_id"])
                if not stats:
                    stats = {"views": 0, "likes": 0, "comments": 0}
                
                card = await self.create_song_card(song, stats)
                cards.append(card)
            
            # STEP 6: Create pack in database with transaction
            pack_id = f"pack_{uuid.uuid4().hex[:8]}"
            cards_json = json.dumps(cards)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                try:
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
                    
                    # STEP 7: Add pack to creator's inventory
                    cursor.execute("""
                        INSERT INTO user_packs (user_id, pack_id, acquired_at)
                        VALUES (?, ?, datetime('now'))
                    """, (interaction.user.id, pack_id))
                    
                    # STEP 8: List in marketplace
                    cursor.execute("""
                        INSERT INTO marketplace (pack_id, price, stock)
                        VALUES (?, ?, ?)
                    """, (pack_id, 6.99, "unlimited"))
                    
                    # Log generated cards to prevent duplicates
                    generated_ids = []
                    for card in cards[1:]:  # Skip hero card
                        if "youtube_video_id" in card:
                            generated_ids.append(card["youtube_video_id"])
                        elif "video_id" in card:  # Try alternative field name
                            generated_ids.append(card["video_id"])
                    
                    print(f"📝 Logging {len(generated_ids)} generated cards")
                    self.log_generated_cards(hero_artist, hero_song_name, generated_ids)
                    
                    conn.commit()
                    print(f"✅ Pack {pack_id} created successfully")
                    
                except Exception as e:
                    conn.rollback()
                    print(f"❌ Database error: {e}")
                    await interaction.followup.send(f"❌ Failed to create pack: {e}")
                    return
            
            # STEP 9: Send confirmation
            is_dev = self.is_dev(interaction.user.id)
            
            embed = discord.Embed(
                title="🎵 Gold Pack Created!",
                description=f"**{hero_song['title']} Pack**\n\nPack added to your inventory and listed in marketplace for $6.99",
                color=discord.Color.gold()
            )
            
            if is_dev:
                embed.set_footer(text="✨ Dev: Payment bypassed")
            
            embed.add_field(name="Pack ID", value=pack_id, inline=False)
            embed.set_thumbnail(url=hero_card.get("image_url", ""))
            
            embed.add_field(
                name="🌟 Hero Card",
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
            
        except Exception as e:
            print(f"❌ Error creating pack: {e}")
            await interaction.followup.send(f"❌ Error creating pack: {e}")


class ArtistSearchModal(ui.Modal, title="Create Pack - Search Artist"):
    """Modal to collect artist name for pack creation"""
    
    artist_name = ui.TextInput(
        label="Artist Name",
        placeholder="e.g., Drake, Taylor Swift, Bad Bunny",
        required=True,
        max_length=100
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            artist = self.artist_name.value.strip()
            print(f"🔍 Searching for songs by: {artist}")
            
            # Search YouTube for artist's songs
            songs = await self.cog.search_youtube_songs(f"{artist} official music video", max_results=10)
            
            if not songs:
                await interaction.followup.send(f"❌ No songs found for {artist}")
                return
            
            print(f"🎵 Found {len(songs)} songs for {artist}")
            
            # Show song selection UI
            view = SongSelectionView(songs, artist, self.cog, interaction.user.id)
            
            embed = discord.Embed(
                title=f"🎵 Select Song for {artist} Pack",
                description="Choose ONE song to be the featured hero card.\nBot will auto-generate 4 related song cards.",
                color=discord.Color.blue()
            )
            
            for i, song in enumerate(songs[:5], 1):
                embed.add_field(
                    name=f"{i}. {song['title']}",
                    value=f"By: {song['artist']}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Error in modal submission: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class SongSelectionView(ui.View):
    """UI for selecting hero song"""
    
    def __init__(self, songs: List[Dict], artist: str, cog, user_id: int):
        super().__init__(timeout=180)
        self.songs = songs
        self.artist = artist
        self.cog = cog
        self.user_id = user_id
        
        # Add buttons for top 5 songs
        for i, song in enumerate(songs[:5]):
            button = ui.Button(
                label=f"{i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"select_song_{i}"
            )
            button.callback = self.create_callback(song, i)
            self.add_item(button)
    
    def create_callback(self, hero_song: Dict, index: int):
        async def callback(interaction: Interaction):
            await interaction.response.defer()
            
            # Check if dev (bypass payment)
            is_dev = self.cog.is_dev(self.user_id)
            
            if not is_dev:
                # Create Stripe checkout for $9.99
                checkout = stripe_manager.create_pack_creation_checkout(
                    creator_id=self.user_id,
                    song_query=f"{self.artist} - {hero_song['title']}"
                )
                
                if not checkout['success']:
                    await interaction.followup.send(f"❌ Payment error: {checkout['error']}")
                    return
                
                # Send payment link
                embed = discord.Embed(
                    title="💳 Pack Creation Payment",
                    description=f"**Hero Song:** {hero_song['title']}\n**Price:** $9.99\n\nClick the link below to complete payment.",
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
            
            # Dev bypass - create pack immediately
            await self.cog._create_pack_from_hero(interaction, hero_song, self.artist)
        
        return callback


async def setup(bot):
    await bot.add_cog(AdminPackCreation(bot))
