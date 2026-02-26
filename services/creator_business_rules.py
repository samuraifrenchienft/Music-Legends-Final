# services/creator_business_rules.py
"""
Creator Pack Business Rules
Flat fee pricing, legendary caps, audit compliance, queue integration
"""

from typing import Dict, List, Optional
from datetime import datetime
from models.creator_pack import CreatorPack
from models.card import Card
from models.audit_minimal import AuditLog
from services.queue_manager import QueueManager

class CreatorBusinessRules:
    """Business rules for creator pack system"""
    
    # Business constants
    FLAT_CREATION_FEE = 999  # $9.99 flat fee
    CREATOR_PROFIT_SHARE = 0.0  # 0% profit share (for now)
    LEGENDARY_CAP_PER_PACK = 2  # Max 2 legendaries per pack
    LEGENDARY_CAP_PER_USER = 10  # Max 10 legendaries per user per day
    
    # Queue priorities
    CREATOR_QUEUE_PRIORITY = 5  # Medium priority for creator operations
    
    def __init__(self):
        self.queue_manager = QueueManager()
    
    def validate_pack_creation(self, user_id: int, artist_names: List[str]) -> Dict[str, any]:
        """
        Validate pack creation against business rules
        
        Args:
            user_id: Discord user ID
            artist_names: List of artist names
            
        Returns:
            Validation result dict
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check artist count
        if len(artist_names) < 1:
            result["valid"] = False
            result["errors"].append("Pack must have at least 1 artist")
        
        if len(artist_names) > 10:
            result["valid"] = False
            result["errors"].append("Pack cannot have more than 10 artists")
        
        # Check user's legendary cap
        user_legendaries_today = self._count_user_legendaries_today(user_id)
        if user_legendaries_today >= self.LEGENDARY_CAP_PER_USER:
            result["warnings"].append(f"You've reached your daily legendary cap ({self.LEGENDARY_CAP_PER_USER})")
        
        # Check for duplicate artists
        if len(set(artist_names)) != len(artist_names):
            result["valid"] = False
            result["errors"].append("Duplicate artists not allowed")
        
        return result
    
    def calculate_pack_price(self, artist_count: int, custom_price: Optional[int] = None) -> int:
        """
        Calculate pack price based on business rules
        
        Args:
            artist_count: Number of artists in pack
            custom_price: Custom price override
            
        Returns:
            Price in cents
        """
        if custom_price is not None:
            # Validate custom price against business rules
            min_price = self.FLAT_CREATION_FEE
            max_price = self.FLAT_CREATION_FEE * 5  # Max 5x flat fee
            
            if custom_price < min_price:
                return min_price
            elif custom_price > max_price:
                return max_price
            else:
                return custom_price
        
        # Default: flat fee regardless of artist count
        return self.FLAT_CREATION_FEE
    
    def validate_pack_opening(self, user_id: int, pack: CreatorPack) -> Dict[str, any]:
        """
        Validate pack opening against business rules
        
        Args:
            user_id: Discord user ID
            pack: CreatorPack object
            
        Returns:
            Validation result dict
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check pack status
        if pack.status != "active":
            result["valid"] = False
            result["errors"].append("Pack is not active")
        
        # Check user's legendary cap for today
        user_legendaries_today = self._count_user_legendaries_today(user_id)
        if user_legendaries_today >= self.LEGENDARY_CAP_PER_USER:
            result["warnings"].append(f"You've reached your daily legendary cap ({self.LEGENDARY_CAP_PER_USER})")
        
        return result
    
    def enforce_legendary_cap(self, cards: List[Card], user_id: int) -> List[Card]:
        """
        Enforce legendary caps on opened cards
        
        Args:
            cards: List of generated cards
            user_id: Discord user ID
            
        Returns:
            Filtered list of cards
        """
        user_legendaries_today = self._count_user_legendaries_today(user_id)
        remaining_cap = self.LEGENDARY_CAP_PER_USER - user_legendaries_today
        
        if remaining_cap <= 0:
            # User has reached cap, remove all legendaries
            filtered_cards = [c for c in cards if c.tier != "legendary"]
            
            # Log cap enforcement
            AuditLog.record(
                event="legendary_cap_enforced",
                user_id=user_id,
                target_id="creator_pack",
                payload={
                    "attempted_legendaries": len([c for c in cards if c.tier == "legendary"]),
                    "allowed_legendaries": 0,
                    "cap": self.LEGENDARY_CAP_PER_USER
                }
            )
            
            return filtered_cards
        
        elif len([c for c in cards if c.tier == "legendary"]) > remaining_cap:
            # Too many legendaries, keep only allowed amount
            legendary_cards = [c for c in cards if c.tier == "legendary"]
            non_legendary_cards = [c for c in cards if c.tier != "legendary"]
            
            # Keep only allowed legendaries
            allowed_legendaries = legendary_cards[:remaining_cap]
            filtered_cards = allowed_legendaries + non_legendary_cards
            
            # Log cap enforcement
            AuditLog.record(
                event="legendary_cap_partial",
                user_id=user_id,
                target_id="creator_pack",
                payload={
                    "attempted_legendaries": len(legendary_cards),
                    "allowed_legendaries": len(allowed_legendaries),
                    "cap": self.LEGENDARY_CAP_PER_USER
                }
            )
            
            return filtered_cards
        
        # No cap issues
        return cards
    
    def audit_pack_creation(self, user_id: int, pack: CreatorPack, artist_names: List[str]):
        """
        Audit pack creation for compliance
        
        Args:
            user_id: Discord user ID
            pack: Created CreatorPack
            artist_names: Original artist names
        """
        AuditLog.record(
            event="creator_pack_created",
            user_id=user_id,
            target_id=str(pack.id),
            payload={
                "pack_name": pack.name,
                "genre": pack.genre,
                "artist_count": len(pack.artist_ids),
                "artist_names": artist_names,
                "price_cents": pack.price_cents,
                "branding": pack.branding,
                "flat_fee": self.FLAT_CREATION_FEE
            }
        )
    
    def audit_pack_opening(self, user_id: int, pack: CreatorPack, cards: List[Card]):
        """
        Audit pack opening for compliance
        
        Args:
            user_id: Discord user ID
            pack: Opened CreatorPack
            cards: Generated cards
        """
        card_details = []
        for card in cards:
            card_details.append({
                "serial": card.serial,
                "tier": card.tier,
                "artist_id": card.artist_id,
                "source": card.source
            })
        
        AuditLog.record(
            event="creator_pack_opened",
            user_id=user_id,
            target_id=str(pack.id),
            payload={
                "pack_name": pack.name,
                "card_count": len(cards),
                "cards": card_details,
                "price_paid": pack.price_cents
            }
        )
    
    def queue_pack_creation(self, user_id: int, pack_data: Dict[str, any]) -> str:
        """
        Queue pack creation for processing
        
        Args:
            user_id: Discord user ID
            pack_data: Pack creation data
            
        Returns:
            Queue job ID
        """
        job_data = {
            "type": "creator_pack_creation",
            "user_id": user_id,
            "pack_data": pack_data,
            "priority": self.CREATOR_QUEUE_PRIORITY,
            "created_at": datetime.utcnow().isoformat()
        }
        
        job_id = self.queue_manager.enqueue(job_data)
        
        # Log queuing
        AuditLog.record(
            event="creator_pack_queued",
            user_id=user_id,
            target_id=job_id,
            payload=job_data
        )
        
        return job_id
    
    def queue_pack_opening(self, user_id: int, pack_id: str) -> str:
        """
        Queue pack opening for processing
        
        Args:
            user_id: Discord user ID
            pack_id: Pack ID
            
        Returns:
            Queue job ID
        """
        job_data = {
            "type": "creator_pack_opening",
            "user_id": user_id,
            "pack_id": pack_id,
            "priority": self.CREATOR_QUEUE_PRIORITY,
            "created_at": datetime.utcnow().isoformat()
        }
        
        job_id = self.queue_manager.enqueue(job_data)
        
        # Log queuing
        AuditLog.record(
            event="creator_pack_open_queued",
            user_id=user_id,
            target_id=job_id,
            payload=job_data
        )
        
        return job_id
    
    def calculate_creator_revenue(self, pack: CreatorPack) -> Dict[str, int]:
        """
        Calculate revenue breakdown for creator pack
        
        Args:
            pack: CreatorPack object
            
        Returns:
            Revenue breakdown dict
        """
        total_revenue = pack.price_cents
        platform_fee = total_revenue  # 100% to platform (no profit sharing yet)
        creator_earnings = 0  # No profit sharing for now
        
        return {
            "total_revenue": total_revenue,
            "platform_fee": platform_fee,
            "creator_earnings": creator_earnings,
            "profit_share_rate": self.CREATOR_PROFIT_SHARE
        }
    
    def get_creator_statistics(self, user_id: int) -> Dict[str, any]:
        """
        Get creator statistics for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Creator statistics dict
        """
        packs = CreatorPack.get_by_owner(user_id)
        
        if not packs:
            return {
                "total_packs": 0,
                "total_purchases": 0,
                "total_revenue": 0,
                "average_price": 0,
                "top_genre": None,
                "packs_by_genre": {}
            }
        
        total_purchases = sum(pack.purchase_count for pack in packs)
        total_revenue = sum(pack.price_cents * pack.purchase_count for pack in packs)
        average_price = sum(pack.price_cents for pack in packs) / len(packs)
        
        # Genre breakdown
        genre_counts = {}
        for pack in packs:
            genre = pack.genre or "unknown"
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        top_genre = max(genre_counts, key=genre_counts.get) if genre_counts else None
        
        return {
            "total_packs": len(packs),
            "total_purchases": total_purchases,
            "total_revenue": total_revenue,
            "average_price": average_price,
            "top_genre": top_genre,
            "packs_by_genre": genre_counts
        }
    
    def _count_user_legendaries_today(self, user_id: int) -> int:
        """
        Count legendary cards user has received today
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Count of legendary cards today
        """
        # This would query the audit logs for today's legendary cards
        # For now, return 0 as placeholder
        today = datetime.utcnow().date()
        
        # Query audit logs for legendary cards today
        # This is a simplified implementation
        try:
            legendary_logs = AuditLog.query.filter(
                AuditLog.event == "creator_pack_opened",
                AuditLog.user_id == user_id,
                AuditLog.created_at >= today
            ).all()
            
            legendary_count = 0
            for log in legendary_logs:
                cards = log.payload.get("cards", [])
                legendary_count += sum(1 for card in cards if card.get("tier") == "legendary")
            
            return legendary_count
            
        except Exception:
            return 0  # Fallback to 0 if audit query fails


# Global business rules instance
creator_business_rules = CreatorBusinessRules()


# Example usage
def example_usage():
    """Example of business rules usage"""
    
    # Validate pack creation
    validation = creator_business_rules.validate_pack_creation(
        user_id=123456789,
        artist_names=["Queen", "Led Zeppelin", "The Beatles"]
    )
    
    if validation["valid"]:
        print("✅ Pack creation validation passed")
    else:
        print("❌ Pack creation validation failed:")
        for error in validation["errors"]:
            print(f"   Error: {error}")
    
    # Calculate pack price
    price = creator_business_rules.calculate_pack_price(artist_count=3)
    print(f"💰 Pack price: ${price / 100:.2f}")
    
    # Get creator statistics
    stats = creator_business_rules.get_creator_statistics(123456789)
    print(f"📊 Creator stats: {stats['total_packs']} packs, ${stats['total_revenue'] / 100:.2f} revenue")


if __name__ == "__main__":
    example_usage()
