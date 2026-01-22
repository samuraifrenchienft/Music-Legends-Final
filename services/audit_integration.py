# services/audit_integration.py
"""
Examples of where to call AuditLog.record() throughout the system
"""
from models.audit import AuditLog

# C) Trade Finalize Integration
def log_trade_finalize(trade):
    """
    Log trade finalization event
    
    Args:
        trade: Trade object with all details
    """
    AuditLog.record(
        event="trade_complete",
        user_id=trade.user_a,
        target_id=str(trade.id),
        cards_a=trade.cards_a,
        cards_b=trade.cards_b,
        user_a=trade.user_a,
        user_b=trade.user_b,
        gold_a=getattr(trade, 'gold_a', 0),
        gold_b=getattr(trade, 'gold_b', 0)
    )

# D) Card Burn Integration
def log_card_burn(user_id, card_id, dust):
    """
    Log card burning event
    
    Args:
        user_id: User who burned the card
        card_id: ID of the burned card
        dust: Amount of dust received
    """
    AuditLog.record(
        event="burn",
        user_id=user_id,
        target_id=card_id,
        dust=dust,
        card_id=card_id
    )

# E) Pack Opening Integration
def log_pack_opening(user_id, pack_type, cards):
    """
    Log pack opening event
    
    Args:
        user_id: The user who opened the pack
        pack_type: Type of pack opened (black, silver, etc.)
        cards: List of card objects received
    """
    AuditLog.record(
        event="pack_open",
        user_id=user_id,
        target_id=pack_type,
        cards=[c.serial for c in cards],
        pack_type=pack_type,
        card_count=len(cards)
    )

# F) Legendary Card Creation Integration
def log_legendary_creation(user_id, card, artist):
    """
    Log legendary card creation event
    
    Args:
        user_id: The user who created the legendary
        card: The legendary card object
        artist: The artist object
    """
    if card.tier == "legendary":
        AuditLog.record(
            event="legendary_created",
            user_id=user_id,
            target_id=artist.id,
            serial=card.serial,
            card_name=card.name,
            artist_name=artist.name,
            tier=card.tier
        )

# C) Trade Completion Integration
def log_trade_completion(session, trade):
    """
    Log trade completion event
    
    Args:
        session: Database session
        trade: Trade object with all details
    """
    AuditLog.record_trade(
        session,
        trade_id=str(trade.id),
        user_a=trade.user_a,
        user_b=trade.user_b,
        cards_a=trade.get_cards_a(),
        cards_b=trade.get_cards_b(),
        gold_a=trade.gold_a,
        gold_b=trade.gold_b
    )

# D) Trade Cancellation Integration
def log_trade_cancellation(session, trade_id, user_id, reason="timeout"):
    """
    Log trade cancellation event
    
    Args:
        session: Database session
        trade_id: The cancelled trade ID
        user_id: User who cancelled (or system for timeout)
        reason: Reason for cancellation
    """
    AuditLog.record_trade_cancelled(
        session,
        trade_id=trade_id,
        user_id=user_id,
        reason=reason
    )

# E) Drop Claim Integration
def log_drop_claim(session, drop_id, user_id, card_ids):
    """
    Log drop claim event
    
    Args:
        session: Database session
        drop_id: The claimed drop ID
        user_id: User who claimed the drop
        card_ids: List of card IDs received
    """
    AuditLog.record_drop(
        session,
        drop_id=drop_id,
        user_id=user_id,
        card_ids=card_ids
    )

# F) Purchase Integration
def log_purchase(session, purchase):
    """
    Log purchase completion event
    
    Args:
        session: Database session
        purchase: Purchase object
    """
    AuditLog.record_purchase(
        session,
        purchase_id=str(purchase.id),
        user_id=purchase.user_id,
        pack_type=purchase.pack_type,
        amount=purchase.amount_cents,
        currency=purchase.currency
    )

# G) User Login Integration
def log_user_login(user_id, ip_address=None):
    """
    Log user login event
    
    Args:
        user_id: User who logged in
        ip_address: Optional IP address
    """
    data = {"login_time": datetime.utcnow().isoformat()}
    if ip_address:
        data["ip_address"] = ip_address
    
    AuditLog.record(
        event="user_login",
        user_id=user_id,
        **data
    )

# H) User Registration Integration
def log_user_registration(user_id, username, discord_id):
    """
    Log user registration event
    
    Args:
        user_id: New user's ID
        username: Username
        discord_id: Discord user ID
    """
    AuditLog.record(
        event="user_registered",
        user_id=user_id,
        target_id=discord_id,
        username=username,
        discord_id=discord_id
    )

# I) Card Creation Integration
def log_card_creation(user_id, card):
    """
    Log card creation event
    
    Args:
        user_id: User who created the card
        card: Card object
    """
    AuditLog.record(
        event="card_created",
        user_id=user_id,
        target_id=card.serial,
        serial=card.serial,
        card_name=card.name,
        tier=card.tier,
        rarity=card.rarity
    )

