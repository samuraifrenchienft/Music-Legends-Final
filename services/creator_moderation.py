# services/creator_moderation.py
"""
Creator Pack Moderation Service
Validation rules and content safety for creator packs
"""

import re
from typing import List, Tuple, Dict, Optional, Set
from datetime import datetime
from models.creator_pack import CreatorPack
from models.audit_minimal import AuditLog

# Business rules
MAX_ARTISTS = 25
MIN_ARTISTS = 5

# Banned keywords and patterns
BANNED_KEYWORDS = [
    "official", "vevo", "topic",
    "reupload", "free music", "download",
    "torrent", "pirate", "illegal", "stolen",
    "copyright", "infringement", "unauthorized"
]

# Suspicious patterns
SUSPICIOUS_PATTERNS = [
    r'\.com$',  # URLs
    r'http[s]?://',  # HTTP/HTTPS
    r'www\.',  # www
    r'\.org$',  .org domains
    r'\.net$',  .net domains
    r'@',  # Email addresses
    r'\d{4,}',  # Long numbers (potential phone numbers)
]

# Inappropriate content
INAPPROPRIATE_CONTENT = [
    "nsfw", "porn", "xxx", "adult",
    "hate", "racist", "nazi", "terrorist",
    "drug", "illegal", "weapon", "violence",
    "suicide", "self-harm", "explicit"
]

# Artist impersonation patterns
IMPERSONATION_PATTERNS = [
    r'official',
    r'vevo',
    r'channel',
    r'music',
    r'records',
    r'studio',
    r'entertainment',
    r'productions'
]

