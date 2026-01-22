# cron_service.py
import asyncio
import logging
from datetime import datetime, timedelta
import time
from typing import Dict, Any, Callable, List
from dataclasses import dataclass
from scheduler.cron import cron_service

@dataclass
class CronJob:
    name: str
    schedule: str  # cron expression
    handler: Callable
    enabled: bool = True
    last_run: float = None
    next_run: float = None
    timezone: str = 'UTC'

class CronService:
    def __init__(self):
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self.timezone_offset = 0  # Could be configured
        
        # Register default jobs
        self._register_default_jobs()
    
    def _register_default_jobs(self):
        """Register default cron jobs"""
        
        # Daily rewards at midnight UTC
        self.register_job(
            name="daily_rewards",
            schedule="0 0 * * *",  # Every day at midnight UTC
            handler=self._handle_daily_rewards
        )
        
        # Drop automation every 30 minutes
        self.register_job(
            name="auto_drops",
            schedule="*/30 * * * *",  # Every 30 minutes
            handler=self._handle_auto_drops
        )
        
        # Cooldown resets every hour
        self.register_job(
            name="cooldown_resets",
            schedule="0 * * * *",  # Every hour
            handler=self._handle_cooldown_resets
        )
        
        # Season tasks daily
        self.register_job(
            name="season_tasks",
            schedule="0 1 * * *",  # Every day at 1 AM UTC
            handler=self._handle_season_tasks
        )
        
        # Cleanup every 6 hours
        self.register_job(
            name="cleanup",
            schedule="0 */6 * * *",  # Every 6 hours
            handler=self._handle_cleanup
        )
        
        # Analytics every hour
        self.register_job(
            name="analytics",
            schedule="0 * * * *",  # Every hour
            handler=self._handle_analytics
        )
    
    def register_job(self, name: str, schedule: str, handler: Callable, enabled: bool = True):
        """Register a cron job"""
        job = CronJob(
            name=name,
            schedule=schedule,
            handler=handler,
            enabled=enabled,
            next_run=self._calculate_next_run(schedule)
        )
        self.jobs[name] = job
        logging.info(f"Registered cron job: {name} with schedule {schedule}")
    
    def _calculate_next_run(self, schedule: str) -> float:
        """Calculate next run time from cron expression"""
        # Simplified cron parsing - in production use croniter library
        now = datetime.now()
        
        # Parse basic cron expressions (minute hour day month weekday)
        parts = schedule.split()
        if len(parts) != 5:
            # Default to 1 hour from now
            return (now + timedelta(hours=1)).timestamp()
        
        minute, hour, day, month, weekday = parts
        
        # Simple implementation - run every hour for now
        next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        return next_run.timestamp()
    
    async def start(self):
        """Start the cron service"""
        if self.running:
            return
        
        self.running = True
        asyncio.create_task(self._cron_loop())
        logging.info("Cron service started")
    
    def stop(self):
        """Stop the cron service"""
        self.running = False
        logging.info("Cron service stopped")
    
    async def _cron_loop(self):
        """Main cron loop"""
        while self.running:
            try:
                now = time.time()
                
                # Check each job
                for job in self.jobs.values():
                    if not job.enabled:
                        continue
                    
                    if job.next_run and now >= job.next_run:
                        await self._execute_job(job)
                        
                        # Calculate next run
                        job.next_run = self._calculate_next_run(job.schedule)
                
                # Sleep for 1 minute (check frequency)
                await asyncio.sleep(60)
                
            except Exception as e:
                logging.error(f"Error in cron loop: {e}")
                await asyncio.sleep(60)
    
    async def _execute_job(self, job: CronJob):
        """Execute a cron job"""
        try:
            logging.info(f"Executing cron job: {job.name}")
            
            # Mark last run
            job.last_run = time.time()
            
            # Execute handler
            if asyncio.iscoroutinefunction(job.handler):
                result = await job.handler()
            else:
                result = job.handler()
            
            logging.info(f"Completed cron job: {job.name}")
            return result
            
        except Exception as e:
            logging.error(f"Error executing cron job {job.name}: {e}")
            return None
    
    # Job Handlers
    async def _handle_daily_rewards(self):
        """Handle daily rewards reset and distribution"""
        logging.info("Processing daily rewards")
        
        # Reset daily bonuses for all users
        # This would query your database and reset daily_claim flags
        # Also grant daily currency to active users
        
        # Queue daily reward processing
        from infrastructure import infrastructure
        await infrastructure.message_queue.enqueue('event-queue', {
            'type': 'daily_reset',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
        return {'processed': 'daily_rewards'}
    
    async def _handle_auto_drops(self):
        """Handle automatic drops based on server activity"""
        logging.info("Processing auto drops")
        
        # Get active servers with high activity
        # Queue auto-drop jobs for eligible servers
        
        await infrastructure.message_queue.enqueue('event-queue', {
            'type': 'auto_drops',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
        return {'processed': 'auto_drops'}
    
    async def _handle_cooldown_resets(self):
        """Handle cooldown resets"""
        logging.info("Processing cooldown resets")
        
        # Reset expired cooldowns
        # This would check your database and reset expired cooldowns
        
        await infrastructure.message_queue.enqueue('event-queue', {
            'type': 'cooldown_resets',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
        return {'processed': 'cooldown_resets'}
    
    async def _handle_season_tasks(self):
        """Handle season-related tasks"""
        logging.info("Processing season tasks")
        
        # Check for season transitions
        # Enforce caps
        # Update leaderboards
        
        await infrastructure.message_queue.enqueue('event-queue', {
            'type': 'season_tasks',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
        return {'processed': 'season_tasks'}
    
    async def _handle_cleanup(self):
        """Handle cleanup tasks"""
        logging.info("Processing cleanup")
        
        # Expire old trades
        # Clear old drops
        # Prune old logs
        
        await infrastructure.message_queue.enqueue('event-queue', {
            'type': 'cleanup',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
        return {'processed': 'cleanup'}
    
    async def _handle_analytics(self):
        """Handle analytics processing"""
        logging.info("Processing analytics")
        
        # Process analytics data
        # Update metrics
        # Generate reports
        
        await infrastructure.message_queue.enqueue('event-queue', {
            'type': 'analytics',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
        return {'processed': 'analytics'}
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all jobs"""
        now = time.time()
        status = {}
        
        for name, job in self.jobs.items():
            status[name] = {
                'enabled': job.enabled,
                'schedule': job.schedule,
                'last_run': job.last_run,
                'next_run': job.next_run,
                'next_run_in': max(0, job.next_run - now) if job.next_run else None
            }
        
        return status
    
    def enable_job(self, name: str):
        """Enable a job"""
        if name in self.jobs:
            self.jobs[name].enabled = True
            logging.info(f"Enabled cron job: {name}")
    
    def disable_job(self, name: str):
        """Disable a job"""
        if name in self.jobs:
            self.jobs[name].enabled = False
            logging.info(f"Disabled cron job: {name}")

# Global cron service instance
cron_service = CronService()
