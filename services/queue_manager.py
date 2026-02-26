# services/queue_manager.py
"""
Queue Manager for Creator Pack Operations
Handles background processing for pack creation and opening
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.creator_service import creator_service
from services.open_creator import open_creator_pack
from services.creator_business_rules import creator_business_rules
from models.audit_minimal import AuditLog

class QueueManager:
    """Queue manager for background operations"""
    
    def __init__(self):
        self.queue = []
        self.processing = False
        self.max_queue_size = 1000
        
    def enqueue(self, job_data: Dict[str, Any]) -> str:
        """
        Add job to queue
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Job ID
        """
        if len(self.queue) >= self.max_queue_size:
            raise Exception("Queue is full")
        
        job_id = f"job_{datetime.utcnow().timestamp()}_{len(self.queue)}"
        job_data["job_id"] = job_id
        
        self.queue.append(job_data)
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self.process_queue())
        
        return job_id
    
    async def process_queue(self):
        """Process jobs in queue"""
        if self.processing:
            return
        
        self.processing = True
        
        try:
            while self.queue:
                job = self.queue.pop(0)
                await self.process_job(job)
                
                # Small delay between jobs to prevent overwhelming
                await asyncio.sleep(0.1)
                
        finally:
            self.processing = False
    
    async def process_job(self, job: Dict[str, Any]):
        """
        Process individual job
        
        Args:
            job: Job data
        """
        job_type = job.get("type")
        job_id = job.get("job_id")
        user_id = job.get("user_id")
        
        try:
            if job_type == "creator_pack_creation":
                await self.process_pack_creation(job)
            elif job_type == "creator_pack_opening":
                await self.process_pack_opening(job)
            else:
                print(f"❌ Unknown job type: {job_type}")
                
        except Exception as e:
            print(f"❌ Error processing job {job_id}: {e}")
            
            # Log job failure
            AuditLog.record(
                event="job_failed",
                user_id=user_id,
                target_id=job_id,
                payload={
                    "job_type": job_type,
                    "error": str(e),
                    "job_data": job
                }
            )
    
    async def process_pack_creation(self, job: Dict[str, Any]):
        """Process pack creation job"""
        user_id = job.get("user_id")
        pack_data = job.get("pack_data", {})
        
        # Extract pack data
        name = pack_data.get("name")
        artist_names = pack_data.get("artist_names", [])
        genre = pack_data.get("genre")
        
        # Validate against business rules
        validation = creator_business_rules.validate_pack_creation(user_id, artist_names)
        
        if not validation["valid"]:
            # Log validation failure
            AuditLog.record(
                event="pack_creation_validation_failed",
                user_id=user_id,
                target_id="validation",
                payload={
                    "errors": validation["errors"],
                    "warnings": validation["warnings"],
                    "pack_data": pack_data
                }
            )
            return
        
        # Calculate price
        price = creator_business_rules.calculate_pack_price(len(artist_names))
        
        # Create pack
        pack = await creator_service.create_creator_pack(
            user_id=user_id,
            name=name,
            artist_names=artist_names,
            genre=genre,
            price_cents=price
        )
        
        if pack:
            # Audit creation
            creator_business_rules.audit_pack_creation(user_id, pack, artist_names)
            
            # Log success
            AuditLog.record(
                event="pack_creation_completed",
                user_id=user_id,
                target_id=str(pack.id),
                payload={
                    "pack_id": str(pack.id),
                    "pack_name": pack.name,
                    "price": price,
                    "processing_time": datetime.utcnow().isoformat()
                }
            )
        else:
            # Log failure
            AuditLog.record(
                event="pack_creation_failed",
                user_id=user_id,
                target_id="creation",
                payload=pack_data
            )
    
    async def process_pack_opening(self, job: Dict[str, Any]):
        """Process pack opening job"""
        user_id = job.get("user_id")
        pack_id = job.get("pack_id")
        
        # Get pack
        from models.creator_pack import CreatorPack
        pack = CreatorPack.get_by_id(pack_id)
        
        if not pack:
            AuditLog.record(
                event="pack_opening_failed",
                user_id=user_id,
                target_id=pack_id,
                payload={"error": "Pack not found"}
            )
            return
        
        # Validate against business rules
        validation = creator_business_rules.validate_pack_opening(user_id, pack)
        
        if not validation["valid"]:
            AuditLog.record(
                event="pack_opening_validation_failed",
                user_id=user_id,
                target_id=pack_id,
                payload={
                    "errors": validation["errors"],
                    "warnings": validation["warnings"]
                }
            )
            return
        
        # Open pack
        cards = open_creator_pack(pack)
        
        if not cards:
            AuditLog.record(
                event="pack_opening_failed",
                user_id=user_id,
                target_id=pack_id,
                payload={"error": "No cards generated"}
            )
            return
        
        # Enforce legendary caps
        filtered_cards = creator_business_rules.enforce_legendary_cap(cards, user_id)
        
        # Audit opening
        creator_business_rules.audit_pack_opening(user_id, pack, filtered_cards)
        
        # Calculate revenue
        revenue = creator_business_rules.calculate_creator_revenue(pack)
        
        # Log success
        AuditLog.record(
            event="pack_opening_completed",
            user_id=user_id,
            target_id=pack_id,
            payload={
                "cards_generated": len(cards),
                "cards_delivered": len(filtered_cards),
                "legendary_enforced": len(cards) - len(filtered_cards),
                "revenue": revenue,
                "processing_time": datetime.utcnow().isoformat()
            }
        )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status
        
        Returns:
            Queue status dict
        """
        return {
            "queue_size": len(self.queue),
            "processing": self.processing,
            "max_queue_size": self.max_queue_size,
            "queue_utilization": len(self.queue) / self.max_queue_size * 100
        }
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific job
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status dict or None
        """
        # Check if job is still in queue
        for job in self.queue:
            if job.get("job_id") == job_id:
                return {
                    "job_id": job_id,
                    "status": "queued",
                    "position": self.queue.index(job),
                    "job_data": job
                }
        
        # Check if job was completed (check audit logs)
        try:
            completed_log = AuditLog.query.filter(
                AuditLog.target_id == job_id,
                AuditLog.event.in_(["pack_creation_completed", "pack_opening_completed"])
            ).first()
            
            if completed_log:
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "completed_at": completed_log.created_at.isoformat(),
                    "result": completed_log.payload
                }
                
            failed_log = AuditLog.query.filter(
                AuditLog.target_id == job_id,
                AuditLog.event.in_(["pack_creation_failed", "pack_opening_failed", "job_failed"])
            ).first()
            
            if failed_log:
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "failed_at": failed_log.created_at.isoformat(),
                    "error": failed_log.payload.get("error", "Unknown error")
                }
                
        except Exception:
            pass
        
        return None


# Global queue manager instance
queue_manager = QueueManager()


# Example usage
async def example_usage():
    """Example of queue manager usage"""
    
    # Queue pack creation
    pack_job_id = queue_manager.enqueue({
        "type": "creator_pack_creation",
        "user_id": 123456789,
        "pack_data": {
            "name": "Test Pack",
            "artist_names": ["Queen", "Led Zeppelin"],
            "genre": "Rock"
        }
    })
    
    print(f"📦 Queued pack creation: {pack_job_id}")
    
    # Queue pack opening
    open_job_id = queue_manager.enqueue({
        "type": "creator_pack_opening",
        "user_id": 123456789,
        "pack_id": "pack_123"
    })
    
    print(f"📦 Queued pack opening: {open_job_id}")
    
    # Check queue status
    status = queue_manager.get_queue_status()
    print(f"📊 Queue status: {status['queue_size']} jobs, {status['queue_utilization']:.1f}% full")
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check job status
    job_status = queue_manager.get_job_status(pack_job_id)
    print(f"📋 Job status: {job_status}")


if __name__ == "__main__":
    asyncio.run(example_usage())
