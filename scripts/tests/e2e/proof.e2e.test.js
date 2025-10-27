/**
 * E2E Proof Tests
 * 
 * Validates E2E infrastructure setup:
 * - Hardhat node lifecycle management
 * - test.env isolation
 * - Snapshot/reset mechanism
 * - Real blockchain interaction
 */

const { expect } = require('chai');
const E2EHarness = require('../helpers/E2EHarness');

describe('E2E Infrastructure Proof Tests', function() {
  // E2E tests are slow (real blockchain)
  this.timeout(60000); // 60 seconds per test
  
  let harness;
  
  before(async function() {
    this.timeout(90000); // Node startup может занять до 30s
    
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
    it('должен иметь запущенный Hardhat node', async () => {
      const { ethers } = require('hardhat');
      
      // WHEN: Check network is running
      const network = await ethers.provider.getNetwork();
      const blockNumber = await ethers.provider.getBlockNumber();
      
      // THEN: Network is responsive
      expect(network).to.exist;
      expect(network.chainId).to.equal(31337n); // Hardhat default chainId
      expect(blockNumber).to.be.a('number');
    });

    it('должен использовать test.env (не production .env)', () => {
      // THEN: Environment loaded from e2e.test.env
      expect(process.env.E2E_TEST_MODE).to.equal('true');
      expect(process.env.DEPLOYER_ADDRESS).to.equal('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266');
      expect(process.env.SELLER_ADDRESS).to.equal('0x70997970C51812dc3A010C7d01b50e0d17dc79C8');
      
      // Hardhat default accounts
      expect(process.env.DEPLOYER_PRIVATE_KEY).to.equal('0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80');
    });

    it('должен иметь доступ к Hardhat accounts с балансом', async () => {
      const { ethers } = require('hardhat');
      
      // GIVEN: Deployer address from test.env
      const deployerAddress = process.env.DEPLOYER_ADDRESS;
      
      // WHEN: Check balance
      const balance = await ethers.provider.getBalance(deployerAddress);
      
      // THEN: Account has ETH (Hardhat gives 10000 ETH default)
      expect(balance > 0n).to.be.true; // BigInt comparison
      expect(ethers.formatEther(balance)).to.match(/^\d+\.\d+$/); // Valid ETH format
    });
  });

  describe('Snapshot/Reset Mechanism', () => {
    it('должен сбрасывать state между тестами', async () => {
      const { ethers } = require('hardhat');
      
      // GIVEN: Initial block number
      const initialBlock = await ethers.provider.getBlockNumber();
      
      // WHEN: Make some transactions (mine blocks)
      const [signer] = await ethers.getSigners();
      await signer.sendTransaction({
        to: '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
        value: ethers.parseEther('1.0')
      });
      
      const afterTxBlock = await ethers.provider.getBlockNumber();
      
      // THEN: Block number increased
      expect(afterTxBlock).to.be.greaterThan(initialBlock);
      
      // WHEN: Reset network
      await harness.resetNetwork();
      
      const afterResetBlock = await ethers.provider.getBlockNumber();
      
      // THEN: Block number reset (snapshot restored)
      // Note: snapshot/revert may increment block by 1-2
      expect(afterResetBlock).to.be.lessThanOrEqual(afterTxBlock);
    });

    it('должен откатывать deployed contracts при reset', async () => {
      const { ethers } = require('hardhat');
      
      // GIVEN: Initial snapshot (clean state)
      const initialBlock = await ethers.provider.getBlockNumber();
      
      // WHEN: Deploy contract AFTER snapshot
      const SimpleContract = await ethers.getContractFactory('MagicRegistry');
      const contract = await SimpleContract.deploy();
      await contract.waitForDeployment();
      
      const contractAddress = await contract.getAddress();
      const codeAfterDeploy = await ethers.provider.getCode(contractAddress);
      expect(codeAfterDeploy).to.not.equal('0x'); // Contract deployed
      
      // WHEN: Reset network (revert to snapshot BEFORE deploy)
      await harness.resetNetwork();
      
      // THEN: Contract reverted (no longer exists at that address)
      const codeAfterReset = await ethers.provider.getCode(contractAddress);
      expect(codeAfterReset).to.equal('0x'); // Contract reverted
      
      // Block number should also be close to initial
      const resetBlock = await ethers.provider.getBlockNumber();
      expect(resetBlock).to.be.lessThanOrEqual(initialBlock + 2); // Allow small delta
    });
  });

  describe('Contract Deployment Validation', () => {
    it('должен деплоить real contract на Hardhat node', async () => {
      const { ethers } = require('hardhat');
      
      // WHEN: Deploy MagicRegistry
      const MagicRegistry = await ethers.getContractFactory('MagicRegistry');
      const registry = await MagicRegistry.deploy();
      await registry.waitForDeployment();
      
      const address = await registry.getAddress();
      
      // THEN: Contract deployed successfully
      expect(address).to.match(/^0x[a-fA-F0-9]{40}$/);
      
      // Validate using harness helper
      const validation = await harness.validateDeployment(address);
      expect(validation.deployed).to.be.true;
      expect(validation.codeLength).to.be.greaterThan(100);
    });

    it('должен взаимодействовать с deployed contract', async () => {
      const { ethers } = require('hardhat');
      
      // GIVEN: Deploy MagicRegistry
      const MagicRegistry = await ethers.getContractFactory('MagicRegistry');
      const registry = await MagicRegistry.deploy();
      await registry.waitForDeployment();
      
      // WHEN: Register contract using set() method
      const testAddress = '0x1234567890123456789012345678901234567890';
      const tx = await registry.set('TestContract', testAddress);
      const receipt = await tx.wait();
      
      // THEN: Transaction successful
      expect(receipt.status).to.equal(1);
      
      // AND: Contract registered
      const registeredAddress = await registry.get('TestContract');
      expect(registeredAddress).to.equal(testAddress);
    });
  });

  describe('E2E Harness Helpers', () => {
    it('должен предоставлять getCurrentBlock helper', async () => {
      // WHEN: Get current block
      const blockNumber = await harness.getCurrentBlock();
      
      // THEN: Valid block number returned
      expect(blockNumber).to.be.a('number');
      expect(blockNumber).to.be.greaterThanOrEqual(0);
    });

    it('должен предоставлять getBalance helper', async () => {
      // GIVEN: Deployer address
      const deployerAddress = process.env.DEPLOYER_ADDRESS;
      
      // WHEN: Get balance
      const balance = await harness.getBalance(deployerAddress);
      
      // THEN: Balance is valid wei string
      expect(balance).to.be.a('string');
      expect(parseInt(balance)).to.be.greaterThan(0);
    });
  });
});

