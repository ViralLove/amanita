# Архитектура решения: Task 1 — ActivityRegistry контракт (TDD)

**Идентификатор:** task-Activities-1  
**Таск:** task-implement-activity-registry-contract-tdd.md  
**Дата:** 2026-01-29  
**Назначение:** Подробная архитектура решения по всем аспектам таска; референс для реализации и тестов

**Связанные документы:**
- `roles-architecture-synthesis.md` — система ролей (ACTIVITY_CREATOR_ROLE, только active, без модерации)
- `task-Activities-1.md` — рабочая документация (UUPS, тесты, эталон ProductRegistry)
- `decision-points-architecture-task1.md` — принятые решения

---

## 1. Обзор решения

ActivityRegistry — смарт-контракт источника истины (Source of Truth) для активностей (events/services) в экосистеме Amanita. Реализуется в виде **UUPS upgradeable** пары Logic + Proxy, с проверкой создателя через **SpiralEngine** (роль ACTIVITY_CREATOR_ROLE + активация по инвайту). Состояние активности на контракте — только флаг **active** (черновик / опубликовано); без enum статусов и без модерации on-chain. События эмитятся с **инициатором** (indexed address), по образцу ProductRegistry и OrganicComponentRegistry.

---

## 2. Архитектура контракта (UUPS)

### 2.1 Компоненты

| Компонент | Файл | Назначение |
|-----------|------|------------|
| **Logic** | `contracts/ActivityRegistryLogic.sol` | Вся бизнес-логика и state variables. Наследует Initializable, UUPSUpgradeable, AccessControlUpgradeable, PausableUpgradeable, ReentrancyGuardUpgradeable, реализует IActivityRegistry. |
| **Proxy** | `contracts/ActivityRegistryProxy.sol` | Минимальный контракт: наследует ERC1967Proxy, конструктор `(implementation, initData)`. Хранит состояние, делегирует вызовы в Logic через delegatecall. |
| **Интерфейс** | `contracts/interfaces/IActivityRegistry.sol` | Публичный API: структура Activity, enum ActivityType, события, сигнатуры функций. |

### 2.2 Порядок наследования (Logic)

```solidity
contract ActivityRegistryLogic is
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    IActivityRegistry
```

Порядок совпадает с ProductRegistry; инициализация модулей в `initialize()` в том же порядке: `__AccessControl_init()`, `__UUPSUpgradeable_init()`, `__Pausable_init()`, `__ReentrancyGuard_init()`.

### 2.3 Инициализация

- **initialize(address admin, address _spiralEngine)** — вызывается один раз при деплое Proxy (через конструктор Proxy). Проверки: admin != address(0), _spiralEngine != address(0). Устанавливает `spiralEngine = ISpiralEngine(_spiralEngine)`, выдаёт admin: DEFAULT_ADMIN_ROLE, ADMIN_ROLE, UPGRADER_ROLE.
- **SpiralEngine обязателен:** без установленного SpiralEngine createActivity не должен проходить (проверка в onlyActivatedActivityCreator).

### 2.4 UUPS upgrade

- **_authorizeUpgrade(address newImplementation)** — internal override, только UPGRADER_ROLE; проверка newImplementation != address(0). Вызов апгрейда с Proxy: `activityRegistry.upgradeToAndCall(newLogicAddress, "0x")`.

### 2.5 Storage layout и __gap

- Все state variables объявлены в Logic; при delegatecall физически хранятся в Proxy.
- Порядок переменных при апгрейдах **не менять**; новые переменные добавлять только в конец, перед __gap.
- В конце Logic: **uint256[N] private __gap;** (резерв слотов; N по образцу ProductRegistry, например 48). При добавлении новых полей — уменьшать N.

---

## 3. Модель данных

### 3.1 Enum ActivityType

```solidity
enum ActivityType {
    Event,   // 0
    Service  // 1
}
```

Используется для газовой оптимизации (вместо string). Соответствует вертикальному анализу и Activity Data Model (event vs service).

### 3.2 Структура Activity (только active, без enum status)

**Enum ActivityStatus не вводится.** Состояние «черновик / опубликовано» задаётся только полем **active**.

```solidity
struct Activity {
    uint256 id;
    address creator;
    ActivityType activity_type;
    string metadataCID;   // Arweave/IPFS CID
    bool active;          // false = черновик, true = опубликовано (в поиске)
}
```

- **id** — уникальный идентификатор (счётчик _activityIdCounter).
- **creator** — адрес создателя (msg.sender при createActivity).
- **activity_type** — Event или Service.
- **metadataCID** — CID метаданных в Arweave/IPFS (полный JSON по Activity Data Model — off-chain).
- **active** — false = черновик (не в поиске), true = опубликовано (доступно в getPublishedActivityIds и поиске).

### 3.3 State variables в Logic

| Переменная | Тип | Назначение |
|------------|-----|------------|
| spiralEngine | ISpiralEngine | Контракт SpiralEngine для проверки ACTIVITY_CREATOR_ROLE и usedInviteByUser. |
| activities | mapping(uint256 => Activity) | Основное хранилище: activityId => Activity. |
| activitiesByCreator | mapping(address => uint256[]) | Индекс: creator => список activityId. |
| publishedActivityIds | uint256[] | Список ID опубликованных активностей (active == true); для getPublishedActivityIds. |
| _activityIdCounter | uint256 | Счётчик для генерации следующего activityId (increment при create). |
| __gap | uint256[48] (или N) | Резерв слотов для апгрейдов. |

При activate: добавлять activityId в publishedActivityIds. При deactivate: удалять из publishedActivityIds (swap-and-pop по образцу ProductRegistry _removeFromActiveProducts).

---

## 4. Роли и доступ

### 4.1 Роли в SpiralEngine (используемые ActivityRegistry)

- **ACTIVITY_CREATOR_ROLE** — выдаётся при активации пользователя (activateUser). Проверка в ActivityRegistry: `spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, msg.sender)` и `spiralEngine.usedInviteByUser(msg.sender) != 0`.
- **SELLER_ROLE** в ActivityRegistry не используется (только в ProductRegistry / OrganicComponentRegistry).

См. полную цепочку выдачи ролей в `roles-architecture-synthesis.md`.

