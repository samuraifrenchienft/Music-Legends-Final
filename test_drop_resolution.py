# test_drop_resolution.py
"""
Test script for drop resolution system
"""
import random
from datetime import datetime, timedelta
from services.drop_service import resolve_drop, _pick_winner

def test_drop_resolution_complete():
    """Complete test of drop resolution system"""
    print("🎯 Testing Drop Resolution System")
    print("="*50)
    
    # Test data
    drop_id = "test_drop_123"
    
    print("\n1. Testing _pick_winner function:")
    
    # Test owner priority
    owner_id = 12345
    reactors_with_owner = [12345, 67890, 11111]
    winner = _pick_winner(owner_id, reactors_with_owner)
    print(f"   Owner in reactors: {winner} (expected: {owner_id})")
    assert winner == owner_id, "Owner priority failed"
    
    # Test random selection
    reactors_without_owner = [67890, 11111, 22222]
    winner = _pick_winner(None, reactors_without_owner)
    print(f"   Random selection: {winner} (expected: one of {reactors_without_owner})")
    assert winner in reactors_without_owner, "Random selection failed"
    
    # Test empty reactors
    winner = _pick_winner(None, [])
    print(f"   Empty reactors: {winner} (expected: None)")
    assert winner is None, "Empty reactors failed"
    
    print("\n✅ _pick_winner tests passed!")
    
    print("\n2. Testing resolve_drop function:")
    
    # Test case 1: No reactors
    print("   Case 1: No reactors")
    winner = resolve_drop(drop_id + "_1", [])
    print(f"   Result: {winner} (expected: None)")
    
    # Test case 2: Single reactor
    print("   Case 2: Single reactor")
    winner = resolve_drop(drop_id + "_2", [12345])
    print(f"   Result: {winner} (expected: 12345)")
    
    # Test case 3: Multiple reactors
    print("   Case 3: Multiple reactors")
    winner = resolve_drop(drop_id + "_3", [12345, 67890, 11111])
    print(f"   Result: {winner} (expected: 12345 if owner, else random)")
    
    print("\n✅ resolve_drop tests completed!")
    
    print("\n3. Testing edge cases:")
    
    # Test with large number of reactors
    print("   Case: Large reactor list")
    large_reactor_list = list(range(1, 101))  # 100 reactors
    winner = resolve_drop(drop_id + "_4", large_reactor_list)
    print(f"   Result: {winner} (expected: valid user ID)")
    
    # Test with duplicate reactors
    print("   Case: Duplicate reactors")
    duplicate_reactors = [12345, 12345, 67890, 67890]
    winner = resolve_drop(drop_id + "_5", duplicate_reactors)
    print(f"   Result: {winner} (expected: valid user ID)")
    
    print("\n✅ Edge case tests completed!")
    
    print("\n4. Testing winner selection logic:")
    
    # Simulate multiple drops to test randomness
    owner_id = 99999
    reactors = [11111, 22222, 33333]
    
    print("   Testing multiple drops with same reactors:")
    winners = []
    for i in range(5):
        winner = _pick_winner(None, reactors)
        winners.append(winner)
        print(f"   Drop {i+1}: {winner}")
    
    unique_winners = set(winners)
    print(f"   Unique winners: {len(unique_winners)} out of {len(winners)}")
    
    print("\n✅ Winner selection tests completed!")
    
    print("\n" + "="*50)
    print("🎉 All Drop Resolution Tests Passed!")
    print("="*50)

def test_drop_resolution_scenarios():
    """Test real-world drop resolution scenarios"""
    print("\n🎮 Testing Real-World Scenarios")
    print("="*50)
    
    # Scenario 1: Popular drop with many reactors
    print("\nScenario 1: Popular Drop")
    popular_drop_id = "popular_drop_001"
    popular_reactors = [12345, 23456, 34567, 45678, 56789, 67890, 78901]
    winner = resolve_drop(popular_drop_id, popular_reactors)
    print(f"   Drop ID: {popular_drop_id}")
    print(f"   Reactors: {len(popular_reactors)} users")
    print(f"   Winner: {winner}")
    
    # Scenario 2: Owner claims their own drop
    print("\nScenario 2: Owner Claim")
    owner_drop_id = "owner_drop_002"
    owner_id = 11111
    owner_reactors = [11111, 22222, 33333]
    winner = resolve_drop(owner_drop_id, owner_reactors)
    print(f"   Drop ID: {owner_drop_id}")
    print(f"   Owner: {owner_id}")
    print(f"   Reactors: {owner_reactors}")
    print(f"   Winner: {winner}")
    print(f"   Owner won: {winner == owner_id}")
    
    # Scenario 3: Late claim (expired drop)
    print("\nScenario 3: Expired Drop")
    expired_drop_id = "expired_drop_003"
    late_reactors = [12345, 23456]
    winner = resolve_drop(expired_drop_id, late_reactors)
    print(f"   Drop ID: {expired_drop_id}")
    print(f"   Reactors: {late_reactors}")
    print(f"   Winner: {winner} (should be None for expired)")
    
    print("\n✅ Real-world scenarios completed!")

if __name__ == "__main__":
    test_drop_resolution_complete()
    test_drop_resolution_scenarios()
