# 🏗️ InviteActions.js - Architectural Documentation

**Date**: 2025-10-20T09:45:00Z  
**Methodology**: @analysis.mdc  
**Version**: 1.0  
**Status**: Production

---

## 📋 General Concept

**InviteActions** is a **social structure module (Layer 4A)** that manages the invitation system and user activation in the Amanita ecosystem. This is a critically important layer that creates the foundation for the spiral social structure.

### 🎯 Architectural Role

```yaml
InviteActions: Social structure and user activation
    ↓
ComponentActions: Delegates user activation
    ↓
SpiralEngine: Stores social graph (who invited whom)
```

---

## 🔧 Class Structure

### **Constructor and Dependencies**
```javascript
constructor(contractManager, ethersUtils, config)
```

**Dependencies**:
- **contractManager**: Contract loading and management
- **ethersUtils**: Blockchain operations and signer management  
- **config**: Configuration from .env files

**Principle**: Layer 4A - Social Structure Foundation

---

## 🚀 Core Methods

### **1. action7() - Create First Seller (Bootstrap)**

**Purpose**: Create the very first seller in the system with full configuration (bootstrap workflow)

**Signature**:
```javascript
async action7(inviteCode)
```

**Algorithm**:
```yaml
Input: inviteCode (string) or from config
  ↓
Step 1: Resolve invite code
  → Try parameter, then config
  ↓
Step 2: Get or generate wallet
  → Existing (from config) OR new (generated)
  ↓
Step 3: Activate seller
  → activateUser(inviteCode, seller, 12 invites)
  ↓
Step 4: Grant roles
  → SELLER_ROLE + ACTIVATOR_ROLE
  ↓
Step 5: Save invites
  ↓
Output: {success, sellerAddress, invites, roles}
```

**Key Features**:
- ✅ **Bootstrap**: First seller creation
- ✅ **Wallet Management**: Use existing or generate
- ✅ **Full Setup**: Activation + both roles + invites
- ✅ **Security**: Only shows generated keys

**Configuration Keys**:
- `seller.inviteCode` - Invite code
- `seller.address` - Existing address (optional)
- `seller.privateKey` - Existing key (optional)

**Use Cases**:
- 🔹 **System Bootstrap**: First seller
- 🔹 **Testing**: Quick configured seller
- 🔹 **Recovery**: Re-create seller

**Example Output**:
```javascript
{
  success: true,
  sellerAddress: '0x...',
  sellerPrivateKey: '0x...' or '[EXISTING - NOT SHOWN]',
  wasGenerated: true/false,
  invitesCreated: 12,
  rolesGranted: ['SELLER_ROLE', 'ACTIVATOR_ROLE']
}
```

---

### **2. action777() - Root Invites Generation**

**Purpose**: Generate root invites for deployer

**Signature**:
```javascript
async action777()
```

**Algorithm**:
```yaml
Input: None
  ↓
Step 1: Load SpiralEngine contract
  ↓
Step 2: Validate deployer access (delegate to AccessControlActions)
  ↓
Step 3: Generate and mint 12 invites
  ↓
Step 4: Save invites to file
  ↓
Output: 12 root invite codes
```

**Key Features**:
- ✅ **Root Generation**: Creates root invites for deployer
- ✅ **Access Control**: Delegates permission validation
- ✅ **File Persistence**: Saves invites to file
- ✅ **Social Foundation**: Foundation for social structure

---

### **2. generateAndMintInvites() - Invite Minting**

**Purpose**: Generate and mint invites on blockchain

**Signature**:
```javascript
async generateAndMintInvites(spiralEngine)
```

**Algorithm**:
```yaml
Input: spiralEngine contract
  ↓
Step 1: Generate 12 invite codes
  ↓
Step 2: Mint each invite on-chain
  ↓
Step 3: Save invites to file
  ↓
Output: Array of minted invite codes
```

