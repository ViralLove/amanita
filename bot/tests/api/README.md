# API Tests Audit & Best Practices Guide

## 📊 Обзор тестирования API

### Текущее состояние (на 2025-07-13)
- **Всего тестов:** 34
- **Проходящих тестов:** 34/34 (100%)
- **Покрытие кода:** ~75% (оценка)
- **Структура тестов:** Хорошо организована по функциональности

## 🧪 Аудит существующих тестов

### ✅ Сильные стороны

#### 1. **Тесты аутентификации** (`test_api_auth.py`)
- **Покрытие:** HMAC middleware, валидация подписей, проверка заголовков
- **Качество:** Высокое - тестирует реальные сценарии аутентификации
- **Практики:** Использует `httpx.AsyncClient` для реальных HTTP запросов

#### 2. **Тесты health endpoints** (`test_health_endpoints.py`)
- **Покрытие:** Базовые и детальные health checks, uptime, метрики
- **Качество:** Отличное - тестирует все компоненты системы
- **Практики:** Использует фикстуры и моки для изоляции тестов

#### 3. **Тесты health utils** (`test_health_utils.py`)
- **Покрытие:** Утилиты форматирования, проверки компонентов, метрики
- **Качество:** Высокое - unit тесты с хорошей изоляцией
- **Практики:** Правильное использование `pytest.mark.asyncio`

#### 4. **Тесты обработчиков ошибок** (`test_error_handlers.py`)
- **Покрытие:** Валидация, внутренние ошибки, аутентификация
- **Качество:** Хорошее - тестирует реальные HTTP ответы
- **Практики:** Использует реальные HMAC заголовки

### ❌ Области для улучшения

#### 1. **Покрытие кода**
- **API Routes:** Отсутствуют тесты для `/api-keys/` эндпоинтов
- **Middleware:** Частичное покрытие edge cases
- **Models:** Отсутствуют тесты валидации Pydantic моделей
- **Services:** Нет интеграционных тестов с реальными сервисами

#### 2. **Качество тестов**
- **Изоляция:** Некоторые тесты зависят от внешних сервисов
- **Данные:** Отсутствуют фикстуры для тестовых данных
- **Очистка:** Нет cleanup после тестов
- **Параметризация:** Отсутствуют параметризованные тесты

#### 3. **Best Practices**
- **Конфигурация:** Отсутствует `pytest.ini` или `pyproject.toml`
- **Фикстуры:** Нет централизованных фикстур
- **Логирование:** Отсутствует настройка логирования для тестов
- **CI/CD:** Нет интеграции с CI/CD pipeline

## 🎯 План достижения 100% покрытия

### Этап 1: Дополнительные тесты API Routes

#### 1.1 Тесты `/api-keys/` эндпоинтов
```python
# test_api_keys.py
@pytest.mark.asyncio
async def test_create_api_key_success():
    """Тест успешного создания API ключа"""
    
@pytest.mark.asyncio
async def test_create_api_key_invalid_address():
    """Тест создания ключа с невалидным адресом"""
    
@pytest.mark.asyncio
async def test_validate_api_key_success():
    """Тест валидации существующего ключа"""
    
@pytest.mark.asyncio
async def test_validate_api_key_not_found():
    """Тест валидации несуществующего ключа"""
```

#### 1.2 Тесты публичных эндпоинтов
```python
# test_public_endpoints.py
@pytest.mark.asyncio
async def test_root_endpoint():
    """Тест корневого эндпоинта"""
    
@pytest.mark.asyncio
async def test_hello_endpoint():
    """Тест hello world эндпоинта"""
    
@pytest.mark.asyncio
async def test_openapi_schema():
    """Тест генерации OpenAPI схемы"""
```

### Этап 2: Тесты Pydantic моделей

#### 2.1 Валидация кастомных типов
```python
# test_models.py
def test_ethereum_address_validation():
    """Тест валидации Ethereum адресов"""
    
def test_api_key_validation():
    """Тест валидации API ключей"""
    
def test_timestamp_validation():
    """Тест валидации timestamp"""
    
def test_request_id_validation():
    """Тест валидации request ID"""
```

#### 2.2 Тесты моделей ответов
```python
def test_health_response_model():
    """Тест модели HealthCheckResponse"""
    
def test_error_response_model():
    """Тест модели ErrorResponse"""
    
def test_auth_response_model():
    """Тест модели AuthResponse"""
```

### Этап 3: Интеграционные тесты

#### 3.1 Тесты с реальными сервисами
```python
# test_integration.py
@pytest.mark.asyncio
async def test_api_key_service_integration():
    """Интеграционный тест с ApiKeyService"""
    
@pytest.mark.asyncio
async def test_blockchain_service_integration():
    """Интеграционный тест с BlockchainService"""
    
@pytest.mark.asyncio
async def test_service_factory_integration():
    """Интеграционный тест с ServiceFactory"""
```

#### 3.2 End-to-end тесты
```python
@pytest.mark.asyncio
async def test_full_api_key_workflow():
    """E2E тест полного workflow создания и валидации ключа"""
    
@pytest.mark.asyncio
async def test_authentication_workflow():
    """E2E тест workflow аутентификации"""
```

### Этап 4: Тесты производительности и безопасности

#### 4.1 Тесты производительности
```python
# test_performance.py
@pytest.mark.asyncio
async def test_health_endpoint_performance():
    """Тест производительности health endpoint"""
    
@pytest.mark.asyncio
async def test_hmac_middleware_performance():
    """Тест производительности HMAC middleware"""
```

