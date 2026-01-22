"""
Physical Card Print System (Canonical)

Core Principle: Every physical card must correspond 1:1 with a digital card.
No exceptions. No "promo-only" shortcuts that undermine scarcity.

Physical cards are redeemed representations, not separate mints.
"""

from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CardSize(Enum):
    """Standard card sizes (LOCKED)"""
    TAROT = "tarot"  # 70 × 120 mm (2.75 × 4.75 in)
    # Future sizes could be added but Tarot is locked for Season 1

class PrintSpec(Enum):
    """Print specifications"""
    BLEED_SIZE = (76, 126)  # mm (3mm bleed on all sides)
    FINAL_SIZE = (70, 120)   # mm (final trimmed size)
    SAFE_MARGIN = 3          # mm from edge
    RESOLUTION = 300        # DPI minimum
    COLOR_MODE = "CMYK"

class MaterialTier(Enum):
    """Material and finish tiers"""
    COMMUNITY_GOLD = "community_gold"
    PLATINUM = "platinum"
    LEGENDARY = "legendary"

@dataclass
class PrintSafeZones:
    """Print-safe zone specifications"""
    header_height: float = 8.0      # mm from top
    art_zone_top: float = 16.0      # mm from top
    art_zone_bottom: float = 104.0  # mm from top
    meta_band_height: float = 6.0   # mm
    serial_zone_height: float = 6.0  # mm
    safe_margin: float = 3.0        # mm from all edges

@dataclass
class MaterialSpec:
    """Material specifications by tier"""
    gsm: int
    finish: str
    special_features: List[str]
    foil: bool = False
    laminate: bool = False