### 4.2 Локальные роли в ActivityRegistry (AccessControl)

| Роль | Кто выдаёт | Назначение |
|------|------------|------------|
| DEFAULT_ADMIN_ROLE | При инициализации (admin) | Управление ролями (наследуется от AccessControl). |
| ADMIN_ROLE | При инициализации (admin) | pause, unpause, setSpiralEngine, при необходимости forceDeactivate(activityId). |
| UPGRADER_ROLE | При инициализации (admin) | _authorizeUpgrade (UUPS). |

Роль CREATOR_ROLE в контракте **не хранится** — «создатель» определяется через SpiralEngine (ACTIVITY_CREATOR_ROLE + активация), а владелец конкретной активности — по полю creator в структуре Activity.

### 4.3 Модификаторы

| Модификатор | Условие | Используется в |
|-------------|---------|----------------|
| onlyActivatedActivityCreator | spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, msg.sender) && spiralEngine.usedInviteByUser(msg.sender) != 0 | createActivity |
| onlyOwnActivity(uint256 activityId) | activities[activityId].creator == msg.sender | activateActivity, deactivateActivity |
| whenNotPaused | !paused() | createActivity, activateActivity, deactivateActivity (и при необходимости setSpiralEngine) |
| nonReentrant | ReentrancyGuard | createActivity, activateActivity, deactivateActivity, pause, unpause, setSpiralEngine |
| onlyRole(ADMIN_ROLE) | — | pause, unpause, setSpiralEngine, forceDeactivate (если введена) |
| onlyRole(UPGRADER_ROLE) | — | внутри _authorizeUpgrade |

---

## 5. Функции

### 5.1 Создание и жизненный цикл

| Функция | Сигнатура | Кто может | Поведение |
|---------|-----------|-----------|-----------|
| createActivity | createActivity(ActivityType activity_type, string calldata metadataCID) external returns (uint256 activityId) | onlyActivatedActivityCreator, whenNotPaused, nonReentrant | Валидация: metadataCID не пустой. Инкремент _activityIdCounter, запись в activities, добавление в activitiesByCreator[msg.sender]. Изначально active = false. Эмит ActivityCreated(creator, activityId, activity_type, metadataCID, false). Возврат activityId. |
| activateActivity | activateActivity(uint256 activityId) external | onlyOwnActivity(activityId), whenNotPaused, nonReentrant | Проверка: активность существует, active == false. Установка active = true, добавление activityId в publishedActivityIds. Эмит ActivityActivated(activityId, msg.sender) или ActivityActiveChanged(activityId, true, msg.sender). |
| deactivateActivity | deactivateActivity(uint256 activityId) external | onlyOwnActivity(activityId), whenNotPaused, nonReentrant | Проверка: активность существует, active == true. Установка active = false, удаление activityId из publishedActivityIds (swap-and-pop). Эмит ActivityDeactivated(activityId, msg.sender) или ActivityActiveChanged(activityId, false, msg.sender). |

Опционально: **forceDeactivate(uint256 activityId)** external onlyRole(ADMIN_ROLE) — снятие с публикации любой активности (экстренные случаи). Поведение аналогично deactivateActivity, но без проверки onlyOwnActivity.

### 5.2 View-функции

| Функция | Сигнатура | Поведение |
|---------|-----------|-----------|
| getActivity | getActivity(uint256 activityId) external view returns (Activity memory) | Возврат activities[activityId]. Revert при несуществующей активности (id == 0 или специальная проверка). |
| getActivitiesByCreator | getActivitiesByCreator(address creator) external view returns (uint256[] memory) | Возврат activitiesByCreator[creator]. |
| getPublishedActivityIds | getPublishedActivityIds() external view returns (uint256[] memory) | Возврат publishedActivityIds (snapshot). |

### 5.3 Админ и апгрейд

| Функция | Кто может | Поведение |
|---------|-----------|-----------|
| pause | onlyRole(ADMIN_ROLE), nonReentrant | _pause(). |
| unpause | onlyRole(ADMIN_ROLE), nonReentrant | _unpause(). |
| setSpiralEngine | setSpiralEngine(address _spiralEngine) external onlyRole(ADMIN_ROLE), whenNotPaused, nonReentrant | Проверка _spiralEngine != address(0). Установка spiralEngine = ISpiralEngine(_spiralEngine). Эмит SpiralEngineUpdated(old, new). |
| upgradeToAndCall | UUPS (через Proxy) | Только UPGRADER_ROLE; _authorizeUpgrade. |

### 5.4 Валидация

- **createActivity:** revert при пустом metadataCID (bytes(metadataCID).length == 0).
- **getActivity:** revert при несуществующей активности (например, activity.id == 0 или отдельный маппинг существования).
- **activateActivity / deactivateActivity:** revert если активность не существует или не принадлежит msg.sender; для activate — если уже active; для deactivate — если уже !active.

---

## 6. События (с инициатором)

По образцу ProductRegistry и OrganicComponentRegistry: **инициатор передаётся как indexed address** для аудита и фильтрации.

| Событие | Параметры | Когда эмитится |
|---------|-----------|----------------|
| ActivityCreated | address indexed creator, uint256 indexed activityId, ActivityType activity_type, string metadataCID, bool active | createActivity (active = false). |
| ActivityActivated | uint256 indexed activityId, address indexed initiator | activateActivity (initiator = msg.sender). |
| ActivityDeactivated | uint256 indexed activityId, address indexed initiator | deactivateActivity (initiator = msg.sender). |
| SpiralEngineUpdated | address indexed oldSpiralEngine, address indexed newSpiralEngine | setSpiralEngine. |

Альтернатива двум событиям Activate/Deactivate: одно **ActivityActiveChanged**(uint256 indexed activityId, bool active, address indexed initiator). В архитектуре допустимы оба варианта; в интерфейсе и тестах зафиксировать выбранный.

---

## 7. Custom errors

Рекомендуется использовать custom errors (экономия газа, как в ProductRegistry):

- ZeroAddress, InvalidSpiralEngine, EmptyCID
- ActivityNotFound, ActivityNotActive, ActivityAlreadyActive
- NotActivityCreator (для onlyOwnActivity)
- NotActivatedActivityCreator (для onlyActivatedActivityCreator — когда нет ACTIVITY_CREATOR_ROLE или не активирован)

