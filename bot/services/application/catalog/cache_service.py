"""
Сервис для кэширования данных каталога.
Содержит логику кэширования продуктов, изображений и других данных.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from services.product.cache import ProductCacheService

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Запись кэша с данными и метаинформацией"""
    data: Any
    timestamp: float
    ttl: int  # Time to live в секундах
    
    def is_expired(self) -> bool:
        """Проверяет, истек ли срок действия записи"""
        return time.time() - self.timestamp > self.ttl


class CacheService:
    """Сервис для кэширования данных каталога"""
    
    def __init__(self, product_cache_service: ProductCacheService = None):
        """
        Инициализация сервиса кэширования
        
        Args:
            product_cache_service: Сервис кэширования продуктов
        """
        self.logger = logging.getLogger(__name__)
        self.product_cache_service = product_cache_service or ProductCacheService()
        
        # Локальный кэш для быстрого доступа
        self.local_cache: Dict[str, CacheEntry] = {}
        
        # Настройки TTL по умолчанию
        self.default_ttl = {
            'catalog': 300,      # 5 минут
            'product': 600,      # 10 минут
            'image': 1800,       # 30 минут
            'navigation': 3600   # 1 час
        }
        
        self.logger.info("[CacheService] Инициализирован")
    
    async def get_catalog_cache(self, cache_key: str = "catalog") -> Optional[List[Any]]:
        """
        Получает кэшированный каталог
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            Optional[List[Any]]: Кэшированный каталог или None
        """
        try:
            self.logger.debug(f"[CacheService] Получение кэша каталога: {cache_key}")
            
            # Проверяем локальный кэш
            if cache_key in self.local_cache:
                entry = self.local_cache[cache_key]
                if not entry.is_expired():
                    self.logger.debug(f"[CacheService] Каталог найден в локальном кэше: {cache_key}")
                    return entry.data
                else:
                    # Удаляем истекшую запись
                    del self.local_cache[cache_key]
            
            # Проверяем кэш продуктов
            cached_products = await self.product_cache_service.get_catalog_cache()
            if cached_products:
                # Сохраняем в локальный кэш
                await self.set_catalog_cache(cached_products, cache_key)
                return cached_products
            
            return None
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка получения кэша каталога: {e}")
            return None
    
    async def set_catalog_cache(self, catalog_data: List[Any], cache_key: str = "catalog") -> bool:
        """
        Сохраняет каталог в кэш
        
        Args:
            catalog_data: Данные каталога
            cache_key: Ключ кэша
            
        Returns:
            bool: True если сохранение прошло успешно
        """
        try:
            self.logger.debug(f"[CacheService] Сохранение каталога в кэш: {cache_key}")
            
            ttl = self.default_ttl.get('catalog', 300)
            entry = CacheEntry(
                data=catalog_data,
                timestamp=time.time(),
                ttl=ttl
            )
            
            # Сохраняем в локальный кэш
            self.local_cache[cache_key] = entry
            
            # Сохраняем в кэш продуктов
            await self.product_cache_service.set_catalog_cache(catalog_data)
            
            self.logger.debug(f"[CacheService] Каталог сохранен в кэш: {cache_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка сохранения кэша каталога: {e}")
            return False
    
    async def get_product_cache(self, product_id: str) -> Optional[Any]:
        """
        Получает кэшированный продукт
        
        Args:
            product_id: ID продукта
            
        Returns:
            Optional[Any]: Кэшированный продукт или None
        """
        try:
            cache_key = f"product_{product_id}"
            self.logger.debug(f"[CacheService] Получение кэша продукта: {product_id}")
            
            # Проверяем локальный кэш
            if cache_key in self.local_cache:
                entry = self.local_cache[cache_key]
                if not entry.is_expired():
                    self.logger.debug(f"[CacheService] Продукт найден в локальном кэше: {product_id}")
                    return entry.data
                else:
                    # Удаляем истекшую запись
                    del self.local_cache[cache_key]
            
            # Проверяем кэш продуктов
            cached_product = await self.product_cache_service.get_product_cache(product_id)
            if cached_product:
                # Сохраняем в локальный кэш
                await self.set_product_cache(product_id, cached_product)
                return cached_product
            
            return None
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка получения кэша продукта: {e}")
            return None
    
    async def set_product_cache(self, product_id: str, product_data: Any) -> bool:
        """
        Сохраняет продукт в кэш
        
        Args:
            product_id: ID продукта
            product_data: Данные продукта
            
        Returns:
            bool: True если сохранение прошло успешно
        """
        try:
            cache_key = f"product_{product_id}"
            self.logger.debug(f"[CacheService] Сохранение продукта в кэш: {product_id}")
            
            ttl = self.default_ttl.get('product', 600)
            entry = CacheEntry(
                data=product_data,
                timestamp=time.time(),
                ttl=ttl
            )
            
            # Сохраняем в локальный кэш
            self.local_cache[cache_key] = entry
            
            # Сохраняем в кэш продуктов
            await self.product_cache_service.set_product_cache(product_id, product_data)
            
            self.logger.debug(f"[CacheService] Продукт сохранен в кэш: {product_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка сохранения кэша продукта: {e}")
            return False
    
    async def get_image_cache(self, image_url: str) -> Optional[str]:
        """
        Получает кэшированное изображение
        
        Args:
            image_url: URL изображения
            
        Returns:
            Optional[str]: Путь к кэшированному изображению или None
        """
        try:
            cache_key = f"image_{hash(image_url)}"
            self.logger.debug(f"[CacheService] Получение кэша изображения: {image_url}")
            
            # Проверяем локальный кэш
            if cache_key in self.local_cache:
                entry = self.local_cache[cache_key]
                if not entry.is_expired():
                    self.logger.debug(f"[CacheService] Изображение найдено в локальном кэше: {image_url}")
                    return entry.data
                else:
                    # Удаляем истекшую запись
                    del self.local_cache[cache_key]
            
            # Проверяем кэш изображений
            cached_image = await self.product_cache_service.get_image_cache(image_url)
            if cached_image:
                # Сохраняем в локальный кэш
                await self.set_image_cache(image_url, cached_image)
                return cached_image
            
            return None
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка получения кэша изображения: {e}")
            return None
    
    async def set_image_cache(self, image_url: str, image_path: str) -> bool:
        """
        Сохраняет изображение в кэш
        
        Args:
            image_url: URL изображения
            image_path: Путь к изображению
            
        Returns:
            bool: True если сохранение прошло успешно
        """
        try:
            cache_key = f"image_{hash(image_url)}"
            self.logger.debug(f"[CacheService] Сохранение изображения в кэш: {image_url}")
            
            ttl = self.default_ttl.get('image', 1800)
            entry = CacheEntry(
                data=image_path,
                timestamp=time.time(),
                ttl=ttl
            )
            
            # Сохраняем в локальный кэш
            self.local_cache[cache_key] = entry
            
            # Сохраняем в кэш изображений
            await self.product_cache_service.set_image_cache(image_url, image_path)
            
            self.logger.debug(f"[CacheService] Изображение сохранено в кэш: {image_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка сохранения кэша изображения: {e}")
            return False
    
    def invalidate_cache(self, cache_key: str) -> bool:
        """
        Инвалидирует запись кэша
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            bool: True если инвалидация прошла успешно
        """
        try:
            if cache_key in self.local_cache:
                del self.local_cache[cache_key]
                self.logger.debug(f"[CacheService] Кэш инвалидирован: {cache_key}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка инвалидации кэша: {e}")
            return False
    
    def clear_expired_cache(self) -> int:
        """
        Очищает истекшие записи кэша
        
        Returns:
            int: Количество удаленных записей
        """
        try:
            expired_keys = []
            for key, entry in self.local_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.local_cache[key]
            
            if expired_keys:
                self.logger.info(f"[CacheService] Очищено {len(expired_keys)} истекших записей кэша")
            
            return len(expired_keys)
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка очистки истекшего кэша: {e}")
            return 0
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику кэша
        
        Returns:
            Dict[str, Any]: Статистика кэша
        """
        try:
            total_entries = len(self.local_cache)
            expired_entries = sum(1 for entry in self.local_cache.values() if entry.is_expired())
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'cache_keys': list(self.local_cache.keys())
            }
            
        except Exception as e:
            self.logger.error(f"[CacheService] Ошибка получения статистики кэша: {e}")
            return {}
