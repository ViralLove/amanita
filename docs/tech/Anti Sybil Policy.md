## Amanita / Loveconomy — Anti-Sybil Security Model

**Version:** 0.2 (conceptual target-state)  
**Date:** 2026-03-12  
**Status:** Target-state policy (not fully implemented yet)  

**Related documents:**

- `docs/tech/SpiralEngine Roles Security Policy.md` (Activators & Sellers)
- `contracts/docs/LoveEmissionEngine.md` (LGOV/LOVE emission)
- `contracts/docs/Loveconomy.md`
- `contracts/docs/GovernanceArchitecture.md`
- `contracts/docs/analysis/tasks/task-fix-loveemission-lgov-continuous-governance/task-fix-loveemission-lgov-continuous-governance.md`
- `contracts/docs/LoveDoPostNFT.md`
- `contracts/SpiralEngineLogic.sol`, `contracts/LoveEmissionEngine.sol`

---

## 1. Purpose

This document defines the **anti-Sybil security model** for the Amanita ecosystem.

The goal is to ensure that:

- **governance influence (`$LGOV`)**  
- **economic rewards (`$LOVECOIN`)**  
- **and seller privileges (`SELLER_ROLE`)**

are granted to **independent participants** rather than clusters of coordinated or automated identities.

The model protects against:

- **identity multiplication attacks**
- **reputation farming**
- **governance capture**

The approach is **not KYC-based**.  
Instead, the system relies on:

- social graph structure,
- economic friction,
- and reputation weighting.

---

## 2. Threat Model

### 2.1. Sybil definition

A **Sybil attack** occurs when **one actor controls multiple identities** to gain **disproportionate influence**.

In Amanita this could target:

1. **Social mining (`$LOVECOIN`)**
   - Attackers generate fake superlikes to farm utility tokens.
2. **Governance mining (`$LGOV`)**
   - Fake identities collaborate to accumulate governance weight.
3. **Seller onboarding**
   - Clusters of controlled accounts recommend each other to obtain `SELLER_ROLE`.
4. **Reputation inflation**
   - Fake interaction loops generate artificial trust signals.

### 2.2. Typical Sybil pattern

Example:

- Attacker controls accounts: `A1 ... A8`.
- These accounts:
  - invite each other;
  - create LoveDo posts;
  - superlike each other;
  - accumulate `LOVECOIN` and `LGOV`;
  - unlock governance;
  - recommend each other as sellers.

Without safeguards, such a cluster can simulate a legitimate community.

---

## 3. Design Principles

The Amanita anti-Sybil model follows **five principles**:

1. **Identity cost**  
   Creating a believable identity must require **time**, **effort**, or **economic stake**.

2. **Graph diversity**  
   Reputation should require interaction with **multiple independent branches** of the network.

3. **Reputation inheritance**  
   Trust signals carry weight only when they come from **trusted nodes**.

4. **Economic accountability**  
   Participants who recommend others must bear **economic and reputational risk** if that recommendation fails.

5. **Progressive access**  
   Sensitive privileges (governance, seller rights) must require **progressively stronger trust proofs**.

---

## 4. Existing Sybil Resistance in Amanita (Current State)

The current system already contains several anti-Sybil mechanisms.  
These create **friction layers** that slow down abuse.

### 4.1. InviteGraph Identity Structure

- Users cannot appear without invitation.
- Each user must satisfy:
  - `usedInviteByUser[user] != 0`
- This creates a **tree of activation**.

**Benefits:**

- prevents anonymous mass entry;
- links identities to existing participants;
- enables reputation inheritance.

### 4.2. Circle-based Interaction Limits

Superlikes require **social proximity**:

- `inviterOfAuthor == inviterOfLiker`

This prevents random network-wide collusion.  
Superlikes must originate within **shared trust circles**.

### 4.3. Monthly Activity Limits

`LoveDoPostNFT` enforces:

- `MAX_MONTHLY_POSTS_PER_USER = 8`
- `MAX_SUPERLIKES_PER_MONTH = 8`
- `MAX_MENTIONS_PER_SELLER = 8`

These constraints reduce **spam** and automated farming.

### 4.4. Reputation Threshold for Governance

Governance tokens require:

- `LOVE_DO_THRESHOLD = 8` posts

This ensures that governance access requires **observable history** in LoveDo.

### 4.5. Reputation Traceability

All trust signals exist **on-chain**:

- LoveDo posts
- superlikes
- seller references
- activation graph

This creates an **auditable reputation trail**.

---

## 5. Decision Point: LGOV Governance Mining Model (Current vs Target)

### 5.1. Current on-chain behavior (2026-03-12)

On 2026-03-12, `LoveEmissionEngine.sol` implements a **one-shot** governance unlock:

