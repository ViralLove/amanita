"""
Тесты для валидаторов системы валидации.

Этот модуль содержит тесты для всех валидаторов:
- CIDValidator
- ProportionValidator
- PriceValidator
- ProductValidator
"""

import pytest
from decimal import Decimal

from bot.validation import (
    CIDValidator,
    ProportionValidator,
    PriceValidator,
    ProductValidator,
    ValidationResult
)


class TestCIDValidator:
    """Тесты для CIDValidator."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.validator = CIDValidator()
        self.validator_custom_length = CIDValidator(min_length=10)
    
    def test_valid_cid(self):
        """Тест валидного CID."""
        valid_cids = [
            "Qm123456789",
            "Qmabcdef123",
            "QmABCDEF456",
            "Qm123456789abcdef"
        ]
        
        for cid in valid_cids:
            result = self.validator.validate(cid)
            assert result.is_valid, f"CID {cid} должен быть валидным"
            assert result.error_message is None
    
    def test_invalid_cid_empty(self):
        """Тест пустого CID."""
        result = self.validator.validate("")
        assert not result.is_valid
        assert result.error_code == "EMPTY_CID"
        assert "пустым" in result.error_message
    
    def test_invalid_cid_none(self):
        """Тест None CID."""
        result = self.validator.validate(None)
        assert not result.is_valid
        assert result.error_code == "EMPTY_CID"
        assert "пустым" in result.error_message
    
    def test_invalid_cid_wrong_type(self):
        """Тест CID неправильного типа."""
        result = self.validator.validate(123)
        assert not result.is_valid
        assert result.error_code == "INVALID_CID_TYPE"
    
    def test_invalid_cid_too_short(self):
        """Тест слишком короткого CID."""
        result = self.validator.validate("Qm")
        assert not result.is_valid
        assert result.error_code == "CID_TOO_SHORT"
        assert "не менее 3 символов" in result.error_message
    
    def test_invalid_cid_custom_length(self):
        """Тест CID с кастомной минимальной длиной."""
        result = self.validator_custom_length.validate("Qm123")
        assert not result.is_valid
        assert result.error_code == "CID_TOO_SHORT"
        assert "не менее 10 символов" in result.error_message
    
    def test_invalid_cid_wrong_prefix(self):
        """Тест CID с неправильным префиксом."""
        invalid_cids = [
            "qm123456789",
            "QM123456789",
            "123456789",
            "abc123456789"
        ]
        
        for cid in invalid_cids:
            result = self.validator.validate(cid)
            assert not result.is_valid, f"CID {cid} должен быть невалидным"
            assert result.error_code == "INVALID_CID_PREFIX"
            assert "начинаться с 'Qm'" in result.error_message
    
    def test_invalid_cid_special_characters(self):
        """Тест CID со специальными символами."""
        invalid_cids = [
            "Qm123-456",
            "Qm123_456",
            "Qm123.456",
            "Qm123@456"
        ]
        
        for cid in invalid_cids:
            result = self.validator.validate(cid)
            assert not result.is_valid, f"CID {cid} должен быть невалидным"
            assert result.error_code == "INVALID_CID_CHARACTERS"
            assert "недопустимые символы" in result.error_message


class TestProportionValidator:
    """Тесты для ProportionValidator."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.validator = ProportionValidator()
    
    def test_valid_percentage(self):
        """Тест валидных процентов."""
        valid_percentages = ["1%", "50%", "100%", "99%"]
        
        for percentage in valid_percentages:
            result = self.validator.validate(percentage)
            assert result.is_valid, f"Процент {percentage} должен быть валидным"
    
    def test_invalid_percentage_range(self):
        """Тест невалидных процентов."""
        invalid_percentages = ["0%", "101%", "200%"]
        
        for percentage in invalid_percentages:
            result = self.validator.validate(percentage)
            assert not result.is_valid, f"Процент {percentage} должен быть невалидным"
            assert result.error_code == "INVALID_PERCENTAGE_RANGE"
    
    def test_valid_weight(self):
        """Тест валидного веса."""
        valid_weights = ["1g", "50.5g", "1kg", "2.5kg", "1oz", "2lb"]
        
        for weight in valid_weights:
            result = self.validator.validate(weight)
            assert result.is_valid, f"Вес {weight} должен быть валидным"
    
    def test_invalid_weight_value(self):
        """Тест невалидного веса."""
        invalid_weights = ["0g", "-1g", "0kg"]
        
        for weight in invalid_weights:
            result = self.validator.validate(weight)
            assert not result.is_valid, f"Вес {weight} должен быть невалидным"
            assert result.error_code == "INVALID_WEIGHT_VALUE"
    
    def test_valid_volume(self):
        """Тест валидного объема."""
        valid_volumes = ["1ml", "50.5ml", "1l", "2.5l", "1oz_fl"]
        
        for volume in valid_volumes:
            result = self.validator.validate(volume)
            assert result.is_valid, f"Объем {volume} должен быть валидным"
    
    def test_invalid_volume_value(self):
        """Тест невалидного объема."""
        invalid_volumes = ["0ml", "-1ml", "0l"]
        
        for volume in invalid_volumes:
            result = self.validator.validate(volume)
            assert not result.is_valid, f"Объем {volume} должен быть невалидным"
            assert result.error_code == "INVALID_VOLUME_VALUE"
    
    def test_invalid_proportion_format(self):
        """Тест невалидного формата пропорции."""
        invalid_formats = [
            "100",  # без единиц измерения
            "50",   # без единиц измерения
            "1m",   # неподдерживаемая единица
            "1cm",  # неподдерживаемая единица
            "abc",  # нечисловое значение
            "1%2",  # неправильный формат
        ]
        
        for format_str in invalid_formats:
            result = self.validator.validate(format_str)
            assert not result.is_valid, f"Формат {format_str} должен быть невалидным"
            assert result.error_code == "INVALID_PROPORTION_FORMAT"
    
    def test_empty_proportion(self):
        """Тест пустой пропорции."""
        result = self.validator.validate("")
        assert not result.is_valid
        assert result.error_code == "EMPTY_PROPORTION"
    
    def test_invalid_proportion_type(self):
        """Тест пропорции неправильного типа."""
        result = self.validator.validate(123)
        assert not result.is_valid
        assert result.error_code == "INVALID_PROPORTION_TYPE"


