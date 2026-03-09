"""
In-memory хранилище sign_request (W4, W5).

Запись после callback: create(user_id, type, upload_id, cid) -> sign_request_id.
W5 добавит GET/POST эндпоинты; здесь только create и хранение.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SignRequestRecord:
    """Одна запись sign_request."""

    id: str
    user_id: str
    type: str  # "create_activity"
    upload_id: str
    cid: str
    status: str  # "pending" | "submitted"
    created_at: datetime
    signed_tx: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None
    submitted_at: Optional[datetime] = None


class SignRequestStore:
    """
    In-memory хранилище sign_request (W4, W5).

    create(user_id, type, upload_id, cid) возвращает id (UUID).
    get(sign_request_id), list_by_user(user_id).
    mark_submitted(id, signed_tx, signature, message) — сохранить подпись (broadcast в W8).
    """

    def __init__(self) -> None:
        self._store: Dict[str, SignRequestRecord] = {}

    def create(
        self,
        user_id: str,
        request_type: str,
        upload_id: str,
        cid: str,
        status: str = "pending",
    ) -> str:
        sign_request_id = str(uuid.uuid4())
        self._store[sign_request_id] = SignRequestRecord(
            id=sign_request_id,
            user_id=user_id,
            type=request_type,
            upload_id=upload_id,
            cid=cid,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        return sign_request_id

    def get(self, sign_request_id: str) -> Optional[SignRequestRecord]:
        return self._store.get(sign_request_id)

    def list_by_user(self, user_id: str) -> List[SignRequestRecord]:
        return [r for r in self._store.values() if r.user_id == user_id]

    def mark_submitted(
        self,
        sign_request_id: str,
        signed_tx: Optional[str] = None,
        signature: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        rec = self._store.get(sign_request_id)
        if not rec:
            raise KeyError(f"SignRequest not found: {sign_request_id}")
        rec.signed_tx = signed_tx
        rec.signature = signature
        rec.message = message
        rec.submitted_at = datetime.now(timezone.utc)
        rec.status = "submitted"
