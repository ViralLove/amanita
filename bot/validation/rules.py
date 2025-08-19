"""
Базовые классы для правил валидации.

Этот модуль содержит абстрактные классы и интерфейсы для создания
правил валидации, которые используются во всех слоях приложения.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Optional
from dataclasses import dataclass

# Тип для данных, которые нужно валидировать
T = TypeVar('T')

@dataclass
class ValidationResult:
    """
    Результат валидации с детальной информацией.
    
    Attributes:
        is_valid: True если валидация прошла успешно
        error_message: Сообщение об ошибке (если is_valid=False)
        field_name: Имя поля, которое вызвало ошибку
        field_value: Значение поля, которое вызвало ошибку
        error_code: Код ошибки для программной обработки
        suggestions: Предложения по исправлению ошибки
    """
    is_valid: bool
    error_message: Optional[str] = None
    field_name: Optional[str] = None
    field_value: Optional[Any] = None
    error_code: Optional[str] = None
    suggestions: Optional[list[str]] = None
    
    def __bool__(self) -> bool:
        """Возвращает True если валидация прошла успешно."""
        return self.is_valid
    
    @classmethod
    def success(cls) -> 'ValidationResult':
        """Создает успешный результат валидации."""
        return cls(is_valid=True)
    
    @classmethod
    def failure(
        cls, 
        error_message: str, 
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        error_code: Optional[str] = None,
        suggestions: Optional[list[str]] = None
    ) -> 'ValidationResult':
        """Создает неуспешный результат валидации."""
        return cls(
            is_valid=False,
            error_message=error_message,
            field_name=field_name,
            field_value=field_value,
            error_code=error_code,
            suggestions=suggestions or []
        )


class ValidationRule(ABC, Generic[T]):
    """
    Абстрактный базовый класс для всех правил валидации.
    
    Этот класс определяет интерфейс для всех правил валидации.
    Каждое правило должно реализовать метод validate().
    
    Пример использования:
        class CIDValidator(ValidationRule[str]):
            def validate(self, value: str) -> ValidationResult:
                if not value.startswith('Qm'):
                    return ValidationResult.failure(
                        "CID должен начинаться с 'Qm'",
                        field_name="cid",
                        field_value=value,
                        error_code="INVALID_CID_FORMAT"
                    )
                return ValidationResult.success()
    """
    
    @abstractmethod
    def validate(self, value: T) -> ValidationResult:
        """
        Валидирует переданное значение.
        
        Args:
            value: Значение для валидации
            
        Returns:
            ValidationResult: Результат валидации
            
        Raises:
            NotImplementedError: Если метод не реализован в подклассе
        """
        raise NotImplementedError("Метод validate() должен быть реализован в подклассе")
    
    def validate_field(self, value: T, field_name: str) -> ValidationResult:
        """
        Валидирует поле с указанным именем.
        
        Args:
            value: Значение для валидации
            field_name: Имя поля
            
        Returns:
            ValidationResult: Результат валидации с именем поля
        """
        result = self.validate(value)
        if not result.is_valid and result.field_name is None:
            result.field_name = field_name
        return result


class CompositeValidationRule(ValidationRule[T]):
    """
    Составное правило валидации, объединяющее несколько правил.
    
    Это правило применяет несколько валидаторов последовательно
    и возвращает первую найденную ошибку или успешный результат.
    
    Пример использования:
        composite_rule = CompositeValidationRule([
            CIDValidator(),
            LengthValidator(min_length=10)
        ])
        result = composite_rule.validate("Qm123456789")
    """
    
    def __init__(self, rules: list[ValidationRule[T]]):
        """
        Инициализирует составное правило валидации.
        
        Args:
            rules: Список правил валидации для применения
        """
        self.rules = rules
    
    def validate(self, value: T) -> ValidationResult:
        """
        Применяет все правила валидации последовательно.
        
        Args:
            value: Значение для валидации
            
        Returns:
            ValidationResult: Первая найденная ошибка или успешный результат
        """
        for rule in self.rules:
            result = rule.validate(value)
            if not result.is_valid:
                return result
        return ValidationResult.success()
    
    def add_rule(self, rule: ValidationRule[T]) -> None:
        """
        Добавляет новое правило валидации.
        
        Args:
            rule: Правило валидации для добавления
        """
        self.rules.append(rule)
    
    def remove_rule(self, rule: ValidationRule[T]) -> None:
        """
        Удаляет правило валидации.
        
        Args:
            rule: Правило валидации для удаления
        """
        if rule in self.rules:
            self.rules.remove(rule)
