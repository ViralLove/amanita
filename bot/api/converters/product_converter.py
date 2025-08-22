"""
Конвертер для продуктов между API и Service моделями.

Этот модуль реализует конвертацию между:
- API: ProductUploadIn (Pydantic)
- Service: Product (class)

Использует другие конвертеры для вложенных объектов:
- OrganicComponentConverter для organic_components
- PriceConverter для prices
"""

from typing import Dict, Any, Optional, List
from bot.api.models.product import ProductUploadIn, OrganicComponentAPI, PriceModel
from bot.model.product import Product, OrganicComponent, PriceInfo
from bot.api.converters.base import BaseConverter
from bot.api.converters.organic_component_converter import OrganicComponentConverter
from bot.api.converters.price_converter import PriceConverter
from bot.validation import ValidationFactory, ValidationResult

class ProductConverter(BaseConverter[ProductUploadIn, Product]):
    """
    Конвертер для преобразования между API и Service моделями продуктов.
    
    Поддерживает:
    - ProductUploadIn ↔ Product
    - Dict ↔ Product
    - Валидацию данных через ValidationFactory
    """
    
    def __init__(self):
        """Инициализирует конвертер с зависимыми конвертерами."""
        self.component_converter = OrganicComponentConverter()
        self.price_converter = PriceConverter()
    
    def api_to_service(self, api_model: ProductUploadIn) -> Product:
        """
        Конвертирует API модель в Service модель.
        
        Args:
            api_model: API модель продукта
            
        Returns:
            Product: Service модель продукта
        """
        # Конвертируем organic_components
        organic_components = [
            self.component_converter.api_to_service(component)
            for component in api_model.organic_components
        ]
        
        # Конвертируем цены
        prices = [
            self.price_converter.api_to_service(price)
            for price in api_model.prices
        ]
        
        # Создаем Service модель
        return Product(
            id=api_model.id,
            alias=str(api_model.id),
            status=0,  # По умолчанию неактивный
            cid="",  # Будет установлен позже
            title=api_model.title,
            organic_components=organic_components,
            cover_image_url=api_model.cover_image,
            categories=api_model.categories,
            forms=api_model.forms,
            species=api_model.species,
            prices=prices
        )
    
    def service_to_api(self, service_model: Product) -> ProductUploadIn:
        """
        Конвертирует Service модель в API модель.
        
        Args:
            service_model: Service модель продукта
            
        Returns:
            ProductUploadIn: API модель продукта
        """
        # Конвертируем organic_components
        organic_components = [
            self.component_converter.service_to_api(component)
            for component in service_model.organic_components
        ]
        
        # Конвертируем цены
        prices = [
            self.price_converter.service_to_api(price)
            for price in service_model.prices
        ]
        
        # Создаем API модель
        return ProductUploadIn(
            id=service_model.id,
            title=service_model.title,
            organic_components=organic_components,
            cover_image=service_model.cover_image_url,
            categories=service_model.categories,
            forms=service_model.forms,
            species=service_model.species,
            prices=prices
        )
    
    def dict_to_api(self, data: Dict[str, Any]) -> ProductUploadIn:
        """
        Конвертирует словарь в API модель.
        
        Args:
            data: Словарь с данными продукта
            
        Returns:
            ProductUploadIn: API модель продукта
        """
        # Конвертируем organic_components
        organic_components = [
            self.component_converter.dict_to_api(component_data)
            for component_data in data.get('organic_components', [])
        ]
        
        # Конвертируем цены
        prices = [
            self.price_converter.dict_to_api(price_data)
            for price_data in data.get('prices', [])
        ]
        
        # Создаем API модель
        return ProductUploadIn(
            id=data.get('id', 0),
            title=data.get('title', ''),
            organic_components=organic_components,
            cover_image=data.get('cover_image', ''),
            categories=data.get('categories', []),
            forms=data.get('forms', []),
            species=data.get('species', ''),
            prices=prices
        )
    
    def api_to_dict(self, api_model: ProductUploadIn) -> Dict[str, Any]:
        """
        Конвертирует API модель в словарь.
        
        Args:
            api_model: API модель продукта
            
        Returns:
            Dict[str, Any]: Словарь с данными продукта
        """
        return {
            'id': api_model.id,
            'title': api_model.title,
            'organic_components': [
                self.component_converter.api_to_dict(component)
                for component in api_model.organic_components
            ],
            'cover_image': api_model.cover_image,
            'categories': api_model.categories,
            'forms': api_model.forms,
            'species': api_model.species,
            'prices': [
                self.price_converter.api_to_dict(price)
                for price in api_model.prices
            ]
        }
    
    def validate_api_model(self, api_model: ProductUploadIn) -> bool:
        """
        Валидирует API модель через ValidationFactory.
        
        Args:
            api_model: API модель для валидации
            
        Returns:
            bool: True если модель валидна, False если нет
        """
        try:
            # Конвертируем API модель в словарь для валидации
            data = self.api_to_dict(api_model)
            
            # Валидируем через ValidationFactory
            validator = ValidationFactory.get_product_validator()
            validation_result = validator.validate(data)
            
            return validation_result.is_valid
            
        except Exception:
            return False
    
    def validate_service_model(self, service_model: Product) -> bool:
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
                'id': service_model.id,
                'title': service_model.title,
                'organic_components': [
                    {
                        'biounit_id': component.biounit_id,
                        'description_cid': component.description_cid,
                        'proportion': component.proportion
                    }
                    for component in service_model.organic_components
                ],
                'cover_image': service_model.cover_image_url,
                'categories': service_model.categories,
                'forms': service_model.forms,
                'species': service_model.species,
                'prices': [
                    {
                        'weight': price.weight,
                        'weight_unit': price.weight_unit,
                        'price': str(price.price),
                        'currency': price.currency
                    }
                    for price in service_model.prices
                ]
            }
            
            # Валидируем через ValidationFactory
            validator = ValidationFactory.get_product_validator()
            validation_result = validator.validate(data)
            
            return validation_result.is_valid
            
        except Exception:
            return False
