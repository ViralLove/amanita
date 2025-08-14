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
    """Проверяет наличие обязательных полей"""
    for field in required_fields:
        if field not in data:
            raise ValidationError(field, "Поле обязательно для заполнения")

def validate_cid(cid: str, field: str) -> None:
    """Валидация IPFS CID"""
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
    has_weight = ("weight" in price_data and price_data["weight"] is not None and 
                  "weight_unit" in price_data and price_data["weight_unit"] is not None)
    has_volume = ("volume" in price_data and price_data["volume"] is not None and 
                  "volume_unit" in price_data and price_data["volume_unit"] is not None)
    
    # Отладочная информация
    logger.info(f"🔍 Отладка валидации: weight={price_data.get('weight')}, weight_unit={price_data.get('weight_unit')}, volume={price_data.get('volume')}, volume_unit={price_data.get('volume_unit')}")
    logger.info(f"🔍 has_weight={has_weight}, has_volume={has_volume}")
    
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
    if not isinstance(categories, list):
        raise ValidationError("categories", "Категории должны быть списком")
    
    if not categories:
        raise ValidationError("categories", "Должна быть указана хотя бы одна категория")
    
    for category in categories:
        if not isinstance(category, str):
            raise ValidationError("categories", "Каждая категория должна быть строкой")
        if not category.strip():
            raise ValidationError("categories", "Категория не может быть пустой")
        if len(category) < 2 or len(category) > 50:
            raise ValidationError("categories", "Длина категории должна быть от 2 до 50 символов")

def validate_forms(forms: List[str]) -> None:
    """Валидация списка форм продукта"""
    if not isinstance(forms, list):
        raise ValidationError("forms", "Формы должны быть списком")
    if not forms:
        raise ValidationError("forms", "Должна быть указана хотя бы одна форма")
    for form in forms:
        if not isinstance(form, str):
            raise ValidationError("forms", "Каждая форма должна быть строкой")
        if not form.strip():
            raise ValidationError("forms", "Форма не может быть пустой")
        if form not in VALID_FORMS:
            raise ValidationError("forms", f"Форма '{form}' должна быть одной из: {', '.join(VALID_FORMS)}")

def validate_organic_component(component: Dict) -> None:
    """Валидация одного органического компонента"""
    if not isinstance(component, dict):
        raise ValidationError("organic_component", "Компонент должен быть словарем")
    
    # Проверка обязательных полей
    required_fields = ["biounit_id", "description_cid", "proportion"]
    for field in required_fields:
        if field not in component:
            raise ValidationError(f"organic_component.{field}", f"Поле {field} обязательно для заполнения")
        if not component[field] or not str(component[field]).strip():
            raise ValidationError(f"organic_component.{field}", f"Поле {field} не может быть пустым")
    
    # Валидация CID
    try:
        validate_cid(component["description_cid"], f"organic_component.description_cid")
    except ValidationError as e:
        raise ValidationError(f"organic_component.{e.field}", e.error)
    
    # Валидация пропорции
    proportion = str(component["proportion"])
    proportion_pattern = r'^(\d+(?:\.\d+)?)(%|g|ml|kg|l|oz|lb|fl_oz)$'
    
    if not re.match(proportion_pattern, proportion):
        raise ValidationError("organic_component.proportion", 
                           f"Некорректный формат пропорции: {proportion}. "
                           f"Поддерживаемые форматы: 50%, 100g, 30ml, 25%")

def validate_organic_components(components: List[Dict]) -> None:
    """Валидация списка органических компонентов"""
    if not isinstance(components, list):
        raise ValidationError("organic_components", "Компоненты должны быть списком")
    
    if not components:
        raise ValidationError("organic_components", "Должен быть указан хотя бы один компонент")
    
    # Валидация каждого компонента
    for i, component in enumerate(components):
        try:
            validate_organic_component(component)
        except ValidationError as e:
            # Добавляем индекс компонента к ошибке
            raise ValidationError(f"organic_components[{i}].{e.field}", e.error)
    
    # Проверка уникальности biounit_id
    biounit_ids = [comp["biounit_id"] for comp in components]
    if len(biounit_ids) != len(set(biounit_ids)):
        raise ValidationError("organic_components", "biounit_id должен быть уникальным для каждого компонента")
    
    # Валидация пропорций
    validate_component_proportions(components)

async def validate_organic_components_with_ipfs(components: List[Dict], storage_service) -> None:
    """Валидация списка органических компонентов с проверкой существования в IPFS"""
    # Сначала базовая валидация
    validate_organic_components(components)
    
    # Проверка существования всех description_cid в IPFS
    for i, component in enumerate(components):
        description_cid = component["description_cid"]
        try:
            description_data = await storage_service.download_json_async(description_cid)
            if description_data is None:
                raise ValidationError(f"organic_components[{i}].description_cid", 
                                   f"Описание с CID {description_cid} не найдено в IPFS")
        except Exception as e:
            raise ValidationError(f"organic_components[{i}].description_cid", 
                               f"Ошибка при проверке существования описания {description_cid}: {str(e)}")

