# AI Development Journal - Amanita Bot

## 📅 2025-10-10: HashiCorp Vault Integration Analysis

**Status:** 🔍 Analysis Phase  
**Cognitive Pattern:** @analysis.mdc (Hard Analysis - Code-based only)  
**Priority:** 🔴 CRITICAL (Security Enhancement)

---

## 🎯 Task Overview

**Goal:** Integrate HashiCorp Vault for secure private key storage in `polygon` profile, replacing direct environment variables.

**Context:**
- Current: Private keys stored in Railway Variables → риск утечки через код
- Target: Private keys in HashiCorp Vault → Railway хранит только Vault credentials
- Scope: `bot/services/core/blockchain.py` + configuration layer

---

## 📊 Current State Analysis (Code-Based)

### 1.1 Configuration Analysis

**File:** `bot/config.py` (Lines 1-114)

**Current Implementation:**
```python
# Lines 51-60
BLOCKCHAIN_PROFILE = os.getenv("BLOCKCHAIN_PROFILE", "localhost")
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
if not SELLER_PRIVATE_KEY:
    raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
if not SELLER_PRIVATE_KEY.startswith("0x"):
    SELLER_PRIVATE_KEY = f"0x{SELLER_PRIVATE_KEY}"
```

**Findings:**
- ✅ `BLOCKCHAIN_PROFILE` exists - can be used as conditional flag
- ✅ `SELLER_PRIVATE_KEY` loaded directly from `os.getenv()`
- ✅ Validation: checks for `0x` prefix
- ⚠️ Raises error if not found - needs graceful Vault fallback

**Additional Private Keys Found:**
```python
# Line 73
ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY")

# Not in config.py but used in contracts deployment (separate concern)
# DEPLOYER_PRIVATE_KEY - used in scripts/*, not in bot runtime
```

---

### 1.2 Architecture Analysis

**File:** `bot/services/core/blockchain.py` (Lines 1-896)

**Current Usage of Private Keys:**

```python
# Line 14, 22: Import from config
from config import (
    SELLER_PRIVATE_KEY,
    RPC_URL,
    ABI_BASE_DIR,
    MAGIC_REGISTRY_CONTRACT_ADDRESS
)

# Lines 135-139: Initialization
if not SELLER_PRIVATE_KEY:
    raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
self.seller_key = SELLER_PRIVATE_KEY
self.seller_account = Account.from_key(SELLER_PRIVATE_KEY)

# Lines 328-394: Transaction signing
def transact_contract_function(..., private_key: str, ...):
    account = Account.from_key(private_key)
    ...
    signed_txn = self.web3.eth.account.sign_transaction(txn, private_key)
```

**Key Methods Using Private Keys:**
1. `__init__` (Line 119) - initializes `self.seller_account`
2. `transact_contract_function` (Line 328) - accepts `private_key` parameter
3. `activate_invite` (Line 428) - passes private key to transact
4. `mint_invite` (Line 552) - uses `self.seller_key`
5. `grant_seller_role` (Line 576) - uses private key parameter
6. `create_product` (Line 677) - uses `self.seller_key`
7. `set_product_active` (Line 726) - accepts private key parameter

**Pattern:**
- `self.seller_key` stored as instance variable
- Some methods accept `private_key` as parameter (flexible)
- Some methods use `self.seller_key` directly (fixed seller context)

---

### 1.3 Dependency Analysis

**ArWeave Service:** `bot/services/core/storage/ar_weave.py` (Line 16)
```python
from config import SUPABASE_URL, SUPABASE_ANON_KEY, ARWEAVE_PRIVATE_KEY
```

**Import Chain:**
```
config.py (loads from env)
    ↓
blockchain.py (imports SELLER_PRIVATE_KEY)
    ↓
BlockchainService.__init__ (creates Account)
    ↓
Various transaction methods (use private_key)
```

---

## 🏗️ Architecture Design

### 2.1 Vault Service Design

**New File:** `bot/services/core/vault_service.py`

**Requirements:**
1. Connect to HashiCorp Vault using `VAULT_ADDR` and `VAULT_TOKEN`
2. Read secrets from specified path `VAULT_PATH`
3. Provide synchronous interface (bot is sync-first)
4. Handle errors gracefully (fallback to env vars for localhost)
5. Cache secrets in memory (avoid repeated API calls)

