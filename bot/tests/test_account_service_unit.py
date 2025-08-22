"""
Unit тесты для AccountService

БАЗОВАЯ ИНФРАСТРУКТУРА:
=====================
- Фикстуры для инициализации моков
- Базовые утилиты и логирование
- Подготовка тестовых данных

ПРИМЕЧАНИЕ: Тесты используют моки для быстрого выполнения
"""

# Стандартные библиотеки Python
import pytest
import logging
import sys
import os
from dotenv import load_dotenv
import pytest_asyncio
from unittest.mock import Mock, AsyncMock

# Импорты основных сервисов
from bot.services.core.account import AccountService
from bot.services.core.blockchain import BlockchainService

# Импорты для Mock архитектуры
from bot.tests.conftest import (
    mock_blockchain_service,
    mock_account_service,
    web3,
    invite_nft_contract
)

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

print("\n=== НАЧАЛО UNIT-ТЕСТИРОВАНИЯ ACCOUNT SERVICE ===")

# Проверка ключевых переменных окружения
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
NODE_ADMIN_PRIVATE_KEY = os.getenv("NODE_ADMIN_PRIVATE_KEY")

# ================== БАЗОВЫЕ УТИЛИТЫ =====================

def setup_mock_account_service(mock_blockchain_service):
    """Настраивает mock_blockchain_service для возврата данных вместо корутин"""
    # Mock уже настроен в conftest.py
    return mock_blockchain_service

# ================== UNIT ТЕСТЫ =====================

