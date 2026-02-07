# config/economy.py
"""
Music Legends - Complete Economy Configuration
All pricing, rewards, ranks, and economy constants in one place
"""

# ============================================
# DAILY STREAK REWARDS
# ============================================

DAILY_REWARDS = {
    1: {"gold": 100, "tickets": 0},      # Day 1
    3: {"gold": 150, "tickets": 0},      # Day 3 streak bonus
    7: {"gold": 300, "tickets": 1},      # Week streak
    14: {"gold": 600, "tickets": 2},     # Two week streak
    30: {"gold": 1100, "tickets": 5},    # Month streak
}

# Default daily reward (for days not in DAILY_REWARDS)
DEFAULT_DAILY = {"gold": 100, "tickets": 0}

# ============================================
# BATTLE WAGER SYSTEM
# ============================================

BATTLE_WAGERS = {
    "casual": {
        "wager": 50,
        "win_bonus": 50,      # Total win = wager + bonus = 100
        "win_xp": 25,
        "loss_xp": 5,
        "tie_gold": 25,
        "tie_xp": 10,
        "consolation_gold": 10  # Loser gets this back
    },
    "standard": {
        "wager": 100,
        "win_bonus": 75,      # Total win = 175
        "win_xp": 38,
        "loss_xp": 5,
        "tie_gold": 25,
        "tie_xp": 10,
        "consolation_gold": 10
    },
    "high": {
        "wager": 250,
        "win_bonus": 100,     # Total win = 350
        "win_xp": 50,
        "loss_xp": 5,
        "tie_gold": 25,
        "tie_xp": 10,
        "consolation_gold": 10
    },
    "extreme": {
        "wager": 500,
        "win_bonus": 150,     # Total win = 650
        "win_xp": 75,
        "loss_xp": 5,
        "tie_gold": 25,
        "tie_xp": 10,
        "consolation_gold": 10
    }
}

# Battle mechanics
BATTLE_CRIT_CHANCE = 0.15  # 15% crit chance
BATTLE_CRIT_MULTIPLIER = 1.5  # 50% bonus on crit

# ============================================
# RANK PROGRESSION SYSTEM
# ============================================

RANKS = {
    "Bronze": {
        "order": 1,
        "xp_required": 0,
        "wins_required": 0,
        "color": 0xCD7F32,  # Bronze color
        "emoji": "🥉"
    },
    "Silver": {
        "order": 2,
        "xp_required": 100,
        "wins_required": 10,
        "color": 0xC0C0C0,  # Silver color
        "emoji": "🥈"
    },
    "Gold": {
        "order": 3,
        "xp_required": 250,
        "wins_required": 25,
        "color": 0xFFD700,  # Gold color
        "emoji": "🥇"
    },
    "Platinum": {
        "order": 4,
        "xp_required": 500,
        "wins_required": 50,
        "color": 0xE5E4E2,  # Platinum color
        "emoji": "💎"
    },
    "Diamond": {
        "order": 5,
        "xp_required": 1000,
        "wins_required": 100,
        "color": 0xB9F2FF,  # Diamond color
        "emoji": "💠"
    },
    "Legend": {
        "order": 6,
        "xp_required": 2500,
        "wins_required": 250,
        "color": 0xFF4500,  # Legend color (orange-red)
        "emoji": "👑"
    }
}

# ============================================
# PACK PRICING
# ============================================

PACK_PRICING = {
    "community": {
        "buy_usd": 2.99,
        "buy_usd_cents": 299,
        "buy_gold": 500,
        "buy_tickets": None,      # Cannot buy with tickets
        "create_usd": None,       # Dev only
        "create_tickets": None,
        "cards_per_pack": 5,
        "bonus_gold": 100,
        "bonus_tickets": 0,
        "marketplace": True,
        "description": "5 cards, mostly Common/Rare + 100 bonus gold"
    },
    "gold": {
        "buy_usd": 4.99,
        "buy_usd_cents": 499,
        "buy_gold": None,         # Cannot buy with gold directly
        "buy_tickets": 100,       # OR buy with 100 tickets
        "create_usd": 6.99,
        "create_usd_cents": 699,
        "create_gold": 2000,      # Create with 2,000 gold + 10 tickets
        "create_tickets": 150,    # OR create with 150 tickets only
        "create_gold_tickets": 10, # Tickets needed when using gold to create
        "cards_per_pack": 5,
        "bonus_gold": 250,
        "bonus_tickets": 2,
        "marketplace": True,
        "description": "5 cards, guaranteed Rare+, chance for Legendary + 250 gold & 2 tickets"
    },
    "platinum": {
        "buy_usd": 6.99,
        "buy_usd_cents": 699,
        "buy_gold": 2500,
        "buy_tickets": 200,
        "create_usd": None,       # Not creator-creatable
        "create_tickets": None,
        "cards_per_pack": 10,
        "bonus_gold": 500,
        "bonus_tickets": 5,
        "marketplace": True,
        "description": "10 premium cards, top-tier artists, bonus gold & tickets"
    }
}

# ============================================
# CARD SELLING PRICES
# ============================================

CARD_SELL_PRICES = {
    "common": 10,
    "Common": 10,
    "rare": 25,
    "Rare": 25,
    "epic": 75,
    "Epic": 75,
    "legendary": 200,
    "Legendary": 200
}

# Duplicate bonus multiplier
DUPLICATE_BONUS = 1.5  # +50% if duplicate

# ============================================
# NEW PLAYER STARTING RESOURCES
# ============================================

NEW_PLAYER_GOLD = 500
NEW_PLAYER_TICKETS = 0
NEW_PLAYER_DUST = 0
NEW_PLAYER_GEMS = 0

