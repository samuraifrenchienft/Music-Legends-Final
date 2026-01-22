# models/drop.py
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import uuid

Base = declarative_base()

class Drop(Base):
    """Minimal Drop Model"""
    
    __tablename__ = "drops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(BigInteger, nullable=True)  # Can be None for unclaimed drops
    card_ids = Column(JSON)                       # [card1, card2, card3]
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
    def find_user_drops(cls, session, user_id):
        """Find drops claimed by a user"""
        return session.query(cls).filter(
            cls.owner_id == user_id,
            cls.resolved == True
        ).all()
    
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

# SQLite version (without UUID and JSON)
class DropSQLite(Base):
    """SQLite-compatible Drop Model"""
    
    __tablename__ = "drops"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(BigInteger, nullable=True)
    card_ids = Column(String(1000))  # JSON string for SQLite
    expires_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, default=False)

    @classmethod
    def create_drop(cls, session, card_ids, expires_minutes=30):
        """Create a new drop (SQLite version)"""
        import json
        drop = cls(
            card_ids=json.dumps(card_ids),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
            resolved=False
        )
        session.add(drop)
        session.commit()
        return drop
    
    @classmethod
    def find_unclaimed(cls, session):
        """Find unclaimed drops that haven't expired (SQLite version)"""
        return session.query(cls).filter(
            cls.owner_id.is_(None),
            cls.resolved == False,
            cls.expires_at > datetime.utcnow()
        ).first()
    
    @classmethod
    def claim_drop(cls, session, drop_id, user_id):
        """Claim a drop for a user (SQLite version)"""
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
    
    def get_card_ids(self):
        """Get card IDs as list (SQLite version)"""
        import json
        try:
            return json.loads(self.card_ids) if self.card_ids else []
        except:
            return []
    
    def set_card_ids(self, card_ids):
        """Set card IDs from list (SQLite version)"""
        import json
        self.card_ids = json.dumps(card_ids)

# Test function
def test_drop_model():
    """Test the drop model functionality"""
    print("Testing Drop Model...")
    
    # Test creating a drop
    card_ids = ["card1", "card2", "card3"]
    drop = Drop(
        card_ids=card_ids,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        resolved=False
    )
    
    print(f"Created drop: {drop.id}")
    print(f"Card IDs: {drop.card_ids}")
    print(f"Expires at: {drop.expires_at}")
    print(f"Resolved: {drop.resolved}")
    
    # Test to_dict
    drop_dict = drop.to_dict()
    print(f"Drop dict: {drop_dict}")
    
    print("Drop Model test complete!")

if __name__ == "__main__":
    test_drop_model()
