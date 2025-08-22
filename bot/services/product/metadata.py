from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bot.validation import ValidationFactory, ValidationResult

logger = logging.getLogger(__name__)

class ProductMetadataService:
    """Сервис для работы с метаданными продуктов (валидация и парсинг JSON)"""
    
    def __init__(self, storage):
        self.logger = logging.getLogger(__name__)
        self.storage = storage
    
    def create_product_metadata(
        self,
        title: str,
        description: str,
        price: int,
        cover_image_cid: str,
        gallery_cids: List[str],
        video_cid: str,
        categories: List[str],
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создает метаданные продукта"""
        # Валидируем входные данные через ValidationFactory
        metadata_data = {
            "title": title,
            "description": description,
            "price": str(price),
            "cover_image": f"ar://{cover_image_cid}" if cover_image_cid else "",
            "gallery": [f"ar://{c}" for c in gallery_cids or []],
            "video": f"ar://{video_cid}" if video_cid else "",
            "categories": categories or [],
            "attributes": attributes or {},
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Валидируем метаданные через ValidationFactory
        validator = ValidationFactory.get_product_validator()
        validation_result = validator.validate(metadata_data)
        
        if not validation_result.is_valid:
            self.logger.error(f"❌ [ProductMetadataService] Валидация метаданных не прошла: {validation_result.error_message}")
            raise ValueError(f"Invalid metadata: {validation_result.error_message}")
        
        self.logger.info(f"✅ [ProductMetadataService] Метаданные успешно валидированы")
        return metadata_data
    
    def validate_and_parse_metadata(self, metadata: Dict[str, Any]) -> ValidationResult:
        """
        Валидирует и парсит метаданные продукта.
        
        Args:
            metadata: Словарь с метаданными продукта
            
        Returns:
            ValidationResult: Результат валидации с дополнительной информацией
        """
        try:
            self.logger.info(f"[validate_and_parse_metadata] Входные данные: type={type(metadata)}, value={repr(metadata)[:500]}")
            
            # Валидируем метаданные через ValidationFactory
            validator = ValidationFactory.get_product_validator()
            validation_result = validator.validate(metadata)
            
            if not validation_result.is_valid:
                self.logger.error(f"❌ [ProductMetadataService] Валидация метаданных не прошла: {validation_result.error_message}")
                return validation_result
            
            self.logger.info(f"✅ [ProductMetadataService] Метаданные успешно валидированы")
            
            # Дополнительная проверка обязательных полей
            required_fields = ['title', 'organic_components', 'prices']
            missing_fields = []
            
            for field in required_fields:
                if not metadata.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                error_message = f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
                self.logger.error(f"❌ [ProductMetadataService] {error_message}")
                return ValidationResult(
                    is_valid=False,
                    error_message=error_message,
                    field_name=missing_fields[0],
                    field_value=None,
                    error_code="MISSING_REQUIRED_FIELD",
                    suggestions=[]
                )
            
            # Проверяем корректность organic_components
            organic_components = metadata.get('organic_components', [])
            if not isinstance(organic_components, list) or len(organic_components) == 0:
                error_message = "organic_components должен быть непустым списком"
                self.logger.error(f"❌ [ProductMetadataService] {error_message}")
                return ValidationResult(
                    is_valid=False,
                    error_message=error_message,
                    field_name="organic_components",
                    field_value=organic_components,
                    error_code="INVALID_ORGANIC_COMPONENTS",
                    suggestions=[]
                )
            
            # Проверяем корректность prices
            prices = metadata.get('prices', [])
            if not isinstance(prices, list) or len(prices) == 0:
                error_message = "prices должен быть непустым списком"
                self.logger.error(f"❌ [ProductMetadataService] {error_message}")
                return ValidationResult(
                    is_valid=False,
                    error_message=error_message,
                    field_name="prices",
                    field_value=prices,
                    error_code="INVALID_PRICES",
                    suggestions=[]
                )
            
            self.logger.info(f"✅ [ProductMetadataService] Метаданные полностью валидны")
            return ValidationResult(
                is_valid=True,
                error_message=None,
                field_name=None,
                field_value=metadata,
                error_code="VALID",
                suggestions=[]
            )
            
        except Exception as e:
            error_message = f"Ошибка валидации метаданных: {str(e)}"
            self.logger.error(f"❌ [ProductMetadataService] {error_message}")
            return ValidationResult(
                is_valid=False,
                error_message=error_message,
                field_name=None,
                field_value=None,
                error_code="VALIDATION_ERROR",
                suggestions=[]
            )
