/**
 * Validate Product Mapping Files
 * Checks integrity of mapping files and CIDs
 * 
 * Usage:
 *   MAPPING_FILE="data/sellers/iveta/output/product_combined_mapping.json" node scripts/validate_product_mappings.js
 * 
 * @version 1.0.0
 * @date 2025-10-23
 */

const fs = require('fs');
const path = require('path');

function validateMappingFile(mappingPath) {
  console.log(`\n🔍 Validating: ${mappingPath}`);
  
  if (!fs.existsSync(mappingPath)) {
    console.error(`❌ File not found: ${mappingPath}`);
    return false;
  }
  
  try {
    const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
    const products = Object.keys(mapping);
    
    console.log(`   → Products: ${products.length}`);
    
    // ✅ FIX P0-1: Fail on empty mapping
    if (products.length === 0) {
      console.error(`❌ Empty mapping file (no products to validate)`);
      return false;
    }
    
    let validCount = 0;
    let invalidCount = 0;
    const invalidProducts = [];
    const warnings = [];
    
    for (const [productId, data] of Object.entries(mapping)) {
      const issues = [];
      
      // Check CID format
      const titleValid = isValidCID(data.title_cid);
      const productValid = isValidCID(data.product_cid);
      
      if (!titleValid) issues.push(`title_cid: ${data.title_cid} (invalid format)`);
      if (!productValid) issues.push(`product_cid: ${data.product_cid} (invalid format)`);
      
      // ✅ FIX P0-2: Check required fields
      const titleUrlValid = data.title_url && 
                            typeof data.title_url === 'string' &&
                            data.title_url.includes(data.title_cid);
      const productUrlValid = data.product_url && 
                              typeof data.product_url === 'string' &&
                              data.product_url.includes(data.product_cid);
      const languagesValid = Array.isArray(data.languages) && data.languages.length > 0;
      
      if (!titleUrlValid) issues.push(`title_url: ${data.title_url} (missing or doesn't match CID)`);
      if (!productUrlValid) issues.push(`product_url: ${data.product_url} (missing or doesn't match CID)`);
      if (!languagesValid) issues.push(`languages: ${JSON.stringify(data.languages)} (empty or not array)`);
      
      // ✅ FIX P1-2: Check for partial mapping
      const hasTitleCID = titleValid;
      const hasProductCID = productValid;
      
      if (hasTitleCID && !hasProductCID) {
        warnings.push(`${productId}: Has title_cid but missing product_cid (partial upload?)`);
      }
      
      if (!hasTitleCID && hasProductCID) {
        warnings.push(`${productId}: Has product_cid but missing title_cid (inconsistent!)`);
      }
      
      // Mark as valid or invalid
      if (issues.length === 0) {
        validCount++;
      } else {
        invalidCount++;
        invalidProducts.push({
          productId,
          issues
        });
      }
    }
    
    console.log(`   → Valid: ${validCount}`);
    console.log(`   → Invalid: ${invalidCount}`);
    
    if (warnings.length > 0) {
      console.log(`\n⚠️ Warnings (${warnings.length}):`);
      warnings.forEach(warning => console.log(`   • ${warning}`));
    }
    
    if (invalidProducts.length > 0) {
      console.log(`\n❌ Invalid products (${invalidProducts.length}):`);
      invalidProducts.forEach(({ productId, issues }) => {
        console.log(`   • ${productId}:`);
        issues.forEach(issue => console.log(`      - ${issue}`));
      });
    }
    
    if (invalidCount === 0) {
      console.log(`\n✅ All CIDs are valid!`);
    } else {
      console.log(`\n❌ Found ${invalidCount} invalid products`);
    }
    
    return invalidCount === 0;
    
  } catch (error) {
    console.error(`❌ Parse error: ${error.message}`);
    return false;
  }
}

function isValidCID(cid) {
  // Arweave TX ID = 43 characters, base64url format
  return cid && 
         typeof cid === 'string' && 
         cid.length === 43 && 
         /^[A-Za-z0-9_-]{43}$/.test(cid);
}

// Run validation
const mappingPath = process.env.MAPPING_FILE || 'data/sellers/iveta/output/product_combined_mapping.json';

console.log('='.repeat(70));
console.log('📊 PRODUCT MAPPING VALIDATION');
console.log('='.repeat(70));

const isValid = validateMappingFile(mappingPath);

console.log('\n' + '='.repeat(70));
if (isValid) {
  console.log('✅ VALIDATION PASSED');
} else {
  console.log('❌ VALIDATION FAILED');
}
console.log('='.repeat(70));

process.exit(isValid ? 0 : 1);

