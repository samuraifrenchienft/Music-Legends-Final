"""
Stripe Checkout Service

Creates Stripe checkout sessions for pack purchases.
Handles pricing, metadata, and redirect URLs.
"""

import stripe
import os
import logging
from typing import Dict, Any, Optional

# Load environment variables from .env.txt
try:
    from dotenv import load_dotenv
    load_dotenv('.env.txt')
except ImportError:
    # Fallback if dotenv not available
    pass

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET")

# Configure logging
logger = logging.getLogger(__name__)

# Pack pricing configuration (in cents)
PACK_PRICING = {
    "black": 999,      # $9.99
    "gold": 699,       # $6.99
    "silver": 499,     # $4.99
    "starter": 299,    # $2.99
    "founder_black": 4999,  # $49.99
    "founder_gold": 2999,   # $29.99
}

# Pack display names
PACK_NAMES = {
    "black": "Black Pack",
    "gold": "Gold Pack", 
    "silver": "Silver Pack",
    "starter": "Starter Pack",
    "founder_black": "Founder Black Pack",
    "founder_gold": "Founder Gold Pack",
}

def create_pack_checkout(user_id: int, pack: str, success_url: str = None, cancel_url: str = None) -> str:
    """
    Create a Stripe checkout session for pack purchase.
    
    Args:
        user_id: Discord user ID
        pack: Pack type identifier
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect after cancelled payment
        
    Returns:
        Checkout session URL
        
    Raises:
        ValueError: If pack type is invalid
        stripe.error.StripeError: If checkout creation fails
    """
    try:
        # Validate pack type
        if pack not in PACK_PRICING:
            raise ValueError(f"Invalid pack type: {pack}")
        
        # Get pack details
        price = PACK_PRICING[pack]
        name = PACK_NAMES.get(pack, pack.title())
        
        # Default URLs if not provided
        if not success_url:
            success_url = "https://your.site/success"
        if not cancel_url:
            cancel_url = "https://your.site/cancel"
        
        logger.info(f"Creating checkout session for user {user_id}, pack {pack} (${price/100:.2f})")
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            payment_method_types=["card"],
            billing_address_collection="auto",
            shipping_address_collection=None,  # No shipping for digital goods
            
            metadata={
                "user_id": str(user_id),
                "pack": pack,
                "created_at": str(int(time.time()))
            },
            
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": price,
                    "product_data": {
                        "name": name,
                        "description": f"Digital pack containing {pack} cards",
                        "images": [],  # Add pack images if available
                        "metadata": {
                            "pack_type": pack,
                            "digital_good": "true"
                        }
                    },
                    "tax_behavior": "exclusive"  # No tax for digital goods
                },
                "quantity": 1
            }],
            
            # Session configuration
            allow_promotion_codes=False,  # No discounts for now
            automatic_tax={"enabled": False},
            invoice_creation=None,  # No invoice for one-time payment
            
            # Customer info
            customer_email=None,  # Don't pre-fill email for privacy
            
            # UI customization
            ui_mode="hosted",
            
            # Payment settings
            payment_intent_data={
                "metadata": {
                    "user_id": str(user_id),
                    "pack": pack,
                    "checkout_session": "true"
                }
            }
        )
        
        logger.info(f"Checkout session created: {session.id} for user {user_id}")
        
        return session.url
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout creation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Checkout session creation failed: {e}")
        raise

def create_subscription_checkout(user_id: int, plan: str) -> str:
    """
    Create a Stripe checkout session for subscription (future feature).
    
    Args:
        user_id: Discord user ID
        plan: Subscription plan identifier
        
    Returns:
        Checkout session URL
    """
    # Placeholder for future subscription functionality
    raise NotImplementedError("Subscription checkout not yet implemented")

def get_checkout_session(session_id: str) -> Dict[str, Any]:
    """
    Retrieve a checkout session by ID.
    
    Args:
        session_id: Stripe checkout session ID
        
    Returns:
        Checkout session object
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve checkout session {session_id}: {e}")
        raise

def validate_checkout_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a checkout session and extract relevant data.
    
    Args:
        session: Stripe checkout session object
        
    Returns:
        Validated session data
        
    Raises:
        ValueError: If session is invalid
    """
    try:
        # Check session status
        if session.get("status") != "complete":
            raise ValueError(f"Session not complete: {session.get('status')}")
        
        # Check payment status
        if session.get("payment_status") != "paid":
            raise ValueError(f"Payment not completed: {session.get('payment_status')}")
        
        # Extract metadata
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        pack = metadata.get("pack")
        
        if not user_id or not pack:
            raise ValueError("Missing required metadata")
        
        # Validate user_id
        try:
            user_id = int(user_id)
        except ValueError:
            raise ValueError(f"Invalid user_id: {user_id}")
        
        # Validate pack
        if pack not in PACK_PRICING:
            raise ValueError(f"Invalid pack type: {pack}")
        
        return {
            "user_id": user_id,
            "pack": pack,
            "session_id": session.get("id"),
            "amount_total": session.get("amount_total"),
            "currency": session.get("currency"),
            "payment_intent": session.get("payment_intent"),
            "customer": session.get("customer")
        }
        
    except Exception as e:
        logger.error(f"Checkout session validation failed: {e}")
        raise

def get_pack_pricing() -> Dict[str, Dict[str, Any]]:
    """
    Get all pack pricing information.
    
    Returns:
        Dictionary with pack pricing details
    """
    return {
        pack: {
            "price_cents": price,
            "price_usd": price / 100,
            "name": PACK_NAMES.get(pack, pack.title())
        }
        for pack, price in PACK_PRICING.items()
    }

def get_pack_price(pack: str) -> int:
    """
    Get price for a specific pack.
    
    Args:
        pack: Pack type identifier
        
    Returns:
        Price in cents
        
    Raises:
        ValueError: If pack type is invalid
    """
    if pack not in PACK_PRICING:
        raise ValueError(f"Invalid pack type: {pack}")
    
    return PACK_PRICING[pack]

def list_available_packs() -> list:
    """
    Get list of available pack types.
    
    Returns:
        List of pack identifiers
    """
    return list(PACK_PRICING.keys())

# Utility functions

import time

def format_price_cents_to_usd(cents: int) -> str:
    """Convert price in cents to USD string."""
    return f"${cents/100:.2f}"

def format_pack_description(pack: str) -> str:
    """Get formatted description for pack."""
    price = get_pack_price(pack)
    name = PACK_NAMES.get(pack, pack.title())
    return f"{name} - {format_price_cents_to_usd(price)}"

# Error handling

class CheckoutError(Exception):
    """Custom exception for checkout errors."""
    pass

class InvalidPackError(CheckoutError):
    """Exception for invalid pack types."""
    pass

class StripeCheckoutError(CheckoutError):
    """Exception for Stripe checkout errors."""
    pass

# Logging helpers

def log_checkout_created(user_id: int, pack: str, session_id: str, price: int):
    """Log successful checkout creation."""
    logger.info(f"Checkout created: user {user_id}, pack {pack}, session {session_id}, price {format_price_cents_to_usd(price)}")

def log_checkout_completed(user_id: int, pack: str, session_id: str, amount: int):
    """Log successful checkout completion."""
    logger.info(f"Checkout completed: user {user_id}, pack {pack}, session {session_id}, amount {format_price_cents_to_usd(amount)}")

def log_checkout_failed(user_id: int, pack: str, error: str):
    """Log checkout failure."""
    logger.error(f"Checkout failed: user {user_id}, pack {pack}, error {error}")
