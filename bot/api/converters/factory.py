"""
Фабрика конвертеров для создания и управления экземплярами конвертеров.

Этот модуль реализует Factory и Singleton паттерны для централизованного
управления конвертерами между API и Service моделями.
"""

from typing import Optional
from .base import BaseConverter

class ConverterFactory:
    """
    Фабрика для создания и управления конвертерами.
    
    Реализует Singleton паттерн для каждого типа конвертера,
    обеспечивая единственный экземпляр на все приложение.
    """
    
    # Приватные атрибуты для хранения экземпляров конвертеров
    _product_converter: Optional['ProductConverter'] = None
    _component_converter: Optional['OrganicComponentConverter'] = None
    _price_converter: Optional['PriceConverter'] = None
    
    @classmethod
    def get_product_converter(cls) -> 'ProductConverter':
        """
        Возвращает синглтон ProductConverter.
        
        Returns:
            ProductConverter: Единственный экземпляр конвертера продуктов
            
        Raises:
            ImportError: Если ProductConverter не может быть импортирован
        """
        if cls._product_converter is None:
            try:
                from .product_converter import ProductConverter
                cls._product_converter = ProductConverter()
            except ImportError as e:
                raise ImportError(f"Не удалось импортировать ProductConverter: {e}")
        return cls._product_converter
    
    @classmethod
    def get_component_converter(cls) -> 'OrganicComponentConverter':
        """
        Возвращает синглтон OrganicComponentConverter.
        
        Returns:
            OrganicComponentConverter: Единственный экземпляр конвертера компонентов
            
        Raises:
            ImportError: Если OrganicComponentConverter не может быть импортирован
        """
        if cls._component_converter is None:
            try:
                from .organic_component_converter import OrganicComponentConverter
                cls._component_converter = OrganicComponentConverter()
            except ImportError as e:
                raise ImportError(f"Не удалось импортировать OrganicComponentConverter: {e}")
        return cls._component_converter
    
    @classmethod
    def get_price_converter(cls) -> 'PriceConverter':
        """
        Возвращает синглтон PriceConverter.
        
        Returns:
            PriceConverter: Единственный экземпляр конвертера цен
            
        Raises:
            ImportError: Если PriceConverter не может быть импортирован
        """
        if cls._price_converter is None:
            try:
                from .price_converter import PriceConverter
                cls._price_converter = PriceConverter()
            except ImportError as e:
                raise ImportError(f"Не удалось импортировать PriceConverter: {e}")
        return cls._price_converter
    
    @classmethod
    def reset_all_converters(cls) -> None:
        """
        Сбрасывает все экземпляры конвертеров.
        
        Этот метод используется в тестах для очистки состояния
        между тестовыми случаями.
        """
        cls._product_converter = None
        cls._component_converter = None
        cls._price_converter = None
    
    @classmethod
    def get_all_converters(cls) -> dict:
        """
        Возвращает словарь со всеми доступными конвертерами.
        
        Returns:
            dict: Словарь с именами и экземплярами конвертеров
        """
        converters = {}
        
        try:
            converters['product'] = cls.get_product_converter()
        except ImportError:
            pass
        
        try:
            converters['component'] = cls.get_component_converter()
        except ImportError:
            pass
        
        try:
            converters['price'] = cls.get_price_converter()
        except ImportError:
            pass
        
        return converters
