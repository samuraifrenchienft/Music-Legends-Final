# models/purchase_sqlalchemy.py
from sqlalchemy import Column, String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Purchase(Base):
    """SQLAlchemy Purchase Model"""
    
    __tablename__ = "purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, nullable=False)
    pack_type = Column(String(50), nullable=False)

    idempotency_key = Column(String(100), unique=True, nullable=False)

    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def exists(cls, session, key: str) -> bool:
        """Check if purchase with idempotency key exists"""
        return session.query(cls.id).filter_by(
            idempotency_key=key
        ).first() is not None
    
    @classmethod
    def find_by_key(cls, session, key: str):
        """Find purchase by idempotency key"""
        return session.query(cls).filter_by(
            idempotency_key=key
        ).first()
    
    @classmethod
    def create(cls, session, user_id: int, pack_type: str, idempotency_key: str):
        """Create new purchase"""
        if cls.exists(session, idempotency_key):
            return None
        
        purchase = cls(
            user_id=user_id,
            pack_type=pack_type,
            idempotency_key=idempotency_key
        )
        
        session.add(purchase)
        session.commit()
        return purchase
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'pack_type': self.pack_type,
            'idempotency_key': self.idempotency_key,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Test function (requires database session)
def test_purchase_model(session):
    """Test the SQLAlchemy Purchase model"""
    print("Testing SQLAlchemy Purchase Model...")
    
    # Test data
    user_id = 12345
    pack_type = "black"
    key = "test_payment_sqlalchemy_123"
    
    # First purchase
    purchase1 = Purchase.create(session, user_id, pack_type, key)
    print(f"Purchase 1: {purchase1.id if purchase1 else 'None'}")
    
    # Test exists
    exists = Purchase.exists(session, key)
    print(f"Exists: {exists}")
    
    # Duplicate purchase (should return None)
    purchase2 = Purchase.create(session, user_id, pack_type, key)
    print(f"Purchase 2: {purchase2.id if purchase2 else 'None'}")
    
    # Find by key
    found = Purchase.find_by_key(session, key)
    print(f"Found: {found.id if found else 'None'}")
    
    print("SQLAlchemy Purchase Model test complete!")

# SQLite version (without UUID)
class PurchaseSQLite(Base):
    """SQLite-compatible Purchase Model"""
    
    __tablename__ = "purchases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, nullable=False)
    pack_type = Column(String(50), nullable=False)

    idempotency_key = Column(String(100), unique=True, nullable=False)

    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def exists(cls, session, key: str) -> bool:
        """Check if purchase with idempotency key exists"""
        return session.query(cls.id).filter_by(
            idempotency_key=key
        ).first() is not None
    
    @classmethod
    def create(cls, session, user_id: int, pack_type: str, idempotency_key: str):
        """Create new purchase"""
        if cls.exists(session, idempotency_key):
            return None
        
        purchase = cls(
            user_id=user_id,
            pack_type=pack_type,
            idempotency_key=idempotency_key
        )
        
        session.add(purchase)
        session.commit()
        return purchase
