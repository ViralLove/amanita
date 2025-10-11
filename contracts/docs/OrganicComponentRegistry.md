# 🌿 OrganicComponentRegistry - Документация

## 📋 Оглавление

1. [Обзор](#обзор)
2. [Ключевые концепции](#ключевые-концепции)
3. [Архитектура UUPS](#архитектура-uups)
4. [Роли и права доступа](#роли-и-права-доступа)
5. [Структуры данных](#структуры-данных)
6. [Основной функционал](#основной-функционал)
7. [Shareable данные](#shareable-данные)
8. [Интеграции с экосистемой](#интеграции-с-экосистемой)
9. [Безопасность](#безопасность)
10. [Газовые оптимизации](#газовые-оптимизации)
11. [Примеры использования](#примеры-использования)
12. [Технические спецификации](#технические-спецификации)

---

## 🎯 Обзор

### Назначение

**OrganicComponentRegistry** - это смарт-контракт для управления библиотекой органических компонентов (ингредиентов, сырья), управляемой сообществом. Контракт служит **единым источником правды** для всех компонентов, которые могут быть использованы в продуктах каталога Amanita.

### Ключевые особенности

- ✅ **Decentralized Registry** - распределённая библиотека компонентов
- ✅ **Community-Driven** - управление через роли и права доступа
- ✅ **Shareable Components** - компоненты доступны всем для составления продуктов
- ✅ **IPFS Integration** - хранение метаданных в IPFS
- ✅ **Usage Tracking** - отслеживание использования компонентов
- ✅ **Upgradeable (UUPS)** - возможность обновления без потери данных
- ✅ **Gas Optimized** - оптимизации для экономии газа

### Версия

- **Версия контракта:** 3.0.0
- **Паттерн:** UUPS (Universal Upgradeable Proxy Standard)
- **Solidity:** ^0.8.22
- **OpenZeppelin:** v5.x (Upgradeable contracts)

---

## 🔑 Ключевые концепции

### Что такое Organic Component?

**Organic Component (Органический компонент)** - это базовый элемент системы, представляющий:
- **Ингредиент/Сырьё** (например, "Amanita Muscaria", "Chaga", "Lion's Mane")
- **Конкретная форма** определяется через shared словарь `component_forms` (Powder, Tincture, Capsules)
- **Характеристики** определяются через shared словарь `features` (Organic, Wildcrafted, Lab-tested)

**Важно:** Компонент обычно включает в businessId форму (например, `amanita_muscaria_powder`), но features выбираются из централизованного словаря.

### Зачем нужен реестр?

1. **Стандартизация** - единая терминология для всей экосистемы
2. **Переиспользование** - один раз создан → используется везде
3. **Управление сообществом** - contributors могут добавлять новые компоненты
4. **Аналитика** - отслеживание популярности компонентов
5. **Валидация** - ProductRegistry проверяет компоненты через этот контракт

### Жизненный цикл компонента

```
┌──────────────┐
│   СОЗДАНИЕ   │  Contributor создаёт компонент
│  (PENDING)   │  с уникальным business_id
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  АКТИВАЦИЯ   │  Admin/Validator одобряет
│   (ACTIVE)   │  Компонент доступен для использования
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ ИСПОЛЬЗОВАНИЕ│  ProductRegistry использует в продуктах
│   + TRACKING │  Счётчик использования увеличивается
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ОБНОВЛЕНИЕ  │  Creator обновляет метаданные (optional)
│  (VERSIONED) │  История изменений сохраняется
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  АРХИВАЦИЯ   │  При необходимости (optional)
│  (ARCHIVED)  │  Компонент больше не используется
└──────────────┘
```

---

## 🏗️ Архитектура UUPS

### Что такое UUPS?

**UUPS (Universal Upgradeable Proxy Standard)** - это паттерн proxy контракта, где:
- **Proxy** - минимальная обёртка, хранит данные и делегирует вызовы
- **Logic** - содержит всю бизнес-логику, может быть обновлён
- **Storage** - физически хранится в Proxy через delegatecall

### Компоненты системы

```
┌─────────────────────────────────────────┐
│    OrganicComponentRegistryProxy        │
│    (Хранит данные, делегирует вызовы)   │
│                                          │
│  • totalComponents: 1000                 │
│  • components[1] = {...}                 │
│  • componentsByCreator[alice] = [1,2,3]  │
└────────────┬────────────────────────────┘
             │ delegatecall
             ▼
┌─────────────────────────────────────────┐
│   OrganicComponentRegistryLogic         │
│   (Бизнес-логика, может быть обновлена) │
│                                          │
│  • function createComponent()            │
│  • function updateComponent()            │
│  • function getComponentByBusinessId()   │
└──────────────────────────────────────────┘
```

### Преимущества UUPS

1. ✅ **Upgradeable** - можно обновлять логику без потери данных
2. ✅ **Gas Efficient** - меньше overhead чем Transparent Proxy
3. ✅ **Secure** - upgrade защищён через UPGRADER_ROLE
4. ✅ **State Preserved** - все данные сохраняются при обновлении
5. ✅ **OpenZeppelin Standard** - проверенная реализация

### Защита от прямых вызовов

- ⚠️ Вызовы **ТОЛЬКО** через Proxy
- ⚠️ Прямые вызовы на Logic контракт не имеют смысла (нет данных)
- ✅ Тесты подтверждают изоляцию implementation

---

## 👥 Роли и права доступа

### Иерархия ролей

```
DEFAULT_ADMIN_ROLE (OpenZeppelin)
    │
    ├─► ADMIN_ROLE
    │     │
    │     ├─► updateShareableData()
    │     ├─► setSpiralEngine()
    │     ├─► setAmanitaInternational()
    │     ├─► setProductRegistry()
    │     ├─► pause() / unpause()
    │     └─► grantRole() / revokeRole()
    │
    ├─► UPGRADER_ROLE
    │     │
    │     └─► upgradeToAndCall()
    │
    └─► CONTRIBUTOR_ROLE
          │
          ├─► createComponent()
          └─► updateComponent() (только свои)
```

### Детальное описание ролей

#### 1️⃣ DEFAULT_ADMIN_ROLE

**Описание:** Супер-администратор, управляющий всеми ролями

**Возможности:**
- ✅ Выдавать и отзывать любые роли
- ✅ Управлять системой ролей
- ✅ Передавать админские права

**Получение:** Автоматически при деплое (параметр `initialize(admin)`)

**Критичность:** 🔴 **МАКСИМАЛЬНАЯ** - полный контроль над системой

---

#### 2️⃣ ADMIN_ROLE

**Описание:** Администратор системы, управляющий конфигурацией

**Возможности:**
- ✅ Обновлять shareable данные (features, component forms)
- ✅ Настраивать интеграции (SpiralEngine, AmanitaInternational, ProductRegistry)
- ✅ Ставить контракт на паузу (emergency stop)
- ✅ Снимать контракт с паузы
- ✅ Управлять ролями contributors

**Не может:**
- ❌ Обновлять Logic контракт (только UPGRADER_ROLE)
- ❌ Удалять компоненты других пользователей
- ❌ Изменять creator компонентов

**Критичность:** 🟠 **ВЫСОКАЯ** - контроль над конфигурацией

---

#### 3️⃣ UPGRADER_ROLE

**Описание:** Роль для обновления Logic контракта

**Возможности:**
- ✅ Вызывать `upgradeToAndCall()` для обновления имплементации
- ✅ Мигрировать данные при необходимости

**Не может:**
- ❌ Изменять данные контракта напрямую
- ❌ Обходить механизмы валидации

**Критичность:** 🔴 **МАКСИМАЛЬНАЯ** - может изменить логику контракта

**Best Practice:** Выдавать только multisig или DAO governance контракту

---

#### 4️⃣ CONTRIBUTOR_ROLE

**Описание:** Участник сообщества, создающий компоненты

**Возможности:**
- ✅ Создавать новые компоненты (`createComponent()`)
- ✅ Обновлять свои компоненты (`updateComponent()`)
- ✅ Добавлять метаданные к своим компонентам

**Ограничения:**
- ❌ Максимум 100 компонентов на пользователя
- ❌ business_id должен быть уникальным
- ❌ Может редактировать только свои компоненты
- ❌ Должен быть активирован в SpiralEngine (onlyActivatedUser)
- ❌ Должен иметь SELLER_ROLE в SpiralEngine (onlySeller)

**Критичность:** 🟢 **НИЗКАЯ** - ограниченный доступ к созданию контента

**Получение:** Через admin или через автоматизированный процесс активации

---

### Модификаторы доступа

#### `onlyActivatedUser`

Проверяет, что пользователь активирован в SpiralEngine:
- Интеграция с `ISpiralEngine.isUserActivated(address)`
- Требуется для создания компонентов
- Защита от spam и неавторизованного доступа

#### `onlySeller`

Проверяет, что пользователь имеет SELLER_ROLE в SpiralEngine:
- Интеграция с `ISpiralEngine.hasRole(SELLER_ROLE, address)`
- Требуется для создания компонентов
- Дополнительный уровень валидации

#### `onlyComponentCreator(componentId)`

Проверяет, что вызывающий является создателем компонента:
- Сравнивает `msg.sender` с `components[componentId].creator`
- Используется в `updateComponent()`
- Защита от несанкционированных изменений

---

## 📦 Структуры данных

### Component (Компонент)

Основная структура, описывающая компонент:

```solidity
struct Component {
    uint256 blockchain_id;      // Уникальный ID в блокчейне
    address creator;             // Адрес создателя
    uint256 created_at;          // Timestamp создания
    uint256 last_updated;        // Timestamp последнего обновления
    ComponentStatus status;      // Статус (ACTIVE/PENDING/ARCHIVED)
    bool is_shared;             // Доступен ли для общего использования
}
```

**Поля:**

- **blockchain_id** - автоинкрементный ID (1, 2, 3, ...)
- **creator** - неизменяемый адрес создателя
- **created_at** - timestamp создания (`block.timestamp`)
- **last_updated** - обновляется при каждом `updateComponent()`
- **status** - текущий статус (по умолчанию `ACTIVE`)
- **is_shared** - флаг доступности (по умолчанию `true`)

---

### ComponentStatus (Статус)

Enum, описывающий состояние компонента:

```solidity
enum ComponentStatus {
    ACTIVE,      // Активен и доступен для использования
    PENDING,     // Создан, но требует проверки (заготовка)
    ARCHIVED     // Устарел или неактуален
}
```

**Использование:**

- **ACTIVE** - компонент полностью готов к использованию в продуктах
- **PENDING** - компонент создан, но может требовать модерации
- **ARCHIVED** - компонент больше не рекомендуется к использованию

---

### ShareableData (Общие данные)

Структура для хранения ссылок на общие словари:

```solidity
struct ShareableData {
    string features_cid;           // IPFS CID для features.json
    string component_forms_cid;    // IPFS CID для component_forms.json
    uint256 features_version;      // Версия features словаря
    uint256 forms_version;         // Версия forms словаря
    uint256 last_updated;          // Timestamp последнего обновления
}
```

**Назначение:**

Хранит ссылки на централизованные словари, используемые всеми компонентами:

1. **features.json** - список доступных features (Organic, Wildcrafted, Lab-tested, etc.)
2. **component_forms.json** - список доступных форм (Powder, Tincture, Capsules, etc.)

**Версионирование:**

- `features_version` и `forms_version` инкрементируются при обновлении
- Фронтенд может кэшировать и инвалидировать кэш по версии

---

### ComponentUpdate (Обновление) - Заготовка

```solidity
struct ComponentUpdate {
    uint256 component_id;           // ID компонента
    address proposer;               // Кто предложил обновление
    string new_root_metadata_cid;   // Новый CID метаданных
    string change_description;      // Описание изменений
    uint256 proposed_at;            // Когда предложено
    bool is_approved;               // Одобрено ли
    address approved_by;            // Кто одобрил
    uint256 approved_at;            // Когда одобрено
}
```

**Статус:** 🚧 **TODO** - функционал не реализован полностью

**Назначение:** Система предложений изменений для компонентов (governance)

---

### ComponentValidator (Валидатор) - Заготовка

```solidity
struct ComponentValidator {
    address validator;              // Адрес валидатора
    uint256 component_id;           // ID компонента
    bool has_validated;             // Провалидировано ли
    uint256 validated_at;           // Когда провалидировано
    string validation_comment;      // Комментарий валидатора
}
```

**Статус:** 🚧 **TODO** - функционал не реализован полностью

**Назначение:** Система валидации компонентов экспертами

---

## 🔧 Основной функционал

### Создание компонента

#### `createComponent(businessId, rootMetadataCID)`

Создаёт новый компонент в реестре.

**Сигнатура:**
```solidity
function createComponent(
    string calldata businessId,
    string calldata rootMetadataCID
) external returns (uint256 componentId)
```

**Параметры:**
- `businessId` - уникальный текстовый ID (например, "amanita_muscaria_powder")
- `rootMetadataCID` - IPFS CID корневого JSON с метаданными

**Требования:**
- ✅ Контракт не на паузе (`whenNotPaused`)
- ✅ Защита от reentrancy (`nonReentrant`)
- ✅ Пользователь активирован (`onlyActivatedUser`)
- ✅ Пользователь имеет SELLER_ROLE (`onlySeller`)
- ✅ businessId не пустой и ≤ 64 символов
- ✅ rootMetadataCID не пустой и ≤ 64 символов
- ✅ businessId уникален (не существует)
- ✅ У пользователя < 100 компонентов

**Что происходит:**
1. Валидация входных данных
2. Проверка уникальности businessId
3. Проверка лимита компонентов на пользователя
4. Создание нового componentId (++totalComponents)
5. Сохранение данных компонента
6. Эмиссия события `ComponentCreated`

**Возвращает:**
- `componentId` - уникальный ID созданного компонента

**События:**
```solidity
emit ComponentCreated(
    componentId,        // uint256 indexed
    businessId,         // string
    creator,           // address indexed
    rootMetadataCID,   // string
    block.timestamp    // uint256
);
```

**Пример использования:**
```javascript
const tx = await registry.createComponent(
    "amanita_muscaria_powder",
    "QmXxYy123..." // IPFS CID
);
const receipt = await tx.wait();
const componentId = receipt.logs[0].args.componentId;
```

---

### Обновление компонента

#### `updateComponent(componentId, newRootMetadataCID)`

Обновляет метаданные существующего компонента.

**Сигнатура:**
```solidity
function updateComponent(
    uint256 componentId,
    string calldata newRootMetadataCID
) external
```

**Параметры:**
- `componentId` - ID компонента для обновления
- `newRootMetadataCID` - новый IPFS CID метаданных

**Требования:**
- ✅ Контракт не на паузе
- ✅ Защита от reentrancy
- ✅ Вызывающий = создатель компонента
- ✅ newRootMetadataCID не пустой и ≤ 64 символов
- ✅ Компонент существует

**Что происходит:**
1. Валидация прав доступа (только creator)
2. Валидация CID
3. Обновление rootMetadataCID
4. Обновление last_updated timestamp
5. Эмиссия события `ComponentUpdated`

**События:**
```solidity
emit ComponentUpdated(
    componentId,           // uint256 indexed
    updater,              // address indexed
    newRootMetadataCID,   // string
    block.timestamp       // uint256
);
```

**Пример:**
```javascript
await registry.updateComponent(
    123,
    "QmNewCID456..." // Новый IPFS CID
);
```

---

### Получение компонента

#### `getComponentByBusinessId(businessId)`

Возвращает полную информацию о компоненте по его business ID.

**Сигнатура:**
```solidity
function getComponentByBusinessId(
    string calldata businessId
) external view returns (Component memory)
```

**Параметры:**
- `businessId` - текстовый ID компонента

**Возвращает:**
- `Component` структуру с данными компонента

**Пример:**
```javascript
const component = await registry.getComponentByBusinessId(
    "amanita_muscaria_powder"
);

console.log({
    id: component.blockchain_id,
    creator: component.creator,
    createdAt: component.created_at,
    lastUpdated: component.last_updated,
    status: component.status, // 0=ACTIVE, 1=PENDING, 2=ARCHIVED
    isShared: component.is_shared
});
```

---

### Проверка существования

#### `componentExists(businessId)`

Быстрая проверка существования компонента.

**Сигнатура:**
```solidity
function componentExists(
    string calldata businessId
) external view returns (bool)
```

**Параметры:**
- `businessId` - текстовый ID компонента

**Возвращает:**
- `true` если компонент существует, `false` иначе

**Пример:**
```javascript
const exists = await registry.componentExists("amanita_muscaria_powder");
if (exists) {
    // Компонент существует, можно использовать
}
```

---

### Отслеживание использования

#### `incrementUsageCount(businessId)`

Увеличивает счётчик использования компонента.

**Сигнатура:**
```solidity
function incrementUsageCount(
    string calldata businessId
) external
```

**Параметры:**
- `businessId` - текстовый ID компонента

**Требования:**
- ✅ Защита от reentrancy
- ✅ Компонент существует

**Назначение:**
- Вызывается ProductRegistry при создании продукта
- Отслеживает популярность компонентов
- Используется для аналитики

**События:**
```solidity
emit ComponentUsageIncremented(
    componentId,           // uint256 indexed
    businessId,           // string
    newUsageCount         // uint256
);
```

**Пример:**
```javascript
// Вызывается из ProductRegistry при создании продукта
await registry.incrementUsageCount("amanita_muscaria_powder");
```

---

#### `addComponentUser(businessId, user)`

Добавляет пользователя к списку использующих компонент.

**Сигнатура:**
```solidity
function addComponentUser(
    string calldata businessId,
    address user
) external
```

**Параметры:**
- `businessId` - текстовый ID компонента
- `user` - адрес пользователя

**Требования:**
- ✅ Защита от reentrancy
- ✅ Компонент существует
- ✅ user не нулевой адрес
- ✅ user ещё не добавлен к компоненту

**Назначение:**
- Отслеживает, кто использует компонент
- Используется для networking и аналитики

**События:**
```solidity
emit ComponentUserAdded(
    componentId,           // uint256 indexed
    businessId,           // string
    user                  // address indexed
);
```

---

### Получение списков компонентов

#### `getComponentsByCreator(creator)`

Возвращает все компоненты, созданные пользователем.

**Сигнатура:**
```solidity
function getComponentsByCreator(
    address creator
) external view returns (uint256[] memory)
```

**Возвращает:**
- Массив ID компонентов

**Пример:**
```javascript
const componentIds = await registry.getComponentsByCreator(alice.address);
// [1, 2, 5, 8, 12]
```

---

#### `getComponentsByUser(user)`

Возвращает все компоненты, используемые пользователем.

**Сигнатура:**
```solidity
function getComponentsByUser(
    address user
) external view returns (uint256[] memory)
```

**Возвращает:**
- Массив ID компонентов

**Пример:**
```javascript
const usedComponents = await registry.getComponentsByUser(bob.address);
// [3, 7, 11, 15]
```

---

## 🔄 Shareable данные

### Концепция

**Shareable Data** - это централизованные словари, используемые всеми компонентами:

1. **features.json** - список возможных характеристик
   - Organic
   - Wildcrafted
   - Lab-tested
   - Non-GMO
   - Vegan
   - Gluten-free

2. **component_forms.json** - список доступных форм
   - Powder
   - Tincture
   - Capsules
   - Extract
   - Raw

### Зачем это нужно?

- ✅ **Стандартизация** - единая терминология
- ✅ **Версионирование** - отслеживание изменений
- ✅ **Кэширование** - фронтенд может кэшировать словари
- ✅ **Мультиязычность** - словари содержат переводы
- ✅ **Валидация** - фронтенд проверяет значения по словарю

### Функции управления

#### `updateShareableData(featuresCID, componentFormsCID, featuresVersion, formsVersion)`

Обновляет ссылки на словари.

**Сигнатура:**
```solidity
function updateShareableData(
    string calldata featuresCID,
    string calldata componentFormsCID,
    uint256 featuresVersion,
    uint256 formsVersion
) external
```

**Требования:**
- ✅ Только ADMIN_ROLE
- ✅ Защита от reentrancy
- ✅ CID валидны (не пустые, ≤ 64 символов)

**События:**
```solidity
emit ShareableDataUpdated(
    featuresCID,           // string
    componentFormsCID,     // string
    featuresVersion,       // uint256 indexed
    formsVersion,          // uint256 indexed
    block.timestamp        // uint256 indexed
);
```

**Пример:**
```javascript
await registry.connect(admin).updateShareableData(
    "QmFeatures_v2",      // Новый features.json
    "QmForms_v3",         // Новый component_forms.json
    2,                   // Версия features
    3                    // Версия forms
);
```

---

#### `getShareableData()`

Получает полную структуру shareable данных.

**Сигнатура:**
```solidity
function getShareableData() 
    external 
    view 
    returns (ShareableData memory)
```

**Возвращает:**
```javascript
{
    features_cid: "QmFeatures_v2",
    component_forms_cid: "QmForms_v3",
    features_version: 2,
    forms_version: 3,
    last_updated: 1234567890
}
```

---

#### Отдельные геттеры

```solidity
function getFeaturesCID() external view returns (string memory);
function getComponentFormsCID() external view returns (string memory);
function getFeaturesVersion() external view returns (uint256);
function getComponentFormsVersion() external view returns (uint256);
```

---

## 🔗 Интеграции с экосистемой

### Архитектура интеграций

```
┌──────────────────────────────────────┐
│      OrganicComponentRegistry        │
│  (Центральный реестр компонентов)    │
└────┬──────────┬──────────┬───────────┘
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌──────────────┐
│ Spiral  │ │ Amanita │ │   Product    │
│ Engine  │ │  Intl   │ │   Registry   │
└─────────┘ └─────────┘ └──────────────┘
```

### 1. SpiralEngine Integration

**Назначение:** Управление пользователями и правами доступа

**Используемые функции:**
```solidity
interface ISpiralEngine {
    function isUserActivated(address user) external view returns (bool);
    function hasRole(bytes32 role, address account) external view returns (bool);
    function SELLER_ROLE() external view returns (bytes32);
}
```

**Как используется:**
- Проверка активации пользователя (`onlyActivatedUser`)
- Проверка SELLER_ROLE (`onlySeller`)
- Валидация прав на создание компонентов

**Настройка:**
```javascript
await registry.connect(admin).setSpiralEngine(spiralEngineAddress);
```

---

### 2. AmanitaInternational Integration

**Назначение:** Управление переводами и мультиязычностью

**Статус:** 🚧 TODO - интеграция готова, функционал в разработке

**Планируемые возможности:**
- Получение переводов для компонентов
- Мультиязычные метаданные
- Локализация UI

**Настройка:**
```javascript
await registry.connect(admin).setAmanitaInternational(amanitaIntlAddress);
```

---

### 3. ProductRegistry Integration

**Назначение:** Валидация компонентов при создании продуктов

**Используемые функции:**
```solidity
interface IOrganicComponentRegistry {
    function componentExists(string memory businessId) external view returns (bool);
    function incrementUsageCount(string memory businessId) external;
    function addComponentUser(string memory businessId, address user) external;
}
```

**Как используется:**
1. ProductRegistry проверяет существование компонентов
2. При создании продукта инкрементирует счётчик использования
3. Добавляет пользователя к списку использующих

**Настройка:**
```javascript
await registry.connect(admin).setProductRegistry(productRegistryAddress);
```

**Пример flow:**
```javascript
// В ProductRegistry при создании продукта
if (!await componentRegistry.componentExists("amanita_muscaria_powder")) {
    revert("Component not found");
}
await componentRegistry.incrementUsageCount("amanita_muscaria_powder");
await componentRegistry.addComponentUser("amanita_muscaria_powder", seller);
```

---

## 🛡️ Безопасность

### 1. ReentrancyGuard

**Защита:** Все мутирующие функции защищены модификатором `nonReentrant`

**Защищённые функции (10):**
1. `createComponent()`
2. `updateComponent()`
3. `incrementUsageCount()`
4. `addComponentUser()`
5. `updateShareableData()`
6. `setSpiralEngine()`
7. `setAmanitaInternational()`
8. `setProductRegistry()`
9. `pause()`
10. `unpause()`

**Механизм:**
- Блокирует рекурсивные вызовы в рамках одной транзакции
- Использует OpenZeppelin `ReentrancyGuardUpgradeable`
- Gas cost: ~2000-3000 газа на вызов

---

### 2. Access Control (Роли)

**Механизм:** OpenZeppelin `AccessControlUpgradeable`

**Защита:**
- ✅ Только admin может обновлять конфигурацию
- ✅ Только upgrader может обновлять Logic
- ✅ Только создатель может обновлять свой компонент
- ✅ Только активированные seller могут создавать компоненты

---

### 3. Pausable (Аварийная остановка)

**Механизм:** OpenZeppelin `PausableUpgradeable`

**Использование:**
```javascript
// Emergency stop
await registry.connect(admin).pause();

// Resume operations
await registry.connect(admin).unpause();
```

**Защищённые функции:**
- `createComponent()` - `whenNotPaused`
- `updateComponent()` - `whenNotPaused`

---

### 4. Input Validation

**Валидации:**

#### businessId:
- ❌ Не может быть пустым
- ❌ Не может быть > 64 символов
- ❌ Должен быть уникальным

#### CID (IPFS):
- ❌ Не может быть пустым
- ❌ Не может быть > 64 символов

#### Адреса:
- ❌ Не могут быть `address(0)` (custom error `ZeroAddress`)

---

### 5. Custom Errors

**Газовая оптимизация:** Custom errors экономят ~50 gas на revert

**Объявленные errors (13):**
```solidity
error NotComponentCreator();
error BusinessIdEmpty();
error BusinessIdTooLong(uint256 max);
error CIDEmpty();
error CIDTooLong(uint256 max);
error ComponentAlreadyExists();
error ComponentLimitExceeded(uint256 max);
error ZeroAddress();
error ComponentNotFound();
error UserAlreadyAdded();
error SpiralEngineNotSet();
error UserNotActivated();
error InvalidAddress();
```

**Использование:**
- ✅ Новые пути используют custom errors
- ✅ Legacy пути используют string reverts (обратная совместимость)

---

### 6. UUPS Upgrade Protection

**Механизм:**
- Upgrade защищён через `_authorizeUpgrade()`
- Требует `UPGRADER_ROLE`
- Невозможен прямой вызов на implementation

**Тесты:**
- ✅ Только UPGRADER_ROLE может апгрейдить
- ✅ Обычный пользователь не может апгрейдить
- ✅ Прямые вызовы на implementation не работают

---

### 7. Limit Enforcement

**Защита от spam:**

- **MAX_COMPONENTS_PER_USER = 100**
  - Ограничение на количество компонентов от одного пользователя
  - Защита от спама и DoS

- **MAX_BUSINESS_ID_LENGTH = 64**
  - Ограничение длины идентификатора
  - Защита от газовых атак

- **MAX_CID_LENGTH = 64**
  - Ограничение длины IPFS CID
  - Защита от газовых атак

---

## ⚡ Газовые оптимизации

### 1. Unchecked блоки (3 места)

**Оптимизация:** Пропуск проверок overflow для безопасных операций

```solidity
// В createComponent
unchecked {
    componentId = ++totalComponents;
}
// Экономия: ~100-200 gas

// В incrementUsageCount
unchecked {
    componentUsageCount[componentId]++;
}
// Экономия: ~100-200 gas

// В цикле addComponentUser
for (uint256 i = 0; i < userComponents.length;) {
    // ...
    unchecked { ++i; }
}
// Экономия: ~30-50 gas на итерацию
```

---

### 2. Calldata вместо Memory (7 функций)

**Оптимизация:** Использование calldata для read-only параметров

```solidity
// Было: string memory businessId
// Стало: string calldata businessId

function createComponent(
    string calldata businessId,      // ← calldata
    string calldata rootMetadataCID  // ← calldata
) external ...
```

**Функции с calldata:**
1. `createComponent()` - 2 параметра
2. `updateComponent()` - 1 параметр
3. `getComponentByBusinessId()` - 1 параметр
4. `componentExists()` - 1 параметр
5. `incrementUsageCount()` - 1 параметр
6. `addComponentUser()` - 1 параметр
7. `updateShareableData()` - 2 параметра

**Экономия:** ~300-500 gas на функцию

---

### 3. Кэширование bytes().length (2 модификатора)

**Оптимизация:** Вычисление length один раз вместо двух

```solidity
// Было:
require(bytes(businessId).length > 0, "...");
require(bytes(businessId).length <= MAX, "...");

// Стало:
uint256 len = bytes(businessId).length; // ← кэшируем
require(len > 0, "...");
require(len <= MAX, "...");
```

**Где применено:**
- `validBusinessId` модификатор
- `validCID` модификатор

**Экономия:** ~100 gas на валидацию

---

### 4. Indexed события (5 событий)

**Оптимизация:** Индексация для быстрой фильтрации off-chain

```solidity
event ComponentCreated(
    uint256 indexed componentId,   // ← indexed
    string businessId,
    address indexed creator,        // ← indexed
    string rootMetadataCID,
    uint256 timestamp
);
```

**События с indexed:**
1. `ComponentCreated` - componentId, creator
2. `ComponentUpdated` - componentId, updater
3. `ComponentUsageIncremented` - componentId
4. `ComponentUserAdded` - componentId, user
5. `ShareableDataUpdated` - featuresVersion, formsVersion, timestamp

**Польза:**
- Быстрая фильтрация событий
- Эффективный поиск по параметрам
- Улучшенная аналитика

---

### 5. Compiler Optimization

**Настройки:**
```javascript
// hardhat.config.js
{
  version: "0.8.22",
  settings: {
    optimizer: {
      enabled: true,
      runs: 200          // Оптимизация для частых вызовов
    },
    viaIR: true         // IR-based code generator
  }
}
```

**Преимущества:**
- Решает "Stack too deep" проблему
- Улучшает оптимизацию кода
- Уменьшает размер контракта

---

### Суммарная экономия

| Операция | Экономия газа |
|----------|---------------|
| `createComponent()` | ~1000 gas |
| `updateComponent()` | ~500 gas |
| `incrementUsageCount()` | ~500 gas |
| `addComponentUser()` | ~700 gas |

**Средняя экономия:** ~500-1000 gas на транзакцию (0.5-1%)

---

## 📚 Примеры использования

### Пример 1: Создание компонента

```javascript
// Подключение к контракту
const registry = await ethers.getContractAt(
    "OrganicComponentRegistryLogic",
    proxyAddress
);

// Подготовка метаданных
const metadata = {
    name: "Amanita Muscaria Powder",
    description: "Wildcrafted Amanita Muscaria caps, dried and powdered",
    image: "QmImageCID...",
    properties: {
        species: "Amanita muscaria",
        form: "powder",
        features: ["wildcrafted", "organic", "lab-tested"],
        origin: "Siberian Taiga",
        harvest_season: "Summer 2024"
    }
};

// Загрузка в IPFS
const metadataCID = await uploadToIPFS(metadata);

// Создание компонента
const tx = await registry.connect(seller).createComponent(
    "amanita_muscaria_powder",  // businessId
    metadataCID                  // IPFS CID
);

const receipt = await tx.wait();
const event = receipt.logs.find(e => e.eventName === "ComponentCreated");
const componentId = event.args.componentId;

console.log(`Component created with ID: ${componentId}`);
```

---

### Пример 2: Обновление метаданных

```javascript
// Обновлённые метаданные
const updatedMetadata = {
    ...metadata,
    properties: {
        ...metadata.properties,
        certifications: ["USDA Organic", "Lab Tested"]
    }
};

// Загрузка обновлённых данных
const newCID = await uploadToIPFS(updatedMetadata);

// Обновление компонента
await registry.connect(seller).updateComponent(
    componentId,
    newCID
);

console.log("Component metadata updated");
```

---

### Пример 3: Использование в ProductRegistry

```javascript
// В ProductRegistry контракте
async function createProduct(components, metadata) {
    // Валидация всех компонентов
    for (const componentId of components) {
        const exists = await componentRegistry.componentExists(componentId);
        if (!exists) {
            revert("Component not found");
        }
    }
    
    // Создание продукта
    const productId = await _createProduct(metadata);
    
    // Обновление статистики компонентов
    for (const componentId of components) {
        await componentRegistry.incrementUsageCount(componentId);
        await componentRegistry.addComponentUser(componentId, msg.sender);
    }
    
    return productId;
}
```

---

### Пример 4: Получение компонентов пользователя

```javascript
// Получить все компоненты, созданные пользователем
const creatorComponents = await registry.getComponentsByCreator(
    alice.address
);

console.log(`Alice created ${creatorComponents.length} components`);

// Детальная информация о каждом
for (const id of creatorComponents) {
    const businessId = await registry.componentBusinessIds(id);
    const component = await registry.getComponentByBusinessId(businessId);
    
    console.log({
        id: id,
        businessId: businessId,
        createdAt: new Date(component.created_at * 1000),
        status: component.status
    });
}
```

---

### Пример 5: Фильтрация событий

```javascript
// Фильтр событий по componentId
const filter = registry.filters.ComponentCreated(123); // componentId = 123
const events = await registry.queryFilter(filter);

console.log(`Component 123 created ${events.length} times (shouldn't happen)`);

// Фильтр по creator
const creatorFilter = registry.filters.ComponentCreated(
    null,              // componentId (любой)
    null,              // businessId (любой)
    alice.address      // creator (только Alice)
);
const aliceEvents = await registry.queryFilter(creatorFilter);

console.log(`Alice created ${aliceEvents.length} components`);
```

---

### Пример 6: Обновление shareable данных

```javascript
// Подготовка словарей
const features = [
    { id: "organic", name: { en: "Organic", ru: "Органический" } },
    { id: "wildcrafted", name: { en: "Wildcrafted", ru: "Дикоросы" } },
    { id: "lab-tested", name: { en: "Lab Tested", ru: "Протестировано" } }
];

const forms = [
    { id: "powder", name: { en: "Powder", ru: "Порошок" } },
    { id: "tincture", name: { en: "Tincture", ru: "Настойка" } },
    { id: "capsules", name: { en: "Capsules", ru: "Капсулы" } }
];

// Загрузка в IPFS
const featuresCID = await uploadToIPFS(features);
const formsCID = await uploadToIPFS(forms);

// Обновление в контракте
await registry.connect(admin).updateShareableData(
    featuresCID,    // CID features.json
    formsCID,       // CID component_forms.json
    2,              // features version
    1               // forms version
);

console.log("Shareable data updated");
```

---

## 🔧 Технические спецификации

### Константы

| Имя | Значение | Назначение |
|-----|----------|------------|
| `LOGIC_VERSION` | 2 | Версия Logic контракта |
| `MAX_BUSINESS_ID_LENGTH` | 64 | Максимальная длина business_id |
| `MAX_CID_LENGTH` | 64 | Максимальная длина IPFS CID |
| `MAX_COMPONENTS_PER_USER` | 100 | Лимит компонентов на пользователя |

---

### Роли (bytes32 hashes)

```solidity
DEFAULT_ADMIN_ROLE = 0x00...00
ADMIN_ROLE = keccak256("ADMIN_ROLE")
UPGRADER_ROLE = keccak256("UPGRADER_ROLE")
CONTRIBUTOR_ROLE = keccak256("CONTRIBUTOR_ROLE")
```

---

### Storage Layout (примерный)

```
Slot 0-50: OpenZeppelin Upgradeable контракты (AccessControl, Pausable, etc.)
Slot 51+: OrganicComponentRegistry данные
  - components (mapping)
  - componentBusinessIds (mapping)
  - componentRootMetadataCIDs (mapping)
  - businessIdToComponentId (mapping)
  - componentsByCreator (mapping)
  - componentsByUser (mapping)
  - shareableData (struct)
  - totalComponents (uint256)
  - spiralEngine (address)
  - amanitaInternational (address)
  - productRegistry (address)
  ...
```

---

### Газовые затраты (оценки)

| Операция | Газ | Примечание |
|----------|-----|------------|
| `createComponent()` | ~180,000 | Включая ERC721-like операции |
| `updateComponent()` | ~80,000 | Только обновление CID |
| `incrementUsageCount()` | ~50,000 | Простой инкремент |
| `addComponentUser()` | ~70,000 | С проверкой дубликатов |
| `componentExists()` | ~1,000 | View функция |
| `getComponentByBusinessId()` | ~2,000 | View функция |

---

### Лимиты и ограничения

- **Компонентов на пользователя:** 100
- **Длина businessId:** 64 символа
- **Длина CID:** 64 символа
- **Общее количество компонентов:** 2^256 - 1 (практически неограничено)

---

### Зависимости

**OpenZeppelin Upgradeable v5.x:**
- `Initializable`
- `UUPSUpgradeable`
- `AccessControlUpgradeable`
- `PausableUpgradeable`
- `ReentrancyGuardUpgradeable`

**Интерфейсы:**
- `ISpiralEngine`
- `IAmanitaInternational`
- `IProductRegistry`
- `IOrganicComponentRegistry`

---

### Сеть и деплой

**Поддерживаемые сети:**
- Polygon Mainnet (рекомендуется)
- Polygon Mumbai (testnet)
- Hardhat Network (development)

**Деплой:**
```bash
# Компиляция
npx hardhat compile

# Деплой (через скрипт)
npx hardhat run scripts/deploy_full.js --network polygon

# Верификация
npx hardhat verify --network polygon <PROXY_ADDRESS>
```

---

## 📖 FAQ

### Q: Можно ли удалить компонент?

**A:** Нет, компоненты нельзя удалить (immutable registry). Можно изменить статус на `ARCHIVED`.

### Q: Как обновить Logic контракт?

**A:** Через `upgradeToAndCall()` с UPGRADER_ROLE:
```javascript
const newLogic = await deploy("OrganicComponentRegistryLogic");
await proxy.connect(upgrader).upgradeToAndCall(
    newLogic.address,
    "0x" // calldata для миграции (если нужна)
);
```

### Q: Что будет при upgrade?

**A:** Все данные сохраняются в Proxy, меняется только логика.

### Q: Можно ли передать ownership компонента?

**A:** Нет, creator неизменяем. Это сделано намеренно для прозрачности авторства.

### Q: Как работает лимит в 100 компонентов?

**A:** Проверка `componentsByCreator[user].length < 100` при создании. Можно увеличить через upgrade.

### Q: Зачем нужен SpiralEngine для создания компонентов?

**A:** Для контроля качества и защиты от spam. Только активированные sellers могут создавать компоненты.

---

## 🔗 Полезные ссылки

- **GitHub Repository:** [github.com/ViralLove/amanita](https://github.com/ViralLove/amanita)
- **Deployed Contract:** (добавить адрес после деплоя)
- **Polygon Explorer:** (добавить ссылку после деплоя)
- **IPFS Gateway:** https://ipfs.io/ipfs/
- **Documentation:** [contracts/docs/](.)

---

## 📝 История версий

### v3.0.0 (Текущая)
- ✅ Рефакторинг к стандартному UUPS паттерну
- ✅ Добавлен ReentrancyGuard
- ✅ Custom errors для газовых оптимизаций
- ✅ Индексация событий
- ✅ Calldata оптимизации
- ✅ Comprehensive тесты (37/37 passing)

### v2.0.0
- Переход на UUPS архитектуру
- Интеграция с экосистемой

### v1.0.0
- Первая версия реестра компонентов

---

## 👥 Контакты

- **Author:** Zeya888 (https://zeya888.me)
- **Team:** Amanita Decentralization Team
- **Support:** (добавить контакты)

---

**Документация актуальна на:** 2025-01-07

**Контракт протестирован:** ✅ 37/37 тестов (100% success)

**Готовность к production:** ✅ Да (требуется настройка CI/CD)

---

## 📐 Архитектура данных

### Metadata Structure (IPFS JSON)

Структура JSON метаданных компонента, хранимого в IPFS:

```json
{
  "version": "1.0.0",
  "component": {
    "businessId": "amanita_muscaria_powder",
    "name": {
      "en": "Amanita Muscaria Powder",
      "ru": "Мухомор красный (порошок)"
    },
    "description": {
      "en": "Wildcrafted Amanita Muscaria caps, dried and powdered",
      "ru": "Дикорастущий мухомор красный, высушенный и измельчённый"
    },
    "category": "mushroom",
    "species": {
      "scientific": "Amanita muscaria",
      "common": {
        "en": "Fly Agaric",
        "ru": "Мухомор красный"
      }
    }
  },
  "properties": {
    "form": "powder",
    "features": [
      "wildcrafted",
      "organic",
      "lab-tested",
      "siberian"
    ],
    "origin": {
      "region": "Siberian Taiga",
      "country": "Russia",
      "coordinates": [60.0, 100.0]
    },
    "harvest": {
      "season": "Summer",
      "year": 2024,
      "method": "hand-picked"
    }
  },
  "quality": {
    "certifications": [
      "USDA Organic",
      "Lab Tested"
    ],
    "tests": [
      {
        "type": "heavy_metals",
        "result": "passed",
        "date": "2024-06-15",
        "cid": "QmTestResultCID..."
      }
    ]
  },
  "media": {
    "images": [
      "QmImage1...",
      "QmImage2..."
    ],
    "videos": [],
    "documents": [
      "QmCertificate1..."
    ]
  },
  "blockchain": {
    "componentId": 123,
    "creator": "0x123...",
    "createdAt": 1704672000
  }
}
```

---

### Features Dictionary (features.json)

Централизованный словарь характеристик:

```json
{
  "version": 2,
  "lastUpdated": 1704672000,
  "features": [
    {
      "id": "organic",
      "name": {
        "en": "Organic",
        "ru": "Органический"
      },
      "description": {
        "en": "Certified organic product",
        "ru": "Сертифицированный органический продукт"
      },
      "icon": "🌿",
      "category": "certification"
    },
    {
      "id": "wildcrafted",
      "name": {
        "en": "Wildcrafted",
        "ru": "Дикоросы"
      },
      "description": {
        "en": "Harvested from wild nature",
        "ru": "Собрано в дикой природе"
      },
      "icon": "🏔️",
      "category": "sourcing"
    },
    {
      "id": "lab-tested",
      "name": {
        "en": "Lab Tested",
        "ru": "Протестировано в лаборатории"
      },
      "description": {
        "en": "Third-party laboratory tested",
        "ru": "Протестировано независимой лабораторией"
      },
      "icon": "🔬",
      "category": "quality"
    }
  ]
}
```

---

### Component Forms Dictionary (component_forms.json)

Словарь доступных форм продукции:

```json
{
  "version": 1,
  "lastUpdated": 1704672000,
  "forms": [
    {
      "id": "powder",
      "name": {
        "en": "Powder",
        "ru": "Порошок"
      },
      "description": {
        "en": "Finely ground dried product",
        "ru": "Измельчённый высушенный продукт"
      },
      "icon": "🧂",
      "typical_packaging": ["bag", "jar"]
    },
    {
      "id": "tincture",
      "name": {
        "en": "Tincture",
        "ru": "Настойка"
      },
      "description": {
        "en": "Alcohol or glycerin extraction",
        "ru": "Спиртовая или глицериновая вытяжка"
      },
      "icon": "💧",
      "typical_packaging": ["bottle", "dropper"]
    },
    {
      "id": "capsules",
      "name": {
        "en": "Capsules",
        "ru": "Капсулы"
      },
      "description": {
        "en": "Powder encapsulated for convenience",
        "ru": "Порошок в капсулах для удобства"
      },
      "icon": "💊",
      "typical_packaging": ["jar", "blister"]
    },
    {
      "id": "extract",
      "name": {
        "en": "Extract",
        "ru": "Экстракт"
      },
      "description": {
        "en": "Concentrated active compounds",
        "ru": "Концентрированные активные вещества"
      },
      "icon": "⚗️",
      "typical_packaging": ["bottle"]
    }
  ]
}
```

---

## 🔄 Паттерны интеграции

### Integration Pattern 1: ProductRegistry валидация

**Сценарий:** При создании продукта валидировать компоненты

```solidity
// В ProductRegistry контракте
contract ProductRegistry {
    IOrganicComponentRegistry public componentRegistry;
    
    function createProduct(
        string[] calldata componentIds,
        string calldata productMetadataCID
    ) external returns (uint256 productId) {
        // Валидация всех компонентов
        for (uint i = 0; i < componentIds.length; i++) {
            require(
                componentRegistry.componentExists(componentIds[i]),
                "ProductRegistry: component not found"
            );
            
            // Опционально: проверка статуса
            require(
                componentRegistry.getComponentStatus(componentIds[i]) == 
                IOrganicComponentRegistry.ComponentStatus.ACTIVE,
                "ProductRegistry: component not active"
            );
        }
        
        // Создание продукта
        productId = _createProduct(componentIds, productMetadataCID);
        
        // Обновление статистики
        for (uint i = 0; i < componentIds.length; i++) {
            componentRegistry.incrementUsageCount(componentIds[i]);
            componentRegistry.addComponentUser(componentIds[i], msg.sender);
        }
        
        return productId;
    }
}
```

---

### Integration Pattern 2: Фронтенд кэширование

**Сценарий:** Кэширование shareable данных на фронтенде

```javascript
class ComponentRegistryCache {
    constructor(contractAddress, provider) {
        this.contract = new ethers.Contract(
            contractAddress,
            IOrganicComponentRegistry.abi,
            provider
        );
        this.featuresCache = null;
        this.formsCache = null;
    }
    
    async getFeatures() {
        const shareableData = await this.contract.getShareableData();
        
        // Проверяем версию кэша
        if (this.featuresCache && 
            this.featuresCache.version === shareableData.features_version) {
            return this.featuresCache.data;
        }
        
        // Загружаем новые данные с IPFS
        const features = await this.fetchFromIPFS(
            shareableData.features_cid
        );
        
        // Обновляем кэш
        this.featuresCache = {
            version: shareableData.features_version,
            data: features
        };
        
        return features;
    }
    
    async getForms() {
        // Аналогично для forms
        // ...
    }
    
    async fetchFromIPFS(cid) {
        const response = await fetch(`https://ipfs.io/ipfs/${cid}`);
        return await response.json();
    }
}
```

---

### Integration Pattern 3: Event Listening

**Сценарий:** Подписка на события для аналитики

```javascript
// Подписка на создание компонентов
registry.on("ComponentCreated", (componentId, businessId, creator, cid, timestamp) => {
    console.log(`New component: ${businessId} by ${creator}`);
    analytics.track("component_created", {
        componentId,
        businessId,
        creator,
        timestamp
    });
});

// Фильтрация событий по creator
const filter = registry.filters.ComponentCreated(null, null, alice.address);
const events = await registry.queryFilter(filter, fromBlock, toBlock);

// Статистика
const componentsByCreator = events.reduce((acc, event) => {
    acc[event.args.creator] = (acc[event.args.creator] || 0) + 1;
    return acc;
}, {});
```

---

## 🧪 Тестирование

### Структура тестов (37 total)

```
OrganicComponentRegistry.UUPS.test.js
│
├─ UUPS Architecture Tests (13)
│  ├─ Deploy and initialize
│  ├─ Create/update component
│  ├─ Usage tracking
│  ├─ Validation (limits, formats, duplicates)
│  └─ Permissions
│
├─ Proxy Management (4)
│  ├─ Upgrade logic
│  ├─ Pause/unpause
│  └─ Role restrictions
│
├─ Integration Tests (5)
│  ├─ SpiralEngine integration
│  ├─ AmanitaInternational integration
│  ├─ ProductRegistry integration
│  ├─ Admin restrictions
│  └─ Zero address validation
│
├─ Shareable Data Tests (3)
│  ├─ Update shareable data
│  ├─ Admin restrictions
│  └─ CID validation
│
├─ Role Management Tests (2)
│  ├─ Grant/revoke roles
│  └─ Admin restrictions
│
├─ Custom Errors Tests (2)
│  ├─ ZeroAddress error
│  └─ Custom vs legacy compatibility
│
├─ Event Filtering Tests (4)
│  ├─ Filter by componentId
│  ├─ Filter by creator
│  ├─ Filter by user
│  └─ Filter by version
│
├─ Reentrancy Protection Tests (1)
│  └─ Smoke test for all protected functions
│
└─ Proxy Protection Tests (3)
   ├─ Direct implementation calls
   ├─ UUPS upgrade protection
   └─ Documentation test
```

### Запуск тестов

```bash
# Все тесты
npx hardhat test

# Только OrganicComponentRegistry
npx hardhat test contracts/tests/OrganicComponentRegistry.UUPS.test.js

# Конкретная группа
npx hardhat test --grep "Integration Tests"

# С детальным выводом
npx hardhat test --verbose
```

---

## 🚨 Troubleshooting

### Проблема: "Stack too deep" при компиляции

**Решение:** Включен viaIR в hardhat.config.js
```javascript
{
  version: "0.8.22",
  settings: {
    viaIR: true  // ← решает проблему
  }
}
```

---

### Проблема: "Component limit exceeded"

**Причина:** Пользователь создал 100+ компонентов

**Решение:**
- Использовать другой адрес
- Или увеличить лимит через upgrade Logic контракта

---

### Проблема: "User not activated"

**Причина:** Пользователь не активирован в SpiralEngine

**Решение:**
```javascript
// Активация через SpiralEngine
await spiralEngine.activateUser(
    inviteCode,
    userAddress,
    newInviteCodes,
    tokenId
);
```

---

### Проблема: "Not component creator"

**Причина:** Попытка обновить чужой компонент

**Решение:**
- Только создатель может обновлять свой компонент
- Используйте адрес создателя для updateComponent()

---

### Проблема: Events не фильтруются

**Причина:** Параметр не indexed

**Решение:**
- Используйте indexed параметры для фильтрации
- businessId не indexed (string нельзя индексировать)
- Используйте componentId вместо businessId для фильтрации

---

## 🎯 Best Practices

### Для Developers

1. **Всегда проверяйте существование**
   ```javascript
   if (!await registry.componentExists(businessId)) {
       throw new Error("Component not found");
   }
   ```

2. **Кэшируйте shareable данные**
   ```javascript
   const features = await getCachedFeatures(registry);
   ```

3. **Используйте events для аналитики**
   ```javascript
   const logs = await registry.queryFilter(
       registry.filters.ComponentCreated()
   );
   ```

4. **Проверяйте роли перед вызовами**
   ```javascript
   const hasRole = await registry.hasRole(CONTRIBUTOR_ROLE, user);
   if (!hasRole) {
       throw new Error("Missing CONTRIBUTOR_ROLE");
   }
   ```

5. **Обрабатывайте custom errors**
   ```javascript
   try {
       await registry.setSpiralEngine(address);
   } catch (error) {
       if (error.errorName === "ZeroAddress") {
           console.error("Invalid address provided");
       }
   }
   ```

---

### Для Contributors

1. **Уникальные businessId**
   - Используйте snake_case: `amanita_muscaria_powder`
   - Включайте форму: `_powder`, `_tincture`
   - Избегайте спецсимволов

2. **Качественные метаданные**
   - Полное описание на нескольких языках
   - Высококачественные изображения
   - Сертификаты и тесты (если есть)

3. **IPFS Best Practices**
   - Pinning через Pinata/Infura
   - Бэкапы CID
   - Проверка доступности перед публикацией

4. **Соблюдайте лимиты**
   - Максимум 100 компонентов на аккаунт
   - Используйте осмысленные ID

---

### Для Admins

1. **Регулярное обновление словарей**
   ```javascript
   // Раз в месяц/квартал
   await registry.updateShareableData(
       newFeaturesCID,
       newFormsCID,
       ++featuresVersion,
       ++formsVersion
   );
   ```

2. **Мониторинг использования**
   ```javascript
   // Топ-10 компонентов
   const stats = await getComponentUsageStats(registry);
   ```

3. **Управление ролями**
   ```javascript
   // Выдача CONTRIBUTOR_ROLE новым продавцам
   await registry.grantRole(CONTRIBUTOR_ROLE, newSeller);
   ```

4. **Emergency procedures**
   ```javascript
   // При обнаружении проблемы
   await registry.pause();
   // Расследование и исправление
   await registry.unpause();
   ```

---

## 📊 Мониторинг и аналитика

### Ключевые метрики

**1. Общие метрики:**
```javascript
const totalComponents = await registry.totalComponents();
const totalUpdates = await registry.totalUpdates();
```

**2. Популярность компонентов:**
```javascript
async function getTopComponents(registry, limit = 10) {
    const total = await registry.totalComponents();
    const components = [];
    
    for (let i = 1; i <= total; i++) {
        const usage = await registry.componentUsageCount(i);
        const businessId = await registry.componentBusinessIds(i);
        components.push({ id: i, businessId, usage });
    }
    
    return components
        .sort((a, b) => b.usage - a.usage)
        .slice(0, limit);
}
```

**3. Активность creators:**
```javascript
async function getCreatorStats(registry, creator) {
    const componentIds = await registry.getComponentsByCreator(creator);
    
    let totalUsage = 0;
    for (const id of componentIds) {
        totalUsage += await registry.componentUsageCount(id);
    }
    
    return {
        componentsCreated: componentIds.length,
        totalUsage: totalUsage,
        avgUsage: totalUsage / componentIds.length
    };
}
```

**4. События за период:**
```javascript
async function getEventsInRange(registry, fromBlock, toBlock) {
    const createdEvents = await registry.queryFilter(
        registry.filters.ComponentCreated(),
        fromBlock,
        toBlock
    );
    
    const updatedEvents = await registry.queryFilter(
        registry.filters.ComponentUpdated(),
        fromBlock,
        toBlock
    );
    
    return {
        created: createdEvents.length,
        updated: updatedEvents.length,
        ratio: updatedEvents.length / createdEvents.length
    };
}
```

---

## 🔐 Безопасность и аудит

### Проведённые проверки

- ✅ **Unit Tests:** 37/37 passing (100% success)
- ✅ **ReentrancyGuard:** Защита от reentrancy атак
- ✅ **Access Control:** Роли правильно настроены
- ✅ **Input Validation:** Все входные данные валидируются
- ✅ **UUPS Security:** Upgrade защищён через UPGRADER_ROLE
- ✅ **Gas Optimizations:** Безопасные оптимизации применены

### Рекомендации для аудита

**Критические пути для проверки:**
1. `_authorizeUpgrade()` - защита upgrade
2. `createComponent()` - валидация входных данных
3. `updateComponent()` - проверка прав creator
4. Integration setters - валидация адресов
5. Role management - корректность DEFAULT_ADMIN_ROLE

**Возможные векторы атак:**
- ❌ Reentrancy - защищено через ReentrancyGuard
- ❌ Unauthorized upgrade - защищено через UPGRADER_ROLE
- ❌ DoS через spam - защищено лимитом 100 компонентов
- ❌ Gas griefing - защищено лимитами длины
- ❌ Front-running - минимальный риск (нет финансовых операций)

---

## 🚀 Deployment Guide

### Pre-deployment Checklist

- [ ] Скомпилирован с viaIR: true
- [ ] Все тесты проходят (37/37)
- [ ] SpiralEngine задеплоен и адрес известен
- [ ] Admin адрес подготовлен (multisig recommended)
- [ ] Features и Forms словари подготовлены в IPFS
- [ ] Gas price приемлемый для сети

### Deployment Steps

**1. Деплой Logic контракта:**
```bash
npx hardhat run scripts/deploy-logic.js --network polygon
```

**2. Деплой Proxy контракта:**
```javascript
const Logic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
const logic = await Logic.deploy();
await logic.waitForDeployment();

const Proxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
const initData = logic.interface.encodeFunctionData("initialize", [
    admin.address
]);

const proxy = await Proxy.deploy(
    await logic.getAddress(),
    initData
);
await proxy.waitForDeployment();

console.log("Proxy deployed at:", await proxy.getAddress());
```

**3. Настройка интеграций:**
```javascript
const registry = await ethers.getContractAt(
    "OrganicComponentRegistryLogic",
    proxyAddress
);

await registry.connect(admin).setSpiralEngine(spiralEngineAddress);
await registry.connect(admin).setProductRegistry(productRegistryAddress);
```

**4. Загрузка начальных данных:**
```javascript
// Upload features и forms в IPFS
const featuresCID = await uploadToIPFS(features);
const formsCID = await uploadToIPFS(forms);

await registry.connect(admin).updateShareableData(
    featuresCID,
    formsCID,
    1, // initial version
    1  // initial version
);
```

**5. Верификация на Polygonscan:**
```bash
npx hardhat verify --network polygon <PROXY_ADDRESS>
npx hardhat verify --network polygon <LOGIC_ADDRESS>
```

---

### Post-deployment Checklist

- [ ] Proxy адрес сохранён
- [ ] Logic адрес сохранён
- [ ] Интеграции настроены
- [ ] Shareable данные загружены
- [ ] Роли выданы нужным адресам
- [ ] Контракт верифицирован
- [ ] Документация обновлена с адресами

---

## 🔄 Upgrade Procedure

### Когда нужен upgrade?

- 🔧 Исправление критических багов
- ✨ Добавление новой функциональности
- ⚡ Газовые оптимизации
- 🔒 Улучшения безопасности

### Upgrade Process

**1. Разработка новой версии:**
```solidity
// OrganicComponentRegistryLogicV2.sol
contract OrganicComponentRegistryLogicV2 is 
    OrganicComponentRegistryLogic // наследуем старую версию
{
    uint256 public constant LOGIC_VERSION = 3; // инкремент версии
    
    // Новые функции
    function newFeature() external {
        // ...
    }
    
    // Миграция данных (если нужна)
    function migrateDataV2ToV3() external onlyRole(ADMIN_ROLE) onlyProxy {
        // ...
    }
}
```

**2. Тестирование:**
```bash
npx hardhat test contracts/tests/OrganicComponentRegistry.UUPS.test.js
```

**3. Деплой новой Logic:**
```javascript
const LogicV2 = await ethers.getContractFactory("OrganicComponentRegistryLogicV2");
const logicV2 = await LogicV2.deploy();
await logicV2.waitForDeployment();
```

**4. Upgrade через Proxy:**
```javascript
const registry = await ethers.getContractAt(
    "OrganicComponentRegistryLogic",
    proxyAddress
);

// Если нужна миграция данных
const migrateCalldata = logicV2.interface.encodeFunctionData("migrateDataV2ToV3");

await registry.connect(upgrader).upgradeToAndCall(
    await logicV2.getAddress(),
    migrateCalldata // или "0x" если миграция не нужна
);
```

**5. Проверка:**
```javascript
const version = await registry.LOGIC_VERSION();
console.log(`Upgraded to version: ${version}`); // должно быть 3

// Проверяем что данные сохранились
const totalComponents = await registry.totalComponents();
console.log(`Total components preserved: ${totalComponents}`);
```

---

## 🎓 Глоссарий

- **businessId** - уникальный текстовый идентификатор компонента
- **componentId** - уникальный числовой ID в блокчейне
- **CID** - Content Identifier в IPFS
- **Shareable Data** - централизованные словари (features, forms)
- **Creator** - адрес создателя компонента
- **Contributor** - пользователь с правом создания компонентов
- **UUPS** - Universal Upgradeable Proxy Standard
- **Delegatecall** - вызов функций Logic в контексте Proxy
- **Implementation** - Logic контракт (код)
- **Proxy** - контракт-обёртка (данные)

---

## 📚 Дополнительные ресурсы

### Документация OpenZeppelin

- [UUPS Upgradeable](https://docs.openzeppelin.com/contracts/5.x/api/proxy#UUPSUpgradeable)
- [Access Control](https://docs.openzeppelin.com/contracts/5.x/api/access#AccessControl)
- [Reentrancy Guard](https://docs.openzeppelin.com/contracts/5.x/api/utils#ReentrancyGuard)
- [Pausable](https://docs.openzeppelin.com/contracts/5.x/api/utils#Pausable)

### IPFS ресурсы

- [IPFS Documentation](https://docs.ipfs.tech/)
- [Pinata](https://www.pinata.cloud/) - IPFS pinning service
- [Infura IPFS](https://infura.io/product/ipfs) - альтернативный сервис

### Polygon ресурсы

- [Polygon Docs](https://docs.polygon.technology/)
- [Polygonscan](https://polygonscan.com/)
- [Gas Tracker](https://polygonscan.com/gastracker)

---

## 📄 Лицензия

MIT License - см. [LICENSE](../../LICENSE)

---

## 🙏 Благодарности

- OpenZeppelin - за upgradeable контракты
- Hardhat - за фреймворк разработки
- IPFS - за децентрализованное хранилище
- Polygon - за быструю и дешёвую сеть
- Amanita Community - за вклад в развитие проекта

---

*Эта документация является частью проекта Amanita Decentralization и защищена лицензией MIT.*

**Версия документации:** 1.0.0  
**Последнее обновление:** 2025-01-07  
**Статус:** ✅ Production Ready


