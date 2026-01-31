/**
 * Deploy Actions Module
 * 
 * This module handles all deployment-related actions from deploy_full.js,
 * centralizing contract deployment logic.
 * 
 * Setup connections delegated to SetupActions for clean architecture.
 */

const logger = require('../utils/Logger');
const SetupActions = require('./SetupActions');
const { CONTRACT_ENV_MAPPING } = require('../config/constants');

class DeployActions {
  constructor(contractManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    
    // Делегируем setup operations в SetupActions
    this.setupActions = new SetupActions(contractManager, ethersUtils, config);
  }

  /**
   * Action 5: Deploy or Upgrade UUPS Contract by Name
   * - Contract name from input (arg, DEPLOY_CONTRACT env, or deployment.contractName)
   * - If contract exists (address in config) and is UUPS → upgrade via upgradeToAndCall
   * - If contract does not exist → fresh deploy (Logic + Proxy)
   *
   * @param {string} contractName - Contract name (SpiralEngine, ProductRegistry, etc.)
   * @returns {Promise<Object>} - Deployment/upgrade result
   */
  async action5(contractName) {
    const uupsContracts = ['SpiralEngine', 'ProductRegistry', 'OrganicComponentRegistry', 'AmanitaInternational', 'ActivityRegistry'];

    contractName = contractName || process.env.DEPLOY_CONTRACT || this.config.get?.('deployment.contractName');
    if (!contractName) {
      throw new Error(
        'Contract name not provided. Use: DEPLOY_ACTION=5 DEPLOY_CONTRACT=SpiralEngine npx hardhat run scripts/deploy_full.js --network polygon'
      );
    }

    logger.action(5, `Deploy/upgrade contract: ${contractName}`);

    try {
      let magicRegistry = null;
      try {
        magicRegistry = await this.contractManager.loadContract('MagicRegistry');
        logger.info(`MagicRegistry loaded: ${await magicRegistry.getAddress()}`);
      } catch (error) {
        logger.warn('MagicRegistry not found - contract will not be registered');
      }

      const existing = await this.contractManager.checkExistingContract(contractName);
      const isUUPS = uupsContracts.includes(contractName);

      let contract;
      if (existing && isUUPS) {
        logger.info(`UUPS contract ${contractName} exists - upgrading Logic...`);
        contract = await this.contractManager.upgradeUUPSContract(contractName, {});
      } else if (existing) {
        logger.info(`Contract ${contractName} already exists at ${await existing.getAddress()} (not UUPS - skipping upgrade)`);
        contract = existing;
      } else {
        logger.info(`Deploying ${contractName}...`);
        contract = await this.contractManager.deploySingleContract(contractName, { registry: magicRegistry });
      }

      const address = await contract.getAddress();
      logger.info(`${contractName} at: ${address}`);

      const envVarName = CONTRACT_ENV_MAPPING[contractName] || `${contractName.toUpperCase()}_CONTRACT_ADDRESS`;
      console.log('');
      console.log(`${envVarName}=${address}`);
      console.log('');

      logger.success(5);
      return {
        success: true,
        contractName,
        contract,
        address,
        upgraded: existing && isUUPS
      };
    } catch (error) {
      logger.failure(5, error.message);
      throw error;
    }
  }
  
  /**
   * Action 0: Deploy MagicRegistry
   * @returns {Promise<Object>} - Deployment result
   */
  async action0() {
    logger.action(0, "Deploy MagicRegistry");
    
    try {
      const magicRegistry = await this.contractManager.deploySingleContract('MagicRegistry', {
        constructorArgs: [],
        isUUPS: false
      });

      // Print address for .env
      const address = await magicRegistry.getAddress();
      console.log("");
      console.log(`MAGIC_REGISTRY_CONTRACT_ADDRESS=${address}`);
      console.log("");

      logger.success(0);
      return {
        success: true,
        contract: magicRegistry,
        address: address
      };
    } catch (error) {
      logger.failure(0, error.message);
      throw error;
    }
  }

