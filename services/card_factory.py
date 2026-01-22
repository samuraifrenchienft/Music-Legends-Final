# services/card_factory.py
"""
Card Creation From Artist
Create cards from artists with serial numbers
"""

from typing import Optional
from models.card import Card
from models.artist import Artist

def create_from_artist(artist: Artist, tier: Optional[str] = None, source: str = "pool") -> Optional[Card]:
    """
    Create a card from an artist
    
    Args:
        artist: Artist object
        tier: Card tier (optional, uses artist's tier if not specified)
        source: Card source (pool, pack, youtube, etc.)
        
    Returns:
        Created Card or None
    """
    try:
        # Use artist's tier if not specified
        if not tier:
            tier = artist.tier
        
        # Get next serial number for this artist/tier combination
        serial = Card.count(artist_id=artist.id, tier=tier) + 1
        
        # Create card
        card = Card.create(
            artist_id=artist.id,
            genre=artist.genre,
            tier=tier,
            serial=f"ML-SF-{serial:04d}",
            print_number=serial,
            season=1,
            source=source
        )
        
        return card
        
    except Exception as e:
        print(f"❌ Error creating card from artist: {e}")
        return None


def create_special_card(artist: Artist, card_type: str = "special") -> Optional[Card]:
    """
    Create a special variant card
    
    Args:
        artist: Artist object
        card_type: Type of special card
        
    Returns:
        Created Card or None
    """
    try:
        # Get next serial number
        serial = Card.count(artist_id=artist.id, tier=artist.tier) + 1
        
        # Create special card with unique serial
        card = Card.create(
            artist_id=artist.id,
            genre=artist.genre,
            tier=artist.tier,
            serial=f"ML-{card_type.upper()}-{serial:04d}",
            print_number=serial,
            season=1,
            source="special",
            card_type=card_type
        )
        
        return card
        
    except Exception as e:
        print(f"❌ Error creating special card: {e}")
        return None


def create_pack_cards(pack_size: int = 5, source: str = "pack") -> list:
    """
    Create a pack of random cards
    
    Args:
        pack_size: Number of cards in pack
        source: Pack source
        
    Returns:
        List of created cards
    """
    from services.artist_pool import get_random_artist
    
    cards = []
    
    for _ in range(pack_size):
        # Get random artist
        artist = get_random_artist()
        
        if artist:
            # Create card from artist
            card = create_from_artist(artist, source=source)
            
            if card:
                cards.append(card)
    
    return cards


def create_genre_pack(genre: str, pack_size: int = 3) -> list:
    """
    Create a pack of cards from specific genre
    
    Args:
        genre: Music genre
        pack_size: Number of cards
        
    Returns:
        List of created cards
    """
    from services.artist_pool import get_random_artist
    
    cards = []
    
    for _ in range(pack_size):
        # Get random artist from genre
        artist = get_random_artist(genre=genre)
        
        if artist:
            # Create card from artist
            card = create_from_artist(artist, source=f"{genre}_pack")
            
            if card:
                cards.append(card)
    
    return cards


def create_tier_pack(tier: str, pack_size: int = 5) -> list:
    """
    Create a pack of cards from specific tier
    
    Args:
        tier: Card tier
        pack_size: Number of cards
        
    Returns:
        List of created cards
    """
    from services.artist_pool import get_artists_by_tier
    
    cards = []
    
    # Get artists from tier
    artists = get_artists_by_tier(tier, limit=pack_size)
    
    for artist in artists:
        # Create card from artist
        card = create_from_artist(artist, tier=tier, source=f"{tier}_pack")
        
        if card:
            cards.append(card)
    
    return cards
