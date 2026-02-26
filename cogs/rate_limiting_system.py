# rate_limiting_system.py
"""
Advanced Rate Limiting & Abuse Prevention System
- Token bucket algorithm with Redis
- In-memory fallback for offline operation
- Multiple strategy types (fixed window, sliding window, token bucket)
- Adaptive rate limiting based on user behavior
- Abuse detection and alerting
- DDoS mitigation
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from enum import Enum
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import redis
from functools import wraps

from cogs.security_event_logger import security_logger, EventSeverity, log_suspicious_activity


# ==========================================
# RATE LIMITING STRATEGIES
# ==========================================

class RateLimitStrategy(Enum):
    """Rate limiting algorithm strategies"""
    FIXED_WINDOW = "fixed_window"           # Count resets at fixed intervals
    SLIDING_WINDOW = "sliding_window"       # Window slides with each request
    TOKEN_BUCKET = "token_bucket"           # Tokens replenish over time
    LEAKY_BUCKET = "leaky_bucket"          # Requests leak out at constant rate


# ==========================================
# RATE LIMIT CONFIGURATION
# ==========================================

from ..config import settings

# Default rate limit configurations
DEFAULT_LIMITS = {k: RateLimitConfig(action=k, **v) for k, v in settings.RATES.items()}


# ==========================================
# RATE LIMITER
# ==========================================

class AdvancedRateLimiter:
    """
    Advanced rate limiting with multiple strategies
    
    Features:
    - Token bucket algorithm
    - Fixed/sliding window counting
    - Redis support with in-memory fallback
    - Adaptive limits based on violations
    - Cascading limits across related actions
    - Abuse detection
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        enable_redis: bool = True
    ):
        self.redis_client = redis_client
        self.use_redis = enable_redis and redis_client is not None
        
        # In-memory storage (fallback)
        self.local_state = defaultdict(dict)  # user_id -> action -> state
        self.violation_history = defaultdict(deque)  # user_id -> violations
        
        # Configurations
        self.configs = DEFAULT_LIMITS.copy()
        
        # Abuse scores
        self.abuse_scores = defaultdict(float)  # user_id -> score
        self.abuse_threshold = 100.0
        
        print(f"✅ [RATE_LIMITER] Initialized (Redis: {self.use_redis})")
    
    def register_limit(self, config: RateLimitConfig):
        """Register a new rate limit configuration"""
        self.configs[config.action] = config
        print(f"✅ [RATE_LIMITER] Registered limit: {config.action}")
    
    def _get_redis_key(self, user_id: int, action: str) -> str:
        """Generate Redis key"""
        return f"rate_limit:{user_id}:{action}"
    
    def _get_state(self, user_id: int, action: str) -> Dict:
        """Get rate limit state (from Redis or memory)"""
        if self.use_redis:
            try:
                key = self._get_redis_key(user_id, action)
                state = self.redis_client.get(key)
                if state:
                    return json.loads(state)
            except Exception as e:
                print(f"⚠️  [RATE_LIMITER] Redis error: {e}")
        
        # Fallback to in-memory
        return self.local_state[user_id].get(action, {})
    
    def _set_state(self, user_id: int, action: str, state: Dict, ttl: int):
        """Set rate limit state (in Redis or memory)"""
        if self.use_redis:
            try:
                key = self._get_redis_key(user_id, action)
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(state)
                )
                return
            except Exception as e:
                print(f"⚠️  [RATE_LIMITER] Redis error: {e}")
        
        # Fallback to in-memory
        self.local_state[user_id][action] = state
    
    def _check_token_bucket(
        self,
        user_id: int,
        action: str,
        config: RateLimitConfig
    ) -> Tuple[bool, Dict]:
        """
        Token bucket algorithm
        
        Tokens refill at constant rate over time
        """
        state = self._get_state(user_id, action)
        current_time = time.time()
        
        # Initialize state
        if not state:
            state = {
                'tokens': float(config.max_requests),
                'last_update': current_time,
                'count': 0
            }
        
        # Calculate tokens to add based on elapsed time
        elapsed = current_time - state['last_update']
        refill_rate = config.max_requests / config.window_seconds
        tokens_to_add = elapsed * refill_rate
        
        state['tokens'] = min(
            config.max_requests,
            state['tokens'] + tokens_to_add
        )
        state['last_update'] = current_time
        
        # Check if tokens available
        if state['tokens'] >= 1:
            state['tokens'] -= 1
            state['count'] += 1
            allowed = True
        else:
            allowed = False
        
        # Save state
        self._set_state(user_id, action, state, config.window_seconds)
        
        return allowed, state
    
    def _check_sliding_window(
        self,
        user_id: int,
        action: str,
        config: RateLimitConfig
    ) -> Tuple[bool, Dict]:
        """
        Sliding window algorithm
        
        Tracks exact timestamps of requests
        """
        state = self._get_state(user_id, action)
        current_time = time.time()
        window_start = current_time - config.window_seconds
        
        # Initialize or retrieve request times
        if not state:
            request_times = deque()
        else:
            request_times = deque(state.get('request_times', []))
        
        # Remove old requests outside window
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check if limit exceeded
        if len(request_times) < config.max_requests:
            request_times.append(current_time)
            allowed = True
        else:
            allowed = False
        
        # Update state
        state = {
            'request_times': list(request_times),
            'count': len(request_times)
        }
        self._set_state(user_id, action, state, config.window_seconds)
        
        return allowed, state
    
    def _check_fixed_window(
        self,
        user_id: int,
        action: str,
        config: RateLimitConfig
    ) -> Tuple[bool, Dict]:
        """
        Fixed window algorithm
        
        Count resets at fixed intervals
        """
        state = self._get_state(user_id, action)
        current_time = time.time()
        
        # Initialize or check if window expired
        if not state or (current_time - state.get('window_start', 0)) >= config.window_seconds:
            state = {
                'window_start': current_time,
                'count': 1,
                'exceeded': False
            }
            allowed = True
        else:
            # Within window
            if state['count'] < config.max_requests:
                state['count'] += 1
                allowed = True
            else:
                allowed = False
                state['exceeded'] = True
        
        # Save state
        self._set_state(user_id, action, state, config.window_seconds)
        
        return allowed, state
    
    def check_rate_limit(
        self,
        user_id: int,
        action: str
    ) -> Tuple[bool, Dict]:
        """
        Check if request is within rate limits
        
        Returns:
            Tuple of (allowed, state_info)
        """
        
        # Get configuration
        if action not in self.configs:
            print(f"⚠️  [RATE_LIMITER] Unknown action: {action}")
            return True, {}  # Allow if no limit defined
        
        config = self.configs[action]
        
        print(f"🔐 [RATE_LIMITER] Checking {action} for user {user_id}")
        
        # Check abuse score
        if self.abuse_scores[user_id] > self.abuse_threshold:
            print(f"🚨 [RATE_LIMITER] User {user_id} has high abuse score: {self.abuse_scores[user_id]}")
            
            security_logger.log_event(
                "HIGH_ABUSE_SCORE_LIMIT",
                severity=EventSeverity.CRITICAL,
                user_id=user_id,
                details={
                    "action": action,
                    "abuse_score": self.abuse_scores[user_id]
                }
            )
            
            return False, {"reason": "high_abuse_score"}
        
        # Select strategy
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            allowed, state = self._check_token_bucket(user_id, action, config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            allowed, state = self._check_sliding_window(user_id, action, config)
        elif config.strategy == RateLimitStrategy.FIXED_WINDOW:
            allowed, state = self._check_fixed_window(user_id, action, config)
        else:
            allowed, state = self._check_token_bucket(user_id, action, config)
        
        # Handle violations
        if not allowed:
            self._record_violation(user_id, action, config)
        
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"{status} [RATE_LIMITER] {action}: {state}")
        
        return allowed, state
    
    def _record_violation(self, user_id: int, action: str, config: RateLimitConfig):
        """Record rate limit violation"""
        
        violation = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id
        }
        
        # Add to violation history
        self.violation_history[user_id].append(violation)
        if len(self.violation_history[user_id]) > 100:
            self.violation_history[user_id].popleft()
        
        # Increment abuse score
        score_increase = 10.0
        if config.enable_adaptive:
            # Check recent violations
            recent_violations = sum(
                1 for v in self.violation_history[user_id]
                if datetime.fromisoformat(v['timestamp']) > 
                   datetime.now() - timedelta(hours=1)
            )
            score_increase *= (1.0 + recent_violations * 0.5)
        
        self.abuse_scores[user_id] += score_increase
        
        print(f"⚠️  [RATE_LIMITER] Violation recorded: {action} (score: {self.abuse_scores[user_id]})")
        
        # Log security event
        security_logger.log_event(
            f"RATE_LIMIT_EXCEEDED_{action.upper()}",
            severity=EventSeverity.WARNING,
            user_id=user_id,
            details={
                "action": action,
                "abuse_score": self.abuse_scores[user_id],
                "recent_violations": len(self.violation_history[user_id])
            }
        )
        
        # Alert if many violations
        if len(self.violation_history[user_id]) > 10:
            log_suspicious_activity(
                activity_type=f"EXCESSIVE_{action.upper()}_ATTEMPTS",
                user_id=user_id,
                details={
                    "violations": len(self.violation_history[user_id]),
                    "abuse_score": self.abuse_scores[user_id]
                }
            )
    
    def get_violation_history(self, user_id: int) -> List[Dict]:
        """Get violation history for user"""
        return list(self.violation_history.get(user_id, []))
    
    def get_abuse_score(self, user_id: int) -> float:
        """Get abuse score for user"""
        return self.abuse_scores.get(user_id, 0.0)
    
    def reset_abuse_score(self, user_id: int):
        """Reset abuse score for user"""
        self.abuse_scores[user_id] = 0.0
        print(f"✅ [RATE_LIMITER] Reset abuse score for user {user_id}")


