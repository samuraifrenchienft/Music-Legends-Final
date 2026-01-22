# scheduler/cron.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from rq_queue.locks import RedisLock
from datetime import datetime, timedelta

class AsyncCronService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running = False
        self.jobs = {}
        
    def safe(self, job_key: str):
        """Decorator for safe job execution with Redis locks"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                with RedisLock(f"cron:{job_key}", ttl=30):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            return
        
        try:
            self.scheduler.start()
            self.running = True
            logging.info("Async cron scheduler started")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        if self.running:
            self.scheduler.shutdown()
            self.running = False
            logging.info("Async cron scheduler stopped")
    
    def add_daily_job(self, job_func, hour: int = 0, minute: int = 0, job_id: str = None):
        """Add daily job"""
        job_id = job_id or f"daily_{job_func.__name__}"
        
        self.scheduler.add_job(
            job_func,
            CronTrigger(hour=hour, minute=minute),
            id=job_id
        )
        
        self.jobs[job_id] = {
            'func': job_func,
            'schedule': f"daily at {hour:02d}:{minute:02d}",
            'type': 'daily'
        }
        
        logging.info(f"Added daily job: {job_id} at {hour:02d}:{minute:02d}")
    
    def add_interval_job(self, job_func, seconds: int, job_id: str = None):
        """Add interval job"""
        job_id = job_id or f"interval_{job_func.__name__}"
        
        self.scheduler.add_job(
            job_func,
            IntervalTrigger(seconds=seconds),
            id=job_id
        )
        
        self.jobs[job_id] = {
            'func': job_func,
            'schedule': f"every {seconds} seconds",
            'type': 'interval'
        }
        
        logging.info(f"Added interval job: {job_id} every {seconds}s")
    
    def add_cron_job(self, job_func, cron_expression: str, job_id: str = None):
        """Add cron job with custom expression"""
        job_id = job_id or f"cron_{job_func.__name__}"
        
        # Parse cron expression (simplified)
        # Format: minute hour day month weekday
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        minute, hour, day, month, weekday = parts
        
        # Convert to APScheduler format
        cron_trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            weekday=weekday
        )
        
        self.scheduler.add_job(
            job_func,
            cron_trigger,
            id=job_id
        )
        
        self.jobs[job_id] = {
            'func': job_func,
            'schedule': cron_expression,
            'type': 'cron'
        }
        
        logging.info(f"Added cron job: {job_id} with schedule {cron_expression}")
    
    def remove_job(self, job_id: str):
        """Remove a job"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logging.info(f"Removed job: {job_id}")
        except Exception as e:
            logging.error(f"Failed to remove job {job_id}: {e}")
    
    def get_job_status(self) -> dict:
        """Get status of all jobs"""
        status = {}
        
        for job_id, job_info in self.jobs.items():
            try:
                job = self.scheduler.get_job(job_id)
                status[job_id] = {
                    'id': job_id,
                    'name': job_id,
                    'next_run_time': job.next_run_time,
                    'schedule': job_info['schedule'],
                    'type': job_info['type'],
                    'active': True
                }
            except Exception as e:
                status[job_id] = {
                    'id': job_id,
                    'name': job_id,
                    'active': False,
                    'error': str(e)
                }
        
        return status
    
    def pause_job(self, job_id: str):
        """Pause a job"""
        try:
            self.scheduler.pause_job(job_id)
            logging.info(f"Paused job: {job_id}")
        except Exception as e:
            logging.error(f"Failed to pause job {job_id}: {e}")
    
    def resume_job(self, job_id: str):
        """Resume a job"""
        try:
            self.scheduler.resume_job(job_id)
            logging.info(f"Resumed job: {job_id}")
        except Exception as e:
            logging.error(f"Failed to resume job {job_id}: {e}")

# Global cron service instance
cron_service = AsyncCronService()

# Import required modules
import os
import time
