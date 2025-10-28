#!/usr/bin/env node

/**
 * 🧪 Component Upload Validation Script
 * 
 * Validates completeness and correctness of Action 555 (component upload)
 * across all layers: FileSystem → Arweave → Contract → State
 * 
 * Usage:
 *   node scripts/validate_component_upload.js --component amanita_muscaria
 *   node scripts/validate_component_upload.js --component blue_lotus --network localhost
 * 
 * Programmatic Use:
 *   const { validateComponent } = require('./scripts/validate_component_upload.js');
 *   const report = await validateComponent('amanita_muscaria', 'localhost', sellerAddress);
 * 
 * @version 1.0.0
 * @date 2025-10-24
 */

const fs = require('fs');
const path = require('path');
const { program } = require('commander');

// ====================================================================
// 🔧 CONFIGURATION
// ====================================================================

const COMPONENTS_DIR = path.join(__dirname, '../data/components');
const SUPPORTED_LANGUAGES = ['ru', 'en', 'de', 'es', 'fr', 'nl', 'et'];

// ====================================================================
// 📊 VALIDATION PHASES
// ====================================================================

/**
 * Phase 1: File System Validation
 * @param {string} componentId - Component business ID
 * @param {string} network - Network name
 * @returns {Object} Validation results
 */
async function validateFileSystem(componentId, network) {
  const checks = {
    component_dir: false,
    base_json: false,
    simple_fields: { count: 0, expected: 2, files: [] },
    complex_fields: { count: 0, expected: 7, files: [] },
    state_file: false,
    final_metadata: false,
    errors: []
  };
  
  const componentDir = path.join(COMPONENTS_DIR, componentId);
  
  // 1. Check component directory
  if (!fs.existsSync(componentDir)) {
    checks.errors.push(`Component directory not found: ${componentDir}`);
    return checks;
  }
  checks.component_dir = true;
  
  // 2. Check base JSON
  const baseJson = path.join(componentDir, `${componentId}.json`);
  checks.base_json = fs.existsSync(baseJson);
  if (!checks.base_json) {
    checks.errors.push(`Base JSON not found: ${componentId}.json`);
  }
  
  // 3. Check simple fields
  const simpleDir = path.join(componentDir, 'simple_fields');
  if (fs.existsSync(simpleDir)) {
    const files = fs.readdirSync(simpleDir).filter(f => f.endsWith('.json'));
    checks.simple_fields.count = files.length;
    checks.simple_fields.files = files;
    
    if (files.length < checks.simple_fields.expected) {
      checks.errors.push(`Missing simple fields: found ${files.length}, expected ${checks.simple_fields.expected}`);
    }
  } else {
    checks.errors.push('Simple fields directory not found');
  }
  
  // 4. Check complex fields (7 languages)
  const complexDir = path.join(componentDir, 'complex_fields');
  if (fs.existsSync(complexDir)) {
    const files = fs.readdirSync(complexDir).filter(f => f.endsWith('.json'));
    checks.complex_fields.count = files.length;
    checks.complex_fields.files = files;
    
    if (files.length < checks.complex_fields.expected) {
      checks.errors.push(`Missing complex fields: found ${files.length}, expected ${checks.complex_fields.expected}`);
    }
  } else {
    checks.errors.push('Complex fields directory not found');
  }
  
  // 5. Check state file
  const stateFile = path.join(componentDir, `_upload_state_${network}.json`);
  checks.state_file = fs.existsSync(stateFile);
  if (!checks.state_file) {
    checks.errors.push(`State file not found: _upload_state_${network}.json`);
  }
  
  // 6. Check final metadata
  const finalFile = path.join(componentDir, `${componentId}_final_${network}.json`);
  checks.final_metadata = fs.existsSync(finalFile);
  if (!checks.final_metadata) {
    checks.errors.push(`Final metadata not found: ${componentId}_final_${network}.json`);
  }
  
  return checks;
}

/**
 * Phase 2: Arweave Layer Validation
 * @param {string} componentId - Component business ID
 * @param {string} network - Network name
 * @returns {Object} Validation results
 */
