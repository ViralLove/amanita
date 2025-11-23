#!/usr/bin/env python3
"""
Тест для проверки исправления проблемы formatter_service = None в реальном сервере
"""
import pytest
import logging
from unittest.mock import Mock

logger = logging.getLogger(__name__)


class TestServerFixVerification:
    """Тест проверяет что исправление работает в реальном сервере"""
    
    def test_real_server_formatter_service_fix(self):
        """Тест проверяет что исправление работает в реальном сервере"""
        logger.info("🔍 Проверяем исправление в реальном сервере")
        
        # Импортируем реальные сервисы как в сервере
        from dependencies import get_catalog_service, get_product_service
        
        # Создаем сервисы через dependency injection (как в реальном сервере)
        catalog_service = get_catalog_service()
        product_service = get_product_service()
        
        # Проверяем что formatter_service инициализирован в обоих сервисах
        assert catalog_service.formatter_service is not None, "CatalogService должен иметь formatter_service"
        assert product_service.formatter_service is not None, "ProductService должен иметь formatter_service"
        
        # Проверяем что это правильный тип
        from handlers.common.formatting import ProductFormatterService
        assert isinstance(catalog_service.formatter_service, ProductFormatterService), "CatalogService должен иметь ProductFormatterService"
        assert isinstance(product_service.formatter_service, ProductFormatterService), "ProductService должен иметь ProductFormatterService"
        
        logger.info("✅ CatalogService имеет корректный formatter_service")
        logger.info("✅ ProductService имеет корректный formatter_service")
        
        # Проверяем что сервисы могут форматировать продукты
        from services.common.localization import Localization
        loc = Localization('ru')
        
        # Создаем тестовый продукт
        from model.product import Product
        from model.organic_component import OrganicComponent
        from model.component_description import ComponentDescription
        
        test_component = OrganicComponent(
            component_id="test_component",
            description_cid="QmTest123",
            proportion="100%",
            description=ComponentDescription(
                generic_description="Тестовый компонент",
                effects="Тестовые эффекты",
                shamanic="Тестовое шаманское использование",
                warnings="Тестовые предупреждения",
                dosage_instructions=[]
            )
        )
        
        test_product = Product(
            business_id="test_product",
            blockchain_id=1,
            title="Тестовый продукт",
            organic_components=[test_component],
            categories=["test"],
            cover_image_url="QmTestImage",
            forms=["test_form"],
            species="Test species",
            prices=[{"weight": "100", "weight_unit": "g", "price": "10", "currency": "EUR"}],
            status=1,
            cid="QmTestProduct"
        )
        
        # Проверяем что форматирование работает
        formatted = catalog_service.formatter_service.format_product_for_telegram(test_product, loc)
        assert formatted is not None, "Форматирование должно работать"
        assert isinstance(formatted, dict), "Форматирование должно возвращать словарь"
        
        logger.info("✅ Форматирование продукта работает корректно")
        logger.info("🎉 Проблема formatter_service = None полностью исправлена!")
        logger.info("🎉 Сервер теперь должен работать без ошибок каталога!")
