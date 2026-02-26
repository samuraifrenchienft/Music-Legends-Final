# pack_creation_helpers.py
"""
Helper methods for pack creation in menu_system.py
Separated to keep menu_system.py cleaner

Features:
- Rate limiting and caching for YouTube searches
- Performance optimization for pack creation
- Graceful fallback strategies
"""

import discord
from discord import Interaction
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from music_api_manager import music_api
from views.song_selection import SongSelectionView
from cogs.pack_preview_integration import show_pack_preview_lastfm


# ==========================================
# RATE LIMITING & CACHING
# ==========================================

class YouTubeSearchCache:
    """Simple cache for YouTube searches with rate limiting"""
    
    def __init__(self, cache_duration_seconds: int = 3600, max_cache_size: int = 100):
        self.cache: Dict[str, Tuple[List, datetime]] = {}
        self.cache_duration = timedelta(seconds=cache_duration_seconds)
        self.max_cache_size = max_cache_size
        self.search_count = 0
        self.search_timestamp = None
        print(f"🎬 [CACHE] YouTube cache initialized (TTL: {cache_duration_seconds}s, Max: {max_cache_size})")
    
    def get(self, artist_name: str) -> Optional[List]:
        """Get cached results for artist search"""
        key = artist_name.lower().strip()
        if key in self.cache:
            results, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_duration:
                print(f"✅ [CACHE] Cache HIT for: {artist_name}")
                return results
            else:
                print(f"⚠️  [CACHE] Cache EXPIRED for: {artist_name}")
                del self.cache[key]
        return None
    
    def set(self, artist_name: str, results: List) -> None:
        """Cache search results"""
        key = artist_name.lower().strip()
        
        # Simple LRU: remove oldest entry if cache is full
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            print(f"🗑️  [CACHE] Evicting oldest cache entry: {oldest_key}")
            del self.cache[oldest_key]
        
        self.cache[key] = (results, datetime.now())
        print(f"💾 [CACHE] Cached {len(results)} results for: {artist_name}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'cache_entries': len(self.cache),
            'max_size': self.max_cache_size,
            'searches': self.search_count,
            'ttl_seconds': self.cache_duration.total_seconds()
        }


# Global cache instance
youtube_cache = YouTubeSearchCache(cache_duration_seconds=3600, max_cache_size=100)

# Default logo image for cards without images
# Using the Music Legends Bot logo from Pinata IPFS
DEFAULT_CARD_IMAGE = "https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeiehxk5zhdxidab4qtuxg6lblrasxcxb2bkj6a3ipyjue5f7pzo3qi"


# ==========================================
# GRACEFUL FALLBACK STRATEGIES
# ==========================================

MINIMUM_VIDEOS_REQUIRED = 5
RECOMMENDED_VIDEO_SEARCH_LIMIT = 15
ALTERNATIVE_SEARCH_TERMS = {
    'artist': ['official', 'music video', 'audio', 'remix', 'cover'],
    'retry_count': 2
}


