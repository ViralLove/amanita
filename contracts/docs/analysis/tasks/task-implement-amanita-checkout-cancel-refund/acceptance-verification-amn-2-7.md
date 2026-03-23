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
| Политика AMN при cancel | В `AmanitaToken` введён `orderDebtRepaid` и `restoreOrderDebtOnCancel` (only checkout, one-shot); checkout вызывает restore при cancel. |
| Reentrancy / double refund | `cancelOrder` и `cancelOwnOrder` с `nonReentrant`; повторный cancel невозможен из-за статуса `Cancelled`; restore one-shot (`orderDebtRepaid -> 0`). |
| События для индексера | Добавлен `OrderRefunded(orderHash, buyer, rail, amount)`; `AmanitaCoin` amount = restored debt, `LoveCoin` amount = transfer escrow. |
| Матрица тестов cancel/refund | Покрыты сценарии: only Love, only AMN, mixed AMN+Love, cancel после `declareFullPayment`, запрет buyer self-cancel после declare. |

## Последняя верификация

- Target suites: зелёные.
- Full suite: **687 passing**.
