#!/usr/bin/env python3
"""
Production bot runner with proper error handling and monitoring
"""

import os
import sys
import logging
import time
import random
from pathlib import Path
import asyncio
import discord

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
        bot_token = settings.DISCORD_TOKEN

        if not bot_token:
            logger.error("DISCORD_TOKEN is required but not set")
            sys.exit(1)
        
        # Start the bot with backoff to avoid restart storms on Discord/Cloudflare 429s.
        print("[DOCKER] Importing main module...")
        import main
        attempt = 0
        max_delay_seconds = 900  # 15 minutes

        while True:
            bot = None
            try:
                print("[DOCKER] Creating bot instance...")
                bot = main.Bot()
                print("[DOCKER] Starting bot run...")
                bot.run(bot_token)
                logger.info("Bot stopped cleanly")
                return
            except discord.HTTPException as e:
                is_rate_limit = getattr(e, "status", None) == 429 or "1015" in str(e)
                if not is_rate_limit:
                    raise

                attempt += 1
                base_delay = min(max_delay_seconds, 30 * (2 ** min(attempt, 5)))
                jitter = random.randint(0, 15)
                delay = base_delay + jitter
                logger.warning(
                    "Discord rate limited startup/login (attempt=%s, status=%s). "
                    "Sleeping %ss before retry to avoid restart storm.",
                    attempt,
                    getattr(e, "status", "unknown"),
                    delay,
                )
                from services.system_monitor import log_bot_crash
                log_bot_crash(
                    error=f"Discord rate limit: {e}",
                    traceback_str="rate_limit_backoff",
                    additional_data={"attempt": attempt, "sleep_seconds": delay},
                )
                time.sleep(delay)
            finally:
                if bot is not None:
                    try:
                        asyncio.run(bot.close())
                    except Exception:
                        # Best-effort cleanup to avoid unclosed aiohttp connector warnings.
                        pass
        
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
