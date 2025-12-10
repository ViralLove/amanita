"""
Test Data Validator для валидации тестовых данных продуктов.

Проверяет соответствие тестовых данных актуальной схеме:
- Наличие обязательных полей
- Отсутствие legacy полей
- Корректность типов данных

Использование:
    from tests.fixtures.test_data_validator import TestDataValidator
    from tests.fixtures.test_data_factory import TestDataFactory
    
    # Валидация валидного продукта
    product = TestDataFactory.create_valid_product()
    result = TestDataValidator.validate_product_data(product)
    assert result.is_valid
    
    # Валидация невалидного продукта
    invalid_product = TestDataFactory.create_invalid_product("forms")
    result = TestDataValidator.validate_product_data(invalid_product)
    assert not result.is_valid
    assert result.error_code == "MISSING_REQUIRED_FIELD"
"""

from typing import Dict, Any, List, Optional
from validation.rules import ValidationResult
from tests.fixtures.test_data_factory import TestDataFactory


class TestDataValidator:
    """
    Валидатор тестовых данных для продуктов.
    
    Обеспечивает:
    - Проверку соответствия схеме валидатора
    - Обнаружение legacy полей
    - Валидацию типов данных
    - Рекурсивную проверку компонентов
    """
    
    # Обязательные поля (синхронизированы с TestDataFactory)
    REQUIRED_FIELDS = TestDataFactory.REQUIRED_FIELDS
    
    # Legacy поля на уровне продукта
    LEGACY_PRODUCT_FIELDS = [
        'form',  # Единственное число (legacy, должно быть forms)
        'component_id'  # На уровне продукта (legacy, должно быть в organic_components)
    ]
    
    # Legacy поля в компонентах
    LEGACY_COMPONENT_FIELDS = [
        'description_cid'  # В компонентах (legacy, удалено в Этапе 5)
    ]
    
    # Поля, которые должны быть массивами
    ARRAY_FIELDS = ['forms', 'organic_components']
    
    @staticmethod
    def validate_product_data(data: Dict[str, Any]) -> ValidationResult:
        """
        Валидирует тестовые данные продукта против актуальной схемы.
        
        Проверяет:
        1. Наличие всех обязательных полей
        2. Отсутствие legacy полей (на уровне продукта и в компонентах)
        3. Корректность типов данных (массивы)
        
        Args:
            data: Словарь с данными продукта для валидации
        
        Returns:
            ValidationResult: Результат валидации с деталями ошибок
        
        Example:
            >>> product = TestDataFactory.create_valid_product()
            >>> result = TestDataValidator.validate_product_data(product)
            >>> assert result.is_valid
        """
        # Проверка 1: Обязательные поля
        missing_fields = TestDataValidator._check_required_fields(data)
        if missing_fields:
            field = missing_fields[0]  # Первое отсутствующее поле
            return ValidationResult.failure(
                f"Отсутствует обязательное поле: {field}",
                field_name=field,
                field_value=None,
                error_code="MISSING_REQUIRED_FIELD",
                suggestions=[f"Добавьте поле '{field}' в продукт"]
            )
        
        # Проверка 2: Legacy поля на уровне продукта
        legacy_product_fields = TestDataValidator._check_legacy_product_fields(data)
        if legacy_product_fields:
            field = legacy_product_fields[0]  # Первое найденное legacy поле
            return ValidationResult.failure(
                f"Обнаружено legacy поле: {field}. Это поле устарело и не должно использоваться.",
                field_name=field,
                field_value=data.get(field),
                error_code="LEGACY_FIELD_DETECTED",
                suggestions=[
                    f"Удалите поле '{field}' из продукта",
                    TestDataValidator._get_legacy_field_suggestion(field)
                ]
            )
        
        # Проверка 3: Типы данных (массивы)
        type_errors = TestDataValidator._check_field_types(data)
        if type_errors:
            field, expected_type, actual_type = type_errors[0]  # Первая ошибка типа
            return ValidationResult.failure(
                f"Неверный тип поля '{field}': ожидается {expected_type}, получен {actual_type}",
                field_name=field,
                field_value=data.get(field),
                error_code="INVALID_FIELD_TYPE",
                suggestions=[f"Измените тип поля '{field}' на {expected_type}"]
            )
        
        # Проверка 4: Legacy поля в компонентах
        legacy_component_errors = TestDataValidator._check_legacy_component_fields(data)
        if legacy_component_errors:
            component_index, field = legacy_component_errors[0]  # Первая ошибка
            return ValidationResult.failure(
                f"Обнаружено legacy поле '{field}' в компоненте #{component_index + 1}",
                field_name=f"organic_components[{component_index}].{field}",
                field_value=data.get('organic_components', [])[component_index].get(field),
                error_code="LEGACY_FIELD_DETECTED",
                suggestions=[
                    f"Удалите поле '{field}' из компонента #{component_index + 1}",
                    "Legacy поле description_cid больше не используется в компонентах"
                ]
            )
        
        # Все проверки пройдены
        return ValidationResult.success()
    
    @staticmethod
    def _check_required_fields(data: Dict[str, Any]) -> List[str]:
        """
        Проверяет наличие обязательных полей.
        
        Args:
            data: Данные продукта
        
        Returns:
            List[str]: Список отсутствующих обязательных полей
        """
        missing = []
        for field in TestDataValidator.REQUIRED_FIELDS:
            if field not in data:
                missing.append(field)
        return missing
    
    @staticmethod
    def _check_legacy_product_fields(data: Dict[str, Any]) -> List[str]:
        """
        Проверяет отсутствие legacy полей на уровне продукта.
        
        Args:
            data: Данные продукта
        
        Returns:
            List[str]: Список найденных legacy полей
        """
        found = []
        for field in TestDataValidator.LEGACY_PRODUCT_FIELDS:
            if field in data:
                found.append(field)
        return found
    
    @staticmethod
    def _check_legacy_component_fields(data: Dict[str, Any]) -> List[tuple[int, str]]:
        """
        Проверяет отсутствие legacy полей в компонентах.
        
        Args:
            data: Данные продукта
        
        Returns:
            List[tuple[int, str]]: Список (индекс_компонента, legacy_поле) для найденных legacy полей
        """
        found = []
        organic_components = data.get('organic_components', [])
        
        if not isinstance(organic_components, list):
            return found  # Тип уже проверен в _check_field_types
        
        for index, component in enumerate(organic_components):
            if not isinstance(component, dict):
                continue  # Пропускаем некорректные компоненты
            
            for legacy_field in TestDataValidator.LEGACY_COMPONENT_FIELDS:
                if legacy_field in component:
                    found.append((index, legacy_field))
        
        return found
    
    @staticmethod
    def _check_field_types(data: Dict[str, Any]) -> List[tuple[str, str, str]]:
        """
        Проверяет типы данных для полей, которые должны быть массивами.
        
        Args:
            data: Данные продукта
        
        Returns:
            List[tuple[str, str, str]]: Список (поле, ожидаемый_тип, фактический_тип) для ошибок
        """
        errors = []
        
        for field in TestDataValidator.ARRAY_FIELDS:
            if field not in data:
                continue  # Отсутствие поля уже проверено в _check_required_fields
            
            value = data[field]
            if not isinstance(value, list):
                errors.append((field, 'list', type(value).__name__))
        
        return errors
    
    @staticmethod
    def _get_legacy_field_suggestion(field: str) -> str:
        """
        Возвращает предложение по замене legacy поля.
        
        Args:
            field: Название legacy поля
        
        Returns:
            str: Предложение по замене
        """
        suggestions = {
            'form': 'Используйте поле "forms" (массив) вместо "form"',
            'component_id': 'Используйте массив "organic_components" с полем "component_id" внутри каждого элемента',
            'description_cid': 'Поле description_cid больше не используется в компонентах'
        }
        return suggestions.get(field, f'Удалите поле "{field}" из продукта')

