# Network Economy - AMANITA Ecosystem

## Overview
This document describes the network economy principles of the AMANITA ecosystem, based on social mining, financial responsibility of participants, and selective invite distribution. The ecosystem implements a multi-token and commerce system with social capital mechanisms: $LOVECOIN (social mining), $LGOV (governance), $AMANITA (seller loyalty emission/debt ledger), SpiralEngine (invite/trust system), and `AmanitaCheckout` (order and payment attestations).

**Related Documentation:**
- **[README.md](../README.md)** — Project overview and getting started guide
- **[Architecture Overview](../tech/architecture-overview.md)** — System architecture and component interactions

**Context:** This document provides the economic foundation for the Amanita ecosystem, detailing how social interactions create value through blockchain-based reputation systems. It complements the technical architecture by explaining the "why" behind the smart contract design decisions.

## Key Principles of the New Economy

### Rejection of Old Patterns
- ❌ **No artificial token distribution schemes**
- ❌ **No centralized economic management**
- ❌ **No speculative mechanisms and bubbles**
- ❌ **No indiscriminate token distribution**

### New Paradigm
- ✅ **Social mining** through real activity
- ✅ **Financial responsibility** of each participant
- ✅ **Selective attraction** of valuable users
- ✅ **Invites as limited resource** and value
- ✅ **Transparency** of all economic processes

## Token System

### 1. $LOVECOIN - Utility Token (ERC-20)
**Purpose:** Utility token for social mining in Loveconomy

**Key Characteristics:**
- **Initial Supply:** 888,888,888 LOVECOIN (initial supply) + additional emission
- **Mining Mechanism:** Through LoveEmissionEngine based on superlikes
- **Usage:** Seller rewards, discounts, internal ecosystem payments
- **Claim Mechanism:** Claimable immediately after accumulation via `claimLOVECOIN()`
- **Contract:** `Lovecoin.sol`

**Economic Model:**
- **Emission Rate:** 1 LOVECOIN per superlike in LoveDoPostNFT
- **Distribution:** Direct to sellers based on social proof
- **Value Creation:** Through real social interactions and reputation building

### 2. $LGOV - Governance Token (ERC-20Votes)
**Purpose:** Governance and collective decision-making for ecosystem development

**Key Characteristics:**
- **Contract:** `AmanitaGovToken.sol` (symbol: AGOV in contract, used as LGOV in LoveEmissionEngine)
- **Mining Mechanism:** Same as $LOVECOIN but with reputation threshold
- **Activation Threshold:** 8 LoveDo posts required for activation
- **Governance Features:** ERC20Votes + ERC20Permit with delegation and snapshot voting
- **Usage:** DAO governance, collective resource management, coalition formation
- **One-time Activation:** Can be activated only once after reputation threshold
- **Issuance:** Based on $LOVECOIN accumulation

**Reputation System:**
- **Pending LGOV:** Accumulated but not yet activated
- **Active LGOV:** Available for governance after reputation threshold
- **LoveDo Count:** Number of posts directed at seller (reputation metric)

### 3. $AMANITA - Decentralized Seller Emission Token (ERC-20)
**Purpose:** Loyalty token layer with seller-driven emission and order-aware debt accounting

**Key Characteristics:**
- **Contract:** `AmanitaToken.sol` (symbol: AMANITA)
- **Initial Supply:** 888,888,888 AMANITA (INITIAL_SUPPLY)
- **Emission Mechanism:** Decentralized seller minting with eligibility/debt policy guards
- **Debt Model:** `sellerDebt` increases on seller emission and decreases through order-aware AMANITA captures
- **Cancel Model (AMN-2.7/2.8):** on cancel, debt can be restored and buyer AMANITA refund can be minted back by checkout flow
- **Usage:** Seller loyalty programs, audience rewards, order-linked repayment mechanics
- **Control:** seller emission guarded by SpiralEngine seller eligibility + policy checks; order repayment/refund hooks restricted to checkout

**Economic Model:**
- **Decentralized Emission:** Each seller can emit tokens based on their sales
- **Value-Based:** Emission tied to actual sold values
- **Burn on Redemption:** Tokens are burned when redeemed, maintaining economic balance
- **Seller Autonomy:** Each seller controls their own emission within ecosystem rules

