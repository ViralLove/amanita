# Синтез архитектуры ролей: SpiralEngine, Products, Components, Activities

**Идентификатор:** task-Activities-1  
**Дата:** 2026-01-29  
**Тип документа:** Архитектурный референс по ролям (живой документ, будет дополняться)

---

## Дисклеймер

В ходе анализа рассматривались варианты с **модерацией on-chain** и **многостатусным lifecycle** (Draft → SentToReview → Approved → Published). Этот функционал **сознательно не реализуется** в контрактах для упрощения работы. Логика одобрения контента и соответствия кодексу экосистемы перенесена в **авторизованные UI**, которые контролируются администраторами экосистемы (валидация по гайду, доступ к API только для авторизованных приложений). On-chain остаётся минимум: creator, флаг active (черновик / опубликовано), события с инициатором.

---

## 1. Принятые решения (фиксация)

| № | Точка решения | Выбор |
|---|----------------|-------|
| 1 | Идентичность создателя Activity | SpiralEngine + **ACTIVATOR_ROLE** + активация (`usedInviteByUser != 0`). |
| 2 | Поле состояния на контракте | Только **active** (черновик / опубликовано). Публикация через авторизованный UI, проверяющий кодекс. |
| 3 | «Свой UI» и качество контента | Авторизация приложений в API (secret key / app auth); валидация по гайду в UI (GPT инструкции). |
| 4 | Роль создателя в SpiralEngine | **ACTIVATOR_ROLE** (единая роль для создателей активностей; SELLER выдаётся по отдельному алгоритму, см. раздел 2). |
| 5 | Зависимость от SpiralEngine | Обязательна; без инвайта нельзя стать activity provider. |
| 6 | События | С инициатором (indexed address), как у Products и Components. |

---

## 2. Цепочка выдачи ролей (полная логика)

### 2.1 Стартовый админ и рутовые инвайты

