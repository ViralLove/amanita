/**
 * E2E Test Harness
 * 
 * Manages Hardhat node lifecycle for end-to-end testing.
 * Unlike IntegrationHarness, this uses a REAL blockchain node.
 * 
 * Key differences from IntegrationHarness:
 * - Real Hardhat node (programmatically controlled)
 * - Real contract deployments
 * - Real blockchain transactions
 * - Snapshot/reset mechanism for test isolation
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class E2EHarness {
  constructor() {
    this.hardhatProcess = null;
    this.networkReady = false;
    this.snapshotId = null;
    this.originalEnv = { ...process.env };
    this.testEnvPath = path.join(__dirname, '../fixtures/env/e2e.test.env');
  }

  /**
   * Start Hardhat node programmatically (or connect to existing)
   * 
   * Strategy:
   * 1. Try to connect to existing node at localhost:8545
   * 2. If connection fails, start new node
   * 
   * @param {boolean} useExisting - Try to use existing node first (default: true)
   * @returns {Promise<void>}
   * @throws {Error} If node fails to start within 30 seconds
   */
  async startHardhatNode(useExisting = true) {
    // Try to connect to existing node first
    if (useExisting) {
      try {
        const { ethers } = require('hardhat');
        await ethers.provider.getNetwork();
        console.log('✅ Connected to existing Hardhat node');
        this.networkReady = true;
        this.hardhatProcess = null; // Not managed by us
        return;
      } catch (error) {
        console.log('ℹ️ No existing node found, starting new one...');
      }
    }
    
    console.log('🚀 Starting Hardhat node...');
    
    return new Promise((resolve, reject) => {
      // Start Hardhat node as separate process
      this.hardhatProcess = spawn('npx', ['hardhat', 'node'], {
        stdio: 'pipe',
        cwd: path.join(__dirname, '../../..'),
        env: process.env
      });

      // Capture stdout for ready signal
      this.hardhatProcess.stdout.on('data', (data) => {
        const output = data.toString();
        
        // Look for ready signal
        if (output.includes('Started HTTP and WebSocket JSON-RPC server')) {
          this.networkReady = true;
          console.log('✅ Hardhat node ready');
          
          // Wait 1 second for full initialization
          setTimeout(() => resolve(), 1000);
        }
      });

      // Log errors but don't fail immediately (some warnings are OK)
      this.hardhatProcess.stderr.on('data', (data) => {
        const error = data.toString();
        // Only log if it's not a common warning
        if (!error.includes('ExperimentalWarning')) {
          console.warn(`⚠️ Hardhat stderr: ${error}`);
        }
      });

      // Handle process exit
      this.hardhatProcess.on('exit', (code) => {
        if (code !== 0 && code !== null) {
          console.error(`❌ Hardhat node exited with code ${code}`);
        }
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (!this.networkReady) {
          this.stopHardhatNode();
          reject(new Error('Hardhat node start timeout (30s)'));
        }
      }, 30000);
    });
  }

  /**
   * Stop Hardhat node
   */
  async stopHardhatNode() {
    if (this.hardhatProcess) {
      console.log('🛑 Stopping Hardhat node...');
      this.hardhatProcess.kill('SIGTERM');
      
      // Wait for graceful shutdown
      await new Promise(resolve => {
        this.hardhatProcess.on('exit', () => {
          console.log('✅ Hardhat node stopped');
          resolve();
        });
        
        // Force kill after 5 seconds
        setTimeout(() => {
          if (this.hardhatProcess) {
            this.hardhatProcess.kill('SIGKILL');
          }
          resolve();
        }, 5000);
      });
      
      this.hardhatProcess = null;
      this.networkReady = false;
    }
  }

  /**
   * Reset network to clean state using EVM snapshot/revert
   * 
   * Uses Hardhat's evm_snapshot and evm_revert RPC methods.
   * This is much faster than restarting the node.
   */
  async resetNetwork() {
    const { ethers } = require('hardhat');
    
    if (this.snapshotId) {
      // Revert to previous snapshot
      await ethers.provider.send('evm_revert', [this.snapshotId]);
    }
    
    // Create new snapshot for next reset
    this.snapshotId = await ethers.provider.send('evm_snapshot', []);
  }

  /**
   * Load test environment variables
   * 
   * Loads e2e.test.env without affecting production .env
   * 
   * @param {Object} overrides - Additional env vars to override
   */
  loadTestEnv(overrides = {}) {
    // Check if test env file exists
    if (!fs.existsSync(this.testEnvPath)) {
      throw new Error(`Test env file not found: ${this.testEnvPath}`);
    }
    
    // Load test environment with override
    require('dotenv').config({ 
      path: this.testEnvPath, 
      override: true 
    });
    
    // Apply additional overrides
    Object.keys(overrides).forEach(key => {
      process.env[key] = overrides[key];
    });
  }

  /**
   * Restore original environment
   */
  restoreEnv() {
    process.env = { ...this.originalEnv };
  }

  /**
   * Save named state snapshot
   * 
   * @param {string} name - Snapshot name
   * @returns {Promise<string>} Snapshot ID
   */
  async saveState(name) {
    const { ethers } = require('hardhat');
    
    const snapshotId = await ethers.provider.send('evm_snapshot', []);
    
    if (!this.namedSnapshots) {
      this.namedSnapshots = {};
    }
    
    this.namedSnapshots[name] = snapshotId;
    
    console.log(`💾 State saved: ${name} (ID: ${snapshotId})`);
    
    return snapshotId;
  }

  /**
   * Restore to named state snapshot
   * 
   * @param {string} name - Snapshot name
   * @returns {Promise<string>} New snapshot ID
   */
  async restoreState(name) {
    const { ethers } = require('hardhat');
    
    if (!this.namedSnapshots || !this.namedSnapshots[name]) {
      throw new Error(`Snapshot '${name}' not found`);
    }
    
    const snapshotId = this.namedSnapshots[name];
    
    // Revert to named snapshot
    await ethers.provider.send('evm_revert', [snapshotId]);
    
    // Create new snapshot with same name
    const newSnapshotId = await ethers.provider.send('evm_snapshot', []);
    this.namedSnapshots[name] = newSnapshotId;
    
    console.log(`🔄 State restored: ${name} (new ID: ${newSnapshotId})`);
    
    return newSnapshotId;
  }

  /**
   * Execute deploy_full.js Action
   * 
   * @param {number} action - Action number (0, 1, 555, 777, 888, etc)
   * @param {Object} envOverrides - Additional env vars for this action
   * @returns {Promise<any>} Result from action execution
   */
  async executeAction(action, envOverrides = {}) {
    // Load test environment
    this.loadTestEnv(envOverrides);
    
    // Import deploy_full router
    const { main } = require('../../deploy_full_new.js');
    
    // Execute action
    const result = await main(action);
    
    return result;
  }

  /**
   * Validate contract deployed correctly
   * 
   * @param {string} contractAddress - Contract address to validate
   * @returns {Promise<Object>} Validation result
   */
  async validateDeployment(contractAddress) {
    const { ethers } = require('hardhat');
    
    const code = await ethers.provider.getCode(contractAddress);
    
    return {
      deployed: code !== '0x' && code !== '0x0',
      codeLength: code.length,
      address: contractAddress
    };
  }

  /**
   * Get contract state from blockchain
   * 
   * @param {string} contractAddress - Contract address
   * @param {Array} abi - Contract ABI
   * @param {string} method - Method to call
   * @param {...any} args - Method arguments
   * @returns {Promise<any>} Method result
   */
  async getContractState(contractAddress, abi, method, ...args) {
    const { ethers } = require('hardhat');
    
    const contract = new ethers.Contract(
      contractAddress,
      abi,
      ethers.provider
    );
    
    return await contract[method](...args);
  }

  /**
   * Wait for transaction to be mined
   * 
   * @param {string} txHash - Transaction hash
   * @returns {Promise<Object>} Transaction receipt
   */
  async waitForTransaction(txHash) {
    const { ethers } = require('hardhat');
    
    const receipt = await ethers.provider.waitForTransaction(txHash);
    return receipt;
  }

  /**
   * Get current block number
   * 
   * @returns {Promise<number>}
   */
  async getCurrentBlock() {
    const { ethers } = require('hardhat');
    
    return await ethers.provider.getBlockNumber();
  }

  /**
   * Get account balance
   * 
   * @param {string} address - Account address
   * @returns {Promise<string>} Balance in wei
   */
  async getBalance(address) {
    const { ethers } = require('hardhat');
    
    const balance = await ethers.provider.getBalance(address);
    return balance.toString();
  }

  // ===== PHASE 1: DEPLOY VALIDATION METHODS =====

  /**
   * Validate UUPS deployment (Proxy + Logic pattern)
   * 
   * @param {string} proxyAddress - Proxy contract address
   * @param {string} logicAddress - Logic contract address (optional check)
   * @returns {Promise<Object>} Validation result
   */
  async validateUUPSDeployment(proxyAddress, logicAddress = null) {
    const { ethers } = require('hardhat');
    
    // Validate Proxy deployed
    const proxyCode = await ethers.provider.getCode(proxyAddress);
    if (proxyCode === '0x' || proxyCode === '0x0') {
      throw new Error(`Proxy not deployed at ${proxyAddress}`);
    }
    
    // Validate Logic deployed (if address provided)
    if (logicAddress) {
      const logicCode = await ethers.provider.getCode(logicAddress);
      if (logicCode === '0x' || logicCode === '0x0') {
        throw new Error(`Logic not deployed at ${logicAddress}`);
      }
    }
    
    // Get implementation address from Proxy (EIP-1967 storage slot)
    const implementationSlot = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc';
    const implementationAddress = await ethers.provider.getStorage(proxyAddress, implementationSlot);
    const actualImplementation = '0x' + implementationAddress.slice(26); // Extract address from bytes32
    
    const result = {
      proxyDeployed: proxyCode !== '0x',
      proxyCodeSize: proxyCode.length,
      logicDeployed: logicAddress ? await ethers.provider.getCode(logicAddress) !== '0x' : null,
      implementation: actualImplementation,
      implementationMatches: logicAddress ? actualImplementation.toLowerCase() === logicAddress.toLowerCase() : null
    };
    
    console.log(`✓ UUPS validated: Proxy ${proxyAddress} → Logic ${actualImplementation}`);
    
    return result;
  }

  /**
   * Get Proxy implementation address
   * 
   * @param {string} proxyAddress - Proxy contract address
   * @returns {Promise<string>} Implementation address
   */
  async getProxyImplementation(proxyAddress) {
    const { ethers } = require('hardhat');
    
    // EIP-1967: Implementation storage slot
    const implementationSlot = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc';
    const implementationData = await ethers.provider.getStorage(proxyAddress, implementationSlot);
    
    // Extract address from bytes32 (last 20 bytes)
    const implementation = '0x' + implementationData.slice(26);
    
    return implementation;
  }

  /**
   * Validate contract registered in MagicRegistry
   * 
   * @param {string} registryAddress - MagicRegistry address
   * @param {string} contractName - Contract name
   * @param {string} expectedAddress - Expected contract address
   * @returns {Promise<Object>} Validation result
   */
  async validateRegistryEntry(registryAddress, contractName, expectedAddress) {
    const { ethers } = require('hardhat');
    
    // Load MagicRegistry ABI
    const MagicRegistryArtifact = require('../../../artifacts/contracts/MagicRegistry.sol/MagicRegistry.json');
    
    const registry = new ethers.Contract(
      registryAddress,
      MagicRegistryArtifact.abi,
      ethers.provider
    );
    
    // Get registered address
    const registeredAddress = await registry.get(contractName);
    
    const result = {
      contractName,
      registered: registeredAddress !== ethers.ZeroAddress,
      registeredAddress,
      expectedAddress,
      matches: registeredAddress.toLowerCase() === expectedAddress.toLowerCase()
    };
    
    if (!result.matches) {
      throw new Error(
        `Registry mismatch for ${contractName}: expected ${expectedAddress}, got ${registeredAddress}`
      );
    }
    
    console.log(`✓ Registry validated: ${contractName} → ${registeredAddress}`);
    
    return result;
  }

  /**
   * Get full deployment state (all deployed contracts)
   * 
   * @returns {Promise<Object>} Deployment state snapshot
   */
  async getDeploymentState() {
    const { ethers } = require('hardhat');
    
    const blockNumber = await ethers.provider.getBlockNumber();
    const [deployer] = await ethers.getSigners();
    const deployerBalance = await ethers.provider.getBalance(deployer.address);
    
    // Try to load known contract addresses from env
    const knownContracts = {
      magicRegistry: process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS,
      spiralEngine: process.env.SPIRAL_ENGINE_PROXY_ADDRESS || process.env.SPIRAL_ENGINE_CONTRACT_ADDRESS,
      productRegistry: process.env.PRODUCT_REGISTRY_PROXY_ADDRESS || process.env.PRODUCT_REGISTRY_CONTRACT_ADDRESS,
      organicComponentRegistry: process.env.ORGANIC_COMPONENT_REGISTRY_PROXY,
      amanitaInternational: process.env.AMANITA_INTERNATIONAL_PROXY,
      soulIdentity: process.env.SOUL_IDENTITY_CONTRACT_ADDRESS
    };
    
    // Check which contracts are actually deployed
    const deployedContracts = {};
    for (const [name, address] of Object.entries(knownContracts)) {
      if (address && address !== '') {
        const code = await ethers.provider.getCode(address);
        if (code !== '0x' && code !== '0x0') {
          deployedContracts[name] = {
            address,
            codeSize: code.length
          };
        }
      }
    }
    
    const state = {
      blockNumber,
      deployer: {
        address: deployer.address,
        balance: ethers.formatEther(deployerBalance)
      },
      contractsDeployed: Object.keys(deployedContracts).length,
      contracts: deployedContracts
    };
    
    console.log(`📊 Deployment state: ${state.contractsDeployed} contracts, block ${state.blockNumber}`);
    
    return state;
  }

  /**
   * Execute deploy action via DeployRouter
   * 
   * @param {number} actionNumber - Action number (0, 1, 2, etc.)
   * @param {Object} envOverrides - Environment variable overrides
   * @returns {Promise<Object>} Action execution result
   */
  async executeAction(actionNumber, envOverrides = {}) {
    // Load test environment (if not already loaded)
    this.loadTestEnv(envOverrides);
    
    // Import deploy_full_new.js main function
    const { main } = require('../../deploy_full_new');
    
    // Execute action
    const result = await main(actionNumber);
    
    return result;
  }

  // ===== PERFORMANCE MEASUREMENT =====

  /**
   * Measure execution time for an operation
   * 
   * @param {string} operationName - Name of operation being measured
   * @returns {Object} Timer object with end() method
   */
  measureExecutionTime(operationName) {
    const startTime = Date.now();
    
    return {
      end: () => {
        const duration = Date.now() - startTime;
        console.log(`⏱️ ${operationName}: ${duration}ms (${(duration / 1000).toFixed(2)}s)`);
        return duration;
      }
    };
  }

  /**
   * Measure gas usage for a transaction
   * 
   * @param {string} txHash - Transaction hash
   * @returns {Promise<string>} Gas used
   */
  async measureGasUsage(txHash) {
    const { ethers } = require('hardhat');
    
    const receipt = await ethers.provider.getTransactionReceipt(txHash);
    if (!receipt) {
      throw new Error(`Transaction not found: ${txHash}`);
    }
    
    const gasUsed = receipt.gasUsed.toString();
    console.log(`⛽ Gas used: ${gasUsed}`);
    
    return gasUsed;
  }

  // ===== PHASE 2: COMPONENT VALIDATION METHODS =====

  /**
   * Validate seller activation on-chain
   * 
   * @param {string} spiralEngineAddress - SpiralEngine contract address
   * @param {string} sellerAddress - Seller address to check
   * @returns {Promise<Object>} Validation result
   */
  async validateSellerActivation(spiralEngineAddress, sellerAddress) {
    const { ethers } = require('hardhat');
    
    const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', spiralEngineAddress);
    
    // Check if seller is activated (has used invite)
    const usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
    const isActivated = usedInvite > 0n;
    
    // Check if seller has SELLER_ROLE
    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
    const hasRole = await SpiralEngine.hasRole(SELLER_ROLE, sellerAddress);
    
    const result = {
      activated: isActivated,
      usedInviteId: usedInvite.toString(),
      hasSellerRole: hasRole,
      sellerAddress
    };
    
    console.log(`✓ Seller validation: activated=${isActivated}, role=${hasRole}`);
    
    return result;
  }

  /**
   * Validate invite codes generated
   * 
   * @param {Array<string>} inviteCodes - Array of invite codes to validate
   * @returns {Promise<Object>} Validation result
   */
  async validateInviteCodes(inviteCodes) {
    const result = {
      count: inviteCodes.length,
      allValid: true,
      codes: inviteCodes
    };
    
    // Validate format (alphanumeric, specific length)
    for (const code of inviteCodes) {
      if (!/^[A-Z0-9-]+$/.test(code)) {
        result.allValid = false;
        break;
      }
    }
    
    // Check uniqueness
    const uniqueCodes = new Set(inviteCodes);
    if (uniqueCodes.size !== inviteCodes.length) {
      result.allValid = false;
    }
    
    console.log(`✓ Invite codes validated: ${result.count} codes, unique=${result.allValid}`);
    
    return result;
  }

  /**
   * Validate component registration on-chain
   * 
   * @param {string} registryAddress - OrganicComponentRegistry address
   * @param {string} componentId - Component ID
   * @param {string} ownerAddress - Expected owner address
   * @returns {Promise<Object>} Validation result
   */
  async validateComponentRegistration(registryAddress, componentId, ownerAddress) {
    const { ethers } = require('hardhat');
    
    const ComponentRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', registryAddress);
    
    // Check if component exists
    const exists = await ComponentRegistry.componentExists(componentId);
    
    let owner = null;
    if (exists) {
      owner = await ComponentRegistry.getComponentOwner(componentId);
    }
    
    const result = {
      componentId,
      exists,
      owner,
      ownerMatches: owner ? owner.toLowerCase() === ownerAddress.toLowerCase() : false
    };
    
    console.log(`✓ Component validated: ${componentId}, exists=${exists}, owner=${owner}`);
    
    return result;
  }

  /**
   * Get component state from registry
   * 
   * @param {string} registryAddress - OrganicComponentRegistry address
   * @param {string} componentId - Component ID
   * @returns {Promise<Object>} Component state
   */
  async getComponentState(registryAddress, componentId) {
    const { ethers } = require('hardhat');
    
    const ComponentRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', registryAddress);
    
    const exists = await ComponentRegistry.componentExists(componentId);
    
    if (!exists) {
      return {
        exists: false,
        componentId
      };
    }
    
    const owner = await ComponentRegistry.getComponentOwner(componentId);
    const cid = await ComponentRegistry.getComponentCID(componentId);
    
    const state = {
      exists: true,
      componentId,
      owner,
      cid
    };
    
    console.log(`📊 Component state: ${componentId} owned by ${owner}`);
    
    return state;
  }
}

module.exports = E2EHarness;

