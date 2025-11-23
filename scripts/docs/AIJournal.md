## 📅 2025-11-10 — Analysis: Поддержка `businessId` в `scripts/tests`

### 🧭 Контекст
- Цель: переосмыслить верхнеуровневые тесты (unit helpers, integration, E2E) после изменения сигнатуры `ProductRegistry.createProduct(businessId, componentIds, metadataCID)`.
- Исходные контракты и контрактные тесты уже унифицированы под `businessId`, однако JS-слой (`scripts/tests`) остаётся на старой модели (`productId`, `registerProduct`).

### 🔍 Ключевые наблюдения
- **E2E Action 43 / 444**: используют устаревший вызов `registerProduct(productId, cid)` и не деплоят `OrganicComponentRegistry`, из-за чего не проверяют события/маппинги по `businessId`.
- **Workflow-тесты** (`workflows/catalog-pipeline.e2e.test.js` и др.) читают CSV без контроля колонки `businessId`; pipeline не гарантирует передачу идентификатора до смарт-контракта.
- **Integration Harness** не разворачивает компонентный реестр, поэтому интеграционные тесты не могут безопасно вызывать `createProduct` с валидными компонентами.
- **contracts.integration.test.js** валидирует конфигурацию и взаимодействия Arweave↔ContractManager, но не подтверждает `businessId`-контракт между Actions/CoreLogic и ProductRegistry.
- **Performance/flow сценарии** опираются на фиктивные `productId` и не замеряют эффекты очистки каталога, событий `ProductCreated`/`CatalogCleared` и mapping `businessIdToProductId`.
- **Fixtures** не гарантируют наличие валидных `businessId`; проверки на уровне CSV/JSON отсутствуют.

### ⚠️ Риски
- Верхние уровни не ловят регрессии по `businessId`; возможен тихий слом pipeline.
- Отсутствие проверки `businessIdToProductId` в E2E не страхует чистку каталога.
- Интеграционный слой не фиксирует недостающую инициализацию (OCR, SELLER_ROLE), поэтому dev/test окружение расходится с контрактной реальностью.

### ✅ План доработок (businessId-first)
1. **Расширить Harness**
   - Обновить `IntegrationHarness`/`E2EHarness`: деплой `OrganicComponentRegistry`, создание тестовых компонентов и линковка с `ProductRegistry`.
   - Ввести общие helper’ы (`expectRevertCustom`, `expectEvent`, валидация mapping) для reuse в integration/E2E.
2. **Интеграционные тесты (`contracts.integration.test.js`)**
   - Добавить сценарии CoreLogic/CoreManager → ContractManager → ProductRegistry: успешное `createProduct`, чтение `getProductIdByBusinessId`, очистка каталога.
   - Проверить, что `ActionsManager` транслирует `businessId` при массовых регистрациях/clear.
3. **E2E Action 43 / 444 и workflows**
   - Переписать регистрацию продуктов на новую сигнатуру (`createProduct`), заменить `productId` → `businessId`.
   - Подтвердить событие `ProductCreated`, корректность `businessIdToProductId`, очистку catalogVersion.
   - Убедиться, что CSV/JSON pipeline сохраняет `businessId` и отлавливает пропуски.
4. **Workflow & performance тесты**
   - Актуализировать измерения: реальные вызовы через Actions/CoreLogic, проверка времени/газа на `businessId`-потоке.
5. **Fixtures и конфигурация**
   - Обновить CSV/JSON-фикстуры с валидным `businessId`, добавить проверки в unit-тестах, что поле присутствует.

### 📌 Следующие шаги
- Согласовать план.
- После одобрения — разложить задачи в рабочий трекер и выполнить по @run-task.mdc (Harness → Integration → E2E → workflows → fixtures).

---

## 📅 2025-11-10 — E2E Regression Audit (Action 43/444/2/888)

### 🔍 Наблюдения
- **Action 43 (Contract Registration)**: сценарии вызывают отсутствующие view (например, `getOrganicComponentRegistry`, `getProductIdCounter`), ожидают устаревший custom error (`BusinessIdAlreadyUsed`) и исполняют `clearSellerCatalog` от admin вместо seller.
- **Action 444 (Automatic Pipeline)**: блок валидации состояния использует неинициализированную переменную `headers`, что приводит к `ReferenceError` и отсутствию проверки `businessId` в CSV.
- **Action 2 (Setup System Connections)** и цепочка **Action 888**: тесты полагаются на заполненный MagicRegistry/.env, вызывают `MagicRegistry.get`, проверяют старый шаблон инвайта (`AMANITA-XXXX-XXXX`) и ожидают поля, которых нет в текущем TDD.

### ⚠️ Проблемы
1. Несоответствие API — E2E тесты не синхронизированы с обновлёнными контрактами (`BusinessIdExists`, отсутствие геттеров).
2. Недостаток accessor’ов в harness’ах — адреса прокси/OCR/SpiralEngine не пробрасываются, поэтому сценарии читают их через MagicRegistry и получают `0x0`.
3. Устаревшие проверки pipeline/инвайтов — жёсткие regex/headers вызывают ложные падения.

### 🏗 Архитектура решений
- **Action 43**: использовать адреса, возвращаемые `deployProductSuite`, вместо обращений к несуществующим view; обновить ожидание ошибки на `BusinessIdExists`; выполнять `clearSellerCatalog` от имени seller.
- **Action 444**: вычислять `headers` внутри теста и централизовать проверку наличия `product_id`/`businessId` в CSV.
- **Action 2 / Action 888**: 
  - расширить `E2EHarness` мини-Registry (регистрировать прокси после деплоя),
  - адаптировать тесты к API `getContract` и опираться на данные harness’а, а не на `.env`,
  - унифицировать шаблон инвайта и переопределить проверки seller state на реальные роли/активацию.
- Вынести инварианты (`assertBusinessId`, invite regex, state snapshot) в helpers, чтобы использовать одинаково во всех тестах.

### 🔄 Следующие шаги
1. Обновить harness’ы и helper’ы под новую схему адресов и ошибок:
   1 IntegrationHarness: возвращать все адреса (logic/proxy/OCR/SpiralEngine), дополнительно трекать seller/admin signers и экспортировать методы очистки/ролей.
   2 E2EHarness: после деплоя регистрировать адреса в локальном MagicRegistry, добавить вспомогательный `loadContractFromSuite(contractName)` и экспортировать CID/CSV валидации.
   3 AssertionHelpers: синхронизировать custom error имена (`BusinessIdExists`, `NotASeller`), добавить проверки для MagicRegistry (`assertRegisteredProxy`) и businessId формат.
   4 MagicRegistry utils: создать модуль-хелпер для регистрации/чтения прокси, использовать его в harness’ах и e2e тестах вместо прямых обращений к `.env`.
   5 Документация: идентифицировать все связанные docs по использованию suite-объектов и новым helper’ам, чтобы остальные сценарии придерживались единого интерфейса. либо создать доки по e2e тестам и тому как идет создание harness со всеми деплоями и UUPS архитектурой.
