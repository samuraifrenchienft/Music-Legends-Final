# rate_config.py
from rate_limiter import SimpleRateLimiter

# Rate limiting configuration
RATES = {
    "drop":  {"limit": 1,  "window": 1800},   # 30 min
    "grab":  {"limit": 5,  "window": 10},     # 10 sec
    "pack":  {"limit": 10, "window": 60},     # 1 min
    "trade": {"limit": 20, "window": 60}      # 1 min
}

class RateLimitManager:
    """Manages multiple rate limiters for different actions"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.limiters = {}
        
        # Initialize limiters for this user
        for action, config in RATES.items():
            key = f"{action}:{user_id}"
            self.limiters[action] = SimpleRateLimiter(
                key, 
                config["limit"], 
                config["window"]
            )
    
    def allow(self, action: str) -> bool:
        """Check if action is allowed for this user"""
        if action not in self.limiters:
            raise ValueError(f"Unknown action: {action}")
        
        return self.limiters[action].allow()
    
    def get_status(self, action: str) -> dict:
        """Get rate limit status for specific action"""
        if action not in self.limiters:
            raise ValueError(f"Unknown action: {action}")
        
        return self.limiters[action].get_status()
    
    def get_all_status(self) -> dict:
        """Get status for all rate limiters"""
        status = {}
        for action, limiter in self.limiters.items():
            status[action] = limiter.get_status()
        return status
    
    def reset(self, action: str = None):
        """Reset specific or all rate limiters"""
        if action:
            if action in self.limiters:
                self.limiters[action].reset()
        else:
            for limiter in self.limiters.values():
                limiter.reset()

# Rate limiting decorator
def rate_limit(action: str):
    """Decorator for rate limiting functions"""
    def decorator(func):
        def wrapper(user_id: int, *args, **kwargs):
            manager = RateLimitManager(user_id)
            
            if not manager.allow(action):
                status = manager.get_status(action)
                raise RateLimitExceeded(
                    f"Rate limit exceeded for {action}. "
                    f"Limit: {status['limit']}, "
                    f"Current: {status['current']}, "
                    f"Remaining: {status['remaining']}"
                )
            
            return func(user_id, *args, **kwargs)
        return wrapper
    return decorator

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass

# Test the rate limiting system
def test_rate_limiting():
    """Test the rate limiting configuration"""
    print("Testing Rate Limiting Configuration...")
    
    user_id = 12345
    manager = RateLimitManager(user_id)
    
    print(f"Configuration: {RATES}")
    print(f"Initial status: {manager.get_all_status()}")
    
    # Test pack rate limiting (10 per minute)
    print("\nTesting pack rate limiting...")
    for i in range(12):
        allowed = manager.allow("pack")
        status = manager.get_status("pack")
        print(f"Pack request {i+1}: allowed={allowed}, remaining={status['remaining']}")
    
    # Test drop rate limiting (1 per 30 minutes)
    print("\nTesting drop rate limiting...")
    allowed = manager.allow("drop")
    print(f"First drop: {allowed}")
    
    allowed = manager.allow("drop")
    print(f"Second drop: {allowed}")
    
    # Test grab rate limiting (5 per 10 seconds)
    print("\nTesting grab rate limiting...")
    for i in range(7):
        allowed = manager.allow("grab")
        status = manager.get_status("grab")
        print(f"Grab request {i+1}: allowed={allowed}, remaining={status['remaining']}")
    
    print("\nFinal status:")
    for action, status in manager.get_all_status().items():
        print(f"  {action}: {status['current']}/{status['limit']} (remaining: {status['remaining']})")
    
    print("Rate limiting test complete!")

# Test decorator
@rate_limit("pack")
def open_pack(user_id: int, pack_type: str):
    """Example function with rate limiting"""
    return f"Pack {pack_type} opened for user {user_id}"

def test_decorator():
    """Test the rate limiting decorator"""
    print("\nTesting Rate Limiting Decorator...")
    
    user_id = 12346
    
    try:
        # Should work
        result = open_pack(user_id, "black")
        print(f"Success: {result}")
        
        # Should work a few more times
        for i in range(9):
            result = open_pack(user_id, "silver")
            print(f"Success {i+1}: {result}")
        
        # Should fail
        result = open_pack(user_id, "gold")
        print(f"Unexpected success: {result}")
        
    except RateLimitExceeded as e:
        print(f"Rate limit exceeded: {e}")
    
    print("Decorator test complete!")

if __name__ == "__main__":
    test_rate_limiting()
    test_decorator()
