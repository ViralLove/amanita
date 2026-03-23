## Task: implement — AMN-2.2 composite checkout funding (AmanitaCoin + LoveCoin + external) and attestation-gated Paid

---
**Приоритет:** P0  
**Сложность:** M–L  
**Оценка времени:** 1.5–2 дня  
**Зависимости:**  
- `subtask-1-checkout-order-lifecycle-and-roles.md`  
- `../task-validate-amanita-token-loyalty-model/subtask-2-seller-emission-and-debt-ledger.md`  
**Блокирует:**  
- `../task-implement-voluntary-payment-signals-commerce-reputation/task-implement-voluntary-payment-signals-commerce-reputation.md` (**AMN-2.6** — репутация и UX-надстройки **над** каноничными событиями AMN-2.2; см. раздел «Граница с AMN-2.6»)  
**Тэги:** amanita, checkout, composite-payment, attestation, debt, lovecoin, architecture  
**Статус:** Implemented (Waiting Acceptance)  
---

## 1. Цель (Purpose)

Реализовать в **AmanitaCheckout** поддержку заказа, оплачиваемого **совокупностью** (любое непустое подмножество, вплоть до всех трёх одновременно):

1. **AmanitaCoin** — on-chain capture в контур протокола; **единственный** рельс, дающий право на **order-based погашение `sellerDebt`** (редемпшн по правилам AMN-2).  
2. **LoveCoin** — on-chain capture в тот же заказ; **без** участия в `sellerDebt` (как согласовано ранее).  
3. **Внешняя оплата** (фиат / PSP / иное вне on-chain контракта протокола) — **не верифицируется** протоколом; учитывается только как часть **осознанной** модели «заказ полностью оплачен» через attestation (см. ниже).

**Ключевое продуктовое правило (run-analysis):**

- Перевод **только** AmanitaCoin и/или LoveCoin on-chain **не** означает и **не** должен автоматически переводить заказ в статус **`Paid`**, потому что:
  - может существовать **незакрытый внешний** след заказа;
  - даже при отсутствии внешнего следа суммарное on-chain покрытие **не** должно подменять **смысловое** согласие сторон о полной оплате (в т.ч. из-за разных номиналов/интерпретаций Love vs цены заказа без отдельного FX-оракула в MVP).

**Факт «заказ оплачен на 100%»** в протоколе фиксируется **только** как **осознанный сигнал покупателя** («заявляю полную оплату по всем согласованным рельсам») и последующее **принятие продавцом** («согласен, считаю заказ полностью оплаченным»). Только после этой пары допускается переход в **`Paid`** (или эквивалентный финальный статус «полная оплата подтверждена сторонами» — имя статуса зафиксировать в реализации; допустимо оставить имя `Paid` при обновлённой семантике в NatSpec/UI).

**AMN-2.6** не дублирует этот жизненный цикл: там — **репутация**, напоминания, привязка к «получен заказ», анти-абьюз-метрики поверх тех же событий.

**Вне scope AMN-2.2:**

- Оракулы курса LoveCoin↔номинал заказа, автоматическая проверка «арифметически 100%» по смешанным рельсам (если не принято явно в отдельном ADR).  
- Арбитраж споров.  
- Полная спецификация репутационных формул и UX reminders — **AMN-2.6**.

---

## 2. Модель данных и семантика (Solution Architecture)

### 2.1 Три рельса оплаты

| Рельс | Что фиксирует протокол on-chain | Участие в `sellerDebt` |
|--------|-----------------------------------|-------------------------|
| AmanitaCoin | Монотонно растущий **накопленный** capture по `orderHash` | Да: инкрементальный repayment по правилам AMN-2 / `AmanitaToken` |
| LoveCoin | Монотонно растущий capture по `orderHash` | Нет |
| Внешняя | Ничего (нет суммы/PSP on-chain) | Нет |

До создания заказа рельсы не применимы. После создания каждый из трёх рельсов может быть **не задействован** до факта оплаты; допустимы **любые непустые подмножества** используемых рельсов, включая ситуацию, когда **одновременно** участвуют AmanitaCoin, LoveCoin и внешняя оплата.

### 2.2 Номинал заказа `order.amount`

- `order.amount` остаётся **единым** полем «цена/сумма заказа» в **канонических единицах учёта заказа** (для MVP зафиксировать в реализации: например наименьшие единицы **AmanitaCoin**, если заказ номинирован в Amanita).  
- **LoveCoin** накапливается в **собственных единицах токена** (отдельный счётчик `capturedLoveRaw`); протокол **не** утверждает эквивалент Love к `order.amount` без отдельной политики (вынести в ADR при необходимости).  
- Смысл «100% оплачено» **не** выводится протоколом автоматически из `capturedAmanita + FX(Love)`; он задаётся **attestation** buyer→seller.

### 2.3 On-chain partial funding vs статус `Paid`

