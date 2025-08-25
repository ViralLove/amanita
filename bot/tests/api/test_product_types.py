#!/usr/bin/env python3
"""Универсальный тест типизации данных продуктов для полного покрытия CI"""

import pytest
import re
from typing import List, Dict, Any
from pydantic import ValidationError

from bot.api.models.product import (
    OrganicComponentAPI, PriceModel, ProductUploadIn, ProductUpdateIn,
    ProductCreateFromDict, ProductStatusUpdate, ProductResponse, ProductsUploadResponse
)
from bot.api.exceptions.validation import InvalidCIDError, InvalidProductFormError, EmptyCategoriesError


# ============================================================================
# A. ТЕСТЫ БАЗОВЫХ ТИПОВ (Basic Type Tests)
# ============================================================================

class TestBasicTypes:
    """Тесты базовых типов данных"""
    
    def test_string_types(self):
        """Тест строковых типов"""
        # Валидные строки
        component = OrganicComponentAPI(
            biounit_id="amanita_muscaria",
            description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            proportion="100%"
        )
        assert isinstance(component.biounit_id, str)
        assert isinstance(component.description_cid, str)
        assert isinstance(component.proportion, str)
        
        # Пустые строки должны отклоняться
        with pytest.raises(ValidationError):
            OrganicComponentAPI(
                biounit_id="",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion="100%"
            )
    
    def test_integer_types(self):
        """Тест целочисленных типов"""
        # Валидные числа
        price = PriceModel(price=100, currency='EUR')
        assert isinstance(price.price, int)
        assert price.price == 100
        
        # Статус продукта
        status = ProductStatusUpdate(status=1)
        assert isinstance(status.status, int)
        assert status.status == 1
    
    def test_list_types(self):
        """Тест списков"""
        # Валидные списки
        product = ProductUploadIn(
            id=1,
            title="Test Product",
            organic_components=[
                OrganicComponentAPI(
                    biounit_id="amanita_muscaria",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion="100%"
                )
            ],
            cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[PriceModel(price=80, currency='EUR')]
        )
        
        assert isinstance(product.organic_components, list)
        assert isinstance(product.categories, list)
        assert isinstance(product.forms, list)
        assert isinstance(product.prices, list)
    
    def test_optional_types(self):
        """Тест опциональных типов"""
        # Без seller_address
        product = ProductUploadIn(
            id=1,
            title="Test Product",
            organic_components=[
                OrganicComponentAPI(
                    biounit_id="amanita_muscaria",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion="100%"
                )
            ],
            cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[PriceModel(price=80, currency='EUR')]
        )
        
        assert product.seller_address is None


# ============================================================================
# B. ТЕСТЫ ВАЛИДАЦИИ (Validation Tests)
# ============================================================================

