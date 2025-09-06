import logging
from dotenv import load_dotenv
import os
from services.core.storage.pinata import SecurePinataUploader
from services.core.storage.ar_weave import ArWeaveUploader
from config import STORAGE_COMMUNICATION_TYPE

logger = logging.getLogger(__name__)

load_dotenv(dotenv_path="bot/.env")

STORAGE_TYPE = os.getenv("STORAGE_TYPE")


class IPFSFactory:
    """
    Фабрика для создания провайдеров IPFS хранилища.
    Поддерживает Pinata и Arweave провайдеры.
    """
    
    def __init__(self):
        """Инициализирует фабрику с Pinata провайдером по умолчанию"""
        self.set_storage(STORAGE_TYPE)
        logger.info(f"[IPFSFactory] Инициализирована фабрика IPFS с типом коммуникации: {STORAGE_COMMUNICATION_TYPE}")

    def get_storage(self):
        """Возвращает текущий провайдер хранилища"""
        return self.storage
    
    def set_storage(self, storage_type: str):
        """
        Устанавливает тип провайдера хранилища.
        
        Args:
            storage_type: Тип провайдера ('pinata' или 'arweave')
        """
        if storage_type.lower() == 'pinata':
            self.storage = SecurePinataUploader()
            logger.info("[IPFSFactory] Установлен Pinata провайдер")
        elif storage_type.lower() == 'arweave':
            self.storage = ArWeaveUploader()
            logger.info("[IPFSFactory] Установлен Arweave провайдер")
        else:
            raise ValueError(f"Неподдерживаемый тип хранилища: {storage_type}")