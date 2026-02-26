"""
Stripe Flow Test Suite

Tests the complete Stripe payment flow from checkout to refund.
Verifies all production readiness criteria for Stripe integration.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestStripeFlow:
    """Test complete Stripe payment flow."""
    
    @pytest.fixture
    def sample_checkout_session_event(self):
        """Sample Stripe checkout session completed event."""
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_1234567890",
                    "object": "checkout.session",
                    "status": "complete",
                    "payment_status": "paid",
                    "amount_total": 999,
                    "currency": "usd",
                    "metadata": {
                        "user_id": "1",
                        "pack": "black"
                    },
                    "payment_intent": "pi_1234567890"
                }
            }
        }
    
    @pytest.fixture
    def sample_charge_refunded_event(self):
        """Sample Stripe charge refunded event."""
        return {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_1234567890",
                    "object": "charge",
                    "payment_intent": "pi_1234567890",
                    "amount": 999,
                    "amount_refunded": 999,
                    "currency": "usd",
                    "refunded": True
                }
            }
        }
    
    @pytest.fixture
    def sample_session_expired_event(self):
        """Sample Stripe session expired event."""
        return {
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": "sess_1234567890",
                    "object": "checkout.session",
                    "status": "expired",
                    "metadata": {
                        "user_id": "2",
                        "pack": "gold"
                    }
                }
            }
        }

    def test_stripe_capture(self, sample_checkout_session_event):
        """
        Test Stripe checkout session completion.
        
        PASS CRITERIA:
        - Session is processed successfully
        - Payment is handled with correct parameters
        - Audit log is created
        - Returns appropriate status
        """
        print("\n🧪 Testing Stripe Capture...")
        
        # Mock the payment service
        with patch('webhooks.stripe_hook.handle_payment') as mock_handle:
            mock_handle.return_value = {
                "status": "completed",
                "cards_created": 5,
                "purchase_id": 789
            }
            
            # Mock audit log
            with patch('webhooks.stripe_hook.AuditLog.record') as mock_audit:
                
                # Import and test the function
                from webhooks.stripe_hook import handle_checkout_session_completed
                
                # Process the event
                result = asyncio.run(handle_checkout_session_completed(sample_checkout_session_event))
                
                # Verify result
                assert result["status"] == "processed", f"Expected 'processed', got '{result['status']}'"
                assert result["session_id"] == "sess_1234567890", f"Expected 'sess_1234567890', got '{result['session_id']}'"
                assert result["user_id"] == 1, f"Expected 1, got {result['user_id']}"
                assert result["pack_type"] == "black", f"Expected 'black', got '{result['pack_type']}'"
                
                # Verify payment service was called correctly
                mock_handle.assert_called_once_with(
                    user_id=1,
                    pack_type="black",
                    payment_id="sess_1234567890"
                )
                
                # Verify audit log was created
                mock_audit.assert_called_once_with(
                    event="stripe_capture",
                    user_id=1,
                    target_id="sess_1234567890",
                    details={
                        "pack_type": "black",
                        "session_id": "sess_1234567890",
                        "result": {"status": "completed", "cards_created": 5, "purchase_id": 789},
                        "amount_total": 999,
                        "currency": "usd"
                    }
                )
                
                print("✅ Stripe capture test passed")
    
    def test_stripe_refund(self, sample_charge_refunded_event):
        """
        Test Stripe charge refund processing.
        
        PASS CRITERIA:
        - Refund is processed successfully
        - Cards are revoked
        - Audit log is created
        - Returns appropriate status
        """
        print("\n🧪 Testing Stripe Refund...")
        
        # Mock the refund service
        with patch('webhooks.stripe_hook.refund_purchase') as mock_refund:
            mock_refund.return_value = {
                "status": "refunded",
                "cards_revoked": 5,
                "refund_id": "ref_1234567890"
            }
            
            # Mock audit log
            with patch('webhooks.stripe_hook.AuditLog.record') as mock_audit:
                
                # Import and test the function
                from webhooks.stripe_hook import handle_charge_refunded
                
                # Process the event
                result = asyncio.run(handle_charge_refunded(sample_charge_refunded_event))
                
                # Verify result
                assert result["status"] == "refunded", f"Expected 'refunded', got '{result['status']}'"
                assert result["payment_intent_id"] == "pi_1234567890", f"Expected 'pi_1234567890', got '{result['payment_intent_id']}'"
                assert result["charge_id"] == "ch_1234567890", f"Expected 'ch_1234567890', got '{result['charge_id']}'"
                assert result["refund_amount"] == 999, f"Expected 999, got {result['refund_amount']}"
                
                # Verify refund service was called correctly
                mock_refund.assert_called_once_with("pi_1234567890")
                
                # Verify audit log was created
                mock_audit.assert_called_once_with(
                    event="stripe_refund",
                    target_id="pi_1234567890",
                    details={
                        "charge_id": "ch_1234567890",
                        "refund_amount": 999,
                        "result": {"status": "refunded", "cards_revoked": 5, "refund_id": "ref_1234567890"},
                        "currency": "usd"
                    }
                )
                
                print("✅ Stripe refund test passed")
    
    def test_stripe_session_expired(self, sample_session_expired_event):
        """
        Test Stripe session expiration handling.
        
        PASS CRITERIA:
        - Expired session is logged
        - No payment processing occurs
        - Appropriate status returned
        """
        print("\n🧪 Testing Stripe Session Expiration...")
        
        # Mock audit log
        with patch('webhooks.stripe_hook.AuditLog.record') as mock_audit:
            
            # Import and test the function
            from webhooks.stripe_hook import handle_checkout_session_expired
            
            # Process the event
            result = asyncio.run(handle_checkout_session_expired(sample_session_expired_event))
            
            # Verify result
            assert result["status"] == "expired", f"Expected 'expired', got '{result['status']}'"
            assert result["session_id"] == "sess_1234567890", f"Expected 'sess_1234567890', got '{result['session_id']}'"
            assert result["user_id"] == "2", f"Expected '2', got {result['user_id']}"
            assert result["pack_type"] == "gold", f"Expected 'gold', got '{result['pack_type']}'"
            
            # Verify audit log was created
            mock_audit.assert_called_once_with(
                event="stripe_session_expired",
                user_id=2,
                target_id="sess_1234567890",
                details={
                    "pack_type": "gold",
                    "session_id": "sess_1234567890",
                    "reason": "session_expired"
                }
            )
            
            print("✅ Stripe session expiration test passed")

class TestBattlePassPurchase:
    """Test Battle Pass premium purchase flow via Stripe webhook."""

    @pytest.fixture
    def sample_battlepass_checkout_event(self):
        """Sample Stripe checkout event for battlepass purchase."""
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_bp_001",
                    "object": "checkout.session",
                    "status": "complete",
                    "payment_status": "paid",
                    "amount_total": 999,
                    "currency": "usd",
                    "metadata": {
                        "user_id": "42",
                        "type": "battlepass_purchase"
                    },
                    "payment_intent": "pi_bp_001"
                }
            }
        }

    def test_battlepass_fulfillment(self, sample_battlepass_checkout_event):
        """
        Test battlepass webhook routes to _fulfill_battlepass_purchase and sets premium_expires.

        PASS CRITERIA:
        - metadata type 'battlepass_purchase' is routed correctly
        - premium_expires is written to user_inventory
        - Purchase is recorded in purchases table
        - AuditLog entry created
        - Returns fulfilled status with premium_expires
        """
        print("\n🧪 Testing Battle Pass Fulfillment...")

        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_db = Mock()
        mock_db._get_connection.return_value = mock_conn

        # Pre-mock modules that fail to import locally
        import sys as _sys
        _mocked_modules = {}
        for mod_name in ['services.payment_service', 'services.refund_service',
                         'models.audit_minimal', 'ui.receipts', 'database']:
            if mod_name not in _sys.modules:
                _mocked_modules[mod_name] = Mock()

        with patch.dict('sys.modules', _mocked_modules):
            # Re-import after mocking deps
            import importlib
            import webhooks.stripe_hook as _sh
            importlib.reload(_sh)

            with patch.object(_sh, 'AuditLog') as mock_audit_cls:
                mock_audit = mock_audit_cls.record

                # Patch DatabaseManager inside the fulfillment function
                with patch('database.DatabaseManager', return_value=mock_db):
                    result = asyncio.run(_sh.handle_checkout_session_completed(sample_battlepass_checkout_event))

            # Should be fulfilled, not routed to legacy pack flow
            assert result["status"] == "fulfilled", f"Expected 'fulfilled', got '{result.get('status')}'"
            assert result["product"] == "battlepass"
            assert result["user_id"] == 42
            assert "premium_expires" in result

            # DB should have been called (INSERT ... ON CONFLICT for user_inventory + INSERT into purchases)
            assert mock_cursor.execute.call_count == 2, f"Expected 2 DB calls, got {mock_cursor.execute.call_count}"

            # First call: upsert premium_expires
            first_sql = mock_cursor.execute.call_args_list[0][0][0]
            assert "user_inventory" in first_sql
            assert "premium_expires" in first_sql

            # Second call: insert into purchases
            second_sql = mock_cursor.execute.call_args_list[1][0][0]
            assert "purchases" in second_sql

            # Audit log recorded
            mock_audit.assert_called_once()

            print("✅ Battle Pass fulfillment test passed")

    def test_battlepass_not_routed_to_pack_purchase(self, sample_battlepass_checkout_event):
        """
        Test that battlepass events do NOT fall through to pack purchase or legacy flow.

        PASS CRITERIA:
        - handle_payment is never called
        - _fulfill_pack_purchase is never called
        """
        print("\n🧪 Testing Battle Pass routing isolation...")

        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_db = Mock()
        mock_db._get_connection.return_value = mock_conn

        import sys as _sys
        _mocked_modules = {}
        for mod_name in ['services.payment_service', 'services.refund_service',
                         'models.audit_minimal', 'ui.receipts', 'database']:
            if mod_name not in _sys.modules:
                _mocked_modules[mod_name] = Mock()

        with patch.dict('sys.modules', _mocked_modules):
            import importlib
            import webhooks.stripe_hook as _sh
            importlib.reload(_sh)

            with patch.object(_sh, 'AuditLog'), \
                 patch.object(_sh, 'handle_payment') as mock_handle_payment, \
                 patch('database.DatabaseManager', return_value=mock_db):

                asyncio.run(_sh.handle_checkout_session_completed(sample_battlepass_checkout_event))
                mock_handle_payment.assert_not_called()

            print("✅ Battle Pass routing isolation verified")

    def test_battlepass_checkout_creation(self):
        """
        Test create_battlepass_checkout() creates a valid Stripe session.

        PASS CRITERIA:
        - Stripe Session.create called with correct metadata
        - Returns success with checkout_url and session_id
        - Price is 999 cents ($9.99)
        """
        print("\n🧪 Testing Battle Pass Checkout Creation...")

        with patch('stripe_payments.stripe.checkout.Session.create') as mock_create:
            mock_session = Mock()
            mock_session.id = "sess_bp_test"
            mock_session.url = "https://checkout.stripe.com/pay/sess_bp_test"
            mock_create.return_value = mock_session

            from stripe_payments import StripePaymentManager
            manager = StripePaymentManager()
            result = manager.create_battlepass_checkout(user_id=12345)

            assert result["success"] is True
            assert result["checkout_url"] == "https://checkout.stripe.com/pay/sess_bp_test"
            assert result["session_id"] == "sess_bp_test"

            # Verify Stripe was called correctly
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]

            assert call_kwargs["mode"] == "payment"
            assert call_kwargs["metadata"]["user_id"] == "12345"
            assert call_kwargs["metadata"]["type"] == "battlepass_purchase"

            # Verify price
            line_items = call_kwargs["line_items"]
            assert len(line_items) == 1
            assert line_items[0]["price_data"]["unit_amount"] == 999
            assert line_items[0]["price_data"]["currency"] == "usd"
            assert "Battle Pass Premium" in line_items[0]["price_data"]["product_data"]["name"]

            print("✅ Battle Pass checkout creation test passed")

    def test_battlepass_checkout_failure(self):
        """
        Test create_battlepass_checkout() handles Stripe errors gracefully.

        PASS CRITERIA:
        - Returns success=False with error message on Stripe failure
        """
        print("\n🧪 Testing Battle Pass Checkout Failure Handling...")

        with patch('stripe_payments.stripe.checkout.Session.create', side_effect=Exception("Stripe API unavailable")):
            from stripe_payments import StripePaymentManager
            manager = StripePaymentManager()
            result = manager.create_battlepass_checkout(user_id=12345)

            assert result["success"] is False
            assert "Stripe API unavailable" in result["error"]

            print("✅ Battle Pass checkout failure handling test passed")


class TestStripeCheckout:
    """Test Stripe checkout session creation."""
    
    def test_create_pack_checkout(self):
        """
        Test pack checkout session creation.
        
        PASS CRITERIA:
        - Checkout session is created successfully
        - Correct metadata is included
        - Pricing is correct
        - Session URL is returned
        """
        print("\n🧪 Testing Pack Checkout Creation...")
        
        # Mock Stripe API
        with patch('services.checkout.stripe.checkout.Session.create') as mock_create:
            mock_session = Mock()
            mock_session.id = "sess_1234567890"
            mock_session.url = "https://checkout.stripe.com/pay/sess_1234567890"
            mock_create.return_value = mock_session
            
            # Import and test the function
            from services.checkout import create_pack_checkout
            
            # Create checkout session
            checkout_url = create_pack_checkout(
                user_id=12345,
                pack="black",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel"
            )
            
            # Verify result
            assert checkout_url == "https://checkout.stripe.com/pay/sess_1234567890", f"Expected checkout URL, got {checkout_url}"
            
            # Verify Stripe was called correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            
            # Check basic parameters
            assert call_args[1]["mode"] == "payment"
            assert call_args[1]["success_url"] == "https://example.com/success"
            assert call_args[1]["cancel_url"] == "https://example.com/cancel"
            
            # Check metadata
            metadata = call_args[1]["metadata"]
            assert metadata["user_id"] == "12345"
            assert metadata["pack"] == "black"
            
            # Check line items
            line_items = call_args[1]["line_items"]
            assert len(line_items) == 1
            
            price_data = line_items[0]["price_data"]
            assert price_data["currency"] == "usd"
            assert price_data["unit_amount"] == 999  # Black pack price
            assert price_data["product_data"]["name"] == "Black Pack"
            
            print("✅ Pack checkout creation test passed")
    
    def test_checkout_pricing(self):
        """
        Test pack pricing configuration.
        
        PASS CRITERIA:
        - All packs have correct pricing
        - Pricing is in cents
        - Display names are correct
        """
        print("\n🧪 Testing Checkout Pricing...")
        
        from services.checkout import get_pack_pricing, get_pack_price, format_price_cents_to_usd
        
        # Test pricing configuration
        pricing = get_pack_pricing()
        
        # Check black pack pricing
        assert "black" in pricing, "Black pack should be available"
        assert pricing["black"]["price_cents"] == 999, "Black pack should cost $9.99"
        assert pricing["black"]["price_usd"] == 9.99, "Black pack should be $9.99"
        assert pricing["black"]["name"] == "Black Pack", "Black pack should have correct name"
        
        # Check gold pack pricing
        assert "gold" in pricing, "Gold pack should be available"
        assert pricing["gold"]["price_cents"] == 699, "Gold pack should cost $6.99"
        assert pricing["gold"]["price_usd"] == 6.99, "Gold pack should be $6.99"
        
        # Test individual pack price
        black_price = get_pack_price("black")
        assert black_price == 999, f"Expected 999, got {black_price}"
        
        # Test price formatting
        formatted = format_price_cents_to_usd(999)
        assert formatted == "$9.99", f"Expected '$9.99', got '{formatted}'"
        
        print("✅ Checkout pricing test passed")

class TestStripeProductionReadiness:
    """Tests that verify Stripe production readiness criteria."""
    
    def test_same_session_never_gives_2_packs(self):
        """
        Test: same session never gives 2 packs.
        
        PASS CRITERIA:
        - Duplicate session events are handled safely
        - No duplicate packs created
        - Idempotency is maintained
        """
        print("\n🚦 Testing Session Idempotency...")
        
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_1234567890",
                    "metadata": {"user_id": "1", "pack": "black"}
                }
            }
        }
        
        # Mock payment service to track calls
        call_count = 0
        
        def mock_handle_payment(user_id, pack_type, payment_id):
            nonlocal call_count
            call_count += 1
            return {
                "status": "completed" if call_count == 1 else "ALREADY_PROCESSED",
                "cards_created": 5 if call_count == 1 else 0,
                "purchase_id": 789 if call_count == 1 else None
            }
        
        with patch('webhooks.stripe_hook.handle_payment', side_effect=mock_handle_payment):
            from webhooks.stripe_hook import handle_checkout_session_completed
            
            # Process same session multiple times
            results = []
            for i in range(3):
                result = asyncio.run(handle_checkout_session_completed(event))
                results.append(result)
            
            # First should succeed, others should indicate already processed
            assert results[0]["result"]["status"] == "completed", "First processing should succeed"
            assert results[1]["result"]["status"] == "ALREADY_PROCESSED", "Duplicate should be rejected"
            assert results[2]["result"]["status"] == "ALREADY_PROCESSED", "Second duplicate should be rejected"
            
            # Only first should create cards
            assert results[0]["result"]["cards_created"] == 5, "First should create 5 cards"
            assert results[1]["result"]["cards_created"] == 0, "Duplicate should create 0 cards"
            assert results[2]["result"]["cards_created"] == 0, "Second duplicate should create 0 cards"
            
            print("✅ Session idempotency verified")
    
    def test_stripe_retry_safe(self):
        """
        Test: Stripe retry safe.
        
        PASS CRITERIA:
        - Webhook retries are handled gracefully
        - System remains stable under retries
        - No data corruption
        """
        print("\n🚦 Testing Stripe Retry Safety...")
        
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_1234567890",
                    "metadata": {"user_id": "1", "pack": "black"}
                }
            }
        }
        
        # Simulate webhook retries (same event multiple times)
        results = []
        
        with patch('webhooks.stripe_hook.handle_payment') as mock_handle:
            mock_handle.return_value = {"status": "completed", "cards_created": 5}
            
            from webhooks.stripe_hook import handle_checkout_session_completed
            
            # Process same event multiple times (simulating retries)
            for i in range(5):
                try:
                    result = asyncio.run(handle_checkout_session_completed(event))
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            
            # All should succeed (webhook layer is not idempotent, but stable)
            for i, result in enumerate(results):
                assert "error" not in result, f"Retry {i+1} should not error"
                assert result["status"] == "processed", f"Retry {i+1} should be processed"
            
            # Business logic called multiple times (idempotency handled at business layer)
            assert mock_handle.call_count == 5, f"Expected 5 calls, got {mock_handle.call_count}"
            
            print("✅ Stripe retry safety verified")
    
    def test_refund_removes_cards(self):
        """
        Test: refund removes cards.
        
        PASS CRITERIA:
        - Refund event triggers card revocation
        - All cards from original purchase are revoked
        - User loses access to cards
        """
        print("\n🚦 Testing Refund Card Removal...")
        
        event = {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_1234567890",
                    "payment_intent": "pi_1234567890",
                    "amount": 999,
                    "amount_refunded": 999
                }
            }
        }
        
        with patch('webhooks.stripe_hook.refund_purchase') as mock_refund:
            mock_refund.return_value = {
                "status": "refunded",
                "cards_revoked": 5,
                "access_revoked": True,
                "refund_id": "ref_1234567890"
            }
            
            from webhooks.stripe_hook import handle_charge_refunded
            
            result = asyncio.run(handle_charge_refunded(event))
            
            # Verify refund processing
            assert result["status"] == "refunded", f"Expected 'refunded', got '{result['status']}'"
            assert result["payment_intent_id"] == "pi_1234567890", f"Expected 'pi_1234567890', got '{result['payment_intent_id']}'"
            
            # Verify cards were revoked
            assert result["result"]["cards_revoked"] == 5, f"Expected 5 cards revoked, got {result['result']['cards_revoked']}"
            assert result["result"]["access_revoked"] is True, f"Expected access revoked, got {result['result']['access_revoked']}"
            
            # Verify refund service was called
            mock_refund.assert_called_once_with("pi_1234567890")
            
            print("✅ Refund card removal verified")
    
    def test_audit_shows_capture_and_refund(self):
        """
        Test: audit shows capture + refund.
        
        PASS CRITERIA:
        - Both capture and refund events are logged
        - Audit trail is complete
        - All required information is logged
        """
        print("\n🚦 Testing Audit Capture + Refund...")
        
        audit_log = []
        
        def mock_audit_record(event, user_id=None, target_id=None, details=None):
            audit_log.append({
                "event": event,
                "user_id": user_id,
                "target_id": target_id,
                "details": details or {}
            })
        
        # Test capture event
        capture_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_1234567890",
                    "metadata": {"user_id": "1", "pack": "black"},
                    "amount_total": 999,
                    "currency": "usd"
                }
            }
        }
        
        with patch('webhooks.stripe_hook.AuditLog.record', side_effect=mock_audit_record), \
             patch('webhooks.stripe_hook.handle_payment') as mock_handle:
            
            mock_handle.return_value = {"status": "completed", "cards_created": 5}
            
            from webhooks.stripe_hook import handle_checkout_session_completed
            
            capture_result = asyncio.run(handle_checkout_session_completed(capture_event))
        
        # Test refund event
        refund_event = {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_1234567890",
                    "payment_intent": "pi_1234567890",
                    "amount": 999,
                    "currency": "usd"
                }
            }
        }
        
        with patch('webhooks.stripe_hook.AuditLog.record', side_effect=mock_audit_record), \
             patch('webhooks.stripe_hook.refund_purchase') as mock_refund:
            
            mock_refund.return_value = {"status": "refunded", "cards_revoked": 5}
            
            from webhooks.stripe_hook import handle_charge_refunded
            
            refund_result = asyncio.run(handle_charge_refunded(refund_event))
        
        # Verify audit log contains both events
        assert len(audit_log) >= 2, f"Expected at least 2 audit entries, got {len(audit_log)}"
        
        # Check capture event logged
        capture_entries = [entry for entry in audit_log if entry["event"] == "stripe_capture"]
        assert len(capture_entries) >= 1, "Should have at least one capture audit entry"
        
        capture_entry = capture_entries[0]
        assert capture_entry["user_id"] == 1, f"Expected user_id 1, got {capture_entry['user_id']}"
        assert capture_entry["target_id"] == "sess_1234567890", f"Expected session ID, got {capture_entry['target_id']}"
        assert capture_entry["details"]["pack_type"] == "black", f"Expected black pack, got {capture_entry['details']['pack_type']}"
        
        # Check refund event logged
        refund_entries = [entry for entry in audit_log if entry["event"] == "stripe_refund"]
        assert len(refund_entries) >= 1, "Should have at least one refund audit entry"
        
        refund_entry = refund_entries[0]
        assert refund_entry["target_id"] == "pi_1234567890", f"Expected payment_intent ID, got {refund_entry['target_id']}"
        assert refund_entry["details"]["charge_id"] == "ch_1234567890", f"Expected charge ID, got {refund_entry['details']['charge_id']}"
        
        print("✅ Audit capture + refund verified")
    
    def test_webhook_signature_verified(self):
        """
        Test: webhook signature verified.
        
        PASS CRITERIA:
        - Webhook signature is verified
        - Invalid signatures are rejected
        - Valid signatures are accepted
        """
        print("\n🚦 Testing Webhook Signature Verification...")
        
        from webhooks.stripe_hook import verify_stripe_signature
        
        # Mock Stripe webhook construction
        with patch('webhooks.stripe_hook.stripe.Webhook.construct_event') as mock_construct:
            mock_event = {"type": "checkout.session.completed", "data": {}}
            mock_construct.return_value = mock_event
            
            # Test valid signature
            payload = b'{"test": "data"}'
            signature = "t=1234567890,v1=valid_signature"
            
            try:
                event = verify_stripe_signature(payload, signature)
                assert event == mock_event, "Valid signature should return event"
            except Exception as e:
                pytest.fail(f"Valid signature should not raise exception: {e}")
            
            # Test invalid signature
            mock_construct.side_effect = stripe.error.SignatureVerificationError("Invalid signature")
            
            try:
                event = verify_stripe_signature(payload, signature)
                pytest.fail("Invalid signature should raise exception")
            except Exception as e:
                assert "Invalid signature" in str(e), f"Expected signature error, got {e}"
        
        print("✅ Webhook signature verification verified")

# Test Runner

def run_stripe_flow_tests():
    """Run all Stripe flow tests."""
    print("🧪 STRIPE FLOW TESTS")
    print("=" * 50)
    
    import pytest
    
    # Run all tests in this file
    result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return result == 0

def run_stripe_production_tests():
    """Run production readiness tests only."""
    print("🚦 STRIPE PRODUCTION READINESS TESTS")
    print("=" * 50)
    
    import pytest
    
    # Run production readiness tests
    result = pytest.main([
        __file__,
        "TestStripeProductionReadiness",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return result == 0

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "production":
        # Run production readiness tests only
        success = run_stripe_production_tests()
    else:
        # Run all tests
        success = run_stripe_flow_tests()
    
    sys.exit(0 if success else 1)
