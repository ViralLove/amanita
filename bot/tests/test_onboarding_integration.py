# Тесты для сценария онбординга 

import os
import pytest
import logging
from datetime import datetime
from bot.services.core.blockchain import BlockchainService
from eth_account import Account
from dotenv import load_dotenv
from bot.tests.utils.invite_code_generator import generate_invite_code, validate_invite_code

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env в /bot
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Устанавливаем профиль на localhost для теста
os.environ["BLOCKCHAIN_PROFILE"] = "localhost"

# Получаем адрес реестра из .env
AMANITA_REGISTRY_CONTRACT_ADDRESS = os.getenv("AMANITA_REGISTRY_CONTRACT_ADDRESS")
assert AMANITA_REGISTRY_CONTRACT_ADDRESS, "AMANITA_REGISTRY_CONTRACT_ADDRESS не найден в .env!"

# Добавляем загрузку приватного ключа деплоера
NODE_ADMIN_PRIVATE_KEY = os.getenv("NODE_ADMIN_PRIVATE_KEY")
assert NODE_ADMIN_PRIVATE_KEY, "NODE_ADMIN_PRIVATE_KEY не найден в .env!"

# Добавляем загрузку приватного ключа продавца
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
assert SELLER_PRIVATE_KEY, "SELLER_PRIVATE_KEY не найден в .env!"

@pytest.fixture
def blockchain_service():
    """Фикстура для создания экземпляра BlockchainService"""
    service = BlockchainService()
    # Проверяем, что реестр и контракты инициализированы
    assert service.registry is not None, "Реестр контрактов не инициализирован"
    assert service.get_contract("InviteNFT") is not None, "Контракт InviteNFT не загружен"
    return service

@pytest.fixture
def seller_account():
    """Фикстура для получения аккаунта продавца"""
    seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
    assert seller_private_key, "SELLER_PRIVATE_KEY не найден в окружении"
    return Account.from_key(seller_private_key)

@pytest.fixture
def generate_account():
    """Фикстура для генерации новых аккаунтов"""
    return Account.create()

@pytest.fixture
def user1_account():
    """Фикстура для первого тестового пользователя"""
    return Account.create()

@pytest.fixture
def user2_account():
    """Фикстура для второго тестового пользователя"""
    return Account.create()

# Хелпер для вызова с явным адресом контракта

def call_contract_function(self, contract_name, function_name, *args, **kwargs):
    contract = self.get_contract(contract_name)
    if not contract:
        self._log(f"Контракт {contract_name} не найден", error=True)
        return None
    # Отделяем служебные параметры, чтобы не передавать их в функцию контракта
    service_keys = ['sender', 'contract_address', 'gas', 'gasPrice', 'nonce']
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in service_keys}
    try:
        func = getattr(contract.functions, function_name)
        result = func(*args, **filtered_kwargs).call()
        self._log(f"Вызов {contract_name}.{function_name} успешен: {result}")
        return result
    except Exception as e:
        self._log(f"Ошибка вызова {contract_name}.{function_name}: {e}", error=True)
        return None

def call_contract_function_with_address(service, method, *args, sender=None):
    # Для call_contract_function не передаём sender и contract_address в kwargs
    return service.call_contract_function(
        "InviteNFT",
        method,
        *args
    )

# Хелперы для генерации inviteCodes и пользователей

def generate_invite_codes(prefix, count=12):
    return [f"{prefix}{i}" for i in range(count)]

def create_user():
    return Account.create()

def log_tx_result(tx_hash, operation, blockchain_service):
    """Хелпер для компактного логирования результатов транзакций"""
    receipt = blockchain_service.web3.eth.wait_for_transaction_receipt(tx_hash)
    status = "✅" if receipt["status"] == 1 else "❌"
    logger.info(f"{status} {operation} (tx: {tx_hash[:10]}...)")
    return receipt

