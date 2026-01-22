# spotify_integration.py
import requests
import json
import os
from typing import Dict, Optional, List
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv('.env.txt')

class SpotifyIntegration:
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('SPOTIFY_CLIENT_SECRET')
        self.access_token = None
        self.base_url = "https://api.spotify.com/v1"
    
    def _get_access_token(self) -> Optional[str]:
        """Get Spotify API access token using client credentials flow"""
        if not self.client_id or not self.client_secret:
            return None
        
        try:
            auth_url = "https://accounts.spotify.com/api/token"
            auth_response = requests.post(
                auth_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
            )
            
            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                self.access_token = auth_data['access_token']
                return self.access_token
            else:
                print(f"Spotify auth error: {auth_response.status_code}")
                return None
                
        except Exception as e:
            print(f"Spotify auth error: {e}")
            return None
    
    def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for artists on Spotify"""
        token = self._get_access_token()
        if not token:
            return self._mock_artist_search(query, limit)
        
        try:
            headers = {'Authorization': f'Bearer {token}'}
            params = {
                'q': query,
                'type': 'artist',
                'limit': min(limit, 10)
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                artists = []
                
                for artist in data.get('artists', {}).get('items', []):
                    artists.append({
                        'id': artist['id'],
                        'name': artist['name'],
                        'popularity': artist.get('popularity', 0),
                        'followers': artist.get('followers', {}).get('total', 0),
                        'genres': artist.get('genres', []),
                        'image_url': artist.get('images', [{}])[0].get('url', ''),
                        'external_urls': artist.get('external_urls', {}),
                        'spotify_url': artist.get('external_urls', {}).get('spotify', '')
                    })
                
                return artists
            else:
                print(f"Spotify search error: {response.status_code}")
                return self._mock_artist_search(query, limit)
                
        except Exception as e:
            print(f"Spotify search error: {e}")
            return self._mock_artist_search(query, limit)
    
    def get_artist_by_id(self, artist_id: str) -> Optional[Dict]:
        """Get detailed artist info by ID"""
        token = self._get_access_token()
        if not token:
            return self._mock_artist_response(f"Artist {artist_id}")
        
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{self.base_url}/artists/{artist_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                artist = response.json()
                return {
                    'id': artist['id'],
                    'name': artist['name'],
                    'popularity': artist.get('popularity', 0),
                    'followers': artist.get('followers', {}).get('total', 0),
                    'genres': artist.get('genres', []),
                    'image_url': artist.get('images', [{}])[0].get('url', ''),
                    'external_urls': artist.get('external_urls', {}),
                    'spotify_url': artist.get('external_urls', {}).get('spotify', '')
                }
            else:
                return self._mock_artist_response(f"Artist {artist_id}")
                
        except Exception as e:
            print(f"Spotify artist error: {e}")
            return self._mock_artist_response(f"Artist {artist_id}")
    
    def search_tracks(self, query: str, artist_id: str = None, limit: int = 10) -> List[Dict]:
        """Search for tracks, optionally by artist"""
        token = self._get_access_token()
        if not token:
            return self._mock_track_search(query, limit)
        
        try:
            headers = {'Authorization': f'Bearer {token}'}
            params = {
                'q': f"{query} artist:{artist_id}" if artist_id else query,
                'type': 'track',
                'limit': min(limit, 10)
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = []
                
                for track in data.get('tracks', {}).get('items', []):
                    tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artist_name': track['artists'][0]['name'] if track.get('artists') else '',
                        'artist_id': track['artists'][0]['id'] if track.get('artists') else '',
                        'album_name': track.get('album', {}).get('name', ''),
                        'image_url': track.get('album', {}).get('images', [{}])[0].get('url', ''),
                        'duration_ms': track.get('duration_ms', 0),
                        'external_urls': track.get('external_urls', {}),
                        'spotify_url': track.get('external_urls', {}).get('spotify', ''),
                        'preview_url': track.get('preview_url', '')
                    })
                
                return tracks
            else:
                return self._mock_track_search(query, limit)
                
        except Exception as e:
            print(f"Spotify track search error: {e}")
            return self._mock_track_search(query, limit)
    
    def validate_spotify_url(self, url: str) -> bool:
        """Validate if a URL is a valid Spotify URL"""
        return url.startswith('https://open.spotify.com/') and ('/artist/' in url or '/track/' in url)
    
    def extract_entity_id_from_url(self, url: str) -> Optional[str]:
        """Extract artist or track ID from Spotify URL"""
        try:
            if '/artist/' in url:
                return url.split('/artist/')[1].split('?')[0]
            elif '/track/' in url:
                return url.split('/track/')[1].split('?')[0]
            return None
        except:
            return None
    
    def generate_card_stats(self, artist_data: Dict) -> Dict:
        """Generate card stats based on Spotify data"""
        popularity = artist_data.get('popularity', 50)
        followers = artist_data.get('followers', 0)
        
        # Map popularity and followers to stats (0-92 scale for creator packs)
        base_stat = min(92, max(20, int(popularity * 0.92)))  # 20-92 based on popularity
        
        # Add variance based on followers
        follower_bonus = min(10, int(followers / 100000))  # Up to +10 for popular artists
        
        # Generate stats with some variance
        import random
        variance = random.randint(-5, 5)
        
        stats = {
            'impact': min(92, max(20, base_stat + variance + follower_bonus)),
            'skill': min(92, max(20, base_stat + random.randint(-3, 3))),
            'longevity': min(92, max(20, base_stat + random.randint(-5, 5))),
            'culture': min(92, max(20, base_stat + random.randint(-3, 3))),
            'hype': min(92, max(20, base_stat + variance + follower_bonus))
        }
        
        return stats
    
    def determine_rarity(self, artist_data: Dict) -> str:
        """Determine card rarity based on artist popularity"""
        popularity = artist_data.get('popularity', 50)
        followers = artist_data.get('followers', 0)
        
        # Rarity thresholds
        if popularity >= 80 or followers >= 1000000:
            return "Legendary"
        elif popularity >= 60 or followers >= 500000:
            return "Epic"
        elif popularity >= 40 or followers >= 100000:
            return "Rare"
        else:
            return "Common"
    
    # Mock methods for when API is not available
    def _mock_artist_search(self, query: str, limit: int) -> List[Dict]:
        """Mock artist search results"""
        return [{
            'id': f"mock_{query.lower().replace(' ', '_')}",
            'name': query,
            'popularity': 75,
            'followers': 1000000,
            'genres': ['pop', 'electronic'],
            'image_url': '',
            'external_urls': {'spotify': f"https://open.spotify.com/artist/{query.lower().replace(' ', '_')}"},
            'spotify_url': f"https://open.spotify.com/artist/{query.lower().replace(' ', '_')}"
        }]
    
    def _mock_track_search(self, query: str, limit: int) -> List[Dict]:
        """Mock track search results"""
        return [{
            'id': f"mock_track_{query.lower().replace(' ', '_')}",
            'name': f"{query} (Single)",
            'artist_name': query,
            'artist_id': f"mock_{query.lower().replace(' ', '_')}",
            'album_name': f"{query} Album",
            'image_url': '',
            'duration_ms': 180000,
            'external_urls': {'spotify': f"https://open.spotify.com/track/{query.lower().replace(' ', '_')}"},
            'spotify_url': f"https://open.spotify.com/track/{query.lower().replace(' ', '_')}",
            'preview_url': ''
        }]
    
    def _mock_artist_response(self, artist_name: str) -> Dict:
        """Mock artist response"""
        return {
            'name': artist_name,
            'id': f"mock_{artist_name.lower().replace(' ', '_')}",
            'external_urls': {
                'spotify': f"https://open.spotify.com/artist/{artist_name.lower().replace(' ', '_')}"
            },
            'images': [
                {'url': '', 'height': 300, 'width': 300}
            ],
            'genres': ['pop', 'electronic'],
            'popularity': 75,
            'followers': {'total': 1000000}
        }

# Global instance
spotify_integration = SpotifyIntegration()
