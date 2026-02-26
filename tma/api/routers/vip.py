'''VIP router.'''
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from tma.api.auth import get_tg_user
from database import get_db
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/vip", tags=["vip"])

class VIPPurchaseRequest(BaseModel):
    tier: int
    duration_days: int

@router.get("")
def get_vip_status_endpoint(tg: dict = Depends(get_tg_user)):
    """Get VIP status for the user."""
    db = get_db()
    user = db.get_or_create_telegram_.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    vip_status = db.get_vip_status(user["user_id"])
    if not vip_status:
        return {"is_vip": False, "tier": 0, "expiration_date": None}
    return vip_status

@router.post("/purchase")
def purchase_vip_endpoint(request: VIPPurchaseRequest, tg: dict = Depends(get_tg_user)):
    """Purchase VIP for the user."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    
    # In a real application, you would handle payment processing here.
    # For now, we'll just set the VIP status directly.
    
    expiration_date = datetime.utcnow() + timedelta(days=request.duration_days)
    db.set_vip_status(user["user_id"], True, request.tier, expiration_date.isoformat())
    
    return {"message": f"VIP Tier {request.tier} purchased successfully."}