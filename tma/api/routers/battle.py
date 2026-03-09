"""Battle router — share-link PvP battles."""
import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
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
    idempotency_key: str | None = None


class AcceptRequest(BaseModel):
    pack_id: str
    idempotency_key: str | None = None


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


def _get_idempotency_key(request: Request, body_key: str | None = None) -> str | None:
    key = request.headers.get("Idempotency-Key") or body_key
    if not key:
        return None
    key = key.strip()
    if not key:
        return None
    if len(key) > 128:
        raise HTTPException(400, "Idempotency key is too long")
    return key


def _idempotency_reserve_or_replay(db, user_id: int, action: str, key: str | None, payload: dict):
    if not key:
        return None
    reservation = db.reserve_idempotency_key(user_id, action, key, payload)
    state = reservation.get("state")
    if state == "payload_conflict":
        raise HTTPException(409, "Idempotency key reuse with different payload")
    if state == "in_progress":
        raise HTTPException(409, "Request with this idempotency key is already in progress")
    if state == "replay":
        return JSONResponse(content=reservation["response"], status_code=reservation["status_code"])
    return None


def _is_expired(expires_at: str | None) -> bool:
    """Return True when expires_at is set and already in the past."""
    if not expires_at:
        return False
    try:
        return datetime.utcnow().isoformat() > expires_at
    except Exception:
        return False


def _expire_waiting_battle(db, battle_id: str) -> bool:
    """Lazy-transition a waiting battle to expired if needed."""
    now = datetime.utcnow().isoformat()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_tma_battles "
            "SET status='expired', waiting_pair_key=NULL "
            "WHERE battle_id=? AND status='waiting' AND expires_at IS NOT NULL AND expires_at < ?",
            (battle_id, now),
        )
        changed = cursor.rowcount > 0
        conn.commit()
    return changed


