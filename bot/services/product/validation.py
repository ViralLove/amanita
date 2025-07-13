from typing import Optional, Dict, Any, List, Union
import logging
import re
from services.product.validation_utils import (
    validate_product_data,
    sanitize_product_data,
    ValidationError
)

logger = logging.getLogger(__name__)

class ProductValidationService:
    """Сервис валидации данных продуктов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def validate_product_data(self, data: Dict) -> Dict[str, Union[bool, List[str]]]:
        """
        Асинхронная валидация данных продукта.
        Включает базовую валидацию и бизнес-правила.
        """
        # Сначала базовая валидация
        validation_result = validate_product_data(data)
        if not validation_result["is_valid"]:
            return validation_result
            
        try:
            # Санитизация только валидных данных
            sanitized_data = sanitize_product_data(data)
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Ошибка санитизации данных: {str(e)}"]
            }
            
        # Дополнительные бизнес-правила можно добавить здесь
        # Например, проверка уникальности ID, специфичные правила для категорий и т.д.
        
        return {
            "is_valid": True,
            "errors": [],
            "sanitized_data": sanitized_data
        }
    
    async def validate_batch_products(self, products: List[Dict]) -> Dict[str, Union[bool, Dict]]:
        """
        Пакетная валидация нескольких продуктов.
        """
        results = {}
        is_valid = True
        
        for product in products:
            product_id = product.get("id", "unknown")
            validation_result = await self.validate_product_data(product)
            results[product_id] = validation_result
            if not validation_result["is_valid"]:
                is_valid = False
        
        return {
            "is_valid": is_valid,
            "results": results
        }
    
    async def validate_product_update(self, old_data: Dict, new_data: Dict) -> Dict[str, Union[bool, List[str]]]:
        """
        Валидация обновления продукта.
        Проверяет корректность изменений.
        """
        # Проверяем новые данные
        validation_result = await self.validate_product_data(new_data)
        if not validation_result["is_valid"]:
            return validation_result
            
        # Проверяем, что ID не изменился
        if old_data["id"] != new_data["id"]:
            return {
                "is_valid": False,
                "errors": ["id: Нельзя изменить ID существующего продукта"]
            }
        
        return validation_result
    
    def validate_title(self, title: str) -> bool:
        """Валидирует заголовок продукта"""
        if not isinstance(title, str):
            return False
            
        # Убираем пробелы
        title = title.strip()
        
        # Проверяем длину
        if len(title) < 3 or len(title) > 100:
            return False
            
        # Проверяем на спецсимволы
        if re.search(r'[<>&;]', title):
            return False
            
        return True
    
    def validate_description(self, description: str) -> bool:
        """Валидирует описание продукта"""
        if not isinstance(description, str):
            return False
            
        # Убираем пробелы
        description = description.strip()
        
        # Проверяем длину
        if len(description) < 10 or len(description) > 5000:
            return False
            
        # Проверяем на спецсимволы
        if re.search(r'[<>&;]', description):
            return False
            
        return True
    
    def validate_categories(self, categories: List[str]) -> bool:
        """Валидирует категории продукта"""
        if not isinstance(categories, list):
            return False
            
        for category in categories:
            if not isinstance(category, str):
                return False
                
            # Убираем пробелы
            category = category.strip()
            
            # Проверяем длину
            if len(category) < 2 or len(category) > 50:
                return False
                
            # Проверяем на спецсимволы
            if re.search(r'[<>&;]', category):
                return False
                
        return True
    
    def validate_attributes(self, attributes: Dict[str, Any]) -> bool:
        """Валидирует атрибуты продукта"""
        if not isinstance(attributes, dict):
            return False
            
        for key, value in attributes.items():
            if not isinstance(key, str):
                return False
                
            # Убираем пробелы
            key = key.strip()
            
            # Проверяем длину ключа
            if len(key) < 2 or len(key) > 50:
                return False
                
            # Проверяем на спецсимволы
            if re.search(r'[<>&;]', key):
                return False
                
            # Проверяем значение
            if not isinstance(value, (str, int, float, bool)):
                return False
                
            if isinstance(value, str):
                # Проверяем длину значения
                if len(value) > 1000:
                    return False
                    
                # Проверяем на спецсимволы
                if re.search(r'[<>&;]', value):
                    return False
                    
        return True 