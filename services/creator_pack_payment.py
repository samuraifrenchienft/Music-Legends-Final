# services/creator_pack_payment.py
"""
Creator Pack Payment Service
Handle pack creation with payment authorization and capture
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from models.creator_pack import CreatorPack
from models.audit_minimal import AuditLog
from services.creator_moderation import creator_moderation
from services.admin_review import admin_review

class CreatorPackPaymentService:
    """Service for creator pack payment processing"""
    
    def __init__(self):
        self.moderation = creator_moderation
        self.admin_review = admin_review
    
    def create_pack_with_hold(self, user_id: int, name: str, artists: List[str], genre: str, payment_id: str, price_cents: int = 999) -> Optional[CreatorPack]:
        """
        Create a creator pack with payment authorization hold
        
        Args:
            user_id: Discord user ID
            name: Pack name
            artists: List of artist names
            genre: Pack genre
            payment_id: Stripe payment intent ID
            price_cents: Price in cents (default 999)
            
        Returns:
            CreatorPack object or None if failed
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate pack before creation
            valid, msg = self.moderation.validate_pack(name, artists, user_id)
            if not valid:
                raise ValueError(msg)
            
            # Record pack before any payment capture
            pack = CreatorPack.create(
                owner_id=user_id,
                name=name,
                artist_ids=artists,  # Store as list for now
                genre=genre,
                payment_id=payment_id,
                price_cents=price_cents,
                payment_status="authorized",
                status="pending"
            )
            
            # Log the pack request
            AuditLog.record(
                event="creator_requested",
                user_id=user_id,
                target_id=str(pack.id),
                payload={
                    "pack_name": name,
                    "artist_count": len(artists),
                    "genre": genre,
                    "payment_id": payment_id,
                    "price_cents": price_cents,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Submit for review
            self.moderation.submit_for_review(pack, user_id)
            
            return pack
            
        except ValueError as e:
            # Log validation failure
            AuditLog.record(
                event="creator_pack_validation_failed",
                user_id=user_id,
                target_id="validation",
                payload={
                    "pack_name": name,
                    "artist_count": len(artists),
                    "genre": genre,
                    "payment_id": payment_id,
                    "validation_error": str(e)
                }
            )
            raise
        except Exception as e:
            # Log creation failure
            AuditLog.record(
                event="creator_pack_creation_failed",
                user_id=user_id,
                target_id="creation",
                payload={
                    "pack_name": name,
                    "payment_id": payment_id,
                    "error": str(e)
                }
            )
            raise
    
    def capture_payment_on_approval(self, pack_id: str, reviewer_id: int) -> bool:
        """
        Capture payment when pack is approved
        
        Args:
            pack_id: Pack ID
            reviewer_id: Reviewer ID
            
        Returns:
            True if captured successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            # Check if payment can be captured
            if not pack.can_be_captured():
                return False
            
            # Capture payment (this would integrate with Stripe)
            # For now, we'll mark it as captured
            pack.capture_payment()
            
            # Log payment capture
            AuditLog.record(
                event="creator_payment_captured",
                user_id=reviewer_id,
                target_id=pack_id,
                payload={
                    "payment_id": pack.payment_id,
                    "amount_cents": pack.price_cents,
                    "captured_at": datetime.utcnow().isoformat(),
                    "captured_by": reviewer_id
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error capturing payment for pack {pack_id}: {e}")
            return False
    
    def refund_payment_on_rejection(self, pack_id: str, reviewer_id: int, reason: str) -> bool:
        """
        Refund payment when pack is rejected
        
        Args:
            pack_id: Pack ID
            reviewer_id: Reviewer ID
            reason: Rejection reason
            
        Returns:
            True if refunded successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            # Check if payment can be refunded
            if not pack.can_be_refunded():
                return False
            
            # Refund payment (this would integrate with Stripe)
            # For now, we'll mark it as refunded
            pack.refund_payment()
            
            # Log payment refund
            AuditLog.record(
                event="creator_payment_refunded",
                user_id=reviewer_id,
                target_id=pack_id,
                payload={
                    "payment_id": pack.payment_id,
                    "amount_cents": pack.price_cents,
                    "refunded_at": datetime.utcnow().isoformat(),
                    "refunded_by": reviewer_id,
                    "rejection_reason": reason
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error refunding payment for pack {pack_id}: {e}")
            return False
    
    def fail_payment_on_error(self, pack_id: str, error_reason: str) -> bool:
        """
        Mark payment as failed due to error
        
        Args:
            pack_id: Pack ID
            error_reason: Reason for failure
            
        Returns:
            True if marked as failed
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            # Mark payment as failed
            pack.fail_payment()
            
            # Log payment failure
            AuditLog.record(
                event="creator_payment_failed",
                user_id=pack.owner_id,
                target_id=pack_id,
                payload={
                    "payment_id": pack.payment_id,
                    "amount_cents": pack.price_cents,
                    "failed_at": datetime.utcnow().isoformat(),
                    "error_reason": error_reason
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error marking payment as failed for pack {pack_id}: {e}")
            return False
    
    def get_pack_by_payment_id(self, payment_id: str) -> Optional[CreatorPack]:
        """
        Get pack by payment ID
        
        Args:
            payment_id: Stripe payment intent ID
            
        Returns:
            CreatorPack object or None
        """
        try:
            return CreatorPack.get_by_payment_id(payment_id)
        except Exception as e:
            print(f"❌ Error getting pack by payment ID {payment_id}: {e}")
            return None
    
    def get_payment_status(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment status for a pack
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Payment status dict or None
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return None
            
            return pack.get_payment_info()
            
        except Exception as e:
            print(f"❌ Error getting payment status for pack {pack_id}: {e}")
            return None
    
    def get_user_payment_history(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get payment history for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of payment history entries
        """
        try:
            packs = CreatorPack.get_by_owner(user_id)
            
            history = []
            for pack in packs:
                payment_info = pack.get_payment_info()
                history.append({
                    "pack_id": str(pack.id),
                    "pack_name": pack.name,
                    "payment_id": pack.payment_id,
                    "payment_status": pack.payment_status,
                    "price_cents": pack.price_cents,
                    "created_at": pack.created_at.isoformat(),
                    "reviewed_at": pack.reviewed_at.isoformat() if pack.reviewed_at else None,
                    "status": pack.status
                })
            
            return sorted(history, key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            print(f"❌ Error getting payment history for user {user_id}: {e}")
            return []
    
    def get_payment_statistics(self) -> Dict[str, Any]:
        """
        Get payment statistics
        
        Returns:
            Payment statistics dict
        """
        try:
            all_packs = CreatorPack.all()
            
            stats = {
                "total_packs": len(all_packs),
                "authorized": 0,
                "captured": 0,
                "failed": 0,
                "refunded": 0,
                "total_revenue_cents": 0,
                "total_revenue_dollars": 0,
                "average_price_cents": 0,
                "average_price_dollars": 0
            }
            
            total_price = 0
            for pack in all_packs:
                if pack.payment_status == "authorized":
                    stats["authorized"] += 1
                elif pack.payment_status == "captured":
                    stats["captured"] += 1
                    stats["total_revenue_cents"] += pack.price_cents
                elif pack.payment_status == "failed":
                    stats["failed"] += 1
                elif pack.payment_status == "refunded":
                    stats["refunded"] += 1
                
                total_price += pack.price_cents
            
            stats["total_revenue_dollars"] = stats["total_revenue_cents"] / 100
            
            if len(all_packs) > 0:
                stats["average_price_cents"] = total_price / len(all_packs)
                stats["average_price_dollars"] = stats["average_price_cents"] / 100
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting payment statistics: {e}")
            return {
                "total_packs": 0,
                "authorized": 0,
                "captured": 0,
                "failed": 0,
                "refunded": 0,
                "total_revenue_cents": 0,
                "total_revenue_dollars": 0,
                "average_price_cents": 0,
                "average_price_dollars": 0
            }


# Global payment service instance
creator_pack_payment = CreatorPackPaymentService()


# Convenience function for backward compatibility
def create_pack_with_hold(user_id: int, name: str, artists: List[str], genre: str, payment_id: str) -> Optional[CreatorPack]:
    """Create pack with payment hold (simplified version)"""
    return creator_pack_payment.create_pack_with_hold(user_id, name, artists, genre, payment_id)


# Example usage
def example_usage():
    """Example of payment service usage"""
    
    try:
        # Create pack with payment hold
        pack = creator_pack_payment.create_pack_with_hold(
            user_id=123456789,
            name="Rock Legends",
            artists=["Queen", "Led Zeppelin", "The Beatles"],
            genre="Rock",
            payment_id="pi_1234567890"
        )
        
        if pack:
            print(f"✅ Pack created with payment hold: {pack.id}")
            print(f"   Payment status: {pack.payment_status}")
            print(f"   Pack status: {pack.status}")
            
            # Get payment status
            payment_info = creator_pack_payment.get_payment_status(str(pack.id))
            if payment_info:
                print(f"   Payment info: {payment_info}")
        else:
            print("❌ Failed to create pack")
            
    except ValueError as e:
        print(f"❌ Validation error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
