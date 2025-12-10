"""
Централизованные фикстуры для всех тестов проекта Amanita
"""
import pytest
import logging
import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add bot/ to Python path for imports (fixes config import issue)
bot_dir = Path(__file__).parent.parent
if str(bot_dir) not in sys.path:
    sys.path.insert(0, str(bot_dir))

# Lazy import: blockchain imported only when needed to avoid config import issues
# from bot.services.core import blockchain
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
def product_formatter_service():
    """
    Fixture для ProductFormatterService без blockchain dependencies.
    
    Используется для unit tests форматирования продуктов.
    Избегает инициализации blockchain при импорте handlers.
    """
    import sys
    from unittest.mock import Mock, patch
    from pathlib import Path
    
    # Mock registry_singleton ПЕРЕД импортом
    mock_registry = Mock()
    
    with patch.dict('sys.modules', {'services.product.registry_singleton': Mock(product_registry_service=mock_registry)}):
        from handlers.common.formatting.product_formatter_service import ProductFormatterService
        from handlers.common.formatting.product_formatter_config import ProductFormatterConfig
        
        # Create с minimal config (no dependencies)
        config = ProductFormatterConfig()
        formatter = ProductFormatterService(config=config, localization_service=None)
        
        return formatter


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
            
            # Состояние для SpiralEngine
            self.spiral_engine_state = {
                "invite_codes": {},
                "user_activations": {},
                "user_roles": {},
                "circle_members": {},
                "violations": {}
            }
            
            # Состояние для OrganicComponentRegistry
            self.component_registry_state = {
                "components": {},
                "total_components": 0,
                "next_component_id": 1
            }
            
            # 🔧 ИЗОЛЯЦИЯ: Сбрасываем состояние при каждом создании фикстуры
            self._reset_state()
        
        def _reset_state(self):
            """Сброс состояния для изоляции тестов"""
            self.create_product_called = False
            self._next_blockchain_id = 1
            self.product_statuses.clear()
            self.product_cids.clear()
            
            # Сброс состояния SpiralEngine
            self.spiral_engine_state = {
                "invite_codes": {},
                "user_activations": {},
                "user_roles": {},
                "circle_members": {},
                "violations": {}
            }
            
            # 🔧 ИСПРАВЛЕНИЕ: Инициализируем тестовые данные с корректными статусами
            self._initialize_test_data()
            
            logger.info("🔧 [MockBlockchainService] Состояние сброшено для изоляции тестов")
        
        def _initialize_test_data(self):
            """Инициализация тестовых данных для изоляции тестов"""
            # Создаем тестовый продукт с ID=1 и статусом False (неактивный)
            self.product_statuses[1] = False
            self.product_cids[1] = "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
            
            # 🔧 ИСПРАВЛЕНИЕ: Создаем только статусы для ID 2-8, но НЕ создаем тестовые CID
            # Это позволит create_product создать правильные CID для динамически создаваемых продуктов
            for i in range(2, 9):  # ID от 2 до 8
                self.product_statuses[i] = False  # 🔧 ИСПРАВЛЕНИЕ: Все продукты неактивны по умолчанию
                # НЕ создаем тестовые CID - они будут созданы через create_product
            
            # 🆕 Инициализация тестовых данных для SpiralEngine
            self._initialize_spiral_engine_test_data()
            
            # 🆕 Инициализация тестовых данных для OrganicComponentRegistry
            self._initialize_component_test_data()
            
            logger.info(f"🔧 [MockBlockchainService] Инициализированы тестовые данные: {len(self.product_statuses)} продуктов")
            logger.info(f"   - product_statuses: {self.product_statuses}")
            logger.info(f"   - product_cids: {self.product_cids}")
            logger.info(f"   - spiral_engine_state: {self.spiral_engine_state}")
        
        def _initialize_spiral_engine_test_data(self):
            """Инициализация тестовых данных для SpiralEngine"""
            # Тестовые адреса
            test_seller_address = "0x1234567890abcdef1234567890abcdef12345678"
            test_user_address = "0x0987654321098765432109876543210987654321"
            test_activator_address = "0x1111111111111111111111111111111111111111"
            
            # Хеши ролей (соответствуют реальным хешам из SpiralEngine)
            seller_role_hash = "0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6"
            activator_role_hash = "0x65d7a28e3265b37a6474929f336521b332c1681b933f6cb9f3376673440d862a"
            
            # Инициализируем состояние SpiralEngine
            self.spiral_engine_state.update({
                # Тестовые инвайт-коды
                "invite_codes": {
                    "SPIRAL-TEST-CODE1": 1,
                    "SPIRAL-TEST-CODE2": 2,
                    "SPIRAL-EXIST-CODE": 3
                },
                
                # Активации пользователей
                "user_activations": {
                    test_user_address: 1,  # Пользователь активирован через инвайт с ID 1
                    "0x2222222222222222222222222222222222222222": 2  # Другой активированный пользователь
                },
                
                # Роли пользователей
                "user_roles": {
                    test_seller_address: {
                        seller_role_hash: True,
                        activator_role_hash: False
                    },
                    test_activator_address: {
                        seller_role_hash: False,
                        activator_role_hash: True
                    }
                },
                
                # Члены кругов (спиральная иерархия)
                "circle_members": {
                    test_activator_address: [
                        test_user_address,
                        "0x2222222222222222222222222222222222222222"
                    ],
                    test_user_address: []  # Пользователь пока не активировал никого
                },
                
                # Нарушения
                "violations": {
                    test_user_address: 0,
                    "0x2222222222222222222222222222222222222222": 1
                }
            })
            
            logger.info("🆕 [MockBlockchainService] Инициализированы тестовые данные SpiralEngine")
        
        def _initialize_component_test_data(self):
            """Инициализация тестовых данных для OrganicComponentRegistry"""
            self.component_registry_state = {
                "components": {
                    "amanita_muscaria": {
                        "id": 1,
                        "businessId": "amanita_muscaria",
                        "creator": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                        "rootMetadataCID": "ar://xyz123abc456def789",
                        "createdAt": 1730000000,
                        "lastUpdated": 1730000000,
                        "status": 0,
                        "isShared": True,
                    },
                    "blue_lotus": {
                        "id": 2,
                        "businessId": "blue_lotus",
                        "creator": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                        "rootMetadataCID": "ar://abc789xyz456def123",
                        "createdAt": 1730000100,
                        "lastUpdated": 1730000100,
                        "status": 0,
                        "isShared": True,
                    }
                },
                "total_components": 2,
                "next_component_id": 3
            }
            
            logger.info("🆕 [MockBlockchainService] Инициализированы тестовые данные OrganicComponentRegistry")
            logger.info(f"   - Компонентов: {len(self.component_registry_state['components'])}")
        
        def _generate_next_blockchain_id(self):
            """Генерирует следующий уникальный blockchain ID"""
            next_id = self._next_blockchain_id
            self._next_blockchain_id += 1
            logger.info(f"🔢 [MockBlockchainService] Сгенерирован новый blockchain ID: {next_id}")
            return next_id
        
        # Возвращает фиктивную версию каталога (например, 1)
        def get_catalog_version(self):
            return 1

        # ✅ ИСПРАВЛЕНО: Возвращает список продуктов с 6-элементной структурой (новая версия контракта)
        def get_all_products(self):
            """
            Возвращает список продуктов (структура ProductRegistry.Product - 6 элементов)
            Структура: (id, seller, businessId, componentIds, metadataCID, active)
            ✅ ИСПРАВЛЕНО: Используем адрес текущего селлера для прохождения фильтрации по seller
            """
            # ✅ ИСПРАВЛЕНО: Используем адрес текущего селлера (как в get_product) для прохождения фильтрации
            seller_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
            return [
                (1, seller_address, "amanita1", ["amanita_muscaria"], "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG", False),
                (2, seller_address, "blue_lotus_tincture", ["blue_lotus"], "QmbTBHeByJwUP9JyTo2GcHzj1YwzVww6zXrEDFt3zgdwQ1", False),
                (3, seller_address, "product_3", ["amanita_muscaria"], "QmUPHsHyuDHKyVbduvqoooAYShFCSfYgcnEioxNNqgZK2B", False),
                (4, seller_address, "product_4", ["blue_lotus"], "Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz", False),
                (5, seller_address, "product_5", ["amanita_muscaria"], "Qmbkp4owyjyjRuYGd7b1KfVjo5bBvCutgYdCi7qKd3ZPoy", False),
                (6, seller_address, "product_6", ["blue_lotus"], "QmWwjNvD8HX6WB2TLsxiEhciMJCHRfiZBw9G2wgfqKyPbd", False),
                (7, seller_address, "product_7", ["amanita_muscaria"], "QmbGrAqeugUxZZxWojavu4rbHdk5XNmSsSv92UV8FKjyHa", False),
                (8, seller_address, "product_8", ["blue_lotus"], "QmdmJFdMQXRpp3qNRTLYqsR1kFLYhTSRA8YMfd5JvNi85S", False)
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
            """Получает продукт по ID (mock)"""
            # Приводим product_id к int для корректного поиска
            try:
                product_id_int = int(product_id)
            except (ValueError, TypeError):
                logger.warning(f"⚠️ [MockBlockchainService] Невалидный product_id: {product_id}")
                return None
            
            # Получаем статус продукта
            status = self.product_statuses.get(product_id_int, False)
            logger.info(f"🔍 [MockBlockchainService] get_product вызван для ID={product_id}")
            logger.info(f"   - product_statuses: {self.product_statuses}")
            logger.info(f"   - status для ID {product_id_int}: {status}")
            
            # ✅ ИСПРАВЛЕНО: Возвращаем 6-элементный tuple (новая структура контракта)
            # Структура: (id, seller, businessId, componentIds, metadataCID, active)
            
            # Проверяем, существует ли продукт с таким ID
            if product_id_int in self.product_cids:
                # Продукт был создан через create_product, возвращаем сохраненный CID
                cid = self.product_cids[product_id_int]
                # Получаем business_id и componentIds из хранилища продуктов (если доступно)
                business_id = f"product_{product_id_int}"  # Дефолтное значение
                component_ids = ["amanita_muscaria"]  # Дефолтное значение
                
                # Если есть доступ к storage_service, пытаемся получить реальные данные
                if hasattr(self, 'storage_service') and self.storage_service and cid:
                    try:
                        metadata = self.storage_service.download_json(cid)
                        if metadata and isinstance(metadata, dict):
                            business_id = metadata.get('business_id', business_id)
                            # componentIds обычно берется из метаданных или используется дефолт
                            if 'organic_components' in metadata:
                                component_ids = [comp.get('component_id', 'amanita_muscaria') for comp in metadata.get('organic_components', [])]
                                if not component_ids:
                                    component_ids = ["amanita_muscaria"]
                    except Exception as e:
                        logger.warning(f"⚠️ [MockBlockchainService] Не удалось получить metadata для CID {cid}: {e}")
                
                logger.info(f"🔍 [MockBlockchainService] Получен продукт: ID={product_id_int}, businessId={business_id}, CID={cid}, Status={status}")
                return (product_id_int, "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", business_id, component_ids, cid, status)
            else:
                # Если продукт не найден в product_cids, возвращаем None для CID
                logger.info(f"🔍 [MockBlockchainService] Продукт {product_id_int} не найден в product_cids, но статус: {status}")
                return (product_id_int, "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", f"product_{product_id_int}", [], None, status)

        # Имитация создания продукта в блокчейне. Сохраняет CID для синхронизации с MockIPFSStorage.
        async def create_product(self, ipfs_cid):
            self.create_product_called = True
            
            # Генерируем уникальный blockchain ID для продукта (в реальной системе это делает блокчейн)
            product_id = self._generate_next_blockchain_id()
            
            # Сохраняем связь между blockchain ID и IPFS CID
            self.product_cids[product_id] = ipfs_cid
            
            # 🔧 ИСПРАВЛЕНИЕ: Продукты создаются неактивными по умолчанию (status=False)
            self.product_statuses[product_id] = False
            
            logger.info(f"🔗 [MockBlockchainService] Создан продукт: ID={product_id}, CID={ipfs_cid}")
            
            return "0x123"  # Хэш транзакции

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
        
        # 🔧 НОВОЕ: Поддержка InviteNFT методов для AccountService
        def _call_contract_read_function(self, contract_name, function_name, default_value, *args):
            """Универсальный метод для вызова read функций контрактов"""
            logger.info(f"🔍 [MockBlockchainService] _call_contract_read_function: {function_name} с аргументами {args}")
            
            # Поддержка SpiralEngine функций
            if contract_name == "SpiralEngine":
                return self._call_spiral_engine_function(function_name, default_value, *args)
            
            # Поддержка OrganicComponentRegistry функций
            elif contract_name == "OrganicComponentRegistry":
                return self._call_component_registry_function(function_name, default_value, *args)
            
            # Определяем тип контракта по функции (старая логика для обратной совместимости)
            if function_name in ["isSeller", "userInviteCount", "isUserActivated", "getAllActivatedUsers", 
                               "batchValidateInviteCodes", "getTokenIdByInviteCode", "getInviteCodeByTokenId",
                               "isInviteTokenUsed", "getInviteCreatedAt", "getInviteExpiry", 
                               "getInviteMinter", "getInviteFirstOwner", "validateInviteCode"]:
                return self._call_invite_nft_function(function_name, *args)
            else:
                # Для других функций возвращаем default_value
                logger.warning(f"⚠️ [MockBlockchainService] Функция {function_name} не поддерживается")
                return default_value
        
        def _call_invite_nft_function(self, function_name, *args):
            """Вызов функций InviteNFT контракта"""
            logger.info(f"🔍 [MockBlockchainService] InviteNFT функция: {function_name} с аргументами {args}")
            
            if function_name == "isSeller":
                user_address = args[0] if args else "0x0000000000000000000000000000000000000000"
                return self._is_seller(user_address)
            elif function_name == "userInviteCount":
                user_address = args[0] if args else "0x0000000000000000000000000000000000000000"
                return self._user_invite_count(user_address)
            elif function_name == "isUserActivated":
                user_address = args[0] if args else "0x0000000000000000000000000000000000000000"
                return self._is_user_activated(user_address)
            elif function_name == "getTokenIdByInviteCode":
                invite_code = args[0] if args else ""
                return self._get_token_id_by_invite_code(invite_code)
            elif function_name == "getInviteCodeByTokenId":
                token_id = args[0] if args else 0
                return self._get_invite_code_by_token_id(token_id)
            elif function_name == "isInviteTokenUsed":
                token_id = args[0] if args else 0
                return self._is_invite_token_used(token_id)
            elif function_name == "getInviteCreatedAt":
                token_id = args[0] if args else 0
                return self._get_invite_created_at(token_id)
            elif function_name == "getInviteExpiry":
                token_id = args[0] if args else 0
                return self._get_invite_expiry(token_id)
            elif function_name == "getInviteMinter":
                token_id = args[0] if args else 0
                return self._get_invite_minter(token_id)
            elif function_name == "getInviteFirstOwner":
                token_id = args[0] if args else 0
                return self._get_invite_first_owner(token_id)
            elif function_name == "validateInviteCode":
                invite_code = args[0] if args else ""
                return self._validate_invite_code(invite_code)
            else:
                logger.warning(f"⚠️ [MockBlockchainService] Неизвестная InviteNFT функция: {function_name}")
                return None
        
        def _is_seller(self, user_address):
            """Проверка роли продавца"""
            return self._get_invite_nft_test_data()["seller_roles"].get(user_address, False)
        
        def _user_invite_count(self, user_address):
            """Количество инвайтов пользователя"""
            return self._get_invite_nft_test_data()["user_invite_counts"].get(user_address, 0)
        
        def _is_user_activated(self, user_address):
            """Проверка активации пользователя"""
            return self._get_invite_nft_test_data()["activated_users"].get(user_address, 0) != 0
        
        
        def _get_token_id_by_invite_code(self, invite_code):
            """Получение token ID по инвайт коду"""
            invite_data = self._get_invite_nft_test_data()["invite_codes"]
            if invite_code in invite_data:
                return invite_data[invite_code]["token_id"]
            return 0
        
        def _get_invite_code_by_token_id(self, token_id):
            """Получение инвайт кода по token ID"""
            invite_data = self._get_invite_nft_test_data()["invite_codes"]
            for code, data in invite_data.items():
                if data["token_id"] == token_id:
                    return code
            return ""
        
        def _is_invite_token_used(self, token_id):
            """Проверка использования инвайт токена"""
            invite_data = self._get_invite_nft_test_data()["invite_codes"]
            for data in invite_data.values():
                if data["token_id"] == token_id:
                    return data["used"]
            return False
        
        def _get_invite_created_at(self, token_id):
            """Получение времени создания инвайта"""
            return int(time.time()) - 3600  # 1 час назад
        
        def _get_invite_expiry(self, token_id):
            """Получение времени истечения инвайта"""
            invite_data = self._get_invite_nft_test_data()["invite_codes"]
            for data in invite_data.values():
                if data["token_id"] == token_id:
                    return data["expiry"]
            return 0
        
        def _get_invite_minter(self, token_id):
            """Получение адреса минтера инвайта"""
            return "0x1234567890abcdef1234567890abcdef12345678"
        
        def _get_invite_first_owner(self, token_id):
            """Получение адреса первого владельца инвайта"""
            return "0x1234567890abcdef1234567890abcdef12345678"
        
        def _validate_invite_code(self, invite_code):
            """Валидация инвайт кода"""
            invite_data = self._get_invite_nft_test_data()["invite_codes"]
            if invite_code in invite_data:
                invite_info = invite_data[invite_code]
                if invite_info["used"]:
                    return False, "already_used"
                elif invite_info["expiry"] != 0 and invite_info["expiry"] < time.time():
                    return False, "expired"
                else:
                    return True, ""
            else:
                return False, "not_found"
        
        def _get_invite_nft_test_data(self):
            """Получение тестовых данных для InviteNFT"""
            if not hasattr(self, '_invite_nft_data'):
                import time
                self._invite_nft_data = {
                    "invite_codes": {
                        "AMANITA-TEST-CODE1": {"token_id": 1, "used": False, "expiry": 0},
                        "AMANITA-TEST-CODE2": {"token_id": 2, "used": True, "expiry": 0},
                        "AMANITA-TEST-CODE3": {"token_id": 3, "used": False, "expiry": 0},
                        "AMANITA-TEST-CODE4": {"token_id": 4, "used": False, "expiry": 0},
                        "AMANITA-TEST-CODE5": {"token_id": 5, "used": False, "expiry": 0}
                    },
                    "user_invite_counts": {
                        "0x1234567890abcdef1234567890abcdef12345678": 2,
                        "0x0987654321098765432109876543210987654321": 0,
                        "0x1111111111111111111111111111111111111111": 5,
                        "0x2222222222222222222222222222222222222222": 1
                    },
                    "activated_users": {
                        "0x1234567890abcdef1234567890abcdef12345678": 1,
                        "0x0987654321098765432109876543210987654321": 0,
                        "0x1111111111111111111111111111111111111111": 1,
                        "0x2222222222222222222222222222222222222222": 0
                    },
                    "seller_roles": {
                        "0x1234567890abcdef1234567890abcdef12345678": True,
                        "0x0987654321098765432109876543210987654321": False,
                        "0x1111111111111111111111111111111111111111": True,
                        "0x2222222222222222222222222222222222222222": False
                    }
                }
            return self._invite_nft_data
        
        def _call_spiral_engine_function(self, function_name, default_value, *args):
            """Вызов функций SpiralEngine в моке"""
            logger.info(f"🔍 [MockBlockchainService] SpiralEngine функция: {function_name} с аргументами {args}")
            
            if function_name == "inviteCodeExists":
                invite_code = args[0] if args else ""
                return invite_code in self.spiral_engine_state["invite_codes"]
            
            elif function_name == "inviteCodeToTokenId":
                invite_code = args[0] if args else ""
                return self.spiral_engine_state["invite_codes"].get(invite_code, 0)
            
            elif function_name == "isInviteUsed":
                token_id = args[0] if args else 0
                return token_id in [v for v in self.spiral_engine_state["user_activations"].values()]
            
            elif function_name == "usedInviteByUser":
                user_address = args[0] if args else ""
                return self.spiral_engine_state["user_activations"].get(user_address, 0)
            
            elif function_name == "hasRole":
                role_hash = args[0] if len(args) > 0 else ""
                user_address = args[1] if len(args) > 1 else ""
                return self.spiral_engine_state["user_roles"].get(user_address, {}).get(role_hash, False)
            
            elif function_name == "getCircleSize":
                activator_address = args[0] if args else ""
                return len(self.spiral_engine_state["circle_members"].get(activator_address, []))
            
            elif function_name == "getCircleMembers":
                activator_address = args[0] if args else ""
                return self.spiral_engine_state["circle_members"].get(activator_address, [])
            
            elif function_name == "userInvites":
                user_address = args[0] if args else ""
                return self.spiral_engine_state["circle_members"].get(user_address, [])
            
            elif function_name == "violationCount":
                user_address = args[0] if args else ""
                return self.spiral_engine_state["violations"].get(user_address, 0)
            
            # Fallback
            return default_value
        
        def _call_component_registry_function(self, function_name, default_value, *args):
            """
            Вызов функций OrganicComponentRegistry в моке
            
            Supported methods:
            - componentExists(businessId) → bool
            - getComponentByBusinessId(businessId) → Component struct (tuple)
            - totalComponents() → uint256
            - componentBusinessIds(id) → string
            - getComponentRootMetadata(businessId) → string
            """
            logger.info(f"🔍 [MockBlockchainService] OrganicComponentRegistry функция: {function_name} с аргументами {args}")
            
            # componentExists(businessId)
            if function_name == "componentExists":
                business_id = args[0] if args else ""
                exists = business_id in self.component_registry_state["components"]
                logger.info(f"   - componentExists('{business_id}') = {exists}")
                return exists
            
            # getComponentByBusinessId(businessId)
            elif function_name == "getComponentByBusinessId":
                business_id = args[0] if args else ""
                component = self.component_registry_state["components"].get(business_id)
                
                if component:
                    # Return tuple matching Solidity struct signature:
                    # (id, creator, createdAt, lastUpdated, status, isShared)
                    result = (
                        component["id"],
                        component["creator"],
                        component.get("createdAt"),
                        component.get("lastUpdated", component.get("createdAt")),
                        component.get("status", 0),
                        component.get("isShared", True),
                    )
                    logger.info(
                        "   - getComponentByBusinessId('%s') = Component(id=%s)",
                        business_id,
                        component["id"],
                    )
                    return result
                else:
                    logger.info(f"   - getComponentByBusinessId('{business_id}') = None (not found)")
                    return None
            
            # totalComponents()
            elif function_name == "totalComponents":
                total = self.component_registry_state["total_components"]
                logger.info(f"   - totalComponents() = {total}")
                return total
            
            # componentBusinessIds(id)
            elif function_name == "componentBusinessIds":
                component_id = args[0] if args else 0
                
                # Find component by blockchain ID
                for comp in self.component_registry_state["components"].values():
                    if comp["id"] == component_id:
                        business_id = comp["businessId"]
                        logger.info(f"   - componentBusinessIds({component_id}) = '{business_id}'")
                        return business_id
                
                logger.info(f"   - componentBusinessIds({component_id}) = '' (not found)")
                return ""
            
            elif function_name == "getComponentRootMetadata":
                business_id = args[0] if args else ""
                component = self.component_registry_state["components"].get(business_id)
                if component:
                    cid = component.get("rootMetadataCID")
                    logger.info(
                        "   - getComponentRootMetadata('%s') = %s",
                        business_id,
                        cid,
                    )
                    return cid
                logger.info(f"   - getComponentRootMetadata('{business_id}') = None (not found)")
                return None
            
            # Unknown method
            else:
                logger.warning(f"⚠️ [MockBlockchainService] Неизвестная OrganicComponentRegistry функция: {function_name}")
                return default_value
        
        def get_contract(self, contract_name):
            """Получение контракта для тестирования"""
            if contract_name == "SpiralEngine":
                # Возвращаем мок контракта с методами ролей
                class MockSpiralEngineContract:
                    class functions:
                        @staticmethod
                        def SELLER_ROLE():
                            class MockRole:
                                def call(self):
                                    return "0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6"  # SELLER_ROLE hash
                            return MockRole()
                        
                        @staticmethod
                        def ACTIVATOR_ROLE():
                            class MockRole:
                                def call(self):
                                    return "0x65d7a28e3265b37a6474929f336521b332c1681b933f6cb9f3376673440d862a"  # ACTIVATOR_ROLE hash
                            return MockRole()
                
                return MockSpiralEngineContract()
            
            return None
        
        # 🆕 Методы для AccountService тестов
        async def activate_invite(self, invite_code, user_address, new_invite_codes, expiry, private_key):
            """Мок активации инвайта через SpiralEngine"""
            logger.info(f"🔍 [MockBlockchainService] activate_invite: {invite_code} -> {user_address}")
            
            if invite_code not in self.spiral_engine_state["invite_codes"]:
                return {"success": False, "reason": "Invite code not found"}
            
            if user_address in self.spiral_engine_state["user_activations"]:
                return {"success": False, "reason": "User already activated"}
            
            # Активируем пользователя
            token_id = self.spiral_engine_state["invite_codes"][invite_code]
            self.spiral_engine_state["user_activations"][user_address] = token_id
            
            # Добавляем новые инвайт-коды
            next_token_id = max(self.spiral_engine_state["invite_codes"].values()) + 1
            for code in new_invite_codes:
                self.spiral_engine_state["invite_codes"][code] = next_token_id
                next_token_id += 1
            
            return {"success": True, "tx_hash": "0xmocked_tx_hash"}
        
        def is_user_activated(self, user_address):
            """Мок проверки активации пользователя"""
            return self.spiral_engine_state["user_activations"].get(user_address, 0) > 0
        
        def validate_invite_code(self, invite_code):
            """Мок валидации инвайт-кода"""
            if invite_code not in self.spiral_engine_state["invite_codes"]:
                return {"success": False, "message": "Invite code not found"}
            
            token_id = self.spiral_engine_state["invite_codes"][invite_code]
            is_used = token_id in self.spiral_engine_state["user_activations"].values()
            
            if is_used:
                return {"success": False, "message": "Invite code already used"}
            
            return {"success": True, "token_id": token_id, "invite_code": invite_code}
        
        # ==========================================
        # OrganicComponentRegistry Methods
        # ==========================================
        
        def component_exists(self, component_id: str) -> bool:
            """Проверяет существование компонента по business ID"""
            return self._call_contract_read_function(
                "OrganicComponentRegistry",
                "componentExists",
                False,
                component_id
            )
        
        def get_component(self, component_id: str):
            """Получает компонент по business ID"""
            return self._call_contract_read_function(
                "OrganicComponentRegistry",
                "getComponentByBusinessId",
                None,
                component_id,
            )

        def get_component_root_metadata(self, component_id: str):
            """Возвращает rootMetadataCID компонента из маппинга."""
            return self._call_contract_read_function(
                "OrganicComponentRegistry",
                "getComponentRootMetadata",
                None,
                component_id,
            )

        def get_component_root_metadata_cid(self, component_id: str):
            """Совместимость со старыми тестами: alias для get_component_root_metadata."""
            return self.get_component_root_metadata(component_id)

        def get_component_business_id(self, blockchain_id: int):
            """Возвращает businessId по числовому ID."""
            return self._call_contract_read_function(
                "OrganicComponentRegistry",
                "componentBusinessIds",
                None,
                blockchain_id,
            )
        
        def get_all_components(self):
            """Получает все компоненты из реестра"""
            try:
                total = self._call_contract_read_function(
                    "OrganicComponentRegistry",
                    "totalComponents",
                    0
                )
                
                components = []
                for i in range(1, total + 1):
                    business_id = self._call_contract_read_function(
                        "OrganicComponentRegistry",
                        "componentBusinessIds",
                        None,
                        i
                    )
                    
                    if business_id:
                        component = self.get_component(business_id)
                        if component:
                            components.append(component)
                
                return components
            except Exception:
                return []
    
    # Подменяем BlockchainService на мок
    from bot.services.core import blockchain  # Lazy import
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainService)
    return MockBlockchainService()


