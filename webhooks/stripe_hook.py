"""
Stripe Webhook Handler

Direct Stripe webhook implementation for checkout sessions and refunds.
Handles Stripe-specific event types and integrates with payment services.
"""

import stripe
import os
import logging
import json
from typing import Dict, Any

# Load environment variables from .env.txt
try:
    from dotenv import load_dotenv
    load_dotenv('.env.txt')
except ImportError:
    # Fallback if dotenv not available
    pass

from services.payment_service import handle_payment
from services.refund_service import refund_purchase
from models.audit_minimal import AuditLog
from ui.receipts import purchase_embed, delivery_embed, refund_embed, admin_sale_embed, admin_refund_embed

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET")
WH_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Configure logging
logger = logging.getLogger(__name__)

async def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    
    Args:
        request: FastAPI/Flask request object
        
    Returns:
        Response dictionary with status
    """
    try:
        # Get payload and signature
        payload = await request.body()
        
        # Handle both function and dict headers
        headers = request.headers() if callable(request.headers) else request.headers
        sig = headers.get("stripe-signature")
        
        if not sig:
            logger.error("Missing Stripe signature")
            return {"error": "Missing signature"}, 400
        
        # Verify webhook signature
        try:
            if not WH_SECRET:
                logger.error("STRIPE_WEBHOOK_SECRET not configured")
                return {"error": "Webhook secret not configured"}, 500

            event = stripe.Webhook.construct_event(
                payload, sig, WH_SECRET
            )
            
        except Exception as e:
            logger.error(f"Stripe webhook construction failed: {e}")
            return {"error": "Webhook construction failed"}, 400
        
        logger.info(f"Processing Stripe event: {event['type']}")
        
        # ---------- PAYMENT CAPTURE ----------
        if event["type"] == "checkout.session.completed":
            return await handle_checkout_session_completed(event)
        
        # ---------- REFUND ----------
        elif event["type"] == "charge.refunded":
            return await handle_charge_refunded(event)
        
        # ---------- PAYMENT FAILED ----------
        elif event["type"] == "checkout.session.expired":
            return await handle_checkout_session_expired(event)
        
        # ---------- OTHER EVENTS ----------
        else:
            logger.info(f"Ignoring Stripe event: {event['type']}")
            return {"status": "ignored"}
            
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        return {"error": "Processing failed"}, 500

async def handle_checkout_session_completed(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle successful checkout session completion."""
    try:
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        session_id = session.get("id")

        # --- Battle Pass purchase flow ---
        if metadata.get("type") == "battlepass_purchase":
            return await _fulfill_battlepass_purchase(session, metadata, session_id)

        # --- Pack purchase flow (from marketplace) ---
        if metadata.get("type") == "pack_purchase":
            return await _fulfill_pack_purchase(session, metadata, session_id)

        # --- Legacy generic pack flow ---
        user_id = metadata.get("user_id")
        pack_type = metadata.get("pack")

        if not user_id or not pack_type:
            logger.error(f"Missing metadata in session {session_id}")
            return {"error": "Missing metadata"}, 400

        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Invalid user_id in metadata: {user_id}")
            return {"error": "Invalid user_id"}, 400

        logger.info(f"Processing payment for user {user_id}, pack {pack_type}, session {session_id}")

        result = handle_payment(
            user_id=user_id,
            pack_type=pack_type,
            payment_id=session_id
        )

        logger.info(f"Stripe payment processed: {session_id} -> {result}")

        return {
            "status": "processed",
            "result": result,
            "session_id": session_id,
            "user_id": user_id,
            "pack_type": pack_type,
        }

    except Exception as e:
        logger.error(f"Checkout session processing failed: {e}")
        return {"error": "Payment processing failed"}, 500


