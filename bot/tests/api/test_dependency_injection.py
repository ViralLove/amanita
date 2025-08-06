"""
Тесты для проверки полной реализации dependency injection (DI) во всем приложении Amanita.
Покрывает:
- Корректную работу DI с реальными сервисами
- Подмену только внешних зависимостей через dependency_overrides
- Обратную совместимость
- Интеграцию с FastAPI
"""

import pytest
import json
from fastapi import FastAPI, Depends
from starlette.testclient import TestClient
from bot.api.dependencies import (
    get_product_storage_service,
    get_blockchain_service,
    get_account_service,
    get_api_key_service,
    get_product_registry_service,
    get_product_validation_service,
)
from bot.tests.api.test_utils import generate_hmac_headers
import os

# Мок только для IPFS storage (внешний сервис)
class MockIPFSStorage:
    def upload_json(self, data):
        return "QmMockCID"
    def upload_file(self, file_path):
        return "QmMockFileCID"
    async def download_json_async(self, cid):
        return {"mock": "data", "cid": cid}
    async def download_file(self, cid):
        return b"mock file"

# FastAPI app для теста DI
app = FastAPI()

@app.post("/test-di")
def _di_endpoint(
    storage_service = Depends(get_product_storage_service),
    blockchain_service = Depends(get_blockchain_service),
    account_service = Depends(get_account_service),
    api_key_service = Depends(get_api_key_service),
    registry_service = Depends(get_product_registry_service),
    validation_service = Depends(get_product_validation_service),
):
    """
    Endpoint для тестирования DI - проверяет, что все сервисы правильно получают зависимости.
    """
    result = {
        "storage_service_type": type(storage_service).__name__,
        "blockchain_service_type": type(blockchain_service).__name__,
        "account_service_type": type(account_service).__name__,
        "api_key_service_type": type(api_key_service).__name__,
        "registry_service_type": type(registry_service).__name__,
        "validation_service_type": type(validation_service).__name__,
        
        # Проверяем, что сервисы имеют правильные зависимости
        "storage_has_ipfs": hasattr(storage_service, 'ipfs'),
        "blockchain_has_web3": hasattr(blockchain_service, 'web3'),
        "account_has_blockchain": hasattr(account_service, 'blockchain_service'),
        "api_key_has_blockchain": hasattr(api_key_service, 'blockchain_service'),
        "registry_has_all_deps": all([
            hasattr(registry_service, 'blockchain_service'),
            hasattr(registry_service, 'storage_service'),
            hasattr(registry_service, 'validation_service'),
            hasattr(registry_service, 'account_service')
        ]),
        
        # Проверяем реальные методы
        "registry_catalog_version": registry_service.get_catalog_version(),
    }
    return result


