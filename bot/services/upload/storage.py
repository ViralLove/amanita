"""
PrepareResolveService: доменный фасад сценария «prepare → sign in wallet → callback → CID».

Роль (не путать с UploadService в upload_service.py):
- Этот модуль реализует сценарий для черновика/activity: «подготовить данные для подписи
  в кошельке → после callback от Edge получить CID → читать/валидировать метаданные по CID».
- Работает с доменными сущностями: draft_id, payload_descriptor (dict); сам сериализует
  descriptor в payload_bytes и передаёт их в UploadService.prepare(); в ответ клиенту
  добавляет payload_bytes (для wallet), которых нет в PrepareResult — чтобы не было
  путаницы: «кто отдаёт payload в wallet» — только PrepareResolveService.
- Не дублирует логику таблицы uploads, JWT, стейт-машины: всё это делегирует UploadService.
- Чтение по CID (download_metadata) и валидация CID (validate_cid) делегируются
  storage_provider или CIDValidator (DP-4, без дублирования).

Кто использует PrepareResolveService:
- Роуты activity (и позже product): prepare_upload_for_draft → клиент подписывает в wallet
  → Edge публикует → callback → resolve_cid_from_callback → create_activity(..., cid).
- Тот же сервис: download_metadata(cid), validate_cid(cid) для проверки и отображения.

Зависимости: UploadService (upload_service.py), storage_provider (download_json, опционально
validate_ipfs_cid). Task 3.3, DP-3.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

_floou_draft_log = logging.getLogger("amanita_api.floou_draft")


@dataclass
class PrepareForDraftResult:
    """
    Результат prepare_upload_for_draft(): данные для кошелька (что будет подписано).

    В отличие от UploadService.PrepareResult, здесь есть payload_bytes — их добавляет
    PrepareResolveService, т.к. клиенту (wallet) нужны bytes для подписи; UploadService
    payload в ответ не возвращает (контракт инфраструктурного слоя).
    """
    upload_id: str
    upload_token: str
    payload_bytes: bytes
    tags_for_item: List[Dict[str, str]]
    anchor: str
    expires_at: datetime


class PrepareResolveService:
    """
    Фасад сценария: подготовка к подписи в wallet, получение CID после callback, работа по CID.

    Отвечает за:
    - prepare_upload_for_draft: превратить payload_descriptor (dict) в payload_bytes,
      вызвать UploadService.prepare(..., activity_id=draft_id), вернуть клиенту данные для
      wallet (включая payload_bytes — их UploadService не отдаёт).
    - resolve_cid_from_callback: вызвать UploadService.handle_callback() и вернуть CID
      (bundle_tx_id) для дальнейшего создания activity/product.
    - download_metadata(cid), validate_cid(cid): делегировать storage_provider или
      CIDValidator; логику не дублируем (DP-4).

    Не дублирует: создание записей upload, JWT, стейт-машину, контракт с Edge — всё в
    UploadService (upload_service.py). Этот класс только оркестрирует вызовы и добавляет
    доменный контракт (draft_id, payload_bytes в ответе).

    Зависит от: UploadService, storage_provider (download_json; опционально validate_ipfs_cid).
    """

    def __init__(
        self,
        upload_service: Any,
        storage_provider: Any,
    ):
        self._upload_service = upload_service
        self._storage_provider = storage_provider

    def prepare_upload_for_draft(
        self,
        draft_id: str,
        user_id: str,
        payload_descriptor: Dict[str, Any],
    ) -> PrepareForDraftResult:
        """
        Подготовить загрузку для черновика: dict → bytes, вызов UploadService.prepare, ответ для wallet.

        Сериализует payload_descriptor в JSON bytes, создаёт запись через UploadService.prepare
        с activity_id=draft_id, возвращает PrepareForDraftResult с payload_bytes (для подписи
        в кошельке). Логику БД/JWT не дублирует — только фасад.
        """
        payload_bytes = json.dumps(payload_descriptor, sort_keys=True).encode("utf-8")
        _floou_draft_log.debug(
            "prepare_upload_for_draft: draft_id=%s user_id=%s payload_bytes=%s",
            draft_id,
            user_id,
            len(payload_bytes),
        )
        result = self._upload_service.prepare(
            payload_bytes,
            user_id,
            activity_id=draft_id,
        )
        _floou_draft_log.debug(
            "prepare_upload_for_draft: UploadService.prepare → upload_id=%s",
            result.upload_id,
        )
        return PrepareForDraftResult(
            upload_id=result.upload_id,
            upload_token=result.upload_token,
            payload_bytes=payload_bytes,
            tags_for_item=result.tags_for_item,
            anchor=result.anchor,
            expires_at=result.expires_at,
        )

    def resolve_cid_from_callback(
        self,
        upload_id: str,
        item_id: str,
        bundle_tx_id: str,
        published_at: Optional[datetime] = None,
        owner_address: Optional[str] = None,
    ) -> str:
        """
        Применить callback от Edge и вернуть CID (bundle_tx_id).

        Вызывает UploadService.handle_callback(upload_id, item_id, bundle_tx_id, …);
        возвращает bundle_tx_id как CID для вызова create_activity(..., cid=...) или
        аналога. Единственная точка входа «после callback → CID» в доменном слое.
        """
        self._upload_service.handle_callback(
            upload_id,
            item_id,
            bundle_tx_id,
            owner_address=owner_address,
        )
        return bundle_tx_id

    def download_metadata(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Загрузить сырые JSON-метаданные по CID (через storage_provider, напр. Arweave gateway).

        Делегирует storage_provider.download_json(cid). Возвращает None при ошибке или
        недоступности. Логику загрузки не дублирует — провайдер один.
        """
        try:
            if hasattr(self._storage_provider, "download_json"):
                return self._storage_provider.download_json(cid)
            return None
        except Exception:
            return None

    def validate_cid(self, cid: str) -> bool:
        """
        Проверить формат/доступность CID (делегация провайдеру или CIDValidator).

        Если у storage_provider есть validate_ipfs_cid — используем его; иначе
        ValidationFactory.get_cid_validator().validate(cid). Дублирования логики нет (DP-4).
        """
        if hasattr(self._storage_provider, "validate_ipfs_cid"):
            return bool(self._storage_provider.validate_ipfs_cid(cid))
        from validation.factory import ValidationFactory
        result = ValidationFactory.get_cid_validator().validate(cid)
        return result.is_valid
