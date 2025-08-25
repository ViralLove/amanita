"""
Тесты для Pydantic моделей API
"""
import pytest
from bot.api.models.common import (
    EthereumAddress, ApiKey, Timestamp, RequestId, Signature, Nonce
)
from bot.api.models.health import HealthCheckResponse, HealthStatus, ServiceInfo
from bot.api.models.errors import ErrorResponse, ErrorDetail
from bot.api.models.auth import AuthRequest, AuthResponse
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
        from bot.api.models.common import Timestamp, RequestId
        
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
        from bot.api.models.common import Timestamp, RequestId
        
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
        from bot.api.models.common import Timestamp, RequestId, Signature, Nonce
        
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
        from bot.api.models.common import Timestamp, RequestId
        
        response = AuthResponse(
            success=True,
            request_id=RequestId("test-123"),
            timestamp=Timestamp(1640995200)
        )
        
        assert response.success is True
        assert str(response.request_id) == "test-123"
        assert int(response.timestamp) == 1640995200 

# ============================================================================
# ТЕСТЫ ДЛЯ НОВЫХ МОДЕЛЕЙ КАТАЛОГА ПРОДАВЦА
# ============================================================================

from bot.api.models.product import ProductCatalogItem, ProductCatalogResponse

class TestProductCatalogItem:
    """Тесты для модели ProductCatalogItem"""
    
    def test_valid_product_catalog_item(self):
        """Тест создания валидного ProductCatalogItem"""
        valid_data = {
            "id": "123",
            "title": "Amanita Muscaria Powder",
            "status": 1,
            "cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            "categories": ["mushroom", "powder"],
            "forms": ["powder"],
            "species": "Amanita Muscaria",
            "cover_image_url": "https://ipfs.io/ipfs/QmImageCID",
            "prices": [
                {
                    "price": 50,
                    "currency": "EUR",
                    "weight": "100",
                    "weight_unit": "g",
                    "form": "powder"
                }
            ]
        }
        
        item = ProductCatalogItem(**valid_data)
        
        assert item.id == "123"
        assert item.title == "Amanita Muscaria Powder"
        assert item.status == 1
        assert item.cid == "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        assert item.categories == ["mushroom", "powder"]
        assert item.forms == ["powder"]
        assert item.species == "Amanita Muscaria"
        assert item.cover_image_url == "https://ipfs.io/ipfs/QmImageCID"
        assert len(item.prices) == 1
        assert item.prices[0]["price"] == 50
        assert item.prices[0]["currency"] == "EUR"
    
    def test_product_catalog_item_without_optional_fields(self):
        """Тест создания ProductCatalogItem без опциональных полей"""
        minimal_data = {
            "id": "123",
            "title": "Test Product",
            "status": 0,
            "cid": "QmTestCID",
            "categories": [],
            "forms": [],
            "species": "Test Species",
            "prices": []
        }
        
        item = ProductCatalogItem(**minimal_data)
        
        assert item.id == "123"
        assert item.title == "Test Product"
        assert item.status == 0
        assert item.cid == "QmTestCID"
        assert item.categories == []
        assert item.forms == []
        assert item.species == "Test Species"
        assert item.cover_image_url is None
        assert item.prices == []
    
    def test_product_catalog_item_status_validation(self):
        """Тест валидации статуса продукта"""
        # Валидные статусы
        valid_statuses = [0, 1]
        for status in valid_statuses:
            data = {
                "id": "123",
                "title": "Test Product",
                "status": status,
                "cid": "QmTestCID",
                "categories": [],
                "forms": [],
                "species": "Test Species",
                "prices": []
            }
            item = ProductCatalogItem(**data)
            assert item.status == status
        
        # Невалидные статусы
        invalid_statuses = [-1, 2, 10]
        for status in invalid_statuses:
            data = {
                "id": "123",
                "title": "Test Product",
                "status": status,
                "cid": "QmTestCID",
                "categories": [],
                "forms": [],
                "species": "Test Species",
                "prices": []
            }
            with pytest.raises(ValueError):
                ProductCatalogItem(**data)

class TestProductCatalogResponse:
    """Тесты для модели ProductCatalogResponse"""
    
    def test_valid_product_catalog_response(self):
        """Тест создания валидного ProductCatalogResponse"""
        valid_data = {
            "seller_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
            "total_count": 2,
            "products": [
                {
                    "id": "123",
                    "title": "Product 1",
                    "status": 1,
                    "cid": "QmCID1",
                    "categories": ["category1"],
                    "forms": ["form1"],
                    "species": "Species 1",
                    "prices": []
                },
                {
                    "id": "456",
                    "title": "Product 2",
                    "status": 1,
                    "cid": "QmCID2",
                    "categories": ["category2"],
                    "forms": ["form2"],
                    "species": "Species 2",
                    "prices": []
                }
            ],
            "catalog_version": 10,
            "last_updated": "2024-01-15T10:30:00Z"
        }
        
        response = ProductCatalogResponse(**valid_data)
        
        assert response.seller_address == "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"
        assert response.total_count == 2
        assert len(response.products) == 2
        assert response.catalog_version == 10
        assert response.last_updated == "2024-01-15T10:30:00Z"
        
        # Проверяем продукты
        assert response.products[0].id == "123"
        assert response.products[0].title == "Product 1"
        assert response.products[1].id == "456"
        assert response.products[1].title == "Product 2"
    
    def test_product_catalog_response_without_optional_fields(self):
        """Тест создания ProductCatalogResponse без опциональных полей"""
        minimal_data = {
            "seller_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
            "total_count": 0,
            "products": []
        }
        
        response = ProductCatalogResponse(**minimal_data)
        
        assert response.seller_address == "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"
        assert response.total_count == 0
        assert response.products == []
        assert response.catalog_version is None
        assert response.last_updated is None
    
    def test_product_catalog_response_total_count_validation(self):
        """Тест валидации total_count"""
        # Валидные значения
        valid_counts = [0, 1, 100, 1000]
        for count in valid_counts:
            data = {
                "seller_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
                "total_count": count,
                "products": []
            }
            response = ProductCatalogResponse(**data)
            assert response.total_count == count
        
        # Невалидные значения
        invalid_counts = [-1, -10]
        for count in invalid_counts:
            data = {
                "seller_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
                "total_count": count,
                "products": []
            }
            with pytest.raises(ValueError):
                ProductCatalogResponse(**data)
    
    def test_product_catalog_response_products_consistency(self):
        """Тест согласованности total_count и количества продуктов"""
        # Случай когда total_count не соответствует количеству продуктов
        data = {
            "seller_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
            "total_count": 5,
            "products": [
                {
                    "id": "123",
                    "title": "Product 1",
                    "status": 1,
                    "cid": "QmCID1",
                    "categories": ["category1"],
                    "forms": ["form1"],
                    "species": "Species 1",
                    "prices": []
                }
            ]
        }
        
        # Модель должна принять данные (валидация только типов, не бизнес-логики)
        response = ProductCatalogResponse(**data)
        assert response.total_count == 5
        assert len(response.products) == 1

# ============================================================================
# ЗАВЕРШЕНИЕ ТЕСТОВ
# ============================================================================ 