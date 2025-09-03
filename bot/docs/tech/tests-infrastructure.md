# 🧪 Инфраструктура тестирования Amanita Bot

## 📋 **Обзор**

Инфраструктура тестирования Amanita Bot представляет собой многоуровневую систему, которая обеспечивает изоляцию тестов, гибкость в выборе режимов тестирования и соответствие принципам TDD. Система поддерживает как unit-тесты с полным мокированием, так и integration-тесты с реальными сервисами.

---

## 🏗️ **Архитектура тестирования**

### **1. Многоуровневая структура**

```
┌─────────────────────────────────────────────────────────────┐
│                    Тестовые файлы                          │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   Unit Tests    │  │      Integration Tests          │  │
│  │                 │  │                                 │  │
│  │ • test_*.py     │  │ • test_*_integration.py         │  │
│  │ • Mock-based    │  │ • Real/Mock hybrid              │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Централизованные фикстуры                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   conftest.py                          │ │
│  │                                                         │ │
│  │ • MockBlockchainService                                │ │
│  │ • MockIPFSStorage                                      │ │
│  │ • MockValidationService                                │ │
│  │ • MockAccountService                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Реальные сервисы                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • BlockchainService                                    │ │
│  │ • ProductValidationService                             │ │
│  │ • AccountService                                       │ │
│  │ • Storage Services (Pinata/ArWeave)                    │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### **2. Принципы проектирования**

- **Изоляция тестов**: Каждый тест независим от внешних зависимостей
- **Гибкость режимов**: Переключение между mock и real сервисами
- **Централизация моков**: Все моки определены в conftest.py
- **TDD соответствие**: Поддержка Red → Green → Refactor цикла
- **DevOps интеграция**: Логирование и метрики для CI/CD

---

## 🔧 **Mock архитектура**

### **1. MockBlockchainService**

#### **Основные возможности:**
```python
class MockBlockchainService:
    def __init__(self):
        self.create_product_called = False
        self.seller_key = "0x1234567890abcdef..."
        self._next_blockchain_id = 1
        self.product_statuses = {}
        self.product_cids = {}
        self.storage_service = None
```

#### **Ключевые методы:**
- **`get_catalog_version()`** - возвращает фиктивную версию каталога
- **`get_all_products()`** - возвращает список из 9 тестовых продуктов
- **`create_product(ipfs_cid)`** - имитирует создание продукта в блокчейне
- **`update_product_status()`** - обновляет статус продукта
- **`get_product_id_from_tx()`** - возвращает динамический ID из транзакции

#### **Особенности реализации:**
```python
def _generate_next_blockchain_id(self):
    """Генерирует следующий уникальный blockchain ID"""
    next_id = self._next_blockchain_id
    self._next_blockchain_id += 1
    return next_id

def _reset_state(self):
    """Сброс состояния для изоляции тестов"""
    self.create_product_called = False
    self._next_blockchain_id = 1
    self.product_statuses.clear()
    self.product_cids.clear()
    self._initialize_test_data()
```

### **2. MockIPFSStorage**

#### **Основные возможности:**
- Эмуляция IPFS операций без реальных API вызовов
- Синхронизация с MockBlockchainService
- Возврат предопределенных тестовых данных
- Поддержка upload_json и download_json операций

#### **Интеграция с блокчейном:**
```python
def sync_with_blockchain_service(self, blockchain_service):
    """Синхронизация с MockBlockchainService"""
    self.blockchain_service = blockchain_service
    # Синхронизация тестовых данных
