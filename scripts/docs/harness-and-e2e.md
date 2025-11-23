# Harness & MagicRegistry Guide

## Overview

Этот документ описывает тестовую инфраструктуру уровня `scripts/tests` после перехода на `businessId` и UUPS-архитектуру:

- `IntegrationHarness` — минимальный стенд для интеграционных сценариев без реального узла.
- `E2EHarness` — полнофункциональный стенд с реальным Hardhat node.
- `MagicRegistryHelper` — единый источник адресов прокси/логики для тестов, независимо от `.env`.
- Набор assertion-хелперов для проверки `businessId`, CID и регистра в MagicRegistry.

## IntegrationHarness

### Ключевые возможности
- Загружает реальные модули (`ContractManager`, `CoreLogic`, `ActionsManager`) и мокает только внешние зависимости (Arweave, RPC).
- Метод `setupProductRegistrySuite({ componentsPerSeller, componentIds, forceRedeploy })` разворачивает полный комплект контрактов: `SpiralEngine` (mock), `OrganicComponentRegistry`, `ProductRegistry`.
- Возвращаемый suite включает:
  ```js
  {
    admin, seller, otherSeller,
    spiralEngine, spiralEngineAddress,
    componentRegistry, componentRegistryAddress, componentRegistryLogicAddress,
    productRegistry, productRegistryAddress, productRegistryLogicAddress,
    sellerComponentIds,
    SELLER_ROLE
  }
  ```
- Helper `getMagicRegistryHelper()` предоставляет доступ к зарегистрированным адресам прокси и логики.
- Дополнительные методы:
  - `clearSellerCatalog({ seller, sellerAddress })`
  - `grantSellerRole(target)`, `revokeSellerRole(target)`
  - `setSellerActivation(target, isActive)`

### Пример использования в тесте
```js
const harness = new IntegrationHarness();
const suite = await harness.setupProductRegistrySuite();

// Проверяем регистрацию продукта
await suite.productRegistry.connect(suite.seller).createProduct(
  'integration-prod-1',
  [suite.sellerComponentIds[0]],
  'QmIntegrationCID'
);
```

## E2EHarness

### Назначение
- Управляет жизненным циклом Hardhat node (старт/остановка, snapshot/reset).
- Разворачивает реальные контракты и автоматически записывает их в локальный MagicRegistry (через `registerMany`).
- Предоставляет методы `registerProxy()` и `loadContractFromSuite(contractName)` для работы с адресами без `.env`.

### Автоматическая регистрация адресов
- `deployProductSuite({ forceRedeploy })` регистрирует `SpiralEngine`, `OrganicComponentRegistry`, `ProductRegistry` (proxy + logic) в локальном `MagicRegistryHelper`.
- `deployCompleteEcosystemFor888()` (используется Action 888) регистрирует полный набор UUPS-контрактов (`MagicRegistry`, `SpiralEngine`, `ProductRegistry`, `OrganicComponentRegistry`, `AmanitaInternational`, а также `SoulboundCore`, `SoulMetadata`, `SoulRecovery`, `SoulIntegration`, `SoulIdentity`).
- При необходимости дополнительные контракты можно добавить через `registerProxy()` или пакетно через `magicRegistry.registerMany([...])`.

### Главные методы
- `deployProductSuite({ componentsPerSeller, componentIds, forceRedeploy })` — аналог интеграционного suite, но на реальном узле.
- `registerProxy(contractName, proxyAddress, logicAddress)` — ручная регистрация дополнительного контракта.
- `loadContractFromSuite(contractName)` — возвращает `{ proxy, implementation }` из MagicRegistryHelper (бросает ошибку, если не найден).
- Утилиты валидации:
  - `assertCidFormat(value)` — базовая проверка CID (`Qm...`).
  - `validateCsvHeaders(headers, required)` — быстрая проверка CSV-структуры (по умолчанию `product_id`, `name`, `description`, `price`, `category`).

### Пример
```js
const { E2EHarness, expectEvent, assertRegisteredProxy } = require('../helpers');

const harness = new E2EHarness();
await harness.startHardhatNode();
const suite = await harness.deployProductSuite({ forceRedeploy: true });

// Проверяем регистрацию ProductRegistry в MagicRegistry
const entry = harness.loadContractFromSuite('ProductRegistry');
assertRegisteredProxy(
  { ProductRegistry: entry },
  'ProductRegistry',
  suite.productRegistryAddress,
  suite.productRegistryLogicAddress
);

// Создаём продукт и проверяем событие
await expectEvent(
  suite.productRegistry.connect(suite.seller)
    .createProduct('e2e-prod-1', [suite.sellerComponentIds[0]], 'QmCID'),
  suite.productRegistry,
  'ProductCreated'
);
```

## MagicRegistryHelper

### API
```js
const registry = new MagicRegistryHelper();
registry.register('ProductRegistry', proxy, implementation);
registry.registerMany([
  ['SpiralEngine', proxyAddress, implementationAddress],
  ['ProductRegistry', proxyAddress, implementationAddress]
]);
const entry = registry.resolve('ProductRegistry');
registry.assertRegistration('ProductRegistry', expectedProxy, expectedImplementation);
registry.clear();
```
- Используется во всех harness’ах и тестах вместо ручного чтения `.env`.
- При отсутствии записи выбрасывает ошибку с понятным сообщением.
- Поддерживает пакетную регистрацию `registerMany` (передаём массив `[contractName, proxy, implementation]`).

## Assertion Helpers (обновления)
- `expectRevertCustom(...)` поддерживает новые ошибки (`BusinessIdExists`, `NotASeller`).
- `assertBusinessIdFormat(value)` и `assertCidFormat(value)` — единые проверки формата.
- `assertRegisteredProxy(registry, contractName, expectedProxy, expectedImplementation)` — гарантия наличия записи в MagicRegistry.

## E2E Pipeline Наблюдения
- **Action 43**: используйте suite-хелперы для получения адресов/ролей; `clearSellerCatalog` следует вызывать от имени продавца.
- **Action 444**: проверяйте наличие `product_id` перед регистрацией; CID генерируйте и валидируйте через `assertCidFormat`.
- **Action 2 / Action 888**: вместо `.env` используйте `loadContractFromSuite` и `assertRegisteredProxy` для проверки развёрнутых прокси/логики.

### Action 888 — Error Cases (актуальные кастомные ошибки)
- `InviteNotFound()` — пустой или отсутствующий `deployerInvite` при `activateUser`.
- `EmptyBusinessId()` — попытка вызвать `createProduct` без `businessId`.
- `InvalidUserAddress()` — `grantSellerRole` с нулевым адресом.
- `InvalidInviteCount()` — `activateUser` с несуществующим инвайтом / неверным массивом новых инвайтов.
- `UserAlreadyActivated()` — повторная активация тем же инвайтом.
- Проверки выполняются через `expectRevertCustom(...)`; текстовые `rejectedWith` больше не используются.
- Для восстановления окружения после suite вызывайте `restoreBaseRegistry(deployedContracts)` — иначе эти ошибки могут маскироваться `Contract ... not registered`.

## Рекомендации
1. **Не храните адреса в .env для тестов** — используйте MagicRegistryHelper.
2. **Используйте suite-объекты**: они возвращают Signer’ов и компоненты, избегайте ручного поиска.
3. **Валидация данных**: при работе с CSV/JSON выполняйте проверки `validateCsvHeaders` и `assertBusinessIdFormat` перед вызовами контрактов.
4. **Документируйте зависимости**: при добавлении новых UUPS-контрактов обновляйте регистрацию в harness’ах и описывайте в этом документе.