def test_onboarding_flow(blockchain_service, seller_account, generate_account):
    """Тест полного процесса онбординга"""
    logger.info("🚀 Начало теста onboarding flow")
    
    # Проверяем, что реестр и контракты инициализированы
    assert blockchain_service.registry is not None, "Реестр контрактов не инициализирован"
    invite_nft_contract = blockchain_service.get_contract("InviteNFT")
    assert invite_nft_contract is not None, "Контракт InviteNFT не загружен"
    
    # Назначаем роль SELLER_ROLE продавцу (если не назначено)
    logger.info("📝 Проверка роли SELLER_ROLE для продавца...")
    SELLER_ROLE = blockchain_service.web3.keccak(text="SELLER_ROLE")
    if not invite_nft_contract.functions.hasRole(SELLER_ROLE, seller_account.address).call():
        tx_hash = blockchain_service.transact_contract_function(
            "InviteNFT",
            "grantRole",
            NODE_ADMIN_PRIVATE_KEY,
            SELLER_ROLE,
            seller_account.address
        )
        blockchain_service.web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info("✅ Роль SELLER_ROLE успешно назначена продавцу")
    else:
        logger.info("✅ Продавец уже имеет роль SELLER_ROLE")
    
    # 1. Проверяем баланс ETH
    logger.info("💰 Проверка баланса ETH продавца...")
    seller_balance = blockchain_service.web3.eth.get_balance(seller_account.address)
    min_required_balance = blockchain_service.web3.to_wei(0.1, 'ether')
    assert seller_balance >= min_required_balance, f"Недостаточно ETH у продавца. Требуется минимум 0.1 ETH, текущий баланс: {blockchain_service.web3.from_wei(seller_balance, 'ether')} ETH"
    logger.info(f"✅ Баланс ETH продавца: {blockchain_service.web3.from_wei(seller_balance, 'ether')} ETH")
    
    # 2. Проверяем, что продавец не был ранее активирован
    logger.info("🔍 Проверка статуса активации продавца...")
    assert not call_contract_function_with_address(
        blockchain_service,
        "isUserActivated",
        seller_account.address
    ), "Продавец уже был активирован ранее"
    logger.info("✅ Продавец не активирован (ожидаемый статус)")

    # 3. Продавец минтит 12 инвайтов для стартовой аудитории
    logger.info("🎫 Минтинг 12 стартовых инвайтов...")
    initial_invite_codes = [generate_invite_code(prefix="INVITE") for _ in range(12)]
    logger.info(f"Параметры mintInvites: invite_codes={initial_invite_codes}, expiry=0")
    try:
        tx_hash = blockchain_service.transact_contract_function(
            "InviteNFT",
            "mintInvites",
            SELLER_PRIVATE_KEY,
            initial_invite_codes,
            0,
            gas=3000000
        )
        logger.info(f"Транзакция отправлена, tx_hash={tx_hash}")
        receipt = blockchain_service.web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Транзакция успешно выполнена, receipt={receipt}")
        logger.info("✅ Стартовые инвайты успешно заминчены")
    except Exception as e:
        logger.error(f"Ошибка при минтинге инвайтов: {e}")
        raise
    
    # 4. Проверяем, что все инвайты созданы
    logger.info("🔍 Проверка созданных инвайтов...")
    for code in initial_invite_codes:
        token_id = call_contract_function_with_address(
            blockchain_service,
            "getTokenIdByInviteCode",
            code
        )
        assert token_id > 0
        assert not call_contract_function_with_address(
            blockchain_service,
            "isInviteTokenUsed",
            token_id
        )
    logger.info("✅ Все инвайты успешно созданы и не использованы")

    # 5. Создаем первого пользователя и активируем инвайт
    logger.info("👤 Создание первого пользователя...")
    user1 = create_user()
    user1_invite_code = initial_invite_codes[0]
    logger.info(f"✅ Создан пользователь с адресом: {user1.address}")
    
    # 6. Генерируем 12 новых инвайтов для user1
    logger.info("🎫 Генерация 12 новых инвайтов для первого пользователя...")
    user1_new_invites = [generate_invite_code(prefix="USER1") for _ in range(12)]
    
    # 7. Активируем инвайт и минтим новые
    logger.info("🔄 Активация инвайта и минт новых инвайтов для первого пользователя...")
    logger.info(f"Параметры activateAndMintInvites: invite_code={user1_invite_code}, user_address={user1.address}, new_invites={user1_new_invites}, expiry=0")
    logger.info(f"Аккаунт отправителя: {seller_account.address}")
    nonce = blockchain_service.web3.eth.get_transaction_count(seller_account.address)
    balance = blockchain_service.web3.eth.get_balance(seller_account.address)
    logger.info(f"Nonce: {nonce}, Баланс: {blockchain_service.web3.from_wei(balance, 'ether')} ETH")
    gas_limit = 4000000
    logger.info(f"Лимит газа: {gas_limit}")
    
    tx_hash = blockchain_service.transact_contract_function(
        "InviteNFT",
        "activateAndMintInvites",
        SELLER_PRIVATE_KEY,
        user1_invite_code,
        user1.address,
        user1_new_invites,
        0,
        gas=gas_limit
    )
    logger.info(f"Транзакция отправлена: {tx_hash}")
    receipt = blockchain_service.web3.eth.wait_for_transaction_receipt(tx_hash)
    logger.info(f"Транзакция выполнена: gasUsed={receipt['gasUsed']}, status={receipt['status']}")
    
    # Проверяем баланс инвайтов
    invite_balance = blockchain_service.call_contract_function(
        "InviteNFT",
        "balanceOf",
        user1.address
    )
    logger.info(f"Баланс инвайтов после активации: {invite_balance}")
    
    # 8. Проверяем, что user1 активирован
    logger.info("🔍 Проверка активации первого пользователя...")
    assert call_contract_function_with_address(
        blockchain_service,
        "isUserActivated",
        user1.address
    )
    logger.info("✅ Первый пользователь успешно активирован")
    
    # 9. Проверяем, что user1 получил свои 12 инвайтов
    logger.info("🔍 Проверка полученных инвайтов первого пользователя...")
    user1_invites = call_contract_function_with_address(
        blockchain_service,
        "getUserInvites",
        user1.address
    )
    assert len(user1_invites) == 12
    logger.info(f"✅ Первый пользователь получил {len(user1_invites)} инвайтов")

    # 10. Создаем второго пользователя через инвайт от user1
    logger.info("👤 Создание второго пользователя...")
    user2 = create_user()
    user2_invite_code = user1_new_invites[0]
    logger.info(f"✅ Создан пользователь с адресом: {user2.address}")
    
    # 11. Генерируем 12 новых инвайтов для user2
    logger.info("🎫 Генерация 12 новых инвайтов для второго пользователя...")
    user2_new_invites = [generate_invite_code(prefix="USER2") for _ in range(12)]
    
    # 12. Активируем инвайт и минтим новые
    logger.info("\n🔄 Активация инвайта и минт новых инвайтов для второго пользователя...")
    logger.info(f"Параметры activateAndMintInvites: invite_code={user2_invite_code}, user_address={user2.address}, new_invites={user2_new_invites}, expiry=0")
    logger.info(f"Аккаунт отправителя: {seller_account.address}")
    nonce = blockchain_service.web3.eth.get_transaction_count(seller_account.address)
    balance = blockchain_service.web3.eth.get_balance(seller_account.address)
    logger.info(f"Nonce: {nonce}, Баланс: {blockchain_service.web3.from_wei(balance, 'ether')} ETH")
    gas_limit = 4000000
    logger.info(f"Лимит газа: {gas_limit}")
    
    tx_hash = blockchain_service.transact_contract_function(
        "InviteNFT",
        "activateAndMintInvites",
        SELLER_PRIVATE_KEY,
        user2_invite_code,
        user2.address,
        user2_new_invites,
        0,
        gas=gas_limit
    )
    logger.info(f"Транзакция отправлена: {tx_hash}")
    receipt = blockchain_service.web3.eth.wait_for_transaction_receipt(tx_hash)
    logger.info(f"Транзакция выполнена: gasUsed={receipt['gasUsed']}, status={receipt['status']}")
    
    # Проверяем баланс инвайтов
    invite_balance = blockchain_service.call_contract_function(
        "InviteNFT",
        "balanceOf",
        user2.address
    )
    logger.info(f"Баланс инвайтов после активации: {invite_balance}")
    
    # 13. Проверяем, что user2 активирован
    logger.info("🔍 Проверка активации второго пользователя...")
    assert call_contract_function_with_address(
        blockchain_service,
        "isUserActivated",
        user2.address
    )
    logger.info("✅ Второй пользователь успешно активирован")
    
    # 14. Проверяем, что user2 получил свои 12 инвайтов
    logger.info("🔍 Проверка полученных инвайтов второго пользователя...")
    user2_invites = call_contract_function_with_address(
        blockchain_service,
        "getUserInvites",
        user2.address
    )
    assert len(user2_invites) == 12
    logger.info(f"✅ Второй пользователь получил {len(user2_invites)} инвайтов")

    # 15. Проверяем события
    logger.info("📊 Проверка событий контракта...")
    
    # 16. Получаем все события InviteActivated
    logger.info("🔍 Проверка событий InviteActivated...")
    web3 = blockchain_service.web3
    contract = blockchain_service.get_contract("InviteNFT")
    # Сигнатура: event InviteActivated(address indexed user, string inviteCode, uint256 tokenId, uint256 timestamp);
    event_signature_hash = web3.keccak(text="InviteActivated(address,string,uint256,uint256)").hex()
    logs = web3.eth.get_logs({
        "fromBlock": receipt['blockNumber'] - 10,
        "toBlock": receipt['blockNumber'],
        "address": contract.address,
        "topics": [event_signature_hash]
    })
    logger.info(f"Найдено {len(logs)} raw логов InviteActivated")
    for log in logs:
        event = contract.events.InviteActivated().process_log(log)
        logger.info(f"Событие InviteActivated:")
        logger.info(f"  - Адрес: {event['args']['user']}")
        logger.info(f"  - Инвайт код: {event['args']['inviteCode']}")
        logger.info(f"  - Token ID: {event['args']['tokenId']}")
        logger.info(f"  - Timestamp: {event['args']['timestamp']}")
    
    # 17. Проверяем события BatchInvitesMinted
    logger.info("🔍 Проверка событий BatchInvitesMinted...")
    # Сигнатура: event BatchInvitesMinted(address indexed to, uint256[] tokenIds, string[] inviteCodes, uint256 expiry);
    batch_event_signature_hash = web3.keccak(text="BatchInvitesMinted(address,uint256[],string[],uint256)").hex()
    batch_logs = web3.eth.get_logs({
        "fromBlock": receipt['blockNumber'] - 10,
        "toBlock": receipt['blockNumber'],
        "address": contract.address,
        "topics": [batch_event_signature_hash]
    })
    logger.info(f"Найдено {len(batch_logs)} raw логов BatchInvitesMinted")
    for log in batch_logs:
        event = contract.events.BatchInvitesMinted().process_log(log)
        logger.info(f"Событие BatchInvitesMinted:")
        logger.info(f"  - Кому: {event['args']['to']}")
        logger.info(f"  - TokenIds: {event['args']['tokenIds']}")
        logger.info(f"  - InviteCodes: {event['args']['inviteCodes']}")
        logger.info(f"  - Expiry: {event['args']['expiry']}")
    
    # 18. Проверяем, что использованные инвайты помечены как использованные
    logger.info("🔍 Проверка статуса использованных инвайтов...")
    user1_token_id = call_contract_function_with_address(
        blockchain_service,
        "getTokenIdByInviteCode",
        user1_invite_code
    )
    user2_token_id = call_contract_function_with_address(
        blockchain_service,
        "getTokenIdByInviteCode",
        user2_invite_code
    )
    
    assert call_contract_function_with_address(
        blockchain_service,
        "isInviteTokenUsed",
        user1_token_id
    )
    assert call_contract_function_with_address(
        blockchain_service,
        "isInviteTokenUsed",
        user2_token_id
    )
    logger.info("✅ Все использованные инвайты помечены как использованные")
    
    # 19. Проверяем, что инвайты активированы
    logger.info("\n🔍 Проверка активации инвайтов...")
    for invite_code in [user1_invite_code, user2_invite_code]:
        token_id = call_contract_function_with_address(
            blockchain_service,
            "getTokenIdByInviteCode",
            invite_code
        )
        is_used = call_contract_function_with_address(
            blockchain_service,
            "isInviteTokenUsed",
            token_id
        )
        owner = blockchain_service.call_contract_function(
            "InviteNFT",
            "ownerOf",
            token_id
        )
        created_at = blockchain_service.call_contract_function(
            "InviteNFT",
            "getInviteCreatedAt",
            token_id
        )
        expiry = blockchain_service.call_contract_function(
            "InviteNFT",
            "getInviteExpiry",
            token_id
        )
        minter = blockchain_service.call_contract_function(
            "InviteNFT",
            "getInviteMinter",
            token_id
        )
        first_owner = blockchain_service.call_contract_function(
            "InviteNFT",
            "getInviteFirstOwner",
            token_id
        )
        logger.info(f"Инвайт {invite_code} (tokenId={token_id}):")
        logger.info(f"  - Использован: {is_used}")
        logger.info(f"  - Владелец: {owner}")
        logger.info(f"  - Дата создания: {created_at}")
        logger.info(f"  - Срок действия: {expiry}")
        logger.info(f"  - Мinter: {minter}")
        logger.info(f"  - Первый владелец: {first_owner}")
    
    logger.info("🎉 Тест onboarding flow успешно завершен!")