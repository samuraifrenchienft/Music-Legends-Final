# test_pack_opening.py
# Test script for creator pack opening system

import asyncio
import sys
sys.path.append('.')

from services.open_creator import (
    open_creator_pack, open_premium_creator_pack, open_genre_focused_pack,
    calculate_pack_value, simulate_pack_opening
)
from services.creator_service import creator_service

def test_pack_opening():
    """Test basic pack opening"""
    print("📦 Testing Pack Opening")
    print("======================")
    
    # Create a mock pack for testing
    class MockPack:
        def __init__(self):
            self.id = "test_pack_123"
            self.name = "Test Rock Pack"
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.genre = "Rock"
            self.price_cents = 999
        
        def increment_purchases(self):
            pass
    
    mock_pack = MockPack()
    
    # Mock Artist.get_random_from for testing
    import services.open_creator
    original_random_from = None
    
    class MockArtist:
        def __init__(self, id, name, tier):
            self.id = id
            self.name = name
            self.tier = tier
            self.genre = "Rock"
    
    def mock_random_from(artist_ids):
        artists = [
            MockArtist("artist_1", "Queen", "legendary"),
            MockArtist("artist_2", "Led Zeppelin", "platinum"),
            MockArtist("artist_3", "The Beatles", "gold")
        ]
        return artists[0]  # Always return first artist for consistent testing
    
    # Mock Artist.where_in for testing
    def mock_where_in(field, ids):
        return [
            MockArtist("artist_1", "Queen", "legendary"),
            MockArtist("artist_2", "Led Zeppelin", "platinum"),
            MockArtist("artist_3", "The Beatles", "gold")
        ]
    
    # Temporarily replace functions
    services.open_creator.Artist.where_in = mock_where_in
    
    # Mock card creation
    class MockCard:
        def __init__(self, artist, tier, source):
            self.artist_id = artist.id
            self.artist_name = artist.name
            self.tier = tier
            self.source = source
            self.serial = f"TEST-{tier.upper()}-{artist.id[:4]}"
    
    original_create_from = None
    
    def mock_create_from_artist(artist, tier, source):
        return MockCard(artist, tier, source)
    
    services.open_creator.create_from_artist = mock_create_from_artist
    
    try:
        # Test standard pack opening
        print("\n1. Testing standard pack opening...")
        cards = open_creator_pack(mock_pack)
        
        if cards:
            print(f"✅ Opened pack: {len(cards)} cards")
            for card in cards:
                print(f"   {card.serial} - {card.artist_name} ({card.tier})")
            
            # Test value calculation
            value = calculate_pack_value(cards)
            print(f"   Total value: ${value['total_value_dollars']:.2f}")
        else:
            print("❌ Failed to open pack")
        
        # Test premium pack opening
        print("\n2. Testing premium pack opening...")
        premium_cards = open_premium_creator_pack(mock_pack, guaranteed_tiers=["gold"])
        
        if premium_cards:
            print(f"✅ Opened premium pack: {len(premium_cards)} cards")
            for card in premium_cards:
                print(f"   {card.serial} - {card.artist_name} ({card.tier})")
            
            premium_value = calculate_pack_value(premium_cards)
            print(f"   Total value: ${premium_value['total_value_dollars']:.2f}")
        else:
            print("❌ Failed to open premium pack")
        
        # Test genre-focused pack opening
        print("\n3. Testing genre-focused pack opening...")
        genre_cards = open_genre_focused_pack(mock_pack, focus_genre="Rock")
        
        if genre_cards:
            print(f"✅ Opened genre-focused pack: {len(genre_cards)} cards")
            for card in genre_cards:
                print(f"   {card.serial} - {card.artist_name} ({card.tier})")
        else:
            print("❌ Failed to open genre-focused pack")
            
    except Exception as e:
        print(f"❌ Error during pack opening tests: {e}")
        import traceback
        traceback.print_exc()

