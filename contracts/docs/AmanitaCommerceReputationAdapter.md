# AmanitaCommerceReputationAdapter (`AmanitaCommerceReputationAdapter.sol`)

## Purpose

`AmanitaCommerceReputationAdapter` converts checkout events into structured seller/buyer metrics for downstream SBT/off-chain consumers.

It is a signal adapter, not an independent payment oracle.

## Data Model

### Seller live metrics (`CommerceMetrics`)

- `sellerRedemptionCount`
- `sellerTotalRedeemedAmount`
- `sellerSuccessfulOrdersCount`
- `sellerRefundCount`
- `sellerDisputeCount`
- `sellerLastRedemptionAt`
- `sellerSettledWithBuyerDeclareCount`
- `sellerSettledWithoutSellerAcceptCount`

### Buyer live metrics (`BuyerSignalMetrics`)

- `settledReceivedCount`
- `settledReceivedMissingDeclareCount`
- `weakExternalClaimCount`

### Anchored snapshots

- seller: `AnchoredSnapshot`
- buyer: `BuyerAnchoredSnapshot`

Anchors freeze current live metrics at `anchoredAt` timestamp for deterministic references.

## Input Trust Assumptions

- `notify*` functions are accepted only from configured `checkout`.
- adapter mirrors checkout truth; it does not verify external PSP/fiat state.
- `recordRefund` and `recordDispute` remain ops-driven inputs (`REPUTATION_OPS_ROLE`).

## Hook Semantics

### `notifyAmanitaRedemption(seller, grossAmount)`

- increments seller redemption counters,
- updates cumulative redeemed amount and last redemption timestamp.

### `notifyOrderSettled(...)`

- increments successful order counter,
- updates seller declare/accept discipline counters,
- updates buyer received/missing-declare counters when buyer had confirmed receipt pre-settle.

### `notifyWeakExternalPaymentClaim(buyer, seller)`

- increments buyer weak claim counter.

## Operational Functions

- `recordRefund(seller)` - increments seller refund counter.
- `recordDispute(seller)` - increments seller dispute counter.
- `anchorSeller(seller)` / `anchorBuyer(buyer)` - snapshot live metrics.

## Derived BPS Views

### `getSellerUnsettledAfterDeclareBps(seller)`

- numerator: settled orders with buyer declare but without seller accept,
- denominator: settled orders with buyer declare,
- returns `0` on zero denominator.

### `getBuyerReceivedWithoutDeclareBps(buyer)`

- numerator: settled received signals missing buyer declare,
- denominator: all settled received signals,
- returns `0` on zero denominator.

## Non-Punitive Interpretation Rules

- metrics are operational quality indicators, not legal judgments,
- weak external payment claims are optional and non-canonical,
- cancel/refund paths do not automatically count as successful settlement.

## Roles

- `DEFAULT_ADMIN_ROLE`: checkout wiring and privileged config.
- `ANCHOR_ROLE`: snapshot commits.
- `REPUTATION_OPS_ROLE`: refund/dispute operational entries.

## Event Surface

- `CheckoutUpdated`
- `LiveMetricsUpdated`
- `BuyerLiveMetricsUpdated`
- `SellerAnchored`
- `BuyerAnchored`
- `RefundRecorded`
- `DisputeRecorded`

## Integration Boundary

For clear operator understanding:

- order lifecycle truth lives in `AmanitaCheckout`,
- debt/refund token accounting lives in `AmanitaToken`,
- social emission truth lives in `LoveEmissionEngine`,
- this adapter only aggregates selected commerce signals into metrics.