- Пока заказ не отменён и не переведён в `Paid`, разрешены многократные вызовы capture **AmanitaCoin** / **LoveCoin** (с инвариантами ниже).  
- Статус **`Paid`**: **только** после `buyerDeclareFullPayment(orderHash)` + `sellerAcceptFullPayment(orderHash)` (имена методов — итоговые в коде; суть фиксирована).  
- Опционально ввести промежуточный статус или **view-only** «накоплено по рельсам» без нового терминального статуса — по усмотрению ревью, главное — **не** ставить `Paid` от одного лишь on-chain capture.

### 2.4 Инварианты capture (P0)

- [ ] `capturedAmanitaCumulative <= order.amount` (если `amount` в единицах AmanitaCoin).  
- [ ] `capturedLoveCumulative` монотонно неубывающий; верхняя граница — по политике (если нет отдельного `maxLove` в заказе, задокументировать «без жёсткого cap в v1» или ввести optional cap в struct — решение в PR + NatSpec).  
- [ ] Повторное применение одного и того же **debt repayment** к одному и тому же on-chain объёму Amanita — запрещено (sub-ledger по `orderHash` / used-amount для redemption).

### 2.5 `CHECKOUT_WRITER_ROLE` и `markOrderPaid`

- Текущий `markOrderPaid` (writer) **противоречит** новой семантике для **каноничных** commerce-заказов.  
- **Требование:** для заказов в новом режиме writer-вызов **не** может перевести в `Paid` без attestation **или** метод помечен deprecated / ограничен **только** admin-emergency с явным NatSpec «не для пользовательского UX оплаты». Конкретный вариант выбрать в PR; в таске — **запрет** использовать writer-paid как обычный путь «оплачено».

### 2.6 Граница с AMN-2.6

| Зона | AMN-2.2 | AMN-2.6 |
|------|---------|---------|
| Каноничные события «полная оплата заявлена покупателем» / «принято продавцом» | Да | Потребляет для метрик |
| Репутационные проценты, «получен заказ», reminders, анти-абьюз копирайт | Нет | Да |
| Дополнительные слабые сигналы (например только внешний follow-up) | При необходимости расширить событиями **другим именем**, не `OrderPaid` | Спецификация |

---

## 3. Факты из кода (Code Facts / SSOT)

1. `AmanitaCheckout` — реестр заказа; `orderHash` из `chainid`, контракта, buyer, seller, amount, `referenceId`; статусы включают `Paid` / `Settled`:

```62:80:contracts/AmanitaCheckout.sol
        orderHash = keccak256(
            abi.encodePacked(block.chainid, address(this), msg.sender, seller, amount, referenceId)
        );
        require(_orders[orderHash].status == OrderStatus.None, "AmanitaCheckout: order exists");

        _orders[orderHash] = Order({
            buyer: msg.sender,
            seller: seller,
            amount: amount,
            referenceId: referenceId,
            status: OrderStatus.Created,
            createdAt: uint64(block.timestamp),
            paidAt: 0,
            settledAt: 0,
            cancelledAt: 0
        });

        emit OrderCreated(orderHash, msg.sender, seller, amount, referenceId);
```

2. Сейчас `markOrderPaid` переводит в `Paid` без учёта композитных рельсов и attestation — **subject to change** per §2.5:

```82:88:contracts/AmanitaCheckout.sol
    function markOrderPaid(bytes32 orderHash) external onlyRole(CHECKOUT_WRITER_ROLE) {
        Order storage order = _getOrder(orderHash);
        require(order.status == OrderStatus.Created, "AmanitaCheckout: invalid transition to paid");

        order.status = OrderStatus.Paid;
        order.paidAt = uint64(block.timestamp);
        emit OrderPaid(orderHash, msg.sender, order.paidAt);
```

3. `AmanitaToken` — `sellerDebt`; repayment только от каноничного AmanitaCoin-capture по заказу.

4. Order-aware redemption / накопители по рельсам в текущем коде **отсутствуют** — gap этого сабтаска.

---

## 4. Gap / Проблема

- Нет учёта **частичных** взносов по нескольким рельсам в одном `orderHash`.  
- Нет разделения: **on-chain funding evidence** vs **статус полной оплаты** (`Paid`).  
- Риск иллюзии: пользователь видит `Paid` после одного Love-transfer, хотя внешняя часть не закрыта.  
- Нужна согласованность с **AMN-2.6**: события attestation должны быть стабильны для индексера.

---

## 5. AC/DoD

### Композитное пополнение и долг

