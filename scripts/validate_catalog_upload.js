/**
 * 🔍 Catalog Upload Validation Script
 * 
 * Validates that all products from a seller's catalog are correctly registered
 * in the ProductRegistry contract and match the Arweave upload mapping.
 * 
 * Usage:
 *   MAPPING_FILE="data/sellers/iveta/output/product_combined_mapping.json" \
 *   npx hardhat run scripts/validate_catalog_upload.js --network localhost
 */

const path = require('path');
const fs = require('fs');
const ContractManager = require('./lib/services/ContractManager');
const logger = require('./lib/utils/Logger');

async function main() {
  const mappingPath = process.env.MAPPING_FILE || 'data/sellers/iveta/output/product_combined_mapping.json';
  const fullPath = path.resolve(mappingPath);
  
  if (!fs.existsSync(fullPath)) {
    console.error(`❌ Mapping file not found: ${fullPath}`);
    process.exit(1);
  }
  
  const mapping = JSON.parse(fs.readFileSync(fullPath, 'utf8'));
  
  console.log('\n' + '='.repeat(80));
  console.log('🔍 CATALOG UPLOAD VALIDATION');
  console.log('='.repeat(80));
  console.log(`📄 Mapping file: ${mappingPath}`);
  console.log(`📊 Total products in mapping: ${Object.keys(mapping).length}\n`);
  
  // Initialize ContractManager
  const { ethers } = require('hardhat');
  const contractManager = new ContractManager(ethers.provider, logger);
  await contractManager.initialize();
  
  const productRegistry = await contractManager.loadUUPSContract('ProductRegistry');
  
  console.log('✅ ProductRegistry loaded:', await productRegistry.getAddress());
  console.log('');
  
  const results = {
    total: Object.keys(mapping).length,
    found: 0,
    active: 0,
    notFound: [],
    inactive: [],
    errors: []
  };
  
  // Get total products in contract
  const totalProductsInContract = await productRegistry.getProductCount();
  console.log(`📊 Total products in contract: ${totalProductsInContract}\n`);
  
  console.log('🔍 Validating each product...\n');
  
  for (const [productId, data] of Object.entries(mapping)) {
    try {
      // Try to find product by metadata CID
      let found = false;
      
      for (let i = 1; i <= totalProductsInContract; i++) {
        try {
          const product = await productRegistry.getProduct(i);
          
          if (product.metadataCID === data.product_cid) {
            results.found++;
            console.log(`✅ ${productId}`);
            console.log(`   → Contract ID: ${i}`);
            console.log(`   → Active: ${product.active ? '✅ YES' : '❌ NO'}`);
            console.log(`   → Seller: ${product.seller}`);
            console.log(`   → Components: [${product.componentIds.map(id => id.toString()).join(', ')}]`);
            console.log(`   → Metadata CID: ${product.metadataCID}`);
            console.log('');
            
            if (product.active) {
              results.active++;
            } else {
              results.inactive.push({ productId, contractId: i });
            }
            
            found = true;
            break;
          }
        } catch (err) {
          // Product ID doesn't exist or error reading, skip
          if (!err.message.includes('Product does not exist')) {
            console.warn(`   ⚠️ Error reading contract product ${i}:`, err.message);
          }
        }
      }
      
      if (!found) {
        results.notFound.push(productId);
        console.log(`❌ ${productId}`);
        console.log(`   → Status: NOT FOUND in contract`);
        console.log(`   → Expected CID: ${data.product_cid}`);
        console.log('');
      }
    } catch (error) {
      console.error(`❌ ${productId}`);
      console.error(`   → Error:`, error.message);
      console.log('');
      results.errors.push({ productId, error: error.message });
    }
  }
  
  // Summary
  console.log('='.repeat(80));
  console.log('📊 VALIDATION SUMMARY');
  console.log('='.repeat(80));
  console.log(`Total products in mapping:     ${results.total}`);
  console.log(`Found in contract:             ${results.found} (${(results.found / results.total * 100).toFixed(1)}%)`);
  console.log(`Active in contract:            ${results.active} (${(results.active / results.total * 100).toFixed(1)}%)`);
  console.log(`Not found:                     ${results.notFound.length}`);
  console.log(`Inactive:                      ${results.inactive.length}`);
  console.log(`Errors:                        ${results.errors.length}`);
  console.log('');
  
  // Detailed failure reports
  if (results.notFound.length > 0) {
    console.log('❌ PRODUCTS NOT FOUND IN CONTRACT:');
    console.log('-'.repeat(80));
    results.notFound.forEach(id => console.log(`   - ${id}`));
    console.log('');
  }
  
  if (results.inactive.length > 0) {
    console.log('⚠️ PRODUCTS INACTIVE IN CONTRACT:');
    console.log('-'.repeat(80));
    results.inactive.forEach(({ productId, contractId }) => {
      console.log(`   - ${productId} (contract ID: ${contractId})`);
    });
    console.log('');
  }
  
  if (results.errors.length > 0) {
    console.log('⚠️ VALIDATION ERRORS:');
    console.log('-'.repeat(80));
    results.errors.forEach(({ productId, error }) => {
      console.log(`   - ${productId}: ${error}`);
    });
    console.log('');
  }
  
  // Exit status
  if (results.found === results.total && results.active === results.total && results.errors.length === 0) {
    console.log('✅ ALL PRODUCTS SUCCESSFULLY VALIDATED!');
    console.log('   → All products found in contract');
    console.log('   → All products are active');
    console.log('   → No errors detected');
    console.log('='.repeat(80));
    process.exit(0);
  } else {
    console.log('❌ VALIDATION FAILED!');
    if (results.found < results.total) {
      console.log(`   → ${results.total - results.found} products not found in contract`);
    }
    if (results.active < results.found) {
      console.log(`   → ${results.found - results.active} products are inactive`);
    }
    if (results.errors.length > 0) {
      console.log(`   → ${results.errors.length} validation errors`);
    }
    console.log('='.repeat(80));
    process.exit(1);
  }
}

main().catch(error => {
  console.error('\n❌ Validation script failed:', error);
  console.error('\nStack trace:');
  console.error(error.stack);
  process.exit(1);
});