2. Переписать сценарии Action 43/444/2/888 и повторно прогнать `scripts/tests/e2e`.
   1 Action 43 (Contract Registration):
      1 Обновить тесты под новую сигнатуру `createProduct` и использовать функции suite (без вызова несуществующих view).
      2 Проверять событие `ProductCreated` и mapping `businessIdToProductId` через `assertBusinessIdMapping`.
      3 В сценарии повторного `businessId` ожидать ошибку `BusinessIdExists`.
      4 Для `clearSellerCatalog` использовать seller-сигнер или helper `clearSellerCatalog`.
   2 Action 444 (Automatic Pipeline):
      1 Проверять CSV headers через `validateCsvHeaders` перед регистрацией.
      2 При регистрации продуктов использовать harness-suite (CID валидировать через `assertCidFormat`).
      3 Добавить проверки очистки mapping и catalogVersion после pipeline.
   3 Action 2 (Setup System Connections):
      1 Заменить чтение `.env` на `loadContractFromSuite`/`assertRegisteredProxy`.
      2 Проверять, что SBT/SpiralEngine/ProductRegistry/OCR зарегистрированы в MagicRegistry.
      3 Обновить тесты idempotency, используя helper `registerProxy` и MagicRegistry.
   4 Action 888 (Full Pipeline):
      1 Обновить валидацию входных параметров (гибкий шаблон invite, `AMANITA-[A-Z0-9-]+`).
      2 Использовать MagicRegistryHelper для загрузки контрактов вместо прямого доступа к `.env`.
      3 Проверять состояние seller через роли/активацию вместо timestamp.
      4 Обновить проверки шагов 7–8 (SoulIdentity, catalog upload) с учётом новых helper’ов.
      5 Переписать error-сценарии с использованием обновлённого API harness’ов.
   5 E2E Regression Pass:
      1 После обновления всех сценариев запустить `scripts/tests/e2e`.
      2 Зафиксировать проблемные кейсы/результаты и обновить журнал.
3. Зафиксировать результат и синхронизировать документацию по pipeline/инвайтам.

---

## 📅 2025-11-11 — E2E Regression Pass (итоги прогона)

### 📊 Результат прогона `./node_modules/.bin/mocha scripts/tests/e2e/**/*.test.js`
- `173 passing` / `6 pending` / `14 failing` (время выполнения ~13s)
- Тесты с префиксом pending — ещё нераскрытые TDD-заглушки, не требуют немедленной реакции.

### ❌ Падения (группировка)
1. **Action 444 — Automatic Pipeline**
   - CID валидация ломается (`assertCidFormat`) из-за псевдо-CID `QmPipeline*` и base36 генератора `generateCid()`.
   - Дублируется очистка каталога внутри цикла, нет единого вызова `clearSellerCatalog`.
2. **Action 2 — Setup System Connections**
   - `deployAllContractsForTest` не определяет `harness`; после рефакторов обращение идёт к несуществующей переменной.
3. **Action 888 — Full Pipeline**
   - Использование `MagicRegistry.get` (контракт `AmanitaRegistry` не имеет метода `get`, нужно `loadContractFromSuite`).
   - `MagicRegistryHelper` неполный: не регистрируются `SoulIdentity`, `SoulboundCore`, `SoulMetadata`, из-за чего `loadContractFromSuite` падает.
   - `rejectedWith` в chai отсутствует — требуется переход на `expectRevertReason` или явный `try/catch`.
   - CID/BusinessId проверки в шагах 8 используют вспомогательные ID, которые не отвечают regex.
   - `SpiralEngine`/`SoulIdentity` ABI: контракт attachится неверно (проксируется логика без `attach`), из-за чего `ACTIVATOR_ROLE()` выбрасывает BAD_DATA.
   - Error-сценарии вызывают `.activateUser(null, …)` — до revert не доходит, ловим `Cannot read properties of null`.

### 🔁 Требуемые блоки исправлений
- **Группа A (CID & Catalog):** Action 444 + Action 888 Step 8 — валидный base58 CID, корректная регистрация/очистка каталога, единый вызов `clearSellerCatalog`.
- **Группа B (Harness/Registry):** добор записей в `MagicRegistryHelper`, единообразный `attach` прокси/логики, отказ от `MagicRegistry.get`.
- **Группа C (Action 2 setup):** исправить `deployAllContractsForTest`, привести `before all` к новому API harness’а.
- **Группа D (Error handling & chai):** заменить `rejectedWith`, переписать сценарии с `null/undefined` через реальные цепочки (отсутствующий invite → создать/удалить), скорректировать ABI-вызовы (`inviteCodeExists`/`inviteCodeToTokenId`).
- **Группа E (Performance hooks):** после правок группы B обновить performance-тесты (они теряются на `loadContractFromSuite`).

### 📐 Подробные планы реализации
- **A. CID & Catalog**
  1. Определить `generateValidCid()` в `E2EHarness` (предопределённый base58 список или библиотека) и заменить все вызовы `generateCid`/`QmPipeline*` в Action 444/888.
  2. В `action444.e2e.test.js` переписать регистрацию продуктов: использовать seller-сигнер из suite, сохранять массив созданных CID, вызывать `clearSellerCatalog` один раз после цикла, а не внутри.
  3. В `action888.e2e.test.js` шаг 8 повторно использовать seller-сигнер и общий helper очистки каталога; после очистки проверить `catalogVersion` и `assertBusinessIdCleared` для всего списка.
  4. Добавить unit-проверку для `generateValidCid()` (микротест в helper’ах), чтобы исключить регрессию base58.

- **B. Harness & MagicRegistry**
  1. В `deployCompleteEcosystemFor888` регистрировать в локальном `MagicRegistryHelper` пары proxy/logic для всех контрактов (`MagicRegistry`, `SpiralEngine`, `ProductRegistry`, `OrganicComponentRegistry`, `SoulIdentity`, `SoulboundCore`, `SoulMetadata`, `SoulRecovery`, `SoulIntegration`, `AmanitaInternational`).
  2. Привести `getContractInstance` к паттерну `logic.attach(proxy)` (или `ethers.getContractAt(abi, proxy)`), чтобы ABI соответствовал proxy-адресу.
  3. В `MagicRegistryHelper` добавить метод `registerMany(entries)` для атомарной регистрации (использовать при деплое), обновить harness для вызова этой функции.
  4. Перепроверить `IntegrationHarness` и `E2EHarness` на предмет обращений к `MagicRegistry.get` — заменить на `loadContractFromSuite`.
  5. Обновить `harness-and-e2e.md`, зафиксировав новую схему регистрации и способ получения адресов.

- **C. Action 2 setup**
  1. В `deployAllContractsForTest` создать `const harness = new E2EHarness()`, вызывать `deployProductSuite({ forceRedeploy: true })`, зарегистрировать адреса через `harness.registerProxy`, вернуть suite и адрес MagicRegistry.
  2. В `before all` Action 2 заменить обращения к `.env` на данные из возвращаемого suite (использовать `harness.loadContractFromSuite`).
  3. Актуализировать idempotency-тест: проверять записи MagicRegistry через свежий helper, убедиться, что список контрактов беру из suite.
  4. Добавить негативный тест «пустой registry» через `harness.magicRegistry.clear()` и `expect(() => loadContractFromSuite).to.throw`.
  5. Вынести `let harness`, `let suite` в верх файла, инициализировать `harness = new E2EHarness()` в `before`, сохранять suite и MagicRegistry, чтобы `deployAllContractsForTest`/`before all` разделяли один инстанс.

- **D. Error Handling & chai**
  0. В prerequisites Action 888 гарантировать генерацию `deployerInvite` (вызвать Action 777/helper), сохранить значение в suite и переиспользовать по всем шагам.
  1. Заменить `chai`-синтаксис `to.be.rejectedWith` на `await expectRevertReason(...)` либо `try/catch` + `expect.fail` в `action888.e2e.test.js`.
  2. Сценарий «invite отсутствует»: вызывать `activateUser('' /* пустая строка */, …)` и ожидать `invalid invite code`; сценарий «invite не существует»: `fakeInvite`, проверка через `expectRevertReason`.
  3. Для «invite уже использован» выполнить первую активацию, затем повторную с тем же кодом и ожидать `invite already used`.
  4. Перенести вызовы `inviteCodeExists`/`inviteCodeToTokenId` на контракты, созданные через `logic.attach(proxy)` (решение группы B), чтобы устранить BAD_DATA.
  5. Обновить документацию/комментарии в тестах, описав ожидаемые ошибки (`BusinessIdExists`, `NotASeller`, `invalid invite code`).