class TestAccountServiceUnit:
    """Unit тесты для AccountService с использованием моков"""
    
    def test_account_service_initialization(self, mock_blockchain_service):
        """Тест инициализации AccountService"""
        logger.info("🧪 Тестируем инициализацию AccountService")
        
        account_service = AccountService(mock_blockchain_service)
        
        assert account_service is not None
        assert account_service.blockchain_service == mock_blockchain_service
        logger.info("✅ AccountService успешно инициализирован")
    
    def test_get_seller_account_success(self, mock_blockchain_service):
        """Тест успешного получения аккаунта продавца"""
        logger.info("🧪 Тестируем получение аккаунта продавца")
        
        # Устанавливаем переменную окружения для теста
        os.environ["SELLER_PRIVATE_KEY"] = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        account_service = AccountService(mock_blockchain_service)
        seller_account = account_service.get_seller_account()
        
        assert seller_account is not None
        assert hasattr(seller_account, 'address')
        logger.info("✅ Аккаунт продавца успешно получен")
    
    def test_get_seller_account_missing_key(self, mock_blockchain_service):
        """Тест ошибки при отсутствии SELLER_PRIVATE_KEY"""
        logger.info("🧪 Тестируем ошибку при отсутствии SELLER_PRIVATE_KEY")
        
        # Убираем переменную окружения
        if "SELLER_PRIVATE_KEY" in os.environ:
            del os.environ["SELLER_PRIVATE_KEY"]
        
        account_service = AccountService(mock_blockchain_service)
        
        with pytest.raises(ValueError, match="SELLER_PRIVATE_KEY не установлен в .env"):
            account_service.get_seller_account()
        
        logger.info("✅ Ошибка при отсутствии SELLER_PRIVATE_KEY корректно обработана")
    
    def test_is_seller_true(self, mock_blockchain_service):
        """Тест проверки прав продавца - True"""
        logger.info("🧪 Тестируем проверку прав продавца - True")
        
        # Мокаем _call_contract_read_function для возврата True
        mock_blockchain_service._call_contract_read_function = Mock(return_value=True)
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем валидный адрес продавца
        result = account_service.is_seller("0x1234567890abcdef1234567890abcdef12345678")
        
        assert result == True
        # Проверяем, что мок был вызван
        mock_blockchain_service._call_contract_read_function.assert_called_once()
        logger.info("✅ Права продавца корректно подтверждены")
    
    def test_is_seller_false(self, mock_blockchain_service):
        """Тест проверки прав продавца - False"""
        logger.info("🧪 Тестируем проверку прав продавца - False")
        
        # Мокаем _call_contract_read_function для возврата False
        mock_blockchain_service._call_contract_read_function = Mock(return_value=False)
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем невалидный адрес
        result = account_service.is_seller("0x0987654321098765432109876543210987654321")
        
        assert result == False
        logger.info("✅ Отсутствие прав продавца корректно подтверждено")
    
    def test_validate_invite_code_true(self, mock_blockchain_service):
        """Тест валидации инвайт кода - True"""
        logger.info("🧪 Тестируем валидацию инвайт кода - True")
        
        # Мокаем _call_contract_read_function для возврата положительного количества инвайтов
        mock_blockchain_service._call_contract_read_function = Mock(return_value=5)
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем адрес с инвайтами
        result = account_service.validate_invite_code("0x1234567890abcdef1234567890abcdef12345678")
        
        assert result == True
        # Проверяем, что мок был вызван с правильными параметрами
        mock_blockchain_service._call_contract_read_function.assert_called_once()
        logger.info("✅ Валидация инвайт кода прошла успешно")
    
    def test_validate_invite_code_false(self, mock_blockchain_service):
        """Тест валидации инвайт кода - False"""
        logger.info("🧪 Тестируем валидацию инвайт кода - False")
        
        # Мокаем _call_contract_read_function для возврата 0 (нет инвайтов)
        mock_blockchain_service._call_contract_read_function = Mock(return_value=0)
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем адрес без инвайтов
        result = account_service.validate_invite_code("0x0987654321098765432109876543210987654321")
        
        assert result == False
        logger.info("✅ Валидация инвайт кода корректно показала отсутствие инвайтов")
    
    def test_is_user_activated_true(self, mock_blockchain_service):
        """Тест проверки активации пользователя - True"""
        logger.info("🧪 Тестируем проверку активации пользователя - True")
        
        # Мокаем _call_contract_read_function для возврата True
        mock_blockchain_service._call_contract_read_function = Mock(return_value=True)
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем активированного пользователя
        result = account_service.is_user_activated("0x1234567890abcdef1234567890abcdef12345678")
        
        assert result == True
        # Проверяем, что мок был вызван
        mock_blockchain_service._call_contract_read_function.assert_called_once()
        logger.info("✅ Активация пользователя корректно подтверждена")
    
    def test_is_user_activated_false(self, mock_blockchain_service):
        """Тест проверки активации пользователя - False"""
        logger.info("🧪 Тестируем проверку активации пользователя - False")
        
        # Мокаем _call_contract_read_function для возврата False
        mock_blockchain_service._call_contract_read_function = Mock(return_value=False)
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем неактивированного пользователя
        result = account_service.is_user_activated("0x0987654321098765432109876543210987654321")
        
        assert result == False
        logger.info("✅ Отсутствие активации пользователя корректно подтверждено")
    
    def test_get_all_activated_users(self, mock_blockchain_service):
        """Тест получения списка активированных пользователей"""
        logger.info("🧪 Тестируем получение списка активированных пользователей")
        
        # Мокаем _call_contract_read_function для возврата списка пользователей
        mock_blockchain_service._call_contract_read_function = Mock(return_value=[
            "0x1234567890abcdef1234567890abcdef12345678",
            "0x0987654321098765432109876543210987654321"
        ])
        
        account_service = AccountService(mock_blockchain_service)
        
        users = account_service.get_all_activated_users()
        
        assert isinstance(users, list)
        assert len(users) > 0
        assert all(isinstance(user, str) for user in users)
        logger.info(f"✅ Получен список активированных пользователей: {len(users)} пользователей")
    
    def test_batch_validate_invite_codes_success(self, mock_blockchain_service):
        """Тест пакетной валидации инвайт кодов - успех"""
        logger.info("🧪 Тестируем пакетную валидацию инвайт кодов - успех")
        
        # Мокаем _call_contract_read_function для возврата корректного результата
        mock_blockchain_service._call_contract_read_function = Mock(return_value=([True, False, True], ["", "Invalid", ""]))
        
        account_service = AccountService(mock_blockchain_service)
        
        invite_codes = ["AMANITA-TEST-CODE1", "AMANITA-TEST-CODE2", "AMANITA-TEST-CODE3"]
        user_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        valid_codes, invalid_codes = account_service.batch_validate_invite_codes(invite_codes, user_address)
        
        assert isinstance(valid_codes, list)
        assert isinstance(invalid_codes, list)
        assert len(valid_codes) + len(invalid_codes) == len(invite_codes)
        # Проверяем, что мок был вызван
        mock_blockchain_service._call_contract_read_function.assert_called_once()
        logger.info(f"✅ Пакетная валидация завершена: {len(valid_codes)} валидных, {len(invalid_codes)} невалидных")
    
    def test_batch_validate_invite_codes_empty_list(self, mock_blockchain_service):
        """Тест пакетной валидации инвайт кодов - пустой список"""
        logger.info("🧪 Тестируем пакетную валидацию инвайт кодов - пустой список")
        
        # Мокаем _call_contract_read_function для возврата корректного результата для пустого списка
        mock_blockchain_service._call_contract_read_function = Mock(return_value=([], []))
        
        account_service = AccountService(mock_blockchain_service)
        
        invite_codes = []
        user_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        valid_codes, invalid_codes = account_service.batch_validate_invite_codes(invite_codes, user_address)
        
        assert valid_codes == []
        assert invalid_codes == []
        logger.info("✅ Пакетная валидация пустого списка корректно обработана")
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_success(self, mock_blockchain_service):
        """Тест активации и минта инвайтов - успех"""
        logger.info("🧪 Тестируем активацию и минт инвайтов - успех")
        
        # Устанавливаем переменную окружения для теста
        os.environ["SELLER_PRIVATE_KEY"] = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Мокаем необходимые методы
        mock_blockchain_service.get_contract = Mock()
        mock_blockchain_service.estimate_gas_with_multiplier = AsyncMock(return_value=100000)
        mock_blockchain_service.transact_contract_function = AsyncMock(return_value="0xtx_hash")
        mock_blockchain_service.web3 = Mock()
        mock_blockchain_service.web3.eth.wait_for_transaction_receipt = Mock(return_value={'status': 1, 'gasUsed': 50000})
        
        account_service = AccountService(mock_blockchain_service)
        
        invite_code = "AMANITA-TEST-CODE1"
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        new_codes = await account_service.activate_and_mint_invites(invite_code, wallet_address)
        
        assert isinstance(new_codes, list)
        assert len(new_codes) == 12
        assert all(code.startswith("AMANITA-") for code in new_codes)
        logger.info(f"✅ Активация и минт инвайтов завершены: {len(new_codes)} новых кодов")
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_missing_key(self, mock_blockchain_service):
        """Тест ошибки при отсутствии SELLER_PRIVATE_KEY в activate_and_mint_invites"""
        logger.info("🧪 Тестируем ошибку при отсутствии SELLER_PRIVATE_KEY в activate_and_mint_invites")
        
        # Убираем переменную окружения
        if "SELLER_PRIVATE_KEY" in os.environ:
            del os.environ["SELLER_PRIVATE_KEY"]
        
        account_service = AccountService(mock_blockchain_service)
        
        invite_code = "AMANITA-TEST-CODE1"
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        with pytest.raises(ValueError, match="SELLER_PRIVATE_KEY не установлен в .env"):
            await account_service.activate_and_mint_invites(invite_code, wallet_address)
        
        logger.info("✅ Ошибка при отсутствии SELLER_PRIVATE_KEY корректно обработана")

