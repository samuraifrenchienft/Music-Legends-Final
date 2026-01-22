# services/creator_service.py
"""
Creator Service
Handle creator pack creation and management
"""

from typing import List, Optional
from datetime import datetime
from models.creator_pack import CreatorPack
from models.audit_minimal import AuditLog

def create_creator_pack(user_id: int, name: str, artists: List[str], genre: str) -> CreatorPack:
    """
    Create a new creator pack
    
    Args:
        user_id: Discord user ID
        name: Pack name
        artists: List of artist names
        genre: Pack genre
        
    Returns:
        Created CreatorPack object
    """
    try:
        # Validate inputs
        if not name or len(name) > 40:
            raise ValueError("Pack name must be 1-40 characters")
        
        if not genre or len(genre) > 20:
            raise ValueError("Genre must be 1-20 characters")
        
        if not artists or len(artists) < 5 or len(artists) > 25:
            raise ValueError("Must have 5-25 artists")
        
        # Create pack
        pack = CreatorPack.create(
            owner_id=user_id,
            name=name,
            artist_ids=artists,  # Store as list for now
            genre=genre,
            price_cents=999,
            payment_status="authorized",
            status="pending"
        )
        
        # Log creation
        AuditLog.record(
            event="creator_pack_created",
            user_id=user_id,
            target_id=str(pack.id),
            payload={
                "pack_name": name,
                "artist_count": len(artists),
                "genre": genre,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        return pack
        
    except Exception as e:
        # Log error
        AuditLog.record(
            event="creator_pack_creation_failed",
            user_id=user_id,
            target_id="creation",
            payload={
                "pack_name": name,
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            }
        )
        raise


def get_user_packs(user_id: int) -> List[CreatorPack]:
    """
    Get all packs for a user
    
    Args:
        user_id: Discord user ID
        
    Returns:
        List of CreatorPack objects
    """
    try:
        return CreatorPack.where(owner_id=user_id)
    except Exception as e:
        print(f"Error getting user packs: {e}")
        return []


def update_pack(pack_id: str, name: Optional[str] = None, artists: Optional[List[str]] = None, genre: Optional[str] = None) -> Optional[CreatorPack]:
    """
    Update an existing pack
    
    Args:
        pack_id: Pack ID
        name: New name (optional)
        artists: New artist list (optional)
        genre: New genre (optional)
        
    Returns:
        Updated CreatorPack object or None
    """
    try:
        pack = CreatorPack.get_by_id(pack_id)
        if not pack:
            return None
        
        # Check if pack can be edited
        if pack.status not in ["pending", "rejected"]:
            raise ValueError("Can only edit pending or rejected packs")
        
        # Update fields
        if name:
            if len(name) > 40:
                raise ValueError("Pack name must be 1-40 characters")
            pack.name = name
        
        if artists:
            if len(artists) < 5 or len(artists) > 25:
                raise ValueError("Must have 5-25 artists")
            pack.artist_ids = artists
        
        if genre:
            if len(genre) > 20:
                raise ValueError("Genre must be 1-20 characters")
            pack.genre = genre
        
        pack.save()
        
        # Log update
        AuditLog.record(
            event="creator_pack_updated",
            user_id=pack.owner_id,
            target_id=pack_id,
            payload={
                "pack_name": pack.name,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        return pack
        
    except Exception as e:
        print(f"Error updating pack: {e}")
        return None


def delete_pack(pack_id: str) -> bool:
    """
    Delete a creator pack
    
    Args:
        pack_id: Pack ID
        
    Returns:
        True if deleted successfully
    """
    try:
        pack = CreatorPack.get_by_id(pack_id)
        if not pack:
            return False
        
        # Check if pack can be deleted
        if pack.status == "approved":
            raise ValueError("Cannot delete approved packs")
        
        pack_name = pack.name
        owner_id = pack.owner_id
        
        # Delete pack
        pack.delete()
        
        # Log deletion
        AuditLog.record(
            event="creator_pack_deleted",
            user_id=owner_id,
            target_id=pack_id,
            payload={
                "pack_name": pack_name,
                "deleted_at": datetime.utcnow().isoformat()
            }
        )
        
        return True
        
    except Exception as e:
        print(f"Error deleting pack: {e}")
        return False


# Example usage
def example_usage():
    """Example of creator service usage"""
    
    try:
        # Create a pack
        pack = create_creator_pack(
            user_id=123456789,
            name="Rock Legends",
            artists=["Queen", "Led Zeppelin", "The Beatles", "Pink Floyd", "The Rolling Stones"],
            genre="Rock"
        )
        
        print(f"✅ Pack created: {pack.name}")
        print(f"   ID: {pack.id}")
        print(f"   Status: {pack.status}")
        
        # Get user packs
        packs = get_user_packs(123456789)
        print(f"✅ User has {len(packs)} packs")
        
        # Update pack
        updated_pack = update_pack(
            pack_id=str(pack.id),
            name="Updated Rock Legends"
        )
        
        if updated_pack:
            print(f"✅ Pack updated: {updated_pack.name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
