import pytest
from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv
import logging
import json

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
logger.info("Загружены переменные окружения")

# Получаем путь к корню проекта
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
logger.info(f"Корень проекта: {PROJECT_ROOT}")

@pytest.fixture
def web3():
    """Фикстура для подключения к Web3"""
    logger.info("Инициализация Web3 подключения к Ganache")
    # Используем локальный Ganache
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    if not w3.is_connected():
        raise ConnectionError("Не удалось подключиться к Ganache")
    logger.info(f"Подключено к Ganache. Chain ID: {w3.eth.chain_id}")
    return w3

@pytest.fixture
def seller_account(web3):
    """Фикстура для аккаунта продавца"""
    logger.info("Инициализация аккаунта продавца")
    # Получаем приватный ключ из .env
    private_key = os.getenv('SELLER_PRIVATE_KEY')
    if not private_key:
        raise ValueError("SELLER_PRIVATE_KEY не найден в .env")
    logger.info(f"Получен приватный ключ продавца: {private_key[:6]}...")
    
    # Создаем аккаунт из приватного ключа
    account = Account.from_key(private_key)
    logger.info(f"Создан аккаунт продавца: {account.address}")
    
    # Проверяем баланс
    balance = web3.eth.get_balance(account.address)
    logger.info(f"Баланс продавца: {web3.from_wei(balance, 'ether')} ETH")
    
    return account

@pytest.fixture
def user_account(web3):
    """Фикстура для тестового пользователя"""
    logger.info("Создание тестового пользователя")
    # Создаем новый аккаунт для тестов
    account = Account.create()
    logger.info(f"Создан тестовый пользователь: {account.address}")
    
    # Проверяем баланс
    balance = web3.eth.get_balance(account.address)
    logger.info(f"Баланс тестового пользователя: {web3.from_wei(balance, 'ether')} ETH")
    
    return account

@pytest.fixture
def user_accounts(web3):
    """Фикстура для нескольких тестовых пользователей"""
    logger.info("Создание пула тестовых пользователей")
    # Создаем несколько аккаунтов для тестов
    accounts = [Account.create() for _ in range(10)]
    logger.info(f"Создано {len(accounts)} тестовых пользователей")
    
    # Логируем адреса
    for i, acc in enumerate(accounts):
        balance = web3.eth.get_balance(acc.address)
        logger.info(f"Пользователь {i+1}: {acc.address}, баланс: {web3.from_wei(balance, 'ether')} ETH")
    
    return accounts

@pytest.fixture
def admin_account(web3):
    private_key = os.getenv('NODE_ADMIN_PRIVATE_KEY')
    if not private_key:
        raise ValueError("NODE_ADMIN_PRIVATE_KEY не найден в .env")
    account = Account.from_key(private_key)
    return account

@pytest.fixture
def invite_nft_contract(web3, seller_account, admin_account):
    """Фикстура для контракта InviteNFT"""
    logger.info("Инициализация контракта InviteNFT")
    
    # Загружаем ABI из artifacts
    contract_path = os.path.join(PROJECT_ROOT, 'artifacts', 'contracts', 'InviteNFT.sol', 'InviteNFT.json')
    logger.info(f"Загрузка ABI из {contract_path}")
    
    try:
        with open(contract_path, 'r') as f:
            contract_json = f.read()
            contract_data = json.loads(contract_json)
            contract_abi = contract_data['abi']
        logger.info("ABI успешно загружен")
    except Exception as e:
        logger.error(f"Ошибка при загрузке ABI: {str(e)}")
        raise
    
    # Получаем адрес контракта
    contract_address = os.getenv('INVITE_NFT_CONTRACT_ADDRESS')
    if not contract_address:
        logger.error("INVITE_NFT_CONTRACT_ADDRESS не найден в .env")
        raise ValueError("INVITE_NFT_CONTRACT_ADDRESS не найден в .env")
    logger.info(f"Адрес контракта: {contract_address}")
    
    # Создаем контракт
    try:
        contract = web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
        logger.info("Контракт успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка при инициализации контракта: {str(e)}")
        raise
    
    # Проверяем код контракта
    code = web3.eth.get_code(contract_address)
    if len(code) == 0:
        logger.error("Контракт не задеплоен по указанному адресу")
        raise ValueError("Контракт не задеплоен по указанному адресу")
    logger.info("Код контракта найден")
    
    # Назначаем роль продавца через raw-транзакцию от admin_account
    try:
        seller_role = contract.functions.SELLER_ROLE().call()
        logger.info(f"Получена роль продавца: {seller_role}")
        tx = contract.functions.grantRole(
            seller_role,
            seller_account.address
        ).build_transaction({
            'from': admin_account.address,
            'nonce': web3.eth.get_transaction_count(admin_account.address),
            'gas': 500000,
            'gasPrice': web3.to_wei('1', 'gwei')
        })
        signed_txn = web3.eth.account.sign_transaction(tx, private_key=os.getenv('NODE_ADMIN_PRIVATE_KEY'))
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Роль продавца назначена. TX: {tx_hash.hex()}")
    except Exception as e:
        logger.error(f"Ошибка при назначении роли продавца: {str(e)}")
        raise
    
    return contract

@pytest.fixture
def registry_contract(web3, admin_account):
    """Фикстура для контракта AmanitaRegistry"""
    logger.info("Инициализация контракта AmanitaRegistry")
    
    # Загружаем ABI из artifacts
    contract_path = os.path.join(PROJECT_ROOT, 'artifacts', 'contracts', 'AmanitaRegistry.sol', 'AmanitaRegistry.json')
    logger.info(f"Загрузка ABI из {contract_path}")
    
    try:
        with open(contract_path, 'r') as f:
            contract_json = f.read()
            contract_data = json.loads(contract_json)
            contract_abi = contract_data['abi']
        logger.info("ABI реестра успешно загружен")
    except Exception as e:
        logger.error(f"Ошибка при загрузке ABI реестра: {str(e)}")
        raise
    
    # Получаем адрес контракта реестра
    contract_address = os.getenv('AMANITA_REGISTRY_CONTRACT_ADDRESS')
    if not contract_address:
        logger.error("AMANITA_REGISTRY_CONTRACT_ADDRESS не найден в .env")
        raise ValueError("AMANITA_REGISTRY_CONTRACT_ADDRESS не найден в .env")
    logger.info(f"Адрес реестра: {contract_address}")
    
    # Создаем контракт
    try:
        contract = web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
        logger.info("Контракт реестра успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка при инициализации контракта реестра: {str(e)}")
        raise
    
    # Проверяем код контракта
    code = web3.eth.get_code(contract_address)
    if len(code) == 0:
        logger.error("Реестр не задеплоен по указанному адресу")
        raise ValueError("Реестр не задеплоен по указанному адресу")
    logger.info("Код контракта реестра найден")
    
    return contract 