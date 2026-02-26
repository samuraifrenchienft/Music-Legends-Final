'''User-created packs router.'''
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api/user_packs", tags=["user_packs"])

class PackCreateRequest(BaseModel):
    name: str
    card_ids: List[str]

@router.post("/create")
def create_user_pack_endpoint(request: PackCreateRequest, tg: dict = Depends(get_tg_user)):
    """Create a new user-defined pack."""
    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    pack_id = str(uuid.uuid4())
    
    # In a real application, you might want to verify that the user owns the cards
    # and remove them from their inventory.
    
    new_pack_id = db.create_user_pack(pack_id, request.name, user["user_id"], request.card_ids)
    return {"pack_id": new_pack_id}

@router.get("/{pack_id}")
def get_user_pack_endpoint(pack_id: str, tg: dict = Depends(get_tg_user)):
    """Get a user-created pack."""
    db = get_db()
    pack = db.get_user_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found.")
    return pack