@pytest.fixture(scope="function")
def mock_storage_service():
    """Мок для ProductStorageService для unit-тестов ComponentService"""
    
    class MockStorageService:
        """Mock storage service для тестирования ComponentService"""
        
        def __init__(self):
            # Mock Arweave metadata для компонентов
            # CIDs must match those in MockBlockchainService._initialize_component_test_data()
            self.mock_metadata = {
                "xyz123abc456def789": {  # amanita_muscaria CID (matches MockBlockchainService)
                    "component_id": "amanita_muscaria",
                    "scientific_title": "Amanita muscaria",
                    "forms": ["dried"],
                    "features": {
                        "common": ["stress_relief", "vitality_boost"],
                        "forms": {
                            "dried": ["long_term_effect", "easy_storage"]
                        }
                    },
                    "localizations": {
                        "simple_fields": {
                            "title": {"cid": "Qm123"}
                        },
                        "complex_fields": {
                            "ru": {"cid": "Qm456", "size": 3902},
                            "en": {"cid": "Qm789", "size": 246}
                        }
                    }
                },
                "abc789xyz456def123": {  # blue_lotus CID (matches MockBlockchainService)
                    "component_id": "blue_lotus",
                    "scientific_title": "Nymphaea caerulea",
                    "forms": ["flower", "tincture"],
                    "features": {
                        "common": ["relaxation", "consciousness_expansion"]
                    },
                    "localizations": {}
                },
                # Nested description CIDs (for get_component_description tests)
                "Qm456": {  # Russian description for amanita_muscaria
                    "generic_description": "🔬 Активные компоненты: мусцимол, иботеновая кислота",
                    "effects": "🌿 Целительное действие: снижение стресса, повышение витальности",
                    "shamanic": "🌀 Шаманская перспектива: расширение сознания, духовное путешествие",
                    "warnings": "⚠️ Предостережения: не рекомендуется при беременности"
                },
                "Qm789": {  # English description for amanita_muscaria
                    "generic_description": "🔬 Active compounds: muscimol, ibotenic acid",
                    "effects": "🌿 Healing action: stress reduction, vitality boost",
                    "shamanic": "🌀 Shamanic perspective: consciousness expansion, spiritual journey",
                    "warnings": "⚠️ Warnings: not recommended during pregnancy"
                }
            }
        
        def download_json(self, cid: str):
            """Mock download_json method"""
            clean_cid = cid.replace("ar://", "")
            return self.mock_metadata.get(clean_cid)
    
    return MockStorageService()


