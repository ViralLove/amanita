## Task: implement — commerce reputation signals, reminders, and profile metrics (post AMN-2.2 attestation)

---
**Приоритет:** P1 (после AMN-2.2: композитный funding + каноничная пара attestation для `Paid`)  
**Сложность:** L  
**Оценка времени:** 2–3 дня (контракты + индексация + спецификация UX-копирайта)  
**Зависимости:**  
- `task-implement-amanita-checkout-escrow-redemption/subtask-2-payment-routing-and-redemption-apply.md` (**AMN-2.2** — каноничный `orderHash`, on-chain capture по рельсам, **пара attestation полной оплаты** buyer→seller для `Paid`; события для индексера)  
**Интеграция (после или параллельно):**  
- `task-implement-amanita-checkout-escrow-redemption/subtask-3-reputation-adapter-hybrid-metrics.md` (**AMN-2.3** — агрегация метрик для SBT/профиля; первая версия адаптера может жить без AMN-2.6, затем подключается voluntary-поток)  
**Тэги:** amanita, checkout, external-payment, attestation, reputation, anti-abuse, ux  
**Статус:** implemented (ожидает финальной приёмки оператора)  
---

### Цель

**Каноничный жизненный цикл «заказ полностью оплачен» (`Paid`)** реализуется в **AMN-2.2**: осознанное **declare** от покупателя + **accept** от продавца, независимо от того, входят ли в заказ AmanitaCoin, LoveCoin и/или внешняя оплата.

**AMN-2.6** добавляет **надстройку** поверх фактов AMN-2.2:

- агрегация **репутационных** метрик профиля (симметрия buyer/seller, анти-абьюз, дисклеймеры);
- **UX reminders** (без штрафных таймеров на оплату) с объяснением ценности сигналов;
- привязка части метрик к событию **«получен заказ»** (канон уточнить в реализации);
- опционально — **дополнительные слабые сигналы** (например промежуточное «отправил внешний платёж»), которые **не** заменяют и **не** дублируют пару declare/accept для `Paid` из AMN-2.2.

Не собирать аналитику «кто чем платит» (PSP, банк, валюта, сумма фиата on-chain).

**Почему это важно (риск):** без явных правил легко получить (а) иллюзию верификации протоколом, (б) дискриминацию забывчивых покупателей, (в) гейминг парой аккаунтов, (г) негативную репутацию продавца из-за ложных сигналов покупателей.

**Вне scope (явно):**
- Реализация **перевода в `Paid`** и on-chain capture AmanitaCoin/LoveCoin — **только** AMN-2.2.
- Арбитраж споров и «истина оплаты» — **не** зона Amanita Protocol.
- Погашение `sellerDebt` — **только** AmanitaCoin, см. AMN-2.2.
- Сбор статистики по способам оплаты, объёмам продаж в фиате, идентификаторам PSP.

---

### Факты из кода (Code Facts / SSOT)

1. `contracts/AmanitaCheckout.sol` — реестр заказа и lifecycle (`Created`, `Paid`, `Settled`, `Cancelled`); `orderHash` как якорь; роли `DEFAULT_ADMIN_ROLE`, `CHECKOUT_WRITER_ROLE`; AMN-2.6: `confirmOrderReceived`, `signalWeakExternalPaymentClaim`, поля `receivedByBuyerAt`, `weakExternalPaymentClaimed`.

```20:37:contracts/AmanitaCheckout.sol
contract AmanitaCheckout is AccessControl, ReentrancyGuard {
    bytes32 public constant CHECKOUT_WRITER_ROLE = keccak256("CHECKOUT_WRITER_ROLE");

    enum OrderStatus {
        None,
        Created,
        Paid,
        Settled,
        Cancelled
    }
```

2. `contracts/AmanitaToken.sol` — ledger `sellerDebt` и смежные счётчики; погашение долга привязано к каноничному loyalty/checkout контурy (AMN-2.2), не к внешним платежам.

3. `contracts/Orders.sol` — legacy registry с `ROUTER_ROLE` и `markAsPaid`; **не** смешивать семантику с новым voluntary-flow без явной миграционной доки (избежать двух «Paid» с разным смыслом).

