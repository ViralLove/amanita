# Task: implement — ActivityRegistry контракт с TDD тестами

## Цель
Реализовать смарт-контракт `ActivityRegistry` для управления активностями (events/services) в экосистеме Amanita с полным покрытием тестами через Test-Driven Development подход, используя существующую инфраструктуру тестирования контрактов.

## Почему это важно (риск)
**Блокирует Фазу 1 Epic Activities API**: без контракта ActivityRegistry невозможно реализовать вертикальную архитектуру данных для Activity (блокчейн → Arweave → Supabase). Контракт является источником истины (Source of Truth) для всех Activity в системе.

## Факты из кода

### 1) Архитектура ActivityRegistry определена в вертикальном анализе
- `docs/tech/activity-vertical-layers-analysis.md:256-328`
  - Структура `Activity` с `enum ActivityType` (Event/Service) и `enum ActivityStatus` (Draft/SentToReview/Approved/Published)
  - Газовые оптимизации: использование `enum` вместо `string` для типов и статусов
  - Рекомендуемая структура: `id`, `creator`, `activity_type`, `metadataCID`, `active`, `status`
  - События: `ActivityCreated`, `ActivityStatusUpdated`

### 2) Epic определяет требования к контракту
- `docs/analysis/epics/epic-activities-api-production.md:580-608`
  - Фаза 1: Blockchain Foundation включает разработку контракта ActivityRegistry
  - Требования: деплой на Hardhat localhost, верификация контракта
  - Интеграция с существующей инфраструктурой (аналог ProductRegistry)

### 3) Существующая инфраструктура тестирования контрактов
- `contracts/docs/testing-infrastructure.md:1-288`
  - Технологический стек: Hardhat + Ethers.js + Chai + Mocha
  - Структура тестов: `contracts/tests/` с паттернами UUPS comprehensive tests
  - Примеры: `ProductRegistry.UUPS.comprehensive.test.js`, `OrganicComponentRegistry.UUPS.test.js`
  - Паттерны: beforeEach setup, state preservation, access control, events validation

### 4) Паттерны UUPS контрактов в проекте
- `contracts/ProductRegistryLogic.sol:1-91`
  - Использование UUPS upgradeable паттерна (ERC1967)
  - Инициализация через `initialize()` функцию
  - Роли через `AccessControlUpgradeable`
  - Пауза через `PausableUpgradeable`
  - Reentrancy protection через `ReentrancyGuardUpgradeable`

### 5) Структура тестов следует TDD методологии
- `contracts/tests/ProductRegistry.UUPS.comprehensive.test.js:68-171`
  - Setup: деплой моков (MockSpiralEngine), деплой Logic и Proxy
  - Тестирование: Full State Preservation (P0), Access Control, Events
  - Паттерны: `expectEvent()`, `expectRevertCustom()`, детальное логирование

### 6) Activity Data Model определяет бизнес-логику
- `GPT UI/instructions/activity-data-model.md` (из контекста Epic)
  - Различение Event vs Service через discriminator
  - Lifecycle статусы: Draft → SentToReview → Approved → Published
  - Условные поля в зависимости от типа Activity

## Gap / Проблема

**Отсутствует контракт ActivityRegistry**:
1. Нет реализации `ActivityRegistry.sol` в `contracts/`
2. Нет тестов для ActivityRegistry в `contracts/tests/`
3. Нет интерфейса `IActivityRegistry.sol` в `contracts/interfaces/`
4. Нет UUPS структуры (Logic + Proxy) для ActivityRegistry
5. Нет интеграции с существующей экосистемой (SpiralEngine, роли)

**Последствия**:
- Блокирует реализацию Python сервисов (ActivityRegistryService)
- Невозможно протестировать вертикальную архитектуру данных
- Epic Activities API не может быть реализован

## AC/DoD

