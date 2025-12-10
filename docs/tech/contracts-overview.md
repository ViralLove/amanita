# Smart Contracts Overview - AMANITA Ecosystem

## Overview
This document provides a comprehensive overview of the Amanita ecosystem smart contracts, their interactions, and implementation details. The contracts implement a decentralized social commerce platform with reputation-based tokenomics.

**Related Documentation:**
- **[README.md](../README.md)** — Project overview and getting started
- **[Architecture Overview](architecture-overview.md)** — System architecture and components
- **[Network Economy](Network-Economy.md)** — Economic model and tokenomics

## Contract Architecture

### Core Contracts

#### **LoveEmissionEngine.sol**
**Purpose:** Central token emission and reputation management

**Key Functions:**
- `emitForSuperlike(uint256 tokenId, address liker)` - Triggers token emission on superlike
- `claimLOVECOIN()` - Allows sellers to claim accumulated utility tokens ($LOVECOIN)
- `claimLGOV()` - Activates governance tokens after reputation threshold
- `getReputationProgress(address seller)` - Returns reputation status

**Security Features:**
- Access control via EMITTER_ROLE
- Reentrancy protection in claimLOVECOIN()
- Social validation for superlikes through invite graph
- One-time LGOV activation

**Key Mappings:**
```solidity
mapping(address => uint256) public loveAccrued;      // Accumulated LOVECOIN
mapping(address => uint256) public lgovAccrued;     // Accumulated LGOV
mapping(address => bool) public lgovClaimed;         // LGOV activation status
```

**Token Integration:**
- Uses `Lovecoin.sol` for utility tokens ($LOVECOIN)
- Uses `AmanitaGovToken.sol` for governance tokens (as $LGOV)
- Integrated with `LoveDoPostNFT.sol` and `SpiralEngine.sol`

#### **Lovecoin.sol**
**Purpose:** Utility token for social mining in Loveconomy

**Characteristics:**
- **Supply:** 888,888,888 LOVECOIN (INITIAL_SUPPLY) + additional emission
- **Standard:** ERC-20 with AccessControl
- **Minting:** Controlled by MINTER_ROLE
- **Burning:** Controlled by MINTER_ROLE
- **Usage:** Social mining through superlikes in LoveDo posts

**Key Functions:**
- `mint(address to, uint256 amount)` - Mint new tokens
- `burn(address from, uint256 amount)` - Burn tokens

**Note:** `AmanitaToken.sol` exists in codebase but is not actively used in `LoveEmissionEngine`. The active token system uses `Lovecoin` for utility tokens.

#### **AmanitaGovToken.sol**
**Purpose:** Governance token with voting capabilities

**Characteristics:**
- **Symbol:** AGOV (in contract), used as LGOV in LoveEmissionEngine
- **Standard:** ERC20Votes + ERC20Permit with delegation
- **Governance:** Snapshot voting support
- **Activation:** Requires reputation threshold (8 LoveDo posts)
- **Minting:** Controlled by MINTER_ROLE

**Key Features:**
- Delegation support for voting
- Permit functionality for gasless approvals
- Integration with OpenZeppelin governance
- One-time activation after reputation threshold

#### **SpiralEngine.sol** (UUPS upgradeable)
**Purpose:** Access control, social capital management, and spiral hierarchy

**⚠️ IMPORTANT:** `InviteNFT.sol` does NOT exist — all invite functionality is implemented in `SpiralEngine.sol`!

**Characteristics:**
- **Standard:** ERC-721 (Soulbound) with IERC5192
- **Supply:** 12 invites per activated user
- **Transfer:** Restricted (soulbound behavior - all transfer functions reverted)
- **Expiry:** Optional time-limited invites
- **Integration:** Delegates SBT functionality to `SoulIdentity` contract

**Key Functions:**
- `mintInvite(string inviteCode, uint256 expiry)` - Creates one invite for distribution
- `activateUser(string inviteCode, address user, string[] newInviteCodes, uint256 expiry)` - Activates user and mints 12 new invites
- `grantSellerRole(address user)` - Grants SELLER_ROLE to activated user
- `getCircleMembers(address activator)` - Returns members of organic trust community
- `isUserActivated(address user)` - Checks if user has activated an invite

**Key Mappings:**
```solidity
mapping(string => uint256) public inviteCodeToTokenId;  // Code to NFT mapping
mapping(uint256 => bool) public isInviteUsed;           // Usage tracking
mapping(address => uint256) public usedInviteByUser;    // User activation
mapping(uint256 => uint256) public inviteExpiry;        // Expiry timestamps
mapping(address => address) public userActivator;        // Who activated user
mapping(address => address[]) public activatedBy;        // Whom user activated (max 12)
```

