# 🏗️ SetupActions.js - Architectural Documentation

**Date**: 2025-10-20T09:15:00Z  
**Methodology**: @analysis.mdc  
**Version**: 1.0  
**Status**: Production

---

## 📋 General Concept

**SetupActions** is a **post-deployment configuration module** that establishes connections between already deployed smart contracts. This is a critically important layer that transforms a set of individual contracts into an integrated ecosystem.

### 🎯 Architectural Role

```yaml
Deployment Phase: Contracts are created in isolation
    ↓
Setup Phase: SetupActions establishes connections between them
    ↓
Production Phase: System works as a unified whole
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

**Principle**: Dependency Injection for loose coupling and easy testing

---

## 🚀 Public Actions

### **1. action2() - Re-setup System Connections**

**Purpose**: Re-run system setup for already deployed contracts (useful after node restart or configuration changes)

**Signature**:
```javascript
async action2()
```

**Algorithm**:
```yaml
Input: None (uses MagicRegistry to find contracts)
  ↓
Step 1: Load all system contracts from MagicRegistry
  ├→ SpiralEngine
  ├→ ProductRegistry
  ├→ OrganicComponentRegistry
  ├→ AmanitaInternational
  ├→ SoulIdentity
  └→ SoulboundCore contracts
  ↓
Step 2: Validate current system connections
  ├→ Check SBT ecosystem integration
  └→ Check registry connections
  ↓
Step 3: Re-run setupSystemConnections()
  ├→ Setup SBT ecosystem
  ├→ Setup OrganicComponentRegistry
  └→ Setup AmanitaInternational
  ↓
Output: {success: true}
```

**Key Features**:
- ✅ **Standalone Action**: Can be called independently via CLI
- ✅ **MagicRegistry-based**: Auto-discovers contract addresses
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Validation**: Checks connections before and after setup
- ✅ **Error Handling**: Clear error messages if contracts not deployed

**Use Cases**:
- 🔹 **After Node Restart**: Re-establish connections after Hardhat node restart
- 🔹 **Configuration Changes**: Apply new configuration to existing contracts
- 🔹 **Troubleshooting**: Fix broken contract connections
- 🔹 **Verification**: Verify system setup is correct

**Example Usage**:
```javascript
// Via CLI
node scripts/deploy_full.js --action 2

// Programmatic
const setupActions = new SetupActions(contractManager, config);
const result = await setupActions.action2();
```

**Prerequisites**:
- ✅ Action 1 must be completed (contracts deployed)
- ✅ MagicRegistry must be accessible
- ✅ All contracts must exist at registered addresses

**Error Scenarios**:
```yaml
Error 1: MagicRegistry not found
  → "MagicRegistry не существует по адресу {address}"
  → Solution: Run Action 1 first

Error 2: Contract not registered
  → "{ContractName} не зарегистрирован в MagicRegistry"
  → Solution: Run Action 1 first

Error 3: Setup validation failed
  → "Setup validation failed: {details}"
  → Solution: Check contract state and permissions
```

---

## 🚀 Core Methods

### **1. setupSystemConnections() - Main Orchestrator**

**Purpose**: Single entry point for complete system configuration

**Signature**:
```javascript
async setupSystemConnections(contracts = null)
```

**Algorithm**:
```yaml
Input: contracts (optional)
  ↓
Step 1: Load contracts (if not provided)
  ↓
Step 2: Setup SBT ecosystem
  ↓
Step 3: Setup OrganicComponentRegistry
  ↓
Output: Fully integrated system
```

**Key Features**:
- ✅ **Idempotent**: Can be called multiple times without side effects
- ✅ **Flexible**: Works with provided contracts or loads them independently
- ✅ **Atomic**: Either everything is configured or nothing
- ✅ **Error Handling**: Graceful degradation with detailed logging

---

### **2. loadSystemContracts() - Contract Loader**

**Purpose**: Centralized loading of all system contracts

**Signature**:
```javascript
async loadSystemContracts()
```

**Architectural Logic**:
```yaml
MagicRegistry (Single Source of Truth)
  ↓
