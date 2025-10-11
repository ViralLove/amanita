/**
 * 🚀 Batch Upload Script for Organic Components
 * 
 * Массовая загрузка всех органических компонентов в Arweave и регистрация в смарт-контрактах
 * Использует модульную архитектуру из scripts/lib/
 * 
 * @version 1.0.0
 * @date 2025-10-09
 * 
 * Использование:
 * # Dry-run (тестирование всех компонентов)
 * DRY_RUN=true npx hardhat run scripts/upload_all_components.js --network localhost
 * 
 * # Только Arweave (без блокчейна) - создаст JSON файл с CID
 * ARWEAVE_ONLY=true npx hardhat run scripts/upload_all_components.js --network localhost
 * 
 * # Production (загрузка всех компонентов в Arweave + блокчейн)
 * npx hardhat run scripts/upload_all_components.js --network polygon
 * 
 * # С загрузкой shareable data (только первый раз)
 * UPLOAD_SHAREABLE=true npx hardhat run scripts/upload_all_components.js --network polygon
 * 
 * # Resume после сбоя
 * npx hardhat run scripts/upload_all_components.js --network polygon
 * (автоматически продолжит с последнего незавершенного компонента)
 * 
 * # Force re-upload (игнорировать существующий state)
 * FORCE_UPLOAD=true npx hardhat run scripts/upload_all_components.js --network localhost
 * (создаст новую сессию, backup старого state)
 */

require("dotenv").config();
const { Web3 } = require("web3");
const Arweave = require("arweave");
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

// Импорт наших модулей
const utils = require("./lib/upload_utils");
const uploadSteps = require("./lib/upload_steps");
const stateManager = require("./lib/state_manager");
const reportCollector = require("./lib/report_collector");

// ====================================================================
// 🔧 CONFIGURATION
// ====================================================================

const network = hre.network.name;
const DRY_RUN = process.env.DRY_RUN === "true";
const UPLOAD_SHAREABLE = process.env.UPLOAD_SHAREABLE === "true";
const ARWEAVE_ONLY = process.env.ARWEAVE_ONLY === "true";
const FORCE_UPLOAD = process.env.FORCE_UPLOAD === "true";
const COMPONENTS_DIR = path.join(__dirname, "organic_components");

// Seller credentials для создания компонентов в OrganicComponentRegistry
const SELLER_ADDRESS = process.env.SELLER_ADDRESS;
const SELLER_PRIVATE_KEY = process.env.SELLER_PRIVATE_KEY ? 
  (process.env.SELLER_PRIVATE_KEY.startsWith('0x') ? process.env.SELLER_PRIVATE_KEY : `0x${process.env.SELLER_PRIVATE_KEY}`) : null;

console.log("🔷 Конфигурация:");
console.log(`   → Network: ${network.toUpperCase()}`);
console.log(`   → Dry-run: ${DRY_RUN ? "ENABLED" : "DISABLED"}`);
console.log(`   → Arweave Only: ${ARWEAVE_ONLY ? "YES (пропуск блокчейна)" : "NO"}`);
console.log(`   → Upload Shareable: ${UPLOAD_SHAREABLE ? "YES" : "NO"}`);
console.log(`   → Force Upload: ${FORCE_UPLOAD ? "YES (игнорировать state)" : "NO"}`);
console.log(`   → Components Dir: ${COMPONENTS_DIR}`);

// Валидация environment variables
const requiredEnvVars = ['DEPLOYER_PRIVATE_KEY'];

if (!DRY_RUN) {
  requiredEnvVars.push('ARWEAVE_PRIVATE_KEY');
}

// Если не только Arweave, требуем адреса контрактов
if (!ARWEAVE_ONLY && (network === 'polygon' || network === 'mumbai')) {
  requiredEnvVars.push('AMANITA_INTERNATIONAL_PROXY_ADDRESS');
  requiredEnvVars.push('ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS');
}

try {
  utils.validateEnvVars(requiredEnvVars);
} catch (error) {
  console.error("❌ Ошибка конфигурации:", error.message);
  process.exit(1);
}

// ====================================================================
// 🌐 NETWORK & WEB3 SETUP
// ====================================================================

let RPC_URL;
if (network === 'polygon') {
  RPC_URL = process.env.POLYGON_MAINNET_RPC || "https://polygon-rpc.com";
} else if (network === 'mumbai') {
  RPC_URL = process.env.POLYGON_MUMBAI_RPC || "https://rpc-mumbai.maticvigil.com";
} else {
  RPC_URL = hre.network.config.url;
}

