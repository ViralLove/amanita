# Scripts Directory Structure

## 🎯 Main Entry Point
- **`deploy_full.js`** - Production deployment router (modular architecture v2.0, 217 lines)

## 🔧 Business Logic (root level)
- **`transform_products_csv.js`** - CSV → JSON transformation for Action 41
  - Dependencies: `lib/csv_parser.js`, `lib/form_mapper.js`, `lib/product_utils.js`

## ✅ Validators (`validators/`)
All validation scripts organized in dedicated directory:
- **`validate_catalog_pipeline.js`** - Full 5-phase catalog validation (2077 lines)
- **`validate_component_upload.js`** - Component upload validation (4 phases)
- **`validate_catalog_upload.js`** - Lightweight contract-only validation
- **`validate_product_mappings.js`** - Mapping integrity checker
- **`validate_full_catalog_pipeline.sh`** - Bash wrapper for CI/CD
- **`verify_component_cids.js`** - Arweave CID verification

See `validators/README.md` for detailed usage and examples.

## 🛠️ Utilities (`utils/`)
- **`view_upload_report.js`** - Upload report viewer
- **`validate_products.js`** - Product JSON structure validation (deep check)
- **`sync_component_mapping.js`** - Manual component mapping synchronization

## 🤖 Automation
- **`clean_components_upload.bash`** - Cleanup before Action 555 re-run
- **`quick_start_automation.sh`** + `.md` - Full ecosystem deployment automation

## 🏗️ Architecture (`lib/`)
Modular architecture with 16 classes:
- **`actions/`** - 6 action classes:
  - `DeployActions.js` - Actions 0, 1, 5 (deployment)
  - `SetupActions.js` - Action 2 (system connections)
  - `AccessControlActions.js` - Actions 9, 13 (roles & diagnostics)
  - `InviteActions.js` - Actions 7, 11, 777, 888 (invites & activation)
  - `CatalogActions.js` - Actions 4, 6, 40, 41, 42, 43, 46, 444 (catalog)
  - `ComponentActions.js` - Action 555 (components)
- **`services/`** - ContractManager, ArweaveManager
- **`utils/`** - Logger, EthersUtils, Web3Utils
- **`config/`** - Centralized configuration (44 env vars)
- **`core/`** - Shared business logic

See `docs/Deploy_Architecture.md` for complete architecture documentation.

## 🧪 Testing (`tests/`)
- **`unit/`** - Unit tests for all modules
- **`integration/`** - Integration tests
- **`e2e/`** - End-to-end tests
- **`helpers/`** - Test harnesses and mocks

## 📚 Documentation (`docs/`)
- **`Deploy_Architecture.md`** - Complete architecture documentation (v2.0)
- **`Catalog-Architecture.md`** - Catalog pipeline technical details
- **`Components-Architecture.md`** - Component upload pipeline
- **`actions/`** - Individual action documentation (6 files)
- **`validation-process.txt`** - Quick reference for validation commands

## 🗄️ Archive (`archive/`)
- **`deploy_full_monolith_legacy_20251014.js`** - Legacy monolithic version (4767 lines)
  - Kept for historical reference only
  - Replaced by modular architecture on 2025-10-14

---

## 🚀 Quick Start

### Deploy Full Ecosystem
```bash
# 1. Deploy contracts
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# 2. Create root invites
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# 3. Upload components
DEPLOY_ACTION=555 DEPLOYER_INVITE=<INVITE> npx hardhat run scripts/deploy_full.js --network localhost

# 4. Upload catalog
DEPLOY_ACTION=444 npx hardhat run scripts/deploy_full.js --network localhost
```

### Validate Uploads
```bash
# Validate components
node scripts/validators/validate_component_upload.js --component amanita_muscaria --network localhost

# Validate catalog
node scripts/validators/validate_catalog_pipeline.js --seller iveta --network localhost
```

---

**Architecture Version**: 2.0  
**Last Updated**: 2025-10-28  
**Status**: Production Ready ✅

