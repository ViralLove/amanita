"""
Централизованные фикстуры для API тестов
"""
import pytest
import httpx
import asyncio
import logging
import os
from typing import AsyncGenerator
import types
from bot.services.core import blockchain

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


# Удалён старый дублирующийся класс MockBlockchainService

@pytest.fixture
def mock_blockchain_service(monkeypatch):
    """Мок для BlockchainService (только для unit-тестов продуктов)"""
    
    class MockBlockchainService:
        def __init__(self):
            self.create_product_called = False
        
        # Возвращает фиктивную версию каталога (например, 1)
        def get_catalog_version(self):
            return 1

        # Возвращает список из 8 фиктивных продуктов (структура ProductRegistry.Product), вдохновлённые active_catalog.json.
        def get_all_products(self):
            """
            Возвращает список из 8 фиктивных продуктов (структура ProductRegistry.Product), вдохновлённые active_catalog.json.
            """
            return [
                (1, "0x0000000000000000000000000000000000000001", "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG", True),
                (2, "0x0000000000000000000000000000000000000002", "QmbTBHeByJwUP9JyTo2GcHzj1YwzVww6zXrEDFt3zgdwQ1", True),
                (3, "0x0000000000000000000000000000000000000003", "QmUPHsHyuDHKyVbduvqoooAYShFCSfYgcnEioxNNqgZK2B", True),
                (4, "0x0000000000000000000000000000000000000004", "Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz", True),
                (5, "0x0000000000000000000000000000000000000005", "Qmbkp4owyjyjRuYGd7b1KfVjo5bBvCutgYdCi7qKd3ZPoy", True),
                (6, "0x0000000000000000000000000000000000000006", "QmWwjNvD8HX6WB2TLsxiEhciMJCHRfiZBw9G2wgfqKyPbd", True),
                (7, "0x0000000000000000000000000000000000000007", "QmbGrAqeugUxZZxWojavu4rbHdk5XNmSsSv92UV8FKjyHa", True),
                (8, "0x0000000000000000000000000000000000000008", "QmdmJFdMQXRpp3qNRTLYqsR1kFLYhTSRA8YMfd5JvNi85S", True)
            ]

        # Возвращает фиктивный продукт по id. Структура соответствует ProductRegistry.Product.
        def get_product(self, product_id):
            """
            Возвращает фиктивный продукт по id. Структура соответствует ProductRegistry.Product.
            Если id != 1, выбрасывает исключение (имитирует revert).
            """
            if product_id == 1 or product_id == "1":
                return (1, "0x0000000000000000000000000000000000000001", "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG", True)
            raise Exception("ProductRegistry: product does not exist")

        # Имитация создания продукта в блокчейне. Всегда возвращает фиктивный tx_hash '0x123'.
        async def create_product(self, ipfs_cid):
            self.create_product_called = True
            """
            Имитация создания продукта в блокчейне. Всегда возвращает фиктивный tx_hash '0x123'.
            """
            return "0x123"

        # Имитация активации продукта в блокчейне. Всегда возвращает фиктивный tx_hash '0xsetactive'.
        async def set_product_active(self, private_key, product_id, is_active):
            return "0xsetactive"

        # Имитация обновления статуса продукта в блокчейне. Всегда возвращает фиктивный tx_hash '0xupdatestatus'.
        async def update_product_status(self, private_key, product_id, new_status):
            return "0xupdatestatus"

        # Имитация получения productId из транзакции. Всегда возвращает фиктивный productId '42' (строка).
        async def get_product_id_from_tx(self, tx_hash):
            return "42"
    
    # Подменяем BlockchainService на мок
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainService)
    return MockBlockchainService()


