# План реализации: Action 5 UUPS upgrade

**Таск:** task-action5-uups-upgrade  
**Дата:** 2026-01-30

---

## Phase 1: ContractManager.upgradeUUPSContract + Action 5 + deploy_full/executeAction

### 1.1 ContractManager.upgradeUUPSContract
**Файл:** `scripts/lib/services/ContractManager.js`

- Добавить метод `upgradeUUPSContract(contractName, deployOptions = {})`:
  1. proxyAddress = this.config.getContractAddress(contractName) || process.env[`${contractName.toUpperCase()}_CONTRACT_ADDRESS`]; if (!proxyAddress) throw.
  2. Задеплоить новую Logic: `deployContract(\`${contractName}Logic\`, getLogicConstructorArgs(\`${contractName}Logic\`), deployOptions)`.
  3. newLogicAddress = await implementationContract.getAddress().
  4. Загрузить Logic artifact; создать proxy contract (Logic ABI) на proxyAddress с signer.
  5. Вызвать proxy.upgradeToAndCall(newLogicAddress, "0x") с gasPrice для Polygon (700 gwei).
  6. await tx.wait() (или waitForTransactionReceipt).
  7. Вернуть Logic.attach(proxyAddress) — контракт по тому же адресу.
- UUPS-список: ['SpiralEngine', 'ProductRegistry', 'OrganicComponentRegistry', 'AmanitaInternational'].

### 1.2 DeployActions.action5
**Файл:** `scripts/lib/actions/DeployActions.js`

- contractName = arg ?? process.env.DEPLOY_CONTRACT ?? config.get('deployment.contractName'); if (!contractName) throw.
- existing = await contractManager.checkExistingContract(contractName).
- isUUPS = uupsContracts.includes(contractName).
- if (existing && isUUPS) → contract = await contractManager.upgradeUUPSContract(contractName); иначе → contract = await contractManager.deploySingleContract(contractName, { registry: magicRegistry }).
- Вывод адреса (Proxy) в формате .env; return.

### 1.3 deploy_full.js — передача contractName
**Файл:** `scripts/deploy_full.js`

- При action 5: contractName = process.env.DEPLOY_CONTRACT.
- Передавать в route: `route(action, { contractName })` или `route(action, contractName)`.

### 1.4 Router и executeAction
**Файл:** `scripts/deploy_full.js` (route), `scripts/lib/actions/index.js` (executeAction)

- route(action, options): при action 5 передать options.contractName в executeAction.
- executeAction(actionNumber, options): при action 5 вызвать action5(options?.contractName).

---

## Phase 2: Unit-тесты DeployActions

**Файл:** `scripts/tests/unit/actions/DeployActions.test.js`

- Мок ContractManager: upgradeUUPSContract (stub).
- Тест: action5 с contractName при existing UUPS — вызывается upgradeUUPSContract, не deploySingleContract.
- Тест: action5 при не existing — вызывается deploySingleContract.
- Тест: contractName из process.env.DEPLOY_CONTRACT.

---

## Phase 3: Верификация и документация

- acceptance-verification-action5-uups-upgrade.md
- Комментарий в deploy_full.js: пример DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine.
- **node-launch.txt** — секция Action 5 (deploy/upgrade UUPS с DEPLOY_CONTRACT).
- **Deploy_Full.md** — раздел Action 5 и Upgrade Process (DEPLOY_CONTRACT, upgrade vs deploy).
