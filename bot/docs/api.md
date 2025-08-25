# AMANITA API - Техническая документация

## Обзор архитектуры

AMANITA API представляет собой REST API сервис, построенный на FastAPI, предназначенный для интеграции e-commerce платформ с блокчейн экосистемой AMANITA. API обеспечивает безопасный интерфейс для управления товарами, API ключами, медиафайлами и описаниями продуктов.

### Технический стек
- **Framework**: FastAPI 0.104.1+
- **Аутентификация**: HMAC-SHA256
- **Логирование**: Структурированное JSON + консольное
- **Документация**: OpenAPI/Swagger
- **Безопасность**: CORS, Trusted Host, HMAC middleware
- **Мониторинг**: Health check эндпоинты

## Архитектурные компоненты

### 1. Основное приложение (`main.py`)

```python
def create_api_app(service_factory=None, log_level: str = "INFO", log_file: Optional[str] = None) -> FastAPI:
```

**Функциональность:**
- Инициализация FastAPI приложения с базовой конфигурацией
- Интеграция ServiceFactory для доступа к бизнес-логике
- Настройка middleware (CORS, Trusted Host, HMAC)
- Регистрация глобальных обработчиков ошибок
- Подключение роутеров для различных доменов

**Ключевые особенности:**
- Асинхронная архитектура
- Dependency injection для сервисов
- Централизованная обработка ошибок
- Структурированное логирование

### 2. Конфигурация (`config.py`)

**Основные параметры:**
```python
class APIConfig:
    API_TITLE = "AMANITA API"
    API_VERSION = "1.0.0"
    ENVIRONMENT = os.environ.get("AMANITA_API_ENVIRONMENT", "development")
    HOST = os.environ.get("AMANITA_API_HOST", "0.0.0.0")
    PORT = int(os.environ.get("AMANITA_API_PORT", "8000"))
```

**Безопасность:**
- HMAC_SECRET_KEY для подписи запросов
- TIMESTAMP_WINDOW (300 сек) для защиты от replay атак
- NONCE_CACHE_TTL (600 сек) для кэширования использованных nonce

### 3. Аутентификация и безопасность

#### HMAC Middleware (`middleware/auth.py`)

**Алгоритм аутентификации:**
1. **Извлечение заголовков**: `X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature`
2. **Валидация timestamp**: Проверка актуальности (в пределах окна)
3. **Проверка nonce**: Уникальность для предотвращения replay атак
4. **Валидация API ключа**: Проверка через ApiKeyService
5. **Проверка подписи**: HMAC-SHA256 валидация

**Формат подписи:**
```python
def _create_signature_message(self, method: str, path: str, body: str, timestamp: str, nonce: str) -> str:
    return f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
```

**Защищенные пути:**
- `/api-keys/*` (кроме создания)
- `/products/*`
- `/media/*`
- `/description/*`
- `/auth-test`

#### API ключи

**Форматы ключей:**
- `ak_` + 16 символов (формат Amanita)
- `sk_` + 64 hex символа (секретный ключ)
- 64 hex символа (традиционный формат)

**Жизненный цикл:**
1. Создание через `/api-keys/`
2. Валидация через `/api-keys/validate/{api_key}`
3. Отзыв через `DELETE /api-keys/{api_key}`

## Доменные эндпоинты

### 1. API Keys (`routes/api_keys.py`)

#### Создание API ключа
```http
POST /api-keys/
Content-Type: application/json

{
  "client_address": "0x1234567890123456789012345678901234567890",
  "description": "Описание ключа"
}
```

**Ответ:**
```json
{
  "success": true,
  "api_key": "ak_22bc74537e53698e",
  "secret_key": "sk_9160864a1ba617780cce32258248c21d085d8ddb18d3250ff4532925102d1b68",
  "request_id": "req_1234567890",
  "timestamp": 1705311045
}
```

#### Получение ключей клиента
```http
GET /api-keys/{client_address}
```

#### Отзыв ключа
```http
DELETE /api-keys/{api_key}
```

### 2. Products (`routes/products.py`)

#### Загрузка продуктов
```http
POST /products/upload
Content-Type: application/json

{
  "products": [
    {
      "id": "12345",
      "title": "Название продукта",
      "description": {
        "short": "Краткое описание",
        "full": "Полное описание"
      },
      "description_cid": "QmHash123...",
      "cover_image": "QmImageHash...",
      "gallery": ["QmGallery1...", "QmGallery2..."],
      "categories": ["category1", "category2"],
      "form": "powder",
      "species": "amanita_muscaria",
      "prices": [
        {
          "currency": "ETH",
          "amount": "0.01",
          "unit": "gram"
        }
      ],
      "attributes": {
        "sku": "SKU123",
        "stock": 100,
        "tags": ["organic", "premium"]
      }
    }
  ]
}
```

