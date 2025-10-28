#!/usr/bin/env node

/**
 * 🧪 Catalog Pipeline Validation Script
 * 
 * Validates completeness and correctness of Action 444 (catalog pipeline)
 * across 5 layers: CSV → JSON → Arweave → Contract → Components
 * 
 * Usage:
 *   node scripts/validate_catalog_pipeline.js
 *   node scripts/validate_catalog_pipeline.js --seller iveta --network localhost
 *   node scripts/validate_catalog_pipeline.js --check-images --json
 * 
 * Programmatic Use:
 *   const { validateCatalogPipeline } = require('./scripts/validate_catalog_pipeline.js');
 *   const report = await validateCatalogPipeline({ seller: 'iveta', network: 'localhost' });
 * 
 * @version 1.0.0
 * @date 2025-10-25
 */

const fs = require('fs');
const path = require('path');
const { program } = require('commander');

// ====================================================================
// 🔧 CONFIGURATION
// ====================================================================

const SUPPORTED_LANGUAGES = ['ru', 'en', 'de', 'es', 'fr', 'nl', 'et'];

// Expected file structures
const REQUIRED_CSV_COLUMNS = ['product_business_id', 'component_business_id', 'form', 'price', 'title'];
const REQUIRED_PRODUCT_FIELDS = ['product_id', 'title', 'components', 'prices'];
const REQUIRED_TITLE_FIELDS = SUPPORTED_LANGUAGES; // At least one language

// Validation thresholds
const PASS_THRESHOLD = 7.0; // Quality score >= 7.0 to pass
const ARWEAVE_SAMPLE_SIZE = 5; // Sample first 5 CIDs for quick check

// ====================================================================
// 🛠️ HELPER UTILITIES
// ====================================================================

/**
 * Build context object from CLI options
 * @param {Object} options - CLI options
 * @returns {Object} - Context object with resolved paths
 */
function buildContext(options) {
  const sellerId = options.seller || process.env.SELLER_BUSINESS_ID || 'iveta';
  const network = options.network || 'localhost';
  
  // Auto-resolve paths based on seller ID
  const sellerBasePath = path.join(__dirname, '..', 'data', 'sellers', sellerId);
  const csvFilename = `${sellerId.charAt(0).toUpperCase() + sellerId.slice(1)}_catalog.csv`;
  const csvPath = options.csv || path.join(sellerBasePath, 'catalog', csvFilename);
  const outputDir = path.join(sellerBasePath, 'output');
  const productsDir = path.join(outputDir, 'products');
  const mappingPath = path.join(outputDir, 'product_combined_mapping.json');
  
  // Get seller address from .env
  const sellerAddress = process.env.SELLER_ADDRESS || 
                        process.env.SELLER_WALLET_ADDRESS || 
                        '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'; // Default localhost seller
  
  return {
    sellerId,
    sellerAddress,
    network,
    csvPath,
    productsDir,
    outputDir,
    mappingPath,
    checkImages: options.checkImages || false,
    fullArweaveCheck: options.fullArweaveCheck || false,
    json: options.json || false,
    
    // Results storage (populated during execution)
    phase1Results: null,
    phase2Results: null,
    phase3Results: null,
    phase4Results: null,
    phase5Results: null
  };
}

/**
 * Check if warning is expected and non-critical
 * @param {string} message - Warning message
 * @returns {boolean} - True if expected
 */
function isExpectedWarning(message) {
  const expectedPatterns = [
    'registry.getComponentId is not a function',
    'Image not found:',
    'TX: undefined',
    'Component status not ACTIVE: 0'
  ];
  
  return expectedPatterns.some(pattern => message.includes(pattern));
}

// ====================================================================
// 📊 PHASE 1: CSV + FILE SYSTEM VALIDATION
// ====================================================================

/**
 * Phase 1: Validate CSV source and generated file structure
 * @param {Object} context - Validation context
 * @returns {Promise<Object>} - Validation results
 */
async function validatePhase1_CSV_FileSystem(context) {
  const { sellerId, csvPath, productsDir, checkImages } = context;
  
  const checks = {
    csv_exists: false,
    csv_row_count: 0,
    csv_columns_valid: false,
    csv_duplicate_ids: [],
    product_dirs_count: 0,
    product_dirs_expected: 0,
    product_json_count: 0,
    product_json_valid: 0,
    title_json_count: 0,
    title_json_valid: 0,
    transformation_report_exists: false,
    report_stats_match: false,
    report_data: null,
    image_checks: { total: 0, found: 0, missing: [] },
    errors: [],
    warnings: []
  };
  
  // 1. Validate CSV file
  if (csvPath && fs.existsSync(csvPath)) {
    checks.csv_exists = true;
    
    try {
      const csvContent = fs.readFileSync(csvPath, 'utf8');
      const rows = csvContent.split('\n').filter(r => r.trim());
      checks.csv_row_count = rows.length - 1; // Exclude header
      
      // Validate headers (flexible matching for common variants)
      const headers = rows[0].toLowerCase().split(',').map(h => h.trim());
      const columnVariants = {
        'product_business_id': ['product_business_id', 'product_id'],
        'component_business_id': ['component_business_id', 'biounit_id', 'component_id'],
        'form': ['form', 'product_form'],
        'price': ['price', 'prices'],
        'title': ['title', 'product_name', 'name']
      };
      
      const missingColumns = [];
      for (const [required, variants] of Object.entries(columnVariants)) {
        const found = variants.some(variant => headers.some(h => h.includes(variant)));
        if (!found) {
          missingColumns.push(required);
        }
      }
      
      checks.csv_columns_valid = missingColumns.length === 0;
      
      if (!checks.csv_columns_valid) {
        checks.errors.push(`CSV missing required columns: ${missingColumns.join(', ')}`);
      }
      
      // Check for duplicate product_business_id
      // CSV structure: component_business_id,product_business_id,...
      // Product ID is in column index 1
      const productIdColIndex = headers.findIndex(h => h.includes('product_business_id'));
      
      if (productIdColIndex >= 0) {
        const productIds = new Set();
        for (let i = 1; i < rows.length; i++) {
          const columns = rows[i].split(',');
          const productId = columns[productIdColIndex]?.trim();
          if (productId) {
            if (productIds.has(productId)) {
              checks.csv_duplicate_ids.push(productId);
            }
            productIds.add(productId);
          }
        }
      }
      
      if (checks.csv_duplicate_ids.length > 0) {
        checks.errors.push(`Duplicate product IDs in CSV: ${checks.csv_duplicate_ids.join(', ')}`);
      }
      
    } catch (error) {
      checks.errors.push(`CSV read error: ${error.message}`);
    }
  } else {
    checks.warnings.push(`CSV file not found: ${csvPath} (optional for validation)`);
  }
  
  // 2. Validate product directories
  if (fs.existsSync(productsDir)) {
    const entries = fs.readdirSync(productsDir, { withFileTypes: true });
    const productDirs = entries.filter(e => e.isDirectory() && !e.name.startsWith('_'));
    checks.product_dirs_count = productDirs.length;
    checks.product_dirs_expected = checks.csv_row_count || productDirs.length;
    
    if (checks.product_dirs_count !== checks.product_dirs_expected) {
      checks.errors.push(
        `Product directory count mismatch: found ${checks.product_dirs_count}, expected ${checks.product_dirs_expected} (from CSV)`
      );
    }
    
    // 3. Validate each product directory
    for (const dir of productDirs) {
      const productId = dir.name;
      const productDir = path.join(productsDir, productId);
      
      // Check product JSON
      const productJsonPath = path.join(productDir, `${productId}.json`);
      if (fs.existsSync(productJsonPath)) {
        checks.product_json_count++;
        
        try {
          const data = JSON.parse(fs.readFileSync(productJsonPath, 'utf8'));
          
          // Validate required fields
          const hasRequired = REQUIRED_PRODUCT_FIELDS.every(field => 
            data[field] !== undefined
          );
          
          if (hasRequired) {
            checks.product_json_valid++;
            
            // Additional validation: components array structure
            if (!Array.isArray(data.components) || data.components.length === 0) {
              checks.warnings.push(`Product ${productId}: components array empty or invalid`);
            }
            
            // Additional validation: prices array structure
            if (!Array.isArray(data.prices) || data.prices.length === 0) {
              checks.warnings.push(`Product ${productId}: prices array empty or invalid`);
            }
            
          } else {
            const missing = REQUIRED_PRODUCT_FIELDS.filter(f => data[f] === undefined);
            checks.errors.push(`Invalid product JSON: ${productId} (missing: ${missing.join(', ')})`);
          }
        } catch (e) {
          checks.errors.push(`Product JSON parse error: ${productId} - ${e.message}`);
        }
      } else {
        checks.errors.push(`Product JSON not found: ${productId}.json`);
      }
      
      // Check title JSON
      const titleJsonPath = path.join(productDir, `${productId}.titles.json`);
      if (fs.existsSync(titleJsonPath)) {
        checks.title_json_count++;
        
        try {
          const titles = JSON.parse(fs.readFileSync(titleJsonPath, 'utf8'));
          
          // Validate has at least one language
          const hasLanguages = Object.keys(titles).length > 0;
          const hasValidStructure = Object.keys(titles).every(lang => 
            typeof titles[lang] === 'string'
          );
          
          if (hasLanguages && hasValidStructure) {
            checks.title_json_valid++;
          } else {
            checks.errors.push(`Invalid title JSON: ${productId} (no languages or invalid structure)`);
          }
        } catch (e) {
          checks.errors.push(`Title JSON parse error: ${productId} - ${e.message}`);
        }
      } else {
        checks.errors.push(`Title JSON not found: ${productId}.titles.json`);
      }
    }
  } else {
    checks.errors.push(`Products directory not found: ${productsDir}`);
  }
  
  // 4. Validate transformation report
  const reportPath = path.join(productsDir, '_transformation_report.json');
  if (fs.existsSync(reportPath)) {
    checks.transformation_report_exists = true;
    
    try {
      const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
      checks.report_data = report;
      
      // Report structure: { statistics: { total_rows, valid_products, ... } }
      const stats = report.statistics || {};
      const totalRows = stats.total_rows || report.totalRows;
      const validProducts = stats.valid_products || report.validProducts;
      
      // Verify statistics match reality
      const statsMatch = 
        (!checks.csv_row_count || totalRows === checks.csv_row_count) &&
        validProducts === checks.product_dirs_count;
      
      checks.report_stats_match = statsMatch;
      
      if (!statsMatch) {
        checks.warnings.push(
          `Transformation report statistics mismatch: ` +
          `report.total_rows=${totalRows} vs CSV=${checks.csv_row_count}, ` +
          `report.valid_products=${validProducts} vs dirs=${checks.product_dirs_count}`
        );
      }
    } catch (e) {
      checks.warnings.push(`Transformation report parse error: ${e.message}`);
    }
  } else {
    checks.warnings.push(`Transformation report not found: ${reportPath}`);
  }
  
  // 5. Optional: Check images
  if (checkImages && csvPath && fs.existsSync(csvPath)) {
    try {
      const csvContent = fs.readFileSync(csvPath, 'utf8');
      const rows = csvContent.split('\n').slice(1).filter(r => r.trim()); // Skip header
      
      // Assuming image column is at index 5 or column name 'image'
      const header = csvContent.split('\n')[0].toLowerCase().split(',');
      const imageColIndex = header.findIndex(h => h.includes('image'));
      
      if (imageColIndex >= 0) {
        const imagesDir = path.join(path.dirname(csvPath), 'images');
        
        for (const row of rows) {
          const columns = row.split(',');
          const imageName = columns[imageColIndex]?.trim();
          
          if (imageName) {
            checks.image_checks.total++;
            const imagePath = path.join(imagesDir, imageName);
            
            if (fs.existsSync(imagePath)) {
              checks.image_checks.found++;
            } else {
              checks.image_checks.missing.push(imageName);
            }
          }
        }
        
        if (checks.image_checks.missing.length > 0) {
          checks.warnings.push(
            `${checks.image_checks.missing.length} images not found (non-critical)`
          );
        }
      }
    } catch (error) {
      checks.warnings.push(`Image validation error: ${error.message}`);
    }
  }
  
  return checks;
}

