import pytest
import os
from unittest.mock import patch, MagicMock
from bot.services.core.storage.base import BaseStorageProvider
from bot.services.core.storage.ar_weave import ArWeaveUploader

@pytest.mark.unit
class TestStorageInterface:
    
    def test_base_storage_provider_abstract(self):
        """Тест что BaseStorageProvider нельзя инстанцировать"""
        with pytest.raises(TypeError):
            BaseStorageProvider()
    
    def test_arweave_implements_interface(self):
        """Тест что ArWeave реализует интерфейс"""
        with patch.dict(os.environ, {'ARWEAVE_PRIVATE_KEY': 'test'}):
            arweave = ArWeaveUploader()
            assert hasattr(arweave, 'get_public_url')
            assert hasattr(arweave, 'upload_file')
            assert hasattr(arweave, 'download_json')
    
    def test_arweave_public_url(self):
        """Тест формирования публичного URL в ArWeave"""
        with patch.dict(os.environ, {'ARWEAVE_PRIVATE_KEY': 'test'}):
            arweave = ArWeaveUploader()
            tx_id = "TestTransactionID123456789012345678901234567890123"
            url = arweave.get_public_url(tx_id)
            assert url == f"https://arweave.net/{tx_id}"
