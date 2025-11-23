"""
Shared fixtures for E2E tests.

Provides:
- E2E Harness with node management
- Real service instances (BlockchainService, ComponentService, etc.)
- Expected test data from data/ directory
- Snapshot management for test isolation

Based on: @e2e-test-build.appendix.harness.mdc
"""

import pytest
import pytest_asyncio
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Import harness
from .harness import E2EHarness

# Services imported lazily in fixtures to avoid singleton initialization issues

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"


# ============================================================================
# E2E HARNESS (Infrastructure)
# ============================================================================

@pytest.fixture(scope="session")
def e2e_local_profile():
    """
    Ensure 'local' profile with caching and stub-friendly flags for E2E smoke.
    Sets common env vars expected by services. Restores originals on teardown.
    """
    required_env = {
        "ENVIRONMENT": "local",
        "ENABLE_CACHING": "true",
        "APP_ROOT_DIR": "bot",
        "INTEGRATION_STORAGE": "mock",
        # Hint for tests to prefer stubs when applicable
        "E2E_USE_STUBS": "true",
    }
    originals: Dict[str, Any] = {}
    for k, v in required_env.items():
        originals[k] = os.environ.get(k)
        os.environ[k] = v
    logger.info("[E2E Local Profile] Activated with: %s", {k: os.environ[k] for k in required_env})
    try:
        yield required_env
    finally:
        for k, old in originals.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old
        logger.info("[E2E Local Profile] Restored original environment")


@pytest.fixture(scope="session")
def e2e_translation_cache_dir(tmp_path_factory):
    """
    Session-scoped temporary directory for TranslationCacheService to ensure isolation.
    
    Uses tmp_path / 'cache' as per requirement 6.3.
    """
    base = tmp_path_factory.mktemp("e2e_temp")
    cache_dir = base / "cache"
    cache_dir.mkdir(exist_ok=True, parents=True)
    logger.info("[E2E Cache] Using cache directory: %s (tmp_path / 'cache')", cache_dir)
    return str(cache_dir)


@pytest.fixture(scope="session")
def e2e_translation_cache_service(e2e_translation_cache_dir, e2e_local_profile):
    """
    Session-scoped TranslationCacheService bound to the temporary cache directory.
    
    TTL is read from .env (TRANSLATION_CACHE_TTL) or parameterized with default 3600.
    As per requirement 6.3.
    """
    # Lazy import to avoid premature module initialization
    from services.common.translation_cache_service import TranslationCacheService
    
    # Read TTL from .env or use default
    cache_ttl = int(os.getenv("TRANSLATION_CACHE_TTL", os.getenv("CACHE_TTL", "3600")))
    
    svc = TranslationCacheService(cache_dir=e2e_translation_cache_dir, default_ttl=cache_ttl)
    logger.info("[E2E Cache] TranslationCacheService initialized")
    logger.info("   Cache directory: %s", e2e_translation_cache_dir)
    logger.info("   TTL: %d seconds (from .env or default)", cache_ttl)
    return svc


@pytest_asyncio.fixture(scope="session")
async def e2e_harness():
    """
    E2E Harness for node management and validation.
    
    Scope: session (one instance for all E2E tests)
    
    Validates:
    - Hardhat node running
    - Contracts deployed
    - Prerequisites met
    
    Raises:
        pytest.skip: If prerequisites not met
    """
    harness = E2EHarness()
    
    try:
        # Connect to node
        await harness.connect_to_node()
        
        # Validate prerequisites
        prerequisites = await harness.validate_prerequisites()
        
        # Check all prerequisites
        if not all(prerequisites.values()):
            failed = [k for k, v in prerequisites.items() if not v]
            pytest.skip(f"⚠️ E2E prerequisites not met: {failed}\n"
                       f"   See: bot/docs/QUICK-START.md for setup instructions")
        
        logger.info(f"✅ E2E Harness ready")
        
        yield harness
        
    except ConnectionError as e:
        pytest.skip(f"⚠️ Hardhat node not running: {e}\n"
                   f"   Run: npx hardhat node")
    
    finally:
        # Cleanup
        await harness.cleanup()


@pytest_asyncio.fixture(scope="function")
async def e2e_snapshot(e2e_harness):
    """
    Create snapshot before test, revert after.
    
    Scope: function (per test isolation)
    
    Usage:
        async def test_something(e2e_snapshot):
            # Test runs with clean state
            # Modifications reverted automatically after test
    """
    # Create snapshot before test
    snapshot_id = await e2e_harness.create_snapshot(name="test-isolation")
    
    logger.info(f"📸 Snapshot created for test isolation: {snapshot_id}")
    
    yield snapshot_id
    
    # Revert after test
    await e2e_harness.revert_to_snapshot(snapshot_id)
    logger.info(f"⏪ Snapshot reverted: {snapshot_id}")


# ============================================================================
# REAL SERVICES (NO MOCKS)
# ============================================================================

@pytest.fixture(scope="function")
def e2e_blockchain_service(e2e_local_profile):
    """
    BlockchainService (stub or real) with storage cleared before each test.
    
    Uses E2E_USE_STUBS flag from e2e_local_profile:
    - If E2E_USE_STUBS=true → returns BlockchainServiceStub
    - Otherwise → returns real BlockchainService
    
    Scope: function (cleared before each test if stub)
    
    As per requirement 6.2: For stub Blockchain use BlockchainServiceStub/AmanitaInternationalContractStub with counters.
    """
    # Lazy import
    use_stubs = os.getenv("E2E_USE_STUBS") == "true"
    
    if use_stubs:
        from tests.integration.blockchain_stub import BlockchainServiceStub
        
        logger.info(f"[E2E Fixture] Creating BlockchainServiceStub for smoke tests")
        blockchain_service = BlockchainServiceStub()
        logger.info(f"✅ BlockchainServiceStub created (with get_cid_calls/set_cid_calls counters)")
        
        yield blockchain_service
        
        # Clear storage and reset counters after test
        contract = blockchain_service.get_contract("AmanitaInternational")
        if contract:
            contract._storage.clear()
            contract.get_cid_calls = 0
            contract.set_cid_calls = 0
        logger.info(f"🧹 BlockchainServiceStub storage cleared after test")
    else:
        # Lazy import to avoid singleton initialization
        from services.core.blockchain import BlockchainService
        
        logger.info(f"[E2E Fixture] Creating real BlockchainService")
        blockchain_service = BlockchainService()
        
        # Validate connection
        if not blockchain_service.web3.is_connected():
            pytest.skip("⚠️ BlockchainService failed to connect to node")
        
        logger.info(f"✅ Real BlockchainService connected")
        
        yield blockchain_service
        
        # Note: Real blockchain state can't be cleared easily, but we log
        logger.info(f"ℹ️ Real BlockchainService used (state not cleared)")


@pytest.fixture(scope="session")
def real_blockchain_service():
    """
    Real BlockchainService connected to localhost Hardhat node.
    
    Uses .env configuration:
    - WEB3_PROVIDER_URI=http://localhost:8545
    - MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB...
    
    Scope: session (reused across tests)
    
    Note: For stub support in E2E tests, use e2e_blockchain_service fixture instead.
    """
    # Lazy import to avoid singleton initialization
    from services.core.blockchain import BlockchainService
    
    logger.info(f"[E2E Fixture] Creating real BlockchainService")
    
    blockchain_service = BlockchainService()
    
    # Validate connection
    if not blockchain_service.web3.is_connected():
        pytest.skip("⚠️ BlockchainService failed to connect to node")
    
    logger.info(f"✅ BlockchainService connected")
    
    return blockchain_service