- **DEFAULT_ADMIN_ROLE** (стартовый админ) — назначается при деплое SpiralEngine (например, constructor выдаёт deployer'у).
- Стартовый админ создаёт **рутовые инвайты** (mintInvite) и через **activateUser** активирует первых пользователей экосистемы.

### 2.2 Что выдаётся при активации (на каждый инвайт)

При вызове **activateUser**(inviteCode, user, newInviteCodes, expiry) пользователь `user` считается активированным (`usedInviteByUser(user) != 0`). **В момент активации** (или сразу после в рамках той же логики) пользователю выдаются:

| Роль | Выдаётся при активации? | Кто выдаёт | Назначение |
|------|-------------------------|------------|------------|
| **ACTIVATOR_ROLE** | **Да** | Активатор (тот, кто вызвал activateUser) или контракт по правилам SpiralEngine | Активировать тех, кто пришёл по инвайтам этого пользователя (минтить инвайты, вызывать activateUser для своих приглашённых) и выступать создателем активностей (ActivityRegistry) при наличии инвайта. |
| **SELLER_ROLE** | **Нет** | Не выдаётся при активации | Продажи (ProductRegistry), создание компонентов (OrganicComponentRegistry). Доступ к SELLER — только по одному из путей ниже. |

Итог: **каждый активированный пользователь** получает возможность быть активатором (растить круг) и создателем активностей, но **не продавцом**. Роль продавца выдаётся отдельно и жёстко контролируется.

### 2.3 Алгоритм выдачи SELLER_ROLE (два пути)

SELLER можно получить **только одним из двух путей**:

**Путь 1 — напрямую от админа (высший уровень допуска)**  
- Админ (DEFAULT_ADMIN_ROLE или уполномоченная роль) вручную выдаёт SELLER_ROLE пользователю.  
- Используется для доверенных участников, партнёров, первых продавцов.  
- Реализация: вызов типа `grantSellerRoleByAdmin(address user)` только от DEFAULT_ADMIN_ROLE (или отдельной ADMIN/SELLER_GRANTER роли).

**Путь 2 — через рекомендации активаторов с наработками**  
- Пользователь получает SELLER_ROLE только при выполнении условия: **не менее 3 рекомендаций** от других активаторов, которые **уже имеют наработки в системе** (продажи и/или отзывы).  
- Концептуально: «проверенные» активаторы голосуют за допуск нового продавца; детали (что считать наработками, как хранить рекомендации — on-chain или off-chain, как учитывать 3 рекомендации) будут зафиксированы позже.  
- Реализация — не в текущем scope; важно зафиксировать **саму концептуальную логику**: SELLER не раздаётся при активации, а только через админа или через механизм рекомендаций с порогом и учётом репутации активаторов.

Сводка:

| Путь | Условие | Уровень допуска |
|------|---------|-----------------|
| От админа | Решение DEFAULT_ADMIN_ROLE (или уполномоченной роли) | Высший; без дополнительных условий. |
| Рекомендации | ≥3 рекомендации от активаторов с наработками (продажи/отзывы) | Социальная верификация; детали реализации позже. |

---

## 3. Целостная схема ролей экосистемы

### 3.1 SpiralEngine — роли и кто их выдаёт

| Роль в SpiralEngine | Кто выдаёт | Когда / условие | Используется в |
|---------------------|------------|----------------|----------------|
| **DEFAULT_ADMIN_ROLE** | При деплое (constructor) | — | Управление SpiralEngine, рутовые инвайты, suspendUser, setSoulIdentity, при необходимости выдача SELLER напрямую. |
| **ACTIVATOR_ROLE** | Активатор при activateUser (или по правилам контракта) | При активации пользователя по инвайту | Активация новых пользователей (activateUser), рост сети и создание активностей (ActivityRegistry) при наличии инвайта. |
| **SELLER_ROLE** | Только по одному из двух путей (см. п. 2.3) | (1) Напрямую от админа; (2) через ≥3 рекомендации от активаторов с наработками | ProductRegistry, OrganicComponentRegistry: создание продуктов и компонентов. |

**Инвайт обязателен** для всех ролей контента: без `usedInviteByUser(user) != 0` пользователь не считается «в экосистеме», и проверки в регистрах (hasRole + usedInviteByUser) не пройдут.

### 3.2 Регистры и проверки создателя

| Контракт | Проверка «кто может создавать» | Проверка «кто может менять своё» |
|----------|--------------------------------|-----------------------------------|
| **ProductRegistry** | SELLER_ROLE + usedInviteByUser != 0 (onlyActivatedSeller). | onlyOwnSellerProduct(productId). |
| **OrganicComponentRegistry** | SELLER_ROLE + активация (аналог onlyActivatedSeller). | onlyOwnCreatorComponent(componentId). |
| **ActivityRegistry** | ACTIVATOR_ROLE + usedInviteByUser != 0 (onlyActivatedActivityCreator / только активированный Activator). | onlyOwnActivity(activityId): creator == msg.sender. |

### 3.3 Локальные роли в регистрах (не в SpiralEngine)

Во всех регистрах (ProductRegistry, OrganicComponentRegistry, ActivityRegistry) — один и тот же набор **управленческих** ролей:

| Роль | Назначение |
|------|------------|
| **DEFAULT_ADMIN_ROLE** | Управление ролями (AccessControl). |
| **ADMIN_ROLE** | pause/unpause, setSpiralEngine, при необходимости setComponentRegistry, setProductRegistry и т.д. |
| **UPGRADER_ROLE** | _authorizeUpgrade (UUPS). |

---

## 4. ActivityRegistry: модель (только active)

### 4.1 Состояние Activity on-chain

- **id**, **creator**, **activity_type** (enum: Event / Service), **metadataCID**, **active** (bool).
- `active == false` → черновик (не в поиске).
- `active == true` → опубликовано (в поиске).
- Переход черновик ↔ публикация — только creator: activateActivity(id) / deactivateActivity(id) (или setActivityActive(id, bool)).

### 4.2 Функции и доступ

| Функция | Кто может | Проверка |
|---------|-----------|----------|
| createActivity(activity_type, metadataCID) | Активированный ACTIVITY_CREATOR | ACTIVITY_CREATOR_ROLE + usedInviteByUser != 0. |
| activateActivity(activityId) / deactivateActivity(activityId) | Creator этой активности | onlyOwnActivity. |
| getActivity, getActivitiesByCreator, getPublishedActivityIds | View | По контракту. |
| pause, unpause, setSpiralEngine | ADMIN_ROLE | onlyRole(ADMIN_ROLE). |
| upgradeToAndCall | UPGRADER_ROLE | _authorizeUpgrade. |

При необходимости экстренного снятия с публикации: ADMIN_ROLE может иметь право forceDeactivate(activityId).

### 4.3 События (как у Products и Components)

Инициатор в каждом событии — **indexed address** (creator или initiator):

- **ActivityCreated**(address indexed creator, uint256 indexed activityId, ActivityType activity_type, string metadataCID, bool active).
- **ActivityActivated**(uint256 indexed activityId, address indexed initiator) и **ActivityDeactivated**(uint256 indexed activityId, address indexed initiator)  
  — либо одно **ActivityActiveChanged**(uint256 indexed activityId, bool active, address indexed initiator).

---

## 5. Сводная картина: от инвайта до ролей

```
Стартовый админ (DEFAULT_ADMIN_ROLE)
└── Создаёт рутовые инвайты, активирует первых пользователей (activateUser).

При активации (activateUser) пользователь получает:
└── ACTIVATOR_ROLE       →  активировать пришедших по своим инвайтам, создавать активности (ActivityRegistry) и расти дальше (потенциально к SELLER), но не становится SELLER автоматически.

SELLER_ROLE — только два пути:
├── Путь 1: напрямую от админа (высший уровень допуска)
└── Путь 2: через ≥3 рекомендации от активаторов с наработками (продажи/отзывы); реализация позже

SpiralEngine
├── usedInviteByUser != 0  →  пользователь «в экосистеме»
├── ACTIVATOR_ROLE         →  активация новых, создание активностей (ActivityRegistry) при наличии инвайта
└── SELLER_ROLE            →  ProductRegistry, OrganicComponentRegistry (только по путям 1 или 2)

Регистры (ProductRegistry, OrganicComponentRegistry, ActivityRegistry)
└── Проверки создателя и владельца — по таблице в п. 3.2.

API / UI
└── Авторизованные приложения (secret key / app auth); валидация по кодексу и гайду в UI (GPT инструкции).
```

---

**Версия:** 1.1  
**Статус:** Архитектурный референс по ролям; документ будет дополняться.