- **E. Performance & Benchmarking**
  1. После завершения группы B перепроверить performance-тесты: убедиться, что все контракты берутся через `loadContractFromSuite`, что `deployCompleteEcosystemFor888`/`deployProductSuite` вызывают `magicRegistry.registerMany(...)` до замеров, и реестр заполнен.
  2. Включить sanity-проверки (`assertRegisteredProxy`) перед замерами, чтобы исключить падения из-за пустого реестра.
  3. Обновить логирование: выводить реальные значения CID, адресов и времени после перехода на новый helper (в Action 888 perf-сценариях добавлены proxy/impl/CID логи).
  4. Добавить smoke-проверку, что после performance-пайплайна состояние catalog/seller сохраняется (быстрая проверка `assertSellerState`).

### 🧪 E2E Regression — 12.11.2025 10:55

**Результат прогона:** `179 passing / 6 pending / 8 failing`

#### Группа G1 — Harness/Action 2 (1 падение)
- **Источник:** `Action 2 – Setup System Connections` (`before all`).
- **Ошибка:** `TypeError: deployerSigner._signingKey is not a function` — Hardhat v6 возвращает signer без `_signingKey()`.
- **Архитектура решения:** получать приватный ключ через `signer.privateKey` (доступно в v6) с fallback на `signer.key`; исключить прямой вызов `_signingKey`.
- **План:**
  1. Обновить `action2.e2e.test.js`, заменив `_signingKey()` на безопасный accessor.
  2. Перепрогнать только Action 2, убедиться в корректном suite/harness после фикса.

#### Группа G2 — MagicRegistryHelper заполнение (5 падений)
- **Тесты:** Action 888 — полный workflow, system state validation, error-сценарии `invite not found` / `invite already used`, performance (оба).
- **Ошибки:** `Contract <…> is not registered in MagicRegistryHelper`, `BAD_DATA` при `ACTIVATOR_ROLE()` и `inviteCode*`.
- **Причина:** в `deployCompleteEcosystemFor888` не все контракты регистрируются через `magicRegistry.registerMany` (нет `SoulIdentity`, `SoulboundCore` и т.д.), либо helper очищается перед использованием.
- **Архитектура решения:** 
  - расширить `registerMany` вызов в deploy-хелпере, добавив все UUPS + SBT контракты; 
  - убедиться, что перф-тесты и error-сценарии не вызывают `magicRegistry.clear()` без последующего восстановления.
- **План:**
  1. Обновить `deployCompleteEcosystemFor888`, добавить недостающие пары proxy/logic.
  2. Проверить, нет ли лишних `magicRegistry.clear()` в тестах.
  3. Повторно прогнать выбросившие тесты (полный run Action 888).

#### Группа G3 — SoulIdentity интерфейс (2 падения)
- **Тесты:** Action 888 Step 7 (SoulIdentity), performance smoke.
- **Ошибки:** `SoulIdentity.setSoulboundIdentity is not a function`, `BAD_DATA` при `ACTIVATOR_ROLE()`.
- **Причина:** тест вызывает метод, которого нет в logic ABI, либо контракт загружен с неверным ABI.
- **Архитектура решения:** 
  - Проверить актуальный интерфейс `SoulIdentity`; заменить вызов на корректный (возможно, `setSoulIdentity` или другой метод). 
  - После исправления G2 убедиться, что ABI-контекст верный (attach logic).
- **План:**
  1. Просмотреть Solidity-контракт SoulIdentity и выяснить правильный метод для ожидаемого revert.
  2. Обновить тест на корректный вызов/ожидаемую ошибку.
  3. Запустить Step 7 и связанные smoke-проверки локально.

#### Следующие шаги
1. Исправить G1 → перепроверить Action 2.
   - 1.1 Обновить `action2.e2e.test.js`: заменить получение приватного ключа (`_signingKey`) на `signer.privateKey || signer.key`.
   - 1.2 Перезапустить только `Action 2` (`mocha scripts/tests/e2e/actions/deploy/action2.e2e.test.js`).
   - 1.3 Если тест зелёный — зафиксировать в журнале, иначе повторить анализ.
2. Исправить G2 → частичный прогон Action 888 (главный блок).
   - 2.1 Расширить `deployCompleteEcosystemFor888` и `E2EHarness.deployProductSuite`: зарегистрировать **все** контракты через `magicRegistry.registerMany` (SpiralEngine, ProductRegistry, OrganicComponentRegistry, AmanitaInternational, SoulboundCore/Metadata/Recovery/Integration/Identity + MagicRegistry).
   - 2.2 Проверить, что ни один тест не оставляет `magicRegistry` пустым (убрать/обновить `clear()` в performance/error-сценариях).
   - 2.3 Прогнать `scripts/tests/e2e/actions/full/action888.e2e.test.js`, убедиться что ошибки регистрации ушли.
3. Исправить G3 → прогон только `action888.e2e.test.js`.
   - 3.1 Изучить интерфейс `SoulIdentity`: корректный метод для негативного сценария (возможно `setSoulIdentity`, `setSoulboundIdentity` отсутствует).
   - 3.2 Обновить Step 7: вызывать существующий метод и ожидать реальный revert (или корректно грузить ABI).
   - 3.3 Прогнать целевой тест файл и проверить, что BAD_DATA/`not a function` исчезли.
4. После всех правок — полный e2e regression.
   - 4.1 Выполнить `mocha "scripts/tests/e2e/**/*.test.js" --config scripts/tests/.mocharc.json`.
   - 4.2 Зафиксировать результат в журнале, обновить планы / выявить новые группы.
   - 4.3 При необходимости повторить цикл до полного зелёного статуса.

---

## 📅 2025-11-12 — E2E Regression Pass #2 (Action 888 частичный прогон)

### 📊 Результат прогона `action888.e2e.test.js`
- `22 passing` / `7 failing` (время выполнения ~1s)
- **Прогресс:** ошибки регистрации MagicRegistryHelper устранены (G2.1/G2.2 работают), но остались отдельные блоки.

### ❌ Сохранившиеся проблемы (группировка)

#### Группа H1 — SoulIdentity Interface Mismatch (1 падение)
- **Тест:** Action 888 Step 7 — "должен пропустить SoulIdentity setup если не deployed"
- **Ошибка:** `SoulIdentity.setSoulboundIdentity is not a function`
- **Причина:** В контракте `SoulIdentity.sol` нет метода `setSoulboundIdentity`. Существующие методы: `linkSoulIdentity(string did)`, `getSoulIdentity(address user)`, `unlinkSoulIdentity()`. Тест пытается вызвать несуществующий метод для negative case.
- **Архитектура решения:**
  - Удалить вызов несуществующего метода `setSoulboundIdentity`.
  - Для negative case использовать проверку конфигурации через `assertSoulIdentitySetup` с неверным адресом (например, `ethers.ZeroAddress` для `soulMetadata` или `soulboundCore`).
  - Либо проверить, что `soulMetadata`/`soulboundCore` не соответствуют ожидаемым адресам через view-функции.
  - Альтернатива: проверить, что `SpiralEngine.setSoulIdentity` revert-ится при неверном адресе (но это уже проверяется в других тестах).

