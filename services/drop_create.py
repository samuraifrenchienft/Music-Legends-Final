# services/drop_create.py
from datetime import datetime, timedelta
from models.drop import Drop, DropSQLite

CLAIM_WINDOW = 1.0   # seconds

def create_drop(owner_id, cards):
    """
    Create a new drop with cards and expiration
    
    Args:
        owner_id: The owner of the drop (can be None for unclaimed)
        cards: List of card objects with .id attribute
    
    Returns:
        Drop object
    """
    return Drop.create(
        owner_id=owner_id,
        card_ids=[c.id for c in cards],
        expires_at=datetime.utcnow() + timedelta(seconds=CLAIM_WINDOW)
    )

def create_drop_with_session(session, owner_id, cards, expires_seconds=None):
    """
    Create a new drop with database session
    
    Args:
        session: Database session
        owner_id: The owner of the drop (can be None)
        cards: List of card objects with .id attribute
        expires_seconds: Custom expiration time (defaults to CLAIM_WINDOW)
    
    Returns:
        DropSQLite object
    """
    if expires_seconds is None:
        expires_seconds = CLAIM_WINDOW
    
    drop = DropSQLite(
        owner_id=owner_id,
        card_ids=[c.id for c in cards],
        expires_at=datetime.utcnow() + timedelta(seconds=expires_seconds)
    )
    
    session.add(drop)
    session.commit()
    return drop

def create_unclaimed_drop(cards):
    """
    Create an unclaimed drop (no owner)
    
    Args:
        cards: List of card objects with .id attribute
    
    Returns:
        Drop object
    """
    return create_drop(owner_id=None, cards=cards)

def create_owner_drop(owner_id, cards):
    """
    Create a drop with an owner
    
    Args:
        owner_id: The owner's user ID
        cards: List of card objects with .id attribute
    
    Returns:
        Drop object
    """
    return create_drop(owner_id=owner_id, cards=cards)

# Mock card class for testing
class MockCard:
    def __init__(self, card_id):
        self.id = card_id

# Test the drop creation
def test_drop_creation():
    """Test drop creation functionality"""
    print("Testing Drop Creation...")
    
    # Create mock cards
    cards = [MockCard("card1"), MockCard("card2"), MockCard("card3")]
    
    # Test unclaimed drop
    unclaimed_drop = create_unclaimed_drop(cards)
    print(f"Unclaimed drop: {unclaimed_drop.id}")
    print(f"Owner: {unclaimed_drop.owner_id}")
    print(f"Card IDs: {unclaimed_drop.card_ids}")
    
    # Test owner drop
    owner_drop = create_owner_drop(12345, cards)
    print(f"Owner drop: {owner_drop.id}")
    print(f"Owner: {owner_drop.owner_id}")
    print(f"Card IDs: {owner_drop.card_ids}")
    
    print("Drop creation test complete!")

if __name__ == "__main__":
    test_drop_creation()
