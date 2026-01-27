# youtube_integration.py
import requests
import json
from typing import Dict, Optional, List

class YouTubeIntegration:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def search_music_video(self, artist_name: str, song_name: str = None, limit: int = 10) -> List[Dict]:
        """Search for music videos on YouTube"""
        if not self.api_key:
            return self._mock_search_results(artist_name, song_name)[:limit]
        
        try:
            # Build search query
            if song_name:
                query = f"{artist_name} {song_name} official music video"
            else:
                query = f"{artist_name} official music video"
            
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': 3,
                'videoCategoryId': '10',  # Music category
                'key': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/search", params=params)
            
            if response.status_code == 200:
                data = response.json()
                videos = []
                
                for item in data.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item['snippet']
                    
                    videos.append({
                        'video_id': video_id,
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'channel_title': snippet['channelTitle'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail_url': snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url'],
                        'youtube_url': f"https://www.youtube.com/watch?v={video_id}"
                    })
                
                return videos
            else:
                return self._mock_search_results(artist_name, song_name)
                
        except Exception as e:
            print(f"YouTube search error: {e}")
            return self._mock_search_results(artist_name, song_name)
    
    def validate_youtube_url(self, url: str) -> bool:
        """Validate if a URL is a valid YouTube URL"""
        return url.startswith('https://www.youtube.com/watch?v=') or url.startswith('https://youtu.be/')
    
    def extract_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        try:
            if 'youtube.com/watch?v=' in url:
                return url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                return url.split('youtu.be/')[1].split('?')[0]
            return None
        except:
            return None
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """Get video information by ID"""
        if not self.api_key:
            return self._mock_video_info(video_id)
        
        try:
            params = {
                'part': 'snippet',
                'id': video_id,
                'key': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/videos", params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                if items:
                    snippet = items[0]['snippet']
                    return {
                        'video_id': video_id,
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'channel_title': snippet['channelTitle'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail_url': snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url'],
                        'youtube_url': f"https://www.youtube.com/watch?v={video_id}"
                    }
            
            return None
        except Exception as e:
            print(f"YouTube video info error: {e}")
            return self._mock_video_info(video_id)
    
    # Mock methods for when API is not available
    def _mock_search_results(self, artist_name: str, song_name: str = None) -> List[Dict]:
        """Mock YouTube search results with realistic data"""
        # Popular songs for common artists
        mock_songs = {
            'drake': [
                "God's Plan", "One Dance", "Hotline Bling", "In My Feelings", "Nice For What",
                "Passionfruit", "Started From the Bottom", "Hold On, We're Going Home", 
                "Controlla", "Too Good"
            ],
            'kendrick lamar': [
                "HUMBLE.", "DNA.", "Alright", "Swimming Pools", "m.A.A.d city",
                "King Kunta", "Bitch, Don't Kill My Vibe", "Money Trees", "Poetic Justice", "i"
            ],
            'j cole': [
                "Middle Child", "No Role Modelz", "ATM", "Kevin's Heart", "GOMD",
                "Wet Dreamz", "Power Trip", "Crooked Smile", "Work Out", "She Knows"
            ],
            'default': []
        }
        
        # Get appropriate song list
        artist_key = artist_name.lower()
        songs = mock_songs.get(artist_key, mock_songs['default'])
        
        # If specific song requested, return just that
        if song_name:
            return [{
                'video_id': f"mock_{artist_name.lower().replace(' ', '_')}_{song_name.lower().replace(' ', '_')}",
                'title': f"{artist_name} - {song_name} (Official Music Video)",
                'description': f"Official music video for {song_name} by {artist_name}",
                'channel_title': f"{artist_name} VEVO",
                'published_at': "2023-01-01T00:00:00Z",
                'thumbnail_url': f"https://i.ytimg.com/vi/mock_{abs(hash(song_name)) % 1000:03x}/maxresdefault.jpg",
                'youtube_url': f"https://www.youtube.com/watch?v=mock_{song_name.lower().replace(' ', '_')}"
            }]
        
        # Return multiple songs
        videos = []
        if songs:
            # Use predefined songs
            for i, song in enumerate(songs):
                videos.append({
                    'video_id': f"mock_{i}_{artist_name.lower().replace(' ', '_')}",
                    'title': f"{artist_name} - {song} (Official Music Video)",
                    'description': f"Official music video for {song} by {artist_name}",
                    'channel_title': f"{artist_name} VEVO",
                    'published_at': "2023-01-01T00:00:00Z",
                    'thumbnail_url': f"https://i.ytimg.com/vi/mock_{i:03x}/maxresdefault.jpg",
                    'youtube_url': f"https://www.youtube.com/watch?v=mock_{i}"
                })
        else:
            # Generate generic songs for unknown artists
            for i in range(10):
                song_titles = ["Hit Single", "Popular Track", "Chart Topper", "Fan Favorite", "Classic Hit", 
                             "New Release", "Radio Hit", "Viral Track", "Top Song", "Greatest Hit"]
                videos.append({
                    'video_id': f"mock_{i}_{artist_name.lower().replace(' ', '_')}",
                    'title': f"{artist_name} - {song_titles[i]} (Official Music Video)",
                    'description': f"Official music video by {artist_name}",
                    'channel_title': f"{artist_name} VEVO",
                    'published_at': "2023-01-01T00:00:00Z",
                    'thumbnail_url': f"https://i.ytimg.com/vi/mock_{i:03x}/maxresdefault.jpg",
                    'youtube_url': f"https://www.youtube.com/watch?v=mock_{i}"
                })
        
        return videos
    
    def _mock_video_info(self, video_id: str) -> Dict:
        """Mock video info"""
        return {
            'video_id': video_id,
            'title': f"Music Video {video_id}",
            'description': "Official music video",
            'channel_title': "Artist VEVO",
            'published_at': "2023-01-01T00:00:00Z",
            'thumbnail_url': '',
            'youtube_url': f"https://www.youtube.com/watch?v={video_id}"
        }

# Global instance - load API key from environment
import os
youtube_integration = YouTubeIntegration(api_key=os.getenv('YOUTUBE_API_KEY'))
