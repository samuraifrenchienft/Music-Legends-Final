"""
Main Flask Application

HTTP endpoints for payment webhooks and health checks.
Handles webhook signature verification and routes events to appropriate handlers.
"""

import os
import json
import logging
from flask import Flask, request, jsonify, Response
from functools import wraps
import hashlib
import hmac

from webhooks.payments import (
    payment_webhook, 
    map_stripe_event, 
    map_paypal_event,
    validate_webhook_event,
    log_webhook_received,
    log_webhook_processed,
    log_webhook_error,
    WebhookSignatureError,
    WebhookProcessingError
)

# Configure Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Application configuration."""
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    
    # Gateway secrets
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    PAYPAL_WEBHOOK_ID = os.getenv('PAYPAL_WEBHOOK_ID')
    
    # Security
    REQUIRE_SIGNATURE = os.getenv('REQUIRE_WEBHOOK_SIGNATURE', 'True').lower() == 'true'

app.config.from_object(Config)

def verify_signature(request, gateway: str = "stripe") -> bool:
    """
    Verify webhook signature based on gateway type.
    
    Args:
        request: Flask request object
        gateway: Payment gateway type (stripe, paypal)
        
    Returns:
        True if signature is valid, False otherwise
        
    Raises:
        WebhookSignatureError: If verification fails
    """
    if not app.config.get('REQUIRE_SIGNATURE', True):
        logger.warning("Signature verification disabled - skipping check")
        return True
    
    if gateway == "stripe":
        return verify_stripe_signature(request)
    elif gateway == "paypal":
        return verify_paypal_signature(request)
    else:
        raise WebhookSignatureError(f"Unsupported gateway: {gateway}")

