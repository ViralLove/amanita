## Task: analyze — buyer AMN credit refund policy on order cancel

---
**Приоритет:** P1  
**Сложность:** M  
**Оценка времени:** 0.5 дня (analysis + decision record)  
**Зависимости:**  
- `task-implement-amanita-checkout-cancel-refund/task-implement-amanita-checkout-cancel-refund.md` (AMN-2.7)  
- `task-implement-amanita-checkout-escrow-redemption/subtask-2-payment-routing-and-redemption-apply.md` (AMN-2.2)  
**Тэги:** amanita, checkout, cancel, refund, tokenomics, debt-ledger  
**Статус:** implemented (decision gate approved; ready for final acceptance)  
**Ключ bullrun:** AMN-2.8  
---

### Цель

Принять архитектурное решение по возврату **AMN-ценности покупателю** при cancel заказа, где уже был `captureAmanitaCoin` и burn в `AmanitaToken`.

Требуемый результат:
- зафиксированная политика (ADR-уровня) для buyer-refund по AMN;
- согласование с текущим debt-ledger и анти-абьюз инвариантами;
- рекомендация для реализации в следующем run-task без двусмысленности.

### Почему это важно (риск)

- В текущем AMN-2.7 восстановление есть только в `sellerDebt` (bookkeeping), но нет token refund в кошелёк buyer.
- Это создаёт UX/доверительный gap: buyer видит cancel, но не видит возврат AMN-ценности.
- Неправильная реализация mint-back может сломать supply/double-refund инварианты.

### Вне scope (явно)

- Полная смена архитектуры AMN-2.2 (deferred burn до `Paid`/`Settled`).
- Рефактор репутационного слоя AMN-2.6.
- Off-chain фиат/PSP возвраты.

---

### Факты из кода (Code Facts / SSOT)

1) `captureAmanitaCoin` сразу переводит AMN в `AmanitaToken` и вызывает burn+repay:

```166:177:contracts/AmanitaCheckout.sol
    function captureAmanitaCoin(bytes32 orderHash, uint256 amount) external nonReentrant {
        // ...
        order.capturedAmanita += amount;
        amanitaCoin.safeTransferFrom(msg.sender, address(amanitaToken), amount);
        amanitaToken.applyOrderDebtRepayment(order.seller, orderHash, amount);
    }
```

2) В `AmanitaToken.applyOrderDebtRepayment` происходит burn и уменьшение `sellerDebt`; учёт `orderDebtRepaid` уже есть:

```86:103:contracts/AmanitaToken.sol
    function applyOrderDebtRepayment(address seller, bytes32 orderHash, uint256 grossAmount) external {
        // ...
        uint256 repay = grossAmount <= debt ? grossAmount : debt;
        unchecked { sellerDebt[seller] = debt - repay; }
        if (repay > 0) { orderDebtRepaid[orderHash] += repay; }
        _burn(address(this), grossAmount);
        emit SellerOrderDebtRepaid(seller, orderHash, grossAmount, repay, sellerDebt[seller]);
    }
```

3) В AMN-2.7 cancel уже восстанавливает `sellerDebt`, но buyer token refund по AMN отсутствует:

```334:342:contracts/AmanitaCheckout.sol
    function _refundOnCancel(bytes32 orderHash, Order storage order) internal {
        if (order.capturedAmanita > 0) {
            uint256 restoredDebt = 0;
            if (amanitaToken.orderDebtRepaid(orderHash) > 0) {
                restoredDebt = amanitaToken.restoreOrderDebtOnCancel(order.seller, orderHash);
            }
            order.capturedAmanita = 0;
            emit OrderRefunded(orderHash, order.buyer, FundingRail.AmanitaCoin, restoredDebt);
        }
    }
```

---

### Gap / Проблема

- Нет прямого on-chain механизма вернуть AMN-покупателю как токен/кредит при cancel.
- `OrderRefunded(..., AmanitaCoin, amount)` сейчас отражает **restore debt amount**, а не buyer token payout.
- Требуется выбрать модель возврата, которая не открывает double-mint/double-refund path.

