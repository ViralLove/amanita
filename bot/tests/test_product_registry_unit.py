import pytest
import logging
import sys
from bot.services.product.validation import ProductValidationService

# Настройка логирования
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

print("\n=== НАЧАЛО ЮНИТ-ТЕСТИРОВАНИЯ PRODUCT REGISTRY ===")

@pytest.mark.asyncio
async def test_validate_product_data_valid():
    """
    Arrange: Подготавливаем валидные данные продукта
    Act: Валидируем данные через ProductValidationService
    Assert: Ожидаем, что результат is_valid == True
    """
    logger.info("🧪 Начинаем юнит-тест валидации валидных данных продукта")
    
    logger.info("🔧 Инициализируем ProductValidationService")
    validation_service = ProductValidationService()
    
    logger.info("📝 Подготавливаем валидные тестовые данные")
    valid_data = {
        "id": "test1",
        "title": "Test Product",
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "categories": ["mushroom"],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "form": "mixed slices",
        "species": "Amanita muscaria",
        "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
    }
    logger.info(f"🔍 Тестовые данные: {valid_data['title']}")
    
    logger.info("🚀 Вызываем validate_product_data")
    result = await validation_service.validate_product_data(valid_data)
    
    logger.info(f"🔍 Результат валидации: {result}")
    assert result["is_valid"] is True
    assert not result["errors"]
    
    logger.info("✅ Юнит-тест валидации валидных данных завершен")

@pytest.mark.asyncio
async def test_validate_product_data_invalid():
    """
    Arrange: Подготавливаем невалидные данные продукта
    Act: Валидируем данные через ProductValidationService
    Assert: Ожидаем, что результат is_valid == False и есть ошибки
    """
    logger.info("🧪 Начинаем юнит-тест валидации невалидных данных продукта")
    
    logger.info("🔧 Инициализируем ProductValidationService")
    validation_service = ProductValidationService()
    
    logger.info("📝 Подготавливаем невалидные тестовые данные")
    invalid_data = {
        "id": "test2",
        "title": "",  # Пустой заголовок
        "description_cid": "invalid_cid",  # Невалидный CID
        "categories": [],  # Пустые категории
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "form": "mixed slices",
        "species": "Amanita muscaria",
        "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "INVALID"}]  # Невалидная валюта
    }
    logger.info(f"🔍 Невалидные тестовые данные: {invalid_data['title']}")
    
    logger.info("🚀 Вызываем validate_product_data")
    result = await validation_service.validate_product_data(invalid_data)
    
    logger.info(f"🔍 Результат валидации: {result}")
    assert result["is_valid"] is False
    assert len(result["errors"]) > 0
    
    logger.info("✅ Юнит-тест валидации невалидных данных завершен")

@pytest.mark.asyncio
async def test_validate_product_data_missing_required():
    """
    Arrange: Подготавливаем данные продукта с отсутствующими обязательными полями
    Act: Валидируем данные через ProductValidationService
    Assert: Ожидаем, что результат is_valid == False и есть ошибки о недостающих полях
    """
    logger.info("🧪 Начинаем юнит-тест валидации данных с недостающими полями")
    
    logger.info("🔧 Инициализируем ProductValidationService")
    validation_service = ProductValidationService()
    
    logger.info("📝 Подготавливаем данные с недостающими полями")
    incomplete_data = {
        "id": "test3",
        # Отсутствует title
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "categories": ["mushroom"],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "form": "mixed slices",
        "species": "Amanita muscaria"
        # Отсутствует prices
    }
    logger.info(f"🔍 Данные с недостающими полями: ID {incomplete_data['id']}")
    
    logger.info("🚀 Вызываем validate_product_data")
    result = await validation_service.validate_product_data(incomplete_data)
    
    logger.info(f"🔍 Результат валидации: {result}")
    assert result["is_valid"] is False
    assert len(result["errors"]) > 0
    
    # Проверяем наличие ошибок о недостающих полях
    error_messages = [error.lower() for error in result["errors"]]
    assert any("title" in error or "заголовок" in error for error in error_messages), "Должна быть ошибка о недостающем заголовке"
    assert any("price" in error or "цена" in error for error in error_messages), "Должна быть ошибка о недостающих ценах"
    
    logger.info("✅ Юнит-тест валидации данных с недостающими полями завершен")

# Добавьте аналогично другие async-тесты, все async-методы только через await 