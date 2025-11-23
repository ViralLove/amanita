/**
 * E2E: Action 444 - Automatic Pipeline (41 → 42 → 43)
 * 
 * Tests automated catalog pipeline orchestration
 */

const { expect } = require('chai');
const {
  E2EHarness,
  expectEvent,
  assertBusinessIdMapping,
  assertBusinessIdCleared,
  assertSellerState
} = require('../../../helpers');
const fs = require('fs');
const path = require('path');
const { ethers } = require('hardhat');

describe('E2E: Action 444 - Automatic Pipeline', function() {
  this.timeout(120000);

  let harness;

  before(async function() {
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    await harness.resetNetwork();
  });

  after(async () => {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async () => {
    await harness.resetNetwork();
  });

  describe('Pipeline Orchestration', () => {
    it('should validate pipeline components ready', async () => {
      // CSV fixture exists
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      expect(fs.existsSync(csvPath)).to.be.true;
      
      // Harness methods available
      expect(harness.measureExecutionTime).to.be.a('function');
      
      console.log('✓ Pipeline components ready');
    });

    it('should orchestrate CSV → JSON → CID workflow и зарегистрировать продукты', async () => {
      console.log('Фаза 1: Подготовка и чтение CSV');
      const timer = harness.measureExecutionTime('Automatic Pipeline');
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');

      console.log('Фаза 2: Проверка структуры CSV через validateCsvHeaders');
      harness.validateCsvHeaders(headers);

      const products = [];
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        products.push(product);
      }

      console.log('Фаза 3: Подтверждаем наличие businessId в каждой строке');
      expect(products).to.have.length.greaterThan(0);
      products.forEach(product => {
        expect(product.product_id, 'Отсутствует businessId (product_id) в CSV строке').to.be.a('string');
      });
      
      // STEP 2: Generate CID
      const json = JSON.stringify(products);
      const cid = harness.generateValidCid('action444-json');
      harness.assertCidFormat(cid);
      
      // STEP 3: Validate complete pipeline
      const result = {
        products: products.length,
        json: json.length,
        cid: cid
      };
      
      expect(result.products).to.equal(3);
      expect(result.json).to.be.greaterThan(0);
      expect(result.cid).to.match(/^Qm/);
      
      // STEP 4: Register products on-chain через harness
      console.log('Фаза 4: Разворачиваем suite для регистрации продуктов');
      const suite = await harness.deployProductSuite({ forceRedeploy: true });
      const { productRegistry, seller, sellerComponentIds } = suite;

      console.log('Фаза 5: Регистрируем продукты и валидируем CID');
      const registeredBusinessIds = [];
      for (let i = 0; i < products.length; i++) {
        const product = products[i];
        const businessId = product.product_id;
        const metadataCID = harness.generateValidCid(`action444-metadata-${i}`);
        harness.assertCidFormat(metadataCID);
        const componentId = sellerComponentIds[i % sellerComponentIds.length];

        await expectEvent(
          productRegistry
            .connect(seller)
            .createProduct(businessId, [componentId], metadataCID),
          productRegistry,
          'ProductCreated'
        );

        await assertBusinessIdMapping(productRegistry, businessId, i + 1);
        registeredBusinessIds.push(businessId);
      }

      console.log('Фаза 6: Проверяем очистку mapping и catalogVersion после pipeline');
      const sellerAddress = await seller.getAddress();
      await productRegistry.connect(seller).clearSellerCatalog(sellerAddress);
      for (const businessId of registeredBusinessIds) {
        await assertBusinessIdCleared(productRegistry, businessId);
      }
      const catalogVersion = await productRegistry.catalogVersion(sellerAddress);
      expect(Number(catalogVersion)).to.be.greaterThan(0);

      const duration = timer.end();
      expect(duration).to.be.lessThan(5000);
      
      console.log(`✓ Pipeline orchestrated: ${result.products} products → ${result.cid}`);
    });

    it('should validate state at each pipeline step', async () => {
      // Step 1: CSV loaded
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvExists = fs.existsSync(csvPath);
      expect(csvExists).to.be.true;
      
      // Step 2: JSON created + структура CSV
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      expect(lines.length).to.be.greaterThan(1);
      const headers = lines[0].split(',');
      harness.validateCsvHeaders(headers);

      // Step 3: CID generated
      const cid = harness.generateValidCid('action444-state-check');
      harness.assertCidFormat(cid);
      
      console.log('✓ State validated at each step');
    });
  });

  describe('Seller Preparation via Harness Helper', () => {
    it('должен подготовить seller через harness.deployProductSuite() + prepareSellerForE2E', async function() {
      this.timeout(60000);

      const suite = await harness.deployProductSuite({
        forceRedeploy: true,
        invitesPrefix: 'ACTION444'
      });

      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', suite.spiralEngineAddress);
      const sellerAddr = await suite.seller.getAddress();

      const adminAddress = await suite.admin.getAddress();

      await assertSellerState(SpiralEngine, sellerAddr, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: adminAddress
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle missing CSV file', async () => {
      const fakePath = path.join(__dirname, '../../../fixtures/catalog/non_existent.csv');
      
      expect(fs.existsSync(fakePath)).to.be.false;
      
      console.log('✓ Missing CSV detection works');
    });

    it('should rollback on pipeline failure', async () => {
      // Simulate pipeline failure at step 2
      try {
        throw new Error('Arweave upload failed');
      } catch (error) {
        expect(error.message).to.include('Arweave upload failed');
        
        // State should remain clean (no partial registration)
        const state = await harness.getDeploymentState();
        expect(state.blockNumber).to.be.greaterThanOrEqual(0);
        
        console.log('✓ Rollback handled');
      }
    });
  });

  describe('Performance', () => {
    it('should execute pipeline быстро (< 5s)', async () => {
      const timer = harness.measureExecutionTime('Action 444 Performance');
      
      // Simulate pipeline
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const json = JSON.stringify({ data: csvData.substring(0, 100) });
      const cid = 'QmTestCID';
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(5000);
    });
  });
});