const web3 = new Web3(RPC_URL);
const deployerAccount = utils.initializeDeployer(web3, process.env.DEPLOYER_PRIVATE_KEY);

// Создаем seller account для создания компонентов в OrganicComponentRegistry
let sellerAccount = null;
if (SELLER_PRIVATE_KEY && SELLER_PRIVATE_KEY !== 'undefined' && SELLER_PRIVATE_KEY !== 'null') {
  try {
    sellerAccount = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
    web3.eth.accounts.wallet.add(sellerAccount);
    console.log(`👤 Deployer address: ${deployerAccount.address}`);
    console.log(`🏪 Seller account created: ${sellerAccount.address}`);
  } catch (error) {
    console.error(`❌ Error creating seller account: ${error.message}`);
    console.error(`❌ SELLER_PRIVATE_KEY value: ${SELLER_PRIVATE_KEY}`);
    process.exit(1);
  }
} else {
  console.log(`👤 Deployer address: ${deployerAccount.address}`);
  console.log(`⚠️ SELLER_PRIVATE_KEY not set - компоненты будут создаваться от имени deployer`);
  sellerAccount = deployerAccount; // Fallback на deployer
}

console.log(`🌐 RPC URL: ${RPC_URL}`);

// ====================================================================
// 📦 CONTRACT ADDRESSES
// ====================================================================

const AMANITA_INTERNATIONAL_PROXY = process.env.AMANITA_INTERNATIONAL_PROXY_ADDRESS;
const ORGANIC_COMPONENT_REGISTRY_PROXY = process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS;

if (!ARWEAVE_ONLY) {
  console.log("📍 Contract Addresses:");
  console.log(`   → AmanitaInternational: ${AMANITA_INTERNATIONAL_PROXY}`);
  console.log(`   → OrganicComponentRegistry: ${ORGANIC_COMPONENT_REGISTRY_PROXY}`);

  // Валидация адресов
  if (!DRY_RUN && (network === 'polygon' || network === 'mumbai')) {
    try {
      utils.validateContractAddresses({
        'AmanitaInternational': AMANITA_INTERNATIONAL_PROXY,
        'OrganicComponentRegistry': ORGANIC_COMPONENT_REGISTRY_PROXY
      });
    } catch (error) {
      console.error("❌ Ошибка валидации адресов:", error.message);
      process.exit(1);
    }
  }
} else {
  console.log("📍 Contract Addresses: N/A (ARWEAVE_ONLY режим)");
}

// ====================================================================
// 🔐 ARWEAVE SETUP
// ====================================================================

const arweave = Arweave.init({
  host: 'arweave.net',
  port: 443,
  protocol: 'https'
});

/**
 * Загрузка Arweave ключа из файла или ENV переменной
 * Приоритет: .arweave-key.json → ARWEAVE_PRIVATE_KEY
 */
function loadArweaveKey() {
  console.log("\n📂 Загрузка Arweave ключа...");
  
  const ARWEAVE_KEY_PATH = path.join(__dirname, "..", ".arweave-key.json");
  
  // Попытка 1: Загрузить из файла
  if (fs.existsSync(ARWEAVE_KEY_PATH)) {
    try {
      const keyContent = fs.readFileSync(ARWEAVE_KEY_PATH, "utf8");
      const key = JSON.parse(keyContent);
      
      console.log("✅ Arweave ключ загружен из файла");
      console.log(`   → Путь: ${ARWEAVE_KEY_PATH}`);
      console.log(`   → Размер ключа: ${JSON.stringify(key).length} bytes`);
      console.log(`   → kty: ${key.kty}`);
      console.log(`   → n length: ${key.n ? key.n.length : 0}`);
      
      return key;
    } catch (error) {
      console.warn(`⚠️ Ошибка чтения файла ключа: ${error.message}`);
      console.log("   → Пробую загрузить из ENV...");
    }
  } else {
    console.log(`⚠️ Файл ключа не найден: ${ARWEAVE_KEY_PATH}`);
    console.log("   → Пробую загрузить из ENV...");
  }
  
  // Попытка 2: Загрузить из ENV переменной
  if (process.env.ARWEAVE_PRIVATE_KEY) {
    try {
      const key = JSON.parse(process.env.ARWEAVE_PRIVATE_KEY);
      
      console.log("✅ Arweave ключ загружен из ENV");
      console.log(`   → Размер ключа: ${JSON.stringify(key).length} bytes`);
      console.log(`   → kty: ${key.kty}`);
      
      return key;
    } catch (error) {
      throw new Error(`Ошибка парсинга ARWEAVE_PRIVATE_KEY: ${error.message}`);
    }
  }
  
  throw new Error(
    "Arweave ключ не найден!\n" +
    `  Создайте файл: ${ARWEAVE_KEY_PATH}\n` +
    "  ИЛИ установите: ARWEAVE_PRIVATE_KEY в .env"
  );
}

