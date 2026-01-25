"""
Hybrid Pack Generation System
Implements professional TCG pack design with balanced stat distribution
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from card_stats import (
    CardStats, CardFactory, RarityAssigner, Rarity, 
    PACK_DISTRIBUTION, RARITY_DISTRIBUTION_PER_PACK
)

@dataclass
class PackGenerationConfig:
    """Configuration for pack generation"""
    total_cards: int = 5
    hero_cards: int = 1
    artist_top_cards: int = 1
    related_cards: int = 2
    wildcard_cards: int = 1
    
    # Stat balancing constraints
    min_power_per_pack: int = 15
    max_power_per_pack: int = 35
    ensure_rarity_variety: bool = True
    
    # Theme consistency
    artist_consistency_weight: float = 0.7  # 70% same artist, 30% related

class VideoSourceManager:
    """Manages video sources for pack generation"""
    
    def __init__(self, youtube_api):
        self.youtube_api = youtube_api
    
    async def get_artist_top_videos(self, channel_id: str, exclude_video_id: str, max_results: int = 20) -> List[Dict]:
        """Get top videos from the same artist/channel"""
        try:
            # Get videos from same channel sorted by views
            videos = await self.youtube_api.get_channel_videos(
                channel_id=channel_id,
                exclude_ids=[exclude_video_id],
                max_results=max_results
            )
            
            # Sort by views (descending) and return top ones
            sorted_videos = sorted(videos, key=lambda x: x.get("views", 0), reverse=True)
            return sorted_videos[:max_results]
            
        except Exception as e:
            print(f"Error getting artist top videos: {e}")
            return []
    
    async def get_related_videos(self, video_id: str, max_results: int = 30) -> List[Dict]:
        """Get related videos using YouTube search/recommendations"""
        try:
            # Use YouTube search to find related videos
            # This could be enhanced with YouTube's recommendation API
            related_videos = await self.youtube_api.get_channel_videos(
                channel_id="",  # Empty to search across all channels
                exclude_ids=[video_id],
                max_results=max_results
            )
            
            # Filter for variety and balance
            filtered_videos = self._filter_for_balance(related_videos)
            return filtered_videos
            
        except Exception as e:
            print(f"Error getting related videos: {e}")
            return []
    
    def _filter_for_balance(self, videos: List[Dict]) -> List[Dict]:
        """Filter videos to ensure balanced stat distribution"""
        if not videos:
            return []
        
        # Sort by views to get variety
        sorted_videos = sorted(videos, key=lambda x: x.get("views", 0))
        
        # Take videos from different view ranges for balance
        total = len(sorted_videos)
        if total <= 10:
            return sorted_videos
        
        # Sample from different quartiles
        quartile_size = total // 4
        selected = []
        
        for i in range(0, total, quartile_size):
            if i + quartile_size <= total:
                selected.extend(sorted_videos[i:i + quartile_size])
            else:
                selected.extend(sorted_videos[i:])
        
        return selected[:20]  # Limit to 20 for processing

class HybridPackGenerator:
    """Generates balanced packs using hybrid model"""
    
    def __init__(self, youtube_api):
        self.video_manager = VideoSourceManager(youtube_api)
        self.config = PackGenerationConfig()
    
    async def generate_pack(self, hero_video_url: str, user_id: int) -> Dict:
        """Generate a complete pack using hybrid model"""
        
        print(f"🎬 Generating hybrid pack from: {hero_video_url}")
        
        # Step 1: Parse and validate hero video
        hero_video_id = self._parse_video_id(hero_video_url)
        if not hero_video_id:
            return {"success": False, "error": "Invalid YouTube URL"}
        
        # Step 2: Get hero video data
        hero_video_data = await self._get_video_data(hero_video_id)
        if not hero_video_data:
            return {"success": False, "error": "Could not fetch hero video data"}
        
        # Step 3: Create hero card
        hero_card = CardFactory.create_card_from_video(hero_video_data, is_hero=True)
        print(f"🌟 Hero card: {hero_card.name} ({hero_card.rarity.value}) - Power: {hero_card.power}")
        
        # Step 4: Get video sources for secondary cards
        artist_videos = await self.video_manager.get_artist_top_videos(
            hero_video_data.get("channel_id", ""),
            hero_video_id
        )
        
        related_videos = await self.video_manager.get_related_videos(hero_video_id)
        
        # Step 5: Generate secondary cards with balance constraints
        secondary_cards = await self._generate_secondary_cards(
            hero_card, artist_videos, related_videos
        )
        
        # Step 6: Validate pack balance
        pack_cards = [hero_card] + secondary_cards
        if not self._validate_pack_balance(pack_cards):
            # If unbalanced, regenerate some cards
            secondary_cards = await self._rebalance_pack(hero_card, artist_videos, related_videos)
            pack_cards = [hero_card] + secondary_cards
        
        # Step 7: Create pack data structure
        pack_data = self._create_pack_data(pack_cards, user_id, hero_video_data)
        
        print(f"✅ Pack generated: {len(pack_cards)} cards, Total Power: {sum(c.power for c in pack_cards)}")
        
        return {
            "success": True,
            "pack_data": pack_data,
            "cards": pack_cards,
            "hero_card": hero_card
        }
    
    def _parse_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        import re
        
        patterns = [
            r'(?:youtube\.com/watch\?v=)([^&]+)',
            r'(?:youtu\.be/)([^?]+)',
            r'(?:youtube\.com/embed/)([^?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _get_video_data(self, video_id: str) -> Optional[Dict]:
        """Get video data from YouTube API"""
        try:
            return await self.video_manager.youtube_api.get_video_details(video_id)
        except Exception as e:
            print(f"Error getting video data: {e}")
            return None
    
    async def _generate_secondary_cards(self, hero_card: CardStats, artist_videos: List[Dict], related_videos: List[Dict]) -> List[CardStats]:
        """Generate secondary cards with balanced distribution"""
        
        secondary_cards = []
        
        # 1 Artist Top Card (high power, same artist)
        if artist_videos:
            artist_card_data = random.choice(artist_videos[:5])  # Top 5 videos
            artist_card = CardFactory.create_balanced_secondary_card(artist_card_data)
            secondary_cards.append(artist_card)
            print(f"🎵 Artist card: {artist_card.name} ({artist_card.rarity.value})")
        
        # 2 Related Cards (mid-power, variety)
        for i in range(self.config.related_cards):
            if related_videos:
                related_card_data = random.choice(related_videos)
                related_card = CardFactory.create_balanced_secondary_card(related_card_data)
                secondary_cards.append(related_card)
                print(f"🔗 Related card {i+1}: {related_card.name} ({related_card.rarity.value})")
        
        # 1 Wildcard (random but balanced)
        all_videos = artist_videos + related_videos
        if all_videos:
            wildcard_data = random.choice(all_videos)
            # Wildcard gets weighted rarity for excitement
            wildcard_rarity = self._get_wildcard_rarity()
            wildcard_card = CardFactory.create_balanced_secondary_card(wildcard_data, wildcard_rarity)
            secondary_cards.append(wildcard_card)
            print(f"🎲 Wildcard: {wildcard_card.name} ({wildcard_card.rarity.value})")
        
        return secondary_cards
    
    def _get_wildcard_rarity(self) -> Rarity:
        """Get weighted rarity for wildcard slot"""
        # Higher chance for better rarity in wildcard slot
        weights = {
            Rarity.COMMON: 20,
            Rarity.UNCOMMON: 25,
            Rarity.RARE: 30,
            Rarity.EPIC: 20,
            Rarity.LEGENDARY: 5
        }
        
        total_weight = sum(weights.values())
        rand = random.random() * total_weight
        
        current_weight = 0
        for rarity, weight in weights.items():
            current_weight += weight
            if rand <= current_weight:
                return rarity
        
        return Rarity.COMMON
    
    def _validate_pack_balance(self, cards: List[CardStats]) -> bool:
        """Validate if pack meets balance constraints"""
        
        total_power = sum(card.power for card in cards)
        
        # Check power range
        if total_power < self.config.min_power_per_pack or total_power > self.config.max_power_per_pack:
            return False
        
        # Check rarity variety
        if self.config.ensure_rarity_variety:
            rarities = [card.rarity for card in cards]
            unique_rarities = set(rarities)
            if len(unique_rarities) < 2:  # Need at least 2 different rarities
                return False
        
        return True
    
    async def _rebalance_pack(self, hero_card: CardStats, artist_videos: List[Dict], related_videos: List[Dict]) -> List[CardStats]:
        """Rebalance pack by regenerating some cards"""
        
        print("🔄 Rebalancing pack...")
        
        secondary_cards = []
        attempts = 0
        max_attempts = 5
        
        while attempts < max_attempts:
            # Generate new secondary cards
            new_cards = await self._generate_secondary_cards(hero_card, artist_videos, related_videos)
            pack_cards = [hero_card] + new_cards
            
            if self._validate_pack_balance(pack_cards):
                return new_cards
            
            attempts += 1
        
        # If still unbalanced after max attempts, force balance
        print("⚠️ Forcing pack balance...")
        return self._force_balanced_cards(hero_card, artist_videos, related_videos)
    
    def _force_balanced_cards(self, hero_card: CardStats, artist_videos: List[Dict], related_videos: List[Dict]) -> List[CardStats]:
        """Force create balanced cards when rebalancing fails"""
        
        secondary_cards = []
        all_videos = artist_videos + related_videos
        
        # Target total power
        target_power = (self.config.min_power_per_pack + self.config.max_power_per_pack) // 2
        remaining_power = target_power - hero_card.power
        
        # Distribute remaining power among secondary cards
        cards_needed = self.config.total_cards - 1
        avg_power_per_card = max(1, remaining_power // cards_needed)
        
        for i in range(cards_needed):
            if all_videos:
                video_data = random.choice(all_videos)
                card = CardFactory.create_balanced_secondary_card(video_data)
                
                # Adjust power to meet target
                if card.power > avg_power_per_card + 3:
                    # Too powerful, downgrade rarity
                    if card.rarity == Rarity.LEGENDARY:
                        card.rarity = Rarity.EPIC
                    elif card.rarity == Rarity.EPIC:
                        card.rarity = Rarity.RARE
                    elif card.rarity == Rarity.RARE:
                        card.rarity = Rarity.UNCOMMON
                
                secondary_cards.append(card)
        
        return secondary_cards
    
    def _create_pack_data(self, cards: List[CardStats], user_id: int, hero_video_data: Dict) -> Dict:
        """Create pack data structure for database storage"""
        
        import uuid
        import json
        
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        
        # Convert cards to serializable format
        cards_data = []
        for card in cards:
            card_dict = {
                "name": card.name,
                "artist": card.artist,
                "power": card.power,
                "cost": card.cost,
                "rarity": card.rarity.value,
                "abilities": card.abilities,
                "views": card.views,
                "likes": card.likes,
                "video_id": card.video_id,
                "card_type": card.card_type.value,
                "engagement_ratio": card.engagement_ratio
            }
            cards_data.append(card_dict)
        
        return {
            "pack_id": pack_id,
            "creator_id": user_id,
            "name": f"{hero_video_data.get('title', 'Unknown')} Pack",
            "description": f"Featured: {hero_video_data.get('title', 'Unknown')} + 4 balanced cards",
            "cards_data": json.dumps(cards_data),
            "total_cards": len(cards),
            "hero_video_id": hero_video_data.get("video_id"),
            "hero_video_title": hero_video_data.get("title"),
            "hero_video_artist": hero_video_data.get("artist"),
            "pack_power_total": sum(card.power for card in cards),
            "pack_rarity_distribution": self._get_rarity_distribution(cards),
            "price": 6.99,  # Standard price
            "status": "ready"
        }
    
    def _get_rarity_distribution(self, cards: List[CardStats]) -> Dict:
        """Get rarity distribution for the pack"""
        distribution = {}
        for card in cards:
            rarity = card.rarity.value
            distribution[rarity] = distribution.get(rarity, 0) + 1
        return distribution

# Pack validation and quality control
class PackQualityController:
    """Ensures pack quality and balance"""
    
    @staticmethod
    def validate_pack_quality(pack_data: Dict) -> Tuple[bool, List[str]]:
        """Validate pack quality and return issues"""
        issues = []
        
        cards = pack_data.get("cards", [])
        if len(cards) != 5:
            issues.append(f"Pack has {len(cards)} cards, expected 5")
        
        # Check power balance
        total_power = sum(card.get("power", 0) for card in cards)
        if total_power < 15 or total_power > 35:
            issues.append(f"Pack power {total_power} outside balanced range (15-35)")
        
        # Check rarity distribution
        rarities = [card.get("rarity", "common") for card in cards]
        unique_rarities = set(rarities)
        if len(unique_rarities) < 2:
            issues.append("Pack lacks rarity variety")
        
        # Check for duplicate cards
        card_names = [card.get("name", "") for card in cards]
        if len(card_names) != len(set(card_names)):
            issues.append("Pack contains duplicate cards")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def get_pack_quality_score(pack_data: Dict) -> float:
        """Calculate quality score for a pack (0.0 to 1.0)"""
        score = 0.0
        
        cards = pack_data.get("cards", [])
        if not cards:
            return 0.0
        
        # Power balance score (40%)
        total_power = sum(card.get("power", 0) for card in cards)
        if 15 <= total_power <= 35:
            score += 0.4
        else:
            # Partial credit for being close
            distance = min(abs(total_power - 15), abs(total_power - 35))
            score += max(0, 0.4 - (distance * 0.02))
        
        # Rarity variety score (30%)
        rarities = [card.get("rarity", "common") for card in cards]
        unique_rarities = len(set(rarities))
        score += (unique_rarities / 5) * 0.3
        
        # Ability variety score (20%)
        abilities = [len(card.get("abilities", [])) for card in cards]
        total_abilities = sum(abilities)
        score += min(total_abilities / 10, 1.0) * 0.2
        
        # No duplicates score (10%)
        card_names = [card.get("name", "") for card in cards]
        if len(card_names) == len(set(card_names)):
            score += 0.1
        
        return min(score, 1.0)
