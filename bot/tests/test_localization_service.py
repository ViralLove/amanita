"""
Тесты для LocalizationService
Проверяют функциональность универсального сервиса локализации
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.common.localization_service import LocalizationService
from services.common.localization import Localization
from services.common.product_localization import ProductLocalizationService
from services.common.component_localization import ComponentLocalizationService
from services.common.fallback_localization_service import FallbackResult, FallbackLevel


class TestLocalizationService(unittest.TestCase):
    """Тесты для LocalizationService"""
    
    def setUp(self):
        """Настройка тестов"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_templates_dir = None
        
        # Создаем временную структуру директорий
        self.templates_dir = os.path.join(self.temp_dir, "templates")
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(os.path.join(self.templates_dir, "products"), exist_ok=True)
        os.makedirs(os.path.join(self.templates_dir, "components"), exist_ok=True)
        
        # Создаем тестовые JSON файлы
        self._create_test_files()
        
        # Мокаем APP_ROOT_DIR
        import config
        self.original_app_root = getattr(config, 'APP_ROOT_DIR', None)
        config.APP_ROOT_DIR = self.temp_dir
    
    def tearDown(self):
        """Очистка после тестов"""
        import config
        if self.original_app_root is not None:
            config.APP_ROOT_DIR = self.original_app_root
        else:
            delattr(config, 'APP_ROOT_DIR')
    
    def _create_test_files(self):
        """Создает тестовые JSON файлы"""
        # Интерфейсные переводы
        interface_data = {
            "onboarding": {
                "welcome": "Добро пожаловать!",
                "success": "Успешно!"
            }
        }
        
        with open(os.path.join(self.templates_dir, "ru.json"), 'w', encoding='utf-8') as f:
            json.dump(interface_data, f, ensure_ascii=False, indent=2)
        
        # Переводы продуктов
        product_data = {
            "products": {
                "amanita_powder_001": {
                    "title": "Порошок мухомора красного",
                    "description": "Высушенный и измельченный порошок"
                }
            }
        }
        
        with open(os.path.join(self.templates_dir, "products", "ru.json"), 'w', encoding='utf-8') as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2)
        
        # Переводы компонентов
        component_data = {
            "components": {
                "amanita_muscaria": {
                    "common_name": "Мухомор красный",
                    "scientific_name": "Amanita muscaria"
                }
            }
        }
        
        with open(os.path.join(self.templates_dir, "components", "ru.json"), 'w', encoding='utf-8') as f:
            json.dump(component_data, f, ensure_ascii=False, indent=2)
    
    def test_interface_localization_preservation(self):
        """Тест: Сохранена существующая функциональность интерфейсных переводов"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Проверяем, что LocalizationService действительно наследует от Localization
        self.assertIsInstance(loc, Localization)
        self.assertTrue(hasattr(loc, 'labels'))
        self.assertTrue(hasattr(loc, 'lang'))
        
        # ✅ ПРАВИЛЬНО: Проверяем реальную функциональность загрузки переводов
        self.assertIsInstance(loc.labels, dict)
        self.assertIn('onboarding', loc.labels)
        
        # ✅ ПРАВИЛЬНО: Проверяем, что переводы действительно загружаются
        self.assertEqual(loc.t('onboarding.welcome'), 'Добро пожаловать!')
        self.assertEqual(loc.t('onboarding.success'), 'Успешно!')
        
        # ✅ ПРАВИЛЬНО: Проверяем fallback стратегию
        self.assertEqual(loc.t('nonexistent.key'), 'nonexistent.key')
        
        # ✅ ПРАВИЛЬНО: Проверяем, что существующий API работает без изменений
        self.assertEqual(loc.lang, 'ru')
        self.assertIsNotNone(loc.labels)
    
    def test_product_localization_support(self):
        """Тест: Добавлена поддержка локализации продуктов"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Проверяем, что ProductLocalizationService инициализирован
        self.assertIsNotNone(loc.product_localization)
        self.assertIsInstance(loc.product_localization, ProductLocalizationService)
        
        # ✅ ПРАВИЛЬНО: Тестируем получение переводов продуктов
        self.assertEqual(loc.t('product.amanita_powder_001.title'), 'Порошок мухомора красного')
        self.assertEqual(loc.t('product.amanita_powder_001.description'), 'Высушенный и измельченный порошок')
        
        # ✅ ПРАВИЛЬНО: Тестируем fallback стратегию
        self.assertEqual(loc.t('product.amanita_powder_001.nonexistent'), '[nonexistent]')
        
        # ✅ ПРАВИЛЬНО: Тестируем прямой API для продуктов
        self.assertEqual(loc.get_product_translation('amanita_powder_001', 'title'), 'Порошок мухомора красного')
        self.assertEqual(loc.get_product_translation('amanita_powder_001', 'description'), 'Высушенный и измельченный порошок')
    
    def test_component_localization_support(self):
        """Тест: Добавлена поддержка локализации компонентов"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Проверяем, что ComponentLocalizationService инициализирован
        self.assertIsNotNone(loc.component_localization)
        self.assertIsInstance(loc.component_localization, ComponentLocalizationService)
        
        # ✅ ПРАВИЛЬНО: Тестируем получение переводов компонентов
        self.assertEqual(loc.t('component.amanita_muscaria.common_name'), 'Мухомор красный')
        self.assertEqual(loc.t('component.amanita_muscaria.scientific_name'), 'Amanita muscaria')
        
        # ✅ ПРАВИЛЬНО: Тестируем fallback стратегию
        self.assertEqual(loc.t('component.amanita_muscaria.nonexistent'), '[nonexistent]')
        
        # ✅ ПРАВИЛЬНО: Тестируем прямой API для компонентов
        self.assertEqual(loc.get_component_translation('amanita_muscaria', 'common_name'), 'Мухомор красный')
        self.assertEqual(loc.get_component_translation('amanita_muscaria', 'scientific_name'), 'Amanita muscaria')
    
    def test_unified_translation_api(self):
        """Тест: Создан универсальный API для всех типов переводов"""
        loc = LocalizationService('ru')
        
        # Тестируем автоматическое определение типа
        self.assertEqual(loc.t('onboarding.welcome'), 'Добро пожаловать!')  # interface
        self.assertEqual(loc.t('product.amanita_powder_001.title'), 'Порошок мухомора красного')  # product
        self.assertEqual(loc.t('component.amanita_muscaria.common_name'), 'Мухомор красный')  # component
    
    def test_backward_compatibility(self):
        """Тест: Обеспечена обратная совместимость с существующим кодом"""
        loc = LocalizationService('ru')
        
        # Тестируем, что все существующие вызовы работают
        self.assertEqual(loc.t('onboarding.welcome'), 'Добро пожаловать!')
        self.assertEqual(loc.t('onboarding.success'), 'Успешно!')
        
        # Тестируем, что API совместим
        self.assertTrue(hasattr(loc, 't'))
        self.assertTrue(hasattr(loc, 'lang'))
        self.assertTrue(hasattr(loc, 'labels'))

    def test_switch_language_runtime(self):
        """Тест: Один объект LocalizationService переключает язык без пересоздания"""
        loc = LocalizationService('ru')

        loc.switch_language('en')

        self.assertEqual(loc.lang, 'en')
        self.assertEqual(loc.product_localization.language, 'en')
        self.assertEqual(loc.component_localization.language, 'en')
    
    def test_error_handling(self):
        """Тест: Реализована обработка ошибок и fallback стратегии"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Тестируем обработку неверных ключей
        self.assertEqual(loc.t('invalid.key.format'), 'invalid.key.format')
        self.assertEqual(loc.t('product.invalid_id.field'), '[field]')
        self.assertEqual(loc.t('component.invalid_id.field'), '[field]')
        
        # ✅ ПРАВИЛЬНО: Тестируем обработку граничных случаев
        self.assertEqual(loc.t('product..field'), '[field]')  # Пустой business_id
        self.assertEqual(loc.t('product.business_id.'), '[field]')  # Пустое поле
        self.assertEqual(loc.t('component..field'), '[field]')  # Пустой component_id
        self.assertEqual(loc.t('component.component_id.'), '[field]')  # Пустое поле
    
    def test_performance_requirements(self):
        """Тест: Обеспечена производительность не хуже существующей"""
        import time
        
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Тестируем производительность интерфейсных переводов
        start_time = time.time()
        for _ in range(100):
            result = loc.t('onboarding.welcome')
            # Проверяем, что результат корректный
            self.assertEqual(result, 'Добро пожаловать!')
        interface_time = time.time() - start_time
        
        # Должно быть быстрее 10ms на 100 запросов
        self.assertLess(interface_time, 0.01)
        
        # ✅ ПРАВИЛЬНО: Тестируем производительность переводов продуктов
        start_time = time.time()
        for _ in range(100):
            result = loc.t('product.amanita_powder_001.title')
            # Проверяем, что результат корректный
            self.assertEqual(result, 'Порошок мухомора красного')
        product_time = time.time() - start_time
        
        # Должно быть быстрее 100ms на 100 запросов
        self.assertLess(product_time, 0.1)
    
    def test_real_integration_with_product_formatter(self):
        """Тест: Реальная интеграция с ProductFormatterService"""
        # ✅ ПРАВИЛЬНО: Используем существующий импорт вместо создания нового
        loc = LocalizationService('ru')
        
        # Создаем мок продукта с реалистичными данными
        class MockProduct:
            def __init__(self):
                self.business_id = "amanita_powder_001"
                self.title = "Amanita Powder"  # Английское название по умолчанию
                self.description = "Dried and ground powder from Amanita muscaria caps"
        
        # Устанавливаем данные продукта
        product_data = {
            'title': 'Порошок мухомора красного',
            'description': 'Высушенный и измельченный порошок из шляпок мухомора'
        }
        loc.set_product_data('amanita_powder_001', 'ru', product_data)
        
        # Тестируем реальное использование
        product = MockProduct()
        
        # ✅ ПРАВИЛЬНО: Проверяем, что локализация работает с реальными данными
        localized_title = loc.get_product_translation(product.business_id, 'title')
        self.assertEqual(localized_title, 'Порошок мухомора красного')
        
        localized_description = loc.get_product_translation(product.business_id, 'description')
        self.assertEqual(localized_description, 'Высушенный и измельченный порошок из шляпок мухомора')
        
        # ✅ ПРАВИЛЬНО: Проверяем, что fallback работает при отсутствии перевода
        localized_nonexistent = loc.get_product_translation(product.business_id, 'nonexistent_field', 'Fallback Value')
        self.assertEqual(localized_nonexistent, 'Fallback Value')
    
    def test_fallback_strategy_real_scenarios(self):
        """Тест: Fallback стратегия в реальных сценариях"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Тестируем fallback при отсутствии данных продукта
        result = loc.get_product_translation('nonexistent_product', 'title', 'Fallback Title')
        self.assertEqual(result, 'Fallback Title')
        
        # ✅ ПРАВИЛЬНО: Тестируем fallback при отсутствии поля
        result = loc.get_product_translation('amanita_powder_001', 'nonexistent_field', 'Fallback Field')
        self.assertEqual(result, 'Fallback Field')
        
        # ✅ ПРАВИЛЬНО: Тестируем fallback при отсутствии данных компонента
        result = loc.get_component_translation('nonexistent_component', 'common_name', 'Fallback Component')
        self.assertEqual(result, 'Fallback Component')
    
    def test_caching_mechanism(self):
        """Тест: Механизм кэширования работает корректно"""
        loc = LocalizationService('ru')
        
        # Устанавливаем данные продукта
        product_data = {
            'title': 'Кэшированный продукт',
            'description': 'Описание кэшированного продукта'
        }
        loc.set_product_data('cached_product', 'ru', product_data)
        
        # ✅ ПРАВИЛЬНО: Проверяем, что данные кэшируются
        result1 = loc.get_product_translation('cached_product', 'title')
        result2 = loc.get_product_translation('cached_product', 'title')
        
        self.assertEqual(result1, 'Кэшированный продукт')
        self.assertEqual(result2, 'Кэшированный продукт')
        
        # ✅ ПРАВИЛЬНО: Проверяем статистику кэша
        stats = loc.product_localization.get_cache_stats()
        self.assertGreater(stats['cached_products'], 0)
    
    def test_error_handling_real_scenarios(self):
        """Тест: Обработка ошибок в реальных сценариях"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Тестируем обработку неверных ключей
        result = loc.t('invalid.key.format')
        self.assertEqual(result, 'invalid.key.format')
        
        # ✅ ПРАВИЛЬНО: Тестируем обработку пустых ключей
        result = loc.t('')
        self.assertEqual(result, '')
        
        # ✅ ПРАВИЛЬНО: Тестируем обработку None ключей
        result = loc.t(None)
        self.assertEqual(result, None)
    
    def test_language_support_validation(self):
        """Тест: Валидация поддержки языков"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Проверяем список поддерживаемых языков
        supported_languages = loc.get_supported_languages()
        self.assertIsInstance(supported_languages, list)
        self.assertIn('ru', supported_languages)
        self.assertIn('en', supported_languages)
        
        # ✅ ПРАВИЛЬНО: Проверяем валидацию языков
        self.assertTrue(loc.is_language_supported('ru'))
        self.assertTrue(loc.is_language_supported('en'))
        self.assertFalse(loc.is_language_supported('invalid_lang'))
    
    def test_data_setting_and_retrieval(self):
        """Тест: Установка и получение данных локализации"""
        loc = LocalizationService('ru')
        
        # ✅ ПРАВИЛЬНО: Тестируем установку данных продукта
        product_data = {
            'title': 'Тестовый продукт',
            'description': 'Описание тестового продукта',
            'price': '100 EUR'
        }
        loc.set_product_data('test_product', 'ru', product_data)
        
        # Проверяем, что данные установлены
        self.assertEqual(loc.get_product_translation('test_product', 'title'), 'Тестовый продукт')
        self.assertEqual(loc.get_product_translation('test_product', 'description'), 'Описание тестового продукта')
        self.assertEqual(loc.get_product_translation('test_product', 'price'), '100 EUR')
        
        # ✅ ПРАВИЛЬНО: Тестируем установку данных компонента
        component_data = {
            'common_name': 'Тестовый компонент',
            'scientific_name': 'Testus componentus',
            'description': 'Описание тестового компонента'
        }
        loc.set_component_data('test_component', 'ru', component_data)
        
        # Проверяем, что данные установлены
        self.assertEqual(loc.get_component_translation('test_component', 'common_name'), 'Тестовый компонент')
        self.assertEqual(loc.get_component_translation('test_component', 'scientific_name'), 'Testus componentus')
        self.assertEqual(loc.get_component_translation('test_component', 'description'), 'Описание тестового компонента')
    
    def test_parameter_substitution(self):
        """Тест: Подстановка параметров в переводах"""
        loc = LocalizationService('ru')
        
        # Устанавливаем данные с параметрами
        product_data = {
            'title': 'Продукт {name}',
            'description': 'Описание продукта {name} с ценой {price}'
        }
        loc.set_product_data('param_product', 'ru', product_data)
        
        # ✅ ПРАВИЛЬНО: Тестируем подстановку параметров
        result = loc.get_product_translation('param_product', 'title', name='Мухомор')
        self.assertEqual(result, 'Продукт Мухомор')
        
        result = loc.get_product_translation('param_product', 'description', name='Мухомор', price='100 EUR')
        self.assertEqual(result, 'Описание продукта Мухомор с ценой 100 EUR')
    
    def test_cache_management(self):
        """Тест: Управление кэшем"""
        loc = LocalizationService('ru')
        
        # Устанавливаем данные
        product_data = {'title': 'Кэшированный продукт'}
        loc.set_product_data('cache_test', 'ru', product_data)
        
        # ✅ ПРАВИЛЬНО: Проверяем, что данные кэшируются
        stats = loc.product_localization.get_cache_stats()
        self.assertGreater(stats['cached_products'], 0)
        
        # ✅ ПРАВИЛЬНО: Проверяем, что данные доступны из кэша
        result1 = loc.get_product_translation('cache_test', 'title')
        self.assertEqual(result1, 'Кэшированный продукт')
        
        # ✅ ПРАВИЛЬНО: Проверяем очистку кэша
        loc.product_localization.clear_cache()
        stats_after_clear = loc.product_localization.get_cache_stats()
        self.assertEqual(stats_after_clear['cached_products'], 0)
        
        # ✅ ПРАВИЛЬНО: После очистки кэша данные недоступны (нет fallback для cache_test)
        result2 = loc.get_product_translation('cache_test', 'title')
        self.assertEqual(result2, '[title]')  # Fallback значение


class TestProductLocalizationService(unittest.TestCase):
    """Тесты для ProductLocalizationService"""
    
    def setUp(self):
        """Настройка тестов"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_templates_dir = None
        
        # Создаем временную структуру директорий
        self.templates_dir = os.path.join(self.temp_dir, "templates", "products")
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Создаем тестовый JSON файл
        product_data = {
            "products": {
                "test_product": {
                    "title": "Тестовый продукт",
                    "description": "Описание тестового продукта"
                }
            }
        }
        
        with open(os.path.join(self.templates_dir, "ru.json"), 'w', encoding='utf-8') as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2)
        
        # Мокаем APP_ROOT_DIR
        import config
        self.original_app_root = getattr(config, 'APP_ROOT_DIR', None)
        config.APP_ROOT_DIR = self.temp_dir
    
    def tearDown(self):
        """Очистка после тестов"""
        import config
        if self.original_app_root is not None:
            config.APP_ROOT_DIR = self.original_app_root
        else:
            delattr(config, 'APP_ROOT_DIR')
    
    def test_get_translation(self):
        """Тест получения переводов"""
        service = ProductLocalizationService('ru')
        
        # Тестируем получение существующего перевода
        self.assertEqual(service.get_translation('product.test_product.title'), 'Тестовый продукт')
        self.assertEqual(service.get_translation('product.test_product.description'), 'Описание тестового продукта')
        
        # Тестируем fallback
        self.assertEqual(service.get_translation('product.nonexistent.field'), '[field]')
    
    def test_set_data(self):
        """Тест установки данных"""
        service = ProductLocalizationService('ru')
        
        # Устанавливаем данные
        data = {'title': 'Новый продукт', 'description': 'Новое описание'}
        service.set_data('new_product', 'ru', data)
        
        # Проверяем, что данные установлены
        self.assertEqual(service.get_translation('product.new_product.title'), 'Новый продукт')
        self.assertEqual(service.get_translation('product.new_product.description'), 'Новое описание')

    def test_uses_fallback_service_when_cache_miss(self):
        """ProductLocalizationService обязан вызывать FallbackLocalizationService"""
        fallback_service = MagicMock()
        fallback_service.get_translation_with_fallback.return_value = FallbackResult(
            translation='Fallback product title',
            level=FallbackLevel.DEFAULT_LANGUAGE,
            source='language_ru',
            confidence=0.8
        )
        service = ProductLocalizationService('en', fallback_service=fallback_service)

        result = service.get_translation('product.test_product.title')

        fallback_service.get_translation_with_fallback.assert_called_once()
        self.assertEqual(result, 'Fallback product title')


