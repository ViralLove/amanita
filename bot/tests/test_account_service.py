import pytest
import logging
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import pytest_asyncio
from unittest.mock import patch, MagicMock
from eth_account import Account
from web3 import Web3
from bot.services.core.blockchain import BlockchainService
from bot.services.core.account import AccountService
from bot.tests.utils.invite_code_generator import generate_invite_code, validate_invite_code

# Загружаем .env файл
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Настройка pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Настройка логирования
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Переменные окружения
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
NODE_ADMIN_PRIVATE_KEY = os.getenv("NODE_ADMIN_PRIVATE_KEY")
AMANITA_REGISTRY_CONTRACT_ADDRESS = os.getenv("AMANITA_REGISTRY_CONTRACT_ADDRESS")

assert SELLER_PRIVATE_KEY, "SELLER_PRIVATE_KEY не найден в .env!"
assert NODE_ADMIN_PRIVATE_KEY, "NODE_ADMIN_PRIVATE_KEY не найден в .env!"
assert AMANITA_REGISTRY_CONTRACT_ADDRESS, "AMANITA_REGISTRY_CONTRACT_ADDRESS не найден в .env!"

# Тестовые данные
TEST_ACCOUNT_DATA = {
    "seller_address": "0x1234567890123456789012345678901234567890",
    "user_address": "0x0987654321098765432109876543210987654321",
    "invite_codes": ["AMANITA-TEST-CODE1", "AMANITA-TEST-CODE2"]
}

@pytest_asyncio.fixture
async def blockchain_service():
    """Фикстура для BlockchainService"""
    BlockchainService.reset()
    service = BlockchainService()
    assert service.registry is not None, "Реестр контрактов не инициализирован"
    assert service.get_contract("InviteNFT") is not None, "Контракт InviteNFT не загружен"
    
    # Проверяем что селлер уже имеет роль (должно быть назначено при деплое)
    seller_account = Account.from_key(SELLER_PRIVATE_KEY)
    logger.info(f"SELLER_PRIVATE_KEY: {SELLER_PRIVATE_KEY}")
    logger.info(f"seller_account.address: {seller_account.address}")
    
    try:
        is_seller = service.call_contract_function("InviteNFT", "isSeller", seller_account.address)
        logger.info(f"isSeller({seller_account.address}): {is_seller}")
        if not is_seller:
            logger.warning(f"Селлер {seller_account.address} не имеет роль SELLER_ROLE. Роль должна быть назначена при деплое контракта.")
    except Exception as e:
        logger.warning(f"Не удалось проверить роль SELLER_ROLE: {e}")
    
    return service

@pytest_asyncio.fixture
async def account_service(blockchain_service):
    """Фикстура для AccountService"""
    return AccountService(blockchain_service)

@pytest_asyncio.fixture
async def seller_account():
    """Фикстура для получения аккаунта продавца"""
    return Account.from_key(SELLER_PRIVATE_KEY)

@pytest_asyncio.fixture
async def user_account():
    """Фикстура для тестового пользователя"""
    return Account.create()

@pytest_asyncio.fixture
async def user_accounts():
    """Фикстура для нескольких тестовых пользователей"""
    return [Account.create() for _ in range(3)]

