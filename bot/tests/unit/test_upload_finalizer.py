"""
Unit tests for upload finalizer: run_finalizer с моком HTTP gateway (task 3.2).
"""

import pytest
from unittest.mock import MagicMock

from services.upload.finalizer import run_finalizer
from model.upload import PUBLISHED, FINALIZED


@pytest.mark.unit
class TestUploadFinalizer:
    def test_finalizer_200_sets_finalized(self):
        """Gateway возвращает 200 → запись переводится в finalized."""
        db = MagicMock()
        db.list_uploads_by_status.return_value = [
            {"upload_id": "u1", "bundle_tx_id": "bundle-tx-1"},
        ]
        fetch = lambda url: 200
        count = run_finalizer(db, fetch_url=fetch)
        assert count == 1
        db.update_upload_status.assert_called_once_with("u1", FINALIZED)

    def test_finalizer_404_leaves_published(self):
        """Gateway возвращает 404 → запись остаётся published, update не вызывается."""
        db = MagicMock()
        db.list_uploads_by_status.return_value = [
            {"upload_id": "u2", "bundle_tx_id": "bundle-tx-2"},
        ]
        fetch = lambda url: 404
        count = run_finalizer(db, fetch_url=fetch)
        assert count == 0
        db.update_upload_status.assert_not_called()

    def test_finalizer_fetch_raises_skips(self):
        """fetch бросает исключение → запись не обновляется."""
        db = MagicMock()
        db.list_uploads_by_status.return_value = [
            {"upload_id": "u3", "bundle_tx_id": "bundle-tx-3"},
        ]
        def fetch(url):
            raise ConnectionError("unavailable")
        count = run_finalizer(db, fetch_url=fetch)
        assert count == 0
        db.update_upload_status.assert_not_called()

    def test_finalizer_skips_row_without_bundle_tx_id(self):
        """Строка без bundle_tx_id пропускается."""
        db = MagicMock()
        db.list_uploads_by_status.return_value = [
            {"upload_id": "u4", "bundle_tx_id": None},
        ]
        count = run_finalizer(db, fetch_url=lambda u: 200)
        assert count == 0
        db.update_upload_status.assert_not_called()

    def test_finalizer_multiple_one_200_one_404(self):
        """Две записи: одна 200, одна 404 → одна finalized."""
        db = MagicMock()
        db.list_uploads_by_status.return_value = [
            {"upload_id": "u5", "bundle_tx_id": "b5"},
            {"upload_id": "u6", "bundle_tx_id": "b6"},
        ]
        def fetch(url):
            if "b5" in url:
                return 200
            return 404
        count = run_finalizer(db, fetch_url=fetch)
        assert count == 1
        db.update_upload_status.assert_called_once_with("u5", FINALIZED)