**Note:** This is a separate token system from $LOVECOIN (social P2P dynamics) and $LGOV (governance). $AMANITA focuses on seller-to-audience loyalty programs.

### 4. SpiralEngine - Social Capital (Invite + Identity/Trust)
**Purpose:** Access control, trust system, and social capital representation through spiral hierarchy

**Key Characteristics:**
- **Contract:** `SpiralEngine.sol` (UUPS upgradeable)
- **Limited Supply:** 12 invites per activated user
- **Unique Codes:** Each invite has a unique string identifier
- **One-time Use:** Each invite can only be used once
- **Soulbound:** Transfers are restricted (all transfer functions reverted)
- **Expiry System:** Optional expiration dates for time-limited invites
- **Integration:** Delegates SBT functionality to `SoulIdentity` contract

**Social Capital Mechanics:**
- **Access Control:** Invite required for ecosystem participation
- **Trust Building:** Activator responsible for activated user behavior
- **Network Growth:** Organic expansion through trusted connections (spiral hierarchy)
- **Reputation Tracking:** Full history of invite usage and organic trust communities

### 5. Commerce Order & Reputation Layer (AMN-2.x)

**Purpose:** Bind payment facts, attestations, and reputation signals into one auditable flow.

**Core contracts:**
- `AmanitaCheckout`: canonical order lifecycle and on-chain funding rails (`AmanitaCoin`, `LoveCoin`), attestation-gated `Paid`, settlement/cancel transitions.
- `AmanitaCommerceReputationAdapter`: hybrid metrics (live + anchored snapshots) for seller/buyer commerce signals.

**Order semantics (important):**
- `Paid` is not "token receipts reached threshold".  
  `Paid` is an explicit attestation pair: buyer `declareFullPayment` + seller `acceptFullPayment` (or emergency admin path).
- External payment leg can exist, but protocol does not verify fiat/PSP settlement.

**Cancel/refund semantics (AMN-2.7/2.8):**
- LoveCoin captured in checkout escrow is returned to buyer on cancel.
- AMANITA order path restores seller debt ledger and can mint buyer refund back for captured AMANITA (one-shot guards by `orderHash`).
- Cancel/refund does not equal successful settlement in reputation metrics.

**Reputation semantics (AMN-2.6):**
- Voluntary signals (for example "received order") are operational hints, not legal/payment proof.
- Reputation percentages are non-punitive signal discipline indicators, not fraud verdicts.

## Social Mining System

### LoveEmissionEngine Mechanics
**Core Principle:** Tokens are mined only through social proof and reputation building via LoveDo posts and superlikes

**Mining Process:**
1. **LoveDo Post Creation:** User creates a post praising a seller (max 8 posts per month)
2. **Superlike Mechanism:** Seller can give superlikes to posts about them (max 8 superlikes per month)
3. **Emission Trigger:** Each superlike triggers token emission (1 LOVECOIN + 1 LGOV pending)
4. **Distribution:** Tokens distributed to the praised seller (sellerTo in LoveDo post)

**Key Constraints:**
- **Monthly Limits:** 8 posts per user, 8 superlikes per seller per month
- **Social Validation:** Only users from the same inviter group (organic trust community) can superlike posts
- **Reputation Threshold:** LGOV activation requires 8 LoveDo posts directed at seller
- **One-time Superlikes:** Each seller can superlike a post only once

**Token Distribution:**
- **$LOVECOIN:** Immediately claimable utility tokens (1 per superlike) via `claimLOVECOIN()`
- **$LGOV:** Governance tokens that require reputation threshold (8 LoveDo posts) via `claimLGOV()`
- **Accumulation:** Tokens accumulate in `loveAccrued` and `lgovAccrued` mappings

**Example Scenarios:**
- **Seller1** receives 5 LoveDo posts → gets 5 superlikes → accumulates 5 $LOVECOIN + 5 $LGOV pending
- **Seller2** receives 10 LoveDo posts → gets 8 superlikes → can claim 8 $LOVECOIN + activate 8 $LGOV (≥8 posts threshold)
- **User A** creates LoveDo post for Seller3 → Seller3 superlikes → Seller3 receives 1 $LOVECOIN + 1 $LGOV pending

### LoveDoPostNFT - Social Proof System
**Purpose:** Decentralized reputation and social proof mechanism

