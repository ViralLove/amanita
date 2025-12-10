"""
Unit тесты для ArWeaveUploader - только чтение (download)
Тестируем функционал чтения через HTTP API с использованием моков
"""

import pytest
import os
import json
import importlib
from unittest.mock import patch, Mock, MagicMock
from bot.services.core.storage import ar_weave
from bot.services.core.storage.ar_weave import ArWeaveUploader
import requests


@pytest.mark.unit
class TestArWeaveUploaderTDD:
    """
    TDD тесты для ArWeaveUploader - базовый функционал
    """
    
    def test_arweave_initialization_with_valid_key(self):
        """✅ Green: Инициализация с валидным ключом (JSON строка)"""
        # ✅ ИСПРАВЛЕНО: Используем валидный RSA ключ с обязательными полями
        test_key = '{"kty":"RSA","e":"AQAB","n":"test_n_value","d":"test_d_value","p":"test_p","q":"test_q","dp":"test_dp","dq":"test_dq","qi":"test_qi"}'
        
        # ✅ ИСПРАВЛЕНО: Патчим bot.config.ARWEAVE_PRIVATE_KEY и ar_weave.ARWEAVE_PRIVATE_KEY
        import bot.config as config_module
        original_key = config_module.ARWEAVE_PRIVATE_KEY
        
        try:
            config_module.ARWEAVE_PRIVATE_KEY = test_key
            # Также патчим в ar_weave модуле после перезагрузки
            importlib.reload(ar_weave)
            ar_weave.ARWEAVE_PRIVATE_KEY = test_key
            
        uploader = ArWeaveUploader()
            assert uploader.private_key == test_key
        finally:
            # Восстанавливаем оригинальное значение
            config_module.ARWEAVE_PRIVATE_KEY = original_key
            importlib.reload(ar_weave)
    
    def test_arweave_initialization_without_key(self):
        """✅ Green: Инициализация без ключа вызывает ошибку"""
        # ✅ ИСПРАВЛЕНО: Патчим bot.config.ARWEAVE_PRIVATE_KEY = None
        import bot.config as config_module
        original_key = config_module.ARWEAVE_PRIVATE_KEY
        
        try:
            config_module.ARWEAVE_PRIVATE_KEY = None
            importlib.reload(ar_weave)
            ar_weave.ARWEAVE_PRIVATE_KEY = None
            
        with pytest.raises(FileNotFoundError):
            ArWeaveUploader()
        finally:
            # Восстанавливаем оригинальное значение
            config_module.ARWEAVE_PRIVATE_KEY = original_key
            importlib.reload(ar_weave)
    
    def test_arweave_public_url_format(self):
        """✅ Green: Проверка формата публичного URL"""
        # ✅ ИСПРАВЛЕНО: Используем валидный ключ и правильный патчинг
        test_key = '{"kty":"RSA","e":"AQAB","n":"test_n_value","d":"test_d_value","p":"test_p","q":"test_q","dp":"test_dp","dq":"test_dq","qi":"test_qi"}'
        import bot.config as config_module
        original_key = config_module.ARWEAVE_PRIVATE_KEY
        
        try:
            config_module.ARWEAVE_PRIVATE_KEY = test_key
            importlib.reload(ar_weave)
            ar_weave.ARWEAVE_PRIVATE_KEY = test_key
            uploader = ArWeaveUploader()
            tx_id = "TestTransactionID123456789012345678901234567890123"
            url = uploader.get_public_url(tx_id)
            assert url == f"https://arweave.net/{tx_id}"
        finally:
            # Восстанавливаем оригинальное значение
            config_module.ARWEAVE_PRIVATE_KEY = original_key
            importlib.reload(ar_weave)


