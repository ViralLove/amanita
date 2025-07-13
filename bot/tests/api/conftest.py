"""
Централизованные фикстуры для API тестов
"""
import pytest
import httpx
import asyncio
import logging
import os
from typing import AsyncGenerator

# Настройка логирования для тестов
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Тестовые ключи
AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "test-api-key-12345")
AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "default-secret-key-change-in-production")
API_URL = os.getenv("AMANITA_API_URL", "http://localhost:8000")


@pytest.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Фикстура для HTTP клиента"""
    async with httpx.AsyncClient(base_url=API_URL) as client:
        yield client


@pytest.fixture
def test_api_key() -> str:
    """Фикстура для тестового API ключа"""
    return AMANITA_API_KEY


@pytest.fixture
def test_secret_key() -> str:
    """Фикстура для тестового секретного ключа"""
    return AMANITA_API_SECRET


@pytest.fixture
def valid_ethereum_address() -> str:
    """Фикстура для валидного Ethereum адреса"""
    return "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"


@pytest.fixture
def invalid_ethereum_address() -> str:
    """Фикстура для невалидного Ethereum адреса"""
    return "invalid-address"


@pytest.fixture
def valid_api_key() -> str:
    """Фикстура для валидного API ключа"""
    return "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"


@pytest.fixture
def invalid_api_key() -> str:
    """Фикстура для невалидного API ключа"""
    return "invalid-key"


@pytest.fixture
def test_request_data() -> dict:
    """Фикстура для тестовых данных запроса"""
    return {
        "client_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
        "description": "Test API key"
    }


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Настройка логирования для тестов"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@pytest.fixture
def mock_service_factory():
    """Фикстура для мока ServiceFactory"""
    class MockServiceFactory:
        def create_api_key_service(self):
            return MockApiKeyService()
        
        def create_blockchain_service(self):
            return MockBlockchainService()
    
    return MockServiceFactory()


class MockApiKeyService:
    """Мок для ApiKeyService"""
    
    async def create_api_key(self, client_address: str, description: str = None):
        return {
            "api_key": "test-api-key-12345",
            "secret_key": "test-secret-key-12345",
            "client_address": client_address,
            "description": description,
            "active": True
        }
    
    async def validate_api_key(self, api_key: str):
        if api_key == "test-api-key-12345":
            return {
                "active": True,
                "client_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
                "secret_key": "test-secret-key-12345"
            }
        raise ValueError("Invalid API key")


class MockBlockchainService:
    """Мок для BlockchainService"""
    
    async def get_balance(self, address: str):
        return {"balance": "1000000000000000000"}
    
    async def is_valid_address(self, address: str):
        return address.startswith("0x") and len(address) == 42 