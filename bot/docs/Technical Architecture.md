# Техническая архитектура AMANITA Bot + API

## Обзор системы

AMANITA представляет собой гибридный микросервис, объединяющий Telegram бота и REST API, интегрированный с блокчейн-сетью Polygon и децентрализованным хранилищем IPFS. Система построена на принципах микросервисной архитектуры с четким разделением ответственности между компонентами.

## Архитектурные принципы

- **Модульность**: Четкое разделение на сервисы с единой точкой входа через ServiceFactory
- **Синглтон паттерн**: Для критических сервисов (BlockchainService, ProductRegistryService)
- **Dependency Injection**: Централизованное управление зависимостями
- **Асинхронность**: Полная поддержка async/await для всех операций
- **Безопасность**: HMAC аутентификация для API, валидация на всех уровнях
- **Масштабируемость**: Поддержка множественных IPFS провайдеров через фабрики

## Структура проекта

```
bot/
├── main.py                 # Точка входа приложения
├── config.py              # Конфигурация и переменные окружения
├── dependencies.py        # Dependency providers
├── api/                   # REST API слой
│   ├── main.py           # FastAPI приложение
│   ├── config.py         # API конфигурация
│   ├── middleware/       # Middleware (HMAC auth)
│   ├── routes/           # API маршруты
│   ├── models/           # Pydantic модели
│   └── utils/            # API утилиты
├── services/             # Сервисный слой
│   ├── service_factory.py # Фабрика сервисов
│   ├── core/             # Основные сервисы
│   │   ├── blockchain.py # Блокчейн интеграция
│   │   ├── account.py    # Управление аккаунтами
│   │   ├── api_key.py    # API ключи
│   │   ├── ipfs_factory.py # IPFS фабрика
│   │   └── storage/      # IPFS провайдеры
│   ├── product/          # Сервисы продуктов
│   └── orders/           # Сервисы заказов
├── handlers/             # Telegram обработчики
├── model/                # Модели данных
├── fsm/                  # Конечные автоматы
├── keyboards/            # Telegram клавиатуры
├── templates/            # Локализация
└── utils/                # Общие утилиты
```

## Сервисный слой

### ServiceFactory

Центральный компонент для создания и управления сервисами. Реализует паттерн Factory с поддержкой синглтонов.

```python
class ServiceFactory:
    def __init__(self):
        self.blockchain = BlockchainService()  # Синглтон
    
    def create_account_service(self):
        return AccountService(self.blockchain)
    
    def create_api_key_service(self):
        return ApiKeyService(self.blockchain)
    
    def create_product_registry_service(self):
        # Создание с зависимостями
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

### BlockchainService

Синглтон для работы с блокчейном Polygon. Архитектурно организован как центральный сервис для всех блокчейн операций.

#### Инициализация и конфигурация

```python
class BlockchainService:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.web3 = self._init_web3()
            self.chain_id = self.web3.eth.chain_id
            self.registry = self._load_registry_contract()
            self.contracts = self._load_contracts()
            self._initialized = True
```

#### Подключение к Web3

```python
def _init_web3(self) -> Web3:
    """Инициализирует подключение к Web3"""
    try:
        if ACTIVE_PROFILE == "localhost":
            provider = Web3.HTTPProvider(RPC_URL)
        else:
            provider = Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60})
        
        web3 = Web3(provider)
        
        if not web3.is_connected():
            raise Exception("Failed to connect to Web3")
            
        logger.info(f"[Web3] Успешное подключение к {ACTIVE_PROFILE}")
        return web3
        
    except Exception as e:
        logger.error(f"[Web3] Ошибка подключения к {ACTIVE_PROFILE}: {e}")
        raise
```

#### Загрузка контрактов

```python
def _load_registry_contract(self) -> Any:
    """Загружает контракт реестра"""
    abi_path = os.path.join(ABI_BASE_DIR, "AmanitaRegistry.sol", "AmanitaRegistry.json")
    with open(abi_path) as f:
        abi = json.load(f)["abi"]
        
    contract = self.web3.eth.contract(
        address=AMANITA_REGISTRY_CONTRACT_ADDRESS,
        abi=abi
    )
    return contract

