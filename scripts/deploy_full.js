/**
 * Deploy Full Script - Modular Router
 * 
 * This is the new modular version of deploy_full.js that replaces the monolithic
 * 4760-line script with a clean, modular architecture.
 * 
 * Architecture:
 * - Config: Centralized configuration management
 * - Logger: Structured logging with level control
 * - Services: ContractManager, ArweaveManager
 * - Utils: Web3Utils for common operations
 * - Actions: DeployActions, CatalogActions, ComponentActions
 * - Core: CoreLogic for shared business logic
 * 
 * @version 2.0.0
 * @date 2025-10-14
 */

// Load environment variables from scripts/.env (same as hardhat.config.js)
const path = require('path');
const { SCRIPTS_DOTENV_PATH } = require('./lib/env-path');
require('dotenv').config({ path: SCRIPTS_DOTENV_PATH });

// Import all modules
const config = require('./lib/config/index');
const logger = require('./lib/utils/Logger');
const { ethers } = require('hardhat');
const ContractManager = require('./lib/services/ContractManager');
const ArweaveManager = require('./lib/services/ArweaveManager');
const EthersUtils = require('./lib/utils/EthersUtils');
const { ActionsManager } = require('./lib/actions/index');
const { CoreManager } = require('./lib/core/index');
const RpcProviderManager = require('./lib/utils/RpcProviderManager');
const readline = require('readline');

function parseCliAddressArg(argv) {
  const addressFlagIndex = argv.findIndex((arg) => arg === '--address' || arg === '-a');
  if (addressFlagIndex !== -1 && argv[addressFlagIndex + 1]) {
    return argv[addressFlagIndex + 1];
  }

  const afterDoubleDash = argv.indexOf('--');
  if (afterDoubleDash !== -1) {
    const candidate = argv[afterDoubleDash + 1];
    if (candidate && !candidate.startsWith('-')) return candidate;
  }

  return null;
}

async function askAddressFromStdin() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const answer = await new Promise((resolve) => {
    rl.question('Введите адрес для диагностики Action 13: ', resolve);
  });
  rl.close();
  return (answer || '').trim();
}

/**
 * Main Deploy Router Class
 * 
 * This class orchestrates all deployment operations using the modular architecture.
 * It replaces the monolithic deploy_full.js with a clean, maintainable structure.
 */
class DeployRouter {
  constructor() {
    this.config = config;
    this.logger = logger;
    this.provider = null;
    this.contractManager = null;
    this.arweaveManager = null;
    this.ethersUtils = null;
    this.actionsManager = null;
    this.coreManager = null;
    this.rpcManager = null;
    this.initialized = false;
  }

  /**
   * Initialize the router with all dependencies
   * @returns {Promise<void>}
   */
  async initialize() {
    try {
      this.logger.section('Initializing Deploy Router');
      
      // Initialize Provider
      await this.initializeProvider();
      
      // Initialize managers
      this.ethersUtils = new EthersUtils(this.provider, this.config);
      this.contractManager = new ContractManager(this.provider, this.config, this.ethersUtils, this.rpcManager);
      this.arweaveManager = new ArweaveManager(this.config);
      
      // Initialize action and core managers
      this.actionsManager = new ActionsManager(
        this.contractManager,
        this.arweaveManager,
        this.ethersUtils,
        this.config
      );
      
      this.coreManager = new CoreManager(
        this.contractManager,
        this.ethersUtils,
        this.config
      );
      
      this.initialized = true;
      this.logger.success('Deploy Router initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize Deploy Router:', error.message);
      throw error;
    }
  }

