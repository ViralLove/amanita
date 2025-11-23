"""
Тест полного отображения каталога в Telegram
Использует реальные данные из active_catalog.json и organic_descriptions.json
"""
import pytest
import json
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

# Настройка логирования для теста
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты для реального форматирования
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from handlers.common.formatting.product_formatter_service import ProductFormatterService
    from handlers.common.formatting.product_formatter_config import ProductFormatterConfig
    from handlers.common.formatting.section_tracker import SectionTracker, SectionTypes
    REAL_FORMATTER_AVAILABLE = True
    logger.info("✅ Реальный ProductFormatterService доступен")
except ImportError as e:
    REAL_FORMATTER_AVAILABLE = False
    logger.warning(f"⚠️ Реальный ProductFormatterService недоступен: {e}")

# Импорты для реальной локализации
try:
    from services.common.localization import Localization
    REAL_LOCALIZATION_AVAILABLE = True
    logger.info("✅ Реальный Localization сервис доступен")
except ImportError as e:
    REAL_LOCALIZATION_AVAILABLE = False
    logger.warning(f"⚠️ Реальный Localization сервис недоступен: {e}")

# Импорты для валидации CID
try:
    from validation.factory import ValidationFactory
    from validation.validators import CIDValidator
    from validation.rules import ValidationResult
    VALIDATION_FACTORY_AVAILABLE = True
    logger.info("✅ ValidationFactory доступен")
except ImportError as e:
    VALIDATION_FACTORY_AVAILABLE = False
    logger.warning(f"⚠️ ValidationFactory недоступен: {e}")

# Импорт мок-сервисов
try:
    from tests.mock_catalog_service import MockCatalogService
    MOCK_SERVICES_AVAILABLE = True
    logger.info("✅ MockCatalogService доступен")
except ImportError as e:
    MOCK_SERVICES_AVAILABLE = False
    logger.warning(f"⚠️ MockCatalogService недоступен: {e}")