### Контракт (P0 - Критично)
- [ ] Контракт `ActivityRegistryLogic.sol` создан в `contracts/`
- [ ] Контракт `ActivityRegistryProxy.sol` создан в `contracts/`
- [ ] Интерфейс `IActivityRegistry.sol` создан в `contracts/interfaces/`
- [ ] Контракт компилируется без ошибок (`npx hardhat compile`)
- [ ] Структура `Activity` соответствует спецификации из `activity-vertical-layers-analysis.md`
- [ ] Используются `enum ActivityType` и `enum ActivityStatus` (газовые оптимизации)
- [ ] Реализованы функции: `createActivity()`, `getActivity()`, `updateActivityStatus()`, `getActivitiesByCreator()`, `getPublishedActivities()`
- [ ] Реализованы события: `ActivityCreated`, `ActivityStatusUpdated`
- [ ] UUPS upgradeable паттерн (наследование от `UUPSUpgradeable`)
- [ ] Access Control через `AccessControlUpgradeable` (роли: ADMIN_ROLE, CREATOR_ROLE)
- [ ] Pausable через `PausableUpgradeable` (пауза всех операций)
- [ ] Reentrancy protection через `ReentrancyGuardUpgradeable`

### Тесты (P0 - Критично, TDD подход)
- [ ] Файл `contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js` создан
- [ ] Тесты написаны **ДО** реализации контракта (TDD: Red → Green → Refactor)
- [ ] Тесты используют существующую инфраструктуру (Hardhat + Ethers.js + Chai)
- [ ] Setup: деплой MockSpiralEngine, деплой Logic и Proxy, инициализация
- [ ] **P0 тесты (критичные пути)**:
  - [ ] Deployment и инициализация контракта
  - [ ] Создание Activity (Event и Service типы)
  - [ ] Получение Activity через `getActivity()`
  - [ ] Обновление статуса Activity (Draft → SentToReview → Approved → Published)
  - [ ] Получение списка Activity по creator
  - [ ] Получение списка опубликованных Activity
  - [ ] События `ActivityCreated` и `ActivityStatusUpdated` эмитятся корректно
  - [ ] Access Control: только creator может обновлять свою Activity
  - [ ] Access Control: только ADMIN может паузить контракт
  - [ ] Валидация: нельзя создать Activity с пустым CID
  - [ ] Валидация: нельзя обновить статус несуществующей Activity
  - [ ] Full State Preservation при UUPS upgrade (аналог ProductRegistry тестов)
- [ ] **P1 тесты (важные пути)**:
  - [ ] Batch операции (создание нескольких Activity)
  - [ ] Edge cases: максимальное количество Activity, граничные значения
  - [ ] Gas оптимизации: проверка затрат газа на операции
- [ ] Все тесты проходят (`npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`)

### Интеграция (P1)
- [ ] Контракт интегрирован с MockSpiralEngine (проверка активации пользователя)
- [ ] Контракт следует паттернам ProductRegistry (консистентность архитектуры)
- [ ] Документация контракта в `contracts/docs/ActivityRegistry.md` (опционально, но желательно)

### Деплой (P1)
- [ ] Скрипт деплоя создан (аналог `scripts/deploy_full.js` для ActivityRegistry)
- [ ] Деплой на Hardhat localhost работает
- [ ] Контракт верифицирован (если требуется)

## Где менять код

### 1. Контракт ActivityRegistry (новые файлы)
- `contracts/ActivityRegistryLogic.sol` - **НОВЫЙ ФАЙЛ**
  - UUPS upgradeable логика контракта
  - Структура `Activity`, mappings, функции
  - События, модификаторы, валидация

- `contracts/ActivityRegistryProxy.sol` - **НОВЫЙ ФАЙЛ**
  - Proxy контракт для UUPS паттерна (аналог `ProductRegistryProxy.sol`)

- `contracts/interfaces/IActivityRegistry.sol` - **НОВЫЙ ФАЙЛ**
  - Интерфейс контракта (аналог `IProductRegistry.sol`)

