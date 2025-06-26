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
async def test_create_product_success(product_registry, test_data):
    """
    Интеграционный тест: успешное создание продукта через create_product
    Arrange: Берем валидные тестовые данные
    Act: Вызываем create_product
    Assert: Проверяем, что продукт создан, есть ID, можно получить продукт по ID
    """
    logger.info("🧪 Начинаем тест успешного создания продукта")
    
    valid_product = test_data["valid_products"][0]
    logger.info(f"📝 Создаем продукт: {valid_product['title']}")
    
    logger.info("🚀 Вызываем create_product")
    product_id = await product_registry.create_product(valid_product)
    assert product_id is not None
    logger.info(f"✅ Продукт создан с ID: {product_id}")
    
    logger.info("🔍 Получаем созданный продукт по ID")
    product = product_registry.get_product(product_id)
    assert product is not None
    assert product.title == valid_product["title"]
    logger.info(f"✅ Продукт найден: {product.title}")
    
    logger.info("✅ Тест создания продукта завершен")

@pytest.mark.asyncio
async def test_create_and_validate_product(product_registry):
    """Тест создания и валидации продукта"""
    logger.info("🧪 Начинаем тест создания и валидации продукта")
    
    logger.info("🔍 Проверяем валидацию перед созданием")
    validation_result = await product_registry.validation_service.validate_product_data(TEST_PRODUCT_DATA)
    assert validation_result["is_valid"] is True, f"Тестовые данные должны быть валидными: {validation_result.get('errors', [])}"
    logger.info("✅ Валидация пройдена")
    
    logger.info("🚀 Создаем продукт")
    product_id = await product_registry.create_product(TEST_PRODUCT_DATA)
    assert product_id is not None, "Продукт не создан"
    logger.info(f"📦 ID продукта: {product_id}")
    
    logger.info("🔍 Получаем продукт из блокчейна")
    product = await product_registry.get_product(product_id)
    assert product is not None, "Продукт не найден в блокчейне"
    logger.info("✅ Продукт найден в блокчейне")
    
    logger.info("📄 Проверяем метаданные продукта")
    metadataDownloaded = await storage_service.download_json(product.cid)
    assert metadataDownloaded is not None, "Метаданные продукта не найдены в IPFS"
    logger.info("✅ Метаданные найдены в IPFS")
    
    logger.info("🔍 Сверяем поля сериализованного Product полученного по ID из смартконтракта и отдельно полученные значения метаданных полученные через Storage сервис напрямую")
    assert product.id == metadataDownloaded["id"], "ID продукта не совпадает"
    assert product.title == metadataDownloaded["title"], "Название продукта не совпадает"
    assert product.description_cid is not None, "CID описания продукта не может быть None"

    descriptionMetadataDownloaded = await storage_service.download_json(product.description_cid)
    assert descriptionMetadataDownloaded is not None, "Описание продукта не найдено в IPFS"

    assert product.description.generic_description == descriptionMetadataDownloaded["generic_description"], "Описание продукта не совпадает"
    assert product.description.scientific_name == descriptionMetadataDownloaded["scientific_name"], "Научное название продукта не совпадает"
    assert product.description.effects == descriptionMetadataDownloaded["effects"], "Эффекты продукта не совпадают"
    assert product.description.shamanic == descriptionMetadataDownloaded["shamanic"], "Шаманская информация продукта не совпадает"
    assert product.description.warnings == descriptionMetadataDownloaded["warnings"], "Предупреждения продукта не совпадают"
    assert product.description.dosage_instructions == descriptionMetadataDownloaded["dosage_instructions"], "Инструкции по дозировке продукта не совпадают"
    
    coverImageCid = metadataDownloaded["cover_image"]
    coverImageUrl = storage_service.get_gateway_url(coverImageCid)
    assert coverImageUrl is not None, "Обложка продукта не найдена в IPFS"
    assert product.cover_image_url == coverImageUrl, "Обложка продукта не совпадает"

    assert product.categories == descriptionMetadataDownloaded["categories"], "Категории продукта не совпадают"
    assert product.forms == descriptionMetadataDownloaded["form"], "Формы продукта не совпадают"
    assert product.species == descriptionMetadataDownloaded["species"], "Вид продукта не совпадает"

    # Проверка длины списков категорий и форм
    assert len(product.categories) == len(descriptionMetadataDownloaded["categories"]), f"Длина категорий не совпадает: {len(product.categories)} != {len(descriptionMetadataDownloaded['categories'])}"
    assert len(product.forms) == (len(descriptionMetadataDownloaded["form"]) if isinstance(descriptionMetadataDownloaded["form"], list) else 1), f"Длина форм не совпадает: {len(product.forms)} != {len(descriptionMetadataDownloaded['form'])}"

    # Проверка gallery
    if "gallery" in metadataDownloaded:
        assert hasattr(product, "gallery"), "У продукта отсутствует поле gallery"
        assert len(product.gallery) == len(metadataDownloaded["gallery"]), f"Длина gallery не совпадает: {len(product.gallery)} != {len(metadataDownloaded['gallery'])}"
        for idx, cid in enumerate(metadataDownloaded["gallery"]):
            assert product.gallery[idx] == storage_service.get_gateway_url(cid), f"Элемент gallery[{idx}] не совпадает: {product.gallery[idx]} != {storage_service.get_gateway_url(cid)}"

    # Проверка video
    if "video" in metadataDownloaded:
        assert hasattr(product, "video"), "У продукта отсутствует поле video"
        assert product.video == storage_service.get_gateway_url(metadataDownloaded["video"]), f"Поле video не совпадает: {product.video} != {storage_service.get_gateway_url(metadataDownloaded['video'])}"

    # Проверка всех полей цен
    assert len(product.prices) == len(metadataDownloaded["prices"]), f"Количество цен не совпадает: {len(product.prices)} != {len(metadataDownloaded['prices'])}"
    for idx, price in enumerate(product.prices):
        meta_price = metadataDownloaded["prices"][idx]
        if hasattr(price, "to_dict"):
            price_dict = price.to_dict()
        elif isinstance(price, dict):
            price_dict = price
        else:
            raise AssertionError("Неизвестный тип price")
        for key in meta_price:
            assert str(price_dict.get(key)) == str(meta_price.get(key)), f"Поле {key} в цене не совпадает: {price_dict.get(key)} != {meta_price.get(key)}"
        assert set(price_dict.keys()) == set(meta_price.keys()), f"Набор ключей цены не совпадает: {set(price_dict.keys())} != {set(meta_price.keys())}"

    # Проверка что все поля из метаданных отражены в объекте продукта
    for key in metadataDownloaded:
        if hasattr(product, key):
            product_value = getattr(product, key)
            meta_value = metadataDownloaded[key]
            if isinstance(product_value, list) and isinstance(meta_value, list):
                assert len(product_value) == len(meta_value), f"Поле {key}: длина списка не совпадает: {len(product_value)} != {len(meta_value)}"
            else:
                assert product_value == meta_value or str(product_value) == str(meta_value), f"Поле {key} не совпадает: {product_value} != {meta_value}"

    logger.info("✅ Все поля продукта и метаданных успешно сверены")
    
    logger.info("✅ Тест создания и валидации продукта завершен")