---

### Решение (варианты для сравнения)

1) **Mint-back buyer (рекомендуемый кандидат)**  
   Новый restricted API в `AmanitaToken`, callable only by checkout, one-shot by `orderHash`.

2) **Internal buyer credit в checkout**  
   Без mint в кошелёк, но с зачётом в следующих заказах.

3) **Deferred burn (post-MVP)**  
   Перенос burn из capture в `Paid/Settled`; самый чистый с точки зрения refund, но high-impact.

### Сравнительная матрица (результат анализа)

| Вариант | UX для buyer | Security риск | Влияние на AMN-2.2/2.7 | Сложность внедрения | Итог |
|---|---|---|---|---|---|
| Mint-back buyer | Максимально понятный: buyer получает AMN обратно в кошелёк | Средний: нужен строгий one-shot и защита от double-mint | Низко-среднее: точечный апдейт `AmanitaToken` + `AmanitaCheckout` | M | **Рекомендуется для MVP-next** |
| Internal buyer credit | Средний: «кредит в системе», но не токен в кошельке | Средний: меньше риска по supply, но выше риск логики credit-учёта | Среднее: добавляет новый credit-layer в checkout | M/L | Возможно, но хуже UX и сложнее поддержка |
| Deferred burn | Чистый refund-path | Низкий в целевой архитектуре, но высокий migration risk | Высокое: ломает существующий capture-поток и AMN-2.2 инварианты | L/XL | Post-MVP / отдельный ADR |

### Recommendation (MVP-next)

Выбрать **Mint-back buyer** как продолжение AMN-2.7:

- сохранить текущий `restoreOrderDebtOnCancel` для корректного seller-ledger;
- добавить restricted payout API в `AmanitaToken` (only checkout, one-shot по `orderHash`);
- при cancel выполнять последовательность:
  1. restore debt seller;
  2. mint buyer refund;
  3. обнулить AMN capture поля заказа;
  4. эмитить отдельное событие buyer AMN payout.

Обоснование:
- закрывает UX-gap без полного редизайна AMN-2.2;
- минимально инвазивно к текущему коду;
- сохраняет прозрачный on-chain audit trail.

### Формула суммы refund (предпочтение)

**Рекомендуемая формула:** `buyerAmnRefund = capturedAmanita`.

Почему не `orderDebtRepaid`:
- `orderDebtRepaid` зависит от величины долга seller и может быть меньше capture;
- это приводит к UX-аномалии: buyer внес AMN, cancel произошёл, но вернул не всю внесённую AMN-сумму;
- для бизнес-смысла «cancel отменяет сделку» лучше возврат полного buyer capture по AMN-рельсу.

Ограничение:
- payout only once per `orderHash` после перехода в `Cancelled`.
- payout never after `Settled`.

## 🚦 Decision Gate (Operator Required Before Implementation)

Ниже — три обязательных решения перед реализацией.  
В каждом DG выбрать **ровно один** вариант. После выбора проставить `[x]`.

### DG-1. Что именно возвращаем покупателю по AMN при cancel?

**Вопрос (простыми словами):**  
После cancel покупатель должен получить AMN обратно прямо в кошелёк или только «внутренний зачёт»/ничего?

**Опции:**

- [x] **Вариант A — Mint-back buyer (прямой возврат AMN в кошелёк).**  
  **Что это:** checkout вызывает restricted API в `AmanitaToken`, который минтит buyer сумму refund (one-shot по `orderHash`).  
  **Плюсы:** максимально понятный UX; cancel реально выглядит как «вернули AMN».  
  **Риски:** нужен строгий guard от double-mint; внимательная проверка supply-инвариантов.

- [ ] **Вариант B — Internal buyer credit (внутренний баланс в checkout).**  
  **Что это:** AMN в кошелёк не возвращается, но создаётся кредит для будущих заказов.  
  **Плюсы:** меньше прямого влияния на supply ERC20.  
  **Риски:** сложная логика кредитов и плохой UX («где мои токены?»); больше surface area для багов.

