# 🧪 Эффективная структура тестов API

## 🎯 Принципы тестирования API

### ✅ **ПРАВИЛЬНЫЙ ПОДХОД (который мы используем):**
- **Сервисный слой уже протестирован** → мокаем сервисы в API тестах
- **API тесты фокусируются на:** HTTP логике, валидации, аутентификации, маршрутизации
- **Минимум интеграционных тестов** → только для проверки соединения слоев
- **Быстрые и надежные тесты** → без внешних зависимостей

### ❌ **НЕПРАВИЛЬНЫЙ ПОДХОД (который избегаем):**
- Дублирование тестов сервисного слоя
- Тестирование бизнес-логики в API тестах
- Медленные интеграционные тесты
- Зависимость от внешних сервисов

## 🏗️ Архитектура тестирования API

### 📊 **Слои тестирования:**

```
┌─────────────────────────────────────────────────────────────┐
│                    API TESTS (100% моки)                   │
├─────────────────────────────────────────────────────────────┤
│  HTTP Logic │ Validation │ Auth │ Routing │ Error Handling │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SERVICE LAYER (уже протестирован)             │
├─────────────────────────────────────────────────────────────┤
│  Business Logic │ Data Processing │ External Integrations  │
└─────────────────────────────────────────────────────────────┘
```

### 🎭 **Стратегия мокирования:**

```python
# В API тестах мокаем ВСЕ сервисы
@pytest.fixture
def mock_product_registry_service():
    """Полностью замоканный ProductRegistryService"""
    mock_service = Mock()
    mock_service.create_product = AsyncMock(return_value={
        "status": "success",
        "blockchain_id": "123",
        "metadata_cid": "QmValidCID123..."
    })
    return mock_service

@pytest.fixture
def mock_blockchain_service():
    """Полностью замоканный BlockchainService"""
    mock_service = Mock()
    mock_service.get_product = AsyncMock(return_value=MockProduct())
    return mock_service
```

## 📁 Структура тестов API

### 🗂️ **Организация файлов:**

```
bot/tests/api/
├── unit/                          # Unit тесты API компонентов
│   ├── test_models.py            # Pydantic модели
│   ├── test_dependencies.py      # Dependency injection
│   ├── test_utils.py             # API утилиты
│   └── test_middleware.py        # Middleware логика
│
├── integration/                   # Интеграционные тесты API
│   ├── test_products_api.py      # Products endpoints
│   ├── test_api_keys_api.py      # API keys endpoints
│   ├── test_health_api.py        # Health endpoints
│   └── test_auth_api.py          # Authentication
│
├── fixtures/                      # Централизованные фикстуры
│   ├── conftest.py               # Основные фикстуры
│   ├── mock_services.py          # Моки сервисов
│   └── test_data.py              # Тестовые данные
│
└── e2e/                          # End-to-end тесты (минимально)
    └── test_api_connectivity.py  # Проверка соединения слоев
```

## 🧪 Типы тестов API

### 1. **Unit тесты (80% покрытия)**

#### **Тестирование Pydantic моделей:**
```python
def test_product_create_model_validation():
    """Тест валидации модели создания продукта"""
    # Валидные данные
    valid_data = {
        "title": "Test Product",
        "categories": ["test"],
        "prices": [{"price": "10", "currency": "EUR", "weight": "100", "weight_unit": "g"}]
    }
    product = ProductCreate(**valid_data)
    assert product.title == "Test Product"
    
    # Невалидные данные
    with pytest.raises(ValidationError):
        ProductCreate(title="", categories=[], prices=[])
```

#### **Тестирование Dependency Injection:**
```python
async def test_get_product_registry_service():
    """Тест получения ProductRegistryService из DI контейнера"""
    service = await get_product_registry_service()
    assert isinstance(service, ProductRegistryService)
    assert hasattr(service, 'create_product')
```

#### **Тестирование Middleware:**
```python
async def test_hmac_middleware_valid_signature():
    """Тест HMAC middleware с валидной подписью"""
    # Тестируем только логику middleware, не реальные сервисы
```

### 2. **Интеграционные тесты API (15% покрытия)**

#### **Тестирование HTTP endpoints с моками:**
```python
@pytest.mark.asyncio
async def test_create_product_endpoint_success(
    client: AsyncClient,
    mock_product_registry_service,
    valid_product_data,
    valid_hmac_headers
):
    """Тест успешного создания продукта через API"""
    # Arrange
    with patch('bot.api.dependencies.get_product_registry_service', 
               return_value=mock_product_registry_service):
        
        # Act
        response = await client.post(
            "/api/products/",
            json=valid_product_data,
            headers=valid_hmac_headers
        )
        
        # Assert
        assert response.status_code == 201
        assert response.json()["status"] == "success"
        assert "blockchain_id" in response.json()
        
        # Проверяем, что сервис был вызван
        mock_product_registry_service.create_product.assert_called_once()
```

#### **Тестирование валидации API:**
```python
@pytest.mark.asyncio
async def test_create_product_validation_error(
    client: AsyncClient,
    invalid_product_data,
    valid_hmac_headers
):
    """Тест валидации данных на уровне API"""
    response = await client.post(
        "/api/products/",
        json=invalid_product_data,
        headers=valid_hmac_headers
    )
    
    assert response.status_code == 422
    assert "validation error" in response.json()["detail"].lower()
```

