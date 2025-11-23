"""
TranslationCacheService - Многоуровневое кэширование для переводов

Обеспечивает трёхуровневое кэширование:
1. Memory Cache - быстрый доступ в памяти
2. File Cache - персистентное хранение на диске  
3. IPFS Cache - кэш переводов из IPFS

Интегрируется с LocalizationService для оптимизации производительности.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Запись в кэше с метаданными"""
    data: Any
    timestamp: float
    ttl: int
    source: str  # 'memory', 'file', 'ipfs'
    
    def is_expired(self) -> bool:
        """Проверяет, истёк ли кэш"""
        return time.time() - self.timestamp > self.ttl

class TranslationCacheService:
    """Многоуровневый сервис кэширования переводов"""
    
    def __init__(self, cache_dir: str = "cache/translations", default_ttl: int = 3600):
        """
        Инициализация сервиса кэширования
        
        Args:
            cache_dir: Директория для файлового кэша
            default_ttl: TTL по умолчанию в секундах (1 час)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.default_ttl = default_ttl
        
        # Уровни кэширования
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.file_cache_path = self.cache_dir / "translations.json"
        self.ipfs_cache_path = self.cache_dir / "ipfs.json"
        
        # TTL для разных типов данных
        self.ttl_config = {
            'interface': 3600,      # 1 час - интерфейсные переводы
            'product': 1800,         # 30 минут - переводы продуктов
            'component': 1800,       # 30 минут - переводы компонентов
            'fallback': 7200,        # 2 часа - fallback данные
            'ipfs': 300              # 5 минут - данные из IPFS
        }
        
        # Статистика
        self.stats = {
            'memory_hits': 0,
            'file_hits': 0,
            'ipfs_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        
        # Загружаем файловый кэш при инициализации
        self._load_file_cache()
        # Прогреваем ipfs-файл (создание директории уже выполнено)
        if not self.ipfs_cache_path.exists():
            try:
                with open(self.ipfs_cache_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            except Exception as e:
                logger.warning(f"[TranslationCacheService] Не удалось подготовить IPFS кэш: {e}")
        
        logger.info(f"[TranslationCacheService] Инициализирован с кэш-директорией: {self.cache_dir}")
    
    def get(self, key: str, cache_type: str = 'interface') -> Optional[Any]:
        """
        Получает данные из кэша с многоуровневым поиском
        
        Args:
            key: Ключ кэша
            cache_type: Тип кэша (interface, product, component, fallback, ipfs)
            
        Returns:
            Кэшированные данные или None
        """
        self.stats['total_requests'] += 1
        
        # 1. Проверяем Memory Cache
        memory_result = self._get_from_memory(key, cache_type)
        if memory_result is not None:
            self.stats['memory_hits'] += 1
            logger.debug(f"[TranslationCacheService] Memory hit: {key}")
            return memory_result
        
        # 2. Проверяем File Cache
        file_result = self._get_from_file(key, cache_type)
        if file_result is not None:
            self.stats['file_hits'] += 1
            # Сохраняем в memory cache для быстрого доступа
            self._set_memory_cache(key, file_result, cache_type)
            logger.debug(f"[TranslationCacheService] File hit: {key}")
            return file_result
        
        # 3. Проверяем IPFS Cache (если применимо)
        if cache_type in ['product', 'component', 'ipfs']:
            ipfs_result = self._get_from_ipfs_cache(key, cache_type)
            if ipfs_result is not None:
                self.stats['ipfs_hits'] += 1
                # Сохраняем в оба кэша
                self._set_memory_cache(key, ipfs_result, cache_type)
                self._set_file_cache(key, ipfs_result, cache_type)
                logger.debug(f"[TranslationCacheService] IPFS hit: {key}")
                return ipfs_result
        
        self.stats['misses'] += 1
        logger.debug(f"[TranslationCacheService] Cache miss: {key}")
        return None
    
    def set(self, key: str, data: Any, cache_type: str = 'interface', ttl: Optional[int] = None) -> bool:
        """
        Сохраняет данные в кэш
        
        Args:
            key: Ключ кэша
            data: Данные для кэширования
            cache_type: Тип кэша
            ttl: Время жизни в секундах (если None, используется default)
            
        Returns:
            True если успешно сохранено
        """
        try:
            if data is None:
                logger.warning(f"[TranslationCacheService] Попытка записи None в кэш: key={key}, type={cache_type}")
                return False
            if ttl is None:
                ttl = self.ttl_config.get(cache_type, self.default_ttl)
            
            # Сохраняем во все уровни кэша
            self._set_memory_cache(key, data, cache_type, ttl)
            self._set_file_cache(key, data, cache_type, ttl)
            if cache_type == 'ipfs':
                self._set_ipfs_cache(key, data, ttl)
            
            logger.debug(f"[TranslationCacheService] Данные сохранены в кэш: {key}, type: {cache_type}")
            return True
            
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка сохранения в кэш: {e}")
            return False
    
    def invalidate(self, key: str, cache_type: str = 'interface') -> bool:
        """
        Удаляет данные из кэша
        
        Args:
            key: Ключ кэша
            cache_type: Тип кэша
            
        Returns:
            True если успешно удалено
        """
        try:
            # Удаляем из memory cache
            memory_key = f"{cache_type}:{key}"
            if memory_key in self.memory_cache:
                del self.memory_cache[memory_key]
            
            # Удаляем из file cache
            self._remove_from_file_cache(key, cache_type)
            # Удаляем из ipfs cache
            if cache_type == 'ipfs':
                self._remove_from_ipfs_cache(key)
            
            logger.debug(f"[TranslationCacheService] Данные удалены из кэша: {key}")
            return True
            
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка удаления из кэша: {e}")
            return False
    
    def clear_cache(self, cache_type: Optional[str] = None) -> bool:
        """
        Очищает кэш
        
        Args:
            cache_type: Тип кэша для очистки (если None, очищает все)
            
        Returns:
            True если успешно очищено
        """
        try:
            if cache_type is None:
                # Очищаем все
                self.memory_cache.clear()
                self._clear_file_cache()
                self._clear_ipfs_cache()
                logger.info("[TranslationCacheService] Весь кэш очищен")
            else:
                # Очищаем конкретный тип
                keys_to_remove = [k for k in self.memory_cache.keys() if k.startswith(f"{cache_type}:")]
                for key in keys_to_remove:
                    del self.memory_cache[key]
                if cache_type == 'ipfs':
                    self._clear_ipfs_cache()
                else:
                    self._clear_file_cache_by_type(cache_type)
                logger.info(f"[TranslationCacheService] Кэш типа '{cache_type}' очищен")
            
            return True
            
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка очистки кэша: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэширования"""
        total_requests = self.stats['total_requests']
        if total_requests == 0:
            hit_rate = 0.0
        else:
            total_hits = self.stats['memory_hits'] + self.stats['file_hits'] + self.stats['ipfs_hits']
            hit_rate = (total_hits / total_requests) * 100
        
        return {
            'memory_hits': self.stats['memory_hits'],
            'file_hits': self.stats['file_hits'],
            'ipfs_hits': self.stats['ipfs_hits'],
            'misses': self.stats['misses'],
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'memory_cache_size': len(self.memory_cache),
            'cache_types': list(self.ttl_config.keys())
        }
    
    def _get_from_memory(self, key: str, cache_type: str) -> Optional[Any]:
        """Получает данные из memory cache"""
        memory_key = f"{cache_type}:{key}"
        if memory_key in self.memory_cache:
            entry = self.memory_cache[memory_key]
            if not entry.is_expired():
                return entry.data
            else:
                # Удаляем истёкшую запись
                del self.memory_cache[memory_key]
        return None
    
    def _set_memory_cache(self, key: str, data: Any, cache_type: str, ttl: Optional[int] = None) -> None:
        """Сохраняет данные в memory cache"""
        if ttl is None:
            ttl = self.ttl_config.get(cache_type, self.default_ttl)
        
        memory_key = f"{cache_type}:{key}"
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl,
            source='memory'
        )
        self.memory_cache[memory_key] = entry
    
    def _get_from_file(self, key: str, cache_type: str) -> Optional[Any]:
        """Получает данные из file cache"""
        try:
            if not self.file_cache_path.exists():
                return None
            
            with open(self.file_cache_path, 'r', encoding='utf-8') as f:
                file_cache = json.load(f)
            
            cache_key = f"{cache_type}:{key}"
            if cache_key in file_cache:
                entry_data = file_cache[cache_key]
                if isinstance(entry_data, dict) and 'data' in entry_data and 'timestamp' in entry_data:
                    # Проверяем TTL
                    entry_ttl = entry_data.get('ttl', self.default_ttl)
                    if time.time() - entry_data['timestamp'] <= entry_ttl:
                        return entry_data['data']
                    else:
                        # Удаляем истёкшую запись
                        del file_cache[cache_key]
                        self._save_file_cache(file_cache)
            
            return None
            
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка чтения файлового кэша: {e}")
            return None
    
    def _set_file_cache(self, key: str, data: Any, cache_type: str, ttl: Optional[int] = None) -> None:
        """Сохраняет данные в file cache"""
        try:
            if ttl is None:
                ttl = self.ttl_config.get(cache_type, self.default_ttl)
            
            # Загружаем существующий кэш
            file_cache = {}
            if self.file_cache_path.exists():
                with open(self.file_cache_path, 'r', encoding='utf-8') as f:
                    file_cache = json.load(f)
            
            # Добавляем новую запись
            cache_key = f"{cache_type}:{key}"
            file_cache[cache_key] = {
                'data': data,
                'timestamp': time.time(),
                'ttl': ttl,
                'source': 'file'
            }
            
            self._save_file_cache(file_cache)
            
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка сохранения в файловый кэш: {e}")
    
    def _get_from_ipfs_cache(self, key: str, cache_type: str) -> Optional[Any]:
        """Получает данные из IPFS cache (отдельный файловый слой ipfs.json + TTL)"""
        try:
            if not self.ipfs_cache_path.exists():
                logger.debug(f"[TranslationCacheService] IPFS cache MISS (no file): {key}")
                return None
            with open(self.ipfs_cache_path, 'r', encoding='utf-8') as f:
                ipfs_cache = json.load(f)
            cache_key = f"{cache_type}:{key}"
            if cache_key in ipfs_cache:
                entry = ipfs_cache[cache_key]
                entry_ttl = entry.get('ttl', self.ttl_config.get('ipfs', self.default_ttl))
                if time.time() - entry.get('timestamp', 0) <= entry_ttl:
                    logger.debug(f"[TranslationCacheService] IPFS cache HIT: {key}")
                    return entry.get('data')
                # TTL истёк — удалить запись
                logger.debug(f"[TranslationCacheService] IPFS cache EXPIRED: {key}")
                del ipfs_cache[cache_key]
                self._save_ipfs_cache(ipfs_cache)
            else:
                logger.debug(f"[TranslationCacheService] IPFS cache MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"[TranslationCacheService] Ошибка чтения IPFS кэша: {e}")
        return None

    def _set_ipfs_cache(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Сохраняет данные в IPFS cache"""
        try:
            if ttl is None:
                ttl = self.ttl_config.get('ipfs', self.default_ttl)
            ipfs_cache = {}
            if self.ipfs_cache_path.exists():
                with open(self.ipfs_cache_path, 'r', encoding='utf-8') as f:
                    ipfs_cache = json.load(f)
            cache_key = f"ipfs:{key}"
            ipfs_cache[cache_key] = {
                'data': data,
                'timestamp': time.time(),
                'ttl': ttl,
                'source': 'ipfs'
            }
            self._save_ipfs_cache(ipfs_cache)
            logger.debug(f"[TranslationCacheService] IPFS cache WRITE: {key}, TTL={ttl}s")
        except Exception as e:
            logger.warning(f"[TranslationCacheService] Ошибка записи в IPFS кэш: {e}")

    def _remove_from_ipfs_cache(self, key: str) -> None:
        """Удаляет данные из IPFS cache"""
        try:
            if not self.ipfs_cache_path.exists():
                return
            with open(self.ipfs_cache_path, 'r', encoding='utf-8') as f:
                ipfs_cache = json.load(f)
            cache_key = f"ipfs:{key}"
            if cache_key in ipfs_cache:
                del ipfs_cache[cache_key]
                self._save_ipfs_cache(ipfs_cache)
        except Exception as e:
            logger.warning(f"[TranslationCacheService] Ошибка удаления из IPFS кэша: {e}")
    
    def _remove_from_file_cache(self, key: str, cache_type: str) -> None:
        """Удаляет данные из file cache"""
        try:
            if not self.file_cache_path.exists():
                return
            
            with open(self.file_cache_path, 'r', encoding='utf-8') as f:
                file_cache = json.load(f)
            
            cache_key = f"{cache_type}:{key}"
            if cache_key in file_cache:
                del file_cache[cache_key]
                self._save_file_cache(file_cache)
                
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка удаления из файлового кэша: {e}")
    
    def _clear_file_cache(self) -> None:
        """Очищает весь файловый кэш"""
        try:
            if self.file_cache_path.exists():
                self.file_cache_path.unlink()
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка очистки файлового кэша: {e}")
    
    def _clear_ipfs_cache(self) -> None:
        """Очищает весь IPFS файловый кэш"""
        try:
            if self.ipfs_cache_path.exists():
                self.ipfs_cache_path.unlink()
                # Пересоздаём пустой файл
                with open(self.ipfs_cache_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка очистки IPFS кэша: {e}")
    
    def _clear_file_cache_by_type(self, cache_type: str) -> None:
        """Очищает файловый кэш по типу"""
        try:
            if not self.file_cache_path.exists():
                return
            
            with open(self.file_cache_path, 'r', encoding='utf-8') as f:
                file_cache = json.load(f)
            
            # Удаляем все ключи данного типа
            keys_to_remove = [k for k in file_cache.keys() if k.startswith(f"{cache_type}:")]
            for key in keys_to_remove:
                del file_cache[key]
            
            self._save_file_cache(file_cache)
            
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка очистки файлового кэша по типу: {e}")
    
    def _load_file_cache(self) -> None:
        """Загружает файловый кэш при инициализации"""
        try:
            if self.file_cache_path.exists():
                with open(self.file_cache_path, 'r', encoding='utf-8') as f:
                    file_cache = json.load(f)
                
                # Очищаем истёкшие записи при загрузке
                current_time = time.time()
                expired_keys = []
                
                for key, entry_data in file_cache.items():
                    if isinstance(entry_data, dict) and 'timestamp' in entry_data and 'ttl' in entry_data:
                        if current_time - entry_data['timestamp'] > entry_data['ttl']:
                            expired_keys.append(key)
                
                for key in expired_keys:
                    del file_cache[key]
                
                if expired_keys:
                    self._save_file_cache(file_cache)
                    logger.info(f"[TranslationCacheService] Удалено {len(expired_keys)} истёкших записей из файлового кэша")
                
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка загрузки файлового кэша: {e}")
    
    def _save_file_cache(self, file_cache: Dict[str, Any]) -> None:
        """Сохраняет файловый кэш"""
        try:
            with open(self.file_cache_path, 'w', encoding='utf-8') as f:
                json.dump(file_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка сохранения файлового кэша: {e}")
    
    def _save_ipfs_cache(self, ipfs_cache: Dict[str, Any]) -> None:
        """Сохраняет IPFS кэш"""
        try:
            with open(self.ipfs_cache_path, 'w', encoding='utf-8') as f:
                json.dump(ipfs_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[TranslationCacheService] Ошибка сохранения IPFS кэша: {e}")
