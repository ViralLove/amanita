# AMN-2.7 — acceptance verification (checkout cancel + refund)

## Команды

```bash
npx hardhat compile
npx hardhat test contracts/tests/AmanitaCheckout.lifecycle.test.js contracts/tests/AmanitaCheckout.composite.test.js
npx hardhat test
```

## Проверки (AC/DoD)

| AC | Проверка |
|----|----------|
| Love refund при cancel | `AmanitaCheckout._refundOnCancel` переводит `capturedLove` buyer и обнуляет `capturedLove`; тест `AMN-2.7: cancelOwnOrder auto-refunds Love escrow to buyer`. |
| Политика AMN при cancel | В `AmanitaToken` введены `orderDebtRepaid`, `restoreOrderDebtOnCancel` (only checkout, one-shot) и `refundBuyerOnOrderCancel` (mint-back buyer one-shot); checkout вызывает restore + buyer refund при cancel. |
| Reentrancy / double refund | `cancelOrder` и `cancelOwnOrder` с `nonReentrant`; повторный cancel невозможен из-за статуса `Cancelled`; restore one-shot (`orderDebtRepaid -> 0`). |
| События для индексера | Добавлены `OrderRefunded(orderHash, buyer, rail, amount)` и `BuyerOrderAmnRefunded(orderHash, buyer, amount)` в checkout + `BuyerOrderAmnRefunded` в token; для AMN rail `OrderRefunded.amount` = buyer payout amount (`capturedAmanita`). |
| Матрица тестов cancel/refund | Покрыты сценарии: only Love, only AMN, mixed AMN+Love, cancel после `declareFullPayment`, запрет buyer self-cancel после declare. |

## Последняя верификация

- Target suites: зелёные.
- Full suite: **688 passing**.
