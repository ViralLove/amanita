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
    """Полностью замоканный ProductRegistryService для новой архитектуры с organic_components"""
    mock_service = Mock()
    mock_service.create_product = AsyncMock(return_value={
        "status": "success",
        "id": "test_product_001",
        "blockchain_id": "123",
        "metadata_cid": "QmValidCID123...",
        "tx_hash": "0x1234567890abcdef..."
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
│   ├── test_models.py            # Pydantic модели (включая OrganicComponentAPI)
│   ├── test_dependencies.py      # Dependency injection
│   ├── test_utils.py             # API утилиты
│   └── test_middleware.py        # Middleware логика
│
├── integration/                   # Интеграционные тесты API
│   ├── test_products_api.py      # Products endpoints с organic_components
│   ├── test_api_keys_api.py      # API keys endpoints
│   ├── test_health_api.py        # Health endpoints
│   └── test_auth_api.py          # Authentication
│
├── fixtures/                      # Централизованные фикстуры
│   ├── conftest.py               # Основные фикстуры
│   ├── mock_services.py          # Моки сервисов
│   └── test_data.py              # Тестовые данные с organic_components
│
└── e2e/                          # End-to-end тесты (минимально)
    └── test_api_connectivity.py  # Проверка соединения слоев
```

## 🧪 Типы тестов API

### 1. **Unit тесты (80% покрытия)**

#### **Тестирование Pydantic моделей с organic_components:**
```python
def test_organic_component_api_validation():
    """Тест валидации модели OrganicComponentAPI"""
    # Валидные данные
    valid_component = {
        "biounit_id": "amanita_muscaria",
        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
        "proportion": "100%"
    }
    component = OrganicComponentAPI(**valid_component)
    assert component.biounit_id == "amanita_muscaria"
    assert component.proportion == "100%"
    
    # Невалидные данные - пустой biounit_id
    with pytest.raises(ValidationError):
        OrganicComponentAPI(
            biounit_id="",
            description_cid="QmValidCID123...",
            proportion="100%"
        )
    
    # Невалидные данные - некорректный CID
    with pytest.raises(InvalidCIDError):
        OrganicComponentAPI(
            biounit_id="amanita_muscaria",
            description_cid="invalid_cid",
            proportion="100%"
        )

def test_product_upload_in_model_validation():
    """Тест валидации модели ProductUploadIn с organic_components"""
    # Валидные данные с organic_components
    valid_data = {
        "id": "test_product_001",
        "title": "Amanita Muscaria — Powder",
        "organic_components": [
            {
                "biounit_id": "amanita_muscaria",
                "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                "proportion": "100%"
            }
        ],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom", "medicinal"],
        "forms": ["powder"],
        "species": "Amanita Muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ]
    }
    product = ProductUploadIn(**valid_data)
    assert product.title == "Amanita Muscaria — Powder"
    assert len(product.organic_components) == 1
    assert product.organic_components[0].biounit_id == "amanita_muscaria"
    
    # Невалидные данные - отсутствуют organic_components
    with pytest.raises(ValidationError):
        ProductUploadIn(
            id="test_002",
            title="Test Product",
            organic_components=[],  # Пустой список
            cover_image="QmValidCID123...",
            categories=["test"],
            forms=["powder"],
            species="Test Species",
            prices=[{"weight": "100", "weight_unit": "g", "price": "50", "currency": "EUR"}]
        )
    
    # Невалидные данные - дублирующиеся biounit_id
    with pytest.raises(ValidationError):
        ProductUploadIn(
            id="test_003",
            title="Test Product",
            organic_components=[
                {
                    "biounit_id": "amanita_muscaria",  # Дублирующийся ID
                    "description_cid": "QmCID1...",
                    "proportion": "70%"
                },
                {
                    "biounit_id": "amanita_muscaria",  # Дублирующийся ID
                    "description_cid": "QmCID2...",
                    "proportion": "30%"
                }
            ],
            cover_image="QmValidCID123...",
            categories=["test"],
            forms=["powder"],
            species="Test Species",
            prices=[{"weight": "100", "weight_unit": "g", "price": "50", "currency": "EUR"}]
        )
```

#### **Тестирование Dependency Injection:**
```python
async def test_get_product_registry_service():
    """Тест получения ProductRegistryService из DI контейнера"""
    service = await get_product_registry_service()
    assert isinstance(service, ProductRegistryService)
    assert hasattr(service, 'create_product')
    assert hasattr(service, 'update_product')
```

#### **Тестирование Middleware:**
```python
async def test_hmac_middleware_valid_signature():
    """Тест HMAC middleware с валидной подписью"""
    # Тестируем только логику middleware, не реальные сервисы
```

### 2. **Интеграционные тесты API (15% покрытия)**

#### **Тестирование HTTP endpoints с organic_components:**
```python
@pytest.mark.asyncio
async def test_create_product_endpoint_success_with_organic_components(
    client: AsyncClient,
    mock_product_registry_service,
    valid_product_data_with_organic_components,
    valid_hmac_headers
):
    """Тест успешного создания продукта с organic_components через API"""
    # Arrange
    with patch('bot.api.dependencies.get_product_registry_service', 
               return_value=mock_product_registry_service):
        
        # Act
        response = await client.post(
            "/api/products/upload",
            json={"products": [valid_product_data_with_organic_components]},
            headers=valid_hmac_headers
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["results"][0]["status"] == "success"
        assert "blockchain_id" in result["results"][0]
        
        # Проверяем, что сервис был вызван
        mock_product_registry_service.create_product.assert_called_once()

@pytest.mark.asyncio
async def test_update_product_endpoint_with_organic_components(
    client: AsyncClient,
    mock_product_registry_service,
    valid_product_update_data,
    valid_hmac_headers
):
    """Тест обновления продукта с organic_components через API"""
    # Arrange
    product_id = "test_product_001"
    with patch('bot.api.dependencies.get_product_registry_service', 
               return_value=mock_product_registry_service):
        
        # Act
        response = await client.put(
            f"/api/products/{product_id}",
            json=valid_product_update_data,
            headers=valid_hmac_headers
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        
        # Проверяем, что сервис был вызван
        mock_product_registry_service.update_product.assert_called_once()
```

#### **Тестирование валидации API с organic_components:**
```python
@pytest.mark.asyncio
async def test_create_product_validation_error_missing_organic_components(
    client: AsyncClient,
    invalid_product_data_missing_organic_components,
    valid_hmac_headers
):
    """Тест валидации данных с отсутствующими organic_components"""
    response = await client.post(
        "/api/products/upload",
        json={"products": [invalid_product_data_missing_organic_components]},
        headers=valid_hmac_headers
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert "organic_components" in str(error_detail).lower()

@pytest.mark.asyncio
async def test_create_product_validation_error_invalid_organic_components(
    client: AsyncClient,
    invalid_product_data_invalid_organic_components,
    valid_hmac_headers
):
    """Тест валидации данных с некорректными organic_components"""
    response = await client.post(
        "/api/products/upload",
        json={"products": [invalid_product_data_invalid_organic_components]},
        headers=valid_hmac_headers
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert "validation error" in str(error_detail).lower()
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

### **1. Централизованные моки сервисов для organic_components:**

```python
# bot/tests/api/fixtures/mock_services.py

class MockProductRegistryService:
    """Полностью замоканный ProductRegistryService для API тестов с organic_components"""
    
    def __init__(self):
        self.create_product = AsyncMock()
        self.get_product = AsyncMock()
        self.update_product = AsyncMock()
        self.delete_product = AsyncMock()
        self.validate_product = AsyncMock()
        
        # Настройка поведения по умолчанию для organic_components
        self.create_product.return_value = {
            "status": "success",
            "id": "test_product_001",
            "blockchain_id": "123",
            "metadata_cid": "QmValidCID123...",
            "tx_hash": "0x1234567890abcdef..."
        }
        
        self.get_product.return_value = MockProduct(
            id="test_product_001",
            title="Test Product",
            organic_components=[
                MockOrganicComponent(
                    biounit_id="amanita_muscaria",
                    description_cid="QmValidCID123...",
                    proportion="100%"
                )
            ],
            status=1
        )
        
        self.validate_product.return_value = True

class MockOrganicComponent:
    """Мок для органического компонента"""
    def __init__(self, biounit_id, description_cid, proportion):
        self.biounit_id = biounit_id
        self.description_cid = description_cid
        self.proportion = proportion

@pytest.fixture
def mock_product_registry_service():
    """Фикстура для замоканного ProductRegistryService"""
    return MockProductRegistryService()
```

### **2. Тестовые данные с organic_components:**

```python
# bot/tests/api/fixtures/test_data.py

@pytest.fixture
def valid_product_data_with_organic_components():
    """Валидные данные для создания продукта с organic_components"""
    return {
        "id": "amanita_muscaria_powder_001",
        "title": "Amanita Muscaria — Powder",
        "organic_components": [
            {
                "biounit_id": "amanita_muscaria",
                "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                "proportion": "100%"
            }
        ],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom", "medicinal"],
        "forms": ["powder"],
        "species": "Amanita Muscaria",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "80",
                "currency": "EUR"
            }
        ]
    }

@pytest.fixture
def valid_product_update_data():
    """Валидные данные для обновления продукта с organic_components"""
    return {
        "title": "Amanita Muscaria — Premium Powder",
        "organic_components": [
            {
                "biounit_id": "amanita_muscaria",
                "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                "proportion": "100%"
            }
        ],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom", "medicinal", "premium"],
        "forms": ["powder", "capsules"],
        "species": "Amanita Muscaria"
    }

@pytest.fixture
def invalid_product_data_missing_organic_components():
    """Невалидные данные с отсутствующими organic_components"""
    return {
        "id": "test_product_001",
        "title": "Test Product",
        # organic_components отсутствует - должно вызвать ошибку валидации
        "cover_image": "QmValidCID123...",
        "categories": ["test"],
        "forms": ["powder"],
        "species": "Test Species",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "50",
                "currency": "EUR"
            }
        ]
    }

@pytest.fixture
def invalid_product_data_invalid_organic_components():
    """Невалидные данные с некорректными organic_components"""
    return {
        "id": "test_product_002",
        "title": "Test Product",
        "organic_components": [
            {
                "biounit_id": "",  # Пустой biounit_id
                "description_cid": "QmValidCID123...",
                "proportion": "100%"
            }
        ],
        "cover_image": "QmValidCID123...",
        "categories": ["test"],
        "forms": ["powder"],
        "species": "Test Species",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "50",
                "currency": "EUR"
            }
        ]
    }

@pytest.fixture
def multi_component_product_data():
    """Данные для многокомпонентного продукта"""
    return {
        "id": "premium_blend_001",
        "title": "Premium Mushroom Blend",
        "organic_components": [
            {
                "biounit_id": "amanita_muscaria",
                "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                "proportion": "60%"
            },
            {
                "biounit_id": "blue_lotus",
                "description_cid": "QmBlueLotusCID1234567890123456789012345678901234567890",
                "proportion": "25%"
            },
            {
                "biounit_id": "chaga",
                "description_cid": "QmChagaCID1234567890123456789012345678901234567890",
                "proportion": "15%"
            }
        ],
        "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
        "categories": ["mushroom", "medicinal", "premium", "blend"],
        "forms": ["powder", "capsules"],
        "species": "Mixed Mushroom Blend",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "120",
                "currency": "EUR"
            },
            {
                "weight": "250",
                "weight_unit": "g",
                "price": "280",
                "currency": "EUR"
            }
        ]
    }

@pytest.fixture
def invalid_product_data_duplicate_biounit_ids():
    """Невалидные данные с дублирующимися biounit_id"""
    return {
        "id": "test_product_003",
        "title": "Test Product",
        "organic_components": [
            {
                "biounit_id": "amanita_muscaria",  # Дублирующийся ID
                "description_cid": "QmCID1...",
                "proportion": "70%"
            },
            {
                "biounit_id": "amanita_muscaria",  # Дублирующийся ID
                "description_cid": "QmCID2...",
                "proportion": "30%"
            }
        ],
        "cover_image": "QmValidCID123...",
        "categories": ["test"],
        "forms": ["powder"],
        "species": "Test Species",
        "prices": [
            {
                "weight": "100",
                "weight_unit": "g",
                "price": "50",
                "currency": "EUR"
            }
        ]
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

# Тестирование organic_components
pytest bot/tests/api/ -k "organic_components" -v
# Ожидаемый результат: все тесты с organic_components проходят
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
- ✅ Валидация входных данных (включая organic_components)
- ✅ Проверка аутентификации
- ✅ Обработка ошибок

## 🚀 План внедрения

### **Этап 1: Рефакторинг существующих тестов (1-2 дня)**
1. Создать централизованные моки сервисов для organic_components
2. Переписать тесты для использования новых моделей данных
3. Убрать зависимости от внешних сервисов

### **Этап 2: Расширение покрытия для organic_components (2-3 дня)**
1. Добавить тесты для всех API endpoints с organic_components
2. Создать тесты валидации новых Pydantic моделей
3. Добавить тесты middleware и валидации

### **Этап 3: Оптимизация и CI/CD (1 день)**
1. Настроить параллельное выполнение
2. Интегрировать в CI/CD pipeline
3. Добавить метрики качества для organic_components

## 🔄 Обновления для новой архитектуры

### **Ключевые изменения в API:**

**1. Новая структура продуктов:**
- ❌ **Убрано:** `description`, `description_cid`, `gallery`, `attributes`, `business_id`
- ✅ **Добавлено:** `organic_components` с детальной валидацией
- ✅ **Улучшено:** Валидация всех обязательных полей

**2. Новые правила валидации:**
- `organic_components`: Обязательное поле, минимум 1 элемент
- `biounit_id`: Уникальный идентификатор для каждого компонента
- `description_cid`: Валидный CID формат (Qm + 44 символа)
- `proportion`: Поддерживаемые форматы (50%, 100g, 30ml, kg, l, oz, lb, fl_oz)

**3. Новые Pydantic модели:**
- `OrganicComponentAPI`: Строгая валидация компонентов
- `ProductUploadIn`: Создание продуктов с organic_components
- `ProductUpdateIn`: Обновление продуктов с organic_components
- `ProductCreateFromDict`: Совместимость с тестами

### **Примеры использования в тестах:**

**Валидация organic_components:**
```python
# Тест уникальности biounit_id
def test_organic_components_unique_biounit_id():
    """Тест что biounit_id должен быть уникальным"""
    with pytest.raises(ValidationError, match="biounit_id должен быть уникальным"):
        ProductUploadIn(
            id="test",
            title="Test",
            organic_components=[
                {"biounit_id": "same_id", "description_cid": "QmCID1...", "proportion": "50%"},
                {"biounit_id": "same_id", "description_cid": "QmCID2...", "proportion": "50%"}
            ],
            cover_image="QmValidCID...",
            categories=["test"],
            forms=["powder"],
            species="Test",
            prices=[{"weight": "100", "weight_unit": "g", "price": "50", "currency": "EUR"}]
        )

# Тест валидации пропорций
def test_organic_components_proportion_validation():
    """Тест валидации формата пропорций"""
    with pytest.raises(ValidationError, match="Некорректный формат пропорции"):
        OrganicComponentAPI(
            biounit_id="test",
            description_cid="QmValidCID123...",
            proportion="invalid_format"
        )
```

## 🎉 Заключение

**Да, вы абсолютно правы!** Если сервисный слой уже протестирован, то в API тестах нужно:

1. **Мокать все сервисы** → для скорости и надежности
2. **Фокусироваться на API логике** → HTTP, валидация, аутентификация
3. **Минимум интеграционных тестов** → только для проверки соединения слоев
4. **100% изоляция** → от внешних зависимостей

**Новая архитектура с organic_components:**
- ✅ **Поддержка многокомпонентных продуктов** → гибкость и масштабируемость
- ✅ **Строгая валидация** → предотвращение некорректных данных
- ✅ **Информативные ошибки** → быстрое выявление проблем
- ✅ **Совместимость с тестами** → плавный переход на новую архитектуру

**Результат:** Быстрые, надежные, понятные тесты API с поддержкой новой архитектуры organic_components, которые действительно тестируют API, а не дублируют тесты сервисного слоя.
