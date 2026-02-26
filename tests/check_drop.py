# tests/check_drop.py
"""
Verification tests for drop system
"""
import pytest
from services.drop_service import _pick_winner
from services.drop_create import create_drop, create_unclaimed_drop, create_owner_drop
from services.drop_create import MockCard

def test_pick_winner():
    """Test the _pick_winner function with all scenarios"""
    print("Testing _pick_winner function...")
    
    # Test 1: Owner priority
    print("  Test 1: Owner priority")
    result = _pick_winner(1, [1, 2, 3])
    print(f"    _pick_winner(1, [1,2,3]) = {result}")
    assert result == 1, f"Expected 1, got {result}"
    print("    ✅ PASS")
    
    # Test 2: RNG fallback
    print("  Test 2: RNG fallback")
    result = _pick_winner(1, [2, 3])
    print(f"    _pick_winner(1, [2,3]) = {result}")
    assert result in [2, 3], f"Expected 2 or 3, got {result}"
    print("    ✅ PASS")
    
    # Test 3: No reactors
    print("  Test 3: No reactors")
    result = _pick_winner(1, [])
    print(f"    _pick_winner(1, []) = {result}")
    assert result is None, f"Expected None, got {result}"
    print("    ✅ PASS")
    
    # Test 4: Owner not in reactors
    print("  Test 4: Owner not in reactors")
    result = _pick_winner(999, [1, 2, 3])
    print(f"    _pick_winner(999, [1,2,3]) = {result}")
    assert result in [1, 2, 3], f"Expected 1, 2, or 3, got {result}"
    print("    ✅ PASS")
    
    # Test 5: Single reactor (not owner)
    print("  Test 5: Single reactor (not owner)")
    result = _pick_winner(999, [123])
    print(f"    _pick_winner(999, [123]) = {result}")
    assert result == 123, f"Expected 123, got {result}"
    print("    ✅ PASS")
    
    # Test 6: Single reactor (is owner)
    print("  Test 6: Single reactor (is owner)")
    result = _pick_winner(123, [123])
    print(f"    _pick_winner(123, [123]) = {result}")
    assert result == 123, f"Expected 123, got {result}"
    print("    ✅ PASS")
    
    print("✅ All _pick_winner tests passed!")

def test_drop_creation():
    """Test drop creation functionality"""
    print("Testing drop creation...")
    
    # Create mock cards
    cards = [MockCard("card1"), MockCard("card2"), MockCard("card3")]
    
    # Test unclaimed drop
    print("  Test 1: Unclaimed drop")
    unclaimed = create_unclaimed_drop(cards)
    print(f"    Owner: {unclaimed.owner_id}")
    print(f"    Card IDs: {unclaimed.card_ids}")
    assert unclaimed.owner_id is None, f"Expected None owner, got {unclaimed.owner_id}"
    assert unclaimed.card_ids == ["card1", "card2", "card3"], f"Expected card IDs, got {unclaimed.card_ids}"
    print("    ✅ PASS")
    
    # Test owner drop
    print("  Test 2: Owner drop")
    owner_drop = create_owner_drop(12345, cards)
    print(f"    Owner: {owner_drop.owner_id}")
    print(f"    Card IDs: {owner_drop.card_ids}")
    assert owner_drop.owner_id == 12345, f"Expected 12345 owner, got {owner_drop.owner_id}"
    assert owner_drop.card_ids == ["card1", "card2", "card3"], f"Expected card IDs, got {owner_drop.card_ids}"
    print("    ✅ PASS")
    
    print("✅ All drop creation tests passed!")

def test_drop_edge_cases():
    """Test edge cases for drop system"""
    print("Testing drop edge cases...")
    
    # Test empty card list
    print("  Test 1: Empty card list")
    empty_cards = []
    drop = create_unclaimed_drop(empty_cards)
    print(f"    Card IDs: {drop.card_ids}")
    assert drop.card_ids == [], f"Expected empty list, got {drop.card_ids}"
    print("    ✅ PASS")
    
    # Test single card
    print("  Test 2: Single card")
    single_card = [MockCard("single_card")]
    drop = create_unclaimed_drop(single_card)
    print(f"    Card IDs: {drop.card_ids}")
    assert drop.card_ids == ["single_card"], f"Expected ['single_card'], got {drop.card_ids}"
    print("    ✅ PASS")
    
    print("✅ All edge case tests passed!")

def run_all_verification_tests():
    """Run all verification tests"""
    print("🚀 Running Drop System Verification Tests")
    print("=" * 50)
    
    try:
        test_pick_winner()
        print()
        test_drop_creation()
        print()
        test_drop_edge_cases()
        
        print("\n" + "=" * 50)
        print("🎉 ALL VERIFICATION TESTS PASSED!")
        print("=" * 50)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        return False

# PyTest compatibility
def test_owner_priority():
    """PyTest: Owner priority"""
    assert _pick_winner(1, [1, 2, 3]) == 1

def test_rng_fallback():
    """PyTest: RNG fallback"""
    assert _pick_winner(1, [2, 3]) in [2, 3]

def test_no_reactors():
    """PyTest: No reactors"""
    assert _pick_winner(1, []) is None

def test_owner_not_in_reactors():
    """PyTest: Owner not in reactors"""
    assert _pick_winner(999, [1, 2, 3]) in [1, 2, 3]

def test_single_reactor_not_owner():
    """PyTest: Single reactor not owner"""
    assert _pick_winner(999, [123]) == 123

def test_single_reactor_is_owner():
    """PyTest: Single reactor is owner"""
    assert _pick_winner(123, [123]) == 123

if __name__ == "__main__":
    run_all_verification_tests()
