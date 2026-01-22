# services/youtube_client.py
import requests
import os
import asyncio
import aiohttp
from typing import Optional, Dict, List, Any
from datetime import datetime

YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_KEY")

class YouTubeClient:
    """YouTube API client for Music Legends bot"""
    
    def __init__(self):
        self.api_key = YOUTUBE_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _check_api_key(self):
        """Check if API key is configured"""
        if not self.api_key:
            raise ValueError("YouTube API key not found. Set YOUTUBE_API_KEY in .env.txt")
    
    async def search_channel(self, name: str) -> Optional[Dict[str, Any]]:
        """Search for a YouTube channel by name"""
        self._check_api_key()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/search"
        params = {
            "part": "snippet",
            "q": name,
            "type": "channel",
            "maxResults": 1,
            "key": self.api_key
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()

                if not data.get("items"):
                    return None

                ch = data["items"][0]

                return {
                    "name": ch["snippet"]["title"],
                    "channel_id": ch["id"]["channelId"],
                    "image": ch["snippet"]["thumbnails"]["high"]["url"],
                    "description": ch["snippet"]["description"],
                    "published_at": ch["snippet"]["publishedAt"]
                }
        except Exception as e:
            print(f"Error searching channel: {e}")
            return None

    async def channel_stats(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel statistics and details"""
        self._check_api_key()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/channels"
        params = {
            "part": "statistics,topicDetails,snippet",
            "id": channel_id,
            "key": self.api_key
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()

                if not data.get("items"):
                    return None

                c = data["items"][0]
                stats = c["statistics"]
                snippet = c["snippet"]

                return {
                    "subs": int(stats.get("subscriberCount", 0)),
                    "views": int(stats.get("viewCount", 0)),
                    "videos": int(stats.get("videoCount", 0)),
                    "topics": c.get("topicDetails", {}).get("topicCategories", []),
                    "created_at": snippet["publishedAt"],
                    "country": snippet.get("country"),
                    "custom_url": snippet.get("customUrl")
                }
        except Exception as e:
            print(f"Error getting channel stats: {e}")
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
