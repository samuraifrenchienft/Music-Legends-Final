# rq_queue/redis_connection.py
import redis
from rq import Queue
import os

# Redis connection
redis_conn = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

# Define all queues
QUEUES = {
    "pack": Queue("pack-queue", connection=redis_conn),
    "trade": Queue("trade-queue", connection=redis_conn),
    "drop": Queue("drop-queue", connection=redis_conn),
    "burn": Queue("burn-queue", connection=redis_conn),
    "event": Queue("event-queue", connection=redis_conn),
}

def get_redis_connection():
    """Get Redis connection"""
    return redis_conn
