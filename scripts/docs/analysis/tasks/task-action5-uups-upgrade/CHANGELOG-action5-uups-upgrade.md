# CHANGELOG: task-action5-uups-upgrade

**Таск:** Action 5 deploy/upgrade UUPS с именем из инпута  
**Дата:** 2026-01-31

---

## Реализовано

- **ContractManager.js**
  - Добавлен метод `upgradeUUPSContract(contractName, deployOptions)`: деплой новой Logic, вызов `proxy.upgradeToAndCall(newLogic, "0x")`, возврат контракта по адресу Proxy.

- **DeployActions.js**
  - `action5(contractName)`: contractName из arg ?? process.env.DEPLOY_CONTRACT ?? config.get; при existing + UUPS → upgradeUUPSContract; иначе deploySingleContract; return { upgraded }.

- **deploy_full.js**
  - При action 5: проверка DEPLOY_CONTRACT; options = { contractName }; route(action, options); main(action, options).
  - Ошибка при action 5 без DEPLOY_CONTRACT с примером команды.

- **index.js**
  - `executeAction(actionNumber, options = {})`; для action 5: `action5(options.contractName)`.

- **DeployActions.test.js**
  - Моки: upgradeUUPSContract, checkExistingContract, loadContract.
  - Тесты: upgrade при existing UUPS; deploy при отсутствии; ошибка без contractName; DEPLOY_CONTRACT из env.