// ====================================================================
// 📊 PHASE 2: ARWEAVE LAYER VALIDATION
// ====================================================================

/**
 * Phase 2: Validate Arweave uploads and CID accessibility
 * @param {Object} context - Validation context
 * @returns {Promise<Object>} - Validation results
 */
async function validatePhase2_ArweaveLayer(context) {
  const { productsDir, mappingPath, fullArweaveCheck } = context;
  
  const checks = {
    mapping_exists: false,
    mapping_valid: false,
    mapping_product_count: 0,
    title_cids_total: 0,
    title_cids_accessible: 0,
    title_cids_checked: 0,
    product_cids_total: 0,
    product_cids_accessible: 0,
    product_cids_checked: 0,
    cid_consistency_errors: 0,
    resume_stats: { total: 0, resumed: 0, new: 0, savings_ar: 0 },
    sampled: !fullArweaveCheck,
    errors: [],
    warnings: []
  };
  
  // 1. Validate mapping file exists
  if (!fs.existsSync(mappingPath)) {
    checks.errors.push(`Mapping file not found: ${mappingPath}`);
    checks.errors.push('   → Action 42 (Arweave upload) not completed yet');
    return checks;
  }
  checks.mapping_exists = true;
  
  // 2. Parse mapping file
  let mapping;
  try {
    mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
    checks.mapping_valid = true;
    checks.mapping_product_count = Object.keys(mapping).length;
  } catch (e) {
    checks.errors.push(`Mapping file parse error: ${e.message}`);
    return checks;
  }
  
  // 3. Determine which CIDs to check (sample or all)
  const productEntries = Object.entries(mapping);
  const entriesToCheck = fullArweaveCheck 
    ? productEntries 
    : productEntries.slice(0, ARWEAVE_SAMPLE_SIZE);
  
  if (!fullArweaveCheck && productEntries.length > ARWEAVE_SAMPLE_SIZE) {
    checks.warnings.push(
      `Sampling ${ARWEAVE_SAMPLE_SIZE}/${productEntries.length} products for quick check. ` +
      `Use --full-arweave-check for exhaustive validation.`
    );
  }
  
  // 4. Validate title CIDs accessibility
  for (const [productId, data] of entriesToCheck) {
    if (data.title_cid) {
      checks.title_cids_total++;
      checks.title_cids_checked++;
      
      try {
        const response = await fetch(`https://arweave.net/${data.title_cid}`);
        if (response.ok) {
          const content = await response.json();
          
          // Validate structure: should be multilingual object
          if (content && typeof content === 'object' && !Array.isArray(content)) {
            const hasLanguages = Object.keys(content).some(key => 
              SUPPORTED_LANGUAGES.includes(key)
            );
            
            if (hasLanguages) {
              checks.title_cids_accessible++;
            } else {
              checks.warnings.push(`Title CID has unexpected structure: ${productId}`);
            }
          } else {
            checks.warnings.push(`Title CID is not a valid multilingual object: ${productId}`);
          }
        } else {
          checks.warnings.push(`Title CID not accessible (HTTP ${response.status}): ${productId}`);
        }
      } catch (e) {
        checks.warnings.push(`Title CID fetch error: ${productId} - ${e.message}`);
      }
    }
  }
  
  // Count remaining (if sampled)
  if (!fullArweaveCheck) {
    checks.title_cids_total = productEntries.filter(([_, data]) => data.title_cid).length;
  }
  
  // 5. Validate product CIDs accessibility
  for (const [productId, data] of entriesToCheck) {
    if (data.product_cid) {
      checks.product_cids_total++;
      checks.product_cids_checked++;
      
      try {
        const response = await fetch(`https://arweave.net/${data.product_cid}`);
        if (response.ok) {
          const content = await response.json();
          
          // Validate structure: should have components and prices arrays
          if (content && content.components && content.prices) {
            checks.product_cids_accessible++;
            
            // Additional validation: components array structure
            if (!Array.isArray(content.components) || content.components.length === 0) {
              checks.warnings.push(`Product CID has empty components: ${productId}`);
            }
            
            // Additional validation: prices array structure
            if (!Array.isArray(content.prices) || content.prices.length === 0) {
              checks.warnings.push(`Product CID has empty prices: ${productId}`);
            }
          } else {
            checks.warnings.push(`Product CID has invalid structure: ${productId} (missing components or prices)`);
          }
        } else {
          checks.warnings.push(`Product CID not accessible (HTTP ${response.status}): ${productId}`);
        }
      } catch (e) {
        checks.warnings.push(`Product CID fetch error: ${productId} - ${e.message}`);
      }
    }
  }
  
  // Count remaining (if sampled)
  if (!fullArweaveCheck) {
    checks.product_cids_total = productEntries.filter(([_, data]) => data.product_cid).length;
  }
  
  // 6. CID consistency check (compare mapping vs local JSONs)
  for (const [productId, data] of productEntries) {
    const productJsonPath = path.join(productsDir, productId, `${productId}.json`);
    if (fs.existsSync(productJsonPath)) {
      try {
        const productData = JSON.parse(fs.readFileSync(productJsonPath, 'utf8'));
        
        // Check title CID consistency
        if (data.title_cid) {
          if (productData.title && productData.title !== data.title_cid) {
            checks.cid_consistency_errors++;
            checks.errors.push(
              `Title CID mismatch: ${productId} ` +
              `(JSON: ${productData.title}, Mapping: ${data.title_cid})`
            );
          }
        }
        
        // Note: product_cid usually not stored in local JSON, only in mapping
        
      } catch (e) {
        checks.warnings.push(`Failed to read product JSON for consistency check: ${productId}`);
      }
    }
  }
  
  // 7. Calculate resume statistics
  // Estimate: if CIDs exist in mapping and are accessible → they were resumed
  checks.resume_stats.total = checks.title_cids_total + checks.product_cids_total;
  
  // Extrapolate from sample if needed
  if (fullArweaveCheck) {
    checks.resume_stats.resumed = checks.title_cids_accessible + checks.product_cids_accessible;
  } else {
    // Extrapolate from sample
    const titleAccessRate = checks.title_cids_checked > 0 
      ? checks.title_cids_accessible / checks.title_cids_checked 
      : 1;
    const productAccessRate = checks.product_cids_checked > 0
      ? checks.product_cids_accessible / checks.product_cids_checked
      : 1;
    
    checks.resume_stats.resumed = Math.round(
      checks.title_cids_total * titleAccessRate +
      checks.product_cids_total * productAccessRate
    );
  }
  
  checks.resume_stats.new = checks.resume_stats.total - checks.resume_stats.resumed;
  checks.resume_stats.savings_ar = parseFloat((checks.resume_stats.resumed * 0.0005).toFixed(4));
  
  // ✅ NEW: Validate AmanitaInternational title localization (Simple Field format)
  checks.amanita_intl_validation = {
    enabled: false,
    products_checked: 0,
    products_in_contract: 0,
    products_missing: 0,
    cid_matches: 0,
    cid_mismatches: 0,
    products_with_intl: []
  };
  
  try {
    // Try to load AmanitaInternational contract
    const { ethers } = require('hardhat');
    const ContractManager = require('./lib/services/ContractManager');
    const EthersUtils = require('./lib/utils/EthersUtils');
    const config = require('./lib/config');
    
    const rpcUrl = context.network === 'localhost' ? 'http://127.0.0.1:8545' : config.get('network.rpcUrl');
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(ethersUtils, config);
    
    const amanitaIntl = await contractManager.loadUUPSContract('AmanitaInternational');
    checks.amanita_intl_validation.enabled = true;
    
    // Sample products for validation (same as Arweave check)
    const sampleSize = fullArweaveCheck ? Object.keys(mapping).length : Math.min(5, Object.keys(mapping).length);
    const productIds = Object.keys(mapping).slice(0, sampleSize);
    
    for (const productId of productIds) {
      const productData = mapping[productId];
      checks.amanita_intl_validation.products_checked++;
      
      // Check if product has AmanitaInternational entry (new format)
      if (productData.amanita_intl_uploaded && productData.amanita_intl_field) {
        const fieldKey = productData.amanita_intl_field; // e.g., "ProductName.amanita1"
        const expectedCID = productData.title_cid; // ✅ FIX: Use title_cid, not cid
        
        try {
          // Query AmanitaInternational for Simple Field
          const contractCID = await amanitaIntl.getSimpleFieldCID(fieldKey);
          
          if (contractCID === expectedCID) {
            checks.amanita_intl_validation.products_in_contract++;
            checks.amanita_intl_validation.cid_matches++;
            checks.amanita_intl_validation.products_with_intl.push(productId);
          } else if (contractCID && contractCID !== '') {
            checks.amanita_intl_validation.products_in_contract++;
            checks.amanita_intl_validation.cid_mismatches++;
            checks.warnings.push(
              `Product ${productId} title: CID mismatch in AmanitaInternational ` +
              `(mapping: ${expectedCID.substring(0, 10)}..., contract: ${contractCID.substring(0, 10)}...)`
            );
          } else {
            checks.amanita_intl_validation.products_missing++;
            checks.warnings.push(
              `Product ${productId} title: NOT in AmanitaInternational ` +
              `(field: ${fieldKey}, expected CID: ${expectedCID.substring(0, 10)}...)`
            );
          }
        } catch (contractError) {
          // Field doesn't exist
          checks.amanita_intl_validation.products_missing++;
          checks.warnings.push(
            `Product ${productId} title: Field not found in AmanitaInternational (${fieldKey})`
          );
        }
      } else {
        // Old format without amanita_intl_uploaded - expected for pre-upgrade data
        checks.warnings.push(
          `Product ${productId}: Not uploaded to AmanitaInternational (pre-upgrade data or upload skipped)`
        );
      }
    }
    
  } catch (contractError) {
    // AmanitaInternational not accessible or not deployed
    checks.warnings.push(
      `AmanitaInternational not accessible (${contractError.message}) - skipping title localization validation`
    );
  }
  
  return checks;
}