**Key Features**:
- ✅ **Batch Minting**: Minting one invite at a time
- ✅ **On-chain Storage**: Storage in SpiralEngine contract
- ✅ **File Backup**: Duplication in file
- ✅ **Transaction Safety**: Wait for confirmation of each transaction

---

### **3. action11() - Generate Invites for Active Seller**

**Purpose**: Generate invites FOR SELLER (seller mints their own invites)

**Signature**:
```javascript
async action11()
```

**Algorithm**:
```yaml
Input: Seller address and config from .env
  ↓
Step 1: Get seller address from config (SELLER_ADDRESS)
  ↓
Step 2: Get invite count from config (default: 12)
  ↓
Step 3: Load SpiralEngine contract
  ↓
Step 4: Validate seller access (delegation → AccessControlActions)
  ↓
Step 5: Generate and mint invites FOR SELLER
  ↓
  Helper Flow (generateAndMintInvitesForSeller):
    → Get seller signer (SELLER_PRIVATE_KEY)
    → Generate N AMANITA-XXXX-XXXX codes
    → Mint each invite FROM SELLER
    → Wait for each transaction
    → Log progress
  ↓
Step 6: Save to bot/flowers/{sellerAddress}_invites_action11.txt
  ↓
Output: {success, sellerAddress, invitesCreated, invites}
```

**Key Features**:
- ✅ **Seller Authentication**: Uses SELLER_PRIVATE_KEY (not deployer!)
- ✅ **Configurable Count**: Default 12, override via config
- ✅ **Validation**: Checks seller activation + SELLER_ROLE
- ✅ **Standard Format**: AMANITA-XXXX-XXXX invites
- ✅ **File Persistence**: Saves to seller-specific file
- ✅ **Progress Logging**: Logs each minted invite
- ✅ **Transaction Safety**: Waits for each tx confirmation

**Configuration Keys**:
- `seller.address` - Seller Ethereum address (required)
- `seller.privateKey` - Seller private key for signing (required)
- `seller.inviteCount` - Number of invites to generate (optional, default: 12)

**Differences from Action 777**:
```yaml
Action 777 (Deployer Invites):
  - Signer: Deployer (DEFAULT_ADMIN_ROLE)
  - Count: 12 (fixed)
  - File: deployer_invites_{network}.txt
  - Purpose: Root invites for activating sellers
  - Used by: Admin/Deployer
  
Action 11 (Seller Invites):
  - Signer: Seller (SELLER_ROLE)
  - Count: Configurable (default 12)
  - File: {sellerAddress}_invites_action11.txt
  - Purpose: Seller's own invites for their network
  - Used by: Active seller
```

**Example Output**:
```javascript
{
  success: true,
  sellerAddress: "0x1234567890abcdef...",
  invitesCreated: 12,
  invites: [
    "AMANITA-A1B2-C3D4",
    "AMANITA-E5F6-G7H8",
    // ... 10 more
  ]
}
```

**Use Cases**:
- 🔹 **Seller Network Growth**: Seller generates invites for their users
- 🔹 **Autonomous Operation**: Seller manages their own invite distribution
- 🔹 **DAO Delegation**: Seller acts independently without deployer

**Private Helpers**:
- `generateAndMintInvitesForSeller(spiralEngine, sellerAddress, count)` - Mint from seller
- `generateAmanitaInviteCodes(count)` - Generate unique codes (reused)
- `saveUserInvites(sellerAddress, invites, suffix)` - Save to file (reused)

**Error Scenarios**:
```yaml
Error 1: SELLER_ADDRESS not configured
  → Clear message: "SELLER_ADDRESS not configured"

Error 2: SELLER_PRIVATE_KEY not found
  → Clear message: "SELLER_PRIVATE_KEY not found in config"

Error 3: Seller not activated
  → Via AccessControlActions: "Seller {address} not activated"

Error 4: No SELLER_ROLE
  → Via AccessControlActions: "Seller {address} does not have SELLER_ROLE"

Error 5: Mint transaction failed
  → Error with tx details from Ethers.js
```

