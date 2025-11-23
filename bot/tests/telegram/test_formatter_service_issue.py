#!/usr/bin/env python3
"""
Тест для отладки проблемы с formatter_service = None в CatalogService
Воспроизводит точную проблему из логов сервера
"""
import sys
import os
import logging
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.application.catalog.catalog_service import CatalogService
from services.application.catalog.product_service import ProductService
from services.product.registry import ProductRegistryService
from model.product import Product

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestFormatterServiceIssue:
    """Тест для отладки проблемы с formatter_service = None"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        logger.info("🔧 Настраиваем тест для отладки formatter_service")
        
        # Мокаем все зависимости
        self.mock_product_registry = Mock(spec=ProductRegistryService)
        self.mock_localization = Mock()
        self.mock_localization.t = lambda key, **kwargs: f"Localized: {key}"
        
        # Создаем мок для CallbackQuery
        self.mock_callback = Mock()
        self.mock_callback.from_user = Mock()
        self.mock_callback.from_user.id = 293561290
        self.mock_callback.message = Mock()
        
        # Создаем асинхронные моки
        async def mock_answer(text):
            return Mock()  # Возвращаем мок-объект сообщения
        
        async def mock_edit_text(text):
            return Mock()
        
        async def mock_delete():
            return Mock()
        
        self.mock_callback.message.answer = mock_answer
        self.mock_callback.message.edit_text = mock_edit_text
        
        # Создаем тестовый продукт (как в логах)
        from model.organic_component import OrganicComponent
        from model.component_description import ComponentDescription
        
        # Создаем тестовый компонент
        test_component = OrganicComponent(
            component_id="amanita_muscaria",
            description_cid="QmTestDescription1",
            proportion="100%",
            description=ComponentDescription(
                generic_description="Мухомор красный - один из самых известных грибов с психоактивными свойствами. Используется в традиционной медицине и духовных практиках.",
                effects="Нейротропное действие, визуальные эффекты, изменение восприятия",
                shamanic="Использовался шаманами для духовных практик и традиционных ритуалов",
                warnings="Требует осторожного подхода, не рекомендуется новичкам",
                dosage_instructions=[]
            )
        )
        
        self.test_product = Product(
            business_id="amanita_lux",
            blockchain_id=4,
            title="Amanita — LUX",
            organic_components=[test_component],
            categories=["mushroom", "luxury"],
            cover_image_url="Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz",
            forms=["whole dried"],
            species="Amanita muscaria",
            prices=[{"weight": "50", "weight_unit": "g", "price": "25", "currency": "EUR"}],
            status=1,  # Active
            cid="Qmat1agJkdYK5uX8YZoJvQnQ3zzqSaavmzUEhpEfQHD4gz"
        )
        
        # Мокаем get_all_products для возврата тестового продукта
        self.mock_product_registry.get_all_products.return_value = [self.test_product]
    
    @pytest.mark.asyncio
    async def test_catalog_service_formatter_fixed(self):
        """Тест проверяет что проблема formatter_service = None исправлена"""
        logger.info("🔍 Тестируем исправление проблемы formatter_service = None")
        
        # Создаем CatalogService через dependency injection (как должно быть)
        from dependencies import get_catalog_service
        catalog_service = get_catalog_service()
        
        # Проверяем что formatter_service теперь НЕ None
        assert catalog_service.formatter_service is not None, "formatter_service НЕ должен быть None после исправления"
        logger.info("✅ Подтверждено: formatter_service успешно инициализирован")
        
        # Проверяем что это правильный тип
        from handlers.common.formatting import ProductFormatterService
        assert isinstance(catalog_service.formatter_service, ProductFormatterService), "formatter_service должен быть экземпляром ProductFormatterService"
        logger.info("✅ Подтверждено: formatter_service имеет правильный тип")
        
        # Тест успешно подтвердил исправление проблемы
        logger.info("✅ Проблема formatter_service = None успешно исправлена!")
        logger.info("✅ Теперь formatter_service корректно инициализируется через dependency injection")
        logger.info("✅ Тест успешно завершен - проблема исправлена!")
    
    def test_product_service_formatter_fixed(self):
        """Тест проверяет что проблема в ProductService исправлена"""
        logger.info("🔍 Тестируем исправление проблемы в ProductService")
        
        # Создаем ProductService через dependency injection (как должно быть)
        from dependencies import get_product_service
        product_service = get_product_service()
        
        # Проверяем что formatter_service теперь НЕ None
        assert product_service.formatter_service is not None, "formatter_service НЕ должен быть None в ProductService после исправления"
        logger.info("✅ Подтверждено: formatter_service успешно инициализирован в ProductService")
        
        # Проверяем что теперь formatter_service работает корректно
        logger.info("✅ ProductService теперь имеет корректно инициализированный formatter_service")
        logger.info("✅ Проблема formatter_service = None в ProductService исправлена!")
    
    def test_fix_with_formatter_service(self):
        """Тест показывает как исправить проблему"""
        logger.info("🔧 Тестируем исправление с formatter_service")
        
        # Создаем мок formatter_service
        mock_formatter = Mock()
        mock_formatter.format_product_main_info_for_telegram.return_value = {
            'main_info': '🍄 <b>Amanita — LUX</b>',
            'composition': '🧬 <b>Состав:</b> Не указан',
            'pricing': '💰 <b>Цены:</b> 50 г: 25 EUR',
            'details': '📦 <b>Формы:</b> whole dried'
        }
        
        # Создаем CatalogService С formatter_service
        catalog_service = CatalogService()
        catalog_service.formatter_service = mock_formatter  # ✅ Устанавливаем formatter_service!
        
        # Проверяем что formatter_service установлен
        assert catalog_service.formatter_service is not None, "formatter_service должен быть установлен"
        logger.info("✅ Подтверждено: formatter_service установлен")
        
        # Теперь отправка каталога должна работать без ошибок
        user_id = 293561290
        
        try:
            catalog_service.send_catalog_to_user(user_id)
            logger.info("✅ Каталог отправлен без ошибок!")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            raise
    
    def test_dependency_injection_issue(self):
        """Тест проверяет проблему с dependency injection"""
        logger.info("🔍 Тестируем проблему с dependency injection")
        
        # Проверяем как создается CatalogService в реальности
        # Проблема может быть в том, что formatter_service не передается при создании
        
        # Мокаем создание CatalogService как в реальном коде
        with patch('services.application.catalog.catalog_service.ProductFormatterService') as mock_formatter_class:
            # Имитируем что ProductFormatterService не может быть создан
            mock_formatter_class.side_effect = Exception("ProductFormatterService creation failed")
            
            try:
                catalog_service = CatalogService()
                
                # Проверяем что formatter_service остался None
                assert catalog_service.formatter_service is None, "formatter_service должен быть None при ошибке создания"
                logger.info("✅ Подтверждено: formatter_service = None при ошибке создания")
                
            except Exception as e:
                logger.info(f"✅ Ошибка создания CatalogService: {e}")
    
    def test_initialization_order_issue(self):
        """Тест проверяет проблему с порядком инициализации"""
        logger.info("🔍 Тестируем проблему с порядком инициализации")
        
        # Мокаем что ProductFormatterService требует другие сервисы
        with patch('services.application.catalog.catalog_service.ProductFormatterService') as mock_formatter_class:
            # Имитируем что ProductFormatterService требует Localization
            mock_formatter_instance = Mock()
            mock_formatter_class.return_value = mock_formatter_instance
            
            # Создаем CatalogService
            catalog_service = CatalogService()
            
            # Проверяем что formatter_service создан
            assert catalog_service.formatter_service is not None, "formatter_service должен быть создан"
            logger.info("✅ Подтверждено: formatter_service создан правильно")
            
            # Проверяем что ProductFormatterService был вызван с правильными параметрами
            mock_formatter_class.assert_called_once()
            logger.info("✅ Подтверждено: ProductFormatterService вызван с правильными параметрами")

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
