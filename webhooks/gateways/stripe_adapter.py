"""
Stripe Payment Gateway Adapter

Maps Stripe webhook events to standardized payment events.
Handles Stripe-specific event parsing and metadata extraction.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from webhooks.payments import (
    validate_webhook_event,
    WebhookSignatureError,
    WebhookProcessingError
)

logger = logging.getLogger(__name__)

class StripeAdapter:
    """Adapter for Stripe webhook events."""
    
    def __init__(self):
        self.event_mappings = {
            # Payment Intent events
            "payment_intent.succeeded": "payment.captured",
            "payment_intent.payment_failed": "payment.failed",
            "payment_intent.canceled": "payment.failed",
            "payment_intent.requires_action": "payment.pending",
            "payment_intent.processing": "payment.pending",
            
            # Charge events
            "charge.succeeded": "payment.captured",
            "charge.failed": "payment.failed",
            "charge.pending": "payment.pending",
            "charge.refunded": "payment.refunded",
            "charge.dispute.created": "payment.disputed",
            
            # Subscription events (if applicable)
            "invoice.payment_succeeded": "payment.captured",
            "invoice.payment_failed": "payment.failed",
        }
    
    def adapt_event(self, stripe_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt Stripe webhook event to standardized format.
        
        Args:
            stripe_event: Raw Stripe webhook event
            
        Returns:
            Standardized payment event
            
        Raises:
            WebhookProcessingError: If event cannot be adapted
        """
        try:
            # Extract basic event information
            stripe_type = stripe_event.get("type", "")
            stripe_data = stripe_event.get("data", {}).get("object", {})
            
            if not stripe_type or not stripe_data:
                raise WebhookProcessingError("Invalid Stripe event structure")
            
            # Map to standard event type
            standard_type = self.event_mappings.get(stripe_type, stripe_type)
            
            # Build standardized event
            standard_event = {
                "type": standard_type,
                "data": self._extract_common_data(stripe_data),
                "gateway": "stripe",
                "original_event": stripe_type,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add event-specific data
            self._add_event_specific_data(standard_event, stripe_type, stripe_data)
            
            # Validate the adapted event
            if not validate_webhook_event(standard_event):
                raise WebhookProcessingError("Adapted event validation failed")
            
            logger.info(f"Adapted Stripe event: {stripe_type} -> {standard_type}")
            
            return standard_event
            
        except Exception as e:
            logger.error(f"Stripe event adaptation failed: {e}")
            raise WebhookProcessingError(f"Stripe adaptation failed: {str(e)}")
    
    def _extract_common_data(self, stripe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common data fields from Stripe object."""
        common_data = {
            "id": stripe_data.get("id"),
            "amount": stripe_data.get("amount"),
            "currency": stripe_data.get("currency"),
            "metadata": stripe_data.get("metadata", {}),
            "created": stripe_data.get("created"),
            "status": stripe_data.get("status"),
        }
        
        # Extract customer information
        if "customer" in stripe_data:
            common_data["customer_id"] = stripe_data["customer"]
        
        # Extract payment method information
        if "payment_method" in stripe_data:
            common_data["payment_method_id"] = stripe_data["payment_method"]
        
        return common_data
    
    def _add_event_specific_data(self, standard_event: Dict[str, Any], 
                                stripe_type: str, stripe_data: Dict[str, Any]):
        """Add event-specific data to standardized event."""
        
        if stripe_type in ["payment_intent.succeeded", "charge.succeeded"]:
            self._add_success_data(standard_event, stripe_data)
        
        elif stripe_type in ["payment_intent.payment_failed", "charge.failed"]:
            self._add_failure_data(standard_event, stripe_data)
        
        elif stripe_type == "charge.refunded":
            self._add_refund_data(standard_event, stripe_data)
        
        elif stripe_type in ["payment_intent.requires_action", "payment_intent.processing"]:
            self._add_pending_data(standard_event, stripe_data)
    
    def _add_success_data(self, standard_event: Dict[str, Any], stripe_data: Dict[str, Any]):
        """Add success-specific data."""
        data = standard_event["data"]
        
        # Add charge information if available
        if "charges" in stripe_data and stripe_data["charges"]["data"]:
            charge = stripe_data["charges"]["data"][0]
            data["charge_id"] = charge.get("id")
            data["receipt_url"] = charge.get("receipt_url")
            data["payment_method_details"] = charge.get("payment_method_details", {})
        
        # Add confirmation details
        data["confirmation_method"] = stripe_data.get("confirmation_method")
        data["capture_method"] = stripe_data.get("capture_method")
    
    def _add_failure_data(self, standard_event: Dict[str, Any], stripe_data: Dict[str, Any]):
        """Add failure-specific data."""
        data = standard_event["data"]
        
        # Extract failure reason
        if "last_payment_error" in stripe_data:
            error = stripe_data["last_payment_error"]
            data["failure_reason"] = error.get("message")
            data["failure_code"] = error.get("code")
            data["failure_type"] = error.get("type")
            data["decline_code"] = error.get("decline_code")
        else:
            data["failure_reason"] = stripe_data.get("outcome", {}).get("reason")
            data["failure_code"] = stripe_data.get("outcome", {}).get("seller_message")
        
        # Add outcome details
        if "outcome" in stripe_data:
            outcome = stripe_data["outcome"]
            data["risk_level"] = outcome.get("risk_level")
            data["risk_score"] = outcome.get("risk_score")
    
    def _add_refund_data(self, standard_event: Dict[str, Any], stripe_data: Dict[str, Any]):
        """Add refund-specific data."""
        data = standard_event["data"]
        
        # Extract refund details
        if "refunds" in stripe_data and stripe_data["refunds"]["data"]:
            refund = stripe_data["refunds"]["data"][0]
            data["refund_id"] = refund.get("id")
            data["refund_amount"] = refund.get("amount")
            data["refund_reason"] = refund.get("reason")
            data["refund_status"] = refund.get("status")
            data["refund_created"] = refund.get("created")
            
            # Add refund metadata
            if "metadata" in refund:
                data["refund_metadata"] = refund["metadata"]
    
    def _add_pending_data(self, standard_event: Dict[str, Any], stripe_data: Dict[str, Any]):
        """Add pending-specific data."""
        data = standard_event["data"]
        
        # Add next action information
        if "next_action" in stripe_data:
            next_action = stripe_data["next_action"]
            data["next_action_type"] = next_action.get("type")
            data["next_action_url"] = next_action.get("redirect_to_url", {}).get("url")
            data["next_action_use_stripe_sdk"] = next_action.get("use_stripe_sdk")
        
        # Add processing details
        data["processing_until"] = stripe_data.get("processing_until")

class StripeSignatureVerifier:
    """Verifies Stripe webhook signatures."""
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
    
    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """
        Verify Stripe webhook signature.
        
        Args:
            payload: Raw request payload
            signature_header: Stripe-Signature header value
            
        Returns:
            True if signature is valid
            
        Raises:
            WebhookSignatureError: If verification fails
        """
        try:
            import hmac
            import hashlib
            import time
            
            if not self.webhook_secret:
                raise WebhookSignatureError("Missing webhook secret")
            
            # Parse signature header
            stripe_signature = signature_header
            timestamp = None
            signatures = []
            
            for item in stripe_signature.split(','):
                key, value = item.split('=', 1)
                if key == 't':
                    timestamp = value
                elif key == 'v1':
                    signatures.append(value)
            
            if not timestamp or not signatures:
                raise WebhookSignatureError("Invalid signature format")
            
            # Check timestamp tolerance (5 minutes)
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:
                raise WebhookSignatureError("Timestamp too old")
            
            # Construct expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            for signature in signatures:
                if hmac.compare_digest(signature, expected_signature):
                    return True
            
            raise WebhookSignatureError("Signature verification failed")
            
        except Exception as e:
            logger.error(f"Stripe signature verification error: {e}")
            raise WebhookSignatureError(f"Verification failed: {str(e)}")

# Utility functions

def create_stripe_adapter() -> StripeAdapter:
    """Create and return Stripe adapter instance."""
    return StripeAdapter()

def create_stripe_verifier(webhook_secret: str) -> StripeSignatureVerifier:
    """Create and return Stripe signature verifier."""
    return StripeSignatureVerifier(webhook_secret)

def extract_stripe_metadata(stripe_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from Stripe event.
    
    Args:
        stripe_event: Stripe webhook event
        
    Returns:
        Metadata dictionary
    """
    stripe_data = stripe_event.get("data", {}).get("object", {})
    return stripe_data.get("metadata", {})

def is_stripe_test_mode(stripe_event: Dict[str, Any]) -> bool:
    """
    Check if Stripe event is from test mode.
    
    Args:
        stripe_event: Stripe webhook event
        
    Returns:
        True if test mode, False otherwise
    """
    # Check livemode flag in event or object
    livemode = stripe_event.get("livemode", True)
    object_livemode = stripe_event.get("data", {}).get("object", {}).get("livemode", True)
    
    return not (livemode and object_livemode)

def get_stripe_event_id(stripe_event: Dict[str, Any]) -> Optional[str]:
    """
    Extract Stripe event ID.
    
    Args:
        stripe_event: Stripe webhook event
        
    Returns:
        Event ID or None if not found
    """
    return stripe_event.get("id")

def get_stripe_payment_intent_id(stripe_event: Dict[str, Any]) -> Optional[str]:
    """
    Extract payment intent ID from Stripe event.
    
    Args:
        stripe_event: Stripe webhook event
        
    Returns:
        Payment intent ID or None if not found
    """
    stripe_data = stripe_event.get("data", {}).get("object", {})
    
    # For payment intent events
    if stripe_data.get("object") == "payment_intent":
        return stripe_data.get("id")
    
    # For charge events
    if stripe_data.get("object") == "charge":
        return stripe_data.get("payment_intent")
    
    return None

# Error handling

class StripeAdapterError(Exception):
    """Custom exception for Stripe adapter errors."""
    pass

class StripeVerificationError(Exception):
    """Custom exception for Stripe verification errors."""
    pass

# Logging helpers

def log_stripe_event_received(stripe_event: Dict[str, Any]):
    """Log Stripe event receipt."""
    event_id = get_stripe_event_id(stripe_event)
    event_type = stripe_event.get("type")
    livemode = stripe_event.get("livemode", True)
    
    logger.info(f"Stripe event received: {event_type} ({event_id}) - {'LIVE' if livemode else 'TEST'}")

def log_stripe_event_processed(stripe_event: Dict[str, Any], result: Dict[str, Any]):
    """Log successful Stripe event processing."""
    event_id = get_stripe_event_id(stripe_event)
    event_type = stripe_event.get("type")
    
    logger.info(f"Stripe event processed: {event_type} ({event_id}) -> {result.get('status')}")

def log_stripe_event_error(stripe_event: Dict[str, Any], error: Exception):
    """Log Stripe event processing error."""
    event_id = get_stripe_event_id(stripe_event)
    event_type = stripe_event.get("type")
    
    logger.error(f"Stripe event error: {event_type} ({event_id}) - {error}")
