"""
Конвертер для органических компонентов между API и Service моделями.

Этот модуль реализует конвертацию между:
- API: OrganicComponentAPI (Pydantic)
- Service: OrganicComponent (dataclass)
"""

from typing import Dict, Any
from .base import BaseConverter
from bot.api.models.product import OrganicComponentAPI
from bot.model.organic_component import OrganicComponent
from bot.validation import ValidationFactory, ValidationResult


class OrganicComponentConverter(BaseConverter[OrganicComponentAPI, OrganicComponent]):
    """
    Конвертер для органических компонентов.
    
    Обеспечивает конвертацию между API моделью OrganicComponentAPI
    и Service моделью OrganicComponent с сохранением валидации.
    """
    
    def api_to_service(self, api_model: OrganicComponentAPI) -> OrganicComponent:
        """
        Конвертирует OrganicComponentAPI в OrganicComponent.
        
        Args:
            api_model: API модель органического компонента
            
        Returns:
            OrganicComponent: Service модель органического компонента
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Валидируем входную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Невалидная API модель OrganicComponentAPI")
            
            # Создаем Service модель
            service_model = OrganicComponent(
                biounit_id=api_model.biounit_id,
                description_cid=api_model.description_cid,
                proportion=api_model.proportion
            )
            
            # Валидируем созданную модель
            if not self.validate_service_model(service_model):
                raise ValueError("Ошибка валидации созданной Service модели")
            
            return service_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации API → Service: {e}")
    
    def service_to_api(self, service_model: OrganicComponent) -> OrganicComponentAPI:
        """
        Конвертирует OrganicComponent в OrganicComponentAPI.
        
        Args:
            service_model: Service модель органического компонента
            
        Returns:
            OrganicComponentAPI: API модель органического компонента
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Валидируем входную модель
            if not self.validate_service_model(service_model):
                raise ValueError("Невалидная Service модель OrganicComponent")
            
            # Создаем API модель
            api_model = OrganicComponentAPI(
                biounit_id=service_model.biounit_id,
                description_cid=service_model.description_cid,
                proportion=service_model.proportion
            )
            
            # Валидируем созданную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Ошибка валидации созданной API модели")
            
            return api_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации Service → API: {e}")
    
    def api_to_dict(self, api_model: OrganicComponentAPI) -> Dict[str, Any]:
        """
        Конвертирует OrganicComponentAPI в словарь для передачи в сервис.
        
        Args:
            api_model: API модель органического компонента
            
        Returns:
            Dict[str, Any]: Словарь с данными компонента
            
        Raises:
            ValueError: При ошибке конвертации
        """
        try:
            # Валидируем входную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Невалидная API модель OrganicComponentAPI")
            
            # Конвертируем в словарь
            return {
                "biounit_id": api_model.biounit_id,
                "description_cid": api_model.description_cid,
                "proportion": api_model.proportion
            }
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации API → dict: {e}")
    
    def dict_to_api(self, data: Dict[str, Any]) -> OrganicComponentAPI:
        """
        Конвертирует словарь в OrganicComponentAPI.
        
        Args:
            data: Словарь с данными компонента
            
        Returns:
            OrganicComponentAPI: API модель органического компонента
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Проверяем наличие обязательных полей
            required_fields = ["biounit_id", "description_cid", "proportion"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Отсутствует обязательное поле: {field}")
            
            # Создаем API модель
            api_model = OrganicComponentAPI(
                biounit_id=data["biounit_id"],
                description_cid=data["description_cid"],
                proportion=data["proportion"]
            )
            
            # Валидируем созданную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Ошибка валидации созданной API модели")
            
            return api_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации dict → API: {e}")
    
    def validate_api_model(self, api_model: OrganicComponentAPI) -> bool:
        """
        Валидирует API модель через ValidationFactory.
        
        Args:
            api_model: API модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Конвертируем API модель в словарь для валидации
            data = {
                'biounit_id': api_model.biounit_id,
                'description_cid': api_model.description_cid,
                'proportion': api_model.proportion
            }
            
            # Валидируем biounit_id (обязательное поле)
            if not data['biounit_id'] or not data['biounit_id'].strip():
                return False
            
            # Валидируем description_cid через CIDValidator
            cid_validator = ValidationFactory.get_cid_validator()
            cid_result = cid_validator.validate(data['description_cid'])
            if not cid_result.is_valid:
                return False
            
            # Валидируем proportion через ProportionValidator
            proportion_validator = ValidationFactory.get_proportion_validator()
            proportion_result = proportion_validator.validate(data['proportion'])
            if not proportion_result.is_valid:
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_service_model(self, service_model: OrganicComponent) -> bool:
        """
        Валидирует Service модель через ValidationFactory.
        
        Args:
            service_model: Service модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Конвертируем Service модель в словарь для валидации
            data = {
                'biounit_id': service_model.biounit_id,
                'description_cid': service_model.description_cid,
                'proportion': service_model.proportion
            }
            
            # Валидируем biounit_id (обязательное поле)
            if not data['biounit_id'] or not data['biounit_id'].strip():
                return False
            
            # Валидируем description_cid через CIDValidator
            cid_validator = ValidationFactory.get_cid_validator()
            cid_result = cid_validator.validate(data['description_cid'])
            if not cid_result.is_valid:
                return False
            
            # Валидируем proportion через ProportionValidator
            proportion_validator = ValidationFactory.get_proportion_validator()
            proportion_result = proportion_validator.validate(data['proportion'])
            if not proportion_result.is_valid:
                return False
            
            return True
            
        except Exception:
            return False
