"""
Season 1 Supply System (Locked)

Core Philosophy:
- Feel scarce without choking the economy
- Reward early adopters permanently  
- Allow growth without reprinting value
- Survive years of trading data

This is economic design law - not implementation detail.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SeasonState(Enum):
    """Season lifecycle states"""
    PLANNING = "planning"
    ACTIVE = "active"
    ENDED = "ended"
    LEGACY = "legacy"

class SerialValueTier(Enum):
    """Serial value psychology tiers"""
    ULTRA_PREMIUM = "ultra_premium"  # #1-#5
    HIGH_VALUE = "high_value"        # #6-#25
    COLLECTIBLE = "collectible"       # #26-#100
    TRADEABLE = "tradeable"          # #101+

class SeasonSupplySystem:
    """
    Canonical Season 1 supply management.
    Enforces global caps and scarcity rules.
    """
    
    def __init__(self, season_number: int = 1):
        self.season_number = season_number
        self.state = SeasonState.ACTIVE
        self.supply_file = f"season_{season_number}_supply.json"
        self.artist_limits_file = f"season_{season_number}_artist_limits.json"
        
        # Season 1 locked supply targets
        self.TOTAL_SUPPLY_TARGET = 250_000
        self.RARITY_DISTRIBUTION = {
            "community": {"percentage": 0.72, "max_cards": 180_000},
            "gold": {"percentage": 0.20, "max_cards": 50_000},
            "platinum": {"percentage": 0.06, "max_cards": 15_000},
            "legendary": {"percentage": 0.02, "max_cards": 5_000}
        }
        
        # Legendary structure (CRITICAL)
        self.LEGENDARY_MAX_PER_ARTIST = 100
        self.LEGENDARY_ABSOLUTE_MAX = 5_000
        
        # Platinum structure
        self.PLATINUM_MAX_PER_ARTIST = 300
        
        # Serial value tiers
        self.SERIAL_VALUE_TIERS = {
            SerialValueTier.ULTRA_PREMIUM: (1, 5),
            SerialValueTier.HIGH_VALUE: (6, 25),
            SerialValueTier.COLLECTIBLE: (26, 100),
            SerialValueTier.TRADEABLE: (101, float('inf'))
        }
        
        # Pack contribution to supply
        self.PACK_MIX = {
            "drops": 0.40,
            "silver_packs": 0.30,
            "black_packs": 0.20,
            "creator_packs": 0.10
        }
        
        # Load current supply state
        self.load_supply_state()
    
    def load_supply_state(self):
        """Load current supply state from file"""
        if os.path.exists(self.supply_file):
            try:
                with open(self.supply_file, 'r') as f:
                    data = json.load(f)
                    self.current_mints = data.get("current_mints", {})
                    self.artist_mints = data.get("artist_mints", {})
                    self.pack_contributions = data.get("pack_contributions", {})
                    self.season_start = data.get("season_start", datetime.utcnow().isoformat())
                    self.last_updated = data.get("last_updated")
            except Exception as e:
                logger.error(f"Error loading supply state: {e}")
                self._initialize_supply_state()
        else:
            self._initialize_supply_state()
    
    def _initialize_supply_state(self):
        """Initialize fresh supply state"""
        self.current_mints = {
            "community": 0,
            "gold": 0,
            "platinum": 0,
            "legendary": 0
        }
        self.artist_mints = {}  # artist_id -> {tier: count}
        self.pack_contributions = {
            "drops": 0,
            "silver_packs": 0,
            "black_packs": 0,
            "creator_packs": 0
        }
        self.season_start = datetime.utcnow().isoformat()
        self.last_updated = None
        self.save_supply_state()
    
    def save_supply_state(self):
        """Save supply state to file"""
        try:
            data = {
                "season_number": self.season_number,
                "state": self.state.value,
                "total_supply_target": self.TOTAL_SUPPLY_TARGET,
                "current_mints": self.current_mints,
                "artist_mints": self.artist_mints,
                "pack_contributions": self.pack_contributions,
                "season_start": self.season_start,
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(self.supply_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving supply state: {e}")
    
    def can_mint_card(self, tier: str, artist_id: str, pack_source: str = "black_packs") -> Dict[str, Any]:
        """
        Check if a card can be minted according to Season 1 supply rules.
        
        Args:
            tier: Card tier to mint
            artist_id: Artist ID
            pack_source: Source of the mint (drops, silver_packs, etc.)
            
        Returns:
            Dictionary with can_mint status and reason
        """
        # Check season state
        if self.state != SeasonState.ACTIVE:
            return {
                "can_mint": False,
                "reason": f"Season {self.season_number} is {self.state.value}",
                "error_code": "SEASON_INACTIVE"
            }
        
        # Check global tier caps
        tier_info = self.RARITY_DISTRIBUTION.get(tier)
        if not tier_info:
            return {
                "can_mint": False,
                "reason": f"Unknown tier: {tier}",
                "error_code": "UNKNOWN_TIER"
            }
        
        current_mints = self.current_mints.get(tier, 0)
        max_cards = tier_info["max_cards"]
        
        if current_mints >= max_cards:
            return {
                "can_mint": False,
                "reason": f"Global {tier} cap reached: {current_mints}/{max_cards}",
                "error_code": "GLOBAL_CAP_REACHED"
            }
        
        # Check artist-specific limits for high tiers
        if tier in ["platinum", "legendary"]:
            artist_limit_error = self._check_artist_limit(tier, artist_id)
            if artist_limit_error:
                return artist_limit_error
        
        # Check pack contribution balance
        pack_balance_error = self._check_pack_balance(pack_source)
        if pack_balance_error:
            return pack_balance_error
        
        return {
            "can_mint": True,
            "reason": "Mint approved",
            "remaining_global": max_cards - current_mints,
            "scarcity_level": self._get_scarcity_level(tier, current_mints, max_cards)
        }
    
    def _check_artist_limit(self, tier: str, artist_id: str) -> Optional[Dict[str, Any]]:
        """Check artist-specific mint limits"""
        artist_data = self.artist_mints.get(artist_id, {})
        current_artist_mints = artist_data.get(tier, 0)
        
        if tier == "legendary":
            max_per_artist = self.LEGENDARY_MAX_PER_ARTIST
            if current_artist_mints >= max_per_artist:
                return {
                    "can_mint": False,
                    "reason": f"Artist {artist_id} legendary cap reached: {current_artist_mints}/{max_per_artist}",
                    "error_code": "ARTIST_LEGENDARY_CAP"
                }
        elif tier == "platinum":
            max_per_artist = self.PLATINUM_MAX_PER_ARTIST
            if current_artist_mints >= max_per_artist:
                return {
                    "can_mint": False,
                    "reason": f"Artist {artist_id} platinum cap reached: {current_artist_mints}/{max_per_artist}",
                    "error_code": "ARTIST_PLATINUM_CAP"
                }
        
        return None
    
    def _check_pack_balance(self, pack_source: str) -> Optional[Dict[str, Any]]:
        """Check if pack source is within contribution limits"""
        target_percentage = self.PACK_MIX.get(pack_source, 0)
        if target_percentage == 0:
            return {
                "can_mint": False,
                "reason": f"Unknown pack source: {pack_source}",
                "error_code": "UNKNOWN_PACK_SOURCE"
            }
        
        # For now, allow any pack source (could implement stricter balance later)
        return None
    
    def _get_scarcity_level(self, tier: str, current_mints: int, max_cards: int) -> str:
        """Get scarcity level for UI display"""
        percentage_filled = current_mints / max_cards
        
        if percentage_filled >= 0.9:
            return "ultra_rare"
        elif percentage_filled >= 0.7:
            return "very_rare"
        elif percentage_filled >= 0.4:
            return "rare"
        else:
            return "available"
    
    def mint_card(self, tier: str, artist_id: str, pack_source: str = "black_packs") -> Dict[str, Any]:
        """
        Record a card mint and update supply state.
        
        Args:
            tier: Card tier minted
            artist_id: Artist ID
            pack_source: Source of the mint
            
        Returns:
            Dictionary with mint result and new supply info
        """
        # Check if can mint
        can_mint_result = self.can_mint_card(tier, artist_id, pack_source)
        if not can_mint_result["can_mint"]:
            return can_mint_result
        
        # Update global mints
        self.current_mints[tier] = self.current_mints.get(tier, 0) + 1
        
        # Update artist mints
        if artist_id not in self.artist_mints:
            self.artist_mints[artist_id] = {}
        self.artist_mints[artist_id][tier] = self.artist_mints[artist_id].get(tier, 0) + 1
        
        # Update pack contributions
        self.pack_contributions[pack_source] = self.pack_contributions.get(pack_source, 0) + 1
        
        # Save state
        self.save_supply_state()
        
        # Get serial number for this mint
        serial_number = self.current_mints[tier]
        
        return {
            "success": True,
            "tier": tier,
            "artist_id": artist_id,
            "serial_number": serial_number,
            "pack_source": pack_source,
            "global_remaining": self.RARITY_DISTRIBUTION[tier]["max_cards"] - self.current_mints[tier],
            "artist_remaining": self._get_artist_remaining(tier, artist_id),
            "scarcity_level": self._get_scarcity_level(tier, self.current_mints[tier], self.RARITY_DISTRIBUTION[tier]["max_cards"])
        }
    
    def _get_artist_remaining(self, tier: str, artist_id: str) -> int:
        """Get remaining mints for artist in specific tier"""
        artist_data = self.artist_mints.get(artist_id, {})
        current_mints = artist_data.get(tier, 0)
        
        if tier == "legendary":
            return self.LEGENDARY_MAX_PER_ARTIST - current_mints
        elif tier == "platinum":
            return self.PLATINUM_MAX_PER_ARTIST - current_mints
        else:
            return float('inf')  # No limit for lower tiers
    
    def get_serial_value_tier(self, serial_number: int) -> SerialValueTier:
        """Get serial value tier based on serial number"""
        for tier, (min_serial, max_serial) in self.SERIAL_VALUE_TIERS.items():
            if min_serial <= serial_number <= max_serial:
                return tier
        return SerialValueTier.TRADEABLE
    
    def get_supply_status(self) -> Dict[str, Any]:
        """Get comprehensive supply status"""
        total_mints = sum(self.current_mints.values())
        
        tier_status = {}
        for tier, info in self.RARITY_DISTRIBUTION.items():
            current = self.current_mints.get(tier, 0)
            max_cards = info["max_cards"]
            percentage = (current / max_cards) * 100 if max_cards > 0 else 0
            
            tier_status[tier] = {
                "current": current,
                "max": max_cards,
                "percentage": percentage,
                "remaining": max_cards - current,
                "scarcity_level": self._get_scarcity_level(tier, current, max_cards)
            }
        
        return {
            "season_number": self.season_number,
            "state": self.state.value,
            "total_supply_target": self.TOTAL_SUPPLY_TARGET,
            "total_mints": total_mints,
            "percentage_complete": (total_mints / self.TOTAL_SUPPLY_TARGET) * 100,
            "tier_status": tier_status,
            "pack_contributions": self.pack_contributions,
            "unique_artists": len(self.artist_mints),
            "season_start": self.season_start,
            "last_updated": self.last_updated
        }
    
    def get_artist_status(self, artist_id: str) -> Dict[str, Any]:
        """Get mint status for specific artist"""
        artist_data = self.artist_mints.get(artist_id, {})
        
        status = {
            "artist_id": artist_id,
            "total_mints": sum(artist_data.values()),
            "by_tier": {}
        }
        
        for tier in ["community", "gold", "platinum", "legendary"]:
            current = artist_data.get(tier, 0)
            
            if tier == "legendary":
                status["by_tier"][tier] = {
                    "current": current,
                    "max": self.LEGENDARY_MAX_PER_ARTIST,
                    "remaining": self.LEGENDARY_MAX_PER_ARTIST - current,
                    "percentage": (current / self.LEGENDARY_MAX_PER_ARTIST) * 100
                }
            elif tier == "platinum":
                status["by_tier"][tier] = {
                    "current": current,
                    "max": self.PLATINUM_MAX_PER_ARTIST,
                    "remaining": self.PLATINUM_MAX_PER_ARTIST - current,
                    "percentage": (current / self.PLATINUM_MAX_PER_ARTIST) * 100
                }
            else:
                status["by_tier"][tier] = {
                    "current": current,
                    "max": "unlimited",
                    "remaining": "unlimited",
                    "percentage": 0.0
                }
        
        return status
    
    def end_season(self):
        """End the season and transition to legacy state"""
        if self.state == SeasonState.ACTIVE:
            self.state = SeasonState.ENDED
            self.save_supply_state()
            logger.info(f"Season {self.season_number} ended")
            
            # Could trigger legacy badge distribution here
            return True
        return False
    
    def make_legacy(self):
        """Transition season to legacy state"""
        if self.state == SeasonState.ENDED:
            self.state = SeasonState.LEGACY
            self.save_supply_state()
            logger.info(f"Season {self.season_number} is now legacy")
            return True
        return False
    
    def validate_supply_integrity(self) -> List[str]:
        """Validate supply system integrity and return issues"""
        issues = []
        
        # Check total supply
        total_mints = sum(self.current_mints.values())
        if total_mints > self.TOTAL_SUPPLY_TARGET:
            issues.append(f"Total supply exceeded: {total_mints} > {self.TOTAL_SUPPLY_TARGET}")
        
        # Check tier caps
        for tier, info in self.RARITY_DISTRIBUTION.items():
            current = self.current_mints.get(tier, 0)
            max_cards = info["max_cards"]
            if current > max_cards:
                issues.append(f"Tier {tier} exceeded cap: {current} > {max_cards}")
        
        # Check artist limits
        for artist_id, artist_data in self.artist_mints.items():
            legendary_mints = artist_data.get("legendary", 0)
            if legendary_mints > self.LEGENDARY_MAX_PER_ARTIST:
                issues.append(f"Artist {artist_id} legendary cap exceeded: {legendary_mints} > {self.LEGENDARY_MAX_PER_ARTIST}")
            
            platinum_mints = artist_data.get("platinum", 0)
            if platinum_mints > self.PLATINUM_MAX_PER_ARTIST:
                issues.append(f"Artist {artist_id} platinum cap exceeded: {platinum_mints} > {self.PLATINUM_MAX_PER_ARTIST}")
        
        return issues

# Global season supply system instance
season_supply = SeasonSupplySystem()

def can_mint_card(tier: str, artist_id: str, pack_source: str = "black_packs") -> Dict[str, Any]:
    """Check if card can be minted"""
    return season_supply.can_mint_card(tier, artist_id, pack_source)

def mint_card(tier: str, artist_id: str, pack_source: str = "black_packs") -> Dict[str, Any]:
    """Record a card mint"""
    return season_supply.mint_card(tier, artist_id, pack_source)

def get_serial_value_tier(serial_number: int) -> SerialValueTier:
    """Get serial value tier"""
    return season_supply.get_serial_value_tier(serial_number)

def get_supply_status() -> Dict[str, Any]:
    """Get supply system status"""
    return season_supply.get_supply_status()

def get_artist_status(artist_id: str) -> Dict[str, Any]:
    """Get artist mint status"""
    return season_supply.get_artist_status(artist_id)

def validate_supply_integrity() -> List[str]:
    """Validate supply system"""
    return season_supply.validate_supply_integrity()
