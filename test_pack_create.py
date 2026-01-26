#!/usr/bin/env python3
"""
Test pack creation functionality
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.txt')

# Add current directory to Python path
sys.path.insert(0, '.')

def test_pack_creation():
    """Test if pack creation works"""
    try:
        print("Testing pack creation...")
        
        # Test database connection
        from database import DatabaseManager
        db = DatabaseManager()
        print("✅ Database connected")
        
        # Test pack creation method
        pack_id = db.create_creator_pack(
            creator_id=123456789,
            name="Test Pack",
            description="Test description",
            pack_size=5
        )
        print(f"✅ Pack created: {pack_id}")
        
        # Test bot loading
        import main
        bot = main.Bot()
        print("✅ Bot created")
        
        # Test cog loading
        async def test_cogs():
            await bot.setup_hook()
            print("✅ Cogs loaded")
            
            # Check commands
            commands = []
            for cog_name in bot.cogs:
                cog = bot.get_cog(cog_name)
                if cog:
                    for cmd in cog.walk_app_commands():
                        commands.append(f"/{cmd.name}")
            
            print(f"✅ Commands loaded: {len(commands)}")
            print(f"Commands: {commands}")
            
            # Check for create_pack
            if "/create_pack" in commands:
                print("✅ /create_pack command found!")
            else:
                print("❌ /create_pack command missing!")
        
        import asyncio
        asyncio.run(test_cogs())
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pack_creation()
