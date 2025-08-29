import os
import requests
import mimetypes
import traceback
import logging
from dotenv import load_dotenv
import time
import aiohttp
import asyncio
from typing import Optional, Dict, Any, Union, List, Tuple
import random
from functools import wraps
import json
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import base64
from pathlib import Path
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

# Импорт типизированных исключений
from .exceptions import (
    StorageError, StorageAuthError, StoragePermissionError, StorageRateLimitError,
    StorageNotFoundError, StorageValidationError, StorageTimeoutError, StorageNetworkError,
    StorageConfigError, StorageProviderError, create_storage_error_from_http_response, create_storage_error_from_exception
)

logger = logging.getLogger(__name__)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """
    Декоратор для повторных попыток с экспоненциальной задержкой
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Too Many Requests
                        if x == retries:
                            raise
                        else:
                            sleep = (backoff_in_seconds * 2 ** x +
                                   random.uniform(0, 1))
                            logger.warning(f"Rate limit hit, waiting {sleep:.2f} seconds...")
                            time.sleep(sleep)
                            x += 1
                    else:
                        raise
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout) as e:
                    if x == retries:
                        raise
                    else:
                        sleep = (backoff_in_seconds * 2 ** x +
                               random.uniform(0, 1))
                        logger.warning(f"Connection error, waiting {sleep:.2f} seconds...")
                        time.sleep(sleep)
                        x += 1
        return wrapper
    return decorator

class PinataMetrics:
    """Класс для сбора метрик работы с Pinata"""
    
    def __init__(self):
        self.upload_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.last_metrics_dump: Optional[datetime] = None
        self.metrics_dump_interval = timedelta(hours=1)
    
    def track_upload(self, duration: float):
        """Записывает время загрузки файла"""
        self.upload_times.append(duration)
        self._check_metrics_dump()
    
    def track_error(self, error_type: str):
        """Записывает ошибку определенного типа"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self._check_metrics_dump()
    
    def track_cache_hit(self):
        """Записывает попадание в кэш"""
        self.cache_hits += 1
        
    def track_cache_miss(self):
        """Записывает промах кэша"""
        self.cache_misses += 1
    
    def _check_metrics_dump(self):
        """Проверяет необходимость сохранения метрик"""
        now = datetime.now()
        if (not self.last_metrics_dump or 
            now - self.last_metrics_dump > self.metrics_dump_interval):
            self.dump_metrics()
            self.last_metrics_dump = now
    
    def get_average_upload_time(self) -> float:
        """Возвращает среднее время загрузки"""
        if not self.upload_times:
            return 0.0
        return sum(self.upload_times) / len(self.upload_times)
    
    def get_cache_hit_ratio(self) -> float:
        """Возвращает соотношение попаданий к промахам кэша"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    def dump_metrics(self):
        """Сохраняет текущие метрики в файл"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'average_upload_time': self.get_average_upload_time(),
                'error_counts': self.error_counts,
                'cache_hit_ratio': self.get_cache_hit_ratio(),
                'total_uploads': len(self.upload_times),
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses
            }
            
            metrics_dir = Path('metrics')
            metrics_dir.mkdir(exist_ok=True)
            
            metrics_file = metrics_dir / f'pinata_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            # Очищаем историю после сохранения
            self.upload_times = self.upload_times[-100:]  # Оставляем только последние 100 записей
            
            logger.info(f"Метрики сохранены в {metrics_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении метрик: {e}")

