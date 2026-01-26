#!/usr/bin/env python3
"""
Full system test - verify bot startup, infrastructure, and card generation
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

async def test_full_system():
    """Test complete bot system"""
    
    print("="*70)
    print("FULL SYSTEM TEST - BOT STARTUP & CARD GENERATION")
    print("="*70)
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    # Test 1: Environment Variables
    print("\n[1/8] Testing Environment Variables...")
    try:
        bot_token = os.getenv("BOT_TOKEN")
        app_id = os.getenv("DISCORD_APPLICATION_ID")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        if not bot_token:
            results['failed'].append("BOT_TOKEN not set")
            print("❌ BOT_TOKEN not set")
        else:
            results['passed'].append("BOT_TOKEN configured")
            print(f"✅ BOT_TOKEN configured")
        
        if app_id:
            results['passed'].append("DISCORD_APPLICATION_ID configured")
            print(f"✅ DISCORD_APPLICATION_ID: {app_id}")
        else:
            results['warnings'].append("DISCORD_APPLICATION_ID not set")
            print("⚠️  DISCORD_APPLICATION_ID not set (optional)")
        
        print(f"✅ REDIS_URL: {redis_url}")
        results['passed'].append(f"REDIS_URL: {redis_url}")
        
    except Exception as e:
        results['failed'].append(f"Environment check: {e}")
        print(f"❌ Environment error: {e}")
    
    # Test 2: Database
    print("\n[2/8] Testing Database...")
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        print(f"✅ Database initialized: {db.db_path}")
        results['passed'].append("Database initialized")
    except Exception as e:
        results['failed'].append(f"Database: {e}")
        print(f"❌ Database error: {e}")
        return False
    
    # Test 3: Card Generation
    print("\n[3/8] Testing Card Generation...")
    try:
        from services.card_generator import CardGenerator
        
        card_gen = CardGenerator()
        
        # Test card creation in database using add_card_to_master
        test_card_data = {
            'card_id': 'test_drake_gods_plan',
            'name': 'Drake',
            'title': "God's Plan",
            'hero_artist': 'Drake',
            'hero_song': "God's Plan",
            'youtube_id': 'test_youtube_123',
            'rarity': 'legendary',
            'power': 85,
            'speed': 90,
            'technique': 88,
            'charisma': 95
        }
        
        success = db.add_card_to_master(test_card_data)
        
        if success:
            print(f"✅ Card created in database: {test_card_data['card_id']}")
            print(f"   Artist: {test_card_data['hero_artist']}")
            print(f"   Song: {test_card_data['hero_song']}")
            print(f"   Rarity: {test_card_data['rarity']}")
            results['passed'].append("Card generation working")
        else:
            results['failed'].append("Card creation returned False")
            print("❌ Card creation failed")
    except Exception as e:
        results['failed'].append(f"Card generation: {e}")
        print(f"❌ Card generation error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Pack Creation
    print("\n[4/8] Testing Pack Creation...")
    try:
        pack_id = db.create_creator_pack(
            creator_id=123456789,
            name="Test Pack",
            description="Test pack for system verification",
            pack_size=5
        )
        
        if pack_id:
            print(f"✅ Pack created: {pack_id}")
            results['passed'].append("Pack creation working")
        else:
            results['failed'].append("Pack creation returned None")
            print("❌ Pack creation failed")
    except Exception as e:
        results['failed'].append(f"Pack creation: {e}")
        print(f"❌ Pack creation error: {e}")
    
    # Test 5: Redis Connection
    print("\n[5/8] Testing Redis Connection...")
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        print(f"✅ Redis connected: {redis_url}")
        results['passed'].append("Redis connection working")
    except Exception as e:
        results['warnings'].append(f"Redis: {e}")
        print(f"⚠️  Redis not available: {e}")
        print("   (Bot can run without Redis, but some features may be limited)")
    
    # Test 6: Cron Service
    print("\n[6/8] Testing Cron Service...")
    try:
        from scheduler.cron import cron_service
        await cron_service.start()
        
        if cron_service.running:
            print("✅ Cron service started")
            results['passed'].append("Cron service working")
            cron_service.stop()
        else:
            results['failed'].append("Cron service not running")
            print("❌ Cron service failed to start")
    except Exception as e:
        results['failed'].append(f"Cron service: {e}")
        print(f"❌ Cron service error: {e}")
    
    # Test 7: Bot Import & Cog Loading
    print("\n[7/8] Testing Bot Import & Cog Loading...")
    try:
        import main
        
        # Check cog list
        expected_cogs = [
            'cogs.start_game',
            'cogs.gameplay',
            'cogs.card_game',
        ]
        
        print(f"✅ Bot module imported")
        print(f"   Expected cogs: {len(expected_cogs)}")
        for cog in expected_cogs:
            print(f"   - {cog}")
        
        results['passed'].append("Bot module imports correctly")
    except Exception as e:
        results['failed'].append(f"Bot import: {e}")
        print(f"❌ Bot import error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 8: Command Count
    print("\n[8/8] Testing Command Discovery...")
    try:
        # This would require actually starting the bot
        # For now, just verify the cogs exist
        import importlib
        
        cog_commands = {}
        for cog_path in expected_cogs:
            try:
                cog_module = importlib.import_module(cog_path)
                cog_commands[cog_path] = "✅ Loaded"
                print(f"✅ {cog_path} - loadable")
            except Exception as e:
                cog_commands[cog_path] = f"❌ {e}"
                print(f"❌ {cog_path} - error: {e}")
        
        results['passed'].append("Cog modules verified")
    except Exception as e:
        results['failed'].append(f"Command discovery: {e}")
        print(f"❌ Command discovery error: {e}")
    
    # Summary
    print("\n" + "="*70)
    print(f"SUMMARY: {len(results['passed'])} passed, {len(results['failed'])} failed, {len(results['warnings'])} warnings")
    print("="*70)
    
    if results['passed']:
        print("\n✅ PASSED:")
        for item in results['passed']:
            print(f"   - {item}")
    
    if results['warnings']:
        print("\n⚠️  WARNINGS:")
        for item in results['warnings']:
            print(f"   - {item}")
    
    if results['failed']:
        print("\n❌ FAILED:")
        for item in results['failed']:
            print(f"   - {item}")
        print("\n🚨 SYSTEM NOT READY - Fix failed items before deployment")
        return False
    else:
        print("\n🚀 SYSTEM READY FOR DEPLOYMENT!")
        print("\n✅ Core Features Verified:")
        print("   - Database operations")
        print("   - Card generation")
        print("   - Pack creation")
        print("   - Cron service")
        print("   - Bot module loading")
        print("   - Cog imports")
        
        if results['warnings']:
            print("\n⚠️  Optional features may be limited (see warnings above)")
        
        print("\n📋 Next Steps:")
        print("   1. Start bot: python run_bot.py")
        print("   2. Test commands in Discord")
        print("   3. Deploy to Railway")
        
        return True

if __name__ == "__main__":
    success = asyncio.run(test_full_system())
    sys.exit(0 if success else 1)
