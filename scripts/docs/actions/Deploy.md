# Deploy Actions Documentation

**Module**: `scripts/lib/actions/DeployActions.js`  
**Purpose**: Handles contract deployment operations  
**Layer**: 1 (Deployment)

---

## Overview

DeployActions encapsulates all deployment-related actions from the legacy `deploy_full.js`, providing a clean interface for contract deployment with automatic type detection (UUPS, SBT, regular) and registry integration.

---

## Core Methods

### **1. action5() - Deploy Single Contract by Name**

**Purpose**: Deploy a specific contract without full system deployment (selective redeploy)

**Signature**:
```javascript
async action5(contractName)
```

**Algorithm**:
```yaml
Input: contractName (string) or from config
  ↓
Step 1: Validate contract name
  → If not provided: try config.get('deployment.contractName')
  → If still missing: throw error
  ↓
Step 2: Load MagicRegistry (optional)
  → Try to load existing MagicRegistry
  → If not found: warn (contract won't be registered)
  ↓
Step 3: Deploy contract
  → Call contractManager.deploySingleContract(contractName, {registry})
  → Auto-detects type (UUPS, SBT, regular)
  → Handles all deployment logic
  ↓
Step 4: Print .env format
  → Format: CONTRACT_NAME_CONTRACT_ADDRESS=0x...
  ↓
Output: {success, contractName, contract, address, registered}
```

**Key Features**:
- ✅ **Flexible Input**: Accept contractName as parameter or from config
- ✅ **Auto Type Detection**: UUPS, SBT, or regular (via ContractManager)
- ✅ **Optional Registration**: Works with or without MagicRegistry
- ✅ **Idempotent**: Checks if contract exists before redeploying
- ✅ **.env Output**: Prints address in .env format for easy copy

**Configuration Keys**:
- `deployment.contractName` - Contract name (fallback if not passed as parameter)

**Use Cases**:
- 🔹 **Selective Redeploy**: Redeploy single contract after bug fix
- 🔹 **Testing**: Deploy specific contract for isolated testing
- 🔹 **Recovery**: Redeploy failed contract without full deployment

**Example Usage**:
```javascript
// Via parameter
await actionsManager.executeAction(5, 'SpiralEngine');

// Via config
config.set('deployment.contractName', 'ProductRegistry');
await actionsManager.executeAction(5);
```

**Example Output**:
```javascript
{
  success: true,
  contractName: 'SpiralEngine',
  contract: Contract { ... },
  address: '0x5FbDB2315678afecb367f032d93F642f64180aa3',
  registered: true
}

// Console output:
// SPIRALENGINE_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
```

**Supported Contracts** (auto-detected via ContractManager):
```yaml
UUPS:
  - SpiralEngine
  - ProductRegistry
  - OrganicComponentRegistry
  - AmanitaInternational

SBT (with dynamic dependencies):
  - SoulboundCore
  - SoulMetadata
  - SoulRecovery
  - SoulIntegration
  - SoulIdentity

Regular:
  - MagicRegistry
  - Lovecoin
  - Orders
  - AmanitaGovToken
  - AmanitaToken
  - AmanitaPaymentRouter
  - LoveDoPostNFT
  - LoveEmissionEngine
```

**Error Scenarios**:
```yaml
Error 1: Contract name not provided
  → Clear message: "Contract name not provided. Use: action5(contractName) or set deployment.contractName in config"

Error 2: Unknown contract
  → ContractManager throws: "Contract artifact not found: {contractName}"

Error 3: Deployment failure
  → ContractManager throws with specific error
  → Logs: "Failed to deploy single contract {contractName}: {error}"

Warning 1: MagicRegistry not found
  → Warning: "MagicRegistry not found - contract will not be registered"
  → Continues with deployment (registered: false)
```

---

### **2. action0() - Deploy MagicRegistry**

**Purpose**: Deploy MagicRegistry contract (first step in full deployment)

