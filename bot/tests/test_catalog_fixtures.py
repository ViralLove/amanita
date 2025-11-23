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
    
    # 🔧 АДАПТАЦИЯ: Обновлено количество продуктов под новую структуру
    assert len(valid_products) == 9, f"Ожидалось 9 валидных продуктов, получено {len(valid_products)}"
    assert len(invalid_products) == 8, f"Ожидалось 8 невалидных продуктов, получено {len(invalid_products)}"
    
    logger.info(f"✅ Валидных продуктов: {len(valid_products)}")
    logger.info(f"✅ Невалидных продуктов: {len(invalid_products)}")
    
    # Проверяем структуру первого валидного продукта
    first_product = valid_products[0]
    # 🔧 АДАПТАЦИЯ: Обновлены названия полей под новую структуру
    required_fields = ["id", "title", "cid", "categories", "cover_image_url", "forms", "species", "prices", "organic_components"]
    
    for field in required_fields:
        assert field in first_product, f"Продукт должен иметь поле '{field}'"
    
    logger.info(f"✅ Первый продукт: {first_product['title']} (ID: {first_product['id']})")
    logger.info(f"✅ Категории: {first_product['categories']}")
    logger.info(f"✅ Цены: {len(first_product['prices'])} вариантов")
    logger.info(f"✅ Органические компоненты: {len(first_product['organic_components'])} компонентов")
    
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
    # 🔧 АДАПТАЦИЯ: Обновлено количество продуктов под новую структуру
    assert catalog_info["count"] == 9, "Количество продуктов должно быть 9"
    assert len(catalog_info["product_ids"]) == 9, "Количество ID должно быть 9"
    
    # 🔧 АДАПТАЦИЯ: Проверяем наличие ключевых продуктов в новой структуре
    expected_ids = ["amanita1", "blue_lotus_tincture", "amanita_multiple_forms", "sleep_formula_1", "focus_enhancer_1"]
    for expected_id in expected_ids:
        assert expected_id in catalog_info["product_ids"], f"Должен содержать ID '{expected_id}'"
    
    # Проверяем структуру каждого продукта
    for product in catalog_info["products"]:
        assert "id" in product, "Продукт должен иметь поле 'id'"
        assert "title" in product, "Продукт должен иметь поле 'title'"
        assert "categories" in product, "Продукт должен иметь поле 'categories'"
        assert "prices" in product, "Продукт должен иметь поле 'prices'"
        assert "organic_components" in product, "Продукт должен иметь поле 'organic_components'"
        assert isinstance(product["categories"], list), "Поле 'categories' должно быть списком"
        assert isinstance(product["prices"], list), "Поле 'prices' должно быть списком"
        assert isinstance(product["organic_components"], list), "Поле 'organic_components' должно быть списком"
        assert len(product["prices"]) > 0, "Продукт должен иметь хотя бы одну цену"
        assert len(product["organic_components"]) > 0, "Продукт должен иметь хотя бы один органический компонент"
    
    logger.info("✅ Структура данных для создания каталога корректна")
    logger.info(f"✅ Продукты для создания: {catalog_info['product_ids'][:5]}... (всего {len(catalog_info['product_ids'])})")
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
        # 🔧 АДАПТАЦИЯ: Заменено description_cid на cid
        assert product["cid"], "CID не должен быть пустым"
        assert product["categories"], "Categories не должны быть пустыми"
        assert product["prices"], "Prices не должны быть пустыми"
        assert product["organic_components"], "Organic components не должны быть пустыми"
        # 🔧 АДАПТАЦИЯ: Проверяем новое поле cover_image_url
        assert product["cover_image_url"], "Cover image URL не должен быть пустым"
        # 🔧 АДАПТАЦИЯ: Проверяем новое поле forms
        assert product["forms"], "Forms не должны быть пустыми"
    
    # Проверяем невалидные продукты (должны быть действительно невалидными)
    for product in invalid_products:
        product_id = product.get('id', 'unknown')
        logger.info(f"🔍 Проверяем невалидный продукт: {product_id}")
        
        # 🔧 АДАПТАЦИЯ: Обновлены проверки под новую структуру данных
        if product_id == "invalid_empty_fields":
            # Все поля пустые (кроме обязательных)
            assert not product.get("title"), "Title должен быть пустым"
            assert not product.get("categories"), "Categories должны быть пустыми"
            assert not product.get("prices"), "Prices должны быть пустыми"
            assert not product.get("organic_components"), "Organic components должны быть пустыми"
            # CID может быть заполнен, так как это обязательное поле
        elif product_id == "invalid_missing_organic_components":
            # Отсутствуют органические компоненты
            assert not product.get("organic_components"), "Organic components должны быть пустыми"
        elif product_id == "invalid_price_format":
            # Невалидный формат цены
            prices = product.get("prices", [])
            assert prices, "Должны быть цены для проверки"
            price = prices[0]
            # 🔧 АДАПТАЦИЯ: Обновлены проверки под новую структуру цен
            if "weight" in price:
                assert price.get("weight") == "-100", "Weight должен быть отрицательным"
            if "volume" in price:
                assert price.get("volume") == "-50", "Volume должен быть отрицательным"
            assert price.get("price") == "not_a_number", "Price должен быть не числом"
            assert price.get("currency") == "INVALID", "Currency должен быть невалидным"
        elif product_id == "invalid_cid_format":
            # Невалидный формат CID в органических компонентах или cover_image_url
            organic_components = product.get("organic_components", [])
            assert organic_components, "Должны быть органические компоненты для проверки"
            component = organic_components[0]
            assert component.get("description_cid") == "invalid_cid", "Description CID в компоненте должен быть невалидным"
            assert product.get("cover_image_url") == "invalid_cid", "Cover image URL должен быть невалидным"
        elif product_id == "invalid_currency":
            # Невалидная валюта
            prices = product.get("prices", [])
            assert prices, "Должны быть цены для проверки"
            price = prices[0]
            assert price.get("currency") == "INVALID", "Currency должен быть невалидным"
        elif product_id == "invalid_proportion_format":
            # Невалидный формат пропорции
            organic_components = product.get("organic_components", [])
            assert organic_components, "Должны быть органические компоненты для проверки"
            component = organic_components[0]
            assert component.get("proportion") == "invalid_proportion", "Proportion должен быть невалидным"
        elif product_id == "invalid_proportion_sum":
            # Невалидная сумма пропорций
            organic_components = product.get("organic_components", [])
            assert organic_components, "Должны быть органические компоненты для проверки"
            # Проверяем, что сумма пропорций не равна 100%
            proportions = [float(c.get("proportion", "0").replace("%", "")) for c in organic_components]
            assert sum(proportions) != 100, "Сумма пропорций не должна быть равна 100%"
        elif product_id == "invalid_duplicate_component_id":
            # Дублирующиеся component_id
            organic_components = product.get("organic_components", [])
            assert organic_components, "Должны быть органические компоненты для проверки"
            component_ids = [c.get("component_id") for c in organic_components]
            assert len(component_ids) != len(set(component_ids)), "Должны быть дублирующиеся component_id"
        
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