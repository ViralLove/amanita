# AccountService - Документация

## Обзор

`AccountService` - это сервис для управления аккаунтами и правами доступа в системе Amanita. Отвечает за аутентификацию пользователей, проверку прав доступа и управление инвайт-системой.

## Архитектура

### Принципы проектирования
- **Единственная ответственность**: Управление аккаунтами и правами доступа
- **Зависимость от BlockchainService**: Использует синглтон BlockchainService для взаимодействия со смарт-контрактами
- **Типизация**: Все методы имеют строгую типизацию
- **Логирование**: Подробное логирование всех операций

### Зависимости
- `BlockchainService` - для взаимодействия со смарт-контрактами
- `eth_account.Account` - для работы с Ethereum аккаунтами
- `web3.Web3` - для веб3 операций

## Методы

### Основные методы

#### `get_seller_account() -> Account`
**Описание**: Получает аккаунт продавца из переменной окружения SELLER_PRIVATE_KEY.

**Возвращает**: Объект Account с адресом и возможностью подписи транзакций.

**Исключения**: 
- `ValueError` - если SELLER_PRIVATE_KEY не установлен в .env

**Пример использования**:
```python
account_service = AccountService(blockchain_service)
seller_account = account_service.get_seller_account()
print(f"Адрес продавца: {seller_account.address}")
```

#### `is_seller(wallet_address: str) -> bool`
**Описание**: Проверяет, является ли указанный адрес адресом продавца через смарт-контракт InviteNFT.

**Параметры**:
- `wallet_address` - адрес кошелька для проверки

**Возвращает**: True если адрес является продавцом, False иначе.

**Пример использования**:
```python
is_seller = account_service.is_seller("0x1234...")
if is_seller:
    print("Это продавец")
```

#### `validate_invite_code(wallet_address: str) -> bool`
**Описание**: Проверяет наличие Invite NFT у указанного адреса.

**Параметры**:
- `wallet_address` - адрес кошелька для проверки

**Возвращает**: True если адрес владеет Invite NFT, False иначе.

**Пример использования**:
```python
has_invite = await account_service.validate_invite_code("0x1234...")
if has_invite:
    print("Пользователь имеет инвайт")
```

### Методы управления пользователями

#### `is_user_activated(user_address: str) -> bool`
**Описание**: Проверяет, активирован ли пользователь в системе.

**Параметры**:
- `user_address` - адрес пользователя

**Возвращает**: True если пользователь активирован, False иначе.

#### `get_all_activated_users() -> List[str]`
**Описание**: Получает список всех активированных пользователей.

**Возвращает**: Список адресов активированных пользователей.

#### `batch_validate_invite_codes(invite_codes: List[str], user_address: str) -> Tuple[List[str], List[str]]`
**Описание**: Пакетная валидация инвайт-кодов для пользователя.

**Параметры**:
- `invite_codes` - список инвайт-кодов для проверки
- `user_address` - адрес пользователя

**Возвращает**: Кортеж (валидные_коды, невалидные_коды).

### Методы управления инвайтами

#### `activate_and_mint_invites(invite_code: str, wallet_address: str) -> List[str]`
**Описание**: Активирует инвайт и минтит новые инвайт-коды для пользователя.

**Параметры**:
- `invite_code` - код для активации
- `wallet_address` - адрес кошелька

**Возвращает**: Список новых инвайт-кодов.

**Процесс**:
1. Генерирует 12 новых кодов в формате AMANITA-XXXX-YYYY
2. Вызывает смарт-контракт для активации и минта
3. Ждет подтверждения транзакции
4. Возвращает новые коды

## Интеграция с другими сервисами

### ServiceFactory
AccountService создается через ServiceFactory:
```python
factory = ServiceFactory()
account_service = factory.create_account_service()
```

### ProductRegistryService
ProductRegistryService использует AccountService для получения аккаунта продавца:
```python
product_registry = ProductRegistryService(
    blockchain_service=blockchain_service,
    account_service=account_service
)
```

## Логирование

Все методы AccountService используют структурированное логирование с префиксом `[AccountService]`:

- `[AccountService]` - общие операции
- `[AccountService][CHECK]` - операции проверки
- `[AccountService][INVITE]` - операции с инвайтами

## Обработка ошибок

AccountService обрабатывает следующие типы ошибок:
- Ошибки подключения к блокчейну
- Ошибки смарт-контрактов
- Ошибки валидации данных
- Ошибки конфигурации (отсутствие SELLER_PRIVATE_KEY)

## Тестирование

AccountService тестируется в `bot/tests/test_account_service.py`:
- Тесты синглтона
- Тесты интеграции с ServiceFactory
- Тесты методов работы с аккаунтами
- Тесты обработки ошибок

## Стандарты

Этот документ устанавливает стандарт для документации других сервисов:
- Обзор и архитектура
- Подробное описание методов с примерами
- Интеграция с другими сервисами
- Логирование и обработка ошибок
- Тестирование 