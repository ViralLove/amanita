# AmanitaCheckout Contract (`AmanitaCheckout.sol`)

## Purpose

`AmanitaCheckout` is the canonical order contract for AMN-2.x commerce flow:

- order lifecycle state machine,
- composite on-chain funding rails,
- explicit payment attestation to reach `Paid`,
- cancel/refund execution,
- reputation hook dispatch.

## Order State Machine

`None -> Created -> Paid -> Settled | Cancelled`

Key rule:

- `Paid` is an attestation state, not an automatic result of capture amounts.

## Funding Rails

### `AmanitaCoin` rail (`captureAmanitaCoin`)

- buyer transfers AMANITA to token contract,
- checkout calls `AmanitaToken.applyOrderDebtRepayment`,
- affects `sellerDebt`,
- emits `OrderOnChainFunded(..., AmanitaCoin, ...)`.

### `LoveCoin` rail (`captureLoveCoin`)

- buyer transfers LOVE to checkout escrow,
- no debt-ledger effect,
- emits `OrderOnChainFunded(..., LoveCoin, ...)`.

## Payment Attestation Flow

### Buyer side

- `declareFullPayment(orderHash)` sets buyer declaration.

### Seller side

- `acceptFullPayment(orderHash)` accepts declaration and transitions order to `Paid`.

### Emergency admin path

- `markOrderPaid(orderHash)` can force `Paid` and emits `OrderPaidEmergency`.

## Settlement and Reputation Hooks

`markOrderSettled(orderHash)`:

- access: `CHECKOUT_WRITER_ROLE`,
- requires current status `Paid`,
- transitions to `Settled`,
- invokes `notifyOrderSettled(...)` in reputation adapter (if configured).

## Cancel and Refund Semantics

### Writer cancel

- `cancelOrder(orderHash)` allowed from `Created` and `Paid`.

### Buyer self-cancel

- `cancelOwnOrder(orderHash)` only in `Created`,
- forbidden after buyer declaration (`self-cancel locked after declare`).

### `_refundOnCancel` behavior

- AMANITA capture path:
  - optional debt restore via `restoreOrderDebtOnCancel`,
  - buyer mint-back via `refundBuyerOnOrderCancel`,
  - emits `BuyerOrderAmnRefunded` and `OrderRefunded(..., AmanitaCoin, ...)`.
- LOVE capture path:
  - escrow transfer back to buyer,
  - emits `OrderRefunded(..., LoveCoin, ...)`.

## Voluntary Signals (AMN-2.6)

### `confirmOrderReceived(orderHash)`

- buyer only, status `Paid`, one-shot,
- emits `OrderReceivedByBuyer`,
- does not change order status.

### `signalWeakExternalPaymentClaim(orderHash)`

- buyer only, status `Created`, one-shot,
- emits `WeakExternalPaymentClaimed`,
- can notify reputation adapter,
- does not set `Paid`.

## Roles and Trust Boundaries

- `DEFAULT_ADMIN_ROLE`: setup and emergency operations.
- `CHECKOUT_WRITER_ROLE`: controlled settle/cancel operations.
- Buyer: funding + buyer attestations/signals.
- Seller: payment acceptance.

## Event Map

- lifecycle:
  - `OrderCreated`, `OrderPaid`, `OrderPaidEmergency`, `OrderSettled`, `OrderCancelled`
- funding:
  - `OrderOnChainFunded`
- refund:
  - `OrderRefunded`, `BuyerOrderAmnRefunded`
- attestation/signals:
  - `OrderFullPaymentDeclared`, `OrderFullPaymentAccepted`,
  - `OrderReceivedByBuyer`, `WeakExternalPaymentClaimed`
- integration:
  - `ReputationHooksUpdated`

## Invariants

- captures are blocked after buyer full-payment declaration,
- AMANITA capture cannot exceed order amount,
- one-order one-status progression with strict transition guards,
- cancel/refund does not imply settlement success.