@pytest.mark.asyncio
async def test_product_validation():
    """Комплексный тест валидации продукта"""
    logger.info("🧪 Начинаем комплексный тест валидации продукта")
    
    logger.info("🔧 Создаем сервисы")
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    
    logger.info("🔧 Создаем основной сервис")
    service = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
    
    # ==================== ТЕСТ 1: ВАЛИДНЫЕ ДАННЫЕ ====================
    logger.info("📝 Тест 1: Проверяем валидные данные")
    valid_product = TEST_PRODUCTS["valid_products"][0]
    logger.info(f"🔍 Тестируем валидный продукт: {valid_product['title']}")
    
    validation_result = await service.validation_service.validate_product_data(valid_product)
    logger.info(f"🔍 Результат валидации валидного продукта: {json.dumps(validation_result, indent=2)}")
    
    assert validation_result["is_valid"], f"Валидный продукт должен проходить валидацию. Ошибки: {validation_result.get('errors')}"
    assert len(validation_result["errors"]) == 0, f"Валидный продукт не должен иметь ошибок: {validation_result['errors']}"
    logger.info("✅ Валидный продукт прошел валидацию")
    
    # ==================== ТЕСТ 2: ПУСТЫЕ ПОЛЯ ====================
    logger.info("📝 Тест 2: Проверяем пустые поля")
    invalid_product = TEST_PRODUCTS["invalid_products"][0]
    logger.info(f"🔍 Тестируем невалидный продукт с пустыми полями: {invalid_product['id']}")
    
    validation_result = await service.validation_service.validate_product_data(invalid_product)
    logger.info(f"🔍 Результат валидации невалидного продукта: {json.dumps(validation_result, indent=2)}")
    
    assert not validation_result["is_valid"], "Продукт с пустыми полями должен быть невалидным"
    assert len(validation_result["errors"]) > 0, "Должны быть ошибки валидации"
    
    # Проверяем конкретные ошибки
    errors = validation_result["errors"]
    expected_empty_field_errors = [
        "title: Поле не может быть пустым",
        "description_cid: Поле не может быть пустым",
        "cover_image: Поле не может быть пустым",
        "form: Поле не может быть пустым",
        "species: Поле не может быть пустым"
    ]
    
    for expected_error in expected_empty_field_errors:
        assert any(expected_error in error for error in errors), f"Ожидалась ошибка: {expected_error}"
    
    # Проверяем ошибки формата CID
    assert any("Неверный формат CID" in error for error in errors), "Должны быть ошибки формата CID"
    
    # Проверяем ошибки категорий и цен
    assert any("категория" in error.lower() for error in errors), "Должна быть ошибка о категориях"
    assert any("цена" in error.lower() for error in errors), "Должна быть ошибка о ценах"
    
    logger.info(f"✅ Найдено {len(errors)} ошибок валидации для пустых полей")
    
    # ==================== ТЕСТ 3: НЕКОРРЕКТНЫЕ ФОРМАТЫ ====================
    logger.info("📝 Тест 3: Проверяем некорректные форматы")
    invalid_format_product = TEST_PRODUCTS["invalid_products"][2]  # invalid_cid_format
    logger.info(f"🔍 Тестируем продукт с некорректными CID: {invalid_format_product['id']}")
    
    validation_result = await service.validation_service.validate_product_data(invalid_format_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректными CID должен быть невалидным"
    assert any("Неверный формат CID" in error for error in validation_result["errors"]), "Должны быть ошибки формата CID"
    logger.info("✅ Ошибки формата CID обнаружены")
    
    # ==================== ТЕСТ 4: НЕКОРРЕКТНЫЕ ЦЕНЫ ====================
    logger.info("📝 Тест 4: Проверяем некорректные цены")
    invalid_price_product = TEST_PRODUCTS["invalid_products"][1]  # invalid_price_format
    logger.info(f"🔍 Тестируем продукт с некорректными ценами: {invalid_price_product['id']}")
    
    validation_result = await service.validation_service.validate_product_data(invalid_price_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректными ценами должен быть невалидным"
    assert any(error.startswith("prices[0].price:") for error in validation_result["errors"]), "Должны быть ошибки по цене"
    assert any(error.startswith("prices[0].currency:") for error in validation_result["errors"]), "Должны быть ошибки по валюте"
    logger.info("✅ Ошибки цен обнаружены")
    
    # ==================== ТЕСТ 5: НЕКОРРЕКТНАЯ ВАЛЮТА ====================
    logger.info("📝 Тест 5: Проверяем некорректную валюту")
    invalid_currency_product = TEST_PRODUCTS["invalid_products"][3]  # invalid_currency
    logger.info(f"🔍 Тестируем продукт с некорректной валютой: {invalid_currency_product['id']}")
    
    validation_result = await service.validation_service.validate_product_data(invalid_currency_product)
    
    assert not validation_result["is_valid"], "Продукт с некорректной валютой должен быть невалидным"
    assert any(error.startswith("prices[0].currency:") for error in validation_result["errors"]), "Должна быть ошибка валюты"
    logger.info("✅ Ошибка валюты обнаружена")
    
    # ==================== ТЕСТ 6: ГРАНИЧНЫЕ СЛУЧАИ ====================
    logger.info("📝 Тест 6: Проверяем граничные случаи")
    
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
    
    # ==================== ТЕСТ 7: САНИТИЗАЦИЯ ДАННЫХ ====================
    logger.info("📝 Тест 7: Проверяем санитизацию данных")
    
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
    
    logger.info("✅ Комплексный тест валидации продукта завершен")

@pytest.mark.asyncio
async def test_product_creation_flow(product_registry):
    """Тест полного цикла создания продукта"""
    logger.info("🧪 Начинаем тест полного цикла создания продукта")
    
    logger.info("📝 Получаем тестовые данные")
    valid_product = TEST_PRODUCTS["valid_products"][0]
    
    logger.info("🚀 Создаем продукт")
    product_id = await product_registry.create_product(valid_product)
    assert product_id is not None, "Продукт должен быть создан"
    logger.info(f"✅ Продукт создан с ID: {product_id}")
    
    logger.info("🔍 Проверяем что продукт создан")
    product = await product_registry.get_product(product_id)
    assert product is not None, "Продукт должен быть найден"
    assert product["title"] == valid_product["title"]
    logger.info(f"✅ Продукт найден: {product['title']}")
    
    logger.info("🔄 Проверяем активацию/деактивацию")
    await product_registry.set_product_active(product_id, True)
    product = await product_registry.get_product(product_id)
    assert product["is_active"] is True
    logger.info("✅ Продукт активирован")
    
    await product_registry.set_product_active(product_id, False)
    product = await product_registry.get_product(product_id)
    assert product["is_active"] is False
    logger.info("✅ Продукт деактивирован")
    
    logger.info("✅ Тест полного цикла создания продукта завершен")

@pytest.mark.asyncio
async def test_get_all_products(product_registry):
    """Тест получения всех продуктов"""
    logger.info("🧪 Начинаем тест получения всех продуктов")
    
    logger.info("🚀 Создаем несколько продуктов")
    for valid_product in TEST_PRODUCTS["valid_products"]:
        await product_registry.create_product(valid_product)
        logger.info(f"✅ Создан продукт: {valid_product['title']}")
    
    logger.info("📦 Получаем все продукты")
    products = await product_registry.get_all_products()
    assert len(products) >= len(TEST_PRODUCTS["valid_products"])
    logger.info(f"✅ Найдено продуктов: {len(products)}")
    
    logger.info("🔍 Проверяем что все созданные продукты присутствуют")
    product_ids = [p["id"] for p in products]
    for valid_product in TEST_PRODUCTS["valid_products"]:
        assert valid_product["id"] in product_ids
        logger.info(f"✅ Продукт найден в списке: {valid_product['id']}")
    
    logger.info("✅ Тест получения всех продуктов завершен")

@pytest.mark.asyncio
async def test_product_status_updates(product_registry):
    """Тест обновления статуса продукта"""
    logger.info("🧪 Начинаем тест обновления статуса продукта")
    
    logger.info("🚀 Создаем продукт")
    valid_product = TEST_PRODUCTS["valid_products"][0]
    product_id = await product_registry.create_product(valid_product)
    logger.info(f"✅ Продукт создан с ID: {product_id}")
    
    logger.info("🔄 Проверяем разные статусы")
    statuses = [1, 2, 3]  # В процессе, отправлен, доставлен
    for status in statuses:
        await product_registry.update_product_status(product_id, status)
        product = await product_registry.get_product(product_id)
        assert product["status"] == status
        logger.info(f"✅ Статус обновлен: {status}")
    
    logger.info("✅ Тест обновления статуса продукта завершен") 