/**
 * Component Actions Module
 * 
 * This module handles all component-related actions from deploy_full.js,
 * centralizing component upload and management logic.
 */

const logger = require('../utils/Logger');
const hre = require('hardhat');

class ComponentActions {
  constructor(contractManager, arweaveManager, ethersUtils, config, inviteActions) {
    this.contractManager = contractManager;
    this.arweaveManager = arweaveManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    this.inviteActions = inviteActions;
  }

  /**
   * Action 555: Композитный Pipeline (51 → 52 → 53)
   * 
   * Последовательно выполняет:
   * 1. Action 51: Активация seller
   * 2. Action 52: Загрузка компонентов в Arweave
   * 3. Action 53: Регистрация компонентов в контракте
   * 
   * Environment Variables Required:
   * - DEPLOYER_INVITE: Root invite code (e.g., "AMANITA-XXXX-YYYY")
   * - SELLER_ADDRESS: Seller address to activate
   * 
   * Environment Variables Optional:
   * - COMPONENTS_DIR: Components directory (default: "data/components")
   * - DRY_RUN: Dry-run mode (default: false)
   * - ARWEAVE: Enable Arweave upload (default: true)
   * 
   * @returns {Promise<Object>} - Pipeline result
   */
  async action555() {
    console.log("\n" + "=".repeat(70));
    console.log("🔷 Action 555: Component Upload Pipeline (51 → 52 → 53)");
    console.log("=".repeat(70));
    
    logger.action(555, "Component Upload Pipeline");
    
    const pipelineResults = {
      action51: null,
      action52: null,
      action53: null,
      success: false,
      errors: []
    };
    
    try {
      // ====================================================================
      // ACTION 51: АКТИВАЦИЯ SELLER
      // ====================================================================
      console.log("\n" + "=".repeat(60));
      console.log("🔄 ACTION 51: АКТИВАЦИЯ SELLER");
      console.log("=".repeat(60));
      
      try {
        const result51 = await this.action51();
        pipelineResults.action51 = {
          success: result51.success,
          result: result51
        };
        console.log("✅ ACTION 51 завершен успешно");
      } catch (error) {
        console.error("❌ ACTION 51 завершен с ошибкой:", error.message);
        pipelineResults.action51 = {
          success: false,
          error: error.message
        };
        pipelineResults.errors.push(`Action 51: ${error.message}`);
        throw error; // Прерываем pipeline при ошибке активации
      }
      
      // ====================================================================
      // ACTION 52: ЗАГРУЗКА В ARWEAVE
      // ====================================================================
      console.log("\n" + "=".repeat(60));
      console.log("🔄 ACTION 52: ЗАГРУЗКА В ARWEAVE");
      console.log("=".repeat(60));
      
      try {
        const result52 = await this.action52();
        pipelineResults.action52 = {
          success: result52.success,
          result: result52.result
        };
        if (result52.success) {
          console.log("✅ ACTION 52 завершен успешно");
        } else {
          throw new Error(result52.result?.error || 'Unknown error');
        }
      } catch (error) {
        console.error("❌ ACTION 52 завершен с ошибкой:", error.message);
        pipelineResults.action52 = {
          success: false,
          error: error.message
        };
        pipelineResults.errors.push(`Action 52: ${error.message}`);
        throw error; // Прерываем pipeline при ошибке загрузки
      }
      
      // ====================================================================
      // ACTION 53: РЕГИСТРАЦИЯ В КОНТРАКТЕ
      // ====================================================================
      console.log("\n" + "=".repeat(60));
      console.log("🔄 ACTION 53: РЕГИСТРАЦИЯ В КОНТРАКТЕ");
      console.log("=".repeat(60));
      
      try {
        const result53 = await this.action53();
        pipelineResults.action53 = {
          success: result53.success,
          result: result53.result
        };
        if (result53.success) {
          console.log("✅ ACTION 53 завершен успешно");
        } else {
          throw new Error(result53.result?.error || 'Unknown error');
        }
      } catch (error) {
        console.error("❌ ACTION 53 завершен с ошибкой:", error.message);
        pipelineResults.action53 = {
          success: false,
          error: error.message
        };
        pipelineResults.errors.push(`Action 53: ${error.message}`);
        throw error; // Прерываем pipeline при ошибке регистрации
      }
      
      // ====================================================================
      // ФИНАЛЬНЫЙ РЕЗУЛЬТАТ
      // ====================================================================
      pipelineResults.success = true;
      
      console.log("\n" + "=".repeat(70));
      console.log("✅ ACTION 555 ЗАВЕРШЕН УСПЕШНО");
      console.log("=".repeat(70));
      console.log(`📊 Статистика:`);
      console.log(`   → Action 51 (Активация): ${pipelineResults.action51.success ? '✅' : '❌'}`);
      console.log(`   → Action 52 (Arweave): ${pipelineResults.action52.success ? '✅' : '❌'}`);
      console.log(`   → Action 53 (Контракт): ${pipelineResults.action53.success ? '✅' : '❌'}`);
      
      if (pipelineResults.action52.success && pipelineResults.action52.result) {
        console.log(`   → Компонентов загружено: ${pipelineResults.action52.result.successCount || 'N/A'}`);
      }
      if (pipelineResults.action53.success && pipelineResults.action53.result) {
        console.log(`   → Компонентов зарегистрировано: ${pipelineResults.action53.result.successCount || 'N/A'}`);
      }
      
      logger.success(555);
      return {
        success: true,
        pipelineResults: pipelineResults
      };
      
    } catch (error) {
      console.error("\n" + "=".repeat(70));
      console.error("❌ ACTION 555 ЗАВЕРШЕН С ОШИБКОЙ");
      console.error("=".repeat(70));
      console.error(`Ошибки:`);
      pipelineResults.errors.forEach((err, idx) => {
        console.error(`   ${idx + 1}. ${err}`);
      });
      
      logger.failure(555, error.message);
      throw error;
    }
  }