def _load_contracts(self) -> Dict[str, Any]:
    """Загружает все контракты из реестра"""
    contracts = {}
    contract_names = ["InviteNFT", "ProductRegistry"]
    
    for name in contract_names:
        # Получаем адрес контракта из реестра
        address = self.registry.functions.getAddress(name).call()
        
        # Загружаем ABI
        abi_path = os.path.join(ABI_BASE_DIR, f"{name}.sol", f"{name}.json")
        with open(abi_path) as f:
            abi = json.load(f)["abi"]
            
        # Создаем контракт
        contract = self.web3.eth.contract(address=address, abi=abi)
        contracts[name] = contract
    
    return contracts
```

#### Универсальные методы для работы с контрактами

```python
def call_contract_function(self, contract_name: str, function_name: str, *args, **kwargs) -> Any:
    """Публичный метод для вызова read-only функций контракта"""
    return self._call_contract_read_function(contract_name, function_name, None, *args, **kwargs)

async def transact_contract_function(self, contract_name: str, function_name: str, private_key: str, *args, **kwargs) -> Optional[str]:
    """Вызывает функцию контракта с транзакцией"""
    try:
        account = Account.from_key(private_key)
        contract = self.get_contract(contract_name)
        contract_function = getattr(contract.functions, function_name)
        
        # Оцениваем газ с множителем
        estimated_gas = await self.estimate_gas_with_multiplier(contract_function, *args)
        
        # Создаем транзакцию
        txn = contract_function(*args).build_transaction({
            'value': 0,
            'chainId': self.chain_id,
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'gas': estimated_gas,
            'gasPrice': self.web3.eth.gas_price
        })
        
        # Подписываем и отправляем транзакцию
        signed_txn = self.web3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()
        
    except Exception as e:
        logger.error(f"[Web3] Ошибка транзакции: {e}")
        return None
```

#### Специализированные методы для InviteNFT

```python
def validate_invite_code(self, invite_code: str) -> dict:
    """Валидация инвайт-кода через контракт InviteNFT"""
    result = self._call_contract_read_function("InviteNFT", "validateInviteCode", (False, "contract_not_found"), invite_code)
    success, reason = result[0], result[1]
    return {"success": success, "reason": reason}

def get_token_id_by_invite_code(self, invite_code: str) -> int:
    return self._call_contract_read_function("InviteNFT", "getTokenIdByInviteCode", None, invite_code)

def get_user_invites(self, user_address: str) -> list:
    return self._call_contract_read_function("InviteNFT", "getUserInvites", [], user_address)

def is_invite_token_used(self, token_id: int) -> bool:
    return self._call_contract_read_function("InviteNFT", "isInviteTokenUsed", False, token_id)
```

#### Специализированные методы для ProductRegistry

```python
def get_catalog_version(self) -> int:
    """Получает текущую версию каталога"""
    try:
        version = self._call_contract_read_function("ProductRegistry", "getMyCatalogVersion", 0)
        logger.info(f"Current catalog version: {version}")
        return version
    except Exception as e:
        logger.error(f"Error getting catalog version: {e}")
        return 0

def get_all_products(self) -> List[dict]:
    """Получает все продукты из блокчейна"""
    try:
        product_ids = self._call_contract_read_function("ProductRegistry", "getAllActiveProductIds", [])
        logger.info(f"Got {len(product_ids)} product IDs from blockchain")
        
        # Получаем полные данные для каждого продукта
        products = []
        for product_id in product_ids:
            product = self._call_contract_read_function("ProductRegistry", "getProduct", None, product_id)
            if product:
                products.append(product)
        
        logger.info(f"Retrieved {len(products)} full products from blockchain")
        return products
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        return []

