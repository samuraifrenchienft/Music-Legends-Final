# battle_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple
import random

Stat = Literal["impact", "skill", "longevity", "culture"]
STATS: List[Stat] = ["impact", "skill", "longevity", "culture"]

@dataclass(frozen=True)
class ArtistCard:
    id: str
    name: str
    rarity: str
    impact: int
    skill: int
    longevity: int
    culture: int
    hype: int  # tie-breaker + momentum

    def total_power(self) -> int:
        return self.impact + self.skill + self.longevity + self.culture

    def get_stat(self, stat: Stat) -> int:
        return getattr(self, stat)

@dataclass
class PlayerState:
    user_id: int
    deck: List[ArtistCard]
    score: int = 0
    hype_bonus: int = 0  # momentum, capped

@dataclass
class MatchState:
    match_id: str
    a: PlayerState
    b: PlayerState
    round_index: int = 0
    categories: List[Stat] = None
    last_round_loser: Optional[int] = None  # user_id
    winner_user_id: Optional[int] = None

def pick_category_option_a(match: MatchState) -> Stat:
    """
    Option A:
      - Round 1: random
      - Round 2: loser chooses (handled by caller UI)
      - Round 3: random
    This function returns a random category when applicable.
    """
    return random.choice(STATS)

def resolve_round(
    card_a: ArtistCard,
    card_b: ArtistCard,
    category: Stat,
    hype_bonus_a: int = 0,
    hype_bonus_b: int = 0
) -> Tuple[str, Dict]:
    """
    Returns: ("A"|"B"|"TIE", debug_dict)
    Deterministic tie-breakers:
      1) higher hype
      2) higher total power
      3) coin flip (rare)
    """
    power_a = card_a.get_stat(category) + hype_bonus_a
    power_b = card_b.get_stat(category) + hype_bonus_b

    debug = {
        "category": category,
        "a_stat": card_a.get_stat(category),
        "b_stat": card_b.get_stat(category),
        "a_hype_bonus": hype_bonus_a,
        "b_hype_bonus": hype_bonus_b,
        "a_power": power_a,
        "b_power": power_b,
    }

    if power_a > power_b:
        return "A", debug
    if power_b > power_a:
        return "B", debug

    # Tie-breaker 1: base hype
    if card_a.hype > card_b.hype:
        debug["tiebreak"] = "hype"
        return "A", debug
    if card_b.hype > card_a.hype:
        debug["tiebreak"] = "hype"
        return "B", debug

    # Tie-breaker 2: total power
    if card_a.total_power() > card_b.total_power():
        debug["tiebreak"] = "total_power"
        return "A", debug
    if card_b.total_power() > card_a.total_power():
        debug["tiebreak"] = "total_power"
        return "B", debug

    # Tie-breaker 3: coin flip
    debug["tiebreak"] = "coin_flip"
    return random.choice(["A", "B"]), debug

def apply_momentum(winner: PlayerState, loser: PlayerState) -> None:
    """
    Optional momentum:
      - winner gets +5 hype bonus next round (cap 10)
      - loser hype bonus resets
    """
    winner.hype_bonus = min(10, winner.hype_bonus + 5)
    loser.hype_bonus = 0

def play_match_best_of_3(
    match_id: str,
    deck_a: List[ArtistCard],
    deck_b: List[ArtistCard],
    category_round1: Optional[Stat] = None,
    category_round3: Optional[Stat] = None,
) -> Dict:
    """
    MVP autoplay example (no interactive loser-pick on round 2).
    For production: run each round via Discord UI, letting loser choose round 2 category.
    """
    a = PlayerState(user_id=1, deck=deck_a)
    b = PlayerState(user_id=2, deck=deck_b)

    log = []

    # Round 1
    cat1 = category_round1 or random.choice(STATS)
    r1_w, r1_dbg = resolve_round(a.deck[0], b.deck[0], cat1, a.hype_bonus, b.hype_bonus)
    log.append(("round1", r1_w, r1_dbg))
    if r1_w == "A":
        a.score += 1
        apply_momentum(a, b)
        loser_id = b.user_id
    else:
        b.score += 1
        apply_momentum(b, a)
        loser_id = a.user_id

    # Round 2 (MVP: random; recommended: loser chooses)
    cat2 = random.choice(STATS)
    r2_w, r2_dbg = resolve_round(a.deck[1], b.deck[1], cat2, a.hype_bonus, b.hype_bonus)
    log.append(("round2", r2_w, r2_dbg))
    if r2_w == "A":
        a.score += 1
        apply_momentum(a, b)
        loser_id = b.user_id
    else:
        b.score += 1
        apply_momentum(b, a)
        loser_id = a.user_id

    # If someone already won 2 rounds, stop
    if a.score == 2 or b.score == 2:
        winner = "A" if a.score > b.score else "B"
        return {"match_id": match_id, "winner": winner, "log": log}

    # Round 3
    cat3 = category_round3 or random.choice(STATS)
    r3_w, r3_dbg = resolve_round(a.deck[2], b.deck[2], cat3, a.hype_bonus, b.hype_bonus)
    log.append(("round3", r3_w, r3_dbg))
    if r3_w == "A":
        a.score += 1
    else:
        b.score += 1

    winner = "A" if a.score > b.score else "B"
    return {"match_id": match_id, "winner": winner, "log": log}