  /**
   * Action 51: Активация seller в SpiralEngine
   * 
   * Environment Variables Required:
   * - SELLER_ADDRESS: Seller address to activate
   * - DEPLOYER_INVITE: Root invite code (e.g., "AMANITA-XXXX-YYYY") - требуется только если seller НЕ активирован
   * 
   * @returns {Promise<Object>} - Activation result
   */
  async action51() {
    logger.action(51, "Activate seller in SpiralEngine");
    
    try {
      // Получение параметров из env
      const sellerAddress = process.env.SELLER_ADDRESS || this.config.get('seller.address');
      
      if (!sellerAddress) {
        throw new Error("Action 51: требуется SELLER_ADDRESS");
      }
      
      // Загрузка SpiralEngine
      console.log("\n📦 Загрузка SpiralEngine...");
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      const spiralEngineAddress = await spiralEngine.getAddress();
      console.log("✅ SpiralEngine загружен:", spiralEngineAddress);
      
      // ✅ НОВОЕ: Проверка активации ДО требования DEPLOYER_INVITE
      console.log("\n🔍 Проверка текущего статуса активации...");
      const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      
      const isActivated = usedInvite > 0;
      console.log(`   Активирован: ${isActivated ? '✅' : '❌'}`);
      console.log(`   SELLER_ROLE: ${hasSellerRole ? '✅' : '❌'}`);
      
      if (isActivated && hasSellerRole) {
        // ✅ Seller уже активирован - пропускаем активацию
        console.log("\n✅ Seller уже активирован, пропуск активации");
        console.log(`   Seller: ${sellerAddress}`);
        console.log(`   Активирован: Уже был активирован`);
        console.log(`   SELLER_ROLE: Уже была назначена`);
        
        logger.success(51);
        return {
          success: true,
          sellerAddress: sellerAddress,
          spiralEngineAddress: spiralEngineAddress,
          wasActivated: false,
          wasRoleGranted: false,
          newInvites: [],
          skipActivation: true
        };
      }
      
      // ✅ Seller НЕ активирован - требуем DEPLOYER_INVITE
      const deployerInvite = process.env.DEPLOYER_INVITE;
      if (!deployerInvite) {
        throw new Error("Action 51: требуется DEPLOYER_INVITE (рутовый инвайт из Action 777)");
      }
      
      // Активация seller
      console.log("\n👤 Активация seller...");
      const activationResult = await this.inviteActions.activateSeller(
        spiralEngine,
        deployerInvite,
        sellerAddress
      );
      
      // Валидация результата через blockchain (не полагаемся на поля результата)
      console.log("\n🔍 Валидация активации через blockchain...");
      const usedInviteAfter = await spiralEngine.usedInviteByUser(sellerAddress);
      if (usedInviteAfter == 0) {
        throw new Error(`Seller ${sellerAddress} не активирован после вызова activateSeller!`);
      }
      
      const hasSellerRoleAfter = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      if (!hasSellerRoleAfter) {
        throw new Error(`Seller ${sellerAddress} не имеет SELLER_ROLE после активации!`);
      }
      
      console.log("✅ Базовая активация завершена успешно!");
      console.log(`   Seller: ${sellerAddress}`);
      console.log(`   Активирован: ${activationResult.wasActivated ? 'Да (только что активирован)' : 'Уже был активирован'}`);
      console.log(`   SELLER_ROLE: ${activationResult.wasRoleGranted ? 'Назначена (только что)' : 'Уже была назначена'}`);
      if (activationResult.newInvites && activationResult.newInvites.length > 0) {
        console.log(`   Инвайтов создано: ${activationResult.newInvites.length}`);
      }
      
      logger.success(51);
      return {
        success: true,
        sellerAddress: sellerAddress,
        spiralEngineAddress: spiralEngineAddress,
        wasActivated: activationResult.wasActivated,
        wasRoleGranted: activationResult.wasRoleGranted,
        newInvites: activationResult.newInvites || [],
        inviteCodeUsed: deployerInvite
      };
    } catch (error) {
      logger.failure(51, error.message);
      throw error;
    }
  }

