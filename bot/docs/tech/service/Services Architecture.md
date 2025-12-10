# Архитектура сервисов AMANITA Bot

> **Примечание:** Данный документ расширяет [Technical Architecture.md](./Technical%20Architecture.md), предоставляя детальное описание внутренней архитектуры сервисов. Для общего понимания системы рекомендуется сначала ознакомиться с основным документом архитектуры.

## Обзор сервисной архитектуры

Архитектура сервисов AMANITA построена по принципу **Clean Architecture** с четким разделением ответственности и зависимостей. Система организована в слои, где каждый слой имеет строго определенные обязанности и может взаимодействовать только с соседними слоями.

### Архитектурные слои

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Telegram    │  │ FastAPI     │  │ WebApp              │  │
│  │ Bot         │  │ REST API    │  │ Wallet Interface    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Handlers    │  │ API Routes  │  │ FSM States          │  │
│  │ (Telegram)  │  │ (FastAPI)   │  │ (Onboarding)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Product     │  │ Account     │  │ Order               │  │
│  │ Services    │  │ Services    │  │ Services            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Blockchain  │  │ IPFS        │  │ External APIs       │  │
│  │ Gateway     │  │ Storage     │  │ (Telegram, etc.)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Детальное описание сервисов

### 🔗 **Infrastructure Layer (Инфраструктурный слой)**

#### BlockchainService - Центральный блокчейн-шлюз

**Назначение:** Единая точка входа для всех блокчейн-операций в системе AMANITA.

**Архитектурные особенности:**
- **Синглтон паттерн** - гарантирует единственный экземпляр для всего приложения
- **Централизованное управление контрактами** - все контракты загружаются через реестр
- **Универсальные методы** - `call_contract_function` и `transact_contract_function` для любых контрактов
- **Специализированные методы** - высокоуровневые методы для конкретных бизнес-операций

**Ключевые методы:**

```python
# Универсальные методы для работы с любыми контрактами
def call_contract_function(self, contract_name: str, function_name: str, *args, **kwargs) -> Any
async def transact_contract_function(self, contract_name: str, function_name: str, private_key: str, *args, **kwargs) -> Optional[str]

# Специализированные методы для SpiralEngine (invite system)
def validate_invite_code(self, invite_code: str) -> dict
def get_token_id_by_invite_code(self, invite_code: str) -> int
def get_user_invites(self, user_address: str) -> list
def is_invite_token_used(self, token_id: int) -> bool

# Специализированные методы для ProductRegistry
def get_catalog_version(self) -> int
def get_all_products(self) -> List[dict]
def get_product(self, product_id: int) -> Optional[dict]
async def create_product(self, ipfs_cid: str) -> Optional[str]
async def set_product_active(self, private_key: str, product_id: int, is_active: bool) -> Optional[str]
async def update_product_status(self, private_key: str, product_id: int, new_status: int) -> Optional[str]

# Методы для работы с транзакциями
async def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> Optional[dict]
def check_transaction_status(self, receipt: dict) -> bool
async def get_product_id_from_tx(self, tx_hash: str) -> Optional[int]
```

**Обработка ошибок:**
- Единообразная обработка ошибок с логированием
- Автоматическая оценка газа с множителем для надежности
- Retry логика для сетевых операций
- Валидация адресов и параметров

#### IPFSFactory - Абстракция хранилища

**Назначение:** Фабрика для создания IPFS клиентов с поддержкой множественных провайдеров.

**Поддерживаемые провайдеры:**
1. **Pinata** - основной IPFS провайдер
   - Асинхронная загрузка файлов
   - Кэширование метаданных
   - Обработка ошибок и retry логика

2. **ArWeave** - альтернативное децентрализованное хранилище
   - Перманентное хранение
   - Поддержка метаданных

**Архитектура:**
```python
class IPFSFactory:
    def __init__(self):
        self.set_storage(STORAGE_TYPE)
    
    def set_storage(self, storage_type: str):
        if storage_type.lower() == 'pinata':
            self.storage = SecurePinataUploader()
        elif storage_type.lower() == 'arweave':
            self.storage = ArWeaveUploader()
        else:
            raise ValueError(f"Неподдерживаемый тип хранилища: {storage_type}")
```

### 🏗️ **Domain Layer (Доменный слой)**

#### ProductRegistryService - Управление продуктами

**Назначение:** Центральный сервис для работы с реестром продуктов, координирующий все операции с продуктами.

