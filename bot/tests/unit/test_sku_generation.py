"""
Unit Tests: SKU Generation для WooCommerce Export

КОНЦЕПЦИЯ:
==========
- Только unit-тесты с моками (быстрые, изолированные)
- Тестирование логики генерации SKU без зависимостей от блокчейна
- Edge cases и error scenarios
- Проверка валидации входных данных
- Проверка формата SKU согласно архитектуре

Quality Gates:
- NO_FALSE_SUCCESSES: Tests fail when logic broken
- VALIDATE_REAL_FUNCTIONALITY: Check actual SKU format
- CORRECT_LOGIC: Valid assertions, not tautologies
- MINIMAL_MOCK_OVERUSE: Mock только данные (MockProduct, MockPriceInfo), тестируем реальные функции
"""

import pytest
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union

# Импорт тестируемых функций
from services.woocommerce.export import generate_product_sku, generate_variation_sku


# Mock classes для тестирования
@dataclass
class MockProduct:
    """Mock Product для тестов"""
    blockchain_id: Union[int, str]
    business_id: str = "test_product_001"
    status: int = 1
    cid: str = "test_cid"
    title: str = "Test Product"
    forms: list = None
    categories: list = None
    
    def __post_init__(self):
        if self.forms is None:
            self.forms = []
        if self.categories is None:
            self.categories = []


@dataclass
class MockPriceInfo:
    """Mock PriceInfo для тестов"""
    price: Union[int, float, str, Decimal]
    currency: str = "EUR"
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    form: Optional[str] = None
    
    @property
    def is_quantity_based(self) -> bool:
        """Проверяет, основана ли цена на количестве."""
        return self.quantity is not None and self.unit is not None


