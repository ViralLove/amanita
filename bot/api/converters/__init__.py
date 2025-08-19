"""
Модуль конвертеров для преобразования между API и Service моделями.

Этот модуль предоставляет централизованную систему конвертации данных
между API слоем (Pydantic модели) и Service слоем (dataclass модели).

Основные компоненты:
- BaseConverter: Базовый интерфейс для всех конвертеров
- ConverterFactory: Фабрика для создания и управления конвертерами
- ProductConverter: Конвертер для продуктов
- OrganicComponentConverter: Конвертер для органических компонентов
- PriceConverter: Конвертер для цен
"""

from .base import BaseConverter
from .factory import ConverterFactory
from .organic_component_converter import OrganicComponentConverter
from .price_converter import PriceConverter
from .product_converter import ProductConverter

__all__ = [
    'BaseConverter',
    'ConverterFactory',
    'OrganicComponentConverter',
    'PriceConverter',
    'ProductConverter',
]
