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

// Load environment variables
require('dotenv').config();

// Import all modules
const config = require('./lib/config/index');
const logger = require('./lib/utils/Logger');
const { ethers } = require('hardhat');
const ContractManager = require('./lib/services/ContractManager');
const ArweaveManager = require('./lib/services/ArweaveManager');
const EthersUtils = require('./lib/utils/EthersUtils');
const { ActionsManager } = require('./lib/actions/index');
const { CoreManager } = require('./lib/core/index');

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
      this.contractManager = new ContractManager(this.provider, this.config, this.ethersUtils);
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
   * @returns {Promise<void>}
   */
  async initializeProvider() {
    try {
      // Determine RPC URL: try RPC_URL, then WEB3_PROVIDER_URI, then use Hardhat network
      const rpcUrl = process.env.RPC_URL || process.env.WEB3_PROVIDER_URI || 'http://localhost:8545';
      this.logger.debug(`[DEBUG] RPC URL sources:`);
      this.logger.debug(`  - RPC_URL: ${process.env.RPC_URL || 'undefined'}`);
      this.logger.debug(`  - WEB3_PROVIDER_URI: ${process.env.WEB3_PROVIDER_URI || 'undefined'}`);
      this.logger.debug(`  - Selected RPC URL: ${rpcUrl}`);
      
      this.provider = new ethers.JsonRpcProvider(rpcUrl);
      
      // Test connection
      const network = await this.provider.getNetwork();
      const blockNumber = await this.provider.getBlockNumber();
      
      this.logger.info(`Connected to network: ${network.chainId}`);
      this.logger.info(`Current block: ${blockNumber}`);
      this.logger.debug(`[DEBUG] Network details:`);
      this.logger.debug(`  - Chain ID: ${network.chainId}`);
      this.logger.debug(`  - RPC URL: ${rpcUrl}`);
      this.logger.debug(`  - Block number: ${blockNumber}`);
    } catch (error) {
      this.logger.error('Failed to initialize Provider:', error.message);
      throw error;
    }
  }

  /**
   * Route action to appropriate handler
   * @param {number} action - Action number to execute
   * @returns {Promise<Object>} - Action result
   */
  async route(action) {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      this.logger.info(`Routing action: ${action}`);
      
      // Execute action through ActionsManager
      const result = await this.actionsManager.executeAction(action);
      
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
 * @returns {Promise<void>}
 */
async function main(action) {
  try {
    const router = new DeployRouter();
    await router.route(action);
  } catch (error) {
    logger.error('Main function failed:', error.message);
    process.exit(1);
  }
}

/**
 * CLI interface
 */
if (require.main === module) {
  // 🔍 DEBUG: Set log level from environment
  const logLevel = process.env.LOG_LEVEL || process.env.DEBUG ? 'debug' : 'info';
  logger.setLevel(logLevel);
  
  if (logLevel === 'debug') {
    logger.debug('[DEBUG] Debug logging enabled via LOG_LEVEL=debug or DEBUG environment variable');
  }
  
  const action = process.env.DEPLOY_ACTION ? parseInt(process.env.DEPLOY_ACTION) : null;
  
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

  main(action).catch(error => {
    logger.error('Script execution failed:', error.message);
    process.exit(1);
  });
}

// Export for use as module
module.exports = {
  DeployRouter,
  main
};