**Ответ:**
```json
{
  "results": [
    {
      "id": "12345",
      "blockchain_id": "0x1234567890abcdef",
      "tx_hash": "0xabcdef1234567890...",
      "metadata_cid": "QmMetadataHash...",
      "status": "success",
      "error": null
    }
  ]
}
```

#### Обновление продукта
```http
PUT /products/{product_id}
Content-Type: application/json

{
  "id": "12345",
  "title": "Обновленное название",
  // ... остальные поля как в загрузке
}
```

#### Обновление статуса
```http
POST /products/{product_id}/status
Content-Type: application/json

{
  "status": "active"  // или "inactive"
}
```

### 3. Media (`routes/media.py`)

#### Загрузка медиафайлов
```http
POST /media/upload
Content-Type: multipart/form-data

file: [бинарные данные файла]
```

**Ограничения:**
- Поддерживаемые форматы: JPEG, PNG, WebP
- Максимальный размер: 10 МБ
- Автоматическая загрузка в IPFS/Arweave

**Ответ:**
```json
{
  "cid": "QmMediaHash...",
  "filename": "image.jpg",
  "status": "success"
}
```

### 4. Description (`routes/description.py`)

#### Загрузка описаний
```http
POST /description/upload
Content-Type: application/json

{
  "title": "Описание продукта",
  "content": "Детальное описание...",
  "metadata": {
    "language": "ru",
    "version": "1.0"
  }
}
```

**Ограничения:**
- Максимальный размер JSON: 128 КБ
- Автоматическая загрузка в IPFS/Arweave

## Модели данных

### Базовые типы (`models/common.py`)

```python
class EthereumAddress(str):
    """Валидация Ethereum адресов"""
    
class ApiKey(str):
    """Валидация API ключей"""
    
class Timestamp(int):
    """Unix timestamp"""
    
class RequestId(str):
    """Уникальный ID запроса"""
```

### Модели аутентификации (`models/auth.py`)

```python
class AuthRequest(BaseModel):
    api_key: ApiKey
    nonce: Nonce
    timestamp: Timestamp
    signature: Signature
    request_id: Optional[RequestId]

class ApiKeyCreateRequest(BaseModel):
    client_address: EthereumAddress
    description: Optional[str]
```

### Модели продуктов (`routes/products.py`)

```python
class ProductUploadIn(BaseModel):
    id: str | int
    title: str
    description: Dict[str, Any]
    description_cid: str
    cover_image: str
    gallery: List[str]
    categories: List[str]
    form: str
    species: str
    prices: List[Dict[str, Any]]
    attributes: Dict[str, Any]
```

## Обработка ошибок

### Глобальные обработчики (`error_handlers.py`)

**Типы ошибок:**
1. **ValidationError**: Ошибки валидации Pydantic
2. **HTTPException**: HTTP ошибки
3. **AuthenticationError**: Ошибки аутентификации
4. **UnhandledException**: Необработанные исключения

**Формат ответа об ошибке:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Ошибка валидации данных",
  "details": [
    {
      "field": "client_address",
      "message": "Invalid Ethereum address format"
    }
  ],
  "timestamp": 1705311045,
  "request_id": "req_1234567890"
}
```

## Мониторинг и диагностика

### Health Check эндпоинты

#### Базовый health check
```http
GET /health
```

**Ответ:**
```json
{
  "success": true,
  "status": {
    "status": "healthy",
    "message": "Service is running normally"
  },
  "service": {
    "name": "amanita_api",
    "version": "1.0.0",
    "environment": "development"
  },
  "timestamp": 1705311045,
  "request_id": "req_1234567890",
  "uptime": {
    "seconds": 3600,
    "formatted": "1:00:00"
  }
}
```

#### Детальный health check
```http
GET /health/detailed
```

**Дополнительные компоненты:**
- API компонент
- ServiceFactory компонент
- Blockchain компонент
- Database компонент
- External APIs компонент
- Системные метрики (CPU, память, диск)

### Логирование

**Структура логов:**
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "amanita_api",
  "message": "Запрос к корневому эндпоинту",
  "module": "main",
  "function": "root",
  "line": 120,
  "endpoint": "/",
  "client_address": "0x1234...",
  "request_id": "req_1234567890"
}
```

**Конфигурация:**
- Ротация логов (10 МБ, 5 файлов)
- Двойной вывод (консоль + файл)
- Структурированный JSON формат

## Интеграция с сервисами

### ServiceFactory интеграция

```python
def get_service_factory() -> ServiceFactory:
    return ServiceFactory()

def get_api_key_service(service_factory: ServiceFactory = Depends(get_service_factory)) -> ApiKeyService:
    return service_factory.create_api_key_service()

def get_product_registry_service(service_factory: ServiceFactory = Depends(get_service_factory)) -> ProductRegistryService:
    return service_factory.create_product_registry_service()
```

