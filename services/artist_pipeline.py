# services/artist_pipeline.py
"""
Artist Pipeline Service
Import YouTube artists and create game cards
"""

import asyncio
from typing import Optional, Dict, List, Any
import uuid
from datetime import datetime

from services.youtube_client import YouTubeClient
from services.tier_mapper import tier_from_youtube, genre_from_topics, analyze_channel_for_game
from services.game_integration import GameIntegration
from models.artist import Artist
from models.card import Card

class ArtistPipeline:
    """Pipeline for importing YouTube artists and creating game cards"""
    
    def __init__(self):
        self.youtube_client = YouTubeClient()
        self.game_integration = GameIntegration()
        
    async def import_artist_to_card(self, name: str, card_type: str = "standard") -> Optional[Card]:
        """
        Import YouTube artist and create first card
        
        Args:
            name: Artist/channel name to search
            card_type: Type of card to create
            
        Returns:
            Created Card object or None if failed
        """
        try:
            # Search for channel
            base = await self.youtube_client.search_channel(name)
            if not base:
                print(f"❌ No channel found for: {name}")
                return None

            # Get channel stats
            stats = await self.youtube_client.channel_stats(base["channel_id"])
            if not stats:
                print(f"❌ No stats found for channel: {base['channel_id']}")
                return None

            # Determine tier and genre
            tier = tier_from_youtube(stats["subs"], stats["views"], stats.get("videos", 0))
            genre = genre_from_topics(stats.get("topics", []))
            
            # Enhanced analysis
            analysis = analyze_channel_for_game(
                subs=stats["subs"],
                views=stats["views"],
                videos=stats.get("videos", 0),
                topics=stats.get("topics", []),
                description=base.get("description", ""),
                channel_name=base.get("name", "")
            )

            # ---- Create Artist ----
            artist = await self._create_artist(base, stats, analysis)
            if not artist:
                print(f"❌ Failed to create artist: {base['name']}")
                return None

            # ---- Create First Card ----
            card = await self._create_card(artist, tier, card_type, analysis)
            if not card:
                print(f"❌ Failed to create card for artist: {artist.name}")
                return None

            print(f"✅ Successfully imported {artist.name} -> {card.serial}")
            return card

        except Exception as e:
            print(f"❌ Error importing artist {name}: {e}")
            return None
    
    async def _create_artist(self, channel_data: Dict[str, Any], 
                           stats: Dict[str, Any], 
                           analysis: Dict[str, Any]) -> Optional[Artist]:
        """Create artist record in database"""
        try:
            artist_data = {
                "name": channel_data["name"],
                "genre": analysis["genre"],
                "image_url": channel_data.get("image", ""),
                "external_ref": channel_data["channel_id"],
                "source": "youtube",
                "popularity": stats.get("subs", 0),
                "tier": analysis["tier"],
                "score": analysis["score"],
                "power_level": analysis["game_data"]["power_level"],
                "created_at": datetime.utcnow(),
                "metadata": {
                    "subscribers": stats.get("subs", 0),
                    "total_views": stats.get("views", 0),
                    "video_count": stats.get("videos", 0),
                    "topics": stats.get("topics", []),
                    "description": channel_data.get("description", ""),
                    "published_at": channel_data.get("published_at"),
                    "country": stats.get("country"),
                    "custom_url": stats.get("custom_url")
                }
            }
            
            artist = Artist.create(**artist_data)
            return artist
            
        except Exception as e:
            print(f"❌ Error creating artist: {e}")
            return None
    
    async def _create_card(self, artist: Artist, tier: str, 
                         card_type: str, analysis: Dict[str, Any]) -> Optional[Card]:
        """Create card record in database"""
        try:
            # Generate card data
            card_data = {
                "artist_id": artist.id,
                "tier": tier,
                "serial": await Card.next_serial(),
                "print_number": 1,
                "source": "youtube",
                "card_type": card_type,
                "power_level": analysis["game_data"]["power_level"],
                "stats": self._calculate_card_stats(analysis),
                "abilities": self._generate_card_abilities(analysis, card_type),
                "rarity_score": self._calculate_rarity_score(analysis),
                "created_at": datetime.utcnow(),
                "image_url": artist.image_url,
                "metadata": {
                    "genre": analysis["genre"],
                    "score": analysis["score"],
                    "requirements": analysis["requirements"]
                }
            }
            
            card = Card.create(**card_data)
            return card
            
        except Exception as e:
            print(f"❌ Error creating card: {e}")
            return None
    
    def _calculate_card_stats(self, analysis: Dict[str, Any]) -> Dict[str, int]:
        """Calculate card statistics from analysis"""
        metrics = analysis["metrics"]
        tier = analysis["tier"]
        
        # Base stats from metrics
        attack = min(metrics["subscribers"] // 10_000, 100)
        defense = min(metrics["total_views"] // 50_000_000, 100)
        speed = min(metrics["video_count"] // 100, 100)
        
        # Tier bonuses
        tier_bonuses = {
            "legendary": {"attack": 20, "defense": 20, "speed": 20},
            "platinum": {"attack": 15, "defense": 15, "speed": 15},
            "gold": {"attack": 10, "defense": 10, "speed": 10},
            "silver": {"attack": 5, "defense": 5, "speed": 5},
            "bronze": {"attack": 3, "defense": 3, "speed": 3},
            "community": {"attack": 1, "defense": 1, "speed": 1}
        }
        
        bonus = tier_bonuses.get(tier, {"attack": 0, "defense": 0, "speed": 0})
        
        return {
            "attack": min(attack + bonus["attack"], 100),
            "defense": min(defense + bonus["defense"], 100),
            "speed": min(speed + bonus["speed"], 100),
            "health": 100
        }
    
    def _generate_card_abilities(self, analysis: Dict[str, Any], card_type: str) -> List[Dict[str, str]]:
        """Generate card abilities"""
        tier = analysis["tier"]
        genre = analysis["genre"]
        
        abilities = []
        
        # Tier abilities
        tier_abilities = {
            "legendary": [
                {"name": "Global Fame", "description": "Boost all allies by 10"},
                {"name": "Viral Hit", "description": "Double attack for 3 turns"}
            ],
            "platinum": [
                {"name": "Platinum Album", "description": "Heal 20 HP"},
                {"name": "World Tour", "description": "Attack all enemies"}
            ],
            "gold": [
                {"name": "Gold Record", "description": "Boost attack by 5"},
                {"name": "Radio Play", "description": "Reduce enemy defense"}
            ],
            "silver": [
                {"name": "Silver Screen", "description": "Increase speed"}
            ],
            "bronze": [
                {"name": "Breakout Hit", "description": "Small attack boost"}
            ],
            "community": [
                {"name": "Local Fame", "description": "Minor stat boost"}
            ]
        }
        
        # Add tier abilities
        abilities.extend(tier_abilities.get(tier, []))
        
        # Genre abilities
        genre_abilities = {
            "Hip-Hop": {"name": "Freestyle", "description": "Unpredictable attack"},
            "Rock": {"name": "Power Chord", "description": "Heavy damage"},
            "Pop": {"name": "Chart Topper", "description": "Popular appeal"},
            "EDM": {"name": "Drop the Beat", "description": "Area effect"},
            "Country": {"name": "Storyteller", "description": "Healing ability"}
        }
        
        genre_ability = genre_abilities.get(genre)
        if genre_ability:
            abilities.append(genre_ability)
        
        return abilities
    
    def _calculate_rarity_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate rarity score for pack generation"""
        tier_scores = {
            "legendary": 100,
            "platinum": 80,
            "gold": 60,
            "silver": 40,
            "bronze": 20,
            "community": 10
        }
        
        base_score = tier_scores.get(analysis["tier"], 10)
        
        # Add score-based bonus
        score_bonus = min(analysis["score"] // 1_000_000, 20)
        
        return base_score + score_bonus
    
    async def import_multiple_artists(self, names: List[str]) -> List[Card]:
        """
        Import multiple artists in batch
        
        Args:
            names: List of artist names to import
            
        Returns:
            List of created cards
        """
        cards = []
        
        for name in names:
            card = await self.import_artist_to_card(name)
            if card:
                cards.append(card)
        
        print(f"✅ Imported {len(cards)} out of {len(names)} artists")
        return cards
    
    async def import_trending_artists(self, region: str = "US", limit: int = 10) -> List[Card]:
        """
        Import artists from trending music
        
        Args:
            region: Region code
            limit: Maximum artists to import
            
        Returns:
            List of created cards
        """
        # Get trending music
        trending_videos = await self.youtube_client.get_trending_music(region, limit)
        
        cards = []
        processed_channels = set()
        
        for video in trending_videos:
            channel_name = video["channel"]
            
            # Avoid duplicates
            if channel_name in processed_channels:
                continue
            
            processed_channels.add(channel_name)
            
            # Import as trending card
            card = await self.import_artist_to_card(channel_name, "trending")
            if card:
                cards.append(card)
        
        print(f"✅ Imported {len(cards)} trending artists from {region}")
        return cards
    
    async def import_genre_artists(self, genre: str, limit: int = 5) -> List[Card]:
        """
        Import artists from specific genre
        
        Args:
            genre: Music genre
            limit: Maximum artists to import
            
        Returns:
            List of created cards
        """
        # Search for genre videos
        videos = await self.youtube_client.search_videos(f"{genre} music official", limit * 2)
        
        cards = []
        processed_channels = set()
        
        for video in videos:
            channel_name = video["channel"]
            
            # Avoid duplicates
            if channel_name in processed_channels:
                continue
            
            processed_channels.add(channel_name)
            
            # Import artist
            card = await self.import_artist_to_card(channel_name, "genre_pack")
            if card:
                cards.append(card)
            
            # Stop when we have enough
            if len(cards) >= limit:
                break
        
        print(f"✅ Imported {len(cards)} {genre} artists")
        return cards
    
    async def update_artist_stats(self, artist_id: str) -> bool:
        """
        Update artist statistics from YouTube
        
        Args:
            artist_id: Artist ID in database
            
        Returns:
            True if updated successfully
        """
        try:
            # Get artist from database
            artist = Artist.get_by_id(artist_id)
            if not artist or artist.source != "youtube":
                return False
            
            # Get fresh stats from YouTube
            stats = await self.youtube_client.channel_stats(artist.external_ref)
            if not stats:
                return False
            
            # Update artist data
            artist.popularity = stats.get("subs", 0)
            artist.metadata.update({
                "subscribers": stats.get("subs", 0),
                "total_views": stats.get("views", 0),
                "video_count": stats.get("videos", 0),
                "updated_at": datetime.utcnow()
            })
            
            # Recalculate tier and power
            new_tier = tier_from_youtube(
                stats["subs"], 
                stats["views"], 
                stats.get("videos", 0)
            )
            
            if new_tier != artist.tier:
                artist.tier = new_tier
                print(f"📈 Artist {artist.name} tier updated to {new_tier}")
            
            artist.save()
            return True
            
        except Exception as e:
            print(f"❌ Error updating artist stats: {e}")
            return False


# Global pipeline instance
artist_pipeline = ArtistPipeline()


# Synchronous wrapper for backward compatibility
def import_artist_to_card(name: str) -> Optional[Card]:
    """Synchronous wrapper for import_artist_to_card"""
    return asyncio.run(artist_pipeline.import_artist_to_card(name))


# Example usage
async def example_usage():
    """Example of artist pipeline usage"""
    
    # Import single artist
    card = await artist_pipeline.import_artist_to_card("Taylor Swift")
    if card:
        print(f"Created card: {card.serial} - {card.artist.name}")
    
    # Import multiple artists
    artists = ["Ed Sheeran", "Drake", "Billie Eilish"]
    cards = await artist_pipeline.import_multiple_artists(artists)
    print(f"Imported {len(cards)} artists")
    
    # Import trending artists
    trending = await artist_pipeline.import_trending_artists("US", 5)
    print(f"Imported {len(trending)} trending artists")
    
    # Import genre artists
    rock_artists = await artist_pipeline.import_genre_artists("Rock", 3)
    print(f"Imported {len(rock_artists)} rock artists")


if __name__ == "__main__":
    asyncio.run(example_usage())
