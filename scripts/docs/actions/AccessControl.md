# 🏗️ AccessControlActions.js - Architectural Documentation

**Date**: 2025-10-20T10:00:00Z  
**Methodology**: @analysis.mdc  
**Version**: 1.0  
**Status**: Production

---

## 📋 General Concept

**AccessControlActions** is a **security and access control module (Layer 3)** that provides fundamental system security and the foundation for DAO governance. This is a critically important layer that protects the entire ecosystem from unauthorized access.

### 🎯 Architectural Role

```yaml
AccessControlActions: Security and Access Control (Layer 3)
    ↓
InviteActions: Deployer permission validation
    ↓
ComponentActions: Seller activation validation
    ↓
SpiralEngine: Role and permission storage
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

**Principle**: Layer 3 - Security Foundation

---

## 🚀 Core Methods

### **STANDALONE ACTIONS**

**Note on Action 10**: REDUNDANT - Use `grantSellerRole()` method directly (see Core Methods below).

#### **1. action9() - Grant ACTIVATOR_ROLE to Seller**

**Purpose**: Grant ACTIVATOR_ROLE to seller from config (enables seller to activate users)

**Signature**:
```javascript
async action9()
```

**Algorithm**:
```yaml
Input: Seller address from config
  ↓
Step 1: Get seller address from config (SELLER_ADDRESS)
  ↓
Step 2: Load SpiralEngine contract
  ↓
Step 3: Optional check - seller activation status (warning if not activated)
  ↓
Step 4: Delegate to grantActivatorRole() helper
  ↓
  Helper Flow:
    → Validate user address (not zero)
    → Get deployer signer
    → Call spiralEngine.grantRole(ACTIVATOR_ROLE, userAddress)
    → Wait for transaction
    → Verify role granted
  ↓
Output: {success, sellerAddress, roleGranted}
```

**Key Features**:
- ✅ **Standalone Action**: Can be called independently
- ✅ **Reuses Helper**: Delegates to grantActivatorRole()
- ✅ **Optional Validation**: Checks seller activation (warning only, doesn't block)
- ✅ **Deployer Authentication**: Uses deployer signer (admin privileges)
- ✅ **Verification**: Verifies role actually granted
- ✅ **Clear Logging**: Action start/progress/success pattern

**Configuration Keys**:
- `seller.address` - Seller Ethereum address (required)

**Use Cases**:
- 🔹 **Seller Empowerment**: Enable seller to activate their own users
- 🔹 **DAO Preparation**: Prepare seller for autonomous user management
- 🔹 **Delegation**: Deployer delegates activation rights to seller

**Example Output**:
```javascript
{
  success: true,
  sellerAddress: "0x1234...",
  roleGranted: "ACTIVATOR_ROLE"
}
```

**Differences from OLD Version**:
```yaml
OLD (deploy_full.js:3493-3512):
  - Function: grantActivatorRoleToSellerOnly()
  - Checks activation: Yes (warning)
  - Delegates to: grantActivatorRoleToSeller()
  - Technology: Web3.js

NEW (AccessControlActions.js:339-381):
  - Method: action9()
  - Checks activation: Yes (warning)
  - Delegates to: grantActivatorRole()
  - Technology: Ethers.js
  
Equivalence: ✅ FUNCTIONALLY IDENTICAL
```

**Error Scenarios**:
```yaml
Error 1: SELLER_ADDRESS not configured
  → Clear message: "SELLER_ADDRESS not configured"

Error 2: Zero address
  → Clear message: "AccessControl: User address не может быть zero address"

Error 3: Role grant failed
  → Clear message from grantActivatorRole()

Error 4: Verification failed
  → Clear message: "ACTIVATOR_ROLE не была назначена (verification failed)"
```

**Relation to Other Actions**:
```yaml
Action 888: Full seller initialization
  └── Includes grantActivatorRole() step
  
Action 9: Grant ACTIVATOR_ROLE only
  └── Uses same grantActivatorRole() helper ← SHARED