**Signature**:
```javascript
async action0()
```

**Algorithm**:
```yaml
Input: None
  ↓
Step 1: Deploy MagicRegistry
  → Call contractManager.deploySingleContract('MagicRegistry')
  → No constructor args
  → Not UUPS
  ↓
Step 2: Print .env format
  → MAGIC_REGISTRY_CONTRACT_ADDRESS=0x...
  ↓
Output: {success, contract, address}
```

**Key Features**:
- ✅ **Entry Point**: First contract to deploy
- ✅ **No Dependencies**: Can be deployed standalone
- ✅ **.env Output**: Prints address for configuration

**Example Output**:
```javascript
{
  success: true,
  contract: Contract { ... },
  address: '0x5FbDB2315678afecb367f032d93F642f64180aa3'
}
```

---

### **3. action1() - Deploy All Contracts + Setup**

**Purpose**: Full system deployment with all contracts and setup connections

**Signature**:
```javascript
async action1()
```

**Algorithm**:
```yaml
Input: None
  ↓
Step 1: Deploy MagicRegistry
  ↓
Step 2: Deploy SpiralEngine (UUPS)
  → Registers in MagicRegistry
  ↓
Step 3: Deploy SBT Ecosystem (5 contracts)
  → SoulboundCore → SoulMetadata → SoulRecovery → SoulIntegration → SoulIdentity
  → Respects dependencies
  ↓
Step 4: Deploy ProductRegistry (UUPS)
  ↓
Step 5: Deploy OrganicComponentRegistry (UUPS)
  ↓
Step 6: Deploy AmanitaInternational (UUPS)
  ↓
Step 7: Delegate to SetupActions.setupSystemConnections()
  → Connects all contracts
  ↓
Output: {success, contracts: {...all contracts}}
```

**Key Features**:
- ✅ **Full Deployment**: All 12 core contracts
- ✅ **Dependency Management**: Correct deployment order
- ✅ **Auto Setup**: Calls SetupActions after deployment
- ✅ **Registry Integration**: All contracts registered in MagicRegistry

**Example Output**:
```javascript
{
  success: true,
  contracts: {
    magicRegistry: Contract { ... },
    spiralEngine: Contract { ... },
    soulboundCore: Contract { ... },
    // ... all contracts
  }
}
```

---

## Architecture

### Layer 1: Deployment

```yaml
DeployActions:
  Purpose: Contract deployment
  Dependencies:
    - ContractManager (deployment logic)
    - EthersUtils (signer management)
    - Config (configuration)
    - SetupActions (post-deployment setup)
  
  Actions:
    - action0(): Deploy MagicRegistry
    - action1(): Deploy all + setup
    - action5(contractName): Deploy single contract
```

### Delegation Pattern

```yaml
DeployActions → ContractManager:
  - deploySingleContract(contractName, options)
    → Auto-detects contract type
    → Handles UUPS, SBT, regular deployment
    → Registers in MagicRegistry

DeployActions → SetupActions:
  - setupSystemConnections()
    → Connects deployed contracts
    → Grants initial roles
```

---

## Error Handling

### Common Errors

```yaml
Error 1: Artifact not found
  Cause: Contract not compiled
  Solution: Run `npx hardhat compile`

Error 2: Deployment out of gas
  Cause: Insufficient gas limit
  Solution: Check ContractManager gas settings

Error 3: MagicRegistry not found (action5)
  Cause: MagicRegistry not deployed yet
  Impact: Contract won't be registered (warning, not error)
  Solution: Deploy MagicRegistry first (action0) or ignore warning

Error 4: Contract already exists
  Cause: Contract deployed before
  Behavior: ContractManager returns existing instance (idempotent)
```

---

## Best Practices

### 1. Deployment Order