  /**
   * Initialize Provider connection
   * Uses Hardhat's ethers.provider (respects --network flag), falls back to env vars
   * @returns {Promise<void>}
   */
  async initializeProvider() {
    try {
      const hre = require('hardhat');
      let provider;
      let rpcUrl;
      let networkName;
      let providerSource;
      
      // Try to use Hardhat's ethers.provider first (respects --network flag)
      // This is the standard approach used throughout the codebase
      try {
        // ethers is already imported at the top, but we need to ensure it's from hardhat
        provider = ethers.provider;
        networkName = hre.network?.name || 'unknown';
        rpcUrl = hre.network?.config?.url || 'unknown';
        providerSource = 'Hardhat ethers.provider';
        
        this.logger.info(`[NETWORK] Using Hardhat ethers.provider for network: '${networkName}'`);
        this.logger.debug(`[DEBUG] Network configuration from Hardhat:`);
        this.logger.debug(`  - Network name: ${networkName}`);
        this.logger.debug(`  - RPC URL: ${rpcUrl}`);
        this.logger.debug(`  - Chain ID (from config): ${hre.network?.config?.chainId || 'unknown'}`);
      } catch (hardhatError) {
        // Fallback: create provider from config or env
        this.logger.warn(`[NETWORK] Hardhat ethers.provider not available, using fallback`);
        this.logger.debug(`[DEBUG] Hardhat error: ${hardhatError.message}`);
        
        // Try to get RPC URL from Hardhat config for the requested network
        if (hre.network && hre.network.name && hre.config?.networks?.[hre.network.name]) {
          const networkConfig = hre.config.networks[hre.network.name];
          if (networkConfig.url) {
            rpcUrl = networkConfig.url;
            networkName = hre.network.name;
            providerSource = `Hardhat config (${networkName})`;
            this.logger.debug(`[DEBUG] Using RPC URL from hardhat.config.js for network '${networkName}'`);
          }
        }
        
        // If still no RPC URL, try env vars
        if (!rpcUrl || rpcUrl === 'unknown') {
          rpcUrl = process.env.RPC_URL || process.env.WEB3_PROVIDER_URI || 'http://localhost:8545';
          providerSource = 'Environment variables or fallback';
          this.logger.debug(`[DEBUG] RPC URL sources (fallback):`);
          this.logger.debug(`  - RPC_URL: ${process.env.RPC_URL || 'undefined'}`);
          this.logger.debug(`  - WEB3_PROVIDER_URI: ${process.env.WEB3_PROVIDER_URI || 'undefined'}`);
          this.logger.debug(`  - Selected RPC URL: ${rpcUrl}`);
        }
        
        provider = new ethers.JsonRpcProvider(rpcUrl);
      }
      
      this.provider = provider;
      
      // Test connection and get network info
      const network = await this.provider.getNetwork();
      const blockNumber = await this.provider.getBlockNumber();
      
      // Determine currency name based on chain ID
      const chainId = Number(network.chainId);
      const currency = chainId === 137 ? 'MATIC' : chainId === 80001 ? 'MATIC' : chainId === 6281971 ? 'DOGE' : 'ETH';
      
      // Initialize RpcProviderManager for Polygon mainnet
      if (chainId === 137) {
        // Get primary endpoint from config or env
        const primaryEndpoint = hre.network?.config?.url || 
                               process.env.POLYGON_MAINNET_RPC || 
                               null;
        
        // Create RpcProviderManager
        this.rpcManager = new RpcProviderManager(
          networkName,
          chainId,
          this.logger,
          primaryEndpoint
        );
        
        // If no primary endpoint was set, use first from alternatives
        if (!primaryEndpoint) {
          rpcUrl = this.rpcManager.getNextEndpoint();
          provider = this.rpcManager.createProvider(rpcUrl);
          this.provider = provider; // Update provider reference
          this.logger.info(`[RPC] Using RpcProviderManager for Polygon mainnet`);
          this.logger.info(`[RPC] Initial endpoint: ${rpcUrl}`);
        } else {
          // Primary endpoint was set, use it
          rpcUrl = primaryEndpoint;
          this.logger.info(`[RPC] Using primary endpoint from config: ${primaryEndpoint}`);
        }
      }
      
      // Get RPC URL for logging (if not already set)
      if (!rpcUrl || rpcUrl === 'unknown') {
        // Try to extract from provider connection
        if (this.provider.connection) {
          rpcUrl = typeof this.provider.connection === 'string' 
            ? this.provider.connection 
            : this.provider.connection.url || 'unknown';
        } else if (this.provider._getConnection) {
          const conn = this.provider._getConnection();
          rpcUrl = typeof conn === 'string' ? conn : conn?.url || 'unknown';
        }
      }
      
      // Log comprehensive network information
      this.logger.info(`[NETWORK] Connected to network`);
      this.logger.info(`  - Network name: ${networkName || network.name || 'unknown'}`);
      this.logger.info(`  - Chain ID: ${chainId}`);
      this.logger.info(`  - Currency: ${currency}`);
      this.logger.info(`  - Current block: ${blockNumber}`);
      this.logger.info(`  - Provider source: ${providerSource}`);
      this.logger.info(`  - RPC URL: ${rpcUrl}`);
      
      // Verify chain ID matches expected for known networks
      if (networkName === 'polygon' && chainId !== 137) {
        this.logger.warn(`[WARNING] Expected Polygon mainnet (Chain ID 137), but connected to Chain ID ${chainId}`);
      } else if (networkName === 'mumbai' && chainId !== 80001) {
        this.logger.warn(`[WARNING] Expected Mumbai testnet (Chain ID 80001), but connected to Chain ID ${chainId}`);
      } else if (networkName === 'dogetestnet' && chainId !== 6281971) {
        this.logger.warn(`[WARNING] Expected DogeOS Chikyu testnet (Chain ID 6281971), but connected to Chain ID ${chainId}`);
      } else if (networkName === 'localhost' && chainId !== 31337) {
        this.logger.warn(`[WARNING] Expected localhost (Chain ID 31337), but connected to Chain ID ${chainId}`);
      }
      
      this.logger.debug(`[DEBUG] Full network details:`);
      this.logger.debug(`  - Chain ID: ${chainId}`);
      this.logger.debug(`  - Network name: ${networkName || network.name || 'unknown'}`);
      this.logger.debug(`  - RPC URL: ${rpcUrl}`);
      this.logger.debug(`  - Block number: ${blockNumber}`);
      this.logger.debug(`  - Currency: ${currency}`);
      this.logger.debug(`  - Provider type: ${provider.constructor.name}`);
    } catch (error) {
      this.logger.error('Failed to initialize Provider:', error.message);
      this.logger.error(`[ERROR] Provider initialization failed. Check:`);
      this.logger.error(`  - Network configuration in hardhat.config.js`);
      this.logger.error(`  - RPC_URL or WEB3_PROVIDER_URI environment variables`);
      this.logger.error(`  - Network connectivity`);
      this.logger.error(`  - Error details: ${error.stack || 'No stack trace'}`);
      throw error;
    }
  }

