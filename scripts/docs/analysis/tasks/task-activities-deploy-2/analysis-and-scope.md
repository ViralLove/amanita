# Анализ и рамки: task-activities-deploy-2 (деплой ActivityRegistry)

**Дата:** 2026-01-29  
**Этап процесса:** 1 (Анализ и рамки)  
**Источник:** task-implement-activity-registry-deploy-script.md

---

## 1. Цель таска

Воспроизводимый деплой контракта ActivityRegistry (Logic + Proxy) из scripts: отдельный скрипт деплоя и проверка на Hardhat localhost. Закрытие критериев приёмки деплоя из контрактного таска; возможность поднимать локальный стек с ActivityRegistry для интеграций и бэкенда.

---

## 2. Gap (подтверждено по коду)

| Gap | Проверка |
|-----|----------|
| Нет `scripts/deploy_activity_registry.js` | В scripts/ есть только `deploy_full.js`, `deploy_full.old.js` — отдельного скрипта деплоя ActivityRegistry нет. |
| Нет поддержки ActivityRegistry в ContractManager | `ContractManager.js`: `uupsContracts` = SpiralEngine, ProductRegistry, OrganicComponentRegistry, AmanitaInternational; ветки `getInitializeArgs('ActivityRegistry')` нет. |
| Нет ActivityRegistry в constants.js | `SUPPORTED_CONTRACTS` и `CONTRACT_ENV_MAPPING` не содержат ActivityRegistry. |
| Нет воспроизводимой процедуры проверки на localhost | В таске описана целевая процедура (нода → скрипт → проверка getActivity/createActivity); сейчас не задокументирована и не проверена. |

---

## 3. Эталон (паттерн деплоя)

- **ContractManager.deployUUPSContract(contractName, constructorArgs, deployOptions)** — деплой Logic, затем Proxy с `encodeFunctionData('initialize', initArgs)`; возврат контракта по адресу Proxy.
- **ContractManager.getInitializeArgs('ProductRegistry')** — `[adminAddress, await spiralEngine.getAddress()]`; SpiralEngine должен быть загружен.
- **ActivityRegistryLogic.initialize(admin, _spiralEngine)** — та же сигнатура, что у ProductRegistry: два аргумента.

---

## 4. План выполнения (из таска)

| Шаг | Действие | Критерий |
|-----|----------|----------|
| 1 | Определить источник адреса SpiralEngine (CLI / env / конфиг); зафиксировать в комментарии или README. | Однозначный способ передачи. |
| 2 | Создать `scripts/deploy_activity_registry.js`: signer, адрес SpiralEngine, деплой Logic → encode initialize → деплой Proxy, вывод адреса Proxy. | Скрипт выполняется, в stdout адрес Proxy. |
| 3 | Опционально: запись адресов в файл (напр. deployments/localhost/activity_registry.json). | Другие скрипты могут читать адрес. |
| 4 | Запуск ноды + скрипт деплоя на localhost. | Деплой на localhost успешен. |
| 5 | Проверка: getActivity(0), при наличии SpiralEngine с ролью — createActivity(0, "QmTest") или минимальный e2e. | Вызовы через Proxy корректны. |

---

## 5. Зависимости

- Контракт ActivityRegistry (Logic + Proxy + IActivityRegistry) реализован и собирается (`npx hardhat compile`) — выполнено в task-Activities-1.

---

## 6. Решение по реализации: интеграция в deploy_full (action 5 + action 1)

**Подход оператора:** не создавать отдельный `deploy_activity_registry.js`, а **добавить ActivityRegistry в существующий механизм** deploy_full.js: UUPS-деплой и регистрация через MagicRegistry уже реализованы в action 5 (универсальный деплой/апгрейд UUPS) и в action 1 (старт проекта — деплой всех контрактов). Достаточно добавить новый сегмент про Activity в эти действия.

### 6.1 Где что менять

