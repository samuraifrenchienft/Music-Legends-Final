"""Battle Pass router."""
from fastapi import APIRouter, Depends, HTTPException
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api/battle_pass", tags=["battle_pass"])

@router.get("")
def get_battle_pass(tg: dict = Depends(get_tg_user)):
    """Get battle pass status for the user."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    # TODO: Implement get_battle_pass logic in database.py
    return {"message": "Battle pass functionality not yet implemented."}

@router.post("/claim/{tier}")
def claim_battle_pass_tier(tier: int, tg: dict = Depends(get_tg_user)):
    """Claim a tier of the battle pass."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    # TODO: Implement claim_battle_pass_tier logic in database.py
    return {"message": f"Claiming tier {tier} not yet implemented."}