---

### **4. action888() - Full Seller Initialization Pipeline**

**Purpose**: Complete seller initialization from invite code to fully activated seller ready for catalog upload

**Signature**:
```javascript
async action888(inviteCode, sellerAddress, options = {})
```

**Parameters**:
- `inviteCode` - Invite code for activation (required)
- `sellerAddress` - Seller Ethereum address (optional, generates new wallet if not provided)
- `options.skipSBT` - Skip SoulIdentity setup (default: false)
- `options.skipCatalog` - Skip catalog upload (default: false)
- `options.skipAdditionalInvites` - Skip generating additional invites (default: false)

**Algorithm**:
```yaml
Input: Invite code + seller address (optional)
  ↓
Step 1: Validate inputs
  ├→ Validate invite code format
  ├→ Validate seller address (or generate new wallet)
  └→ Check SELLER_PRIVATE_KEY if catalog upload needed
  ↓
Step 2: Load contracts (SpiralEngine)
  ↓
Step 3: Validate invite on blockchain
  ├→ Check invite exists
  ├→ Check invite not used
  └→ Verify invite active
  ↓
Steps 4-7: Activate seller (delegate to activateSeller)
  ├→ Activate user with invite
  ├→ Grant SELLER_ROLE
  ├→ Grant ACTIVATOR_ROLE
  ├→ Generate 12 invites for seller
  └→ Save invites to file
  ↓
Step 8 (optional): Setup SoulIdentity
  ├→ Skip if skipSBT=true
  └→ Delegate to AccessControlActions.setupSoulIdentity()
  ↓
Output: {success, sellerAddress, activated, rolesGranted, invites, sbtSetup}
```

**Key Features**:
- ✅ **Full Pipeline**: Complete seller initialization in one command
- ✅ **Wallet Generation**: Auto-generates wallet if address not provided
- ✅ **Multi-Step Orchestration**: 8 steps with clear logging
- ✅ **Flexible Options**: Skip SBT/catalog/invites if needed
- ✅ **Delegation Pattern**: Reuses activateSeller() helper
- ✅ **SBT Integration**: Optional SoulIdentity setup
- ✅ **Error Handling**: Clear error messages at each step

**Configuration Keys**:
- `seller.address` - Seller Ethereum address (optional)
- `seller.privateKey` - Seller private key (required if not skipping catalog)

**Example Usage**:
```javascript
// Full initialization with new wallet
const result = await inviteActions.action888('AMANITA-ROOT-0001');

// Full initialization with existing wallet
const result = await inviteActions.action888(
  'AMANITA-ROOT-0001',
  '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
);

// Skip SBT setup
const result = await inviteActions.action888(
  'AMANITA-ROOT-0001',
  '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
  { skipSBT: true }
);
```

**Output Example**:
```javascript
{
  success: true,
  sellerAddress: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  activated: true,
  rolesGranted: ["SELLER_ROLE", "ACTIVATOR_ROLE"],
  invites: ["AMANITA-A1B2-C3D4", ...],
  sbtSetup: { success: true, soulId: "1" }
}
```

**Use Cases**:
- 🔹 **Seller Onboarding**: Complete seller onboarding in one command
- 🔹 **Bootstrap**: Initialize first seller in system
- 🔹 **Testing**: Quick seller setup for testing
- 🔹 **Production**: Production seller activation workflow

**Delegation Chain**:
```yaml
action888()
  ↓
activateSeller() [InviteActions]
  ├→ activateUser() [contract interaction]
  ├→ grantSellerRole() [AccessControlActions]
  ├→ grantActivatorRole() [AccessControlActions]
  └→ generateAndMintInvitesForSeller()
  ↓
setupSoulIdentity() [AccessControlActions] (optional)
```

---