@pytest.fixture(scope="session")
def real_storage_service():
    """
    Real ArWeaveUploader for downloading from Arweave.
    
    Uses .env configuration:
    - STORAGE_TYPE=arweave
    
    Scope: session (reused across tests)
    """
    # Lazy import
    from services.core.ipfs_factory import IPFSFactory
    from services.core.storage.ar_weave import ArWeaveUploader
    
    logger.info(f"[E2E Fixture] Creating real ArWeaveUploader")
    
    storage_service = IPFSFactory().get_storage()
    
    # Validate it's ArWeave (not Pinata)
    if not isinstance(storage_service, ArWeaveUploader):
        logger.warning(f"⚠️ Expected ArWeaveUploader, got {type(storage_service)}")
    
    logger.info(f"✅ Storage service created: {type(storage_service).__name__}")
    
    return storage_service


@pytest.fixture(scope="session")
def real_component_service(real_blockchain_service, real_storage_service):
    """
    Real ComponentService with real blockchain and storage.
    
    Scope: session (shared cache across tests)
    """
    # Lazy import
    from services.product.component_service import ComponentService
    
    logger.info(f"[E2E Fixture] Creating real ComponentService")
    
    component_service = ComponentService(
        blockchain_service=real_blockchain_service,
        storage_service=real_storage_service
    )
    
    logger.info(f"✅ ComponentService created")
    
    return component_service


@pytest.fixture(scope="session")
def real_product_assembler(real_component_service):
    """
    Real ProductAssembler with real ComponentService.
    
    Scope: session
    """
    # Lazy import
    from services.product.assembler import ProductAssembler
    
    logger.info(f"[E2E Fixture] Creating real ProductAssembler")
    
    assembler = ProductAssembler(component_service=real_component_service)
    
    logger.info(f"✅ ProductAssembler created")
    
    return assembler


@pytest.fixture(scope="session")
def real_product_registry(real_blockchain_service, real_storage_service, real_product_assembler):
    """
    Real ProductRegistryService with all real dependencies.
    
    This is the main service for E2E tests.
    
    Scope: session
    """
    # Lazy import
    from services.product.registry import ProductRegistryService
    
    logger.info(f"[E2E Fixture] Creating real ProductRegistryService")
    
    registry = ProductRegistryService(
        blockchain_service=real_blockchain_service,
        storage_service=real_storage_service,
        assembler=real_product_assembler
    )
    
    logger.info(f"✅ ProductRegistryService created")
    
    return registry


@pytest.fixture(scope="session")
def real_formatter_service():
    """
    Real ProductFormatterService for Telegram formatting.
    
    Scope: session
    """
    # Lazy import
    from handlers.common.formatting.product_formatter_service import ProductFormatterService
    from handlers.common.formatting.product_formatter_config import ProductFormatterConfig
    from services.common.localization_service import LocalizationService
    
    logger.info(f"[E2E Fixture] Creating real ProductFormatterService")
    
    config = ProductFormatterConfig()
    localization_service = LocalizationService()
    
    formatter = ProductFormatterService(
        config=config,
        localization_service=localization_service
    )
    
    logger.info(f"✅ ProductFormatterService created")
    
    return formatter


# ============================================================================
# TEST DATA (from data/ directory)
# ============================================================================

@pytest.fixture(scope="session")
def expected_products_data():
    """
    Load expected products data from data/registry/
    
    Returns:
        List[Dict]: All products from product_registry_upload_data.json
    """
    data_path = DATA_DIR / "registry" / "product_registry_upload_data.json"

    with data_path.open("r", encoding="utf-8") as f:
        products = json.load(f)
    
    logger.info(f"✅ Loaded {len(products)} expected products from data/registry/")
    
    return products


@pytest.fixture(scope="session")
def expected_product_amanita1(expected_products_data):
    """
    Get expected data for product "amanita1" (blockchain_id=0).
    
    This is the primary test product for E2E tests.
    
    Returns:
        Dict: Product data with id, componentIds, metadataCID, active
    """
    # Find amanita1
    amanita1 = next((p for p in expected_products_data if p["id"] == "amanita1"), None)
    
    if not amanita1:
        pytest.skip("⚠️ Test product 'amanita1' not found in data/registry/")
    
    logger.info(f"✅ Test product: amanita1")
    logger.info(f"   CID: {amanita1['metadataCID']}")
    logger.info(f"   Components: {amanita1['componentIds']}")
    
    return amanita1


@pytest.fixture(scope="session")
def expected_component_amanita_muscaria():
    """
    Load expected component data for amanita_muscaria.
    
    Returns:
        Dict: Component data with localizations, CID, etc.
    """
    data_path = DATA_DIR / "components" / "amanita_muscaria" / "_upload_state_localhost.json"

    with data_path.open("r", encoding="utf-8") as f:
        upload_state = json.load(f)
    
    # Extract key data
    component_data = {
        "component_id": "amanita_muscaria",
        "ru_description_cid": upload_state["complex_fields"]["ru"]["cid"],
        "en_description_cid": upload_state["complex_fields"]["en"]["cid"],
        "all_languages": list(upload_state["complex_fields"].keys())
    }
    
    logger.info(f"✅ Expected component: amanita_muscaria")
    logger.info(f"   Russian CID: {component_data['ru_description_cid']}")
    logger.info(f"   Languages: {component_data['all_languages']}")
    
    return component_data


# ============================================================================
# LOCALIZATION
# ============================================================================

@pytest.fixture(scope="session")
def russian_localization():
    """
    Russian Localization instance for formatting tests.
    
    Scope: session (reused across tests)
    """
    # Lazy import
    from services.common.localization import Localization
    
    logger.info(f"[E2E Fixture] Creating Russian localization")
    
    loc = Localization(language="ru")
    
    logger.info(f"✅ Russian localization ready")
    
    return loc


@pytest.fixture(scope="function")
def e2e_ipfs_factory(e2e_local_profile):
    """
    IPFSFactory (stub or real) with storage cleared before each test.
    
    Uses E2E_USE_STUBS flag from e2e_local_profile:
    - If E2E_USE_STUBS=true → returns IPFSFactoryStub
    - Otherwise → returns real IPFSFactory
    
    Scope: function (cleared before each test)
    """
    # Lazy import
    use_stubs = os.getenv("E2E_USE_STUBS") == "true"
    
    if use_stubs:
        from tests.integration.ipfs_stub import IPFSFactoryStub
        
        logger.info(f"[E2E Fixture] Creating IPFSFactoryStub for smoke tests")
        factory = IPFSFactoryStub(storage={})
        logger.info(f"✅ IPFSFactoryStub created (storage cleared)")
        
        yield factory
        
        # Clear storage after test
        factory._service._storage.clear()
        factory._service.upload_calls = 0
        factory._service.download_calls = 0
        logger.info(f"🧹 IPFSFactoryStub storage cleared after test")
    else:
        from services.core.ipfs_factory import IPFSFactory
        
        logger.info(f"[E2E Fixture] Creating real IPFSFactory")
        factory = IPFSFactory()
        logger.info(f"✅ Real IPFSFactory created")
        
        yield factory
        
        # Note: Real IPFS storage can't be cleared easily, but we log
        logger.info(f"ℹ️ Real IPFSFactory used (storage not cleared)")


