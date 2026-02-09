# config/vip.py
"""
Music Legends - VIP Subscription System
$4.99/month recurring subscription
Daily bonuses, battle perks, cosmetics, quality of life
"""

from datetime import datetime, timedelta
from typing import Dict, List

# ============================================
# VIP SUBSCRIPTION CONFIGURATION
# ============================================

class VIPSubscription:
    """VIP Membership Benefits"""
    
    # Pricing
    MONTHLY_PRICE_USD = 4.99
    MONTHLY_PRICE_CENTS = 499
    MONTHLY_PRICE_TICKETS = 50  # Alternative: pay with tickets
    
    # Subscription tiers (future expansion)
    TIERS = {
        "vip": {
            "name": "VIP Member",
            "price_usd": 4.99,
            "color": "#FFD700",  # Gold
            "badge": "👑",
        },
        # Future tiers:
        # "vip_plus": {"price_usd": 9.99},
        # "legend": {"price_usd": 19.99},
    }


# ============================================
# DAILY BONUSES
# ============================================

class VIPDailyBonuses:
    """Daily bonuses for VIP members"""
    
    DAILY_REWARDS = {
        # Currency bonuses
        "gold_bonus": {
            "base": 100,              # Non-VIP daily claim
            "vip": 200,               # VIP daily claim (+100%)
            "description": "2x Daily Gold Claim",
        },
        
        "ticket_bonus": {
            "base": 0,                # Non-VIP gets 0 daily
            "vip": 1,                 # VIP gets 1 ticket/day
            "monthly_value": 30,      # 30 tickets/month = $3 value
            "description": "+1 Ticket Daily",
        },
        
        # Free pack
        "monthly_pack": {
            "type": "gold_pack",
            "value": 4.99,
            "description": "1 Free Gold Pack/Month",
        },
        
        # XP boost
        "xp_boost": {
            "multiplier": 1.5,        # +50% XP permanently
            "description": "+50% XP from all sources",
        },
    }
    
    @staticmethod
    def calculate_monthly_value() -> float:
        """Calculate total monthly value of VIP"""
        
        # Daily gold: 100 extra/day * 30 days = 3,000 gold
        # 3,000 gold ÷ 500 gold per pack = 6 packs worth
        # 6 packs * $2.99 = $17.94 value
        gold_value = (100 * 30) / 500 * 2.99
        
        # Daily tickets: 30 tickets/month * $0.10/ticket = $3.00 value
        ticket_value = 30 * 0.10
        
        # Monthly pack: $4.99 value
        pack_value = 4.99
        
        # XP boost: Hard to quantify, estimate $2
        xp_value = 2.00
        
        total = gold_value + ticket_value + pack_value + xp_value
        
        return total


# ============================================
# BATTLE BONUSES
# ============================================

class VIPBattleBonuses:
    """Battle-related VIP benefits"""
    
    BONUSES = {
        # Gold rewards
        "battle_gold_multiplier": {
            "base": 1.0,
            "vip": 1.5,               # +50% gold from battles
            "description": "+50% Gold from Battles",
        },
        
        # XP rewards (stacks with daily XP boost)
        "battle_xp_multiplier": {
            "base": 1.0,
            "vip": 1.5,               # +50% XP from battles
            "description": "+50% XP from Battles",
        },
        
        # Wager protection
        "wager_protection": {
            "enabled": True,
            "multiplier": 0.5,        # Lose only 50% of wager
            "effect": "Lose only 50% of wager when defeated",
            "example": "Lose 250g wager → Only lose 125g",
            "description": "50% Wager Protection",
        },
        
        # Battle streak bonus
        "win_streak_bonus": {
            "enabled": True,
            "per_streak": 25,         # +25 gold per win in streak
            "max_streak": 10,         # Max +250 gold
            "description": "Win Streak Bonuses",
        },
    }


# ============================================
# MARKETPLACE BENEFITS
# ============================================

