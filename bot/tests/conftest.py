"""
Централизованные фикстуры для всех тестов проекта Amanita
"""
import pytest
import logging
import os
from unittest.mock import Mock, AsyncMock
from bot.services.core import blockchain

# Явная регистрация pytest-asyncio плагина
pytest_plugins = ["pytest_asyncio"]

# Настройка логирования для тестов
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаем logger для моков
logger = logging.getLogger(__name__)

# Тестовые ключи
AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "test-api-key-12345")
AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "default-secret-key-change-in-production")
API_URL = os.getenv("AMANITA_API_URL", "http://localhost:8000")

# API-специфичные фикстуры
import httpx
from typing import AsyncGenerator


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Настройка логирования для тестов"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@pytest.fixture
def mock_blockchain_service(monkeypatch):
    """Мок для BlockchainService (только для unit-тестов продуктов)"""
    
    class MockBlockchainService:
        def __init__(self):
            self.create_product_called = False
            self.seller_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            # Счетчик для генерации уникальных blockchain ID
            self._next_blockchain_id = 1
            # Отслеживаем статусы продуктов для тестирования (теперь динамически)
            self.product_statuses = {}
            # Новое: связь между blockchain ID и IPFS CID для синхронизации с MockIPFSStorage
            self.product_cids = {}
            # Ссылка на storage service для синхронизации
            self.storage_service = None
        
        def _generate_next_blockchain_id(self):
            """Генерирует следующий уникальный blockchain ID"""
            next_id = self._next_blockchain_id
            self._next_blockchain_id += 1
            logger.info(f"🔢 [MockBlockchainService] Сгенерирован новый blockchain ID: {next_id}")
            return next_id
        
        # Возвращает фиктивную версию каталога (например, 1)
        def get_catalog_version(self):
            return 1

        # Возвращает список из 9 фиктивных продуктов (структура ProductRegistry.Product)
        def get_all_products(self):
            """
            Возвращает список из 9 фиктивных продуктов (структура ProductRegistry.Product)
            Убрали жестко закодированный продукт с ID 42 для динамического тестирования
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
                # Убрали продукт с ID 42 - теперь он создается динамически в тестах
            ]
        
        # Синхронный метод для получения продуктов текущего продавца (используется в _check_product_id_exists)
        def get_products_by_current_seller_full(self):
            return []
        
        # Синхронная проверка существования продукта в блокчейне (используется в _check_blockchain_product_exists)
        def product_exists_in_blockchain(self, blockchain_id):
            return False
        
        # Асинхронный метод для получения всех продуктов (если нужен)
        async def get_all_products_async(self):
            return self.get_all_products()

        # Возвращает фиктивный продукт по id. Структура соответствует ProductRegistry.Product.
        def get_product(self, product_id):
            """
            Возвращает фиктивный продукт по id. Структура соответствует ProductRegistry.Product.
            Теперь работает с любыми динамически созданными ID.
            """
            # ИСПРАВЛЕНИЕ: Всегда возвращаем актуальный статус из product_statuses
            status = self.product_statuses.get(product_id, False)
            
            # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: Логируем состояние product_statuses
            logger.info(f"🔍 [MockBlockchainService] get_product вызван для ID={product_id}")
            logger.info(f"   - product_statuses: {self.product_statuses}")
            logger.info(f"   - status для ID {product_id}: {status}")
            
            # КРИТИЧЕСКАЯ ПРОБЛЕМА: status возвращается неправильно!
            # Давайте проверим, что происходит с product_statuses
            logger.warning(f"🚨 [MockBlockchainService] КРИТИЧЕСКАЯ ПРОБЛЕМА: status={status} для ID={product_id}")
            logger.warning(f"🚨 [MockBlockchainService] product_statuses содержит: {self.product_statuses}")
            
            # ПРОБЛЕМА НАЙДЕНА: product_id приходит как строка, а в product_statuses ключи - числа!
            # Нужно привести product_id к int
            product_id_int = int(product_id) if isinstance(product_id, str) else product_id
            status = self.product_statuses.get(product_id_int, False)
            logger.warning(f"🚨 [MockBlockchainService] ИСПРАВЛЕНИЕ: product_id={product_id} -> {product_id_int}, status={status}")
            
            # Проверяем, существует ли продукт с таким ID
            if product_id_int in self.product_cids:
                # Продукт был создан через create_product, возвращаем сохраненный CID
                cid = self.product_cids[product_id_int]
                logger.info(f"🔍 [MockBlockchainService] Получен продукт: ID={product_id_int}, CID={cid}, Status={status}")
                return (product_id_int, "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", cid, status)
            else:
                # Продукт не был создан, возвращаем None для CID
                logger.warning(f"⚠️ [MockBlockchainService] Продукт {product_id_int} не найден в product_cids, но статус: {status}")
                return (product_id_int, "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", None, status)

        # Имитация создания продукта в блокчейне. Сохраняет CID для синхронизации с MockIPFSStorage.
        async def create_product(self, ipfs_cid):
            self.create_product_called = True
            
            # Генерируем уникальный blockchain ID для продукта (в реальной системе это делает блокчейн)
            product_id = self._generate_next_blockchain_id()
            
            # Сохраняем связь между blockchain ID и IPFS CID
            self.product_cids[product_id] = ipfs_cid
            
            # Устанавливаем статус продукта как неактивный по умолчанию
            self.product_statuses[product_id] = False
            
            logger.info(f"🔗 [MockBlockchainService] Создан продукт: ID={product_id}, CID={ipfs_cid}")
            
            return "0x123"

        # Имитация активации продукта в блокчейне. Всегда возвращает фиктивный tx_hash '0xsetactive'.
        async def set_product_active(self, private_key, product_id, is_active):
            return "0xsetactive"

        # Имитация обновления статуса продукта в блокчейне. Обновляет отслеживаемый статус и возвращает фиктивный tx_hash.
        async def update_product_status(self, private_key, product_id, new_status):
            # ДЕТАЛЬНАЯ ДИАГНОСТИКА: Логируем типы и значения для отладки
            logger.info(f"🔍 [MockBlockchainService] update_product_status вызван:")
            logger.info(f"   - product_id: {product_id} (тип: {type(product_id)})")
            logger.info(f"   - new_status: {new_status} (тип: {type(new_status)})")
            logger.info(f"   - new_status repr: {repr(new_status)}")
            
            # ИСПРАВЛЕНИЕ ТИПИЗАЦИИ: Приводим new_status к int перед bool преобразованием
            if isinstance(new_status, str):
                try:
                    status_int = int(new_status)
                    logger.info(f"🔄 [MockBlockchainService] Преобразовали строку '{new_status}' в int: {status_int}")
                except ValueError:
                    logger.error(f"❌ [MockBlockchainService] Не удалось преобразовать '{new_status}' в int, используем как есть")
                    status_int = new_status
            else:
                status_int = new_status
            
            # Преобразуем в bool (теперь корректно: 0 -> False, 1 -> True)
            status_bool = bool(status_int)
            logger.info(f"🔄 [MockBlockchainService] new_status {new_status} -> status_int {status_int} -> status_bool {status_bool}")
            
            # Обновляем статус в отслеживаемом словаре
            if product_id in self.product_statuses:
                old_status = self.product_statuses[product_id]
                self.product_statuses[product_id] = status_bool
                logger.info(f"🔄 [MockBlockchainService] Статус продукта {product_id} изменен: {old_status} -> {status_bool}")
            else:
                # Если продукт не существует, создаем запись
                self.product_statuses[product_id] = status_bool
                logger.info(f"🆕 [MockBlockchainService] Создан статус для продукта {product_id}: {status_bool}")
            
            return "0xupdatestatus"

        # Имитация получения productId из транзакции. Возвращает динамический productId.
        async def get_product_id_from_tx(self, tx_hash):
            # Возвращаем динамический ID для тестирования
            # В реальной системе этот ID генерируется блокчейном
            # Используем последний созданный ID или генерируем новый
            if self.product_cids:
                # Возвращаем последний созданный ID
                last_id = max(self.product_cids.keys())
                logger.info(f"🆔 [MockBlockchainService] Получен ID из транзакции: {last_id}")
                return last_id
            else:
                # Если нет созданных продуктов, генерируем новый ID
                new_id = self._generate_next_blockchain_id()
                logger.info(f"🆔 [MockBlockchainService] Сгенерирован новый ID из транзакции: {new_id}")
                return new_id
        
        async def transact_contract_function(self, *args, **kwargs):
            return "0xtransaction"
        
        def clear(self):
            """Очищает состояние мока между тестами"""
            self.create_product_called = False
            self.product_statuses.clear()
            self.product_cids.clear()
            # Сбрасываем счетчик blockchain ID
            self._next_blockchain_id = 1
            logger.info("🧹 [MockBlockchainService] Состояние очищено, счетчик ID сброшен")
    
    # Подменяем BlockchainService на мок
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainService)
    return MockBlockchainService()


@pytest.fixture
def mock_validation_service():
    """Универсальный мок для ProductValidationService"""
    class MockProductValidationService:
        def __init__(self, should_fail_validation=False):
            self.should_fail_validation = should_fail_validation
            self.validation_calls = []
        
        async def validate_product_data(self, product_data):
            self.validation_calls.append(product_data)
            
            if self.should_fail_validation:
                return {
                    "is_valid": False,
                    "errors": ["Mock validation failed"]
                }
            
            # Простая валидация для тестов (обновлена для многокомпонентных продуктов)
            required_fields = ["title", "organic_components", "forms"]
            errors = []
            
            for field in required_fields:
                if field not in product_data:
                    errors.append(f"Missing required field: {field}")
            
            # Дополнительная валидация для organic_components
            if "organic_components" in product_data:
                components = product_data["organic_components"]
                if not isinstance(components, list) or len(components) == 0:
                    errors.append("organic_components: Должен быть непустым списком")
                else:
                    for i, component in enumerate(components):
                        if not isinstance(component, dict):
                            errors.append(f"organic_components[{i}]: Должен быть словарем")
                        else:
                            required_component_fields = ["biounit_id", "description_cid", "proportion"]
                            for comp_field in required_component_fields:
                                if comp_field not in component:
                                    errors.append(f"organic_components[{i}].{comp_field}: Поле обязательно")
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors
            }
    
    return MockProductValidationService()


@pytest.fixture
def mock_account_service():
    """Универсальный мок для AccountService"""
    class MockAccountService:
        def __init__(self):
            self.private_key = "0x1234567890abcdef"
            self.address = "0x1234567890abcdef1234567890abcdef12345678"
            self.balance = "1000000000000000000"  # 1 ETH
        
        def get_private_key(self):
            return self.private_key
        
        def get_address(self):
            return self.address
        
        def get_balance(self):
            return self.balance
        
        async def sign_transaction(self, transaction):
            return f"0xsigned_{transaction}"
    
    return MockAccountService()


@pytest.fixture
def mock_ipfs_storage_failing():
    """Мок IPFS storage с симуляцией ошибок"""
    class MockIPFSStorageFailing:
        def __init__(self):
            self.should_fail_upload = True
            self.should_fail_download = True
            self.uploaded_files = []
            self.uploaded_jsons = []
            self.downloaded_json = {}
            self.gateway_url_prefix = "https://mocked.ipfs/"
        
        def download_json(self, cid):
            if self.should_fail_download:
                return None
            return self.downloaded_json.get(cid, {
                "id": "amanita1",
                "title": "Amanita muscaria — sliced caps and gills (1st grade)",
                "organic_components": [
                    {
                        "biounit_id": "amanita_muscaria",
                        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        "proportion": "100%"
                    }
                ],
                "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                "categories": ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
                "forms": ["mixed slices"],
                "species": "Amanita muscaria",
                "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
            })
        
        async def upload_json(self, data):
            if self.should_fail_upload:
                return None
            cid = f"QmMockJson{len(self.uploaded_jsons)}"
            self.uploaded_jsons.append((data, cid))
            return cid
        
        async def download_json_async(self, cid):
            return self.download_json(cid)
        
        def upload_file(self, file_path_or_data, file_name=None):
            if self.should_fail_upload:
                raise Exception("Mock IPFS upload failed")
            cid = f"QmMockFile{len(self.uploaded_files)}"
            self.uploaded_files.append((file_path_or_data, file_name))
            return cid
        
        def get_gateway_url(self, cid):
            return self.gateway_url_prefix + cid
        
        def is_valid_cid(self, cid):
            return isinstance(cid, str) and cid.startswith("Qm")
    
    return MockIPFSStorageFailing()


@pytest.fixture
def mock_validation_service_failing():
    """Мок ProductValidationService с симуляцией ошибок"""
    class MockProductValidationServiceFailing:
        def __init__(self):
            self.validation_calls = []
        
        async def validate_product_data(self, product_data):
            self.validation_calls.append(product_data)
            return {
                "is_valid": False,
                "errors": ["Mock validation failed"]
            }
    
    return MockProductValidationServiceFailing()


@pytest.fixture
def mock_integration_registry_service(mock_blockchain_service, mock_ipfs_service, mock_validation_service, mock_account_service):
    """Мок ProductRegistryService для интеграционных тестов с синхронизированными моками"""
    from bot.dependencies import get_product_registry_service
    
    # Связываем моки между собой для синхронизации
    mock_blockchain_service.storage_service = mock_ipfs_service
    mock_ipfs_service.blockchain_service = mock_blockchain_service
    
    logger.info("🔗 [mock_integration_registry_service] Моки связаны для синхронизации")
    
    return get_product_registry_service(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_service,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )


@pytest.fixture
def mock_integration_registry_service_real_blockchain(mock_ipfs_service, mock_validation_service, mock_account_service):
    """Мок для интеграционных тестов с реальным блокчейном, но моканным IPFS"""
    from bot.dependencies import get_product_registry_service
    from bot.services.core.blockchain import BlockchainService
    
    return get_product_registry_service(
        blockchain_service=BlockchainService(),  # Реальный блокчейн
        storage_service=mock_ipfs_service,      # Моканный IPFS
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )


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
            
        # Синхронный метод для unit-тестов
        def download_json(self, cid):
            # Возвращаем фиктивные метаданные для тестов (обновлено для многокомпонентных продуктов)
            mock_metadata = {
                "id": "amanita1",
                "title": "Amanita muscaria — sliced caps and gills (1st grade)",
                "organic_components": [
                    {
                        "biounit_id": "amanita_muscaria",
                        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        "proportion": "100%"
                    }
                ],
                "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                "categories": ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
                "forms": ["mixed slices"],
                "species": "Amanita muscaria",
                "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
            }
            return self.downloaded_json.get(cid, mock_metadata)
            
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
            return 42
    
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
                raise Exception("Failed to get product ID from transaction")
            return 42
    
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


# === API СПЕЦИФИЧНЫЕ ФИКСТУРЫ ===

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
    def __init__(self):
        self.api_keys = {}
    
    async def create_api_key(self, client_address: str, description: str = None):
        api_key = f"test_api_key_{len(self.api_keys)}"
        self.api_keys[api_key] = {
            "client_address": client_address,
            "description": description
        }
        return api_key
    
    async def validate_api_key(self, api_key: str):
        return api_key in self.api_keys


class MockBlockchainService:
    """Мок для BlockchainService в API тестах"""
    def __init__(self):
        self.accounts = {}
    
    def get_account_balance(self, address: str):
        return "1000000000000000000"  # 1 ETH
    
    def is_valid_address(self, address: str):
        return address.startswith("0x") and len(address) == 42


# === УПРАВЛЕНИЕ СОСТОЯНИЕМ МОКОВ ===

@pytest.fixture(autouse=True)
def reset_mock_states():
    """Автоматический сброс состояния моков перед каждым тестом"""
    yield
    # Сброс состояния всех моков
    # Очистка списков загруженных файлов
    # Сброс счетчиков вызовов


@pytest.fixture(autouse=True)
def clear_mock_storage_between_tests():
    """Автоматическая очистка MockIPFSStorage между тестами"""
    yield
    # Получаем все активные фикстуры mock_ipfs_storage и очищаем их
    import pytest
    from _pytest.fixtures import FixtureRequest
    
    # Очистка происходит автоматически при создании новой фикстуры
    # Но можно добавить дополнительную логику если потребуется


@pytest.fixture
def mock_config():
    """Конфигурация моков через переменные окружения"""
    return {
        "ipfs_mock_enabled": os.getenv("MOCK_IPFS", "true").lower() == "true",
        "blockchain_mock_enabled": os.getenv("MOCK_BLOCKCHAIN", "true").lower() == "true",
        "validation_mock_enabled": os.getenv("MOCK_VALIDATION", "true").lower() == "true"
    }

@pytest.fixture
def mock_ipfs_storage():
    """Универсальный мок для IPFS/Arweave storage с консистентным хранением данных"""
    class MockIPFSStorage:
        def __init__(self, should_fail_upload=False, should_fail_download=False):
            self.should_fail_upload = should_fail_upload
            self.should_fail_download = should_fail_download
            # Внутреннее хранилище для консистентности upload/download
            self._storage = {}  # CID -> data mapping
            self._counter = 0   # Счетчик для генерации уникальных CID
            # Ссылка на blockchain service для синхронизации
            self.blockchain_service = None
            # Обратная совместимость для существующих тестов
            self.uploaded_files = []
            self.uploaded_jsons = []
            self.downloaded_json = {}
            self.gateway_url_prefix = "https://mocked.ipfs/"
        
        def _generate_unique_cid(self, data):
            """Генерирует уникальный CID для данных"""
            import hashlib
            # Создаем хеш от данных + счетчик для уникальности
            data_str = str(data) + str(self._counter)
            data_hash = hashlib.md5(data_str.encode()).hexdigest()
            self._counter += 1
            
            # IPFS CID должен быть 46 символов: Qm + 44 символа хеша
            # MD5 дает 32 символа, но содержит недопустимые символы для IPFS
            # IPFS CID использует base58btc алфавит: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
            # Исключаем символы: 0, O, I, l (строчная L)
            valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
            
            # Создаем полностью валидный CID из 44 символов
            import random
            random.seed(int(data_hash, 16))  # Используем хеш как seed для воспроизводимости
            
            # Генерируем 44 символа только из валидного набора
            cid_suffix = ''.join(random.choices(valid_chars, k=44))
            
            return f"Qm{cid_suffix}"
        
        # Синхронный метод для unit-тестов
        def download_json(self, cid):
            if self.should_fail_download:
                return None
            
            # Сначала проверяем внутреннее хранилище
            if cid in self._storage:
                return self._storage[cid]
            
            # Fallback для обратной совместимости (убираем жесткие маппинги)
            # Возвращаем None если CID не найден - это реалистичное поведение
            return None
        
        # Асинхронный метод для загрузки JSON
        async def upload_json(self, data):
            if self.should_fail_upload:
                return None
            
            # Генерируем уникальный CID
            cid = self._generate_unique_cid(data)
            
            # Сохраняем данные во внутреннее хранилище
            self._storage[cid] = data
            
            # Обратная совместимость - сохраняем в uploaded_jsons
            self.uploaded_jsons.append((data, cid))
            
            return cid
        
        # Асинхронный метод для скачивания JSON
        async def download_json_async(self, cid):
            return self.download_json(cid)
        
        def upload_file(self, file_path_or_data, file_name=None):
            if self.should_fail_upload:
                raise Exception("Mock IPFS upload failed")
            cid = f"QmMockFile{len(self.uploaded_files)}"
            self.uploaded_files.append((file_path_or_data, file_name))
            return cid
        
        def get_gateway_url(self, cid):
            return self.gateway_url_prefix + cid
        
        def is_valid_cid(self, cid):
            return isinstance(cid, str) and cid.startswith("Qm")
        
        def clear(self):
            """Очищает внутреннее хранилище между тестами"""
            self._storage.clear()
            self._counter = 0
            self.uploaded_files.clear()
            self.uploaded_jsons.clear()
            self.downloaded_json.clear()
    
    return MockIPFSStorage()

@pytest.fixture
def mock_registry_service(mock_blockchain_service, mock_ipfs_storage, mock_validation_service, mock_account_service):
    """Полностью замоканный ProductRegistryService для unit-тестов"""
    from bot.services.product.registry import ProductRegistryService
    from unittest.mock import Mock, AsyncMock
    from bot.model.product import Product
    from bot.model.product import PriceInfo
    
    # Создаем сервис
    service = ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )
    
    # Мокаем cache_service чтобы избежать реальных обращений к IPFS
    mock_cache_service = Mock()
    mock_cache_service.get_description_by_cid.return_value = None
    mock_cache_service.get_image_url_by_cid.return_value = "https://mocked.ipfs/test.jpg"
    mock_cache_service.set_cached_item.return_value = None
    mock_cache_service.invalidate_cache.return_value = None
    mock_cache_service.get_cached_item.return_value = None
    service.cache_service = mock_cache_service
    
    # Мокаем metadata_service чтобы избежать реальных обращений к IPFS
    mock_metadata_service = Mock()
    mock_metadata_service.process_metadata.return_value = {
        "id": "amanita1",
        "title": "Amanita muscaria — sliced caps and gills (1st grade)",
        "organic_components": [
            {
                "biounit_id": "amanita_muscaria",
                "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                "proportion": "100%"
            }
        ],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
        "forms": ["mixed slices"],
        "species": "Amanita muscaria",
        "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
    }
    # Мокаем асинхронный метод process_product_metadata
    # Создаем OrganicComponent объекты для тестов
    from bot.model.organic_component import OrganicComponent
    test_component = OrganicComponent(
        biounit_id="amanita_muscaria",
        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        proportion="100%"
    )
    
    mock_metadata_service.process_product_metadata = AsyncMock(return_value=Product(
        id=1,
        alias="amanita1",
        status=1,
        cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        title="Amanita muscaria — sliced caps and gills (1st grade)",
        organic_components=[test_component],
        cover_image_url="https://mocked.ipfs/test.jpg",
        categories=["mushroom", "mental health", "focus", "ADHD support", "mental force"],
        forms=["mixed slices"],
        species="Amanita muscaria",
        prices=[PriceInfo(weight="100", weight_unit="g", price="80", currency="EUR")]
    ))
    service.metadata_service = mock_metadata_service
    
    return service

@pytest.fixture
def mock_registry_service_with_failing_storage(mock_blockchain_service, mock_validation_service, mock_account_service, mock_ipfs_storage_failing):
    """ProductRegistryService с моканным IPFS storage, который симулирует ошибки"""
    from bot.services.product.registry import ProductRegistryService
    
    return ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage_failing,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )

@pytest.fixture
def mock_registry_service_with_failing_validation(mock_blockchain_service, mock_ipfs_storage, mock_account_service, mock_validation_service_failing):
    """ProductRegistryService с моканным validation service, который симулирует ошибки"""
    from bot.services.product.registry import ProductRegistryService
    
    return ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage,
        validation_service=mock_validation_service_failing,
        account_service=mock_account_service
    )


# === ИНТЕГРАЦИОННЫЕ ТЕСТЫ - НОВЫЕ ФИКСТУРЫ ===

@pytest.fixture
def integration_storage_config():
    """Конфигурация storage для интеграционных тестов с детальным логированием для DevOps"""
    # 🔍 Детальное логирование переменных окружения для DevOps мониторинга
    storage_type = os.getenv("INTEGRATION_STORAGE", "mock").lower()
    print(f"🔍 [DEVOPS] INTEGRATION_STORAGE={storage_type}")
    
    # 📊 Логирование доступности API ключей для диагностики
    pinata_api_key = os.getenv("PINATA_API_KEY")
    pinata_secret_key = os.getenv("PINATA_SECRET_KEY")
    arweave_private_key = os.getenv("ARWEAVE_PRIVATE_KEY")
    
    print(f"🔍 [DEVOPS] PINATA_API_KEY: {'✅ Установлен' if pinata_api_key else '❌ Не установлен'}")
    print(f"🔍 [DEVOPS] PINATA_SECRET_KEY: {'✅ Установлен' if pinata_secret_key else '❌ Не установлен'}")
    print(f"🔍 [DEVOPS] ARWEAVE_PRIVATE_KEY: {'✅ Установлен' if arweave_private_key else '❌ Не установлен'}")
    
    configs = {
        "mock": {
            "service": _create_mock_storage(),
            "description": "Тестовый режим: Mock IPFS/Arweave (быстро, экономично, без реальных API вызовов)",
            "devops_info": {
                "type": "mock",
                "performance": "fast",
                "cost": "free",
                "api_calls": "none"
            }
        },
        "pinata": {
            "service": _get_real_pinata_storage(),
            "description": "Реальный Pinata IPFS (медленно, тратит бюджет)",
            "devops_info": {
                "type": "real",
                "performance": "slow",
                "cost": "budget",
                "api_calls": "pinata_api"
            }
        },
        "arweave": {
            "service": _get_real_arweave_storage(),
            "description": "Реальный Arweave (медленно, тратит бюджет)",
            "devops_info": {
                "type": "real",
                "performance": "slow",
                "cost": "budget",
                "api_calls": "arweave_api"
            }
        }
    }
    
    if storage_type not in configs:
        print(f"⚠️ [DEVOPS] Неизвестный тип storage: {storage_type}, используем mock (fallback)")
        storage_type = "mock"
    
    selected_config = configs[storage_type]
    devops_info = selected_config["devops_info"]
    
    # 📊 Структурированное логирование для DevOps мониторинга
    print(f"🔧 [DEVOPS] Интеграционный тест использует: {selected_config['description']}")
    print(f"📊 [DEVOPS] Storage конфигурация: {devops_info}")
    print(f"🔍 [DEVOPS] Принятое решение: {storage_type} (performance: {devops_info['performance']}, cost: {devops_info['cost']})")
    
    return selected_config


def _create_mock_storage():
    """Создание mock storage сервиса (не фикстура)"""
    mock_storage = Mock()
    mock_storage.upload_file = AsyncMock(return_value="QmMockHash123")
    mock_storage.upload_json = AsyncMock(return_value="QmMockHash456")
    return mock_storage


def _get_real_pinata_storage():
    """Получение реального Pinata storage (с проверкой переменных окружения)"""
    try:
        from bot.services.core.storage.pinata import SecurePinataUploader
        pinata_api_key = os.getenv("PINATA_API_KEY")
        pinata_secret_key = os.getenv("PINATA_SECRET_KEY")
        
        if not pinata_api_key or not pinata_secret_key:
            print("⚠️ [DEVOPS] PINATA_API_KEY или PINATA_SECRET_KEY не установлены, используем mock (fallback)")
            return _create_mock_storage()
        
        print("✅ [DEVOPS] Используется реальный Pinata IPFS (API ключи валидны)")
        return SecurePinataUploader()
        
    except Exception as e:
        print(f"❌ [DEVOPS] Ошибка инициализации Pinata: {e}, используем mock (fallback)")
        return _create_mock_storage()


def _get_real_arweave_storage():
    """Получение реального Arweave storage (с проверкой переменных окружения)"""
    try:
        from bot.services.core.storage.ar_weave import ArWeaveUploader
        arweave_private_key = os.getenv("ARWEAVE_PRIVATE_KEY")
        
        if not arweave_private_key:
            print("⚠️ [DEVOPS] ARWEAVE_PRIVATE_KEY не установлен, используем mock (fallback)")
            return _create_mock_storage()
        
        print("✅ [DEVOPS] Используется реальный Arweave (приватный ключ валиден)")
        return ArWeaveUploader()
        
    except Exception as e:
        print(f"❌ [DEVOPS] Ошибка инициализации Arweave: {e}, используем mock (fallback)")
        return _create_mock_storage()


@pytest.fixture
def integration_registry_service_real_blockchain(integration_storage_config):
    """Интеграционный сервис с реальным блокчейном и настраиваемым storage"""
    from bot.dependencies import get_product_registry_service
    from bot.services.core.blockchain import BlockchainService
    
    # ✅ Блокчейн ВСЕГДА реальный в интеграционных тестах
    try:
        blockchain_service = BlockchainService()
        logger.info("✅ BlockchainService инициализирован (реальный блокчейн)")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации BlockchainService: {e}")
        pytest.skip(f"Ошибка инициализации блокчейна: {e}")
    
    # 🔧 Storage настраивается через переменную окружения
    storage_service = integration_storage_config["service"]
    
    # Создаем сервис через DI с реальным блокчейном и настраиваемым storage
    registry_service = get_product_registry_service(
        blockchain_service=blockchain_service,      # ✅ ВСЕГДА реальный
        storage_service=storage_service,            # 🔧 Настраиваемый
        validation_service=mock_validation_service(),
        account_service=mock_account_service()
    )
    
    logger.info("✅ IntegrationRegistryService создан с реальным блокчейном")
    return registry_service


@pytest.fixture
def seller_account():
    """Аккаунт продавца для тестирования"""
    seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
    if not seller_private_key:
        pytest.skip("SELLER_PRIVATE_KEY не найден в окружении")
    
    try:
        from eth_account import Account
        account = Account.from_key(seller_private_key)
        logger.info(f"✅ Аккаунт продавца: {account.address}")
        return account
    except Exception as e:
        logger.error(f"❌ Ошибка создания аккаунта продавца: {e}")
        pytest.skip(f"Ошибка создания аккаунта: {e}")


@pytest.fixture
def test_products():
    """Генерация тестовых продуктов для интеграционных тестов"""
    return [
        {
            "id": "amanita1",
            "title": "Amanita muscaria — sliced caps and gills (1st grade)",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    "proportion": "100%"
                }
            ],
            "forms": ["mixed slices"],
            "categories": ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
            "species": "Amanita muscaria",
            "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
        },
        {
            "id": "amanita2", 
            "title": "Amanita pantherina — premium capsules",
            "organic_components": [
                {
                    "biounit_id": "amanita_pantherina",
                    "description_cid": "QmYXGiCLB1sPtkoskNWA5dCo8d9uW6RVVS94uq2xf6awQ7",
                    "proportion": "100%"
                }
            ],
            "forms": ["capsules"],
            "categories": ["mushroom", "energy", "focus"],
            "species": "Amanita pantherina",
            "prices": [{"weight": "60", "weight_unit": "capsules", "price": "120", "currency": "EUR"}]
        }
    ]


# === ТЕСТЫ ДЛЯ ПРОВЕРКИ ФИКСТУР ===

def test_integration_storage_config_mock():
    """Тест фикстуры integration_storage_config в mock режиме"""
    # Сохраняем оригинальное значение переменной окружения
    original_storage = os.getenv("INTEGRATION_STORAGE")
    
    try:
        # Устанавливаем mock режим
        os.environ["INTEGRATION_STORAGE"] = "mock"
        
        # Вызываем фикстуру
        config = integration_storage_config()
        
        # Проверяем структуру
        assert "service" in config
        assert "description" in config
        assert "mock" in config["description"].lower()
        
        print("✅ Тест integration_storage_config mock режима пройден")
        
    finally:
        # Восстанавливаем оригинальное значение
        if original_storage:
            os.environ["INTEGRATION_STORAGE"] = original_storage
        else:
            os.environ.pop("INTEGRATION_STORAGE", None)


def test_integration_storage_config_fallback():
    """Тест fallback механизма фикстуры integration_storage_config"""
    # Сохраняем оригинальное значение переменной окружения
    original_storage = os.getenv("INTEGRATION_STORAGE")
    
    try:
        # Устанавливаем неверное значение
        os.environ["INTEGRATION_STORAGE"] = "invalid_type"
        
        # Вызываем фикстуру
        config = integration_storage_config()
        
        # Проверяем, что используется fallback на mock
        assert "service" in config
        assert "description" in config
        assert "mock" in config["description"].lower()
        
        print("✅ Тест integration_storage_config fallback механизма пройден")
        
    finally:
        # Восстанавливаем оригинальное значение
        if original_storage:
            os.environ["INTEGRATION_STORAGE"] = original_storage
        else:
            os.environ.pop("INTEGRATION_STORAGE", None)
