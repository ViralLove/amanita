"""
Сервис для управления API ключами AMANITA
"""
import os
import uuid
import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .blockchain import BlockchainService
from config import AMANITA_API_KEY, AMANITA_API_SECRET

logger = logging.getLogger(__name__)


class InvalidAPIKeyError(Exception):
    """Исключение для неверных API ключей"""
    pass


class ApiKeyService:
    """
    Сервис для управления API ключами
    
    Особенности:
    - API ключи хранятся в блокчейне с привязкой к селлеру
    - Секретные ключи шифруются и хранятся локально
    - Поддержка множественных ключей для одного селлера
    - Кэширование для производительности
    """
    
    def __init__(self, blockchain_service: BlockchainService):
        self.blockchain = blockchain_service
        self._init_encryption()
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 минут
        self._cache_timestamps: Dict[str, float] = {}
        
        logger.info("ApiKeyService инициализирован")
    
    def _init_encryption(self):
        """Инициализирует шифрование для секретных ключей"""
        # Получаем ключ шифрования из переменных окружения
        encryption_key = os.getenv("AMANITA_API_ENCRYPTION_KEY")
        
        if not encryption_key:
            # Генерируем новый ключ если не установлен
            encryption_key = Fernet.generate_key()
            logger.warning("AMANITA_API_ENCRYPTION_KEY не установлен, сгенерирован новый ключ")
            logger.warning("Установите AMANITA_API_ENCRYPTION_KEY в .env для production")
        
        # Преобразуем в bytes если это строка
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
        logger.info("Шифрование инициализировано")
    
    def _encrypt_secret_key(self, secret_key: str) -> str:
        """Шифрует секретный ключ"""
        encrypted = self.cipher.encrypt(secret_key.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_secret_key(self, encrypted_key: str) -> str:
        """Расшифровывает секретный ключ"""
        encrypted_bytes = base64.b64decode(encrypted_key.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def _generate_api_key(self) -> str:
        """Генерирует новый API ключ"""
        return f"ak_{uuid.uuid4().hex[:16]}"
    
    def _generate_secret_key(self) -> str:
        """Генерирует новый секретный ключ"""
        return f"sk_{uuid.uuid4().hex[:32]}"
    
    def _get_cache_key(self, api_key: str) -> str:
        """Получает ключ кэша для API ключа"""
        return f"api_key_{api_key}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверяет валидность кэша"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now().timestamp() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    def _update_cache(self, api_key: str, data: Dict):
        """Обновляет кэш"""
        cache_key = self._get_cache_key(api_key)
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.now().timestamp()
    
    def _get_from_cache(self, api_key: str) -> Optional[Dict]:
        """Получает данные из кэша"""
        cache_key = self._get_cache_key(api_key)
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        return None
    
    def _clear_cache(self, api_key: str):
        """Очищает кэш для API ключа"""
        cache_key = self._get_cache_key(api_key)
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
    
    async def create_api_key(self, seller_address: str, description: str = "") -> Dict[str, str]:
        """
        Создает новый API ключ для селлера
        
        Args:
            seller_address: Адрес селлера в блокчейне
            description: Описание ключа (опционально)
        
        Returns:
            Dict с api_key и secret_key
        """
        try:
            # Генерируем ключи
            api_key = self._generate_api_key()
            secret_key = self._generate_secret_key()
            
            # Шифруем секретный ключ
            encrypted_secret = self._encrypt_secret_key(secret_key)
            
            # Сохраняем в блокчейн (пока заглушка, в production будет реальный контракт)
            await self._register_api_key_in_blockchain(seller_address, api_key, description)
            
            # Сохраняем секретный ключ локально
            await self._save_secret_key_locally(api_key, encrypted_secret)
            
            # Обновляем кэш
            self._update_cache(api_key, {
                "seller_address": seller_address,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "active": True
            })
            
            logger.info(f"Создан новый API ключ для селлера {seller_address}", extra={
                "api_key": api_key,
                "seller_address": seller_address
            })
            
            return {
                "api_key": api_key,
                "secret_key": secret_key,  # Возвращаем незашифрованный для клиента
                "seller_address": seller_address,
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания API ключа для {seller_address}: {e}")
            raise
    
    async def _register_api_key_in_blockchain(self, seller_address: str, api_key: str, description: str):
        """Регистрирует API ключ в блокчейне (заглушка для MVP)"""
        # TODO: В production здесь будет вызов смарт-контракта
        # contract = self.blockchain.get_contract("AmanitaRegistry")
        # await self.blockchain.transact_contract_function(
        #     "AmanitaRegistry", 
        #     "registerApiKey", 
        #     self.blockchain.seller_key,
        #     seller_address, 
        #     api_key, 
        #     description
        # )
        
        logger.info(f"API ключ {api_key} зарегистрирован в блокчейне для {seller_address}")
    
    async def _save_secret_key_locally(self, api_key: str, encrypted_secret: str):
        """Сохраняет зашифрованный секретный ключ локально"""
        # TODO: В production использовать базу данных или защищенное хранилище
        # Пока используем простой файл (не для production!)
        storage_file = "api_keys.json"
        
        try:
            # Загружаем существующие ключи
            keys_data = {}
            if os.path.exists(storage_file):
                with open(storage_file, 'r') as f:
                    keys_data = json.load(f)
            
            # Добавляем новый ключ
            keys_data[api_key] = {
                "encrypted_secret": encrypted_secret,
                "created_at": datetime.now().isoformat()
            }
            
            # Сохраняем
            with open(storage_file, 'w') as f:
                json.dump(keys_data, f, indent=2)
            
            logger.debug(f"Секретный ключ для {api_key} сохранен локально")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения секретного ключа: {e}")
            raise
    
    async def validate_api_key(self, api_key: str) -> Dict[str, any]:
        """
        Валидирует API ключ и возвращает информацию о селлере
        
        Args:
            api_key: API ключ для валидации
        
        Returns:
            Dict с информацией о селлере и секретным ключом
        """
        try:
            # Проверяем кэш
            cached_data = self._get_from_cache(api_key)
            if cached_data and cached_data.get("active", True):
                # Получаем секретный ключ из локального хранилища
                secret_key = await self._get_secret_key_locally(api_key)
                if secret_key:
                    return {
                        "seller_address": cached_data["seller_address"],
                        "secret_key": secret_key,
                        "description": cached_data.get("description", ""),
                        "active": True
                    }
            
            # Если нет в кэше, проверяем блокчейн
            blockchain_data = await self._get_api_key_from_blockchain(api_key)
            if not blockchain_data:
                raise InvalidAPIKeyError(f"API ключ {api_key} не найден")
            
            # Получаем секретный ключ
            secret_key = await self._get_secret_key_locally(api_key)
            if not secret_key:
                raise InvalidAPIKeyError(f"Секретный ключ для {api_key} не найден")
            
            # Обновляем кэш
            self._update_cache(api_key, {
                "seller_address": blockchain_data["seller_address"],
                "description": blockchain_data.get("description", ""),
                "active": blockchain_data.get("active", True),
                "created_at": blockchain_data.get("created_at", datetime.now().isoformat())
            })
            
            return {
                "seller_address": blockchain_data["seller_address"],
                "secret_key": secret_key,
                "description": blockchain_data.get("description", ""),
                "active": blockchain_data.get("active", True)
            }
            
        except Exception as e:
            logger.warning(f"Ошибка валидации API ключа {api_key}: {e}")
            raise InvalidAPIKeyError(f"Неверный API ключ: {api_key}")
    
    async def _get_api_key_from_blockchain(self, api_key: str) -> Optional[Dict]:
        """Получает информацию об API ключе из блокчейна (заглушка для MVP)"""
        # Проверяем API ключ из .env (MVP)
        if api_key == AMANITA_API_KEY:
            try:
                # Получаем адрес селлера из приватного ключа
                seller_account = self.blockchain.seller_account
                return {
                    "seller_address": seller_account.address,
                    "active": True,
                    "description": "Seller API Key from .env"
                }
            except Exception as e:
                logger.error(f"Ошибка получения адреса селлера: {e}")
                return None
        
        # TODO: В production здесь будет вызов смарт-контракта
        # contract = self.blockchain.get_contract("AmanitaRegistry")
        # try:
        #     seller_address = contract.functions.getSellerByApiKey(api_key).call()
        #     if seller_address != "0x0000000000000000000000000000000000000000":
        #         return {
        #             "seller_address": seller_address,
        #             "active": contract.functions.isApiKeyActive(seller_address, api_key).call()
        #         }
        # except Exception as e:
        #     logger.error(f"Ошибка получения API ключа из блокчейна: {e}")
        
        # Заглушка для MVP - проверяем локальный файл
        storage_file = "api_keys.json"
        if os.path.exists(storage_file):
            try:
                with open(storage_file, 'r') as f:
                    keys_data = json.load(f)
                
                if api_key in keys_data:
                    # В MVP используем тестовый адрес
                    return {
                        "seller_address": "0x1234567890123456789012345678901234567890",
                        "active": True,
                        "description": "Test API Key"
                    }
            except Exception as e:
                logger.error(f"Ошибка чтения локального хранилища: {e}")
        
        return None
    
    async def _get_secret_key_locally(self, api_key: str) -> Optional[str]:
        """Получает секретный ключ из локального хранилища"""
        # Проверяем API ключ из .env (MVP)
        if api_key == AMANITA_API_KEY:
            return AMANITA_API_SECRET
        
        # Проверяем локальное хранилище
        storage_file = "api_keys.json"
        
        try:
            if not os.path.exists(storage_file):
                return None
            
            with open(storage_file, 'r') as f:
                keys_data = json.load(f)
            
            if api_key in keys_data:
                encrypted_secret = keys_data[api_key]["encrypted_secret"]
                return self._decrypt_secret_key(encrypted_secret)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения секретного ключа: {e}")
            return None
    
    async def revoke_api_key(self, api_key: str, seller_address: str) -> bool:
        """
        Отзывает API ключ
        
        Args:
            api_key: API ключ для отзыва
            seller_address: Адрес селлера (для проверки прав)
        
        Returns:
            True если ключ успешно отозван
        """
        try:
            # Проверяем права доступа
            key_info = await self.validate_api_key(api_key)
            if key_info["seller_address"].lower() != seller_address.lower():
                raise InvalidAPIKeyError("Нет прав для отзыва этого ключа")
            
            # Отзываем в блокчейне
            await self._revoke_api_key_in_blockchain(api_key, seller_address)
            
            # Удаляем из локального хранилища
            await self._remove_secret_key_locally(api_key)
            
            # Очищаем кэш
            self._clear_cache(api_key)
            
            logger.info(f"API ключ {api_key} отозван для селлера {seller_address}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отзыва API ключа {api_key}: {e}")
            return False
    
    async def _revoke_api_key_in_blockchain(self, api_key: str, seller_address: str):
        """Отзывает API ключ в блокчейне (заглушка для MVP)"""
        # TODO: В production здесь будет вызов смарт-контракта
        # contract = self.blockchain.get_contract("AmanitaRegistry")
        # await self.blockchain.transact_contract_function(
        #     "AmanitaRegistry", 
        #     "revokeApiKey", 
        #     self.blockchain.seller_key,
        #     seller_address, 
        #     api_key
        # )
        
        logger.info(f"API ключ {api_key} отозван в блокчейне для {seller_address}")
    
    async def _remove_secret_key_locally(self, api_key: str):
        """Удаляет секретный ключ из локального хранилища"""
        storage_file = "api_keys.json"
        
        try:
            if os.path.exists(storage_file):
                with open(storage_file, 'r') as f:
                    keys_data = json.load(f)
                
                if api_key in keys_data:
                    del keys_data[api_key]
                    
                    with open(storage_file, 'w') as f:
                        json.dump(keys_data, f, indent=2)
                    
                    logger.debug(f"Секретный ключ для {api_key} удален локально")
            
        except Exception as e:
            logger.error(f"Ошибка удаления секретного ключа: {e}")
    
    async def get_seller_api_keys(self, seller_address: str) -> List[Dict]:
        """
        Получает список API ключей селлера
        
        Args:
            seller_address: Адрес селлера
        
        Returns:
            Список API ключей (без секретных ключей)
        """
        try:
            # Проверяем адрес селлера из .env (MVP)
            seller_account = self.blockchain.seller_account
            if seller_address.lower() == seller_account.address.lower():
                return [{
                    "api_key": AMANITA_API_KEY,
                    "created_at": "2024-01-01T00:00:00",  # Фиксированная дата для MVP
                    "active": True,
                    "description": "Seller API Key from .env"
                }]
            
            # TODO: В production получать из блокчейна
            # Пока возвращаем из локального хранилища
            storage_file = "api_keys.json"
            keys = []
            
            if os.path.exists(storage_file):
                with open(storage_file, 'r') as f:
                    keys_data = json.load(f)
                
                for api_key, data in keys_data.items():
                    # В MVP все ключи принадлежат тестовому адресу
                    if seller_address.lower() == "0x1234567890123456789012345678901234567890".lower():
                        keys.append({
                            "api_key": api_key,
                            "created_at": data.get("created_at", ""),
                            "active": True
                        })
            
            return keys
            
        except Exception as e:
            logger.error(f"Ошибка получения API ключей для {seller_address}: {e}")
            return [] 