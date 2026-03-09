"""Battle router — share-link PvP battles."""
import json
import secrets
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from tma.api.auth import get_tg_user
from database import get_db
from cards_config import compute_card_power, compute_team_power
from battle_engine import BattleEngine
from discord_cards import ArtistCard
from models import PendingTmaBattle, User

router = APIRouter(prefix="/api/battle", tags=["battle"])


class ChallengeRequest(BaseModel):
    opponent_telegram_id: int
    pack_id: str | None = None
    card_id: str | None = None
    wager_tier: str = "casual"


class AcceptRequest(BaseModel):
    pack_id: str | None = None
    card_id: str | None = None


def _make_battle_id() -> str:
    return secrets.token_hex(3).upper()


def _build_tma_battle_link(battle_id: str) -> str:
    """
    Build a safe Mini App deep-link for battle acceptance.
    Uses configured TMA_URL when present; otherwise falls back to current bot username.
    """
    raw = (os.environ.get("TMA_URL") or "").strip()
    if not raw:
        bot_username = (os.environ.get("TELEGRAM_BOT_USERNAME") or "MusicLegendsBot").lstrip("@")
        raw = f"https://t.me/{bot_username}"
    elif raw.startswith("t.me/"):
        raw = f"https://{raw}"
    elif raw.startswith("http://"):
        raw = "https://" + raw[len("http://") :]

    parsed = urlparse(raw)
    if parsed.scheme != "https":
        bot_username = (os.environ.get("TELEGRAM_BOT_USERNAME") or "MusicLegendsBot").lstrip("@")
        parsed = urlparse(f"https://t.me/{bot_username}")

    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    q["startapp"] = f"battle_{battle_id}"
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(q), parsed.fragment))


def _build_bot_start_link(battle_id: str) -> str:
    """Universal fallback link that always opens bot chat with /start payload."""
    bot_username = (os.environ.get("TELEGRAM_BOT_USERNAME") or "MusicLegendsBot").lstrip("@")
    return f"https://t.me/{bot_username}?start=battle_{battle_id}"


def _extract_telegram_id(db, user: User) -> int | None:
    tag = (user.discord_tag or "").strip()
    if tag.startswith("telegram:"):
        try:
            return int(tag.split(":", 1)[1])
        except Exception:
            return None
    try:
        uid = int(str(user.user_id))
        if uid >= db._TG_OFFSET:
            return uid - db._TG_OFFSET
    except Exception:
        return None
    return None


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


def _build_collection_pack(db, user_id: str, focus_card_id: str | None = None) -> dict | None:
    """
    Build a synthetic battle pack from a user's collection.
    If focus_card_id is provided, it is forced as champion and surrounded by strongest supports.
    """
    cards = db.get_user_collection(user_id) or []
    if not cards:
        return None

    # Deduplicate by card_id and sort strongest-first.
    unique = {}
    for c in cards:
        cid = str(c.get("card_id") or "")
        if cid and cid not in unique:
            unique[cid] = c
    ordered = sorted(unique.values(), key=compute_card_power, reverse=True)
    if not ordered:
        return None

    selected = None
    if focus_card_id:
        selected = next((c for c in ordered if str(c.get("card_id")) == str(focus_card_id)), None)
        if not selected:
            return None
        supports = [c for c in ordered if str(c.get("card_id")) != str(focus_card_id)][:4]
        squad = [selected] + supports
        name = selected.get("name") or "Selected Card"
        pack_id = f"card:{focus_card_id}"
        pack_name = f"{name} Squad"
    else:
        squad = ordered[:5]
        pack_id = f"collection:{user_id}"
        pack_name = "My Collection Squad"

    return {
        "pack_id": pack_id,
        "pack_name": pack_name,
        "pack_tier": "community",
        "genre": "Music",
        "cards": squad,
    }


