/**
 * Component Actions Module
 * 
 * This module handles all component-related actions from deploy_full.js,
 * centralizing component upload and management logic.
 */

const logger = require('../utils/Logger');

class ComponentActions {
  constructor(contractManager, arweaveManager, ethersUtils, config, inviteActions) {
    this.contractManager = contractManager;
    this.arweaveManager = arweaveManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    this.inviteActions = inviteActions;
  }

  /**
   * Action 555: Базовая активация seller + загрузка компонентов
   * @returns {Promise<Object>} - Upload result
   */
  async action555() {
    console.log("\n" + "=".repeat(70));
    console.log("🔷 Action 555: Базовая активация seller + загрузка компонентов");
    console.log("=".repeat(70));
    
    try {
      // Получение параметров из env
      const deployerInvite = process.env.DEPLOYER_INVITE;
      const sellerAddress = process.env.SELLER_ADDRESS || this.config.get('seller.address');
      const dryRun = process.env.DRY_RUN === 'true';
      
      if (!deployerInvite) {
        throw new Error("Action 555: требуется DEPLOYER_INVITE (рутовый инвайт из Action 777)");
      }
      if (!sellerAddress) {
        throw new Error("Action 555: требуется SELLER_ADDRESS");
      }
      
      // ШАГ 1/3: Загрузка SpiralEngine
      console.log("\n📦 Шаг 1/3: Загрузка SpiralEngine...");
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      const spiralEngineAddress = await spiralEngine.getAddress();
      console.log("✅ SpiralEngine загружен:", spiralEngineAddress);
      
      // ШАГ 2/3: Базовая активация seller (delegation → InviteActions)
      console.log("\n👤 Шаг 2/3: Базовая активация seller...");
      try {
        const activationResult = await this.inviteActions.activateSeller(
          spiralEngine,
          deployerInvite,
          sellerAddress
        );
        console.log("✅ Базовая активация завершена успешно!");
        console.log(`   Активирован: ${activationResult.wasActivated ? 'Да' : 'Уже был активирован'}`);
        console.log(`   Роль назначена: ${activationResult.wasRoleGranted ? 'Да' : 'Уже была назначена'}`);
      } catch (error) {
        console.error("❌ Ошибка при базовой активации seller:");
        console.error(`   ${error.message}`);
        throw error;
      }
      
      // ШАГ 3/3: Загрузка компонентов
      console.log("\n📦 Шаг 3/3: Загрузка компонентов...");
      try {
        const uploadResults = await this.uploadComponentsCore(
          sellerAddress,
          "data/components",
          this.config.get('network.name') || 'localhost',
          dryRun,
          process.env.ARWEAVE !== 'false'
        );
        
        // Финальный отчет
        console.log("\n" + "=".repeat(70));
        console.log("📊 ФИНАЛЬНЫЙ ОТЧЕТ Action 555");
        console.log("=".repeat(70));
        console.log(`✅ Seller активирован: ${sellerAddress}`);
        console.log(`✅ Компонентов обработано: ${uploadResults.totalCount}`);
        console.log(`   → Успешно: ${uploadResults.successCount}`);
        console.log(`   → Пропущено: ${uploadResults.skippedCount || 0}`);
        console.log(`   → Ошибок: ${uploadResults.failCount}`);
        
        // ✅ CRITICAL FIX: Honest error reporting - throw error if ANY component failed
        if (uploadResults.failCount > 0) {
          const failedComponents = uploadResults.results.filter(r => !r.success).map(r => r.componentId);
          const successPercent = Math.round((uploadResults.successCount / uploadResults.totalCount) * 100);
          const failPercent = Math.round((uploadResults.failCount / uploadResults.totalCount) * 100);
          
          console.log(`\n${'='.repeat(70)}`);
          console.error(`❌ КРИТИЧЕСКАЯ ОШИБКА: ${uploadResults.failCount} компонентов НЕ зарегистрированы!`);
          console.error(`${'='.repeat(70)}`);
          console.error(`Успешно: ${uploadResults.successCount}/${uploadResults.totalCount} (${successPercent}%)`);
          console.error(`Провалено: ${uploadResults.failCount}/${uploadResults.totalCount} (${failPercent}%)`);
          console.error(`\nПровалившиеся компоненты:`);
          failedComponents.forEach((id, idx) => {
            const result = uploadResults.results.find(r => r.componentId === id);
            console.error(`   ${idx + 1}. ${id}`);
            console.error(`      → Ошибка: ${result.error}`);
          });
          console.error(`\n⚠️ Action 555 НЕ МОЖЕТ считаться успешным!`);
          console.error(`Необходимо исправить ошибки и перезапустить.`);
          console.error(`${'='.repeat(70)}\n`);
          
          throw new Error(
            `Action 555 failed: ${uploadResults.failCount}/${uploadResults.totalCount} components not registered. ` +
            `Failed: [${failedComponents.join(', ')}]`
          );
        }
        
        console.log("\n" + "=".repeat(70));
        console.log(`✅ Action 555 завершен успешно: ${uploadResults.successCount}/${uploadResults.totalCount} компонентов`);
        console.log("=".repeat(70));
        
      return {
        success: true,
          uploadResults: uploadResults
      };
      } catch (error) {
        console.error("❌ Ошибка при загрузке компонентов:");
        console.error(`   ${error.message}`);
        throw error;
      }
    } catch (error) {
      logger.failure(555, error.message);
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
        
        // Загрузка state
        let state = stateManager.loadComponentState(componentDir, networkName) || {
          steps_completed: [],
          biounit_id: componentId,  // ✅ biounit_id - текстовое значение (например "amanita_muscaria")
          network: networkName,
          created_at: new Date().toISOString()
        };
        
        // Проверка выполненных шагов
        const isStepCompleted = (stepName) => {
          return state.steps_completed && state.steps_completed.includes(stepName);
        };
        
        console.log(`💾 Загрузка component state: ${componentId} (biounit_id: ${context.biounit_id})`);
        if (state.steps_completed && state.steps_completed.length > 0) {
          console.log(`✅ State найден, шагов завершено: ${state.steps_completed.length}`);
          console.log(`   → Завершенные шаги: ${state.steps_completed.join(', ')}`);
        } else {
          console.log(`🆕 State файл не найден, создаем новый`);
        }
        
        console.log(`📝 Начинаем полную загрузку компонента...`);
        
        // Выполнение шагов
        let simpleFieldCIDs = {};
        if (isStepCompleted('simple_fields_uploaded')) {
          console.log(`\n⏭️  ШАГ 1: Simple Fields уже загружены (пропуск)`);
          simpleFieldCIDs = state.simple_fields || {};
        } else {
          simpleFieldCIDs = await uploadSteps.uploadSimpleFields(context, state);
          console.log(`✅ Simple Fields загружены`);
        }
        
        let complexFieldCIDs = {};
        if (isStepCompleted('complex_fields_uploaded')) {
          console.log(`\n⏭️  ШАГ 2: Complex Fields уже загружены (пропуск)`);
          complexFieldCIDs = state.complex_fields || {};
        } else {
          complexFieldCIDs = await uploadSteps.uploadComplexFields(context, state);
          console.log(`✅ Complex Fields загружены`);
        }
        
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
          finalRootData = state.root_metadata?.data;
        } else {
          finalRootData = uploadSteps.updateRootMetadata(context, simpleFieldCIDs, complexFieldCIDs, state);
          console.log(`✅ Root Metadata обновлен`);
        }
        
        let rootCID;
        if (isStepCompleted('root_metadata_uploaded')) {
          console.log(`\n⏭️  ШАГ 5: Root Metadata уже загружен в Arweave (пропуск)`);
          rootCID = state.root_metadata?.cid;
        } else {
          rootCID = await uploadSteps.uploadRootMetadata(context, finalRootData, state);
          console.log(`✅ Root Metadata загружен в Arweave: ${rootCID}`);
        }
        
        let componentIdResult;
        if (isStepCompleted('component_registered')) {
          // ✅ FIX: Verify component actually exists in contract before skipping
          console.log(`\n🔍 ШАГ 6: Проверка регистрации компонента в контракте...`);
          console.log(`   State file: зарегистрирован (block ${state.contract_registration?.blockNumber || 'N/A'})`);
          
          try {
            const componentExists = await context.contracts.organicComponentRegistry.componentExists(context.biounit_id);
            
            if (componentExists) {
              // Component confirmed in contract - safe to skip
              console.log(`   ✅ Подтверждено в контракте: componentExists() = TRUE`);
              
              const blockchainId = await context.contracts.organicComponentRegistry.businessIdToComponentId(context.biounit_id);
              console.log(`   ✅ Blockchain ID: ${blockchainId}`);
              console.log(`   → Пропуск регистрации (компонент уже в контракте)`);
              
              componentIdResult = blockchainId.toString();
              
            } else {
              // Critical mismatch: state says registered but component not in contract
              console.warn(`   ❌ НЕСООТВЕТСТВИЕ: State file говорит "зарегистрирован", но componentExists() = FALSE`);
              console.warn(`   💡 Вероятная причина: Node был перезапущен, blockchain state сброшен`);
              console.warn(`   🔧 Выполняем регистрацию заново с сохранённым Arweave CID...`);
              
              componentIdResult = await uploadSteps.registerComponent(context, rootCID, state);
              console.log(`   ✅ Компонент зарегистрирован в контракте: ID ${componentIdResult}`);
            }
            
          } catch (verifyError) {
            // Contract verification failed - fail-safe: re-register
            console.error(`   ❌ Ошибка проверки контракта: ${verifyError.message}`);
            console.warn(`   🔧 Fail-safe: Регистрируем заново...`);
            
            componentIdResult = await uploadSteps.registerComponent(context, rootCID, state);
            console.log(`   ✅ Компонент зарегистрирован в контракте: ID ${componentIdResult}`);
          }
          
        } else {
          componentIdResult = await uploadSteps.registerComponent(context, rootCID, state);
          console.log(`✅ Компонент зарегистрирован в контракте: ID ${componentIdResult}`);
        }
        
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
