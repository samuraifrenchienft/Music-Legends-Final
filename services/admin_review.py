# services/admin_review.py
"""
Admin Review Service
Handle admin approval/rejection of creator packs
"""

from typing import Optional, Dict, Any
from datetime import datetime
from models.creator_pack import CreatorPack
from models.audit_minimal import AuditLog
from services.creator_moderation import creator_moderation

class AdminReviewService:
    """Service for admin review of creator packs"""
    
    def __init__(self):
        self.moderation = creator_moderation
    
    def review_pack(self, pack_id: str, admin_id: int, approve: bool, note: str = "") -> Optional[str]:
        """
        Review and approve/reject a creator pack
        
        Args:
            pack_id: Pack ID to review
            admin_id: Admin user ID
            approve: True to approve, False to reject
            note: Review notes
            
        Returns:
            Pack status or None if failed
        """
        try:
            # Get the pack
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return None
            
            # Check if pack is in reviewable state
            if pack.status not in ["pending", "rejected"]:
                return pack.status  # Return current status if not reviewable
            
            # Perform final validation before approval
            if approve:
                validation_result = self._final_validation(pack)
                if not validation_result["valid"]:
                    # Reject with validation failure reason
                    pack.status = "rejected"
                    pack.reviewed_by = admin_id
                    pack.reviewed_at = datetime.utcnow()
                    pack.rejection_reason = validation_result["reason"]
                    pack.notes = note
                    pack.save()
                    
                    # Refund payment on rejection
                    from services.creator_pack_payment import creator_pack_payment
                    creator_pack_payment.refund_payment_on_rejection(pack_id, admin_id, validation_result["reason"])
                    
                    # Log rejection
                    self._log_review(pack, admin_id, False, note, validation_result["reason"])
                    return "rejected"
            
            # Update pack status
            status = "approved" if approve else "rejected"
            pack.status = status
            pack.reviewed_by = admin_id
            pack.reviewed_at = datetime.utcnow()
            pack.notes = note
            
            if not approve:
                pack.rejection_reason = note or "Rejected by admin"
                
                # Refund payment on rejection
                from services.creator_pack_payment import creator_pack_payment
                creator_pack_payment.refund_payment_on_rejection(pack_id, admin_id, pack.rejection_reason)
            
            pack.save()
            
            # Log the review
            self._log_review(pack, admin_id, approve, note, pack.rejection_reason if not approve else "")
            
            # If approved, capture payment and remove from pending reviews
            if approve:
                # Capture payment
                from services.creator_pack_payment import creator_pack_payment
                payment_captured = creator_pack_payment.capture_payment_on_approval(pack_id, admin_id)
                
                if payment_captured:
                    # Remove from pending reviews
                    self.moderation.pending_reviews = [
                        r for r in self.moderation.pending_reviews 
                        if r["pack_id"] != pack_id
                    ]
                    
                    # Add to approved creators
                    self.moderation.approved_creators.add(pack.owner_id)
                else:
                    # Mark payment as failed if capture fails
                    creator_pack_payment.fail_payment_on_error(pack_id, "Payment capture failed")
            
            return status
            
        except Exception as e:
            print(f"❌ Error reviewing pack {pack_id}: {e}")
            return None
    
    def _final_validation(self, pack: CreatorPack) -> Dict[str, Any]:
        """
        Perform final validation before approval
        
        Args:
            pack: CreatorPack object
            
        Returns:
            Validation result dict
        """
        result = {
            "valid": True,
            "reason": "",
            "warnings": []
        }
        
        try:
            # Get artists for validation
            artists = pack.get_artists()
            artist_names = [artist.name for artist in artists]
            
            # Check for duplicates
            if len(set(artist_names)) != len(artist_names):
                result["valid"] = False
                result["reason"] = "Duplicate artists in pack"
                return result
            
            # Check for impersonation
            for artist_name in artist_names:
                if self.moderation._is_impersonation_attempt(artist_name.lower()):
                    result["valid"] = False
                    result["reason"] = f"Impersonation detected: {artist_name}"
                    return result
            
            # Check for non-music channels
            non_music_keywords = ["gaming", "vlog", "comedy", "news", "sports", "tech", "cooking"]
            for artist_name in artist_names:
                artist_lower = artist_name.lower()
                for keyword in non_music_keywords:
                    if keyword in artist_lower:
                        result["warnings"].append(f"Possible non-music channel: {artist_name}")
            
            # Check for hate/illegal content
            hate_keywords = ["hate", "racist", "nazi", "terrorist", "illegal", "crime", "violence"]
            for artist_name in artist_names:
                artist_lower = artist_name.lower()
                for keyword in hate_keywords:
                    if keyword in artist_lower:
                        result["valid"] = False
                        result["reason"] = f"Inappropriate content: {artist_name}"
                        return result
            
            # Check roster size
            if len(artists) < self.moderation.MIN_ARTISTS:
                result["valid"] = False
                result["reason"] = f"Roster too small: {len(artists)} (minimum {self.moderation.MIN_ARTISTS})"
                return result
            
            if len(artists) > self.moderation.MAX_ARTISTS:
                result["valid"] = False
                result["reason"] = f"Roster too large: {len(artists)} (maximum {self.moderation.MAX_ARTISTS})"
                return result
            
            # Check pack name
            name_valid, name_error = self.moderation._validate_pack_name(pack.name, pack.owner_id)
            if not name_valid:
                result["valid"] = False
                result["reason"] = f"Invalid pack name: {name_error}"
                return result
            
            # Check image safety if pack has image
            if hasattr(pack, 'image_url') and pack.image_url:
                image_safe, image_reason = self.moderation.check_image_safety(pack.image_url)
                if not image_safe:
                    result["warnings"].append(f"Image safety issue: {image_reason}")
            
            return result
            
        except Exception as e:
            result["valid"] = False
            result["reason"] = f"Validation error: {str(e)}"
            return result
    
    def _log_review(self, pack: CreatorPack, admin_id: int, approved: bool, note: str, reason: str = ""):
        """Log the review decision"""
        event_type = "creator_pack_approved" if approved else "creator_pack_rejected"
        
        payload = {
            "pack_name": pack.name,
            "pack_id": str(pack.id),
            "admin_id": admin_id,
            "decision": "approved" if approved else "rejected",
            "note": note,
            "reason": reason,
            "reviewed_at": datetime.utcnow().isoformat(),
            "artist_count": len(pack.artist_ids) if pack.artist_ids else 0,
            "genre": pack.genre,
            "price_cents": pack.price_cents
        }
        
        AuditLog.record(
            event=event_type,
            user_id=pack.owner_id,
            target_id=str(pack.id),
            payload=payload
        )
    
    def get_review_history(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete review history for a pack
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Review history dict or None
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return None
            
            # Get audit logs for this pack
            review_logs = AuditLog.query.filter(
                AuditLog.target_id == pack_id,
                AuditLog.event.in_(["creator_pack_submitted", "creator_pack_approved", "creator_pack_rejected", "creator_pack_disabled"])
            ).order_by(AuditLog.created_at.desc()).all()
            
            history = []
            for log in review_logs:
                history.append({
                    "event": log.event,
                    "timestamp": log.created_at.isoformat(),
                    "user_id": log.user_id,
                    "payload": log.payload
                })
            
            return {
                "pack_id": pack_id,
                "pack_name": pack.name,
                "current_status": pack.status,
                "review_history": history
            }
            
        except Exception as e:
            print(f"❌ Error getting review history for {pack_id}: {e}")
            return None
    
    def get_admin_stats(self, admin_id: int) -> Dict[str, Any]:
        """
        Get statistics for a specific admin
        
        Args:
            admin_id: Admin user ID
            
        Returns:
            Admin statistics dict
        """
        try:
            # Get audit logs for this admin
            admin_logs = AuditLog.query.filter(
                AuditLog.payload.contains({"admin_id": admin_id})
            ).all()
            
            stats = {
                "total_reviews": len(admin_logs),
                "approvals": 0,
                "rejections": 0,
                "recent_reviews": []
            }
            
            # Count approvals and rejections
            for log in admin_logs:
                if log.event == "creator_pack_approved":
                    stats["approvals"] += 1
                elif log.event == "creator_pack_rejected":
                    stats["rejections"] += 1
            
            # Get recent reviews (last 10)
            recent_logs = sorted(admin_logs, key=lambda x: x.created_at, reverse=True)[:10]
            for log in recent_logs:
                stats["recent_reviews"].append({
                    "pack_id": log.target_id,
                    "pack_name": log.payload.get("pack_name", "Unknown"),
                    "decision": log.payload.get("decision", "unknown"),
                    "timestamp": log.created_at.isoformat()
                })
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting admin stats for {admin_id}: {e}")
            return {
                "total_reviews": 0,
                "approvals": 0,
                "rejections": 0,
                "recent_reviews": []
            }
    
    def get_pending_count(self) -> int:
        """Get count of pending packs"""
        return len(self.moderation.get_pending_reviews())
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get review queue statistics"""
        pending = self.moderation.get_pending_reviews()
        
        return {
            "pending_count": len(pending),
            "oldest_pending": min([r["submitted_at"] for r in pending]) if pending else None,
            "newest_pending": max([r["submitted_at"] for r in pending]) if pending else None,
            "pending_by_genre": self._count_pending_by_genre(pending)
        }
    
    def _count_pending_by_genre(self, pending_reviews: list) -> Dict[str, int]:
        """Count pending packs by genre"""
        genre_counts = {}
        
        for review in pending_reviews:
            pack = CreatorPack.get_by_id(review["pack_id"])
            if pack:
                genre = pack.genre or "unknown"
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        return genre_counts


# Global admin review service instance
admin_review = AdminReviewService()


# Convenience function for backward compatibility
def review_pack(pack_id: str, admin_id: int, approve: bool, note: str = "") -> Optional[str]:
    """Review pack (simplified version)"""
    return admin_review.review_pack(pack_id, admin_id, approve, note)


# Example usage
def example_usage():
    """Example of admin review usage"""
    
    # Approve a pack
    result = admin_review.review_pack(
        pack_id="pack_123",
        admin_id=123456789,
        approve=True,
        note="Good quality pack with diverse artists"
    )
    
    print(f"✅ Review result: {result}")
    
    # Reject a pack
    result = admin_review.review_pack(
        pack_id="pack_456",
        admin_id=123456789,
        approve=False,
        note="Contains duplicate artists"
    )
    
    print(f"❌ Review result: {result}")
    
    # Get review history
    history = admin_review.get_review_history("pack_123")
    if history:
        print(f"📋 Review history for {history['pack_name']}: {len(history['review_history'])} events")


if __name__ == "__main__":
    example_usage()
