# ui/gallery.py
"""
Multi-Image Gallery View
Interactive gallery for browsing artist images
"""

import discord
from discord.ui import View, Button
from discord import Interaction, Embed
from services.image_cache import safe_image, DEFAULT_IMG

class GalleryView(View):
    """
    Interactive gallery view for browsing artist images
    Features navigation and image safety
    """
    
    def __init__(self, artists):
        super().__init__(timeout=None)  # No timeout for persistence
        self.artists = artists
        self.index = 0

    def embed(self):
        """Generate embed for current artist"""
        try:
            a = self.artists[self.index]
            
            # Get safe image URL
            safe_url = safe_image(a.get("image"))
            
            # Create embed
            e = discord.Embed(
                title=f"🎴 {a['name']}",
                description=f"🎼 {a.get('genre', 'Unknown')} • 🏆 {a.get('estimated_tier', 'Unknown')}",
                color=discord.Color.blue()
            )
            
            # Set image (safe URL or default)
            if safe_url:
                e.set_image(url=safe_url)
            
            # Add artist details
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(a.get('estimated_tier', ''), "❓")
            
            # Add fields with artist information
            e.add_field(name="🎼 Genre", value=a.get('genre', 'Unknown'), inline=True)
            e.add_field(name="🏆 Tier", value=f"{tier_emoji} {a.get('estimated_tier', 'Unknown')}", inline=True)
            e.add_field(name="👥 Popularity", value=str(a.get('popularity', 0)), inline=True)
            
            # Add YouTube stats if available
            if a.get('subscribers', 0) > 0:
                e.add_field(name="📺 Subscribers", value=f"{a.get('subscribers', 0):,}", inline=True)
            
            if a.get('views', 0) > 0:
                e.add_field(name="👁️ Views", value=f"{a.get('views', 0):,}", inline=True)
            
            # Add channel info if available
            if a.get('channel_id'):
                e.add_field(name="📺 Channel ID", value=a.get('channel_id'), inline=True)
            
            # Set footer with navigation info
            e.set_footer(text=f"🖼️ {self.index + 1}/{len(self.artists)} • Use ◀ ▶ to navigate")
            
            return e
            
        except Exception as e:
            # Fallback embed if error
            e = discord.Embed(
                title="❌ Gallery Error",
                description=f"Error displaying artist: {e}",
                color=discord.Color.red()
            )
            e.set_footer(text=f"🖼️ {self.index + 1}/{len(self.artists)}")
            return e

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, emoji="◀️")
    async def prev(self, interaction: Interaction, button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, emoji="▶️")
    async def next(self, interaction: Interaction, button):
        self.index = min(len(self.artists) - 1, self.index + 1)
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="First", style=discord.ButtonStyle.primary, emoji="⏮️")
    async def first(self, interaction: Interaction, button):
        self.index = 0
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="Last", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def last(self, interaction: Interaction, button):
        self.index = len(self.artists) - 1
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="Info", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def info(self, interaction: Interaction, button):
        """Show detailed information about current artist"""
        try:
            a = self.artists[self.index]
            
            # Create detailed info embed
            e = discord.Embed(
                title=f"ℹ️ {a['name']} - Detailed Info",
                color=discord.Color.gold()
            )
            
            # Get safe image URL
            safe_url = safe_image(a.get("image"))
            if safe_url:
                e.set_thumbnail(url=safe_url)
            
            # Comprehensive artist information
            e.add_field(name="🎼 Genre", value=a.get('genre', 'Unknown'), inline=True)
            e.add_field(name="🏆 Estimated Tier", value=a.get('estimated_tier', 'Unknown'), inline=True)
            e.add_field(name="👥 Popularity Score", value=str(a.get('popularity', 0)), inline=True)
            
            # YouTube statistics
            if a.get('subscribers', 0) > 0:
                e.add_field(name="📺 Subscribers", value=f"{a.get('subscribers', 0):,}", inline=True)
            
            if a.get('views', 0) > 0:
                e.add_field(name="👁️ Total Views", value=f"{a.get('views', 0):,}", inline=True)
            
            # Channel information
            if a.get('channel_id'):
                e.add_field(name="📺 Channel ID", value=a.get('channel_id'), inline=True)
            
            # Image information
            if a.get('image'):
                e.add_field(name="🖼️ Image URL", value=a.get('image'), inline=False)
                e.add_field(name="✅ Image Status", value="Available", inline=True)
            else:
                e.add_field(name="🖼️ Image Status", value="❌ Missing", inline=True)
            
            # Additional metadata
            if a.get('created_at'):
                e.add_field(name="📅 Added", value=a.get('created_at'), inline=True)
            
            if a.get('updated_at'):
                e.add_field(name="🔄 Updated", value=a.get('updated_at'), inline=True)
            
            # Set footer
            e.set_footer(text=f"Artist {self.index + 1} of {len(self.artists)}")
            
            await interaction.response.send_message(embed=e, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error showing artist info: {e}",
                ephemeral=True
            )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌")
    async def close(self, interaction: Interaction, button):
        await interaction.response.send_message(
            "🖼️ Gallery closed",
            ephemeral=True
        )


