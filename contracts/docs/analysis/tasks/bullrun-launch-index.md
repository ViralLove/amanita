## Bullrun Launch — Contract & Tests Tasks Index

**Зона:** `contracts/docs/analysis/tasks/`  
**Цель:** собрать в одном месте **все ключевые таски для Contract Layer MVP** (SpiralEngine, Amanita Passport, social mining, токены и тесты), с ссылками на тематические индексы и явным разделением **MVP vs post‑MVP**.

Связанная навигация:  
- SBT / Passport: [sbt-index.md](./sbt-index.md)  
- Social mining: [social-mining-index.md](./social-mining-index.md)  
- Tests (SpiralEngine & infra): [tests-tasks-index.md](./tests-tasks-index.md)  
- Security / roles / LGOV: [security-tasks-index.md](./security-tasks-index.md)  
- MVP‑архитектура: `contracts/docs/SpiralEngine & LGOV Security MVP Scope.md`

---

### Легенда статусов

**S колонка (цвет + цифра):**

- ⚪ = `0` — **Todo** (постановка есть, работа не начата).  
- 🟡 = `1` — **In Progress** (идут фазы 1–5 по run-task).  
- 🔵 = `2` — **Implemented (Acceptance approved TODO change status and circle color)** (код есть, ждёт приёмки/ревью).  
- 🟢 = `3` — **Done** (фазы 1–9 завершены; коммиты/push отдельно).

**Цвет строк:**

- обычный текст — **входит в Contract Layer MVP**;  
- <span style="color:#999999">серый текст</span> — **post‑MVP / target‑state**, не блокирует запуск, но уже спланирован.

---

## A. SpiralEngine / Roles / Security (MVP)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | SEC-AC-1 | [`task-fix-spiralengine-activator-auto-role`](./task-fix-spiralengine-activator-auto-role/task-fix-spiralengine-activator-auto-role.md) | fix | Done | Auto‑grant `ACTIVATOR_ROLE` при `activateUser`; задел `_isEligibleForActivatorRole` под отзыв/возврат; тесты и доки актуализированы. |
| 🟢 | SEC-AR-1 | [`task-implement-spiralengine-activity-creator-role`](./task-implement-spiralengine-activity-creator-role/task-implement-spiralengine-activity-creator-role.md) | implement | Done | Архитектурный слой: создатель активностей = ACTIVATOR_ROLE + инвайт; roles-architecture-synthesis, decision-points task-Activities-1 и таск обновлены; код — в SEC-AC-1 и ActivityRegistry (уже ACTIVATOR_ROLE). |
| 🟢 | SEC-AR-2 | [`task-fix-activityregistry-creator-role-alignment`](./task-fix-activityregistry-creator-role-alignment/task-fix-activityregistry-creator-role-alignment.md) | fix | Done | ActivityRegistryLogic уже проверяет ACTIVATOR_ROLE + usedInviteByUser; доки и analysis выровнены; таск перенесён в папку, постановка актуализирована. |
| 🟢 | SEC-SE-1 | [`task-fix-spiralengine-seller-grant-policy-alignment`](./task-fix-spiralengine-seller-grant-policy-alignment/task-fix-spiralengine-seller-grant-policy-alignment.md) | fix | Done | Выдача SELLER только ADMIN_ROLE; событие SellerRoleGranted для оффчейн. Код и тесты закоммичены; доки (MVP Scope, SpiralEngine.md) обновлены. |

---