// ====================================================================
// 📊 PHASE 3: CONTRACT LAYER VALIDATION
// ====================================================================

/**
 * Phase 3: Validate ProductRegistry contract state
 * @param {Object} context - Validation context
 * @returns {Promise<Object>} - Validation results
 */
async function validatePhase3_ContractLayer(context) {
  const { network, sellerAddress, mappingPath, productsDir } = context;
  
  const checks = {
    contracts_loaded: false,
    total_products_contract: 0,
    total_products_expected: 0,
    products_active_count: 0,
    products_inactive_count: 0,
    seller_match_count: 0,
    seller_mismatch_count: 0,
    metadata_cid_match_count: 0,
    metadata_cid_mismatch_count: 0,
    component_ids_valid_count: 0,
    component_ids_invalid_count: 0,
    seller_authorized: false,
    products_detail: [], // Array of {id, name, active, seller_match, cid_match, component_count}
    errors: [],
    warnings: []
  };
  
  try {
    // Initialize contracts (same pattern as component validator and Phase 2)
    const { ethers } = require('hardhat');
    const ContractManager = require('./lib/services/ContractManager');
    const EthersUtils = require('./lib/utils/EthersUtils');
    const config = require('./lib/config');
    
    const rpcUrl = network === 'localhost' ? 'http://127.0.0.1:8545' : config.get('network.rpcUrl');
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(ethersUtils, config);
    
    // Load contracts via MagicRegistry
    const productRegistry = await contractManager.loadUUPSContract('ProductRegistry');
    const organicRegistry = await contractManager.loadUUPSContract('OrganicComponentRegistry');
    const spiralEngine = await contractManager.loadUUPSContract('SpiralEngine');
    
    checks.contracts_loaded = true;
    
    // Load mapping for product names and CID comparison
    let mapping = {};
    if (fs.existsSync(mappingPath)) {
      mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
      checks.total_products_expected = Object.keys(mapping).length;
    }
    
    // Get seller's products from contract
    const productIds = await productRegistry.getProductsBySeller(sellerAddress);
    checks.total_products_contract = productIds.length;
    
    if (checks.total_products_contract === 0) {
      checks.warnings.push('No products in ProductRegistry for this seller (Action 43 not completed yet)');
      return checks;
    }
    
    // Validate each product
    for (const productIdBigInt of productIds) {
      const productId = parseInt(productIdBigInt.toString());
      
      try {
        const product = await productRegistry.getProduct(productId);
        
        const productDetail = {
          id: productId,
          active: product.active,
          seller: product.seller,
          seller_match: product.seller.toLowerCase() === sellerAddress.toLowerCase(),
          component_count: product.componentIds.length,
          metadata_cid: product.metadataCID,
          component_ids: product.componentIds,
          name: `product_${productId}` // Default name
        };
        
        // Find product name from mapping (match by metadata CID)
        const mappingEntry = Object.entries(mapping).find(([_, data]) => 
          data.product_cid === product.metadataCID
        );
        
        if (mappingEntry) {
          productDetail.name = mappingEntry[0];
          productDetail.metadata_cid_match = true;
          checks.metadata_cid_match_count++;
        } else {
          productDetail.metadata_cid_match = false;
          checks.metadata_cid_mismatch_count++;
          checks.warnings.push(`Product ${i}: metadata CID not found in mapping (${product.metadataCID})`);
        }
        
        // Count active/inactive
        if (product.active) {
          checks.products_active_count++;
        } else {
          checks.products_inactive_count++;
          checks.errors.push(`Product ${productId} (${productDetail.name}) is NOT active (critical for frontend)`);
        }
        
        // Verify seller
        if (productDetail.seller_match) {
          checks.seller_match_count++;
        } else {
          checks.seller_mismatch_count++;
          checks.warnings.push(`Product ${productId} (${productDetail.name}): seller mismatch`);
        }
        
        // Verify component IDs exist in OrganicComponentRegistry
        let allComponentsValid = true;
        for (const compId of product.componentIds) {
          const exists = await organicRegistry.componentExists(compId);
          if (!exists) {
            allComponentsValid = false;
            checks.errors.push(
              `Product ${productId} (${productDetail.name}): Component '${compId}' NOT in OrganicComponentRegistry (product broken!)`
            );
          }
        }
        
        if (allComponentsValid) {
          checks.component_ids_valid_count++;
        } else {
          checks.component_ids_invalid_count++;
        }
        
        checks.products_detail.push(productDetail);
        
      } catch (e) {
        checks.errors.push(`Failed to validate product ${productId}: ${e.message}`);
      }
    }
    
    // Check seller authorization
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    checks.seller_authorized = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
    
    if (!checks.seller_authorized) {
      checks.errors.push(`Seller ${sellerAddress} NOT authorized (missing SELLER_ROLE)`);
      checks.errors.push('   → Run Action 777 or Action 888 to activate seller');
    }
    
  } catch (error) {
    checks.errors.push(`Contract validation error: ${error.message}`);
    checks.warnings.push('Contract validation skipped (ensure node is running and Action 1 completed)');
  }
  
  return checks;
}

// ====================================================================
// 📊 PHASE 4: CONSISTENCY LAYER VALIDATION
// ====================================================================

/**
 * Phase 4: Validate cross-layer data consistency
 * @param {Object} context - Validation context
 * @returns {Promise<Object>} - Validation results
 */