def _resolve_selected_pack(db, user_id: str, pack_id: str | None, card_id: str | None) -> tuple[str, dict]:
    """
    Resolve battle selection from either purchased pack_id or selected card_id.
    Returns (selection_ref, pack_payload).
    """
    if pack_id:
        # Backward-compatible card-first selection for older clients that send card ids via pack_id.
        if str(pack_id).startswith("card:"):
            parsed_card_id = str(pack_id).split(":", 1)[1]
            pack = _build_collection_pack(db, user_id, focus_card_id=parsed_card_id)
            if not pack:
                raise HTTPException(403, "You don't own that card")
            return str(pack_id), pack
        if str(pack_id).startswith("collection:"):
            pack = _build_collection_pack(db, user_id)
            if not pack:
                raise HTTPException(403, "You don't have cards for battle")
            return str(pack_id), pack

        packs = db.get_user_purchased_packs(user_id)
        resolved = next((p for p in packs if str(p.get("pack_id")) == str(pack_id)), None)
        if not resolved:
            raise HTTPException(403, "You don't own that pack")
        return str(pack_id), resolved

    if card_id:
        pack = _build_collection_pack(db, user_id, focus_card_id=card_id)
        if not pack:
            raise HTTPException(403, "You don't own that card")
        return f"card:{card_id}", pack

    raise HTTPException(400, "Select a pack or a card")


def _resolve_pack_from_ref(db, user_id: str, selection_ref: str) -> dict | None:
    """Resolve a stored battle selection reference into a concrete pack payload."""
    if selection_ref.startswith("card:"):
        card_id = selection_ref.split(":", 1)[1]
        return _build_collection_pack(db, user_id, focus_card_id=card_id)
    if selection_ref.startswith("collection:"):
        return _build_collection_pack(db, user_id)

    packs = db.get_user_purchased_packs(user_id)
    return next((p for p in packs if str(p.get("pack_id")) == str(selection_ref)), None)


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
            "youtube_url": c_champ.get("youtube_url"),
            "rarity":      c_champ.get("rarity"),
        },
        "opponent": {
            "name":        o_champ.get("name"),
            "power":       o_power,
            "gold_reward": p2["gold_reward"],
            "xp_reward":   p2.get("xp_reward", 0),
            "image_url":   o_champ.get("image_url"),
            "youtube_url": o_champ.get("youtube_url"),
            "rarity":      o_champ.get("rarity"),
        },
    }


@router.post("/challenge")
async def create_challenge(body: ChallengeRequest, tg: dict = Depends(get_tg_user)):
    """Challenger picks pack and creates a pending battle. Returns shareable link."""
    db = get_db()
    challenger = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    selection_ref, _challenger_pack = _resolve_selected_pack(
        db, challenger["user_id"], body.pack_id, body.card_id
    )

    battle_id = _make_battle_id()
    expires = datetime.utcnow() + timedelta(hours=24)

    # Ensure opponent placeholder user exists
    opponent_user = db.get_or_create_telegram_user(body.opponent_telegram_id)

    session = db.get_session()
    try:
        battle_row = PendingTmaBattle(
            battle_id=battle_id,
            challenger_id=challenger["user_id"],
            opponent_id=opponent_user["user_id"],
            challenger_pack=selection_ref,
            wager_tier=body.wager_tier,
            status="waiting",
            expires_at=expires,
        )
        session.add(battle_row)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Failed to create battle: {e}")
    finally:
        session.close()

    mini_app_link = _build_tma_battle_link(battle_id)
    link = _build_bot_start_link(battle_id)

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

    return {
        "battle_id": battle_id,
        "link": link,
        "mini_app_link": mini_app_link,
        "status": "waiting",
        "expires_at": expires.isoformat(),
    }


