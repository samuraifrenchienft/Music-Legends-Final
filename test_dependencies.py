#!/usr/bin/env python3
"""
Test all critical dependencies can be imported
"""

import sys

def test_dependencies():
    """Test import of all critical dependencies"""
    
    results = {
        'passed': [],
        'failed': []
    }
    
    dependencies = [
        ('discord.py', 'discord'),
        ('python-dotenv', 'dotenv'),
        ('flask', 'flask'),
        ('requests', 'requests'),
        ('spotipy', 'spotipy'),
        ('stripe', 'stripe'),
        ('redis', 'redis'),
        ('rq', 'rq'),
        ('aioredis', 'aioredis'),
        ('apscheduler', 'apscheduler'),
        ('Pillow', 'PIL'),
        ('aiohttp', 'aiohttp'),
        ('eth-account', 'eth_account'),
        ('web3', 'web3'),
        ('google-api-python-client', 'googleapiclient'),
        ('sqlalchemy', 'sqlalchemy'),
        ('aiosqlite', 'aiosqlite'),
    ]
    
    print("Testing critical dependencies...\n")
    
    for package_name, import_name in dependencies:
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            results['passed'].append((package_name, version))
            print(f"✅ {package_name:30} v{version}")
        except ImportError as e:
            results['failed'].append((package_name, str(e)))
            print(f"❌ {package_name:30} MISSING")
        except Exception as e:
            results['failed'].append((package_name, str(e)))
            print(f"⚠️  {package_name:30} ERROR: {e}")
    
    # Test specific critical imports for the bot
    print("\nTesting bot-specific imports...")
    
    critical_imports = [
        ('APScheduler AsyncIOScheduler', 'apscheduler.schedulers.asyncio', 'AsyncIOScheduler'),
        ('APScheduler CronTrigger', 'apscheduler.triggers.cron', 'CronTrigger'),
        ('Redis Queue', 'rq', 'Queue'),
        ('Discord Bot', 'discord.ext.commands', 'Bot'),
    ]
    
    for name, module_path, class_name in critical_imports:
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {name:30} OK")
            results['passed'].append((name, 'OK'))
        except ImportError as e:
            print(f"❌ {name:30} MISSING")
            results['failed'].append((name, str(e)))
        except Exception as e:
            print(f"⚠️  {name:30} ERROR: {e}")
            results['failed'].append((name, str(e)))
    
    # Summary
    print("\n" + "="*60)
    print(f"SUMMARY: {len(results['passed'])} passed, {len(results['failed'])} failed")
    print("="*60)
    
    if results['failed']:
        print("\n❌ FAILED DEPENDENCIES:")
        for pkg, error in results['failed']:
            print(f"   - {pkg}: {error}")
        print("\nRun: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ ALL DEPENDENCIES INSTALLED AND WORKING!")
        return True

if __name__ == "__main__":
    success = test_dependencies()
    sys.exit(0 if success else 1)
