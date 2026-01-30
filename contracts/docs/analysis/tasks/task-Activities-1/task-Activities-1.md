# Task-Activities-1 — Рабочая документация (ActivityRegistry, Фаза 1)

**Идентификатор:** task-Activities-1  
**Фокус:** contracts/  
**Контекст:** Epic Activities API Production (EPIC-001), Фаза 1 — Blockchain Foundation  
**Дата анализа:** 2026-01-29  
**Методология:** run-analysis (@analysis), эталон ProductRegistry + SpiralEngine

---

## 1. Анализ: архитектура UUPSUpgradeable (на примере ProductRegistry)

### 1.1 Разделение Logic / Proxy

| Компонент | Файл | Назначение |
|-----------|------|------------|
| **Logic** | `contracts/ProductRegistryLogic.sol` | Вся бизнес-логика и state variables. Наследует `UUPSUpgradeable`, `Initializable`, `AccessControlUpgradeable`, `PausableUpgradeable`, `ReentrancyGuardUpgradeable`, реализует `IProductRegistry`. |
| **Proxy** | `contracts/ProductRegistryProxy.sol` | Минимальный контракт: наследует `ERC1967Proxy`, только конструктор `(implementation, initData)`. Хранит состояние и делегирует вызовы в Logic через `delegatecall`. |
| **Интерфейс** | `contracts/interfaces/IProductRegistry.sol` | Публичный API: структуры, события, сигнатуры функций (create/update/activate/deactivate, view, admin). |

### 1.2 Порядок наследования и инициализация (Logic)

```solidity
contract ProductRegistryLogic is
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    IProductRegistry
```

- **initialize(admin, _spiralEngine)** — вызывается один раз при деплое Proxy. Вызывает `__AccessControl_init()`, `__UUPSUpgradeable_init()`, `__Pausable_init()`, `__ReentrancyGuard_init()`, устанавливает `spiralEngine`, выдаёт админу `DEFAULT_ADMIN_ROLE`, `ADMIN_ROLE`, `UPGRADER_ROLE`.
- **Хранение состояния:** при `delegatecall` все state variables физически хранятся в Proxy; Logic не хранит данные.

### 1.3 Защита апгрейда (UUPS)

- **\_authorizeUpgrade(address newImplementation)** — `internal override`, вызывается при `upgradeToAndCall`. Проверка: только `UPGRADER_ROLE`; проверка `newImplementation != address(0)`.
- Апгрейд вызывается с Proxy: `productRegistry.upgradeToAndCall(newLogicAddress, "0x")`.

### 1.4 Storage layout и __gap

- Порядок state variables **не менять** при апгрейдах (риск коллизии слотов).
- В конце Logic: `uint256[48] private __gap;` — резерв слотов для будущих переменных; при добавлении новых переменных уменьшать размер gap.

### 1.5 Деплой (последовательность)

1. Deploy `ProductRegistryLogic`.
2. Encode `initialize(admin, spiralEngine)` → `initCalldata`.
3. Deploy `ProductRegistryProxy(logicAddress, initCalldata)`.
4. Работать через Proxy: `Logic.attach(proxyAddress)` — вызовы идут на Proxy, исполнение в Logic.

**Итог для ActivityRegistry:** повторить структуру Logic + Proxy + IActivityRegistry; `initialize(admin, _spiralEngine)`; `_authorizeUpgrade` с `UPGRADER_ROLE`; storage gap; порядок наследования и init-модулей сохранить.

---

## 2. Анализ: инфраструктура тестирования

### 2.1 Стек и расположение

- **Стек:** Hardhat, Ethers.js, Mocha, Chai (expect).
- **Тесты:** `contracts/tests/`.
- **Документация:** `contracts/docs/testing-infrastructure.md`.

### 2.2 Паттерны тестов ProductRegistry (UUPS)

| Файл | Назначение |
|------|------------|
| `ProductRegistry.UUPS.smoke.test.js` | Быстрая проверка: деплой Proxy+Logic, initialize, createProduct, activateProduct, custom errors, ReentrancyGuard, Pausable. |
| `ProductRegistry.UUPS.comprehensive.test.js` | P0: сохранение состояния при upgrade. P1: whenNotPaused на функциях. Access Control. События. |
| `ProductRegistryClearCatalog.test.js` / `.simple.test.js` | Специфика clearSellerCatalog. |
| `ProductRegistry.Integration.test.js` | Интеграция с реальной/моковой инфраструктурой. |

### 2.3 Типичный beforeEach (comprehensive)

1. **Мок SpiralEngine:** `MockSpiralEngine` (contracts/mocks/MockSpiralEngine.sol) — деплой, вызовы `setUserActivated(seller, true)`, `grantRole(SELLER_ROLE, seller)`.
2. **OrganicComponentRegistry UUPS:** деплой Logic → encode initialize(admin) → деплой Proxy → attach Logic к Proxy → `setSpiralEngine(mock)`.
3. **ProductRegistry UUPS:** деплой Logic → encode initialize(admin, spiralEngine) → деплой Proxy → attach Logic к Proxy → `setOrganicComponentRegistry(ocr)`.
4. Создание компонентов в OCR для продавцов (для createProduct).

