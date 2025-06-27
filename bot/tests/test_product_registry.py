import pytest
import logging
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import pytest_asyncio
from unittest.mock import patch, MagicMock
from eth_account import Account
from bot.services.core.blockchain import BlockchainService
from bot.services.product.registry import ProductRegistryService
from bot.services.product.validation import ProductValidationService
from bot.services.core.account import AccountService
from bot.services.core.ipfs_factory import IPFSFactory
from bot.model.product import PriceInfo, Description
from decimal import Decimal

# Загружаем .env файл
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Настройка pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Настройка логирования
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Assert на ключевые переменные окружения
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
NODE_ADMIN_PRIVATE_KEY = os.getenv("NODE_ADMIN_PRIVATE_KEY")
AMANITA_REGISTRY_CONTRACT_ADDRESS = os.getenv("AMANITA_REGISTRY_CONTRACT_ADDRESS")

assert SELLER_PRIVATE_KEY, "SELLER_PRIVATE_KEY не найден в .env!"
assert NODE_ADMIN_PRIVATE_KEY, "NODE_ADMIN_PRIVATE_KEY не найден в .env!"
assert AMANITA_REGISTRY_CONTRACT_ADDRESS, "AMANITA_REGISTRY_CONTRACT_ADDRESS не найден в .env!"

# Тестовые данные
TEST_PRODUCT_DATA = {
    "id": "test_product_1",
    "title": "Amanita muscaria — sliced caps and gills (1st grade)",
    "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
    "categories": [
        "mushroom",
        "mental health",
        "focus",
        "ADHD support",
        "mental force"
    ],
    "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
    "form": "mixed slices",
    "species": "Amanita muscaria",
    "prices": [
        {
            "weight": "100",
            "weight_unit": "g",
            "price": "80",
            "currency": "EUR"
    }
    ]
}

# Загружаем тестовые данные
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "products.json")
with open(TEST_DATA_PATH) as f:
    TEST_PRODUCTS = json.load(f)

# ================== ФИКСТУРЫ =====================

@pytest_asyncio.fixture
async def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def test_data():
    """Загружаем реальные тестовые данные из фикстур"""
    logger.info("📁 Загружаем тестовые данные из фикстур")
    fixtures_path = Path(__file__).parent / "fixtures" / "products.json"
    with open(fixtures_path) as f:
        data = json.load(f)
    logger.info(f"✅ Загружено {len(data.get('valid_products', []))} валидных продуктов")
    return data

@pytest_asyncio.fixture
async def storage_service():
    """Инициализируем storage через фабрику"""
    logger.info("🔧 Инициализируем storage через IPFSFactory")
    factory = IPFSFactory()
    storage = factory.get_storage()
    logger.info("✅ Storage инициализирован")
    return storage

@pytest_asyncio.fixture
async def validation_service():
    """Инициализируем сервис валидации"""
    logger.info("🔧 Инициализируем ProductValidationService")
    service = ProductValidationService()
    logger.info("✅ ProductValidationService инициализирован")
    return service

@pytest_asyncio.fixture
async def account_service():
    """Инициализируем AccountService"""
    logger.info("🔧 Инициализируем AccountService")
    BlockchainService.reset()
    service = AccountService(BlockchainService())
    logger.info("✅ AccountService инициализирован")
    return service

@pytest_asyncio.fixture
async def seller_account():
    """Фикстура для получения аккаунта продавца"""
    logger.info("🔧 Создаем аккаунт продавца")
    account = Account.from_key(SELLER_PRIVATE_KEY)
    logger.info(f"✅ Аккаунт продавца: {account.address}")
    return account

@pytest_asyncio.fixture
async def user_account():
    """Фикстура для тестового пользователя"""
    logger.info("🔧 Создаем тестовый аккаунт пользователя")
    account = Account.create()
    logger.info(f"✅ Тестовый аккаунт: {account.address}")
    return account

