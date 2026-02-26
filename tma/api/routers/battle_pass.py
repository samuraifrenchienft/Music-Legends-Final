"""Battle Pass router."""
from fastapi import APIRouter, Depends, HTTPException
from tma.api.auth import get_tg_user
from database import get_db
from config.battle_pass import SeasonConfig

router = APIRouter(prefix="/api/battle_pass", tags=["battle_pass"])

@router.get("")
def get_battle_pass(tg: dict = Depends(get_tg_user)):
    """Get battle pass status for the user."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    battle_pass_status = db.get_battle_pass_status(user['user_id'], SeasonConfig.CURRENT_SEASON_ID)
    return battle_pass_status

@router.post("/claim/{tier}")
def claim_battle_pass_tier_endpoint(tier: int, tg: dict = Depends(get_tg_user)):
    """Claim a tier of the battle pass."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    
    # You might want to add more validation here, e.g. checking if the user has premium
    # and if the tier is a premium tier.
    
    success, message = db.claim_battle_pass_tier(user['user_id'], SeasonConfig.CURRENT_SEASON_ID, tier)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
        
    # Here you would typically grant the rewards for the claimed tier.
    # This logic would likely live in another module, e.g., a rewards service.
    # For now, we'll just return a success message.
    
    return {"message": message}