Имена и набор уточняются при реализации; перечень зафиксировать в IActivityRegistry или в Logic.

---

## 8. Интеграция со SpiralEngine и моком для тестов

### 8.1 Зависимость от SpiralEngine

- ActivityRegistry хранит `ISpiralEngine public spiralEngine;` и при createActivity проверяет через spiralEngine: ACTIVITY_CREATOR_ROLE и usedInviteByUser != 0.
- Интерфейс ISpiralEngine должен содержать: `hasRole(bytes32 role, address account) returns (bool)`, `usedInviteByUser(address user) returns (uint256)`, константу ACTIVITY_CREATOR_ROLE (через getter, например `ACTIVITY_CREATOR_ROLE() returns (bytes32)` если в SpiralEngine добавлена эта роль).

### 8.2 MockSpiralEngine для тестов

- Существующий мок `contracts/mocks/MockSpiralEngine.sol` использует SELLER_ROLE и setUserActivated / grantRole. Для ActivityRegistry в тестах нужно:
  - Либо расширить MockSpiralEngine: добавить **ACTIVITY_CREATOR_ROLE** и вызовы grantRole(ACTIVITY_CREATOR_ROLE, account), setUserActivated(account, true).
  - Либо в тестах вызывать grantRole с константой ACTIVITY_CREATOR_ROLE = keccak256("ACTIVITY_CREATOR_ROLE") и setUserActivated(creator, true) для аккаунтов-создателей активностей.
- В beforeEach тестов: деплой MockSpiralEngine, настройка активации и роли ACTIVITY_CREATOR_ROLE для тестового creator; деплой ActivityRegistry Logic + Proxy с initialize(admin, mockSpiralEngine).

---

## 9. Тестирование

### 9.1 Стек и расположение

- Hardhat, Ethers.js, Mocha, Chai (expect).
- Файл тестов: `contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js` (при необходимости дополнительно `ActivityRegistry.UUPS.smoke.test.js`).
- Документация по инфраструктуре: `contracts/docs/testing-infrastructure.md`.

### 9.2 TDD подход

- Тесты пишутся **до** реализации контракта (Red → Green → Refactor).
- Сначала структура тестового файла и P0 тесты (deployment, createActivity для Event и Service, getActivity, activateActivity, deactivateActivity, события, access control, валидация); запуск — RED. Затем реализация Logic, Proxy, Interface — GREEN. Затем P1 и рефакторинг.

### 9.3 P0 тесты (критичные)

| Группа | Что проверять |
|--------|----------------|
| Deployment и инициализация | Деплой Logic, Proxy с initialize(admin, spiralEngine); attach Logic к Proxy; проверка spiralEngine, ролей admin. |
| Создание | createActivity(Event, cid) и createActivity(Service, cid) от активированного ACTIVITY_CREATOR; возврат activityId; начальное active = false; событие ActivityCreated с creator, activityId, activity_type, metadataCID, active. |
| Получение | getActivity(activityId) возвращает корректную структуру; revert при несуществующем id. |
| Публикация и снятие | activateActivity(activityId) только от creator; active становится true; событие с initiator; deactivateActivity(activityId) только от creator; active становится false; событие с initiator. |
| Списки | getActivitiesByCreator(creator) возвращает список id; getPublishedActivityIds() после активации содержит id. |
| Access Control | createActivity без ACTIVITY_CREATOR_ROLE или без активации — revert; activateActivity/deactivateActivity от не-creator — revert; pause/unpause только ADMIN. |
| Валидация | createActivity с пустым CID — revert; activate несуществующей активности — revert. |
| Full State Preservation | Создать несколько активностей, часть активировать; сохранить состояние через getActivity, getActivitiesByCreator, getPublishedActivityIds; выполнить upgradeToAndCall(newLogic); сравнить состояние после апгрейда; проверить создание новой активности (следующий activityId) и activate/deactivate после апгрейда. |

### 9.4 P1 тесты (важные)

- Pausable: при pause() createActivity и activateActivity/deactivateActivity ревертят.
- События: точная проверка аргументов (creator, initiator, activity_type, active).
- Edge cases: множество активностей у одного creator; пустой список getPublishedActivityIds до первой активации.
- Газ: замер createActivity, activateActivity, deactivateActivity (опционально REPORT_GAS).

### 9.5 Вспомогательные функции в тестах

- expectRevertCustom(txPromise, errorName, contract) — ожидание custom error.
- expectEvent(txPromise, contract, eventName, assertFn) — выполнение tx и проверка события с опциональной проверкой args.
- expectNotReverted(txPromise, msg) — транзакция не ревертится.

По образцу ProductRegistry.UUPS.comprehensive.test.js.

### 9.6 Setup beforeEach (comprehensive)

1. Получить signers (admin, creator, otherCreator, user1).
2. Деплой MockSpiralEngine; вызов setUserActivated(creator, true), grantRole(ACTIVITY_CREATOR_ROLE, creator) (и при необходимости otherCreator).
3. Деплой ActivityRegistryLogic; encode initialize(admin.address, spiralEngine.address); деплой ActivityRegistryProxy(logic.address, initCalldata); attach Logic к proxy address.
4. Дальнейшие тесты — через привязанный к proxy контракт (ActivityRegistryLogic.attach(proxy.address)).

---

## 10. Деплой

### 10.1 Последовательность

1. Деплой ActivityRegistryLogic (implementation).
2. Подготовка initCalldata: encode initialize(adminAddress, spiralEngineAddress).
3. Деплой ActivityRegistryProxy(logicAddress, initCalldata).
4. Все вызовы — к адресу Proxy (например, Logic.attach(proxyAddress)).

### 10.2 Скрипты

- Опционально: отдельный скрипт `scripts/deploy_activity_registry.js` или расширение `scripts/deploy_full.js` для деплоя ActivityRegistry после SpiralEngine (и при необходимости других контрактов). В скрипте: получение адреса SpiralEngine из окружения или предыдущего деплоя, вызов деплоя Logic и Proxy, вывод адреса Proxy.

---

## 11. Файлы и артефакты

