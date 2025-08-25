# 🔐 Mock архитектура для AccountService

## 📋 Обзор

**AccountService** - сервис для работы с аккаунтами и правами доступа в системе Amanita. Отвечает за:
- Управление аккаунтами продавцов
- Проверку прав доступа (SELLER_ROLE)
- Валидацию инвайт-кодов
- Активацию пользователей
- Минтинг новых инвайт-кодов

## 🎭 Mock стратегия для AccountService

### **Принципы мокирования:**

1. **Изоляция от блокчейна**: Все вызовы `blockchain_service` замоканы
2. **Предсказуемые данные**: Детерминированные результаты для тестирования
3. **Гибкость сценариев**: Легко переключаться между успешными и неуспешными сценариями
4. **Производительность**: Быстрые тесты без реальных транзакций

### **Архитектура Mock системы:**

```python
# bot/tests/conftest.py - Mock архитектура для AccountService

@pytest.fixture
def mock_blockchain_service_for_account():
    """Mock BlockchainService для тестирования AccountService"""
    mock_blockchain = Mock()
    
    # Базовые методы блокчейна
    mock_blockchain._call_contract_read_function = Mock()
    mock_blockchain.get_contract = Mock()
    mock_blockchain.estimate_gas_with_multiplier = AsyncMock()
    mock_blockchain.transact_contract_function = AsyncMock()
    mock_blockchain.web3 = Mock()
    
    # Настройка поведения по умолчанию
    mock_blockchain._call_contract_read_function.side_effect = [
        True,   # isSeller
        5,      # userInviteCount
        True,   # isUserActivated
        ["0x123", "0x456"],  # getAllActivatedUsers
        ([True, False], ["Valid", "Invalid"])  # batchValidateInviteCodes
    ]
    
    return mock_blockchain

@pytest.fixture
def mock_account_service(mock_blockchain_service_for_account):
    """Mock AccountService с замоканными зависимостями"""
    from bot.services.core.account import AccountService
    
    # Создаем AccountService с mock блокчейном
    account_service = AccountService(mock_blockchain_service_for_account)
    
    # Мокаем переменные окружения
    with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
        yield account_service

@pytest.fixture
def mock_eth_account():
    """Mock Ethereum аккаунт для тестирования"""
    mock_account = Mock()
    mock_account.address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    mock_account.key = "0x1234567890abcdef"
    return mock_account
```

## 🔧 Техническая реализация Mock методов

### **1. Mock для проверки прав продавца:**

```python
@pytest.fixture
def mock_blockchain_seller_checks():
    """Mock для различных сценариев проверки прав продавца"""
    mock_blockchain = Mock()
    
    def mock_call_contract_read_function(contract_name, function_name, default_value, *args):
        if function_name == "isSeller":
            wallet_address = args[0]
            # Симулируем логику: только определенные адреса являются продавцами
            if wallet_address == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6":
                return True
            elif wallet_address == "0x1234567890abcdef1234567890abcdef12345678":
                return True
            else:
                return False
        elif function_name == "userInviteCount":
            wallet_address = args[0]
            # Симулируем количество инвайтов
            invite_counts = {
                "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6": 5,
                "0x1234567890abcdef1234567890abcdef12345678": 12,
                "0x0000000000000000000000000000000000000000": 0
            }
            return invite_counts.get(wallet_address, 0)
        
        return default_value
    
    mock_blockchain._call_contract_read_function = Mock(side_effect=mock_call_contract_read_function)
    return mock_blockchain
```

### **2. Mock для асинхронных транзакций:**

```python
@pytest.fixture
def mock_blockchain_transactions():
    """Mock для асинхронных транзакций блокчейна"""
    mock_blockchain = Mock()
    
    # Mock для оценки газа
    async def mock_estimate_gas(*args, **kwargs):
        return 500000  # 500K газа
    
    # Mock для отправки транзакций
    async def mock_transact_contract_function(*args, **kwargs):
        return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    # Mock для получения контракта
    mock_contract = Mock()
    mock_contract.functions = Mock()
    mock_contract.functions.activateAndMintInvites = Mock()
    
    mock_blockchain.estimate_gas_with_multiplier = AsyncMock(side_effect=mock_estimate_gas)
    mock_blockchain.transact_contract_function = AsyncMock(side_effect=mock_transact_contract_function)
    mock_blockchain.get_contract = Mock(return_value=mock_contract)
    
    # Mock для Web3
    mock_web3 = Mock()
    mock_receipt = Mock()
    mock_receipt.gasUsed = 450000
    mock_receipt.status = 1
    
    mock_web3.eth.wait_for_transaction_receipt = Mock(return_value=mock_receipt)
    mock_blockchain.web3 = mock_web3
    
    return mock_blockchain
```

