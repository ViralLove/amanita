# ActivityRegistry — контракт реестра активностей

## Обзор

`ActivityRegistry` — смарт-контракт **источника истины (Source of Truth)** для активностей (events/services) в экосистеме Amanita. Реализован в виде пары **UUPS upgradeable**: Logic (`ActivityRegistryLogic.sol`) и Proxy (`ActivityRegistryProxy.sol`). Состояние хранится в Proxy, вызовы делегируются в Logic через `delegatecall`.

**Интерфейс:** [contracts/interfaces/IActivityRegistry.sol](../interfaces/IActivityRegistry.sol)  
**Архитектура и план реализации:** [contracts/docs/analysis/tasks/task-Activities-1/solution-architecture-task1-activity-registry.md](analysis/tasks/task-Activities-1/solution-architecture-task1-activity-registry.md)

---

## Модель данных

### Enum ActivityType

Тип активности (газовая оптимизация вместо string):

- `Event` (0)
- `Service` (1)

### Struct Activity

| Поле            | Тип          | Описание |
|-----------------|--------------|----------|
| `id`            | uint256      | Уникальный идентификатор активности |
| `creator`       | address      | Адрес создателя (владельца) |
| `activity_type` | ActivityType | Тип: Event или Service |
| `metadataCID`   | string       | Arweave/IPFS CID метаданных (полный JSON off-chain) |
| `active`        | bool         | `false` = черновик (не в поиске), `true` = опубликовано |

Состояние публикации задаётся **только полем `active`**. Отдельный enum статусов (Draft/SentToReview/Approved/Published) в контракте не вводится — черновик и опубликовано достаточно для текущей модели; см. solution-architecture и decision-points.

---

## Основные функции

### Жизненный цикл

#### `createActivity(ActivityType activity_type, string calldata metadataCID) → uint256 activityId`

Создаёт активность в статусе черновика (`active = false`).

**Revert:**
- `EmptyCID` — пустой `metadataCID`
- `NotActivatedActivityCreator` — у `msg.sender` нет роли ACTIVITY_CREATOR_ROLE в SpiralEngine или `usedInviteByUser == 0`
- `EnforcedPause` — контракт на паузе

**Событие:** `ActivityCreated(creator, activityId, activity_type, metadataCID, false)`

---

#### `activateActivity(uint256 activityId)`

Публикует активность (добавляет в список опубликованных, `active = true`).

**Revert:**
- `ActivityNotFound` — активности с таким id нет (в теле; при несуществующем id раньше срабатывает `NotActivityCreator`)
- `ActivityAlreadyActive` — активность уже опубликована
- `NotActivityCreator` — `msg.sender` не создатель этой активности
- `EnforcedPause` — контракт на паузе

**Событие:** `ActivityActivated(activityId, initiator)`

---

#### `deactivateActivity(uint256 activityId)`

Снимает активность с публикации (`active = false`, удаление из списка опубликованных — swap-and-pop).

**Revert:**
- `ActivityNotFound` — активности с таким id нет
- `ActivityNotActive` — активность уже черновик
- `NotActivityCreator` — `msg.sender` не создатель этой активности
- `EnforcedPause` — контракт на паузе

**Событие:** `ActivityDeactivated(activityId, initiator)`

---

### View-функции

#### `getActivity(uint256 activityId) → Activity memory`

Возвращает структуру активности. **Revert:** `ActivityNotFound` — при `activityId == 0` или несуществующем id.

#### `getActivitiesByCreator(address creator) → uint256[] memory`

Возвращает массив id активностей, созданных указанным `creator`.

#### `getPublishedActivityIds() → uint256[] memory`

Возвращает массив id активностей с `active == true` (опубликованные). Используется для списка/дискавери и синхронизации кэша/индекса.

---

### Админ-функции

#### `pause()` / `unpause()`

Приостановка и снятие приостановки контракта. Доступ: только `ADMIN_ROLE`. При паузе блокируются createActivity, activateActivity, deactivateActivity, setSpiralEngine.

#### `setSpiralEngine(address _spiralEngine)`

Установка адреса контракта SpiralEngine (проверка роли и активации создателя). Доступ: только `ADMIN_ROLE`, при снятой паузе. **Revert:** `ZeroAddress` при `address(0)`.

**Событие:** `SpiralEngineUpdated(oldSpiralEngine, newSpiralEngine)`

#### `forceDeactivate(uint256 activityId)`

Принудительное снятие активности с публикации (в т.ч. чужой). Доступ: только `ADMIN_ROLE`. **Revert:** `ActivityNotFound`, `ActivityNotActive`.

---

## События

| Событие | Параметры | Когда эмитится |
|---------|-----------|----------------|
| `ActivityCreated` | `creator` (indexed), `activityId` (indexed), `activity_type`, `metadataCID`, `active` | После успешного `createActivity` (всегда `active == false`) |
| `ActivityActivated` | `activityId` (indexed), `initiator` (indexed) | После успешного `activateActivity` |
| `ActivityDeactivated` | `activityId` (indexed), `initiator` (indexed) | После успешного `deactivateActivity` или `forceDeactivate` |
| `SpiralEngineUpdated` | `oldSpiralEngine` (indexed), `newSpiralEngine` (indexed) | После успешного `setSpiralEngine` |

---

## Роли и доступ

| Роль | Константа | Назначение |
|------|-----------|------------|
| **ADMIN_ROLE** | `keccak256("ADMIN_ROLE")` | pause, unpause, setSpiralEngine, forceDeactivate |
| **UPGRADER_ROLE** | `keccak256("UPGRADER_ROLE")` | вызов `upgradeToAndCall` (UUPS) |

Проверка «создатель активности»:
- **SpiralEngine:** при `createActivity` требуется, чтобы у `msg.sender` в SpiralEngine были роль `ACTIVITY_CREATOR_ROLE` и `usedInviteByUser(msg.sender) != 0` (модификатор `onlyActivatedActivityCreator`).
- **Владелец активности:** при `activateActivity` и `deactivateActivity` требуется `activities[activityId].creator == msg.sender` (модификатор `onlyOwnActivity`). Роль CREATOR в самом контракте не заведена.

Подробнее о ролях: [roles-architecture-synthesis.md](roles-architecture-synthesis.md).

---

## Деплой

Контракт разворачивается как пара **Logic + Proxy**:

1. Деплой `ActivityRegistryLogic`.
2. Кодирование вызова `initialize(admin, spiralEngine)` (например, `logic.interface.encodeFunctionData("initialize", [adminAddress, spiralEngineAddress])`).
3. Деплой `ActivityRegistryProxy(logicAddress, initCalldata)`.
4. Работа с контрактом — через адрес **Proxy** (ABI Logic, attach к адресу Proxy).

Скрипт деплоя вынесен в отдельный таск в репозитории scripts (другой технический контекст). Детали процедуры деплоя и проверки на localhost см. в [solution-architecture-task1-activity-registry.md](analysis/tasks/task-Activities-1/solution-architecture-task1-activity-registry.md), раздел «Фаза 7: Деплой-скрипт».
