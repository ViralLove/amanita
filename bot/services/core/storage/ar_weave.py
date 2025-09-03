import os
import requests
import mimetypes
import traceback
import json
import time
from typing import Optional, Dict, Any, Union

from dotenv import load_dotenv
# from arweave import Wallet, Transaction  # Закомментировано из-за проблем с зависимостями

import logging
logger = logging.getLogger(__name__)

# Импорт конфигурации
from bot.config import SUPABASE_URL, SUPABASE_ANON_KEY, ARWEAVE_PRIVATE_KEY

from .base import BaseStorageProvider

class ArWeaveUploader(BaseStorageProvider):
    def __init__(self):
        load_dotenv()
        
        # Используем импортированную переменную из config
        if not ARWEAVE_PRIVATE_KEY:
            raise FileNotFoundError("ARWEAVE_PRIVATE_KEY is missing.")
        
        logger.info(f"ARWEAVE_PRIVATE_KEY: {ARWEAVE_PRIVATE_KEY[:50]}..." if len(ARWEAVE_PRIVATE_KEY) > 50 else ARWEAVE_PRIVATE_KEY)
        
        # Проверяем, является ли ключ JSON строкой или файлом
        if ARWEAVE_PRIVATE_KEY.startswith('{'):
            logger.info("ARWEAVE_PRIVATE_KEY установлен как JSON строка")
            self.private_key = ARWEAVE_PRIVATE_KEY
        else:
            if not os.path.isfile(ARWEAVE_PRIVATE_KEY):
                raise FileNotFoundError(f"ARWEAVE_PRIVATE_KEY file does not exist: {ARWEAVE_PRIVATE_KEY}")
            logger.info("ARWEAVE_PRIVATE_KEY установлен как путь к файлу")
            self.private_key = ARWEAVE_PRIVATE_KEY
        
        # Валидация ключа
        self._validate_key(self.private_key)
        
        # Кошелек загружается из JSON-ключа
        # self.wallet = Wallet(private_key_path)  # Закомментировано из-за проблем с зависимостями
        self.wallet = None  # Временная заглушка
        
        # Инициализация HTTP клиента для Edge Functions
        self._init_edge_function_client()
        
        # Проверка баланса (если SDK доступен)
        # self._check_balance()

    def _init_edge_function_client(self):
        """Инициализация HTTP клиента для Edge Functions"""
        self.edge_function_url = f"{SUPABASE_URL}/functions/v1/arweave-upload"
        self.edge_function_headers = {
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
            'Content-Type': 'application/json'
        }
        self.timeout = 30
        self.max_retries = 3
        
        logger.info(f"[ArWeave] Edge Function URL: {self.edge_function_url}")
        if not SUPABASE_ANON_KEY:
            logger.warning("[ArWeave] SUPABASE_ANON_KEY не установлен - Edge Functions недоступны")

    def get_public_url(self, transaction_id: str) -> str:
        """
        Возвращает публичный URL для доступа к изображению в ArWeave.
        Используется для отображения в Telegram и других публичных интерфейсах.
        
        Args:
            transaction_id: ArWeave transaction ID файла
            
        Returns:
            str: Полный публичный URL для доступа к файлу
        """
        # ArWeave использует прямой доступ через transaction ID
        return f"https://arweave.net/{transaction_id}"

    def _call_edge_function(self, endpoint: str, data: Dict[str, Any], is_file: bool = False) -> Optional[str]:
        """
        Вызывает Supabase Edge Function для загрузки данных
        
        Args:
            endpoint: Endpoint edge function (/upload-text или /upload-file)
            data: Данные для отправки
            is_file: True если загружается файл (использует multipart)
        
        Returns:
            transaction_id или None при ошибке
        """
        if not SUPABASE_ANON_KEY:
            logger.error("[ArWeave] SUPABASE_ANON_KEY не установлен - невозможно вызвать Edge Function")
            return None
        
        url = f"{self.edge_function_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"[ArWeave] Попытка {attempt + 1}/{self.max_retries} вызова Edge Function: {endpoint}")
                
                if is_file:
                    # Для файлов используем multipart/form-data
                    with open(data['file_path'], 'rb') as f:
                        files = {'file': (os.path.basename(data['file_path']), f, data.get('content_type', 'application/octet-stream'))}
                        response = requests.post(
                            url,
                            files=files,
                            headers={'Authorization': f'Bearer {SUPABASE_ANON_KEY}'},
                            timeout=self.timeout
                        )
                else:
                    # Для текста используем JSON
                    response = requests.post(
                        url,
                        json=data,
                        headers=self.edge_function_headers,
                        timeout=self.timeout
                    )
                
                logger.debug(f"[ArWeave] Edge Function ответ: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success') and result.get('transaction_id'):
                        logger.info(f"[ArWeave] ✅ Edge Function успешно загрузил данные: {result['transaction_id']}")
                        return result['transaction_id']
                    else:
                        logger.error(f"[ArWeave] Edge Function вернул ошибку: {result}")
                        return None
                else:
                    logger.error(f"[ArWeave] Edge Function HTTP ошибка: {response.status_code} - {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"[ArWeave] Ошибка сети при вызове Edge Function: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
            except Exception as e:
                logger.error(f"[ArWeave] Неожиданная ошибка при вызове Edge Function: {e}")
                return None
        
        return None

    def _validate_key(self, key_path: str):
        """Валидация формата приватного ключа ArWeave"""
        try:
            # Проверяем, является ли ключ JSON строкой или файлом
            if key_path.startswith('{'):
                # Это JSON строка
                key_data = json.loads(key_path)
            else:
                # Это путь к файлу
                with open(key_path, 'r') as f:
                    key_data = json.load(f)
            
            # Проверяем обязательные поля RSA ключа
            required_fields = ['kty', 'n', 'e', 'd']
            for field in required_fields:
                if field not in key_data:
                    raise ValueError(f"Отсутствует обязательное поле '{field}' в ключе")
            
            if key_data.get('kty') != 'RSA':
                raise ValueError("Ключ должен быть RSA типа")
                
            logger.info("✅ Приватный ключ ArWeave валиден")
            
        except json.JSONDecodeError:
            raise ValueError("Неверный формат JSON в ключе")
        except Exception as e:
            raise ValueError(f"Ошибка валидации ключа: {e}")

    def _check_balance(self):
        """Проверка баланса кошелька (если SDK доступен)"""
        if self.wallet:
            try:
                # balance = self.wallet.balance
                # logger.info(f"Баланс кошелька: {balance} AR")
                pass
            except Exception as e:
                logger.warning(f"Не удалось проверить баланс: {e}")

    def upload_text(self, text: str, content_type: str = "text/plain") -> str:
        """
        Загружает текстовый контент (например, JSON) в Arweave через Edge Function.
        Возвращает transaction ID или error строку при неудаче.
        """
        try:
            logger.info(f"[ArWeave] Начинаем загрузку текста размером {len(text)} байт через Edge Function")
            
            # Используем Edge Function для загрузки
            if not SUPABASE_ANON_KEY:
                logger.error("[ArWeave] SUPABASE_ANON_KEY не установлен - невозможно загрузить данные")
                return "arweave_upload_error_no_key"
            
            data = {
                "data": text,
                "contentType": content_type
            }
            
            transaction_id = self._call_edge_function("/upload-text", data)
            if transaction_id:
                logger.info(f"[ArWeave] ✅ Edge Function успешно загрузил текст: {transaction_id}")
                return transaction_id
            else:
                logger.error("[ArWeave] Edge Function вернул None")
                return "arweave_upload_error"
                
        except Exception as e:
            logger.error(f"[ArWeave] Ошибка загрузки текста: {e}")
            logger.error(f"[ArWeave] Traceback: {traceback.format_exc()}")
            return "arweave_upload_exception"



    def upload_file(self, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> str:
        """
        Загружает файл (медиа или другой) в Arweave через Edge Function.
        Определяет Content-Type автоматически.
        Возвращает transaction ID или error строку при неудаче.
        """
        try:
            # Обрабатываем разные типы входных данных
            if isinstance(file_path_or_data, str):
                file_path = file_path_or_data
            elif isinstance(file_path_or_data, dict):
                # Если передан словарь, извлекаем путь к файлу
                file_path = file_path_or_data.get('file_path', '')
                if not file_path:
                    raise ValueError("Dictionary must contain 'file_path' key")
            else:
                raise TypeError("file_path_or_data must be string or dict")
            
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File {file_path} does not exist.")

            # Определяем Content-Type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = "application/octet-stream"

            logger.info(f"[ArWeave] Начинаем загрузку файла {file_path} через Edge Function")
            
            # Используем Edge Function для загрузки
            if not SUPABASE_ANON_KEY:
                logger.error("[ArWeave] SUPABASE_ANON_KEY не установлен - невозможно загрузить файл")
                return "arweave_file_upload_error_no_key"
            
            data = {
                "file_path": file_path,
                "content_type": content_type
            }
            
            transaction_id = self._call_edge_function("/upload-file", data, is_file=True)
            if transaction_id:
                logger.info(f"[ArWeave] ✅ Edge Function успешно загрузил файл: {transaction_id}")
                return transaction_id
            else:
                logger.error("[ArWeave] Edge Function вернул None")
                return "arweave_file_upload_error"
                
        except Exception as e:
            logger.error(f"[ArWeave] Ошибка загрузки файла: {e}")
            logger.error(f"[ArWeave] Traceback: {traceback.format_exc()}")
            return "arweave_file_upload_exception"



    def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Загружает JSON-файл с Arweave.
        Возвращает словарь с данными или None при ошибке.
        """
        try:
            # Используем основной домен arweave.net
            logger.debug(f"[ArWeave] Начинаем загрузку JSON для CID: {cid}")
            
            # Проверяем, не содержит ли CID уже префикс ar://
            if cid.startswith("ar://"):
                logger.debug(f"[ArWeave] Обнаружен префикс ar:// в CID, удаляем")
                cid = cid.replace("ar://", "")
            
            url = f"https://arweave.net/{cid}"
            logger.debug(f"[ArWeave] Сформирован URL для загрузки: {url}")
            
            logger.debug(f"[ArWeave] Отправляем GET запрос к {url}")
            response = requests.get(url, timeout=30)
            
            logger.debug(f"[ArWeave] Получен ответ от сервера:")
            logger.debug(f"[ArWeave] Статус: {response.status_code}")
            logger.debug(f"[ArWeave] Заголовки: {response.headers}")
            
            # Проверяем статус ответа
            if response.status_code == 404:
                logger.warning(f"[ArWeave] Файл не найден для CID: {cid}")
                return None
            elif response.status_code != 200:
                logger.error(f"[ArWeave] Ошибка HTTP {response.status_code} для CID: {cid}")
                return None
            
            # Проверяем, что ответ не пустой
            if not response.content:
                logger.warning(f"[ArWeave] Пустой ответ для CID: {cid}")
                return None
            
            # Пытаемся распарсить JSON
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"[ArWeave] Ошибка парсинга JSON для CID {cid}: {e}")
                logger.error(f"[ArWeave] Содержимое ответа: {response.text[:200]}...")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[ArWeave] Ошибка сети для CID {cid}: {e}")
            return None
        except Exception as e:
            logger.error(f"[ArWeave] Неожиданная ошибка для CID {cid}: {e}")
            logger.error(f"[ArWeave] Traceback: {traceback.format_exc()}")
            return None

    def download_file(self, cid: str) -> Optional[bytes]:
        """
        Загружает файл с Arweave.
        Возвращает байтовое представление данных или None при ошибке.
        """
        try:
            url = f"https://arweave.net/{cid}"
            logger.debug(f"[ArWeave] Загружаем файл с URL: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 404:
                logger.warning(f"[ArWeave] Файл не найден для CID: {cid}")
                return None
            elif response.status_code != 200:
                logger.error(f"[ArWeave] Ошибка HTTP {response.status_code} для CID: {cid}")
                return None
                
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ArWeave] Ошибка сети для CID {cid}: {e}")
            return None
        except Exception as e:
            logger.error(f"[ArWeave] Неожиданная ошибка для CID {cid}: {e}")
            logger.error(f"[ArWeave] Traceback: {traceback.format_exc()}")
            return None
    
    def is_valid_identifier(self, identifier: str) -> bool:
        """
        Проверяет валидность идентификатора для ArWeave.
        Поддерживает IPFS CID v0, CID v1 и ArWeave transaction ID.
        
        Args:
            identifier: Идентификатор файла (CID или transaction ID)
            
        Returns:
            bool: True если идентификатор валиден
        """
        if not identifier:
            return False
        
        # Базовая проверка - должен быть строкой
        if not isinstance(identifier, str):
            return False
        
        # IPFS CID v0 (начинается с Qm, 46 символов)
        if identifier.startswith("Qm"):
            return len(identifier) >= 46
        
        # IPFS CID v1 (начинается с bafy, длиннее 46 символов)
        if identifier.startswith("bafy"):
            return len(identifier) > 46
        
        # IPFS CID v1 другие префиксы (baf, bag, bah, bai, baj)
        if identifier.startswith(("baf", "bag", "bah", "bai", "baj")):
            return len(identifier) > 30
        
        # ArWeave transaction ID (43 символа, Base64)
        if len(identifier) == 43 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in identifier):
            return True
        
        # Если не соответствует ни одному формату
        return False