├── UUPS Contracts (SpiralEngine, ProductRegistry, etc.)
└── Regular Contracts (SoulboundCore, SoulMetadata, etc.)
```

**Contract Classification**:
- **UUPS Contracts**: `['SpiralEngine', 'ProductRegistry', 'OrganicComponentRegistry', 'AmanitaInternational']`
- **Regular Contracts**: All others via MagicRegistry lookup

**Error Handling**: 
- ✅ Graceful degradation - if contract fails to load, system continues operation
- ✅ Detailed logging of successes and warnings
- ✅ Return partially loaded contracts object

---

### **3. setupSBTEcosystem() - SBT Integration**

**Purpose**: Configuration of Soulbound Token ecosystem

**Signature**:
```javascript
async setupSBTEcosystem(contracts)
```

**Architectural Schema**:
```yaml
SoulboundCore (Central Hub)
  ├── SoulMetadata (Metadata management)
  ├── SoulRecovery (Recovery mechanisms)  
  └── SoulIntegration (External integrations)
      ↓
SoulIdentity ← SpiralEngine (Cross-ecosystem connection)
```

**Setup Sequence**:
1. **SoulMetadata → SoulboundCore**: Metadata management
2. **SoulRecovery → SoulboundCore**: Recovery mechanisms
3. **SoulIntegration → SoulboundCore**: External integrations
4. **SoulIdentity → SpiralEngine**: Connection to main system

**Criticality**: SBT ecosystem must be configured first, as other modules depend on it

**Error Handling**: Fail fast - if SBT setup fails, entire operation is aborted

---

### **4. setupOrganicComponentRegistry() - Component System**

**Purpose**: Configuration of organic component management system

**Signature**:
```javascript
async setupOrganicComponentRegistry(contracts)
```

**Architectural Connection**:
```yaml
OrganicComponentRegistry ← SpiralEngine
    (Component management) ← (User management)
```

**Functionality**:
- **setSpiralEngine()**: Links component system with user management system
- **Access Control**: Requires ADMIN_ROLE for operation execution
- **Transaction Safety**: Waits for transaction confirmation

**Error Handling**: Fail fast - critical operation for component system functionality

---

## 🔄 Data Flows

### **Main Flow (setupSystemConnections)**
```yaml
1. Contract Loading:
   MagicRegistry → Contract Addresses → Contract Instances
   
2. SBT Setup:
   SoulboundCore ← [Metadata, Recovery, Integration]
   SpiralEngine ← SoulIdentity
   
3. Component Setup:
   OrganicComponentRegistry ← SpiralEngine
```

### **Contract Loading Flow (loadSystemContracts)**
```yaml
1. MagicRegistry Load:
   .env → MagicRegistry Address → Contract Instance
   
2. UUPS Contracts:
   Direct Loading → Contract Instances
   
3. Regular Contracts:
   MagicRegistry.get(name) → Address → Contract Instance
```

### **SBT Setup Flow (setupSBTEcosystem)**
```yaml
1. Contract Validation:
   Check soulboundCore && spiralEngine existence
   
2. Connection Setup:
   soulboundCore.setMetadataContract(soulMetadata)
   soulboundCore.setRecoveryContract(soulRecovery)
   soulboundCore.setIntegrationContract(soulIntegration)
   spiralEngine.setSoulIdentity(soulIdentity)
   
3. Transaction Confirmation:
   await tx.wait() for each connection
```

### **Component Setup Flow (setupOrganicComponentRegistry)**
```yaml
1. Contract Validation:
   Check organicComponentRegistry && spiralEngine existence
   
2. Connection Setup:
   organicComponentRegistry.setSpiralEngine(spiralEngine)
   
3. Transaction Confirmation:
   await tx.wait()
