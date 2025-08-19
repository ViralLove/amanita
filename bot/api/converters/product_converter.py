"""
Конвертер для продуктов между API и Service моделями.

Этот модуль реализует конвертацию между:
- API: ProductUploadIn (Pydantic)
- Service: Product (class)

Использует другие конвертеры для вложенных объектов:
- OrganicComponentConverter для organic_components
- PriceConverter для prices
"""

from typing import Dict, Any, List
from .base import BaseConverter
from .organic_component_converter import OrganicComponentConverter
from .price_converter import PriceConverter
from bot.api.models.product import ProductUploadIn
from bot.model.product import Product
from bot.model.organic_component import OrganicComponent
from bot.model.product import PriceInfo


class ProductConverter(BaseConverter[ProductUploadIn, Product]):
    """
    Конвертер для продуктов.
    
    Обеспечивает конвертацию между API моделью ProductUploadIn
    и Service моделью Product с использованием других конвертеров
    для вложенных объектов.
    """
    
    def __init__(self):
        """Инициализирует конвертер с зависимостями"""
        self.component_converter = OrganicComponentConverter()
        self.price_converter = PriceConverter()
    
    def api_to_service(self, api_model: ProductUploadIn) -> Product:
        """
        Конвертирует ProductUploadIn в Product.
        
        Args:
            api_model: API модель продукта
            
        Returns:
            Product: Service модель продукта
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Валидируем входную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Невалидная API модель ProductUploadIn")
            
            # Конвертируем органические компоненты
            organic_components = [
                self.component_converter.api_to_service(comp)
                for comp in api_model.organic_components
            ]
            
            # Конвертируем цены
            prices = [
                self.price_converter.api_to_service(price)
                for price in api_model.prices
            ]
            
            # Создаем Service модель
            service_model = Product(
                id=str(api_model.id),  # API int → Service str
                alias=str(api_model.id),  # Используем id как alias
                status=0,  # По умолчанию неактивен
                cid=str(api_model.id),  # Используем id как CID
                title=api_model.title,
                organic_components=organic_components,
                cover_image_url=api_model.cover_image,
                categories=api_model.categories,
                forms=api_model.forms,
                species=api_model.species,
                prices=prices
            )
            
            # Валидируем созданную модель
            if not self.validate_service_model(service_model):
                raise ValueError("Ошибка валидации созданной Service модели")
            
            return service_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации API → Service: {e}")
    
    def service_to_api(self, service_model: Product) -> ProductUploadIn:
        """
        Конвертирует Product в ProductUploadIn.
        
        Args:
            service_model: Service модель продукта
            
        Returns:
            ProductUploadIn: API модель продукта
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Валидируем входную модель
            if not self.validate_service_model(service_model):
                raise ValueError("Невалидная Service модель Product")
            
            # Конвертируем органические компоненты
            organic_components = [
                self.component_converter.service_to_api(comp)
                for comp in service_model.organic_components
            ]
            
            # Конвертируем цены
            prices = [
                self.price_converter.service_to_api(price)
                for price in service_model.prices
            ]
            
            # Создаем API модель
            api_model = ProductUploadIn(
                id=int(service_model.id),  # Service str → API int
                title=service_model.title,
                organic_components=organic_components,
                cover_image=service_model.cover_image_url,
                categories=service_model.categories,
                forms=service_model.forms,
                species=service_model.species,
                prices=prices,
                seller_address=None  # Не хранится в Service модели
            )
            
            # Валидируем созданную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Ошибка валидации созданной API модели")
            
            return api_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации Service → API: {e}")
    
    def api_to_dict(self, api_model: ProductUploadIn) -> Dict[str, Any]:
        """
        Конвертирует ProductUploadIn в словарь для передачи в сервис.
        
        Args:
            api_model: API модель продукта
            
        Returns:
            Dict[str, Any]: Словарь с данными продукта
            
        Raises:
            ValueError: При ошибке конвертации
        """
        try:
            # Валидируем входную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Невалидная API модель ProductUploadIn")
            
            # Конвертируем органические компоненты
            organic_components = [
                self.component_converter.api_to_dict(comp)
                for comp in api_model.organic_components
            ]
            
            # Конвертируем цены
            prices = [
                self.price_converter.api_to_dict(price)
                for price in api_model.prices
            ]
            
            # Конвертируем в словарь
            return {
                "id": str(api_model.id),  # int → str для сервиса
                "title": api_model.title,
                "organic_components": organic_components,
                "cover_image": api_model.cover_image,
                "categories": api_model.categories,
                "forms": api_model.forms,
                "species": api_model.species,
                "prices": prices,
                "seller_address": api_model.seller_address
            }
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации API → dict: {e}")
    
    def dict_to_api(self, data: Dict[str, Any]) -> ProductUploadIn:
        """
        Конвертирует словарь в ProductUploadIn.
        
        Args:
            data: Словарь с данными продукта
            
        Returns:
            ProductUploadIn: API модель продукта
            
        Raises:
            ValueError: При ошибке конвертации или невалидных данных
        """
        try:
            # Проверяем наличие обязательных полей
            required_fields = ["id", "title", "organic_components", "cover_image", "categories", "forms", "species", "prices"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Отсутствует обязательное поле: {field}")
            
            # Конвертируем органические компоненты
            organic_components = [
                self.component_converter.dict_to_api(comp)
                for comp in data["organic_components"]
            ]
            
            # Конвертируем цены
            prices = [
                self.price_converter.dict_to_api(price)
                for price in data["prices"]
            ]
            
            # Создаем API модель
            api_model = ProductUploadIn(
                id=int(data["id"]),  # str → int для API
                title=data["title"],
                organic_components=organic_components,
                cover_image=data["cover_image"],
                categories=data["categories"],
                forms=data["forms"],
                species=data["species"],
                prices=prices,
                seller_address=data.get("seller_address")
            )
            
            # Валидируем созданную модель
            if not self.validate_api_model(api_model):
                raise ValueError("Ошибка валидации созданной API модели")
            
            return api_model
            
        except Exception as e:
            raise ValueError(f"Ошибка конвертации dict → API: {e}")
    
    def validate_api_model(self, api_model: ProductUploadIn) -> bool:
        """
        Расширенная валидация API модели.
        
        Args:
            api_model: API модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Базовая валидация
            if not super().validate_api_model(api_model):
                return False
            
            # Дополнительная валидация полей
            if api_model.id <= 0:
                return False
            
            if not api_model.title or not api_model.title.strip():
                return False
            
            if not api_model.organic_components or len(api_model.organic_components) == 0:
                return False
            
            if not api_model.cover_image or not api_model.cover_image.strip():
                return False
            
            if not api_model.categories or len(api_model.categories) == 0:
                return False
            
            if not api_model.forms or len(api_model.forms) == 0:
                return False
            
            if not api_model.species or not api_model.species.strip():
                return False
            
            if not api_model.prices or len(api_model.prices) == 0:
                return False
            
            # Валидируем вложенные объекты
            for component in api_model.organic_components:
                if not self.component_converter.validate_api_model(component):
                    return False
            
            for price in api_model.prices:
                if not self.price_converter.validate_api_model(price):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def validate_service_model(self, service_model: Product) -> bool:
        """
        Расширенная валидация Service модели.
        
        Args:
            service_model: Service модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Базовая валидация
            if not super().validate_service_model(service_model):
                return False
            
            # Дополнительная валидация полей
            if not service_model.id:
                return False
            
            if not service_model.title or not service_model.title.strip():
                return False
            
            if not service_model.organic_components or len(service_model.organic_components) == 0:
                return False
            
            if not service_model.cover_image_url or not service_model.cover_image_url.strip():
                return False
            
            if not service_model.categories or len(service_model.categories) == 0:
                return False
            
            if not service_model.forms or len(service_model.forms) == 0:
                return False
            
            if not service_model.species or not service_model.species.strip():
                return False
            
            if not service_model.prices or len(service_model.prices) == 0:
                return False
            
            # Валидируем вложенные объекты
            for component in service_model.organic_components:
                if not self.component_converter.validate_service_model(component):
                    return False
            
            for price in service_model.prices:
                if not self.price_converter.validate_service_model(price):
                    return False
            
            return True
            
        except Exception:
            return False
