"""ASG-3: ActivityRegistryService.create_draft без FastAPI (юнит)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.application.activity import ActivityRegistryService
from services.upload.storage import PrepareForDraftResult
from services.wallet_push import PayloadCache, StubPushSender


@pytest.mark.unit
def test_registry_create_draft_orchestrates_storage_prepare_cache_push():
    storage = MagicMock()
    storage.create.return_value = {"activity_id": "draft-xyz", "status": "Draft"}

    prepare = MagicMock()
    prepare.prepare_upload_for_draft.return_value = PrepareForDraftResult(
        upload_id="u1",
        upload_token="tok",
        payload_bytes=b"{}",
        tags_for_item=[],
        anchor="a",
        expires_at=datetime.now(timezone.utc),
    )

    push = StubPushSender()
    cache = PayloadCache(default_ttl_sec=60)

    reg = ActivityRegistryService(
        storage=storage,
        prepare_resolve=prepare,
        push_sender=push,
        payload_cache=cache,
    )
    out = reg.create_draft("user-42", {"title": "T", "activity_type": "event"})

    storage.create.assert_called_once()
    prepare.prepare_upload_for_draft.assert_called_once_with("draft-xyz", "user-42", {"title": "T", "activity_type": "event"})
    assert out.upload_id == "u1"
    assert out.upload_token == "tok"
    assert cache.get("u1") is not None
    events = push.get_pending_events()
    assert len(events) == 1
    assert events[0]["user_id"] == "user-42"
    assert events[0]["request_type"] == "sign_arweave"