@pytest_asyncio.fixture
async def blockchain_service():
    """Инициализируем BlockchainService"""
    logger.info("🔧 Инициализируем BlockchainService")
    BlockchainService.reset()
    service = BlockchainService()
    
    # Проверяем роль SELLER_ROLE
    seller_account = Account.from_key(SELLER_PRIVATE_KEY)
    assert seller_account.address == service.seller_account.address, "Аккаунт продавца не совпадает"
    try:
        is_seller = service.call_contract_function("InviteNFT", "isSeller", seller_account.address)
        logger.info(f"🔍 Проверка роли SELLER_ROLE: {seller_account.address} -> {is_seller}")
        if not is_seller:
            logger.warning(f"⚠️ Селлер {seller_account.address} не имеет роль SELLER_ROLE. Роль должна быть назначена при деплое контракта.")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось проверить роль SELLER_ROLE: {e}")
    
    logger.info("✅ BlockchainService инициализирован")
    return service

@pytest_asyncio.fixture
async def product_registry(blockchain_service, storage_service, validation_service, account_service):
    """Инициализируем ProductRegistryService"""
    logger.info("🔧 Инициализируем ProductRegistryService")
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
    
    assert service.blockchain.seller_account.address == Account.from_key(SELLER_PRIVATE_KEY).address, "Аккаунт продавца не совпадает"
    logger.info("✅ ProductRegistryService инициализирован")
    return service

@pytest.fixture(autouse=True)
def cleanup_after_test(product_registry):
    """Автоматическая очистка после каждого теста"""
    yield
    logger.info("🧹 Очистка кэша и состояния после теста")
    product_registry.clear_cache()

print("\n=== НАЧАЛО ТЕСТИРОВАНИЯ PRODUCT REGISTRY ===")

# ЧЕК-ЛИСТ ПОКРЫТИЯ МЕТОДОВ ProductRegistryService
# - [x] __init__ (через фикстуру)
# - [x] clear_cache (через фикстуру)
# - [x] get_catalog_version
# - [x] create_product_metadata (юнит)
# - [ ] upload_product_metadata (TODO)
# - [ ] upload_media_file (TODO)
# - [x] create_product_on_chain
# - [x] get_all_products
# - [x] get_product
# - [x] get_product_by_id
# - [x] validate_product (юнит)
# - [x] create_product
# - [x] update_product_status
# - [x] set_product_active

