# cogs/simple_pack_creation.py - Artist name-based pack creation with YouTube options
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3
from database import DatabaseManager
import uuid
import random
from googleapiclient.discovery import build
import asyncio

class VideoSelectionView(discord.ui.View):
    """View for selecting YouTube videos for pack creation"""
    
    def __init__(self, cog, videos, artist_name, pack_type, user):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.cog = cog
        self.videos = videos
        self.artist_name = artist_name
        self.pack_type = pack_type
        self.user = user
        self.current_page = 0
        self.videos_per_page = 5
        
        # Add navigation buttons
        self.add_item(discord.ui.Button(label="◀️ Previous", style=discord.ButtonStyle.secondary, custom_id="prev"))
        self.add_item(discord.ui.Button(label="▶️ Next", style=discord.ButtonStyle.secondary, custom_id="next"))
        
        # Add video selection buttons
        self.update_video_buttons()
    
    def update_video_buttons(self):
        """Update video selection buttons for current page"""
        # Remove old video buttons
        to_remove = []
        for child in self.children:
            if child.custom_id and child.custom_id.startswith("video_"):
                to_remove.append(child)
        
        for item in to_remove:
            self.remove_item(item)
        
        # Add new video buttons for current page
        start_idx = self.current_page * self.videos_per_page
        end_idx = min(start_idx + self.videos_per_page, len(self.videos))
        
        for i in range(start_idx, end_idx):
            video = self.videos[i]
            button_text = f"📹 {video['title'][:30]}..."
            
            button = discord.ui.Button(
                label=button_text,
                style=discord.ButtonStyle.primary,
                custom_id=f"video_{i}"
            )
            button.callback = self.create_video_callback(video, i)
            self.add_item(button)
    
    def create_video_callback(self, video, index):
        """Create callback for video selection"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("❌ You can't select videos for someone else's pack!", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Create the pack with selected video
            await self.cog.create_pack_from_video(
                interaction, video, self.artist_name, self.pack_type
            )
            
            # Disable all buttons after selection
            for child in self.children:
                child.disabled = True
            
            await interaction.edit_original_response(view=self)
        
        return callback
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original user to interact"""
        return interaction.user.id == self.user.id

