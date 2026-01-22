"""
Hero Slot System (Top-Tier Feature)

Premium packs must feel premium.
Hero Slot Rules:
- Slot 1 uses boosted artist selection
- Pulls higher-popularity artists first
- Guarantees visual impact, not just tier

Hero ≠ Legendary
Hero = recognizable
"""

from typing import List, Dict, Optional, Tuple
import random
from schemas.card_canonical import CardTier, ArtistSource
from schemas.pack_definition import PackDefinition

class Artist:
    """Artist model with popularity metrics"""
    
    def __init__(
        self,
        artist_id: str,
        name: str,
        primary_genre: str,
        image_url: str,
        source: ArtistSource,
        popularity_score: float = 50.0,
        visual_impact_score: float = 50.0,
        genre_tags: List[str] = None
    ):
        self.artist_id = artist_id
        self.name = name
        self.primary_genre = primary_genre
        self.image_url = image_url
        self.source = source
        self.popularity_score = popularity_score  # 0-100, based on followers/subs
        self.visual_impact_score = visual_impact_score  # 0-100, based on art quality
        self.genre_tags = genre_tags or []
        
        # Hero eligibility score
        self.hero_score = self._calculate_hero_score()
    
    def _calculate_hero_score(self) -> float:
        """Calculate hero slot eligibility score"""
        # Weighted combination of popularity and visual impact
        popularity_weight = 0.6
        visual_weight = 0.4
        
        return (self.popularity_score * popularity_weight + 
                self.visual_impact_score * visual_weight)
    
    def is_hero_eligible(self, min_score: float = 70.0) -> bool:
        """Check if artist is eligible for hero slot"""
        return self.hero_score >= min_score
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "artist_id": self.artist_id,
            "name": self.name,
            "primary_genre": self.primary_genre,
            "image_url": self.image_url,
            "source": self.source.value,
            "popularity_score": self.popularity_score,
            "visual_impact_score": self.visual_impact_score,
            "hero_score": self.hero_score,
            "genre_tags": self.genre_tags
        }