class CompactGalleryView(View):
    """
    Compact gallery view with minimal UI
    For mobile-friendly experience
    """
    
    def __init__(self, artists):
        super().__init__(timeout=None)
        self.artists = artists
        self.index = 0

    def embed(self):
        """Generate compact embed"""
        try:
            a = self.artists[self.index]
            
            # Get safe image URL
            safe_url = safe_image(a.get("image"))
            
            # Create compact embed
            e = discord.Embed(
                title=f"🎴 {a['name']}",
                description=f"🎼 {a.get('genre', 'Unknown')} • 🏆 {a.get('estimated_tier', 'Unknown')}",
                color=discord.Color.blue()
            )
            
            # Set image
            if safe_url:
                e.set_image(url=safe_url)
            
            # Add minimal info
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(a.get('estimated_tier', ''), "❓")
            
            e.add_field(name="🎼 Genre", value=a.get('genre', 'Unknown'), inline=True)
            e.add_field(name="🏆 Tier", value=f"{tier_emoji} {a.get('estimated_tier', 'Unknown')}", inline=True)
            e.add_field(name="👥 Popularity", value=str(a.get('popularity', 0)), inline=True)
            
            # Set footer
            e.set_footer(text=f"🖼️ {self.index + 1}/{len(self.artists)}")
            
            return e
            
        except Exception as e:
            # Fallback embed
            e = discord.Embed(
                title="❌ Gallery Error",
                description=f"Error displaying artist: {e}",
                color=discord.Color.red()
            )
            e.set_footer(text=f"🖼️ {self.index + 1}/{len(self.artists)}")
            return e

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: Interaction, button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button):
        self.index = min(len(self.artists) - 1, self.index + 1)
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )


