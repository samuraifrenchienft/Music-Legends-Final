# handlers/purchase_minimal.py
"""
Minimal purchase handler stub.
"""
from typing import Any


async def handle_purchase_minimal(interaction: Any, item_id: str, **kwargs) -> dict:
    """Minimal purchase flow handler."""
    return {"success": False, "error": "Purchase handler not implemented"}