### 2. Тесты (новый файл)
- `contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js` - **НОВЫЙ ФАЙЛ**
  - Comprehensive test suite (аналог `ProductRegistry.UUPS.comprehensive.test.js`)
  - TDD подход: сначала тесты (RED), потом реализация (GREEN)

### 3. Моки (если требуется)
- `contracts/mocks/MockSpiralEngine.sol` - **УЖЕ СУЩЕСТВУЕТ**
  - Используется для тестирования (не требует изменений)

### 4. Деплой скрипты (новый файл или расширение существующего)
- `scripts/deploy_activity_registry.js` - **НОВЫЙ ФАЙЛ** (опционально)
  - Или расширение `scripts/deploy_full.js` для поддержки ActivityRegistry

## План выполнения

### Шаг 1: TDD - Написание тестов (RED фаза)
**Цель**: Определить требования к контракту через тесты

1. **Создать структуру тестового файла**
   - Создать `contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`
   - Скопировать структуру из `ProductRegistry.UUPS.comprehensive.test.js`
   - Адаптировать под ActivityRegistry (Activity вместо Product)

2. **Написать тесты для базовой функциональности (P0)**
   - Тест: Deployment и инициализация
   - Тест: `createActivity()` для Event типа
   - Тест: `createActivity()` для Service типа
   - Тест: `getActivity()` возвращает корректные данные
   - Тест: `updateActivityStatus()` меняет статус
   - Тест: События эмитятся корректно
   - Тест: Access Control работает

3. **Запустить тесты (ожидаем RED - все тесты падают)**
   ```bash
   npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
   # Ожидаем: все тесты падают (контракт не существует)
   ```

### Шаг 2: Реализация контракта (GREEN фаза)
**Цель**: Реализовать минимальную версию контракта, чтобы тесты прошли

1. **Создать интерфейс**
   - Создать `contracts/interfaces/IActivityRegistry.sol`
   - Определить структуру `Activity`, события, функции

2. **Создать Logic контракт**
   - Создать `contracts/ActivityRegistryLogic.sol`
   - Наследование: `UUPSUpgradeable`, `AccessControlUpgradeable`, `PausableUpgradeable`, `ReentrancyGuardUpgradeable`
   - Реализовать `initialize()` функцию
   - Реализовать структуру `Activity` с `enum ActivityType` и `enum ActivityStatus`
   - Реализовать mappings: `activities`, `activitiesByCreator`, `publishedActivityIds`
   - Реализовать функции: `createActivity()`, `getActivity()`, `updateActivityStatus()`, `getActivitiesByCreator()`, `getPublishedActivities()`
   - Реализовать события: `ActivityCreated`, `ActivityStatusUpdated`
   - Добавить модификаторы: `onlyCreator()`, `whenNotPaused()`, `nonReentrant()`
   - Добавить валидацию: проверка CID, проверка существования Activity

3. **Создать Proxy контракт**
   - Создать `contracts/ActivityRegistryProxy.sol`
   - Аналог `ProductRegistryProxy.sol`

4. **Компиляция и проверка**
   ```bash
   npx hardhat compile
   # Ожидаем: компиляция успешна
   ```

5. **Запустить тесты (ожидаем GREEN - базовые тесты проходят)**
   ```bash
   npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
   # Ожидаем: базовые P0 тесты проходят
   ```

### Шаг 3: Расширение функциональности (P1 тесты + реализация)
**Цель**: Добавить расширенную функциональность

1. **Добавить P1 тесты**
   - Тест: Batch операции
   - Тест: Edge cases
   - Тест: Gas оптимизации
   - Тест: Full State Preservation при upgrade

2. **Реализовать расширенную функциональность**
   - Оптимизация газа (использование `calldata`, упаковка storage)
   - Batch операции (если требуется)
   - Дополнительная валидация

3. **Запустить все тесты**
   ```bash
   npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
   # Ожидаем: все тесты проходят
   ```

### Шаг 4: Рефакторинг (REFACTOR фаза)
**Цель**: Улучшить код без изменения поведения

