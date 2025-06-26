"""
Тесты для утилит валидации продуктов.
"""
import pytest
from decimal import Decimal
import decimal
from bot.services.product.validation_utils import (
    validate_product_data,
    sanitize_product_data,
    validate_price,
    validate_categories,
    validate_cid,
    validate_form,
    ValidationError,
    VALID_FORMS
)

def test_validate_price():
    """Тест валидации цен"""
    # Валидные цены с разными форматами и единицами измерения
    valid_prices = [
        # Стандартные цены с весом
        {
            "price": "100",
            "currency": "EUR",
            "weight": "100",
            "weight_unit": "g"
        },
        # Цены с объемом
        {
            "price": "20.50",
            "currency": "EUR",
            "volume": "50",
            "volume_unit": "ml"
        },
        # Цены в USD
        {
            "price": "99.99",
            "currency": "USD",
            "weight": "250",
            "weight_unit": "g"
        },
        # Цены в килограммах
        {
            "price": "1000",
            "currency": "EUR",
            "weight": "1",
            "weight_unit": "kg"
        },
        # Цены в литрах
        {
            "price": "50",
            "currency": "EUR",
            "volume": "1",
            "volume_unit": "l"
        }
    ]
    
    # Проверка валидных цен
    for price in valid_prices:
        validate_price(price)
    
    # Невалидные цены с реальными сценариями ошибок
    invalid_prices = [
        # Отсутствие обязательных полей
        ({}, "Цена обязательна"),
        ({"weight": "100", "weight_unit": "g"}, "Цена обязательна"),
        
        # Некорректные значения цены
        ({"price": "-100", "currency": "EUR", "weight": "100", "weight_unit": "g"}, 
         "Цена должна быть положительной"),
        ({"price": "0", "currency": "EUR", "weight": "100", "weight_unit": "g"}, 
         "Цена должна быть положительной"),
        ({"price": "abc", "currency": "EUR", "weight": "100", "weight_unit": "g"}, 
         "Неверный формат цены"),
        
        # Некорректная валюта
        ({"price": "100", "currency": "BTC", "weight": "100", "weight_unit": "g"}, 
         "Валюта должна быть одной из: EUR, USD"),
        ({"price": "100", "weight": "100", "weight_unit": "g"}, 
         "Валюта должна быть одной из: EUR, USD"),
        
        # Некорректные единицы измерения
        ({"price": "100", "currency": "EUR"}, 
         "Должен быть указан вес или объем"),
        ({"price": "100", "currency": "EUR", "weight": "100", "weight_unit": "oz"}, 
         "Единица веса должна быть одной из: g, kg"),
        ({"price": "100", "currency": "EUR", "volume": "100", "volume_unit": "oz"}, 
         "Единица объема должна быть одной из: ml, l"),
        
        # Смешанные единицы измерения
        ({"price": "100", "currency": "EUR", "weight": "100", "weight_unit": "g", 
          "volume": "100", "volume_unit": "ml"}, 
         "Должен быть указан вес или объем")
    ]
    
    for price_data, expected_error in invalid_prices:
        with pytest.raises(ValidationError) as exc:
            validate_price(price_data)
        assert expected_error in str(exc.value)

def test_validate_categories():
    """Тест валидации категорий"""
    # Валидные категории из реального каталога
    valid_categories = [
        ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
        ["plant", "immune system", "vital force"],
        ["mushroom", "antiparasite", "immune system", "vital force"],
        ["plant", "mental health", "focus"]
    ]
    
    for categories in valid_categories:
        validate_categories(categories)
    
    # Невалидные категории с реальными сценариями ошибок
    invalid_categories = [
        # Пустой список категорий
        ([], "Должна быть указана хотя бы одна категория"),
        
        # Превышение максимального количества категорий
        (["cat" + str(i) for i in range(11)], 
         "Превышено максимальное количество категорий"),
        
        # Некорректные значения
        ([None], "Все категории должны быть непустыми строками"),
        (["valid", ""], "Все категории должны быть непустыми строками"),
        (["valid", "   "], "Все категории должны быть непустыми строками"),
        ([123], "Все категории должны быть непустыми строками")
    ]
    
    for categories, expected_error in invalid_categories:
        with pytest.raises(ValidationError) as exc:
            validate_categories(categories)
        assert expected_error in str(exc.value)

def test_validate_cid():
    """Тест валидации CID"""
    # Валидные CID из реального каталога
    valid_cids = [
        "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "QmbTBHeByJwUP9JyTo2GcHzj1YwzVww6zXrEDFt3zgdwQ1",
        "QmUPHsHyuDHKyVbduvqoooAYShFCSfYgcnEioxNNqgZK2B"
    ]
    
    for cid in valid_cids:
        validate_cid(cid, "test_field")
    
    # Невалидные CID с реальными сценариями ошибок
    invalid_cids = [
        # Пустой CID
        ("", "Неверный формат CID"),
        
        # Некорректный формат
        ("invalid_cid", "Неверный формат CID"),
        ("Qm1234", "Неверный формат CID"),
        ("QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG_invalid", "Неверный формат CID"),
        
        # Модифицированные CID
        ("QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVS", "Неверный формат CID"),
        ("QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSGG", "Неверный формат CID"),
        ("QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG ", "Неверный формат CID")
    ]
    
    for cid, expected_error in invalid_cids:
        with pytest.raises(ValidationError) as exc:
            validate_cid(cid, "test_field")
        assert expected_error in str(exc.value)

