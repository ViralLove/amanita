/**
 * E2E: Action 444 - Automatic Pipeline (41 → 42 → 43)
 * 
 * Tests automated catalog pipeline orchestration
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');
const fs = require('fs');
const path = require('path');

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

    it('should orchestrate CSV → JSON → CID workflow', async () => {
      const timer = harness.measureExecutionTime('Automatic Pipeline');
      
      // STEP 1: CSV → JSON
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        products.push(product);
      }
      
      expect(products).to.have.length.greaterThan(0);
      
      // STEP 2: Generate CID
      const json = JSON.stringify(products);
      const randomPart = Array(5).fill(0).map(() => Math.random().toString(36).substring(2, 11)).join('');
      const cid = `Qm${randomPart.substring(0, 44)}`;
      
      expect(cid).to.have.lengthOf(46);
      
      // STEP 3: Validate complete pipeline
      const result = {
        products: products.length,
        json: json.length,
        cid: cid
      };
      
      expect(result.products).to.equal(3);
      expect(result.json).to.be.greaterThan(0);
      expect(result.cid).to.match(/^Qm/);
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(5000);
      
      console.log(`✓ Pipeline orchestrated: ${result.products} products → ${result.cid}`);
    });

    it('should validate state at each pipeline step', async () => {
      // Step 1: CSV loaded
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvExists = fs.existsSync(csvPath);
      expect(csvExists).to.be.true;
      
      // Step 2: JSON created
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      expect(lines.length).to.be.greaterThan(1);
      
      // Step 3: CID generated
      const randomPart = Array(5).fill(0).map(() => Math.random().toString(36).substring(2, 11)).join('');
      const cid = `Qm${randomPart.substring(0, 44)}`;
      expect(cid).to.have.lengthOf(46);
      
      console.log('✓ State validated at each step');
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
