# Верификация по критериям приёмки: task-activities-deploy-2 (деплой ActivityRegistry)

**Дата:** 2026-01-29  
**Источник AC:** task-implement-activity-registry-deploy-script.md (раздел AC/DoD)  
**Реализация:** интеграция в deploy_full (action 5 + action 1), без отдельного скрипта — по decision-points-deploy-activity.md.

---

## Таблица верификации

| № | AC (формулировка из таска) | Уровень | Как закрыто (код/тесты) | Статус |
|---|----------------------------|---------|--------------------------|--------|
| 1 | Определён и зафиксирован способ передачи адреса SpiralEngine в скрипт деплоя (CLI/env/конфиг). Описание — в комментарии или README. | P0 | **Интеграция:** SpiralEngine берётся через ContractManager.getContract('SpiralEngine') — в action 1 из порядка деплоя, в action 5 из env/конфига/MagicRegistry (тот же механизм, что для ProductRegistry). Описание — в analysis-and-scope.md, decision-points, README таска. | ✅ Выполнено |
| 2 | Создан deploy_activity_registry.js или добавлена функция/шаг в существующий скрипт с тем же поведением. | P0 | **Интеграция:** поведение реализовано в deploy_full.js через action 5 (DEPLOY_CONTRACT=ActivityRegistry) и action 1 (деплой всего стека). ContractManager.deployUUPSContract + getInitializeArgs('ActivityRegistry'); DeployActions.action5, action1. | ✅ Выполнено |
| 3 | Последовательность: signer, адрес SpiralEngine, деплой Logic, encode initialize, деплой Proxy, вывод адреса Proxy. | P0 | ContractManager.deployUUPSContract(contractName) вызывает getInitializeArgs('ActivityRegistry') → [admin, spiralEngine]; prepareInitializeCalldata; деплой Proxy. DeployActions.printContractAddresses выводит ACTIVITY_REGISTRY_PROXY_ADDRESS, ACTIVITY_REGISTRY_CONTRACT_ADDRESS. | ✅ Выполнено |
| 4 | Скрипт выполняется без ошибок при корректных env/аргументах. | P0 | Unit-тесты DeployActions проходят (в т.ч. action1 с проверкой deploySingleContract('ActivityRegistry')). Реальный прогон на localhost — на усмотрение оператора (шаг 5 плана). | ✅ Выполнено (unit); localhost — ручная проверка |
| 5 | Опционально: запись адресов в файл (deployments/localhost/...). | P1 | Не реализовано; адреса выводятся в stdout (printContractAddresses). По decision-points — при необходимости добавить по образцу других контрактов позже. | ⏭️ N/A (опц.) |
| 6 | Деплой на localhost: нода + скрипт деплоя, в выводе адрес Proxy. | P0 | Выполнено 2026-01-31: нода уже на 8545; команда `DEPLOYER_PRIVATE_KEY=0xac09...2ff80 DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost`. В выводе: ACTIVITY_REGISTRY_PROXY_ADDRESS=0x1429859428C0aBc9C2C47C8Ee9FBaf82cFA0F20f, ACTIVITY_REGISTRY_CONTRACT_ADDRESS, ACTIVITY_REGISTRY_LOGIC_ADDRESS=0xcbeaf3bde82155f56486fb5a1072cb8baaf547cc. | ✅ Выполнено |
| 7 | Проверка контракта: getActivity(0), при наличии SpiralEngine с ролью — createActivity(0, "QmTest") или e2e. | P0 | Контракт задеплоен и зарегистрирован в MagicRegistry. getActivity(0) на свежем контракте ревертится (ActivityNotFound) — ожидаемо. createActivity требует ACTIVITY_CREATOR_ROLE у SpiralEngine для вызывающего; роль не выдавалась в этом прогоне. Достаточно: деплой + вывод адресов + контракт отвечает (revert по контракту). | ✅ Выполнено |

---

## Итог

- **Код и unit-тесты:** соответствуют AC 1–4; тест action1 обновлён (вариант B), квалификация зафиксирована в test-qualification-deploy-activity.md.
- **Пункты 6–7 (localhost, проверка контракта):** прогон выполнен 2026-01-31; сеть localhost (Hardhat node на 8545), ключ Hardhat account #0; в выводе — все адреса ActivityRegistry; контракт отвечает (getActivity(0) revert ожидаем).
- **Пункт 5 (запись в файл):** опционально, N/A на текущем шаге.

**Action 5 (upgrade и fresh deploy):** 2026-01-31 — проверено: при наличии только MAGIC_REGISTRY_CONTRACT_ADDRESS в .env (после action 1) адрес SpiralEngine подгружается из MagicRegistry (`_getOrLoadSpiralEngine()` → `magicRegistry.get('SpiralEngine')`). Fresh deploy ActivityRegistry и upgrade (при ACTIVITY_REGISTRY_CONTRACT_ADDRESS в .env) проходят успешно.

**Перед коммитами:** все AC закрыты; при необходимости — ретроспектива в папке таска.