**Key Features:**
- **Post Creation:** Users create posts praising sellers
- **Superlike System:** Sellers can superlike posts about them
- **Monthly Limits:** 8 posts per user per month, 8 superlikes per seller per month
- **Reputation Tracking:** Full history of social interactions

**Economic Impact:**
- **Social Capital:** Posts create reputation for sellers
- **Token Distribution:** Superlikes trigger token emission
- **Quality Control:** Limits prevent spam and manipulation
- **Transparency:** All interactions recorded on blockchain

## Financial Responsibility System

### Limited Budget Principle
**Key Rule:** Sellers can only use tokens within their earned budget

**Examples:**
- **Seller1** mined 88 $LOVECOIN → can only give discounts up to 88 euros
- **Seller2** mined 44 $LOVECOIN → limited to discounts of 44 euros
- **No Overdraft:** Cannot spend more than earned

### Direct User Priority
- **Discounts First:** For users directly invited by the seller
- **Direct Connection:** Clear link between invitation and reward
- **Fair Distribution:** Equitable resource allocation
- **Responsibility:** Accountability for invitation quality

## Invite System as Valuable Resource

### Selective Distribution
**Principle:** Each seller carefully manages their 12 invites

**Selection Criteria:**
- **Real Interest:** Genuine interest in seller's products
- **Purchase Potential:** Likelihood to make purchases
- **Interaction Quality:** Quality of engagement
- **Trust and Reputation:** Trustworthiness and reputation

### Invite Value
- **Receiving Invite:** Gaining access to AMANITA ecosystem
- **Invite = Opportunity:** To participate in social mining
- **Invite = Right:** To invite others and earn tokens
- **Invite = Privilege:** Not an entitlement

### Distribution Limitations
- **No Indiscriminate Distribution:** No "spray and pray" approach
- **Each Invite:** Conscious decision
- **Responsibility:** For invited users
- **Quality Over Quantity:** Focus on meaningful connections

## Network Economy Architecture

### Multi-Level Activity
**Network Example:**
```
Seller1 (88 $LOVECOIN)
├── User A (invited User B)
│   ├── User B (made purchase) → User A received tokens
│   └── User C (invited User D)
│       └── User D (made purchase) → User C and User A received tokens
└── User E (invited User F)
    └── User F (made purchase) → User E received tokens
```

### Network Transparency
- **Visibility:** Each participant sees their invitation network
- **Contribution Tracking:** Shows each participant's contribution
- **History:** All transactions recorded on blockchain
- **Efficiency Metrics:** Invitation effectiveness tracking

## Web3 Social-Conceptual Paradigm

### Decentralized Trust
**Traditional vs Web3 Trust:**
- **Traditional:** Centralized authority (banks, platforms)
- **Web3:** Decentralized trust through social proof and reputation
- **AMANITA Implementation:** SpiralEngine + LoveDoPostNFT create trust networks

### Post-Barter Economy
**Economic Evolution:**
- **Barter:** Direct goods exchange
- **Money:** Centralized currency systems
- **Post-Barter:** Social capital + utility tokens + governance
- **AMANITA Model:** Combines social proof with economic incentives through LOVECOIN and LGOV

### Social Capital Monetization
**Innovation:** Converting social interactions into economic value
- **LoveDo Posts:** Social proof becomes economic asset
- **Superlikes:** Reputation triggers token emission
- **Invite System:** Social connections create economic opportunities
- **Governance:** Social capital enables collective decision-making

## Integration with WordPress/WooCommerce

### Seller as "AMANITA Functionality Window"
- **Shortcode Integration:** Access to ecosystem functionality
- **Secure Non-Custodial Zone:** User-controlled assets
- **Invite Management:** Through familiar interface
- **Network Analytics:** Social activity tracking

### Shortcode Functions
- **`[amanita-wallet]`** - Secure wallet access
- **`[amanita-rewards]`** - Display earned tokens
- **`[amanita-invites]`** - Invite management
- **`[amanita-network]`** - Invited user network

## Economic Sustainability

### Speculation Protection
- **Usage Restrictions:** Token usage limitations
- **Temporal Constraints:** Exchange time restrictions
- **Activity Binding:** Tied to real activity
- **Protection:** Against artificial schemes

### Scalability
- **Organic Growth:** Through quality invitations
- **Sustainable Economy:** No bubbles
- **Transparency:** All processes visible
- **Fair Distribution:** Equitable resource allocation

