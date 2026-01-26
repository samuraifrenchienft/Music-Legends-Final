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
        # Load environment variables from .env.txt
        from dotenv import load_dotenv
        load_dotenv('.env.txt')
        
        # Check environment
        logger.info("Starting Music Legends Bot...")
        
        # Verify critical environment variables
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            logger.error("BOT_TOKEN is required but not set in .env.txt")
            sys.exit(1)
        
        # Start the bot
        import main
        bot = main.Bot()
        bot.run(bot_token)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