**Архитектурные принципы:**
- **Координатор паттерн** - координирует работу всех подсервисов
- **Фасад паттерн** - предоставляет единый интерфейс для работы с продуктами
- **Кэширование** - многоуровневое кэширование для оптимизации производительности

**Зависимости:**
```python
class ProductRegistryService:
    def __init__(self, 
                 blockchain_service: BlockchainService,
                 storage_service: ProductStorageService,
                 validation_service: ProductValidationService,
                 account_service: AccountService):
        self.blockchain_service = blockchain_service
        self.storage_service = storage_service
        self.validation_service = validation_service
        self.account_service = account_service
        self.cache_service = ProductCacheService()
        self.metadata_service = ProductMetadataService(storage_service)
```

**Ключевые методы:**

```python
# Основные операции с продуктами
async def create_product(self, product_data: dict) -> dict
def get_all_products(self) -> List[Product]
def get_product(self, product_id: Union[str, int]) -> Optional[Product]
async def update_product(self, product_id: str, product_data: dict) -> dict
async def update_product_status(self, product_id: int, new_status: int) -> bool
async def deactivate_product(self, product_id: int) -> bool

# Кэширование
def clear_cache(self, cache_type: Optional[str] = None)
def get_catalog_version(self) -> int

# Метаданные
def create_product_metadata(self, product_data: dict) -> dict
def _process_product_metadata(self, product_id: Union[int, str], ipfs_cid: str, active: bool) -> Optional[Product]
```

**Стратегия кэширования:**
```python
CACHE_TTL = {
    'catalog': timedelta(minutes=5),      # Каталог продуктов
    'description': timedelta(hours=24),   # Описания продуктов
    'image': timedelta(hours=12)          # Изображения
}
```

#### AccountService - Управление аккаунтами

**Назначение:** Сервис для управления аккаунтами продавцов и покупателей в экосистеме AMANITA.

**Функциональность:**
- Получение аккаунта продавца
- Управление ключами
- Валидация прав доступа
- Работа с инвайт-кодами

**Ключевые методы:**
```python
def get_seller_account(self) -> Account
def is_seller(self, address: str) -> bool
def is_user_activated(self, address: str) -> bool
def get_all_activated_users(self) -> List[str]
def batch_validate_invite_codes(self, codes: List[str]) -> List[dict]
def activate_and_mint_invites(self, invite_code: str, user_address: str) -> dict
```

#### ApiKeyService - Управление API ключами

**Назначение:** Сервис для валидации и управления API ключами с поддержкой HMAC аутентификации.

**Архитектура:**
```python
class ApiKeyService:
    def __init__(self, blockchain_service: BlockchainService):
        self.blockchain_service = blockchain_service
        self._init_encryption()
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 минут

    async def validate_api_key(self, api_key: str) -> Dict[str, any]:
        # MVP: Проверяет статический ключ из .env
        # TODO: В production здесь будет проверка через блокчейн
```

### 🔧 **Support Services (Вспомогательные сервисы)**

#### ProductStorageService
**Назначение:** Абстракция для работы с IPFS хранилищем.
**Особенности:** Не имеет зависимостей от других сервисов, использует IPFSFactory.

#### ProductMetadataService
**Назначение:** Управление метаданными продуктов.
**Зависимости:** Только от ProductStorageService.
**Функции:** Форматирование, валидация и обработка метаданных.

#### ProductCacheService
**Назначение:** Кэширование данных для оптимизации производительности.
**Особенности:** Не имеет зависимостей, использует локальное хранилище.

#### ProductValidationService
**Назначение:** Валидация данных продуктов.
**Особенности:** Не имеет зависимостей, содержит правила валидации.

## Принципы инициализации сервисов

### ServiceFactory - Центральная фабрика сервисов

**Назначение:** Центральный компонент для создания и управления сервисами с поддержкой синглтонов.

```python
class ServiceFactory:
    def __init__(self):
        # Используем синглтон BlockchainService
        self.blockchain = BlockchainService()

    def create_account_service(self):
        return AccountService(self.blockchain)
    
    def create_api_key_service(self):
        return ApiKeyService(self.blockchain)
    
    def create_product_registry_service(self):
        # Создаем зависимости для ProductRegistryService
        storage_service = ProductStorageService()
        validation_service = ProductValidationService()
        account_service = AccountService(self.blockchain)
        
        return ProductRegistryService(
            blockchain_service=self.blockchain,
            storage_service=storage_service,
            validation_service=validation_service,
            account_service=account_service
        )
```

