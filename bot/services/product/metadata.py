from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bot.model.product import Product, PriceInfo
from bot.services.product.cache import ProductCacheService

logger = logging.getLogger(__name__)

class ProductMetadataService:
    """Сервис для работы с метаданными продуктов"""
    
    def __init__(self, storage):
        self.logger = logging.getLogger(__name__)
        self.storage = storage
        self.cache_service = ProductCacheService()
    
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
        return {
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
    
    def process_product_metadata(self, metadata: Dict[str, Any]) -> Optional[Product]:
        """Обрабатывает метаданные продукта и создает объект Product"""
        try:
            self.logger.info(f"[process_product_metadata] Входные данные: type={type(metadata)}, value={repr(metadata)[:500]}")
            
            # Извлекаем базовые поля
            title = metadata.get('title', '')
            product_id = metadata.get('id', '')  # Блокчейн ID будет установлен позже
            alias = metadata.get('id', '')  # Бизнес-идентификатор из метаданных

            cover_image_cid = metadata.get('cover_image', '')
            cover_image_url = self.cache_service.get_image_url_by_cid(cover_image_cid)
            
            if not cover_image_url:
                self.logger.warning(f"Картинка по CID {cover_image_cid} не найдена!")
            
            # Обрабатываем категории
            categories = metadata.get('categories', [])
            
            # Обрабатываем формы
            forms = metadata.get('forms', [])
            # Если есть поле 'form' (единственное число), добавляем его в список форм
            if 'form' in metadata and metadata['form']:
                if not forms:  # Если forms пустой, создаем список с одним элементом
                    forms = [metadata['form']]
                elif metadata['form'] not in forms:  # Если формы нет в списке, добавляем
                    forms.append(metadata['form'])
            
            # Получаем вид
            species = metadata.get('species', '')
            
            # Обрабатываем цены
            prices_data = metadata.get('prices', [])
            prices = [PriceInfo.from_dict(price) for price in prices_data]

            # Обрабатываем organic_components
            organic_components_data = metadata.get('organic_components', [])
            if not organic_components_data:
                self.logger.error("organic_components не может быть пустым!")
                return None
            
            # Создаем OrganicComponent объекты
            from bot.model.organic_component import OrganicComponent
            organic_components = []
            for component_data in organic_components_data:
                try:
                    component = OrganicComponent(
                        biounit_id=component_data['biounit_id'],
                        description_cid=component_data['description_cid'],
                        proportion=component_data['proportion']
                    )
                    organic_components.append(component)
                except Exception as e:
                    self.logger.error(f"Ошибка создания OrganicComponent: {e}")
                    return None
            
            # Создаем объект продукта (неактивный по умолчанию)
            product = Product(
                id=product_id,  # Временно используем ID из метаданных, будет заменен на блокчейн ID
                alias=alias,    # Бизнес-идентификатор из метаданных
                status=0,       # Продукт создается неактивным
                cid=cover_image_cid,
                title=title,
                organic_components=organic_components,
                cover_image_url=cover_image_url or "",
                categories=categories,
                forms=forms,
                species=species,
                prices=prices
            )
            
            self.logger.info(f"Product: {product}")
            return product
            
        except Exception as e:
            self.logger.error(f"Error processing product metadata: {e}")
            return None
    
    def process_description_metadata(self, description_data: Any) -> Optional[Any]:
        """Обрабатывает метаданные описания и создает объект Description"""
        try:
            self.logger.info(f"[process_description_metadata] Входные данные: type={type(description_data)}, value={repr(description_data)[:500]}")
            
            # Если это уже объект, возвращаем его
            if hasattr(description_data, 'biounit_id') and hasattr(description_data, 'description_cid'):
                self.logger.info(f"[process_description_metadata] Данные уже являются объектом OrganicComponent")
                return description_data
            
            # Если это словарь, создаем OrganicComponent из него
            if isinstance(description_data, dict):
                self.logger.info(f"[process_description_metadata] Обрабатываем словарь: keys={list(description_data.keys())}")
                try:
                    from bot.model.organic_component import OrganicComponent
                    component = OrganicComponent(
                        biounit_id=description_data['biounit_id'],
                        description_cid=description_data['description_cid'],
                        proportion=description_data['proportion']
                    )
                    self.logger.info(f"[process_description_metadata] Успешно создан объект OrganicComponent из словаря")
                    return component
                except Exception as e:
                    self.logger.error(f"[process_description_metadata] Ошибка создания OrganicComponent из словаря: {e}")
                    return None
            
            # Если это строка, пытаемся распарсить как JSON
            if isinstance(description_data, str):
                self.logger.info(f"[process_description_metadata] Обрабатываем строку длиной {len(description_data)}")
                import json
                try:
                    parsed_data = json.loads(description_data)
                    self.logger.info(f"[process_description_metadata] JSON успешно распарсен, тип: {type(parsed_data)}")
                    if isinstance(parsed_data, dict):
                        self.logger.info(f"[process_description_metadata] Создаем OrganicComponent из распарсенного JSON")
                        from bot.model.organic_component import OrganicComponent
                        component = OrganicComponent(
                            biounit_id=parsed_data['biounit_id'],
                            description_cid=parsed_data['description_cid'],
                            proportion=parsed_data['proportion']
                        )
                        self.logger.info(f"[process_description_metadata] Успешно создан объект OrganicComponent из JSON строки")
                        return component
                    else:
                        self.logger.error(f"[process_description_metadata] JSON строка не содержит словарь: {type(parsed_data)}")
                        return None
                except json.JSONDecodeError as e:
                    self.logger.error(f"[process_description_metadata] Не удалось распарсить JSON строку: {e}")
                    return None
            
            self.logger.error(f"[process_description_metadata] Неподдерживаемый тип данных для описания: {type(description_data)}")
            return None
            
        except Exception as e:
            self.logger.error(f"[process_description_metadata] Неожиданная ошибка: {e}")
        return None 

    def process_metadata(self, metadata: Dict[str, Any]) -> Optional[Product]:
        """Обрабатывает метаданные и создает объект Product (устаревший метод, используйте process_product_metadata)"""
        self.logger.warning("Используется устаревший метод process_metadata, используйте process_product_metadata")
        return self.process_product_metadata(metadata)