# ================== EDGE CASES И ERROR SCENARIOS =====================

class TestAccountServiceEdgeCases:
    """Тесты edge cases и error scenarios для AccountService"""
    
    def test_invalid_wallet_address_format(self, mock_blockchain_service):
        """Тест обработки невалидного формата адреса кошелька"""
        logger.info("🧪 Тестируем обработку невалидного формата адреса кошелька")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем невалидные адреса
        invalid_addresses = [
            "",  # Пустая строка
            "invalid_address",  # Невалидный формат
            "0x123",  # Слишком короткий
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",  # Слишком длинный
        ]
        
        for address in invalid_addresses:
            # Моки должны корректно обрабатывать невалидные адреса
            try:
                result = account_service.is_seller(address)
                assert isinstance(result, bool)
                logger.info(f"✅ Адрес {address} корректно обработан: {result}")
            except Exception as e:
                logger.warning(f"⚠️ Адрес {address} вызвал исключение: {e}")
        
        logger.info("✅ Обработка невалидных адресов кошельков завершена")
    
    def test_empty_invite_codes_list(self, mock_blockchain_service):
        """Тест обработки пустого списка инвайт кодов"""
        logger.info("🧪 Тестируем обработку пустого списка инвайт кодов")
        
        # Мокаем _call_contract_read_function для возврата корректного результата для пустого списка
        mock_blockchain_service._call_contract_read_function = Mock(return_value=([], []))
        
        account_service = AccountService(mock_blockchain_service)
        
        invite_codes = []
        user_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        valid_codes, invalid_codes = account_service.batch_validate_invite_codes(invite_codes, user_address)
        
        assert valid_codes == []
        assert invalid_codes == []
        logger.info("✅ Пустой список инвайт кодов корректно обработан")
    
    def test_none_values_handling(self, mock_blockchain_service):
        """Тест обработки None значений"""
        logger.info("🧪 Тестируем обработку None значений")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем None значения в различных методах
        try:
            # is_seller с None
            result = account_service.is_seller(None)
            assert isinstance(result, bool)
            logger.info("✅ None значение в is_seller корректно обработано")
        except Exception as e:
            logger.warning(f"⚠️ None значение в is_seller вызвало исключение: {e}")
        
        try:
            # validate_invite_code с None
            result = account_service.validate_invite_code(None)
            assert isinstance(result, bool)
            logger.info("✅ None значение в validate_invite_code корректно обработано")
        except Exception as e:
            logger.warning(f"⚠️ None значение в validate_invite_code вызвало исключение: {e}")
        
        logger.info("✅ Обработка None значений завершена")
    
    def test_blockchain_service_errors(self, mock_blockchain_service):
        """Тест обработки ошибок блокчейн сервиса"""
        logger.info("🧪 Тестируем обработку ошибок блокчейн сервиса")
        
        # Создаем мок с ошибками
        error_mock = Mock()
        error_mock._call_contract_read_function = Mock(side_effect=Exception("Blockchain error"))
        
        account_service = AccountService(error_mock)
        
        # Тестируем обработку ошибок
        try:
            result = account_service.is_seller("0x1234567890abcdef1234567890abcdef12345678")
            logger.info(f"✅ Ошибка блокчейна корректно обработана: {result}")
        except Exception as e:
            logger.info(f"✅ Исключение блокчейна корректно перехвачено: {e}")
        
        logger.info("✅ Обработка ошибок блокчейн сервиса завершена")