class VIPMarketplaceBenefits:
    """Trading and marketplace VIP perks"""
    
    BENEFITS = {
        # Fees
        "marketplace_fee": {
            "base": 0.10,             # 10% fee for non-VIP
            "vip": 0.00,              # 0% fee for VIP
            "savings_example": "Sell 1,000g card → Save 100g",
            "description": "0% Marketplace Fees",
        },
        
        "trading_fee": {
            "base": 50,               # 50 gold fee per trade
            "vip": 0,                 # Free trades
            "description": "Free Direct Trading",
        },
        
        # Limits
        "daily_trade_limit": {
            "base": 5,                # 5 trades/day for non-VIP
            "vip": 20,                # 20 trades/day for VIP
            "description": "20 Trades/Day (vs 5)",
        },
        
        "marketplace_listings": {
            "base": 3,                # 3 active listings
            "vip": 10,                # 10 active listings
            "description": "10 Marketplace Slots (vs 3)",
        },
        
        # Priority
        "priority_listing": {
            "enabled": True,
            "effect": "Your cards appear at top of marketplace",
            "description": "Priority Marketplace Placement",
        },
    }


# ============================================
# COSMETICS & PRESTIGE
# ============================================

class VIPCosmetics:
    """Exclusive cosmetics and visual perks"""
    
    COSMETICS = {
        # Profile customization
        "username_color": {
            "color": "#FFD700",       # Gold color
            "description": "Gold Username Color",
        },
        
        "profile_badge": {
            "badge": "👑 VIP",
            "position": "next to username",
            "description": "VIP Crown Badge",
        },
        
        "profile_frame": {
            "name": "Gold Frame",
            "rarity": "exclusive",
            "description": "Exclusive Profile Frame",
        },
        
        # Card backs (rotating monthly)
        "monthly_card_back": {
            "rotation": "monthly",
            "exclusive": True,
            "description": "Exclusive Monthly Card Back",
            "examples": [
                "January: Crystal Waves",
                "February: Neon Hearts",
                "March: Electric Storm",
            ],
        },
        
        # Emotes
        "vip_emotes": {
            "count": 5,
            "exclusive": True,
            "description": "5 Exclusive VIP Emotes",
            "list": [
                "🎵 Vibing",
                "💰 Money Rain",
                "👑 Crown Flex",
                "⚡ Hype",
                "🔥 Fire Track",
            ],
        },
        
        # Battle effects
        "battle_entrance": {
            "effect": "Gold particle entrance animation",
            "description": "VIP Battle Entrance",
        },
        
        # Leaderboard
        "leaderboard_highlight": {
            "effect": "Gold highlight on leaderboards",
            "description": "Leaderboard Gold Highlight",
        },
    }


# ============================================
# QUALITY OF LIFE FEATURES
# ============================================

class VIPQualityOfLife:
    """Convenience features for VIP members"""
    
    FEATURES = {
        # Auto-battle
        "favorite_cards": {
            "base": 1,                # Non-VIP: 1 favorite card
            "vip": 5,                 # VIP: 5 favorite cards
            "effect": "Bot auto-rotates through favorites in battles",
            "description": "5 Favorite Card Slots (vs 1)",
        },
        
        # Matchmaking
        "priority_matchmaking": {
            "enabled": True,
            "effect": "Matched with opponents 30 seconds faster",
            "description": "Priority Matchmaking Queue",
        },
        
        # Notifications
        "custom_notifications": {
            "enabled": True,
            "features": [
                "Choose which battle invites to receive",
                "Trading notifications",
                "Marketplace sale alerts",
                "Battle Pass tier-up alerts",
            ],
            "description": "Custom Notification Settings",
        },
        
        # Card management
        "bulk_actions": {
            "enabled": True,
            "actions": [
                "Sell multiple cards at once",
                "List multiple cards on marketplace",
                "Mass trade cards",
            ],
            "description": "Bulk Card Management",
        },
        
        # Statistics
        "advanced_stats": {
            "enabled": True,
            "features": [
                "Detailed battle history",
                "Win rate by card",
                "Gold earning trends",
                "Card collection analytics",
            ],
            "description": "Advanced Statistics Dashboard",
        },
        
        # Support
        "priority_support": {
            "enabled": True,
            "response_time": "Within 24 hours",
            "description": "Priority Customer Support",
        },
    }


