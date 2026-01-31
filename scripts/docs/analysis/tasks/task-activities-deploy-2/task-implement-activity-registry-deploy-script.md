# Task: implement — деплой ActivityRegistry (скрипт и проверка на localhost)

## Цель

Реализовать воспроизводимый деплой контракта ActivityRegistry (Logic + Proxy) из проекта scripts: отдельный скрипт деплоя и проверка на Hardhat localhost, чтобы закрыть критерии приёмки по деплою из контрактного таска и дать возможность поднимать локальный стек с ActivityRegistry для интеграционных проверок и бэкенда.

**Почему это важно (риск):**
- Без скрипта деплоя нельзя воспроизводимо развернуть ActivityRegistry на localhost для тестов бэкенда и E2E.
- В `scripts/deploy_full.js` и в `ContractManager` явного шага деплоя ActivityRegistry нет; адрес SpiralEngine, деплой Logic и Proxy для ActivityRegistry не автоматизированы.
- Критерии приёмки таска контракта (task-implement-activity-registry-contract-tdd.md, P1): «Скрипт деплоя создан», «Деплой на Hardhat localhost работает» — закрываются этим таском.

**Границы задачи:**
- Реализация в репозитории `scripts/` (Node.js, Hardhat, ethers).
- Сеть: в первую очередь Hardhat localhost; источник адреса SpiralEngine — env/CLI/конфиг (см. план).
- Не входит: деплой на mainnet/testnet (отдельная настройка), верификация контракта в блокэксплорерах.

---

## Факты из кода

### 1) Контракт ActivityRegistry уже реализован (Logic + Proxy)
- `contracts/ActivityRegistryLogic.sol:96-107`
  - `initialize(address admin, address _spiralEngine)` — единственный инициализатор; требует ненулевые admin и SpiralEngine.
- `contracts/ActivityRegistryProxy.sol` — прокси для UUPS (аналог ProductRegistryProxy).
- `contracts/interfaces/IActivityRegistry.sol` — интерфейс (Activity, createActivity, getActivity, activateActivity, deactivateActivity, getActivitiesByCreator, getPublishedActivityIds).

### 2) В scripts нет деплоя ActivityRegistry
- `scripts/lib/config/constants.js:9-26`
  - `CONTRACT_ENV_MAPPING` и `SUPPORTED_CONTRACTS` не содержат `ActivityRegistry`.
- `scripts/lib/services/ContractManager.js:529-563`
  - `getInitializeArgs(contractName)` реализован для SpiralEngine, ProductRegistry, OrganicComponentRegistry, AmanitaInternational; ветки для `ActivityRegistry` нет.
- В `scripts/deploy_full.js` и в действиях (DeployActions) явного шага деплоя ActivityRegistry нет.

### 3) Паттерн UUPS-деплоя в ContractManager
- `scripts/lib/services/ContractManager.js:337-487`
  - `deployUUPSContract(contractName, constructorArgs, deployOptions)`: деплой Logic, затем Proxy с `encodeFunctionData('initialize', initArgs)`; возвращает контракт, привязанный к адресу Proxy.
- `scripts/lib/services/ContractManager.js:491-503`
  - `prepareInitializeCalldata(contractName, initArgs)` — кодирование `initialize` для Proxy.
- Для использования в отдельном скрипте нужны: signer (deployer), адрес SpiralEngine, вызов деплоя Logic и Proxy с теми же шагами.

### 4) ProductRegistry — эталон инициализации
- `scripts/lib/services/ContractManager.js:539-546`
  - ProductRegistry: `getInitializeArgs` возвращает `[adminAddress, await spiralEngine.getAddress()]`; SpiralEngine должен быть уже задеплоен/загружен.
- ActivityRegistryLogic.initialize(admin, _spiralEngine) совпадает по сигнатуре с ProductRegistry — те же два аргумента.

### 5) Референс плана реализации (solution-architecture)
- `contracts/docs/analysis/tasks/task-Activities-1/solution-architecture-task1-activity-registry.md:489-508`
  - План Фазы 7: источник адреса SpiralEngine (CLI/env/конфиг); скрипт деплоя Logic → encode initialize(admin, spiralEngine) → деплой Proxy; опционально запись адресов в файл; проверка на localhost (getActivity(0), createActivity).