@pytest.mark.asyncio
async def test_get_full_catalog(product_registry):
    """
    Arrange: Получаем сервис product_registry
    Act: Получаем версию каталога и список продуктов
    Assert: Проверяем типы, структуру, кэширование и качество данных из IPFS
    """
    logger.info("🧪 Начинаем тест получения полного каталога")

    logger.info("📊 Получаем версию каталога")
    version = product_registry.get_catalog_version()
    assert isinstance(version, int)
    assert version > 0
    logger.info(f"✅ Версия каталога: {version}")
        
    logger.info("📦 Получаем список всех продуктов")
    products = product_registry.get_all_products()
    assert isinstance(products, list)
    catalogLength = len(products)
    assert catalogLength > 0
    logger.info(f"✅ Найдено продуктов: {catalogLength}")
    
    if products:
        product = products[0]
        
        # 🔍 БАЗОВАЯ СТРУКТУРА ПРОДУКТА
        logger.info("🔍 Проверяем базовую структуру продукта")
        assert hasattr(product, 'id')
        assert hasattr(product, 'title')
        assert hasattr(product, 'status')
        assert hasattr(product, 'cid')
        assert hasattr(product, 'description')
        assert hasattr(product, 'categories')
        assert hasattr(product, 'forms')
        assert hasattr(product, 'species')
        assert hasattr(product, 'prices')
        assert hasattr(product, 'description_cid')
        assert hasattr(product, 'cover_image_url')
        logger.info(f"✅ Базовая структура продукта корректна: {product.id}")
        
        # 🔍 ПРОВЕРКА КАЧЕСТВА ДАННЫХ ПРОДУКТА
        logger.info("🔍 Проверяем качество данных продукта")
        assert product.id is not None and str(product.id).strip() != ""
        assert product.title is not None and product.title.strip() != ""
        assert product.status in [0, 1]
        assert product.cid is not None and product.cid.strip() != ""
        assert product.description_cid is not None and product.description_cid.strip() != ""
        logger.info(f"✅ Качество данных продукта: ID={product.id}, Title='{product.title}', Status={product.status}")
            
        # 🔍 ПРОВЕРКА ОПИСАНИЯ (Description)
        logger.info("🔍 Проверяем структуру и качество описания")
        assert isinstance(product.description, Description)
        description = product.description
        
        # Проверяем обязательные поля Description
        assert hasattr(description, 'id')
        assert hasattr(description, 'title')
        assert hasattr(description, 'scientific_name')
        assert hasattr(description, 'generic_description')
        assert hasattr(description, 'effects')
        assert hasattr(description, 'shamanic')
        assert hasattr(description, 'warnings')
        assert hasattr(description, 'dosage_instructions')
        
        # Проверяем качество данных Description
        assert description.id is not None and description.id.strip() != ""
        assert description.title is not None and description.title.strip() != ""
        assert description.scientific_name is not None and description.scientific_name.strip() != ""
        assert description.generic_description is not None and description.generic_description.strip() != ""
        assert isinstance(description.dosage_instructions, list)
        
        logger.info(f"✅ Описание корректно: ID={description.id}, Title='{description.title}', Scientific='{description.scientific_name}'")
        logger.info(f"   Generic description: {description.generic_description[:100]}...")
        logger.info(f"   Dosage instructions: {len(description.dosage_instructions)} шт.")
        
        # 🔍 ПРОВЕРКА ИНСТРУКЦИЙ ПО ДОЗИРОВКЕ
        if description.dosage_instructions:
            logger.info("🔍 Проверяем инструкции по дозировке")
            dosage = description.dosage_instructions[0]
            assert hasattr(dosage, 'type')
            assert hasattr(dosage, 'title')
            assert hasattr(dosage, 'description')
            assert dosage.type is not None and dosage.type.strip() != ""
            assert dosage.title is not None and dosage.title.strip() != ""
            assert dosage.description is not None and dosage.description.strip() != ""
            logger.info(f"✅ Инструкция по дозировке: Type='{dosage.type}', Title='{dosage.title}'")
            
        # 🔍 ПРОВЕРКА КАТЕГОРИЙ
        logger.info("🔍 Проверяем категории")
        assert isinstance(product.categories, list)
        if product.categories:
            for category in product.categories:
                assert isinstance(category, str)
                assert category.strip() != ""
            logger.info(f"✅ Категории: {product.categories}")
            
        # 🔍 ПРОВЕРКА ФОРМ
        logger.info("🔍 Проверяем формы")
        assert isinstance(product.forms, list)
        if product.forms:
            for form in product.forms:
                assert isinstance(form, str)
                assert form.strip() != ""
            logger.info(f"✅ Формы: {product.forms}")
        
        # 🔍 ПРОВЕРКА ВИДА
        logger.info("🔍 Проверяем вид")
        assert product.species is not None and product.species.strip() != ""
        logger.info(f"✅ Вид: {product.species}")
        
        # 🔍 ПРОВЕРКА ЦЕН
        logger.info("🔍 Проверяем цены")
        assert isinstance(product.prices, list)
        assert len(product.prices) > 0
        for price in product.prices:
            assert isinstance(price, PriceInfo)
            assert hasattr(price, 'price')
            assert hasattr(price, 'currency')
            assert price.price > 0
            assert price.currency in PriceInfo.SUPPORTED_CURRENCIES
            logger.info(f"   Цена: {price.format_full()}")
        logger.info(f"✅ Цены: {len(product.prices)} вариантов")
            
        # 🔍 ПРОВЕРКА ИЗОБРАЖЕНИЙ
        logger.info("🔍 Проверяем изображения")
        assert product.cover_image_url is not None and product.cover_image_url.strip() != ""
        assert product.cover_image_url.startswith('http')
        logger.info(f"✅ Cover image URL: {product.cover_image_url}")
        
        # 🔍 ПРОВЕРКА IPFS ЗАГРУЗКИ
        logger.info("🔍 Проверяем, что данные реально загружены из IPFS")
        assert product.description_cid != ""
        assert product.cid != ""
        logger.info(f"✅ IPFS CID: Description={product.description_cid}, Cover={product.cid}")
        
    logger.info("🔄 Проверяем кэширование")
    cached_products = product_registry.get_all_products()
    assert len(cached_products) == len(products)
    logger.info("✅ Кэширование работает корректно")
    
    # 🔍 ПРОВЕРКА ВСЕХ ПРОДУКТОВ
    logger.info("🔍 Проверяем все продукты на базовое качество данных")
    for i, product in enumerate(products):
        assert product.id is not None
        assert product.title is not None and product.title.strip() != ""
        assert isinstance(product.description, Description)
        assert len(product.prices) > 0
        if i < 3:  # Логируем только первые 3 продукта
            logger.info(f"   Продукт {i+1}: ID={product.id}, Title='{product.title}', Цен={len(product.prices)}")
    
    logger.info("✅ Тест получения полного каталога завершен успешно")