async function validatePhase4_ConsistencyLayer(context) {
  const { csvPath, productsDir, mappingPath, phase1Results, phase3Results } = context;
  
  const checks = {
    csv_count: 0,
    json_count: 0,
    mapping_count: 0,
    contract_count: 0,
    count_consistency: false,
    traceability_coverage: 0,
    traceability_expected: 0,
    errors: [],
    warnings: []
  };
  
  // 1. Collect counts from previous phases and direct checks
  
  // CSV count
  if (phase1Results && phase1Results.csv_row_count > 0) {
    checks.csv_count = phase1Results.csv_row_count;
  } else if (csvPath && fs.existsSync(csvPath)) {
    const csvContent = fs.readFileSync(csvPath, 'utf8');
    checks.csv_count = csvContent.split('\n').filter(r => r.trim()).length - 1;
  }
  
  // JSON count (product directories)
  if (phase1Results) {
    checks.json_count = phase1Results.product_dirs_count;
  } else if (fs.existsSync(productsDir)) {
    const entries = fs.readdirSync(productsDir, { withFileTypes: true });
    checks.json_count = entries.filter(e => e.isDirectory() && !e.name.startsWith('_')).length;
  }
  
  // Mapping count
  if (fs.existsSync(mappingPath)) {
    try {
      const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
      checks.mapping_count = Object.keys(mapping).length;
    } catch (e) {
      checks.warnings.push(`Failed to read mapping for count: ${e.message}`);
    }
  }
  
  // Contract count
  if (phase3Results && phase3Results.contracts_loaded) {
    checks.contract_count = phase3Results.total_products_contract;
  }
  
  // 2. Check count consistency across all layers
  const counts = [checks.csv_count, checks.json_count, checks.mapping_count, checks.contract_count].filter(c => c > 0);
  
  if (counts.length > 1) {
    const allMatch = counts.every(c => c === counts[0]);
    checks.count_consistency = allMatch;
    
    if (!allMatch) {
      checks.errors.push(
        `❌ CRITICAL: Count mismatch across layers! ` +
        `CSV=${checks.csv_count}, JSON=${checks.json_count}, ` +
        `Mapping=${checks.mapping_count}, Contract=${checks.contract_count}`
      );
    }
  } else {
    checks.warnings.push('Insufficient data for cross-layer count validation');
  }
  
  // 3. End-to-end traceability (if CSV provided)
  if (csvPath && fs.existsSync(csvPath) && fs.existsSync(mappingPath)) {
    try {
      const csvContent = fs.readFileSync(csvPath, 'utf8');
      const rows = csvContent.split('\n').slice(1).filter(r => r.trim());
      const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
      
      checks.traceability_expected = rows.length;
      
      // Parse CSV header to find column indices
      const header = csvContent.split('\n')[0].toLowerCase().split(',');
      const productIdColIndex = header.findIndex(h => h.includes('product_business_id') || h.includes('product_id'));
      
      for (const row of rows) {
        const columns = row.split(',');
        const productBusinessId = columns[productIdColIndex]?.trim();
        
        if (!productBusinessId) continue;
        
        let traced = true;
        
        // Check 1: Product directory exists
        const productDir = path.join(productsDir, productBusinessId);
        if (!fs.existsSync(productDir)) {
          checks.errors.push(`❌ Traceability broken: ${productBusinessId} - product directory not found`);
          traced = false;
          continue;
        }
        
        // Check 2: In mapping file
        if (!mapping[productBusinessId]) {
          checks.errors.push(`❌ Traceability broken: ${productBusinessId} - not in mapping file`);
          traced = false;
          continue;
        }
        
        // Check 3: In contract (if phase3 available)
        if (phase3Results && phase3Results.products_detail && phase3Results.products_detail.length > 0) {
          const inContract = phase3Results.products_detail.some(p => p.name === productBusinessId);
          if (!inContract) {
            checks.errors.push(`❌ Traceability broken: ${productBusinessId} - not found in contract`);
            traced = false;
            continue;
          }
        }
        
        if (traced) {
          checks.traceability_coverage++;
        }
      }
      
      // Check traceability coverage
      if (checks.traceability_coverage < checks.traceability_expected) {
        const missing = checks.traceability_expected - checks.traceability_coverage;
        checks.warnings.push(
          `${missing}/${checks.traceability_expected} products have broken traceability (see errors above)`
        );
      }
      
    } catch (e) {
      checks.warnings.push(`Traceability check failed: ${e.message}`);
    }
  } else {
    checks.warnings.push('CSV or mapping not available - skipping end-to-end traceability check');
  }
  
  return checks;
}

// ====================================================================
// 🖼️ PHASE 6: IMAGE VALIDATION
// ====================================================================

/**
 * Phase 6: Image Validation
 * 
 * Validates that product images are properly uploaded to Arweave
 * and accessible via their CIDs.
 * 
 * @param {Object} context - Validation context
 * @returns {Object} Phase 6 validation results
 */
async function validatePhase6_ImageValidation(context) {
  const { mappingPath, productsDir, sellerId } = context;
  
  const checks = {
    products_with_images: 0,
    images_uploaded_count: 0,
    images_missing_count: 0,
    images_accessible_count: 0,
    images_inaccessible_count: 0,
    image_formats_valid: 0,
    image_formats_invalid: 0,
    total_image_size: 0,
    image_cids: [],
    errors: [],
    warnings: []
  };
  
  console.log('\n🖼️ Phase 6: Image Validation');
  console.log('='.repeat(50));
  
  // Load combined mapping
  const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
  const productIds = Object.keys(mapping);
  
  console.log(`📁 Checking ${productIds.length} products for images...`);
  
  for (const productId of productIds) {
    const productData = mapping[productId];
    
    // Check if product has image data
    if (productData.image_cid || productData.image_filename) {
      checks.products_with_images++;
      
      // Check if image CID exists
      if (productData.image_cid) {
        checks.images_uploaded_count++;
        checks.image_cids.push({
          product_id: productId,
          cid: productData.image_cid,
          filename: productData.image_filename,
          url: productData.image_url,
          size: productData.image_size
        });
        
        // Add to total size
        if (productData.image_size) {
          checks.total_image_size += parseInt(productData.image_size);
        }
        
        // Test accessibility and format validation
        try {
          const imageUrl = productData.image_url || `https://arweave.net/${productData.image_cid}`;
          const response = await fetch(imageUrl, { method: 'HEAD' });
          
          if (response.ok) {
            checks.images_accessible_count++;
            
            // ✅ NEW: Validate image format (Content-Type header)
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.startsWith('image/')) {
              checks.image_formats_valid++;
            } else {
              checks.image_formats_invalid++;
              const errorMsg = `Product ${productId}: Invalid image format (${contentType || 'unknown'})`;
              checks.errors.push(errorMsg);
              console.error(`   ❌ ${errorMsg}`);
            }
            
          } else {
            checks.images_inaccessible_count++;
            const warnMsg = `Product ${productId}: Image not accessible (HTTP ${response.status})`;
            checks.warnings.push(warnMsg);
            console.warn(`   ⚠️ ${warnMsg}`);
          }
        } catch (error) {
          checks.images_inaccessible_count++;
          const warnMsg = `Product ${productId}: Image accessibility check failed (${error.message})`;
          checks.warnings.push(warnMsg);
          console.warn(`   ⚠️ ${warnMsg}`);
        }
        
      } else {
        checks.images_missing_count++;
        const warnMsg = `Product ${productId} has image filename but no CID`;
        checks.warnings.push(warnMsg);
        console.warn(`   ⚠️ ${warnMsg}`);
      }
    }
  }
  
  // Calculate score
  let score = 10.0;
  
  if (checks.products_with_images > 0) {
    const uploadRate = checks.images_uploaded_count / checks.products_with_images;
    if (uploadRate < 1.0) {
      score -= (1.0 - uploadRate) * 3; // Penalty for missing uploads
    }
    
    if (checks.images_uploaded_count > 0) {
      const accessibilityRate = checks.images_accessible_count / checks.images_uploaded_count;
      if (accessibilityRate < 1.0) {
        score -= (1.0 - accessibilityRate) * 5; // Penalty for inaccessible images
      }
      
      // ✅ NEW: Format validation penalty
      if (checks.images_accessible_count > 0) {
        const formatRate = checks.image_formats_valid / checks.images_accessible_count;
        if (formatRate < 1.0) {
          score -= (1.0 - formatRate) * 3; // Penalty for invalid image formats
        }
      }
    }
  }
  
  return {
    checks,
    score: Math.max(0, score),
    execution_time_ms: 0 // Will be set by caller
  };
}

/**
 * Print Phase 6 (Image Validation) results
 * @param {Object} phase6 - Phase 6 validation results
 * @param {number} score - Phase 6 score
 */
function printPhase6(phase6, score) {
  console.log('\n🖼️ Phase 6: Image Validation');
  console.log('='.repeat(50));
  console.log(`   Score: ${score.toFixed(1)}/10 ${score >= 8 ? '✅' : score >= 6 ? '⚠️' : '❌'}`);
  console.log(`   Products with Images: ${phase6.checks.products_with_images}`);
  console.log(`   Images Uploaded: ${phase6.checks.images_uploaded_count}`);
  console.log(`   Images Accessible: ${phase6.checks.images_accessible_count}`);
  
  // ✅ NEW: Format validation stats
  if (phase6.checks.images_accessible_count > 0) {
    console.log(`   Image Formats Valid: ${phase6.checks.image_formats_valid}/${phase6.checks.images_accessible_count}`);
    if (phase6.checks.image_formats_invalid > 0) {
      console.log(`   ❌ Invalid Formats: ${phase6.checks.image_formats_invalid}`);
    }
  }
  
  console.log(`   Total Image Size: ${(phase6.checks.total_image_size / 1024 / 1024).toFixed(2)} MB`);
  
  if (phase6.checks.images_missing_count > 0) {
    console.log(`   ⚠️ Missing CIDs: ${phase6.checks.images_missing_count}`);
  }
  
  if (phase6.checks.images_inaccessible_count > 0) {
    console.log(`   ⚠️ Inaccessible Images: ${phase6.checks.images_inaccessible_count}`);
  }
  
  // Show errors if any
  if (phase6.checks.errors.length > 0) {
    console.log(`\n   ❌ Errors (${phase6.checks.errors.length}):`);
    phase6.checks.errors.slice(0, 3).forEach(err => {
      console.log(`      • ${err}`);
    });
    if (phase6.checks.errors.length > 3) {
      console.log(`      ... and ${phase6.checks.errors.length - 3} more`);
    }
  }
  
  // Show warnings if any
  if (phase6.checks.warnings.length > 0) {
    console.log(`\n   ⚠️ Warnings (${phase6.checks.warnings.length}):`);
    phase6.checks.warnings.slice(0, 3).forEach(warn => {
      console.log(`      • ${warn}`);
    });
    if (phase6.checks.warnings.length > 3) {
      console.log(`      ... and ${phase6.checks.warnings.length - 3} more`);
    }
  }
  
  // Show sample image CIDs
  if (phase6.checks.image_cids.length > 0) {
    console.log(`\n   📸 Sample Image CIDs:`);
    phase6.checks.image_cids.slice(0, 3).forEach(img => {
      console.log(`      • ${img.product_id}: ${img.cid}`);
    });
    if (phase6.checks.image_cids.length > 3) {
      console.log(`      ... and ${phase6.checks.image_cids.length - 3} more`);
    }
  }
}

