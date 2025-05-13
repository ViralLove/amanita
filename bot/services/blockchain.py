# Универсальный слой для работы с web3 и блокчейном 
import os
from web3 import Web3
from dotenv import load_dotenv
import json
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()

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

CONTRACTS = {
    "InviteNFT": {
        "address_env": "INVITE_NFT_CONTRACT_ADDRESS"
    },
    "AmanitaSale": {
        "address_env": "SALE_CONTRACT_ADDRESS"
    },
    "AmanitaToken": {
        "address_env": "AMANITA_TOKEN_CONTRACT_ADDRESS"
    },
    "OrderNFT": {
        "address_env": "ORDER_NFT_CONTRACT_ADDRESS"
    },
    "ReviewNFT": {
        "address_env": "REVIEW_NFT_CONTRACT_ADDRESS"
    }
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ABI_DIR = os.path.join(BASE_DIR, "contracts", "abi")

def load_abi(contract_name):
    abi_path = os.path.join(ABI_DIR, f"{contract_name}.json")
    try:
        with open(abi_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Web3] Ошибка загрузки ABI: {abi_path}: {e}")
        return None

def is_valid_address(address):
    return isinstance(address, str) and address.startswith('0x') and len(address) == 42

class BlockchainService:
    def __init__(self, profile: str = None):
        self.profile = (profile or os.getenv("BLOCKCHAIN_PROFILE") or "localhost").lower()
        if self.profile not in PROFILES:
            self._log(f"Профиль {self.profile} не найден, используется localhost", error=True)
            self.profile = "localhost"
        self.rpc = PROFILES[self.profile]['RPC']
        self._log(f"Активный профиль: {self.profile}, RPC: {self.rpc}")
        self.web3 = Web3(Web3.HTTPProvider(self.rpc))
        
        # Добавляем middleware для POA-сетей (Hardhat, Amoy) для web3.py 7.x
        self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if self.web3.is_connected():
            self._log(f"Успешное подключение к {self.profile}")
        else:
            self._log(f"Ошибка подключения к {self.profile}", error=True)
        self.contracts = {}
        self._load_contracts()

    def _log(self, msg, error=False):
        prefix = "[Web3][ERROR]" if error else "[Web3]"
        print(f"{prefix} {msg}")

    def _load_contracts(self):
        for name, meta in CONTRACTS.items():
            address = os.getenv(meta["address_env"])
            abi = load_abi(name)
            if not address or not is_valid_address(address):
                self._log(f"Контракт {name} не подключён: невалидный адрес ({address})", error=True)
                continue
            if not abi:
                self._log(f"Контракт {name} не подключён: ABI не найден или невалиден", error=True)
                continue
            try:
                self.contracts[name] = self.web3.eth.contract(address=address, abi=abi["abi"])
                self._log(f"Контракт {name} подключён: {address}")
            except Exception as e:
                self._log(f"Ошибка подключения контракта {name}: {e}", error=True)

    def get_contract(self, name):
        return self.contracts.get(name)

    def call_contract_function(self, contract_name, function_name, *args, **kwargs):
        contract = self.get_contract(contract_name)
        if not contract:
            self._log(f"Контракт {contract_name} не найден", error=True)
            return None
        try:
            func = getattr(contract.functions, function_name)
            result = func(*args, **kwargs).call()
            self._log(f"Вызов {contract_name}.{function_name} успешен: {result}")
            return result
        except Exception as e:
            self._log(f"Ошибка вызова {contract_name}.{function_name}: {e}", error=True)
            return None

    def transact_contract_function(self, contract_name, function_name, private_key, *args, **kwargs):
        contract = self.get_contract(contract_name)
        if not contract:
            self._log(f"Контракт {contract_name} не найден", error=True)
            return None
        try:
            account = self.web3.eth.account.from_key(private_key)
            func = getattr(contract.functions, function_name)
            txn = func(*args, **kwargs).build_transaction({
                'from': account.address,
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'gas': 2000000,
                'gasPrice': self.web3.to_wei('5', 'gwei')
            })
            signed_txn = self.web3.eth.account.sign_transaction(txn, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            self._log(f"Транзакция {contract_name}.{function_name} отправлена: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            self._log(f"Ошибка транзакции {contract_name}.{function_name}: {e}", error=True)
            return None

    def check_invite_code(self, invite_code: str) -> bool:
        """Проверка валидности инвайт-кода через контракт (заглушка)"""
        # TODO: заменить на реальную проверку через web3
        return invite_code.startswith("AMANITA")

    def activate_invite(self, invite_code: str, user_id: int) -> dict:
        """Активация инвайта (заглушка)"""
        # TODO: заменить на реальный вызов контракта
        return {
            "success": True,
            "tx_hash": "0x1234567890abcdef",
            "message": "Инвайт успешно активирован"
        }

    def get_tx_status(self, tx_hash: str) -> str:
        """Получение статуса транзакции (заглушка)"""
        # TODO: заменить на реальный запрос статуса
        return "confirmed" 