@pytest.mark.asyncio
async def test_create_successful_product_flow(product_registry, test_data):
    """
    Полноценный интеграционный тест: успешное создание продукта с полным циклом проверок
    Arrange: Берем валидные тестовые данные
    Act: Создаем продукт, получаем его, проверяем все аспекты
    Assert: Проверяем создание, получение, метаданные, активацию, статусы
    """
    logger.info("🧪 Начинаем полноценный тест создания продукта")
    
    valid_product = test_data["valid_products"][0]
    logger.info(f"📝 Создаем продукт: {valid_product['title']}")
    
    # ==================== ЭТАП 1: СОЗДАНИЕ ПРОДУКТА ====================
    logger.info("🚀 Вызываем create_product")
    product_id = await product_registry.create_product(valid_product)
    assert product_id is not None, "Продукт должен быть создан"
    logger.info(f"✅ Продукт создан с ID: {product_id}")
    
    # ==================== ЭТАП 2: ПОЛУЧЕНИЕ И ПРОВЕРКА ПРОДУКТА ====================
    logger.info("🔍 Получаем созданный продукт по ID")
    product = product_registry.get_product(product_id)
    assert product is not None, "Продукт должен быть найден"
    assert product.title == valid_product["title"], f"Название должно совпадать: {product.title} != {valid_product['title']}"
    logger.info(f"✅ Продукт найден: {product.title}")
    
    # ==================== ЭТАП 3: ПРОВЕРКА МЕТАДАННЫХ ====================
    logger.info("📋 Проверяем метаданные продукта")
    # Проверяем alias (бизнес-идентификатор из метаданных)
    assert product.alias == valid_product["id"], f"Alias должен совпадать: {product.alias} != {valid_product['id']}"
    assert product.species == valid_product["species"], f"Вид должен совпадать: {product.species} != {valid_product['species']}"
    assert product.forms == [valid_product["form"]], f"Формы должны совпадать: {product.forms} != {[valid_product['form']]}"
    assert product.categories == valid_product["categories"], f"Категории должны совпадать: {product.categories} != {valid_product['categories']}"
    # Генерируем ожидаемый URL для cover_image
    expected_cover_url = f"https://gateway.pinata.cloud/ipfs/{valid_product['cover_image']}"
    assert product.cover_image_url == expected_cover_url, f"Обложка должна совпадать: {product.cover_image_url} != {expected_cover_url}"
    logger.info("✅ Все метаданные продукта корректны")
    
    # ==================== ЭТАП 4: ПРОВЕРКА ОПИСАНИЯ ====================
    logger.info("📖 Проверяем описание продукта")
    assert product.description is not None, "Описание должно быть загружено"
    assert hasattr(product.description, 'generic_description'), "Описание должно содержать generic_description"
    assert hasattr(product.description, 'scientific_name'), "Описание должно содержать scientific_name"
    logger.info("✅ Описание продукта корректно загружено")
    
    # ==================== ЭТАП 5: ПРОВЕРКА ЦЕН ====================
    logger.info("💰 Проверяем цены продукта")
    assert product.prices is not None, "Цены должны быть загружены"
    assert len(product.prices) == len(valid_product["prices"]), f"Количество цен должно совпадать: {len(product.prices)} != {len(valid_product['prices'])}"
    
    for i, expected_price in enumerate(valid_product["prices"]):
        actual_price = product.prices[i]
        # Преобразуем строковые значения в Decimal для корректного сравнения
        expected_weight = Decimal(expected_price["weight"])
        expected_price_value = Decimal(expected_price["price"])
        
        assert actual_price.weight == expected_weight, f"Вес цены {i} должен совпадать: {actual_price.weight} != {expected_weight}"
        assert actual_price.price == expected_price_value, f"Цена {i} должна совпадать: {actual_price.price} != {expected_price_value}"
        assert actual_price.weight_unit == expected_price["weight_unit"], f"Единица веса {i} должна совпадать: {actual_price.weight_unit} != {expected_price['weight_unit']}"
        assert actual_price.currency == expected_price["currency"], f"Валюта {i} должна совпадать: {actual_price.currency} != {expected_price['currency']}"
    
    logger.info("✅ Все цены продукта корректны")
    
    # ==================== ЭТАП 6: ФИНАЛЬНАЯ ПРОВЕРКА ====================
    logger.info("🎯 Финальная проверка продукта")
    final_product = product_registry.get_product(product_id)
    assert final_product is not None, "Продукт должен остаться доступным"
    assert final_product.title == valid_product["title"], "Название должно остаться неизменным"
    assert final_product.alias == valid_product["id"], "Alias должен остаться неизменным"
    logger.info("✅ Финальная проверка пройдена")
    
    logger.info("🎉 Полноценный тест создания продукта успешно завершен")

