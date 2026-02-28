# monitor/health_checks.py
import asyncio
import redis
import sqlite3
import psutil
from datetime import datetime
from config import settings
from config.monitor import MONITOR, HEALTH_CHECKS
from monitor.alerts import (
    send_ops, send_econ, queue_backlog, job_failures, 
    high_memory_usage, redis_connection_failed, database_connection_failed
)


class HealthChecker:
    def __init__(self, redis_conn, queues):
        self.redis_conn = redis_conn
        self.queues = queues
        self.last_check = None
        
    async def check_all(self):
        """Run all health checks"""
        self.last_check = datetime.utcnow()
        
        await asyncio.gather(
            self.check_redis_connection(),
            self.check_database_connection(),
            self.check_queue_sizes(),
            self.check_failed_jobs(),
            self.check_memory_usage(),
            self.check_cpu_usage(),
        )
    
    async def check_redis_connection(self):
        """Check Redis connection"""
        try:
            # Test Redis ping
            self.redis_conn.ping(timeout=HEALTH_CHECKS["redis_ping_timeout"])
        except (redis.ConnectionError, redis.TimeoutError) as e:
            await redis_connection_failed()
            return False
        return True
    
    async def check_database_connection(self):
        """Check database connection (supports both SQLite and PostgreSQL)"""
        try:
            db_url = settings.DATABASE_URL

            if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
                # PostgreSQL check
                import psycopg2
                from database import _PgConnectionWrapper
                url = db_url
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql://", 1)
                conn = _PgConnectionWrapper(psycopg2.connect(url, connect_timeout=HEALTH_CHECKS["db_connection_timeout"]))
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
            else:
                # SQLite check
                db_path = db_url
                if db_path.startswith("sqlite:///"):
                    db_path = db_path[10:]
                conn = sqlite3.connect(db_path, timeout=HEALTH_CHECKS["db_connection_timeout"])
                conn.execute("SELECT 1")
                conn.close()
        except Exception as e:
            await database_connection_failed()
            return False
        return True
    
    async def check_queue_sizes(self):
        """Check all queue sizes"""
        for name, queue in self.queues.items():
            try:
                size = len(queue)
                threshold = MONITOR["QUEUE_WARN"]
                
                if size > threshold:
                    await queue_backlog(name, size, threshold)
                    
            except Exception as e:
                await send_ops("Queue Check Error", f"Failed to check queue '{name}': {e}", "red")
    
    async def check_failed_jobs(self):
        """Check failed job count"""
        try:
            failed_count = self.redis_conn.llen("rq:failed")
            threshold = MONITOR["FAIL_WARN"]
            
            if failed_count >= threshold:
                await job_failures(failed_count, threshold)
                
        except Exception as e:
            await send_ops("Failed Jobs Check Error", f"Failed to check failed jobs: {e}", "red")
    
    async def check_memory_usage(self):
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            percentage = memory.percent
            used_mb = memory.used / 1024 / 1024
            total_mb = memory.total / 1024 / 1024
            
            threshold = HEALTH_CHECKS["memory_usage_warning"]
            
            if percentage > threshold:
                await high_memory_usage(int(percentage), int(used_mb), int(total_mb))
                
        except Exception as e:
            await send_ops("Memory Check Error", f"Failed to check memory usage: {e}", "red")
    
    async def check_cpu_usage(self):
        """Check CPU usage"""
        try:
            percentage = psutil.cpu_percent(interval=1)
            threshold = HEALTH_CHECKS["cpu_usage_warning"]
            
            if percentage > threshold:
                await send_ops(
                    "🔥 High CPU Usage", 
                    f"CPU usage: {percentage}% (threshold: {threshold}%)", 
                    "orange" if percentage < 95 else "red"
                )
                
        except Exception as e:
            await send_ops("CPU Check Error", f"Failed to check CPU usage: {e}", "red")


# Background monitoring task
async def start_monitoring(redis_conn, queues):
    """Start background monitoring"""
    health_checker = HealthChecker(redis_conn, queues)
    
    # Send startup alert
    await send_ops("🚀 Monitoring Started", "Health monitoring is now active", "success")
    
    while True:
        try:
            await health_checker.check_all()
            await asyncio.sleep(MONITOR["CHECK_INTERVAL"])
        except Exception as e:
            await send_ops("Monitoring Error", f"Health check failed: {e}", "red")
            await asyncio.sleep(30)  # Wait before retrying


# Individual check functions for manual use
async def check_queues():
    """Check queue sizes (legacy compatibility)"""
    for name, q in QUEUES.items():
        size = len(q)
        if size > MONITOR["QUEUE_WARN"]:
            await queue_backlog(name, size, MONITOR["QUEUE_WARN"])


async def check_failures():
    """Check failed jobs (legacy compatibility)"""
    failed = redis_conn.llen("rq:failed")
    if failed >= MONITOR["FAIL_WARN"]:
        await job_failures(failed, MONITOR["FAIL_WARN"])


# Global variables for legacy compatibility
QUEUES = {}  # Will be populated by main application
redis_conn = None  # Will be set by main application
