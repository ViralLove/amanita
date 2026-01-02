"""
Unit-тесты MultilingualIPFSService (Phase 2.1 @unit-test-build)

Задача 4.1.1.1 из temp-localization-testing-plan:
 - убедиться, что сервис тянет CID из AmanitaInternational и грузит JSON из IPFS
 - тест ПАДАЕТ, пока код не реализует доступ к блокчейну и сохранение в TranslationCacheService
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock
import tempfile
import os


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.common.multilingual_ipfs_service import MultilingualIPFSService  # noqa: E402
from services.common.translation_cache_service import TranslationCacheService  # noqa: E402


class TestMultilingualIPFSService(unittest.TestCase):
    """Первые падающие тесты для MultilingualIPFSService"""

    def setUp(self):
        # Backward-compatible test harness:
        # Many existing tests refer to self.ipfs_service.* for convenience.
        # The SSOT contract is still enforced: MultilingualIPFSService uses storage_service for I/O.
        self.ipfs_service = MagicMock(name="IPFSService")

        # SSOT injection for read/write path:
        # MultilingualIPFSService must use storage_service.download_json/upload_json (no ipfs_factory).
        self.storage_service = MagicMock(name="ProductStorageService")
        # Alias storage_service I/O to ipfs_service mocks so older assertions remain valid.
        self.storage_service.download_json = self.ipfs_service.download_json
        self.storage_service.upload_json = self.ipfs_service.upload_json

        self.cache_service = MagicMock(name="TranslationCacheService")
        self.fallback_service = MagicMock(name="FallbackLocalizationService")
        self.blockchain_service = MagicMock(name="BlockchainService")
        self.amanita_contract = MagicMock(name="AmanitaInternationalContract")

        # имитируем цепочку contract.functions.getSimpleFieldCID(...).call() -> CID
        self.blockchain_service.get_contract.return_value = self.amanita_contract
        # CID должен быть validate_ipfs_cid()-compatible после миграции на ProductStorageService
        self.valid_cid = "Qm" + ("1" * 44)
        self.amanita_contract.functions.getSimpleFieldCID.return_value.call.return_value = self.valid_cid

        self.service = MultilingualIPFSService(
            storage_service=self.storage_service,
            cache_service=self.cache_service,
            fallback_service=self.fallback_service,
            blockchain_service=self.blockchain_service
        )

    def test_fetches_json_by_cid_from_amanita_international(self):
        """Базовый end-to-end unit-тест (Phase 2.1 + 2.2)"""
        business_id = "prod-001"
        language = "en"
        expected_payload = {"title": {"en": "Lion's Mane"}}
        cache_key = f"product_{business_id}_{language}"
        # 5.1: внешнего кэша нет перед первым вызовом
        self.cache_service.get.return_value = None
        self.storage_service.download_json.return_value = expected_payload

        result = self.service.get_product_translations(business_id, language)

        # ожидаем CID через AmanitaInternational
        self.blockchain_service.get_contract.assert_called_once_with("AmanitaInternational")
        self.amanita_contract.functions.getSimpleFieldCID.assert_called_once()

        # ожидаем загрузку JSON по CID
        self.storage_service.download_json.assert_called_once_with(self.valid_cid)

        # 5.2: результат должен сохраниться в TranslationCacheService c правильными аргументами (динамический TTL)
        expected_ttl = self.service.cache_ttl['product']
        self.cache_service.set.assert_called_once_with(cache_key, expected_payload, 'ipfs', expected_ttl)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)  # 5.4: результат — dict
        self.assertEqual(result, expected_payload)

    def test_get_product_translations_uses_storage_service_download_json(self):
        """SSOT contract: get_product_translations() должен звать storage_service.download_json(cid)"""
        business_id = "prod-ssot-001"
        language = "en"
        expected_payload = {"title": {"en": "SSOT Title"}}

        # GIVEN: external cache miss + storage_service возвращает dict
        self.cache_service.get.return_value = None
        self.storage_service.download_json.return_value = expected_payload

        # WHEN
        result = self.service.get_product_translations(business_id, language)

        # THEN
        self.assertEqual(result, expected_payload)
        self.storage_service.download_json.assert_called_once()

    def test_upload_product_translations_uses_storage_service_upload_json(self):
        """SSOT contract: upload_product_translations() использует storage_service.upload_json"""
        business_id = "prod-up-001"
        translations = {
            "en": {"title": "T", "description": "D"},
            "ru": {"title": "Т", "description": "Д"},
        }
        expected_cid = "Qm" + ("9" * 44)

        # GIVEN
        self.storage_service.upload_json.return_value = expected_cid

        # WHEN
        cid = self.service.upload_product_translations(business_id, translations)

        # THEN
        self.assertEqual(cid, expected_cid)
        self.storage_service.upload_json.assert_called_once()
        uploaded = self.storage_service.upload_json.call_args[0][0]
        self.assertEqual(uploaded["business_id"], business_id)
        self.assertEqual(uploaded["type"], "product")
        self.assertEqual(uploaded["versions"], translations)

    def test_upload_component_translations_uses_storage_service_upload_json(self):
        """SSOT contract: upload_component_translations() использует storage_service.upload_json"""
        component_id = "comp-up-001"
        translations = {
            "en": {"name": "N", "description": "D"},
            "ru": {"name": "Н", "description": "Д"},
        }
        expected_cid = "Qm" + ("8" * 44)

        # GIVEN
        self.storage_service.upload_json.return_value = expected_cid

        # WHEN
        cid = self.service.upload_component_translations(component_id, translations)

        # THEN
        self.assertEqual(cid, expected_cid)
        self.storage_service.upload_json.assert_called_once()
        uploaded = self.storage_service.upload_json.call_args[0][0]
        self.assertEqual(uploaded["component_id"], component_id)
        self.assertEqual(uploaded["type"], "component")
        self.assertEqual(uploaded["versions"], translations)

    def test_upload_methods_return_none_when_storage_service_missing(self):
        """Fail-safe: если storage_service отсутствует — upload_* возвращают None и не падают"""
        service = MultilingualIPFSService(
            storage_service=None,
            cache_service=self.cache_service,
            fallback_service=self.fallback_service,
            blockchain_service=self.blockchain_service,
        )

        product_cid = service.upload_product_translations("prod-x", {"en": {"title": "T", "description": "D"}})
        self.assertIsNone(product_cid)
        component_cid = service.upload_component_translations("comp-x", {"en": {"name": "N", "description": "D"}})
        self.assertIsNone(component_cid)

    def test_upload_product_translations_exception_returns_none_and_increments_errors(self):
        """P0: storage_service.upload_json throws → returns None, no crash, stats['errors']++ (product)"""
        business_id = "prod-up-ex-001"
        translations = {"en": {"title": "T", "description": "D"}}

        # GIVEN
        before_errors = self.service.stats["errors"]
        self.storage_service.upload_json.side_effect = Exception("upload failed")

        # WHEN
        cid = self.service.upload_product_translations(business_id, translations)

        # THEN
        self.assertIsNone(cid)
        self.assertEqual(self.service.stats["errors"], before_errors + 1)

    def test_upload_component_translations_exception_returns_none_and_increments_errors(self):
        """P0: storage_service.upload_json throws → returns None, no crash, stats['errors']++ (component)"""
        component_id = "comp-up-ex-001"
        translations = {"en": {"name": "N", "description": "D"}}

        # GIVEN
        before_errors = self.service.stats["errors"]
        self.storage_service.upload_json.side_effect = Exception("upload failed")

        # WHEN
        cid = self.service.upload_component_translations(component_id, translations)

        # THEN
        self.assertIsNone(cid)
        self.assertEqual(self.service.stats["errors"], before_errors + 1)

    def test_caches_ipfs_payload_per_entity_language(self):
        """Проверка TTL/инвалидации (Phase 2.2 @unit-test-build)"""
        business_id = "prod-002"
        language = "en"
        payload_first = {"title": {"en": "Chaga"}}
        payload_second = {"title": {"en": "Chaga (fresh)"}}
        cache_key = f"product_{business_id}_{language}"
        # 5.1: внешнего кэша нет перед первым вызовом
        self.cache_service.get.return_value = None
        self.storage_service.download_json.return_value = payload_first
        self.service.cache_ttl["product"] = 1  # ускоряем TTL

        # 1 вызов — должен ходить в блокчейн+IPFS и сохранить в кэш
        first = self.service.get_product_translations(business_id, language)
        self.assertEqual(first, payload_first)
        self.assertEqual(self.storage_service.download_json.call_count, 1)

        # 2 вызов — смоделируем отсутствие локального кэша, но внешний вернёт данные → IPFS не дергается
        self.storage_service.download_json.reset_mock()
        # очищаем локальный кэш, чтобы проверить путь external cache
        if cache_key in self.service.ipfs_cache:
            del self.service.ipfs_cache[cache_key]
        self.cache_service.get.return_value = payload_first
        second = self.service.get_product_translations(business_id, language)
        self.assertEqual(second, payload_first)
        self.storage_service.download_json.assert_not_called()
        # локальный кэш восстановлен из external и имеет корректный TTL
        self.assertIn(cache_key, self.service.ipfs_cache)
        self.assertEqual(self.service.ipfs_cache[cache_key].ttl, self.service.cache_ttl['product'])

    def test_real_ipfs_cache_persists_across_service_instances(self):
        """Integration-lite: файловый ipfs.json сохраняет данные и доступен в новом инстансе"""
        business_id = "prod-006"
        language = "en"
        payload = {"title": {"en": "Shiitake"}}
        cache_key = f"product_{business_id}_{language}"
        with tempfile.TemporaryDirectory() as tmpdir:
            # Реальный TranslationCacheService с отдельной директорией
            real_cache = TranslationCacheService(cache_dir=os.path.join(tmpdir, "cache/translations"))
            # 1) Первый инстанс сервиса — загрузка из IPFS и запись в внешний кэш
            from services.product.storage import ProductStorageService
            ipfs_service_1 = MagicMock(name="IPFSService1")
            ipfs_service_1.download_json.return_value = payload
            storage_service_1 = ProductStorageService(storage_provider=ipfs_service_1)
            service1 = MultilingualIPFSService(
                storage_service=storage_service_1,
                cache_service=real_cache,
                fallback_service=self.fallback_service,
                blockchain_service=self.blockchain_service
            )
            # external miss → IPFS → запись
            result1 = service1.get_product_translations(business_id, language)
            self.assertEqual(result1, payload)
            self.assertTrue(ipfs_service_1.download_json.called)
            # 2) Новый инстанс сервиса — должен прочитать из внешнего кэша без IPFS
            ipfs_service_2 = MagicMock(name="IPFSService2")
            storage_service_2 = ProductStorageService(storage_provider=ipfs_service_2)
            service2 = MultilingualIPFSService(
                storage_service=storage_service_2,
                cache_service=real_cache,
                fallback_service=self.fallback_service,
                blockchain_service=self.blockchain_service
            )
            # Обнуляем локальный кэш на всякий случай
            self.assertEqual(len(service2.ipfs_cache), 0)
            result2 = service2.get_product_translations(business_id, language)
            self.assertEqual(result2, payload)
            ipfs_service_2.download_json.assert_not_called()

        # Проверка завершена: данные прочитаны из внешнего кэша без IPFS

    def test_fallback_used_when_ipfs_none_and_external_miss(self):
        """Fallback: external miss → IPFS None → fallback returns dict"""
        business_id = "prod-004"
        language = "en"
        fallback_payload = {"title": {"en": "Fallback Title"}}
        # external miss
        self.cache_service.get.return_value = None
        # IPFS returns None (no exception)
        self.ipfs_service.download_json.return_value = None
        # fallback returns dict
        self.fallback_service.get_translation_with_fallback.return_value = fallback_payload

        result = self.service.get_product_translations(business_id, language)

        # external checked
        self.cache_service.get.assert_called()
        # IPFS tried once
        self.ipfs_service.download_json.assert_called_once()
        # fallback used
        self.fallback_service.get_translation_with_fallback.assert_called_once()
        # result is fallback dict
        self.assertIsInstance(result, dict)
        self.assertEqual(result, fallback_payload)

    def test_product_returns_none_when_ipfs_fails_and_no_fallback(self):
        """NO_FALSE_SUCCESSES: IPFS fail + no fallback → None (не 'error_*')"""
        business_id = "prod-007"
        language = "en"
        self.cache_service.get.return_value = None  # external miss
        self.ipfs_service.download_json.return_value = None  # IPFS fail
        self.fallback_service.get_translation_with_fallback.return_value = None  # no fallback

        result = self.service.get_product_translations(business_id, language)

        self.cache_service.get.assert_called()
        self.ipfs_service.download_json.assert_called_once()
        self.fallback_service.get_translation_with_fallback.assert_called_once()
        self.assertIsNone(result)
        # не должно быть "успеха" в виде error_строки
        self.assertFalse(isinstance(result, str) and result.startswith("error_"))

    def test_component_returns_none_when_ipfs_fails_and_no_fallback(self):
        """NO_FALSE_SUCCESSES: IPFS fail + no fallback (component) → None (не 'error_*')"""
        component_id = "comp-007"
        language = "en"
        className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
        expected_cid = "Qm" + ("1" * 44)
        self.cache_service.get.return_value = None  # external miss
        self.ipfs_service.download_json.return_value = None  # IPFS fail
        self.fallback_service.get_translation_with_fallback.return_value = None  # no fallback
        # CID есть (валидный как строка), но payload не скачался → None
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn

        result = self.service.get_component_translations(component_id, language)

        self.cache_service.get.assert_called()
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        self.ipfs_service.download_json.assert_called_once_with(expected_cid)
        self.fallback_service.get_translation_with_fallback.assert_called_once()
        self.assertIsNone(result)
        self.assertFalse(isinstance(result, str) and result.startswith("error_"))

    def test_fallback_to_cache_when_ipfs_unreachable(self):
        """Сценарий: внешний кэш содержит данные → сразу возврат из external, без IPFS и fallback"""
        business_id = "prod-003"
        language = "ru"
        cached_payload = {"title": {"ru": "Чага"}}

        # внешний кэш возвращает данные
        self.cache_service.get.return_value = cached_payload

        result = self.service.get_product_translations(business_id, language)

        # при C-приоритете: external cache → немедленный возврат
        self.cache_service.get.assert_called_once()
        self.ipfs_service.download_json.assert_not_called()
        self.fallback_service.get_translation_with_fallback.assert_not_called()
        self.assertEqual(result, cached_payload)

    # ===== Components symmetry tests =====
    def test_component_fetches_json_by_cid_from_amanita(self):
        """Component: базовый путь контракт → IPFS → кэш (через complex fields)"""
        component_id = "comp-001"
        language = "en"
        className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
        expected_cid = "Qm" + ("2" * 44)
        expected_complex_data = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {
                "generic_description": "Reishi description",
                "effects": "Reishi effects"
            }
        }
        expected_fields = expected_complex_data["fields"]
        cache_key = f"component_{component_id}_{language}"
        
        # Настраиваем mocks для complex fields
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None
        self.ipfs_service.download_json.return_value = expected_complex_data

        result = self.service.get_component_translations(component_id, language)

        # контракт, IPFS вызваны (через complex fields)
        self.blockchain_service.get_contract.assert_called_with("AmanitaInternational")
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        self.ipfs_service.download_json.assert_called_once_with(expected_cid)
        # запись в кэш с TTL компонента (fields из complex data)
        self.cache_service.set.assert_called_with(cache_key, expected_fields, 'ipfs', self.service.cache_ttl['component'])
        self.assertIsInstance(result, dict)
        self.assertEqual(result, expected_fields)

    def test_component_caches_ipfs_payload_per_entity_language(self):
        """Component: TTL/инвалидация и повторная загрузка (через complex fields)"""
        component_id = "comp-002"
        language = "en"
        className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
        fields_first = {"generic_description": "Cordyceps description", "effects": "Cordyceps effects"}
        fields_second = {"generic_description": "Cordyceps (fresh) description", "effects": "Cordyceps (fresh) effects"}
        complex_data_first = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": fields_first
        }
        complex_data_second = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": fields_second
        }
        cache_key = f"component_{component_id}_{language}"
        
        # Настраиваем mocks для complex fields
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = "Qm" + ("3" * 44)
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None
        self.ipfs_service.download_json.return_value = complex_data_first
        self.service.cache_ttl["component"] = 1

        first = self.service.get_component_translations(component_id, language)
        self.assertEqual(first, fields_first)
        self.assertEqual(self.ipfs_service.download_json.call_count, 1)

        # external fast-path: очищаем локальный кэш и возвращаем из external
        self.ipfs_service.download_json.reset_mock()
        if cache_key in self.service.ipfs_cache:
            del self.service.ipfs_cache[cache_key]
        self.cache_service.get.return_value = fields_first
        second = self.service.get_component_translations(component_id, language)
        self.assertEqual(second, fields_first)
        self.ipfs_service.download_json.assert_not_called()

        # истечение TTL и повторная загрузка
        self.assertIn(cache_key, self.service.ipfs_cache)
        self.service.ipfs_cache[cache_key].timestamp = 0
        # Также очищаем кэш для complex field
        complex_cache_key = f"complex_{className}_{language}"
        if complex_cache_key in self.service.ipfs_cache:
            self.service.ipfs_cache[complex_cache_key].timestamp = 0
        self.cache_service.get.return_value = None  # Нет в external кэше
        self.ipfs_service.download_json.return_value = complex_data_second
        third = self.service.get_component_translations(component_id, language)
        self.assertEqual(third, fields_second)
        self.ipfs_service.download_json.assert_called_once()

    def test_component_external_cache_fast_path(self):
        """Component: external cache → немедленный возврат без IPFS (через complex fields)"""
        component_id = "comp-003"
        language = "ru"
        cached_fields = {"generic_description": "Рейши описание", "effects": "Рейши эффекты"}
        self.cache_service.get.return_value = cached_fields

        result = self.service.get_component_translations(component_id, language)

        self.cache_service.get.assert_called_once()
        self.ipfs_service.download_json.assert_not_called()
        self.assertEqual(result, cached_fields)
        # локальный кэш восстановлен
        cache_key = f"component_{component_id}_{language}"
        self.assertIn(cache_key, self.service.ipfs_cache)

    def test_component_fallback_used_when_ipfs_none_and_external_miss(self):
        """Component: external miss → IPFS None → fallback dict (через complex fields)"""
        component_id = "comp-004"
        language = "en"
        className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
        fallback_fields = {"generic_description": "Fallback Component description", "effects": "Fallback effects"}
        
        # Настраиваем mocks для complex fields: CID есть, но IPFS отдаёт None → fallback
        complex_field_fn = MagicMock()
        expected_cid = "Qm" + ("1" * 44)
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None
        # IPFS "недоступен"/не вернул payload
        self.ipfs_service.download_json.return_value = None
        self.fallback_service.get_translation_with_fallback.return_value = fallback_fields

        result = self.service.get_component_translations(component_id, language)

        self.cache_service.get.assert_called()
        # Проверяем, что был вызов getComplexFieldCID (через complex fields путь)
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        self.ipfs_service.download_json.assert_called_once_with(expected_cid)
        self.fallback_service.get_translation_with_fallback.assert_called_once()
        self.assertIsInstance(result, dict)
        self.assertEqual(result, fallback_fields)

    def test_product_local_expired_but_external_valid_uses_external_without_ipfs(self):
        """Product: истёкший локальный TTL при актуальном external → external-hit, без IPFS"""
        business_id = "prod-005"
        language = "en"
        payload_first = {"title": {"en": "Maitake"}}
        cache_key = f"product_{business_id}_{language}"
        # Ускоряем TTL для локального кэша
        self.service.cache_ttl["product"] = 1
        # Первая загрузка: external miss, IPFS отдаёт payload_first
        self.cache_service.get.return_value = None
        self.ipfs_service.download_json.return_value = payload_first
        first = self.service.get_product_translations(business_id, language)
        self.assertEqual(first, payload_first)
        # Истекаем локальный кэш
        self.assertIn(cache_key, self.service.ipfs_cache)
        self.service.ipfs_cache[cache_key].timestamp = 0
        # External теперь валиден и должен перехватить запрос
        self.cache_service.get.return_value = payload_first
        self.ipfs_service.download_json.reset_mock()
        second = self.service.get_product_translations(business_id, language)
        self.assertEqual(second, payload_first)
        # IPFS не должен вызываться — берём из external
        self.ipfs_service.download_json.assert_not_called()
        # Локальный кэш восстановлен
        self.assertIn(cache_key, self.service.ipfs_cache)
        self.assertEqual(self.service.ipfs_cache[cache_key].ttl, self.service.cache_ttl['product'])

    def test_get_stats_returns_all_metrics(self):
        """Тест: get_stats() возвращает все необходимые метрики"""
        # GIVEN: Сервис с выполненными операциями
        self.service.stats['ipfs_requests'] = 10
        self.service.stats['ipfs_hits'] = 7
        self.service.stats['ipfs_misses'] = 3
        self.service.stats['cache_hits'] = 5
        self.service.stats['fallback_hits'] = 2
        self.service.stats['errors'] = 1
        self.service.ipfs_cache['test_key'] = MagicMock()
        self.service.supported_languages = {'en', 'ru'}
        
        # WHEN: Получаем статистику
        stats = self.service.get_stats()
        
        # THEN: Все основные метрики присутствуют
        self.assertIn('ipfs_requests', stats)
        self.assertIn('ipfs_hits', stats)
        self.assertIn('ipfs_misses', stats)
        self.assertIn('cache_hits', stats)
        self.assertIn('fallback_hits', stats)
        self.assertIn('errors', stats)
        
        # THEN: Все производные метрики присутствуют
        self.assertIn('hit_rate_percent', stats)
        self.assertIn('cache_hit_rate_percent', stats)
        self.assertIn('fallback_rate_percent', stats)
        self.assertIn('error_rate_percent', stats)
        
        # THEN: Дополнительные метрики присутствуют
        self.assertIn('cached_entries', stats)
        self.assertIn('supported_languages', stats)
        
        # THEN: Всего 12 метрик (6 основных + 4 производных + 2 дополнительных)
        self.assertEqual(len(stats), 12)

    def test_get_stats_computes_derived_metrics(self):
        """Тест: get_stats() корректно вычисляет производные метрики"""
        # GIVEN: Сервис с известными значениями
        self.service.stats['ipfs_requests'] = 100
        self.service.stats['ipfs_hits'] = 60
        self.service.stats['ipfs_misses'] = 40
        self.service.stats['cache_hits'] = 30
        self.service.stats['fallback_hits'] = 10
        self.service.stats['errors'] = 5
        
        # WHEN: Получаем статистику
        stats = self.service.get_stats()
        
        # THEN: Производные метрики вычислены корректно
        self.assertEqual(stats['hit_rate_percent'], 60.0)  # 60/100 * 100
        self.assertEqual(stats['cache_hit_rate_percent'], 30.0)  # 30/100 * 100
        self.assertEqual(stats['fallback_rate_percent'], 10.0)  # 10/100 * 100
        self.assertEqual(stats['error_rate_percent'], 5.0)  # 5/100 * 100
        
        # THEN: Производные метрики являются float и округлены до 2 знаков
        self.assertIsInstance(stats['hit_rate_percent'], float)
        # Проверяем что значение корректно округлено (может быть целым, например 60.0)
        self.assertGreaterEqual(stats['hit_rate_percent'], 0.0)
        self.assertLessEqual(stats['hit_rate_percent'], 100.0)

    def test_get_stats_rounds_derived_metrics_correctly(self):
        """Тест: get_stats() корректно округляет производные метрики до 2 знаков"""
        # GIVEN: Сервис с дробными значениями, которые требуют округления
        # Случай, который даст дробное значение: 1/3 = 0.333... * 100 = 33.333...
        self.service.stats['ipfs_requests'] = 3
        self.service.stats['ipfs_hits'] = 1  # 1/3 * 100 = 33.333... → должно быть 33.33
        self.service.stats['ipfs_misses'] = 2
        self.service.stats['cache_hits'] = 0
        self.service.stats['fallback_hits'] = 0
        self.service.stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats = self.service.get_stats()
        
        # THEN: Производные метрики округлены до 2 знаков после запятой
        # 1/3 * 100 = 33.333... → должно быть округлено до 33.33
        expected_hit_rate = round((1 / 3) * 100, 2)  # 33.33
        self.assertEqual(stats['hit_rate_percent'], expected_hit_rate)
        self.assertEqual(stats['hit_rate_percent'], 33.33)
        
        # GIVEN: Случай с другим дробным значением: 2/7 = 0.2857... * 100 = 28.571...
        self.service.stats['ipfs_requests'] = 7
        self.service.stats['ipfs_hits'] = 2  # 2/7 * 100 = 28.571... → должно быть 28.57
        self.service.stats['cache_hits'] = 1  # 1/7 * 100 = 14.285... → должно быть 14.29
        
        # WHEN: Получаем статистику
        stats_fractional = self.service.get_stats()
        
        # THEN: Производные метрики округлены до 2 знаков
        # 2/7 * 100 = 28.571... → должно быть округлено до 28.57
        expected_hit_rate_fractional = round((2 / 7) * 100, 2)  # 28.57
        self.assertEqual(stats_fractional['hit_rate_percent'], expected_hit_rate_fractional)
        self.assertEqual(stats_fractional['hit_rate_percent'], 28.57)
        
        # 1/7 * 100 = 14.285... → должно быть округлено до 14.29
        expected_cache_rate = round((1 / 7) * 100, 2)  # 14.29
        self.assertEqual(stats_fractional['cache_hit_rate_percent'], expected_cache_rate)
        self.assertEqual(stats_fractional['cache_hit_rate_percent'], 14.29)
        
        # THEN: Проверяем, что округление действительно до 2 знаков
        # Преобразуем в строку и проверяем количество знаков после запятой
        hit_rate_str = str(stats_fractional['hit_rate_percent'])
        if '.' in hit_rate_str:
            decimal_places = len(hit_rate_str.split('.')[-1])
            self.assertLessEqual(decimal_places, 2, 
                                f"Округление должно быть до 2 знаков, получено {decimal_places}")

    def test_get_stats_handles_zero_requests(self):
        """Тест: get_stats() корректно обрабатывает случай нулевых запросов"""
        # GIVEN: Сервис без запросов
        self.service.stats['ipfs_requests'] = 0
        self.service.stats['ipfs_hits'] = 0
        self.service.stats['ipfs_misses'] = 0
        self.service.stats['cache_hits'] = 0
        self.service.stats['fallback_hits'] = 0
        self.service.stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats = self.service.get_stats()
        
        # THEN: Все производные метрики равны 0.0 (без деления на ноль)
        self.assertEqual(stats['hit_rate_percent'], 0.0)
        self.assertEqual(stats['cache_hit_rate_percent'], 0.0)
        self.assertEqual(stats['fallback_rate_percent'], 0.0)
        self.assertEqual(stats['error_rate_percent'], 0.0)
        
        # THEN: Основные метрики равны 0
        self.assertEqual(stats['ipfs_requests'], 0)
        self.assertEqual(stats['ipfs_hits'], 0)

    def test_get_stats_boundary_cases_for_derived_metrics(self):
        """Тест: get_stats() корректно обрабатывает граничные случаи производных метрик"""
        # GIVEN: Граничный случай 1 - 100% hit rate (все запросы успешны)
        self.service.stats['ipfs_requests'] = 50
        self.service.stats['ipfs_hits'] = 50  # 100% успешных запросов
        self.service.stats['ipfs_misses'] = 0
        self.service.stats['cache_hits'] = 25
        self.service.stats['fallback_hits'] = 0
        self.service.stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats_100_percent = self.service.get_stats()
        
        # THEN: Производные метрики корректны для 100% hit rate
        self.assertEqual(stats_100_percent['hit_rate_percent'], 100.0)  # 50/50 * 100
        self.assertEqual(stats_100_percent['cache_hit_rate_percent'], 50.0)  # 25/50 * 100
        self.assertEqual(stats_100_percent['fallback_rate_percent'], 0.0)  # 0/50 * 100
        self.assertEqual(stats_100_percent['error_rate_percent'], 0.0)  # 0/50 * 100
        
        # GIVEN: Граничный случай 2 - 0% hit rate при не нулевых запросах (все запросы промахнулись)
        self.service.stats['ipfs_requests'] = 30
        self.service.stats['ipfs_hits'] = 0  # 0% успешных запросов
        self.service.stats['ipfs_misses'] = 30
        self.service.stats['cache_hits'] = 0
        self.service.stats['fallback_hits'] = 30  # Все запросы пошли в fallback
        self.service.stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats_0_percent = self.service.get_stats()
        
        # THEN: Производные метрики корректны для 0% hit rate
        self.assertEqual(stats_0_percent['hit_rate_percent'], 0.0)  # 0/30 * 100
        self.assertEqual(stats_0_percent['cache_hit_rate_percent'], 0.0)  # 0/30 * 100
        self.assertEqual(stats_0_percent['fallback_rate_percent'], 100.0)  # 30/30 * 100
        self.assertEqual(stats_0_percent['error_rate_percent'], 0.0)  # 0/30 * 100
        
        # GIVEN: Граничный случай 3 - 100% error rate (все запросы с ошибками)
        self.service.stats['ipfs_requests'] = 20
        self.service.stats['ipfs_hits'] = 0
        self.service.stats['ipfs_misses'] = 0
        self.service.stats['cache_hits'] = 0
        self.service.stats['fallback_hits'] = 0
        self.service.stats['errors'] = 20  # 100% ошибок
        
        # WHEN: Получаем статистику
        stats_100_error = self.service.get_stats()
        
        # THEN: Производные метрики корректны для 100% error rate
        self.assertEqual(stats_100_error['hit_rate_percent'], 0.0)  # 0/20 * 100
        self.assertEqual(stats_100_error['cache_hit_rate_percent'], 0.0)  # 0/20 * 100
        self.assertEqual(stats_100_error['fallback_rate_percent'], 0.0)  # 0/20 * 100
        self.assertEqual(stats_100_error['error_rate_percent'], 100.0)  # 20/20 * 100

    def test_get_stats_integrates_with_cache_manager(self):
        """Тест: get_stats() совместим с CacheManager (hasattr проверка)"""
        # GIVEN: Сервис с методом get_stats
        # WHEN: Проверяем наличие метода get_stats через hasattr
        has_get_stats = hasattr(self.service, 'get_stats')
        
        # THEN: Метод существует
        self.assertTrue(has_get_stats)
        
        # THEN: Метод можно вызвать и он возвращает словарь (совместимый с CacheManager)
        # CacheManager проверяет hasattr и вызывает get_stats(), ожидая dict
        stats = self.service.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertGreaterEqual(len(stats), 1)  # Хотя бы одна метрика

    def test_get_complex_field_cid(self):
        """Тест: получение CID для complex field через блокчейн контракт"""
        # GIVEN: Настроенный сервис с blockchain_service
        className = "ComponentDescription"
        language = "ru"
        expected_cid = "Qm" + ("4" * 44)
        
        # Настраиваем mock для getComplexFieldCID
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        
        # WHEN: Получаем CID для complex field
        result = self.service._get_complex_field_cid(className, language)
        
        # THEN: Метод вызывал правильный контракт метод
        self.blockchain_service.get_contract.assert_called_with("AmanitaInternational")
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        complex_field_fn.call.assert_called_once()
        
        # THEN: Возвращен правильный CID
        self.assertEqual(result, expected_cid)

    def test_get_complex_field_cid_returns_none_when_empty(self):
        """Тест: _get_complex_field_cid возвращает None при пустом CID"""
        # GIVEN: Контракт возвращает пустую строку
        className = "ComponentDescription"
        language = "ru"
        
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = ""
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        
        # WHEN: Получаем CID
        result = self.service._get_complex_field_cid(className, language)
        
        # THEN: Возвращается None
        self.assertIsNone(result)

    def test_get_complex_field_cid_handles_contract_error(self):
        """Тест: _get_complex_field_cid обрабатывает ошибки контракта"""
        # GIVEN: Контракт выбрасывает исключение
        className = "ComponentDescription"
        language = "ru"
        
        complex_field_fn = MagicMock()
        complex_field_fn.call.side_effect = Exception("Contract error")
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        
        # WHEN: Получаем CID
        result = self.service._get_complex_field_cid(className, language)
        
        # THEN: Возвращается None (ошибка обработана)
        self.assertIsNone(result)

    def test_load_complex_field_from_ipfs(self):
        """Тест: загрузка complex field из IPFS через блокчейн маппинг"""
        # GIVEN: Настроенный сервис
        className = "ComponentDescription"
        language = "ru"
        expected_cid = "Qm" + ("5" * 44)
        expected_payload = {
            "label": "ComponentDescription",
            "type": "complex_fields",
            "language": "ru",
            "fields": {
                "generic_description": "Описание компонента",
                "effects": "Эффекты",
                "shamanic": "Шаманское использование",
                "warnings": "Предупреждения"
            }
        }
        cache_key = f"complex_{className}_{language}"
        
        # Настраиваем mocks
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None  # Нет в кэше
        self.ipfs_service.download_json.return_value = expected_payload
        
        # WHEN: Загружаем complex field
        result = self.service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Метод вызывал правильный контракт метод
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        
        # THEN: Загрузил JSON из IPFS
        self.ipfs_service.download_json.assert_called_once_with(expected_cid)
        
        # THEN: Сохранил в кэш
        expected_ttl = self.service.cache_ttl['component']
        self.cache_service.set.assert_called_once_with(cache_key, expected_payload, 'ipfs', expected_ttl)
        
        # THEN: Возвращен правильный payload
        self.assertEqual(result, expected_payload)

    def test_load_complex_field_from_ipfs_validates_structure(self):
        """Тест: _load_complex_field_from_ipfs валидирует структуру JSON"""
        # GIVEN: Неправильная структура JSON (без полей label, type, fields)
        className = "ComponentDescription"
        language = "ru"
        invalid_payload = {"some_field": "value"}
        
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = "Qm" + ("6" * 44)
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None
        self.ipfs_service.download_json.return_value = invalid_payload
        
        # WHEN: Загружаем complex field
        result = self.service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Возвращается None (валидация не прошла)
        self.assertIsNone(result)

    def test_load_complex_field_from_ipfs_uses_cache(self):
        """Тест: _load_complex_field_from_ipfs использует кэш"""
        # GIVEN: Данные уже в кэше
        className = "ComponentDescription"
        language = "ru"
        cached_payload = {
            "label": "ComponentDescription",
            "type": "complex_fields",
            "language": "ru",
            "fields": {"generic_description": "Cached"}
        }
        cache_key = f"complex_{className}_{language}"
        
        self.cache_service.get.return_value = cached_payload
        
        # WHEN: Загружаем complex field
        result = self.service._load_complex_field_from_ipfs(className, language)
        
        # THEN: Возвращены данные из кэша
        self.assertEqual(result, cached_payload)
        
        # THEN: IPFS не вызывался
        self.ipfs_service.download_json.assert_not_called()
        
        # THEN: Блокчейн не вызывался
        self.amanita_contract.functions.getComplexFieldCID.assert_not_called()

    def test_get_component_description_template(self):
        """Тест: получение глобального шаблона ComponentDescription через блокчейн (complex field)"""
        # GIVEN: Настроенный сервис с complex field данными (глобальный шаблон)
        language = "ru"
        complex_data = {
            "label": "ComponentDescription",
            "type": "complex_fields",
            "language": "ru",
            "fields": {
                "generic_description": "Глобальный шаблон описания",
                "effects": "Глобальный шаблон эффектов",
                "shamanic": "Глобальный шаблон шаманского использования",
                "warnings": "Глобальный шаблон предупреждений"
            }
        }
        expected_fields = complex_data["fields"]
        
        # Mock _load_complex_field_from_ipfs
        self.service._load_complex_field_from_ipfs = MagicMock(return_value=complex_data)
        
        # WHEN: Получаем ComponentDescription шаблон
        result = self.service.get_component_description_template(language)
        
        # THEN: Вызван _load_complex_field_from_ipfs с правильными параметрами
        self.service._load_complex_field_from_ipfs.assert_called_once_with("ComponentDescription", language)
        
        # THEN: Возвращены только fields из глобального шаблона
        self.assertEqual(result, expected_fields)

    def test_get_component_description_template_returns_none_when_no_data(self):
        """Тест: get_component_description_template возвращает None при отсутствии данных"""
        # GIVEN: _load_complex_field_from_ipfs возвращает None
        language = "ru"
        self.service._load_complex_field_from_ipfs = MagicMock(return_value=None)
        
        # WHEN: Получаем ComponentDescription шаблон
        result = self.service.get_component_description_template(language)
        
        # THEN: Возвращается None
        self.assertIsNone(result)

    def test_get_component_description_template_returns_none_when_fields_missing(self):
        """Тест: get_component_description_template возвращает None при отсутствии fields"""
        # GIVEN: complex_data без поля fields
        language = "ru"
        complex_data = {
            "label": "ComponentDescription",
            "type": "complex_fields",
            "language": "ru"
        }
        
        self.service._load_complex_field_from_ipfs = MagicMock(return_value=complex_data)
        
        # WHEN: Получаем ComponentDescription шаблон
        result = self.service.get_component_description_template(language)
        
        # THEN: Возвращается None
        self.assertIsNone(result)

    # ===== Per-component complex fields tests (with biounit_id) =====
    
    def test_load_component_description_from_ipfs_success(self):
        """Тест: успешная загрузка per-component описания через complex fields с biounit_id"""
        # GIVEN: Настроенный сервис для per-component данных
        component_id = "amanita_muscaria"
        language = "ru"
        className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
        expected_cid = "Qm" + ("7" * 44)
        expected_complex_data = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {
                "generic_description": "Описание компонента amanita_muscaria",
                "effects": "Эффекты",
                "shamanic": "Шаманское использование",
                "warnings": "Предупреждения"
            }
        }
        expected_fields = expected_complex_data["fields"]
        
        # Настраиваем mocks для _load_complex_field_from_ipfs
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None  # Нет в кэше
        self.ipfs_service.download_json.return_value = expected_complex_data
        
        # WHEN: Загружаем per-component описание
        result = self.service._load_component_description_from_ipfs(component_id, language)
        
        # THEN: Метод вызывал _load_complex_field_from_ipfs с правильным className (с biounit_id)
        # Проверяем, что был вызов через внутренний метод _load_complex_field_from_ipfs
        # с className = "ComponentDescription.amanita_muscaria"
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        
        # THEN: Загрузил JSON из IPFS
        self.ipfs_service.download_json.assert_called_once_with(expected_cid)
        
        # THEN: Возвращены только fields из complex data
        self.assertEqual(result, expected_fields)
        self.assertIn("generic_description", result)
        self.assertEqual(result["generic_description"], "Описание компонента amanita_muscaria")

    def test_load_component_description_from_ipfs_uses_cache(self):
        """Тест: _load_component_description_from_ipfs использует кэш"""
        # GIVEN: Данные уже в кэше
        component_id = "amanita_muscaria"
        language = "ru"
        className = f"ComponentDescription.{component_id}"
        cache_key = f"complex_{className}_{language}"
        cached_complex_data = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {"generic_description": "Cached description"}
        }
        cached_fields = cached_complex_data["fields"]
        
        self.cache_service.get.return_value = cached_complex_data
        
        # WHEN: Загружаем per-component описание
        result = self.service._load_component_description_from_ipfs(component_id, language)
        
        # THEN: Возвращены fields из кэша
        self.assertEqual(result, cached_fields)
        
        # THEN: IPFS не вызывался
        self.ipfs_service.download_json.assert_not_called()
        
        # THEN: Блокчейн не вызывался
        self.amanita_contract.functions.getComplexFieldCID.assert_not_called()

    def test_load_component_description_from_ipfs_validates_structure(self):
        """Тест: _load_component_description_from_ipfs валидирует структуру JSON"""
        # GIVEN: Неправильная структура JSON (без поля fields)
        component_id = "amanita_muscaria"
        language = "ru"
        className = f"ComponentDescription.{component_id}"
        invalid_complex_data = {
            "label": "ComponentDescription",
            "type": "complex"
            # Отсутствует поле "fields"
        }
        
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = "Qm" + ("8" * 44)
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None
        self.ipfs_service.download_json.return_value = invalid_complex_data
        
        # WHEN: Загружаем per-component описание
        result = self.service._load_component_description_from_ipfs(component_id, language)
        
        # THEN: Возвращается None (валидация не прошла)
        self.assertIsNone(result)

    def test_load_component_description_from_ipfs_returns_none_when_no_data(self):
        """Тест: _load_component_description_from_ipfs возвращает None при отсутствии данных"""
        # GIVEN: _load_complex_field_from_ipfs возвращает None
        component_id = "amanita_muscaria"
        language = "ru"
        
        # Mock _load_complex_field_from_ipfs для возврата None
        self.service._load_complex_field_from_ipfs = MagicMock(return_value=None)
        
        # WHEN: Загружаем per-component описание
        result = self.service._load_component_description_from_ipfs(component_id, language)
        
        # THEN: Возвращается None
        self.assertIsNone(result)

    def test_get_component_translations_uses_complex_fields(self):
        """Тест: get_component_translations() использует complex fields через _load_component_description_from_ipfs"""
        # GIVEN: Настроенный сервис для per-component данных
        component_id = "amanita_muscaria"
        language = "ru"
        className = f"ComponentDescription.{component_id}"  # ✅ С biounit_id
        expected_cid = "Qm" + ("9" * 44)
        expected_fields = {
            "generic_description": "Test description",
            "effects": "Test effects",
            "shamanic": "Test shamanic",
            "warnings": "Test warnings"
        }
        expected_complex_data = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": expected_fields
        }
        cache_key = f"component_{component_id}_{language}"
        
        # Настраиваем mocks
        complex_field_fn = MagicMock()
        complex_field_fn.call.return_value = expected_cid
        self.amanita_contract.functions.getComplexFieldCID.return_value = complex_field_fn
        self.cache_service.get.return_value = None  # Нет в кэше
        self.ipfs_service.download_json.return_value = expected_complex_data
        
        # WHEN: Получаем переводы компонента
        result = self.service.get_component_translations(component_id, language)
        
        # THEN: Метод использовал complex fields (через _load_component_description_from_ipfs)
        # Проверяем, что был вызов getComplexFieldCID с правильным className (с biounit_id)
        self.amanita_contract.functions.getComplexFieldCID.assert_called_once_with(className, language)
        
        # THEN: Загрузил JSON из IPFS
        self.ipfs_service.download_json.assert_called_once_with(expected_cid)
        
        # THEN: Сохранил в кэш (вызывается дважды: для complex data и для fields)
        expected_ttl = self.service.cache_ttl['component']
        # Проверяем последний вызов (для fields)
        self.assertGreaterEqual(self.cache_service.set.call_count, 1)
        # Проверяем, что был вызов с fields
        calls = self.cache_service.set.call_args_list
        fields_call_found = any(
            call[0][0] == cache_key and call[0][1] == expected_fields 
            for call in calls
        )
        self.assertTrue(fields_call_found, f"Expected call with cache_key={cache_key} and fields, got calls: {calls}")
        
        # THEN: Возвращены fields из complex data
        self.assertEqual(result, expected_fields)
        self.assertIn("generic_description", result)
        self.assertEqual(result["generic_description"], "Test description")

    def test_get_component_translations_uses_cache_for_complex_fields(self):
        """Тест: get_component_translations() использует кэш для complex fields"""
        # GIVEN: Данные уже в кэше
        component_id = "amanita_muscaria"
        language = "ru"
        cache_key = f"component_{component_id}_{language}"
        cached_fields = {
            "generic_description": "Cached description",
            "effects": "Cached effects"
        }
        
        self.cache_service.get.return_value = cached_fields
        
        # WHEN: Получаем переводы компонента
        result = self.service.get_component_translations(component_id, language)
        
        # THEN: Возвращены данные из кэша
        self.assertEqual(result, cached_fields)
        
        # THEN: IPFS не вызывался
        self.ipfs_service.download_json.assert_not_called()
        
        # THEN: Блокчейн не вызывался
        self.amanita_contract.functions.getComplexFieldCID.assert_not_called()


if __name__ == "__main__":
    unittest.main()