class TestValidation:
    """Тесты валидации данных"""
    
    def test_cid_validation(self):
        """Тест валидации CID"""
        # Валидный CID
        valid_cid = "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG"
        component = OrganicComponentAPI(
            biounit_id="test",
            description_cid=valid_cid,
            proportion="100%"
        )
        assert component.description_cid == valid_cid
        
        # Некорректный CID (не начинается с Qm)
        with pytest.raises(InvalidCIDError):
            OrganicComponentAPI(
                biounit_id="test",
                description_cid="invalid_cid",
                proportion="100%"
            )
        
        # Некорректный CID (слишком короткий)
        with pytest.raises(ValueError):
            OrganicComponentAPI(
                biounit_id="test",
                description_cid="Qm123",
                proportion="100%"
            )
    
    def test_ethereum_address_validation(self):
        """Тест валидации Ethereum адресов"""
        # Валидный адрес
        valid_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        product = ProductUploadIn(
            id=1,
            title="Test Product",
            organic_components=[
                OrganicComponentAPI(
                    biounit_id="amanita_muscaria",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion="100%"
                )
            ],
            cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[PriceModel(price=80, currency='EUR')],
            seller_address=valid_address
        )
        assert product.seller_address == valid_address
        
        # Некорректный адрес
        with pytest.raises(ValidationError):
            ProductUploadIn(
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
                prices=[PriceModel(price=80, currency='EUR')],
                seller_address="invalid_address"
            )
    
    def test_proportion_validation(self):
        """Тест валидации пропорций"""
        # Валидные пропорции
        valid_proportions = ["100%", "50%", "25.5%", "100g", "30ml", "1.5kg", "2l", "16oz", "1lb"]
        
        for proportion in valid_proportions:
            component = OrganicComponentAPI(
                biounit_id="test",
                description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                proportion=proportion
            )
            assert component.proportion == proportion
        
        # Некорректные пропорции
        invalid_proportions = ["100", "50", "invalid", "100x", "30px", ""]
        
        for proportion in invalid_proportions:
            with pytest.raises(ValidationError):
                OrganicComponentAPI(
                    biounit_id="test",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion=proportion
                )
    
    def test_product_forms_validation(self):
        """Тест валидации форм продуктов"""
        # Валидные формы
        valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", 
                      "mixed slices", "whole caps", "broken caps", "premium caps", 
                      "flower", "chunks", "dried whole", "dried powder", "dried strips"]
        
        for form in valid_forms:
            product = ProductUploadIn(
                id=1,
                title="Test Product",
                organic_components=[
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    )
                ],
                cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=[form],
                species="Amanita Muscaria",
                prices=[PriceModel(price=80, currency='EUR')]
            )
            assert form in product.forms
        
        # Некорректные формы
        invalid_forms = ["invalid", "test", "unknown", ""]
        
        for form in invalid_forms:
            with pytest.raises(InvalidProductFormError):
                ProductUploadIn(
                    id=1,
                    title="Test Product",
                    organic_components=[
                        OrganicComponentAPI(
                            biounit_id="amanita_muscaria",
                            description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                            proportion="100%"
                        )
                    ],
                    cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                    categories=["mushroom"],
                    forms=[form],
                    species="Amanita Muscaria",
                    prices=[PriceModel(price=80, currency='EUR')]
                )
    
    def test_biounit_id_uniqueness(self):
        """Тест уникальности biounit_id"""
        # Дублирующиеся biounit_id должны отклоняться
        with pytest.raises(ValidationError):
            ProductUploadIn(
                id=1,
                title="Test Product",
                organic_components=[
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="100%"
                    ),
                    OrganicComponentAPI(
                        biounit_id="amanita_muscaria",  # Дублирующийся ID
                        description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        proportion="50%"
                    )
                ],
                cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[PriceModel(price=80, currency='EUR')]
            )


# ============================================================================
# C. ТЕСТЫ ГРАНИЧНЫХ ЗНАЧЕНИЙ (Boundary Tests)
# ============================================================================

class TestBoundaryValues:
    """Тесты граничных значений"""
    
    def test_minimum_values(self):
        """Тест минимальных значений"""
        # ID должен быть > 0
        with pytest.raises(ValidationError):
            ProductUploadIn(
                id=0,  # Минимальное недопустимое значение
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
                prices=[PriceModel(price=80, currency='EUR')]
            )
        
        # Цена должна быть > 0
        with pytest.raises(ValidationError):
            PriceModel(price=0, currency='EUR')  # Минимальное недопустимое значение
        
        # Отрицательные значения
        with pytest.raises(ValidationError):
            ProductUploadIn(
                id=-1,  # Отрицательное значение
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
                prices=[PriceModel(price=80, currency='EUR')]
            )
    
    def test_empty_lists(self):
        """Тест пустых списков"""
        # Пустые списки должны отклоняться
        with pytest.raises(ValidationError):
            ProductUploadIn(
                id=1,
                title="Test Product",
                organic_components=[],  # Пустой список
                cover_image="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                categories=["mushroom"],
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[PriceModel(price=80, currency='EUR')]
            )
        
        with pytest.raises(EmptyCategoriesError):
            ProductUploadIn(
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
                categories=[],  # Пустой список
                forms=["powder"],
                species="Amanita Muscaria",
                prices=[PriceModel(price=80, currency='EUR')]
            )
    
    def test_string_lengths(self):
        """Тест длин строк"""
        # Минимальная длина строк
        with pytest.raises(ValidationError):
            ProductUploadIn(
                id=1,
                title="",  # Пустая строка
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
                prices=[PriceModel(price=80, currency='EUR')]
            )


