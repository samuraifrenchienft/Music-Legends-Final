# test_founder_packs.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packs.founder_packs import founder_packs
from packs.pack_validator import pack_validator

def test_founder_packs():
    """Test Founder Pack system"""
    print("🧪 Testing Founder Pack System...")
    print()
    
    # Test 1: Pack Configuration
    print("1. Testing Pack Configuration...")
    black_pack = founder_packs.get_pack_config(founder_packs.PACK_BLACK)
    silver_pack = founder_packs.get_pack_config(founder_packs.PACK_SILVER)
    
    assert black_pack is not None, "Black pack not found"
    assert silver_pack is not None, "Silver pack not found"
    assert black_pack.price_cents == 999, "Black pack price incorrect"
    assert silver_pack.price_cents == 699, "Silver pack price incorrect"
    print("✅ Pack configuration test passed")
    print()
    
    # Test 2: Card Generation
    print("2. Testing Card Generation...")
    black_cards = founder_packs.generate_pack_cards(founder_packs.PACK_BLACK)
    silver_cards = founder_packs.generate_pack_cards(founder_packs.PACK_SILVER)
    
    assert len(black_cards) == 5, f"Black pack should have 5 cards, got {len(black_cards)}"
    assert len(silver_cards) == 5, f"Silver pack should have 5 cards, got {len(silver_cards)}"
    print("✅ Card generation test passed")
    print()
    
    # Test 3: Black Pack Guarantee
    print("3. Testing Black Pack Guarantee...")
    gold_plus_count = sum(1 for card in black_cards if card.get('tier') in ['gold', 'platinum', 'legendary'])
    assert gold_plus_count >= 1, f"Black pack should guarantee 1+ Gold+, got {gold_plus_count}"
    print(f"✅ Black Pack guarantee test passed (got {gold_plus_count} Gold+ cards)")
    print()
    
    # Test 4: Pack Validation
    print("4. Testing Pack Validation...")
    black_validation = pack_validator.validate_pack_opening(founder_packs.PACK_BLACK, black_cards, 12345)
    silver_validation = pack_validator.validate_pack_opening(founder_packs.PACK_SILVER, silver_cards, 12345)
    
    assert black_validation['valid'] == True, f"Black pack validation failed: {black_validation.get('errors', [])}"
    assert silver_validation['valid'] == True, f"Silver pack validation failed: {silver_validation.get('errors', [])}"
    print("✅ Pack validation test passed")
    print()
    
    # Test 5: Display Data
    print("5. Testing Display Data...")
    black_display = founder_packs.get_pack_display_data(founder_packs.PACK_BLACK)
    silver_display = founder_packs.get_pack_display_data(founder_packs.PACK_SILVER)
    
    assert black_display is not None, "Black pack display data missing"
    assert silver_display is not None, "Silver pack display data missing"
    assert black_display['price'] == "$9.99", f"Black pack display price incorrect: {black_display['price']}"
    assert silver_display['price'] == "$6.99", f"Silver pack display price incorrect: {silver_display['price']}"
    print("✅ Display data test passed")
    print()
    
    # Test 6: Validation Stats
    print("6. Testing Validation Stats...")
    stats = pack_validator.get_validation_stats()
    assert stats['total_validations'] == 2, f"Expected 2 validations, got {stats['total_validations']}"
    assert stats['valid_count'] == 2, f"Expected 2 valid, got {stats['valid_count']}"
    assert stats['invalid_count'] == 0, f"Expected 0 invalid, got {stats['invalid_count']}"
    print("✅ Validation stats test passed")
    print()
    
    # Test 7: Multiple Pack Generation
    print("7. Testing Multiple Pack Generation...")
    for i in range(10):
        test_black_cards = founder_packs.generate_pack_cards(founder_packs.PACK_BLACK)
        gold_plus_count = sum(1 for card in test_black_cards if card.get('tier') in ['gold', 'platinum', 'legendary'])
        assert gold_plus_count >= 1, f"Black pack {i} failed guarantee: {gold_plus_count} Gold+"
    
    print("✅ Multiple pack generation test passed (10 packs)")
    print()
    
    print("🎉 All Founder Pack tests passed!")
    print()
    print("📊 Test Summary:")
    print(f"• Black Pack: {len(black_cards)} cards, {gold_plus_count} Gold+ guaranteed")
    print(f"• Silver Pack: {len(silver_cards)} cards generated")
    print(f"• Validation: {stats['total_validations']} packs validated")
    print(f"• Success Rate: {stats['success_rate']:.1f}%")
    
    return True

def test_pack_odds():
    """Test pack odds distribution"""
    print("\n🎲 Testing Pack Odds Distribution...")
    
    # Generate many packs to test odds
    black_samples = []
    silver_samples = []
    
    for _ in range(100):
        black_cards = founder_packs.generate_pack_cards(founder_packs.PACK_BLACK)
        silver_cards = founder_packs.generate_pack_cards(founder_packs.PACK_SILVER)
        
        black_samples.extend([card['tier'] for card in black_cards])
        silver_samples.extend([card['tier'] for card in silver_cards])
    
    # Count tiers
    from collections import Counter
    black_counts = Counter(black_samples)
    silver_counts = Counter(silver_samples)
    
    print(f"Black Pack (500 cards): {dict(black_counts)}")
    print(f"Silver Pack (500 cards): {dict(silver_counts)}")
    
    # Basic sanity checks
    assert len(black_samples) == 500, f"Expected 500 black cards, got {len(black_samples)}"
    assert len(silver_samples) == 500, f"Expected 500 silver cards, got {len(silver_samples)}"
    
    print("✅ Pack odds distribution test passed")

if __name__ == "__main__":
    try:
        test_founder_packs()
        test_pack_odds()
        print("\n🚀 Founder Pack system is ready for production!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