#### 4.2 Тесты безопасности
```python
# test_security.py
@pytest.mark.asyncio
async def test_replay_attack_protection():
    """Тест защиты от replay атак"""
    
@pytest.mark.asyncio
async def test_timestamp_window_validation():
    """Тест валидации временного окна"""
    
@pytest.mark.asyncio
async def test_nonce_uniqueness():
    """Тест уникальности nonce"""
```

## 🔧 Рекомендации по улучшению

### 1. Конфигурация тестов

#### 1.1 Создать `pytest.ini`
```ini
[tool:pytest]
asyncio_mode = auto
testpaths = bot/tests/api
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    e2e: marks tests as end-to-end tests
```

#### 1.2 Создать `conftest.py` с фикстурами
```python
# conftest.py
import pytest
import httpx
import asyncio
from typing import AsyncGenerator

@pytest.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Фикстура для HTTP клиента"""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client

@pytest.fixture
def test_api_key() -> str:
    """Фикстура для тестового API ключа"""
    return "test-api-key-12345"

@pytest.fixture
def test_secret_key() -> str:
    """Фикстура для тестового секретного ключа"""
    return "default-secret-key-change-in-production"

@pytest.fixture
def valid_ethereum_address() -> str:
    """Фикстура для валидного Ethereum адреса"""
    return "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"
```

### 2. Улучшение структуры тестов

#### 2.1 Параметризованные тесты
```python
@pytest.mark.parametrize("invalid_address", [
    "invalid-address",
    "0x123",
    "not-an-address",
    "",
    None
])
def test_ethereum_address_validation_invalid(invalid_address):
    """Тест валидации невалидных Ethereum адресов"""
    with pytest.raises(ValueError):
        EthereumAddress(invalid_address)
```

#### 2.2 Тестовые данные
```python
# test_data.py
VALID_ETHEREUM_ADDRESSES = [
    "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
    "0x1234567890123456789012345678901234567890",
    "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
]

INVALID_ETHEREUM_ADDRESSES = [
    "invalid-address",
    "0x123",
    "not-an-address",
    "",
    None
]

VALID_API_KEYS = [
    "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678",
    "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12"
]
```

### 3. Логирование и отладка

#### 3.1 Настройка логирования для тестов
```python
# conftest.py
import logging

@pytest.fixture(autouse=True)
def setup_test_logging():
    """Настройка логирования для тестов"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
```

#### 3.2 Тестовые утилиты
```python
# test_utils.py
import time
import uuid
import hmac
import hashlib
from typing import Dict

def generate_hmac_headers(method: str, path: str, body: str, 
                         api_key: str, api_secret: str) -> Dict[str, str]:
    """Генерация HMAC заголовков для тестов"""
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return {
        "X-API-Key": api_key,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }

def assert_error_response(response, expected_status: int, expected_error: str):
    """Утилита для проверки ответов с ошибками"""
    assert response.status_code == expected_status
    data = response.json()
    assert data["success"] is False
    assert data["error"] == expected_error
    assert "message" in data
```

### 4. CI/CD интеграция

#### 4.1 GitHub Actions workflow
```yaml
# .github/workflows/api-tests.yml
name: API Tests

on:
  push:
    paths: ['bot/api/**', 'bot/tests/api/**']
  pull_request:
    paths: ['bot/api/**', 'bot/tests/api/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Start API server
        run: |
          cd bot
          python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
      - name: Run tests
        run: |
          cd bot
          pytest tests/api/ -v --cov=api --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./bot/coverage.xml
```

#### 4.2 Coverage configuration
```ini
# .coveragerc
[run]
source = bot/api
omit = 
    */tests/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod
```

## 📈 Метрики качества

### Текущие метрики
- **Покрытие кода:** ~75%
- **Время выполнения тестов:** ~1.5 секунды
- **Количество тестов:** 34
- **Процент проходящих тестов:** 100%

### Целевые метрики
- **Покрытие кода:** 95%+
- **Время выполнения тестов:** <5 секунд
- **Количество тестов:** 50+
- **Процент проходящих тестов:** 100%

## 🚀 Приоритеты развития

### Высокий приоритет
1. ✅ Исправить проблему с `/openapi.json`
2. ✅ Восстановить тест 404 ошибки
3. 🔄 Добавить тесты для `/api-keys/` эндпоинтов
4. 🔄 Создать интеграционные тесты

### Средний приоритет
1. 🔄 Добавить параметризованные тесты
2. 🔄 Улучшить фикстуры и тестовые данные
3. 🔄 Добавить тесты производительности
4. 🔄 Настроить CI/CD pipeline

### Низкий приоритет
1. 🔄 Добавить тесты безопасности
2. 🔄 Создать E2E тесты
3. 🔄 Добавить тесты для edge cases
4. 🔄 Оптимизировать время выполнения тестов

## 📚 Дополнительные ресурсы

### Документация
- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [HTTPX Testing](https://www.python-httpx.org/async/)

### Best Practices
- [Testing Best Practices](https://realpython.com/python-testing/)
- [API Testing Strategies](https://martinfowler.com/articles/microservice-testing/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

---

**Последнее обновление:** 2025-07-13  
**Версия:** 1.0.0  
**Автор:** AMANITA Development Team 