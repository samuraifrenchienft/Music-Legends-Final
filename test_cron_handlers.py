#!/usr/bin/env python3
"""
Test all cron job handlers execute properly
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.txt')

# Add current directory to Python path
sys.path.insert(0, '.')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_cron_handlers():
    """Test all cron job handlers"""
    
    print("="*60)
    print("TESTING CRON JOB HANDLERS")
    print("="*60)
    
    results = {
        'passed': [],
        'failed': []
    }
    
    try:
        # Import services
        from scheduler.services import rewards, drops, trades, seasons, data
        print("\n✅ Imported all service modules")
        
        # Test 1: Daily Rewards
        print("\n[1/6] Testing Daily Rewards Handler...")
        try:
            result = await rewards.reset_all()
            if result.get('success'):
                print(f"✅ Daily rewards handler: {result}")
                results['passed'].append('rewards.reset_all')
            else:
                print(f"❌ Daily rewards handler failed: {result}")
                results['failed'].append('rewards.reset_all')
        except Exception as e:
            print(f"❌ Daily rewards handler error: {e}")
            results['failed'].append(f'rewards.reset_all: {e}')
        
        # Test 2: Auto Drops
        print("\n[2/6] Testing Auto Drops Handler...")
        try:
            result = await drops.activity_spawn()
            if result.get('success'):
                print(f"✅ Auto drops handler: {result}")
                results['passed'].append('drops.activity_spawn')
            else:
                print(f"❌ Auto drops handler failed: {result}")
                results['failed'].append('drops.activity_spawn')
        except Exception as e:
            print(f"❌ Auto drops handler error: {e}")
            results['failed'].append(f'drops.activity_spawn: {e}')
        
        # Test 3: Trade Expiration
        print("\n[3/6] Testing Trade Expiration Handler...")
        try:
            result = await trades.expire_old()
            if result.get('success'):
                print(f"✅ Trade expiration handler: {result}")
                results['passed'].append('trades.expire_old')
            else:
                print(f"❌ Trade expiration handler failed: {result}")
                results['failed'].append('trades.expire_old')
        except Exception as e:
            print(f"❌ Trade expiration handler error: {e}")
            results['failed'].append(f'trades.expire_old: {e}')
        
        # Test 4: Season Caps
        print("\n[4/6] Testing Season Caps Handler...")
        try:
            result = await seasons.enforce_caps()
            if result.get('success'):
                print(f"✅ Season caps handler: {result}")
                results['passed'].append('seasons.enforce_caps')
            else:
                print(f"❌ Season caps handler failed: {result}")
                results['failed'].append('seasons.enforce_caps')
        except Exception as e:
            print(f"❌ Season caps handler error: {e}")
            results['failed'].append(f'seasons.enforce_caps: {e}')
        
        # Test 5: Season Transition
        print("\n[5/6] Testing Season Transition Handler...")
        try:
            result = await seasons.check_season_transition()
            if result.get('success'):
                print(f"✅ Season transition handler: {result}")
                results['passed'].append('seasons.check_season_transition')
            else:
                print(f"❌ Season transition handler failed: {result}")
                results['failed'].append('seasons.check_season_transition')
        except Exception as e:
            print(f"❌ Season transition handler error: {e}")
            results['failed'].append(f'seasons.check_season_transition: {e}')
        
        # Test 6: Data Cleanup
        print("\n[6/6] Testing Data Cleanup Handler...")
        try:
            result = await data.prune_old_data()
            if result.get('success'):
                print(f"✅ Data cleanup handler: {result}")
                results['passed'].append('data.prune_old_data')
            else:
                print(f"❌ Data cleanup handler failed: {result}")
                results['failed'].append('data.prune_old_data')
        except Exception as e:
            print(f"❌ Data cleanup handler error: {e}")
            results['failed'].append(f'data.prune_old_data: {e}')
        
        # Summary
        print("\n" + "="*60)
        print(f"SUMMARY: {len(results['passed'])} passed, {len(results['failed'])} failed")
        print("="*60)
        
        if results['passed']:
            print("\n✅ PASSED HANDLERS:")
            for handler in results['passed']:
                print(f"   - {handler}")
        
        if results['failed']:
            print("\n❌ FAILED HANDLERS:")
            for handler in results['failed']:
                print(f"   - {handler}")
            return False
        else:
            print("\n🚀 ALL CRON HANDLERS WORKING!")
            print("\nImplemented Functionality:")
            print("  1. Daily Rewards - Resets daily claims, grants currency")
            print("  2. Auto Drops - Spawns activity-based drops")
            print("  3. Trade Expiration - Expires old pending trades")
            print("  4. Season Caps - Enforces card printing limits")
            print("  5. Season Transition - Checks for season changes")
            print("  6. Data Cleanup - Prunes old logs and expired data")
            return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cron_handlers())
    sys.exit(0 if success else 1)
