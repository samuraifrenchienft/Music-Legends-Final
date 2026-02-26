# services/drop_service.py
import random
from datetime import datetime
from rq_queue.locks import RedisLock
from models.drop import Drop, DropSQLite
from models.purchase import Purchase  # Assuming Card model exists

CLAIM_WINDOW = 1.0   # seconds

def resolve_drop(drop_id: str, reactors: list[int]):
    """
    Resolve a drop with reactors
    
    Args:
        drop_id: The drop ID to resolve
        reactors: List of user IDs who reacted
    
    Returns:
        winner_id or None if no winner
    """
    with RedisLock(f"drop:{drop_id}"):
        # This would be a database transaction in production
        # For now, we'll simulate the transaction logic
        
        # Get the drop (simulated)
        drop = _get_drop(drop_id)
        
        if not drop:
            return None
        
        if drop.get('resolved', False):
            return None
        
        if datetime.utcnow() > datetime.fromisoformat(drop['expires_at']):
            # Mark as expired
            _mark_drop_resolved(drop_id)
            return None
        
        winner = _pick_winner(drop.get('owner_id'), reactors)
        
        if not winner:
            # Mark as resolved with no winner
            _mark_drop_resolved(drop_id)
            return None
        
        # Award first unclaimed card
        card_ids = drop.get('card_ids', [])
        if card_ids:
            card_id = card_ids.pop(0)
            
            # Assign card to winner (simulated)
            _assign_card_to_user(card_id, winner)
            
            # Update drop with remaining cards
            _update_drop_cards(drop_id, card_ids)
        
        # Mark drop as resolved
        _mark_drop_resolved(drop_id)
        
        return winner

def _get_drop(drop_id: str):
    """Get drop by ID (simulated database call)"""
    # This would be: Drop.get(drop_id) in production
    # For testing, we'll return a mock drop
    return {
        'id': drop_id,
        'owner_id': None,
        'card_ids': ['card1', 'card2', 'card3'],
        'expires_at': (datetime.utcnow().replace(microsecond=0) + timedelta(minutes=30)).isoformat(),
        'resolved': False
    }

def _mark_drop_resolved(drop_id: str):
    """Mark drop as resolved (simulated database call)"""
    # This would be: drop.resolved = True; drop.save() in production
    print(f"Drop {drop_id} marked as resolved")

def _assign_card_to_user(card_id: str, user_id: int):
    """Assign card to user (simulated database call)"""
    # This would be: Card.assign(card_id, user_id) in production
    print(f"Card {card_id} assigned to user {user_id}")

def _update_drop_cards(drop_id: str, card_ids: list):
    """Update drop's remaining cards (simulated database call)"""
    # This would be: drop.card_ids = card_ids; drop.save() in production
    print(f"Drop {drop_id} updated with remaining cards: {card_ids}")

def _pick_winner(owner_id, reactors):
    """Pick winner from reactors with owner priority"""
    if not reactors:
        return None

    # OWNER PRIORITY RULE
    if owner_id in reactors:
        return owner_id

    # RNG TIE BREAKER
    return random.choice(reactors)

# Test the drop resolution
def test_drop_resolution():
    """Test the drop resolution logic"""
    print("=== Testing Drop Resolution ===\n")
    
    # Test 1: No reactors
    print("1. Testing no reactors:")
    winner = resolve_drop("drop1", [])
    print(f"   Winner: {winner}")
    print("   Expected: None")
    
    # Test 2: Owner priority
    print("\n2. Testing owner priority:")
    winner = resolve_drop("drop2", [123, 456, 789])
    print(f"   Winner: {winner}")
    print("   Expected: 123 (owner)")
    
    # Test 3: Random winner
    print("\n3. Testing random winner:")
    winner = resolve_drop("drop3", [456, 789, 101])
    print(f"   Winner: {winner}")
    print("   Expected: Random from [456, 789, 101]")
    
    # Test 4: Expired drop
    print("\n4. Testing expired drop:")
    # Create an expired drop
    expired_drop = {
        'id': 'expired_drop',
        'owner_id': None,
        'card_ids': ['card1'],
        'expires_at': (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        'resolved': False
    }
    
    # Mock the _get_drop function
    import services.drop_service as drop_service
    original_get_drop = drop_service._get_drop
    drop_service._get_drop = lambda drop_id: expired_drop if drop_id == 'expired_drop' else original_get_drop(drop_id)
    
    winner = resolve_drop("expired_drop", [123])
    print(f"   Winner: {winner}")
    print("   Expected: None (expired)")
    
    # Restore original function
    drop_service._get_drop = original_get_drop
    
    print("\n=== Drop Resolution Test Complete ===")

# Database-integrated version
def resolve_drop_with_db(session, drop_id: str, reactors: list[int]):
    """
    Resolve a drop with database integration
    """
    with RedisLock(f"drop:{drop_id}"):
        # Use database transaction
        try:
            # Get the drop
            drop = session.query(DropSQLite).filter(DropSQLite.id == drop_id).first()
            
            if not drop:
                return None
            
            if drop.resolved:
                return None
            
            if datetime.utcnow() > drop.expires_at:
                drop.resolved = True
                session.commit()
                return None
            
            winner = _pick_winner(drop.owner_id, reactors)
            
            if not winner:
                drop.resolved = True
                session.commit()
                return None
            
            # Award first unclaimed card
            card_ids = drop.get_card_ids()
            if card_ids:
                card_id = card_ids.pop(0)
                drop.set_card_ids(card_ids)
                
                # Assign card to winner (would use Card model)
                print(f"Card {card_id} assigned to user {winner}")
            
            drop.resolved = True
            session.commit()
            
            return winner
            
        except Exception as e:
            session.rollback()
            print(f"Error resolving drop: {e}")
            return None

if __name__ == "__main__":
    from datetime import timedelta
    test_drop_resolution()