---

### Gap / Проблема

- После AMN-2.2 остаётся потребность в **профильной репутации** и **UX-надстройках**, не смешивая их с контрактной логикой `Paid`.
- Нужны **симметричные** метрики и защита от абьюза, согласованные с событиями AMN-2.2 (в т.ч. attestation полной оплаты).
- Нужны явные правила привязки к **«получен заказ»** без штрафных таймеров на оплату.

---

### Решение (архитектура и термины)

**Именование активов (UX/docs/events):** **AmanitaCoin**, **LoveCoin** — как источники **on-chain** оплаты через протокол. Отдельно: **внешняя оплата** без указания рельса.

**Три слоя истины (не смешивать в одном событии):**
1. **On-chain funding** — доказуемые переводы AmanitaCoin/LoveCoin в контур checkout (частичные взносы по заказу).
2. **Full-payment attestation (AMN-2.2)** — пара вызовов buyer→seller, фиксирующая **согласие сторон** о полной оплате по всем рельсам; **не** proof-of-funds для внешней части.
3. **Reputation (AMN-2.6)** — агрегаты из (1), (2) и опциональных слабых сигналов; дисклеймеры в UI и NatSpec.

**Временное окно (8.3):**
- **Запрещено:** жёсткие дедлайны, штрафующие за «медленную оплату» или за отсутствие сигнала до произвольного SLA.
- **Разрешено:** привязка eligibility сигналов к **событию «заказ получен покупателем»** (on-chain или подтверждённый off-chain с якорем на `orderHash` — выбрать один канон в реализации; зафиксировать в AC).
- **UX:** напоминания (reminders) с объяснением **ценности для репутации**, без штрафов за пропуск напоминания.

**Метрики (симметрия и анти-абьюз):**

| Метрика | Назначение | Защита от злоупотреблений |
|--------|------------|---------------------------|
| **Согласованная полная оплата (канон AMN-2.2)** | События пары declare/accept, ведущие к `Paid` | В репутации не называть «протокол верифицировал оплату»; вес выше слабых опциональных сигналов, но ниже судебного proof |
| **Покупатель: доля без declare полной оплаты** в релевантных заказах | Дисциплина сигнализации | Считать только после **«получен заказ»**; не учитывать отменённые; копирайт: не «плохой плательщик» |
| **Продавец: доля без accept** среди заказов, где buyer сделал declare и заказ успешно завершён | Стимул не «забывать» accept | Знаменатель **только** с buyer declare; фейк declare без accept не должен автоматически карать продавца |
| **Защита продавца от фейков покупателя** | Ложный declare не должен ломать репутацию продавца | Accept **не обязателен**; метрики продавца — на подмножестве с осмысленным контекстом; опционально нейтральные close-сигналы |

**Гейминг парой аккаунтов:** полностью не устранить без арбитража; в AC — явный trust assumption + ограничение веса «мягких» метрик относительно счётчика **каноничных** пар attestation полной оплаты из AMN-2.2.

---

### AC/DoD

**Интеграция с AMN-2.2 / данные**
- [x] (P0) **Не** дублировать в AMN-2.6 контрактный API пары declare/accept для `Paid` — он живёт в **AMN-2.2** (`AmanitaCheckout` или согласованное расширение).
- [x] (P0) Индексер/адаптер подписан на события AMN-2.2: on-chain funding по рельсам + **attestation полной оплаты** (имена фиксируются в AMN-2.2); путаницы с устаревшим writer-`markOrderPaid` избегать.
- [x] (P0) Любые **дополнительные** опциональные сигналы AMN-2.6 — отдельные события/имена, **не** `OrderPaid` и не замена declare/accept.
- [x] (P0) В state не хранить PSP/валюту/сумму фиата; LoveCoin/debt-инварианты не нарушать (без хуков в AMN-2.6).