```

### **3. MockValidationService**

#### **Основные возможности:**
- Эмуляция валидации продуктов
- Настраиваемые результаты валидации
- Поддержка как успешных, так и неуспешных сценариев
- Async/await совместимость

#### **Пример использования:**
```python
mock_validation_service = Mock()
mock_validation_service.validate_product_data = AsyncMock(
    return_value=ValidationResult(is_valid=True, error_message=None)
)
```

### **4. MockAccountService**

#### **Основные возможности:**
- Эмуляция аккаунтных операций
- Предоставление тестовых приватных ключей
- Поддержка адресов кошельков
- Интеграция с MockBlockchainService

---

## 📁 **Структура тестовых файлов**

### **1. Unit тесты (test_product_registry_unit.py)**

#### **Характеристики:**
- **Полное мокирование**: Все внешние зависимости заменены моками
- **Быстрое выполнение**: Нет реальных API вызовов
- **Изоляция**: Каждый тест независим от других
- **TDD подход**: Тесты написаны до реализации

#### **Пример структуры:**
```python
@pytest.mark.asyncio
async def test_update_product_success():
    """Тест успешного обновления продукта"""
    # Arrange: Создаем моки напрямую
    mock_blockchain_service = Mock()
    mock_storage_service = Mock()
    mock_validation_service = Mock()
    mock_account_service = Mock()
    
    # Настраиваем моки
    mock_validation_service.validate_product_data = AsyncMock(
        return_value=ValidationResult(is_valid=True, error_message=None)
    )
    
    # Act: Создаем сервис с моками
    registry_service = ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_storage_service,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )
    
    # Assert: Проверяем результат
    result = await registry_service.update_product("1", update_data)
    assert result["status"] == "success"
```

### **2. Integration тесты (test_product_registry_integration.py)**

#### **Характеристики:**
- **Гибридный подход**: Поддержка как mock, так и real сервисов
- **Режимы тестирования**: Переключение через переменные окружения
- **Реальные сценарии**: Тестирование полного жизненного цикла
- **DevOps интеграция**: Детальное логирование и метрики

#### **Режимы тестирования:**
```python
# Mock режим (быстро, экономично)
@pytest_asyncio.fixture
async def integration_registry_service_mock(
    mock_blockchain_service,
    mock_ipfs_storage,
    mock_validation_service,
    mock_account_service
):
    """Быстрое тестирование с Mock архитектурой"""
    return ProductRegistryService(
        blockchain_service=mock_blockchain_service,
        storage_service=mock_ipfs_storage,
        validation_service=mock_validation_service,
        account_service=mock_account_service
    )

# Real режим (полное тестирование)
@pytest_asyncio.fixture
async def integration_registry_service_real(
    integration_storage_config
):
    """Полное тестирование с реальными сервисами"""
    blockchain_service = BlockchainService()
    validation_service = ProductValidationService()
    account_service = AccountService(blockchain_service)
    
    return ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=integration_storage_config["service"],
        validation_service=validation_service,
        account_service=account_service
    )
