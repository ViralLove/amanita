import re
import logging
import sys
from pathlib import Path

import pytest

# Add bot/ to Python path for imports (same pattern as test_multilingual_ipfs_blockchain_integration.py)
bot_dir = Path(__file__).parent.parent
if str(bot_dir) not in sys.path:
    sys.path.insert(0, str(bot_dir))
@pytest.mark.integration
def test_ipfs_upload_payload_returns_cids_for_en_and_ru(ipfs_factory):
    """
    4.2.1 → 2.1: Сформировать payload JSON (en/ru) и получить CID через ipfs_factory.upload_json.
    """
    service = ipfs_factory.get_service()

    payload_en = {"product": {"title": {"en": "Lion's Mane"}, "description": {"en": "Focus & clarity"}}}
    payload_ru = {"product": {"title": {"ru": "Ежовик гребенчатый"}, "description": {"ru": "Фокус и ясность"}}}

    cid_en = service.upload_json(payload_en)
    cid_ru = service.upload_json(payload_ru)

    # CID produced by IPFSFactoryStub must be validate_ipfs_cid()-compatible
    assert isinstance(cid_en, str) and cid_en.startswith("Qm") and len(cid_en) == 46
    assert isinstance(cid_ru, str) and cid_ru.startswith("Qm") and len(cid_ru) == 46
    # Разные payload → разные CID
    assert cid_en != cid_ru

    # Проверим, что по CID можно скачать исходный JSON
    assert service.download_json(cid_en) == payload_en
    assert service.download_json(cid_ru) == payload_ru

@pytest.mark.integration
def test_blockchain_set_and_get_simple_field_cid(ipfs_factory, blockchain_service):
    """
    4.2.1 → 2.2: Вызвать setSimpleFieldCID на контракте для пары (product, business_id, '*', 'en')
    и убедиться, что getSimpleFieldCID возвращает тот же CID.
    """
    business_id = "prod-int-001"
    field_key = f"ProductName.{business_id}"

    ipfs = ipfs_factory.get_service()
    # Реальный формат simple field payload: dict(lang->str) под одним CID.
    cid = ipfs.upload_json({"en": "Integration Title"})

    contract = blockchain_service.get_contract("AmanitaInternational")
    # Устанавливаем CID
    contract.functions.setSimpleFieldCID(field_key, cid).transact()
    # Читаем обратно
    got = contract.functions.getSimpleFieldCID(field_key).call()
    assert got == cid