class HeroSlotSystem:
    """
    Manages hero slot logic for premium packs.
    Ensures visual impact and recognizability.
    """
    
    def __init__(self):
        self.artists: Dict[str, Artist] = {}
        self.load_default_artists()
    
    def load_default_artists(self):
        """Load default artist database"""
        # Sample artists with varying popularity and visual impact
        default_artists = [
            # High-tier hero candidates (top tier)
            Artist(
                artist_id="artist_001",
                name="Luna Echo",
                primary_genre="Electronic",
                image_url="https://example.com/luna.jpg",
                source=ArtistSource.SPOTIFY,
                popularity_score=95.0,
                visual_impact_score=92.0,
                genre_tags=["synthwave", "ambient", "electronic"]
            ),
            Artist(
                artist_id="artist_002", 
                name="Neon Dreams",
                primary_genre="Pop",
                image_url="https://example.com/neon.jpg",
                source=ArtistSource.YOUTUBE,
                popularity_score=88.0,
                visual_impact_score=95.0,
                genre_tags=["pop", "synthpop", "electronic"]
            ),
            Artist(
                artist_id="artist_003",
                name="Crystal Waves",
                primary_genre="Indie",
                image_url="https://example.com/crystal.jpg",
                source=ArtistSource.SPOTIFY,
                popularity_score=82.0,
                visual_impact_score=89.0,
                genre_tags=["indie", "alternative", "dream-pop"]
            ),
            
            # Mid-tier artists
            Artist(
                artist_id="artist_004",
                name="Urban Pulse",
                primary_genre="Hip-Hop",
                image_url="https://example.com/urban.jpg",
                source=ArtistSource.YOUTUBE,
                popularity_score=75.0,
                visual_impact_score=78.0,
                genre_tags=["hip-hop", "trap", "urban"]
            ),
            Artist(
                artist_id="artist_005",
                name="Folk Revival",
                primary_genre="Folk",
                image_url="https://example.com/folk.jpg",
                source=ArtistSource.SPOTIFY,
                popularity_score=68.0,
                visual_impact_score=72.0,
                genre_tags=["folk", "acoustic", "indie-folk"]
            ),
            
            # Standard artists
            Artist(
                artist_id="artist_006",
                name="Jazz Fusion",
                primary_genre="Jazz",
                image_url="https://example.com/jazz.jpg",
                source=ArtistSource.SPOTIFY,
                popularity_score=55.0,
                visual_impact_score=60.0,
                genre_tags=["jazz", "fusion", "instrumental"]
            ),
            Artist(
                artist_id="artist_007",
                name="Classical Modern",
                primary_genre="Classical",
                image_url="https://example.com/classical.jpg",
                source=ArtistSource.YOUTUBE,
                popularity_score=45.0,
                visual_impact_score=52.0,
                genre_tags=["classical", "modern", "orchestral"]
            ),
            
            # Community tier
            Artist(
                artist_id="artist_008",
                name="Bedroom Producer",
                primary_genre="Lo-Fi",
                image_url="https://example.com/bedroom.jpg",
                source=ArtistSource.YOUTUBE,
                popularity_score=25.0,
                visual_impact_score=35.0,
                genre_tags=["lo-fi", "chill", "bedroom-pop"]
            ),
            Artist(
                artist_id="artist_009",
                name="Garage Band",
                primary_genre="Rock",
                image_url="https://example.com/garage.jpg",
                source=ArtistSource.SPOTIFY,
                popularity_score=15.0,
                visual_impact_score=20.0,
                genre_tags=["rock", "garage", "indie-rock"]
            ),
            Artist(
                artist_id="artist_010",
                name="SoundCloud Rapper",
                primary_genre="Hip-Hop",
                image_url="https://example.com/soundcloud.jpg",
                source=ArtistSource.YOUTUBE,
                popularity_score=8.0,
                visual_impact_score=12.0,
                genre_tags=["hip-hop", "underground", "soundcloud"]
            )
        ]
        
        for artist in default_artists:
            self.artists[artist.artist_id] = artist
    
    def add_artist(self, artist: Artist):
        """Add artist to database"""
        self.artists[artist.artist_id] = artist
    
    def get_hero_candidates(self, min_tier: CardTier = CardTier.PLATINUM) -> List[Artist]:
        """Get artists eligible for hero slot"""
        min_scores = {
            CardTier.PLATINUM: 70.0,
            CardTier.LEGENDARY: 85.0
        }
        
        min_score = min_scores.get(min_tier, 70.0)
        return [artist for artist in self.artists.values() 
                if artist.is_hero_eligible(min_score)]
    
    def select_hero_artist(self, min_tier: CardTier = CardTier.PLATINUM) -> Artist:
        """
        Select hero artist with boosted probability for higher scores.
        Premium packs must feel premium.
        """
        candidates = self.get_hero_candidates(min_tier)
        
        if not candidates:
            # Fallback to highest scoring artist
            candidates = sorted(self.artists.values(), 
                              key=lambda x: x.hero_score, reverse=True)[:3]
        
        # Weighted selection based on hero score
        # Higher hero scores get higher probability
        weights = [artist.hero_score for artist in candidates]
        total_weight = sum(weights)
        
        # Normalize weights
        normalized_weights = [w / total_weight for w in weights]
        
        # Select using weighted probability
        selected = random.choices(candidates, weights=normalized_weights)[0]
        
        return selected
    
    def select_standard_artist(self, tier: CardTier) -> Artist:
        """Select artist for non-hero slots"""
        # Different selection pools for different tiers
        tier_filters = {
            CardTier.COMMUNITY: lambda a: a.hero_score < 40,
            CardTier.GOLD: lambda a: 40 <= a.hero_score < 60,
            CardTier.PLATINUM: lambda a: 60 <= a.hero_score < 80,
            CardTier.LEGENDARY: lambda a: a.hero_score >= 80
        }
        
        filter_func = tier_filters.get(tier, tier_filters[CardTier.GOLD])
        candidates = [artist for artist in self.artists.values() if filter_func(artist)]
        
        if not candidates:
            # Fallback to any artist
            candidates = list(self.artists.values())
        
        return random.choice(candidates)
    
    def generate_pack_artists(self, pack_def: PackDefinition) -> List[Artist]:
        """
        Generate artists for a pack with hero slot logic.
        Slot 1 uses boosted selection if pack has hero slot.
        """
        artists = []
        
        for slot in range(pack_def.cards_per_pack):
            if slot == 0 and pack_def.has_hero_slot():
                # Hero slot - boosted selection
                min_tier = CardTier(pack_def.get_min_rarity())
                artist = self.select_hero_artist(min_tier)
            else:
                # Standard slot
                artist = self.select_standard_artist(CardTier.GOLD)  # Default to gold tier
            
            artists.append(artist)
        
        return artists
    
    def get_artist_stats(self) -> Dict:
        """Get statistics about artist distribution"""
        total_artists = len(self.artists)
        hero_eligible = len([a for a in self.artists.values() if a.is_hero_eligible()])
        
        tier_distribution = {
            "community": len([a for a in self.artists.values() if a.hero_score < 40]),
            "gold": len([a for a in self.artists.values() if 40 <= a.hero_score < 60]),
            "platinum": len([a for a in self.artists.values() if 60 <= a.hero_score < 80]),
            "legendary": len([a for a in self.artists.values() if a.hero_score >= 80])
        }
        
        return {
            "total_artists": total_artists,
            "hero_eligible": hero_eligible,
            "hero_eligible_percentage": (hero_eligible / total_artists * 100) if total_artists > 0 else 0,
            "tier_distribution": tier_distribution,
            "average_hero_score": sum(a.hero_score for a in self.artists.values()) / total_artists if total_artists > 0 else 0
        }
    
    def validate_hero_system(self) -> List[str]:
        """Validate hero slot system and return issues"""
        issues = []
        
        if len(self.artists) < 10:
            issues.append("Too few artists in database")
        
        hero_candidates = self.get_hero_candidates()
        if len(hero_candidates) < 3:
            issues.append("Too few hero-eligible artists")
        
        # Check genre diversity
        genres = set(artist.primary_genre for artist in self.artists.values())
        if len(genres) < 3:
            issues.append("Insufficient genre diversity")
        
        return issues

# Global hero slot system instance
hero_system = HeroSlotSystem()

def get_hero_artist(min_tier: CardTier = CardTier.PLATINUM) -> Artist:
    """Get hero artist for premium packs"""
    return hero_system.select_hero_artist(min_tier)

def get_standard_artist(tier: CardTier) -> Artist:
    """Get standard artist for regular slots"""
    return hero_system.select_standard_artist(tier)

def generate_pack_artists(pack_def: PackDefinition) -> List[Artist]:
    """Generate artists for a pack"""
    return hero_system.generate_pack_artists(pack_def)
