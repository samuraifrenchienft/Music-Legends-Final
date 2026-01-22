# test_redis.py
import redis
import sys

def test_redis_connection():
    """Test Redis connection"""
    try:
        # Try localhost Redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis connection successful!")
        return True
    except redis.ConnectionError:
        print("❌ Redis connection failed!")
        print("\n🔧 Solutions:")
        print("1. Run: redis-quick-start.bat (Docker)")
        print("2. Install Redis CLI: https://github.com/microsoftarchive/redis/releases")
        print("3. Use WSL: sudo apt install redis-server")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_redis_connection()
