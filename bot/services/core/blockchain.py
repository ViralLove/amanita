# Универсальный слой для работы с web3 и блокчейном 
import os
from web3 import Web3
from dotenv import load_dotenv
import json
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import logging
from typing import Optional, Any, List, Dict, Union
import asyncio
from bot.config import (
    SELLER_PRIVATE_KEY,
    ACTIVE_PROFILE,
    RPC_URL,
    ABI_BASE_DIR,
    AMANITA_REGISTRY_CONTRACT_ADDRESS
)

load_dotenv(dotenv_path="bot/.env")
logger = logging.getLogger(__name__)

PROFILES = {
    "localhost": {
        "RPC": "http://127.0.0.1:8545"
    },
    "mainnet": {
        "RPC": "https://polygon-mainnet.infura.io/v3/YOUR_INFURA_KEY"
    },
    "amoy": {
        "RPC": "https://rpc-amoy.polygon.technology"
    }
}

# Список контрактов без адресов, так как теперь они будут получены из реестра
CONTRACTS = {
    "InviteNFT": {},
    "ProductRegistry": {}
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_abi(contract_name):
    """
    Универсальная загрузка ABI с подробным логированием:
    - Если ABI лежит в формате Hardhat: <base_dir>/<ContractName>.sol/<ContractName>.json
    - Если ABI лежит в плоской папке: <base_dir>/<ContractName>.json
    """
    hh_path = os.path.join(ABI_BASE_DIR, f"{contract_name}.sol", f"{contract_name}.json")
    flat_path = os.path.join(ABI_BASE_DIR, f"{contract_name}.json")

    print(f"[ABI] Проверка путей для {contract_name}:")
    print(f"  - Hardhat: {hh_path} {'✅' if os.path.exists(hh_path) else '❌'}")
    print(f"  - Flat:    {flat_path} {'✅' if os.path.exists(flat_path) else '❌'}")

    if os.path.exists(hh_path):
        abi_path = hh_path
    elif os.path.exists(flat_path):
        abi_path = flat_path
    else:
        raise FileNotFoundError(f"ABI-файл для {contract_name} не найден ни по пути {hh_path}, ни по пути {flat_path}")

    print(f"[ABI] Загружаем ABI из: {abi_path}")
    with open(abi_path, "r") as f:
        abi_data = json.load(f)
        if isinstance(abi_data, dict) and "abi" in abi_data:
            print(f"[ABI] Ключи: {list(abi_data.keys())}")
            print(f"[ABI] Кол-во функций: {len(abi_data['abi'])}")
            print(f"[ABI] Пример функции: {abi_data['abi'][0] if abi_data['abi'] else 'Пусто'}")
            return abi_data["abi"]
        print(f"[ABI] ABI (массив): {abi_data[:1] if isinstance(abi_data, list) else abi_data}")
        return abi_data

def is_valid_address(address):
    return isinstance(address, str) and address.startswith('0x') and len(address) == 42

class BlockchainService:
    """Сервис для работы с блокчейном - реализован как синглтон"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Реализация паттерна синглтон"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Приватный конструктор - инициализация происходит только один раз"""
        if not hasattr(self, '_initialized'):
            # Инициализируем Web3
            self.web3 = self._init_web3()
            
            # Получаем chain_id
            self.chain_id = self.web3.eth.chain_id
            
            # Загружаем реестр контрактов
            self.registry = self._load_registry_contract()
            
            # Загружаем контракты из реестра
            self.contracts = self._load_contracts()
            
            # Инициализируем аккаунт продавца
            if not SELLER_PRIVATE_KEY:
                raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
                
            self.seller_key = SELLER_PRIVATE_KEY
            self.seller_account = Account.from_key(SELLER_PRIVATE_KEY)
            
            logger.info(f"[Web3] Активный профиль: {ACTIVE_PROFILE}, RPC: {RPC_URL}")
            
            self._initialized = True
    
    @classmethod
    def reset(cls):
        """Сброс синглтона (для тестирования)"""
        cls._instance = None

    def _init_web3(self) -> Web3:
        """Инициализирует подключение к Web3"""
        try:
            # Создаем провайдер
            if ACTIVE_PROFILE == "localhost":
                provider = Web3.HTTPProvider(RPC_URL)
            else:
                provider = Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60})
            
            # Инициализируем Web3
            web3 = Web3(provider)
            
            # Проверяем подключение
            if not web3.is_connected():
                raise Exception("Failed to connect to Web3")
                
            logger.info(f"[Web3] Успешное подключение к {ACTIVE_PROFILE}")
            return web3
            
        except Exception as e:
            logger.error(f"[Web3] Ошибка подключения к {ACTIVE_PROFILE}: {e}")
            raise

    def _log(self, msg, error=False):
        prefix = "[Web3][ERROR]" if error else "[Web3]"
        print(f"{prefix} {msg}")

    def _load_registry_contract(self) -> Any:
        """Загружает контракт реестра"""
        try:
            # Загружаем ABI (единый путь загрузки)
            abi = load_abi("AmanitaRegistry")
                
            # Создаем контракт
            contract = self.web3.eth.contract(
                address=AMANITA_REGISTRY_CONTRACT_ADDRESS,
                abi=abi
            )
            
            logger.info(f"[Web3] Загружен контракт реестра: {AMANITA_REGISTRY_CONTRACT_ADDRESS}")
            return contract
            
        except Exception as e:
            logger.error(f"[Web3] Ошибка загрузки контракта реестра: {e}")
            raise
            
    def _load_contracts(self) -> Dict[str, Any]:
        """Загружает все контракты из реестра"""
        try:
            contracts = {}
            
            # Получаем список всех контрактов из реестра
            contract_names = ["InviteNFT", "ProductRegistry"]  # TODO: получать динамически из реестра
            
            for name in contract_names:
                try:
                    # Получаем адрес контракта из реестра
                    address = self.registry.functions.getAddress(name).call()
                    logger.info(f"[Web3] Получен адрес контракта {name}: {address}")
                    
                    # Загружаем ABI (единый путь загрузки)
                    abi = load_abi(name)
                        
                    # Создаем контракт
                    contract = self.web3.eth.contract(
                        address=address,
                        abi=abi
                    )
                    
                    contracts[name] = contract
                    logger.info(f"[Web3] Загружен контракт {name}")
                    
                except Exception as e:
                    logger.error(f"[Web3] Ошибка загрузки контракта {name}: {e}")
                    raise
            
            logger.info(f"[Web3] Загружено контрактов: {len(contracts)}")
            return contracts
            
        except Exception as e:
            logger.error(f"[Web3] Ошибка загрузки контрактов: {e}")
            raise

    def get_contract(self, name):
        return self.contracts.get(name)

    def call_contract_function(self, contract_name: str, function_name: str, *args, **kwargs) -> Any:
        """
        Публичный метод для вызова read-only функций контракта.
        
        Args:
            contract_name: Имя контракта
            function_name: Имя функции
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            Any: Результат вызова функции или None в случае ошибки
        """
        return self._call_contract_read_function(contract_name, function_name, None, *args, **kwargs)

    async def estimate_gas_with_multiplier(self, contract_function, *args, multiplier: float = 1.2) -> int:
        """
        Оценивает газ для транзакции с множителем для надежности.
        
        Args:
            contract_function: Функция контракта
            *args: Аргументы функции
            multiplier: Множитель для газа (по умолчанию 1.2 = +20%)
            
        Returns:
            int: Оценка газа с множителем
        """
        try:
            # Базовая транзакция для оценки
            base_transaction = {
                'from': contract_function.address,
                'value': 0,
                'chainId': self.chain_id,
            }
            
            # Оцениваем газ
            estimated_gas = contract_function(*args).estimate_gas(base_transaction)
            
            # Применяем множитель и округляем вверх
            gas_with_multiplier = int(estimated_gas * multiplier)
            
            logger.info(f"[Web3] [GAS] estimated: {estimated_gas}, with multiplier ({multiplier}): {gas_with_multiplier}")
            
            return gas_with_multiplier
            
        except Exception as e:
            logger.warning(f"[Web3] [GAS] Ошибка оценки газа: {e}, используем fallback")
            # Fallback значение для сложных операций
            return 2000000

    async def transact_contract_function(self, contract_name: str, function_name: str, private_key: str, *args, **kwargs) -> Optional[str]:
        """
        Вызывает функцию контракта с транзакцией.
        
        Args:
            contract_name: Имя контракта
            function_name: Имя функции
            private_key: Приватный ключ для подписи
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            Optional[str]: Хэш транзакции или None в случае ошибки
        """
        try:
            # Получаем аккаунт из приватного ключа
            account = Account.from_key(private_key)
            logger.info(f"[Web3] [TX] account.address: {account.address}")
            
            # Получаем контракт
            contract = self.get_contract(contract_name)
            if not contract:
                logger.error(f"[Web3] Контракт {contract_name} не найден")
                return None
            
            # Получаем функцию контракта
            contract_function = getattr(contract.functions, function_name)
            logger.info(f"[Web3] [TX] func: {contract_function}, args: {args}, kwargs: {kwargs}")
            
            # Оцениваем газ с множителем
            estimated_gas = await self.estimate_gas_with_multiplier(contract_function, *args)
            
            # Создаем транзакцию
            gas_limit = kwargs.get('gas', estimated_gas)  # Берем gas из kwargs или используем оценку
            txn = contract_function(*args).build_transaction({
                'value': 0,
                'chainId': self.chain_id,
                'from': account.address,
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'gas': gas_limit,
                'gasPrice': self.web3.eth.gas_price
            })
            logger.info(f"[Web3] [TX] txn (build_transaction): {txn}")
            
            # Подписываем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(txn, private_key)
            logger.info(f"[Web3] [TX] signed_txn: {signed_txn}, type: {type(signed_txn)}")
            
            # Отправляем транзакцию
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            logger.info(f"[Web3] Транзакция {contract_name}.{function_name} отправлена: {tx_hash_hex}")
            
            # Ждем подтверждения и проверяем статус
            receipt = await self.wait_for_transaction(tx_hash_hex)
            if not self.check_transaction_status(receipt):
                return None
                
            return tx_hash_hex
            
        except Exception as e:
            logger.error(f"[Web3] Ошибка в transact_contract_function: {e}")
            return None

    def validate_invite_code(self, invite_code: str) -> dict:
        """Валидация инвайт-кода через контракт InviteNFT (web3 call)"""
        result = self._call_contract_read_function("InviteNFT", "validateInviteCode", (False, "contract_not_found"), invite_code)
        success, reason = result[0], result[1]
        return {"success": success, "reason": reason}

    def activate_invite(self, invite_code: str, user_address: str) -> dict:
        """Активация инвайта"""
        result = self._call_contract_read_function("InviteNFT", "activateInvite", None, invite_code, user_address)
        if result is None:
            return {"success": False, "reason": "contract_not_found"}
        return {"success": True, "reason": "success"}

    def get_tx_status(self, tx_hash: str) -> str:
        """Получение статуса транзакции (заглушка)"""
        # TODO: заменить на реальный запрос статуса
        return "confirmed" 

    def get_token_id_by_invite_code(self, invite_code: str) -> int:
        return self._call_contract_read_function("InviteNFT", "getTokenIdByInviteCode", None, invite_code)

    def get_invite_code_by_token_id(self, token_id: int) -> str:
        return self._call_contract_read_function("InviteNFT", "getInviteCodeByTokenId", None, token_id)

    def get_invite_transfer_history(self, token_id: int) -> list:
        return self._call_contract_read_function("InviteNFT", "getInviteTransferHistory", [], token_id)

    def get_user_invites(self, user_address: str) -> list:
        return self._call_contract_read_function("InviteNFT", "getUserInvites", [], user_address)

    def is_invite_token_used(self, token_id: int) -> bool:
        return self._call_contract_read_function("InviteNFT", "isInviteTokenUsed", False, token_id)

    def get_invite_created_at(self, token_id: int) -> int:
        return self._call_contract_read_function("InviteNFT", "getInviteCreatedAt", 0, token_id)

    def get_invite_expiry(self, token_id: int) -> int:
        return self._call_contract_read_function("InviteNFT", "getInviteExpiry", 0, token_id)

    def get_invite_minter(self, token_id: int) -> str:
        return self._call_contract_read_function("InviteNFT", "getInviteMinter", None, token_id)

    def get_invite_first_owner(self, token_id: int) -> str:
        return self._call_contract_read_function("InviteNFT", "getInviteFirstOwner", None, token_id)

    # Методы для работы с продуктами
    def get_catalog_version(self) -> int:
        """Получает текущую версию каталога"""
        try:
            version = self._call_contract_read_function(
                "ProductRegistry",
                "getMyCatalogVersion",
                0
            )
            logger.info(f"Current catalog version: {version}")
            return version
        except Exception as e:
            logger.error(f"Error getting catalog version: {e}")
            return 0

    def get_all_products(self) -> List[dict]:
        """Получает все продукты из блокчейна"""
        try:
            product_ids = self._call_contract_read_function(
                "ProductRegistry",
                "getAllActiveProductIds",
                []
            )
            logger.info(f"Got {len(product_ids)} product IDs from blockchain")
            
            # Получаем полные данные для каждого продукта
            products = []
            for product_id in product_ids:
                product = self._call_contract_read_function(
                    "ProductRegistry",
                    "getProduct",
                    None,
                    product_id
                )
                if product:
                    products.append(product)
            
            logger.info(f"Retrieved {len(products)} full products from blockchain")
            return products
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []

    def get_products_by_current_seller_full(self) -> List[tuple]:
        """
        Возвращает все товары текущего продавца со структурами Product (id, seller, ipfsCID, active).
        Использует ProductRegistry.getProductsBySellerFull(), требующий isSeller(msg.sender).
        """
        try:
            products = self._call_contract_read_function(
                "ProductRegistry",
                "getProductsBySellerFull",
                []
            )
            logger.info(f"Retrieved {len(products)} seller products (full) from blockchain")
            return products or []
        except Exception as e:
            logger.error(f"Error getProductsBySellerFull: {e}")
            return []
    
    def get_product(self, product_id: int) -> Optional[dict]:
        """Получает продукт по ID"""
        try:
            product = self._call_contract_read_function(
                "ProductRegistry",
                "getProduct",
                None,
                product_id
            )
            if product:
                logger.info(f"Got product {product_id} from blockchain")
            else:
                logger.warning(f"Product {product_id} not found")
            return product
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None

    async def create_product(self, ipfs_cid: str) -> Optional[str]:
        """Создает новый продукт в смарт-контракте"""
        try:
            tx_hash = await self.transact_contract_function(
                "ProductRegistry",
                "createProduct",
                self.seller_key,
                ipfs_cid
            )
            if tx_hash:
                logger.info(f"Created product with CID {ipfs_cid}, tx_hash: {tx_hash}")
            return tx_hash
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return None

    def product_exists_in_blockchain(self, product_id: int) -> bool:
        """
        Проверяет, существует ли продукт с указанным blockchain ID в смарт-контракте.
        
        Args:
            product_id: Blockchain ID продукта для проверки
            
        Returns:
            bool: True если продукт существует в блокчейне, False если нет
        """
        try:
            logger.debug(f"🔗 Проверка существования продукта в блокчейне: ID {product_id}")
            
            # Используем getProduct для проверки существования
            # Если продукт не существует, контракт вернет ошибку "product does not exist"
            product = self._call_contract_read_function(
                "ProductRegistry",
                "getProduct",
                None,
                product_id
            )
            
            # Если продукт получен, проверяем что ID не 0 (дополнительная защита)
            exists = product is not None and product[0] != 0
            logger.debug(f"🔗 Продукт с blockchain ID {product_id} {'существует' if exists else 'не существует'} в блокчейне")
            
            return exists
            
        except Exception as e:
            # Если контракт вернул "product does not exist" или другую ошибку
            logger.debug(f"🔗 Продукт с blockchain ID {product_id} не существует в блокчейне: {e}")
            return False

    async def set_product_active(self, private_key: str, product_id: int, is_active: bool) -> Optional[str]:
        """
        Устанавливает активность продукта (доступен/не доступен для покупки).
        
        Args:
            private_key: Приватный ключ для подписи
            product_id: ID продукта
            is_active: True - продукт активен, False - не активен
            
        Returns:
            Optional[str]: Хэш транзакции или None в случае ошибки
        """
        logger.info(f"[BlockchainService] Установка активности продукта {product_id}: {is_active}")
        
        if is_active:
            # Используем новую функцию activateProduct
            return await self.transact_contract_function(
                "ProductRegistry",
                "activateProduct",
                private_key,
                product_id
            )
        else:
            # Используем существующую функцию deactivateProduct
            return await self.transact_contract_function(
                "ProductRegistry",
                "deactivateProduct",
                private_key,
                product_id
            )

    async def update_product_status(self, private_key: str, product_id: int, new_status: int) -> Optional[str]:
        """
        Обновляет статус продукта (активен/неактивен).
        
        Args:
            private_key: Приватный ключ для подписи
            product_id: ID продукта
            new_status: Новый статус (0 - неактивен, 1 - активен)
            
        Returns:
            Optional[str]: Хэш транзакции или None в случае ошибки
        """
        logger.info(f"[BlockchainService] Обновление статуса продукта {product_id} на {new_status}")
        
        # Преобразуем статус в boolean
        is_active = bool(new_status)
        
        return await self.set_product_active(private_key, product_id, is_active)

    async def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> Optional[dict]:
        """
        Ждет подтверждения транзакции.
        
        Args:
            tx_hash: Хэш транзакции
            timeout: Таймаут в секундах
            
        Returns:
            Optional[dict]: Receipt транзакции или None в случае ошибки
        """
        if not tx_hash:
            logger.error("[Web3] Ошибка ожидания транзакции None: tx_hash не может быть None")
            return None
            
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            logger.info(f"[Web3] Транзакция {tx_hash} подтверждена")
            return receipt
        except Exception as e:
            logger.error(f"[Web3] Ошибка ожидания транзакции {tx_hash}: {e}")
            return None

    def check_transaction_status(self, receipt: dict) -> bool:
        """Проверяет статус транзакции"""
        if not receipt:
            return False
        
        status = receipt.get('status')
        if status is None:
            logger.error("[Web3] Статус транзакции не найден в receipt")
            return False
            
        if status == 1:
            return True
        else:
            logger.error(f"[Web3] Транзакция не удалась. Receipt: {receipt}")
            return False

    def _load_contract_abi(self, contract_name: str) -> Optional[list]:
        """
        Загружает ABI контракта из файла.
        
        Args:
            contract_name: Имя контракта
            
        Returns:
            Optional[list]: ABI контракта или None в случае ошибки
        """
        try:
            # Единый способ получения ABI
            abi = load_abi(contract_name)
            return abi
                
        except Exception as e:
            logger.error(f"[ABI] Ошибка загрузки ABI для {contract_name}: {e}")
            return None

    def _call_contract_read_function(self, contract_name: str, function_name: str, default_value: Any, *args, **kwargs) -> Any:
        """
        Универсальный метод для вызова read-only функций контракта.
        
        Args:
            contract_name: Имя контракта
            function_name: Имя функции
            default_value: Значение по умолчанию в случае ошибки
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            Any: Результат вызова функции или default_value в случае ошибки
        """
        contract = self.get_contract(contract_name)
        if not contract:
            self._log(f"Контракт {contract_name} не найден", error=True)
            return default_value
        try:
            self._log(f"[Web3] Вызов функции {contract_name}.{function_name} с адресом {self.seller_account.address} и аргументами: {args} и kwargs: {kwargs}")   
            return contract.functions[function_name](*args).call(
                {"from": self.seller_account.address},
                **kwargs
            )
        except Exception as e:
            self._log(f"Ошибка вызова {contract_name}.{function_name}: {e}", error=True)
            return default_value

    async def get_product_id_from_tx(self, tx_hash: str) -> Optional[int]:
        """
        Получает productId из события ProductCreated по хэшу транзакции.
        Args:
            tx_hash: Хэш транзакции
        Returns:
            Optional[int]: productId или None, если не найден
        """
        try:
            receipt = await self.wait_for_transaction(tx_hash)
            if not receipt:
                logger.error(f"[Web3] Не удалось получить receipt для tx {tx_hash}")
                return None
            contract = self.get_contract("ProductRegistry")
            if not contract:
                logger.error("[Web3] Контракт ProductRegistry не найден")
                return None
            # Безопасная обработка события с защитой от MismatchedABI
            try:
                logs = contract.events.ProductCreated().process_receipt(receipt)
            except Exception as e:
                logger.error(f"[Web3] Ошибка обработки события ProductCreated: {e}")
                return None
            for log in logs:
                product_id = log.args.get("productId")
                if product_id is not None:
                    logger.info(f"[Web3] Найден productId в логах: {product_id}")
                    return product_id
            logger.error(f"[Web3] Событие ProductCreated не найдено в логах tx {tx_hash}")
            return None
        except Exception as e:
            logger.error(f"[Web3] Ошибка при парсинге логов ProductCreated: {e}")
            return None

