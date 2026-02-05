"""
Uploads API — мок-эндпоинты для тестирования Edge Function arweave-upload.

PUT /v1/uploads/{upload_id}/status — приём статуса от Edge (queued_for_publish / failed).
POST /v1/uploads/callback — приём callback после публикации в Arweave.
Авторизация: Authorization: Bearer EDGE_TO_BACKEND_SECRET (из env или fallback для dev).
"""

from __future__ import annotations

import os
import secrets as secmod
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

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
):
    """Мок: приём статуса от Edge (queued_for_publish или failed с failure_code)."""
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/uploads/callback")
async def post_upload_callback(
    body: CallbackBody,
    _: None = Depends(verify_edge_bearer),
):
    """Мок: приём callback после успешной публикации в Arweave."""
    return JSONResponse(status_code=200, content={"ok": True})