async def search_youtube_with_fallback(
    artist_name: str, 
    interaction: Interaction,
    youtube_integration,
    attempt: int = 1
) -> Optional[List]:
    """
    Search YouTube with rate limiting, caching, and graceful fallbacks.
    
    Strategy:
    1. Check cache first (avoids redundant API calls)
    2. If cache miss, search YouTube
    3. If insufficient results, try alternative search terms
    4. If still insufficient, return what we have or None
    
    Args:
        artist_name: Artist to search for
        interaction: Discord interaction for logging
        youtube_integration: YouTube integration module
        attempt: Current attempt number (for retry logic)
        
    Returns:
        List of videos or None if search failed
    """
    
    print(f"🎬 [SEARCH] Starting YouTube search (Attempt {attempt})")
    print(f"🎬 [SEARCH] Artist: {artist_name} | Limit: {RECOMMENDED_VIDEO_SEARCH_LIMIT}")
    
    # Step 1: Check cache first
    cached_results = youtube_cache.get(artist_name)
    if cached_results is not None:
        return cached_results
    
    # Step 2: Try primary search
    try:
        print(f"🎬 [SEARCH] Querying YouTube API (primary search)...")
        videos = youtube_integration.search_music_video(
            artist_name, 
            limit=RECOMMENDED_VIDEO_SEARCH_LIMIT
        )
        
        if videos and len(videos) >= MINIMUM_VIDEOS_REQUIRED:
            print(f"✅ [SEARCH] Found {len(videos)} videos")
            youtube_cache.set(artist_name, videos)
            return videos
        else:
            found_count = len(videos) if videos else 0
            print(f"⚠️  [SEARCH] Insufficient videos: {found_count}/{MINIMUM_VIDEOS_REQUIRED}")
            
    except Exception as e:
        print(f"❌ [SEARCH] Primary search error: {type(e).__name__}: {e}")
    
    # Step 3: Try alternative search terms (retry strategy)
    if attempt <= ALTERNATIVE_SEARCH_TERMS['retry_count']:
        for alt_term in ALTERNATIVE_SEARCH_TERMS['artist']:
            try:
                alternative_query = f"{artist_name} {alt_term}"
                print(f"🎬 [SEARCH] Trying alternative query: '{alternative_query}'")
                
                alt_videos = youtube_integration.search_music_video(
                    alternative_query,
                    limit=RECOMMENDED_VIDEO_SEARCH_LIMIT
                )
                
                if alt_videos and len(alt_videos) >= MINIMUM_VIDEOS_REQUIRED:
                    print(f"✅ [SEARCH] Alternative search found {len(alt_videos)} videos")
                    youtube_cache.set(artist_name, alt_videos)
                    return alt_videos
                    
            except Exception as e:
                print(f"⚠️  [SEARCH] Alternative search failed: {e}")
                continue
    
    # Step 4: Return partial results or None
    print(f"❌ [SEARCH] YouTube search exhausted all strategies")
    return None


def extract_image_url(track: dict, artist_data: dict, default: str = DEFAULT_CARD_IMAGE) -> str:
    """
    Extract image URL from track or artist data with robust fallback mechanism.
    
    Prioritization:
    1. YouTube thumbnails (track or artist)
    2. Last.fm track images (xlarge -> large -> medium)
    3. Last.fm artist images (xlarge -> large -> medium)
    4. Generic track images
    5. Generic artist images
    6. Default placeholder
    
    Args:
        track: Track data dict
        artist_data: Artist data dict
        default: Default image URL if none found
        
    Returns:
        Valid image URL string
    """
    # Priority 1: YouTube thumbnails (most reliable for videos)
    if track.get('thumbnail_url'):
        print(f"🎨 [IMAGE] Using track thumbnail_url: {track['thumbnail_url'][:80]}...")
        return track['thumbnail_url']
    if track.get('youtube_thumbnail'):
        print(f"🎨 [IMAGE] Using track youtube_thumbnail: {track['youtube_thumbnail'][:80]}...")
        return track['youtube_thumbnail']
    if artist_data.get('thumbnail_url'):
        print(f"🎨 [IMAGE] Using artist thumbnail_url: {artist_data['thumbnail_url'][:80]}...")
        return artist_data['thumbnail_url']
    
    # Priority 2: Last.fm track images (best quality)
    for size in ['image_xlarge', 'image_large', 'image_medium']:
        if track.get(size):
            print(f"🎨 [IMAGE] Using track {size}: {track[size][:80]}...")
            return track[size]
    
    # Priority 3: Last.fm artist images
    for size in ['image_xlarge', 'image_large', 'image_medium']:
        if artist_data.get(size):
            print(f"🎨 [IMAGE] Using artist {size}: {artist_data[size][:80]}...")
            return artist_data[size]
    
    # Priority 4: Generic track images
    if track.get('image'):
        print(f"🎨 [IMAGE] Using track image: {track['image'][:80]}...")
        return track['image']
    if track.get('image_url'):
        print(f"🎨 [IMAGE] Using track image_url: {track['image_url'][:80]}...")
        return track['image_url']
    
    # Priority 5: Generic artist images
    if artist_data.get('image'):
        print(f"🎨 [IMAGE] Using artist image: {artist_data['image'][:80]}...")
        return artist_data['image']
    if artist_data.get('image_url'):
        print(f"🎨 [IMAGE] Using artist image_url: {artist_data['image_url'][:80]}...")
        return artist_data['image_url']
    
    # Priority 6: Default placeholder
    print(f"🎨 [IMAGE] No image found, using default placeholder")
    return default


