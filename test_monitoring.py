# test_monitoring.py
# Test script for the monitoring system

import asyncio
import os
import sys

# Add current directory to path
sys.path.append('.')

async def test_monitoring():
    """Test all monitoring functionality"""
    print("🔍 Testing Music Legends Monitoring System")
    print("==========================================")
    
    # Load environment variables
    with open('.env.txt', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    
    # Import monitoring modules
    from monitor.alerts import (
        send_ops, send_econ, legendary_created, purchase_completed,
        refund_executed, trade_completed, pack_opened, system_error
    )
    from config.monitor import MONITOR
    
    print(f"📡 Ops webhook configured: {'✅' if MONITOR['WEBHOOK_OPS'] else '❌'}")
    print(f"💰 Econ webhook configured: {'✅' if MONITOR['WEBHOOK_ECON'] else '❌'}")
    
    # Test basic alerts
    print("\n1. Testing basic alerts...")
    await send_ops("🔧 Test Alert", "Operations monitoring test - SUCCESS!", "success")
    await send_econ("💰 Test Alert", "Economy monitoring test - SUCCESS!", "success")
    print("   ✅ Basic alerts sent")
    
    # Test economy events
    print("\n2. Testing economy events...")
    await legendary_created(user_id=12345, card_serial="LEG_001", card_name="Fire Dragon")
    await purchase_completed(user_id=12345, purchase_id="PUR_001", amount=9999, pack_type="founder_pack_black")
    await refund_executed(user_id=12345, purchase_id="PUR_002", amount=4999)
    await trade_completed(user_a=12345, user_b=67890, trade_id="TRADE_001", card_count=5)
    await pack_opened(user_id=12345, pack_type="black", card_count=3, legendary=False)
    await pack_opened(user_id=67890, pack_type="silver", card_count=2, legendary=True)
    print("   ✅ Economy events sent")
    
    # Test operations events
    print("\n3. Testing operations events...")
    await send_ops("🚀 System Started", "Music Legends bot is online", "success")
    await send_ops("⚠️ Queue Backlog", "Pack queue: 25 jobs (threshold: 20)", "orange")
    await send_ops("🔥 Job Failures", "3 failed jobs (threshold: 1)", "red")
    await send_ops("💾 Database Backup", "Backup completed: 15.2MB", "success")
    print("   ✅ Operations events sent")
    
    # Test error handling
    print("\n4. Testing error handling...")
    await system_error("Test error message", {"user_id": 12345, "action": "test"})
    print("   ✅ Error alert sent")
    
    # Test webhook failure handling
    print("\n5. Testing webhook failure handling...")
    # Temporarily set invalid webhook to test failure handling
    original_ops = MONITOR["WEBHOOK_OPS"]
    MONITOR["WEBHOOK_OPS"] = "https://invalid-webhook-url"
    
    await send_ops("Should Fail", "This should fail silently")
    print("   ✅ Webhook failure handled silently")
    
    # Restore original webhook
    MONITOR["WEBHOOK_OPS"] = original_ops
    
    print("\n🎉 All monitoring tests completed!")
    print("📊 Check your Discord channels for the test messages")
    
    # Show configuration
    print("\n📋 Current Configuration:")
    print(f"   Check interval: {MONITOR['CHECK_INTERVAL']} seconds")
    print(f"   Queue warning threshold: {MONITOR['QUEUE_WARN']}")
    print(f"   Fail warning threshold: {MONITOR['FAIL_WARN']}")
    print(f"   Worker timeout: {MONITOR['WORKER_TIMEOUT']} seconds")


async def test_health_checks():
    """Test health check functionality"""
    print("\n🏥 Testing Health Check System")
    print("================================")
    
    try:
        from monitor.health_checks import HealthChecker
        import redis
        import sqlite3
        
        # Mock Redis connection
        class MockRedis:
            def __init__(self):
                self.data = {}
                
            def ping(self, timeout=None):
                return True
                
            def llen(self, key):
                return self.data.get(key, 0)
        
        # Mock queues
        mock_queues = {
            "pack_queue": ["job1", "job2", "job3"],
            "trade_queue": ["job1"],
            "large_queue": ["job"] * 25  # Over threshold
        }
        
        # Create health checker
        health_checker = HealthChecker(MockRedis(), mock_queues)
        
        # Run health checks
        await health_checker.check_redis_connection()
        print("   ✅ Redis connection check")
        
        await health_checker.check_database_connection()
        print("   ✅ Database connection check")
        
        await health_checker.check_queue_sizes()
        print("   ✅ Queue size check (should trigger alert for large_queue)")
        
        await health_checker.check_failed_jobs()
        print("   ✅ Failed jobs check")
        
        await health_checker.check_memory_usage()
        print("   ✅ Memory usage check")
        
        await health_checker.check_cpu_usage()
        print("   ✅ CPU usage check")
        
        print("\n🎉 Health check tests completed!")
        
    except ImportError as e:
        print(f"   ⚠️  Health check test skipped: {e}")
    except Exception as e:
        print(f"   ❌ Health check test failed: {e}")


async def main():
    """Run all tests"""
    await test_monitoring()
    await test_health_checks()
    
    print("\n🎯 Monitoring System Test Complete!")
    print("📊 All alerts should appear in your Discord channels:")
    print("   🔧 Operations channel: System alerts, errors, health checks")
    print("   💰 Economy channel: Purchases, trades, legendaries, packs")


if __name__ == "__main__":
    asyncio.run(main())
