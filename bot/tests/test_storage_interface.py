import pytest
import os
from unittest.mock import patch, MagicMock
from bot.services.core.storage.base import BaseStorageProvider
from bot.services.core.storage.pinata import SecurePinataUploader
from bot.services.core.storage.ar_weave import ArWeaveUploader

class TestStorageInterface:
    
    def test_base_storage_provider_abstract(self):
        """Тест что BaseStorageProvider нельзя инстанцировать"""
        with pytest.raises(TypeError):
            BaseStorageProvider()
    
    def test_pinata_implements_interface(self):
        """Тест что Pinata реализует интерфейс"""
        with patch.dict(os.environ, {'PINATA_API_KEY': 'test', 'PINATA_API_SECRET': 'test'}):
            pinata = SecurePinataUploader()
            assert hasattr(pinata, 'get_public_url')
            assert hasattr(pinata, 'upload_file')
            assert hasattr(pinata, 'download_json')
    
    def test_arweave_implements_interface(self):
        """Тест что ArWeave реализует интерфейс"""
        with patch.dict(os.environ, {'ARWEAVE_PRIVATE_KEY': 'test'}):
            arweave = ArWeaveUploader()
            assert hasattr(arweave, 'get_public_url')
            assert hasattr(arweave, 'upload_file')
            assert hasattr(arweave, 'download_json')
    
    def test_pinata_public_url(self):
        """Тест формирования публичного URL в Pinata"""
        with patch.dict(os.environ, {'PINATA_API_KEY': 'test', 'PINATA_API_SECRET': 'test'}):
            pinata = SecurePinataUploader()
            cid = "QmTestCID123456789"
            url = pinata.get_public_url(cid)
            assert url == f"https://gateway.pinata.cloud/ipfs/{cid}"
    
    def test_arweave_public_url(self):
        """Тест формирования публичного URL в ArWeave"""
        with patch.dict(os.environ, {'ARWEAVE_PRIVATE_KEY': 'test'}):
            arweave = ArWeaveUploader()
            tx_id = "TestTransactionID123456789012345678901234567890123"
            url = arweave.get_public_url(tx_id)
            assert url == f"https://arweave.net/{tx_id}"