async def show_song_selection_lastfm(
    interaction: Interaction,
    pack_name: str,
    artist_data: dict,
    tracks: list,
    pack_type: str,
    db,
    finalize_callback,
    use_smaller_image: bool = False
):
    """Show song selection UI using Last.fm data"""
    
    # Create selection embed
    selection_embed = discord.Embed(
        title=f"🎵 Select Songs for Your {pack_type.title()} Pack",
        description=(
            f"**{pack_name}** featuring **{artist_data['name']}**\n\n"
            f"✅ Using Last.fm images and data\n"
            f"Select up to 5 songs for your pack."
        ),
        color=discord.Color.gold() if pack_type == 'gold' else discord.Color.blue()
    )
    
    if artist_data.get('image_xlarge'):
        selection_embed.set_thumbnail(url=artist_data['image_xlarge'])
    
    selection_embed.add_field(
        name="📋 Instructions",
        value="1. Select songs from the dropdown menu\n"
              "2. Click 'Confirm Selection' to create your pack\n"
              "3. Cards will be generated with stats based on popularity",
        inline=False
    )
    
    # Add pack type info
    if pack_type == 'gold':
        selection_embed.add_field(
            name="💎 Gold Pack Bonus",
            value="Higher base stats (70-92) • Better rarity chances",
            inline=False
        )
    else:
        selection_embed.add_field(
            name="📦 Community Pack",
            value="Standard stats (50-85) • Normal rarity distribution",
            inline=False
        )
    
    # Format tracks for selection view
    formatted_tracks = []
    for track in tracks:
        # Choose image size based on user preference
        if use_smaller_image:
            # Try ALL available image sizes in order of preference
            thumbnail = (track.get('image_medium') or 
                        track.get('image_large') or 
                        track.get('image_xlarge') or
                        artist_data.get('image_medium') or 
                        artist_data.get('image_large') or 
                        artist_data.get('image_xlarge') or
                        track.get('image') or  # Fallback to any image
                        artist_data.get('image', ''))
            print(f"🔧 Using smaller image: {thumbnail[:50] if thumbnail else 'NO IMAGE'}")
        else:
            # Use largest available image with fallbacks
            thumbnail = (track.get('youtube_thumbnail') or 
                        track.get('image_xlarge') or 
                        track.get('image_large') or 
                        track.get('image_medium') or
                        artist_data.get('image_xlarge') or 
                        artist_data.get('image_large') or 
                        artist_data.get('image_medium') or
                        track.get('image') or
                        artist_data.get('image', ''))
        
        formatted_tracks.append({
            'title': f"{track['name']} ({track['playcount']:,} plays)",
            'track_data': track,
            'thumbnail_url': thumbnail
        })
    
    # Create callback for when songs are selected
    async def on_songs_selected(confirm_interaction: Interaction, selected_tracks_raw: list):
        # selected_tracks_raw are formatted track dicts from SongSelectionView
        # Extract the actual track_data from each formatted track
        selected_tracks = []
        for item in selected_tracks_raw:
            if isinstance(item, dict) and 'track_data' in item:
                selected_tracks.append(item['track_data'])
            else:
                selected_tracks.append(item)
        
        # Generate preview cards
        preview_cards = []
        for track in selected_tracks:
            card_data = music_api.format_track_for_card(
                track=track,
                artist_name=artist_data['name'],
                pack_type=pack_type,
                image_url=track.get('image_xlarge') or artist_data.get('image_xlarge'),
                video_url=track.get('url', '')
            )
            preview_cards.append(card_data)
        
        # Show pack preview
        await show_pack_preview_lastfm(
            confirm_interaction,
            pack_name,
            artist_data,
            selected_tracks,
            preview_cards,
            pack_type,
            db,
            interaction
        )
    
    # Show selection view
    view = SongSelectionView(formatted_tracks, max_selections=5, callback=on_songs_selected)
    await interaction.followup.send(
        embed=selection_embed,
        view=view,
        ephemeral=False
    )


