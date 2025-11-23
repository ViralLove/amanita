# Структура продукта в Amanita

## Обзор

В системе Amanita продукт имеет два ключевых идентификатора:
- **`business_id`** - бизнес-логический идентификатор (строка)
- **`blockchain_id`** - числовой идентификатор в блокчейне (uint256)

## Business ID (`business_id`)

### Определение
`business_id` - это строковый идентификатор продукта, который используется в бизнес-логике приложения. Это человекочитаемый ID, который может содержать буквы, цифры и специальные символы.

### Логика получения
1. **Создание**: `business_id` задается при создании продукта в поле `id` входных данных
2. **Валидация**: Проверяется уникальность через `_check_product_id_exists()`
3. **Хранение**: Сохраняется в метаданных продукта в IPFS

### Назначение
- Уникальная идентификация продукта в бизнес-логике
- Используется для поиска и фильтрации продуктов
- Связывает продукт с внешними системами (каталоги, заказы)
- Человекочитаемый формат для администраторов и пользователей

### Жизненный цикл
```
Создание продукта → Валидация уникальности → Сохранение в метаданных → Использование в API
```

На уровне контракта `ProductRegistryLogic` уникальность поддерживается через маппинг `businessIdToProductId`. При вызове `createProduct` проверяется, что `businessIdToProductId[businessId] == 0`, иначе выбрасывается `BusinessIdExists`. Это гарантирует, что бизнес-идентификатор остаётся глобально уникальным и быстро разрешается в on-chain `productId`.

## Blockchain ID (`blockchain_id`)

### Определение
`blockchain_id` - это числовой идентификатор продукта в смарт-контракте ProductRegistry. Это автоматически генерируемый uint256, который присваивается при записи в блокчейн.

### Логика получения
1. **Подготовка данных**: формируется `metadataCID` с метаданными продукта без дублирования компонентов.
2. **Формирование `componentIds[]`**: из метаданных собираются `component_id`/`organic_components[].component_id`, соответствующие бизнес-id в `OrganicComponentRegistry`.
3. **Запись в блокчейн**: вызывается `createProduct(businessId, componentIds, metadataCID)` на смарт-контракте `ProductRegistryLogic`.
4. **Генерация ID**: контракт увеличивает `_productIdCounter`, сохраняет `businessId`, `componentIds` и `metadataCID`, затем возвращает `productId`.
5. **Извлечение из транзакции**: через событие `ProductCreated` или `getProductIdByBusinessId`.
6. **Проверка существования**: вызывается `getProduct(productId)` либо `businessIdToProductId[businessId]` для валидации и чтения статуса.

### Назначение
- Уникальная идентификация продукта в блокчейне
- Используется для вызова функций смарт-контракта (активация, деактивация, обновление)
- Связывает метаданные IPFS с записью в блокчейне
- Обеспечивает неизменность и прозрачность

### Жизненный цикл
```
Создание метаданных → Загрузка в IPFS → Запись в блокчейн → Получение blockchain_id → Валидация → Использование
```

## Связь между идентификаторами

### Создание продукта
```python
# 1. Создание метаданных с business_id
metadata = {
    "id": "amanita_muscaria_powder_100g",  # business_id
    "title": "Amanita Muscaria Powder 100g",
    # ... другие поля
}

# 2. Загрузка в IPFS
metadata_cid = await storage_service.upload_json(metadata)

# 3. Сбор componentIds
component_ids = metadata_utils.collect_component_ids(metadata)

# 4. Запись в блокчейн
tx_hash = await blockchain_service.create_product(
    business_id=metadata["id"],
    component_ids=component_ids,
    metadata_cid=metadata_cid
)

# 5. Получение blockchain_id
blockchain_id = await blockchain_service.get_product_id_from_tx(tx_hash)
```

### Структура в блокчейне
```solidity
// contracts/interfaces/IProductRegistry.sol
struct Product {
    uint256 id;            // blockchain_id
    address seller;        // адрес продавца
    string businessId;     // бизнес-идентификатор продукта
    string[] componentIds; // бизнес-id компонентов из OrganicComponentRegistry
    string metadataCID;    // CID метаданных без вложенных компонентов
    bool active;           // статус активности
}
```