- `lgovAccrued[addr]` accumulates `LGOV` per superlike.
- `claimLGOV()`:
  - checks `LOVE_DO_THRESHOLD` (≥ 8 LoveDo posts),
  - mints accumulated `lgovAccrued`,
  - sets `lgovClaimed[addr] = true`,
  - and **never allows `claimLGOV()` again** (`"already claimed"`).
- Future superlikes continue to increase `lgovAccrued[addr]`, but **these tokens cannot be activated**.

This creates a **“dead zone” of governance emission** after the first claim.

### 5.2. Target model: reputation‑gated continuous governance mining (Model 2)

Target-state (accepted design, see task `task-fix-loveemission-lgov-continuous-governance`) is:

- `LOVE_DO_THRESHOLD` remains a **gate of maturity**:
  - before the threshold, no `LGOV` activation allowed;
  - after the threshold, access to **governance mining** opens.
- After the gate is passed:
  - the participant can **activate accumulated `LGOV` repeatedly**:
    - new superlikes → new `lgovAccrued` → new `claimLGOV` calls;
  - governance weight grows **together with sustained contribution**, not frozen after a single moment.
- Protection from governance capture moves from **“one-shot & freeze”** to:
  - reputation weighting,
  - graph diversity,
  - and LGOV staking / slashing.

This model is aligned with Amanita values:

- **trust first**;
- **reputation-gated governance**;
- **long reputational path**, not one-time membership.

### 5.3. Migration note

Implementation of the target model is tracked in:

- `contracts/docs/analysis/tasks/task-fix-loveemission-lgov-continuous-governance/task-fix-loveemission-lgov-continuous-governance.md`.

Until that task is completed:

- this Anti-Sybil Policy describes the **target-state behavior**;
- auditors must refer to `LoveEmissionEngine.sol` as SSOT for **current** one-shot semantics of `claimLGOV`.

---

## 6. Additional Anti-Sybil Mechanisms (Target State)

To address remaining risks, the system introduces the following **additional mechanisms**.  
They are designed to remain **decentralized** and **privacy-preserving**.

### 6.1. Identity Economic Cost (LGOV Bonding)

Certain system transitions require **temporary economic stake (`LGOV` bond)**.

**Example transitions:**

- governance unlock and continuous governance mining after threshold;
- seller candidacy;
- recommendation weight for SELLER candidates.

**Principles:**

- a bond is **locked** for the duration of the high-impact role (e.g. SELLER probation);
- the bond is:
  - **refundable** after successful participation;
  - **slashable** for violations (severity-dependent).

This increases the **cost of identity multiplication** for attackers while remaining fair for honest users.

### 6.2. Graph Diversity Requirement

Important reputation signals should require **diverse graph participation**.

**Target rule (for LGOV accrual):**

- A portion of superlikes that contribute to **governance-relevant `LGOV`** must originate from at least:
  - `N_branches_min` **distinct activation branches** in `InviteGraph`  
    over a diversity window `T_diversity` (e.g., last 3–6 months).

This prevents small tightly-knit clusters from generating **closed trust loops** that dominate governance.

In early phases this rule can be applied:

- **analytically** (off-chain monitoring and reporting),
- and later as **soft limits** (e.g., capping contribution from a single branch).

### 6.3. Reputation & Circle Weighting (Aligned with SpiralEngine Roles Policy)

Superlikes and endorsements are **not equal**. Their weight depends on:

- account age;
- reputation score (`repScore`);
- distance from root in `InviteGraph` (`distanceFromRoot`);
- violation history and sanctions.

We define:

\[
\text{effectiveWeight}_r
  = superlikeWeight_r
  \times repWeight[r]
  \times circleWeight[d(r)]
\]

Where:

- \( d(r) = \mathrm{distanceFromRoot}(r) \) — concentric circle index (see `SpiralEngine Roles Security Policy.md`);
- `circleWeight[d]` is defined via a **global community parameter** `circleDecay`:

\[
circleWeight[0] = 1, \quad
circleWeight[d] = circleDecay^d, \quad 0 < circleDecay < 1
\]

This connects Anti-Sybil policy with the **Seller recommendation model** from SpiralEngine Roles Security Policy:

- close circles (small `d`) have **higher base weight**;
- distant circles can contribute but need **more stake / more people** to achieve the same effect.

### 6.4. Reputation Decay

Inactive accounts gradually lose influence.

We define:

\[
repWeight[r] = baseWeight[r] \times \exp(-\lambda \cdot inactivityTime[r])
\]

Where:

- `λ` is a governance-controlled parameter;
- `inactivityTime[r]` is time since last meaningful contribution (e.g. LoveDo activity, valid recommendations).

This prevents abandoned accounts from retaining **permanent governance power** and encourages **long-term participation**.

