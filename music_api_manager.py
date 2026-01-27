# music_api_manager.py
"""
Unified Music API Manager for Music Legends
Handles Last.fm (primary) + YouTube (fallback) integration
"""

import os
from typing import List, Dict, Optional, Tuple
from lastfm_integration import lastfm_integration

class MusicAPIManager:
    """Manages music data from Last.fm and YouTube with smart fallbacks"""
    
    def __init__(self):
        self.lastfm = lastfm_integration
    
    async def search_artist_with_tracks(self, artist_name: str, limit: int = 10) -> Optional[Dict]:
        """
        Search for artist and get top tracks from Last.fm
        
        Args:
            artist_name: Artist name to search
            limit: Number of tracks to return
        
        Returns:
            Dict with artist_data and tracks, or None if not found
        """
        try:
            artist_data = self.lastfm.get_artist_info(artist_name)
            
            if not artist_data:
                print(f"❌ Artist '{artist_name}' not found on Last.fm")
                return None
            
            tracks = self.lastfm.get_top_tracks(artist_name, limit=limit)
            
            if not tracks:
                print(f"⚠️ No tracks found for '{artist_name}' on Last.fm")
                return None
            
            return {
                'artist': artist_data,
                'tracks': tracks,
                'source': 'lastfm'
            }
        
        except Exception as e:
            print(f"❌ Last.fm API error: {e}")
            return None
    
    async def search_youtube_videos(self, artist_name: str, max_results: int = 10) -> Optional[List[Dict]]:
        """
        Search YouTube for music videos
        
        Note: This method is not used in the current implementation.
        YouTube search is handled directly by youtube_integration module.
        
        Args:
            artist_name: Artist name to search
            max_results: Number of videos to return
        
        Returns:
            List of video data, or None if error
        """
        # YouTube integration is handled separately in menu_system.py
        # This method is kept for future use if needed
        return None
    
    def calculate_card_stats(self, playcount: int, pack_type: str = 'community', track_name: str = '') -> Dict[str, int]:
        """
        Calculate card stats based on Last.fm play count
        
        Args:
            playcount: Track play count from Last.fm
            pack_type: 'community' or 'gold'
        
        Returns:
            Dict with attack, defense, speed stats
        """
        base_ranges = {
            'community': (50, 85),
            'gold': (70, 92)
        }
        
        min_stat, max_stat = base_ranges.get(pack_type, (50, 85))
        
        # Normalize play count to stat range
        # 1B+ plays = max stats
        # 10M plays = mid stats
        # <1M plays = min stats
        
        if playcount >= 1_000_000_000:  # 1B+
            base_power = max_stat
        elif playcount >= 500_000_000:  # 500M+
            base_power = int(max_stat * 0.9)
        elif playcount >= 100_000_000:  # 100M+
            base_power = int(max_stat * 0.75)
        elif playcount >= 50_000_000:   # 50M+
            base_power = int(max_stat * 0.6)
        elif playcount >= 10_000_000:   # 10M+
            base_power = int(max_stat * 0.5)
        else:
            base_power = min_stat
        
        # Make stats deterministic based on play count (no randomness)
        # Use play count to create consistent variations
        import hashlib
        hash_seed = int(hashlib.md5(f"{playcount}{track_name}".encode()).hexdigest()[:8], 16)
        
        # Create consistent variations (0-4 range instead of random)
        attack_var = (hash_seed % 5)
        defense_var = ((hash_seed // 5) % 5) 
        speed_var = ((hash_seed // 25) % 5)
        
        attack = max(min_stat, min(max_stat, base_power + attack_var))
        defense = max(min_stat, min(max_stat, base_power + defense_var))
        speed = max(min_stat, min(max_stat, base_power + speed_var))
        
        return {
            'attack': attack,
            'defense': defense,
            'speed': speed
        }
    
    def determine_rarity(self, stats: Dict[str, int], pack_type: str = 'community') -> str:
        """
        Determine card rarity based on stats
        
        Args:
            stats: Dict with attack, defense, speed
            pack_type: 'community' or 'gold'
        
        Returns:
            Rarity string: common, rare, epic, legendary, mythic
        """
        avg_stat = (stats['attack'] + stats['defense'] + stats['speed']) / 3
        
        # Adjust thresholds for pack type
        rarity_boost = 10 if pack_type == 'gold' else 0
        
        if avg_stat >= (85 + rarity_boost):
            return 'mythic'
        elif avg_stat >= (75 + rarity_boost):
            return 'legendary'
        elif avg_stat >= (65 + rarity_boost):
            return 'epic'
        elif avg_stat >= (55 + rarity_boost):
            return 'rare'
        else:
            return 'common'
    
    def match_track_to_video(self, track_name: str, videos: List[Dict]) -> Optional[Dict]:
        """
        Match a Last.fm track to a YouTube video
        
        Args:
            track_name: Track name from Last.fm
            videos: List of YouTube video data
        
        Returns:
            Best matching video or None
        """
        track_lower = track_name.lower()
        
        for video in videos:
            video_title = video.get('title', '').lower()
            
            # Simple contains check
            if track_lower in video_title:
                return video
        
        # No exact match, return first video as fallback
        return videos[0] if videos else None
    
    def format_track_for_card(
        self,
        track: Dict,
        artist_name: str,
        pack_type: str = 'community',
        image_url: str = None,
        video_url: str = None
    ) -> Dict:
        """
        Format track data into card data structure
        
        Args:
            track: Track data from Last.fm
            artist_name: Artist name
            pack_type: 'community' or 'gold'
            image_url: Optional image URL (Last.fm or YouTube)
            video_url: Optional YouTube video URL
        
        Returns:
            Card data dict
        """
        playcount = track.get('playcount', 0)
        stats = self.calculate_card_stats(playcount, pack_type, track['name'])
        rarity = self.determine_rarity(stats, pack_type)
        
        # Use provided image or fallback to track image
        if not image_url:
            image_url = track.get('image_xlarge') or track.get('image_large', '')
        
        return {
            'name': track['name'],
            'artist': artist_name,
            'attack': stats['attack'],
            'defense': stats['defense'],
            'speed': stats['speed'],
            'rarity': rarity,
            'image_url': image_url,
            'video_url': video_url or '',
            'playcount': playcount,
            'source': 'lastfm'
        }


# Global instance
music_api = MusicAPIManager()


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("🎵 Music API Manager Test\n")
        
        # Test Last.fm search
        print("1. Searching Last.fm for 'Drake'...")
        result = await music_api.search_artist_with_tracks("Drake", limit=5)
        
        if result:
            artist = result['artist']
            tracks = result['tracks']
            
            print(f"   Artist: {artist['name']}")
            print(f"   Listeners: {artist['listeners']:,}")
            print(f"   Image: {artist['image_xlarge'][:50]}...")
            print(f"\n   Top Tracks:")
            
            for i, track in enumerate(tracks, 1):
                stats = music_api.calculate_card_stats(track['playcount'], 'gold', track['name'])
                rarity = music_api.determine_rarity(stats, 'gold')
                print(f"   {i}. {track['name']}")
                print(f"      Plays: {track['playcount']:,}")
                print(f"      Stats: {stats['attack']}/{stats['defense']}/{stats['speed']}")
                print(f"      Rarity: {rarity.upper()}")
        
        print("\n✅ Test complete!")
    
    asyncio.run(test())
