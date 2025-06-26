# Архитектура сервисов бота

## Общая структура

Архитектура сервисов построена по принципу слоев с четким разделением ответственности. Основные слои:

1. Базовые сервисы (Core Services)
2. Доменные сервисы (Domain Services)
3. Вспомогательные сервисы (Support Services)

### Базовые сервисы

#### BlockchainService
- Синглтон для работы с блокчейном
- Инициализирует подключение к сети
- Загружает и кэширует контракты
- Предоставляет базовые операции с блокчейном

#### IPFSFactory
- Фабрика для создания IPFS клиентов
- Обеспечивает единую точку конфигурации IPFS
- Поддерживает разные провайдеры (Pinata, локальный IPFS и т.д.)

### Доменные сервисы

#### ProductRegistryService
- Основной сервис для работы с продуктами
- Координирует работу всех подсервисов
- Реализует бизнес-логику управления продуктами
- Зависит от:
  * BlockchainService
  * ProductStorageService
  * ProductValidationService
  * ProductCacheService
  * ProductMetadataService

### Вспомогательные сервисы

#### ProductStorageService
- Отвечает за хранение файлов и метаданных
- Использует IPFSFactory для работы с IPFS
- Не имеет зависимостей от других сервисов

#### ProductMetadataService
- Управляет метаданными продуктов
- Зависит только от ProductStorageService
- Отвечает за форматирование и валидацию метаданных

#### ProductCacheService
- Реализует кэширование данных
- Не имеет зависимостей от других сервисов
- Использует локальное хранилище

#### ProductValidationService
- Отвечает за валидацию данных продуктов
- Не имеет зависимостей от других сервисов
- Содержит правила валидации

## Принципы инициализации

1. Базовые сервисы инициализируются первыми:
```python
blockchain_service = BlockchainService()
ipfs_factory = IPFSFactory()
```

2. Создание вспомогательных сервисов:
```python
storage_service = ProductStorageService(ipfs_factory)
validation_service = ProductValidationService()
cache_service = ProductCacheService()
metadata_service = ProductMetadataService(storage_service)
```

3. Инициализация основного сервиса:
```python
product_registry = ProductRegistryService(
    blockchain_service=blockchain_service,
    storage_service=storage_service,
    validation_service=validation_service
)
```

## Правила и принципы

1. **Единая ответственность**: Каждый сервис отвечает за конкретную область функциональности

2. **Инверсия зависимостей**: Сервисы получают зависимости через конструктор

3. **Отсутствие циклических зависимостей**: Сервисы организованы в направленный ациклический граф

4. **Изоляция слоев**: Каждый слой взаимодействует только с соседними слоями

5. **Кэширование и переиспользование**: Базовые сервисы создаются один раз и переиспользуются

6. **Чистота и безопасность**:
   - Явные зависимости
   - Отсутствие глобального состояния
   - Безопасная инициализация
   - Корректная обработка ошибок

## Тестирование

1. **Модульные тесты**: Каждый сервис тестируется изолированно с моками зависимостей

2. **Интеграционные тесты**: Проверяют взаимодействие между сервисами

3. **Фикстуры**: Предоставляют готовые инстансы сервисов для тестов:
```python
@pytest.fixture
def product_registry(blockchain_service, storage_service, validation_service):
    return ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service
    )
``` 