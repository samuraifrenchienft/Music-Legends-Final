# services/creator_preview.py
"""
Creator Pack Preview System
Build comprehensive previews for admin review
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from models.creator_pack import CreatorPack
from models.artist import Artist
from services.tier_mapper import tier_from_youtube, get_tier_metadata
from services.youtube_client import YouTubeClient

class CreatorPreviewBuilder:
    """Service for building creator pack previews"""
    
    def __init__(self):
        self.youtube_client = YouTubeClient()
    
    def build_preview(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """
        Build comprehensive preview for a creator pack
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Preview data dict or None if not found
        """
        try:
            # Get the pack
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                return None
            
            # Get artists
            artists = Artist.where_in("id", pack.artist_ids)
            
            # Build artist roster with details
            roster = []
            tier_distribution = {
                "legendary": 0,
                "platinum": 0,
                "gold": 0,
                "silver": 0,
                "bronze": 0,
                "community": 0
            }
            
            genre_distribution = {}
            total_popularity = 0
            total_subscribers = 0
            total_videos = 0
            total_views = 0
            
            for artist in artists:
                # Estimate tier from YouTube data
                estimated_tier = tier_from_youtube(artist.popularity or 0, 0)
                
                # Get tier metadata
                tier_meta = get_tier_metadata(estimated_tier)
                
                # Build artist entry
                artist_entry = {
                    "id": str(artist.id),
                    "name": artist.name,
                    "genre": artist.genre or "Unknown",
                    "image": artist.image_url,
                    "estimated_tier": estimated_tier,
                    "tier_emoji": tier_meta.get("emoji", "❓"),
                    "tier_color": tier_meta.get("color", "#808080"),
                    "popularity": artist.popularity or 0,
                    "subscribers": artist.subscribers or 0,
                    "videos": artist.video_count or 0,
                    "views": artist.view_count or 0,
                    "channel_id": artist.channel_id,
                    "description": artist.description or ""
                }
                
                roster.append(artist_entry)
                
                # Update statistics
                tier_distribution[estimated_tier] += 1
                total_popularity += artist.popularity or 0
                total_subscribers += artist.subscribers or 0
                total_videos += artist.video_count or 0
                total_views += artist.view_count or 0
                
                # Track genre distribution
                genre = artist.genre or "Unknown"
                genre_distribution[genre] = genre_distribution.get(genre, 0) + 1
            
            # Calculate pack statistics
            avg_popularity = total_popularity / len(artists) if artists else 0
            avg_subscribers = total_subscribers / len(artists) if artists else 0
            avg_videos = total_videos / len(artists) if artists else 0
            avg_views = total_views / len(artists) if artists else 0
            
            # Determine pack quality score
            quality_score = self._calculate_quality_score(
                tier_distribution, 
                len(artists),
                avg_popularity
            )
            
            # Get YouTube channel images if available
            youtube_images = self._get_youtube_images(artists)
            
            # Build preview
            preview = {
                # Basic pack info
                "pack_id": str(pack.id),
                "name": pack.name,
                "genre": pack.genre,
                "status": pack.status,
                "payment_status": pack.payment_status,
                "price_cents": pack.price_cents,
                "price_dollars": pack.price_cents / 100,
                
                # Owner info
                "owner_id": pack.owner_id,
                "created_at": pack.created_at.isoformat() if pack.created_at else None,
                "reviewed_at": pack.reviewed_at.isoformat() if pack.reviewed_at else None,
                
                # Artist roster
                "artists": roster,
                "artist_count": len(artists),
                
                # Statistics
                "tier_distribution": tier_distribution,
                "genre_distribution": genre_distribution,
                "avg_popularity": round(avg_popularity, 2),
                "avg_subscribers": round(avg_subscribers),
                "avg_videos": round(avg_videos),
                "avg_views": round(avg_views),
                "total_subscribers": total_subscribers,
                "total_views": total_views,
                
                # Quality assessment
                "quality_score": quality_score,
                "quality_rating": self._get_quality_rating(quality_score),
                
                # YouTube data
                "youtube_images": youtube_images,
                "has_youtube_data": any(artist.channel_id for artist in artists),
                
                # Review info
                "reviewed_by": pack.reviewed_by,
                "notes": pack.notes,
                "rejection_reason": pack.rejection_reason,
                
                # Metadata
                "preview_generated_at": datetime.utcnow().isoformat()
            }
            
            return preview
            
        except Exception as e:
            print(f"❌ Error building preview for pack {pack_id}: {e}")
            return None
    
    def _calculate_quality_score(self, tier_distribution: Dict[str, int], artist_count: int, avg_popularity: float) -> float:
        """
        Calculate quality score for the pack
        
        Args:
            tier_distribution: Distribution of tiers
            artist_count: Number of artists
            avg_popularity: Average popularity score
            
        Returns:
            Quality score (0-100)
        """
        try:
            # Tier weights
            tier_weights = {
                "legendary": 10,
                "platinum": 8,
                "gold": 6,
                "silver": 4,
                "bronze": 2,
                "community": 1
            }
            
            # Calculate weighted tier score
            tier_score = 0
            total_artists = sum(tier_distribution.values())
            
            if total_artists > 0:
                for tier, count in tier_distribution.items():
                    weight = tier_weights.get(tier, 0)
                    tier_score += (count / total_artists) * weight
            
            # Normalize tier score (0-50 points)
            tier_score_normalized = min(tier_score, 50)
            
            # Artist count score (0-20 points)
            # Optimal range: 5-15 artists
            if 5 <= artist_count <= 15:
                count_score = 20
            elif 3 <= artist_count <= 20:
                count_score = 15
            elif 1 <= artist_count <= 25:
                count_score = 10
            else:
                count_score = 0
            
            # Popularity score (0-30 points)
            # Scale popularity to 0-30
            popularity_score = min(avg_popularity / 100 * 30, 30)
            
            # Total score
            total_score = tier_score_normalized + count_score + popularity_score
            
            return round(total_score, 2)
            
        except Exception as e:
            print(f"❌ Error calculating quality score: {e}")
            return 0.0
    
    def _get_quality_rating(self, score: float) -> str:
        """Get quality rating based on score"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        elif score >= 20:
            return "Poor"
        else:
            return "Very Poor"
    
    def _get_youtube_images(self, artists: List[Artist]) -> Dict[str, str]:
        """
        Get YouTube channel images for artists
        
        Args:
            artists: List of Artist objects
            
        Returns:
            Dict mapping artist ID to image URL
        """
        images = {}
        
        for artist in artists:
            if artist.image_url:
                images[str(artist.id)] = artist.image_url
            elif artist.channel_id:
                # Could fetch from YouTube API here if needed
                images[str(artist.id)] = f"https://img.youtube.com/vi/{artist.channel_id}/maxresdefault.jpg"
            else:
                images[str(artist.id)] = "https://via.placeholder.com/300x300/cccccc/000000?text=No+Image"
        
        return images
    
    def build_comparison_preview(self, pack_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        Build comparison preview for multiple packs
        
        Args:
            pack_ids: List of pack IDs
            
        Returns:
            Comparison preview dict
        """
        try:
            previews = []
            
            for pack_id in pack_ids:
                preview = self.build_preview(pack_id)
                if preview:
                    previews.append(preview)
            
            if not previews:
                return None
            
            # Calculate comparison statistics
            comparison = {
                "packs": previews,
                "pack_count": len(previews),
                "comparison_generated_at": datetime.utcnow().isoformat()
            }
            
            # Add comparison metrics
            comparison["avg_quality_score"] = sum(p["quality_score"] for p in previews) / len(previews)
            comparison["avg_price"] = sum(p["price_cents"] for p in previews) / len(previews)
            comparison["total_artists"] = sum(p["artist_count"] for p in previews)
            
            # Find best pack by quality
            comparison["best_quality_pack"] = max(previews, key=lambda p: p["quality_score"])
            
            # Find most expensive pack
            comparison["most_expensive_pack"] = max(previews, key=lambda p: p["price_cents"])
            
            return comparison
            
        except Exception as e:
            print(f"❌ Error building comparison preview: {e}")
            return None
    
    def get_preview_summary(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """
        Get quick summary of pack preview
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Summary dict or None
        """
        try:
            preview = self.build_preview(pack_id)
            if not preview:
                return None
            
            # Extract key information for summary
            summary = {
                "pack_id": preview["pack_id"],
                "name": preview["name"],
                "genre": preview["genre"],
                "status": preview["status"],
                "payment_status": preview["payment_status"],
                "price_dollars": preview["price_dollars"],
                "artist_count": preview["artist_count"],
                "quality_score": preview["quality_score"],
                "quality_rating": preview["quality_rating"],
                "top_tiers": self._get_top_tiers(preview["tier_distribution"]),
                "has_youtube_data": preview["has_youtube_data"],
                "preview_generated_at": preview["preview_generated_at"]
            }
            
            return summary
            
        except Exception as e:
            print(f"❌ Error getting preview summary: {e}")
            return None
    
    def _get_top_tiers(self, tier_distribution: Dict[str, int]) -> List[str]:
        """Get top tiers from distribution"""
        tiers = []
        
        tier_order = ["legendary", "platinum", "gold", "silver", "bronze", "community"]
        
        for tier in tier_order:
            count = tier_distribution.get(tier, 0)
            if count > 0:
                tier_emoji = {
                    "legendary": "🏆",
                    "platinum": "💎",
                    "gold": "🥇",
                    "silver": "🥈",
                    "bronze": "🥉",
                    "community": "👥"
                }.get(tier, "❓")
                
                tiers.append(f"{tier_emoji} {tier.title()}: {count}")
        
        return tiers


# Global preview builder instance
creator_preview = CreatorPreviewBuilder()


# Convenience function for backward compatibility
def build_preview(pack_id: str) -> Optional[Dict[str, Any]]:
    """Build preview (simplified version)"""
    return creator_preview.build_preview(pack_id)


# Example usage
def example_usage():
    """Example of preview builder usage"""
    
    # Build preview for a pack
    preview = creator_preview.build_preview("pack_123")
    
    if preview:
        print(f"✅ Preview built for: {preview['name']}")
        print(f"   Genre: {preview['genre']}")
        print(f"   Artists: {preview['artist_count']}")
        print(f"   Quality Score: {preview['quality_score']}")
        print(f"   Quality Rating: {preview['quality_rating']}")
        
        # Show tier distribution
        tiers = preview['tier_distribution']
        print(f"   Tiers: {tiers}")
        
        # Show top artists
        top_artists = sorted(preview['artists'], key=lambda a: a['popularity'], reverse=True)[:3]
        print(f"   Top Artists:")
        for artist in top_artists:
            print(f"      • {artist['name']} ({artist['estimated_tier']})")
    else:
        print("❌ Failed to build preview")


if __name__ == "__main__":
    example_usage()