  /**
   * Action 52: Загрузка компонентов в Arweave из JSON
   * 
   * Environment Variables Required:
   * - SELLER_ADDRESS: Seller address (must be activated via Action 51)
   * 
   * Environment Variables Optional:
   * - COMPONENTS_DIR: Components directory (default: "data/components")
   * - DRY_RUN: Dry-run mode (default: false)
   * - ARWEAVE: Enable Arweave upload (default: true)
   * - USE_EXISTING_CIDS: Use existing CID from state files instead of uploading to Arweave (default: false)
   * 
   * @returns {Promise<Object>} - Upload result
   */
  async action52() {
    logger.action(52, "Upload components to Arweave");
    
    try {
      // Получение параметров из env
      const sellerAddress = process.env.SELLER_ADDRESS || this.config.get('seller.address');
      const componentsDir = process.env.COMPONENTS_DIR || 'data/components';
      const dryRun = process.env.DRY_RUN === 'true';
      const useExistingCids = process.env.USE_EXISTING_CIDS === 'true';  // ✅ НОВОЕ
      
      if (!sellerAddress) {
        throw new Error("Action 52: требуется SELLER_ADDRESS");
      }
      
      // Определение сети
      let networkName = 'localhost';
      try {
        if (hre && hre.network && hre.network.name) {
          networkName = hre.network.name;
        } else {
          networkName = this.config.get('network.name') || 'localhost';
        }
      } catch (error) {
        networkName = this.config.get('network.name') || 'localhost';
      }
      
      // Инициализация Arweave
      if (!this.arweaveManager.isReady()) {
        const initResult = await this.arweaveManager.initialize();
        if (!initResult.success) {
          throw new Error(`ArweaveManager initialization failed: ${initResult.error || 'Unknown error'}`);
        }
      }
      
      // Подготовка контрактов
      const organicRegistry = await this.contractManager.loadUUPSContract('OrganicComponentRegistry');
      const amanitaIntl = await this.contractManager.loadUUPSContract('AmanitaInternational');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      
      // Создание signers
      const deployerSigner = this.ethersUtils.getSigner();
      const deployerAddress = await deployerSigner.getAddress();
      
      const sellerPrivateKey = this.config.get('seller.privateKey');
      if (!sellerPrivateKey) {
        throw new Error('SELLER_PRIVATE_KEY не найден в .env');
      }
      const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
      
      // Создание context
      const context = {
        seller: {
          address: sellerAddress,
          signer: sellerSigner
        },
        deployer: {
          address: deployerAddress,
          signer: deployerSigner
        },
        contracts: {
          organicComponentRegistry: organicRegistry,
          amanitaInternational: amanitaIntl,
          spiralEngine: spiralEngine
        },
        arweave: {
          client: this.arweaveManager.getClient(),
          key: this.arweaveManager.getKey()
        },
        ethersProvider: this.ethersUtils.provider,
        supportedLanguages: require('../upload_utils').getSupportedLanguages(),
        useExistingCids: useExistingCids  // ✅ НОВОЕ: Флаг для использования существующих CID
      };
      
      // Импорт функции загрузки
      const { action52_UnifiedArweaveUpload } = require('../upload_steps');
      
      // Вызов функции загрузки
      const result = await action52_UnifiedArweaveUpload(
        context,
        componentsDir,
        networkName,
        dryRun
      );
      
      logger.success(52);
      return {
        success: result.success,
        result: result
      };
    } catch (error) {
      logger.failure(52, error.message);
      throw error;
    }
  }