### 6.5. Recommendation Accountability (Stake & Slash)

Participants recommending sellers bear **economic responsibility**:

- each recommender `r` stakes `stake[r]` in `LGOV` behind the candidate;
- on SELLER violations:
  - part of `stake[r]` may be **slashed**;
  - `repWeight[r]` is reduced;
  - future recommendation weight decreases.

Combined with circle weighting and reputation, recommendation weight for a candidate SELLER becomes:

\[
W_r = stake[r] \cdot repWeight[r] \cdot circleWeight[d(r)]
\]

Total recommendation index for candidate `C`:

\[
I(C) = \sum_{r \in \text{recommenders}(C)} W_r
\]

**Target threshold:**  

- governance parameter `T_seller` is chosen so that:
  - **8 “full-weight” recommendations** from circles 1–2 with high `repWeight` roughly give `I(C) \approx 8`;
  - for more distant circles and weaker reputations, reaching `I(C) ≥ 8` requires:
    - **more stake**, and/or
    - **more independent recommenders**.

This formalizes:

- the **“8 recommendations from near circles”** intuition,
- and is aligned with `SpiralEngine Roles Security Policy.md`.

### 6.6. Cluster Detection & Governance Escalation

Optional analytical systems can detect **suspicious graph patterns**.  
Signals include:

- high mutual interaction density;
- low external interaction diversity;
- repeated circular endorsement patterns.

Clusters exhibiting such behavior:

- are **flagged** in monitoring systems;
- may become the subject of a **governance proposal**:
  - rate-limiting,
  - temporary caps on governance influence,
  - or other transparent measures.

Any strong action against a cluster must:

- be based on **publicly observable criteria**;
- follow an **on-chain governance process** (LGOV voting);
- include a **grace period** and clear documentation.

---

## 7. Layered Protection Model

Amanita’s anti-Sybil strategy uses **multiple defensive layers**:

| Layer | Component / Mechanism           | Purpose                    |
|-------|---------------------------------|----------------------------|
| 1     | `InviteGraph`                   | identity lineage           |
| 2     | LoveDo activity limits          | spam resistance            |
| 3     | `LOVE_DO_THRESHOLD`             | governance gate            |
| 4     | graph diversity rules           | cluster resistance         |
| 5     | LGOV bonding / stakes           | identity & action cost     |
| 6     | accountability & slashing       | long-term responsibility   |

The goal is not **perfect Sybil elimination**, but **economic and social infeasibility** of large-scale abuse.

---

## 8. Security Philosophy

Amanita does **not** rely on:

- centralized identity verification;
- mandatory KYC;
- single authority trust decisions.

Instead the protocol relies on:

- social graph structure;
- reputation accumulation;
- economic accountability.

This creates a **self-regulating trust network**:

- honest participation becomes easier than manipulation.

---

## 9. Governance Implications

Because **`$LGOV` governs protocol evolution**, its distribution must remain **resistant to coordinated capture**.

Therefore:

- governance mining remains **reputation-gated** (via LoveDo history and rep weights);
- reputation signals require **social validation and graph diversity**;
- recommendation systems include **economic responsibility** (LGOV stake & slash);
- governance parameters (e.g. `circleDecay`, `T_seller`, `λ`, `N_branches_min`) may **evolve through LGOV voting**.

The system is designed so that:

- long-term honest participants gradually gain influence;
- short-term exploiters face increasing friction and economic cost.

---

## 10. Risk Tolerance & Trade-offs

- **No zero-risk promise.**  
  The model accepts that some small Sybil clusters may pass filters if they sustain long-term contribution and stake.

- **Bias towards protection.**  
  In ambiguous situations, priority is given to:
  - protecting buyers and vulnerable users,
  - preserving governance integrity,
  - even at the cost of a **longer path** for some honest participants.

- **Transparency over opaque bans.**  
  Any strong sanctions (slashing, limiting governance influence) must be:
  - grounded in **documented rules**,
  - traceable to **on-chain or public data**,
  - and applied via **transparent governance processes**.

---

## 11. Future Work

Future improvements may include:

- decentralized identity attestations;
- proof-of-personhood integrations;
- reputation zk-proofs;
- adaptive Sybil scoring;
- advanced graph analysis tools.

These enhancements may strengthen the model without compromising decentralization.

---

## 12. Conclusion

The Amanita anti-Sybil model combines:

- social trust graphs,
- reputation-based mining,
- economic bonding,
- and governance accountability.

This layered approach ensures that **political and economic power** in the ecosystem emerges from **sustained trusted participation**, rather than identity multiplication or automated farming.

The system does not attempt to eliminate Sybil attacks completely.  
Instead, it makes large-scale Sybil manipulation **progressively expensive, detectable, and economically irrational**.