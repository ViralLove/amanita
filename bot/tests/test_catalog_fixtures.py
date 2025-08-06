import pytest
import json
import logging
from pathlib import Path

# Настройка логирования
logger = logging.getLogger(__name__)

def test_fixtures_products_json_structure():
    """Тест структуры файла fixtures/products.json"""
    logger.info("🧪 Начинаем тест структуры fixtures/products.json")
    
    # Arrange - загружаем данные напрямую
    fixtures_path = Path(__file__).parent / "fixtures" / "products.json"
    with open(fixtures_path) as f:
        data = json.load(f)
    
    # Assert - проверяем структуру
    assert "valid_products" in data, "Файл должен содержать ключ 'valid_products'"
    assert "invalid_products" in data, "Файл должен содержать ключ 'invalid_products'"
    
    valid_products = data["valid_products"]
    invalid_products = data["invalid_products"]
    
    assert len(valid_products) == 2, f"Ожидалось 2 валидных продукта, получено {len(valid_products)}"
    assert len(invalid_products) == 4, f"Ожидалось 4 невалидных продукта, получено {len(invalid_products)}"
    
    logger.info(f"✅ Валидных продуктов: {len(valid_products)}")
    logger.info(f"✅ Невалидных продуктов: {len(invalid_products)}")
    
    # Проверяем структуру первого валидного продукта
    first_product = valid_products[0]
    required_fields = ["id", "title", "description_cid", "categories", "cover_image", "form", "species", "prices"]
    
    for field in required_fields:
        assert field in first_product, f"Продукт должен иметь поле '{field}'"
    
    logger.info(f"✅ Первый продукт: {first_product['title']} (ID: {first_product['id']})")
    logger.info(f"✅ Категории: {first_product['categories']}")
    logger.info(f"✅ Цены: {len(first_product['prices'])} вариантов")
    
    # Проверяем уникальность ID валидных продуктов
    valid_product_ids = [p["id"] for p in valid_products]
    assert len(valid_product_ids) == len(set(valid_product_ids)), "Все ID валидных продуктов должны быть уникальными"
    
    # Проверяем уникальность ID невалидных продуктов
    invalid_product_ids = [p["id"] for p in invalid_products]
    assert len(invalid_product_ids) == len(set(invalid_product_ids)), "Все ID невалидных продуктов должны быть уникальными"
    
    logger.info("✅ Тест структуры fixtures/products.json завершен успешно")

def test_catalog_info_structure():
    """Тест структуры данных для создания каталога"""
    logger.info("🧪 Начинаем тест структуры данных для создания каталога")
    
    # Arrange - загружаем данные напрямую
    fixtures_path = Path(__file__).parent / "fixtures" / "products.json"
    with open(fixtures_path) as f:
        data = json.load(f)
    
    valid_products = data["valid_products"]
    
    # Создаем структуру данных для создания каталога
    catalog_info = {
        "products": valid_products,
        "count": len(valid_products),
        "product_ids": [p["id"] for p in valid_products]
    }
    
    # Assert
    assert catalog_info["count"] == 2, "Количество продуктов должно быть 2"
    assert len(catalog_info["product_ids"]) == 2, "Количество ID должно быть 2"
    assert "amanita1" in catalog_info["product_ids"], "Должен содержать ID 'amanita1'"
    assert "blue_lotus_tincture" in catalog_info["product_ids"], "Должен содержать ID 'blue_lotus_tincture'"
    
    # Проверяем структуру каждого продукта
    for product in catalog_info["products"]:
        assert "id" in product, "Продукт должен иметь поле 'id'"
        assert "title" in product, "Продукт должен иметь поле 'title'"
        assert "categories" in product, "Продукт должен иметь поле 'categories'"
        assert "prices" in product, "Продукт должен иметь поле 'prices'"
        assert isinstance(product["categories"], list), "Поле 'categories' должно быть списком"
        assert isinstance(product["prices"], list), "Поле 'prices' должно быть списком"
        assert len(product["prices"]) > 0, "Продукт должен иметь хотя бы одну цену"
    
    logger.info("✅ Структура данных для создания каталога корректна")
    logger.info(f"✅ Продукты для создания: {catalog_info['product_ids']}")
    logger.info("✅ Тест структуры данных для создания каталога завершен успешно")

def test_product_validation_data():
    """Тест данных для валидации продуктов"""
    logger.info("🧪 Начинаем тест данных для валидации продуктов")
    
    # Arrange - загружаем данные напрямую
    fixtures_path = Path(__file__).parent / "fixtures" / "products.json"
    with open(fixtures_path) as f:
        data = json.load(f)
    
    valid_products = data["valid_products"]
    invalid_products = data["invalid_products"]
    
    # Проверяем валидные продукты
    for product in valid_products:
        assert product["id"], "ID не должен быть пустым"
        assert product["title"], "Title не должен быть пустым"
        assert product["description_cid"], "Description CID не должен быть пустым"
        assert product["categories"], "Categories не должны быть пустыми"
        assert product["prices"], "Prices не должны быть пустыми"
    
    # Проверяем невалидные продукты (должны быть действительно невалидными)
    for product in invalid_products:
        product_id = product.get('id', 'unknown')
        logger.info(f"🔍 Проверяем невалидный продукт: {product_id}")
        
        # Проверяем различные типы невалидности
        if product_id == "invalid_empty_fields":
            # Все поля пустые
            assert not product.get("title"), "Title должен быть пустым"
            assert not product.get("description_cid"), "Description CID должен быть пустым"
            assert not product.get("categories"), "Categories должны быть пустыми"
            assert not product.get("prices"), "Prices должны быть пустыми"
        elif product_id == "invalid_price_format":
            # Невалидный формат цены
            prices = product.get("prices", [])
            assert prices, "Должны быть цены для проверки"
            price = prices[0]
            assert price.get("weight") == "-100", "Weight должен быть отрицательным"
            assert price.get("price") == "not_a_number", "Price должен быть не числом"
            assert price.get("currency") == "INVALID", "Currency должен быть невалидным"
        elif product_id == "invalid_cid_format":
            # Невалидный формат CID
            assert product.get("description_cid") == "invalid_cid", "Description CID должен быть невалидным"
            assert product.get("cover_image") == "invalid_cid", "Cover image CID должен быть невалидным"
        elif product_id == "invalid_currency":
            # Невалидная валюта
            prices = product.get("prices", [])
            assert prices, "Должны быть цены для проверки"
            price = prices[0]
            assert price.get("currency") == "INVALID", "Currency должен быть невалидным"
        
        logger.info(f"✅ Невалидный продукт {product_id} проверен")
    
    logger.info(f"✅ Проверено {len(valid_products)} валидных продуктов")
    logger.info(f"✅ Проверено {len(invalid_products)} невалидных продуктов")
    logger.info("✅ Тест данных для валидации продуктов завершен успешно")

if __name__ == "__main__":
    # Запуск тестов напрямую
    test_fixtures_products_json_structure()
    test_catalog_info_structure()
    test_product_validation_data()
    print("✅ Все тесты фикстур прошли успешно!") 