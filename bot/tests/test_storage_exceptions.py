"""
Тесты для типизированных исключений storage сервиса
Создано согласно TDD плану для проверки правильной обработки ошибок
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
import requests

from bot.services.core.storage.exceptions import (
    StorageError, StorageAuthError, StoragePermissionError, StorageRateLimitError,
    StorageNotFoundError, StorageValidationError, StorageTimeoutError, StorageNetworkError,
    StorageConfigError, StorageProviderError,
    create_storage_error_from_http_response, create_storage_error_from_exception
)
from bot.services.core.storage.pinata import SecurePinataUploader


class TestStorageExceptions:
    """Тесты для типизированных исключений storage сервиса"""
    
    def test_storage_error_base_class(self):
        """Тест: Базовый класс StorageError"""
        error = StorageError("Test error", status_code=500, provider="test")
        
        assert str(error) == "Test error (HTTP 500) [test]"
        assert error.status_code == 500
        assert error.provider == "test"
    
    def test_storage_auth_error(self):
        """Тест: Ошибка аутентификации"""
        error = StorageAuthError("Invalid credentials", provider="pinata")
        
        assert str(error) == "Invalid credentials (HTTP 401) [pinata]"
        assert error.status_code == 401
        assert error.provider == "pinata"
    
    def test_storage_permission_error(self):
        """Тест: Ошибка разрешений"""
        error = StoragePermissionError("Insufficient permissions", provider="pinata")
        
        assert str(error) == "Insufficient permissions (HTTP 403) [pinata]"
        assert error.status_code == 403
        assert error.provider == "pinata"
    
    def test_storage_rate_limit_error(self):
        """Тест: Ошибка rate limiting"""
        error = StorageRateLimitError("Rate limit exceeded", provider="pinata", retry_after=60)
        
        assert str(error) == "Rate limit exceeded (HTTP 429) [pinata] (retry after 60s)"
        assert error.status_code == 429
        assert error.retry_after == 60
    
    def test_storage_not_found_error(self):
        """Тест: Ошибка - ресурс не найден"""
        error = StorageNotFoundError("Resource not found", provider="pinata", cid="QmTest")
        
        assert str(error) == "Resource not found (HTTP 404) [pinata] (CID: QmTest)"
        assert error.status_code == 404
        assert error.cid == "QmTest"
    
    def test_storage_validation_error(self):
        """Тест: Ошибка валидации"""
        error = StorageValidationError("Validation failed", provider="pinata", field="file_size")
        
        assert str(error) == "Validation failed (HTTP 400) [pinata] (field: file_size)"
        assert error.status_code == 400
        assert error.field == "file_size"
    
    def test_storage_timeout_error(self):
        """Тест: Ошибка таймаута"""
        error = StorageTimeoutError("Operation timeout", provider="pinata", timeout=30.0)
        
        assert str(error) == "Operation timeout [pinata] (timeout: 30.0s)"
        assert error.timeout == 30.0
    
    def test_storage_network_error(self):
        """Тест: Ошибка сети"""
        original_error = requests.exceptions.ConnectionError("Connection failed")
        error = StorageNetworkError("Network error", provider="pinata", original_error=original_error)
        
        assert "Network error [pinata] (original:" in str(error)
        assert error.original_error == original_error
    
    def test_storage_config_error(self):
        """Тест: Ошибка конфигурации"""
        error = StorageConfigError("Configuration error", missing_key="API_KEY")
        
        assert str(error) == "Configuration error (missing: API_KEY)"
        assert error.missing_key == "API_KEY"
    
    def test_storage_provider_error(self):
        """Тест: Ошибка провайдера"""
        error = StorageProviderError("Server error", provider="pinata", status_code=500)
        
        assert str(error) == "Server error (HTTP 500) [pinata]"
        assert error.status_code == 500


class TestExceptionCreationFunctions:
    """Тесты для утилитарных функций создания исключений"""
    
    def test_create_storage_error_from_http_response_401(self):
        """Тест: Создание ошибки аутентификации из HTTP 401"""
        error = create_storage_error_from_http_response(401, "Unauthorized", "pinata")
        
        assert isinstance(error, StorageAuthError)
        assert error.status_code == 401
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_http_response_403(self):
        """Тест: Создание ошибки разрешений из HTTP 403"""
        error = create_storage_error_from_http_response(403, "Forbidden", "pinata")
        
        assert isinstance(error, StoragePermissionError)
        assert error.status_code == 403
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_http_response_429(self):
        """Тест: Создание ошибки rate limiting из HTTP 429"""
        error = create_storage_error_from_http_response(429, "Too Many Requests", "pinata")
        
        assert isinstance(error, StorageRateLimitError)
        assert error.status_code == 429
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_http_response_404(self):
        """Тест: Создание ошибки not found из HTTP 404"""
        error = create_storage_error_from_http_response(404, "Not Found", "pinata")
        
        assert isinstance(error, StorageNotFoundError)
        assert error.status_code == 404
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_http_response_400(self):
        """Тест: Создание ошибки валидации из HTTP 400"""
        error = create_storage_error_from_http_response(400, "Bad Request", "pinata")
        
        assert isinstance(error, StorageValidationError)
        assert error.status_code == 400
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_http_response_500(self):
        """Тест: Создание ошибки провайдера из HTTP 500"""
        error = create_storage_error_from_http_response(500, "Internal Server Error", "pinata")
        
        assert isinstance(error, StorageProviderError)
        assert error.status_code == 500
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_exception_timeout(self):
        """Тест: Создание ошибки таймаута из исключения"""
        original_error = requests.exceptions.Timeout("Request timeout")
        error = create_storage_error_from_exception(original_error, "pinata")
        
        assert isinstance(error, StorageTimeoutError)
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_exception_connection(self):
        """Тест: Создание ошибки сети из исключения"""
        original_error = requests.exceptions.ConnectionError("Connection failed")
        error = create_storage_error_from_exception(original_error, "pinata")
        
        assert isinstance(error, StorageNetworkError)
        assert error.provider == "pinata"
        assert error.original_error == original_error
    
    def test_create_storage_error_from_exception_generic(self):
        """Тест: Создание общей ошибки из исключения"""
        original_error = ValueError("Invalid value")
        error = create_storage_error_from_exception(original_error, "pinata")
        
        assert isinstance(error, StorageError)
        assert error.provider == "pinata"
    
    def test_create_storage_error_from_exception_already_storage_error(self):
        """Тест: Передача уже существующего StorageError"""
        original_error = StorageAuthError("Already auth error", "pinata")
        error = create_storage_error_from_exception(original_error, "pinata")
        
        assert error is original_error


class TestSecurePinataUploaderExceptions:
    """Тесты для SecurePinataUploader с типизированными исключениями"""
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    def test_uploader_init_with_valid_credentials(self, mock_load_dotenv):
        """Тест: Инициализация с валидными credentials"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        assert uploader.api_key == 'test_key'
        assert uploader.secret_api_key == 'test_secret'
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_uploader_init_without_api_key(self, mock_load_dotenv):
        """Тест: Инициализация без API ключа"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        # Удаляем переменные окружения если они есть
        os.environ.pop('PINATA_API_KEY', None)
        os.environ.pop('PINATA_API_SECRET', None)
        
        with pytest.raises(StorageConfigError) as exc_info:
            SecurePinataUploader()
        
        assert exc_info.value.missing_key == "PINATA_API_KEY"
        assert "Pinata API key is missing" in str(exc_info.value)
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {'PINATA_API_KEY': 'test_key'}, clear=True)
    def test_uploader_init_without_api_secret(self, mock_load_dotenv):
        """Тест: Инициализация без API secret"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        # Устанавливаем только API key, но не secret
        os.environ['PINATA_API_KEY'] = 'test_key'
        os.environ.pop('PINATA_API_SECRET', None)
        
        with pytest.raises(StorageConfigError) as exc_info:
            SecurePinataUploader()
        
        assert exc_info.value.missing_key == "PINATA_API_SECRET"
        assert "Pinata API secret is missing" in str(exc_info.value)
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    def test_validate_file_nonexistent(self, mock_load_dotenv):
        """Тест: Валидация несуществующего файла"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        with pytest.raises(StorageValidationError) as exc_info:
            uploader.validate_file("/nonexistent/file.txt")
        
        assert exc_info.value.field == "file_path"
        assert "Файл не существует" in str(exc_info.value)
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    def test_validate_file_too_large(self, mock_load_dotenv):
        """Тест: Валидация слишком большого файла"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        # Создаем временный файл больше 50MB
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'0' * (50 * 1024 * 1024 + 1))  # 50MB + 1 byte
            temp_file = f.name
        
        try:
            with pytest.raises(StorageValidationError) as exc_info:
                uploader.validate_file(temp_file)
            
            assert exc_info.value.field == "file_size"
            assert "Файл слишком большой" in str(exc_info.value)
        finally:
            os.unlink(temp_file)
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    def test_upload_text_empty_data(self, mock_load_dotenv):
        """Тест: Загрузка пустых данных"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        with pytest.raises(StorageValidationError) as exc_info:
            uploader.upload_text("")
        
        assert exc_info.value.field == "data"
        assert "Data cannot be empty" in str(exc_info.value)
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    def test_download_json_empty_cid(self, mock_load_dotenv):
        """Тест: Скачивание с пустым CID"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        with pytest.raises(StorageValidationError) as exc_info:
            uploader.download_json("")
        
        assert exc_info.value.field == "cid"
        assert "CID cannot be empty" in str(exc_info.value)
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    @patch('requests.request')
    def test_make_request_http_error_401(self, mock_request, mock_load_dotenv):
        """Тест: HTTP ошибка 401 в _make_request"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        # Мокаем ответ с 401
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_request.return_value = mock_response
        
        with pytest.raises(StorageAuthError) as exc_info:
            uploader._make_request('POST', 'https://api.pinata.cloud/test')
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.provider == "pinata"
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    @patch('requests.request')
    def test_make_request_http_error_403(self, mock_request, mock_load_dotenv):
        """Тест: HTTP ошибка 403 в _make_request"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        # Мокаем ответ с 403
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "Forbidden"}
        mock_request.return_value = mock_response
        
        with pytest.raises(StoragePermissionError) as exc_info:
            uploader._make_request('POST', 'https://api.pinata.cloud/test')
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.provider == "pinata"
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    @patch('requests.request')
    def test_make_request_http_error_429(self, mock_request, mock_load_dotenv):
        """Тест: HTTP ошибка 429 в _make_request"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        # Мокаем ответ с 429
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Too Many Requests"}
        mock_request.return_value = mock_response
        
        with pytest.raises(StorageRateLimitError) as exc_info:
            uploader._make_request('POST', 'https://api.pinata.cloud/test')
        
        assert exc_info.value.status_code == 429
        assert exc_info.value.provider == "pinata"
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    @patch('requests.request')
    def test_make_request_timeout_error(self, mock_request, mock_load_dotenv):
        """Тест: Ошибка таймаута в _make_request"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        # Мокаем таймаут
        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with pytest.raises(StorageTimeoutError) as exc_info:
            uploader._make_request('POST', 'https://api.pinata.cloud/test')
        
        assert exc_info.value.provider == "pinata"
        # 🔧 ИСПРАВЛЕНИЕ: Изменено с 30 на 60, чтобы соответствовать реальной конфигурации REQUEST_TIMEOUT
        assert exc_info.value.timeout == 60  # REQUEST_TIMEOUT = 60
    
    @patch('bot.services.core.storage.pinata.load_dotenv')
    @patch.dict(os.environ, {
        'PINATA_API_KEY': 'test_key',
        'PINATA_API_SECRET': 'test_secret'
    })
    @patch('requests.request')
    def test_make_request_connection_error(self, mock_request, mock_load_dotenv):
        """Тест: Ошибка соединения в _make_request"""
        # Мокаем load_dotenv чтобы не загружать .env файл
        mock_load_dotenv.return_value = None
        
        uploader = SecurePinataUploader()
        
        # Мокаем ошибку соединения
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with pytest.raises(StorageNetworkError) as exc_info:
            uploader._make_request('POST', 'https://api.pinata.cloud/test')
        
        assert exc_info.value.provider == "pinata"
        assert "Connection error" in str(exc_info.value)