@pytest.fixture(scope="function")
def mock_validation_service():
    """Универсальный мок для ProductValidationService с ValidationResult"""
    from bot.validation import ValidationResult
    
    class MockProductValidationService:
        def __init__(self, should_fail_validation=False):
            self.should_fail_validation = should_fail_validation
            self.validation_calls = []
        
        async def validate_product_data(self, product_data, storage_service=None):
            self.validation_calls.append(product_data)
            
            if self.should_fail_validation:
                return ValidationResult.failure(
                    "Mock validation failed",
                    field_name="mock_error",
                    error_code="MOCK_VALIDATION_FAILED"
                )
            
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
                            required_component_fields = ["component_id", "description_cid", "proportion"]
                            for comp_field in required_component_fields:
                                if comp_field not in component:
                                    errors.append(f"organic_components[{i}].{comp_field}: Поле обязательно")
            
            if errors:
                return ValidationResult.failure(
                    "; ".join(errors),
                    field_name="validation_errors",
                    error_code="VALIDATION_ERRORS"
                )
            
            return ValidationResult.success()
    
    return MockProductValidationService()


@pytest.fixture(scope="function")
def mock_localization_service():
    """
    Фикстура для создания мока LocalizationService.
    
    Используется в unit тестах для изоляции от реальных зависимостей.
    Следует паттерну существующих фикстур (mock_blockchain_service, mock_storage_service).
    
    Returns:
        MagicMock: Мок LocalizationService с базовой функциональностью для тестов.
    """
    from unittest.mock import MagicMock
    from bot.services.common.localization_service import LocalizationService
    
    mock_service = MagicMock(spec=LocalizationService)
    
    # Базовые методы для локализации
    mock_service.t = MagicMock(return_value="Mock Translation")
    mock_service.get_translation = MagicMock(return_value="Mock Translation")
    mock_service.get = MagicMock(return_value="Mock Value")
    mock_service.get_localized_text = MagicMock(return_value="Mock Localized Text")
    
    # Методы для работы с языками
    mock_service.lang = "ru"
    mock_service.get_language = MagicMock(return_value="ru")
    mock_service.set_language = MagicMock()
    mock_service.switch_language = MagicMock()
    
    # Атрибуты для дочерних сервисов (используются в LocalizationService)
    mock_service.product_localization = MagicMock()
    mock_service.component_localization = MagicMock()
    
    return mock_service