## B. SBT / Amanita Passport (MVP)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | **SBT-INV-1** | [`task-implement-invites-log-soul-on-activation`](./task-implement-invites-log-soul-on-activation/task-implement-invites-log-soul-on-activation.md) | implement | Done | **Full:** инвайты как лог + душа при активации. Субтаски 1.1–1.6 выполнены; feat/test/docs закоммичены. |
| 🟢 | SBT-INV-1.1 | [`subtask-1-soulbound-minter`](./task-implement-invites-log-soul-on-activation/subtask-1-soulbound-minter.md) | implement | Done | _Субтаск 1.1._ SoulboundCore: MINTER_ROLE (AccessControl), mint только owner или MINTER_ROLE; тесты обновлены и пройдены. |
| 🟢 | SBT-INV-1.2 | [`subtask-2-invites-as-log`](./task-implement-invites-log-soul-on-activation/subtask-2-invites-as-log.md) | refactor | Done | _Субтаск 1.2._ SpiralEngineLogic: инвайты только лог (_inviteIdCounter, без _mint/ERC721); совместимые view и заглушки; тесты пройдены. |
| 🟢 | SBT-INV-1.3 | [`subtask-3-mint-soul-on-activation`](./task-implement-invites-log-soul-on-activation/subtask-3-mint-soul-on-activation.md) | implement | Done | _Субтаск 1.3._ setSoulboundCore + mintSoul(user) в activateUser при balanceOf(user)==0; интеграционный тест. |
| 🟢 | SBT-INV-1.4 | [`subtask-4-facade-interfaces`](./task-implement-invites-log-soul-on-activation/subtask-4-facade-interfaces.md) | refactor | Done | _Субтаск 1.4._ Фасад без ERC721, inviteId-логика; ISpiralEngine NatSpec inviteId; тесты пройдены. |
| 🟢 | SBT-INV-1.5 | [`subtask-5-tests`](./task-implement-invites-log-soul-on-activation/subtask-5-tests.md) | tests | Done | _Субтаск 1.5._ Тесты: активация→душа (ownerOf); invite как лог; негатив «уже с душой»; 587 passing. |
| 🟢 | SBT-INV-1.6 | [`subtask-6-docs`](./task-implement-invites-log-soul-on-activation/subtask-6-docs.md) | add (docs) | Done | _Субтаск 1.6._ Доки: SpiralEngine.md, MVP Scope §2.2, 06-identity-did-invite — инвайты как лог, душа при активации, MINTER_ROLE. |
| 🟢 | SBT-PAS-1 | [`task-implement-passport-display-name-handle`](./task-implement-passport-display-name-handle/task-implement-passport-display-name-handle.md) | implement | Done | displayName и handle в SoulIdentity (маппинги); getSoulProfile(7 полей), getDisplayName/getHandle, setDisplayName/setHandle (владелец души); тесты и доки закоммичены. |
| 🟢 | SBT-REC-1 | [`task-delegate-soul-identity-recovery-to-soul-recovery`](./task-delegate-soul-identity-recovery-to-soul-recovery/task-delegate-soul-identity-recovery-to-soul-recovery.md) | fix | Done | Делегирование guardians/recovery SoulIdentity → SoulRecovery: DP B/A/hybrid; ISoulRecovery, setSoulRecovery; SoulRecovery *For методы и setSoulIdentity; getSoulProfile(guardians); тесты SoulIdentity + SpiralEngine.sbt.deep + SoulRecovery — 70 passing. |
| 🟢 | SBT-X-1 | [`task-document-passport-x-integration`](./task-document-passport-x-integration/task-document-passport-x-integration.md) | add (docs) | Done | Документ docs/tech/X-Integration-Schema.md: привязка X, discovery, превью, границы «X не source of truth»; ссылка в 10-amanita-passport-mvp-scope; AC верифицированы. |
| 🟢 | SBT-IDX-1 | [`task-implement-soul-identity-user-tokenid-index`](./task-implement-soul-identity-user-tokenid-index/task-implement-soul-identity-user-tokenid-index.md) | implement | Done | Индекс owner→tokenId в SoulIdentity (B1): notifySoulCreated/notifySoulRecovered, registerSoulTokenId(ADMIN), _getUserTokenId индекс+fallback без лимита 1000; тесты SBT-IDX-1; док ретроспективы. |