### Правила инициализации

1. **Базовые сервисы инициализируются первыми:**
   ```python
   blockchain_service = BlockchainService()  # Синглтон
   ipfs_factory = IPFSFactory()
   ```

2. **Создание вспомогательных сервисов:**
   ```python
   storage_service = ProductStorageService(ipfs_factory)
   validation_service = ProductValidationService()
   cache_service = ProductCacheService()
   metadata_service = ProductMetadataService(storage_service)
   ```

3. **Инициализация доменных сервисов:**
   ```python
   product_registry = ProductRegistryService(
       blockchain_service=blockchain_service,
       storage_service=storage_service,
       validation_service=validation_service,
       account_service=account_service
   )
   ```

## Архитектурные принципы и правила

### 1. **Единая ответственность (Single Responsibility Principle)**
Каждый сервис отвечает за конкретную область функциональности:
- `BlockchainService` - только блокчейн операции
- `ProductRegistryService` - только управление продуктами
- `AccountService` - только управление аккаунтами

### 2. **Инверсия зависимостей (Dependency Inversion Principle)**
Сервисы получают зависимости через конструктор:
```python
def __init__(self, blockchain_service: BlockchainService):
    self.blockchain_service = blockchain_service
```

### 3. **Отсутствие циклических зависимостей**
Сервисы организованы в направленный ациклический граф:
```
Infrastructure Layer → Domain Layer → Application Layer
```

### 4. **Изоляция слоев**
Каждый слой взаимодействует только с соседними слоями:
- Presentation Layer → Application Layer
- Application Layer → Domain Layer
- Domain Layer → Infrastructure Layer

### 5. **Кэширование и переиспользование**
- Базовые сервисы создаются один раз и переиспользуются
- Синглтон паттерн для критических сервисов
- Многоуровневое кэширование данных

### 6. **Чистота и безопасность**
- Явные зависимости через конструктор
- Отсутствие глобального состояния
- Безопасная инициализация с проверками
- Корректная обработка ошибок на всех уровнях

## Тестирование сервисов

### Стратегия тестирования

1. **Модульные тесты:** Каждый сервис тестируется изолированно с моками зависимостей
2. **Интеграционные тесты:** Проверяют взаимодействие между сервисами
3. **E2E тесты:** Проверяют полные пользовательские сценарии

### Фикстуры для тестирования

```python
@pytest.fixture
def product_registry(blockchain_service, storage_service, validation_service):
    return ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )

@pytest.fixture
def mock_blockchain_service():
    # Мок для BlockchainService
    pass

@pytest.fixture
def mock_ipfs_service():
    # Мок для IPFS операций
    pass
```

### Покрытие тестами

- **ProductRegistryService:** 100% (59 тестов)
- **AccountService:** 60%
- **BlockchainService:** 30%
- **ApiKeyService:** 80%

## Производительность и масштабирование

### Оптимизации производительности

1. **Кэширование:**
   - Каталог продуктов: 5 минут
   - Описания: 24 часа
   - Изображения: 12 часов

2. **Асинхронная обработка:**
   - Все блокчейн операции асинхронные
   - IPFS загрузки не блокируют основной поток
   - Batch операции для множественных запросов

3. **Connection Pooling:**
   - Переиспользование Web3 соединений
   - Кэширование контрактов
   - Оптимизация RPC запросов

### Мониторинг и метрики

1. **Метрики производительности:**
   - Время создания продукта
   - Время загрузки каталога
   - Эффективность кэширования

2. **Метрики надежности:**
   - Успешность транзакций
   - Доступность IPFS
   - Ошибки валидации

3. **Метрики использования:**
   - Количество созданных продуктов
   - Активность пользователей
   - Популярность категорий

## Заключение

Архитектура сервисов AMANITA построена на принципах Clean Architecture с четким разделением ответственности, что обеспечивает:

- **Масштабируемость:** Легкое добавление новых сервисов
- **Тестируемость:** Изоляция зависимостей для простого тестирования
- **Поддерживаемость:** Четкая структура и принципы
- **Производительность:** Оптимизация через кэширование и асинхронность
- **Безопасность:** Валидация на всех уровнях и безопасная обработка ошибок

Данная архитектура служит основой для дальнейшего развития системы и интеграции с внешними платформами e-commerce. 