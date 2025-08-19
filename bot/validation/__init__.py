"""
Единая система валидации для всех слоев архитектуры.

Этот модуль предоставляет централизованную систему валидации данных,
которая используется во всех слоях приложения (API, Service, Blockchain)
для обеспечения консистентности и надежности.

Основные компоненты:
- ValidationRule: Базовый класс для всех правил валидации
- ValidationResult: Результат валидации с детальной информацией
- Validators: Специфичные валидаторы для разных типов данных
- ValidationFactory: Фабрика для создания валидаторов

Использование:
    from bot.validation import ValidationFactory
    
    validator = ValidationFactory.get_product_validator()
    result = validator.validate(product_data)
    
    if not result.is_valid:
        print(f"Ошибка валидации: {result.error_message}")
"""

from typing import List

# Импорты будут добавлены по мере создания файлов
from .rules import ValidationRule, ValidationResult, CompositeValidationRule
from .exceptions import (
    ValidationError,
    CIDValidationError,
    ProportionValidationError,
    PriceValidationError,
    ProductValidationError,
    CompositeValidationError,
    ValidationRuleError,
    create_validation_error_from_result
)
from .validators import CIDValidator, ProportionValidator, PriceValidator, ProductValidator
from .factory import ValidationFactory, CompositeValidationFactory

__version__ = "1.0.0"
__author__ = "Amanita Team"

__all__ = [
    "ValidationRule",
    "ValidationResult", 
    "CompositeValidationRule",
    "ValidationError",
    "CIDValidationError",
    "ProportionValidationError",
    "PriceValidationError",
    "ProductValidationError",
    "CompositeValidationError",
    "ValidationRuleError",
    "create_validation_error_from_result",
    "CIDValidator",
    "ProportionValidator", 
    "PriceValidator",
    "ProductValidator",
    "ValidationFactory",
    "CompositeValidationFactory",
]
