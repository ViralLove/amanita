"""
CacheManager - Централизованное управление кэшами

Обеспечивает единый интерфейс для управления всеми типами кэшей:
- TranslationCacheService - кэш переводов
- ProductCacheService - кэш продуктов  
- CacheService - кэш каталога
- SecurePinataCache - кэш IPFS файлов

Предоставляет централизованную статистику, мониторинг и управление.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class CacheType(Enum):
    """Типы кэшей в системе"""
    TRANSLATION = "translation"
    PRODUCT = "product"
    CATALOG = "catalog"
    IPFS = "ipfs"
    IMAGE = "image"
    NAVIGATION = "navigation"

@dataclass
class CacheStats:
    """Статистика кэша"""
    cache_type: CacheType
    total_requests: int
    hits: int
    misses: int
    hit_rate: float
    size: int
    memory_usage: int
    last_cleanup: Optional[datetime]

@dataclass
class CacheConfig:
    """Конфигурация кэша"""
    cache_type: CacheType
    enabled: bool
    ttl: int
    max_size: int
    cleanup_interval: int
    auto_cleanup: bool

class CacheManager:
    """Централизованный менеджер кэшей"""
    
    def __init__(self):
        """Инициализация менеджера кэшей"""
        self.logger = logging.getLogger(__name__)
        
        # Регистр кэш-сервисов
        self.cache_services: Dict[CacheType, Any] = {}
        
        # Конфигурация кэшей
        self.cache_configs: Dict[CacheType, CacheConfig] = {}
        
        # Глобальная статистика
        self.global_stats = {
            'total_requests': 0,
            'total_hits': 0,
            'total_misses': 0,
            'cache_services_count': 0,
            'last_cleanup': None
        }
        
        # Инициализируем конфигурации по умолчанию
        self._init_default_configs()
        
        self.logger.info("[CacheManager] Инициализирован")
    
    def register_cache_service(self, cache_type: CacheType, service: Any) -> bool:
        """
        Регистрирует кэш-сервис
        
        Args:
            cache_type: Тип кэша
            service: Экземпляр кэш-сервиса
            
        Returns:
            True если успешно зарегистрирован
        """
        try:
            self.cache_services[cache_type] = service
            self.global_stats['cache_services_count'] = len(self.cache_services)
            self.logger.info(f"[CacheManager] Зарегистрирован кэш-сервис: {cache_type.value}")
            return True
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка регистрации кэш-сервиса {cache_type.value}: {e}")
            return False
    
    def get(self, key: str, cache_type: CacheType, **kwargs) -> Optional[Any]:
        """
        Получает данные из кэша
        
        Args:
            key: Ключ кэша
            cache_type: Тип кэша
            **kwargs: Дополнительные параметры
            
        Returns:
            Кэшированные данные или None
        """
        try:
            if not self._is_cache_enabled(cache_type):
                return None
            
            service = self.cache_services.get(cache_type)
            if not service:
                self.logger.warning(f"[CacheManager] Кэш-сервис не зарегистрирован: {cache_type.value}")
                return None
            
            # Вызываем метод get сервиса (приоритет стандартному интерфейсу)
            if hasattr(service, 'get'):
                result = service.get(key, **kwargs)
            elif hasattr(service, 'get_cached_item'):
                result = service.get_cached_item(key, cache_type.value)
            else:
                self.logger.error(f"[CacheManager] Неподдерживаемый интерфейс кэш-сервиса: {cache_type.value}")
                return None
            
            # Обновляем статистику
            self._update_stats(cache_type, result is not None)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка получения из кэша {cache_type.value}: {e}")
            return None
    
    def set(self, key: str, data: Any, cache_type: CacheType, **kwargs) -> bool:
        """
        Сохраняет данные в кэш
        
        Args:
            key: Ключ кэша
            data: Данные для кэширования
            cache_type: Тип кэша
            **kwargs: Дополнительные параметры
            
        Returns:
            True если успешно сохранено
        """
        try:
            if not self._is_cache_enabled(cache_type):
                return False
            
            service = self.cache_services.get(cache_type)
            if not service:
                self.logger.warning(f"[CacheManager] Кэш-сервис не зарегистрирован: {cache_type.value}")
                return False
            
            # Вызываем метод set сервиса
            if hasattr(service, 'set'):
                result = service.set(key, data, **kwargs)
            elif hasattr(service, 'set_cached_item'):
                result = service.set_cached_item(key, data, cache_type.value)
            else:
                self.logger.error(f"[CacheManager] Неподдерживаемый интерфейс кэш-сервиса: {cache_type.value}")
                return False
            
            return result
            
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка сохранения в кэш {cache_type.value}: {e}")
            return False
    
    def invalidate(self, key: str, cache_type: CacheType, **kwargs) -> bool:
        """
        Удаляет данные из кэша
        
        Args:
            key: Ключ кэша
            cache_type: Тип кэша
            **kwargs: Дополнительные параметры
            
        Returns:
            True если успешно удалено
        """
        try:
            service = self.cache_services.get(cache_type)
            if not service:
                return False
            
            # Вызываем метод invalidate сервиса
            if hasattr(service, 'invalidate'):
                return service.invalidate(key, **kwargs)
            elif hasattr(service, 'remove_cached_item'):
                return service.remove_cached_item(key, cache_type.value)
            else:
                self.logger.warning(f"[CacheManager] Неподдерживаемый метод invalidate: {cache_type.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка инвалидации кэша {cache_type.value}: {e}")
            return False
    
    def clear_cache(self, cache_type: Optional[CacheType] = None) -> bool:
        """
        Очищает кэш
        
        Args:
            cache_type: Тип кэша (если None, очищает все)
            
        Returns:
            True если успешно очищено
        """
        try:
            if cache_type is None:
                # Очищаем все кэши
                success = True
                for ct, service in self.cache_services.items():
                    if hasattr(service, 'clear_cache'):
                        result = service.clear_cache()
                        success = success and result
                    elif hasattr(service, 'clear_all_cache'):
                        result = service.clear_all_cache()
                        success = success and result
                
                self.global_stats['last_cleanup'] = datetime.now()
                self.logger.info("[CacheManager] Все кэши очищены")
                return success
            else:
                # Очищаем конкретный кэш
                service = self.cache_services.get(cache_type)
                if not service:
                    return False
                
                if hasattr(service, 'clear_cache'):
                    result = service.clear_cache()
                elif hasattr(service, 'clear_all_cache'):
                    result = service.clear_all_cache()
                else:
                    self.logger.warning(f"[CacheManager] Неподдерживаемый метод clear_cache: {cache_type.value}")
                    return False
                
                self.logger.info(f"[CacheManager] Кэш очищен: {cache_type.value}")
                return result
                
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка очистки кэша: {e}")
            return False
    
    def get_cache_stats(self, cache_type: Optional[CacheType] = None) -> Union[CacheStats, Dict[CacheType, CacheStats]]:
        """
        Получает статистику кэша
        
        Args:
            cache_type: Тип кэша (если None, возвращает все)
            
        Returns:
            Статистика кэша или словарь со статистикой всех кэшей
        """
        try:
            if cache_type is None:
                # Возвращаем статистику всех кэшей
                stats = {}
                for ct in self.cache_services.keys():
                    stats[ct] = self._get_single_cache_stats(ct)
                return stats
            else:
                return self._get_single_cache_stats(cache_type)
                
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка получения статистики: {e}")
            return {}
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        Получает глобальную статистику
        
        Returns:
            Словарь с глобальной статистикой
        """
        total_requests = self.global_stats['total_requests']
        if total_requests == 0:
            hit_rate = 0.0
        else:
            hit_rate = (self.global_stats['total_hits'] / total_requests) * 100
        
        return {
            'total_requests': total_requests,
            'total_hits': self.global_stats['total_hits'],
            'total_misses': self.global_stats['total_misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'cache_services_count': self.global_stats['cache_services_count'],
            'last_cleanup': self.global_stats['last_cleanup'],
            'enabled_caches': [ct.value for ct, config in self.cache_configs.items() if config.enabled]
        }
    
    def configure_cache(self, cache_type: CacheType, **config) -> bool:
        """
        Настраивает параметры кэша
        
        Args:
            cache_type: Тип кэша
            **config: Параметры конфигурации
            
        Returns:
            True если успешно настроено
        """
        try:
            if cache_type not in self.cache_configs:
                self.logger.error(f"[CacheManager] Неизвестный тип кэша: {cache_type.value}")
                return False
            
            # Обновляем конфигурацию
            for key, value in config.items():
                if hasattr(self.cache_configs[cache_type], key):
                    setattr(self.cache_configs[cache_type], key, value)
            
            self.logger.info(f"[CacheManager] Конфигурация обновлена: {cache_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка настройки кэша {cache_type.value}: {e}")
            return False
    
    def enable_cache(self, cache_type: CacheType) -> bool:
        """
        Включает кэш
        
        Args:
            cache_type: Тип кэша
            
        Returns:
            True если успешно включён
        """
        return self.configure_cache(cache_type, enabled=True)
    
    def disable_cache(self, cache_type: CacheType) -> bool:
        """
        Отключает кэш
        
        Args:
            cache_type: Тип кэша
            
        Returns:
            True если успешно отключён
        """
        return self.configure_cache(cache_type, enabled=False)
    
    def cleanup_expired(self, cache_type: Optional[CacheType] = None) -> int:
        """
        Очищает истёкшие записи из кэша
        
        Args:
            cache_type: Тип кэша (если None, очищает все)
            
        Returns:
            Количество очищенных записей
        """
        try:
            cleaned_count = 0
            
            if cache_type is None:
                # Очищаем все кэши
                for ct in self.cache_services.keys():
                    cleaned_count += self._cleanup_single_cache(ct)
            else:
                cleaned_count = self._cleanup_single_cache(cache_type)
            
            self.global_stats['last_cleanup'] = datetime.now()
            self.logger.info(f"[CacheManager] Очищено {cleaned_count} истёкших записей")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка очистки истёкших записей: {e}")
            return 0
    
    def _init_default_configs(self) -> None:
        """Инициализирует конфигурации по умолчанию"""
        default_configs = {
            CacheType.TRANSLATION: CacheConfig(
                cache_type=CacheType.TRANSLATION,
                enabled=True,
                ttl=3600,  # 1 час
                max_size=1000,
                cleanup_interval=1800,  # 30 минут
                auto_cleanup=True
            ),
            CacheType.PRODUCT: CacheConfig(
                cache_type=CacheType.PRODUCT,
                enabled=True,
                ttl=1800,  # 30 минут
                max_size=500,
                cleanup_interval=900,  # 15 минут
                auto_cleanup=True
            ),
            CacheType.CATALOG: CacheConfig(
                cache_type=CacheType.CATALOG,
                enabled=True,
                ttl=300,  # 5 минут
                max_size=100,
                cleanup_interval=300,  # 5 минут
                auto_cleanup=True
            ),
            CacheType.IPFS: CacheConfig(
                cache_type=CacheType.IPFS,
                enabled=True,
                ttl=300,  # 5 минут
                max_size=200,
                cleanup_interval=600,  # 10 минут
                auto_cleanup=True
            ),
            CacheType.IMAGE: CacheConfig(
                cache_type=CacheType.IMAGE,
                enabled=True,
                ttl=1800,  # 30 минут
                max_size=50,
                cleanup_interval=1800,  # 30 минут
                auto_cleanup=True
            ),
            CacheType.NAVIGATION: CacheConfig(
                cache_type=CacheType.NAVIGATION,
                enabled=True,
                ttl=3600,  # 1 час
                max_size=200,
                cleanup_interval=1800,  # 30 минут
                auto_cleanup=True
            )
        }
        
        self.cache_configs.update(default_configs)
    
    def _is_cache_enabled(self, cache_type: CacheType) -> bool:
        """Проверяет, включён ли кэш"""
        config = self.cache_configs.get(cache_type)
        return config is not None and config.enabled
    
    def _update_stats(self, cache_type: CacheType, hit: bool) -> None:
        """Обновляет статистику"""
        self.global_stats['total_requests'] += 1
        if hit:
            self.global_stats['total_hits'] += 1
        else:
            self.global_stats['total_misses'] += 1
    
    def _get_single_cache_stats(self, cache_type: CacheType) -> CacheStats:
        """Получает статистику одного кэша"""
        try:
            service = self.cache_services.get(cache_type)
            if not service:
                return CacheStats(
                    cache_type=cache_type,
                    total_requests=0,
                    hits=0,
                    misses=0,
                    hit_rate=0.0,
                    size=0,
                    memory_usage=0,
                    last_cleanup=None
                )
            
            # Получаем статистику от сервиса
            if hasattr(service, 'get_stats'):
                stats = service.get_stats()
                return CacheStats(
                    cache_type=cache_type,
                    total_requests=stats.get('total_requests', 0),
                    hits=stats.get('memory_hits', 0) + stats.get('file_hits', 0) + stats.get('ipfs_hits', 0),
                    misses=stats.get('misses', 0),
                    hit_rate=stats.get('hit_rate_percent', 0.0),
                    size=stats.get('memory_cache_size', 0),
                    memory_usage=0,  # TODO: Реализовать подсчёт памяти
                    last_cleanup=self.global_stats['last_cleanup']
                )
            else:
                return CacheStats(
                    cache_type=cache_type,
                    total_requests=0,
                    hits=0,
                    misses=0,
                    hit_rate=0.0,
                    size=0,
                    memory_usage=0,
                    last_cleanup=None
                )
                
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка получения статистики {cache_type.value}: {e}")
            return CacheStats(
                cache_type=cache_type,
                total_requests=0,
                hits=0,
                misses=0,
                hit_rate=0.0,
                size=0,
                memory_usage=0,
                last_cleanup=None
            )
    
    def _cleanup_single_cache(self, cache_type: CacheType) -> int:
        """Очищает один кэш"""
        try:
            service = self.cache_services.get(cache_type)
            if not service:
                return 0
            
            # Вызываем метод очистки сервиса
            if hasattr(service, 'cleanup_expired'):
                return service.cleanup_expired()
            elif hasattr(service, 'clear_expired'):
                return service.clear_expired()
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"[CacheManager] Ошибка очистки кэша {cache_type.value}: {e}")
            return 0