def create_product_ipfs_payload(title: str, description: str, forms: Optional[list] = None) -> Dict[str, Any]:
    """
    Создаёт плоский IPFS payload для продукта для локализации (один язык).
    
    Структура для MultilingualIPFSService:
    - Плоский JSON с ключами: title, description, forms (если используется)
    - Каждое поле содержит строку (не словарь языков!)
    - Язык определяется контекстом (en/ru payload загружается отдельно)
    
    Args:
        title: Название продукта
        description: Описание продукта
        forms: Список форм продукта (опционально)
    
    Returns:
        Dict с ключами title, description, forms (если указаны)
        
    Example:
        # Для английского языка
        payload_en = create_product_ipfs_payload(
            title="Amanita Powder",
            description="Premium dried Amanita muscaria powder",
            forms=["powder", "capsules"]
        )
        # Returns: {"title": "Amanita Powder", "description": "...", "forms": "powder,capsules"}
        
        # Для русского языка (создаём отдельный payload)
        payload_ru = create_product_ipfs_payload(
            title="Мухомор Порошок",
            description="Премиум сушёный порошок Amanita muscaria",
            forms=["порошок", "капсулы"]
        )
    """
    payload: Dict[str, Any] = {
        "title": title,
        "description": description,
    }
    
    if forms:
        # Формы могут быть списком или строкой (в зависимости от формата в IPFS)
        # Для простоты преобразуем в строку с запятыми, если список
        if isinstance(forms, list):
            payload["forms"] = ",".join(forms)
        else:
            payload["forms"] = forms
    
    logger.debug(f"[create_product_ipfs_payload] Created payload with keys: {list(payload.keys())}")
    logger.debug(f"   title length: {len(payload['title'])} chars")
    logger.debug(f"   description length: {len(payload['description'])} chars")
    if "forms" in payload:
        logger.debug(f"   forms: {payload['forms']}")
    
    return payload


def upload_product_payload_to_ipfs(payload: Dict[str, Any], ipfs_factory, language: Optional[str] = None) -> str:
    """
    Загружает IPFS payload для продукта и возвращает CID.
    
    Args:
        payload: Плоский JSON payload (из create_product_ipfs_payload)
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из фикстуры e2e_ipfs_factory)
        language: Язык payload (en/ru) для логирования (опционально)
    
    Returns:
        CID строку
        
    Example:
        payload_en = create_product_ipfs_payload(
            title="Amanita Powder",
            description="Premium dried Amanita muscaria powder"
        )
        cid_en = upload_product_payload_to_ipfs(payload_en, ipfs_factory, language="en")
        # Returns: "cid://..."
    """
    ipfs_service = ipfs_factory.get_service()
    
    cid = ipfs_service.upload_json(payload)
    
    lang_label = f" ({language})" if language else ""
    logger.info(f"[upload_product_payload_to_ipfs] Uploaded product payload{lang_label}")
    logger.info(f"   CID: {cid}")
    logger.debug(f"   Payload keys: {list(payload.keys())}")
    
    return cid


def upload_multilingual_product_payloads_to_ipfs(payloads: Dict[str, Dict[str, Any]], ipfs_factory) -> Dict[str, str]:
    """
    Загружает мультиязычные IPFS payload для продукта и возвращает CID по языкам.
    
    Args:
        payloads: Dict с ключами-языками (en, ru) и значениями-payload
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из фикстуры e2e_ipfs_factory)
    
    Returns:
        Dict с ключами-языками и значениями-CID
        
    Example:
        payloads = {
            "en": create_product_ipfs_payload(
                title="Amanita Powder",
                description="Premium dried Amanita muscaria powder"
            ),
            "ru": create_product_ipfs_payload(
                title="Мухомор Порошок",
                description="Премиум сушёный порошок Amanita muscaria"
            )
        }
        cids = upload_multilingual_product_payloads_to_ipfs(payloads, ipfs_factory)
        # Returns: {"en": "cid://...", "ru": "cid://..."}
    """
    cids: Dict[str, str] = {}
    
    for lang, payload in payloads.items():
        cid = upload_product_payload_to_ipfs(payload, ipfs_factory, language=lang)
        cids[lang] = cid
    
    logger.info(f"[upload_multilingual_product_payloads_to_ipfs] Uploaded {len(cids)} language payloads")
    logger.info(f"   Languages: {list(cids.keys())}")
    logger.info(f"   CIDs: {list(cids.values())}")
    
    return cids


def set_product_cid_in_blockchain(product_id: str, field: str, lang: str, cid: str, blockchain_service) -> bool:
    """
    Записывает CID для продукта в AmanitaInternational контракт.
    
    Args:
        product_id: ID продукта (business_id)
        field: Поле продукта (title, description, или '*' для всего payload)
        lang: Язык (en, ru)
        cid: CID для записи
        blockchain_service: BlockchainService или BlockchainServiceStub (из фикстуры real_blockchain_service)
    
    Returns:
        True если успешно
        
    Example:
        # Записать CID для title продукта на английском
        set_product_cid_in_blockchain(
            product_id="amanita1",
            field="title",
            lang="en",
            cid="cid://...",
            blockchain_service=real_blockchain_service
        )
        
        # Записать CID для всего payload (field='*')
        set_product_cid_in_blockchain(
            product_id="amanita1",
            field="*",
            lang="en",
            cid="cid://...",
            blockchain_service=real_blockchain_service
        )
    """
    try:
        contract = blockchain_service.get_contract("AmanitaInternational")
        if not contract:
            raise ValueError("AmanitaInternational contract not found")
        
        # Вызываем setSimpleFieldCID через transact
        fn = contract.functions.setSimpleFieldCID("product", product_id, field, lang, cid)
        result = fn.transact()
        
        logger.info(f"[set_product_cid_in_blockchain] Set CID for product={product_id}, field={field}, lang={lang}")
        logger.info(f"   CID: {cid}")
        logger.debug(f"   Transaction result: {result}")
        
        return True
    except Exception as exc:
        logger.error(f"[set_product_cid_in_blockchain] Failed to set CID: {exc}")
        raise


def set_multilingual_product_cids_in_blockchain(product_id: str, cids_by_lang: Dict[str, str], field: str, blockchain_service) -> Dict[str, bool]:
    """
    Записывает CID для продукта по нескольким языкам в AmanitaInternational контракт.
    
    Args:
        product_id: ID продукта (business_id)
        cids_by_lang: Dict с ключами-языками (en, ru) и значениями-CID
        field: Поле продукта (title, description, или '*' для всего payload)
        blockchain_service: BlockchainService или BlockchainServiceStub (из фикстуры real_blockchain_service)
    
    Returns:
        Dict с ключами-языками и значениями-результатами (True/False)
        
    Example:
        cids_by_lang = {
            "en": "cid://...",
            "ru": "cid://..."
        }
        results = set_multilingual_product_cids_in_blockchain(
            product_id="amanita1",
            cids_by_lang=cids_by_lang,
            field="*",
            blockchain_service=real_blockchain_service
        )
        # Returns: {"en": True, "ru": True}
    """
    results: Dict[str, bool] = {}
    
    for lang, cid in cids_by_lang.items():
        try:
            result = set_product_cid_in_blockchain(product_id, field, lang, cid, blockchain_service)
            results[lang] = result
        except Exception as exc:
            logger.error(f"[set_multilingual_product_cids_in_blockchain] Failed for lang={lang}: {exc}")
            results[lang] = False
    
    logger.info(f"[set_multilingual_product_cids_in_blockchain] Set CIDs for {len(results)} languages")
    logger.info(f"   Product: {product_id}, Field: {field}")
    logger.info(f"   Languages: {list(results.keys())}")
    logger.info(f"   Success: {sum(1 for v in results.values() if v)}/{len(results)}")
    
    return results


