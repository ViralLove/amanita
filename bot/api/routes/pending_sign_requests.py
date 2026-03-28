"""
Pending sign-requests (W6): GET событий из StubPushSender для wallet-mock runner.

GET /v1/pending-sign-requests?user_id=... — возвращает события для user_id и забирает их из очереди.
Требуется X-User-Id, совпадающий с user_id (для мока один пользователь).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from api.dependencies import get_push_sender
from api.utils.wallet_auth_guard import authenticate_wallet_request

router = APIRouter(prefix="/v1", tags=["pending-sign-requests"])


@router.get("/pending-sign-requests")
async def get_pending_sign_requests(
    user_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="User ID (must match user_id)"),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    push_sender=Depends(get_push_sender),
):
    """
    События запросов на подпись для wallet-mock runner (StubPushSender).
    Возвращает события для user_id и удаляет их из очереди (claim).
    """
    authenticate_wallet_request(
        expected_user_id=user_id,
        x_user_id=x_user_id,
        x_wallet_address=x_wallet_address,
        authorization=authorization,
    )
    if hasattr(push_sender, "get_and_claim_events"):
        events = push_sender.get_and_claim_events(user_id)
    else:
        events = []
    return JSONResponse(status_code=200, content={"events": events})
