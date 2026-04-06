"""
Оркестратор операций Activity (ASG-3).

Все сценарии /activities/* (мок GPT API) проходят через Registry; роуты остаются тонкими (HTTP + simulate_error).
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from services.application.activity.models import ActivityCreateDraftResult, ActivityMutationOutcome
from services.wallet_push import PushSender

if TYPE_CHECKING:
    from api.services import ActivityStorage
    from services.upload.storage import PrepareResolveService
    from services.wallet_push import PayloadCache

logger = logging.getLogger(__name__)
# Явный канал для сквозной трассировки POST /activities/draft (наследует уровень от amanita_api.*).
floou_draft_log = logging.getLogger("amanita_api.floou_draft")

_STATUS_DRAFT = "Draft"
_STATUS_PUBLISHED = "Published"


class ActivityRegistryService:
    """
    Координация жизненного цикла Activity (мок-хранилище + prepare/upload/sign для draft).

    Расширение под BlockchainService и подсервисы из activity-services-architecture.md —
    через конструктор, без возврата оркестрации в роуты.
    """

    def __init__(
        self,
        storage: ActivityStorage,
        prepare_resolve: PrepareResolveService,
        push_sender: PushSender,
        payload_cache: PayloadCache,
    ) -> None:
        self._storage = storage
        self._prepare_resolve = prepare_resolve
        self._push_sender = push_sender
        self._payload_cache = payload_cache

    def create_draft(self, user_id: str, payload: dict[str, Any]) -> ActivityCreateDraftResult:
        title = (payload.get("title") or "")[:80]
        floou_draft_log.debug(
            "create_draft: start user_id=%s title=%r",
            user_id,
            title,
        )
        activity = self._storage.create(payload)
        draft_id = activity["activity_id"]
        floou_draft_log.info(
            "create_draft: in-memory Draft stored activity_id=%s user_id=%s",
            draft_id,
            user_id,
        )
        prepare_result = self._prepare_resolve.prepare_upload_for_draft(draft_id, user_id, payload)
        floou_draft_log.info(
            "create_draft: Supabase prepare done upload_id=%s activity_id=%s token_expires=%s",
            prepare_result.upload_id,
            draft_id,
            prepare_result.expires_at.isoformat() if prepare_result.expires_at else None,
        )
        self._payload_cache.put(
            prepare_result.upload_id,
            prepare_result.payload_bytes,
            prepare_result.upload_token,
            prepare_result.tags_for_item,
            prepare_result.anchor,
            prepare_result.expires_at,
        )
        _anchor_snip = prepare_result.anchor
        if len(_anchor_snip) > 16:
            _anchor_snip = _anchor_snip[:16] + "…"
        floou_draft_log.debug(
            "create_draft: PayloadCache.put upload_id=%s payload_bytes=%s anchor=%s",
            prepare_result.upload_id,
            len(prepare_result.payload_bytes),
            _anchor_snip,
        )
        self._push_sender.send_sign_request(user_id, "sign_arweave", prepare_result.upload_id)
        floou_draft_log.info(
            "create_draft: wallet push sign_arweave enqueued upload_id=%s user_id=%s (StubPushSender logs pending events in tests)",
            prepare_result.upload_id,
            user_id,
        )
        floou_draft_log.info(
            "create_draft: sync leg finished — HTTP will return 201. "
            "Further floou is async/out-of-band: client uses upload_token → wallet signs → "
            "Edge/uploader publishes → POST /v1/uploads/callback → sign_request optional.",
            extra={"activity_id": draft_id, "upload_id": prepare_result.upload_id},
        )
        return ActivityCreateDraftResult(
            activity=activity,
            upload_id=prepare_result.upload_id,
            upload_token=prepare_result.upload_token,
            expires_at=prepare_result.expires_at,
        )

    def list_my_activities(
        self,
        *,
        owner_id: Optional[str] = None,
        status: Optional[str] = None,
        activity_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._storage.list(
            owner_id=owner_id,
            status=status,
            activity_type=activity_type,
            page=page,
            per_page=per_page,
        )

    def search_activities(
        self,
        *,
        text: Optional[str] = None,
        activity_type: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20,
        sort_field: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._storage.search(
            text=text,
            activity_type=activity_type,
            filters=filters,
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order,
        )

    def get_activity(self, activity_id: str) -> Optional[dict[str, Any]]:
        return self._storage.get(activity_id)

    def update_draft(self, activity_id: str, body: dict[str, Any]) -> ActivityMutationOutcome:
        existing = self._storage.get(activity_id)
        if not existing:
            return ActivityMutationOutcome(error="not_found")
        current = existing.get("status", _STATUS_DRAFT)
        if current != _STATUS_DRAFT:
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state=_STATUS_DRAFT,
            )
        activity = self._storage.update(activity_id, body)
        return ActivityMutationOutcome(activity=activity)

    def submit_review(self, activity_id: str) -> ActivityMutationOutcome:
        existing = self._storage.get(activity_id)
        if not existing:
            return ActivityMutationOutcome(error="not_found")
        current = existing.get("status", _STATUS_DRAFT)
        if current != _STATUS_DRAFT:
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state=_STATUS_DRAFT,
            )
        try:
            activity = self._storage.update_status(activity_id, "SentToReview")
        except ValueError:
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state=_STATUS_DRAFT,
            )
        return ActivityMutationOutcome(activity=activity)

    def publish(self, activity_id: str) -> ActivityMutationOutcome:
        existing = self._storage.get(activity_id)
        if not existing:
            return ActivityMutationOutcome(error="not_found")
        current = existing.get("status", _STATUS_DRAFT)
        if current != "Approved":
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state="Approved",
            )
        try:
            activity = self._storage.update_status(activity_id, _STATUS_PUBLISHED)
        except ValueError:
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state="Approved",
            )
        return ActivityMutationOutcome(activity=activity)

    def unpublish(self, activity_id: str) -> ActivityMutationOutcome:
        existing = self._storage.get(activity_id)
        if not existing:
            return ActivityMutationOutcome(error="not_found")
        current = existing.get("status", _STATUS_DRAFT)
        if current != _STATUS_PUBLISHED:
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state=_STATUS_PUBLISHED,
            )
        try:
            activity = self._storage.update_status(activity_id, _STATUS_DRAFT)
        except ValueError:
            return ActivityMutationOutcome(
                error="invalid_state",
                current_state=current,
                required_state=_STATUS_PUBLISHED,
            )
        return ActivityMutationOutcome(activity=activity)
