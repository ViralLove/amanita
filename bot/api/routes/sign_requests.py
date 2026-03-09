"""
Sign-requests API (W5, W8): GET параметров для подписи, POST submit подписи.

GET /v1/sign-requests/{id} — параметры для подписи (type, cid, chain_id, contract_address, upload_id).
POST /v1/sign-requests/{id}/submit — приём signedTransaction или signature+message; при signedTransaction — broadcast (W8).
Авторизация: X-User-Id.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.dependencies import get_sign_request_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["sign-requests"])


def _get_blockchain_service_for_broadcast():
    """Used only when broadcast is needed; inject via Depends in tests."""
    from api.dependencies import get_blockchain_service
    return get_blockchain_service()


class SubmitBody(BaseModel):
    """Тело POST /sign-requests/{id}/submit."""

    signedTransaction: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None


@router.get("/sign-requests/{sign_request_id}")
async def get_sign_request(
    sign_request_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="User ID (required)"),
    store=Depends(get_sign_request_store),
):
    """Параметры для подписи контракта по id. X-User-Id должен совпадать с владельцем записи."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    rec = store.get(sign_request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Sign request not found")
    if rec.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Sign request does not belong to this user")
    chain_id = os.environ.get("CHAIN_ID", "")
    contract_address = os.environ.get("ACTIVITY_REGISTRY_ADDRESS", "")
    return JSONResponse(
        status_code=200,
        content={
            "type": rec.type,
            "cid": rec.cid,
            "upload_id": rec.upload_id,
            "chain_id": chain_id,
            "contract_address": contract_address,
            "deadline": None,
        },
    )


@router.post("/sign-requests/{sign_request_id}/submit")
async def submit_sign_request(
    sign_request_id: str,
    body: SubmitBody,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="User ID (required)"),
    store=Depends(get_sign_request_store),
    blockchain_service=Depends(_get_blockchain_service_for_broadcast),
):
    """Принять подписанную транзакцию или подпись EIP-712. Сохраняем данные; при signedTransaction — broadcast (W8)."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    rec = store.get(sign_request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Sign request not found")
    if rec.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Sign request does not belong to this user")
    try:
        store.mark_submitted(
            sign_request_id,
            signed_tx=body.signedTransaction,
            signature=body.signature,
            message=body.message,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Sign request not found")

    tx_hash: Optional[str] = None
    if body.signedTransaction and body.signedTransaction.strip():
        try:
            tx_hash = blockchain_service.send_raw_transaction_hex(body.signedTransaction)
            store.set_tx_hash(sign_request_id, tx_hash)
        except ValueError as e:
            logger.warning("Submit broadcast invalid hex: %s", e)
            raise HTTPException(status_code=422, detail=f"Invalid signed transaction: {e!s}") from e
        except Exception as e:
            logger.exception("Submit broadcast failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Broadcast failed: {e!s}") from e

    content: dict = {"ok": True}
    if tx_hash:
        content["tx_hash"] = tx_hash
    return JSONResponse(status_code=200, content=content)