@pytest.fixture(scope="function")
def mock_service_factory(mock_blockchain_service):
    """
    Фикстура для создания мока ServiceFactory.
    
    Использует существующую фикстуру mock_blockchain_service для изоляции.
    Следует паттерну существующих фикстур (mock_blockchain_service, mock_storage_service).
    
    Args:
        mock_blockchain_service: Существующая фикстура для мока BlockchainService
    
    Returns:
        MockServiceFactory: Мок ServiceFactory с использованием mock_blockchain_service
    
    Note:
        Эта фикстура опциональна. Альтернативный подход - мокировать
        dependencies.get_localization_service() напрямую в тестах.
    """
    from unittest.mock import MagicMock
    from bot.services.common.localization_service import LocalizationService
    from bot.services.common.multilingual_ipfs_service import MultilingualIPFSService
    from bot.services.common.translation_cache_service import TranslationCacheService
    from bot.services.common.fallback_localization_service import FallbackLocalizationService
    from bot.services.core.ipfs_factory import IPFSFactory
    
    class MockServiceFactory:
        """
        Мок ServiceFactory для unit тестов.
        
        Использует mock_blockchain_service вместо реального BlockchainService.
        """
        
        def __init__(self, blockchain_service):
            """Инициализация с моком BlockchainService"""
            self.blockchain = blockchain_service
        
        def create_localization_service(self, lang: str = 'ru'):
            """
            Создает LocalizationService с моками вместо реальных зависимостей.
            
            Args:
                lang: Язык локализации (по умолчанию 'ru')
            
            Returns:
                MagicMock: Мок LocalizationService с базовой функциональностью
            """
            # Создаем моки для зависимостей
            cache_service = MagicMock(spec=TranslationCacheService)
            fallback_service = MagicMock(spec=FallbackLocalizationService)
            ipfs_factory = MagicMock(spec=IPFSFactory)
            
            # Создаем мок MultilingualIPFSService
            ipfs_service = MagicMock(spec=MultilingualIPFSService)
            ipfs_service.blockchain_service = self.blockchain
            
            # Создаем мок LocalizationService (используем mock_localization_service паттерн)
            localization_service = MagicMock(spec=LocalizationService)
            localization_service.lang = lang
            localization_service.t = MagicMock(return_value="Mock Translation")
            localization_service.get_translation = MagicMock(return_value="Mock Translation")
            localization_service.get = MagicMock(return_value="Mock Value")
            localization_service.get_localized_text = MagicMock(return_value="Mock Localized Text")
            localization_service.get_language = MagicMock(return_value=lang)
            localization_service.set_language = MagicMock()
            localization_service.switch_language = MagicMock()
            localization_service.cache_service = cache_service
            localization_service.fallback_service = fallback_service
            localization_service.ipfs_service = ipfs_service
            localization_service.product_localization = MagicMock()
            localization_service.component_localization = MagicMock()
            
            return localization_service
    
    return MockServiceFactory(mock_blockchain_service)


