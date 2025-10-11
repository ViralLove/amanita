/**
 * 🧬 Organic Components Upload Script
 * 
 * Скрипт для загрузки органических компонентов в Arweave и регистрации в смарт-контрактах
 * Основан на инфраструктуре deploy_full.js
 * 
 * @version 1.0.0
 * @date 2025-10-08
 * 
 * Использование:
 * # Dry-run (тестирование)
 * DRY_RUN=true COMPONENT_ID=amanita_muscaria npx hardhat run scripts/upload_organic_component.js --network localhost
 * 
 * # Production
 * COMPONENT_ID=amanita_muscaria npx hardhat run scripts/upload_organic_component.js --network polygon
 * 
 * # С загрузкой shareable data
 * COMPONENT_ID=amanita_muscaria UPLOAD_SHAREABLE=true npx hardhat run scripts/upload_organic_component.js --network polygon
 * 
 * См. анализ: scripts/docs/AIJournal.md
 */

// ====================================================================
// 🔧 INFRASTRUCTURE SETUP (from deploy_full.js)
// ====================================================================

require("dotenv").config();
const { Web3 } = require("web3");
const Arweave = require("arweave");
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

// === NETWORK CONFIGURATION ===
const network = hre.network.name;
const deployerPrivateKey = process.env.DEPLOYER_PRIVATE_KEY.startsWith('0x') 
  ? process.env.DEPLOYER_PRIVATE_KEY 
  : `0x${process.env.DEPLOYER_PRIVATE_KEY}`;

// === CONTRACT ADDRESSES ===
const AMANITA_INTERNATIONAL_PROXY = process.env.AMANITA_INTERNATIONAL_PROXY_ADDRESS;
const ORGANIC_COMPONENT_REGISTRY_PROXY = process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS;

console.log("🔷 Конфигурация сети:", network.toUpperCase());
console.log("📍 AmanitaInternational Proxy:", AMANITA_INTERNATIONAL_PROXY);
console.log("📍 OrganicComponentRegistry Proxy:", ORGANIC_COMPONENT_REGISTRY_PROXY);

// === RPC URL CONFIGURATION ===
let RPC_URL;
if (network === 'polygon') {
  RPC_URL = process.env.POLYGON_MAINNET_RPC || "https://polygon-rpc.com";
} else if (network === 'mumbai') {
  RPC_URL = process.env.POLYGON_MUMBAI_RPC || "https://rpc-mumbai.maticvigil.com";
} else {
  RPC_URL = hre.network.config.url;
}
console.log("🌐 RPC URL:", RPC_URL);

// === WEB3 INITIALIZATION ===
const web3 = new Web3(RPC_URL);
const deployerAccount = web3.eth.accounts.privateKeyToAccount(deployerPrivateKey);
web3.eth.accounts.wallet.add(deployerAccount);

console.log("👤 Deployer address:", deployerAccount.address);

// === COMPONENT CONFIGURATION ===
const COMPONENT_ID = process.env.COMPONENT_ID || "amanita_muscaria";
const COMPONENT_DIR = path.join(__dirname, "organic_components", COMPONENT_ID);
const UPLOAD_SHAREABLE = process.env.UPLOAD_SHAREABLE === "true";
const DRY_RUN = process.env.DRY_RUN === "true";

// === ARWEAVE CONFIGURATION ===
const arweave = Arweave.init({
  host: 'arweave.net',
  port: 443,
  protocol: 'https'
});

let arweaveKey = null;
if (!DRY_RUN) {
  const ARWEAVE_PRIVATE_KEY = process.env.ARWEAVE_PRIVATE_KEY;
  if (!ARWEAVE_PRIVATE_KEY) {
    throw new Error("ARWEAVE_PRIVATE_KEY не найден в .env (требуется для загрузки в Arweave)");
  }
  try {
    arweaveKey = JSON.parse(ARWEAVE_PRIVATE_KEY);
    console.log("✅ Arweave ключ загружен");
  } catch (error) {
    throw new Error("Ошибка парсинга ARWEAVE_PRIVATE_KEY: " + error.message);
  }
} else {
  console.log("🔷 Dry-run режим: Arweave ключ не требуется");
}

