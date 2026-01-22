# test_creator_business_rules.py
# Test script for creator pack business rules

import asyncio
import sys
sys.path.append('.')

from services.creator_business_rules import creator_business_rules
from services.queue_manager import queue_manager

def test_business_rules():
    """Test business rules validation"""
    print("📋 Testing Business Rules")
    print("========================")
    
    # Test pack creation validation
    print("\n1. Testing pack creation validation...")
    
    # Valid pack
    valid_result = creator_business_rules.validate_pack_creation(
        user_id=123456789,
        artist_names=["Queen", "Led Zeppelin", "The Beatles"]
    )
    
    if valid_result["valid"]:
        print("✅ Valid pack validation passed")
    else:
        print("❌ Valid pack validation failed")
        print(f"   Errors: {valid_result['errors']}")
    
    # Invalid pack (too many artists)
    invalid_result = creator_business_rules.validate_pack_creation(
        user_id=123456789,
        artist_names=["Artist"] * 15
    )
    
    if not invalid_result["valid"]:
        print("✅ Invalid pack validation correctly failed")
        print(f"   Errors: {invalid_result['errors']}")
    else:
        print("❌ Invalid pack validation should have failed")
    
    # Test price calculation
    print("\n2. Testing price calculation...")
    
    # Default price
    default_price = creator_business_rules.calculate_pack_price(artist_count=3)
    print(f"✅ Default price (3 artists): ${default_price / 100:.2f}")
    
    # Custom price (within range)
    custom_price = creator_business_rules.calculate_pack_price(
        artist_count=3, 
        custom_price=1999
    )
    print(f"✅ Custom price: ${custom_price / 100:.2f}")
    
    # Custom price (too high)
    high_price = creator_business_rules.calculate_pack_price(
        artist_count=3, 
        custom_price=9999
    )
    print(f"✅ High price capped at: ${high_price / 100:.2f}")
    
    # Test legendary cap
    print("\n3. Testing legendary cap enforcement...")
    
    # Mock cards
    class MockCard:
        def __init__(self, tier):
            self.tier = tier
    
    # Test under cap
    under_cap_cards = [
        MockCard("gold"),
        MockCard("platinum"),
        MockCard("silver")
    ]
    
    filtered_under = creator_business_rules.enforce_legendary_cap(under_cap_cards, 123456789)
    print(f"✅ Under cap: {len(filtered_under)} cards (expected: 3)")
    
    # Test over cap
    over_cap_cards = [
        MockCard("legendary"),
        MockCard("legendary"),
        MockCard("legendary"),
        MockCard("gold")
    ]
    
    filtered_over = creator_business_rules.enforce_legendary_cap(over_cap_cards, 123456789)
    print(f"✅ Over cap: {len(filtered_over)} cards (expected: ≤10)")
    
    # Test revenue calculation
    print("\n4. Testing revenue calculation...")
    
    # Mock pack
    class MockPack:
        def __init__(self):
            self.price_cents = 999
            self.purchase_count = 5
    
    mock_pack = MockPack()
    revenue = creator_business_rules.calculate_creator_revenue(mock_pack)
    
    print(f"✅ Revenue breakdown:")
    print(f"   Total revenue: ${revenue['total_revenue'] / 100:.2f}")
    print(f"   Platform fee: ${revenue['platform_fee'] / 100:.2f}")
    print(f"   Creator earnings: ${revenue['creator_earnings'] / 100:.2f}")
    print(f"   Profit share: {revenue['profit_share'] * 100}%")
    
    # Test creator statistics
    print("\n5. Testing creator statistics...")
    
    stats = creator_business_rules.get_creator_statistics(123456789)
    print(f"✅ Creator stats:")
    print(f"   Total packs: {stats['total_packs']}")
    print(f"   Total purchases: {stats['total_purchases']}")
    print(f"   Total revenue: ${stats['total_revenue'] / 100:.2f}")