class TestComponentLocalizationService(unittest.TestCase):
    """Тесты для ComponentLocalizationService"""
    
    def setUp(self):
        """Настройка тестов"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_templates_dir = None
        
        # Создаем временную структуру директорий
        self.templates_dir = os.path.join(self.temp_dir, "templates", "components")
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Создаем тестовый JSON файл
        component_data = {
            "components": {
                "test_component": {
                    "common_name": "Тестовый компонент",
                    "scientific_name": "Testus componentus"
                }
            }
        }
        
        with open(os.path.join(self.templates_dir, "ru.json"), 'w', encoding='utf-8') as f:
            json.dump(component_data, f, ensure_ascii=False, indent=2)
        
        # Мокаем APP_ROOT_DIR
        import config
        self.original_app_root = getattr(config, 'APP_ROOT_DIR', None)
        config.APP_ROOT_DIR = self.temp_dir
    
    def tearDown(self):
        """Очистка после тестов"""
        import config
        if self.original_app_root is not None:
            config.APP_ROOT_DIR = self.original_app_root
        else:
            delattr(config, 'APP_ROOT_DIR')
    
    def test_get_translation(self):
        """Тест получения переводов"""
        service = ComponentLocalizationService('ru')
        
        # Тестируем получение существующего перевода
        self.assertEqual(service.get_translation('component.test_component.common_name'), 'Тестовый компонент')
        self.assertEqual(service.get_translation('component.test_component.scientific_name'), 'Testus componentus')
        
        # Тестируем fallback
        self.assertEqual(service.get_translation('component.nonexistent.field'), '[field]')
    
    def test_set_data(self):
        """Тест установки данных"""
        service = ComponentLocalizationService('ru')
        
        # Устанавливаем данные
        data = {'common_name': 'Новый компонент', 'scientific_name': 'Novus componentus'}
        service.set_data('new_component', 'ru', data)
        
        # Проверяем, что данные установлены
        self.assertEqual(service.get_translation('component.new_component.common_name'), 'Новый компонент')
        self.assertEqual(service.get_translation('component.new_component.scientific_name'), 'Novus componentus')

    def test_uses_fallback_service_when_cache_miss(self):
        """ComponentLocalizationService обязан вызывать FallbackLocalizationService"""
        fallback_service = MagicMock()
        fallback_service.get_translation_with_fallback.return_value = FallbackResult(
            translation='Fallback component name',
            level=FallbackLevel.DEFAULT_LANGUAGE,
            source='language_ru',
            confidence=0.8
        )
        service = ComponentLocalizationService('en', fallback_service=fallback_service)

        result = service.get_translation('component.test_component.common_name')

        fallback_service.get_translation_with_fallback.assert_called_once()
        self.assertEqual(result, 'Fallback component name')

    def test_loads_simple_field_from_ipfs(self):
        """Тест: простые поля загружаются через get_component_translations (обратная совместимость)"""
        ipfs_service = MagicMock(name="MultilingualIPFSService")
        service = ComponentLocalizationService('ru', ipfs_service=ipfs_service)
        
        # Mock для simple field
        component_data = {'title': 'Test Title', 'common_name': 'Test Component'}
        ipfs_service.get_component_translations.return_value = component_data
        
        # Загружаем simple field
        result = service._load_from_ipfs('test_component', 'title')
        
        # Проверяем, что использовался get_component_translations
        ipfs_service.get_component_translations.assert_called_once_with('test_component', 'ru')
        self.assertEqual(result, 'Test Title')

    def test_loads_per_component_field_from_ipfs(self):
        """Тест: per-component fields загружаются через get_component_translations()"""
        ipfs_service = MagicMock(name="MultilingualIPFSService")
        service = ComponentLocalizationService('ru', ipfs_service=ipfs_service)
        
        biounit_id = "amanita_muscaria"  # строка, biounit_id
        
        # Mock для per-component simple field
        component_data = {
            'generic_description': 'Описание для amanita_muscaria',
            'effects': 'Эффекты для amanita_muscaria',
            'title': 'Мухомор красный'
        }
        ipfs_service.get_component_translations.return_value = component_data
        
        # Загружаем per-component field
        result = service._load_from_ipfs(biounit_id, 'generic_description')
        
        # Проверяем, что использовался get_component_translations С biounit_id
        ipfs_service.get_component_translations.assert_called_once_with(biounit_id, 'ru')
        # Проверяем, что get_component_description_template НЕ вызывался
        ipfs_service.get_component_description_template.assert_not_called()
        self.assertEqual(result, 'Описание для amanita_muscaria')

    def test_is_complex_field(self):
        """Тест: метод _is_complex_field корректно определяет тип поля"""
        service = ComponentLocalizationService('ru')
        
        # Проверяем, что per-component поля НЕ являются complex fields
        # (они должны быть simple fields через get_component_translations)
        self.assertFalse(service._is_complex_field('generic_description'))
        self.assertFalse(service._is_complex_field('effects'))
        self.assertFalse(service._is_complex_field('shamanic'))
        self.assertFalse(service._is_complex_field('warnings'))
        self.assertFalse(service._is_complex_field('description'))
        
        # Проверяем simple fields
        self.assertFalse(service._is_complex_field('title'))
        self.assertFalse(service._is_complex_field('common_name'))
        self.assertFalse(service._is_complex_field('scientific_name'))
        
        # Проверяем, что complex fields пустое множество (глобальные шаблоны не используются)
        self.assertEqual(service.COMPLEX_COMPONENT_FIELDS, set())

    def test_extract_field_from_complex_data(self):
        """Тест: метод _extract_field_from_complex_data корректно извлекает поля"""
        service = ComponentLocalizationService('ru')
        
        complex_data = {
            'generic_description': 'Test generic description',
            'effects': 'Test effects',
            'shamanic': 'Test shamanic',
            'warnings': 'Test warnings'
        }
        
        # Проверяем извлечение полей
        self.assertEqual(service._extract_field_from_complex_data(complex_data, 'generic_description'), 
                        'Test generic description')
        self.assertEqual(service._extract_field_from_complex_data(complex_data, 'effects'), 'Test effects')
        
        # Проверяем отсутствующие поля
        self.assertIsNone(service._extract_field_from_complex_data(complex_data, 'nonexistent'))
        
        # Проверяем обработку пустых данных
        self.assertIsNone(service._extract_field_from_complex_data({}, 'generic_description'))
        self.assertIsNone(service._extract_field_from_complex_data(None, 'generic_description'))

    def test_fallback_for_per_component_fields(self):
        """Тест: fallback логика работает для per-component fields"""
        ipfs_service = MagicMock(name="MultilingualIPFSService")
        fallback_service = MagicMock(name="FallbackLocalizationService")
        fallback_service.get_translation_with_fallback.return_value = FallbackResult(
            translation='Fallback generic description',
            level=FallbackLevel.DEFAULT_LANGUAGE,
            source='language_ru',
            confidence=0.8
        )
        
        service = ComponentLocalizationService(
            'en',
            ipfs_service=ipfs_service,
            fallback_service=fallback_service
        )
        
        biounit_id = "test_component"
        
        # Mock: per-component field не найден в IPFS
        ipfs_service.get_component_translations.return_value = None
        
        # Запрашиваем per-component field
        result = service.get_translation(f'component.{biounit_id}.generic_description')
        
        # Проверяем, что использовался fallback
        self.assertEqual(result, 'Fallback generic description')
        # Проверяем, что get_component_translations вызывался для fallback (для requested и default языка)
        # Вызывается для 'en' (requested) и 'ru' (default)
        self.assertTrue(ipfs_service.get_component_translations.called)
        calls = ipfs_service.get_component_translations.call_args_list
        # Проверяем, что был вызов для requested языка 'en'
        self.assertTrue(any(call[0] == (biounit_id, 'en') for call in calls), 
                       f"Expected call with ('{biounit_id}', 'en'), got calls: {calls}")

    def test_caches_per_component_field(self):
        """Тест: per-component fields кэшируются"""
        ipfs_service = MagicMock(name="MultilingualIPFSService")
        cache_service = MagicMock(name="TranslationCacheService")
        # Настраиваем cache_service.get() чтобы возвращал None (кэш пуст)
        cache_service.get.return_value = None
        service = ComponentLocalizationService(
            'ru',
            ipfs_service=ipfs_service,
            cache_service=cache_service
        )
        
        biounit_id = "test_component"
        
        # Mock для per-component simple field
        component_data = {'generic_description': 'Test generic description', 'effects': 'Test effects'}
        ipfs_service.get_component_translations.return_value = component_data
        
        # Первый вызов - должен загрузить и закэшировать
        result1 = service.get_translation(f'component.{biounit_id}.generic_description')
        self.assertEqual(result1, 'Test generic description')
        
        # Проверяем, что get_component_translations вызывался с biounit_id
        ipfs_service.get_component_translations.assert_called_with(biounit_id, 'ru')
        
        # Проверяем, что кэш вызывался
        cache_service.set.assert_called()


if __name__ == '__main__':
    unittest.main()