### **5. generateAmanitaInviteCodes() - Code Generation**

**Purpose**: Generate unique invite codes in AMANITA-XXXX-XXXX format

**Signature**:
```javascript
generateAmanitaInviteCodes(count)
```

**Algorithm**:
```yaml
Input: count (number of codes)
  ↓
Step 1: Generate random alphanumeric pairs
  ↓
Step 2: Format as AMANITA-XXXX-XXXX
  ↓
Step 3: Ensure uniqueness
  ↓
Output: Array of unique invite codes
```

**Key Features**:
- ✅ **Unique Format**: AMANITA-XXXX-XXXX pattern
- ✅ **Uniqueness**: Guaranteed code uniqueness
- ✅ **Random Generation**: Cryptographically secure generation
- ✅ **Branded**: Contains Amanita branding

---

### **4. activateUser() - User Activation**

**Purpose**: Activate user in system with new invite creation

**Signature**:
```javascript
async activateUser(spiralEngine, inviteCode, userAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, inviteCode, userAddress
  ↓
Step 1: Generate 12 new invites for user
  ↓
Step 2: Activate user on-chain
  ↓
Step 3: Return activation result
  ↓
Output: Activation result with new invites
```

**Key Features**:
- ✅ **User Activation**: Activate user in system
- ✅ **Invite Generation**: Create new invites for user
- ✅ **On-chain Storage**: Storage in SpiralEngine
- ✅ **Social Graph**: Build social graph

---

### **5. activateSeller() - Complete Seller Activation** ⭐ NEW

**Purpose**: Activate seller with complete setup (activation + SELLER_ROLE assignment)

**Signature**:
```javascript
async activateSeller(spiralEngine, inviteCode, sellerAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, inviteCode, sellerAddress
  ↓
Step 1: Check current status (activation + SELLER_ROLE)
  ↓
Step 2: If not activated → call activateUser()
  ↓
Step 3: Save seller invites via saveUserInvites(address, invites, 'seller')
  ↓
Step 4: If no SELLER_ROLE → delegate to AccessControlActions.grantSellerRole()
  ↓
Output: Complete activation result { success, wasActivated, wasRoleGranted, newInvites }
```

**Key Features**:
- ✅ **Idempotent**: Safe for repeated execution (checks status first)
- ✅ **Complete Setup**: Handles both activation AND role assignment
- ✅ **Delegation Pattern**: Delegates role assignment to AccessControlActions
- ✅ **Structured Result**: Returns detailed result with flags
- ✅ **File Persistence**: Saves seller invites with 'seller' suffix

**Return Structure**:
```javascript
{
  success: true,
  sellerAddress: '0xSeller',
  wasActivated: boolean,      // true if activated during this call
  wasRoleGranted: boolean,     // true if role granted during this call
  newInvites: ['INVITE1', ...],
  activationResult: { ... }    // Full activation result if activated
}
```

---

### **6. saveUserInvites() - Universal Invite Persistence** ⭐ NEW

**Purpose**: Universal method for saving invites for any user type

**Signature**:
```javascript
async saveUserInvites(userAddress, invites, suffix = null)
```

**Algorithm**:
```yaml
Input: userAddress, invites array, optional suffix
  ↓
Step 1: Determine filename based on userAddress and suffix
  ↓
Step 2: Create logs directory if not exists
  ↓
Step 3: Write invites to file
  ↓
Output: File path
```

**File Naming Logic**:
- `userAddress === 'deployer'` OR `suffix === null` → `deployer_invites_{network}.txt` (backward compatibility)
- `suffix !== null` → `{userAddress}_invites_{suffix}.txt` (new format)

**Key Features**:
- ✅ **Universal**: Works for deployer, seller, and any user type
- ✅ **Backward Compatible**: Preserves deployer file format
- ✅ **Flexible Naming**: Custom suffix support
- ✅ **Network Specific**: Different files for different networks

