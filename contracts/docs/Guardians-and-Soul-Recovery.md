# Guardians and Soul Recovery — Architecture and User Flow

**Version:** 1.0  
**Date:** 2026-03-19  
**Scope:** Technical architecture and process for creating guardians and recovering soul (SBT) ownership in the Amanita SBT stack.  
**Related:** [SoulboundCore](../SoulboundCore.sol), [SoulRecovery](../SoulRecovery.sol), [SoulIdentity](../SoulIdentity.sol); task [SBT-REC-1](./analysis/tasks/task-delegate-soul-identity-recovery-to-soul-recovery/task-delegate-soul-identity-recovery-to-soul-recovery.md).

---

## 1. Technical architecture

### 1.1 Contract roles

| Contract | Role |
|----------|------|
| **SoulboundCore** | Holds SBT (soul) ownership. Only way to change owner is `executeRecovery(tokenId, newOwner)`, callable **only** by the configured recovery contract. |
| **SoulRecovery** | Holds one guardian per soul (tokenId). Guardian can start a recovery (nominate new owner) and, after a delay, confirm it. On confirm, SoulRecovery calls SoulboundCore.executeRecovery(tokenId, newOwner). |
| **SoulIdentity** | Single entry point for apps: user-facing calls (add/remove guardian, initiate/complete recovery) are on SoulIdentity; it delegates to SoulRecovery by resolving the user’s soul tokenId and calling SoulRecovery’s “For” methods. |

So: **SoulIdentity** = facade (user ↔ soul by address); **SoulRecovery** = guardian + recovery state and logic; **SoulboundCore** = actual ownership change.

### 1.2 Deployment and wiring

1. Deploy **SoulboundCore** (SBT), **SoulRecovery**(soulboundCore), **SoulIdentity**(soulboundCore, soulMetadata).
2. **SoulboundCore:** `setRecoveryContract(soulRecovery)` (only owner). Needed so that only SoulRecovery can call `executeRecovery`.
3. **SoulRecovery:** `setSoulIdentity(soulIdentity)` (only SoulRecovery owner). Needed so SoulRecovery accepts “For” calls from SoulIdentity.
4. **SoulIdentity:** `setSoulRecovery(soulRecovery)` (only DEFAULT_ADMIN_ROLE). Needed so SoulIdentity delegates guardian/recovery to SoulRecovery.

If SoulIdentity has no SoulRecovery set: guardian/recovery **writes** (add/remove guardian, initiate/complete recovery) revert with “SoulRecovery not set”; **reads** (getTrustedGuardians, isTrustedGuardian, isRecoveryInProgress) return empty/false.

### 1.3 Data model

- **One guardian per soul:** each SoulboundCore tokenId has at most one active guardian in SoulRecovery (address + set timestamp).
- **One recovery per soul:** at most one active recovery per tokenId (newOwner, guardian, initiatedAt). After confirm or cancel, that slot is cleared.
- SoulIdentity exposes guardians per **user**: it maps user → tokenId (via its owner→tokenId index or fallback), then reads/writes guardian for that tokenId in SoulRecovery.

### 1.4 Timings

| Constant | Value | Meaning |
|----------|--------|---------|
| **GUARDIAN_DELAY** (SoulRecovery) | 7 days | After setting a guardian, recovery cannot be **initiated** until this time has passed. |
| **RECOVERY_DELAY** (SoulRecovery) | 24 hours | After **initiating** recovery, the guardian cannot **confirm** until this time has passed. |

So: set guardian → wait 7 days → guardian can initiate recovery → wait 24 hours → guardian can confirm → ownership moves to new address.

### 1.5 Flow (technical)

**Guardian lifecycle**

- **Add guardian (user → guardian address):**  
  User calls `SoulIdentity.addTrustedGuardian(guardian)`. SoulIdentity resolves user’s tokenId, checks SoulRecovery is set, then calls `SoulRecovery.setGuardianFor(tokenId, guardian, msg.sender)`. SoulRecovery stores guardian and setTimestamp for that tokenId.
- **Remove guardian:**  
  User calls `SoulIdentity.removeTrustedGuardian(guardian)`. SoulIdentity calls `SoulRecovery.removeGuardianFor(tokenId, msg.sender)`. SoulRecovery clears the guardian for that tokenId.

**Recovery lifecycle**

- **Initiate:**  
  Guardian calls `SoulIdentity.initiateRecovery(user, newKey)`. SoulIdentity resolves user’s tokenId and calls `SoulRecovery.initiateRecoveryFor(tokenId, newKey, msg.sender)`. SoulRecovery checks msg.sender is the guardian for that tokenId, GUARDIAN_DELAY has passed, and no recovery is active; then stores RecoveryInfo (newOwner = newKey, guardian, initiatedAt).