  /**
   * Action 53: Регистрация компонентов в OrganicComponentRegistry
   * 
   * Environment Variables Required:
   * - SELLER_ADDRESS: Seller address (must be activated via Action 51)
   * 
   * Environment Variables Optional:
   * - COMPONENTS_DIR: Components directory (default: "data/components")
   * - DRY_RUN: Dry-run mode (default: false)
   * 
   * @returns {Promise<Object>} - Registration result
   */
  async action53() {
    logger.action(53, "Register components in OrganicComponentRegistry");
    
    try {
      // Получение параметров из env
      const sellerAddress = process.env.SELLER_ADDRESS || this.config.get('seller.address');
      const componentsDir = process.env.COMPONENTS_DIR || 'data/components';
      const dryRun = process.env.DRY_RUN === 'true';
      
      if (!sellerAddress) {
        throw new Error("Action 53: требуется SELLER_ADDRESS");
      }
      
      // Определение сети
      let networkName = 'localhost';
      try {
        if (hre && hre.network && hre.network.name) {
          networkName = hre.network.name;
        } else {
          networkName = this.config.get('network.name') || 'localhost';
        }
      } catch (error) {
        networkName = this.config.get('network.name') || 'localhost';
      }
      
      // Подготовка контрактов
      const organicRegistry = await this.contractManager.loadUUPSContract('OrganicComponentRegistry');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      
      // Создание signers
      const deployerSigner = this.ethersUtils.getSigner();
      const deployerAddress = await deployerSigner.getAddress();
      
      const sellerPrivateKey = this.config.get('seller.privateKey');
      if (!sellerPrivateKey) {
        throw new Error('SELLER_PRIVATE_KEY не найден в .env');
      }
      const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
      
      // Создание context
      const context = {
        seller: {
          address: sellerAddress,
          signer: sellerSigner
        },
        deployer: {
          address: deployerAddress,
          signer: deployerSigner
        },
        contracts: {
          organicComponentRegistry: organicRegistry,
          spiralEngine: spiralEngine
        },
        arweave: {
          client: this.arweaveManager.getClient(),
          key: this.arweaveManager.getKey()
        },
        ethersProvider: this.ethersUtils.provider,
        supportedLanguages: require('../upload_utils').getSupportedLanguages()
      };
      
      // Импорт функции регистрации
      const { action53_UnifiedContractRegistration } = require('../upload_steps');
      
      // Вызов функции регистрации
      const result = await action53_UnifiedContractRegistration(
        context,
        componentsDir,
        networkName,
        dryRun
      );
      
      logger.success(53);
      return {
        success: result.success,
        result: result
      };
    } catch (error) {
      logger.failure(53, error.message);
      throw error;
    }
  }

