"""
Serial System (Investor-Grade)

Your serials must tell a story.
Format: ML-S{season}-{tier_letter}-{print_number}

Examples:
ML-S1-L-0001 → First Legendary ever
ML-S1-G-0123 → Gold, mid-run

Rules:
- Legendary serials are globally scarce
- Print # never reused
- Burned cards do NOT free serials
"""

from typing import Dict, Optional, Set
from datetime import datetime
import json
import os
from schemas.card_canonical import CardTier

class SerialSystem:
    """
    Investor-grade serial number management.
    Ensures scarcity and prevents reuse.
    """
    
    def __init__(self, season: int = 1):
        self.season = season
        self.serial_file = f"serials_season_{season}.json"
        self.used_serials: Set[str] = set()
        self.print_counters: Dict[str, int] = {}
        self.load_serial_data()
    
    def load_serial_data(self):
        """Load existing serial data from file"""
        if os.path.exists(self.serial_file):
            try:
                with open(self.serial_file, 'r') as f:
                    data = json.load(f)
                    self.used_serials = set(data.get("used_serials", []))
                    self.print_counters = data.get("print_counters", {})
            except Exception as e:
                print(f"Error loading serial data: {e}")
                self.used_serials = set()
                self.print_counters = {}
    
    def save_serial_data(self):
        """Save serial data to file"""
        try:
            data = {
                "season": self.season,
                "used_serials": list(self.used_serials),
                "print_counters": self.print_counters,
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(self.serial_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving serial data: {e}")
    
    def get_tier_letter(self, tier: CardTier) -> str:
        """Get tier letter for serial format"""
        tier_letters = {
            CardTier.COMMUNITY: "C",
            CardTier.GOLD: "G",
            CardTier.PLATINUM: "P",
            CardTier.LEGENDARY: "L"
        }
        return tier_letters.get(tier, "C")
    
    def generate_serial(self, tier: CardTier) -> str:
        """
        Generate unique serial number.
        Format: ML-S{season}-{tier_letter}-{print_number}
        """
        tier_letter = self.get_tier_letter(tier)
        counter_key = f"S{self.season}_{tier_letter}"
        
        # Increment print counter
        if counter_key not in self.print_counters:
            self.print_counters[counter_key] = 0
        
        self.print_counters[counter_key] += 1
        print_number = self.print_counters[counter_key]
        
        # Generate serial
        serial = f"ML-S{self.season}-{tier_letter}-{print_number:04d}"
        
        # Ensure uniqueness
        if serial in self.used_serials:
            # This should never happen, but handle it
            print(f"Serial collision detected: {serial}")
            return self.generate_serial(tier)
        
        # Mark as used
        self.used_serials.add(serial)
        self.save_serial_data()
        
        return serial
    
    def is_serial_used(self, serial: str) -> bool:
        """Check if serial is already used"""
        return serial in self.used_serials
    
    def get_print_count(self, tier: CardTier) -> int:
        """Get current print count for tier"""
        tier_letter = self.get_tier_letter(tier)
        counter_key = f"S{self.season}_{tier_letter}"
        return self.print_counters.get(counter_key, 0)
    
    def get_serial_info(self, serial: str) -> Optional[Dict]:
        """Parse serial and return information"""
        try:
            # Parse ML-S{season}-{tier_letter}-{print_number}
            parts = serial.split('-')
            if len(parts) != 3 or not parts[0].startswith('ML-S'):
                return None
            
            season_part = parts[0][3:]  # Remove 'ML-S'
            tier_letter = parts[1]
            print_number = int(parts[2])
            
            # Map tier letter back to tier
            tier_map = {
                "C": CardTier.COMMUNITY,
                "G": CardTier.GOLD,
                "P": CardTier.PLATINUM,
                "L": CardTier.LEGENDARY
            }
            
            tier = tier_map.get(tier_letter)
            if not tier:
                return None
            
            return {
                "season": int(season_part),
                "tier": tier,
                "tier_letter": tier_letter,
                "print_number": print_number,
                "serial": serial,
                "is_used": serial in self.used_serials
            }
            
        except Exception:
            return None
    
    def get_scarcity_info(self, tier: CardTier) -> Dict:
        """Get scarcity information for a tier"""
        print_count = self.get_print_count(tier)
        
        # Define scarcity thresholds
        scarcity_thresholds = {
            CardTier.LEGENDARY: {
                "ultra_rare": 10,
                "very_rare": 50,
                "rare": 100,
                "common": 500
            },
            CardTier.PLATINUM: {
                "ultra_rare": 25,
                "very_rare": 100,
                "rare": 250,
                "common": 1000
            },
            CardTier.GOLD: {
                "ultra_rare": 100,
                "very_rare": 500,
                "rare": 1000,
                "common": 5000
            },
            CardTier.COMMUNITY: {
                "ultra_rare": 1000,
                "very_rare": 5000,
                "rare": 10000,
                "common": 50000
            }
        }
        
        thresholds = scarcity_thresholds.get(tier, scarcity_thresholds[CardTier.COMMUNITY])
        
        if print_count <= thresholds["ultra_rare"]:
            scarcity = "ultra_rare"
        elif print_count <= thresholds["very_rare"]:
            scarcity = "very_rare"
        elif print_count <= thresholds["rare"]:
            scarcity = "rare"
        else:
            scarcity = "common"
        
        return {
            "tier": tier.value,
            "print_count": print_count,
            "scarcity": scarcity,
            "thresholds": thresholds,
            "next_serial": f"ML-S{self.season}-{self.get_tier_letter(tier)}-{print_count + 1:04d}"
        }
    
    def get_all_scarcity_info(self) -> Dict:
        """Get scarcity info for all tiers"""
        return {
            tier.value: self.get_scarcity_info(tier)
            for tier in CardTier
        }
    
    def validate_serial_format(self, serial: str) -> bool:
        """Validate serial format"""
        info = self.get_serial_info(serial)
        return info is not None
    
    def get_legendary_status(self, serial: str) -> Optional[Dict]:
        """Get special status for legendary cards"""
        info = self.get_serial_info(serial)
        if not info or info["tier"] != CardTier.LEGENDARY:
            return None
        
        print_number = info["print_number"]
        
        if print_number == 1:
            return {"status": "first_legendary", "description": "The first Legendary card ever minted"}
        elif print_number <= 10:
            return {"status": "early_legendary", "description": f"One of the first {print_number} Legendary cards"}
        elif print_number <= 100:
            return {"status": "early_print", "description": f"Early Legendary print #{print_number}"}
        else:
            return {"status": "standard", "description": f"Legendary print #{print_number}"}

# Global serial system instance
serial_system = SerialSystem()

def generate_serial(tier: CardTier) -> str:
    """Generate serial for a tier"""
    return serial_system.generate_serial(tier)

def get_serial_info(serial: str) -> Optional[Dict]:
    """Get serial information"""
    return serial_system.get_serial_info(serial)

def get_scarcity_info(tier: CardTier) -> Dict:
    """Get scarcity information for tier"""
    return serial_system.get_scarcity_info(tier)

def is_serial_used(serial: str) -> bool:
    """Check if serial is used"""
    return serial_system.is_serial_used(serial)
