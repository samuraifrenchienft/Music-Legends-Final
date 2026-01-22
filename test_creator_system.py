# test_creator_system.py
# Test script for creator pack system

import asyncio
import sys
sys.path.append('.')

from services.creator_service import creator_service, create_creator_pack

async def test_pack_creation():
    """Test creator pack creation"""
    print("🎵 Testing Creator Pack Creation")
    print("================================")
    
    # Test pack creation
    pack = await creator_service.create_creator_pack(
        user_id=123456789,
        name="Test Rock Pack",
        artist_names=["Queen", "Led Zeppelin", "The Beatles"],
        genre="Rock",
        description="A test pack with classic rock artists",
        price_cents=1499
    )
    
    if pack:
        print(f"✅ Created pack: {pack.name}")
        print(f"   ID: {pack.id}")
        print(f"   Owner: {pack.owner_id}")
        print(f"   Artists: {len(pack.artist_ids)}")
        print(f"   Genre: {pack.genre}")
        print(f"   Price: ${pack.price_cents / 100:.2f}")
        print(f"   Status: {pack.status}")
    else:
        print("❌ Failed to create pack")

def test_pack_retrieval():
    """Test pack retrieval functions"""
    print("\n📦 Testing Pack Retrieval")
    print("========================")
    
    # Test user packs
    print("\n1. Testing get_user_packs()...")
    user_packs = creator_service.get_user_packs(123456789)
    print(f"✅ Found {len(user_packs)} packs for user 123456789")
    
    for pack in user_packs:
        print(f"   {pack.name} - {pack.genre} (${pack.price_cents / 100:.2f})")
    
    # Test featured packs
    print("\n2. Testing get_featured_packs()...")
    featured = creator_service.get_featured_packs(5)
    print(f"✅ Found {len(featured)} featured packs")
    
    # Test genre packs
    print("\n3. Testing get_packs_by_genre()...")
    rock_packs = creator_service.get_packs_by_genre("Rock", 3)
    print(f"✅ Found {len(rock_packs)} rock packs")
    
    # Test search
    print("\n4. Testing search_packs()...")
    search_results = creator_service.search_packs("test", 3)
    print(f"✅ Found {len(search_results)} packs matching 'test'")

def test_pack_details():
    """Test pack details function"""
    print("\n🔍 Testing Pack Details")
    print("=======================")
    
    # Get a pack to test
    user_packs = creator_service.get_user_packs(123456789)
    
    if user_packs:
        pack = user_packs[0]
        print(f"\n📦 Getting details for: {pack.name}")
        
        details = creator_service.get_pack_details(str(pack.id))
        
        if details:
            print(f"✅ Pack details retrieved:")
            print(f"   Name: {details['name']}")
            print(f"   Genre: {details['genre']}")
            print(f"   Artists: {len(details['artists'])}")
            print(f"   Price: ${details['price_cents'] / 100:.2f}")
            print(f"   Purchases: {details['purchase_count']}")
            
            # Show artist details
            for artist in details['artists'][:3]:
                print(f"      🎵 {artist['name']} ({artist['tier']})")
        else:
            print("❌ Failed to get pack details")
    else:
        print("⚠️  No packs available for testing")

def test_pack_management():
    """Test pack management functions"""
    print("\n⚙️ Testing Pack Management")
    print("=========================")
    
    # Get a pack to test
    user_packs = creator_service.get_user_packs(123456789)
    
    if user_packs:
        pack = user_packs[0]
        print(f"\n📦 Testing management for: {pack.name}")
        
        # Test pack update
        print("\n1. Testing pack update...")
        success = creator_service.update_pack(
            str(pack.id), 
            pack.owner_id,
            description="Updated description for testing"
        )
        
        if success:
            print("✅ Pack updated successfully")
        else:
            print("❌ Failed to update pack")
        
        # Test pack rating
        print("\n2. Testing pack rating...")
        rating_success = creator_service.rate_pack(str(pack.id), 5)
        
        if rating_success:
            print("✅ Pack rated successfully")
        else:
            print("❌ Failed to rate pack")
        
        # Test featuring
        print("\n3. Testing pack featuring...")
        feature_success = creator_service.feature_pack(str(pack.id), True)
        
        if feature_success:
            print("✅ Pack featured successfully")
        else:
            print("❌ Failed to feature pack")
    else:
        print("⚠️  No packs available for testing")

def test_pack_purchase():
    """Test pack purchase functionality"""
    print("\n🛒 Testing Pack Purchase")
    print("=======================")
    
    # Get a pack to test
    user_packs = creator_service.get_user_packs(123456789)
    
    if user_packs:
        pack = user_packs[0]
        print(f"\n📦 Testing purchase for: {pack.name}")
        
        # Mock card creation for testing
        class MockCard:
            def __init__(self, artist):
                self.artist_id = artist.id
                self.artist_name = artist.name
                self.tier = artist.tier
        
        # Temporarily replace create_from_artist for testing
        import services.creator_service
        original_create = None
        
        def mock_create_from_artist(artist, source="test"):
            return MockCard(artist)
        
        try:
            # Test purchase
            cards = creator_service.purchase_pack(str(pack.id))
            
            if cards:
                print(f"✅ Pack purchased successfully")
                print(f"   Generated {len(cards)} cards:")
                for card in cards:
                    print(f"      🎵 {card.artist_name} ({card.tier})")
            else:
                print("❌ Failed to purchase pack")
                
        except Exception as e:
            print(f"❌ Error during purchase test: {e}")
    else:
        print("⚠️  No packs available for testing")

def test_statistics():
    """Test statistics function"""
    print("\n📊 Testing Statistics")
    print("====================")
    
    stats = creator_service.get_pack_statistics()
    
    print(f"✅ Statistics retrieved:")
    print(f"   Total packs: {stats['total_packs']}")
    print(f"   Active packs: {stats['active_packs']}")
    print(f"   Total purchases: {stats['total_purchases']}")
    print(f"   Average price: ${stats['average_price'] / 100:.2f}")
    
    if stats['by_genre']:
        print(f"   By genre: {stats['by_genre']}")
    
    if stats['by_branding']:
        print(f"   By branding: {stats['by_branding']}")

async def main():
    """Run all tests"""
    print("🎵 Creator Pack System Test Suite")
    print("================================")
    
    try:
        await test_pack_creation()
        test_pack_retrieval()
        test_pack_details()
        test_pack_management()
        test_pack_purchase()
        test_statistics()
        
        print("\n🎉 Creator Pack System Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
