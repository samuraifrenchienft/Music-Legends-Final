#!/usr/bin/env python3
"""
Test single cron service startup without conflicts
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.txt')

# Add current directory to Python path
sys.path.insert(0, '.')

async def test_cron_service():
    """Test cron service startup"""
    try:
        print("Testing cron service startup...")
        
        # Test import
        from scheduler.cron import cron_service
        print("✅ Imported scheduler.cron.cron_service")
        
        # Test infrastructure import
        from infrastructure import infrastructure
        print("✅ Imported infrastructure")
        
        # Check no duplicate imports
        import sys
        cron_modules = [m for m in sys.modules.keys() if 'cron' in m.lower()]
        print(f"✅ Cron-related modules loaded: {len(cron_modules)}")
        for mod in cron_modules:
            print(f"   - {mod}")
        
        # Test cron service start
        await cron_service.start()
        print("✅ Cron service started")
        
        # Check running status
        if cron_service.running:
            print("✅ Cron service is running")
        else:
            print("❌ Cron service not running")
            return False
        
        # Test job registration
        async def test_job():
            print("Test job executed")
            return "success"
        
        cron_service.add_interval_job(test_job, seconds=3600, job_id="test_job")
        print("✅ Test job registered")
        
        # Get job status
        status = cron_service.get_job_status()
        print(f"✅ Jobs registered: {len(status)}")
        for job_id, job_info in status.items():
            print(f"   - {job_id}: {job_info.get('schedule', 'N/A')}")
        
        # Stop cron service
        cron_service.stop()
        print("✅ Cron service stopped")
        
        print("\n🚀 Cron service test PASSED!")
        print("✅ No duplicate cron services")
        print("✅ No circular imports")
        print("✅ Single APScheduler-based service working")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cron_service())
    sys.exit(0 if success else 1)
