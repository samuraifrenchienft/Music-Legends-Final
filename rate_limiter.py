# rate_limiter.py
import redis
import time
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import settings

@dataclass
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    penalty_multiplier: float = 2.0
    max_penalty_minutes: int = 60

class RateLimiter:
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = settings.REDIS_URL
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # Define rate limit rules
        self.rules = {
            # Command limits
            'drop': RateLimitRule('drop', 1, 1800),  # 1 drop per 30 minutes
            'grab': RateLimitRule('grab', 5, 10),      # 5 grabs per 10 seconds
            'pack_open': RateLimitRule('pack_open', 10, 60),  # 10 packs per minute
            'trade': RateLimitRule('trade', 20, 60),     # 20 trades per minute
            'burn': RateLimitRule('burn', 5, 60),        # 5 burns per minute
            
            # Global limits
            'global_commands': RateLimitRule('global_commands', 100, 60),  # 100 commands per minute per user
            'server_commands': RateLimitRule('server_commands', 1000, 60),  # 1000 commands per minute per server
        }
        
        # Penalty tracking
        self.penalties = {}
        
    async def check_limit(self, identifier: str, action: str, amount: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Check if action is allowed for identifier"""
        rule = self.rules.get(action)
        if not rule:
            return True, {'allowed': True, 'reason': 'No rule for action'}
        
        # Check for active penalty
        penalty_end = await self._get_penalty_end(identifier, action)
        if penalty_end and time.time() < penalty_end:
            return False, {
                'allowed': False,
                'reason': 'Penalty active',
                'penalty_end': penalty_end
            }
        
        # Get current usage
        key = f"rate_limit:{identifier}:{action}"
        current_time = time.time()
        window_start = current_time - rule.window_seconds
        
        # Clean old entries
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Get current count
        current_count = await self.redis.zcard(key)
        
        # Check if limit exceeded
        if current_count + amount > rule.limit:
            # Apply penalty
            await self._apply_penalty(identifier, action, rule)
            
            return False, {
                'allowed': False,
                'reason': f'Rate limit exceeded: {current_count + amount}/{rule.limit}',
                'limit': rule.limit,
                'window': rule.window_seconds,
                'retry_after': rule.window_seconds
            }
        
        # Record usage
        await self.redis.zadd(key, {str(uuid.uuid4()): current_time})
        await self.redis.expire(key, rule.window_seconds + 60)  # Keep a bit longer for cleanup
        
        return True, {
            'allowed': True,
            'remaining': rule.limit - (current_count + amount),
            'reset_time': current_time + rule.window_seconds
        }
    
    async def _get_penalty_end(self, identifier: str, action: str) -> Optional[float]:
        """Get penalty end time for identifier and action"""
        key = f"penalty:{identifier}:{action}"
        penalty_end = await self.redis.get(key)
        
        if penalty_end:
            return float(penalty_end)
        
        return None
    
    async def _apply_penalty(self, identifier: str, action: str, rule: RateLimitRule):
        """Apply penalty to identifier"""
        # Calculate penalty duration
        base_penalty = rule.window_seconds
        penalty_duration = min(
            base_penalty * rule.penalty_multiplier,
            rule.max_penalty_minutes * 60
        )
        
        penalty_end = time.time() + penalty_duration
        
        # Store penalty
        key = f"penalty:{identifier}:{action}"
        await self.redis.setex(key, penalty_duration, str(penalty_end))
        
        # Log penalty
        logging.warning(f"Applied penalty to {identifier} for {action}: {penalty_duration}s")
    
    async def clear_penalty(self, identifier: str, action: str):
        """Clear penalty for identifier and action"""
        key = f"penalty:{identifier}:{action}"
        await self.redis.delete(key)
        logging.info(f"Cleared penalty for {identifier} for {action}")
    
    async def get_usage_stats(self, identifier: str, action: str) -> Dict[str, Any]:
        """Get usage statistics for identifier and action"""
        rule = self.rules.get(action)
        if not rule:
            return {'error': 'No rule for action'}
        
        key = f"rate_limit:{identifier}:{action}"
        current_time = time.time()
        window_start = current_time - rule.window_seconds
        
        # Get usage in current window
        usage = await self.redis.zrangebyscore(key, window_start, current_time)
        current_count = len(usage)
        
        # Get penalty info
        penalty_end = await self._get_penalty_end(identifier, action)
        
        return {
            'action': action,
            'identifier': identifier,
            'limit': rule.limit,
            'window_seconds': rule.window_seconds,
            'current_usage': current_count,
            'remaining': max(0, rule.limit - current_count),
            'penalty_active': penalty_end is not None,
            'penalty_end': penalty_end,
            'reset_time': current_time + rule.window_seconds
        }
    
    async def get_all_stats(self, identifier: str) -> Dict[str, Any]:
        """Get all usage statistics for identifier"""
        stats = {}
        
        for action in self.rules.keys():
            stats[action] = await self.get_usage_stats(identifier, action)
        
        return stats
    
    def add_rule(self, rule: RateLimitRule):
        """Add a new rate limit rule"""
        self.rules[rule.name] = rule
        logging.info(f"Added rate limit rule: {rule.name}")
    
    def remove_rule(self, name: str):
        """Remove a rate limit rule"""
        if name in self.rules:
            del self.rules[name]
            logging.info(f"Removed rate limit rule: {name}")
    
    def update_rule(self, name: str, **kwargs):
        """Update an existing rate limit rule"""
        if name in self.rules:
            rule = self.rules[name]
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            logging.info(f"Updated rate limit rule: {name}")

class RateLimitMiddleware:
    """Middleware for Discord.py commands"""
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def check_command(self, user_id: int, command_name: str, server_id: int = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if command is allowed"""
        # Check user-specific limit
        user_key = f"user_{user_id}"
        user_allowed, user_result = await self.rate_limiter.check_limit(user_key, command_name)
        
        if not user_allowed:
            return False, user_result
        
        # Check server-specific limit if server_id provided
        if server_id:
            server_key = f"server_{server_id}"
            server_allowed, server_result = await self.rate_limiter.check_limit(server_key, 'server_commands', 1)
            
            if not server_allowed:
                return False, server_result
        
        # Check global command limit
        global_allowed, global_result = await self.rate_limiter.check_limit(user_key, 'global_commands', 1)
        
        if not global_allowed:
            return False, global_result
        
        return True, {'allowed': True}
    
    async def create_error_embed(self, result: Dict[str, Any]) -> 'discord.Embed':
        """Create error embed for rate limit violation"""
        from discord import Embed, Color
        
        embed = Embed(
            title="⏱️ Rate Limit Exceeded",
            description=result.get('reason', 'Too many requests'),
            color=Color.red()
        )
        
        if 'retry_after' in result:
            embed.add_field(
                name="🕐 Retry After",
                value=f"{result['retry_after']} seconds",
                inline=False
            )
        
        if 'penalty_end' in result:
            penalty_end = datetime.fromtimestamp(result['penalty_end'])
            embed.add_field(
                name="🚫 Penalty Active",
                value=f"Until {penalty_end.strftime('%H:%M:%S')}",
                inline=False
            )
        
        embed.add_field(
            name="📊 Limits",
            value=f"Limit: {result.get('limit', 'N/A')} per {result.get('window', 'N/A')}s",
            inline=False
        )
        
        embed.set_footer(text="Please wait before trying again.")
        
        return embed

# Global rate limiter instance
rate_limiter = RateLimiter(settings.REDIS_URL)

def initialize_rate_limiter(redis_url: str = None):
    """Initialize the rate limiter"""
    global rate_limiter
    if redis_url is None:
        redis_url = settings.REDIS_URL
    rate_limiter = RateLimiter(redis_url)
    return rate_limiter

# Simple Rate Limiter Class
class SimpleRateLimiter:
    """Redis-based rate limiter using sorted sets"""
    
    def __init__(self, key, limit, window, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.key = f"rate:{key}"
        self.limit = limit
        self.window = window

    def allow(self):
        """Check if request is allowed"""
        now = int(time.time())

        pipe = self.redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(self.key, 0, now - self.window)
        
        # Count current requests
        pipe.zcard(self.key)
        
        # Add current request
        pipe.zadd(self.key, {str(now): now})
        
        # Set expiration
        pipe.expire(self.key, self.window)

        _, count, _, _ = pipe.execute()

        return count < self.limit
    
    def reset(self):
        """Reset the rate limiter"""
        self.redis.delete(self.key)
    
    def get_status(self):
        """Get current rate limit status"""
        now = int(time.time())
        
        # Remove old entries
        self.redis.zremrangebyscore(self.key, 0, now - self.window)
        
        # Count current requests
        count = self.redis.zcard(self.key)
        
        return {
            'current': count,
            'limit': self.limit,
            'remaining': max(0, self.limit - count),
            'reset_time': now + self.window
        }

# Test the simple rate limiter
def test_simple_rate_limiter():
    """Test simple rate limiter functionality"""
    print("Testing Simple Rate Limiter...")
    
    # Create rate limiter: 5 requests per 10 seconds
    limiter = SimpleRateLimiter("test_user", 5, 10)
    
    # Reset to start clean
    limiter.reset()
    
    print(f"Initial status: {limiter.get_status()}")
    
    # Test allowed requests
    for i in range(5):
        allowed = limiter.allow()
        status = limiter.get_status()
        print(f"Request {i+1}: allowed={allowed}, status={status}")
    
    # Test exceeded limit
    exceeded = limiter.allow()
    status = limiter.get_status()
    print(f"Exceeded request: allowed={exceeded}, status={status}")
    
    print("Simple Rate Limiter test complete!")

# Import uuid for generating unique IDs
import uuid
