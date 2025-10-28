# 🏗️ ComponentActions.js - Architectural Documentation

**Date**: 2025-10-20T10:15:00Z  
**Methodology**: @analysis.mdc  
**Version**: 1.0  
**Status**: Production

---

## 📋 General Concept

**ComponentActions** is a **component management module (Layer 5)** that provides the complete lifecycle of seller activation and organic component upload to Arweave and blockchain. This is a high-level orchestrator that coordinates the work of all underlying layers.

### 🎯 Architectural Role

```yaml
ComponentActions: Component Upload and Management (Layer 5)
    ↓
InviteActions: Seller activation with invites (Layer 4A)
    ↓
AccessControlActions: Permission validation (Layer 3)
    ↓
Arweave + Blockchain: Decentralized storage + contracts
```

---

## 🔧 Class Structure

### **Constructor and Dependencies**
```javascript
constructor(contractManager, arweaveManager, ethersUtils, config)
```

**Dependencies**:
- **contractManager**: Contract loading and management
- **arweaveManager**: Arweave storage management
- **ethersUtils**: Blockchain operations and signer management  
- **config**: Configuration from .env files

**Principle**: Layer 5 - High-Level Orchestration

---

## 🚀 Core Methods

### **1. action555() - Seller Activation + Component Upload**

**Purpose**: Complete lifecycle of seller activation and component upload

**Signature**:
```javascript
async action555()
```

**Algorithm**:
```yaml
Input: Environment variables (DEPLOYER_INVITE, SELLER_ADDRESS, DRY_RUN, ARWEAVE)
  ↓
Step 1: Load SpiralEngine contract
  ↓
Step 2: Activate seller (delegate to InviteActions.activateSeller) ⭐ UPDATED
  ↓
Step 3: Upload components (delegate to uploadComponentsCore)
  ↓
Output: Upload results with statistics
```

**Key Features**:
- ✅ **Complete Workflow**: Full workflow from activation to upload
- ✅ **Environment Configuration**: Configuration from environment variables
- ✅ **Error Handling**: Detailed error handling at each stage
- ✅ **Detailed Reporting**: Final report with statistics

---

### **2. uploadComponentsCore() - Component Upload Router**

**Purpose**: Router for selecting component upload mode (Full/Quick)

**Signature**:
```javascript
async uploadComponentsCore(sellerAddress, componentsDir, networkName, dryRun, withArweave)
```

**Algorithm**:
```yaml
Input: sellerAddress, componentsDir, networkName, dryRun, withArweave
  ↓
Step 1: Log configuration
  ↓
Step 2: Route based on withArweave flag
  ↓
  withArweave=true → uploadComponentFull()
  withArweave=false → Quick mode (not implemented)
  ↓
Output: Upload results
```

**Key Features**:
- ✅ **Mode Selection**: Select upload mode
- ✅ **Configuration Logging**: Detailed configuration logging
- ✅ **Future Extensibility**: Ready for Quick mode
- ✅ **Router Pattern**: Clear mode separation

---

### **3. uploadComponentFull() - Full Component Upload**

**Purpose**: Full component upload to Arweave + contract registration

**Signature**:
```javascript
async uploadComponentFull(sellerAddress, componentsDir, networkName, dryRun)
```

**Algorithm**:
```yaml
Input: sellerAddress, componentsDir, networkName, dryRun
  ↓
Step 1: Initialize Arweave (via Arweave-Readiness.js)
  ↓
Step 2: Prepare contracts (OrganicRegistry, AmanitaIntl, SpiralEngine)
  ↓
Step 3: Find components in directory
  ↓
Step 4: Process each component:
  ↓
  4.1: Upload Simple Fields to Arweave
  4.2: Upload Complex Fields to Arweave
  4.3: Upload Shareable Data (first component only)
  4.4: Update Root Metadata
  4.5: Upload Root Metadata to Arweave
  4.6: Register component in contract
  ↓
Step 5: Generate final report
  ↓
Output: Results with statistics
```