// ====================================================================
// 📊 PHASE 5: COMPONENT INTEGRATION VALIDATION
// ====================================================================

/**
 * Phase 5: Validate component integration with OrganicComponentRegistry
 * @param {Object} context - Validation context
 * @returns {Promise<Object>} - Validation results
 */
async function validatePhase5_ComponentIntegration(context) {
  const { mappingPath, productsDir, network, sellerAddress } = context;
  
  const checks = {
    unique_components: [],
    components_exist_count: 0,
    components_missing_count: 0,
    components_mapping_valid: 0,
    components_mapping_invalid: 0,
    components_active_count: 0,
    components_creator_match: 0,
    registry_connected: false,
    registry_address: null,
    action444_compatible: false,
    critical_blockers: [],
    errors: [],
    warnings: []
  };
  
  try {
    // Initialize contracts
    const { ethers } = require('hardhat');
    const ContractManager = require('./lib/services/ContractManager');
    const EthersUtils = require('./lib/utils/EthersUtils');
    const config = require('./lib/config');
    
    const rpcUrl = network === 'localhost' ? 'http://127.0.0.1:8545' : config.get('network.rpcUrl');
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(ethersUtils, config);
    
    const productRegistry = await contractManager.loadUUPSContract('ProductRegistry');
    const organicRegistry = await contractManager.loadUUPSContract('OrganicComponentRegistry');
    
    // 1. Check registry connection
    const registryAddr = await productRegistry.componentRegistry();
    checks.registry_connected = registryAddr !== ethers.ZeroAddress;
    checks.registry_address = registryAddr;
    
    if (!checks.registry_connected) {
      checks.critical_blockers.push('ProductRegistry not connected to OrganicComponentRegistry');
      checks.errors.push('❌ CRITICAL: ProductRegistry.organicComponentRegistry() == ZeroAddress');
      checks.errors.push('   → Run Action 2 to setup connections');
      return checks;
    }
    
    // 2. Extract unique components from mapping
    if (!fs.existsSync(mappingPath)) {
      checks.warnings.push('Mapping file not found - skipping component extraction');
      return checks;
    }
    
    const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
    const componentSet = new Set();
    
    for (const [productId, data] of Object.entries(mapping)) {
      if (data.component_ids && Array.isArray(data.component_ids)) {
        data.component_ids.forEach(id => componentSet.add(id));
      } else {
        // Fallback: read from product JSON
        const productJsonPath = path.join(productsDir, productId, `${productId}.json`);
        if (fs.existsSync(productJsonPath)) {
          const productData = JSON.parse(fs.readFileSync(productJsonPath, 'utf8'));
          if (productData.components) {
            productData.components.forEach(comp => {
              if (comp.component_business_id) {
                componentSet.add(comp.component_business_id);
              }
            });
          }
        }
      }
    }
    
    checks.unique_components = Array.from(componentSet);
    
    if (checks.unique_components.length === 0) {
      checks.warnings.push('No components found in products');
      return checks;
    }
    
    // 3. Validate each component
    for (const compId of checks.unique_components) {
      // Check existence
      const exists = await organicRegistry.componentExists(compId);
      if (exists) {
        checks.components_exist_count++;
        
        // Get blockchain ID
        const blockchainId = await organicRegistry.businessIdToComponentId(compId);
        if (blockchainId.toString() !== '0') {
          checks.components_mapping_valid++;
          
          // Get component details
          try {
            const component = await organicRegistry.getComponent(blockchainId);
            
            // Check status (0 = ACTIVE)
            if (component.status.toString() === '0') {
              checks.components_active_count++;
            } else {
              checks.warnings.push(`Component ${compId} not ACTIVE (status: ${component.status})`);
            }
            
            // Check creator
            if (component.creator.toLowerCase() === sellerAddress.toLowerCase()) {
              checks.components_creator_match++;
            } else {
              checks.warnings.push(`Component ${compId} creator mismatch (expected: ${sellerAddress}, got: ${component.creator})`);
            }
            
          } catch (e) {
            checks.warnings.push(`Failed to get component details for ${compId}: ${e.message}`);
          }
          
        } else {
          checks.components_mapping_invalid++;
          checks.errors.push(`❌ Component ${compId} has invalid mapping (businessIdToComponentId returned 0)`);
        }
        
      } else {
        checks.components_missing_count++;
        checks.critical_blockers.push(`Component ${compId} NOT in OrganicComponentRegistry`);
        checks.errors.push(`❌ CRITICAL: Component '${compId}' missing from OrganicComponentRegistry`);
        checks.errors.push(`   → ProductRegistry.createProduct() will FAIL with ComponentNotFound(${compId})`);
        checks.errors.push(`   → Run Action 555 to upload components before Action 444`);
      }
    }
    
    // 4. Determine Action 444 compatibility
    checks.action444_compatible = 
      checks.registry_connected &&
      checks.components_missing_count === 0 &&
      checks.critical_blockers.length === 0;
    
  } catch (error) {
    checks.errors.push(`Component integration validation error: ${error.message}`);
    checks.warnings.push('Component validation skipped (ensure node is running and Action 1 completed)');
  }
  
  return checks;
}

// ====================================================================
// 📊 SCORING FUNCTIONS
// ====================================================================

/**
 * Calculate Phase 1 score
 * @param {Object} phase1 - Phase 1 validation results
 * @returns {number} - Score 0-10
 */
function calculatePhase1Score(phase1) {
  if (!phase1) return 0;
  
  let score = 10;
  
  // Critical checks
  if (!phase1.csv_exists && phase1.csv_row_count === 0) {
    score -= 2; // CSV optional if products already exist
  }
  if (!phase1.csv_columns_valid && phase1.csv_exists) {
    score -= 3; // Invalid CSV structure is critical
  }
  if (phase1.csv_duplicate_ids.length > 0) {
    score -= 2; // Duplicates are serious
  }
  if (phase1.product_dirs_count !== phase1.product_dirs_expected) {
    score -= 3; // Count mismatch is critical
  }
  if (phase1.product_json_count !== phase1.product_dirs_count) {
    score -= 2; // Missing product files
  }
  if (phase1.product_json_valid !== phase1.product_json_count) {
    score -= 2; // Invalid JSON structure
  }
  
  // Important checks
  if (phase1.title_json_count !== phase1.product_dirs_count) {
    score -= 1; // Missing title files
  }
  if (phase1.title_json_valid !== phase1.title_json_count) {
    score -= 1; // Invalid title structure
  }
  if (!phase1.transformation_report_exists) {
    score -= 1; // Report missing (warning)
  }
  if (!phase1.report_stats_match && phase1.transformation_report_exists) {
    score -= 1; // Stats mismatch (warning)
  }
  
  // Image checks (don't penalize, just informational)
  // Missing images are warnings, not errors
  
  return Math.max(0, score);
}

/**
 * Calculate Phase 2 score - Arweave layer
 * @param {Object} phase2 - Phase 2 validation results
 * @returns {number} - Score 0-10
 */
function calculatePhase2Score(phase2) {
  if (!phase2 || !phase2.mapping_exists) return 0;
  
  let score = 10;
  
  // Critical: mapping file validity
  if (!phase2.mapping_valid) return 0;
  
  // Important: CID accessibility
  // If sampled, use checked counts; if full, use totals
  const titleAccessRate = phase2.title_cids_checked > 0 
    ? phase2.title_cids_accessible / phase2.title_cids_checked 
    : 1;
  const productAccessRate = phase2.product_cids_checked > 0
    ? phase2.product_cids_accessible / phase2.product_cids_checked
    : 1;
  
  const avgAccessRate = (titleAccessRate + productAccessRate) / 2;
  score = avgAccessRate * 10;
  
  // Penalty for consistency errors (critical)
  if (phase2.cid_consistency_errors > 0) {
    score -= Math.min(3, phase2.cid_consistency_errors);
  }
  
  // ✅ NEW: AmanitaInternational title localization (Simple Field)
  if (phase2.amanita_intl_validation?.enabled) {
    const checked = phase2.amanita_intl_validation.products_checked;
    if (checked > 0) {
      const matches = phase2.amanita_intl_validation.cid_matches;
      const matchRate = matches / checked;
      
      // Penalty if products missing from AmanitaInternational (up to -1 point)
      if (matchRate < 1.0) {
        score -= (1.0 - matchRate) * 1;
      }
    }
  }
  // No penalty if AmanitaInternational not enabled (backward compatibility)
  
  return Math.max(0, score);
}