def _resolve_active_opponent(db, challenger_telegram_id: int, opponent_telegram_id: int) -> dict | None:
    """Return active opponent row for challenge creation."""
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, telegram_id, username
            FROM users
            WHERE CAST(telegram_id AS TEXT) = ?
              AND CAST(telegram_id AS TEXT) != ?
              AND telegram_id IS NOT NULL
              AND COALESCE(last_active, created_at) >= ?
            LIMIT 1
            """,
            (str(opponent_telegram_id), str(challenger_telegram_id), cutoff),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))


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
async def create_challenge(body: ChallengeRequest, request: Request, tg: dict = Depends(get_tg_user)):
    """Challenger picks pack and creates a pending battle. Returns shareable link."""
    db = get_db()
    challenger = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    packs = db.get_user_purchased_packs(challenger["user_id"])
    if not any(str(p.get("pack_id")) == body.pack_id for p in packs):
        raise HTTPException(403, "You don't own that pack")

    if body.opponent_telegram_id == tg["id"]:
        raise HTTPException(400, "You can't challenge yourself")
    if body.opponent_telegram_id <= 0:
        raise HTTPException(400, "Invalid Telegram opponent ID")
    opponent = _resolve_active_opponent(db, tg["id"], body.opponent_telegram_id)
    if not opponent:
        raise HTTPException(404, "Opponent not found or not recently active on Telegram")

    idempotency_key = _get_idempotency_key(request, body.idempotency_key)
    replay = _idempotency_reserve_or_replay(
        db,
        challenger["user_id"],
        "battle_challenge_create",
        idempotency_key,
        {
            "opponent_telegram_id": body.opponent_telegram_id,
            "pack_id": body.pack_id,
            "wager_tier": body.wager_tier,
        },
    )
    if replay is not None:
        return replay

    now = datetime.utcnow().isoformat()
    pair_key = f"{challenger['user_id']}:{opponent['user_id']}"
    existing_battle_id = None

    import os
    tma_url = os.environ.get("TMA_URL", "https://t.me/MusicLegendsBot/app")
    try:
        battle_id = _make_battle_id()
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()

        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            # Expire stale waiting rows for this pair before insert.
            cursor.execute(
                "UPDATE pending_tma_battles "
                "SET status='expired', waiting_pair_key=NULL "
                "WHERE challenger_id=? AND opponent_id=? AND status='waiting' "
                "AND expires_at IS NOT NULL AND expires_at < ?",
                (challenger["user_id"], opponent["user_id"], now),
            )
            try:
                cursor.execute(
                    "INSERT INTO pending_tma_battles "
                    "(battle_id, challenger_id, opponent_id, challenger_pack, wager_tier, status, expires_at, created_at, waiting_pair_key) "
                    "VALUES (?, ?, ?, ?, ?, 'waiting', ?, ?, ?)",
                    (
                        battle_id,
                        challenger["user_id"],
                        opponent["user_id"],
                        body.pack_id,
                        body.wager_tier,
                        expires,
                        now,
                        pair_key,
                    ),
                )
            except sqlite3.IntegrityError:
                cursor.execute(
                    "SELECT battle_id FROM pending_tma_battles "
                    "WHERE waiting_pair_key=? AND status='waiting' "
                    "ORDER BY COALESCE(created_at, expires_at) DESC, rowid DESC LIMIT 1",
                    (pair_key,),
                )
                row = cursor.fetchone()
                existing_battle_id = row[0] if row else None
            conn.commit()

        if existing_battle_id:
            response_payload = {
                "battle_id": existing_battle_id,
                "link": f"{tma_url}?startapp=battle_{existing_battle_id}",
                "status": "waiting",
                "duplicate_prevented": True,
            }
            if idempotency_key:
                db.finalize_idempotency_key(
                    challenger["user_id"],
                    "battle_challenge_create",
                    idempotency_key,
                    200,
                    response_payload,
                )
            return response_payload

        link = f"{tma_url}?startapp=battle_{battle_id}"
        response_payload = {"battle_id": battle_id, "link": link, "status": "waiting"}

        if idempotency_key:
            db.finalize_idempotency_key(
                challenger["user_id"],
                "battle_challenge_create",
                idempotency_key,
                200,
                response_payload,
            )

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

        return response_payload
    except Exception:
        if idempotency_key:
            db.release_idempotency_key(challenger["user_id"], "battle_challenge_create", idempotency_key)
        raise


@router.post("/{battle_id}/accept")
async def accept_challenge(battle_id: str, body: AcceptRequest, request: Request,
                           tg: dict = Depends(get_tg_user)):
    """Opponent selects pack and battle executes immediately."""
    db = get_db()
    opponent = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    idempotency_key = _get_idempotency_key(request, body.idempotency_key)
    replay = _idempotency_reserve_or_replay(
        db,
        opponent["user_id"],
        "battle_challenge_accept",
        idempotency_key,
        {"battle_id": battle_id, "pack_id": body.pack_id},
    )
    if replay is not None:
        return replay

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT battle_id, challenger_id, opponent_id, challenger_pack, wager_tier, status, expires_at "
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
        if _is_expired(battle.get("expires_at")):
            _expire_waiting_battle(db, battle_id)
            raise HTTPException(400, "Battle link has expired")
        if int(battle["opponent_id"]) != int(opponent["user_id"]):
            raise HTTPException(403, "This challenge is for a different player")

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
                "SET status='complete', opponent_id=?, opponent_pack=?, result_json=?, waiting_pair_key=NULL "
                "WHERE battle_id=? AND status='waiting'",
                (opponent["user_id"], body.pack_id, json.dumps(result), battle_id)
            )
            if cursor.rowcount == 0:
                raise HTTPException(409, "Battle state changed. Please refresh.")
            conn.commit()

        response_payload = {"battle_id": battle_id, "result": result}
        if idempotency_key:
            db.finalize_idempotency_key(
                opponent["user_id"], "battle_challenge_accept", idempotency_key, 200, response_payload
            )

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

        return response_payload
    except Exception:
        if idempotency_key:
            db.release_idempotency_key(opponent["user_id"], "battle_challenge_accept", idempotency_key)
        raise


@router.post("/{battle_id}/decline")
async def decline_challenge(battle_id: str, request: Request, tg: dict = Depends(get_tg_user)):
    """Target opponent declines a waiting challenge."""
    db = get_db()
    opponent = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    idempotency_key = _get_idempotency_key(request)
    replay = _idempotency_reserve_or_replay(
        db,
        opponent["user_id"],
        "battle_challenge_decline",
        idempotency_key,
        {"battle_id": battle_id},
    )
    if replay is not None:
        return replay

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT opponent_id, status, expires_at FROM pending_tma_battles WHERE battle_id = ?",
                (battle_id,),
            )
            row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Battle not found")
        opponent_id, status, expires_at = row
        if int(opponent_id) != int(opponent["user_id"]):
            raise HTTPException(403, "Only the challenged player can decline")
        if status != "waiting":
            raise HTTPException(400, f"Battle is already {status}")
        if _is_expired(expires_at):
            _expire_waiting_battle(db, battle_id)
            raise HTTPException(400, "Battle link has expired")

        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pending_tma_battles SET status='declined', waiting_pair_key=NULL "
                "WHERE battle_id=? AND status='waiting'",
                (battle_id,),
            )
            if cursor.rowcount == 0:
                raise HTTPException(409, "Battle state changed. Please refresh.")
            conn.commit()

        response_payload = {"battle_id": battle_id, "status": "declined"}
        if idempotency_key:
            db.finalize_idempotency_key(
                opponent["user_id"], "battle_challenge_decline", idempotency_key, 200, response_payload
            )
        return response_payload
    except Exception:
        if idempotency_key:
            db.release_idempotency_key(opponent["user_id"], "battle_challenge_decline", idempotency_key)
        raise


@router.post("/{battle_id}/cancel")
async def cancel_challenge(battle_id: str, request: Request, tg: dict = Depends(get_tg_user)):
    """Challenger cancels a waiting challenge."""
    db = get_db()
    challenger = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    idempotency_key = _get_idempotency_key(request)
    replay = _idempotency_reserve_or_replay(
        db,
        challenger["user_id"],
        "battle_challenge_cancel",
        idempotency_key,
        {"battle_id": battle_id},
    )
    if replay is not None:
        return replay

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT challenger_id, status, expires_at FROM pending_tma_battles WHERE battle_id = ?",
                (battle_id,),
            )
            row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Battle not found")
        challenger_id, status, expires_at = row
        if int(challenger_id) != int(challenger["user_id"]):
            raise HTTPException(403, "Only the challenger can cancel")
        if status != "waiting":
            raise HTTPException(400, f"Battle is already {status}")
        if _is_expired(expires_at):
            _expire_waiting_battle(db, battle_id)
            raise HTTPException(400, "Battle link has expired")

        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pending_tma_battles SET status='cancelled', waiting_pair_key=NULL "
                "WHERE battle_id=? AND status='waiting'",
                (battle_id,),
            )
            if cursor.rowcount == 0:
                raise HTTPException(409, "Battle state changed. Please refresh.")
            conn.commit()

        response_payload = {"battle_id": battle_id, "status": "cancelled"}
        if idempotency_key:
            db.finalize_idempotency_key(
                challenger["user_id"], "battle_challenge_cancel", idempotency_key, 200, response_payload
            )
        return response_payload
    except Exception:
        if idempotency_key:
            db.release_idempotency_key(challenger["user_id"], "battle_challenge_cancel", idempotency_key)
        raise


@router.get("/inbox")
def get_challenge_inbox(
    waiting_limit: int = Query(default=20, ge=1, le=100),
    recent_limit: int = Query(default=20, ge=1, le=100),
    tg: dict = Depends(get_tg_user),
):
    """Return incoming/outgoing waiting and recent terminal challenge rows."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    user_id = user["user_id"]
    now = datetime.utcnow().isoformat()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_tma_battles "
            "SET status='expired', waiting_pair_key=NULL "
            "WHERE status='waiting' AND expires_at IS NOT NULL AND expires_at < ? "
            "AND (challenger_id=? OR opponent_id=?)",
            (now, user_id, user_id),
        )
        conn.commit()

        def _fetch_rows(role_col: str, counterpart_col: str, waiting_only: bool, limit: int):
            status_sql = "b.status = 'waiting'" if waiting_only else "b.status != 'waiting'"
            cursor.execute(
                f"""
                SELECT
                    b.battle_id,
                    b.status,
                    b.expires_at,
                    b.created_at,
                    b.wager_tier,
                    u.user_id AS counterpart_user_id,
                    u.telegram_id AS counterpart_telegram_id,
                    u.username AS counterpart_username
                FROM pending_tma_battles b
                LEFT JOIN users u ON u.user_id = b.{counterpart_col}
                WHERE b.{role_col} = ? AND {status_sql}
                ORDER BY COALESCE(b.created_at, b.expires_at) DESC, b.rowid DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    "battle_id": r["battle_id"],
                    "status": r["status"],
                    "expires_at": r["expires_at"],
                    "created_at": r["created_at"],
                    "wager_tier": r["wager_tier"],
                    "counterpart": {
                        "user_id": r["counterpart_user_id"],
                        "telegram_id": r["counterpart_telegram_id"],
                        "username": r["counterpart_username"],
                    },
                }
                for r in rows
            ]

        incoming_waiting = _fetch_rows("opponent_id", "challenger_id", True, waiting_limit)
        outgoing_waiting = _fetch_rows("challenger_id", "opponent_id", True, waiting_limit)
        incoming_recent = _fetch_rows("opponent_id", "challenger_id", False, recent_limit)
        outgoing_recent = _fetch_rows("challenger_id", "opponent_id", False, recent_limit)

    return {
        "incoming_waiting": incoming_waiting,
        "outgoing_waiting": outgoing_waiting,
        "incoming_recent": incoming_recent,
        "outgoing_recent": outgoing_recent,
    }


@router.get("/{battle_id}")
def get_battle(battle_id: str, tg: dict = Depends(get_tg_user)):
    """Poll for battle status/result."""
    db = get_db()
    _expire_waiting_battle(db, battle_id)
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
