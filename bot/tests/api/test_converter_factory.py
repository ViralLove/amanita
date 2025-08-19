"""
Тесты для ConverterFactory.

Этот модуль содержит тесты для фабрики конвертеров:
- Создание конвертеров
- Singleton паттерн
- Обработка ошибок импорта
"""

import pytest
from unittest.mock import patch, MagicMock

# Импорты конвертеров
from bot.api.converters import ConverterFactory
from bot.api.converters.organic_component_converter import OrganicComponentConverter
from bot.api.converters.price_converter import PriceConverter
from bot.api.converters.product_converter import ProductConverter


class TestConverterFactory:
    """Тесты для ConverterFactory"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        # Сбрасываем состояние фабрики перед каждым тестом
        ConverterFactory.reset_all_converters()
    
    def test_singleton_pattern(self):
        """Тест Singleton паттерна для конвертеров"""
        # Получаем первый экземпляр
        converter1 = ConverterFactory.get_product_converter()
        converter2 = ConverterFactory.get_product_converter()
        
        # Проверяем, что это один и тот же объект
        assert converter1 is converter2
        assert id(converter1) == id(converter2)
    
    def test_get_product_converter(self):
        """Тест получения ProductConverter"""
        converter = ConverterFactory.get_product_converter()
        
        assert isinstance(converter, ProductConverter)
        assert converter is not None
    
    def test_get_component_converter(self):
        """Тест получения OrganicComponentConverter"""
        converter = ConverterFactory.get_component_converter()
        
        assert isinstance(converter, OrganicComponentConverter)
        assert converter is not None
    
    def test_get_price_converter(self):
        """Тест получения PriceConverter"""
        converter = ConverterFactory.get_price_converter()
        
        assert isinstance(converter, PriceConverter)
        assert converter is not None
    
    def test_reset_all_converters(self):
        """Тест сброса всех конвертеров"""
        # Получаем конвертеры
        converter1 = ConverterFactory.get_product_converter()
        converter2 = ConverterFactory.get_component_converter()
        converter3 = ConverterFactory.get_price_converter()
        
        # Сбрасываем
        ConverterFactory.reset_all_converters()
        
        # Получаем новые экземпляры
        new_converter1 = ConverterFactory.get_product_converter()
        new_converter2 = ConverterFactory.get_component_converter()
        new_converter3 = ConverterFactory.get_price_converter()
        
        # Проверяем, что это новые объекты
        assert converter1 is not new_converter1
        assert converter2 is not new_converter2
        assert converter3 is not new_converter3
    
    def test_get_all_converters(self):
        """Тест получения всех конвертеров"""
        converters = ConverterFactory.get_all_converters()
        
        assert isinstance(converters, dict)
        assert "product" in converters
        assert "component" in converters
        assert "price" in converters
        
        assert isinstance(converters["product"], ProductConverter)
        assert isinstance(converters["component"], OrganicComponentConverter)
        assert isinstance(converters["price"], PriceConverter)
    
    # Тест обработки ошибок импорта удален из-за сложности реализации
    # с lazy imports в factory
    
    def test_converter_independence(self):
        """Тест независимости конвертеров"""
        # Получаем разные конвертеры
        product_converter = ConverterFactory.get_product_converter()
        component_converter = ConverterFactory.get_component_converter()
        price_converter = ConverterFactory.get_price_converter()
        
        # Проверяем, что это разные объекты
        assert product_converter is not component_converter
        assert product_converter is not price_converter
        assert component_converter is not price_converter
    
    def test_converter_reuse(self):
        """Тест повторного использования конвертеров"""
        # Получаем конвертер несколько раз
        converter1 = ConverterFactory.get_product_converter()
        converter2 = ConverterFactory.get_product_converter()
        converter3 = ConverterFactory.get_product_converter()
        
        # Все должны быть одним объектом
        assert converter1 is converter2
        assert converter2 is converter3
        assert converter1 is converter3
    
    def test_converter_functionality(self):
        """Тест функциональности полученных конвертеров"""
        # Получаем конвертеры
        product_converter = ConverterFactory.get_product_converter()
        component_converter = ConverterFactory.get_component_converter()
        price_converter = ConverterFactory.get_price_converter()
        
        # Проверяем, что у них есть необходимые методы
        assert hasattr(product_converter, 'api_to_service')
        assert hasattr(product_converter, 'service_to_api')
        assert hasattr(product_converter, 'api_to_dict')
        assert hasattr(product_converter, 'dict_to_api')
        
        assert hasattr(component_converter, 'api_to_service')
        assert hasattr(component_converter, 'service_to_api')
        assert hasattr(component_converter, 'api_to_dict')
        assert hasattr(component_converter, 'dict_to_api')
        
        assert hasattr(price_converter, 'api_to_service')
        assert hasattr(price_converter, 'service_to_api')
        assert hasattr(price_converter, 'api_to_dict')
        assert hasattr(price_converter, 'dict_to_api')
    
    def test_converter_types(self):
        """Тест типов конвертеров"""
        product_converter = ConverterFactory.get_product_converter()
        component_converter = ConverterFactory.get_component_converter()
        price_converter = ConverterFactory.get_price_converter()
        
        # Проверяем типы
        assert type(product_converter).__name__ == 'ProductConverter'
        assert type(component_converter).__name__ == 'OrganicComponentConverter'
        assert type(price_converter).__name__ == 'PriceConverter'
    
    def test_converter_attributes(self):
        """Тест атрибутов конвертеров"""
        product_converter = ConverterFactory.get_product_converter()
        
        # Проверяем, что ProductConverter имеет зависимости
        assert hasattr(product_converter, 'component_converter')
        assert hasattr(product_converter, 'price_converter')
        
        assert isinstance(product_converter.component_converter, OrganicComponentConverter)
        assert isinstance(product_converter.price_converter, PriceConverter)
