/**
 * Test Script: Simple Fields Restoration After Node Reset
 * 
 * Проверяет сценарий перезапуска ноды:
 * 1. State файл содержит simple_fields_uploaded = true
 * 2. Контракт пуст (нода перезапущена)
 * 3. uploadSimpleFields должен восстановить данные из state в контракт
 * 
 * Usage:
 *   node scripts/tests/test-simple-fields-restoration.js
 */

const { ethers } = require('hardhat');
const path = require('path');
const fs = require('fs');
const uploadSteps = require('../lib/upload_steps');
const stateManager = require('../lib/state_manager');
const contractVerification = require('../lib/contract_verification');

async function testRestorationScenario() {
  console.log('\n' + '='.repeat(70));
  console.log('🧪 Test: Simple Fields Restoration After Node Reset');
  console.log('='.repeat(70));

  // 1. Загружаем реальный state файл
  const componentId = 'amanita_muscaria';
  const network = 'localhost';
  const componentDir = path.resolve(__dirname, '../../data/components', componentId);
  const stateFile = path.join(componentDir, `_upload_state_${network}.json`);

  if (!fs.existsSync(stateFile)) {
    console.error(`❌ State file not found: ${stateFile}`);
    process.exit(1);
  }

  const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  console.log(`\n✅ State file loaded: ${stateFile}`);
  console.log(`   Component: ${state.component_id}`);
  console.log(`   Steps completed: ${state.steps_completed.join(', ')}`);
  console.log(`   Simple fields CIDs:`);
  if (state.simple_fields) {
    console.log(`     - title: ${state.simple_fields.title?.cid || 'N/A'}`);
    console.log(`     - dosage: ${state.simple_fields.dosage_types?.cid || 'N/A'}`);
  }

  // 2. Проверяем, что шаг simple_fields_uploaded выполнен в state
  const isCompletedInState = stateManager.isStepCompleted(state, 'simple_fields_uploaded');
  if (!isCompletedInState) {
    console.error('❌ Test precondition failed: simple_fields_uploaded not in state');
    process.exit(1);
  }
  console.log('\n✅ Precondition: simple_fields_uploaded is marked in state');

  // 3. Загружаем контракты
  const [deployer, seller] = await ethers.getSigners();
  const sellerAddress = seller.address;
  console.log(`\n📦 Loading contracts...`);
  console.log(`   Seller: ${sellerAddress}`);

  const ContractManager = require('../lib/services/ContractManager');
  const config = require('../lib/config');
  const contractManager = new ContractManager(config);

  const amanitaInternational = await contractManager.loadUUPSContract('AmanitaInternational');
  const amanitaIntlAddress = await amanitaInternational.getAddress();
  console.log(`   AmanitaInternational: ${amanitaIntlAddress}`);

  // 4. Проверяем состояние контракта (должно быть пусто для теста)
  console.log('\n🔍 Checking contract state...');
  const contractCheck = await contractVerification.checkSimpleFieldsInContract({
    contracts: { amanitaInternational },
    seller: { address: sellerAddress, signer: seller },
    biounit_id: componentId
  });

  console.log(`   Contract check result:`);
  console.log(`     - All present: ${contractCheck.allPresent}`);
  console.log(`     - Missing: ${contractCheck.missing.join(', ') || 'none'}`);
  console.log(`     - Present: ${Object.keys(contractCheck.present).join(', ') || 'none'}`);

  // 5. Выполняем унифицированную проверку
  console.log('\n🔍 Running verifyStepCompletion...');
  const verification = await contractVerification.verifyStepCompletion({
    state,
    stepName: 'simple_fields_uploaded',
    contractCheckFn: () => contractVerification.checkSimpleFieldsInContract({
      contracts: { amanitaInternational },
      seller: { address: sellerAddress, signer: seller },
      biounit_id: componentId
    })
  });

  console.log(`   Verification result:`);
  console.log(`     - isComplete: ${verification.isComplete}`);
  console.log(`     - isConsistent: ${verification.isConsistent}`);
  console.log(`     - missingItems: ${verification.missingItems.join(', ') || 'none'}`);

  // 6. Если несоответствие обнаружено, проверяем восстановление
  if (verification.isComplete && !verification.isConsistent) {
    console.log('\n⚠️  Inconsistency detected: State says "uploaded", but contract is empty');
    console.log('   This simulates a node reset scenario');
    console.log('   Testing restoration...');

    // Создаем context для uploadSimpleFields
    const context = {
      contracts: { amanitaInternational },
      seller: { address: sellerAddress, signer: seller },
      biounit_id: componentId,
      componentDir: componentDir,
      network: network,
      dryRun: false,
      arweaveOnly: false
    };

    // Вызываем uploadSimpleFields (должен восстановить данные)
    console.log('\n🔧 Calling uploadSimpleFields (should restore from state)...');
    const result = await uploadSteps.uploadSimpleFields(context, state);

    console.log('\n✅ uploadSimpleFields completed');
    console.log(`   Result keys: ${Object.keys(result).join(', ')}`);

    // 7. Проверяем, что данные теперь в контракте
    console.log('\n🔍 Verifying contract state after restoration...');
    const contractCheckAfter = await contractVerification.checkSimpleFieldsInContract({
      contracts: { amanitaInternational },
      seller: { address: sellerAddress, signer: seller },
      biounit_id: componentId
    });

    console.log(`   Contract check after restoration:`);
    console.log(`     - All present: ${contractCheckAfter.allPresent}`);
    console.log(`     - Missing: ${contractCheckAfter.missing.join(', ') || 'none'}`);
    console.log(`     - Present: ${Object.keys(contractCheckAfter.present).join(', ') || 'none'}`);

    // 8. Проверяем CIDs
    if (contractCheckAfter.allPresent) {
      console.log('\n✅ SUCCESS: All fields restored to contract');
      console.log(`   Title CID: ${contractCheckAfter.present.title}`);
      console.log(`   Dosage CID: ${contractCheckAfter.present.dosage}`);
      
      // Сравниваем с state
      if (state.simple_fields?.title?.cid === contractCheckAfter.present.title &&
          state.simple_fields?.dosage_types?.cid === contractCheckAfter.present.dosage) {
        console.log('\n✅ CID verification: CIDs match state file');
      } else {
        console.warn('\n⚠️  CID verification: CIDs do not match state file');
        console.warn(`   State title: ${state.simple_fields?.title?.cid}`);
        console.warn(`   Contract title: ${contractCheckAfter.present.title}`);
        console.warn(`   State dosage: ${state.simple_fields?.dosage_types?.cid}`);
        console.warn(`   Contract dosage: ${contractCheckAfter.present.dosage}`);
      }
    } else {
      console.error('\n❌ FAILURE: Not all fields restored');
      console.error(`   Missing: ${contractCheckAfter.missing.join(', ')}`);
      process.exit(1);
    }
  } else if (verification.isComplete && verification.isConsistent) {
    console.log('\n✅ Contract already has data (no restoration needed)');
    console.log('   This means the contract was not reset, or data was already restored');
  } else {
    console.log('\n⚠️  Step not completed in state (expected for first upload)');
  }

  console.log('\n' + '='.repeat(70));
  console.log('✅ Test completed');
  console.log('='.repeat(70));
}

// Run test
if (require.main === module) {
  testRestorationScenario()
    .then(() => {
      console.log('\n✅ All tests passed');
      process.exit(0);
    })
    .catch((error) => {
      console.error('\n❌ Test failed:', error);
      process.exit(1);
    });
}

module.exports = { testRestorationScenario };