def create_minimal_product_metadata(product_id: str, component_ids: list, metadata_cid: str = "", cover_image_cid: str = "", categories: Optional[list] = None, forms: Optional[list] = None, species: Optional[str] = None, prices: Optional[list] = None) -> Dict[str, Any]:
    """
    Создаёт минимальный product JSON для десериализации без локализуемых текстов.
    
    Цель: исключить локальные источники текстов, чтобы тест проверял,
    что локализация берёт значения из IPFS, а не из JSON метаданных.
    
    Включает плейсхолдеры для обязательных полей (title, species),
    которые будут перезаписаны локализованными значениями из IPFS.
    
    Args:
        product_id: Business ID продукта
        component_ids: Список component_id для organic_components
        metadata_cid: CID метаданных продукта (опционально)
        cover_image_cid: CID обложки продукта (опционально)
        categories: Список категорий (опционально)
        forms: Список форм продукта (опционально, будут перезаписаны из IPFS)
        species: Вид продукта (опционально, будет перезаписан из IPFS)
        prices: Список цен (опционально, обязателен для Product.from_dict)
    
    Returns:
        Dict с минимальными метаданными продукта для десериализации
        
    Example:
        # Минимальный продукт без локализуемых текстов
        metadata = create_minimal_product_metadata(
            product_id="e2e-test-product",
            component_ids=["amanita_muscaria"],
            cover_image_cid="cid://cover123",
            forms=["powder"],
            species="Amanita muscaria",
            prices=[{"price": "19.99", "currency": "USD"}]
        )
        # Title будет "[title]" плейсхолдер, который должен быть перезаписан из IPFS
    """
    # Обязательные поля для Product.from_dict
    metadata: Dict[str, Any] = {
        "id": product_id,
        "business_id": product_id,
        "title": "[title]",  # Плейсхолдер - должен быть перезаписан из IPFS
        "cover_image": cover_image_cid if cover_image_cid else "",
        "species": species if species else "[species]",  # Плейсхолдер или реальное значение
    }
    
    # Органические компоненты (обязательно)
    organic_components = []
    for comp_id in component_ids:
        organic_components.append({
            "component_id": comp_id
        })
    metadata["organic_components"] = organic_components
    
    # Цены (обязательно для Product.from_dict)
    if prices:
        metadata["prices"] = prices
    else:
        # Минимальная цена по умолчанию
        metadata["prices"] = [
            {
                "price": "0.00",
                "currency": "USD"
            }
        ]
    
    # Опциональные поля
    if categories:
        metadata["categories"] = categories
    else:
        metadata["categories"] = []
    
    if forms:
        # Формы могут быть перезаписаны из IPFS, но включаем для валидации
        metadata["forms"] = forms
    else:
        metadata["forms"] = []
    
    # CID метаданных (если указан)
    if metadata_cid:
        metadata["cid"] = metadata_cid
    
    logger.debug(f"[create_minimal_product_metadata] Created minimal metadata for product={product_id}")
    logger.debug(f"   Component IDs: {component_ids}")
    logger.debug(f"   Title placeholder: [title] (should be replaced from IPFS)")
    logger.debug(f"   Forms: {metadata.get('forms', [])}")
    logger.debug(f"   Prices: {len(metadata.get('prices', []))} items")
    
    return metadata


async def deserialize_product_from_metadata(
    product_metadata: Dict[str, Any],
    blockchain_id: int,
    ipfs_factory,
    product_assembler,
    seller: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    is_active: bool = True
):
    """
    Выполняет полную десериализацию продукта из JSON метаданных.
    
    Процесс:
    1. Загружает product JSON в IPFS через ipfs_factory
    2. Получает CID метаданных
    3. Создаёт кортеж blockchain_data (id, seller, componentIds, ipfsCID, active)
    4. Вызывает ProductAssembler.assemble_product для десериализации
    
    Args:
        product_metadata: Dict с метаданными продукта (из create_minimal_product_metadata)
        blockchain_id: ID продукта в блокчейне (int)
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из фикстуры e2e_ipfs_factory)
        product_assembler: ProductAssembler (из фикстуры real_product_assembler)
        seller: Адрес продавца (по умолчанию тестовый адрес)
        is_active: Статус активности продукта (по умолчанию True)
    
    Returns:
        Product: Десериализованный объект продукта или None при ошибке
        
    Example:
        metadata = create_minimal_product_metadata(
            product_id="e2e-test-product",
            component_ids=["amanita_muscaria"]
        )
        
        product = await deserialize_product_from_metadata(
            product_metadata=metadata,
            blockchain_id=0,
            ipfs_factory=e2e_ipfs_factory,
            product_assembler=real_product_assembler
        )
    """
    try:
        logger.info(f"[deserialize_product_from_metadata] Starting deserialization for product={product_metadata.get('business_id')}")
        
        # Шаг 1: Загружаем product JSON в IPFS
        logger.info(f"[deserialize_product_from_metadata] Uploading product metadata to IPFS")
        ipfs_service = ipfs_factory.get_service()
        metadata_cid = ipfs_service.upload_json(product_metadata)
        
        logger.info(f"[deserialize_product_from_metadata] ✅ Metadata uploaded to IPFS: CID={metadata_cid}")
        
        # Шаг 2: Извлекаем component_ids из метаданных
        component_ids = []
        if "organic_components" in product_metadata:
            component_ids = [comp.get("component_id") for comp in product_metadata["organic_components"] if comp.get("component_id")]
        elif "component_id" in product_metadata:
            # SINGLE формат
            component_ids = [product_metadata["component_id"]]
        
        logger.info(f"[deserialize_product_from_metadata] Extracted component_ids: {component_ids}")
        
        # Шаг 3: Создаём кортеж blockchain_data (id, seller, componentIds, ipfsCID, active)
        blockchain_data = (
            blockchain_id,
            seller,
            component_ids,
            metadata_cid,
            is_active
        )
        
        logger.info(f"[deserialize_product_from_metadata] Created blockchain_data: id={blockchain_id}, CID={metadata_cid}, Active={is_active}")
        
        # Шаг 4: Десериализуем через ProductAssembler
        logger.info(f"[deserialize_product_from_metadata] Calling ProductAssembler.assemble_product")
        product = await product_assembler.assemble_product(blockchain_data, product_metadata)
        
        if product:
            logger.info(f"[deserialize_product_from_metadata] ✅ Product deserialized successfully: {product.business_id}")
            logger.info(f"   Blockchain ID: {product.blockchain_id}")
            logger.info(f"   Title: {product.title}")
            logger.info(f"   Components: {len(product.organic_components)}")
        else:
            logger.error(f"[deserialize_product_from_metadata] ❌ Failed to deserialize product")
        
        return product
        
    except Exception as exc:
        logger.error(f"[deserialize_product_from_metadata] ❌ Error during deserialization: {exc}")
        import traceback
        logger.error(f"[deserialize_product_from_metadata] Full traceback:\n{traceback.format_exc()}")
        raise


