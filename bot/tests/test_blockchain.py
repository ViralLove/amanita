import os
import pytest
from bot.services.blockchain import BlockchainService
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# Устанавливаем профиль на localhost для теста
os.environ["BLOCKCHAIN_PROFILE"] = "localhost"

@pytest.fixture
def blockchain_service():
    return BlockchainService()

def test_network_info(blockchain_service):
    """Проверка информации о сети"""
    web3 = blockchain_service.web3
    assert web3.is_connected(), "Нет подключения к ноде"
    
    print("\n=== Информация о сети ===")
    print(f"Подключение к: {web3.provider.endpoint_uri}")
    print(f"Версия клиента: {web3.client_version}")
    print(f"Chain ID: {web3.eth.chain_id}")
    print(f"Последний блок: {web3.eth.block_number}")
    print(f"Gas Price: {web3.from_wei(web3.eth.gas_price, 'gwei')} Gwei")

def test_accounts(blockchain_service):
    """Проверка аккаунтов и их состояния"""
    web3 = blockchain_service.web3
    accounts = web3.eth.accounts
    assert len(accounts) > 0, "Нет доступных аккаунтов"
    
    print("\n=== Аккаунты и их состояние ===")
    for acc in accounts:
        balance = web3.eth.get_balance(acc)
        nonce = web3.eth.get_transaction_count(acc)
        print(f"Адрес: {acc}")
        print(f"  Баланс: {web3.from_wei(balance, 'ether')} ETH")
        print(f"  Nonce: {nonce}")

def test_contracts(blockchain_service):
    """Проверка контрактов и их функциональности"""
    contracts = {
        "AmanitaToken": {
            "address": os.getenv("AMANITA_TOKEN_CONTRACT_ADDRESS"),
            "name": "Amanita Coin",
            "symbol": "AMN"
        },
        "InviteNFT": {
            "address": os.getenv("INVITE_NFT_CONTRACT_ADDRESS"),
            "name": "Amanita Invite",
            "symbol": "INV"
        },
        "AmanitaSale": {
            "address": os.getenv("SALE_CONTRACT_ADDRESS"),
            "name": "Amanita Sale"
        },
        "OrderNFT": {
            "address": os.getenv("ORDER_NFT_CONTRACT_ADDRESS"),
            "name": "Amanita Order",
            "symbol": "ORD"
        },
        "ReviewNFT": {
            "address": os.getenv("REVIEW_NFT_CONTRACT_ADDRESS"),
            "name": "Amanita Review",
            "symbol": "REV"
        }
    }
    
    print("\n=== Проверка контрактов ===")
    for name, meta in contracts.items():
        address = meta["address"]
        assert address, f"Адрес контракта {name} не задан в .env"
        
        # Проверяем наличие контракта
        code = blockchain_service.web3.eth.get_code(address)
        assert code and code != b'', f"Контракт {name} не найден по адресу {address}"
        
        # Проверяем подключение через сервис
        contract = blockchain_service.get_contract(name)
        assert contract is not None, f"Не удалось получить контракт {name} через сервис"
        
        # Проверяем базовую функциональность
        try:
            contract_name = blockchain_service.call_contract_function(name, 'name')
            assert contract_name == meta["name"], f"Неверное имя контракта {name}: {contract_name} != {meta['name']}"
            
            if "symbol" in meta:
                symbol = blockchain_service.call_contract_function(name, 'symbol')
                assert symbol == meta["symbol"], f"Неверный символ контракта {name}: {symbol} != {meta['symbol']}"
            
            print(f"✓ {name}:")
            print(f"  Адрес: {address}")
            print(f"  Байткод: {len(code)} байт")
            print(f"  Имя: {contract_name}")
            if "symbol" in meta:
                print(f"  Символ: {symbol}")
        except Exception as e:
            print(f"! {name}:")
            print(f"  Адрес: {address}")
            print(f"  Байткод: {len(code)} байт")
            print(f"  Ошибка проверки: {e}")

def test_recent_activity(blockchain_service):
    """Проверка недавней активности в сети"""
    web3 = blockchain_service.web3
    latest = web3.eth.block_number
    
    print("\n=== Недавняя активность ===")
    print(f"Последний блок: {latest}")
    
    # Проверяем последние 5 блоков
    for i in range(max(0, latest - 4), latest + 1):
        block = web3.eth.get_block(i, full_transactions=True)
        print(f"\nБлок {i}:")
        print(f"  Hash: {block.hash.hex()}")
        print(f"  Timestamp: {block.timestamp}")
        print(f"  Транзакций: {len(block.transactions)}")
        
        for tx in block.transactions:
            print(f"  TX: {tx.hash.hex()}")
            print(f"    From: {tx['from']}")
            print(f"    To: {tx['to']}")
            print(f"    Value: {web3.from_wei(tx['value'], 'ether')} ETH")
            print(f"    Gas: {tx['gas']}")
            print(f"    Gas Price: {web3.from_wei(tx['gasPrice'], 'gwei')} Gwei")


def print_accounts_and_balances(web3):
    accounts = web3.eth.accounts
    print("\nАккаунты и балансы:")
    for acc in accounts:
        balance = web3.eth.get_balance(acc)
        print(f"{acc}: {web3.from_wei(balance, 'ether')} ETH")

def print_contract_code(web3, address):
    code = web3.eth.get_code(address)
    if code and code != b'':
        print(f"Контракт по адресу {address} найден, длина байткода: {len(code)}")
    else:
        print(f"Контракт по адресу {address} не найден (пустой байткод)")

def print_last_blocks(web3, n=3):
    latest = web3.eth.block_number
    print(f"\nПоследние {n} блоков:")
    for i in range(latest, max(latest-n, 0), -1):
        block = web3.eth.get_block(i, full_transactions=True)
        print(f"Блок {i}: hash={block.hash.hex()}, txs={len(block.transactions)}")
        for tx in block.transactions:
            print(f"  TX: {tx.hash.hex()} from {tx['from']} to {tx['to']}")


def print_all_contracts(web3, n_blocks=20):
    print(f"\nПоиск контрактов в последних {n_blocks} блоках:")
    latest = web3.eth.block_number
    found = set()
    for i in range(max(0, latest - n_blocks + 1), latest + 1):
        block = web3.eth.get_block(i, full_transactions=True)
        for tx in block.transactions:
            to_addr = tx['to']
            if to_addr and to_addr not in found:
                code = web3.eth.get_code(to_addr)
                if code and code != b'':
                    print(f"Контракт найден: {to_addr} (длина байткода: {len(code)}) в блоке {i}")
                    found.add(to_addr)
    if not found:
        print("Контракты не найдены в последних блоках.")


# Подключение к локальной или тестовой POA-сети
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Инжекция middleware для обработки extraData
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Проверка подключения
print(w3.client_version) 