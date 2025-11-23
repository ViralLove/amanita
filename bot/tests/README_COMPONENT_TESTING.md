# OrganicComponentRegistry Integration Testing Guide

## Prerequisites

Before running tests, ensure:

### 1. Hardhat Node Running

```bash
# Terminal 1: Start Hardhat node
npx hardhat node
```

### 2. Contracts Deployed

```bash
# Terminal 2: Deploy contracts
node scripts/deploy_full.js --action deploy-all
```

### 3. Components Uploaded (Action 555)

```bash
# Upload components to OrganicComponentRegistry
node scripts/deploy_full.js --action 555
```

**Required env variables:**
- `DEPLOYER_INVITE` - invite code for activation
- `SELLER_ADDRESS` - seller wallet address

**This will:**
- Activate seller via SpiralEngine
- Upload 11+ components to OrganicComponentRegistry
- Store metadata in Arweave

## Running Tests

### Full Test Suite

```bash
python3 bot/tests/test_component_integration.py
```

### Expected Output (if successful)

```
============================================================
TEST SUMMARY
============================================================
✅ PASSED: Contract Loading
✅ PASSED: component_exists()
✅ PASSED: get_component()
✅ PASSED: get_component_root_metadata_cid()
✅ PASSED: get_all_components()
✅ PASSED: Error Handling

============================================================
Total: 6/6 tests passed
============================================================

🎉 ALL TESTS PASSED! OrganicComponentRegistry integration is working.
```

## Manual Testing from Python REPL

```python
from bot.services.core.blockchain import BlockchainService

# Initialize
bs = BlockchainService()

# Test 1: Check if contract loaded
contract = bs.get_contract("OrganicComponentRegistry")
print(f"Contract address: {contract.address}")

# Test 2: Check if component exists
exists = bs.component_exists("amanita_muscaria")
print(f"Component exists: {exists}")

# Test 3: Get component data
component = bs.get_component("amanita_muscaria")
print(f"Component: {component}")

# Test 4: Get metadata CID
cid = bs.get_component_root_metadata_cid("amanita_muscaria")
print(f"Arweave CID: {cid}")
print(f"Arweave URL: https://arweave.net/{cid}")

# Test 5: Get all components
all_components = bs.get_all_components()
print(f"Total components: {len(all_components)}")
for comp in all_components:
    print(f"  - {comp[1]}")  # business_id
```

## Troubleshooting

### Error: "Failed to connect to Web3"

**Cause:** Hardhat node not running

**Solution:**
```bash
# Start Hardhat node in separate terminal
npx hardhat node
```

### Error: "OrganicComponentRegistry not found in registry"

**Cause:** Contracts not deployed

**Solution:**
```bash
node scripts/deploy_full.js --action deploy-all
```

### Error: "Component 'amanita_muscaria' not found"

**Cause:** Components not uploaded via Action 555

**Solution:**
```bash
# Set env variables
export DEPLOYER_INVITE="your_invite_code"
export SELLER_ADDRESS="0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

# Run Action 555
node scripts/deploy_full.js --action 555
```

## Next Steps

After tests pass:

1. **Create ComponentService** (`bot/services/product/component_service.py`)
   - Wrap blockchain.py methods with business logic
   - Add caching
   - Handle Arweave metadata fetching

2. **Integrate into ProductAssembler** (`bot/services/product/assembler.py`)
   - Resolve `component_id` from product metadata
   - Fetch component data from OrganicComponentRegistry
   - Merge component details into product display

3. **Update Bot UI**
   - Show scientific names in product cards
   - Display component features (organic, wildcrafted, etc.)
   - Add multilingual component descriptions

