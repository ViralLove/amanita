# 🏗️ Dependency Injection Architecture в Amanita

## 📋 Обзор

Документ описывает архитектуру dependency injection (DI) в проекте Amanita, включая принципы, реализацию и лучшие практики для тестирования.

## 🎯 Принципы архитектуры

### 1. Централизованное управление зависимостями
- Все зависимости управляются через `bot/dependencies.py`
- API-специфичные зависимости в `bot/api/dependencies.py`
- ServiceFactory для создания сервисов с зависимостями

### 2. Инверсия зависимостей
- Сервисы не создают зависимости самостоятельно
- Зависимости передаются извне через конструктор
- Легко подменять зависимости для тестирования

### 3. Единая точка конфигурации
- Все сервисы создаются через dependency providers
- Конфигурация вынесена в отдельные модули
- Легко переключать между реальными и тестовыми зависимостями

## 🏛️ Структура архитектуры

```
bot/
├── dependencies.py              # Общие dependency providers
├── api/
│   └── dependencies.py         # FastAPI-specific DI
├── services/
│   ├── service_factory.py      # Фабрика сервисов
│   ├── core/                   # Базовые сервисы
│   └── product/                # Сервисы продуктов
└── tests/
    └── conftest.py             # Тестовые фикстуры
```

## 🔧 Ключевые компоненты

### 1. Общий модуль зависимостей (`bot/dependencies.py`)

```python
def get_product_registry_service(
    blockchain_service: BlockchainService = None,
    storage_service: ProductStorageService = None,
    validation_service: ProductValidationService = None,
    account_service: AccountService = None,
) -> ProductRegistryService:
    """Dependency provider для ProductRegistryService"""
    if blockchain_service is None:
        blockchain_service = get_blockchain_service()
    if storage_service is None:
        storage_service = get_product_storage_service()
    # ... остальные зависимости
    
    return ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
```

**Особенности:**
- Все параметры опциональны
- Автоматическое создание зависимостей по умолчанию
- Возможность переопределения любой зависимости

### 2. FastAPI DI (`bot/api/dependencies.py`)

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

**Особенности:**
- Интеграция с FastAPI `Depends()`
- Автоматическое разрешение зависимостей
- Ленивая загрузка сервисов

### 3. ServiceFactory (`bot/services/service_factory.py`)

```python
class ServiceFactory:
    def __init__(self):
        self.blockchain = BlockchainService()  # Синглтон
    
    def create_product_registry_service(self):
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

**Особенности:**
- Централизованное создание сервисов
- Управление жизненным циклом зависимостей
- Синглтоны для тяжелых сервисов (blockchain)

## 🧪 Стратегии тестирования

### 1. Использование существующего DI

**❌ НЕПРАВИЛЬНО - создавать синхронную версию:**
```python
class ProductRegistryServiceSync(ProductRegistryService):
    # Дублирование кода - антипаттерн!
    pass
```

**✅ ПРАВИЛЬНО - использовать существующий DI с моками:**
```python
@pytest.fixture
def mock_registry_service():
    """Используем существующий DI с моками"""
    from bot.dependencies import get_product_registry_service
    
    # Создаем моки
    mock_blockchain = Mock()
    mock_storage = Mock()
    mock_validation = Mock()
    mock_account = Mock()
    
    # Используем существующий DI с моками
    return get_product_registry_service(
        blockchain_service=mock_blockchain,
        storage_service=mock_storage,
        validation_service=mock_validation,
        account_service=mock_account
    )
```

### 2. Правильное мокирование

**❌ НЕПРАВИЛЬНО - AsyncMock без return_value:**
```python
mock_storage_service = AsyncMock()
# Это создает корутину, которую нужно await
```

**✅ ПРАВИЛЬНО - Mock с return_value:**
```python
mock_storage_service = Mock()
mock_storage_service.download_json = Mock(return_value=mock_data)
mock_storage_service.upload_json = Mock(return_value="QmMockCID")

