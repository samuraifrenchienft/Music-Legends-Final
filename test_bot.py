# test_bot.py - Quick validation script
import json
import sys
from pathlib import Path

def test_config():
    """Test if config.json exists and has required fields"""
    try:
        with open("config.json") as f:
            config = json.load(f)
        
        required_fields = ["token", "application-id", "test-server-id"]
        missing = [field for field in required_fields if not config.get(field)]
        
        if missing:
            print(f"❌ Config missing fields: {missing}")
            print("Please fill in config.json with your Discord bot details")
            return False
        
        print("✅ Config structure is valid")
        return True
    except FileNotFoundError:
        print("❌ config.json not found")
        return False
    except json.JSONDecodeError:
        print("❌ config.json has invalid JSON")
        return False

def test_imports():
    """Test if all modules can be imported"""
    try:
        import discord
        import discord_cards
        import battle_engine
        import database
        import card_data
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database initialization"""
    try:
        from database import DatabaseManager
        from card_data import CardDataManager
        
        # Test database creation
        db = DatabaseManager("test_music_legends.db")
        card_manager = CardDataManager(db)
        
        # Test card loading
        success_count = card_manager.initialize_database_cards()
        if success_count > 0:
            print(f"✅ Database initialized with {success_count} cards")
            print("✅ Database operations working")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_cogs():
    """Test if cogs can be loaded"""
    try:
        from cogs.card_game import CardGameCog
        print("✅ Card game cog loaded successfully")
        return True
    except ImportError as e:
        print(f"❌ Cog import error: {e}")
        return False

def main():
    print("🔍 Testing Discord Card Game Bot Setup\n")
    
    tests = [
        ("Config Validation", test_config),
        ("Module Imports", test_imports),
        ("Database Operations", test_database),
        ("Cog Loading", test_cogs),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 {name}:")
        if test_func():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Bot is ready to run!")
        print("Next steps:")
        print("1. Fill in your Discord bot token in config.json")
        print("2. Run: python main.py")
    else:
        print("\n❌ Please fix the issues above before running the bot")
        sys.exit(1)

if __name__ == "__main__":
    main()
