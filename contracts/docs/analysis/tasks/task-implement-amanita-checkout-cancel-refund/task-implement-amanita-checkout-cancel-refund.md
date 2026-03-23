## Task: implement — AmanitaCheckout order cancel with on-chain refund policy

---
**Приоритет:** P1  
**Сложность:** M  
**Оценка времени:** 0.5–1 день  
**Зависимости:**  
- `task-implement-amanita-checkout-escrow-redemption/subtask-2-payment-routing-and-redemption-apply.md` (**AMN-2.2** — текущий capture / debt / cancel без refund)  
**Тэги:** amanita, checkout, cancel, refund, escrow, debt-ledger  
**Статус:** implemented (ожидает финальной приёмки оператора)  
**Ключ bullrun:** AMN-2.7  
---

### Цель

Закрыть **экономический и UX-разрыв** после **AMN-2.2**: при отмене заказа (`Cancelled`) on-chain средства, уже вовлечённые в заказ, **не возвращаются** автоматически:

- **LoveCoin** остаётся на балансе `AmanitaCheckout` (escrow), покупатель не получает его обратно при `cancelOwnOrder` / `cancelOrder`.
- **AmanitaCoin** при `captureAmanitaCoin` переводится на `AmanitaToken`, **сжигается** и уменьшает `sellerDebt`; при отмене заказа **нет** обратного движения токенов и **нет** политики восстановления долга продавца.

Нужно **специфицировать и реализовать** согласованную политику **cancel + refund** (кто инициирует, какие роли, порядок вызовов, влияние на `sellerDebt`), плюс **события** для индексеров и тесты.

### Почему это важно (риск)

- Пользователи теряют **Love** и **AMN** при отмене после частичного funding — репутационный и правовой риск «протокол удерживает средства без механики возврата».
- Несогласованность **debt ledger** и фактической отмены сделки (долг уже уменьшен burn-ом).

### Вне scope (явно)

- Арбитраж споров buyer/seller вне сценария «отмена заказа по правилам контракта».
- Возврат **внешних** (фиат) платежей — вне on-chain.
- Изменение семантики **attestation-gated `Paid`** (остаётся как в AMN-2.2).

---

### Факты из кода (Code Facts / SSOT)

1) **AmanitaCoin capture** — перевод на `AmanitaToken` и немедленный вызов погашения долга (burn + `sellerDebt`):

```135:147:contracts/AmanitaCheckout.sol
    function captureAmanitaCoin(bytes32 orderHash, uint256 amount) external nonReentrant {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for capture");
        require(!order.buyerDeclaredFullPayment, "AmanitaCheckout: funding locked after declare");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(amount > 0, "AmanitaCheckout: invalid capture amount");
        require(order.capturedAmanita + amount <= order.amount, "AmanitaCheckout: amanita exceeds order amount");

        order.capturedAmanita += amount;
        amanitaCoin.safeTransferFrom(msg.sender, address(amanitaToken), amount);
        amanitaToken.applyOrderDebtRepayment(order.seller, orderHash, amount);

        emit OrderOnChainFunded(orderHash, FundingRail.AmanitaCoin, amount, order.capturedAmanita);
    }
```

2) **LoveCoin capture** — токены остаются на `AmanitaCheckout`:

```153:163:contracts/AmanitaCheckout.sol
    function captureLoveCoin(bytes32 orderHash, uint256 amount) external nonReentrant {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid status for capture");
        require(!order.buyerDeclaredFullPayment, "AmanitaCheckout: funding locked after declare");
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer");
        require(amount > 0, "AmanitaCheckout: invalid capture amount");

        order.capturedLove += amount;
        loveCoin.safeTransferFrom(msg.sender, address(this), amount);

        emit OrderOnChainFunded(orderHash, FundingRail.LoveCoin, amount, order.capturedLove);
    }
```

3) **Отмена** — только смена статуса, **без** `safeTransfer` refund:

```220:239:contracts/AmanitaCheckout.sol
    function cancelOrder(bytes32 orderHash) external onlyRole(CHECKOUT_WRITER_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(
            order.status == OrderStatus.Created || order.status == OrderStatus.Paid,
            "AmanitaCheckout: invalid transition to cancelled"
        );

        order.status = OrderStatus.Cancelled;
        order.cancelledAt = uint64(block.timestamp);
        emit OrderCancelled(orderHash, msg.sender, order.cancelledAt);
    }

    function cancelOwnOrder(bytes32 orderHash) external {
        Order storage order = _getOrder(orderHash);
        require(msg.sender == order.buyer, "AmanitaCheckout: only buyer can self-cancel");
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid self-cancel status");

        order.status = OrderStatus.Cancelled;
        order.cancelledAt = uint64(block.timestamp);
        emit OrderCancelled(orderHash, msg.sender, order.cancelledAt);
    }
```

4) **`applyOrderDebtRepayment`** — burn и уменьшение `sellerDebt` без обратного API:

```78:91:contracts/AmanitaToken.sol
    function applyOrderDebtRepayment(address seller, bytes32 orderHash, uint256 grossAmount) external {
        require(msg.sender == amanitaCheckout, "AmanitaToken: only checkout");
        require(amanitaCheckout != address(0), "AmanitaToken: checkout not set");
        require(seller != address(0), "AmanitaToken: invalid seller");
        require(grossAmount > 0, "AmanitaToken: amount");
        require(balanceOf(address(this)) >= grossAmount, "AmanitaToken: insufficient AMN received");

        uint256 debt = sellerDebt[seller];
        uint256 repay = grossAmount <= debt ? grossAmount : debt;
        unchecked {
            sellerDebt[seller] = debt - repay;
        }
        _burn(address(this), grossAmount);
        emit SellerOrderDebtRepaid(seller, orderHash, grossAmount, repay, sellerDebt[seller]);
    }
```

