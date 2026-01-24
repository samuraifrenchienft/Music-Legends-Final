#!/usr/bin/env python3
"""
Health check script for Railway
"""
import sys
import os

def main():
    try:
        # Test basic imports
        import discord
        import main
        
        # Test environment
        token = os.getenv("BOT_TOKEN")
        if not token:
            print("❌ BOT_TOKEN not found")
            return False
            
        # Test database
        try:
            from database import DatabaseManager
            db = DatabaseManager()
            print("✅ Database OK")
        except Exception as e:
            print(f"⚠️ Database warning: {e}")
        
        # Test cogs
        try:
            from cogs.essential_commands import EssentialCommandsCog
            from cogs.pack_creation import PackCreation
            print("✅ Cogs OK")
        except Exception as e:
            print(f"⚠️ Cogs warning: {e}")
        
        print("✅ Health check passed")
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
