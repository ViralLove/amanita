"""
Конвертер для цен между API и Service моделями.

Этот модуль реализует конвертацию между:
- API: PriceModel (Pydantic)
- Service: PriceInfo (class)
"""

from typing import Dict, Any, Optional, Union
from decimal import Decimal
from .base import BaseConverter
from api.models.product import PriceModel
from model.product import PriceInfo
from validation import ValidationFactory, ValidationResult


class PriceConverter(BaseConverter[PriceModel, PriceInfo]):
    """
    Конвертер для цен.
    
    Обеспечивает конвертацию между API моделью PriceModel
    и Service моделью PriceInfo с сохранением валидации.
    """
    
    def api_to_service(self, api_model: PriceModel) -> PriceInfo:
        """
        Конвертирует PriceModel в PriceInfo.
        
        Args:
            api_model: API модель цены
            
        Returns:
            PriceInfo: Service модель цены
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Валидируем входную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Невалидная API модель PriceModel")
            
            # Подготавливаем параметры для PriceInfo
            kwargs = {
                "price": api_model.price,
                "currency": api_model.currency,
                "form": api_model.form
            }
            
            # Добавляем количество (quantity/unit)
            if api_model.quantity is not None:
                kwargs["quantity"] = api_model.quantity
                kwargs["unit"] = api_model.unit
            
            # Создаем Service модель
            service_model = PriceInfo(**kwargs)
            
            # Валидируем созданную модель
            if not self.validate_service_model(service_model):
                raise ValueError("Ошибка валидации созданной Service модели")
            
            return service_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации API → Service: {e}")
    
    def service_to_api(self, service_model: PriceInfo) -> PriceModel:
        """
        Конвертирует PriceInfo в PriceModel.
        
        Args:
            service_model: Service модель цены
            
        Returns:
            PriceModel: API модель цены
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Валидируем входную модель
            if not self.validate_service_model(service_model):
                raise ValueError("Невалидная Service модель PriceInfo")
            
            # Подготавливаем параметры для PriceModel
            kwargs = {
                "price": service_model.price,
                "currency": service_model.currency,
                "form": service_model.form
            }
            
            # Добавляем количество (quantity/unit)
            if service_model.is_quantity_based:
                kwargs["quantity"] = str(service_model.quantity)
                kwargs["unit"] = service_model.unit
            
            # Создаем API модель
            api_model = PriceModel(**kwargs)
            
            # Валидируем созданную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Ошибка валидации созданной API модели")
            
            return api_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации Service → API: {e}")
    
    def api_to_dict(self, api_model: PriceModel) -> Dict[str, Any]:
        """
        Конвертирует PriceModel в словарь для передачи в сервис.
        
        Args:
            api_model: API модель цены
            
        Returns:
            Dict[str, Any]: Словарь с данными цены
            
        Raises:
            ValueError: При ошибке конвертации
        """
        try:
            # Валидируем входную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Невалидная API модель PriceModel")
            
            # Конвертируем в словарь
            result = {
                "price": api_model.price,
                "currency": api_model.currency,
                "form": api_model.form
            }
            
            # Добавляем количество (quantity/unit)
            if api_model.quantity is not None:
                result["quantity"] = api_model.quantity
                result["unit"] = api_model.unit
            
            return result
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации API → dict: {e}")
    
    def dict_to_api(self, data: Dict[str, Any]) -> PriceModel:
        """
        Конвертирует словарь в PriceModel.
        
        Args:
            data: Словарь с данными цены
            
        Returns:
            PriceModel: API модель цены
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Проверяем наличие обязательных полей
            if "price" not in data:
                raise ValueError("Отсутствует обязательное поле: price")
            
            # Подготавливаем параметры для PriceModel
            kwargs = {
                "price": data["price"],
                "currency": data.get("currency", "EUR"),
                "form": data.get("form")
            }
            
            # Добавляем количество (quantity/unit)
            if "quantity" in data:
                kwargs["quantity"] = data["quantity"]
                kwargs["unit"] = data.get("unit")
            
            # Создаем API модель
            api_model = PriceModel(**kwargs)
            
            # Валидируем созданную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Ошибка валидации созданной API модели")
            
            return api_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации dict → API: {e}")
    
    def validate_api_model(self, api_model: PriceModel) -> bool:
        """
        Валидирует API модель через ValidationFactory.
        
        Args:
            api_model: API модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Валидируем цену и валюту через PriceValidator
            price_validator = ValidationFactory.get_price_validator()
            price_result = price_validator.validate_with_currency(api_model.price, api_model.currency)
            if not price_result.is_valid:
                return False
            
            # Проверяем, что указано количество
            has_quantity = api_model.quantity is not None
            if not has_quantity:
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_service_model(self, service_model: PriceInfo) -> bool:
        """
        Валидирует Service модель через ValidationFactory.
        
        Args:
            service_model: Service модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Валидируем цену и валюту через PriceValidator
            price_validator = ValidationFactory.get_price_validator()
            price_result = price_validator.validate_with_currency(service_model.price, service_model.currency)
            if not price_result.is_valid:
                return False
            
            # Проверяем, что указано количество
            if not service_model.is_quantity_based:
                return False
            
            return True
            
        except Exception:
            return False