let arweaveKey = null;
let arweaveAddress = null;

if (!DRY_RUN) {
  try {
    arweaveKey = loadArweaveKey();
    
    // Получить адрес кошелька
    arweave.wallets.jwkToAddress(arweaveKey).then(address => {
      arweaveAddress = address;
      console.log(`💰 Arweave адрес: ${address}`);
    }).catch(error => {
      console.error(`❌ Ошибка получения адреса: ${error.message}`);
    });
    
  } catch (error) {
    console.error("❌ Ошибка загрузки Arweave ключа:", error.message);
    process.exit(1);
  }
} else {
  console.log("🔷 [DRY-RUN] Arweave ключ не требуется");
}

// ====================================================================
// 📋 COMPONENT DISCOVERY
// ====================================================================

/**
 * Получить список всех компонентов из директории
 * @returns {Array<string>} Список component IDs
 */
function discoverComponents() {
  console.log("\n📋 Поиск компонентов...");
  
  if (!fs.existsSync(COMPONENTS_DIR)) {
    throw new Error(`Директория компонентов не найдена: ${COMPONENTS_DIR}`);
  }
  
  const entries = fs.readdirSync(COMPONENTS_DIR, { withFileTypes: true });
  
  // Фильтруем только директории с валидными названиями
  const components = entries
    .filter(entry => entry.isDirectory())
    .map(entry => entry.name)
    .filter(name => {
      // Пропускаем служебные директории
      if (name.startsWith('_') || name.startsWith('.')) {
        return false;
      }
      
      // Проверяем валидность component ID
      if (!utils.isValidComponentId(name)) {
        console.warn(`⚠️ Пропускаем невалидный ID: ${name}`);
        return false;
      }
      
      // Проверяем существование root файла
      const componentDir = path.join(COMPONENTS_DIR, name);
      const rootFile = path.join(componentDir, `${name}.json`);
      
      if (!fs.existsSync(rootFile)) {
        console.warn(`⚠️ Пропускаем ${name}: отсутствует root файл`);
        return false;
      }
      
      return true;
    });
  
  console.log(`✅ Найдено компонентов: ${components.length}`);
  components.forEach((id, index) => {
    console.log(`   ${index + 1}. ${id}`);
  });
  
  return components;
}

// ====================================================================
// 🎯 CONTEXT CREATION
// ====================================================================

/**
 * Создать upload context для компонента
 * @param {string} componentId - ID компонента
 * @param {Object} contracts - Загруженные контракты
 * @returns {Object} Context object
 */
function createComponentContext(componentId, contracts) {
  const componentDir = utils.getComponentDir(COMPONENTS_DIR, componentId);
  
  return {
    componentId,
    componentDir,
    network,
    dryRun: DRY_RUN,
    arweaveOnly: ARWEAVE_ONLY,
    contracts,
    arweave: {
      client: arweave,
      key: arweaveKey
    },
    web3,
    deployer: deployerAccount,
    seller: sellerAccount,  // ← Seller для создания компонентов
    supportedLanguages: utils.getSupportedLanguages()
  };
}

// ====================================================================
// 📤 COMPONENT UPLOAD
// ====================================================================

/**
 * Загрузить один компонент (интеграция всех Steps 1-6)
 * @param {Object} context - Upload context
 * @param {Object} report - Report object для метрик
 * @param {Function} onProgress - Progress callback
 * @returns {Promise<Object>} Upload results
 */
