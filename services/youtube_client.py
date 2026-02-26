# services/youtube_client.py
import os
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime

YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")

# Import Google API client
try:
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("google-api-python-client not installed - using mock data only")

class YouTubeClient:
    """YouTube API client for Music Legends bot using Google API Python Client"""
    
    def __init__(self):
        self.api_key = YOUTUBE_KEY
        self.youtube = None
        
        # Log API key status
        if self.api_key:
            print(f"✅ YouTube API key found (length: {len(self.api_key)})")
        else:
            print("❌ YouTube API key NOT found - will use mock data")
        
        # Initialize YouTube client if API available and key configured
        if GOOGLE_API_AVAILABLE and self.api_key:
            try:
                self.youtube = build("youtube", "v3", developerKey=self.api_key)
                print("✅ YouTube API client initialized successfully - REAL DATA MODE")
            except Exception as e:
                print(f"❌ Failed to initialize YouTube client: {e}")
                self.youtube = None
        elif not GOOGLE_API_AVAILABLE:
            print("❌ google-api-python-client not installed")
        else:
            print("⚠️ YouTube API key missing - using MOCK DATA")
    
    def _check_api_key(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
        
    async def search_channel(self, name: str) -> Optional[Dict[str, Any]]:
        """Search for a YouTube channel by name using async executor - REAL DATA ONLY"""
        if not self.youtube:
            print(f"❌ CRITICAL: YouTube API not initialized - check API key and google-api-python-client")
            return None
        
        loop = asyncio.get_running_loop()
        
        def _search():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.search().list(
                    q=name,
                    part="snippet",
                    type="channel",
                    maxResults=1
                )
                result = request.execute()
                print(f"✅ YouTube API search successful for: {name}")
                return result
            except Exception as e:
                print(f"❌ YouTube API error: {e}")
                return None
        
        try:
            # Run blocking call in executor
            result = await loop.run_in_executor(None, _search)
            
            if not result or not result.get("items"):
                print(f"⚠️ No YouTube results found for: {name}")
                return None
            
            ch = result["items"][0]
            snippet = ch["snippet"]
            
            return {
                "name": snippet["title"],
                "channel_id": ch["id"]["channelId"],
                "image": snippet["thumbnails"]["high"]["url"] if snippet.get("thumbnails", {}).get("high") else "",
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", "")
            }
        except Exception as e:
            print(f"❌ Error searching channel: {e}")
            return None

    async def channel_stats(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel statistics and details using async executor - REAL DATA ONLY"""
        if not self.youtube:
            print(f"❌ CRITICAL: YouTube API not initialized - cannot get stats")
            return None
        
        loop = asyncio.get_running_loop()
        
        def _get_stats():
            """Blocking YouTube API call"""
            try:
                request = self.youtube.channels().list(
                    part="statistics,topicDetails,snippet",
                    id=channel_id
                )
                result = request.execute()
                print(f"✅ YouTube API stats retrieved for channel: {channel_id}")
                return result
            except Exception as e:
                print(f"❌ YouTube API error getting stats: {e}")
                return None
        
        try:
            # Run blocking call in executor
            result = await loop.run_in_executor(None, _get_stats)
            
            if not result or not result.get("items"):
                print(f"⚠️ No stats found for channel: {channel_id}")
                return None
            
            c = result["items"][0]
            stats = c.get("statistics", {})
            snippet = c.get("snippet", {})
            
            return {
                "subs": int(stats.get("subscriberCount", 0)),
                "views": int(stats.get("viewCount", 0)),
                "videos": int(stats.get("videoCount", 0)),
                "topics": c.get("topicDetails", {}).get("topicCategories", []),
                "created_at": snippet.get("publishedAt", ""),
                "country": snippet.get("country"),
                "custom_url": snippet.get("customUrl")
            }
        except Exception as e:
            print(f"❌ Error getting channel stats: {e}")
            return None

    async def search_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for videos by query"""
        self._check_api_key()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": self.api_key
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                    
                data = await response.json()
                videos = []

                for item in data.get("items", []):
                    video = {
                        "title": item["snippet"]["title"],
                        "video_id": item["id"]["videoId"],
                        "channel": item["snippet"]["channelTitle"],
                        "description": item["snippet"]["description"][:200] + "...",
                        "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                        "published_at": item["snippet"]["publishedAt"]
                    }
                    videos.append(video)

                return videos
        except Exception as e:
            print(f"Error searching videos: {e}")
            return []

    async def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed video information"""
        self._check_api_key()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/videos"
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": self.api_key
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()

                if not data.get("items"):
                    return None

                video = data["items"][0]
                snippet = video["snippet"]
                stats = video["statistics"]
                content = video["contentDetails"]

                return {
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "channel": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "tags": snippet.get("tags", []),
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "duration": content["duration"],
                    "definition": content["definition"]
                }
        except Exception as e:
            print(f"Error getting video details: {e}")
            return None

    async def get_channel_videos(self, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get recent videos from a channel"""
        self._check_api_key()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": max_results,
            "key": self.api_key
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                    
                data = await response.json()
                videos = []

                for item in data.get("items", []):
                    video = {
                        "title": item["snippet"]["title"],
                        "video_id": item["id"]["videoId"],
                        "description": item["snippet"]["description"][:200] + "...",
                        "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                        "published_at": item["snippet"]["publishedAt"]
                    }
                    videos.append(video)

                return videos
        except Exception as e:
            print(f"Error getting channel videos: {e}")
            return []

    async def get_trending_music(self, region_code: str = "US") -> List[Dict[str, Any]]:
        """Get trending music videos"""
        self._check_api_key()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/videos"
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "videoCategoryId": "10",  # Music category
            "regionCode": region_code,
            "maxResults": 10,
            "key": self.api_key
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                    
                data = await response.json()
                videos = []

                for item in data.get("items", []):
                    video = {
                        "title": item["snippet"]["title"],
                        "video_id": item["id"],
                        "channel": item["snippet"]["channelTitle"],
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        "views": int(item["statistics"].get("viewCount", 0)),
                        "published_at": item["snippet"]["publishedAt"]
                    }
                    videos.append(video)

                return videos
        except Exception as e:
            print(f"Error getting trending music: {e}")
            return []

    # Synchronous methods for backward compatibility
    def search_channel_sync(self, name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of search_channel"""
        return asyncio.run(self.search_channel(name))

    def channel_stats_sync(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of channel_stats"""
        return asyncio.run(self.channel_stats(channel_id))

    def search_videos_sync(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Synchronous version of search_videos"""
        return asyncio.run(self.search_videos(query, max_results))

    def get_video_details_sync(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of get_video_details"""
        return asyncio.run(self.get_video_details(video_id))


# Global instance for easy access
youtube_client = YouTubeClient()

# Helper functions for common operations
async def search_music_artist(artist_name: str) -> Optional[Dict[str, Any]]:
    """Search for a music artist's channel"""
    return await youtube_client.search_channel(f"{artist_name} music official")

async def get_music_videos(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search for music videos"""
    return await youtube_client.search_videos(f"{query} music", max_results)

async def get_trending_songs(region: str = "US") -> List[Dict[str, Any]]:
    """Get trending songs"""
    return await youtube_client.get_trending_music(region)


# Example usage
async def example_usage():
    """Example of how to use the YouTube client"""
    
    # Search for an artist
    artist = await search_music_artist("Taylor Swift")
    if artist:
        print(f"Found artist: {artist['name']}")
        print(f"Channel ID: {artist['channel_id']}")
        
        # Get artist stats
        stats = await youtube_client.channel_stats(artist['channel_id'])
        if stats:
            print(f"Subscribers: {stats['subs']:,}")
            print(f"Total views: {stats['views']:,}")
        
        # Get recent videos
        videos = await youtube_client.get_channel_videos(artist['channel_id'], 5)
        print(f"Recent videos: {len(videos)}")
    
    # Search for music videos
    videos = await get_music_videos("pop", 3)
    print(f"Found {len(videos)} music videos")
    
    # Get trending music
    trending = await get_trending_songs()
    print(f"Trending songs: {len(trending)}")


if __name__ == "__main__":
    asyncio.run(example_usage())