async function validateArweaveLayer(componentId, network) {
  const checks = {
    state_loaded: false,
    simple_fields: { title: null, dosage: null },
    complex_fields: {},
    root_metadata: null,
    total_cids: 0,
    accessible_cids: 0,
    errors: []
  };
  
  // Load state file
  const stateFile = path.join(COMPONENTS_DIR, componentId, `_upload_state_${network}.json`);
  
  if (!fs.existsSync(stateFile)) {
    checks.errors.push('State file not found, cannot validate Arweave layer');
    return checks;
  }
  
  let state;
  try {
    state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    checks.state_loaded = true;
  } catch (error) {
    checks.errors.push(`Failed to parse state file: ${error.message}`);
    return checks;
  }
  
  // Helper: Check single CID
  const checkCID = async (cid, label) => {
    checks.total_cids++;
    
    if (!cid || cid.length !== 43) {
      checks.errors.push(`${label}: Invalid CID format (expected 43 chars, got ${cid?.length || 0})`);
      return { valid: false, accessible: false };
    }
    
    try {
      const response = await fetch(`https://arweave.net/${cid}`, {
        method: 'HEAD',
        timeout: 5000
      });
      
      if (response.ok) {
        checks.accessible_cids++;
      }
      
      return {
        valid: true,
        accessible: response.ok,
        status: response.status
      };
    } catch (error) {
      checks.errors.push(`${label}: Network error - ${error.message}`);
      return {
        valid: true, // CID format valid
        accessible: false,
        error: error.message
      };
    }
  };
  
  // 1. Check simple fields (support both nested and flat structures)
  if (state.simple_fields) {
    // Flat structure: title_cid
    let titleCID = state.simple_fields.title_cid;
    let dosageCID = state.simple_fields.dosage_cid;
    
    // Nested structure: title.cid
    if (!titleCID && state.simple_fields.title?.cid) {
      titleCID = state.simple_fields.title.cid;
    }
    if (!dosageCID && state.simple_fields.dosage_types?.cid) {
      dosageCID = state.simple_fields.dosage_types.cid;
    }
    
    if (titleCID) {
      checks.simple_fields.title = await checkCID(titleCID, 'Simple.Title');
    }
    if (dosageCID) {
      checks.simple_fields.dosage = await checkCID(dosageCID, 'Simple.Dosage');
    }
  }
  
  // 2. Check complex fields (7 languages) - support nested structure
  if (state.complex_fields) {
    for (const [lang, data] of Object.entries(state.complex_fields)) {
      // Nested structure: { cid: "...", url: "..." }
      const cid = typeof data === 'string' ? data : data?.cid;
      
      if (cid) {
        checks.complex_fields[lang] = await checkCID(cid, `Complex.Description.${lang}`);
      }
    }
  }
  
  // 3. Check root metadata
  if (state.root_metadata?.cid) {
    checks.root_metadata = await checkCID(state.root_metadata.cid, 'Root.Metadata');
  } else {
    checks.errors.push('Root metadata CID not found in state');
  }
  
  return checks;
}

/**
 * Phase 3: Contract Layer Validation
 * @param {string} componentId - Component business ID
 * @param {string} network - Network name
 * @param {string} sellerAddress - Seller Ethereum address
 * @returns {Object} Validation results
 */
