"""ASG-3: переходы статусов и чтение через ActivityRegistryService (без FastAPI)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from api.services import ActivityStorage
from services.application.activity import ActivityRegistryService
from services.wallet_push import PayloadCache, StubPushSender


def _minimal_registry(storage: ActivityStorage) -> ActivityRegistryService:
    prepare = MagicMock()
    return ActivityRegistryService(
        storage=storage,
        prepare_resolve=prepare,
        push_sender=StubPushSender(),
        payload_cache=PayloadCache(default_ttl_sec=60),
    )


@pytest.mark.unit
def test_update_draft_requires_draft_status():
    storage = ActivityStorage()
    reg = _minimal_registry(storage)
    # act_1 from seed is Draft in template - pick one
    draft_id = "act_1"
    out = reg.update_draft(draft_id, {"title": "New"})
    assert out.error is None
    assert out.activity and out.activity.get("title") == "New"

    approved_id = "act_3"  # template #3 is Approved
    out2 = reg.update_draft(approved_id, {"title": "X"})
    assert out2.error == "invalid_state"
    assert out2.required_state == "Draft"


@pytest.mark.unit
def test_submit_review_from_draft():
    storage = ActivityStorage()
    reg = _minimal_registry(storage)
    draft_id = "act_1"
    out = reg.submit_review(draft_id)
    assert out.error is None
    assert out.activity and out.activity.get("status") == "SentToReview"


@pytest.mark.unit
def test_publish_requires_approved():
    storage = ActivityStorage()
    reg = _minimal_registry(storage)
    out = reg.publish("act_1")
    assert out.error == "invalid_state"
    assert out.required_state == "Approved"

    approved_id = "act_3"
    out_ok = reg.publish(approved_id)
    assert out_ok.error is None
    assert out_ok.activity and out_ok.activity.get("status") == "Published"


@pytest.mark.unit
def test_unpublish_from_published():
    storage = ActivityStorage()
    reg = _minimal_registry(storage)
    published_id = "act_8"
    out = reg.unpublish(published_id)
    assert out.error is None
    assert out.activity and out.activity.get("status") == "Draft"


@pytest.mark.unit
def test_search_returns_only_published():
    storage = ActivityStorage()
    reg = _minimal_registry(storage)
    items, total = reg.search_activities(text=None, activity_type=None, page=1, per_page=100)
    assert total >= 1
    assert all(x.get("status") == "Published" for x in items)


@pytest.mark.unit
def test_get_missing_returns_none():
    storage = ActivityStorage()
    reg = _minimal_registry(storage)
    assert reg.get_activity("nonexistent") is None