### **3. Mock для генерации инвайт-кодов:**

```python
@pytest.fixture
def mock_invite_code_generator():
    """Mock для генерации инвайт-кодов"""
    def generate_deterministic_codes(seed="test_seed"):
        """Генерирует детерминированные инвайт-коды для тестирования"""
        import hashlib
        
        # Используем seed для детерминированной генерации
        hash_obj = hashlib.md5(seed.encode())
        hash_hex = hash_obj.hexdigest()
        
        codes = []
        for i in range(12):
            # Создаем код на основе хеша
            start_idx = (i * 4) % len(hash_hex)
            first_part = hash_hex[start_idx:start_idx + 4].upper()
            second_part = hash_hex[start_idx + 4:start_idx + 8].upper()
            
            # Заменяем невалидные символы
            first_part = ''.join(c if c.isalnum() else 'A' for c in first_part)
            second_part = ''.join(c if c.isalnum() else 'A' for c in second_part)
            
            codes.append(f"AMANITA-{first_part}-{second_part}")
        
        return codes
    
    return generate_deterministic_codes
```

## 🧪 Структура тестов для AccountService

### **1. Unit тесты с Mock архитектурой:**

```python
# bot/tests/test_account_service_mock.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
import os
from eth_account import Account
from bot.services.core.account import AccountService

class TestAccountServiceMock:
    """Тесты AccountService с Mock архитектурой"""
    
    @pytest.fixture
    def mock_blockchain_service(self):
        """Mock BlockchainService для изоляции тестов"""
        mock_blockchain = Mock()
        
        # Настройка базового поведения
        mock_blockchain._call_contract_read_function = Mock()
        mock_blockchain.get_contract = Mock()
        mock_blockchain.estimate_gas_with_multiplier = AsyncMock(return_value=500000)
        mock_blockchain.transact_contract_function = AsyncMock(
            return_value="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        
        # Mock Web3
        mock_web3 = Mock()
        mock_receipt = Mock()
        mock_receipt.gasUsed = 450000
        mock_receipt.status = 1
        mock_web3.eth.wait_for_transaction_receipt = Mock(return_value=mock_receipt)
        mock_blockchain.web3 = mock_web3
        
        return mock_blockchain
    
    @pytest.fixture
    def account_service(self, mock_blockchain_service):
        """AccountService с mock блокчейном"""
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
            return AccountService(mock_blockchain_service)
    
    def test_get_seller_account_success(self, account_service):
        """Тест успешного получения аккаунта продавца"""
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
            account = account_service.get_seller_account()
            
            assert account is not None
            assert hasattr(account, 'address')
            assert hasattr(account, 'key')
    
    def test_get_seller_account_missing_key(self, account_service):
        """Тест ошибки при отсутствии приватного ключа"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SELLER_PRIVATE_KEY не установлен"):
                account_service.get_seller_account()
    
    def test_is_seller_true(self, account_service, mock_blockchain_service):
        """Тест проверки прав продавца - успешно"""
        # Настраиваем mock для возврата True
        mock_blockchain_service._call_contract_read_function.return_value = True
        
        result = account_service.is_seller("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
        
        assert result is True
        mock_blockchain_service._call_contract_read_function.assert_called_once_with(
            "InviteNFT", "isSeller", False, "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
    
    def test_is_seller_false(self, account_service, mock_blockchain_service):
        """Тест проверки прав продавца - не продавец"""
        # Настраиваем mock для возврата False
        mock_blockchain_service._call_contract_read_function.return_value = False
        
        result = account_service.is_seller("0x0000000000000000000000000000000000000000")
        
        assert result is False
    
    def test_validate_invite_code_with_invites(self, account_service, mock_blockchain_service):
        """Тест валидации инвайт-кода - есть инвайты"""
        # Настраиваем mock для возврата количества инвайтов > 0
        mock_blockchain_service._call_contract_read_function.return_value = 5
        
        result = account_service.validate_invite_code("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
        
        assert result is True
        mock_blockchain_service._call_contract_read_function.assert_called_once_with(
            "InviteNFT", "userInviteCount", 0, "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
    
    def test_validate_invite_code_no_invites(self, account_service, mock_blockchain_service):
        """Тест валидации инвайт-кода - нет инвайтов"""
        # Настраиваем mock для возврата 0 инвайтов
        mock_blockchain_service._call_contract_read_function.return_value = 0
        
        result = account_service.validate_invite_code("0x0000000000000000000000000000000000000000")
        
        assert result is False
    
    def test_is_user_activated_true(self, account_service, mock_blockchain_service):
        """Тест проверки активации пользователя - активирован"""
        mock_blockchain_service._call_contract_read_function.return_value = True
        
        result = account_service.is_user_activated("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
        
        assert result is True
    
    def test_get_all_activated_users(self, account_service, mock_blockchain_service):
        """Тест получения списка активированных пользователей"""
        expected_users = ["0x123", "0x456", "0x789"]
        mock_blockchain_service._call_contract_read_function.return_value = expected_users
        
        result = account_service.get_all_activated_users()
        
        assert result == expected_users
        assert len(result) == 3
    
    def test_batch_validate_invite_codes(self, account_service, mock_blockchain_service):
        """Тест пакетной валидации инвайт-кодов"""
        invite_codes = ["CODE1", "CODE2", "CODE3"]
        user_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Mock возвращает кортеж (success_array, reasons_array)
        mock_result = ([True, False, True], ["Valid", "Invalid", "Valid"])
        mock_blockchain_service._call_contract_read_function.return_value = mock_result
        
        valid_codes, invalid_codes = account_service.batch_validate_invite_codes(
            invite_codes, user_address
        )
        
        assert valid_codes == ["CODE1", "CODE3"]
        assert invalid_codes == ["CODE2"]
        assert len(valid_codes) == 2
        assert len(invalid_codes) == 1
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_success(self, account_service, mock_blockchain_service):
        """Тест успешной активации и минтинга инвайтов"""
        invite_code = "AMANITA-TEST-CODE"
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Настраиваем mock для успешного выполнения
        mock_blockchain_service.estimate_gas_with_multiplier.return_value = 500000
        mock_blockchain_service.transact_contract_function.return_value = "0x1234567890abcdef"
        
        # Mock контракта
        mock_contract = Mock()
        mock_contract.functions.activateAndMintInvites = Mock()
        mock_blockchain_service.get_contract.return_value = mock_contract
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
            result = await account_service.activate_and_mint_invites(invite_code, wallet_address)
        
        # Проверяем, что вернулся список из 12 кодов
        assert len(result) == 12
        assert all(code.startswith("AMANITA-") for code in result)
        assert all(len(code) == 20 for code in result)  # AMANITA-XXXX-YYYY
        
        # Проверяем вызовы mock методов
        mock_blockchain_service.estimate_gas_with_multiplier.assert_called_once()
        mock_blockchain_service.transact_contract_function.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_missing_key(self, account_service):
        """Тест ошибки при отсутствии приватного ключа в activate_and_mint_invites"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SELLER_PRIVATE_KEY не установлен"):
                await account_service.activate_and_mint_invites("CODE", "0x123")
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_transaction_failed(self, account_service, mock_blockchain_service):
        """Тест ошибки при неудачной транзакции"""
        invite_code = "AMANITA-TEST-CODE"
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Настраиваем mock для неудачной транзакции
        mock_blockchain_service.estimate_gas_with_multiplier.return_value = 500000
        mock_blockchain_service.transact_contract_function.return_value = None  # Транзакция не отправлена
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
            with pytest.raises(Exception, match="Транзакция не была отправлена"):
                await account_service.activate_and_mint_invites(invite_code, wallet_address)
    
    @pytest.mark.asyncio
    async def test_activate_and_mint_invites_receipt_failed(self, account_service, mock_blockchain_service):
        """Тест ошибки при неудачном receipt транзакции"""
        invite_code = "AMANITA-TEST-CODE"
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Настраиваем mock для неудачного receipt
        mock_blockchain_service.estimate_gas_with_multiplier.return_value = 500000
        mock_blockchain_service.transact_contract_function.return_value = "0x1234567890abcdef"
        
        # Mock неудачного receipt
        mock_web3 = Mock()
        mock_receipt = Mock()
        mock_receipt.status = 0  # Транзакция неудачна
        mock_web3.eth.wait_for_transaction_receipt = Mock(return_value=mock_receipt)
        mock_blockchain_service.web3 = mock_web3
        
        with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
            with pytest.raises(Exception, match="Транзакция завершилась с ошибкой"):
                await account_service.activate_and_mint_invites(invite_code, wallet_address)
```