async def _fulfill_pack_purchase(session: Dict, metadata: Dict, session_id: str) -> Dict[str, Any]:
    """Fulfill a marketplace pack purchase after Stripe payment succeeds."""
    import uuid as _uuid
    try:
        pack_id = metadata.get("pack_id")
        buyer_id = metadata.get("buyer_id")
        amount_cents = session.get("amount_total", 0)

        if not pack_id or not buyer_id:
            logger.error(f"Missing pack_id or buyer_id in session {session_id}")
            return {"error": "Missing pack purchase metadata"}, 400

        buyer_id = int(buyer_id)
        logger.info(f"Fulfilling pack purchase: pack={pack_id}, buyer={buyer_id}, session={session_id}")

        from database import DatabaseManager
        db = DatabaseManager()

        # Fetch pack data
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cards_data, name FROM creator_packs WHERE pack_id = ? AND status = 'LIVE'",
                (pack_id,),
            )
            row = cursor.fetchone()

        if not row:
            logger.error(f"Pack {pack_id} not found for fulfillment")
            return {"error": "Pack not found"}, 404

        cards_data_json, pack_name = row
        cards_data = json.loads(cards_data_json) if cards_data_json else []

        # Grant cards to buyer
        for card in cards_data:
            if 'card_id' not in card:
                card['card_id'] = str(_uuid.uuid4())
            db.add_card_to_master(card)
            db.add_card_to_collection(buyer_id, card['card_id'], 'pack_purchase')

        # Increment total_purchases
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE creator_packs SET total_purchases = total_purchases + 1 WHERE pack_id = ?",
                (pack_id,),
            )
            conn.commit()

        # Record in purchases audit table
        purchase_id = str(_uuid.uuid4())
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO purchases
                   (purchase_id, user_id, pack_id, amount_cents, payment_method, stripe_session_id, status)
                   VALUES (?, ?, ?, ?, 'stripe', ?, 'completed')""",
                (purchase_id, buyer_id, pack_id, amount_cents, session_id),
            )
            conn.commit()

        logger.info(f"Pack purchase fulfilled: {len(cards_data)} cards granted to user {buyer_id}")

        return {
            "status": "fulfilled",
            "pack_id": pack_id,
            "buyer_id": buyer_id,
            "cards_granted": len(cards_data),
            "session_id": session_id,
            "purchase_id": purchase_id,
        }

    except Exception as e:
        logger.error(f"Pack purchase fulfillment failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "Fulfillment failed"}, 500

async def _fulfill_battlepass_purchase(session: Dict, metadata: Dict, session_id: str) -> Dict[str, Any]:
    """Grant premium battle pass — sets premium_expires to now + SEASON_DURATION_DAYS."""
    from datetime import datetime, timedelta
    import uuid as _uuid
    from config.battle_pass import BattlePass

    try:
        user_id = int(metadata.get("user_id"))
        expires_at = (datetime.now() + timedelta(days=BattlePass.SEASON_DURATION_DAYS)).isoformat()
        amount_cents = session.get("amount_total", 0)

        logger.info(f"Fulfilling battlepass purchase: user={user_id}, session={session_id}")

        from database import DatabaseManager
        db = DatabaseManager()

        # Ensure user row exists, then set premium_expires
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_inventory (user_id, premium_expires) VALUES (?, ?) "
                "ON CONFLICT (user_id) DO UPDATE SET premium_expires = ?",
                (user_id, expires_at, expires_at)
            )
            conn.commit()

        # Record in purchases audit table
        purchase_id = str(_uuid.uuid4())
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO purchases (purchase_id, user_id, pack_id, amount_cents, payment_method, stripe_session_id, status) "
                "VALUES (?, ?, ?, ?, 'stripe', ?, 'completed')",
                (purchase_id, user_id, 'battlepass_premium', amount_cents, session_id)
            )
            conn.commit()

        AuditLog.record(
            event="battlepass_purchased",
            user_id=user_id,
            target_id=session_id,
            details={"expires_at": expires_at, "amount_cents": amount_cents}
        )

        # Send Discord notifications
        try:
            from main import bot

            # DM buyer a receipt
            user = bot.get_user(user_id)
            if user:
                receipt = purchase_embed(
                    user=user,
                    pack_type="Battle Pass Premium",
                    session_id=session_id,
                    amount=amount_cents
                )
                await user.send(embed=receipt)
                logger.info(f"Battle pass receipt sent to user {user_id}")
            else:
                logger.warning(f"Could not find user {user_id} for battle pass receipt")

            # Post to admin sales channel
            SALES_CHANNEL = os.getenv("SALES_CHANNEL_ID")
            if SALES_CHANNEL:
                sales_channel = bot.get_channel(int(SALES_CHANNEL))
                if sales_channel:
                    admin_embed = admin_sale_embed(
                        pack_type="Battle Pass Premium",
                        session_id=session_id,
                        user_id=user_id,
                        amount=amount_cents
                    )
                    await sales_channel.send(embed=admin_embed)
                    logger.info(f"Battle pass sale logged to channel {SALES_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to send battle pass notifications: {e}")

        logger.info(f"Battlepass purchase fulfilled: user={user_id}, expires={expires_at}")

        return {"status": "fulfilled", "product": "battlepass", "user_id": user_id, "premium_expires": expires_at}

    except Exception as e:
        logger.error(f"Battlepass purchase fulfillment failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "Fulfillment failed"}, 500


async def handle_charge_refunded(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle charge refund event."""
    try:
        charge = event["data"]["object"]
        payment_intent_id = charge.get("payment_intent")
        charge_id = charge.get("id")
        refund_amount = charge.get("amount_refunded")
        
        if not payment_intent_id:
            logger.error(f"Missing payment_intent in charge {charge_id}")
            return {"error": "Missing payment_intent"}, 400
        
        logger.info(f"Processing refund for payment_intent {payment_intent_id}")
        
        # Process the refund
        result = refund_purchase(payment_intent_id)
        
        # Get user ID from payment intent or purchase
        user_id = None
        try:
            # Try to get user from the refund result
            if isinstance(result, dict) and "user_id" in result:
                user_id = result["user_id"]
            else:
                # Fallback: try to get from purchase records
                from models.purchase import Purchase
                purchase = Purchase.get_by_payment_id(payment_intent_id)
                if purchase:
                    user_id = purchase.user_id
        except Exception as e:
            logger.warning(f"Could not determine user_id for refund: {e}")
        
        # Send refund receipt to user
        if user_id:
            try:
                from main import bot  # Adjust import based on your bot structure
                
                user = bot.get_user(user_id)
                if user:
                    refund_receipt = refund_embed(
                        user=user,
                        session_id=payment_intent_id,
                        refund_amount=refund_amount,
                        cards_revoked=result.get("cards_revoked") if isinstance(result, dict) else None
                    )
                    await user.send(embed=refund_receipt)
                    logger.info(f"Refund receipt sent to user {user_id}")
                else:
                    logger.warning(f"Could not find user {user_id} for refund receipt")
            except Exception as e:
                logger.error(f"Failed to send refund receipt: {e}")
        
        # Log refund to admin channel
        try:
            SALES_CHANNEL = os.getenv("SALES_CHANNEL_ID")
            if SALES_CHANNEL and user_id:
                from main import bot
                
                sales_channel = bot.get_channel(int(SALES_CHANNEL))
                if sales_channel:
                    admin_refund = admin_refund_embed(
                        session_id=payment_intent_id,
                        user_id=user_id,
                        refund_amount=refund_amount,
                        cards_revoked=result.get("cards_revoked", 0) if isinstance(result, dict) else 0
                    )
                    await sales_channel.send(embed=admin_refund)
                    logger.info(f"Admin refund logged to channel {SALES_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to log admin refund: {e}")
        
        # Log successful refund
        AuditLog.record(
            event="stripe_refund",
            target_id=payment_intent_id,
            user_id=user_id,
            details={
                "charge_id": charge_id,
                "refund_amount": refund_amount,
                "result": result,
                "currency": charge.get("currency"),
                "receipt_sent": user_id is not None
            }
        )
        
        logger.info(f"Stripe refund processed: {payment_intent_id} -> {result}")
        
        return {
            "status": "refunded",
            "result": result,
            "payment_intent_id": payment_intent_id,
            "charge_id": charge_id,
            "refund_amount": refund_amount,
            "receipt_sent": user_id is not None
        }
        
    except Exception as e:
        logger.error(f"Charge refund processing failed: {e}")
        return {"error": "Refund processing failed"}, 500

