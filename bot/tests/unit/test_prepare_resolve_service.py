"""
Unit tests for PrepareResolveService (task 3.3): prepare for wallet, resolve CID, download_metadata, validate_cid.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.upload.upload_service import PrepareResult
from services.upload.storage import PrepareResolveService, PrepareForDraftResult


@pytest.fixture
def mock_upload_service():
    return MagicMock()


@pytest.fixture
def mock_storage_provider():
    return MagicMock()


@pytest.fixture
def service(mock_upload_service, mock_storage_provider):
    return PrepareResolveService(mock_upload_service, mock_storage_provider)


class TestPrepareUploadForDraft:
    def test_returns_wallet_data(self, service, mock_upload_service):
        payload_descriptor = {"title": "Test", "activity_type": "event"}
        expected_bytes = b'{"activity_type": "event", "title": "Test"}'
        mock_upload_service.prepare.return_value = PrepareResult(
            upload_id="u1",
            upload_token="jwt.token",
            tags_for_item=[{"name": "Upload-Id", "value": "u1"}],
            anchor="anchor123",
            expires_at=datetime.now(timezone.utc),
            payload_hash="abc",
            payload_size=len(expected_bytes),
        )
        result = service.prepare_upload_for_draft("draft-1", "user-1", payload_descriptor)
        assert isinstance(result, PrepareForDraftResult)
        assert result.upload_id == "u1"
        assert result.upload_token == "jwt.token"
        assert result.payload_bytes == expected_bytes
        assert result.tags_for_item == [{"name": "Upload-Id", "value": "u1"}]
        assert result.anchor == "anchor123"

    def test_calls_upload_service_with_activity_id(self, service, mock_upload_service):
        mock_upload_service.prepare.return_value = PrepareResult(
            upload_id="u2",
            upload_token="tok",
            tags_for_item=[],
            anchor="a",
            expires_at=datetime.now(timezone.utc),
            payload_hash="h",
            payload_size=2,
        )
        service.prepare_upload_for_draft("draft-42", "user-99", {"x": 1})
        mock_upload_service.prepare.assert_called_once()
        call_kw = mock_upload_service.prepare.call_args[1]
        assert call_kw.get("activity_id") == "draft-42"


class TestResolveCidFromCallback:
    def test_returns_bundle_tx_id(self, service, mock_upload_service):
        mock_upload_service.handle_callback.return_value = None
        cid = service.resolve_cid_from_callback(
            "upload-1", "item-1", "bundle_tx_abc123", owner_address="0x123"
        )
        assert cid == "bundle_tx_abc123"

    def test_calls_handle_callback_with_args(self, service, mock_upload_service):
        service.resolve_cid_from_callback(
            "up1", "it1", "tx1", owner_address="0xabc"
        )
        mock_upload_service.handle_callback.assert_called_once_with(
            "up1", "it1", "tx1", owner_address="0xabc"
        )


class TestValidateCid:
    def test_delegates_to_provider_validate_ipfs_cid(self, service, mock_storage_provider):
        mock_storage_provider.validate_ipfs_cid.return_value = True
        assert service.validate_cid("A" * 43) is True
        mock_storage_provider.validate_ipfs_cid.assert_called_once_with("A" * 43)

    def test_delegates_false(self, service, mock_storage_provider):
        mock_storage_provider.validate_ipfs_cid.return_value = False
        assert service.validate_cid("short") is False


class TestDownloadMetadata:
    def test_returns_dict_from_provider(self, service, mock_storage_provider):
        mock_storage_provider.download_json.return_value = {"title": "Meta"}
        result = service.download_metadata("cid123")
        assert result == {"title": "Meta"}
        mock_storage_provider.download_json.assert_called_once_with("cid123")

    def test_returns_none_when_provider_returns_none(self, service, mock_storage_provider):
        mock_storage_provider.download_json.return_value = None
        assert service.download_metadata("cid") is None

    def test_returns_none_on_exception(self, service, mock_storage_provider):
        mock_storage_provider.download_json.side_effect = Exception("network")
        assert service.download_metadata("cid") is None
