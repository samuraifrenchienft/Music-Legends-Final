#!/usr/bin/env python3
"""
Simple bot startup test without Discord connection
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.txt')

# Add current directory to Python path
sys.path.insert(0, '.')

async def test_bot_startup():
    """Test bot startup without connecting to Discord"""
    try:
        print("Testing bot startup...")
        
        # Create bot instance
        import main
        bot = main.Bot()
        print("✅ Bot instance created")
        
        # Test setup_hook (loads cogs)
        await bot.setup_hook()
        print("✅ Cogs loaded successfully")
        
        # Check commands
        commands = []
        for cog_name in bot.cogs:
            cog = bot.get_cog(cog_name)
            if cog:
                for cmd in cog.walk_app_commands():
                    commands.append(f"/{cmd.name}")
        
        print(f"✅ {len(commands)} commands loaded")
        
        # Check for pack creation
        pack_commands = [cmd for cmd in commands if 'pack' in cmd]
        print(f"✅ Pack commands: {pack_commands}")
        
        # Test database methods
        from database import DatabaseManager
        db = DatabaseManager()
        
        # Test the actual create_pack method that the command uses
        pack_id = db.create_creator_pack(
            creator_id=123456789,
            name="Test Pack",
            description="Test pack description", 
            pack_size=5
        )
        print(f"✅ Pack creation works: {pack_id}")
        
        print("✅ Bot is ready to run!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_startup())
    if success:
        print("\n🚀 Bot is ready for deployment!")
    else:
        print("\n❌ Bot has issues that need fixing")
