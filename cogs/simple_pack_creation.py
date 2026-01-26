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

class PackConfirmationView(discord.ui.View):
    """View for confirming pack creation with main content + related videos"""
    
    def __init__(self, cog, main_content, related_videos, artist_name, pack_type, user):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.cog = cog
        self.main_content = main_content
        self.related_videos = related_videos
        self.artist_name = artist_name
        self.pack_type = pack_type
        self.user = user
        
        # Add confirmation button
        confirm_button = discord.ui.Button(
            label="✅ Create Pack",
            style=discord.ButtonStyle.success,
            custom_id="confirm_pack"
        )
        confirm_button.callback = self.create_pack_callback
        self.add_item(confirm_button)
        
        # Add cancel button
        cancel_button = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel_pack"
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)
    
    async def create_pack_callback(self, interaction: discord.Interaction):
        """Create the pack with main content + related videos"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ You can't create packs for someone else!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create the pack
        await self.cog.create_pack_with_content(
            interaction, self.main_content, self.related_videos, 
            self.artist_name, self.pack_type
        )
        
        # Disable all buttons after creation
        for child in self.children:
            child.disabled = True
        
        await interaction.edit_original_response(view=self)
    
    async def cancel_callback(self, interaction: discord.Interaction):
        """Cancel pack creation"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ You can't cancel someone else's pack!", ephemeral=True)
            return
        
        await interaction.response.send_message("❌ Pack creation cancelled", ephemeral=True)
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        await interaction.edit_original_response(view=self)
    
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
        
        # Step 1: Get main artist content
        try:
            main_content = await self.search_artist_main_content(artist_name)
            
            if not main_content:
                await interaction.followup.send(f"❌ No main content found for artist: {artist_name}", ephemeral=True)
                return
            
            # Step 2: Fetch related videos for full pack
            related_videos = await self.fetch_related_videos(artist_name)
            
            # Show main content confirmation
            embed = discord.Embed(
                title=f"🎵 Create {artist_name.title()} {pack_type.title()} Pack",
                description=f"**Main Card:** {main_content['title']}\n**Related Videos Found:** {len(related_videos)}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=main_content.get("thumbnail", ""))
            embed.add_field(name="Main Content", value=f"👁️ {main_content.get('views', 0):,} views | ⏱️ {main_content.get('duration', 'Unknown')}", inline=False)
            embed.add_field(name="Pack Size", value=f"1 main card + {len(related_videos)} related cards", inline=False)
            
            # Add confirmation button
            view = PackConfirmationView(self, main_content, related_videos, artist_name, pack_type, interaction.user)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Error creating pack: {e}")
            await interaction.followup.send(f"❌ Error creating pack: {e}", ephemeral=True)
    
    async def search_artist_main_content(self, artist_name: str) -> dict:
        """Search for main artist content with image for hero card"""
        try:
            # Search for artist + official music videos
            search_query = f"{artist_name} official music video"
            
            request = self.youtube.search().list(
                part="snippet",
                q=search_query,
                type="video",
                maxResults=1,
                videoCategoryId="10"  # Music category
            )
            
            response = request.execute()
            
            if not response.get("items"):
                return None
            
            item = response["items"][0]
            
            # Get video details
            try:
                details_request = self.youtube.videos().list(
                    part="statistics,contentDetails",
                    id=item["id"]["videoId"]
                )
                details_response = details_request.execute()
                
                video_details = details_response["items"][0] if details_response.get("items") else {}
                
                main_content = {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"] if "high" in item["snippet"]["thumbnails"] else item["snippet"]["thumbnails"]["default"]["url"],
                    "views": int(video_details.get("statistics", {}).get("viewCount", 0)),
                    "duration": self.parse_duration(video_details.get("contentDetails", {}).get("duration", "PT0S"))
                }
                
                return main_content
                
            except Exception as e:
                print(f"Error getting video details: {e}")
                return None
            
        except Exception as e:
            print(f"❌ YouTube main content search error: {e}")
            return None
    
    async def fetch_related_videos(self, artist_name: str, max_results: int = 8) -> list:
        """Fetch related videos for pack creation"""
        try:
            # Search for related content
            search_queries = [
                f"{artist_name} music video",
                f"{artist_name} live performance",
                f"{artist_name} remix",
                f"{artist_name} acoustic"
            ]
            
            all_videos = []
            
            for query in search_queries:
                try:
                    request = self.youtube.search().list(
                        part="snippet",
                        q=query,
                        type="video",
                        maxResults=2,  # Get 2 per query
                        videoCategoryId="10"
                    )
                    
                    response = request.execute()
                    
                    for item in response.get("items", []):
                        video_data = {
                            "video_id": item["id"]["videoId"],
                            "title": item["snippet"]["title"],
                            "description": item["snippet"]["description"],
                            "channel_title": item["snippet"]["channelTitle"],
                            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"] if "high" in item["snippet"]["thumbnails"] else item["snippet"]["thumbnails"]["default"]["url"]
                        }
                        
                        # Get basic stats
                        try:
                            details_request = self.youtube.videos().list(
                                part="statistics",
                                id=item["id"]["videoId"]
                            )
                            details_response = details_request.execute()
                            
                            if details_response.get("items"):
                                video_details = details_response["items"][0]
                                video_data["views"] = int(video_details["statistics"].get("viewCount", 0))
                            else:
                                video_data["views"] = 0
                        except:
                            video_data["views"] = 0
                        
                        all_videos.append(video_data)
                        
                except Exception as e:
                    print(f"Error with query '{query}': {e}")
                    continue
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_videos = []
            for video in all_videos:
                if video["video_id"] not in seen_ids:
                    seen_ids.add(video["video_id"])
                    unique_videos.append(video)
                    if len(unique_videos) >= max_results:
                        break
            
            return unique_videos
            
        except Exception as e:
            print(f"❌ Related videos fetch error: {e}")
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
    
    async def create_pack_with_content(self, interaction: discord.Interaction, main_content: dict, related_videos: list, artist_name: str, pack_type: str):
        """Create pack using main content + related videos"""
        
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        
        # Generate cards based on main content + related videos
        cards = self.generate_cards_from_content(main_content, related_videos, artist_name, pack_type)
        
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
                    f"Featured: {main_content['title']} + {len(related_videos)} related cards",
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
                print(f"✅ {pack_type.title()} pack {pack_id} created with main content + {len(related_videos)} related videos")
        
        except Exception as e:
            print(f"❌ Database error: {e}")
            await interaction.followup.send(f"❌ Database error: {e}", ephemeral=True)
            return
        
        # Send confirmation
        embed = discord.Embed(
            title=f"✅ {pack_type.title()} Pack Created!",
            description=f"**{artist_name.title()}** pack created with main content + related videos.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=main_content.get("thumbnail", ""))
        embed.add_field(name="Main Content", value=f"[{main_content['title']}]('https://youtube.com/watch?v={main_content['video_id']}')", inline=False)
        embed.add_field(name="Related Videos", value=f"{len(related_videos)} videos included", inline=False)
        embed.add_field(name="Pack ID", value=pack_id, inline=False)
        embed.add_field(name="Total Cards", value=f"{len(cards)} cards", inline=False)
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
    
    def generate_cards_from_content(self, main_content: dict, related_videos: list, artist_name: str, pack_type: str) -> list:
        """Generate cards based on main content + related videos"""
        cards = []
        
        # Main hero card from main content
        main_rarity = {"community": "gold", "gold": "platinum", "platinum": "legendary"}[pack_type]
        cards.append({
            "name": main_content['title'],
            "rarity": main_rarity,
            "impact": random.randint(70, 95),
            "skill": random.randint(70, 95),
            "longevity": random.randint(70, 95),
            "culture": random.randint(70, 95),
            "hype": random.randint(70, 95),
            "video_id": main_content['video_id'],
            "views": main_content.get('views', 0),
            "thumbnail": main_content.get('thumbnail', ''),
            "is_main": True
        })
        
        # Generate cards from related videos
        supporting_rarities = {
            "community": ["community", "community", "community", "community"],
            "gold": ["gold", "community", "community", "community"],
            "platinum": ["platinum", "gold", "gold", "community"]
        }
        
        rarities = supporting_rarities[pack_type]
        
        # Use actual related videos first, then fill with generated ones if needed
        for i, rarity in enumerate(rarities):
            if i < len(related_videos):
                # Use actual related video
                video = related_videos[i]
                cards.append({
                    "name": video['title'],
                    "rarity": rarity,
                    "impact": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                    "skill": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                    "longevity": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                    "culture": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                    "hype": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                    "video_id": video['video_id'],
                    "views": video.get('views', 0),
                    "thumbnail": video.get('thumbnail', ''),
                    "is_main": False
                })
            else:
                # Generate fallback card if not enough related videos
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
                    "hype": random.randint(50, 80) if rarity == "community" else random.randint(60, 85),
                    "is_main": False
                })
        
        return cards
    
    def is_dev(self, user_id: int) -> bool:
        """Check if user is a developer"""
        dev_ids = os.getenv("DEV_USER_IDS", "").split(",") if os.getenv("DEV_USER_IDS") else []
        return str(user_id) in dev_ids or user_id == 123456789  # Add your Discord ID here

async def setup(bot):
    cog = SimplePackCreation(bot)
    await bot.add_cog(cog)
    print("🔥 SimplePackCreation cog loaded with /create_pack command")
