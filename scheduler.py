# scheduler.py
import time
import uuid
import asyncio
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Job:
    id: str
    type: str  # 'autoDrop' | 'resetCooldown' | 'expireTrade'
    payload: Any
    run_at: float
    attempts: int = 0
    max_attempts: int = 3

class Scheduler:
    def __init__(self):
        self.queue: List[Job] = []
        self.interval: float = 1.0  # 1 second
        self.running: bool = False
        self.handlers: Dict[str, Callable] = {}
        
        # Register default handlers
        self.register_handler('autoDrop', self._handle_auto_drop)
        self.register_handler('resetCooldown', self._handle_reset_cooldown)
        self.register_handler('expireTrade', self._handle_expire_trade)
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            asyncio.create_task(self._tick_loop())
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
    
    def schedule(self, job_type: str, payload: Any, delay_ms: int):
        """Schedule a job to run after delay_ms"""
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            payload=payload,
            run_at=time.time() + (delay_ms / 1000),
            max_attempts=3
        )
        self.queue.append(job)
        return job.id
    
    def schedule_at(self, job_type: str, payload: Any, run_at: datetime):
        """Schedule a job to run at specific time"""
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            payload=payload,
            run_at=run_at.timestamp(),
            max_attempts=3
        )
        self.queue.append(job)
        return job.id
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type"""
        self.handlers[job_type] = handler
    
    async def _tick_loop(self):
        """Main scheduler loop"""
        while self.running:
            await self._tick()
            await asyncio.sleep(self.interval)
    
    async def _tick(self):
        """Process due jobs"""
        now = time.time()
        due_jobs = [job for job in self.queue if job.run_at <= now]
        
        for job in due_jobs:
            await self._execute(job)
        
        # Remove completed/failed jobs
        self.queue = [job for job in self.queue if job.run_at > now or job in due_jobs]
    
    async def _execute(self, job: Job):
        """Execute a job"""
        try:
            handler = self.handlers.get(job.type)
            if handler:
                await handler(job.payload)
            else:
                print(f"No handler for job type: {job.type}")
        except Exception as e:
            print(f"Job {job.id} failed: {e}")
            job.attempts += 1
            
            if job.attempts < job.max_attempts:
                # Retry after 5 seconds
                job.run_at = time.time() + 5
                self.queue.append(job)
            else:
                print(f"Job {job.id} failed after {job.max_attempts} attempts")
    
    # Default handlers
    async def _handle_auto_drop(self, payload: Dict):
        """Handle automatic drop"""
        server_id = payload.get('server_id')
        channel_id = payload.get('channel_id')
        
        # Import here to avoid circular imports
        from card_economy import economy_manager
        
        if economy_manager and server_id and channel_id:
            # Check if server can auto-drop
            if economy_manager._can_drop(server_id):
                drop_result = economy_manager.create_drop(channel_id, server_id, 0, 'auto')
                
                if drop_result['success']:
                    # Send drop message (would need bot instance)
                    print(f"Auto drop created in channel {channel_id}")
    
    async def _handle_reset_cooldown(self, payload: Dict):
        """Handle cooldown reset"""
        server_id = payload.get('server_id')
        
        from card_economy import economy_manager
        
        if economy_manager and server_id:
            # Reset server cooldown
            economy_manager.drop_cooldowns.pop(server_id, None)
            print(f"Cooldown reset for server {server_id}")
    
    async def _handle_expire_trade(self, payload: Dict):
        """Handle trade expiration"""
        trade_id = payload.get('trade_id')
        
        # Would need to implement trade expiration logic
        print(f"Trade {trade_id} expired")
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        now = time.time()
        due_count = len([job for job in self.queue if job.run_at <= now])
        future_count = len([job for job in self.queue if job.run_at > now])
        
        return {
            'total_jobs': len(self.queue),
            'due_jobs': due_count,
            'future_jobs': future_count,
            'running': self.running
        }

# Global scheduler instance
scheduler = Scheduler()