class TestExceptionIntegration:
    """Интеграционные тесты исключений"""
    
    def test_exception_hierarchy(self):
        """Тест: Иерархия исключений"""
        # Проверяем, что все исключения наследуются от StorageError
        exceptions = [
            StorageAuthError("test"),
            StoragePermissionError("test"),
            StorageRateLimitError("test"),
            StorageNotFoundError("test"),
            StorageValidationError("test"),
            StorageTimeoutError("test"),
            StorageNetworkError("test"),
            StorageConfigError("test"),
            StorageProviderError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, StorageError)
            assert isinstance(exc, Exception)
    
    def test_exception_serialization(self):
        """Тест: Сериализация исключений"""
        error = StorageAuthError("Test error", provider="pinata")
        
        # Проверяем, что исключение можно преобразовать в строку
        error_str = str(error)
        assert "Test error" in error_str
        assert "401" in error_str
        assert "pinata" in error_str
    
    def test_exception_attributes(self):
        """Тест: Атрибуты исключений"""
        error = StorageRateLimitError("Rate limit", provider="pinata", retry_after=60)
        
        assert hasattr(error, 'message')
        assert hasattr(error, 'status_code')
        assert hasattr(error, 'provider')
        assert hasattr(error, 'retry_after')
        
        assert error.message == "Rate limit"
        assert error.status_code == 429
        assert error.provider == "pinata"
        assert error.retry_after == 60 