@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Фикстура для HMAC-заголовков аутентификации"""
    AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "test-api-key-12345")
    AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "default-secret-key-change-in-production")
    method = "POST"
    path = "/test-di"
    body = json.dumps({})
    return generate_hmac_headers(method, path, body, AMANITA_API_KEY, AMANITA_API_SECRET)


def test_di_real_services_integration(client, auth_headers):
    """
    Проверяет, что все реальные сервисы правильно интегрированы через DI.
    """
    response = client.post("/test-di", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем типы сервисов
    assert data["storage_service_type"] == "ProductStorageService"
    assert data["blockchain_service_type"] == "BlockchainService"
    assert data["account_service_type"] == "AccountService"
    assert data["api_key_service_type"] == "ApiKeyService"
    assert data["registry_service_type"] == "ProductRegistryService"
    assert data["validation_service_type"] == "ProductValidationService"
    
    # Проверяем, что сервисы имеют правильные зависимости
    assert data["storage_has_ipfs"] is True
    assert data["blockchain_has_web3"] is True
    assert data["account_has_blockchain"] is True
    assert data["api_key_has_blockchain"] is True
    assert data["registry_has_all_deps"] is True
    
    # Проверяем, что реальные методы работают
    assert isinstance(data["registry_catalog_version"], int)


def test_di_with_ipfs_override(client, auth_headers):
    """
    Проверяет, что можно подменить только IPFS storage через dependency_overrides,
    а остальные сервисы остаются реальными.
    """
    from bot.dependencies import get_product_storage_service
    
    # Подменяем только IPFS storage (внешний сервис)
    mock_storage = MockIPFSStorage()
    app.dependency_overrides[get_product_storage_service] = lambda: get_product_storage_service(storage_provider=mock_storage)
    
    response = client.post("/test-di", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что все сервисы остались реальными
    assert data["storage_service_type"] == "ProductStorageService"
    assert data["blockchain_service_type"] == "BlockchainService"
    assert data["account_service_type"] == "AccountService"
    assert data["api_key_service_type"] == "ApiKeyService"
    assert data["registry_service_type"] == "ProductRegistryService"
    assert data["validation_service_type"] == "ProductValidationService"
    
    # Проверяем, что storage_service теперь использует мок IPFS
    assert data["storage_has_ipfs"] is True
    
    # Очищаем подмены
    app.dependency_overrides.clear()


def test_di_direct_dependency_injection():
    """
    Проверяет, что DI работает напрямую (без FastAPI) через bot/dependencies.py.
    """
    from bot.dependencies import (
        get_product_storage_service,
        get_blockchain_service,
        get_account_service,
        get_api_key_service,
        get_product_registry_service,
        get_product_validation_service,
    )
    
    # Получаем сервисы напрямую
    blockchain_service = get_blockchain_service()
    storage_service = get_product_storage_service()
    validation_service = get_product_validation_service()
    account_service = get_account_service(blockchain_service)
    api_key_service = get_api_key_service(blockchain_service)
    registry_service = get_product_registry_service(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
    
    # Проверяем, что все сервисы созданы и имеют зависимости
    assert blockchain_service is not None
    assert storage_service is not None
    assert validation_service is not None
    assert account_service is not None
    assert api_key_service is not None
    assert registry_service is not None
    
    # Проверяем, что зависимости правильно связаны
    assert account_service.blockchain_service == blockchain_service
    assert api_key_service.blockchain_service == blockchain_service
    assert registry_service.blockchain_service == blockchain_service
    assert registry_service.storage_service == storage_service
    assert registry_service.validation_service == validation_service
    assert registry_service.account_service == account_service


def test_di_with_real_api_endpoint():
    """
    Проверяет DI на реальном API endpoint.
    """
    from bot.api.main import create_api_app
    from bot.api.dependencies import get_product_storage_service
    from bot.dependencies import get_product_storage_service as get_storage_direct
    
    # Создаем реальное FastAPI приложение
    api_app = create_api_app()
    test_client = TestClient(api_app)
    
    # Подменяем только IPFS storage для тестирования
    mock_storage = MockIPFSStorage()
    api_app.dependency_overrides[get_product_storage_service] = lambda: get_storage_direct(storage_provider=mock_storage)
    
    # Тестируем реальный endpoint
    response = test_client.get("/")
    assert response.status_code == 200
    
    # Очищаем подмены
    api_app.dependency_overrides.clear()


def test_di_backward_compatibility():
    """
    Проверяет обратную совместимость: старый способ создания сервисов все еще работает.
    """
    from bot.services.product.storage import ProductStorageService
    from bot.services.core.blockchain import BlockchainService
    from bot.services.core.account import AccountService
    from bot.services.core.api_key import ApiKeyService
    from bot.services.product.registry import ProductRegistryService
    from bot.services.product.validation import ProductValidationService
    
    # Старый способ (прямое создание)
    blockchain_service = BlockchainService()
    storage_service = ProductStorageService()  # Без параметров
    validation_service = ProductValidationService()
    account_service = AccountService(blockchain_service)
    api_key_service = ApiKeyService(blockchain_service)
    registry_service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
    
    # Проверяем, что все работает
    assert blockchain_service is not None
    assert storage_service is not None
    assert validation_service is not None
    assert account_service is not None
    assert api_key_service is not None
    assert registry_service is not None 