async function uploadComponent(context, report, onProgress = null) {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`🚀 ЗАГРУЗКА КОМПОНЕНТА: ${context.componentId}`);
  console.log(`${"=".repeat(70)}`);
  
  const startTime = Date.now();
  
  // Начать tracking в report
  reportCollector.startComponentTracking(report, context.componentId);
  
  try {
    // Загрузить component state
    const state = stateManager.loadComponentState(context.componentDir, context.network);
    
    // Progress callback wrapper
    const reportProgress = (stepInfo) => {
      if (onProgress) {
        onProgress({
          type: 'step_progress',
          componentId: context.componentId,
          ...stepInfo
        });
      }
    };
    
    // === STEP 1: Upload Simple Fields ===
    const simpleFieldCIDs = await uploadSteps.uploadSimpleFields(
      context,
      state,
      reportProgress
    );
    
    // === STEP 2: Upload Complex Fields ===
    const complexFieldCIDs = await uploadSteps.uploadComplexFields(
      context,
      state,
      reportProgress
    );
    
    // === STEP 4: Update Root Metadata ===
    const rootData = uploadSteps.updateRootMetadata(
      context,
      simpleFieldCIDs,
      complexFieldCIDs,
      state
    );
    
    // === STEP 5: Upload Root Metadata ===
    const rootCID = await uploadSteps.uploadRootMetadata(
      context,
      rootData,
      state,
      reportProgress
    );
    
    // === STEP 6: Register Component (опционально) ===
    let componentId = null;
    let blockchainMetrics = null;
    
    if (!ARWEAVE_ONLY) {
      componentId = await uploadSteps.registerComponent(
        context,
        rootCID,
        state,
        reportProgress
      );
      
      // Собираем Blockchain метрики
      blockchainMetrics = {
        component_id: componentId,
        registration_tx: state.contract_registration.txHash,
        registration_block: state.contract_registration.blockNumber,
        total_gas_used: 0, // TODO: calculate from tx receipts
        total_cost_matic: "0",
        total_cost_usd: "0"
      };
      
      reportCollector.addBlockchainMetrics(report, context.componentId, blockchainMetrics);
    } else {
      console.log("\n⏭️  Пропуск Step 6: ARWEAVE_ONLY режим");
    }
    
    // Расчет метрик
    const duration = Math.round((Date.now() - startTime) / 1000);
    
    // Собираем Arweave метрики
    const arweaveMetrics = {
      root_cid: rootCID,
      simple_fields: simpleFieldCIDs,
      complex_fields: complexFieldCIDs,
      total_files: 2 + Object.keys(complexFieldCIDs).length + 1, // simple + complex + root
      total_size_bytes: 0, // TODO: calculate from actual file sizes
      upload_duration_seconds: duration
    };
    
    reportCollector.addArweaveMetrics(report, context.componentId, arweaveMetrics);
    
    // Собираем Metadata
    reportCollector.addComponentMetadata(report, context.componentId, rootData);
    
    // Завершить tracking
    reportCollector.completeComponentTracking(report, context.componentId);
    
    const results = {
      blockchain: blockchainMetrics,
      arweave: arweaveMetrics,
      duration_seconds: duration
    };
    
    console.log(`\n✅ Компонент ${context.componentId} загружен успешно!`);
    console.log(`   → Duration: ${utils.formatDuration(duration)}`);
    console.log(`   → Root CID: ${rootCID}`);
    if (!ARWEAVE_ONLY) {
      console.log(`   → Blockchain ID: ${componentId}`);
    }
    
    return results;
    
  } catch (error) {
    const duration = Math.round((Date.now() - startTime) / 1000);
    
    console.error(`\n❌ Ошибка загрузки ${context.componentId}:`, error.message);
    console.error(`   → Duration: ${utils.formatDuration(duration)}`);
    
    // Отметить как failed в report
    reportCollector.failComponentTracking(report, context.componentId, error);
    
    throw error;
  }
}

// ====================================================================
// 🔄 BATCH PROCESSING
// ====================================================================

/**
 * Обработать очередь компонентов
 * @param {Object} batchState - Batch state
 * @param {Object} report - Report object
 * @param {string} reportPath - Путь к файлу отчета
 * @param {Object} contracts - Контракты
 * @returns {Promise<Object>} Results summary
 */