# ============================================
# EXCLUSIVE ACCESS
# ============================================

class VIPExclusiveAccess:
    """VIP-only features and events"""
    
    EXCLUSIVE = {
        # Tournaments
        "vip_tournaments": {
            "frequency": "weekly",
            "entry_fee": 0,           # Free for VIP (25 tickets for non-VIP)
            "prize_pool": "Enhanced prizes",
            "description": "Weekly VIP-Only Tournaments",
        },
        
        # Early access
        "early_pack_access": {
            "enabled": True,
            "hours_early": 24,
            "effect": "Access new packs 24h before public release",
            "description": "24h Early Pack Access",
        },
        
        # Exclusive packs
        "vip_monthly_pack": {
            "frequency": "monthly",
            "contents": "VIP-exclusive cards",
            "free": True,
            "description": "Monthly VIP Exclusive Pack",
        },
        
        # Beta features
        "beta_access": {
            "enabled": True,
            "effect": "Test new features before release",
            "description": "Beta Feature Access",
        },
        
        # Server perks
        "server_creation": {
            "base": False,
            "vip": True,
            "effect": "Create custom tournament servers",
            "description": "Custom Server Creation",
        },
    }


# ============================================
# VIP MANAGER
# ============================================

class VIPManager:
    """Manage VIP subscriptions"""
    
    def __init__(self, subscription_start: datetime = None, subscription_end: datetime = None):
        self.subscription_start = subscription_start or datetime.now()
        self.subscription_end = subscription_end or (self.subscription_start + timedelta(days=30))
    
    def days_remaining(self) -> int:
        """Days until subscription expires"""
        remaining = self.subscription_end - datetime.now()
        return max(0, remaining.days)
    
    def is_active(self) -> bool:
        """Check if VIP subscription is active"""
        return datetime.now() < self.subscription_end
    
    def get_gold_multiplier(self) -> float:
        """Get gold multiplier for battles"""
        return VIPBattleBonuses.BONUSES["battle_gold_multiplier"]["vip"]
    
    def get_xp_multiplier(self) -> float:
        """Get XP multiplier"""
        return VIPDailyBonuses.DAILY_REWARDS["xp_boost"]["multiplier"]
    
    def get_wager_protection(self) -> float:
        """Get wager protection multiplier (0.5 = lose only 50%)"""
        return VIPBattleBonuses.BONUSES["wager_protection"]["multiplier"]
    
    def get_marketplace_fee(self) -> float:
        """Get marketplace fee (0.0 for VIP)"""
        return VIPMarketplaceBenefits.BENEFITS["marketplace_fee"]["vip"]
    
    def get_trading_fee(self) -> int:
        """Get trading fee (0 for VIP)"""
        return VIPMarketplaceBenefits.BENEFITS["trading_fee"]["vip"]
    
    def get_daily_trade_limit(self) -> int:
        """Get daily trade limit"""
        return VIPMarketplaceBenefits.BENEFITS["daily_trade_limit"]["vip"]
    
    def get_marketplace_slots(self) -> int:
        """Get marketplace listing slots"""
        return VIPMarketplaceBenefits.BENEFITS["marketplace_listings"]["vip"]
    
    def get_favorite_card_slots(self) -> int:
        """Get favorite card slots"""
        return VIPQualityOfLife.FEATURES["favorite_cards"]["vip"]
    
    def calculate_savings(self, days_active: int = 30) -> Dict:
        """Calculate gold/money saved with VIP"""
        
        # Marketplace fee savings
        # Assume 10 trades/month @ avg 500 gold each
        marketplace_fee_saved = 10 * 500 * 0.10  # 500 gold saved
        
        # Trading fee savings
        # Assume 20 trades/month @ 50 gold each
        trading_fee_saved = 20 * 50  # 1,000 gold saved
        
        # Battle gold bonus
        # Assume 5 battles/day * 30 days * 50 base gold * 0.5 bonus
        battle_bonus = 5 * days_active * 50 * 0.5  # 3,750 gold extra
        
        # Wager protection
        # Assume lose 10 battles/month @ avg 150 wager * 0.5 protection
        wager_saved = 10 * 150 * 0.5  # 750 gold saved
        
        total_gold_value = (
            marketplace_fee_saved +
            trading_fee_saved +
            battle_bonus +
            wager_saved
        )
        
        # Convert to USD (500 gold ≈ $2.99 pack)
        gold_usd_value = (total_gold_value / 500) * 2.99
        
        # Add direct value items
        daily_tickets_value = days_active * 0.10  # $0.10/ticket
        monthly_pack_value = 4.99
        
        total_usd_value = gold_usd_value + daily_tickets_value + monthly_pack_value
        
        return {
            "gold_saved": total_gold_value,
            "gold_usd_value": gold_usd_value,
            "tickets_earned": days_active,
            "tickets_usd_value": daily_tickets_value,
            "monthly_pack_value": monthly_pack_value,
            "total_usd_value": total_usd_value,
            "subscription_cost": VIPSubscription.MONTHLY_PRICE_USD,
            "net_value": total_usd_value - VIPSubscription.MONTHLY_PRICE_USD,
            "value_ratio": total_usd_value / VIPSubscription.MONTHLY_PRICE_USD,
        }
    
    def format_benefits_display(self) -> str:
        """Format VIP benefits for display"""
        output = "👑 **VIP MEMBERSHIP BENEFITS** 👑\n\n"
        output += f"**Price:** ${VIPSubscription.MONTHLY_PRICE_USD}/month\n\n"
        
        output += "**💰 DAILY BONUSES:**\n"
        output += f"• {VIPDailyBonuses.DAILY_REWARDS['gold_bonus']['description']}\n"
        output += f"• {VIPDailyBonuses.DAILY_REWARDS['ticket_bonus']['description']}\n"
        output += f"• {VIPDailyBonuses.DAILY_REWARDS['monthly_pack']['description']}\n"
        output += f"• {VIPDailyBonuses.DAILY_REWARDS['xp_boost']['description']}\n\n"
        
        output += "**⚔️ BATTLE BONUSES:**\n"
        output += f"• {VIPBattleBonuses.BONUSES['battle_gold_multiplier']['description']}\n"
        output += f"• {VIPBattleBonuses.BONUSES['wager_protection']['description']}\n"
        output += f"• {VIPBattleBonuses.BONUSES['win_streak_bonus']['description']}\n\n"
        
        output += "**🏪 MARKETPLACE:**\n"
        output += f"• {VIPMarketplaceBenefits.BENEFITS['marketplace_fee']['description']}\n"
        output += f"• {VIPMarketplaceBenefits.BENEFITS['daily_trade_limit']['description']}\n"
        output += f"• {VIPMarketplaceBenefits.BENEFITS['priority_listing']['description']}\n\n"
        
        output += "**✨ COSMETICS:**\n"
        output += f"• {VIPCosmetics.COSMETICS['username_color']['description']}\n"
        output += f"• {VIPCosmetics.COSMETICS['monthly_card_back']['description']}\n"
        output += f"• {VIPCosmetics.COSMETICS['vip_emotes']['description']}\n\n"
        
        output += "**🎯 EXCLUSIVE ACCESS:**\n"
        output += f"• {VIPExclusiveAccess.EXCLUSIVE['vip_tournaments']['description']}\n"
        output += f"• {VIPExclusiveAccess.EXCLUSIVE['early_pack_access']['description']}\n"
        output += f"• {VIPExclusiveAccess.EXCLUSIVE['beta_access']['description']}\n\n"
        
        # Value calculation
        value = VIPDailyBonuses.calculate_monthly_value()
        output += f"**💎 ESTIMATED VALUE:** ${value:.2f}/month\n"
        output += f"**💳 PRICE:** ${VIPSubscription.MONTHLY_PRICE_USD}/month\n"
        output += f"**📈 VALUE RATIO:** {value / VIPSubscription.MONTHLY_PRICE_USD:.1f}x your money\n"
        
        return output


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_vip_manager() -> VIPManager:
    """Get a VIPManager instance"""
    return VIPManager()


