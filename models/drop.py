# models/drop.py
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean
from datetime import datetime, timedelta
import uuid
import json
from models import Base, UUIDType, JSONType

class Drop(Base):
    """Minimal Drop Model"""
    
    __tablename__ = "drops"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    owner_id = Column(BigInteger, nullable=True)  # Can be None for unclaimed drops
    card_ids = Column(JSONType)                       # [card1, card2, card3]
    expires_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, default=False)

    @classmethod
    def create_drop(cls, session, card_ids, expires_minutes=30):
        """Create a new drop"""
        drop = cls(
            card_ids=card_ids,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
            resolved=False
        )
        session.add(drop)
        session.commit()
        return drop
    
    @classmethod
    def find_unclaimed(cls, session):
        """Find unclaimed drops that haven't expired"""
        return session.query(cls).filter(
            cls.owner_id.is_(None),
            cls.resolved == False,
            cls.expires_at > datetime.utcnow()
        ).first()
    
    @classmethod
    def claim_drop(cls, session, drop_id, user_id):
        """Claim a drop for a user"""
        drop = session.query(cls).filter(
            cls.id == drop_id,
            cls.owner_id.is_(None),
            cls.resolved == False,
            cls.expires_at > datetime.utcnow()
        ).first()
        
        if drop:
            drop.owner_id = user_id
            drop.resolved = True
            session.commit()
            return drop
        
        return None
    
    @classmethod
    def cleanup_expired(cls, session):
        """Clean up expired drops"""
        expired_count = session.query(cls).filter(
            cls.expires_at <= datetime.utcnow(),
            cls.resolved == False
        ).count()
        
        # Delete expired drops
        session.query(cls).filter(
            cls.expires_at <= datetime.utcnow(),
            cls.resolved == False
        ).delete()
        
        session.commit()
        return expired_count
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'owner_id': self.owner_id,
            'card_ids': self.card_ids,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'resolved': self.resolved,
            'is_expired': self.expires_at <= datetime.utcnow() if self.expires_at else False
        }
# Alias for backward compatibility
DropSQLite = Drop
