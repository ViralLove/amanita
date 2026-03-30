/**
 * Setup Actions Module
 * 
 * This module handles all contract initialization and setup connections,
 * separating deployment from configuration for clean architecture.
 * 
 * Setup происходит ПОСЛЕ deploy и устанавливает связи между контрактами.
 * Все контракты загружаются через MagicRegistry, минимизируя .env зависимости.
 */

const logger = require('../utils/Logger');

class SetupActions {
  constructor(contractManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
  }

  /**
   * Validate current system connections state
   * @param {Object} contracts - Deployed contracts
   * @returns {Promise<Array>} - Array of validation issues
   */
  async validateSystemConnections(contracts) {
    const { ethers } = require('hardhat');
    console.log("\n🔍 Валидация текущих связей...");
    
    const issues = [];
    
    // Check ProductRegistry → OrganicComponentRegistry
    if (contracts.productRegistry && contracts.organicComponentRegistry) {
      try {
        const currentRegistry = await contracts.productRegistry.componentRegistry();
        const expectedRegistry = await contracts.organicComponentRegistry.getAddress();
        
        if (currentRegistry === ethers.ZeroAddress) {
          issues.push("❌ ProductRegistry.componentRegistry не установлен");
        } else if (currentRegistry !== expectedRegistry) {
          issues.push(`⚠️ ProductRegistry.componentRegistry указывает на неправильный адрес`);
        } else {
          console.log("✅ ProductRegistry → OrganicComponentRegistry связь OK");
        }
      } catch (error) {
        issues.push(`❌ ProductRegistry validation error: ${error.message}`);
      }
    }
    
    // Check AmanitaInternational → SpiralEngine
    if (contracts.amanitaInternational && contracts.spiralEngine) {
      try {
        const currentSpiral = await contracts.amanitaInternational.spiralEngine();
        const expectedSpiral = await contracts.spiralEngine.getAddress();
        
        if (currentSpiral === ethers.ZeroAddress) {
          issues.push("❌ AmanitaInternational.spiralEngine не установлен");
        } else if (currentSpiral !== expectedSpiral) {
          issues.push(`⚠️ AmanitaInternational.spiralEngine указывает на неправильный адрес`);
        } else {
          console.log("✅ AmanitaInternational → SpiralEngine связь OK");
        }
      } catch (error) {
        issues.push(`❌ AmanitaInternational validation error: ${error.message}`);
      }
    }
    
    // Check OrganicComponentRegistry → SpiralEngine
    if (contracts.organicComponentRegistry && contracts.spiralEngine) {
      try {
        const currentSpiral = await contracts.organicComponentRegistry.spiralEngine();
        const expectedSpiral = await contracts.spiralEngine.getAddress();
        
        if (currentSpiral === ethers.ZeroAddress) {
          issues.push("❌ OrganicComponentRegistry.spiralEngine не установлен");
        } else if (currentSpiral !== expectedSpiral) {
          issues.push(`⚠️ OrganicComponentRegistry.spiralEngine указывает на неправильный адрес`);
        } else {
          console.log("✅ OrganicComponentRegistry → SpiralEngine связь OK");
        }
      } catch (error) {
        issues.push(`❌ OrganicComponentRegistry validation error: ${error.message}`);
      }
    }
    
    if (issues.length > 0) {
      console.log("\n⚠️ Найдены проблемы:");
      issues.forEach(issue => console.log(`  ${issue}`));
      console.log("\n🔧 Применяем исправления...\n");
    } else {
      console.log("\n✅ Все связи настроены корректно!\n");
    }
    
    return issues;
  }

  /**
   * Setup all system connections (полная инициализация)
   * Используется внутри Action 1 и может быть вызвана отдельно для re-setup
   * @param {Object} contracts - Deployed contracts (опционально, загрузит через MagicRegistry если не передано)
   * @returns {Promise<void>}
   */
  async setupSystemConnections(contracts = null) {
    logger.info("Setting up all system connections...");
    
    // Helper: Wait for nonce update between setup operations
    const waitForNonce = async (ms = 1000) => {
      logger.info(`⏱️ Waiting ${ms}ms for nonce update...`);
      await new Promise(resolve => setTimeout(resolve, ms));
      logger.info('✅ Nonce settled, proceeding...');
    };
    
    try {
      // Если контракты не переданы, загружаем через MagicRegistry
      if (!contracts) {
        contracts = await this.loadSystemContracts();
      }
      
      // 1. Setup SBT ecosystem connections
      await this.setupSBTEcosystem(contracts);
      await waitForNonce();
      
      // 2. Setup OrganicComponentRegistry connections
      await this.setupOrganicComponentRegistry(contracts);
      await waitForNonce();
      
      // 3. Setup ProductRegistry connections (depends on OrganicComponentRegistry)
      await this.setupProductRegistry(contracts);
      await waitForNonce();
      
      // 4. Setup AmanitaInternational connections (depends on SpiralEngine)
      await this.setupAmanitaInternational(contracts);
      
      logger.success("All system connections configured");
    } catch (error) {
      logger.error("Failed to setup system connections:", error.message);
      throw error;
    }
  }

  /**
   * Action 2: Re-setup all system connections with validation
   * @returns {Promise<Object>} - Result object
   */
  async action2() {
    logger.action(2, "Re-setup all system connections");
    
    try {
      // Load all contracts from MagicRegistry
      const contracts = await this.loadSystemContracts();
      
      // Validate current state before setup
      await this.validateSystemConnections(contracts);
      
      // Re-run setup
      await this.setupSystemConnections(contracts);
      
      logger.success(2);
      return { success: true };
    } catch (error) {
      logger.failure(2, error.message);
      throw error;
    }
  }

  /**
   * Load all system contracts from MagicRegistry
   * @returns {Promise<Object>} - Loaded contracts
   */
  async loadSystemContracts() {
    logger.info("Loading system contracts from MagicRegistry...");
    
    const contracts = {};
    
    // Load MagicRegistry from .env
    const magicRegistryAddress = this.config.get('contracts.magicRegistry');
    if (!magicRegistryAddress) {
      throw new Error('MAGIC_REGISTRY_CONTRACT_ADDRESS не найден в .env');
    }
    
    contracts.magicRegistry = await this.contractManager.loadContract('MagicRegistry', magicRegistryAddress);
    logger.info(`✅ MagicRegistry: ${magicRegistryAddress}`);
    
    // Load all other contracts через MagicRegistry
    const contractNames = [
      'SpiralEngine',
      'SoulboundCore',
      'SoulMetadata',
      'SoulRecovery',
      'SoulIntegration',
      'SoulIdentity',
      'ProductRegistry',
      'ActivityRegistry',
      'OrganicComponentRegistry',
      'AmanitaInternational'
    ];

    const uupsNames = [
      'SpiralEngine',
      'ProductRegistry',
      'ActivityRegistry',
      'OrganicComponentRegistry',
      'AmanitaInternational'
    ];

    for (const name of contractNames) {
      try {
        // UUPS контракты
        if (uupsNames.includes(name)) {
          contracts[name.charAt(0).toLowerCase() + name.slice(1)] = await this.contractManager.loadUUPSContract(name);
        } else {
          // Обычные контракты
          const address = await contracts.magicRegistry.get(name);
          contracts[name.charAt(0).toLowerCase() + name.slice(1)] = await this.contractManager.loadContract(name, address);
        }
        logger.info(`✅ ${name} loaded`);
      } catch (error) {
        logger.warn(`⚠️ Failed to load ${name}:`, error.message);
      }
    }
    
    return contracts;
  }

  /**
   * Setup SBT ecosystem connections
   * @param {Object} contracts - Deployed contracts
   * @returns {Promise<void>}
   */
  async setupSBTEcosystem(contracts) {
    logger.info("Setting up SBT ecosystem connections...");
    
    const { soulboundCore, soulMetadata, soulRecovery, soulIntegration, soulIdentity, spiralEngine } = contracts;
    
    if (!soulboundCore || !spiralEngine) {
      logger.warn("SBT contracts not fully deployed, skipping setup");
      return;
    }
    
    // Helper: Wait for nonce update between transactions
    const waitForNonce = async (ms = 1000) => {
      logger.info(`⏱️ Waiting ${ms}ms for nonce update...`);
      await new Promise(resolve => setTimeout(resolve, ms));
      logger.info('✅ Nonce settled, proceeding...');
    };
    
    try {
      const signer = this.ethersUtils.getSigner();
      
      // 1. Connect SoulMetadata to SoulboundCore
      console.log("--------------------------------------------------");
      console.log("📋 Connecting SoulMetadata to SoulboundCore");
      console.log("--------------------------------------------------");
      const soulboundCoreWithSigner = soulboundCore.connect(signer);
      const tx1 = await soulboundCoreWithSigner.setMetadataContract(await soulMetadata.getAddress());
      await tx1.wait();
      await waitForNonce();
      
      // 2. Connect SoulRecovery to SoulboundCore
      console.log("--------------------------------------------------");
      console.log("📋 Connecting SoulRecovery to SoulboundCore");
      console.log("--------------------------------------------------");
      const tx2 = await soulboundCoreWithSigner.setRecoveryContract(await soulRecovery.getAddress());
      await tx2.wait();
      await waitForNonce();
      
      // 3. Connect SoulIntegration to SoulboundCore
      console.log("--------------------------------------------------");
      console.log("📋 Connecting SoulIntegration to SoulboundCore");
      console.log("--------------------------------------------------");
      const tx3 = await soulboundCoreWithSigner.setIntegrationContract(await soulIntegration.getAddress());
      await tx3.wait();
      await waitForNonce();
      
      // 4. Connect SoulIdentity to SpiralEngine
      console.log("--------------------------------------------------");
      console.log("📋 Connecting SoulIdentity to SpiralEngine");
      console.log("--------------------------------------------------");
      const spiralEngineWithSigner = spiralEngine.connect(signer);
      const tx4 = await spiralEngineWithSigner.setSoulIdentity(await soulIdentity.getAddress());
      await tx4.wait();
      
      logger.success("SBT ecosystem connections configured");
    } catch (error) {
      logger.error("Failed to setup SBT connections:", error.message);
      throw error;
    }
  }