async def create_product(self, ipfs_cid: str) -> Optional[str]:
    """Создает новый продукт в блокчейне"""
    try:
        tx_hash = await self.transact_contract_function(
            "ProductRegistry", 
            "createProduct", 
            SELLER_PRIVATE_KEY, 
            ipfs_cid
        )
        return tx_hash
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        return None
```

#### Архитектурные особенности

1. **Синглтон паттерн** - гарантирует единственный экземпляр для всего приложения
2. **Централизованное управление контрактами** - все контракты загружаются через реестр
3. **Универсальные методы** - `call_contract_function` и `transact_contract_function` для любых контрактов
4. **Специализированные методы** - высокоуровневые методы для конкретных бизнес-операций
5. **Обработка ошибок** - единообразная обработка ошибок с логированием
6. **Gas estimation** - автоматическая оценка газа с множителем для надежности

### IPFS Factory и Storage

Поддержка множественных IPFS провайдеров через фабрику:

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

#### Поддерживаемые провайдеры:

1. **Pinata**: Основной IPFS провайдер
   - Асинхронная загрузка файлов
   - Кэширование метаданных
   - Обработка ошибок и retry логика

2. **ArWeave**: Альтернативное децентрализованное хранилище
   - Перманентное хранение
   - Поддержка метаданных

## API Архитектура

### FastAPI приложение

Создание приложения с интеграцией сервисов:

```python
def create_api_app(service_factory=None, log_level: str = "INFO", log_file: Optional[str] = None) -> FastAPI:
    app = FastAPI(**fastapi_config)
    
    # CORS middleware
    app.add_middleware(CORSMiddleware, **cors_config)
    
    # Trusted Host middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=APIConfig.TRUSTED_HOSTS)
    
    # HMAC аутентификация
    api_key_service = service_factory.create_api_key_service()
    app.add_middleware(HMACMiddleware, api_key_service=api_key_service)
    
    # Сохранение service_factory в состоянии приложения
    app.state.service_factory = service_factory
    
    return app
```

### Система API ключей

#### Конфигурация ключей

Система API ключей настраивается через переменные окружения в `bot/config.py`:

```python
# API ключи для аутентификации (MVP)
AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "ak_seller_amanita_mvp_2024")
AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "sk_seller_secret_amanita_mvp_2024_secure_key")
```

HMAC настройки находятся в `bot/api/config.py`:

```python
class APIConfig:
    # Настройки HMAC аутентификации
    HMAC_SECRET_KEY = os.environ.get("AMANITA_API_HMAC_SECRET_KEY", "default-secret-key-change-in-production")
    HMAC_TIMESTAMP_WINDOW = int(os.environ.get("AMANITA_API_HMAC_TIMESTAMP_WINDOW", "300"))  # 5 минут
    HMAC_NONCE_CACHE_TTL = int(os.environ.get("AMANITA_API_HMAC_NONCE_CACHE_TTL", "600"))  # 10 минут
```

#### ApiKeyService

Сервис управления API ключами с MVP реализацией:

```python
class ApiKeyService:
    def __init__(self, blockchain_service: BlockchainService):
        self.blockchain_service = blockchain_service
        self._init_encryption()
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 минут
    
    def _init_encryption(self):
        """Инициализирует шифрование для секретных ключей"""
        encryption_key = os.getenv("AMANITA_API_ENCRYPTION_KEY")
        if not encryption_key:
            encryption_key = Fernet.generate_key()
        self.cipher = Fernet(encryption_key)
    
    async def validate_api_key(self, api_key: str) -> Dict[str, any]:
        """Валидирует API ключ (MVP - проверяет статический ключ из .env)"""
        # Проверяем кэш
        cached = self._get_from_cache(api_key)
        if cached:
            return cached
        
        # MVP: Проверяем API ключ из .env
        if api_key == AMANITA_API_KEY:
            try:
                seller_account = self.blockchain_service.seller_account
                result = {
                    "seller_address": seller_account.address,
                    "secret_key": AMANITA_API_SECRET,
                    "active": True,
                    "description": "Seller API Key from .env"
                }
                self._update_cache(api_key, result)
                return result
            except Exception as e:
                logger.error(f"Ошибка получения адреса селлера: {e}")
                raise InvalidAPIKeyError("Ошибка валидации API ключа")
        
        # TODO: В production здесь будет проверка через блокчейн
        raise InvalidAPIKeyError(f"Неверный API ключ: {api_key}")
```

#### HMAC Middleware

Безопасная аутентификация API запросов:

```python
class HMACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key_service: Optional[ApiKeyService] = None):
        super().__init__(app)
        self.api_key_service = api_key_service
        self.used_nonces: Set[str] = set()
        self.nonce_timestamps: Dict[str, float] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Проверка HMAC подписи
        # Валидация timestamp (защита от replay атак)
        # Проверка уникальности nonce
        # Валидация API ключа через ApiKeyService