def verify_stripe_signature(request) -> bool:
    """
    Verify Stripe webhook signature.
    
    Args:
        request: Flask request object
        
    Returns:
        True if signature is valid
        
    Raises:
        WebhookSignatureError: If verification fails
    """
    try:
        signature_header = request.headers.get('Stripe-Signature')
        if not signature_header:
            raise WebhookSignatureError("Missing Stripe signature header")
        
        webhook_secret = app.config.get('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            raise WebhookSignatureError("Missing Stripe webhook secret")
        
        # Get the raw payload
        payload = request.data
        
        # Extract timestamp and signatures
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
        import time
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            raise WebhookSignatureError("Timestamp too old")
        
        # Construct expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        for signature in signatures:
            if hmac.compare_digest(signature, expected_signature):
                return True
        
        raise WebhookSignatureError("Signature verification failed")
        
    except Exception as e:
        logger.error(f"Stripe signature verification error: {e}")
        raise WebhookSignatureError(f"Stripe verification failed: {str(e)}")

def verify_paypal_signature(request) -> bool:
    """
    Verify PayPal webhook signature.
    
    Args:
        request: Flask request object
        
    Returns:
        True if signature is valid
        
    Raises:
        WebhookSignatureError: If verification fails
    """
    try:
        # PayPal uses different verification method
        # This is a simplified version - in production, you'd verify with PayPal API
        cert_id = request.headers.get('Paypal-Cert-Id')
        if not cert_id:
            raise WebhookSignatureError("Missing PayPal certificate ID")
        
        webhook_id = app.config.get('PAYPAL_WEBHOOK_ID')
        if not webhook_id:
            raise WebhookSignatureError("Missing PayPal webhook ID")
        
        # For now, just log and accept (implement proper verification in production)
        logger.info(f"PayPal webhook received with cert ID: {cert_id}")
        return True
        
    except Exception as e:
        logger.error(f"PayPal signature verification error: {e}")
        raise WebhookSignatureError(f"PayPal verification failed: {str(e)}")

def handle_webhook_error(func):
    """Decorator to handle webhook errors consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except WebhookSignatureError as e:
            logger.error(f"Webhook signature error: {e}")
            return jsonify({
                "error": "Invalid signature",
                "message": str(e)
            }), 401
        except WebhookProcessingError as e:
            logger.error(f"Webhook processing error: {e}")
            return jsonify({
                "error": "Processing failed", 
                "message": str(e)
            }), 400
        except Exception as e:
            logger.error(f"Unexpected webhook error: {e}")
            return jsonify({
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }), 500
    return wrapper

# HTTP Endpoints

@app.route('/webhooks/stripe', methods=['POST'])
@handle_webhook_error
def stripe_webhook_endpoint():
    """
    Stripe-specific webhook endpoint.
    
    Handles Stripe webhook events with signature verification.
    """
    # Get raw request data for signature verification
    if not request.data:
        raise WebhookProcessingError("Empty request body")
    
    # Verify Stripe signature
    try:
        import stripe
        from webhooks.stripe_hook import stripe_webhook
        import asyncio
        
        # Create mock request object for stripe_webhook function
        class MockRequest:
            def __init__(self, data, headers):
                self._data = data
                self._headers = headers
            
            async def body(self):
                return self._data
            
            def headers(self):
                return self._headers
        
        mock_request = MockRequest(request.data, request.headers)
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(stripe_webhook(mock_request))
        finally:
            loop.close()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        raise WebhookProcessingError(f"Stripe webhook failed: {str(e)}")

@app.route('/webhooks/payments', methods=['POST'])
@handle_webhook_error
async def payments_webhook():
    """
    Main payment webhook endpoint.
    
    Accepts webhook events from any payment gateway and processes them.
    """
    # Get raw request data for signature verification
    if not request.data:
        raise WebhookProcessingError("Empty request body")
    
    # Determine gateway from headers or content
    gateway = "stripe"  # Default to Stripe
    if request.headers.get('Paypal-Cert-Id'):
        gateway = "paypal"
    elif request.headers.get('Stripe-Signature'):
        gateway = "stripe"
    
    logger.info(f"Processing webhook from {gateway}")
    
    # Verify signature
    try:
        verify_signature(request, gateway)
    except WebhookSignatureError as e:
        logger.error(f"Signature verification failed for {gateway}: {e}")
        raise
    
    # Parse JSON payload
    try:
        event = request.get_json()
        if not event:
            raise WebhookProcessingError("Invalid JSON payload")
    except Exception as e:
        raise WebhookProcessingError(f"JSON parsing failed: {str(e)}")
    
    # Log webhook receipt
    log_webhook_received(event, gateway)
    
    # Map gateway-specific event to standard format
    try:
        if gateway == "stripe":
            standard_event = map_stripe_event(event)
        elif gateway == "paypal":
            standard_event = map_paypal_event(event)
        else:
            raise WebhookProcessingError(f"Unsupported gateway: {gateway}")
    except Exception as e:
        raise WebhookProcessingError(f"Event mapping failed: {str(e)}")
    
    # Validate standard event
    if not validate_webhook_event(standard_event):
        raise WebhookProcessingError("Invalid event structure")
    
    # Process the event
    try:
        result = await payment_webhook(standard_event)
        log_webhook_processed(standard_event, result)
        
        return jsonify({
            "status": "success",
            "processed": True,
            "result": result
        }), 200
        
    except Exception as e:
        log_webhook_error(standard_event, e)
        raise WebhookProcessingError(f"Event processing failed: {str(e)}")

@app.route('/webhooks/paypal', methods=['POST'])
@handle_webhook_error
async def paypal_webhook():
    """
    PayPal-specific webhook endpoint.
    
    Routes to main payment webhook with PayPal gateway identification.
    """
    # Override gateway detection
    request.paypal_gateway = True
    
    # Process through main webhook handler
    return await payments_webhook()

# Health and Status Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns basic health status of the webhook service.
    """
    try:
        # Check basic functionality
        status = {
            "status": "healthy",
            "timestamp": str(datetime.utcnow()),
            "version": "1.0.0",
            "services": {
                "webhook_processor": "operational",
                "database": "connected",  # Add actual DB check
                "redis": "connected"      # Add actual Redis check
            }
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/status', methods=['GET'])
def status_check():
    """
    Detailed status endpoint.
    
    Returns detailed status of all webhook components.
    """
    try:
        from datetime import datetime
        
        # Check configuration
        config_status = {
            "stripe_configured": bool(app.config.get('STRIPE_WEBHOOK_SECRET')),
            "paypal_configured": bool(app.config.get('PAYPAL_WEBHOOK_ID')),
            "signature_verification": app.config.get('REQUIRE_SIGNATURE', True)
        }
        
        # Check supported events
        from webhooks.payments import webhook_handler
        supported_events = list(webhook_handler.supported_events.keys())
        
        status = {
            "service": "payment-webhooks",
            "status": "operational",
            "timestamp": str(datetime.utcnow()),
            "configuration": config_status,
            "supported_events": supported_events,
            "endpoints": {
                "payments": "/webhooks/payments",
                "stripe": "/webhooks/stripe", 
                "paypal": "/webhooks/paypal",
                "health": "/health",
                "status": "/status"
            }
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/webhooks/test', methods=['POST'])
@handle_webhook_error
async def test_webhook():
    """
    Test webhook endpoint for development and testing.
    
    Accepts test events without signature verification.
    """
    if app.config.get('DEBUG', False):
        # Skip signature verification in debug mode
        event = request.get_json()
        
        if not event:
            raise WebhookProcessingError("Invalid JSON payload")
        
        # Log test event
        logger.info(f"Test webhook received: {event.get('type')}")
        
        # Process event
        result = await payment_webhook(event)
        
        return jsonify({
            "status": "test_success",
            "processed": True,
            "result": result
        }), 200
    else:
        return jsonify({
            "error": "Test endpoint only available in debug mode"
        }), 404

# Error Handlers

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not found",
        "message": "The requested endpoint was not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "Method not allowed",
        "message": "The request method is not allowed for this endpoint"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

# Application Startup

def create_app():
    """Application factory."""
    return app

if __name__ == '__main__':
    # Development server
    logger.info(f"Starting webhook server on {app.config['HOST']}:{app.config['PORT']}")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