class TestArWeaveUploaderDownloadJSON:
    """
    Unit тесты для download_json() - чтение JSON через HTTP API
    """
    
    @pytest.fixture
    def arweave_uploader(self):
        """Фикстура для создания ArWeaveUploader с моком окружения"""
        test_key = '{"kty":"RSA","e":"AQAB","n":"test_n_value","d":"test_d_value","p":"test_p","q":"test_q","dp":"test_dp","dq":"test_dq","qi":"test_qi"}'
        import bot.config as config_module
        original_key = config_module.ARWEAVE_PRIVATE_KEY
        
        try:
            config_module.ARWEAVE_PRIVATE_KEY = test_key
            importlib.reload(ar_weave)
            ar_weave.ARWEAVE_PRIVATE_KEY = test_key
            yield ArWeaveUploader()
        finally:
            config_module.ARWEAVE_PRIVATE_KEY = original_key
            importlib.reload(ar_weave)
    
    def test_arweave_download_json_success(self, arweave_uploader):
        """Тест успешного чтения JSON через HTTP API"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        expected_data = {"test": "data", "key": "value"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_response.content = json.dumps(expected_data).encode('utf-8')
        mock_response.text = json.dumps(expected_data)
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response) as mock_get:
            result = arweave_uploader.download_json(test_cid)
            
            # Проверяем результат
            assert result == expected_data
            
            # Проверяем что requests.get был вызван с правильными параметрами
            mock_get.assert_called_once_with(
                f"https://arweave.net/{test_cid}",
                timeout=30
            )
    
    def test_arweave_download_json_404(self, arweave_uploader):
        """Тест обработки HTTP 404 (несуществующая транзакция)"""
        # Arrange
        test_cid = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b''
        mock_response.text = 'Not Found'
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
    
    def test_arweave_download_json_network_error(self, arweave_uploader):
        """Тест обработки сетевых ошибок"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        
        # Act & Assert - ConnectionError
        with patch('bot.services.core.storage.ar_weave.requests.get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
        
        # Act & Assert - TimeoutError
        with patch('bot.services.core.storage.ar_weave.requests.get', side_effect=requests.exceptions.Timeout("Request timeout")):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
        
        # Act & Assert - RequestException (общий класс)
        with patch('bot.services.core.storage.ar_weave.requests.get', side_effect=requests.exceptions.RequestException("Request failed")):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
    
    def test_arweave_download_json_invalid_json(self, arweave_uploader):
        """Тест обработки невалидного JSON"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        invalid_json_str = '{"test": "data" invalid}'
        invalid_json_bytes = invalid_json_str.encode('utf-8')
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = invalid_json_bytes
        mock_response.text = invalid_json_str
        # ✅ ИСПРАВЛЕНО: JSONDecodeError требует правильный формат (msg, doc, pos)
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", invalid_json_str, 18)
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
    
    def test_arweave_download_json_empty_response(self, arweave_uploader):
        """Тест обработки пустого ответа"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_response.text = ''
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
    
    def test_arweave_download_json_ar_prefix(self, arweave_uploader):
        """Тест обработки префикса ar://"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        test_cid_with_prefix = f"ar://{test_cid}"
        expected_data = {"test": "data"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_response.content = json.dumps(expected_data).encode('utf-8')
        mock_response.text = json.dumps(expected_data)
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response) as mock_get:
            result = arweave_uploader.download_json(test_cid_with_prefix)
            
            assert result == expected_data
            # Проверяем что префикс ar:// был удален
            mock_get.assert_called_once_with(
                f"https://arweave.net/{test_cid}",
                timeout=30
            )
    
    def test_arweave_download_json_http_error(self, arweave_uploader):
        """Тест обработки других HTTP ошибок (500, 503)"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        
        # Test 500
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.content = b'Internal Server Error'
        mock_response_500.text = 'Internal Server Error'
        
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response_500):
            result = arweave_uploader.download_json(test_cid)
            assert result is None
        
        # Test 503
        mock_response_503 = Mock()
        mock_response_503.status_code = 503
        mock_response_503.content = b'Service Unavailable'
        mock_response_503.text = 'Service Unavailable'
        
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response_503):
            result = arweave_uploader.download_json(test_cid)
            assert result is None


