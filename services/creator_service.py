# services/creator_service.py
"""
Creator Pack Service
Manage user-created custom card packs
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.creator_pack import CreatorPack
from services.youtube_client import YouTubeClient
from services.artist_pipeline import import_artist_to_card
from services.card_factory import create_from_artist
from models.artist import Artist

class CreatorService:
    """Service for managing creator packs"""
    
    def __init__(self):
        self.youtube_client = YouTubeClient()
    
    async def create_creator_pack(self, user_id: int, name: str, artist_names: List[str], 
                                 genre: str, price_cents: int = 999, 
                                 description: str = "", branding: str = "samurai") -> Optional[CreatorPack]:
        """
        Create a new creator pack
        
        Args:
            user_id: Discord user ID
            name: Pack name
            artist_names: List of artist names to include
            genre: Pack genre
            price_cents: Price in cents
            description: Pack description
            branding: Visual branding theme
            
        Returns:
            Created CreatorPack or None
        """
        try:
            # Validate inputs
            if not name or len(name) > 60:
                raise ValueError("Pack name must be 1-60 characters")
            
            if not artist_names or len(artist_names) > 10:
                raise ValueError("Pack must have 1-10 artists")
            
            if not genre or len(genre) > 20:
                raise ValueError("Genre must be 1-20 characters")
            
            # Ensure artists exist and get their IDs
            artist_ids = []
            
            for artist_name in artist_names:
                try:
                    # Import artist and create card
                    card = await import_artist_to_card(artist_name)
                    if card:
                        artist_ids.append(card.artist_id)
                    else:
                        print(f"⚠️  Could not import artist: {artist_name}")
                        
                except Exception as e:
                    print(f"❌ Error importing artist {artist_name}: {e}")
                    continue
            
            if not artist_ids:
                raise ValueError("No valid artists could be imported")
            
            # Create creator pack
            pack = CreatorPack.create(
                owner_id=user_id,
                name=name,
                artist_ids=artist_ids,
                genre=genre,
                price_cents=price_cents,
                description=description,
                branding=branding,
                status="active"
            )
            
            print(f"✅ Created creator pack: {pack.name} with {len(artist_ids)} artists")
            return pack
            
        except Exception as e:
            print(f"❌ Error creating creator pack: {e}")
            return None
    
    async def create_pack_from_existing_artists(self, user_id: int, name: str, 
                                              artist_ids: List[str], genre: str,
                                              **kwargs) -> Optional[CreatorPack]:
        """
        Create a pack from existing artist IDs
        
        Args:
            user_id: Discord user ID
            name: Pack name
            artist_ids: List of existing artist IDs
            genre: Pack genre
            **kwargs: Additional pack fields
            
        Returns:
            Created CreatorPack or None
        """
        try:
            # Validate artists exist
            existing_artists = Artist.where_in("id", artist_ids)
            existing_ids = [artist.id for artist in existing_artists]
            
            if len(existing_ids) != len(artist_ids):
                missing = set(artist_ids) - set(existing_ids)
                raise ValueError(f"Artists not found: {missing}")
            
            # Create pack
            pack = CreatorPack.create(
                owner_id=user_id,
                name=name,
                artist_ids=existing_ids,
                genre=genre,
                **kwargs
            )
            
            return pack
            
        except Exception as e:
            print(f"❌ Error creating pack from existing artists: {e}")
            return None
    
    def get_user_packs(self, user_id: int, status: str = "active") -> List[CreatorPack]:
        """
        Get all packs for a user
        
        Args:
            user_id: Discord user ID
            status: Pack status filter
            
        Returns:
            List of CreatorPack objects
        """
        try:
            return CreatorPack.get_by_owner(user_id, status)
        except Exception as e:
            print(f"❌ Error getting user packs: {e}")
            return []
    
    def get_featured_packs(self, limit: int = 10) -> List[CreatorPack]:
        """
        Get featured creator packs
        
        Args:
            limit: Maximum number of packs
            
        Returns:
            List of CreatorPack objects
        """
        try:
            return CreatorPack.get_featured(limit)
        except Exception as e:
            print(f"❌ Error getting featured packs: {e}")
            return []
    
    def get_packs_by_genre(self, genre: str, limit: int = 20) -> List[CreatorPack]:
        """
        Get packs by genre
        
        Args:
            genre: Music genre
            limit: Maximum number of packs
            
        Returns:
            List of CreatorPack objects
        """
        try:
            return CreatorPack.get_by_genre(genre, limit)
        except Exception as e:
            print(f"❌ Error getting packs by genre: {e}")
            return []
    
    def search_packs(self, query: str, limit: int = 20) -> List[CreatorPack]:
        """
        Search packs by name
        
        Args:
            query: Search query
            limit: Maximum number of packs
            
        Returns:
            List of CreatorPack objects
        """
        try:
            return CreatorPack.search(query, limit)
        except Exception as e:
            print(f"❌ Error searching packs: {e}")
            return []
    
    def get_pack_details(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed pack information
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Pack details dictionary or None
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return None
            
            # Get artist details
            artists = pack.get_artists()
            artist_details = []
            
            for artist in artists:
                artist_details.append({
                    "id": artist.id,
                    "name": artist.name,
                    "genre": artist.genre,
                    "tier": artist.tier,
                    "image_url": getattr(artist, 'image_url', ''),
                    "popularity": getattr(artist, 'popularity', 0)
                })
            
            # Build pack details
            details = pack.to_dict()
            details["artists"] = artist_details
            
            return details
            
        except Exception as e:
            print(f"❌ Error getting pack details: {e}")
            return None
    
    def update_pack(self, pack_id: str, user_id: int, **updates) -> bool:
        """
        Update pack details
        
        Args:
            pack_id: Pack ID
            user_id: User ID (for ownership verification)
            **updates: Fields to update
            
        Returns:
            True if updated successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack or pack.owner_id != user_id:
                return False
            
            # Update allowed fields
            allowed_fields = ["name", "description", "price_cents", "branding"]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(pack, field, value)
            
            pack.updated_at = datetime.utcnow()
            pack.save()
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating pack: {e}")
            return False
    
    def delete_pack(self, pack_id: str, user_id: int) -> bool:
        """
        Delete a creator pack
        
        Args:
            pack_id: Pack ID
            user_id: User ID (for ownership verification)
            
        Returns:
            True if deleted successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack or pack.owner_id != user_id:
                return False
            
            pack.delete()
            return True
            
        except Exception as e:
            print(f"❌ Error deleting pack: {e}")
            return False
    
    def feature_pack(self, pack_id: str, featured: bool = True) -> bool:
        """
        Feature or unfeature a pack
        
        Args:
            pack_id: Pack ID
            featured: Whether to feature the pack
            
        Returns:
            True if updated successfully
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            pack.featured = "true" if featured else "false"
            pack.save()
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating pack featured status: {e}")
            return False
    
    def rate_pack(self, pack_id: str, rating: int) -> bool:
        """
        Rate a pack
        
        Args:
            pack_id: Pack ID
            rating: Rating (1-5)
            
        Returns:
            True if rated successfully
        """
        try:
            if rating < 1 or rating > 5:
                return False
            
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return False
            
            pack.update_rating(rating)
            return True
            
        except Exception as e:
            print(f"❌ Error rating pack: {e}")
            return False
    
    def purchase_pack(self, pack_id: str) -> Optional[List[Any]]:
        """
        Purchase a pack and generate cards
        
        Args:
            pack_id: Pack ID
            
        Returns:
            List of generated cards or None
        """
        try:
            pack = CreatorPack.get_by_id(pack_id)
            if not pack or pack.status != "active":
                return None
            
            # Increment purchase count
            pack.increment_purchases()
            
            # Generate cards from pack artists
            cards = []
            artists = pack.get_artists()
            
            for artist in artists:
                card = create_from_artist(artist, source="creator_pack")
                if card:
                    cards.append(card)
            
            return cards
            
        except Exception as e:
            print(f"❌ Error purchasing pack: {e}")
            return None
    
    def get_pack_statistics(self) -> Dict[str, Any]:
        """
        Get overall creator pack statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            all_packs = CreatorPack.all()
            
            if not all_packs:
                return {
                    "total_packs": 0,
                    "active_packs": 0,
                    "total_purchases": 0,
                    "average_price": 0,
                    "by_genre": {},
                    "by_branding": {}
                }
            
            active_packs = [p for p in all_packs if p.status == "active"]
            total_purchases = sum(p.purchase_count for p in all_packs)
            average_price = sum(p.price_cents for p in all_packs) / len(all_packs)
            
            # Count by genre
            genre_counts = {}
            for pack in all_packs:
                genre = pack.genre or "unknown"
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Count by branding
            branding_counts = {}
            for pack in all_packs:
                branding = pack.branding or "default"
                branding_counts[branding] = branding_counts.get(branding, 0) + 1
            
            return {
                "total_packs": len(all_packs),
                "active_packs": len(active_packs),
                "total_purchases": total_purchases,
                "average_price": int(average_price),
                "by_genre": genre_counts,
                "by_branding": branding_counts
            }
            
        except Exception as e:
            print(f"❌ Error getting pack statistics: {e}")
            return {}


# Global service instance
creator_service = CreatorService()


# Convenience functions for backward compatibility
async def create_creator_pack(user_id: int, name: str, artist_names: List[str], 
                            genre: str) -> Optional[CreatorPack]:
    """Create a creator pack"""
    return await creator_service.create_creator_pack(user_id, name, artist_names, genre)


# Example usage
async def example_usage():
    """Example of creator service usage"""
    
    # Create a new creator pack
    pack = await creator_service.create_creator_pack(
        user_id=123456789,
        name="Rock Legends Pack",
        artist_names=["Queen", "Led Zeppelin", "The Beatles"],
        genre="Rock",
        description="The ultimate rock collection",
        price_cents=1499
    )
    
    if pack:
        print(f"✅ Created pack: {pack.name}")
        print(f"   Artists: {len(pack.artist_ids)}")
        print(f"   Price: ${pack.price_cents / 100:.2f}")
    
    # Get user's packs
    user_packs = creator_service.get_user_packs(123456789)
    print(f"✅ User has {len(user_packs)} packs")
    
    # Get featured packs
    featured = creator_service.get_featured_packs(5)
    print(f"✅ Found {len(featured)} featured packs")
    
    # Search packs
    rock_packs = creator_service.search_packs("rock")
    print(f"✅ Found {len(rock_packs)} rock packs")


if __name__ == "__main__":
    asyncio.run(example_usage())
