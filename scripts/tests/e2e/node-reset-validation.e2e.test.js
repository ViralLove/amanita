/**
 * E2E Test: Node Reset Validation - Complete Workflow
 * 
 * Phase 4: E2E Validation - Node reset scenario with full workflow validation
 * 
 * Goal: Verify that Actions 1, 777, 555 work correctly on a clean node and
 * all CIDs are found in the contract after upload (7/7 for complex, 2/2 for simple)
 * 
 * Method: @e2e-test-build.core.mdc
 * - Real Hardhat node
 * - Real contracts deployment
 * - Real component upload
 * - Real validator check
 * 
 * @version 1.0.0
 * @date 2025-11-25
 */

const { expect } = require('chai');
const { ethers } = require('hardhat');
const { E2EHarness } = require('../helpers');
const EthersUtils = require('../../../lib/utils/EthersUtils');
const ContractManager = require('../../../lib/services/ContractManager');
const ArweaveManager = require('../../../lib/services/ArweaveManager');
const { ActionsManager } = require('../../../lib/actions');
const config = require('../../../lib/config');

describe('E2E: Node Reset Validation - Complete Workflow', function() {
  this.timeout(300000); // 5 minutes for full workflow

  let harness;
  let deployerAddress;
  let sellerAddress;
  let deployerInvite;
  let actionsManager;
  let provider;

  before(async function() {
    this.timeout(120000); // 2 minutes for setup

    // Start E2E infrastructure
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();

    // Get signers
    const [deployer, seller] = await ethers.getSigners();
    deployerAddress = deployer.address;
    sellerAddress = seller.address;

    // Reset network for clean state
    await harness.resetNetwork();

    // Initialize ActionsManager
    provider = ethers.provider;
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(provider, config, ethersUtils);
    const arweaveManager = new ArweaveManager(config);
    actionsManager = new ActionsManager(contractManager, arweaveManager, ethersUtils, config);

    console.log(`\n✅ E2E Infrastructure ready`);
    console.log(`   Deployer: ${deployerAddress}`);
    console.log(`   Seller: ${sellerAddress}`);
  });

  after(async function() {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  // ====================================================================
  // 🔹 TEST 1: Action 1 - Deploy Contracts
  // ====================================================================

  describe('Test 1: Action 1 - Deploy Contracts on Clean Node', () => {
    it('должен развернуть все контракты на чистой ноде', async function() {
      // WHEN: Action 1 выполняется на чистой ноде
      const result = await actionsManager.executeAction(1);
      
      // THEN: Контракты развернуты
      expect(result).to.exist;
      expect(result.success).to.be.true;
      expect(result.contracts).to.exist;
      
      // Проверяем, что MagicRegistry развернут
      const magicRegistryAddress = process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS;
      expect(magicRegistryAddress).to.exist;
      expect(magicRegistryAddress).to.match(/^0x[a-fA-F0-9]{40}$/);
      
      console.log(`\n✅ Action 1 completed`);
      console.log(`   MagicRegistry: ${magicRegistryAddress}`);
    });
  });

  // ====================================================================
  // 🔹 TEST 2: Action 777 - Generate Deployer Invites
  // ====================================================================

  describe('Test 2: Action 777 - Generate Deployer Invites', () => {
    it('должен сгенерировать 12 инвайтов для деплоера', async function() {
      // WHEN: Action 777 выполняется
      const result = await actionsManager.executeAction(777);
      
      // THEN: Инвайты сгенерированы
      expect(result).to.exist;
      expect(result.success).to.be.true;
      
      // Проверяем файл с инвайтами
      const fs = require('fs');
      const path = require('path');
      const invitesFile = path.join(__dirname, '../../../../bot/flowers/deployer_invites_localhost.txt');
      
      expect(fs.existsSync(invitesFile)).to.be.true;
      
      const invitesContent = fs.readFileSync(invitesFile, 'utf8');
      const invites = invitesContent.split('\n').filter(line => line.trim().startsWith('AMANITA-'));
      
      expect(invites.length).to.equal(12);
      
      // Сохраняем первый инвайт для Action 555
      deployerInvite = invites[0];
      process.env.DEPLOYER_INVITE = deployerInvite;
      
      console.log(`\n✅ Action 777 completed`);
      console.log(`   Invites generated: ${invites.length}`);
      console.log(`   First invite (for Action 555): ${deployerInvite}`);
    });
  });

  // ====================================================================
  // 🔹 TEST 3: Action 555 - Upload Components
  // ====================================================================

  describe('Test 3: Action 555 - Upload Components', () => {
    it('должен загрузить компоненты и активировать seller', async function() {
      // Setup environment
      process.env.DEPLOYER_INVITE = deployerInvite;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false'; // Используем mock Arweave для теста
      
      // WHEN: Action 555 выполняется
      const result = await actionsManager.executeAction(555);
      
      // THEN: Компоненты загружены
      expect(result).to.exist;
      expect(result.success).to.be.true;
      expect(result.uploadResults).to.exist;
      
      console.log(`\n✅ Action 555 completed`);
      console.log(`   Upload results:`, result.uploadResults);
    });
  });

  // ====================================================================
  // 🔹 TEST 4: Validator Check - All CIDs Found
  // ====================================================================

  describe('Test 4: Validator Check - All CIDs Found', () => {
    it('должен найти все CIDs в контракте (7/7 для complex, 2/2 для simple)', async function() {
      // WHEN: Валидатор проверяет загруженный компонент
      const { validateComponent } = require('../../../validators/validate_component_upload');
      
      const componentId = 'amanita_muscaria';
      const validationReport = await validateComponent(componentId, 'localhost', sellerAddress);
      
      // THEN: Все CIDs найдены
      expect(validationReport).to.exist;
      
      // Проверяем contract layer (CIDs в контракте)
      const contractChecks = validationReport.contract;
      
      console.log(`\n📊 Validation Report:`);
      console.log(`   Component: ${componentId}`);
      console.log(`   Quality Score: ${validationReport.qualityScore}/10`);
      console.log(`   Contract - Simple Fields Found: ${contractChecks.simple_fields?.keys_found || 0}/2`);
      console.log(`   Contract - Complex Fields Found: ${contractChecks.complex_fields?.keys_found || 0}/7`);
      
      // Проверяем simple fields (2/2)
      expect(contractChecks.simple_fields).to.exist;
      expect(contractChecks.simple_fields.keys_found).to.equal(2);
      expect(contractChecks.simple_fields.keys_found).to.equal(contractChecks.simple_fields.keys_total);
      
      // Проверяем complex fields (7/7)
      expect(contractChecks.complex_fields).to.exist;
      expect(contractChecks.complex_fields.keys_found).to.equal(7);
      expect(contractChecks.complex_fields.keys_found).to.equal(contractChecks.complex_fields.keys_total);
      
      // Проверяем качество (должно быть >= 8.0)
      expect(validationReport.qualityScore).to.be.at.least(8.0);
      expect(validationReport.passed).to.be.true;
      
      // Проверяем совместимость с Action 444
      expect(contractChecks.action444_compatible).to.be.true;
      
      console.log(`\n✅ All CIDs found in contract`);
      console.log(`   Simple Fields: ${contractChecks.simple_fields.keys_found}/${contractChecks.simple_fields.keys_total} ✅`);
      console.log(`   Complex Fields: ${contractChecks.complex_fields.keys_found}/${contractChecks.complex_fields.keys_total} ✅`);
      console.log(`   Quality Score: ${validationReport.qualityScore}/10 ✅`);
      console.log(`   Action 444 Compatible: ✅`);
    });
  });
});