```yaml
Correct Order:
  1. action0() - Deploy MagicRegistry
  2. action1() - Deploy all contracts + setup
  3. action5(contractName) - Selective redeploy (if needed)

Skip MagicRegistry:
  - action5() can work without MagicRegistry
  - Contract won't be registered (warning only)
```

### 2. Selective Redeploy

```yaml
Scenario: Bug fix in ProductRegistry
  Step 1: Fix contract code
  Step 2: Compile: npx hardhat compile
  Step 3: Redeploy: action5('ProductRegistry')
  Step 4: Update .env with new address
  Step 5: Test integration
```

### 3. Configuration

```yaml
Required .env:
  - DEPLOYER_PRIVATE_KEY (for deployment)
  - MAGIC_REGISTRY_CONTRACT_ADDRESS (for action5 registry integration)

Optional .env:
  - deployment.contractName (fallback for action5)
```

---

## Integration Points

### Upstream (triggers DeployActions)

```yaml
User:
  - CLI: node deploy_full_new.js 5 SpiralEngine
  - Script: actionsManager.executeAction(5, 'SpiralEngine')
```

### Downstream (called by DeployActions)

```yaml
ContractManager:
  - deploySingleContract(contractName, options)
  - loadContract(contractName)

SetupActions:
  - setupSystemConnections() (called by action1)
```

---

## Testing

### Unit Tests

**File**: `scripts/tests/unit/actions/DeployActions.test.js`

**Coverage**:
- ✅ action0() - MagicRegistry deployment
- ✅ action1() - Full deployment
- ⚠️ action5() - NOT TESTED YET (new action)

**Test Scenarios for action5()**:
```yaml
Test 1: Deploy with contract name parameter
  Given: contractName = 'SpiralEngine'
  When: action5('SpiralEngine')
  Then: Contract deployed, registered, address returned

Test 2: Deploy from config
  Given: config.set('deployment.contractName', 'ProductRegistry')
  When: action5()
  Then: ProductRegistry deployed from config

Test 3: Missing contract name
  Given: No parameter, no config
  When: action5()
  Then: Error thrown with clear message

Test 4: Without MagicRegistry
  Given: MagicRegistry not deployed
  When: action5('SpiralEngine')
  Then: Warning logged, contract deployed, registered: false

Test 5: Idempotent behavior
  Given: SpiralEngine already deployed
  When: action5('SpiralEngine')
  Then: Returns existing contract (no redeploy)
```

---

## Migration Notes

### OLD vs NEW

**OLD (deploy_full.js:892-896)**:
```javascript
if (action === 5) {
  const contractName = args[1] || process.env.CONTRACT_NAME;
  console.log(`\n🔷 Обрабатываем контракт: ${contractName}`);
  await deploySingleContract(contractName, amanitaRegistry);
  console.log(`✅ Контракт ${contractName} успешно обработан!`);
}
```

**NEW (DeployActions.js:30-81)**:
```javascript
async action5(contractName) {
  // 1. Validate contract name (parameter or config)
  // 2. Load MagicRegistry (optional)
  // 3. Deploy via ContractManager (auto-detects type)
  // 4. Print .env format
  // 5. Return structured result
}
```

**Improvements**:
- ✅ Cleaner API (parameter vs process.env)
- ✅ Config fallback support
- ✅ Auto type detection (UUPS, SBT, regular)
- ✅ Structured output
- ✅ Better error handling
- ✅ Full Ethers.js migration (no Web3.js)

---

## Changelog

**v2.0** (2025-10-20):
- ✅ Added action5() - Deploy single contract by name
- ✅ Migrated to Ethers.js v6
- ✅ Integrated with ContractManager
- ✅ Added flexible input (parameter + config)
- ✅ Added .env output format

**v1.0** (2025-10-12):
- Initial version with action0() and action1()

---

**Version**: 2.0  
**Last Updated**: 2025-10-20  
**Compatibility**: Ethers.js v6, Hardhat  
**Related Modules**: ContractManager, SetupActions, Config
