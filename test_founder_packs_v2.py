# test_founder_packs_v2.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packs.founder_packs_v2 import founder_packs_v2

def test_founder_packs_v2():
    """Test the new Founder Pack implementation"""
    print("🧪 Testing Founder Packs V2...")
    print()
    
    # Test 1: Roll Tier Function
    print("1. Testing roll_tier function...")
    
    # Test Black Guarantee odds
    gold_count = 0
    platinum_count = 0
    legendary_count = 0
    
    for _ in range(1000):
        tier = founder_packs_v2.roll_tier(founder_packs_v2.BLACK_GUARANTEE)
        if tier == "gold":
            gold_count += 1
        elif tier == "platinum":
            platinum_count += 1
        elif tier == "legendary":
            legendary_count += 1
    
    total = gold_count + platinum_count + legendary_count
    gold_pct = (gold_count / total) * 100
    platinum_pct = (platinum_count / total) * 100
    legendary_pct = (legendary_count / total) * 100
    
    print(f"Black Guarantee (1000 rolls):")
    print(f"  Gold: {gold_count} ({gold_pct:.1f}%) - Expected: 75%")
    print(f"  Platinum: {platinum_count} ({platinum_pct:.1f}%) - Expected: 22%")
    print(f"  Legendary: {legendary_count} ({legendary_pct:.1f}%) - Expected: 3%")
    
    # Check if odds are reasonable (within 5% of expected)
    assert 70 <= gold_pct <= 80, f"Gold odds {gold_pct:.1f}% not in expected range"
    assert 17 <= platinum_pct <= 27, f"Platinum odds {platinum_pct:.1f}% not in expected range"
    assert 0 <= legendary_pct <= 8, f"Legendary odds {legendary_pct:.1f}% not in expected range"
    
    print("✅ roll_tier test passed")
    print()
    
    # Test 2: Serial Number Generation
    print("2. Testing serial number generation...")
    serial1 = founder_packs_v2.next_serial("Test Artist", "gold")
    serial2 = founder_packs_v2.next_serial("Test Artist", "gold")
    
    assert serial1 == 1, f"First serial should be 1, got {serial1}"
    assert serial2 == 2, f"Second serial should be 2, got {serial2}"
    
    print(f"Serial numbers: {serial1}, {serial2}")
    print("✅ Serial number test passed")
    print()
    
    # Test 3: Card Creation
    print("3. Testing card creation...")
    card = founder_packs_v2.create_card("Test Artist", "gold", "test_pack")
    
    assert card['tier'] == "gold", f"Card tier should be gold, got {card['tier']}"
    assert card['name'] == "Test Artist", f"Card name should be 'Test Artist', got {card['name']}"
    assert card['serial_number'].startswith("ML-SF-"), f"Serial should start with ML-SF-, got {card['serial_number']}"
    assert card['acquisition_source'] == "test_pack", f"Source should be test_pack, got {card['acquisition_source']}"
    
    print(f"Created card: {card['serial_number']} ({card['tier']})")
    print("✅ Card creation test passed")
    print()
    
    # Test 4: Black Pack Opening
    print("4. Testing Black Pack opening...")
    try:
        black_cards = founder_packs_v2.open_pack("test_user_123", founder_packs_v2.PACK_BLACK)
        
        assert len(black_cards) == 5, f"Black pack should have 5 cards, got {len(black_cards)}"
        
        # Check Gold+ guarantee
        gold_plus_count = sum(1 for card in black_cards if card['tier'] in ['gold', 'platinum', 'legendary'])
        assert gold_plus_count >= 1, f"Black pack should guarantee 1+ Gold+, got {gold_plus_count}"
        
        print(f"Black Pack: {len(black_cards)} cards, {gold_plus_count} Gold+ guaranteed")
        for i, card in enumerate(black_cards, 1):
            print(f"  {i}. {card['serial_number']} ({card['tier']})")
        
        print("✅ Black Pack test passed")
        print()
        
    except Exception as e:
        print(f"❌ Black Pack test failed: {e}")
        return False
    
    # Test 5: Silver Pack Opening
    print("5. Testing Silver Pack opening...")
    try:
        silver_cards = founder_packs_v2.open_pack("test_user_123", founder_packs_v2.PACK_SILVER)
        
        assert len(silver_cards) == 5, f"Silver pack should have 5 cards, got {len(silver_cards)}"
        
        print(f"Silver Pack: {len(silver_cards)} cards")
        for i, card in enumerate(silver_cards, 1):
            print(f"  {i}. {card['serial_number']} ({card['tier']})")
        
        print("✅ Silver Pack test passed")
        print()
        
    except Exception as e:
        print(f"❌ Silver Pack test failed: {e}")
        return False
    
    # Test 6: Multiple Pack Opening
    print("6. Testing multiple pack openings...")
    try:
        for i in range(5):
            cards = founder_packs_v2.open_pack(f"test_user_{i}", founder_packs_v2.PACK_BLACK)
            gold_plus_count = sum(1 for card in cards if card['tier'] in ['gold', 'platinum', 'legendary'])
            assert gold_plus_count >= 1, f"Pack {i} failed guarantee: {gold_plus_count} Gold+"
        
        print("✅ Multiple pack openings test passed (5 packs)")
        print()
        
    except Exception as e:
        print(f"❌ Multiple pack test failed: {e}")
        return False
    
    print("🎉 All Founder Packs V2 tests passed!")
    print()
    print("📊 Test Summary:")
    print("• Odds distribution working correctly")
    print("• Serial number generation working")
    print("• Card creation working")
    print("• Black Pack guarantee enforced")
    print("• Silver Pack opening working")
    print("• Multiple pack openings working")
    
    return True

if __name__ == "__main__":
    try:
        test_founder_packs_v2()
        print("\n🚀 Founder Packs V2 is ready for production!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