class ThumbnailGalleryView(View):
    """
    Gallery view with thumbnails for quick navigation
    """
    
    def __init__(self, artists):
        super().__init__(timeout=None)
        self.artists = artists
        self.index = 0
        self.page_size = 6  # 6 thumbnails per page
        self.current_page = 0

    def embed(self):
        """Generate embed with thumbnails"""
        try:
            a = self.artists[self.index]
            
            # Get safe image URL
            safe_url = safe_image(a.get("image"))
            
            # Create main embed
            e = discord.Embed(
                title=f"🎴 {a['name']}",
                description=f"🎼 {a.get('genre', 'Unknown')} • 🏆 {a.get('estimated_tier', 'Unknown')}",
                color=discord.Color.blue()
            )
            
            # Set main image
            if safe_url:
                e.set_image(url=safe_url)
            
            # Add thumbnails
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.artists))
            
            thumbnail_text = ""
            for i in range(start_idx, end_idx):
                if i < len(self.artists):
                    artist = self.artists[i]
                    tier_emoji = {
                        "legendary": "🏆",
                        "platinum": "💎",
                        "gold": "🥇",
                        "silver": "🥈",
                        "bronze": "🥉",
                        "community": "👥"
                    }.get(artist.get('estimated_tier', ''), "❓")
                    
                    # Highlight current artist
                    if i == self.index:
                        thumbnail_text += f"👉 **{tier_emoji} {artist['name']}**\n"
                    else:
                        thumbnail_text += f"   {tier_emoji} {artist['name']}\n"
            
            if thumbnail_text:
                e.add_field(name="🖼️ Gallery", value=thumbnail_text, inline=False)
            
            # Add navigation info
            total_pages = (len(self.artists) + self.page_size - 1) // self.page_size
            e.set_footer(text=f"🖼️ {self.index + 1}/{len(self.artists)} • Page {self.current_page + 1}/{total_pages}")
            
            return e
            
        except Exception as e:
            # Fallback embed
            e = discord.Embed(
                title="❌ Gallery Error",
                description=f"Error displaying artist: {e}",
                color=discord.Color.red()
            )
            e.set_footer(text=f"🖼️ {self.index + 1}/{len(self.artists)}")
            return e

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: Interaction, button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button):
        self.index = min(len(self.artists) - 1, self.index + 1)
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    @discord.ui.button(label="Prev Page", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: Interaction, button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(
                embed=self.embed(),
                view=self
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: Interaction, button):
        total_pages = (len(self.artists) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(
                embed=self.embed(),
                view=self
            )
        else:
            await interaction.response.defer()

    @discord.ui.select(
        placeholder="Jump to artist...",
        custom_id="artist_jump"
    )
    async def artist_jump(self, interaction: Interaction, select):
        self.index = int(select.values[0])
        await interaction.response.edit_message(
            embed=self.embed(),
            view=self
        )

    def __init__(self, artists):
        super().__init__(timeout=None)
        self.artists = artists
        self.index = 0
        self.page_size = 6
        
        # Add jump options
        for i, artist in enumerate(artists):
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(artist.get('estimated_tier', ''), "❓")
            
            option = discord.SelectOption(
                label=f"{tier_emoji} {artist['name']}",
                description=f"{artist.get('genre', 'Unknown')} • {artist.get('estimated_tier', 'Unknown')}",
                value=str(i)
            )
            self.add_item(option)


# Utility functions
def create_gallery_view(artists, style="default"):
    """
    Create appropriate gallery view based on style preference
    
    Args:
        artists: List of artist dictionaries
        style: "default", "compact", or "thumbnail"
    
    Returns:
        GalleryView instance
    """
    if style == "compact":
        return CompactGalleryView(artists)
    elif style == "thumbnail":
        return ThumbnailGalleryView(artists)
    else:
        return GalleryView(artists)


def get_gallery_stats(artists):
    """
    Get statistics about the gallery
    
    Args:
        artists: List of artist dictionaries
    
    Returns:
        Dictionary with gallery statistics
    """
    try:
        total_artists = len(artists)
        
        # Count tiers
        tier_counts = {}
        for artist in artists:
            tier = artist.get('estimated_tier', 'unknown')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Count genres
        genre_counts = {}
        for artist in artists:
            genre = artist.get('genre', 'unknown')
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Count images
        image_count = sum(1 for artist in artists if artist.get('image'))
        
        # Calculate average popularity
        avg_popularity = sum(artist.get('popularity', 0) for artist in artists) / total_artists if total_artists > 0 else 0
        
        return {
            'total_artists': total_artists,
            'tier_distribution': tier_counts,
            'genre_distribution': genre_counts,
            'image_count': image_count,
            'image_coverage': f"{(image_count / total_artists * 100):.1f}%",
            'avg_popularity': round(avg_popularity, 1)
        }
        
    except Exception as e:
        print(f"Error calculating gallery stats: {e}")
        return {
            'total_artists': 0,
            'tier_distribution': {},
            'genre_distribution': {},
            'image_count': 0,
            'image_coverage': "0%",
            'avg_popularity': 0
        }


# Example usage
def example_usage():
    """Example of gallery usage"""
    
    # Mock artists data
    mock_artists = [
        {
            'name': 'Queen',
            'genre': 'Rock',
            'estimated_tier': 'legendary',
            'popularity': 95,
            'subscribers': 1000000,
            'views': 1000000000,
            'image': 'https://i.ytimg.com/vi/queen/maxresdefault.jpg',
            'channel_id': 'UC123'
        },
        {
            'name': 'Led Zeppelin',
            'genre': 'Rock',
            'estimated_tier': 'platinum',
            'popularity': 90,
            'subscribers': 800000,
            'views': 800000000,
            'image': 'https://i.ytimg.com/vi/ledzep/maxresdefault.jpg',
            'channel_id': 'UC456'
        }
    ]
    
    print("🖼️ Gallery View Examples:")
    print("========================")
    
    print("1. Standard Gallery View")
    gallery = GalleryView(mock_artists)
    print(f"   Total artists: {len(gallery.artists)}")
    print(f"   Current index: {gallery.index}")
    
    print("\n2. Compact Gallery View")
    compact = CompactGalleryView(mock_artists)
    print(f"   Total artists: {len(compact.artists)}")
    print(f"   Current index: {compact.index}")
    
    print("\n3. Thumbnail Gallery View")
    thumbnail = ThumbnailGalleryView(mock_artists)
    print(f"   Total artists: {len(thumbnail.artists)}")
    print(f"   Page size: {thumbnail.page_size}")
    
    print("\n4. Gallery Statistics")
    stats = get_gallery_stats(mock_artists)
    print(f"   Total artists: {stats['total_artists']}")
    print(f"   Image coverage: {stats['image_coverage']}")
    print(f"   Average popularity: {stats['avg_popularity']}")
    print(f"   Tier distribution: {stats['tier_distribution']}")


if __name__ == "__main__":
    example_usage()