<span style="color:#999999">Post‑MVP (Passport / SBT):</span>

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | SBT-B2-1 | <span style="color:#999999">[`task-implement-sbt-temporary-key-delegation`](./task-implement-sbt-temporary-key-delegation/task-implement-sbt-temporary-key-delegation.md)</span> | implement | Done | <span style="color:#999999">B2: временный ключ в SoulIdentity — хранилище, create/revoke/get/isValid, _getEffectiveOwner, link/unlink от temp key; MAX 30 days; 10 тестов.</span> |

---

## C. Social Mining (LoveDo / LoveEmission / X)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🔵 | SM-1 | [`task-fix-lovedo-emission-interface`](./task-fix-lovedo-emission-interface/task-fix-lovedo-emission-interface.md) | fix | Implemented (Acceptance approved TODO change status and circle color) | ILoveDoPostNFT + emitForSuperlike(tokenId, liker, expectedNonce); тесты на реальном LoveDoPostNFT + LoveAmanitaRegistryMock; 9 passing. |
| 🔵 | SM-1.1 | [`task-refactor-lovedo-user-driven-superlike-flow`](./task-refactor-lovedo-user-driven-superlike-flow/task-refactor-lovedo-user-driven-superlike-flow.md) | refactor | Implemented (Acceptance approved TODO change status and circle color) | User-driven flow реализован: лайк ставит liker в LoveDo, Engine валидирует `hasSuperliked` и начисляет; добавлен anti-double-emit guard `(tokenId, liker)`; 11 passing. |
| 🟢 | SM-1.2 | [`task-refactor-lovedo-circle-depth-model`](./task-refactor-lovedo-circle-depth-model/task-refactor-lovedo-circle-depth-model.md) | refactor | Done | Реализована depth-circle модель (K=3, L=1), связь `liker -> sellerTo`, `MAX_DEPTH_HOPS` guard; circle-check убран из Engine (без дублирования); 14 passing. |
| 🔵 | SM-2 | [`task-tests-loveemission-lovedo-social-mining-mvp`](./task-tests-loveemission-lovedo-social-mining-mvp/task-tests-loveemission-lovedo-social-mining-mvp.md) | tests | Implemented (Acceptance approved TODO change status and circle color) | Добавлен отдельный suite `LoveEmissionEngine.social-mining.mvp.test.js`: accrual инварианты, depth-circle gating, monthly limits, threshold + one-shot LGOV; 8 passing. |
| 🔵 | DOC-1 | [`task-contracts-docs-vs-code-mismatches.md`](./task-contracts-docs-vs-code-mismatches.md) | analyze | Implemented (Acceptance approved TODO change status and circle color) | Проведён проход по персистентной зоне social-mining docs: синхронизированы `LoveEmissionEngine.md`, `LoveDoPostNFT.md`, `SpiralEngine & LGOV Security MVP Scope.md`; в реестре mismatch оставлены только реально открытые пункты (AmanitaRegistry API, registry дубликаты, UUPS/non-UUPS, остаточный LGOV/AGOV нейминг вне social-mining пакета). |
| 🔵 | DOC-2 | [`task-sync-loveemission-engine-docs`](./task-sync-loveemission-engine-docs/task-sync-loveemission-engine-docs.md) | fix (docs) | Implemented (Acceptance approved TODO change status and circle color) | Закрыта синхронизация `contracts/docs/LoveEmissionEngine.md` с `LoveEmissionEngine.sol`: устранён остаточный event mismatch (`amanitaAmount/agovAccrued` → `lovecoinAmount/lgovAccrued`), AC/DoD в задаче отмечены выполненными. |

---

