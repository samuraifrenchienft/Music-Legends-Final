"""
Card Stats System - Professional TCG Design Principles
Implements normalized stats, rarity tiers, and balanced pack generation
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon" 
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class CardType(Enum):
    SONG = "song"
    ARTIST = "artist"
    COLLABORATION = "collaboration"

@dataclass
class CardStats:
    """Core card attributes following TCG design principles"""
    power: int           # Direct gameplay strength (1-20)
    cost: int            # Resource requirement (1-10)
    rarity: Rarity       # Rarity tier
    abilities: List[str] # Special effects/keywords
    
    # YouTube-derived metrics (normalized)
    views: int
    likes: int
    engagement_ratio: float
    
    # Card metadata
    name: str
    artist: str
    video_id: str
    card_type: CardType
    
    def get_effective_power(self) -> int:
        """Calculate power with ability bonuses"""
        base_power = self.power
        ability_bonus = len(self.abilities) * 2  # Each ability adds +2 power
        return base_power + ability_bonus

class StatNormalizer:
    """Normalizes YouTube metrics into balanced gameplay stats"""
    
    @staticmethod
    def normalize_power(views: int, likes: int) -> int:
        """
        Convert YouTube metrics to balanced power stat
        Uses log10 scaling to prevent outliers from dominating
        """
        # Log10 scaling compresses huge numbers
        view_power = math.floor(math.log10(max(views, 1)) * 2)
        
        # Likes provide secondary bonus
        like_bonus = math.floor(math.log10(max(likes, 1)) * 0.5)
        
        # Combine and cap at reasonable range
        raw_power = view_power + like_bonus
        return max(1, min(20, raw_power))  # Cap between 1-20
    
    @staticmethod
    def calculate_cost(power: int, rarity: Rarity) -> int:
        """Cost should correlate with power and rarity"""
        base_cost = max(1, power // 3)  # Roughly 1 cost per 3 power
        
        # Rarity increases cost
        rarity_cost_modifier = {
            Rarity.COMMON: 0,
            Rarity.UNCOMMON: 1,
            Rarity.RARE: 2,
            Rarity.EPIC: 3,
            Rarity.LEGENDARY: 4
        }
        
        total_cost = base_cost + rarity_cost_modifier[rarity]
        return max(1, min(10, total_cost))  # Cap between 1-10
    
    @staticmethod
    def calculate_engagement_ratio(views: int, likes: int) -> float:
        """Calculate likes/views ratio for ability determination"""
        if views == 0:
            return 0.0
        return min(1.0, likes / views)  # Cap at 1.0 (100%)

class RarityAssigner:
    """Assigns rarity based on normalized stats and engagement"""
    
    # Rarity buckets based on power and engagement
    RARITY_THRESHOLDS = {
        Rarity.LEGENDARY: {"power_min": 13, "engagement_min": 0.08},
        Rarity.EPIC: {"power_min": 10, "engagement_min": 0.05},
        Rarity.RARE: {"power_min": 7, "engagement_min": 0.03},
        Rarity.UNCOMMON: {"power_min": 4, "engagement_min": 0.01},
        Rarity.COMMON: {"power_min": 0, "engagement_min": 0.0}
    }
    
    # Frequency weights for pack generation
    RARITY_WEIGHTS = {
        Rarity.COMMON: 40,
        Rarity.UNCOMMON: 30,
        Rarity.RARE: 20,
        Rarity.EPIC: 8,
        Rarity.LEGENDARY: 2
    }
    
    @classmethod
    def assign_rarity(cls, power: int, engagement_ratio: float) -> Rarity:
        """Assign rarity based on stats"""
        for rarity in [Rarity.LEGENDARY, Rarity.EPIC, Rarity.RARE, Rarity.UNCOMMON, Rarity.COMMON]:
            threshold = cls.RARITY_THRESHOLDS[rarity]
            if power >= threshold["power_min"] and engagement_ratio >= threshold["engagement_min"]:
                return rarity
        return Rarity.COMMON
    
    @classmethod
    def get_weighted_rarity(cls, exclude_rarities: List[Rarity] = None) -> Rarity:
        """Get random rarity based on frequency weights"""
        exclude_rarities = exclude_rarities or []
        
        # Filter out excluded rarities
        available_rarities = {
            rarity: weight for rarity, weight in cls.RARITY_WEIGHTS.items()
            if rarity not in exclude_rarities
        }
        
        if not available_rarities:
            return Rarity.COMMON
        
        # Weighted random selection
        total_weight = sum(available_rarities.values())
        rand = random.random() * total_weight
        
        current_weight = 0
        for rarity, weight in available_rarities.items():
            current_weight += weight
            if rand <= current_weight:
                return rarity
        
        return list(available_rarities.keys())[0]

class AbilityGenerator:
    """Generates thematic abilities based on video metrics"""
    
    ABILITIES = {
        "trendsetter": {
            "name": "Trendsetter",
            "requirement": lambda views, likes: views > 1000000,  # 1M+ views
            "description": "This card gains +1 power for each Trendsetter card in play"
        },
        "viral_surge": {
            "name": "Viral Surge", 
            "requirement": lambda views, likes: (likes / max(views, 1)) > 0.1,  # 10%+ engagement
            "description": "When played, draw an extra card if this was the last card played"
        },
        "classic_hit": {
            "name": "Classic Hit",
            "requirement": lambda views, likes: views > 50000000,  # 50M+ views
            "description": "This card cannot be removed from play by opponent's abilities"
        },
        "rising_star": {
            "name": "Rising Star",
            "requirement": lambda views, likes: 100000 < views < 1000000,  # 100K-1M views
            "description": "This card gains +2 power if played in the first 3 turns"
        },
        "fan_favorite": {
            "name": "Fan Favorite",
            "requirement": lambda views, likes: (likes / max(views, 1)) > 0.05,  # 5%+ engagement
            "description": "Reduce cost of next card by 1"
        },
        "breakout_hit": {
            "name": "Breakout Hit",
            "requirement": lambda views, likes: views < 50000 and likes > 10000,  # Low views, high likes
            "description": "Double power when opponent has no cards in play"
        }
    }
    
    @classmethod
    def generate_abilities(cls, views: int, likes: int, rarity: Rarity) -> List[str]:
        """Generate abilities based on video metrics and rarity"""
        abilities = []
        
        # Check each ability requirement
        for ability_key, ability_data in cls.ABILITIES.items():
            if ability_data["requirement"](views, likes):
                abilities.append(ability_key)
        
        # Higher rarity cards get bonus abilities
        rarity_bonus_abilities = {
            Rarity.LEGENDARY: 2,
            Rarity.EPIC: 1,
            Rarity.RARE: 1,
            Rarity.UNCOMMON: 0,
            Rarity.COMMON: 0
        }
        
        bonus_count = rarity_bonus_abilities[rarity]
        if bonus_count > 0:
            # Add random bonus abilities for higher rarity
            all_abilities = list(cls.ABILITIES.keys())
            available_bonus = [a for a in all_abilities if a not in abilities]
            
            if available_bonus:
                bonus_abilities = random.sample(available_bonus, min(bonus_count, len(available_bonus)))
                abilities.extend(bonus_abilities)
        
        return abilities

class CardFactory:
    """Factory for creating balanced cards from YouTube data"""
    
    @staticmethod
    def create_card_from_video(video_data: Dict, is_hero: bool = False) -> CardStats:
        """Create a balanced card from YouTube video data"""
        
        # Extract metrics
        views = video_data.get("views", 0)
        likes = video_data.get("likes", 0)
        title = video_data.get("title", "Unknown")
        artist = video_data.get("artist", "Unknown Artist")
        video_id = video_data.get("video_id", "")
        
        # Normalize stats
        power = StatNormalizer.normalize_power(views, likes)
        engagement_ratio = StatNormalizer.calculate_engagement_ratio(views, likes)
        
        # Assign rarity (hero cards get rarity boost)
        base_rarity = RarityAssigner.assign_rarity(power, engagement_ratio)
        if is_hero:
            # Hero cards get at least Rare rarity
            rarity_upgrade = {
                Rarity.COMMON: Rarity.RARE,
                Rarity.UNCOMMON: Rarity.RARE,
                Rarity.RARE: Rarity.EPIC,
                Rarity.EPIC: Rarity.LEGENDARY,
                Rarity.LEGENDARY: Rarity.LEGENDARY
            }
            rarity = rarity_upgrade[base_rarity]
        else:
            rarity = base_rarity
        
        # Calculate cost
        cost = StatNormalizer.calculate_cost(power, rarity)
        
        # Generate abilities
        abilities = AbilityGenerator.generate_abilities(views, likes, rarity)
        
        # Determine card type
        card_type = CardType.SONG  # Default to song for YouTube videos
        
        return CardStats(
            power=power,
            cost=cost,
            rarity=rarity,
            abilities=abilities,
            views=views,
            likes=likes,
            engagement_ratio=engagement_ratio,
            name=title,
            artist=artist,
            video_id=video_id,
            card_type=card_type
        )
    
    @staticmethod
    def create_balanced_secondary_card(video_data: Dict, target_rarity: Optional[Rarity] = None) -> CardStats:
        """Create a secondary card with balanced stats for pack generation"""
        
        card = CardFactory.create_card_from_video(video_data, is_hero=False)
        
        # If target rarity specified, adjust the card
        if target_rarity and card.rarity != target_rarity:
            # Adjust stats to match target rarity
            card.rarity = target_rarity
            card.cost = StatNormalizer.calculate_cost(card.power, target_rarity)
            card.abilities = AbilityGenerator.generate_abilities(card.views, card.likes, target_rarity)
        
        return card

# Pack generation configuration
PACK_DISTRIBUTION = {
    "total_cards": 5,
    "hero_cards": 1,
    "artist_top_cards": 1,
    "related_cards": 2,
    "wildcard_cards": 1
}

RARITY_DISTRIBUTION_PER_PACK = {
    Rarity.COMMON: 2,
    Rarity.UNCOMMON: 1,
    Rarity.RARE: 1,
    Rarity.EPIC: 0.5,  # 50% chance
    Rarity.LEGENDARY: 0.1   # 10% chance
}
