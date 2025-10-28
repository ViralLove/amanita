# 🛒 Product Catalog Architecture - Complete Pipeline & Validation

**Version:** 2.0  
**Date:** 2025-10-27  
**Methodology:** @analysis.mdc  
**Status:** ✅ Production Ready

---

## 📋 Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Core Concepts](#core-concepts)
3. [Product Structure](#product-structure)
4. [CSV to JSON Transformation](#csv-to-json-transformation)
5. [Localization Architecture](#localization-architecture)
6. [Upload Pipeline](#upload-pipeline)
7. [Contract Integration](#contract-integration)
8. [Component Integration](#component-integration)
9. [Validation System](#validation-system)
10. [Usage Examples](#usage-examples)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## 🎯 Overview & Purpose

### **What is the Product Catalog?**

The **Product Catalog** is a multi-seller marketplace system that enables sellers to create, manage, and sell products composed of **organic components**. Each product references one or more components from the shared registry, creating a decentralized, transparent supply chain.

### **Key Objectives**

```yaml
Multi-Seller Ecosystem:
  - Each seller maintains independent catalog
  - Products reference shared organic components
  - Decentralized ownership & management
  - Transparent pricing & inventory

Product Composition:
  - Products = Component(s) + Form + Proportion
  - Example: "Amanita Tincture 50ml" = amanita_muscaria + tincture + 50ml
  - Component reusability across sellers
  - Flexible composition (single/multi-component)

Localization:
  - Multi-language titles (7 core languages)
  - CID-based storage (Arweave)
  - Translation workflow support
  - Fallback to source language

Blockchain Integration:
  - ProductRegistry: On-chain product records
  - Immutable product metadata
  - Seller ownership verification
  - Activation/suspension lifecycle
```

### **Architecture Principles**

- ✅ **CSV-First Workflow**: Sellers provide simple CSV catalogs
- ✅ **Component-Based**: Products built from shared component library
- ✅ **Decentralized Storage**: Arweave for immutable metadata
- ✅ **Multi-Language Support**: 7 languages with translation stubs
- ✅ **Validation-Driven**: 6-phase validation before production
- ✅ **Resumable Pipeline**: State management for fault tolerance

---

## 🏗️ Core Concepts

### **1. Product Identity**

```yaml
Product ID (product_business_id):
  Format: "{component}_{form}_{variant}"
  Examples: 
    - "amanita_tincture_50ml"
    - "blue_lotus_tea_organic"
    - "lions_mane_capsules_500mg"
  Requirements:
    - Unique within seller's catalog
    - Immutable after registration
    - Used for contract storage key

Seller ID:
  Format: "seller_name" or "seller_businessname"
  Examples: "iveta_zeya888", "seller_123"
  Purpose: Namespace for products
```

### **2. Product Components**

Products reference components from `OrganicComponentRegistry`:

```json
{
  "components": [
    {
      "component_business_id": "amanita_muscaria",
      "proportion": "100%",
      "form": "tincture",
      "notes": "Wild-harvested from Siberian forests"
    }
  ]
}
```

**Single-Component Products** (most common):
- One component at 100%
- Form inherited from component's available forms
- Example: "Amanita Tincture" = 100% amanita_muscaria

**Multi-Component Products** (blends):
- Multiple components with proportions
- Example: "Stress Relief Blend" = 40% amanita + 30% blue_lotus + 30% lions_mane

### **3. Product Forms**

Forms must match component's available forms:

```json
{
  "forms": ["tincture"],
  "components": [
    {
      "component_business_id": "amanita_muscaria",
      "form": "tincture"  // Must be in component's forms array
    }
  ]
}
```

**Form Validation:**
- ✅ Form exists in `bot/catalog/component_forms.json`
- ✅ Form available for referenced component
- ❌ Reject if form not supported by component

### **4. Product Pricing**

```json
{
  "prices": [
    {
      "amount": "29.99",
      "currency": "EUR",
      "unit": "bottle"
    }
  ]
}
```

**Pricing Rules:**
- Amount: Decimal string (e.g., "29.99")
- Currency: ISO 4217 code (EUR, USD, GBP)
- Unit: Descriptive unit (bottle, jar, pack, etc.)
- Multiple prices: Different currencies/sizes

### **5. Product Lifecycle**

```yaml
States:
  1. Created: Product registered in ProductRegistry
  2. Inactive: Exists but not visible in catalog
  3. Active: Visible and purchasable
  4. Suspended: Temporarily unavailable
  5. Deprecated: Removed from catalog

Transitions:
  Created → Inactive (default after registration)
  Inactive → Active (activateProduct())
  Active → Suspended (suspendProduct())
  Suspended → Active (activateProduct())
  Any → Deprecated (deprecateProduct())
```

---

## 📦 Product Structure

### **Directory Layout**

```
data/sellers/{seller_id}/
├── catalog/
│   └── {seller}_catalog.csv                 # ✅ Input CSV
├── output/
│   └── products/
│       ├── {product_id}/                    # ✅ Product directory
│       │   ├── {product_id}.json            # Product metadata
│       │   ├── {product_id}.titles.json     # Multi-language titles
│       │   ├── translations/                # Translation workspace
│       │   │   └── title.json               # Translation stubs
│       │   └── README.md                    # Translation guide
│       ├── product_combined_mapping.json    # ✅ CID mappings
│       └── image_cid_mapping.json           # Image CIDs
└── images/                                  # Product images
    └── {product_id}.{ext}
```

### **CSV Structure**

**Required Columns:**

```csv
component_business_id,product_business_id,product_name,image_file,form,prices
amanita_muscaria,amanita_tincture_50ml,Amanita — LUX,amanita_lux.jpg,tincture,"29.99 EUR"
blue_lotus,blue_lotus_tea_organic,Blue Lotus Tea,blue_lotus_tea.jpg,tea_bags,"19.99 EUR, 24.99 USD"
```

**Column Definitions:**

```yaml
component_business_id:
  Type: String
  Description: Component reference from OrganicComponentRegistry
  Example: "amanita_muscaria"
  Validation: Must exist in component registry

product_business_id:
  Type: String
  Description: Unique product identifier
  Example: "amanita_tincture_50ml"
  Validation: Unique within seller catalog

product_name:
  Type: String
  Description: Product title in source language
  Example: "Amanita — LUX"
  Note: Will be translated to 7 languages

image_file:
  Type: String
  Description: Image filename in images/ directory
  Example: "amanita_lux.jpg"
  Validation: File must exist

form:
  Type: String
  Description: Product form (must match component forms)
  Example: "tincture", "tea_bags", "capsules"
  Validation: Must be in component_forms.json

prices:
  Type: String (comma-separated)
  Description: Prices in format "amount currency"
  Example: "29.99 EUR, 24.99 USD"
  Validation: Valid amount and ISO currency code
```

### **Product JSON (`{product_id}.json`)**

```json
{
  "product_id": "amanita_tincture_50ml",
  "seller_id": "iveta_zeya888",
  "created_at": "2025-10-27T10:00:00Z",
  "last_updated": "2025-10-27T10:00:00Z",
  "created_by": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  
  "title": null,  // CID placeholder (filled during upload)
  
  "components": [
    {
      "component_business_id": "amanita_muscaria",
      "proportion": "100%",
      "form": "tincture",
      "form_mapping_confidence": 1.0,
      "form_original": "tincture",
      "notes": ""
    }
  ],
  
  "forms": ["tincture"],
  
  "prices": [
    {
      "amount": "29.99",
      "currency": "EUR",
      "unit": "bottle"
    }
  ],
  
  "images": {
    "cover": "amanita_lux.jpg",
    "cover_cid": null,  // Filled during upload
    "cover_url": null,
    "gallery": []
  },
  
  "metadata": {
    "version": "1.0",
    "schema_version": "1.0",
    "status": "active",
    "transformation": {
      "from_csv": "data/sellers/iveta/catalog/Iveta_catalog.csv",
      "transformed_at": "2025-10-27T10:00:00Z",
      "form_mapping_type": "exact",
      "form_mapping_confidence": 1.0
    },
    "translation_status": {
      "source_language": "en",
      "completed": ["en"],
      "pending": ["ru", "et", "es", "fr", "de", "nl"],
      "has_stubs": true
    }
  }
}
```

### **Title Translations (`{product_id}.titles.json`)**

```json
{
  "ru": "Аманита — ЛЮКС",
  "et": "Amanita — LUX",
  "en": "Amanita — LUX",
  "es": "[NEEDS TRANSLATION] Amanita — LUX",
  "fr": "[NEEDS TRANSLATION] Amanita — LUX",
  "de": "[NEEDS TRANSLATION] Amanita — LUX",
  "nl": "[NEEDS TRANSLATION] Amanita — LUX"
}
```

**Translation Workflow:**
1. Source title extracted from CSV
2. Title file created with source language + stubs
3. Translator edits `translations/title.json`
4. Action 42 uploads translated titles to Arweave
5. CIDs stored in AmanitaInternational contract

---

## 🔄 CSV to JSON Transformation

### **Action 41: Transform CSV to JSON**

**Purpose:** Convert CSV catalog to structured JSON products with translation support

**Script:** `scripts/transform_products_csv.js`

**Usage:**

```bash
# Transform with default settings
node scripts/transform_products_csv.js \
  --csv data/sellers/iveta/catalog/Iveta_catalog.csv \
  --output data/sellers/iveta/output/products/ \
  --seller-id iveta_zeya888

# With translation stubs
node scripts/transform_products_csv.js \
  --csv data/sellers/iveta/catalog/Iveta_catalog.csv \
  --output data/sellers/iveta/output/products/ \
  --seller-id iveta_zeya888 \
  --create-stubs

# Dry-run (no file creation)
DRY_RUN=true node scripts/transform_products_csv.js --csv ...
```

### **Transformation Process (8 Steps)**

```yaml
Step 1: Validate Product ID
  - Check format (lowercase, underscores)
  - Check uniqueness in catalog
  - Validate against naming rules

Step 2: Validate Component
  - Check component exists in OrganicComponentRegistry
  - Load component metadata
  - Verify component active

Step 3: Map Form
  - Parse form from CSV
  - Match against component's available forms
  - Calculate mapping confidence (0.0-1.0)
  - Warn if confidence < 0.8

Step 4: Parse Prices
  - Extract amount, currency, unit
  - Validate currency codes (ISO 4217)
  - Support multiple prices per product

Step 5: Handle Images
  - Verify image file exists
  - Store filename (CID added during upload)
  - Support gallery images (optional)

Step 6: Create Product JSON
  - Assemble complete product structure
  - Add metadata (transformation info)
  - Set default status (inactive)

Step 7: Add Translation Metadata
  - Detect source language
  - Mark translations as pending
  - Create translation status object

Step 8: Save Files
  - Save product JSON
  - Create titles JSON (source + stubs)
  - Create translation workspace (if --create-stubs)
  - Generate README for translators
```

### **Form Mapping Algorithm**

**Confidence Levels:**

```yaml
Exact Match (1.0):
  Input: "tincture"
  Component forms: ["tincture", "dried"]
  Result: "tincture" (confidence: 1.0)

Fuzzy Match (0.8-0.99):
  Input: "Настойка" (Russian)
  Component forms: ["tincture", "dried"]
  Result: "tincture" (confidence: 0.85)
  Note: Uses transliteration + levenshtein distance

Partial Match (0.6-0.79):
  Input: "alcohol extract"
  Component forms: ["tincture", "dried"]
  Result: "tincture" (confidence: 0.7)
  Note: Keyword matching

Default (0.5):
  Input: "unknown_form"
  Component forms: ["dried", "powder"]
  Result: "dried" (confidence: 0.5)
  Note: Falls back to first form, requires manual review
```

### **Translation Stub Generation**

**File:** `translations/title.json`

```json
{
  "product_id": "amanita_tincture_50ml",
  "source_language": "en",
  "translations": {
    "ru": "[NEEDS TRANSLATION] Amanita — LUX",
    "et": "[NEEDS TRANSLATION] Amanita — LUX",
    "en": "Amanita — LUX",
    "es": "[NEEDS TRANSLATION] Amanita — LUX",
    "fr": "[NEEDS TRANSLATION] Amanita — LUX",
    "de": "[NEEDS TRANSLATION] Amanita — LUX",
    "nl": "[NEEDS TRANSLATION] Amanita — LUX"
  },
  "created_at": "2025-10-27T10:00:00Z",
  "last_updated": "2025-10-27T10:00:00Z",
  "translation_notes": "Edit this file to add translations for each language. Remove [NEEDS TRANSLATION] prefix when done."
}
```

**README.md for Translators:**

```markdown
# Translation Instructions: amanita_tincture_50ml

## File to Edit
`translations/title.json`

## How to Translate
1. Open `translations/title.json`
2. Replace `[NEEDS TRANSLATION]` with actual translation
3. Save file
4. After all translations complete, run Action 42 to upload to Arweave

## Example:
```json
"es": "Amanita — LUX"  // Was: [NEEDS TRANSLATION] Amanita — LUX
```

## Supported Languages
- **ru**: Russian (Русский)
- **et**: Estonian (Eesti)
- **en**: English
- **es**: Spanish (Español)
- **fr**: French (Français)
- **de**: German (Deutsch)
- **nl**: Dutch (Nederlands)

## Important!
- Keep JSON formatting (quotes, commas)
- Do not change file structure
- Do not remove language keys
- Verify translation correctness before saving
```

---

## 🌍 Localization Architecture

### **Supported Languages**

```yaml
Core Languages (7):
  - ru: Russian (Русский)
  - et: Estonian (Eesti)
  - en: English
  - es: Spanish (Español)
  - fr: French (Français)
  - de: German (Deutsch)
  - nl: Dutch (Nederlands)

Note: Same as component localization for consistency
```

### **Localization Layers**

```yaml
Layer 1: CSV Source
  - Single title in source language
  - Extracted during transformation
  - Used as base for all translations

Layer 2: JSON Files (File System)
  - {product_id}.titles.json
  - Source language + translation stubs
  - Manual translation by sellers/translators

Layer 3: Arweave Storage
  - Each title file → Unique CID
  - Immutable after upload
  - Versioned (can upload new version with new CID)

Layer 4: Contract (AmanitaInternational)
  - Stores CID reference only
  - Key format: "ProductName.{product_id}"
  - Gas-optimized: No full text on-chain

Layer 5: Bot (ProductLocalizationService)
  - Cache: In-memory + Redis
  - Fallback: Source language if translation missing
  - IPFS Gateway: Fetch from CID
  - Format: JSON → User-friendly display

Layer 6: UI (Telegram Bot)
  - User language detection
  - Dynamic product display
  - Price formatting per locale
  - Inline keyboard localization
```

### **Localization Flow**

```yaml
1. CSV Input (Action 41):
   CSV: "Amanita — LUX" (en)
     ↓
   Transform to JSON + Title files
     ├→ product.json (metadata)
     └→ product.titles.json (en + 6 stubs)

2. Translation Phase (Manual):
   Translator edits: translations/title.json
     ├→ ru: "Аманита — ЛЮКС"
     ├→ et: "Amanita — LUX"
     ├→ es: "Amanita — LUJO"
     └→ ... (all languages)

3. Upload Phase (Action 42):
   Upload product.titles.json → Arweave
     ↓
   Generate CID: QmTitleCID123...
     ↓
   Store in AmanitaInternational:
     Key: "ProductName.amanita_tincture_50ml"
     Value: "QmTitleCID123..."

4. Product Creation (Action 43):
   Register in ProductRegistry
     ├→ Store product_id, seller, component refs
     ├→ Title stored as CID reference
     └→ Mark as inactive (default)

5. User Interaction (Bot):
   User selects language: ru
     ↓
   Bot fetches product from ProductRegistry
     ↓
   Load title CID from AmanitaInternational
     ↓
   Fetch from Arweave: QmTitleCID123...
     ↓
   Extract title: "Аманита — ЛЮКС"
     ↓
   Display to user with product details
```

### **Fallback Strategy**

```yaml
User Language: ru
  ↓
Try: ProductName.{product_id} → Fetch CID → Parse JSON → Get "ru"
  ↓
Success? → Return Russian title
  ↓
Fail (translation not ready)? → Get "en" (source language)
  ↓
Success? → Return English title (fallback)
  ↓
Fail? → Return product_id as display name (last resort)
```

---

## 🚀 Upload Pipeline

### **Action 444: Automatic Pipeline (CSV → Blockchain)**

**Purpose:** Complete end-to-end pipeline from CSV to active products on blockchain

**Flow:**

```yaml
Input: CSV file path + seller configuration
  ↓
Phase 1: Action 41 (Transform CSV → JSON)
  ├→ Parse CSV
  ├→ Validate products
  ├→ Map forms
  ├→ Create product JSONs
  └→ Generate title translation files
  ↓
Phase 2: Action 42 (Upload to Arweave)
  ├→ Upload product titles (7 languages each)
  ├→ Upload product images
  ├→ Upload product metadata JSONs
  ├→ Store title CIDs in AmanitaInternational
  └→ Create CID mapping files
  ↓
Phase 3: Action 43 (Register in Contract)
  ├→ Step 0: Clear existing catalog (Fix 2)
  ├→ Step 1: Register products in ProductRegistry
  ├→ Step 2: Activate products
  └→ Step 3: Validate registration
  ↓
Output: Complete product catalog live on blockchain
```

### **Action 41: CSV Transformation**

See [CSV to JSON Transformation](#csv-to-json-transformation) section above.

### **Action 42: Arweave Upload**

**Purpose:** Upload product data to Arweave + store CIDs in contracts

**Process:**

```yaml
Step 1: Initialize Arweave
  ├→ Load key from .arweave-key.json
  ├→ Check balance (>= 0.01 AR required)
  └→ Verify network connection

Step 2: Prepare Contracts
  ├→ Load AmanitaInternational (UUPS proxy)
  ├→ Load ProductRegistry (UUPS proxy)
  └→ Verify seller has SELLER_ROLE

Step 3: Upload Title Files (Per Product)
  ├→ Load {product_id}.titles.json
  ├→ Upload to Arweave → CID_title
  ├→ Store in AmanitaInternational:
  │   Key: "ProductName.{product_id}"
  │   Value: CID_title
  ├→ Delay 500ms (nonce management)
  └→ Update title_cid_mapping.json

Step 4: Upload Product Images (Per Product)
  ├→ Load image from images/ directory
  ├→ Upload to Arweave → CID_image
  ├→ Update product JSON: images.cover_cid = CID_image
  └→ Update image_cid_mapping.json

Step 5: Upload Product Metadata (Per Product)
  ├→ Load updated product JSON (with CIDs)
  ├→ Upload to Arweave → CID_product
  ├→ Update product_cid_mapping.json
  └→ This CID used for contract registration

Step 6: Create Combined Mapping File
  ├→ Merge title, image, product mappings
  ├→ Save to product_combined_mapping.json
  └→ Used by Action 43 for registration
```

**Mapping File Format (`product_combined_mapping.json`):**

```json
{
  "amanita_tincture_50ml": {
    "product_id": "amanita_tincture_50ml",
    "title_cid": "QmTitleCID123...",
    "image_cid": "QmImageCID456...",
    "metadata_cid": "QmProductCID789...",
    "uploaded_at": "2025-10-27T10:15:00Z"
  },
  "blue_lotus_tea_organic": {
    "product_id": "blue_lotus_tea_organic",
    "title_cid": "QmTitleCID234...",
    "image_cid": "QmImageCID567...",
    "metadata_cid": "QmProductCID890...",
    "uploaded_at": "2025-10-27T10:16:00Z"
  }
}
```

### **Action 43: Contract Registration & Activation**

**Purpose:** Register products in ProductRegistry and activate them

**Process:**

```yaml
Step 0: Clear Existing Catalog (Fix 2 - v2.0)
  ├→ Load seller's existing products
  ├→ If products exist:
  │   ├→ Call productRegistry.clearSellerCatalog(seller)
  │   ├→ Wait for transaction confirmation
  │   └→ Delay 500ms (nonce management)
  └→ If no products: Skip (catalog already empty)

Step 1: Register Products (Per Product)
  ├→ Load product data from JSON
  ├→ Load CIDs from product_combined_mapping.json
  ├→ Extract component references
  ├→ Call productRegistry.createProduct():
  │   ├→ product_id (string)
  │   ├→ seller (address)
  │   ├→ metadata_cid (string)
  │   ├→ component_ids (string[])
  │   └→ forms (string[])
  ├→ Wait for transaction confirmation
  ├→ Delay 500ms (nonce management)
  └→ Store contract product ID

Step 2: Activate Products (Batch)
  ├→ Collect all registered product IDs
  ├→ Call productRegistry.activateProducts(productIds[])
  ├→ Wait for transaction confirmation
  └→ All products become active simultaneously

Step 3: Validate Registration
  ├→ For each product:
  │   ├→ Verify exists in contract
  │   ├→ Verify active flag = true
  │   ├→ Verify seller = expected
  │   └→ Verify metadata CID matches
  └→ Report success/failures
```

**Fix 2 Impact:**

```yaml
Before Fix 2:
  - Multiple Action 444 runs → Duplicate products
  - CSV: 17 products
  - Contract: 34 products (duplicates!)
  - Phase 4 Score: 5.0/10 ❌

After Fix 2:
  - Step 0 clears catalog before registration
  - CSV: 17 products
  - Contract: 17 products ✅
  - Phase 4 Score: 10.0/10 ✅
```

### **State Management**

Unlike component uploads, product pipeline uses **mapping files** for state:

```yaml
State Files:
  - title_cid_mapping.json: Title CIDs per product
  - image_cid_mapping.json: Image CIDs per product
  - product_cid_mapping.json: Metadata CIDs per product
  - product_combined_mapping.json: All CIDs combined

Benefits:
  - Resume uploads from any point
  - Skip already-uploaded files
  - Track CID mappings
  - Validate completeness
```

---

## 🔗 Contract Integration

### **ProductRegistry (UUPS Proxy)**

**Purpose:** On-chain registry of seller products

**Key Functions:**

```solidity
// Create new product (seller only)
function createProduct(
    string memory product_id,
    address seller,
    string memory metadata_cid,
    string[] memory component_ids,
    string[] memory forms
) external onlyRole(SELLER_ROLE) returns (uint256);

// Activate multiple products (batch operation)
function activateProducts(uint256[] memory productIds) 
    external onlyRole(SELLER_ROLE);

// Check if product exists
function productExists(string memory product_id) 
    external view returns (bool);

// Get product by ID
function getProductById(uint256 productId) 
    external view returns (Product memory);

// Get all products by seller
function getProductsBySeller(address seller) 
    external view returns (uint256[] memory);

// Clear seller's catalog (Fix 2)
function clearSellerCatalog(address seller) 
    external onlyRole(SELLER_ROLE);

// Get active products only
function getAllActiveProductIds() 
    external view returns (uint256[] memory);
```

**Product Structure:**

```solidity
struct Product {
    uint256 id;                    // Auto-incremented ID
    string product_id;             // Business identifier
    address seller;                // Product owner
    string metadata_cid;           // Arweave CID (product JSON)
    string[] component_ids;        // Component references
    string[] forms;                // Product forms
    uint256 created_at;            // Creation timestamp
    bool active;                   // Active flag
}
```

### **AmanitaInternational (Localization Contract)**

**Purpose:** Store CID references for product titles

**Usage:**

```solidity
// Store title CID
await amanitaIntl.setSimpleFieldCID(
  "ProductName.amanita_tincture_50ml",
  "QmTitleCID123..."
);

// Retrieve title CID
const titleCID = await amanitaIntl.getSimpleFieldCID(
  "ProductName.amanita_tincture_50ml"
);
```

**Storage Pattern:**

```yaml
Key Format: "ProductName.{product_id}"
Value: Arweave CID containing multi-language titles

Example:
  Key: "ProductName.amanita_tincture_50ml"
  Value: "QmTitleCID123..."
  
  CID Content (JSON):
    {
      "ru": "Аманита — ЛЮКС",
      "en": "Amanita — LUX",
      "es": "Amanita — LUJO",
      ...
    }
```

---

## 🔗 Component Integration

### **Component Validation During Transform**

**Process:**

```yaml
Step 1: Check Component Exists
  Query: OrganicComponentRegistry.componentExists(component_id)
  
  If false:
    → Error: "Component not found: {component_id}"
    → Advice: "Upload component first: Action 555"
    → Halt transformation

Step 2: Load Component Metadata
  Query: OrganicComponentRegistry.getComponentByBusinessId(component_id)
  
  Extract:
    - Available forms: component.forms
    - Features: component.features
    - Scientific name: component.scientific_title

Step 3: Validate Form Compatibility
  Check: product.form IN component.forms
  
  If false:
    → Error: "Form '{form}' not available for component '{component_id}'"
    → Available: component.forms
    → Halt transformation

Step 4: Store Component Reference
  In product JSON:
    {
      "components": [{
        "component_business_id": component_id,
        "form": validated_form,
        "proportion": "100%"
      }]
    }
```

### **Component Usage Tracking**

**During Product Registration:**

```javascript
// Action 43 registers product
await productRegistry.createProduct(
  product_id,
  seller,
  metadata_cid,
  [component_id],  // Component references
  [form]
);

// ProductRegistry automatically calls:
await organicRegistry.incrementUsageCount(component_id);

// Component usage count incremented
component.usage_count++;  // Now tracked on-chain
```

**Benefits:**
- Track component popularity
- Identify most-used components
- Analytics for component creators
- Reward frequently-used components

### **Component Description Inheritance**

**Product Display:**

```yaml
Product Page:
  Title: From ProductName CID (Arweave)
  Description: From Component CID (Arweave)
  
  User sees:
    - Product Title: "Amanita — LUX"
    - Component Title: "Fly Agaric (Amanita muscaria)"
    - Component Description: Detailed description from ComponentDescription CID
    - Dosage Instructions: From component's DosageInstruction CID
    
  Benefit: Sellers don't duplicate descriptions
```

---

## 🧪 Validation System

### **validate_catalog_pipeline.js**

**Purpose:** Validate completeness and correctness of catalog pipeline (Action 444) across all layers

**Usage:**

```bash
# Full validation (all 6 phases)
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost

# With full Arweave check (all CIDs, not sampled)
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost \
  --full-arweave-check

# With summary output only
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost \
  --summary

# Custom seller address (override .env)
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost \
  --seller-address 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

### **6-Phase Validation**

#### **Phase 1: CSV & File System Validation (10% weight)**

```yaml
Checks:
  ✅ CSV file exists and readable
  ✅ CSV has required columns
  ✅ CSV row count > 0
  ✅ No duplicate product_business_id
  ✅ Products directory exists
  ✅ Product JSON files exist (count matches CSV)
  ✅ Title translation files exist
  ✅ Mapping files exist (combined, title, product, image)
  ✅ Images directory exists (if check-images flag)

Scoring:
  - 10/10: All files present, no duplicates
  - 7-9/10: Minor issues (1-2 missing files)
  - 4-6/10: Major issues (many missing files)
  - 0-3/10: Critical issues (CSV invalid/missing)
```

#### **Phase 2: Arweave Layer Validation (25% weight)**

```yaml
Checks:
  ✅ Title CIDs accessible (sampled: 3 products)
  ✅ Image CIDs accessible (sampled: 3 products)
  ✅ Product metadata CIDs accessible (sampled: 3 products)
  ✅ CID content matches expected structure
  ✅ Title JSON has all 7 languages
  ✅ File sizes reasonable (< 1MB per file)

Arweave Gateway Check:
  - Primary: https://arweave.net/{CID}
  - Fallback: https://gateway.irys.xyz/{CID}
  - Timeout: 10 seconds per request
  - Retry: 2 attempts

Sampling Strategy:
  - Default: Sample 3 random products
  - --full-arweave-check: Check ALL products

Scoring:
  - 10/10: All sampled CIDs resolve, content valid
  - 7-9/10: 1 CID slow/timeout (recoverable)
  - 4-6/10: 2+ CIDs inaccessible
  - 0-3/10: All CIDs inaccessible (critical)
```

#### **Phase 3: Contract Layer Validation (30% weight - CRITICAL)**

```yaml
Checks:
  ✅ All products exist in ProductRegistry
  ✅ Product count: Contract == CSV
  ✅ All products active (activateProducts called)
  ✅ Product sellers match expected seller
  ✅ Product metadata CIDs match uploaded CIDs
  ✅ Product IDs match business IDs
  ✅ Title CIDs stored in AmanitaInternational

Contract Queries:
  - getProductsBySeller(seller) → Get all products
  - getAllActiveProductIds() → Verify activation
  - For each product:
      - getProductById(id) → Verify metadata
      - Verify seller == expected_seller
      - Verify metadata_cid == uploaded_cid

Scoring:
  - 10/10: All products registered, active, CIDs match
  - 7-9/10: Products registered, minor CID gaps
  - 4-6/10: Products registered, major issues
  - 0-3/10: Products NOT registered (Action 43 failed)
```

#### **Phase 4: Product Count Consistency (15% weight)**

```yaml
Checks:
  ✅ CSV row count == Product JSON count
  ✅ Product JSON count == Contract product count
  ✅ Contract product count == Active product count
  ✅ Title mapping count == Product count
  ✅ Image mapping count == Product count

Count Sources:
  - CSV: Parse CSV, count rows (exclude header)
  - File System: Count product JSON files
  - Contract: getProductsBySeller().length
  - Active: getAllActiveProductIds().length
  - Mappings: Count keys in mapping files

Expected: All counts EQUAL

Scoring:
  - 10/10: Perfect match (all counts equal)
  - 7-9/10: Minor mismatch (1-2 products difference)
  - 4-6/10: Major mismatch (3+ products difference)
  - 0-3/10: Critical mismatch (2x difference, duplicates)

Fix 2 Impact:
  Before: CSV=17, Contract=34 → Score=5.0 ❌
  After: CSV=17, Contract=17 → Score=10.0 ✅
```

#### **Phase 5: Component Integration Validation (15% weight)**

```yaml
Checks:
  ✅ All referenced components exist in OrganicComponentRegistry
  ✅ All component IDs valid (no null/undefined)
  ✅ All forms valid for components
  ✅ Component usage counts updated
  ✅ Component active flags = true

Component Validation (Per Product):
  For each component_id in product.components:
    1. Query: OrganicComponentRegistry.componentExists(component_id)
       → Must be true
    
    2. Query: OrganicComponentRegistry.getComponentByBusinessId(component_id)
       → Verify component.active == true
       → Verify product.form IN component.forms
    
    3. Check: component.usage_count > 0
       → Incremented during product registration

Common Issues:
  - Component not uploaded (Action 555 not run)
  - Component not active
  - Form mismatch (product form not in component forms)

Scoring:
  - 10/10: All components exist, active, forms valid
  - 7-9/10: Minor issues (1 component inactive)
  - 4-6/10: Major issues (multiple missing components)
  - 0-3/10: Critical issues (no components found)
```

#### **Phase 6: Seller Readiness Validation (5% weight)**

```yaml
Checks:
  ✅ Seller activated (usedInviteByUser > 0)
  ✅ Seller has SELLER_ROLE
  ✅ Seller has ACTIVATOR_ROLE (optional, recommended)
  ✅ Seller has catalog (products > 0)
  ✅ Seller has active products (active > 0)

Seller Diagnostics:
  Query: SpiralEngine contract
    - usedInviteByUser(seller) → Activation status
    - hasRole(SELLER_ROLE, seller) → Role check
    - hasRole(ACTIVATOR_ROLE, seller) → Role check
  
  Query: ProductRegistry contract
    - getProductsBySeller(seller).length → Catalog size
    - Filter active products → Active count

Readiness Score (0-5):
  - Activated: +1
  - Has SELLER_ROLE: +1
  - Has ACTIVATOR_ROLE: +1
  - Has catalog: +1
  - Has active products: +1

Scoring:
  - 10/10: Readiness 5/5 (fully ready)
  - 8-9/10: Readiness 4/5 (missing ACTIVATOR_ROLE)
  - 6-7/10: Readiness 3/5 (no active products)
  - 4-5/10: Readiness 2/5 (no catalog)
  - 0-3/10: Readiness 0-1/5 (not activated)
```

### **Quality Score Calculation**

```javascript
Quality Score = (
  (Phase1_Score * 0.10) +  // File System: 10%
  (Phase2_Score * 0.25) +  // Arweave: 25%
  (Phase3_Score * 0.30) +  // Contract: 30% (CRITICAL)
  (Phase4_Score * 0.15) +  // Count Consistency: 15%
  (Phase5_Score * 0.15) +  // Component Integration: 15%
  (Phase6_Score * 0.05)    // Seller Readiness: 5%
);

Passing Threshold: >= 8.0/10

Result:
  - 9.5-10.0: ✅ EXCELLENT - Production ready
  - 8.0-9.4:  ✅ PASS - Minor issues, acceptable
  - 6.0-7.9:  ⚠️ WARNING - Needs attention
  - 0.0-5.9:  ❌ FAIL - Critical issues, re-run pipeline
```

### **Validation Report Example**

```
================================================================================
🧪 CATALOG PIPELINE VALIDATION REPORT
================================================================================

📦 Seller: iveta_zeya888
🌐 Network: localhost
👤 Seller Address: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
⏰ Validation Time: 2025-10-27T11:30:00Z

────────────────────────────────────────────────────────────────────────────────
📁 PHASE 1: CSV & FILE SYSTEM VALIDATION (Weight: 10%)
────────────────────────────────────────────────────────────────────────────────

✅ CSV file exists: data/sellers/iveta/catalog/Iveta_catalog.csv
✅ CSV row count: 17 products
✅ CSV columns valid: All required columns present
✅ No duplicate product_business_id
✅ Products directory exists: data/sellers/iveta/output/products/
✅ Product JSON files: 17/17 found
✅ Title translation files: 17/17 found
✅ Mapping files:
   ✅ product_combined_mapping.json (17 entries)
   ✅ title_cid_mapping.json (17 entries)
   ✅ product_cid_mapping.json (17 entries)
   ✅ image_cid_mapping.json (17 entries)

Phase 1 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
☁️ PHASE 2: ARWEAVE LAYER VALIDATION (Weight: 25%)
────────────────────────────────────────────────────────────────────────────────

Sampling: 3 products (use --full-arweave-check for all)

✅ Title CIDs accessible (3/3):
   ✅ amanita_tincture_50ml: QmTitle123... (245ms)
   ✅ blue_lotus_tea_organic: QmTitle234... (198ms)
   ✅ lions_mane_capsules_500mg: QmTitle345... (312ms)

✅ Image CIDs accessible (3/3):
   ✅ amanita_lux.jpg: QmImage456... (423ms, 145 KB)
   ✅ blue_lotus_tea.jpg: QmImage567... (387ms, 98 KB)
   ✅ lions_mane.jpg: QmImage678... (295ms, 112 KB)

✅ Product metadata CIDs accessible (3/3):
   ✅ amanita_tincture_50ml: QmProduct789... (356ms, 3.2 KB)
   ✅ blue_lotus_tea_organic: QmProduct890... (401ms, 2.9 KB)
   ✅ lions_mane_capsules_500mg: QmProduct901... (278ms, 3.1 KB)

Average Response Time: 322ms
Total Storage (sampled): 362.2 KB

Phase 2 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
⛓️ PHASE 3: CONTRACT LAYER VALIDATION (Weight: 30%)
────────────────────────────────────────────────────────────────────────────────

✅ Products in ProductRegistry: 17/17 found
✅ All products active: 17/17
✅ Product sellers match: 17/17
✅ Metadata CIDs match: 17/17

✅ Title CIDs in AmanitaInternational: 17/17
   Sample verification:
   ✅ ProductName.amanita_tincture_50ml → QmTitle123...
   ✅ ProductName.blue_lotus_tea_organic → QmTitle234...
   ✅ ProductName.lions_mane_capsules_500mg → QmTitle345...

Phase 3 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
📊 PHASE 4: PRODUCT COUNT CONSISTENCY (Weight: 15%)
────────────────────────────────────────────────────────────────────────────────

✅ Count consistency check:
   CSV rows:           17
   Product JSONs:      17
   Contract products:  17
   Active products:    17
   Title mappings:     17
   Image mappings:     17
   Product mappings:   17

✅ ALL COUNTS MATCH ✅

Phase 4 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
🔗 PHASE 5: COMPONENT INTEGRATION VALIDATION (Weight: 15%)
────────────────────────────────────────────────────────────────────────────────

✅ Components referenced: 3 unique
   - amanita_muscaria (usage_count: 5)
   - blue_lotus (usage_count: 8)
   - lions_mane (usage_count: 4)

✅ All components exist in OrganicComponentRegistry: 3/3
✅ All components active: 3/3
✅ All component forms valid: 17/17 products
✅ Component usage counts updated: 3/3

Phase 5 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
👤 PHASE 6: SELLER READINESS VALIDATION (Weight: 5%)
────────────────────────────────────────────────────────────────────────────────

✅ Seller activated: Yes (invite token: 1)
✅ Seller has SELLER_ROLE: Yes
✅ Seller has ACTIVATOR_ROLE: Yes
✅ Seller has catalog: Yes (17 products)
✅ Seller has active products: Yes (17 active)

🎉 Readiness Score: 5/5 (100%)
Verdict: ✅ Seller fully ready for production

Phase 6 Score: 10.0/10 ✅ EXCELLENT

────────────────────────────────────────────────────────────────────────────────
🎯 FINAL QUALITY SCORE
────────────────────────────────────────────────────────────────────────────────

Phase 1 (File System):       10.0/10 × 10% = 1.00
Phase 2 (Arweave):            10.0/10 × 25% = 2.50
Phase 3 (Contract):           10.0/10 × 30% = 3.00
Phase 4 (Count):              10.0/10 × 15% = 1.50
Phase 5 (Components):         10.0/10 × 15% = 1.50
Phase 6 (Seller):             10.0/10 × 5%  = 0.50
                                           ──────
                             Quality Score: 10.0/10 ✅ EXCELLENT

Status: ✅ VALIDATION PASSED
Pipeline Ready: ✅ Production deployment approved
Seller Ready: ✅ Fully operational

================================================================================
```

---

## 📚 Usage Examples

### **Example 1: Complete Pipeline (CSV → Blockchain)**

```bash
# Prerequisites:
# 1. Contracts deployed (Action 1)
# 2. Seller activated (Action 888)
# 3. Components uploaded (Action 555)
# 4. CSV catalog prepared

# Run complete pipeline
DEPLOY_ACTION=444 \
CSV_FILE=data/sellers/iveta/catalog/Iveta_catalog.csv \
OUTPUT_DIR=data/sellers/iveta/output \
SELLER_BUSINESS_ID=iveta_zeya888 \
npx hardhat run scripts/deploy_full.js --network localhost

# Validate results
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost
```

### **Example 2: Step-by-Step Pipeline**

```bash
# Step 1: Transform CSV to JSON
DEPLOY_ACTION=41 \
CSV_FILE=data/sellers/iveta/catalog/Iveta_catalog.csv \
OUTPUT_DIR=data/sellers/iveta/output \
SELLER_BUSINESS_ID=iveta_zeya888 \
npx hardhat run scripts/deploy_full.js --network localhost

# Step 2: Upload to Arweave
DEPLOY_ACTION=42 \
SELLER_BUSINESS_ID=iveta_zeya888 \
npx hardhat run scripts/deploy_full.js --network localhost

# Step 3: Register in contracts
DEPLOY_ACTION=43 \
npx hardhat run scripts/deploy_full.js --network localhost

# Validate each step
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost \
  --summary
```

### **Example 3: Translation Workflow**

```bash
# 1. Transform CSV (creates translation stubs)
node scripts/transform_products_csv.js \
  --csv data/sellers/iveta/catalog/Iveta_catalog.csv \
  --output data/sellers/iveta/output/products/ \
  --seller-id iveta_zeya888 \
  --create-stubs

# 2. Translator edits files
# Edit: data/sellers/iveta/output/products/{product_id}/translations/title.json

# 3. Re-upload with new translations
DEPLOY_ACTION=42 \
SELLER_BUSINESS_ID=iveta_zeya888 \
npx hardhat run scripts/deploy_full.js --network localhost

# 4. Verify translations
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost \
  --full-arweave-check
```

### **Example 4: Programmatic Validation**

```javascript
const { validateCatalogPipeline } = require('./scripts/validators/validate_catalog_pipeline.js');

async function checkBeforeDeployment() {
  const validation = await validateCatalogPipeline({
    sellerId: 'iveta',
    network: 'localhost',
    sellerAddress: '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
    fullArweaveCheck: true
  });
  
  if (validation.qualityScore < 8.0) {
    console.error(`❌ Validation failed: ${validation.qualityScore}/10`);
    console.error('Issues:');
    for (const phase of validation.phases) {
      if (phase.score < 8.0) {
        console.error(`  - ${phase.name}: ${phase.score}/10`);
        console.error(`    Errors: ${phase.errors.join(', ')}`);
      }
    }
    process.exit(1);
  }
  
  console.log(`✅ Validation passed: ${validation.qualityScore}/10`);
  console.log('Ready for production deployment');
}

checkBeforeDeployment();
```

---

## 🔧 Troubleshooting

### **Issue 1: CSV Parsing Error**

**Symptom:**
```
❌ Error: Missing required columns: product_business_id
Available columns: ProductID, Name, Image, Form, Price
```

**Root Cause:** CSV column names don't match expected format

**Solution:**
```bash
# Check CSV headers (first line)
head -1 data/sellers/iveta/catalog/Iveta_catalog.csv

# Expected format:
# component_business_id,product_business_id,product_name,image_file,form,prices

# Fix: Rename columns in CSV to match expected names
```

### **Issue 2: Component Not Found**

**Symptom:**
```
❌ Error transforming product: amanita_tincture_50ml
Component not found: amanita_muscaria
Upload component first: Action 555
```

**Root Cause:** Component not uploaded to OrganicComponentRegistry

**Solution:**
```bash
# Upload missing component
DEPLOY_ACTION=555 \
npx hardhat run scripts/deploy_full.js --network localhost

# Verify component exists
node scripts/validate_component_upload.js \
  --component amanita_muscaria \
  --network localhost

# Re-run Action 41
DEPLOY_ACTION=41 ... npx hardhat run scripts/deploy_full.js --network localhost
```

### **Issue 3: Form Mismatch**

**Symptom:**
```
⚠️ Phase 5 Score: 6.5/10
Error: Form 'tea_bags' not available for component 'amanita_muscaria'
Available forms: ["dried", "tincture", "powder_extract"]
```

**Root Cause:** CSV specifies form not supported by component

**Solution:**
```bash
# Option 1: Fix CSV (change form to valid value)
# Edit CSV: Change "tea_bags" → "tincture"

# Option 2: Update component forms (if form is valid)
# Edit component metadata, re-upload with Action 555
```

### **Issue 4: Arweave Balance Too Low**

**Symptom:**
```
❌ Error: Insufficient Arweave balance
Current: 0.003 AR
Required: >= 0.01 AR (estimated 0.08 AR for 17 products)
```

**Root Cause:** Not enough AR tokens for catalog upload

**Solution:**
```bash
# Check current balance
cat .arweave-key.json | npx arweave balance

# Get more AR from faucet (testnet)
# Visit: https://faucet.arweave.net

# Or use mainnet wallet with sufficient balance
```

### **Issue 5: Duplicate Products in Contract**

**Symptom:**
```
⚠️ Phase 4 Score: 5.0/10
Count mismatch:
  CSV: 17 products
  Contract: 34 products (duplicates!)
```

**Root Cause:** Multiple Action 444 runs without catalog clearing (Fix 2 not applied)

**Solution:**
```bash
# Manual clear (if Fix 2 not available)
# Call productRegistry.clearSellerCatalog(seller)

# Or with updated code (Fix 2):
# Action 43 automatically clears before registration

# Re-run Action 43 only
DEPLOY_ACTION=43 \
npx hardhat run scripts/deploy_full.js --network localhost

# Verify fix
node scripts/validate_catalog_pipeline.js \
  --seller iveta \
  --network localhost
```

### **Issue 6: Products Not Activated**

**Symptom:**
```
⚠️ Phase 3 Score: 7.5/10
Products registered: 17/17
Products active: 0/17 ❌
```

**Root Cause:** Step 2 of Action 43 (activateProducts) not called

**Solution:**
```bash
# Re-run Action 43 (includes activation)
DEPLOY_ACTION=43 \
npx hardhat run scripts/deploy_full.js --network localhost

# Or manually activate via contract call:
# await productRegistry.activateProducts([...productIds])
```

---

## 📖 API Reference

### **CatalogActions.action444()**

Complete pipeline from CSV to blockchain

**Signature:**
```javascript
async action444()
```

**Environment Variables:**
```yaml
Required:
  - CSV_FILE: Path to CSV catalog
  - OUTPUT_DIR: Output directory for JSON files
  - SELLER_BUSINESS_ID: Seller identifier
  - SELLER_ADDRESS: Seller Ethereum address
  - SELLER_PRIVATE_KEY: Seller private key

Optional:
  - SOURCE_LANG: Source language (default: "en")
  - DRY_RUN: Simulate without actual changes (default: false)
```

**Returns:**
```javascript
{
  success: true,
  phase1: {
    transformed: 17,
    skipped: 0,
    errors: []
  },
  phase2: {
    titlesUploaded: 17,
    imagesUploaded: 17,
    productsUploaded: 17,
    totalCIDs: 51,
    arweaveFees: "0.08 AR"
  },
  phase3: {
    registered: 17,
    activated: 17,
    failed: 0
  }
}
```

### **validateCatalogPipeline(options)**

Validate catalog across 6 phases

**Signature:**
```javascript
async function validateCatalogPipeline(options = {})
```

**Parameters:**
```javascript
{
  sellerId: "iveta",              // Seller business ID
  network: "localhost",           // Network name
  sellerAddress: "0x...",         // Seller address (default: from .env)
  csvPath: "path/to/csv",         // CSV path (default: auto-detect)
  productsDir: "path/to/products",// Products directory (default: auto-detect)
  fullArweaveCheck: false,        // Check all CIDs (default: sample 3)
  checkImages: false,             // Validate image files
  summary: false                  // Print summary only
}
```

**Returns:**
```javascript
{
  sellerId: "iveta",
  network: "localhost",
  sellerAddress: "0x...",
  
  phase1: { score: 10.0, errors: [], warnings: [] },
  phase2: { score: 10.0, cidsChecked: 9, totalCIDs: 51 },
  phase3: { score: 10.0, productsFound: 17, allActive: true },
  phase4: { score: 10.0, csvCount: 17, contractCount: 17 },
  phase5: { score: 10.0, componentsValid: 3, formsValid: 17 },
  phase6: { score: 10.0, readinessScore: 5 },
  
  qualityScore: 10.0,
  passed: true,
  timestamp: "2025-10-27T11:30:00Z"
}
```

### **ProductRegistry.createProduct()**

Register product on-chain

**Signature:**
```solidity
function createProduct(
    string memory product_id,
    address seller,
    string memory metadata_cid,
    string[] memory component_ids,
    string[] memory forms
) external onlyRole(SELLER_ROLE) returns (uint256)
```

**Parameters:**
- `product_id`: Product business ID (e.g., "amanita_tincture_50ml")
- `seller`: Seller address
- `metadata_cid`: Arweave CID of product JSON
- `component_ids`: Array of component references
- `forms`: Array of product forms

**Returns:**
- `uint256`: Product ID (auto-incremented)

**Events:**
```solidity
event ProductCreated(
    uint256 indexed productId,
    string indexed product_id,
    address indexed seller,
    string metadata_cid
);
```

### **ProductRegistry.activateProducts()**

Activate multiple products (batch operation)

**Signature:**
```solidity
function activateProducts(uint256[] memory productIds) 
    external onlyRole(SELLER_ROLE)
```

**Parameters:**
- `productIds`: Array of product IDs to activate

**Events:**
```solidity
event ProductsActivated(
    address indexed seller,
    uint256[] productIds
);
```

### **ProductRegistry.clearSellerCatalog()**

Clear seller's entire catalog (Fix 2)

**Signature:**
```solidity
function clearSellerCatalog(address seller) 
    external onlyRole(SELLER_ROLE)
```

**Parameters:**
- `seller`: Seller address

**Events:**
```solidity
event CatalogCleared(
    address indexed seller,
    uint256 productsRemoved
);
```

---

## 📊 Catalog Metrics & Analytics

### **Storage Costs**

```yaml
Average Product Storage:
  - Title JSON (7 languages): ~0.5 KB
  - Product metadata JSON: ~3 KB
  - Product image: ~100 KB (varies)
  - Total per product: ~103.5 KB

Arweave Costs (approximate):
  - Per KB: ~0.00001 AR
  - Per Product: ~0.001 AR
  - 100 Products: ~0.1 AR (~$2 at $20/AR)

Bulk Upload (1000 products):
  - Storage: ~100 MB
  - Cost: ~1 AR (~$20 at $20/AR)
```

### **Performance Metrics**

```yaml
Pipeline Performance (17 products):
  - Action 41 (Transform): ~5 seconds
  - Action 42 (Arweave Upload): ~3-5 minutes
  - Action 43 (Contract Registration): ~30 seconds
  - Total: ~6 minutes

Scaling (100 products):
  - Action 41: ~20 seconds
  - Action 42: ~15-20 minutes
  - Action 43: ~2 minutes
  - Total: ~23 minutes
```

---

## 🚀 Next Steps

### **For Sellers**

1. **Prepare CSV Catalog**
   - Use template format
   - Verify component references
   - Check image filenames

2. **Upload Components First**
   - Action 555 for each component
   - Validate with validate_component_upload.js
   - Verify components active

3. **Run Catalog Pipeline**
   - Action 444 for complete pipeline
   - Validate with validate_catalog_pipeline.js
   - Verify 10.0/10 score before production

### **For Translators**

1. **Access Translation Stubs**
   - Find in `products/{product_id}/translations/`
   - Read README.md for instructions
   - Edit title.json files

2. **Complete Translations**
   - Replace [NEEDS TRANSLATION] markers
   - Verify JSON formatting
   - Save files

3. **Re-upload**
   - Run Action 42 to upload new translations
   - Verify with --full-arweave-check
   - Confirm all 7 languages present

### **For System Administrators**

1. **Monitoring**
   - Track pipeline success rates
   - Monitor Arweave costs
   - Alert on validation failures below 8.0/10

2. **Backup & Recovery**
   - Regular mapping file backups
   - CID archive for disaster recovery
   - Contract event log backup

3. **Performance Optimization**
   - Cache popular products
   - CDN for IPFS gateway
   - Batch validation scripts
   - Database indexing for bot queries

---

## 📚 See Also

### **Related Documentation**
- **[actions/Catalog.md](./actions/Catalog.md)** - CatalogActions detailed architecture
- **[Components-Architecture.md](./Components-Architecture.md)** - Component system (required dependency)
- **[actions/Invite.md](./actions/Invite.md)** - Seller activation (action888)
- **[contracts/docs/ProductRegistry.md](../contracts/docs/ProductRegistry.md)** - Smart contract specification

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
  - Action 555: Upload components (REQUIRED)

Catalog Pipeline:
  - Action 41: CSV → JSON transformation
  - Action 42: Arweave upload
  - Action 43: Contract registration
  - Action 444: Complete pipeline (41 → 42 → 43)
  - validate_catalog_pipeline.js: Validation

Downstream Integrations:
  - Telegram Bot: Display products to users
  - ProductRegistry: Query products by seller
  - AmanitaInternational: Fetch localized titles
```

---

**Version:** 2.0  
**Status:** ✅ Production Ready  
**Last Updated:** 2025-10-27  
**Maintainer:** Amanita Development Team  
**License:** MIT

