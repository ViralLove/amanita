# AMN-2.6 — acceptance verification (voluntary payment signals)

## Команды

```bash
npx hardhat compile
npx hardhat test contracts/tests/AmanitaCommerceReputationAdapter.test.js contracts/tests/AmanitaCheckout.voluntary-signals.test.js
npx hardhat test   # полный набор (ожидается зелёный)
```

## Проверки (ручная сверка с AC)

| AC | Как проверено |
|----|----------------|
| Не дублировать declare/accept для `Paid` | `Paid` по-прежнему только AMN-2.2 путь + emergency admin; AMN-2.6 добавляет отдельные вызовы/события. |
| Слабые сигналы — отдельные события | `OrderReceivedByBuyer`, `WeakExternalPaymentClaimed`; не переиспользуют семантику `OrderPaid`. |
| «Получен заказ» on-chain | `confirmOrderReceived` при `Paid`; `receivedByBuyerAt` в storage; хук при settle с `buyerConfirmedReceivedBeforeSettle`. |
| Buyer-метрика без declare только после «получено» | `settledReceivedMissingDeclareCount` инкрементируется только если `buyerConfirmedReceivedBeforeSettle && !buyerDeclaredFullPayment`. |
| Seller: доля без accept среди declare+settle | `sellerSettledWithBuyerDeclareCount` / `sellerSettledWithoutSellerAcceptCount`; view `getSellerUnsettledAfterDeclareBps`. |
| Без PSP/фиата в state | Новые поля только временные метки и bool-флаги сигналов. |
| Тесты | `AmanitaCommerceReputationAdapter.test.js` (AMN-2.6 блок), `AmanitaCheckout.voluntary-signals.test.js`. |

## Результат последнего прогона (локально)

- Full suite: **684 passing** (после внедрения AMN-2.6).