#### Группа H2 — MagicRegistryHelper Registration Gaps (4 падения)
- **Тесты:** Complete workflow, System state validation, Error scenarios (`invite not found` / `invite already used`)
- **Ошибки:** `Contract SoulIdentity is not registered in MagicRegistryHelper`, `BAD_DATA` при `ACTIVATOR_ROLE()`, `inviteCodeExists`, `inviteCodeToTokenId`
- **Причина:** 
  - В некоторых сценариях (особенно после `magicRegistry.clear()` в error-тестах) `SoulIdentity` не восстанавливается в полном списке.
  - `BAD_DATA` указывает на ABI mismatch: `getContractInstance` не всегда корректно attach-ит logic ABI к proxy для UUPS контрактов.
  - Для `SpiralEngine` (UUPS) нужно использовать `SpiralEngineLogic.attach(proxyAddress)`, но текущий `getContractInstance` может не учитывать все случаи.
- **Архитектура решения:**
  - Убедиться, что после каждого `magicRegistry.clear()` в error-сценариях восстанавливается **полный** список контрактов (включая все SBT: `SoulboundCore`, `SoulMetadata`, `SoulRecovery`, `SoulIntegration`, `SoulIdentity`).
  - Улучшить `getContractInstance`: для UUPS контрактов всегда использовать `Factory.attach(proxyAddress)`, где `Factory` создан из logic ABI (например, `SpiralEngineLogic` для `SpiralEngine`).
  - Добавить fallback: если `implementation` есть, но `attach` не работает, использовать `ethers.getContractAt(abiName, proxyAddress)` с явным указанием logic ABI.
  - Для non-UUPS контрактов (SBT) использовать `ethers.getContractAt(abiName, proxyAddress)` напрямую.

#### Группа H3 — SpiralEngine Role Management (2 падения)
- **Тесты:** Performance Benchmarking — оба теста (Action 888 < 3 min, Activation < 30s)
- **Ошибка:** `spiralWithDeployer.revokeSellerRole is not a function`
- **Причина:** В `SpiralEngineLogic` нет метода `revokeSellerRole`. Есть только `grantSellerRole(address user)`. Для отзыва роли нужно использовать стандартный `revokeRole(bytes32 role, address account)` из `AccessControl`.
- **Архитектура решения:**
  - Заменить `spiralWithDeployer.revokeSellerRole(sellerAddress)` на `spiralWithDeployer.revokeRole(SELLER_ROLE, sellerAddress)`.
  - Получить `SELLER_ROLE` через `await SpiralEngine.SELLER_ROLE()` (это `bytes32` константа).
  - Убедиться, что `deployer` имеет `DEFAULT_ADMIN_ROLE` для отзыва ролей (обычно это так после инициализации).

### 📐 Подробные планы реализации

#### H1. SoulIdentity Interface Fix
1. **Изучить negative case requirement:**
   - Цель теста: проверить, что SoulIdentity setup пропускается, если контракт не deployed или конфигурация неверна.
   - Текущий подход: вызов несуществующего метода → ожидание revert.
   - Правильный подход: проверить конфигурацию через `assertSoulIdentitySetup` с неверными адресами или использовать view-функции для валидации.

2. **Обновить тест Step 7:**
   - Удалить вызов `SoulIdentity.setSoulboundIdentity(ethers.ZeroAddress)`.
   - Использовать `assertSoulIdentitySetup` с неверным `soulMetadata` адресом (например, `ethers.ZeroAddress`).
   - Ожидать, что helper выбросит ошибку или вернёт `false` для неверной конфигурации.
   - Альтернатива: проверить, что `soulIdentity.soulMetadata()` возвращает неверный адрес, и ожидать revert при попытке использования.

3. **Прогнать Step 7 тест локально.**

#### H2. MagicRegistryHelper & ABI Fix
1. **Расширить восстановление MagicRegistryHelper:**
   - В error-сценарии "contracts not deployed" после `magicRegistry.clear()` восстановить **все** контракты из `deployedContracts`:
     ```javascript
     harness.magicRegistry.registerMany([
       ['MagicRegistry', deployedContracts.magicRegistry, null],
       ['SpiralEngine', deployedContracts.spiralEngine, deployedContracts.spiralEngineLogic],
       ['ProductRegistry', deployedContracts.productRegistry, deployedContracts.productRegistryLogic],
       ['OrganicComponentRegistry', deployedContracts.organicComponentRegistry, deployedContracts.organicComponentRegistryLogic],
       ['AmanitaInternational', deployedContracts.amanitaInternational, deployedContracts.amanitaInternationalLogic],
       ['SoulboundCore', deployedContracts.soulboundCore, null],
       ['SoulMetadata', deployedContracts.soulMetadata, null],
       ['SoulRecovery', deployedContracts.soulRecovery, null],
       ['SoulIntegration', deployedContracts.soulIntegration, null],
       ['SoulIdentity', deployedContracts.soulIdentity, null]  // ✅ Убедиться, что включён
     ]);
     ```

2. **Улучшить `getContractInstance` для UUPS:**
   - Для UUPS контрактов (когда `implementation` не `null`):
     ```javascript
     const getContractInstance = async (contractName, abiName) => {
       const proxyAddress = getProxyAddress(contractName);
       const implementation = getImplementationAddress(contractName);

       if (implementation) {
         // UUPS: attach logic ABI to proxy address
         const Factory = await ethers.getContractFactory(abiName);
         const contract = Factory.attach(proxyAddress);
         
         // Sanity check: попробовать вызвать простую view-функцию
         try {
           if (contractName === 'SpiralEngine') {
             await contract.SELLER_ROLE(); // Проверка ABI
           }
         } catch (e) {
           console.warn(`⚠️ ABI check failed for ${contractName}, falling back to getContractAt`);
           return ethers.getContractAt(abiName, proxyAddress);
         }
         
         return contract;
       }

       // Non-UUPS: direct getContractAt
       return ethers.getContractAt(abiName, proxyAddress);
     };
     ```

3. **Добавить fallback для BAD_DATA:**
   - Если `ACTIVATOR_ROLE()` или `inviteCodeExists` возвращают `BAD_DATA`, попробовать альтернативный способ загрузки:
     ```javascript
     // Fallback: попробовать через прямой ABI
     const abi = await ethers.getContractFactory(abiName).then(f => f.interface);
     return new ethers.Contract(proxyAddress, abi, ethers.provider);
     ```

4. **Прогнать error-сценарии и complete workflow.**

#### H3. SpiralEngine Role Revocation Fix
1. **Обновить performance тесты:**
   - Заменить `spiralWithDeployer.revokeSellerRole(sellerAddress)` на:
     ```javascript
     const SELLER_ROLE = await SpiralEngine.SELLER_ROLE();
     await spiralWithDeployer.revokeRole(SELLER_ROLE, sellerAddress);
     ```

2. **Проверить права deployer:**
   - Убедиться, что `deployer` имеет `DEFAULT_ADMIN_ROLE` (обычно это так после `initialize(deployer.address)`).

3. **Обновить оба performance теста:**
   - "должен завершить Action 888 за < 3 минут"
   - "должен выполнить activation за < 30 секунд"

4. **Прогнать performance тесты локально.**

### 🧪 Следующие шаги
1. Исправить H1 → прогон Step 7.
   - H1.1 Обновить `action888.e2e.test.js` Step 7: удалить `setSoulboundIdentity`, использовать `assertSoulIdentitySetup` с неверным адресом.
   - H1.2 Прогнать только Step 7 тест.
   - H1.3 Если зелёный — зафиксировать, иначе повторить анализ.

