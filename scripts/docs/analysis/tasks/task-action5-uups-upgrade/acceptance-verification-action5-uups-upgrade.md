# Верификация по критериям приёмки: Action 5 UUPS upgrade

**Таск:** task-action5-uups-upgrade  
**Дата:** 2026-01-31

---

## Сводка

| AC | Уровень | Формулировка | Код/тесты | Статус |
|----|---------|--------------|-----------|--------|
| 1 | P0 | Имя контракта из инпута (DEPLOY_CONTRACT env) | deploy_full.js читает DEPLOY_CONTRACT; action5 принимает contractName из arg/env/config | ✅ |
| 2 | P0 | При отсутствии контракта — fresh deploy | action5: if (!existing) → deploySingleContract | ✅ |
| 3 | P0 | При наличии UUPS — upgrade via upgradeToAndCall | action5: if (existing && isUUPS) → upgradeUUPSContract; ContractManager.upgradeUUPSContract | ✅ |
| 4 | P0 | UUPS список: SpiralEngine, ProductRegistry, OrganicComponentRegistry, AmanitaInternational | uupsContracts в action5 и upgradeUUPSContract | ✅ |
| 5 | P1 | deploy_full.js: DEPLOY_CONTRACT при DEPLOY_ACTION=5 | deploy_full.js: contractName, options, route(action, options) | ✅ |
| 6 | P1 | executeAction для action 5 принимает options.contractName | index.js: executeAction(actionNumber, options), action5(options.contractName) | ✅ |
| 7 | P1 | Unit-тесты: upgrade при existing, deploy при отсутствии | DeployActions.test.js: 4 теста action5 | ✅ |
| 8 | P2 | Документация: пример команды | deploy_full.js: комментарий в блоке action 5 | ✅ |

---

## Прогон тестов

```bash
npx hardhat test tests/unit/actions/DeployActions.test.js --grep "action5"
# 4 passing
```

---

## Итог

Критерии P0, P1, P2 выполнены. Action 5 поддерживает deploy и upgrade UUPS контрактов с именем из DEPLOY_CONTRACT.