# ============================================================================
# D. ТЕСТЫ ОТРИЦАТЕЛЬНЫХ СЛУЧАЕВ (Negative Tests)
# ============================================================================

class TestNegativeCases:
    """Тесты отрицательных случаев"""
    
    def test_incorrect_types(self):
        """Тест некорректных типов данных"""
        # Передача строки вместо числа для ID
        with pytest.raises(ValidationError):
            ProductUploadIn(
                id="invalid_id",  # Строка вместо числа
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
                prices=[PriceModel(price=80, currency='EUR')]
            )
        
        # Передача числа вместо строки для цены
        with pytest.raises(ValidationError):
            PriceModel(price="invalid_price", currency='EUR')  # Строка вместо числа
    
    def test_invalid_formats(self):
        """Тест некорректных форматов"""
        # Некорректный CID
        with pytest.raises(InvalidCIDError):
            OrganicComponentAPI(
                biounit_id="test",
                description_cid="invalid_cid_format",
                proportion="100%"
            )
        
        # Некорректный Ethereum адрес
        with pytest.raises(ValueError):
            ProductUploadIn(
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
                prices=[PriceModel(price=80, currency='EUR')],
                seller_address="0xinvalid"  # Некорректный адрес
            )


# ============================================================================
# E. ИНТЕГРАЦИОННЫЕ ТЕСТЫ (Integration Tests)
# ============================================================================

class TestIntegration:
    """Интеграционные тесты"""
    
    def test_product_creation_chain(self):
        """Тест цепочки создания продукта"""
        # Создание компонента
        component = OrganicComponentAPI(
            biounit_id="amanita_muscaria",
            description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            proportion="100%"
        )
        
        # Создание цены
        price = PriceModel(price=80, currency='EUR')
        
        # Создание продукта
        product = ProductUploadIn(
            id=1,
            title="Test Product",
            organic_components=[component],
            cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[price]
        )
        
        # Проверка цепочки
        assert product.organic_components[0] == component
        assert product.prices[0] == price
        assert product.organic_components[0].biounit_id == "amanita_muscaria"
        assert product.prices[0].price == 80
    
    def test_product_update_partial(self):
        """Тест частичного обновления продукта"""
        # Создание продукта
        product = ProductUploadIn(
            id=1,
            title="Original Title",
            organic_components=[
                OrganicComponentAPI(
                    biounit_id="amanita_muscaria",
                    description_cid="QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    proportion="100%"
                )
            ],
            cover_image_url="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            categories=["mushroom"],
            forms=["powder"],
            species="Amanita Muscaria",
            prices=[PriceModel(price=80, currency='EUR')]
        )
        
        # Частичное обновление
        update = ProductUpdateIn(
            title="Updated Title",
            species="Updated Species"
        )
        
        # Проверка частичного обновления
        assert update.title == "Updated Title"
        assert update.species == "Updated Species"
        assert update.organic_components is None  # Не изменено
    
    def test_dict_to_model_conversion(self):
        """Тест преобразования словаря в модель"""
        # Словарь с данными
        product_dict = {
            "id": 1,
            "title": "Test Product",
            "organic_components": [
                {
                    "biounit_id": "amanita_muscaria",
                    "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                    "proportion": "100%"
                }
            ],
            "cover_image_url": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            "categories": ["mushroom"],
            "forms": ["powder"],
            "species": "Amanita Muscaria",
            "prices": [
                {
                    "price": 80,
                    "currency": "EUR"
                }
            ]
        }
        
        # Преобразование в модель
        product = ProductCreateFromDict(**product_dict)
        
        # Проверка преобразования
        assert product.id == 1
        assert product.title == "Test Product"
        assert len(product.organic_components) == 1
        assert product.organic_components[0]["biounit_id"] == "amanita_muscaria"
        assert len(product.prices) == 1
        assert product.prices[0]["price"] == 80


# ============================================================================
# F. ТЕСТЫ JSON SCHEMA (Schema Tests)
# ============================================================================

