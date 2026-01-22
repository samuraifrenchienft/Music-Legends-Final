# models/trade.py
from sqlalchemy import Column, String, BigInteger, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import uuid

Base = declarative_base()

class Trade(Base):
    """Minimal Trade Model for Escrow System"""
    
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_a = Column(BigInteger, nullable=False)
    user_b = Column(BigInteger, nullable=False)

    cards_a = Column(JSON, default=list)
    cards_b = Column(JSON, default=list)

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

# SQLite version (without UUID and JSON)
class TradeSQLite(Base):
    """SQLite-compatible Trade Model"""
    
    __tablename__ = "trades"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_a = Column(BigInteger, nullable=False)
    user_b = Column(BigInteger, nullable=False)
    cards_a = Column(String(1000), default="[]")  # JSON string
    cards_b = Column(String(1000), default="[]")  # JSON string
    gold_a = Column(Integer, default=0)
    gold_b = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    def get_cards_a(self):
        """Get cards_a as list"""
        import json
        try:
            return json.loads(self.cards_a) if self.cards_a else []
        except:
            return []
    
    def set_cards_a(self, cards):
        """Set cards_a from list"""
        import json
        self.cards_a = json.dumps(cards)
    
    def get_cards_b(self):
        """Get cards_b as list"""
        import json
        try:
            return json.loads(self.cards_b) if self.cards_b else []
        except:
            return []
    
    def set_cards_b(self, cards):
        """Set cards_b from list"""
        import json
        self.cards_b = json.dumps(cards)

# Test function
def test_trade_model():
    """Test the trade model functionality"""
    print("Testing Trade Model...")
    
    # Test creating a trade
    trade = Trade(
        user_a=12345,
        user_b=67890,
        cards_a=["card1", "card2"],
        cards_b=["card3"],
        gold_a=100,
        gold_b=200,
        status="pending"
    )
    
    print(f"Created trade: {trade.id}")
    print(f"User A: {trade.user_a}")
    print(f"User B: {trade.user_b}")
    print(f"Cards A: {trade.cards_a}")
    print(f"Cards B: {trade.cards_b}")
    print(f"Gold A: {trade.gold_a}")
    print(f"Gold B: {trade.gold_b}")
    print(f"Status: {trade.status}")
    
    # Test to_dict
    trade_dict = trade.to_dict()
    print(f"Trade dict: {trade_dict}")
    
    print("Trade Model test complete!")

if __name__ == "__main__":
    test_trade_model()