**Key Features**:
- ✅ **Complete Pipeline**: Full upload pipeline
- ✅ **Arweave Integration**: Integration with Arweave storage
- ✅ **State Management**: Upload state management
- ✅ **Resumable**: Support for resuming after failures
- ✅ **Multi-step Process**: 6-step upload process
- ✅ **Error Recovery**: Continue after errors
- ✅ **Detailed Reporting**: Detailed report per component

---

## 🔄 Data Flows

### **Main Flow (action555)**
```yaml
1. Environment Configuration:
   process.env → DEPLOYER_INVITE, SELLER_ADDRESS, DRY_RUN, ARWEAVE
   
2. Contract Loading:
   ContractManager.loadUUPSContract('SpiralEngine') → SpiralEngine Instance
   
3. Seller Activation:
   InviteActions.activateSeller() → Seller Activated + SELLER_ROLE ⭐ UPDATED
   
4. Component Upload:
   uploadComponentsCore() → Upload Results
   
5. Final Report:
   Statistics + Results
```

### **Seller Activation Flow (via InviteActions.activateSeller)** ⭐ UPDATED
```yaml
1. Delegation to InviteActions:
   ComponentActions.action555() → InviteActions.activateSeller()
   
2. InviteActions executes:
   - Check usedInviteByUser() and hasRole(SELLER_ROLE)
   - If not activated → activateUser()
   - saveUserInvites(sellerAddress, newInvites, 'seller')
   - If no role → AccessControlActions.grantSellerRole()
   
3. Return to ComponentActions:
   activationResult → { wasActivated, wasRoleGranted, newInvites }
```

**Note**: `activateSellerBasic()` and `saveSellerInvites()` removed from ComponentActions.
All seller activation logic now in InviteActions (Layer 4A).

### **Component Upload Flow (uploadComponentFull)**
```yaml
1. Arweave Initialization:
   Arweave-Readiness → Key, Client, Connection, Wallet
   
2. Contract Preparation:
   ContractManager → OrganicRegistry, AmanitaIntl, SpiralEngine
   
3. Component Discovery:
   fs.readdirSync() → Component IDs
   
4. Component Processing:
   For each component:
     → Upload Simple Fields (Arweave)
     → Upload Complex Fields (Arweave)
     → Upload Shareable Data (Arweave, first component only)
     → Update Root Metadata
     → Upload Root Metadata (Arweave)
     → Register Component (Contract)
   
5. Results Aggregation:
   Success/Fail counts + Detailed results
```

---

## 🛡️ Architectural Principles

### **1. Layer 5 - High-Level Orchestration**
- **Complete Workflows**: Full workflows from start to finish
- **Delegation Pattern**: Delegate specialized tasks
- **Error Recovery**: Recover from errors
- **Detailed Reporting**: Detailed reporting

### **2. Idempotent Operations**
- **Status Checking**: Check state before action
- **Conditional Execution**: Execute only if needed
- **Safe Retry**: Safe for repeated execution
- **State Management**: Upload state management

### **3. Multi-Layer Integration**
- **InviteActions**: User activation (Layer 4A)
- **AccessControlActions**: Permission validation (Layer 3)
- **Arweave**: Decentralized storage
- **Blockchain**: Smart contracts

### **4. Resumable Processing**
- **State Persistence**: Save state to files
- **Step Tracking**: Track completed steps
- **Step Skipping**: Skip completed steps
- **Crash Recovery**: Recover from crashes

### **5. Error Handling Strategy**
```yaml
Component-Level: Continue on error, aggregate results
Seller Activation: Fail fast with detailed messages
Arweave Operations: Fail fast with connection/balance checks
Contract Operations: Fail fast with validation
```

---

## 🔗 Integration Points

### **Incoming Dependencies**:
- **ContractManager**: Contract loading (OrganicRegistry, AmanitaIntl, SpiralEngine)
- **ArweaveManager**: Arweave management (not used directly in current implementation)
- **EthersUtils**: Blockchain operations and signers
- **Config**: Configuration from .env files