2. Исправить H2 → прогон error-сценариев и complete workflow.
   - H2.1 Расширить восстановление MagicRegistryHelper в error-сценарии (включить `SoulIdentity`).
   - H2.2 Улучшить `getContractInstance` с fallback для UUPS и sanity-check ABI.
   - H2.3 Прогнать error-сценарии и complete workflow.

3. Исправить H3 → прогон performance тестов.
   - H3.1 Заменить `revokeSellerRole` на `revokeRole(SELLER_ROLE, sellerAddress)` в обоих performance тестах.
   - H3.2 Прогнать performance тесты.

4. После всех правок — полный e2e regression.
   - H4.1 Выполнить `mocha "scripts/tests/e2e/**/*.test.js" --config scripts/tests/.mocharc.json`.
   - H4.2 Зафиксировать результат в журнале.

---

## 📅 2025-11-12 — Action 888 regression (после H3)

### 📊 Прогон `./node_modules/.bin/mocha scripts/tests/e2e/actions/full/action888.e2e.test.js`
- 25 passing / 4 failing (~1s)

### ❌ Падения
1. **Complete Workflow** — `Contract SoulIdentity is not registered in MagicRegistryHelper`  
   `harness.deployProductSuite()` внутри Step 8 очищает локальный `MagicRegistryHelper` и регистрирует только три контракта (SpiralEngine/OrganicComponentRegistry/ProductRegistry). После отката снапшота helper остаётся усечённым.

2. **System State Validation** — `BAD_DATA` при `ACTIVATOR_ROLE()`  
   Аналогично: `getContractInstance` использует адреса из suite-реестра, ABI не совпадает.

3. **Error Scenarios (invite not found / invite already used)** — `BAD_DATA` на `inviteCodeExists` / `inviteCodeToTokenId`  
   Всё ещё следствие усечённого реестра. Дополнительно предстоит обновить проверки на реальные custom errors (`InviteNotFound`, `InvalidInviteCount`, `UserAlreadyActivated`) — перенесено в блок D.

### 🏗 Архитектура решений
1. **Сохранность MagicRegistryHelper**
   - `E2EHarness.deployProductSuite` должен merge’ить записи, а не очищать весь helper.
   - В Step 8 после использования suite восстанавливать базовые адреса из `deployedContracts`.

2. **Контроль наличия регистраций**
   - Добавить sanity-check в `beforeEach` полного workflow: `loadContractFromSuite('SoulIdentity')` → ранний fail при отсутствии записи.

3. **Обновление error-сценариев (блок D)**
   - Перейти на `expectRevertCustom` с актуальными custom errors после устранения BAD_DATA.

### ✅ План реализации
1. **MagicRegistry Preservation**
   - 1.1 Обновить `E2EHarness.deployProductSuite`: сохранять snapshot `this.magicRegistry.registry`, регистрировать suite и затем восстанавливать исходные записи (merge).
   - 1.2 Добавить helper `restoreBaseRegistry(deployedContracts)` в тесте и вызывать его сразу после workflow Step 8.
   - 1.3 В `beforeEach` полного workflow и системных проверок проверять регистрацию SoulIdentity.

2. **Регрессия после фикса**
   - 2.1 Прогнать частичные тесты: `--grep "Complete Action 888 Workflow"` и `--grep "Complete System State Validation"`.
   - 2.2 Прогнать `--grep "Error Scenarios"` и зафиксировать новые результаты (подготовка к блоку D).

3. **Подготовка блока D**
   - Переписать error-сценарии на `expectRevertCustom` / `expectRevertReason` с актуальными custom errors (`InviteNotFound`, `InvalidUserAddress`, `InvalidInviteCount`, `UserAlreadyActivated`).

### 📌 Блок D — Error Handling & chai (подготовка к реализации)

#### Текущее состояние
- Локальный MagicRegistry теперь восстанавливается (H2.x закрыты), BAD_DATA отсутствует.
- Все error-сценарии падают исключительно из-за устаревших ожиданий: код возврата → `InviteNotFound`, `InvalidUserAddress`, `InvalidInviteCount`, `UserAlreadyActivated`, а тесты по-прежнему ждут строки `invalid invite code`, `invalid address`, и т.д.
- Утилита `expectRevertReason` ориентирована на reason string; для кастомных ошибок нужно использовать `expectRevertCustom` (уже есть в helpers).

#### План блока D
1. **Пререквизиты**  
   1 Убедиться, что `deployerInvite` сохраняется в suite (уже происходит в Step 0); задокументировать в тесте.

2. **Обновление инфраструктуры проверок**  
   - использовать `expectRevertCustom` для кастомных ошибок:  
     - `InviteNotFound` — отсутствующий или пустой инвайт  
     - `EmptyBusinessId` — при попытке создать продукт без businessId  
     - `InvalidUserAddress` — некорректный sellerAddress  
     - `InvalidInviteCount` — invite не существует / некорректный массив  
     - `UserAlreadyActivated` — повторное использование invite  
   - строковых reason теперь нет; везде применяем кастомные ошибки

3. **Сценарии Action 888**  
   1) *deployerInvite отсутствует* — ожидать `InviteNotFound()` (custom error).  
   2) *sellerAddress invalid* — ожидать `InvalidUserAddress()`.  
   3) *deployer invite не существует* — ожидать `InvalidInviteCount()` (возникает из-за некорректного массива инвайтов).  
   4) *deployer invite уже использован* — ожидать `UserAlreadyActivated()`.  
   5) Обновить комментарии/логи, чтобы явно указывать ожидаемую ошибку.

4. **ABI и обращения к invite API**  
   - Вызовы `inviteCodeExists` / `inviteCodeToTokenId` остаются через `getContractInstance('SpiralEngine', ...)` (после фиксов H2 они корректны). Проверить отрисовку helper’ов, при необходимости использовать `expectNotReverted`.

5. **Документация**  
   - Зафиксировать новые ожидаемые ошибки в `harness-and-e2e.md` (раздел по Action 888 error cases).

6. **Валидация**  
   - Запуск `--grep "Error Scenarios"` → ожидается полный зелёный статус.  
   - Затем полный `action888.e2e.test.js` для интеграционной проверки перед блоком E.

---

## 📅 2025-11-13 — E2E Deploy Actions Regression Attempt

### 🧭 Контекст
- Цель: прогнать `scripts/tests/e2e/actions/deploy/**/*.test.js` для проверки Action 0/1/2 после обновлений harness’ов.
- Команда: `DEPLOYER_PRIVATE_KEY=0xac09... ./node_modules/.bin/mocha "scripts/tests/e2e/actions/deploy/**/*.test.js" --config scripts/tests/.mocharc.json`

### 🔍 Action 2 — разбор падений
- Все 6 падений связаны с отсутствием адресов прокси в MagicRegistry/`.env`, вследствие чего `setupSystemConnections` получает `0x0` вместо фактических UUPS прокси и пропускает настройку связей.
- Логи harness’а фиксируют повторяющиеся предупреждения: `Failed to load UUPS contract <...>: Proxy адрес не найден ни в .env, ни в MagicRegistry`.
- Happy-path проверки (`setupSystemConnections`, `setupSBTEcosystem`, `OrganicComponentRegistry ↔ SpiralEngine`, idempotency, интеграция после Action 1) ожидают, что адреса подхватятся из локального MagicRegistryHelper или env, но оба источника пусты.

### 🏗 Архитектура решения (Action 2)
1. **Регистрация адресов после Action 1**
   - Убедиться, что `E2EHarness`/`SetupActions` после полного деплоя вызывают `magicRegistry.registerMany([...])` со свежими адресами всех UUPS контрактов.
   - Обновить тестовую инфраструктуру (suite, helpers), чтобы MagicRegistryHelper восстанавливался между шагами (где вызывается `magicRegistry.clear()` — возвращать базовый набор).
