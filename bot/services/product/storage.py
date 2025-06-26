from typing import Optional, Dict, Any
import logging
import aiohttp
import re
from bot.services.core.ipfs_factory import IPFSFactory

logger = logging.getLogger(__name__)

class ProductStorageService:
    """Сервис для работы с хранилищами (IPFS)"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    # Регулярное выражение для валидации IPFS CID
    IPFS_CID_PATTERN = re.compile(r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[A-Za-z2-7]{55})$')
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            # Инициализация только при первом создании
            self.ipfs = IPFSFactory().get_storage()
            self.logger = logging.getLogger(__name__)
            self._initialized = True
    
    def validate_ipfs_cid(self, cid: str) -> bool:
        """Проверяет валидность IPFS CID"""
        if not cid:
            return False
        return bool(self.IPFS_CID_PATTERN.match(cid))
    
    async def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """Загружает JSON из IPFS"""
        try:
            if not self.validate_ipfs_cid(cid):
                self.logger.warning(f"Invalid CID format: {cid}")
                return None
                
            return await self.ipfs.download_json_async(cid)
            
        except Exception as e:
            self.logger.error(f"Error downloading JSON from IPFS: {e}")
            return None
    
    async def download_file(self, cid: str) -> Optional[bytes]:
        """Загружает файл из IPFS"""
        try:
            if not self.validate_ipfs_cid(cid):
                self.logger.warning(f"Invalid CID format: {cid}")
                return None
                
            return await self.ipfs.download_file(cid)
            
        except Exception as e:
            self.logger.error(f"Error downloading file from IPFS: {e}")
            return None
    
    def upload_media_file(self, file_path: str) -> Optional[str]:
        """Загружает медиафайл в Arweave"""
        try:
            return self.ipfs.upload_file(file_path)
        except Exception as e:
            self.logger.error(f"Error uploading file to IPFS: {e}")
            return None
    
    def upload_json(self, data: Dict[str, Any]) -> Optional[str]:
        """Загружает JSON в IPFS"""
        try:
            return self.ipfs.upload_json(data)
        except Exception as e:
            self.logger.error(f"Error uploading JSON to IPFS: {e}")
            return None
    
    def get_gateway_url(self, cid: str, gateway: str = "ipfs") -> Optional[str]:
        """Получает URL для доступа к файлу через gateway"""
        if not self.validate_ipfs_cid(cid):
            return None
            
        if gateway == "ipfs":
            return f"https://ipfs.io/ipfs/{cid}"
        elif gateway == "arweave":
            return f"https://arweave.net/{cid}"
        return None 