### **Outgoing Connections**:
- **InviteActions**: Activate seller via activateSeller() ⭐ UPDATED
- **Arweave-Readiness**: Arweave initialization and validation
- **upload_steps**: Component upload steps
- **upload_utils**: Upload utilities
- **state_manager**: State management

### **Integration with Other Modules**:
```yaml
ComponentActions.action555() → InviteActions.activateSeller() ⭐ UPDATED
    ↓
Complete seller activation (activation + SELLER_ROLE + invites)
```

```yaml
ComponentActions.uploadComponentFull() → upload_steps.*
    ↓
Arweave uploads + Contract registration
```

---

## 🎯 Critical Points

### **1. Complete Workflow Orchestration**
```yaml
Seller Activation → Component Upload → Contract Registration → Final Report
(Layer 4A) → (Arweave) → (Blockchain) → (Statistics)
```

**Rationale**: ComponentActions coordinates all system layers

### **2. Delegation Pattern**
- **InviteActions**: User activation
- **AccessControlActions**: Permission validation (indirectly via InviteActions)
- **upload_steps**: Component upload steps
- **state_manager**: State management

### **3. Resumable Upload Process**
- **State Files**: JSON files with state for each component
- **Step Tracking**: `steps_completed` array
- **Step Skipping**: Skip completed steps
- **Crash Recovery**: Resume from last successful step

### **4. Multi-step Component Upload**
```yaml
1. Simple Fields → Arweave CIDs
2. Complex Fields → Arweave CIDs
3. Shareable Data → Arweave (first component only)
4. Root Metadata → Updated with CIDs
5. Root Metadata → Arweave CID
6. Component Registration → Contract ID
```

### **5. Error Recovery Strategy**
- **Component-Level**: Continue after errors
- **Results Aggregation**: Collect successful and failed results
- **Detailed Logging**: Detailed error logging
- **Final Report**: Complete report with errors

---

## 🚀 System Usage

### **Basic Usage**
```javascript
// Action 555: Seller activation + component upload
const result = await componentActions.action555();

// Result structure
{
  success: true,
  uploadResults: {
    successCount: 10,
    failCount: 0,
    totalCount: 10,
    results: [...]
  }
}
```

### **Direct Seller Activation** ⭐ MIGRATED
```javascript
// ❌ OLD (removed from ComponentActions):
// await componentActions.activateSellerBasic(spiralEngine, sellerAddress, deployerInvite);

// ✅ NEW (use InviteActions directly):
const inviteActions = new InviteActions(contractManager, ethersUtils, config);
const activationResult = await inviteActions.activateSeller(
  spiralEngine,
  deployerInvite,
  sellerAddress
);
console.log(`Activated: ${activationResult.wasActivated}`);
console.log(`Role Granted: ${activationResult.wasRoleGranted}`);
```

### **Direct Component Upload**
```javascript
// Upload components directly (full mode)
const uploadResults = await componentActions.uploadComponentFull(
  sellerAddress,
  'data/components',
  'localhost',
  false // dryRun
);
```

---

## 📊 Metrics and Monitoring

### **Successful Seller Activation**
```yaml
Seller Activated: ✅ User activated via InviteActions
SELLER_ROLE: ✅ Role assigned
Invites Saved: ✅ File created
Status: ✅ Seller ready for component registration
```

### **Successful Component Upload**
```yaml
Components Processed: 10
Success: 10
Failures: 0
Arweave: ✅ FULL UPLOAD mode
State Management: ✅ Resumable process
Status: ✅ All components registered
```

### **Error Handling**
```yaml
Seller Activation: Detailed error messages with context
Arweave Connection: Fail fast with connection/balance checks
Component Upload: Component-level errors, continue processing
Final Report: Aggregated success/fail counts
```

---

## 🔧 Configuration

