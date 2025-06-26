"""
Утилиты для валидации продуктов.
Централизованная логика валидации, используемая разными сервисами.
"""
import re
from typing import Dict, List, Union, Optional
from decimal import Decimal
import decimal
import json
import logging

logger = logging.getLogger(__name__)

# Константы валидации
VALID_CURRENCIES = ["EUR", "USD"]
VALID_WEIGHT_UNITS = ["g", "kg"]
VALID_VOLUME_UNITS = ["ml", "l"]
MAX_TITLE_LENGTH = 255
MAX_CATEGORIES = 10
VALID_FORMS = ["mixed slices", "whole caps", "broken caps", "premium caps", "powder", "tincture", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
CID_PATTERN = r"^Qm[1-9A-HJ-NP-Za-km-z]{44}$"

class ValidationError(Exception):
    """Ошибка валидации с детальным описанием"""
    def __init__(self, field: str, error: str):
        self.field = field
        self.error = error
        super().__init__(f"{field}: {error}")

def validate_required_fields(data: Dict, required_fields: List[str]) -> None:
    """Проверка наличия обязательных полей"""
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(field, "Поле обязательно для заполнения")

def validate_string_length(value: str, max_length: int, field: str) -> None:
    """Проверка длины строки"""
    if len(value) > max_length:
        raise ValidationError(field, f"Превышена максимальная длина {max_length} символов")

def validate_cid(cid: str, field: str) -> None:
    """Проверка формата CID"""
    if not re.match(CID_PATTERN, cid):
        raise ValidationError(field, "Неверный формат CID")

def validate_price(price_data: Dict) -> None:
    """Валидация данных о цене"""
    logger.info(f"🔍 Валидация цены: {json.dumps(price_data, indent=2)}")
    
    if not isinstance(price_data, dict):
        error = "Данные о цене должны быть словарем"
        logger.error(f"❌ {error}")
        raise ValidationError("price", error)

    if "price" not in price_data:
        error = "Цена обязательна"
        logger.error(f"❌ {error}")
        raise ValidationError("price", error)
    
    try:
        price = Decimal(str(price_data["price"]))
        if price <= 0:
            error = "Цена должна быть положительной"
            logger.error(f"❌ {error}")
            raise ValidationError("price", error)
    except (ValueError, TypeError, decimal.InvalidOperation):
        error = "Неверный формат цены"
        logger.error(f"❌ {error}")
        raise ValidationError("price", error)

    # Валидация валюты
    if "currency" not in price_data:
        error = "Некорректная валюта"
        logger.error(f"❌ {error}")
        raise ValidationError("currency", error)
    if price_data["currency"] not in VALID_CURRENCIES:
        error = "Некорректная валюта"
        logger.error(f"❌ {error}")
        raise ValidationError("currency", error)
    
    logger.info("✅ Валидация цены успешна")

    # Проверка единиц измерения
    has_weight = "weight" in price_data and "weight_unit" in price_data
    has_volume = "volume" in price_data and "volume_unit" in price_data
    
    if has_weight and has_volume:
        raise ValidationError("measurement", "Должен быть указан вес или объем, но не оба")
    elif has_weight:
        if price_data["weight_unit"] not in VALID_WEIGHT_UNITS:
            raise ValidationError("weight_unit", f"Единица веса должна быть одной из: {', '.join(VALID_WEIGHT_UNITS)}")
        try:
            weight = Decimal(str(price_data["weight"]))
            if weight <= 0:
                raise ValidationError("weight", "Вес должен быть положительным")
        except (ValueError, TypeError, decimal.InvalidOperation):
            raise ValidationError("weight", "Неверный формат веса")
    elif has_volume:
        if price_data["volume_unit"] not in VALID_VOLUME_UNITS:
            raise ValidationError("volume_unit", f"Единица объема должна быть одной из: {', '.join(VALID_VOLUME_UNITS)}")
        try:
            volume = Decimal(str(price_data["volume"]))
            if volume <= 0:
                raise ValidationError("volume", "Объем должен быть положительным")
        except (ValueError, TypeError, decimal.InvalidOperation):
            raise ValidationError("volume", "Неверный формат объема")
    else:
        raise ValidationError("measurement", "Должен быть указан вес или объем")

def validate_categories(categories: List[str]) -> None:
    """Валидация категорий"""
    if not categories:
        raise ValidationError("categories", "Должна быть указана хотя бы одна категория")
    if len(categories) > MAX_CATEGORIES:
        raise ValidationError("categories", f"Превышено максимальное количество категорий ({MAX_CATEGORIES})")
    if not all(isinstance(cat, str) and cat.strip() for cat in categories):
        raise ValidationError("categories", "Все категории должны быть непустыми строками")

def validate_form(form: str) -> None:
    """Валидация формы продукта"""
    if form not in VALID_FORMS:
        raise ValidationError("form", f"Форма должна быть одной из: {', '.join(VALID_FORMS)}")

def validate_product_data(data: Dict) -> Dict[str, Union[bool, List[str]]]:
    """
    Комплексная валидация данных продукта.
    Возвращает словарь с результатом валидации и списком ошибок.
    """
    errors = []
    try:
        # Проверка обязательных полей
        required_fields = ["id", "title", "description_cid", "categories", "cover_image", "form", "species", "prices"]
        for field in required_fields:
            if field not in data:
                errors.append(f"{field}: Поле обязательно для заполнения")

        # Если есть отсутствующие поля, возвращаем только эти ошибки
        if any(field not in data for field in required_fields):
            return {
                "is_valid": False,
                "errors": errors
            }

        # Проверка пустых значений (кроме списков и цен)
        for field in required_fields:
            if field not in ["categories", "prices"] and not data[field]:
                errors.append(f"{field}: Поле не может быть пустым")

        # Валидация строковых полей
        if len(data["title"]) > MAX_TITLE_LENGTH:
            errors.append(f"title: Превышена максимальная длина {MAX_TITLE_LENGTH} символов")
        
        # Валидация CID
        try:
            validate_cid(data["description_cid"], "description_cid")
        except ValidationError as e:
            errors.append(f"{e.field}: {e.error}")
            
        try:
            validate_cid(data["cover_image"], "cover_image")
        except ValidationError as e:
            errors.append(f"{e.field}: {e.error}")
        
        # Валидация категорий
        try:
            validate_categories(data["categories"])
        except ValidationError as e:
            errors.append(f"{e.field}: {e.error}")
        
        # Валидация формы
        try:
            validate_form(data["form"])
        except ValidationError as e:
            errors.append(f"{e.field}: {e.error}")
        
        # Валидация цен
        if not data["prices"]:
            errors.append("prices: Должна быть указана хотя бы одна цена")
        else:
            for i, price in enumerate(data["prices"]):
                try:
                    validate_price(price)
                except ValidationError as e:
                    errors.append(f"prices[{i}].{e.field}: {e.error}")

    except Exception as e:
        errors.append(f"Неожиданная ошибка: {str(e)}")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }

def sanitize_product_data(data: Dict) -> Dict:
    """
    Санитизация данных продукта.
    Удаляет лишние пробелы, приводит к нужным типам данных.
    """
    sanitized = data.copy()
    
    # Очистка строковых полей
    for field in ["id", "title", "form", "species"]:
        if field in sanitized:
            sanitized[field] = str(sanitized[field]).strip()
    
    # Очистка категорий
    if "categories" in sanitized:
        sanitized["categories"] = [cat.strip() for cat in sanitized["categories"]]
    
    # Нормализация цен
    if "prices" in sanitized:
        for price in sanitized["prices"]:
            if "price" in price:
                price["price"] = str(Decimal(str(price["price"])))
            if "weight" in price:
                price["weight"] = str(Decimal(str(price["weight"])))
            if "volume" in price:
                price["volume"] = str(Decimal(str(price["volume"])))
    
    return sanitized 