### Блокчейн интеграция

**Поддерживаемые контракты:**
- AmanitaRegistry: `0x5FbDB2315678afecb367f032d93F642f64180aa3`
- InviteNFT: `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`
- ProductRegistry: `0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9`

## Развертывание и конфигурация

### Переменные окружения

```bash
# Основные настройки
AMANITA_API_ENVIRONMENT=production
AMANITA_API_HOST=0.0.0.0
AMANITA_API_PORT=8000

# Логирование
AMANITA_API_LOG_LEVEL=INFO
AMANITA_API_LOG_FILE=logs/amanita_api.log
AMANITA_API_LOG_MAX_SIZE=10485760
AMANITA_API_LOG_BACKUP_COUNT=5

# Безопасность - HMAC аутентификация
AMANITA_API_KEY=ak_seller_node_amanita_launch_september_2025  # API ключ для аутентификации
AMANITA_API_SECRET=sk_seller_secret_amanita_mvp_2024_secure_key  # Секретный ключ для HMAC подписи
AMANITA_API_HMAC_TIMESTAMP_WINDOW=300  # Окно валидации timestamp (5 минут)
AMANITA_API_HMAC_NONCE_CACHE_TTL=600   # TTL для nonce кэша (10 минут)
AMANITA_API_TRUSTED_HOSTS=your-domain.com

# CORS
AMANITA_API_CORS_ORIGINS=https://your-frontend.com
AMANITA_API_CORS_ALLOW_CREDENTIALS=true

# Примечание: AMANITA_API_HMAC_SECRET_KEY не используется в текущей реализации
# HMAC подписи создаются с использованием AMANITA_API_SECRET
```

### Запуск в production

```bash
# С использованием uvicorn
uvicorn bot.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# С использованием gunicorn
gunicorn bot.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Тестирование

### Структура тестов

```
tests/api/
├── test_api_auth.py      # Тесты аутентификации
├── test_data.py          # Тестовые данные
├── test_error_handlers.py # Тесты обработки ошибок
├── test_models.py        # Тесты моделей данных
└── conftest.py           # Конфигурация pytest
```

### Запуск тестов

```bash
# Все тесты API
python -m pytest tests/api/ -v

# Конкретный тест
python -m pytest tests/api/test_api_auth.py::test_hmac_authentication -v

# С покрытием
python -m pytest tests/api/ --cov=bot.api --cov-report=html
```

## Производительность и масштабирование

### Оптимизации

1. **Асинхронная обработка**: Все эндпоинты асинхронные
2. **Кэширование nonce**: In-memory кэш (в production - Redis)
3. **Буферизация логов**: Асинхронная запись
4. **Connection pooling**: Для базы данных и внешних API

### Мониторинг производительности

```python
# Время обработки запроса
start_time = time.time()
response = await call_next(request)
processing_time = time.time() - start_time

# Метрики в логах
logger.info("Request processed", extra={
    "processing_time": processing_time,
    "endpoint": request.url.path,
    "method": request.method
})
```

## Безопасность

### Защитные механизмы

1. **HMAC аутентификация**: Для всех защищенных эндпоинтов
2. **Timestamp validation**: Защита от replay атак
3. **Nonce uniqueness**: Дополнительная защита от replay
4. **CORS**: Контроль доступа для веб-клиентов
5. **Trusted Host**: Валидация заголовка Host
6. **Input validation**: Валидация всех входных данных
7. **Rate limiting**: Ограничение частоты запросов (планируется)

### Рекомендации по безопасности

1. **Смена секретных ключей**: Регулярная ротация HMAC_SECRET_KEY
2. **HTTPS**: Обязательное использование в production
3. **API ключи**: Регулярная ротация и мониторинг использования
4. **Логирование**: Мониторинг подозрительной активности
5. **Обновления**: Регулярное обновление зависимостей

## Планы развития

### Приоритет 1 (MVP)
- [x] Базовая аутентификация HMAC
- [x] Управление API ключами
- [x] Загрузка продуктов
- [x] Health check эндпоинты
- [x] Структурированное логирование

### Приоритет 2 (Расширение)
- [ ] Интеграция с блокчейн сервисами
- [ ] Управление инвайтами
- [ ] Синхронизация заказов
- [ ] Rate limiting
- [ ] Метрики и мониторинг

### Приоритет 3 (Production)
- [ ] Redis для кэширования
- [ ] Load balancing
- [ ] Автоматическое масштабирование
- [ ] Advanced monitoring
- [ ] Disaster recovery

## Заключение

AMANITA API предоставляет надежный, безопасный и масштабируемый интерфейс для интеграции e-commerce платформ с блокчейн экосистемой. Архитектура построена с учетом современных практик разработки API и обеспечивает высокий уровень безопасности и производительности. 