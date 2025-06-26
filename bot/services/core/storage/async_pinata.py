import os
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any, Union, List, Tuple
from datetime import datetime
import json
import traceback
from .pinata import SecurePinataCache, PinataMetrics
from dotenv import load_dotenv
import mimetypes
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class AsyncPinataUploader:
    """Асинхронная версия PinataUploader"""
    
    # Константы для настройки запросов
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1
    REQUEST_TIMEOUT = 30
    REQUEST_DELAY = 0.5
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Разрешенные MIME типы (такие же как в SecurePinataUploader)
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
        if not self.api_key or not self.secret_api_key:
            raise ValueError("Pinata API credentials are missing in .env")
        
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
        self._rate_limit_lock = asyncio.Lock()
    
    async def _wait_for_rate_limit(self):
        """Асинхронный rate limiting с фиксированной задержкой"""
        async with self._rate_limit_lock:
            current_time = datetime.now().timestamp()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.REQUEST_DELAY:
                sleep_time = self.REQUEST_DELAY - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
            self._last_request_time = datetime.now().timestamp()
    
    async def _make_request(self, session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> Dict:
        """Выполняет асинхронный HTTP запрос с учетом ограничений и авторизации"""
        start_time = datetime.now().timestamp()
        retries = 0
        
        while retries <= self.MAX_RETRIES:
            try:
                await self._wait_for_rate_limit()
                
                # Добавляем заголовки авторизации если их нет
                headers = kwargs.pop('headers', {})
                if url.startswith(self.api_url):  # Для API запросов
                    headers.update(self.base_headers)
                
                timeout = aiohttp.ClientTimeout(total=kwargs.pop('timeout', self.REQUEST_TIMEOUT))
                
                async with session.request(method, url, headers=headers, timeout=timeout, **kwargs) as response:
                    if response.status == 401:
                        logger.error("Ошибка авторизации в Pinata API")
                        self.metrics.track_error("auth_error")
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=401,
                            message="Unauthorized"
                        )
                    
                    response.raise_for_status()
                    return await response.json()
            
            except aiohttp.ClientError as e:
                retries += 1
                if retries > self.MAX_RETRIES:
                    logger.error(f"Превышено количество попыток: {e}")
                    self.metrics.track_error(type(e).__name__)
                    raise
                
                sleep_time = (self.INITIAL_BACKOFF * 2 ** (retries - 1))
                logger.warning(f"Попытка {retries}, ожидание {sleep_time} секунд...")
                await asyncio.sleep(sleep_time)
            
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                self.metrics.track_error(type(e).__name__)
                raise
            
            finally:
                duration = datetime.now().timestamp() - start_time
                if method == 'POST':  # Только для загрузок
                    self.metrics.track_upload(duration)
    
    def validate_file(self, file_path: str):
        """Проверяет файл на соответствие ограничениям"""
        # Проверка размера
        size = os.path.getsize(file_path)
        if size > self.MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой: {size} байт (максимум {self.MAX_FILE_SIZE} байт)")
        
        # Проверка MIME типа
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            raise ValueError(f"Невозможно определить тип файла: {file_path}")
        
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"Неподдерживаемый тип файла: {mime_type}")
    
    async def calculate_file_hash(self, file_path: str) -> str:
        """Асинхронно вычисляет SHA-256 хеш файла"""
        sha256_hash = hashlib.sha256()
        
        # Используем ThreadPoolExecutor для файловых операций
        def read_file():
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
        
        await asyncio.get_event_loop().run_in_executor(None, read_file)
        return sha256_hash.hexdigest()
    
    async def update_cache_if_needed(self, session: aiohttp.ClientSession):
        """Асинхронно обновляет кэш, если прошло достаточно времени"""
        if self.cache.needs_update():
            try:
                logger.info("Обновляем кэш из Pinata API...")
                response = await self._make_request(
                    session,
                    'GET',
                    f"{self.api_url}/data/pinList",
                    headers=self.json_headers
                )
                pins = response.get('rows', [])
                self.cache.update_from_pins(pins)
                logger.info("Кэш успешно обновлен")
            except Exception as e:
                logger.error(f"Ошибка при обновлении кэша: {e}")
                self.metrics.track_error("cache_update_error")
    
    async def find_file_by_name(self, session: aiohttp.ClientSession, file_name: str) -> Optional[Tuple[str, Dict]]:
        """
        Асинхронно ищет файл по имени в кэше, при необходимости обновляя его.
        Возвращает кортеж (CID, метаданные) или None, если файл не найден.
        """
        await self.update_cache_if_needed(session)
        
        file_info = self.cache.get_file(file_name)
        if file_info:
            return file_info['cid'], file_info['metadata']
        return None
    
    async def upload_text(self, session: aiohttp.ClientSession, data: Union[str, dict], file_name: Optional[str] = None) -> Optional[str]:
        """Асинхронно загружает текстовые данные в IPFS через JSON API"""
        try:
            logger.info("Начинаем загрузку текстовых данных в IPFS")
            
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
            result = await self._make_request(
                session,
                'POST',
                f"{self.api_url}/pinning/pinJSONToIPFS",
                headers=self.json_headers,
                json=payload
            )
            
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
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке в IPFS: {e}\n{traceback.format_exc()}")
            self.metrics.track_error("upload_error")
            return None
    
    async def upload_file(self, session: aiohttp.ClientSession, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> Optional[str]:
        """Асинхронно загружает файл или данные в IPFS"""
        try:
            logger.info(f"Начинаем загрузку в IPFS: {file_path_or_data if isinstance(file_path_or_data, str) else 'data'}")
            
            # Если передан путь к файлу и он существует
            if isinstance(file_path_or_data, str) and os.path.exists(file_path_or_data):
                # Проверяем файл
                self.validate_file(file_path_or_data)
                
                # Вычисляем хеш файла
                file_hash = await self.calculate_file_hash(file_path_or_data)
                logger.debug(f"SHA-256 хеш файла: {file_hash}")
                
                # Используем ThreadPoolExecutor для чтения файла
                def read_file():
                    with open(file_path_or_data, 'rb') as f:
                        return f.read()
                
                file_data = await asyncio.get_event_loop().run_in_executor(None, read_file)
                actual_file_name = file_name or os.path.basename(file_path_or_data)
                
                data = aiohttp.FormData()
                data.add_field('file',
                             file_data,
                             filename=actual_file_name,
                             content_type='application/octet-stream')
                
                logger.info(f"Загружаем файл: {actual_file_name}")
                result = await self._make_request(
                    session,
                    'POST',
                    f"{self.api_url}/pinning/pinFileToIPFS",
                    data=data
                )
                
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
                    return None
            else:
                # Если переданы данные вместо пути к файлу
                logger.info("Обнаружены данные вместо пути к файлу, используем upload_text")
                return await self.upload_text(session, file_path_or_data, file_name)
                    
        except Exception as e:
            logger.error(f"Ошибка при загрузке в IPFS: {e}\n{traceback.format_exc()}")
            self.metrics.track_error("upload_error")
            return None
    
    async def download_json(self, session: aiohttp.ClientSession, cid: str) -> Optional[Dict]:
        """Асинхронно загружает JSON данные из IPFS"""
        try:
            if cid.startswith("ipfs://"):
                cid = cid.replace("ipfs://", "")
                
            url = f"{self.gateway_url}/{cid}"
            result = await self._make_request(session, 'GET', url)
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании JSON для CID {cid}: {e}\n{traceback.format_exc()}")
            self.metrics.track_error("download_error")
            return None
    
    def get_gateway_url(self, cid: str) -> str:
        """Возвращает URL для доступа к файлу через gateway"""
        if cid.startswith("ipfs://"):
            cid = cid.replace("ipfs://", "")
        return f"{self.gateway_url}/{cid}"
    
    async def upload_files_batch(self, files: List[Tuple[str, str]]) -> Dict[str, Optional[str]]:
        """
        Асинхронно загружает batch файлов в IPFS.
        
        Args:
            files: Список кортежей (путь_к_файлу, имя_файла)
            
        Returns:
            Словарь {имя_файла: cid} с результатами загрузки
        """
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for file_path, file_name in files:
                task = asyncio.create_task(self.upload_file(session, file_path, file_name))
                tasks.append((file_name, task))
            
            for file_name, task in tasks:
                try:
                    cid = await task
                    results[file_name] = cid
                except Exception as e:
                    logger.error(f"Ошибка при загрузке {file_name}: {e}")
                    results[file_name] = None
                    self.metrics.track_error("batch_upload_error")
        
        return results 