2. **Загрузка UUPS контрактов**
   - В `setupSystemConnections` заменить обращения к `.env` на чтение из MagicRegistry/локального helper’а.
   - Добавить fallback: если адрес не найден, логировать явную ошибку и прерывать happy-path (не пропускать «тихо»).
3. **Обновление тестов**
   - Отразить новую схему (использование `loadContractFromSuite`, проверку `assertRegisteredProxy`) в `action2.e2e.test.js`.

### 📋 План реализации
1. Расширить регистрацию адресов в `SetupActions`/`E2EHarness.deployProductSuite` после Action 1 → восстановление `magicRegistry` перед Action 2.
2. Переписать `setupSystemConnections` на работу с MagicRegistryHelper (без `.env`), добавить стоп при отсутствии адресов.
3. Актуализировать `action2.e2e.test.js` (happy-path/идемпотентность/интеграция) с учётом нового источника адресов.
4. Повторно прогнать `Action 2` suite.

### ❌ Итог
- Все три тестовых набора (`Action 0`, `Action 1`, `Action 2`) упали до выполнения сценариев.
- Причина 1: Hardhat node, поднимаемый `E2EHarness.startHardhatNode()`, зовёт `npx hardhat node`; глобальный `npx` падает с `Cannot find module 'proc-log'` → процесс завершается с кодом 7 → таймаут 30s в harness.
- Причина 2: для `Action 1` дополнительно зафиксирован `FileSystemAccessError: EPERM: scandir 'artifacts/build-info'` (Hardhat пытается прочитать build-info до деплоя).

### 📌 Наблюдения / TODO
1. **Infra:** решить зависимость `proc-log` (либо переопределить запуск на локальный `./node_modules/.bin/hardhat node`, либо доставить недостающий модуль) — без этого любой e2e тест, требующий Hardhat node, падает.
2. **Artifacts:** подготовить `artifacts/build-info` (скомпилировать контракты или отключить трейсинг в Hardhat) перед повторным прогоном deploy-цепочки.
3. Перезапустить suite после устранения инфраструктурных блокеров; без фикса `proc-log` прогон бессмысленен.

---

### ✅ Action 2 — успешный прогон после инициализации UUPS
- Команда: `DEPLOYER_PRIVATE_KEY=0xac09... ./node_modules/.bin/mocha scripts/tests/e2e/actions/deploy/action2.e2e.test.js`
- Изменения: в helper `deployAllContractsForTest` UUPS прокси (SpiralEngine, OrganicComponentRegistry) теперь получают `initialize(...)` calldata с адресом deployer → роли/владельцы назначаются корректно сразу при деплое.
- Итог: `11 passing / 0 failing` (≈1 s). Все happy-path сценарии, идемпотентность и интеграция Action 1→Action 2 прошли; AccessControl ошибок больше нет.
- Логи подтверждают, что SBT connections выполняются (`Action SBT ecosystem connections configured completed successfully`).

### 🔁 Следующие шаги
- Перейти к `b1-setupactions` (переиспользование signer и общая устойчивость), затем `c3-ree2e` (финальная проверка всей deploy-последовательности).
- Зафиксировать выданные роли в основному Action 1 (`DeployActions`) при необходимости и держать helper в синхронизации.

---

### 🔁 Action 2 — повторный прогон (после фиксов MagicRegistry & PrivateKey)
- Команда: `DEPLOYER_PRIVATE_KEY=0xac09... ./node_modules/.bin/mocha scripts/tests/e2e/actions/deploy/action2.e2e.test.js`
- Результат: 6 падений (happy path, idempotency, интеграция). Hardhat стартует и контракты грузятся из MagicRegistry, но все `setupSystemConnections()` ветки ревертятся с `AccessControlUnauthorizedAccount` при вызовах SBT setters.
- Логи: `Failed to setup SBT connections: AccessControlUnauthorizedAccount("0xf39F...92266", "0xa4980...21775")` — deployer не имеет требуемой роли для `setMetadataContract/setRecoveryContract/setSoulIdentity`.

### 🧩 Архитектура решения (AccessControl)
1. **Роли при деплое Action 1**
   - Проверить `SoulboundCore/SoulIdentity` и определить нужные роли (вероятно `DEFAULT_ADMIN_ROLE` либо специализированный `MANAGER_ROLE`).
   - После деплоя (в Action 1 и в тестовом `deployAllContractsForTest`) явно назначить эти роли deployer’у и/или SetupActions executor’у.
2. **SetupActions signer**
   - Убедиться, что `ethersUtils.getSigner()` использует тот же приватный ключ, которому выданы роли (в тесте — `process.env.DEPLOYER_PRIVATE_KEY`).
3. **Тестовое окружение**
   - В `deployAllContractsForTest` добавить шаг `grantRole` для всех необходимых ролей перед регистрацией в MagicRegistry (SBT + OrganicComponentRegistry).
   - При необходимости расширить helpers (`SetupActions`/`EthersUtils`) логами по ролям для быстрого анализа.

### 📋 План
1. Проанализировать Solidity-контракты SBT, определить требуемые роли для `set*` методов.
2. Внести правки в Action 1 (основной код и тестовый helper) — назначить роли deployer’у.
3. Повторить Action 2 e2e; ожидание — happy path зелёный, AccessControl ошибок нет.

### ✅ Action 777 — генерация рутовых инвайтов (e2e)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/component/action777.e2e.test.js`
- Результат: 2 passing / 0 failing (≈1 s). Генерация 12 инвайтов и валидация формата прошли успешно.
- Обновлено на 2025-11-13 12:52 UTC.

---

### ✅ Action 555 — загрузка компонентов (e2e)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/component/action555.e2e.test.js`
- Результат: 18 passing / 0 failing (≈0.7 s). Проверены подготовительные шаги, Arweave readines (quick mode), seller activation TDD-заглушки и основные error-сценарии.
- Время прогонов: 2025-11-13 12:54 UTC.

---

### ✅ Action 444 — автоматический pipeline (e2e)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/catalog/action444.e2e.test.js`
- Результат: 6 passing / 0 failing (≈0.64 s). Проверены фазы CSV → JSON → CID, валидация состояний, обработка ошибок (missing CSV, rollback) и performance-гард.
- Время прогона: 2025-11-13 12:56 UTC.

---

### ⚠️ Action 888 — error scenarios падают на NotASeller (e2e)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/full/action888.e2e.test.js`
- Результат: 30 passing / 1 failing — блок "Error Scenarios" (`должен выбросить ошибку если deployerInvite отсутствует`).
- Ошибка: `AssertionError… expected '…' to include 'emptybusinessid'`. Контракт `ProductRegistry.createProduct` ревертит `NotASeller` раньше, чем доходит до проверки `EmptyBusinessId`, т.к. модификатор `onlyActivatedSeller` требует SELLER_ROLE и активированного пользователя.
- Вывод: тестовый сценарий пытается в одном тесте покрыть две разные ветки (InviteNotFound + EmptyBusinessId) с неподготовленным продавцом. Требуется отдельно подготавливать продавца (активация + роли) или проверять бизнес-ID в другом сценарии.
- Время фикса: TBD. Требуется обновление helper’ов и/или тестовой архитектуры.

---

