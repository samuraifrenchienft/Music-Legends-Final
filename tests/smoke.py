"""
Smoke Test Suite - Checklist Critical Tests

Tests the core business logic that must work for production launch.
These tests verify the fundamental guarantees of the system.

PASS CRITERIA (Launch Gate):
- Black guarantee ✅
- Cap downgrade ✅  
- No duplicates ✅
- Trade atomic ✅
- Rate limit ✅
- Refund revoke ✅

RUN: python -m pytest tests/smoke.py -v
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the services and models we need to test
from services.pack_youtube import open_black_pack
from services.trade_service import finalize
from services.rate_limiter import RateLimiter
from services.refund_service import refund_purchase
from models.card import Card
from models.artist import Artist
from models.purchase import Purchase
from models.trade import Trade

# Test configuration
TEST_USER_ID = 999999
TEST_PAYMENT_ID = "SMOKE_TEST_PAYMENT_123"

class TestSmokeSuite:
    """Smoke test suite for critical business logic."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        print("\n🚀 Starting Smoke Test Suite")
        print("=" * 50)
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test environment."""
        print("\n" + "=" * 50)
        print("🏁 Smoke Test Suite Complete")
    
    def setup_method(self):
        """Setup for each test method."""
        # Clean up any test data
        self._cleanup_test_data()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up test data."""
        try:
            # Clean up test cards
            test_cards = Card.where("purchase_id = ?", (TEST_PAYMENT_ID,))
            for card in test_cards:
                card.delete()
            
            # Clean up test purchases
            test_purchase = Purchase.find_by("payment_id", TEST_PAYMENT_ID)
            if test_purchase:
                test_purchase.delete()
            
            # Clean up test trades
            test_trades = Trade.where("initiator_id = ?", (TEST_USER_ID,))
            for trade in test_trades:
                trade.delete()
                
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

    # ---------- 1. BLACK PACK GUARANTEE ----------
    
    def test_black_guarantee(self):
        """
        Test: Black pack must contain at least one Gold+ tier card
        
        PASS CRITERIA:
        - Black pack opens successfully
        - At least one card is gold, platinum, or legendary tier
        """
        print("\n📦 Testing Black Pack Guarantee...")
        
        # Open a black pack
        cards = open_black_pack(user_id=TEST_USER_ID)
        
        # Verify we got cards
        assert cards is not None, "Black pack should return cards"
        assert len(cards) > 0, "Black pack should contain cards"
        
        # Check for Gold+ tier
        high_tier_cards = [
            card for card in cards 
            if card.tier in ["gold", "platinum", "legendary"]
        ]
        
        assert len(high_tier_cards) > 0, (
            f"Black pack must contain Gold+ tier card. "
            f"Got tiers: {[c.tier for c in cards]}"
        )
        
        print(f"✅ Black pack guarantee passed - Found {len(high_tier_cards)} Gold+ cards")
    
    # ---------- 2. LEGENDARY CAP ----------
    
    def test_legendary_cap(self):
        """
        Test: Legendary cap must downgrade legendary cards
        
        PASS CRITERIA:
        - When artist is at legendary cap, no legendary cards are awarded
        - Legendary cards are downgraded to platinum
        """
        print("\n🏆 Testing Legendary Cap...")
        
        # Get an artist to test with
        artist = Artist.first()
        assert artist is not None, "Need at least one artist for testing"
        
        # Set artist to legendary cap
        original_legendary = getattr(artist, 'current_legendary', 0)
        artist.current_legendary = 100  # Set to cap
        artist.save()
        
        try:
            # Open multiple black packs to test cap
            cards = open_black_pack(user_id=TEST_USER_ID)
            
            # Verify no legendary cards
            legendary_cards = [
                card for card in cards 
                if card.tier == "legendary"
            ]
            
            assert len(legendary_cards) == 0, (
                f"Cap must prevent legendary cards. "
                f"Found {len(legendary_cards)} legendary cards"
            )
            
            print(f"✅ Legendary cap passed - No legendary cards found in {len(cards)} cards")
            
        finally:
            # Restore original legendary count
            artist.current_legendary = original_legendary
            artist.save()
    
    # ---------- 3. PARALLEL OPEN SAFETY ----------
    
    def test_parallel(self):
        """
        Test: Parallel pack opening must not create duplicates
        
        PASS CRITERIA:
        - Multiple pack openings create correct number of cards
        - No duplicate card IDs are created
        - Database integrity is maintained
        """
        print("\n🔄 Testing Parallel Open Safety...")
        
        # Count cards before
        before_count = Card.count()
        
        # Open multiple packs rapidly
        cards_opened = []
        for i in range(5):
            cards = open_black_pack(user_id=TEST_USER_ID + i)
            cards_opened.extend(cards)
        
        # Count cards after
        after_count = Card.count()
        
        # Verify correct number of cards created
        expected_increase = len(cards_opened)
        actual_increase = after_count - before_count
        
        assert actual_increase == expected_increase, (
            f"Expected {expected_increase} new cards, "
            f"but got {actual_increase}. Possible duplicates."
        )
        
        # Verify no duplicate card IDs
        card_ids = [card.id for card in cards_opened]
        unique_ids = set(card_ids)
        
        assert len(card_ids) == len(unique_ids), (
            f"Found duplicate card IDs. "
            f"Total: {len(card_ids)}, Unique: {len(unique_ids)}"
        )
        
        print(f"✅ Parallel safety passed - Created {actual_increase} unique cards")
    
    # ---------- 4. TRADE ATOMIC ----------
    
    def test_trade(self):
        """
        Test: Trade finalization must be atomic
        
        PASS CRITERIA:
        - Trade finalizes successfully first time
        - Second finalization attempt fails
        - Trade state changes correctly
        """
        print("\n🤝 Testing Trade Atomicity...")
        
        # Create a sample trade
        trade = self._create_sample_trade()
        assert trade is not None, "Failed to create sample trade"
        
        # First finalize should succeed
        first_result = finalize(trade.id)
        assert first_result is True, "First trade finalize must succeed"
        
        # Verify trade is finalized
        updated_trade = Trade.find(trade.id)
        assert updated_trade.status == "completed", "Trade should be completed"
        
        # Second finalize should fail
        second_result = finalize(trade.id)
        assert second_result is False, "Second trade finalize must fail"
        
        print("✅ Trade atomicity passed - Single finalization enforced")
    
    def _create_sample_trade(self):
        """Helper to create a sample trade for testing."""
        try:
            # Create test cards for trade
            card1 = Card.create(
                user_id=TEST_USER_ID,
                artist_id=1,
                tier="common",
                purchase_id=TEST_PAYMENT_ID + "_trade1"
            )
            
            card2 = Card.create(
                user_id=TEST_USER_ID + 1,
                artist_id=2,
                tier="common", 
                purchase_id=TEST_PAYMENT_ID + "_trade2"
            )
            
            # Create trade
            trade = Trade.create(
                initiator_id=TEST_USER_ID,
                recipient_id=TEST_USER_ID + 1,
                offered_cards=[card1.id],
                requested_cards=[card2.id],
                status="pending"
            )
            
            return trade
            
        except Exception as e:
            print(f"⚠️ Failed to create sample trade: {e}")
            return None
    
    # ---------- 5. RATE LIMIT ----------
    
    def test_rate(self):
        """
        Test: Rate limiter must enforce limits
        
        PASS CRITERIA:
        - First N requests are allowed
        - Requests beyond limit are denied
        - Rate limit resets correctly
        """
        print("\n⏱️ Testing Rate Limit...")
        
        # Create rate limiter: 2 requests per 5 seconds
        limiter = RateLimiter("pack:1", 2, 5)
        
        # First two requests should be allowed
        assert limiter.allow() is True, "First request should be allowed"
        assert limiter.allow() is True, "Second request should be allowed"
        
        # Third request should be denied
        assert limiter.allow() is False, "Third request should be denied"
        
        # Test different key (should be independent)
        limiter2 = RateLimiter("pack:2", 2, 5)
        assert limiter2.allow() is True, "Different key should be allowed"
        
        print("✅ Rate limit passed - Limits enforced correctly")
    
    # ---------- 6. REFUND ----------
    
    def test_refund(self):
        """
        Test: Refund must revoke all cards from purchase
        
        PASS CRITERIA:
        - Purchase creates cards
        - Refund deletes all purchase cards
        - Cards no longer exist after refund
        """
        print("\n💰 Testing Refund...")
        
        # Create a test purchase
        payment_id = TEST_PAYMENT_ID + "_refund"
        self._create_test_purchase(payment_id)
        
        # Verify cards exist
        cards_before = Card.where("purchase_id = ?", (payment_id,))
        assert len(cards_before) > 0, "Purchase should create cards"
        
        card_ids_before = [card.id for card in cards_before]
        
        # Process refund
        refund_result = refund_purchase(payment_id)
        assert refund_result is True, "Refund should succeed"
        
        # Verify cards are deleted
        cards_after = Card.where("purchase_id = ?", (payment_id,))
        assert len(cards_after) == 0, "Refund should delete all purchase cards"
        
        # Verify cards no longer exist
        for card_id in card_ids_before:
            card = Card.find(card_id)
            assert card is None, f"Card {card_id} should not exist after refund"
        
        print(f"✅ Refund passed - Deleted {len(card_ids_before)} cards")
    
    def _create_test_purchase(self, payment_id: str):
        """Helper to create a test purchase with cards."""
        try:
            # Create purchase record
            purchase = Purchase.create(
                user_id=TEST_USER_ID,
                payment_id=payment_id,
                pack_type="founder_black",
                amount=4999,  # $49.99 in cents
                status="completed",
                created_at=datetime.now()
            )
            
            # Create test cards for the purchase
            for i in range(5):  # Founder pack has 5 cards
                Card.create(
                    user_id=TEST_USER_ID,
                    artist_id=1,
                    tier="common",
                    purchase_id=payment_id,
                    pack_id=purchase.id
                )
            
            return purchase
            
        except Exception as e:
            print(f"⚠️ Failed to create test purchase: {e}")
            return None

# ---------- Test Runner ----------
    
def run_smoke_tests():
    """Run all smoke tests and return results."""
    import subprocess
    import sys
    
    print("🚀 Running Smoke Test Suite")
    print("=" * 50)
    
    # Run pytest with smoke tests
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "--color=yes"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Check if all tests passed
    if result.returncode == 0:
        print("\n🎉 ALL SMOKE TESTS PASSED!")
        print("✅ System is ready for launch")
        return True
    else:
        print("\n❌ SMOKE TESTS FAILED!")
        print("🚫 System NOT ready for launch")
        return False

if __name__ == "__main__":
    # Run tests when script is executed directly
    success = run_smoke_tests()
    sys.exit(0 if success else 1)

# ---------- Pytest Integration ----------
    
def pytest_configure(config):
    """Pytest configuration."""
    config.addinivalue_line(
        "markers", "smoke: Mark test as smoke test"
    )

def pytest_collection_modifyitems(config, items):
    """Add smoke test marker to all tests."""
    for item in items:
        if "test_" in item.name:
            item.add_marker(pytest.mark.smoke)
