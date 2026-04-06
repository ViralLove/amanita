"""
Sign-requests API (W5, W8): GET параметров для подписи, POST submit подписи.

Слой HTTP: аутентификация кошелька, чтение/обновление SignRequestStore, маппинг ошибок.
Контекст EVM (chain_id, contract): снимок в записи при create (см. uploads callback) либо
fallback через BlockchainService — тот же контекст для GET и для проверки raw tx при submit.
Разбор и проверка подписанной транзакции — BlockchainService.submit_sign_request_raw_transaction.

GET /v1/sign-requests/{id} — параметры для подписи (type, cid, chain_id, contract_address, upload_id).
POST /v1/sign-requests/{id}/submit — signedTransaction (broadcast с проверкой контекста) или signature+message (EIP-712, без broadcast здесь).
Авторизация: X-User-Id.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.dependencies import get_blockchain_service, get_sign_request_store
from api.utils.wallet_auth_guard import authenticate_wallet_request
from services.wallet_push.sign_request_store import SignRequestRecord

logger = logging.getLogger(__name__)
sign_flow_log = logging.getLogger("amanita_api.sign_flow")

router = APIRouter(prefix="/v1", tags=["sign-requests"])


def _evm_sign_context(rec: SignRequestRecord, blockchain_service) -> tuple[str, str]:
    """
    Целевая сеть и контракт для подписи: снимок с момента create (предпочтительно),
    иначе — текущие параметры из BlockchainService (старые записи / тесты).
    """
    cid = (rec.evm_chain_id or "").strip()
    addr = (rec.evm_contract_address or "").strip()
    if cid and addr:
        return cid, addr
    return blockchain_service.get_sign_request_evm_params()


class SubmitBody(BaseModel):
    """Тело POST /sign-requests/{id}/submit."""

    signedTransaction: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None


@router.get("/sign-requests/{sign_request_id}")
async def get_sign_request(
    sign_request_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="User ID (required)"),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    store=Depends(get_sign_request_store),
    blockchain_service=Depends(get_blockchain_service),
):
    """Параметры для подписи контракта по id. X-User-Id должен совпадать с владельцем записи."""
    rec = store.get(sign_request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Sign request not found")
    principal = authenticate_wallet_request(
        expected_user_id=rec.user_id,
        x_user_id=x_user_id,
        x_wallet_address=x_wallet_address,
        authorization=authorization,
    )
    if rec.user_id != principal["user_id"]:
        raise HTTPException(status_code=403, detail="Sign request does not belong to this user")
    chain_id, contract_address = _evm_sign_context(rec, blockchain_service)
    sign_flow_log.info(
        "GET sign-requests: params issued sign_request_id=%s upload_id=%s chain_id=%s "
        "contract_address=%s type=%s — кошелёк собирает unsigned tx с этим chain_id; "
        "WALLET_MOCK_RPC_URL должен давать тот же eth_chainId, иначе ethers: transaction chainId mismatch",
        sign_request_id,
        rec.upload_id,
        chain_id,
        contract_address,
        rec.type,
    )
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
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    store=Depends(get_sign_request_store),
    blockchain_service=Depends(get_blockchain_service),
):
    """Принять подписанную транзакцию или подпись EIP-712. Сохраняем данные; при signedTransaction — broadcast (W8)."""
    rec = store.get(sign_request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Sign request not found")
    principal = authenticate_wallet_request(
        expected_user_id=rec.user_id,
        x_user_id=x_user_id,
        x_wallet_address=x_wallet_address,
        authorization=authorization,
    )
    if rec.user_id != principal["user_id"]:
        raise HTTPException(status_code=403, detail="Sign request does not belong to this user")

    expected_chain_id, expected_contract = _evm_sign_context(rec, blockchain_service)

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
            tx_hash = blockchain_service.submit_sign_request_raw_transaction(
                body.signedTransaction,
                expected_chain_id=expected_chain_id,
                expected_to_address=expected_contract,
            )
            store.set_tx_hash(sign_request_id, tx_hash)
            sign_flow_log.info(
                "POST sign-requests/submit: broadcast ok sign_request_id=%s tx_hash=%s",
                sign_request_id,
                tx_hash,
            )
        except ValueError as e:
            logger.warning("Submit broadcast validation or hex error: %s", e)
            raise HTTPException(status_code=422, detail=f"Invalid signed transaction: {e!s}") from e
        except Exception as e:
            logger.exception("Submit broadcast failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Broadcast failed: {e!s}") from e

    content: dict = {"ok": True}
    if tx_hash:
        content["tx_hash"] = tx_hash
    return JSONResponse(status_code=200, content=content)