class SecurePinataCache:
    """Улучшенный класс для безопасного управления кэшем файлов Pinata"""
    
    def __init__(self, cache_file: str = "pinata_cache.json", max_size: int = 1000):
        self.cache_file = cache_file
        self.cache: Dict[str, Dict] = {}
        self.last_update: Optional[datetime] = None
        self.update_interval = timedelta(minutes=30)
        self.max_size = max_size
        self.metrics = PinataMetrics()
        
        # Инициализация шифрования
        self._init_encryption()
        self.load_cache()
    
    def _init_encryption(self):
        """Инициализирует или загружает ключ шифрования"""
        key_file = '.cache_key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.key)
        self.cipher = Fernet(self.key)
    
    def _encrypt_data(self, data: Dict) -> bytes:
        """Шифрует данные кэша"""
        json_str = json.dumps(data)
        return self.cipher.encrypt(json_str.encode())
    
    def _decrypt_data(self, encrypted_data: bytes) -> Dict:
        """Расшифровывает данные кэша"""
        json_str = self.cipher.decrypt(encrypted_data).decode()
        return json.loads(json_str)
    
    def load_cache(self):
        """Загружает и расшифровывает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        data = self._decrypt_data(encrypted_data)
                        self.cache = data.get('files', {})
                        last_update = data.get('last_update')
                        if last_update:
                            self.last_update = datetime.fromisoformat(last_update)
                        logger.info(f"Кэш загружен, {len(self.cache)} записей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке кэша: {e}")
            self.cache = {}
            self.last_update = None
    
    def save_cache(self):
        """Шифрует и сохраняет кэш в файл"""
        try:
            data = {
                'files': self.cache,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            encrypted_data = self._encrypt_data(data)
            with open(self.cache_file, 'wb') as f:
                f.write(encrypted_data)
            logger.debug("Кэш сохранен")
        except Exception as e:
            logger.error(f"Ошибка при сохранении кэша: {e}")
    
    def cleanup_old_entries(self):
        """Удаляет старые записи если превышен максимальный размер кэша"""
        if len(self.cache) > self.max_size:
            # Сортируем по времени последнего обновления и оставляем только max_size записей
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: datetime.fromisoformat(x[1]['last_updated']),
                reverse=True
            )
            self.cache = dict(sorted_entries[:self.max_size])
            logger.info(f"Кэш очищен до {len(self.cache)} записей")
            self.save_cache()
    
    def needs_update(self) -> bool:
        """Проверяет, нужно ли обновить кэш"""
        if not self.last_update:
            return True
        return datetime.now() - self.last_update > self.update_interval
    
    def update_file(self, file_name: str, cid: str, metadata: Optional[Dict] = None):
        """Обновляет информацию о файле в кэше"""
        self.cache[file_name] = {
            'cid': cid,
            'metadata': metadata or {},
            'last_updated': datetime.now().isoformat()
        }
        self.cleanup_old_entries()
        self.save_cache()
    
    def get_file(self, file_name: str) -> Optional[Dict]:
        """Получает информацию о файле из кэша"""
        file_info = self.cache.get(file_name)
        if file_info:
            self.metrics.track_cache_hit()
        else:
            self.metrics.track_cache_miss()
        return file_info
    
    def update_from_pins(self, pins: List[Dict]):
        """Обновляет кэш из списка пинов"""
        new_cache = {}
        for pin in pins:
            metadata = pin.get('metadata', {})
            name = metadata.get('name')
            if name:
                new_cache[name] = {
                    'cid': pin.get('ipfs_pin_hash'),
                    'metadata': metadata,
                    'last_updated': datetime.now().isoformat()
                }
        self.cache = new_cache
        self.last_update = datetime.now()
        self.cleanup_old_entries()
        self.save_cache()

from .base import BaseStorageProvider

class SecurePinataUploader(BaseStorageProvider):
    """Улучшенная версия PinataUploader с дополнительными мерами безопасности"""
    
    # Константы для настройки запросов - УВЕЛИЧЕНЫ для решения rate limiting
    MAX_RETRIES = 10  # Увеличиваем количество попыток для стабильности
    INITIAL_BACKOFF = 5  # Увеличиваем начальную задержку для Pinata API
    REQUEST_TIMEOUT = 60  # Увеличиваем таймаут для медленных соединений
    REQUEST_DELAY = 10.0  # Увеличиваем задержку между запросами до 10 секунд (Pinata recommendation)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Разрешенные MIME типы
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/gif',
        'application/json', 'text/plain',
        'application/pdf', 'application/xml'
    }
    
    api_url = "https://api.pinata.cloud"
    gateway_url = "https://gateway.pinata.cloud/ipfs"
    
    def __init__(self, cache_file: str = "pinata_cache.json"):
        load_dotenv()
        self.api_key = os.getenv("PINATA_API_KEY")
        self.secret_api_key = os.getenv("PINATA_API_SECRET")
        
        # Проверка конфигурации с типизированными исключениями
        if not self.api_key:
            raise StorageConfigError("Pinata API key is missing", missing_key="PINATA_API_KEY")
        if not self.secret_api_key:
            raise StorageConfigError("Pinata API secret is missing", missing_key="PINATA_API_SECRET")
        
        # Заголовки для API запросов
        self.base_headers = {
            "pinata_api_key": self.api_key,
            "pinata_secret_api_key": self.secret_api_key
        }
        
        # Заголовки для JSON API
        self.json_headers = {
            **self.base_headers,
            "Content-Type": "application/json"
        }
        
        self._last_request_time = 0
        self.cache = SecurePinataCache(cache_file)
        self.metrics = PinataMetrics()
        
        # Circuit breaker для предотвращения каскадных сбоев
        self._consecutive_errors = 0
        self._circuit_breaker_threshold = 5  # Максимум 5 ошибок подряд
        self._circuit_breaker_timeout = 300  # 5 минут блокировки
        self._circuit_breaker_last_failure = 0
        self._circuit_breaker_open = False
    
    def validate_file(self, file_path: str):
        """Проверяет файл на соответствие ограничениям"""
        # Проверка существования файла
        if not os.path.exists(file_path):
            raise StorageValidationError(f"Файл не существует: {file_path}", field="file_path")
            
        # Проверка размера
        size = os.path.getsize(file_path)
        if size > self.MAX_FILE_SIZE:
            raise StorageValidationError(
                f"Файл слишком большой: {size} байт (максимум {self.MAX_FILE_SIZE} байт)", 
                field="file_size"
            )
        
        # Проверка MIME типа
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            raise StorageValidationError(f"Невозможно определить тип файла: {file_path}", field="mime_type")
        
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise StorageValidationError(f"Неподдерживаемый тип файла: {mime_type}", field="mime_type")
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Вычисляет SHA-256 хеш файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _wait_for_rate_limit(self):
        """Улучшенный rate limiting с jitter для предотвращения thundering herd"""
        # Базовая задержка согласно Pinata API рекомендациям
        base_delay = self.REQUEST_DELAY
        
        # Добавляем jitter (случайность) для предотвращения одновременных запросов
        jitter = random.uniform(0.5, 2.0)  # Случайность 0.5-2 секунды
        total_delay = base_delay + jitter
        
        logger.info(f"[Pinata] Rate limiting: ожидание {total_delay:.2f}s (базовая: {base_delay}s + jitter: {jitter:.2f}s)")
        time.sleep(total_delay)
        
        # Обновляем время последнего запроса
        self._last_request_time = time.time()
    
    def _check_circuit_breaker(self):
        """Проверяет состояние circuit breaker"""
        if self._circuit_breaker_open:
            current_time = time.time()
            if current_time - self._circuit_breaker_last_failure > self._circuit_breaker_timeout:
                logger.info("[Pinata] Circuit breaker: переход в полуоткрытое состояние")
                self._circuit_breaker_open = False
                self._consecutive_errors = 0
            else:
                raise StorageRateLimitError(
                    f"Circuit breaker открыт. Повторите через {self._circuit_breaker_timeout - (current_time - self._circuit_breaker_last_failure):.0f} секунд",
                    retry_after=self._circuit_breaker_timeout
                )
    
    def _record_success(self):
        """Записывает успешную операцию"""
        self._consecutive_errors = 0
        self._circuit_breaker_open = False
    
    def _record_error(self):
        """Записывает ошибку и проверяет circuit breaker"""
        self._consecutive_errors += 1
        self._circuit_breaker_last_failure = time.time()
        
        if self._consecutive_errors >= self._circuit_breaker_threshold:
            self._circuit_breaker_open = True
            logger.error(f"[Pinata] Circuit breaker открыт после {self._consecutive_errors} ошибок подряд")
    
    @retry_with_backoff(retries=MAX_RETRIES, backoff_in_seconds=INITIAL_BACKOFF)
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Выполняет HTTP запрос с учетом ограничений и авторизации"""
        start_time = time.time()
        
        # Проверяем circuit breaker перед выполнением запроса
        self._check_circuit_breaker()
        
        try:
            self._wait_for_rate_limit()
            
            # Добавляем заголовки авторизации если их нет
            headers = kwargs.pop('headers', {})
            if url.startswith(self.api_url):  # Для API запросов
                headers.update(self.base_headers)
            
            timeout = kwargs.pop('timeout', self.REQUEST_TIMEOUT)
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            
            # Проверяем статус код и создаем соответствующие исключения
            if response.status_code != 200:
                # Записываем ошибку для circuit breaker
                self._record_error()
                
                provider = "pinata" if url.startswith(self.api_url) else "gateway"
                error = create_storage_error_from_http_response(
                    response.status_code, 
                    f"HTTP {response.status_code} error", 
                    provider
                )
                logger.error(f"HTTP error {response.status_code}: {error}")
                self.metrics.track_error(f"http_{response.status_code}")
                raise error
            
            # Записываем успешную операцию для circuit breaker
            self._record_success()
            
            return response
            
        except requests.exceptions.Timeout:
            error = StorageTimeoutError("Request timeout", provider="pinata", timeout=timeout)
            logger.error(f"Request timeout: {error}")
            self.metrics.track_error("timeout")
            raise error
        except requests.exceptions.ConnectionError as e:
            error = StorageNetworkError("Connection error", provider="pinata", original_error=e)
            logger.error(f"Connection error: {error}")
            self.metrics.track_error("connection_error")
            raise error
        except StorageError:
            # Перебрасываем уже созданные StorageError исключения
            raise
        except Exception as e:
            error = create_storage_error_from_exception(e, provider="pinata")
            logger.error(f"Unexpected error: {error}")
            self.metrics.track_error("unexpected_error")
            raise error
        finally:
            duration = time.time() - start_time
            if method == 'POST':  # Только для загрузок
                self.metrics.track_upload(duration)
    
    def update_cache_if_needed(self):
        """Обновляет кэш, если прошло достаточно времени"""
        if self.cache.needs_update():
            try:
                logger.info("Обновляем кэш из Pinata API...")
                response = self._make_request(
                    'GET',
                    f"{self.api_url}/data/pinList",
                    headers=self.json_headers,
                    timeout=10  # Добавляем таймаут 10 секунд
                )
                pins = response.json().get('rows', [])
                self.cache.update_from_pins(pins)
                logger.info("Кэш успешно обновлен")
            except Exception as e:
                logger.error(f"Ошибка при обновлении кэша: {e}")
                self.metrics.track_error("cache_update_error")
                # Не падаем, просто логируем ошибку
    
    def find_file_by_name(self, file_name: str) -> Optional[Tuple[str, Dict]]:
        """
        Ищет файл по имени в кэше, при необходимости обновляя его.
        Возвращает кортеж (CID, метаданные) или None, если файл не найден.
        """
        self.update_cache_if_needed()
        
        file_info = self.cache.get_file(file_name)
        if file_info:
            self.metrics.track_cache_hit()
            return file_info['cid'], file_info['metadata']
        self.metrics.track_cache_miss()
        return None
    
    def upload_text(self, data: Union[str, dict], file_name: Optional[str] = None) -> str:
        """Загружает текстовые данные в IPFS через JSON API"""
        try:
            logger.info("Начинаем загрузку текстовых данных в IPFS")
            
            # Валидация входных данных
            if not data:
                raise StorageValidationError("Data cannot be empty", field="data")
            
            # Подготовка данных
            if isinstance(data, str):
                try:
                    # Пробуем распарсить как JSON
                    json_data = json.loads(data)
                    payload = {"pinataContent": json_data}
                except json.JSONDecodeError:
                    # Если не JSON, загружаем как текст
                    payload = {"pinataContent": {"text": data}}
            else:
                payload = {"pinataContent": data}
            
            # Добавляем метаданные с именем файла, если оно предоставлено
            if file_name:
                payload["pinataMetadata"] = {
                    "name": file_name
                }
            
            logger.info("Отправляем запрос в Pinata JSON API")
            response = self._make_request(
                'POST',
                f"{self.api_url}/pinning/pinJSONToIPFS",
                headers=self.json_headers,
                json=payload
            )
            
            result = response.json()
            cid = result.get('IpfsHash')
            if cid:
                logger.info(f"Успешно получен CID: {cid}")
                # Обновляем кэш
                if file_name:
                    self.cache.update_file(file_name, cid, payload.get("pinataMetadata"))
                return cid
            else:
                logger.error(f"Не удалось получить CID из ответа: {result}")
                self.metrics.track_error("missing_cid")
                raise StorageProviderError("No CID in response", provider="pinata")
                
        except StorageError:
            # Перебрасываем уже созданные StorageError исключения
            raise
        except Exception as e:
            error = create_storage_error_from_exception(e, provider="pinata")
            logger.error(f"Ошибка при загрузке в IPFS: {error}")
            self.metrics.track_error("upload_error")
            raise error
    
    def upload_file(self, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> str:
        """Загружает файл или данные в IPFS"""
        try:
            logger.info(f"Начинаем загрузку в IPFS: {file_path_or_data if isinstance(file_path_or_data, str) else 'data'}")
            
            # Если передан путь к файлу и он существует
            if isinstance(file_path_or_data, str) and os.path.exists(file_path_or_data):
                # Проверяем файл
                self.validate_file(file_path_or_data)
                
                # Вычисляем хеш файла
                file_hash = self.calculate_file_hash(file_path_or_data)
                logger.debug(f"SHA-256 хеш файла: {file_hash}")
                
                with open(file_path_or_data, 'rb') as f:
                    actual_file_name = file_name or os.path.basename(file_path_or_data)
                    files = {
                        'file': (actual_file_name, f, 'application/octet-stream')
                    }
                    logger.info(f"Загружаем файл: {actual_file_name}")
                    
                    response = self._make_request(
                        'POST',
                        f"{self.api_url}/pinning/pinFileToIPFS",
                        files=files
                    )
                    
                    result = response.json()
                    cid = result.get('IpfsHash')
                    if cid:
                        logger.info(f"Успешно получен CID: {cid}")
                        # Обновляем кэш
                        metadata = {
                            "name": actual_file_name,
                            "sha256": file_hash
                        }
                        self.cache.update_file(actual_file_name, cid, metadata)
                        return cid
                    else:
                        logger.error(f"Не удалось получить CID из ответа: {result}")
                        self.metrics.track_error("missing_cid")
                        raise StorageProviderError("No CID in response", provider="pinata")
            else:
                # Если переданы данные вместо пути к файлу
                logger.info("Обнаружены данные вместо пути к файлу, используем upload_text")
                return self.upload_text(file_path_or_data, file_name)
                    
        except StorageError:
            # Перебрасываем уже созданные StorageError исключения
            raise
        except Exception as e:
            error = create_storage_error_from_exception(e, provider="pinata")
            logger.error(f"Ошибка при загрузке в IPFS: {error}")
            self.metrics.track_error("upload_error")
            raise error
    
    def download_json(self, cid: str) -> Optional[Dict]:
        """Загружает JSON данные из IPFS"""
        try:
            # Валидация CID
            if not cid:
                raise StorageValidationError("CID cannot be empty", field="cid")
            
            if cid.startswith("ipfs://"):
                cid = cid.replace("ipfs://", "")
                
            url = f"{self.gateway_url}/{cid}"
            logger.info(f"Downloading JSON from {url}")
            
            # Увеличиваем задержку перед скачиванием
            time.sleep(3)
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = self._make_request('GET', url)
                    result = response.json()
                    logger.info(f"Successfully downloaded JSON from {url}, result type: {type(result)}")
                    return result
                except StorageRateLimitError:
                    if attempt == self.MAX_RETRIES - 1:
                        raise
                    sleep = (self.INITIAL_BACKOFF * 2 ** attempt + random.uniform(0, 1))
                    logger.warning(f"Rate limit hit, waiting {sleep:.2f} seconds...")
                    time.sleep(sleep)
                    continue
                except StorageError:
                    # Перебрасываем другие StorageError исключения
                    raise
                
        except StorageError:
            # Перебрасываем уже созданные StorageError исключения
            raise
        except Exception as e:
            error = create_storage_error_from_exception(e, provider="pinata")
            logger.error(f"Ошибка при скачивании JSON для CID {cid}: {error}")
            self.metrics.track_error("download_error")
            raise error
    
    def get_gateway_url(self, cid: str) -> str:
        """Возвращает URL для доступа к файлу через gateway"""
        if cid.startswith("ipfs://"):
            cid = cid.replace("ipfs://", "")
        return f"{self.gateway_url}/{cid}"

    def get_public_url(self, cid: str) -> str:
        """
        Возвращает публичный URL для доступа к изображению.
        Используется для отображения в Telegram и других публичных интерфейсах.
        
        Args:
            cid: IPFS CID файла
            
        Returns:
            str: Полный публичный URL для доступа к файлу
        """
        return self.get_gateway_url(cid)

    def upload_files_batch(self, files: List[Tuple[str, str]], max_workers: Optional[int] = None) -> Dict[str, Optional[str]]:
        """
        Загружает batch файлов в IPFS используя многопоточность.
        
        Args:
            files: Список кортежей (путь_к_файлу, имя_файла)
            max_workers: Максимальное количество потоков (по умолчанию: кол-во CPU * 5)
            
        Returns:
            Словарь {имя_файла: cid} с результатами загрузки
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Создаем задачи для загрузки
            future_to_file = {
                executor.submit(self.upload_file, path, name): (path, name)
                for path, name in files
            }
            
            # Обрабатываем результаты по мере завершения
            for future in as_completed(future_to_file):
                file_path, file_name = future_to_file[future]
                try:
                    cid = future.result()
                    results[file_name] = cid
                    if cid:
                        logger.info(f"✅ Успешно загружен {file_name}: {cid}")
                    else:
                        logger.error(f"❌ Не удалось загрузить {file_name}")
                except Exception as e:
                    logger.error(f"❌ Ошибка при загрузке {file_name}: {e}")
                    self.metrics.track_error("batch_upload_error")
                    results[file_name] = None
        
        return results

    async def upload_json(self, data: dict) -> str:
        """
        Асинхронная загрузка JSON данных в IPFS
        """
        temp_file_path = None
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                json.dump(data, temp_file, ensure_ascii=False)
                temp_file_path = temp_file.name
            
            logger.info(f"Начинаем загрузку в IPFS: {temp_file_path}")
            
            # Вычисляем хеш файла
            file_hash = self.calculate_file_hash(temp_file_path)
            logger.debug(f"SHA-256 хеш файла: {file_hash}")
            
            # Проверяем кэш
            cached_file = self.cache.get_file(file_hash)
            if cached_file:
                logger.info(f"Найден в кэше: {cached_file['cid']}")
                return cached_file['cid']
            
            # Загружаем файл
            logger.info(f"Загружаем файл: {os.path.basename(temp_file_path)}")
            
            # Запускаем синхронную загрузку в отдельном потоке
            loop = asyncio.get_event_loop()
            cid = await loop.run_in_executor(None, self.upload_file, temp_file_path)
            
            # Обновляем кэш
            if cid:
                self.cache.update_file(file_hash, cid, {'name': file_hash})
                return cid
            else:
                raise StorageProviderError("Failed to upload JSON file", provider="pinata")
            
        except StorageError:
            # Перебрасываем уже созданные StorageError исключения
            raise
        except Exception as e:
            error = create_storage_error_from_exception(e, provider="pinata")
            logger.error(f"Ошибка при асинхронной загрузке JSON в IPFS: {error}")
            self.metrics.track_error("async_upload_error")
            raise error
        finally:
            # Удаляем временный файл
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {temp_file_path}: {e}")