@pytest.fixture(scope="function")
def mock_account_service():
    """Универсальный мок для AccountService с полной функциональностью для InviteNFT"""
    class MockAccountService:
        def __init__(self):
            self.private_key = "0x1234567890abcdef"
            self.address = "0x1234567890abcdef1234567890abcdef12345678"
            self.balance = "1000000000000000000"  # 1 ETH
            
            # 🔧 НОВОЕ: Тестовые данные для AccountService
            self._initialize_test_data()
        
        def _initialize_test_data(self):
            """Инициализация тестовых данных для AccountService"""
            self.test_sellers = {
                "0x1234567890abcdef1234567890abcdef12345678": True,
                "0x0987654321098765432109876543210987654321": False,
                "0x1111111111111111111111111111111111111111": True,
                "0x2222222222222222222222222222222222222222": False
            }
            
            self.test_user_invite_counts = {
                "0x1234567890abcdef1234567890abcdef12345678": 2,
                "0x0987654321098765432109876543210987654321": 0,
                "0x1111111111111111111111111111111111111111": 5,
                "0x2222222222222222222222222222222222222222": 1
            }
            
            self.test_activated_users = {
                "0x1234567890abcdef1234567890abcdef12345678": True,
                "0x0987654321098765432109876543210987654321": False,
                "0x1111111111111111111111111111111111111111": True,
                "0x2222222222222222222222222222222222222222": False
            }
            
            self.test_invite_codes = {
                "AMANITA-TEST-CODE1": {"valid": True, "used": False},
                "AMANITA-TEST-CODE2": {"valid": True, "used": True},
                "AMANITA-TEST-CODE3": {"valid": True, "used": False},
                "AMANITA-TEST-CODE4": {"valid": False, "used": False},
                "AMANITA-TEST-CODE5": {"valid": True, "used": False}
            }
        
        def get_private_key(self):
            return self.private_key
        
        def get_address(self):
            return self.address
        
        def get_balance(self):
            return self.balance
        
        async def sign_transaction(self, transaction):
            return f"0xsigned_{transaction}"
        
        # 🔧 НОВОЕ: Методы для InviteNFT функциональности
        async def is_seller(self, user_address: str) -> bool:
            """Проверка роли продавца"""
            return self.test_sellers.get(user_address, False)
        
        async def validate_invite_code(self, invite_code: str, user_address: str) -> bool:
            """Валидация инвайт кода для пользователя"""
            if invite_code not in self.test_invite_codes:
                return False
            
            invite_data = self.test_invite_codes[invite_code]
            if not invite_data["valid"] or invite_data["used"]:
                return False
            
            # Проверяем, что у пользователя есть доступ к инвайту
            user_count = self.test_user_invite_counts.get(user_address, 0)
            return user_count > 0
        
        async def is_user_activated(self, user_address: str) -> bool:
            """Проверка активации пользователя"""
            return self.test_activated_users.get(user_address, False)
        
        
        async def activate_and_mint_invites(self, invite_codes: list, user_address: str) -> bool:
            """Активация и минт инвайтов"""
            # Проверяем, что пользователь является продавцом
            if not await self.is_seller(user_address):
                return False
            
            # Проверяем все инвайт коды
            for code in invite_codes:
                if not await self.validate_invite_code(code, user_address):
                    return False
            
            # Симулируем успешную активацию
            return True
        
        async def get_seller_account(self) -> dict:
            """Получение аккаунта продавца"""
            return {
                "address": self.address,
                "private_key": self.private_key,
                "is_seller": True,
                "balance": self.balance
            }
        
        def _generate_random_code(self) -> str:
            """Генерация случайного кода (внутренний метод)"""
            import random
            import string
            return "AMANITA-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
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
                        "component_id": "amanita_muscaria",
                        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        "proportion": "100%"
                    }
                ],
                "cover_image_url": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
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
    from bot.validation import ValidationResult
    
    class MockProductValidationServiceFailing:
        def __init__(self):
            self.validation_calls = []
        
        async def validate_product_data(self, product_data, storage_service=None):
            self.validation_calls.append(product_data)
            return ValidationResult.failure(
                "Mock validation failed",
                field_name="mock_error",
                error_code="MOCK_VALIDATION_FAILED"
            )
    
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
                        "component_id": "amanita_muscaria",
                        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        "proportion": "100%"
                    }
                ],
                "cover_image_url": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
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
def api_client() -> httpx.AsyncClient:
    """Фикстура для HTTP клиента с HMAC аутентификацией"""
    print("🔧 [API Client] Создание HTTP клиента для теста")
    
    # Создаем HTTP клиент
    client = httpx.AsyncClient(base_url=API_URL)
    # Базовые заголовки
    client.headers.update({
        "Content-Type": "application/json"
    })
    
    return client


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
    """Универсальный мок для IPFS/Arweave storage сервиса"""
    
    class MockIPFSStorage:
        def __init__(self, should_fail_upload=False, should_fail_download=False):
            self.should_fail_upload = should_fail_upload
            self.should_fail_download = should_fail_download
            self.uploaded_jsons = []
            self.downloaded_json = {}
            self._storage = {}
            self._counter = 0
            
            # Загружаем тестовые данные при инициализации
            self._populate_test_data()
        
        # 🔧 ИСПРАВЛЕНИЕ: Добавляю синхронизацию с MockBlockchainService
        def sync_with_blockchain_service(self, blockchain_service):
            """Синхронизирует MockIPFSStorage с MockBlockchainService"""
            if hasattr(blockchain_service, 'product_cids'):
                for blockchain_id, cid in blockchain_service.product_cids.items():
                    if cid not in self._storage:
                        # 🔧 ИСПРАВЛЕНИЕ: Ищем оригинальные данные продукта по business_id
                        # Нужно найти продукт, который был создан с этим blockchain_id
                        original_data = None
                        
                        # Ищем по всем сохраненным данным
                        for stored_cid, stored_data in self._storage.items():
                            # Проверяем, есть ли у нас данные с business_id, который соответствует этому blockchain_id
                            # В тестах мы создаем продукт с business_id='amanita1', а blockchain_id=8
                            # Нужно найти данные, которые были созданы для этого продукта
                            if 'created_at' in stored_data:  # Это недавно созданный продукт
                                original_data = stored_data.copy()
                                break
                        
                        if original_data:
                            # Используем оригинальные данные, но обновляем CID и blockchain_id
                            original_data['cid'] = cid
                            original_data['blockchain_id'] = blockchain_id
                            self._storage[cid] = original_data
                            logger.info(f"🔧 [MockIPFSStorage] Синхронизирован CID {cid} с оригинальными данными для blockchain ID {blockchain_id}")
                        else:
                            # Создаем тестовые данные для CID, если оригинальных нет
                            test_data = {
                                "id": blockchain_id,
                                "cid": cid,
                                "title": f"Test Product {blockchain_id}",
                                "organic_components": [
                                    {
                                        "component_id": f"test_component_{blockchain_id}",
                                        "description_cid": cid,
                                        "proportion": "100%"
                                    }
                                ],
                                "cover_image_url": cid,
                                "categories": ["mushroom"],
                                "forms": ["powder"],
                                "species": "Test Species",
                                "prices": [{"weight": "100", "weight_unit": "g", "price": "10", "currency": "EUR"}]
                            }
                            self._storage[cid] = test_data
                            logger.info(f"🔧 [MockIPFSStorage] Синхронизирован CID {cid} с тестовыми данными для blockchain ID {blockchain_id}")
        
        def _reset_state(self):
            """Сброс состояния для изоляции тестов"""
            self.uploaded_jsons.clear()
            self.downloaded_json.clear()
            
            # После сброса состояния заново загружаем тестовые данные
            self._populate_test_data()
            
            logger.info("🔧 [MockIPFSStorage] Состояние сброшено для изоляции тестов")
        
        def _populate_test_data(self):
            """Предзаполняет хранилище тестовыми данными для продуктов"""
            # Тестовые данные для продуктов, которые возвращает mock blockchain service (8 продуктов)
            test_products = {
                "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG": {
                    "business_id": "amanita1",
                    "blockchain_id": 1,
                    "cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    "title": "Amanita muscaria — sliced caps and gills (1st grade)",
                    "organic_components": [
                        {
                            "component_id": "amanita_muscaria",
                            "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                    "categories": ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
                    "forms": ["mixed slices"],
                    "species": "Amanita muscaria",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
                },
                "QmbTBHeByJwUP9JyTo2GcHzj1YwzVww6zXrEDFt3zgdwQ1": {
                    "business_id": "amanita2",
                    "blockchain_id": 2,
                    "cid": "QmbTBHeByJwUP9JyTo2GcHzj1YwzVww6zXrEDFt3zgdwQ1",
                    "title": "Amanita pantherina — premium powder",
                    "organic_components": [
                        {
                            "component_id": "amanita_pantherina",
                            "description_cid": "QmbTBHeByJwUP9JyTo2GcHzj1YwzVww6zXrEDFt3zgdwQ1",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmPantherinaCoverCID",
                    "categories": ["mushroom", "mental health", "focus"],
                    "forms": ["powder"],
                    "species": "Amanita pantherina",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "90", "currency": "EUR"}]
                },
                "QmUPHsHyuDHKyVbduvqoooAYShFCSfYgcnEioxNNqgZK2B": {
                    "business_id": "blue_lotus1",
                    "blockchain_id": 3,
                    "cid": "QmUPHsHyuDHKyVbduvqoooAYShFCSfYgcnEioxNNqgZK2B",
                    "title": "Blue Lotus — flower extract",
                    "organic_components": [
                        {
                            "component_id": "blue_lotus",
                            "description_cid": "QmUPHsHyuDHKyVbduvqoooAYShFCSfYgcnEioxNNqgZK2B",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmBlueLotusCoverCID",
                    "categories": ["flower", "relaxation", "sleep"],
                    "forms": ["tincture"],
                    "species": "Blue Lotus",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "45", "currency": "EUR"}]
                },
                "Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz": {
                    "business_id": "chaga1",
                    "blockchain_id": 4,
                    "cid": "Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz",
                    "title": "Chaga — medicinal mushroom",
                    "organic_components": [
                        {
                            "component_id": "chaga",
                            "description_cid": "Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmChagaCoverCID",
                    "categories": ["mushroom", "immunity", "antioxidant"],
                    "forms": ["powder", "capsules"],
                    "species": "Chaga",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "70", "currency": "EUR"}]
                },
                "Qmbkp4owyjyjRuYGd7b1KfVjo5bBvCutgYdCi7qKd3ZPoy": {
                    "business_id": "lions_mane1",
                    "blockchain_id": 5,
                    "cid": "Qmbkp4owyjyjRuYGd7b1KfVjo5bBvCutgYdCi7qKd3ZPoy",
                    "title": "Lion's Mane — cognitive support",
                    "organic_components": [
                        {
                            "component_id": "lions_mane",
                            "description_cid": "Qmbkp4owyjyjRuYGd7b1KfVjo5bBvCutgYdCi7qKd3ZPoy",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmLionsManeCoverCID",
                    "categories": ["mushroom", "cognitive", "memory"],
                    "forms": ["powder"],
                    "species": "Lion's Mane",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "85", "currency": "EUR"}]
                },
                "QmWwjNvD8HX6WB2TLsxiEhciMJCHRfiZBw9G2wgfqKyPbd": {
                    "business_id": "reishi1",
                    "blockchain_id": 6,
                    "cid": "QmWwjNvD8HX6WB2TLsxiEhciMJCHRfiZBw9G2wgfqKyPbd",
                    "title": "Reishi — longevity mushroom",
                    "organic_components": [
                        {
                            "component_id": "reishi",
                            "description_cid": "QmWwjNvD8HX6WB2TLsxiEhciMJCHRfiZBw9G2wgfqKyPbd",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmReishiCoverCID",
                    "categories": ["mushroom", "longevity", "stress"],
                    "forms": ["powder", "tincture"],
                    "species": "Reishi",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "95", "currency": "EUR"}]
                },
                "QmbGrAqeugUxZZxWojavu4rbHdk5XNmSsSv92UV8FKjyHa": {
                    "business_id": "cordyceps1",
                    "blockchain_id": 7,
                    "cid": "QmbGrAqeugUxZZxWojavu4rbHdk5XNmSsSv92UV8FKjyHa",
                    "title": "Cordyceps — energy boost",
                    "organic_components": [
                        {
                            "component_id": "cordyceps",
                            "description_cid": "QmbGrAqeugUxZZxWojavu4rbHdk5XNmSsSv92UV8FKjyHa",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmCordycepsCoverCID",
                    "categories": ["mushroom", "energy", "endurance"],
                    "forms": ["powder", "capsules"],
                    "species": "Cordyceps",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "88", "currency": "EUR"}]
                },
                "QmdmJFdMQXRpp3qNRTLYqsR1kFLYhTSRA8YMfd5JvNi85S": {
                    "business_id": "turkey_tail1",
                    "blockchain_id": 8,
                    "cid": "QmdmJFdMQXRpp3qNRTLYqsR1kFLYhTSRA8YMfd5JvNi85S",
                    "title": "Turkey Tail — immune support",
                    "organic_components": [
                        {
                            "component_id": "turkey_tail",
                            "description_cid": "QmdmJFdMQXRpp3qNRTLYqsR1kFLYhTSRA8YMfd5JvNi85S",
                            "proportion": "100%"
                        }
                    ],
                    "cover_image_url": "QmTurkeyTailCoverCID",
                    "categories": ["mushroom", "immunity", "digestive"],
                    "forms": ["powder"],
                    "species": "Turkey Tail",
                    "prices": [{"weight": "100", "weight_unit": "g", "price": "75", "currency": "EUR"}]
                }
            }
            
            # Загружаем тестовые данные в хранилище
            for cid, data in test_products.items():
                self._storage[cid] = data
                logger.info(f"🔧 [MockIPFSStorage] Загружены тестовые данные для CID: {cid}")
        
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
        
        # 🔧 ИСПРАВЛЕНИЕ: Добавляем метод для получения данных по blockchain ID
        def get_product_by_blockchain_id(self, blockchain_id):
            """Получает данные продукта по blockchain ID (для синхронизации с MockBlockchainService)"""
            # Ищем продукт по blockchain ID в загруженных данных
            for cid, data in self._storage.items():
                if data.get('blockchain_id') == blockchain_id:
                    return data
            return None
        
        # 🔧 ИСПРАВЛЕНИЕ: Добавляем метод для получения CID по blockchain ID
        def get_cid_by_blockchain_id(self, blockchain_id):
            """Получает CID по blockchain ID (для синхронизации с MockBlockchainService)"""
            for cid, data in self._storage.items():
                if data.get('blockchain_id') == blockchain_id:
                    return cid
            return None
        
        # Асинхронный метод для скачивания JSON
        async def download_json_async(self, cid):
            return self.download_json(cid)
        
        # ✅ ИСПРАВЛЕНО: download_json должен быть синхронным для ProductStorageService
        # (ProductStorageService.download_json() вызывает синхронный метод)
        def download_json(self, cid):
            return self.download_json_sync(cid)
        
        # Переименовываем старый метод для ясности (используется внутри)
        def download_json_sync(self, cid):
            if self.should_fail_download:
                return None
            
            # Сначала проверяем внутреннее хранилище
            if cid in self._storage:
                return self._storage[cid]
            
            # Fallback для обратной совместимости (убираем жесткие маппинги)
            # Возвращаем None если CID не найден - это реалистичное поведение
            return None
        
        def upload_file(self, file_path_or_data, file_name=None):
            if self.should_fail_upload:
                raise Exception("Mock IPFS upload failed")
            cid = f"QmMockFile{len(self.uploaded_jsons)}"
            self.uploaded_jsons.append((file_path_or_data, file_name))
            return cid
        
        def get_gateway_url(self, cid):
            return f"https://mocked.ipfs/{cid}"
        
        def is_valid_cid(self, cid):
            return isinstance(cid, str) and cid.startswith("Qm")
        
        def clear(self):
            """Очищает внутреннее хранилище между тестами"""
            self._storage.clear()
            self._counter = 0
            self.uploaded_jsons.clear()
            self.downloaded_json.clear()
            
            # После очистки заново загружаем тестовые данные
            self._populate_test_data()
    
    return MockIPFSStorage()

@pytest.fixture(scope="function")
def mock_registry_service(mock_blockchain_service, mock_ipfs_storage, mock_validation_service, mock_account_service):
    """
    Полностью замоканный ProductRegistryService для unit-тестов.
    
    Использует TestServiceFactory для создания сервиса с правильно замокированными зависимостями.
    Все зависимости передаются явно, предотвращая создание реальных сервисов.
    
    ✅ ИСПРАВЛЕНО: Используем реальный ProductAssembler с моком ComponentService
    для правильной сборки продуктов из метаданных.
    """
    from bot.tests.fixtures.service_factory import TestServiceFactory
    from unittest.mock import Mock, AsyncMock
    from bot.services.product.assembler import ProductAssembler
    # ✅ ИСПРАВЛЕНО: Используем правильный импорт ComponentService (как в assembler)
    # Проверяем через sys.path для работы с относительными импортами
    import sys
    import os
    # Добавляем bot в path для корректного импорта
    bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot')
    if bot_path not in sys.path:
        sys.path.insert(0, bot_path)
    
    try:
        from services.product.component_service import ComponentService
    except ImportError:
        # Fallback на bot.services если первый не работает
        from bot.services.product.component_service import ComponentService
    
    # ✅ ИСПРАВЛЕНО: Создаем реальный ProductAssembler с моком ComponentService
    # Это позволяет реально собирать продукты из метаданных, но без реальных обращений к компонентам
    mock_component_service = Mock(spec=ComponentService)
    mock_component_service.get_component_description = AsyncMock(return_value=None)  # Мокируем получение описаний
    
    # ✅ ИСПРАВЛЕНО: Настройка get_component_full для возврата реального OrganicComponent
    # По аналогии с test_product_assembler.py (MockComponentService возвращает реальные объекты)
    def mock_get_component_full(component_id: str):
        """
        Возвращает реальный OrganicComponent для тестов.
        
        Args:
            component_id: ID компонента (например, "amanita_muscaria")
        
        Returns:
            OrganicComponent: Реальный объект компонента для тестирования
        """
        if not component_id:
            return None
        
        # Создаем реальный объект OrganicComponent (как в test_product_assembler.py, строки 35-40)
        return OrganicComponent(
            component_id=component_id,
            blockchain_id=1,
            creator="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            active=True,
            created_at=None,
            scientific_title=f"Test {component_id}",
            forms=[],
            features={},  # features должен быть dict, не list
            localizations={}
        )
    
    mock_component_service.get_component_full = Mock(side_effect=mock_get_component_full)
    
    real_assembler = ProductAssembler(component_service=mock_component_service, validation_service=mock_validation_service)
    
    # Создаем сервис через TestServiceFactory с явной передачей всех зависимостей
    # Передаем реальный assembler вместо мока
    service = TestServiceFactory.create_product_registry_service(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage,
        validation_service=mock_validation_service,
        account_service=mock_account_service,
        assembler=real_assembler  # ✅ Используем реальный assembler
    )
    
    # Мокаем cache_service чтобы избежать реальных обращений к IPFS
    # (сохраняем для обратной совместимости с существующими тестами)
    mock_cache_service = Mock()
    mock_cache_service.get_description_by_cid.return_value = None
    mock_cache_service.get_image_url_by_cid.return_value = "https://mocked.ipfs/test.jpg"
    mock_cache_service.set_cached_item.return_value = None
    mock_cache_service.invalidate_cache.return_value = None
    mock_cache_service.get_cached_item.return_value = None
    service.cache_service = mock_cache_service
    
    # Мокаем metadata_service чтобы избежать реальных обращений к IPFS
    # (сохраняем для обратной совместимости с существующими тестами)
    mock_metadata_service = Mock()
    mock_metadata_service.process_metadata.return_value = None
    service.metadata_service = mock_metadata_service
    
    logger.debug("✅ mock_registry_service создан через TestServiceFactory")
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
            
            # 🔧 ИСПРАВЛЕНИЕ: Добавляем seller_account для тестов endpoint GET /products/{seller_address}
            self.seller_account = Mock()
            self.seller_account.address = "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"  # Тестовый адрес по умолчанию
            
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
            # Настройка проверки прав доступа
            self.check_permissions = False  # По умолчанию проверка прав отключена
            self.simulate_permission_denied = False  # По умолчанию права не ограничены
            
            # Настройка cache_service
            self.cache_service.get_cached_item.return_value = None
            self.cache_service.set_cached_item.return_value = True
            self.cache_service.invalidate_cache.return_value = None
            self.cache_service.get_description_by_cid.return_value = None
            self.cache_service.get_image_url_by_cid.return_value = "https://mocked.ipfs/test.jpg"
            
            # Настройка metadata_service
            from bot.validation import ValidationResult
            test_metadata = {
                "id": "test_product",
                "title": "Test Product",
                "organic_components": [{"component_id": "test_biounit", "description_cid": "QmTestDesc", "proportion": "100%"}],
                "cover_image_url": "QmTestImage",
                "categories": ["mushroom"],
                "forms": ["powder"],
                "species": "test_species",
                "prices": [{"weight": "100", "weight_unit": "g", "price": "50", "currency": "EUR"}]
            }
            self.metadata_service.validate_and_parse_metadata.return_value = ValidationResult(
                is_valid=True, 
                error_message=None, 
                field_name=None, 
                field_value=test_metadata, 
                error_code="VALID", 
                suggestions=[]
            )
            self.metadata_service.create_product_metadata.return_value = {}
            
            # Настройка validation_service - не переопределяем, используем оригинальный mock
            # self.validation_service.validate_product_data уже настроен в mock_validation_service
            
            # Настройка storage_service - только если это Mock объект
            if hasattr(self.storage_service, 'return_value'):
                # Если storage_service - это Mock объект, настраиваем его
                self.storage_service.download_json.return_value = {
                    "id": "test_product",
                    "title": "Test Product",
                    "description_cid": "QmDescriptionCID",
                    "cover_image_url": "QmImageCID",
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
                "cover_image_url": "QmTestCoverCID1",
                "gallery": ["QmTestGalleryCID1"],
                "categories": ["mushroom"],
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
                # 🔧 ИСПРАВЛЕНО: используем business_id или id из данных
                business_id = product_data.get("business_id") or product_data.get("id")
                
                # 🔧 ДОБАВЛЕНО: генерируем уникальный business_id только если оба поля отсутствуют
                if not business_id:
                    business_id = f"generated_product_{self._product_counter}_{int(time.time())}"
                    logger.info(f"🔧 [Mock] Сгенерирован business_id: {business_id}")
                else:
                    logger.info(f"🔧 [Mock] Используем предоставленный business_id/id: {business_id}")
                
                logger.info(f"🔧 [Mock] Создание продукта: {business_id}")
                
                # Валидация
                validation_result = await self.validation_service.validate_product_data(product_data)
                if not validation_result.is_valid:
                    return {
                        "business_id": business_id,
                        "status": "error",
                        "error": validation_result.error_message or "Validation failed"
                    }
                
                # 🔧 ИСПРАВЛЕНО: проверяем уникальность business_id
                if business_id and await self._check_product_id_exists(business_id):
                    return {
                        "business_id": business_id,
                        "status": "error",
                        "error": f"Продукт с business_id '{business_id}' уже существует"
                    }
                
                # Создание метаданных
                metadata = self.create_product_metadata(product_data)
                
                # Загрузка в IPFS
                metadata_cid = await self.storage_service.upload_json(metadata)
                if not metadata_cid:
                    return {
                        "business_id": business_id,
                        "status": "error",
                        "error": "Ошибка загрузки метаданных в IPFS"
                    }
                
                # Запись в блокчейн
                tx_hash = await self.blockchain_service.create_product(metadata_cid)
                if not tx_hash:
                    return {
                        "business_id": business_id,
                        "metadata_cid": metadata_cid,
                        "status": "error",
                        "error": "Ошибка записи в блокчейн"
                    }
                
                # Получение blockchain_id
                blockchain_id = await self.blockchain_service.get_product_id_from_tx(tx_hash)
                
                # 🔧 ИСПРАВЛЕНО: сохраняем по business_id вместо id
                self._products[business_id] = product_data
                self._metadata_cids[business_id] = metadata_cid
                self._blockchain_ids[business_id] = blockchain_id
                self._product_counter += 1
                
                logger.info(f"🔧 [Mock] Продукт {business_id} создан успешно")
                return {
                    "business_id": business_id,
                    "id": business_id,  # 🔧 ДОБАВЛЕНО: обратная совместимость для тестов
                    "metadata_cid": metadata_cid,
                    "blockchain_id": str(blockchain_id) if blockchain_id else None,
                    "tx_hash": str(tx_hash) if tx_hash else None,
                    "status": "success",
                    "error": None
                }
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка создания продукта: {e}")
                return {
                    "business_id": business_id,
                    "status": "error",
                    "error": str(e)
                }
        
        async def get_product(self, product_id: Union[str, int]) -> Optional[Product]:
            """Получает продукт по ID"""
            try:
                if not product_id:
                    return None
                
                # 🔧 ИСПРАВЛЕНО: добавляем импорты в начало метода
                from bot.model.product import Product, OrganicComponent, PriceInfo
                
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
                        component_id="test_biounit_1",
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
                    
                    # 🔧 ИСПРАВЛЕНО: используем новую структуру Product
                    product = Product(
                        business_id=product_id_str,
                        blockchain_id=blockchain_id or int(product_id_str),
                        status=1,  # Активный по умолчанию
                        cid=metadata_cid or "QmMockCID",
                        title=product_data.get("title", ""),
                        organic_components=[organic_component],
                        cover_image_url="QmMockCID",  # 🔧 ИСПРАВЛЕНО: используем CID вместо URL
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
                    # Проверяем, что у продукта есть CID (продукт действительно существует)
                    blockchain_id, seller_address, cid, status = product_data
                    if cid is None:
                        # Продукт не найден в блокчейне
                        logger.info(f"🔧 [Mock] Продукт {product_id} не найден в блокчейне (CID=None)")
                        return None
                    
                    # Валидируем метаданные через metadata_service
                    validation_result = self.metadata_service.validate_and_parse_metadata(product_data)
                    if validation_result.is_valid:
                        # Создаем продукт из валидированных метаданных
                        metadata = validation_result.field_value
                        # Создаем тестовый продукт для мока
                        
                        test_component = OrganicComponent(
                            component_id="test_biounit_1",
                            description_cid="QmTestDescriptionCID1",
                            proportion="100%"
                        )
                        
                        test_price = PriceInfo(
                            price=50.0,
                            weight=100,
                            weight_unit="g",
                            currency="EUR"
                        )
                        
                        # 🔧 ИСПРАВЛЕНО: используем новую структуру Product
                        product = Product(
                            business_id=str(product_id),
                            blockchain_id=product_id,
                            status=1,
                            cid="QmTestCID",
                            title="Test Product from Blockchain",
                            organic_components=[test_component],
                            cover_image_url="QmTestCID",  # 🔧 ИСПРАВЛЕНО: используем CID вместо URL
                            categories=["mushroom"],
                            forms=["powder"],
                            species="test_species",
                            prices=[test_price]
                        )
                        
                        return product
                    else:
                        self.logger.warning(f"🔧 [Mock] Метаданные невалидны: {validation_result.error_message}")
                        return None
                
                logger.info(f"🔧 [Mock] Продукт {product_id_str} не найден")
                return None
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка получения продукта {product_id}: {e}")
                return None
        
        async def get_all_products(self) -> List[Product]:
            """Получает все продукты"""
            try:
                logger.info("🔧 [Mock] Получение всех продуктов")
                
                # 🔧 ИСПРАВЛЕНО: Возвращаем тестовые данные вместо пустого списка
                from bot.model.product import Product, OrganicComponent, PriceInfo
                
                # Создаем тестовый продукт для каталога
                test_product = Product(
                    business_id="test_product_001",
                    blockchain_id=1,
                    status=1,
                    cid="QmTestProductCID",
                    title="Test Amanita Product",
                    organic_components=[
                        OrganicComponent(
                            component_id="amanita_muscaria",
                            description_cid="QmTestDescCID",
                            proportion="100%"
                        )
                    ],
                    cover_image_url="QmTestImageCID",
                    categories=["mushroom"],
                    forms=["powder"],
                    species="Amanita Muscaria",
                    prices=[
                        PriceInfo(
                            price=50,
                            currency="EUR",
                            weight="100",
                            weight_unit="g",
                            volume=None,
                            volume_unit=None,
                            form="powder"
                        )
                    ]
                )
                
                products = [test_product]
                
                # Обновляем кэш
                self.cache_service.set_cached_item("catalog", {
                    "version": self._catalog_version,
                    "products": products
                }, "catalog")
                
                logger.info(f"🔧 [Mock] Получено {len(products)} тестовых продуктов")
                return products
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка получения всех продуктов: {e}")
                return []
        
        async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
            """Обновляет продукт"""
            try:
                logger.info(f"🔧 [Mock] Обновление продукта: {product_id}")
                
                # 🔧 ПРОВЕРКА ПРАВ ДОСТУПА (приоритет 1)
                if self.check_permissions and self.simulate_permission_denied:
                    logger.info(f"🔧 [Mock] Отказ в правах доступа для продукта {product_id}")
                    return {
                        "business_id": product_id,
                        "status": "error",
                        "error": "Недостаточно прав для обновления продукта",
                        "error_code": "403"
                    }
                
                # 🔧 ИСПРАВЛЕНИЕ: Имитация ошибки доступа для тестов 403 (должна быть второй!)
                if "403_error" in product_id:
                    logger.info(f"🔧 [Mock] Имитация 403 ошибки для продукта {product_id}")
                    return {
                        "business_id": product_id,
                        "status": "error",
                        "error": "Недостаточно прав для обновления продукта",
                        "error_code": "403"
                    }
                
                # 🔧 ИСПРАВЛЕНО: используем business_id вместо id
                # Проверка существования
                existing_product = await self.get_product(product_id)
                if not existing_product:
                    return {
                        "business_id": product_id,
                        "status": "error",
                        "error": f"Продукт с business_id {product_id} не найден"
                    }
                
                # Валидация
                is_valid = await self.validate_product(product_data)
                if not is_valid:
                    return {
                        "business_id": product_id,
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
                    "business_id": product_id,  # 🔧 ИСПРАВЛЕНО: используем business_id
                    "metadata_cid": new_metadata_cid,
                    "blockchain_id": None,  # Не обновляем в блокчейне в Mock
                    "tx_hash": None,
                    "status": "success",
                    "error": None
                }
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка обновления продукта {product_id}: {e}")
                return {
                    "business_id": product_id,  # 🔧 ИСПРАВЛЕНО: используем business_id
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
                required_fields = ['title', 'organic_components', 'categories', 'cover_image_url', 'forms', 'species', 'prices']
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
                
                # Детальная валидация цен
                for price in product_data['prices']:
                    # Проверяем price - должен быть числом
                    if not isinstance(price.get('price'), (int, float)) or price.get('price') <= 0:
                        self.logger.error(f"Invalid price: {price.get('price')} - должен быть положительным числом")
                        return False
                    
                    # Проверяем currency - должна быть валидной валютой
                    valid_currencies = ['USD', 'EUR', 'GBP', 'RUB']
                    if price.get('currency') not in valid_currencies:
                        self.logger.error(f"Invalid currency: {price.get('currency')} - должна быть одной из {valid_currencies}")
                        return False
                    
                    # Проверяем weight - должен быть положительным числом
                    if not isinstance(price.get('weight'), (int, float)) or price.get('weight') <= 0:
                        self.logger.error(f"Invalid weight: {price.get('weight')} - должен быть положительным числом")
                        return False
                    
                    # Проверяем weight_unit - должна быть валидной единицей
                    valid_weight_units = ['g', 'kg', 'ml', 'l', 'capsules', 'tablets']
                    if price.get('weight_unit') not in valid_weight_units:
                        self.logger.error(f"Invalid weight_unit: {price.get('weight_unit')} - должна быть одной из {valid_weight_units}")
                        return False
                
                # Проверяем формы
                if not isinstance(product_data['forms'], list) or not product_data['forms']:
                    self.logger.error("Формы должны быть непустым списком")
                    return False
                
                # Проверяем IPFS CID
                if not self.storage_service.is_valid_cid(product_data['cover_image_url']):
                    self.logger.error("Invalid cover image CID")
                    return False
                
                logger.info("🔧 [Mock] Валидация продукта прошла успешно")
                return True
                
            except Exception as e:
                self.logger.error(f"🔧 [Mock] Ошибка валидации продукта: {e}")
                return False
        
        async def _check_product_id_exists(self, product_id: Union[str, int]) -> bool:
            """Проверяет существование продукта по business_id"""
            try:
                product_id_str = str(product_id)
                logger.info(f"🔧 [Mock] Проверка существования продукта по business_id: {product_id_str}")
                
                # 🔧 ИСПРАВЛЕНИЕ: Имитация ошибки для тестов 400
                if product_id_str.endswith("400_error"):
                    logger.info(f"🔧 [Mock] Имитация ошибки 400 для продукта {product_id_str}")
                    return False
                
                # 🔧 ИСПРАВЛЕНО: проверяем только во внутреннем состоянии для создания новых продуктов
                # В Mock архитектуре мы не проверяем существование в блокчейне при создании
                if product_id_str in self._products:
                    logger.info(f"🔧 [Mock] Продукт с business_id {product_id_str} найден во внутреннем состоянии")
                    return True
                
                logger.info(f"🔧 [Mock] Продукт {product_id_str} не найден во внутреннем состоянии")
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
                
                # 🔧 ИСПРАВЛЕНО: поддерживаем как business_id, так и id для обратной совместимости
                business_id = product_data.get("business_id") or product_data.get("id")
                if not business_id:
                    raise KeyError("business_id или id")
                
                metadata = {
                    "business_id": business_id,
                    "title": product_data["title"],
                    "organic_components": product_data["organic_components"],
                    "cover_image_url": product_data["cover_image_url"],
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
                
                # 🔧 ИСПРАВЛЕНО: используем новую структуру Product с business_id и blockchain_id
                product = Product(
                    business_id=str(product_id),  # Используем product_id как business_id
                    blockchain_id=product_id,      # Используем product_id как blockchain_id
                    status=1 if active else 0,
                    cid=ipfs_cid,
                    title=metadata.get('title', ''),
                    description=None,
                    description_cid=metadata.get('description_cid', ''),
                    cover_image_url=self._get_cached_image(metadata.get('cover_image_url', '')),
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
                validation_result = self.metadata_service.validate_and_parse_metadata(metadata)
                if validation_result.is_valid:
                    # Создаем тестовый продукт для мока
                    from bot.model.product import Product, OrganicComponent, PriceInfo
                    
                    test_component = OrganicComponent(
                        component_id="test_biounit_1",
                        description_cid="QmTestDescriptionCID1",
                        proportion="100%"
                    )
                    
                    test_price = PriceInfo(
                        price=50.0,
                        weight=100,
                        weight_unit="g",
                        currency="EUR"
                    )
                    
                    product = Product(
                        id=product_id,
                        alias=str(product_id),
                        status=1 if is_active else 0,
                        cid=ipfs_cid,
                        title="Test Product from Mock",
                        organic_components=[test_component],
                        cover_image_url="https://mocked.ipfs/test.jpg",
                        categories=["mushroom"],
                        forms=["powder"],
                        species="test_species",
                        prices=[test_price]
                    )
                else:
                    self.logger.warning(f"🔧 [Mock] Метаданные невалидны: {validation_result.error_message}")
                    return None
                
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
    storage_type = os.getenv("INTEGRATION_STORAGE", "arweave").lower()
    print(f"🔍 [DEVOPS] INTEGRATION_STORAGE={storage_type}")
    
    # 📊 Логирование доступности API ключей для диагностики
    arweave_private_key = os.getenv("ARWEAVE_PRIVATE_KEY")
    
    print("🔍 [DEVOPS] ARWEAVE_PRIVATE_KEY: ********")
    
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
    from bot.services.product.validation import ProductValidationService
    from bot.services.core.account import AccountService
    
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
        validation_service=ProductValidationService(),  # ✅ Реальный сервис
        account_service=AccountService(blockchain_service)  # ✅ Реальный сервис
    )
    
    logger.info("✅ IntegrationRegistryService создан с реальным блокчейном")
    return registry_service


@pytest.fixture(scope="function")
def integration_registry_service_real_full():
    """
    Интеграционный сервис с ПОЛНОСТЬЮ реальными сервисами.
    
    Использует:
    - ✅ Реальный BlockchainService (Hardhat node)
    - ✅ Реальный ArWeaveUploader, обернутый в ProductStorageService (real Arweave)
    - ✅ Реальный ProductValidationService
    - ✅ Реальный AccountService
    - ✅ Реальный ProductAssembler и ComponentService
    
    Требует:
    - SELLER_PRIVATE_KEY в .env
    - ARWEAVE_PRIVATE_KEY в .env
    - Запущенный Hardhat node
    
    Эта фикстура предназначена для интеграционных тестов с реальными данными селлера.
    """
    from bot.dependencies import get_product_registry_service
    from bot.services.core.blockchain import BlockchainService
    from bot.services.product.validation import ProductValidationService
    from bot.services.core.account import AccountService
    from bot.services.core.storage.ar_weave import ArWeaveUploader
    from bot.services.product.storage import ProductStorageService
    import os
    
    # Проверка обязательных переменных окружения
    seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
    arweave_private_key = os.getenv("ARWEAVE_PRIVATE_KEY")
    
    if not seller_private_key:
        pytest.skip("⚠️ SELLER_PRIVATE_KEY не установлен в .env (требуется для интеграционных тестов)")
    
    if not arweave_private_key:
        pytest.skip("⚠️ ARWEAVE_PRIVATE_KEY не установлен в .env (требуется для интеграционных тестов)")
    
    try:
        # ✅ Реальный блокчейн
        blockchain_service = BlockchainService()
        if not blockchain_service.web3.is_connected():
            pytest.skip("⚠️ Hardhat node недоступен (проверьте, что node запущен на localhost:8545)")
        
        logger.info("✅ BlockchainService инициализирован (реальный блокчейн)")
        
        # ✅ Реальный Arweave storage, обернутый в ProductStorageService
        arweave_provider = ArWeaveUploader()
        storage_service = ProductStorageService(storage_provider=arweave_provider)
        logger.info("✅ ArWeaveUploader обернут в ProductStorageService (реальный Arweave)")
        
        # ✅ Реальный validation service
        validation_service = ProductValidationService()
        logger.info("✅ ProductValidationService инициализирован (реальный сервис)")
        
        # ✅ Реальный account service
        account_service = AccountService(blockchain_service)
        logger.info("✅ AccountService инициализирован (реальный сервис)")
        
        # Создаем ProductRegistryService через DI с полностью реальными сервисами
        registry_service = get_product_registry_service(
            blockchain_service=blockchain_service,      # ✅ Реальный
            storage_service=storage_service,            # ✅ Реальный (ArWeaveUploader в ProductStorageService)
            validation_service=validation_service,      # ✅ Реальный
            account_service=account_service             # ✅ Реальный
            # assembler создается автоматически с реальными зависимостями
        )
        
        logger.info("✅ ProductRegistryService создан с ПОЛНОСТЬЮ реальными сервисами")
        logger.info("🚀 Готов к интеграционному тестированию с реальными данными")
        
        return registry_service
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации реальных сервисов: {e}")
        pytest.skip(f"Ошибка инициализации: {e}")


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
def seller_address(request):
    """
    Фикстура для получения адреса селлера как строки.
    
    Источники адреса (в порядке приоритета):
    1. SELLER_ADDRESS env var (если установлен)
    2. seller_account.address (если seller_account доступен через SELLER_PRIVATE_KEY)
    3. Создание Account из SELLER_PRIVATE_KEY напрямую (если доступен)
    4. Hardcoded fallback для localhost: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
    
    Returns:
        str: Ethereum адрес селлера (lowercase, нормализованный)
    
    Использование:
        def test_example(seller_address):
            assert seller_address.startswith("0x")
            assert seller_address == "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
    """
    import os
    
    # Получаем оба источника для проверки соответствия (если доступны)
    seller_address_env = os.getenv("SELLER_ADDRESS")
    seller_account_obj = None
    account_address_from_fixture = None
    
    # Попытка получить seller_account fixture для проверки соответствия
    try:
        seller_account_obj = request.getfixturevalue('seller_account')
        if seller_account_obj and hasattr(seller_account_obj, 'address'):
            account_address_from_fixture = seller_account_obj.address.lower() if seller_account_obj.address else None
    except (pytest.FixtureLookupError, Exception) as e:
        # Фикстура seller_account недоступна - это нормально, продолжаем
        logger.debug(f"ℹ️ seller_account fixture недоступна для проверки соответствия: {e}")
    
    # Проверка соответствия адресов (если оба источника доступны)
    if seller_address_env and account_address_from_fixture:
        seller_address_normalized = seller_address_env.lower()
        if seller_address_normalized != account_address_from_fixture:
            logger.warning(
                f"⚠️ Несоответствие адресов: "
                f"SELLER_ADDRESS={seller_address_env} != seller_account.address={account_address_from_fixture}. "
                f"Используется SELLER_ADDRESS (приоритет 1)."
            )
    
    # Приоритет 1: SELLER_ADDRESS env var
    if seller_address_env:
        normalized = seller_address_env.lower()
        logger.info(f"✅ Seller address from SELLER_ADDRESS env: {normalized}")
        return normalized
    
    # Приоритет 2: seller_account.address (если seller_account доступен)
    if seller_account_obj and account_address_from_fixture:
        logger.info(f"✅ Seller address from seller_account fixture: {account_address_from_fixture}")
        return account_address_from_fixture
    
    # Приоритет 3: Создание Account из SELLER_PRIVATE_KEY напрямую
    seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
    if seller_private_key:
        try:
            from eth_account import Account
            account = Account.from_key(seller_private_key)
            if account and hasattr(account, 'address'):
                normalized = account.address.lower()
                logger.info(f"✅ Seller address from SELLER_PRIVATE_KEY: {normalized}")
                return normalized
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать Account из SELLER_PRIVATE_KEY: {e}")
    
    # Приоритет 4: Hardcoded fallback для localhost
    fallback_address = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
    logger.info(f"⚠️ Seller address using hardcoded fallback (localhost): {fallback_address}")
    logger.warning("💡 Рекомендуется установить SELLER_ADDRESS в .env для явности")
    return fallback_address


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
                    "component_id": "amanita_muscaria",
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
                    "component_id": "amanita_pantherina",
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
                    "component_id": "amanita_muscaria",
                    "description_cid": "QmBasicTestCID001",
                    "proportion": "100%"
                }
            ],
            "cover_image_url": "QmBasicCoverCID001",
            "categories": ["mushroom"],
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
                    "component_id": "amanita_pantherina",
                    "description_cid": "QmBasicTestCID002",
                    "proportion": "100%"
                }
            ],
            "cover_image_url": "QmBasicCoverCID002",
            "categories": ["mushroom"],
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
    
    return created_products

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
                    "component_id": "amanita_muscaria",
                    "description_cid": "QmExtendedTestCID001",
                    "proportion": "70%"
                },
                {
                    "component_id": "amanita_pantherina",
                    "description_cid": "QmExtendedTestCID002",
                    "proportion": "30%"
                }
            ],
            "cover_image_url": "QmExtendedCoverCID001",
            "categories": ["mushroom", "extended"],
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
                    "component_id": "blue_lotus",
                    "description_cid": "QmExtendedTestCID003",
                    "proportion": "100%"
                }
            ],
            "cover_image_url": "QmExtendedCoverCID002",
            "categories": ["flower", "extended"],
            "forms": ["powder"],
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
    
    return created_products

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
                    "component_id": "amanita_muscaria",
                    "description_cid": "QmValidationTestCID001",
                    "proportion": "100%"
                }
            ],
            "cover_image_url": "QmValidationCoverCID001",
            "categories": ["mushroom"],
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
                    "component_id": "amanita_pantherina",
                    "description_cid": "QmValidationTestCID002",
                    "proportion": "100%"
                }
            ],
            "cover_image_url": "QmValidationCoverCID002",
            "categories": ["mushroom"],
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
    
    return created_products

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
    
    return all_data
    
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
    
    return product_type

