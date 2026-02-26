# config/battle_pass.py
"""
Music Legends - Battle Pass System
Season 1: "Rhythm Rising"
50 Tiers, 60-day season, $9.99 premium unlock
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================
# SEASON CONFIGURATION
# ============================================

class SeasonConfig:
    """Current season configuration"""
    
    CURRENT_SEASON = 1
    
    # Hardcoded season start/end dates
    # TODO: Load season start date from database
    SEASON_START = datetime(2025, 1, 27)
    SEASON_END = SEASON_START + timedelta(days=60) # Use BattlePass.SEASON_DURATION_DAYS once defined
    
    # Exclusive cards for this season
    EXCLUSIVE_CARDS = [
        {"name": "Rhythm Rising Champion", "rarity": "mythic"},
        {"name": "Rhythm Rising Elite", "rarity": "mythic"},
        {"name": "Rhythm Rising Master", "rarity": "mythic"},
        {"name": "Rhythm Rising Legend", "rarity": "mythic"},
        {"name": "Rhythm Rising Ultimate", "rarity": "ultra_mythic"},
    ]
    
    def is_active(self) -> bool:
        """Check if season is currently active"""
        now = datetime.now()
        return self.SEASON_START <= now <= self.SEASON_END
    
    def days_remaining(self) -> int:
        """Days left in the season"""
        remaining = self.SEASON_END - datetime.now()
        return max(0, remaining.days)


# ============================================
# BATTLE PASS CONFIGURATION
# ============================================

class BattlePass:
    """Battle Pass Season 1 Configuration"""
    
    # Season info
    SEASON_NAME = "Rhythm Rising"
    SEASON_NUMBER = 1
    SEASON_DURATION_DAYS = 60
    PREMIUM_PRICE_USD = 9.99
    PREMIUM_PRICE_CENTS = 999
    
    # Progression
    TOTAL_TIERS = 50
    XP_PER_TIER = [
        # Early tiers = easier
        100,  # Tier 1
        100,  # Tier 2
        100,  # Tier 3
        100,  # Tier 4
        100,  # Tier 5
        150,  # Tier 6-10
        150, 150, 150, 150,
        200,  # Tier 11-15
        200, 200, 200, 200,
        250,  # Tier 16-20
        250, 250, 250, 250,
        300,  # Tier 21-30
        300, 300, 300, 300, 300, 300, 300, 300, 300,
        400,  # Tier 31-40
        400, 400, 400, 400, 400, 400, 400, 400, 400,
        500,  # Tier 41-50 (hardest)
        500, 500, 500, 500, 500, 500, 500, 500, 500,
    ]
    
    TOTAL_XP_REQUIRED = sum(XP_PER_TIER)  # 14,500 XP total
    
    # Tier skip pricing
    TIER_SKIP_PRICE_USD = 1.00
    TIER_SKIP_PRICE_CENTS = 100
    TIER_SKIP_TICKETS = 10  # Or 10 tickets per tier
    
    # XP sources
    XP_SOURCES = {
        "daily_claim": 50,
        "battle_win": 25,
        "battle_loss": 5,
        "quest_complete": 100,
        "first_win_bonus": 50,  # Per day
        "friend_battle": 10,    # Battle with friend
    }


# ============================================
# TIER REWARDS (FREE TRACK)
# ============================================

FREE_TRACK_REWARDS = {
    1: {"type": "gold", "amount": 100},
    2: {"type": "xp_boost", "amount": "10% for 24h"},
    3: {"type": "gold", "amount": 150},
    4: {"type": "card", "rarity": "common"},
    5: {"type": "gold", "amount": 200},
    
    6: {"type": "card", "rarity": "common"},
    7: {"type": "gold", "amount": 250},
    8: {"type": "card", "rarity": "common"},
    9: {"type": "gold", "amount": 300},
    10: {"type": "pack", "pack_type": "community"},
    
    11: {"type": "gold", "amount": 400},
    12: {"type": "card", "rarity": "rare"},
    13: {"type": "gold", "amount": 500},
    14: {"type": "card", "rarity": "rare"},
    15: {"type": "gold", "amount": 600},
    
    16: {"type": "card", "rarity": "rare"},
    17: {"type": "gold", "amount": 700},
    18: {"type": "xp_boost", "amount": "25% for 48h"},
    19: {"type": "gold", "amount": 800},
    20: {"type": "pack", "pack_type": "community"},
    
    21: {"type": "gold", "amount": 900},
    22: {"type": "card", "rarity": "rare"},
    23: {"type": "gold", "amount": 1000},
    24: {"type": "card", "rarity": "epic"},
    25: {"type": "tickets", "amount": 1},
    
    26: {"type": "gold", "amount": 1200},
    27: {"type": "card", "rarity": "epic"},
    28: {"type": "gold", "amount": 1400},
    29: {"type": "card", "rarity": "epic"},
    30: {"type": "pack", "pack_type": "community"},
    
    31: {"type": "gold", "amount": 1600},
    32: {"type": "card", "rarity": "epic"},
    33: {"type": "gold", "amount": 1800},
    34: {"type": "tickets", "amount": 2},
    35: {"type": "gold", "amount": 2000},
    
    36: {"type": "card", "rarity": "legendary"},
    37: {"type": "gold", "amount": 2200},
    38: {"type": "xp_boost", "amount": "50% for 72h"},
    39: {"type": "gold", "amount": 2400},
    40: {"type": "pack", "pack_type": "community"},
    
    41: {"type": "gold", "amount": 2600},
    42: {"type": "card", "rarity": "legendary"},
    43: {"type": "gold", "amount": 2800},
    44: {"type": "tickets", "amount": 3},
    45: {"type": "gold", "amount": 3000},
    
    46: {"type": "card", "rarity": "legendary"},
    47: {"type": "gold", "amount": 3500},
    48: {"type": "pack", "pack_type": "gold"},
    49: {"type": "gold", "amount": 4000},
    50: {"type": "exclusive_card", "name": "Rhythm Rising Champion", "rarity": "mythic"},
}


# ============================================
# TIER REWARDS (PREMIUM TRACK)
# ============================================

PREMIUM_TRACK_REWARDS = {
    1: {"type": "gold", "amount": 500},
    2: {"type": "cosmetic", "item": "Neon Beats Card Back"},
    3: {"type": "gold", "amount": 600},
    4: {"type": "card", "rarity": "rare"},
    5: {"type": "pack", "pack_type": "gold"},
    
    6: {"type": "gold", "amount": 700},
    7: {"type": "card", "rarity": "epic"},
    8: {"type": "tickets", "amount": 5},
    9: {"type": "gold", "amount": 800},
    10: {"type": "pack", "pack_type": "gold", "amount": 2},
    
    11: {"type": "gold", "amount": 1000},
    12: {"type": "cosmetic", "item": "Premium Player Badge"},
    13: {"type": "card", "rarity": "legendary"},
    14: {"type": "gold", "amount": 1200},
    15: {"type": "pack", "pack_type": "gold"},
    
    16: {"type": "tickets", "amount": 10},
    17: {"type": "gold", "amount": 1400},
    18: {"type": "cosmetic", "item": "Bass Drop Emote"},
    19: {"type": "card", "rarity": "legendary"},
    20: {"type": "pack", "pack_type": "gold", "amount": 2},
    
    21: {"type": "gold", "amount": 1600},
    22: {"type": "xp_boost", "amount": "100% for 7 days"},
    23: {"type": "card", "rarity": "legendary"},
    24: {"type": "gold", "amount": 1800},
    25: {"type": "exclusive_card", "name": "Rhythm Rising Elite", "rarity": "mythic"},
    
    26: {"type": "tickets", "amount": 15},
    27: {"type": "gold", "amount": 2000},
    28: {"type": "cosmetic", "item": "Platinum Profile Frame"},
    29: {"type": "pack", "pack_type": "gold", "amount": 3},
    30: {"type": "exclusive_card", "name": "Rhythm Rising Master", "rarity": "mythic"},
    
    31: {"type": "gold", "amount": 2500},
    32: {"type": "card", "rarity": "legendary", "amount": 2},
    33: {"type": "tickets", "amount": 20},
    34: {"type": "gold", "amount": 3000},
    35: {"type": "pack", "pack_type": "gold", "amount": 3},
    
    36: {"type": "cosmetic", "item": "Diamond Card Back"},
    37: {"type": "gold", "amount": 3500},
    38: {"type": "card", "rarity": "legendary", "amount": 2},
    39: {"type": "tickets", "amount": 25},
    40: {"type": "pack", "pack_type": "gold", "amount": 4},
    
    41: {"type": "gold", "amount": 4000},
    42: {"type": "cosmetic", "item": "Legendary Profile Animation"},
    43: {"type": "exclusive_card", "name": "Rhythm Rising Legend", "rarity": "mythic"},
    44: {"type": "tickets", "amount": 30},
    45: {"type": "pack", "pack_type": "gold", "amount": 5},
    
    46: {"type": "gold", "amount": 5000},
    47: {"type": "cosmetic", "item": "Champion's Crown Card Back"},
    48: {"type": "card", "rarity": "legendary", "amount": 3},
    49: {"type": "tickets", "amount": 50},
    50: {"type": "exclusive_bundle", "contents": [
        {"type": "exclusive_card", "name": "Rhythm Rising Ultimate", "rarity": "ultra_mythic"},
        {"type": "cosmetic", "item": "Ultimate Champion Title"},
        {"type": "gold", "amount": 10000},
        {"type": "tickets", "amount": 100},
        {"type": "pack", "pack_type": "gold", "amount": 10},
    ]},
}


# ============================================
# BATTLE PASS MANAGER
# ============================================

class BattlePassManager:
    """Manage Battle Pass progression"""
    
    def __init__(self, season_start: datetime = None):
        self.season_start = season_start or datetime.now()
        self.season_end = self.season_start + timedelta(days=BattlePass.SEASON_DURATION_DAYS)
    
    def calculate_tier_from_xp(self, xp: int) -> int:
        """Calculate current tier based on XP"""
        cumulative_xp = 0
        for tier, xp_needed in enumerate(BattlePass.XP_PER_TIER, start=1):
            cumulative_xp += xp_needed
            if xp < cumulative_xp:
                return tier
        return BattlePass.TOTAL_TIERS
    
    def get_cumulative_xp_for_tier(self, tier: int) -> int:
        """Get total XP needed to reach a specific tier"""
        if tier <= 0:
            return 0
        if tier > BattlePass.TOTAL_TIERS:
            tier = BattlePass.TOTAL_TIERS
        return sum(BattlePass.XP_PER_TIER[:tier])
    
    def xp_to_next_tier(self, current_xp: int) -> int:
        """Calculate XP needed for next tier"""
        current_tier = self.calculate_tier_from_xp(current_xp)
        
        if current_tier >= BattlePass.TOTAL_TIERS:
            return 0  # Already max tier
        
        # Calculate cumulative XP up to current tier
        cumulative_xp = sum(BattlePass.XP_PER_TIER[:current_tier])
        
        # XP needed for next tier
        next_tier_xp = cumulative_xp + BattlePass.XP_PER_TIER[current_tier]
        
        return next_tier_xp - current_xp
    
    def get_xp_progress_in_tier(self, current_xp: int) -> tuple:
        """Get XP progress within current tier (current, needed)"""
        current_tier = self.calculate_tier_from_xp(current_xp)
        
        if current_tier >= BattlePass.TOTAL_TIERS:
            return (0, 0)  # Max tier
        
        # XP at start of current tier
        tier_start_xp = sum(BattlePass.XP_PER_TIER[:current_tier - 1]) if current_tier > 1 else 0
        
        # XP needed for this tier
        tier_xp_needed = BattlePass.XP_PER_TIER[current_tier - 1]
        
        # Progress in current tier
        progress = current_xp - tier_start_xp
        
        return (progress, tier_xp_needed)
    
    def get_tier_rewards(self, tier: int, has_premium: bool) -> Dict:
        """Get rewards for a specific tier"""
        rewards = {
            "tier": tier,
            "free_reward": FREE_TRACK_REWARDS.get(tier),
            "premium_reward": None,
        }
        
        if has_premium:
            rewards["premium_reward"] = PREMIUM_TRACK_REWARDS.get(tier)
        
        return rewards
    
    def get_unclaimed_rewards(self, current_tier: int, claimed_tiers: List[int], has_premium: bool) -> List[Dict]:
        """Get list of unclaimed rewards up to current tier"""
        unclaimed = []
        for tier in range(1, current_tier + 1):
            if tier not in claimed_tiers:
                rewards = self.get_tier_rewards(tier, has_premium)
                unclaimed.append(rewards)
        return unclaimed
    
    def days_remaining(self) -> int:
        """Calculate days remaining in season"""
        remaining = self.season_end - datetime.now()
        return max(0, remaining.days)
    
    def is_season_active(self) -> bool:
        """Check if season is currently active"""
        now = datetime.now()
        return self.season_start <= now <= self.season_end
    
    def estimate_completion(self, current_xp: int, daily_xp_avg: int) -> dict:
        """Estimate if player will complete Battle Pass"""
        days_left = self.days_remaining()
        current_tier = self.calculate_tier_from_xp(current_xp)
        xp_needed = BattlePass.TOTAL_XP_REQUIRED - current_xp
        
        # Projected XP by season end
        projected_xp = current_xp + (daily_xp_avg * days_left)
        projected_tier = self.calculate_tier_from_xp(projected_xp)
        
        will_complete = projected_tier >= BattlePass.TOTAL_TIERS
        
        return {
            "current_tier": current_tier,
            "projected_tier": projected_tier,
            "will_complete": will_complete,
            "days_remaining": days_left,
            "xp_needed": xp_needed,
            "daily_xp_needed": xp_needed // days_left if days_left > 0 else 0,
        }
    
    def calculate_tier_skip_cost(self, current_tier: int, target_tier: int) -> Dict:
        """Calculate cost to skip to a target tier"""
        if target_tier <= current_tier:
            return {"tiers": 0, "usd": 0, "tickets": 0}
        
        tiers_to_skip = target_tier - current_tier
        
        return {
            "tiers": tiers_to_skip,
            "usd": tiers_to_skip * BattlePass.TIER_SKIP_PRICE_USD,
            "tickets": tiers_to_skip * BattlePass.TIER_SKIP_TICKETS,
        }
    
    def format_reward(self, reward: Dict) -> str:
        """Format a single reward for display"""
        if not reward:
            return "No reward"
        
        reward_type = reward.get("type", "")
        
        if reward_type == "gold":
            return f"💰 {reward['amount']:,} Gold"
        
        elif reward_type == "tickets":
            return f"🎫 {reward['amount']} Tickets"
        
        elif reward_type == "card":
            rarity = reward['rarity'].upper()
            count = reward.get('amount', 1)
            if count > 1:
                return f"🎴 {count}x {rarity} Cards"
            return f"🎴 {rarity} Card"
        
        elif reward_type == "pack":
            pack_type = reward['pack_type'].title()
            count = reward.get('amount', 1)
            if count > 1:
                return f"📦 {count}x {pack_type} Packs"
            return f"📦 {pack_type} Pack"
        
        elif reward_type == "cosmetic":
            return f"✨ {reward['item']}"
        
        elif reward_type == "exclusive_card":
            return f"🌟 **EXCLUSIVE:** {reward['name']} ({reward['rarity'].upper()})"
        
        elif reward_type == "xp_boost":
            return f"⚡ XP Boost: {reward['amount']}"
        
        elif reward_type == "exclusive_bundle":
            bundle_items = []
            for item in reward['contents']:
                bundle_items.append(self.format_reward(item))
            return "🎁 **ULTIMATE BUNDLE:**\n" + "\n".join(f"   • {item}" for item in bundle_items)
        
        return str(reward)
    
    def format_tier_display(self, tier: int, has_premium: bool) -> str:
        """Format tier rewards for display"""
        rewards = self.get_tier_rewards(tier, has_premium)
        
        output = f"🎵 **TIER {tier}** 🎵\n\n"
        
        # Free reward
        free = rewards["free_reward"]
        if free:
            output += "**FREE:**\n"
            output += f"└ {self.format_reward(free)}\n\n"
        
        # Premium reward
        if has_premium and rewards["premium_reward"]:
            premium = rewards["premium_reward"]
            output += "**PREMIUM:**\n"
            output += f"└ {self.format_reward(premium)}\n"
        elif not has_premium and tier in PREMIUM_TRACK_REWARDS:
            output += "**PREMIUM:** 🔒 *Unlock for $9.99*\n"
        
        return output


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_battle_pass_manager() -> BattlePassManager:
    """Get a BattlePassManager instance with current season dates"""
    # TODO: Load season start date from database
    return BattlePassManager()


def calculate_premium_track_value() -> Dict:
    """Calculate total value of premium track rewards"""
    total_gold = 0
    total_tickets = 0
    gold_packs = 0
    community_packs = 0
    exclusive_cards = 0
    cosmetics = 0
    legendary_cards = 0
    
    for tier, reward in PREMIUM_TRACK_REWARDS.items():
        reward_type = reward.get("type", "")
        
        if reward_type == "gold":
            total_gold += reward.get("amount", 0)
        elif reward_type == "tickets":
            total_tickets += reward.get("amount", 0)
        elif reward_type == "pack":
            count = reward.get("amount", 1)
            if reward.get("pack_type") == "gold":
                gold_packs += count
            else:
                community_packs += count
        elif reward_type == "cosmetic":
            cosmetics += 1
        elif reward_type == "exclusive_card":
            exclusive_cards += 1
        elif reward_type == "card" and reward.get("rarity") == "legendary":
            legendary_cards += reward.get("amount", 1)
        elif reward_type == "exclusive_bundle":
            for item in reward.get("contents", []):
                if item.get("type") == "gold":
                    total_gold += item.get("amount", 0)
                elif item.get("type") == "tickets":
                    total_tickets += item.get("amount", 0)
                elif item.get("type") == "pack":
                    gold_packs += item.get("amount", 1)
                elif item.get("type") == "exclusive_card":
                    exclusive_cards += 1
                elif item.get("type") == "cosmetic":
                    cosmetics += 1
    
    # Calculate USD value
    gold_value = (total_gold / 500) * 4.99  # 500 gold = $4.99 (community pack)
    ticket_value = total_tickets * 0.10  # ~$0.10 per ticket
    gold_pack_value = gold_packs * 4.99
    
    total_value = gold_value + ticket_value + gold_pack_value
    
    return {
        "total_gold": total_gold,
        "total_tickets": total_tickets,
        "gold_packs": gold_packs,
        "community_packs": community_packs,
        "exclusive_cards": exclusive_cards,
        "cosmetics": cosmetics,
        "legendary_cards": legendary_cards,
        "estimated_usd_value": total_value,
        "price": BattlePass.PREMIUM_PRICE_USD,
        "value_ratio": total_value / BattlePass.PREMIUM_PRICE_USD,
    }
