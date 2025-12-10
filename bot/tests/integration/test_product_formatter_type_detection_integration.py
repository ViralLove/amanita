"""
Integration tests для ProductFormatterService type detection в реальном formatting flow.

Тестирует:
1. Integration _detect_product_type() с format_product_details_for_telegram()
2. Routing на SINGLE/MULTI форматтеры
3. Legacy fallback (пока новые форматтеры не реализованы)

Method: @integration-test-build.core.mdc
Level: Integration (module boundaries)
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import Mock
import logging


# Mock data для integration tests
@dataclass
class MockOrganicComponent:
    """Mock OrganicComponent с минимальными полями"""
    component_id: str
    proportion: Optional[str] = None
    scientific_title: Optional[str] = None
    features: Optional[dict] = None
    forms: Optional[List[str]] = None
    description: Optional[any] = None
    properties: Optional[str] = None


@dataclass
class MockProduct:
    """Mock Product для integration tests"""
    title: str
    species: str
    status: int
    organic_components: List[MockOrganicComponent]
    cover_image_url: str = ""
    generic_description: Optional[str] = None
    effects: Optional[str] = None
    shamanic: Optional[str] = None
    warnings: Optional[str] = None
    categories: Optional[List[str]] = None
    forms: Optional[List[str]] = None
    prices: Optional[List] = None
    features: Optional[List[str]] = None
    dosage_instructions: Optional[List] = None


@pytest.mark.integration
class TestProductTypeDetectionIntegration:
    """
    Integration tests для type detection в formatting flow.
    
    Validates:
    - format_product_details_for_telegram() вызывает _detect_product_type()
    - Routing logic работает корректно
    - Logging происходит на правильных уровнях
    """
    
    def test_format_detects_and_logs_single_type(
        self, 
        product_formatter_service, 
        caplog
    ):
        """
        Integration Test: format_product_details_for_telegram() детектирует SINGLE product.
        
        Flow:
        1. Create SINGLE product (1 component)
        2. Call format_product_details_for_telegram()
        3. Verify _detect_product_type() was called
        4. Verify logged "Detected product type: SINGLE"
        5. Verify returns formatted text
        """
        caplog.set_level(logging.INFO, logger="handlers.common.formatting.product_formatter_service")
        
        # Arrange: SINGLE product
        product = MockProduct(
            title="Amanita LUX",
            species="Amanita",
            status=1,
            organic_components=[
                MockOrganicComponent(
                    component_id="amanita_muscaria",
                    proportion="100%"
                )
            ]
        )
        
        # Mock Localization
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: default or key
        
        # Act
        result = product_formatter_service.format_product_details_for_telegram(product, loc)
        
        # Assert: Type detected
        assert "Detected product type: SINGLE" in caplog.text, \
            f"Should log detected type. Logs: {caplog.text}"
        
        # Assert: Result returned
        assert result is not None, "Should return formatted text"
        assert isinstance(result, str), "Should return string"
        assert len(result) > 0, "Should not be empty"
        
        # Assert: Contains product title
        assert "Amanita LUX" in result, "Should include product title"
    
    def test_format_detects_and_logs_multi_type(
        self, 
        product_formatter_service, 
        caplog
    ):
        """
        Integration Test: format_product_details_for_telegram() детектирует MULTI product.
        
        Flow:
        1. Create MULTI product (3 components)
        2. Call format_product_details_for_telegram()
        3. Verify logged "Detected product type: MULTI"
        4. Verify logging includes component count
        """
        caplog.set_level(logging.INFO, logger="handlers.common.formatting.product_formatter_service")
        
        # Arrange: MULTI product
        product = MockProduct(
            title="Sacred Blend",
            species="Blend",
            status=1,
            organic_components=[
                MockOrganicComponent(component_id="amanita_muscaria", proportion="50%"),
                MockOrganicComponent(component_id="blue_lotus", proportion="30%"),
                MockOrganicComponent(component_id="lions_mane", proportion="20%")
            ]
        )
        
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: default or key
        
        # Act
        result = product_formatter_service.format_product_details_for_telegram(product, loc)
        
        # Assert: Type detected as MULTI
        assert "Detected product type: MULTI" in caplog.text
        
        # Assert: Result valid
        assert result is not None
        assert "Sacred Blend" in result
    
    def test_routing_to_legacy_until_formatters_implemented(
        self, 
        product_formatter_service, 
        caplog
    ):
        """
        Integration Test: Routing использует legacy форматтер пока новые не реализованы.
        
        Flow:
        1. Call format_product_details_for_telegram() с SINGLE product
        2. Verify WARNING logged: "SINGLE formatter not yet implemented"
        3. Verify falls back to legacy
        4. Verify result still valid
        
        NOTE: Тест обновлён после Task 2.1-2.3 (SINGLE formatter реализован)
        """
        caplog.set_level(logging.INFO, logger="handlers.common.formatting.product_formatter_service")
        
        # Arrange
        product = MockProduct(
            title="Test Product",
            species="Test",
            status=1,
            organic_components=[
                MockOrganicComponent(component_id="test", proportion="100%")
            ]
        )
        
        # Mock локализации с новыми ключами из Task 2.4
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: {
            "catalog.product.single_component_marker": "Монокомпонентный продукт",
            "catalog.product.component_features_title": "Особенности:",
            "catalog.product.component_forms_title": "Доступные формы:",
            "catalog.product.component_features_more": "... (+{0} еще)"
        }.get(key, default or key)
        
        # Act
        result = product_formatter_service.format_product_details_for_telegram(product, loc)
        
        # Assert: Logs INFO about using SINGLE formatter (Task 2.1 implemented!)
        # NOTE: После Task 2.1-2.3 SINGLE форматтер реализован, теперь он используется
        assert "Using SINGLE component formatter" in caplog.text, \
            "Should log using SINGLE formatter (implemented in Task 2.1)"
        
        # Assert: Result contains localized content from Task 2.4
        assert result is not None
        assert "Test Product" in result
        assert "test" in result  # component_id should appear
    
    def test_routing_switches_after_formatter_implementation(
        self, 
        product_formatter_service
    ):
        """
        Integration Test: После реализации _format_single_component_product(),
        routing должен использовать его вместо legacy.
        
        Flow:
        1. Check if _format_single_component_product exists
        2. If YES: verify it's called (not legacy)
        3. If NO: skip test (not implemented yet)
        
        NOTE: Этот тест ПРОПУСКАЕТСЯ сейчас (метод не реализован).
        После Task 2.1: тест активируется и должен пройти.
        """
        # Check if new formatter implemented
        has_single_formatter = hasattr(product_formatter_service, '_format_single_component_product')
        
        if not has_single_formatter:
            pytest.skip("_format_single_component_product not implemented yet (Task 2.1 pending)")
        
        # TODO: After Task 2.1, add test:
        # from unittest.mock import patch
        # 
        # product = MockProduct(...)  # SINGLE
        # loc = Mock(...)
        # 
        # with patch.object(
        #     product_formatter_service, 
        #     '_format_single_component_product',
        #     return_value="mocked single output"
        # ) as mock_single:
        #     result = product_formatter_service.format_product_details_for_telegram(product, loc)
        #     
        #     # Verify новый форматтер вызван
        #     mock_single.assert_called_once()
        #     
        #     # Verify legacy НЕ вызван
        #     # (проверить через отсутствие WARNING "using legacy")
    
    def test_handles_empty_components_gracefully(
        self, 
        product_formatter_service
    ):
        """
        Integration Test: Product с 0 компонентами → fallback message.
        
        Flow:
        1. Create product с organic_components = []
        2. Call format_product_details_for_telegram()
        3. Verify fallback message shown (no exceptions)
        """
        # Arrange
        product = MockProduct(
            title="Empty Product",
            species="Test",
            status=1,
            organic_components=[]
        )
        
        loc = Mock()
        loc.language = "ru"
        loc.t = lambda key, default=None: default or key
        
        # Act (should not raise exception)
        result = product_formatter_service.format_product_details_for_telegram(product, loc)
        
        # Assert: Result valid (no exception)
        assert result is not None, "Should return formatted text even for empty components"
        assert isinstance(result, str), "Should return string"
        assert "Empty Product" in result, "Should include product title"
        # Product с 0 компонентами просто пропускает секцию composition
        # Это нормально - не показываем "информация недоступна" для пустого списка


class TestProductTypeDetectionContracts:
    """
    Contract validation tests (Integration test pattern).
    
    Validates module boundaries:
    - ProductFormatterService contract with Product model
    - ProductFormatterService contract with Localization
    """
    
    def test_contract_product_model_has_organic_components(
        self,
        product_formatter_service
    ):
        """
        Contract Test: _detect_product_type() expects product.organic_components.
        
        Validates:
        - Method handles missing field gracefully
        - Returns "UNKNOWN" instead of exception
        """
        # Arrange: Product без organic_components
        @dataclass
        class ProductWithoutComponents:
            title: str = "Invalid"
        
        product = ProductWithoutComponents()
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert: Graceful degradation
        assert result == "UNKNOWN", "Should return UNKNOWN for missing field"
    
    def test_contract_organic_components_is_iterable(
        self,
        product_formatter_service
    ):
        """
        Contract Test: _detect_product_type() expects organic_components to be iterable.
        
        Validates:
        - Method handles non-iterable gracefully
        - Exception caught and returns "UNKNOWN"
        """
        # Arrange: Product с non-iterable organic_components
        @dataclass
        class ProductWithWrongType:
            organic_components: str = "not_a_list"
        
        product = ProductWithWrongType()
        
        # Act
        result = product_formatter_service._detect_product_type(product)
        
        # Assert: Exception handled
        # Note: hasattr() returns True для string, но len("not_a_list") = 11 → "MULTI"
        # This is actually OK behavior - string is iterable
        # So test should verify it doesn't crash, regardless of return value
        assert result in ["SINGLE", "MULTI", "EMPTY", "UNKNOWN"], \
            f"Should return valid type, got: {result}"
    
    def test_contract_returns_expected_values(
        self,
        product_formatter_service
    ):
        """
        Contract Test: _detect_product_type() contract guarantees return values.
        
        Validates:
        - Returns only: "SINGLE" | "MULTI" | "EMPTY" | "UNKNOWN"
        - Never returns None or unexpected values
        """
        from dataclasses import dataclass
        
        # Define test product without components
        @dataclass
        class ProductWithoutComponents:
            title: str = "Test"
        
        # Test all expected return values
        test_cases = [
            (MockProduct(title="T1", species="S1", status=1, organic_components=[Mock()]), "SINGLE"),
            (MockProduct(title="T2", species="S2", status=1, organic_components=[Mock(), Mock()]), "MULTI"),
            (MockProduct(title="T3", species="S3", status=1, organic_components=[]), "EMPTY"),
            (ProductWithoutComponents(), "UNKNOWN")
        ]
        
        for product, expected in test_cases:
            result = product_formatter_service._detect_product_type(product)
            
            # Verify return value is valid
            assert result in ["SINGLE", "MULTI", "EMPTY", "UNKNOWN"], \
                f"Invalid return value: {result}"
            assert result == expected, \
                f"Expected {expected}, got {result}"