**Логика времени и «получение заказа»**
- [x] (P0) Негативные метрики покупателя **не** активируются до наступления канонического события «получен заказ» (**on-chain:** `confirmOrderReceived` → `OrderReceivedByBuyer`; учёт в адаптере на `markOrderSettled` при флаге «подтвердил до settle»).
- [x] (P0) Нет обязательных таймаутов, штрафующих за скорость оплаты или за отсутствие сигнала вне привязки к «получено».

**Репутация**
- [x] (P0) Специфицированы формулы **двух** процентов: (1) покупатель — `getBuyerReceivedWithoutDeclareBps` (знаменатель: `settledReceivedCount` при подтверждённом получении до settle); (2) продавец — `getSellerUnsettledAfterDeclareBps` (знаменатель: settled с `buyerDeclaredFullPayment`; числитель: без `sellerAcceptedFullPayment`).
- [x] (P1) Документированы дисклеймеры: `contracts/docs/commerce-reputation-disclaimers.md`.

**Тесты**
- [x] (P0) Интеграционные тесты: checkout → хуки → агрегаты (`AmanitaCommerceReputationAdapter.test.js`); AMN-2.6 не вызывает debt API.
- [x] (P1) Сценарий declare + emergency `Paid` + settle — seller bps = 10000; без ложного «наказания» продавца вне подмножества с buyer declare.

**Интеграция**
- [x] (P1) Адаптер получает расширенный `notifyOrderSettled` + `notifyWeakExternalPaymentClaim`; view и события `LiveMetricsUpdated` / `BuyerLiveMetricsUpdated`.

---

### Где менять код (планируемо)

- Новый контракт или расширение с явным разделением событий (уточнить при реализации): `contracts/*Checkout*Signals*.sol` или расширение `AmanitaCheckout` **только если** не ломает SSOT семантики `Paid`.
- `contracts/AmanitaCommerceReputationAdapter.sol` (AMN-2.3) — чтение/агрегация.
- Индексер / subgraph spec (если применимо) — отдельный артефакт в таске.
- Тесты: новый suite `*voluntary*signal*.test.js`.
- Доки: disambiguation AmanitaCoin vs LoveCoin vs external attestation; ссылка на bullrun **AMN-2.6**.

---

### План выполнения

1. Зафиксировать канон: событие «получен заказ» (on-chain vs commit). → **On-chain:** `confirmOrderReceived` / `OrderReceivedByBuyer`.
2. Синхронизировать схему событий с **AMN-2.2** (имена declare/accept, funding events). → без изменения имён AMN-2.2.
3. Реализовать опциональные доп. сигналы **отдельно** от пары `Paid` AMN-2.2. → `signalWeakExternalPaymentClaim` / `WeakExternalPaymentClaimed`.
4. Задать формулы метрик и edge cases в doc + адаптер. → bps-views, `commerce-reputation-disclaimers.md`.
5. Тесты P0/P1 + копирайт-гайд для UI. → `AmanitaCheckout.voluntary-signals.test.js`, расширение adapter tests.

### Execution log (2026-03-16)

- Расширены `IAmanitaCommerceReputationHooks`, `AmanitaCommerceReputationAdapter`, `AmanitaCheckout` (см. git diff).
- Добавлены `acceptance-verification-amn-2-6.md`, `contracts/docs/commerce-reputation-disclaimers.md`.
- Обновлён `bullrun-launch-index.md` (строка AMN-2.6).
- `npx hardhat test`: **684 passing**.

---

### Команды проверки

```bash
cd contracts
npx hardhat compile
npx hardhat test --grep "voluntary|external signal|attestation|commerce reputation"
```

---

### Риски / подводные камни

- Смешение семантики `Paid` с attestation — **критично избегать**.
- Негативные метрики без осторожного копирайта воспринимаются как обвинение — только «сигнальная дисциплина».
- Sybil / collusion — ограничить весом и прозрачными disclaimers.

---

### Связь с AMN-2.2

**AMN-2.2** реализует композитный funding (AmanitaCoin + LoveCoin + логически внешняя доля) и **каноничную пару attestation** для перехода в `Paid`. **AMN-2.6** использует эти события для репутации и UX и **не подменяет** жизненный цикл оплаты заказа.
