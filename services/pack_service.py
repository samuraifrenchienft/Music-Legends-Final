# services/pack_service.py
"""
Pack service — tier rolling utilities for pack opening.
"""
import random
from typing import Optional, Dict

SILVER_ODDS = {
    "S": 0.01,
    "A": 0.05,
    "B": 0.14,
    "C": 0.30,
    "D": 0.50,
}

GOLD_ODDS = {
    "S": 0.03,
    "A": 0.10,
    "B": 0.20,
    "C": 0.32,
    "D": 0.35,
}

PACK_ODDS = {
    "silver": SILVER_ODDS,
    "gold": GOLD_ODDS,
}


def roll_tier(pack_type: str = "silver", odds_override: Optional[Dict[str, float]] = None) -> str:
    """Roll a card tier based on pack odds."""
    odds = odds_override or PACK_ODDS.get(pack_type, SILVER_ODDS)
    tiers = list(odds.keys())
    weights = list(odds.values())
    return random.choices(tiers, weights=weights, k=1)[0]
