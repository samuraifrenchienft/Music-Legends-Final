# models/audit.py
from sqlalchemy import Column, String, BigInteger, DateTime
from datetime import datetime
import uuid
import json
from models import Base, UUIDType, JSONType

class AuditLog(Base):
    """Minimal Audit Log Model"""
    
    __tablename__ = "audit_logs"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    event = Column(String(40), nullable=False)
    user_id = Column(BigInteger)
    target_id = Column(String(64))
    payload = Column(JSONType)
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def record(cls, session, event, user_id=None, target_id=None, **data):
        """Record an audit log entry"""
        audit = cls(
            event=event,
            user_id=user_id,
            target_id=target_id,
            payload=data
        )
        session.add(audit)
        session.commit()
        return audit
    
    @classmethod
    def record_trade(cls, session, trade_id, user_a, user_b, cards_a, cards_b, gold_a, gold_b):
        """Record a trade event"""
        return cls.record(
            session,
            event="trade_completed",
            user_id=user_a,
            target_id=trade_id,
            trade_id=trade_id,
            user_a=user_a,
            user_b=user_b,
            cards_a=cards_a,
            cards_b=cards_b,
            gold_a=gold_a,
            gold_b=gold_b
        )
    
    @classmethod
    def record_drop(cls, session, drop_id, user_id, card_ids):
        """Record a drop claim event"""
        return cls.record(
            session,
            event="drop_claimed",
            user_id=user_id,
            target_id=drop_id,
            drop_id=drop_id,
            card_ids=card_ids
        )
    
    @classmethod
    def record_purchase(cls, session, purchase_id, user_id, pack_type, amount):
        """Record a purchase event"""
        return cls.record(
            session,
            event="purchase_completed",
            user_id=user_id,
            target_id=purchase_id,
            purchase_id=purchase_id,
            pack_type=pack_type,
            amount=amount
        )
    
    @classmethod
    def record_trade_cancelled(cls, session, trade_id, user_id, reason="timeout"):
        """Record a trade cancellation event"""
        return cls.record(
            session,
            event="trade_cancelled",
            user_id=user_id,
            target_id=trade_id,
            trade_id=trade_id,
            reason=reason
        )
    
    @classmethod
    def record_pack_opened(cls, session, user_id, pack_type, cards_received):
        """Record a pack opening event"""
        return cls.record(
            session,
            event="pack_opened",
            user_id=user_id,
            target_id=f"pack_{user_id}_{datetime.utcnow().timestamp()}",
            pack_type=pack_type,
            cards_received=cards_received
        )
    
    @classmethod
    def get_user_activity(cls, session, user_id, limit=50):
        """Get audit logs for a specific user"""
        return session.query(cls).filter(
            cls.user_id == user_id
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_event_logs(cls, session, event, limit=100):
        """Get audit logs for a specific event type"""
        return session.query(cls).filter(
            cls.event == event
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_recent_logs(cls, session, limit=100):
        """Get recent audit logs"""
        return session.query(cls).order_by(
            cls.created_at.desc()
        ).limit(limit).all()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'event': self.event,
            'user_id': self.user_id,
            'target_id': self.target_id,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }