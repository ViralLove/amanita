#!/usr/bin/env node

/**
 * Manual Complex Fields Check Script
 * Quick validation of complex fields keys after Action 555
 * 
 * Usage:
 *   node scripts/validators/manual_complex_fields_check.js <component1> [component2] ...
 *   node scripts/validators/manual_complex_fields_check.js amanita_muscaria blue_lotus
 *   node scripts/validators/manual_complex_fields_check.js --network localhost amanita_muscaria blue_lotus
 * 
 * @version 1.0.0
 * @date 2025-01-12
 */

const { ethers } = require('hardhat');
const path = require('path');

// Import required modules
const ContractManager = require('../lib/services/ContractManager');
const EthersUtils = require('../lib/utils/EthersUtils');
const config = require('../lib/config');

// Supported languages for validation
const SUPPORTED_LANGUAGES = ['ru', 'en', 'de'];

/**
 * Check complex fields for given component IDs
 * @param {Array<string>} componentIds - Array of component biounit_ids
 * @param {string} network - Network name (default: 'localhost')
 * @returns {Promise<Object>} - Check results
 */
async function checkComplexFields(componentIds, network = 'localhost') {
  console.log('\n' + '='.repeat(80));
  console.log('🔍 MANUAL COMPLEX FIELDS CHECK');
  console.log('='.repeat(80));
  console.log(`📦 Components: ${componentIds.join(', ')}`);
  console.log(`🌐 Network: ${network}`);
  console.log('='.repeat(80) + '\n');

  const results = {};
  let contractsLoaded = false;
  let amanitaIntl = null;

  try {
    // Initialize contracts
    const rpcUrl = network === 'localhost' ? 'http://127.0.0.1:8545' : config.get('network.rpcUrl');
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(ethersUtils, config);

    try {
      amanitaIntl = await contractManager.loadUUPSContract('AmanitaInternational');
      contractsLoaded = true;
      console.log(`✅ AmanitaInternational contract loaded: ${await amanitaIntl.getAddress()}\n`);
    } catch (loadError) {
      console.error(`❌ Failed to load AmanitaInternational contract: ${loadError.message}`);
      console.error(`   → Make sure contracts are deployed (run Action 1 first)`);
      console.error(`   → Make sure Hardhat node is running (for localhost)`);
      console.error(`   → Check MAGIC_REGISTRY_CONTRACT_ADDRESS in .env\n`);
      throw loadError;
    }

    // Check complex fields for each component
    for (const componentId of componentIds) {
      const className = `ComponentDescription.${componentId}`;
      results[componentId] = {
        className,
        languages: {},
        allFound: false
      };

      console.log(`📦 ${componentId}:`);
      console.log(`   ClassName: ${className}`);

      let foundCount = 0;
      for (const lang of SUPPORTED_LANGUAGES) {
        try {
          const cid = await amanitaIntl.getComplexFieldCID(className, lang);
          const exists = cid && cid !== '' && cid !== ethers.ZeroAddress;

          results[componentId].languages[lang] = { cid, exists };
          foundCount += exists ? 1 : 0;

          const status = exists ? '✅' : '❌';
          const cidDisplay = exists ? cid : 'MISSING';
          console.log(`   ${lang}: ${status} ${cidDisplay}`);
        } catch (error) {
          results[componentId].languages[lang] = { cid: null, exists: false, error: error.message };
          console.log(`   ${lang}: ❌ ERROR - ${error.message}`);
        }
      }

      results[componentId].allFound = foundCount === SUPPORTED_LANGUAGES.length;
      console.log(`   Status: ${results[componentId].allFound ? '✅ ALL FOUND' : `⚠️ FOUND ${foundCount}/${SUPPORTED_LANGUAGES.length}`}\n`);
    }

    // Проверка уникальности
    if (componentIds.length >= 2) {
      console.log('🔑 Uniqueness Check:');
      console.log('-'.repeat(80));

      const cidsByLang = {};
      for (const componentId of componentIds) {
        for (const lang of SUPPORTED_LANGUAGES) {
          if (!cidsByLang[lang]) cidsByLang[lang] = [];
          const langResult = results[componentId].languages[lang];
          if (langResult && langResult.exists && langResult.cid) {
            cidsByLang[lang].push({ componentId, cid: langResult.cid });
          }
        }
      }

      let allUnique = true;
      for (const lang of Object.keys(cidsByLang)) {
        const cids = cidsByLang[lang].map(item => item.cid);
        const uniqueSet = new Set(cids);
        const isUnique = uniqueSet.size === cids.length;

        if (!isUnique) {
          allUnique = false;
        }

        const status = isUnique ? '✅ UNIQUE' : '❌ DUPLICATES DETECTED';
        console.log(`   ${lang}: ${status}`);

        if (!isUnique) {
          // Find duplicates
          const duplicates = [];
          for (let i = 0; i < cidsByLang[lang].length; i++) {
            for (let j = i + 1; j < cidsByLang[lang].length; j++) {
              if (cidsByLang[lang][i].cid === cidsByLang[lang][j].cid) {
                duplicates.push({
                  cid: cidsByLang[lang][i].cid,
                  components: [cidsByLang[lang][i].componentId, cidsByLang[lang][j].componentId]
                });
              }
            }
          }
          duplicates.forEach(dup => {
            console.log(`      ⚠️ Same CID for: ${dup.components.join(', ')}`);
            console.log(`         CID: ${dup.cid}`);
          });
        }
      }

      console.log('\n' + '='.repeat(80));
      if (allUnique) {
        console.log('✅ UNIQUENESS VERIFIED: All keys are unique');
      } else {
        console.log('❌ UNIQUENESS VIOLATION: Some components have same CID!');
      }
      console.log('='.repeat(80) + '\n');
    } else {
      console.log('ℹ️  Uniqueness check skipped (need at least 2 components)\n');
    }

  } catch (error) {
    console.error('\n❌ Error during validation:');
    console.error(`   ${error.message}`);
    if (error.stack) {
      console.error('\nStack trace:');
      console.error(error.stack);
    }
    throw error;
  }

  return results;
}

// CLI parsing
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    network: 'localhost',
    componentIds: []
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--network' && i + 1 < args.length) {
      options.network = args[i + 1];
      i++;
    } else if (!args[i].startsWith('--')) {
      options.componentIds.push(args[i]);
    }
  }

  return options;
}

// Main execution
async function main() {
  const options = parseArgs();

  if (options.componentIds.length === 0) {
    console.error('❌ Error: No component IDs provided');
    console.error('\nUsage:');
    console.error('  node scripts/validators/manual_complex_fields_check.js <component1> [component2] ...');
    console.error('  node scripts/validators/manual_complex_fields_check.js --network localhost amanita_muscaria blue_lotus');
    console.error('\nExamples:');
    console.error('  node scripts/validators/manual_complex_fields_check.js amanita_muscaria');
    console.error('  node scripts/validators/manual_complex_fields_check.js amanita_muscaria blue_lotus');
    console.error('  node scripts/validators/manual_complex_fields_check.js --network sepolia amanita_muscaria');
    process.exit(1);
  }

  try {
    await checkComplexFields(options.componentIds, options.network);
    console.log('✅ Check completed successfully\n');
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Check failed');
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for programmatic use
module.exports = { checkComplexFields };