class TestArWeaveUploaderDownloadFile:
    """
    Unit тесты для download_file() - чтение файлов через HTTP API
    """
    
    @pytest.fixture
    def arweave_uploader(self):
        """Фикстура для создания ArWeaveUploader с моком окружения"""
        test_key = '{"kty":"RSA","e":"AQAB","n":"test_n_value","d":"test_d_value","p":"test_p","q":"test_q","dp":"test_dp","dq":"test_dq","qi":"test_qi"}'
        import bot.config as config_module
        original_key = config_module.ARWEAVE_PRIVATE_KEY
        
        try:
            config_module.ARWEAVE_PRIVATE_KEY = test_key
            importlib.reload(ar_weave)
            ar_weave.ARWEAVE_PRIVATE_KEY = test_key
            yield ArWeaveUploader()
        finally:
            config_module.ARWEAVE_PRIVATE_KEY = original_key
            importlib.reload(ar_weave)
    
    def test_arweave_download_file_success(self, arweave_uploader):
        """Тест успешного чтения файла через HTTP API"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        expected_content = b"Binary file content"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = expected_content
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response) as mock_get:
            result = arweave_uploader.download_file(test_cid)
            
            assert result == expected_content
            assert isinstance(result, bytes)
            
            # Проверяем что requests.get был вызван с правильными параметрами
            mock_get.assert_called_once_with(
                f"https://arweave.net/{test_cid}",
                timeout=30
            )
    
    def test_arweave_download_file_404(self, arweave_uploader):
        """Тест обработки HTTP 404 для файла"""
        # Arrange
        test_cid = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b''
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response):
            result = arweave_uploader.download_file(test_cid)
            assert result is None
    
    def test_arweave_download_file_network_error(self, arweave_uploader):
        """Тест обработки сетевых ошибок для файла"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', side_effect=requests.exceptions.RequestException("Network error")):
            result = arweave_uploader.download_file(test_cid)
            assert result is None


class TestArWeaveUploaderValidation:
    """
    Unit тесты для валидации и конфигурации
    """
    
    @pytest.fixture
    def arweave_uploader(self):
        """Фикстура для создания ArWeaveUploader с моком окружения"""
        test_key = '{"kty":"RSA","e":"AQAB","n":"test_n_value","d":"test_d_value","p":"test_p","q":"test_q","dp":"test_dp","dq":"test_dq","qi":"test_qi"}'
        import bot.config as config_module
        original_key = config_module.ARWEAVE_PRIVATE_KEY
        
        try:
            config_module.ARWEAVE_PRIVATE_KEY = test_key
            importlib.reload(ar_weave)
            ar_weave.ARWEAVE_PRIVATE_KEY = test_key
            yield ArWeaveUploader()
        finally:
            config_module.ARWEAVE_PRIVATE_KEY = original_key
            importlib.reload(ar_weave)
    
    def test_arweave_timeout_configuration(self, arweave_uploader):
        """Тест что timeout=30 используется в requests.get()"""
        # Arrange
        test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.content = b'{"test": "data"}'
        
        # Act & Assert
        with patch('bot.services.core.storage.ar_weave.requests.get', return_value=mock_response) as mock_get:
            arweave_uploader.download_json(test_cid)
            
            # Проверяем что timeout=30 был передан
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['timeout'] == 30
    
    def test_arweave_invalid_transaction_id(self, arweave_uploader):
        """Тест валидации transaction ID через is_valid_identifier()"""
        # Arrange & Act & Assert
        # Валидные форматы
        # IPFS CID v1 (длиннее 46 символов, начинается с bafy)
        assert arweave_uploader.is_valid_identifier("bafybeiemxf5abjwjbikoz4mc3a3dla6ual3jsgpdr4cjr3oz3evfyavhwq") == True
        
        # Невалидные форматы
        assert arweave_uploader.is_valid_identifier("") == False  # Пустая строка
        assert arweave_uploader.is_valid_identifier("invalid") == False  # Невалидный формат
        assert arweave_uploader.is_valid_identifier("123") == False  # Слишком короткий


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
