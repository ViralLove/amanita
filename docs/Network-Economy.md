# Network Economy - AMANITA Ecosystem

## Overview
This document describes the network economy principles of the AMANITA ecosystem, based on social mining, financial responsibility of participants, and selective invite distribution. The ecosystem implements a three-tier token system with social capital mechanisms.

**Related Documentation:**
- **[README.md](../README.md)** — Project overview and getting started guide
- **[Architecture Overview](architecture-overview.md)** — System architecture and component interactions

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

## Three-Tier Token System

### 1. $AMANITA - Utility Token (ERC-20)
**Purpose:** Internal ecosystem currency for seller rewards and sales stimulation

**Key Characteristics:**
- **Initial Supply:** 888,888,888 AMANITA (fixed supply)
- **Mining Mechanism:** Through LoveEmissionEngine based on superlikes
- **Usage:** Seller rewards, discounts, internal ecosystem payments
- **Transfer Restrictions:** Only from users to sellers (inter-user transfers prohibited)
- **Burn Mechanism:** Burned on first payment to prevent speculation

**Economic Model:**
- **Emission Rate:** 1 AMANITA per superlike in LoveDoPostNFT
- **Distribution:** Direct to sellers based on social proof
- **Value Creation:** Through real social interactions and reputation building

### 2. $AGOV - Governance Token (ERC-20Votes)
**Purpose:** Governance and collective decision-making for ecosystem development

**Key Characteristics:**
- **Mining Mechanism:** Same as $AMANITA but with reputation threshold
- **Activation Threshold:** 8 LoveDo posts required for activation
- **Governance Features:** ERC20Votes with delegation and snapshot voting
- **Usage:** DAO governance, collective resource management, coalition formation

**Reputation System:**
- **Pending AGOV:** Accumulated but not yet activated
- **Active AGOV:** Available for governance after reputation threshold
- **LoveDo Count:** Number of posts directed at seller (reputation metric)

### 3. InviteNFT - Social Capital (ERC-721)
**Purpose:** Access control, trust system, and social capital representation

**Key Characteristics:**
- **Limited Supply:** 12 invites per activated user
- **Unique Codes:** Each invite has a unique string identifier
- **One-time Use:** Each invite can only be used once
- **Transferable:** Can be transferred between users
- **Expiry System:** Optional expiration dates for time-limited invites

**Social Capital Mechanics:**
- **Access Control:** Invite required for ecosystem participation
- **Trust Building:** Inviter responsible for invitee behavior
- **Network Growth:** Organic expansion through trusted connections
- **Reputation Tracking:** Full history of invite transfers and usage

## Social Mining System

### LoveEmissionEngine Mechanics
**Core Principle:** Tokens are mined only through social proof and reputation building via LoveDo posts and superlikes

**Mining Process:**
1. **LoveDo Post Creation:** User creates a post praising a seller (max 8 posts per month)
2. **Superlike Mechanism:** Seller can give superlikes to posts about them (max 8 superlikes per month)
3. **Emission Trigger:** Each superlike triggers token emission (1 AMANITA + 1 AGOV pending)
4. **Distribution:** Tokens distributed to the praised seller (sellerTo in LoveDo post)

**Key Constraints:**
- **Monthly Limits:** 8 posts per user, 8 superlikes per seller per month
- **Social Validation:** Only users from the same inviter group can superlike posts
- **Reputation Threshold:** AGOV activation requires 8 LoveDo posts directed at seller
- **One-time Superlikes:** Each seller can superlike a post only once

**Token Distribution:**
- **$AMANITA:** Immediately claimable utility tokens (1 per superlike)
- **$AGOV:** Governance tokens that require reputation threshold (8 LoveDo posts)
- **Accumulation:** Tokens accumulate in amanitaAccrued and agovAccrued mappings

**Example Scenarios:**
- **Seller1** receives 5 LoveDo posts → gets 5 superlikes → accumulates 5 $AMANITA + 5 $AGOV pending
- **Seller2** receives 10 LoveDo posts → gets 8 superlikes → can claim 8 $AMANITA + activate 8 $AGOV (≥8 posts threshold)
- **User A** creates LoveDo post for Seller3 → Seller3 superlikes → Seller3 receives 1 $AMANITA + 1 $AGOV pending

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
- **Seller1** mined 88 $AMANITA → can only give discounts up to 88 euros
- **Seller2** mined 44 $AMANITA → limited to discounts of 44 euros
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
Seller1 (88 $AMANITA)
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
- **AMANITA Implementation:** InviteNFT + LoveDoPostNFT create trust networks

