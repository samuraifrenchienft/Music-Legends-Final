# test_rate_limiter.py
from rate_limiter import SimpleRateLimiter

# Test the exact code you provided
KEY = "TEST-123"

# Create rate limiter: 3 requests per 5 seconds
limiter = SimpleRateLimiter(KEY, 3, 5)

# Reset to start clean
limiter.reset()

print("Testing Simple Rate Limiter...")
print(f"Initial status: {limiter.get_status()}")

# Test allowed requests
for i in range(3):
    allowed = limiter.allow()
    print(f"Request {i+1}: {allowed}")

# Test exceeded limit
exceeded = limiter.allow()
print(f"Exceeded request: {exceeded}")

print(f"Final status: {limiter.get_status()}")

# Test with different key
print("\nTesting with different key...")
limiter2 = SimpleRateLimiter("DIFFERENT-KEY", 2, 10)
limiter2.reset()

print(f"Request 1: {limiter2.allow()}")
print(f"Request 2: {limiter2.allow()}")
print(f"Request 3: {limiter2.allow()}")  # Should be False

print("\nRate limiter test complete!")