- **Confirm (complete):**  
  After RECOVERY_DELAY, guardian calls `SoulIdentity.completeRecovery(user, newKey)`. SoulIdentity calls `SoulRecovery.confirmRecoveryFor(tokenId, msg.sender)`. SoulRecovery checks recovery is active, delay has passed, then calls `SoulboundCore.executeRecovery(tokenId, newOwner)`, which updates SBT ownership and notifies integration (e.g. SoulIdentity index). SoulRecovery then clears the recovery slot.
- **Cancel:**  
  The **soul owner** (current owner in SoulboundCore) can cancel an active recovery by calling **SoulRecovery** directly: `SoulRecovery.cancelRecovery(tokenId)`. There is no cancelRecovery on SoulIdentity; UIs that need cancel must call SoulRecovery with the correct tokenId (e.g. from SoulIdentity’s owner→tokenId resolution).

**Reads**

- `SoulIdentity.getTrustedGuardians(user)` → SoulRecovery.getGuardian(tokenId); returns one-element array or empty.
- `SoulIdentity.isTrustedGuardian(user, guardian)` → compare SoulRecovery.getGuardian(tokenId) with guardian.
- `SoulIdentity.isRecoveryInProgress(user)` → SoulRecovery.isRecoveryActive(tokenId).
- `SoulIdentity.getSoulProfile(user)` includes guardians from getTrustedGuardians(user).

---

## 2. User flow

### 2.1 As soul owner (I have a soul and want a guardian)

1. **Add a trusted guardian**  
   From your wallet (soul owner), call SoulIdentity: **addTrustedGuardian(guardianAddress)**.  
   - Effect: Your soul’s single guardian slot is set to that address. You can only have one guardian at a time; setting a new one replaces the previous.  
   - Guard: You must have a soul (SBT); SoulRecovery must be set on SoulIdentity.

2. **Remove guardian**  
   Call SoulIdentity: **removeTrustedGuardian(guardianAddress)**.  
   - Effect: Your soul’s guardian is cleared. No one can initiate recovery until you set a guardian again.

3. **Cancel an active recovery**  
   If a recovery was started by your guardian and you want to stop it: call **SoulRecovery.cancelRecovery(tokenId)** from the soul owner wallet. (Apps need to obtain tokenId for your address, e.g. via SoulIdentity’s public owner→tokenId index if exposed, or from events/indexer.)

4. **Check state**  
   Use SoulIdentity: **getTrustedGuardians(yourAddress)**, **isRecoveryInProgress(yourAddress)**, or **getSoulProfile(yourAddress)** (includes guardians).

### 2.2 As guardian (I was set as guardian for someone’s soul)

1. **Initiate recovery (owner lost access)**  
   From your wallet (guardian), call SoulIdentity: **initiateRecovery(ownerAddress, newOwnerAddress)**.  
   - Conditions: You must be the current guardian for that soul; at least **7 days** must have passed since you were set as guardian; there must be no active recovery.  
   - Effect: A recovery is started: the soul will move to `newOwnerAddress` after a **24-hour** wait, unless the current owner cancels it.

2. **Complete recovery (after 24 hours)**  
   After 24 hours from initiate, from your wallet call SoulIdentity: **completeRecovery(ownerAddress, newOwnerAddress)**.  
   - Effect: SoulRecovery calls SoulboundCore to transfer the SBT to the new owner. The soul (tokenId) is now owned by the new address; the previous owner no longer owns it.

3. **Check state**  
   You can use SoulIdentity view functions with the **owner’s** address to see guardians and recovery status (e.g. isRecoveryInProgress(ownerAddress)).

### 2.3 Summary (user flow)

| Actor | Action | Entry point | Main constraint |
|-------|--------|-------------|------------------|
| Soul owner | Add guardian | SoulIdentity.addTrustedGuardian(guardian) | Must have soul; SoulRecovery set |
| Soul owner | Remove guardian | SoulIdentity.removeTrustedGuardian(guardian) | Must have soul |
| Soul owner | Cancel recovery | SoulRecovery.cancelRecovery(tokenId) | Must be current owner |
| Guardian | Start recovery | SoulIdentity.initiateRecovery(user, newKey) | Must be guardian; 7 days after set |
| Guardian | Finish recovery | SoulIdentity.completeRecovery(user, newKey) | Must be same guardian; 24 h after start |

---

## 3. References

- **Contracts:** SoulboundCore.sol (executeRecovery, setRecoveryContract), SoulRecovery.sol (guardian/recovery logic, *For methods), SoulIdentity.sol (addTrustedGuardian, removeTrustedGuardian, initiateRecovery, completeRecovery, getTrustedGuardians, isRecoveryInProgress).
- **Task:** [task-delegate-soul-identity-recovery-to-soul-recovery](analysis/tasks/task-delegate-soul-identity-recovery-to-soul-recovery/) (SBT-REC-1).
- **Architecture (RU):** [solution-architecture-sbt-rec-1.md](analysis/tasks/task-delegate-soul-identity-recovery-to-soul-recovery/solution-architecture-sbt-rec-1.md).
