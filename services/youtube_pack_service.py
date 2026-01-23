# services/youtube_pack_service.py
"""
YouTube-based pack creation service for Music Legends
Integrates YouTube Data API v3 with Discord bot pack creation
"""

from typing import Dict, List, Optional, Any
from services.youtube_client import youtube_client
from database import DatabaseManager
import random

class YouTubePackService:
    """Service for creating card packs from YouTube artist data"""
    
    def __init__(self):
        self.youtube = youtube_client
        self.db = DatabaseManager()
    
    async def search_artist_channels(self, artist_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for artist channels on YouTube
        Returns top matching channels with metadata
        """
        # Search for channel
        channel = await self.youtube.search_channel(f"{artist_name} music official")
        
        if not channel:
            return []
        
        # Get channel stats
        stats = await self.youtube.channel_stats(channel['channel_id'])
        
        if not stats:
            stats = {
                "subs": 0,
                "views": 0,
                "videos": 0,
                "topics": []
            }
        
        # Combine channel info with stats
        artist_data = {
            "name": channel['name'],
            "channel_id": channel['channel_id'],
            "image": channel['image'],
            "description": channel['description'],
            "subscribers": stats['subs'],
            "total_views": stats['views'],
            "video_count": stats['videos'],
            "topics": stats.get('topics', []),
            "youtube_url": f"https://youtube.com/channel/{channel['channel_id']}"
        }
        
        return [artist_data]
    
    def calculate_tier_from_youtube(self, subscribers: int, views: int) -> str:
        """
        Calculate card tier based on YouTube metrics
        
        Tier thresholds:
        - Legendary: 10M+ subs or 1B+ views
        - Platinum: 1M+ subs or 100M+ views
        - Gold: 100K+ subs or 10M+ views
        - Community: < 100K subs
        """
        if subscribers >= 10_000_000 or views >= 1_000_000_000:
            return "legendary"
        elif subscribers >= 1_000_000 or views >= 100_000_000:
            return "platinum"
        elif subscribers >= 100_000 or views >= 10_000_000:
            return "gold"
        else:
            return "community"
    
    def generate_card_stats(self, subscribers: int, views: int, video_count: int) -> Dict[str, int]:
        """
        Generate card stats based on YouTube metrics
        Stats range from 20-92 for creator packs
        """
        # Base stat from subscribers (logarithmic scale)
        if subscribers > 0:
            sub_score = min(92, max(20, int(20 + (subscribers / 100_000) * 2)))
        else:
            sub_score = 20
        
        # View bonus
        if views > 0:
            view_bonus = min(15, int(views / 10_000_000))
        else:
            view_bonus = 0
        
        # Video count bonus (consistency)
        video_bonus = min(10, int(video_count / 50))
        
        # Generate stats with variance
        base_stat = min(92, max(20, sub_score + view_bonus + video_bonus))
        
        stats = {
            'impact': min(92, max(20, base_stat + random.randint(-3, 3))),
            'skill': min(92, max(20, base_stat + random.randint(-5, 5))),
            'longevity': min(92, max(20, base_stat + random.randint(-2, 2))),
            'culture': min(92, max(20, base_stat + random.randint(-4, 4))),
            'hype': min(92, max(20, base_stat + random.randint(-3, 3)))
        }
        
        return stats
    
    async def create_artist_card(self, artist_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a card from YouTube artist data
        Returns card data ready for database insertion
        """
        # Calculate tier
        tier = self.calculate_tier_from_youtube(
            artist_data['subscribers'],
            artist_data['total_views']
        )
        
        # Generate stats
        stats = self.generate_card_stats(
            artist_data['subscribers'],
            artist_data['total_views'],
            artist_data['video_count']
        )
        
        # Create card data
        card_data = {
            "name": artist_data['name'],
            "rarity": tier,
            "youtube_channel_id": artist_data['channel_id'],
            "youtube_url": artist_data['youtube_url'],
            "image_url": artist_data['image'],
            "description": artist_data['description'][:200] if artist_data['description'] else "",
            "card_type": "artist",
            "era": "Modern",
            **stats,
            "subscribers": artist_data['subscribers'],
            "total_views": artist_data['total_views']
        }
        
        return card_data
    
    def add_card_to_pack(self, pack_id: str, card_data: Dict[str, Any]) -> bool:
        """
        Add a card to a creator pack
        Returns True if successful
        """
        return self.db.add_card_to_pack(pack_id, card_data)
    
    def get_pack_info(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Get pack information from database"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pack_id, name, description, pack_size, status, cards_data
                FROM creator_packs
                WHERE pack_id = ?
            """, (pack_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

# Global instance
youtube_pack_service = YouTubePackService()
