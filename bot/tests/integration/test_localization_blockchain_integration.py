import re


def test_ipfs_upload_payload_returns_cids_for_en_and_ru(ipfs_factory):
    """
    4.2.1 → 2.1: Сформировать payload JSON (en/ru) и получить CID через ipfs_factory.upload_json.
    """
    service = ipfs_factory.get_service()

    payload_en = {"product": {"title": {"en": "Lion's Mane"}, "description": {"en": "Focus & clarity"}}}
    payload_ru = {"product": {"title": {"ru": "Ежовик гребенчатый"}, "description": {"ru": "Фокус и ясность"}}}

    cid_en = service.upload_json(payload_en)
    cid_ru = service.upload_json(payload_ru)

    assert isinstance(cid_en, str) and cid_en.startswith("cid://")
    assert isinstance(cid_ru, str) and cid_ru.startswith("cid://")
    # Разные payload → разные CID
    assert cid_en != cid_ru

    # Проверим, что по CID можно скачать исходный JSON
    assert service.download_json(cid_en) == payload_en
    assert service.download_json(cid_ru) == payload_ru

def test_blockchain_set_and_get_simple_field_cid(ipfs_factory, blockchain_service):
    """
    4.2.1 → 2.2: Вызвать setSimpleFieldCID на контракте для пары (product, business_id, '*', 'en')
    и убедиться, что getSimpleFieldCID возвращает тот же CID.
    """
    business_id = "prod-int-001"
    entity_type = "product"
    field = "*"
    lang = "en"

    ipfs = ipfs_factory.get_service()
    cid = ipfs.upload_json({"product": {"title": {"en": "Integration Title"}}})

    contract = blockchain_service.get_contract("AmanitaInternational")
    # Устанавливаем CID
    contract.functions.setSimpleFieldCID(entity_type, business_id, field, lang, cid).transact()
    # Читаем обратно
    got = contract.functions.getSimpleFieldCID(entity_type, business_id, field, lang).call()
    assert got == cid