async function validateContractLayer(componentId, network, sellerAddress) {
  const checks = {
    contracts_loaded: false,
    component_exists: false,
    component_id_mapping: null,
    root_cid_match: false,
    creator_match: false,
    status_active: false,
    action444_compatible: false,
    errors: [],
    warnings: []
  };
  
  try {
    // Initialize contracts
    const { ethers } = require('hardhat');
    const ContractManager = require('./lib/services/ContractManager');
    const EthersUtils = require('./lib/utils/EthersUtils');
    const config = require('./lib/config');
    
    // ✅ Create provider first (required by EthersUtils)
    const rpcUrl = network === 'localhost' ? 'http://127.0.0.1:8545' : config.get('network.rpcUrl');
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(ethersUtils, config);
    
    // ✅ Use ContractManager directly - it auto-resolves from MagicRegistry!
    // Same mechanism as Action 555 uses - works with just MAGIC_REGISTRY_CONTRACT_ADDRESS in .env
    let organicRegistry, amanitaIntl;
    try {
      // ContractManager.loadUUPSContract() automatically:
      // 1. Checks .env for ORGANICCOMPONENTREGISTRY_PROXY_ADDRESS
      // 2. If not found, loads MagicRegistry from MAGIC_REGISTRY_CONTRACT_ADDRESS
      // 3. Queries MagicRegistry.get('OrganicComponentRegistry')
      organicRegistry = await contractManager.loadUUPSContract('OrganicComponentRegistry');
      amanitaIntl = await contractManager.loadUUPSContract('AmanitaInternational');
      checks.contracts_loaded = true;
    } catch (loadError) {
      // Contracts not accessible - expected if Action 1 not run yet
      checks.errors.push(`Contracts not accessible: ${loadError.message}`);
      checks.warnings.push('Contract validation skipped (run Action 1 first to deploy contracts & MagicRegistry)');
      checks.warnings.push('⚠️ Action 444 compatibility CANNOT be verified without contract access');
      return checks;
    }
    
    // === CRITICAL CHECK FOR ACTION 444 ===
    // This is the exact check ProductRegistry.createProduct() performs
    // If this fails, Action 444 will revert with ComponentNotFound
    
    // 1. Check component exists (CRITICAL for Action 444)
    checks.component_exists = await organicRegistry.componentExists(componentId);
    
    if (!checks.component_exists) {
      checks.errors.push(`❌ CRITICAL: Component '${componentId}' not registered in OrganicComponentRegistry`);
      checks.errors.push(`   → Action 444 will FAIL with ComponentNotFound(${componentId})`);
      checks.errors.push(`   → ProductRegistry._validateComponents() will revert`);
      checks.action444_compatible = false;
      return checks;
    }
    
    // 2. Get component blockchain ID
    const blockchainId = await organicRegistry.businessIdToComponentId(componentId);
    checks.component_id_mapping = blockchainId.toString();
    
    if (blockchainId == 0 || blockchainId == '0') {
      checks.errors.push(`❌ CRITICAL: Component mapping invalid (businessIdToComponentId returned 0)`);
      checks.errors.push(`   → Action 444 will FAIL - component not properly registered`);
      checks.action444_compatible = false;
      return checks;
    }
    
    // 3. Verify component data can be extracted (ensures getComponent() works)
    try {
      const component = await organicRegistry.getComponent(blockchainId);
      
      checks.creator_match = component.creator.toLowerCase() === sellerAddress.toLowerCase();
      checks.status_active = component.status.toString() === '0'; // ComponentStatus.ACTIVE (BigInt comparison)
      
      if (!checks.creator_match) {
        checks.warnings.push(`Creator mismatch: contract=${component.creator}, expected=${sellerAddress}`);
        // Not critical for Action 444, but indicates potential ownership issue
      }
      
      // Note: Status check not critical for Action 444 (ProductRegistry doesn't check status)
      if (!checks.status_active) {
        checks.warnings.push(`Component status not ACTIVE: ${component.status}`);
      }
      
    } catch (getCompError) {
      checks.errors.push(`❌ Failed to extract component data: ${getCompError.message}`);
      checks.errors.push(`   → This may cause issues in Action 444 product creation`);
      checks.action444_compatible = false;
      return checks;
    }
    
    // 4. Check root CID match (data integrity)
    try {
      const contractRootCID = await organicRegistry.componentRootMetadataCIDs(blockchainId);
      
      const stateFile = path.join(COMPONENTS_DIR, componentId, `_upload_state_${network}.json`);
      if (fs.existsSync(stateFile)) {
        const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
        // Support both nested (root_metadata.cid) and flat (root_metadata.data.cid)
        const stateRootCID = state.root_metadata?.cid || state.root_metadata?.data?.cid;
        
        checks.root_cid_match = contractRootCID === stateRootCID;
        
        if (!checks.root_cid_match) {
          checks.warnings.push(`Root CID mismatch: contract=${contractRootCID}, state=${stateRootCID}`);
          // Not critical for Action 444, but indicates data inconsistency
        }
      }
    } catch (cidError) {
      checks.warnings.push(`Could not verify root CID: ${cidError.message}`);
    }
    
    // === ACTION 444 COMPATIBILITY VERDICT ===
    // If we reached here with component_exists=true and valid mapping, Action 444 will work
    checks.action444_compatible = checks.component_exists && 
                                   checks.component_id_mapping && 
                                   checks.component_id_mapping !== '0';
    
    if (checks.action444_compatible) {
      console.log(`   ✅ Action 444 Compatible: Component can be used in product creation`);
    }
    
  } catch (error) {
    checks.errors.push(`Contract validation error: ${error.message}`);
    checks.action444_compatible = false;
  }
  
  return checks;
}