**Interface Design:**
```python
class VaultService:
    """Service for retrieving secrets from HashiCorp Vault"""
    
    def __init__(self, vault_addr: str, vault_token: str, vault_path: str):
        """Initialize Vault client"""
        
    def get_secret(self, key: str) -> Optional[str]:
        """Get single secret by key"""
        
    def get_all_secrets(self) -> Dict[str, str]:
        """Get all secrets from vault path"""
        
    def is_available(self) -> bool:
        """Check if Vault is available"""
```

---

### 2.2 Configuration Layer Modification

**File:** `bot/config.py`

**New Configuration Variables:**
```python
# Vault configuration (only for polygon profile)
VAULT_ADDR = os.getenv("VAULT_ADDR")  # https://vault.company.com
VAULT_TOKEN = os.getenv("VAULT_TOKEN")  # hvs.xxxxx
VAULT_PATH = os.getenv("VAULT_PATH", "secret/amanita")  # path in Vault

USE_VAULT = BLOCKCHAIN_PROFILE == "polygon" and VAULT_ADDR and VAULT_TOKEN
```

**Modified Key Loading Logic:**
```python
if USE_VAULT:
    # Load from Vault
    from services.core.vault_service import VaultService
    vault = VaultService(VAULT_ADDR, VAULT_TOKEN, VAULT_PATH)
    
    SELLER_PRIVATE_KEY = vault.get_secret("seller_private_key")
    if not SELLER_PRIVATE_KEY:
        raise ValueError("SELLER_PRIVATE_KEY не найден в Vault")
        
    ARWEAVE_PRIVATE_KEY = vault.get_secret("arweave_private_key")
    # Note: can be None, ArWeave is optional
else:
    # Load from environment (localhost profile)
    SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
    if not SELLER_PRIVATE_KEY:
        raise ValueError("SELLER_PRIVATE_KEY не установлен")
        
    ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY")
```

---

### 2.3 Integration Points

**Unchanged Components:**
- ✅ `blockchain.py` - no changes needed, imports from `config`
- ✅ `ar_weave.py` - no changes needed, imports from `config`
- ✅ All other services - transparent to Vault integration

**Changed Components:**
- 🔄 `config.py` - conditional key loading logic
- ➕ `vault_service.py` - new service (to be created)

**Environment Variables (Railway):**

**Before (Current - INSECURE):**
```bash
BLOCKCHAIN_PROFILE=polygon
SELLER_PRIVATE_KEY=0xYOUR_ACTUAL_KEY  # ❌ Exposed in Railway
ARWEAVE_PRIVATE_KEY={"kty":"RSA"...}  # ❌ Exposed in Railway
```

**After (Target - SECURE):**
```bash
BLOCKCHAIN_PROFILE=polygon
VAULT_ADDR=https://vault.hashicorp.cloud/...
VAULT_TOKEN=hvs.xxxxx  # ✅ Read-only token
VAULT_PATH=secret/amanita

# ❌ Remove these from Railway:
# SELLER_PRIVATE_KEY
# ARWEAVE_PRIVATE_KEY
```

---

## 📋 Implementation Tasks

### ✅ Phase 1: Vault Service Creation [COMPLETED 2025-10-10]
**File:** `bot/services/vault_service.py`

**Dependencies:**
```bash
pip install hvac>=2.1.0  # Official HashiCorp Vault Python client
```

**Implementation:**
- [x] Create `VaultService` class
- [x] Implement `__init__` with connection logic
- [x] Implement `get_secret` method
- [x] Implement `get_all_secrets` method
- [x] Add error handling and logging
- [x] Add healthcheck method
- [x] Add connection validation (fail-fast)
- [ ] Add in-memory caching (future enhancement)
- [ ] Add connection retry logic (future enhancement)

**Result:** 367 lines, fully functional VaultService with comprehensive error handling

---

### ✅ Phase 2: Config Modification [COMPLETED 2025-10-10]
**File:** `bot/config.py`

**Changes:**
- [x] Add DEPLOYMENT_PROFILE variable
- [x] Add Vault import (with graceful fallback)
- [x] Add `_load_secrets_from_vault()` helper function
- [x] Refactor `SELLER_PRIVATE_KEY` loading with if/else by profile
- [x] Refactor `ARWEAVE_PRIVATE_KEY` loading with if/else by profile
- [x] Add logging for which source is used (env vs Vault)
- [x] Ensure backward compatibility (localhost profile unchanged)

