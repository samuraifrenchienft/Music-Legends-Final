# services/payment_gateway.py
"""
Payment Gateway Integration
Handle Stripe payment processing for creator packs
"""

from typing import Dict, Optional, Any
import os
import stripe
from datetime import datetime
from models.audit_minimal import AuditLog

class PaymentGateway:
    """Payment gateway service for Stripe integration"""
    
    def __init__(self):
        # Initialize Stripe with API key from environment
        self.api_key = os.getenv('STRIPE_SECRET_KEY')
        if self.api_key:
            stripe.api_key = self.api_key
        else:
            print("⚠️ Stripe API key not found in environment variables")
    
    def capture_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Capture a payment intent
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Capture result dict
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "Stripe API key not configured",
                    "status": "failed"
                }
            
            # Retrieve the payment intent
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Check if it's in the right state
            if intent.status != 'requires_capture':
                return {
                    "success": False,
                    "error": f"Payment intent not capturable: {intent.status}",
                    "status": intent.status
                }
            
            # Capture the payment
            captured_intent = stripe.PaymentIntent.capture(
                payment_intent_id,
                amount_to_capture=intent.amount
            )
            
            # Log the capture
            AuditLog.record(
                event="payment_captured",
                user_id=0,  # System action
                target_id=payment_intent_id,
                payload={
                    "payment_intent_id": payment_intent_id,
                    "amount_captured": captured_intent.amount_captured,
                    "currency": captured_intent.currency,
                    "captured_at": datetime.utcnow().isoformat(),
                    "stripe_status": captured_intent.status
                }
            )
            
            return {
                "success": True,
                "payment_intent": captured_intent,
                "amount_captured": captured_intent.amount_captured,
                "status": captured_intent.status
            }
            
        except stripe.error.StripeError as e:
            # Log Stripe error
            AuditLog.record(
                event="payment_capture_failed",
                user_id=0,
                target_id=payment_intent_id,
                payload={
                    "payment_intent_id": payment_intent_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
        except Exception as e:
            # Log general error
            AuditLog.record(
                event="payment_capture_error",
                user_id=0,
                target_id=payment_intent_id,
                payload={
                    "payment_intent_id": payment_intent_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
    
    def void_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Void/cancel a payment intent
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Void result dict
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "Stripe API key not configured",
                    "status": "failed"
                }
            
            # Retrieve the payment intent
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Cancel the payment intent
            canceled_intent = stripe.PaymentIntent.cancel(payment_intent_id)
            
            # Log the void
            AuditLog.record(
                event="payment_voided",
                user_id=0,  # System action
                target_id=payment_intent_id,
                payload={
                    "payment_intent_id": payment_intent_id,
                    "canceled_at": datetime.utcnow().isoformat(),
                    "stripe_status": canceled_intent.status,
                    "original_status": intent.status
                }
            )
            
            return {
                "success": True,
                "payment_intent": canceled_intent,
                "status": canceled_intent.status
            }
            
        except stripe.error.StripeError as e:
            # Log Stripe error
            AuditLog.record(
                event="payment_void_failed",
                user_id=0,
                target_id=payment_intent_id,
                payload={
                    "payment_intent_id": payment_intent_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
        except Exception as e:
            # Log general error
            AuditLog.record(
                event="payment_void_error",
                user_id=0,
                target_id=payment_intent_id,
                payload={
                    "payment_intent_id": payment_intent_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
    
    def refund_payment(self, charge_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """
        Refund a payment charge
        
        Args:
            charge_id: Stripe charge ID
            amount: Amount to refund in cents (optional, full refund if None)
            
        Returns:
            Refund result dict
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "Stripe API key not configured",
                    "status": "failed"
                }
            
            # Create refund
            refund_params = {"charge": charge_id}
            if amount:
                refund_params["amount"] = amount
            
            refund = stripe.Refund.create(**refund_params)
            
            # Log the refund
            AuditLog.record(
                event="payment_refunded",
                user_id=0,  # System action
                target_id=charge_id,
                payload={
                    "charge_id": charge_id,
                    "refund_id": refund.id,
                    "amount_refunded": refund.amount,
                    "currency": refund.currency,
                    "refunded_at": datetime.utcnow().isoformat(),
                    "stripe_status": refund.status
                }
            )
            
            return {
                "success": True,
                "refund": refund,
                "amount_refunded": refund.amount,
                "status": refund.status
            }
            
        except stripe.error.StripeError as e:
            # Log Stripe error
            AuditLog.record(
                event="payment_refund_failed",
                user_id=0,
                target_id=charge_id,
                payload={
                    "charge_id": charge_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
        except Exception as e:
            # Log general error
            AuditLog.record(
                event="payment_refund_error",
                user_id=0,
                target_id=charge_id,
                payload={
                    "charge_id": charge_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
    
    def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Get payment status from Stripe
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Payment status dict
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "Stripe API key not configured"
                }
            
            # Retrieve payment intent
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "success": True,
                "payment_intent": intent,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
                "created": intent.created,
                "charges": intent.charges.data if intent.charges else []
            }
            
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def create_payment_intent(self, amount: int, currency: str = "usd", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a payment intent for authorization
        
        Args:
            amount: Amount in cents
            currency: Currency code
            metadata: Additional metadata
            
        Returns:
            Payment intent creation result
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "Stripe API key not configured"
                }
            
            # Create payment intent with capture_method=manual for authorization only
            intent_params = {
                "amount": amount,
                "currency": currency,
                "capture_method": "manual",  # Authorization only
                "confirm": False,  # Don't confirm yet
                "payment_method_types": ["card"]
            }
            
            if metadata:
                intent_params["metadata"] = metadata
            
            intent = stripe.PaymentIntent.create(**intent_params)
            
            # Log creation
            AuditLog.record(
                event="payment_intent_created",
                user_id=0,
                target_id=intent.id,
                payload={
                    "payment_intent_id": intent.id,
                    "amount": amount,
                    "currency": currency,
                    "capture_method": "manual",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": True,
                "payment_intent": intent,
                "client_secret": intent.client_secret,
                "id": intent.id
            }
            
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


# Global gateway instance
gateway = PaymentGateway()


# Example usage
def example_usage():
    """Example of gateway usage"""
    
    # Create payment intent
    print("💳 Creating payment intent...")
    result = gateway.create_payment_intent(999, "usd", {"pack_type": "creator"})
    
    if result["success"]:
        print(f"✅ Payment intent created: {result['id']}")
        print(f"   Client secret: {result['client_secret']}")
        
        # Capture payment
        print("\n💰 Capturing payment...")
        capture_result = gateway.capture_payment(result['id'])
        
        if capture_result["success"]:
            print(f"✅ Payment captured: ${capture_result['amount_captured'] / 100:.2f}")
        else:
            print(f"❌ Capture failed: {capture_result['error']}")
    else:
        print(f"❌ Payment intent creation failed: {result['error']}")


if __name__ == "__main__":
    example_usage()