| Место | Что сделать |
|-------|-------------|
| **ContractManager.js** | 1) В список UUPS-контрактов (в `deployUUPSContract` / `upgradeUUPSContract`, ~стр. 498) добавить `'ActivityRegistry'`. 2) В `getInitializeArgs(contractName)` добавить ветку для `'ActivityRegistry'`: `[adminAddress, await spiralEngine.getAddress()]` (как у ProductRegistry — SpiralEngine должен быть задеплоен/загружен). 3) В `getLogicConstructorArgs` добавить `'ActivityRegistryLogic': []`. |
| **DeployActions.js — action 5** | В массив `uupsContracts` (стр. 33) добавить `'ActivityRegistry'`. Тогда `DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry` будет деплоить или апгрейдить ActivityRegistry; адрес попадёт в MagicRegistry при деплое. |
| **DeployActions.js — action 1** | После деплоя ProductRegistry (или в блоке UUPS после SpiralEngine) добавить деплой ActivityRegistry: `contracts.activityRegistry = await this.contractManager.deploySingleContract('ActivityRegistry', { isUUPS: true, registry: contracts.magicRegistry });` + `waitForNonce()`. В `printContractAddresses(contracts)` добавить вывод адресов ActivityRegistry (Proxy + Logic), по образцу ProductRegistry. |
| **constants.js** (опционально) | Для полного стека: добавить `'ActivityRegistry'` в `SUPPORTED_CONTRACTS` и в `CONTRACT_ENV_MAPPING` (напр. `'ActivityRegistry': 'ACTIVITY_REGISTRY_CONTRACT_ADDRESS'`). |

### 6.2 Источник адреса SpiralEngine

В action 1 и action 5 контракты уже получают зависимости через **ContractManager**: `getInitializeArgs('ActivityRegistry')` вызывает `this.getContract('SpiralEngine')` — т.е. SpiralEngine берётся из уже задеплоенных/загруженных контрактов (в action 1 — из `contracts.spiralEngine`, в action 5 — из загрузки по env/конфигу). Отдельный скрипт с CLI/env для одного контракта не нужен: **источник SpiralEngine — тот же, что и для ProductRegistry** (деплой в порядке action 1 или загрузка из MagicRegistry/env при action 5).

### 6.3 Проверка на localhost

- **Action 1:** `DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost` — поднимет весь стек, включая ActivityRegistry; адреса в stdout.
- **Только ActivityRegistry (если остальные уже есть):** `DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry npx hardhat run scripts/deploy_full.js --network localhost`.
- Проверка контракта: как в таске — `npx hardhat console --network localhost`, attach Logic ABI к адресу Proxy, `getActivity(0)` (ожидаем revert/ошибку), при наличии SpiralEngine с ролью — `createActivity(0, "QmTest")`. Опционально: минимальный e2e или шаги в README/документации.

### 6.4 Действия 444 и 555

- **Action 444** (Catalog pipeline 41→42→43) и **Action 555** (Component upload) используют уже задеплоенные контракты (ProductRegistry, OrganicComponentRegistry и т.д.). Добавление ActivityRegistry в action 1 и action 5 **не меняет** 444/555; при необходимости обращения к ActivityRegistry из других действий его адрес можно получать через ContractManager/MagicRegistry по тому же механизму, что и остальные UUPS.

---

## 7. План выполнения (обновлённый под интеграцию)

| Шаг | Действие | Критерий |
|-----|----------|----------|
| 1 | **ContractManager.js:** добавить `'ActivityRegistry'` в список UUPS; `getInitializeArgs('ActivityRegistry')` → `[adminAddress, await spiralEngine.getAddress()]`; `getLogicConstructorArgs('ActivityRegistryLogic')` → `[]`. | ActivityRegistry деплоится через deployUUPSContract. |
| 2 | **DeployActions.js — action 5:** добавить `'ActivityRegistry'` в `uupsContracts`. | `DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry` работает. |
| 3 | **DeployActions.js — action 1:** добавить деплой ActivityRegistry (после ProductRegistry, с waitForNonce); добавить вывод адресов в `printContractAddresses`. | Action 1 деплоит ActivityRegistry и выводит адреса. |
| 4 | **constants.js** (опционально): добавить ActivityRegistry в SUPPORTED_CONTRACTS и CONTRACT_ENV_MAPPING. | Полный стек знает про ActivityRegistry. |
| 5 | Запуск на localhost: `DEPLOY_ACTION=1` или `DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry`; проверка вывода адресов. | Деплой на localhost успешен. |
| 6 | Проверка контракта: console или скрипт — getActivity(0), при наличии SpiralEngine с ролью — createActivity(0, "QmTest"). Документировать в README/документации деплоя. | Вызовы через Proxy корректны; процедура воспроизводима. |

---

**Итог этапа 1 (обновлённый):** Gap подтверждён; принято решение **интегрировать ActivityRegistry в deploy_full** (action 5 + action 1 + ContractManager), без отдельного скрипта. План выполнения скорректирован под эту реализацию.
