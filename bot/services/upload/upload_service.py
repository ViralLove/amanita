"""
UploadService: инфраструктурный слой таблицы uploads и контракта Edge → Backend.

Роль (не путать с PrepareResolveService в storage.py):
- Этот модуль реализует «движок» таблицы uploads: создание записей (prepared), JWT для
  upload_token, стейт-машина статусов (prepared → queued_for_publish → published → …),
  приём обновлений от Edge (PUT status, POST callback).
- Работает с уже готовыми payload_bytes и user_id; не знает про «черновик», «activity»,
  «wallet» — только опциональный activity_id как строка для связки записи с сущностью.
- Не возвращает payload в ответе (контракт: payload не хранить и не отдавать обратно).
- Не занимается чтением/валидацией данных по CID (Arweave gateway) — это в PrepareResolveService.

Кто использует UploadService:
- PrepareResolveService (storage.py) — вызывает prepare() и handle_callback() для сценария
  «подготовка к подписи → callback → CID» и добавляет доменный контракт (payload_bytes в ответе).
- Роуты uploads (PUT status, POST callback) — вызывают update_status() и handle_callback()
  при запросах от Edge.

Зависимости: Supabase (таблица uploads), JWT RS256 (upload_token). Task 3.2.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from model.upload import PREPARED, can_transition, UploadRecord
from services.upload.jwt_upload_token import sign_upload_token, JWTUploadTokenError

logger = logging.getLogger(__name__)


class UploadNotFoundError(Exception):
    """Запись upload с указанным upload_id не найдена в БД."""
    pass


class UploadConflictError(Exception):
    """Недопустимый переход статуса (например prepared → published без queued_for_publish)."""
    pass


class RateLimitExceededError(Exception):
    """Превышен лимит загрузок в минуту или байт в день по user_id."""
    pass


@dataclass
class PrepareResult:
    """
    Результат prepare(): данные для клиента/Edge после создания записи (prepared).

    Важно: payload_bytes здесь нет — по контракту payload не храним и не возвращаем
    из этого слоя. Если вызывающему коду (например PrepareResolveService) нужны
    payload_bytes для отдачи в wallet, он передаёт в prepare() те же bytes и сохраняет
    их у себя в ответе (PrepareForDraftResult в storage.py).
    """
    upload_id: str
    upload_token: str
    tags_for_item: List[Dict[str, str]]  # [{"name": "Upload-Id", "value": "..."}, ...]
    anchor: str
    expires_at: datetime
    payload_hash: str
    payload_size: int


def _default_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


class UploadService:
    """
    Инфраструктурный сервис: таблица uploads, JWT upload_token, стейт-машина записей.

    Отвечает за:
    - Создание записи в статусе prepared (prepare), выпуск JWT, теги Data Item, rate limits.
    - Обновление статуса на queued_for_publish или failed (update_status) — вызывается
      из роута при PUT от Edge.
    - Приём callback от Edge: переход в published, сохранение item_id, bundle_tx_id,
      owner_address (handle_callback) — вызывается из роута POST callback или из
      PrepareResolveService.resolve_cid_from_callback().

    Не отвечает за:
    - Преобразование «черновик / метаданные» в payload_bytes (это делает PrepareResolveService).
    - Возврат payload_bytes клиенту для подписи в wallet (это PrepareResolveService).
    - Чтение или валидацию данных по CID (Arweave) — это PrepareResolveService + провайдер.

    См. также: storage.PrepareResolveService — фасад доменного сценария «prepare for draft →
    sign in wallet → callback → CID» и работа с метаданными по CID.
    """

    def __init__(
        self,
        supabase_client: Any,
        *,
        rate_limit_per_min: Optional[int] = None,
        rate_limit_bytes_per_day: Optional[int] = None,
        anchor_ttl_sec: Optional[int] = None,
        token_exp_sec: Optional[int] = None,
    ):
        self._db = supabase_client
        self.rate_limit_per_min = rate_limit_per_min or _default_int("UPLOAD_RATE_LIMIT_PER_MIN", 10)
        self.rate_limit_bytes_per_day = rate_limit_bytes_per_day or _default_int(
            "UPLOAD_RATE_LIMIT_BYTES_PER_DAY", 50 * 1024 * 1024
        )  # 50 MB
        self.anchor_ttl_sec = anchor_ttl_sec or _default_int("UPLOAD_ANCHOR_TTL_SEC", 3600)
        self.token_exp_sec = token_exp_sec or _default_int("UPLOAD_TOKEN_EXP_SEC", 3600)

    def _check_rate_limits(self, user_id: str, payload_size: int) -> None:
        now = datetime.now(timezone.utc)
        since_minute = (now - timedelta(minutes=1)).isoformat()
        since_day = (now - timedelta(days=1)).isoformat()
        count = self._db.count_uploads_by_user_since(user_id, since_minute)
        if count >= self.rate_limit_per_min:
            logger.warning("Upload rate limit exceeded", extra={"user_id": user_id, "count": count})
            raise RateLimitExceededError("Uploads per minute limit exceeded")
        total_bytes = self._db.sum_payload_size_by_user_since(user_id, since_day)
        if total_bytes + payload_size > self.rate_limit_bytes_per_day:
            logger.warning("Upload bytes per day limit exceeded", extra={"user_id": user_id, "total": total_bytes})
            raise RateLimitExceededError("Max bytes per day exceeded")

    def prepare(
        self,
        payload_bytes: bytes,
        user_id: str,
        *,
        content_type: str = "application/json",
        app_name: str = "Amanita",
        data_schema: str = "activity-metadata-v1",
        activity_id: Optional[str] = None,
        max_bytes: Optional[int] = None,
    ) -> PrepareResult:
        """
        Создать запись upload в статусе prepared, выпустить JWT, вернуть данные для клиента/Edge.

        Вход: уже готовые payload_bytes (этот сервис не знает, откуда они — dict, JSON и т.д.).
        В БД сохраняются только hash и size; сами bytes не хранятся и не возвращаются в
        PrepareResult. Rate limits и anchor TTL применяются здесь.

        Вызывается из PrepareResolveService.prepare_upload_for_draft() (который передаёт
        activity_id=draft_id и затем добавляет payload_bytes в свой ответ для wallet).
        """
        payload_size = len(payload_bytes)
        max_bytes = max_bytes or payload_size
        self._check_rate_limits(user_id, payload_size)

        upload_id = str(uuid.uuid4())
        anchor = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.anchor_ttl_sec)
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        tags_for_item: List[Dict[str, str]] = [
            {"name": "Upload-Id", "value": upload_id},
            {"name": "Content-Type", "value": content_type},
            {"name": "App-Name", "value": app_name},
            {"name": "Data-Schema", "value": data_schema},
        ]
        if activity_id:
            tags_for_item.append({"name": "Activity-Id", "value": str(activity_id)})

        tags_snapshot = {t["name"]: t["value"] for t in tags_for_item}

        try:
            upload_token = sign_upload_token(
                upload_id=upload_id,
                user_id=user_id,
                max_bytes=max_bytes,
                exp_seconds=self.token_exp_sec,
            )
        except JWTUploadTokenError as e:
            logger.error("Upload token signing failed", extra={"upload_id": upload_id, "error": str(e)})
            raise

        row = {
            "upload_id": upload_id,
            "user_id": user_id,
            "status": PREPARED,
            "payload_hash": payload_hash,
            "payload_size": payload_size,
            "tags_snapshot": tags_snapshot,
            "anchor": anchor,
            "expires_at": expires_at.isoformat(),
            "activity_id": activity_id,
        }
        self._db.insert_upload(row)
        logger.info(
            "Upload prepared",
            extra={"upload_id": upload_id, "user_id": user_id, "status": PREPARED},
        )
        return PrepareResult(
            upload_id=upload_id,
            upload_token=upload_token,
            tags_for_item=tags_for_item,
            anchor=anchor,
            expires_at=expires_at,
            payload_hash=payload_hash,
            payload_size=payload_size,
        )

    def get_upload(self, upload_id: str) -> Optional[UploadRecord]:
        """Получить запись upload по upload_id; None, если не найдена."""
        row = self._db.get_upload_by_id(upload_id)
        if not row:
            return None
        return UploadRecord.from_row(row)

    def update_status(
        self,
        upload_id: str,
        status: str,
        failure_reason: Optional[str] = None,
        failure_code: Optional[str] = None,
    ) -> None:
        """
        Перевести запись в queued_for_publish или failed.

        Вызывается из роута PUT /v1/uploads/{id}/status при запросе от Edge (после валидации
        подписи или при ошибке). Raises UploadNotFoundError, UploadConflictError.
        """
        rec = self.get_upload(upload_id)
        if not rec:
            raise UploadNotFoundError(f"Upload not found: {upload_id}")
        if not can_transition(rec.status, status):
            logger.warning(
                "Invalid upload status transition",
                extra={"upload_id": upload_id, "from": rec.status, "to": status},
            )
            raise UploadConflictError(f"Invalid transition {rec.status} -> {status}")
        self._db.update_upload_status(upload_id, status, failure_reason=failure_reason, failure_code=failure_code)
        logger.info(
            "Upload status updated",
            extra={"upload_id": upload_id, "old_status": rec.status, "new_status": status, "failure_code": failure_code},
        )

    def handle_callback(
        self,
        upload_id: str,
        item_id: str,
        bundle_tx_id: str,
        owner_address: Optional[str] = None,
    ) -> None:
        """
        Перевести запись в published и сохранить item_id, bundle_tx_id, owner_address.

        Вызывается из роута POST /v1/uploads/callback при запросе от Edge (после публикации
        в Arweave), а также из PrepareResolveService.resolve_cid_from_callback() (который
        затем возвращает bundle_tx_id как CID вызывающему коду). Raises UploadNotFoundError,
        UploadConflictError.
        """
        rec = self.get_upload(upload_id)
        if not rec:
            raise UploadNotFoundError(f"Upload not found: {upload_id}")
        if not can_transition(rec.status, "published"):
            logger.warning(
                "Invalid upload status for callback",
                extra={"upload_id": upload_id, "current_status": rec.status},
            )
            raise UploadConflictError(f"Cannot publish from status {rec.status}")
        self._db.update_upload_callback(upload_id, item_id=item_id, bundle_tx_id=bundle_tx_id, owner_address=owner_address)
        logger.info(
            "Upload callback applied",
            extra={"upload_id": upload_id, "bundle_tx_id": bundle_tx_id},
        )