> ⚠️ `businessId` и `componentIds` теперь являются on-chain источником правды. Метаданные в Arweave/Pinata содержат только ссылки на компоненты, а обогащение выполняется на backend через `ComponentService`.

### Событие ProductCreated
```solidity
event ProductCreated(
    address indexed seller,
    uint256 productId,
    string businessId,
    string[] componentIds,
    string metadataCID,
    uint256 status // 0 - неактивный, 1 - активный
);
```

Событие сразу содержит `businessId` и набор `componentIds`, поэтому фронтенд/бот может синхронизировать все идентификаторы сразу после майнинга транзакции.

### Индексация `businessId`
```solidity
mapping(string => uint256) public businessIdToProductId;

function getProductIdByBusinessId(string calldata businessId)
    external
    view
    returns (uint256 productId);
```

Контракт поддерживает двунаправленное соответствие:
- `businessIdToProductId[businessId]` возвращает `productId` или ревертит `BusinessIdUnknown`.
- `getProductComponents(productId)` отдаёт точный массив `componentIds`.
- `_validateComponents(componentIds)` проверяет наличие компонентов в `componentRegistry`.

## Валидация и проверки

### Business ID
- Проверка уникальности в системе
- Валидация формата и длины
- Проверка на запрещенные символы

### Blockchain ID
- Проверка существования в смарт-контракте
- Валидация через `getProduct(blockchain_id)`
- Проверка статуса активности

## Использование в API

### Создание продукта
```javascript
const metadata = buildProductMetadata(payload);  // содержит ссылки на component_id
const metadataCID = await storage.uploadJson(metadata);
const componentIds = extractComponentIds(metadata); // ['blue_lotus', 'passionflower']

const tx = await productRegistry
  .connect(sellerSigner)
  .createProduct(metadata.id, componentIds, metadataCID);

const receipt = await tx.wait();
const productId = receipt.logs[0].args.productId;
```

```python
# backend-поток (service layer)
metadata = registry_service.create_product_metadata(product_data)
metadata_cid = storage_service.upload_json(metadata)
component_ids = metadata_utils.collect_component_ids(metadata)

tx_hash = await blockchain_service.create_product(
    business_id=metadata["id"],
    component_ids=component_ids,
    metadata_cid=metadata_cid
)

return {
    "business_id": metadata["id"],
    "blockchain_id": blockchain_service.get_product_id_from_tx(tx_hash),
    "metadata_cid": metadata_cid,
    "tx_hash": tx_hash
}
```

### Получение продукта
```python
# По business_id
product = registry.get_product("amanita_muscaria_powder_100g")

# По blockchain_id (через блокчейн)
product_data = blockchain_service.get_product(123)
```

### Обновление статуса
```python
# Используется blockchain_id
await blockchain_service.set_product_active(
    private_key, 
    blockchain_id=123, 
    is_active=True
)
```

## Кэширование и производительность

### Кэш метаданных
- Метаданные кэшируются по IPFS CID
- Время жизни: 24 часа для описаний, 12 часов для изображений
- Автоматическая инвалидация при обновлении

### Кэш каталога
- Список продуктов кэшируется на 5 минут
- Версия каталога отслеживается в блокчейне
- Автоматическое обновление при изменениях

## Обработка ошибок

### Business ID конфликты
- Проверка уникальности перед созданием
- Возврат ошибки с описанием конфликта
- Возможность изменения ID пользователем

### Blockchain ID ошибки
- Проверка существования после создания
- Логирование предупреждений при расхождениях
- Повторные попытки получения ID из транзакции

## Безопасность

### Валидация входных данных
- Проверка CID через регулярные выражения
- Валидация обязательных полей
- Санитизация пользовательского ввода

### Контроль доступа
- Проверка активации пользователя через InviteNFT
- Проверка прав продавца на продукт
- Аудит всех операций через события блокчейна
