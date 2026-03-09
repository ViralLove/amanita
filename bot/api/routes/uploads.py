"""
Uploads API — приём статуса и callback от Edge Function arweave-upload (task 3.2).

PUT /v1/uploads/{upload_id}/status — приём статуса от Edge (queued_for_publish / failed).
POST /v1/uploads/callback — приём callback после публикации в Arweave.
GET /v1/uploads/{upload_id}/sign-payload — данные для подписи по upload_id (W3; X-User-Id).
Авторизация: status/callback — Bearer EDGE_TO_BACKEND_SECRET; sign-payload — X-User-Id.
"""

from __future__ import annotations

import base64
import os
import secrets as secmod
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from api.dependencies import get_payload_cache, get_upload_service
from services.upload.upload_service import UploadConflictError, UploadNotFoundError

router = APIRouter(prefix="/v1", tags=["uploads"])

# Допустимые значения по контракту Edge → Backend (arweave-upload-publish-api.md)
STATUS_QUEUED = "queued_for_publish"
STATUS_FAILED = "failed"
FAILURE_CODES = ("token_invalid", "signature_invalid", "publish_failed")


def _get_edge_secret() -> str:
    return os.environ.get("EDGE_TO_BACKEND_SECRET") or "mock-edge-to-backend-secret"


def verify_edge_bearer(request: Request) -> None:
    """Проверяет заголовок Authorization: Bearer <token>; при несовпадении с секретом — 401."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth[7:].strip()
    expected = _get_edge_secret()
    if not secmod.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


# --- Модели тела ---


class PutStatusBody(BaseModel):
    status: Literal["queued_for_publish", "failed"]
    failure_code: Optional[Literal["token_invalid", "signature_invalid", "publish_failed"]] = None

    @model_validator(mode="after")
    def failure_code_required_if_failed(self):
        if self.status == "failed":
            if self.failure_code is None:
                raise ValueError("failure_code required when status is 'failed'")
            if self.failure_code not in FAILURE_CODES:
                raise ValueError(f"failure_code must be one of {FAILURE_CODES}")
        return self


class CallbackBody(BaseModel):
    upload_id: str
    item_id: str
    bundle_tx_id: str
    published_at: str  # ISO 8601


# --- Эндпоинты ---


@router.put("/uploads/{upload_id}/status")
async def put_upload_status(
    upload_id: str,
    body: PutStatusBody,
    _: None = Depends(verify_edge_bearer),
    upload_svc=Depends(get_upload_service),
):
    """Приём статуса от Edge (queued_for_publish или failed с failure_code). Обновляет запись в uploads."""
    try:
        upload_svc.update_status(
            upload_id,
            body.status,
            failure_code=body.failure_code,
        )
    except UploadNotFoundError:
        raise HTTPException(status_code=404, detail="Upload not found")
    except UploadConflictError:
        raise HTTPException(status_code=409, detail="Invalid status transition")
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/uploads/callback")
async def post_upload_callback(
    body: CallbackBody,
    _: None = Depends(verify_edge_bearer),
    upload_svc=Depends(get_upload_service),
):
    """Приём callback после успешной публикации в Arweave. Обновляет upload (published, bundle_tx_id, item_id)."""
    try:
        upload_svc.handle_callback(
            body.upload_id,
            item_id=body.item_id,
            bundle_tx_id=body.bundle_tx_id,
            owner_address=None,
        )
    except UploadNotFoundError:
        raise HTTPException(status_code=404, detail="Upload not found")
    except UploadConflictError:
        raise HTTPException(status_code=409, detail="Invalid status for callback")
    return JSONResponse(status_code=200, content={"ok": True})


@router.get("/uploads/{upload_id}/sign-payload")
async def get_upload_sign_payload(
    upload_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="User ID (required for sign-payload)"),
    upload_svc=Depends(get_upload_service),
    payload_cache=Depends(get_payload_cache),
):
    """
    Данные для подписи Data Item по upload_id (W3).

    Требуется X-User-Id. Проверяется совпадение с upload.user_id; данные берутся из кэша (W2).
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    user_id = x_user_id
    rec = upload_svc.get_upload(upload_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Upload not found")
    if rec.user_id != user_id:
        raise HTTPException(status_code=403, detail="Upload does not belong to this user")
    cached = payload_cache.get(upload_id)
    if not cached:
        raise HTTPException(status_code=410, detail="Sign payload not available or expired")
    payload_base64 = base64.b64encode(cached.payload_bytes).decode("ascii")
    arweave_uploader_url = os.environ.get("ARWEAVE_SERVICE_URL", "")
    return JSONResponse(
        status_code=200,
        content={
            "upload_id": upload_id,
            "upload_token": cached.upload_token,
            "payload_base64": payload_base64,
            "tags": cached.tags_for_item,
            "anchor": cached.anchor,
            "expires_at": cached.expires_at.isoformat() if cached.expires_at else None,
            "arweave_uploader_url": arweave_uploader_url,
        },
    )
