# Архитектура тестирования (Unit → Integration → E2E)

Документ описывает, как выстроена многоуровневая проверка JavaScript-слоя (`scripts/tests`) и какие инструменты используются на каждом уровне. Цель — понять, где размещать новые сценарии и как запускать существующие без необходимости перечитывать весь исходный код.

## Слои и их роли
- `unit` — изолированная проверка модулей (`lib/actions`, `core`, `services`, `utils`). Все внешние зависимости замоканы через `sinon`.
- `integration` — проверка стыков 2–4 модулей с минимальным мокированием. Используется `IntegrationHarness`, поднимающий реальные экземпляры менеджеров и конфигов.
- `e2e` — полный сценарий с запуском Hardhat-нод, развёртыванием прокси и взаимодействием с реальными контрактами через `E2EHarness` и `MagicRegistryHelper`.
- Общая инфраструктура: Mocha + Chai, единый конфиг `.mocharc.json`, фикстуры в `scripts/tests/fixtures`, хелперы в `scripts/tests/helpers`.

## Структура каталогов и команды
- `scripts/tests/unit/**/*.test.js` → `npm run test:unit`
- `scripts/tests/integration/**/*.test.js` → `npm run test:integration`
- `scripts/tests/e2e/**/*.test.js` → `npm run test:e2e`
- `npm run test` запускает все уровни подряд; `npm run test:coverage` использует `nyc` для отчёта.
- Глобальный конфиг Mocha подключает `scripts/tests/setup.js` и увеличивает таймауты.
```1:8:scripts/tests/.mocharc.json
{
  "require": ["scripts/tests/setup.js"],
  "timeout": 30000,
  "recursive": true
}
```

## Unit layer
- Покрытие: действия (`lib/actions`), сервисы (`lib/services`), утилиты (`lib/utils`).
- Подход: stub/stub-моки на `ContractManager`, `EthersUtils`, `Config` и т.д.; проверяем только бизнес-ветки текущего модуля.
- Инструменты: Chai + Sinon; никакого доступа к Hardhat или файлам.
- Фикстуры: создаются в тестах/через `sinon.stub`. 
```14:117:scripts/tests/unit/actions/AccessControlActions.test.js
beforeEach(function () {
  mockContractManager = { loadContract: sinon.stub() };
  mockEthersUtils = { getSigner: sinon.stub(), isValidAddress: sinon.stub().returns(true) };
  accessControlActions = new AccessControlActions(
    mockContractManager,
    mockEthersUtils,
    mockConfig
  );
});
```
- Когда добавлять тест: если меняется отдельный метод, появляется новая ветка ошибок, добавляется конфигурационная опция.

## Integration layer
- Назначение: подтвердить, что модули корректно разговаривают друг с другом (CoreLogic ↔ ContractManager ↔ ArweaveManager и т.д.).
- `IntegrationHarness` поднимает реальные экземпляры менеджеров и конфигов, но заменяет внешние API моками (Arweave, RPC).
- Основные директории: `integration/contracts.integration.test.js`, `integration/flows.integration.test.js`, `integration/proof.integration.test.js`.
- `setupIntegrationEnvironment()` отдаёт объект `modules` с живыми сервисами и вспомогательными метриками; `setupProductRegistrySuite()` разворачивает набор контрактов (SpiralEngine mock + UUPS-прокси Product/Organic Registries).
```217:311:scripts/tests/helpers/IntegrationHarness.js
const ProductProxy = await ethers.getContractFactory('ProductRegistryProxy');
const productProxy = await ProductProxy.deploy(productLogicAddress, initCalldata);
...
this.magicRegistry.register('ProductRegistry', productProxyAddress, productLogicAddress);
return this.productSuite;
```
- Рекомендации: используйте интеграционный слой, если нужно проверить связку нескольких модулей без подъёма Hardhat-ноды (например, формат данных на границах, флоу `CoreLogic.activateSellerBasic`).

## E2E layer
- Назначение: повторить реальные CLI-сценарии (`deploy_full` actions, пайплайны 41/42/43/444, Action 888).
- `E2EHarness` управляет жизненным циклом Hardhat-ноды, создаёт снапшоты через `evm_snapshot`, регистрирует все прокси в локальном `MagicRegistryHelper` и умеет валидировать CID/CSV.
```44:105:scripts/tests/helpers/E2EHarness.js
if (output.includes('Started HTTP and WebSocket JSON-RPC server')) {
  this.networkReady = true;
  setTimeout(() => resolve(), 1000);
}
...
setTimeout(() => {
  if (!this.networkReady) {
    this.stopHardhatNode();
    reject(new Error('Hardhat node start timeout (30s)'));
  }
}, 30000);
```
- Структура `e2e/actions` отражает `deploy_full` с номерами action (0,1,2,555,777,888 и т.п.); `e2e/workflows` описывает последовательные пайплайны; дополнительные файлы (`performance`, `idempotency`, `proof`) проверяют нефункциональные требования.
- Для Action 888 используется `deployCompleteEcosystemFor888()` → развёртывает полный набор прокси и регистрирует пары proxy/logic. Документ `harness-and-e2e.md` подробно объясняет работу helper’ов и ожидаемые кастомные ошибки.
- При работе с e2e обязательно указывайте `DEPLOY_ACTION` и используйте снапшоты (`harness.saveState/restoreState`) для ускорения тестов.
- **Подготовка продавца:** `harness.prepareSellerForE2E({ sellerSigner, deployerSigner, invitesPrefix, useExistingInvite })` — единый способ активировать seller, выдать SELLER/ACTIVATOR роли и сгенерировать 12 инвайтов. Helper автоматически:
  - генерирует root invite префикса `<invitesPrefix>-ROOT-*` (минтит через `SpiralEngine.mintInvite`, если такого кода нет);
  - вызывает `activateUser` от имени deployer/activator;
  - выдаёт SELLER_ROLE + ACTIVATOR_ROLE, проверяет состояние через `assertSellerState`;
  - возвращает `sellerInvites`, `tokenId`, финальный state.
  Используйте этот helper во всех e2e тестах, где требуется продавец (Actions 43/444/555/777/888), вместо ручных вызовов `activateUser`/`grantRole`.