### 3. **End-to-End тесты (5% покрытия)**

#### **Проверка соединения слоев:**
```python
@pytest.mark.asyncio
async def test_api_service_layer_connection():
    """Тест что API правильно подключается к сервисному слою"""
    # Минимальный тест для проверки архитектуры
    # НЕ тестируем бизнес-логику, только соединение
```

## 🔧 Техническая реализация

### **1. Централизованные моки сервисов:**

```python
# bot/tests/api/fixtures/mock_services.py

class MockProductRegistryService:
    """Полностью замоканный ProductRegistryService для API тестов"""
    
    def __init__(self):
        self.create_product = AsyncMock()
        self.get_product = AsyncMock()
        self.update_product = AsyncMock()
        self.delete_product = AsyncMock()
        
        # Настройка поведения по умолчанию
        self.create_product.return_value = {
            "status": "success",
            "blockchain_id": "123",
            "metadata_cid": "QmValidCID123..."
        }
        
        self.get_product.return_value = MockProduct(
            id="123",
            title="Test Product",
            status=1
        )

@pytest.fixture
def mock_product_registry_service():
    """Фикстура для замоканного ProductRegistryService"""
    return MockProductRegistryService()
```

### **2. Тестовые данные:**

```python
# bot/tests/api/fixtures/test_data.py

@pytest.fixture
def valid_product_data():
    """Валидные данные для создания продукта"""
    return {
        "title": "Test Product",
        "categories": ["test"],
        "prices": [{
            "price": "10",
            "currency": "EUR",
            "weight": "100",
            "weight_unit": "g"
        }]
    }

@pytest.fixture
def invalid_product_data():
    """Невалидные данные для тестирования валидации"""
    return {
        "title": "",  # Пустой заголовок
        "categories": [],  # Пустые категории
        "prices": []  # Пустые цены
    }
```

### **3. HTTP клиент для тестов:**

```python
# bot/tests/api/fixtures/conftest.py

@pytest.fixture
async def client():
    """Async HTTP клиент для тестирования API"""
    from bot.api.main import app
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def valid_hmac_headers():
    """Валидные HMAC заголовки для аутентификации"""
    return {
        "X-API-Key": "test-api-key",
        "X-Timestamp": str(int(time.time())),
        "X-Signature": "valid-signature-hash"
    }
```

## 📊 Метрики качества тестов

### **Целевые показатели:**

- **Время выполнения:** < 5 секунд для всех API тестов
- **Покрытие кода:** 90%+ для API слоя
- **Изоляция:** 100% моки для внешних зависимостей
- **Надежность:** 0% flaky тестов
- **Читаемость:** Понятные названия и структура

### **Метрики успеха:**

```bash
# Быстрые тесты
pytest bot/tests/api/ -v --durations=10
# Ожидаемый результат: все тесты < 100ms

# Полное покрытие
pytest bot/tests/api/ --cov=bot.api --cov-report=html
# Ожидаемый результат: 90%+ coverage

# Изоляция от внешних зависимостей
pytest bot/tests/api/ --tb=short
# Ожидаемый результат: 0 network calls, 0 external dependencies
```

## 🎯 Преимущества такого подхода

### **1. Скорость:**
- ✅ Тесты выполняются за миллисекунды
- ✅ Нет ожидания внешних сервисов
- ✅ Параллельное выполнение

### **2. Надежность:**
- ✅ 0% flaky тестов
- ✅ Предсказуемые результаты
- ✅ Изоляция от внешних проблем

### **3. Поддержка:**
- ✅ Легко обновлять при изменении API
- ✅ Четкое разделение ответственности
- ✅ Простая отладка

### **4. Безопасность:**
- ✅ Тестирование всех API сценариев
- ✅ Валидация входных данных
- ✅ Проверка аутентификации
- ✅ Обработка ошибок

## 🚀 План внедрения

### **Этап 1: Рефакторинг существующих тестов (1-2 дня)**
1. Создать централизованные моки сервисов
2. Переписать тесты для использования моков
3. Убрать зависимости от внешних сервисов

### **Этап 2: Расширение покрытия (2-3 дня)**
1. Добавить тесты для всех API endpoints
2. Создать тесты валидации моделей
3. Добавить тесты middleware

### **Этап 3: Оптимизация и CI/CD (1 день)**
1. Настроить параллельное выполнение
2. Интегрировать в CI/CD pipeline
3. Добавить метрики качества

## 🎉 Заключение

**Да, вы абсолютно правы!** Если сервисный слой уже протестирован, то в API тестах нужно:

1. **Мокать все сервисы** → для скорости и надежности
2. **Фокусироваться на API логике** → HTTP, валидация, аутентификация
3. **Минимум интеграционных тестов** → только для проверки соединения слоев
4. **100% изоляция** → от внешних зависимостей

**Результат:** Быстрые, надежные, понятные тесты API, которые действительно тестируют API, а не дублируют тесты сервисного слоя.