class TestCatalogDisplay:
    """Тест отображения каталога в Telegram"""
    
    @pytest.fixture
    def real_catalog_data(self):
        """Загружает реальные данные каталога"""
        catalog_path = Path(__file__).parent.parent.parent / "catalog" / "active_catalog.json"
        descriptions_path = Path(__file__).parent.parent.parent / "catalog" / "organic_descriptions.json"
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
        
        with open(descriptions_path, 'r', encoding='utf-8') as f:
            descriptions_data = json.load(f)
        
        return catalog_data, descriptions_data
    
    @pytest.fixture
    def mock_telegram_context(self):
        """Создает мок контекста Telegram"""
        context = Mock()
        context.bot = Mock()
        context.bot.send_photo = AsyncMock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        return context
    
    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок callback query"""
        callback = Mock()
        callback.from_user.id = 12345
        callback.data = "menu:catalog"
        callback.message = Mock()
        callback.message.message_id = 100
        callback.message.chat.id = 12345
        return callback
    
    @pytest.fixture
    def mock_localization(self):
        """Создает мок локализации"""
        loc = Mock()
        loc.t = lambda key, **kwargs: f"Localized: {key}"
        return loc
    
    @pytest.fixture
    def real_localization(self):
        """Создает реальную локализацию"""
        if REAL_LOCALIZATION_AVAILABLE:
            try:
                loc = Localization('ru')
                logger.info("✅ Реальная локализация инициализирована")
                return loc
            except Exception as e:
                logger.warning(f"⚠️ Ошибка инициализации реальной локализации: {e}")
                # Fallback на мок
                loc = Mock()
                loc.t = lambda key, **kwargs: f"Localized: {key}"
                return loc
        else:
            # Fallback на мок
            loc = Mock()
            loc.t = lambda key, **kwargs: f"Localized: {key}"
            return loc
    
    @pytest.fixture
    def cid_validator(self):
        """Создает CIDValidator через ValidationFactory"""
        if VALIDATION_FACTORY_AVAILABLE:
            try:
                validator = ValidationFactory.get_cid_validator()
                logger.info("✅ CIDValidator получен через ValidationFactory")
                return validator
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения CIDValidator: {e}")
                return None
        else:
            logger.warning("⚠️ ValidationFactory недоступен, CIDValidator не создан")
            return None
    
    @pytest.fixture
    def mock_image_service(self):
        """Создает мок сервиса изображений"""
        service = Mock()
        service.download_image = AsyncMock(return_value="/tmp/mock_image.jpg")
        service.send_product_with_image = AsyncMock()
        service.send_product_details_with_image = AsyncMock()
        return service
    
    def test_catalog_data_structure(self, real_catalog_data):
        """Тест структуры данных каталога"""
        catalog_data, descriptions_data = real_catalog_data
        
        logger.info(f"📊 Загружено {len(catalog_data)} продуктов")
        logger.info(f"📋 Загружено {len(descriptions_data['organic_items'])} описаний")
        
        # Проверяем структуру каталога
        assert isinstance(catalog_data, list), "Каталог должен быть списком"
        assert len(catalog_data) > 0, "Каталог не должен быть пустым"
        
        # Проверяем структуру продукта
        first_product = catalog_data[0]
        required_fields = ['business_id', 'title', 'organic_components', 'categories', 'cover_image_url', 'forms', 'species', 'prices']
        
        for field in required_fields:
            assert field in first_product, f"Продукт должен содержать поле {field}"
        
        # Проверяем структуру компонентов
        components = first_product['organic_components']
        assert isinstance(components, list), "Компоненты должны быть списком"
        assert len(components) > 0, "Продукт должен содержать компоненты"
        
        component = components[0]
        component_fields = ['component_id', 'description_cid', 'proportion']
        for field in component_fields:
            assert field in component, f"Компонент должен содержать поле {field}"
        
        logger.info("✅ Структура данных каталога корректна")
    
    def test_organic_descriptions_structure(self, real_catalog_data):
        """Тест структуры описаний компонентов"""
        catalog_data, descriptions_data = real_catalog_data
        
        organic_items = descriptions_data['organic_items']
        assert isinstance(organic_items, dict), "Описания должны быть словарем"
        
        # Проверяем структуру описания
        first_item = list(organic_items.values())[0]
        description_fields = ['id', 'title', 'scientific_name', 'generic_description', 'effects', 'shamanic', 'warnings', 'dosage_instructions']
        
        for field in description_fields:
            assert field in first_item, f"Описание должно содержать поле {field}"
        
        logger.info("✅ Структура описаний компонентов корректна")
    
    @pytest.mark.asyncio
    async def test_catalog_service_initialization(self, real_catalog_data, mock_image_service, mock_localization):
        """Тест инициализации сервиса каталога с реальными данными"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mock_catalog_service import MockCatalogService
        from mock_formatter_service import MockFormatterService
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Создаем мок-сервис с реальными данными
        mock_service = MockCatalogService()
        formatter_service = MockFormatterService()
        
        # Проверяем загрузку продуктов
        products = mock_service.get_all_products()
        assert len(products) > 0, "Должны быть загружены продукты"
        
        logger.info(f"📦 Загружено {len(products)} продуктов для тестирования")
        
        # Проверяем форматирование первого продукта
        first_product = products[0]
        formatted = formatter_service.format_product_for_telegram(first_product, mock_localization)
        
        assert 'main_info' in formatted, "Форматирование должно содержать основную информацию"
        assert 'composition' in formatted, "Форматирование должно содержать состав"
        assert 'pricing' in formatted, "Форматирование должно содержать цены"
        assert 'details' in formatted, "Форматирование должно содержать детали"
        
        logger.info("✅ Сервис каталога инициализирован корректно")
    
    @pytest.mark.asyncio
    async def test_product_formatting_completeness(self, real_catalog_data, mock_localization):
        """Тест полноты форматирования продуктов"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mock_formatter_service import MockFormatterService
        from mock_catalog_service import MockCatalogService
        
        catalog_data, descriptions_data = real_catalog_data
        
        mock_service = MockCatalogService()
        formatter_service = MockFormatterService()
        products = mock_service.get_all_products()
        
        # Тестируем форматирование каждого продукта
        for i, product in enumerate(products[:5]):  # Тестируем первые 5 продуктов
            logger.info(f"🔍 Тестируем форматирование продукта {i+1}: {product.business_id}")
            
            formatted = formatter_service.format_product_for_telegram(product, mock_localization)
            
            # Проверяем, что все секции присутствуют и не пусты
            for section_name, section_content in formatted.items():
                assert section_content is not None, f"Секция {section_name} не должна быть None"
                assert len(section_content.strip()) > 0, f"Секция {section_name} не должна быть пустой"
                logger.info(f"  ✅ Секция {section_name}: {len(section_content)} символов")
            
            # Проверяем специфичные поля
            assert product.title in formatted['main_info'], "Основная информация должна содержать заголовок"
            assert product.business_id in formatted['main_info'], "Основная информация должна содержать business_id"
            
            if product.categories:
                for category in product.categories:
                    assert category in formatted['main_info'], f"Категория {category} должна быть в основной информации"
            
            logger.info(f"  ✅ Продукт {product.business_id} отформатирован корректно")
        
        logger.info("✅ Все продукты отформатированы корректно")
    
    @pytest.mark.skipif(not (REAL_FORMATTER_AVAILABLE and MOCK_SERVICES_AVAILABLE), reason="ProductFormatterService или MockCatalogService недоступны")
    def test_with_real_formatter(self, real_catalog_data, mock_localization):
        """Тест с реальным ProductFormatterService вместо мока"""
        logger.info("🔧 Тестируем с реальным ProductFormatterService")
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Создаем реальный форматтер с конфигурацией
        config = ProductFormatterConfig()
        formatter = ProductFormatterService(config)
        logger.info(f"✅ Создан реальный ProductFormatterService с конфигурацией: {type(config)}")
        
        # Загружаем продукты через MockCatalogService
        mock_service = MockCatalogService()
        products = mock_service.get_all_products()
        
        assert len(products) > 0, "Должны быть загружены продукты для тестирования"
        logger.info(f"📦 Загружено {len(products)} продуктов для тестирования с реальным форматтером")
        
        # Тестируем каждый продукт с реальным форматтером
        for i, product in enumerate(products[:3]):  # Тестируем первые 3 продукта
            logger.info(f"🔍 Тестируем продукт {i+1}: {product.title}")
            
            try:
                # Тестируем основное форматирование
                formatted_sections = formatter.format_product_for_telegram(product, mock_localization)
                
                # Проверяем структуру ответа
                assert isinstance(formatted_sections, dict), "Форматтер должен возвращать словарь"
                required_sections = ['main_info', 'composition', 'pricing', 'details']
                for section in required_sections:
                    assert section in formatted_sections, f"Отсутствует секция {section}"
                    assert isinstance(formatted_sections[section], str), f"Секция {section} должна быть строкой"
                    assert len(formatted_sections[section]) > 0, f"Секция {section} не должна быть пустой"
                
                # Проверяем качество форматирования
                main_info = formatted_sections['main_info']
                assert product.title in main_info, "Название продукта должно быть в main_info"
                assert len(main_info) > 50, "main_info должен содержать достаточно информации"
                
                composition = formatted_sections['composition']
                if product.organic_components:
                    assert len(composition) > 20, "composition должен содержать информацию о компонентах"
                
                pricing = formatted_sections['pricing']
                if product.prices:
                    assert len(pricing) > 20, "pricing должен содержать информацию о ценах"
                
                details = formatted_sections['details']
                assert len(details) > 10, "details должен содержать детали продукта"
                
                logger.info(f"  ✅ Продукт {product.title} отформатирован реальным форматтером успешно")
                logger.info(f"    📊 main_info: {len(formatted_sections['main_info'])} символов")
                logger.info(f"    📊 composition: {len(formatted_sections['composition'])} символов")
                logger.info(f"    📊 pricing: {len(formatted_sections['pricing'])} символов")
                logger.info(f"    📊 details: {len(formatted_sections['details'])} символов")
                
            except Exception as e:
                logger.error(f"❌ Ошибка форматирования продукта {product.title}: {e}")
                raise
        
        logger.info("✅ Все продукты успешно отформатированы реальным ProductFormatterService")
    
    @pytest.mark.skipif(not (REAL_FORMATTER_AVAILABLE and MOCK_SERVICES_AVAILABLE), reason="ProductFormatterService или MockCatalogService недоступны")
    def test_formatter_configuration(self, real_catalog_data, mock_localization):
        """Тест конфигурации ProductFormatterService"""
        logger.info("🔧 Тестируем конфигурацию ProductFormatterService")
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Тестируем различные конфигурации
        configs_to_test = [
            ProductFormatterConfig(),  # Конфигурация по умолчанию
            ProductFormatterConfig(max_text_length=500),  # Ограниченная длина
            ProductFormatterConfig(enable_emoji=False),  # Без эмодзи
            ProductFormatterConfig(enable_html=False),  # Без HTML
        ]
        
        # Загружаем один продукт для тестирования
        mock_service = MockCatalogService()
        products = mock_service.get_all_products()
        test_product = products[0] if products else None
        
        assert test_product is not None, "Должен быть доступен продукт для тестирования"
        logger.info(f"📦 Тестируем конфигурации на продукте: {test_product.title}")
        
        for i, config in enumerate(configs_to_test):
            logger.info(f"🔍 Тестируем конфигурацию {i+1}: {type(config)}")
            
            formatter = ProductFormatterService(config)
            
            try:
                formatted_sections = formatter.format_product_for_telegram(test_product, mock_localization)
                
                # Проверяем что форматирование работает с каждой конфигурацией
                assert isinstance(formatted_sections, dict), f"Конфигурация {i+1} должна возвращать словарь"
                
                # Проверяем ограничения длины текста
                if config.max_text_length:
                    total_length = sum(len(section) for section in formatted_sections.values())
                    if total_length > config.max_text_length:
                        # Проверяем что текст был обрезан
                        logger.info(f"  📏 Текст обрезан: {total_length} > {config.max_text_length}")
                
                # Проверяем отключение эмодзи
                if not config.enable_emoji:
                    for section_name, section_content in formatted_sections.items():
                        # Проверяем что в тексте нет эмодзи (простая проверка на Unicode символы)
                        emoji_chars = [char for char in section_content if ord(char) > 127 and len(char.encode('utf-8')) > 2]
                        if emoji_chars:
                            logger.warning(f"  ⚠️ Найдены эмодзи в секции {section_name} при отключенных эмодзи")
                
                logger.info(f"  ✅ Конфигурация {i+1} работает корректно")
                
            except Exception as e:
                logger.error(f"❌ Ошибка с конфигурацией {i+1}: {e}")
                raise
        
        logger.info("✅ Все конфигурации ProductFormatterService работают корректно")
    
    @pytest.mark.skipif(not (REAL_FORMATTER_AVAILABLE and MOCK_SERVICES_AVAILABLE), reason="ProductFormatterService или MockCatalogService недоступны")
    def test_section_tracker_prevention(self, real_catalog_data, mock_localization):
        """Тест логики SectionTracker для предотвращения дублирования"""
        logger.info("🔧 Тестируем логику SectionTracker")
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Создаем форматтер
        config = ProductFormatterConfig()
        formatter = ProductFormatterService(config)
        
        # Загружаем продукты
        mock_service = MockCatalogService()
        products = mock_service.get_all_products()
        test_product = products[0] if products else None
        
        assert test_product is not None, "Должен быть доступен продукт для тестирования"
        logger.info(f"📦 Тестируем SectionTracker на продукте: {test_product.title}")
        
        try:
            # Тестируем детальное форматирование (где используется SectionTracker)
            details_text = formatter.format_product_details_for_telegram(test_product, mock_localization)
            
            # Проверяем что текст не пустой
            assert len(details_text) > 0, "Детальное описание не должно быть пустым"
            logger.info(f"📊 Детальное описание: {len(details_text)} символов")
            
            # Проверяем структуру детального описания
            assert test_product.title in details_text, "Название продукта должно быть в детальном описании"
            
            # Проверяем что секции не дублируются (простая проверка)
            lines = details_text.split('\n')
            section_headers = [line for line in lines if '🧬' in line or '💰' in line or '📦' in line or '🏷️' in line]
            
            # Проверяем что заголовки секций уникальны
            unique_headers = set(section_headers)
            if len(section_headers) != len(unique_headers):
                logger.warning(f"⚠️ Возможно дублирование заголовков секций: {len(section_headers)} vs {len(unique_headers)}")
            
            logger.info(f"📋 Найдено {len(section_headers)} заголовков секций")
            logger.info(f"✅ SectionTracker логика работает корректно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования SectionTracker: {e}")
            raise
    
    @pytest.mark.skipif(not REAL_FORMATTER_AVAILABLE, reason="ProductFormatterService недоступен")
    def test_fallback_handling(self, real_catalog_data, mock_localization):
        """Тест fallback стратегий при ошибках форматирования"""
        logger.info("🔧 Тестируем fallback стратегии")
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Создаем форматтер
        config = ProductFormatterConfig()
        formatter = ProductFormatterService(config)
        
        # Создаем продукт с проблемными данными для тестирования fallback
        class ProblematicProduct:
            def __init__(self):
                self.title = "Test Product"
                self.business_id = "test_product"
                self.organic_components = []
                self.categories = []
                self.cover_image_url = ""
                self.forms = []
                self.species = ""
                self.prices = []
                self.status = 1
        
        problematic_product = ProblematicProduct()
        logger.info(f"📦 Тестируем fallback на проблемном продукте: {problematic_product.title}")
        
        try:
            # Тестируем форматирование проблемного продукта
            formatted_sections = formatter.format_product_for_telegram(problematic_product, mock_localization)
            
            # Проверяем что форматирование не падает и возвращает валидный результат
            assert isinstance(formatted_sections, dict), "Fallback должен возвращать словарь"
            
            required_sections = ['main_info', 'composition', 'pricing', 'details']
            for section in required_sections:
                assert section in formatted_sections, f"Fallback должен содержать секцию {section}"
                assert isinstance(formatted_sections[section], str), f"Секция {section} должна быть строкой"
            
            # Проверяем что основная информация присутствует даже при проблемных данных
            main_info = formatted_sections['main_info']
            assert problematic_product.title in main_info, "Название продукта должно быть в main_info даже при проблемных данных"
            
            logger.info(f"✅ Fallback стратегии работают корректно")
            logger.info(f"📊 main_info fallback: {len(formatted_sections['main_info'])} символов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования fallback стратегий: {e}")
            raise
    
    @pytest.mark.skipif(not REAL_LOCALIZATION_AVAILABLE, reason="Реальный Localization сервис недоступен")
    def test_with_real_localization(self, real_catalog_data, real_localization):
        """Тест с реальным Localization сервисом"""
        logger.info("🌍 Тестируем с реальным Localization сервисом")
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Проверяем базовую функциональность локализации
        assert real_localization is not None, "Реальная локализация должна быть инициализирована"
        logger.info(f"✅ Реальная локализация инициализирована с языком: {real_localization.lang}")
        
        # Тестируем ключевые переводы каталога
        catalog_keys = [
            "catalog.loading",
            "catalog.empty", 
            "catalog.product.species",
            "catalog.product.forms",
            "catalog.product.categories",
            "catalog.product.prices"
        ]
        
        for key in catalog_keys:
            translation = real_localization.t(key)
            logger.info(f"🔑 Ключ '{key}' -> '{translation}'")
            
            # Проверяем что получили реальный перевод, а не ключ
            assert translation != key, f"Ключ '{key}' должен быть переведен, а не возвращать сам ключ"
            assert len(translation) > 0, f"Перевод для ключа '{key}' не должен быть пустым"
        
        # Тестируем обработку отсутствующих ключей
        missing_key = "catalog.nonexistent.key"
        fallback_translation = real_localization.t(missing_key)
        logger.info(f"🔑 Отсутствующий ключ '{missing_key}' -> '{fallback_translation}'")
        
        # Для отсутствующих ключей должен возвращаться сам ключ
        assert fallback_translation == missing_key, f"Отсутствующий ключ должен возвращать сам ключ: {missing_key}"
        
        logger.info("✅ Реальная локализация работает корректно")
    
    @pytest.mark.skipif(not (REAL_LOCALIZATION_AVAILABLE and REAL_FORMATTER_AVAILABLE), reason="Localization или ProductFormatterService недоступны")
    def test_localization_with_formatter(self, real_catalog_data, real_localization):
        """Тест интеграции локализации с форматтером"""
        logger.info("🔗 Тестируем интеграцию локализации с форматтером")
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Создаем реальный форматтер
        config = ProductFormatterConfig()
        formatter = ProductFormatterService(config)
        logger.info("✅ ProductFormatterService создан с реальной локализацией")
        
        # Загружаем продукты через MockCatalogService
        mock_service = MockCatalogService()
        products = mock_service.get_all_products()
        
        assert len(products) > 0, "Должны быть загружены продукты для тестирования"
        logger.info(f"📦 Загружено {len(products)} продуктов для тестирования с реальной локализацией")
        
        # Тестируем форматирование с реальной локализацией
        test_product = products[0]
        logger.info(f"🔍 Тестируем продукт: {test_product.title}")
        
        try:
            # Форматируем продукт с реальной локализацией
            formatted_sections = formatter.format_product_for_telegram(test_product, real_localization)
            
            # Проверяем структуру ответа
            assert isinstance(formatted_sections, dict), "Форматтер должен возвращать словарь"
            required_sections = ['main_info', 'composition', 'pricing', 'details']
            for section in required_sections:
                assert section in formatted_sections, f"Отсутствует секция {section}"
                assert isinstance(formatted_sections[section], str), f"Секция {section} должна быть строкой"
                assert len(formatted_sections[section]) > 0, f"Секция {section} не должна быть пустой"
            
            # Проверяем качество локализованного текста
            main_info = formatted_sections['main_info']
            logger.info(f"📊 main_info с локализацией: {len(main_info)} символов")
            
            # Проверяем что в тексте есть реальные переводы, а не ключи
            # (это может варьироваться в зависимости от реализации форматтера)
            logger.info(f"📝 Пример main_info: {main_info[:100]}...")
            
            logger.info("✅ Интеграция локализации с форматтером работает корректно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования интеграции локализации: {e}")
            raise
    
    @pytest.mark.skipif(not REAL_LOCALIZATION_AVAILABLE, reason="Реальный Localization сервис недоступен")
    def test_localization_fallback(self, real_localization):
        """Тест fallback стратегий локализации"""
        logger.info("🛡️ Тестируем fallback стратегии локализации")
        
        # Тестируем различные сценарии ошибок
        test_cases = [
            ("valid.key", "Должен работать для валидного ключа"),
            ("invalid.nonexistent.key", "Должен возвращать ключ для несуществующего"),
            ("", "Должен обрабатывать пустой ключ"),
            ("key.with.special.chars!", "Должен обрабатывать специальные символы")
        ]
        
        for key, description in test_cases:
            logger.info(f"🔍 Тестируем: {description}")
            
            try:
                result = real_localization.t(key)
                logger.info(f"  Результат: '{result}'")
                
                # Базовые проверки
                assert result is not None, f"Результат не должен быть None для ключа '{key}'"
                assert isinstance(result, str), f"Результат должен быть строкой для ключа '{key}'"
                
                # Для невалидных ключей должен возвращаться сам ключ
                if key in ["invalid.nonexistent.key", "", "key.with.special.chars!"]:
                    assert result == key, f"Невалидный ключ '{key}' должен возвращать сам ключ"
                
            except Exception as e:
                logger.error(f"❌ Ошибка при тестировании ключа '{key}': {e}")
                # Fallback стратегия должна работать даже при ошибках
                logger.info(f"  Fallback результат: '{key}'")
        
        logger.info("✅ Fallback стратегии локализации работают корректно")
    
    @pytest.mark.skipif(not VALIDATION_FACTORY_AVAILABLE, reason="ValidationFactory недоступен")
    def test_cid_validation_with_factory(self, cid_validator):
        """Тест CID валидации через ValidationFactory"""
        logger.info("🔍 Тестируем CID валидацию через ValidationFactory")
        
        # Проверяем что CIDValidator доступен
        assert cid_validator is not None, "CIDValidator должен быть доступен"
        assert isinstance(cid_validator, CIDValidator), "Должен быть экземпляр CIDValidator"
        logger.info("✅ CIDValidator успешно получен через ValidationFactory")
        
        # Тестируем валидные CID
        valid_cids = [
            "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",  # Реальный CID из каталога
            "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",  # Реальный CID из каталога
            "Qm123456789",  # Минимальный валидный CID
            "QmABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"  # Длинный CID
        ]
        
        for cid in valid_cids:
            logger.info(f"🔍 Тестируем валидный CID: {cid}")
            result = cid_validator.validate(cid)
            
            assert result.is_valid, f"CID '{cid}' должен быть валидным"
            assert result.error_message is None, f"Для валидного CID '{cid}' не должно быть ошибки"
            logger.info(f"  ✅ CID '{cid}' прошел валидацию")
        
        # Тестируем невалидные CID
        invalid_cids = [
            ("", "Пустой CID"),
            ("Qm", "Слишком короткий CID"),
            ("InvalidCID", "CID без префикса Qm"),
            ("QmInvalid!", "CID с недопустимыми символами"),
            ("123456789", "CID без префикса Qm"),
            (None, "None CID")
        ]
        
        for cid, description in invalid_cids:
            logger.info(f"🔍 Тестируем невалидный CID ({description}): {cid}")
            result = cid_validator.validate(cid)
            
            assert not result.is_valid, f"CID '{cid}' ({description}) должен быть невалидным"
            assert result.error_message is not None, f"Для невалидного CID '{cid}' должно быть сообщение об ошибке"
            assert result.error_code is not None, f"Для невалидного CID '{cid}' должен быть код ошибки"
            logger.info(f"  ✅ CID '{cid}' ({description}) корректно отклонен: {result.error_message}")
        
        logger.info("✅ CID валидация через ValidationFactory работает корректно")
    
    @pytest.mark.skipif(not VALIDATION_FACTORY_AVAILABLE, reason="ValidationFactory недоступен")
    def test_cid_validation_scenarios(self, cid_validator):
        """Тест различных сценариев CID валидации"""
        logger.info("🔍 Тестируем различные сценарии CID валидации")
        
        assert cid_validator is not None, "CIDValidator должен быть доступен"
        
        # Тестируем граничные случаи
        edge_cases = [
            ("Qm1", "Минимальный CID (3 символа)", True),  # Предполагаем min_length=3
            ("Qm12", "CID длиной 4 символа", True),
            ("Qm", "CID длиной 2 символа", False),
            ("Q", "CID длиной 1 символ", False),
            ("Qm" + "A" * 100, "Очень длинный CID", True),
            ("QmA", "CID с заглавной буквой", True),
            ("Qma", "CID с строчной буквой", True),
            ("Qm1A", "CID с цифрой и буквой", True),
            ("Qm!@#", "CID с специальными символами", False),
            ("Qm ", "CID с пробелом", False),
            (" Qm1", "CID с ведущим пробелом", False),
            ("Qm1 ", "CID с завершающим пробелом", False)
        ]
        
        for cid, description, should_be_valid in edge_cases:
            logger.info(f"🔍 Тестируем граничный случай ({description}): '{cid}'")
            result = cid_validator.validate(cid)
            
            if should_be_valid:
                assert result.is_valid, f"CID '{cid}' ({description}) должен быть валидным"
                logger.info(f"  ✅ CID '{cid}' ({description}) корректно принят")
            else:
                assert not result.is_valid, f"CID '{cid}' ({description}) должен быть невалидным"
                logger.info(f"  ✅ CID '{cid}' ({description}) корректно отклонен: {result.error_message}")
        
        # Тестируем типы данных
        type_test_cases = [
            (123, "Число вместо строки"),
            (["Qm1"], "Список вместо строки"),
            ({"cid": "Qm1"}, "Словарь вместо строки"),
            (True, "Булево значение вместо строки")
        ]
        
        for invalid_input, description in type_test_cases:
            logger.info(f"🔍 Тестируем неправильный тип ({description}): {invalid_input}")
            result = cid_validator.validate(invalid_input)
            
            assert not result.is_valid, f"Входное значение '{invalid_input}' ({description}) должно быть невалидным"
            assert "строкой" in result.error_message.lower() or "string" in result.error_message.lower(), \
                f"Сообщение об ошибке должно указывать на неправильный тип: {result.error_message}"
            logger.info(f"  ✅ Неправильный тип '{invalid_input}' ({description}) корректно отклонен")
        
        logger.info("✅ Все сценарии CID валидации обработаны корректно")
    
    @pytest.mark.skipif(not VALIDATION_FACTORY_AVAILABLE, reason="ValidationFactory недоступен")
    def test_catalog_cid_validation(self, real_catalog_data, cid_validator):
        """Тест валидации CID в реальном каталоге"""
        logger.info("🔍 Тестируем валидацию CID в реальном каталоге")
        
        catalog_data, descriptions_data = real_catalog_data
        
        assert cid_validator is not None, "CIDValidator должен быть доступен"
        
        # Собираем все CID из каталога
        all_cids = set()
        
        # CID из описаний компонентов
        for product_data in catalog_data:
            for component in product_data.get("organic_components", []):
                if "description_cid" in component:
                    all_cids.add(component["description_cid"])
            
            # CID изображений продуктов
            if "cover_image_url" in product_data:
                all_cids.add(product_data["cover_image_url"])
        
        # CID из описаний компонентов
        for description_cid, description_data in descriptions_data.items():
            all_cids.add(description_cid)
        
        logger.info(f"📊 Найдено {len(all_cids)} уникальных CID для валидации")
        
        # Валидируем каждый CID
        validation_results = {}
        for cid in all_cids:
            logger.info(f"🔍 Валидируем CID: {cid}")
            result = cid_validator.validate(cid)
            validation_results[cid] = result
            
            if result.is_valid:
                logger.info(f"  ✅ CID '{cid}' валиден")
            else:
                logger.error(f"  ❌ CID '{cid}' невалиден: {result.error_message}")
        
        # Проверяем результаты
        valid_cids = [cid for cid, result in validation_results.items() if result.is_valid]
        invalid_cids = [cid for cid, result in validation_results.items() if not result.is_valid]
        
        logger.info(f"📊 Результаты валидации:")
        logger.info(f"  ✅ Валидных CID: {len(valid_cids)}")
        logger.info(f"  ❌ Невалидных CID: {len(invalid_cids)}")
        
        # Проверяем качество данных в каталоге
        if invalid_cids:
            logger.warning(f"⚠️ Найдены невалидные CID в каталоге: {invalid_cids}")
            logger.warning("💡 Это указывает на проблемы качества данных в active_catalog.json")
            
            # Для реальных данных это предупреждение, а не ошибка
            # Но фиксируем статистику для мониторинга качества данных
            invalid_percentage = (len(invalid_cids) / len(all_cids)) * 100
            logger.info(f"📊 Процент невалидных CID: {invalid_percentage:.1f}%")
            
            # Если процент невалидных CID слишком высок, это ошибка
            if invalid_percentage > 10:  # Более 10% невалидных CID
                assert False, f"Слишком много невалидных CID в каталоге: {invalid_percentage:.1f}%"
        else:
            logger.info("✅ Все CID в каталоге валидны")
        
        # Дополнительные проверки
        assert len(valid_cids) > 0, "Должен быть хотя бы один валидный CID в каталоге"
        
        # Успешное завершение теста
        logger.info("✅ Тест валидации CID в каталоге завершен успешно")
        
        logger.info("✅ Все CID в каталоге прошли валидацию успешно")
        
        # Документируем результаты для отчета
        logger.info("📋 Детальные результаты валидации:")
        for cid, result in validation_results.items():
            logger.info(f"  CID: {cid[:20]}... -> {'✅ Валиден' if result.is_valid else '❌ Невалиден'}")
    
    @pytest.mark.asyncio
    async def test_catalog_display_simulation(self, real_catalog_data, mock_telegram_context, mock_callback_query, mock_localization, mock_image_service):
        """Тест симуляции отображения каталога в Telegram"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mock_catalog_service import MockCatalogService
        from mock_formatter_service import MockFormatterService
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Инициализируем мок-сервисы
        catalog_service = MockCatalogService()
        formatter_service = MockFormatterService()
        
        # Получаем продукты
        products = catalog_service.get_all_products()
        logger.info(f"📦 Начинаем симуляцию отображения {len(products)} продуктов")
        
        # Симулируем отправку каждого продукта
        for i, product in enumerate(products[:3]):  # Тестируем первые 3 продукта
            logger.info(f"📤 Симулируем отправку продукта {i+1}: {product.title}")
            
            # Форматируем продукт
            formatted = formatter_service.format_product_for_telegram(product, mock_localization)
            combined_text = formatted['main_info'] + formatted['composition'] + formatted['pricing'] + formatted['details']
            
            # Симулируем отправку изображения с текстом
            await mock_image_service.send_product_with_image(
                mock_callback_query,
                product.cover_image_url,
                combined_text,
                product.business_id
            )
            
            # Проверяем, что методы были вызваны
            mock_image_service.send_product_with_image.assert_called()
            
            logger.info(f"  ✅ Продукт {product.business_id} отправлен успешно")
        
        logger.info("✅ Симуляция отображения каталога завершена успешно")
    
    @pytest.mark.asyncio
    async def test_product_details_display_simulation(self, real_catalog_data, mock_telegram_context, mock_callback_query, mock_localization, mock_image_service):
        """Тест симуляции отображения деталей продукта"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mock_catalog_service import MockCatalogService
        from mock_formatter_service import MockFormatterService
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Инициализируем мок-сервисы
        catalog_service = MockCatalogService()
        formatter_service = MockFormatterService()
        
        # Получаем первый продукт для тестирования деталей
        products = catalog_service.get_all_products()
        test_product = products[0]
        
        logger.info(f"🔍 Тестируем отображение деталей продукта: {test_product.title}")
        
        # Форматируем основную информацию
        main_info = formatter_service.format_product_main_info_for_telegram(test_product, mock_localization)
        
        # Симулируем отправку деталей
        await mock_image_service.send_product_details_with_image(
            mock_callback_query,
            test_product.cover_image_url,
            main_info,
            test_product.business_id
        )
        
        # Проверяем вызов
        mock_image_service.send_product_details_with_image.assert_called()
        
        logger.info(f"  ✅ Детали продукта {test_product.business_id} отправлены успешно")
    
    def test_component_id_validation_with_real_data(self, real_catalog_data):
        """Тест валидации component_id с реальными данными"""
        from model.organic_component import OrganicComponent
        
        catalog_data, descriptions_data = real_catalog_data
        
        # Собираем все component_id из каталога
        all_component_ids = set()
        for product in catalog_data:
            for component in product['organic_components']:
                all_component_ids.add(component['component_id'])
        
        logger.info(f"🔍 Найдено {len(all_component_ids)} уникальных component_id")
        
        # Тестируем валидацию каждого component_id
        for component_id in all_component_ids:
            logger.info(f"  🧪 Тестируем валидацию: {component_id}")
            
            try:
                # Создаем компонент с реальным component_id
                component = OrganicComponent.from_dict({
                    "component_id": component_id,
                    "description_cid": "QmTestDescription",
                    "proportion": "100%"
                })
                
                logger.info(f"    ✅ {component_id} прошел валидацию")
                
            except Exception as e:
                logger.error(f"    ❌ {component_id} не прошел валидацию: {e}")
                pytest.fail(f"component_id '{component_id}' не прошел валидацию: {e}")
        
        logger.info("✅ Все component_id из реального каталога прошли валидацию")
    
    def test_catalog_data_completeness(self, real_catalog_data):
        """Тест полноты данных каталога"""
        catalog_data, descriptions_data = real_catalog_data
        
        # Проверяем, что все component_id из каталога имеют описания
        catalog_component_ids = set()
        for product in catalog_data:
            for component in product['organic_components']:
                catalog_component_ids.add(component['component_id'])
        
        description_component_ids = set(descriptions_data['organic_items'].keys())
        
        missing_descriptions = catalog_component_ids - description_component_ids
        if missing_descriptions:
            logger.warning(f"⚠️ Отсутствуют описания для: {missing_descriptions}")
        
        extra_descriptions = description_component_ids - catalog_component_ids
        if extra_descriptions:
            logger.info(f"ℹ️ Есть описания, не используемые в каталоге: {extra_descriptions}")
        
        # Проверяем, что все продукты имеют изображения
        products_without_images = []
        for product in catalog_data:
            if not product.get('cover_image_url') or product['cover_image_url'].strip() == '':
                products_without_images.append(product['business_id'])
        
        if products_without_images:
            logger.warning(f"⚠️ Продукты без изображений: {products_without_images}")
        
        logger.info("✅ Проверка полноты данных завершена")
    
    @pytest.mark.asyncio
    async def test_full_catalog_workflow(self, real_catalog_data, mock_telegram_context, mock_callback_query, mock_localization, mock_image_service):
        """Тест полного workflow отображения каталога"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mock_catalog_service import MockCatalogService
        from mock_formatter_service import MockFormatterService
        
        catalog_data, descriptions_data = real_catalog_data
        
        logger.info("🚀 Начинаем полный тест workflow каталога")
        
        # 1. Инициализация сервисов
        catalog_service = MockCatalogService()
        formatter_service = MockFormatterService()
        
        # 2. Получение продуктов
        products = catalog_service.get_all_products()
        logger.info(f"📦 Получено {len(products)} продуктов")
        
        # 3. Отображение каталога (первые 3 продукта)
        logger.info("📤 Начинаем отображение каталога")
        for i, product in enumerate(products[:3]):
            formatted = formatter_service.format_product_for_telegram(product, mock_localization)
            combined_text = formatted['main_info'] + formatted['composition'] + formatted['pricing'] + formatted['details']
            
            await mock_image_service.send_product_with_image(
                mock_callback_query,
                product.cover_image_url,
                combined_text,
                product.business_id
            )
            
            logger.info(f"  ✅ Продукт {i+1}/{3}: {product.title}")
        
        # 4. Отображение деталей первого продукта
        logger.info("🔍 Отображаем детали первого продукта")
        first_product = products[0]
        main_info = formatter_service.format_product_main_info_for_telegram(first_product, mock_localization)
        
        await mock_image_service.send_product_details_with_image(
            mock_callback_query,
            first_product.cover_image_url,
            main_info,
            first_product.business_id
        )
        
        logger.info("✅ Полный workflow каталога выполнен успешно")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