## D. Tokens / Loyalty ($LOVECOIN / $LGOV / $AMANITA)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🔵 | CORE-1 | [`task-fix-tests-ethers-v6-bigint`](./task-fix-tests-ethers-v6-bigint.md) | fix (infra) | Implemented (Acceptance approved TODO change status and circle color) | Базовая адаптация всех контрактных тестов под ethers v6/bigint (включая LoveEmission/Lovecoin/Soul*); Phase 1 infra‑миграции. |
| 🟢 | CORE-2 | [`task-fix-contracts-tests-matchers-bigint-phase2`](./task-fix-contracts-tests-matchers-bigint-phase2/task-fix-contracts-tests-matchers-bigint-phase2.md) | fix (infra) | Done | Закрыт фактический остаток Phase 2: обновлены 2 edge-теста temporary key в `SpiralEngine.sbt.deep.test.js`; verification: target suite `11 passing`, полный `npx hardhat test` — `628 passing`. |
| 🟡 | AMN-1 | [`task-validate-amanita-token-loyalty-model`](./task-validate-amanita-token-loyalty-model/task-validate-amanita-token-loyalty-model.md) | analyze/fix | In Progress | Декомпозировано в AMN-1.x: seller-only emission gating, debt ledger, redemption debt-repayment, cross-seller settlement, security/tests/docs. |
| 🔵 | AMN-1.1 | [`subtask-1-seller-emission-role-gating`](./task-validate-amanita-token-loyalty-model/subtask-1-seller-emission-role-gating.md) | analyze/fix | Implemented (Acceptance approved TODO change status and circle color) | Source-of-truth = SpiralEngine (`SELLER_ROLE` + activation + suspension check); runtime gating внедрён в `AmanitaToken.mint()`; добавлен suite `AmanitaToken.seller-gating.test.js` (6 passing). |
| 🔵 | AMN-1.2 | [`subtask-2-seller-emission-and-debt-ledger`](./task-validate-amanita-token-loyalty-model/subtask-2-seller-emission-and-debt-ledger.md) | implement | Implemented (Acceptance approved TODO change status and circle color) | Реализован ledger (`sellerDebt`, `sellerTotalEmitted`, liquidity counters), hybrid debt caps (absolute + ratio), activeLiquidity=`accepted-refunds`; emission-flow без дублирования `MINTER_ROLE`; тесты `AmanitaToken.seller-gating.test.js` — 23 passing. |
| ⚪ | AMN-1.3 | [`subtask-3-redemption-and-debt-repayment`](./task-validate-amanita-token-loyalty-model/subtask-3-redemption-and-debt-repayment.md) | implement | Deprecated | Сабтаск деприкейтнут; требования перенесены в standalone task `AMN-2` (вариант C). |
| ⚪ | AMN-1.4 | [`subtask-4-cross-seller-settlement`](./task-validate-amanita-token-loyalty-model/subtask-4-cross-seller-settlement.md) | implement | Todo | Межселлерский взаимозачет (net settlement), правила клиринга и защита от двойного учета. |
| ⚪ | AMN-1.5 | [`subtask-5-security-tests-and-docs`](./task-validate-amanita-token-loyalty-model/subtask-5-security-tests-and-docs.md) | tests/add | Todo | Security hardening, анти-абьюз, тесты и синхронизация docs/acceptance verification. |
| 🟡 | AMN-2 | [`task-implement-amanita-checkout-escrow-redemption`](./task-implement-amanita-checkout-escrow-redemption/task-implement-amanita-checkout-escrow-redemption.md) | implement | In Progress | `AmanitaCheckout`: **композитная** оплата (AmanitaCoin + LoveCoin + внешняя логически), on-chain capture как **частичное** funding; **`Paid` только** buyer declare полной оплаты + seller accept; AMN→`sellerDebt` инкрементально; профильная репутация/reminders — **AMN-2.6**; адаптер — **AMN-2.3**. |
| 🔵 | AMN-2.1 | [`subtask-1-checkout-order-lifecycle-and-roles`](./task-implement-amanita-checkout-escrow-redemption/subtask-1-checkout-order-lifecycle-and-roles.md) | implement | Implemented (Acceptance approved TODO change status and circle color) | Реализован `AmanitaCheckout` (новый контракт) с lifecycle `Created -> Paid -> Settled/Cancelled`, role model `DEFAULT_ADMIN_ROLE + CHECKOUT_WRITER_ROLE`, и согласованной cancel policy B (buyer self-cancel только в `Created`; writer cancel в `Created|Paid`); suite `AmanitaCheckout.lifecycle.test.js` — 10 passing. |
| 🔵 | AMN-2.2 | [`subtask-2-payment-routing-and-redemption-apply`](./task-implement-amanita-checkout-escrow-redemption/subtask-2-payment-routing-and-redemption-apply.md) | implement | Implemented (Acceptance approved TODO change status and circle color) | Композитное funding + attestation-gated `Paid`; `AmanitaToken.applyOrderDebtRepayment`; emergency `markOrderPaid` только admin; тесты lifecycle + composite; `acceptance-verification-amn-2-2.md`; full suite 669 passing. |
| 🔵 | AMN-2.3 | [`subtask-3-reputation-adapter-hybrid-metrics`](./task-implement-amanita-checkout-escrow-redemption/subtask-3-reputation-adapter-hybrid-metrics.md) | implement | Implemented (Acceptance approved TODO change status and circle color) | `AmanitaCommerceReputationAdapter` + hooks из `AmanitaCheckout` (capture/settle); live + `anchorSeller`; refund/dispute ops; тесты `AmanitaCommerceReputationAdapter.test.js`; `acceptance-verification-amn-2-3.md`; suite 675 passing. |
| ⚪ | AMN-2.4 | [`subtask-4-tests-checkout-redemption-reputation`](./task-implement-amanita-checkout-escrow-redemption/subtask-4-tests-checkout-redemption-reputation.md) | tests | Todo | Qualification suite для checkout/redemption/reputation инвариантов и edge cases. |
| ⚪ | AMN-2.5 | [`subtask-5-docs-and-bullrun-sync`](./task-implement-amanita-checkout-escrow-redemption/subtask-5-docs-and-bullrun-sync.md) | docs/add | Todo | Acceptance verification и синхронизация docs/bullrun после реализации AMN-2.x. |
| 🔵 | AMN-2.6 | [`task-implement-voluntary-payment-signals-commerce-reputation`](./task-implement-voluntary-payment-signals-commerce-reputation/task-implement-voluntary-payment-signals-commerce-reputation.md) | implement | Implemented (Acceptance approved TODO change status and circle color) | `confirmOrderReceived` + `signalWeakExternalPaymentClaim`; события `OrderReceivedByBuyer` / `WeakExternalPaymentClaimed`; расширенный `notifyOrderSettled` + `notifyWeakExternalPaymentClaim`; buyer/seller метрики и bps-views, `anchorBuyer`; `acceptance-verification-amn-2-6.md`; `contracts/docs/commerce-reputation-disclaimers.md`; suites adapter + `AmanitaCheckout.voluntary-signals.test.js`; full `npx hardhat test` — 684 passing. |
| ⚪ | AMN-2.7 | [`task-implement-amanita-checkout-cancel-refund`](./task-implement-amanita-checkout-cancel-refund/task-implement-amanita-checkout-cancel-refund.md) | implement | Todo | **Cancel + on-chain refund:** Love escrow → buyer при `Cancelled`; политика AMN (burn необратим / восстановление `sellerDebt` — decision record в таске); события, reentrancy, тесты. Зависит от AMN-2.2. |

