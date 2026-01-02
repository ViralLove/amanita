"""
E2E Tests for Product Localization via IPFS/CID.

Tests the complete localization flow through IPFS:
1. IPFS payload upload (multilingual)
2. CID storage in AmanitaInternational contract
3. Translation retrieval via LocalizationService
4. Product localization with IPFS source validation
5. Cache and fallback mechanisms

Based on: @e2e-test-build.core.mdc (Phase 2: Localization Flow)
Plan: @temp-localization-testing-plan.md (4.4 E2E smoke)
"""

import pytest
import logging
import os

logger = logging.getLogger(__name__)


@pytest.mark.e2e
class TestProductLocalizationIPFSE2E:
    """
    E2E tests for product localization via IPFS/CID.
    
    GOAL: Validate complete localization pipeline from IPFS to UI.
    
    Prerequisites:
    - E2E_USE_STUBS=true (uses stub IPFS/Blockchain for fast execution)
    - Local profile with caching enabled
    - TranslationCacheService with tmp_path / 'cache'
    
    Tests:
    1. Product Localization via IPFS/CID — 5 stages (4.1-4.5 validations)
    
    Plan: @temp-localization-e2e-compliance-check.md
    """
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_product_localization_via_ipfs_e2e(
        self,
        e2e_local_profile,
        e2e_translation_cache_service,
        e2e_ipfs_factory,
        e2e_blockchain_service,
        real_product_assembler,
        caplog
    ):
        """
        E2E TEST: Product Localization via IPFS/CID
        
        Проверяет полный flow локализации продукта через IPFS согласно плану 4.4:
        1. Подготовка окружения (1.1-1.4) ✅
        2. Подготовка данных (2.1-2.4) ✅
        3. Действие (E2E поток) (3.1-3.4) ✅
        4. Проверки (4.1-4.5) ✅
        5. Вариации/мутации (5.1-5.2) [опционально] ✅
        
        Время выполнения: ~2-3 секунды (stub режим)
        
        Plan: @temp-localization-e2e-compliance-check.md
        """
        logger.info("="*80)
        logger.info("E2E TEST: Product Localization via IPFS/CID")
        logger.info("="*80)
        
        # Импорт EnvironmentValidator для проверки окружения
        from bot.tests.fixtures.env_validator import EnvironmentValidator
        
        # Проверка окружения: если не stub режим, проверяем Hardhat node
        is_valid, error_message = EnvironmentValidator.validate_e2e_environment()
        if not is_valid:
            pytest.skip(f"⚠️ {error_message}")
        
        use_stubs = EnvironmentValidator.should_use_stubs()
        if use_stubs:
            logger.info("✅ E2E_USE_STUBS=true: stub режим активирован, Hardhat node не требуется")
        else:
            node_available, node_message = EnvironmentValidator.validate_hardhat_node()
            if node_available:
                logger.info(f"✅ Hardhat node доступен: {node_message}")
            else:
                pytest.skip(f"⚠️ Hardhat node недоступен: {node_message}. Установите E2E_USE_STUBS=true для stub режима.")
        
        # Импорт функций из conftest (доступны как модуль через pytest)
        from tests.e2e.conftest import (
            create_product_ipfs_payload,
            upload_product_payload_to_ipfs,
            set_product_cid_in_blockchain,
            create_minimal_product_metadata,
            deserialize_product_from_metadata,
            create_localization_service_for_e2e,
            get_product_translations_via_localization_service,
            build_localized_product_card,
            validate_ipfs_source_used,
            validate_no_local_json_used,
            validate_translation_values_correct,
            validate_caching_works,
            validate_fallback_placeholders_when_ipfs_disabled,
            validate_cache_invalidation_on_cid_update,
            validate_multilingual_cache_independence
        )
        
        product_id = "e2e-test-product-localization"
        
        # ========================================
        # 1. Подготовка окружения (1.1-1.4)
        # ========================================
        logger.info("\n🔧 STAGE 1: Environment Setup")
        
        # 1.1: Профиль local активирован
        assert os.getenv("ENVIRONMENT") == "local", "Environment should be 'local'"
        assert os.getenv("ENABLE_CACHING") == "true", "Caching should be enabled"
        # E2E_USE_STUBS может быть true или false (проверено выше через EnvironmentValidator)
        logger.info("✅ 1.1: Local profile activated")
        logger.info(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
        logger.info(f"   ENABLE_CACHING: {os.getenv('ENABLE_CACHING')}")
        logger.info(f"   E2E_USE_STUBS: {os.getenv('E2E_USE_STUBS')} ({'stub mode' if use_stubs else 'real mode'})")
        
        # 1.2: TranslationCacheService инициализирован
        assert e2e_translation_cache_service is not None, "TranslationCacheService should be initialized"
        assert e2e_translation_cache_service.cache_dir.exists(), f"Cache directory should exist: {e2e_translation_cache_service.cache_dir}"
        logger.info("✅ 1.2: TranslationCacheService initialized")
        logger.info(f"   Cache directory: {e2e_translation_cache_service.cache_dir}")
        logger.info(f"   Default TTL: {e2e_translation_cache_service.default_ttl}s")
        
        # 1.3: BlockchainService инициализирован (с контрактом AmanitaInternational)
        assert e2e_blockchain_service is not None, "BlockchainService should be initialized"
        contract = e2e_blockchain_service.get_contract("AmanitaInternational")
        assert contract is not None, "AmanitaInternational contract should be loaded in BlockchainService"
        logger.info("✅ 1.3: BlockchainService initialized with AmanitaInternational contract")
        logger.info(f"   Blockchain service type: {type(e2e_blockchain_service).__name__}")
        
        # 1.4: IPFSFactory инициализирован (stub при E2E_USE_STUBS=true)
        assert e2e_ipfs_factory is not None, "IPFSFactory should be initialized"
        ipfs_service = e2e_ipfs_factory.get_service()
        assert ipfs_service is not None, "IPFS service should be available"
        
        # Проверка, что это stub (если E2E_USE_STUBS=true)
        if use_stubs:
            assert hasattr(ipfs_service, 'download_calls'), "IPFS stub should have download_calls counter"
            assert hasattr(ipfs_service, 'upload_calls'), "IPFS stub should have upload_calls counter"
            assert ipfs_service.download_calls == 0, f"Initial download_calls should be 0, got {ipfs_service.download_calls}"
            logger.info("✅ 1.4: IPFSFactory initialized (stub mode)")
            logger.info(f"   Service type: {type(ipfs_service).__name__}")
            logger.info(f"   Initial download_calls: {ipfs_service.download_calls}")
            logger.info(f"   Initial upload_calls: {ipfs_service.upload_calls}")
        else:
            logger.info("✅ 1.4: IPFSFactory initialized (real mode)")
            logger.info(f"   Service type: {type(ipfs_service).__name__}")
        
        logger.info("✅ Environment setup complete (1.1-1.4)")
        
        # ========================================
        # 2. Подготовка данных (2.1-2.4)
        # ========================================
        logger.info("\n📦 STAGE 2: Data Preparation")
        
        # 2.1: Сформировать IPFS payload для продукта
        title_en = "Amanita Powder (E2E Test)"
        description_en = "Premium dried Amanita muscaria powder for testing localization via IPFS."
        
        payload_en = create_product_ipfs_payload(
            title=title_en,
            description=description_en,
            forms=["powder", "capsules"]
        )
        
        # Проверка структуры payload
        assert payload_en is not None, "Payload should be created"
        assert "title" in payload_en, "Payload should contain 'title'"
        assert "description" in payload_en, "Payload should contain 'description'"
        assert "forms" in payload_en, "Payload should contain 'forms'"
        assert payload_en["title"] == title_en, f"Expected title='{title_en}', got '{payload_en['title']}'"
        assert payload_en["description"] == description_en, f"Expected description='{description_en}', got '{payload_en['description']}'"
        # Формы преобразуются в строку с запятыми (см. create_product_ipfs_payload в conftest.py)
        expected_forms_str = "powder,capsules"
        assert payload_en["forms"] == expected_forms_str, f"Expected forms='{expected_forms_str}', got '{payload_en['forms']}'"
        
        logger.info("✅ 2.1: IPFS payload created")
        logger.info(f"   Structure: {list(payload_en.keys())}")
        logger.info(f"   Title: {payload_en['title'][:50]}...")
        logger.info(f"   Description: {payload_en['description'][:50]}...")
        logger.info(f"   Forms: {payload_en['forms']} (string format)")
        
        # 2.2: Загрузить payload в IPFS и получить CID
        # Проверка счётчика до запроса (должен быть 0)
        ipfs_service = e2e_ipfs_factory.get_service()
        initial_download_calls = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
        
        if initial_download_calls is not None:
            assert initial_download_calls == 0, f"Initial download_calls should be 0, got {initial_download_calls}"
            logger.info(f"   Initial download_calls: {initial_download_calls} (before upload)")
        
        cid_en = upload_product_payload_to_ipfs(
            payload=payload_en,
            ipfs_factory=e2e_ipfs_factory,
            language="en"
        )
        
        # Проверки CID
        assert cid_en is not None, "CID should be returned from IPFS upload"
        
        # Если stub, CID должен быть validate_ipfs_cid()-compatible (после миграции на ProductStorageService)
        use_stubs = os.getenv("E2E_USE_STUBS") == "true"
        if use_stubs and hasattr(ipfs_service, '_storage'):
            assert cid_en.startswith("Qm") and len(cid_en) == 46, (
                f"Stub CID should look like CIDv0 (Qm + 44 base58 chars), got '{cid_en}'"
            )
        
        logger.info("✅ 2.2: IPFS payload uploaded")
        logger.info(f"   CID: {cid_en}")
        if initial_download_calls is not None:
            logger.info(f"   download_calls after upload: {ipfs_service.download_calls} (should still be 0)")
        
        # 2.3: Записать CID в AmanitaInternational
        # Проверка счётчика до записи
        contract = e2e_blockchain_service.get_contract("AmanitaInternational")
        initial_set_cid_calls = contract.set_cid_calls if hasattr(contract, 'set_cid_calls') else None
        
        if initial_set_cid_calls is not None:
            logger.info(f"   Initial set_cid_calls: {initial_set_cid_calls} (before set)")
        
        success = set_product_cid_in_blockchain(
            product_id=product_id,
            field="*",  # Всё поле payload
            lang="en",
            cid=cid_en,
            blockchain_service=e2e_blockchain_service
        )
        
        # Проверки успеха записи
        assert success is True, "Failed to set CID in blockchain"
        
        # Проверка счётчика после записи (если stub)
        if initial_set_cid_calls is not None and hasattr(contract, 'set_cid_calls'):
            assert contract.set_cid_calls >= 1, f"set_cid_calls should be >= 1, got {contract.set_cid_calls}"
            logger.info(f"   set_cid_calls after write: {contract.set_cid_calls} (should be >= 1)")
        
        logger.info("✅ 2.3: CID set in blockchain")
        logger.info(f"   Product ID: {product_id}")
        logger.info(f"   Field: * (all payload)")
        logger.info(f"   Lang: en")
        logger.info(f"   CID: {cid_en}")
        
        # 2.4: Подготовить product JSON без встроенных текстов
        product_metadata = create_minimal_product_metadata(
            product_id=product_id,
            component_ids=["amanita_muscaria"],
            metadata_cid="",  # Не используется в этом тесте
            cover_image_cid="",
            categories=["dried", "powder"],
            forms=["powder", "capsules"],
            species="Amanita muscaria",
            prices=[
                {"price": "100", "currency": "USD", "form": "powder", "weight": "10g"}
            ]
        )
        
        # Проверка плейсхолдеров (критично для E2E - должны быть плейсхолдеры, не реальные тексты)
        assert product_metadata is not None, "Product metadata should be created"
        assert "title" in product_metadata, "Product metadata should contain 'title'"
        assert "description" in product_metadata, "Product metadata should contain 'description'"
        assert product_metadata["title"] == "[title]", f"Title should be placeholder '[title]', got '{product_metadata['title']}'"
        assert product_metadata["description"] == "[description]", f"Description should be placeholder '[description]', got '{product_metadata['description']}'"
        
        logger.info("✅ 2.4: Product metadata created with placeholders")
        logger.info(f"   Product ID: {product_id}")
        logger.info(f"   Title placeholder: {product_metadata['title']} ✅")
        logger.info(f"   Description placeholder: {product_metadata['description']} ✅")
        logger.info(f"   Component IDs: {product_metadata.get('components', [])}")
        logger.info(f"   Forms: {product_metadata.get('forms', [])}")
        logger.info(f"   Species: {product_metadata.get('species', 'N/A')}")
        
        logger.info("✅ Data preparation complete (2.1-2.4)")
        
        # ========================================
        # 3. Действие (E2E поток) (3.1-3.4)
        # ========================================
        logger.info("\n🚀 STAGE 3: E2E Flow Execution")
        
        # 3.1: Выполнить полную десериализацию продукта
        product = await deserialize_product_from_metadata(
            product_metadata=product_metadata,
            blockchain_id=999,  # Тестовый ID
            ipfs_factory=e2e_ipfs_factory,
            product_assembler=real_product_assembler,
            seller="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            is_active=True
        )
        
        # Проверки десериализации
        assert product is not None, "Product should be deserialized"
        assert product.business_id == product_id, f"Expected business_id={product_id}, got {product.business_id}"
        # Критично: product.title должен быть плейсхолдером (не локализованным текстом)
        assert product.title == "[title]", f"Expected product.title='[title]' (placeholder), got '{product.title}'"
        
        logger.info("✅ 3.1: Product deserialized")
        logger.info(f"   Business ID: {product.business_id}")
        logger.info(f"   Title (placeholder): {product.title} ✅")
        logger.info(f"   Description (placeholder): {getattr(product, 'description', 'N/A')}")
        
        # 3.2: Создать LocalizationService(lang='en')
        localization_service = create_localization_service_for_e2e(
            lang="en",
            blockchain_service=e2e_blockchain_service,
            ipfs_factory=e2e_ipfs_factory,
            translation_cache_service=e2e_translation_cache_service,
            fallback_service=None  # Будет создан stub
        )
        
        # Проверки LocalizationService
        assert localization_service is not None, "LocalizationService should be created"
        assert localization_service.lang == "en", f"Expected lang='en', got '{localization_service.lang}'"
        assert localization_service.product_localization is not None, "ProductLocalizationService should be initialized"
        assert hasattr(localization_service, 'product_localization'), "LocalizationService should have product_localization attribute"
        
        logger.info("✅ 3.2: LocalizationService created")
        logger.info(f"   Language: {localization_service.lang}")
        logger.info(f"   ProductLocalizationService: {type(localization_service.product_localization).__name__} ✅")
        
        # 3.3: Запросить переводы через localization_service.t()
        # Сохраняем счётчики ДО запроса переводов
        ipfs_service = e2e_ipfs_factory.get_service()
        contract = e2e_blockchain_service.get_contract("AmanitaInternational")
        
        download_calls_before = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
        get_cid_calls_before = contract.get_cid_calls if hasattr(contract, 'get_cid_calls') else None
        
        if download_calls_before is not None:
            logger.info(f"   IPFS download_calls before translation request: {download_calls_before}")
        if get_cid_calls_before is not None:
            logger.info(f"   Blockchain get_cid_calls before translation request: {get_cid_calls_before}")
        
        translations = get_product_translations_via_localization_service(
            localization_service=localization_service,
            product_id=product_id,
            fields=["title", "description"]
        )
        
        # Проверки переводов
        assert "title" in translations, "Title translation should be returned"
        assert "description" in translations, "Description translation should be returned"
        assert translations["title"] == title_en, f"Expected title='{title_en}', got '{translations['title']}'"
        assert translations["description"] == description_en, f"Expected description='{description_en}', got '{translations['description']}'"
        
        # Проверка счётчиков ПОСЛЕ запроса (если stub)
        download_calls_after = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
        get_cid_calls_after = contract.get_cid_calls if hasattr(contract, 'get_cid_calls') else None
        
        if download_calls_after is not None:
            assert download_calls_after > 0, f"IPFS should be called (download_calls > 0), got {download_calls_after}"
            logger.info(f"   IPFS download_calls after translation request: {download_calls_after} ✅ (> 0)")
        
        if get_cid_calls_after is not None:
            assert get_cid_calls_after > 0, f"Gateway should be called (get_cid_calls > 0), got {get_cid_calls_after}"
            logger.info(f"   Blockchain get_cid_calls after translation request: {get_cid_calls_after} ✅ (> 0)")
        
        logger.info("✅ 3.3: Translations retrieved via localization_service.t()")
        logger.info(f"   Fields: {list(translations.keys())}")
        logger.info(f"   Title: {translations['title'][:50]}... ✅ (from IPFS)")
        logger.info(f"   Description: {translations['description'][:50]}... ✅ (from IPFS)")
        
        # 3.4: Собрать карточку продукта для UI
        card = build_localized_product_card(
            product=product,
            localization_service=localization_service,
            include_fields=["title", "description", "forms"]
        )
        
        # Проверки карточки продукта
        assert card is not None, "Localized card should be built"
        assert card["business_id"] == product_id, f"Expected business_id={product_id}, got '{card['business_id']}'"
        assert card["title"] == title_en, f"Expected localized title='{title_en}', got '{card['title']}'"
        assert card["description"] == description_en, f"Expected localized description='{description_en}', got '{card['description']}'"
        # Критично: не должно быть плейсхолдеров в локализованной карточке
        assert "[title]" not in card["title"], f"Card title should not contain placeholder, got '{card['title']}'"
        assert "[description]" not in card["description"], f"Card description should not contain placeholder, got '{card['description']}'"
        
        logger.info("✅ 3.4: Localized product card built for UI")
        logger.info(f"   Business ID: {card['business_id']}")
        logger.info(f"   Title: {card['title'][:50]}... ✅ (localized from IPFS)")
        logger.info(f"   Description: {card['description'][:50]}... ✅ (localized from IPFS)")
        logger.info(f"   Placeholders removed: ✅ (no '[title]' or '[description]')")
        if "forms" in card:
            logger.info(f"   Forms: {card['forms']}")
        
        logger.info("✅ E2E flow execution complete (3.1-3.4)")
        
        # ========================================
        # 4. Проверки (4.1-4.5)
        # ========================================
        logger.info("\n✅ STAGE 4: Validations")
        
        # 4.1: Источник данных — IPFS
        is_valid, message = validate_ipfs_source_used(
            ipfs_factory=e2e_ipfs_factory,
            blockchain_service=e2e_blockchain_service
        )
        
        assert is_valid, f"IPFS source validation failed: {message}"
        
        # Дополнительные проверки счётчиков
        ipfs_service = e2e_ipfs_factory.get_service()
        if hasattr(ipfs_service, 'download_calls'):
            assert ipfs_service.download_calls > 0, f"IPFS download_calls should be > 0, got {ipfs_service.download_calls}"
            logger.info(f"   IPFS download_calls: {ipfs_service.download_calls} ✅ (> 0)")
        
        contract = e2e_blockchain_service.get_contract("AmanitaInternational")
        if hasattr(contract, 'get_cid_calls'):
            assert contract.get_cid_calls > 0, f"Gateway get_cid_calls should be > 0, got {contract.get_cid_calls}"
            logger.info(f"   Gateway get_cid_calls: {contract.get_cid_calls} ✅ (> 0)")
        
        logger.info("✅ 4.1: IPFS source validated")
        logger.info(f"   Validation message: {message}")
        
        # 4.2: Исключение локальных JSON
        is_valid, message = validate_no_local_json_used(
            captured_logs=caplog.text,
            expected_values={
                "title": title_en,
                "description": description_en
            },
            actual_values={
                "title": card["title"],
                "description": card["description"]
            }
        )
        
        assert is_valid, f"Local JSON exclusion validation failed: {message}"
        
        # Дополнительная проверка логов
        assert "templates/products/" not in caplog.text, "Should not read local JSON templates"
        assert card["title"] != "[title]", f"Should not use placeholder from metadata, got '{card['title']}'"
        assert card["description"] != "[description]", f"Should not use placeholder from metadata, got '{card['description']}'"
        
        logger.info("✅ 4.2: No local JSON validated")
        logger.info(f"   Validation message: {message}")
        logger.info(f"   No templates/products/ in logs: ✅")
        logger.info(f"   Placeholders not used: ✅ (title != '[title]', description != '[description]')")
        
        # 4.3: Значения корректны
        is_valid, message = validate_translation_values_correct(
            actual_values={
                "title": card["title"],
                "description": card["description"]
            },
            expected_values={
                "title": title_en,
                "description": description_en
            }
        )
        
        assert is_valid, f"Translation values validation failed: {message}"
        
        # Дополнительные проверки значений
        assert card["title"] == title_en, f"Expected '{title_en}', got '{card['title']}'"
        assert card["description"] == description_en, f"Expected '{description_en}', got '{card['description']}'"
        
        logger.info("✅ 4.3: Translation values validated")
        logger.info(f"   Validation message: {message}")
        logger.info(f"   Title match: ✅ ('{card['title']}' == '{title_en}')")
        logger.info(f"   Description match: ✅ ('{card['description'][:50]}...' == '{description_en[:50]}...')")
        
        # 4.4: Кэширование работает
        ipfs_service = e2e_ipfs_factory.get_service()
        
        # Первый запрос (уже выполнен в 3.3)
        first_call_count = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
        
        if first_call_count is not None:
            logger.info(f"   First request download_calls: {first_call_count}")
        
        # Второй запрос (должен использовать кэш)
        translations_2 = get_product_translations_via_localization_service(
            localization_service=localization_service,
            product_id=product_id,
            fields=["title", "description"]
        )
        
        second_call_count = ipfs_service.download_calls if hasattr(ipfs_service, 'download_calls') else None
        
        if first_call_count is not None and second_call_count is not None:
            is_valid, message = validate_caching_works(
                ipfs_factory=e2e_ipfs_factory,
                first_call_count=first_call_count,
                second_call_count=second_call_count
            )
            
            assert is_valid, f"Cache validation failed: {message}"
            assert second_call_count == first_call_count, f"IPFS should not be called on second request: {first_call_count} → {second_call_count}"
            
            logger.info(f"   Second request download_calls: {second_call_count} ✅ (== {first_call_count}, cache used)")
        else:
            logger.warning("⚠️ 4.4: IPFS download_calls counter not available (using real IPFS)")
        
        # Проверка значений идентичны
        assert translations_2["title"] == translations["title"], "Cached value should match first request"
        assert translations_2["description"] == translations["description"], "Cached description should match first request"
        
        logger.info("✅ 4.4: Caching validated")
        logger.info(f"   Cached title match: ✅ ('{translations_2['title']}' == '{translations['title']}')")
        logger.info(f"   Cached description match: ✅")
        
        # 4.5: Честность падения — fallback на плейсхолдеры
        # Создаём новый LocalizationService для чистого теста
        localization_service_fallback = create_localization_service_for_e2e(
            lang="en",
            blockchain_service=e2e_blockchain_service,
            ipfs_factory=e2e_ipfs_factory,
            translation_cache_service=e2e_translation_cache_service
        )
        
        logger.info("   Created new LocalizationService for fallback test")
        
        # Очищаем IPFS хранилище (если stub)
        ipfs_service = e2e_ipfs_factory.get_service()
        if hasattr(ipfs_service, '_storage'):
            ipfs_service._storage.clear()
            logger.info("   IPFS storage cleared for fallback test")
        
        # Очищаем кэш
        e2e_translation_cache_service.clear_cache()
        logger.info("   Cache cleared for fallback test")
        
        # Проверяем fallback
        is_valid, message = validate_fallback_placeholders_when_ipfs_disabled(
            localization_service=localization_service_fallback,
            product_id=product_id,
            ipfs_factory=e2e_ipfs_factory
        )
        
        assert is_valid, f"Fallback validation failed: {message}"
        
        # Дополнительная проверка: должен вернуть плейсхолдер или ключ
        title_fallback = localization_service_fallback.t(f'product.{product_id}.title', default=None)
        expected_fallback_values = ["[title]", f"product.{product_id}.title"]
        assert title_fallback in expected_fallback_values, \
            f"Expected fallback to be one of {expected_fallback_values}, got: {title_fallback}"
        
        logger.info("✅ 4.5: Fallback placeholders validated")
        logger.info(f"   Validation message: {message}")
        logger.info(f"   Title fallback: {title_fallback} ✅ (placeholder or key)")
        
        logger.info("✅ All validations complete (4.1-4.5)")
        
        # ========================================
        # 5. Вариации/мутации (5.1-5.2)
        # ========================================
        logger.info("\n🔄 STAGE 5: Variations")
        
        # 5.1: Обновление CID инвалидирует кэш
        logger.info("\n📝 5.1: Cache Invalidation on CID Update")
        
        # Подготавливаем новый payload
        title_updated = "Amanita Powder UPDATED (E2E Test)"
        description_updated = "Updated description for cache invalidation test."
        
        payload_updated = create_product_ipfs_payload(
            title=title_updated,
            description=description_updated,
            forms=["powder"]
        )
        
        logger.info(f"   Created updated payload: title='{title_updated}'")
        
        cid_updated = upload_product_payload_to_ipfs(
            payload=payload_updated,
            ipfs_factory=e2e_ipfs_factory,
            language="en"
        )
        
        assert cid_updated is not None, "Updated CID should be returned"
        logger.info(f"   Uploaded updated payload: CID={cid_updated}")
        
        # Восстанавливаем IPFS хранилище для первого CID (если очистили в 4.5)
        ipfs_service = e2e_ipfs_factory.get_service()
        if hasattr(ipfs_service, '_storage') and cid_en not in ipfs_service._storage:
            ipfs_service.upload_json(payload_en)
            logger.info(f"   Restored original payload in IPFS storage: CID={cid_en}")
        
        is_valid, message = validate_cache_invalidation_on_cid_update(
            product_id=product_id,
            field="*",
            lang="en",
            old_cid=cid_en,
            new_cid=cid_updated,
            new_payload=payload_updated,
            ipfs_factory=e2e_ipfs_factory,
            blockchain_service=e2e_blockchain_service,
            localization_service=localization_service,
            expected_new_value=title_updated
        )
        
        assert is_valid, f"Cache invalidation validation failed: {message}"
        logger.info("✅ 5.1: Cache invalidation on CID update validated")
        logger.info(f"   Validation message: {message}")
        
        # 5.2: Независимость кэшей по языкам
        logger.info("\n📝 5.2: Multilingual Cache Independence")
        
        # Подготавливаем русский payload
        title_ru = "Порошок мухомора (E2E тест)"
        description_ru = "Премиум сушёный порошок мухомора для тестирования локализации через IPFS."
        
        payload_ru = create_product_ipfs_payload(
            title=title_ru,
            description=description_ru,
            forms=["порошок", "капсулы"]
        )
        
        logger.info(f"   Created Russian payload: title='{title_ru}'")
        
        is_valid, message = validate_multilingual_cache_independence(
            product_id=product_id,
            field="*",
            en_payload=payload_en,
            ru_payload=payload_ru,
            ipfs_factory=e2e_ipfs_factory,
            blockchain_service=e2e_blockchain_service,
            translation_cache_service=e2e_translation_cache_service
        )
        
        assert is_valid, f"Multilingual cache independence validation failed: {message}"
        logger.info("✅ 5.2: Multilingual cache independence validated")
        logger.info(f"   Validation message: {message}")
        
        logger.info("✅ All variations complete (5.1-5.2)")
        
        # ========================================
        # FINAL VERIFICATION
        # ========================================
        logger.info("\n" + "="*80)
        logger.info("🎉 E2E TEST PASSED: Product Localization via IPFS/CID")
        logger.info("="*80)
        logger.info(f"✅ STAGE 1: Environment setup")
        logger.info(f"✅ STAGE 2: Data preparation")
        logger.info(f"✅ STAGE 3: E2E flow execution")
        logger.info(f"✅ STAGE 4: All validations (4.1-4.5)")
        logger.info(f"✅ STAGE 5: All variations (5.1-5.2)")
        logger.info(f"")
        logger.info(f"📊 METRICS:")
        logger.info(f"   Product ID: {product_id}")
        logger.info(f"   Title: {card['title']}")
        logger.info(f"   Description: {card['description'][:50]}...")
        logger.info(f"   IPFS CID: {cid_en}")
        logger.info(f"   Cache working: ✅")
        logger.info(f"   Fallback working: ✅")
        logger.info("="*80)

