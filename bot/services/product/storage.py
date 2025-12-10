from typing import Optional, Dict, Any
import logging
import aiohttp
import re
import asyncio
from services.core.ipfs_factory import IPFSFactory
from config import STORAGE_COMMUNICATION_TYPE

logger = logging.getLogger(__name__)

class ProductStorageService:
    """Сервис для работы с хранилищами (IPFS)"""
    
    # Регулярное выражение для валидации IPFS CID
    IPFS_CID_PATTERN = re.compile(r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[A-Za-z2-7]{55})$')
    
    def __init__(self, storage_provider=None):
        """
        Инициализирует ProductStorageService.
        
        Args:
            storage_provider: Провайдер хранилища (IPFS/Arweave). 
                            Если None, создается через IPFSFactory.
        """
        # Для обратной совместимости: если storage_provider не передан, используем фабрику
        if storage_provider is None:
            self.ipfs = IPFSFactory().get_storage()
        else:
            self.ipfs = storage_provider
            
        self.logger = logging.getLogger(__name__)
        self.communication_type = STORAGE_COMMUNICATION_TYPE
        self.logger.info(f"[ProductStorageService] Тип коммуникации: {self.communication_type}")
    
    def validate_ipfs_cid(self, cid: str) -> bool:
        """
        Проверяет валидность CID (IPFS или Arweave transaction ID).
        
        Поддерживает:
        - IPFS CID v0 (Qm..., 46 символов)
        - IPFS CID v1 (bafy..., >46 символов)
        - Arweave transaction ID (43 символа, base64url: A-Za-z0-9_-)
        """
        if not cid:
            return False
        
        # IPFS CID (Qm... или bafy...)
        if self.IPFS_CID_PATTERN.match(cid):
            return True
        
        # Arweave transaction ID (43 символа, base64url: A-Za-z0-9_-)
        if len(cid) == 43 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in cid):
            return True
        
        return False
    
    def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Синхронный метод для загрузки JSON из IPFS.
        Автоматически адаптируется к типу провайдера и режиму коммуникации.
        """
        try:
            if not self.validate_ipfs_cid(cid):
                self.logger.warning(f"Invalid CID format: {cid}")
                return None
            
            self.logger.debug(f"[ProductStorageService] Загружаем JSON для CID: {cid}, тип коммуникации: {self.communication_type}")
            
            # 🔧 ИСПРАВЛЕНИЕ: Проверяем доступные методы у провайдера
            has_async = hasattr(self.ipfs, 'download_json_async')
            has_sync = hasattr(self.ipfs, 'download_json')
            
            self.logger.debug(f"[ProductStorageService] Провайдер {type(self.ipfs)}: async={has_async}, sync={has_sync}")
            
            # Выбираем стратегию на основе типа коммуникации и доступных методов
            if self.communication_type == "sync":
                # 🔧 СИНХРОННЫЙ РЕЖИМ: Прямой вызов для Pinata, моков
                if has_sync:
                    self.logger.debug(f"[ProductStorageService] Sync mode: прямой вызов download_json для CID: {cid}")
                    result = self.ipfs.download_json(cid)
                    self.logger.debug(f"[ProductStorageService] Sync mode: результат получен, тип: {type(result)}")
                    return result
                else:
                    # Fallback для async провайдеров в sync режиме
                    self.logger.debug(f"[ProductStorageService] Sync mode: fallback на async через asyncio.run для CID: {cid}")
                    try:
                        result = asyncio.run(self.ipfs.download_json_async(cid))
                        self.logger.debug(f"[ProductStorageService] Sync mode fallback: результат получен, тип: {type(result)}")
                        return result
                    except Exception as e:
                        self.logger.error(f"Sync mode fallback failed: {e}")
                        return None
                    
            elif self.communication_type == "async":
                # 🔧 АСИНХРОННЫЙ РЕЖИМ: Через asyncio.run для Arweave
                if has_async:
                    self.logger.debug(f"[ProductStorageService] Async mode: используем download_json_async через asyncio.run для CID: {cid}")
                    try:
                        result = asyncio.run(self.ipfs.download_json_async(cid))
                        self.logger.debug(f"[ProductStorageService] Async mode: результат получен, тип: {type(result)}")
                        return result
                    except Exception as e:
                        self.logger.error(f"Async mode failed: {e}")
                        return None
                elif has_sync:
                    # Fallback: sync метод напрямую
                    self.logger.debug(f"[ProductStorageService] Async mode: fallback на sync метод для CID: {cid}")
                    result = self.ipfs.download_json(cid)
                    self.logger.debug(f"[ProductStorageService] Async mode fallback: результат получен, тип: {type(result)}")
                    return result
                else:
                    self.logger.error(f"IPFS провайдер не поддерживает download_json методы: {type(self.ipfs)}")
                    return None
                    
            elif self.communication_type == "hybrid":
                # 🔧 ГИБРИДНЫЙ РЕЖИМ: Сначала async через asyncio.run, потом sync
                if has_async:
                    self.logger.debug(f"[ProductStorageService] Hybrid mode: пробуем async метод через asyncio.run для CID: {cid}")
                    try:
                        result = asyncio.run(self.ipfs.download_json_async(cid))
                        self.logger.debug(f"[ProductStorageService] Hybrid mode: результат получен, тип: {type(result)}")
                        return result
                    except Exception as e:
                        self.logger.warning(f"Hybrid mode async failed, falling back to sync: {e}")
                        if has_sync:
                            result = self.ipfs.download_json(cid)
                            self.logger.debug(f"[ProductStorageService] Hybrid mode fallback: результат получен, тип: {type(result)}")
                            return result
                        else:
                            self.logger.error(f"Hybrid mode: no fallback available")
                            return None
                elif has_sync:
                    self.logger.debug(f"[ProductStorageService] Hybrid mode: используем sync метод для CID: {cid}")
                    result = self.ipfs.download_json(cid)
                    self.logger.debug(f"[ProductStorageService] Hybrid mode: результат получен, тип: {type(result)}")
                    return result
                else:
                    self.logger.error(f"IPFS провайдер не поддерживает download_json методы: {type(self.ipfs)}")
                    return None
            else:
                self.logger.error(f"Неизвестный тип коммуникации: {self.communication_type}")
                return None
                
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