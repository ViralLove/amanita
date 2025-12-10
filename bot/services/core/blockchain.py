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
try:
    # Попытка импорта для запуска из корня проекта
    from config import (
        SELLER_PRIVATE_KEY,
        RPC_URL,
        ABI_BASE_DIR,
        MAGIC_REGISTRY_CONTRACT_ADDRESS
    )
except ImportError:
    # Fallback для запуска из папки bot
    from config import (
        SELLER_PRIVATE_KEY,
        RPC_URL,
        ABI_BASE_DIR,
        MAGIC_REGISTRY_CONTRACT_ADDRESS
    )

load_dotenv(dotenv_path="bot/.env")
logger = logging.getLogger(__name__)

# Удалены неиспользуемые словари PROFILES и CONTRACTS
# RPC конфигурация теперь управляется через переменные окружения в config.py

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_abi(contract_name):
    """
    Универсальная загрузка ABI с подробным логированием:
    - Если ABI лежит в формате Hardhat: <base_dir>/<ContractName>.sol/<ContractName>.json
    - Если ABI лежит в плоской папке: <base_dir>/<ContractName>.json
    - Для UUPS контрактов: используется Logic ABI (OrganicComponentRegistryLogic, etc.)
    """
    # UUPS контракты — используем Logic ABI
    uups_contracts = {
        "OrganicComponentRegistry": "OrganicComponentRegistryLogic",
        "SpiralEngine": "SpiralEngineLogic",
        "ProductRegistry": "ProductRegistryLogic",
        "AmanitaInternational": "AmanitaInternationalLogic"
    }
    
    # Если это UUPS контракт, загружаем Logic ABI
    actual_contract_name = uups_contracts.get(contract_name, contract_name)
    
    hh_path = os.path.join(ABI_BASE_DIR, f"{actual_contract_name}.sol", f"{actual_contract_name}.json")
    flat_path = os.path.join(ABI_BASE_DIR, f"{actual_contract_name}.json")

    # Логируем если используется Logic ABI для UUPS
    if actual_contract_name != contract_name:
        print(f"[ABI] {contract_name} — UUPS контракт, используем {actual_contract_name} ABI")
    
    print(f"[ABI] Проверка путей для {contract_name}:")
    print(f"  - Hardhat: {hh_path} {'✅' if os.path.exists(hh_path) else '❌'}")
    print(f"  - Flat:    {flat_path} {'✅' if os.path.exists(flat_path) else '❌'}")
    
    # Подробное логирование для диагностики
    print(f"[ABI] ABI_BASE_DIR: {ABI_BASE_DIR}")
    print(f"[ABI] Текущая рабочая директория: {os.getcwd()}")
    print(f"[ABI] Содержимое ABI_BASE_DIR:")
    try:
        if os.path.exists(ABI_BASE_DIR):
            for item in os.listdir(ABI_BASE_DIR):
                item_path = os.path.join(ABI_BASE_DIR, item)
                print(f"    - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
        else:
            print(f"    - Директория {ABI_BASE_DIR} не существует!")
    except Exception as e:
        print(f"    - Ошибка при чтении директории: {e}")
    
    # Проверяем существование файлов
    print(f"[ABI] Проверка существования файлов:")
    print(f"    - {hh_path} существует: {os.path.exists(hh_path)}")
    print(f"    - {flat_path} существует: {os.path.exists(flat_path)}")
    
    # Если файлы не найдены, ищем альтернативные пути
    if not os.path.exists(hh_path) and not os.path.exists(flat_path):
        print(f"[ABI] Файлы не найдены, ищем альтернативные пути...")
        try:
            # Ищем в корне проекта
            root_path = os.path.join(os.getcwd(), "artifacts", "contracts", f"{contract_name}.json")
            print(f"    - Корень проекта: {root_path} {'✅' if os.path.exists(root_path) else '❌'}")
            
            # Ищем в текущей директории
            current_path = os.path.join(os.getcwd(), f"{contract_name}.json")
            print(f"    - Текущая директория: {current_path} {'✅' if os.path.exists(current_path) else '❌'}")
            
            # Ищем в /app
            app_path = os.path.join("/app", "artifacts", "contracts", f"{contract_name}.json")
            print(f"    - /app: {app_path} {'✅' if os.path.exists(app_path) else '❌'}")
            
        except Exception as e:
            print(f"    - Ошибка при поиске альтернативных путей: {e}")

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
            
            logger.info(f"[Web3] RPC: {RPC_URL}")
            
            self._initialized = True
    
    @classmethod
    def reset(cls):
        """Сброс синглтона (для тестирования)"""
        cls._instance = None

    def _init_web3(self) -> Web3:
        """Инициализирует подключение к Web3"""
        try:
            print(f"[Web3] === НАЧАЛО ИНИЦИАЛИЗАЦИИ WEB3 ===")
            print(f"[Web3] Подключение к RPC: {RPC_URL}")
            print(f"[Web3] Текущая рабочая директория: {os.getcwd()}")
            print(f"[Web3] ABI_BASE_DIR: {ABI_BASE_DIR}")
            
            print(f"[Web3] Содержимое /app:")
            try:
                for item in os.listdir("/app"):
                    item_path = os.path.join("/app", item)
                    print(f"    - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
            except Exception as e:
                print(f"    - Ошибка при чтении /app: {e}")
            
            # Дополнительная диагностика папки artifacts
            print(f"[Web3] === ДИАГНОСТИКА ARTIFACTS ===")
            artifacts_path = "/app/artifacts"
            print(f"[Web3] Проверяем: {artifacts_path}")
            print(f"[Web3] Существует: {os.path.exists(artifacts_path)}")
            
            if os.path.exists(artifacts_path):
                print(f"[Web3] Содержимое {artifacts_path}:")
                try:
                    for item in os.listdir(artifacts_path):
                        item_path = os.path.join(artifacts_path, item)
                        print(f"    - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
                        
                        # Если это папка, проверяем её содержимое
                        if os.path.isdir(item_path):
                            try:
                                sub_items = os.listdir(item_path)
                                print(f"      └─ содержимое: {sub_items[:5]}{'...' if len(sub_items) > 5 else ''}")
                            except Exception as e:
                                print(f"      └─ ошибка чтения: {e}")
                except Exception as e:
                    print(f"    - Ошибка при чтении {artifacts_path}: {e}")
            else:
                print(f"[Web3] Папка {artifacts_path} не существует!")
            
            # Создаем провайдер с timeout для всех внешних RPC
            provider = Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60})
            print(f"[Web3] Создан провайдер с timeout=60")
            
            # Инициализируем Web3
            web3 = Web3(provider)
            print(f"[Web3] Web3 объект создан")
            
            # Проверяем подключение
            print(f"[Web3] Проверяем подключение...")
            is_connected = web3.is_connected()
            print(f"[Web3] is_connected() = {is_connected}")
            
            if not is_connected:
                raise Exception("Failed to connect to Web3")
                
            print(f"[Web3] Успешное подключение к {RPC_URL}")
            return web3
            
        except Exception as e:
            print(f"[Web3] Ошибка подключения к {RPC_URL}: {e}")
            print(f"[Web3] Тип ошибки: {type(e).__name__}")
            raise

    def _log(self, msg, error=False):
        prefix = "[Web3][ERROR]" if error else "[Web3]"
        print(f"{prefix} {msg}")

    def _load_registry_contract(self) -> Any:
        """Загружает контракт реестра"""
        try:
            # Загружаем ABI (единый путь загрузки)
            abi = load_abi("MagicRegistry")
                
            # Создаем контракт
            contract = self.web3.eth.contract(
                address=MAGIC_REGISTRY_CONTRACT_ADDRESS,
                abi=abi
            )
            
            logger.info(f"[Web3] Загружен контракт реестра: {MAGIC_REGISTRY_CONTRACT_ADDRESS}")
            return contract
            
        except Exception as e:
            logger.error(f"[Web3] Ошибка загрузки контракта реестра: {e}")
            raise
            
    def _load_contracts(self) -> Dict[str, Any]:
        """Загружает все контракты из реестра"""
        try:
            contracts = {}
            
            # Получаем список всех контрактов из реестра
            contract_names = ["SpiralEngine", "ProductRegistry", "OrganicComponentRegistry", "SoulIdentity", "AmanitaInternational"]
            
            for name in contract_names:
                try:
                    # Получаем адрес контракта из реестра
                    address = self.registry.functions.get(name).call()
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
            
            # Специальный лимит газа для SpiralEngine.activateUser (создает много новых инвайтов)
            if contract_name == "SpiralEngine" and function_name == "activateUser":
                gas_limit = kwargs.get('gas', max(estimated_gas, 5000000))  # Минимум 5M газа для activateUser
                logger.info(f"[Web3] [TX] SpiralEngine.activateUser: увеличен лимит газа до {gas_limit}")
            else:
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
        """Валидация инвайт-кода через контракт SpiralEngine (web3 call)"""
        logger.info(f"[BlockchainService] Валидация инвайт-кода: {invite_code}")
        
        try:
            # Проверяем существование кода в SpiralEngine
            exists = self._call_contract_read_function(
                "SpiralEngine", "inviteCodeExists", False, invite_code
            )
            
            if not exists:
                return {"success": False, "reason": "Invite code not found"}
            
            # Получаем token ID
            token_id = self._call_contract_read_function(
                "SpiralEngine", "inviteCodeToTokenId", 0, invite_code
            )
            
            # Проверяем, использован ли код
            is_used = self._call_contract_read_function(
                "SpiralEngine", "isInviteUsed", False, token_id
            )
            
            if is_used:
                return {"success": False, "reason": "Invite code already used"}
            
            return {"success": True, "token_id": token_id, "invite_code": invite_code}
            
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка валидации инвайт-кода: {e}")
            return {"success": False, "reason": str(e)}
    
    def validate_activator_invite_pair(self, activator_address: str, invite_code: str) -> dict:
        """
        Валидирует связь между активатором и инвайтом перед активацией.
        
        Проверяет:
        1. Инвайт существует
        2. inviteMinter[tokenId] == activator (синхронизация)
        3. Инвайт не использован
        4. Инвайт не истек
        5. Активатор имеет capacity (circle < 12)
        
        Args:
            activator_address: Адрес активатора (например, seller address)
            invite_code: Код инвайта для проверки
            
        Returns:
            dict: {
                'valid': bool,
                'reason': str (если не valid),
                'token_id': int (если найден),
                'minter': str (если найден),
                'is_used': bool,
                'expired': bool,
                'activator_capacity': int (если valid),
                'circle_size': int (если valid),
                'expected_activator': str (если не синхронизирован)
            }
        """
        logger.info(f"[BlockchainService] Валидация пары активатор-инвайт: activator={activator_address[:10]}..., invite={invite_code}")
        
        try:
            contract = self.get_contract("SpiralEngine")
            if not contract:
                return {
                    'valid': False,
                    'reason': 'contract_not_found',
                    'token_id': None,
                    'minter': None
                }
            
            # 1. Проверка существования инвайта
            exists = self._call_contract_read_function(
                "SpiralEngine", "inviteCodeExists", False, invite_code
            )
            if not exists:
                logger.warning(f"[BlockchainService] Инвайт {invite_code} не найден")
                return {
                    'valid': False,
                    'reason': 'invite_not_found',
                    'token_id': None,
                    'minter': None
                }
            
            # 2. Получение token_id
            token_id = self._call_contract_read_function(
                "SpiralEngine", "inviteCodeToTokenId", 0, invite_code
            )
            if not token_id:
                logger.warning(f"[BlockchainService] Не удалось получить token_id для инвайта {invite_code}")
                return {
                    'valid': False,
                    'reason': 'invalid_token_id',
                    'token_id': None,
                    'minter': None
                }
            
            # 3. Проверка минтера (критично для синхронизации)
            minter = self._call_contract_read_function(
                "SpiralEngine", "inviteMinter", None, token_id
            )
            if not minter:
                logger.warning(f"[BlockchainService] Не удалось получить минтера для token_id {token_id}")
                return {
                    'valid': False,
                    'reason': 'minter_not_found',
                    'token_id': token_id,
                    'minter': None
                }
            
            # Normalize addresses for comparison
            if minter.lower() != activator_address.lower():
                logger.warning(
                    f"[BlockchainService] Рассинхронизация: инвайт {invite_code} создан {minter[:10]}..., "
                    f"а активирует {activator_address[:10]}..."
                )
                return {
                    'valid': False,
                    'reason': 'invite_not_from_activator',
                    'token_id': token_id,
                    'minter': minter,
                    'expected_activator': activator_address
                }
            
            # 4. Проверка использования
            is_used = self._call_contract_read_function(
                "SpiralEngine", "isInviteUsed", False, token_id
            )
            if is_used:
                logger.warning(f"[BlockchainService] Инвайт {invite_code} уже использован")
                return {
                    'valid': False,
                    'reason': 'invite_already_used',
                    'token_id': token_id,
                    'minter': minter,
                    'is_used': True
                }
            
            # 5. Проверка срока действия
            expiry = self._call_contract_read_function(
                "SpiralEngine", "inviteExpiry", 0, token_id
            )
            current_time = self.web3.eth.get_block('latest').timestamp
            expired = expiry > 0 and expiry <= current_time
            if expired:
                logger.warning(
                    f"[BlockchainService] Инвайт {invite_code} истек: expiry={expiry}, current={current_time}"
                )
                return {
                    'valid': False,
                    'reason': 'invite_expired',
                    'token_id': token_id,
                    'minter': minter,
                    'expired': True,
                    'expiry': expiry,
                    'current_time': current_time
                }
            
            # 6. Проверка capacity активатора
            circle = self._call_contract_read_function(
                "SpiralEngine", "getCircleMembers", [], activator_address
            )
            if circle is None:
                circle = []
            
            capacity = 12 - len(circle)
            if capacity <= 0:
                logger.warning(
                    f"[BlockchainService] Активатор {activator_address[:10]}... заполнен: "
                    f"circle_size={len(circle)}/12, capacity={capacity}"
                )
                return {
                    'valid': False,
                    'reason': 'activator_circle_full',
                    'token_id': token_id,
                    'minter': minter,
                    'capacity': capacity,
                    'circle_size': len(circle)
                }
            
            # Все проверки пройдены
            logger.info(
                f"[BlockchainService] ✅ Пара валидна: activator={activator_address[:10]}..., "
                f"invite={invite_code}, capacity={capacity}/12"
            )
            return {
                'valid': True,
                'reason': None,
                'token_id': token_id,
                'minter': minter,
                'is_used': False,
                'expired': False,
                'activator_capacity': capacity,
                'circle_size': len(circle)
            }
            
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка валидации пары активатор-инвайт: {e}")
            return {
                'valid': False,
                'reason': f'validation_error: {str(e)}',
                'token_id': None,
                'minter': None
            }

    async def activate_invite(self, invite_code: str, user_address: str, new_invite_codes: List[str] = None, expiry: int = 0, private_key: str = None) -> dict:
        """Активация инвайта через SpiralEngine"""
        logger.info(f"[BlockchainService] Активация инвайта {invite_code} для пользователя {user_address}")
        
        try:
            # Для SpiralEngine требуется транзакция, а не read функция
            if not private_key:
                return {"success": False, "reason": "Private key required for activation"}
            
            # Проверяем что передано ровно 12 новых кодов (требование SpiralEngine)
            if not new_invite_codes or len(new_invite_codes) != 12:
                return {"success": False, "reason": "SpiralEngine требует ровно 12 новых инвайт-кодов"}
            
            # Активируем пользователя через SpiralEngine
            tx_hash = await self.transact_contract_function(
                "SpiralEngine",
                "activateUser",
                private_key,
                invite_code,
                user_address,
                new_invite_codes,
                expiry
            )
            
            if tx_hash:
                logger.info(f"[BlockchainService] Пользователь {user_address} активирован, tx: {tx_hash}")
                return {"success": True, "tx_hash": tx_hash}
            else:
                return {"success": False, "reason": "Ошибка активации пользователя"}
                
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка активации инвайта: {e}")
            return {"success": False, "reason": str(e)}

    def get_tx_status(self, tx_hash: str) -> str:
        """Получение статуса транзакции (заглушка)"""
        # TODO: заменить на реальный запрос статуса
        return "confirmed" 

    def get_token_id_by_invite_code(self, invite_code: str) -> int:
        """Получение token ID по инвайт-коду через SpiralEngine"""
        return self._call_contract_read_function("SpiralEngine", "inviteCodeToTokenId", 0, invite_code)

    def get_invite_code_by_token_id(self, token_id: int) -> str:
        """Получение инвайт-кода по token ID через SpiralEngine"""
        # SpiralEngine не имеет прямого метода для этого, возвращаем None
        return None

    def get_invite_transfer_history(self, token_id: int) -> list:
        """История передачи токена (Soulbound токены не передаются)"""
        # SpiralEngine использует Soulbound токены, которые не передаются
        return []

    def get_user_invites(self, user_address: str) -> list:
        """Получение инвайтов пользователя через SpiralEngine"""
        logger.info(f"[BlockchainService] Получение инвайтов пользователя: {user_address}")
        
        try:
            # Получаем инвайты пользователя из SpiralEngine
            invites = self._call_contract_read_function(
                "SpiralEngine", "userInvites", [], user_address
            )
            
            result = []
            for invite_code in invites:
                token_id = self._call_contract_read_function(
                    "SpiralEngine", "inviteCodeToTokenId", 0, invite_code
                )
                
                is_used = self._call_contract_read_function(
                    "SpiralEngine", "isInviteUsed", False, token_id
                )
                
                result.append({
                    "invite_code": invite_code,
                    "token_id": token_id,
                    "is_used": is_used
                })
            
            logger.info(f"[BlockchainService] Найдено {len(result)} инвайтов для пользователя {user_address}")
            return result
            
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка получения инвайтов пользователя: {e}")
            return []

    def is_invite_token_used(self, token_id: int) -> bool:
        """Проверка использования токена через SpiralEngine"""
        return self._call_contract_read_function("SpiralEngine", "isInviteUsed", False, token_id)

    def get_invite_created_at(self, token_id: int) -> int:
        """Получение времени создания токена (SpiralEngine не поддерживает)"""
        return 0

    def get_invite_expiry(self, token_id: int) -> int:
        """Получение времени истечения токена (SpiralEngine не поддерживает)"""
        return 0

    def get_invite_minter(self, token_id: int) -> str:
        """Получение минтера токена (SpiralEngine не поддерживает)"""
        return None

    def get_invite_first_owner(self, token_id: int) -> str:
        """Получение первого владельца токена (SpiralEngine использует Soulbound)"""
        return None
    
    def is_user_activated(self, user_address: str) -> bool:
        """Проверка активации пользователя через SpiralEngine"""
        logger.info(f"[BlockchainService] Проверка активации пользователя: {user_address}")
        
        try:
            # Проверяем использованный инвайт пользователя
            used_invite = self._call_contract_read_function(
                "SpiralEngine", "usedInviteByUser", 0, user_address
            )
            
            is_activated = used_invite > 0
            logger.info(f"[BlockchainService] Пользователь {user_address} активирован: {is_activated}")
            return is_activated
            
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка проверки активации пользователя: {e}")
            return False
    
    async def mint_invite(self, invite_code: str, token_id: int, private_key: str) -> str:
        """Минт инвайта через SpiralEngine"""
        logger.info(f"[BlockchainService] Минт инвайта {invite_code} с token_id {token_id}")
        
        try:
            # Минтим инвайт через SpiralEngine
            tx_hash = await self.transact_contract_function(
                "SpiralEngine",
                "mintInvite",
                private_key,
                invite_code,
                token_id
            )
            
            if tx_hash:
                logger.info(f"[BlockchainService] Инвайт {invite_code} заминчен, tx: {tx_hash}")
                return tx_hash
            else:
                raise Exception("Ошибка минта инвайта")
                
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка минта инвайта: {e}")
            raise
    
    async def grant_seller_role(self, user_address: str, private_key: str) -> str:
        """Назначение роли продавца через SpiralEngine"""
        logger.info(f"[BlockchainService] Назначение роли продавца пользователю: {user_address}")
        
        try:
            # Назначаем роль продавца через SpiralEngine
            tx_hash = await self.transact_contract_function(
                "SpiralEngine",
                "grantSellerRole",
                private_key,
                user_address
            )
            
            if tx_hash:
                logger.info(f"[BlockchainService] Роль продавца назначена пользователю {user_address}, tx: {tx_hash}")
                return tx_hash
            else:
                raise Exception("Ошибка назначения роли продавца")
                
        except Exception as e:
            logger.error(f"[BlockchainService] Ошибка назначения роли продавца: {e}")
            raise

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

    # ==========================================
    # OrganicComponentRegistry Methods
    # ==========================================

    def get_component(self, component_id: str) -> Optional[dict]:
        """
        Получает компонент по business ID из OrganicComponentRegistry
        
        Contract function: getComponentByBusinessId(string businessId)
        
        Args:
            component_id: Business ID компонента (например, "amanita_muscaria")
            
        Returns:
            tuple | None: Component struct из контракта (6 полей):
                - [0] blockchain_id (int): числовой ID в блокчейне
                - [1] creator (str): адрес создателя
                - [2] created_at (int): timestamp создания
                - [3] last_updated (int): timestamp последнего обновления
                - [4] status (int): статус (ACTIVE=0, PENDING=1, ARCHIVED=2)
                - [5] is_shared (bool): доступен ли для общего использования
            
            None: Если компонент не найден или произошла ошибка
        
        Note:
            businessId и rootMetadataCID НЕ входят в Component struct.
            Они хранятся в отдельных mappings и получаются через:
            - get_component_business_id(blockchain_id) для businessId
            - get_component_root_metadata(business_id) для rootMetadataCID
        """
        try:
            component = self._call_contract_read_function(
                "OrganicComponentRegistry",
                "getComponentByBusinessId",
                None,
                component_id
            )
            if component:
                logger.info(f"Got component '{component_id}' from blockchain")
            else:
                logger.warning(f"Component '{component_id}' not found")
            return component
        except Exception as e:
            logger.error(f"Error getting component '{component_id}': {e}")
            return None

    def get_component_root_metadata(self, component_id: str) -> Optional[str]:
        """
        Получает rootMetadataCID компонента из отдельного mapping в контракте.

        Contract function: getComponentRootMetadata(string businessId)

        Args:
            component_id: Business ID компонента (например, "amanita_muscaria")

        Returns:
            str | None: IPFS/Arweave CID (например, "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4")
        """

        try:
            cid = self._call_contract_read_function(
                "OrganicComponentRegistry",
                "getComponentRootMetadata",
                None,
                component_id,
            )

            if cid:
                logger.info(
                    "Got root CID for component '%s': %s...",
                    component_id,
                    cid[:20],
                )
            else:
                logger.warning(
                    "No root CID for component '%s'",
                    component_id,
                )

            return cid if cid else None

        except Exception as e:
            logger.error(
                "Error getting root CID for '%s': %s",
                component_id,
                e,
            )
            return None

    def get_component_business_id(self, blockchain_id: int) -> Optional[str]:
        """
        Получает businessId компонента по его числовому ID из контракта.

        Contract mapping: componentBusinessIds (public auto-getter)

        Args:
            blockchain_id: Числовой ID компонента в реестре

        Returns:
            str | None: Business ID (например, "amanita_muscaria")
        """

        try:
            business_id = self._call_contract_read_function(
                "OrganicComponentRegistry",
                "componentBusinessIds",
                None,
                blockchain_id,
            )

            if business_id:
                logger.info(
                    "Got business_id for component ID %s: %s",
                    blockchain_id,
                    business_id,
                )
            else:
                logger.warning(
                    "No business_id for component ID %s",
                    blockchain_id,
                )

            return business_id if business_id else None

        except Exception as e:
            logger.error(
                "Error getting business_id for ID %s: %s",
                blockchain_id,
                e,
            )
            return None

    def component_exists(self, component_id: str) -> bool:
        """
        Проверяет существование компонента по business ID
        
        Args:
            component_id: Business ID компонента
            
        Returns:
            bool: True если компонент существует, False иначе
        """
        try:
            exists = self._call_contract_read_function(
                "OrganicComponentRegistry",
                "componentExists",
                False,
                component_id
            )
            logger.info(f"Component '{component_id}' exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking component existence '{component_id}': {e}")
            return False

    def get_component_root_metadata_cid(self, component_id: str) -> Optional[str]:
        """
        Получает rootMetadataCID компонента из отдельного mapping в контракте.
        
        Contract function: getComponentRootMetadata(string businessId)
        
        НЕ извлекает из Component struct, а использует отдельный mapping в контракте.
        Это alias для get_component_root_metadata() для обратной совместимости.
        
        Args:
            component_id: Business ID компонента (например, "amanita_muscaria")
            
        Returns:
            str | None: IPFS/Arweave CID (например, "ar://xyz123abc456def789")
            None: Если компонент не найден или произошла ошибка
        """
        # ✅ ПРАВИЛЬНО: использует отдельный метод для получения CID через mapping
        return self.get_component_root_metadata(component_id)

    def get_all_components(self) -> List[tuple]:
        """
        Получает все компоненты из OrganicComponentRegistry
        
        Returns:
            List[tuple]: Список Component struct из контракта (каждый tuple содержит 6 полей):
                - [0] blockchain_id (int): числовой ID в блокчейне
                - [1] creator (str): адрес создателя
                - [2] created_at (int): timestamp создания
                - [3] last_updated (int): timestamp последнего обновления
                - [4] status (int): статус (ACTIVE=0, PENDING=1, ARCHIVED=2)
                - [5] is_shared (bool): доступен ли для общего использования
        
        Note:
            businessId и rootMetadataCID НЕ входят в Component struct.
            Они получаются через:
            - get_component_business_id(blockchain_id) для businessId
            - get_component_root_metadata(business_id) для rootMetadataCID
        """
        try:
            # Получаем общее количество компонентов
            total = self._call_contract_read_function(
                "OrganicComponentRegistry",
                "totalComponents",
                0
            )
            logger.info(f"Total components in registry: {total}")
            
            components = []
            # Перебираем все ID (начиная с 1, так как 0 обычно reserved)
            for i in range(1, total + 1):
                try:
                    # Получаем business_id по blockchain ID
                    business_id = self._call_contract_read_function(
                        "OrganicComponentRegistry",
                        "componentBusinessIds",
                        None,
                        i
                    )
                    
                    if business_id:
                        # Получаем полные данные компонента
                        component = self.get_component(business_id)
                        if component:
                            components.append(component)
                except Exception as e:
                    logger.warning(f"Error getting component at index {i}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(components)} components from blockchain")
            return components
            
        except Exception as e:
            logger.error(f"Error getting all components: {e}")
            return []

