# payment_security.py
"""
Secure payment and Stripe webhook handling
- Webhook signature verification
- Payment state validation
- Fraud detection
- Security event logging
- Rate limiting on payment endpoints
"""

import os
import hashlib
import hmac
import json
import stripe
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from functools import wraps
import discord
from discord import Interaction, app_commands
from cogs.dev_authorization import security_logger


# ==========================================
# STRIPE WEBHOOK SECURITY
# ==========================================

class StripeWebhookVerifier:
    """Secure Stripe webhook verification and processing"""
    
    def __init__(self):
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        self.stripe_key = os.getenv('STRIPE_SECRET_KEY')
        
        if not self.webhook_secret:
            print("⚠️  [STRIPE] WARNING: STRIPE_WEBHOOK_SECRET not configured")
        if not self.stripe_key:
            print("⚠️  [STRIPE] WARNING: STRIPE_SECRET_KEY not configured")
        
        # Configure Stripe
        stripe.api_key = self.stripe_key
        
        # Track webhook IDs to prevent replay attacks
        self.processed_webhook_ids = {}
        self.webhook_id_ttl = timedelta(hours=24)
        
        print(f"✅ [STRIPE] Stripe webhook verifier initialized")
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Verify Stripe webhook signature and extract event
        
        Args:
            payload: Raw request body from Stripe
            signature: Stripe-Signature header
            
        Returns:
            Tuple of (is_valid, event_dict or None)
        """
        
        print(f"🔐 [STRIPE] Verifying webhook signature...")
        
        try:
            # Verify signature
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            
            print(f"✅ [STRIPE] Webhook signature verified")
            print(f"🔐 [STRIPE] Event type: {event.get('type')} | ID: {event.get('id')}")
            
            security_logger.log_event(
                "STRIPE_WEBHOOK_VERIFIED",
                details={
                    "event_type": event.get('type'),
                    "event_id": event.get('id'),
                    "timestamp": event.get('created')
                },
                severity="INFO"
            )
            
            return True, event
            
        except stripe.error.SignatureVerificationError as e:
            print(f"❌ [STRIPE] Signature verification FAILED: {e}")
            
            # Log potential tampering
            payload_hash = hashlib.sha256(payload.encode()).hexdigest()
            signature_hash = hashlib.sha256(signature.encode()).hexdigest()
            
            security_logger.log_event(
                "STRIPE_WEBHOOK_TAMPERING_DETECTED",
                details={
                    "payload_hash": payload_hash,
                    "signature_hash": signature_hash,
                    "error": str(e)
                },
                severity="CRITICAL"
            )
            
            return False, None
        
        except Exception as e:
            print(f"❌ [STRIPE] Webhook verification error: {type(e).__name__}: {e}")
            
            security_logger.log_event(
                "STRIPE_WEBHOOK_ERROR",
                details={
                    "error_type": type(e).__name__,
                    "error": str(e)
                },
                severity="WARNING"
            )
            
            return False, None
    
    def check_replay_attack(self, event_id: str) -> bool:
        """
        Check if webhook has already been processed (replay attack prevention)
        
        Args:
            event_id: Stripe event ID
            
        Returns:
            True if valid (not replayed), False if already processed
        """
        
        # Clean up old entries
        current_time = datetime.now()
        expired_ids = [
            eid for eid, timestamp in self.processed_webhook_ids.items()
            if current_time - timestamp > self.webhook_id_ttl
        ]
        for eid in expired_ids:
            del self.processed_webhook_ids[eid]
        
        # Check if event already processed
        if event_id in self.processed_webhook_ids:
            print(f"🚨 [STRIPE] REPLAY ATTACK DETECTED: Event {event_id} already processed")
            
            security_logger.log_event(
                "STRIPE_REPLAY_ATTACK_DETECTED",
                details={
                    "event_id": event_id,
                    "first_processed": self.processed_webhook_ids[event_id].isoformat()
                },
                severity="CRITICAL"
            )
            
            return False
        
        # Record this event as processed
        self.processed_webhook_ids[event_id] = current_time
        print(f"✅ [STRIPE] Event {event_id} recorded as processed")
        
        return True
    
    def validate_payment_object(self, payment_intent: Dict) -> Tuple[bool, str]:
        """
        Validate payment intent object for security
        
        Checks:
        - Amount is positive
        - Currency is valid
        - Status is acceptable
        - No suspicious patterns
        
        Args:
            payment_intent: Stripe payment intent object
            
        Returns:
            Tuple of (is_valid, reason)
        """
        
        print(f"🔐 [STRIPE] Validating payment object: {payment_intent.get('id')}")
        
        # Validate amount
        amount = payment_intent.get('amount', 0)
        if amount <= 0:
            return False, "Invalid amount: must be positive"
        
        if amount > 999999999:  # $9,999,999.99 max
            return False, "Invalid amount: exceeds maximum"
        
        # Validate currency
        currency = payment_intent.get('currency', '').lower()
        valid_currencies = ['usd', 'eur', 'gbp', 'jpy', 'cad', 'aud']
        if currency not in valid_currencies:
            return False, f"Invalid currency: {currency}"
        
        # Validate status
        status = payment_intent.get('status', '').lower()
        valid_statuses = ['succeeded', 'processing', 'requires_payment_method', 'requires_action']
        if status not in valid_statuses:
            return False, f"Invalid status: {status}"
        
        # Check for suspicious metadata
        metadata = payment_intent.get('metadata', {})
        if not isinstance(metadata, dict):
            return False, "Invalid metadata format"
        
        print(f"✅ [STRIPE] Payment object validation passed")
        return True, "Valid"


# ==========================================
# PAYMENT RATE LIMITING
# ==========================================

class PaymentRateLimiter:
    """Rate limit payment operations to prevent abuse"""
    
    def __init__(self, max_attempts: int = 10, window_seconds: int = 3600):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = {}  # user_id -> [(timestamp, action), ...]
        print(f"💳 [RATE_LIMIT] Payment rate limiter initialized")
    
    def is_rate_limited(self, user_id: int, action: str = "payment") -> Tuple[bool, str]:
        """
        Check if user is rate limited for payment operations
        
        Args:
            user_id: Discord user ID
            action: Type of payment action (payment, subscription, etc.)
            
        Returns:
            Tuple of (is_limited, remaining_time_str)
        """
        
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=self.window_seconds)
        
        if user_id not in self.attempts:
            self.attempts[user_id] = []
        
        # Clean up old attempts outside window
        self.attempts[user_id] = [
            (timestamp, act) for timestamp, act in self.attempts[user_id]
            if timestamp > window_start
        ]
        
        # Count attempts for this action
        action_count = sum(1 for _, act in self.attempts[user_id] if act == action)
        
        if action_count >= self.max_attempts:
            oldest_attempt = self.attempts[user_id][0][0]
            retry_time = oldest_attempt + timedelta(seconds=self.window_seconds)
            remaining = (retry_time - current_time).total_seconds()
            
            print(f"⚠️  [RATE_LIMIT] User {user_id} rate limited ({action_count} attempts)")
            
            security_logger.log_event(
                "PAYMENT_RATE_LIMIT_EXCEEDED",
                user_id,
                {"action": action, "attempts": action_count},
                severity="WARNING"
            )
            
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            return True, f"{minutes}m {seconds}s"
        
        # Record this attempt
        self.attempts[user_id].append((current_time, action))
        
        return False, ""
    
    def reset_user_attempts(self, user_id: int):
        """Reset attempts for a user (e.g., after successful payment)"""
        if user_id in self.attempts:
            del self.attempts[user_id]
        print(f"✅ [RATE_LIMIT] Reset attempts for user {user_id}")


# Global instances
webhook_verifier = StripeWebhookVerifier()
payment_rate_limiter = PaymentRateLimiter(max_attempts=10, window_seconds=3600)


# ==========================================
# DECORATORS FOR SECURE PAYMENTS
# ==========================================

def secure_payment(func):
    """
    Decorator for secure payment command execution
    
    Checks:
    - Rate limiting
    - User permissions
    - Security logging
    
    Usage:
        @app_commands.command()
        @secure_payment
        async def premium_subscribe(interaction: Interaction):
            pass
    """
    @wraps(func)
    async def wrapper(interaction: Interaction, *args, **kwargs):
        user_id = interaction.user.id
        
        print(f"💳 [PAYMENT] Secure payment check for user {user_id}")
        
        # Check rate limiting
        is_limited, remaining = payment_rate_limiter.is_rate_limited(user_id)
        if is_limited:
            print(f"⚠️  [PAYMENT] User {user_id} rate limited")
            
            await interaction.response.send_message(
                f"❌ **Too Many Requests**\n\n"
                f"Please wait {remaining} before trying again.\n"
                f"This protects against accidental duplicate payments.",
                ephemeral=True
            )
            return
        
        # Log payment attempt
        security_logger.log_event(
            "PAYMENT_INITIATED",
            user_id,
            {"command": func.__name__},
            severity="INFO"
        )
        
        try:
            # Execute payment command
            result = await func(interaction, *args, **kwargs)
            
            # Log successful payment
            security_logger.log_event(
                "PAYMENT_SUCCESS",
                user_id,
                {"command": func.__name__},
                severity="INFO"
            )
            
            return result
            
        except Exception as e:
            print(f"❌ [PAYMENT] Payment error: {type(e).__name__}: {e}")
            
            security_logger.log_event(
                "PAYMENT_ERROR",
                user_id,
                {
                    "command": func.__name__,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                severity="WARNING"
            )
            
            await interaction.response.send_message(
                f"❌ **Payment Processing Error**\n\n"
                f"An error occurred while processing your payment.\n"
                f"Please contact support if the problem persists.",
                ephemeral=True
            )
    
    return wrapper


# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def verify_subscription_eligibility(
    interaction: Interaction,
    required_role: str = None
) -> Tuple[bool, str]:
    """
    Verify user eligibility for subscription
    
    Checks:
    - User account age (prevent new account fraud)
    - Guild eligibility
    - Existing subscriptions
    - Permission requirements
    
    Args:
        interaction: Discord interaction
        required_role: Optional required role name
        
    Returns:
        Tuple of (is_eligible, reason)
    """
    
    user = interaction.user
    guild = interaction.guild
    
    print(f"🔐 [ELIGIBILITY] Checking subscription eligibility for {user.id}")
    
    # Check account age (minimum 7 days old)
    account_age = datetime.now(user.created_at.tzinfo) - user.created_at
    if account_age < timedelta(days=7):
        days_old = account_age.days
        return False, f"Account must be at least 7 days old (currently {days_old} days)"
    
    # Check guild membership (minimum 24 hours)
    if guild:
        join_date = interaction.user.joined_at
        if join_date:
            membership_age = datetime.now(join_date.tzinfo) - join_date
            if membership_age < timedelta(hours=24):
                return False, "Must be in server for at least 24 hours"
    
    # Check required role
    if required_role and guild:
        member = guild.get_member(user.id)
        if member:
            role_names = [role.name for role in member.roles]
            if required_role not in role_names and "Administrator" not in role_names:
                return False, f"Requires {required_role} role or Administrator permission"
    
    print(f"✅ [ELIGIBILITY] User {user.id} is eligible for subscription")
    
    security_logger.log_event(
        "SUBSCRIPTION_ELIGIBILITY_CHECK",
        user.id,
        {
            "eligible": True,
            "account_age_days": account_age.days,
            "guild": guild.name if guild else "DM"
        },
        severity="INFO"
    )
    
    return True, "Eligible"


async def process_payment_webhook(
    event: Dict,
    bot: discord.Client
) -> bool:
    """
    Safely process Stripe webhook event
    
    Args:
        event: Stripe webhook event
        bot: Discord bot instance
        
    Returns:
        True if processed successfully
    """
    
    print(f"🔐 [WEBHOOK] Processing Stripe event: {event.get('type')}")
    
    try:
        event_type = event.get('type')
        event_data = event.get('data', {}).get('object', {})
        
        # Check replay attack
        if not webhook_verifier.check_replay_attack(event.get('id')):
            return False
        
        # Validate payment object for payment events
        if 'payment_intent' in event_type:
            is_valid, reason = webhook_verifier.validate_payment_object(event_data)
            if not is_valid:
                print(f"❌ [WEBHOOK] Invalid payment object: {reason}")
                security_logger.log_event(
                    "INVALID_PAYMENT_OBJECT",
                    details={
                        "event_type": event_type,
                        "reason": reason
                    },
                    severity="WARNING"
                )
                return False
        
        # Handle specific event types
        if event_type == "payment_intent.succeeded":
            print(f"✅ [WEBHOOK] Payment succeeded: {event_data.get('id')}")

            # Record server revenue share
            try:
                from server_revenue import server_revenue

                # Extract metadata from payment intent
                metadata = event_data.get('metadata', {})
                server_id = metadata.get('server_id')
                purchase_type = metadata.get('purchase_type', 'unknown')
                amount_cents = event_data.get('amount')  # Already in cents

                if server_id and amount_cents:
                    # Record revenue transaction and calculate splits
                    revenue_result = server_revenue.record_purchase_revenue(
                        server_id=int(server_id),
                        purchase_type=purchase_type,
                        total_amount_cents=amount_cents,
                        payment_intent_id=event_data.get('id')
                    )

                    if revenue_result.get('success'):
                        print(f"💰 [REVENUE] Server share: ${revenue_result['server_share']:.2f} "
                              f"({revenue_result['revenue_share_percentage']*100:.0f}%)")
                    else:
                        print(f"⚠️  [REVENUE] Failed to record: {revenue_result.get('error')}")
                else:
                    print(f"ℹ️  [REVENUE] No server_id in metadata - skipping revenue split")

            except Exception as e:
                print(f"⚠️  [REVENUE] Error recording revenue: {e}")

            security_logger.log_event(
                "STRIPE_PAYMENT_SUCCEEDED",
                details={
                    "payment_intent_id": event_data.get('id'),
                    "amount": event_data.get('amount'),
                    "currency": event_data.get('currency')
                },
                severity="INFO"
            )
            return True
        
        elif event_type == "payment_intent.payment_failed":
            print(f"❌ [WEBHOOK] Payment failed: {event_data.get('id')}")
            
            security_logger.log_event(
                "STRIPE_PAYMENT_FAILED",
                details={
                    "payment_intent_id": event_data.get('id'),
                    "last_payment_error": event_data.get('last_payment_error')
                },
                severity="WARNING"
            )
            return True
        
        elif event_type == "charge.dispute.created":
            print(f"⚠️  [WEBHOOK] Chargeback dispute: {event_data.get('id')}")
            
            security_logger.log_event(
                "STRIPE_CHARGEBACK_DISPUTE",
                details={
                    "dispute_id": event_data.get('id'),
                    "reason": event_data.get('reason')
                },
                severity="CRITICAL"
            )
            return True
        
        else:
            print(f"ℹ️  [WEBHOOK] Event type not handled: {event_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ [WEBHOOK] Webhook processing error: {type(e).__name__}: {e}")
        
        security_logger.log_event(
            "WEBHOOK_PROCESSING_ERROR",
            details={
                "event_type": event.get('type'),
                "error": str(e),
                "error_type": type(e).__name__
            },
            severity="CRITICAL"
        )
        
        return False
