"""
Payment Gateway Webhook Handler

Gateway-agnostic adapter that processes payment events from any payment provider.
Maps standardized events to business logic services.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.payment_service import handle_payment
from services.refund_service import refund_purchase
from models.audit_minimal import AuditLog

# Configure logging
logger = logging.getLogger(__name__)

class PaymentWebhookError(Exception):
    """Custom exception for payment webhook errors."""
    pass

class PaymentWebhookHandler:
    """Gateway-agnostic payment webhook processor."""
    
    def __init__(self):
        self.supported_events = {
            "payment.captured": self._handle_payment_captured,
            "payment.refunded": self._handle_payment_refunded,
            "payment.failed": self._handle_payment_failed,
            "payment.pending": self._handle_payment_pending,
        }
    
    async def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a payment webhook event.
        
        Args:
            event: Standardized payment event from gateway
            
        Returns:
            Processing result with status and details
        """
        try:
            # Validate event structure
            event_type = event.get("type")
            event_data = event.get("data", {})
            
            if not event_type:
                raise PaymentWebhookError("Missing event type")
            
            if not event_data:
                raise PaymentWebhookError("Missing event data")
            
            logger.info(f"Processing payment event: {event_type}")
            
            # Route to appropriate handler
            handler = self.supported_events.get(event_type)
            
            if handler:
                result = await handler(event_data)
                
                # Log successful processing
                AuditLog.record(
                    event="webhook_processed",
                    details={
                        "event_type": event_type,
                        "payment_id": event_data.get("id"),
                        "result": result.get("status"),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return result
            else:
                # Unsupported event type
                logger.warning(f"Unsupported event type: {event_type}")
                
                AuditLog.record(
                    event="webhook_ignored",
                    details={
                        "event_type": event_type,
                        "reason": "unsupported_event_type"
                    }
                )
                
                return {"status": "ignored", "reason": "unsupported_event_type"}
        
        except PaymentWebhookError as e:
            logger.error(f"Payment webhook error: {e}")
            
            AuditLog.record(
                event="webhook_error",
                details={
                    "error": str(e),
                    "event": event
                }
            )
            
            return {"status": "error", "error": str(e)}
        
        except Exception as e:
            logger.error(f"Unexpected webhook processing error: {e}")
            
            AuditLog.record(
                event="webhook_critical_error",
                details={
                    "error": str(e),
                    "event": event
                }
            )
            
            return {"status": "error", "error": "processing_failed"}
    
    async def _handle_payment_captured(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment capture event."""
        try:
            payment_id = data.get("id")
            metadata = data.get("metadata", {})
            
            if not payment_id:
                raise PaymentWebhookError("Missing payment ID")
            
            user_id = metadata.get("user")
            pack_type = metadata.get("pack")
            
            if not user_id or not pack_type:
                raise PaymentWebhookError("Missing required metadata (user, pack)")
            
            logger.info(f"Processing captured payment: {payment_id} for user {user_id}")
            
            # Process the payment through payment service
            result = handle_payment(
                user_id=int(user_id),
                pack_type=pack_type,
                payment_id=payment_id
            )
            
            # Record successful capture
            AuditLog.record(
                event="gateway_capture",
                user_id=int(user_id),
                target_id=payment_id,
                details={
                    "pack_type": pack_type,
                    "result": result,
                    "amount": data.get("amount"),
                    "currency": data.get("currency")
                }
            )
            
            logger.info(f"Payment captured successfully: {payment_id}")
            
            return {
                "status": "captured",
                "payment_id": payment_id,
                "user_id": user_id,
                "pack_type": pack_type,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Payment capture failed: {e}")
            raise PaymentWebhookError(f"Capture failed: {str(e)}")
    
    async def _handle_payment_refunded(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment refund event."""
        try:
            payment_id = data.get("id")
            refund_amount = data.get("amount")
            reason = data.get("reason", "customer_request")
            
            if not payment_id:
                raise PaymentWebhookError("Missing payment ID")
            
            logger.info(f"Processing refund: {payment_id} for amount {refund_amount}")
            
            # Process the refund through refund service
            result = refund_purchase(payment_id)
            
            # Record successful refund
            AuditLog.record(
                event="gateway_refund",
                target_id=payment_id,
                details={
                    "refund_amount": refund_amount,
                    "reason": reason,
                    "result": result
                }
            )
            
            logger.info(f"Payment refunded successfully: {payment_id}")
            
            return {
                "status": "refunded",
                "payment_id": payment_id,
                "refund_amount": refund_amount,
                "reason": reason,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Payment refund failed: {e}")
            raise PaymentWebhookError(f"Refund failed: {str(e)}")
    
    async def _handle_payment_failed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment failure event."""
        try:
            payment_id = data.get("id")
            failure_reason = data.get("failure_reason", "unknown")
            metadata = data.get("metadata", {})
            
            if not payment_id:
                raise PaymentWebhookError("Missing payment ID")
            
            user_id = metadata.get("user")
            pack_type = metadata.get("pack")
            
            logger.warning(f"Payment failed: {payment_id} - {failure_reason}")
            
            # Record payment failure
            AuditLog.record(
                event="gateway_failure",
                user_id=int(user_id) if user_id else None,
                target_id=payment_id,
                details={
                    "failure_reason": failure_reason,
                    "pack_type": pack_type,
                    "metadata": metadata
                }
            )
            
            return {
                "status": "failed",
                "payment_id": payment_id,
                "failure_reason": failure_reason,
                "user_id": user_id,
                "pack_type": pack_type
            }
        
        except Exception as e:
            logger.error(f"Payment failure handling failed: {e}")
            raise PaymentWebhookError(f"Failure handling failed: {str(e)}")
    
    async def _handle_payment_pending(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment pending event."""
        try:
            payment_id = data.get("id")
            metadata = data.get("metadata", {})
            
            if not payment_id:
                raise PaymentWebhookError("Missing payment ID")
            
            user_id = metadata.get("user")
            pack_type = metadata.get("pack")
            
            logger.info(f"Payment pending: {payment_id}")
            
            # Record pending payment
            AuditLog.record(
                event="gateway_pending",
                user_id=int(user_id) if user_id else None,
                target_id=payment_id,
                details={
                    "pack_type": pack_type,
                    "metadata": metadata
                }
            )
            
            return {
                "status": "pending",
                "payment_id": payment_id,
                "user_id": user_id,
                "pack_type": pack_type
            }
        
        except Exception as e:
            logger.error(f"Payment pending handling failed: {e}")
            raise PaymentWebhookError(f"Pending handling failed: {str(e)}")

# Global handler instance
webhook_handler = PaymentWebhookHandler()

async def payment_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main webhook entry point - gateway-agnostic payment event processor.
    
    Args:
        event: Standardized payment event from any gateway
        
    Returns:
        Processing result with status and details
    """
    return await webhook_handler.process_event(event)

# Gateway-specific mapping functions

def map_stripe_event(stripe_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Stripe webhook event to standardized format.
    
    Args:
        stripe_event: Raw Stripe webhook event
        
    Returns:
        Standardized payment event
    """
    event_type = stripe_event.get("type", "")
    stripe_data = stripe_event.get("data", {}).get("object", {})
    
    # Map Stripe event types to standard types
    type_mapping = {
        "payment_intent.succeeded": "payment.captured",
        "payment_intent.payment_failed": "payment.failed",
        "payment_intent.canceled": "payment.failed",
        "charge.refunded": "payment.refunded",
        "charge.pending": "payment.pending",
    }
    
    standard_type = type_mapping.get(event_type, event_type)
    
    # Extract common fields
    mapped_event = {
        "type": standard_type,
        "data": {
            "id": stripe_data.get("id"),
            "amount": stripe_data.get("amount"),
            "currency": stripe_data.get("currency"),
            "metadata": stripe_data.get("metadata", {}),
            "created": stripe_data.get("created"),
        }
    }
    
    # Add failure reason if present
    if stripe_data.get("last_payment_error"):
        mapped_event["data"]["failure_reason"] = stripe_data["last_payment_error"].get("message")
    
    # Add refund details
    if event_type == "charge.refunded":
        refunds = stripe_data.get("refunds", {}).get("data", [])
        if refunds:
            refund = refunds[0]  # Take first refund
            mapped_event["data"]["reason"] = refund.get("reason", "customer_request")
            mapped_event["data"]["amount"] = refund.get("amount")
    
    return mapped_event

def map_paypal_event(paypal_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map PayPal webhook event to standardized format.
    
    Args:
        paypal_event: Raw PayPal webhook event
        
    Returns:
        Standardized payment event
    """
    event_type = paypal_event.get("event_type", "")
    resource = paypal_event.get("resource", {})
    
    # Map PayPal event types to standard types
    type_mapping = {
        "PAYMENT.CAPTURE.COMPLETED": "payment.captured",
        "PAYMENT.CAPTURE.DENIED": "payment.failed",
        "PAYMENT.SALE.REFUNDED": "payment.refunded",
        "PAYMENT.SALE.PENDING": "payment.pending",
    }
    
    standard_type = type_mapping.get(event_type, event_type)
    
    # Extract common fields
    mapped_event = {
        "type": standard_type,
        "data": {
            "id": resource.get("id"),
            "amount": resource.get("amount", {}).get("total"),
            "currency": resource.get("amount", {}).get("currency"),
            "metadata": resource.get("custom_id", {}),  # PayPal uses custom_id for metadata
            "created": resource.get("create_time"),
        }
    }
    
    # Add PayPal-specific fields
    if event_type == "PAYMENT.SALE.REFUNDED":
        mapped_event["data"]["reason"] = resource.get("reason_code", "customer_request")
    
    return mapped_event

# Utility functions

def validate_webhook_event(event: Dict[str, Any]) -> bool:
    """
    Validate webhook event structure.
    
    Args:
        event: Webhook event to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["type", "data"]
    
    for field in required_fields:
        if field not in event:
            return False
    
    # Validate data has at least an ID
    if not event["data"].get("id"):
        return False
    
    return True

def extract_payment_metadata(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract payment metadata from event.
    
    Args:
        event: Webhook event
        
    Returns:
        Metadata dictionary
    """
    return event.get("data", {}).get("metadata", {})

def is_payment_event(event_type: str) -> bool:
    """
    Check if event type is payment-related.
    
    Args:
        event_type: Event type to check
        
    Returns:
        True if payment-related, False otherwise
    """
    payment_prefixes = ["payment.", "charge.", "billing."]
    
    return any(event_type.startswith(prefix) for prefix in payment_prefixes)

# Error handling

class WebhookSignatureError(Exception):
    """Exception for webhook signature verification failures."""
    pass

class WebhookProcessingError(Exception):
    """Exception for webhook processing failures."""
    pass

# Logging helpers

def log_webhook_received(event: Dict[str, Any], gateway: str = "unknown"):
    """Log webhook event receipt."""
    logger.info(f"Webhook received from {gateway}: {event.get('type')}")

def log_webhook_processed(event: Dict[str, Any], result: Dict[str, Any]):
    """Log successful webhook processing."""
    logger.info(f"Webhook processed: {event.get('type')} -> {result.get('status')}")

def log_webhook_error(event: Dict[str, Any], error: Exception):
    """Log webhook processing error."""
    logger.error(f"Webhook error for {event.get('type')}: {error}")
