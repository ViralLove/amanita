import os
import requests
import mimetypes
import traceback

from dotenv import load_dotenv
# from arweave import Wallet, Transaction  # Закомментировано из-за проблем с зависимостями

import logging
logger = logging.getLogger(__name__)

class ArWeaveUploader:
    def __init__(self):
        load_dotenv()
        private_key_path = os.getenv("ARWEAVE_PRIVATE_KEY")
        print(f"ARWEAVE_PRIVATE_KEY: {private_key_path}")
        if not private_key_path or not os.path.isfile(private_key_path):
            raise FileNotFoundError("ARWEAVE_PRIVATE_KEY is missing or file does not exist.")
        
        # Кошелек загружается из JSON-ключа
        # self.wallet = Wallet(private_key_path)  # Закомментировано из-за проблем с зависимостями
        self.wallet = None  # Временная заглушка

    def upload_text(self, text: str) -> str:
        """
        Загружает текстовый контент (например, JSON) в Arweave.
        Возвращает ссылку на Arweave.
        """
        # Закомментировано из-за проблем с ArWeave SDK
        # tx = Transaction(self.wallet, data=text.encode('utf-8'))
        # tx.add_tag('Content-Type', 'application/json')
        # tx.sign()
        # tx.send()
        # return tx.id
        logger.warning("ArWeave upload_text временно отключен из-за проблем с SDK")
        return "arweave_placeholder_id"

    def upload_file(self, file_path: str) -> str:
        """
        Загружает файл (медиа или другой) в Arweave.
        Определяет Content-Type автоматически.
        Возвращает ссылку на Arweave.
        """
        # Закомментировано из-за проблем с ArWeave SDK
        # if not os.path.isfile(file_path):
        #     raise FileNotFoundError(f"File {file_path} does not exist.")

        # with open(file_path, 'rb') as f:
        #     data = f.read()

        # # Определяем Content-Type
        # content_type, _ = mimetypes.guess_type(file_path)
        # if not content_type:
        #     content_type = "application/octet-stream"

        # tx = Transaction(self.wallet, data=data)
        # tx.add_tag('Content-Type', content_type)
        # tx.sign()
        # tx.send()
        # return tx.id
        logger.warning("ArWeave upload_file временно отключен из-за проблем с SDK")
        return "arweave_placeholder_id"

    def download_json(self, cid: str) -> dict:
        """
        Загружает JSON-файл с Arweave.
        Возвращает словарь с данными.
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
            response = requests.get(url)
            
            logger.debug(f"[ArWeave] Получен ответ от сервера:")
            logger.debug(f"[ArWeave] Статус: {response.status_code}")
            logger.debug(f"[ArWeave] Заголовки: {response.headers}")
            
            return response.json()
        except Exception as e:
            logger.error(f"[ArWeave] Ошибка загрузки JSON для CID {cid}: {e}")
            logger.error(f"[ArWeave] Traceback: {traceback.format_exc()}")
            raise

    def download_file(self, cid: str) -> bytes:
        """
        Загружает файл с Arweave.
        Возвращает байтовое представление данных.
        """
        try:
            url = f"https://arweave.net/{cid}"
            logger.debug(f"[ArWeave] Загружаем файл с URL: {url}")
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"[ArWeave] Ошибка загрузки файла для CID {cid}: {e}")
            logger.error(f"[ArWeave] URL: {url}")
            logger.error(f"[ArWeave] Traceback: {traceback.format_exc()}")
            raise