### 📋 Как подготовить продавца для e2e (используется в Action 888)
- Ориентирами служат блоки `Action 888: Step 3-6` в `action888.e2e.test.js` и `grantSellerRole()` в `scripts/tests/e2e/actions/access/validation.e2e.test.js`.
- Последовательность:
  1. Получить инвайт (`generateDeployerInvitesFor888` в before hook или «Action 777 helper»).
  2. Активировать продавца: `SpiralEngine.connect(deployer).activateUser(deployerInvite, sellerAddress, sellerInvites, 0)` (см. `action888.e2e.test.js`, тест «должен активировать seller если не активирован»).
  3. Проверить состояние `assertSellerState(...)` — гарантирует `activated=true`, роли ещё `false`.
  4. Выдать роли по порядку: `grantSellerRole` и `grantActivatorRole` от `SpiralEngine` с деплоерским signer’ом (см. `Action 888: Step 5-6` и `access/validation.e2e.test.js`).
  5. После ролей повторно вызвать `assertSellerState`, убедиться, что `sellerRole` и `activatorRole` выставлены.
- Для негативных сценариев (например, проверка `InviteNotFound`) достаточно шагов до активации: не выдавать роли, чтобы модификаторы `onlyActivatedSeller`/`NotASeller` сработали корректно.
- Для проверок `ProductRegistry.createProduct` обязательно проходить все шаги 1–4, иначе модификатор `onlyActivatedSeller` перехватит выполнение раньше бизнес-проверок (`EmptyBusinessId` и т.д.).

---

### 🛠️ План унифицированной подготовки продавца для e2e (Action 888 и смежные)
1. **Инвентаризация текущих шагов** — пересмотреть `action888.e2e.test.js` (шаги 3–6) и `scripts/tests/e2e/actions/access/validation.e2e.test.js`; учесть, что `IntegrationHarness` использует shortcuts и не годится для e2e.
2. **Helper в E2EHarness** — вынести логику в функцию `prepareSellerForE2E({ sellerSigner, deployerSigner, spiralEngine, invitesPrefix })`, которая генерирует инвайты, активирует продавца, проверяет `assertSellerState`, выдаёт `SELLER_ROLE`/`ACTIVATOR_ROLE`, повторно проверяет состояние.
3. **Разделение негативных сценариев** — сценарии InviteNotFound/NotASeller оставляем на «до активации» (без grantRole), чтобы гарантированно ловить `onlyActivatedSeller`/`NotASeller`, а проверки `ProductRegistry.createProduct`/`EmptyBusinessId` переводим на полный helper с активированным продавцом и ролями.
4. **Рефакторинг Action 888** — перевести before/after hooks и позитивные кейсы на `harness.prepareSellerForE2E`, вынести `EmptyBusinessId`/`NotActivatedUser` в отдельные describe-блоки с явным подготовленным состоянием, проверить, что снапшоты берутся до/после helper-вызовов и не ломают shared state.
5. **Кросс-проверка других e2e** — постепенно мигрировать `action555.e2e` и будущие сценарии на новый helper, исключить дублирование логики.
6. **Документация** — зафиксировать процесс в `Deploy_Full.md` (раздел Action 888) и обновить комментарии helper’а ссылками на тесты.
7. **Контрольный прогон** — после рефакторинга прогнать Action 888 e2e → 31/31 passing, затем Action 555 (и др.) для проверки обратной совместимости; результаты записать в журнал и обновить блок успешных прогонов.

---

### ✅ Action 888 — рефакторинг seller helper + негативные сценарии (2025-11-14)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/full/action888.e2e.test.js --config scripts/tests/.mocharc.json`
- Результат: 33 passing / 0 failing (≈1.0 s) после миграции на `harness.prepareSellerForE2E`.
- Что сделано:
  - Добавлен универсальный helper `prepareSellerForE2E` в `E2EHarness` (генерация инвайтов, активация, выдача SELLER/ACTIVATOR-ролей через `grantSellerRole` + `grantRole(ACTIVATOR_ROLE, …)`).
  - Хуки `Action 888: Step 5-6`, `Complete System State Validation` и свежий блок `ProductRegistry Seller Validation Errors` переключены на helper; все вызовы оборачиваются снапшотами `saveState/restoreState`.
  - Негативные сценарии разделены: InviteNotFound/InvalidInviteCount работают без активации, а `EmptyBusinessId` вынесен в отдельный тест с полностью подготовленным seller; дополнительно зафиксирована фактическая защита `SpiralEngine.grantSellerRole` (revert `UserNotActivated`) отдельным тестом.
- Выводы:
  - `ProductRegistry.createProduct` теперь проверяет `EmptyBusinessId` строго после прохождения `onlyActivatedSeller`; повторное совмещение с InviteNotFound исключено.
  - Ошибка `NotActivatedUser` в текущей архитектуре всплывает на слое SpiralEngine (grantSellerRole), поэтому она задокументирована и покрыта e2e-тестом напрямую.
  - Единый helper устранил дублирование подготовки продавца и гарантирует повторное использование `deployerInvite` между фазами.
- Время прогона: 2025-11-14 13:40 UTC (sandbox).

---

### 🔄 Следующие шаги по синхронизации с новым helper’ом (2025-11-14)
- **Action 555 / ComponentActions** — текущие e2e тесты продолжают вручную активировать seller и выдавать роли (см. `scripts/tests/e2e/actions/component/action555.e2e.test.js`, блоки `beforeEach` и `grantSellerRole`). План @run-task:
  1. **Инвентаризация (555.1)** — просмотр `scripts/tests/e2e/actions/component/action555.e2e.test.js` показал, что текущие e2e сценарии пока содержат только TDD-заглушки: ни `activateUser`, ни `grantSellerRole/grantRole`, ни `assertSellerState` фактически не вызываются (поиск по файлу подтверждает отсутствие этих вызовов). Единственное, что есть в `before`, — деплой контрактов и генерация `deployerInvite` (`generateDeployerInviteForTest`). Значит, перед внедрением helper’а понадобится:
     - добавить реальные positive-path тесты (разделы `Component Upload E2E Workflow` и `Error Scenarios`) и только затем заменить ручные шаги на helper;
     - синхронизировать helper c существующими помощниками `deployAllContractsForAction555`/`generateDeployerInviteForTest`, чтобы избежать двойной генерации инвайтов.
  2. **Миграция (555.2)** — после добавления реальных happy-path тестов (например, `describe('Component Upload E2E Workflow')` → вызовы `componentActions.action555()` в режиме `ARWEAVE=false`, `DRY_RUN=true`) подключить `harness.prepareSellerForE2E({ invitesPrefix: 'ACTION555' })` в `beforeEach`. Для негативов (NotActivated/NotSeller) использовать опции `skipActivation` / `grantRoles: false`; для повторного invite — `useExistingInvite`. Внутренние helpers `deployAllContractsForAction555` и `generateDeployerInviteForTest` должны проксировать результаты в `harness.magicRegistry`, чтобы Action 555 reuse registry как в Action 888. Требуется завести тестовый `ArweaveManager` (заглушку) вместо `null`, иначе вызовы `uploadComponentFull` падают на `this.arweaveManager.isReady()`.
  3. **Регрессия** — прогнать `./node_modules/.bin/mocha scripts/tests/e2e/actions/component/action555.e2e.test.js --config scripts/tests/.mocharc.json` с установленными `DEPLOYER_PRIVATE_KEY/SELLER_PRIVATE_KEY/SELLER_ADDRESS`, зафиксировать дату/время успешного прогона.
  4. **Документация** — синхронизировать `Deploy_Full.md` (секция Action 555) и `Testing-Architecture.md`: добавить подпункт «Seller Preparation via prepareSellerForE2E» с таблицей опций и требованиями по invitesPrefix; упомянуть, что error-сценарии теперь используют helper.
