"""
Кастомные исключения для валидации продуктов и унифицированная ошибка API-уровня.
"""

from typing import Any, Dict, Optional
from bot.validation import ValidationError as CoreValidationError


class ProductValidationError(Exception):
    """Базовое исключение для ошибок валидации продуктов"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)

class InvalidCIDError(ProductValidationError):
    """Ошибка валидации CID"""
    def __init__(self, field: str, value: str):
        super().__init__(
            f"Неверный формат CID для поля '{field}': {value}. CID должен начинаться с 'Qm'",
            field=field,
            value=value
        )

class InvalidProductFormError(ProductValidationError):
    """Ошибка валидации формы продукта"""
    def __init__(self, value: str):
        valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", "mixed slices", "whole caps", "broken caps", "premium caps", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
        super().__init__(
            f"Неверная форма продукта: {value}. Допустимые значения: {', '.join(valid_forms)}",
            field="forms",
            value=value
        )

class InvalidBusinessIdError(ProductValidationError):
    """Ошибка валидации business_id"""
    def __init__(self, message: str):
        super().__init__(
            f"Ошибка валидации business_id: {message}",
            field="business_id",
            value=None
        )

class InvalidCurrencyError(ProductValidationError):
    """Ошибка валидации валюты"""
    def __init__(self, value: str):
        valid_currencies = ["EUR", "USD", "GBP"]
        super().__init__(
            f"Неверная валюта: {value}. Допустимые значения: {', '.join(valid_currencies)}",
            field="currency",
            value=value
        )

class EmptyCategoriesError(ProductValidationError):
    """Ошибка валидации пустых категорий"""
    def __init__(self):
        super().__init__(
            "Категории продукта не могут быть пустыми",
            field="categories",
            value=[]
        )

class InvalidPriceFormatError(ProductValidationError):
    """Ошибка валидации формата цены"""
    def __init__(self, field: str, value: any):
        super().__init__(
            f"Неверный формат для поля '{field}': {value}",
            field=field,
            value=value
        )


class UnifiedValidationError(ProductValidationError):
    """
    Унифицированная ошибка валидации для API-уровня.
    Совмещает внутренний результат валидации и человекочитаемое сообщение.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, field=field, value=value)
        self.error_code = error_code
        self.details = details or {}

    @classmethod
    def from_core_error(
        cls,
        core_error: CoreValidationError,
        default_message: str = "Ошибка валидации данных"
    ) -> "UnifiedValidationError":
        """Создает UnifiedValidationError из ядрового ValidationError."""
        return cls(
            message=str(core_error) or default_message,
            field=getattr(core_error, "field_name", None),
            value=getattr(core_error, "field_value", None),
            error_code=getattr(core_error, "error_code", None),
            details=getattr(core_error, "to_dict", lambda: {})(),
        )