---

## E. Tests (SpiralEngine core)

> Подробная разбивка по тестам — в [tests-tasks-index.md](./tests-tasks-index.md). Здесь — только high‑level таски, важные для bullrun‑запуска.

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | SBT-1 | [`task-fix-spiralengine-sbt-tests`](./task-fix-spiralengine-sbt-tests.md) | fix | Todo | Привести `SpiralEngine.sbt.test.js` к стабильному состоянию под ethers v6 (без hardhat‑chai‑matchers) + добавить smoke‑проверку профиля души. |
| 🟢 | SAN-1 | [`task-tests-spiralengine-sanctions-deep`](./task-tests-spiralengine-sanctions-deep/task-tests-spiralengine-sanctions-deep.md) | tests (deep) | Done | Deep‑suite санкций SpiralEngine (strict/edge, expectCustomError); sanctions‑smoke остаётся в основном тест‑наборе. |
| 🟢 | UUPS-1 | [`task-fix-spiralengine-upgrade-matchers`](./task-fix-spiralengine-upgrade-matchers/task-fix-spiralengine-upgrade-matchers.md) | fix | Done | UUPS‑suite SpiralEngine (smoke+comprehensive): фиксы reverted‑matchers, bigint‑сравнения LOGIC_VERSION и счётчиков. |
| 🟢 | INT-1 | [`task-fix-spiralengine-integration-roles-matchers-bigint`](./task-fix-spiralengine-integration-roles-matchers-bigint/task-fix-spiralengine-integration-roles-matchers-bigint.md) | fix | Done | `SpiralEngine.integration.test.js` + `SpiralEngine.roles.test.js`: expectCustomError, bigint для getCircleSize/usedInviteByUser/suspensionUntil/tokenId. |
| 🟢 | INT-2 | [`task-fix-spiralengine-basic-circles-matchers-bigint`](./task-fix-spiralengine-basic-circles-matchers-bigint/task-fix-spiralengine-basic-circles-matchers-bigint.md) | fix | Done | `SpiralEngine.basic.test.js` + `SpiralEngine.circles.test.js`: bigint‑корректные проверки totalInvites*, circle sizes, diagnostics. |
| ⚪ | REF-1 | [`task-refactor-tests-adapt-to-contracts-api`](./task-refactor-tests-adapt-to-contracts-api.md) | refactor | Draft | Адаптация тестов под актуальные API контрактов: чеклист тест↔контракт, связь LoveEmission с task-fix-lovedo-emission-interface, устранение устаревших вызовов. |

