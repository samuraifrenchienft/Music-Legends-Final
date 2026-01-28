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
        print(f"🔍 YouTube API Key present: {bool(self.api_key)}")
        if self.api_key:
            print(f"   Key starts with: {self.api_key[:10]}...")
        
        if not self.api_key:
            print(f"❌ FATAL: No YouTube API key configured!")
            print(f"   Set YOUTUBE_API_KEY in Railway environment variables")
            raise ValueError("YouTube API key is required. Mock data is disabled.")
        
        try:
            # Build search query
            if song_name:
                query = f"{artist_name} {song_name} official music video"
            else:
                query = f"{artist_name} official music video"
            
            print(f"🔍 Searching YouTube for: {query}")
            
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': limit,
                'videoCategoryId': '10',  # Music category
                'key': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/search", params=params)
            print(f"📡 YouTube API response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                videos = []
                
                for item in data.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item['snippet']
                    title = snippet['title'].lower()
                    channel = snippet['channelTitle'].lower()
                    
                    if ('topic' in channel or
                        'audio library' in channel.lower() or
                        'no copyright' in title.lower()):
                        print(f"🚫 Filtering out spam: {snippet['title']}")
                        continue
                    
                    thumbnail_url = snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url']
                    
                    videos.append({
                        'video_id': video_id,
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'channel_title': snippet['channelTitle'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail_url': thumbnail_url,
                        'youtube_url': f"https://www.youtube.com/watch?v={video_id}"
                    })
                
                print(f"✅ Found {len(videos)} YouTube videos")
                if videos:
                    print(f"   First video thumbnail: {videos[0]['thumbnail_url'][:50]}...")
                return videos
            else:
                print(f"❌ YouTube API error {response.status_code}: {response.text[:200]}")
                raise Exception(f"YouTube API returned error {response.status_code}")
                
        except Exception as e:
            print(f"❌ YouTube search error: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise instead of mock data
    
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
            raise ValueError("YouTube API key is required for video info")
        
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
            return None
    
# Global instance - load API key from environment
import os
youtube_integration = YouTubeIntegration(api_key=os.getenv('YOUTUBE_API_KEY'))