  /**
   * Роутер для загрузки компонентов (Full/Quick режим)
   * @param {string} sellerAddress - Адрес seller
   * @param {string} componentsDir - Директория с компонентами
   * @param {string} networkName - Название сети
   * @param {boolean} dryRun - Режим dry-run
   * @param {boolean} withArweave - Полная загрузка в Arweave
   * @returns {Promise<Object>} - Результаты загрузки
   * @private
   */
  async uploadComponentsCore(sellerAddress, componentsDir, networkName, dryRun, withArweave) {
    console.log(`\n🔷 Загрузка компонентов в OrganicComponentRegistry...`);
    console.log(`👤 Seller: ${sellerAddress}`);
    console.log(`📁 Директория: ${componentsDir}`);
    console.log(`🌐 Сеть: ${networkName}`);
    console.log(`🔍 Dry-run: ${dryRun ? 'YES' : 'NO'}`);
    console.log(`📤 Arweave: ${withArweave ? 'FULL UPLOAD' : 'QUICK MODE'}`);
    
    if (withArweave) {
      console.log(`\n🚀 Режим ARWEAVE=true - полная загрузка в Arweave`);
      return await this.uploadComponentFull(sellerAddress, componentsDir, networkName, dryRun);
    } else {
      console.log(`\n⚡ Режим ARWEAVE=false - быстрая регистрация`);
      throw new Error('Quick mode not implemented yet');
    }
  }

