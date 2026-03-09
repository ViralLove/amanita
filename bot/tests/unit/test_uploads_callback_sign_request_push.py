"""
Unit tests for callback → sign_request + push sign_contract (W4).

Моки UploadService (handle_callback, get_upload); реальные StubPushSender и SignRequestStore.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from model.upload import UploadRecord
from services.wallet_push import SignRequestStore, StubPushSender

EDGE_SECRET = "mock-edge-to-backend-secret"


@pytest.fixture(autouse=True)
def set_edge_secret():
    old = os.environ.get("EDGE_TO_BACKEND_SECRET")
    os.environ["EDGE_TO_BACKEND_SECRET"] = EDGE_SECRET
    yield
    if old is None:
        os.environ.pop("EDGE_TO_BACKEND_SECRET", None)
    else:
        os.environ["EDGE_TO_BACKEND_SECRET"] = old


@pytest.fixture
def upload_id():
    return "upload-cb-123"


@pytest.fixture
def mock_upload_record(upload_id):
    return UploadRecord(
        upload_id=upload_id,
        user_id="user-callback",
        status="published",
        payload_hash=None,
        payload_size=100,
        tags_snapshot=None,
        anchor="anchor-1",
        expires_at=datetime.now(timezone.utc),
        item_id="item-1",
        bundle_tx_id="bundle-tx-456",
        activity_id="draft-1",
        created_at=None,
        updated_at=None,
    )


@pytest.fixture
def mock_upload_svc(mock_upload_record, upload_id):
    svc = MagicMock()
    svc.get_upload.side_effect = lambda uid: mock_upload_record if uid == upload_id else None
    return svc


@pytest.fixture
def push_sender():
    return StubPushSender()


@pytest.fixture
def sign_request_store():
    return SignRequestStore()


@pytest.fixture
def app(mock_upload_svc, push_sender, sign_request_store):
    mock_registry = MagicMock()
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry}):
        from api.dependencies import get_push_sender, get_sign_request_store, get_upload_service
        from api.routes import uploads
    app = FastAPI()
    app.include_router(uploads.router)
    app.dependency_overrides[get_upload_service] = lambda: mock_upload_svc
    app.dependency_overrides[get_push_sender] = lambda: push_sender
    app.dependency_overrides[get_sign_request_store] = lambda: sign_request_store
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def _headers():
    return {"Authorization": f"Bearer {EDGE_SECRET}", "Content-Type": "application/json"}


@pytest.mark.unit
class TestCallbackSignRequestPush:
    def test_callback_creates_sign_request_and_sends_push(
        self, client, mock_upload_svc, upload_id, push_sender, sign_request_store
    ):
        body = {
            "upload_id": upload_id,
            "item_id": "item-1",
            "bundle_tx_id": "bundle-tx-456",
            "published_at": "2026-01-29T12:00:00Z",
        }
        r = client.post("/v1/uploads/callback", json=body, headers=_headers())
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        mock_upload_svc.handle_callback.assert_called_once()
        mock_upload_svc.get_upload.assert_called_with(upload_id)

        events = push_sender.get_pending_events()
        assert len(events) == 1
        assert events[0]["user_id"] == "user-callback"
        assert events[0]["request_type"] == "sign_contract"
        sign_request_id = events[0]["request_id"]
        assert sign_request_id

        rec = sign_request_store.get(sign_request_id)
        assert rec is not None
        assert rec.user_id == "user-callback"
        assert rec.type == "create_activity"
        assert rec.upload_id == upload_id
        assert rec.cid == "bundle-tx-456"
        assert rec.status == "pending"
