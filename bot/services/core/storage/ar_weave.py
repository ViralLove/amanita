import os
import requests
import mimetypes
import traceback
import json
import time
from typing import Optional, Dict, Any, Union

from dotenv import load_dotenv

import logging
logger = logging.getLogger(__name__)

# Импорт конфигурации (ключ ArWeave не нужен: загрузка через Edge, чтение — публичное)
from config import SUPABASE_URL, SUPABASE_ANON_KEY

from ..edge_client import SupabaseEdgeClient, get_edge_mock_headers, SupabaseEdgeClientWithMockHeaders
from .base import BaseStorageProvider


def _default_edge_client():
    """Клиент Edge по умолчанию: с мок-заголовками из env при EDGE_USE_MOCK, иначе без них."""
    base_url = f"{SUPABASE_URL}/functions/v1/arweave-upload"
    if get_edge_mock_headers():
        return SupabaseEdgeClientWithMockHeaders(base_url, SUPABASE_ANON_KEY or "")
    return SupabaseEdgeClient(base_url, SUPABASE_ANON_KEY or "")


class ArWeaveUploader(BaseStorageProvider):
    def __init__(self, edge_client=None):
        load_dotenv()
        self.edge_client = edge_client if edge_client is not None else _default_edge_client()
        self.edge_function_url = f"{SUPABASE_URL}/functions/v1/arweave-upload"
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
        Вызывает Supabase Edge Function через абстракцию edge_client.
        """
        if not SUPABASE_ANON_KEY:
            logger.error("[ArWeave] SUPABASE_ANON_KEY не установлен - невозможно вызвать Edge Function")
            return None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"[ArWeave] Попытка {attempt + 1}/{self.max_retries} вызова Edge Function: {endpoint}")
                response = self.edge_client.post(
                    endpoint, data=data, is_file=is_file, timeout=self.timeout
                )
                if response is None:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None
                logger.debug(f"[ArWeave] Edge Function ответ: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("transaction_id"):
                        logger.info(f"[ArWeave] ✅ Edge Function успешно загрузил данные: {result['transaction_id']}")
                        return result["transaction_id"]
                    logger.error(f"[ArWeave] Edge Function вернул ошибку: {result}")
                    return None
                logger.error(f"[ArWeave] Edge Function HTTP ошибка: {response.status_code} - {response.text}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
            except requests.exceptions.RequestException as e:
                logger.error(f"[ArWeave] Ошибка сети при вызове Edge Function: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                logger.error(f"[ArWeave] Неожиданная ошибка при вызове Edge Function: {e}")
                return None
        return None

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

    def is_cid_available(self, cid: str, timeout: int = 10) -> bool:
        """
        Проверка доступности контента по CID по сети (HEAD/GET arweave.net).
        Для сценариев «контент реально доступен» (task 3.3, DP-4).
        """
        try:
            if cid.startswith("ar://"):
                cid = cid.replace("ar://", "")
            url = f"https://arweave.net/{cid}"
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 405:
                response = requests.get(url, timeout=timeout, stream=True)
                response.close()
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
        except Exception:
            return False