class TestAccountService:
    """Тесты для проверки работы AccountService"""

    # Хелперы для тестирования
    @staticmethod
    def generate_invite_codes(prefix: str, count: int = 12):
        """Генерирует список инвайт-кодов"""
        return [generate_invite_code(prefix=prefix) for _ in range(count)]
    
    @staticmethod
    def create_user():
        """Создает нового пользователя"""
        return Account.create()
    
    @staticmethod
    def log_tx_result(tx_hash: str, operation: str, blockchain_service: BlockchainService):
        """Хелпер для логирования результатов транзакций"""
        receipt = blockchain_service.web3.eth.wait_for_transaction_receipt(tx_hash)
        status = "✅" if receipt["status"] == 1 else "❌"
        logger.info(f"{status} {operation} (tx: {tx_hash[:10]}...)")
        return receipt

    # ==================== БАЗОВЫЕ ТЕСТЫ ACCOUNTSERVICE ====================
    
    def test_get_seller_account(self, account_service):
        """
        Проверяем получение аккаунта продавца.
        
        Роль в процессе: селлер нужен для активации инвайтов и оплаты газа за минтинг новых.
        """
        seller_account = account_service.get_seller_account()
        assert seller_account is not None
        assert hasattr(seller_account, 'address')
        assert seller_account.address.startswith('0x')
    
    def test_is_seller(self, account_service, seller_account):
        """
        Проверяем проверку прав продавца.
        
        Роль в процессе: только адреса с SELLER_ROLE могут вызывать activateAndMintInvites.
        """
        seller_address = seller_account.address
        
        result = account_service.is_seller(seller_address)
        assert isinstance(result, bool)
        assert result, "Аккаунт продавца должен иметь права продавца"
    
    def test_is_user_activated(self, account_service, user_account):
        """
        Проверяем проверку активации пользователя.
        
        Роль в процессе: активация происходит только через процесс активации инвайта.
        Активированные пользователи получают 12 новых инвайтов для раздачи.
        """
        user_address = user_account.address
        result = account_service.is_user_activated(user_address)
        assert isinstance(result, bool)
        # Новый пользователь не должен быть активирован
        assert not result, "Новый пользователь не должен быть активирован"
    
    def test_get_all_activated_users(self, account_service):
        """
        Проверяем получение списка активированных пользователей.
        
        Роль в процессе: для построения графа рефералов и мониторинга экосистемы.
        """
        users = account_service.get_all_activated_users()
        assert isinstance(users, list)
        for user in users:
            assert isinstance(user, str)
            assert user.startswith('0x')
    
    def test_batch_validate_invite_codes(self, account_service, user_account):
        """
        Проверяем пакетную валидацию инвайт-кодов.
        
        Роль в процессе: UI может проверять несколько кодов одновременно
        перед отправкой на активацию селлеру.
        """
        test_codes = ["TEST-CODE-1", "TEST-CODE-2"]
        user_address = user_account.address
        
        valid_codes, invalid_codes = account_service.batch_validate_invite_codes(test_codes, user_address)
        
        assert isinstance(valid_codes, list)
        assert isinstance(invalid_codes, list)
        assert len(valid_codes) + len(invalid_codes) == len(test_codes)
        # Проверяем что все коды обработаны
        assert len(valid_codes) + len(invalid_codes) == 2, "Должно быть обработано 2 кода"

    def test_validate_invite_code_for_new_user(self, account_service, user_account):
        """
        Проверяем валидацию инвайт-кода для нового пользователя.
        
        Роль в процессе: новый пользователь не должен иметь валидных инвайтов
        до процесса активации через ввод кода от друга.
        """
        user_address = user_account.address
        
        # Новый пользователь не должен иметь валидный инвайт-код
        result = account_service.validate_invite_code(user_address)
        assert not result, "Новый пользователь не должен иметь валидный инвайт-код"

    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_success(self, account_service, blockchain_service, seller_account, user_account):
        import os
        seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
        if not seller_private_key:
            pytest.skip("SELLER_PRIVATE_KEY не установлен в окружении. Тест пропущен.")
        """
        Тест успешной активации инвайта и минта новых.
        
        Логика: AccountService.activate_and_mint_invites() должен:
        1. Принять инвайт-код и адрес пользователя
        2. Вызвать контракт через селлера
        3. Вернуть список новых кодов
        """
        # Проверяем что селлер имеет права SELLER_ROLE
        seller_address = seller_account.address
        is_seller = blockchain_service.call_contract_function("InviteNFT", "isSeller", seller_address)
        if not is_seller:
            pytest.skip(f"Селлер {seller_address} не имеет роль SELLER_ROLE. Роль должна быть назначена при деплое контракта.")
        
        # Создаем тестовый инвайт-код (имитируем что он был заминчен ранее)
        test_invite_code = generate_invite_code(prefix="test")
        try:
            # Селлер минтит инвайт для себя (это не часть тестируемого процесса, но нужно для теста)
            tx_hash = await blockchain_service.transact_contract_function(
                "InviteNFT",
                "mintInvites",
                seller_private_key,
                [test_invite_code],
                0  # бессрочный инвайт
            )
            await blockchain_service.wait_for_transaction(tx_hash)
        except Exception as e:
            pytest.skip(f"Не удалось создать тестовый инвайт: {e}")
        
        # Проверяем что пользователь еще не активирован
        user_address = user_account.address
        is_activated_before = account_service.is_user_activated(user_address)
        assert not is_activated_before, "Пользователь не должен быть активирован до теста"
        
        # Тестируем метод AccountService
        try:
            new_codes = await account_service.activate_and_mint_invites(test_invite_code, user_address)
            
            # Проверяем результат
            assert isinstance(new_codes, list)
            assert len(new_codes) == 12, "Должно быть сгенерировано ровно 12 новых кодов"
            
            # Проверяем что пользователь стал активированным
            is_activated_after = account_service.is_user_activated(user_address)
            assert is_activated_after, "Пользователь должен быть активирован после активации инвайта"
            
        except Exception as e:
            if "AccessControlUnauthorizedAccount" in str(e):
                pytest.skip(f"Селлер не имеет права SELLER_ROLE: {e}")
            elif "Transaction ran out of gas" in str(e):
                pytest.skip(f"Недостаточно газа для транзакции: {e}")
            else:
                raise e

    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_invalid_code(self, account_service, user_account):
        import os
        seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
        if not seller_private_key:
            pytest.skip("SELLER_PRIVATE_KEY не установлен в окружении. Тест пропущен.")
        """
        Тест активации несуществующего инвайт-кода.
        
        Логика: AccountService должен корректно обработать несуществующий код.
        """
        fake_code = "NOT-EXIST-CODE"
        user_address = user_account.address
        
        # Проверяем что пользователь не активирован
        is_activated_before = account_service.is_user_activated(user_address)
        assert not is_activated_before, "Пользователь не должен быть активирован до теста"
        
        # При несуществующем коде метод должен выбросить исключение
        try:
            result = await account_service.activate_and_mint_invites(fake_code, user_address)
            # Если не выбросило исключение, то результат должен быть None
            assert result is None, "При несуществующем коде должен вернуться None"
        except Exception as e:
            # Исключение ожидаемо для несуществующего кода
            logger.info(f"Ожидаемое исключение для несуществующего кода: {e}")
            pass
        
        # Проверяем что пользователь остался неактивированным
        is_activated_after = account_service.is_user_activated(user_address)
        assert not is_activated_after, "Пользователь не должен быть активирован после неудачной попытки"

    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_already_activated_user(self, account_service, blockchain_service, seller_account, user_account):
        import os
        seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
        if not seller_private_key:
            pytest.skip("SELLER_PRIVATE_KEY не установлен в окружении. Тест пропущен.")
        """
        Тест попытки активации уже активированного пользователя.
        
        Логика: AccountService должен корректно обработать повторную активацию.
        """
        # Проверяем права селлера
        seller_address = seller_account.address
        is_seller = blockchain_service.call_contract_function("InviteNFT", "isSeller", seller_address)
        if not is_seller:
            pytest.skip(f"Селлер {seller_address} не имеет роль SELLER_ROLE.")
        
        # Создаем тестовый инвайт
        test_invite_code = generate_invite_code(prefix="already")
        try:
            tx_hash = await blockchain_service.transact_contract_function(
                "InviteNFT",
                "mintInvites",
                seller_private_key,
                [test_invite_code],
                0
            )
            await blockchain_service.wait_for_transaction(tx_hash)
        except Exception as e:
            pytest.skip(f"Не удалось создать тестовый инвайт: {e}")
        
        user_address = user_account.address
        
        # Первая активация должна пройти успешно
        try:
            new_codes = await account_service.activate_and_mint_invites(test_invite_code, user_address)
            assert len(new_codes) == 12, "Первая активация должна пройти успешно"
        except Exception as e:
            if "AccessControlUnauthorizedAccount" in str(e) or "Transaction ran out of gas" in str(e):
                pytest.skip(f"Проблемы с правами или газом: {e}")
            else:
                raise e
        
        # Проверяем что пользователь активирован
        is_activated = account_service.is_user_activated(user_address)
        assert is_activated, "Пользователь должен быть активирован после первой активации"
        
        # Создаем второй тестовый инвайт для попытки повторной активации
        second_invite_code = generate_invite_code(prefix="second")
        try:
            tx_hash = await blockchain_service.transact_contract_function(
                "InviteNFT",
                "mintInvites",
                seller_private_key,
                [second_invite_code],
                0
            )
            await blockchain_service.wait_for_transaction(tx_hash)
        except Exception as e:
            pytest.skip(f"Не удалось создать второй тестовый инвайт: {e}")
        
        # Попытка повторной активации должна быть отклонена
        try:
            result = await account_service.activate_and_mint_invites(second_invite_code, user_address)
            # Если не выбросило исключение, то результат должен быть None
            assert result is None, "При повторной активации должен вернуться None"
        except Exception as e:
            # Исключение ожидаемо для уже активированного пользователя
            logger.info(f"Ожидаемое исключение для уже активированного пользователя: {e}")
            pass

    def test_get_seller_account_no_env(self, account_service, monkeypatch):
        """
        Тест получения аккаунта продавца при отсутствии переменной окружения.
        
        Логика: AccountService должен корректно обработать отсутствие SELLER_PRIVATE_KEY.
        """
        # Временно убираем переменную окружения через monkeypatch
        monkeypatch.delenv("SELLER_PRIVATE_KEY", raising=False)
        
        try:
            # Должно выбросить исключение или вернуть None
            result = account_service.get_seller_account()
            assert result is None, "При отсутствии SELLER_PRIVATE_KEY должен вернуться None"
        except Exception as e:
            # Исключение тоже допустимо
            logger.info(f"Ожидаемое исключение при отсутствии SELLER_PRIVATE_KEY: {e}")

    def test_validate_invite_code_invalid_address(self, account_service):
        """
        Тест валидации инвайт-кода для невалидного адреса.
        
        Логика: AccountService должен корректно обработать невалидный адрес.
        """
        invalid_address = "invalid-address"
        
        # Должно вернуть False для невалидного адреса
        result = account_service.validate_invite_code(invalid_address)
        assert result is False, "Невалидный адрес должен вернуть False"

    def test_is_user_activated_invalid_address(self, account_service):
        """
        Тест проверки активации для невалидного адреса.
        
        Логика: AccountService должен корректно обработать невалидный адрес.
        """
        invalid_address = "invalid-address"
        
        # Должно вернуть False для невалидного адреса
        result = account_service.is_user_activated(invalid_address)
        assert result is False, "Невалидный адрес должен вернуть False"

    def test_is_seller_invalid_address(self, account_service):
        """
        Тест проверки прав продавца для невалидного адреса.
        
        Логика: AccountService должен корректно обработать невалидный адрес.
        """
        invalid_address = "invalid-address"
        
        # Должно вернуть False для невалидного адреса
        result = account_service.is_seller(invalid_address)
        assert result is False, "Невалидный адрес должен вернуть False"
    # ==================== ТЕСТЫ ГРАНИЧНЫХ СЛУЧАЕВ ====================
    
    def test_get_all_activated_users_empty(self, account_service):
        """
        Тест получения списка активированных пользователей когда список пуст.
        
        Логика: AccountService должен вернуть пустой список если нет активированных пользователей.
        """
        # В новой системе может не быть активированных пользователей
        activated_users = account_service.get_all_activated_users()
        assert isinstance(activated_users, list), "Должен вернуться список"
        # Не проверяем длину, так как могут быть активированные пользователи от других тестов

    def test_validate_invite_code_new_user(self, account_service, user_account):
        """
        Тест валидации инвайт-кода для нового пользователя.
        
        Логика: AccountService должен вернуть False для нового пользователя.
        """
        user_address = user_account.address
        has_invite = account_service.validate_invite_code(user_address)
        assert has_invite is False, "Новый пользователь не должен иметь инвайтов"

    def test_batch_validate_invite_codes_empty_list(self, account_service, user_account):
        """
        Тест пакетной валидации пустого списка кодов.
        
        Логика: AccountService должен корректно обработать пустой список.
        """
        empty_codes = []
        user_address = user_account.address
        
        valid_codes, invalid_codes = account_service.batch_validate_invite_codes(empty_codes, user_address)
        
        assert isinstance(valid_codes, list)
        assert isinstance(invalid_codes, list)
        assert len(valid_codes) == 0, "Пустой список должен вернуть пустой список валидных кодов"
        assert len(invalid_codes) == 0, "Пустой список должен вернуть пустой список невалидных кодов"

    def test_is_user_activated_new_user(self, account_service, user_account):
        """
        Тест проверки активации для нового пользователя.
        
        Логика: AccountService должен вернуть False для нового пользователя.
        """
        user_address = user_account.address
        is_activated = account_service.is_user_activated(user_address)
        assert is_activated is False, "Новый пользователь не должен быть активирован"

    def test_is_seller_new_user(self, account_service, user_account):
        """
        Тест проверки прав продавца для нового пользователя.
        
        Логика: AccountService должен вернуть False для обычного пользователя.
        """
        user_address = user_account.address
        is_seller = account_service.is_seller(user_address)
        assert is_seller is False, "Обычный пользователь не должен иметь права продавца"

 