- **Action 444 / CatalogActions** — в `scripts/tests/e2e/actions/catalog/action444.e2e.test.js` seller активируется вручную через повторяющиеся вызовы `activateUser` и `grantSellerRole`. План:
  1. Внести helper в `before` и `beforeEach`, гарантируя, что seller готов перед CSV → CID pipeline.
  2. Указать в `Deploy_Full.md` (раздел Action 444) ссылку на helper и требования к invitesPrefix/количеству инвайтов.
- **Action 777 / InviteActions** — негативные сценарии (например, проверка повторного использования инвайта) должны использовать единый helper для генерации deployerInvite, чтобы исключить дублирование логики генерации кода. Необходимо:
  1. Добавить helper в `scripts/tests/e2e/actions/invite/action777.e2e.test.js` (или соответствующий файл).
  2. Зафиксировать в `AIJournal` и `Deploy_Full.md`, что генерация deployerInvite стандартизирована через helper.
- **Документация** — требуется синхронизация:
  - `Deploy_Full.md`: обновить разделы Actions 0/1/2/444/555/777/888, добавить подсекции «Seller Preparation» с ссылкой на helper и опциями (`skipActivation`, `grantRoles`, `useExistingInvite`).
  - `Testing-Architecture.md`: добавить пункт о повторном использовании `harness.prepareSellerForE2E` на e2e-уровне как обязательный шаг для сценарием, затрагивающих `ProductRegistry`.
  - `AIJournal.md`: вести отдельный список прогонов, где helper уже внедрён, и TODO для оставшихся сценариев.
- **Контроль** — после миграции каждого сценария на helper:
  - Прогнать соответствующий e2e файл (Action 555 → Action 444 → Action 777).
  - Зафиксировать дату/время успешного прогона в `Deploy_Full.md` (секция «Критический порядок для MVP»).
  - Обновить `AIJournal.md` ссылкой на конкретный тест и commit, где helper внедрён.

---

### ✅ Action 555 — seller helper smoke + mock Arweave (2025-11-14)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/component/action555.e2e.test.js --config scripts/tests/.mocharc.json`
- Результат: 19 passing / 0 failing (≈0.75 s). Включён новый реальный тест «Seller Preparation Helper» — `harness.prepareSellerForE2E` активирует продавца с reuse `AMANITA-TEST-E2E0`; проверяем `assertSellerState` (activated + SELLER_ROLE + ACTIVATOR_ROLE) и регистрируем контракты в `harness.magicRegistry`.
- Изменения в коде:
  - `MockArweaveManager` получил методы `isReady`, `getClient`, `getKey`, `getWalletAddress` и хранит состояние (client/key/wallet), что позволяет безопасно проксировать его в `ComponentActions`.
  - `action555.e2e.test.js` теперь использует агрегированный helpers import, регистрирует деплой в `harness.magicRegistry`, сохраняет `deployerInvite`/адреса в `process.env`, создаёт `MockArweaveManager` и реальный smoke-тест seller helper.
- Выводы:
  - Инфраструктура для Action 555 синхронизирована с Action 888: один и тот же helper готовит продавца и reuse’ит рутовый инвайт.
  - `ComponentActions` в e2e теперь получает валидный Arweave manager, что разблокирует дальнейшую реализацию happy-path тестов (нужно завести DRY_RUN=true + ограниченный набор фикстур).
  - Следующий шаг — дополнить `Component Upload E2E Workflow` реальными вызовами `componentActions.action555()` (с мокнутым Arweave) и покрыть негативные ветви с помощью опций helper’а.

---

### ✅ Action 444 — единый helper в deployProductSuite (2025-11-14)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/catalog/action444.e2e.test.js --config scripts/tests/.mocharc.json`
- Результат: 7 passing / 0 failing (≈0.64 s). `deployProductSuite()` теперь разворачивает UUPS-версии SpiralEngine/Organic/Product Registry, регистрирует их в `MagicRegistryHelper` и вызывает `harness.prepareSellerForE2E` (с авто-mint root invite, если отсутствует). Action 444 e2e покрыт новым тестом «Seller Preparation via Harness Helper», который проверяет `assertSellerState` перед запуском pipeline.
- Ключевые изменения:
  - `E2EHarness.deployProductSuite` заменил mock-цепочку на реальные прокси, регистрирует их в MagicRegistry и вызывает helper с настраиваемым `invitesPrefix`.
  - `prepareSellerForE2E` научился автоматически минтить root invite через `mintInvite`, если `useExistingInvite` не передан.
  - `action444.e2e.test.js` подключает `assertSellerState`, импортирует `ethers` и содержит отдельный smoke-тест seller подготовки.
- Выводы:
  - Все тесты в 44* сериях теперь используют один и тот же seller lifecycle; можно мигрировать `action43.e2e` и другие сценарии без ручной выдачи ролей.
  - Автогенерация root invite решает проблему InviteNotFound при первом запуске и будет полезна для других action (555/777) при отсутствии заранее подготовленных кодов.

---

### ✅ Action 777 — реальный SpiralEngine и prepareSellerForE2E (2025-11-14)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/component/action777.e2e.test.js --config scripts/tests/.mocharc.json`
- Результат: 3 passing / 0 failing (≈0.75 s). Тесты заменены на реальные проверки SpiralEngine:
  - Минт root invite от имени admin (UUPS-прокси из `deployProductSuite`), проверка `inviteCodeExists` и `inviteCodeToTokenId`.
  - Повторное использование root invite через `harness.prepareSellerForE2E` (генерирует 12 seller-инвайтов, подтверждаем `assertSellerState`).
  - Негативный кейс: пользователь без SELLER_ROLE не может вызвать `mintInvite` (`AccessControlUnauthorizedAccount`).
- Инфраструктура:
  - `deployProductSuite()` теперь переиспользуется для 777: возвращает `suite` с реальными proxied контрактами и зарегистрированным seller.
  - `prepareSellerForE2E` автоматически минтит root invite, если его нет, — это устраняет `InviteNotFound` при первом запуске.
- Дальнейшие шаги: перенести обновлённый hedger в документацию Action 777 и добавить негативы с истёкшим invite/InvalidInviteCount после рефакторинга InviteActions.

---

### ✅ Action 888 — полный pipeline на унифицированной подготовке (2025-11-14)
- Команда: `DEPLOYER_PRIVATE_KEY=… SELLER_PRIVATE_KEY=… SELLER_ADDRESS=… ./node_modules/.bin/mocha scripts/tests/e2e/actions/full/action888.e2e.test.js --config scripts/tests/.mocharc.json`
- Результат: 33 passing / 0 failing (≈1 s). Все шаги Action 888 (0–8) выполняются end-to-end, включая негативные сценарии и performance-блок.
- Что обновлено: 
  - `prepareSellerStateForTests()` вызывает `harness.prepareSellerForE2E`, reuse общего deployerInvite (минтится автоматически в helper’е).
  - Тесты Step 5-6, Complete System State Validation и ProductRegistry error cases больше не вызывают ручные activation/role-grant; вся подготовка центрально контролируется helper’ом.
  - Negative блок «ProductRegistry Seller Validation» теперь проверяет `EmptyBusinessId` (готовый продавец) и `UserNotActivated` на grantSellerRole, что отражает реальные гварды SpiralEngine.
- Выводы:
  - Action 888 находится в синхроне с 444/43/777 по инфраструктуре; повторный прогон на свежей ноде подтверждает 8 шагов + все error/performance кейсы.
  - Следующие доработки (TDD секции) требуют рефакторинга CatalogActions/InviteActions, но базовая e2e регрессия закрыта.

---