### 2.4 Вспомогательные функции в тестах

- **expectRevertCustom(txPromise, errorName, contract)** — ожидание custom error (по errorName или по selector в return data).
- **expectEvent(txPromise, contract, eventName, assertFn)** — выполнить tx, распарсить receipt.logs, найти событие, опционально проверить args.
- **expectNotReverted(txPromise, msg)** — убедиться, что tx не ревертится.

### 2.5 Сценарий проверки сохранения состояния (P0)

1. Создать тестовые данные (продукты, активации, catalogVersion, businessIdToProductId, activeProductIds, productsBySeller).
2. Сохранить состояние до апгрейда через публичные getters (getProduct, getAllActiveProductIds, getProductsBySeller, getMyCatalogVersion, getProductIdByBusinessId).
3. Выполнить upgrade: деплой новой Logic V2, вызов от admin `upgradeToAndCall(newLogic, "0x")`.
4. Сравнить состояние после апгрейда с сохранённым (все поля структур, массивы, маппинги).
5. Проверить пост-апгрейд функциональность: создание нового продукта (следующий ID), активация, обновление.

### 2.6 Запуск

- `npx hardhat test`
- Конкретный файл: `npx hardhat test contracts/tests/ProductRegistry.UUPS.comprehensive.test.js`

**Итог для ActivityRegistry:** использовать тот же стек; smoke + comprehensive (state preservation + Pausable + Access Control + события); мок SpiralEngine с `hasRole` и `usedInviteByUser`; хелперы expectRevertCustom/expectEvent; при необходимости мок только для ролей/активации (без OCR, если ActivityRegistry не зависит от компонентов).

---

## 3. Анализ: существующая система ролей

### 3.1 Роли в ProductRegistryLogic

| Константа | Значение | Назначение |
|-----------|----------|------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin | Управление ролями (наследуется от AccessControl). |
| `ADMIN_ROLE` | keccak256("ADMIN_ROLE") | Пауза/unpause, setSpiralEngine, setOrganicComponentRegistry. |
| `UPGRADER_ROLE` | keccak256("UPGRADER_ROLE") | Вызов upgradeToAndCall (в _authorizeUpgrade). |
| `SELLER_ROLE` | keccak256("SELLER_ROLE") | Не хранится в ProductRegistry — запрашивается у SpiralEngine. |

При инициализации админу выдаются: `DEFAULT_ADMIN_ROLE`, `ADMIN_ROLE`, `UPGRADER_ROLE`.

### 3.2 Интеграция с SpiralEngine (роли и активация)

- **SpiralEngine** хранит и выдаёт `SELLER_ROLE` и `ACTIVATOR_ROLE` (собственный AccessControl).
- ProductRegistry **не хранит** SELLER_ROLE у себя, а проверяет через **внешний контракт**: `spiralEngine.hasRole(SELLER_ROLE, msg.sender)` и `spiralEngine.usedInviteByUser(msg.sender) != 0` (активация).
- Модификатор **onlyActivatedSeller:** требует `hasRole(SELLER_ROLE, msg.sender)` и `usedInviteByUser(msg.sender) != 0` в SpiralEngine; иначе `NotASeller` / `NotActivatedUser`.

### 3.3 Модификаторы доступа в ProductRegistry

- `onlyRole(ADMIN_ROLE)` — pause, unpause, setSpiralEngine, setOrganicComponentRegistry.
- `onlyRole(UPGRADER_ROLE)` — внутри _authorizeUpgrade (при вызове upgradeToAndCall с Proxy).
- `onlyActivatedSeller` — createProduct (через SpiralEngine).
- `onlyOwnSellerProduct(productId)` — updateProduct, deactivateProduct, activateProduct (проверка products[productId].seller == msg.sender).

**Итог для ActivityRegistry:** при необходимости «создателя» активности можно аналогично привязать к SpiralEngine (например, та же SELLER_ROLE или отдельная CREATOR_ROLE в SpiralEngine) и ввести onlyActivatedCreator; либо ввести свою роль в ActivityRegistry и выдавать её через admin. Решение зафиксировать в таске: использовать ли SpiralEngine для проверки создателя (как ProductRegistry для seller) или локальные роли.

---

## 4. Анализ: функционал SpiralEngine.sol

### 4.1 Назначение

**SpiralEngine** — контракт спиральной иерархии: инвайты (NFT), активация пользователей, назначение ролей. SBT-функциональность делегируется в SoulIdentity. Для ProductRegistry и ActivityRegistry важны: **роли** и **факт активации** пользователя.

### 4.2 Роли (константы)

- `SELLER_ROLE` — минтинг инвайтов, право создавать продукты (в ProductRegistry).
- `ACTIVATOR_ROLE` — активация пользователей (`activateUser`), выдача SELLER_ROLE (`grantSellerRole`).
- `DEFAULT_ADMIN_ROLE` — suspendUser, setSoulIdentity, доступ к диагностике.

