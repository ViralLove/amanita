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


@pytest.mark.unit
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