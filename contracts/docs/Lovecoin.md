# Lovecoin Contract (`Lovecoin.sol`)

## Purpose

`Lovecoin` is the utility ERC-20 token (`LOVECOIN`) used in social-mining flows.
It is intentionally simple and role-gated.

## Contract Profile

- Standard: ERC20 + AccessControl
- Symbol: `LOVECOIN`
- Decimals: `18`
- Initial supply: `888_888_888 ether`
- Roles:
  - `DEFAULT_ADMIN_ROLE`
  - `MINTER_ROLE`

## Constructor Semantics

`constructor(address owner)`:

- validates non-zero owner,
- mints initial supply to owner,
- grants admin and minter roles to owner.

## Functional Surface

### `mint(address to, uint256 amount)`

- Access: `onlyRole(MINTER_ROLE)`
- Guards:
  - `to != address(0)`
  - `amount > 0`
- Effect: `_mint(to, amount)`

### `burn(address from, uint256 amount)`

- Access: `onlyRole(MINTER_ROLE)`
- Guards:
  - `from != address(0)`
  - `amount > 0`
  - `balanceOf(from) >= amount`
- Effect: `_burn(from, amount)`

### `decimals()`

- returns constant `18`.

### `supportsInterface(bytes4 interfaceId)`

- AccessControl compatibility passthrough.

## Security and Governance Notes

- mint/burn are fully role-controlled, so operational key management is critical.
- no supply cap in code beyond policy and role governance.
- token itself does not encode social logic; social emission policy is implemented in `LoveEmissionEngine`.

## Integration Notes

- Primary integrator for accrual/claim path: `LoveEmissionEngine`.
- In checkout context, LOVE token can be captured as `LoveCoin` rail escrow by `AmanitaCheckout` and refunded on cancel.

## Out of Scope of `Lovecoin.sol`

- reputation thresholds,
- superlike validation,
- order lifecycle,
- debt-ledger accounting.