class TestPriceValidator:
    """Тесты для PriceValidator."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.validator = PriceValidator()
        self.validator_min_price = PriceValidator(min_price=10)
    
    def test_valid_price(self):
        """Тест валидных цен."""
        valid_prices = [1, 10.5, "100", Decimal("50.25")]
        
        for price in valid_prices:
            result = self.validator.validate(price)
            assert result.is_valid, f"Цена {price} должна быть валидной"
    
    def test_invalid_price_too_low(self):
        """Тест слишком низкой цены."""
        invalid_prices = [0, -1, -10.5]
        
        for price in invalid_prices:
            result = self.validator.validate(price)
            assert not result.is_valid, f"Цена {price} должна быть невалидной"
            assert result.error_code == "PRICE_TOO_LOW"
    
    def test_invalid_price_custom_min(self):
        """Тест цены с кастомной минимальной ценой."""
        result = self.validator_min_price.validate(5)
        assert not result.is_valid
        assert result.error_code == "PRICE_TOO_LOW"
        assert "больше 10" in result.error_message
    
    def test_invalid_price_type(self):
        """Тест цены неправильного типа."""
        invalid_prices = ["abc", "invalid"]
        
        for price in invalid_prices:
            result = self.validator.validate(price)
            assert not result.is_valid, f"Цена {price} должна быть невалидной"
            assert result.error_code == "INVALID_PRICE_TYPE"
    
    def test_empty_price(self):
        """Тест пустой цены."""
        result = self.validator.validate(None)
        assert not result.is_valid
        assert result.error_code == "EMPTY_PRICE"
    
    def test_valid_currency(self):
        """Тест валидных валют."""
        valid_currencies = ["EUR", "USD", "GBP", "JPY", "RUB", "CNY", "USDT", "ETH", "BTC"]
        
        for currency in valid_currencies:
            result = self.validator.validate_with_currency(100, currency)
            assert result.is_valid, f"Валюта {currency} должна быть валидной"
    
    def test_invalid_currency(self):
        """Тест невалидных валют."""
        invalid_currencies = ["INVALID", "RUBLES", "DOLLARS"]
        
        for currency in invalid_currencies:
            result = self.validator.validate_with_currency(100, currency)
            assert not result.is_valid, f"Валюта {currency} должна быть невалидной"
            assert result.error_code == "UNSUPPORTED_CURRENCY"
    
    def test_empty_currency(self):
        """Тест пустой валюты."""
        result = self.validator.validate_with_currency(100, "")
        assert not result.is_valid
        assert result.error_code == "EMPTY_CURRENCY"


class TestProductValidator:
    """Тесты для ProductValidator."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.validator = ProductValidator()
    
    def test_valid_product(self):
        """Тест валидного продукта."""
        valid_product = {
            "business_id": "test_product_1",
            "title": "Test Product",
            "cover_image_url": "Qm123456789",
            "species": "Amanita muscaria",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "Qm123456789",
                    "proportion": "100%"
                }
            ]
        }

        result = self.validator.validate(valid_product)
        assert result.is_valid, "Продукт должен быть валидным"

    def test_invalid_product_type(self):
        """Тест невалидного типа продукта."""
        invalid_product = "not a dict"

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.error_code == "INVALID_PRODUCT_TYPE"

    def test_missing_required_fields(self):
        """Тест отсутствующих обязательных полей."""
        incomplete_product = {
            "business_id": "test_product_1",
            "title": "Test Product"
            # отсутствует cover_image_url, species, organic_components
        }

        result = self.validator.validate(incomplete_product)
        assert not result.is_valid
        assert result.error_code == "MISSING_REQUIRED_FIELD"
        # Первое отсутствующее поле - cover_image_url
        assert "cover_image_url" in result.error_message

    def test_invalid_product_id(self):
        """Тест невалидного business_id продукта."""
        invalid_product = {
            "business_id": "",  # пустой business_id
            "title": "Test Product",
            "cover_image_url": "Qm123456789",
            "species": "Amanita muscaria",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "Qm123456789",
                    "proportion": "100%"
                }
            ]
        }

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.error_code == "MISSING_BUSINESS_ID"

    def test_empty_title(self):
        """Тест пустого заголовка."""
        invalid_product = {
            "business_id": "test_product_1",
            "title": "",  # пустой заголовок
            "cover_image_url": "Qm123456789",
            "species": "Amanita muscaria",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "Qm123456789",
                    "proportion": "100%"
                }
            ]
        }

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.error_code == "EMPTY_TITLE"

    def test_empty_organic_components(self):
        """Тест пустых органических компонентов."""
        invalid_product = {
            "business_id": "test_product_1",
            "title": "Test Product",
            "cover_image_url": "Qm123456789",
            "species": "Amanita muscaria",
            "organic_components": []  # пустой список
        }

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.error_code == "EMPTY_ORGANIC_COMPONENTS"

    def test_invalid_component(self):
        """Тест невалидного компонента."""
        invalid_product = {
            "business_id": "test_product_1",
            "title": "Test Product",
            "cover_image_url": "Qm123456789",
            "species": "Amanita muscaria",
            "organic_components": [
                {
                    "biounit_id": "",  # пустой biounit_id
                    "description_cid": "Qm123456789",
                    "proportion": "100%"
                }
            ]
        }

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.error_code == "EMPTY_BIOUNIT_ID"

    def test_invalid_cover_image(self):
        """Тест невалидного изображения."""
        invalid_product = {
            "business_id": "test_product_1",
            "title": "Test Product",
            "cover_image_url": "invalid_cid",  # невалидный CID
            "species": "Amanita muscaria",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "Qm123456789",
                    "proportion": "100%"
                }
            ]
        }

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.field_name == "cover_image_url"

    def test_invalid_price(self):
        """Тест невалидной цены."""
        invalid_product = {
            "business_id": "test_product_1",
            "title": "Test Product",
            "cover_image_url": "Qm123456789",
            "species": "Amanita muscaria",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "Qm123456789",
                    "proportion": "100%"
                }
            ],
            "prices": [
                {
                    "price": -10,  # невалидная цена
                    "currency": "EUR"
                }
            ]
        }

        result = self.validator.validate(invalid_product)
        assert not result.is_valid
        assert result.error_code == "PRICE_TOO_LOW"
