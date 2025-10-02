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

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.common.localization_service import LocalizationService
from services.common.localization import Localization
from services.common.product_localization import ProductLocalizationService
from services.common.component_localization import ComponentLocalizationService


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
        self.assertEqual(loc.t('component..field'), '[field]')  # Пустой biounit_id
        self.assertEqual(loc.t('component.biounit_id.'), '[field]')  # Пустое поле
    
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


if __name__ == '__main__':
    unittest.main()