  /**
   * Полная загрузка компонентов в Arweave + регистрация в контрактах
   * @param {string} sellerAddress - Адрес seller
   * @param {string} componentsDir - Директория с компонентами
   * @param {string} networkName - Название сети
   * @param {boolean} dryRun - Режим dry-run
   * @returns {Promise<Object>} - Результаты загрузки
   * @private
   */
  async uploadComponentFull(sellerAddress, componentsDir, networkName, dryRun) {
    console.log(`\n🚀 ПОЛНАЯ ЗАГРУЗКА КОМПОНЕНТОВ В ARWEAVE`);
    
    const fs = require('fs');
    const path = require('path');
    const uploadSteps = require('../upload_steps');
    const uploadUtils = require('../upload_utils');
    const stateManager = require('../state_manager');
    
    // 1. Инициализация Arweave (через централизованный ArweaveManager)
    console.log(`\n📋 Шаг 1/6: Инициализация Arweave...`);
    
    // DEFENSIVE: Ensure ArweaveManager is initialized
    if (!this.arweaveManager.isReady()) {
      const initResult = await this.arweaveManager.initialize();
      if (!initResult.success) {
        throw new Error(`ArweaveManager initialization failed: ${initResult.error || 'Unknown error'}`);
      }
      console.log(`✅ Arweave готов: ${initResult.balance.balanceInAR} AR, wallet: ${initResult.wallet}`);
    } else {
      console.log(`✅ Arweave уже инициализирован`);
    }
    
    // Get client and key from ArweaveManager
    const arweaveClient = this.arweaveManager.getClient();
    const arweaveKey = this.arweaveManager.getKey();
    const wallet = this.arweaveManager.getWalletAddress();
    
    // 2. Подготовка контрактов
    console.log(`\n📦 Шаг 2/6: Подготовка...`);
    const organicRegistry = await this.contractManager.loadUUPSContract('OrganicComponentRegistry');
    const amanitaIntl = await this.contractManager.loadUUPSContract('AmanitaInternational');
    const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
    
    // Создаем signers
    const deployerSigner = this.ethersUtils.getSigner();
    const deployerAddress = await deployerSigner.getAddress();
    
    const sellerPrivateKey = this.config.get('seller.privateKey');
    if (!sellerPrivateKey) {
      throw new Error('SELLER_PRIVATE_KEY не найден в .env');
    }
    const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
    
    // Валидация seller
    const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
    if (usedInvite == 0) {
      throw new Error(`Seller ${sellerAddress} не активирован!`);
    }
    
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
    if (!hasSellerRole) {
      throw new Error(`Seller ${sellerAddress} не имеет SELLER_ROLE!`);
    }
    
    console.log(`✅ Контракты загружены`);
    console.log(`✅ Seller валиден: активирован + SELLER_ROLE`);
    
    // 3. Поиск компонентов
    // scripts/lib/actions/ComponentActions.js находится в <projectRoot>/scripts/lib/actions
    // поэтому projectRoot = три уровня вверх (actions -> lib -> scripts -> projectRoot) = '..','..','..'
    // НО: путь выше уже используется как base для относительных данных, и нам нужен именно <projectRoot>.
    // Из actions достаточно подняться на 3 уровня? Проверка:
    // __dirname = <projectRoot>/scripts/lib/actions
    // '..' -> <projectRoot>/scripts/lib
    // '..' -> <projectRoot>/scripts
    // '..' -> <projectRoot>
    // => оставляем 3 уровня, но предыдущая логика ломала путь из других файлов; здесь корректно.
    const projectRoot = path.join(__dirname, '..', '..', '..');
    const componentsPath = path.join(projectRoot, componentsDir);
    
    if (!fs.existsSync(componentsPath)) {
      throw new Error(`Директория компонентов не найдена: ${componentsPath}`);
    }
    
    const entries = fs.readdirSync(componentsPath, { withFileTypes: true });
    const componentIds = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .filter(name => {
        if (name.startsWith('_') || name.startsWith('.')) return false;
        const componentDir = path.join(componentsPath, name);
        const rootFile = path.join(componentDir, `${name}.json`);
        return fs.existsSync(rootFile);
      })
      .sort();
    
    if (componentIds.length === 0) {
      throw new Error(`Компоненты не найдены в ${componentsPath}`);
    }
    
    console.log(`✅ Найдено компонентов: ${componentIds.length}`);
    
    // 4. Обработка компонентов
    console.log(`\n🚀 Шаг 3/6: Обработка компонентов...`);
    
    const results = [];
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < componentIds.length; i++) {
      const componentId = componentIds[i];
      const componentDir = path.join(componentsPath, componentId);
      
      console.log(`\n${'='.repeat(70)}`);
      console.log(`🔷 Компонент ${i + 1}/${componentIds.length}: ${componentId}`);
      console.log(`${'='.repeat(70)}`);
      
      try {
        // Создаем context для upload_steps (ethers.js версия)
        const context = {
          biounit_id: componentId,  // ✅ biounit_id - текстовое значение из имени директории (например "amanita_muscaria")
          componentDir: componentDir,
          network: networkName,
          dryRun: dryRun,
          seller: {
            address: sellerAddress,
            signer: sellerSigner  // ✅ ethers.Wallet
          },
          deployer: {
            address: deployerAddress,
            signer: deployerSigner  // ✅ ethers.Wallet
          },
          contracts: {
            organicComponentRegistry: organicRegistry,  // ✅ ethers.Contract
            amanitaInternational: amanitaIntl  // ✅ ethers.Contract
          },
          arweave: {
            client: arweaveClient,
            key: arweaveKey
          },
          ethersProvider: this.ethersUtils.provider,  // ✅ ethers provider
          supportedLanguages: uploadUtils.getSupportedLanguages()
        };
        
        // ✅ CHANGE (2025-12-02): Load state with new structure
        let state = stateManager.loadComponentState(componentDir, networkName) || {
          biounit_id: componentId,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          arweave: {
            steps_completed: [],
            simple_fields: {},
            complex_fields: {},
            root_metadata: {}
          },
          deployments: {}
        };
        
        // ✅ CHANGE (2025-12-02): Check arweave section for steps
        const isStepCompleted = (stepName) => {
          return state.arweave?.steps_completed?.includes(stepName) || false;
        };
        
        console.log(`💾 Загрузка component state: ${componentId} (biounit_id: ${context.biounit_id})`);
        const arweaveSteps = state.arweave?.steps_completed || [];
        const deployments = Object.keys(state.deployments || {});
        
        if (arweaveSteps.length > 0 || deployments.length > 0) {
          console.log(`✅ State найден:`);
          console.log(`   → Arweave шагов: ${arweaveSteps.length}`);
          console.log(`   → Deployments: ${deployments.join(', ') || 'none'}`);
          if (arweaveSteps.length > 0) {
            console.log(`   → Завершенные шаги: ${arweaveSteps.join(', ')}`);
          }
        } else {
          console.log(`🆕 State файл не найден, создаем новый`);
        }
        
        console.log(`📝 Начинаем полную загрузку компонента...`);
        
        // Выполнение шагов
        // ✅ ВАЖНО: Функции uploadSimpleFields() и uploadComplexFields() сами проверяют
        //    state + контракт и автоматически восстанавливают при несоответствии.
        //    Поэтому всегда вызываем их - они решат, что делать.
        let simpleFieldCIDs = await uploadSteps.uploadSimpleFields(context, state);
        let complexFieldCIDs = await uploadSteps.uploadComplexFields(context, state);
        
        if (i === 0) {
          if (isStepCompleted('shareable_data_uploaded')) {
            console.log(`\n⏭️  ШАГ 3: Shareable Data уже загружены (пропуск)`);
          } else {
            await uploadSteps.uploadShareableData(context, state);
            console.log(`✅ Shareable Data загружены`);
          }
        }
        
        let finalRootData;
        if (isStepCompleted('root_metadata_updated')) {
          console.log(`\n⏭️  ШАГ 4: Root Metadata уже обновлен (пропуск)`);
          finalRootData = state.arweave?.root_metadata?.data;
        } else {
          finalRootData = uploadSteps.updateRootMetadata(context, simpleFieldCIDs, complexFieldCIDs, state);
          console.log(`✅ Root Metadata обновлен`);
        }
        
        let rootCID;
        if (isStepCompleted('root_metadata_uploaded')) {
          console.log(`\n⏭️  ШАГ 5: Root Metadata уже загружен в Arweave (пропуск)`);
          rootCID = state.arweave?.root_metadata?.cid;
        } else {
          rootCID = await uploadSteps.uploadRootMetadata(context, finalRootData, state);
          console.log(`✅ Root Metadata загружен в Arweave: ${rootCID}`);
        }
        
        // ✅ CHANGE (2025-12-02): Step 6 logic now handles deployments internally
        // registerComponent checks state.deployments[network] and componentExists()
        // We just call it - it will decide whether to skip or register
        let componentIdResult = await uploadSteps.registerComponent(context, rootCID, state);
        console.log(`✅ Компонент обработан: ID ${componentIdResult}`);
        
        results.push({
          componentId,
          success: true,
          rootCID: rootCID,
          contractComponentId: componentIdResult,
          simpleFields: Object.keys(simpleFieldCIDs).length,
          complexFields: Object.keys(complexFieldCIDs).length
        });
        successCount++;
        
      } catch (error) {
        console.error(`❌ Ошибка обработки компонента ${componentId}:`);
        console.error(`   ${error.message}`);
        
        results.push({
          componentId,
          success: false,
          error: error.message
        });
        failCount++;
        
        console.log(`⏭️  Продолжаем со следующим компонентом...`);
      }
    }
    
