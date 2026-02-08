"""
Unit tests for UploadService: prepare, update_status, handle_callback (task 3.2).
Mock Supabase; no real Edge. JWT signing patched to avoid PEM in tests.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from model.upload import PREPARED, QUEUED_FOR_PUBLISH, PUBLISHED, FAILED
from services.upload.upload_service import (
    UploadService,
    PrepareResult,
    UploadNotFoundError,
    UploadConflictError,
    RateLimitExceededError,
)


class MockSupabase:
    """In-memory store for uploads; same interface as SupabaseService uploads methods."""

    def __init__(self):
        self.uploads = {}  # upload_id -> row dict
        self._created_order = []

    def insert_upload(self, row):
        from datetime import datetime, timezone
        rid = row.get("upload_id")
        if not rid:
            rid = "gen-" + str(len(self.uploads))
        row = dict(row)
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self.uploads[rid] = row
        self._created_order.append(rid)
        return row

    def get_upload_by_id(self, upload_id):
        return self.uploads.get(upload_id)

    def update_upload_status(self, upload_id, status, failure_reason=None, failure_code=None):
        if upload_id not in self.uploads:
            return False
        self.uploads[upload_id]["status"] = status
        if failure_reason is not None:
            self.uploads[upload_id]["failure_reason"] = failure_reason
        if failure_code is not None:
            self.uploads[upload_id]["failure_code"] = failure_code
        return True

    def update_upload_callback(self, upload_id, item_id, bundle_tx_id, owner_address=None):
        if upload_id not in self.uploads:
            return False
        self.uploads[upload_id]["status"] = PUBLISHED
        self.uploads[upload_id]["item_id"] = item_id
        self.uploads[upload_id]["bundle_tx_id"] = bundle_tx_id
        if owner_address is not None:
            self.uploads[upload_id]["owner_address"] = owner_address
        return True

    def list_uploads_by_status(self, status, limit=100):
        return [r for r in self.uploads.values() if isinstance(r, dict) and r.get("status") == status][:limit]

    def count_uploads_by_user_since(self, user_id, since_ts):
        return sum(
            1 for r in self.uploads.values()
            if isinstance(r, dict) and r.get("user_id") == user_id and r.get("created_at", "") >= since_ts
        )

    def sum_payload_size_by_user_since(self, user_id, since_ts):
        return sum(
            r.get("payload_size") or 0 for r in self.uploads.values()
            if isinstance(r, dict) and r.get("user_id") == user_id and r.get("created_at", "") >= since_ts
        )


@pytest.fixture
def mock_db():
    return MockSupabase()


@pytest.fixture
def upload_service(mock_db):
    return UploadService(
        mock_db,
        rate_limit_per_min=5,
        rate_limit_bytes_per_day=1000,
        anchor_ttl_sec=3600,
        token_exp_sec=3600,
    )


@pytest.mark.unit
class TestUploadServicePrepare:
    @patch("services.upload.upload_service.sign_upload_token")
    def test_prepare_returns_result(self, mock_sign, upload_service, mock_db):
        mock_sign.return_value = "mock-jwt-token"
        payload = b'{"title":"test"}'
        result = upload_service.prepare(payload, "user-123")
        assert isinstance(result, PrepareResult)
        assert result.upload_id
        assert result.upload_token == "mock-jwt-token"
        assert result.anchor
        assert result.payload_size == len(payload)
        assert result.payload_hash
        assert any(t["name"] == "Upload-Id" and t["value"] == result.upload_id for t in result.tags_for_item)
        assert mock_db.get_upload_by_id(result.upload_id)["status"] == PREPARED

    @patch("services.upload.upload_service.sign_upload_token")
    def test_prepare_with_activity_id_adds_tag(self, mock_sign, upload_service):
        mock_sign.return_value = "jwt"
        result = upload_service.prepare(b"x", "user-1", activity_id="42")
        assert any(t["name"] == "Activity-Id" and t["value"] == "42" for t in result.tags_for_item)

    @patch("services.upload.upload_service.sign_upload_token")
    def test_prepare_rate_limit_per_min_exceeded(self, mock_sign, upload_service, mock_db):
        mock_sign.return_value = "jwt"
        since = "2000-01-01T00:00:00Z"
        # Fill mock so count_uploads_by_user_since returns 5 (our limit)
        for i in range(5):
            mock_db.insert_upload({
                "upload_id": f"u-{i}", "user_id": "user-1", "status": PREPARED,
                "created_at": "2020-01-01T00:00:00Z", "payload_size": 0,
            })
        # Mock count to return 5 for any since
        mock_db.count_uploads_by_user_since = lambda uid, since_ts: 5
        with pytest.raises(RateLimitExceededError, match="minute"):
            upload_service.prepare(b"x", "user-1")


@pytest.mark.unit
class TestUploadServiceUpdateStatus:
    @patch("services.upload.upload_service.sign_upload_token")
    def test_update_status_prepared_to_queued(self, mock_sign, upload_service, mock_db):
        mock_sign.return_value = "jwt"
        result = upload_service.prepare(b"x", "user-1")
        upload_service.update_status(result.upload_id, QUEUED_FOR_PUBLISH)
        assert mock_db.get_upload_by_id(result.upload_id)["status"] == QUEUED_FOR_PUBLISH

    @patch("services.upload.upload_service.sign_upload_token")
    def test_update_status_prepared_to_failed_with_code(self, mock_sign, upload_service, mock_db):
        mock_sign.return_value = "jwt"
        result = upload_service.prepare(b"x", "user-1")
        upload_service.update_status(result.upload_id, FAILED, failure_code="token_invalid")
        row = mock_db.get_upload_by_id(result.upload_id)
        assert row["status"] == FAILED
        assert row["failure_code"] == "token_invalid"

    def test_update_status_not_found_raises(self, upload_service):
        with pytest.raises(UploadNotFoundError, match="not found"):
            upload_service.update_status("unknown-uuid", QUEUED_FOR_PUBLISH)

    @patch("services.upload.upload_service.sign_upload_token")
    def test_update_status_invalid_transition_raises(self, mock_sign, upload_service, mock_db):
        mock_sign.return_value = "jwt"
        result = upload_service.prepare(b"x", "user-1")
        # prepared -> published not allowed (must go queued first)
        with pytest.raises(UploadConflictError, match="Invalid transition"):
            upload_service.update_status(result.upload_id, PUBLISHED)


@pytest.mark.unit
class TestUploadServiceHandleCallback:
    @patch("services.upload.upload_service.sign_upload_token")
    def test_handle_callback_queued_to_published(self, mock_sign, upload_service, mock_db):
        mock_sign.return_value = "jwt"
        result = upload_service.prepare(b"x", "user-1")
        upload_service.update_status(result.upload_id, QUEUED_FOR_PUBLISH)
        upload_service.handle_callback(result.upload_id, "item-1", "bundle-tx-1", owner_address="0xabc")
        row = mock_db.get_upload_by_id(result.upload_id)
        assert row["status"] == PUBLISHED
        assert row["item_id"] == "item-1"
        assert row["bundle_tx_id"] == "bundle-tx-1"
        assert row["owner_address"] == "0xabc"

    def test_handle_callback_not_found_raises(self, upload_service):
        with pytest.raises(UploadNotFoundError):
            upload_service.handle_callback("unknown", "i", "b", None)

    @patch("services.upload.upload_service.sign_upload_token")
    def test_handle_callback_from_prepared_conflict(self, mock_sign, upload_service):
        mock_sign.return_value = "jwt"
        result = upload_service.prepare(b"x", "user-1")
        # prepared -> published not allowed (must be queued_for_publish first)
        with pytest.raises(UploadConflictError, match="Cannot publish"):
            upload_service.handle_callback(result.upload_id, "i", "b", None)