- [ ] **Вариант C — Без buyer refund (только restore sellerDebt, как в текущем AMN-2.7).**  
  **Что это:** покупатель не получает токены обратно, система корректирует только seller debt ledger.  
  **Плюсы:** минимальные изменения.  
  **Риски:** сохраняется исходный UX-gap и продуктовый конфликт ожиданий.

**Рекомендация:** ✅ **Вариант A (Mint-back buyer)** для MVP-next.

---

### DG-2. Какую сумму AMN возвращаем покупателю?

**Вопрос (простыми словами):**  
Если возвращаем AMN buyer, это должна быть полная сумма, которую buyer внёс в AMN-рельс, или только часть, которая реально уменьшила `sellerDebt`?

**Опции:**

- [x] **Вариант A — `capturedAmanita` (полный buyer capture по AMN-рельсу).**  
  **Что это:** refund amount = то, что buyer внёс через `captureAmanitaCoin` по заказу.  
  **Плюсы:** экономически и UX согласовано с идеей cancel («сделка отменена — внесённое возвращено»).  
  **Риски:** требует аккуратного one-shot учёта по order.

- [ ] **Вариант B — `orderDebtRepaid` (только часть, которая пошла в уменьшение долга seller).**  
  **Что это:** refund amount ограничен фактическим debt repayment.  
  **Плюсы:** tight связка с ledger seller.  
  **Риски:** buyer может получить меньше, чем внёс; высокая вероятность недоверия/споров.

- [ ] **Вариант C — Гибрид (`min/max` или policy-driven split).**  
  **Что это:** сложная формула в зависимости от долга/статуса.  
  **Плюсы:** тонкая настройка политики.  
  **Риски:** самый высокий риск ошибок, сложность объяснения и тестирования.

**Рекомендация:** ✅ **Вариант A (`capturedAmanita`)**.

---

### DG-3. Как фиксируем события refund для индексера и аудита?

**Вопрос (простыми словами):**  
Достаточно ли одного `OrderRefunded`, или нужен отдельный event именно для AMN payout buyer?

**Опции:**

- [ ] **Вариант A — Оставить только `OrderRefunded` (расширив его семантику).**  
  **Что это:** один event для всего refund-потока, в т.ч. AMN buyer payout.  
  **Плюсы:** меньше изменений.  
  **Риски:** семантическая перегрузка; тяжелее отличать debt-restore от buyer payout в аналитике.

- [x] **Вариант B — Добавить отдельный `BuyerOrderAmnRefunded` + сохранить `OrderRefunded`.**  
  **Что это:** `OrderRefunded` остаётся rail-агрегатором, новый event — точный сигнал о mint-back buyer.  
  **Плюсы:** максимально прозрачный audit trail и простая индексация.  
  **Риски:** дополнительный event и обновление indexer mapping.

- [ ] **Вариант C — Только `BuyerOrderAmnRefunded`, без `OrderRefunded` для AMN.**  
  **Что это:** разделение событий по типам операций без общего агрегатора для AMN.  
  **Плюсы:** чистая предметная модель по AMN refund.  
  **Риски:** потеря единообразия с Love rail и существующими агрегатами.

**Рекомендация:** ✅ **Вариант B** (отдельный `BuyerOrderAmnRefunded` + сохранить `OrderRefunded`).

---

### Как принять gate

Чтобы открыть implementation subtask, нужно подтвердить:

- [x] **DG-1 выбран (рекомендуется A)**
- [x] **DG-2 выбран (рекомендуется A)**
- [x] **DG-3 выбран (рекомендуется B)**

Если хотя бы один пункт не подтверждён — implementation не стартуем.

Если все 3 пункта согласованы, следующий шаг: открыть implementation subtask и перейти к run-task.

---

### AC/DoD

