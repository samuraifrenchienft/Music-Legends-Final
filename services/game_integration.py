# services/game_integration.py
"""
Integration between YouTube data and Music Legends game system
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import uuid

from services.youtube_client import youtube_client
from services.tier_mapper import analyze_channel_for_game, get_tier_emoji, get_tier_color

class GameIntegration:
    """Bridge between YouTube data and game mechanics"""
    
    def __init__(self):
        self.youtube_client = youtube_client
        
    async def create_artist_from_youtube(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """
        Create game artist from YouTube channel
        
        Args:
            channel_name: YouTube channel name to search
            
        Returns:
            Artist data for game integration
        """
        try:
            # Search for channel
            channel = await self.youtube_client.search_channel(channel_name)
            if not channel:
                return None
            
            # Get channel stats
            stats = await self.youtube_client.channel_stats(channel['channel_id'])
            if not stats:
                stats = {"subs": 0, "views": 0, "videos": 0, "topics": []}
            
            # Analyze for game
            analysis = analyze_channel_for_game(
                subs=stats.get('subs', 0),
                views=stats.get('views', 0),
                videos=stats.get('videos', 0),
                topics=stats.get('topics', []),
                description=channel.get('description', ''),
                channel_name=channel.get('name', '')
            )
            
            # Create artist data
            artist = {
                "id": str(uuid.uuid4()),
                "name": channel['name'],
                "youtube_channel_id": channel['channel_id'],
                "tier": analysis['tier'],
                "genre": analysis['genre'],
                "score": analysis['score'],
                "image": channel.get('image', ''),
                "description": channel.get('description', ''),
                "created_at": datetime.utcnow().isoformat(),
                "stats": {
                    "subscribers": stats.get('subs', 0),
                    "total_views": stats.get('views', 0),
                    "video_count": stats.get('videos', 0),
                    "avg_views_per_video": analysis['metrics']['avg_views_per_video']
                },
                "game_data": {
                    "tier_emoji": analysis['tier_emoji'],
                    "tier_color": analysis['tier_color'],
                    "requirements": analysis['requirements'],
                    "power_level": self._calculate_power_level(analysis['score'], analysis['tier'])
                }
            }
            
            return artist
            
        except Exception as e:
            print(f"Error creating artist from YouTube: {e}")
            return None
    
    def _calculate_power_level(self, score: int, tier: str) -> int:
        """
        Calculate game power level from YouTube metrics
        
        Args:
            score: Popularity score
            tier: Game tier
            
        Returns:
            Power level (1-100)
        """
        # Base power from tier
        tier_power = {
            "legendary": 90,
            "platinum": 80,
            "gold": 70,
            "silver": 60,
            "bronze": 50,
            "community": 40
        }
        
        base_power = tier_power.get(tier, 40)
        
        # Adjust based on score within tier
        score_bonus = min(score // 100_000, 10)  # Max 10 bonus points
        
        return min(base_power + score_bonus, 100)
    
    async def create_card_from_artist(self, artist: Dict[str, Any], card_type: str = "standard") -> Dict[str, Any]:
        """
        Create game card from artist data
        
        Args:
            artist: Artist data from create_artist_from_youtube
            card_type: Type of card (standard, special, legendary)
            
        Returns:
            Card data for game
        """
        # Generate card serial
        serial = f"{artist['tier'].upper()[:1]}{artist['genre'].upper()[:2]}{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate card stats based on artist metrics
        base_stats = self._calculate_card_stats(artist)
        
        card = {
            "id": str(uuid.uuid4()),
            "serial": serial,
            "artist_id": artist['id'],
            "artist_name": artist['name'],
            "tier": artist['tier'],
            "genre": artist['genre'],
            "card_type": card_type,
            "image": artist.get('image', ''),
            "stats": base_stats,
            "abilities": self._generate_abilities(artist, card_type),
            "power_level": artist['game_data']['power_level'],
            "created_at": datetime.utcnow().isoformat(),
            "rarity_score": self._calculate_rarity_score(artist, base_stats)
        }
        
        return card
    
    def _calculate_card_stats(self, artist: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate card stats based on artist metrics
        
        Args:
            artist: Artist data
            
        Returns:
            Card statistics
        """
        subs = artist['stats']['subscribers']
        views = artist['stats']['total_views']
        videos = artist['stats']['video_count']
        
        # Base stats calculation
        attack = min(subs // 10_000, 100)  # Max 100
        defense = min(views // 50_000_000, 100)  # Max 100
        speed = min(videos // 100, 100)  # Max 100
        
        # Tier bonuses
        tier_bonuses = {
            "legendary": {"attack": 20, "defense": 20, "speed": 20},
            "platinum": {"attack": 15, "defense": 15, "speed": 15},
            "gold": {"attack": 10, "defense": 10, "speed": 10},
            "silver": {"attack": 5, "defense": 5, "speed": 5},
            "bronze": {"attack": 3, "defense": 3, "speed": 3},
            "community": {"attack": 1, "defense": 1, "speed": 1}
        }
        
        bonus = tier_bonuses.get(artist['tier'], {"attack": 0, "defense": 0, "speed": 0})
        
        return {
            "attack": min(attack + bonus['attack'], 100),
            "defense": min(defense + bonus['defense'], 100),
            "speed": min(speed + bonus['speed'], 100),
            "health": 100  # Base health for all cards
        }
    
    def _generate_abilities(self, artist: Dict[str, Any], card_type: str) -> List[Dict[str, Any]]:
        """
        Generate card abilities based on artist and tier
        
        Args:
            artist: Artist data
            card_type: Type of card
            
        Returns:
            List of abilities
        """
        abilities = []
        
        # Tier-based abilities
        tier_abilities = {
            "legendary": [
                {"name": "Global Fame", "description": "Boost all allied cards by 10", "power": 10},
                {"name": "Viral Hit", "description": "Double attack for 3 turns", "power": 15}
            ],
            "platinum": [
                {"name": "Platinum Album", "description": "Heal 20 HP", "power": 8},
                {"name": "World Tour", "description": "Attack all enemies", "power": 12}
            ],
            "gold": [
                {"name": "Gold Record", "description": "Boost attack by 5", "power": 5},
                {"name": "Radio Play", "description": "Reduce enemy defense", "power": 7}
            ],
            "silver": [
                {"name": "Silver Screen", "description": "Increase speed", "power": 3}
            ],
            "bronze": [
                {"name": "Breakout Hit", "description": "Small attack boost", "power": 2}
            ],
            "community": [
                {"name": "Local Fame", "description": "Minor stat boost", "power": 1}
            ]
        }
        
        # Genre-based abilities
        genre_abilities = {
            "Hip-Hop": {"name": "Freestyle", "description": "Unpredictable attack", "power": 5},
            "Rock": {"name": "Power Chord", "description": "Heavy damage", "power": 8},
            "Pop": {"name": "Chart Topper", "description": "Popular appeal", "power": 6},
            "EDM": {"name": "Drop the Beat", "description": "Area effect", "power": 7},
            "Country": {"name": "Storyteller", "description": "Healing ability", "power": 4}
        }
        
        # Add tier abilities
        abilities.extend(tier_abilities.get(artist['tier'], []))
        
        # Add genre ability if available
        genre_ability = genre_abilities.get(artist['genre'])
        if genre_ability:
            abilities.append(genre_ability)
        
        return abilities
    
    def _calculate_rarity_score(self, artist: Dict[str, Any], stats: Dict[str, int]) -> int:
        """
        Calculate card rarity score for pack generation
        
        Args:
            artist: Artist data
            stats: Card stats
            
        Returns:
            Rarity score (higher = rarer)
        """
        tier_scores = {
            "legendary": 100,
            "platinum": 80,
            "gold": 60,
            "silver": 40,
            "bronze": 20,
            "community": 10
        }
        
        base_score = tier_scores.get(artist['tier'], 10)
        
        # Add stat bonuses
        stat_bonus = sum(stats.values()) // 10
        
        # Add subscriber bonus
        sub_bonus = min(artist['stats']['subscribers'] // 100_000, 20)
        
        return base_score + stat_bonus + sub_bonus
    
    async def create_pack_from_genre(self, genre: str, pack_size: int = 5) -> List[Dict[str, Any]]:
        """
        Create a pack of cards from a specific genre
        
        Args:
            genre: Music genre
            pack_size: Number of cards in pack
            
        Returns:
            List of cards
        """
        # Search for artists in genre
        search_query = f"{genre} music official"
        videos = await self.youtube_client.search_videos(search_query, 20)
        
        if not videos:
            return []
        
        cards = []
        
        # Create cards from different channels
        for video in videos[:pack_size]:
            # Extract channel name from video
            channel_name = video['channel']
            
            # Create artist from channel
            artist = await self.create_artist_from_youtube(channel_name)
            
            if artist:
                # Create card from artist
                card = await self.create_card_from_artist(artist)
                cards.append(card)
        
        return cards
    
    async def get_trending_cards(self, region: str = "US", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get cards from trending music
        
        Args:
            region: Region code
            limit: Maximum number of cards
            
        Returns:
            List of trending cards
        """
        # Get trending music
        trending_videos = await self.youtube_client.get_trending_music(region)
        
        cards = []
        
        for video in trending_videos[:limit]:
            channel_name = video['channel']
            
            # Create artist from trending channel
            artist = await self.create_artist_from_youtube(channel_name)
            
            if artist:
                # Create special "trending" card
                card = await self.create_card_from_artist(artist, "trending")
                cards.append(card)
        
        return cards


# Global instance
game_integration = GameIntegration()


# Example usage
async def example_usage():
    """Example of game integration usage"""
    
    # Create artist from YouTube
    artist = await game_integration.create_artist_from_youtube("Taylor Swift")
    if artist:
        print(f"Created artist: {artist['name']}")
        print(f"Tier: {artist['tier']} {artist['game_data']['tier_emoji']}")
        print(f"Power level: {artist['game_data']['power_level']}")
        
        # Create card from artist
        card = await game_integration.create_card_from_artist(artist)
        print(f"Card serial: {card['serial']}")
        print(f"Stats: {card['stats']}")
        print(f"Abilities: {[a['name'] for a in card['abilities']]}")
    
    # Create genre pack
    pack = await game_integration.create_pack_from_genre("Rock", 3)
    print(f"\nRock pack: {len(pack)} cards")
    for card in pack:
        print(f"  {card['artist_name']} - {card['tier']}")
    
    # Get trending cards
    trending = await game_integration.get_trending_cards("US", 5)
    print(f"\nTrending cards: {len(trending)} cards")


if __name__ == "__main__":
    asyncio.run(example_usage())