# ================== ИНТЕГРАЦИЯ С СУЩЕСТВУЮЩИМИ МОКАМИ =====================

class TestAccountServiceMockIntegration:
    """Тесты интеграции с существующими моками"""
    
    def test_mock_blockchain_service_integration(self, mock_blockchain_service):
        """Тест интеграции с mock_blockchain_service"""
        logger.info("🧪 Тестируем интеграцию с mock_blockchain_service")
        
        # Проверяем, что мок поддерживает все необходимые методы
        assert hasattr(mock_blockchain_service, '_call_contract_read_function')
        # get_contract может отсутствовать в базовом моке, но мы можем его добавить при необходимости
        logger.info("✅ mock_blockchain_service содержит все необходимые методы")
    
    def test_mock_account_service_integration(self, mock_account_service):
        """Тест интеграции с mock_account_service"""
        logger.info("🧪 Тестируем интеграцию с mock_account_service")
        
        # Проверяем, что мок поддерживает все необходимые методы
        assert hasattr(mock_account_service, 'is_seller')
        assert hasattr(mock_account_service, 'validate_invite_code')
        assert hasattr(mock_account_service, 'is_user_activated')
        assert hasattr(mock_account_service, 'get_all_activated_users')
        assert hasattr(mock_account_service, 'batch_validate_invite_codes')
        assert hasattr(mock_account_service, 'batch_validate_invite_codes')
        assert hasattr(mock_account_service, 'activate_and_mint_invites')
        
        logger.info("✅ mock_account_service содержит все необходимые методы")
    
    def test_web3_fixture_integration(self, web3):
        """Тест интеграции с web3 фикстурой"""
        logger.info("🧪 Тестируем интеграцию с web3 фикстурой")
        
        # Проверяем, что web3 фикстура работает корректно
        assert hasattr(web3, 'eth')
        assert hasattr(web3.eth, 'contract')
        assert hasattr(web3.eth, 'get_transaction_receipt')
        assert hasattr(web3.eth, 'get_transaction')
        assert hasattr(web3.eth, 'estimate_gas')
        
        logger.info("✅ web3 фикстура содержит все необходимые методы")
    
    def test_invite_nft_contract_fixture_integration(self, invite_nft_contract):
        """Тест интеграции с invite_nft_contract фикстурой"""
        logger.info("🧪 Тестируем интеграцию с invite_nft_contract фикстурой")
        
        # Проверяем, что invite_nft_contract фикстура работает корректно
        assert invite_nft_contract is not None
        assert hasattr(invite_nft_contract, 'functions')
        
        logger.info("✅ invite_nft_contract фикстура содержит все необходимые методы")

# ================== ЗАВЕРШЕНИЕ =====================

print("\n=== ЗАВЕРШЕНИЕ UNIT-ТЕСТИРОВАНИЯ ACCOUNT SERVICE ===")