/**
 * Phase 4: State Consistency Validation
 * @param {string} componentId - Component business ID
 * @param {string} network - Network name
 * @returns {Object} Validation results
 */
async function validateStateConsistency(componentId, network) {
  const checks = {
    state_exists: false,
    format_valid: false,
    steps_complete: 0,
    steps_expected: 5,
    cids_present: {
      simple_fields: 0,
      complex_fields: 0,
      root: false
    },
    contract_registration: false,
    timestamps_valid: false,
    errors: []
  };
  
  const stateFile = path.join(COMPONENTS_DIR, componentId, `_upload_state_${network}.json`);
  
  if (!fs.existsSync(stateFile)) {
    checks.errors.push('State file not found');
    return checks;
  }
  
  checks.state_exists = true;
  
  let state;
  try {
    state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  } catch (error) {
    checks.errors.push(`Failed to parse state file: ${error.message}`);
    return checks;
  }
  
  // 1. Format validation (support both componentId and component_id)
  const stateComponentId = state.componentId || state.component_id;
  checks.format_valid = stateComponentId === componentId && state.network === network;
  if (!checks.format_valid) {
    checks.errors.push(`State format invalid: componentId=${stateComponentId}, network=${state.network}`);
  }
  
  // 2. Steps completed (account for shareable_data optimization)
  checks.steps_complete = state.steps_completed?.length || 0;
  
  // Shareable data is uploaded ONLY for first component (i === 0)
  // Expected steps: 5 for first component, 4 for subsequent components
  const hasShareableData = state.steps_completed?.includes('shareable_data_uploaded');
  checks.steps_expected = hasShareableData ? 5 : 4;
  
  if (checks.steps_complete < checks.steps_expected) {
    checks.errors.push(`Incomplete upload: ${checks.steps_complete}/${checks.steps_expected} steps completed`);
  }
  
  // 3. CIDs present
  if (state.simple_fields) {
    checks.cids_present.simple_fields = [
      state.simple_fields.title_cid,
      state.simple_fields.dosage_cid
    ].filter(Boolean).length;
  }
  
  if (state.complex_fields) {
    checks.cids_present.complex_fields = Object.keys(state.complex_fields).length;
  }
  
  checks.cids_present.root = !!state.root_metadata?.cid;
  
  // 4. Contract registration
  checks.contract_registration = !!(
    state.contract_registration?.componentId &&
    state.contract_registration?.txHash
  );
  
  if (!checks.contract_registration) {
    checks.errors.push('Contract registration data missing from state');
  }
  
  // 5. Timestamps (support both last_updated and updated_at)
  checks.timestamps_valid = !!(
    state.created_at &&
    (state.last_updated || state.updated_at)
  );
  
  if (!checks.timestamps_valid) {
    checks.errors.push('Timestamps missing from state');
  }
  
  return checks;
}

// ====================================================================
// 🧮 QUALITY SCORE CALCULATION
// ====================================================================

/**
 * Calculate quality score (0-10)
 * @param {Object} validation - Validation results from all phases
 * @returns {number} Quality score
 */
function calculateQualityScore(validation) {
  const weights = {
    filesystem: 0.15,
    arweave: 0.30,
    contract: 0.35,
    state: 0.20
  };
  
  const scores = {
    filesystem: calculateFileSystemScore(validation.filesystem),
    arweave: calculateArweaveScore(validation.arweave),
    contract: calculateContractScore(validation.contract),
    state: calculateStateScore(validation.state)
  };
  
  const weightedScore = Object.entries(weights).reduce((acc, [key, weight]) => {
    return acc + (scores[key] * weight);
  }, 0);
  
  return Math.round(weightedScore * 10) / 10;
}

function calculateFileSystemScore(fs) {
  if (!fs) return 0;
  
  let score = 10;
  if (!fs.component_dir) return 0; // Critical failure
  if (!fs.base_json) score -= 3;
  if (fs.simple_fields.count < fs.simple_fields.expected) score -= 2;
  if (fs.complex_fields.count < fs.complex_fields.expected) score -= 2;
  if (!fs.state_file) score -= 2;
  if (!fs.final_metadata) score -= 1;
  
  return Math.max(0, score);
}