async function processBatchQueue(batchState, report, reportPath, contracts) {
  console.log(`\n${"=".repeat(70)}`);
  console.log("🚀 НАЧАЛО BATCH ОБРАБОТКИ");
  console.log(`${"=".repeat(70)}`);
  console.log(`📊 Всего компонентов: ${batchState.queue.total}`);
  console.log(`✅ Завершено: ${batchState.queue.completed.length}`);
  console.log(`❌ Ошибки: ${batchState.queue.failed.length}`);
  console.log(`⏳ Ожидают: ${batchState.queue.pending.length}`);
  
  const results = {
    successful: [],
    failed: [],
    skipped: []
  };
  
  let processedCount = batchState.queue.completed.length;
  
  // === STEP 3: Upload Shareable Data (если требуется) ===
  if (UPLOAD_SHAREABLE && !stateManager.isShareableDataUploaded(batchState)) {
    console.log(`\n${"=".repeat(70)}`);
    console.log("📚 ЗАГРУЗКА ГЛОБАЛЬНЫХ СЛОВАРЕЙ");
    console.log(`${"=".repeat(70)}`);
    
    try {
      // Создаем temporary context для shareable data
      const tempContext = createComponentContext('_global', contracts);
      
      const shareableResults = await uploadSteps.uploadShareableData(
        tempContext,
        batchState,
        (progress) => {
          console.log(`   → ${progress.substep}: ${progress.status}`);
        }
      );
      
      stateManager.markShareableDataUploaded(
        batchState,
        shareableResults.featuresCID,
        shareableResults.formsCID
      );
      
      stateManager.saveBatchState(COMPONENTS_DIR, batchState);
      
      // Добавить в report
      reportCollector.reportGlobalDictionaries(
        report,
        shareableResults.featuresCID,
        shareableResults.formsCID,
        1, // features version
        1  // forms version
      );
      
      reportCollector.saveReport(reportPath, report);
      
      console.log("✅ Глобальные словари загружены");
      
    } catch (error) {
      console.error("❌ Ошибка загрузки глобальных словарей:", error.message);
      console.warn("⚠️ Продолжаем без shareable data");
    }
  } else if (UPLOAD_SHAREABLE) {
    console.log("\n⏭️ Глобальные словари уже загружены, пропускаем");
  }
  
  // === Последовательная обработка компонентов ===
  let newUploadsInThisRun = 0;
  
  while (true) {
    let componentId = stateManager.getNextComponent(batchState);
    
    // Если нет pending компонентов, проверим completed и failed на необходимость blockchain registration
    if (!componentId && !ARWEAVE_ONLY && !DRY_RUN) {
      console.log("\n🔍 Проверка completed и failed компонентов на необходимость blockchain registration...");
      
      // Проверяем все completed компоненты
      for (const completedId of batchState.queue.completed) {
        const componentDir = utils.getComponentDir(COMPONENTS_DIR, completedId);
        const componentState = stateManager.loadComponentState(componentDir, network);
        
        if (stateManager.needsBlockchainRegistration(componentState, true)) {
          console.log(`   → ${completedId} (completed): нужна blockchain регистрация (Step 6)`);
          componentId = completedId;
          // Переместить обратно в pending для обработки
          batchState.queue.completed = batchState.queue.completed.filter(id => id !== completedId);
          batchState.queue.pending.unshift(completedId);
          batchState.components[completedId].status = "pending";
          stateManager.saveBatchState(COMPONENTS_DIR, batchState);
          break;
        }
      }
      
      // Проверяем также failed компоненты (могли упасть на Step 6)
      if (!componentId) {
        for (const failedId of batchState.queue.failed) {
          const componentDir = utils.getComponentDir(COMPONENTS_DIR, failedId);
          const componentState = stateManager.loadComponentState(componentDir, network);
          
          if (stateManager.needsBlockchainRegistration(componentState, true)) {
            console.log(`   → ${failedId} (failed): нужна blockchain регистрация (Step 6) - retry`);
            componentId = failedId;
            // Переместить из failed в pending для retry
            batchState.queue.failed = batchState.queue.failed.filter(id => id !== failedId);
            batchState.queue.pending.unshift(failedId);
            batchState.components[failedId].status = "pending";
            batchState.components[failedId].error = undefined; // Очищаем старую ошибку
            stateManager.saveBatchState(COMPONENTS_DIR, batchState);
            break;
          }
        }
      }
      
      if (!componentId) {
        console.log(`   → Все компоненты полностью обработаны (включая blockchain)`);
      }
    }
    
    if (!componentId) {
      console.log(`\n${"=".repeat(70)}`);
      console.log("📊 ЗАВЕРШЕНИЕ BATCH ОБРАБОТКИ");
      console.log(`${"=".repeat(70)}`);
      console.log(`✅ Все компоненты обработаны`);
      console.log(`   → Новых загрузок в этой сессии: ${newUploadsInThisRun}`);
      console.log(`   → Всего в queue: ${batchState.queue.total}`);
      console.log(`   → Уже было обработано: ${batchState.queue.completed.length - newUploadsInThisRun}`);
      
      if (newUploadsInThisRun === 0 && batchState.queue.completed.length > 0) {
        console.log("");
        console.log("💡 СОВЕТ: Компоненты уже были загружены ранее.");
        console.log("   Для повторной загрузки используйте:");
        console.log("   FORCE_UPLOAD=true npx hardhat run scripts/upload_all_components.js --network " + network);
      }
      
      console.log(`${"=".repeat(70)}`);
      break;
    }
    
    processedCount++;
    newUploadsInThisRun++;
    
    console.log(`\n${"=".repeat(70)}`);
    console.log(`📦 КОМПОНЕНТ ${processedCount}/${batchState.queue.total}: ${componentId}`);
    console.log(`🆕 Новая загрузка в этой сессии`);
    console.log(`${"=".repeat(70)}`);
    
    // Отметить как in_progress
    stateManager.markComponentInProgress(batchState, componentId);
    stateManager.saveBatchState(COMPONENTS_DIR, batchState);
    
    try {
      // Создать context для компонента
      const context = createComponentContext(componentId, contracts);
      
      // Progress callback
      const onProgress = (progress) => {
        // Можно логировать прогресс здесь
        if (progress.step && progress.status === 'completed') {
          console.log(`   ✅ ${progress.step} завершен`);
        }
      };
      
      // Загрузить компонент
      const componentResults = await uploadComponent(context, report, onProgress);
      
      // Отметить как completed
      stateManager.markComponentCompleted(batchState, componentId, componentResults);
      stateManager.saveBatchState(COMPONENTS_DIR, batchState);
      
      // Сохранить report (incremental)
      reportCollector.updateSummary(report);
      reportCollector.saveReport(reportPath, report);
      
      results.successful.push(componentId);
      
      // Показать прогресс
      const progress = stateManager.getBatchProgress(batchState);
      console.log(`\n📊 Общий прогресс: ${progress.completed}/${progress.total} (${progress.percentage}%)`);
      
      if (progress.estimatedTimeRemaining) {
        console.log(`   ⏱️ Осталось примерно: ${utils.formatDuration(progress.estimatedTimeRemaining)}`);
      }
      
    } catch (error) {
      console.error(`\n❌ Ошибка обработки ${componentId}:`, error.message);
      
      // Отметить как failed
      stateManager.markComponentFailed(batchState, componentId, error);
      stateManager.saveBatchState(COMPONENTS_DIR, batchState);
      
      // Сохранить report (failed component уже в report через failComponentTracking)
      reportCollector.updateSummary(report);
      reportCollector.saveReport(reportPath, report);
      
      results.failed.push({
        componentId,
        error: error.message
      });
      
      // Продолжаем со следующим (не падаем)
      console.warn(`⚠️ Пропускаем ${componentId}, продолжаем со следующим`);
    }
    
    // Небольшая задержка между компонентами (rate limiting)
    await utils.sleep(1000);
  }
  
  // === Финальная статистика ===
  console.log(`\n${"=".repeat(70)}`);
  console.log("📊 ИТОГОВАЯ СТАТИСТИКА");
  console.log(`${"=".repeat(70)}`);
  console.log(`✅ Успешно: ${results.successful.length}`);
  console.log(`❌ Ошибки: ${results.failed.length}`);
  console.log(`⏭️ Пропущено: ${results.skipped.length}`);
  console.log(`📝 Всего: ${batchState.queue.total}`);
  console.log(`🆕 Новых загрузок в этой сессии: ${newUploadsInThisRun}`);
  
  if (results.failed.length > 0) {
    console.log(`\n❌ Компоненты с ошибками:`);
    results.failed.forEach(({ componentId, error }) => {
      console.log(`   → ${componentId}: ${error}`);
    });
  }
  
  console.log(`${"=".repeat(70)}`);
  
  // Add newUploadsInThisRun to results
  results.newUploads = newUploadsInThisRun;
  
  return results;
}

