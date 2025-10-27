/**
 * E2E Tests: Action 0 - Deploy MagicRegistry
 * 
 * Tests complete deployment workflow for MagicRegistry contract:
 * - Real Hardhat node
 * - Real contract deployment
 * - Real on-chain validation
 * 
 * Critical Path Coverage:
 * - Registry deployment (happy path)
 * - Registry operations (set, get)
 * - Error scenarios
 * - State validation on-chain
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');

describe('E2E: Action 0 - Deploy MagicRegistry', function() {
  this.timeout(120000); // 2 minutes for E2E tests

  let harness;
  let deployRouter;

  before(async function() {
    this.timeout(90000); // Node startup

    harness = new E2EHarness();

    // Start Hardhat node
    await harness.startHardhatNode();

    // Load test environment
    harness.loadTestEnv();

    // Create initial snapshot
    await harness.resetNetwork();
  });

  after(async function() {
    // Stop Hardhat node
    await harness.stopHardhatNode();

    // Restore original environment
    harness.restoreEnv();
  });

  beforeEach(async function() {
    // Reset network to clean state before each test
    await harness.resetNetwork();
  });

  describe('Infrastructure Validation', () => {
    it('должен иметь готовую E2E инфраструктуру', async () => {
      const { ethers } = require('hardhat');
      const network = await ethers.provider.getNetwork();
      const blockNumber = await ethers.provider.getBlockNumber();
      
      expect(network).to.exist;
      expect(network.chainId).to.equal(31337n);
      expect(blockNumber).to.be.a('number');
      
      console.log(`✓ Network ready: chainId ${network.chainId}, block ${blockNumber}`);
    });

    it('должен использовать e2e.test.env (не production)', () => {
      expect(process.env.E2E_TEST_MODE).to.equal('true');
      expect(process.env.DEPLOYER_ADDRESS).to.match(/^0x[a-fA-F0-9]{40}$/);
      expect(process.env.NETWORK).to.equal('localhost');
      
      console.log('✓ Test environment isolated');
    });
  });

  describe('MagicRegistry Deployment', () => {
    it('должен деплоить MagicRegistry contract на Hardhat node', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // EXECUTE: Deploy MagicRegistry using ethers (E2E direct deployment)
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      const address = await magicRegistry.getAddress();
      
      // VALIDATE: Address format
      expect(address).to.exist;
      expect(address).to.match(/^0x[a-fA-F0-9]{40}$/);
      
      // VALIDATE: Contract deployed on-chain
      const validation = await harness.validateDeployment(address);
      expect(validation.deployed).to.be.true;
      expect(validation.codeLength).to.be.greaterThan(100);
      
      console.log(`✓ MagicRegistry deployed at ${address}`);
    });

    it('должен возвращать functional contract instance', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // Deploy
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      const address = await magicRegistry.getAddress();
      
      // VALIDATE: Contract is functional
      expect(magicRegistry).to.exist;
      expect(address).to.exist;
      
      // VALIDATE: Can get target (returns address)
      const target = await magicRegistry.target;
      expect(target).to.equal(address);
      
      console.log('✓ Contract instance functional');
    });

    it('должен иметь корректные contract methods', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // Deploy
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      // VALIDATE: Key methods exist and work
      const testAddress = '0x1234567890123456789012345678901234567890';
      
      // Should be able to call view methods
      const getResult = await magicRegistry.get('TestContract');
      expect(getResult).to.exist; // Returns zero address if not found
      
      console.log('✓ Contract methods accessible');
    });
  });

  describe('Registry Operations', () => {
    let registryAddress;
    let MagicRegistry;

    beforeEach(async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // Deploy MagicRegistry
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const registry = await MagicRegistryFactory.deploy();
      await registry.waitForDeployment();
      
      registryAddress = await registry.getAddress();
      MagicRegistry = registry;
    });

    it('должен регистрировать contract в registry', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      const testContractName = 'TestContract';
      const testContractAddress = '0x' + '1234567890'.repeat(4);
      
      // EXECUTE: Register contract
      const tx = await MagicRegistry.set(testContractName, testContractAddress);
      const receipt = await tx.wait();
      
      // VALIDATE: Transaction succeeded
      expect(receipt.status).to.equal(1);
      
      // VALIDATE: Contract registered on-chain
      const registeredAddress = await MagicRegistry.get(testContractName);
      expect(registeredAddress).to.equal(testContractAddress);
      
      console.log(`✓ Contract registered: ${testContractName} → ${registeredAddress}`);
    });

    it('должен получать зарегистрированный contract address', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      const contractName = 'SpiralEngine';
      const contractAddress = '0x' + 'abcdef1234'.repeat(4);
      
      // Register
      await MagicRegistry.set(contractName, contractAddress);
      
      // GET: Retrieve
      const retrievedAddress = await MagicRegistry.get(contractName);
      
      // VALIDATE: Address matches (case-insensitive comparison)
      expect(retrievedAddress.toLowerCase()).to.equal(contractAddress.toLowerCase());
      
      console.log(`✓ Retrieved address: ${retrievedAddress}`);
    });

    it('должен обновлять existing registry entry', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      const contractName = 'ProductRegistry';
      const addressV1 = '0x' + '1111111111'.repeat(4);
      const addressV2 = '0x' + '2222222222'.repeat(4);
      
      // Register V1
      await MagicRegistry.set(contractName, addressV1);
      const v1Address = await MagicRegistry.get(contractName);
      expect(v1Address).to.equal(addressV1);
      
      // UPDATE: Register V2
      await MagicRegistry.set(contractName, addressV2);
      const v2Address = await MagicRegistry.get(contractName);
      
      // VALIDATE: Updated
      expect(v2Address).to.equal(addressV2);
      expect(v2Address).to.not.equal(v1Address);
      
      console.log(`✓ Registry updated: ${addressV1} → ${addressV2}`);
    });
  });

  describe('Error Scenarios', () => {
    it('должен handle deployment failure gracefully', async () => {
      const { ethers } = require('hardhat');
      
      // This test validates error handling is present
      // Simulating deployment failure with invalid contract name
      
      try {
        await ethers.getContractFactory('NonExistentContract');
        expect.fail('Should have thrown error for non-existent contract');
      } catch (error) {
        // Expected: error thrown
        expect(error).to.be.an('error');
        expect(error.message).to.be.a('string');
        
        console.log(`✓ Error handled: ${error.message}`);
      }
    });

    it('должен валидировать contract address format', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // Deploy
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      const address = await magicRegistry.getAddress();
      
      // VALIDATE: Address format
      expect(address).to.match(/^0x[a-fA-F0-9]{40}$/);
      
      // VALIDATE: Not zero address
      expect(address).to.not.equal(ethers.ZeroAddress);
      
      console.log('✓ Address format valid');
    });
  });

  describe('State Validation', () => {
    it('должен валидировать on-chain state после deploy', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // Deploy
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      const address = await magicRegistry.getAddress();
      
      // VALIDATE: Deployment state via harness
      const deploymentState = await harness.getDeploymentState();
      
      expect(deploymentState.blockNumber).to.be.greaterThan(0);
      expect(deploymentState.deployer.address).to.exist;
      
      // VALIDATE: Bytecode on-chain
      const code = await ethers.provider.getCode(address);
      expect(code).to.not.equal('0x');
      expect(code.length).to.be.greaterThan(100);
      
      console.log(`✓ On-chain state validated: block ${deploymentState.blockNumber}`);
    });

    it('должен иметь non-empty bytecode on-chain', async () => {
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      // Deploy
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      const address = await magicRegistry.getAddress();
      
      // VALIDATE: Bytecode
      const code = await ethers.provider.getCode(address);
      
      expect(code).to.be.a('string');
      expect(code).to.not.equal('0x');
      expect(code).to.not.equal('0x0');
      expect(code.length).to.be.greaterThan(100);
      
      console.log(`✓ Bytecode validated: ${code.length} characters`);
    });
  });

  describe('Performance Metrics', () => {
    it('должен деплоиться за разумное время (<30s)', async function() {
      this.timeout(45000); // 45s for performance test
      
      const { ethers } = require('hardhat');
      const [deployer] = await ethers.getSigners();
      
      const startTime = Date.now();
      
      // Deploy
      const MagicRegistryFactory = await ethers.getContractFactory('MagicRegistry', deployer);
      const magicRegistry = await MagicRegistryFactory.deploy();
      await magicRegistry.waitForDeployment();
      
      const duration = Date.now() - startTime;
      const address = await magicRegistry.getAddress();
      
      // VALIDATE: Deployment time
      expect(duration).to.be.lessThan(30000); // < 30 seconds
      expect(address).to.exist;
      
      console.log(`⏱️ Deployment time: ${duration}ms`);
    });
  });
});

