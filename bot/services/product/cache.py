from typing import Optional, Any, Dict, Tuple, List
from datetime import datetime, timedelta
import logging
import json
import traceback
from model.product import Description, DosageInstruction
from services.core.ipfs_factory import IPFSFactory

logger = logging.getLogger(__name__)

class ProductCacheService:
    """Единый сервис кэширования для продуктов с интеграцией IPFS хранилища"""
    
    # Время жизни кэша для разных типов данных
    CACHE_TTL = {
        'catalog': timedelta(hours=24),
        'description': timedelta(hours=24),
        'image': timedelta(hours=12)
    }
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"[ProductCacheService] __init__ id(self)={id(self)}")
        
        # Всегда инициализируем кэши (даже для singleton)
        if not hasattr(self, 'catalog_cache'):
            self.logger.info(f"[ProductCacheService] Инициализируем catalog_cache")
            self.catalog_cache: Dict = {}  # {"version": int, "products": List[Product], "timestamp": datetime}
        else:
            self.logger.info(f"[ProductCacheService] catalog_cache уже существует")
            
        if not hasattr(self, 'description_cache'):
            self.logger.info(f"[ProductCacheService] Инициализируем description_cache")
            self.description_cache: Dict[str, Tuple[Description, datetime]] = {}  # {cid: (description, timestamp)}
        else:
            self.logger.info(f"[ProductCacheService] description_cache уже существует")
            
        if not hasattr(self, 'image_cache'):
            self.logger.info(f"[ProductCacheService] Инициализируем image_cache")
            self.image_cache: Dict[str, Tuple[str, datetime]] = {}  # {cid: (url, timestamp)}
        else:
            self.logger.info(f"[ProductCacheService] image_cache уже существует")
        
        if not hasattr(self, '_initialized'):
            # Инициализация только при первом создании
            self.logger.info(f"ProductCacheService initialization started...")
            self._storage_service = None  # Lazy loading
            self._initialized = True
            self.logger.info(f"ProductCacheService initialization completed")
    
    @property
    def storage_service(self):
        """Lazy loading storage service для избежания циркулярных зависимостей"""
        if self._storage_service is None:  
            self._storage_service = IPFSFactory().get_storage()
        return self._storage_service
    
    def set_storage_service(self, storage_service):
        """Устанавливает storage service (для тестирования или внешней инициализации)"""
        self._storage_service = storage_service
    
    def get_cached_item(self, key: str, cache_type: str) -> Optional[Any]:
        """
        Получает элемент из кэша.
        
        Args:
            key: Ключ для поиска в кэше
            cache_type: Тип кэша ('catalog', 'description', 'image')
            
        Returns:
            Optional[Any]: Закэшированное значение или None
        """
        self.logger.info(f"[ProductCacheService] get_cached_item id(self)={id(self)}")
        self.logger.info(f"[ProductCacheService] get_cached_item: key='{key}', cache_type='{cache_type}'")
        
        cache = self._get_cache_by_type(cache_type)
        if cache is None:
            self.logger.info(f"[ProductCacheService] Кэш типа '{cache_type}' не найден")
            return None
            
        # Проверяем, есть ли ключ в кэше
        if key in cache:
            cached_data = cache[key]
            self.logger.info(f"[ProductCacheService] Найден элемент в кэше: key='{key}', type='{cache_type}'")
            
            # Проверяем структуру кэшированных данных (value, timestamp)
            if isinstance(cached_data, tuple) and len(cached_data) == 2:
                value, timestamp = cached_data
                
                if self._is_cache_valid(timestamp, cache_type):
                    self.logger.info(f"[ProductCacheService] ✅ Кэш валиден для key='{key}', cache_type='{cache_type}'")
                    return value
                else:
                    self.logger.info(f"[ProductCacheService] ❌ Кэш устарел для key='{key}', cache_type='{cache_type}'")
                    return None
            else:
                # Если данные не в формате (value, timestamp), возвращаем как есть
                self.logger.info(f"[ProductCacheService] Данные в кэше не в ожидаемом формате: {type(cached_data)}")
                return cached_data
        else:
            self.logger.info(f"[ProductCacheService] Элемент не найден в кэше: key='{key}', type='{cache_type}'")
            return None
    
    def set_cached_item(self, key: str, value: Any, cache_type: str) -> bool:
        """
        Сохраняет элемент в кэш.
        
        Args:
            key: Ключ для сохранения в кэше
            value: Значение для кэширования
            cache_type: Тип кэша ('catalog', 'description', 'image')
            
        Returns:
            bool: True если успешно сохранено, False в противном случае
        """
        self.logger.info(f"[ProductCacheService] set_cached_item: key='{key}', cache_type='{cache_type}'")
        
        cache = self._get_cache_by_type(cache_type)
        if cache is None:
            self.logger.error(f"[ProductCacheService] Не удалось найти кэш типа '{cache_type}'")
            return False
            
        # Для description проверяем тип и конвертируем если нужно
        if cache_type == 'description' and isinstance(value, dict):
            value = Description.from_dict(value)
            
        # Сохраняем в кэш с временной меткой
        cache[key] = (value, datetime.utcnow())
        self.logger.info(f"[ProductCacheService] ✅ Элемент сохранен в кэш: key='{key}', cache_type='{cache_type}'")
        
        # Дополнительная информация для каталога
        if cache_type == 'catalog' and isinstance(value, dict):
            version = value.get('version', 'unknown')
            products_count = len(value.get('products', []))
            self.logger.info(f"[ProductCacheService] 📦 Каталог в кэше: version={version}, products_count={products_count}")
            
        return True
    
    def get_description_by_cid(self, description_cid: str) -> Optional[Description]:
        """
        Получает описание продукта по CID с кэшированием.
        
        Args:
            description_cid: CID описания в IPFS
            
        Returns:
            Optional[Description]: Объект Description или None если не найдено
        """
        if not description_cid:
            self.logger.debug("Получен пустой description_cid")
            return None
        
        # Проверяем кэш
        cached_description = self.get_cached_item(description_cid, 'description')
        if cached_description:
            self.logger.debug(f"Найдено описание в кэше для {description_cid}")
            return cached_description
        
        # Если нет в кэше, загружаем из IPFS
        try:
            self.logger.info(f"Загрузка описания из IPFS: {description_cid}")
            description_data = self.storage_service.download_json(description_cid)
            
            if not description_data:
                self.logger.warning(f"Не удалось загрузить данные описания для {description_cid}")
                return None
            
            # Обрабатываем данные описания напрямую
            self.logger.info(f"[cache] Обрабатываем данные описания: type={type(description_data)}")
            
            # Если это уже объект Description, возвращаем его
            if isinstance(description_data, Description):
                self.logger.info(f"[cache] Данные уже являются объектом Description")
                description = description_data
            # Если это словарь, создаем Description из него
            elif isinstance(description_data, dict):
                self.logger.info(f"[cache] Обрабатываем словарь: keys={list(description_data.keys())}")
                try:
                    description = Description.from_dict(description_data)
                    self.logger.info(f"[cache] Успешно создан объект Description из словаря")
                except Exception as e:
                    self.logger.error(f"[cache] Ошибка создания Description из словаря: {e}")
                    return None
            # Если это строка, пытаемся распарсить как JSON
            elif isinstance(description_data, str):
                self.logger.info(f"[cache] Обрабатываем строку длиной {len(description_data)}")
                try:
                    parsed_data = json.loads(description_data)
                    self.logger.info(f"[cache] JSON успешно распарсен, тип: {type(parsed_data)}")
                    if isinstance(parsed_data, dict):
                        self.logger.info(f"[cache] Создаем Description из распарсенного JSON")
                        description = Description.from_dict(parsed_data)
                        self.logger.info(f"[cache] Успешно создан объект Description из JSON строки")
                    else:
                        self.logger.error(f"[cache] JSON строка не содержит словарь: {type(parsed_data)}")
                        return None
                except json.JSONDecodeError as e:
                    self.logger.error(f"[cache] Не удалось распарсить JSON строку: {e}")
                    return None
            else:
                self.logger.error(f"[cache] Неподдерживаемый тип данных для описания: {type(description_data)}")
                return None
            
            # Сохраняем в кэш
            self.set_cached_item(description_cid, description, 'description')
            self.logger.info(f"Описание загружено и сохранено в кэш: {description_cid}")
            
            return description
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки описания {description_cid}: {e}\n{traceback.format_exc()}")
            return None
    
    def get_image_url_by_cid(self, image_cid: str) -> Optional[str]:
        """
        Получает URL изображения по CID с кэшированием.
        
        Args:
            image_cid: CID изображения в IPFS
            
        Returns:
            Optional[str]: URL изображения или None если не найдено
        """
        if not image_cid:
            return None
        
        # Проверяем кэш
        cached_url = self.get_cached_item(image_cid, 'image')
        if cached_url:
            self.logger.debug(f"Найдено изображение в кэше для {image_cid}")
            return cached_url
        
        # Если нет в кэше, получаем URL из IPFS
        try:
            self.logger.info(f"Получение URL изображения из IPFS: {image_cid}")
            url = self.storage_service.get_gateway_url(image_cid)
            
            if not url:
                self.logger.warning(f"Не удалось получить URL изображения для {image_cid}")
                return None
            
            # Сохраняем в кэш
            self.set_cached_item(image_cid, url, 'image')
            self.logger.info(f"URL изображения получен и сохранен в кэш: {image_cid}")
            
            return url
            
        except Exception as e:
            self.logger.error(f"Ошибка получения URL изображения {image_cid}: {e}\n{traceback.format_exc()}")
            return None
    
    def invalidate_cache(self, cache_type: Optional[str] = None):
        """
        Инвалидирует кэш указанного типа или все кэши.
        
        Args:
            cache_type: Тип кэша для очистки ('catalog', 'description', 'image') или None для очистки всех
        """
        if cache_type == 'catalog' or cache_type is None:
            self.catalog_cache.clear()
            self.logger.info("Catalog cache cleared")
            
        if cache_type == 'description' or cache_type is None:
            self.description_cache.clear()
            self.logger.info("Description cache cleared")
            
        if cache_type == 'image' or cache_type is None:
            self.image_cache.clear()
            self.logger.info("Image cache cleared")
    
    def _get_cache_by_type(self, cache_type: str) -> Optional[Dict]:
        """
        Возвращает нужный кэш по типу.
        
        Args:
            cache_type: Тип кэша ('catalog', 'description', 'image')
            
        Returns:
            Optional[Dict]: Словарь с кэшем или None
        """
        self.logger.info(f"[ProductCacheService] _get_cache_by_type: cache_type='{cache_type}'")
        self.logger.info(f"[ProductCacheService] _get_cache_by_type: hasattr(self, 'catalog_cache')={hasattr(self, 'catalog_cache')}")
        self.logger.info(f"[ProductCacheService] _get_cache_by_type: hasattr(self, 'description_cache')={hasattr(self, 'description_cache')}")
        self.logger.info(f"[ProductCacheService] _get_cache_by_type: hasattr(self, 'image_cache')={hasattr(self, 'image_cache')}")
        
        if cache_type == 'catalog':
            self.logger.info(f"[ProductCacheService] _get_cache_by_type: catalog_cache={self.catalog_cache}")
            return self.catalog_cache  # Возвращаем всегда, даже если пустой
        elif cache_type == 'description':
            self.logger.info(f"[ProductCacheService] _get_cache_by_type: description_cache={self.description_cache}")
            return self.description_cache  # Возвращаем всегда, даже если пустой
        elif cache_type == 'image':
            self.logger.info(f"[ProductCacheService] _get_cache_by_type: image_cache={self.image_cache}")
            return self.image_cache  # Возвращаем всегда, даже если пустой
        else:
            self.logger.error(f"[ProductCacheService] Неизвестный тип кэша: {cache_type}")
            return None
    
    def _is_cache_valid(self, timestamp: datetime, cache_type: str) -> bool:
        """
        Проверяет актуальность кэша.
        
        Args:
            timestamp: Временная метка кэша
            cache_type: Тип кэша ('catalog', 'description', 'image')
            
        Returns:
            bool: True если кэш актуален, False если устарел
        """
        if not timestamp:
            self.logger.info(f"[ProductCacheService] _is_cache_valid: timestamp is None")
            return False
            
        ttl = self.CACHE_TTL.get(cache_type)
        if not ttl:
            self.logger.info(f"[ProductCacheService] _is_cache_valid: TTL not found for cache_type='{cache_type}'")
            return False
            
        now = datetime.utcnow()
        age = now - timestamp
        is_valid = age < ttl
        
        self.logger.info(f"[ProductCacheService] _is_cache_valid: cache_type='{cache_type}', timestamp={timestamp}, now={now}, age={age}, ttl={ttl}, is_valid={is_valid}")
        
        return is_valid 