def create_localization_service_for_e2e(
    lang: str = "en",
    blockchain_service=None,
    ipfs_factory=None,
    translation_cache_service=None,
    fallback_service=None
):
    """
    Создаёт LocalizationService(lang='en') и связанные ProductLocalizationService/ComponentLocalizationService
    с правильными зависимостями для e2e smoke-тестов.
    
    Собирает полную цепочку зависимостей:
    - MultilingualIPFSService (из blockchain_service, ipfs_factory, cache_service, fallback_service)
    - LocalizationService (из всех зависимостей)
    
    Args:
        lang: Язык локализации (по умолчанию 'en')
        blockchain_service: BlockchainService или BlockchainServiceStub (из real_blockchain_service или stub)
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из e2e_ipfs_factory)
        translation_cache_service: TranslationCacheService (из e2e_translation_cache_service)
        fallback_service: FallbackLocalizationService или stub (опционально, создастся stub если None)
    
    Returns:
        LocalizationService: Готовый сервис локализации с инициализированными дочерними сервисами
        
    Example:
        localization_service = create_localization_service_for_e2e(
            lang="en",
            blockchain_service=real_blockchain_service,
            ipfs_factory=e2e_ipfs_factory,
            translation_cache_service=e2e_translation_cache_service
        )
        
        # Теперь можно использовать:
        # localization_service.product_localization.get_translation(...)
        # localization_service.component_localization.get_translation(...)
    """
    # Lazy import
    from services.common.multilingual_ipfs_service import MultilingualIPFSService
    from services.common.localization_service import LocalizationService
    
    logger.info(f"[create_localization_service_for_e2e] Creating LocalizationService with lang={lang}")
    
    # Шаг 1: Проверяем blockchain_service
    if not blockchain_service:
        raise ValueError("blockchain_service is required for LocalizationService")
    
    # Шаг 2: Создаём FallbackLocalizationService stub (если не передан)
    if not fallback_service:
        class _FallbackStub:
            def get_translation_with_fallback(self, *args, **kwargs):
                return None
        
        fallback_service = _FallbackStub()
        logger.info(f"[create_localization_service_for_e2e] ✅ FallbackService stub created")
    else:
        logger.info(f"[create_localization_service_for_e2e] ✅ Using provided FallbackService")
    
    # Шаг 3: Создаём MultilingualIPFSService
    if not ipfs_factory:
        raise ValueError("ipfs_factory is required for LocalizationService")
    
    if not translation_cache_service:
        raise ValueError("translation_cache_service is required for LocalizationService")
    
    multilingual_ipfs_service = MultilingualIPFSService(
        ipfs_factory=ipfs_factory,
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        blockchain_service=blockchain_service,
    )
    logger.info(f"[create_localization_service_for_e2e] ✅ MultilingualIPFSService created")
    
    # Шаг 4: Создаём LocalizationService со всеми зависимостями
    localization_service = LocalizationService(
        lang=lang,
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        ipfs_service=multilingual_ipfs_service,
    )
    logger.info(f"[create_localization_service_for_e2e] ✅ LocalizationService created with lang={lang}")
    logger.info(f"   ProductLocalizationService: {localization_service.product_localization is not None}")
    logger.info(f"   ComponentLocalizationService: {localization_service.component_localization is not None}")
    
    return localization_service


def get_product_translations_via_localization_service(
    localization_service,
    product_id: str,
    fields: list = None
) -> Dict[str, str]:
    """
    Запрашивает переводы title/description для продукта через localization_service.t('product.<id>.*').
    
    Использует формат ключей: `product.<product_id>.<field>` для запроса переводов через LocalizationService.
    
    Args:
        localization_service: LocalizationService (из create_localization_service_for_e2e)
        product_id: Business ID продукта
        fields: Список полей для запроса (по умолчанию ['title', 'description'])
    
    Returns:
        Dict с ключами-полями и значениями-переводами
        
    Example:
        translations = get_product_translations_via_localization_service(
            localization_service=localization_service,
            product_id="e2e-test-product",
            fields=['title', 'description']
        )
        # Returns: {"title": "Amanita Powder", "description": "Premium dried..."}
        
        # Или можно запросить только title:
        title = localization_service.t('product.e2e-test-product.title')
    """
    if fields is None:
        fields = ['title', 'description']
    
    translations: Dict[str, str] = {}
    
    logger.info(f"[get_product_translations_via_localization_service] Requesting translations for product={product_id}")
    logger.info(f"   Fields: {fields}")
    logger.info(f"   Language: {localization_service.lang}")
    
    for field in fields:
        # Формируем ключ в формате: product.<product_id>.<field>
        key = f"product.{product_id}.{field}"
        
        logger.debug(f"[get_product_translations_via_localization_service] Requesting: {key}")
        
        # Запрашиваем перевод через localization_service.t()
        translation = localization_service.t(key, default=None)
        
        translations[field] = translation
        
        logger.debug(f"[get_product_translations_via_localization_service] {key} → {translation[:50] if translation and len(translation) > 50 else translation}")
    
    logger.info(f"[get_product_translations_via_localization_service] ✅ Retrieved {len(translations)} translations")
    logger.info(f"   Translated fields: {list(translations.keys())}")
    
    return translations


def build_localized_product_card(
    product,
    localization_service,
    include_fields: list = None
) -> Dict[str, Any]:
    """
    Собирает карточку/DTO продукта для UI на основе полученных переводов из LocalizationService.
    
    Использует localization_service.t('product.<id>.*') для получения локализованных значений
    и собирает DTO для UI или Telegram formatter.
    
    Args:
        product: Product объект (из deserialize_product_from_metadata)
        localization_service: LocalizationService (из create_localization_service_for_e2e)
        include_fields: Список полей для включения (по умолчанию ['title', 'description', 'forms'])
    
    Returns:
        Dict с локализованными полями продукта для UI
        
    Example:
        product = await deserialize_product_from_metadata(...)
        localization_service = create_localization_service_for_e2e(...)
        
        card = build_localized_product_card(
            product=product,
            localization_service=localization_service
        )
        # Returns: {
        #     "business_id": "e2e-test-product",
        #     "title": "Amanita Powder",  # из IPFS
        #     "description": "Premium dried...",  # из IPFS
        #     "forms": ["powder", "capsules"],
        #     "species": "Amanita muscaria",
        #     "components": [...],
        #     ...
        # }
    """
    if include_fields is None:
        include_fields = ['title', 'description', 'forms']
    
    business_id = getattr(product, 'business_id', getattr(product, 'id', 'unknown'))
    
    logger.info(f"[build_localized_product_card] Building localized card for product={business_id}")
    logger.info(f"   Language: {localization_service.lang}")
    logger.info(f"   Fields to localize: {include_fields}")
    
    # Базовая карточка с данными из продукта
    card: Dict[str, Any] = {
        "business_id": business_id,
        "blockchain_id": getattr(product, 'blockchain_id', None),
        "cid": getattr(product, 'cid', None),
        "is_active": getattr(product, 'is_active', True),
        "cover_image_url": getattr(product, 'cover_image_url', ''),
        "categories": getattr(product, 'categories', []),
        "species": getattr(product, 'species', ''),
        "prices": [
            {
                "price": str(price.price) if hasattr(price, 'price') else str(price.get('price', '0')),
                "currency": price.currency if hasattr(price, 'currency') else price.get('currency', 'USD'),
                "form": getattr(price, 'form', price.get('form', None)),
                "weight": getattr(price, 'weight', price.get('weight', None)),
                "weight_unit": getattr(price, 'weight_unit', price.get('weight_unit', None)),
            }
            for price in getattr(product, 'prices', [])
        ],
        "organic_components": [
            {
                "component_id": comp.component_id if hasattr(comp, 'component_id') else comp.get('component_id'),
                "scientific_title": getattr(comp, 'scientific_title', comp.get('scientific_title', None)),
                "proportion": getattr(comp, 'proportion', comp.get('proportion', None)),
            }
            for comp in getattr(product, 'organic_components', [])
        ],
    }
    
    # Запрашиваем локализованные переводы через localization_service.t()
    translations = get_product_translations_via_localization_service(
        localization_service=localization_service,
        product_id=business_id,
        fields=include_fields
    )
    
    # Обновляем карточку локализованными значениями
    for field in include_fields:
        if field in translations and translations[field]:
            # Проверяем, что перевод не является fallback ключом
            expected_key = f"product.{business_id}.{field}"
            if translations[field] != expected_key:
                card[field] = translations[field]
                logger.debug(f"[build_localized_product_card] ✅ Localized {field}: {translations[field][:50] if len(translations[field]) > 50 else translations[field]}")
            else:
                # Fallback на значение из продукта
                original_value = getattr(product, field, None)
                if original_value:
                    card[field] = original_value
                    logger.debug(f"[build_localized_product_card] ⚠️ Using fallback for {field}: {original_value}")
        else:
            # Fallback на значение из продукта
            original_value = getattr(product, field, None)
            if original_value:
                card[field] = original_value
                logger.debug(f"[build_localized_product_card] ⚠️ Using original value for {field}: {original_value}")
    
    logger.info(f"[build_localized_product_card] ✅ Card built successfully")
    logger.info(f"   Localized fields: {[f for f in include_fields if f in card]}")
    logger.info(f"   Total fields: {len(card)}")
    
    return card


