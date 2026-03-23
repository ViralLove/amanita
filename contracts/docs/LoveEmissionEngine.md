# LoveEmissionEngine Contract (`LoveEmissionEngine.sol`)

## Purpose

`LoveEmissionEngine` is the social-mining accrual and claim engine for:

- utility token `$LOVECOIN`,
- governance token `$LGOV`.

It converts validated social actions (superlikes) into token accrual and controlled claim flows.

## Non-Goals (Important)

`LoveEmissionEngine` does **not**:

- process checkout order lifecycle,
- perform cancel/refund logic,
- verify external payments.

Refund semantics are implemented in `AmanitaCheckout` + `AmanitaToken` and documented in `AmanitaCheckout.md` / `Loveconomy.md`.

## Dependency Graph

- `LoveDoPostNFT`: source of post/superlike state and reputation threshold input.
- `InviteGraph` / depth-circle gating logic (through LoveDo validation model).
- `Lovecoin`: utility token transfer on claim.
- `AmanitaGovToken`: governance token mint on claim.

## Core State and Constants

- `loveAccrued[seller]`: pending utility accrual.
- `lgovAccrued[seller]`: pending governance accrual.
- `lgovClaimed[seller]`: one-time claim guard in current implementation.
- `EMISSION_RATE = 1 ether`.
- `LOVE_DO_THRESHOLD = 8`.

## Functional Semantics

### `emitForSuperlike(uint256 tokenId, address liker)`

Access: `EMITTER_ROLE`.

Behavior:

1. reads post context,
2. verifies that `liker` has valid superlike for `tokenId`,
3. enforces anti-double-emit for `(tokenId, liker)`,
4. increments both `loveAccrued[sellerTo]` and `lgovAccrued[sellerTo]` by `EMISSION_RATE`,
5. emits `Emission`.

### `claimLOVECOIN()`

Behavior:

- seller claims all pending `loveAccrued[msg.sender]`,
- storage is zeroed before transfer (reentrancy-safe pattern),
- emits `ClaimedLOVECOIN`.

### `claimLGOV()`

Behavior:

- checks reputation threshold (`LoveDo >= 8`),
- checks pending governance accrual,
- mints LGOV from accrued amount,
- emits `ClaimedLGOV`.

Current implementation nuance:

- `lgovClaimed` makes claim effectively one-time.
- additional accrual after first claim can remain unclaimable until model migration.

## Utility vs Governance Differentiation (No Ambiguity)

### `$LOVECOIN` (utility)

- objective: immediate ecosystem utility rewards,
- claim model: recurrent claim path,
- gating: valid social emission events only.

### `$LGOV` (governance)

- objective: governance voting power,
- additional gating: reputation threshold,
- current code path: one-time claim due to `lgovClaimed`,
- target policy (documented): continuous claim after threshold (future task).

## Interaction with Refund and Checkout Domain

There is **no direct refund path** in `LoveEmissionEngine`.

Why it matters for operators:

- a refund in checkout does not "reverse" social emission in this contract,
- checkout refunds affect order and debt-ledger domain, not social-mining accrual domain,
- this separation avoids semantic coupling between social reputation mining and commerce dispute outcomes.

## Events

- `Emission(address seller, uint256 lovecoinAmount, uint256 lgovAccrued)`
- `ClaimedLOVECOIN(address seller, uint256 amount)`
- `ClaimedLGOV(address seller, uint256 amount)`

## Security Notes

- strict role gating for emission trigger.
- accrual reset-before-transfer in claim path.
- trust boundary: correctness of social validation depends on upstream LoveDo/invite-gating model.

## Operator Checklist

When explaining this contract to another operator, always separate:

1. social accrual truth (`LoveEmissionEngine`),
2. order/refund truth (`AmanitaCheckout` + `AmanitaToken`),
3. reputation signal aggregation (`AmanitaCommerceReputationAdapter`).

This prevents cross-domain ambiguity and incorrect assumptions about refunds or payment proofs.