Code Reuse: grantActivatorRole() helper used by both ✅
```

---

#### **2. action13() - Diagnose Seller State**

**Purpose**: Comprehensive seller diagnostics including catalog info and readiness score

**Signature**:
```javascript
async action13()
```

**Algorithm**:
```yaml
Input: Seller address from config
  ↓
Step 1: Get seller address from config
  ↓
Step 2: Load contracts (SpiralEngine, ProductRegistry)
  ↓
Step 3: Get base diagnostics via getUserDiagnostics()
  ↓
  Base Diagnostics:
    → Check activation (usedInviteByUser)
    → Check roles (SELLER_ROLE, ACTIVATOR_ROLE)
    → Get activator address
  ↓
Step 4: Get catalog info from ProductRegistry
  ↓
  Catalog Check:
    → Get all seller products (getProductsBySeller)
    → Get active products (getAllActiveProductIds)
    → Calculate active/inactive counts
  ↓
Step 5: Calculate readiness score (0-5)
  ↓
  Readiness Checks:
    → Activated? (1 point)
    → Has SELLER_ROLE? (1 point)
    → Has ACTIVATOR_ROLE? (1 point)
    → Has catalog? (1 point)
    → Has active products? (1 point)
  ↓
Step 6: Pretty print summary with verdict
  ↓
Output: {success, diagnostics, readinessChecks, readinessScore, readinessPercent}
```

**Key Features**:
- ✅ **Comprehensive**: Activation + Roles + Catalog + Readiness
- ✅ **Extends getUserDiagnostics**: Adds catalog info on top
- ✅ **Readiness Score**: 0-5 score with percentage
- ✅ **Verdict**: "Fully ready" / "Partially ready" / "Not ready"
- ✅ **Error Tolerant**: Continues if catalog check fails
- ✅ **Clear Reporting**: Structured output with visual indicators

**Configuration Keys**:
- `seller.address` - Seller Ethereum address (required)

**Example Output**:
```javascript
{
  success: true,
  diagnostics: {
    address: "0x1234...",
    valid: true,
    activation: {
      activated: true,
      usedInviteTokenId: "1",
      activatedBy: "0xdeployer..."
    },
    roles: {
      SELLER_ROLE: true,
      ACTIVATOR_ROLE: true
    },
    catalog: {
      totalProducts: 17,
      activeProducts: 15,
      inactiveProducts: 2,
      hasCatalog: true
    }
  },
  readinessChecks: {
    activated: true,
    hasSellerRole: true,
    hasActivatorRole: true,
    hasCatalog: true,
    hasActiveProducts: true
  },
  readinessScore: 5,
  readinessPercent: 100
}
```

**Readiness Score Interpretation**:
```yaml
5/5 (100%): 🎉 Seller fully ready
  - Activated ✅
  - SELLER_ROLE ✅
  - ACTIVATOR_ROLE ✅
  - Has catalog ✅
  - Has active products ✅

3-4/5 (60-80%): ⚠️ Seller partially ready
  - Missing some components
  - Requires attention

0-2/5 (0-40%): ❌ Seller not ready
  - Critical components missing
  - Requires full setup
```

**Use Cases**:
- 🔹 **Debugging**: Quickly identify seller issues
- 🔹 **Monitoring**: Check seller readiness before operations
- 🔹 **Onboarding**: Verify seller setup complete

**Relation to getUserDiagnostics()**:
```yaml
getUserDiagnostics(): Base diagnostics
  - Activation status
  - Roles (SELLER_ROLE, ACTIVATOR_ROLE)
  - Activator address
  
action13(): Extended diagnostics
  - All from getUserDiagnostics() ✅
  + Catalog info (total, active, inactive)
  + Readiness score (0-5)
  + Readiness verdict
  
Pattern: action13() calls getUserDiagnostics() + extends ✅
```

---

### **VALIDATION & ROLE MANAGEMENT**

#### **3. validateDeployerAccess() - Deployer Permission Validation**

**Purpose**: Validate deployer permissions for invite generation

**Signature**:
```javascript
async validateDeployerAccess(spiralEngine)
```

**Algorithm**:
```yaml
Input: spiralEngine contract
  ↓