@pytest.fixture
def category_for_basic():
    """Категории для базовых продуктов"""
    return ["mushroom", "flower"]

@pytest.fixture
def category_for_extended():
    """Категории для расширенных продуктов"""
    return ["mushroom", "flower"]

@pytest.fixture
def category_for_validation():
    """Категории для продуктов валидации"""
    return ["mushroom"]

@pytest.fixture
def form_for_basic():
    """Формы для базовых продуктов"""
    return ["powder", "capsules", "tincture"]

@pytest.fixture
def form_for_extended():
    """Формы для расширенных продуктов"""
    return ["powder", "capsules"]

@pytest.fixture
def form_for_validation():
    """Формы для продуктов валидации"""
    return ["powder", "capsules"]

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


@pytest.fixture(scope="function")
def web3():
    """Фикстура для Web3 экземпляра (mock для unit тестов)"""
    from unittest.mock import Mock
    
    mock_web3 = Mock()
    
    # Настройка mock Web3
    mock_web3.eth.contract.return_value = Mock()
    mock_web3.eth.get_transaction_receipt.return_value = {
        'status': 1,
        'blockNumber': 12345,
        'transactionHash': '0xmock_transaction_hash'
    }
    mock_web3.eth.get_transaction.return_value = {
        'from': '0x1234567890abcdef1234567890abcdef12345678',
        'to': '0xcontract_address',
        'value': 0,
        'gas': 21000,
        'gasPrice': 20000000000
    }
    
    # Настройка mock для gas estimation
    mock_web3.eth.estimate_gas.return_value = 21000
    
    return mock_web3


