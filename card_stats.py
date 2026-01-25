"""
Card Stats System - Exact normalization as specified
Implements YouTube data to normalized stats with proper rarity mapping
"""

import math
import random
from typing import Dict, List, Optional

# Simple rarity system as specified
RARITY_WEIGHTS = {
    "Common": 60,
    "Uncommon": 28,
    "Rare": 10,
    "Epic": 1.5,
    "Legendary": 0.5,
}

def calc_power(view_count: int, like_count: int) -> int:
    """Calculate normalized power from YouTube metrics"""
    # Base power using log10 scaling: power = floor(log10(view_count + 1) * A + B)
    # Using A=2, B=0 as specified
    base = math.floor(math.log10(view_count + 1) * 2)
    
    # Engagement modifier: bonus = clamp(floor(engagement_ratio * C), 0, D)
    # Using C=100, D=5 as specified
    engagement_ratio = like_count / (view_count + 1)
    bonus = min(int(engagement_ratio * 100), 5)
    
    # Final power
    return base + bonus

def assign_rarity(power: int) -> str:
    """Assign rarity based on power using exact thresholds specified"""
    if power >= 15:
        return "Legendary"
    elif power >= 12:
        return "Epic"
    elif power >= 8:
        return "Rare"
    elif power >= 4:
        return "Uncommon"
    else:
        return "Common"

def pick_random_rarity() -> str:
    """Pick random rarity using weighted selection"""
    choices = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    return random.choices(choices, weights, k=1)[0]

def create_card_from_video(video_data: Dict, is_hero: bool = False) -> Dict:
    """Create card from YouTube video data using exact normalization"""
    
    # Extract metrics
    views = video_data.get("views", 0)
    likes = video_data.get("likes", 0)
    title = video_data.get("title", "Unknown")
    artist = video_data.get("artist", "Unknown Artist")
    video_id = video_data.get("video_id", "")
    
    # Calculate power using exact formula
    power = calc_power(views, likes)
    
    # Assign rarity based on power
    rarity = assign_rarity(power)
    
    # Hero cards get rarity boost
    if is_hero:
        if rarity == "Common":
            rarity = "Rare"
        elif rarity == "Uncommon":
            rarity = "Rare"
        elif rarity == "Rare":
            rarity = "Epic"
        elif rarity == "Epic":
            rarity = "Legendary"
        # Legendary stays Legendary
    
    # Calculate cost (simple formula: 1 cost per 3 power, minimum 1)
    cost = max(1, power // 3)
    
    # Generate simple abilities based on metrics
    abilities = []
    if views > 1000000:
        abilities.append("Trendsetter")
    if likes / max(views, 1) > 0.1:
        abilities.append("Viral")
    if views > 50000000:
        abilities.append("Classic")
    
    # Higher rarity gets bonus abilities
    if rarity == "Legendary" and len(abilities) < 2:
        abilities.append("Special")
    elif rarity == "Epic" and len(abilities) < 1:
        abilities.append("Rare")
    
    return {
        "name": title,
        "artist": artist,
        "power": power,
        "cost": cost,
        "rarity": rarity,
        "abilities": abilities,
        "views": views,
        "likes": likes,
        "video_id": video_id,
        "card_type": "song"
    }

def generate_pack_cards(hero_video_data: Dict, other_videos: List[Dict]) -> List[Dict]:
    """Generate a 5-card pack using exact specifications"""
    
    cards = []
    
    # Card 1: Hero (from YouTube URL → guaranteed)
    hero_card = create_card_from_video(hero_video_data, is_hero=True)
    cards.append(hero_card)
    
    # Cards 2-5: Weighted random picks from other videos
    for i in range(4):
        if other_videos:
            # Pick random video
            video_data = random.choice(other_videos)
            
            # Create card
            card = create_card_from_video(video_data, is_hero=False)
            
            # For secondary cards, sometimes force rarity for variety
            if i == 0:  # Card 2: ensure at least uncommon
                if card["rarity"] == "Common":
                    card["rarity"] = "Uncommon"
                    card["cost"] = max(1, card["power"] // 3)
            
            cards.append(card)
        else:
            # Fallback: create generic card
            fallback_card = {
                "name": f"Generated Card {i+2}",
                "artist": "System",
                "power": random.randint(2, 8),
                "cost": random.randint(1, 3),
                "rarity": pick_random_rarity(),
                "abilities": [],
                "views": 0,
                "likes": 0,
                "video_id": f"generated_{i+2}",
                "card_type": "song"
            }
            cards.append(fallback_card)
    
    return cards

def validate_pack_balance(cards: List[Dict]) -> bool:
    """Simple pack validation"""
    total_power = sum(card["power"] for card in cards)
    
    # Basic balance check: total power should be reasonable
    return 10 <= total_power <= 50
