# -*- coding: utf-8 -*-
"""
Dev Webhook Commands Cog
Provides dev-only commands accessible via webhook channel
Commands: announcement, pack creation (community/gold), restart
"""

import discord
from discord.ext import commands
from discord import Interaction, app_commands
from discord.ui import Modal, TextInput
from database import DatabaseManager
import os
import sys
from typing import List, Dict
import asyncio

# Import pack creation helpers
from services.image_cache import safe_image
from youtube_integration import youtube_integration
from cogs.dev_helpers import check_test_server, check_and_respond


class AnnouncementModal(Modal, title="Send Update Announcement"):
    """Modal for sending announcements to all servers"""
    
    title_input = TextInput(
        label="Announcement Title",
        placeholder="Enter announcement title (e.g., 'New Feature Update')",
        max_length=100,
        required=True
    )
    
    message_input = TextInput(
        label="Announcement Message",
        placeholder="Enter the announcement message...",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            title = self.title_input.value
            message = self.message_input.value
            
            # Create announcement embed
            embed = discord.Embed(
                title=f"📢 {title}",
                description=message,
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Music Legends Bot")
            
            # Send to all servers
            sent_count = 0
            failed_count = 0
            
            for guild in self.bot.guilds:
                try:
                    # Try to find a general/announcements channel
                    channel = None
                    for ch in guild.text_channels:
                        if ch.name in ['general', 'announcements', 'updates', 'news']:
                            channel = ch
                            break
                    
                    # If no specific channel found, use first text channel
                    if not channel:
                        channel = guild.text_channels[0] if guild.text_channels else None
                    
                    if channel:
                        await channel.send(embed=embed)
                        sent_count += 1
                except Exception as e:
                    print(f"❌ Failed to send announcement to {guild.name}: {e}")
                    failed_count += 1
            
            await interaction.followup.send(
                f"✅ Announcement sent!\n"
                f"**Sent to:** {sent_count} servers\n"
                f"**Failed:** {failed_count} servers",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Error sending announcement: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


class DevWebhookCommandsCog(commands.Cog):
    """Dev-only commands for webhook channel"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    @app_commands.command(name="dev_announcement", description="[DEV] Send update announcement to all servers")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(check_test_server)
    async def dev_announcement(self, interaction: Interaction):
        """Send announcement to all servers"""
        if not await check_and_respond(interaction):
            return
        modal = AnnouncementModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="dev_create_community_pack", description="[DEV] Create a community pack (simplified)")
    @app_commands.describe(artist_name="Artist name (becomes pack name)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(check_test_server)
    async def dev_create_community_pack(self, interaction: Interaction, artist_name: str):
        """Create a community pack using simplified flow"""
        if not await check_and_respond(interaction):
            return
        await self._create_pack_with_type(interaction, artist_name, "community")
    
    @app_commands.command(name="dev_create_gold_pack", description="[DEV] Create a gold pack (simplified, better stats)")
    @app_commands.describe(artist_name="Artist name (becomes pack name)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(check_test_server)
    async def dev_create_gold_pack(self, interaction: Interaction, artist_name: str):
        """Create a gold pack using simplified flow with better stats"""
        if not await check_and_respond(interaction):
            return
        await self._create_pack_with_type(interaction, artist_name, "gold")
    
    async def _create_pack_with_type(self, interaction: Interaction, artist_name: str, pack_type: str):
        """Create pack with specified type (community or gold)"""
        pack_name = artist_name  # Pack name automatically equals artist name
        print(f"🔥 [DEV] Creating {pack_type} pack: {pack_name} by {interaction.user.name}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if YouTube API key is configured
            youtube_api_key = os.getenv("YOUTUBE_API_KEY")
            if not youtube_api_key:
                await interaction.followup.send(
                    "❌ YouTube API is not configured. Please contact an administrator.\n"
                    "**For admins**: Set `YOUTUBE_API_KEY` in environment variables.",
                    ephemeral=True
                )
                return
            
            # Search for music videos on YouTube
            print(f"🔥 [DEV] Searching YouTube for {artist_name}")
            videos = youtube_integration.search_music_video(artist_name, limit=50)
            print(f"🔥 [DEV] Found {len(videos) if videos else 0} videos")
            
            if not videos:
                await interaction.followup.send(
                    f"❌ Could not find videos for '{artist_name}'\n"
                    f"Please try:\n"
                    f"• Checking the artist name spelling\n"
                    f"• Using a different variation of the artist name\n"
                    f"• Trying a more popular artist", 
                    ephemeral=True
                )
                return
            
            # Create artist data from first video
            thumbnail_url = videos[0].get('thumbnail_url', '') if videos else ''
            print(f"🔥 [DEV] Artist thumbnail URL: {thumbnail_url[:50] if thumbnail_url else 'None'}...")
            artist = {
                'name': artist_name,
                'image_url': thumbnail_url,
                'popularity': 75,
                'followers': 1000000
            }
            
            tracks = videos
            
            # Show song selection UI
            selection_embed = discord.Embed(
                title=f"🎵 Select Songs for Your {pack_type.title()} Pack",
                description=f"**{pack_name}** featuring **{artist['name']}**\n\nFound **{len(tracks)}** videos. Select up to 5 songs for your pack.",
                color=discord.Color.blue() if pack_type == "community" else discord.Color.gold()
            )
            
            if artist.get('image_url'):
                safe_thumbnail = safe_image(artist['image_url'])
                if safe_thumbnail != artist['image_url']:
                    print(f"🖼️ Using fallback image for artist {artist['name']}: {artist['image_url'][:50]}...")
                selection_embed.set_thumbnail(url=safe_thumbnail)
            
            pack_type_info = {
                "community": "Stats: 50-85 • Standard rarity chances",
                "gold": "Stats: 70-92 • Better rarity chances (+10 boost)"
            }
            
            selection_embed.add_field(
                name="📋 Instructions",
                value="1. Select songs from the dropdown menu\n2. Click 'Confirm Selection' to create your pack\n3. Your pack will be published to the marketplace",
                inline=False
            )
            selection_embed.add_field(
                name="📊 Pack Type",
                value=pack_type_info[pack_type],
                inline=False
            )
            
            # Import SongSelectionView
            from views.song_selection import SongSelectionView
            
            # Create callback for when songs are selected
            async def on_songs_selected(confirm_interaction: Interaction, selected_tracks: List[Dict]):
                await self._finalize_pack_creation(
                    confirm_interaction,
                    pack_name,
                    artist,
                    selected_tracks,
                    interaction.user.id,
                    pack_type
                )
            
            # Show selection view
            print(f"🔥 [DEV] Creating SongSelectionView with {len(tracks)} tracks")
            view = SongSelectionView(tracks, max_selections=5, callback=on_songs_selected)
            print(f"🔥 [DEV] Sending selection embed with view")
            await interaction.followup.send(embed=selection_embed, view=view, ephemeral=True)
            print(f"🔥 [DEV] Selection UI sent successfully")
                
        except Exception as e:
            print(f"❌ [DEV] Error creating pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    async def _finalize_pack_creation(self, interaction: Interaction, pack_name: str, artist: Dict, selected_tracks: List[Dict], creator_id: int, pack_type: str):
        """Finalize pack creation after song selection - uses same logic as menu_system"""
        import random
        import sqlite3
        
        try:
            print(f"🎯 [DEV] Starting {pack_type} pack creation for {pack_name} by {artist['name']}")
            print(f"   Selected tracks: {len(selected_tracks)}")
            
            # Create pack in database
            pack_id = self.db.create_creator_pack(
                creator_id=creator_id,
                name=pack_name,
                description=f"{pack_type.title()} pack featuring {artist['name']}",
                pack_size=len(selected_tracks)
            )
            
            if not pack_id:
                print(f"❌ [DEV] Failed to create pack in database")
                await interaction.followup.send("❌ Failed to create pack in database", ephemeral=True)
                return
            
            print(f"✅ [DEV] Pack created with ID: {pack_id}")
            
            # Generate cards for each selected track
            cards_created = []
            
            # Stat ranges based on pack type (from menu_system.py lines 1677-1682)
            if pack_type == 'gold':
                stat_min, stat_max = 70, 92
                rarity_boost = 10
            else:  # community
                stat_min, stat_max = 50, 85
                rarity_boost = 0
            
            for track in selected_tracks:
                try:
                    print(f"📦 [DEV] Processing track: {track.get('title', track.get('name', 'Unknown'))}")
                    
                    # Generate stats
                    base_stat = random.randint(stat_min, stat_max)
                    
                    stats = {
                        'impact': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'skill': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'longevity': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'culture': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'hype': min(99, max(20, base_stat + random.randint(-10, 10)))
                    }
                    
                    # Determine rarity based on average stats (from menu_system.py lines 1702-1710)
                    avg_stat = sum(stats.values()) / len(stats) + rarity_boost
                    if avg_stat >= 85:
                        rarity = "legendary"
                    elif avg_stat >= 75:
                        rarity = "epic"
                    elif avg_stat >= 65:
                        rarity = "rare"
                    else:
                        rarity = "common"
                    
                    # Extract song title
                    video_title = track.get('title', track.get('name', ''))
                    song_title = video_title.replace(artist['name'], '').replace('-', '').strip()
                    for suffix in ['(Official Music Video)', '(Official Video)', '(Lyrics)', '(Audio)', 'ft.', 'feat.']:
                        song_title = song_title.replace(suffix, '').strip()
                    if not song_title or len(song_title) < 2:
                        song_title = video_title[:50]
                    
                    # Get image URL using robust extraction with fallback
                    from cogs.pack_creation_helpers import extract_image_url
                    image_url = extract_image_url(track, artist)
                    
                    # Get video ID
                    video_id = track.get('video_id', str(random.randint(1000, 9999)))
                    youtube_url = track.get('youtube_url', f"https://youtube.com/watch?v={video_id}")
                    
                    # Create card data
                    card_id = f"{pack_id}_{video_id}"
                    card_data = {
                        'card_id': card_id,
                        'name': artist['name'],
                        'title': song_title[:100],
                        'rarity': rarity,
                        'image_url': image_url,
                        'youtube_url': youtube_url,
                        'impact': stats['impact'],
                        'skill': stats['skill'],
                        'longevity': stats['longevity'],
                        'culture': stats['culture'],
                        'hype': stats['hype'],
                        'pack_id': pack_id,
                        'created_by_user_id': creator_id
                    }
                    
                    # Add card to master list
                    success = self.db.add_card_to_master(card_data)
                    if success:
                        self.db.add_card_to_pack(pack_id, card_data)
                        # Give creator a copy
                        self.db.add_card_to_collection(creator_id, card_id, 'pack_creation')
                        cards_created.append(card_data)
                    
                except Exception as e:
                    print(f"❌ [DEV] Error creating card: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Publish pack
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE creator_packs 
                    SET status = 'LIVE', published_at = CURRENT_TIMESTAMP
                    WHERE pack_id = ?
                """, (pack_id,))
                conn.commit()
            
            # Trigger backup
            try:
                from services.backup_service import backup_service
                backup_path = await backup_service.backup_critical('pack_published', pack_id)
                if backup_path:
                    print(f"💾 [DEV] Critical backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️ [DEV] Backup trigger failed (non-critical): {e}")
            
            # Create visual confirmation embed
            embed = discord.Embed(
                title=f"✅ {pack_type.title()} Pack Created Successfully!",
                description=f"**{pack_name}** featuring {artist['name']}",
                color=discord.Color.green() if pack_type == "community" else discord.Color.gold()
            )
            
            embed.add_field(name="📦 Pack ID", value=f"`{pack_id}`", inline=True)
            embed.add_field(name="🎤 Artist", value=artist['name'], inline=True)
            embed.add_field(name="🎵 Cards Created", value=str(len(cards_created)), inline=True)
            
            if artist.get('image_url'):
                embed.set_thumbnail(url=artist['image_url'])
            
            # Show all cards with stats
            card_list = ""
            for card in cards_created:
                rarity_emoji = {"legendary": "⭐", "epic": "🟣", "rare": "🔵", "common": "⚪"}.get(card['rarity'], "⚪")
                total_power = card['impact'] + card['skill'] + card['longevity'] + card['culture'] + card['hype']
                card_list += f"{rarity_emoji} **{card['title'][:30]}** ({card['rarity'].title()}) - Power: {total_power}\n"
            
            embed.add_field(name="🎴 Pack Contents", value=card_list or "No cards", inline=False)
            
            # Rarity distribution
            rarity_counts = {}
            for card in cards_created:
                rarity_counts[card['rarity']] = rarity_counts.get(card['rarity'], 0) + 1
            rarity_text = " | ".join([f"{r.title()}: {c}" for r, c in rarity_counts.items()])
            embed.add_field(name="🎯 Rarity Distribution", value=rarity_text or "N/A", inline=False)
            
            embed.add_field(
                name="📢 Status",
                value="✅ Published to Marketplace\n🎁 Cards added to your collection",
                inline=False
            )
            
            embed.set_footer(text="Use /deck to see your new cards!")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ [DEV] Error finalizing pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="dev_restart", description="[DEV] Restart the bot (with confirmation)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(check_test_server)
    async def dev_restart(self, interaction: Interaction):
        """Restart the bot"""
        if not await check_and_respond(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Log restart
            from services.bot_logger import get_bot_logger
            logger = get_bot_logger(self.bot)
            logger.log_restart('manual', {'triggered_by': interaction.user.id})
            
            await interaction.followup.send(
                "🔄 **Bot Restart Initiated**\n\n"
                "The bot will restart shortly. This may take a few moments.",
                ephemeral=True
            )
            
            # Wait a moment then exit
            await asyncio.sleep(2)
            await self.bot.close()
            
        except Exception as e:
            print(f"❌ [DEV] Error restarting bot: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DevWebhookCommandsCog(bot))
