# tests/test_queue.py
import asyncio
import unittest.mock as mock
from rq_queue.redis_connection import QUEUES
from rq_queue.tasks import task_open_pack
import uuid

async def test_pack_spam():
    """Test pack opening spam protection"""
    user_id = 12345
    
    # Simulate multiple pack openings
    job_ids = []
    
    for i in range(3):
        job_id = str(uuid.uuid4())
        job_ids.append(job_id)
        
        # Enqueue pack opening
        QUEUES["pack-queue"].enqueue(
            task_open_pack,
            user_id,
            "black",  # Use correct pack type
            None,
            job_id=job_id
        )
    
    print(f"Enqueued {len(job_ids)} pack openings:")
    for job_id in job_ids:
        print(f"  - Job {job_id}")
    
    return job_ids

async def test_concurrent_pack_opening():
    """Test concurrent pack opening with locking"""
    user_id = 12345
    
    # Test concurrent execution
    tasks = []
    for i in range(3):
        job_id = str(uuid.uuid4())
        task = asyncio.create_task(
            simulate_pack_opening(user_id, "black", job_id)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print("Concurrent pack opening results:")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  - Task {i}: ERROR - {result}")
        else:
            print(f"  - Task {i}: SUCCESS - {result}")
    
    return results

async def simulate_pack_opening(user_id, pack_type, job_id):
    """Simulate pack opening task"""
    try:
        result = task_open_pack(user_id, pack_type, None, job_id)
        return result
    except Exception as e:
        return {"error": str(e), "job_id": job_id}

# Run the test
if __name__ == "__main__":
    print("Testing pack queue spam protection...")
    
    # Test 1: Queue spam
    print("\n=== Test 1: Queue Spam ===")
    job_ids = asyncio.run(test_pack_spam())
    
    # Test 2: Concurrent execution
    print("\n=== Test 2: Concurrent Execution ===")
    results = asyncio.run(test_concurrent_pack_opening())
    
    print("\n=== Test Complete ===")
