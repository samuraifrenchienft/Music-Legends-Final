"""
Refund Service

Handles refund processing and card revocation for refunded purchases.
Integrates with Stripe webhooks to revoke user cards.
"""

import logging
from typing import Dict, Any, Optional

from models.card import Card
from models.purchase import Purchase

# Configure logging
logger = logging.getLogger(__name__)

def refund_purchase(payment_id: str) -> Dict[str, Any]:
    """
    Process a refund and revoke all cards from the original purchase.
    
    Args:
        payment_id: Stripe payment_intent ID
        
    Returns:
        Processing result with status and details
    """
    try:
        logger.info(f"Processing refund: payment {payment_id}")
        
        # Find the original purchase
        purchase = Purchase.get_by_payment_id(payment_id)
        if not purchase:
            logger.warning(f"No purchase found for payment {payment_id}")
            return {
                "status": "no_purchase",
                "payment_id": payment_id,
                "cards_revoked": 0
            }
        
        # Check if already refunded
        if purchase.status == "refunded":
            logger.info(f"Purchase {payment_id} already refunded")
            return {
                "status": "already_refunded",
                "purchase_id": purchase.id,
                "payment_id": payment_id,
                "cards_revoked": 0
            }
        
        # Get all cards from this purchase
        cards = Card.from_purchase(payment_id)
        revoked_count = 0
        
        # Revoke each card
        for card in cards:
            try:
                card.revoke()
                revoked_count += 1
                logger.debug(f"Revoked card {card.id}")
            except Exception as e:
                logger.error(f"Failed to revoke card {card.id}: {e}")
        
        # Update purchase status
        purchase.update_status("refunded")
        
        logger.info(f"Refund processed: {payment_id} -> {revoked_count} cards revoked")
        
        return {
            "status": "refunded",
            "purchase_id": purchase.id,
            "payment_id": payment_id,
            "cards_revoked": revoked_count,
            "original_amount": purchase.amount
        }
        
    except Exception as e:
        logger.error(f"Refund processing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "cards_revoked": 0
        }

def get_refund_summary(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get summary of a refund including revoked cards.
    
    Args:
        payment_id: Payment ID
        
    Returns:
        Refund summary or None if not found
    """
    try:
        purchase = Purchase.get_by_payment_id(payment_id)
        if not purchase:
            return None
        
        cards = Card.from_purchase(payment_id)
        
        return {
            "purchase": purchase.to_dict(),
            "cards": [card.to_dict() for card in cards],
            "card_count": len(cards),
            "refunded": purchase.status == "refunded",
            "refund_amount": purchase.amount if purchase.status == "refunded" else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get refund summary: {e}")
        return None

# Utility functions

def validate_payment_id(payment_id: str) -> bool:
    """Validate payment ID format."""
    if not payment_id:
        return False
    
    # Basic validation - payment IDs should start with 'pi_' or 'cs_'
    return payment_id.startswith(('pi_', 'cs_'))

def get_refund_statistics() -> Dict[str, Any]:
    """
    Get refund statistics for admin dashboard.
    
    Returns:
        Refund statistics
    """
    try:
        # This would query your database for refund stats
        # For now, return placeholder data
        return {
            "total_refunds": 0,
            "total_cards_revoked": 0,
            "total_amount_refunded": 0,
            "refund_rate": 0.0
        }
    except Exception as e:
        logger.error(f"Failed to get refund statistics: {e}")
        return {}

# Error handling

class RefundServiceError(Exception):
    """Custom exception for refund service errors."""
    pass

class PurchaseNotFoundError(RefundServiceError):
    """Exception when purchase is not found."""
    pass

class AlreadyRefundedError(RefundServiceError):
    """Exception when purchase is already refunded."""
    pass

# Logging helpers

def log_refund_processed(payment_id: str, purchase_id: int, cards_revoked: int):
    """Log successful refund processing."""
    logger.info(f"Refund processed: payment {payment_id}, purchase {purchase_id}, cards {cards_revoked}")

def log_refund_failed(payment_id: str, error: str):
    """Log refund processing failure."""
    logger.error(f"Refund failed: payment {payment_id}, error {error}")

def log_card_revocation(card_id: int, payment_id: str):
    """Log individual card revocation."""
    logger.debug(f"Card revoked: {card_id} for payment {payment_id}")
