# Выполнено: шаги 1–3 (ContractManager + DeployActions)

**Дата:** 2026-01-29  
**План:** analysis-and-scope.md, раздел 7

---

## Сделано

### Шаг 1 — ContractManager.js
- В **upgradeUUPSContract**: в список `uupsContracts` добавлен `'ActivityRegistry'`.
- В **getInitializeArgs**: добавлена ветка для `'ActivityRegistry'` — `[adminAddress, await spiralEngine.getAddress()]` (SpiralEngine должен быть задеплоен/загружен).
- В **getLogicConstructorArgs**: добавлен `'ActivityRegistryLogic': []`.
- В **deploySingleContract** (auto-detect): в массив `uupsContracts` добавлен `'ActivityRegistry'`.

### Шаг 2 — DeployActions.js, action 5
- В массив `uupsContracts` в action5 добавлен `'ActivityRegistry'`.
- Итог: `DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry` деплоит или апгрейдит ActivityRegistry; адрес выводится в stdout и при наличии MagicRegistry регистрируется там.

### Шаг 3 — DeployActions.js, action 1
- После деплоя ProductRegistry добавлен деплой ActivityRegistry (с `waitForNonce()`):  
  `contracts.activityRegistry = await this.contractManager.deploySingleContract('ActivityRegistry', { isUUPS: true, registry: contracts.magicRegistry });`
- В **printContractAddresses** добавлен блок для `contracts.activityRegistry`: вывод `ACTIVITY_REGISTRY_PROXY_ADDRESS`, `ACTIVITY_REGISTRY_CONTRACT_ADDRESS`, `ACTIVITY_REGISTRY_LOGIC_ADDRESS`.

---

## Проверка

- `npx hardhat compile` — успешно (контракты ActivityRegistry уже собраны).
- Линтер по изменённым файлам — без ошибок.

---

## Шаг 4 — constants.js (выполнено 2026-01-29)

- В **CONTRACT_ENV_MAPPING** добавлено: `'ActivityRegistry': 'ACTIVITY_REGISTRY_CONTRACT_ADDRESS'`.
- В **SUPPORTED_CONTRACTS** добавлено: `'ActivityRegistry'` (после ProductRegistry).
- Линтер — без ошибок.

---

## Дальше (по плану)

- Шаг 5: запуск на localhost (DEPLOY_ACTION=1 или DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry).
- Шаг 6: проверка контракта (getActivity(0), createActivity при наличии роли) и документация.
