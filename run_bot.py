#!/usr/bin/env python3
"""
Production bot runner with proper error handling and monitoring
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging for Windows compatibility
import io
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main bot entry point"""
    try:
        print("[DOCKER] Starting bot in Docker container")
        print(f"[DOCKER] Working directory: {os.getcwd()}")
        print(f"[DOCKER] Python path: {sys.path}")
        print(f"[DOCKER] Files in current dir: {os.listdir('.')}")
        
        # Load environment variables from .env.txt
        from dotenv import load_dotenv
        load_dotenv('.env.txt')
        print("[DOCKER] Environment variables loaded")
        
        # Check environment
        logger.info("Starting Music Legends Bot...")
        bot_token = os.getenv("BOT_TOKEN")
        print(f"[DOCKER] BOT_TOKEN present: {bool(bot_token)}")
        print(f"[DOCKER] BOT_TOKEN starts with: {bot_token[:10] if bot_token else 'None'}...")
        
        if not bot_token:
            logger.error("BOT_TOKEN is required but not set in .env.txt")
            sys.exit(1)
        
        # Start the bot
        print("[DOCKER] Importing main module...")
        import main
        print("[DOCKER] Creating bot instance...")
        bot = main.Bot()
        print("[DOCKER] Starting bot run...")
        bot.run(bot_token)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