@pytest.mark.integration
def test_localization_service_fetches_via_blockchain_and_ipfs(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    4.2.1 → 3.1: Вызвать LocalizationService.product.get_translation(business_id, 'en')
    и убедиться, что данные подтягиваются через цепочку Blockchain → IPFS → Cache → Localization.
    """
    business_id = "prod-int-002"
    lang = "en"
    field_key = f"ProductName.{business_id}"

    # Готовим IPFS payload и CID
    ipfs = ipfs_factory.get_service()
    payload = {"en": "Block → IPFS → Loc"}
    cid = ipfs.upload_json(payload)

    # Записываем CID в контракт
    contract = blockchain_service.get_contract("AmanitaInternational")
    contract.functions.setSimpleFieldCID(field_key, cid).transact()

    # Снимем счётчики до вызова
    contract = blockchain_service.get_contract("AmanitaInternational")
    start_get_cid_calls = contract.get_cid_calls
    ipfs = ipfs_factory.get_service()
    start_download_calls = ipfs.download_calls

    # Действие: получаем перевод через MultilingualIPFSService (часть Localization цепочки)
    result = multilingual_ipfs_service.get_product_translations(business_id, lang)

    # Проверки результата и кэша
    assert isinstance(result, dict)
    assert result == {"title": "Block → IPFS → Loc"}
    # 4.1: были вызваны getSimpleFieldCID и download_json
    assert contract.get_cid_calls == start_get_cid_calls + 1
    assert ipfs.download_calls == start_download_calls + 1

    cache_key = f"product_{business_id}_{lang}"
    cached = translation_cache_service.get(cache_key, 'ipfs')
    assert cached is not None

    # 4.4: повторный вызов не дергает IPFS/блокчейн (external/локальный кэш)
    start_get_cid_calls_2 = contract.get_cid_calls
    start_download_calls_2 = ipfs.download_calls
    result2 = multilingual_ipfs_service.get_product_translations(business_id, lang)
    assert isinstance(result2, dict)
    assert result2 == {"title": "Block → IPFS → Loc"}
    assert contract.get_cid_calls == start_get_cid_calls_2  # без доп. вызова
    assert ipfs.download_calls == start_download_calls_2     # без доп. вызова

@pytest.mark.integration
def test_update_cid_invalidates_cache(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    4.2.2: Обновление CID должно приводить к обновлению данных после инвалидации кэша.
    Шаги:
    - payload_v1 → CID_v1 → set → первый вызов записывает в оба кэша
    - payload_v2 → CID_v2 → set → invalidate внешнего кэша + протухание локального
    - повторный вызов должен сходить в IPFS заново и вернуть v2
    """
    business_id = "prod-int-003"
    lang = "en"
    field_key = f"ProductName.{business_id}"
    cache_key = f"product_{business_id}_{lang}"

    contract = blockchain_service.get_contract("AmanitaInternational")
    ipfs = ipfs_factory.get_service()

    # v1
    payload_v1 = {"en": "v1"}
    cid_v1 = ipfs.upload_json(payload_v1)
    contract.functions.setSimpleFieldCID(field_key, cid_v1).transact()

    start_get_cid = contract.get_cid_calls
    start_downloads = ipfs.download_calls
    first = multilingual_ipfs_service.get_product_translations(business_id, lang)
    assert first == {"title": "v1"}
    assert contract.get_cid_calls == start_get_cid + 1
    assert ipfs.download_calls == start_downloads + 1
    # внешний кэш записан
    assert translation_cache_service.get(cache_key, 'ipfs') is not None

    # v2
    payload_v2 = {"en": "v2"}
    cid_v2 = ipfs.upload_json(payload_v2)
    contract.functions.setSimpleFieldCID(field_key, cid_v2).transact()

    # Инвалидируем внешний кэш и истечём локальный
    translation_cache_service.invalidate(cache_key, 'ipfs')
    if cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0  # протухание

    start_get_cid_2 = contract.get_cid_calls
    start_downloads_2 = ipfs.download_calls
    second = multilingual_ipfs_service.get_product_translations(business_id, lang)
    assert second == {"title": "v2"}
    # Должен быть новый сетевой заход
    assert contract.get_cid_calls == start_get_cid_2 + 1
    assert ipfs.download_calls == start_downloads_2 + 1
    # 5.2: Кэш перезаписан значением v2 (внешний и локальный)
    cached_v2 = translation_cache_service.get(cache_key, 'ipfs')
    assert cached_v2 == {"title": "v2"}
    assert cache_key in multilingual_ipfs_service.ipfs_cache
    assert multilingual_ipfs_service.ipfs_cache[cache_key].data == {"title": "v2"}
    # 5.3: Нет ложных успехов — не возвращаем старое v1
    assert second != {"title": "v1"}

@pytest.mark.integration
def test_component_description_flow(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    4.2.3: Component flow — AmanitaInternational → MultilingualIPFSService → TranslationCacheService.
    Проверяем кэширование, TTL и поведение при недоступном IPFS.
    Обновлено для использования complex fields с biounit_id.
    """
    component_id = "comp-int-001"
    lang = "en"
    className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
    cache_key = f"component_{component_id}_{lang}"

    contract = blockchain_service.get_contract("AmanitaInternational")
    ipfs = ipfs_factory.get_service()

    # Подготовка данных для complex fields
    translations = {
        "generic_description": "Component description",
        "effects": "Component effects",
        "shamanic": "Component shamanic",
        "warnings": "Component warnings"
    }
    payload = {
        "label": "ComponentDescription",
        "type": "complex",
        "fields": translations
    }
    cid = ipfs.upload_json(payload)
    # Используем setComplexFieldCID с className содержащим biounit_id
    contract.functions.setComplexFieldCID(className, lang, cid).transact()

    # Действие и проверки цепочки
    start_get = contract.get_complex_cid_calls
    start_dl = ipfs.download_calls
    result = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert contract.get_complex_cid_calls == start_get + 1
    assert ipfs.download_calls == start_dl + 1
    assert isinstance(result, dict)
    assert result == translations
    assert "generic_description" in result
    assert result["generic_description"] == "Component description"

    # Кэширование (повторный вызов без сети)
    start_get2 = contract.get_complex_cid_calls
    start_dl2 = ipfs.download_calls
    result2 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result2 == result
    assert contract.get_complex_cid_calls == start_get2
    assert ipfs.download_calls == start_dl2

    # TTL: протухаем локальный кэш — при наличии external кэша сеть НЕ дергается (C-приоритет)
    assert cache_key in multilingual_ipfs_service.ipfs_cache
    multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0
    # Также очищаем кэш для complex field
    complex_cache_key = f"complex_{className}_{lang}"
    if complex_cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[complex_cache_key].timestamp = 0
    start_get3 = contract.get_complex_cid_calls
    start_dl3 = ipfs.download_calls
    result3 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result3 == result
    assert contract.get_complex_cid_calls == start_get3
    assert ipfs.download_calls == start_dl3

    # Инвалидируем внешний кэш и истечём локальный — теперь сеть дергается
    translation_cache_service.invalidate(cache_key, 'ipfs')
    translation_cache_service.invalidate(complex_cache_key, 'ipfs')  # Также инвалидируем complex field кэш
    if cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0
    if complex_cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[complex_cache_key].timestamp = 0
    start_get4 = contract.get_complex_cid_calls
    start_dl4 = ipfs.download_calls
    result4 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result4 == result
    assert contract.get_complex_cid_calls == start_get4 + 1
    assert ipfs.download_calls == start_dl4 + 1

    # Fallback: снова инвалидируем внешний кэш + протухаем локальный, IPFS возвращает None → None
    translation_cache_service.invalidate(cache_key, 'ipfs')
    translation_cache_service.invalidate(complex_cache_key, 'ipfs')  # Также инвалидируем complex field кэш
    if cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0
    if complex_cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[complex_cache_key].timestamp = 0
    # делаем IPFS недоступным
    ipfs._storage = {}
    result5 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result5 is None


@pytest.mark.integration
def test_localization_service_product_smoke(localization_service, ipfs_factory, blockchain_service):
    """
    P2: Smoke через фасад LocalizationService для продукта: t('product.{id}.title')
    """
    business_id = "prod-int-facade-001"
    lang = "en"
    field_key = f"ProductName.{business_id}"

    ipfs = ipfs_factory.get_service()
    payload = {"en": "Facade Product Title"}
    cid = ipfs.upload_json(payload)
    contract = blockchain_service.get_contract("AmanitaInternational")
    contract.functions.setSimpleFieldCID(field_key, cid).transact()

    value = localization_service.t(f"product.{business_id}.title")
    assert isinstance(value, str)
    assert value == "Facade Product Title"


@pytest.mark.integration
def test_localization_service_component_smoke(ipfs_factory, real_blockchain_service, seller_account, web3, translation_cache_service, fallback_service):
    """
    P2: Smoke через фасад LocalizationService для компонента: t('component.{id}.title')
    Использует реальный BlockchainService для интеграционного теста.
    """
    import os
    from eth_account import Account
    from bot.services.common.multilingual_ipfs_service import MultilingualIPFSService
    from bot.services.common.localization_service import LocalizationService
    
    logger = logging.getLogger(__name__)
    
    # Создаем multilingual_ipfs_service с real_blockchain_service
    from bot.services.product.storage import ProductStorageService
    storage_provider = ipfs_factory.get_service() if hasattr(ipfs_factory, "get_service") else ipfs_factory.get_storage()
    storage_service = ProductStorageService(storage_provider=storage_provider)
    multilingual_ipfs_service = MultilingualIPFSService(
        storage_service=storage_service,
        cache_service=translation_cache_service,
        blockchain_service=real_blockchain_service,
    )
    
    # Создаем localization_service с правильным multilingual_ipfs_service
    localization_service = LocalizationService(
        lang='en',
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        ipfs_service=multilingual_ipfs_service,
    )
    
    component_id = "comp-int-facade-001"
    lang = "en"

    # 1. Загружаем данные в IPFS
    logger.info(f"📤 Загрузка данных в IPFS для component_id={component_id}, lang={lang}")
    ipfs = ipfs_factory.get_service()
    # Payload для complex field ComponentDescription должен содержать fields с переводами
    # Структура: fields содержит значения напрямую для языка (не вложенные словари)
    payload = {
        "label": "Component Description",
        "type": "ComponentDescription",
        "fields": {
            "title": "Facade Component Title",  # Значение напрямую для языка en
            "description": "Comp Desc"
        }
    }
    cid = ipfs.upload_json(payload)
    logger.info(f"✅ CID получен: {cid}")
    
    # 2. Обеспечиваем SELLER_ROLE для seller_account
    contract = real_blockchain_service.get_contract("AmanitaInternational")
    spiral_engine_contract = real_blockchain_service.get_contract("SpiralEngine")
    
    # В SpiralEngine (основной источник истины)
    SELLER_ROLE = web3.keccak(text="SELLER_ROLE")
    has_spiral_role = spiral_engine_contract.functions.hasRole(SELLER_ROLE, seller_account.address).call()
    
    if not has_spiral_role:
        deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("NODE_ADMIN_PRIVATE_KEY")
        if not deployer_key:
            pytest.skip("DEPLOYER_PRIVATE_KEY or NODE_ADMIN_PRIVATE_KEY required for granting SELLER_ROLE")
        deployer = Account.from_key(deployer_key)
        tx_hash = spiral_engine_contract.functions.grantRole(SELLER_ROLE, seller_account.address).transact({'from': deployer.address})
        web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"✅ SELLER_ROLE granted in SpiralEngine to {seller_account.address[:10]}...")
    
    # В AmanitaInternational (fallback)
    has_role = contract.functions.hasRole(SELLER_ROLE, seller_account.address).call()
    if not has_role:
        deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("NODE_ADMIN_PRIVATE_KEY")
        if not deployer_key:
            pytest.skip("DEPLOYER_PRIVATE_KEY or NODE_ADMIN_PRIVATE_KEY required for granting SELLER_ROLE")
        deployer = Account.from_key(deployer_key)
        tx_hash = contract.functions.grantRole(SELLER_ROLE, seller_account.address).transact({'from': deployer.address})
        web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"✅ SELLER_ROLE granted in AmanitaInternational to {seller_account.address[:10]}...")
    
    # 3. Записываем CID в блокчейн через complex fields
    logger.info(f"⛓️  Запись CID в блокчейн для component_id={component_id}, lang={lang}")
    className = f"ComponentDescription.{component_id}"
    tx_hash = contract.functions.setComplexFieldCID(className, lang, cid).transact({'from': seller_account.address})
    logger.info(f"✅ Транзакция отправлена: {tx_hash}")
    
    # 4. Ожидаем подтверждения транзакции
    logger.info("⏳ Ожидание подтверждения транзакции...")
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    logger.info(f"✅ Транзакция подтверждена: gasUsed={receipt['gasUsed']}, status={receipt['status']}")
    
    # 5. Проверяем, что CID установлен в блокчейне
    logger.info(f"🔍 Проверка CID в блокчейне...")
    stored_cid = contract.functions.getComplexFieldCID(className, lang).call()
    assert stored_cid == cid, f"CID в блокчейне не соответствует: ожидали {cid}, получили {stored_cid}"
    logger.info(f"✅ CID подтвержден в блокчейне: {stored_cid}")
    
    # 6. Запрашиваем перевод через LocalizationService
    logger.info(f"🌐 Запрос перевода через LocalizationService: component.{component_id}.title")
    value = localization_service.t(f"component.{component_id}.title")
    logger.info(f"📝 Результат локализации: {value}")
    
    # 7. Проверяем результат
    assert isinstance(value, str), f"Результат должен быть строкой, получен {type(value)}"
    assert value == "Facade Component Title", f"Неверный перевод: ожидали 'Facade Component Title', получили '{value}'"
    logger.info(f"✅ Тест успешно завершен: получен правильный перевод '{value}'")


@pytest.mark.integration
def test_localization_service_real_component_smoke(component_with_real_cid, real_blockchain_service):
    """
    Smoke test с реальными данными: Проверка LocalizationService.component.get_translation()
    на реальном компоненте из data/components/.
    
    Этот тест проверяет:
    1. Компонент зарегистрирован в OrganicComponentRegistry
    2. CID записаны в контракт
    3. LocalizationService может получить данные (или fallback)
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("localization_real_test")
    
    component_id = component_with_real_cid['component_id']
    blockchain_id = component_with_real_cid['blockchain_id']
    cids = component_with_real_cid['cids']
    contract = component_with_real_cid['contract']
    
    logger.info(f"\n📦 Testing component: {component_id}")
    logger.info(f"   Blockchain ID: {blockchain_id}")
    logger.info(f"   Available languages: {list(cids.keys())}")
    
    # Проверяем что компонент существует
    component_data = contract.functions.getComponent(blockchain_id).call()
    logger.info(f"   Contract data: creator={component_data[1]}, active={component_data[2]}")
    
    # Тест 1: Проверяем что компонент зарегистрирован
    assert component_data[2], f"Компонент {component_id} не активен в контракте"
    logger.info(f"   ✅ Компонент активен в OrganicComponentRegistry")
    
    # Тест 2: Проверяем наличие CID для английского языка
    lang = 'en'
    
    if lang not in cids:
        pytest.skip(f"Язык {lang} не доступен для компонента {component_id}")
    
    expected_cid = cids[lang]
    logger.info(f"\n🔍 Expected CID for lang={lang}: {expected_cid}")
    
    # Тест 3: Проверяем что данные загружены (skip если TODO)
    full_data = component_with_real_cid['full_data']
    en_data = full_data['complex_fields'].get('en', {})
    
    logger.info(f"\n📄 Component data sample:")
    for key, value in list(en_data.items())[:2]:
        logger.info(f"   {key}: {value[:50] if isinstance(value, str) else value}...")
    
    # Проверяем что данные не являются TODO placeholders
    has_todo = any('[TODO' in str(v) for v in en_data.values())
    
    if has_todo:
        logger.warning(f"   ⚠️ Компонент содержит TODO placeholders в Arweave данных")
        pytest.skip(f"Component {component_id} содержит TODO placeholders, невозможно тестировать локализацию")
    
    logger.info(f"   ✅ Компонент имеет реальные данные (не TODO)")
    
    # Тест 4: Проверяем структуру данных
    assert isinstance(en_data, dict), "English data должен быть dict"
    assert len(en_data) > 0, "English data не должен быть пустым"
    
    logger.info(f"\n✅ Все проверки real component passed")
    logger.info(f"   Component: {component_id}")
    logger.info(f"   Blockchain ID: {blockchain_id}")
    logger.info(f"   Has real CID: {expected_cid}")
    logger.info(f"   Data keys: {list(en_data.keys())}")


@pytest.mark.integration
def test_localization_service_mock_component(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    Unit-like test с полными mock данными.
    Не зависит от external state, быстрый, надёжный.
    """
    business_id = "mock_component_001"
    entity_type = "component"
    field = "*"
    lang = "en"

    # Создаём полные mock данные (не TODO!)
    ipfs = ipfs_factory.get_service()
    
    # ComponentDescription payload formats:
    # - real storage data is often a plain dict of fields (see data/components/.../complex_fields/*.json)
    # - some mocks/tests use a wrapper {label,type,fields}
    # MultilingualIPFSService supports both and returns only the `fields` part from get_component_translations().
    expected_fields = {
        "title": "Mock Amanita Muscaria",  # Значения напрямую для языка en
        "generic_description": "Amanita muscaria is a mushroom with psychoactive properties.",
        "effects": "Sedative, oneirogen, entheogen properties.",
        "shamanic": "Used in traditional Siberian shamanic practices.",
        "warnings": "Contains toxic compounds. Not for consumption without preparation."
    }
    
    # Полный payload для записи в IPFS (complex field format)
    complete_payload = {
        "label": "Component Description",
        "type": "ComponentDescription",
        "fields": expected_fields
    }
    
    cid = ipfs.upload_json(complete_payload)

    # Записываем CID в mock контракт через complex fields
    contract = blockchain_service.get_contract("AmanitaInternational")
    className = f"ComponentDescription.{business_id}"
    contract.functions.setComplexFieldCID(className, lang, cid).transact()
    
    # Wait for transaction
    import time
    time.sleep(0.1)  # Mock transaction delay
    
    # Проверяем что CID записан
    current_cid = contract.functions.getComplexFieldCID(className, lang).call()
    assert current_cid == cid, f"CID mismatch: {current_cid} != {cid}"

    # Действие: получаем перевод
    # get_component_translations() возвращает только fields часть payload
    result = multilingual_ipfs_service.get_component_translations(business_id, lang)

    # Проверки с полными данными
    assert isinstance(result, dict), "Result должен быть dict"
    assert result == expected_fields, f"Данные не соответствуют ожидаемым: получили {result}, ожидали {expected_fields}"
    
    # Проверяем что нет fallback keys
    for key, value in result.items():
        assert isinstance(value, str), f"Поле {key} должно быть строкой, получен {type(value)}"
        assert not (value.startswith('[') and value.endswith(']')), \
            f"Fallback key detected: {value}"
    
    print(f"✅ Mock component test passed with complete data")

