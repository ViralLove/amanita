# Loveconomy - Deep Tokenomics and Commerce Semantics

## Purpose

This document is the implementation-level source of truth for Amanita tokenomics across social mining and commerce flows.  
Compared with `docs/concept/Network-Economy.md`, this file goes deeper into contract semantics, invariants, and responsibility split.

## Scope and Layers

- **Concept layer (`docs/*`)**: narrative architecture and ecosystem principles.
- **Contracts layer (`contracts/docs/*`)**: concrete contract behavior, events, and state transitions.

This document belongs to the contracts layer.

## System Model

Loveconomy in the current AMN-2.x architecture is a **three-token + checkout + reputation** model:

- **`Lovecoin` (`$LOVECOIN`)**: utility social-mining token.
- **`AmanitaGovToken` (`$LGOV`)**: governance token gated by reputation.
- **`AmanitaToken` (`$AMANITA`)**: seller loyalty token with debt-ledger mechanics.
- **`AmanitaCheckout`**: canonical order lifecycle, funding rails, payment attestation, cancel/refund.
- **`AmanitaCommerceReputationAdapter`**: checkout-driven seller/buyer commerce metrics.

## Core Contract Responsibilities

### 1) `LoveEmissionEngine` - Utility/Governance Accrual

- accrues `$LOVECOIN` and `$LGOV` on valid superlikes,
- exposes claim functions,
- enforces reputation gate for governance path.

Important: current implementation has one-time `claimLGOV` behavior (`lgovClaimed` guard), while target model is continuous governance mining after threshold.

### 2) `AmanitaToken` - Loyalty + Debt Ledger

- seller emission increases `sellerDebt`,
- order-aware repayment hooks reduce `sellerDebt`,
- cancel path can restore debt and mint buyer refund on DG-approved AMN-2.8 flow.

### 3) `AmanitaCheckout` - Order Truth

- order statuses: `Created -> Paid -> Settled/Cancelled`,
- funding rails: `AmanitaCoin`, `LoveCoin`,
- `Paid` is an explicit attestation state (buyer declare + seller accept, or emergency admin path),
- cancel/refund emits canonical order refund events.

### 4) `AmanitaCommerceReputationAdapter` - Signal Aggregator

- receives hooks from checkout only,
- computes live and anchored seller/buyer signal metrics,
- exposes basis-point risk indicators,
- treats voluntary signals as non-punitive hints.

## Payment Rails and Semantic Rules

### Funding rails

- **AmanitaCoin rail**:
  - buyer transfers AMANITA into `AmanitaToken`,
  - checkout applies order debt repayment hook,
  - affects seller debt ledger.
- **LoveCoin rail**:
  - buyer transfers LOVE into checkout escrow,
  - does not affect `sellerDebt`.
- **External rail**:
  - can be part of business agreement,
  - not verifiable by protocol.

### Canonical `Paid` rule

`Paid` is not auto-derived from on-chain capture totals.  
`Paid` is set by attestation:

- buyer: `declareFullPayment(orderHash)`,
- seller: `acceptFullPayment(orderHash)`.

Emergency admin path exists (`markOrderPaid`) and is explicitly non-normal UX.

## Cancel/Refund Model (AMN-2.7 + AMN-2.8)

### LoveCoin

- escrow amount is transferred back to buyer on cancel,
- checkout emits `OrderRefunded(..., LoveCoin, amount)`.

### AmanitaCoin

- if order repaid debt: `restoreOrderDebtOnCancel` restores `sellerDebt` from `orderDebtRepaid`,
- buyer AMANITA refund uses `refundBuyerOnOrderCancel` mint-back (one-shot),
- checkout emits:
  - `BuyerOrderAmnRefunded(orderHash, buyer, amount)`,
  - `OrderRefunded(..., AmanitaCoin, amount)`.

### Invariants

- no double AMN buyer payout (`orderBuyerRefunded`),
- no double debt restore for same order (restore consumes `orderDebtRepaid`),
- cancel/refund is not equal to successful settlement.

## Utility vs Governance vs Loyalty - No Ambiguity Matrix

| Dimension | `$LOVECOIN` | `$LGOV` | `$AMANITA` |
|---|---|---|---|
| Primary role | Utility rewards | Governance power | Seller loyalty + debt ledger |
| Main source | `LoveEmissionEngine` social accrual | `LoveEmissionEngine` social accrual + reputation gate | Seller mint + checkout order hooks |
| Claim/Mint style | multi-claim utility flow | currently one-time claim in code | seller mint + order cancel mint-back path |
| Relation to checkout | escrow rail only | no direct checkout rail | canonical checkout rail for debt repayment/refund |
| Relation to reputation adapter | indirect social context | indirect social context | direct commerce signal via checkout hooks |

## Event-Level Mapping (Indexer-Oriented)

### Social mining layer

- `Emission`
- `ClaimedLOVECOIN`
- `ClaimedLGOV`

### Order and payment attestation layer

- `OrderCreated`
- `OrderOnChainFunded`
- `OrderFullPaymentDeclared`
- `OrderFullPaymentAccepted`
- `OrderPaid`
- `OrderPaidEmergency`
- `OrderSettled`
- `OrderCancelled`
- `OrderRefunded`
- `BuyerOrderAmnRefunded`

### Debt ledger layer

- `SellerOrderDebtRepaid`
- `SellerOrderDebtRestoredOnCancel`

### Reputation layer

- `LiveMetricsUpdated`
- `BuyerLiveMetricsUpdated`
- `SellerAnchored`
- `BuyerAnchored`

## Risk and Interpretation Rules

- External payment proof is outside protocol guarantees.
- Voluntary buyer signals are operational and non-punitive.
- BPS metrics are risk indicators, not legal verdicts.
- Emergency `Paid` path must be operationally constrained.

## Recommended Reading Order

1. `docs/concept/Network-Economy.md` (high level),
2. `contracts/docs/Loveconomy.md` (this document),
3. token-level docs (`Lovecoin.md`, `AmanitaToken.md`),
4. flow-level docs (`LoveEmissionEngine.md`, `AmanitaCheckout.md`, `AmanitaCommerceReputationAdapter.md`),
5. disclaimer layer (`commerce-reputation-disclaimers.md`).

