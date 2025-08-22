"""
Тесты для фабрик конвертации API ↔ Service модели.

Этот модуль содержит тесты для всех конвертеров:
- OrganicComponentConverter
- PriceConverter  
- ProductConverter
"""

import pytest
from typing import Dict, Any, List
from decimal import Decimal

# Импорты конвертеров
from bot.api.converters import (
    BaseConverter,
    OrganicComponentConverter,
    PriceConverter,
    ProductConverter
)

# Импорты API моделей
from bot.api.models.product import (
    OrganicComponentAPI,
    PriceModel,
    ProductUploadIn
)

# Импорты Service моделей
from bot.model.organic_component import OrganicComponent
from bot.model.product import Product, PriceInfo

# Импорты для тестовых данных (опционально)
# from bot.tests.fixtures.products import get_test_products


class TestBaseConverter:
    """Базовые тесты для всех конвертеров"""
    
    def test_base_converter_abstract(self):
        """Тест, что BaseConverter является абстрактным классом"""
        with pytest.raises(TypeError):
            BaseConverter()


class TestOrganicComponentConverter:
    """Тесты для OrganicComponentConverter"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.converter = OrganicComponentConverter()
    
    def test_converter_creation(self):
        """Тест создания конвертера"""
        assert isinstance(self.converter, OrganicComponentConverter)
        assert isinstance(self.converter, BaseConverter)
    
    def test_valid_api_to_service(self):
        """Тест конвертации валидной API модели в Service модель"""
        api_model = OrganicComponentAPI(
            biounit_id="amanita_muscaria",
            description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            proportion="100%"
        )
        
        service_model = self.converter.api_to_service(api_model)
        
        assert isinstance(service_model, OrganicComponent)
        assert service_model.biounit_id == "amanita_muscaria"
        assert service_model.description_cid == "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        assert service_model.proportion == "100%"
    
    def test_valid_service_to_api(self):
        """Тест конвертации валидной Service модели в API модель"""
        service_model = OrganicComponent(
            biounit_id="amanita_muscaria",
            description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            proportion="100%"
        )
        
        api_model = self.converter.service_to_api(service_model)
        
        assert isinstance(api_model, OrganicComponentAPI)
        assert api_model.biounit_id == "amanita_muscaria"
        assert api_model.description_cid == "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        assert api_model.proportion == "100%"
    
    def test_api_to_dict(self):
        """Тест конвертации API модели в словарь"""
        api_model = OrganicComponentAPI(
            biounit_id="amanita_muscaria",
            description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            proportion="100%"
        )
        
        result = self.converter.api_to_dict(api_model)
        
        assert isinstance(result, dict)
        assert result["biounit_id"] == "amanita_muscaria"
        assert result["description_cid"] == "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        assert result["proportion"] == "100%"
    
    def test_dict_to_api(self):
        """Тест конвертации словаря в API модель"""
        data = {
            "biounit_id": "amanita_muscaria",
            "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            "proportion": "100%"
        }
        
        api_model = self.converter.dict_to_api(data)
        
        assert isinstance(api_model, OrganicComponentAPI)
        assert api_model.biounit_id == "amanita_muscaria"
        assert api_model.description_cid == "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        assert api_model.proportion == "100%"
    
    def test_validate_api_model_success(self):
        """Тест успешной валидации API модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_cid_result = Mock(spec=ValidationResult)
        mock_cid_result.is_valid = True
        
        mock_proportion_result = Mock(spec=ValidationResult)
        mock_proportion_result.is_valid = True
        
        # Создаем моки валидаторов
        mock_cid_validator = Mock()
        mock_cid_validator.validate.return_value = mock_cid_result
        
        mock_proportion_validator = Mock()
        mock_proportion_validator.validate.return_value = mock_proportion_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.organic_component_converter.ValidationFactory') as mock_factory:
            mock_factory.get_cid_validator.return_value = mock_cid_validator
            mock_factory.get_proportion_validator.return_value = mock_proportion_validator
            
            # Тестируем валидацию
            api_model = OrganicComponentAPI(
                biounit_id="amanita_muscaria",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion="100%"
            )
            
            result = self.converter.validate_api_model(api_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_cid_validator.assert_called_once()
            mock_factory.get_proportion_validator.assert_called_once()
            mock_cid_validator.validate.assert_called_once()
            mock_proportion_validator.validate.assert_called_once()
            assert result is True
    
    def test_validate_api_model_failure(self):
        """Тест неуспешной валидации API модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult с ошибкой
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = False
        mock_result.error_message = "CID validation failed"
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.organic_component_converter.ValidationFactory') as mock_factory:
            mock_factory.get_cid_validator.return_value = mock_validator
            mock_factory.get_proportion_validator.return_value = mock_validator
            
            # Тестируем валидацию с валидными данными для создания модели
            api_model = OrganicComponentAPI(
                biounit_id="amanita_muscaria",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion="100%"
            )
            
            result = self.converter.validate_api_model(api_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_cid_validator.assert_called_once()
            mock_validator.validate.assert_called_once()
            assert result is False
    
    def test_validate_service_model_success(self):
        """Тест успешной валидации Service модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_cid_result = Mock(spec=ValidationResult)
        mock_cid_result.is_valid = True
        
        mock_proportion_result = Mock(spec=ValidationResult)
        mock_proportion_result.is_valid = True
        
        # Создаем моки валидаторов
        mock_cid_validator = Mock()
        mock_cid_validator.validate.return_value = mock_cid_result
        
        mock_proportion_validator = Mock()
        mock_proportion_validator.validate.return_value = mock_proportion_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.organic_component_converter.ValidationFactory') as mock_factory:
            mock_factory.get_cid_validator.return_value = mock_cid_validator
            mock_factory.get_proportion_validator.return_value = mock_proportion_validator
            
            # Тестируем валидацию
            service_model = OrganicComponent(
                biounit_id="amanita_muscaria",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion="100%"
            )
            
            result = self.converter.validate_service_model(service_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_cid_validator.assert_called_once()
            mock_factory.get_proportion_validator.assert_called_once()
            mock_cid_validator.validate.assert_called_once()
            mock_proportion_validator.validate.assert_called_once()
            assert result is True
    
    def test_validate_service_model_failure(self):
        """Тест неуспешной валидации Service модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult с ошибкой
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = False
        mock_result.error_message = "Proportion validation failed"
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.organic_component_converter.ValidationFactory') as mock_factory:
            mock_factory.get_cid_validator.return_value = mock_validator
            mock_factory.get_proportion_validator.return_value = mock_validator
            
            # Тестируем валидацию с валидными данными для создания модели
            service_model = OrganicComponent(
                biounit_id="amanita_muscaria",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion="100%"
            )
            
            result = self.converter.validate_service_model(service_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_cid_validator.assert_called_once()
            mock_validator.validate.assert_called_once()
            assert result is False
    
    def test_invalid_cid_format(self):
        """Тест обработки невалидного CID"""
        # Pydantic валидация происходит при создании модели
        with pytest.raises(Exception):  # InvalidCIDError или ValidationError
            api_model = OrganicComponentAPI(
                biounit_id="amanita_muscaria",
                description_cid="invalid_cid",
                proportion="100%"
            )
    
    def test_invalid_proportion_format(self):
        """Тест обработки невалидной пропорции"""
        # Pydantic валидация происходит при создании модели
        with pytest.raises(Exception):  # ValidationError
            api_model = OrganicComponentAPI(
                biounit_id="amanita_muscaria",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion="invalid"
            )


class TestPriceConverter:
    """Тесты для PriceConverter"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.converter = PriceConverter()
    
    def test_converter_creation(self):
        """Тест создания конвертера"""
        assert isinstance(self.converter, PriceConverter)
        assert isinstance(self.converter, BaseConverter)
    
    def test_valid_api_to_service(self):
        """Тест конвертации валидной API модели в Service модель"""
        api_model = PriceModel(
            price=100,
            currency="EUR",
            weight="100",
            weight_unit="g"
        )
        
        service_model = self.converter.api_to_service(api_model)
        
        assert isinstance(service_model, PriceInfo)
        assert service_model.price == Decimal('100')
        assert service_model.currency == "EUR"
        assert service_model.weight == Decimal('100')
        assert service_model.weight_unit == "g"
    
    def test_valid_service_to_api(self):
        """Тест конвертации валидной Service модели в API модель"""
        service_model = PriceInfo(
            price=100,
            currency="EUR",
            weight="100",
            weight_unit="g"
        )
        
        api_model = self.converter.service_to_api(service_model)
        
        assert isinstance(api_model, PriceModel)
        assert api_model.price == 100
        assert api_model.currency == "EUR"
        assert api_model.weight == "100"
        assert api_model.weight_unit == "g"
    
    def test_api_to_dict(self):
        """Тест конвертации API модели в словарь"""
        api_model = PriceModel(
            price=100,
            currency="EUR",
            weight="100",
            weight_unit="g"
        )
        
        result = self.converter.api_to_dict(api_model)
        
        assert isinstance(result, dict)
        assert result["price"] == 100
        assert result["currency"] == "EUR"
        assert result["weight"] == "100"
        assert result["weight_unit"] == "g"
    
    def test_dict_to_api(self):
        """Тест конвертации словаря в API модель"""
        data = {
            "price": 100,
            "currency": "EUR",
            "weight": "100",
            "weight_unit": "g"
        }
        
        api_model = self.converter.dict_to_api(data)
        
        assert isinstance(api_model, PriceModel)
        assert api_model.price == 100
        assert api_model.currency == "EUR"
        assert api_model.weight == "100"
        assert api_model.weight_unit == "g"
    
    def test_invalid_price(self):
        """Тест обработки невалидной цены"""
        # Pydantic валидация происходит при создании модели
        with pytest.raises(Exception):  # ValidationError
            api_model = PriceModel(
                price=0,  # Невалидная цена
                currency="EUR"
            )
    
    def test_weight_and_volume_conflict(self):
        """Тест обработки конфликта веса и объема"""
        api_model = PriceModel(
            price=100,
            currency="EUR",
            weight="100",
            weight_unit="g",
            volume="50",
            volume_unit="ml"
        )
        
        with pytest.raises(ValueError):
            self.converter.api_to_service(api_model)
    
    def test_validate_api_model_success(self):
        """Тест успешной валидации API модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = True
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate_with_currency.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.price_converter.ValidationFactory') as mock_factory:
            mock_factory.get_price_validator.return_value = mock_validator
            
            # Тестируем валидацию
            api_model = PriceModel(
                price=100,
                currency="EUR",
                weight="100",
                weight_unit="g"
            )
            
            result = self.converter.validate_api_model(api_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_price_validator.assert_called_once()
            mock_validator.validate_with_currency.assert_called_once_with(100, "EUR")
            assert result is True
    
    def test_validate_api_model_failure(self):
        """Тест неуспешной валидации API модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult с ошибкой
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = False
        mock_result.error_message = "Price validation failed"
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate_with_currency.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.price_converter.ValidationFactory') as mock_factory:
            mock_factory.get_price_validator.return_value = mock_validator
            
            # Тестируем валидацию с валидными данными для создания модели
            api_model = PriceModel(
                price=100,  # Валидная цена
                currency="EUR",
                weight="100",
                weight_unit="g"
            )
            
            result = self.converter.validate_api_model(api_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_price_validator.assert_called_once()
            mock_validator.validate_with_currency.assert_called_once_with(100, "EUR")
            assert result is False
    
    def test_validate_service_model_success(self):
        """Тест успешной валидации Service модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = True
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate_with_currency.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.price_converter.ValidationFactory') as mock_factory:
            mock_factory.get_price_validator.return_value = mock_validator
            
            # Тестируем валидацию
            service_model = PriceInfo(
                price=100,
                currency="EUR",
                weight="100",
                weight_unit="g"
            )
            
            result = self.converter.validate_service_model(service_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_price_validator.assert_called_once()
            mock_validator.validate_with_currency.assert_called_once_with(100, "EUR")
            assert result is True
    
    def test_validate_service_model_failure(self):
        """Тест неуспешной валидации Service модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult с ошибкой
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = False
        mock_result.error_message = "Currency validation failed"
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate_with_currency.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.price_converter.ValidationFactory') as mock_factory:
            mock_factory.get_price_validator.return_value = mock_validator
        
            # Тестируем валидацию с валидными данными для создания модели
            service_model = PriceInfo(
                price=100,
                currency="EUR",  # Валидная валюта
                weight="100",
                weight_unit="g"
            )
            
            result = self.converter.validate_service_model(service_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_price_validator.assert_called_once()
            mock_validator.validate_with_currency.assert_called_once_with(100, "EUR")
            assert result is False


class TestProductConverter:
    """Тесты для ProductConverter"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.converter = ProductConverter()
    
    def test_converter_creation(self):
        """Тест создания конвертера"""
        assert isinstance(self.converter, ProductConverter)
        assert isinstance(self.converter, BaseConverter)
    
    def test_valid_api_to_service(self):
        """Тест конвертации валидной API модели в Service модель"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = True
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory для модели Product
        with patch('bot.model.product.ValidationFactory') as mock_factory:
            mock_factory.get_cid_validator.return_value = mock_validator
            mock_factory.get_proportion_validator.return_value = mock_validator
            mock_factory.get_price_validator.return_value = mock_validator
            
            api_model = ProductUploadIn(
                id=1,
                title="Test Product",
                organic_components=[
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[
                    PriceModel(price=100, currency="EUR")
                ]
            )
            
            service_model = self.converter.api_to_service(api_model)
            
            assert isinstance(service_model, Product)
            assert service_model.id == 1  # API int остается int в Service
            assert service_model.title == "Test Product"
            assert len(service_model.organic_components) == 1
            assert len(service_model.prices) == 1
    
    def test_valid_service_to_api(self):
        """Тест конвертации валидной Service модели в API модель"""
        service_model = Product(
            id="1",
            alias="test",
            status=0,
            cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            title="Test Product",
            organic_components=[
                OrganicComponent(
                    biounit_id="amanita_muscaria",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion="100%"
                )
            ],
            cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[
                PriceInfo(price=100, currency="EUR")
            ]
        )
        
        api_model = self.converter.service_to_api(service_model)
        
        assert isinstance(api_model, ProductUploadIn)
        assert api_model.id == 1  # Service str → API int
        assert api_model.title == "Test Product"
        assert len(api_model.organic_components) == 1
        assert len(api_model.prices) == 1
    
    def test_api_to_dict(self):
        """Тест конвертации API модели в словарь"""
        api_model = ProductUploadIn(
            id=1,
            title="Test Product",
            organic_components=[
                OrganicComponentAPI(
                    biounit_id="amanita_muscaria",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion="100%"
                )
            ],
            cover_image="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[
                PriceModel(price=100, currency="EUR")
            ]
        )
        
        result = self.converter.api_to_dict(api_model)
        
        assert isinstance(result, dict)
        assert result["id"] == 1  # int остается int для сервиса
        assert result["title"] == "Test Product"
        assert len(result["organic_components"]) == 1
        assert len(result["prices"]) == 1
    
    def test_dict_to_api(self):
        """Тест конвертации словаря в API модель"""
        data = {
            "id": "1",
            "title": "Test Product",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    "proportion": "100%"
                }
            ],
            "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            "categories": ["mushroom"],
            "forms": ["powder"],
            "species": "Amanita Muscaria",
            "prices": [
                {
                    "price": 100,
                    "currency": "EUR"
                }
            ]
        }
        
        api_model = self.converter.dict_to_api(data)
        
        assert isinstance(api_model, ProductUploadIn)
        assert api_model.id == 1  # str → int для API
        assert api_model.title == "Test Product"
        assert len(api_model.organic_components) == 1
        assert len(api_model.prices) == 1
    
    def test_invalid_product_data(self):
        """Тест обработки невалидных данных продукта"""
        # Pydantic валидация происходит при создании модели
        with pytest.raises(Exception):  # ValidationError
            api_model = ProductUploadIn(
                id=0,  # Невалидный ID
                title="Test Product",
                organic_components=[
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[
                    PriceModel(price=100, currency="EUR")
                ]
            )
    
    def test_validate_api_model_success(self):
        """Тест успешной валидации API модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = True
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.product_converter.ValidationFactory') as mock_factory:
            mock_factory.get_product_validator.return_value = mock_validator
            
            # Тестируем валидацию
            api_model = ProductUploadIn(
                id=1,
                title="Test Product",
                organic_components=[
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[
                    PriceModel(price=100, currency="EUR")
                ]
            )
            
            result = self.converter.validate_api_model(api_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_product_validator.assert_called_once()
            mock_validator.validate.assert_called_once()
            assert result is True
    
    def test_validate_api_model_failure(self):
        """Тест неуспешной валидации API модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult с ошибкой
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = False
        mock_result.error_message = "Validation failed"
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.product_converter.ValidationFactory') as mock_factory:
            mock_factory.get_product_validator.return_value = mock_validator
            
            # Тестируем валидацию
            api_model = ProductUploadIn(
                id=1,
                title="Test Product",
                organic_components=[
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[
                    PriceModel(price=100, currency="EUR")
                ]
            )
            
            result = self.converter.validate_api_model(api_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_product_validator.assert_called_once()
            mock_validator.validate.assert_called_once()
            assert result is False
    
    def test_validate_service_model_success(self):
        """Тест успешной валидации Service модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = True
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.product_converter.ValidationFactory') as mock_factory:
            mock_factory.get_product_validator.return_value = mock_validator
            
            # Тестируем валидацию
            service_model = Product(
                id="1",
                alias="test",
                status=0,
                cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                title="Test Product",
                organic_components=[
                    OrganicComponent(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[
                    PriceInfo(price=100, currency="EUR")
                ]
            )
            
            result = self.converter.validate_service_model(service_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_product_validator.assert_called_once()
            mock_validator.validate.assert_called_once()
            assert result is True
    
    def test_validate_service_model_failure(self):
        """Тест неуспешной валидации Service модели через ValidationFactory"""
        from unittest.mock import patch, Mock
        from bot.validation import ValidationResult
        
        # Создаем мок ValidationResult с ошибкой
        mock_result = Mock(spec=ValidationResult)
        mock_result.is_valid = False
        mock_result.error_message = "Validation failed"
        
        # Создаем мок валидатора
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        
        # Создаем мок ValidationFactory
        with patch('bot.api.converters.product_converter.ValidationFactory') as mock_factory:
            mock_factory.get_product_validator.return_value = mock_validator
            
            # Тестируем валидацию
            service_model = Product(
                id="1",
                alias="test",
                status=0,
                cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                title="Test Product",
                organic_components=[
                    OrganicComponent(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[
                    PriceInfo(price=100, currency="EUR")
                ]
            )
            
            result = self.converter.validate_service_model(service_model)
            
            # Проверяем, что ValidationFactory был вызван
            mock_factory.get_product_validator.assert_called_once()
            mock_validator.validate.assert_called_once()
            assert result is False
