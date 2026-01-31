# Task: implement — Action 5: deploy/upgrade UUPS контракта с именем из инпута

**Идентификатор:** task-action5-uups-upgrade  
**Фокус:** scripts/ (DeployActions, ContractManager, deploy_full)  
**Контекст:** Сейчас Action 5 — «ни рыба ни мясо»: при существующем контракте возвращает его без апгрейда; имя контракта берётся из config, а не из явного инпута. Нужен полноценный action для деплоя/апгрейда UUPS контракта с именем из инпута.  
**Дата анализа:** 2026-01-30  
**Методология:** @docs/methodology/task-standard.md, @.cursor/commands/run-analysis.md (analysis.mdc)

---

## Метаданные

| Поле | Значение |
|------|----------|
| **Приоритет** | P1 |
| **Сложность** | M |
| **Оценка времени** | 1 день |
| **Зависимости** | Нет |
| **Тэги** | action-5, deploy, upgrade, UUPS, ContractManager |
| **Статус** | done |

**Границы задачи:** Только скрипты. Контракты UUPS (SpiralEngine, ProductRegistry, OrganicComponentRegistry, AmanitaInternational) уже реализованы; здесь — скриптовая логика deploy/upgrade.

---

## 1. Цель (Purpose)

Превратить Action 5 в **полноценный action** для деплоя или апгрейда UUPS контракта:

1. **Имя контракта — из инпута:** передаётся явно (env `DEPLOY_CONTRACT` или CLI-аргумент), а не только из `deployment.contractName` в config.
2. **Два режима:**  
   - **Контракт не существует** (нет адреса в env) → fresh deploy (Logic + Proxy) — как сейчас.  
   - **Контракт существует** (есть адрес Proxy в env) и это UUPS → **upgrade**: деплой новой Logic, вызов `proxy.upgradeToAndCall(newLogicAddress, "0x")`.
3. **Результат:** возможность отправлять новые версии UUPS контрактов на mainnet через upgrade без полного редеплоя Action 1.

**Почему это важно (риск):** Без upgrade flow нельзя обновить SpiralEngine (или другой UUPS контракт) на новую Logic с новыми функциями (например `mintInviteBatch`). Сейчас при наличии адреса Action 5 просто возвращает существующий контракт; апгрейда нет.

**Что НЕ входит в scope:** Апгрейд non-UUPS контрактов; верификация в блокэксплорерах; batch upgrade нескольких контрактов за раз.

---

## 2. Факты из кода (Code Facts / SSOT)

### 2.1 Action 5 — текущая реализация

- **Файл:** `scripts/lib/actions/DeployActions.js`
  - Строки 30–81: `async action5(contractName)`:
    - Если `!contractName`, берёт `this.config.get('deployment.contractName')`; иначе ошибка.
    - Вызывает `this.contractManager.deploySingleContract(contractName, { registry: magicRegistry })`.
    - Печатает адрес в формате `.env`.
  - **Факт:** Имя контракта берётся из config или аргумента; логика только в `deploySingleContract`.

### 2.2 deploySingleContract — при наличии контракта возвращает его без upgrade

- **Файл:** `scripts/lib/services/ContractManager.js`
  - Строки 685–690:
    ```javascript
    const existing = await this.checkExistingContract(contractName);
    if (existing) {
      logger.info(`Contract ${contractName} already exists at ${existingAddress}`);
      return existing;
    }
    ```
  - **Факт:** При существующем контракте возвращается загруженный инстанс; апгрейда нет.

### 2.3 checkExistingContract — проверка по config

- **Файл:** `scripts/lib/services/ContractManager.js`
  - Строки 638–642: `checkExistingContract(contractName)` вызывает `this.config.getContractAddress(contractName)`; при наличии адреса загружает контракт и возвращает его.
  - **Факт:** «Существует» = есть адрес в config (env: `SPIRAL_ENGINE_CONTRACT_ADDRESS` и т.п.).

### 2.4 deploy_full.js — только DEPLOY_ACTION из env

- **Файл:** `scripts/deploy_full.js`
  - Строки 321, 248: `const action = process.env.DEPLOY_ACTION`; `await this.actionsManager.executeAction(action)` — без передачи дополнительных параметров.
  - **Факт:** Для Action 5 не передаётся имя контракта; `executeAction(5)` вызывает `action5(undefined)`.

### 2.5 executeAction — action 5 без аргументов

- **Файл:** `scripts/lib/actions/index.js`
  - Строка 61: `5: (contractName) => this.deployActions.action5(contractName)`.
  - Строка 100: `return await action()` — вызывается без аргументов.
  - **Факт:** `action5(undefined)`; contractName берётся только из config (`deployment.contractName`).

