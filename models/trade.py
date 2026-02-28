# models/trade.py
from sqlalchemy import Column, String, BigInteger, Integer, DateTime
import uuid
from datetime import datetime, timedelta
from models import Base, UUIDType, JSONType

class Trade(Base):
    """Minimal Trade Model for Escrow System"""
    
    __tablename__ = "trades"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    user_a = Column(BigInteger, nullable=False)
    user_b = Column(BigInteger, nullable=False)

    cards_a = Column(JSONType, default=list)
    cards_b = Column(JSONType, default=list)

    gold_a = Column(Integer, default=0)
    gold_b = Column(Integer, default=0)

    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    @classmethod
    def create_trade(cls, session, user_a, user_b, cards_a=None, cards_b=None, gold_a=0, gold_b=0, timeout_minutes=5):
        """Create a new trade"""
        trade = cls(
            user_a=user_a,
            user_b=user_b,
            cards_a=cards_a or [],
            cards_b=cards_b or [],
            gold_a=gold_a,
            gold_b=gold_b,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(minutes=timeout_minutes)
        )
        session.add(trade)
        session.commit()
        return trade
    
    @classmethod
    def get_pending_trades(cls, session, user_id):
        """Get pending trades for a user"""
        return session.query(cls).filter(
            cls.status == "pending",
            (cls.user_a == user_id) | (cls.user_b == user_id)
        ).all()
    
    @classmethod
    def get_trade(cls, session, trade_id):
        """Get trade by ID"""
        return session.query(cls).filter(cls.id == trade_id).first()
    
    def is_expired(self):
        """Check if trade is expired"""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'user_a': self.user_a,
            'user_b': self.user_b,
            'cards_a': self.cards_a,
            'cards_b': self.cards_b,
            'gold_a': self.gold_a,
            'gold_b': self.gold_b,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }


# Alias for backward compatibility
TradeSQLite = Trade