class PhysicalCardSystem:
    """
    Canonical physical card system.
    Enforces 1:1 digital-to-physical parity and print specifications.
    """
    
    def __init__(self):
        self.season = 1
        self.redemptions_file = f"physical_redemptions_season_{self.season}.json"
        self.print_orders_file = f"print_orders_season_{self.season}.json"
        
        # Locked card specifications
        self.card_size = CardSize.TAROT
        self.print_spec = PrintSpec
        self.safe_zones = PrintSafeZones()
        
        # Material specifications (TOP-TIER ONLY)
        self.material_specs = {
            MaterialTier.COMMUNITY_GOLD: MaterialSpec(
                gsm=350,
                finish="matte",
                special_features=["black_core_cardstock"],
                foil=False,
                laminate=False
            ),
            MaterialTier.PLATINUM: MaterialSpec(
                gsm=350,
                finish="soft_touch_laminate",
                special_features=["spot_uv_tier_badge"],
                foil=False,
                laminate=True
            ),
            MaterialTier.LEGENDARY: MaterialSpec(
                gsm=400,
                finish="soft_touch_laminate",
                special_features=["gold_foil_tier", "optional_holographic_foil"],
                foil=True,
                laminate=True
            )
        }
        
        # Rich black for luxury packs
        self.rich_black_cmyk = {
            "C": 60,
            "M": 40,
            "Y": 40,
            "K": 100
        }
        
        # Load redemption state
        self.load_redemption_state()
    
    def load_redemption_state(self):
        """Load physical redemption state"""
        if os.path.exists(self.redemptions_file):
            try:
                with open(self.redemptions_file, 'r') as f:
                    data = json.load(f)
                    self.redeemed_cards = set(data.get("redeemed_cards", []))
                    self.print_orders = data.get("print_orders", [])
                    self.last_updated = data.get("last_updated")
            except Exception as e:
                logger.error(f"Error loading redemption state: {e}")
                self.redeemed_cards = set()
                self.print_orders = []
        else:
            self.redeemed_cards = set()
            self.print_orders = []
    
    def save_redemption_state(self):
        """Save redemption state"""
        try:
            data = {
                "season": self.season,
                "redeemed_cards": list(self.redeemed_cards),
                "print_orders": self.print_orders,
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(self.redemptions_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving redemption state: {e}")
    
    def get_material_tier(self, card_tier: str) -> MaterialTier:
        """Get material tier based on card rarity"""
        tier_mapping = {
            "community": MaterialTier.COMMUNITY_GOLD,
            "gold": MaterialTier.COMMUNITY_GOLD,
            "platinum": MaterialTier.PLATINUM,
            "legendary": MaterialTier.LEGENDARY
        }
        return tier_mapping.get(card_tier, MaterialTier.COMMUNITY_GOLD)
    
    def can_redeem_physical(self, card_id: str, owner_id: str) -> Dict[str, Any]:
        """
        Check if a digital card can be redeemed for physical.
        
        Args:
            card_id: Digital card ID
            owner_id: Current owner ID
            
        Returns:
            Dictionary with redemption eligibility
        """
        # Check if card already redeemed
        if card_id in self.redeemed_cards:
            return {
                "can_redeem": False,
                "reason": "Card already redeemed for physical printing",
                "error_code": "ALREADY_REDEEMED"
            }
        
        # In a real implementation, you'd check:
        # - Card ownership in database
        # - Card is not burned
        # - Owner matches current user
        
        # For now, assume ownership check passes
        return {
            "can_redeem": True,
            "reason": "Card eligible for physical redemption",
            "material_tier": self.get_material_tier("legendary").value,  # Would get from actual card
            "print_spec": self.get_print_spec_summary()
        }
    
    def redeem_physical_card(self, card_id: str, owner_id: str, shipping_address: Dict[str, str]) -> Dict[str, Any]:
        """
        Redeem a digital card for physical printing.
        
        Args:
            card_id: Digital card ID
            owner_id: Owner ID
            shipping_address: Shipping information
            
        Returns:
            Dictionary with redemption result
        """
        # Check eligibility
        eligibility = self.can_redeem_physical(card_id, owner_id)
        if not eligibility["can_redeem"]:
            return eligibility
        
        # Create print order
        print_order = {
            "order_id": f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{len(self.print_orders) + 1:04d}",
            "card_id": card_id,
            "owner_id": owner_id,
            "material_tier": eligibility["material_tier"],
            "shipping_address": shipping_address,
            "order_date": datetime.utcnow().isoformat(),
            "status": "pending",
            "tracking_number": None,
            "estimated_delivery": None
        }
        
        # Mark card as redeemed (burns the digital card)
        self.redeemed_cards.add(card_id)
        self.print_orders.append(print_order)
        
        # Save state
        self.save_redemption_state()
        
        logger.info(f"Physical redemption: Card {card_id} redeemed by {owner_id}")
        
        return {
            "success": True,
            "order_id": print_order["order_id"],
            "material_tier": print_order["material_tier"],
            "status": print_order["status"],
            "estimated_delivery": "2-3 weeks"
        }
    
    def get_print_spec_summary(self) -> Dict[str, Any]:
        """Get print specification summary"""
        return {
            "card_size": {
                "final_size_mm": self.print_spec.FINAL_SIZE,
                "final_size_in": (self.print_spec.FINAL_SIZE[0] / 25.4, self.print_spec.FINAL_SIZE[1] / 25.4),
                "aspect_ratio": self.print_spec.FINAL_SIZE[1] / self.print_spec.FINAL_SIZE[0],
                "corners": "3mm rounded"
            },
            "print_specs": {
                "bleed_size_mm": self.print_spec.BLEED_SIZE,
                "resolution_dpi": self.print_spec.RESOLUTION,
                "color_mode": self.print_spec.COLOR_MODE,
                "rich_black_cmyk": self.rich_black_cmyk
            },
            "safe_zones": {
                "header_height_mm": self.safe_zones.header_height,
                "art_zone_top_mm": self.safe_zones.art_zone_top,
                "art_zone_bottom_mm": self.safe_zones.art_zone_bottom,
                "meta_band_height_mm": self.safe_zones.meta_band_height,
                "serial_zone_height_mm": self.safe_zones.serial_zone_height,
                "safe_margin_mm": self.safe_zones.safe_margin
            }
        }
    
    def generate_print_file_data(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate print-ready file data for a card.
        
        Args:
            card_data: Canonical card data
            
        Returns:
            Dictionary with print file specifications
        """
        material_tier = self.get_material_tier(card_data.get("rarity", {}).get("tier", "community"))
        material_spec = self.material_specs[material_tier]
        
        # Front layout data
        front_layout = {
            "size_mm": self.print_spec.FINAL_SIZE,
            "bleed_mm": self.print_spec.BLEED_SIZE,
            "safe_zones": {
                "header": {
                    "y_mm": self.safe_zones.safe_margin,
                    "height_mm": self.safe_zones.header_height,
                    "content": {
                        "artist_name": card_data.get("artist", {}).get("name", ""),
                        "tier": card_data.get("rarity", {}).get("tier", "community").upper()
                    }
                },
                "art_zone": {
                    "y_mm": self.safe_zones.art_zone_top,
                    "height_mm": self.safe_zones.art_zone_bottom - self.safe_zones.art_zone_top,
                    "content": {
                        "artist_image_url": card_data.get("artist", {}).get("image_url", ""),
                        "no_text_overlays": True
                    }
                },
                "meta_band": {
                    "y_mm": self.safe_zones.art_zone_bottom,
                    "height_mm": self.safe_zones.meta_band_height,
                    "content": {
                        "genre": card_data.get("artist", {}).get("primary_genre", ""),
                        "season": f"Season {card_data.get('identity', {}).get('season', 1)}"
                    }
                },
                "serial_zone": {
                    "y_mm": self.safe_zones.art_zone_bottom + self.safe_zones.meta_band_height,
                    "height_mm": self.safe_zones.serial_zone_height,
                    "content": {
                        "serial": card_data.get("identity", {}).get("serial", ""),
                        "print_info": f"/ {card_data.get('rarity', {}).get('print_cap', '???')}"
                    }
                }
            },
            "material_spec": {
                "gsm": material_spec.gsm,
                "finish": material_spec.finish,
                "special_features": material_spec.special_features,
                "foil": material_spec.foil,
                "laminate": material_spec.laminate
            },
            "color_spec": {
                "mode": self.print_spec.COLOR_MODE,
                "rich_black": self.rich_black_cmyk if material_tier == MaterialTier.LEGENDARY else None
            }
        }
        
        # Back layout data (no artist data, no serial, no QR)
        back_layout = {
            "size_mm": self.print_spec.FINAL_SIZE,
            "bleed_mm": self.print_spec.BLEED_SIZE,
            "content": {
                "game_logo": True,
                "season_mark": f"S{card_data.get('identity', {}).get('season', 1)}",
                "pattern": True,
                "no_artist_data": True,
                "no_serial": True,
                "no_qr_code": True
            }
        }
        
        # QR code (optional, front-only, micro-sized)
        qr_code = None
        if card_data.get("include_qr", False):
            qr_code = {
                "position": "front_bottom_right",
                "size_mm": 8,  # Micro-sized
                "content": {
                    "verification_url": f"https://verify.game/card/{card_data.get('identity', {}).get('serial', '')}",
                    "serial_only": True,
                    "no_wallet_info": True,
                    "no_minting": True
                }
            }
        
        return {
            "card_id": card_data.get("card_id"),
            "front_layout": front_layout,
            "back_layout": back_layout,
            "qr_code": qr_code,
            "material_tier": material_tier.value,
            "print_order_id": f"PRINT-{card_data.get('card_id', 'UNKNOWN')}",
            "generation_date": datetime.utcnow().isoformat()
        }
    
    def get_redemption_status(self, owner_id: str) -> Dict[str, Any]:
        """Get redemption status for a user"""
        user_orders = [order for order in self.print_orders if order["owner_id"] == owner_id]
        
        return {
            "owner_id": owner_id,
            "total_redemptions": len(user_orders),
            "orders": user_orders,
            "redeemed_cards": [order["card_id"] for order in user_orders],
            "pending_orders": len([o for o in user_orders if o["status"] == "pending"]),
            "shipped_orders": len([o for o in user_orders if o["status"] == "shipped"])
        }
    
    def update_order_status(self, order_id: str, status: str, tracking_number: str = None) -> bool:
        """Update print order status"""
        for order in self.print_orders:
            if order["order_id"] == order_id:
                order["status"] = status
                if tracking_number:
                    order["tracking_number"] = tracking_number
                if status == "shipped":
                    order["shipped_date"] = datetime.utcnow().isoformat()
                
                self.save_redemption_state()
                logger.info(f"Order {order_id} updated to status: {status}")
                return True
        
        return False
    
    def validate_print_integrity(self) -> List[str]:
        """Validate physical print system integrity"""
        issues = []
        
        # Check for duplicate card IDs in print orders
        card_ids = [order["card_id"] for order in self.print_orders]
        duplicate_cards = [card_id for card_id in set(card_ids) if card_ids.count(card_id) > 1]
        
        if duplicate_cards:
            issues.append(f"Duplicate card IDs in print orders: {duplicate_cards}")
        
        # Check for cards in redeemed set but not in print orders
        missing_orders = [card_id for card_id in self.redeemed_cards if card_id not in card_ids]
        if missing_orders:
            issues.append(f"Redeemed cards without print orders: {missing_orders}")
        
        # Check for print orders without redemption
        unclaimed_orders = [order for order in self.print_orders if order["card_id"] not in self.redeemed_cards]
        if unclaimed_orders:
            issues.append(f"Print orders without redemption: {unclaimed_orders}")
        
        return issues

# Global physical card system instance
physical_card_system = PhysicalCardSystem()

def can_redeem_physical(card_id: str, owner_id: str) -> Dict[str, Any]:
    """Check if card can be redeemed for physical"""
    return physical_card_system.can_redeem_physical(card_id, owner_id)

def redeem_physical_card(card_id: str, owner_id: str, shipping_address: Dict[str, str]) -> Dict[str, Any]:
    """Redeem digital card for physical printing"""
    return physical_card_system.redeem_physical_card(card_id, owner_id, shipping_address)

def generate_print_file_data(card_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate print-ready file data"""
    return physical_card_system.generate_print_file_data(card_data)

def get_redemption_status(owner_id: str) -> Dict[str, Any]:
    """Get user's redemption status"""
    return physical_card_system.get_redemption_status(owner_id)

def validate_print_integrity() -> List[str]:
    """Validate physical print system"""
    return physical_card_system.validate_print_integrity()