  /**
   * Setup OrganicComponentRegistry connections
   * @param {Object} contracts - Deployed contracts
   * @returns {Promise<void>}
   */
  async setupOrganicComponentRegistry(contracts) {
    const { organicComponentRegistry, spiralEngine } = contracts;
    
    if (!organicComponentRegistry || !spiralEngine) {
      logger.warn("OrganicComponentRegistry or SpiralEngine not deployed, skipping connections");
      return;
    }
    
    try {
      const signer = this.ethersUtils.getSigner();
      
      console.log("--------------------------------------------------");
      console.log("📋 Настраиваем связи OrganicComponentRegistry");
      console.log("--------------------------------------------------");
      
      // Connect SpiralEngine to OrganicComponentRegistry
      console.log("🔗 Подключаем SpiralEngine к OrganicComponentRegistry...");
      const organicRegistryWithSigner = organicComponentRegistry.connect(signer);
      const tx = await organicRegistryWithSigner.setSpiralEngine(await spiralEngine.getAddress());
      await tx.wait();
      console.log("✅ SpiralEngine подключен к OrganicComponentRegistry");
      
      console.log("\n✅ OrganicComponentRegistry полностью настроен!");
      
    } catch (error) {
      logger.error("Failed to setup OrganicComponentRegistry connections:", error.message);
      throw error;
    }
  }

  /**
   * Setup ProductRegistry connections
   * @param {Object} contracts - Deployed contracts
   * @returns {Promise<void>}
   */
  async setupProductRegistry(contracts) {
    const { productRegistry, organicComponentRegistry } = contracts;
    
    if (!productRegistry || !organicComponentRegistry) {
      logger.warn("ProductRegistry or OrganicComponentRegistry not deployed, skipping connections");
      return;
    }
    
    try {
      const signer = this.ethersUtils.getSigner();
      
      console.log("--------------------------------------------------");
      console.log("📋 Настраиваем связи ProductRegistry");
      console.log("--------------------------------------------------");
      
      // Connect OrganicComponentRegistry to ProductRegistry
      console.log("🔗 Подключаем OrganicComponentRegistry к ProductRegistry...");
      const productRegistryWithSigner = productRegistry.connect(signer);
      const tx = await productRegistryWithSigner.setOrganicComponentRegistry(
        await organicComponentRegistry.getAddress()
      );
      await tx.wait();
      console.log("✅ OrganicComponentRegistry подключен к ProductRegistry");
      
      console.log("\n✅ ProductRegistry полностью настроен!");
      
    } catch (error) {
      logger.error("Failed to setup ProductRegistry connections:", error.message);
      throw error;
    }
  }

  /**
   * Setup AmanitaInternational connections
   * @param {Object} contracts - Deployed contracts
   * @returns {Promise<void>}
   */
  async setupAmanitaInternational(contracts) {
    const { amanitaInternational, spiralEngine } = contracts;
    
    if (!amanitaInternational || !spiralEngine) {
      logger.warn("AmanitaInternational or SpiralEngine not deployed, skipping connections");
      return;
    }
    
    try {
      const signer = this.ethersUtils.getSigner();
      
      console.log("--------------------------------------------------");
      console.log("📋 Настраиваем связи AmanitaInternational");
      console.log("--------------------------------------------------");
      
      // Check if already set
      const currentSpiral = await amanitaInternational.spiralEngine();
      const expectedSpiral = await spiralEngine.getAddress();
      
      if (currentSpiral === expectedSpiral) {
        console.log("⚠️ SpiralEngine уже подключен к AmanitaInternational, пропускаем...");
        return;
      }
      
      // Connect SpiralEngine to AmanitaInternational
      console.log("🔗 Подключаем SpiralEngine к AmanitaInternational...");
      const amanitaIntlWithSigner = amanitaInternational.connect(signer);
      const tx = await amanitaIntlWithSigner.setSpiralEngine(expectedSpiral);
      await tx.wait();
      console.log("✅ SpiralEngine подключен к AmanitaInternational");
      
      console.log("\n✅ AmanitaInternational полностью настроен!");
      
    } catch (error) {
      logger.error("Failed to setup AmanitaInternational connections:", error.message);
      throw error;
    }
  }
}

module.exports = SetupActions;

