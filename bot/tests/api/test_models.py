"""
Тесты для Pydantic моделей API
"""
import pytest
from api.models.common import (
    EthereumAddress, ApiKey, Timestamp, RequestId, Signature, Nonce
)
from api.models.health import HealthCheckResponse, HealthStatus, ServiceInfo
from api.models.errors import ErrorResponse, ErrorDetail
from api.models.auth import AuthRequest, AuthResponse
from test_data import (
    VALID_ETHEREUM_ADDRESSES, INVALID_ETHEREUM_ADDRESSES,
    VALID_API_KEYS, INVALID_API_KEYS
)


class TestEthereumAddress:
    """Тесты для валидации Ethereum адресов"""
    
    @pytest.mark.parametrize("valid_address", VALID_ETHEREUM_ADDRESSES)
    def test_valid_ethereum_address(self, valid_address):
        """Тест валидации корректных Ethereum адресов"""
        address = EthereumAddress(valid_address)
        assert str(address) == valid_address.lower()
    
    @pytest.mark.parametrize("invalid_address", INVALID_ETHEREUM_ADDRESSES)
    def test_invalid_ethereum_address(self, invalid_address):
        """Тест валидации некорректных Ethereum адресов"""
        with pytest.raises(ValueError, match="Invalid Ethereum address format"):
            EthereumAddress(invalid_address)


class TestApiKey:
    """Тесты для валидации API ключей"""
    
    @pytest.mark.parametrize("valid_key", VALID_API_KEYS)
    def test_valid_api_key(self, valid_key):
        """Тест валидации корректных API ключей"""
        key = ApiKey(valid_key)
        assert str(key) == valid_key.lower()
    
    @pytest.mark.parametrize("invalid_key", INVALID_API_KEYS)
    def test_invalid_api_key(self, invalid_key):
        """Тест валидации некорректных API ключей"""
        with pytest.raises(ValueError, match="Invalid API key format"):
            ApiKey(invalid_key)


class TestTimestamp:
    """Тесты для валидации timestamp"""
    
    def test_valid_timestamp(self):
        """Тест валидации корректного timestamp"""
        import time
        current_time = int(time.time())
        timestamp = Timestamp(current_time)
        assert int(timestamp) == current_time
    
    def test_invalid_timestamp_negative(self):
        """Тест валидации отрицательного timestamp"""
        with pytest.raises(ValueError, match="Timestamp must be a positive integer"):
            Timestamp(-1)
    
    def test_invalid_timestamp_string(self):
        """Тест валидации timestamp из строки"""
        import time
        current_time = int(time.time())
        timestamp = Timestamp(str(current_time))
        assert int(timestamp) == current_time


class TestRequestId:
    """Тесты для валидации Request ID"""
    
    def test_valid_request_id(self):
        """Тест валидации корректного Request ID"""
        request_id = RequestId("req_1234567890abcdef")
        assert str(request_id) == "req_1234567890abcdef"
    
    def test_invalid_request_id_too_short(self):
        """Тест валидации слишком короткого Request ID"""
        with pytest.raises(ValueError, match="Invalid request ID format"):
            RequestId("123")
    
    def test_invalid_request_id_special_chars(self):
        """Тест валидации Request ID со специальными символами"""
        with pytest.raises(ValueError, match="Invalid request ID format"):
            RequestId("req@#$%^&*()")


class TestHealthModels:
    """Тесты для моделей health check"""
    
    def test_health_status_model(self):
        """Тест модели HealthStatus"""
        status = HealthStatus(
            status="healthy",
            message="Service is running normally"
        )
        assert status.status == "healthy"
        assert status.message == "Service is running normally"
    
    def test_service_info_model(self):
        """Тест модели ServiceInfo"""
        service = ServiceInfo(
            name="amanita_api",
            version="1.0.0",
            environment="development"
        )
        assert service.name == "amanita_api"
        assert service.version == "1.0.0"
        assert service.environment == "development"
    
    def test_health_check_response_model(self):
        """Тест модели HealthCheckResponse"""
        from api.models.common import Timestamp, RequestId
        
        response = HealthCheckResponse(
            success=True,
            status=HealthStatus(status="healthy", message="OK"),
            service=ServiceInfo(name="test", version="1.0.0", environment="test"),
            timestamp=Timestamp(1640995200),
            request_id=RequestId("test-123"),
            uptime=None
        )
        
        assert response.success is True
        assert response.status.status == "healthy"
        assert response.service.name == "test"


class TestErrorModels:
    """Тесты для моделей ошибок"""
    
    def test_error_detail_model(self):
        """Тест модели ErrorDetail"""
        detail = ErrorDetail(
            field="client_address",
            message="Invalid Ethereum address format",
            value="invalid-address"
        )
        assert detail.field == "client_address"
        assert detail.message == "Invalid Ethereum address format"
        assert detail.value == "invalid-address"
    
    def test_error_response_model(self):
        """Тест модели ErrorResponse"""
        from api.models.common import Timestamp, RequestId
        
        response = ErrorResponse(
            success=False,
            error="validation_error",
            message="Validation failed",
            details=[ErrorDetail(field="test", message="Test error")],
            request_id=RequestId("test-123"),
            timestamp=Timestamp(1640995200),
            path="/test"
        )
        
        assert response.success is False
        assert response.error == "validation_error"
        assert len(response.details) == 1
        assert response.details[0].field == "test"


class TestAuthModels:
    """Тесты для моделей аутентификации"""
    
    def test_auth_request_model(self):
        """Тест модели AuthRequest"""
        from api.models.common import Timestamp, RequestId, Signature, Nonce
        
        request = AuthRequest(
            api_key=ApiKey("a" * 64),
            nonce=Nonce(12345),
            timestamp=Timestamp(1640995200),
            signature=Signature("signature"),
            request_id=RequestId("test-123")
        )
        
        assert str(request.api_key) == "a" * 64
        assert int(request.nonce) == 12345
        assert int(request.timestamp) == 1640995200
        assert str(request.signature) == "signature"
    
    def test_auth_response_model(self):
        """Тест модели AuthResponse"""
        from api.models.common import Timestamp, RequestId
        
        response = AuthResponse(
            success=True,
            request_id=RequestId("test-123"),
            timestamp=Timestamp(1640995200)
        )
        
        assert response.success is True
        assert str(response.request_id) == "test-123"
        assert int(response.timestamp) == 1640995200 