  /**
   * Action 1: Deploy all contracts
   * @returns {Promise<Object>} - Deployment result
   */
  async action1() {
    logger.action(1, "Deploy all contracts");
    
    try {
      const contracts = {};
      
      // Get network info to determine delay (mainnet needs longer delays for rate limits)
      let delayMs = 500; // Default delay for localhost/testnet
      try {
        const network = await this.ethersUtils.provider.getNetwork();
        const chainId = Number(network.chainId);
        // Polygon mainnet (137) needs longer delays to avoid rate limits
        if (chainId === 137) {
          delayMs = 2000; // 2 seconds for Polygon mainnet
          logger.debug(`[NETWORK] Detected Polygon mainnet (Chain ID ${chainId}), using ${delayMs}ms delay between contracts`);
        } else if (chainId === 80001) {
          delayMs = 1000; // 1 second for Mumbai testnet
          logger.debug(`[NETWORK] Detected Mumbai testnet (Chain ID ${chainId}), using ${delayMs}ms delay between contracts`);
        }
      } catch (networkError) {
        logger.debug(`[NETWORK] Could not determine network, using default ${delayMs}ms delay`);
      }
      
      // Helper: Wait between contract deployments to prevent nonce conflicts and rate limits
      // IMPORTANT: Define BEFORE using to avoid race conditions!
      const waitForNonce = async () => {
        logger.info(`⏱️ Waiting ${delayMs}ms for nonce update between contracts...`);
        await new Promise(resolve => setTimeout(resolve, delayMs));
      };
      
      // Deploy MagicRegistry first
      contracts.magicRegistry = await this.contractManager.deploySingleContract('MagicRegistry', {
        constructorArgs: [],
        isUUPS: false
      });
      await waitForNonce();

      // Deploy SpiralEngine (UUPS)
      contracts.spiralEngine = await this.contractManager.deploySingleContract('SpiralEngine', {
        isUUPS: true,
        registry: contracts.magicRegistry
      });
      await waitForNonce();

      // Deploy SBT Ecosystem (in dependency order)
      logger.info("Deploying SBT ecosystem...");
      
      // 1. SoulboundCore (no dependencies)
      contracts.soulboundCore = await this.contractManager.deploySingleContract('SoulboundCore', {
        isUUPS: false,
        registry: contracts.magicRegistry
      });
      await waitForNonce();
      
      // 2. SoulMetadata (depends on SoulboundCore)
      contracts.soulMetadata = await this.contractManager.deploySingleContract('SoulMetadata', {
        isUUPS: false,
        registry: contracts.magicRegistry
      });
      await waitForNonce();
      
      // 3. SoulRecovery (depends on SoulboundCore)
      contracts.soulRecovery = await this.contractManager.deploySingleContract('SoulRecovery', {
        isUUPS: false,
        registry: contracts.magicRegistry
      });
      await waitForNonce();
      
      // 4. SoulIntegration (depends on SpiralEngine + SoulboundCore)
      contracts.soulIntegration = await this.contractManager.deploySingleContract('SoulIntegration', {
        isUUPS: false,
        registry: contracts.magicRegistry
      });
      await waitForNonce();
      
      // 5. SoulIdentity (depends on SoulboundCore + SoulMetadata)
      contracts.soulIdentity = await this.contractManager.deploySingleContract('SoulIdentity', {
        isUUPS: false,
        registry: contracts.magicRegistry
      });

      // Deploy ProductRegistry (UUPS)
      await waitForNonce();
      contracts.productRegistry = await this.contractManager.deploySingleContract('ProductRegistry', {
        isUUPS: true,
        registry: contracts.magicRegistry
      });

      // Deploy ActivityRegistry (UUPS)
      await waitForNonce();
      contracts.activityRegistry = await this.contractManager.deploySingleContract('ActivityRegistry', {
        isUUPS: true,
        registry: contracts.magicRegistry
      });

      // Deploy OrganicComponentRegistry (UUPS)
      await waitForNonce();
      contracts.organicComponentRegistry = await this.contractManager.deploySingleContract('OrganicComponentRegistry', {
        isUUPS: true,
        registry: contracts.magicRegistry
      });

      // Deploy AmanitaInternational (UUPS)
      await waitForNonce();
      contracts.amanitaInternational = await this.contractManager.deploySingleContract('AmanitaInternational', {
        isUUPS: true,
        registry: contracts.magicRegistry
      });
      await waitForNonce();

      // ⏱️ CRITICAL: Wait for nonce to settle after all deployments before setup
      logger.info('⏱️ Waiting 1000ms for nonce to settle after all contract deployments...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      logger.info('✅ Nonce settled, proceeding with system connections setup...');

      // Setup all system connections (делегируем в SetupActions)
      await this.setupActions.setupSystemConnections(contracts);

      // Print contract addresses for .env
      await this.printContractAddresses(contracts);

      logger.success(1);
      return {
        success: true,
        contracts: contracts
      };
    } catch (error) {
      logger.failure(1, error.message);
      throw error;
    }
  }

  /**
   * Print contract addresses in .env format
   * @param {Object} contracts - Deployed contracts
   * @returns {Promise<void>}
   */
  async printContractAddresses(contracts) {
    console.log("");
    console.log("=".repeat(70));
    console.log("📋 CONTRACT ADDRESSES (copy to .env)");
    console.log("=".repeat(70));
    console.log("");
    
    // MagicRegistry
    if (contracts.magicRegistry) {
      const addr = await contracts.magicRegistry.getAddress();
      console.log(`MAGIC_REGISTRY_CONTRACT_ADDRESS=${addr}`);
    }
    
    // UUPS Contracts (Proxy + Logic)
    if (contracts.spiralEngine) {
      const proxyAddr = await contracts.spiralEngine.getAddress();
      console.log(`SPIRAL_ENGINE_PROXY_ADDRESS=${proxyAddr}`);
      console.log(`SPIRAL_ENGINE_CONTRACT_ADDRESS=${proxyAddr}`); // Alias for compatibility
      
      const logicAddr = await this.getUUPSImplementationAddress(proxyAddr);
      if (logicAddr) {
        console.log(`SPIRAL_ENGINE_LOGIC_ADDRESS=${logicAddr}`);
      }
    }
    
    if (contracts.productRegistry) {
      const proxyAddr = await contracts.productRegistry.getAddress();
      console.log("");
      console.log(`PRODUCT_REGISTRY_PROXY_ADDRESS=${proxyAddr}`);
      console.log(`PRODUCT_REGISTRY_CONTRACT_ADDRESS=${proxyAddr}`); // Alias
      
      const logicAddr = await this.getUUPSImplementationAddress(proxyAddr);
      if (logicAddr) {
        console.log(`PRODUCT_REGISTRY_LOGIC_ADDRESS=${logicAddr}`);
      }
    }
    
    if (contracts.activityRegistry) {
      const proxyAddr = await contracts.activityRegistry.getAddress();
      console.log("");
      console.log(`ACTIVITY_REGISTRY_PROXY_ADDRESS=${proxyAddr}`);
      console.log(`ACTIVITY_REGISTRY_CONTRACT_ADDRESS=${proxyAddr}`); // Alias
      
      const logicAddr = await this.getUUPSImplementationAddress(proxyAddr);
      if (logicAddr) {
        console.log(`ACTIVITY_REGISTRY_LOGIC_ADDRESS=${logicAddr}`);
      }
    }
    
    if (contracts.organicComponentRegistry) {
      const proxyAddr = await contracts.organicComponentRegistry.getAddress();
      console.log("");
      console.log(`ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS=${proxyAddr}`);
      console.log(`ORGANIC_COMPONENT_REGISTRY_CONTRACT_ADDRESS=${proxyAddr}`); // Alias
      
      const logicAddr = await this.getUUPSImplementationAddress(proxyAddr);
      if (logicAddr) {
        console.log(`ORGANIC_COMPONENT_REGISTRY_LOGIC_ADDRESS=${logicAddr}`);
      }
    }
    
    if (contracts.amanitaInternational) {
      const proxyAddr = await contracts.amanitaInternational.getAddress();
      console.log("");
      console.log(`AMANITA_INTERNATIONAL_PROXY_ADDRESS=${proxyAddr}`);
      console.log(`AMANITA_INTERNATIONAL_CONTRACT_ADDRESS=${proxyAddr}`); // Alias
      
      const logicAddr = await this.getUUPSImplementationAddress(proxyAddr);
      if (logicAddr) {
        console.log(`AMANITA_INTERNATIONAL_LOGIC_ADDRESS=${logicAddr}`);
      }
    }
    
    // SBT Contracts
    if (contracts.soulboundCore) {
      console.log("");
      console.log(`SOULBOUND_CORE_CONTRACT_ADDRESS=${await contracts.soulboundCore.getAddress()}`);
    }
    if (contracts.soulMetadata) {
      console.log(`SOUL_METADATA_CONTRACT_ADDRESS=${await contracts.soulMetadata.getAddress()}`);
    }
    if (contracts.soulRecovery) {
      console.log(`SOUL_RECOVERY_CONTRACT_ADDRESS=${await contracts.soulRecovery.getAddress()}`);
    }
    if (contracts.soulIntegration) {
      console.log(`SOUL_INTEGRATION_CONTRACT_ADDRESS=${await contracts.soulIntegration.getAddress()}`);
    }
    if (contracts.soulIdentity) {
      console.log(`SOUL_IDENTITY_CONTRACT_ADDRESS=${await contracts.soulIdentity.getAddress()}`);
    }
    
    console.log("");
    console.log("=".repeat(70));
  }

  /**
   * Get UUPS implementation address using EIP-1967 storage slot
   * @param {string} proxyAddress - Proxy contract address
   * @returns {Promise<string|null>} - Implementation address or null
   */
  async getUUPSImplementationAddress(proxyAddress) {
    try {
      const EIP1967_IMPLEMENTATION_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc';
      const implementationBytes = await this.ethersUtils.provider.getStorage(
        proxyAddress,
        EIP1967_IMPLEMENTATION_SLOT
      );
      // Extract address from bytes32 (last 20 bytes)
      const logicAddress = '0x' + implementationBytes.slice(-40);
      return logicAddress;
    } catch (error) {
      logger.warn(`Failed to get implementation address for ${proxyAddress}:`, error.message);
      return null;
    }
  }

}

module.exports = DeployActions;
