#!/usr/bin/env python3
"""
Quick System Test for Music Legends Bot
Tests all core functionality without starting the full bot
"""

import os
import sys
import sqlite3
from pathlib import Path

def test_environment():
    """Test environment variables"""
    print("🔧 Testing Environment Variables...")
    
    required_vars = ['BOT_TOKEN', 'DISCORD_APPLICATION_ID', 'TEST_SERVER_ID']
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Missing")
            missing_vars.append(var)
    
    return len(missing_vars) == 0

def test_database():
    """Test database connectivity and basic operations"""
    print("\n🗄️ Testing Database...")
    
    db_path = 'music_legends.db'
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"✅ Database tables found: {len(tables)}")
        
        # Check key tables
        key_tables = ['users', 'cards', 'creator_packs', 'battle_matches']
        for table in key_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ {table}: {count} records")
            else:
                print(f"❌ {table}: Missing")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_module_imports():
    """Test core module imports"""
    print("\n📦 Testing Module Imports...")
    
    modules = [
        'database',
        'battle_engine', 
        'season_system',
        # 'spotify_integration',  # Removed — not used
        'youtube_integration',
        'card_economy',
        'models'
    ]
    
    success_count = 0
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
            success_count += 1
        except Exception as e:
            print(f"❌ {module}: {e}")
    
    return success_count == len(modules)

def test_cog_loading():
    """Test cog directory structure"""
    print("\n⚙️ Testing Cog Structure...")
    
    cogs_dir = Path('cogs')
    if not cogs_dir.exists():
        print("❌ Cogs directory not found")
        return False
    
    cog_files = list(cogs_dir.glob('*.py'))
    print(f"✅ Found {len(cog_files)} cog files")
    
    for cog_file in cog_files:
        print(f"✅ {cog_file.name}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 Music Legends Bot - System Test\n")
    
    tests = [
        ("Environment", test_environment),
        ("Database", test_database), 
        ("Modules", test_module_imports),
        ("Cogs", test_cog_loading)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:15} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All systems operational!")
        return 0
    else:
        print("⚠️ Some issues detected - review above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