### **Environment Variables**
```yaml
# Required for action555
DEPLOYER_INVITE: Root invite code from action777
SELLER_ADDRESS: Seller Ethereum address
SELLER_PRIVATE_KEY: Seller private key for signing

# Optional
DRY_RUN: "true" for dry-run mode (default: false)
ARWEAVE: "false" for quick mode (default: true, full upload)
```

### **Directory Structure**
```yaml
# Components directory
data/components/
  └── component-name/
      ├── component-name.json (root metadata)
      ├── simple_fields/
      ├── complex_fields/
      └── state.component-name.localhost.json (state file)

# Invites directory (UPDATED - now managed by InviteActions)
bot/flowers/
  └── {sellerAddress}_invites_seller.txt  ⭐ UPDATED (was: _invites_action555.txt)
```

---

## 🔄 Upload Process Details

### **6-Step Upload Pipeline**
```yaml
Step 1: Simple Fields Upload
  - Upload simple field files to Arweave
  - Generate CIDs for each field
  - Update state with simple_fields_uploaded

Step 2: Complex Fields Upload
  - Upload complex field files to Arweave
  - Generate CIDs for each field
  - Update state with complex_fields_uploaded

Step 3: Shareable Data Upload (first component only)
  - Upload shared data to Arweave
  - Used across multiple components
  - Update state with shareable_data_uploaded

Step 4: Root Metadata Update
  - Merge CIDs into root metadata
  - Prepare final metadata structure
  - Update state with root_metadata_updated

Step 5: Root Metadata Upload
  - Upload final metadata to Arweave
  - Generate root CID
  - Update state with root_metadata_uploaded

Step 6: Component Registration
  - Register component in OrganicComponentRegistry
  - Store root CID on-chain
  - Update state with component_registered
```

### **State Management**
```json
{
  "componentId": "component-name",
  "network": "localhost",
  "created_at": "2025-10-20T10:00:00Z",
  "steps_completed": [
    "simple_fields_uploaded",
    "complex_fields_uploaded",
    "shareable_data_uploaded",
    "root_metadata_updated",
    "root_metadata_uploaded",
    "component_registered"
  ],
  "simple_fields": { "field1": "CID1", "field2": "CID2" },
  "complex_fields": { "field3": "CID3" },
  "root_metadata": {
    "cid": "RootCID",
    "data": { /* metadata */ }
  },
  "contract_registration": {
    "componentId": "1",
    "txHash": "0x..."
  }
}
```
---

## 🎉 Conclusion

**ComponentActions** is a **high-level architectural orchestrator** that provides the complete component management lifecycle. 

### **Key Achievements**:
- ✅ **Complete Workflows**: Full workflows from activation to upload
- ✅ **Multi-Layer Orchestration**: Coordinate all system layers
- ✅ **Resumable Processing**: Resumable upload with state management
- ✅ **Error Recovery**: Continue after component-level errors
- ✅ **Delegation Pattern**: Clear delegation of specialized tasks
- ✅ **Idempotent Operations**: Safe for repeated execution

**Its proper operation determines the success of the entire component upload process.**

---

**Generated**: 2025-10-20T10:15:00Z  
**Updated**: 2025-10-20T10:30:00Z (Migration: Seller Activation Delegated to InviteActions)  
**Methodology**: @analysis.mdc  
**Author**: AI Assistant  
**Status**: Production Ready

---

## 📝 Migration Notes (2025-10-20)

### **Removed Methods** (Migrated to InviteActions):
- ❌ `activateSellerBasic()` → Use `InviteActions.activateSeller()`
- ❌ `saveSellerInvites()` → Use `InviteActions.saveUserInvites()`

### **Updated Methods**:
- ⭐ `action555()` now delegates to `InviteActions.activateSeller()`
- Improved logging with `wasActivated` and `wasRoleGranted` flags

### **Rationale**:
- ComponentActions (Layer 5) is now pure orchestrator
- All seller activation logic centralized in InviteActions (Layer 4A)
- Better architectural separation of concerns

See: `scripts/docs/MIGRATION_SELLER_ACTIVATION.md` for full details

