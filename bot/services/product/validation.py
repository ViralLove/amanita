from typing import Optional, Dict, Any, List, Union
import logging
import re
from bot.validation import ValidationFactory, ValidationResult

logger = logging.getLogger(__name__)

class ProductValidationService:
    """Сервис валидации данных продуктов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def validate_product_data(self, data: Dict, storage_service=None) -> ValidationResult:
        """
        Асинхронная валидация данных продукта.
        Если передан storage_service, дополнительно проверяет существование description_cid в IPFS.
        Включает базовую валидацию и бизнес-правила.
        """
        self.logger.info(f"🔍 [ProductValidationService] Начинаем валидацию данных: {data}")
        
        # Используем единую систему валидации
        validator = ValidationFactory.get_product_validator()
        validation_result = validator.validate(data)
        
        self.logger.info(f"🔍 [ProductValidationService] Результат валидации: {validation_result}")
        
        # Если базовая валидация не прошла, возвращаем результат
        if not validation_result.is_valid:
            return validation_result
            
        # Дополнительная IPFS валидация, если передан storage_service
        if storage_service and "organic_components" in data:
            ipfs_result = await self._validate_with_ipfs(data, storage_service)
            if not ipfs_result.is_valid:
                return ipfs_result
        
        # Дополнительные бизнес-правила можно добавить здесь
        # Например, проверка уникальности ID, специфичные правила для категорий и т.д.
        
        return validation_result
    
    async def _validate_with_ipfs(self, data: Dict, storage_service) -> ValidationResult:
        """
        Дополнительная валидация с использованием IPFS storage_service.
        Проверяет существование CID в IPFS.
        """
        try:
            if "organic_components" in data:
                for component in data["organic_components"]:
                    if "description_cid" in component:
                        cid = component["description_cid"]
                        # Проверяем существование CID в IPFS
                        if not storage_service.is_valid_cid(cid):
                            return ValidationResult.failure(
                                f"CID {cid} не существует в IPFS",
                                field_name="description_cid",
                                field_value=cid,
                                error_code="INVALID_IPFS_CID"
                            )
            
            if "cover_image" in data:
                cover_cid = data["cover_image"]
                if not storage_service.is_valid_cid(cover_cid):
                    return ValidationResult.failure(
                        f"CID {cover_cid} не существует в IPFS",
                        field_name="cover_image",
                        field_value=cover_cid,
                        error_code="INVALID_IPFS_CID"
                    )
            
            return ValidationResult.success()
            
        except Exception as e:
            return ValidationResult.failure(
                f"Ошибка IPFS валидации: {str(e)}",
                field_name="ipfs_validation",
                error_code="IPFS_VALIDATION_ERROR"
            )
    
    async def validate_batch_products(self, products: List[Dict], storage_service=None) -> Dict[str, Union[bool, Dict]]:
        """
        Пакетная валидация нескольких продуктов.
        """
        results = {}
        is_valid = True
        
        for product in products:
            product_id = product.get("id", "unknown")
            validation_result = await self.validate_product_data(product, storage_service)
            results[product_id] = validation_result
            if not validation_result.is_valid:
                is_valid = False
        
        return {
            "is_valid": is_valid,
            "results": results
        }
    
    async def validate_product_update(self, old_data: Dict, new_data: Dict, storage_service=None) -> ValidationResult:
        """
        Валидация обновления продукта.
        Проверяет корректность изменений.
        """
        # Проверяем новые данные
        validation_result = await self.validate_product_data(new_data, storage_service)
        if not validation_result.is_valid:
            return validation_result
            
        # Проверяем, что ID не изменился
        if old_data["id"] != new_data["id"]:
            return ValidationResult.failure(
                "Нельзя изменить ID существующего продукта",
                field_name="id",
                field_value=new_data["id"],
                error_code="ID_CHANGE_NOT_ALLOWED"
            )
        
        return validation_result 