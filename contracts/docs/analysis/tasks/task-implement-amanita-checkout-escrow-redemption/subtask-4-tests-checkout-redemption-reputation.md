## Task: tests — AMN-2.4 checkout/redemption/reputation qualification and remaining gaps

---
**Приоритет:** P0  
**Сложность:** M  
**Оценка времени:** 0.5–1 день  
**Зависимости:**  
- `subtask-1-checkout-order-lifecycle-and-roles.md`  
- `subtask-2-payment-routing-and-redemption-apply.md`  
- `subtask-3-reputation-adapter-hybrid-metrics.md`  
- `../task-implement-voluntary-payment-signals-commerce-reputation/task-implement-voluntary-payment-signals-commerce-reputation.md` (AMN-2.6)  
- `../task-implement-amanita-checkout-cancel-refund/task-implement-amanita-checkout-cancel-refund.md` (AMN-2.7)  
- `../task-implement-amanita-checkout-cancel-refund/subtask-1-buyer-amn-credit-refund-options-and-recommendation.md` (AMN-2.8)  
**Тэги:** amanita, lovecoin, checkout, order, refund, reputation, tests, qualification  
**Статус:** implemented (ожидает финальной приёмки оператора)  
---

## 1. Цель (Purpose)

Актуализировать и добить **qualification suite** для `AMN-2` уже на базе фактически реализованного checkout-стека:

- lifecycle заказа (`Created -> Paid -> Settled/Cancelled`);
- композитный funding по `$AMANITA` и `$LOVE`;
- attestation-переход в `Paid`;
- cancel/refund политика из AMN-2.7 + buyer mint-back policy из AMN-2.8;
- reputation hooks / hybrid metrics из AMN-2.3 и voluntary signals из AMN-2.6.

Задача AMN-2.4 теперь не про «создать первые тесты», а про **закрыть остаточные qualification gaps** после уже выполненных runtime/subtask-изменений.

### Почему это важно (риск)

- Базовые happy-path suite уже есть, но без отдельного qualification-прохода легко оставить ложное ощущение полноты покрытия.
- После AMN-2.7/2.8 cancel-path стал экономически сложнее: restore `sellerDebt` + buyer AMN mint-back + Love escrow refund.
- Репутационный слой должен явно не ломаться при cancel/refund и не трактовать cancel как completed commerce signal.

### Вне scope (явно)

- Новая бизнес-логика checkout/reputation beyond current contracts.
- Переписывание существующих suite «ради красоты» без закрытия реальных gaps.
- Post-MVP redesign вида deferred burn.

---

## 2. Факты из кода (Code Facts / SSOT)

1. **Checkout lifecycle suite уже существует** и покрывает role model, transition rules, self-cancel ограничения и writer/admin behavior:

```138:215:contracts/tests/AmanitaCheckout.lifecycle.test.js
it("allows cancellation only from Created/Paid", async function () {
    // ...
});

it("rejects buyer self-cancel for non-owner or non-Created status", async function () {
    // ...
    await expectRevertWithMessage(
        checkout.connect(buyer).cancelOwnOrder(orderHash3),
        "AmanitaCheckout: self-cancel locked after declare",
    );
});
```

2. **Composite funding suite уже покрывает `$AMANITA` / `$LOVE`, attestation-gated `Paid`, cancel refund и buyer AMN mint-back event**:

```208:279:contracts/tests/AmanitaCheckout.composite.test.js
it("AMN-2.7: cancelOwnOrder auto-refunds Love escrow to buyer", async function () {
    // ...
});

it("AMN-2.7: cancel restores sellerDebt by order repaid AMN amount", async function () {
    // ...
    expect(await amanitaToken.orderBuyerRefunded(orderHash)).to.equal(true);
});

it("AMN-2.8: emits BuyerOrderAmnRefunded with capturedAmanita amount", async function () {
    // ...
});
```

3. **Reputation adapter suite уже покрывает live metrics, anchor snapshots и AMN-2.6 buyer/seller signal metrics**:

```91:221:contracts/tests/AmanitaCommerceReputationAdapter.test.js
it("increments live redemption metrics on each Amanita capture", async function () {
    // ...
});

it("AMN-2.6: buyer confirmed received updates buyer metrics; bps views", async function () {
    // ...
});

it("anchorBuyer freezes buyer signal snapshot", async function () {
    // ...
});
```

4. Runtime now includes **cancel refund side effects** that are more complex than the original AMN-2.2 scope:

```334:349:contracts/AmanitaCheckout.sol
function _refundOnCancel(bytes32 orderHash, Order storage order) internal {
    if (order.capturedAmanita > 0) {
        uint256 buyerAmnRefund = order.capturedAmanita;
        // restore debt + mint-back buyer + events
    }

    if (order.capturedLove > 0) {
        // escrow refund to buyer
    }
}
```

---

## 3. Gap / Проблема

Базовые suite **уже существуют**, поэтому исходная постановка AMN-2.4 устарела. Реальный gap теперь такой:

- нет отдельного **qualification checklist/task** с явным перечислением уже покрытого и оставшихся edge cases;
- отсутствует целевой проход по **cancel/refund invariants** как по целостной подсистеме (`$LOVE` + `$AMANITA` + order status + events);
- не зафиксированы тестовые ожидания, что **cancel/refund path не должен accidentally signal successful commerce** для reputation;
- не выделены случаи, где нужна дополнительная deep-проверка beyond current happy-path suites.

