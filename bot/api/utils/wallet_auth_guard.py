from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException

from api.dependencies import get_wallet_auth_service


def _is_fallback_enabled() -> bool:
    return os.environ.get("ALLOW_X_USER_ID_FALLBACK", "true").lower() == "true"


def _wallet_auth_mode() -> str:
    return os.environ.get("WALLET_AUTH_MODE", "challenge_signature")


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip()


def authenticate_wallet_request(
    expected_user_id: Optional[str],
    x_user_id: Optional[str],
    x_wallet_address: Optional[str],
    authorization: Optional[str],
) -> dict:
    """
    Returns wallet auth principal and enforces fallback policy.
    """
    mode = _wallet_auth_mode()
    auth_service = get_wallet_auth_service()
    token = _parse_bearer(authorization)

    if mode == "challenge_signature" and token:
        try:
            session = auth_service.validate_session(token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail={"error_code": str(e)})
        if x_wallet_address and session.wallet_address != x_wallet_address.strip().lower():
            raise HTTPException(status_code=403, detail={"error_code": "auth_wallet_mismatch"})
        if expected_user_id and session.user_id != expected_user_id:
            raise HTTPException(status_code=403, detail={"error_code": "auth_user_mismatch"})
        if x_user_id and session.user_id != x_user_id:
            raise HTTPException(status_code=403, detail={"error_code": "auth_user_mismatch"})
        return {
            "user_id": session.user_id,
            "wallet_address": session.wallet_address,
            "auth_mode": "token",
        }

    if _is_fallback_enabled():
        if not x_user_id:
            raise HTTPException(status_code=401, detail="X-User-Id header required")
        if expected_user_id and x_user_id != expected_user_id:
            raise HTTPException(status_code=403, detail="X-User-Id must match user_id")
        return {"user_id": x_user_id, "wallet_address": None, "auth_mode": "fallback"}

    raise HTTPException(status_code=403, detail={"error_code": "auth_fallback_disabled"})