1. **Рефакторинг контракта**
   - Выделение общих паттернов с ProductRegistry
   - Оптимизация газа
   - Улучшение читаемости кода

2. **Рефакторинг тестов**
   - Выделение общих утилит (аналог `expectEvent()`, `expectRevertCustom()`)
   - Улучшение структуры тестов

3. **Проверка после рефакторинга**
   ```bash
   npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
   # Ожидаем: все тесты все еще проходят
   ```

### Шаг 5: Интеграция и документация
**Цель**: Интегрировать контракт в экосистему

1. **Интеграция с существующими контрактами**
   - Проверка работы с MockSpiralEngine
   - Проверка консистентности с ProductRegistry паттернами

2. **Документация** (опционально)
   - Создать `contracts/docs/ActivityRegistry.md`
   - Описать структуру, функции, события

3. **Деплой скрипт** (опционально)
   - Создать `scripts/deploy_activity_registry.js`
   - Или расширить `scripts/deploy_full.js`

## Команды проверки

### До реализации (демонстрация gap):
```bash
# Проверка отсутствия контракта
ls contracts/ActivityRegistry*.sol
# Ожидаем: файлы не найдены

# Проверка отсутствия тестов
ls contracts/tests/ActivityRegistry*.test.js
# Ожидаем: файлы не найдены

# Попытка запустить тесты (должна упасть)
npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
# Ожидаем: ошибка "Cannot find module" или "File not found"
```

### После реализации (ожидаемый результат):
```bash
# Компиляция контракта
npx hardhat compile
# Ожидаем: ✅ Compilation successful

# Запуск всех тестов ActivityRegistry
npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
# Ожидаем: ✅ Все тесты проходят (15-20+ тестов)

# Запуск с детальным выводом
npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js --verbose
# Ожидаем: Детальный вывод всех тестов

# Проверка покрытия (если настроено)
npx hardhat coverage
# Ожидаем: ActivityRegistry покрыт тестами >80%
```

### Проверка интеграции:
```bash
# Деплой на локальную ноду
npx hardhat node
# В новом терминале:
node scripts/deploy_activity_registry.js
# Ожидаем: ✅ ActivityRegistry deployed at 0x...

# Проверка через Hardhat console
npx hardhat console --network localhost
# В консоли:
# const ActivityRegistry = await ethers.getContractFactory("ActivityRegistryLogic");
# const registry = ActivityRegistry.attach("0x...");
# await registry.getActivity(1);
# Ожидаем: корректные данные Activity
```

### Проверка газовых оптимизаций:
```bash
# Запуск тестов с измерением газа
REPORT_GAS=true npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js
# Ожидаем: отчет о затратах газа на каждую операцию
# Проверка: createActivity() < 150,000 gas (благодаря enum оптимизациям)
```

---

## Метаданные задачи
**Приоритет:** P0 (Критично - блокирует Epic Activities API)  
**Сложность:** M (Средняя - требует понимания UUPS паттерна и TDD)  
**Оценка времени:** 3-4 дня (TDD: тесты 1 день, реализация 1.5 дня, рефакторинг 0.5 дня, интеграция 1 день)  
**Зависимости:** Требует понимания ProductRegistry паттернов, UUPS архитектуры, TDD методологии  
**Тэги:** contracts, activity-registry, tdd, uups, smart-contracts, epic-activities-api  
**Статус:** ready

---

## Решение (Архитектура)

### Архитектура контракта (на основе ProductRegistry)
```
ActivityRegistryLogic (UUPS Upgradeable)
├── Initializable
├── UUPSUpgradeable (upgrade через _authorizeUpgrade)
├── AccessControlUpgradeable (роли: ADMIN_ROLE, CREATOR_ROLE)
├── PausableUpgradeable (пауза всех операций)
├── ReentrancyGuardUpgradeable (защита от reentrancy)
└── IActivityRegistry (интерфейс)

ActivityRegistryProxy (ERC1967Proxy)
└── Хранит state variables через delegatecall
```

