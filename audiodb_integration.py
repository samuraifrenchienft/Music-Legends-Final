# audiodb_integration.py
"""
TheAudioDB API Integration for Music Legends
Fallback source for high-quality artist images and album art
"""

import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.txt')

class AudioDBIntegration:
    """TheAudioDB API client for artist images and metadata"""
    
    def __init__(self):
        self.api_key = os.getenv('AUDIODB_API_KEY', '1')  # Default to public v1 key
        self.base_url_v1 = f"https://www.theaudiodb.com/api/v1/json/{self.api_key}"
        # v2 requires Patreon key in path
        self.base_url_v2 = f"https://www.theaudiodb.com/api/v2/json/{self.api_key}"
        
        if self.api_key in ['1', '2']:
            print("ℹ️ Using TheAudioDB public test key (limited features)")
            print("💎 Get Patreon key at: https://www.patreon.com/thedatadb for v2 API access")
        else:
            print("✅ Using TheAudioDB Patreon key (full v2 API access)")
    
    def _make_request(self, endpoint: str, params: Dict = None, use_v2: bool = False) -> Optional[Dict]:
        """Make request to TheAudioDB API"""
        try:
            if use_v2:
                url = f"{self.base_url_v2}/{endpoint}"
            else:
                url = f"{self.base_url_v1}/{endpoint}"
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ AudioDB API error: {e}")
            return None
    
    def search_artist(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """
        Search for artists by name (v1 API)
        
        Args:
            artist_name: Artist name to search
            limit: Max results to return
        
        Returns:
            List of artist data with high-res images, bio, genre, country
        """
        data = self._make_request('search.php', params={'s': artist_name})
        
        if data and 'artists' in data and data['artists']:
            artists = data['artists'][:limit]
            return [self._format_artist(artist) for artist in artists]
        
        return []
    
    def lookup_artist_by_id(self, artist_id: str) -> Optional[Dict]:
        """
        Lookup artist by TheAudioDB ID (v2 API - requires Patreon key)
        
        Args:
            artist_id: TheAudioDB artist ID (e.g., "111239")
        
        Returns:
            Full artist details with all metadata
        
        Note:
            Requires Patreon API key. Falls back to v1 get_artist_by_id() if public key.
        """
        if self.api_key in ['1', '2']:
            # Public key doesn't support v2, use v1 instead
            return self.get_artist_by_id(artist_id)
        
        data = self._make_request(f"lookup/artist/{artist_id}", use_v2=True)
        
        if data and 'artists' in data and data['artists']:
            return self._format_artist(data['artists'][0])
        
        return None
    
    def lookup_artist_by_mbid(self, mbid: str) -> Optional[Dict]:
        """
        Lookup artist by MusicBrainz ID (v2 API - requires Patreon key)
        
        Args:
            mbid: MusicBrainz artist ID (e.g., "cc197bad-dc9c-440d-a5b5-d52ba2e14234")
        
        Returns:
            Full artist details
        
        Note:
            Requires Patreon API key. Returns None if using public key.
        """
        if self.api_key in ['1', '2']:
            print("⚠️ MusicBrainz lookup requires Patreon API key")
            return None
        
        data = self._make_request(f"lookup/artist_mb/{mbid}", use_v2=True)
        
        if data and 'artists' in data and data['artists']:
            return self._format_artist(data['artists'][0])
        
        return None
    
    def get_artist_by_id(self, artist_id: str) -> Optional[Dict]:
        """
        Get artist by TheAudioDB ID (v1 API - legacy)
        Use lookup_artist_by_id() for v2 API instead
        
        Args:
            artist_id: TheAudioDB artist ID
        
        Returns:
            Artist data
        """
        data = self._make_request('artist.php', params={'i': artist_id})
        
        if data and 'artists' in data and data['artists']:
            return self._format_artist(data['artists'][0])
        
        return None
    
    def get_artist_albums(self, artist_id: str) -> List[Dict]:
        """
        Get all albums for an artist
        
        Args:
            artist_id: TheAudioDB artist ID
        
        Returns:
            List of albums with cover art
        """
        data = self._make_request('album.php', params={'i': artist_id})
        
        if data and 'album' in data and data['album']:
            return [self._format_album(album) for album in data['album']]
        
        return []
    
    def search_album(self, album_name: str) -> Optional[Dict]:
        """
        Search for album by name
        
        Returns:
            Album data with cover art
        """
        data = self._make_request('searchalbum.php', params={'s': album_name})
        
        if data and 'album' in data and data['album']:
            return self._format_album(data['album'][0])
        
        return None
    
    def get_music_videos(self, artist_id: str) -> List[Dict]:
        """
        Get music videos for an artist
        
        Args:
            artist_id: TheAudioDB artist ID
        
        Returns:
            List of music videos with thumbnails
        """
        data = self._make_request('mvid.php', params={'i': artist_id})
        
        if data and 'mvids' in data and data['mvids']:
            return [self._format_video(video) for video in data['mvids']]
        
        return []
    
    def _format_artist(self, artist: Dict) -> Dict:
        """Format artist data"""
        return {
            'id': artist.get('idArtist', ''),
            'name': artist.get('strArtist', ''),
            'genre': artist.get('strGenre', ''),
            'style': artist.get('strStyle', ''),
            'country': artist.get('strCountry', ''),
            'formed_year': artist.get('intFormedYear', ''),
            'bio_en': artist.get('strBiographyEN', ''),
            'bio_short': artist.get('strBiographyEN', '')[:500] if artist.get('strBiographyEN') else '',
            
            # High-quality images
            'image_thumb': artist.get('strArtistThumb', ''),
            'image_logo': artist.get('strArtistLogo', ''),
            'image_banner': artist.get('strArtistBanner', ''),
            'image_fanart': artist.get('strArtistFanart', ''),
            'image_fanart2': artist.get('strArtistFanart2', ''),
            'image_fanart3': artist.get('strArtistFanart3', ''),
            
            # Social links
            'website': artist.get('strWebsite', ''),
            'facebook': artist.get('strFacebook', ''),
            'twitter': artist.get('strTwitter', ''),
            'lastfm': artist.get('strLastFMChart', ''),
            
            # IDs
            'mbid': artist.get('strMusicBrainzID', ''),
            'locked': artist.get('strLocked', '') == 'unlocked'
        }
    
    def _format_album(self, album: Dict) -> Dict:
        """Format album data"""
        return {
            'id': album.get('idAlbum', ''),
            'name': album.get('strAlbum', ''),
            'artist': album.get('strArtist', ''),
            'year': album.get('intYearReleased', ''),
            'genre': album.get('strGenre', ''),
            'style': album.get('strStyle', ''),
            'description': album.get('strDescriptionEN', ''),
            
            # Album art
            'cover_thumb': album.get('strAlbumThumb', ''),
            'cover_large': album.get('strAlbumThumbHQ', ''),
            'cover_back': album.get('strAlbumThumbBack', ''),
            'cd_art': album.get('strAlbumCDart', ''),
            'spine': album.get('strAlbumSpine', ''),
            
            # Ratings
            'score': album.get('intScore', 0),
            'score_votes': album.get('intScoreVotes', 0),
            
            # IDs
            'mbid': album.get('strMusicBrainzID', ''),
            'mbid_artist': album.get('strMusicBrainzArtistID', '')
        }
    
    def _format_video(self, video: Dict) -> Dict:
        """Format music video data"""
        return {
            'id': video.get('idTrack', ''),
            'name': video.get('strTrack', ''),
            'artist': video.get('strArtist', ''),
            'album': video.get('strAlbum', ''),
            'description': video.get('strDescriptionEN', ''),
            
            # Video links
            'youtube_url': f"https://www.youtube.com/watch?v={video.get('strMusicVid', '')}" if video.get('strMusicVid') else '',
            'youtube_id': video.get('strMusicVid', ''),
            
            # Thumbnails
            'thumb': video.get('strTrackThumb', ''),
            
            # IDs
            'mbid': video.get('strMusicBrainzID', '')
        }
    
    def get_best_image(self, artist_data: Dict) -> str:
        """
        Get the best available image for an artist
        Priority: Thumb > Fanart > Logo > Banner
        
        Args:
            artist_data: Formatted artist data
        
        Returns:
            URL of best image
        """
        for key in ['image_thumb', 'image_fanart', 'image_logo', 'image_banner']:
            if artist_data.get(key):
                return artist_data[key]
        return ''


# Global instance
audiodb_integration = AudioDBIntegration()


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    print("🎨 TheAudioDB Integration Test\n")
    
    # Test artist search (v1)
    print("1. Searching for 'Drake' (v1 API)...")
    artists = audiodb_integration.search_artist("Drake", limit=3)
    if artists:
        for i, artist in enumerate(artists, 1):
            print(f"   {i}. {artist['name']} (ID: {artist['id']})")
            print(f"      Genre: {artist['genre']} | Country: {artist['country']}")
    
    print()
    
    # Test artist lookup by ID (v1 fallback for public key)
    if artists:
        artist_id = artists[0]['id']
        print(f"2. Looking up artist by ID '{artist_id}' (v1 API)...")
        artist_detail = audiodb_integration.lookup_artist_by_id(artist_id)
        if artist_detail:
            print(f"   Name: {artist_detail['name']}")
            print(f"   Genre: {artist_detail['genre']}")
            print(f"   Formed: {artist_detail['formed_year']}")
            print(f"   Thumb: {artist_detail['image_thumb'][:50] if artist_detail['image_thumb'] else 'N/A'}...")
            print(f"   Logo: {artist_detail['image_logo'][:50] if artist_detail['image_logo'] else 'N/A'}...")
            print(f"   Best Image: {audiodb_integration.get_best_image(artist_detail)[:50]}...")
        else:
            print("   Not found")
    
    print()
    
    # Test artist lookup by MusicBrainz ID (v2 - requires Patreon)
    print("3. Looking up artist by MBID (requires Patreon key)...")
    # Drake's MusicBrainz ID
    mbid = "cc197bad-dc9c-440d-a5b5-d52ba2e14234"
    artist_mb = audiodb_integration.lookup_artist_by_mbid(mbid)
    if artist_mb:
        print(f"   Found: {artist_mb['name']}")
        print(f"   MBID: {artist_mb['mbid']}")
    
    print()
    
    # Test album search
    print("4. Searching for album 'Scorpion'...")
    album = audiodb_integration.search_album("Scorpion")
    if album:
        print(f"   Album: {album['name']}")
        print(f"   Artist: {album['artist']}")
        print(f"   Year: {album['year']}")
        print(f"   Cover: {album['cover_thumb'][:50] if album['cover_thumb'] else 'N/A'}...")
    
    print()
    
    # Test music videos
    if artists and artists[0]['id']:
        print(f"5. Getting music videos for artist ID {artists[0]['id']}...")
        videos = audiodb_integration.get_music_videos(artists[0]['id'])
        if videos:
            for i, video in enumerate(videos[:3], 1):
                print(f"   {i}. {video['name']}")
                print(f"      YouTube: {video['youtube_url'][:50] if video['youtube_url'] else 'N/A'}...")
        else:
            print("   No videos found")
    
    print("\n✅ Test complete!")
    print("\n📝 Note: Public key (1 or 2) uses v1 API with basic features")
    print("   Patreon key ($3/mo) unlocks v2 API with:")
    print("   • Better lookup by ID")
    print("   • MusicBrainz ID support")
    print("   • Higher rate limits")
    print("   • More metadata fields")
