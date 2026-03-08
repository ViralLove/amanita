"""
Unit tests for create_draft: prepare + payload cache + push (W2).

Моки PrepareResolveService и PushSender; реальные StubPushSender и PayloadCache для assert.
"""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.upload.storage import PrepareForDraftResult
from services.wallet_push import PayloadCache, StubPushSender


@pytest.fixture
def mock_prepare_svc():
    svc = MagicMock()
    svc.prepare_upload_for_draft.return_value = PrepareForDraftResult(
        upload_id="upload-uuid-1",
        upload_token="jwt.token",
        payload_bytes=b'{"title": "Test", "activity_type": "event"}',
        tags_for_item=[{"name": "Upload-Id", "value": "upload-uuid-1"}],
        anchor="anchor123",
        expires_at=datetime.now(timezone.utc),
    )
    return svc


@pytest.fixture
def push_sender():
    return StubPushSender()


@pytest.fixture
def payload_cache():
    return PayloadCache(default_ttl_sec=3600)


@pytest.fixture
def app(mock_prepare_svc, push_sender, payload_cache):
    """App с роутом activities и подменёнными зависимостями."""
    mock_registry = MagicMock()
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry}):
        from api.dependencies import (
            get_activity_storage,
            get_payload_cache,
            get_prepare_resolve_service,
            get_push_sender,
        )
        from api.routes import activities
        from api.services import ActivityStorage
    app = FastAPI()
    app.include_router(activities.router)
    app.dependency_overrides[get_activity_storage] = lambda: ActivityStorage()
    app.dependency_overrides[get_prepare_resolve_service] = lambda: mock_prepare_svc
    app.dependency_overrides[get_push_sender] = lambda: push_sender
    app.dependency_overrides[get_payload_cache] = lambda: payload_cache
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.mark.unit
class TestCreateDraftPreparePush:
    def test_create_draft_calls_prepare_and_push_and_caches(
        self, client, mock_prepare_svc, push_sender, payload_cache
    ):
        body = {
            "activity_type": "event",
            "title": "Test Event",
            "short_summary": "Summary",
        }
        r = client.post(
            "/activities/draft",
            json=body,
            headers={"X-User-Id": "user-1", "Content-Type": "application/json"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data.get("success") is True
        assert "activity" in data
        assert data["activity"].get("activity_id")
        assert data.get("upload_id") == "upload-uuid-1"
        assert data.get("upload_token") == "jwt.token"

        mock_prepare_svc.prepare_upload_for_draft.assert_called_once()
        call_kwargs = mock_prepare_svc.prepare_upload_for_draft.call_args
        assert call_kwargs[0][0] == data["activity"]["activity_id"]
        assert call_kwargs[0][1] == "user-1"
        assert call_kwargs[0][2] == body

        events = push_sender.get_pending_events()
        assert len(events) == 1
        assert events[0]["user_id"] == "user-1"
        assert events[0]["request_type"] == "sign_arweave"
        assert events[0]["request_id"] == "upload-uuid-1"

        cached = payload_cache.get("upload-uuid-1")
        assert cached is not None
        assert cached.payload_bytes == b'{"title": "Test", "activity_type": "event"}'
        assert cached.upload_token == "jwt.token"

    def test_create_draft_uses_mock_user_when_no_x_user_id(
        self, client, mock_prepare_svc, push_sender
    ):
        """Без заголовка X-User-Id используется fallback mock_user."""
        r = client.post(
            "/activities/draft",
            json={
                "activity_type": "event",
                "title": "No Header",
                "short_summary": "Summary",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 201
        call_args = mock_prepare_svc.prepare_upload_for_draft.call_args
        assert call_args[0][1] == "mock_user"
        events = push_sender.get_pending_events()
        assert len(events) >= 1
        assert events[-1]["user_id"] == "mock_user"
