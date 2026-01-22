"""
PayPal Payment Gateway Adapter

Maps PayPal webhook events to standardized payment events.
Handles PayPal-specific event parsing and metadata extraction.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from webhooks.payments import (
    validate_webhook_event,
    WebhookSignatureError,
    WebhookProcessingError
)

logger = logging.getLogger(__name__)

class PayPalAdapter:
    """Adapter for PayPal webhook events."""
    
    def __init__(self):
        self.event_mappings = {
            # Payment capture events
            "PAYMENT.CAPTURE.COMPLETED": "payment.captured",
            "PAYMENT.CAPTURE.DENIED": "payment.failed",
            "PAYMENT.CAPTURE.PENDING": "payment.pending",
            
            # Sale events
            "PAYMENT.SALE.COMPLETED": "payment.captured",
            "PAYMENT.SALE.DENIED": "payment.failed",
            "PAYMENT.SALE.PENDING": "payment.pending",
            "PAYMENT.SALE.REFUNDED": "payment.refunded",
            "PAYMENT.SALE.REVERSED": "payment.refunded",
            
            # Authorization events
            "PAYMENT.AUTHORIZATION.CREATED": "payment.pending",
            "PAYMENT.AUTHORIZATION.VOIDED": "payment.failed",
            "PAYMENT.AUTHORIZATION.CAPTURED": "payment.captured",
            
            # Order events
            "CHECKOUT.ORDER.APPROVED": "payment.pending",
            "CHECKOUT.ORDER.COMPLETED": "payment.captured",
            
            # Dispute events
            "CUSTOMER.DISPUTE.CREATED": "payment.disputed",
            "CUSTOMER.DISPUTE.RESOLVED": "payment.dispute_resolved",
        }
    
    def adapt_event(self, paypal_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt PayPal webhook event to standardized format.
        
        Args:
            paypal_event: Raw PayPal webhook event
            
        Returns:
            Standardized payment event
            
        Raises:
            WebhookProcessingError: If event cannot be adapted
        """
        try:
            # Extract basic event information
            paypal_type = paypal_event.get("event_type", "")
            resource = paypal_event.get("resource", {})
            
            if not paypal_type or not resource:
                raise WebhookProcessingError("Invalid PayPal event structure")
            
            # Map to standard event type
            standard_type = self.event_mappings.get(paypal_type, paypal_type)
            
            # Build standardized event
            standard_event = {
                "type": standard_type,
                "data": self._extract_common_data(resource),
                "gateway": "paypal",
                "original_event": paypal_type,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add event-specific data
            self._add_event_specific_data(standard_event, paypal_type, resource)
            
            # Validate the adapted event
            if not validate_webhook_event(standard_event):
                raise WebhookProcessingError("Adapted event validation failed")
            
            logger.info(f"Adapted PayPal event: {paypal_type} -> {standard_type}")
            
            return standard_event
            
        except Exception as e:
            logger.error(f"PayPal event adaptation failed: {e}")
            raise WebhookProcessingError(f"PayPal adaptation failed: {str(e)}")
    
    def _extract_common_data(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common data fields from PayPal resource."""
        common_data = {
            "id": resource.get("id"),
            "status": resource.get("status"),
            "created": resource.get("create_time"),
            "updated": resource.get("update_time"),
        }
        
        # Extract amount information
        if "amount" in resource:
            amount_info = resource["amount"]
            common_data["amount"] = self._parse_amount(amount_info.get("total", "0"))
            common_data["currency"] = amount_info.get("currency", "USD")
        
        # Extract payer information
        if "payer" in resource:
            payer = resource["payer"]
            common_data["payer_id"] = payer.get("payer_id")
            common_data["payer_email"] = payer.get("email_address")
            common_data["payer_name"] = payer.get("name", {}).get("full_name")
        
        # Extract custom metadata (PayPal uses custom_id)
        if "custom_id" in resource:
            try:
                # PayPal custom_id is often JSON string
                metadata = json.loads(resource["custom_id"])
                if isinstance(metadata, dict):
                    common_data["metadata"] = metadata
                else:
                    common_data["metadata"] = {"custom_id": metadata}
            except (json.JSONDecodeError, TypeError):
                common_data["metadata"] = {"custom_id": resource["custom_id"]}
        else:
            common_data["metadata"] = {}
        
        # Extract links for API access
        if "links" in resource:
            common_data["links"] = resource["links"]
        
        return common_data
    
    def _add_event_specific_data(self, standard_event: Dict[str, Any], 
                                paypal_type: str, resource: Dict[str, Any]):
        """Add event-specific data to standardized event."""
        
        if paypal_type in ["PAYMENT.CAPTURE.COMPLETED", "PAYMENT.SALE.COMPLETED"]:
            self._add_success_data(standard_event, resource)
        
        elif paypal_type in ["PAYMENT.CAPTURE.DENIED", "PAYMENT.SALE.DENIED"]:
            self._add_failure_data(standard_event, resource)
        
        elif paypal_type in ["PAYMENT.SALE.REFUNDED", "PAYMENT.SALE.REVERSED"]:
            self._add_refund_data(standard_event, resource)
        
        elif paypal_type in ["PAYMENT.CAPTURE.PENDING", "PAYMENT.SALE.PENDING"]:
            self._add_pending_data(standard_event, resource)
    
    def _add_success_data(self, standard_event: Dict[str, Any], resource: Dict[str, Any]):
        """Add success-specific data."""
        data = standard_event["data"]
        
        # Add transaction fees
        if "transaction_fee" in resource:
            fee_info = resource["transaction_fee"]
            data["transaction_fee"] = self._parse_amount(fee_info.get("value", "0"))
            data["transaction_fee_currency"] = fee_info.get("currency", "USD")
        
        # Add processor response
        if "processor_response" in resource:
            data["processor_response"] = resource["processor_response"]
        
        # Add protection eligibility
        if "seller_protection" in resource:
            protection = resource["seller_protection"]
            data["seller_protection"] = {
                "status": protection.get("status"),
                "dispute_categories": protection.get("dispute_categories", [])
            }
        
        # Add payment method details
        if "payee" in resource:
            payee = resource["payee"]
            data["payee_email"] = payee.get("email_address")
            data["payee_merchant_id"] = payee.get("merchant_id")
    
    def _add_failure_data(self, standard_event: Dict[str, Any], resource: Dict[str, Any]):
        """Add failure-specific data."""
        data = standard_event["data"]
        
        # Extract failure reason
        data["failure_reason"] = resource.get("status_details", {}).get("reason")
        
        # Add processor response for failures
        if "processor_response" in resource:
            data["processor_response"] = resource["processor_response"]
        
        # Add error details if available
        if "error_details" in resource:
            error_details = resource["error_details"]
            data["failure_code"] = error_details.get("issue")
            data["failure_description"] = error_details.get("description")
    
    def _add_refund_data(self, standard_event: Dict[str, Any], resource: Dict[str, Any]):
        """Add refund-specific data."""
        data = standard_event["data"]
        
        # Extract refund details
        data["refund_id"] = resource.get("id")
        data["refund_status"] = resource.get("status")
        data["refund_reason"] = resource.get("reason_code", "customer_request")
        data["refund_created"] = resource.get("create_time")
        
        # Extract refund amount
        if "amount" in resource:
            amount_info = resource["amount"]
            data["refund_amount"] = self._parse_amount(amount_info.get("total", "0"))
            data["refund_currency"] = amount_info.get("currency", "USD")
        
        # Extract sale ID if this is a refund of a sale
        if "sale_id" in resource:
            data["original_payment_id"] = resource["sale_id"]
        elif "parent_payment" in resource:
            data["original_payment_id"] = resource["parent_payment"]
    
    def _add_pending_data(self, standard_event: Dict[str, Any], resource: Dict[str, Any]):
        """Add pending-specific data."""
        data = standard_event["data"]
        
        # Add pending reason
        data["pending_reason"] = resource.get("status_details", {}).get("reason")
        
        # Add expiration time if available
        if "expiration_time" in resource:
            data["expires_at"] = resource["expiration_time"]
        
        # Add links for completion
        if "links" in resource:
            approval_url = None
            execute_url = None
            
            for link in resource["links"]:
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                elif link.get("rel") == "execute":
                    execute_url = link.get("href")
            
            if approval_url:
                data["approval_url"] = approval_url
            if execute_url:
                data["execute_url"] = execute_url
    
    def _parse_amount(self, amount_str: str) -> int:
        """
        Parse PayPal amount string to integer cents.
        
        Args:
            amount_str: Amount string (e.g., "10.99")
            
        Returns:
            Amount in cents (e.g., 1099)
        """
        try:
            # Remove currency symbols and convert to float
            amount_float = float(str(amount_str).replace(',', '').replace('$', ''))
            return int(amount_float * 100)
        except (ValueError, TypeError):
            return 0

class PayPalSignatureVerifier:
    """Verifies PayPal webhook signatures."""
    
    def __init__(self, webhook_id: str):
        self.webhook_id = webhook_id
    
    def verify_signature(self, payload: bytes, headers: Dict[str, str]) -> bool:
        """
        Verify PayPal webhook signature.
        
        Args:
            payload: Raw request payload
            headers: Request headers
            
        Returns:
            True if signature is valid
            
        Raises:
            WebhookSignatureError: If verification fails
        """
        try:
            # PayPal signature verification requires API call
            # This is a simplified version - implement full verification in production
            
            cert_id = headers.get('Paypal-Cert-Id')
            auth_algo = headers.get('Paypal-Auth-Algo')
            transmission_id = headers.get('Paypal-Transmission-Id')
            transmission_sig = headers.get('Paypal-Transmission-Sig')
            transmission_time = headers.get('Paypal-Transmission-Time')
            
            if not all([cert_id, auth_algo, transmission_id, transmission_sig, transmission_time]):
                raise WebhookSignatureError("Missing PayPal signature headers")
            
            # For now, just validate structure and log
            # In production, make API call to PayPal for verification
            logger.info(f"PayPal webhook verification: cert_id={cert_id}, transmission_id={transmission_id}")
            
            # TODO: Implement full PayPal signature verification
            # This requires making API call to PayPal's verification endpoint
            # with all the signature components
            
            return True
            
        except Exception as e:
            logger.error(f"PayPal signature verification error: {e}")
            raise WebhookSignatureError(f"Verification failed: {str(e)}")

# Utility functions

def create_paypal_adapter() -> PayPalAdapter:
    """Create and return PayPal adapter instance."""
    return PayPalAdapter()

def create_paypal_verifier(webhook_id: str) -> PayPalSignatureVerifier:
    """Create and return PayPal signature verifier."""
    return PayPalSignatureVerifier(webhook_id)

def extract_paypal_metadata(paypal_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from PayPal event.
    
    Args:
        paypal_event: PayPal webhook event
        
    Returns:
        Metadata dictionary
    """
    resource = paypal_event.get("resource", {})
    
    if "custom_id" in resource:
        try:
            metadata = json.loads(resource["custom_id"])
            return metadata if isinstance(metadata, dict) else {"custom_id": metadata}
        except (json.JSONDecodeError, TypeError):
            return {"custom_id": resource["custom_id"]}
    
    return {}

def is_paypal_sandbox(paypal_event: Dict[str, Any]) -> bool:
    """
    Check if PayPal event is from sandbox environment.
    
    Args:
        paypal_event: PayPal webhook event
        
    Returns:
        True if sandbox, False otherwise
    """
    # PayPal events typically include environment info
    # Check for sandbox indicators in resource URLs or metadata
    resource = paypal_event.get("resource", {})
    
    # Check for sandbox URLs
    if "links" in resource:
        for link in resource["links"]:
            href = link.get("href", "")
            if "sandbox.paypal.com" in href:
                return True
    
    # Check for sandbox-specific fields
    if resource.get("environment") == "sandbox":
        return True
    
    return False

def get_paypal_event_id(paypal_event: Dict[str, Any]) -> Optional[str]:
    """
    Extract PayPal event ID.
    
    Args:
        paypal_event: PayPal webhook event
        
    Returns:
        Event ID or None if not found
    """
    return paypal_event.get("id")

def get_paypal_resource_id(paypal_event: Dict[str, Any]) -> Optional[str]:
    """
    Extract resource ID from PayPal event.
    
    Args:
        paypal_event: PayPal webhook event
        
    Returns:
        Resource ID or None if not found
    """
    return paypal_event.get("resource", {}).get("id")

# Error handling

class PayPalAdapterError(Exception):
    """Custom exception for PayPal adapter errors."""
    pass

class PayPalVerificationError(Exception):
    """Custom exception for PayPal verification errors."""
    pass

# Logging helpers

def log_paypal_event_received(paypal_event: Dict[str, Any]):
    """Log PayPal event receipt."""
    event_id = get_paypal_event_id(paypal_event)
    event_type = paypal_event.get("event_type")
    resource_id = get_paypal_resource_id(paypal_event)
    sandbox = is_paypal_sandbox(paypal_event)
    
    logger.info(f"PayPal event received: {event_type} ({event_id}) - Resource: {resource_id} - {'SANDBOX' if sandbox else 'LIVE'}")

def log_paypal_event_processed(paypal_event: Dict[str, Any], result: Dict[str, Any]):
    """Log successful PayPal event processing."""
    event_id = get_paypal_event_id(paypal_event)
    event_type = paypal_event.get("event_type")
    
    logger.info(f"PayPal event processed: {event_type} ({event_id}) -> {result.get('status')}")

def log_paypal_event_error(paypal_event: Dict[str, Any], error: Exception):
    """Log PayPal event processing error."""
    event_id = get_paypal_event_id(paypal_event)
    event_type = paypal_event.get("event_type")
    
    logger.error(f"PayPal event error: {event_type} ({event_id}) - {error}")
