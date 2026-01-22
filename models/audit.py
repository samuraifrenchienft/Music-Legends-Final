# models/audit.py
from sqlalchemy import Column, String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class AuditLog(Base):
    """Minimal Audit Log Model"""
    
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event = Column(String(40), nullable=False)
    user_id = Column(BigInteger)
    target_id = Column(String(64))
    payload = Column(JSONB)
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

# SQLite version (without UUID and JSONB)
class AuditLogSQLite(Base):
    """SQLite-compatible Audit Log Model"""
    
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event = Column(String(40), nullable=False)
    user_id = Column(BigInteger)
    target_id = Column(String(64))
    payload = Column(String(2000))  # JSON string for SQLite
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def record(cls, session, event, user_id=None, target_id=None, **data):
        """Record an audit log entry (SQLite version)"""
        import json
        audit = cls(
            event=event,
            user_id=user_id,
            target_id=target_id,
            payload=json.dumps(data) if data else None
        )
        session.add(audit)
        session.commit()
        return audit
    
    def get_payload(self):
        """Get payload as dictionary (SQLite version)"""
        import json
        try:
            return json.loads(self.payload) if self.payload else {}
        except:
            return {}
    
    def set_payload(self, data):
        """Set payload from dictionary (SQLite version)"""
        import json
        self.payload = json.dumps(data) if data else None

# Test function
def test_audit_model():
    """Test the audit model functionality"""
    print("Testing Audit Model...")
    
    # Test creating an audit log
    audit = AuditLog(
        event="test_event",
        user_id=12345,
        target_id="test_target",
        payload={"key": "value", "number": 42}
    )
    
    print(f"Created audit log: {audit.id}")
    print(f"Event: {audit.event}")
    print(f"User ID: {audit.user_id}")
    print(f"Target ID: {audit.target_id}")
    print(f"Payload: {audit.payload}")
    print(f"Created at: {audit.created_at}")
    
    # Test to_dict
    audit_dict = audit.to_dict()
    print(f"Audit dict: {audit_dict}")
    
    print("Audit Model test complete!")

if __name__ == "__main__":
    test_audit_model()