```

---

## 🎯 **Фикстуры и их назначение**

### **1. Основные фикстуры**

#### **`mock_blockchain_service`**
- **Назначение**: Эмуляция блокчейн операций
- **Область применения**: Unit и integration тесты
- **Особенности**: Динамическая генерация ID, отслеживание состояния

#### **`mock_ipfs_storage`**
- **Назначение**: Эмуляция IPFS/ArWeave операций
- **Область применения**: Unit и integration тесты
- **Особенности**: Синхронизация с блокчейн сервисом

#### **`mock_validation_service`**
- **Назначение**: Эмуляция валидации продуктов
- **Область применения**: Unit и integration тесты
- **Особенности**: Настраиваемые результаты валидации

#### **`mock_account_service`**
- **Назначение**: Эмуляция аккаунтных операций
- **Область применения**: Unit и integration тесты
- **Особенности**: Предоставление тестовых ключей

### **2. Специализированные фикстуры**

#### **`integration_storage_config`**
- **Назначение**: Конфигурация storage для integration тестов
- **Режимы**: mock, pinata, arweave
- **Переключение**: Через переменную окружения `INTEGRATION_STORAGE`

#### **`integration_test_data`**
- **Назначение**: Загрузка тестовых данных из JSON файлов
- **Источник**: `tests/fixtures/products.json`
- **Содержание**: Валидные и невалидные продукты

---

## 🔄 **Режимы тестирования**

### **1. Mock режим (по умолчанию)**

#### **Характеристики:**
- **Производительность**: Быстрое выполнение
- **Стоимость**: Бесплатно (нет API вызовов)
- **Изоляция**: Полная независимость от внешних сервисов
- **Применение**: Unit тесты, быстрые integration тесты

#### **Настройка:**
```bash
export INTEGRATION_STORAGE=mock
# или не устанавливать переменную (по умолчанию)
```

### **2. Pinata режим**

#### **Характеристики:**
- **Производительность**: Медленное выполнение (реальные API)
- **Стоимость**: Тратит бюджет Pinata
- **Реализм**: Тестирование реальных IPFS операций
- **Применение**: Полные integration тесты

#### **Настройка:**
```bash
export INTEGRATION_STORAGE=pinata
export PINATA_API_KEY=your_key
export PINATA_API_SECRET=your_secret
```

### **3. ArWeave режим**

#### **Характеристики:**
- **Производительность**: Медленное выполнение (реальные API)
- **Стоимость**: Тратит баланс ArWeave
- **Реализм**: Тестирование реальных ArWeave операций
- **Применение**: Полные integration тесты

#### **Настройка:**
```bash
export INTEGRATION_STORAGE=arweave
export ARWEAVE_PRIVATE_KEY=your_key
```

---

## 🧪 **Примеры использования**

### **1. Создание unit теста**

```python
@pytest.mark.asyncio
async def test_create_product_success():
    """Тест успешного создания продукта"""
    # Arrange: Используем фикстуры из conftest.py
    mock_blockchain = Mock()
    mock_blockchain.create_product = AsyncMock(return_value="0x123")
    mock_blockchain.get_product_id_from_tx = AsyncMock(return_value=42)
    
    mock_storage = Mock()
    mock_storage.upload_json = AsyncMock(return_value="QmMockCID")
    
    mock_validation = Mock()
    mock_validation.validate_product_data = AsyncMock(
        return_value=ValidationResult(is_valid=True, error_message=None)
    )
    
    # Act: Создаем сервис с моками
    registry_service = ProductRegistryService(
        blockchain_service=mock_blockchain,
        storage_service=mock_storage,
        validation_service=mock_validation
    )
    
    # Assert: Проверяем результат
    result = await registry_service.create_product(product_data)
    assert result["status"] == "success"
```

### **2. Создание integration теста**

```python
@pytest.mark.asyncio
async def test_integration_product_lifecycle(
    integration_registry_service_mock,  # Используем mock фикстуру
    integration_test_data
):
    """Тест полного жизненного цикла продукта"""
    # Arrange: Получаем тестовые данные
    product_data = integration_test_data["valid_products"][0]
    
    # Act: Создаем продукт
    create_result = await integration_registry_service_mock.create_product(product_data)
    assert create_result["status"] == "success"
    
    # Act: Получаем продукт
    product = await integration_registry_service_mock.get_product(1)
    assert product is not None
    
    # Act: Обновляем статус
    update_result = await integration_registry_service_mock.update_product_status(1, 1)
    assert update_result is True
```

---

## 🔍 **Отладка и диагностика**

### **1. Логирование**

#### **Настройка логирования:**
```python
# Настройка логирования для тестов
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)
```

#### **DevOps логирование:**
```python
logger.info("🔧 [DEVOPS] Mock режим: быстро, экономично, без реальных API вызовов")
logger.info("⚡ [DEVOPS] Готов к быстрому тестированию с mock сервисами")
logger.info(f"📊 [DEVOPS] Storage детали: type={devops_info['type']}, performance={devops_info['performance']}")
```

### **2. Диагностика моков**

#### **Проверка вызовов:**
```python
# Проверяем, что метод был вызван
mock_validation_service.validate_product_data.assert_called_once_with(product_data)