## Общие хелперы и фикстуры
- `scripts/tests/helpers/index.js` экспортирует все harness’ы, assertion helpers и mock-утилиты; единый импорт предотвращает дублирование.
- Assertions: `AssertionHelpers.js` унифицирует проверку `BusinessId`, `CID`, `expectRevertCustom`, `assertRegisteredProxy`.
- Фикстуры: CSV/JSON/Arweave в `scripts/tests/fixtures`; `fixtures/env/test.env` и `fixtures/env/e2e.test.env` подменяют `.env` при запуске интеграционных и e2e тестов.
- Глобальные флаги: `SUPPRESS_LOGS=true npm run test:e2e` отключит `console.log` (см. `setup.js`).

## Как выбирать слой
- **Unit** — меняете чисто JS-логику в одном модуле: добавили ветку `AccessControlActions`, расширили `EthersUtils` → тест в `unit`.
- **Integration** — нужно подтвердить контракт между модулями (формат данных, совместимость сервисов, новая фасадная операция). Пример: `flows.integration.test.js` проверяет цепочку `CoreManager → CoreLogic → ContractManager`.
- **E2E** — end-to-end сценарии, регрессии после изменений в смарт-контрактах, проверка новых CLI action. Любой кейс, где задействуется Hardhat node, magic registry, реальные прокси.
- Если сценарий затрагивает несколько слоёв, начинайте с unit (для веток ошибок), затем integration (чтобы убедиться в совместимости модулей) и завершающий тест на e2e (гарантия, что CLI/консольный сценарий работает полностью).

## CI и запуск в пакетном режиме
- `npm run test` — полный прогон всех уровней.
- `npm run test:watch` — watcher на Mocha для быстрого редактирования unit/integration тестов (e2e лучше запускать точечно).
- `npm run test:coverage` — отчёт по покрытию `nyc`; учитывает unit + integration (e2e обычно исключаются из покрытия).
- В CI рекомендуется запускать `test:unit` и `test:integration` на каждом пулл-реквесте, `test:e2e` — ночные прогоны или перед релизом.

## Быстрые команды для scripts/tests

| Уровень | Команда | Примечания |
| --- | --- | --- |
| Unit | `npm run test:unit` или `./node_modules/.bin/mocha scripts/tests/unit/**/*.test.js --config scripts/tests/.mocharc.json` | Без окружения; все зависимости мокируются. |
| Integration | `npm run test:integration` или `./node_modules/.bin/mocha scripts/tests/integration/**/*.test.js --config scripts/tests/.mocharc.json` | Используется `IntegrationHarness`, Hardhat не нужен. |
| E2E (по одному файлу) | `DEPLOYER_PRIVATE_KEY=<64hex> SELLER_PRIVATE_KEY=<64hex> SELLER_ADDRESS=<0x...> ./node_modules/.bin/mocha scripts/tests/e2e/actions/<action>.e2e.test.js --config scripts/tests/.mocharc.json` | Нужны валидные приватные ключи (64 hex, без `…`), Hardhat-нода стартует автоматически; при повторном запуске можно переиспользовать уже подключённую ноду. |
| E2E (все) | `npm run test:e2e` | Долго: разворачивает несколько action-файлов подряд. Использовать только при полной регрессии. |

### Как подставлять переменные для e2e

```
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d \
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
./node_modules/.bin/mocha scripts/tests/e2e/actions/component/action555.e2e.test.js \
  --config scripts/tests/.mocharc.json
```

- Ключи должны быть ровно 64 hex-символа (Hardhat выдаст HH8, если поставить `…` или укороченный ключ).
- Команда запускается в корне репозитория (`/Users/eslinko/Development/Amanita`), иначе `node_modules/.bin` и `scripts/tests` не найдутся.
- Если в терминале уже крутится Hardhat-нода, `E2EHarness` подключится к ней автоматически; при первом запуске harness стартует ноду сам.

## Дополнительные материалы
- `scripts/docs/harness-and-e2e.md` — подробный гайд по работе с `IntegrationHarness`/`E2EHarness` и `MagicRegistryHelper`.
- `scripts/docs/AIJournal.md` — актуальные заметки о состоянии e2e/regression и списке блокеров.
- `scripts/docs/validation-process.txt` — команды для ручной валидации Action 555/444 между запусками тестов.