def test_value_calculation():
    """Test value calculation"""
    print("\n💰 Testing Value Calculation")
    print("===========================")
    
    # Mock cards for testing
    class MockCard:
        def __init__(self, tier):
            self.tier = tier
    
    test_cards = [
        MockCard("legendary"),
        MockCard("gold"),
        MockCard("silver"),
        MockCard("bronze"),
        MockCard("community")
    ]
    
    value = calculate_pack_value(test_cards)
    
    print(f"✅ Value calculation for test cards:")
    print(f"   Tier counts: {value['tier_counts']}")
    print(f"   Total value: ${value['total_value_dollars']:.2f}")
    print(f"   Card count: {value['card_count']}")
    print(f"   Average per card: ${value['average_value_per_card'] / 100:.2f}")

def test_simulation():
    """Test pack opening simulation"""
    print("\n🎲 Testing Pack Simulation")
    print("==========================")
    
    # Mock pack for simulation
    class MockPack:
        def __init__(self):
            self.id = "sim_pack_123"
            self.name = "Simulation Pack"
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.genre = "Rock"
            self.price_cents = 999
        
        def increment_purchases(self):
            pass
    
    mock_pack = MockPack()
    
    # Mock functions for simulation
    import services.open_creator
    
    class MockArtist:
        def __init__(self, id, name, tier):
            self.id = id
            self.name = name
            self.tier = tier
            self.genre = "Rock"
    
    def mock_where_in(field, ids):
        return [
            MockArtist("artist_1", "Queen", "legendary"),
            MockArtist("artist_2", "Led Zeppelin", "platinum"),
            MockArtist("artist_3", "The Beatles", "gold")
        ]
    
    services.open_creator.Artist.where_in = mock_where_in
    
    class MockCard:
        def __init__(self, artist, tier, source):
            self.artist_id = artist.id
            self.artist_name = artist.name
            self.tier = tier
            self.source = source
            self.serial = f"SIM-{tier.upper()}-{artist.id[:4]}"
    
    def mock_create_from_artist(artist, tier, source):
        return MockCard(artist, tier, source)
    
    services.open_creator.create_from_artist = mock_create_from_artist
    
    try:
        print("\n🎲 Running simulation (20 iterations)...")
        results = simulate_pack_opening(mock_pack, simulations=20)
        
        print(f"✅ Simulation results:")
        print(f"   Simulations: {results['simulations']}")
        print(f"   Average value: ${results['average_value_dollars']:.2f}")
        print(f"   Min value: ${results['min_value_cents'] / 100:.2f}")
        print(f"   Max value: ${results['max_value_cents'] / 100:.2f}")
        
        print(f"   Hit rates:")
        for tier, rate in results['hit_rates'].items():
            print(f"      {tier}: {rate:.1f}%")
        
        print(f"   Tier distribution:")
        for tier, count in results['tier_distribution'].items():
            if count > 0:
                print(f"      {tier}: {count}")
                
    except Exception as e:
        print(f"❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🧪 Testing Edge Cases")
    print("====================")
    
    # Test with empty pack
    class EmptyPack:
        def __init__(self):
            self.id = "empty_pack"
            self.name = "Empty Pack"
            self.artist_ids = []
            self.genre = "None"
            self.price_cents = 999
        
        def increment_purchases(self):
            pass
    
    empty_pack = EmptyPack()
    
    print("\n1. Testing empty pack...")
    cards = open_creator_pack(empty_pack)
    print(f"   Result: {len(cards)} cards (expected: 0)")
    
    # Test with invalid pack
    print("\n2. Testing None pack...")
    try:
        cards = open_creator_pack(None)
        print(f"   Result: {len(cards)} cards (should handle gracefully)")
    except Exception as e:
        print(f"   Error handled: {type(e).__name__}")
    
    # Test value calculation with empty cards
    print("\n3. Testing value calculation with empty cards...")
    empty_value = calculate_pack_value([])
    print(f"   Result: ${empty_value['total_value_dollars']:.2f} (expected: $0.00)")

def main():
    """Run all tests"""
    print("📦 Creator Pack Opening Test Suite")
    print("=================================")
    
    try:
        test_pack_opening()
        test_value_calculation()
        test_simulation()
        test_edge_cases()
        
        print("\n🎉 Pack Opening Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