# Проверяем количество вызовов
assert mock_storage.upload_json.call_count == 2

# Проверяем параметры вызова
mock_blockchain.create_product.assert_called_once_with("QmMockCID")
```

#### **Отслеживание состояния:**
```python
# Проверяем внутреннее состояние мока
assert mock_blockchain_service.create_product_called
assert mock_blockchain_service.product_statuses[1] is True
```

---

## 🚀 **Лучшие практики**

### **1. Создание моков**

#### **Прямое создание (для простых случаев):**
```python
mock_service = Mock()
mock_service.method = Mock(return_value="expected_value")
```

#### **Использование фикстур (для сложных случаев):**
```python
def test_with_fixtures(mock_blockchain_service, mock_ipfs_storage):
    # Фикстуры автоматически предоставляют настроенные моки
    pass
```

### **2. Настройка поведения моков**

#### **Простой возврат значения:**
```python
mock_service.method = Mock(return_value="result")
```

#### **Async методы:**
```python
mock_service.async_method = AsyncMock(return_value="async_result")
```

#### **Условное поведение:**
```python
mock_service.method = Mock(side_effect=[
    "first_call",
    "second_call",
    Exception("error")
])
```

### **3. Проверка взаимодействий**

#### **Проверка вызовов:**
```python
# Метод был вызван
mock_service.method.assert_called()

# Метод был вызван один раз
mock_service.method.assert_called_once()

# Метод был вызван с определенными параметрами
mock_service.method.assert_called_with("param1", "param2")

# Метод был вызван определенное количество раз
assert mock_service.method.call_count == 3
```

---

## 📊 **Метрики и производительность**

### **1. Время выполнения**

#### **Mock режим:**
- **Unit тесты**: <100ms на тест
- **Integration тесты**: <500ms на тест
- **Общее время**: <5 минут для всего набора

#### **Real режим:**
- **Integration тесты**: 2-10 секунд на тест
- **Общее время**: 10-30 минут для всего набора

### **2. Стоимость тестирования**

#### **Mock режим:**
- **API вызовы**: 0
- **Стоимость**: Бесплатно
- **Бюджет**: Не тратится

#### **Real режим:**
- **API вызовы**: 1-10 на тест
- **Стоимость**: Зависит от провайдера
- **Бюджет**: Тратится при каждом запуске

---

## 🔧 **Конфигурация и настройка**

### **1. Переменные окружения**

#### **Обязательные:**
```bash
export SELLER_PRIVATE_KEY="0x1234567890abcdef..."
export AMANITA_REGISTRY_CONTRACT_ADDRESS="0xabcdef1234567890..."
```

#### **Опциональные:**
```bash
# Режим storage для integration тестов
export INTEGRATION_STORAGE="mock"  # mock, pinata, arweave

# API ключи для реальных сервисов
export PINATA_API_KEY="your_pinata_key"
export PINATA_API_SECRET="your_pinata_secret"
export ARWEAVE_PRIVATE_KEY="your_arweave_key"
```

### **2. Конфигурация pytest**

#### **pytest.ini:**
```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

#### **conftest.py:**
```python
# Автоматическая регистрация pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Глобальные фикстуры
@pytest.fixture(autouse=True)
def setup_test_logging():
    # Автоматическая настройка логирования
    pass
```

---

## 🎯 **Заключение**

Инфраструктура тестирования Amanita Bot обеспечивает:

1. **Гибкость**: Переключение между mock и real режимами
2. **Изоляцию**: Полная независимость тестов от внешних зависимостей
3. **Производительность**: Быстрое выполнение в mock режиме
4. **Реализм**: Полное тестирование в real режиме
5. **TDD соответствие**: Поддержка принципов Test-Driven Development
6. **DevOps интеграция**: Детальное логирование и метрики

Система позволяет разработчикам выбирать подходящий уровень тестирования в зависимости от задач: быстрые unit тесты для разработки и полные integration тесты для валидации перед деплоем.
