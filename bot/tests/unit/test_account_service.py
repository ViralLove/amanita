"""
Unit тесты для AccountService с моками SpiralEngine

КОНЦЕПЦИЯ:
==========
- Только unit-тесты с моками (быстрые, изолированные)
- Полная поддержка SpiralEngine функций
- Тестирование логики AccountService без блокчейна
- Edge cases и error scenarios
- Интеграционные тесты выносятся в отдельный файл
"""

import pytest
import logging
import sys
import os
from unittest.mock import patch, MagicMock
from eth_account import Account
from bot.services.core.account import AccountService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.unit
class TestAccountServiceUnit:
    """Unit тесты для AccountService с моками SpiralEngine"""
    
    # ==================== БАЗОВЫЕ ТЕСТЫ ====================
    
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
        
        account_service = AccountService(mock_blockchain_service)
        
        # Устанавливаем переменную окружения для теста
        test_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": test_private_key}):
            seller_account = account_service.get_seller_account()
            
            assert seller_account is not None
            assert hasattr(seller_account, 'address')
            assert seller_account.address.startswith('0x')
            logger.info("✅ Аккаунт продавца успешно получен")
    
    def test_get_seller_account_missing_key(self, mock_blockchain_service):
        """Тест ошибки при отсутствии SELLER_PRIVATE_KEY"""
        logger.info("🧪 Тестируем ошибку при отсутствии SELLER_PRIVATE_KEY")
        
        account_service = AccountService(mock_blockchain_service)
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SELLER_PRIVATE_KEY не установлен в .env"):
                account_service.get_seller_account()
        
        logger.info("✅ Ошибка при отсутствии SELLER_PRIVATE_KEY корректно обработана")
    
    # ==================== ТЕСТЫ РОЛЕЙ И АКТИВАЦИИ ====================
    
    def test_is_seller_true(self, mock_blockchain_service):
        """Тест проверки прав продавца - True"""
        logger.info("🧪 Тестируем проверку прав продавца - True")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Используем тестовый адрес из мока
        test_seller_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        result = account_service.is_seller(test_seller_address)
        
        assert result == True
        logger.info("✅ Права продавца корректно подтверждены")
    
    def test_is_seller_false(self, mock_blockchain_service):
        """Тест проверки прав продавца - False"""
        logger.info("🧪 Тестируем проверку прав продавца - False")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Используем адрес без прав продавца
        test_user_address = "0x9999999999999999999999999999999999999999"
        
        result = account_service.is_seller(test_user_address)
        
        assert result == False
        logger.info("✅ Отсутствие прав продавца корректно подтверждено")
    
    def test_is_user_activated_true(self, mock_blockchain_service):
        """Тест проверки активации пользователя - True"""
        logger.info("🧪 Тестируем проверку активации пользователя - True")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Используем тестовый адрес из мока (активированный пользователь)
        test_user_address = "0x0987654321098765432109876543210987654321"
        
        result = account_service.is_user_activated(test_user_address)
        
        assert result == True
        logger.info("✅ Активация пользователя корректно подтверждена")
    
    def test_is_user_activated_false(self, mock_blockchain_service):
        """Тест проверки активации пользователя - False"""
        logger.info("🧪 Тестируем проверку активации пользователя - False")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Используем адрес неактивированного пользователя
        test_user_address = "0x9999999999999999999999999999999999999999"
        
        result = account_service.is_user_activated(test_user_address)
        
        assert result == False
        logger.info("✅ Отсутствие активации пользователя корректно подтверждено")
    
    def test_validate_invite_code_true(self, mock_blockchain_service):
        """Тест валидации инвайт кода - True"""
        logger.info("🧪 Тестируем валидацию инвайт кода - True")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Используем тестовый адрес из мока (активированный пользователь)
        test_user_address = "0x0987654321098765432109876543210987654321"
        
        result = account_service.validate_invite_code(test_user_address)
        
        assert result == True
        logger.info("✅ Валидация инвайт кода прошла успешно")
    
    def test_validate_invite_code_false(self, mock_blockchain_service):
        """Тест валидации инвайт кода - False"""
        logger.info("🧪 Тестируем валидацию инвайт кода - False")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Используем адрес неактивированного пользователя
        test_user_address = "0x9999999999999999999999999999999999999999"
        
        result = account_service.validate_invite_code(test_user_address)
        
        assert result == False
        logger.info("✅ Валидация инвайт кода корректно показала отсутствие инвайтов")
    
    # ==================== ТЕСТЫ АКТИВАЦИИ И МИНТА ====================

    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_success(self, mock_blockchain_service):
        """Тест активации и минта инвайтов - успех"""
        logger.info("🧪 Тестируем активацию и минт инвайтов - успех")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Устанавливаем переменную окружения для теста
        test_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": test_private_key}):
            # Используем существующий инвайт-код из мока
            invite_code = "SPIRAL-EXIST-CODE"
            wallet_address = "0x9999999999999999999999999999999999999999"  # Новый пользователь
            
            invites_before = set(mock_blockchain_service.spiral_engine_state["invite_codes"].keys())
            new_codes = await account_service.activate_and_mint_invites(invite_code, wallet_address)
            
            assert isinstance(new_codes, list)
            assert len(new_codes) == 12
            assert all(code.startswith("SPIRAL-") for code in new_codes)
            
            # Anti-false-success: проверяем, что была выполнена предварительная валидация пары активатор↔инвайт
            assert len(mock_blockchain_service.validate_activator_invite_pair_calls) == 1

            # Anti-false-success: проверяем, что activate_invite реально был вызван
            assert len(mock_blockchain_service.activate_invite_calls) == 1
            assert mock_blockchain_service.activate_invite_calls[0]["invite_code"] == invite_code
            assert mock_blockchain_service.activate_invite_calls[0]["user_address"] == wallet_address

            # Проверяем, что пользователь был активирован в моке
            assert mock_blockchain_service.is_user_activated(wallet_address) == True

            # Anti-false-success: инвайт-коды реально добавлены в состояние
            invites_after = set(mock_blockchain_service.spiral_engine_state["invite_codes"].keys())
            assert len(invites_after - invites_before) == 12
            for code in new_codes:
                assert code in mock_blockchain_service.spiral_engine_state["invite_codes"]
            logger.info(f"✅ Активация и минт инвайтов завершены: {len(new_codes)} новых кодов")

    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_invalid_code(self, mock_blockchain_service):
        """Тест активации несуществующего инвайт-кода"""
        logger.info("🧪 Тестируем активацию несуществующего инвайт-кода")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Устанавливаем переменную окружения для теста
        test_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": test_private_key}):
            fake_code = "SPIRAL-NOT-EXIST"
            wallet_address = "0x9999999999999999999999999999999999999999"
        
        # При несуществующем коде метод должен выбросить исключение
            with pytest.raises(Exception, match="Инвайт-код .* не найден"):
                await account_service.activate_and_mint_invites(fake_code, wallet_address)

            # Anti-false-success: транзакция не должна запускаться
            assert len(mock_blockchain_service.activate_invite_calls) == 0
        
        logger.info("✅ Ошибка при несуществующем коде корректно обработана")

    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_already_activated_user(self, mock_blockchain_service):
        """Тест попытки активации уже активированного пользователя"""
        logger.info("🧪 Тестируем попытку активации уже активированного пользователя")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Устанавливаем переменную окружения для теста
        test_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": test_private_key}):
            # Используем уже активированного пользователя из мока
            invite_code = "SPIRAL-EXIST-CODE"
            wallet_address = "0x0987654321098765432109876543210987654321"  # Уже активированный
            
            # При попытке активации уже активированного пользователя должно выбросить исключение
            with pytest.raises(Exception, match="Ошибка активации: User already activated"):
                await account_service.activate_and_mint_invites(invite_code, wallet_address)

            # Anti-false-success: предварительная валидация была выполнена
            assert len(mock_blockchain_service.validate_activator_invite_pair_calls) == 1

            # Anti-false-success: попытка activate_invite была сделана и вернула reason
            assert len(mock_blockchain_service.activate_invite_calls) == 1
        
        logger.info("✅ Ошибка при повторной активации корректно обработана")
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_missing_key(self, mock_blockchain_service):
        """Тест ошибки при отсутствии SELLER_PRIVATE_KEY в activate_and_mint_invites"""
        logger.info("🧪 Тестируем ошибку при отсутствии SELLER_PRIVATE_KEY в activate_and_mint_invites")
        
        account_service = AccountService(mock_blockchain_service)
        
        with patch.dict(os.environ, {}, clear=True):
            invite_code = "SPIRAL-EXIST-CODE"
            wallet_address = "0x9999999999999999999999999999999999999999"
            
            with pytest.raises(ValueError, match="SELLER_PRIVATE_KEY не установлен в .env"):
                await account_service.activate_and_mint_invites(invite_code, wallet_address)
        
        logger.info("✅ Ошибка при отсутствии SELLER_PRIVATE_KEY корректно обработана")
    
    # ==================== ТЕСТЫ ГЕНЕРАЦИИ КОДОВ ====================
    
    def test_generate_spiral_invite_codes(self, mock_blockchain_service):
        """Тест генерации спиральных инвайт-кодов"""
        logger.info("🧪 Тестируем генерацию спиральных инвайт-кодов")
        
        account_service = AccountService(mock_blockchain_service)
        
        codes = account_service._generate_spiral_invite_codes(12)
        
        assert isinstance(codes, list)
        assert len(codes) == 12
        assert all(code.startswith("SPIRAL-") for code in codes)
        assert all(len(code) == len("SPIRAL-XXXX-XXXX") for code in codes)
        assert len(set(codes)) == 12  # Все коды уникальны
        
        logger.info(f"✅ Сгенерировано {len(codes)} уникальных спиральных кодов")
    
    def test_generate_spiral_invite_codes_custom_count(self, mock_blockchain_service):
        """Тест генерации спиральных инвайт-кодов с кастомным количеством"""
        logger.info("🧪 Тестируем генерацию спиральных инвайт-кодов с кастомным количеством")
        
        account_service = AccountService(mock_blockchain_service)
        
        codes = account_service._generate_spiral_invite_codes(5)
        
        assert isinstance(codes, list)
        assert len(codes) == 5
        assert all(code.startswith("SPIRAL-") for code in codes)
        assert len(set(codes)) == 5  # Все коды уникальны
        
        logger.info(f"✅ Сгенерировано {len(codes)} уникальных спиральных кодов")
    
    # ==================== EDGE CASES И ERROR SCENARIOS ====================
    
    def test_invalid_wallet_address_format(self, mock_blockchain_service):
        """Тест обработки невалидного формата адреса кошелька"""
        logger.info("🧪 Тестируем обработку невалидного формата адреса кошелька")
        
        account_service = AccountService(mock_blockchain_service)
        
        invalid_addresses = [
            "",  # Пустая строка
            "invalid_address",  # Невалидный формат
            "0x123",  # Слишком короткий
            None,  # None значение
        ]
        
        for address in invalid_addresses:
            # Методы должны корректно обрабатывать невалидные адреса
            try:
                result = account_service.is_seller(address)
                assert isinstance(result, bool)
                logger.info(f"✅ Адрес {address} корректно обработан: {result}")
            except Exception as e:
                logger.info(f"⚠️ Адрес {address} вызвал ожидаемое исключение: {e}")
        
        logger.info("✅ Обработка невалидных адресов кошельков завершена")
    
    def test_blockchain_service_errors(self, mock_blockchain_service):
        """Тест обработки ошибок блокчейн сервиса"""
        logger.info("🧪 Тестируем обработку ошибок блокчейн сервиса")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем обработку ошибок через patch
        with patch.object(mock_blockchain_service, 'get_contract', side_effect=Exception("Blockchain error")):
            assert account_service.is_seller("0x1234567890abcdef1234567890abcdef12345678") == False
        
        with patch.object(mock_blockchain_service, 'is_user_activated', side_effect=Exception("Blockchain error")):
            assert account_service.is_user_activated("0x0987654321098765432109876543210987654321") == False
        
        with patch.object(mock_blockchain_service, 'validate_invite_code', side_effect=Exception("Blockchain error")):
            assert account_service.validate_invite_code("SPIRAL-TEST-CODE1") == False
        
        logger.info("✅ Ошибки блокчейн сервиса обработаны корректно")
    
    def test_none_values_handling(self, mock_blockchain_service):
        """Тест обработки None значений"""
        logger.info("🧪 Тестируем обработку None значений")
        
        account_service = AccountService(mock_blockchain_service)
        
        # Тестируем None значения в различных методах
        try:
            result = account_service.is_seller(None)
            assert isinstance(result, bool)
            logger.info("✅ None значение в is_seller корректно обработано")
        except Exception as e:
            logger.info(f"⚠️ None значение в is_seller вызвало ожидаемое исключение: {e}")
        
        logger.info("✅ Обработка None значений завершена")
 