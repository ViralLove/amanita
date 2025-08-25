# AMANITA API - Аутентификация и безопасность

## Обзор

AMANITA API представляет собой FastAPI-приложение для интеграции с e-commerce платформами (WooCommerce, Shopify, Magento) через стандартные механизмы безопасности. API использует существующую архитектуру Telegram бота и расширяет её для внешних клиентов.

## Архитектура

```
[E-commerce Client] → [FastAPI] → [ServiceFactory] → [Existing Services] → [Blockchain]
     (WooCommerce)      (API)         (DI)              (Bot Services)     (Contracts)
```

## 1. API Gateway

### 1.1 FastAPI как основа
- **FastAPI** - веб-фреймворк с автоматической документацией
- **Pydantic** - валидация данных
- **Uvicorn** - ASGI сервер
- **OpenAPI/Swagger** - автоматическая документация

### 1.2 Интеграция с существующим main.py
```python
# bot/main.py - расширенная версия
import asyncio
from aiogram import Bot, Dispatcher
from fastapi import FastAPI
import uvicorn
from bot.api.main import create_api_app
from bot.services.service_factory import ServiceFactory

async def main():
    # Инициализация сервисов (общие для бота и API)
    service_factory = ServiceFactory()
    
    # Инициализация Telegram бота (существующий код)
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    # ... регистрация хендлеров
    
    # Создание FastAPI приложения с доступом к сервисам
    api_app = create_api_app(service_factory)
    
    # Запуск API сервера в отдельной задаче
    config = uvicorn.Config(
        api_app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Запуск бота и API сервера параллельно
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

**Преимущества интеграции:**
- Единая точка входа для бота и API
- Общие сервисы и конфигурация
- Параллельная работа Telegram бота и API сервера
- Минимальные изменения существующего кода

### 1.3 Структура API слоя

```
bot/                          # Существующая архитектура Telegram бота
├── main.py                   # Точка входа (Telegram Bot + API Server)
├── config.py                 # Конфигурация (общая для бота и API)
├── services/                 # Существующий сервисный слой
│   ├── service_factory.py   # Фабрика сервисов (расширяется для API)
│   ├── core/                # Основные сервисы
│   │   ├── blockchain.py    # BlockchainService (синглтон)
│   │   ├── account.py       # AccountService
│   │   ├── circle.py        # CircleService
│   │   └── supabase.py      # SupabaseService
│   ├── product/             # Сервисы продуктов
│   │   ├── registry.py      # ProductRegistryService
│   │   ├── storage.py       # ProductStorageService
│   │   └── validation.py    # ProductValidationService
│   └── orders/              # Сервисы заказов
├── model/                    # Модели данных (общие)
├── handlers/                 # Telegram handlers (остаются без изменений)
├── keyboards/                # Telegram keyboards (остаются без изменений)
├── fsm/                      # FSM для Telegram (остаются без изменений)
├── templates/                # Шаблоны (общие)
├── utils/                    # Утилиты (общие)
└── api/                      # НОВЫЙ API слой (расширение)
    ├── __init__.py
    ├── main.py              # FastAPI приложение
    ├── config.py            # API-специфичная конфигурация
    ├── middleware/          # API middleware
    │   ├── __init__.py
    │   ├── auth.py          # HMAC аутентификация
    │   ├── logging.py       # API логирование
    │   ├── rate_limiting.py # Rate limiting
    │   └── cors.py          # CORS настройки
    ├── models/              # Pydantic модели для API
    │   ├── __init__.py
    │   ├── requests.py      # Request модели
    │   ├── responses.py     # Response модели
    │   └── common.py        # Общие API модели
    ├── routes/              # API маршруты
    │   ├── __init__.py
    │   ├── products.py      # Продукты (использует ProductRegistryService)
    │   ├── orders.py        # Заказы (использует OrderService)
    │   ├── sellers.py       # Продавцы (использует AccountService)
    │   └── invites.py       # Инвайты (использует InviteService)
    └── exceptions/          # API исключения
        ├── __init__.py
        └── handlers.py      # Обработчики ошибок