| Артефакт | Путь | Описание |
|----------|------|----------|
| ActivityRegistryLogic | contracts/ActivityRegistryLogic.sol | Logic-контракт (новая реализация). |
| ActivityRegistryProxy | contracts/ActivityRegistryProxy.sol | Proxy ERC1967 (новый). |
| IActivityRegistry | contracts/interfaces/IActivityRegistry.sol | Интерфейс (новый). |
| Тесты comprehensive | contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js | Comprehensive test suite (новый). |
| Тесты smoke | contracts/tests/ActivityRegistry.UUPS.smoke.test.js | Опционально; быстрая проверка деплоя и базовых вызовов. |
| MockSpiralEngine | contracts/mocks/MockSpiralEngine.sol | Существующий; при необходимости расширить поддержкой ACTIVITY_CREATOR_ROLE. |
| Деплой-скрипт | scripts/deploy_activity_registry.js или в deploy_full.js | Опционально. |

В SpiralEngine (вне scope таска 1, но для полной интеграции): добавление константы ACTIVITY_CREATOR_ROLE и выдача этой роли при activateUser (см. roles-architecture-synthesis.md).

---

## 12. Риски и митигации

| Риск | Митигация |
|------|-----------|
| Потеря состояния при UUPS upgrade | Строго сохранять порядок state variables; использовать __gap; тесты Full State Preservation (как в ProductRegistry). |
| Несовместимость с MockSpiralEngine | Использовать в моке ту же сигнатуру hasRole(bytes32, address) и usedInviteByUser(address); в тестах выдавать ACTIVITY_CREATOR_ROLE и активацию. |
| Высокий газ createActivity | Использовать enum ActivityType, calldata для metadataCID, indexed в событиях; замерять газ в тестах. |
| Ошибки в логике publishedActivityIds | Тесты: после activate список getPublishedActivityIds содержит id; после deactivate — не содержит; при upgrade список сохраняется. |

---

## 13. Соответствие AC/DoD таска

Настоящая архитектура приводит к следующему соответствию с разделом AC/DoD таска (с учётом упрощения «только active»):

- Контракт: ActivityRegistryLogic, ActivityRegistryProxy, IActivityRegistry — созданы; компиляция без ошибок; структура Activity с id, creator, activity_type, metadataCID, active (без enum ActivityStatus); функции createActivity, getActivity, activateActivity, deactivateActivity, getActivitiesByCreator, getPublishedActivityIds; события ActivityCreated, ActivityActivated, ActivityDeactivated (или ActivityActiveChanged) с инициатором; UUPS, AccessControl (ADMIN_ROLE, UPGRADER_ROLE), Pausable, ReentrancyGuard.
- Тесты: comprehensive (и при необходимости smoke); TDD; setup с MockSpiralEngine и ACTIVITY_CREATOR_ROLE; P0 — deployment, create (Event/Service), get, activate, deactivate, списки, события, access control, валидация, Full State Preservation; P1 — Pausable, edge cases, газ; все тесты проходят.
- Интеграция: контракт работает с MockSpiralEngine (и с реальным SpiralEngine после добавления ACTIVITY_CREATOR_ROLE); следует паттернам ProductRegistry.
- Деплой: скрипт опционален; деплой на Hardhat localhost и верификация — по требованию.

Пункты таска, ссылающиеся на «updateActivityStatus» и «enum ActivityStatus», трактуются в смысле **activateActivity / deactivateActivity** и **только active** согласно roles-architecture-synthesis и принятым решениям.

---

## 14. План реализации (подробный)

План разбит на фазы в порядке TDD (Red → Green → Refactor) и интеграции. Каждая фаза завершается проверкой (чеклист и команды).

---

### Фаза 0: Подготовка мока и констант

**Цель:** Обеспечить возможность тестировать ActivityRegistry с проверкой ACTIVITY_CREATOR_ROLE и активации.

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 0.1 | Решить: расширять MockSpiralEngine или использовать существующий grantRole(bytes32, address). | Если мок уже поддерживает произвольный bytes32 — достаточно в тестах задать ACTIVITY_CREATOR_ROLE = keccak256("ACTIVITY_CREATOR_ROLE") и вызывать grantRole(ACTIVITY_CREATOR_ROLE, creator), setUserActivated(creator, true). |
| 0.2 | При необходимости добавить в MockSpiralEngine константу ACTIVITY_CREATOR_ROLE (bytes32 public constant) и при необходимости отдельный grantActivityCreatorRole(address) для ясности тестов. | contracts/mocks/MockSpiralEngine.sol — без изменения логики hasRole/usedInviteByUser; только константа и/или обёртка. |
| 0.3 | Зафиксировать в тестах или в общем месте константу ACTIVITY_CREATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVITY_CREATOR_ROLE")) для использования в grantRole. | В тестах: const ACTIVITY_CREATOR_ROLE = ...; await spiralEngine.grantRole(ACTIVITY_CREATOR_ROLE, creator.address); await spiralEngine.setUserActivated(creator.address, true); |

**Проверка:** MockSpiralEngine деплоится; в тестах можно вызвать grantRole(ACTIVITY_CREATOR_ROLE, account) и setUserActivated(account, true); hasRole и usedInviteByUser возвращают ожидаемые значения.

---

### Фаза 1: TDD Red — интерфейс и тесты (ожидаем падение)