---

### Gap / Проблема

- Нет **атомарной** или **явной** процедуры возврата **LoveCoin** покупателю при `Cancelled`.
- Нет политики по **AmanitaCoin**: либо признать burn необратимым при cancel (и зафиксировать в NatSpec), либо ввести **восстановление `sellerDebt`** / иной механизм компенсации (требует нового доверенного вызова в `AmanitaToken` и аудита инвариантов emission caps).
- Риск **double refund** при повторном вызове, если refund вынесен в отдельную функцию без `nonReentrant` / флагов.

---

### Решение (архитектура — зафиксировать в PR до кода)

**Ветвь A (рекомендуемый MVP-minimum):**

- При переходе в `Cancelled` из состояния, где `capturedLove > 0`: **автоматически** вернуть `capturedLove` на `order.buyer` (в том же tx, если cancel и refund объединены, или одним последующим вызовом `claimRefundAfterCancel` — выбрать один паттерн).
- **AmanitaCoin:** зафиксировать продуктово: при cancel **возврат покупателю невозможен** (уже сожжено); опционально **P1** — увеличить `sellerDebt` обратно на величину `debtRepaid`, зафиксированную по заказу (нужен **учёт per-order repaid** в `AmanitaToken` или событийный replay — явно описать в реализации).

**Ветвь B (более тяжёлая):**

- Отложить burn до `Paid`/`Settled` (меняет AMN-2.2 — только если принято на уровне протокола отдельным ADR).

В таске **обязательно** выбрать ветку в **Decision record** внизу файла при старте реализации.

---

### AC/DoD

- [x] (P0) Документирована и реализована политика **LoveCoin** при `Cancelled`: покупатель получает обратно **ровно** накопленный `capturedLove` в том же tx cancel.
- [x] (P0) Документирована политика **AmanitaCoin** при cancel: выбран вариант восстановления `sellerDebt` по реально репейднутому per-order значению (`orderDebtRepaid`), без возврата AMN токенов покупателю.
- [x] (P0) Защита от **reentrancy** и **повторного** refund на один `orderHash` (cancel функции `nonReentrant`; статус блокирует повторный cancel; `restoreOrderDebtOnCancel` one-shot).
- [x] (P0) События: `OrderRefunded(orderHash, buyer, rail, amount)` по обоим рельсам (`LoveCoin` transfer, `AmanitaCoin` debt-restore amount).
- [x] (P0) Тесты: cancel после только Love; cancel после только AMN; cancel после AMN+Love; после `declareFullPayment`; негативы self-cancel после declare.
- [x] (P1) Согласовано с **AMN-2.6**: refund не меняет семантику attestation/репутационных сигналов, трактуется как cancel-компенсация.

---

### Где менять код

- `contracts/AmanitaCheckout.sol` — hook refund при `cancelOrder` / `cancelOwnOrder` или отдельный `refundCancelledOrder(orderHash)`.
- `contracts/AmanitaToken.sol` — при выборе ветки восстановления debt: новый ограниченный API только от `amanitaCheckout` + события.
- `contracts/tests/AmanitaCheckout.*.test.js` — новые кейсы cancel/refund.

---

### План выполнения

1. Зафиксировать **Decision record** (ветка A/B, поведение AMN при cancel).  
2. Спроектировать порядок: cancel → internal `_refundIfCancelled` vs отдельный user-facing шаг.  
3. Реализовать Love refund + события.  
4. Реализовать выбранную политику AMN (NatSpec-only или debt restore).  
5. Тесты + `acceptance-verification-amn-2-7.md` + обновление bullrun статуса.

### Execution log (2026-03-16)

1. Decision record зафиксирован с оператором: Love=auto-on-cancel, AMN=restore sellerDebt, cancel после declare=только writer/admin.  
2. Реализация `AmanitaCheckout`: `cancelOrder`/`cancelOwnOrder` стали `nonReentrant`, добавлен internal `_refundOnCancel`, событие `OrderRefunded`.  
3. Реализация `AmanitaToken`: `orderDebtRepaid[orderHash]`, `restoreOrderDebtOnCancel`, событие `SellerOrderDebtRestoredOnCancel`.  
4. Тесты: расширены `AmanitaCheckout.composite.test.js` и `AmanitaCheckout.lifecycle.test.js`.  
5. Верификация: targeted suites зелёные; полный прогон `npx hardhat test` — **687 passing**.

---

### Команды проверки

```bash
cd /path/to/repo
npx hardhat compile
npx hardhat test --grep "checkout|cancel|refund"
npx hardhat test
```

---

### Риски / подводные камни

- Восстановление `sellerDebt` без строгого учёта по `orderHash` → двойной сдвиг ledger.  
- `cancelOrder` в статусе `Paid` при уже прошедшем settle-пути — уточнить матрицу (сейчас writer может cancel из `Paid`).

---

### Связь с AMN-2.2

Открытый пункт **P1** в `subtask-2-payment-routing-and-redemption-apply.md` (refund при cancel) **переносится сюда**; после выполнения AMN-2.7 отметить cross-link в subtask-2 как closed.

---

### Decision record (заполнить при старте реализации)

| Поле | Выбор |
|------|--------|
| Love refund | **Авто при cancel** (в том же tx) |
| AMN при cancel | **Restore `sellerDebt` by `orderDebtRepaid[orderHash]`** (one-shot) |
| Cancel после `declareFullPayment` | **Только writer/admin**; buyer self-cancel блокируется |