```

**Принципы интеграции:**
- Переиспользование существующих сервисов через ServiceFactory
- Общие модели данных между ботом и API
- Единая конфигурация для блокчейна и внешних сервисов
- Изоляция API логики в отдельном слое
- Совместимость с существующей архитектурой Telegram бота

## 2. Аутентификация и безопасность

### 2.1 HMAC Middleware

API использует HMAC-SHA256 аутентификацию для всех защищенных эндпоинтов:

```python
class HMACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропускаем аутентификацию для определенных путей
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Проверяем наличие заголовков аутентификации
        if not self._has_auth_headers(request):
            return JSONResponse(status_code=401, content={"error": "Missing authentication headers"})
        
        try:
            # Извлекаем заголовки аутентификации
            auth_headers = self._extract_auth_headers(request)
            
            # Валидируем timestamp
            self._validate_timestamp(auth_headers["timestamp"])
            
            # Валидируем nonce
            self._validate_nonce(auth_headers["nonce"])
            
            # Валидируем API ключ и получаем секретный ключ
            secret_key = await self._validate_api_key(auth_headers["api_key"])
            
            # Валидируем HMAC подпись
            await self._validate_signature(request, auth_headers, secret_key)
            
            # Добавляем контекст продавца в request state
            request.state.seller_address = auth_headers["api_key"]
            
            # Продолжаем обработку запроса
            response = await call_next(request)
            return response
            
        except Exception as e:
            return JSONResponse(status_code=401, content={"error": str(e)})
```

### 2.2 Структура аутентификации

**Обязательные заголовки:**
```http
X-API-Key: seller_public_key
X-Timestamp: 1640995200
X-Nonce: unique_nonce_string
X-Signature: hmac_signature
```

**Процесс подписи:**
1. Сбор данных: метод + путь + тело запроса + timestamp + nonce
2. Создание строки: `{method}\n{path}\n{body}\n{timestamp}\n{nonce}`
3. HMAC подпись: `hmac.new(secret_key, message, hashlib.sha256).hexdigest()`
4. Валидация: проверка подписи, timestamp, nonce на сервере

### 2.3 Публичные пути

Следующие пути не требуют аутентификации:
```python
skip_paths = {
    "/", "/health", "/health/detailed", "/hello", 
    "/docs", "/redoc", "/openapi.json"
}
```

### 2.4 Fallback механизм

Если ApiKeyService недоступен, система использует fallback:
```python
if not self.api_key_service:
    # Fallback на базовую проверку если ApiKeyService недоступен
    if not api_key or len(api_key) < 10:
        raise InvalidAPIKeyError("API key is invalid or too short")
    # Возвращаем дефолтный секретный ключ для совместимости
    return self.config.get("secret_key", "default-secret-key-change-in-production")
```

## 3. Интеграция с существующими сервисами

### 3.1 Использование ServiceFactory в API

```python
# bot/api/routes/products.py
from fastapi import APIRouter, Depends
from bot.services.service_factory import ServiceFactory
from bot.api.models.requests import ProductCreateRequest
from bot.api.models.responses import ProductResponse

router = APIRouter(prefix="/products", tags=["products"])

def get_service_factory() -> ServiceFactory:
    """Dependency injection для ServiceFactory"""
    return ServiceFactory()

@router.post("/", response_model=ProductResponse)
async def create_product(
    request: ProductCreateRequest,
    service_factory: ServiceFactory = Depends(get_service_factory)
):
    # Использование существующего ProductRegistryService
    product_service = service_factory.create_product_registry_service()
    
    # Создание продукта через существующую логику
    product = await product_service.create_product(
        name=request.name,
        description=request.description,
        price=request.price,
        seller_address=request.seller_address
    )
    
    return ProductResponse(
        success=True,
        data=product,
        blockchain_id=product.blockchain_id,
        ipfs_cid=product.ipfs_cid
    )
```

### 3.2 Переиспользование моделей данных

```python
# bot/api/models/requests.py
from pydantic import BaseModel
from bot.model.product import Product  # Существующая модель

class ProductCreateRequest(BaseModel):
    name: str
    description: str
    price: float
    category: str
    seller_address: str
    
    def to_product_model(self) -> Product:
        """Конвертация в существующую модель Product"""
        return Product(
            name=self.name,
            description=self.description,
            price=self.price,
            category=self.category
        )
```

### 3.3 Общие утилиты и конфигурация

```python
# bot/api/config.py
from bot.config import *  # Импорт существующей конфигурации

# API-специфичные настройки
API_HOST = "0.0.0.0"
API_PORT = 8000
API_WORKERS = 4

# Переиспользование блокчейн конфигурации
BLOCKCHAIN_RPC_URL = BLOCKCHAIN_RPC_URL  # Из bot/config.py
CONTRACT_ADDRESSES = CONTRACT_ADDRESSES   # Из bot/config.py
```

## 4. Модели данных

### 4.1 Request Models
```python
class BaseRequest(BaseModel):
    timestamp: int
    nonce: str
    
class ProductCreateRequest(BaseRequest):
    name: str
    description: str
    price: Decimal
    category: str
    # ... другие поля
```

### 4.2 Response Models
```python
class BaseResponse(BaseModel):
    success: bool
    timestamp: int
    request_id: str
    
