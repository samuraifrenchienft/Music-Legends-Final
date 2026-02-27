# lastfm_integration.py
"""
Last.fm API Integration for Music Legends
Primary source for artist info, track search, and popularity data
"""

import requests
from typing import List, Dict, Optional

from .config import settings

class LastFmIntegration:
    """Last.fm API client for artist and track data"""
    
    def __init__(self):
        self.api_key = settings.LASTFM_API_KEY
        self.shared_secret = settings.LASTFM_SHARED_SECRET
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        
        if not self.api_key:
            print("⚠️ LASTFM_API_KEY not found in environment variables")
            print("📝 Get your key at: https://www.last.fm/api/account/create")
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make request to Last.fm API"""
        try:
            params['api_key'] = self.api_key
            params['format'] = 'json'
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Last.fm API error: {e}")
            return None
    
    def search_artist(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """
        Search for artists by name
        
        Returns:
            List of artists with name, listeners, playcount, images, url
        """
        params = {
            'method': 'artist.search',
            'artist': artist_name,
            'limit': limit
        }
        
        data = self._make_request(params)
        
        if data and 'results' in data and 'artistmatches' in data['results']:
            artists = data['results']['artistmatches']['artist']
            
            # Normalize to list if single result
            if isinstance(artists, dict):
                artists = [artists]
            
            return [self._format_artist(artist) for artist in artists]
        
        return []
    
    def get_artist_info(self, artist_name: str) -> Optional[Dict]:
        """
        Get detailed artist information
        
        Returns:
            Artist data with bio, images, stats, similar artists, tags
        """
        params = {
            'method': 'artist.getInfo',
            'artist': artist_name,
            'autocorrect': 1  # Auto-correct artist name
        }
        
        data = self._make_request(params)
        
        if data and 'artist' in data:
            return self._format_artist_detailed(data['artist'])
        
        return None
    
    def get_top_tracks(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """
        Get artist's top tracks
        
        Returns:
            List of tracks with name, playcount, listeners, url, images
        """
        params = {
            'method': 'artist.getTopTracks',
            'artist': artist_name,
            'limit': limit
        }
        
        data = self._make_request(params)
        
        if data and 'toptracks' in data and 'track' in data['toptracks']:
            tracks = data['toptracks']['track']
            
            # Normalize to list if single result
            if isinstance(tracks, dict):
                tracks = [tracks]
            
            return [self._format_track(track) for track in tracks]
        
        return []
    
    def search_track(self, track_name: str, artist_name: str = "", limit: int = 10) -> List[Dict]:
        """
        Search for tracks
        
        Args:
            track_name: Song name to search
            artist_name: Optional artist filter
            limit: Max results
        
        Returns:
            List of tracks
        """
        params = {
            'method': 'track.search',
            'track': track_name,
            'limit': limit
        }
        
        if artist_name:
            params['artist'] = artist_name
        
        data = self._make_request(params)
        
        if data and 'results' in data and 'trackmatches' in data['results']:
            tracks = data['results']['trackmatches']['track']
            
            # Normalize to list
            if isinstance(tracks, dict):
                tracks = [tracks]
            
            return [self._format_track(track) for track in tracks]
        
        return []
    
    def get_track_info(self, track_name: str, artist_name: str) -> Optional[Dict]:
        """
        Get detailed track information
        
        Returns:
            Track data with playcount, listeners, album, tags
        """
        params = {
            'method': 'track.getInfo',
            'track': track_name,
            'artist': artist_name,
            'autocorrect': 1
        }
        
        data = self._make_request(params)
        
        if data and 'track' in data:
            return self._format_track_detailed(data['track'])
        
        return None
    
    def _format_artist(self, artist: Dict) -> Dict:
        """Format artist data from search results"""
        images = self._extract_images(artist.get('image', []))
        
        return {
            'name': artist.get('name', ''),
            'listeners': int(artist.get('listeners', 0)),
            'playcount': int(artist.get('playcount', 0)) if 'playcount' in artist else 0,
            'url': artist.get('url', ''),
            'image_small': images.get('small', ''),
            'image_medium': images.get('medium', ''),
            'image_large': images.get('large', ''),
            'image_xlarge': images.get('extralarge', ''),
            'mbid': artist.get('mbid', '')
        }
    
    def _format_artist_detailed(self, artist: Dict) -> Dict:
        """Format detailed artist data"""
        images = self._extract_images(artist.get('image', []))
        
        # Extract bio
        bio = artist.get('bio', {})
        bio_summary = bio.get('summary', '') if isinstance(bio, dict) else ''
        
        # Extract tags
        tags = []
        if 'tags' in artist and 'tag' in artist['tags']:
            tag_list = artist['tags']['tag']
            if isinstance(tag_list, list):
                tags = [tag.get('name', '') for tag in tag_list]
            elif isinstance(tag_list, dict):
                tags = [tag_list.get('name', '')]
        
        # Extract similar artists
        similar = []
        if 'similar' in artist and 'artist' in artist['similar']:
            similar_list = artist['similar']['artist']
            if isinstance(similar_list, list):
                similar = [s.get('name', '') for s in similar_list]
            elif isinstance(similar_list, dict):
                similar = [similar_list.get('name', '')]
        
        return {
            'name': artist.get('name', ''),
            'listeners': int(artist.get('stats', {}).get('listeners', 0)),
            'playcount': int(artist.get('stats', {}).get('playcount', 0)),
            'url': artist.get('url', ''),
            'image_small': images.get('small', ''),
            'image_medium': images.get('medium', ''),
            'image_large': images.get('large', ''),
            'image_xlarge': images.get('extralarge', ''),
            'bio': bio_summary,
            'tags': tags,
            'similar_artists': similar,
            'mbid': artist.get('mbid', '')
        }
    
    def _format_track(self, track: Dict) -> Dict:
        """Format track data"""
        images = self._extract_images(track.get('image', []))
        
        return {
            'name': track.get('name', ''),
            'artist': track.get('artist', {}).get('name', '') if isinstance(track.get('artist'), dict) else track.get('artist', ''),
            'listeners': int(track.get('listeners', 0)),
            'playcount': int(track.get('playcount', 0)) if 'playcount' in track else 0,
            'url': track.get('url', ''),
            'image_small': images.get('small', ''),
            'image_medium': images.get('medium', ''),
            'image_large': images.get('large', ''),
            'image_xlarge': images.get('extralarge', ''),
            'mbid': track.get('mbid', '')
        }
    
    def _format_track_detailed(self, track: Dict) -> Dict:
        """Format detailed track data"""
        images = self._extract_images(track.get('image', []))
        
        # Extract album info
        album = track.get('album', {})
        album_name = album.get('title', '') if isinstance(album, dict) else ''
        album_image = self._extract_images(album.get('image', [])).get('extralarge', '') if isinstance(album, dict) else ''
        
        # Extract tags
        tags = []
        if 'toptags' in track and 'tag' in track['toptags']:
            tag_list = track['toptags']['tag']
            if isinstance(tag_list, list):
                tags = [tag.get('name', '') for tag in tag_list]
            elif isinstance(tag_list, dict):
                tags = [tag_list.get('name', '')]
        
        return {
            'name': track.get('name', ''),
            'artist': track.get('artist', {}).get('name', '') if isinstance(track.get('artist'), dict) else '',
            'listeners': int(track.get('listeners', 0)),
            'playcount': int(track.get('playcount', 0)),
            'url': track.get('url', ''),
            'image_small': images.get('small', ''),
            'image_medium': images.get('medium', ''),
            'image_large': images.get('large', ''),
            'image_xlarge': images.get('extralarge', ''),
            'album': album_name,
            'album_image': album_image,
            'tags': tags,
            'mbid': track.get('mbid', '')
        }
    
    def _extract_images(self, image_list: List[Dict]) -> Dict[str, str]:
        """Extract image URLs by size"""
        images = {
            'small': '',
            'medium': '',
            'large': '',
            'extralarge': ''
        }
        
        if not isinstance(image_list, list):
            return images
        
        for img in image_list:
            if isinstance(img, dict):
                size = img.get('size', '')
                url = img.get('#text', '')
                if size in images:
                    images[size] = url
        
        return images
    
    def calculate_popularity_score(self, listeners: int, playcount: int) -> int:
        """
        Calculate popularity score (0-100) based on Last.fm stats
        
        Args:
            listeners: Number of unique listeners
            playcount: Total play count
        
        Returns:
            Score from 0-100
        """
        # Normalize listeners (log scale)
        # 1M listeners = 60 points, 10M = 80 points, 100M = 100 points
        listener_score = min(100, (listeners / 1000000) ** 0.5 * 30)
        
        # Normalize playcount (log scale)
        # 10M plays = 40 points, 100M = 60 points, 1B = 80 points
        playcount_score = min(100, (playcount / 10000000) ** 0.5 * 40)
        
        # Weighted average (60% listeners, 40% playcount)
        total_score = (listener_score * 0.6) + (playcount_score * 0.4)
        
        return int(total_score)


# Global instance
lastfm_integration = LastFmIntegration()


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    print("🎵 Last.fm Integration Test\n")
    
    # Test artist search
    print("1. Searching for 'Drake'...")
    artists = lastfm_integration.search_artist("Drake", limit=3)
    for artist in artists:
        print(f"   - {artist['name']}: {artist['listeners']:,} listeners")
    
    print()
    
    # Test artist info
    print("2. Getting detailed info for 'Drake'...")
    artist_info = lastfm_integration.get_artist_info("Drake")
    if artist_info:
        print(f"   Name: {artist_info['name']}")
        print(f"   Listeners: {artist_info['listeners']:,}")
        print(f"   Playcount: {artist_info['playcount']:,}")
        print(f"   Tags: {', '.join(artist_info['tags'][:5])}")
        print(f"   Image: {artist_info['image_xlarge'][:50]}...")
        
        # Calculate popularity
        score = lastfm_integration.calculate_popularity_score(
            artist_info['listeners'],
            artist_info['playcount']
        )
        print(f"   Popularity Score: {score}/100")
    
    print()
    
    # Test top tracks
    print("3. Getting top tracks for 'Drake'...")
    tracks = lastfm_integration.get_top_tracks("Drake", limit=5)
    for i, track in enumerate(tracks, 1):
        print(f"   {i}. {track['name']} - {track['playcount']:,} plays")
    
    print()
    
    # Test track search
    print("4. Searching for track 'Hotline Bling'...")
    tracks = lastfm_integration.search_track("Hotline Bling", artist_name="Drake", limit=1)
    if tracks:
        track = tracks[0]
        print(f"   Found: {track['name']} by {track['artist']}")
        print(f"   Listeners: {track['listeners']:,}")
    
    print("\n✅ Test complete!")