**Usage Examples**:
```javascript
// Deployer (backward compatible)
await saveUserInvites('deployer', invites);
// → bot/flowers/deployer_invites_localhost.txt

// Seller
await saveUserInvites('0xSeller', invites, 'seller');
// → bot/flowers/0xSeller_invites_seller.txt

// Custom
await saveUserInvites('0xUser', invites, 'activator');
// → bot/flowers/0xUser_invites_activator.txt
```

---

### **7. saveInvitesToFile() - File Persistence** [DEPRECATED]

**Purpose**: Legacy method for backward compatibility

**Signature**:
```javascript
async saveInvitesToFile(invites)
```

**Implementation**: Delegates to `saveUserInvites('deployer', invites)`

**Status**: ⚠️ Deprecated - Use `saveUserInvites()` instead

---

### **8. generateRandomAlphanumeric() - Random Generation**

**Purpose**: Generate random strings from letters and numbers

**Signature**:
```javascript
generateRandomAlphanumeric(length)
```

**Algorithm**:
```yaml
Input: length
  ↓
Step 1: Select random characters from charset
  ↓
Step 2: Build string of specified length
  ↓
Output: Random alphanumeric string
```

**Key Features**:
- ✅ **Cryptographically Secure**: Uses Math.random()
- ✅ **Alphanumeric**: Letters and numbers only
- ✅ **Configurable Length**: Configurable length
- ✅ **Helper Function**: Utility function

---

## 🔄 Data Flows

### **Main Flow (action777)**
```yaml
1. Contract Loading:
   ContractManager → SpiralEngine Instance
   
2. Access Validation:
   AccessControlActions.validateDeployerAccess()
   
3. Invite Generation:
   generateAmanitaInviteCodes(12) → Invite Codes
   
4. On-chain Minting:
   SpiralEngine.mintInvite() → Transaction
   
5. File Persistence:
   saveInvitesToFile() → File Path
```

### **User Activation Flow (activateUser)**
```yaml
1. Invite Generation:
   generateAmanitaInviteCodes(12) → New Invites
   
2. On-chain Activation:
   SpiralEngine.activateUser() → Transaction
   
3. Social Graph Update:
   User → Inviter relationship stored
   
4. Result Return:
   Activation result with new invites
```

### **Seller Activation Flow (activateSeller)** ⭐ NEW
```yaml
1. Status Check:
   SpiralEngine.usedInviteByUser() → Activation Status
   SpiralEngine.hasRole(SELLER_ROLE) → Role Status
   
2. Conditional Activation:
   If not activated → activateUser(spiralEngine, inviteCode, sellerAddress)
   
3. Invite Persistence:
   saveUserInvites(sellerAddress, newInvites, 'seller') → File Path
   
4. Conditional Role Assignment:
   If no SELLER_ROLE → AccessControlActions.grantSellerRole()
   
5. Result Return:
   { success, wasActivated, wasRoleGranted, newInvites }
```

### **Code Generation Flow (generateAmanitaInviteCodes)**
```yaml
1. Random Generation:
   generateRandomAlphanumeric(4) → Alpha
   generateRandomAlphanumeric(4) → Beta
   
2. Format Creation:
   "AMANITA-" + Alpha + "-" + Beta → Invite Code
   
3. Uniqueness Check:
   usedCodes.has(invite) → Unique Check
   
4. Array Building:
   invites.push(invite) → Final Array
```

---

## 🛡️ Architectural Principles

### **1. Layer 4A - Social Structure**
- **Social Foundation**: Foundation for social structure
- **Invite Management**: Invitation system management
- **User Activation**: User activation in system
- **Social Graph**: Social graph building

### **2. Delegation Pattern**
- **Access Control**: Delegates permission validation to AccessControlActions
- **Clean Architecture**: Clear separation of responsibilities
- **Single Responsibility**: Each module handles its own domain

