# 🌿 Organic Components Architecture - Complete Pipeline & Validation

**Version:** 2.0  
**Date:** 2025-10-27  
**Methodology:** @analysis.mdc  
**Status:** ✅ Production Ready

---

## 📋 Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Core Concepts](#core-concepts)
3. [Component Structure](#component-structure)
4. [Localization Architecture](#localization-architecture)
5. [Upload Pipeline](#upload-pipeline)
6. [Contract Integration](#contract-integration)
7. [Validation System](#validation-system)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

---

## 🎯 Overview & Purpose

### **What are Organic Components?**

**Organic Components** are biological entities (plants, fungi, herbs) that form a **centralized, community-driven registry** serving as a **single source of truth** for all participants in the Amanita ecosystem.

### **Key Objectives**

```yaml
Standardization:
  - Unified biological component terminology
  - Shared vocabulary across all sellers
  - Consistent taxonomic classification

Crowdsourcing:
  - Community-driven component proposals
  - Staking-based validation mechanism
  - Contributor reward system

Reusability:
  - One component definition → used by all sellers
  - Decentralized storage (Arweave/IPFS)
  - Multi-language support (15+ languages)

Integration:
  - ProductRegistry validation
  - AmanitaInternational localization
  - Bot catalog generation
```

### **Architecture Principles**

- ✅ **Decentralized Storage**: Arweave for immutable metadata
- ✅ **Multi-Language Support**: 7 core languages + 8 extended languages
- ✅ **Contract-First Design**: Smart contract as source of truth
- ✅ **Resumable Uploads**: State management for fault tolerance
- ✅ **Validation-Driven**: 4-phase validation before production use

---

## 🏗️ Core Concepts

### **1. Component Identity**

```yaml
Component ID (biounit_id):
  Format: "snake_case_identifier"
  Examples: "amanita_muscaria", "blue_lotus", "lions_mane"
  Requirements:
    - Unique across ecosystem
    - Immutable after creation
    - Used for contract storage key

Scientific Name:
  Format: "Genus species"
  Examples: "Amanita muscaria", "Nymphaea caerulea"
  Purpose: Taxonomic identification
```

### **2. Component Forms**

Components can exist in multiple physical forms:

```json
{
  "forms": [
    "dried",           // Dried material
    "tincture",        // Alcohol extraction
    "powder_extract",  // Ground/powdered
    "oil_extract",     // Oil-based extraction
    "water_extract",   // Aqueous extraction
    "capsules",        // Encapsulated form
    "tea_bags"         // Pre-packaged tea
  ]
}
```

**Forms are referenced from shared dictionary:** `bot/catalog/component_forms.json`

### **3. Component Features**

Features describe characteristics and certifications:

```json
{
  "features": {
    "common": [
      "organic",        // Organic certification
      "wildcrafted",    // Wild-harvested
      "lab_tested",     // Laboratory verified
      "sustainable",    // Sustainable sourcing
      "fair_trade"      // Fair trade certified
    ],
    "forms": {
      "dried": ["organic", "wildcrafted"],
      "tincture": ["organic", "lab_tested"]
    }
  }
}
```

**Features are referenced from shared dictionary:** `bot/catalog/features.json`

### **4. Lifecycle States**

```solidity
enum ValidationStatus {
    Proposed,      // Initial submission
    Validating,    // Community review
    Approved,      // Validated and active
    Rejected,      // Failed validation
    Deprecated     // Obsolete/replaced
}
```

---

## 📦 Component Structure

### **Directory Layout**

```
data/components/
└── amanita_muscaria/                    # Component directory
    ├── amanita_muscaria.json            # ✅ Root metadata (base file)
    ├── simple_fields/                   # ✅ Multi-language simple strings
    │   ├── amanita_muscaria.ComponentDescription.title.json
    │   └── amanita_muscaria.DosageInstruction.description.json
    ├── complex_fields/                  # ✅ Multi-language descriptions
    │   ├── amanita_muscaria.ComponentDescription.ru.json
    │   ├── amanita_muscaria.ComponentDescription.en.json
    │   ├── amanita_muscaria.ComponentDescription.es.json
    │   ├── amanita_muscaria.ComponentDescription.fr.json
    │   ├── amanita_muscaria.ComponentDescription.de.json
    │   ├── amanita_muscaria.ComponentDescription.nl.json
    │   └── amanita_muscaria.ComponentDescription.et.json
    └── state.amanita_muscaria.localhost.json  # ✅ Upload state tracker
```

### **Root Metadata File (`amanita_muscaria.json`)**

```json
{
  "biounit_id": "amanita_muscaria",
  "scientific_title": "Amanita muscaria",
  "created_at": "2024-01-15T00:00:00Z",
  "last_updated": "2024-01-15T00:00:00Z",
  "created_by": "0x1234567890abcdef1234567890abcdef12345678",
  
  "contributors": [
    {
      "address": "0x1234567890abcdef1234567890abcdef12345678",
      "role": "creator",
      "added_at": "2024-01-15T00:00:00Z"
    }
  ],
  
  "localizations": {
    "simple_fields": {
      "title": {
        "cid": "QmTitleCID123...",
        "label": "ComponentDescription.title"
      },
      "dosage_types": {
        "cid": "QmDosageTypesCID012...",
        "label": "DosageInstruction.description"
      }
    },
    "complex_fields": {
      "ru": { "cid": "QmRuCID345...", "label": "ComponentDescription" },
      "en": { "cid": "QmEnCID901...", "label": "ComponentDescription" },
      "es": { "cid": "QmEsCID234...", "label": "ComponentDescription" },
      "fr": { "cid": "QmFrCID567...", "label": "ComponentDescription" },
      "de": { "cid": "QmDeCID890...", "label": "ComponentDescription" },
      "nl": { "cid": "QmNlCID123...", "label": "ComponentDescription" },
      "et": { "cid": "QmEtCID456...", "label": "ComponentDescription" }
    }
  },
  
  "forms": ["dried", "tincture", "powder_extract", "oil_extract", "water_extract"],
  
  "features": {
    "common": ["stress_relief", "adaptogenic", "nootropic"],
    "forms": {
      "dried": ["wildcrafted", "organic"],
      "tincture": ["lab_tested", "organic"],
      "powder_extract": ["standardized_extract", "lab_tested"]
    }
  },
  
  "safety_profile": {
    "toxicity_class": "moderate",
    "ld50": "not established",
    "contraindications": [
      "pregnancy",
      "breastfeeding",
      "children_under_18",
      "liver_disease"
    ],
    "drug_interactions": [
      "alcohol",
      "sedatives",
      "antipsychotics"
    ],
    "warnings": [
      "Do not consume raw",
      "Requires proper preparation",
      "Start with low doses"
    ]
  },
  
  "taxonomy": {
    "kingdom": "Fungi",
    "phylum": "Basidiomycota",
    "class": "Agaricomycetes",
    "order": "Agaricales",
    "family": "Amanitaceae",
    "genus": "Amanita",
    "species": "muscaria"
  },
  
  "properties": {
    "active_compounds": [
      {
        "name": "Muscimol",
        "cas_number": "2763-96-4",
        "content_range": "0.03-0.1%"
      },
      {
        "name": "Ibotenic acid",
        "cas_number": "2552-55-8",
        "content_range": "0.02-0.08%"
      }
    ],
    "traditional_uses": [
      "Shamanic practices",
      "Stress relief",
      "Sleep support"
    ],
    "modern_applications": [
      "Microdosing",
      "Nootropic support",
      "Adaptogenic blend ingredient"
    ]
  }
}
```

**⚠️ Important:** The `localizations` section is auto-populated by the upload script. Initial file should have empty CIDs.

### **Simple Fields (`ComponentDescription.title.json`)**

**Purpose:** Short, translatable strings (titles, labels, short descriptions)

```json
{
  "ru": "Мухомор красный",
  "en": "Fly Agaric",
  "es": "Matamoscas",
  "fr": "Amanite tue-mouches",
  "de": "Fliegenpilz",
  "nl": "Vliegenzwam",
  "et": "Kärbseseen"
}
```

### **Simple Fields (`DosageInstruction.description.json`)**

**Purpose:** Dosage instructions per form

```json
{
  "dried": {
    "ru": "Начинать с 0.5-1г сушёного материала. Максимум 3г в день.",
    "en": "Start with 0.5-1g dried material. Maximum 3g per day.",
    "es": "Comenzar con 0.5-1g de material seco. Máximo 3g por día.",
    "fr": "Commencer avec 0.5-1g de matériel séché. Maximum 3g par jour.",
    "de": "Beginnen Sie mit 0,5-1g getrocknetem Material. Maximum 3g pro Tag.",
    "nl": "Begin met 0,5-1g gedroogd materiaal. Maximum 3g per dag.",
    "et": "Alusta 0,5-1g kuivatatud materjalist. Maksimaalselt 3g päevas."
  },
  "tincture": {
    "ru": "10-30 капель 2-3 раза в день",
    "en": "10-30 drops 2-3 times per day",
    "es": "10-30 gotas 2-3 veces al día",
    "fr": "10-30 gouttes 2-3 fois par jour",
    "de": "10-30 Tropfen 2-3 mal pro Tag",
    "nl": "10-30 druppels 2-3 keer per dag",
    "et": "10-30 tilka 2-3 korda päevas"
  }
}
```

### **Complex Fields (`ComponentDescription.ru.json`)**

**Purpose:** Detailed, markdown-formatted descriptions

```json
{
  "generic_description": "🔬 **Amanita muscaria** (Мухомор красный) - один из самых узнаваемых грибов в мире...\n\n### Химический состав\n- Мусцимол (основное психоактивное соединение)\n- Иботеновая кислота (преобразуется в мусцимол при сушке)\n\n### Традиционное использование\nИспользовался в шаманских практиках народов Сибири...",
  
  "dosage_instructions": {
    "dried": {
      "title": "Сушёный материал",
      "description": "### Микродозирование\n- **Начальная доза:** 0.5г\n- **Стандартная доза:** 1-2г\n- **Высокая доза:** 3-5г\n\n### Важные замечания\n- Эффекты проявляются через 30-90 минут\n- Продолжительность: 4-8 часов\n- Не превышайте 5г за один приём"
    },
    "tincture": {
      "title": "Настойка (1:5)",
      "description": "### Дозировка\n- **Начальная:** 10 капель\n- **Стандартная:** 20-30 капель\n- **Частота:** 2-3 раза в день\n\n### Применение\nРастворить в воде или соке. Принимать натощак или через 2 часа после еды."
    }
  }
}
```

**Note:** Each language (ru, en, es, fr, de, nl, et) has its own file with identical structure.

---

## 🌍 Localization Architecture

### **Supported Languages**

```yaml
Core Languages (7):
  - ru: Russian (Русский)
  - en: English
  - es: Spanish (Español)
  - fr: French (Français)
  - de: German (Deutsch)
  - nl: Dutch (Nederlands)
  - et: Estonian (Eesti)

Extended Languages (8):
  - pt: Portuguese (Português)
  - pl: Polish (Polski)
  - uk: Ukrainian (Українська)
  - tr: Turkish (Türkçe)
  - ar: Arabic (العربية)
  - zh: Chinese (中文)
  - ja: Japanese (日本語)
  - ko: Korean (한국어)
  - hi: Hindi (हिंदी)

Total: 15 languages
```

### **Localization Layers**

```yaml
Layer 1: Storage (Arweave)
  - Each language stored as separate file
  - Immutable CID for each translation
  - Simple fields: 1 file per field type
  - Complex fields: 1 file per language

Layer 2: Contract (AmanitaInternational)
  - Stores CID references only
  - Key format: "ComponentDescription.{biounit_id}"
  - Lazy loading: Fetch CID when needed
  - Gas-optimized: No full text on-chain

Layer 3: Bot (ProductLocalizationService)
  - Cache: In-memory + Redis
  - Fallback: Default language if translation missing
  - IPFS Gateway: Fetch from CID
  - Format: JSON → User-friendly markdown

Layer 4: UI (Telegram Bot)
  - User language detection
  - Dynamic content formatting
  - Inline keyboard localization
  - Error message localization
```

### **Localization Flow**

```yaml
1. Component Upload (Action 555):
   ├→ Upload title.json (7 languages) → Arweave → CID_title
   ├→ Upload dosage.json (7 languages) → Arweave → CID_dosage
   ├→ Upload ru.json → Arweave → CID_ru
   ├→ Upload en.json → Arweave → CID_en
   ├→ ... (5 more languages)
   └→ Store CIDs in AmanitaInternational contract

2. Product Creation (Action 444):
   ├→ Reference component by biounit_id
   ├→ ProductRegistry stores component reference
   └→ Component localization inherited from OrganicComponentRegistry

3. User Interaction (Telegram Bot):
   ├→ User selects language → Bot state
   ├→ Product loaded from ProductRegistry
   ├→ Component description fetched via CID
   ├→ Cache hit → Return immediately
   └→ Cache miss → Fetch from IPFS → Cache → Return
```

### **Fallback Strategy**

```yaml
User Language: ru
  ↓
Try: ComponentDescription.ru → CID_ru → IPFS
  ↓
Success? → Return Russian description
  ↓
Fail? → Try: ComponentDescription.en → CID_en → IPFS
  ↓
Success? → Return English description (fallback)
  ↓
Fail? → Return: "Description unavailable" (default message)
```

---

## 🚀 Upload Pipeline

### **Action 555: Seller Activation + Component Upload**

**Purpose:** Complete lifecycle of seller activation and component upload

**Flow:**

```yaml
Step 1/8: Validate Inputs
  - Check invite code format
  - Validate seller address
  - Check SELLER_PRIVATE_KEY if needed

Step 2/8: Load Contracts
  - SpiralEngine (for activation)
  - OrganicComponentRegistry
  - AmanitaInternational

Step 3/8: Validate Invite on Blockchain
  - Check invite exists
  - Check invite not used
  - Verify invite active

Steps 4-7/8: Activate Seller
  - Activate user with invite
  - Grant SELLER_ROLE
  - Grant ACTIVATOR_ROLE
  - Generate 12 invites for seller

Step 8/8: Upload Components
  - Delegate to uploadComponentFull()
  - Upload to Arweave
  - Register in contract
```

### **uploadComponentFull(): 6-Step Upload Process**

```yaml
Step 1/6: Initialize Arweave
  ├→ Load Arweave key from .arweave-key.json
  ├→ Check balance (requires >= 0.01 AR)
  ├→ Get wallet address
  └→ Verify connection to Arweave network

Step 2/6: Prepare Contracts
  ├→ Load OrganicComponentRegistry (UUPS proxy)
  ├→ Load AmanitaInternational (UUPS proxy)
  ├→ Load SpiralEngine (for seller validation)
  └→ Verify seller has SELLER_ROLE

Step 3/6: Find Components
  ├→ Scan data/components/ directory
  ├→ Identify component by directory name
  ├→ Load root metadata file
  └→ Load state file (if exists)

Step 4/6: Upload to Arweave (Per Component)
  ├→ 4.1: Upload Simple Fields
  │   ├→ ComponentDescription.title.json → Arweave → CID_title
  │   └→ DosageInstruction.description.json → Arweave → CID_dosage
  ├→ 4.2: Upload Complex Fields (7 languages)
  │   ├→ ComponentDescription.ru.json → Arweave → CID_ru
  │   ├→ ComponentDescription.en.json → Arweave → CID_en
  │   └→ ... (5 more languages)
  ├→ 4.3: Upload Shareable Data (first component only)
  │   ├→ component_forms.json → Arweave → CID_forms
  │   └→ features.json → Arweave → CID_features
  ├→ 4.4: Update Root Metadata
  │   └→ Merge CIDs into root metadata JSON
  ├→ 4.5: Upload Root Metadata
  │   └→ Final metadata → Arweave → CID_root
  └→ 4.6: Register in Contract
      └→ OrganicComponentRegistry.createComponent(biounit_id, CID_root)

Step 5/6: Store CIDs in AmanitaInternational
  ├→ setSimpleFieldCID("ComponentDescription.title", CID_title)
  ├→ setSimpleFieldCID("DosageInstruction.description", CID_dosage)
  └→ For each language: setComplexFieldCID("ComponentDescription.{lang}", CID_{lang})

Step 6/6: Generate Report
  ├→ Components uploaded: X
  ├→ Total CIDs generated: Y
  ├→ Arweave fees: Z AR
  └→ Save final state file
```

### **State Management**

**State File:** `state.{component_id}.{network}.json`

```json
{
  "componentId": "amanita_muscaria",
  "network": "localhost",
  "created_at": "2025-10-27T10:00:00Z",
  "updated_at": "2025-10-27T10:15:30Z",
  
  "steps_completed": [
    "simple_fields_uploaded",
    "complex_fields_uploaded",
    "shareable_data_uploaded",
    "root_metadata_updated",
    "root_metadata_uploaded",
    "component_registered"
  ],
  
  "simple_fields": {
    "title": {
      "cid": "QmTitleCID123...",
      "uploaded_at": "2025-10-27T10:05:00Z",
      "arweave_tx": "TX_ABC123..."
    },
    "dosage": {
      "cid": "QmDosageCID456...",
      "uploaded_at": "2025-10-27T10:06:00Z",
      "arweave_tx": "TX_DEF456..."
    }
  },
  
  "complex_fields": {
    "ru": { "cid": "QmRuCID789...", "uploaded_at": "2025-10-27T10:07:00Z" },
    "en": { "cid": "QmEnCID012...", "uploaded_at": "2025-10-27T10:08:00Z" },
    "es": { "cid": "QmEsCID345...", "uploaded_at": "2025-10-27T10:09:00Z" },
    "fr": { "cid": "QmFrCID678...", "uploaded_at": "2025-10-27T10:10:00Z" },
    "de": { "cid": "QmDeCID901...", "uploaded_at": "2025-10-27T10:11:00Z" },
    "nl": { "cid": "QmNlCID234...", "uploaded_at": "2025-10-27T10:12:00Z" },
    "et": { "cid": "QmEtCID567...", "uploaded_at": "2025-10-27T10:13:00Z" }
  },
  
  "root_metadata": {
    "cid": "QmRootCID890...",
    "uploaded_at": "2025-10-27T10:14:00Z",
    "arweave_tx": "TX_ROOT123...",
    "size_bytes": 15432
  },
  
  "contract_registration": {
    "componentId": "1",
    "txHash": "0x123abc...",
    "blockNumber": 12345,
    "gasUsed": "125000",
    "registered_at": "2025-10-27T10:15:00Z"
  }
}
```

**Resumable Uploads:**

If upload fails at any step, rerun the script — it will:
1. Load state file
2. Skip completed steps
3. Resume from last successful step
4. Update state after each step

---

## 🔗 Contract Integration

### **OrganicComponentRegistry (UUPS Proxy)**

**Purpose:** On-chain registry of organic components

**Key Functions:**

```solidity
// Create new component (seller only)
function createComponent(
    string memory biounit_id,
    string memory description_cid
) external onlyRole(SELLER_ROLE) returns (uint256);

// Check if component exists
function componentExists(string memory biounit_id) 
    external view returns (bool);

// Get component by ID
function getComponentById(uint256 componentId) 
    external view returns (OrganicComponent memory);

// Get component by business ID
function getComponentByBusinessId(string memory biounit_id) 
    external view returns (OrganicComponent memory);

// Get all components by seller
function getComponentsBySeller(address seller) 
    external view returns (uint256[] memory);

// Increment usage count (called by ProductRegistry)
function incrementUsageCount(string memory biounit_id) 
    external onlyRole(PRODUCT_REGISTRY_ROLE);
```

**Component Structure:**

```solidity
struct OrganicComponent {
    uint256 id;                    // Auto-incremented ID
    string biounit_id;             // Business identifier
    string description_cid;        // Arweave CID (root metadata)
    address creator;               // Component creator
    uint256 created_at;            // Creation timestamp
    uint256 usage_count;           // Times used in products
    bool active;                   // Active flag
}
```

### **AmanitaInternational (Localization Contract)**

**Purpose:** Store CID references for localized content

**Key Functions:**

```solidity
// Set simple field CID (short strings)
function setSimpleFieldCID(
    string memory fieldKey,
    string memory cid
) external onlyRole(CONTENT_MANAGER_ROLE);

// Set complex field CID (descriptions per language)
function setComplexFieldCID(
    string memory fieldKey,
    string memory language,
    string memory cid
) external onlyRole(CONTENT_MANAGER_ROLE);

// Get simple field CID
function getSimpleFieldCID(string memory fieldKey) 
    external view returns (string memory);

// Get complex field CID
function getComplexFieldCID(string memory fieldKey, string memory language) 
    external view returns (string memory);
```

**Storage Pattern:**

```yaml
Simple Fields:
  Key: "ComponentDescription.title.{biounit_id}"
  Value: "QmTitleCID123..."

Complex Fields:
  Key: "ComponentDescription.{lang}.{biounit_id}"
  Value: "QmDescriptionCID456..."

Example:
  - ComponentDescription.title.amanita_muscaria → QmTitleCID...
  - ComponentDescription.ru.amanita_muscaria → QmRuDescCID...
  - ComponentDescription.en.amanita_muscaria → QmEnDescCID...
```

---

## 🧪 Validation System

### **validate_component_upload.js**

**Purpose:** Validate completeness and correctness of Action 555 across all layers

**Usage:**

```bash
# Single component validation
node scripts/validators/validate_component_upload.js \
  --component amanita_muscaria \
  --network localhost

# With JSON output
node scripts/validators/validate_component_upload.js \
  --component blue_lotus \
  --network localhost \
  --json

# Custom seller (override .env)
node scripts/validators/validate_component_upload.js \
  --component lions_mane \
  --network localhost \
  --seller 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

### **4-Phase Validation**

#### **Phase 1: File System Validation (15% weight)**

```yaml
Checks:
  ✅ Component directory exists
  ✅ Root metadata file (component.json)
  ✅ Simple fields directory
    ├→ title.json exists
    └→ dosage.json exists
  ✅ Complex fields directory
    ├→ 7 language files present
    └→ ru.json, en.json, es.json, fr.json, de.json, nl.json, et.json
  ✅ State file exists
  ✅ Final metadata with CIDs populated

Scoring:
  - 10/10: All files present and valid
  - 7-9/10: Minor issues (e.g., missing 1 language)
  - 4-6/10: Major issues (e.g., no complex fields)
  - 0-3/10: Critical issues (e.g., no root file)
```

#### **Phase 2: Arweave Layer Validation (30% weight)**

```yaml
Checks:
  ✅ Root metadata CID accessible
  ✅ Simple field CIDs accessible
    ├→ title CID resolves
    └→ dosage CID resolves
  ✅ Complex field CIDs accessible (7 languages)
  ✅ CID content matches expected structure
  ✅ File size within reasonable limits (< 1MB per file)

Arweave Gateway Check:
  - Primary: https://arweave.net/{CID}
  - Fallback: https://gateway.irys.xyz/{CID}
  - Timeout: 10 seconds per request
  - Retry: 2 attempts

Scoring:
  - 10/10: All CIDs resolve, content valid
  - 7-9/10: 1-2 CIDs slow/timeout (recoverable)
  - 4-6/10: 3+ CIDs inaccessible
  - 0-3/10: Root CID inaccessible (critical)
```

#### **Phase 3: Contract Layer Validation (35% weight - CRITICAL)**

```yaml
Checks:
  ✅ Component exists in OrganicComponentRegistry
  ✅ componentExists(biounit_id) == true
  ✅ Component active flag == true
  ✅ Component creator matches expected seller
  ✅ Description CID matches uploaded root CID
  ✅ Component ID assigned (non-zero)
  ✅ Localization CIDs stored in AmanitaInternational
    ├→ title CID stored
    ├→ dosage CID stored
    └→ All 7 language CIDs stored

Action 444 Compatibility:
  - ✅ COMPATIBLE: Component can be used in products
  - ❌ INCOMPATIBLE: ProductRegistry will reject component reference
  - ⚠️ UNKNOWN: Contract not accessible (node down)

Scoring:
  - 10/10: Component fully registered, all CIDs stored
  - 7-9/10: Component registered, minor CID gaps
  - 4-6/10: Component registered, major CID gaps
  - 0-3/10: Component NOT registered (Action 444 will fail)
```

#### **Phase 4: State Consistency Validation (20% weight)**

```yaml
Checks:
  ✅ State file matches contract data
  ✅ All 6 steps marked completed
  ✅ CIDs in state == CIDs on-chain
  ✅ Transaction hashes valid
  ✅ Timestamps logical (sequential)
  ✅ No duplicate steps

State Steps:
  1. simple_fields_uploaded
  2. complex_fields_uploaded
  3. shareable_data_uploaded (first component only)
  4. root_metadata_updated
  5. root_metadata_uploaded
  6. component_registered

Scoring:
  - 10/10: Perfect consistency
  - 7-9/10: Minor inconsistencies (timestamps)
  - 4-6/10: CID mismatches (needs re-upload)
  - 0-3/10: State file corrupt/missing
```

### **Quality Score Calculation**

```javascript
Quality Score = (
  (Phase1_Score * 0.15) +  // File System: 15%
  (Phase2_Score * 0.30) +  // Arweave: 30%
  (Phase3_Score * 0.35) +  // Contract: 35% (CRITICAL)
  (Phase4_Score * 0.20)    // State: 20%
);

Passing Threshold: >= 8.0/10

Result:
  - 9.0-10.0: ✅ EXCELLENT - Production ready
  - 8.0-8.9:  ✅ PASS - Minor issues, acceptable
  - 6.0-7.9:  ⚠️ WARNING - Needs attention
  - 0.0-5.9:  ❌ FAIL - Critical issues, re-upload required
```

### **Validation Report Example**

```
================================================================================
🧪 COMPONENT VALIDATION REPORT
================================================================================

📦 Component: amanita_muscaria
🌐 Network: localhost
👤 Seller: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
⏰ Validation Time: 2025-10-27T10:30:00Z

────────────────────────────────────────────────────────────────────────────────
📁 PHASE 1: FILE SYSTEM VALIDATION (Weight: 15%)
────────────────────────────────────────────────────────────────────────────────

✅ Component directory exists
✅ Root metadata file: amanita_muscaria.json
✅ Simple fields (2/2):
   ✅ ComponentDescription.title.json
   ✅ DosageInstruction.description.json
✅ Complex fields (7/7):
   ✅ ComponentDescription.ru.json
   ✅ ComponentDescription.en.json
   ✅ ComponentDescription.es.json
   ✅ ComponentDescription.fr.json
   ✅ ComponentDescription.de.json
   ✅ ComponentDescription.nl.json
   ✅ ComponentDescription.et.json
✅ State file: state.amanita_muscaria.localhost.json
✅ Final metadata with CIDs populated

Phase 1 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
☁️ PHASE 2: ARWEAVE LAYER VALIDATION (Weight: 30%)
────────────────────────────────────────────────────────────────────────────────

✅ Root CID accessible: QmRootCID890... (12.3 KB)
✅ Title CID accessible: QmTitleCID123... (456 bytes)
✅ Dosage CID accessible: QmDosageCID456... (1.2 KB)
✅ Language CIDs accessible (7/7):
   ✅ ru: QmRuCID789... (8.7 KB)
   ✅ en: QmEnCID012... (7.3 KB)
   ✅ es: QmEsCID345... (8.1 KB)
   ✅ fr: QmFrCID678... (8.5 KB)
   ✅ de: QmDeCID901... (8.0 KB)
   ✅ nl: QmNlCID234... (7.9 KB)
   ✅ et: QmEtCID567... (7.5 KB)

Average Response Time: 245ms
Total Storage: 62.9 KB

Phase 2 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
⛓️ PHASE 3: CONTRACT LAYER VALIDATION (Weight: 35%)
────────────────────────────────────────────────────────────────────────────────

✅ Component exists in OrganicComponentRegistry
✅ Component ID: 1
✅ Component active: true
✅ Creator: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
✅ Description CID: QmRootCID890...
✅ Usage count: 17 (used in 17 products)

✅ Localization in AmanitaInternational:
   ✅ title CID: QmTitleCID123...
   ✅ dosage CID: QmDosageCID456...
   ✅ ru CID: QmRuCID789...
   ✅ en CID: QmEnCID012...
   ✅ es CID: QmEsCID345...
   ✅ fr CID: QmFrCID678...
   ✅ de CID: QmDeCID901...
   ✅ nl CID: QmNlCID234...
   ✅ et CID: QmEtCID567...

🎯 Action 444 Compatible: ✅ COMPATIBLE
   Component can be used in product creation

Phase 3 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
📊 PHASE 4: STATE CONSISTENCY VALIDATION (Weight: 20%)
────────────────────────────────────────────────────────────────────────────────

✅ State file exists and valid
✅ All 6 steps completed:
   ✅ simple_fields_uploaded
   ✅ complex_fields_uploaded
   ✅ shareable_data_uploaded
   ✅ root_metadata_updated
   ✅ root_metadata_uploaded
   ✅ component_registered

✅ CID consistency: All CIDs match contract
✅ Transaction hashes valid
✅ Timestamps sequential

Phase 4 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
🎯 FINAL QUALITY SCORE
────────────────────────────────────────────────────────────────────────────────

Phase 1 (File System):       10.0/10 × 15% = 1.50
Phase 2 (Arweave):            10.0/10 × 30% = 3.00
Phase 3 (Contract):           10.0/10 × 35% = 3.50
Phase 4 (State):              10.0/10 × 20% = 2.00
                                           ──────
                             Quality Score: 10.0/10 ✅ EXCELLENT

Status: ✅ VALIDATION PASSED
Component Ready: ✅ Production use approved
Action 444 Ready: ✅ Can be referenced in products

================================================================================
```

---

## 📚 Usage Examples

### **Example 1: Upload First Component (with Shareable Data)**

```bash
# 1. Activate seller (if not already activated)
DEPLOY_ACTION=888 \
DEPLOYER_INVITE=AMANITA-ROOT-0001 \
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
npx hardhat run scripts/deploy_full.js --network localhost

# 2. Upload component with shareable data
DEPLOY_ACTION=555 \
UPLOAD_SHAREABLE=true \
npx hardhat run scripts/deploy_full.js --network localhost

# 3. Validate component
node scripts/validators/validate_component_upload.js \
  --component amanita_muscaria \
  --network localhost
```

### **Example 2: Upload Additional Components**

```bash
# Upload without shareable data (already uploaded)
DEPLOY_ACTION=555 \
UPLOAD_SHAREABLE=false \
npx hardhat run scripts/deploy_full.js --network localhost

# Validate
node scripts/validators/validate_component_upload.js \
  --component blue_lotus \
  --network localhost
```

### **Example 3: Batch Validation**

```bash
# Validate all components in data/components/
for comp in data/components/*/; do
  component=$(basename "$comp")
  [[ "$component" == "component_features_presets.json" ]] && continue
  
  echo "=== Validating: $component ==="
  node scripts/validators/validate_component_upload.js \
    --component "$component" \
    --network localhost \
    | grep -E "Quality Score|Action 444"
  echo ""
done
```

### **Example 4: Programmatic Validation**

```javascript
const { validateComponent } = require('./scripts/validators/validate_component_upload.js');

async function checkBeforeProductCreation() {
  const components = ['amanita_muscaria', 'blue_lotus', 'lions_mane'];
  
  for (const comp of components) {
    const report = await validateComponent(comp, 'localhost');
    
    if (!report.passed) {
      console.error(`❌ Component ${comp} validation failed: ${report.qualityScore}/10`);
      process.exit(1);
    }
    
    if (!report.contract.action444Compatible) {
      console.error(`❌ Component ${comp} not compatible with Action 444`);
      process.exit(1);
    }
    
    console.log(`✅ Component ${comp} ready: ${report.qualityScore}/10`);
  }
  
  console.log('✅ All components validated, proceeding with Action 444...');
}

checkBeforeProductCreation();
```

---

## 🔧 Troubleshooting

### **Issue 1: Component Not Found in Contract**

**Symptom:**
```
❌ Phase 3 Score: 0.0/10
❌ Action 444 Compatible: INCOMPATIBLE
Error: Component does not exist in OrganicComponentRegistry
```

**Root Cause:** Step 6 (component_registered) failed during upload

**Solution:**
```bash
# Check state file
cat data/components/your_component/state.your_component.localhost.json

# If "component_registered" missing, re-run Action 555
DEPLOY_ACTION=555 npx hardhat run scripts/deploy_full.js --network localhost

# Validate again
node scripts/validators/validate_component_upload.js --component your_component --network localhost
```

### **Issue 2: CIDs Not Accessible on Arweave**

**Symptom:**
```
⚠️ Phase 2 Score: 4.5/10
⚠️ Warning: 3/9 CIDs timed out
```

**Root Cause:** Arweave gateway slow/unreachable, or CID not yet propagated

**Solution:**
```bash
# 1. Wait 5-10 minutes for Arweave propagation
sleep 600

# 2. Retry validation
node scripts/validators/validate_component_upload.js --component your_component --network localhost

# 3. If still failing, check CID manually
curl https://arweave.net/YOUR_CID

# 4. Try alternative gateway
curl https://gateway.irys.xyz/YOUR_CID
```

### **Issue 3: State File Corrupted**

**Symptom:**
```
❌ Phase 4 Score: 2.0/10
Error: CID mismatch between state and contract
```

**Root Cause:** State file out of sync with contract

**Solution:**
```bash
# 1. Backup current state
cp data/components/your_component/state.your_component.localhost.json \
   data/components/your_component/state.backup.json

# 2. Delete state file
rm data/components/your_component/state.your_component.localhost.json

# 3. Re-run validation (will rebuild state from contract)
node scripts/validators/validate_component_upload.js --component your_component --network localhost
```

### **Issue 4: Missing Language Files**

**Symptom:**
```
⚠️ Phase 1 Score: 6.5/10
Warning: Missing complex fields: found 4, expected 7
```

**Root Cause:** Not all language files created

**Solution:**
```bash
# 1. Check which languages missing
ls data/components/your_component/complex_fields/

# 2. Create missing language files
cd data/components/your_component/complex_fields/
cp your_component.ComponentDescription.en.json \
   your_component.ComponentDescription.es.json

# Edit es.json with Spanish translations

# 3. Re-upload
DEPLOY_ACTION=555 npx hardhat run scripts/deploy_full.js --network localhost
```

### **Issue 5: Arweave Balance Too Low**

**Symptom:**
```
❌ Error: Insufficient Arweave balance
Current: 0.005 AR
Required: >= 0.01 AR
```

**Root Cause:** Not enough AR tokens for upload

**Solution:**
```bash
# 1. Check current balance
cat .arweave-key.json | npx arweave balance

# 2. Get more AR from faucet (testnet)
# Visit: https://faucet.arweave.net

# 3. Or use mainnet wallet with sufficient balance
```

---

## 📖 API Reference

### **ComponentActions.action555()**

Upload seller activation + components

**Signature:**
```javascript
async action555()
```

**Environment Variables:**
```yaml
Required:
  - DEPLOYER_INVITE: Root invite code
  - SELLER_ADDRESS: Seller Ethereum address
  - SELLER_PRIVATE_KEY: Seller private key

Optional:
  - UPLOAD_SHAREABLE: Upload shared dictionaries (default: false)
  - DRY_RUN: Simulate without actual upload (default: false)
```

**Returns:**
```javascript
{
  success: true,
  sellerAddress: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  activated: true,
  rolesGranted: ["SELLER_ROLE", "ACTIVATOR_ROLE"],
  invites: ["AMANITA-A1B2-C3D4", ...],
  componentsUploaded: 3,
  totalCIDs: 27,
  arweaveFees: "0.05 AR"
}
```

### **validateComponent(componentId, network, sellerAddress)**

Validate component across 4 phases

**Signature:**
```javascript
async function validateComponent(componentId, network = 'localhost', sellerAddress = null)
```

**Parameters:**
- `componentId` (string): Component business ID (e.g., "amanita_muscaria")
- `network` (string): Network name (default: "localhost")
- `sellerAddress` (string): Seller address (default: from .env)

**Returns:**
```javascript
{
  componentId: "amanita_muscaria",
  network: "localhost",
  sellerAddress: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  
  filesystem: { score: 10.0, errors: [] },
  arweave: { score: 10.0, cidsAccessible: 9, totalCIDs: 9 },
  contract: { score: 10.0, exists: true, active: true, action444Compatible: true },
  state: { score: 10.0, consistent: true },
  
  qualityScore: 10.0,
  passed: true,
  timestamp: "2025-10-27T10:30:00Z"
}
```

### **OrganicComponentRegistry.createComponent()**

Register component on-chain

**Signature:**
```solidity
function createComponent(
    string memory biounit_id,
    string memory description_cid
) external onlyRole(SELLER_ROLE) returns (uint256)
```

**Parameters:**
- `biounit_id`: Component business ID (e.g., "amanita_muscaria")
- `description_cid`: Arweave CID of root metadata

**Returns:**
- `uint256`: Component ID (auto-incremented)

**Events:**
```solidity
event ComponentCreated(
    uint256 indexed componentId,
    string indexed biounit_id,
    address indexed creator,
    string description_cid
);
```

### **AmanitaInternational.setSimpleFieldCID()**

Store CID for simple field

**Signature:**
```solidity
function setSimpleFieldCID(
    string memory fieldKey,
    string memory cid
) external onlyRole(CONTENT_MANAGER_ROLE)
```

**Parameters:**
- `fieldKey`: Key format "ComponentDescription.title.{biounit_id}"
- `cid`: Arweave CID

**Example:**
```javascript
await amanitaIntl.setSimpleFieldCID(
  "ComponentDescription.title.amanita_muscaria",
  "QmTitleCID123..."
);
```

---

## 📊 Component Metrics & Analytics

### **Usage Tracking**

Each time a component is used in a product, `OrganicComponentRegistry.incrementUsageCount()` is called:

```javascript
// In ProductRegistry.createProduct()
for (const component of components) {
  await organicRegistry.incrementUsageCount(component.biounit_id);
}
```

**Query Most Popular Components:**

```javascript
const components = await organicRegistry.getAllComponents();
const sorted = components.sort((a, b) => b.usage_count - a.usage_count);

console.log("Top 10 Components:");
sorted.slice(0, 10).forEach((comp, i) => {
  console.log(`${i+1}. ${comp.biounit_id}: ${comp.usage_count} uses`);
});
```

### **Storage Costs**

```yaml
Average Component Storage:
  - Root metadata: ~15 KB
  - Title (7 languages): ~0.5 KB
  - Dosage (7 languages): ~1.2 KB
  - Descriptions (7 languages): ~55 KB (7.5 KB × 7)
  - Total: ~72 KB per component

Arweave Costs (approximate):
  - Per KB: ~0.00001 AR
  - Per Component: ~0.00072 AR
  - 100 Components: ~0.072 AR (~$1.50 at $20/AR)
```

---

## 🚀 Next Steps

### **For Developers**

1. **Create New Component**
   - Follow structure in [Component Structure](#component-structure)
   - Use existing component as template
   - Test with dry-run first

2. **Upload to Testnet**
   - Use Mumbai (Polygon testnet)
   - Get testnet MATIC from faucet
   - Validate before mainnet

3. **Validate Before Production**
   - Run validation script
   - Ensure Quality Score >= 8.0
   - Check Action 444 compatibility

### **For Content Creators**

1. **Research & Documentation**
   - Gather scientific sources
   - Document traditional uses
   - Verify safety information

2. **Translation**
   - Start with English (most important)
   - Use professional translation services
   - Maintain consistent terminology

3. **Quality Assurance**
   - Peer review content
   - Verify dosage instructions
   - Check legal compliance

### **For System Administrators**

1. **Monitoring**
   - Track upload success rates
   - Monitor Arweave costs
   - Alert on validation failures

2. **Backup & Recovery**
   - Regular state file backups
   - CID archive for disaster recovery
   - Contract event log backup

3. **Performance Optimization**
   - Cache popular components
   - CDN for IPFS gateway
   - Batch validation scripts

---

## 📚 See Also

### **Related Documentation**
- **[actions/Component.md](./actions/Component.md)** - ComponentActions detailed architecture
- **[actions/Catalog.md](./actions/Catalog.md)** - How components integrate with products
- **[CATALOG_PIPELINE.md](./CATALOG_PIPELINE.md)** - Full catalog upload process
- **[contracts/docs/OrganicComponentRegistry.md](../contracts/docs/OrganicComponentRegistry.md)** - Smart contract specification

### **Technical References**
- **Arweave Documentation:** https://docs.arweave.org
- **IPFS Documentation:** https://docs.ipfs.tech
- **OpenZeppelin UUPS:** https://docs.openzeppelin.com/contracts/api/proxy

### **Integration Points**
```yaml
Upstream Dependencies:
  - Action 1: Deploy contracts
  - Action 777: Create root invites
  - Action 888: Activate seller

Component Pipeline:
  - Action 555: Upload components
  - validate_component_upload.js: Validate components

Downstream Integrations:
  - Action 444: Catalog upload (uses components)
  - ProductRegistry: Product creation (references components)
  - Telegram Bot: Display component info to users
```

---

**Version:** 2.0  
**Status:** ✅ Production Ready  
**Last Updated:** 2025-10-27  
**Maintainer:** Amanita Development Team  
**License:** MIT