async def finalize_pack_creation_lastfm(
    interaction: Interaction,
    pack_name: str,
    artist_data: dict,
    selected_tracks: list,
    creator_id: int,
    pack_type: str,
    db
):
    """Finalize pack creation with Last.fm data"""
    
    try:
        # Don't defer again - interaction was already deferred in PackCreationModal
        
        print(f"🔧 [FINALIZE] Starting pack finalization")
        print(f"🔧 [FINALIZE] Pack: {pack_name} | Type: {pack_type} | Tracks: {len(selected_tracks)}")
        print(f"🔧 [FINALIZE] Creator ID: {creator_id} | Artist: {artist_data.get('name', 'Unknown')}")
        
        # Create pack in database
        try:
            print(f"🔧 [FINALIZE] Creating pack record in database...")
            pack_id = db.create_creator_pack(
                creator_id=creator_id,
                name=pack_name,
                description=f"{pack_type.title()} pack featuring {artist_data['name']}",
                pack_size=len(selected_tracks)
            )
            if pack_id:
                print(f"✅ [FINALIZE] Pack created with ID: {pack_id}")
            else:
                print(f"❌ [FINALIZE] create_creator_pack returned None")
        except Exception as db_error:
            print(f"❌ [FINALIZE] Database error creating pack: {type(db_error).__name__}: {db_error}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                "❌ Failed to create pack in database. Please try again or contact support.",
                ephemeral=True
            )
            return
        
        if not pack_id:
            print(f"❌ [FINALIZE] pack_id is None or empty")
            await interaction.followup.send("❌ Failed to create pack in database", ephemeral=True)
            return
        
        # Generate cards for each selected track
        cards_created = []
        cards_failed = 0
        
        print(f"🔧 [FINALIZE] Starting card generation for {len(selected_tracks)} tracks...")
        for track in selected_tracks:
            try:
                # Get image URL with robust fallback mechanism
                image_url = extract_image_url(track, artist_data)
                
                print(f"🎨 [FINALIZE_LFM] Card image selected: {image_url[:80] if image_url else 'DEFAULT'}...")
                if not image_url or image_url == '':
                    print(f"⚠️  [FINALIZE_LFM] WARNING: Image URL is empty after extraction!")
                    image_url = DEFAULT_CARD_IMAGE
                    print(f"🎨 [FINALIZE_LFM] Using default image: {image_url[:80]}...")
                
                card_data = music_api.format_track_for_card(
                    track=track,
                    artist_name=artist_data['name'],
                    pack_type=pack_type,
                    image_url=image_url,
                    video_url=track.get('url', '')
                )
                
                print(f"🎨 DEBUG: Card data image_url: {card_data.get('image_url', 'NO IMAGE')[:80] if card_data.get('image_url') else 'MISSING'}")
                
                # Create card ID
                card_id = f"{pack_id}_{track['name'].lower().replace(' ', '_')[:20]}_{random.randint(1000, 9999)}"
                
                # Prepare card data for database - ensure all required fields are present
                final_image_url = card_data.get('image_url', '') or image_url or DEFAULT_CARD_IMAGE
                
                db_card_data = {
                    'card_id': card_id,
                    'name': artist_data['name'],
                    'title': card_data.get('name', track['name'])[:100],
                    'rarity': card_data.get('rarity', 'common'),
                    'image_url': final_image_url,  # Guaranteed to have an image
                    'youtube_url': card_data.get('video_url', ''),
                    'impact': card_data.get('attack', 50),
                    'skill': card_data.get('defense', 50),
                    'longevity': card_data.get('speed', 50),
                    'culture': card_data.get('attack', 50),  # Fallback to attack
                    'hype': card_data.get('defense', 50),    # Fallback to defense
                    'pack_id': pack_id,
                    'created_by_user_id': creator_id
                }
                
                print(f"📦 Creating card: {db_card_data['title']} (Rarity: {db_card_data['rarity']})")
                print(f"🖼️ Card image_url: {db_card_data.get('image_url', 'EMPTY')[:80] if db_card_data.get('image_url') else 'DEFAULT'}")
                
                # Add card to master list
                success = db.add_card_to_master(db_card_data)
                if success:
                    db.add_card_to_pack(pack_id, db_card_data)
                    # Give creator a copy
                    db.add_card_to_collection(creator_id, card_id, 'pack_creation')
                    cards_created.append(db_card_data)
                    print(f"✅ Card created successfully: {card_id}")
                else:
                    print(f"❌ Failed to add card to database: {card_id}")
                
            except Exception as e:
                print(f"❌ Error creating card for track {track.get('name', 'Unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Publish pack
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE creator_packs 
                SET status = 'LIVE', published_at = CURRENT_TIMESTAMP
                WHERE pack_id = ?
            """, (pack_id,))
            conn.commit()
        db.add_to_dev_supply(pack_id)
        
        # Trigger backup after pack is published to marketplace
        try:
            from services.backup_service import backup_service
            backup_path = await backup_service.backup_critical('pack_published', pack_id)
            if backup_path:
                print(f"💾 Critical backup created after pack publication: {backup_path}")
        except Exception as e:
            print(f"⚠️ Backup trigger failed (non-critical): {e}")
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Pack Created Successfully!",
            description=f"**{pack_name}** is now live in the marketplace!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📦 Pack Details",
            value=f"**Pack ID:** {pack_id}\n"
                  f"**Artist:** {artist_data['name']}\n"
                  f"**Cards:** {len(cards_created)}\n"
                  f"**Type:** {pack_type.title()}",
            inline=False
        )
        
        # Show card list with stats
        if cards_created:
            card_list = []
            rarity_counts = {'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0}
            
            for card in cards_created:
                rarity = card['rarity']
                rarity_counts[rarity] += 1
                power = (card['impact'] + card['skill'] + card['longevity']) // 3
                
                rarity_emoji = {
                    'common': '⚪',
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟡',
                    'mythic': '🔴'
                }.get(rarity, '⚪')
                
                card_list.append(f"{rarity_emoji} **{card['title']}** ({power} power)")
            
            embed.add_field(
                name="🎴 Cards Created",
                value="\n".join(card_list[:5]) + (f"\n...and {len(card_list) - 5} more" if len(card_list) > 5 else ""),
                inline=False
            )
            
            # Rarity distribution
            rarity_text = " • ".join([
                f"{count} {rarity.title()}" 
                for rarity, count in rarity_counts.items() if count > 0
            ])
            embed.add_field(
                name="📊 Rarity Distribution",
                value=rarity_text,
                inline=False
            )
        
        if artist_data.get('image_xlarge'):
            embed.set_thumbnail(url=artist_data['image_xlarge'])
        
        embed.set_footer(text=f"✨ All {len(cards_created)} cards have been added to your collection!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"❌ Error finalizing Last.fm pack: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send("❌ Something went wrong finalizing the pack. Please try again.", ephemeral=True)