/**
 * Calculate Phase 3 score - Contract layer
 * @param {Object} phase3 - Phase 3 validation results
 * @returns {number} - Score 0-10
 */
function calculatePhase3Score(phase3) {
  if (!phase3 || !phase3.contracts_loaded) return 5; // Partial credit if contracts not accessible
  
  if (phase3.total_products_contract === 0) return 0; // No products = action 43 not done
  
  let score = 10;
  
  // CRITICAL: All products must be active
  const activeRate = phase3.total_products_contract > 0
    ? phase3.products_active_count / phase3.total_products_contract
    : 0;
  if (activeRate < 1.0) {
    score -= (1.0 - activeRate) * 5; // Up to -5 for inactive products
  }
  
  // CRITICAL: Component IDs must be valid
  if (phase3.component_ids_invalid_count > 0) {
    score -= 3;
  }
  
  // Important: Metadata CID matching
  const cidMatchRate = phase3.total_products_contract > 0
    ? phase3.metadata_cid_match_count / phase3.total_products_contract
    : 1;
  if (cidMatchRate < 1.0) {
    score -= (1.0 - cidMatchRate) * 2;
  }
  
  // Important: Seller authorization
  if (!phase3.seller_authorized) {
    score -= 1;
  }
  
  // Medium: Seller match for products
  const sellerMatchRate = phase3.total_products_contract > 0
    ? phase3.seller_match_count / phase3.total_products_contract
    : 1;
  if (sellerMatchRate < 1.0) {
    score -= (1.0 - sellerMatchRate) * 1;
  }
  
  return Math.max(0, score);
}

/**
 * Calculate Phase 4 score - Consistency layer
 * @param {Object} phase4 - Phase 4 validation results
 * @returns {number} - Score 0-10
 */
function calculatePhase4Score(phase4) {
  if (!phase4) return 0;
  
  let score = 10;
  
  // CRITICAL: Count consistency across layers
  if (!phase4.count_consistency) {
    score -= 5;
  }
  
  // Important: End-to-end traceability
  if (phase4.traceability_expected > 0) {
    const traceabilityRate = phase4.traceability_coverage / phase4.traceability_expected;
    if (traceabilityRate < 1.0) {
      score -= (1.0 - traceabilityRate) * 5; // Up to -5 for broken traceability
    }
  }
  
  return Math.max(0, score);
}

/**
 * Calculate Phase 5 score - Component integration
 * @param {Object} phase5 - Phase 5 validation results
 * @returns {number} - Score 0-10
 */
function calculatePhase5Score(phase5) {
  if (!phase5) return 0;
  
  // Binary critical checks: if any fail, score = 0
  if (!phase5.registry_connected) return 0; // CRITICAL: ProductRegistry not connected
  if (phase5.components_missing_count > 0) return 0; // CRITICAL: Missing components = Action 444 will fail
  if (phase5.critical_blockers.length > 0) return 0; // CRITICAL: Blockers present
  
  let score = 10;
  
  // Medium penalties for warnings
  if (phase5.components_mapping_invalid > 0) {
    score -= 3; // Invalid mappings are serious
  }
  
  // Check if all components are active
  if (phase5.unique_components.length > 0) {
    const activeRate = phase5.components_active_count / phase5.unique_components.length;
    if (activeRate < 1.0) {
      score -= (1.0 - activeRate) * 2; // Up to -2 for inactive components
    }
  }
  
  // Check creator match
  if (phase5.unique_components.length > 0) {
    const creatorRate = phase5.components_creator_match / phase5.unique_components.length;
    if (creatorRate < 1.0) {
      score -= (1.0 - creatorRate) * 1; // Up to -1 for creator mismatches
    }
  }
  
  return Math.max(0, score);
}

/**
 * Calculate overall quality score (weighted average)
 * @param {Object} scores - Individual phase scores
 * @returns {number} - Overall quality score 0-10
 */
function calculateQualityScore(scores) {
  const weights = {
    phase1: 0.15,  // CSV + FileSystem
    phase2: 0.25,  // Arweave
    phase3: 0.35,  // Contract (most critical)
    phase4: 0.20,  // Consistency
    phase5: 0.05   // Component Integration (binary)
  };
  
  const weightedScore = 
    scores.phase1 * weights.phase1 +
    scores.phase2 * weights.phase2 +
    scores.phase3 * weights.phase3 +
    scores.phase4 * weights.phase4 +
    scores.phase5 * weights.phase5;
  
  return parseFloat(weightedScore.toFixed(1));
}

// ====================================================================
// 🎨 REPORT PRINTING
// ====================================================================

/**
 * Print Phase 1 results
 */
function printPhase1(phase1, score) {
  console.log('\n📁 PHASE 1: CSV + FILE SYSTEM VALIDATION');
  console.log('-'.repeat(80));
  
  if (phase1.csv_exists) {
    console.log(`   CSV File: ✅ EXISTS (${phase1.csv_row_count} rows)`);
    console.log(`   CSV Columns: ${phase1.csv_columns_valid ? '✅ VALID' : '❌ INVALID'}`);
    
    if (phase1.csv_duplicate_ids.length > 0) {
      console.log(`   ⚠️ Duplicate IDs: ${phase1.csv_duplicate_ids.length}`);
    }
  } else {
    console.log(`   CSV File: ⚠️ NOT PROVIDED (validation based on existing files)`);
  }
  
  console.log(`   Product Directories: ${phase1.product_dirs_count}/${phase1.product_dirs_expected} ${phase1.product_dirs_count === phase1.product_dirs_expected ? '✅' : '❌'}`);
  console.log(`   Product JSONs: ${phase1.product_json_valid}/${phase1.product_json_count} ${phase1.product_json_valid === phase1.product_json_count ? '✅' : '❌'}`);
  console.log(`   Title JSONs: ${phase1.title_json_valid}/${phase1.title_json_count} ${phase1.title_json_valid === phase1.title_json_count ? '✅' : '❌'}`);
  console.log(`   Transformation Report: ${phase1.transformation_report_exists ? '✅ EXISTS' : '⚠️ MISSING'}`);
  
  if (phase1.transformation_report_exists) {
    console.log(`      Report Stats Match: ${phase1.report_stats_match ? '✅ YES' : '⚠️ NO'}`);
  }
  
  if (phase1.image_checks.total > 0) {
    const foundPercent = Math.round((phase1.image_checks.found / phase1.image_checks.total) * 100);
    console.log(`   Images: ${phase1.image_checks.found}/${phase1.image_checks.total} (${foundPercent}%)`);
    if (phase1.image_checks.missing.length > 0) {
      console.log(`      ⚠️ Missing (non-critical): ${phase1.image_checks.missing.slice(0, 3).join(', ')}${phase1.image_checks.missing.length > 3 ? '...' : ''}`);
    }
  }
  
  console.log(`\n   Score: ${score.toFixed(1)}/10 ${score >= 7 ? '✅' : '❌'}`);
  
  // Print errors
  if (phase1.errors.length > 0) {
    console.log(`\n   ❌ Errors: ${phase1.errors.length}`);
    phase1.errors.forEach(err => console.log(`      ${err}`));
  }
  
  // Print warnings (filter expected ones)
  const unexpectedWarnings = phase1.warnings.filter(w => !isExpectedWarning(w));
  if (unexpectedWarnings.length > 0) {
    console.log(`\n   ⚠️ Warnings: ${unexpectedWarnings.length}`);
    unexpectedWarnings.forEach(warn => console.log(`      ${warn}`));
  }
}

/**
 * Print Phase 2 results
 */
