# packs/pack_validator.py
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from packs.founder_packs import founder_packs

class PackValidator:
    """Validate pack openings and ensure compliance"""
    
    def __init__(self):
        self.validation_log = []
    
    def validate_pack_opening(self, pack_id: str, cards: List[Dict], user_id: int) -> Dict:
        """Comprehensive pack opening validation"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "pack_id": pack_id,
            "user_id": user_id,
            "card_count": len(cards),
            "timestamp": datetime.now().isoformat()
        }
        
        # Get pack configuration
        pack_config = founder_packs.get_pack_config(pack_id)
        if not pack_config:
            validation_result["valid"] = False
            validation_result["errors"].append("Invalid pack ID")
            return validation_result
        
        # Validate card count
        if len(cards) != pack_config.card_count:
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Card count mismatch: expected {pack_config.card_count}, got {len(cards)}"
            )
        
        # Validate guarantee (Black Pack)
        if pack_id == founder_packs.PACK_BLACK and pack_config.guarantee == "gold+":
            gold_plus_count = sum(1 for card in cards if card.get('tier') in ['gold', 'platinum', 'legendary'])
            if gold_plus_count < 1:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Black Pack guarantee violation: expected 1+ Gold+, got {gold_plus_count}"
                )
        
        # Validate tier distribution
        tier_counts = self._count_tiers(cards)
        expected_tiers = self._get_expected_tier_distribution(pack_id)
        
        for tier, count in tier_counts.items():
            if tier in expected_tiers:
                expected_range = expected_tiers[tier]
                if count < expected_range["min"] or count > expected_range["max"]:
                    validation_result["warnings"].append(
                        f"Unusual {tier} count: {count} (expected {expected_range['min']}-{expected_range['max']})"
                    )
        
        # Validate against season caps (if available)
        cap_violations = self._check_tier_caps(cards)
        if cap_violations:
            validation_result["errors"].extend(cap_violations)
            validation_result["valid"] = False
        
        # Log validation result
        self._log_validation(validation_result)
        
        return validation_result
    
    def _count_tiers(self, cards: List[Dict]) -> Dict[str, int]:
        """Count cards by tier"""
        tier_counts = {"community": 0, "gold": 0, "platinum": 0, "legendary": 0}
        
        for card in cards:
            tier = card.get('tier', 'community')
            if tier in tier_counts:
                tier_counts[tier] += 1
        
        return tier_counts
    
    def _get_expected_tier_distribution(self, pack_id: str) -> Dict[str, Dict[str, int]]:
        """Get expected tier distribution ranges"""
        pack_config = founder_packs.get_pack_config(pack_id)
        if not pack_config:
            return {}
        
        if pack_id == founder_packs.PACK_BLACK:
            # Black Pack: 1 guaranteed + 4 regular
            return {
                "community": {"min": 0, "max": 4},  # From regular slots
                "gold": {"min": 1, "max": 5},      # At least 1 from guarantee
                "platinum": {"min": 0, "max": 2},  # Could be from guarantee or regular
                "legendary": {"min": 0, "max": 1}   # Rare but possible
            }
        else:
            # Silver Pack: 5 regular slots
            return {
                "community": {"min": 2, "max": 5},  # Most likely
                "gold": {"min": 0, "max": 2},       # Possible
                "platinum": {"min": 0, "max": 1},   # Rare
                "legendary": {"min": 0, "max": 1}    # Very rare
            }
    
    def _check_tier_caps(self, cards: List[Dict]) -> List[str]:
        """Check against season tier caps"""
        violations = []
        
        # This would integrate with your season system
        # For now, just log the check
        for card in cards:
            tier = card.get('tier')
            artist = card.get('artist_name', 'Unknown')
            
            # Log for audit
            logging.info(f"Checking cap for {artist} {tier}")
        
        return violations
    
    def _log_validation(self, result: Dict):
        """Log validation result"""
        log_entry = {
            "timestamp": result["timestamp"],
            "valid": result["valid"],
            "pack_id": result["pack_id"],
            "user_id": result["user_id"],
            "card_count": result["card_count"],
            "errors": result["errors"],
            "warnings": result["warnings"]
        }
        
        self.validation_log.append(log_entry)
        
        # Log to file/database
        if result["valid"]:
            logging.info(f"Pack validation passed: {result['pack_id']} for user {result['user_id']}")
        else:
            logging.error(f"Pack validation failed: {result['pack_id']} for user {result['user_id']} - {result['errors']}")
    
    def get_validation_stats(self) -> Dict:
        """Get validation statistics"""
        total_validations = len(self.validation_log)
        valid_count = sum(1 for log in self.validation_log if log["valid"])
        invalid_count = total_validations - valid_count
        
        pack_stats = {}
        for log in self.validation_log:
            pack_id = log["pack_id"]
            if pack_id not in pack_stats:
                pack_stats[pack_id] = {"total": 0, "valid": 0, "invalid": 0}
            
            pack_stats[pack_id]["total"] += 1
            if log["valid"]:
                pack_stats[pack_id]["valid"] += 1
            else:
                pack_stats[pack_id]["invalid"] += 1
        
        return {
            "total_validations": total_validations,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "success_rate": (valid_count / total_validations * 100) if total_validations > 0 else 0,
            "pack_stats": pack_stats
        }
    
    def get_recent_validations(self, limit: int = 50) -> List[Dict]:
        """Get recent validation results"""
        return self.validation_log[-limit:]
    
    def clear_validation_log(self):
        """Clear validation log (for maintenance)"""
        self.validation_log.clear()
        logging.info("Validation log cleared")

# Global validator instance
pack_validator = PackValidator()