// ====================================================================
// 🎯 ARWEAVE UTILITIES
// ====================================================================

/**
 * Проверка баланса Arweave кошелька
 */
async function checkArweaveBalance() {
  if (DRY_RUN) {
    console.log("\n💰 [DRY-RUN] Arweave баланс: N/A (dry-run режим)");
    return { balance: 0, balanceAR: "0", address: "mock" };
  }
  
  console.log("\n💰 Проверка Arweave баланса...");
  
  try {
    // Получить адрес кошелька
    const address = await arweave.wallets.jwkToAddress(arweaveKey);
    console.log(`   → Адрес: ${address}`);
    
    // Получить баланс в winston (1 AR = 1e12 winston)
    const winston = await arweave.wallets.getBalance(address);
    const balanceAR = arweave.ar.winstonToAr(winston);
    
    console.log(`   → Баланс: ${balanceAR} AR`);
    
    // Примерная стоимость в USD (если есть)
    // TODO: можно добавить fetch курса AR/USD
    
    // Предупреждение при низком балансе
    const balanceNum = parseFloat(balanceAR);
    if (balanceNum < 0.001) {
      console.warn(`\n⚠️ ВНИМАНИЕ: Низкий баланс Arweave (${balanceAR} AR)`);
      console.warn("   → Рекомендуется минимум 0.01 AR для загрузки компонентов");
      console.warn("   → Пополните кошелек: https://www.arweave.org/");
      console.warn(`   → Адрес для пополнения: ${address}`);
    } else {
      console.log(`✅ Баланс достаточный для загрузки`);
    }
    
    return { balance: winston, balanceAR, address };
    
  } catch (error) {
    console.error(`❌ Ошибка проверки баланса: ${error.message}`);
    throw error;
  }
}

