"""Stripe Checkout session creation for Telegram Mini App (card payments)."""
import os
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from tma.api.auth import get_tg_user
from database import get_db

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


class TierPackCheckoutBody(BaseModel):
    tier: str = Field(..., description="community, gold, or platinum")


class CreatorPackCheckoutBody(BaseModel):
    pack_id: str


def _host_context(db, user_id: str) -> Tuple[Optional[str], Optional[int]]:
    """Return (host_token, host_share_bps) from user referral + telegram_hosts row."""
    session = db.get_session()
    try:
        from models import User

        user = session.query(User).filter_by(user_id=str(user_id)).first()
        token = (user.referrer_host_token or "").strip() if user else ""
        if not token:
            return None, None
        host = db.get_telegram_host_by_token(token)
        if host:
            return token, int(host.get("share_bps") or 0)
        default_bps = int(os.getenv("DEFAULT_HOST_SHARE_BPS", "1000"))
        return token, default_bps
    finally:
        session.close()


@router.post("/tier-pack")
def create_tier_pack_checkout(body: TierPackCheckoutBody, tg: dict = Depends(get_tg_user)):
    """Create Stripe Checkout for a built-in tier pack (USD from config)."""
    from config.economy import PACK_PRICING
    from stripe_payments import stripe_manager

    tier = (body.tier or "").strip().lower()
    if tier not in PACK_PRICING:
        raise HTTPException(400, f"Invalid tier: {body.tier}")

    pricing = PACK_PRICING[tier]
    price_cents = pricing.get("buy_usd_cents")
    if not price_cents:
        raise HTTPException(400, "This tier is not available for card checkout")

    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    uid = str(user["user_id"])
    host_token, host_share_bps = _host_context(db, uid)

    labels = {
        "community": "Community Pack",
        "gold": "Gold Pack",
        "platinum": "Platinum Pack",
    }
    pack_name = labels.get(tier, tier.title() + " Pack")

    result = stripe_manager.create_tma_tier_pack_checkout(
        tier=tier,
        buyer_id=uid,
        pack_name=pack_name,
        price_cents=int(price_cents),
        host_token=host_token,
        host_share_bps=host_share_bps,
    )
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Stripe error"))
    return {
        "checkout_url": result["checkout_url"],
        "session_id": result.get("session_id"),
        "tier": tier,
        "price_cents": int(price_cents),
    }


@router.post("/creator-pack")
def create_creator_pack_checkout(body: CreatorPackCheckoutBody, tg: dict = Depends(get_tg_user)):
    """Create Stripe Checkout for a LIVE creator pack (price from DB or tier default)."""
    from stripe_payments import stripe_manager

    pack_id = (body.pack_id or "").strip()
    if not pack_id:
        raise HTTPException(400, "pack_id required")

    db = get_db()
    user = db.get_or_create_telegram_user(tg["id"], tg.get("username", ""))
    uid = str(user["user_id"])
    host_token, host_share_bps = _host_context(db, uid)

    session = db.get_session()
    try:
        from models import CreatorPacks

        pack = session.query(CreatorPacks).filter_by(pack_id=pack_id).first()
        if not pack:
            raise HTTPException(404, "Pack not found")
        if not pack.is_public and (pack.card_count or 0) <= 0:
            raise HTTPException(400, "Pack is not available for purchase")
        name = pack.name or pack_id
        price = int(pack.price or 0)
        tier_key = (pack.pack_tier or "community").strip().lower()
    finally:
        session.close()

    if price <= 0:
        from config.economy import PACK_PRICING

        fallback = PACK_PRICING.get(tier_key, PACK_PRICING.get("community", {}))
        price = int(fallback.get("buy_usd_cents") or 299)

    result = stripe_manager.create_tma_pack_purchase_checkout(
        pack_id=pack_id,
        buyer_id=uid,
        pack_name=name,
        price_cents=price,
        host_token=host_token,
        host_share_bps=host_share_bps,
    )
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Stripe error"))
    return {
        "checkout_url": result["checkout_url"],
        "session_id": result.get("session_id"),
        "pack_id": pack_id,
        "price_cents": price,
    }