def test_localization_service_fetches_via_blockchain_and_ipfs(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    4.2.1 → 3.1: Вызвать LocalizationService.product.get_translation(business_id, 'en')
    и убедиться, что данные подтягиваются через цепочку Blockchain → IPFS → Cache → Localization.
    """
    business_id = "prod-int-002"
    entity_type = "product"
    field = "*"
    lang = "en"

    # Готовим IPFS payload и CID
    ipfs = ipfs_factory.get_service()
    payload = {"product": {"title": {"en": "Block → IPFS → Loc"}, "description": {"en": "Integration path"}}}
    cid = ipfs.upload_json(payload)

    # Записываем CID в контракт
    contract = blockchain_service.get_contract("AmanitaInternational")
    contract.functions.setSimpleFieldCID(entity_type, business_id, field, lang, cid).transact()

    # Снимем счётчики до вызова
    contract = blockchain_service.get_contract("AmanitaInternational")
    start_get_cid_calls = contract.get_cid_calls
    ipfs = ipfs_factory.get_service()
    start_download_calls = ipfs.download_calls

    # Действие: получаем перевод через MultilingualIPFSService (часть Localization цепочки)
    result = multilingual_ipfs_service.get_product_translations(business_id, lang)

    # Проверки результата и кэша
    assert isinstance(result, dict)
    # Это исходный JSON из IPFS
    assert result == payload
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
    assert result2 == payload
    assert contract.get_cid_calls == start_get_cid_calls_2  # без доп. вызова
    assert ipfs.download_calls == start_download_calls_2     # без доп. вызова

def test_update_cid_invalidates_cache(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    4.2.2: Обновление CID должно приводить к обновлению данных после инвалидации кэша.
    Шаги:
    - payload_v1 → CID_v1 → set → первый вызов записывает в оба кэша
    - payload_v2 → CID_v2 → set → invalidate внешнего кэша + протухание локального
    - повторный вызов должен сходить в IPFS заново и вернуть v2
    """
    business_id = "prod-int-003"
    entity_type = "product"
    field = "*"
    lang = "en"
    cache_key = f"product_{business_id}_{lang}"

    contract = blockchain_service.get_contract("AmanitaInternational")
    ipfs = ipfs_factory.get_service()

    # v1
    payload_v1 = {"product": {"title": {"en": "v1"}, "description": {"en": "first"}}}
    cid_v1 = ipfs.upload_json(payload_v1)
    contract.functions.setSimpleFieldCID(entity_type, business_id, field, lang, cid_v1).transact()

    start_get_cid = contract.get_cid_calls
    start_downloads = ipfs.download_calls
    first = multilingual_ipfs_service.get_product_translations(business_id, lang)
    assert first == payload_v1
    assert contract.get_cid_calls == start_get_cid + 1
    assert ipfs.download_calls == start_downloads + 1
    # внешний кэш записан
    assert translation_cache_service.get(cache_key, 'ipfs') is not None

    # v2
    payload_v2 = {"product": {"title": {"en": "v2"}, "description": {"en": "second"}}}
    cid_v2 = ipfs.upload_json(payload_v2)
    contract.functions.setSimpleFieldCID(entity_type, business_id, field, lang, cid_v2).transact()

    # Инвалидируем внешний кэш и истечём локальный
    translation_cache_service.invalidate(cache_key, 'ipfs')
    if cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0  # протухание

    start_get_cid_2 = contract.get_cid_calls
    start_downloads_2 = ipfs.download_calls
    second = multilingual_ipfs_service.get_product_translations(business_id, lang)
    assert second == payload_v2
    # Должен быть новый сетевой заход
    assert contract.get_cid_calls == start_get_cid_2 + 1
    assert ipfs.download_calls == start_downloads_2 + 1
    # 5.2: Кэш перезаписан значением v2 (внешний и локальный)
    cached_v2 = translation_cache_service.get(cache_key, 'ipfs')
    assert cached_v2 == payload_v2
    assert cache_key in multilingual_ipfs_service.ipfs_cache
    assert multilingual_ipfs_service.ipfs_cache[cache_key].data == payload_v2
    # 5.3: Нет ложных успехов — не возвращаем старое v1
    assert second != payload_v1

def test_component_description_flow(multilingual_ipfs_service, ipfs_factory, blockchain_service, translation_cache_service):
    """
    4.2.3: Component flow — AmanitaInternational → MultilingualIPFSService → TranslationCacheService.
    Проверяем кэширование, TTL и поведение при недоступном IPFS.
    """
    component_id = "comp-int-001"
    entity_type = "component"
    field = "*"
    lang = "en"
    cache_key = f"component_{component_id}_{lang}"

    contract = blockchain_service.get_contract("AmanitaInternational")
    ipfs = ipfs_factory.get_service()

    # Подготовка данных
    payload = {"component": {"title": {"en": "Component EN"}, "description": {"en": "Component description"}}}
    cid = ipfs.upload_json(payload)
    contract.functions.setSimpleFieldCID(entity_type, component_id, field, lang, cid).transact()

    # Действие и проверки цепочки
    start_get = contract.get_cid_calls
    start_dl = ipfs.download_calls
    result = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert contract.get_cid_calls == start_get + 1
    assert ipfs.download_calls == start_dl + 1
    assert isinstance(result, dict)
    assert "component" in result and "title" in result["component"]

    # Кэширование (повторный вызов без сети)
    start_get2 = contract.get_cid_calls
    start_dl2 = ipfs.download_calls
    result2 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result2 == result
    assert contract.get_cid_calls == start_get2
    assert ipfs.download_calls == start_dl2

    # TTL: протухаем локальный кэш — при наличии external кэша сеть НЕ дергается (C-приоритет)
    assert cache_key in multilingual_ipfs_service.ipfs_cache
    multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0
    start_get3 = contract.get_cid_calls
    start_dl3 = ipfs.download_calls
    result3 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result3 == result
    assert contract.get_cid_calls == start_get3
    assert ipfs.download_calls == start_dl3

    # Инвалидируем внешний кэш и истечём локальный — теперь сеть дергается
    translation_cache_service.invalidate(cache_key, 'ipfs')
    if cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0
    start_get4 = contract.get_cid_calls
    start_dl4 = ipfs.download_calls
    result4 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result4 == result
    assert contract.get_cid_calls == start_get4 + 1
    assert ipfs.download_calls == start_dl4 + 1

    # Fallback: снова инвалидируем внешний кэш + протухаем локальный, IPFS возвращает None → None
    translation_cache_service.invalidate(cache_key, 'ipfs')
    if cache_key in multilingual_ipfs_service.ipfs_cache:
        multilingual_ipfs_service.ipfs_cache[cache_key].timestamp = 0
    # делаем IPFS недоступным
    ipfs._storage = {}
    result5 = multilingual_ipfs_service.get_component_translations(component_id, lang)
    assert result5 is None


def test_localization_service_product_smoke(localization_service, ipfs_factory, blockchain_service):
    """
    P2: Smoke через фасад LocalizationService для продукта: t('product.{id}.title')
    """
    business_id = "prod-int-facade-001"
    entity_type = "product"
    field = "*"
    lang = "en"

    ipfs = ipfs_factory.get_service()
    payload = {"title": "Facade Product Title", "description": "Desc"}
    cid = ipfs.upload_json(payload)
    contract = blockchain_service.get_contract("AmanitaInternational")
    contract.functions.setSimpleFieldCID(entity_type, business_id, field, lang, cid).transact()

    value = localization_service.t(f"product.{business_id}.title")
    assert isinstance(value, str)
    assert value == "Facade Product Title"


def test_localization_service_component_smoke(localization_service, ipfs_factory, blockchain_service):
    """
    P2: Smoke через фасад LocalizationService для компонента: t('component.{id}.title')
    """
    component_id = "comp-int-facade-001"
    entity_type = "component"
    field = "*"
    lang = "en"

    ipfs = ipfs_factory.get_service()
    payload = {"title": "Facade Component Title", "description": "Comp Desc"}
    cid = ipfs.upload_json(payload)
    contract = blockchain_service.get_contract("AmanitaInternational")
    contract.functions.setSimpleFieldCID(entity_type, component_id, field, lang, cid).transact()

    value = localization_service.t(f"component.{component_id}.title")
    assert isinstance(value, str)
    assert value == "Facade Component Title"

