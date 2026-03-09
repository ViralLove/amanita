"""
Unit tests for GET /v1/uploads/{upload_id}/sign-payload (W3).

Моки UploadService (get_upload) и PayloadCache (get).
"""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from model.upload import UploadRecord
from services.wallet_push import CachedPayload, PayloadCache


@pytest.fixture
def upload_id():
    return "upload-uuid-123"


@pytest.fixture
def mock_upload_record(upload_id):
    return UploadRecord(
        upload_id=upload_id,
        user_id="user-1",
        status="prepared",
        payload_hash=None,
        payload_size=100,
        tags_snapshot=None,
        anchor="anchor-1",
        expires_at=datetime.now(timezone.utc),
        activity_id="draft-1",
        created_at=None,
        updated_at=None,
    )


@pytest.fixture
def cached_payload():
    return CachedPayload(
        payload_bytes=b'{"title": "Test"}',
        upload_token="jwt.token.here",
        tags_for_item=[{"name": "Upload-Id", "value": "upload-uuid-123"}],
        anchor="anchor-1",
        expires_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_upload_svc(mock_upload_record, upload_id):
    svc = MagicMock()
    svc.get_upload.side_effect = lambda uid: mock_upload_record if uid == upload_id else None
    return svc


@pytest.fixture
def payload_cache(cached_payload, upload_id):
    cache = PayloadCache()
    cache.put(
        upload_id,
        cached_payload.payload_bytes,
        cached_payload.upload_token,
        cached_payload.tags_for_item,
        cached_payload.anchor,
        cached_payload.expires_at,
    )
    return cache


@pytest.fixture
def app(mock_upload_svc, payload_cache):
    mock_registry = MagicMock()
    with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry}):
        from api.dependencies import get_payload_cache, get_upload_service
        from api.routes import uploads
    app = FastAPI()
    app.include_router(uploads.router)
    app.dependency_overrides[get_upload_service] = lambda: mock_upload_svc
    app.dependency_overrides[get_payload_cache] = lambda: payload_cache
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.mark.unit
class TestGetUploadSignPayload:
    def test_200_returns_payload_and_meta(self, client, upload_id):
        r = client.get(
            f"/v1/uploads/{upload_id}/sign-payload",
            headers={"X-User-Id": "user-1"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["upload_id"] == upload_id
        assert data["upload_token"] == "jwt.token.here"
        assert data["payload_base64"] == "eyJ0aXRsZSI6ICJUZXN0In0="
        assert data["tags"] == [{"name": "Upload-Id", "value": upload_id}]
        assert data["anchor"] == "anchor-1"
        assert "expires_at" in data
        assert "arweave_uploader_url" in data

    def test_401_without_x_user_id(self, client, upload_id):
        r = client.get(f"/v1/uploads/{upload_id}/sign-payload")
        assert r.status_code == 401
        assert "X-User-Id" in r.json().get("detail", "")

    def test_403_wrong_user(self, client, upload_id):
        r = client.get(
            f"/v1/uploads/{upload_id}/sign-payload",
            headers={"X-User-Id": "other-user"},
        )
        assert r.status_code == 403
        assert "does not belong" in r.json().get("detail", "")

    def test_404_unknown_upload_id(self, client):
        r = client.get(
            "/v1/uploads/unknown-uuid/sign-payload",
            headers={"X-User-Id": "user-1"},
        )
        assert r.status_code == 404
        assert "not found" in r.json().get("detail", "").lower()

    def test_410_cache_empty(self, client, upload_id, mock_upload_svc):
        empty_cache = PayloadCache()
        mock_registry = MagicMock()
        with patch.dict(sys.modules, {"services.product.registry_singleton": mock_registry}):
            from api.dependencies import get_payload_cache, get_upload_service
            from api.routes import uploads
        app = FastAPI()
        app.include_router(uploads.router)
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_svc
        app.dependency_overrides[get_payload_cache] = lambda: empty_cache
        r = TestClient(app).get(
            f"/v1/uploads/{upload_id}/sign-payload",
            headers={"X-User-Id": "user-1"},
        )
        assert r.status_code == 410
        assert "expired" in r.json().get("detail", "").lower() or "not available" in r.json().get("detail", "").lower()