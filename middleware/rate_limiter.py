# middleware/rate_limiter.py
from rate_limiter import SimpleRateLimiter

class RateLimiter:
    """Discord-compatible rate limiter middleware"""
    
    def __init__(self, key, limit, window):
        self.key = key
        self.limit = limit
        self.window = window
        self.limiter = SimpleRateLimiter(key, limit, window)
    
    def allow(self):
        """Check if request is allowed"""
        return self.limiter.allow()
    
    def get_status(self):
        """Get current rate limit status"""
        return self.limiter.get_status()
    
    def reset(self):
        """Reset the rate limiter"""
        self.limiter.reset()