### **3. Error Handling Strategy**
```yaml
Contract Operations: Fail fast (throw error)
File Operations: Graceful degradation
Code Generation: Ensure uniqueness
```

### **4. Data Persistence**
- **Dual Storage**: On-chain + file backup
- **Network Specific**: Different files for different networks
- **Transaction Safety**: Wait for transaction confirmation

### **5. Social Graph Management**
- **Invite Chain**: Invitation chain
- **User Relationships**: User relationships
- **Spiral Structure**: Spiral social structure

---

## 🔗 Integration Points

### **Incoming Dependencies**:
- **ContractManager**: SpiralEngine contract loading
- **EthersUtils**: Blockchain operations
- **Config**: Network configuration

### **Outgoing Connections**:
- **AccessControlActions**: Deployer permission validation
- **SpiralEngine**: Invite storage and social graph
- **File System**: Invite backup

### **Integration with Other Modules**:
```yaml
ComponentActions.action555() → InviteActions.activateSeller()
    ↓
Complete seller activation (activation + SELLER_ROLE + invites)
```

```yaml
InviteActions.activateSeller() → AccessControlActions.grantSellerRole()
    ↓
SELLER_ROLE assignment (Layer 3 delegation)
```

---

## 🎯 Critical Points

### **1. Social Structure Foundation**
```yaml
Root Invites → User Activation → New Invites → Social Graph
(Foundation) → (Growth) → (Expansion) → (Network)
```

**Rationale**: InviteActions creates the foundation for the entire social structure

### **2. Invite Code Format**
- **AMANITA-XXXX-XXXX**: Unique format with branding
- **Uniqueness**: Guaranteed code uniqueness
- **Random Generation**: Cryptographically secure generation

### **3. Dual Storage Strategy**
- **On-chain**: Primary storage in SpiralEngine
- **File Backup**: Backup in file
- **Network Specific**: Different files for different networks

### **4. User Activation Flow**
- **Invite Validation**: Validate invite validity
- **New Invite Generation**: Create new invites for user
- **Social Graph Update**: Update social graph

---

## 🚀 System Usage

### **Basic Usage**
```javascript
// Generate root invites
const result777 = await inviteActions.action777();

// Activate user
const activationResult = await inviteActions.activateUser(spiralEngine, inviteCode, userAddress);
```

### **Integration with Other Actions**
```javascript
// In ComponentActions for seller activation (UPDATED)
const activationResult = await this.inviteActions.activateSeller(
  spiralEngine,
  deployerInvite,
  sellerAddress
);
console.log(`Activated: ${activationResult.wasActivated}`);
console.log(`Role Granted: ${activationResult.wasRoleGranted}`);

// In DeployActions for root invite creation
await inviteActions.action777();

// Direct user activation (for non-sellers)
const userResult = await inviteActions.activateUser(spiralEngine, inviteCode, userAddress);
```

### **Testing**
```javascript
// Mock dependencies
const mockContractManager = { loadUUPSContract: sinon.stub() };
const mockEthersUtils = { getSigner: sinon.stub() };
const mockConfig = { get: sinon.stub() };

const inviteActions = new InviteActions(mockContractManager, mockEthersUtils, mockConfig);
```

---

## 📊 Metrics and Monitoring

### **Successful Invite Generation**
```yaml
Root Invites: 12 codes generated
Format: AMANITA-XXXX-XXXX
Storage: On-chain + file backup
Status: ✅ Social foundation ready
```

### **Successful User Activation**
```yaml
User Activated: 1 user
New Invites: 12 codes generated
Social Graph: Updated
Status: ✅ User ready for system
```

### **Error Handling**
```yaml
Contract Operations: Fail fast with detailed logging
File Operations: Graceful degradation
Code Generation: Ensure uniqueness
```

---

## 🔧 Configuration

### **Required .env Variables**
```yaml
# Network configuration
NETWORK_NAME: "localhost" # or "mainnet", "testnet"
```

