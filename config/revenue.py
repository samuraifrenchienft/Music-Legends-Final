# config/revenue.py
"""
Music Legends - Revenue Model Configuration
Battle Pass, VIP Subscription, and Hybrid monetization
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# ============================================
# BATTLE PASS CONFIGURATION
# ============================================

class BattlePassConfig:
    """
    Battle Pass = Seasonal subscription model
    
    - Season lasts 60 days
    - Free track: Basic rewards
    - Premium track ($9.99): Better rewards
    - 100 tiers for maximum engagement and whale revenue
    """
    
    PRICE_USD = 9.99
    PRICE_USD_CENTS = 999
    SEASON_LENGTH_DAYS = 60
    TOTAL_TIERS = 100
    
    # Tier skip pricing
    TIER_SKIP_PRICE_USD = 1.00
    TIER_SKIP_PRICE_CENTS = 100
    TIER_SKIP_BUNDLE_10 = 8.99  # 10 tiers for $8.99 (10% discount)
    TIER_SKIP_BUNDLE_25 = 19.99  # 25 tiers for $19.99 (20% discount)
    
    # XP Requirements
    XP_PER_TIER = 100  # 100 XP = 1 tier level
    TOTAL_XP_FOR_MAX = 10000  # 100 tiers × 100 XP
    
    # Free Track Rewards (every 5-10 tiers)
    FREE_TRACK_REWARDS = {
        1: {"type": "gold", "amount": 100},
        5: {"type": "pack", "pack_type": "community", "amount": 1},
        10: {"type": "gold", "amount": 200},
        15: {"type": "card", "rarity": "rare", "amount": 1},
        20: {"type": "pack", "pack_type": "community", "amount": 1},
        25: {"type": "gold", "amount": 500},
        30: {"type": "card", "rarity": "epic", "amount": 1},
        35: {"type": "gold", "amount": 300},
        40: {"type": "pack", "pack_type": "community", "amount": 2},
        45: {"type": "gold", "amount": 400},
        50: {"type": "card", "rarity": "epic", "amount": 1},
        55: {"type": "gold", "amount": 500},
        60: {"type": "pack", "pack_type": "community", "amount": 2},
        65: {"type": "gold", "amount": 600},
        70: {"type": "card", "rarity": "epic", "amount": 1},
        75: {"type": "gold", "amount": 750},
        80: {"type": "pack", "pack_type": "community", "amount": 3},
        85: {"type": "gold", "amount": 800},
        90: {"type": "card", "rarity": "legendary", "amount": 1},
        95: {"type": "gold", "amount": 1000},
        100: {"type": "gold", "amount": 2000},
    }
    
    # Premium Track Rewards (every tier has something)
    PREMIUM_TRACK_REWARDS = {
        1: {"type": "gold", "amount": 500, "bonus": "exclusive_card_back_s1"},
        5: {"type": "pack", "pack_type": "gold", "amount": 1},
        10: {"type": "gold", "amount": 1000, "bonus": "premium_badge"},
        15: {"type": "card", "rarity": "legendary", "amount": 1},
        20: {"type": "pack", "pack_type": "gold", "amount": 2},
        25: {"type": "gold", "amount": 2000, "bonus": "exclusive_emote"},
        30: {"type": "card", "rarity": "mythic", "amount": 1, "note": "season_exclusive"},
        35: {"type": "pack", "pack_type": "gold", "amount": 3},
        40: {"type": "gold", "amount": 3000},
        45: {"type": "card", "rarity": "legendary", "amount": 1},
        50: {"type": "gold", "amount": 5000, "bonus": "exclusive_frame"},
        55: {"type": "pack", "pack_type": "gold", "amount": 3},
        60: {"type": "card", "rarity": "legendary", "amount": 1},
        65: {"type": "gold", "amount": 4000},
        70: {"type": "pack", "pack_type": "gold", "amount": 4},
        75: {"type": "gold", "amount": 5000, "bonus": "exclusive_title"},
        80: {"type": "card", "rarity": "mythic", "amount": 1, "note": "season_exclusive"},
        85: {"type": "pack", "pack_type": "gold", "amount": 5},
        90: {"type": "gold", "amount": 7500},
        95: {"type": "card", "rarity": "ultra_rare", "amount": 1},
        100: {"type": "card", "rarity": "legendary", "amount": 1, 
              "bonus": "season_exclusive_legendary", "gold": 10000},
    }
    
    # Season-exclusive cards are tradeable but NEVER return
    SEASON_EXCLUSIVE_TRADEABLE = True
    SEASON_EXCLUSIVE_RETURNS = False


# ============================================
# VIP SUBSCRIPTION CONFIGURATION
# ============================================

class VIPConfig:
    """
    Monthly VIP membership - $4.99/month
    Lower price point for easier conversion
    """
    
    PRICE_USD = 4.99
    PRICE_USD_CENTS = 499
    BILLING_CYCLE_DAYS = 30
    
    # VIP Benefits
    BENEFITS = {
        "daily_bonus_gold": 100,           # +100 gold/day (total 200 with regular daily)
        "daily_bonus_tickets": 1,          # +1 ticket/day
        "free_gold_pack_monthly": 1,       # 1 free Gold Pack per month
        "battle_reward_multiplier": 1.5,   # +50% gold from battles
        "trading_fee_reduction": 0.5,      # 50% off trading fees (5% instead of 10%)
        "marketplace_fee_reduction": 0.5,  # 50% off marketplace fees
        "exclusive_cosmetics": True,       # VIP-only card backs
        "priority_support": True,          # Faster bot responses
        "leaderboard_highlight": True,     # Gold username in leaderboards
        "early_access_packs": True,        # See new packs 24h early
    }
    
    # What VIP does NOT include (to preserve Battle Pass value)
    NOT_INCLUDED = [
        "battle_pass_premium_track",
        "season_exclusive_cards",
        "tier_skips",
    ]


# ============================================
# TICKET BUNDLES
# ============================================

TICKET_BUNDLES = {
    "starter": {
        "tickets": 50,
        "price_usd": 4.99,
        "price_cents": 499,
        "bonus_tickets": 0,
        "total_tickets": 50,
        "value_per_ticket": 0.10,
    },
    "value": {
        "tickets": 100,
        "price_usd": 9.99,
        "price_cents": 999,
        "bonus_tickets": 20,
        "total_tickets": 120,
        "value_per_ticket": 0.083,  # 17% better value
    },
    "premium": {
        "tickets": 250,
        "price_usd": 24.99,
        "price_cents": 2499,
        "bonus_tickets": 75,
        "total_tickets": 325,
        "value_per_ticket": 0.077,  # 23% better value
    },
    "whale": {
        "tickets": 500,
        "price_usd": 49.99,
        "price_cents": 4999,
        "bonus_tickets": 200,
        "total_tickets": 700,
        "value_per_ticket": 0.071,  # 29% better value
    },
}


# ============================================
# COSMETIC BUNDLES
# ============================================

COSMETIC_BUNDLES = {
    "card_back_basic": {
        "type": "card_back",
        "price_usd": 1.99,
        "price_cents": 199,
        "items": ["card_back_flame", "card_back_ice"],
    },
    "card_back_premium": {
        "type": "card_back",
        "price_usd": 4.99,
        "price_cents": 499,
        "items": ["card_back_galaxy", "card_back_neon", "card_back_gold"],
    },
    "profile_bundle": {
        "type": "profile",
        "price_usd": 2.99,
        "price_cents": 299,
        "items": ["profile_frame_silver", "profile_badge_collector"],
    },
    "emote_pack": {
        "type": "emotes",
        "price_usd": 3.99,
        "price_cents": 399,
        "items": ["emote_gg", "emote_fire", "emote_crown", "emote_sad"],
    },
    "ultimate_bundle": {
        "type": "bundle",
        "price_usd": 9.99,
        "price_cents": 999,
        "items": [
            "card_back_legendary",
            "profile_frame_gold",
            "profile_badge_whale",
            "emote_legendary",
            "title_collector",
        ],
        "bonus_gold": 1000,
    },
}


# ============================================
# HYBRID MODEL SUMMARY
# ============================================

class HybridRevenueModel:
    """
    Combined revenue streams for maximum monetization
    while keeping F2P viable
    """
    
    REVENUE_STREAMS = {
        "battle_pass": {
            "price": BattlePassConfig.PRICE_USD,
            "frequency": "seasonal",  # Every 60 days
            "expected_conversion": 0.35,  # 35% of active users
        },
        "vip_subscription": {
            "price": VIPConfig.PRICE_USD,
            "frequency": "monthly",
            "expected_conversion": 0.25,  # 25% of active users
        },
        "pack_sales": {
            "price_range": (2.99, 6.99),
            "frequency": "one-time",
            "expected_monthly_purchases": 0.15,  # 15% buy a pack/month
        },
        "ticket_bundles": {
            "price_range": (4.99, 49.99),
            "frequency": "one-time",
            "expected_monthly_purchases": 0.10,  # 10% buy tickets/month
        },
        "cosmetic_bundles": {
            "price_range": (1.99, 9.99),
            "frequency": "one-time",
            "expected_monthly_purchases": 0.05,  # 5% buy cosmetics/month
        },
        "tier_skips": {
            "price": BattlePassConfig.TIER_SKIP_PRICE_USD,
            "frequency": "seasonal",
            "expected_whale_spend": 50,  # Avg 50 tiers skipped by whales
            "whale_percentage": 0.05,  # 5% are whales
        },
    }
    
    # Player segments
    PLAYER_SEGMENTS = {
        "f2p": {
            "percentage": 0.40,
            "monthly_spend": 0,
            "behavior": "Free track only, earns gold through gameplay",
        },
        "light_spender": {
            "percentage": 0.35,
            "monthly_spend": 5.00,  # Battle Pass only (~$5/month avg)
            "behavior": "Buys Battle Pass each season",
        },
        "dolphin": {
            "percentage": 0.15,
            "monthly_spend": 15.00,
            "behavior": "Battle Pass + VIP + occasional packs",
        },
        "whale": {
            "percentage": 0.05,
            "monthly_spend": 75.00,
            "behavior": "Everything + tier skips + cosmetics",
        },
        "super_whale": {
            "percentage": 0.05,
            "monthly_spend": 150.00,
            "behavior": "Max everything, multiple accounts, gifts to others",
        },
    }
    
    @staticmethod
    def estimate_monthly_revenue(active_users: int) -> Dict:
        """Estimate monthly revenue based on active user count"""
        segments = {
            "f2p": {"percentage": 0.40, "monthly_spend": 0},
            "light_spender": {"percentage": 0.35, "monthly_spend": 5.00},
            "dolphin": {"percentage": 0.15, "monthly_spend": 15.00},
            "whale": {"percentage": 0.05, "monthly_spend": 75.00},
            "super_whale": {"percentage": 0.05, "monthly_spend": 150.00},
        }
        
        revenue = {
            "f2p": 0,
            "light_spender": 0,
            "dolphin": 0,
            "whale": 0,
            "super_whale": 0,
            "total": 0,
        }
        
        for segment, data in segments.items():
            users_in_segment = int(active_users * data["percentage"])
            segment_revenue = users_in_segment * data["monthly_spend"]
            revenue[segment] = segment_revenue
            revenue["total"] += segment_revenue
        
        return revenue


# Pre-calculated revenue estimates
ESTIMATED_MONTHLY_REVENUE = {
    100: HybridRevenueModel.estimate_monthly_revenue(100),
    500: HybridRevenueModel.estimate_monthly_revenue(500),
    1000: HybridRevenueModel.estimate_monthly_revenue(1000),
    5000: HybridRevenueModel.estimate_monthly_revenue(5000),
    10000: HybridRevenueModel.estimate_monthly_revenue(10000),
}


# ============================================
# SEASON MANAGEMENT
# ============================================

class SeasonConfig:
    """Configuration for seasonal content"""
    
    CURRENT_SEASON = 1
    SEASON_NAME = "Launch Season"
    SEASON_THEME = "Origins"
    
    # Season dates (update each season)
    SEASON_START = datetime(2025, 1, 27)  # Update this
    SEASON_END = SEASON_START + timedelta(days=BattlePassConfig.SEASON_LENGTH_DAYS)
    
    # Season-exclusive content
    EXCLUSIVE_CARDS = [
        {
            "name": "Founder's Legend",
            "rarity": "mythic",
            "tier": 30,
            "track": "premium",
            "tradeable": True,
            "returns": False,
        },
        {
            "name": "Season 1 Champion",
            "rarity": "mythic", 
            "tier": 80,
            "track": "premium",
            "tradeable": True,
            "returns": False,
        },
        {
            "name": "Origin Master",
            "rarity": "legendary",
            "tier": 100,
            "track": "premium",
            "tradeable": True,
            "returns": False,
        },
    ]
    
    @staticmethod
    def days_remaining() -> int:
        """Get days remaining in current season"""
        now = datetime.now()
        if now > SeasonConfig.SEASON_END:
            return 0
        return (SeasonConfig.SEASON_END - now).days
    
    @staticmethod
    def is_season_active() -> bool:
        """Check if season is currently active"""
        now = datetime.now()
        return SeasonConfig.SEASON_START <= now <= SeasonConfig.SEASON_END


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_battle_pass_reward(tier: int, is_premium: bool) -> Dict:
    """Get reward for a specific Battle Pass tier"""
    if is_premium:
        rewards = BattlePassConfig.PREMIUM_TRACK_REWARDS
    else:
        rewards = BattlePassConfig.FREE_TRACK_REWARDS
    
    return rewards.get(tier, None)


def calculate_tiers_from_xp(xp: int) -> int:
    """Calculate Battle Pass tier from XP"""
    tier = xp // BattlePassConfig.XP_PER_TIER
    return min(tier, BattlePassConfig.TOTAL_TIERS)


def get_xp_for_next_tier(current_xp: int) -> int:
    """Get XP needed for next tier"""
    current_tier = calculate_tiers_from_xp(current_xp)
    if current_tier >= BattlePassConfig.TOTAL_TIERS:
        return 0  # Already max
    
    next_tier_xp = (current_tier + 1) * BattlePassConfig.XP_PER_TIER
    return next_tier_xp - current_xp


def apply_vip_bonus(base_gold: int, is_vip: bool) -> int:
    """Apply VIP bonus to gold rewards"""
    if is_vip:
        return int(base_gold * VIPConfig.BENEFITS["battle_reward_multiplier"])
    return base_gold


def get_trading_fee(gold_value: int, is_vip: bool) -> int:
    """Calculate trading fee with VIP discount"""
    base_fee_percent = 0.10  # 10%
    
    if is_vip:
        fee_percent = base_fee_percent * VIPConfig.BENEFITS["trading_fee_reduction"]
    else:
        fee_percent = base_fee_percent
    
    return int(gold_value * fee_percent)


def get_ticket_bundle_value(bundle_name: str) -> Dict:
    """Get ticket bundle details"""
    return TICKET_BUNDLES.get(bundle_name, None)
