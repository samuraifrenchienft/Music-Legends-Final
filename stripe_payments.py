# stripe_payments.py
import stripe
import os
import uuid
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv('.env.txt')

# Configure Stripe
stripe.api_key = (os.getenv('STRIPE_SECRET') or '').strip()
STRIPE_WEBHOOK_SECRET = (os.getenv('STRIPE_WEBHOOK_SECRET') or '').strip()

class StripePaymentManager:
    def __init__(self):
        # Pack prices (Season 1)
        self.pack_prices = {
            'founder_silver': 499,   # $4.99 Silver Pack
            'founder_black': 699     # $6.99 Black Pack
        }
        
        # Creator pack publishing fees (if needed later)
        self.publish_prices = {
            5: 1000,   # $10.00 for Micro (5 cards)
            10: 2500,  # $25.00 for Mini (10 cards) 
            15: 5000   # $50.00 for Event (15 cards)
        }
        
        # Pack creation fee
        self.pack_creation_fee = 999  # $9.99 to create a pack
        
        # Revenue split between platform and creator
        self.platform_split = 0.30  # 30% to platform
        self.creator_split = 0.70   # 70% to creator

        # Stripe Connect (for server owner payouts)
        self.connect_platform_fee = 0.029  # 2.9% Stripe Connect fee
    
    def create_pack_creation_checkout(self, creator_id: int, song_query: str) -> Dict:
        """Create Stripe Checkout session for pack creation ($9.99)"""
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_intent_data={
                    'metadata': {
                        'creator_id': str(creator_id),
                        'song_query': song_query,
                        'type': 'pack_creation'
                    }
                },
                customer_email=None,
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Pack Creation',
                            'description': f'Create pack with featured song: {song_query}',
                            'images': [],
                        },
                        'unit_amount': self.pack_creation_fee,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://discord.com/channels/@me',
                cancel_url=f'https://discord.com/channels/@me',
                metadata={
                    'creator_id': str(creator_id),
                    'song_query': song_query,
                    'type': 'pack_creation'
                }
            )
            
            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'price_cents': self.pack_creation_fee
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        
    def create_pack_publish_checkout(self, pack_id: str, creator_id: int, pack_size: int, pack_name: str) -> Dict:
        """Create Stripe Checkout session for pack publishing"""
        try:
            price_cents = self.publish_prices.get(pack_size, 2500)
            
            checkout_session = stripe.checkout.Session.create(
                payment_intent_data={
                    'metadata': {
                        'pack_id': pack_id,
                        'creator_id': str(creator_id),
                        'type': 'pack_publish'
                    }
                },
                customer_email=None,  # Will be collected in checkout
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Pack Publishing: {pack_name}',
                            'description': f'Publish your {pack_size}-card pack "{pack_name}" to the Music Legends store',
                            'images': [],
                        },
                        'unit_amount': price_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://discord.com/channels/@me',  # Return to Discord
                cancel_url=f'https://discord.com/channels/@me',
                metadata={
                    'pack_id': pack_id,
                    'creator_id': str(creator_id),
                    'type': 'pack_publish'
                }
            )
            
            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'price_cents': price_cents
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_pack_purchase_checkout(self, pack_id: str, buyer_id: int, pack_name: str, price_cents: int) -> Dict:
        """Create Stripe Checkout session for pack purchase"""
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_intent_data={
                    'metadata': {
                        'pack_id': pack_id,
                        'buyer_id': str(buyer_id),
                        'type': 'pack_purchase'
                    }
                },
                customer_email=None,
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Pack: {pack_name}',
                            'description': f'Purchase the "{pack_name}" card pack',
                            'images': [],
                        },
                        'unit_amount': price_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://discord.com/channels/@me',
                cancel_url=f'https://discord.com/channels/@me',
                metadata={
                    'pack_id': pack_id,
                    'buyer_id': str(buyer_id),
                    'type': 'pack_purchase'
                }
            )
            
            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_battlepass_checkout(self, user_id: int) -> Dict:
        """Create Stripe Checkout session for Battle Pass Premium ($9.99)"""
        try:
            from config.battle_pass import BattlePass

            checkout_session = stripe.checkout.Session.create(
                payment_intent_data={
                    'metadata': {
                        'user_id': str(user_id),
                        'type': 'battlepass_purchase'
                    }
                },
                customer_email=None,
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Battle Pass Premium - {BattlePass.SEASON_NAME}',
                            'description': f'Unlock premium rewards for Season {BattlePass.SEASON_NUMBER} ({BattlePass.SEASON_DURATION_DAYS} days)',
                        },
                        'unit_amount': BattlePass.PREMIUM_PRICE_CENTS,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='https://discord.com/channels/@me',
                cancel_url='https://discord.com/channels/@me',
                metadata={
                    'user_id': str(user_id),
                    'type': 'battlepass_purchase'
                }
            )

            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def create_stripe_connect_account(self, creator_id: int, email: str) -> Dict:
        """Create Stripe Connect account for creator"""
        try:
            account = stripe.Account.create(
                type='express',
                country='US',
                email=email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                business_type='individual',
                metadata={
                    'creator_id': str(creator_id)
                }
            )
            
            # Create account link for onboarding
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url='https://discord.com/channels/@me',
                return_url='https://discord.com/channels/@me',
                type='account_onboarding'
            )
            
            return {
                'success': True,
                'account_id': account.id,
                'onboarding_url': account_link.url
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_transfer_to_creator(self, amount_cents: int, creator_stripe_account_id: str, purchase_id: str) -> Dict:
        """Create transfer to creator's Stripe account"""
        try:
            transfer = stripe.Transfer.create(
                amount=amount_cents,
                currency='usd',
                destination=creator_stripe_account_id,
                metadata={
                    'purchase_id': purchase_id,
                    'type': 'creator_payout'
                }
            )
            
            return {
                'success': True,
                'transfer_id': transfer.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_webhook_signature(self, payload: str, sig_header: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return True
        except ValueError:
            return False
        except stripe.error.SignatureVerificationError:
            return False
    
    def process_webhook_event(self, payload: str) -> Dict:
        """Process Stripe webhook event"""
        try:
            event = stripe.Webhook.construct_event(
                payload, None, STRIPE_WEBHOOK_SECRET
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                metadata = session['metadata']
                
                if metadata.get('type') == 'pack_publish':
                    return {
                        'type': 'pack_publish_completed',
                        'pack_id': metadata['pack_id'],
                        'creator_id': int(metadata['creator_id']),
                        'payment_intent_id': session['payment_intent'],
                        'amount_cents': session['amount_total']
                    }
                
                elif metadata.get('type') == 'pack_purchase':
                    return {
                        'type': 'pack_purchase_completed',
                        'pack_id': metadata['pack_id'],
                        'buyer_id': int(metadata['buyer_id']),
                        'payment_intent_id': session['payment_intent'],
                        'amount_cents': session['amount_total']
                    }
            
            elif event['type'] == 'account.updated':
                # Stripe Connect account updated
                account = event['data']['object']
                return {
                    'type': 'stripe_account_updated',
                    'account_id': account.id,
                    'status': account.get('payouts_enabled', False)
                }
            
            return {'type': 'unhandled', 'event_type': event['type']}
            
        except Exception as e:
            return {'type': 'error', 'error': str(e)}
    
    def calculate_revenue_split(self, amount_cents: int) -> Dict:
        """Calculate platform and creator revenue splits"""
        platform_amount = int(amount_cents * self.platform_split)
        creator_amount = int(amount_cents * self.creator_split)
        
        return {
            'total_cents': amount_cents,
            'platform_cents': platform_amount,
            'creator_cents': creator_amount,
            'platform_split_percent': self.platform_split * 100,
            'creator_split_percent': self.creator_split * 100
        }

# Global instance
stripe_manager = StripePaymentManager()
