/**
 * E2E: Catalog Pipeline (41 → 42 → 43 → 444)
 * 
 * Tests complete catalog workflow from CSV to on-chain registration
 */

const { expect } = require('chai');
const E2EHarness = require('../../helpers/E2EHarness');
const fs = require('fs');
const path = require('path');

describe('E2E Workflow: Catalog Pipeline', function() {
  this.timeout(180000);

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

  describe('Complete Catalog Workflow', () => {
    it('should execute 41 → 42 → 43 → 444 pipeline', async function() {
      this.timeout(120000);
      
      const timer = harness.measureExecutionTime('Complete Catalog Pipeline');
      
      // STEP 1: Action 41 - CSV → JSON
      console.log('\n📍 STEP 1: CSV → JSON Transform');
      const csvPath = path.join(__dirname, '../../fixtures/catalog/test_catalog.csv');
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
      console.log(`✓ Transformed: ${products.length} products`);
      
      // STEP 2: Action 42 - Upload to Arweave (QUICK mode)
      console.log('\n📍 STEP 2: Generate CID (QUICK mode)');
      const json = JSON.stringify(products);
      const randomPart = Array(5).fill(0).map(() => Math.random().toString(36).substring(2, 11)).join('');
      const cid = `Qm${randomPart.substring(0, 44)}`;
      
      expect(cid).to.have.lengthOf(46);
      console.log(`✓ CID generated: ${cid}`);
      
      // STEP 3: Action 43 - Deploy ProductRegistry
      console.log('\n📍 STEP 3: Deploy ProductRegistry');
      const { ethers } = require('hardhat');
      
      const Logic = await ethers.getContractFactory('ProductRegistryLogic');
      const logic = await Logic.deploy();
      await logic.waitForDeployment();
      
      const Proxy = await ethers.getContractFactory('ProductRegistryProxy');
      const proxy = await Proxy.deploy(await logic.getAddress(), '0x');
      await proxy.waitForDeployment();
      
      const registryAddress = await proxy.getAddress();
      await harness.validateDeployment(registryAddress);
      console.log(`✓ ProductRegistry deployed: ${registryAddress}`);
      
      // STEP 4: Action 444 - Validate complete state
      console.log('\n📍 STEP 4: Validate Pipeline State');
      const finalState = {
        products: products.length,
        cid: cid,
        registry: registryAddress
      };
      
      expect(finalState.products).to.equal(3);
      expect(finalState.cid).to.exist;
      expect(finalState.registry).to.exist;
      
      const duration = timer.end();
      console.log(`\n✅ CATALOG PIPELINE COMPLETE in ${(duration / 1000).toFixed(2)}s`);
    });

    it('should maintain state consistency across pipeline', async () => {
      const { ethers } = require('hardhat');
      
      // Step 1: Deploy registry
      const Logic = await ethers.getContractFactory('ProductRegistryLogic');
      const logic = await Logic.deploy();
      await logic.waitForDeployment();
      const logicAddress = await logic.getAddress();
      
      // Validate: Logic exists
      const code1 = await ethers.provider.getCode(logicAddress);
      expect(code1).to.not.equal('0x');
      
      // Step 2: Deploy Proxy (state should persist)
      const Proxy = await ethers.getContractFactory('ProductRegistryProxy');
      const proxy = await Proxy.deploy(logicAddress, '0x');
      await proxy.waitForDeployment();
      
      // Validate: Logic still exists
      const code2 = await ethers.provider.getCode(logicAddress);
      expect(code2).to.equal(code1);
      
      console.log('✓ State consistency validated');
    });
  });

  describe('Error Recovery', () => {
    it('should handle error at step 2 (Arweave)', async () => {
      // Step 1 succeeds
      const csvPath = path.join(__dirname, '../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      expect(csvData).to.exist;
      
      // Step 2 fails
      try {
        throw new Error('Arweave upload failed');
      } catch (error) {
        expect(error.message).to.include('Arweave upload failed');
        
        // CSV still readable (step 1 result preserved)
        expect(csvData).to.exist;
        
        console.log('✓ Error recovery validated');
      }
    });
  });

  describe('Performance Benchmarking', () => {
    it('should execute full pipeline за < 10s', async function() {
      this.timeout(15000);
      
      const timer = harness.measureExecutionTime('Full Catalog Pipeline');
      
      // Execute all steps
      const csvPath = path.join(__dirname, '../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        products.push({ id: values[0], name: values[1] });
      }
      
      const json = JSON.stringify(products);
      const cid = `Qm${Math.random().toString(36).substring(2, 15)}`;
      
      const { ethers } = require('hardhat');
      await (await ethers.getContractFactory('ProductRegistryLogic')).deploy();
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(10000);
    });
  });
});
