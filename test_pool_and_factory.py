# test_pool_and_factory.py
# Test script for artist pool and card factory

import asyncio
import sys
sys.path.append('.')

from services.artist_pool import artist_pool, get_random_artist
from services.card_factory import card_factory, create_from_artist

def test_artist_pool():
    """Test artist pool functionality"""
    print("🎵 Testing Artist Pool")
    print("====================")
    
    # Test random artist selection
    print("\n1. Testing random artist selection...")
    artist = get_random_artist()
    if artist:
        print(f"✅ Random artist: {artist.name} ({artist.tier})")
    else:
        print("⚠️  No artists in pool (this is expected if database is empty)")
    
    # Test genre filtering
    print("\n2. Testing genre filtering...")
    rock_artists = artist_pool.get_artists_by_genre("Rock", limit=3)
    print(f"✅ Found {len(rock_artists)} rock artists")
    
    # Test tier filtering
    print("\n3. Testing tier filtering...")
    legendary_artists = artist_pool.get_artists_by_tier("legendary", limit=3)
    print(f"✅ Found {len(legendary_artists)} legendary artists")
    
    # Test diverse pool
    print("\n4. Testing diverse pool...")
    diverse = artist_pool.get_diverse_pool(size=5)
    print(f"✅ Diverse pool: {len(diverse)} artists")
    
    # Test statistics
    print("\n5. Testing pool statistics...")
    stats = artist_pool.get_pool_statistics()
    print(f"✅ Pool statistics:")
    print(f"   Total artists: {stats.get('total_artists', 0)}")
    print(f"   By tier: {stats.get('by_tier', {})}")
    print(f"   By genre: {stats.get('by_genre', {})}")

def test_card_factory():
    """Test card factory functionality"""
    print("\n🃏 Testing Card Factory")
    print("======================")
    
    # This would require actual Artist objects
    # For now, we'll test the factory structure
    
    print("\n1. Testing serial generation...")
    # Mock artist for testing
    class MockArtist:
        def __init__(self):
            self.id = "12345678"
            self.name = "Test Artist"
            self.genre = "Pop"
            self.tier = "gold"
            self.popularity = 100000
            self.score = 5000000
            self.image_url = ""
    
    mock_artist = MockArtist()
    
    # Test serial generation
    serial1 = card_factory._generate_serial(mock_artist, "gold")
    serial2 = card_factory._generate_serial(mock_artist, "gold")
    
    print(f"✅ Generated serials: {serial1}, {serial2}")
    
    # Test stat calculation
    print("\n2. Testing stat calculation...")
    stats = card_factory._calculate_card_stats(mock_artist, "gold", "standard")
    print(f"✅ Card stats: {stats}")
    
    # Test ability generation
    print("\n3. Testing ability generation...")
    abilities = card_factory._generate_abilities(mock_artist, "gold", "standard")
    print(f"✅ Abilities: {[a['name'] for a in abilities]}")
    
    # Test rarity score
    print("\n4. Testing rarity score...")
    rarity = card_factory._calculate_rarity_score(mock_artist, "gold", "standard")
    print(f"✅ Rarity score: {rarity}")
    
    # Test power level
    print("\n5. Testing power level...")
    power = card_factory._calculate_power_level(mock_artist, "gold", stats)
    print(f"✅ Power level: {power}")

def test_pack_creation():
    """Test pack creation functionality"""
    print("\n📦 Testing Pack Creation")
    print("======================")
    
    # Test different pack types
    pack_configs = [
        {"type": "standard", "size": 5},
        {"type": "genre", "genre": "Rock", "size": 3},
        {"type": "tier", "tier": "gold", "size": 5},
        {"type": "trending", "size": 5},
        {"type": "diverse", "size": 10}
    ]
    
    for config in pack_configs:
        print(f"\n📦 Testing {config['type']} pack...")
        
        # This would require actual artists in database
        # For now, we'll test the configuration
        artists = card_factory._get_pack_artists(config)
        print(f"   Artists available: {len(artists)}")
        
        # Test card type determination
        for i in range(config['size']):
            card_type = card_factory._determine_card_type(config['type'], i, config['size'])
            print(f"   Position {i}: {card_type}")

def test_special_cards():
    """Test special card creation"""
    print("\n✨ Testing Special Cards")
    print("======================")
    
    # Mock artist for testing
    class MockArtist:
        def __init__(self):
            self.id = "12345678"
            self.name = "Test Artist"
            self.genre = "Pop"
            self.tier = "legendary"
            self.popularity = 1000000
            self.score = 50000000
            self.image_url = ""
    
    mock_artist = MockArtist()
    
    # Test special card types
    special_types = ["foil", "holographic", "promotional"]
    
    for special_type in special_types:
        print(f"\n✨ Testing {special_type} card...")
        
        if special_type == "promotional":
            card = card_factory.create_promotional_card(mock_artist, "TEST2024")
        else:
            card = card_factory.create_special_card(mock_artist, special_type)
        
        if card:
            print(f"✅ Created {special_type} card")
            print(f"   Serial: {card.serial}")
            print(f"   Power level: {card.power_level}")
            print(f"   Rarity score: {card.rarity_score}")
        else:
            print(f"⚠️  Could not create {special_type} card")

def test_integration():
    """Test integration between pool and factory"""
    print("\n🔗 Testing Integration")
    print("====================")
    
    # Get artist from pool
    artist = get_random_artist()
    
    if artist:
        print(f"🎵 Selected artist: {artist.name}")
        
        # Create card from artist
        card = create_from_artist(artist)
        
        if card:
            print(f"✅ Created card: {card.serial}")
            print(f"   Tier: {card.tier}")
            print(f"   Power level: {card.power_level}")
            print(f"   Abilities: {len(card.abilities)}")
        else:
            print("❌ Failed to create card")
    else:
        print("⚠️  No artists available for integration test")

def test_performance():
    """Test performance of pool and factory operations"""
    print("\n⚡ Testing Performance")
    print("====================")
    
    import time
    
    # Test pool performance
    start_time = time.time()
    
    for _ in range(100):
        artist = get_random_artist()
    
    pool_time = time.time() - start_time
    print(f"✅ Pool performance: 100 random selections in {pool_time:.3f}s")
    
    # Test factory performance
    start_time = time.time()
    
    # Mock artist for performance test
    class MockArtist:
        def __init__(self, i):
            self.id = f"artist_{i}"
            self.name = f"Artist {i}"
            self.genre = "Pop"
            self.tier = "gold"
            self.popularity = 100000
            self.score = 5000000
            self.image_url = ""
    
    for i in range(50):
        mock_artist = MockArtist(i)
        stats = card_factory._calculate_card_stats(mock_artist, "gold", "standard")
    
    factory_time = time.time() - start_time
    print(f"✅ Factory performance: 50 stat calculations in {factory_time:.3f}s")

def main():
    """Run all tests"""
    print("🎵 Artist Pool & Card Factory Test Suite")
    print("=======================================")
    
    try:
        test_artist_pool()
        test_card_factory()
        test_pack_creation()
        test_special_cards()
        test_integration()
        test_performance()
        
        print("\n🎉 Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