# J) Gold Transaction Integration
def log_gold_transaction(user_id, amount, transaction_type, source=None):
    """
    Log gold transaction event
    
    Args:
        user_id: User involved in transaction
        amount: Amount of gold (positive for gain, negative for loss)
        transaction_type: Type of transaction (purchase, reward, trade, etc.)
        source: Source of transaction (optional)
    """
    AuditLog.record(
        event="gold_transaction",
        user_id=user_id,
        target_id=source,
        amount=amount,
        transaction_type=transaction_type,
        source=source
    )

# K) System Events Integration
def log_system_event(event, details=None):
    """
    Log system-level events
    
    Args:
        event: Event name
        details: Optional details dictionary
    """
    data = details or {}
    data["timestamp"] = datetime.utcnow().isoformat()
    
    AuditLog.record(
        event=event,
        **data
    )

# L) Error Logging Integration
def log_error(error_type, error_message, user_id=None, context=None):
    """
    Log error events
    
    Args:
        error_type: Type of error
        error_message: Error message
        user_id: User affected (optional)
        context: Additional context (optional)
    """
    data = {
        "error_type": error_type,
        "error_message": error_message,
        "context": context or {}
    }
    
    AuditLog.record(
        event="error_occurred",
        user_id=user_id,
        **data
    )

# M) Rate Limit Integration
def log_rate_limit_violation(user_id, action, limit, window):
    """
    Log rate limit violations
    
    Args:
        user_id: User who violated rate limit
        action: Action that was rate limited
        limit: The limit that was exceeded
        window: Time window for the limit
    """
    AuditLog.record(
        event="rate_limit_violation",
        user_id=user_id,
        target_id=action,
        action=action,
        limit=limit,
        window=window
    )

# N) Command Usage Integration
def log_command_usage(user_id, command_name, success=True, error_message=None):
    """
    Log Discord command usage
    
    Args:
        user_id: User who used the command
        command_name: Name of the command
        success: Whether command succeeded
        error_message: Error message if failed
    """
    data = {
        "command_name": command_name,
        "success": success
    }
    
    if error_message:
        data["error_message"] = error_message
    
    AuditLog.record(
        event="command_used",
        user_id=user_id,
        target_id=command_name,
        **data
    )

# Integration examples in actual functions
def integrate_pack_opening_example():
    """Example of integrating audit logging in pack opening"""
    from services.pack_service import open_pack
    
    def open_pack_with_audit(user_id, pack_type):
        try:
            # Open the pack
            cards = open_pack(user_id, pack_type)
            
            # Log the successful opening
            log_pack_opening(user_id, pack_type, cards)
            
            return cards
            
        except Exception as e:
            # Log the error
            log_error("pack_open_error", str(e), user_id, {"pack_type": pack_type})
            raise

def integrate_trade_example():
    """Example of integrating audit logging in trade system"""
    from services.trade_service import finalize
    
    def finalize_with_audit(session, trade_id):
        try:
            # Finalize the trade
            success = finalize(trade_id)
            
            if success:
                # Get trade details and log completion
                trade = session.query(Trade).filter(Trade.id == trade_id).first()
                log_trade_completion(session, trade)
            else:
                # Log failure (could be timeout or cancellation)
                log_trade_cancellation(session, trade_id, None, "finalize_failed")
            
            return success
            
        except Exception as e:
            # Log the error
            log_error("trade_finalize_error", str(e), None, {"trade_id": trade_id})
            raise

# Test function
def test_audit_integration():
    """Test audit integration examples"""
    print("Testing Audit Integration Examples...")
    
    # Mock objects for testing
    class MockCard:
        def __init__(self, serial, tier="common"):
            self.serial = serial
            self.tier = tier
            self.name = f"Card {serial}"
    
    class MockArtist:
        def __init__(self, id, name):
            self.id = id
            self.name = name
    
    class MockTrade:
        def __init__(self, id, user_a, user_b, cards_a, cards_b, gold_a=0, gold_b=0):
            self.id = id
            self.user_a = user_a
            self.user_b = user_b
            self.cards_a = cards_a
            self.cards_b = cards_b
            self.gold_a = gold_a
            self.gold_b = gold_b
    
    # Test C) Trade Finalize logging
    print("\nC) Testing trade finalize logging:")
    trade = MockTrade(
        id="trade_123",
        user_a=12345,
        user_b=67890,
        cards_a=["card1", "card2"],
        cards_b=["card3"],
        gold_a=100,
        gold_b=200
    )
    log_trade_finalize(trade)
    print("   ✅ Trade finalize logged")
    
    # Test D) Card Burn logging
    print("\nD) Testing card burn logging:")
    log_card_burn(12345, "card_123", 50)
    print("   ✅ Card burn logged")
    
    # Test E) Pack opening logging
    print("\nE) Testing pack opening logging:")
    cards = [MockCard("card1"), MockCard("card2"), MockCard("card3")]
    log_pack_opening(12345, "black", cards)
    print("   ✅ Pack opening logged")
    
    # Test F) Legendary creation logging
    print("\nF) Testing legendary creation logging:")
    legendary_card = MockCard("legendary_1", "legendary")
    artist = MockArtist(1, "Artist Name")
    log_legendary_creation(12345, legendary_card, artist)
    print("   ✅ Legendary creation logged")
    
    print("\n✅ All Audit Integration Examples test complete!")

if __name__ == "__main__":
    from datetime import datetime
    test_audit_integration()