### Структура данных
```solidity
enum ActivityType {
    Event,      // 0
    Service     // 1
}

enum ActivityStatus {
    Draft,          // 0
    SentToReview,   // 1
    Approved,       // 2
    Published       // 3
}

struct Activity {
    uint256 id;
    address creator;
    ActivityType activity_type;  // enum (экономия газа)
    string metadataCID;          // Arweave/IPFS CID
    bool active;
    ActivityStatus status;        // enum (экономия газа)
}
```

### Основные функции
1. `createActivity(ActivityType, string calldata metadataCID) → uint256`
   - Создает новую Activity со статусом Draft
   - Эмитит событие `ActivityCreated`
   - Возвращает `activityId`

2. `getActivity(uint256 activityId) → Activity memory`
   - Возвращает полную структуру Activity

3. `updateActivityStatus(uint256 activityId, ActivityStatus newStatus)`
   - Обновляет статус Activity (только creator или ADMIN)
   - Валидация переходов статусов (state machine)
   - Эмитит событие `ActivityStatusUpdated`

4. `getActivitiesByCreator(address creator) → uint256[]`
   - Возвращает список ID Activity созданных указанным creator

5. `getPublishedActivities() → uint256[]`
   - Возвращает список ID всех опубликованных Activity

### Обоснование getPublishedActivities()

**Зачем нужна в цепочке тасков и архитектуре:**

- **ActivityRegistryService.list_activities()** (Фаза 6): сценарий «список всех опубликованных» — бэкенд вызывает контракт, получает `uint256[]` ID, затем по каждому ID собирает полный Activity (Assembler) или берёт из кэша. Без этой функции пришлось бы либо сканировать события (индексер/subgraph), либо хранить список оффчейн — контракт остаётся единственным источником истины для «кто опубликован».
- **Кэш и индекс поиска**: синхронизация кэша (ActivityCacheService) и индекса Supabase (Фаза 5) — бэкенд периодически вызывает `getPublishedActivities()`, сравнивает с уже проиндексированными ID и дотягивает недостающие. Аналог использования `getAllActiveProductIds()` в скриптах (например, `AccessControlActions.js`) для подсчёта активных продуктов и проверки каталога.
- **Discovery / публичный список**: API «показать все публичные активности» без фильтра по creator — источник списка ID именно эта функция.

**Да, по смыслу это «вытащить все опубликованные ID» для кэширования, индексации и выдачи списка.**

**Эффективность и газ:**

- **Вызов `view`**: вызывающий (bot/RPC) газ не платит; нода только читает storage. Для бэкенда вызов дёшев.
- **Поддержка списка в контракте**: при переходе в Published — `push(id)` в массив, при unpublish — удаление из массива (как в ProductRegistry: swap с последним + `pop`), чтобы не сдвигать весь массив. Один лишний SSTORE при publish и при unpublish — приемлемо.
- **Масштаб**: возврат `uint256[]` целиком при десятках тысяч записей даёт большой ответ и возможные лимиты RPC/таймауты. Для MVP и умеренного масштаба (сотни — низкие тысячи) подход адекватен и совпадает с паттерном ProductRegistry (`getAllActiveProductIds()`). При росте до очень больших объёмов можно рассмотреть индексер по событиям или subgraph, но это уже следующий этап; для текущего Epic функция обоснована.

**Итог:** функция нужна для list/discovery, кэша и синхронизации индекса; по газу и эффективности для вызывающего и контракта — адекватна, согласована с ProductRegistry.

### Газовые оптимизации
- ✅ `enum` вместо `string` для типов и статусов (~40,000 gas экономии)
- ✅ `calldata` для параметров (~300-500 gas на функцию)
- ✅ `indexed` в событиях для фильтрации (экономия off-chain)
- ✅ Упаковка storage (enum + bool в один slot)

---

## Риски/Подводные камни

### Риск 1: Неправильная структура storage при upgrade
**Симптом:** State variables теряются при UUPS upgrade  
**Решение:** Следовать паттерну ProductRegistry, тестировать Full State Preservation

