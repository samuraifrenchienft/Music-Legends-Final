# tests/check_rate.py
from middleware.rate_limiter import RateLimiter
import time

def test_basic_rate_limiting():
    """Test basic rate limiting functionality"""
    print("=== Basic Rate Limiting Test ===")
    
    # Test: 3 requests per 5 seconds
    lim = RateLimiter("test:user1", 3, 5)
    
    results = [lim.allow() for _ in range(5)]
    print(f"Results: {results}")
    print(f"Expected: [True, True, True, False, False]")
    
    if results == [True, True, True, False, False]:
        print("✅ PASS: Basic rate limiting works correctly")
    else:
        print("❌ FAIL: Basic rate limiting failed")
    
    return results == [True, True, True, False, False]

def test_drop_rate_limiting():
    """Test drop rate limiting (1 per 30 minutes)"""
    print("\n=== Drop Rate Limiting Test ===")
    
    # Test: 1 drop per 30 minutes (use 5 seconds for testing)
    lim = RateLimiter("test:drop", 1, 5)
    
    # First request should work
    first = lim.allow()
    print(f"First drop: {first}")
    
    # Second request should fail
    second = lim.allow()
    print(f"Second drop: {second}")
    
    if first and not second:
        print("✅ PASS: Drop blocked after 1 in window")
    else:
        print("❌ FAIL: Drop rate limiting failed")
    
    return first and not second

def test_pack_rate_limiting():
    """Test pack rate limiting (10 per minute)"""
    print("\n=== Pack Rate Limiting Test ===")
    
    # Test: 10 packs per minute (use 2 seconds for testing)
    lim = RateLimiter("test:pack", 10, 2)
    
    # Should allow 10 requests
    allowed_count = 0
    for i in range(12):
        if lim.allow():
            allowed_count += 1
        else:
            break
    
    print(f"Allowed requests: {allowed_count}")
    print(f"Expected: 10")
    
    if allowed_count == 10:
        print("✅ PASS: Pack blocked after 10 per minute")
    else:
        print("❌ FAIL: Pack rate limiting failed")
    
    return allowed_count == 10

def test_spam_protection():
    """Test that spam cannot crash the bot"""
    print("\n=== Spam Protection Test ===")
    
    try:
        # Create multiple limiters
        limiters = []
        for i in range(100):
            lim = RateLimiter(f"test:spam:{i}", 5, 10)
            limiters.append(lim)
        
        # Rapid fire requests
        crash_detected = False
        for lim in limiters:
            try:
                # Multiple rapid requests
                for _ in range(20):
                    lim.allow()
            except Exception as e:
                print(f"❌ CRASH DETECTED: {e}")
                crash_detected = True
                break
        
        if not crash_detected:
            print("✅ PASS: Spam cannot crash bot")
        else:
            print("❌ FAIL: Bot crashed under spam")
        
        return not crash_detected
        
    except Exception as e:
        print(f"❌ FAIL: Exception during spam test: {e}")
        return False

def test_window_reset():
    """Test that limits reset after window"""
    print("\n=== Window Reset Test ===")
    
    # Test: 2 requests per 3 seconds
    lim = RateLimiter("test:reset", 2, 3)
    
    # Use up the limit
    first = lim.allow()
    second = lim.allow()
    third = lim.allow()
    
    print(f"Before wait: {first}, {second}, {third}")
    
    # Wait for window to reset
    print("Waiting 4 seconds for window to reset...")
    time.sleep(4)
    
    # Should work again
    fourth = lim.allow()
    print(f"After wait: {fourth}")
    
    if first and second and not third and fourth:
        print("✅ PASS: Limits reset after window")
    else:
        print("❌ FAIL: Window reset failed")
    
    return first and second and not third and fourth

def test_concurrent_users():
    """Test rate limiting with multiple users"""
    print("\n=== Concurrent Users Test ===")
    
    # Create limiters for different users
    lim1 = RateLimiter("test:user1", 2, 5)
    lim2 = RateLimiter("test:user2", 2, 5)
    
    # Both users should be able to make requests
    user1_first = lim1.allow()
    user2_first = lim2.allow()
    
    user1_second = lim1.allow()
    user2_second = lim2.allow()
    
    # Both should be blocked now
    user1_third = lim1.allow()
    user2_third = lim2.allow()
    
    print(f"User1: {user1_first}, {user1_second}, {user1_third}")
    print(f"User2: {user2_first}, {user2_second}, {user2_third}")
    
    expected = [True, True, False]
    if ([user1_first, user1_second, user1_third] == expected and 
        [user2_first, user2_second, user2_third] == expected):
        print("✅ PASS: Concurrent users rate limited independently")
    else:
        print("❌ FAIL: Concurrent users not rate limited independently")
    
    return ([user1_first, user1_second, user1_third] == expected and 
            [user2_first, user2_second, user2_third] == expected)

def run_all_tests():
    """Run all rate limiting tests"""
    print("🚀 Running Rate Limiting Tests...\n")
    
    tests = [
        ("Basic Rate Limiting", test_basic_rate_limiting),
        ("Drop Rate Limiting", test_drop_rate_limiting),
        ("Pack Rate Limiting", test_pack_rate_limiting),
        ("Spam Protection", test_spam_protection),
        ("Window Reset", test_window_reset),
        ("Concurrent Users", test_concurrent_users),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Rate limiting is working correctly!")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()