@pytest.fixture(scope="function")
def invite_nft_contract(web3):
    """Фикстура для InviteNFT контракта (mock для unit тестов)"""
    from unittest.mock import Mock
    
    mock_contract = Mock()
    
    # Настройка методов контракта
    mock_contract.functions.isSeller.return_value.call.return_value = False
    mock_contract.functions.userInviteCount.return_value.call.return_value = 0
    mock_contract.functions.isUserActivated.return_value.call.return_value = False
    mock_contract.functions.getAllActivatedUsers.return_value.call.return_value = []
    mock_contract.functions.batchValidateInviteCodes.return_value.call.return_value = ([], [])
    mock_contract.functions.getTokenIdByInviteCode.return_value.call.return_value = 0
    mock_contract.functions.getInviteCodeByTokenId.return_value.call.return_value = ""
    mock_contract.functions.isInviteTokenUsed.return_value.call.return_value = False
    mock_contract.functions.getInviteCreatedAt.return_value.call.return_value = 0
    mock_contract.functions.getInviteExpiry.return_value.call.return_value = 0
    mock_contract.functions.getInviteMinter.return_value.call.return_value = "0x0000000000000000000000000000000000000000"
    mock_contract.functions.getInviteFirstOwner.return_value.call.return_value = "0x0000000000000000000000000000000000000000"
    mock_contract.functions.validateInviteCode.return_value.call.return_value = (False, "not_found")
    
    return mock_contract