### Риск 2: Неправильная валидация переходов статусов
**Симптом:** Можно перейти из Draft сразу в Published, минуя Review  
**Решение:** Реализовать state machine валидацию в `updateActivityStatus()`

### Риск 3: Gas costs выше ожидаемых
**Симптом:** `createActivity()` стоит >200,000 gas  
**Решение:** Использовать `enum`, `calldata`, упаковку storage, измерить газ в тестах

### Риск 4: Несовместимость с существующими контрактами
**Симптом:** ActivityRegistry не работает с MockSpiralEngine  
**Решение:** Использовать тот же паттерн интеграции, что и ProductRegistry

---

## Оценка сложности

*По методологии: `docs/methodology/task-complexity-assessment.md`*

### Критерии оценки (шкала 1-10)

| Критерий | Оценка | Обоснование |
|----------|--------|-------------|
| **Объём изменений кода** | 6/10 | 4 новых файла (Logic, Proxy, Interface, тесты), ~800 строк: Solidity ~400, тесты ~400. Деплой-скрипт опционально |
| **Архитектурная сложность** | 5/10 | Новый контрактный слой, UUPS, интерфейсы, state machine статусов. Повторяет паттерны ProductRegistry |
| **Риск регрессии** | 4/10 | Изолированный код (новый контракт). Критичен для Epic, но не трогает существующие контракты |
| **Необходимость тестирования** | 7/10 | TDD: comprehensive test suite (P0+P1), Full State Preservation, access control, события. Интеграция с MockSpiralEngine |
| **Понимание контекста** | 5/10 | Нужно знать ProductRegistry, UUPS, вертикальный анализ (activity-vertical-layers-analysis.md), Hardhat-инфраструктуру |
| **Зависимости** | 4/10 | Внутренние: паттерны ProductRegistry, Hardhat. Внешних блокирующих нет |
| **Неопределённость** | 2/10 | Требования и структура заданы в vertical analysis и Epic; решение известно |

### Итоговая оценка

**Средняя сложность:** (6+5+4+7+5+4+2) / 7 = **4.7 / 10**  
**Категория:** **M** (Medium)  
**Оценка времени:** 3-4 дня (TDD: тесты 1 день, реализация 1.5 дня, рефакторинг 0.5 дня, интеграция 1 день)

### Рекомендации

- Выполнять в порядке TDD: Red → Green → Refactor
- Сверить структуру `Activity` с `docs/tech/activity-vertical-layers-analysis.md`
- Проверить Full State Preservation при upgrade (аналог ProductRegistry)
- Замерить газ по ключевым операциям (createActivity, updateStatus)

---

## High-ROI доп. задачи

### Задача 1: Batch операции для создания Activity (+15% эффективности)
Добавить функцию `createActivitiesBatch()` для создания нескольких Activity за одну транзакцию.

### Задача 2: Фильтрация Activity по типу и статусу (+20% функциональности)
Добавить функции `getActivitiesByType()`, `getActivitiesByStatus()` для эффективной фильтрации.

### Задача 3: Версионирование метаданных (+10% гибкости)
Добавить поддержку версионирования CID (история изменений метаданных Activity).

### Задача 4: Интеграция с SpiralEngine для проверки ролей (+5% безопасности)
Использовать SpiralEngine для проверки прав creator (аналог ProductRegistry).

---

## Связи с другими задачами

### Блокирует:
- Epic Activities API - Фаза 1 (Blockchain Foundation) не может быть завершена без контракта
- Python ActivityRegistryService - не может быть реализован без контракта

### Зависит от:
- Понимания ProductRegistry паттернов (для консистентности)
- Существующей инфраструктуры тестирования (Hardhat + Ethers.js)

### Связано с:
- `docs/tech/activity-vertical-layers-analysis.md` - определяет структуру контракта
- `docs/analysis/epics/epic-activities-api-production.md` - определяет требования к контракту