**Validation:**
- [x] Test script created: `validate_vault_integration.py`
- [x] Localhost profile validated (uses env vars as before)
- [x] Polygon profile validated (fails gracefully without Vault)

**Result:** +70 lines, profile-based configuration with backward compatibility

---

### 📋 Phase 3: Railway Configuration [USER ACTION REQUIRED]
**Railway Dashboard:**

**Add New Variables:**
- [ ] `DEPLOYMENT_PROFILE=polygon` - Enable Vault for production
- [ ] `VAULT_ADDR` - Vault server URL (from HCP Vault cluster)
- [ ] `VAULT_TOKEN` - Read-only access token
- [ ] `VAULT_PATH` - Path to secrets (default: `secret/data/amanita`)

**Remove Old Variables (after validation):**
- [ ] ~~`SELLER_PRIVATE_KEY`~~ → Move to Vault
- [ ] ~~`ARWEAVE_PRIVATE_KEY`~~ → Move to Vault

**Migration Steps:**
1. Create secrets in Vault first (Phase 4)
2. Add Vault variables to Railway
3. Deploy new code
4. Test that keys are loaded from Vault
5. Only then remove old variables

**Documentation:** See `docs/VAULT_RAILWAY_SETUP.md` for detailed instructions

---

### 📋 Phase 4: Vault Setup (External) [USER ACTION REQUIRED]
**HashiCorp Vault Cloud:**

**Setup Steps:**
1. [ ] Create HCP Vault cluster
2. [ ] Enable KV v2 secrets engine
3. [ ] Create secrets at `secret/amanita`:
   - [ ] `SELLER_PRIVATE_KEY = "0x..."`
   - [ ] `ARWEAVE_PRIVATE_KEY = "{...}"`
4. [ ] Create read-only policy `amanita-bot-readonly`
5. [ ] Generate service token with policy

**Secrets Structure:**
```
secret/amanita/
├── SELLER_PRIVATE_KEY = "0x..."
├── ARWEAVE_PRIVATE_KEY = "{\"kty\":\"RSA\"...}"
└── (future: DEPLOYER_PRIVATE_KEY for scripts)
```

**Access Policy:**
```hcl
# Read-only policy for bot
path "secret/data/amanita" {
  capabilities = ["read"]
}

path "secret/metadata/amanita" {
  capabilities = ["list", "read"]
}
```

**Token Requirements:**
- ✅ Read-only access to `secret/data/amanita`
- ✅ TTL >= 30 days or renewable
- ❌ No write/delete permissions

**Documentation:** See `docs/VAULT_SETUP.md` for detailed instructions

---

## 🔒 Security Improvements

### Current (Before):
```
Railway Variables
├── SELLER_PRIVATE_KEY = "0xREAL_KEY"  ❌
├── ARWEAVE_PRIVATE_KEY = "{...}"     ❌
└── (риск утечки через console.log, error.stack)
```

### Target (After):
```
Railway Variables                      HashiCorp Vault
├── VAULT_ADDR = "https://..."    →   secret/amanita/
├── VAULT_TOKEN = "hvs.xxx"       →   ├── seller_private_key
└── VAULT_PATH = "secret/amanita" →   └── arweave_private_key
    ✅ Только credentials               ✅ Actual secrets
```

**Benefits:**
- ✅ Private keys НЕ в Railway → no risk via UI/API
- ✅ Railway compromised ≠ keys compromised (need Vault token + addr)
- ✅ Vault token can be rotated independently
- ✅ Audit log in Vault (who accessed what, when)
- ✅ Centralized secret management
- ✅ Easy to rotate keys (update in Vault → restart bot)

---

## ⚠️ Risk Analysis

### Implementation Risks:

**Risk 1: Vault Unavailable**
- **Impact:** Bot cannot start or perform transactions
- **Mitigation:** Add connection retry with exponential backoff
- **Fallback:** Keep error message clear, suggest checking Vault status

**Risk 2: Invalid Token**
- **Impact:** Cannot read secrets, bot fails to start
- **Mitigation:** Validate token on startup, fail fast with clear error
- **Monitoring:** Alert on token expiration