- [x] (P0) Подготовлена сравнительная матрица вариантов (security, UX, tokenomics, migration impact).
- [x] (P0) Зафиксирована **одна** рекомендуемая стратегия для MVP-next (mint-back buyer).
- [x] (P0) Определена точная формула AMN refund amount: `capturedAmanita`.
- [x] (P0) Определены anti-abuse ограничения: one-shot, статусная матрица (`Created/Paid/Settled/Cancelled`), запрет повторов.
- [x] (P1) Описано влияние на события/indexer (нужен отдельный event для buyer AMN payout).
- [x] (P1) Подготовлен implementation handoff: список файлов и минимальный план патча.

---

### Где менять код (после одобрения решения)

- `contracts/AmanitaToken.sol` — потенциально новый refund API для buyer.
- `contracts/AmanitaCheckout.sol` — вызов buyer-refund в `_refundOnCancel`.
- `contracts/tests/AmanitaCheckout.composite.test.js` — buyer AMN refund happy/negative paths.
- `contracts/tests/AmanitaCheckout.lifecycle.test.js` — статусные ограничения.

---

### План выполнения

1. Зафиксировать текущие инварианты AMN-2.2/2.7 (burn/restore/status).
2. Сравнить 3 варианта по security + product fit.
3. Выбрать рекомендованный вариант и формулу суммы.
4. Сформировать decision gate для оператора (2-3 бинарных решения).
5. После подтверждения — открыть run-task на имплементацию.

### Implementation handoff (после approval)

1. `contracts/AmanitaToken.sol`
   - добавить mapping one-shot payout по `orderHash`;
   - добавить `refundBuyerOnOrderCancel(address buyer, bytes32 orderHash, uint256 amount)` only checkout;
   - добавить событие `BuyerOrderAmnRefunded`.

2. `contracts/AmanitaCheckout.sol`
   - в `_refundOnCancel` после restore debt вызвать buyer payout;
   - переопределить семантику `OrderRefunded(AmanitaCoin, amount)` как buyer payout amount (или оставить для compatibility и добавить отдельный event).

3. Тесты
   - `AmanitaCheckout.composite.test.js`: full AMN buyer payout on cancel, one-shot guard, no payout after settled;
   - `AmanitaCheckout.lifecycle.test.js`: статусная матрица и негативы повторного cancel/refund.

### Статусная матрица (рекомендуемая)

| Статус | writer cancel | buyer self-cancel | buyer AMN payout |
|---|---|---|---|
| Created | да | да (если не declare) | да |
| Paid | да | нет | да (через writer cancel) |
| Settled | нет | нет | нет |
| Cancelled | нет (повтор) | нет (повтор) | нет (one-shot) |

---

### Команды проверки (для следующего implementation task)

```bash
cd /Users/eslinko/Development/Amanita
npx hardhat compile
npx hardhat test --grep "AmanitaCheckout|cancel|refund|composite"
npx hardhat test
```

---

### Риски / подводные камни

- Double-mint при повторном cancel/refund path.
- Несоответствие между событием refund и фактическим payout buyer.
- Конфликт с debt-cap моделью при неверной формуле суммы refund.

---

### Decision record (заполняется в analysis-review)

| Поле | Выбор |
|------|-------|
| Buyer AMN refund model | mint-back / internal credit / deferred burn |
| Refund amount formula | capturedAmanita / orderDebtRepaid / hybrid |
| Event model | расширить `OrderRefunded` / добавить отдельный AMN buyer payout event |
| Cancel statuses for buyer AMN payout | Created only / Created+Paid(writer) |

### Decision gate (ожидается от оператора)

1. Подтвердить модель: `mint-back buyer` (yes/no).  
2. Подтвердить формулу: `capturedAmanita` (yes/no).  
3. Подтвердить event-модель: отдельный `BuyerOrderAmnRefunded` + сохранение `OrderRefunded` для rail-агрегации (yes/no).  

### Checkpoint

- **Сделано:** анализ завершён; operator decision gate подтверждён (`1A / 2A / 3B`); implementation выполнен в коде (`AmanitaToken` + `AmanitaCheckout`) и покрыт тестами.
- **Осталось:** финальная приёмка и перевод статусов в Done по решению оператора.
- **Требует согласования:** нет блокеров для выбранной модели.
- **Жду фидбек:** подтвердить финальный acceptance для закрытия этапа.
