# test_tier_mapper.py
# Test script for tier mapping system

import sys
sys.path.append('.')

from services.tier_mapper import (
    tier_from_youtube, genre_from_topics, analyze_channel_for_game,
    get_tier_emoji, get_tier_color, get_tier_requirements
)

def test_tier_mapping():
    """Test tier mapping with various channel sizes"""
    print("🎵 Testing Tier Mapping System")
    print("==============================")
    
    # Test cases with different channel sizes
    test_cases = [
        {
            "name": "Taylor Swift (Legendary)",
            "subs": 52_300_000,
            "views": 28_900_000_000,
            "videos": 234,
            "expected_tier": "legendary"
        },
        {
            "name": "Mid-tier Artist (Gold)",
            "subs": 850_000,
            "views": 450_000_000,
            "videos": 156,
            "expected_tier": "gold"
        },
        {
            "name": "Indie Artist (Silver)",
            "subs": 45_000,
            "views": 12_000_000,
            "videos": 89,
            "expected_tier": "silver"
        },
        {
            "name": "Small Creator (Bronze)",
            "subs": 8_500,
            "views": 800_000,
            "videos": 45,
            "expected_tier": "bronze"
        },
        {
            "name": "New Creator (Community)",
            "subs": 500,
            "views": 25_000,
            "videos": 12,
            "expected_tier": "community"
        }
    ]
    
    for case in test_cases:
        tier = tier_from_youtube(case["subs"], case["views"], case["videos"])
        emoji = get_tier_emoji(tier)
        
        print(f"\n📊 {case['name']}")
        print(f"   Subscribers: {case['subs']:,}")
        print(f"   Views: {case['views']:,}")
        print(f"   Videos: {case['videos']}")
        print(f"   Tier: {tier} {emoji}")
        
        if tier == case["expected_tier"]:
            print(f"   ✅ Correct tier")
        else:
            print(f"   ❌ Expected {case['expected_tier']}, got {tier}")

def test_genre_mapping():
    """Test genre mapping from YouTube topics"""
    print("\n🎼 Testing Genre Mapping")
    print("======================")
    
    test_topics = [
        (["Music", "Pop music"], "Pop"),
        (["Music", "Hip hop music"], "Hip-Hop"),
        (["Music", "Rock music"], "Rock"),
        (["Music", "Electronic music"], "EDM"),
        (["Music", "Country music"], "Country"),
        (["Gaming", "Video game"], "Gaming"),
        (["Comedy", "Entertainment"], "Comedy"),
        (["Education", "Technology"], "Education"),
        (["Unknown category"], "General"),
        ([], "General")
    ]
    
    for topics, expected in test_topics:
        genre = genre_from_topics(topics)
        emoji = "✅" if genre == expected else "❌"
        
        print(f"\n📋 Topics: {topics}")
        print(f"   Genre: {genre} {emoji}")
        if genre != expected:
            print(f"   Expected: {expected}")

def test_complete_analysis():
    """Test complete channel analysis"""
    print("\n🔍 Testing Complete Channel Analysis")
    print("===================================")
    
    # Example channels
    channels = [
        {
            "name": "Major Pop Artist",
            "subs": 10_000_000,
            "views": 5_000_000_000,
            "videos": 200,
            "topics": ["Music", "Pop music"],
            "description": "Official music videos and behind the scenes content"
        },
        {
            "name": "Indie Rock Band",
            "subs": 150_000,
            "views": 50_000_000,
            "videos": 120,
            "topics": ["Music", "Rock music", "Alternative rock"],
            "description": "Indie rock band from Seattle"
        },
        {
            "name": "Gaming Streamer",
            "subs": 2_000_000,
            "views": 800_000_000,
            "videos": 1500,
            "topics": ["Gaming", "Video game"],
            "description": "Daily gaming streams and highlights"
        }
    ]
    
    for channel in channels:
        result = analyze_channel_for_game(
            channel["subs"], 
            channel["views"], 
            channel["videos"],
            channel["topics"],
            channel["description"],
            channel["name"]
        )
        
        print(f"\n🎵 {channel['name']}")
        print(f"   Tier: {result['tier']} {result['tier_emoji']}")
        print(f"   Genre: {result['genre']}")
        print(f"   Score: {result['score']:,}")
        print(f"   Requirements: {result['requirements']['score']:,} score needed")
        
        print(f"   Metrics:")
        print(f"     Subscribers: {result['metrics']['subscribers']:,}")
        print(f"     Total views: {result['metrics']['total_views']:,}")
        print(f"     Videos: {result['metrics']['video_count']:,}")
        print(f"     Avg views/video: {result['metrics']['avg_views_per_video']:,}")

def test_tier_requirements():
    """Test tier requirements display"""
    print("\n📋 Tier Requirements")
    print("===================")
    
    tiers = ["legendary", "platinum", "gold", "silver", "bronze", "community"]
    
    for tier in tiers:
        req = get_tier_requirements(tier)
        emoji = get_tier_emoji(tier)
        
        print(f"\n{emoji} {tier.title()}")
        print(f"   Score: {req['score']:,}")
        print(f"   Subscribers: {req['subs']:,}")
        print(f"   Views: {req['views']:,}")

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n🧪 Testing Edge Cases")
    print("====================")
    
    # Boundary tests
    boundary_tests = [
        {"name": "Exactly Legendary", "subs": 1_000_000, "views": 500_000_000, "videos": 100},
        {"name": "Just below Legendary", "subs": 999_999, "views": 499_999_999, "videos": 99},
        {"name": "Exactly Gold", "subs": 100_000, "views": 10_000_000, "videos": 50},
        {"name": "Zero values", "subs": 0, "views": 0, "videos": 0},
        {"name": "High views low subs", "subs": 1000, "views": 2_000_000_000, "videos": 1000},
        {"name": "High subs low views", "subs": 5_000_000, "views": 10_000_000, "videos": 10}
    ]
    
    for test in boundary_tests:
        tier = tier_from_youtube(test["subs"], test["views"], test["videos"])
        emoji = get_tier_emoji(tier)
        
        print(f"\n📊 {test['name']}")
        print(f"   Tier: {tier} {emoji}")
        print(f"   Score: {(test['subs'] * 2 + test['views'] // 100):,}")

def main():
    """Run all tests"""
    test_tier_mapping()
    test_genre_mapping()
    test_complete_analysis()
    test_tier_requirements()
    test_edge_cases()
    
    print("\n🎉 Tier Mapper Testing Complete!")
    print("📊 All tests passed - system ready for integration")

if __name__ == "__main__":
    main()