**Risk 3: Network Latency**
- **Impact:** Slower bot startup (need to fetch secrets)
- **Mitigation:** Cache secrets in memory after first fetch
- **Optimization:** Fetch all secrets at once (not per-key)

**Risk 4: Breaking Localhost Development**
- **Impact:** Developers cannot run bot locally
- **Mitigation:** Strict conditional - only use Vault if `BLOCKCHAIN_PROFILE=polygon`
- **Documentation:** Clear setup instructions for both modes

---

## 📊 Verification Checklist

### Configuration Verification:
- [ ] `BLOCKCHAIN_PROFILE` read correctly from env
- [ ] `USE_VAULT` conditional works as expected
- [ ] Vault variables present when profile=polygon
- [ ] Environment variables used when profile=localhost

### Functional Verification:
- [ ] Bot starts successfully (polygon profile + Vault)
- [ ] Bot starts successfully (localhost profile + env vars)
- [ ] Private keys loaded correctly from Vault
- [ ] `BlockchainService` initializes with Vault keys
- [ ] Transactions can be signed with Vault keys
- [ ] ArWeave operations work with Vault key

### Security Verification:
- [ ] No private keys in Railway Variables
- [ ] Vault credentials have read-only access
- [ ] Vault logs show access from bot
- [ ] No keys logged in Railway logs
- [ ] Error messages don't expose keys

---

## 🎓 Learning Points

### From Code Analysis:

**Pattern 1: Centralized Configuration**
- ✅ All config in `config.py` - good separation of concerns
- ✅ Import pattern allows transparent switching (env → Vault)
- ✅ Services don't need to know about Vault existence

**Pattern 2: Private Key Flexibility**
- ✅ Some methods accept `private_key` parameter (flexible)
- ✅ Some methods use `self.seller_key` (fixed context)
- 💡 Design allows future multi-wallet support

**Pattern 3: Singleton Service**
- ✅ `BlockchainService` is singleton - initialized once
- ✅ Vault fetch only happens once at startup
- ✅ No repeated Vault calls during runtime

### Dependencies Found:
```
hvac==1.2.1  # Official HashiCorp Vault client
    ├── requests>=2.27.0  # Already in project
    └── pyhcl>=0.4.4      # HCL parser (not needed for client usage)
```

---

## 📝 Next Steps

### Immediate (Today):
1. ✅ Complete this analysis document
2. ⏳ Create `vault_service.py` implementation
3. ⏳ Write unit tests for `VaultService`
4. ⏳ Modify `config.py` with conditional logic

### Short-term (This Week):
5. ⏳ Set up HashiCorp Vault Cloud account
6. ⏳ Create secrets in Vault
7. ⏳ Generate read-only token
8. ⏳ Test integration end-to-end (localhost → dev Vault)

### Before Production:
9. ⏳ Add Vault variables to Railway
10. ⏳ Deploy to Railway staging
11. ⏳ Verify bot startup with Vault
12. ⏳ Test transactions on polygon testnet
13. ⏳ Remove old private key variables from Railway
14. ⏳ Update documentation

---

## 📚 References

### Code Files Analyzed:
- `bot/config.py` (lines 1-114) - configuration layer
- `bot/services/core/blockchain.py` (lines 1-896) - blockchain service
- `bot/services/core/storage/ar_weave.py` (line 16) - ArWeave key usage

### External Documentation:
- HashiCorp Vault Python Client: https://hvac.readthedocs.io/
- Vault KV Secrets Engine: https://developer.hashicorp.com/vault/docs/secrets/kv
- Best Practices: https://developer.hashicorp.com/vault/tutorials/recommended-patterns

### Related Security Docs:
- `SECURITY_SUMMARY.md` - Overall security analysis
- `RAILWAY_SECURITY_REAL.md` - Railway variables vs external secrets
- `security_analysis_20251010_133220/` - Detailed security scan results

---

## ✅ Analysis Complete

**Status:** Ready for implementation  
**Confidence:** HIGH (based on actual code analysis)  
**Breaking Changes:** NONE (backward compatible with localhost profile)  
**Security Impact:** CRITICAL IMPROVEMENT

---

**Next File to Create:** `bot/services/core/vault_service.py`  
**Next File to Modify:** `bot/config.py`


