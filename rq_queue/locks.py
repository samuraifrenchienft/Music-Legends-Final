# queue/locks.py
import redis
import time
from contextlib import contextmanager
import uuid
import os

class RedisLock:
    def __init__(self, key, ttl=10):
        self.key = f"lock:{key}"
        self.ttl = ttl
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.identifier = str(uuid.uuid4())

    def __enter__(self):
        # Try to acquire lock with timeout
        end_time = time.time() + self.ttl
        while time.time() < end_time:
            # Use SET with NX and EX for atomic lock
            if self.redis.set(self.key, self.identifier, nx=True, ex=self.ttl):
                return True
            time.sleep(0.05)  # Wait 50ms before retry
        raise TimeoutError(f"Could not acquire lock {self.key} within {self.ttl}s")

    def __exit__(self, *args):
        # Only delete if we still own the lock
        current_value = self.redis.get(self.key)
        if current_value == self.identifier:
            self.redis.delete(self.key)

def user_lock(user_id: int, ttl: int = 10):
    """Create a user-specific lock"""
    return RedisLock(f"user:{user_id}", ttl)

def trade_lock(trade_id: str, ttl: int = 30):
    """Create a trade-specific lock"""
    return RedisLock(f"trade:{trade_id}", ttl)

def card_lock(card_id: str, ttl: int = 10):
    """Create a card-specific lock"""
    return RedisLock(f"card:{card_id}", ttl)

def pack_lock(pack_id: str, ttl: int = 15):
    """Create a pack-specific lock"""
    return RedisLock(f"pack:{pack_id}", ttl)
