"""
Мок-сервис каталога для быстрой отладки без загрузки из блокчейна
Использует реальные данные из active_catalog.json
"""
import json
import logging
from pathlib import Path
from typing import List, Optional
from model.product import Product

logger = logging.getLogger(__name__)

class MockCatalogService:
    """Мок-сервис каталога для отладки с реальными данными"""
    
    def __init__(self, catalog_data_path: str = None, mock_data_path: str = None):
        self.catalog_data_path = catalog_data_path or "catalog/active_catalog.json"
        self.mock_data_path = mock_data_path or "tests/mock_catalog_data.json"
        self._products: List[Product] = []
        self._load_catalog_data()
    
    def _load_catalog_data(self):
        """Загружает реальные данные каталога из active_catalog.json"""
        try:
            # Сначала пробуем загрузить реальные данные каталога
            catalog_path = Path(self.catalog_data_path)
            if catalog_path.exists():
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    catalog_data = json.load(f)
                
                logger.info(f"📋 Загружены реальные данные каталога из {self.catalog_data_path}")
                self._load_products_from_catalog(catalog_data)
            else:
                # Fallback на мок-данные
                logger.info(f"📋 Реальные данные не найдены, используем мок-данные")
                self._load_mock_data()
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки данных каталога: {e}")
            # Fallback на мок-данные
            self._load_mock_data()
    
    def _load_products_from_catalog(self, catalog_data: List[dict]):
        """Загружает продукты из реального каталога"""
        for i, product_data in enumerate(catalog_data, 1):
            try:
                # Создаем Product объект с реальными данными
                product = Product.from_dict(product_data)
                # Устанавливаем blockchain_id для мока
                product.blockchain_id = i
                product.cid = f"QmRealCID{i}"
                product.status = 1  # Активный
                
                self._products.append(product)
                logger.info(f"✅ Реальный продукт загружен: {product.business_id} (ID: {i})")
                
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки продукта {product_data.get('business_id', 'unknown')}: {e}")
        
        logger.info(f"🎉 Загружено {len(self._products)} продуктов из реального каталога")
    
    def _load_mock_data(self):
        """Загружает мок-данные из JSON файла (fallback)"""
        try:
            mock_path = Path(self.mock_data_path)
            if mock_path.exists():
                with open(mock_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                logger.info(f"📋 Загружены мок-данные из {self.mock_data_path}")
                
                for i, product_data in enumerate(data.get("products", []), 1):
                    try:
                        # Создаем Product объект с мок-данными
                        product = Product.from_dict(product_data)
                        # Устанавливаем blockchain_id для мока
                        product.blockchain_id = i
                        product.cid = f"QmMockCID{i}"
                        product.status = 1  # Активный
                        
                        self._products.append(product)
                        logger.info(f"✅ Мок-продукт создан: {product.business_id} (ID: {i})")
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка создания мок-продукта {product_data.get('business_id', 'unknown')}: {e}")
                
                logger.info(f"🎉 Загружено {len(self._products)} мок-продуктов")
            else:
                logger.warning(f"⚠️ Мок-данные не найдены по пути {self.mock_data_path}")
                self._products = []
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки мок-данных: {e}")
            self._products = []
    
    def get_all_products(self) -> List[Product]:
        """Возвращает все мок-продукты"""
        logger.info(f"📦 Возвращаем {len(self._products)} мок-продуктов")
        return self._products.copy()
    
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Возвращает продукт по business_id"""
        for product in self._products:
            if product.business_id == product_id:
                logger.info(f"🔍 Найден мок-продукт: {product_id}")
                return product
        
        logger.warning(f"⚠️ Мок-продукт не найден: {product_id}")
        return None
    
    def get_products_count(self) -> int:
        """Возвращает количество продуктов"""
        return len(self._products)
    
    def reload_mock_data(self):
        """Перезагружает мок-данные"""
        logger.info("🔄 Перезагружаем мок-данные...")
        self._products.clear()
        self._load_mock_data()

# Создаем глобальный экземпляр для использования в тестах
mock_catalog_service = MockCatalogService()
