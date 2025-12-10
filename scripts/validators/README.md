# Validators Directory

Централизованная директория для всех validation скриптов экосистемы Amanita.

## 📋 Available Validators

### 🔍 Catalog Validators

#### `validate_catalog_pipeline.js` (Primary - Full Validation)
**Purpose**: Полная 5-фазовая валидация catalog pipeline

**Phases**:
1. **CSV/FileSystem** (15% weight) - Проверка CSV файла и product JSON
2. **Arweave Layer** (25% weight) - Проверка CID на Arweave
3. **Contract Layer** (35% weight) - Проверка регистрации в ProductRegistry
4. **Consistency** (20% weight) - Сопоставление данных между слоями
5. **Components** (5% weight) - Проверка зависимостей компонентов

**Usage**:
```bash
# Quick validation (sampled - first 5 products only)
node scripts/validators/validate_catalog_pipeline.js --seller iveta --network localhost

# Full validation (recommended for production)
node scripts/validators/validate_catalog_pipeline.js --seller iveta --network localhost --full-arweave-check

# JSON output for automation
node scripts/validators/validate_catalog_pipeline.js --seller iveta --network localhost --json
```

**Output**: Quality Score 0-10, PASS threshold >= 7.0

**📚 Detailed Audit**: See [Catalog Upload Validation Audit](../../docs/Catalog-Upload-Validation-Audit.md) for comprehensive analysis of validation honesty, scoring system, and known limitations.

---

#### `validate_catalog_upload.js` (Lightweight - Contract Only)
**Purpose**: Быстрая проверка только contract layer

**Usage**:
```bash
MAPPING_FILE="data/sellers/iveta/output/product_combined_mapping.json" \
  node scripts/validators/validate_catalog_upload.js --network localhost
```

**When to use**: После Action 43 для быстрой проверки регистрации

---

#### `validate_product_mappings.js` (Mapping Integrity)
**Purpose**: Валидация product_combined_mapping.json

**Checks**:
- CID format validation
- URL consistency (CID matching)
- Required fields (languages, urls)
- Partial upload detection

**Usage**:
```bash
MAPPING_FILE="data/sellers/iveta/output/product_combined_mapping.json" \
  node scripts/validators/validate_product_mappings.js
```

---

### 🧬 Component Validators

#### `validate_component_upload.js` (Primary)
**Purpose**: Полная 4-фазовая валидация component upload

**Phases**:
1. **FileSystem** - Проверка локальных файлов
2. **Arweave** - Проверка CID на Arweave
3. **Contract** - Проверка регистрации в OrganicComponentRegistry
4. **State** - Проверка upload state файлов

**Usage**:
```bash
# Single component
node scripts/validators/validate_component_upload.js \
  --component amanita_muscaria --network localhost

# With JSON output
node scripts/validators/validate_component_upload.js \
  --component blue_lotus --network localhost --json

# Custom seller
node scripts/validators/validate_component_upload.js \
  --component lions_mane --network localhost \
  --seller 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

**Critical Check**: Action 444 Compatibility
- ✅ COMPATIBLE: componentExists(componentId) == true
- ❌ INCOMPATIBLE: Action 444 will fail with ComponentNotFound

---

#### `verify_component_cids.js` (Arweave Direct Check)
**Purpose**: Прямая проверка CID на Arweave (без контрактов)

**Usage**:
```bash
node scripts/validators/verify_component_cids.js
```

**Checks**:
- HTTP status на arweave.net/{CID}
- Content size
- JSON validity

---

### 🚀 Bash Wrappers

#### `validate_full_catalog_pipeline.sh`
**Purpose**: Wrapper для CI/CD интеграции

**Usage**:
```bash
bash scripts/validators/validate_full_catalog_pipeline.sh
```

---

## 📊 Validation Workflow

### After Action 555 (Components)
```bash
# 1. Validate critical components
for comp in amanita_muscaria blue_lotus lions_mane; do
  node scripts/validators/validate_component_upload.js \
    --component "$comp" --network localhost | grep "Action 444 Compatible"
done

# Expected: ✅ COMPATIBLE for all
```

### After Action 444 (Catalog)
```bash
# 2. Full catalog validation
node scripts/validators/validate_catalog_pipeline.js \
  --seller iveta --network localhost

# Expected: Quality Score >= 8.0/10
```

---

## 🎯 Quality Metrics

### Passing Thresholds
- **Catalog Pipeline**: >= 8.0/10 overall score
- **Component Upload**: >= 8.0/10 overall score
- **Action 444 Compatibility**: ✅ COMPATIBLE (componentExists == true)

### Weights (Catalog)
- FileSystem: 15%
- Arweave: 30%
- Contract: 35% (CRITICAL for production)
- Consistency: 20%

---

## 🔧 Troubleshooting

### "Contracts not accessible"
**Solution**: Check Hardhat node and .env proxy addresses
```bash
curl -s -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545
```

### "Component not registered"
**Solution**: Re-run Action 555
```bash
DEPLOY_ACTION=555 DEPLOYER_INVITE=<INVITE> \
  npx hardhat run scripts/deploy_full.js --network localhost
```

### Quality Score < 8.0
**Solution**: Check specific phase failures in detailed output

---

## 📚 Related Documentation
- `../docs/Catalog-Architecture.md` - Catalog pipeline details
- `../docs/Components-Architecture.md` - Component upload details
- `../docs/validation-process.txt` - Quick reference commands

---

**Version**: 1.0  
**Last Updated**: 2025-10-28  
**Status**: Production Ready ✅

