# handlers/purchase_sqlalchemy_handler.py
import logging
from models.purchase_sqlalchemy import Purchase, PurchaseSQLite
from rq_queue.redis_connection import QUEUES
from rq_queue.tasks import task_open_pack

def handle_purchase_sqlalchemy(session, user_id: int, pack_type: str, key: str) -> str:
    """SQLAlchemy purchase handler"""
    
    # Check if already processed
    if Purchase.exists(session, key):
        return "already processed"
    
    # Create new purchase
    purchase = Purchase.create(session, user_id, pack_type, key)
    if not purchase:
        return "creation failed"
    
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
        session.commit()
        
        return f"processed: {purchase.id}"
        
    except Exception as e:
        logging.error(f"Queue error: {e}")
        purchase.status = "failed"
        session.commit()
        return f"queue error: {e}"

def handle_purchase_sqlite(session, user_id: int, pack_type: str, key: str) -> str:
    """SQLite-compatible purchase handler"""
    
    # Check if already processed
    if PurchaseSQLite.exists(session, key):
        return "already processed"
    
    # Create new purchase
    purchase = PurchaseSQLite.create(session, user_id, pack_type, key)
    if not purchase:
        return "creation failed"
    
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
        session.commit()
        
        return f"processed: {purchase.id}"
        
    except Exception as e:
        logging.error(f"Queue error: {e}")
        purchase.status = "failed"
        session.commit()
        return f"queue error: {e}"

# Test setup function
def setup_sqlite_session():
    """Setup SQLite session for testing"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:', echo=True)
    
    # Create tables
    from models.purchase_sqlalchemy import Base
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    return Session()

def test_sqlalchemy_handler():
    """Test the SQLAlchemy purchase handler"""
    print("Testing SQLAlchemy Purchase Handler...")
    
    # Setup database session
    session = setup_sqlite_session()
    
    try:
        # Test data
        user_id = 12345
        pack_type = "black"
        key = "test_payment_sqlalchemy_456"
        
        # First purchase
        result1 = handle_purchase_sqlite(session, user_id, pack_type, key)
        print(f"First purchase: {result1}")
        
        # Duplicate purchase
        result2 = handle_purchase_sqlite(session, user_id, pack_type, key)
        print(f"Duplicate purchase: {result2}")
        
        # Different purchase
        key2 = "test_payment_sqlalchemy_789"
        result3 = handle_purchase_sqlite(session, user_id, pack_type, key2)
        print(f"Different purchase: {result3}")
        
        # Check database state
        all_purchases = session.query(PurchaseSQLite).all()
        print(f"Total purchases in DB: {len(all_purchases)}")
        
        for purchase in all_purchases:
            print(f"  - {purchase.id}: {purchase.pack_type} ({purchase.status})")
        
    finally:
        session.close()
    
    print("SQLAlchemy Purchase Handler test complete!")

if __name__ == "__main__":
    test_sqlalchemy_handler()