### Post-Barter Economy
**Economic Evolution:**
- **Barter:** Direct goods exchange
- **Money:** Centralized currency systems
- **Post-Barter:** Social capital + utility tokens + governance
- **AMANITA Model:** Combines social proof with economic incentives

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
- `claimAMANITA()`: Allows sellers to claim accumulated utility tokens (reentrancy protected)
- `claimAGOV()`: Activates governance tokens after reputation threshold (8 LoveDo posts required)
- `getReputationProgress(address seller)`: Returns (pending AGOV, active AGOV, loveDoCount)

**Key Mappings:**
- `amanitaAccrued[address]`: Accumulated AMANITA tokens per seller
- `agovAccrued[address]`: Accumulated AGOV tokens per seller
- `agovClaimed[address]`: Whether AGOV has been claimed (one-time activation)

### InviteNFT
**Key Features:**
- Unique invite codes with one-time use (soulbound NFTs)
- Full history tracking of all transfers and usage
- Expiry system for time-limited invites (optional)
- Integration with LoveEmissionEngine for access control

**Core Functions:**
- `activateAndMintInvites()`: Activates invite and mints exactly 12 new invites
- `mintInvites()`: Batch mint invites for sellers (SELLER_ROLE only)
- `validateInviteCode()`: Validates invite code and user eligibility
- `isUserActivated()`: Checks if user has activated an invite

**Key Mappings:**
- `inviteCodeToTokenId[string]`: Maps invite code to NFT tokenId
- `isInviteUsed[uint256]`: Tracks if invite has been used
- `usedInviteByUser[address]`: Maps user to their used invite
- `inviteExpiry[uint256]`: Optional expiry timestamps

### LoveDoPostNFT
**Social Proof System:**
- Monthly limits to prevent spam (8 posts/user, 8 superlikes/seller)
- Superlike mechanism for reputation building
- Integration with InviteNFT for access control
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
- **LoveEmissionEngine:** Core token emission logic
- **AmanitaToken:** Utility token (888,888,888 supply)
- **AmanitaGovToken:** Governance token with voting (ERC20Votes)
- **InviteNFT:** Social capital and access control (soulbound NFTs)
- **LoveDoPostNFT:** Social proof and reputation
- **ProductRegistry:** Decentralized product catalog
- **AmanitaRegistry:** Central contract registry
- **Orders:** Order management with OTP validation
- **AmanitaPaymentRouter:** Payment processing with stablecoins

### Economic Parameters
- **Emission Rate:** 1 AMANITA per superlike (EMISSION_RATE = 1 ether)
- **Reputation Threshold:** 8 LoveDo posts for AGOV activation (LOVE_DO_THRESHOLD = 8)
- **Monthly Limits:** 8 posts per user, 8 superlikes per seller (MAX_MONTHLY_POSTS_PER_USER = 8, MAX_SUPERLIKES_PER_MONTH = 8)
- **Invite Limit:** 12 invites per activated user (exactly 12 in activateAndMintInvites)
- **Seller Mentions:** 8 mentions per seller (MAX_MENTIONS_PER_SELLER = 8)
- **Token Supply:** 888,888,888 AMANITA (INITIAL_SUPPLY)

### Integration Points
- **WordPress Plugin:** WooCommerce integration
- **Telegram Bot:** User interface and onboarding
- **WebApp Wallet:** Non-custodial asset management
- **Supabase Edge Functions:** ArWeave storage integration

---

## 📚 **Documentation Navigation**

**For comprehensive understanding of the Amanita ecosystem:**

- **[README.md](../README.md)** — Project overview, mission, and getting started
- **[Architecture Overview](architecture-overview.md)** — Technical architecture and system components

**This document focuses on:**
- Economic model and tokenomics
- Social mining mechanics
- Smart contract integration details
- Sustainability principles