### 4.3 Ключевые функции для регистров (ProductRegistry / ActivityRegistry)

| Функция | Назначение |
|---------|------------|
| **hasRole(bytes32 role, address account)** | Проверка роли (AccessControl). ProductRegistry вызывает `spiralEngine.hasRole(SELLER_ROLE, msg.sender)`. |
| **usedInviteByUser(address user)** | Возвращает использованный инвайт (tokenId+1 или 0). ProductRegistry требует `!= 0` для «активированного» продавца. |
| **grantSellerRole(address user)** | Вызов от ACTIVATOR_ROLE; требует активированного user; выдаёт SELLER_ROLE. |
| **mintInvite(string inviteCode, uint256 expiry)** | SELLER_ROLE; создаёт NFT-инвайт. |
| **activateUser(inviteCode, user, newInviteCodes[12], expiry)** | ACTIVATOR_ROLE; помечает инвайт использованным, записывает usedInviteByUser(user), минтит 12 новых инвайтов пользователю. |

### 4.4 Интерфейс для зависимых контрактов

**ISpiralEngine** (`contracts/interfaces/ISpiralEngine.sol`) — объявляет `SELLER_ROLE()`, `ACTIVATOR_ROLE()`, `hasRole(bytes32, address)`, `usedInviteByUser(address)`, события и остальные view/функции управления. ProductRegistry и мок в тестах ориентируются на этот интерфейс.

### 4.5 Мок для тестов (MockSpiralEngine)

- Константа `SELLER_ROLE`.
- `mapping(address => uint256) usedInviteByUser` — тесты выставляют через `setUserActivated(user, true/false)` (1/0).
- `mapping(bytes32 => mapping(address => bool)) _roles` — выдача через `grantRole(role, account)`, проверка через `hasRole(role, account)`.

**Итог для ActivityRegistry:** если создатель Activity должен быть «активированным» пользователем (как продавец в ProductRegistry), достаточно в ActivityRegistry хранить `ISpiralEngine spiralEngine` и в модификаторе создателя вызывать `spiralEngine.hasRole(???, msg.sender)` и `spiralEngine.usedInviteByUser(msg.sender) != 0`. Роль для создателя Activity можно оставить SELLER_ROLE или ввести в SpiralEngine новую роль (например ACTIVITY_CREATOR_ROLE) — решить в дизайне Фазы 1.

---

## 5. Сводная таблица: что взять из ProductRegistry для ActivityRegistry

| Аспект | ProductRegistry | Рекомендация для ActivityRegistry |
|--------|-----------------|-----------------------------------|
| **UUPS** | Logic + Proxy + I*, initialize(admin, spiralEngine), _authorizeUpgrade(UPGRADER_ROLE), __gap | То же: ActivityRegistryLogic, ActivityRegistryProxy, IActivityRegistry, initialize(admin, _spiralEngine), __gap. |
| **Тесты** | Smoke + Comprehensive (state preservation, Pausable, Access Control), expectRevertCustom/expectEvent, MockSpiralEngine | То же; при необходимости упрощённый мок (только hasRole + usedInviteByUser). |
| **Роли** | ADMIN_ROLE, UPGRADER_ROLE; SELLER через SpiralEngine | ADMIN_ROLE, UPGRADER_ROLE; создатель Activity — через SpiralEngine (SELLER или отдельная роль). |
| **SpiralEngine** | Зависимость для onlyActivatedSeller (hasRole + usedInviteByUser) | Аналогично для «создателя» Activity; интерфейс ISpiralEngine уже есть. |
| **Доп. защиты** | Pausable, ReentrancyGuard, custom errors | Сохранить для ActivityRegistry. |

---

## 6. Ссылки на файлы (эталон)

| Ресурс | Путь |
|--------|------|
| Logic | `contracts/ProductRegistryLogic.sol` |
| Proxy | `contracts/ProductRegistryProxy.sol` |
| Интерфейс | `contracts/interfaces/IProductRegistry.sol` |
| SpiralEngine | `contracts/SpiralEngine.sol` |
| ISpiralEngine | `contracts/interfaces/ISpiralEngine.sol` |
| MockSpiralEngine | `contracts/mocks/MockSpiralEngine.sol` |
| Тесты UUPS comprehensive | `contracts/tests/ProductRegistry.UUPS.comprehensive.test.js` |
| Тесты UUPS smoke | `contracts/tests/ProductRegistry.UUPS.smoke.test.js` |
| Инфраструктура тестов | `contracts/docs/testing-infrastructure.md` |
| Таск реализации контракта | `contracts/docs/analysis/tasks/task-implement-activity-registry-contract-tdd.md` |
| Вертикальные слои (структура Activity) | `docs/tech/activity-vertical-layers-analysis.md` |

---

**Версия:** 1.0  
**Статус:** Рабочая документация анализа; реализация — по task-implement-activity-registry-contract-tdd.md