class CreatorModeration:
    """Moderation service for creator packs"""
    
    def __init__(self):
        self.banned_artists = self._load_banned_artists()
        self.pending_reviews = []
        self.approved_creators = set()
        
    def _load_banned_artists(self) -> Set[str]:
        """Load list of banned artists"""
        # This would typically come from a database or config file
        # For now, return a sample set
        return {
            "banned_artist_1",
            "banned_artist_2",
            "suspended_user_1"
        }
    
    def validate_pack(self, name: str, artists: List[str], user_id: int) -> Tuple[bool, str]:
        """
        Validate pack against all moderation rules
        
        Args:
            name: Pack name
            artists: List of artist names
            user_id: User ID
            
        Returns:
            (is_valid, error_message)
        """
        # Check roster size
        if not (MIN_ARTISTS <= len(artists) <= MAX_ARTISTS):
            return False, f"Roster must be {MIN_ARTISTS}–{MAX_ARTISTS} artists (got {len(artists)})"
        
        # Check for duplicates
        if len(set(artists)) != len(artists):
            return False, "Duplicate artists not allowed"
        
        # Validate pack name
        name_valid, name_error = self._validate_pack_name(name, user_id)
        if not name_valid:
            return False, name_error
        
        # Validate each artist
        for artist in artists:
            artist_valid, artist_error = self._validate_artist(artist, user_id)
            if not artist_valid:
                return False, artist_error
        
        # Check for too many high-tier artists
        high_tier_count = self._count_high_tier_artists(artists)
        if high_tier_count > len(artists) * 0.6:  # More than 60% high-tier
            return False, f"Too many high-tier artists ({high_tier_count}/{len(artists)}). Maximum 60% allowed."
        
        return True, "ok"
    
    def _validate_pack_name(self, name: str, user_id: int) -> Tuple[bool, str]:
        """Validate pack name"""
        if not name or len(name.strip()) == 0:
            return False, "Pack name cannot be empty"
        
        if len(name) > 60:
            return False, "Pack name too long (max 60 characters)"
        
        # Check for banned keywords
        name_lower = name.lower()
        for keyword in BANNED_KEYWORDS:
            if keyword in name_lower:
                return False, f"Pack name contains banned keyword: {keyword}"
        
        # Check for inappropriate content
        for word in INAPPROPRIATE_CONTENT:
            if word in name_lower:
                return False, f"Pack name contains inappropriate content: {word}"
        
        # Check for suspicious patterns
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, name_lower):
                return False, f"Pack name contains suspicious pattern: {pattern}"
        
        # Check for impersonation
        if self._is_impersonation_attempt(name_lower):
            return False, "Pack name suggests impersonation"
        
        # Check user's pack limit
        user_packs = CreatorPack.get_by_owner(user_id, status="pending")
        if len(user_packs) >= 5:  # Max 5 pending packs per user
            return False, "Too many pending packs. Wait for current packs to be reviewed."
        
        return True, "ok"
    
    def _validate_artist(self, artist: str, user_id: int) -> Tuple[bool, str]:
        """Validate individual artist"""
        if not artist or len(artist.strip()) == 0:
            return False, "Artist name cannot be empty"
        
        artist_clean = artist.strip()
        artist_lower = artist_clean.lower()
        
        # Check banned artists
        if artist_lower in [a.lower() for a in self.banned_artists]:
            return False, f"Artist is banned: {artist}"
        
        # Check for banned keywords
        for keyword in BANNED_KEYWORDS:
            if keyword in artist_lower:
                return False, f"Artist name contains banned keyword: {keyword}"
        
        # Check for inappropriate content
        for word in INAPPROPRIATE_CONTENT:
            if word in artist_lower:
                return False, f"Artist name contains inappropriate content: {word}"
        
        # Check for suspicious patterns
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, artist_lower):
                return False, f"Artist name contains suspicious pattern: {pattern}"
        
        # Check for impersonation
        if self._is_impersonation_attempt(artist_lower):
            return False, f"Artist name suggests impersonation: {artist}"
        
        # Check for valid format (basic validation)
        if not re.match(r'^[a-zA-Z0-9\s\-\.\'\&]+$', artist_clean):
            return False, f"Artist name contains invalid characters: {artist}"
        
        return True, "ok"
    
    def _is_impersonation_attempt(self, text: str) -> bool:
        """Check if text suggests impersonation"""
        for pattern in IMPERSONATION_PATTERNS:
            if pattern in text:
                return True
        return False
    
    def _count_high_tier_artists(self, artists: List[str]) -> int:
        """Count high-tier artists (would need actual artist data)"""
        # This is a simplified implementation
        # In reality, you'd check actual artist tiers from database
        high_tier_keywords = ["legendary", "platinum", "gold", "queen", "beatles", "zeppelin"]
        
        count = 0
        for artist in artists:
            artist_lower = artist.lower()
            for keyword in high_tier_keywords:
                if keyword in artist_lower:
                    count += 1
                    break
        
        return count
    
    def check_image_safety(self, image_url: str) -> Tuple[bool, str]:
        """
        Check if image URL is safe
        
        Args:
            image_url: Image URL to check
            
        Returns:
            (is_safe, reason)
        """
        if not image_url:
            return True, "No image provided"
        
        # Check for suspicious domains
        suspicious_domains = [
            "nsfw", "adult", "xxx", "porn",
            "suspicious", "malware", "virus"
        ]
        
        url_lower = image_url.lower()
        for domain in suspicious_domains:
            if domain in url_lower:
                return False, f"Image from suspicious domain: {domain}"
        
        # Check file extensions
        unsafe_extensions = [".exe", ".bat", ".cmd", ".scr", ".zip", ".rar"]
        for ext in unsafe_extensions:
            if url_lower.endswith(ext):
                return False, f"Unsafe file type: {ext}"
        
        # Basic URL validation
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            return False, "Invalid URL protocol"
        
        return True, "ok"
    
    def submit_for_review(self, pack: CreatorPack, user_id: int) -> bool:
        """
        Submit pack for admin review
        
        Args:
            pack: CreatorPack object
            user_id: Submitting user ID
            
        Returns:
            True if submitted successfully
        """
        try:
            # Validate before submission
            artists = pack.get_artists()
            artist_names = [artist.name for artist in artists]
            
            is_valid, error_message = self.validate_pack(pack.name, artist_names, user_id)
            
            if not is_valid:
                return False
            
            # Set status to pending
            pack.status = "pending"
            pack.save()
            
            # Add to review queue
            self.pending_reviews.append({
                "pack_id": str(pack.id),
                "user_id": user_id,
                "submitted_at": datetime.utcnow(),
                "pack_name": pack.name,
                "artist_count": len(artist_names)
            })
            
            # Log submission
            AuditLog.record(
                event="creator_pack_submitted",
                user_id=user_id,
                target_id=str(pack.id),
                payload={
                    "pack_name": pack.name,
                    "artist_count": len(artist_names),
                    "genre": pack.genre
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error submitting pack for review: {e}")
            return False
    
    def get_pending_reviews(self, limit: int = 50) -> List[Dict]:
        """Get list of pending reviews"""
        return self.pending_reviews[:limit]
    
    def approve_pack(self, pack_id: str, reviewer_id: int, notes: str = "") -> bool:
        """
        Approve a pending pack
        
        Args:
            pack_id: Pack ID
            reviewer_id: Reviewer ID
            notes: Review notes
            
        Returns:
            True if approved successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            if pack.status != "pending":
                return False
            
            # Approve the pack
            pack.approve(reviewer_id, notes)
            
            # Remove from pending reviews
            self.pending_reviews = [
                r for r in self.pending_reviews 
                if r["pack_id"] != pack_id
            ]
            
            # Add to approved creators
            self.approved_creators.add(pack.owner_id)
            
            # Log approval
            AuditLog.record(
                event="creator_pack_approved",
                user_id=reviewer_id,
                target_id=pack_id,
                payload={
                    "pack_name": pack.name,
                    "reviewer_notes": notes,
                    "approved_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error approving pack: {e}")
            return False
    
    def reject_pack(self, pack_id: str, reviewer_id: int, reason: str, notes: str = "") -> bool:
        """
        Reject a pending pack
        
        Args:
            pack_id: Pack ID
            reviewer_id: Reviewer ID
            reason: Rejection reason
            notes: Review notes
            
        Returns:
            True if rejected successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            if pack.status != "pending":
                return False
            
            # Reject the pack
            pack.reject(reviewer_id, reason, notes)
            
            # Remove from pending reviews
            self.pending_reviews = [
                r for r in self.pending_reviews 
                if r["pack_id"] != pack_id
            ]
            
            # Log rejection
            AuditLog.record(
                event="creator_pack_rejected",
                user_id=reviewer_id,
                target_id=pack_id,
                payload={
                    "pack_name": pack.name,
                    "rejection_reason": reason,
                    "reviewer_notes": notes,
                    "rejected_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error rejecting pack: {e}")
            return False
    
    def disable_pack(self, pack_id: str, reviewer_id: int, reason: str) -> bool:
        """
        Disable an approved pack
        
        Args:
            pack_id: Pack ID
            reviewer_id: Reviewer ID
            reason: Disable reason
            
        Returns:
            True if disabled successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            # Disable the pack
            pack.disable(reviewer_id, reason)
            
            # Log disabling
            AuditLog.record(
                event="creator_pack_disabled",
                user_id=reviewer_id,
                target_id=pack_id,
                payload={
                    "pack_name": pack.name,
                    "disable_reason": reason,
                    "disabled_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error disabling pack: {e}")
            return False
    
    def get_moderation_stats(self) -> Dict:
        """Get moderation statistics"""
        try:
            total_packs = len(CreatorPack.all())
            pending_packs = len(CreatorPack.get_pending())
            approved_packs = len(CreatorPack.get_approved())
            rejected_packs = len(CreatorPack.where(status="rejected"))
            
            return {
                "total_packs": total_packs,
                "pending_packs": pending_packs,
                "approved_packs": approved_packs,
                "rejected_packs": rejected_packs,
                "approval_rate": (approved_packs / total_packs * 100) if total_packs > 0 else 0,
                "pending_reviews": len(self.pending_reviews),
                "approved_creators": len(self.approved_creators)
            }
            
        except Exception as e:
            print(f"❌ Error getting moderation stats: {e}")
            return {
                "total_packs": 0,
                "pending_packs": 0,
                "approved_packs": 0,
                "rejected_packs": 0,
                "approval_rate": 0,
                "pending_reviews": 0,
                "approved_creators": 0
            }


# Global moderation instance
creator_moderation = CreatorModeration()


# Convenience functions for backward compatibility
def validate_pack(name: str, artists: List[str]) -> Tuple[bool, str]:
    """Validate pack (simplified version)"""
    return creator_moderation.validate_pack(name, artists, 0)


# Example usage
def example_usage():
    """Example of moderation usage"""
    
    # Test validation
    valid, message = creator_moderation.validate_pack(
        name="Rock Legends",
        artists=["Queen", "Led Zeppelin", "The Beatles"],
        user_id=123456789
    )
    
    if valid:
        print("✅ Pack validation passed")
    else:
        print(f"❌ Pack validation failed: {message}")
    
    # Test image safety
    image_safe, image_reason = creator_moderation.check_image_safety("https://example.com/image.jpg")
    print(f"✅ Image safety: {image_safe} - {image_reason}")
    
    # Get moderation stats
    stats = creator_moderation.get_moderation_stats()
    print(f"📊 Moderation stats: {stats}")


if __name__ == "__main__":
    example_usage()
