"""
Основные валидаторы для системы валидации.

Этот модуль содержит конкретные реализации валидаторов для различных
типов данных, используемых в приложении.
"""

import re
import decimal
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

from .rules import ValidationRule, ValidationResult
from .exceptions import (
    CIDValidationError,
    ProportionValidationError,
    PriceValidationError,
    ProductValidationError
)


class CIDValidator(ValidationRule[str]):
    """
    Валидатор для IPFS CID.
    
    Проверяет, что CID соответствует формату IPFS:
    - Начинается с 'Qm'
    - Содержит только буквы и цифры
    - Имеет минимальную длину
    """
    
    def __init__(self, min_length: int = 3):
        """
        Инициализирует валидатор CID.
        
        Args:
            min_length: Минимальная длина CID
        """
        self.min_length = min_length
        self.cid_pattern = re.compile(r'^Qm[a-zA-Z0-9]+$')
    
    def validate(self, value: str) -> ValidationResult:
        """
        Валидирует CID.
        
        Args:
            value: CID для валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not value:
            return ValidationResult.failure(
                "CID не может быть пустым",
                field_name="cid",
                field_value=value,
                error_code="EMPTY_CID"
            )
        
        if not isinstance(value, str):
            return ValidationResult.failure(
                "CID должен быть строкой",
                field_name="cid",
                field_value=value,
                error_code="INVALID_CID_TYPE"
            )
        
        if len(value) < self.min_length:
            return ValidationResult.failure(
                f"CID должен содержать не менее {self.min_length} символов",
                field_name="cid",
                field_value=value,
                error_code="CID_TOO_SHORT"
            )
        
        if not value.startswith('Qm'):
            return ValidationResult.failure(
                "CID должен начинаться с 'Qm'",
                field_name="cid",
                field_value=value,
                error_code="INVALID_CID_PREFIX"
            )
        
        if not self.cid_pattern.match(value):
            return ValidationResult.failure(
                "CID содержит недопустимые символы",
                field_name="cid",
                field_value=value,
                error_code="INVALID_CID_CHARACTERS"
            )
        
        return ValidationResult.success()


class ProportionValidator(ValidationRule[str]):
    """
    Валидатор для пропорций.
    
    Поддерживает форматы:
    - Проценты: 100%, 50%
    - Вес: 100g, 50.5g, 1kg
    - Объем: 30ml, 1.5l
    """
    
    def __init__(self):
        """Инициализирует валидатор пропорций."""
        # Паттерны для различных форматов
        self.percentage_pattern = re.compile(r'^(\d{1,3})(?:\.\d+)?%$')
        self.weight_pattern = re.compile(r'^(-?\d+(?:\.\d+)?)\s*(g|kg|oz|lb)$')
        self.volume_pattern = re.compile(r'^(-?\d+(?:\.\d+)?)\s*(ml|l|oz_fl)$')
    
    def validate(self, value: str) -> ValidationResult:
        """
        Валидирует пропорцию.
        
        Args:
            value: Пропорция для валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not value:
            return ValidationResult.failure(
                "Пропорция не может быть пустой",
                field_name="proportion",
                field_value=value,
                error_code="EMPTY_PROPORTION"
            )
        
        if not isinstance(value, str):
            return ValidationResult.failure(
                "Пропорция должна быть строкой",
                field_name="proportion",
                field_value=value,
                error_code="INVALID_PROPORTION_TYPE"
            )
        
        # Проверяем проценты
        percentage_match = self.percentage_pattern.match(value)
        if percentage_match:
            percentage = int(percentage_match.group(1))
            if percentage < 1 or percentage > 100:
                return ValidationResult.failure(
                    "Процент должен быть от 1% до 100%",
                    field_name="proportion",
                    field_value=value,
                    error_code="INVALID_PERCENTAGE_RANGE"
                )
            return ValidationResult.success()
        
        # Проверяем вес
        weight_match = self.weight_pattern.match(value)
        if weight_match:
            weight_value = float(weight_match.group(1))
            if weight_value <= 0:
                return ValidationResult.failure(
                    "Вес должен быть положительным числом",
                    field_name="proportion",
                    field_value=value,
                    error_code="INVALID_WEIGHT_VALUE"
                )
            return ValidationResult.success()
        
        # Проверяем объем
        volume_match = self.volume_pattern.match(value)
        if volume_match:
            volume_value = float(volume_match.group(1))
            if volume_value <= 0:
                return ValidationResult.failure(
                    "Объем должен быть положительным числом",
                    field_name="proportion",
                    field_value=value,
                    error_code="INVALID_VOLUME_VALUE"
                )
            return ValidationResult.success()
        
        return ValidationResult.failure(
            "Некорректный формат пропорции. Поддерживаемые форматы: 50%, 100g, 30ml",
            field_name="proportion",
            field_value=value,
            error_code="INVALID_PROPORTION_FORMAT"
        )