## Key Advantages of the Model

### For Ecosystem
- **Real Activity:** Instead of artificial schemes
- **Financial Stability:** Through limitations
- **Quality Growth:** Through selectivity
- **Transparency:** All processes visible
- **Long-term Stability:** Sustainable economic model

### For Sellers
- **Responsibility:** For their decisions
- **Motivation:** For quality invitations
- **Direct Connection:** Between efforts and results
- **Participation:** In ecosystem development
- **Reputation System:** Social capital building

### For Users
- **Invite Value:** As privilege, not entitlement
- **Real Opportunities:** For earning
- **Transparency:** All operations visible
- **Participation:** In decentralized economy
- **Social Connections:** In ecosystem

## Smart Contract Integration

### LoveEmissionEngine
**Core Functions:**
- `emitForSuperlike(uint256 tokenId, address liker)`: Triggers token emission on superlike (EMITTER_ROLE only)
- `claimLOVECOIN()`: Allows sellers to claim accumulated utility tokens (reentrancy protected)
- `claimLGOV()`: Activates governance tokens after reputation threshold (8 LoveDo posts required)
- `getReputationProgress(address seller)`: Returns (pending LGOV, active LGOV, loveDoCount)

**Key Mappings:**
- `loveAccrued[address]`: Accumulated LOVECOIN tokens per seller
- `lgovAccrued[address]`: Accumulated LGOV tokens per seller
- `lgovClaimed[address]`: Whether LGOV has been claimed (one-time activation)

**Token Integration:**
- Uses `Lovecoin.sol` for utility tokens ($LOVECOIN)
- Uses `AmanitaGovToken.sol` for governance tokens (as $LGOV)

### SpiralEngine (Invite System)
**⚠️ IMPORTANT:** `InviteNFT.sol` does NOT exist — all invite functionality is in `SpiralEngine.sol`!

**Key Features:**
- Unique invite codes with one-time use (soulbound NFTs, IERC5192)
- Full history tracking of all usage and organic trust communities
- Expiry system for time-limited invites (optional)
- Integration with LoveEmissionEngine for access control
- Spiral hierarchy with 12-granular circles (max 12 activated users per activator)

**Core Functions:**
- `mintInvite(string inviteCode, uint256 expiry)`: Creates one invite for distribution
- `activateUser(string inviteCode, address user, string[] newInviteCodes, uint256 expiry)`: Activates user and mints exactly 12 new invites
- `grantSellerRole(address user)`: Grants SELLER_ROLE to activated user
- `isUserActivated(address user)`: Checks if user has activated an invite
- `getCircleMembers(address activator)`: Returns members of organic trust community

**Key Mappings:**
- `inviteCodeToTokenId[string]`: Maps invite code to NFT tokenId
- `isInviteUsed[uint256]`: Tracks if invite has been used
- `usedInviteByUser[address]`: Maps user to their used invite
- `inviteExpiry[uint256]`: Optional expiry timestamps
- `userActivator[address]`: Who activated the user
- `activatedBy[address]`: Array of users activated by this address (max 12)

### LoveDoPostNFT
**Social Proof System:**
- Monthly limits to prevent spam (8 posts/user, 8 superlikes/seller)
- Superlike mechanism for reputation building
- Integration with SpiralEngine for access control
- Full transparency of social interactions

**Core Functions:**
- `mintLoveDoPost()`: Creates new LoveDo post (monthly limit enforced)
- `addSuperlike()`: Adds superlike to post (social validation required)
- `getLoveDoCount()`: Returns number of posts directed at seller
- `getPost()`: Returns full LoveDo post data

**Key Constraints:**
- **Social Validation:** Only users from same inviter group can superlike
- **Anti-Spam:** Monthly limits on posts and superlikes
- **Self-Prevention:** Authors cannot superlike their own posts
- **Nonce Protection:** Front-running protection via superlikeNonces

**Data Structure:**
```solidity
struct LoveDo {
    address author;          // post author
    address sellerTo;        // praised seller
    address linkedSeller;    // author's inviter
    uint8 superlikes;        // superlike count
    uint256 timestamp;       // creation time
}
```

### ProductRegistry
**Decentralized Catalog:**
- IPFS-based metadata storage (only CID stored on-chain)
- Seller-controlled product management
- Cross-selling capabilities
- Integration with invite system for access control

