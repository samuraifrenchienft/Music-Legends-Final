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

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

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

DEPLOY_VERSION = "v3.0-2026-02-07-SEED-DAILY-FIX"

def main():
    """Main bot entry point"""
    try:
        print(f"[DEPLOY] ====== VERSION: {DEPLOY_VERSION} ======")
        print(f"[DEPLOY] Working directory: {os.getcwd()}")
        print(f"[DEPLOY] Files: {sorted(os.listdir('.'))}")
        
        # Log startup
        from services.system_monitor import log_bot_restart
        log_bot_restart('startup')
        
        from config import settings

        # Initialize Sentry error tracking (optional — only if SENTRY_DSN is set)
        sentry_dsn = settings.SENTRY_DSN
        if sentry_dsn:
            import sentry_sdk
            sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.1)
            print("[SENTRY] Error tracking enabled")
        
        # Check environment
        logger.info("Starting Music Legends Bot...")
        bot_token = settings.BOT_TOKEN
        
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
        import traceback
        from services.system_monitor import log_bot_crash
        log_bot_crash(error=str(e), traceback_str=traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