# Для асинхронных методов, если нужно
mock_storage_service.upload_json_async = AsyncMock(return_value="QmMockCID")
```

### 3. Фикстуры в conftest.py

```python
@pytest.fixture
def mock_blockchain_service(monkeypatch):
    """Мок для BlockchainService"""
    class MockBlockchainService:
        def get_catalog_version(self):
            return 1
        
        def get_all_products(self):
            return [(1, "0x123", "QmCID", True)]
        
        async def create_product(self, ipfs_cid):
            return "0x123"
    
    # Подменяем через monkeypatch
    monkeypatch.setattr(blockchain, "BlockchainService", MockBlockchainService)
    return MockBlockchainService()
```

## 🚀 Лучшие практики

### 1. Создание новых сервисов

```python
# 1. Определить зависимости в конструкторе
class NewService:
    def __init__(self, dependency1, dependency2):
        self.dependency1 = dependency1
        self.dependency2 = dependency2

# 2. Добавить в dependencies.py
def get_new_service(
    dependency1: Dependency1 = None,
    dependency2: Dependency2 = None,
) -> NewService:
    if dependency1 is None:
        dependency1 = get_dependency1()
    if dependency2 is None:
        dependency2 = get_dependency2()
    
    return NewService(dependency1, dependency2)

# 3. Добавить в ServiceFactory
def create_new_service(self):
    dependency1 = self.get_dependency1()
    dependency2 = self.get_dependency2()
    return NewService(dependency1, dependency2)
```

### 2. Тестирование новых сервисов

```python
@pytest.fixture
def mock_new_service():
    """Используем существующий DI с моками"""
    from bot.dependencies import get_new_service
    
    mock_dep1 = Mock()
    mock_dep2 = Mock()
    
    return get_new_service(
        dependency1=mock_dep1,
        dependency2=mock_dep2
    )

def test_new_service(mock_new_service):
    # Тестируем с замоканными зависимостями
    assert mock_new_service.dependency1 is not None
    assert mock_new_service.dependency2 is not None
```

## 🔍 Решение проблем

### 1. Медленные тесты

**Симптомы:**
- Тесты выполняются долго (>1 минуты)
- `RuntimeWarning: coroutine was never awaited`
- Тесты "зависают"

**Решение:**
```python
# 1. Проверить pytest.ini
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# 2. Использовать Mock вместо AsyncMock где возможно
mock_service = Mock()
mock_service.method = Mock(return_value=result)

# 3. Для асинхронных методов использовать return_value
mock_service.async_method = AsyncMock(return_value=result)
```

### 2. Проблемы с зависимостями

**Симптомы:**
- `ImportError` в тестах
- Сервисы не получают зависимости
- Циклические зависимости

**Решение:**
```python
# 1. Использовать monkeypatch для подмены модулей
monkeypatch.setattr(module, "Service", MockService)

# 2. Создавать моки в conftest.py
@pytest.fixture
def mock_service(monkeypatch):
    # Подмена через monkeypatch
    pass

# 3. Использовать существующий DI
from bot.dependencies import get_service
return get_service(mock_dependency)
```

## 📚 Примеры использования

### 1. Тест ProductRegistryService

```python
def test_create_product_success(mock_registry_service):
    """Тест создания продукта с замоканными зависимостями"""
    product_data = {
        "title": "Test Product",
        "description": "Test Description"
    }
    
    result = await mock_registry_service.create_product(product_data)
    
    assert result["success"] is True
    assert "product_id" in result
```

### 2. Тест с кастомными моками

```python
def test_storage_error_handling(mock_registry_service):
    """Тест обработки ошибок хранилища"""
    # Настраиваем мок для симуляции ошибки
    mock_registry_service.storage_service.upload_json = Mock(return_value=None)
    
    result = await mock_registry_service.create_product(product_data)
    
    assert result["success"] is False
    assert "error" in result
```

## 🎯 Ключевые выводы

1. **НЕ создавать синхронные версии сервисов** - это антипаттерн
2. **Использовать существующий DI** - он уже реализован правильно
3. **Мокать зависимости, а не сервисы** - через dependency injection
4. **Централизовать моки** - в conftest.py для переиспользования
5. **Использовать Mock вместо AsyncMock** где возможно

## 🔗 Связанные документы

- [API Architecture](./api.md)
- [Testing Strategy](./tests/)
- [Service Layer Design](./service-layer.md)
- [FastAPI Integration](./fastapi-integration.md)

---

*Документ обновлен: $(date)*
*Версия: 1.0*