Step 1: Get deployer address from signer
  ↓
Step 2: Check SELLER_ROLE for deployer
  ↓
Step 3: Throw error if no role
  ↓
Output: Validation success or error
```

**Key Features**:
- ✅ **Security Critical**: Critically important security check
- ✅ **Role Validation**: SELLER_ROLE validation
- ✅ **Error Handling**: Detailed error messages
- ✅ **Foundation Security**: System security foundation

---

### **2. validateSellerAccess() - Seller Activation Validation**

**Purpose**: Validate seller activation before component upload

**Signature**:
```javascript
async validateSellerAccess(spiralEngine, sellerAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, sellerAddress
  ↓
Step 1: Check zero address
  ↓
Step 2: Check activation via usedInviteByUser
  ↓
Step 3: Throw error if not activated
  ↓
Output: Activation status or error
```

**Key Features**:
- ✅ **Activation Check**: Check activation via usedInviteByUser
- ✅ **Zero Address Protection**: Protection from zero address
- ✅ **Prerequisite Validation**: Prerequisite validation
- ✅ **Security Gate**: Security barrier for component upload

---

### **3. validateInviteCode() - Invite Code Validation**

**Purpose**: Validate invite code before user activation

**Signature**:
```javascript
async validateInviteCode(spiralEngine, inviteCode)
```

**Algorithm**:
```yaml
Input: spiralEngine, inviteCode
  ↓
Step 1: Validate invite code format
  ↓
Step 2: Check invite exists via inviteCodeExists
  ↓
Step 3: Get tokenId via inviteCodeToTokenId
  ↓
Step 4: Check if used via isInviteUsed
  ↓
Output: Validation result { exists, used, tokenId }
```

**Key Features**:
- ✅ **Format Validation**: Invite code format validation
- ✅ **Existence Check**: Check invite existence
- ✅ **Usage Check**: Check invite usage
- ✅ **Token ID**: Get token ID for invite

---

### **4. checkActivationStatus() - User Activation Check**

**Purpose**: Simple user activation status check

**Signature**:
```javascript
async checkActivationStatus(spiralEngine, userAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, userAddress
  ↓
Step 1: Check zero address
  ↓
Step 2: Get usedInvite via usedInviteByUser
  ↓
Step 3: Check if activated (usedInvite > 0)
  ↓
Output: Boolean activation status
```

**Key Features**:
- ✅ **Simple Check**: Simple activation check
- ✅ **Zero Address Protection**: Protection from zero address
- ✅ **Helper Function**: Utility function
- ✅ **Status Return**: Return activation status

---

### **5. grantSellerRole() - SELLER_ROLE Assignment**

**Purpose**: Assign SELLER_ROLE to activated user

**Signature**:
```javascript
async grantSellerRole(spiralEngine, userAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, userAddress
  ↓
Step 1: Check zero address
  ↓
Step 2: Check user activation (prerequisite)
  ↓
Step 3: Grant SELLER_ROLE on-chain
  ↓
Step 4: Verify role assignment
  ↓
Output: Role assignment success or error
```

**Key Features**:
- ✅ **Prerequisite Check**: Check activation as prerequisite
- ✅ **On-chain Role**: Assign role on blockchain
- ✅ **Verification**: Verify successful role assignment
- ✅ **Security Critical**: Critically important security operation

---

### **6. grantActivatorRole() - ACTIVATOR_ROLE Assignment**

**Purpose**: Assign ACTIVATOR_ROLE for activating invited users

**Signature**:
```javascript
async grantActivatorRole(spiralEngine, userAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, userAddress
  ↓
Step 1: Check zero address
  ↓
Step 2: Grant ACTIVATOR_ROLE on-chain
  ↓
Step 3: Verify role assignment
  ↓
Output: Role assignment success or error
```

**Key Features**:
- ✅ **Activator Permission**: Permission to activate users
- ✅ **On-chain Role**: Assign role on blockchain
- ✅ **Verification**: Verify successful role assignment
- ✅ **Social Structure**: Support social structure

---

### **7. getUserDiagnostics() - Complete User Diagnostics**

**Purpose**: Complete user diagnostics for debugging and monitoring

**Signature**:
```javascript
async getUserDiagnostics(spiralEngine, userAddress)
```

**Algorithm**:
```yaml
Input: spiralEngine, userAddress
  ↓
Step 1: Check zero address
  ↓
Step 2: Get activation status
  ↓
Step 3: Get role statuses
  ↓
Step 4: Get activator info
  ↓
Step 5: Format diagnostics
  ↓
Output: Complete user diagnostics object
```

**Key Features**:
- ✅ **Complete Diagnostics**: Complete user diagnostics
- ✅ **Activation Status**: Activation status
- ✅ **Role Status**: Role status
- ✅ **Activator Info**: Activator information
- ✅ **Debugging Support**: Debugging support

---

## 🔄 Data Flows

### **Main Validation Flow (validateDeployerAccess)**
```yaml
1. Signer Access:
   EthersUtils.getSigner() → Deployer Address
   
2. Role Check:
   SpiralEngine.SELLER_ROLE() → Role ID
   SpiralEngine.hasRole() → Boolean
   
3. Validation Result:
   Success or Error with details
```

### **Seller Validation Flow (validateSellerAccess)**
```yaml
1. Address Validation:
   Check zero address → Valid/Invalid
   
2. Activation Check:
   SpiralEngine.usedInviteByUser() → Token ID
   
3. Activation Status:
   Token ID > 0 → Activated
```

### **Invite Validation Flow (validateInviteCode)**
```yaml
1. Format Validation:
   String check → Valid/Invalid
   
2. Existence Check:
   SpiralEngine.inviteCodeExists() → Boolean
   
3. Usage Check:
   SpiralEngine.inviteCodeToTokenId() → Token ID
   SpiralEngine.isInviteUsed() → Boolean
   
4. Result:
   { exists, used, tokenId }
```

### **Role Assignment Flow (grantSellerRole)**
```yaml
1. Prerequisite Check:
   checkActivationStatus() → Activated
   
2. Role Assignment:
   SpiralEngine.grantSellerRole() → Transaction
   
3. Verification:
   SpiralEngine.hasRole() → Boolean
```

---

## 🛡️ Architectural Principles

### **1. Layer 3 - Security Foundation**
- **Security Critical**: Critically important security
- **Access Control**: Access control and roles
- **Permission Validation**: Permission validation
- **DAO Governance**: Foundation for DAO governance

### **2. Zero Address Protection**
- **Input Validation**: Input data validation
- **Zero Address Check**: Zero address check
- **Security Gate**: Security barrier
- **Error Prevention**: Error prevention

### **3. Prerequisite Validation**
- **Activation Check**: Check activation before role assignment
- **Role Dependencies**: Role dependencies
- **Security Chain**: Security chain
- **Fail Fast**: Fast failure on errors

### **4. On-chain Verification**
- **Blockchain Storage**: Role storage on blockchain
- **Transaction Safety**: Transaction safety
- **Verification**: Operation success verification
- **Immutable Security**: Immutable security

### **5. Comprehensive Diagnostics**
- **Complete Status**: Complete user status
- **Debugging Support**: Debugging support
- **Monitoring**: System monitoring
- **Troubleshooting**: Troubleshooting

---

## 🔗 Integration Points

### **Incoming Dependencies**:
- **ContractManager**: SpiralEngine contract loading
- **EthersUtils**: Blockchain operations and signer
- **Config**: System configuration

### **Outgoing Connections**:
- **SpiralEngine**: Role and permission storage
- **InviteActions**: Deployer permission validation
- **ComponentActions**: Seller activation validation

### **Integration with Other Modules**:
```yaml
InviteActions.action777() → AccessControlActions.validateDeployerAccess()
    ↓
Deployer permission validation
```

```yaml
ComponentActions.activateSellerBasic() → AccessControlActions.validateSellerAccess()
    ↓
Seller activation validation
```

---

## 🎯 Critical Points

### **1. Security Foundation**
```yaml
Access Control → Role Management → Permission Validation → System Security
(Security) → (Governance) → (Validation) → (Protection)
```

**Rationale**: AccessControlActions creates the security foundation for the entire system

### **2. Role Hierarchy**
- **SELLER_ROLE**: Basic role for sellers
- **ACTIVATOR_ROLE**: Role for user activation
- **DEFAULT_ADMIN_ROLE**: Administrative role (in SpiralEngine)
- **Role Dependencies**: Role dependencies

### **3. Prerequisite Chain**
- **Activation First**: Activation before role assignment
- **Role Assignment**: Role assignment after activation
- **Verification**: Operation success verification
- **Security Chain**: Security chain

### **4. Zero Address Protection**
- **Input Validation**: Validate all input addresses
- **Zero Address Check**: Check zero address
- **Error Prevention**: Error prevention
- **Security Gate**: Security barrier

---

## 🚀 System Usage

### **Basic Usage**
```javascript
// Validate deployer permissions
await accessControl.validateDeployerAccess(spiralEngine);

// Validate seller activation
await accessControl.validateSellerAccess(spiralEngine, sellerAddress);

// Assign SELLER_ROLE
await accessControl.grantSellerRole(spiralEngine, userAddress);
```

### **Integration with Other Actions**
```javascript
// In InviteActions for deployer permission validation
await accessControl.validateDeployerAccess(spiralEngine);

// In ComponentActions for seller activation validation
await accessControl.validateSellerAccess(spiralEngine, sellerAddress);
```

### **Diagnostics and Debugging**
```javascript
// Complete user diagnostics
const diagnostics = await accessControl.getUserDiagnostics(spiralEngine, userAddress);

// Check activation status
const isActivated = await accessControl.checkActivationStatus(spiralEngine, userAddress);
```

---

## 📊 Metrics and Monitoring

### **Successful Permission Validation**
```yaml
Deployer Access: ✅ SELLER_ROLE validated
Seller Access: ✅ User activated
Invite Validation: ✅ Code valid and unused
Status: ✅ Security gates passed
```

### **Successful Role Assignment**
```yaml
SELLER_ROLE: ✅ Role assigned and verified
ACTIVATOR_ROLE: ✅ Role assigned and verified
Verification: ✅ On-chain verification passed
Status: ✅ User ready for system operations
```

### **Error Handling**
```yaml
Access Denied: Detailed error messages with solutions
Role Assignment: Prerequisite validation and verification
Zero Address: Protection and error prevention
```

---

## 🔧 Configuration

### **Required .env Variables**
```yaml
# No specific .env variables required
# Uses standard blockchain configuration
```

### **Role Management**
```yaml
# Roles managed in SpiralEngine contract:
SELLER_ROLE: Basic seller role
ACTIVATOR_ROLE: User activation role
DEFAULT_ADMIN_ROLE: Administrative role
```

---

## 🎉 Conclusion

**AccessControlActions** is a **critically important architectural security layer** that provides fundamental protection for the entire ecosystem. 

### **Key Achievements**:
- ✅ **Security Foundation**: Foundation for entire system security
- ✅ **Access Control**: Complete access control and role management
- ✅ **Permission Validation**: Validation of all permissions
- ✅ **DAO Governance**: Foundation for DAO governance
- ✅ **Zero Address Protection**: Protection from zero address
- ✅ **Comprehensive Diagnostics**: Complete diagnostics for debugging

**Its proper operation determines the security of the entire system and the possibility of DAO governance.**

---

**Generated**: 2025-10-20T10:00:00Z  
**Methodology**: @analysis.mdc  
**Author**: AI Assistant  
**Status**: Production Ready