# ==========================================
# GLOBAL RATE LIMITER
# ==========================================

# Initialize with Redis client if available
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    rate_limiter = AdvancedRateLimiter(redis_client, enable_redis=True)
except Exception as e:
    print(f"⚠️  [RATE_LIMITER] Redis unavailable: {e}, using in-memory storage")
    rate_limiter = AdvancedRateLimiter(enable_redis=False)


# ==========================================
# DECORATORS FOR RATE LIMITED COMMANDS
# ==========================================

def rate_limited(action: str):
    """
    Decorator for rate-limited commands
    
    Usage:
        @rate_limited('pack_create')
        async def create_pack(interaction: Interaction):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction, *args, **kwargs):
            user_id = interaction.user.id
            
            # Check rate limit
            allowed, state = rate_limiter.check_rate_limit(user_id, action)
            
            if not allowed:
                remaining_msg = ""
                if 'request_times' in state:
                    # Sliding window - show time until oldest request expires
                    oldest = state['request_times'][0]
                    window_size = rate_limiter.configs[action].window_seconds
                    expires_in = int(oldest + window_size - time.time())
                    remaining_msg = f"\n⏱️  Try again in **{expires_in} seconds**"
                elif 'window_start' in state:
                    # Fixed window - show time until window resets
                    window_size = rate_limiter.configs[action].window_seconds
                    expires_in = int(state['window_start'] + window_size - time.time())
                    remaining_msg = f"\n⏱️  Try again in **{expires_in} seconds**"
                
                await interaction.response.send_message(
                    f"❌ **Rate Limit Exceeded**\n\n"
                    f"Action: **{action}**\n"
                    f"You've reached your limit for this action.{remaining_msg}\n\n"
                    f"*Repeated violations may result in temporary restrictions.*",
                    ephemeral=True
                )
                return
            
            # Execute function
            try:
                return await func(interaction, *args, **kwargs)
            except Exception as e:
                print(f"❌ [RATE_LIMITER] Error executing {action}: {e}")
                raise
        
        return wrapper
    return decorator


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_rate_limit_status(user_id: int) -> Dict:
    """Get current rate limit status for user"""
    
    status = {
        "user_id": user_id,
        "abuse_score": rate_limiter.get_abuse_score(user_id),
        "violations": len(rate_limiter.get_violation_history(user_id)),
        "limits": {}
    }
    
    # Check each configured action
    for action, config in rate_limiter.configs.items():
        _, state = rate_limiter.check_rate_limit(user_id, action)
        status['limits'][action] = {
            "max_requests": config.max_requests,
            "window_seconds": config.window_seconds,
            "current_count": state.get('count', 0),
            "remaining": max(0, config.max_requests - state.get('count', 0))
        }
    
    return status


def is_user_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited due to abuse"""
    return rate_limiter.get_abuse_score(user_id) > rate_limiter.abuse_threshold
