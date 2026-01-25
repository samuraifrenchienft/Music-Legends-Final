"""
Card Stats System - Hybrid Weighted Pool Model
Implements industry-standard TCG pack generation with weighted pools
"""

import math
import random
from typing import Dict, List, Optional

def assign_rarity_by_views(views: int) -> str:
    """Assign rarity based on view count tiers"""
    if views >= 1_000_000_000:  # 1B+ views
        return "Legendary"
    elif views >= 100_000_000:  # 100M-1B views
        return "Epic"
    elif views >= 10_000_000:   # 10M-100M views
        return "Rare"
    else:                       # <10M views
        return "Common"

def calculate_power_by_views(views: int, artist_baseline: int = 50) -> int:
    """Calculate power based on view count tiers with normalization"""
    
    # Base power by tier
    if views >= 1_000_000_000:  # Legendary: 90-100 power
        base_power = random.randint(90, 100)
    elif views >= 100_000_000:  # Epic: 70-89 power
        base_power = random.randint(70, 89)
    elif views >= 10_000_000:   # Rare: 50-69 power
        base_power = random.randint(50, 69)
    else:                       # Common: 30-49 power
        base_power = random.randint(30, 49)
    
    # Normalize based on artist baseline popularity
    # (Drake's "worst" song still beats most artists)
    if artist_baseline > 80:  # Super popular artist
        base_power = max(base_power, 60)  # Minimum Rare-tier power
    
    # Genre weighting (K-pop inflated views vs niche indie)
    # This would need genre detection - simplified for now
    
    # Recency decay (2010 song with 100M ≠ 2024 song with 100M)
    # This would need release date - simplified for now
    
    return base_power

