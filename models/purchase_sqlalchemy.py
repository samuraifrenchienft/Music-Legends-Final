# models/purchase_sqlalchemy.py
from sqlalchemy import Column, String, BigInteger, DateTime
from datetime import datetime
import uuid
from models import Base, UUIDType

class Purchase(Base):
    """SQLAlchemy Purchase Model"""
    
    __tablename__ = "purchases"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
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