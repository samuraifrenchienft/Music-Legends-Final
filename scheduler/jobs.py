# scheduler/jobs.py
import logging
from scheduler.cron import cron_service
from scheduler.services import rewards, drops, trades, seasons, data

# Import safe decorator
from scheduler.cron import AsyncCronService

# Get the cron service instance
cron = cron_service

# Daily rewards job - runs at 00:05 UTC
@cron.safe("daily")
async def job_daily_rewards():
    """Reset daily bonuses and grant currency"""
    logging.info("Running daily rewards job")
    
    try:
        result = await rewards.reset_all()
        logging.info(f"Daily rewards completed: {result}")
        return result
    except Exception as e:
        logging.error(f"Daily rewards job failed: {e}")
        raise

# Auto drops job - runs every 60 seconds
@cron.safe("drops")
async def job_auto_drops():
    """Spawn activity-based drops"""
    logging.info("Running auto drops job")
    
    try:
        result = await drops.activity_spawn()
        logging.info(f"Auto drops completed: {result}")
        return result
    except Exception as e:
        logging.error(f"Auto drops job failed: {e}")
        raise

# Trade expiration job - runs every 10 minutes
@cron.safe("trades")
async def job_expire_trades():
    """Cancel stale trades"""
    logging.info("Running trade expiration job")
    
    try:
        result = await trades.expire_old()
        logging.info(f"Trade expiration completed: {result}")
        return result
    except Exception as e:
        logging.error(f"Trade expiration job failed: {e}")
        raise

# Season check job - runs every hour
@cron.safe("season")
async def job_season_check():
    """Check season caps and maintenance"""
    logging.info("Running season check job")
    
    try:
        # Enforce printing caps
        caps_result = await seasons.enforce_caps()
        
        # Check for season transition
        season_result = await seasons.check_season_transition()
        
        logging.info(f"Season check completed: caps={caps_result}, season={season_result}")
        return {
            'caps': caps_result,
            'season': season_result
        }
    except Exception as e:
        logging.error(f"Season check job failed: {e}")
        raise

# Cleanup job - runs daily at 03:00 UTC
@cron.safe("cleanup")
async def job_cleanup():
    """Prune old data and cleanup"""
    logging.info("Running cleanup job")
    
    try:
        result = await data.prune_old_data()
        logging.info(f"Cleanup completed: {result}")
        return result
    except Exception as e:
        logging.error(f"Cleanup job failed: {e}")
        raise

async def init_cron():
    """Initialize cron service with all jobs"""
    logging.info("Initializing cron service...")
    
    # Add daily rewards at 00:05 UTC
    cron.add_daily_job(job_daily_rewards, hour=0, minute=5, job_id="daily_rewards")
    
    # Add auto drops every 60 seconds
    cron.add_interval_job(job_auto_drops, seconds=60, job_id="auto_drops")
    
    # Add trade expiration every 10 minutes
    cron.add_interval_job(job_expire_trades, seconds=600, job_id="expire_trades")
    
    # Add season checks every hour
    cron.add_interval_job(job_season_check, seconds=3600, job_id="season_check")
    
    # Add cleanup daily at 03:00 UTC
    cron.add_daily_job(job_cleanup, hour=3, minute=0, job_id="cleanup")
    
    # Start the scheduler
    await cron.start()
    
    logging.info("Cron service initialized")
    
    # Return job status
    return cron.get_job_status()