function printPhase2(phase2, score) {
  console.log('\n☁️ PHASE 2: ARWEAVE LAYER VALIDATION');
  console.log('-'.repeat(80));
  console.log(`   Mapping File: ${phase2.mapping_exists ? '✅ EXISTS' : '❌ MISSING'}`);
  console.log(`   Mapping Valid: ${phase2.mapping_valid ? '✅ YES' : '❌ NO'}`);
  console.log(`   Products in Mapping: ${phase2.mapping_product_count}`);
  
  if (phase2.mapping_valid) {
    // CID accessibility stats
    if (phase2.sampled) {
      console.log(`   Title CIDs Checked: ${phase2.title_cids_checked}/${phase2.title_cids_total} (sampled)`);
      console.log(`   Title CIDs Accessible: ${phase2.title_cids_accessible}/${phase2.title_cids_checked} ✅`);
      console.log(`   Product CIDs Checked: ${phase2.product_cids_checked}/${phase2.product_cids_total} (sampled)`);
      console.log(`   Product CIDs Accessible: ${phase2.product_cids_accessible}/${phase2.product_cids_checked} ✅`);
    } else {
      console.log(`   Title CIDs Accessible: ${phase2.title_cids_accessible}/${phase2.title_cids_total} ✅`);
      console.log(`   Product CIDs Accessible: ${phase2.product_cids_accessible}/${phase2.product_cids_total} ✅`);
    }
    
    // CID consistency
    if (phase2.cid_consistency_errors > 0) {
      console.log(`   CID Consistency: ❌ ${phase2.cid_consistency_errors} errors`);
    } else {
      console.log(`   CID Consistency: ✅ MATCH`);
    }
    
    // Resume statistics
    console.log(`\n   📊 Resume Statistics:`);
    console.log(`      Total CIDs: ${phase2.resume_stats.total}`);
    console.log(`      Resumed (existing): ${phase2.resume_stats.resumed}`);
    console.log(`      New uploads: ${phase2.resume_stats.new}`);
    console.log(`      💰 Estimated savings: ${phase2.resume_stats.savings_ar.toFixed(4)} AR`);
  }
  
  // ✅ NEW: AmanitaInternational title localization status (Simple Field)
  if (phase2.amanita_intl_validation?.enabled) {
    console.log(`\n   🌐 AmanitaInternational Title Localization (Simple Field):`);
    const checked = phase2.amanita_intl_validation.products_checked;
    const inContract = phase2.amanita_intl_validation.products_in_contract;
    const missing = phase2.amanita_intl_validation.products_missing;
    const matches = phase2.amanita_intl_validation.cid_matches;
    
    if (checked > 0) {
      const coverageRate = Math.round((inContract / checked) * 100);
      console.log(`      Products Checked: ${checked}`);
      console.log(`      In Contract: ${inContract}/${checked} (${coverageRate}%)`);
      
      if (matches > 0) {
        console.log(`      ✅ CID Matches: ${matches}/${inContract}`);
      }
      
      if (missing > 0) {
        console.log(`      ⚠️ Missing: ${missing} products not in contract`);
      }
      
      if (phase2.amanita_intl_validation.products_with_intl.length > 0) {
        console.log(`      Products: ${phase2.amanita_intl_validation.products_with_intl.slice(0, 3).join(', ')}${phase2.amanita_intl_validation.products_with_intl.length > 3 ? '...' : ''}`);
      }
    } else {
      console.log(`      ⚠️ No products with AmanitaInternational entries (pre-upgrade data)`);
    }
  }
  
  console.log(`\n   Score: ${score.toFixed(1)}/10 ${score >= 7 ? '✅' : '❌'}`);
  
  // Print errors
  if (phase2.errors.length > 0) {
    console.log(`\n   ❌ Errors: ${phase2.errors.length}`);
    phase2.errors.forEach(err => console.log(`      ${err}`));
  }
  
  // Print warnings (filter expected ones)
  const unexpectedWarnings = phase2.warnings.filter(w => !isExpectedWarning(w));
  if (unexpectedWarnings.length > 0) {
    console.log(`\n   ⚠️ Warnings: ${unexpectedWarnings.length}`);
    unexpectedWarnings.slice(0, 5).forEach(warn => console.log(`      ${warn}`));
    if (unexpectedWarnings.length > 5) {
      console.log(`      ... and ${unexpectedWarnings.length - 5} more`);
    }
  }
}

/**
 * Print Phase 3 results
 */
function printPhase3(phase3, score) {
  console.log('\n📜 PHASE 3: CONTRACT LAYER VALIDATION');
  console.log('-'.repeat(80));
  console.log(`   Contracts Loaded: ${phase3.contracts_loaded ? '✅ YES' : '❌ NO'}`);
  
  if (!phase3.contracts_loaded) {
    console.log(`   ⚠️ Contract validation skipped (node not running or contracts not deployed)`);
  } else {
    console.log(`   Total Products (contract): ${phase3.total_products_contract}`);
    console.log(`   Total Products (expected): ${phase3.total_products_expected}`);
    
    // Count matching
    const countMatch = phase3.total_products_contract === phase3.total_products_expected;
    console.log(`   Count Match: ${countMatch ? '✅ YES' : '⚠️ NO'}`);
    
    // Activation status
    const allActive = phase3.products_active_count === phase3.total_products_contract;
    console.log(`   Products Active: ${phase3.products_active_count}/${phase3.total_products_contract} ${allActive ? '✅' : '❌'}`);
    
    if (phase3.products_inactive_count > 0) {
      console.log(`   Products Inactive: ${phase3.products_inactive_count} ❌`);
    }
    
    // Seller matching
    const allSellerMatch = phase3.seller_match_count === phase3.total_products_contract;
    console.log(`   Seller Match: ${phase3.seller_match_count}/${phase3.total_products_contract} ${allSellerMatch ? '✅' : '⚠️'}`);
    
    // Metadata CID matching
    const allCidMatch = phase3.metadata_cid_match_count === phase3.total_products_contract;
    console.log(`   Metadata CID Match: ${phase3.metadata_cid_match_count}/${phase3.total_products_contract} ${allCidMatch ? '✅' : '⚠️'}`);
    
    // Component IDs validity
    const allComponentsValid = phase3.component_ids_valid_count === phase3.total_products_contract;
    console.log(`   Component IDs Valid: ${phase3.component_ids_valid_count}/${phase3.total_products_contract} ${allComponentsValid ? '✅' : '❌'}`);
    
    // Seller authorization
    console.log(`   Seller Authorized: ${phase3.seller_authorized ? '✅ YES' : '❌ NO'}`);
    
    // List products (first 5)
    if (phase3.products_detail.length > 0) {
      console.log(`\n   📦 Products (showing first 5/${phase3.products_detail.length}):`);
      phase3.products_detail.slice(0, 5).forEach(p => {
        const status = p.active ? '✅' : '❌';
        console.log(`      ${status} ${p.id}. ${p.name} (${p.component_count} components)`);
      });
      if (phase3.products_detail.length > 5) {
        console.log(`      ... and ${phase3.products_detail.length - 5} more`);
      }
    }
  }
  
  console.log(`\n   Score: ${score.toFixed(1)}/10 ${score >= 7 ? '✅' : '❌'}`);
  
  // Print errors
  if (phase3.errors.length > 0) {
    console.log(`\n   ❌ Errors: ${phase3.errors.length}`);
    phase3.errors.slice(0, 5).forEach(err => console.log(`      ${err}`));
    if (phase3.errors.length > 5) {
      console.log(`      ... and ${phase3.errors.length - 5} more`);
    }
  }
  
  // Print warnings (filter expected ones)
  const unexpectedWarnings = phase3.warnings.filter(w => !isExpectedWarning(w));
  if (unexpectedWarnings.length > 0) {
    console.log(`\n   ⚠️ Warnings: ${unexpectedWarnings.length}`);
    unexpectedWarnings.slice(0, 5).forEach(warn => console.log(`      ${warn}`));
    if (unexpectedWarnings.length > 5) {
      console.log(`      ... and ${unexpectedWarnings.length - 5} more`);
    }
  }
}

/**
 * Print Phase 4 results
 */
function printPhase4(phase4, score) {
  console.log('\n🔗 PHASE 4: CROSS-LAYER CONSISTENCY');
  console.log('-'.repeat(80));
  
  // Count breakdown
  console.log(`   CSV Rows: ${phase4.csv_count || 'N/A'}`);
  console.log(`   JSON Products: ${phase4.json_count}`);
  console.log(`   Mapping Entries: ${phase4.mapping_count}`);
  console.log(`   Contract Products: ${phase4.contract_count}`);
  
  // Count consistency
  const allCounts = [phase4.csv_count, phase4.json_count, phase4.mapping_count, phase4.contract_count]
    .filter(c => c > 0);
  
  if (allCounts.length > 1) {
    console.log(`   Count Consistency: ${phase4.count_consistency ? '✅ ALL MATCH' : '❌ MISMATCH'}`);
  } else {
    console.log(`   Count Consistency: ⚠️ INSUFFICIENT DATA`);
  }
  
  // Traceability
  if (phase4.traceability_expected > 0) {
    const tracePercent = Math.round((phase4.traceability_coverage / phase4.traceability_expected) * 100);
    console.log(`   End-to-End Traceability: ${phase4.traceability_coverage}/${phase4.traceability_expected} (${tracePercent}%)`);
  } else {
    console.log(`   End-to-End Traceability: ⚠️ NOT CHECKED (CSV not provided)`);
  }
  
  console.log(`\n   Score: ${score.toFixed(1)}/10 ${score >= 7 ? '✅' : '❌'}`);
  
  // Print errors
  if (phase4.errors.length > 0) {
    console.log(`\n   ❌ Errors: ${phase4.errors.length}`);
    phase4.errors.slice(0, 3).forEach(err => console.log(`      ${err}`));
    if (phase4.errors.length > 3) {
      console.log(`      ... and ${phase4.errors.length - 3} more`);
    }
  }
  
  // Print warnings (filter expected ones)
  const unexpectedWarnings = phase4.warnings.filter(w => !isExpectedWarning(w));
  if (unexpectedWarnings.length > 0) {
    console.log(`\n   ⚠️ Warnings: ${unexpectedWarnings.length}`);
    unexpectedWarnings.slice(0, 3).forEach(warn => console.log(`      ${warn}`));
    if (unexpectedWarnings.length > 3) {
      console.log(`      ... and ${unexpectedWarnings.length - 3} more`);
    }
  }
}

/**
 * Print Phase 5 results
 */
