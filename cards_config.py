"""Shared card constants used across cogs."""

# Canonical rarity emoji map — use this everywhere instead of defining inline
RARITY_EMOJI = {
    "common": "⚪",      # ⚪
    "rare": "🔵",     # 🔵
    "epic": "🟣",     # 🟣
    "legendary": "⭐",    # ⭐
    "mythic": "🔴",   # 🔴
}

# Battle power bonuses by rarity
RARITY_BONUS = {
    "common": 0,
    "rare": 5,
    "epic": 10,
    "legendary": 20,
    "mythic": 35,
}

# Tier emoji map
TIER_EMOJI = {
    "community": "📦",  # 📦
    "gold": "🥇",       # 🥇
    "platinum": "💎",   # 💎
}


def compute_card_power(card: dict) -> int:
    """Compute battle power directly from card DB stats.
    Formula: average of 5 stats (0-100 each) + rarity bonus -> range 0-135."""
    base = ((card.get('impact', 50) or 50) +
            (card.get('skill', 50) or 50) +
            (card.get('longevity', 50) or 50) +
            (card.get('culture', 50) or 50) +
            (card.get('hype', 50) or 50)) // 5
    rarity = (card.get('rarity') or 'common').lower()
    return base + RARITY_BONUS.get(rarity, 0)


def compute_team_power(champ_power: int, support_powers: list) -> int:
    """Weighted team power: champion counts double.
    Formula: (champ*2 + sum(supports)) / (2 + len(supports))"""
    if not support_powers:
        return champ_power
    return (champ_power * 2 + sum(support_powers)) // (2 + len(support_powers))