async def handle_checkout_session_expired(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle expired checkout session."""
    try:
        session = event["data"]["object"]
        session_id = session.get("id")
        
        # Extract metadata for logging
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        pack_type = metadata.get("pack")
        
        logger.info(f"Checkout session expired: {session_id} for user {user_id}, pack {pack_type}")
        
        # Log expiration
        AuditLog.record(
            event="stripe_session_expired",
            user_id=int(user_id) if user_id else None,
            target_id=session_id,
            details={
                "pack_type": pack_type,
                "session_id": session_id,
                "reason": "session_expired"
            }
        )
        
        return {
            "status": "expired",
            "session_id": session_id,
            "user_id": user_id,
            "pack_type": pack_type
        }
        
    except Exception as e:
        logger.error(f"Session expiration handling failed: {e}")
        return {"error": "Expiration handling failed"}, 500

# Utility functions

def verify_stripe_signature(payload: bytes, signature: str) -> Dict[str, Any]:
    """
    Verify Stripe webhook signature.
    
    Args:
        payload: Raw request payload
        signature: Stripe signature header
        
    Returns:
        Verified event object
        
    Raises:
        Exception: If verification fails
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, WH_SECRET
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        raise Exception(f"Invalid signature: {e}")
    except Exception as e:
        raise Exception(f"Verification failed: {e}")

def extract_session_metadata(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and validate metadata from checkout session.
    
    Args:
        session: Stripe checkout session object
        
    Returns:
        Validated metadata dictionary
        
    Raises:
        Exception: If metadata is invalid
    """
    metadata = session.get("metadata", {})
    
    user_id = metadata.get("user_id")
    pack_type = metadata.get("pack")
    
    if not user_id or not pack_type:
        raise Exception("Missing required metadata: user_id, pack")
    
    try:
        user_id = int(user_id)
    except ValueError:
        raise Exception(f"Invalid user_id: {user_id}")
    
    return {
        "user_id": user_id,
        "pack_type": pack_type,
        "session_id": session.get("id")
    }

# Error handling

class StripeWebhookError(Exception):
    """Custom exception for Stripe webhook errors."""
    pass

class StripeSignatureError(StripeWebhookError):
    """Exception for signature verification errors."""
    pass

class StripeMetadataError(StripeWebhookError):
    """Exception for metadata validation errors."""
    pass

# Logging helpers

def log_stripe_event_received(event: Dict[str, Any]):
    """Log Stripe event receipt."""
    event_type = event.get("type")
    event_id = event.get("id")
    logger.info(f"Stripe event received: {event_type} ({event_id})")

def log_stripe_event_processed(event: Dict[str, Any], result: Dict[str, Any]):
    """Log successful Stripe event processing."""
    event_type = event.get("type")
    event_id = event.get("id")
    logger.info(f"Stripe event processed: {event_type} ({event_id}) -> {result.get('status')}")

def log_stripe_event_error(event: Dict[str, Any], error: Exception):
    """Log Stripe event processing error."""
    event_type = event.get("type")
    event_id = event.get("id")
    logger.error(f"Stripe event error: {event_type} ({event_id}) - {error}")