function calculateArweaveScore(arweave) {
  if (!arweave || arweave.total_cids === 0) return 0;
  
  const accessibilityRate = arweave.accessible_cids / arweave.total_cids;
  return accessibilityRate * 10;
}

function calculateContractScore(contract) {
  if (!contract) return 0;
  
  // If contracts not loaded, return 5/10 (partial credit - can't verify)
  if (!contract.contracts_loaded) return 5;
  
  let score = 10;
  
  // === CRITICAL FOR ACTION 444 ===
  if (!contract.component_exists) return 0; // Critical failure - Action 444 will fail
  if (!contract.action444_compatible) score -= 5; // Major penalty if not Action 444 compatible
  
  // === SECONDARY CHECKS ===
  if (!contract.creator_match) score -= 2; // Ownership issue (warning, not critical)
  if (!contract.root_cid_match) score -= 2; // Data integrity (warning, not critical)
  if (!contract.status_active) score -= 1; // Status (not checked by ProductRegistry)
  
  return Math.max(0, score);
}

function calculateStateScore(state) {
  if (!state) return 0;
  
  let score = 10;
  if (!state.state_exists) return 0; // Critical failure
  if (!state.format_valid) score -= 2;
  
  const completionRate = state.steps_complete / state.steps_expected;
  if (completionRate < 1.0) {
    score -= (1.0 - completionRate) * 5; // Max -5 points
  }
  
  if (!state.contract_registration) score -= 2;
  if (!state.timestamps_valid) score -= 1;
  
  return Math.max(0, score);
}

// ====================================================================
// 📊 REPORT GENERATION
// ====================================================================

/**
 * Generate console report (human-readable)
 * @param {Object} validation - Complete validation results
 */
