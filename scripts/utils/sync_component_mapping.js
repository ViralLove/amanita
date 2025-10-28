#!/usr/bin/env node

/**
 * 🔄 Sync Component Mapping Script
 * 
 * Синхронизация маппинга компонентов для быстрого доступа к CID
 * 
 * Usage:
 * node scripts/sync_component_mapping.js --network localhost
 * 
 * @version 1.0.0
 * @date 2025-01-12
 */

const fs = require('fs');
const path = require('path');
const { program } = require('commander');

// ====================================================================
// 🔧 CLI CONFIGURATION
// ====================================================================

program
  .name('sync_component_mapping')
  .description('Sync component CID mapping from upload states')
  .version('1.0.0')
  .requiredOption('--network <name>', 'Network name (localhost, polygon, etc.)')
  .parse(process.argv);

const options = program.opts();
const NETWORK = options.network;

console.log("🔄 Component Mapping Synchronization");
console.log("=".repeat(70));
console.log(`🌐 Network: ${NETWORK}`);
console.log("=".repeat(70));

// ====================================================================
// 📊 MAIN LOGIC
// ====================================================================

async function syncComponentMapping(network) {
  console.log("\n🔍 Scanning components directory...");
  
  const componentsDir = path.join(__dirname, 'organic_components');
  
  if (!fs.existsSync(componentsDir)) {
    throw new Error(`Components directory not found: ${componentsDir}`);
  }
  
  const allEntries = fs.readdirSync(componentsDir);
  const components = allEntries.filter(name => {
    const fullPath = path.join(componentsDir, name);
    return fs.statSync(fullPath).isDirectory() && 
           !name.startsWith('_') && 
           !name.startsWith('.');
  });
  
  console.log(`   ✅ Found ${components.length} component directories`);
  
  const mapping = {
    version: "1.0",
    network,
    last_updated: new Date().toISOString(),
    components: {},
    stats: {
      total_components: 0,
      active_components: 0,
      pending_components: 0,
      last_sync: new Date().toISOString()
    }
  };
  
  console.log("\n🔍 Processing components...");
  
  for (const biounit_id of components) {
    const componentDir = path.join(componentsDir, biounit_id);
    const stateFile = path.join(componentDir, `_upload_state_${network}.json`);
    const componentFile = path.join(componentDir, `${biounit_id}.json`);
    
    if (!fs.existsSync(componentFile)) {
      console.warn(`   ⚠️ ${biounit_id}: component JSON not found, skipping`);
      continue;
    }
    
    mapping.stats.total_components++;
    
    if (!fs.existsSync(stateFile)) {
      console.warn(`   ⚠️ ${biounit_id}: state file not found (not uploaded yet)`);
      mapping.stats.pending_components++;
      
      // Добавляем в маппинг как pending
      const componentJSON = JSON.parse(fs.readFileSync(componentFile, 'utf8'));
      mapping.components[biounit_id] = {
        status: "pending",
        root_cid: null,
        root_url: null,
        contract_id: null,
        last_updated: null,
        forms: componentJSON.forms || [],
        upload_state_path: stateFile
      };
      
      continue;
    }
    
    try {
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      
      // Проверяем что компонент полностью загружен
      if (!state.root_cid) {
        console.warn(`   ⚠️ ${biounit_id}: root_cid not set (upload incomplete)`);
        mapping.stats.pending_components++;
        
        mapping.components[biounit_id] = {
          status: "uploading",
          root_cid: null,
          root_url: null,
          contract_id: state.contract_registration?.component_id || null,
          last_updated: state.updated_at,
          forms: [],
          upload_state_path: stateFile
        };
        
        continue;
      }
      
      const componentJSON = JSON.parse(fs.readFileSync(componentFile, 'utf8'));
      
      mapping.components[biounit_id] = {
        status: "active",
        root_cid: state.root_cid,
        root_url: state.root_url || `https://arweave.net/${state.root_cid}`,
        contract_id: state.contract_registration?.component_id || null,
        last_updated: state.updated_at,
        forms: componentJSON.forms || [],
        upload_state_path: stateFile
      };
      
      mapping.stats.active_components++;
      
      console.log(`   ✅ ${biounit_id}: root_cid=${state.root_cid?.substring(0, 10)}...`);
      
    } catch (error) {
      console.error(`   ❌ ${biounit_id}: Error reading state - ${error.message}`);
      mapping.stats.pending_components++;
    }
  }
  
  // Сохранение маппинга
  const outputDir = path.join(__dirname, 'products');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const mappingFile = path.join(outputDir, `_component_cid_mapping_${network}.json`);
  fs.writeFileSync(mappingFile, JSON.stringify(mapping, null, 2));
  
  console.log("\n" + "=".repeat(70));
  console.log("✅ MAPPING SYNCHRONIZED");
  console.log("=".repeat(70));
  console.log(`Total components: ${mapping.stats.total_components}`);
  console.log(`Active (with CID): ${mapping.stats.active_components}`);
  console.log(`Pending (no CID): ${mapping.stats.pending_components}`);
  console.log(`\n💾 Mapping saved to: ${mappingFile}`);
  console.log("=".repeat(70));
  
  return mapping;
}

// ====================================================================
// 🚀 RUN
// ====================================================================

syncComponentMapping(NETWORK)
  .then(() => {
    console.log("\n✅ Sync completed successfully");
    process.exit(0);
  })
  .catch(error => {
    console.error("\n❌ Sync failed:");
    console.error(error.message);
    console.error(error.stack);
    process.exit(1);
  });

