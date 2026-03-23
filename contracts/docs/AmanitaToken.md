# AmanitaToken Contract (`AmanitaToken.sol`)

## Purpose

`AmanitaToken` (`AMANITA`) is a loyalty token contract with embedded seller debt-ledger mechanics and checkout-facing order hooks.

## Contract Profile

- Standard: ERC20 + AccessControl
- Symbol: `AMANITA`
- Decimals: `18`
- Initial supply: `888_888_888 ether` (to constructor owner)
- Key role constant: `SELLER_ROLE` (validated via external SpiralEngine source)

## Main State Model

- `sellerDebt[address]`: current debt from seller emissions.
- `sellerTotalEmitted[address]`: cumulative seller emission volume.
- `sellerAcceptedPayments[address]`: accepted payment ledger input.
- `sellerLiquidityRefunds[address]`: liquidity corrections/refunds.
- `orderDebtRepaid[bytes32 orderHash]`: cumulative debt repaid by order.
- `orderBuyerRefunded[bytes32 orderHash]`: one-shot AMN buyer refund guard.
- `amanitaCheckout`: authorized checkout contract for order hooks.

## Seller Emission Path

### `mint(address to, uint256 amount)`

Access: seller-driven (not admin-only), but gated by:

1. eligibility checks via configured `spiralEngine` source:
   - `SELLER_ROLE`,
   - activated invite (`usedInviteByUser > 0`),
   - not suspended.
2. debt policy checks:
   - absolute cap (optional),
   - debt-to-liquidity ratio cap (optional).

Effects:

- increases `sellerTotalEmitted[msg.sender]`,
- increases `sellerDebt[msg.sender]`,
- mints AMANITA to target address.

## Checkout Order Hooks (AMN-2.x)

### `applyOrderDebtRepayment(address seller, bytes32 orderHash, uint256 grossAmount)`

- Access: only `amanitaCheckout`.
- Requires AMANITA already transferred to contract.
- Burns `grossAmount`.
- Repays seller debt by `min(grossAmount, sellerDebt[seller])`.
- Increments `orderDebtRepaid[orderHash]` by actual repaid amount.

### `restoreOrderDebtOnCancel(address seller, bytes32 orderHash)`

- Access: only `amanitaCheckout`.
- One-time restore semantics by consuming `orderDebtRepaid[orderHash]`.
- Adds restored amount back into `sellerDebt[seller]`.

### `refundBuyerOnOrderCancel(address buyer, bytes32 orderHash, uint256 amount)`

- Access: only `amanitaCheckout`.
- One-shot guard via `orderBuyerRefunded[orderHash]`.
- Mints AMANITA back to buyer (DG-approved AMN-2.8 mint-back model).

## Admin and Policy Surface

### `setSpiralEngine(address)`

- sets seller eligibility source.

### `setAmanitaCheckout(address)`

- authorizes checkout for order hooks.

### `setDebtPolicy(...)`

- updates cap enforcement flags and thresholds.

### `recordAcceptedPayment(...)` / `recordLiquidityRefund(...)`

- admin inputs for liquidity accounting used by ratio caps.

### `burn(address from, uint256 amount)`

- admin burn capability.

## Invariants and Safety

- checkout hooks cannot be called before checkout is set.
- AMN buyer refund is one-shot per order.
- debt restore requires non-zero prior repaid debt.
- repayment burns gross AMANITA even if seller debt is smaller; repayment counter tracks actual debt decrease.

## Event Map

- debt/emission:
  - `SellerDebtIncreased`
  - `SellerOrderDebtRepaid`
  - `SellerOrderDebtRestoredOnCancel`
- cancel buyer payout:
  - `BuyerOrderAmnRefunded`
- policy and ops:
  - `DebtPolicyUpdated`
  - `SellerAcceptedPaymentRecorded`
  - `SellerLiquidityRefundRecorded`

## Responsibility Boundaries

- `AmanitaToken` does not own order state.
- `AmanitaCheckout` owns order lifecycle and decides when hooks are called.
- `AmanitaCommerceReputationAdapter` interprets order outcomes separately from debt-ledger accounting.

