"""
Централизованные фикстуры для всех тестов проекта Amanita
"""
import pytest
import logging
import os
from unittest.mock import Mock, AsyncMock
from bot.services.core import blockchain
from bot.model.product import Product
from bot.model.organic_component import OrganicComponent
from bot.model.product import PriceInfo

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


@pytest.fixture(scope="function")
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
            
            # 🔧 ИЗОЛЯЦИЯ: Сбрасываем состояние при каждом создании фикстуры
            self._reset_state()
        
        def _reset_state(self):
            """Сброс состояния для изоляции тестов"""
            self.create_product_called = False
            self._next_blockchain_id = 1
            self.product_statuses.clear()
            self.product_cids.clear()
            logger.info("🔧 [MockBlockchainService] Состояние сброшено для изоляции тестов")
        
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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

@pytest.fixture(scope="function")
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Фикстура для HTTP клиента"""
    print("🔧 [API Client] Создание HTTP клиента для теста")
    
    async with httpx.AsyncClient(base_url=API_URL) as client:
        yield client
    
    print("🧹 [API Client] HTTP клиент закрыт и очищен")


@pytest.fixture(scope="function")
def test_api_key() -> str:
    """Фикстура для тестового API ключа"""
    return AMANITA_API_KEY


@pytest.fixture(scope="function")
def test_secret_key() -> str:
    """Фикстура для тестового секретного ключа"""
    return AMANITA_API_SECRET


@pytest.fixture(scope="function")
def valid_ethereum_address() -> str:
    """Фикстура для валидного Ethereum адреса"""
    return "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"


@pytest.fixture(scope="function")
def invalid_ethereum_address() -> str:
    """Фикстура для невалидного Ethereum адреса"""
    return "invalid-address"


@pytest.fixture(scope="function")
def valid_api_key() -> str:
    """Фикстура для валидного API ключа"""
    return "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"


@pytest.fixture(scope="function")
def invalid_api_key() -> str:
    """Фикстура для невалидного API ключа"""
    return "invalid-key"


@pytest.fixture(scope="function")
def test_request_data() -> dict:
    """Фикстура для тестовых данных запроса"""
    return {
        "client_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
        "description": "Test API key"
    }


@pytest.fixture(scope="function")
def mock_service_factory():
    """Фикстура для мока ServiceFactory"""
    print("🔧 [Service Factory] Создание Mock ServiceFactory")
    
    class MockServiceFactory:
        def create_api_key_service(self):
            return MockApiKeyService()
        
        def create_blockchain_service(self):
            return MockBlockchainService()
    
    factory = MockServiceFactory()
    yield factory
    
    print("🧹 [Service Factory] Mock ServiceFactory очищен")


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

@pytest.fixture(autouse=True, scope="function")
def reset_mock_states():
    """Автоматический сброс состояния моков перед каждым тестом"""
    print("🔧 [Reset] Сброс состояния моков для изоляции тестов")
    
    yield
    
    print("🧹 [Reset] Очистка состояния моков после теста")
    # Очистка происходит автоматически при создании новой фикстуры
    # благодаря scope="function" и методам _reset_state


@pytest.fixture(autouse=True, scope="function")
def clear_mock_storage_between_tests():
    """Автоматическая очистка MockIPFSStorage между тестами"""
    print("🔧 [Clear] Очистка MockIPFSStorage для изоляции тестов")
    
    yield
    
    print("🧹 [Clear] Очистка MockIPFSStorage после теста")
    # Очистка происходит автоматически при создании новой фикстуры
    # благодаря scope="function" и методам _reset_state


@pytest.fixture(autouse=True, scope="function")
def comprehensive_cleanup():
    """
    Комплексная фикстура для очистки всех данных после каждого теста.
    Автоматически запускается для каждого теста.
    """
    print("🔧 [Comprehensive] Комплексная очистка для изоляции тестов")
    
    yield
    
    print("🧹 [Comprehensive] Комплексная очистка завершена")
    # Дополнительная логика очистки может быть добавлена здесь
    # например, очистка временных файлов, сброс глобальных переменных и т.д.


@pytest.fixture(scope="function")
def temp_files_cleanup():
    """
    Фикстура для очистки временных файлов, созданных во время тестов.
    """
    import tempfile
    import os
    
    # Список временных файлов для очистки
    temp_files = []
    
    print("🔧 [Temp Files] Подготовка к очистке временных файлов")
    
    yield temp_files
    
    # Очистка временных файлов
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🧹 [Temp Files] Удален временный файл: {temp_file}")
        except Exception as e:
            print(f"⚠️ [Temp Files] Ошибка удаления файла {temp_file}: {e}")
    
    print("🧹 [Temp Files] Очистка временных файлов завершена")


@pytest.fixture(scope="function")
def cache_cleanup():
    """
    Фикстура для очистки кэша между тестами.
    """
    print("🔧 [Cache] Подготовка к очистке кэша")
    
    # Здесь можно добавить логику очистки различных типов кэша
    # например, очистка Redis, Memcached, локального кэша и т.д.
    
    yield
    
    print("🧹 [Cache] Кэш очищен")


@pytest.fixture(scope="function")
def mock_config():
    """Конфигурация моков через переменные окружения"""
    print("🔧 [Mock Config] Загрузка конфигурации моков")
    
    config = {
        "ipfs_mock_enabled": os.getenv("MOCK_IPFS", "true").lower() == "true",
        "blockchain_mock_enabled": os.getenv("MOCK_BLOCKCHAIN", "true").lower() == "true",
        "validation_mock_enabled": os.getenv("MOCK_VALIDATION", "true").lower() == "true"
    }
    
    yield config
    
    print("🧹 [Mock Config] Конфигурация моков очищена")

@pytest.fixture(scope="function")
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
            
            # 🔧 ИЗОЛЯЦИЯ: Сбрасываем состояние при каждом создании фикстуры
            self._reset_state()
        
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
        
        def _reset_state(self):
            """Сброс состояния для изоляции тестов"""
            self._storage.clear()
            self._counter = 0
            self.uploaded_files.clear()
            self.uploaded_jsons.clear()
            self.downloaded_json.clear()
            logger.info("🔧 [MockIPFSStorage] Состояние сброшено для изоляции тестов")
        
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

@pytest.fixture(scope="function")
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
    mock_metadata_service.process_metadata.return_value = None
    service.metadata_service = mock_metadata_service
    
    return service


@pytest.fixture(scope="function")
def mock_product_registry_service(mock_blockchain_service, mock_ipfs_storage, mock_validation_service, mock_account_service):
    """Полноценный Mock ProductRegistryService с полным интерфейсом"""
    from unittest.mock import Mock, AsyncMock
    from datetime import datetime, timedelta
    from typing import Dict, List, Optional, Union, Any
    from bot.model.product import Product, Description, PriceInfo
    import logging
    
    class MockProductRegistryService:
        """
        Полноценный Mock для ProductRegistryService.
        Реализует все публичные методы с детерминированным поведением.
        """
        
        def __init__(self, blockchain_service=None, storage_service=None, validation_service=None, account_service=None):
            """Инициализация Mock ProductRegistryService"""
            self.logger = logging.getLogger(__name__)
            
            # Зависимости
            self.blockchain_service = blockchain_service or Mock()
            self.storage_service = storage_service or Mock()
            self.validation_service = validation_service or Mock()
            self.account_service = account_service or Mock()
            
            # Внутренние сервисы
            self.cache_service = Mock()
            self.metadata_service = Mock()
            
            # Внутреннее состояние для тестирования
            self._products = {}  # product_id -> Product
            self._product_counter = 1
            self._catalog_version = 1
            self._cache_data = {}
            self._metadata_cids = {}  # product_id -> metadata_cid
            self._blockchain_ids = {}  # product_id -> blockchain_id
            
            # 🔧 ИЗОЛЯЦИЯ: Сбрасываем состояние при каждом создании фикстуры
            self._reset_state()
            
            # Инициализация начальных данных для тестирования
            self._initialize_test_data()
            
            # Настройка поведения по умолчанию
            self._setup_default_behavior()
            
            logger.info("🔧 MockProductRegistryService инициализирован")
        
        def _reset_state(self):
            """Сброс состояния для изоляции тестов"""
            self._products.clear()
            self._product_counter = 1
            self._catalog_version = 1
            self._cache_data.clear()
            self._metadata_cids.clear()
            self._blockchain_ids.clear()
            logger.info("🔧 [MockProductRegistryService] Состояние сброшено для изоляции тестов")
        
        def _setup_default_behavior(self):
            """Настройка поведения по умолчанию"""
            # Настройка cache_service
            self.cache_service.get_cached_item.return_value = None
            self.cache_service.set_cached_item.return_value = True
            self.cache_service.invalidate_cache.return_value = None
            self.cache_service.get_description_by_cid.return_value = None
            self.cache_service.get_image_url_by_cid.return_value = "https://mocked.ipfs/test.jpg"
            
            # Настройка metadata_service
            self.metadata_service.process_product_metadata.return_value = None
            self.metadata_service.create_product_metadata.return_value = {}
            
            # Настройка validation_service
            self.validation_service.validate_product_data = AsyncMock(return_value={
                "is_valid": True,
                "errors": []
            })
            
            # Настройка storage_service - только если это Mock объект
            if hasattr(self.storage_service, 'return_value'):
                # Если storage_service - это Mock объект, настраиваем его
                self.storage_service.download_json.return_value = {
                    "id": "test_product",
                    "title": "Test Product",
                    "description_cid": "QmDescriptionCID",
                    "cover_image": "QmImageCID",
                    "categories": ["mushroom"],
                    "forms": ["powder"],
                    "species": "Amanita muscaria",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
                }
                self.storage_service.upload_json = AsyncMock(return_value="QmMockCID")
                self.storage_service.is_valid_cid.return_value = True
            # Если storage_service уже имеет реализованные методы (например, MockIPFSStorage),
            # то не нужно их переопределять
            
            # Настройка blockchain_service - только если это Mock объект
            if hasattr(self.blockchain_service, 'return_value'):
                # Если blockchain_service - это Mock объект, настраиваем его
                self.blockchain_service.get_catalog_version.return_value = 1
                self.blockchain_service.get_all_products.return_value = []
                self.blockchain_service.get_products_by_current_seller_full.return_value = []
                self.blockchain_service.product_exists_in_blockchain.return_value = False
                self.blockchain_service.create_product = AsyncMock(return_value="0x123")
                self.blockchain_service.update_product_status = AsyncMock(return_value="0x456")
                self.blockchain_service.deactivate_product = AsyncMock(return_value="0x789")
                self.blockchain_service.get_product_id_from_tx = AsyncMock(return_value="0x42")
            # Если blockchain_service уже имеет реализованные методы (например, MockBlockchainService),
            # то не нужно их переопределять
        
        def _initialize_test_data(self):
            """Инициализация начальных тестовых данных"""
            # Создаем продукт с ID=1 для тестирования
            test_product = {
                "id": "1",
                "title": "Test Product 1",
                "description": {"en": "Test description for product 1"},
                "description_cid": "QmTestDescriptionCID1",
                "cover_image": "QmTestCoverCID1",
                "gallery": ["QmTestGalleryCID1"],
                "categories": ["mushroom", "test"],
                "forms": ["powder"],
                "species": "Amanita muscaria",
                "organic_components": ["Amanita muscaria"],
                "prices": [{"weight": "100", "weight_unit": "g", "price": "50", "currency": "EUR"}],
                "attributes": {"sku": "TEST1", "stock": 10}
            }
            
            # Добавляем в внутреннее состояние
            self._products["1"] = test_product
            self._metadata_cids["1"] = "QmTestMetadataCID1"
            self._blockchain_ids["1"] = 1
            
            # Обновляем счетчик
            self._product_counter = 2
            
            logger.info("🔧 [Mock] Инициализированы тестовые данные: продукт с ID=1")
        
        # === ОСНОВНЫЕ МЕТОДЫ УПРАВЛЕНИЯ ПРОДУКТАМИ ===
        
        async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
            """Создает новый продукт"""
            try:
                product_id = product_data.get("id")
                logger.info(f"🔧 [Mock] Создание продукта: {product_id}")
                
                # Валидация
                validation_result = await self.validation_service.validate_product_data(product_data)
                if not validation_result["is_valid"]:
                    return {
                        "id": product_id,
                        "status": "error",
                        "error": "; ".join(validation_result["errors"])
                    }
                
                # Проверка уникальности ID
                if product_id and await self._check_product_id_exists(product_id):
                    return {
                        "id": product_id,
                        "status": "error",
                        "error": f"Продукт с ID '{product_id}' уже существует"
                    }
                
                # Создание метаданных
                metadata = self.create_product_metadata(product_data)
                
                # Загрузка в IPFS
                metadata_cid = await self.storage_service.upload_json(metadata)
                if not metadata_cid:
                    return {
                        "id": product_id,
                        "status": "error",
                        "error": "Ошибка загрузки метаданных в IPFS"
                    }
                
                # Запись в блокчейн
                tx_hash = await self.blockchain_service.create_product(metadata_cid)
                if not tx_hash:
                    return {
                        "id": product_id,
                        "metadata_cid": metadata_cid,
                        "status": "error",
                        "error": "Ошибка записи в блокчейн"
                    }
                
                # Получение blockchain_id
                blockchain_id = await self.blockchain_service.get_product_id_from_tx(tx_hash)
                
                # Сохранение в внутреннем состоянии
                self._products[product_id] = product_data
                self._metadata_cids[product_id] = metadata_cid
                self._blockchain_ids[product_id] = blockchain_id
                self._product_counter += 1
                
                logger.info(f"🔧 [Mock] Продукт {product_id} создан успешно")
                return {
                    "id": product_id,
                    "metadata_cid": metadata_cid,
                    "blockchain_id": str(blockchain_id) if blockchain_id else None,
                    "tx_hash": str(tx_hash) if tx_hash else None,
                    "status": "success",
                    "error": None
                }
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка создания продукта: {e}")
                return {
                    "id": product_data.get("id"),
                    "status": "error",
                    "error": str(e)
                }
        
        async def get_product(self, product_id: Union[str, int]) -> Optional[Product]:
            """Получает продукт по ID"""
            try:
                if not product_id:
                    return None
                
                product_id_str = str(product_id)
                logger.info(f"🔧 [Mock] Получение продукта: {product_id_str}")
                
                # Проверяем внутреннее состояние
                if product_id_str in self._products:
                    product_data = self._products[product_id_str]
                    metadata_cid = self._metadata_cids.get(product_id_str)
                    blockchain_id = self._blockchain_ids.get(product_id_str)
                    
                    # Создаем объект Product
                    
                    # Создаем OrganicComponent для тестирования
                    organic_component = OrganicComponent(
                        biounit_id="test_biounit_1",
                        description_cid="QmTestDescriptionCID1",
                        proportion="100%"
                    )
                    
                    # Создаем тестовую цену
                    test_price = PriceInfo(
                        price=50.0,
                        weight=100,
                        weight_unit="g",
                        currency="EUR"
                    )
                    
                    product = Product(
                        id=blockchain_id or int(product_id_str),
                        alias=product_id_str,
                        status=1,  # Активный по умолчанию
                        cid=metadata_cid or "QmMockCID",
                        title=product_data.get("title", ""),
                        organic_components=[organic_component],
                        cover_image_url="https://mocked.ipfs/test.jpg",
                        categories=product_data.get("categories", []),
                        forms=product_data.get("forms", []),
                        species=product_data.get("species", ""),
                        prices=[test_price]
                    )
                    
                    logger.info(f"🔧 [Mock] Продукт {product_id_str} найден")
                    return product
                
                # Если не найден в внутреннем состоянии, пробуем блокчейн
                product_data = self.blockchain_service.get_product(product_id)
                if product_data:
                    return await self._deserialize_product(product_data)
                
                logger.info(f"🔧 [Mock] Продукт {product_id_str} не найден")
                return None
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка получения продукта {product_id}: {e}")
                return None
        
        async def get_all_products(self) -> List[Product]:
            """Получает все продукты"""
            try:
                logger.info("🔧 [Mock] Получение всех продуктов")
                
                # Проверяем кэш
                cached_catalog = self.cache_service.get_cached_item("catalog", "catalog")
                if cached_catalog and cached_catalog.get("products"):
                    logger.info("🔧 [Mock] Возвращаем кэшированный каталог")
                    return cached_catalog["products"]
                
                # Получаем из блокчейна
                products_data = self.blockchain_service.get_all_products()
                products = []
                
                for product_data in products_data:
                    product = await self._deserialize_product(product_data)
                    if product:
                        products.append(product)
                
                # Обновляем кэш
                self.cache_service.set_cached_item("catalog", {
                    "version": self._catalog_version,
                    "products": products
                }, "catalog")
                
                logger.info(f"🔧 [Mock] Получено {len(products)} продуктов")
                return products
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка получения всех продуктов: {e}")
                return []
        
        async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
            """Обновляет продукт"""
            try:
                logger.info(f"🔧 [Mock] Обновление продукта: {product_id}")
                
                # Проверка существования
                existing_product = await self.get_product(product_id)
                if not existing_product:
                    return {
                        "id": product_id,
                        "status": "error",
                        "error": f"Продукт с ID {product_id} не найден"
                    }
                
                # Валидация
                is_valid = await self.validate_product(product_data)
                if not is_valid:
                    return {
                        "id": product_id,
                        "status": "error",
                        "error": f"Данные продукта {product_id} не прошли валидацию"
                    }
                
                # Обновление метаданных
                new_metadata = self.create_product_metadata(product_data)
                new_metadata["updated_at"] = datetime.now().isoformat()
                
                # Загрузка в IPFS
                new_metadata_cid = await self.storage_service.upload_json(new_metadata)
                if not new_metadata_cid:
                    return {
                        "id": product_id,
                        "status": "error",
                        "error": f"Не удалось загрузить метаданные в IPFS для продукта {product_id}"
                    }
                
                # Обновление внутреннего состояния
                self._products[product_id] = product_data
                self._metadata_cids[product_id] = new_metadata_cid
                
                logger.info(f"🔧 [Mock] Продукт {product_id} обновлен успешно")
                return {
                    "id": product_id,
                    "metadata_cid": new_metadata_cid,
                    "blockchain_id": None,  # Не обновляем в блокчейне в Mock
                    "tx_hash": None,
                    "status": "success",
                    "error": None
                }
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка обновления продукта {product_id}: {e}")
                return {
                    "id": product_id,
                    "status": "error",
                    "error": str(e)
                }
        
        async def update_product_status(self, product_id: int, new_status: int) -> bool:
            """Обновляет статус продукта"""
            try:
                logger.info(f"🔧 [Mock] Обновление статуса продукта {product_id} на {new_status}")
                
                # Проверка существования
                existing_product = await self.get_product(str(product_id))
                if not existing_product:
                    self.logger.error(f"🔧 [Mock] Продукт {product_id} не найден")
                    return False
                
                # Выполнение операции в блокчейне
                tx_hash = await self.blockchain_service.update_product_status(
                    "mock_private_key",
                    product_id,
                    new_status
                )
                
                if not tx_hash:
                    self.logger.error(f"🔧 [Mock] Ошибка обновления статуса продукта {product_id}")
                    return False
                
                logger.info(f"🔧 [Mock] Статус продукта {product_id} обновлен: {new_status}")
                return True
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка обновления статуса продукта {product_id}: {e}")
                return False
        
        async def deactivate_product(self, product_id: int) -> bool:
            """Деактивирует продукт"""
            try:
                logger.info(f"🔧 [Mock] Деактивация продукта {product_id}")
                
                tx_hash = await self.blockchain_service.deactivate_product(product_id)
                if not tx_hash:
                    self.logger.error(f"🔧 [Mock] Ошибка деактивации продукта {product_id}")
                    return False
                
                logger.info(f"🔧 [Mock] Продукт {product_id} деактивирован")
                return True
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка деактивации продукта {product_id}: {e}")
                return False
        
        # === МЕТОДЫ ВАЛИДАЦИИ И ПРОВЕРКИ ===
        
        async def validate_product(self, product_data: Dict[str, Any]) -> bool:
            """Валидирует данные продукта"""
            try:
                logger.info(f"🔧 [Mock] Валидация продукта")
                
                # Проверяем обязательные поля
                required_fields = ['title', 'organic_components', 'categories', 'cover_image', 'forms', 'species', 'prices']
                for field in required_fields:
                    if field not in product_data:
                        self.logger.error(f"Missing required field: {field}")
                        return False
                    
                    if not product_data[field]:
                        self.logger.error(f"Empty required field: {field}")
                        return False
                
                # Проверяем цены
                if not isinstance(product_data['prices'], list) or not product_data['prices']:
                    self.logger.error("Цены должны быть непустым списком")
                    return False
                
                # Проверяем формы
                if not isinstance(product_data['forms'], list) or not product_data['forms']:
                    self.logger.error("Формы должны быть непустым списком")
                    return False
                
                # Проверяем IPFS CID
                if not self.storage_service.is_valid_cid(product_data['cover_image']):
                    self.logger.error("Invalid cover image CID")
                    return False
                
                logger.info("🔧 [Mock] Валидация продукта прошла успешно")
                return True
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка валидации продукта: {e}")
                return False
        
        async def _check_product_id_exists(self, product_id: Union[str, int]) -> bool:
            """Проверяет существование продукта по ID"""
            try:
                product_id_str = str(product_id)
                logger.info(f"🔧 [Mock] Проверка существования продукта: {product_id_str}")
                
                # Проверяем внутреннее состояние
                if product_id_str in self._products:
                    logger.info(f"🔧 [Mock] Продукт {product_id_str} найден во внутреннем состоянии")
                    return True
                
                # Проверяем через get_product
                product = await self.get_product(product_id_str)
                if product:
                    logger.info(f"🔧 [Mock] Продукт {product_id_str} найден через get_product")
                    return True
                
                # Проверяем блокчейн ID если это число
                try:
                    numeric_id = int(product_id_str)
                    if self._check_blockchain_product_exists(numeric_id):
                        logger.info(f"🔧 [Mock] Продукт с blockchain ID {numeric_id} найден")
                        return True
                except (ValueError, TypeError):
                    pass
                
                logger.info(f"🔧 [Mock] Продукт {product_id_str} не найден")
                return False
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка проверки существования продукта {product_id}: {e}")
                return False
        
        def _check_blockchain_product_exists(self, blockchain_id: int) -> bool:
            """Проверяет существование продукта в блокчейне"""
            try:
                logger.info(f"🔧 [Mock] Проверка blockchain ID: {blockchain_id}")
                
                exists = self.blockchain_service.product_exists_in_blockchain(blockchain_id)
                logger.info(f"🔧 [Mock] Blockchain ID {blockchain_id} {'найден' if exists else 'не найден'}")
                return exists
                
            except Exception as e:
                self.logger.warning(f"🔧 [Mock] Ошибка при проверке blockchain ID {blockchain_id}: {e}")
                return False
        
        # === МЕТОДЫ КЭШИРОВАНИЯ ===
        
        def _is_cache_valid(self, timestamp: datetime, cache_type: str) -> bool:
            """Проверяет актуальность кэша"""
            if not timestamp:
                return False
            
            cache_ttl = {
                'catalog': timedelta(minutes=5),
                'description': timedelta(hours=24),
                'image': timedelta(hours=12)
            }
            
            return datetime.utcnow() - timestamp < cache_ttl.get(cache_type, timedelta(minutes=5))
        
        def _update_catalog_cache(self, version: int, products: List[Product]) -> None:
            """Обновляет кэш каталога"""
            self.cache_service.set_cached_item("catalog", {
                "version": version,
                "products": products
            }, "catalog")
            logger.info(f"🔧 [Mock] Кэш каталога обновлен: {len(products)} продуктов")
        
        def clear_cache(self, cache_type: Optional[str] = None) -> None:
            """Очищает кэш"""
            self.cache_service.invalidate_cache(cache_type)
            logger.info(f"🔧 [Mock] Кэш очищен: {cache_type if cache_type else 'все'}")
        
        def get_catalog_version(self) -> int:
            """Получает версию каталога"""
            try:
                version = self.blockchain_service.get_catalog_version()
                logger.info(f"🔧 [Mock] Версия каталога: {version}")
                return version
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка получения версии каталога: {e}")
                return 0
        
        # === МЕТОДЫ РАБОТЫ С МЕТАДАННЫМИ ===
        
        def create_product_metadata(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
            """Создает метаданные продукта"""
            try:
                logger.info("🔧 [Mock] Создание метаданных продукта")
                
                metadata = {
                    "id": product_data["id"],
                    "title": product_data["title"],
                    "organic_components": product_data["organic_components"],
                    "cover_image": product_data["cover_image"],
                    "categories": product_data["categories"],
                    "forms": product_data["forms"],
                    "species": product_data["species"],
                    "prices": product_data["prices"],
                    "created_at": datetime.now().isoformat()
                }
                
                logger.info("🔧 [Mock] Метаданные созданы успешно")
                return metadata
                
            except KeyError as e:
                self.logger.error(f"🔧 [Mock] Отсутствует обязательное поле: {e}")
                raise
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка создания метаданных: {e}")
                raise
        
        def upload_product_metadata(self, product_metadata: Dict[str, Any]) -> str:
            """Загружает метаданные продукта"""
            try:
                logger.info("🔧 [Mock] Загрузка метаданных продукта")
                cid = self.storage_service.upload_json(product_metadata)
                logger.info(f"🔧 [Mock] Метаданные загружены: {cid}")
                return cid
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка загрузки метаданных: {e}")
                raise
        
        def upload_media_file(self, file_path: str) -> str:
            """Загружает медиафайл"""
            try:
                logger.info(f"🔧 [Mock] Загрузка медиафайла: {file_path}")
                cid = self.storage_service.upload_media_file(file_path)
                logger.info(f"🔧 [Mock] Медиафайл загружен: {cid}")
                return cid
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка загрузки медиафайла: {e}")
                raise
        
        def create_product_on_chain(self, ipfs_cid: str) -> str:
            """Создает продукт в блокчейне"""
            try:
                logger.info(f"🔧 [Mock] Создание продукта в блокчейне: {ipfs_cid}")
                
                if not self._validate_ipfs_cid(ipfs_cid):
                    raise ValueError(f"Некорректный CID: {ipfs_cid}")
                
                tx_hash = self.blockchain_service.create_product(ipfs_cid)
                if not tx_hash:
                    raise Exception("Транзакция не прошла")
                
                logger.info(f"🔧 [Mock] Продукт создан в блокчейне: {tx_hash}")
                return tx_hash
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка создания продукта в блокчейне: {e}")
                raise
        
        # === МЕТОДЫ ОБРАБОТКИ ПРОДУКТОВ ===
        
        def _process_product_metadata(self, product_id: Union[int, str], ipfs_cid: str, active: bool) -> Optional[Product]:
            """Обрабатывает метаданные продукта"""
            try:
                logger.info(f"🔧 [Mock] Обработка метаданных продукта: {product_id}")
                
                # Валидация CID
                validation_result = self.validation_service.validate_cid(ipfs_cid)
                if not validation_result["is_valid"]:
                    self.logger.error(f"🔧 [Mock] Некорректный CID метаданных: {ipfs_cid}")
                    return None
                
                # Загрузка метаданных
                metadata = self.storage_service.download_json(ipfs_cid)
                if not isinstance(metadata, dict):
                    self.logger.error(f"🔧 [Mock] Некорректный формат метаданных: {product_id}")
                    return None
                
                # Создание объекта Product
                product = Product(
                    id=product_id,
                    alias=str(product_id),
                    status=1 if active else 0,
                    cid=ipfs_cid,
                    title=metadata.get('title', ''),
                    description=None,
                    description_cid=metadata.get('description_cid', ''),
                    cover_image_url=self._get_cached_image(metadata.get('cover_image', '')),
                    categories=metadata.get('categories', []),
                    forms=metadata.get('forms', []),
                    species=metadata.get('species', ''),
                    prices=[]
                )
                
                logger.info(f"🔧 [Mock] Метаданные продукта {product_id} обработаны")
                return product
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка обработки метаданных продукта {product_id}: {e}")
                return None
        
        async def _deserialize_product(self, product_data: tuple) -> Optional[Product]:
            """Десериализует продукт из кортежа блокчейна"""
            try:
                if not hasattr(product_data, '__getitem__') or len(product_data) < 4:
                    self.logger.error(f"🔧 [Mock] Некорректная структура product_data: {product_data}")
                    return None
                
                product_id = product_data[0]
                ipfs_cid = product_data[2]
                is_active = bool(product_data[3])
                
                logger.info(f"🔧 [Mock] Десериализация продукта: {product_id}, {ipfs_cid}, {is_active}")
                
                # Загрузка метаданных
                metadata = self.storage_service.download_json(ipfs_cid)
                if not metadata:
                    self.logger.warning(f"🔧 [Mock] Не удалось получить метаданные для продукта {product_id}")
                    return None
                
                # Обработка через metadata_service
                product = self.metadata_service.process_product_metadata(metadata)
                if product:
                    product.id = product_id
                    product.cid = ipfs_cid
                    product.status = 1 if is_active else 0
                
                logger.info(f"🔧 [Mock] Продукт {product_id} десериализован")
                return product
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка десериализации продукта: {e}")
                return None
        
        # === МЕТОДЫ РАБОТЫ С IPFS CID ===
        
        def _validate_ipfs_cid(self, cid: str) -> bool:
            """Проверяет валидность IPFS CID"""
            if not cid:
                return False
            import re
            pattern = re.compile(r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[A-Za-z2-7]{55})$')
            return bool(pattern.match(cid))
        
        def _get_cached_description(self, description_cid: str) -> Optional[Description]:
            """Получает кэшированное описание продукта"""
            return self.cache_service.get_description_by_cid(description_cid)
        
        def _get_cached_image(self, image_cid: str) -> Optional[str]:
            """Получает кэшированную ссылку на изображение"""
            return self.cache_service.get_image_url_by_cid(image_cid)
        
        # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
        
        def clear_state(self):
            """Очищает внутреннее состояние для тестирования"""
            self._products.clear()
            self._metadata_cids.clear()
            self._blockchain_ids.clear()
            self._product_counter = 1
            self._catalog_version = 1
            self._cache_data.clear()
            logger.info("🔧 [Mock] Внутреннее состояние очищено")
        
        def get_internal_state(self) -> Dict[str, Any]:
            """Возвращает внутреннее состояние для отладки"""
            return {
                "products_count": len(self._products),
                "metadata_cids_count": len(self._metadata_cids),
                "blockchain_ids_count": len(self._blockchain_ids),
                "product_counter": self._product_counter,
                "catalog_version": self._catalog_version
            }
    
    return MockProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )

@pytest.fixture(scope="function")
def mock_registry_service_with_failing_storage(mock_blockchain_service, mock_validation_service, mock_account_service, mock_ipfs_storage_failing):
    """ProductRegistryService с моканным IPFS storage, который симулирует ошибки"""
    from bot.services.product.registry import ProductRegistryService
    
    return ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage_failing,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )

@pytest.fixture(scope="function")
def mock_product_registry_service_with_failing_validation(mock_blockchain_service, mock_ipfs_storage, mock_account_service, mock_validation_service_failing):
    """ProductRegistryService с моканным validation service, который симулирует ошибки"""
    from bot.services.product.registry import ProductRegistryService
    
    return ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage,
        validation_service=mock_validation_service_failing,
        account_service=mock_account_service
    )


# === ИНТЕГРАЦИОННЫЕ ТЕСТЫ - НОВЫЕ ФИКСТУРЫ ===

@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def test_products():
    """Генерация тестовых продуктов для интеграционных тестов"""
    print("🔧 [Test Products] Создание тестовых продуктов")
    
    products = [
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
    
    yield products
    
    print("🧹 [Test Products] Тестовые продукты очищены")

# === ФИКСТУРЫ ДЛЯ ПРЕДВАРИТЕЛЬНОЙ ЗАГРУЗКИ ДАННЫХ ===

@pytest.fixture(scope="function")
async def preloaded_products_basic(mock_product_registry_service):
    """
    Фикстура для предварительной загрузки базовых тестовых продуктов.
    Scope: function - каждый тест получает свежие данные.
    """
    products_data = [
        {
            "id": "preload_basic_001",
            "title": "Basic Test Product 1",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "QmBasicTestCID001",
                    "proportion": "100%"
                }
            ],
            "cover_image": "QmBasicCoverCID001",
            "categories": ["mushroom", "test"],
            "forms": ["powder"],
            "species": "Amanita muscaria",
            "prices": [
                {
                    "weight": "100",
                    "weight_unit": "g",
                    "price": "50",
                    "currency": "EUR"
                }
            ]
        },
        {
            "id": "preload_basic_002",
            "title": "Basic Test Product 2",
            "organic_components": [
                {
                    "biounit_id": "amanita_pantherina",
                    "description_cid": "QmBasicTestCID002",
                    "proportion": "100%"
                }
            ],
            "cover_image": "QmBasicCoverCID002",
            "categories": ["mushroom", "test"],
            "forms": ["capsules"],
            "species": "Amanita pantherina",
            "prices": [
                {
                    "weight": "60",
                    "weight_unit": "capsules",
                    "price": "75",
                    "currency": "EUR"
                }
            ]
        }
    ]
    
    # Загружаем продукты в mock сервис
    created_products = []
    for product_data in products_data:
        result = await mock_product_registry_service.create_product(product_data)
        if result["status"] == "success":
            created_products.append(result)
            print(f"🔧 [Preload] Создан продукт: {product_data['id']}")
        else:
            print(f"⚠️ [Preload] Ошибка создания продукта {product_data['id']}: {result['error']}")
    
    yield created_products
    
    # Очистка после теста (автоматически)
    print(f"🧹 [Preload] Очистка {len(created_products)} предзагруженных продуктов")

@pytest.fixture(scope="function")
async def preloaded_products_extended(mock_product_registry_service):
    """
    Фикстура для предварительной загрузки расширенных тестовых продуктов.
    Scope: function - каждый тест получает свежие данные.
    """
    products_data = [
        {
            "id": "preload_extended_001",
            "title": "Extended Test Product 1",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "QmExtendedTestCID001",
                    "proportion": "70%"
                },
                {
                    "biounit_id": "amanita_pantherina",
                    "description_cid": "QmExtendedTestCID002",
                    "proportion": "30%"
                }
            ],
            "cover_image": "QmExtendedCoverCID001",
            "categories": ["mushroom", "test", "extended"],
            "forms": ["powder", "capsules"],
            "species": "Amanita muscaria",
            "prices": [
                {
                    "weight": "200",
                    "weight_unit": "g",
                    "price": "120",
                    "currency": "EUR"
                },
                {
                    "weight": "100",
                    "weight_unit": "capsules",
                    "price": "80",
                    "currency": "EUR"
                }
            ]
        },
        {
            "id": "preload_extended_002",
            "title": "Extended Test Product 2",
            "organic_components": [
                {
                    "biounit_id": "blue_lotus",
                    "description_cid": "QmExtendedTestCID003",
                    "proportion": "100%"
                }
            ],
            "cover_image": "QmExtendedCoverCID002",
            "categories": ["flower", "test", "extended"],
            "forms": ["tincture"],
            "species": "Blue Lotus",
            "prices": [
                {
                    "weight": "50",
                    "weight_unit": "ml",
                    "price": "45",
                    "currency": "EUR"
                }
            ]
        }
    ]
    
    # Загружаем продукты в mock сервис
    created_products = []
    for product_data in products_data:
        result = await mock_product_registry_service.create_product(product_data)
        if result["status"] == "success":
            created_products.append(result)
            print(f"🔧 [Preload] Создан расширенный продукт: {product_data['id']}")
        else:
            print(f"⚠️ [Preload] Ошибка создания расширенного продукта {product_data['id']}: {result['error']}")
    
    yield created_products
    
    # Очистка после теста (автоматически)
    print(f"🧹 [Preload] Очистка {len(created_products)} расширенных продуктов")

@pytest.fixture(scope="function")
async def preloaded_products_validation(mock_product_registry_service):
    """
    Фикстура для предварительной загрузки продуктов для тестирования валидации.
    Scope: function - каждый тест получает свежие данные.
    """
    products_data = [
        {
            "id": "preload_validation_001",
            "title": "Validation Test Product 1",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "QmValidationTestCID001",
                    "proportion": "100%"
                }
            ],
            "cover_image": "QmValidationCoverCID001",
            "categories": ["mushroom", "validation"],
            "forms": ["powder"],
            "species": "Amanita muscaria",
            "prices": [
                {
                    "weight": "100",
                    "weight_unit": "g",
                    "price": "50",
                    "currency": "EUR"
                }
            ]
        },
        {
            "id": "preload_validation_002",
            "title": "Validation Test Product 2",
            "organic_components": [
                {
                    "biounit_id": "amanita_pantherina",
                    "description_cid": "QmValidationTestCID002",
                    "proportion": "100%"
                }
            ],
            "cover_image": "QmValidationCoverCID002",
            "categories": ["mushroom", "validation"],
            "forms": ["capsules"],
            "species": "Amanita pantherina",
            "prices": [
                {
                    "weight": "60",
                    "weight_unit": "capsules",
                    "price": "75",
                    "currency": "EUR"
                }
            ]
        }
    ]
    
    # Загружаем продукты в mock сервис
    created_products = []
    for product_data in products_data:
        result = await mock_product_registry_service.create_product(product_data)
        if result["status"] == "success":
            created_products.append(result)
            print(f"🔧 [Preload] Создан продукт для валидации: {product_data['id']}")
        else:
            print(f"⚠️ [Preload] Ошибка создания продукта для валидации {product_data['id']}: {result['error']}")
    
    yield created_products
    
    # Очистка после теста (автоматически)
    print(f"🧹 [Preload] Очистка {len(created_products)} продуктов для валидации")

@pytest.fixture(scope="function")
def preloaded_categories():
    """
    Фикстура для предварительной загрузки категорий продуктов.
    Scope: function - каждый тест получает свежие данные.
    """
    print("🔧 [Preload] Загрузка категорий продуктов")
    
    categories = [
        "mushroom",
        "flower", 
        "herb",
        "test",
        "validation",
        "extended",
        "mental health",
        "focus",
        "ADHD support",
        "mental force",
        "energy",
        "relaxation",
        "sleep",
        "immunity",
        "digestion"
    ]
    
    print(f"🔧 [Preload] Загружено {len(categories)} категорий")
    yield categories
    
    print("🧹 [Preload] Категории продуктов очищены")

@pytest.fixture(scope="function")
def preloaded_forms():
    """
    Фикстура для предварительной загрузки форм продуктов.
    Scope: function - каждый тест получает свежие данные.
    """
    print("🔧 [Preload] Загрузка форм продуктов")
    
    forms = [
        "powder",
        "capsules",
        "tincture",
        "tea",
        "extract",
        "mixed slices",
        "dried",
        "fresh",
        "oil",
        "cream"
    ]
    
    print(f"🔧 [Preload] Загружено {len(forms)} форм")
    yield forms
    
    print("🧹 [Preload] Формы продуктов очищены")

@pytest.fixture(scope="function")
def preloaded_species():
    """
    Фикстура для предварительной загрузки видов продуктов.
    Scope: function - каждый тест получает свежие данные.
    """
    print("🔧 [Preload] Загрузка видов продуктов")
    
    species = [
        "Amanita muscaria",
        "Amanita pantherina",
        "Blue Lotus",
        "Chaga",
        "Cordyceps militaris",
        "Lion's Mane",
        "Reishi",
        "Chamomile",
        "Lavender",
        "Peppermint"
    ]
    
    print(f"🔧 [Preload] Загружено {len(species)} видов")
    yield species
    
    print("🧹 [Preload] Виды продуктов очищены")

@pytest.fixture(scope="function")
def preloaded_biounits():
    """
    Фикстура для предварительной загрузки биологических единиц.
    Scope: function - каждый тест получает свежие данные.
    """
    print("🔧 [Preload] Загрузка биологических единиц")
    
    biounits = [
        "amanita_muscaria",
        "amanita_pantherina",
        "blue_lotus",
        "chaga",
        "cordyceps_militaris",
        "lions_mane",
        "reishi",
        "chamomile",
        "lavender",
        "peppermint"
    ]
    
    print(f"🔧 [Preload] Загружено {len(biounits)} биологических единиц")
    yield biounits
    
    print("🧹 [Preload] Биологические единицы очищены")

@pytest.fixture(scope="function")
async def preloaded_all_data(mock_product_registry_service):
    """
    Фикстура для предварительной загрузки всех типов данных.
    Scope: function - каждый тест получает свежие данные.
    """
    # Загружаем продукты
    basic_products = await preloaded_products_basic(mock_product_registry_service)
    extended_products = await preloaded_products_extended(mock_product_registry_service)
    validation_products = await preloaded_products_validation(mock_product_registry_service)
    
    # Загружаем справочные данные
    categories = preloaded_categories()
    forms = preloaded_forms()
    species = preloaded_species()
    biounits = preloaded_biounits()
    
    # Собираем все данные
    all_data = {
        "products": {
            "basic": basic_products,
            "extended": extended_products,
            "validation": validation_products
        },
        "reference": {
            "categories": categories,
            "forms": forms,
            "species": species,
            "biounits": biounits
        }
    }
    
    print(f"🔧 [Preload] Загружены все данные: {len(basic_products)} + {len(extended_products)} + {len(validation_products)} продуктов, {len(categories)} категорий, {len(forms)} форм")
    
    yield all_data
    
    # Очистка происходит автоматически через yield в отдельных фикстурах
    print("🧹 [Preload] Очистка всех предзагруженных данных")

@pytest.fixture(params=["basic", "extended", "validation"])
def product_type_parametrized(request):
    """
    Фикстура для параметризованного тестирования разных типов продуктов.
    Scope: function - каждый тест получает свежие данные.
    """
    product_type = request.param
    print(f"🔧 [Preload] Параметризованный тип продукта: {product_type}")
    
    yield product_type
    
    print(f"🧹 [Preload] Параметризованный тип продукта {product_type} очищен")

@pytest.fixture(params=["mushroom", "flower", "herb"])
def category_parametrized(request):
    """
    Фикстура для параметризованного тестирования разных категорий.
    Scope: function - каждый тест получает свежие данные.
    """
    category = request.param
    print(f"🔧 [Preload] Параметризованная категория: {category}")
    
    yield category
    
    print(f"🧹 [Preload] Параметризованная категория {category} очищена")

@pytest.fixture(params=["powder", "capsules", "tincture"])
def form_parametrized(request):
    """
    Фикстура для параметризованного тестирования разных форм.
    Scope: function - каждый тест получает свежие данные.
    """
    form = request.param
    print(f"🔧 [Preload] Параметризованная форма: {form}")
    
    yield form
    
    print(f"🧹 [Preload] Параметризованная форма {form} очищена")

# === ТЕСТЫ ДЛЯ ПРОВЕРКИ ФИКСТУР ===

def test_integration_storage_config_mock():
    """Тест фикстуры integration_storage_config в mock режиме"""
    # Сохраняем оригинальное значение переменной окружения
    original_storage = os.getenv("INTEGRATION_STORAME")
    
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


def test_preloaded_fixtures():
    """Тест новых фикстур для предварительной загрузки данных"""
    # Тестируем синхронные фикстуры
    categories = preloaded_categories()
    forms = preloaded_forms()
    species = preloaded_species()
    biounits = preloaded_biounits()
    
    # Проверяем структуру данных
    assert isinstance(categories, list)
    assert isinstance(forms, list)
    assert isinstance(species, list)
    assert isinstance(biounits, list)
    
    # Проверяем содержимое
    assert len(categories) > 0
    assert len(forms) > 0
    assert len(species) > 0
    assert len(biounits) > 0
    
    # Проверяем конкретные значения
    assert "mushroom" in categories
    assert "powder" in forms
    assert "Amanita muscaria" in species
    assert "amanita_muscaria" in biounits
    
    print("✅ Тест новых фикстур для предварительной загрузки данных пройден")


@pytest.mark.asyncio
async def test_preloaded_products_fixtures(mock_product_registry_service):
    """Тест асинхронных фикстур для предварительной загрузки продуктов"""
    # Тестируем асинхронные фикстуры
    basic_products = await preloaded_products_basic(mock_product_registry_service)
    extended_products = await preloaded_products_extended(mock_product_registry_service)
    validation_products = await preloaded_products_validation(mock_product_registry_service)
    
    # Проверяем структуру данных
    assert isinstance(basic_products, list)
    assert isinstance(extended_products, list)
    assert isinstance(validation_products, list)
    
    # Проверяем содержимое
    assert len(basic_products) > 0
    assert len(extended_products) > 0
    assert len(validation_products) > 0
    
    # Проверяем, что продукты созданы успешно
    for product in basic_products + extended_products + validation_products:
        assert "status" in product
        assert product["status"] == "success"
        assert "id" in product
    
    print("✅ Тест асинхронных фикстур для предварительной загрузки продуктов пройден")


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