@pytest.fixture(scope="function")
def mock_blockchain_service_with_invite_nft(mock_blockchain_service):
    """Фикстура для MockBlockchainService с поддержкой InviteNFT"""
    # Используем существующий mock_blockchain_service, который уже расширен
    # для поддержки InviteNFT методов
    return mock_blockchain_service


@pytest.fixture(scope="function")
def real_blockchain_service():
    """Фикстура для реального BlockchainService (для integration тестов)"""
    from bot.services.core.blockchain import BlockchainService
    
    # Возвращаем реальный сервис для integration тестов
    # В реальных тестах может потребоваться настройка тестовой сети
    return BlockchainService()


# === ТЕСТОВОЕ FASTAPI ПРИЛОЖЕНИЕ ===

@pytest.fixture(scope="function")
def test_app(mock_product_registry_service):
    """Фикстура для создания тестового FastAPI приложения с подмененными зависимостями"""
    from fastapi.testclient import TestClient
    from bot.api.main import create_api_app
    from unittest.mock import Mock
    
    # Создаем mock ServiceFactory
    mock_service_factory = Mock()
    mock_service_factory.create_product_registry_service.return_value = mock_product_registry_service
    
    # Создаем тестовое приложение БЕЗ аутентификации для тестов
    app = create_api_app(service_factory=mock_service_factory)
    
    # 🔧 ИСПРАВЛЕНО: Создаем тестовое приложение без аутентификации
    # Создаем новое приложение без middleware
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Создаем чистое FastAPI приложение
    test_app = FastAPI(
        title="Amanita API Test",
        description="Тестовое приложение без аутентификации",
        version="1.0.0"
    )
    
    # Добавляем только CORS middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Копируем роутеры из основного приложения
    from bot.api.routes import api_keys, products, media, description
    test_app.include_router(api_keys.router)
    test_app.include_router(products.router)
    test_app.include_router(media.router)
    test_app.include_router(description.router)
    
    # Подменяем зависимости для тестирования
    from bot.api.dependencies import get_product_registry_service
    
    def override_get_product_registry_service():
        return mock_product_registry_service
    
    test_app.dependency_overrides[get_product_registry_service] = override_get_product_registry_service
    
    # Создаем тестовый клиент
    with TestClient(test_app) as client:
        yield client
    
    # Очищаем зависимости после теста
    test_app.dependency_overrides.clear()
    