#### **LoveDoPostNFT.sol**
**Purpose:** Social proof and reputation system

**Characteristics:**
- **Standard:** ERC-721 with URI storage
- **Limits:** Monthly limits on posts and superlikes
- **Validation:** Social group validation
- **Anti-spam:** Nonce protection and limits

**Key Functions:**
- `mintLoveDoPost(address sellerTo, string uri)` - Creates new LoveDo post
- `addSuperlike(uint256 tokenId, uint256 expectedNonce)` - Adds superlike
- `getLoveDoCount(address seller)` - Returns posts directed at seller
- `getPost(uint256 tokenId)` - Returns full post data

**Data Structure:**
```solidity
struct LoveDo {
    address author;          // Post author
    address sellerTo;        // Praised seller
    address linkedSeller;    // Author's inviter
    uint8 superlikes;        // Superlike count
    uint256 timestamp;       // Creation time
}
```

**Key Constraints:**
- **Monthly Limits:** 8 posts per user, 8 superlikes per seller
- **Social Validation:** Only same inviter group can superlike
- **Self-Prevention:** Authors cannot superlike own posts
- **Mention Limits:** 8 mentions per seller

#### **ProductRegistry.sol**
**Purpose:** Decentralized product catalog

**Characteristics:**
- **Storage:** IPFS CID-based metadata
- **Gas Optimization:** Only CID stored on-chain
- **Version Tracking:** Catalog versioning
- **Access Control:** Seller-only modifications

**Key Functions:**
- `createProduct(string ipfsCID)` - Creates new product
- `updateProduct(uint256 productId, string newIpfsCID, uint256 newPrice)` - Updates product
- `deactivateProduct(uint256 productId)` - Deactivates product
- `getProduct(uint256 productId)` - Returns product data

**Data Structure:**
```solidity
struct Product {
    uint256 id;          // Unique product ID
    address seller;      // Product owner
    string ipfsCID;      // IPFS metadata link
    bool active;         // Visibility status
}
```

### Supporting Contracts

#### **AmanitaRegistry.sol**
**Purpose:** Central contract registry

**Key Functions:**
- `setAddress(string name, address newAddress)` - Updates contract addresses
- `getAddress(string name)` - Retrieves contract address
- `getAllContractNames()` - Returns all registered contracts

**Security:**
- Owner-only address updates
- Zero address validation

#### **Orders.sol**
**Purpose:** Order management with OTP validation

**Characteristics:**
- **OTP Integration:** Unique OTP per order
- **IPFS Storage:** Order metadata on IPFS
- **Payment Tracking:** Order status management

**Key Functions:**
- `createOrder(address buyer, address seller, uint256 amount, string otp, string ipfsHash)` - Creates order
- `markAsPaid(bytes32 orderHash)` - Marks order as paid
- `getOrder(bytes32 orderHash)` - Returns order data

**Data Structure:**
```solidity
struct Order {
    address buyer;
    address seller;
    uint256 amount;
    string otp;
    string ipfsHash;
    bool paid;
}
```

#### **AmanitaPaymentRouter.sol**
**Purpose:** Payment processing with stablecoins

**Characteristics:**
- **Stablecoin Support:** USDT/USDC integration
- **OTP Validation:** Links payments to orders
- **Automatic Payout:** Direct seller payments

**Key Functions:**
- `pay(address seller, uint256 amount, bytes32 orderHash)` - Processes payment

## Contract Interactions

### Token Emission Flow
```
1. User creates LoveDo post → LoveDoPostNFT.mintLoveDoPost()
2. Seller gives superlike → LoveDoPostNFT.addSuperlike()
3. Emission triggered → LoveEmissionEngine.emitForSuperlike()
4. Tokens accumulated → loveAccrued[seller] += EMISSION_RATE (LOVECOIN)
5. Tokens accumulated → lgovAccrued[seller] += EMISSION_RATE (LGOV pending)
6. Seller claims utility tokens → LoveEmissionEngine.claimLOVECOIN()
7. Seller activates governance → LoveEmissionEngine.claimLGOV() (if ≥8 LoveDo posts)
```

### Access Control Flow
```
1. User receives invite code → SpiralEngine validation
2. Activator calls activateUser() → SpiralEngine.activateUser()
3. User gains access → SpiralEngine.isUserActivated() returns true
4. 12 new invites minted → SpiralEngine creates invites for activated user
5. User can participate → All ecosystem functions available
```