    // 5. Финальный отчет
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📊 ФИНАЛЬНЫЙ ОТЧЁТ ПОЛНОЙ ЗАГРУЗКИ`);
    console.log(`${'='.repeat(70)}`);
    console.log(`✅ Успешно: ${successCount}`);
    console.log(`❌ Ошибок: ${failCount}`);
    console.log(`📊 Всего: ${componentIds.length}`);
    console.log(`🌐 Сеть: ${networkName}`);
    console.log(`📤 Arweave: ПОЛНАЯ ЗАГРУЗКА`);
    
    if (successCount > 0) {
      console.log(`\n🎉 Успешно загружены:`);
      results.filter(r => r.success).forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.componentId}`);
        console.log(`      → Root CID: ${result.rootCID}`);
        console.log(`      → Contract ID: ${result.contractComponentId}`);
        console.log(`      → Simple Fields: ${result.simpleFields}`);
        console.log(`      → Complex Fields: ${result.complexFields}`);
      });
    }
    
    if (failCount > 0) {
      console.log(`\n❌ Ошибки:`);
      results.filter(r => !r.success).forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.componentId}: ${result.error}`);
      });
    }
    
    console.log(`\n✅ Полная загрузка завершена`);
    console.log(`${'='.repeat(70)}`);
    
    // ✅ CRITICAL FIX: Final contract state validation
    if (!dryRun && successCount > 0) {
      console.log(`\n${'='.repeat(70)}`);
      console.log(`🔍 ФИНАЛЬНАЯ ВАЛИДАЦИЯ КОНТРАКТНОГО СОСТОЯНИЯ`);
      console.log(`${'='.repeat(70)}`);
      
      try {
        // Load contract (context not available in this scope)
        const organicComponentRegistry = await this.contractManager.loadUUPSContract('OrganicComponentRegistry');
        
        const totalInContract = await organicComponentRegistry.totalComponents();
        console.log(`\n📊 Статистика OrganicComponentRegistry:`);
        console.log(`   Всего компонентов в контракте: ${totalInContract}`);
        console.log(`   Обработано в Action 555: ${successCount}`);
        
        if (totalInContract.toString() !== successCount.toString()) {
          console.error(`\n❌ КРИТИЧЕСКАЯ ОШИБКА: Несоответствие количества компонентов!`);
          console.error(`   Обработано: ${successCount}`);
          console.error(`   В контракте: ${totalInContract}`);
          console.error(`   → Некоторые компоненты НЕ зарегистрированы в контракте!`);
          throw new Error(`Component count mismatch: processed ${successCount}, in contract ${totalInContract}`);
        }
        
        console.log(`\n🔍 Проверка каждого компонента:`);
        let verifiedCount = 0;
        for (const result of results.filter(r => r.success)) {
          const exists = await organicComponentRegistry.componentExists(result.componentId);
          const status = exists ? '✅ В КОНТРАКТЕ' : '❌ НЕ НАЙДЕН';
          console.log(`   ${status}: ${result.componentId}`);
          
          if (!exists) {
            console.error(`\n❌ КРИТИЧЕСКАЯ ОШИБКА: Component ${result.componentId} reported success but NOT in contract!`);
            throw new Error(`Component ${result.componentId} validation failed - not found in OrganicComponentRegistry`);
          }
          verifiedCount++;
        }
        
        console.log(`\n✅ ВАЛИДАЦИЯ ПРОЙДЕНА: Все ${verifiedCount} компонентов подтверждены в контракте`);
        console.log(`🎯 Action 444 готов к запуску!`);
        console.log(`${'='.repeat(70)}\n`);
        
      } catch (validationError) {
        console.error(`\n❌ ФИНАЛЬНАЯ ВАЛИДАЦИЯ ПРОВАЛИЛАСЬ: ${validationError.message}`);
        console.error(`   → Action 555 НЕ МОЖЕТ считаться успешным!`);
        throw validationError;
      }
    }
    
    return {
      successCount,
      failCount,
      skippedCount: 0,
      totalCount: componentIds.length,
      results,
      mode: 'FULL_ARWEAVE'
    };
  }

}

module.exports = ComponentActions;
