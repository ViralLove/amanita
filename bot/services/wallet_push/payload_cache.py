"""
In-memory кэш данных для подписи по upload_id (W2).

Хранит payload_bytes и мету (upload_token, tags_for_item, anchor, expires_at) с TTL.
Ключ — upload_id; интерфейс допускает подмену в тестах (протокол или прямой инстанс).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CachedPayload:
    """Один элемент кэша: данные для GET sign-payload."""

    payload_bytes: bytes
    upload_token: str
    tags_for_item: List[Dict[str, str]]
    anchor: str
    expires_at: datetime


class PayloadCache:
    """
    In-memory кэш по upload_id с TTL.

    put(upload_id, ...) сохраняет запись; get(upload_id) возвращает её или None,
    если истёк TTL или ключа нет. Однопоточное использование (документировано).
    """

    DEFAULT_TTL_SEC = 60 * 30  # 30 минут

    def __init__(self, default_ttl_sec: int = DEFAULT_TTL_SEC) -> None:
        self._default_ttl_sec = default_ttl_sec
        self._store: Dict[str, tuple[CachedPayload, float]] = {}  # upload_id -> (value, expiry_ts)

    def put(
        self,
        upload_id: str,
        payload_bytes: bytes,
        upload_token: str,
        tags_for_item: List[Dict[str, str]],
        anchor: str,
        expires_at: datetime,
        ttl_sec: Optional[int] = None,
    ) -> None:
        ttl = ttl_sec if ttl_sec is not None else self._default_ttl_sec
        expiry = time.time() + ttl
        self._store[upload_id] = (
            CachedPayload(
                payload_bytes=payload_bytes,
                upload_token=upload_token,
                tags_for_item=tags_for_item,
                anchor=anchor,
                expires_at=expires_at,
            ),
            expiry,
        )

    def get(self, upload_id: str) -> Optional[CachedPayload]:
        """Вернуть запись по upload_id или None, если нет или истёк TTL."""
        entry = self._store.get(upload_id)
        if entry is None:
            return None
        value, expiry_ts = entry
        if time.time() > expiry_ts:
            del self._store[upload_id]
            return None
        return value
