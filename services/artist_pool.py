# services/artist_pool.py
"""
Artist Pool Service
Pull from artists already imported via YouTube
"""

import random
from typing import Optional, List
from models.artist import Artist

def get_random_artist(genre: Optional[str] = None) -> Optional[Artist]:
    """
    Pull from artists already imported via YouTube
    
    Args:
        genre: Filter by genre (optional)
        
    Returns:
        Random Artist or None
    """
    try:
        if genre:
            artists = Artist.where(genre=genre)
        else:
            artists = Artist.all()

        if not artists:
            return None

        return random.choice(artists)
        
    except Exception as e:
        print(f"❌ Error getting random artist: {e}")
        return None


def get_artists_by_genre(genre: str, limit: Optional[int] = None) -> List[Artist]:
    """
    Get artists filtered by genre
    
    Args:
        genre: Music genre
        limit: Maximum number of artists
        
    Returns:
        List of artists
    """
    try:
        artists = Artist.where(genre=genre)
        
        if limit:
            artists = artists[:limit]
            
        return artists
        
    except Exception as e:
        print(f"❌ Error getting artists by genre: {e}")
        return []


def get_artists_by_tier(tier: str, limit: Optional[int] = None) -> List[Artist]:
    """
    Get artists filtered by tier
    
    Args:
        tier: Artist tier
        limit: Maximum number of artists
        
    Returns:
        List of artists
    """
    try:
        artists = Artist.where(tier=tier)
        
        if limit:
            artists = artists[:limit]
            
        return artists
        
    except Exception as e:
        print(f"❌ Error getting artists by tier: {e}")
        return []


def get_pool_stats() -> dict:
    """
    Get basic pool statistics
    
    Returns:
        Pool statistics
    """
    try:
        all_artists = Artist.all()
        
        if not all_artists:
            return {
                "total_artists": 0,
                "by_tier": {},
                "by_genre": {}
            }
        
        # Count by tier
        tier_counts = {}
        genre_counts = {}
        
        for artist in all_artists:
            tier = getattr(artist, 'tier', 'unknown')
            genre = getattr(artist, 'genre', 'unknown')
            
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        return {
            "total_artists": len(all_artists),
            "by_tier": tier_counts,
            "by_genre": genre_counts
        }
        
    except Exception as e:
        print(f"❌ Error getting pool stats: {e}")
        return {"total_artists": 0, "by_tier": {}, "by_genre": {}}
