# queue/worker.py
import logging
import os
from rq import Worker, Connection
from rq_queue.redis_connection import get_redis_connection, QUEUES
from rq.job import Job
from rq.exceptions import NoSuchJobError

def start_worker():
    """Start RQ worker"""
    redis_conn = get_redis_connection()
    
    logging.info("Starting RQ worker...")
    
    try:
        with Connection(redis_conn):
            # Create worker with all queues
            worker = Worker(
                queues=list(QUEUES.values()),
                connection=redis_conn,
                default_worker_ttl=43200,  # 12 hours
                job_monitoring_interval=10,
                log_job_description=True
            )
            
            logging.info("Worker started, processing jobs...")
            worker.work(with_scheduler=True)
            
    except Exception as e:
        logging.error(f"Worker error: {e}")
        raise

class CustomWorker(Worker):
    """Custom worker with enhanced error handling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failure_ttl = 300  # 5 minutes for failed jobs
    
    def perform_job(self, job: Job):
        """Perform job with enhanced error handling"""
        try:
            super().perform_job(job)
            logging.info(f"Successfully completed job {job.id}")
            
        except Exception as e:
            logging.error(f"Job {job.id} failed: {e}")
            
            # Move to dead letter queue after 3 failures
            if job.meta.get('failure_count', 0) >= 3:
                self.move_to_dlq(job)
                logging.warning(f"Moved job {job.id} to DLQ after 3 failures")
            else:
                # Increment failure count and retry
                job.meta['failure_count'] = job.meta.get('failure_count', 0) + 1
                raise
    
    def move_to_dlq(self, job: Job):
        """Move job to dead letter queue"""
        from rq import Queue
        
        dlq = Queue('dead-letter-queue', connection=self.connection)
        dlq.enqueue(job.origin, job.description, job.args, job.kwargs)
        
        # Delete from original queue
        job.cancel()

def start_custom_worker():
    """Start custom worker with enhanced error handling"""
    redis_conn = get_redis_connection()
    
    logging.info("Starting custom RQ worker...")
    
    try:
        with Connection(redis_conn):
            worker = CustomWorker(
                queues=list(QUEUES.values()),
                connection=redis_conn
            )
            
            logging.info("Custom worker started, processing jobs...")
            worker.work(with_scheduler=True)
            
    except Exception as e:
        logging.error(f"Custom worker error: {e}")
        raise

# Import required modules
import time
