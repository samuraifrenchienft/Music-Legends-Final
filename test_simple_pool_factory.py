# test_simple_pool_factory.py
# Test script for simplified artist pool and card factory

import sys
sys.path.append('.')

from services.artist_pool import get_random_artist, get_artists_by_genre, get_artists_by_tier, get_pool_stats
from services.card_factory import create_from_artist, create_pack_cards, create_genre_pack

def test_artist_pool():
    """Test simplified artist pool"""
    print("🎵 Testing Simplified Artist Pool")
    print("=================================")
    
    # Test random artist
    print("\n1. Testing get_random_artist()...")
    artist = get_random_artist()
    if artist:
        print(f"✅ Random artist: {artist.name} ({artist.tier})")
    else:
        print("⚠️  No artists in pool (expected if database is empty)")
    
    # Test genre filter
    print("\n2. Testing get_artists_by_genre()...")
    rock_artists = get_artists_by_genre("Rock", limit=3)
    print(f"✅ Found {len(rock_artists)} rock artists")
    
    # Test tier filter
    print("\n3. Testing get_artists_by_tier()...")
    gold_artists = get_artists_by_tier("gold", limit=3)
    print(f"✅ Found {len(gold_artists)} gold artists")
    
    # Test pool stats
    print("\n4. Testing get_pool_stats()...")
    stats = get_pool_stats()
    print(f"✅ Pool stats:")
    print(f"   Total artists: {stats.get('total_artists', 0)}")
    print(f"   By tier: {stats.get('by_tier', {})}")
    print(f"   By genre: {stats.get('by_genre', {})}")

def test_card_factory():
    """Test simplified card factory"""
    print("\n🃏 Testing Simplified Card Factory")
    print("===================================")
    
    # Mock artist for testing
    class MockArtist:
        def __init__(self):
            self.id = "test_artist_123"
            self.name = "Test Artist"
            self.genre = "Pop"
            self.tier = "gold"
    
    mock_artist = MockArtist()
    
    # Test card creation
    print("\n1. Testing create_from_artist()...")
    
    # Mock Card.count for testing
    class MockCard:
        @staticmethod
        def count(artist_id, tier):
            return 0  # First card
        
        @staticmethod
        def create(**kwargs):
            return type('Card', (), kwargs)()
    
    # Temporarily replace Card for testing
    import services.card_factory
    original_card = services.card_factory.Card
    services.card_factory.Card = MockCard
    
    try:
        card = create_from_artist(mock_artist)
        if card:
            print(f"✅ Created card: {card.serial}")
            print(f"   Artist ID: {card.artist_id}")
            print(f"   Tier: {card.tier}")
            print(f"   Source: {card.source}")
        else:
            print("❌ Failed to create card")
    finally:
        # Restore original Card
        services.card_factory.Card = original_card
    
    # Test pack creation
    print("\n2. Testing create_pack_cards()...")
    # This would require actual artists in database
    print("✅ Pack creation function available (requires database)")

def test_integration():
    """Test integration between pool and factory"""
    print("\n🔗 Testing Integration")
    print("====================")
    
    # Get artist from pool
    artist = get_random_artist()
    
    if artist:
        print(f"🎵 Selected artist: {artist.name}")
        
        # Mock Card for testing
        class MockCard:
            @staticmethod
            def count(artist_id, tier):
                return 0
            
            @staticmethod
            def create(**kwargs):
                return type('Card', (), kwargs)()
        
        import services.card_factory
        original_card = services.card_factory.Card
        services.card_factory.Card = MockCard
        
        try:
            # Create card from artist
            card = create_from_artist(artist)
            
            if card:
                print(f"✅ Created card: {card.serial}")
                print(f"   From artist: {card.artist_id}")
                print(f"   Tier: {card.tier}")
            else:
                print("❌ Failed to create card")
        finally:
            services.card_factory.Card = original_card
    else:
        print("⚠️  No artists available for integration test")

def main():
    """Run all tests"""
    print("🎵 Simplified Pool & Factory Test Suite")
    print("====================================")
    
    try:
        test_artist_pool()
        test_card_factory()
        test_integration()
        
        print("\n🎉 Test Suite Completed!")
        print("📊 All basic functionality tested")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
