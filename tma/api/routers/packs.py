"""Packs router — view acquired packs + open them."""
from fastapi import APIRouter, Depends, HTTPException
from tma.api.auth import get_tg_user
from database import get_db
from cards_config import compute_card_power, RARITY_EMOJI

router = APIRouter(prefix="/api/packs", tags=["packs"])


@router.get("")
def list_packs(tg: dict = Depends(get_tg_user)):
    """Return all packs the user has acquired."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    packs = db.get_user_purchased_packs(user["user_id"])
    # Always expose card-based pseudo packs too.
    # Users can own cards from daily/trade/market without a matching purchased pack row.
    cards = db.get_user_collection(user["user_id"]) or []
    pseudo = []
    for c in cards[:50]:
        cid = str(c.get("card_id") or "")
        if not cid:
            continue
        pseudo.append({
            "pack_id": f"card:{cid}",
            "name": f"Card: {c.get('name') or cid}",
            "pack_name": f"Card: {c.get('name') or cid}",
            "pack_tier": (c.get("rarity") or "community").lower(),
            "tier": (c.get("rarity") or "community").lower(),
            "genre": "Music",
            "cards": [c],
            "card_count": 1,
            "_type": "card",
        })

    merged = []
    seen = set()
    for p in (packs or []) + pseudo:
        pid = str(p.get("pack_id") or "")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        merged.append(p)
    return {"packs": merged, "total": len(merged)}


@router.get("/store")
def get_store(tg: dict = Depends(get_tg_user)):
    """Return live packs available in the store."""
    db = get_db()
    return {"packs": db.get_live_packs(limit=20)}


@router.post("/{pack_id}/purchase")
def purchase_pack(pack_id: str, tg: dict = Depends(get_tg_user)):
    """Purchase a live pack using gold."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    result = db.purchase_live_pack(user["user_id"], pack_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to purchase pack"))
    return result


@router.post("/{pack_id}/open")
def open_pack(pack_id: str, tg: dict = Depends(get_tg_user)):
    """Open a pack the user owns. Returns enriched cards."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))

    # Verify ownership before opening
    packs = db.get_user_purchased_packs(user["user_id"])
    owned = {str(p.get("pack_id")) for p in packs}
    if pack_id not in owned:
        raise HTTPException(403, "You don't own this pack")

    result = db.open_pack_for_drop(pack_id, user["user_id"])
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to open pack"))

    cards = result.get("cards", [])
    for c in cards:
        c["power"] = compute_card_power(c)
        c["rarity_emoji"] = RARITY_EMOJI.get((c.get("rarity") or "common").lower(), "⚪")

    return {"cards": cards, "pack_id": pack_id}
