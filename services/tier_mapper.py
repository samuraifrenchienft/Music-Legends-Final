# services/tier_mapper.py
"""
Music Legends Tier Mapper
Convert YouTube channel data to game tiers and genres
"""

from typing import Dict, List, Optional, Tuple
import re

def tier_from_youtube(subs: int, views: int, videos: int = 0) -> str:
    """
    Convert YouTube channel metrics to game tier
    
    Args:
        subs: Subscriber count
        views: Total view count
        videos: Number of videos (optional bonus)
    
    Returns:
        Game tier: legendary, platinum, gold, silver, bronze, community
    """
    # Base score calculation
    score = (subs * 2) + (views // 100)
    
    # Video count bonus (encourages active channels)
    if videos > 0:
        video_bonus = min(videos * 50, 500_000)  # Cap bonus at 500k
        score += video_bonus
    
    # Tier thresholds
    if score >= 10_000_000:
        return "legendary"
    elif score >= 5_000_000:
        return "platinum"
    elif score >= 1_000_000:
        return "gold"
    elif score >= 100_000:
        return "silver"
    elif score >= 10_000:
        return "bronze"
    else:
        return "community"

def tier_from_score(score: int) -> str:
    """
    Convert raw score to tier
    
    Args:
        score: Calculated popularity score
    
    Returns:
        Game tier string
    """
    if score >= 10_000_000:
        return "legendary"
    elif score >= 5_000_000:
        return "platinum"
    elif score >= 1_000_000:
        return "gold"
    elif score >= 100_000:
        return "silver"
    elif score >= 10_000:
        return "bronze"
    else:
        return "community"

def calculate_popularity_score(subs: int, views: int, videos: int = 0, 
                              avg_views_per_video: float = 0) -> int:
    """
    Calculate comprehensive popularity score
    
    Args:
        subs: Subscriber count
        views: Total view count
        videos: Number of videos
        avg_views_per_video: Average views per video
    
    Returns:
        Popularity score
    """
    # Base score
    score = (subs * 2) + (views // 100)
    
    # Video count bonus
    if videos > 0:
        video_bonus = min(videos * 50, 500_000)
        score += video_bonus
    
    # Engagement bonus (average views per video)
    if avg_views_per_video > 0:
        engagement_bonus = min(int(avg_views_per_video * 10), 1_000_000)
        score += engagement_bonus
    
    return score

def genre_from_topics(topics: List[str]) -> str:
    """
    Convert YouTube topic categories to game genres
    
    Args:
        topics: List of YouTube topic categories
    
    Returns:
        Game genre string
    """
    # Comprehensive genre mapping
    GENRE_MAP = {
        # Music genres
        "Music": "Music",
        "Hip hop": "Hip-Hop",
        "Hip hop music": "Hip-Hop",
        "Rap": "Hip-Hop",
        "Rock music": "Rock",
        "Rock": "Rock",
        "Pop music": "Pop",
        "Pop": "Pop",
        "Electronic": "EDM",
        "Electronic music": "EDM",
        "House": "EDM",
        "Techno": "EDM",
        "Dubstep": "EDM",
        "Country": "Country",
        "Country music": "Country",
        "Folk": "Folk",
        "Folk music": "Folk",
        "Jazz": "Jazz",
        "Jazz music": "Jazz",
        "Blues": "Blues",
        "Classical": "Classical",
        "Classical music": "Classical",
        "R&B": "R&B",
        "Rhythm and blues": "R&B",
        "Soul": "R&B",
        "Reggae": "Reggae",
        "Latin": "Latin",
        "Latin music": "Latin",
        "Metal": "Metal",
        "Heavy metal": "Metal",
        "Punk": "Punk",
        "Punk rock": "Punk",
        "Indie": "Indie",
        "Alternative": "Alternative",
        "Alternative rock": "Alternative",
        
        # Non-music categories
        "Gaming": "Gaming",
        "Video game": "Gaming",
        "Sports": "Sports",
        "Comedy": "Comedy",
        "Entertainment": "Entertainment",
        "Education": "Education",
        "Technology": "Technology",
        "Science": "Science",
        "News": "News",
        "Politics": "News",
        "Fashion": "Fashion",
        "Beauty": "Beauty",
        "Food": "Food",
        "Cooking": "Food",
        "Travel": "Travel",
        "Lifestyle": "Lifestyle",
        "Health": "Health",
        "Fitness": "Fitness"
    }
    
    # Normalize topics and check matches
    for topic in topics:
        topic_lower = topic.lower()
        
        # Direct matches
        if topic in GENRE_MAP:
            return GENRE_MAP[topic]
        
        # Partial matches
        for pattern, genre in GENRE_MAP.items():
            if pattern.lower() in topic_lower:
                return genre
    
    # Fallback to "General"
    return "General"

def genre_from_channel_description(description: str, channel_name: str = "") -> str:
    """
    Extract genre from channel description and name
    
    Args:
        description: Channel description text
        channel_name: Channel name (optional)
    
    Returns:
        Game genre string
    """
    text = f"{channel_name} {description}".lower()
    
    # Genre keywords
    genre_keywords = {
        "Hip-Hop": ["hip hop", "rap", "hip-hop", "rapper"],
        "Rock": ["rock", "metal", "punk", "alternative"],
        "Pop": ["pop", "top 40", "hits"],
        "EDM": ["edm", "electronic", "house", "techno", "dubstep", "dance"],
        "Country": ["country", "nashville", "cowboy"],
        "Jazz": ["jazz", "blues", "swing"],
        "Classical": ["classical", "orchestra", "symphony"],
        "R&B": ["r&b", "rnb", "soul", "rhythm and blues"],
        "Latin": ["latin", "salsa", "reggaeton", "bachata"],
        "Folk": ["folk", "acoustic", "indie folk"],
        "Gaming": ["gaming", "game", "gamer", "lets play"],
        "Comedy": ["comedy", "funny", "humor", "standup"],
        "Education": ["education", "learn", "tutorial", "educational"],
        "Technology": ["tech", "technology", "programming", "software"],
        "Food": ["food", "cooking", "recipe", "chef"],
        "Travel": ["travel", "vlog", "adventure", "explore"]
    }
    
    # Check for genre keywords
    for genre, keywords in genre_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return genre
    
    return "General"

def get_tier_color(tier: str) -> str:
    """
    Get Discord embed color for tier
    
    Args:
        tier: Game tier
    
    Returns:
        Discord color hex code
    """
    tier_colors = {
        "legendary": 0xFFD700,  # Gold
        "platinum": 0xE5E4E2,  # Silver
        "gold": 0xFFD700,       # Gold
        "silver": 0xC0C0C0,     # Silver
        "bronze": 0xCD7F32,     # Bronze
        "community": 0x808080   # Gray
    }
    return tier_colors.get(tier, 0x808080)

def get_tier_emoji(tier: str) -> str:
    """
    Get emoji for tier
    
    Args:
        tier: Game tier
    
    Returns:
        Discord emoji string
    """
    tier_emojis = {
        "legendary": "🏆",
        "platinum": "💎",
        "gold": "🥇",
        "silver": "🥈",
        "bronze": "🥉",
        "community": "👥"
    }
    return tier_emojis.get(tier, "👥")

def get_tier_requirements(tier: str) -> Dict[str, int]:
    """
    Get minimum requirements for tier
    
    Args:
        tier: Game tier
    
    Returns:
        Dictionary with minimum requirements
    """
    requirements = {
        "legendary": {"score": 10_000_000, "subs": 1_000_000, "views": 500_000_000},
        "platinum": {"score": 5_000_000, "subs": 500_000, "views": 100_000_000},
        "gold": {"score": 1_000_000, "subs": 100_000, "views": 10_000_000},
        "silver": {"score": 100_000, "subs": 10_000, "views": 1_000_000},
        "bronze": {"score": 10_000, "subs": 1_000, "views": 100_000},
        "community": {"score": 0, "subs": 0, "views": 0}
    }
    return requirements.get(tier, requirements["community"])

def analyze_channel_for_game(subs: int, views: int, videos: int, 
                            topics: List[str], description: str = "", 
                            channel_name: str = "") -> Dict[str, any]:
    """
    Complete channel analysis for game integration
    
    Args:
        subs: Subscriber count
        views: Total view count
        videos: Number of videos
        topics: YouTube topic categories
        description: Channel description
        channel_name: Channel name
    
    Returns:
        Dictionary with tier, genre, and metadata
    """
    # Calculate metrics
    avg_views = views // videos if videos > 0 else 0
    score = calculate_popularity_score(subs, views, videos, avg_views)
    tier = tier_from_score(score)
    
    # Determine genre
    genre = genre_from_topics(topics)
    if genre == "General":
        genre = genre_from_channel_description(description, channel_name)
    
    return {
        "tier": tier,
        "genre": genre,
        "score": score,
        "tier_emoji": get_tier_emoji(tier),
        "tier_color": get_tier_color(tier),
        "requirements": get_tier_requirements(tier),
        "metrics": {
            "subscribers": subs,
            "total_views": views,
            "video_count": videos,
            "avg_views_per_video": avg_views
        }
    }

# Example usage and testing
def example_usage():
    """Example of tier mapper usage"""
    
    # Example 1: Major artist
    taylor_swift = {
        "subs": 52_300_000,
        "views": 28_900_000_000,
        "videos": 234,
        "topics": ["Music", "Pop music"],
        "description": "Taylor Swift Official Music Videos"
    }
    
    result = analyze_channel_for_game(**taylor_swift)
    print(f"Taylor Swift - Tier: {result['tier']} ({result['tier_emoji']})")
    print(f"Genre: {result['genre']}")
    print(f"Score: {result['score']:,}")
    
    # Example 2: Indie artist
    indie_artist = {
        "subs": 45_000,
        "views": 12_000_000,
        "videos": 89,
        "topics": ["Music", "Indie"],
        "description": "Indie folk and acoustic music"
    }
    
    result = analyze_channel_for_game(**indie_artist)
    print(f"\nIndie Artist - Tier: {result['tier']} ({result['tier_emoji']})")
    print(f"Genre: {result['genre']}")
    print(f"Score: {result['score']:,}")

if __name__ == "__main__":
    example_usage()