```

---

## 🛡️ Architectural Principles

### **1. Separation of Concerns**
- **Deployment**: Contract creation (separate process)
- **Setup**: Connection configuration (this module)
- **Runtime**: System usage (other modules)

### **2. Dependency Injection**
- All dependencies passed through constructor
- Easy testing and mocking
- Loose coupling of components

### **3. Error Handling Strategy**
```yaml
Contract Loading: Graceful degradation (warn + continue)
SBT Setup: Fail fast (throw error)
Component Setup: Fail fast (throw error)
```

### **4. Configuration Management**
- **Single Source of Truth**: MagicRegistry for contract addresses
- **Environment-based**: .env files for critical addresses
- **Fallback Strategy**: Graceful handling of missing contracts

### **5. Transaction Safety**
- All blockchain operations wait for confirmation
- Detailed logging of each transaction
- Rollback strategy through error propagation

---

## 🔗 Integration Points

### **Incoming Dependencies**:
- **ContractManager**: Contract loading
- **EthersUtils**: Blockchain operations
- **Config**: System configuration

### **Outgoing Connections**:
- **SBT Ecosystem**: Fully configured Soulbound system
- **Component System**: Integrated component system
- **Cross-ecosystem**: Connections between different subsystems

### **Integration with Other Modules**:
```yaml
Action 1: Complete system setup
  ↓
SetupActions.setupSystemConnections()
  ↓
Ready-to-use ecosystem
```

---

## 🎯 Critical Points

### **1. Setup Order**
```yaml
SBT Ecosystem → Component System
(Base infrastructure) → (Business logic)
```

**Rationale**: SBT system is the foundation for other modules

### **2. Access Control**
- **SBT Setup**: Requires deployer permissions
- **Component Setup**: Requires ADMIN_ROLE
- **Transaction Safety**: All operations wait for confirmation

### **3. Idempotency**
- ✅ Can be called multiple times
- ✅ Safe for re-setup
- ✅ Does not create duplicate connections

### **4. Error Recovery**
- **Contract Loading**: Continues with available contracts
- **SBT Setup**: Full rollback on error
- **Component Setup**: Full rollback on error

---

## 🚀 System Usage

### **Basic Usage**
```javascript
// In Action 1 (complete setup)
await setupActions.setupSystemConnections();

// In other Actions (with provided contracts)
await setupActions.setupSystemConnections(deployedContracts);

// For re-setup after changes
await setupActions.setupSystemConnections();
```

### **Integration with Actions**
```javascript
// In DeployActions after deployment
const deployedContracts = await deployActions.deployAll();
await setupActions.setupSystemConnections(deployedContracts);

// In other Actions for connection verification
const contracts = await setupActions.loadSystemContracts();
```

### **Testing**
```javascript
// Mock dependencies
const mockContractManager = { loadContract: sinon.stub(), loadUUPSContract: sinon.stub() };
const mockEthersUtils = { getSigner: sinon.stub() };
const mockConfig = { get: sinon.stub() };

const setupActions = new SetupActions(mockContractManager, mockEthersUtils, mockConfig);
```

---

## 📊 Metrics and Monitoring

### **Successful Setup**
```yaml
SBT Ecosystem: 4 connections established
Component System: 1 connection established
Total Contracts: 9 contracts loaded
Status: ✅ All systems operational
```

### **Error Handling**
```yaml
Contract Loading Errors: Graceful degradation
SBT Setup Errors: Fail fast with detailed logging
Component Setup Errors: Fail fast with detailed logging
```

---

## 🔧 Configuration

### **Required .env Variables**
```yaml
MAGIC_REGISTRY_CONTRACT_ADDRESS: "0x..."
```

### **Optional Variables**
```yaml
# All other addresses loaded via MagicRegistry
```

---

## 🎉 Conclusion

**SetupActions** is a **critically important architectural layer** that transforms a set of disparate contracts into an integrated, functional ecosystem. 

### **Key Achievements**:
- ✅ **Clean Architecture**: Separation of deployment and setup
- ✅ **Reliability**: Graceful error handling and transaction safety
- ✅ **Flexibility**: Support for various usage scenarios
- ✅ **Testability**: Dependency injection and mocking
- ✅ **Monitoring**: Detailed logging of all operations

**Its proper operation determines the success of the entire system.**

---

**Generated**: 2025-10-20T09:15:00Z  
**Methodology**: @analysis.mdc  
**Author**: AI Assistant  
**Status**: Production Ready