class PriceValidator(ValidationRule[Union[int, float, str, Decimal]]):
    """
    Валидатор для цен.
    
    Проверяет:
    - Цена является положительным числом
    - Поддерживаемые валюты
    - Корректные единицы измерения
    """
    
    SUPPORTED_CURRENCIES = {
        'EUR', 'USD', 'GBP', 'JPY', 'RUB', 'CNY', 'USDT', 'ETH', 'BTC'
    }
    
    def __init__(self, min_price: Union[int, float, Decimal] = 0):
        """
        Инициализирует валидатор цен.
        
        Args:
            min_price: Минимальная допустимая цена
        """
        self.min_price = Decimal(str(min_price))
    
    def validate(self, value: Union[int, float, str, Decimal]) -> ValidationResult:
        """
        Валидирует цену.
        
        Args:
            value: Цена для валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        if value is None:
            return ValidationResult.failure(
                "Цена не может быть пустой",
                field_name="price",
                field_value=value,
                error_code="EMPTY_PRICE"
            )
        
        try:
            price_decimal = Decimal(str(value))
        except (ValueError, TypeError, decimal.InvalidOperation):
            return ValidationResult.failure(
                "Цена должна быть числом",
                field_name="price",
                field_value=value,
                error_code="INVALID_PRICE_TYPE"
            )
        
        if price_decimal <= self.min_price:
            return ValidationResult.failure(
                f"Цена должна быть больше {self.min_price}",
                field_name="price",
                field_value=value,
                error_code="PRICE_TOO_LOW"
            )
        
        return ValidationResult.success()
    
    def validate_with_currency(self, price: Union[int, float, str, Decimal], currency: str) -> ValidationResult:
        """
        Валидирует цену с валютой.
        
        Args:
            price: Цена для валидации
            currency: Валюта
            
        Returns:
            ValidationResult: Результат валидации
        """
        # Сначала валидируем цену
        price_result = self.validate(price)
        if not price_result.is_valid:
            return price_result
        
        # Затем валидируем валюту
        if not currency:
            return ValidationResult.failure(
                "Валюта не может быть пустой",
                field_name="currency",
                field_value=currency,
                error_code="EMPTY_CURRENCY"
            )
        
        if currency.upper() not in self.SUPPORTED_CURRENCIES:
            return ValidationResult.failure(
                f"Неподдерживаемая валюта: {currency}. Поддерживаемые: {', '.join(sorted(self.SUPPORTED_CURRENCIES))}",
                field_name="currency",
                field_value=currency,
                error_code="UNSUPPORTED_CURRENCY"
            )
        
        return ValidationResult.success()


class ProductValidator(ValidationRule[Dict[str, Any]]):
    """
    Валидатор для продуктов.
    
    Проверяет комплексную валидацию продукта:
    - Обязательные поля
    - Валидация компонентов
    - Валидация цен
    - Валидация изображений
    """
    
    def __init__(self):
        """Инициализирует валидатор продуктов."""
        self.cid_validator = CIDValidator()
        self.proportion_validator = ProportionValidator()
        self.price_validator = PriceValidator()
    
    def validate(self, value: Dict[str, Any]) -> ValidationResult:
        """
        Валидирует продукт.
        
        Args:
            value: Данные продукта для валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not isinstance(value, dict):
            return ValidationResult.failure(
                "Продукт должен быть словарем",
                field_name="product",
                field_value=value,
                error_code="INVALID_PRODUCT_TYPE"
            )
        
        # Проверяем обязательные поля
        required_fields = ['id', 'title', 'organic_components']
        for field in required_fields:
            if field not in value:
                return ValidationResult.failure(
                    f"Отсутствует обязательное поле: {field}",
                    field_name=field,
                    field_value=None,
                    error_code="MISSING_REQUIRED_FIELD"
                )
        
        # Валидируем ID
        product_id = value.get('id')
        if not product_id:
            return ValidationResult.failure(
                "ID продукта не может быть пустым",
                field_name="id",
                field_value=product_id,
                error_code="MISSING_PRODUCT_ID"
            )
        
        # ID может быть строкой (business ID) или числом (blockchain ID)
        # Проверяем, что это не пустая строка
        if isinstance(product_id, str) and not product_id.strip():
            return ValidationResult.failure(
                "ID продукта не может быть пустой строкой",
                field_name="id",
                field_value=product_id,
                error_code="EMPTY_PRODUCT_ID"
            )
        
        # Если это число, проверяем, что оно положительное
        if isinstance(product_id, (int, float)) and product_id <= 0:
            return ValidationResult.failure(
                "ID продукта должен быть положительным числом",
                field_name="id",
                field_value=product_id,
                error_code="INVALID_PRODUCT_ID"
            )
        
        # Валидируем заголовок
        title = value.get('title')
        if not title or not title.strip():
            return ValidationResult.failure(
                "Заголовок продукта не может быть пустым",
                field_name="title",
                field_value=title,
                error_code="EMPTY_TITLE"
            )
        
        # Валидируем органические компоненты
        organic_components = value.get('organic_components', [])
        if not organic_components:
            return ValidationResult.failure(
                "Продукт должен содержать хотя бы один органический компонент",
                field_name="organic_components",
                field_value=organic_components,
                error_code="EMPTY_ORGANIC_COMPONENTS"
            )
        
        # Валидируем каждый компонент
        for i, component in enumerate(organic_components):
            component_result = self._validate_component(component, i)
            if not component_result.is_valid:
                return component_result
        
        # Валидируем изображение (если есть)
        cover_image = value.get('cover_image')
        if cover_image:
            image_result = self.cid_validator.validate(cover_image)
            if not image_result.is_valid:
                image_result.field_name = "cover_image"
                return image_result
        
        # Валидируем цены (если есть)
        prices = value.get('prices', [])
        for i, price_data in enumerate(prices):
            price_result = self._validate_price(price_data, i)
            if not price_result.is_valid:
                return price_result
        
        return ValidationResult.success()
    
    def _validate_component(self, component: Dict[str, Any], index: int) -> ValidationResult:
        """
        Валидирует органический компонент.
        
        Args:
            component: Данные компонента
            index: Индекс компонента
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not isinstance(component, dict):
            return ValidationResult.failure(
                f"Компонент {index} должен быть словарем",
                field_name=f"organic_components[{index}]",
                field_value=component,
                error_code="INVALID_COMPONENT_TYPE"
            )
        
        # Проверяем обязательные поля компонента
        required_component_fields = ['biounit_id', 'description_cid', 'proportion']
        for field in required_component_fields:
            if field not in component:
                return ValidationResult.failure(
                    f"Отсутствует обязательное поле компонента: {field}",
                    field_name=f"organic_components[{index}].{field}",
                    field_value=None,
                    error_code="MISSING_COMPONENT_FIELD"
                )
        
        # Валидируем biounit_id
        biounit_id = component.get('biounit_id')
        if not biounit_id or not biounit_id.strip():
            return ValidationResult.failure(
                "biounit_id не может быть пустым",
                field_name=f"organic_components[{index}].biounit_id",
                field_value=biounit_id,
                error_code="EMPTY_BIOUNIT_ID"
            )
        
        # Валидируем description_cid
        description_cid = component.get('description_cid')
        cid_result = self.cid_validator.validate(description_cid)
        if not cid_result.is_valid:
            cid_result.field_name = f"organic_components[{index}].description_cid"
            return cid_result
        
        # Валидируем proportion
        proportion = component.get('proportion')
        proportion_result = self.proportion_validator.validate(proportion)
        if not proportion_result.is_valid:
            proportion_result.field_name = f"organic_components[{index}].proportion"
            return proportion_result
        
        return ValidationResult.success()
    
    def _validate_price(self, price_data: Dict[str, Any], index: int) -> ValidationResult:
        """
        Валидирует данные цены.
        
        Args:
            price_data: Данные цены
            index: Индекс цены
            
        Returns:
            ValidationResult: Результат валидации
        """
        if not isinstance(price_data, dict):
            return ValidationResult.failure(
                f"Цена {index} должна быть словарем",
                field_name=f"prices[{index}]",
                field_value=price_data,
                error_code="INVALID_PRICE_TYPE"
            )
        
        price = price_data.get('price')
        currency = price_data.get('currency', 'EUR')
        
        return self.price_validator.validate_with_currency(price, currency)