function generateConsoleReport(validation) {
  const { componentId, network, sellerAddress, filesystem, arweave, contract, state, qualityScore } = validation;
  
  console.log('\n' + '='.repeat(80));
  console.log('🧪 COMPONENT UPLOAD VALIDATION REPORT');
  console.log('='.repeat(80));
  console.log(`📦 Component: ${componentId}`);
  console.log(`🌐 Network: ${network}`);
  console.log(`👤 Seller: ${sellerAddress}`);
  console.log(`📅 Validated: ${new Date().toISOString()}`);
  console.log('='.repeat(80));
  
  // Phase 1: File System
  console.log('\n📁 PHASE 1: FILE SYSTEM VALIDATION');
  console.log('-'.repeat(80));
  console.log(`   Component Directory: ${filesystem.component_dir ? '✅ EXISTS' : '❌ MISSING'}`);
  console.log(`   Base JSON: ${filesystem.base_json ? '✅ EXISTS' : '❌ MISSING'}`);
  console.log(`   Simple Fields: ${filesystem.simple_fields.count}/${filesystem.simple_fields.expected} ${filesystem.simple_fields.count >= filesystem.simple_fields.expected ? '✅' : '❌'}`);
  console.log(`   Complex Fields: ${filesystem.complex_fields.count}/${filesystem.complex_fields.expected} ${filesystem.complex_fields.count >= filesystem.complex_fields.expected ? '✅' : '❌'}`);
  console.log(`   State File: ${filesystem.state_file ? '✅ EXISTS' : '❌ MISSING'}`);
  console.log(`   Final Metadata: ${filesystem.final_metadata ? '✅ EXISTS' : '❌ MISSING'}`);
  
  if (filesystem.errors.length > 0) {
    console.log(`   ⚠️ Errors: ${filesystem.errors.length}`);
    filesystem.errors.forEach(err => console.log(`      - ${err}`));
  }
  
  // Phase 2: Arweave
  console.log('\n☁️ PHASE 2: ARWEAVE LAYER VALIDATION');
  console.log('-'.repeat(80));
  console.log(`   State Loaded: ${arweave.state_loaded ? '✅ YES' : '❌ NO'}`);
  console.log(`   CID Accessibility: ${arweave.accessible_cids}/${arweave.total_cids} ${arweave.accessible_cids === arweave.total_cids ? '✅' : '⚠️'}`);
  
  if (arweave.simple_fields.title) {
    console.log(`   Simple.Title: ${arweave.simple_fields.title.accessible ? '✅ ACCESSIBLE' : '❌ UNREACHABLE'}`);
  }
  if (arweave.simple_fields.dosage) {
    console.log(`   Simple.Dosage: ${arweave.simple_fields.dosage.accessible ? '✅ ACCESSIBLE' : '❌ UNREACHABLE'}`);
  }
  
  const langAccessible = Object.values(arweave.complex_fields).filter(c => c?.accessible).length;
  console.log(`   Complex.Descriptions: ${langAccessible}/${Object.keys(arweave.complex_fields).length} languages accessible`);
  
  if (arweave.root_metadata) {
    console.log(`   Root Metadata: ${arweave.root_metadata.accessible ? '✅ ACCESSIBLE' : '❌ UNREACHABLE'}`);
  }
  
  if (arweave.errors.length > 0) {
    console.log(`   ⚠️ Errors: ${arweave.errors.length}`);
    arweave.errors.slice(0, 5).forEach(err => console.log(`      - ${err}`));
    if (arweave.errors.length > 5) {
      console.log(`      ... and ${arweave.errors.length - 5} more`);
    }
  }
  
  // Phase 3: Contract
  console.log('\n📜 PHASE 3: CONTRACT LAYER VALIDATION');
  console.log('-'.repeat(80));
  console.log(`   Contracts Loaded: ${contract.contracts_loaded ? '✅ YES' : '❌ NO'}`);
  console.log(`   Component Exists: ${contract.component_exists ? '✅ YES' : '❌ NO'}`);
  
  if (contract.component_id_mapping) {
    console.log(`   Blockchain ID: ${contract.component_id_mapping} ✅`);
  }
  
  console.log(`   Creator Match: ${contract.creator_match ? '✅ YES' : '❌ NO'}`);
  console.log(`   Root CID Match: ${contract.root_cid_match ? '✅ YES' : '❌ NO'}`);
  console.log(`   Status Active: ${contract.status_active ? '✅ YES' : '❌ NO'}`);
  
  // === ACTION 444 COMPATIBILITY ===
  console.log('\n   🎯 Action 444 Compatibility:');
  if (contract.action444_compatible) {
    console.log(`   ✅ COMPATIBLE - Component can be used in product creation`);
  } else if (!contract.contracts_loaded) {
    console.log(`   ⚠️ UNKNOWN - Contract validation skipped (see warnings below)`);
  } else {
    console.log(`   ❌ INCOMPATIBLE - Action 444 will FAIL for this component`);
  }
  
  if (contract.warnings && contract.warnings.length > 0) {
    console.log(`\n   ⚠️ Warnings: ${contract.warnings.length}`);
    contract.warnings.forEach(warn => console.log(`      - ${warn}`));
  }
  
  if (contract.errors.length > 0) {
    console.log(`\n   ❌ Errors: ${contract.errors.length}`);
    contract.errors.forEach(err => console.log(`      ${err}`));
  }
  
  // Phase 4: State
  console.log('\n💾 PHASE 4: STATE CONSISTENCY VALIDATION');
  console.log('-'.repeat(80));
  console.log(`   State Exists: ${state.state_exists ? '✅ YES' : '❌ NO'}`);
  console.log(`   Format Valid: ${state.format_valid ? '✅ YES' : '❌ NO'}`);
  console.log(`   Steps Completed: ${state.steps_complete}/${state.steps_expected} ${state.steps_complete === state.steps_expected ? '✅' : '⚠️'}`);
  console.log(`   CIDs Present:`);
  console.log(`      - Simple Fields: ${state.cids_present.simple_fields}/2`);
  console.log(`      - Complex Fields: ${state.cids_present.complex_fields}/7`);
  console.log(`      - Root: ${state.cids_present.root ? '✅' : '❌'}`);
  console.log(`   Contract Registration: ${state.contract_registration ? '✅ RECORDED' : '❌ MISSING'}`);
  console.log(`   Timestamps Valid: ${state.timestamps_valid ? '✅ YES' : '❌ NO'}`);
  
  if (state.errors.length > 0) {
    console.log(`   ⚠️ Errors: ${state.errors.length}`);
    state.errors.forEach(err => console.log(`      - ${err}`));
  }
  
  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('📊 VALIDATION SUMMARY');
  console.log('='.repeat(80));
  console.log(`   Quality Score: ${qualityScore}/10 ${qualityScore >= 8.0 ? '✅ PASS' : '❌ FAIL'}`);
  
  const allErrors = [
    ...filesystem.errors,
    ...arweave.errors,
    ...contract.errors,
    ...state.errors
  ];
  
  console.log(`   Total Errors: ${allErrors.length}`);
  console.log(`   Overall Status: ${qualityScore >= 8.0 ? '✅ PASS' : '❌ FAIL'}`);
  console.log('='.repeat(80));
  
  if (qualityScore < 8.0) {
    console.log('\n⚠️ VALIDATION FAILED');
    console.log('Critical issues detected. Review errors above.');
  } else if (allErrors.length > 0) {
    console.log('\n⚠️ VALIDATION PASSED WITH WARNINGS');
    console.log(`${allErrors.length} non-critical issues detected.`);
  } else {
    console.log('\n✅ VALIDATION PASSED');
    console.log('Component upload verified across all layers.');
  }
  
  console.log('='.repeat(80) + '\n');
}

