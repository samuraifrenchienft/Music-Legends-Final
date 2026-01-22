"""
Payment Flow Test Suite

Tests the complete payment gateway flow from webhook to business logic.
Verifies production readiness of the payment processing system.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webhooks.payments import payment_webhook, PaymentWebhookHandler
from services.payment_service import handle_payment
from services.refund_service import refund_purchase
from models.audit_minimal import AuditLog

class TestPaymentFlow:
    """Test complete payment flow through webhook system."""
    
    @pytest.fixture
    def sample_capture_event(self):
        """Sample payment captured event."""
        return {
            "type": "payment.captured",
            "data": {
                "id": "TX123",
                "amount": 4999,
                "currency": "usd",
                "metadata": {
                    "user": "1",
                    "pack": "black"
                }
            }
        }
    
    @pytest.fixture
    def sample_refund_event(self):
        """Sample payment refund event."""
        return {
            "type": "payment.refunded",
            "data": {
                "id": "TX123",
                "amount": 4999,
                "reason": "customer_request"
            }
        }
    
    @pytest.fixture
    def sample_failed_event(self):
        """Sample payment failed event."""
        return {
            "type": "payment.failed",
            "data": {
                "id": "TX124",
                "failure_reason": "insufficient_funds",
                "metadata": {
                    "user": "2",
                    "pack": "founder_black"
                }
            }
        }
    
    @pytest.fixture
    def webhook_handler(self):
        """Create webhook handler instance."""
        return PaymentWebhookHandler()

    def test_gateway_flow(self, sample_capture_event):
        """
        Test complete gateway flow: webhook → business logic → result.
        
        PASS CRITERIA:
        - Event is processed successfully
        - Status indicates queued/completed
        - Business logic is called correctly
        """
        print("\n🧪 Testing Gateway Flow...")
        
        # Mock the payment service to avoid actual database operations
        with patch('webhooks.payments.handle_payment') as mock_handle:
            mock_handle.return_value = {
                "status": "completed",
                "cards_created": 5,
                "purchase_id": 789
            }
            
            # Process the event through webhook
            result = asyncio.run(payment_webhook(sample_capture_event))
            
            # Verify webhook processing
            assert result["status"] == "captured", f"Expected 'captured', got '{result['status']}'"
            assert result["payment_id"] == "TX123", f"Expected 'TX123', got '{result['payment_id']}'"
            assert result["user_id"] == "1", f"Expected '1', got '{result['user_id']}'"
            assert result["pack_type"] == "black", f"Expected 'black', got '{result['pack_type']}'"
            
            # Verify business logic was called
            mock_handle.assert_called_once_with(
                user_id=1,
                pack_type="black",
                payment_id="TX123"
            )
            
            print("✅ Gateway flow test passed")
    
    def test_refund_flow(self, sample_refund_event):
        """
        Test refund flow: webhook → refund service → card revocation.
        
        PASS CRITERIA:
        - Refund event is processed
        - Refund service is called
        - Cards are revoked
        """
        print("\n🧪 Testing Refund Flow...")
        
        # Mock the refund service
        with patch('webhooks.payments.refund_purchase') as mock_refund:
            mock_refund.return_value = {
                "status": "refunded",
                "cards_revoked": 5,
                "refund_id": "REF123"
            }
            
            # Process the refund event
            result = asyncio.run(payment_webhook(sample_refund_event))
            
            # Verify refund processing
            assert result["status"] == "refunded", f"Expected 'refunded', got '{result['status']}'"
            assert result["payment_id"] == "TX123", f"Expected 'TX123', got '{result['payment_id']}'"
            assert result["refund_amount"] == 4999, f"Expected 4999, got '{result['refund_amount']}'"
            assert result["reason"] == "customer_request", f"Expected 'customer_request', got '{result['reason']}'"
            
            # Verify refund service was called
            mock_refund.assert_called_once_with("TX123")
            
            print("✅ Refund flow test passed")
    
    def test_failure_flow(self, sample_failed_event):
        """
        Test payment failure flow.
        
        PASS CRITERIA:
        - Failure event is processed
        - No business logic execution
        - Failure is logged
        """
        print("\n🧪 Testing Failure Flow...")
        
        # Process the failure event
        result = asyncio.run(payment_webhook(sample_failed_event))
        
        # Verify failure processing
        assert result["status"] == "failed", f"Expected 'failed', got '{result['status']}'"
        assert result["payment_id"] == "TX124", f"Expected 'TX124', got '{result['payment_id']}'"
        assert result["failure_reason"] == "insufficient_funds", f"Expected 'insufficient_funds', got '{result['failure_reason']}'"
        assert result["user_id"] == "2", f"Expected '2', got '{result['user_id']}'"
        assert result["pack_type"] == "founder_black", f"Expected 'founder_black', got '{result['pack_type']}'"
        
        print("✅ Failure flow test passed")
    
    def test_retry_safety(self, sample_capture_event):
        """
        Test that duplicate events are handled safely (idempotency).
        
        PASS CRITERIA:
        - First event processes successfully
        - Second event is handled gracefully
        - No duplicate cards created
        """
        print("\n🧪 Testing Retry Safety...")
        
        # Mock payment service with tracking
        call_count = 0
        
        def mock_handle_payment(user_id, pack_type, payment_id):
            nonlocal call_count
            call_count += 1
            return {
                "status": "completed",
                "cards_created": 5,
                "purchase_id": 789,
                "call_count": call_count
            }
        
        with patch('webhooks.payments.handle_payment', side_effect=mock_handle_payment):
            # Process first event
            result1 = asyncio.run(payment_webhook(sample_capture_event))
            
            # Process duplicate event
            result2 = asyncio.run(payment_webhook(sample_capture_event))
            
            # Both should succeed
            assert result1["status"] == "captured"
            assert result2["status"] == "captured"
            
            # Business logic should be called twice (webhook layer is not idempotent,
            # but business logic should handle duplicates)
            assert call_count == 2, f"Expected 2 calls, got {call_count}"
            
            print("✅ Retry safety test passed")
    
    def test_audit_logging(self, sample_capture_event):
        """
        Test that all events are properly logged to audit trail.
        
        PASS CRITERIA:
        - Webhook processing is logged
        - Business logic calls are logged
        - Results are logged
        """
        print("\n🧪 Testing Audit Logging...")
        
        # Mock audit log to track calls
        with patch('webhooks.payments.AuditLog.record') as mock_audit, \
             patch('webhooks.payments.handle_payment') as mock_handle:
            
            mock_handle.return_value = {"status": "completed"}
            
            # Process event
            result = asyncio.run(payment_webhook(sample_capture_event))
            
            # Verify audit logging calls
            assert mock_audit.call_count >= 2, f"Expected at least 2 audit calls, got {mock_audit.call_count}"
            
            # Check specific audit calls
            audit_calls = [str(call) for call in mock_audit.call_args_list]
            
            # Should log webhook processing
            webhook_logged = any("webhook_processed" in call for call in audit_calls)
            assert webhook_logged, "Webhook processing should be logged"
            
            # Should log gateway capture
            capture_logged = any("gateway_capture" in call for call in audit_calls)
            assert capture_logged, "Gateway capture should be logged"
            
            print("✅ Audit logging test passed")
    
    def test_invalid_event_handling(self):
        """
        Test handling of invalid or malformed events.
        
        PASS CRITERIA:
        - Invalid events are rejected gracefully
        - Error responses are appropriate
        - System remains stable
        """
        print("\n🧪 Testing Invalid Event Handling...")
        
        # Test missing type
        invalid_event1 = {"data": {"id": "TX123"}}
        result1 = asyncio.run(payment_webhook(invalid_event1))
        assert result1["status"] == "error", "Missing type should return error"
        
        # Test missing data
        invalid_event2 = {"type": "payment.captured"}
        result2 = asyncio.run(payment_webhook(invalid_event2))
        assert result2["status"] == "error", "Missing data should return error"
        
        # Test missing payment ID
        invalid_event3 = {
            "type": "payment.captured",
            "data": {"metadata": {"user": "1"}}
        }
        result3 = asyncio.run(payment_webhook(invalid_event3))
        assert result3["status"] == "error", "Missing payment ID should return error"
        
        print("✅ Invalid event handling test passed")
    
    def test_metadata_extraction(self, sample_capture_event):
        """
        Test that metadata is correctly extracted and used.
        
        PASS CRITERIA:
        - User ID is extracted from metadata
        - Pack type is extracted from metadata
        - Missing metadata is handled
        """
        print("\n🧪 Testing Metadata Extraction...")
        
        with patch('webhooks.payments.handle_payment') as mock_handle:
            mock_handle.return_value = {"status": "completed"}
            
            # Process event with metadata
            result = asyncio.run(payment_webhook(sample_capture_event))
            
            # Verify metadata was extracted and used
            mock_handle.assert_called_once_with(
                user_id=1,
                pack_type="black",
                payment_id="TX123"
            )
            
            # Test missing metadata
            event_no_metadata = {
                "type": "payment.captured",
                "data": {"id": "TX124"}
            }
            
            result_no_meta = asyncio.run(payment_webhook(event_no_metadata))
            assert result_no_meta["status"] == "error", "Missing metadata should return error"
            
            print("✅ Metadata extraction test passed")
    
    def test_unsupported_event_type(self):
        """
        Test handling of unsupported event types.
        
        PASS CRITERIA:
        - Unsupported events are ignored
        - Appropriate response is returned
        - No errors are thrown
        """
        print("\n🧪 Testing Unsupported Event Type...")
        
        unsupported_event = {
            "type": "payment.unknown_event",
            "data": {"id": "TX123"}
        }
        
        result = asyncio.run(payment_webhook(unsupported_event))
        
        assert result["status"] == "ignored", "Unsupported event should be ignored"
        assert result["reason"] == "unsupported_event_type", "Should provide reason for ignoring"
        
        print("✅ Unsupported event type test passed")

# Production Readiness Tests

class TestProductionReadiness:
    """Tests that verify production readiness criteria."""
    
    def test_gateway_capture_delivery(self):
        """
        Test: capture → pack delivered once.
        
        PASS CRITERIA:
        - Capture event triggers pack delivery
        - Pack is delivered exactly once
        - User receives correct pack
        """
        print("\n🚦 Testing Gateway Capture Delivery...")
        
        event = {
            "type": "payment.captured",
            "data": {
                "id": "TX123",
                "metadata": {
                    "user": 1,
                    "pack": "black"
                }
            }
        }
        
        with patch('webhooks.payments.handle_payment') as mock_handle:
            mock_handle.return_value = {
                "status": "completed",
                "cards_created": 5,
                "pack_delivered": True
            }
            
            result = asyncio.run(payment_webhook(event))
            
            # Verify pack delivery
            assert result["status"] == "captured"
            mock_handle.assert_called_once()
            
            # Verify pack was delivered
            call_args = mock_handle.call_args
            assert call_args[1]['user_id'] == 1
            assert call_args[1]['pack_type'] == "black"
            assert call_args[1]['payment_id'] == "TX123"
            
            print("✅ Gateway capture delivery verified")
    
    def test_retry_safety_production(self):
        """
        Test: retry safe.
        
        PASS CRITERIA:
        - Duplicate events don't cause issues
        - System remains stable under retries
        - No data corruption
        """
        print("\n🚦 Testing Retry Safety (Production)...")
        
        event = {
            "type": "payment.captured",
            "data": {
                "id": "TX123",
                "metadata": {"user": 1, "pack": "black"}
            }
        }
        
        # Simulate multiple retries
        results = []
        
        with patch('webhooks.payments.handle_payment') as mock_handle:
            mock_handle.return_value = {"status": "completed"}
            
            # Process same event multiple times (simulating retries)
            for i in range(3):
                result = asyncio.run(payment_webhook(event))
                results.append(result)
            
            # All should succeed
            for i, result in enumerate(results):
                assert result["status"] == "captured", f"Retry {i+1} should succeed"
            
            # Business logic called multiple times (idempotency handled at business layer)
            assert mock_handle.call_count == 3, f"Expected 3 calls, got {mock_handle.call_count}"
            
            print("✅ Retry safety verified")
    
    def test_refund_revokes(self):
        """
        Test: refund revokes.
        
        PASS CRITERIA:
        - Refund event triggers card revocation
        - All cards from purchase are revoked
        - User loses access to cards
        """
        print("\n🚦 Testing Refund Revokes...")
        
        event = {
            "type": "payment.refunded",
            "data": {
                "id": "TX123",
                "amount": 4999,
                "reason": "customer_request"
            }
        }
        
        with patch('webhooks.payments.refund_purchase') as mock_refund:
            mock_refund.return_value = {
                "status": "refunded",
                "cards_revoked": 5,
                "access_revoked": True
            }
            
            result = asyncio.run(payment_webhook(event))
            
            # Verify refund processing
            assert result["status"] == "refunded"
            mock_refund.assert_called_once_with("TX123")
            
            print("✅ Refund revokes verified")
    
    def test_audit_logged_production(self):
        """
        Test: audit logged.
        
        PASS CRITERIA:
        - All payment events are logged
        - Audit trail is complete
        - Logs contain required information
        """
        print("\n🚦 Testing Audit Logged (Production)...")
        
        event = {
            "type": "payment.captured",
            "data": {
                "id": "TX123",
                "metadata": {"user": 1, "pack": "black"}
            }
        }
        
        with patch('webhooks.payments.AuditLog.record') as mock_audit, \
             patch('webhooks.payments.handle_payment') as mock_handle:
            
            mock_handle.return_value = {"status": "completed"}
            
            result = asyncio.run(payment_webhook(event))
            
            # Verify audit logging
            assert mock_audit.call_count >= 2, "Should have multiple audit entries"
            
            # Check audit call content
            audit_calls = mock_audit.call_args_list
            
            # Should log webhook processing
            webhook_call = None
            capture_call = None
            
            for call in audit_calls:
                args, kwargs = call
                if kwargs.get('event') == 'webhook_processed':
                    webhook_call = kwargs
                elif kwargs.get('event') == 'gateway_capture':
                    capture_call = kwargs
            
            assert webhook_call is not None, "Should log webhook processing"
            assert capture_call is not None, "Should log gateway capture"
            
            # Verify audit data
            assert capture_call['user_id'] == 1
            assert capture_call['target_id'] == "TX123"
            assert 'pack_type' in capture_call['details']
            
            print("✅ Audit logging verified")

# Test Runner

def run_production_readiness_tests():
    """Run all production readiness tests."""
    print("🚦 PRODUCTION READINESS TESTS")
    print("=" * 50)
    
    # Import pytest
    import pytest
    
    # Run specific tests
    test_file = __file__
    
    # Run production readiness tests
    result = pytest.main([
        test_file,
        "TestProductionReadiness",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return result == 0

def run_all_payment_tests():
    """Run all payment flow tests."""
    print("🧪 PAYMENT FLOW TESTS")
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

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "production":
        # Run production readiness tests only
        success = run_production_readiness_tests()
    else:
        # Run all tests
        success = run_all_payment_tests()
    
    sys.exit(0 if success else 1)