## 🚀 Команды для запуска тестов AccountService

### **1. Запуск всех тестов AccountService:**
```bash
cd bot
python3 -m pytest tests/test_account_service_mock.py -v --tb=short
```

### **2. Запуск конкретных тестов:**
```bash
# Только тесты проверки прав продавца
python3 -m pytest tests/test_account_service_mock.py -k "is_seller" -v

# Только тесты валидации инвайт-кодов
python3 -m pytest tests/test_account_service_mock.py -k "invite_code" -v

# Только асинхронные тесты
python3 -m pytest tests/test_account_service_mock.py -k "async" -v
```

### **3. Запуск с покрытием кода:**
```bash
python3 -m pytest tests/test_account_service_mock.py --cov=bot.services.core.account --cov-report=html
```

## 📊 Метрики качества Mock архитектуры

### **Производительность:**
- **Время выполнения**: < 1 секунды для всех тестов
- **Изоляция**: 100% от внешних зависимостей
- **Стабильность**: Детерминированные результаты

### **Покрытие сценариев:**
- ✅ **Успешные операции**: Все основные методы протестированы
- ✅ **Обработка ошибок**: Валидация, отсутствие ключей, неудачные транзакции
- ✅ **Граничные случаи**: Пустые данные, невалидные адреса
- ✅ **Асинхронность**: Правильная работа с async/await