### 2.6 deployUUPSContract — только fresh deploy

- **Файл:** `scripts/lib/services/ContractManager.js`
  - Строки 343–428: `deployUUPSContract` деплоит Logic, затем Proxy с `initialize`. Нет вызова `upgradeToAndCall`.
  - **Факт:** Поддерживается только первичный деплой, upgrade не реализован.

### 2.7 UUPS контракты и UPGRADER_ROLE

- **Файлы:** `contracts/SpiralEngineLogic.sol`, `ProductRegistryLogic.sol`, `OrganicComponentRegistryLogic.sol`, `AmanitaInternationalLogic.sol`
  - Каждый имеет `UPGRADER_ROLE`, `_authorizeUpgrade` только для UPGRADER_ROLE.
  - Апгрейд вызывается на Proxy: `proxy.upgradeToAndCall(newLogicAddress, "0x")`.
  - **Факт:** Deployer (admin) получает UPGRADER_ROLE при initialize; апгрейд возможен от того же signer.

### 2.8 config — нет deployment.contractName и DEPLOY_CONTRACT

- **Файл:** `scripts/lib/config/index.js`
  - В `config` нет `deployment.contractName`; `getContractAddress` маппит `SpiralEngine` → `contracts.spiralEngine` (из `SPIRAL_ENGINE_CONTRACT_ADDRESS`).
  - **Факт:** `deployment.contractName` сейчас не задаётся в config; action5 полагается на fallback, которого по сути нет.

---

## 3. Gap / Проблема (Gap Analysis)

1. **Имя контракта не передаётся из инпута.** deploy_full.js не поддерживает `DEPLOY_CONTRACT`; executeAction не передаёт параметры для action 5.
2. **Нет логики upgrade.** При существующем UUPS контракте `deploySingleContract` возвращает его и завершает работу; новой Logic не деплоится, `upgradeToAndCall` не вызывается.
3. **Action 5 бесполезен для апгрейда.** Для отправки новых версий UUPS контрактов на mainnet нужен отдельный скрипт или ручной вызов; через actions этого сделать нельзя.

---

## 4. AC/DoD (Acceptance Criteria / Definition of Done)

- [x] **(P0)** Имя контракта передаётся в Action 5 из **инпута** (env `DEPLOY_CONTRACT=SpiralEngine` или CLI-аргумент при вызове deploy_full), а не только из config. Fallback на `deployment.contractName` допустим для обратной совместимости.
- [x] **(P0)** При **отсутствии** контракта (нет адреса в config): выполняется fresh deploy (Logic + Proxy) — текущее поведение.
- [x] **(P0)** При **наличии** UUPS контракта (адрес Proxy в config): выполняется **upgrade**: деплой новой Logic, вызов `proxy.upgradeToAndCall(newLogicAddress, "0x")` от имени signer с UPGRADER_ROLE. Адрес Proxy не меняется; возвращается контракт по тому же адресу.
- [x] **(P0)** Контракт считается UUPS, если входит в список `['SpiralEngine', 'ProductRegistry', 'OrganicComponentRegistry', 'AmanitaInternational']` (или аналог в ContractManager).
- [x] **(P1)** deploy_full.js поддерживает `DEPLOY_CONTRACT=SpiralEngine` при `DEPLOY_ACTION=5`; при action 5 передаёт contractName в executeAction.
- [x] **(P1)** ExecuteAction для action 5 принимает contractName (из env или аргумента router) и передаёт в action5.
- [x] **(P1)** Unit-тесты DeployActions обновлены: мок ContractManager с `upgradeUUPSContract`; при существующем UUPS — вызов upgrade.
- [x] **(P2)** Документация: комментарий в deploy_full.js с примером команды.

---

## 5. Где менять код (Code Changes Location)

| Файл | Изменения |
|------|-----------|
| `scripts/deploy_full.js` | При `DEPLOY_ACTION=5`: читать `process.env.DEPLOY_CONTRACT` (или CLI arg); передавать contractName в `route(action, { contractName })` или в `executeAction(5, contractName)`. |
| `scripts/lib/actions/index.js` | `executeAction(actionNumber, options)` — для action 5 передавать `options.contractName` в action5. Альтернатива: `executeAction(5, contractName)` — перегрузка по сигнатуре. |
| `scripts/lib/actions/DeployActions.js` | `action5(contractName)`: приоритет — contractName из аргумента, fallback — `config.get('deployment.contractName')` или `process.env.DEPLOY_CONTRACT`. При существующем UUPS — вызывать `contractManager.upgradeUUPSContract(contractName)` вместо return existing. |
| `scripts/lib/services/ContractManager.js` | Добавить `upgradeUUPSContract(contractName)`: загрузить Proxy по адресу из config; задеплоить новую Logic; вызвать `proxy.upgradeToAndCall(newLogicAddress, "0x")`; дождаться receipt; вернуть контракт (Logic ABI) по адресу Proxy. |
| `scripts/tests/unit/actions/DeployActions.test.js` | Обновить тесты action5: передача contractName; мок `upgradeUUPSContract` при существующем UUPS. |

