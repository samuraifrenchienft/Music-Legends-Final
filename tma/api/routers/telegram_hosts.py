"""Register Telegram community hosts (revenue share). Protected by env TELEGRAM_HOST_ADMIN_KEY."""
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from database import get_db
from models import TelegramHost

router = APIRouter(prefix="/api/hosts", tags=["hosts"])


class RegisterHostBody(BaseModel):
    host_token: str = Field(..., min_length=4, max_length=128)
    owner_telegram_id: int = Field(..., gt=0)
    share_bps: int = Field(1000, ge=0, le=10000, description="Basis points, e.g. 1000 = 10%")
    label: Optional[str] = None
    chat_id: Optional[int] = None


def _check_admin_key(x_admin_key: Optional[str]) -> None:
    expected = (os.getenv("TELEGRAM_HOST_ADMIN_KEY") or "").strip()
    if not expected or (x_admin_key or "") != expected:
        raise HTTPException(401, "Invalid admin key")


@router.post("/register")
def register_host(
    body: RegisterHostBody,
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
):
    _check_admin_key(x_admin_key)
    """Create or update a host token (manual Phase A onboarding)."""
    db = get_db()
    session = db.get_session()
    try:
        tok = body.host_token.strip()
        row = session.query(TelegramHost).filter_by(host_token=tok).first()
        if row:
            row.owner_telegram_id = body.owner_telegram_id
            row.share_bps = body.share_bps
            row.label = body.label
            if body.chat_id is not None:
                row.chat_id = body.chat_id
        else:
            session.add(
                TelegramHost(
                    host_token=tok,
                    owner_telegram_id=body.owner_telegram_id,
                    chat_id=body.chat_id,
                    label=body.label,
                    share_bps=body.share_bps,
                )
            )
        session.commit()
        return {"ok": True, "host_token": tok, "share_bps": body.share_bps}
    except Exception as e:
        session.rollback()
        raise HTTPException(500, str(e)) from e
    finally:
        session.close()