### **File Storage**
```yaml
# Invite files stored in:
bot/flowers/deployer_invites_{network}.txt         # Deployer (via action777)
bot/flowers/{address}_invites_seller.txt           # Seller (via activateSeller)
bot/flowers/{address}_invites_{custom_suffix}.txt  # Custom users
```

---

## 🎉 Conclusion

**InviteActions** is a **critically important architectural layer** that creates the foundation for the ecosystem's social structure. 

### **Key Achievements**:
- ✅ **Social Foundation**: Foundation for spiral social structure
- ✅ **Invite Management**: Complete invitation system management
- ✅ **User Activation**: User activation with new invite creation
- ✅ **Dual Storage**: On-chain + file backup for reliability
- ✅ **Clean Architecture**: Clear separation of responsibilities

**Its proper operation determines the success of the entire social structure system.**

---

**Generated**: 2025-10-20T09:45:00Z  
**Updated**: 2025-10-20T10:30:00Z (Migration: Seller Activation Methods Added)  
**Methodology**: @analysis.mdc  
**Author**: AI Assistant  
**Status**: Production Ready

---

## 📝 Migration Notes (2025-10-20)

### **New Methods Added**:
- ⭐ `activateSeller()` - Complete seller activation with SELLER_ROLE
- ⭐ `saveUserInvites()` - Universal invite persistence

### **Changes**:
- `saveInvitesToFile()` marked as deprecated (delegates to `saveUserInvites()`)
- Added Layer 3 delegation to `AccessControlActions.grantSellerRole()`

### **Rationale**:
- Centralize ALL activation logic in InviteActions (Layer 4A)
- Remove seller activation from ComponentActions (Layer 5)
- Improve architectural separation of concerns

See: `scripts/docs/MIGRATION_SELLER_ACTIVATION.md` for full details

---

## 📚 See Also

### **Related Action Documentation**:
- **[Catalog.md](./Catalog.md)** - `action444()` Catalog Pipeline (run after seller initialization)
- **[Component.md](./Component.md)** - `action555()` Component upload (includes seller activation)
- **[AccessControl.md](./AccessControl.md)** - `action9()` Grant ACTIVATOR_ROLE, `action13()` Diagnose seller
- **[Deploy.md](./Deploy.md)** - `action1()` Initial deployment (creates root invites)

### **Pipeline Documentation**:
- **[CATALOG_PIPELINE.md](../CATALOG_PIPELINE.md)** - Full catalog pipeline (requires seller activation first)
- **[Deploy_Architecture.md](../Deploy_Architecture.md)** - Overall system architecture

### **Integration Points**:
```yaml
Invite Lifecycle:
  action777: Generate root invites (deployer)
    ↓
  action888: Full seller initialization
    ├→ activateUser() - Activate with invite
    ├→ grantSellerRole() - Grant SELLER_ROLE
    ├→ grantActivatorRole() - Grant ACTIVATOR_ROLE
    └→ generateAndMintInvitesForSeller() - Create 12 invites
    ↓
  action555: Upload components (Component.md) - optional
    ↓
  action444: Upload catalog (Catalog.md) - requires activated seller
    ↓
  action11: Generate additional invites (seller self-service)

Related Actions:
  - action9: Grant ACTIVATOR_ROLE manually (AccessControl.md)
  - action13: Check seller readiness (AccessControl.md)
```

### **Critical Dependencies**:
```yaml
Before Catalog Upload (action444):
  ✅ Required: action888() completed (seller activated + roles granted)
  ✅ Required: action777() completed (root invites generated)
  ⚠️ Optional: action555() completed (components uploaded)

Seller Self-Service:
  ✅ action11: Seller generates own invites (requires SELLER_ROLE)
```

---

**Generated**: 2025-10-27  
**Methodology**: @analysis.mdc  
**Version**: 2.0 (action888 added)  
**Author**: AI Assistant  
**Status**: Production Ready