---

## Gap / Проблема

1. **Нет отдельного скрипта деплоя ActivityRegistry**  
   Файла `scripts/deploy_activity_registry.js` (или эквивалентного шага в существующем скрипте) нет.

2. **Нет автоматизации в deploy_full/ContractManager**  
   В `scripts/deploy_full.js` и в `ContractManager` (SUPPORTED_CONTRACTS, getInitializeArgs, CONTRACT_ENV_MAPPING) явного шага/поддержки ActivityRegistry нет — адрес SpiralEngine, деплой Logic и Proxy, вывод адреса Proxy не автоматизированы для ActivityRegistry.

3. **Нет воспроизводимой проверки на localhost**  
   Нет задокументированной процедуры «поднять ноду → вызвать скрипт → получить адрес Proxy → проверить getActivity(0) / createActivity».

---

## AC/DoD

### Источник адреса SpiralEngine (P0)
- [ ] Определён и зафиксирован способ передачи адреса SpiralEngine в скрипт деплоя: (a) аргумент CLI, (b) env (например `SPIRAL_ENGINE_ADDRESS`), или (c) конфиг/файл после предыдущего деплоя (если ActivityRegistry деплоится в составе полного стека). Описание — в комментарии скрипта или в README деплоя.

### Скрипт деплоя (P0)
- [ ] Создан `scripts/deploy_activity_registry.js` (или добавлена функция/шаг в существующий скрипт с тем же поведением).
- [ ] Последовательность: загрузка ethers/Hardhat, получение signer (deployer), получение адреса SpiralEngine (по выбранному способу), деплой `ActivityRegistryLogic`, получение адреса Logic, кодирование `initialize(admin, spiralEngine)` через интерфейс Logic, деплой `ActivityRegistryProxy` с аргументами `(logicAddress, initCalldata)`.
- [ ] В stdout выводится адрес Proxy (и при необходимости Logic).
- [ ] Скрипт выполняется без ошибок при корректных env/аргументах.

### Опционально: запись адресов (P1)
- [ ] Опционально: запись адресов Proxy (и Logic) в конфиг или файл (например `deployments/localhost/activity_registry.json` или аналог по образцу существующих скриптов). Повторные вызовы других скриптов могут читать адрес ActivityRegistry из одного места.

### Деплой на localhost (P0)
- [ ] В одном терминале запускается `npx hardhat node`, в другом выполняется скрипт деплоя с сетью localhost (или default). Деплой завершается успешно, в выводе есть адрес Proxy.

### Проверка контракта после деплоя (P0)
- [ ] Через `npx hardhat console --network localhost` или одноразовый скрипт: к Proxy подключается ABI Logic, вызывается `getActivity(0)` — ожидаем revert (ActivityNotFound) или корректную ошибку. По сценарию: вызов `createActivity(0, "QmTest")` от имени аккаунта с ACTIVITY_CREATOR_ROLE в SpiralEngine (если SpiralEngine уже задеплоен и настроен) при успехе даёт activityId. Альтернатива: минимальный e2e-скрипт, который деплоит MockSpiralEngine, настраивает роль, деплоит ActivityRegistry, создаёт активность, вызывает getActivity(1).

---

## Где менять код

| Роль | Файл / действие |
|------|------------------|
| Новый скрипт | `scripts/deploy_activity_registry.js` — создать. |
| Опционально | `scripts/lib/services/ContractManager.js` — добавить `ActivityRegistry` в список UUPS-контрактов, `getInitializeArgs('ActivityRegistry')` → `[adminAddress, spiralEngineAddress]`, при необходимости `CONTRACT_ENV_MAPPING` / загрузка SpiralEngine из env. |
| Опционально | `scripts/lib/config/constants.js` — добавить `ActivityRegistry` в `SUPPORTED_CONTRACTS` и `CONTRACT_ENV_MAPPING` при интеграции в полный стек. |
| Документация | Комментарии в скрипте или `scripts/docs/` — способ передачи SpiralEngine, пример запуска на localhost. |

---

## План выполнения