```

### API Маршруты и Dependency Injection

#### Dependency Injection система

API использует FastAPI Depends для внедрения зависимостей через `bot/api/dependencies.py`:

```python
def get_product_registry_service(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    storage_service: ProductStorageService = Depends(get_product_storage_service),
    validation_service: ProductValidationService = Depends(get_product_validation_service),
) -> ProductRegistryService:
    """FastAPI dependency provider для ProductRegistryService"""
    account_service = _get_account_service(blockchain_service)
    
    return _get_product_registry_service(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
```

#### Структура маршрутов

Маршруты организованы в модули с четким разделением ответственности:

```python
# bot/api/routes/products.py
router = APIRouter(prefix="/products", tags=["products"])

@router.post("/upload", response_model=ProductsUploadResponse)
async def upload_products(
    request: ProductsUploadRequest,
    registry_service: ProductRegistryService = Depends(get_product_registry_service),
    http_request: Request = None
):
    """Загрузка продуктов из e-commerce систем"""
    results = []
    
    for product in request.products:
        try:
            product_dict = product.model_dump()
            result = await registry_service.create_product(product_dict)
            results.append(ProductUploadResult(
                id=str(result.get("id")),
                blockchain_id=result.get("blockchain_id"),
                tx_hash=result.get("tx_hash"),
                metadata_cid=result.get("metadata_cid"),
                status=result.get("status", "error"),
                error=result.get("error")
            ))
        except Exception as e:
            logger.error(f"Ошибка при обработке продукта {product.id}: {e}")
            results.append(ProductUploadResult(
                id=product.id,
                status="error",
                error=str(e)
            ))
    
    return ProductsUploadResponse(results=results)
```

#### Доступные маршруты:

- `/health` - Проверка состояния системы
- `/health/detailed` - Детальная диагностика
- `/api/products/upload` - Загрузка продуктов
- `/api/products/{product_id}` - Обновление продукта
- `/api/products/{product_id}/status` - Изменение статуса
- `/api/orders` - Управление заказами
- `/api/keys` - Управление API ключами

#### Связь с сервисами

API маршруты используют:

1. **ProductRegistryService** - для операций с продуктами (который внутри использует BlockchainService)
2. **ProductStorageService** - для IPFS операций  
3. **ApiKeyService** - для валидации ключей (только в HMAC middleware)

**Важно**: API эндпойнты работают через высокоуровневые сервисы, а не напрямую с блокчейном.

#### Пример реального взаимодействия

```python
# API маршрут вызывает ProductRegistryService
@router.post("/upload")
async def upload_products(
    request: ProductsUploadRequest,
    registry_service: ProductRegistryService = Depends(get_product_registry_service)
):
    for product in request.products:
        result = await registry_service.create_product(product.model_dump())
        # ProductRegistryService внутри вызывает BlockchainService.create_product()

# ProductRegistryService делегирует блокчейн операции
def create_product_on_chain(self, ipfs_cid: str) -> str:
    # Делегируем создание продукта BlockchainService
    tx_hash = self.blockchain_service.create_product(ipfs_cid)
    return tx_hash
```

## Telegram Bot интеграция

### Архитектура обработчиков

Модульная система обработчиков с поддержкой FSM:

```python
# Регистрация роутеров
dp.include_router(onboarding_router)
dp.include_router(catalog_router)
dp.include_router(menu_router)
dp.include_router(webapp_router)
```

### FSM (Finite State Machine)

Управление состояниями пользователя:

```python
class OnboardingStates(StatesGroup):
    LanguageSelection = State()
    OnboardingPathChoice = State()
    InviteInput = State()
    WebAppConnecting = State()
    RestoreAccess = State()
    Completed = State()
```

### Обработчики

1. **Onboarding**: Процесс регистрации пользователя
2. **Catalog**: Просмотр каталога продуктов
3. **Menu**: Основное меню бота
4. **WebApp**: Интеграция с веб-приложением кошелька

## Модели данных

### Product Model

Структурированная модель продукта с поддержкой:
- Множественных цен и валют
- Различных форм продукта
- Детальных описаний
- IPFS метаданных

```python
@dataclass
class Product:
    id: Union[int, str]
    alias: str
    status: int
    cid: str
    title: str
    description: Description
    description_cid: str
    cover_image_url: str
    categories: List[str]
    forms: List[str]
    species: str
    prices: List[PriceInfo]
```

### PriceInfo

Гибкая система ценообразования:

```python
class PriceInfo:
    SUPPORTED_CURRENCIES = {
        'EUR': '€', 'USD': '$', 'GBP': '£', 'JPY': '¥',
        'RUB': '₽', 'CNY': '¥', 'USDT': '₮', 'ETH': 'Ξ', 'BTC': '₿'
    }
    
    SUPPORTED_WEIGHT_UNITS = {'g', 'kg', 'oz', 'lb'}
    SUPPORTED_VOLUME_UNITS = {'ml', 'l', 'oz_fl'}
```

## Локализация

Многоязычная поддержка через JSON шаблоны:

```
templates/
├── en.json
├── ru.json
├── es.json
├── fr.json
└── ...
```

## Безопасность

### Аутентификация

1. **HMAC подписи**: Для API запросов
2. **API ключи**: Управление доступом
3. **Timestamp валидация**: Защита от replay атак
4. **Nonce проверка**: Дополнительная защита

### Валидация данных

- Pydantic модели для API
- Валидация на уровне сервисов
- Проверка блокчейн транзакций

## Логирование и мониторинг

### Структурированное логирование

```python
logger = setup_logging(
    log_level=APIConfig.LOG_LEVEL,
    log_file=APIConfig.LOG_FILE,
    max_size=APIConfig.LOG_MAX_SIZE,
    backup_count=APIConfig.LOG_BACKUP_COUNT
)
```

### Sentry интеграция

Автоматический сбор ошибок и производительности.

### Health Checks

Детальная диагностика состояния системы:
- Проверка блокчейн подключения
- Статус IPFS провайдеров
- Состояние сервисов
- Метрики производительности

## Конфигурация

### Переменные окружения

```bash
# Telegram
TELEGRAM_BOT_TOKEN=

# Блокчейн
BLOCKCHAIN_PROFILE=localhost
WEB3_PROVIDER_URI=http://localhost:8545
SELLER_PRIVATE_KEY=
AMANITA_REGISTRY_CONTRACT_ADDRESS=

# API ключи (MVP - статические ключи)
AMANITA_API_KEY=ak_22bc74537e53698e
AMANITA_API_SECRET=sk_9160864a1ba617780cce32258248c21d085d8ddb18d3250ff4532925102d1b68

# HMAC настройки
AMANITA_API_HMAC_SECRET_KEY=default-secret-key-change-in-production
AMANITA_API_HMAC_TIMESTAMP_WINDOW=300
AMANITA_API_HMAC_NONCE_CACHE_TTL=600

# IPFS
STORAGE_TYPE=pinata

# WebApp
WALLET_APP_URL=
```

## Развертывание

### Параллельный запуск

```python
async def main():
    # Инициализация сервисов
    service_factory = ServiceFactory()
    
    # Создание бота и API
    bot = Bot(token=API_TOKEN)
    api_app = create_api_app(service_factory=service_factory)
    
    # Параллельный запуск
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )
```

### Docker поддержка

Готовность к контейнеризации с переменными окружения.

## Тестирование

### Структура тестов

```
tests/
├── api/           # API тесты
├── unit/          # Модульные тесты
├── integration/   # Интеграционные тесты
└── fixtures/      # Тестовые данные
```

### Mock стратегия

- Mock блокчейн коннектора
- Фикстуры для тестовых данных
- Изоляция сервисов

## Масштабирование

### Горизонтальное масштабирование

- Stateless API сервисы
- Поддержка множественных экземпляров
- Redis для кэширования nonce

### Вертикальное масштабирование

- Асинхронная обработка
- Оптимизация блокчейн запросов
- Кэширование IPFS метаданных

## Мониторинг и метрики

### Ключевые метрики

1. **Производительность API**
   - Время ответа
   - Throughput
   - Ошибки

2. **Блокчейн операции**
   - Время транзакций
   - Gas usage
   - Успешность операций

3. **IPFS операции**
   - Время загрузки
   - Размер файлов
   - Доступность провайдеров

### Алерты

- Критические ошибки блокчейна
- Недоступность IPFS
- Высокая латентность API

## Заключение

AMANITA Bot + API представляет собой современную микросервисную архитектуру с четким разделением ответственности, поддержкой масштабирования и безопасности. Система готова к production развертыванию с полным набором инструментов для мониторинга и поддержки.
