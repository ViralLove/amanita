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
        self.logger.info(f"🔍 [ProductValidationService] Начинаем валидацию данных: {data}")
        validation_result = validate_product_data(data)
        self.logger.info(f"🔍 [ProductValidationService] Результат валидации: {validation_result}")
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
    
    async def validate_product_data_with_ipfs(self, data: Dict, storage_service) -> Dict[str, Union[bool, List[str]]]:
        """
        Асинхронная валидация данных продукта с проверкой существования в IPFS.
        Включает базовую валидацию, проверку IPFS и бизнес-правила.
        """
        # Сначала базовая валидация с проверкой IPFS
        self.logger.info(f"🔍 [ProductValidationService] Начинаем валидацию данных с IPFS: {data}")
        validation_result = await validate_product_data_with_ipfs(data, storage_service)
        self.logger.info(f"🔍 [ProductValidationService] Результат валидации с IPFS: {validation_result}")
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
    
    def validate_organic_components(self, components: List[Dict]) -> bool:
        """Валидирует список органических компонентов"""
        if not isinstance(components, list):
            return False
            
        if not components:
            return False
            
        # Проверяем каждый компонент
        for component in components:
            if not isinstance(component, dict):
                return False
                
            # Проверяем обязательные поля
            required_fields = ["biounit_id", "description_cid", "proportion"]
            for field in required_fields:
                if field not in component:
                    return False
                if not component[field] or not str(component[field]).strip():
                    return False
            
            # Проверяем формат пропорции
            proportion = str(component["proportion"])
            proportion_pattern = r'^(\d+(?:\.\d+)?)(%|g|ml|kg|l|oz|lb|fl_oz)$'
            if not re.match(proportion_pattern, proportion):
                return False
        
        # Проверяем уникальность biounit_id
        biounit_ids = [comp["biounit_id"] for comp in components]
        if len(biounit_ids) != len(set(biounit_ids)):
            return False
        
        # Проверяем пропорции
        return self._validate_component_proportions(components)
    
    def _validate_component_proportions(self, components: List[Dict]) -> bool:
        """Валидирует корректность пропорций компонентов"""
        if not components:
            return False
        
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
            return False
        
        # Проверяем, что все компоненты имеют одинаковый тип
        for component in components:
            proportion = str(component["proportion"])
            if proportion_type == 'percentage' and not proportion.endswith('%'):
                return False
            elif proportion_type == 'weight' and not any(proportion.endswith(unit) for unit in ['g', 'kg', 'oz', 'lb']):
                return False
            elif proportion_type == 'volume' and not any(proportion.endswith(unit) for unit in ['ml', 'l', 'fl_oz']):
                return False
        
        # Для процентных пропорций проверяем, что сумма = 100%
        if proportion_type == 'percentage':
            total_percentage = 0
            for component in components:
                proportion_value = float(str(component["proportion"]).rstrip('%'))
                total_percentage += proportion_value
            
            if abs(total_percentage - 100.0) > 0.01:  # Допуск 0.01%
                return False
        
        # Для весовых/объемных пропорций проверяем, что все > 0
        elif proportion_type in ['weight', 'volume']:
            for component in components:
                proportion_value = float(str(component["proportion"])[:-2] if str(component["proportion"])[-2:].isalpha() else str(component["proportion"])[:-1])
                if proportion_value <= 0:
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