@pytest.fixture
def mock_ipfs_service(monkeypatch):
    """Мок для ProductStorageService (IPFS/Pinata) для unit-тестов API продуктов"""
    class MockIPFSService:
        def __init__(self):
            self.should_fail_upload = False
            self.uploaded_json = []
            self.uploaded_files = []
            self.downloaded_json = {}
            self.gateway_url_prefix = "https://mocked.ipfs/"
        async def upload_json(self, data):
            print(f"[MOCK upload_json] should_fail_upload={self.should_fail_upload}")
            if self.should_fail_upload:
                print("[MOCK upload_json] returning None (simulate IPFS error)")
                return None
            self.uploaded_json.append(data)
            cid = "QmMockedCID" + str(len(self.uploaded_json))
            print(f"[MOCK upload_json] returning {cid}")
            return cid
        def upload_file(self, file_path_or_data, file_name=None):
            self.uploaded_files.append((file_path_or_data, file_name))
            return "QmMockedFileCID"
        def download_json(self, cid):
            return self.downloaded_json.get(cid, {"mocked": True, "cid": cid})
        def get_gateway_url(self, cid):
            return self.gateway_url_prefix + cid
        def is_valid_cid(self, cid):
            return isinstance(cid, str) and cid.startswith("Qm")
    # Подменяем ProductStorageService на мок
    from bot.services.product import storage
    monkeypatch.setattr(storage, "ProductStorageService", MockIPFSService)
    return MockIPFSService() 


@pytest.fixture
def mock_blockchain_service_with_error(monkeypatch):
    """Мок для BlockchainService с симуляцией ошибки создания продукта"""
    class MockBlockchainServiceWithError:
        def __init__(self):
            self.create_product_called = False
            self.should_fail_create = True  # Включаем ошибку
        
        def get_catalog_version(self):
            return 1
        
        def get_all_products(self):
            return []
        
        def get_product(self, product_id):
            raise Exception("ProductRegistry: product does not exist")
        
        async def create_product(self, ipfs_cid):
            self.create_product_called = True
            if self.should_fail_create:
                raise Exception("Blockchain transaction failed: insufficient gas")
            return "0x123"
        
        async def set_product_active(self, private_key, product_id, is_active):
            return "0xsetactive"
        
        async def update_product_status(self, private_key, product_id, new_status):
            return "0xupdatestatus"
        
        async def get_product_id_from_tx(self, tx_hash):
            return "42"
    
    # Подменяем BlockchainService на мок
    from bot.services.core import blockchain
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainServiceWithError)
    return MockBlockchainServiceWithError()


@pytest.fixture
def mock_blockchain_service_with_id_error(monkeypatch):
    """Мок для BlockchainService с симуляцией ошибки получения blockchain_id"""
    class MockBlockchainServiceWithIdError:
        def __init__(self):
            self.create_product_called = False
            self.get_product_id_called = False
            self.should_fail_get_id = True  # Включаем ошибку получения ID
        
        def get_catalog_version(self):
            return 1
        
        def get_all_products(self):
            return []
        
        def get_product(self, product_id):
            raise Exception("ProductRegistry: product does not exist")
        
        async def create_product(self, ipfs_cid):
            self.create_product_called = True
            return "0x123"  # Успешная транзакция
        
        async def set_product_active(self, private_key, product_id, is_active):
            return "0xsetactive"
        
        async def update_product_status(self, private_key, product_id, new_status):
            return "0xupdatestatus"
        
        async def get_product_id_from_tx(self, tx_hash):
            self.get_product_id_called = True
            if self.should_fail_get_id:
                raise Exception("Failed to get product ID from transaction: transaction not found")
            return "42"
    
    # Подменяем BlockchainService на мок
    from bot.services.core import blockchain
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainServiceWithIdError)
    return MockBlockchainServiceWithIdError()


@pytest.fixture
def mock_blockchain_service_with_tracking(monkeypatch):
    """Мок для BlockchainService с отслеживанием вызовов для тестирования идемпотентности"""
    class MockBlockchainServiceWithTracking:
        def __init__(self):
            self.create_product_calls = []
            self.get_product_id_calls = []
        
        def get_catalog_version(self):
            return 1
        
        def get_all_products(self):
            return []
        
        def get_product(self, product_id):
            raise Exception("ProductRegistry: product does not exist")
        
        async def create_product(self, ipfs_cid):
            self.create_product_calls.append(ipfs_cid)
            return "0x123"
        
        async def set_product_active(self, private_key, product_id, is_active):
            return "0xsetactive"
        
        async def update_product_status(self, private_key, product_id, new_status):
            return "0xupdatestatus"
        
        async def get_product_id_from_tx(self, tx_hash):
            self.get_product_id_calls.append(tx_hash)
            return "42"
    
    # Подменяем BlockchainService на мок
    from bot.services.core import blockchain
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainServiceWithTracking)
    return MockBlockchainServiceWithTracking() 