// ====================================================================
// 🎯 MAIN FUNCTION
// ====================================================================

async function main() {
  console.log("\n" + "=".repeat(70));
  console.log("🚀 BATCH UPLOAD: ORGANIC COMPONENTS");
  console.log("=".repeat(70));
  console.log(`📦 Network: ${network.toUpperCase()}`);
  console.log(`👤 Deployer: ${deployerAccount.address}`);
  console.log(`🏪 Seller (создатель компонентов): ${sellerAccount.address}`);
  console.log(`🔷 Dry-run: ${DRY_RUN ? "ENABLED" : "DISABLED"}`);
  console.log("=".repeat(70));
  
  try {
    // 1. Проверка баланса Arweave
    const arweaveBalance = await checkArweaveBalance();
    
    // 2. Проверка баланса блокчейна (если нужно)
    if (!ARWEAVE_ONLY) {
      const balanceInfo = await utils.checkBalance(web3, deployerAccount.address, network);
      
      if (balanceInfo.isZero && !DRY_RUN) {
        console.warn("\n⚠️ ВНИМАНИЕ: Blockchain баланс равен 0!");
        console.warn("   Контрактные операции не будут выполнены.");
        console.warn("   Пополните баланс перед production upload.");
      }
    }
    
    // 3. Поиск компонентов
    const components = discoverComponents();
    
    if (components.length === 0) {
      throw new Error("Нет компонентов для загрузки");
    }
    
    // 3. Загрузка или создание batch state
    let batchState = null;
    
    if (FORCE_UPLOAD) {
      console.log("\n🔄 FORCE_UPLOAD режим активен");
      
      // Backup старого state если существует
      const oldBatchState = stateManager.loadBatchState(COMPONENTS_DIR, network);
      if (oldBatchState) {
        const backupPath = path.join(COMPONENTS_DIR, `_batch_state_${network}_backup_${Date.now()}.json`);
        fs.writeFileSync(backupPath, JSON.stringify(oldBatchState, null, 2));
        console.log(`📦 Старый state сохранен в backup: ${path.basename(backupPath)}`);
      }
      
      console.log("🆕 Создание НОВОГО batch state (игнорируем старый)...");
    } else {
      batchState = stateManager.loadBatchState(COMPONENTS_DIR, network);
    }
    
    if (!batchState) {
      console.log("\n🆕 Создание нового batch state...");
      
      batchState = stateManager.createBatchState({
        network,
        deployer: deployerAccount.address,
        dryRun: DRY_RUN,
        uploadShareable: UPLOAD_SHAREABLE,
        components
      });
      
      stateManager.saveBatchState(COMPONENTS_DIR, batchState);
      console.log("✅ Batch state создан");
    } else {
      console.log("\n✅ Batch state загружен, продолжаем с сохраненного прогресса");
      console.log(`   → Session ID: ${batchState.session.session_id}`);
      console.log(`   → Started: ${batchState.session.started_at}`);
      console.log(`   → Completed: ${batchState.queue.completed.length}/${batchState.queue.total}`);
      console.log(`   → Pending: ${batchState.queue.pending.length}`);
      console.log(`   → Failed: ${batchState.queue.failed.length}`);
    }
    
    // 3.5 Создание или загрузка report
    const reportPath = reportCollector.getReportPath(
      COMPONENTS_DIR,
      network,
      batchState.session.session_id
    );
    
    let report = reportCollector.loadReport(reportPath);
    
    if (!report) {
      console.log("\n🆕 Создание нового report...");
      report = reportCollector.createReport(batchState.session);
      reportCollector.saveReport(reportPath, report);
      console.log(`✅ Report создан: ${path.basename(reportPath)}`);
    } else {
      console.log(`\n✅ Report загружен: ${path.basename(reportPath)}`);
    }
    
    // 4. Подключение к контрактам (если не dry-run и не arweave-only)
    let contracts = null;
    
    if (!DRY_RUN && !ARWEAVE_ONLY) {
      console.log("\n🔷 Подключение к контрактам...");
      console.log(`   → Сеть: ${network}`);
      console.log(`   → AmanitaInternational: ${AMANITA_INTERNATIONAL_PROXY}`);
      console.log(`   → OrganicComponentRegistry: ${ORGANIC_COMPONENT_REGISTRY_PROXY}`);
      
      const amanitaInternational = await utils.loadUUPSContract(
        "AmanitaInternational",
        AMANITA_INTERNATIONAL_PROXY,
        web3
      );
      
      const organicComponentRegistry = await utils.loadUUPSContract(
        "OrganicComponentRegistry",
        ORGANIC_COMPONENT_REGISTRY_PROXY,
        web3
      );
      
      contracts = {
        amanitaInternational,
        organicComponentRegistry
      };
      
      console.log("✅ Контракты подключены");
    } else {
      const reason = DRY_RUN ? "DRY-RUN режим" : "ARWEAVE_ONLY режим";
      console.log(`\n🔷 Пропускаем подключение к контрактам (${reason})`);
      
      // Mock contracts для dry-run/arweave-only
      contracts = {
        amanitaInternational: { methods: {} },
        organicComponentRegistry: { methods: {} }
      };
    }
    
    // 5. Обработка очереди компонентов
    const results = await processBatchQueue(batchState, report, reportPath, contracts);
    
    // 6. Финализация report
    console.log("\n🔷 Финализация отчета...");
    reportCollector.finalizeReport(report);
    reportCollector.saveReport(reportPath, report);
    console.log(`✅ Финальный отчет сохранен: ${path.basename(reportPath)}`);
    
    // 7. Вывод summary
    reportCollector.printSummary(report);
    
    console.log(`\n💾 Файлы сохранены:`);
    console.log(`   → Batch state: _batch_state_${network}.json`);
    console.log(`   → Report: ${path.basename(reportPath)}`);
    
    if (DRY_RUN) {
      console.log("\n🔷 [DRY-RUN] Это был тестовый запуск.");
      console.log("   Для реальной загрузки запустите без DRY_RUN=true");
    }
    
    console.log("=".repeat(70));
    
    // Exit code based on results
    if (results.failed.length > 0) {
      console.log("\n⚠️ Некоторые компоненты не были загружены.");
      console.log("   Проверьте ошибки выше и запустите скрипт повторно для retry.");
      process.exit(1);
    }
    
  } catch (error) {
    console.error("\n" + "=".repeat(70));
    console.error("❌ КРИТИЧЕСКАЯ ОШИБКА");
    console.error("=".repeat(70));
    console.error(`Сообщение: ${error.message}`);
    console.error(`\nStack trace:\n${error.stack}`);
    console.error("\n💾 Прогресс сохранен, можно продолжить позже");
    console.error("=".repeat(70));
    process.exit(1);
  }
}

// ====================================================================
// 🚀 EXECUTION
// ====================================================================

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

