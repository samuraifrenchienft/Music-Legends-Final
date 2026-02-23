"""Cards router — user collection."""
from fastapi import APIRouter, Depends, HTTPException
from tma.api.auth import get_tg_user
from database import get_db
from config.cards import compute_card_power, RARITY_EMOJI

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _enrich(card: dict) -> dict:
    """Add computed power + rarity emoji to a card dict."""
    card["power"] = compute_card_power(card)
    card["rarity_emoji"] = RARITY_EMOJI.get((card.get("rarity") or "common").lower(), "⚪")
    return card


@router.get("")
def list_collection(tg: dict = Depends(get_tg_user)):
    """Return all cards the user owns, sorted by power descending."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    cards = db.get_user_collection(user["user_id"])
    cards = [_enrich(c) for c in cards]
    cards.sort(key=lambda c: c["power"], reverse=True)
    return {"cards": cards, "total": len(cards)}


@router.get("/{card_id}")
def get_card(card_id: str, tg: dict = Depends(get_tg_user)):
    """Return a single card from the user's collection."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    cards = db.get_user_collection(user["user_id"])
    card = next((c for c in cards if c.get("card_id") == card_id), None)
    if not card:
        raise HTTPException(404, "Card not found in your collection")
    return _enrich(card)
