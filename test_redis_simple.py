# test_redis_simple.py
import sys

def test_redis_import():
    """Test if Redis library is installed"""
    try:
        import redis
        print("✅ Redis library is installed")
        return True
    except ImportError:
        print("❌ Redis library not installed")
        print("Run: pip install redis")
        return False

def test_redis_connection():
    """Test Redis connection"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6381, decode_responses=True)
        r.ping()
        print("✅ Redis server is running and accessible")
        return True
    except redis.ConnectionError:
        print("❌ Redis server is not running")
        print("Start Redis with:")
        print("1. Docker: docker run --name redis -p 6380:6380 -d redis:7-alpine")
        print("2. Or install Redis CLI: https://github.com/microsoftarchive/redis/releases")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Redis: {e}")
        return False

def main():
    print("🧪 Testing Redis Setup...")
    print()
    
    # Test 1: Redis library
    if not test_redis_import():
        return
    
    print()
    
    # Test 2: Redis connection
    if not test_redis_connection():
        return
    
    print()
    print("🎉 Redis is ready for your bot!")
    print("You can now run: python main.py")

if __name__ == "__main__":
    main()
