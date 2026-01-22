# handlers/purchase_handler.py
import logging
from models.purchase import Purchase
from rq_queue.redis_connection import QUEUES
from rq_queue.tasks import task_open_pack

def handle_purchase(user_id: int, pack_type: str, key: str) -> str:
    """Minimal purchase handler for testing uniqueness"""
    
    # Check if already processed
    if Purchase.exists(key):
        return "already processed"
    
    # Create new purchase
    purchase = Purchase.create(user_id, pack_type, key)
    if not purchase:
        return "creation failed"
    
    # Save purchase
    purchase.save()
    
    # Queue pack opening
    try:
        QUEUES["pack-queue"].enqueue(
            task_open_pack,
            user_id,
            pack_type,
            None,
            job_id=key
        )
        
        # Mark as delivered
        purchase.status = "delivered"
        purchase.save()
        
        return f"processed: {purchase.id}"
        
    except Exception as e:
        logging.error(f"Queue error: {e}")
        purchase.status = "failed"
        purchase.save()
        return f"queue error: {e}"

# Test the handler
def test_purchase_handler():
    """Test the minimal purchase handler"""
    print("Testing Purchase Handler...")
    
    # Test data
    user_id = 12345
    pack_type = "black"
    key = "test_payment_456"
    
    # First purchase
    result1 = handle_purchase(user_id, pack_type, key)
    print(f"First purchase: {result1}")
    
    # Duplicate purchase
    result2 = handle_purchase(user_id, pack_type, key)
    print(f"Duplicate purchase: {result2}")
    
    # Different purchase
    key2 = "test_payment_789"
    result3 = handle_purchase(user_id, pack_type, key2)
    print(f"Different purchase: {result3}")
    
    print("Purchase Handler test complete!")

if __name__ == "__main__":
    test_purchase_handler()
