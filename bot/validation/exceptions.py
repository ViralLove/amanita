"""
Исключения для системы валидации.

Этот модуль содержит исключения, которые используются в системе валидации
для обработки различных типов ошибок валидации.
"""

from typing import Any, Optional, Dict, List
from .rules import ValidationResult


class ValidationError(Exception):
    """
    Базовое исключение для всех ошибок валидации.
    
    Это исключение используется для представления ошибок валидации
    с детальной информацией о проблеме.
    
    Attributes:
        message: Основное сообщение об ошибке
        field_name: Имя поля, которое вызвало ошибку
        field_value: Значение поля, которое вызвало ошибку
        error_code: Код ошибки для программной обработки
        suggestions: Предложения по исправлению ошибки
        validation_result: Результат валидации (если есть)
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        error_code: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        validation_result: Optional[ValidationResult] = None
    ):
        """
        Инициализирует исключение валидации.
        
        Args:
            message: Основное сообщение об ошибке
            field_name: Имя поля, которое вызвало ошибку
            field_value: Значение поля, которое вызвало ошибку
            error_code: Код ошибки для программной обработки
            suggestions: Предложения по исправлению ошибки
            validation_result: Результат валидации
        """
        super().__init__(message)
        self.message = message
        self.field_name = field_name
        self.field_value = field_value
        self.error_code = error_code
        self.suggestions = suggestions or []
        self.validation_result = validation_result
    
    def __str__(self) -> str:
        """Возвращает строковое представление исключения."""
        if self.field_name:
            return f"{self.field_name}: {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует исключение в словарь для сериализации."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "field_name": self.field_name,
            "field_value": self.field_value,
            "error_code": self.error_code,
            "suggestions": self.suggestions
        }


class CIDValidationError(ValidationError):
    """Исключение для ошибок валидации CID."""
    
    def __init__(
        self,
        message: str,
        cid_value: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            field_name="cid",
            field_value=cid_value,
            error_code=error_code or "INVALID_CID_FORMAT",
            suggestions=[
                "CID должен начинаться с 'Qm'",
                "CID должен содержать только буквы и цифры",
                "Длина CID должна быть не менее 3 символов"
            ]
        )


class ProportionValidationError(ValidationError):
    """Исключение для ошибок валидации пропорций."""
    
    def __init__(
        self,
        message: str,
        proportion_value: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            field_name="proportion",
            field_value=proportion_value,
            error_code=error_code or "INVALID_PROPORTION_FORMAT",
            suggestions=[
                "Используйте формат: 100%, 50g, 30ml",
                "Процент должен быть от 1% до 100%",
                "Вес должен быть положительным числом с единицей измерения"
            ]
        )


class PriceValidationError(ValidationError):
    """Исключение для ошибок валидации цен."""
    
    def __init__(
        self,
        message: str,
        price_value: Optional[Any] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            field_name="price",
            field_value=price_value,
            error_code=error_code or "INVALID_PRICE_FORMAT",
            suggestions=[
                "Цена должна быть положительным числом",
                "Поддерживаемые валюты: EUR, USD, GBP, RUB",
                "Цена не может быть нулевой или отрицательной"
            ]
        )


class ProductValidationError(ValidationError):
    """Исключение для ошибок валидации продуктов."""
    
    def __init__(
        self,
        message: str,
        product_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            field_name="product",
            field_value=product_data,
            error_code=error_code or "INVALID_PRODUCT_DATA",
            suggestions=[
                "Проверьте обязательные поля: id, title, organic_components",
                "Убедитесь, что все CID имеют правильный формат",
                "Проверьте, что пропорции указаны корректно"
            ]
        )


class CompositeValidationError(ValidationError):
    """Исключение для составных ошибок валидации."""
    
    def __init__(
        self,
        message: str,
        errors: List[ValidationError],
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code or "COMPOSITE_VALIDATION_ERROR",
            suggestions=["Исправьте все указанные ошибки валидации"]
        )
        self.errors = errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует составное исключение в словарь."""
        base_dict = super().to_dict()
        base_dict["errors"] = [error.to_dict() for error in self.errors]
        return base_dict


class ValidationRuleError(ValidationError):
    """Исключение для ошибок в правилах валидации."""
    
    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            field_name="validation_rule",
            field_value=rule_name,
            error_code=error_code or "VALIDATION_RULE_ERROR",
            suggestions=[
                "Проверьте конфигурацию правила валидации",
                "Убедитесь, что правило правильно инициализировано"
            ]
        )


def create_validation_error_from_result(
    validation_result: ValidationResult,
    error_class: type[ValidationError] = ValidationError
) -> ValidationError:
    """
    Создает исключение валидации из результата валидации.
    
    Args:
        validation_result: Результат валидации
        error_class: Класс исключения для создания
        
    Returns:
        ValidationError: Созданное исключение
        
    Raises:
        ValueError: Если validation_result.is_valid=True
    """
    if validation_result.is_valid:
        raise ValueError("Нельзя создать исключение из успешного результата валидации")
    
    return error_class(
        message=validation_result.error_message or "Ошибка валидации",
        field_name=validation_result.field_name,
        field_value=validation_result.field_value,
        error_code=validation_result.error_code,
        suggestions=validation_result.suggestions,
        validation_result=validation_result
    )
