# models/card.py
import uuid
from datetime import datetime

class Card:
    """Minimal Card Model for testing"""
    
    _storage = {}  # Simple in-memory storage for testing
    
    def __init__(self, user_id: int, artist_id: int, tier: str, serial: str, purchase_id: str = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.artist_id = artist_id
        self.tier = tier
        self.serial = serial
        self.purchase_id = purchase_id
        self.revoked = False
        self.created_at = datetime.now()
    
    @classmethod
    def create(cls, user_id: int, artist_id: int, tier: str, serial: str, purchase_id: str = None):
        """Create new card"""
        card = cls(user_id, artist_id, tier, serial, purchase_id)
        cls._storage[card.id] = card
        return card
    
    @classmethod
    def from_purchase(cls, purchase_id: str):
        """Get all cards from a purchase"""
        return [card for card in cls._storage.values() if card.purchase_id == purchase_id and not card.revoked]
    
    @classmethod
    def get_by_user(cls, user_id: int):
        """Get all cards for a user"""
        return [card for card in cls._storage.values() if card.user_id == user_id and not card.revoked]
    
    def revoke(self):
        """Revoke this card"""
        self.revoked = True
    
    def artist(self):
        """Get artist information (mock)"""
        class MockArtist:
            def __init__(self, artist_id):
                self.id = artist_id
                self.name = f"Artist {artist_id}"
                self.image_url = f"https://example.com/artist_{artist_id}.jpg"
        
        return MockArtist(self.artist_id)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'artist_id': self.artist_id,
            'tier': self.tier,
            'serial': self.serial,
            'purchase_id': self.purchase_id,
            'revoked': self.revoked,
            'created_at': self.created_at.isoformat()
        }

# Test the model
if __name__ == "__main__":
    print("Testing Card Model...")
    
    # Test card creation
    card1 = Card.create(12345, 1, "legendary", "LEG-001", "sess_123")
    print(f"Card 1: {card1.id if card1 else 'None'}")
    
    # Test from_purchase
    cards = Card.from_purchase("sess_123")
    print(f"Cards from purchase: {len(cards)}")
    
    # Test revoke
    if cards:
        cards[0].revoke()
        print(f"Card revoked: {cards[0].revoked}")
    
    print("Card Model test complete!")