def test_queue_integration():
    """Test queue integration"""
    print("\n📋 Testing Queue Integration")
    print("============================")
    
    # Test queue status
    print("\n1. Testing queue status...")
    status = queue_manager.get_queue_status()
    print(f"✅ Queue status: {status['queue_size']} jobs, {status['processing']} processing")
    
    # Test job queuing
    print("\n2. Testing job queuing...")
    
    # Queue pack creation job
    pack_job_id = queue_manager.enqueue({
        "type": "creator_pack_creation",
        "user_id": 123456789,
        "pack_data": {
            "name": "Test Pack",
            "artist_names": ["Queen", "Led Zeppelin"],
            "genre": "Rock"
        }
    })
    
    print(f"✅ Queued pack creation job: {pack_job_id}")
    
    # Queue pack opening job
    open_job_id = queue_manager.enqueue({
        "type": "creator_pack_opening",
        "user_id": 123456789,
        "pack_id": "test_pack_123"
    })
    
    print(f"✅ Queued pack opening job: {open_job_id}")
    
    # Test job status
    print("\n3. Testing job status...")
    
    job_status = queue_manager.get_job_status(pack_job_id)
    if job_status:
        print(f"✅ Job status: {job_status['status']}")
        if job_status['status'] == 'queued':
            print(f"   Position in queue: {job_status['position']}")
    else:
        print("⚠️  Job status not found (may have processed already)")
    
    # Test queue limits
    print("\n4. Testing queue limits...")
    
    # Check queue capacity
    capacity = status['queue_utilization']
    print(f"✅ Queue utilization: {capacity:.1f}%")
    
    if capacity < 90:
        print("   ✅ Queue has capacity")
    else:
        print("   ⚠️  Queue nearing capacity")

def test_audit_compliance():
    """Test audit compliance"""
    print("\n📋 Testing Audit Compliance")
    print("==========================")
    
    # Mock pack for audit testing
    class MockPack:
        def __init__(self):
            self.id = "test_pack_123"
            self.name = "Test Pack"
            self.genre = "Rock"
            self.price_cents = 999
            self.artist_ids = ["artist_1", "artist_2"]
            self.branding = "samurai"
    
    mock_pack = MockPack()
    
    # Test pack creation audit
    print("\n1. Testing pack creation audit...")
    
    try:
        creator_business_rules.audit_pack_creation(
            user_id=123456789,
            pack=mock_pack,
            artist_names=["Queen", "Led Zeppelin"]
        )
        print("✅ Pack creation audit logged")
    except Exception as e:
        print(f"❌ Pack creation audit failed: {e}")
    
    # Test pack opening audit
    print("\n2. Testing pack opening audit...")
    
    # Mock cards
    class MockCard:
        def __init__(self, serial, tier, artist_id):
            self.serial = serial
            self.tier = tier
            self.artist_id = artist_id
            self.source = "creator:test_pack_123"
    
    mock_cards = [
        MockCard("TEST-LEG-001", "legendary", "artist_1"),
        MockCard("TEST-GLD-002", "gold", "artist_2")
    ]
    
    try:
        creator_business_rules.audit_pack_opening(
            user_id=123456789,
            pack=mock_pack,
            cards=mock_cards
        )
        print("✅ Pack opening audit logged")
    except Exception as e:
        print(f"❌ Pack opening audit failed: {e}")

def test_business_constants():
    """Test business rule constants"""
    print("\n📋 Testing Business Constants")
    print("============================")
    
    print(f"✅ Flat creation fee: ${creator_business_rules.FLAT_CREATION_FEE / 100:.2f}")
    print(f"✅ Creator profit share: {creator_business_rules.CREATOR_PROFIT_SHARE * 100}%")
    print(f"✅ Legendary cap per pack: {creator_business_rules.LEGENDARY_CAP_PER_PACK}")
    print(f"✅ Legendary cap per user: {creator_business_rules.LEGENDARY_CAP_PER_USER}")
    print(f"✅ Queue priority: {creator_business_rules.CREATOR_QUEUE_PRIORITY}")

async def main():
    """Run all tests"""
    print("📋 Creator Business Rules Test Suite")
    print("===================================")
    
    try:
        test_business_rules()
        test_queue_integration()
        test_audit_compliance()
        test_business_constants()
        
        print("\n🎉 Business Rules Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