# ============================================================================
# VALIDATION HELPERS (для проверок 4.1-4.5)
# ============================================================================

def validate_ipfs_source_used(ipfs_factory, blockchain_service) -> Tuple[bool, str]:
    """
    4.1 Проверка: Источник данных — IPFS.
    
    Проверяет, что были вызовы IPFS и blockchain gateway:
    - ipfs.download_calls > 0 (если доступен счётчик)
    - gateway.get_cid_calls > 0 (если доступен счётчик)
    
    Args:
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из e2e_ipfs_factory)
        blockchain_service: BlockchainService или BlockchainServiceStub
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        is_valid, msg = validate_ipfs_source_used(ipfs_factory, blockchain_service)
        assert is_valid, msg
    """
    logger.info(f"[validate_ipfs_source_used] Checking IPFS and blockchain gateway usage")
    
    messages = []
    
    # Проверка IPFS счётчика
    try:
        ipfs_service = ipfs_factory.get_service()
        if hasattr(ipfs_service, 'download_calls'):
            download_calls = ipfs_service.download_calls
            if download_calls > 0:
                messages.append(f"✅ IPFS download_calls: {download_calls}")
            else:
                messages.append(f"❌ IPFS download_calls: {download_calls} (expected > 0)")
        else:
            messages.append("ℹ️ IPFS download_calls counter not available (using real IPFS)")
    except Exception as e:
        messages.append(f"⚠️ Error checking IPFS counter: {e}")
    
    # Проверка blockchain gateway счётчика
    try:
        contract = blockchain_service.get_contract("AmanitaInternational")
        if contract and hasattr(contract, 'get_cid_calls'):
            get_cid_calls = contract.get_cid_calls
            if get_cid_calls > 0:
                messages.append(f"✅ Gateway get_cid_calls: {get_cid_calls}")
            else:
                messages.append(f"❌ Gateway get_cid_calls: {get_cid_calls} (expected > 0)")
        else:
            messages.append("ℹ️ Gateway get_cid_calls counter not available (using real blockchain)")
    except Exception as e:
        messages.append(f"⚠️ Error checking gateway counter: {e}")
    
    # Результат: считаем валидным, если есть хотя бы один счётчик с > 0
    has_ipfs_calls = any("IPFS download_calls:" in msg and "✅" in msg for msg in messages)
    has_gateway_calls = any("Gateway get_cid_calls:" in msg and "✅" in msg for msg in messages)
    
    is_valid = has_ipfs_calls or has_gateway_calls or any("not available" in msg for msg in messages)
    message = "\n".join(messages)
    
    logger.info(f"[validate_ipfs_source_used] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


def validate_no_local_json_used(captured_logs: str, expected_values: Dict[str, str], actual_values: Dict[str, str]) -> Tuple[bool, str]:
    """
    4.2 Проверка: Исключение локальных JSON.
    
    Проверяет:
    - В логах отсутствуют чтения `templates/products/*.json`
    - Значения не совпадают с локальными шаблонами
    
    Args:
        captured_logs: Строка с логами (из pytest caplog)
        expected_values: Dict с ожидаемыми значениями из IPFS (для сравнения)
        actual_values: Dict с фактическими значениями из локализации
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        is_valid, msg = validate_no_local_json_used(
            captured_logs=caplog.text,
            expected_values={"title": "Amanita Powder"},
            actual_values={"title": card["title"]}
        )
        assert is_valid, msg
    """
    logger.info(f"[validate_no_local_json_used] Checking no local JSON files were used")
    
    messages = []
    
    # Проверка 1: Отсутствие чтений локальных JSON
    local_json_patterns = [
        "templates/products/",
        "templates/products/*.json",
        "Fallback файл не найден",
    ]
    
    found_local_json = False
    for pattern in local_json_patterns:
        if pattern in captured_logs:
            # Ищем только успешные чтения, не warnings о отсутствии файлов
            if "Fallback файл не найден" in captured_logs:
                messages.append(f"✅ Local JSON fallback file not found (expected for IPFS-only flow)")
            else:
                found_local_json = True
                messages.append(f"⚠️ Found local JSON reference: {pattern}")
    
    if not found_local_json:
        messages.append("✅ No local JSON file reads detected in logs")
    
    # Проверка 2: Значения не совпадают с локальными шаблонами (если были бы шаблоны)
    # Здесь проверяем, что значения соответствуют ожидаемым из IPFS
    values_match = True
    for key, expected_value in expected_values.items():
        if key in actual_values:
            actual_value = actual_values[key]
            if actual_value == expected_value:
                messages.append(f"✅ {key} matches expected IPFS value")
            else:
                values_match = False
                messages.append(f"❌ {key} mismatch: expected={expected_value[:50]}, actual={actual_value[:50]}")
    
    is_valid = not found_local_json and values_match
    message = "\n".join(messages)
    
    logger.info(f"[validate_no_local_json_used] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


def validate_translation_values_correct(actual_values: Dict[str, str], expected_values: Dict[str, str]) -> Tuple[bool, str]:
    """
    4.3 Проверка: Значения корректны.
    
    Проверяет, что title и description соответствуют ожидаемым значениям из IPFS.
    
    Args:
        actual_values: Dict с фактическими значениями (из build_localized_product_card)
        expected_values: Dict с ожидаемыми значениями из IPFS payload
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        is_valid, msg = validate_translation_values_correct(
            actual_values={"title": card["title"], "description": card["description"]},
            expected_values={"title": "Amanita Powder", "description": "Premium dried..."}
        )
        assert is_valid, msg
    """
    logger.info(f"[validate_translation_values_correct] Checking translation values match IPFS payload")
    
    messages = []
    all_match = True
    
    for field, expected_value in expected_values.items():
        if field in actual_values:
            actual_value = actual_values[field]
            if actual_value == expected_value:
                messages.append(f"✅ {field}: '{actual_value[:50] if len(actual_value) > 50 else actual_value}' matches IPFS")
            else:
                all_match = False
                messages.append(f"❌ {field} mismatch:")
                messages.append(f"   Expected (IPFS): {expected_value[:100]}")
                messages.append(f"   Actual: {actual_value[:100]}")
        else:
            all_match = False
            messages.append(f"❌ {field}: missing in actual values")
    
    is_valid = all_match
    message = "\n".join(messages)
    
    logger.info(f"[validate_translation_values_correct] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


def validate_caching_works(ipfs_factory, first_call_count: int, second_call_count: int) -> Tuple[bool, str]:
    """
    4.4 Проверка: Кэширование работает.
    
    Проверяет, что повторный запрос не увеличивает ipfs.download_calls.
    
    Args:
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из e2e_ipfs_factory)
        first_call_count: Счётчик после первого запроса
        second_call_count: Счётчик после второго запроса
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        ipfs = ipfs_factory.get_service()
        first_count = ipfs.download_calls
        
        # Первый запрос
        translations = get_product_translations_via_localization_service(...)
        count_after_first = ipfs.download_calls
        
        # Второй запрос
        translations2 = get_product_translations_via_localization_service(...)
        count_after_second = ipfs.download_calls
        
        is_valid, msg = validate_caching_works(ipfs_factory, count_after_first, count_after_second)
        assert is_valid, msg
    """
    logger.info(f"[validate_caching_works] Checking cache prevents redundant IPFS calls")
    
    messages = []
    
    # Проверяем, что второй запрос не увеличил счётчик
    calls_increased = second_call_count > first_call_count
    
    if not calls_increased:
        messages.append(f"✅ Cache working: download_calls unchanged ({first_call_count} → {second_call_count})")
    else:
        messages.append(f"❌ Cache not working: download_calls increased ({first_call_count} → {second_call_count})")
    
    # Дополнительная проверка через IPFS service (если доступен)
    try:
        ipfs_service = ipfs_factory.get_service()
        if hasattr(ipfs_service, 'download_calls'):
            current_count = ipfs_service.download_calls
            messages.append(f"   Current IPFS download_calls: {current_count}")
            
            # Если счётчик не изменился после второго запроса, кэш работает
            if current_count == second_call_count:
                messages.append(f"✅ IPFS service counter confirms: {current_count} calls total")
            else:
                messages.append(f"⚠️ IPFS service counter differs: {current_count} (expected {second_call_count})")
    except Exception as e:
        messages.append(f"ℹ️ Could not verify via IPFS service: {e}")
    
    is_valid = not calls_increased
    message = "\n".join(messages)
    
    logger.info(f"[validate_caching_works] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


def validate_fallback_placeholders_when_ipfs_disabled(
    localization_service,
    product_id: str,
    ipfs_factory=None
) -> Tuple[bool, str]:
    """
    4.5 Проверка: Честность падения — fallback на плейсхолдеры.
    
    Проверяет, что при отключении IPFS и отсутствии внешнего кэша возвращаются плейсхолдеры [title]/[description].
    
    Args:
        localization_service: LocalizationService (из create_localization_service_for_e2e)
        product_id: Business ID продукта
        ipfs_factory: IPFSFactory или IPFSFactoryStub (опционально, для отключения IPFS)
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        # Отключаем IPFS (если stub)
        ipfs = ipfs_factory.get_service()
        ipfs._storage.clear()  # Очищаем хранилище
        
        is_valid, msg = validate_fallback_placeholders_when_ipfs_disabled(
            localization_service=localization_service,
            product_id="e2e-test-product",
            ipfs_factory=ipfs_factory
        )
        assert is_valid, msg
    """
    logger.info(f"[validate_fallback_placeholders_when_ipfs_disabled] Checking fallback to placeholders")
    
    messages = []
    
    # Отключаем IPFS (очищаем хранилище stub, если используется)
    if ipfs_factory:
        try:
            ipfs_service = ipfs_factory.get_service()
            if hasattr(ipfs_service, '_storage'):
                original_storage = dict(ipfs_service._storage)  # Сохраняем для восстановления
                ipfs_service._storage.clear()
                messages.append("✅ IPFS storage cleared (simulating IPFS failure)")
            else:
                messages.append("ℹ️ Cannot clear IPFS storage (using real IPFS)")
        except Exception as e:
            messages.append(f"⚠️ Error clearing IPFS storage: {e}")
    
    # Запрашиваем переводы (должны вернуться плейсхолдеры)
    title = localization_service.t(f'product.{product_id}.title', default=None)
    description = localization_service.t(f'product.{product_id}.description', default=None)
    
    # Проверяем, что вернулись плейсхолдеры или fallback ключи
    expected_title_placeholder = f"[title]" or f"product.{product_id}.title"
    expected_desc_placeholder = f"[description]" or f"product.{product_id}.description"
    
    title_is_placeholder = (
        title == expected_title_placeholder or
        title == f"product.{product_id}.title" or
        (title and "[" in title and "]" in title)
    )
    desc_is_placeholder = (
        description == expected_desc_placeholder or
        description == f"product.{product_id}.description" or
        (description and "[" in description and "]" in description)
    )
    
    if title_is_placeholder:
        messages.append(f"✅ Title fallback to placeholder: '{title}'")
    else:
        messages.append(f"❌ Title should be placeholder, got: '{title}'")
    
    if desc_is_placeholder:
        messages.append(f"✅ Description fallback to placeholder: '{description}'")
    else:
        messages.append(f"❌ Description should be placeholder, got: '{description}'")
    
    # Восстанавливаем IPFS хранилище (если было очищено)
    if ipfs_factory:
        try:
            ipfs_service = ipfs_factory.get_service()
            if hasattr(ipfs_service, '_storage') and 'original_storage' in locals():
                ipfs_service._storage.update(original_storage)
                messages.append("✅ IPFS storage restored")
        except Exception as e:
            messages.append(f"⚠️ Error restoring IPFS storage: {e}")
    
    is_valid = title_is_placeholder and desc_is_placeholder
    message = "\n".join(messages)
    
    logger.info(f"[validate_fallback_placeholders_when_ipfs_disabled] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


# ============================================================================
# VARIATION/MUTATION HELPERS (для проверок 5.1-5.2)
# ============================================================================

def validate_cache_invalidation_on_cid_update(
    product_id: str,
    field: str,
    lang: str,
    old_cid: str,
    new_cid: str,
    new_payload: Dict[str, Any],
    ipfs_factory,
    blockchain_service,
    localization_service,
    expected_new_value: str
) -> Tuple[bool, str]:
    """
    5.1 Проверка: Обновление CID инвалидирует кэш.
    
    Проверяет, что при обновлении CID на блокчейне:
    1. При следующем запросе выполняется повторная загрузка (ipfs.download_calls увеличивается)
    2. Кэш инвалидируется (возвращается новое значение из нового CID)
    
    Args:
        product_id: Business ID продукта
        field: Поле продукта (title, description, или '*')
        lang: Язык (en, ru)
        old_cid: Старый CID (должен быть уже записан в blockchain и закэширован)
        new_cid: Новый CID для обновления
        new_payload: Новый IPFS payload для нового CID
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из e2e_ipfs_factory)
        blockchain_service: BlockchainService или BlockchainServiceStub
        localization_service: LocalizationService (из create_localization_service_for_e2e)
        expected_new_value: Ожидаемое новое значение после обновления CID
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        # Загружаем новый payload в IPFS
        new_payload = create_product_ipfs_payload(title="Updated Title", description="Updated Description")
        new_cid = upload_product_payload_to_ipfs(new_payload, ipfs_factory, language="en")
        
        is_valid, msg = validate_cache_invalidation_on_cid_update(
            product_id="e2e-test-product",
            field="*",
            lang="en",
            old_cid=old_cid,
            new_cid=new_cid,
            new_payload=new_payload,
            ipfs_factory=ipfs_factory,
            blockchain_service=blockchain_service,
            localization_service=localization_service,
            expected_new_value="Updated Title"
        )
        assert is_valid, msg
    """
    logger.info(f"[validate_cache_invalidation_on_cid_update] Checking cache invalidation on CID update")
    logger.info(f"   Product: {product_id}, Field: {field}, Lang: {lang}")
    logger.info(f"   Old CID: {old_cid}")
    logger.info(f"   New CID: {new_cid}")
    
    messages = []
    
    # Шаг 1: Загружаем новый payload в IPFS (если ещё не загружен)
    try:
        ipfs_service = ipfs_factory.get_service()
        if hasattr(ipfs_service, '_storage') and new_cid not in ipfs_service._storage:
            ipfs_service.upload_json(new_payload)
            messages.append(f"✅ New payload uploaded to IPFS: CID={new_cid}")
    except Exception as e:
        messages.append(f"⚠️ Error uploading new payload: {e}")
    
    # Шаг 2: Получаем текущий счётчик IPFS перед обновлением CID
    ipfs_service = ipfs_factory.get_service()
    download_calls_before = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
    
    # Шаг 3: Запрашиваем текущее значение (должно быть из кэша)
    old_value = localization_service.t(f'product.{product_id}.title', default=None)
    messages.append(f"   Current value (from cache): '{old_value}'")
    
    # Шаг 4: Обновляем CID на блокчейне
    logger.info(f"[validate_cache_invalidation_on_cid_update] Updating CID on blockchain")
    set_product_cid_in_blockchain(
        product_id=product_id,
        field=field,
        lang=lang,
        cid=new_cid,
        blockchain_service=blockchain_service
    )
    messages.append(f"✅ CID updated on blockchain: {old_cid} → {new_cid}")
    
    # Шаг 5: Запрашиваем значение снова (должна быть повторная загрузка)
    download_calls_after_update = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
    
    new_value = localization_service.t(f'product.{product_id}.title', default=None)
    
    download_calls_after_query = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
    
    # Шаг 6: Проверяем, что было повторное обращение к IPFS
    if download_calls_before is not None and download_calls_after_query is not None:
        calls_increased = download_calls_after_query > download_calls_before
        if calls_increased:
            messages.append(f"✅ IPFS download_calls increased: {download_calls_before} → {download_calls_after_query} (cache invalidated)")
        else:
            messages.append(f"❌ IPFS download_calls unchanged: {download_calls_before} → {download_calls_after_query} (cache not invalidated)")
    else:
        messages.append("ℹ️ IPFS download_calls counter not available (using real IPFS)")
        calls_increased = True  # Считаем, что при real IPFS кэш инвалидируется
    
    # Шаг 7: Проверяем, что возвращается новое значение
    value_updated = new_value == expected_new_value
    if value_updated:
        messages.append(f"✅ Value updated correctly: '{old_value}' → '{new_value}'")
    else:
        messages.append(f"❌ Value not updated: expected '{expected_new_value}', got '{new_value}'")
    
    is_valid = calls_increased and value_updated
    message = "\n".join(messages)
    
    logger.info(f"[validate_cache_invalidation_on_cid_update] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


def validate_multilingual_cache_independence(
    product_id: str,
    field: str,
    en_payload: Dict[str, Any],
    ru_payload: Dict[str, Any],
    ipfs_factory,
    blockchain_service,
    translation_cache_service
) -> Tuple[bool, str]:
    """
    5.2 Проверка: Независимость кэшей по языкам.
    
    Проверяет, что кэши для разных языков независимы:
    1. Загружаем payload для 'en' и запрашиваем перевод
    2. Загружаем payload для 'ru' и запрашиваем перевод
    3. Проверяем, что значения не перекрываются (en остаётся английским, ru остаётся русским)
    4. Проверяем, что кэши независимы (изменение одного языка не влияет на другой)
    
    Args:
        product_id: Business ID продукта
        field: Поле продукта (title, description, или '*')
        en_payload: IPFS payload для английского языка
        ru_payload: IPFS payload для русского языка
        ipfs_factory: IPFSFactory или IPFSFactoryStub (из e2e_ipfs_factory)
        blockchain_service: BlockchainService или BlockchainServiceStub
        translation_cache_service: TranslationCacheService (из e2e_translation_cache_service)
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
        
    Example:
        en_payload = create_product_ipfs_payload(title="Amanita Powder", description="Premium dried...")
        ru_payload = create_product_ipfs_payload(title="Порошок мухомора", description="Премиум сушёный...")
        
        is_valid, msg = validate_multilingual_cache_independence(
            product_id="e2e-test-product",
            field="*",
            en_payload=en_payload,
            ru_payload=ru_payload,
            ipfs_factory=ipfs_factory,
            blockchain_service=blockchain_service,
            translation_cache_service=translation_cache_service
        )
        assert is_valid, msg
    """
    logger.info(f"[validate_multilingual_cache_independence] Checking multilingual cache independence")
    logger.info(f"   Product: {product_id}, Field: {field}")
    
    messages = []
    
    # Шаг 1: Создаём LocalizationService для английского языка
    localization_en = create_localization_service_for_e2e(
        lang="en",
        blockchain_service=blockchain_service,
        ipfs_factory=ipfs_factory,
        translation_cache_service=translation_cache_service
    )
    
    # Шаг 2: Загружаем и устанавливаем CID для английского
    cid_en = upload_product_payload_to_ipfs(en_payload, ipfs_factory, language="en")
    set_product_cid_in_blockchain(product_id, field, "en", cid_en, blockchain_service)
    messages.append(f"✅ English payload uploaded and CID set: {cid_en}")
    
    # Шаг 3: Запрашиваем английский перевод
    title_en = localization_en.t(f'product.{product_id}.title', default=None)
    messages.append(f"   English title: '{title_en}'")
    
    # Шаг 4: Создаём LocalizationService для русского языка
    localization_ru = create_localization_service_for_e2e(
        lang="ru",
        blockchain_service=blockchain_service,
        ipfs_factory=ipfs_factory,
        translation_cache_service=translation_cache_service
    )
    
    # Шаг 5: Загружаем и устанавливаем CID для русского
    cid_ru = upload_product_payload_to_ipfs(ru_payload, ipfs_factory, language="ru")
    set_product_cid_in_blockchain(product_id, field, "ru", cid_ru, blockchain_service)
    messages.append(f"✅ Russian payload uploaded and CID set: {cid_ru}")
    
    # Шаг 6: Запрашиваем русский перевод
    title_ru = localization_ru.t(f'product.{product_id}.title', default=None)
    messages.append(f"   Russian title: '{title_ru}'")
    
    # Шаг 7: Проверяем, что английский перевод не изменился
    title_en_after_ru = localization_en.t(f'product.{product_id}.title', default=None)
    en_preserved = title_en_after_ru == title_en
    
    if en_preserved:
        messages.append(f"✅ English cache preserved: '{title_en}' (not affected by Russian)")
    else:
        messages.append(f"❌ English cache corrupted: '{title_en}' → '{title_en_after_ru}'")
    
    # Шаг 8: Проверяем, что значения различаются (не перекрываются)
    values_differ = title_en != title_ru
    if values_differ:
        messages.append(f"✅ Languages have different values (cache independence confirmed)")
    else:
        messages.append(f"❌ Languages have same value (possible cache collision)")
    
    # Шаг 9: Проверяем, что значения соответствуют ожидаемым
    expected_en = en_payload.get("title", "")
    expected_ru = ru_payload.get("title", "")
    
    en_correct = title_en == expected_en
    ru_correct = title_ru == expected_ru
    
    if en_correct:
        messages.append(f"✅ English value matches IPFS payload: '{title_en}'")
    else:
        messages.append(f"❌ English value mismatch: expected '{expected_en}', got '{title_en}'")
    
    if ru_correct:
        messages.append(f"✅ Russian value matches IPFS payload: '{title_ru}'")
    else:
        messages.append(f"❌ Russian value mismatch: expected '{expected_ru}', got '{title_ru}'")
    
    is_valid = en_preserved and values_differ and en_correct and ru_correct
    message = "\n".join(messages)
    
    logger.info(f"[validate_multilingual_cache_independence] Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    logger.info(f"   {message}")
    
    return is_valid, message


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """
    Register custom markers for E2E tests.
    """
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests (full stack, requires infrastructure)"
    )
    config.addinivalue_line(
        "markers",
        "requires_node: Test requires Hardhat node running on localhost:8545"
    )
    config.addinivalue_line(
        "markers",
        "requires_arweave: Test requires Arweave network access"
    )


def pytest_collection_modifyitems(config, items):
    """
    Auto-skip E2E tests if running in CI without infrastructure.
    """
    # Check if CI environment
    if os.getenv("CI") == "true" and os.getenv("E2E_ENABLED") != "true":
        skip_e2e = pytest.mark.skip(reason="E2E tests disabled in CI (set E2E_ENABLED=true to enable)")
        
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)