@pytest.mark.unit
class TestGenerateProductSku:
    """Unit тесты для generate_product_sku()"""
    
    # ============================================================
    # Tests for generate_product_sku() - Valid data
    # ============================================================
    
    def test_generate_product_sku_with_int_blockchain_id(self):
        """
        generate_product_sku() с int blockchain_id возвращает правильный SKU
        
        GIVEN: Product с blockchain_id=123 (int), form="dried"
        WHEN: generate_product_sku(product, "dried") вызывается
        THEN: Возвращается "123_dried"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        
        # Act
        result = generate_product_sku(product, "dried")
        
        # Assert
        assert result == "123_dried"
        assert isinstance(result, str)
    
    def test_generate_product_sku_with_str_blockchain_id(self):
        """
        generate_product_sku() с str blockchain_id возвращает правильный SKU
        
        GIVEN: Product с blockchain_id="456" (str), form="powder"
        WHEN: generate_product_sku(product, "powder") вызывается
        THEN: Возвращается "456_powder"
        """
        # Arrange
        product = MockProduct(blockchain_id="456")
        
        # Act
        result = generate_product_sku(product, "powder")
        
        # Assert
        assert result == "456_powder"
        assert isinstance(result, str)
    
    def test_generate_product_sku_with_zero_blockchain_id(self):
        """
        generate_product_sku() с blockchain_id=0 возвращает правильный SKU
        
        GIVEN: Product с blockchain_id=0 (int), form="dried"
        WHEN: generate_product_sku(product, "dried") вызывается
        THEN: Возвращается "0_dried" (0 валиден для int)
        """
        # Arrange
        product = MockProduct(blockchain_id=0)
        
        # Act
        result = generate_product_sku(product, "dried")
        
        # Assert
        assert result == "0_dried"
    
    def test_generate_product_sku_with_different_forms(self):
        """
        generate_product_sku() генерирует разные SKU для разных форм
        
        GIVEN: Product с blockchain_id=123, разные формы: "dried", "powder", "capsules"
        WHEN: generate_product_sku(product, form) вызывается для каждой формы
        THEN: Возвращаются разные SKU: "123_dried", "123_powder", "123_capsules"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        forms = ["dried", "powder", "capsules"]
        expected_skus = ["123_dried", "123_powder", "123_capsules"]
        
        # Act & Assert
        for form, expected_sku in zip(forms, expected_skus):
            result = generate_product_sku(product, form)
            assert result == expected_sku
    
    # ============================================================
    # Tests for generate_product_sku() - blockchain_id validation
    # ============================================================
    
    def test_generate_product_sku_with_none_blockchain_id(self):
        """
        generate_product_sku() выбрасывает ValueError для blockchain_id=None
        
        GIVEN: Product с blockchain_id=None
        WHEN: generate_product_sku(product, "dried") вызывается
        THEN: Выбрасывается ValueError с сообщением "blockchain_id не может быть None"
        """
        # Arrange
        product = MockProduct(blockchain_id=None)
        
        # Act & Assert
        with pytest.raises(ValueError, match="blockchain_id не может быть None"):
            generate_product_sku(product, "dried")
    
    def test_generate_product_sku_with_empty_str_blockchain_id(self):
        """
        generate_product_sku() выбрасывает ValueError для пустого blockchain_id
        
        GIVEN: Product с blockchain_id="" (пустая строка)
        WHEN: generate_product_sku(product, "dried") вызывается
        THEN: Выбрасывается ValueError с сообщением "blockchain_id не может быть пустой строкой"
        """
        # Arrange
        product = MockProduct(blockchain_id="")
        
        # Act & Assert
        with pytest.raises(ValueError, match="blockchain_id не может быть пустой строкой"):
            generate_product_sku(product, "dried")
    
    def test_generate_product_sku_with_whitespace_str_blockchain_id(self):
        """
        generate_product_sku() выбрасывает ValueError для blockchain_id из пробелов
        
        GIVEN: Product с blockchain_id="   " (только пробелы)
        WHEN: generate_product_sku(product, "dried") вызывается
        THEN: Выбрасывается ValueError с сообщением "blockchain_id не может быть пустой строкой"
        """
        # Arrange
        product = MockProduct(blockchain_id="   ")
        
        # Act & Assert
        with pytest.raises(ValueError, match="blockchain_id не может быть пустой строкой"):
            generate_product_sku(product, "dried")
    
    def test_generate_product_sku_with_negative_int_blockchain_id(self):
        """
        generate_product_sku() выбрасывает ValueError для отрицательного blockchain_id
        
        GIVEN: Product с blockchain_id=-1 (отрицательный int)
        WHEN: generate_product_sku(product, "dried") вызывается
        THEN: Выбрасывается ValueError с сообщением "blockchain_id не может быть отрицательным"
        """
        # Arrange
        product = MockProduct(blockchain_id=-1)
        
        # Act & Assert
        with pytest.raises(ValueError, match="blockchain_id не может быть отрицательным"):
            generate_product_sku(product, "dried")
    
    # ============================================================
    # Tests for generate_product_sku() - form validation
    # ============================================================
    
    def test_generate_product_sku_with_none_form(self):
        """
        generate_product_sku() выбрасывает ValueError для form=None
        
        GIVEN: Product с валидным blockchain_id=123, form=None
        WHEN: generate_product_sku(product, None) вызывается
        THEN: Выбрасывается ValueError с сообщением "form не может быть None или пустым"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        
        # Act & Assert
        with pytest.raises(ValueError, match="form не может быть None или пустым"):
            generate_product_sku(product, None)
    
    def test_generate_product_sku_with_empty_form(self):
        """
        generate_product_sku() выбрасывает ValueError для пустого form
        
        GIVEN: Product с валидным blockchain_id=123, form=""
        WHEN: generate_product_sku(product, "") вызывается
        THEN: Выбрасывается ValueError с сообщением "form не может быть None или пустым"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        
        # Act & Assert
        with pytest.raises(ValueError, match="form не может быть None или пустым"):
            generate_product_sku(product, "")
    
    def test_generate_product_sku_with_whitespace_form(self):
        """
        generate_product_sku() выбрасывает ValueError для form из пробелов
        
        GIVEN: Product с валидным blockchain_id=123, form="   " (только пробелы)
        WHEN: generate_product_sku(product, "   ") вызывается
        THEN: Выбрасывается ValueError с сообщением "form не может быть пустой строкой или состоять только из пробелов"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        
        # Act & Assert
        with pytest.raises(ValueError, match="form не может быть пустой строкой или состоять только из пробелов"):
            generate_product_sku(product, "   ")
    
    def test_generate_product_sku_with_non_str_form(self):
        """
        generate_product_sku() выбрасывает ValueError для form не-строки
        
        GIVEN: Product с валидным blockchain_id=123, form=123 (int вместо str)
        WHEN: generate_product_sku(product, 123) вызывается
        THEN: Выбрасывается ValueError с сообщением "form должен быть строкой"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        
        # Act & Assert
        with pytest.raises(ValueError, match="form должен быть строкой"):
            generate_product_sku(product, 123)
    
    # ============================================================
    # Tests for generate_product_sku() - Edge cases
    # ============================================================
    
    def test_generate_product_sku_format_consistency(self):
        """
        generate_product_sku() возвращает одинаковый результат для int и str blockchain_id
        
        GIVEN: Product с blockchain_id=123 (int) и blockchain_id="123" (str)
        WHEN: generate_product_sku(product, "dried") вызывается для обоих
        THEN: Оба возвращают одинаковый результат "123_dried"
        """
        # Arrange
        product_int = MockProduct(blockchain_id=123)
        product_str = MockProduct(blockchain_id="123")
        
        # Act
        result_int = generate_product_sku(product_int, "dried")
        result_str = generate_product_sku(product_str, "dried")
        
        # Assert
        assert result_int == result_str == "123_dried"
    
    def test_generate_product_sku_with_special_characters_in_form(self):
        """
        generate_product_sku() поддерживает спецсимволы в form
        
        GIVEN: Product с blockchain_id=123, form="dried-powder" (с дефисом)
        WHEN: generate_product_sku(product, "dried-powder") вызывается
        THEN: Возвращается "123_dried-powder" (спецсимволы допустимы в form)
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        
        # Act
        result = generate_product_sku(product, "dried-powder")
        
        # Assert
        assert result == "123_dried-powder"


@pytest.mark.unit
class TestGenerateVariationSku:
    """Unit тесты для generate_variation_sku()"""
    
    # ============================================================
    # Tests for generate_variation_sku() - Weight-based products
    # ============================================================
    
    def test_generate_variation_sku_with_weight_based_price(self):
        """
        generate_variation_sku() генерирует правильный SKU для весового продукта
        
        GIVEN: Product с blockchain_id=123, form="dried", PriceInfo с quantity=Decimal("100"), unit="g", currency="EUR"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Возвращается "123_dried_100g_EUR"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result == "123_dried_100g_EUR"
        assert isinstance(result, str)
    
    def test_generate_variation_sku_with_different_weight_units(self):
        """
        generate_variation_sku() поддерживает разные единицы веса
        
        GIVEN: Product с blockchain_id=123, разные единицы: "g", "kg", "oz"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается для каждой единицы
        THEN: Возвращаются SKU: "123_dried_100g_EUR", "123_dried_1kg_EUR", "123_dried_28oz_EUR"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        test_cases = [
            (Decimal("100"), "g", "123_dried_100g_EUR"),
            (Decimal("1"), "kg", "123_dried_1kg_EUR"),
            (Decimal("28"), "oz", "123_dried_28oz_EUR"),
        ]
        
        # Act & Assert
        for quantity, unit, expected_sku in test_cases:
            price_info = MockPriceInfo(
                price=60,
                currency="EUR",
                quantity=quantity,
                unit=unit
            )
            result = generate_variation_sku(product, "dried", price_info)
            assert result == expected_sku
    
    def test_generate_variation_sku_with_decimal_weight(self):
        """
        generate_variation_sku() конвертирует Decimal weight в int для SKU
        
        GIVEN: Product с blockchain_id=123, PriceInfo с quantity=Decimal("100.5"), unit="g"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Возвращается "123_dried_100g_EUR" (Decimal конвертируется в int, округление вниз)
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100.5"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result == "123_dried_100g_EUR"
        assert "100.5g" not in result  # Дробная часть не должна быть в SKU
    
    def test_generate_variation_sku_with_large_decimal_weight(self):
        """
        generate_variation_sku() корректно обрабатывает большие Decimal значения
        
        GIVEN: Product с blockchain_id=123, PriceInfo с quantity=Decimal("100.999"), unit="g"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Возвращается "123_dried_100g_EUR" (округление вниз)
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100.999"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result == "123_dried_100g_EUR"
        assert "100.999g" not in result
    
    # ============================================================
    # Tests for generate_variation_sku() - Volume-based products
    # ============================================================
    
    def test_generate_variation_sku_with_volume_based_price(self):
        """
        generate_variation_sku() генерирует правильный SKU для объемного продукта
        
        GIVEN: Product с blockchain_id=456, form="tincture", PriceInfo с quantity=Decimal("50"), unit="ml", currency="USD"
        WHEN: generate_variation_sku(product, "tincture", price_info) вызывается
        THEN: Возвращается "456_tincture_50ml_USD"
        """
        # Arrange
        product = MockProduct(blockchain_id=456)
        price_info = MockPriceInfo(
            price=20,
            currency="USD",
            quantity=Decimal("50"),
            unit="ml"
        )
        
        # Act
        result = generate_variation_sku(product, "tincture", price_info)
        
        # Assert
        assert result == "456_tincture_50ml_USD"
    
    def test_generate_variation_sku_with_different_volume_units(self):
        """
        generate_variation_sku() поддерживает разные единицы объема
        
        GIVEN: Product с blockchain_id=456, разные единицы: "ml", "l", "oz_fl"
        WHEN: generate_variation_sku(product, "tincture", price_info) вызывается для каждой единицы
        THEN: Возвращаются SKU: "456_tincture_50ml_USD", "456_tincture_1l_USD", "456_tincture_30oz_fl_USD"
        """
        # Arrange
        product = MockProduct(blockchain_id=456)
        test_cases = [
            (Decimal("50"), "ml", "456_tincture_50ml_USD"),
            (Decimal("1"), "l", "456_tincture_1l_USD"),
            (Decimal("30"), "oz_fl", "456_tincture_30oz_fl_USD"),
        ]
        
        # Act & Assert
        for quantity, unit, expected_sku in test_cases:
            price_info = MockPriceInfo(
                price=20,
                currency="USD",
                quantity=quantity,
                unit=unit
            )
            result = generate_variation_sku(product, "tincture", price_info)
            assert result == expected_sku
    
    def test_generate_variation_sku_with_decimal_volume(self):
        """
        generate_variation_sku() конвертирует Decimal volume в int для SKU
        
        GIVEN: Product с blockchain_id=456, PriceInfo с quantity=Decimal("50.7"), unit="ml"
        WHEN: generate_variation_sku(product, "tincture", price_info) вызывается
        THEN: Возвращается "456_tincture_50ml_USD" (Decimal конвертируется в int, округление вниз)
        """
        # Arrange
        product = MockProduct(blockchain_id=456)
        price_info = MockPriceInfo(
            price=20,
            currency="USD",
            quantity=Decimal("50.7"),
            unit="ml"
        )
        
        # Act
        result = generate_variation_sku(product, "tincture", price_info)
        
        # Assert
        assert result == "456_tincture_50ml_USD"
        assert "50.7ml" not in result
    
    # ============================================================
    # Tests for generate_variation_sku() - Simple prices (should raise ValueError)
    # ============================================================
    
    def test_generate_variation_sku_with_simple_price_no_weight_no_volume(self):
        """
        generate_variation_sku() выбрасывает ValueError для простой цены без quantity
        
        GIVEN: Product с blockchain_id=123, form="dried", PriceInfo без quantity (простая цена)
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Выбрасывается ValueError с сообщением содержащим "не имеет quantity"
        """
        # Arrange
        product = MockProduct(blockchain_id=123, business_id="test_product_001")
        price_info = MockPriceInfo(
            price=60,
            currency="EUR"
            # Нет quantity
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="не имеет quantity"):
            generate_variation_sku(product, "dried", price_info)
    
    def test_generate_variation_sku_error_message_includes_business_id(self):
        """
        generate_variation_sku() включает business_id и form в сообщение об ошибке
        
        GIVEN: Product с business_id="test_product_001", PriceInfo без quantity
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Сообщение об ошибке содержит "test_product_001" и "форма: dried"
        """
        # Arrange
        product = MockProduct(blockchain_id=123, business_id="test_product_001")
        price_info = MockPriceInfo(
            price=60,
            currency="EUR"
            # Нет quantity
        )
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            generate_variation_sku(product, "dried", price_info)
        
        error_message = str(exc_info.value)
        assert "test_product_001" in error_message
        assert "форма: dried" in error_message or "dried" in error_message
    
    # ============================================================
    # Tests for generate_variation_sku() - Different currencies
    # ============================================================
    
    def test_generate_variation_sku_with_eur_currency(self):
        """
        generate_variation_sku() включает валюту EUR в SKU
        
        GIVEN: Product с blockchain_id=123, PriceInfo с currency="EUR"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: SKU заканчивается на "_EUR"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result.endswith("_EUR")
        assert result == "123_dried_100g_EUR"
    
    def test_generate_variation_sku_with_usd_currency(self):
        """
        generate_variation_sku() включает валюту USD в SKU
        
        GIVEN: Product с blockchain_id=123, PriceInfo с currency="USD"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: SKU заканчивается на "_USD"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=70,
            currency="USD",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result.endswith("_USD")
        assert result == "123_dried_100g_USD"
    
    def test_generate_variation_sku_with_rub_currency(self):
        """
        generate_variation_sku() включает валюту RUB в SKU
        
        GIVEN: Product с blockchain_id=123, PriceInfo с currency="RUB"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: SKU заканчивается на "_RUB"
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=5000,
            currency="RUB",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result.endswith("_RUB")
        assert result == "123_dried_100g_RUB"
    
    def test_generate_variation_sku_currency_always_included(self):
        """
        generate_variation_sku() всегда включает валюту в SKU
        
        GIVEN: Product с blockchain_id=123, PriceInfo с разными валютами: "EUR", "USD", "RUB", "GBP"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается для каждой валюты
        THEN: Все SKU заканчиваются на соответствующую валюту (валюта всегда включается)
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        currencies = ["EUR", "USD", "RUB", "GBP"]
        
        # Act & Assert
        for currency in currencies:
            price_info = MockPriceInfo(
                price=60,
                currency=currency,
                weight=Decimal("100"),
                weight_unit="g"
            )
            result = generate_variation_sku(product, "dried", price_info)
            assert result.endswith(f"_{currency}")
            assert currency in result
    
    # ============================================================
    # Tests for generate_variation_sku() - Integration and edge cases
    # ============================================================
    
    def test_generate_variation_sku_uses_base_sku_from_generate_product_sku(self):
        """
        generate_variation_sku() использует базовый SKU из generate_product_sku()
        
        GIVEN: Product с blockchain_id=123, form="dried", PriceInfo с quantity=Decimal("100"), unit="g"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: SKU начинается с "123_dried_" (базовый SKU из generate_product_sku())
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result.startswith("123_dried_")
        base_sku = generate_product_sku(product, "dried")
        assert result.startswith(base_sku + "_")
    
    def test_generate_variation_sku_propagates_validation_errors_from_generate_product_sku(self):
        """
        generate_variation_sku() распространяет ошибки валидации из generate_product_sku()
        
        GIVEN: Product с blockchain_id=None, PriceInfo с валидными quantity и unit
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Выбрасывается ValueError из generate_product_sku() (ошибка валидации blockchain_id)
        """
        # Arrange
        product = MockProduct(blockchain_id=None)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="blockchain_id не может быть None"):
            generate_variation_sku(product, "dried", price_info)
    
    def test_generate_variation_sku_format_consistency_int_vs_str_blockchain_id(self):
        """
        generate_variation_sku() возвращает одинаковый результат для int и str blockchain_id
        
        GIVEN: Product с blockchain_id=123 (int) и blockchain_id="123" (str), одинаковые PriceInfo
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается для обоих
        THEN: Оба возвращают одинаковый результат "123_dried_100g_EUR"
        """
        # Arrange
        product_int = MockProduct(blockchain_id=123)
        product_str = MockProduct(blockchain_id="123")
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("100"),
            unit="g"
        )
        
        # Act
        result_int = generate_variation_sku(product_int, "dried", price_info)
        result_str = generate_variation_sku(product_str, "dried", price_info)
        
        # Assert
        assert result_int == result_str == "123_dried_100g_EUR"
    
    def test_generate_variation_sku_with_zero_weight(self):
        """
        generate_variation_sku() обрабатывает quantity=0 корректно
        
        GIVEN: Product с blockchain_id=123, PriceInfo с quantity=Decimal("0"), unit="g"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Возвращается "123_dried_0g_EUR" (0 валиден для quantity, но не должен встречаться в реальных данных)
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("0"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result == "123_dried_0g_EUR"
    
    def test_generate_variation_sku_with_very_large_weight(self):
        """
        generate_variation_sku() обрабатывает большие значения quantity корректно
        
        GIVEN: Product с blockchain_id=123, PriceInfo с quantity=Decimal("10000"), unit="g"
        WHEN: generate_variation_sku(product, "dried", price_info) вызывается
        THEN: Возвращается "123_dried_10000g_EUR" (большие значения обрабатываются корректно)
        """
        # Arrange
        product = MockProduct(blockchain_id=123)
        price_info = MockPriceInfo(
            price=60,
            currency="EUR",
            quantity=Decimal("10000"),
            unit="g"
        )
        
        # Act
        result = generate_variation_sku(product, "dried", price_info)
        
        # Assert
        assert result == "123_dried_10000g_EUR"