def validate_component_proportions(components: List[Dict]) -> None:
    """Валидация корректности пропорций компонентов"""
    if not components:
        return
    
    # Определяем тип пропорций
    first_proportion = str(components[0]["proportion"])
    proportion_type = None
    
    if first_proportion.endswith('%'):
        proportion_type = 'percentage'
    elif any(first_proportion.endswith(unit) for unit in ['g', 'kg', 'oz', 'lb']):
        proportion_type = 'weight'
    elif any(first_proportion.endswith(unit) for unit in ['ml', 'l', 'fl_oz']):
        proportion_type = 'volume'
    else:
        raise ValidationError("organic_components", "Неподдерживаемый тип пропорции")
    
    # Проверяем, что все компоненты имеют одинаковый тип
    for i, component in enumerate(components):
        proportion = str(component["proportion"])
        if proportion_type == 'percentage' and not proportion.endswith('%'):
            raise ValidationError(f"organic_components[{i}].proportion", 
                               "Все компоненты должны иметь одинаковый тип пропорции")
        elif proportion_type == 'weight' and not any(proportion.endswith(unit) for unit in ['g', 'kg', 'oz', 'lb']):
            raise ValidationError(f"organic_components[{i}].proportion", 
                               "Все компоненты должны иметь одинаковый тип пропорции")
        elif proportion_type == 'volume' and not any(proportion.endswith(unit) for unit in ['ml', 'l', 'fl_oz']):
            raise ValidationError(f"organic_components[{i}].proportion", 
                               "Все компоненты должны иметь одинаковый тип пропорции")
    
    # Для процентных пропорций проверяем, что сумма = 100%
    if proportion_type == 'percentage':
        total_percentage = 0
        for component in components:
            proportion_value = float(str(component["proportion"]).rstrip('%'))
            total_percentage += proportion_value
        
        if abs(total_percentage - 100.0) > 0.01:  # Допуск 0.01%
            raise ValidationError("organic_components", 
                               f"Сумма процентных пропорций должна быть 100%, текущая сумма: {total_percentage}%")
    
    # Для весовых/объемных пропорций проверяем, что все > 0
    elif proportion_type in ['weight', 'volume']:
        for i, component in enumerate(components):
            proportion_value = float(str(component["proportion"])[:-2] if str(component["proportion"])[-2:].isalpha() else str(component["proportion"])[:-1])
            if proportion_value <= 0:
                raise ValidationError(f"organic_components[{i}].proportion", 
                                   "Пропорция должна быть положительной")

async def validate_product_data(data: Dict, storage_service=None) -> Dict[str, Union[bool, List[str]]]:
    """
    Комплексная валидация данных продукта.
    Если передан storage_service, дополнительно проверяет существование description_cid в IPFS.
    Возвращает словарь с результатом валидации и списком ошибок.
    """
    errors = []
    try:
        # Проверка обязательных полей - новый формат с компонентами
        required_fields = ["id", "title", "organic_components", "categories", "cover_image", "forms", "species", "prices"]
        
        # Проверяем обязательные поля
        for field in required_fields:
            if field not in data:
                errors.append(f"{field}: Поле обязательно для заполнения")

        # Если есть отсутствующие поля, возвращаем только эти ошибки
        if any(field not in data for field in required_fields):
            return {
                "is_valid": False,
                "errors": errors
            }

        # Проверка типов данных
        if not isinstance(data["title"], str):
            errors.append("title: Должно быть строкой")
        if not isinstance(data["cover_image"], str):
            errors.append("cover_image: Должно быть строкой")
        if not isinstance(data["forms"], list):
            errors.append("forms: Должно быть списком")
        if not isinstance(data["species"], str):
            errors.append("species: Должно быть строкой")
        if not isinstance(data["categories"], list):
            errors.append("categories: Должно быть списком")
        
        # Проверка типа organic_components
        if not isinstance(data["organic_components"], list):
            errors.append("organic_components: Должно быть списком")

        # Проверка пустых значений (кроме списков и цен)
        for field in required_fields:
            if field not in ["categories", "prices", "forms", "organic_components"]:
                # Для строковых полей проверяем на пустоту и None
                if field in ["id", "title", "cover_image", "species"]:
                    if data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                        errors.append(f"{field}: Поле не может быть пустым")
                # Для остальных полей используем стандартную проверку
                elif not data[field]:
                    errors.append(f"{field}: Поле не может быть пустым")

        # Валидация строковых полей
        if len(data["title"]) > MAX_TITLE_LENGTH:
            errors.append(f"title: Превышена максимальная длина {MAX_TITLE_LENGTH} символов")
        
        # Валидация компонентов (включает валидацию CID)
        try:
            validate_organic_components(data["organic_components"])
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
        
        # Валидация форм
        try:
            validate_forms(data["forms"])
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
        
        # Дополнительная IPFS валидация компонентов, если передан storage_service
        if storage_service and "organic_components" in data:
            try:
                await validate_organic_components_with_ipfs(data["organic_components"], storage_service)
            except ValidationError as e:
                errors.append(f"{e.field}: {e.error}")

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
    for field in ["id", "title", "species"]:
        if field in sanitized:
            sanitized[field] = str(sanitized[field]).strip()
    
    # Очистка форм
    if "forms" in sanitized:
        sanitized["forms"] = [form.strip() for form in sanitized["forms"] if form.strip()]
    
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