# models/purchase.py
import uuid
from datetime import datetime

class Purchase:
    """Minimal Purchase Model for testing"""
    
    _storage = {}  # Simple in-memory storage for testing
    
    def __init__(self, user_id: int, pack_type: str, payment_id: str, amount: int = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.pack_type = pack_type
        self.payment_id = payment_id
        self.amount = amount or 999  # Default amount in cents
        self.status = "pending"
        self.created_at = datetime.now()
    
    @classmethod
    def exists(cls, payment_id: str) -> bool:
        """Check if purchase with payment ID exists"""
        return payment_id in cls._storage
    
    @classmethod
    def create(cls, user_id: int, pack_type: str, payment_id: str, amount: int = None):
        """Create new purchase"""
        if cls.exists(payment_id):
            return None
        
        purchase = cls(user_id, pack_type, payment_id, amount)
        purchase.status = "completed"
        cls._storage[payment_id] = purchase
        return purchase
    
    @classmethod
    def get_by_payment_id(cls, payment_id: str):
        """Find purchase by payment ID"""
        return cls._storage.get(payment_id)
    
    @classmethod
    def find_by_key(cls, key: str):
        """Find purchase by idempotency key (legacy method)"""
        return cls._storage.get(key)
    
    def save(self):
        """Save purchase (already in storage)"""
        self._storage[self.payment_id] = self
    
    def update_status(self, status: str):
        """Update purchase status"""
        self.status = status
        self.save()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'pack_type': self.pack_type,
            'payment_id': self.payment_id,
            'amount': self.amount,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

# Test the model
if __name__ == "__main__":
    print("Testing Purchase Model...")
    
    # Test uniqueness
    key = "test_payment_123"
    user_id = 12345
    pack_type = "black"
    
    # First purchase
    purchase1 = Purchase.create(user_id, pack_type, key)
    print(f"Purchase 1: {purchase1.id if purchase1 else 'None'}")
    
    # Test exists
    print(f"Exists: {Purchase.exists(key)}")
    
    # Duplicate purchase (should return None)
    purchase2 = Purchase.create(user_id, pack_type, key)
    print(f"Purchase 2: {purchase2.id if purchase2 else 'None'}")
    
    # Find by key
    found = Purchase.find_by_key(key)
    print(f"Found: {found.id if found else 'None'}")
    
    print("Purchase Model test complete!")