**Цель:** Зафиксировать контракт API через интерфейс и тесты; запуск тестов даёт RED (контракт отсутствует или не компилируется).

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 1.1 | Создать `contracts/interfaces/IActivityRegistry.sol`. | Файл создан. |
| 1.2 | Объявить в интерфейсе: enum ActivityType { Event, Service }; struct Activity { uint256 id; address creator; ActivityType activity_type; string metadataCID; bool active; }. | IActivityRegistry.sol |
| 1.3 | Объявить события: ActivityCreated(address indexed creator, uint256 indexed activityId, ActivityType activity_type, string metadataCID, bool active); ActivityActivated(uint256 indexed activityId, address indexed initiator); ActivityDeactivated(uint256 indexed activityId, address indexed initiator); SpiralEngineUpdated(address indexed oldSpiralEngine, address indexed newSpiralEngine). | IActivityRegistry.sol |
| 1.4 | Объявить функции: createActivity(ActivityType, string calldata metadataCID) external returns (uint256); getActivity(uint256) external view returns (Activity memory); activateActivity(uint256) external; deactivateActivity(uint256) external; getActivitiesByCreator(address) external view returns (uint256[] memory); getPublishedActivityIds() external view returns (uint256[] memory); setSpiralEngine(address) external. | IActivityRegistry.sol |
| 1.5 | Создать `contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`. Скопировать структуру из ProductRegistry.UUPS.comprehensive.test.js (describe, beforeEach, хелперы expectRevertCustom, expectEvent, expectNotReverted). | Файл тестов создан. |
| 1.6 | В beforeEach: деплой MockSpiralEngine; настройка ACTIVITY_CREATOR_ROLE и setUserActivated для creator (и при необходимости otherCreator); деплой ActivityRegistryLogic; encode initialize(admin, spiralEngine); деплой ActivityRegistryProxy(logic, initCalldata); attach Logic к proxy; сохранение в переменные (activityRegistry, spiralEngine, admin, creator, otherCreator, user1). | Тесты: setup готов. |
| 1.7 | Написать P0 тесты: deployment и инициализация (spiralEngine, роли admin); createActivity(Event, cid) от creator → activityId, событие ActivityCreated, getActivity возвращает структуру с active=false; createActivity(Service, cid); getActivity несуществующего id → revert; activateActivity(activityId) от creator → active=true, событие с initiator; deactivateActivity(activityId) от creator → active=false, событие; getActivitiesByCreator(creator) содержит id; getPublishedActivityIds() до/после activate; createActivity без роли/без активации → revert; activateActivity/deactivateActivity от не-creator → revert; pause → createActivity ревертит; пустой metadataCID → revert. | Все P0 тесты написаны. |
| 1.8 | Добавить тест Full State Preservation: создать несколько активностей, часть активировать; сохранить состояние через getActivity, getActivitiesByCreator, getPublishedActivityIds; upgradeToAndCall(newLogic); сравнить состояние после апгрейда; создать новую активность (следующий activityId), activate. | Тест state preservation добавлен. |
| 1.9 | Запустить тесты: `npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`. | Ожидаем: RED (контракт не найден или не компилируется). |

**Проверка:** Интерфейс компилируется (если подключить к временному контракту); тесты запускаются и падают из-за отсутствия Logic/Proxy.

---

### Фаза 2: Реализация Logic (минимальная, без UUPS пока — опционально)

**Цель:** Иметь компилируемый Logic с минимальным набором функций для быстрой проверки. Альтернатива: сразу писать полный Logic с UUPS (см. фазу 3).

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 2.1 | Создать `contracts/ActivityRegistryLogic.sol`. | Файл создан. |
| 2.2 | Подключить импорты: Initializable, AccessControlUpgradeable, PausableUpgradeable, ReentrancyGuardUpgradeable, IActivityRegistry, ISpiralEngine (без UUPSUpgradeable — UUPS в фазе 3). | Logic компилируется. |
| 2.3 | Объявить константы: LOGIC_VERSION, UPGRADER_ROLE, ADMIN_ROLE; константу ACTIVITY_CREATOR_ROLE не хранить в Logic — брать из spiralEngine или через bytes32(keccak256("ACTIVITY_CREATOR_ROLE")) при проверке. В тестах мок возвращает hasRole для любого role; в Logic проверять spiralEngine.hasRole(spiralEngine.ACTIVITY_CREATOR_ROLE(), msg.sender) — значит в ISpiralEngine нужен getter ACTIVITY_CREATOR_ROLE(). Либо в Logic задать bytes32 public constant ACTIVITY_CREATOR_ROLE = keccak256("ACTIVITY_CREATOR_ROLE") и проверять spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, msg.sender). | Константы заданы. |
| 2.4 | Объявить state variables: ISpiralEngine public spiralEngine; mapping(uint256 => Activity) private activities; mapping(address => uint256[]) private activitiesByCreator; uint256[] private publishedActivityIds; uint256 private _activityIdCounter; uint256[N] private __gap. | Storage layout зафиксирован. |
| 2.5 | Реализовать initialize(admin, _spiralEngine): проверки адресов, __AccessControl_init(), __Pausable_init(), __ReentrancyGuard_init(), spiralEngine = ISpiralEngine(_spiralEngine), _grantRole(DEFAULT_ADMIN_ROLE/ADMIN_ROLE/UPGRADER_ROLE, admin). Без __UUPSUpgradeable_init() — UUPS в фазе 3. | initialize готов. |
| 2.6 | Реализовать custom errors: ZeroAddress, InvalidSpiralEngine, EmptyCID, ActivityNotFound, ActivityNotActive, ActivityAlreadyActive, NotActivityCreator, NotActivatedActivityCreator. | Errors готовы. |
| 2.7 | Реализовать модификатор onlyActivatedActivityCreator: spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, msg.sender) && spiralEngine.usedInviteByUser(msg.sender) != 0. Реализовать onlyOwnActivity(activityId): activities[activityId].creator == msg.sender. | Модификаторы готовы. |
| 2.8 | Реализовать createActivity(activity_type, metadataCID): whenNotPaused, nonReentrant, onlyActivatedActivityCreator; валидация metadataCID; unchecked { ++_activityIdCounter }; запись в activities, в activitiesByCreator[msg.sender]; emit ActivityCreated; return activityId. | createActivity готов. |
| 2.9 | Реализовать getActivity(activityId): возврат activities[activityId]; revert при несуществующей (id == 0). | getActivity готов. |
| 2.10 | Реализовать activateActivity(activityId): whenNotPaused, nonReentrant, onlyOwnActivity(activityId); проверка !activities[activityId].active; active = true; publishedActivityIds.push(activityId); emit ActivityActivated(activityId, msg.sender). | activateActivity готов. |
| 2.11 | Реализовать deactivateActivity(activityId): whenNotPaused, nonReentrant, onlyOwnActivity(activityId); проверка activities[activityId].active; active = false; удаление activityId из publishedActivityIds (swap-and-pop, аналог _removeFromActiveProducts в ProductRegistry). | deactivateActivity готов. |
| 2.12 | Реализовать getActivitiesByCreator(creator), getPublishedActivityIds(): возврат массивов. | View-функции готовы. |
| 2.13 | Реализовать pause(), unpause(): onlyRole(ADMIN_ROLE), nonReentrant. Реализовать setSpiralEngine(_spiralEngine): onlyRole(ADMIN_ROLE), whenNotPaused, nonReentrant; проверка _spiralEngine != address(0); spiralEngine = ISpiralEngine(_spiralEngine); emit SpiralEngineUpdated. | Админ-функции готовы. |
| 2.14 | Добавить в IActivityRegistry недостающие сигнатуры (если что-то упущено). Собрать: `npx hardhat compile`. | Компиляция без ошибок. |