### Product Management Flow
```
1. Seller creates product → ProductRegistry.createProduct()
2. Product stored on IPFS → Only CID stored on-chain
3. Product available → Cross-selling across network
4. Product updates → ProductRegistry.updateProduct()
5. Version tracking → catalogVersion increments
```

## Security Analysis

### Access Control
- **Role-Based:** EMITTER_ROLE, SELLER_ROLE, ADMIN_ROLE
- **Ownership:** DEFAULT_ADMIN_ROLE for critical functions
- **Validation:** Invite-based access control

### Reentrancy Protection
- **State Updates:** Balance clearing before transfers
- **Checks-Effects-Interactions:** Proper function ordering
- **External Calls:** Limited and controlled

### Input Validation
- **Address Validation:** Zero address checks
- **String Validation:** Non-empty CID requirements
- **Numeric Validation:** Positive amounts and limits

### Economic Safeguards
- **Monthly Limits:** Anti-spam protection
- **Social Validation:** Group-based interactions
- **Reputation Threshold:** AGOV activation requirements

## Gas Optimization

### Storage Efficiency
- **IPFS Integration:** Only CIDs stored on-chain
- **Efficient Deactivation:** Swap-and-pop for arrays
- **Minimal Storage:** Essential data only

### Function Optimization
- **Batch Operations:** Multiple invites in single transaction
- **View Functions:** Gas-free data retrieval
- **Efficient Loops:** Optimized array operations

### Cost Reduction
- **Event Usage:** Minimal storage for tracking
- **Mapping Access:** O(1) storage operations
- **Struct Packing:** Optimized data structures

## Economic Parameters

### Token Economics
- **LOVECOIN Supply:** 888,888,888 (INITIAL_SUPPLY) + additional emission
- **Emission Rate:** 1 LOVECOIN per superlike (EMISSION_RATE = 1 ether)
- **LGOV Emission Rate:** 1 LGOV per superlike (pending until reputation threshold)
- **LGOV Threshold:** 8 LoveDo posts (LOVE_DO_THRESHOLD = 8)

### Activity Limits
- **Monthly Posts:** 8 per user (MAX_MONTHLY_POSTS_PER_USER)
- **Monthly Superlikes:** 8 per seller (MAX_SUPERLIKES_PER_MONTH)
- **Seller Mentions:** 8 per seller (MAX_MENTIONS_PER_SELLER)
- **User Invites:** 12 per activated user

### Network Parameters
- **Invite Expiry:** Optional time limits
- **Catalog Versioning:** Incremental updates
- **Order OTP:** Unique per transaction

## Integration Points

### External Systems
- **IPFS:** Metadata storage for products and posts
- **ArWeave:** Alternative storage solution
- **Polygon:** Layer 2 deployment
- **Stablecoins:** USDT/USDC for payments

### Internal Systems
- **Telegram Bot:** User interface and onboarding
- **WordPress Plugin:** E-commerce integration
- **WebApp Wallet:** Non-custodial asset management
- **Python API:** Backend services

## Deployment Considerations

### Network Selection
- **Polygon:** Low-cost transactions
- **Ethereum Compatibility:** Standard tooling support
- **Fast Finality:** Quick transaction confirmation

### Contract Dependencies
- **OpenZeppelin:** Standard library usage
- **Access Control:** Role-based permissions
- **ERC Standards:** Token compatibility

### Upgrade Strategy
- **Immutable Core:** Critical functions immutable
- **Configurable Parameters:** Adjustable limits
- **Registry Pattern:** Address updates via registry

## Monitoring and Analytics

### Key Metrics
- **Token Emission:** LOVECOIN and LGOV distribution
- **Social Activity:** LoveDo posts and superlikes
- **Network Growth:** Invite activations through SpiralEngine
- **Product Activity:** Catalog updates

### Events Tracking
- **Emission Events:** Token distribution tracking
- **Social Events:** Post and superlike activity
- **Network Events:** Invite activations
- **Product Events:** Catalog changes

### Health Monitoring
- **Contract Balances:** Token supply tracking
- **Activity Levels:** User engagement metrics
- **Gas Usage:** Transaction cost optimization
- **Error Rates:** Function failure tracking

---

## 📚 **Documentation Navigation**

**For comprehensive understanding of the Amanita ecosystem:**

- **[README.md](../README.md)** — Project overview, mission, and getting started
- **[Architecture Overview](architecture-overview.md)** — Technical architecture and system components
- **[Network Economy](Network-Economy.md)** — Economic model and tokenomics
- **[AI-Navigator.md](../AI-Navigator.md)** — Development diary and decision history

**This document focuses on:**
- Smart contract architecture and implementation
- Security analysis and best practices
- Gas optimization strategies
- Integration patterns and deployment considerations 