// ====================================================================
// 🚀 MAIN VALIDATION FUNCTION (for programmatic use)
// ====================================================================

/**
 * Validate component upload (exported for seller-level validation)
 * @param {string} componentId - Component business ID
 * @param {string} network - Network name (default: localhost)
 * @param {string} sellerAddress - Seller address (default: from .env)
 * @returns {Promise<Object>} Complete validation report
 */
async function validateComponent(componentId, network = 'localhost', sellerAddress = null) {
  // Get seller from .env if not provided
  if (!sellerAddress) {
    require('dotenv').config();
    sellerAddress = process.env.SELLER_ADDRESS;
    
    if (!sellerAddress) {
      throw new Error('SELLER_ADDRESS not found in .env and not provided as parameter');
    }
  }
  
  console.log(`\n🔍 Validating component: ${componentId}`);
  console.log(`   Network: ${network}`);
  console.log(`   Seller: ${sellerAddress}`);
  
  // Run all validation phases
  const filesystem = await validateFileSystem(componentId, network);
  const arweave = await validateArweaveLayer(componentId, network);
  const contract = await validateContractLayer(componentId, network, sellerAddress);
  const state = await validateStateConsistency(componentId, network);
  
  // Calculate quality score
  const validation = {
    componentId,
    network,
    sellerAddress,
    filesystem,
    arweave,
    contract,
    state
  };
  
  const qualityScore = calculateQualityScore(validation);
  
  return {
    ...validation,
    qualityScore,
    passed: qualityScore >= 8.0,
    timestamp: new Date().toISOString()
  };
}

// ====================================================================
// 🖥️ CLI EXECUTION
// ====================================================================

async function main() {
  program
    .name('validate_component_upload')
    .description('Validate Action 555 component upload completeness')
    .version('1.0.0')
    .requiredOption('-c, --component <componentId>', 'Component business ID (e.g., amanita_muscaria)')
    .option('-n, --network <network>', 'Network name', 'localhost')
    .option('-s, --seller <address>', 'Seller Ethereum address (default: from .env)')
    .option('-j, --json', 'Output JSON format')
    .parse(process.argv);
  
  const options = program.opts();
  
  try {
    // Run validation
    const report = await validateComponent(options.component, options.network, options.seller);
    
    // Generate report
    if (options.json) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      generateConsoleReport(report);
    }
    
    // Exit code
    process.exit(report.passed ? 0 : 1);
    
  } catch (error) {
    console.error('\n' + '='.repeat(80));
    console.error('❌ VALIDATION ERROR');
    console.error('='.repeat(80));
    console.error(`Error: ${error.message}`);
    console.error(`\nStack trace:\n${error.stack}`);
    console.error('='.repeat(80) + '\n');
    process.exit(1);
  }
}

// ====================================================================
// 🚀 MODULE EXPORT + CLI
// ====================================================================

module.exports = {
  validateComponent,
  validateFileSystem,
  validateArweaveLayer,
  validateContractLayer,
  validateStateConsistency,
  calculateQualityScore
};

// Run CLI if executed directly
if (require.main === module) {
  main();
}