---

## 6. План выполнения (Execution Plan)

1. **Инпут для Action 5**  
   В deploy_full.js при action 5 читать `DEPLOY_CONTRACT` из env (или второй CLI-аргумент). Передавать в router → executeAction. В index.js — `executeAction(5, { contractName })` или `executeAction(5, contractName)`.

2. **ContractManager.upgradeUUPSContract**  
   Реализовать метод: получить proxyAddress из `config.getContractAddress(contractName)`; загрузить Proxy (ABI Proxy или Logic — вызовы идут через Proxy); задеплоить `SpiralEngineLogic` (или `${contractName}Logic`) без Proxy; закодировать `upgradeToAndCall(newLogic, "0x")`; отправить tx от signer; дождаться receipt; вернуть contract instance (Logic ABI, attach к proxyAddress).

3. **DeploySingleContract или отдельный путь**  
   Либо добавить `options.forceUpgrade` в deploySingleContract и при existing + UUPS + forceUpgrade вызывать upgrade; либо в action5 явно: если existing и UUPS — вызывать upgradeUUPSContract, иначе deploySingleContract. Выбрать и зафиксировать в решении.

4. **Action 5 — полная логика**  
   В action5: приоритет contractName из аргумента/options; проверка, что contractName задан; если existing — вызов upgrade (для UUPS); если не existing — deploySingleContract. Вывод адреса (Proxy) в формате .env.

5. **Тесты**  
   Unit-тесты: action5 с contractName; мок checkExistingContract (return contract) + upgradeUUPSContract; проверка, что upgrade вызван, а не deploy. Тест на fresh deploy (checkExistingContract return null).

6. **Документация**  
   Комментарий в deploy_full.js или README: пример `DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine npx hardhat run scripts/deploy_full.js --network polygon`.

---

## 7. Команды проверки (Verification Commands)

```bash
# Fresh deploy (контракт не существует) — как раньше
DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine npx hardhat run scripts/deploy_full.js --network localhost

# Upgrade (контракт существует, SPIRAL_ENGINE_CONTRACT_ADDRESS в .env)
DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine npx hardhat run scripts/deploy_full.js --network polygon

# Unit-тесты
npx hardhat test scripts/tests/unit/actions/DeployActions.test.js --grep "action5\|upgrade"
```

---

## 8. Решение / архитектура (Solution Architecture)

- **Инпут:** `DEPLOY_CONTRACT` в env при `DEPLOY_ACTION=5`. При необходимости — второй позиционный аргумент в CLI (`node deploy_full.js 5 SpiralEngine`) как альтернатива.
- **Роутинг:** deploy_full.js передаёт contractName в router; router передаёт в `executeAction(5, { contractName })`; ActionsManager для action 5 вызывает `action5(options.contractName)`.
- **Логика action5:**  
  1) contractName = arg ?? `process.env.DEPLOY_CONTRACT` ?? config.get('deployment.contractName');  
  2) existing = checkExistingContract(contractName);  
  3) if (existing && isUUPS(contractName)) → upgradeUUPSContract(contractName);  
  4) else → deploySingleContract(contractName).
- **upgradeUUPSContract:** Deploy Logic only; get proxyAddress from config; proxy.upgradeToAndCall(newLogic, "0x"); return Logic.attach(proxyAddress).
- **Обратная совместимость:** Если contractName не передан и контракт не существует — ошибка (как сейчас). Если передан — работа в режиме deploy или upgrade.

---

## 9. Риски и подводные камни (Risks & Pitfalls)

- **Storage layout:** При апгрейте UUPS нельзя менять порядок и типы state variables; новая Logic должна быть совместима. Это ответственность разработчика контракта.
- **UPGRADER_ROLE:** Signer (deployer) должен иметь UPGRADER_ROLE на Proxy. При action1 deployer получает его; при ручном деплое — проверить.
- **Initialize при upgrade:** `upgradeToAndCall(newLogic, "0x")` с пустым calldata — initialize не вызывается (уже вызван при первом деплое). Для re-initialize нужна отдельная логика (не в scope).