// === SUPPORTED LANGUAGES ===
const SUPPORTED_LANGUAGES = ["ru", "et", "en", "es", "fr", "de", "nl"];

// === STATE FILE (для продолжения с середины процесса) ===
const STATE_FILE = path.join(COMPONENT_DIR, `_upload_state_${network}.json`);

console.log("📦 Component ID:", COMPONENT_ID);
console.log("📁 Component Directory:", COMPONENT_DIR);
console.log("🌍 Supported Languages:", SUPPORTED_LANGUAGES.join(", "));
console.log("🔷 Dry-run Mode:", DRY_RUN ? "ENABLED" : "DISABLED");
console.log("📄 State File:", STATE_FILE);

// ====================================================================
// 🛠️ UTILITY FUNCTIONS (from deploy_full.js patterns)
// ====================================================================

/**
 * Загрузка артефакта контракта
 * @param {string} contractName - Название контракта
 * @returns {Object} Артефакт контракта с ABI
 */
async function loadContractArtifact(contractName) {
  const artifactPath = path.join(
    __dirname, 
    "..", 
    "artifacts", 
    "contracts", 
    `${contractName}.sol`, 
    `${contractName}.json`
  );
  
  if (!fs.existsSync(artifactPath)) {
    throw new Error(`Contract artifact not found for ${contractName}. Please compile the contract first.`);
  }
  
  return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

/**
 * Загрузка UUPS контракта (Logic ABI + Proxy address)
 * @param {string} contractName - Название контракта (без суффикса Logic)
 * @param {string} proxyAddress - Адрес Proxy контракта
 * @returns {Object} Web3 Contract instance
 */
async function loadUUPSContract(contractName, proxyAddress) {
  console.log(`🔷 Загружаем UUPS контракт ${contractName}`);
  console.log(`   → Proxy: ${proxyAddress}`);
  
  // Маппинг имен контрактов к Logic именам
  const CONTRACT_LOGIC_MAPPING = {
    'AmanitaInternational': 'AmanitaInternationalLogic',
    'OrganicComponentRegistry': 'OrganicComponentRegistryLogic',
    'ProductRegistry': 'ProductRegistryLogic',
    'SpiralEngine': 'SpiralEngineLogic'
  };
  
  // Определяем имя Logic контракта
  const logicContractName = CONTRACT_LOGIC_MAPPING[contractName] || `${contractName}Logic`;
  const artifact = await loadContractArtifact(logicContractName);
  
  console.log(`   → Logic ABI: ${logicContractName}`);
  
  return new web3.eth.Contract(artifact.abi, proxyAddress);
}

/**
 * Чтение JSON файла
 * @param {string} filepath - Относительный путь к файлу
 * @returns {Object} Parsed JSON
 */
function readJSON(filepath) {
  const fullPath = path.join(COMPONENT_DIR, filepath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Файл не найден: ${fullPath}`);
  }
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

/**
 * Сохранение JSON файла
 * @param {string} filepath - Относительный путь к файлу
 * @param {Object} data - Данные для сохранения
 */
function saveJSON(filepath, data) {
  const fullPath = path.join(COMPONENT_DIR, filepath);
  fs.writeFileSync(fullPath, JSON.stringify(data, null, 2));
  console.log(`💾 Сохранено: ${filepath}`);
}

/**
 * Получение текущей цены газа с учетом сети
 * @returns {string} Gas price в Wei
 */
async function getGasPrice() {
  if (network === 'polygon') {
    return web3.utils.toWei('100', 'gwei'); // 100 Gwei для Polygon mainnet
  }
  return await web3.eth.getGasPrice();
}

/**
 * Получение лимита газа с учетом сети
 * @param {number} defaultGas - Дефолтный лимит
 * @returns {number} Gas limit
 */
function getGasLimit(defaultGas = 500000) {
  return network === 'polygon' ? 30000000 : defaultGas;
}

// ====================================================================
// 💾 STATE MANAGEMENT (для продолжения с середины)
// ====================================================================

/**
 * Загрузить state из файла
 * @returns {Object} State объект или пустой state
 */
function loadState() {
  console.log("💾 Загрузка state...");
  
  // Проверяем существование state файла
  if (fs.existsSync(STATE_FILE)) {
    try {
      const stateData = fs.readFileSync(STATE_FILE, "utf8");
      const state = JSON.parse(stateData);
      
      console.log(`✅ State загружен из ${STATE_FILE}`);
      console.log(`📊 Выполнено шагов: ${state.steps_completed.length}`);
      
      if (state.steps_completed.length > 0) {
        console.log(`   → Последние шаги: ${state.steps_completed.slice(-3).join(", ")}`);
      }
      
      return state;
    } catch (error) {
      console.warn(`⚠️ Ошибка загрузки state из ${STATE_FILE}:`, error.message);
      console.warn("   → Создаем новый state");
    }
  } else {
    console.log(`🆕 State файл не найден, создаем новый: ${STATE_FILE}`);
  }
  
  // Возвращаем пустой state с дефолтной структурой
  return {
    component_id: COMPONENT_ID,
    network: network,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    steps_completed: [],
    simple_fields: {},
    complex_fields: {},
    shareable_data: {},
    root_metadata: {},
    contract_registration: {}
  };
}

/**
 * Сохранить state в файл
 * @param {Object} state - State объект для сохранения
 */
function saveState(state) {
  console.log("💾 Сохранение state...");
  
  try {
    // Обновляем timestamp
    state.updated_at = new Date().toISOString();
    
    // Проверяем существование директории компонента
    if (!fs.existsSync(COMPONENT_DIR)) {
      console.log(`📁 Создаем директорию: ${COMPONENT_DIR}`);
      fs.mkdirSync(COMPONENT_DIR, { recursive: true });
    }
    
    // Сохраняем state в файл с форматированием
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
    
    console.log(`✅ State сохранен: ${STATE_FILE}`);
    console.log(`📊 Выполнено шагов: ${state.steps_completed.length}`);
    
  } catch (error) {
    console.error(`❌ Ошибка сохранения state в ${STATE_FILE}:`, error.message);
    throw error;
  }
}

/**
 * Проверить, был ли шаг уже выполнен
 * @param {Object} state - State объект
 * @param {string} stepName - Название шага
 * @returns {boolean} true если шаг уже выполнен
 */
function isStepCompleted(state, stepName) {
  if (!state || !state.steps_completed) {
    return false;
  }
  
  return state.steps_completed.includes(stepName);
}

/**
 * Отметить шаг как выполненный
 * @param {Object} state - State объект
 * @param {string} stepName - Название шага
 */
function markStepCompleted(state, stepName) {
  // Инициализируем массив если не существует
  if (!state.steps_completed) {
    state.steps_completed = [];
  }
  
  // Проверяем, что шаг еще не добавлен (избегаем дубликатов)
  if (!state.steps_completed.includes(stepName)) {
    state.steps_completed.push(stepName);
    console.log(`✅ Шаг "${stepName}" отмечен как выполненный`);
  } else {
    console.log(`⚠️ Шаг "${stepName}" уже был отмечен ранее`);
  }
}

// ====================================================================
// 📤 ARWEAVE INTEGRATION
// ====================================================================

/**
 * Загрузка JSON в Arweave
 * @param {Object} data - Данные для загрузки
 * @param {string} filename - Имя файла для логирования
 * @param {boolean} dryRun - Режим dry-run (не загружать реально)
 * @returns {Promise<string>} Arweave TX ID (используется как CID)
 */
async function uploadToArweave(data, filename, dryRun = false) {
  console.log(`📤 Загрузка ${filename} в Arweave...`);
  
  // Если dry-run режим → вернуть mock TX ID
  if (dryRun) {
    const mockTxId = `DRYRUN_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    console.log(`🔷 [DRY-RUN] Mock TX ID: ${mockTxId}`);
    return mockTxId;
  }
  
  // Реальная загрузка в Arweave
  try {
    // Конвертируем данные в JSON строку
    const dataString = JSON.stringify(data, null, 2);
    
    // Создаем transaction
    const transaction = await arweave.createTransaction({
      data: dataString
    }, arweaveKey);
    
    // Добавляем tags для метаданных
    transaction.addTag('Content-Type', 'application/json');
    transaction.addTag('App-Name', 'Amanita-Organic-Components');
    transaction.addTag('File-Name', filename);
    transaction.addTag('Type', 'organic-component-metadata');
    transaction.addTag('Version', '1.0.0');
    
    // Подписываем transaction
    await arweave.transactions.sign(transaction, arweaveKey);
    
    // Отправляем transaction
    const response = await arweave.transactions.post(transaction);
    
    if (response.status === 200) {
      console.log(`✅ ${filename} загружен: ${transaction.id}`);
      console.log(`🔗 https://arweave.net/${transaction.id}`);
      return transaction.id;
    } else {
      throw new Error(`Arweave API вернул статус ${response.status}`);
    }
    
  } catch (error) {
    console.error(`❌ Ошибка загрузки ${filename} в Arweave:`, error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 1: UPLOAD SIMPLE FIELDS
// ====================================================================

/**
 * Загрузка Simple Fields в Arweave и сохранение CID в контракте
 * @param {Object} amanitaInternational - Контракт AmanitaInternational
 * @param {Object} state - State объект для сохранения прогресса
 * @returns {Promise<Object>} Маппинг field → CID
 */
async function uploadSimpleFields(amanitaInternational, state) {
  console.log("\n🔹 ШАГ 1: Загрузка Simple Fields");
  
  // Проверяем, был ли шаг уже выполнен
  if (isStepCompleted(state, 'simple_fields_uploaded')) {
    console.log("✅ Шаг уже выполнен, используем сохраненные данные");
    return state.simple_fields;
  }
  
  const simpleFieldCIDs = {};
  
  try {
    // 1. Загрузка ComponentDescription.title.json
    console.log("\n📝 1.1. ComponentDescription.title");
    const titleFilePath = `simple_fields/${COMPONENT_ID}.ComponentDescription.title.json`;
    const titleData = readJSON(titleFilePath);
    
    const titleFilename = `${COMPONENT_ID}_ComponentDescription_title.json`;
    const titleCID = await uploadToArweave(titleData, titleFilename, DRY_RUN);
    
    simpleFieldCIDs.title = {
      cid: titleCID,
      label: "ComponentDescription.title",
      file_path: titleFilePath
    };
    
    // Сохраняем CID в контракте (если не dry-run)
    if (!DRY_RUN) {
      console.log("🔷 Сохраняем CID в AmanitaInternational...");
      const gasPrice = await getGasPrice();
      await amanitaInternational.methods.setSimpleFieldCID(
        "ComponentDescription.title",
        titleCID
      ).send({
        from: deployerAccount.address,
        gas: getGasLimit(300000),
        gasPrice: gasPrice
      });
      console.log("✅ CID сохранен в контракте");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
    }
    
    // 2. Загрузка DosageInstruction.description.json
    console.log("\n📝 1.2. DosageInstruction.description");
    const dosageFilePath = `simple_fields/${COMPONENT_ID}.DosageInstruction.description.json`;
    const dosageData = readJSON(dosageFilePath);
    
    const dosageFilename = `${COMPONENT_ID}_DosageInstruction_description.json`;
    const dosageCID = await uploadToArweave(dosageData, dosageFilename, DRY_RUN);
    
    simpleFieldCIDs.dosage_types = {
      cid: dosageCID,
      label: "DosageInstruction.description",
      file_path: dosageFilePath
    };
    
    // Сохраняем CID в контракте (если не dry-run)
    if (!DRY_RUN) {
      console.log("🔷 Сохраняем CID в AmanitaInternational...");
      const gasPrice = await getGasPrice();
      await amanitaInternational.methods.setSimpleFieldCID(
        "DosageInstruction.description",
        dosageCID
      ).send({
        from: deployerAccount.address,
        gas: getGasLimit(300000),
        gasPrice: gasPrice
      });
      console.log("✅ CID сохранен в контракте");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
    }
    
    // Сохраняем state
    state.simple_fields = simpleFieldCIDs;
    markStepCompleted(state, 'simple_fields_uploaded');
    saveState(state);
    
    console.log("\n✅ ШАГ 1 завершен: Simple Fields загружены");
    
    return simpleFieldCIDs;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 1:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 2: UPLOAD COMPLEX FIELDS
// ====================================================================

/**
 * Загрузка Complex Fields в Arweave и сохранение CID в контракте
 * @param {Object} amanitaInternational - Контракт AmanitaInternational
 * @param {Object} state - State объект для сохранения прогресса
 * @returns {Promise<Object>} Маппинг language → CID
 */
async function uploadComplexFields(amanitaInternational, state) {
  console.log("\n🔹 ШАГ 2: Загрузка Complex Fields");
  
  // Проверяем, был ли шаг уже выполнен
  if (isStepCompleted(state, 'complex_fields_uploaded')) {
    console.log("✅ Шаг уже выполнен, используем сохраненные данные");
    return state.complex_fields;
  }
  
  const complexFieldCIDs = {};
  let processedCount = 0;
  
  try {
    // Цикл по всем поддерживаемым языкам
    for (const lang of SUPPORTED_LANGUAGES) {
      console.log(`\n📝 2.${processedCount + 1}. ComponentDescription.${lang}`);
      
      const filePath = `complex_fields/${COMPONENT_ID}.ComponentDescription.${lang}.json`;
      
      try {
        // Читаем файл описания для текущего языка
        const descData = readJSON(filePath);
        
        const filename = `${COMPONENT_ID}_ComponentDescription_${lang}.json`;
        const descCID = await uploadToArweave(descData, filename, DRY_RUN);
        
        complexFieldCIDs[lang] = {
          cid: descCID,
          label: "ComponentDescription",
          file_path: filePath
        };
        
        // Сохраняем CID в контракте (если не dry-run)
        if (!DRY_RUN) {
          console.log("🔷 Сохраняем CID в AmanitaInternational...");
          const gasPrice = await getGasPrice();
          await amanitaInternational.methods.setComplexFieldCID(
            "ComponentDescription",
            lang,
            descCID
          ).send({
            from: deployerAccount.address,
            gas: getGasLimit(300000),
            gasPrice: gasPrice
          });
          console.log("✅ CID сохранен в контракте");
        } else {
          console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
        }
        
        processedCount++;
        
      } catch (fileError) {
        console.warn(`⚠️ Файл не найден или ошибка чтения: ${filePath}`);
        console.warn(`   Пропускаем язык: ${lang}`);
        // Продолжаем со следующим языком
      }
    }
    
    if (processedCount === 0) {
      throw new Error("Ни один файл complex fields не был загружен");
    }
    
    console.log(`\n📊 Обработано языков: ${processedCount} из ${SUPPORTED_LANGUAGES.length}`);
    
    // Сохраняем state
    state.complex_fields = complexFieldCIDs;
    markStepCompleted(state, 'complex_fields_uploaded');
    saveState(state);
    
    console.log("\n✅ ШАГ 2 завершен: Complex Fields загружены");
    
    return complexFieldCIDs;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 2:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 3: UPLOAD SHAREABLE DATA
// ====================================================================

/**
 * Загрузка глобальных словарей (features, component_forms) в Arweave
 * @param {Object} organicComponentRegistry - Контракт OrganicComponentRegistry
 * @param {Object} state - State объект для сохранения прогресса
 * @returns {Promise<Object>} { featuresCID, formsCID }
 */
async function uploadShareableData(organicComponentRegistry, state) {
  console.log("\n🔹 ШАГ 3: Загрузка глобальных словарей");
  
  // Проверяем, был ли шаг уже выполнен
  if (isStepCompleted(state, 'shareable_data_uploaded')) {
    console.log("✅ Шаг уже выполнен, используем сохраненные данные");
    return state.shareable_data;
  }
  
  try {
    // 1. Загрузка features.json
    console.log("\n📝 3.1. features.json");
    const featuresPath = path.join(__dirname, "..", "bot", "catalog", "features.json");
    const featuresData = JSON.parse(fs.readFileSync(featuresPath, "utf8"));
    
    const featuresCID = await uploadToArweave(
      featuresData,
      "features_global_dictionary.json",
      DRY_RUN
    );
    console.log(`✅ Features загружены: ${featuresCID}`);
    
    // 2. Загрузка component_forms.json
    console.log("\n📝 3.2. component_forms.json");
    const formsPath = path.join(__dirname, "..", "bot", "catalog", "component_forms.json");
    const formsData = JSON.parse(fs.readFileSync(formsPath, "utf8"));
    
    const formsCID = await uploadToArweave(
      formsData,
      "component_forms_global_dictionary.json",
      DRY_RUN
    );
    console.log(`✅ Component forms загружены: ${formsCID}`);
    
    // 3. Сохраняем CID в контракте (если не dry-run)
    if (!DRY_RUN) {
      console.log("\n🔷 Обновляем shareable data в OrganicComponentRegistry...");
      const gasPrice = await getGasPrice();
      await organicComponentRegistry.methods.updateShareableData(
        featuresCID,
        formsCID,
        1, // features version
        1  // forms version
      ).send({
        from: deployerAccount.address,
        gas: getGasLimit(500000),
        gasPrice: gasPrice
      });
      console.log("✅ Shareable data обновлены в контракте");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем обновление в контракте");
    }
    
    const shareableData = { featuresCID, formsCID };
    
    // Сохраняем state
    state.shareable_data = shareableData;
    markStepCompleted(state, 'shareable_data_uploaded');
    saveState(state);
    
    console.log("\n✅ ШАГ 3 завершен: Shareable Data загружены");
    
    return shareableData;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 3:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 4: UPDATE ROOT METADATA
// ====================================================================

/**
 * Создание финального root metadata с полученными CID
 * @param {Object} simpleFieldCIDs - CID простых полей
 * @param {Object} complexFieldCIDs - CID сложных полей
 * @param {Object} state - State объект
 * @returns {Object} Финальные метаданные для загрузки
 */
function updateRootMetadata(simpleFieldCIDs, complexFieldCIDs, state) {
  console.log("\n🔹 ШАГ 4: Создание финального Root Metadata");
  
  try {
    // 1. Читаем оригинальный root файл
    console.log(`📖 Чтение оригинального файла: ${COMPONENT_ID}.json`);
    const rootData = readJSON(`${COMPONENT_ID}.json`);
    
    // 2. Создаем финальную структуру с CID references
    const finalRootData = {
      ...rootData,
      localizations: {
        simple_fields: simpleFieldCIDs,
        complex_fields: complexFieldCIDs
      },
      last_updated: new Date().toISOString(),
      network: network
    };
    
    // 3. Сохраняем финальный root файл локально (для истории)
    const finalFileName = `${COMPONENT_ID}_final_${network}.json`;
    const finalRootPath = path.join(COMPONENT_DIR, finalFileName);
    
    fs.writeFileSync(finalRootPath, JSON.stringify(finalRootData, null, 2), "utf8");
    console.log(`💾 Финальный файл сохранен: ${finalFileName}`);
    
    // 4. Сохраняем в state
    state.root_metadata = {
      path: finalFileName,
      data: finalRootData
    };
    saveState(state);
    
    console.log("\n✅ ШАГ 4 завершен: Root Metadata обновлен");
    
    return finalRootData;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 4:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 5: UPLOAD ROOT METADATA
// ====================================================================

/**
 * Загрузка корневого метаданных в Arweave
 * @param {Object} rootData - Корневые метаданные
 * @param {Object} state - State объект
 * @returns {Promise<string>} Arweave TX ID (CID)
 */
async function uploadRootMetadata(rootData, state) {
  console.log("\n🔹 ШАГ 5: Загрузка Root Metadata");
  
  // Проверяем, был ли шаг уже выполнен
  if (isStepCompleted(state, 'root_metadata_uploaded')) {
    console.log("✅ Шаг уже выполнен, используем сохраненный CID");
    return state.root_metadata.cid;
  }
  
  try {
    // Загружаем root metadata в Arweave
    const filename = `${COMPONENT_ID}_root_metadata.json`;
    const rootCID = await uploadToArweave(rootData, filename, DRY_RUN);
    
    console.log(`✅ Root Metadata загружен: ${rootCID}`);
    
    // Сохраняем CID в state
    state.root_metadata.cid = rootCID;
    markStepCompleted(state, 'root_metadata_uploaded');
    saveState(state);
    
    console.log("\n✅ ШАГ 5 завершен: Root Metadata загружен в Arweave");
    
    return rootCID;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 5:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 6: REGISTER COMPONENT
// ====================================================================

/**
 * Регистрация компонента в OrganicComponentRegistry
 * @param {Object} organicComponentRegistry - Контракт OrganicComponentRegistry
 * @param {string} rootCID - Arweave TX ID корневых метаданных
 * @param {Object} state - State объект
 * @returns {Promise<number>} Component ID
 */
async function registerComponent(organicComponentRegistry, rootCID, state) {
  console.log("\n🔹 ШАГ 6: Регистрация в OrganicComponentRegistry");
  
  // Проверяем, был ли шаг уже выполнен
  if (isStepCompleted(state, 'component_registered')) {
    console.log("✅ Шаг уже выполнен, используем сохраненный componentId");
    return state.contract_registration.componentId;
  }
  
  // В dry-run режиме не регистрируем в контракте
  if (DRY_RUN) {
    console.log("🔷 [DRY-RUN] Пропускаем регистрацию в контракте");
    const mockComponentId = 999;
    
    state.contract_registration = {
      componentId: mockComponentId,
      txHash: "DRYRUN_TX_HASH",
      dry_run: true
    };
    markStepCompleted(state, 'component_registered');
    saveState(state);
    
    console.log(`🔷 [DRY-RUN] Mock Component ID: ${mockComponentId}`);
    console.log("\n✅ ШАГ 6 завершен (DRY-RUN)");
    
    return mockComponentId;
  }
  
  try {
    // Регистрируем компонент в контракте
    console.log(`📝 Регистрируем компонент: ${COMPONENT_ID}`);
    console.log(`📄 Root CID: ${rootCID}`);
    
    const gasPrice = await getGasPrice();
    const tx = await organicComponentRegistry.methods.createComponent(
      COMPONENT_ID,
      rootCID
    ).send({
      from: deployerAccount.address,
      gas: getGasLimit(1000000),
      gasPrice: gasPrice
    });
    
    console.log(`📝 Транзакция отправлена: ${tx.transactionHash}`);
    
    // Получаем receipt
    const receipt = await web3.eth.getTransactionReceipt(tx.transactionHash);
    console.log(`✅ Транзакция подтверждена: блок ${receipt.blockNumber}`);
    
    // Извлекаем componentId из события ComponentCreated
    let componentId = null;
    
    for (const log of receipt.logs) {
      try {
        // Пытаемся распарсить лог как событие контракта
        const parsedLog = organicComponentRegistry._decodeEventABI.bind({
          name: 'allEvents',
          jsonInterface: organicComponentRegistry.options.jsonInterface
        })(log);
        
        if (parsedLog && parsedLog.event === 'ComponentCreated') {
          componentId = parsedLog.returnValues.componentId;
          console.log(`🎉 Компонент создан с ID: ${componentId}`);
          break;
        }
      } catch (parseError) {
        // Пропускаем логи, которые не относятся к нашему контракту
        continue;
      }
    }
    
    if (!componentId) {
      // Fallback: пытаемся найти componentId другим способом
      console.warn("⚠️ Не удалось извлечь componentId из события, используем fallback");
      componentId = receipt.logs.length > 0 ? 1 : 0; // Fallback значение
    }
    
    // Сохраняем в state
    state.contract_registration = {
      componentId: componentId,
      txHash: tx.transactionHash,
      blockNumber: receipt.blockNumber
    };
    markStepCompleted(state, 'component_registered');
    saveState(state);
    
    console.log("\n✅ ШАГ 6 завершен: Компонент зарегистрирован в контракте");
    
    return componentId;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 6:", error.message);
    throw error;
  }
}

// ====================================================================
// 🎯 MAIN FUNCTION
// ====================================================================

/**
 * Основная функция загрузки компонента
 */
async function main() {
  console.log("\n" + "=".repeat(60));
  console.log("🚀 Начало загрузки органического компонента");
  console.log("=".repeat(60));
  console.log(`📦 Component ID: ${COMPONENT_ID}`);
  console.log(`📁 Component Directory: ${COMPONENT_DIR}`);
  console.log(`🌐 Network: ${network.toUpperCase()}`);
  console.log(`👤 Deployer: ${deployerAccount.address}`);
  console.log(`🔷 Dry-run: ${DRY_RUN ? "ENABLED" : "DISABLED"}`);
  console.log(`📤 Upload Shareable: ${UPLOAD_SHAREABLE ? "YES" : "NO"}`);
  
  // 1. Проверка существования директории
  if (!fs.existsSync(COMPONENT_DIR)) {
    throw new Error(`Директория компонента не найдена: ${COMPONENT_DIR}`);
  }
  
  // 2. Проверка баланса деплоера
  const balance = await web3.eth.getBalance(deployerAccount.address);
  const currency = network === 'polygon' ? 'MATIC' : 'ETH';
  console.log(`💰 Баланс: ${web3.utils.fromWei(balance, 'ether')} ${currency}`);
  
  if (parseFloat(web3.utils.fromWei(balance, 'ether')) === 0 && !DRY_RUN) {
    console.warn("⚠️ ВНИМАНИЕ: Баланс равен 0! Контрактные операции не выполнятся.");
  }
  
  // 3. Загрузка state
  const state = loadState();
  console.log(`📊 Прогресс: ${state.steps_completed.length} шагов завершено`);
  
  try {
    // 4. Подключение к контрактам
    console.log("\n🔷 Подключение к контрактам...");
    const amanitaInternational = await loadUUPSContract(
      "AmanitaInternational",
      AMANITA_INTERNATIONAL_PROXY
    );
    const organicComponentRegistry = await loadUUPSContract(
      "OrganicComponentRegistry",
      ORGANIC_COMPONENT_REGISTRY_PROXY
    );
    console.log("✅ Контракты подключены");
    
    // 5. Последовательное выполнение шагов
    const simpleFieldCIDs = await uploadSimpleFields(amanitaInternational, state);
    const complexFieldCIDs = await uploadComplexFields(amanitaInternational, state);
    
    // Шаг 3 опционален
    if (UPLOAD_SHAREABLE) {
      await uploadShareableData(organicComponentRegistry, state);
    } else {
      console.log("\n⏭️ ШАГ 3: Пропущен (UPLOAD_SHAREABLE !== true)");
    }
    
    const rootData = updateRootMetadata(simpleFieldCIDs, complexFieldCIDs, state);
    const rootCID = await uploadRootMetadata(rootData, state);
    const componentId = await registerComponent(organicComponentRegistry, rootCID, state);
    
    // 6. Финальный отчет
    console.log("\n" + "=".repeat(60));
    console.log("🎉 ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО!");
    console.log("=".repeat(60));
    console.log(`📦 Component ID: ${COMPONENT_ID}`);
    console.log(`🔢 Blockchain Component ID: ${componentId}`);
    console.log(`📄 Root Metadata CID: ${rootCID}`);
    console.log(`🔗 Arweave Gateway: https://arweave.net/${rootCID}`);
    console.log(`💾 State File: ${STATE_FILE}`);
    console.log("=".repeat(60));
    
    if (DRY_RUN) {
      console.log("\n🔷 [DRY-RUN] Это был тестовый запуск.");
      console.log("   Для реальной загрузки запустите без DRY_RUN=true");
    }
    
  } catch (error) {
    console.error("\n" + "=".repeat(60));
    console.error("❌ ОШИБКА ПРИ ЗАГРУЗКЕ КОМПОНЕНТА");
    console.error("=".repeat(60));
    console.error(`Сообщение: ${error.message}`);
    console.error(`\nStack trace:\n${error.stack}`);
    console.error("\n💾 State сохранен, можно продолжить с текущего шага");
    console.error("=".repeat(60));
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