**Core Functions:**
- `createProduct()`: Creates new product with IPFS CID
- `updateProduct()`: Updates product metadata (seller only)
- `deactivateProduct()`: Deactivates product (swap-and-pop optimization)
- `getProduct()`: Returns product data by ID
- `getProductsBySeller()`: Returns all products by seller

**Key Features:**
- **Gas Optimization:** Only IPFS CID stored on-chain
- **Version Tracking:** catalogVersion increments on changes
- **Efficient Deactivation:** Swap-and-pop for activeProductIds
- **Access Control:** Only product owner can modify

**Data Structure:**
```solidity
struct Product {
    uint256 id;          // unique product ID
    address seller;      // product owner
    string ipfsCID;      // IPFS metadata link
    bool active;         // visibility status
}
```

## Architectural Principles

1. **Social Mining** through real activity
2. **Financial Responsibility** of each participant
3. **Selectivity** in invite distribution
4. **Priority** for direct users
5. **Limitations** based on earned budget
6. **Transparency** of all processes
7. **Security** of non-custodial wallets
8. **Sustainability** of economic model

## Conclusion

The AMANITA network economy creates a **sustainable ecosystem** where each participant is **responsible for their decisions** and **receives fair rewards** for real activity.

**Key Achievements:**
- Rejection of outdated economic patterns
- Creation of real value through social mining
- Financial responsibility and transparency
- Selective and quality participant attraction
- Long-term sustainability of economic model

This model ensures **fair and sustainable development** of a decentralized ecosystem where each participant has **real incentives** for quality participation and **transparent opportunities** for earning.

## Technical Implementation Notes

### Smart Contract Addresses
- **LoveEmissionEngine:** Core token emission logic for $LOVECOIN and $LGOV
- **Lovecoin:** Utility token for social mining (888,888,888 initial supply + emission)
- **AmanitaGovToken:** Governance token with voting (ERC20Votes + ERC20Permit, used as LGOV)
- **AmanitaToken:** Decentralized seller emission token with debt ledger and order hooks
- **AmanitaCheckout:** Canonical order contract for funding rails, payment attestation, settle/cancel
- **AmanitaCommerceReputationAdapter:** Checkout-driven commerce signal aggregation (live + anchor)
- **SpiralEngine:** Social capital and access control (soulbound NFTs, invite system)
- **LoveDoPostNFT:** Social proof and reputation
- **ProductRegistry:** Decentralized product catalog
- **AmanitaRegistry:** Central contract registry
- **Orders / PaymentRouter:** Legacy paths may still exist in repository; AMN-2.x source of truth for checkout flow is `AmanitaCheckout`

### Economic Parameters
- **Emission Rate:** 1 LOVECOIN per superlike (EMISSION_RATE = 1 ether)
- **LGOV Emission Rate:** 1 LGOV per superlike (pending until reputation threshold)
- **Reputation Threshold:** 8 LoveDo posts for LGOV activation (LOVE_DO_THRESHOLD = 8)
- **Monthly Limits:** 8 posts per user, 8 superlikes per seller (MAX_MONTHLY_POSTS_PER_USER = 8, MAX_SUPERLIKES_PER_MONTH = 8)
- **Invite Limit:** 12 invites per activated user (exactly 12 in activateAndMintInvites)
- **Seller Mentions:** 8 mentions per seller (MAX_MENTIONS_PER_SELLER = 8)
- **Token Supply:** 
  - 888,888,888 LOVECOIN (INITIAL_SUPPLY) + additional emission
  - 888,888,888 AMANITA (INITIAL_SUPPLY) + decentralized seller emission (burned on redemption)

### Integration Points
- **WordPress Plugin:** WooCommerce integration
- **Telegram Bot:** User interface and onboarding
- **WebApp Wallet:** Non-custodial asset management
- **Supabase Edge Functions:** ArWeave storage integration

---

## 📚 **Documentation Navigation**

**For comprehensive understanding of the Amanita ecosystem:**

- **[README.md](../README.md)** — Project overview, mission, and getting started
- **[Architecture Overview](../tech/architecture-overview.md)** — Technical architecture and system components

**This document focuses on:**
- Economic model and tokenomics
- Social mining mechanics
- Smart contract integration details
- Sustainability principles