class ProductResponse(BaseResponse):
    data: ProductData
    blockchain_id: str
    ipfs_cid: str
```

### 4.3 Error Models
```python
class APIError(BaseModel):
    code: str
    message: str
    details: Optional[Dict]
    request_id: str
```

## 5. Обработка ошибок

### 5.1 Иерархия исключений
```python
class AmanitaAPIException(Exception):
    """Base exception for all API errors"""
    
class AuthenticationError(AmanitaAPIException):
    """Authentication/Authorization errors"""
    
class ValidationError(AmanitaAPIException):
    """Request validation errors"""
    
class BlockchainError(AmanitaAPIException):
    """Blockchain interaction errors"""
```

### 5.2 HTTP Status Codes
- **200** - Success
- **201** - Created
- **400** - Bad Request (validation errors)
- **401** - Unauthorized (authentication failed)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found
- **429** - Too Many Requests (rate limit exceeded)
- **500** - Internal Server Error

### 5.3 Error Handler
```python
@app.exception_handler(AmanitaAPIException)
async def amanita_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIError(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.state.request_id
        ).dict()
    )
```

## 6. Конфигурация и развертывание

### 6.1 Environment Variables
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
JWT_SECRET_KEY=your-secret-key
HMAC_SECRET=your-hmac-secret

# Database
DATABASE_URL=postgresql://user:pass@localhost/amanita
REDIS_URL=redis://localhost:6379

# Blockchain
BLOCKCHAIN_RPC_URL=https://mainnet.infura.io/v3/your-key
CONTRACT_ADDRESSES={"registry": "0x...", "payment": "0x..."}

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

### 6.2 Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.3 Health Checks
- **/health** - базовый health check
- **/health/detailed** - детальная проверка всех компонентов
- **/metrics** - Prometheus метрики

## 7. Мониторинг и метрики

### 7.1 Prometheus Metrics
- Request count по эндпоинтам
- Response time percentiles
- Error rate по типам ошибок
- Active connections
- Rate limiting статистика

### 7.2 Logging Strategy
- Structured logging с correlation IDs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log aggregation через ELK stack или аналоги
- Audit trail для всех операций

### 7.3 Alerting
- High error rate (>5%)
- High response time (>2s)
- Rate limit превышения
- Authentication failures
- Blockchain ошибки

## 8. Масштабируемость

### 8.1 Горизонтальное масштабирование
- Stateless API серверы
- Load balancer (nginx/haproxy)
- Database connection pooling
- Redis для кэширования и сессий

### 8.2 Кэширование
- Redis для API responses
- Database query caching
- Blockchain data caching
- CDN для статических ресурсов

### 8.3 Асинхронная обработка
- Celery для фоновых задач
- Message queues (Redis/RabbitMQ)
- Event-driven архитектура
- Webhooks для уведомлений

## 9. Документация

### 9.1 OpenAPI/Swagger
- Автоматическая генерация из кода
- Interactive документация
- Request/Response примеры
- Authentication схемы

### 9.2 SDK и примеры
- Python SDK для клиентов
- PHP SDK для WooCommerce
- JavaScript SDK для веб-клиентов
- Postman коллекции

### 9.3 Интеграционные гайды
- WooCommerce интеграция
- Shopify интеграция
- Magento интеграция
- Custom интеграции

## 10. Тестирование

### 10.1 Unit Tests
- Pytest для тестирования
- Mock внешних зависимостей
- Coverage > 90%
- CI/CD интеграция

### 10.2 Integration Tests
- Test database с фикстурами
- Mock blockchain для тестов
- API testing с реальными запросами
- Performance тестирование

### 10.3 Security Testing
- Penetration testing регулярно
- Vulnerability scanning автоматически
- Code security анализ
- Dependency проверки

## Заключение

AMANITA API представляет собой расширение существующей архитектуры Telegram бота для внешних клиентов. API использует стандартные механизмы безопасности (HMAC аутентификация) и переиспользует существующие сервисы через ServiceFactory.

**Ключевые особенности:**
- HMAC аутентификация для всех защищенных эндпоинтов
- Fallback механизм при недоступности ApiKeyService
- Переиспользование существующих сервисов и моделей
- Стандартные практики безопасности и обработки ошибок
- Планы на блокчейн интеграцию (не реализовано в текущей версии)

**Текущий статус:**
- ✅ HMAC аутентификация реализована
- ✅ Fallback механизм работает
- ✅ Интеграция с существующими сервисами
- ❌ Блокчейн интеграция - только планы
- ❌ Context-aware security - не реализовано
- ❌ Threat intelligence - не реализовано

API готов для базового использования и может быть расширен для блокчейн интеграции в будущем.
