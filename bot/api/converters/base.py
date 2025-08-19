"""
Базовый интерфейс для конвертеров API ↔ Service моделей.

Этот модуль определяет абстрактный базовый класс для всех конвертеров,
обеспечивая единообразный интерфейс и типобезопасность.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Dict, Any

# Type variables для Generic типов
T_API = TypeVar('T_API')      # API модель (Pydantic)
T_SERVICE = TypeVar('T_SERVICE')  # Service модель (dataclass)

class BaseConverter(ABC, Generic[T_API, T_SERVICE]):
    """
    Базовый интерфейс для конвертеров между API и Service моделями.
    
    Этот абстрактный класс определяет стандартный интерфейс для всех конвертеров,
    обеспечивая типобезопасность и единообразие API.
    
    Generic типы:
    - T_API: Тип API модели (обычно Pydantic BaseModel)
    - T_SERVICE: Тип Service модели (обычно dataclass)
    """
    
    @abstractmethod
    def api_to_service(self, api_model: T_API) -> T_SERVICE:
        """
        Конвертирует API модель в Service модель.
        
        Args:
            api_model: Модель API (Pydantic)
            
        Returns:
            T_SERVICE: Модель Service (dataclass)
            
        Raises:
            ValueError: При ошибке конвертации
        """
        pass
    
    @abstractmethod
    def service_to_api(self, service_model: T_SERVICE) -> T_API:
        """
        Конвертирует Service модель в API модель.
        
        Args:
            service_model: Модель Service (dataclass)
            
        Returns:
            T_API: Модель API (Pydantic)
            
        Raises:
            ValueError: При ошибке конвертации
        """
        pass
    
    @abstractmethod
    def api_to_dict(self, api_model: T_API) -> Dict[str, Any]:
        """
        Конвертирует API модель в словарь для передачи в сервис.
        
        Этот метод используется для передачи данных от API к сервисному слою
        без создания промежуточных объектов Service моделей.
        
        Args:
            api_model: Модель API (Pydantic)
            
        Returns:
            Dict[str, Any]: Словарь с данными для сервиса
            
        Raises:
            ValueError: При ошибке конвертации
        """
        pass
    
    @abstractmethod
    def dict_to_api(self, data: Dict[str, Any]) -> T_API:
        """
        Конвертирует словарь в API модель.
        
        Этот метод используется для создания API моделей из данных,
        полученных от сервисного слоя.
        
        Args:
            data: Словарь с данными от сервиса
            
        Returns:
            T_API: Модель API (Pydantic)
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        pass
    
    def validate_api_model(self, api_model: T_API) -> bool:
        """
        Валидирует API модель перед конвертацией.
        
        Args:
            api_model: Модель API для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Для Pydantic моделей валидация происходит автоматически
            # при создании объекта, поэтому просто проверяем, что объект существует
            return api_model is not None
        except Exception:
            return False
    
    def validate_service_model(self, service_model: T_SERVICE) -> bool:
        """
        Валидирует Service модель перед конвертацией.
        
        Args:
            service_model: Модель Service для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Для dataclass моделей проверяем, что объект существует
            return service_model is not None
        except Exception:
            return False
