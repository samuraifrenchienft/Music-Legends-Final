# infrastructure.py
import asyncio
import logging
from message_queue import initialize_message_queue
from rate_limiter import initialize_rate_limiter
from scheduler.cron import cron_service

from config import settings

class InfrastructureManager:
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = settings.REDIS_URL
        self.redis_url = redis_url
        self.message_queue = None
        self.rate_limiter = None
        self.running = False
        
    async def initialize(self):
        """Initialize all infrastructure components"""
        logging.info("Initializing infrastructure...")
        
        # Initialize message queue
        self.message_queue = initialize_message_queue(self.redis_url)
        logging.info("✅ Message queue initialized")
        
        # Initialize rate limiter
        self.rate_limiter = initialize_rate_limiter(self.redis_url)
        logging.info("✅ Rate limiter initialized")
        
        # Initialize cron service (APScheduler)
        await cron_service.start()
        logging.info("✅ Cron service started")
        
        self.running = True
        logging.info("🚀 Infrastructure initialized successfully")
    
    async def start_queue_processors(self):
        """Start queue processor tasks"""
        if not self.message_queue:
            return
        
        # Start processors for each queue
        queues = ['drop-queue', 'pack-queue', 'trade-queue', 'burn-queue', 'event-queue']
        
        for queue_name in queues:
            asyncio.create_task(self.message_queue.process_queue(queue_name))
            logging.info(f"Started processor for {queue_name}")
        
        return queues
    
    async def shutdown(self):
        """Shutdown all infrastructure components"""
        logging.info("Shutting down infrastructure...")
        
        # Stop cron service
        cron_service.stop()
        logging.info("✅ Cron service stopped")
        
        self.running = False
        logging.info("🛑 Infrastructure shutdown complete")
    
    def get_status(self) -> dict:
        """Get infrastructure status"""
        return {
            'running': self.running,
            'message_queue': self.message_queue is not None,
            'rate_limiter': self.rate_limiter is not None,
            'cron_service': cron_service.running
        }

# Global infrastructure manager
infrastructure = InfrastructureManager(settings.REDIS_URL)

# Import logging
import logging