class SimplePackCreation(commands.Cog):
    """Pack creation using artist names with YouTube video selection"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.youtube = None
    
    async def cog_load(self):
        """Initialize database and YouTube API when cog loads"""
        print("🔥 SimplePackCreation cog is loading!")
        
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
                print("✅ YouTube API initialized for pack creation")
            else:
                print("⚠️ No YouTube API key found")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            self.youtube = None
    
    @app_commands.command(name="create_pack", description="Create a pack using artist name")
    @app_commands.describe(artist_name="Name of the main artist", pack_type="Type of pack to create")
    @app_commands.choices(pack_type=[
        discord.app_commands.Choice(name="Community Pack", value="community"),
        discord.app_commands.Choice(name="Gold Pack", value="gold"),
        discord.app_commands.Choice(name="Platinum Pack", value="platinum")
    ])
    async def create_pack(self, interaction: Interaction, artist_name: str, pack_type: str = "community"):
        """Create a pack by searching artist and showing YouTube video options"""
        
        await interaction.response.defer(ephemeral=True)
        
        if not self.db:
            await interaction.followup.send("❌ Database not available", ephemeral=True)
            return
        
        if not self.youtube:
            await interaction.followup.send("❌ YouTube API not available", ephemeral=True)
            return
        
        # Check permissions for different pack types
        is_dev = self.is_dev(interaction.user.id)
        
        if pack_type == "platinum" and not is_dev:
            await interaction.followup.send("❌ Platinum packs are developer only!", ephemeral=True)
            return
        
        # Search YouTube for artist videos
        try:
            videos = await self.search_artist_videos(artist_name)
            
            if not videos:
                await interaction.followup.send(f"❌ No videos found for artist: {artist_name}", ephemeral=True)
                return
            
            # Show video selection view
            view = VideoSelectionView(self, videos, artist_name, pack_type, interaction.user)
            
            embed = discord.Embed(
                title=f"🎵 Select Video for {artist_name.title()} {pack_type.title()} Pack",
                description=f"Found {len(videos)} videos. Choose one for the hero card:",
                color=discord.Color.blue()
            )
            
            # Show first few videos as preview
            for i, video in enumerate(videos[:3], 1):
                embed.add_field(
                    name=f"Video {i}: {video['title'][:50]}...",
                    value=f"👁️ {video.get('views', 0):,} views | ⏱️ {video.get('duration', 'Unknown')}",
                    inline=False
                )
            
            embed.set_footer(text="Click the buttons below to see all options and select")
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Error searching videos: {e}")
            await interaction.followup.send(f"❌ Error searching for videos: {e}", ephemeral=True)
    
    async def search_artist_videos(self, artist_name: str, max_results: int = 10) -> list:
        """Search YouTube for videos by artist"""
        try:
            # Search for artist + official videos
            search_query = f"{artist_name} official music video"
            
            request = self.youtube.search().list(
                part="snippet",
                q=search_query,
                type="video",
                maxResults=max_results,
                videoCategoryId="10"  # Music category
            )
            
            response = request.execute()
            
            videos = []
            for item in response.get("items", []):
                video_data = {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"] if "high" in item["snippet"]["thumbnails"] else item["snippet"]["thumbnails"]["default"]["url"]
                }
                
                # Get video details for view count and duration
                try:
                    details_request = self.youtube.videos().list(
                        part="statistics,contentDetails",
                        id=item["id"]["videoId"]
                    )
                    details_response = details_request.execute()
                    
                    if details_response.get("items"):
                        video_details = details_response["items"][0]
                        video_data["views"] = int(video_details["statistics"].get("viewCount", 0))
                        
                        # Parse duration
                        duration = video_details["contentDetails"].get("duration", "PT0S")
                        video_data["duration"] = self.parse_duration(duration)
                        
                except Exception as e:
                    print(f"Error getting video details: {e}")
                    video_data["views"] = 0
                    video_data["duration"] = "Unknown"
                
                videos.append(video_data)
            
            return videos
            
        except Exception as e:
            print(f"❌ YouTube search error: {e}")
            return []
    
    def parse_duration(self, duration: str) -> str:
        """Parse ISO 8601 duration to readable format"""
        try:
            import re
            # PT4M13S -> 4:13
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if match:
                hours, minutes, seconds = match.groups()
                if hours:
                    return f"{hours}:{minutes.zfill(2)}:{seconds.zfill(2)}"
                else:
                    return f"{minutes}:{seconds.zfill(2)}"
            return "Unknown"
        except:
            return "Unknown"
    
    async def create_pack_from_video(self, interaction: discord.Interaction, video: dict, artist_name: str, pack_type: str):
        """Create pack using selected YouTube video"""
        
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        
        # Generate cards based on selected video
        cards = self.generate_cards_from_video(video, artist_name, pack_type)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert pack
                price = {"community": 0, "gold": 9.99, "platinum": 19.99}[pack_type]
                
                cursor.execute("""
                    INSERT INTO creator_packs (pack_id, creator_id, name, description, pack_size, status, cards_data, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pack_id,
                    interaction.user.id,
                    f"{artist_name.title()} {pack_type.title()} Pack",
                    f"Featured: {video['title']} + {len(cards)-1} related cards",
                    len(cards),
                    "live",
                    str(cards),  # Store as Python dict string
                    price
                ))
                
                # Add to user inventory
                cursor.execute("""
                    INSERT INTO user_packs (user_id, pack_id, acquired_at)
                    VALUES (?, ?, datetime('now'))
                """, (interaction.user.id, pack_id))
                
                # List in marketplace if paid pack
                if price > 0:
                    cursor.execute("""
                        INSERT INTO marketplace (pack_id, price, stock)
                        VALUES (?, ?, ?)
                    """, (pack_id, price, "unlimited"))
                
                conn.commit()
                print(f"✅ {pack_type.title()} pack {pack_id} created from video: {video['title']}")
        
        except Exception as e:
            print(f"❌ Database error: {e}")
            await interaction.followup.send(f"❌ Database error: {e}", ephemeral=True)
            return
        
        # Send confirmation
        embed = discord.Embed(
            title=f"✅ {pack_type.title()} Pack Created!",
            description=f"**{artist_name.title()}** pack created from selected video.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=video.get("thumbnail", ""))
        embed.add_field(name="Selected Video", value=f"[{video['title']}]('https://youtube.com/watch?v={video['video_id']}')", inline=False)
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        embed.add_field(name="Cards", value=f"{len(cards)} cards", inline=False)
        embed.add_field(name="Price", value=f"${price}" if price > 0 else "Free", inline=False)
        
        # Show card preview
        rarity_emojis = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}
        for i, card in enumerate(cards[:3], 1):  # Show first 3 cards
            rarity = card.get('rarity', 'community')
            emoji = rarity_emojis.get(rarity, "🎴")
            embed.add_field(
                name=f"{emoji} Card {i}",
                value=f"{card.get('name', 'Unknown')}\nRarity: {rarity.title()}",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def generate_cards_from_video(self, video: dict, artist_name: str, pack_type: str) -> list:
        """Generate cards based on selected YouTube video"""
        cards = []
        
        # Main hero card from video
        main_rarity = {"community": "gold", "gold": "platinum", "platinum": "legendary"}[pack_type]
        cards.append({
            "name": video['title'],
            "rarity": main_rarity,
            "impact": random.randint(70, 95),
            "skill": random.randint(70, 95),
            "longevity": random.randint(70, 95),
            "culture": random.randint(70, 95),
            "hype": random.randint(70, 95),
            "video_id": video['video_id'],
            "views": video.get('views', 0)
        })
        
        # Generate supporting cards
        supporting_rarities = {
            "community": ["community", "community", "community", "community"],
            "gold": ["gold", "community", "community", "community"],
            "platinum": ["platinum", "gold", "gold", "community"]
        }
        
        for rarity in supporting_rarities[pack_type]:
            # Generate related video names
            related_names = [
                f"{artist_name} Remix",
                f"{artist_name} Live",
                f"{artist_name} Acoustic",
                f"{artist_name} Collab"
            ]
            
            cards.append({
                "name": random.choice(related_names),
                "rarity": rarity,
                "impact": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "skill": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "longevity": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "culture": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                "hype": random.randint(50, 80) if rarity == "community" else random.randint(60, 85)
            })
        
        return cards
    
    @app_commands.command(name="test_pack", description="Test if pack creation cog is working")
    async def test_pack(self, interaction: Interaction):
        """Test command to verify cog is loaded"""
        await interaction.response.send_message("✅ Pack creation cog is working! Commands available: /create_pack", ephemeral=True)
    
    def is_dev(self, user_id: int) -> bool:
        """Check if user is a developer"""
        dev_ids = os.getenv("DEV_USER_IDS", "").split(",") if os.getenv("DEV_USER_IDS") else []
        return str(user_id) in dev_ids or user_id == 123456789  # Add your Discord ID here

async def setup(bot):
    cog = SimplePackCreation(bot)
    await bot.add_cog(cog)
    
    # List all commands in this cog for debugging
    commands = []
    for cmd in cog.walk_app_commands():
        commands.append(f"/{cmd.name}")
    
    print(f"🔥 SimplePackCreation cog loaded with commands: {commands}")