| Шаг | Действие | Критерий приёмки |
|-----|----------|------------------|
| 1 | Определить источник адреса SpiralEngine: (a) аргумент CLI, (b) env `SPIRAL_ENGINE_ADDRESS`, (c) конфиг/файл. Зафиксировать в комментарии скрипта или README. | Однозначный способ передачи адреса SpiralEngine. |
| 2 | Создать `scripts/deploy_activity_registry.js`: подключение ethers/Hardhat, получение signer, получение адреса SpiralEngine, деплой ActivityRegistryLogic, `logic.getAddress()`, `encodeFunctionData("initialize", [adminAddress, spiralEngineAddress])`, деплой ActivityRegistryProxy с `(logicAddress, initCalldata)`, вывод в консоль адреса Proxy (и при необходимости Logic). | Скрипт выполняется без ошибок; в stdout адрес Proxy. |
| 3 | Опционально: запись адресов Proxy/Logic в файл (например `deployments/localhost/activity_registry.json`) по образцу существующих скриптов. | Другие скрипты могут читать адрес ActivityRegistry из одного места. |
| 4 | Запустить `npx hardhat node` в одном терминале; в другом выполнить скрипт деплоя с сетью localhost. Убедиться, что в выводе есть адрес Proxy. | Деплой на localhost завершается успешно. |
| 5 | Проверка: через `npx hardhat console --network localhost` или скрипт — attach Logic ABI к адресу Proxy, вызвать `getActivity(0)` (ожидаем revert/ошибку); при наличии SpiralEngine с ролью — `createActivity(0, "QmTest")` или минимальный e2e (MockSpiralEngine + ActivityRegistry + createActivity + getActivity(1)). | Вызов getActivity(0) и createActivity через Proxy корректен по сценарию. |

---

## Команды проверки

### До реализации
```bash
# Скрипта нет
ls scripts/deploy_activity_registry.js
# Ожидаем: No such file or directory (или аналог)
```

### После реализации
```bash
# Запуск ноды
npx hardhat node

# В другом терминале: деплой на localhost (адрес SpiralEngine из env или CLI)
SPIRAL_ENGINE_ADDRESS=0x... node scripts/deploy_activity_registry.js
# или: node scripts/deploy_activity_registry.js 0x...
# Ожидаем: в stdout адрес Proxy (и при необходимости Logic)

# Проверка контракта (подставить PROXY_ADDRESS)
npx hardhat console --network localhost
# В консоли: const Logic = await ethers.getContractFactory("ActivityRegistryLogic"); const r = Logic.attach("PROXY_ADDRESS"); await r.getActivity(0);
# Ожидаем: revert ActivityNotFound или корректная ошибка
```

---

## Зависимости и связи

- **Зависит от:** контракт ActivityRegistry (Logic + Proxy + интерфейс) реализован и собирается (`npx hardhat compile`). Таск контракта: `contracts/docs/analysis/tasks/task-Activities-1/task-implement-activity-registry-contract-tdd.md`.
- **Блокирует:** локальная проверка бэкенда и E2E с реальным ActivityRegistry; критерии приёмки деплоя контрактного таска (P1).
- **Epic:** Activities API Production — таск выполняется после завершения контрактной части (Фаза 1), в roadmap Epic добавлен после Фазы 1 как «Деплой ActivityRegistry (scripts)».

---

## Метаданные задачи

---
**Приоритет:** P1 (закрытие критериев деплоя контрактного таска; локальный стек для бэкенда)  
**Сложность:** S–M  
**Оценка времени:** 0.5–1 день  
**Зависимости:** ActivityRegistry контракт реализован (contracts/); Hardhat, ethers в scripts.  
**Тэги:** scripts, deploy, activity-registry, hardhat, localhost  
**Статус:** ready  
**Epic:** EPIC-001 (Activities API Production)  
**Фаза:** После Фазы 1 (Blockchain Foundation) — деплой и проверка на localhost  

---

## Ссылки

- План реализации (Фаза 7): `contracts/docs/analysis/tasks/task-Activities-1/solution-architecture-task1-activity-registry.md:489-511`
- Таск контракта: `contracts/docs/analysis/tasks/task-Activities-1/task-implement-activity-registry-contract-tdd.md`
- Паттерн UUPS в scripts: `scripts/lib/services/ContractManager.js` (deployUUPSContract, getInitializeArgs для ProductRegistry)
- Epic: `docs/analysis/epics/epic-activities-api-production.md`