**Проверка:** ActivityRegistryLogic компилируется; интерфейс IActivityRegistry реализован в Logic (implements IActivityRegistry).

---

### Фаза 3: UUPS в Logic, Proxy и привязка к тестам

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 3.1 | **Добавить UUPS в Logic:** импорт и наследование UUPSUpgradeable; в initialize добавить вызов __UUPSUpgradeable_init(); реализовать _authorizeUpgrade(address newImplementation) internal override: onlyRole(UPGRADER_ROLE), проверка newImplementation != address(0), revert ZeroAddress при нуле. | Logic с UUPS, компилируется. |
| 3.2 | Создать `contracts/ActivityRegistryProxy.sol`. Наследование ERC1967Proxy; конструктор (address implementation, bytes memory initData) ERC1967Proxy(implementation, initData). | ActivityRegistryProxy.sol создан. |
| 3.3 | В Hardhat config (или в тестах) убедиться, что компилируются ActivityRegistryLogic и ActivityRegistryProxy. Перевести тесты на деплой Proxy + Logic, attach Logic ABI к Proxy. Запустить тесты: `npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`. | Ожидаем: часть тестов проходит (GREEN), часть может падать — поправить логику (например, проверка несуществующей активности по id == 0 или по отдельному маппингу). |
| 3.4 | Исправить все падающие тесты: доработка Logic (проверки, порядок push в publishedActivityIds, swap-and-pop при deactivate). Добавить тест upgradeToAndCall от не-UPGRADER → AccessControlUnauthorizedAccount; тест Full State Preservation после upgradeToAndCall. | Все P0 тесты зелёные. |
| 3.5 | Добавить при необходимости forceDeactivate(activityId) onlyRole(ADMIN_ROLE) и тест: admin снимает с публикации чужую активность. | Опционально. |

**Проверка:** `npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js` — все написанные тесты проходят.

---

### Фаза 4: Full State Preservation и P1

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 4.1 | Убедиться, что тест Full State Preservation полный: несколько активностей от разных creator, часть active, часть неактивных; сохранение всех getActivity, getActivitiesByCreator для каждого creator, getPublishedActivityIds; upgrade; сравнение всех полей и массивов; создание новой активности (activityId = _activityIdCounter) и activate. | Тест state preservation проходит. |
| 4.2 | Добавить P1 тесты: вызов createActivity при pause() → revert; несколько активностей у одного creator; getPublishedActivityIds пустой до первой активации. | P1 тесты добавлены и проходят. |
| 4.3 | Запуск с отчётом по газу: REPORT_GAS=true npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js. Зафиксировать порядок величин газа для createActivity, activateActivity, deactivateActivity. | Метрики газа зафиксированы. |

**Проверка:** Все тесты проходят; Full State Preservation зелёный; газ в разумных пределах.

---

### Фаза 5: Рефакторинг и консистентность

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 5.1 | Привести код Logic к стилю ProductRegistry: секции (константы, errors, state, gap, init, UUPS, модификаторы, функции, view, admin), комментарии NatSpec. | Читаемость и консистентность. |
| 5.2 | Убедиться, что порядок state variables совпадает с планом и не нарушается при апгрейдах; __gap в конце. | Storage layout стабилен. |
| 5.3 | Вынести общие хелперы тестов (expectRevertCustom, expectEvent) в один блок или файл, если ещё не вынесены. | Тесты без дублирования. |
| 5.4 | Повторный прогон всех тестов после рефакторинга. | Все тесты по-прежнему проходят. |

**Проверка:** Код готов к ревью; тесты стабильны.

---

### Фаза 6: Smoke-тест (опционально)

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 6.1 | Создать `contracts/tests/ActivityRegistry.UUPS.smoke.test.js`: минимальный beforeEach (MockSpiralEngine + ACTIVITY_CREATOR_ROLE + активация, деплой Logic + Proxy), один тест createActivity(Event, cid) и activateActivity(1). | Smoke-тест готов. |
| 6.2 | Запустить smoke: `npx hardhat test contracts/tests/ActivityRegistry.UUPS.smoke.test.js`. | Быстрая проверка деплоя и базового сценария. |

**Проверка:** Smoke проходит за несколько секунд.

---

### Фаза 7: Деплой-скрипт (опционально)

| Шаг | Действие | Артефакт / результат |
|-----|----------|----------------------|
| 7.1 | Создать `scripts/deploy_activity_registry.js` или добавить шаг в существующий deploy_full.js: получение адреса SpiralEngine (из аргументов/env/предыдущего деплоя), деплой ActivityRegistryLogic, encode initialize(admin, spiralEngine), деплой ActivityRegistryProxy(logic, initCalldata), вывод адреса Proxy и при необходимости сохранение в конфиг/файл. | Скрипт готов. |
| 7.2 | Прогнать деплой на Hardhat localhost: `npx hardhat node` в одном терминале, в другом — вызов скрипта деплоя. | ActivityRegistry доступен по адресу Proxy. |

**Проверка:** Деплой на localhost успешен; вызов getActivity(0) или createActivity через Proxy корректен (по сценарию).

---

### Сводный чеклист по артефактам