@router.get("/incoming")
def list_incoming_challenges(tg: dict = Depends(get_tg_user)):
    """List waiting battle challenges for the current Telegram user."""
    db = get_db()
    me = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    now = datetime.utcnow()

    session = db.get_session()
    try:
        rows = (
            session.query(PendingTmaBattle)
            .filter(PendingTmaBattle.opponent_id == str(me["user_id"]))
            .filter(PendingTmaBattle.status == "waiting")
            .order_by(desc(PendingTmaBattle.created_at))
            .limit(50)
            .all()
        )
        valid = [r for r in rows if not r.expires_at or r.expires_at > now]
        challenger_ids = list({str(r.challenger_id) for r in valid})
        users = (
            session.query(User).filter(User.user_id.in_(challenger_ids)).all()
            if challenger_ids else []
        )
        u_map = {str(u.user_id): u for u in users}

        out = []
        for r in valid:
            cu = u_map.get(str(r.challenger_id))
            challenger_name = (cu.username if cu and cu.username else f"user_{r.challenger_id}")
            out.append({
                "battle_id": r.battle_id,
                "challenger_user_id": str(r.challenger_id),
                "challenger_username": challenger_name,
                "challenger_telegram_id": _extract_telegram_id(db, cu) if cu else None,
                "wager_tier": r.wager_tier or "casual",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            })
        return {"challenges": out}
    finally:
        session.close()


@router.post("/{battle_id}/accept")
async def accept_challenge(battle_id: str, body: AcceptRequest,
                           tg: dict = Depends(get_tg_user)):
    """Opponent selects pack and battle executes immediately."""
    db = get_db()
    opponent = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    session = db.get_session()
    try:
        battle_row = session.query(PendingTmaBattle).filter_by(battle_id=battle_id).first()
        if not battle_row:
            raise HTTPException(404, "Battle not found")
        battle = {
            "battle_id":      battle_row.battle_id,
            "challenger_id":  battle_row.challenger_id,
            "challenger_pack": battle_row.challenger_pack,
            "wager_tier":     battle_row.wager_tier,
            "status":         battle_row.status,
            "expires_at":     battle_row.expires_at,
        }
    finally:
        session.close()

    if battle["status"] != "waiting":
        raise HTTPException(400, f"Battle is already {battle['status']}")
    if battle["expires_at"] and datetime.utcnow() > battle["expires_at"]:
        raise HTTPException(400, "Battle link has expired")

    opponent_ref, o_pack = _resolve_selected_pack(
        db, opponent["user_id"], body.pack_id, body.card_id
    )
    c_pack = _resolve_pack_from_ref(db, battle["challenger_id"], str(battle["challenger_pack"]))

    if not c_pack or not o_pack:
        raise HTTPException(400, "Could not resolve battle squads")

    result = _run_battle(db, battle["challenger_id"], opponent["user_id"],
                         c_pack, o_pack, battle["wager_tier"])

    session = db.get_session()
    try:
        battle_row = session.query(PendingTmaBattle).filter_by(battle_id=battle_id).first()
        if battle_row:
            battle_row.status = "complete"
            battle_row.opponent_id = opponent["user_id"]
            battle_row.opponent_pack = opponent_ref
            battle_row.result_json = json.dumps(result)
            session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

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


@router.post("/{battle_id}/cancel")
def cancel_challenge(battle_id: str, tg: dict = Depends(get_tg_user)):
    """Cancel a waiting challenge (challenger or opponent)."""
    db = get_db()
    actor = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    actor_id = str(actor["user_id"])

    session = db.get_session()
    try:
        row = session.query(PendingTmaBattle).filter_by(battle_id=battle_id).first()
        if not row:
            raise HTTPException(404, "Battle not found")
        if row.status != "waiting":
            raise HTTPException(400, f"Battle is already {row.status}")
        if actor_id not in {str(row.challenger_id), str(row.opponent_id)}:
            raise HTTPException(403, "Not allowed to cancel this battle")
        row.status = "cancelled"
        session.commit()
        return {"success": True, "battle_id": battle_id, "status": "cancelled"}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Failed to cancel battle: {e}")
    finally:
        session.close()


@router.get("/{battle_id}")
def get_battle(battle_id: str, tg: dict = Depends(get_tg_user)):
    """Poll for battle status/result."""
    db = get_db()
    session = db.get_session()
    try:
        row = session.query(PendingTmaBattle).filter_by(battle_id=battle_id).first()
        if not row:
            raise HTTPException(404, "Battle not found")
        status = row.status
        if status == "waiting" and row.expires_at and datetime.utcnow() > row.expires_at:
            status = "expired"
        return {
            "battle_id": battle_id,
            "status":    status,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "result":    json.loads(row.result_json) if row.result_json else None,
        }
    finally:
        session.close()