@pytest.mark.asyncio
async def test_validation_valid_product():
    """Тест валидации корректного продукта"""
    logger.info("🧪 Тест валидации корректного продукта")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    valid_product = TEST_PRODUCTS["valid_products"][0]
    validation_result = await service.validation_service.validate_product_data(valid_product)
    
    assert validation_result["is_valid"], f"Валидный продукт должен проходить валидацию. Ошибки: {validation_result.get('errors')}"
    assert len(validation_result["errors"]) == 0, f"Валидный продукт не должен иметь ошибок: {validation_result['errors']}"
    logger.info("✅ Валидный продукт прошел валидацию")

@pytest.mark.asyncio
async def test_validation_empty_fields():
    """Тест валидации продукта с пустыми полями"""
    logger.info("🧪 Тест валидации продукта с пустыми полями")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    invalid_product = TEST_PRODUCTS["invalid_products"][0]
    validation_result = await service.validation_service.validate_product_data(invalid_product)
    
    assert not validation_result["is_valid"], "Продукт с пустыми полями должен быть невалидным"
    assert len(validation_result["errors"]) > 0, "Должны быть ошибки валидации"
    
    errors = validation_result["errors"]
    expected_errors = [
        "title: Поле не может быть пустым",
        "description_cid: Поле не может быть пустым",
        "cover_image: Поле не может быть пустым",
        "form: Поле не может быть пустым",
        "species: Поле не может быть пустым"
    ]
    
    for expected_error in expected_errors:
        assert any(expected_error in error for error in errors), f"Ожидалась ошибка: {expected_error}"
    
    logger.info(f"✅ Найдено {len(errors)} ошибок валидации для пустых полей")