| Артефакт | Фаза | Чеклист |
|----------|------|---------|
| IActivityRegistry.sol | 1 | Enum ActivityType; struct Activity (id, creator, activity_type, metadataCID, active); события с initiator; все сигнатуры функций. |
| MockSpiralEngine | 0 | Поддержка ACTIVITY_CREATOR_ROLE (константа или grantRole(role, account)); setUserActivated; hasRole; usedInviteByUser. |
| ActivityRegistryLogic.sol | 2, 3 | Наследование UUPS, AccessControl, Pausable, ReentrancyGuard; initialize; _authorizeUpgrade; onlyActivatedActivityCreator, onlyOwnActivity; createActivity, getActivity, activateActivity, deactivateActivity; getActivitiesByCreator, getPublishedActivityIds; pause, unpause, setSpiralEngine; custom errors; __gap. |
| ActivityRegistryProxy.sol | 3 | ERC1967Proxy; конструктор (implementation, initData). |
| ActivityRegistry.UUPS.comprehensive.test.js | 1, 3, 4 | beforeEach с MockSpiralEngine и ACTIVITY_CREATOR_ROLE; P0 тесты (deployment, create Event/Service, get, activate, deactivate, списки, события, access control, валидация, pause); Full State Preservation; P1 (edge cases, газ). |
| ActivityRegistry.UUPS.smoke.test.js | 6 | Минимальный setup; один сценарий create + activate. |
| deploy_activity_registry.js | 7 | Деплой Logic и Proxy; initialize(admin, spiralEngine); вывод адреса Proxy. |

---

### Порядок выполнения (кратко)

1. **Фаза 0** — подготовка мока (ACTIVITY_CREATOR_ROLE в тестах или в MockSpiralEngine).
2. **Фаза 1** — IActivityRegistry + тесты (RED).
3. **Фаза 2** — ActivityRegistryLogic (все функции и модификаторы).
4. **Фаза 3** — ActivityRegistryProxy; прогон тестов до GREEN.
5. **Фаза 4** — Full State Preservation и P1 тесты.
6. **Фаза 5** — рефакторинг и консистентность с ProductRegistry.
7. **Фаза 6** — smoke-тест (опционально).
8. **Фаза 7** — деплой-скрипт (опционально).

После фазы 5 контракт готов к передаче в интеграцию (Epic Фаза 1, bot ActivityRegistryService). Деплой и расширение SpiralEngine (ACTIVITY_CREATOR_ROLE в основном контракте) — отдельные задачи.

---

## Недореализованное и план реализации

Ниже — всё, что по текущему состоянию не реализовано или помечено опционально, с подробностями и пошаговым планом закрытия. Референс оценки: task1-acceptance-evaluation.md.

---

### 1. Деплой-скрипт и проверка на localhost (Фаза 7 — опционально)

**Что недореализовано:**
- Отдельного скрипта `scripts/deploy_activity_registry.js` нет.
- В `scripts/deploy_full.js` явного шага деплоя ActivityRegistry нет (адрес SpiralEngine, деплой Logic и Proxy, вывод адреса Proxy не автоматизированы для ActivityRegistry).
- Деплой на Hardhat localhost не проверялся: нет воспроизводимой процедуры «поднять ноду → вызвать скрипт → получить адрес Proxy → проверить вызов getActivity(0) или createActivity».

**Зачем нужно:** закрытие критериев приёмки по деплою (task-implement-activity-registry-contract-tdd.md); возможность поднимать локальный стек с ActivityRegistry для интеграционных проверок и бэкенда.

**План реализации:**

| Шаг | Действие | Критерий приёмки |
|-----|----------|------------------|
| 7.1.1 | Определить источник адреса SpiralEngine для деплоя: (a) аргумент CLI, (b) env (например `SPIRAL_ENGINE_ADDRESS`), (c) конфиг/файл после предыдущего деплоя (если ActivityRegistry деплоится в составе полного стека). Зафиксировать в комментарии скрипта или в README деплоя. | Однозначный способ передачи адреса SpiralEngine. |
| 7.1.2 | Создать `scripts/deploy_activity_registry.js` (или добавить функцию/шаг в существующий скрипт). Последовательность: загрузка ethers/Hardhat, получение signer (deployer), получение адреса SpiralEngine (по выбранному в 7.1.1 способу), деплой `ActivityRegistryLogic`, вызов `logic.getAddress()`, кодирование `initialize(admin, spiralEngine)` через `logic.interface.encodeFunctionData("initialize", [adminAddress, spiralEngineAddress])`, деплой `ActivityRegistryProxy` с аргументами `(logicAddress, initCalldata)`, вывод в консоль адреса Proxy (и при необходимости Logic). | Скрипт выполняется без ошибок; в stdout адрес Proxy. |
| 7.1.3 | Опционально: запись адресов Proxy (и Logic) в конфиг или файл (например `deployments/localhost/activity_registry.json`) по образцу существующих скриптов проекта. | Повторные вызовы других скриптов могут читать адрес ActivityRegistry из одного места. |
| 7.2.1 | В одном терминале запустить `npx hardhat node`. В другом — выполнить скрипт деплоя с указанием сети localhost (или default). Убедиться, что в выводе есть адрес Proxy. | Деплой на localhost завершается успешно. |
| 7.2.2 | Проверка контракта: через `npx hardhat console --network localhost` или одноразовый скрипт: attach Logic ABI к адресу Proxy, вызвать `getActivity(0)` — ожидаем revert (ActivityNotFound) или корректную ошибку; вызвать `createActivity(0, "QmTest")` от имени аккаунта с ACTIVITY_CREATOR_ROLE в SpiralEngine (если SpiralEngine уже задеплоен и настроен) — при успехе получить activityId. Альтернатива: минимальный e2e-скрипт, который деплоит MockSpiralEngine, настраивает роль, деплоит ActivityRegistry, создаёт активность, вызывает getActivity(1). | Вызов getActivity(0) и createActivity через Proxy корректен (по сценарию). |

**Результат:** Фаза 7 выполнена; критерии «скрипт деплоя создан» и «деплой на Hardhat localhost работает» закрыты.

---

### 2. Документация контракта (ActivityRegistry.md)

**Что недореализовано:**
- Отдельного файла `contracts/docs/ActivityRegistry.md` нет. Описание API, структуры данных, событий и ролей содержится в solution-architecture-task1-activity-registry.md и в ретроспективах фаз; для быстрого онбординга и критерия «документация контракта» (task-implement, P1) желателен один выделенный документ в `contracts/docs/`.

