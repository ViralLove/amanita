# AMN-2.4 — acceptance verification (checkout / redemption / reputation qualification)

## Команды

```bash
cd /Users/eslinko/Development/Amanita
npx hardhat compile
npx hardhat test contracts/tests/AmanitaCheckout.lifecycle.test.js contracts/tests/AmanitaCheckout.composite.test.js contracts/tests/AmanitaCommerceReputationAdapter.test.js
npx hardhat test --grep "AmanitaCheckout|AmanitaCommerceReputationAdapter|refund|anchor|voluntary"
npx hardhat test
```

## Проверки (qualification coverage)

| Домен | Что проверено | Где проверено |
|---|---|---|
| `$AMANITA` funding / debt | decrease on capture, over-capture reject, restore `sellerDebt` on cancel, buyer mint-back one-shot refund, no refund after `Settled` | `AmanitaCheckout.composite.test.js` |
| `$LOVE` funding / refund | escrow capture, refund to buyer on cancel, no `sellerDebt` side effects from Love rail | `AmanitaCheckout.composite.test.js` |
| Order lifecycle | duplicate order reject, capture lock after declare, `Paid` only via declare+accept or admin emergency, cancel matrix incl. self-cancel restrictions | `AmanitaCheckout.lifecycle.test.js`, `AmanitaCheckout.composite.test.js` |
| Reputation | live redemption metrics, successful-order metrics only on settle, AMN-2.6 buyer/seller bps views, cancel/refund not counted as successful commerce | `AmanitaCommerceReputationAdapter.test.js` |
| Event semantics | `BuyerOrderAmnRefunded` emitted; AMN rail `OrderRefunded` amount matches buyer refund amount | `AmanitaCheckout.composite.test.js` |

## Добавленные qualification cases в рамках AMN-2.4

- duplicate order hash rejection
- paired AMN refund events consistency
- one-shot direct negative around `orderBuyerRefunded`
- no cancel refund path after `Settled`
- reputation non-interaction on cancel/refund

## Последняя верификация

- Target suites: **38 passing**
- Full suite: **693 passing**