function printPhase5(phase5, score) {
  console.log('\n🧩 PHASE 5: COMPONENT INTEGRATION');
  console.log('-'.repeat(80));
  
  // Registry connection status
  if (phase5.registry_connected) {
    console.log(`   Registry Connected: ✅ YES`);
    console.log(`   Registry Address: ${phase5.registry_address}`);
  } else {
    console.log(`   Registry Connected: ❌ NO (ZeroAddress)`);
  }
  
  // Component statistics
  console.log(`   Unique Components: ${phase5.unique_components.length}`);
  
  if (phase5.unique_components.length > 0) {
    console.log(`   Components in Registry: ${phase5.components_exist_count}/${phase5.unique_components.length}`);
    
    if (phase5.components_missing_count > 0) {
      console.log(`   ❌ Missing Components: ${phase5.components_missing_count}`);
    }
    
    // Mapping validity
    if (phase5.components_exist_count > 0) {
      console.log(`   Valid Mappings: ${phase5.components_mapping_valid}/${phase5.components_exist_count}`);
      console.log(`   Active Components: ${phase5.components_active_count}/${phase5.components_exist_count}`);
      console.log(`   Creator Match: ${phase5.components_creator_match}/${phase5.components_exist_count}`);
    }
  }
  
  // Action 444 compatibility
  console.log(`\n   🎯 Action 444 Compatible: ${phase5.action444_compatible ? '✅ YES' : '❌ NO'}`);
  
  if (phase5.critical_blockers && phase5.critical_blockers.length > 0) {
    console.log(`\n   🚫 Critical Blockers: ${phase5.critical_blockers.length}`);
    phase5.critical_blockers.slice(0, 3).forEach(blocker => {
      console.log(`      • ${blocker}`);
    });
    if (phase5.critical_blockers.length > 3) {
      console.log(`      ... and ${phase5.critical_blockers.length - 3} more`);
    }
  }
  
  console.log(`\n   Score: ${score.toFixed(1)}/10 ${score >= 7 ? '✅' : '❌'}`);
  
  // Print errors
  if (phase5.errors.length > 0) {
    console.log(`\n   ❌ Errors: ${phase5.errors.length}`);
    phase5.errors.slice(0, 5).forEach(err => console.log(`      ${err}`));
    if (phase5.errors.length > 5) {
      console.log(`      ... and ${phase5.errors.length - 5} more`);
    }
  }
  
  // Print warnings (filter expected ones)
  const unexpectedWarnings = phase5.warnings.filter(w => !isExpectedWarning(w));
  if (unexpectedWarnings.length > 0) {
    console.log(`\n   ⚠️ Warnings: ${unexpectedWarnings.length}`);
    unexpectedWarnings.slice(0, 3).forEach(warn => console.log(`      ${warn}`));
    if (unexpectedWarnings.length > 3) {
      console.log(`      ... and ${unexpectedWarnings.length - 3} more`);
    }
  }
}

/**
 * Print complete validation report
 */
function printReport(validation) {
  console.log('\n' + '='.repeat(80));
  console.log('🧪 CATALOG PIPELINE VALIDATION REPORT');
  console.log('='.repeat(80));
  console.log(`📦 Seller: ${validation.context.seller}`);
  console.log(`🌐 Network: ${validation.context.network}`);
  console.log(`📅 Validated: ${validation.context.timestamp}`);
  console.log('='.repeat(80));
  
  // Phase 1: CSV + File System
  printPhase1(validation.phase1_csv_filesystem, validation.scores.phase1);
  
  // Phase 2: Arweave
  printPhase2(validation.phase2_arweave, validation.scores.phase2);
  
  // Phase 3: Contract
  printPhase3(validation.phase3_contract, validation.scores.phase3);
  
  // Phase 4: Consistency
  printPhase4(validation.phase4_consistency, validation.scores.phase4);
  
  // Phase 5: Component Integration
  printPhase5(validation.phase5_components, validation.scores.phase5);
  
  // Phase 6: Image Validation (if enabled)
  if (validation.phase6_images) {
    printPhase6(validation.phase6_images, validation.scores.phase6);
  }
  
  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('📊 VALIDATION SUMMARY');
  console.log('='.repeat(80));
  console.log(`   Quality Score: ${validation.quality_score.toFixed(1)}/10 ${validation.quality_score >= PASS_THRESHOLD ? '✅ PASS' : '❌ FAIL'}`);
  console.log(`   Execution Time: ${validation.execution_time_ms}ms`);
  console.log(`   Overall Status: ${validation.overall_status}`);
  console.log('='.repeat(80));
  
  // Recommendations
  if (validation.overall_status === 'FAIL') {
    console.log('\n⚠️ VALIDATION FAILED');
    console.log('Critical issues must be fixed before production deployment.');
  } else if (validation.quality_score < 9.0) {
    console.log('\n⚠️ VALIDATION PASSED WITH WARNINGS');
    console.log('Some non-critical issues detected. Review warnings above.');
  } else {
    console.log('\n✅ VALIDATION PASSED');
    console.log('Catalog pipeline verified across all layers.');
  }
  console.log('='.repeat(80) + '\n');
}

// ====================================================================
// 🎯 MAIN VALIDATION FUNCTION
// ====================================================================

/**
 * Main validation function
 * @param {Object} options - Validation options
 * @returns {Promise<Object>} - Complete validation report
 */
async function validateCatalogPipeline(options = {}) {
  const startTime = Date.now();
  
  // 1. Build context from options
  const context = buildContext(options);
  
  if (!options.json) {
    console.log('\n🔍 Starting catalog pipeline validation...');
    console.log(`📦 Seller: ${context.sellerId}`);
    console.log(`🌐 Network: ${context.network}`);
    console.log(`📁 Products: ${context.productsDir}`);
  }
  
  // 2. Run validation phases
  const phase1 = await validatePhase1_CSV_FileSystem(context);
  context.phase1Results = phase1;
  
  const phase2 = await validatePhase2_ArweaveLayer(context);
  context.phase2Results = phase2;
  
  const phase3 = await validatePhase3_ContractLayer(context);
  context.phase3Results = phase3;
  
  const phase4 = await validatePhase4_ConsistencyLayer(context);
  context.phase4Results = phase4;
  
  const phase5 = await validatePhase5_ComponentIntegration(context);
  context.phase5Results = phase5;
  
  // Phase 6: Image Validation (if --check-images flag is set)
  let phase6 = null;
  if (options.checkImages) {
    phase6 = await validatePhase6_ImageValidation(context);
    context.phase6Results = phase6;
  }
  
  // 3. Calculate scores
  const scores = {
    phase1: calculatePhase1Score(phase1),
    phase2: calculatePhase2Score(phase2),
    phase3: calculatePhase3Score(phase3),
    phase4: calculatePhase4Score(phase4),
    phase5: calculatePhase5Score(phase5),
    ...(phase6 ? { phase6: phase6.score } : {})
  };
  
  const qualityScore = calculateQualityScore(scores);
  
  // 4. Aggregate errors and warnings
  const allErrors = [
    ...phase1.errors,
    ...phase2.errors,
    ...phase3.errors,
    ...phase4.errors,
    ...phase5.errors,
    ...(phase6 ? phase6.errors || [] : [])
  ];
  
  const allWarnings = [
    ...phase1.warnings,
    ...phase2.warnings,
    ...phase3.warnings,
    ...phase4.warnings,
    ...phase5.warnings,
    ...(phase6 ? phase6.warnings || [] : [])
  ].filter(w => !isExpectedWarning(w)); // Filter expected warnings
  
  // 5. Build validation report
  const validation = {
    context: {
      seller: context.sellerId,
      network: context.network,
      timestamp: new Date().toISOString()
    },
    phase1_csv_filesystem: phase1,
    phase2_arweave: phase2,
    phase3_contract: phase3,
    phase4_consistency: phase4,
    phase5_components: phase5,
    ...(phase6 ? { phase6_images: phase6 } : {}),
    scores: scores,
    quality_score: qualityScore,
    total_errors: allErrors.length,
    total_warnings: allWarnings.length,
    execution_time_ms: Date.now() - startTime,
    overall_status: qualityScore >= PASS_THRESHOLD ? 'PASS' : 'FAIL'
  };
  
  // 6. Print report (if not --json mode)
  if (!options.json) {
    printReport(validation);
  }
  
  return validation;
}

// ====================================================================
// 🖥️ CLI INTERFACE
// ====================================================================

if (require.main === module) {
  program
    .option('--seller <id>', 'Seller business ID', process.env.SELLER_BUSINESS_ID || 'iveta')
    .option('--network <name>', 'Network name', 'localhost')
    .option('--csv <path>', 'CSV file path (optional, auto-resolves from seller)')
    .option('--check-images', 'Validate image files existence', false)
    .option('--full-arweave-check', 'Check all CIDs (slower)', false)
    .option('--json', 'Output JSON only (no formatted report)', false)
    .parse();

  const options = program.opts();
  
  validateCatalogPipeline(options)
    .then(result => {
      if (options.json) {
        console.log(JSON.stringify(result, null, 2));
      }
      
      // Exit with appropriate code
      process.exit(result.overall_status === 'PASS' ? 0 : 1);
    })
    .catch(error => {
      console.error(`\n❌ Validation failed: ${error.message}`);
      if (error.stack) {
        console.error(error.stack);
      }
      process.exit(1);
    });
}

// ====================================================================
// 📦 MODULE EXPORT
// ====================================================================

module.exports = {
  validateCatalogPipeline,
  validatePhase1_CSV_FileSystem,
  validatePhase2_ArweaveLayer,
  validatePhase3_ContractLayer,
  validatePhase4_ConsistencyLayer,
  validatePhase5_ComponentIntegration,
  calculatePhase1Score,
  calculateQualityScore,
  buildContext
};

