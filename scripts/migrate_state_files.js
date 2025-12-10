/**
 * Migration Script: Convert old state files to new network-agnostic structure
 * 
 * Old: _upload_state_localhost.json (flat structure)
 * New: _upload_state.json (arweave + deployments structure)
 * 
 * @version 1.0.0
 * @date 2025-12-02
 */

const fs = require('fs');
const path = require('path');

const COMPONENTS_DIR = path.join(__dirname, '../data/components');

/**
 * Migrate single component state file
 * @param {string} componentDir - Component directory path
 * @returns {boolean} - True if migrated, false if skipped
 */
function migrateStateFile(componentDir) {
  const component = path.basename(componentDir);
  const oldStateFile = path.join(componentDir, '_upload_state_localhost.json');
  const newStateFile = path.join(componentDir, '_upload_state.json');
  
  // Skip if new file already exists
  if (fs.existsSync(newStateFile)) {
    console.log(`⏭️  ${component}: Already migrated (${path.basename(newStateFile)} exists)`);
    return false;
  }
  
  // Skip if old file doesn't exist
  if (!fs.existsSync(oldStateFile)) {
    console.log(`⏭️  ${component}: No localhost state to migrate`);
    return false;
  }
  
  console.log(`🔄 Migrating: ${component}`);
  
  try {
    // 1. Read old state
    const oldState = JSON.parse(fs.readFileSync(oldStateFile, 'utf8'));
    
    // 2. Create backup
    const backupFile = path.join(componentDir, '_upload_state_localhost.backup.json');
    fs.copyFileSync(oldStateFile, backupFile);
    console.log(`   → Backup: ${path.basename(backupFile)}`);
    
    // 3. Convert structure
    const newState = {
      biounit_id: oldState.biounit_id || oldState.component_id || oldState.componentId || component,
      created_at: oldState.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString(),
      
      // ✅ Arweave section (network-agnostic)
      arweave: {
        steps_completed: oldState.steps_completed || [],
        simple_fields: oldState.simple_fields || {},
        complex_fields: oldState.complex_fields || {},
        shareable_data: oldState.shareable_data || {},
        root_metadata: oldState.root_metadata || {}
      },
      
      // ✅ Deployments section (per-network)
      deployments: {}
    };
    
    // 4. Migrate contract_registration → deployments.localhost
    if (oldState.contract_registration) {
      newState.deployments.localhost = {
        blockchain_id: (oldState.contract_registration.blockchain_id || oldState.contract_registration.componentId)?.toString(),
        txHash: oldState.contract_registration.txHash,
        blockNumber: oldState.contract_registration.blockNumber,
        registered_at: oldState.contract_registration.registered_at || oldState.updated_at
      };
      console.log(`   → Contract registration migrated to deployments.localhost`);
    }
    
    // 5. Save new state
    fs.writeFileSync(newStateFile, JSON.stringify(newState, null, 2), 'utf8');
    console.log(`   ✅ Created: ${path.basename(newStateFile)}`);
    
    // 6. Validate new file
    if (!fs.existsSync(newStateFile)) {
      throw new Error('New state file was not created');
    }
    
    const newStateContent = JSON.parse(fs.readFileSync(newStateFile, 'utf8'));
    if (!newStateContent.arweave || !newStateContent.deployments) {
      throw new Error('New state file has invalid structure');
    }
    
    console.log(`   ✅ Validated: structure correct`);
    
    // 7. Delete old file (commented out for safety - user can delete manually)
    // fs.unlinkSync(oldStateFile);
    // console.log(`   → Deleted: ${path.basename(oldStateFile)}`);
    
    return true;
  } catch (error) {
    console.error(`   ❌ Error: ${error.message}`);
    console.error(`   → Rollback: keeping old file`);
    
    // Cleanup: remove new file if created but invalid
    if (fs.existsSync(newStateFile)) {
      try {
        fs.unlinkSync(newStateFile);
        console.error(`   → Removed invalid new file`);
      } catch (e) {
        // Ignore cleanup errors
      }
    }
    
    return false;
  }
}

// ====================================================================
// MAIN
// ====================================================================

console.log('\n' + '='.repeat(70));
console.log('🔄 STATE FILES MIGRATION: localhost → network-agnostic');
console.log('='.repeat(70));
console.log(`📁 Components directory: ${COMPONENTS_DIR}\n`);

// Check if components directory exists
if (!fs.existsSync(COMPONENTS_DIR)) {
  console.error(`❌ Components directory not found: ${COMPONENTS_DIR}`);
  console.error(`   → Please run this script from project root`);
  process.exit(1);
}

// Get all component directories
const allEntries = fs.readdirSync(COMPONENTS_DIR);
const components = allEntries.filter(name => {
  const fullPath = path.join(COMPONENTS_DIR, name);
  return fs.statSync(fullPath).isDirectory();
});

console.log(`📊 Found ${components.length} component directories\n`);

let migrated = 0;
let skipped = 0;
let errors = 0;

// Migrate each component
components.forEach((component, index) => {
  const componentDir = path.join(COMPONENTS_DIR, component);
  
  console.log(`[${index + 1}/${components.length}]`);
  
  try {
    if (migrateStateFile(componentDir)) {
      migrated++;
    } else {
      skipped++;
    }
  } catch (error) {
    console.error(`❌ Fatal error migrating ${component}: ${error.message}`);
    errors++;
  }
  
  console.log(''); // Empty line between components
});

// Summary
console.log('='.repeat(70));
console.log('📊 MIGRATION SUMMARY');
console.log('='.repeat(70));
console.log(`✅ Migrated: ${migrated}`);
console.log(`⏭️  Skipped: ${skipped}`);
console.log(`❌ Errors: ${errors}`);
console.log(`📊 Total: ${components.length}`);
console.log('='.repeat(70));

if (migrated > 0) {
  console.log('\n✅ Migration successful!');
  console.log('\n📝 Next steps:');
  console.log('   1. Review migrated files in data/components/');
  console.log('   2. Test Action 555 with migrated state');
  console.log('   3. If all works, delete backup files:');
  console.log('      find data/components -name "*_localhost.backup.json" -delete');
  console.log('   4. Delete old state files:');
  console.log('      find data/components -name "_upload_state_localhost.json" -delete');
}

if (errors > 0) {
  console.error('\n⚠️ Some components had errors during migration');
  console.error('   → Review error messages above');
  console.error('   → Old files preserved for manual inspection');
  process.exit(1);
}

process.exit(0);

