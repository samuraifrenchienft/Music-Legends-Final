# models/creator_pack.py
"""
Creator Pack Model
User-created custom card packs with payment integration
"""

from sqlalchemy import Column, String, Integer, DateTime, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from models.base import Model
import uuid

class CreatorPack(Model):
    __tablename__ = "creator_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    owner_id = Column(BigInteger, nullable=False)
    
    name = Column(String(60), nullable=False)
    genre = Column(String(20), nullable=False)
    
    artist_ids = Column(JSON, nullable=False)  # locked roster
    
    branding = Column(String(20), default="samurai")
    
    # Payment fields
    payment_id = Column(String(80), nullable=True)  # Stripe payment intent ID
    payment_status = Column(String(20), default="authorized")  # authorized, captured, failed, refunded
    price_cents = Column(Integer, nullable=False, default=999)
    
    status = Column(String(20), default="pending")  # pending → approved → rejected → disabled
    
    # Moderation fields
    notes = Column(String(200))
    reviewed_by = Column(BigInteger, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(500))
    
    # Additional fields
    description = Column(String(500))
    purchase_count = Column(Integer, default=0)
    rating = Column(Integer, default=0)
    featured = Column(String(10), default="false")  # true/false
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def create(cls, **kwargs):
        """Create a new creator pack"""
        pack = cls(**kwargs)
        pack.save()
        return pack
    
    @classmethod
    def get_by_owner(cls, owner_id: int, status: str = None):
        """Get packs by owner"""
        if status:
            return cls.where(owner_id=owner_id, status=status)
        else:
            return cls.where(owner_id=owner_id)
    
    @classmethod
    def get_pending(cls, limit: int = 50):
        """Get pending packs for review"""
        return cls.where(status="pending").limit(limit)
    
    @classmethod
    def get_approved(cls, limit: int = 20):
        """Get approved packs"""
        return cls.where(status="approved").limit(limit)
    
    @classmethod
    def get_featured(cls, limit: int = 10):
        """Get featured creator packs"""
        return cls.where(featured="true", status="approved").limit(limit)
    
    @classmethod
    def get_by_genre(cls, genre: str, limit: int = 20):
        """Get packs by genre"""
        return cls.where(genre=genre, status="approved").limit(limit)
    
    @classmethod
    def search(cls, query: str, limit: int = 20):
        """Search packs by name"""
        return cls.where(
            "name ILIKE ? AND status = ?", 
            f"%{query}%", 
            "approved"
        ).limit(limit)
    
    @classmethod
    def get_by_payment_id(cls, payment_id: str):
        """Get pack by payment ID"""
        return cls.where(payment_id=payment_id).first()
    
    def get_artists(self):
        """Get artist objects for this pack"""
        from models.artist import Artist
        return Artist.where_in("id", self.artist_ids)
    
    def get_card_count(self):
        """Get number of cards in this pack"""
        return len(self.artist_ids) if self.artist_ids else 0
    
    def approve(self, reviewer_id: int, notes: str = ""):
        """Approve the pack"""
        self.status = "approved"
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.notes = notes
        self.save()
    
    def reject(self, reviewer_id: int, reason: str, notes: str = ""):
        """Reject the pack"""
        self.status = "rejected"
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason
        self.notes = notes
        self.save()
    
    def disable(self, reviewer_id: int, reason: str):
        """Disable the pack"""
        self.status = "disabled"
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason
        self.save()
    
    def capture_payment(self):
        """Mark payment as captured"""
        self.payment_status = "captured"
        self.save()
    
    def refund_payment(self):
        """Mark payment as refunded"""
        self.payment_status = "refunded"
        self.save()
    
    def fail_payment(self):
        """Mark payment as failed"""
        self.payment_status = "failed"
        self.save()
    
    def is_payment_authorized(self):
        """Check if payment is authorized"""
        return self.payment_status == "authorized"
    
    def is_payment_captured(self):
        """Check if payment is captured"""
        return self.payment_status == "captured"
    
    def is_payment_failed(self):
        """Check if payment is failed"""
        return self.payment_status == "failed"
    
    def is_payment_refunded(self):
        """Check if payment is refunded"""
        return self.payment_status == "refunded"
    
    def can_be_captured(self):
        """Check if payment can be captured"""
        return self.payment_status == "authorized" and self.status == "approved"
    
    def can_be_refunded(self):
        """Check if payment can be refunded"""
        return self.payment_status == "captured"
    
    def update_rating(self, new_rating: int):
        """Update pack rating"""
        self.rating = new_rating
        self.save()
    
    def increment_purchases(self):
        """Increment purchase count"""
        self.purchase_count += 1
        self.save()
    
    def is_active(self):
        """Check if pack is active for purchase"""
        return self.status == "approved" and self.payment_status == "captured"
    
    def can_be_edited(self):
        """Check if pack can be edited by owner"""
        return self.status in ["pending", "rejected"] and not self.is_payment_captured()
    
    def get_review_history(self):
        """Get review history"""
        return {
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "notes": self.notes,
            "rejection_reason": self.rejection_reason
        }
    
    def get_payment_info(self):
        """Get payment information"""
        return {
            "payment_id": self.payment_id,
            "payment_status": self.payment_status,
            "price_cents": self.price_cents,
            "price_dollars": self.price_cents / 100,
            "can_be_captured": self.can_be_captured(),
            "can_be_refunded": self.can_be_refunded(),
            "is_authorized": self.is_payment_authorized(),
            "is_captured": self.is_payment_captured(),
            "is_failed": self.is_payment_failed(),
            "is_refunded": self.is_payment_refunded()
        }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "owner_id": self.owner_id,
            "name": self.name,
            "genre": self.genre,
            "artist_ids": self.artist_ids,
            "artist_count": self.get_card_count(),
            "branding": self.branding,
            "price_cents": self.price_cents,
            "price_dollars": self.price_cents / 100,
            "status": self.status,
            "payment_info": self.get_payment_info(),
            "description": self.description,
            "purchase_count": self.purchase_count,
            "rating": self.rating,
            "featured": self.featured,
            "review_history": self.get_review_history(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