def test_validate_form():
    """Тест валидации формы продукта"""
    # Проверяем все валидные формы из констант
    for form in VALID_FORMS:
        validate_form(form)
    
    # Невалидные формы с реальными сценариями ошибок
    invalid_forms = [
        # Пустая форма
        ("", "Форма должна быть одной из"),
        
        # Некорректный формат
        ("invalid_form", "Форма должна быть одной из"),
        ("mixed_slices", "Форма должна быть одной из"),
        ("POWDER", "Форма должна быть одной из"),
        
        # Похожие, но неверные формы
        ("whole-caps", "Форма должна быть одной из"),
        ("dried_whole", "Форма должна быть одной из"),
        ("powder ", "Форма должна быть одной из"),
        (" tincture", "Форма должна быть одной из")
    ]
    
    for form, expected_error in invalid_forms:
        with pytest.raises(ValidationError) as exc:
            validate_form(form)
        assert expected_error in str(exc.value)

def test_validate_product_data():
    """Тест комплексной валидации продукта"""
    # Валидный продукт на основе реального каталога
    valid_product = {
        "id": "amanita1",
        "title": "Amanita muscaria — sliced caps and gills (1st grade)",
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "categories": ["mushroom", "mental health", "focus", "ADHD support", "mental force"],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "form": "mixed slices",
        "species": "Amanita muscaria",
        "prices": [
            {
                "price": "80",
                "currency": "EUR",
                "weight": "100",
                "weight_unit": "g"
            }
        ]
    }
    
    result = validate_product_data(valid_product)
    assert result["is_valid"]
    assert not result["errors"]
    
    # Невалидные продукты с реальными сценариями ошибок
    invalid_products = [
        # Отсутствие обязательных полей
        ({
            "title": "Test Product"
        }, [
            "id: Поле обязательно для заполнения",
            "description_cid: Поле обязательно для заполнения",
            "categories: Поле обязательно для заполнения",
            "cover_image: Поле обязательно для заполнения",
            "form: Поле обязательно для заполнения",
            "species: Поле обязательно для заполнения",
            "prices: Поле обязательно для заполнения"
        ]),
        
        # Некорректные форматы данных
        ({
            "id": "test1",
            "title": "A" * 300,  # Слишком длинное название
            "description_cid": "invalid_cid",
            "categories": [],
            "cover_image": "invalid_cid",
            "form": "invalid_form",
            "species": "Test",
            "prices": [
                {
                    "price": "100",
                    "currency": "EUR",
                    "weight": "100",
                    "weight_unit": "g"
                }
            ]
        }, [
            "title: Превышена максимальная длина 255 символов",
            "description_cid: Неверный формат CID",
            "cover_image: Неверный формат CID",
            "categories: Должна быть указана хотя бы одна категория",
            "form: Форма должна быть одной из: mixed slices, whole caps, broken caps, premium caps, powder, tincture, flower, chunks, dried whole, dried powder, dried strips"
        ]),
        
        # Некорректные цены
        ({
            "id": "test2",
            "title": "Test Product",
            "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
            "categories": ["test"],
            "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
            "form": "powder",
            "species": "Test",
            "prices": [
                {
                    "price": "-100",
                    "currency": "EUR",
                    "weight": "100",
                    "weight_unit": "g"
                }
            ]
        }, ["prices[0].price: Цена должна быть положительной"])
    ]
    
    for product, expected_errors in invalid_products:
        result = validate_product_data(product)
        assert not result["is_valid"]
        for error in expected_errors:
            assert error in result["errors"]
        assert len(result["errors"]) == len(expected_errors), \
            f"Ожидалось {len(expected_errors)} ошибок, получено {len(result['errors'])}: {result['errors']}"

def test_sanitize_product_data():
    """Тест санитизации данных продукта"""
    # Тестовые данные с реальными сценариями очистки
    input_data = {
        "id": " amanita1 ",
        "title": " Amanita muscaria — sliced caps and gills (1st grade) ",
        "form": " mixed slices ",
        "species": " Amanita muscaria ",
        "categories": [" mushroom ", "mental health ", " focus"],
        "prices": [
            {
                "price": "80.00",
                "weight": "100.00",
                "currency": "EUR",
                "weight_unit": "g"
            },
            {
                "price": "150.000",
                "weight": "200.000",
                "currency": "EUR",
                "weight_unit": "g"
            }
        ]
    }
    
    sanitized = sanitize_product_data(input_data)
    
    # Проверка очистки строковых полей
    assert sanitized["id"] == "amanita1"
    assert sanitized["title"] == "Amanita muscaria — sliced caps and gills (1st grade)"
    assert sanitized["form"] == "mixed slices"
    assert sanitized["species"] == "Amanita muscaria"
    
    # Проверка очистки категорий
    assert sanitized["categories"] == ["mushroom", "mental health", "focus"]
    
    # Проверка нормализации чисел
    assert sanitized["prices"][0]["price"] == "80.00"
    assert sanitized["prices"][0]["weight"] == "100.00"
    assert sanitized["prices"][1]["price"] == "150.000"
    assert sanitized["prices"][1]["weight"] == "200.000"
    
    # Проверка сохранения структуры данных
    assert len(sanitized["prices"]) == 2
    assert all(price["currency"] == "EUR" for price in sanitized["prices"])
    assert all(price["weight_unit"] == "g" for price in sanitized["prices"]) 