def is_user_vip(user_id: int, db_path: str = "music_legends.db") -> bool:
    """Check if a user has active VIP subscription"""
    import sqlite3
    import os
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            import psycopg2
            from database import _PgConnectionWrapper
            url = database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            conn = _PgConnectionWrapper(psycopg2.connect(url))
        else:
            conn = sqlite3.connect(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT vip_status, vip_expires FROM user_inventory
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

            if not row:
                return False

            status, expires_at = row
            if not status or status != 'active':
                return False

            if expires_at:
                # Check if not expired
                from datetime import datetime
                expiry = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at
                return datetime.utcnow() < expiry

            return status == 'active'
    except Exception:
        return False


def get_user_vip_benefits(user_id: int, db_path: str = "music_legends.db") -> Dict:
    """Get VIP benefits for a user (returns defaults if not VIP)"""
    is_vip = is_user_vip(user_id, db_path)
    
    if is_vip:
        return {
            "is_vip": True,
            "gold_multiplier": VIPBattleBonuses.BONUSES["battle_gold_multiplier"]["vip"],
            "xp_multiplier": VIPDailyBonuses.DAILY_REWARDS["xp_boost"]["multiplier"],
            "wager_protection": VIPBattleBonuses.BONUSES["wager_protection"]["multiplier"],
            "marketplace_fee": VIPMarketplaceBenefits.BENEFITS["marketplace_fee"]["vip"],
            "trading_fee": VIPMarketplaceBenefits.BENEFITS["trading_fee"]["vip"],
            "daily_trade_limit": VIPMarketplaceBenefits.BENEFITS["daily_trade_limit"]["vip"],
            "marketplace_slots": VIPMarketplaceBenefits.BENEFITS["marketplace_listings"]["vip"],
            "favorite_slots": VIPQualityOfLife.FEATURES["favorite_cards"]["vip"],
            "daily_gold": VIPDailyBonuses.DAILY_REWARDS["gold_bonus"]["vip"],
            "daily_tickets": VIPDailyBonuses.DAILY_REWARDS["ticket_bonus"]["vip"],
        }
    else:
        return {
            "is_vip": False,
            "gold_multiplier": VIPBattleBonuses.BONUSES["battle_gold_multiplier"]["base"],
            "xp_multiplier": 1.0,
            "wager_protection": 1.0,  # No protection
            "marketplace_fee": VIPMarketplaceBenefits.BENEFITS["marketplace_fee"]["base"],
            "trading_fee": VIPMarketplaceBenefits.BENEFITS["trading_fee"]["base"],
            "daily_trade_limit": VIPMarketplaceBenefits.BENEFITS["daily_trade_limit"]["base"],
            "marketplace_slots": VIPMarketplaceBenefits.BENEFITS["marketplace_listings"]["base"],
            "favorite_slots": VIPQualityOfLife.FEATURES["favorite_cards"]["base"],
            "daily_gold": VIPDailyBonuses.DAILY_REWARDS["gold_bonus"]["base"],
            "daily_tickets": VIPDailyBonuses.DAILY_REWARDS["ticket_bonus"]["base"],
        }


def apply_vip_gold_bonus(base_gold: int, user_id: int, db_path: str = "music_legends.db") -> int:
    """Apply VIP gold bonus to a base amount"""
    benefits = get_user_vip_benefits(user_id, db_path)
    return int(base_gold * benefits["gold_multiplier"])


def apply_vip_xp_bonus(base_xp: int, user_id: int, db_path: str = "music_legends.db") -> int:
    """Apply VIP XP bonus to a base amount"""
    benefits = get_user_vip_benefits(user_id, db_path)
    return int(base_xp * benefits["xp_multiplier"])


def apply_vip_wager_protection(wager_amount: int, user_id: int, db_path: str = "music_legends.db") -> int:
    """Apply VIP wager protection (returns amount to actually lose)"""
    benefits = get_user_vip_benefits(user_id, db_path)
    return int(wager_amount * benefits["wager_protection"])