def calculate_cost(power: int) -> int:
    """Calculate cost based on power (1 cost per 10 power, minimum 1)"""
    return max(1, power // 10)

def assign_abilities_by_rarity(rarity: str, views: int) -> List[str]:
    """Assign abilities based on rarity and view count"""
    abilities = []
    
    # Base abilities by view count
    if views >= 1_000_000_000:
        abilities.append("Mega Hit")
    elif views >= 500_000_000:
        abilities.append("Viral Sensation")
    elif views >= 100_000_000:
        abilities.append("Chart Topper")
    
    # Rarity bonus abilities
    if rarity == "Legendary":
        if len(abilities) < 2:
            abilities.append("Iconic Status")
        abilities.append("Legendary Power")
    elif rarity == "Epic":
        if len(abilities) < 1:
            abilities.append("Epic Performance")
    elif rarity == "Rare":
        if len(abilities) < 1:
            abilities.append("Rare Find")
    
    return abilities

def create_card_from_video(video_data: Dict, is_hero: bool = False, artist_baseline: int = 50) -> Dict:
    """Create card using view count tier system"""
    
    # Extract metrics
    views = video_data.get("views", 0)
    likes = video_data.get("likes", 0)
    title = video_data.get("title", "Unknown")
    artist = video_data.get("artist", "Unknown Artist")
    video_id = video_data.get("video_id", "")
    
    # Assign rarity by view count
    rarity = assign_rarity_by_views(views)
    
    # Hero cards get rarity boost
    if is_hero:
        if rarity == "Common":
            rarity = "Rare"
        elif rarity == "Rare":
            rarity = "Epic"
        elif rarity == "Epic":
            rarity = "Legendary"
        # Legendary stays Legendary
    
    # Calculate power
    power = calculate_power_by_views(views, artist_baseline)
    
    # Calculate cost
    cost = calculate_cost(power)
    
    # Assign abilities
    abilities = assign_abilities_by_rarity(rarity, views)
    
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

def generate_weighted_pools(hero_video_data: Dict, same_artist_videos: List[Dict], related_videos: List[Dict]) -> Dict:
    """Build weighted pools for card generation"""
    
    pools = {
        "same_artist": same_artist_videos[:20],  # Top 20 most viewed
        "related_genre": related_videos[:30],    # Related videos
        "wildcard": related_videos[30:50] if len(related_videos) > 30 else []  # Broader pool
    }
    
    return pools

def weighted_random_selection(pools: Dict, target_count: int = 4) -> List[Dict]:
    """Select cards using weighted pool system"""
    
    selected_cards = []
    
    # Pool 1: Same artist (60% weight) - Pick 2-3 cards
    same_artist_pool = pools.get("same_artist", [])
    if same_artist_pool:
        # 60% chance to pick from same artist
        if random.random() < 0.6:
            artist_count = random.randint(2, 3)  # 2-3 cards from same artist
            artist_count = min(artist_count, len(same_artist_pool))
            selected_cards.extend(random.sample(same_artist_pool, artist_count))
    
    # Pool 2: Related genre (30% weight) - Pick 1-2 cards
    related_genre_pool = pools.get("related_genre", [])
    if len(selected_cards) < 4 and related_genre_pool:
        # 30% chance to pick from related genre
        if random.random() < 0.3:
            genre_count = random.randint(1, 2)  # 1-2 cards from related genre
            genre_count = min(genre_count, len(related_genre_pool))
            selected_cards.extend(random.sample(related_genre_pool, genre_count))
    
    # Pool 3: Wildcard (10% weight) - Fill remaining
    wildcard_pool = pools.get("wildcard", [])
    while len(selected_cards) < 4:
        if wildcard_pool:
            selected_cards.append(random.choice(wildcard_pool))
        else:
            # Fallback to any available pool
            all_pools = same_artist_pool + related_genre_pool
            if all_pools:
                selected_cards.append(random.choice(all_pools))
            else:
                break
    
    return selected_cards[:4]  # Ensure exactly 4 cards

def generate_hybrid_pack(hero_video_data: Dict, same_artist_videos: List[Dict], related_videos: List[Dict]) -> List[Dict]:
    """Generate pack using hybrid weighted pool system"""
    
    cards = []
    
    # Step 1: Hero card (user-selected URL)
    hero_card = create_card_from_video(hero_video_data, is_hero=True)
    cards.append(hero_card)
    
    # Step 2: Build weighted pools
    pools = generate_weighted_pools(hero_video_data, same_artist_videos, related_videos)
    
    # Step 3: Select 4 secondary cards using weighted random
    selected_video_data = weighted_random_selection(pools, 4)
    
    # Step 4: Create cards from selected videos
    artist_baseline = hero_card.get("power", 50)  # Use hero power as baseline
    
    for video_data in selected_video_data:
        card = create_card_from_video(video_data, is_hero=False, artist_baseline=artist_baseline)
        cards.append(card)
    
    # Step 5: Ensure exactly 5 cards
    while len(cards) < 5:
        # Fallback cards if needed
        fallback_card = {
            "name": f"Bonus Card {len(cards)+1}",
            "artist": hero_card["artist"],
            "power": random.randint(40, 60),
            "cost": 4,
            "rarity": "Rare",
            "abilities": ["Bonus"],
            "views": 50_000_000,
            "likes": 2_000_000,
            "video_id": f"bonus_{len(cards)}",
            "card_type": "song"
        }
        cards.append(fallback_card)
    
    return cards

def validate_pack_theme(cards: List[Dict]) -> Dict:
    """Validate pack theme coherence"""
    
    artists = [card["artist"] for card in cards]
    hero_artist = cards[0]["artist"]
    
    # Calculate theme coherence
    same_artist_count = artists.count(hero_artist)
    theme_coherence = same_artist_count / len(cards)
    
    # Rarity distribution
    rarity_dist = {}
    for card in cards:
        rarity = card["rarity"]
        rarity_dist[rarity] = rarity_dist.get(rarity, 0) + 1
    
    return {
        "coherence": theme_coherence,
        "same_artist_count": same_artist_count,
        "rarity_distribution": rarity_dist,
        "total_power": sum(card["power"] for card in cards)
    }

def get_pack_theme_description(cards: List[Dict]) -> str:
    """Generate theme description for pack"""
    
    validation = validate_pack_theme(cards)
    coherence = validation["coherence"]
    hero_artist = cards[0]["artist"]
    
    if coherence >= 0.6:
        return f"Artist-focused: {hero_artist} themed pack"
    elif coherence >= 0.3:
        return f"Mixed theme: {hero_artist} + related artists"
    else:
        return "Variety pack: Diverse artist collection"
