# services/admin_payment_actions.py
"""
Admin Payment Actions
Handle approval with capture and rejection with void
"""

from typing import Optional
from datetime import datetime
from models.creator_pack import CreatorPack
from models.audit_minimal import AuditLog
from services.payment_gateway import gateway

class AdminPaymentActions:
    """Service for admin payment actions"""
    
    def approve_and_capture(self, pack_id: str, admin_id: int) -> bool:
        """
        Approve a pack and capture payment
        
        Args:
            pack_id: Pack ID
            admin_id: Admin user ID
            
        Returns:
            True if successful
        """
        try:
            # Get the pack
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                print(f"❌ Pack not found: {pack_id}")
                return False
            
            # Check payment status
            if pack.payment_status != "authorized":
                raise ValueError(f"Payment not in hold state: {pack.payment_status}")
            
            # Check if already captured (double capture prevention)
            if pack.payment_status == "captured":
                print(f"❌ Payment already captured: {pack_id}")
                return False
            
            # ---- CAPTURE VIA GATEWAY ----
            capture_result = gateway.capture_payment(pack.payment_id)
            
            if not capture_result["success"]:
                # Mark payment as failed
                pack.payment_status = "failed"
                pack.save()
                
                # Log capture failure
                AuditLog.record(
                    event="creator_approval_payment_failed",
                    user_id=admin_id,
                    target_id=pack_id,
                    payload={
                        "pack_name": pack.name,
                        "payment_id": pack.payment_id,
                        "capture_error": capture_result["error"],
                        "admin_id": admin_id,
                        "failed_at": datetime.utcnow().isoformat()
                    }
                )
                
                print(f"❌ Payment capture failed: {capture_result['error']}")
                return False
            
            # Update pack status
            pack.status = "approved"
            pack.payment_status = "captured"
            pack.reviewed_by = admin_id
            pack.reviewed_at = datetime.utcnow()
            pack.save()
            
            # Log approval and capture
            AuditLog.record(
                event="creator_approved",
                user_id=pack.owner_id,
                target_id=pack_id,
                payload={
                    "pack_name": pack.name,
                    "payment_id": pack.payment_id,
                    "amount_captured": capture_result.get("amount_captured", pack.price_cents),
                    "admin_id": admin_id,
                    "approved_at": datetime.utcnow().isoformat(),
                    "payment_status": "captured"
                }
            )
            
            print(f"✅ Pack approved and payment captured: {pack.name}")
            return True
            
        except ValueError as e:
            print(f"❌ Validation error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error approving and capturing: {e}")
            
            # Log error
            AuditLog.record(
                event="creator_approval_error",
                user_id=admin_id,
                target_id=pack_id,
                payload={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "admin_id": admin_id,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return False
    
    def reject_and_void(self, pack_id: str, admin_id: int, note: str) -> bool:
        """
        Reject a pack and void payment
        
        Args:
            pack_id: Pack ID
            admin_id: Admin user ID
            note: Rejection note
            
        Returns:
            True if successful
        """
        try:
            # Get the pack
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                print(f"❌ Pack not found: {pack_id}")
                return False
            
            # Void payment if authorized
            void_result = None
            if pack.payment_status == "authorized":
                # ---- VOID VIA GATEWAY ----
                void_result = gateway.void_payment(pack.payment_id)
                
                if not void_result["success"]:
                    # Log void failure but continue with rejection
                    print(f"⚠️ Payment void failed: {void_result['error']}")
                    
                    AuditLog.record(
                        event="creator_rejection_void_failed",
                        user_id=admin_id,
                        target_id=pack_id,
                        payload={
                            "pack_name": pack.name,
                            "payment_id": pack.payment_id,
                            "void_error": void_result["error"],
                            "admin_id": admin_id,
                            "rejected_at": datetime.utcnow().isoformat()
                        }
                    )
            
            # Update pack status
            original_payment_status = pack.payment_status
            pack.status = "rejected"
            pack.payment_status = "voided" if original_payment_status == "authorized" else original_payment_status
            pack.notes = note
            pack.reviewed_by = admin_id
            pack.reviewed_at = datetime.utcnow()
            pack.save()
            
            # Log rejection and void
            AuditLog.record(
                event="creator_rejected",
                user_id=pack.owner_id,
                target_id=pack_id,
                payload={
                    "pack_name": pack.name,
                    "payment_id": pack.payment_id,
                    "original_payment_status": original_payment_status,
                    "new_payment_status": pack.payment_status,
                    "rejection_note": note,
                    "admin_id": admin_id,
                    "rejected_at": datetime.utcnow().isoformat(),
                    "void_success": void_result["success"] if void_result else None
                }
            )
            
            print(f"✅ Pack rejected and payment voided: {pack.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error rejecting and voiding: {e}")
            
            # Log error
            AuditLog.record(
                event="creator_rejection_error",
                user_id=admin_id,
                target_id=pack_id,
                payload={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "admin_id": admin_id,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            return False
    
    def get_pack_payment_status(self, pack_id: str) -> Optional[dict]:
        """
        Get detailed payment status for a pack
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Payment status dict or None
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return None
            
            # Get Stripe status if payment_id exists
            stripe_status = None
            if pack.payment_id:
                stripe_result = gateway.get_payment_status(pack.payment_id)
                if stripe_result["success"]:
                    stripe_status = {
                        "stripe_status": stripe_result["status"],
                        "amount": stripe_result["amount"],
                        "currency": stripe_result["currency"],
                        "charges": stripe_result["charges"]
                    }
            
            return {
                "pack_id": pack_id,
                "pack_name": pack.name,
                "pack_status": pack.status,
                "payment_id": pack.payment_id,
                "payment_status": pack.payment_status,
                "price_cents": pack.price_cents,
                "stripe_status": stripe_status,
                "can_be_captured": pack.can_be_captured(),
                "can_be_refunded": pack.can_be_refunded(),
                "reviewed_by": pack.reviewed_by,
                "reviewed_at": pack.reviewed_at.isoformat() if pack.reviewed_at else None
            }
            
        except Exception as e:
            print(f"❌ Error getting pack payment status: {e}")
            return None
    
    def get_admin_payment_stats(self, admin_id: int) -> dict:
        """
        Get payment statistics for an admin
        
        Args:
            admin_id: Admin user ID
            
        Returns:
            Admin payment statistics
        """
        try:
            # Get all packs reviewed by this admin
            reviewed_packs = CreatorPack.where(reviewed_by=admin_id)
            
            stats = {
                "total_reviews": len(reviewed_packs),
                "approved": 0,
                "rejected": 0,
                "payments_captured": 0,
                "payments_voided": 0,
                "total_revenue_cents": 0,
                "total_revenue_dollars": 0,
                "failed_captures": 0,
                "failed_voids": 0
            }
            
            for pack in reviewed_packs:
                if pack.status == "approved":
                    stats["approved"] += 1
                    if pack.payment_status == "captured":
                        stats["payments_captured"] += 1
                        stats["total_revenue_cents"] += pack.price_cents
                    elif pack.payment_status == "failed":
                        stats["failed_captures"] += 1
                elif pack.status == "rejected":
                    stats["rejected"] += 1
                    if pack.payment_status == "voided":
                        stats["payments_voided"] += 1
                    elif pack.payment_status == "authorized":
                        stats["failed_voids"] += 1
            
            stats["total_revenue_dollars"] = stats["total_revenue_cents"] / 100
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting admin payment stats: {e}")
            return {
                "total_reviews": 0,
                "approved": 0,
                "rejected": 0,
                "payments_captured": 0,
                "payments_voided": 0,
                "total_revenue_cents": 0,
                "total_revenue_dollars": 0,
                "failed_captures": 0,
                "failed_voids": 0
            }
    
    def validate_payment_state(self, pack_id: str) -> dict:
        """
        Validate payment state for a pack
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Validation result dict
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return {
                    "valid": False,
                    "error": "Pack not found"
                }
            
            # Check payment state consistency
            issues = []
            
            # Pack should be approved only if payment is captured
            if pack.status == "approved" and pack.payment_status != "captured":
                issues.append("Pack is approved but payment is not captured")
            
            # Pack should not be approved if payment is not captured
            if pack.payment_status == "captured" and pack.status != "approved":
                issues.append("Payment is captured but pack is not approved")
            
            # Rejected packs should have voided payments
            if pack.status == "rejected" and pack.payment_status not in ["voided", "failed", "refunded"]:
                issues.append("Pack is rejected but payment is not voided/failed/refunded")
            
            # Check for double capture prevention
            if pack.payment_status == "captured" and pack.status != "approved":
                issues.append("Payment is captured but pack is not approved")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "pack_status": pack.status,
                "payment_status": pack.payment_status
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "issues": [f"Validation error: {e}"]
            }


# Global admin payment actions instance
admin_payment_actions = AdminPaymentActions()


# Example usage
def example_usage():
    """Example of admin payment actions"""
    
    # Test approval and capture
    print("✅ Testing approval and capture...")
    success = admin_payment_actions.approve_and_capture("pack_123", 999999999)
    
    if success:
        print("✅ Pack approved and payment captured")
    else:
        print("❌ Approval and capture failed")
    
    # Test rejection and void
    print("\n❌ Testing rejection and void...")
    success = admin_payment_actions.reject_and_void("pack_456", 999999999, "Invalid content")
    
    if success:
        print("✅ Pack rejected and payment voided")
    else:
        print("❌ Rejection and void failed")
    
    # Get payment status
    print("\n📊 Getting payment status...")
    status = admin_payment_actions.get_pack_payment_status("pack_123")
    
    if status:
        print(f"✅ Payment status: {status['payment_status']}")
        print(f"   Pack status: {status['pack_status']}")
    else:
        print("❌ Failed to get payment status")


if __name__ == "__main__":
    example_usage()
