# services/purchase_service.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from rq_queue.redis_connection import QUEUES
from rq_queue.tasks import task_open_pack

class Purchase:
    """Purchase model for Founder Packs"""
    
    def __init__(self, user_id: int, pack_type: str, idempotency_key: str, amount_cents: int = None, currency: str = 'USD'):
        self.id = None  # Will be set by database (UUID as CHAR(36))
        self.user_id = user_id
        self.pack_type = pack_type
        self.idempotency_key = idempotency_key
        self.status = "pending"  # pending | delivered
        self.amount_cents = amount_cents
        self.currency = currency
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def save(self):
        """Save purchase to SQLite database"""
        # This would save to your SQLite database
        # INSERT or UPDATE purchases SET ...
        logging.info(f"Purchase saved: {self.id} - {self.status} - {self.amount_cents} {self.currency}")
    
    @classmethod
    def find_by_key(cls, key: str) -> Optional['Purchase']:
        """Find purchase by idempotency key"""
        # This would query your SQLite database
        # SELECT * FROM purchases WHERE idempotency_key = ?
        return None
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'pack_type': self.pack_type,
            'idempotency_key': self.idempotency_key,
            'status': self.status,
            'amount_cents': self.amount_cents,
            'currency': self.currency,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

def handle_purchase(user_id: int, pack_type: str, key: str, amount_cents: int = None) -> Purchase:
    """Handle Founder Pack purchase with idempotency"""
    logging.info(f"Processing purchase: {key} for user {user_id}")
    
    purchase = None
    try:
        # Check if already processed
        existing = Purchase.find_by_key(key)
        if existing:
            logging.info(f"Purchase already processed: {key}")
            return existing
        
        # Create new purchase
        purchase = Purchase(
            user_id=user_id,
            pack_type=pack_type,
            idempotency_key=key,
            amount_cents=amount_cents
        )
        purchase.save()
        
        # Queue pack opening
        QUEUES["pack-queue"].enqueue(
            task_open_pack,
            user_id,
            pack_type,
            None,
            job_id=key
        )
        
        # Mark as delivered
        purchase.status = "delivered"
        purchase.updated_at = datetime.now()
        purchase.save()
        
        # TODO: Add cards to purchase_cards table when pack is opened
        # This would be handled in the task_open_pack function
        
        logging.info(f"Purchase delivered: {key}")
        return purchase
        
    except Exception as e:
        logging.error(f"Purchase failed: {key} - {e}")
        if purchase:
            purchase.status = "failed"
            purchase.updated_at = datetime.now()
            purchase.save()
        raise

def add_cards_to_purchase(purchase_id: str, card_ids: list):
    """Add awarded cards to purchase record"""
    try:
        # This would insert into purchase_cards table
        # INSERT INTO purchase_cards (purchase_id, card_id) VALUES (?, ?)
        logging.info(f"Added {len(card_ids)} cards to purchase {purchase_id}")
        
        for card_id in card_ids:
            # Add each card to the purchase
            pass
            
    except Exception as e:
        logging.error(f"Failed to add cards to purchase {purchase_id}: {e}")
        raise

# Stripe webhook handler
async def on_payment(event: Dict[str, Any]):
    """Handle Stripe payment webhook"""
    try:
        payment_id = event.get("payment_id")
        user_id = event.get("user_id")
        pack_type = event.get("pack")
        
        if not all([payment_id, user_id, pack_type]):
            logging.error("Missing required webhook data")
            return
        
        logging.info(f"Payment webhook: {payment_id}")
        
        # Process the purchase
        purchase = handle_purchase(
            user_id=user_id,
            pack_type=pack_type,
            key=payment_id
        )
        
        logging.info(f"Purchase processed: {purchase.idempotency_key}")
        
    except Exception as e:
        logging.error(f"Webhook processing failed: {e}")
        raise

# Test function
def test_purchase_service():
    """Test the purchase service"""
    print("Testing purchase service...")
    
    # Test idempotency
    key = "test_payment_123"
    user_id = 12345
    pack_type = "black"
    amount_cents = 999  # $9.99
    
    # First purchase
    purchase1 = handle_purchase(user_id, pack_type, key, amount_cents)
    print(f"First purchase: {purchase1.idempotency_key} - {purchase1.status} - {purchase1.amount_cents} {purchase1.currency}")
    
    # Duplicate purchase (should return existing)
    purchase2 = handle_purchase(user_id, pack_type, key, amount_cents)
    print(f"Duplicate purchase: {purchase2.idempotency_key} - {purchase2.status} - {purchase2.amount_cents} {purchase2.currency}")
    
    print("Purchase service test complete!")

if __name__ == "__main__":
    test_purchase_service()