class TestJSONSchema:
    """Тесты JSON схемы"""
    
    def test_schema_generation(self):
        """Тест генерации JSON схемы"""
        # Генерация схем для всех моделей
        schemas = {
            "OrganicComponentAPI": OrganicComponentAPI.model_json_schema(),
            "PriceModel": PriceModel.model_json_schema(),
            "ProductUploadIn": ProductUploadIn.model_json_schema(),
            "ProductUpdateIn": ProductUpdateIn.model_json_schema(),
            "ProductStatusUpdate": ProductStatusUpdate.model_json_schema(),
            "ProductResponse": ProductResponse.model_json_schema(),
            "ProductsUploadResponse": ProductsUploadResponse.model_json_schema()
        }
        
        # Проверка, что схемы сгенерированы
        for name, schema in schemas.items():
            assert schema is not None
            assert "properties" in schema
            assert "type" in schema
            print(f"✅ Схема {name} сгенерирована успешно")
    
    def test_schema_examples(self):
        """Тест примеров в JSON схеме"""
        # Проверка примеров для ProductUploadIn
        schema = ProductUploadIn.model_json_schema()
        assert "example" in schema
        
        # Проверка примера
        example = schema["example"]
        assert "id" in example
        assert "title" in example
        assert "organic_components" in example
        assert "cover_image_url" in example
        assert "categories" in example
        assert "forms" in example
        assert "species" in example
        assert "prices" in example
        assert "seller_address" in example
    
    def test_field_descriptions(self):
        """Тест описаний полей"""
        # Проверка описаний ключевых полей
        schema = ProductUploadIn.model_json_schema()
        
        # Проверка описания ID
        id_field = schema["properties"]["id"]
        assert "description" in id_field
        assert "положительным числом" in id_field["description"]
        
        # Проверка описания цены
        price_schema = PriceModel.model_json_schema()
        price_field = price_schema["properties"]["price"]
        assert "description" in price_field
        assert "положительным числом" in price_field["description"]


# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ДЛЯ ПОЛНОГО ПОКРЫТИЯ
# ============================================================================

class TestAdditionalCoverage:
    """Дополнительные тесты для полного покрытия"""
    
    def test_status_validation_constraints(self):
        """Тест ограничений валидации статуса"""
        # Валидные статусы
        valid_statuses = [0, 1]
        for status in valid_statuses:
            status_model = ProductStatusUpdate(status=status)
            assert status_model.status == status
        
        # Недопустимые статусы
        invalid_statuses = [-1, 2, 10, "active", "inactive"]
        for status in invalid_statuses:
            with pytest.raises(ValidationError):
                ProductStatusUpdate(status=status)
    
    def test_response_models(self):
        """Тест моделей ответов"""
        # ProductResponse
        response = ProductResponse(
            id="test_product_001",
            blockchain_id=12345,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            metadata_cid="QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            status="success"
        )
        
        assert response.id == "test_product_001"
        assert response.blockchain_id == 12345
        assert response.status == "success"
        assert response.error is None
        
        # ProductsUploadResponse
        upload_response = ProductsUploadResponse(results=[response])
        assert len(upload_response.results) == 1
        assert upload_response.results[0] == response
    
    def test_currency_defaults(self):
        """Тест значений по умолчанию для валюты"""
        # EUR по умолчанию
        price = PriceModel(price=100)
        assert price.currency == "EUR"
        
        # Другие валюты
        price_usd = PriceModel(price=100, currency="USD")
        assert price_usd.currency == "USD"
    
    def test_optional_price_fields(self):
        """Тест опциональных полей цены"""
        # Минимальная цена
        minimal_price = PriceModel(price=100)
        assert minimal_price.weight is None
        assert minimal_price.weight_unit is None
        assert minimal_price.volume is None
        assert minimal_price.volume_unit is None
        assert minimal_price.form is None
        
        # Полная цена
        full_price = PriceModel(
            price=100,
            weight="100",
            weight_unit="g",
            volume="50",
            volume_unit="ml",
            form="powder"
        )
        
        assert full_price.weight == "100"
        assert full_price.weight_unit == "g"
        assert full_price.volume == "50"
        assert full_price.volume_unit == "ml"
        assert full_price.form == "powder"