<span style="color:#999999">Post‑MVP усиление тестов:</span>

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | SBT-2 | <span style="color:#999999">[`task-tests-spiralengine-sbt-deep`](./task-tests-spiralengine-sbt-deep.md)</span> | tests (deep) | Todo | <span style="color:#999999">Глубокий SBT‑suite (non‑transferability, recovery, DID, B2) сверх базового MVP‑smoke.</span> |
| ⚪ | SBT-3 | <span style="color:#999999">[`task-implement-sbt-temporary-key-delegation`](./task-implement-sbt-temporary-key-delegation/task-implement-sbt-temporary-key-delegation.md)</span> | implement | Todo | <span style="color:#999999">Реализация B2‑ключей и тестов — часть расширенного SBT/Passport‑roadmap.</span> |

---

## F. LGOV Model 2 (post‑MVP target)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | LGOV-2 | <span style="color:#999999">[`task-fix-loveemission-lgov-continuous-governance`](./task-fix-loveemission-lgov-continuous-governance/task-fix-loveemission-lgov-continuous-governance.md)</span> | fix (arch) | Todo | <span style="color:#999999">Переход от one‑shot `claimLGOV` к continuous, reputation‑gated governance‑майнингу (Model 2) — следующий этап после MVP (см. Anti Sybil / Governance Architecture).</span> |

---

### Как пользоваться этим индексом

- Если задача касается **SBT / Passport / SpiralEngine security / social mining / токенов**, сперва ищи её здесь по Key/домену.  
- Для подробностей по подпроекту (tests, social‑mining, SBT) — переходи по ссылке на тематический индекс.  
- Любой новый таск, относящийся к Contract Layer и влияющий на MVP‑scope, должен:  
  - иметь собственный task‑файл по `task-standard.md`;  
  - быть привязан к тематическому индексу;  
  - появиться в `bullrun-launch-index.md` с корректным Key и статусом.