---

## 4. AC/DoD

- [x] (P0) Актуализирован test scope: задача ссылается на **существующие** suite (`AmanitaCheckout.lifecycle`, `AmanitaCheckout.composite`, `AmanitaCommerceReputationAdapter`) вместо абстрактного «создать новые тесты».
- [x] (P0) Добавлен qualification checklist для `$AMANITA`:
  - [x] debt decrease on capture;
  - [x] over-capture rejection;
  - [x] restore `sellerDebt` on cancel;
  - [x] buyer mint-back one-shot refund on cancel;
  - [x] no payout after `Settled`.
- [x] (P0) Добавлен qualification checklist для `$LOVE`:
  - [x] escrow capture;
  - [x] buyer refund on cancel;
  - [x] no `sellerDebt` side effects from Love rail.
- [x] (P0) Добавлен qualification checklist для order model:
  - [x] duplicate order rejection;
  - [x] capture lock after declare;
  - [x] `Paid` only by declare+accept or admin emergency path;
  - [x] cancel matrix (`Created`, `Paid`, self-cancel restrictions, no repeat).
- [x] (P0) Добавлен qualification checklist для reputation:
  - [x] capture updates live metrics;
  - [x] settlement updates successful-order metrics;
  - [x] AMN-2.6 buyer/seller bps views;
  - [x] cancel/refund explicitly **не** приравнивается к successful commerce path.
- [x] (P1) Выделены **remaining gaps** для новых тестов, если они действительно ещё не покрыты:
  - [x] one-shot direct negative around `orderBuyerRefunded`;
  - [x] event pairing consistency (`OrderRefunded` + `BuyerOrderAmnRefunded`);
  - [x] reputation non-interaction on cancel/refund.
- [x] (P1) Задача готова к следующему run-task без перепридумывания scope.

---

## 5. Где менять код

- Основной артефакт этой задачи:  
  `contracts/docs/analysis/tasks/task-implement-amanita-checkout-escrow-redemption/subtask-4-tests-checkout-redemption-reputation.md`

- Потенциальные test files для follow-up implementation:
  - `contracts/tests/AmanitaCheckout.lifecycle.test.js`
  - `contracts/tests/AmanitaCheckout.composite.test.js`
  - `contracts/tests/AmanitaCommerceReputationAdapter.test.js`
  - при необходимости отдельный qualification suite вида `contracts/tests/AmanitaCheckout.qualification.test.js`

- Acceptance artifacts:
  - `contracts/docs/analysis/tasks/.../acceptance-verification-amn-2-4.md`

---

## 6. План выполнения

1. Зафиксировать, какие test-suites уже закрывают AMN-2.1 / 2.2 / 2.3 / 2.6 / 2.7 / 2.8.
2. Отделить **already covered** от **remaining gaps**.
3. Сформировать qualification checklist по четырём доменам:
   - `$AMANITA`,
   - `$LOVE`,
   - order lifecycle,
   - reputation / voluntary signals.
4. Явно записать, какие edge cases должны быть добавлены следующим implementation-run, если они ещё не закрыты.
5. Подготовить acceptance-verification план для AMN-2.4.

### Execution log (2026-03-23)

1. Расширены существующие suite, а не создан новый test-file:
   - `contracts/tests/AmanitaCheckout.lifecycle.test.js`
   - `contracts/tests/AmanitaCheckout.composite.test.js`
   - `contracts/tests/AmanitaCommerceReputationAdapter.test.js`
2. Добавлены qualification кейсы:
   - duplicate order hash rejection;
   - paired AMN refund events consistency;
   - one-shot negative for `orderBuyerRefunded`;
   - no cancel refund path after `Settled`;
   - reputation non-interaction on cancel/refund.
3. Создан `acceptance-verification-amn-2-4.md`.
4. Верификация:
   - target suites: **38 passing**
   - full suite: **693 passing**

---

## 7. Команды проверки

```bash
cd /Users/eslinko/Development/Amanita
npx hardhat compile
npx hardhat test contracts/tests/AmanitaCheckout.lifecycle.test.js contracts/tests/AmanitaCheckout.composite.test.js contracts/tests/AmanitaCommerceReputationAdapter.test.js
npx hardhat test --grep "AmanitaCheckout|AmanitaCommerceReputationAdapter|refund|anchor|voluntary"
npx hardhat test
```

---

## 8. Recommendation / Framing

AMN-2.4 стоит вести как **qualification hardening** task, а не как greenfield tests task:

- уже существующие suite должны считаться базой;
- новые тесты добавлять только на реально оставшиеся invariants;
- главный remaining emphasis после последних изменений:
  - cancel/refund edge cases,
  - event semantics,
  - non-interaction reputation on cancelled flows.

---

## 9. Checkpoint

- **Сделано:** qualification gaps закрыты через расширение трёх существующих suite; acceptance-verification создан; тесты прогнаны.
- **Осталось:** финальная приёмка и, при желании оператора, перевод строки AMN-2.4 в `Done`.
- **Требует согласования:** нет архитектурных блокеров.
- **Жду фидбек:** подтвердить acceptance или попросить добить дополнительные deep-edge tests.
