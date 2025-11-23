"""
Unit tests для ProductFormatterService._detect_product_type()

Тестирует детекцию типа продукта (SINGLE/MULTI/EMPTY/UNKNOWN).

FIXED: Теперь тестируют РЕАЛЬНЫЙ ProductFormatterService (не копию).
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional, Any
import logging

# Mock classes для тестирования
@dataclass
class MockOrganicComponent:
    """Mock OrganicComponent для тестов"""
    component_id: str
    proportion: Optional[str] = None


@dataclass
class MockProduct:
    """Mock Product для тестов"""
    organic_components: List[MockOrganicComponent]


class TestProductTypeDetection:
    """Tests для _detect_product_type() method в РЕАЛЬНОМ ProductFormatterService"""
    
    def test_detect_single_component_product(self, product_formatter_service):
        """
        Test: Продукт с 1 компонентом → "SINGLE"
        
        Validates REAL ProductFormatterService._detect_product_type() method.
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id="amanita_muscaria", proportion="100%")
            ]
        )
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert
        assert result == "SINGLE", f"Expected 'SINGLE', got '{result}'"
    
    def test_detect_multi_component_product_two(self, product_formatter_service):
        """
        Test: Продукт с 2 компонентами → "MULTI"
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id="amanita_muscaria", proportion="50%"),
                MockOrganicComponent(component_id="blue_lotus", proportion="50%")
            ]
        )
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert
        assert result == "MULTI", f"Expected 'MULTI', got '{result}'"
    
    def test_detect_multi_component_product_many(self, product_formatter_service):
        """
        Test: Продукт с 5 компонентами → "MULTI"
        """
        # Arrange
        product = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id=f"component_{i}", proportion="20%")
                for i in range(5)
            ]
        )
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert
        assert result == "MULTI", f"Expected 'MULTI', got '{result}'"
    
    def test_detect_empty_components(self, product_formatter_service):
        """
        Test: Продукт с 0 компонентами → "EMPTY"
        """
        # Arrange
        product = MockProduct(organic_components=[])
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert
        assert result == "EMPTY", f"Expected 'EMPTY', got '{result}'"
    
    def test_detect_no_components_field(self, product_formatter_service):
        """
        Test: Продукт без поля organic_components → "UNKNOWN"
        """
        # Arrange
        @dataclass
        class ProductWithoutComponents:
            title: str = "Test"
        
        product = ProductWithoutComponents()
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert
        assert result == "UNKNOWN", f"Expected 'UNKNOWN', got '{result}'"
    
    def test_detect_handles_none_safely(self, product_formatter_service):
        """
        Test: Продукт с organic_components = None → не падает, returns "UNKNOWN"
        """
        # Arrange
        @dataclass
        class ProductWithNoneComponents:
            organic_components: Any = None
        
        product = ProductWithNoneComponents()
        
        # Act
        # Should not raise exception
        result = product_formatter_service._detect_product_type(product)
        
        # Assert
        # When organic_components is None, len() will fail
        # So it should catch exception and return "UNKNOWN"
        assert result == "UNKNOWN", f"Expected 'UNKNOWN' for None components, got '{result}'"
    
    def test_detect_logs_correctly(self, product_formatter_service, caplog):
        """
        Test: Метод логирует корректно для каждого типа
        
        Enhanced: Проверяет не только текст, но и log levels.
        """
        import logging
        
        # Set log level для правильного logger
        caplog.set_level(logging.DEBUG, logger="handlers.common.formatting.product_formatter_service")
        
        # Test SINGLE logging (DEBUG level)
        product_single = MockProduct(
            organic_components=[MockOrganicComponent(component_id="test")]
        )
        product_formatter_service._detect_product_type(product_single)
        
        # Verify log content (с префиксом [ProductFormatterService])
        assert "Product type: SINGLE" in caplog.text, f"SINGLE not in logs. Captured: {caplog.text}"
        
        # Verify log level is DEBUG
        single_records = [r for r in caplog.records if "Product type: SINGLE" in r.message]
        assert len(single_records) >= 1, f"Should log SINGLE. Records: {[r.message for r in caplog.records]}"
        assert single_records[0].levelname == "DEBUG", "SINGLE should log at DEBUG level"
        assert "1 component" in single_records[0].message, "Should include component count"
        
        caplog.clear()
        
        # Test MULTI logging (DEBUG level)
        product_multi = MockProduct(
            organic_components=[
                MockOrganicComponent(component_id="test1"),
                MockOrganicComponent(component_id="test2")
            ]
        )
        product_formatter_service._detect_product_type(product_multi)
        
        assert "Product type: MULTI" in caplog.text
        multi_records = [r for r in caplog.records if "MULTI" in r.message]
        assert len(multi_records) >= 1, "Should log MULTI"
        assert multi_records[0].levelname == "DEBUG", "MULTI should log at DEBUG level"
        assert "2 components" in multi_records[0].message, "Should include component count"
        
        caplog.clear()
        
        # Test EMPTY logging (DEBUG level)
        product_empty = MockProduct(organic_components=[])
        product_formatter_service._detect_product_type(product_empty)
        
        assert "Product type: EMPTY" in caplog.text
        empty_records = [r for r in caplog.records if "EMPTY" in r.message]
        assert len(empty_records) >= 1, "Should log EMPTY"
        assert empty_records[0].levelname == "DEBUG", "EMPTY should log at DEBUG level"
        
        caplog.clear()
        
        # Test UNKNOWN logging (WARNING level)
        @dataclass
        class ProductWithoutComponents:
            title: str = "Test"
        
        product_unknown = ProductWithoutComponents()
        product_formatter_service._detect_product_type(product_unknown)
        
        assert "Product без поля organic_components" in caplog.text
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_records) >= 1, "UNKNOWN should log WARNING"
        assert "без поля organic_components" in warning_records[0].message


# NOTE: Integration tests с Product model требуют blockchain connection
# Эти тесты будут добавлены в отдельный файл integration tests
# после реализации полных SINGLE/MULTI форматтеров