  /**
   * Route action to appropriate handler
   * @param {number} action - Action number to execute
   * @param {Object} options - Optional parameters (e.g. { contractName } for action 5)
   * @returns {Promise<Object>} - Action result
   */
  async route(action, options = {}) {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      this.logger.info(`Routing action: ${action}`);
      const result = await this.actionsManager.executeAction(action, options);
      this.logger.info(`Action ${action} completed successfully`);
      return result;
    } catch (error) {
      this.logger.error(`Action ${action} failed:`, error.message);
      throw error;
    }
  }

  /**
   * Get available actions
   * @returns {Array} - List of available actions
   */
  getAvailableActions() {
    return this.actionsManager ? this.actionsManager.getAvailableActions() : [];
  }

  /**
   * Get action description
   * @param {number} action - Action number
   * @returns {string} - Action description
   */
  getActionDescription(action) {
    return this.actionsManager ? this.actionsManager.getActionDescription(action) : 'Unknown action';
  }

  /**
   * Get router status
   * @returns {Object} - Router status information
   */
  getStatus() {
    return {
      initialized: this.initialized,
      providerConnected: this.provider !== null,
      contractManagerReady: this.contractManager !== null,
      arweaveManagerReady: this.arweaveManager !== null,
      ethersUtilsReady: this.ethersUtils !== null,
      actionsManagerReady: this.actionsManager !== null,
      coreManagerReady: this.coreManager !== null,
      availableActions: this.getAvailableActions()
    };
  }
}

/**
 * Main function - entry point for the script
 * @param {number} action - Action number to execute
 * @param {Object} options - Optional (e.g. DEPLOY_CONTRACT for action 5)
 * @returns {Promise<void>}
 */
async function main(action, options = {}) {
  try {
    const router = new DeployRouter();
    await router.route(action, options);
  } catch (error) {
    logger.error('Main function failed:', error.message);
    process.exit(1);
  }
}

/**
 * CLI interface
 */
if (require.main === module) {
  const runCli = async () => {
  // 🔍 DEBUG: Set log level from environment
  const logLevel = process.env.LOG_LEVEL || process.env.DEBUG ? 'debug' : 'info';
  logger.setLevel(logLevel);
  
  if (logLevel === 'debug') {
    logger.debug('[DEBUG] Debug logging enabled via LOG_LEVEL=debug or DEBUG environment variable');
  }
  
  const action = process.env.DEPLOY_ACTION ? parseInt(process.env.DEPLOY_ACTION) : null;
  // Action 5: deploy/upgrade UUPS contract. Requires DEPLOY_CONTRACT (e.g. SpiralEngine).
  // Upgrade: DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine npx hardhat run scripts/deploy_full.js --network polygon
  const contractName = process.env.DEPLOY_CONTRACT;
  const cliAddress = parseCliAddressArg(process.argv);
  if (action === 5 && !contractName) {
    logger.error('For action 5, DEPLOY_CONTRACT is required (e.g. DEPLOY_CONTRACT=SpiralEngine)');
    logger.info('Example: DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine npx hardhat run scripts/deploy_full.js --network polygon');
    process.exit(1);
  }
  let validatedAddress = process.env.VALIDATED_ADDRESS || cliAddress || null;
  if (action === 13 && !validatedAddress && process.env.ASK_FOR_ADDRESS === 'true') {
    if (!process.stdin.isTTY) {
      logger.error('ASK_FOR_ADDRESS=true requires interactive TTY. Use VALIDATED_ADDRESS in non-interactive mode.');
      process.exit(1);
    }
    validatedAddress = await askAddressFromStdin();
  }

  const options = {};
  if (action === 5) options.contractName = contractName;
  if (action === 13 && validatedAddress) options.validatedAddress = validatedAddress;
  if (!action) {
    logger.error('DEPLOY_ACTION environment variable is required');
    logger.info('Available actions:');
    const router = new DeployRouter();
    router.initialize().then(() => {
      const actions = router.getAvailableActions();
      actions.forEach(actionNum => {
        logger.info(`  ${actionNum}: ${router.getActionDescription(actionNum)}`);
      });
      process.exit(1);
    }).catch(() => {
      process.exit(1);
    });
    return;
  }

  main(action, options).catch(error => {
    logger.error('Script execution failed:', error.message);
    process.exit(1);
  });
  };

  runCli().catch((error) => {
    logger.error('CLI initialization failed:', error.message);
    process.exit(1);
  });
}

// Export for use as module
module.exports = {
  DeployRouter,
  main
};