**Зачем нужно:** закрытие опционального критерия приёмки; единая точка входа для разработчиков, которые подключают бэкенд или пишут скрипты против ActivityRegistry.

**План реализации:**

| Шаг | Действие | Критерий приёмки |
|-----|----------|------------------|
| D.1 | Создать `contracts/docs/ActivityRegistry.md`. Структура: краткое назначение контракта (источник истины для Activity, UUPS Logic+Proxy); ссылка на IActivityRegistry.sol и solution-architecture. | Файл создан. |
| D.2 | Секция «Модель данных»: enum ActivityType (Event, Service); struct Activity (id, creator, activity_type, metadataCID, active); пояснение, что состояние публикации задаётся только полем active (без enum ActivityStatus). | Описание структуры совпадает с контрактом. |
| D.3 | Секция «Основные функции»: createActivity(activity_type, metadataCID) → activityId; getActivity(activityId) → Activity; activateActivity(activityId), deactivateActivity(activityId); getActivitiesByCreator(creator) → uint256[]; getPublishedActivityIds() → uint256[]; условия revert (EmptyCID, ActivityNotFound, NotActivityCreator и т.д.) — по интерфейсу и Logic. | Перечислены все публичные и view-функции и основные ошибки. |
| D.4 | Секция «События»: ActivityCreated, ActivityActivated, ActivityDeactivated, SpiralEngineUpdated — параметры и когда эмитятся. | Описание событий совпадает с IActivityRegistry. |
| D.5 | Секция «Роли и доступ»: ADMIN_ROLE (pause, unpause, setSpiralEngine, forceDeactivate); UPGRADER_ROLE (upgradeToAndCall); проверка создателя через SpiralEngine (ACTIVITY_CREATOR_ROLE, usedInviteByUser) и onlyOwnActivity; ссылка на roles-architecture-synthesis при необходимости. | Роли и модификаторы описаны без противоречий с контрактом. |
| D.6 | Краткая секция «Деплой»: Logic + Proxy, initialize(admin, spiralEngine); ссылка на скрипт деплоя (после реализации п. 1) или на solution-architecture, фаза 7. | Читатель понимает, как контракт разворачивается. |

**Результат:** Критерий «документация контракта в contracts/docs/ActivityRegistry.md» закрыт; при изменении API документ обновлять вместе с интерфейсом.

---

### 3. Осознанные отличия от формулировок таска (не «недореализация»)

В task-implement-activity-registry-contract-tdd.md в AC указаны сущности, которые **намеренно не вводились** по solution-architecture и decision-points. Они не считаются недореализованными в рамках текущей архитектуры; ниже — кратко что «не так» в формулировках и при необходимости **план возможного расширения**, если позже понадобится полное совпадение с таском или вертикальным анализом.

**3.1. Enum ActivityStatus и updateActivityStatus()**

- **В таске / activity-vertical-layers-analysis:** enum ActivityStatus (Draft, SentToReview, Approved, Published), функция updateActivityStatus(activityId, newStatus) с валидацией переходов (state machine).
- **В решении:** только поле **active** (bool) и функции **activateActivity** / **deactivateActivity** (черновик ↔ опубликовано). Обоснование: roles-architecture-synthesis, без модерации on-chain.

**План возможного расширения (если понадобится):**
- Ввести в IActivityRegistry и Logic enum ActivityStatus (Draft, SentToReview, Approved, Published); добавить в struct Activity поле `ActivityStatus status`; при создании устанавливать status = Draft.
- Реализовать updateActivityStatus(uint256 activityId, ActivityStatus newStatus) с проверкой допустимых переходов (например Draft → SentToReview → Approved → Published; откат — отдельно или не допускать). Права: только creator или ADMIN в зависимости от перехода (по решению).
- Эмитить событие ActivityStatusUpdated(activityId, oldStatus, newStatus, initiator).
- Обновить getPublishedActivityIds(): в список включать только активности со status == Published (вместо или в дополнение к active; при совместимости с текущим API оставить active синхронным со status == Published).
- **Storage layout:** добавить поле в Activity и уменьшить __gap; при апгрейде миграция данных не требуется, если новое поле инициализируется по умолчанию и логика обрабатывает «старые» записи (active уже есть).
- Тесты: переходы по state machine, недопустимые переходы → revert, события ActivityStatusUpdated.

**3.2. Событие ActivityStatusUpdated**

- **В таске:** событие ActivityStatusUpdated.
- **В решении:** события ActivityActivated и ActivityDeactivated.

При введении updateActivityStatus (п. 3.1) добавить событие ActivityStatusUpdated; при сохранении текущей модели оставить как есть — в оценке приёмки зафиксировано как осознанное отличие.

**3.3. CREATOR_ROLE в контракте**

- **В таске:** роли ADMIN_ROLE, CREATOR_ROLE.
- **В решении:** ADMIN_ROLE, UPGRADER_ROLE; «роль создателя» проверяется через SpiralEngine (ACTIVITY_CREATOR_ROLE + usedInviteByUser) и onlyOwnActivity(activityId).

Расширение не обязательно: текущая схема достаточна для Epic и бэкенда. При желании можно ввести в контракте CREATOR_ROLE и выдавать её при первой createActivity или через отдельную функцию — тогда дублирование проверки (SpiralEngine + роль в контракте) нужно явно описать в ролевой модели.

---

### 4. Сводка: что делать для полного закрытия AC

| Элемент | Статус | Действие |
|---------|--------|----------|
| Деплой-скрипт | Не реализован | Выполнить план п. 1 (Фаза 7). |
| Деплой на localhost | Не проверен | Выполнить шаги 7.2.1–7.2.2. |
| ActivityRegistry.md | Не создан | Выполнить план п. 2. |
| ActivityStatus / updateActivityStatus | Не в архитектуре | Оставить как есть или реализовать по плану п. 3.1 при появлении требований. |

После выполнения п. 1 и п. 2 все явные пробелы по критериям приёмки (деплой и документация) закрыты; отличия по модели статусов остаются осознанным архитектурным выбором и при необходимости расширяются по п. 3.

---

**Версия:** 1.1  
**Статус:** Архитектура решения и план реализации для Task 1 (ActivityRegistry).
