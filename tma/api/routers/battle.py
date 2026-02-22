"""Battle router — share-link PvP battles."""
import json
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from tma.api.auth import get_tg_user
from database import get_db
from config.cards import compute_card_power, compute_team_power
from battle_engine import BattleEngine
from discord_cards import ArtistCard

router = APIRouter(prefix="/api/battle", tags=["battle"])


class ChallengeRequest(BaseModel):
    opponent_telegram_id: int
    pack_id: str
    wager_tier: str = "casual"


class AcceptRequest(BaseModel):
    pack_id: str


def _make_battle_id() -> str:
    return secrets.token_hex(3).upper()


def _card_to_artist(card: dict) -> ArtistCard:
    """Build a minimal ArtistCard from a card dict (power via p1_override/p2_override)."""
    return ArtistCard(
        card_id=card.get("card_id", "unknown"),
        artist=card.get("name", "Unknown"),
        song=card.get("title", "Unknown"),
        youtube_url=card.get("youtube_url", ""),
        youtube_id="",
        view_count=0,
        thumbnail=card.get("image_url", ""),
        rarity=card.get("rarity", "common"),
    )


def _run_battle(db, challenger_id: int, opponent_id: int,
                c_pack: dict, o_pack: dict, wager_tier: str) -> dict:
    """Execute battle and distribute rewards. Rewards are distributed first —
    they must never be orphaned by a downstream failure."""
    c_cards = sorted(c_pack.get("cards", []), key=compute_card_power, reverse=True)
    o_cards = sorted(o_pack.get("cards", []), key=compute_card_power, reverse=True)

    if not c_cards or not o_cards:
        return {"error": "Empty pack", "winner": 0}

    c_champ, o_champ = c_cards[0], o_cards[0]
    c_power = compute_team_power(
        compute_card_power(c_champ), [compute_card_power(c) for c in c_cards[1:5]]
    )
    o_power = compute_team_power(
        compute_card_power(o_champ), [compute_card_power(c) for c in o_cards[1:5]]
    )

    result = BattleEngine.execute_battle(
        _card_to_artist(c_champ),
        _card_to_artist(o_champ),
        wager_tier,
        p1_override=c_power,
        p2_override=o_power,
    )

    p1, p2 = result["player1"], result["player2"]

    # Distribute BEFORE returning — gold must not be orphaned
    db.update_user_economy(challenger_id, gold_change=p1["gold_reward"])
    db.update_user_economy(opponent_id,   gold_change=p2["gold_reward"])

    return {
        "winner":      result["winner"],
        "is_critical": result.get("is_critical", False),
        "challenger": {
            "name":        c_champ.get("name"),
            "power":       c_power,
            "gold_reward": p1["gold_reward"],
            "xp_reward":   p1.get("xp_reward", 0),
            "image_url":   c_champ.get("image_url"),
            "rarity":      c_champ.get("rarity"),
        },
        "opponent": {
            "name":        o_champ.get("name"),
            "power":       o_power,
            "gold_reward": p2["gold_reward"],
            "xp_reward":   p2.get("xp_reward", 0),
            "image_url":   o_champ.get("image_url"),
            "rarity":      o_champ.get("rarity"),
        },
    }


@router.post("/challenge")
async def create_challenge(body: ChallengeRequest, tg: dict = Depends(get_tg_user)):
    """Challenger picks pack and creates a pending battle. Returns shareable link."""
    db = get_db()
    challenger = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    packs = db.get_user_purchased_packs(challenger["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(403, "You don't own that pack")

    battle_id = _make_battle_id()
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pending_tma_battles "
            "(battle_id, challenger_id, opponent_id, challenger_pack, wager_tier, status, expires_at) "
            "VALUES (?, ?, ?, ?, ?, 'waiting', ?)",
            (battle_id, challenger["user_id"], body.opponent_telegram_id,
             body.pack_id, body.wager_tier, expires)
        )
        conn.commit()

    import os
    tma_url = os.environ.get("TMA_URL", "https://t.me/MusicLegendsBot/app")
    link = f"{tma_url}?startapp=battle_{battle_id}"

    # Notify opponent (best-effort)
    try:
        from tma.api.bot.handlers import notify_battle_challenge
        await notify_battle_challenge(
            opponent_telegram_id=body.opponent_telegram_id,
            challenger_name=tg.get("username") or tg.get("first_name", "Someone"),
            battle_id=battle_id,
            wager_tier=body.wager_tier,
            link=link,
        )
    except Exception as e:
        print(f"[BATTLE] Notification failed (non-critical): {e}")

    return {"battle_id": battle_id, "link": link, "status": "waiting"}


@router.post("/{battle_id}/accept")
async def accept_challenge(battle_id: str, body: AcceptRequest,
                           tg: dict = Depends(get_tg_user)):
    """Opponent selects pack and battle executes immediately."""
    db = get_db()
    opponent = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT battle_id, challenger_id, challenger_pack, wager_tier, status, expires_at "
            "FROM pending_tma_battles WHERE battle_id = ?",
            (battle_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Battle not found")
        cols = [d[0] for d in cursor.description]
        battle = dict(zip(cols, row))

    if battle["status"] != "waiting":
        raise HTTPException(400, f"Battle is already {battle['status']}")
    if datetime.utcnow().isoformat() > (battle.get("expires_at") or "9999"):
        raise HTTPException(400, "Battle link has expired")

    packs = db.get_user_purchased_packs(opponent["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(403, "You don't own that pack")

    c_packs = db.get_user_purchased_packs(battle["challenger_id"])
    c_pack = next((p for p in c_packs if str(p.get("pack_id")) == battle["challenger_pack"]), None)
    o_pack = next((p for p in packs if str(p.get("pack_id")) == body.pack_id), None)

    if not c_pack or not o_pack:
        raise HTTPException(400, "Could not resolve packs for battle")

    result = _run_battle(db, battle["challenger_id"], opponent["user_id"],
                         c_pack, o_pack, battle["wager_tier"])

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_tma_battles "
            "SET status='complete', opponent_id=?, opponent_pack=?, result_json=? "
            "WHERE battle_id=?",
            (opponent["user_id"], body.pack_id, json.dumps(result), battle_id)
        )
        conn.commit()

    # Notify challenger (best-effort)
    try:
        from tma.api.bot.handlers import notify_battle_result
        await notify_battle_result(
            challenger_id=battle["challenger_id"],
            result=result,
            opponent_name=tg.get("username") or tg.get("first_name", "Opponent"),
            battle_id=battle_id,
        )
    except Exception as e:
        print(f"[BATTLE] Result notification failed (non-critical): {e}")

    return {"battle_id": battle_id, "result": result}


@router.get("/{battle_id}")
def get_battle(battle_id: str, tg: dict = Depends(get_tg_user)):
    """Poll for battle status/result."""
    db = get_db()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, result_json FROM pending_tma_battles WHERE battle_id = ?",
            (battle_id,)
        )
        row = cursor.fetchone()
    if not row:
        raise HTTPException(404, "Battle not found")
    status, result_json = row
    return {
        "battle_id": battle_id,
        "status":    status,
        "result":    json.loads(result_json) if result_json else None,
    }