- [x] (P0) Реализованы отдельные накопители по заказу: **AmanitaCoin** и **LoveCoin** (cumulative); события при каждом increment capture с указанием рельса и `orderHash`.  
- [x] (P0) **AmanitaCoin**: при каждом допустимом capture вызывается узкая интеграция с `AmanitaToken` для **инкрементального** repayment в пределах `sellerDebt` и без double-count (один вызов `applyOrderDebtRepayment` на инкремент capture).  
- [x] (P0) **LoveCoin**: capture **не** вызывает debt API; не эмитить события, имплицирующие redemption.  
- [x] (P0) **Внешняя** часть заказа: **не** хранить PSP/валюту/сумму; учитывается только через пару attestation (ниже).  
- [x] (P0) Переход в **`Paid`** **только** после последовательности: покупатель `declareFullPayment` → продавец `acceptFullPayment` (оба только соответствующие роли `msg.sender == order.buyer` / `order.seller`); до этого **запрещено** выставлять `Paid` только на основании on-chain capture Amanita/Love.  
- [x] (P0) До `Paid` заказ остаётся в статусе, совместимом с `Created` (или введён явный подстатус **только если** нужен для читаемости; минимум — остаться в `Created` с view накопителей).  
- [x] (P0) После `Paid` — прежняя логика перехода к `Settled` (writer) или согласованное обновление в том же PR.  
- [x] (P0) События attestation **именовать отлично** от `OrderOnChainFunded` / redemption events (например `OrderFullPaymentDeclared`, `OrderFullPaymentAccepted`).  
- [x] (P1) Политика `markOrderPaid`: emergency-only или удалён из публичного UX-пути; задокументировано в NatSpec.  
- [x] (P1) Отмена: если заказ отменён до `Paid`, capture дальше revert; **refund** при cancel вынесен в **AMN-2.7** и закрыт реализацией [`task-implement-amanita-checkout-cancel-refund`](../task-implement-amanita-checkout-cancel-refund/task-implement-amanita-checkout-cancel-refund.md) + `acceptance-verification-amn-2-7.md`.

### Тесты

- [x] (P0) Сценарии: только AMN; только Love; AMN+Love; AMN+внешняя (внешняя симулируется только attestation без токена); все три рельса; убедиться, что **ни один** сценарий не ставит `Paid` без пары attestation.  
- [x] (P0) Негатив: seller не может declare за buyer; buyer не может accept за seller; double `Paid`; capture после `Paid` / после cancel.  
- [x] (P0) Debt: partial AMN captures уменьшают debt корректно; duplicate repayment revert.  
- [x] (P1) Love capture не меняет `sellerDebt`.

### Документация

- [x] (P0) NatSpec/UI-копирайт: «Протокол не подтверждает внешнюю оплату; `Paid` — согласие сторон, а не proof-of-funds».  
- [x] (P1) Родительский таск AMN-2 + bullrun строка AMN-2.2 синхронизированы.

---

## 6. Где менять код

- `contracts/AmanitaCheckout.sol` (struct Order, captures, attestation, статусы)  
- `contracts/AmanitaToken.sol` (repayment hook по инкрементам AMN per order)  
- `contracts/tests/*checkout*.test.js` или новый suite composite + attestation  

---

## 7. План выполнения

1. Расширить `Order` накопителями + флаги/таймстемпы attestation (минимальный набор полей).  
2. Реализовать `captureAmanitaCoin` / `captureLoveCoin` (или единый метод с enum рельса) с инвариантами.  
3. Реализовать инкрементальный debt apply для AMN с защитой от дублей.  
4. Реализовать `declareFullPayment` / `acceptFullPayment` и переход в `Paid` **только** через них для нового потока.  
5. Урезать/обозначить `markOrderPaid` (writer).  
6. Тесты + обновление родительского таска и bullrun (делегировать частично AMN-2.5 при необходимости).

---

## 8. Команды проверки

```bash
cd contracts
npx hardhat compile
npx hardhat test --grep "checkout|composite|capture|full payment|attestation|debt repayment|LoveCoin|AmanitaCoin"
```

---

## 9. Связанные решения (чекпоинт)

| ID | Решение |
|----|--------|
| 8.1 | LoveCoin не участвует в `sellerDebt`. |
| 8.2 | Репутация и reminders — **AMN-2.6**; каноничные attestation-события полной оплаты — **AMN-2.2**. |
| 8.3 | Временное давление на оплату — не в контракте; UX — AMN-2.6. |
| **NEW** | **Совокупная оплата:** до **трёх** рельсов; **Paid** только buyer declare + seller accept; on-chain AMN/Love = доказуемые **частичные** взносы, не «заказ оплачен целиком». |

---

## 10. Реализация (Execution Log)

1. **`contracts/AmanitaToken.sol`:** `amanitaCheckout`, `setAmanitaCheckout`, `applyOrderDebtRepayment` (burn + уменьшение `sellerDebt` на min(gross, debt)), событие `SellerOrderDebtRepaid`.
2. **`contracts/AmanitaCheckout.sol`:** конструктор `(admin, amanitaToken, loveCoin)`; `captureAmanitaCoin` / `captureLoveCoin`; блокировка capture после `declareFullPayment` (`funding locked after declare`); `declareFullPayment` / `acceptFullPayment` → `Paid` + `OrderFullPaymentDeclared` / `OrderFullPaymentAccepted`; `markOrderPaid` только `DEFAULT_ADMIN_ROLE` + `OrderPaidEmergency`; `ReentrancyGuard` на внешних вызовах.
3. **`contracts/mocks/MockERC20.sol`:** LoveCoin stand-in для тестов.
4. **Тесты:** `AmanitaCheckout.lifecycle.test.js` (обновлён деплой), `AmanitaCheckout.composite.test.js` (композит + debt).
5. **Верификация:** `npx hardhat test` — **669 passing** (корень репозитория); таргетные suite: lifecycle 12 + composite 7 + seller-gating 23.
6. **Acceptance:** `acceptance-verification-amn-2-2.md` в папке таска.