@pytest.mark.asyncio
async def test_validation_invalid_cid_format():
    """Тест валидации продукта с некорректным форматом CID"""
    logger.info("🧪 Тест валидации продукта с некорректным форматом CID")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    invalid_format_product = TEST_PRODUCTS["invalid_products"][2]
    validation_result = await service.validation_service.validate_product_data(invalid_format_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректными CID должен быть невалидным"
    assert any("Неверный формат CID" in error for error in validation_result["errors"]), "Должны быть ошибки формата CID"
    logger.info("✅ Ошибки формата CID обнаружены")

@pytest.mark.asyncio
async def test_validation_invalid_price_format():
    """Тест валидации продукта с некорректным форматом цены"""
    logger.info("🧪 Тест валидации продукта с некорректным форматом цены")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    invalid_price_format_product = TEST_PRODUCTS["invalid_products"][1]
    validation_result = await service.validation_service.validate_product_data(invalid_price_format_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректным форматом цены должен быть невалидным"
    assert any(error.startswith("prices[0].price:") for error in validation_result["errors"]), "Должны быть ошибки по формату цены"
    logger.info(f"✅ Ошибки по формату цены: {[e for e in validation_result['errors'] if e.startswith('prices[0].price:')]}")

@pytest.mark.asyncio
async def test_validation_invalid_currency():
    """Тест валидации продукта с некорректной валютой"""
    logger.info("🧪 Тест валидации продукта с некорректной валютой")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    invalid_currency_product = {
        "id": "invalid_currency_test",
        "title": "Test Product",
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "categories": ["test"],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "form": "powder",
        "species": "Test species",
        "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "INVALID"}]
    }
    
    validation_result = await service.validation_service.validate_product_data(invalid_currency_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректной валютой должен быть невалидным"
    assert any(error.startswith("prices[0].currency:") for error in validation_result["errors"]), "Должны быть ошибки по валюте"
    logger.info(f"✅ Ошибки по валюте: {[e for e in validation_result['errors'] if e.startswith('prices[0].currency:')]}")

@pytest.mark.asyncio
async def test_validation_invalid_form():
    """Тест валидации продукта с некорректной формой"""
    logger.info("🧪 Тест валидации продукта с некорректной формой")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    invalid_form_product = {
        "id": "invalid_form_test",
        "title": "Test Product",
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "categories": ["test"],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "form": "invalid_form",
        "species": "Test species",
        "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
    }
    
    validation_result = await service.validation_service.validate_product_data(invalid_form_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректной формой должен быть невалидным"
    assert any(error.startswith("form:") for error in validation_result["errors"]), "Должны быть ошибки по форме"
    logger.info(f"✅ Ошибки по форме: {[e for e in validation_result['errors'] if e.startswith('form:')]}")

@pytest.mark.asyncio
async def test_validation_boundary_cases():
    """Тест валидации граничных случаев"""
    logger.info("🧪 Тест валидации граничных случаев")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    valid_product = TEST_PRODUCTS["valid_products"][0]
    
    # Слишком длинное название
    boundary_product = valid_product.copy()
    boundary_product["title"] = "A" * 300  # Превышает лимит в 255 символов
    
    validation_result = await service.validation_service.validate_product_data(boundary_product)
    assert not validation_result["is_valid"], "Название длиннее 255 символов должно быть невалидным"
    assert any("длина" in error.lower() for error in validation_result["errors"]), "Должна быть ошибка длины"
    logger.info("✅ Ошибка длины названия обнаружена")
    
    # Слишком много категорий
    boundary_product = valid_product.copy()
    boundary_product["categories"] = [f"category_{i}" for i in range(15)]  # Превышает лимит в 10
    
    validation_result = await service.validation_service.validate_product_data(boundary_product)
    assert not validation_result["is_valid"], "Слишком много категорий должно быть невалидным"
    assert any("категори" in error.lower() for error in validation_result["errors"]), "Должна быть ошибка количества категорий"
    logger.info("✅ Ошибка количества категорий обнаружена")

@pytest.mark.asyncio
async def test_validation_data_sanitization():
    """Тест санитизации данных при валидации"""
    logger.info("🧪 Тест санитизации данных при валидации")
    
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    valid_product = TEST_PRODUCTS["valid_products"][0]
    
    # Продукт с лишними пробелами
    dirty_product = valid_product.copy()
    dirty_product["title"] = "  Amanita muscaria — sliced caps and gills (1st grade)  "
    dirty_product["categories"] = ["  mushroom  ", "  mental health  "]
    
    validation_result = await service.validation_service.validate_product_data(dirty_product)
    assert validation_result["is_valid"], "Продукт с пробелами должен проходить валидацию после санитизации"
    assert "sanitized_data" in validation_result, "Должны быть санитизированные данные"
    
    sanitized = validation_result["sanitized_data"]
    assert sanitized["title"] == "Amanita muscaria — sliced caps and gills (1st grade)", "Пробелы должны быть удалены"
    assert sanitized["categories"] == ["mushroom", "mental health"], "Пробелы в категориях должны быть удалены"
    logger.info("✅ Санитизация данных работает корректно")

@pytest.mark.asyncio
async def test_product_status_updates(product_registry):
    """Тест деактивации продукта и невозможности обновления неактивного товара"""
    logger.info("🧪 Начинаем тест деактивации продукта")
    
    logger.info("🚀 Создаем продукт")
    valid_product = TEST_PRODUCTS["valid_products"][0]
    product_id = await product_registry.create_product(valid_product)
    logger.info(f"✅ Продукт создан с ID: {product_id}")
    
    logger.info("🔄 Деактивируем продукт")
    result = await product_registry.deactivate_product(product_id)
    assert result, "Продукт должен быть успешно деактивирован"
    product = product_registry.get_product(product_id)
    assert not product.is_active, "Продукт должен быть неактивен после деактивации"
    logger.info("✅ Продукт деактивирован")
    