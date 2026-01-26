#!/usr/bin/env python3
"""
Test Redis connection with correct port
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.txt')

def test_redis_connection():
    """Test Redis connection on port 6379"""
    try:
        import redis
        
        # Test default connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        print(f"Testing Redis connection: {redis_url}")
        
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Test ping
        response = r.ping()
        print(f"✅ Redis PING: {response}")
        
        # Test set/get
        r.set("test_key", "test_value")
        value = r.get("test_key")
        print(f"✅ Redis SET/GET: {value}")
        
        # Test delete
        r.delete("test_key")
        print("✅ Redis DELETE: Success")
        
        # Test queue connection
        from rq import Queue
        queue = Queue("test-queue", connection=r)
        print(f"✅ RQ Queue created: {queue.name}")
        
        print("\n🚀 Redis connection test PASSED!")
        print(f"Port: 6379")
        print(f"Connection: Working")
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Redis is running: redis-server")
        print("2. Check port 6379 is available")
        print("3. Or start with Docker: docker-compose up -d redis")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