# ============================================
# TRADING SYSTEM
# ============================================

TRADING = {
    "direct": {
        "enabled": True,
        "fee_percent": 10,        # 10% gold fee (both players)
        "cooldown_hours": 24,     # Cannot trade same card back within 24h
        "max_trades_per_day": 5
    },
    "marketplace": {
        "enabled": True,
        "listing_fee_percent": 5,  # 5% gold to list
        "sale_fee_percent": 10,    # 10% of sale price
        "max_active_listings": 10
    }
}

# ============================================
# GOLD (Server-Specific Currency)
# ============================================

GOLD_CONFIG = {
    "server_specific": True,      # Gold doesn't transfer between servers
    "can_buy_with_usd": False,    # Cannot purchase gold directly
    "daily_income_target": 450,   # Active player daily income
    "uses": [
        "battle_wagers",
        "community_packs",
        "server_tournaments",
        "basic_cosmetics",
        "trading_fees"
    ]
}

# ============================================
# TICKETS (Global Currency)
# ============================================

TICKETS_CONFIG = {
    "global": True,               # Tickets transfer between servers
    "usd_per_ticket": 0.10,       # $1 = 10 tickets
    "f2p_monthly_rate": 10,       # ~10 tickets/month from streaks
    "uses": [
        "gold_packs_buy",         # 100 tickets
        "gold_packs_create",      # 150 tickets
        "premium_tournaments",
        "exclusive_cosmetics",
        "boosters",
        "server_transfer"         # 50 tickets to keep cards
    ]
}

# ============================================
# DAILY QUESTS (Future Implementation)
# ============================================

DAILY_QUESTS = {
    "battle_3": {
        "description": "Win 3 battles",
        "reward_gold": 100,
        "reward_xp": 25
    },
    "collect_5": {
        "description": "Collect 5 cards",
        "reward_gold": 100,
        "reward_xp": 25
    },
    "trade_1": {
        "description": "Complete 1 trade",
        "reward_gold": 100,
        "reward_xp": 25
    }
}

# Total daily quest gold: 300

# ============================================
# FIRST WIN BONUS
# ============================================

FIRST_WIN_BONUS = {
    "gold": 50,
    "xp": 10,
    "resets": "daily"  # Resets at midnight UTC
}

# ============================================
# TIER TO RARITY MAPPING
# ============================================

TIER_TO_RARITY = {
    "community": "Common",
    "gold": "Rare",
    "platinum": "Epic",
    "legendary": "Legendary"
}

RARITY_TO_TIER = {
    "Common": "community",
    "common": "community",
    "Rare": "gold",
    "rare": "gold",
    "Epic": "platinum",
    "epic": "platinum",
    "Legendary": "legendary",
    "legendary": "legendary"
}

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_daily_reward(streak_days: int) -> dict:
    """Get daily reward based on streak length"""
    # Check for milestone days
    if streak_days in DAILY_REWARDS:
        return DAILY_REWARDS[streak_days]
    
    # Check for closest milestone below current streak
    milestones = sorted(DAILY_REWARDS.keys(), reverse=True)
    for milestone in milestones:
        if streak_days >= milestone:
            return DAILY_REWARDS[milestone]
    
    return DEFAULT_DAILY


def get_rank(xp: int, wins: int) -> str:
    """Determine player rank based on XP and wins"""
    current_rank = "Bronze"
    
    for rank_name, requirements in RANKS.items():
        if xp >= requirements["xp_required"] and wins >= requirements["wins_required"]:
            if RANKS[rank_name]["order"] > RANKS[current_rank]["order"]:
                current_rank = rank_name
    
    return current_rank


def get_next_rank(current_rank: str) -> dict:
    """Get requirements for next rank"""
    current_order = RANKS[current_rank]["order"]
    
    for rank_name, requirements in RANKS.items():
        if requirements["order"] == current_order + 1:
            return {
                "name": rank_name,
                "xp_required": requirements["xp_required"],
                "wins_required": requirements["wins_required"]
            }
    
    return None  # Already at max rank


def get_card_sell_price(rarity: str, is_duplicate: bool = False) -> int:
    """Get gold value for selling a card"""
    base_price = CARD_SELL_PRICES.get(rarity, 10)
    
    if is_duplicate:
        return int(base_price * DUPLICATE_BONUS)
    
    return base_price


def calculate_battle_rewards(wager_type: str, result: str) -> dict:
    """Calculate rewards for battle outcome"""
    wager = BATTLE_WAGERS.get(wager_type, BATTLE_WAGERS["casual"])
    
    if result == "win":
        return {
            "gold": wager["wager"] + wager["win_bonus"],
            "xp": wager["win_xp"],
            "wager_returned": True
        }
    elif result == "loss":
        return {
            "gold": wager["consolation_gold"],
            "xp": wager["loss_xp"],
            "gold_lost": wager["wager"],
            "wager_returned": False
        }
    elif result == "tie":
        return {
            "gold": wager["tie_gold"],
            "xp": wager["tie_xp"],
            "wager_returned": True
        }
    
    return {"gold": 0, "xp": 0}


def calculate_trade_fee(gold_value: int, trade_type: str = "direct") -> int:
    """Calculate trading fee"""
    if trade_type == "direct":
        return int(gold_value * TRADING["direct"]["fee_percent"] / 100)
    elif trade_type == "listing":
        return int(gold_value * TRADING["marketplace"]["listing_fee_percent"] / 100)
    elif trade_type == "sale":
        return int(gold_value * TRADING["marketplace"]["sale_fee_percent"] / 100)
    
    return 0
