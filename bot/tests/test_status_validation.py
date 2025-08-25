#!/usr/bin/env python3
"""
Тесты для валидации статуса продукта
"""

import pytest
from bot.api.models.product import ProductStatusUpdate
from pydantic import ValidationError

def test_valid_statuses():
    """Тест валидных статусов"""
    # Статус 1 (активен)
    status = ProductStatusUpdate(status=1)
    assert status.status == 1
    
    # Статус 0 (неактивен)
    status = ProductStatusUpdate(status=0)
    assert status.status == 0

def test_invalid_statuses():
    """Тест невалидных статусов"""
    # Статус 2 (недопустим)
    with pytest.raises(ValidationError):
        ProductStatusUpdate(status=2)
    
    # Статус -1 (недопустим)
    with pytest.raises(ValidationError):
        ProductStatusUpdate(status=-1)
    
    # Статус "active" (недопустим)
    with pytest.raises(ValidationError):
        ProductStatusUpdate(status="active")
    
    # Статус None (недопустим)
    with pytest.raises(ValidationError):
        ProductStatusUpdate(status=None)

def test_status_validation_constraints():
    """Тест ограничений валидации статуса"""
    # Проверяем, что ge=0 и le=1 работают корректно
    # Граничные значения должны быть приняты
    status = ProductStatusUpdate(status=0)  # Минимальное значение
    assert status.status == 0
    
    status = ProductStatusUpdate(status=1)  # Максимальное значение
    assert status.status == 1

def test_status_description():
    """Тест описания поля статуса"""
    # Проверяем, что описание поля корректно
    field_info = ProductStatusUpdate.model_fields['status']
    assert "Статус продукта (0 - неактивен, 1 - активен)" in field_info.description

def test_status_json_schema():
    """Тест JSON схемы для статуса"""
    # Проверяем, что JSON схема генерируется корректно
    schema = ProductStatusUpdate.model_json_schema()
    assert 'status' in schema['properties']
    assert schema['properties']['status']['type'] == 'integer'
    assert schema['properties']['status']['minimum'] == 0
    assert schema['properties']['status']['maximum'] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