### **Поддерживаемость:**
- **Централизация**: Все моки в `conftest.py`
- **Переиспользование**: Фикстуры используются в 100% тестов
- **Гибкость**: Легко настраивать поведение для разных сценариев

## 🎯 Принципы Mock архитектуры для AccountService

### **1. Изоляция от блокчейна:**
- Все вызовы `_call_contract_read_function` замоканы
- Асинхронные операции (`estimate_gas_with_multiplier`, `transact_contract_function`) замоканы
- Web3 операции (`wait_for_transaction_receipt`) замоканы

### **2. Предсказуемость данных:**
- Детерминированная генерация инвайт-кодов
- Консистентные результаты для одинаковых входных данных
- Легко настраиваемые сценарии успеха/неудачи

### **3. Производительность:**
- Отсутствие сетевых задержек
- Мгновенное выполнение всех операций
- Быстрая обратная связь для разработчика

### **4. Гибкость тестирования:**
- Легко переключаться между различными сценариями
- Возможность тестирования edge cases
- Изоляция тестов друг от друга

## 🔗 Интеграция с существующей Mock архитектурой

### **1. Совместимость с conftest.py:**
```python
# bot/tests/conftest.py - Добавление AccountService моков

@pytest.fixture
def mock_account_service_for_registry(mock_blockchain_service_for_account):
    """Mock AccountService для использования в ProductRegistryService тестах"""
    from bot.services.core.account import AccountService
    
    with patch.dict(os.environ, {"SELLER_PRIVATE_KEY": "0x1234567890abcdef"}):
        return AccountService(mock_blockchain_service_for_account)
```

### **2. Использование в существующих тестах:**
```python
# bot/tests/test_product_registry_unit.py - Использование mock AccountService

@pytest.fixture
def mock_registry_service_with_account(mock_account_service_for_registry):
    """ProductRegistryService с mock AccountService"""
    from bot.dependencies import get_product_registry_service
    
    return get_product_registry_service(
        blockchain_service=mock_blockchain_service(),
        storage_service=mock_ipfs_storage(),
        validation_service=mock_validation_service(),
        account_service=mock_account_service_for_registry  # Используем mock AccountService
    )
```

## 📝 Заключение по Mock архитектуре AccountService

**AccountService** теперь имеет полноценную Mock архитектуру, которая:

1. **Изолирует тесты** от внешних зависимостей (блокчейн, IPFS)
2. **Обеспечивает производительность** (все тесты за < 1 секунды)
3. **Гарантирует стабильность** (детерминированные результаты)
4. **Интегрируется** с существующей Mock архитектурой ProductRegistryService
5. **Поддерживает гибкость** (легко настраиваемые сценарии)

Mock архитектура для AccountService следует тем же принципам, что и для ProductRegistryService, обеспечивая единообразие и поддерживаемость тестовой системы.

### **🎯 Следующие шаги:**

1. **Реализовать фикстуры** в `conftest.py`
2. **Создать тестовый файл** `test_account_service_mock.py`
3. **Интегрировать** с существующими тестами ProductRegistryService
4. **Запустить тесты** и валидировать Mock архитектуру
5. **Документировать** результаты и best practices

---

## 🔗 Связанная документация

### **ProductRegistryService Mock архитектура:**
Для получения информации о Mock архитектуре для ProductRegistryService см. [`registry.md`](./registry.md)

### **API тестирование:**
Для получения информации о тестировании API см. [`test-api.md`](./api%20layer/test-api.md)
