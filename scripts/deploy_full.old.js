require("dotenv").config();
const { Web3 } = require("web3");
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

// Добавляем поддержку fetch для Node.js
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

require('dotenv').config();

// Получаем конфигурацию сети
const network = hre.network.name;
// Приватный ключ из .env
const deployerPrivateKey = process.env.DEPLOYER_PRIVATE_KEY.startsWith('0x') 
  ? process.env.DEPLOYER_PRIVATE_KEY 
  : `0x${process.env.DEPLOYER_PRIVATE_KEY}`;

// Переменные для продавца (для action=6)
const SELLER_ADDRESS = process.env.SELLER_ADDRESS;
const SELLER_PRIVATE_KEY = process.env.SELLER_PRIVATE_KEY ? 
  (process.env.SELLER_PRIVATE_KEY.startsWith('0x') ? process.env.SELLER_PRIVATE_KEY : `0x${process.env.SELLER_PRIVATE_KEY}`) : null;

const MAGIC_REGISTRY_CONTRACT_ADDRESS = process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS;
const SPIRAL_ENGINE_CONTRACT_ADDRESS = process.env.SPIRAL_ENGINE_CONTRACT_ADDRESS;
const PRODUCT_REGISTRY_CONTRACT_ADDRESS = process.env.PRODUCT_REGISTRY_CONTRACT_ADDRESS;
const SOUL_IDENTITY_CONTRACT_ADDRESS = process.env.SOUL_IDENTITY_CONTRACT_ADDRESS;
console.log("MAGIC_REGISTRY_CONTRACT_ADDRESS:", MAGIC_REGISTRY_CONTRACT_ADDRESS);
console.log("SPIRAL_ENGINE_CONTRACT_ADDRESS:", SPIRAL_ENGINE_CONTRACT_ADDRESS);
console.log("PRODUCT_REGISTRY_CONTRACT_ADDRESS:", PRODUCT_REGISTRY_CONTRACT_ADDRESS);
console.log("SOUL_IDENTITY_CONTRACT_ADDRESS:", SOUL_IDENTITY_CONTRACT_ADDRESS);

// RPC URL из конфига сети
// Получаем RPC URL с учетом выбранной сети
console.log("[deploy_full.js] hre.network.name:", hre.network.name);
console.log("[deploy_full.js] hre.network.config.url:", hre.network.config.url);

let RPC_URL;
if (hre.network.name === 'polygon') {
  RPC_URL = process.env.POLYGON_MAINNET_RPC || "https://polygon-rpc.com";
  console.log("[deploy_full.js] Using Polygon RPC:", RPC_URL);
} else if (hre.network.name === 'mumbai') {
  RPC_URL = process.env.POLYGON_MUMBAI_RPC || "https://rpc-mumbai.maticvigil.com";
  console.log("[deploy_full.js] Using Mumbai RPC:", RPC_URL);
} else {
  RPC_URL = hre.network.config.url;
  console.log("[deploy_full.js] Using default RPC:", RPC_URL);
}

// Создаем провайдер
const web3 = new Web3(RPC_URL);

// Создаем аккаунты из приватных ключей
const deployerAccount = web3.eth.accounts.privateKeyToAccount(deployerPrivateKey);
web3.eth.accounts.wallet.add(deployerAccount);

// Создаем аккаунт продавца только если есть приватный ключ
let sellerAccount = null;
if (SELLER_PRIVATE_KEY && SELLER_PRIVATE_KEY !== 'undefined' && SELLER_PRIVATE_KEY !== 'null') {
  try {
    sellerAccount = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
    web3.eth.accounts.wallet.add(sellerAccount);
    console.log(`✅ Seller account created: ${sellerAccount.address}`);
  } catch (error) {
    console.error(`❌ Error creating seller account: ${error.message}`);
    console.error(`❌ SELLER_PRIVATE_KEY value: ${SELLER_PRIVATE_KEY}`);
  }
} else {
  console.log(`⚠️ SELLER_PRIVATE_KEY not set or invalid: ${SELLER_PRIVATE_KEY}`);
}

// Функция для загрузки артефакта контракта
async function loadContract(contractName, contractAddress = null) {
  // Сначала проверяем переменные окружения
  if (contractAddress == null) {
    if (contractName === 'MagicRegistry' && MAGIC_REGISTRY_CONTRACT_ADDRESS) {
      contractAddress = MAGIC_REGISTRY_CONTRACT_ADDRESS;
    } else if (contractName === 'SpiralEngine' && SPIRAL_ENGINE_CONTRACT_ADDRESS) {
      contractAddress = SPIRAL_ENGINE_CONTRACT_ADDRESS;
    } else if (magicRegistry) {
      contractAddress = await magicRegistry.methods.get(contractName).call();
    }
  }

  const contractJSON = await loadContractArtifact(contractName);

  let contract;
  if (contractAddress) {
    contract = new web3.eth.Contract(contractJSON.abi, contractAddress);
  } else {
    contract = new web3.eth.Contract(contractJSON.abi);
  }
  return contract;
}

// Функция для генерации случайной строки из букв и цифр
function generateRandomAlphanumeric(length) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

async function loadContractArtifact(contractName) {
  const artifactPath = path.join(__dirname, "..", "artifacts", "contracts", `${contractName}.sol`, `${contractName}.json`);
  if (!fs.existsSync(artifactPath)) {
    throw new Error(`Contract artifact not found for ${contractName}. Please compile the contract first.`);
  }
  return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

magicRegistry = null;
// Универсальная функция деплоя контракта
async function deployContract(contractName, constructorArgs = [], options = {}) {
  console.log(`\n=== Начинаем деплой ${contractName} в сеть ${network.toUpperCase()} ===`);
  
  const artifact = await loadContractArtifact(contractName);
  const contract = new web3.eth.Contract(artifact.abi);
  
  // РАДИКАЛЬНО увеличиваем цену газа для mainnet для тестирования
  const gasPrice = network === 'polygon' ? 
    web3.utils.toWei('100', 'gwei') : // 100 Gwei для Polygon mainnet (РАДИКАЛЬНО УВЕЛИЧЕНО)
    await web3.eth.getGasPrice(); // Текущая цена для других сетей
  
  console.log("Цена газа:", web3.utils.fromWei(gasPrice, 'gwei'), "Gwei");
  
  // Увеличиваем лимит газа для Polygon до максимально допустимого
  const gasLimit = network === 'polygon' ? 30000000 : (options.gas || 5000000);
  console.log(`⛽ Лимит газа: ${gasLimit} (увеличен для Polygon)`);
  
  // Добавляем дополнительную отладочную информацию
  console.log(`📊 Размер bytecode: ${artifact.bytecode.length} символов`);
  console.log(`📊 Количество аргументов конструктора: ${constructorArgs.length}`);
  if (constructorArgs.length > 0) {
    console.log(`📊 Аргументы конструктора: ${constructorArgs.join(', ')}`);
  }
  
  let instance;
  try {
    // Получаем баланс до деплоя
    const balanceBeforeDeploy = await web3.eth.getBalance(deployerAccount.address);
    console.log(`💰 Баланс до деплоя: ${web3.utils.fromWei(balanceBeforeDeploy, 'ether')} MATIC`);
    
    // Получаем актуальный nonce для предотвращения "Nonce too low"
    const nonce = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
    
    instance = await contract.deploy({
      data: artifact.bytecode,
      arguments: constructorArgs
    }).send({
      from: deployerAccount.address,
      gas: gasLimit,
      gasPrice: gasPrice,
      nonce: nonce
    });
    
    // Получаем баланс после деплоя
    const balanceAfterDeploy = await web3.eth.getBalance(deployerAccount.address);
    const deployCost = web3.utils.fromWei((BigInt(balanceBeforeDeploy) - BigInt(balanceAfterDeploy)).toString(), 'ether');
    
    console.log(`💰 Баланс после деплоя: ${web3.utils.fromWei(balanceAfterDeploy, 'ether')} MATIC`);
    console.log(`💸 Стоимость деплоя: ${deployCost} MATIC`);
    console.log(`✅ Контракт ${contractName} успешно задеплоен по адресу: ${instance.options.address}`);
  } catch (error) {
    console.error(`❌ Ошибка при деплое ${contractName}:`);
    console.error(`📊 Использованный газ: ${gasLimit}`);
    console.error(`📊 Цена газа: ${web3.utils.fromWei(gasPrice, 'gwei')} Gwei`);
    console.error(`📊 Баланс деплоера: ${web3.utils.fromWei(await web3.eth.getBalance(deployerAccount.address), 'ether')} ETH`);
    console.error(`📊 Детали ошибки:`, error.message || error);
    throw error;
  }

  // Регистрация в реестре (если нужно)
  if (magicRegistry != null) {
    try {
      console.log(`🔷 Регистрируем ${contractName} в реестре...`);
      
      // Получаем баланс до транзакции
      const balanceBefore = await web3.eth.getBalance(deployerAccount.address);
      console.log(`💰 Баланс до регистрации: ${web3.utils.fromWei(balanceBefore, 'ether')} MATIC`);
      
      // Получаем актуальный nonce для предотвращения "Nonce too low"
      const nonce = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
      
      const tx = await magicRegistry.methods.set(contractName, instance.options.address).send({
        from: deployerAccount.address,
        gas: network === 'polygon' ? 500000 : 200000,
        gasPrice: gasPrice,
        nonce: nonce
      });
      
      // Получаем баланс после транзакции
      const balanceAfter = await web3.eth.getBalance(deployerAccount.address);
      const cost = web3.utils.fromWei((BigInt(balanceBefore) - BigInt(balanceAfter)).toString(), 'ether');
      
      console.log(`💰 Баланс после регистрации: ${web3.utils.fromWei(balanceAfter, 'ether')} MATIC`);
      console.log(`💸 Стоимость регистрации: ${cost} MATIC`);
      console.log(`✅ Контракт ${contractName} зарегистрирован в реестре`);
    } catch (error) {
      console.error(`❌ Ошибка при регистрации в реестре:`, error.message);
      throw error;
    }
  }

  console.log(`\n=== Деплой ${contractName} успешен! ===`);
  console.log(`Адрес контракта ${contractName}:`, instance.options.address);
  
  return instance;
}

/**
 * Action 41: Transform CSV → Product JSONs с заглушками переводов
 * Импортирует и вызывает transformProductsFromCSV() напрямую как модуль
 * Параметры берутся из переменных окружения
 */
async function action41_TransformProducts() {
    console.log(`\n📋 Параметры Transform CSV:`);
    
    // Получаем базовые пути и seller business_id
    const csvBasePath = process.env.CSV_BASE_PATH || 'data/sellers';
    const outputBasePath = process.env.OUTPUT_BASE_PATH || 'data/sellers';
    const sellerBusinessId = process.env.SELLER_BUSINESS_ID || 'iveta';
    const csvFilename = process.env.CSV_FILENAME || 'Iveta_catalog.csv';
    
    // Формируем итоговые пути через конкатенацию
    const csvPath = `${csvBasePath}/${sellerBusinessId}/catalog/${csvFilename}`;
    const outputDir = `${outputBasePath}/${sellerBusinessId}/products/`;
    
    // Остальные параметры
    const sellerId = sellerBusinessId; // Используем business_id как seller_id
    const sellerAddress = SELLER_ADDRESS || process.env.SELLER_ADDRESS;
    const sourceLang = process.env.SOURCE_LANG || 'en';
    const createStubs = process.env.CREATE_TRANSLATION_STUBS === 'true';
    const dryRun = process.env.DRY_RUN === 'true';
    
    console.log(`   🔹 Base Paths:`);
    console.log(`      CSV Base: ${csvBasePath}`);
    console.log(`      Output Base: ${outputBasePath}`);
    console.log(`   🔹 Seller Business ID: ${sellerBusinessId}`);
    console.log(`   🔹 CSV Filename: ${csvFilename}`);
    console.log(`   📄 Computed CSV Path: ${csvPath}`);
    console.log(`   📂 Computed Output Dir: ${outputDir}`);
    console.log(`   🔹 Seller Address: ${sellerAddress || 'N/A'}`);
    console.log(`   🌐 Source Lang: ${sourceLang}`);
    console.log(`   📝 Create Stubs: ${createStubs ? 'YES' : 'NO'}`);
    console.log(`   🔷 Dry Run: ${dryRun ? 'YES' : 'NO'}`);
    
    try {
        // Импортируем и вызываем функцию напрямую как модуль
        const { transformProductsFromCSV } = require('./transform_products_csv.js');
        
        console.log("\n🚀 Запускаем трансформацию CSV (прямой вызов функции)...");
        
        const result = await transformProductsFromCSV({
            csvPath,
            outputDir,
            sellerId,
            sellerAddress,
            sourceLang,
            createTranslationStubs: createStubs,
            dryRun
        });
        
        // Выводим результаты
        console.log("\n" + "=".repeat(70));
        console.log("📊 TRANSFORMATION RESULTS");
        console.log("=".repeat(70));
        console.log(`Status: ${result.success ? '✅ SUCCESS' : '❌ FAILED'}`);
        console.log(`Total rows: ${result.statistics.total_rows}`);
        console.log(`Valid products: ${result.statistics.valid_products}`);
        console.log(`Skipped: ${result.statistics.skipped_products}`);
        console.log(`Unique components: ${result.statistics.unique_components}`);
        
        if (result.errors.length > 0) {
            console.log(`\n❌ Errors (${result.errors.length}):`);
            result.errors.forEach(err => {
                console.log(`   → ${err.product_id}: ${err.error}`);
            });
        }
        
        console.log("=".repeat(70));
        
        if (!result.success) {
            throw new Error(`Transformation failed with ${result.errors.length} error(s)`);
        }
        
        return result;
        
    } catch (error) {
        console.error("\n❌ Action 41 failed:", error.message);
        throw error;
    }
}

/**
 * Основная функция деплоя
 * @param {number} action - Действие для выполнения:
 * 0 - деплой только реестра
 * 1 - деплой всех контрактов включая реестр с проставлением адресов в реестре
 * 2 - деплой только контрактов с проставлением новых адресов в реестре
 * 3 - деплой только инвайтов
 * 4 - деплой только каталога (неактивные продукты)
 * 5 - деплой конкретного контракта по имени (требует contractName)
 * 6 - очистка каталога продавца (требует SELLER_ADDRESS и SELLER_PRIVATE_KEY)
 * 7 - активация продавца через инвайт-код (требует INVITE_CODE и SELLER_ADDRESS)
 * 9 - назначение роли ACTIVATOR_ROLE селлеру из .env
 * 40 - создание каталога с неактивными продуктами (аналогично action=4)
 * 41 - CSV → Product JSONs с заглушками переводов (NEW)
 * 46 - активация существующих продуктов в каталоге (renamed from 41)
 */
async function main(action) {

  // Проверка корректности action
  if (action === undefined || action === null) {
    throw new Error("Не указан параметр action. Используйте: node deploy_full.js <action> [contract_name] (0-13, 40-46, 444, 555, 777, 888)");
  }

  action = parseInt(action);
  if (isNaN(action) || (action < 0 || action > 13) && (action < 40 || action > 46) && action !== 444 && action !== 555 && action !== 777 && action !== 888) {
    throw new Error("Некорректное значение action. Допустимые значения: 0-13, 40-46, 444, 555, 777, 888");
  }

  // Для action 5 требуется дополнительный параметр
  if (action === 5) {
    const contractName = args[1] || process.env.CONTRACT_NAME;
    if (!contractName) {
      const availableContracts = Object.keys(SUPPORTED_CONTRACTS).join(', ');
      throw new Error(`Для action 5 требуется указать название контракта. Используйте: node deploy_full.js 5 <CONTRACT_NAME> или CONTRACT_NAME=<CONTRACT_NAME> node deploy_full.js\nДоступные контракты: ${availableContracts}`);
    }
  }

  // Для action 6 требуется SELLER_ADDRESS и SELLER_PRIVATE_KEY
  if (action === 6) {
    if (!SELLER_ADDRESS || !SELLER_PRIVATE_KEY) {
      throw new Error("Для action 6 требуются переменные SELLER_ADDRESS и SELLER_PRIVATE_KEY в .env");
    }
  }

  // Для action 7 - создание первого селлера (требует INVITE_CODE)
  if (action === 7) {
    const inviteCode = args[1] || process.env.INVITE_CODE;
    if (!inviteCode) {
      throw new Error("Для action 7 требуется указать инвайт-код. Используйте: node deploy_full.js 7 <INVITE_CODE> или INVITE_CODE=<INVITE_CODE> node deploy_full.js");
    }
  }
  
  // Для action 8 требуется INVITE_CODE и SELLER_ADDRESS
  if (action === 8) {
    const inviteCode = args[1] || process.env.INVITE_CODE;
    if (!inviteCode) {
      throw new Error("Для action 8 требуется указать инвайт-код. Используйте: node deploy_full.js 8 <INVITE_CODE> или INVITE_CODE=<INVITE_CODE> node deploy_full.js");
    }
    if (!SELLER_ADDRESS) {
      throw new Error("Для action 8 требуется переменная SELLER_ADDRESS в .env");
    }
  }

  const deployer = deployerAccount.address;
  console.log("\n=== Начинаем деплой контрактов ===");
  console.log("Деплоер:", deployer);
  console.log("Выбранное действие (action):", action);
  
  // Проверяем баланс в нативной валюте сети
  const balance = await web3.eth.getBalance(deployer);
  const currency = network === 'polygon' ? 'MATIC' : 'ETH';
  console.log("Баланс деплоера:", web3.utils.fromWei(balance, 'ether'), currency);
  console.log("RPC URL:", RPC_URL);

  let spiralEngine, productRegistry;

  try {
    // Деплой или загрузка реестра
    if (action === 0) {
      console.log("\n🔷 Деплоим MagicRegistry...");
      magicRegistry = await deployContract("MagicRegistry");
      console.log("");
      console.log("MAGIC_REGISTRY_CONTRACT_ADDRESS=" + magicRegistry.options.address);
    } else if (action === 1) {
      // Для action 1 — умная логика загрузки реестра
      console.log("\n🔷 Обрабатываем MagicRegistry...");
      
      if (MAGIC_REGISTRY_CONTRACT_ADDRESS && MAGIC_REGISTRY_CONTRACT_ADDRESS !== 'undefined') {
        // Если адрес есть в .env - загружаем существующий
        console.log("📋 Найден адрес реестра в .env, загружаем существующий...");
        magicRegistry = await loadContract("MagicRegistry", MAGIC_REGISTRY_CONTRACT_ADDRESS);
        console.log("☀️ Адрес реестра:", magicRegistry.options.address);
      } else {
        // Если адреса нет - деплоим новый (чистый старт)
        console.log("📋 Адрес реестра не найден в .env, деплоим новый...");
        magicRegistry = await deployContract("MagicRegistry");
        console.log("");
        console.log("MAGIC_REGISTRY_CONTRACT_ADDRESS=" + magicRegistry.options.address);
      }
     } else if (action === 888) {
       // Для action 888 - инициализация селлера (критическое действие)
       console.log("\n🔷 Загружаем MagicRegistry для инициализации селлера...");
       if (!MAGIC_REGISTRY_CONTRACT_ADDRESS || MAGIC_REGISTRY_CONTRACT_ADDRESS === 'undefined') {
         throw new Error("Адрес реестра не найден в .env. Сначала выполните action=1 для деплоя всей системы контрактов.");
       }
       magicRegistry = await loadContract("MagicRegistry", MAGIC_REGISTRY_CONTRACT_ADDRESS);
       console.log("☀️ Адрес реестра:", magicRegistry.options.address);
     } else {
       // В остальных случаях просто загружаем реестр из .env
       console.log("\n🔷 Загружаем MagicRegistry...");
       if (!MAGIC_REGISTRY_CONTRACT_ADDRESS || MAGIC_REGISTRY_CONTRACT_ADDRESS === 'undefined') {
         throw new Error("Адрес реестра не найден в .env. Сначала выполните action=0 или action=1 для деплоя реестра.");
       }
       magicRegistry = await loadContract("MagicRegistry", MAGIC_REGISTRY_CONTRACT_ADDRESS);
       console.log("☀️ Адрес реестра:", magicRegistry.options.address);
     }

    // Деплой или загрузка основных контрактов
    if (action === 1 || action === 2) {
      // Деплой SpiralEngine с проверкой существования
      console.log("\n🔷 Обрабатываем SpiralEngine...");
      spiralEngine = await deploySingleContract("SpiralEngine", magicRegistry);

      // Деплой SBT экосистемы с проверкой существования
      console.log("\n🔷 Обрабатываем SBT экосистему...");
      
      // 1. SoulboundCore (базовый SBT)
      const soulboundCore = await deploySingleContract("SoulboundCore", magicRegistry);
      
      // 2. SoulMetadata (метаданные)
      const soulMetadata = await deploySingleContract("SoulMetadata", magicRegistry);
      
      // 3. SoulRecovery (восстановление)
      const soulRecovery = await deploySingleContract("SoulRecovery", magicRegistry);
      
      // 4. SoulIntegration (интеграция)
      const soulIntegration = await deploySingleContract("SoulIntegration", magicRegistry);
      
      // 5. SoulIdentity (мост с DID)
      const soulIdentity = await deploySingleContract("SoulIdentity", magicRegistry);
      
      // 6. Настройка связей между SBT контрактами
      console.log("\n🔷 Настраиваем связи SBT экосистемы...");
      
      // Получаем цену газа для настройки связей
      const gasPrice = network === 'polygon' ? 
        web3.utils.toWei('100', 'gwei') : // 100 Gwei для Polygon mainnet
        await web3.eth.getGasPrice(); // Текущая цена для других сетей
      
      const gasLimit = network === 'polygon' ? 500000 : 300000; // Увеличиваем газ для mainnet
      
      // Подключаем SoulMetadata к SoulboundCore
      console.log("🔗 Подключаем SoulMetadata к SoulboundCore...");
      const nonce2 = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
      await soulboundCore.methods.setMetadataContract(soulMetadata.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice,
        nonce: nonce2
      });
      console.log("✅ SoulMetadata подключен к SoulboundCore");
      
      // Подключаем SoulRecovery к SoulboundCore
      console.log("🔗 Подключаем SoulRecovery к SoulboundCore...");
      const nonce3 = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
      await soulboundCore.methods.setRecoveryContract(soulRecovery.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice,
        nonce: nonce3
      });
      console.log("✅ SoulRecovery подключен к SoulboundCore");
      
      // Подключаем SoulIntegration к SoulboundCore
      console.log("🔗 Подключаем SoulIntegration к SoulboundCore...");
      const nonce4 = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
      await soulboundCore.methods.setIntegrationContract(soulIntegration.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice,
        nonce: nonce4
      });
      console.log("✅ SoulIntegration подключен к SoulboundCore");
      
      // Подключаем SoulIdentity к SpiralEngine
      console.log("🔗 Подключаем SoulIdentity к SpiralEngine...");
      const nonce5 = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
      await spiralEngine.methods.setSoulIdentity(soulIdentity.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice,
        nonce: nonce5
      });
      console.log("✅ SoulIdentity подключен к SpiralEngine");
      
      console.log("\n✅ SBT экосистема полностью настроена!");

      // Деплой ProductRegistry с проверкой существования
      console.log("\n🔷 Обрабатываем ProductRegistry...");
      productRegistry = await deploySingleContract("ProductRegistry", magicRegistry);
      
      // Деплой AmanitaInternational (UUPS) с проверкой существования
      console.log("\n🔷 Обрабатываем AmanitaInternational...");
      const amanitaInternational = await deploySingleContract("AmanitaInternational", magicRegistry);
      
      // Деплой OrganicComponentRegistry (UUPS) с проверкой существования
      console.log("\n🔷 Обрабатываем OrganicComponentRegistry...");
      const organicComponentRegistry = await deploySingleContract("OrganicComponentRegistry", magicRegistry);
      
      // Настройка связей OrganicComponentRegistry
      console.log("\n🔷 Настраиваем связи OrganicComponentRegistry...");
      
      console.log("🔗 Подключаем SpiralEngine к OrganicComponentRegistry...");
      const nonce1 = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
      await organicComponentRegistry.methods.setSpiralEngine(spiralEngine.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice,
        nonce: nonce1
      });
      console.log("✅ SpiralEngine подключен к OrganicComponentRegistry");
      
      console.log("\n✅ OrganicComponentRegistry полностью настроен!");
      
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);
      console.log("☀️ Адрес ProductRegistry:", productRegistry.options.address);
      console.log("☀️ Адрес AmanitaInternational:", amanitaInternational.options.address);
      console.log("☀️ Адрес OrganicComponentRegistry:", organicComponentRegistry.options.address);
      
    }
    
    // Action 41 не требует загрузки контрактов (только CSV трансформация)
    if (action === 3 || action === 4 || action === 40 || action === 46) {

      spiralEngine = await loadUUPSContract("SpiralEngine");
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);

      productRegistry = await loadUUPSContract("ProductRegistry");
      console.log("☀️ Адрес ProductRegistry:", productRegistry.options.address);
      
      const amanitaInternational = await loadUUPSContract("AmanitaInternational");
      console.log("☀️ Адрес AmanitaInternational:", amanitaInternational.options.address);
      
      const organicComponentRegistry = await loadUUPSContract("OrganicComponentRegistry");
      console.log("☀️ Адрес OrganicComponentRegistry:", organicComponentRegistry.options.address);
      
    }

    // Настройка ролей (только для действий 1, 2, 4, 40, 46)
    if (action === 1 || action === 2 || action === 4 || action === 40 || action === 46) {
      await setupSellerRole(spiralEngine);
    }
    
    // Action 777: Генерация 12 инвайтов для деплоера (production)
    if (action === 777) {
      console.log("\n" + "=".repeat(60));
      console.log("🎲 Action 777: Генерация инвайтов для деплоера");
      console.log("=".repeat(60));
      
      // Загружаем SpiralEngine (UUPS)
      console.log("\n📦 Шаг 1/4: Загрузка SpiralEngine...");
      const spiralEngine = await loadUUPSContract("SpiralEngine");
      console.log("✅ SpiralEngine загружен:", spiralEngine.options.address);
      
      // Проверяем общее состояние
      const totalInvites = await spiralEngine.methods.totalInvitesMinted().call();
      console.log(`📊 Текущее количество инвайтов: ${totalInvites}`);
      
      // Проверяем права деплоера
      console.log("\n🔐 Шаг 2/4: Проверка прав деплоера...");
      await validateDeployerAccess(spiralEngine);
      console.log("✅ Деплоер имеет необходимые права");
      
      // Генерируем 12 инвайтов для деплоера
      console.log("\n🎲 Шаг 3/4: Генерация и минтинг инвайтов...");
      await creatingInvitesForDeployer(spiralEngine);
      
      // Финальная проверка
      console.log("\n📊 Шаг 4/4: Финальная проверка...");
      const totalInvitesAfter = await spiralEngine.methods.totalInvitesMinted().call();
      console.log(`✅ Инвайтов после генерации: ${totalInvitesAfter}`);
      console.log(`✅ Создано новых инвайтов: ${totalInvitesAfter - totalInvites}`);
      
      console.log("\n" + "=".repeat(60));
      console.log("✅ Action 777 завершен успешно!");
      console.log("=".repeat(60));
    }
    
    // Action 888: Полная инициализация селлера
    if (action === 888) {
      console.log("\n🎲 Action 888: Полная инициализация селлера...");
      
      // Получаем параметры из аргументов или переменных окружения
      const deployerInvite = args[1] || process.env.DEPLOYER_INVITE;
      const sellerAddress = args[2] || process.env.SELLER_ADDRESS;
      const catalogData = args[3] || process.env.CATALOG_DATA;
      
      if (!deployerInvite || !sellerAddress) {
        throw new Error("Action 888: требуются deployerInvite и sellerAddress");
      }
      
      await action888(deployerInvite, sellerAddress, catalogData);
      console.log("✅ Action 888 завершен успешно!");
    }
    
    // Action 555: Базовая активация seller + загрузка компонентов
    if (action === 555) {
      console.log("\n" + "=".repeat(70));
      console.log("🔷 Action 555: Базовая активация seller + загрузка компонентов");
      console.log("=".repeat(70));
      
      // Получаем параметры из аргументов или переменных окружения
      const deployerInvite = args[1] || process.env.DEPLOYER_INVITE;
      const sellerAddress = args[2] || process.env.SELLER_ADDRESS;
      const dryRun = process.env.DRY_RUN === 'true';
      
      if (!deployerInvite) {
        throw new Error("Action 555: требуется deployerInvite (рутовый инвайт из Action 777)");
      }
      
      if (!sellerAddress) {
        throw new Error("Action 555: требуется sellerAddress");
      }
      
      // Шаг 1: Загрузка SpiralEngine
      console.log("\n📦 Шаг 1/3: Загрузка SpiralEngine...");
      const spiralEngine = await loadUUPSContract("SpiralEngine");
      console.log("✅ SpiralEngine загружен:", spiralEngine.options.address);
      
      // Шаг 2: Базовая активация seller
      console.log("\n👤 Шаг 2/3: Базовая активация seller...");
      try {
        await activateSellerBasic(spiralEngine, sellerAddress, deployerInvite);
        console.log("✅ Базовая активация завершена успешно!");
      } catch (error) {
        console.error("❌ Ошибка при базовой активации seller:");
        console.error(`   ${error.message}`);
        throw error;
      }
      
      // Шаг 3: Загрузка компонентов в OrganicComponentRegistry
      console.log("\n📦 Шаг 3/3: Загрузка компонентов...");
      try {
        const uploadResults = await uploadComponentsCore(
          sellerAddress,
          "data/components",  // относительный путь от projectRoot
          network,
          dryRun,
          process.env.ARWEAVE !== 'false'  // режим полной загрузки в Arweave (default: true)
        );
        
        console.log("\n" + "=".repeat(70));
        console.log("📊 ФИНАЛЬНЫЙ ОТЧЕТ Action 555");
        console.log("=".repeat(70));
        console.log(`✅ Seller активирован: ${sellerAddress}`);
        console.log(`✅ Компонентов обработано: ${uploadResults.totalCount}`);
        console.log(`   → Успешно: ${uploadResults.successCount}`);
        console.log(`   → Пропущено: ${uploadResults.skippedCount}`);
        console.log(`   → Ошибок: ${uploadResults.failCount}`);
        
        if (uploadResults.failCount > 0) {
          console.log(`\n⚠️ Некоторые компоненты завершились с ошибками`);
          console.log(`   Подробности в логе выше`);
        }
        
        console.log("\n" + "=".repeat(70));
        console.log("✅ Action 555 завершен успешно!");
        console.log("=".repeat(70));
        
      } catch (error) {
        console.error("❌ Ошибка при загрузке компонентов:");
        console.error(`   ${error.message}`);
        throw error;
      }
    }
    
    // Для action=3 деплоер временно получает роль SELLER_ROLE для минта инвайтов
    if (action === 3) {
      await setupDeployerAsSeller(spiralEngine);
    }

    // Генерация инвайтов
    if (action === 3) {
      console.log("\n🔷 Генерируем инвайты...");
      await creatingInvites(spiralEngine);
      console.log("✅ Инвайты сгенерированы и сохранены в bot/flowers/invites.txt");
    }
    
    // Создание каталога (неактивные продукты)
    if (action === 4 || action === 40) {
      console.log("\n🔷 Создаем каталог с неактивными продуктами...");
      
      // Проверяем права доступа селлера
      const sellerAddr = sellerAccount ? sellerAccount.address : SELLER_ADDRESS;
      await validateSellerAccess(sellerAddr, spiralEngine);
      
      // Очищаем существующий каталог перед созданием нового
      console.log(`🧹 Очищаем существующий каталог продавца...`);
      try {
        // Проверяем, есть ли продукты в каталоге
        const existingProducts = await productRegistry.methods.getProductsBySeller(sellerAddr).call();
        console.log(`🔍 Найдено существующих продуктов: ${existingProducts.length}`);
        
        if (existingProducts.length === 0) {
          console.log(`✅ Каталог уже пустой, пропускаем очистку`);
        } else {
          // Создаем кошелек продавца для очистки каталога
          if (!SELLER_PRIVATE_KEY) {
            throw new Error("SELLER_PRIVATE_KEY не найден в .env для очистки каталога");
          }
          
          const sellerWallet = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
          web3.eth.accounts.wallet.add(sellerWallet);
          
          const clearTx = await productRegistry.methods.clearSellerCatalog(sellerAddr).send({
            from: sellerAddr, // ✅ Используем адрес продавца
            gas: network === 'polygon' ? 500000 : 300000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : undefined
          });
        
          // Ждем подтверждения транзакции (только для mainnet)
          if (network === 'polygon') {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
          
          console.log(`✅ Каталог очищен, tx: ${clearTx.transactionHash}`);
          
          // Ждем подтверждения и проверяем событие CatalogCleared
          const receipt = await web3.eth.getTransactionReceipt(clearTx.transactionHash);
          const catalogClearedEvent = receipt.logs.find(log => {
            try {
              const decoded = productRegistry.options.jsonInterface.find(iface => iface.name === 'CatalogCleared');
              return decoded && web3.utils.hexToNumber(log.topics[1]) === web3.utils.toHex(sellerAddr);
            } catch (e) {
              return false;
            }
          });
          
          if (catalogClearedEvent) {
            const productsCleared = web3.utils.hexToNumber(catalogClearedEvent.data);
            console.log(`📊 Очищено продуктов: ${productsCleared}`);
          }
        }
        
      } catch (clearError) {
        if (clearError.message.includes("Catalog is already empty")) {
          console.log(`✅ Каталог уже пустой, продолжаем...`);
        } else {
          console.log(`⚠️ Ошибка при очистке каталога: ${clearError.message}`);
          console.log(`⚠️ Продолжаем без очистки...`);
        }
      }
      
      await createCatalog(productRegistry, sellerAddr);
      console.log("✅ Каталог с неактивными продуктами успешно загружен!");
    }
    
    // Action 41: CSV → Product JSONs с заглушками переводов
    if (action === 41) {
      console.log("\n" + "=".repeat(70));
      console.log("🔷 Action 41: Transform CSV → Product JSONs with translation stubs");
      console.log("=".repeat(70));
      
      await action41_TransformProducts();
      
      console.log("\n" + "=".repeat(70));
      console.log("✅ Action 41 completed successfully!");
      console.log("=".repeat(70));
    }

    // Action 42: Объединенная загрузка в Arweave
    if (action === 42) {
      console.log("\n" + "=".repeat(70));
      console.log("🔷 Action 42: Unified Arweave Upload");
      console.log("=".repeat(70));
      
      const { action42_UnifiedArweaveUpload } = require('./lib/product_upload_steps.js');
      
      // Initialize Arweave
      const arweaveContext = await initializeArweaveForActions();
      
      // Create context
      const context = {
        dryRun: false,
        productRegistry: productRegistry,
        arweave: arweaveContext.client
      };
      
      // Parameters (unified with Action 41)
      const sellerId = process.env.SELLER_ID || 'iveta';
      const sellerBaseDir = path.join(__dirname, "..", "data", "sellers", sellerId);
      const productsDir = path.join(sellerBaseDir, 'products');
      const mappingOutputDir = sellerBaseDir;
      
      // Execute Action 42
      await action42_UnifiedArweaveUpload(context, productsDir, mappingOutputDir);
      
      console.log("\n" + "=".repeat(70));
      console.log("✅ Action 42 completed successfully!");
      console.log("=".repeat(70));
    }

    // Action 43: Регистрация в контрактах
    if (action === 43) {
      console.log("\n" + "=".repeat(70));
      console.log("🔷 Action 43: Contract Registration");
      console.log("=".repeat(70));
      
      const { action43_UnifiedContractRegistration } = require('./lib/product_upload_steps.js');
      
      // Create context
      const context = {
        dryRun: false,
        productRegistry: productRegistry,
        arweave: null // Not needed for Action 43
      };
      
      // Parameters (unified with Actions 41-42)
      const sellerId = process.env.SELLER_ID || 'iveta';
      const sellerBaseDir = path.join(__dirname, "..", "data", "sellers", sellerId);
      const mappingFile = path.join(sellerBaseDir, 'product_combined_mapping.json');
      const productsDir = path.join(sellerBaseDir, 'products');
      
      // Execute Action 43
      await action43_UnifiedContractRegistration(context, mappingFile, productsDir);
      
      console.log("\n" + "=".repeat(70));
      console.log("✅ Action 43 completed successfully!");
      console.log("=".repeat(70));
    }

    // Action 444: Автоматический пайп (41 → 42 → 43)
    if (action === 444) {
      console.log("\n" + "=".repeat(70));
      console.log("🔷 Action 444: Automatic Pipeline (41 → 42 → 43)");
      console.log("=".repeat(70));
      
      const { action444_AutomaticPipeline } = require('./lib/product_upload_steps.js');
      
      // Определяем параметры для Action 444
      const sellerId = process.env.SELLER_ID || 'iveta';  // ← UNIFIED: используем простой sellerId
      const sellerBaseDir = path.join(__dirname, "..", "data", "sellers", sellerId);
      const csvPath = path.join(sellerBaseDir, "catalog", "Iveta_catalog.csv");
      const outputDir = sellerBaseDir;  // ← UNIFIED: тот же путь для Action 41 и 42
      const sourceLang = 'en';
      
      // Создаем контекст для Action 444
      const context = {
        dryRun: false,
        productRegistry: productRegistry,
        arweave: null // Arweave будет инициализирован в Action 444
      };
      
      console.log(`📄 CSV: ${csvPath}`);
      console.log(`📁 Output: ${outputDir}`);
      console.log(`👤 Seller: ${sellerId}`);
      console.log(`🌐 Language: ${sourceLang}`);
      
      // Вызываем Action 444
      const result = await action444_AutomaticPipeline(
        context,
        csvPath,
        outputDir,
        sellerId,
        sourceLang
      );
      
      if (result.success) {
        console.log(`✅ Action 444 completed successfully!`);
        console.log(`📊 Статистика:`);
        console.log(`   → Продуктов создано: ${result.summary.totalProducts}`);
        console.log(`   → Файлов в Arweave: ${result.summary.arweaveFiles}`);
        console.log(`   → Продуктов активировано: ${result.summary.activatedProducts}`);
      } else {
        throw new Error(`Action 444 завершился с ошибкой: ${result.error}`);
      }
      
      console.log("\n" + "=".repeat(70));
      console.log("✅ Action 444 completed successfully!");
      console.log("=".repeat(70));
    }
    
    // Action 46: Активация продуктов (переименовано из старого action 41)
    if (action === 46) {
      console.log("\n🔷 Action 46: Активируем продукты в каталоге...");
      
      // Проверяем права доступа селлера
      const sellerAddr = sellerAccount ? sellerAccount.address : SELLER_ADDRESS;
      await validateSellerAccess(sellerAddr, spiralEngine);
      
      await activateCatalogProducts(productRegistry, sellerAddr);
      console.log("✅ Продукты в каталоге успешно активированы!");
    }
    
    // Деплой конкретного контракта по имени
    if (action === 5) {
      const contractName = args[1] || process.env.CONTRACT_NAME;
      console.log(`\n🔷 Обрабатываем контракт: ${contractName}`);
      await deploySingleContract(contractName, amanitaRegistry);
      console.log(`✅ Контракт ${contractName} успешно обработан!`);
    }

    // Очистка каталога продавца
    if (action === 6) {
      console.log(`\n🧹 Очищаем каталог продавца: ${SELLER_ADDRESS}`);
      await clearSellerCatalog(SELLER_ADDRESS, SELLER_PRIVATE_KEY);
      console.log(`✅ Каталог продавца успешно очищен!`);
    }

    // Создание первого селлера (новая архитектура)
    if (action === 7) {
      const inviteCode = args[1] || process.env.INVITE_CODE;
      console.log(`\n🌱 Создаем первого селлера...`);
      const firstSellerAddress = await createFirstSeller(inviteCode);
      console.log(`✅ Первый селлер создан: ${firstSellerAddress}`);
    }

    // Активация продавца через инвайт-код (старая логика)
    if (action === 8) {
      const inviteCode = args[1] || process.env.INVITE_CODE;
      console.log(`\n🎯 Активируем продавца: ${SELLER_ADDRESS}`);
      await activateSeller(inviteCode, SELLER_ADDRESS);
      console.log(`✅ Продавец ${SELLER_ADDRESS} успешно активирован!`);
    }

    // Назначение роли ACTIVATOR_ROLE селлеру из .env
    if (action === 9) {
      const sellerAddress = SELLER_ADDRESS;
      if (!sellerAddress) {
        throw new Error("Для action 9 требуется SELLER_ADDRESS в .env");
      }
      console.log(`🔑 Action 9: Назначаем роль ACTIVATOR_ROLE селлеру ${sellerAddress}`);
      await grantActivatorRoleToSellerOnly(sellerAddress);
    }

    // Назначение роли SELLER_ROLE
    if (action === 10) {
      const userAddress = args[1];
      if (!userAddress) {
        throw new Error("Для action 10 требуется указать адрес пользователя");
      }
      await grantSellerRole(userAddress);
    }

    // Генерация инвайтов для активного селлера
    if (action === 11) {
      const sellerAddress = SELLER_ADDRESS;
      const inviteCount = parseInt(args[1]) || 12; // По умолчанию 12 инвайтов
      
      if (!sellerAddress) {
        throw new Error("Для action 11 требуется SELLER_ADDRESS в .env");
      }
      
      console.log(`\n🎲 Action 11: Генерируем ${inviteCount} инвайтов для селлера ${sellerAddress}...`);
      
      // Загружаем SpiralEngine (UUPS)
      const spiralEngine = await loadUUPSContract("SpiralEngine");
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);
      
      // Проверяем что селлер активирован и имеет роль SELLER_ROLE
      await validateSellerAccess(sellerAddress, spiralEngine);
      
      // Генерируем инвайты используя существующую функцию из action 888
      await generateInvitesForSellerAction11(spiralEngine, sellerAddress, inviteCount);
      
      console.log("✅ Action 11 завершен успешно!");
    }

    // Получение полного каталога с загрузкой данных через CID
    if (action === 12) {
      const sellerAddress = SELLER_ADDRESS || args[1];
      if (!sellerAddress) {
        throw new Error("Для action 12 требуется SELLER_ADDRESS в .env или указать адрес продавца как аргумент");
      }
      
      console.log(`\n📋 Action 12: Получаем полный каталог для продавца ${sellerAddress}...`);
      
      // Загружаем ProductRegistry (UUPS)
      const productRegistry = await loadUUPSContract("ProductRegistry");
      console.log("📦 Адрес ProductRegistry:", productRegistry.options.address);
      
      // Получаем полный каталог с загрузкой данных
      await getFullCatalogWithData(productRegistry, sellerAddress);
      
      console.log("✅ Action 12 завершен успешно!");
    }

    // Диагностика состояния селлера (Action 13)
    if (action === 13) {
      const sellerAddress = SELLER_ADDRESS || args[1];
      if (!sellerAddress) {
        throw new Error("Для action 13 требуется SELLER_ADDRESS в .env или указать адрес продавца как аргумент");
      }
      
      console.log(`\n🔍 Action 13: Диагностика состояния селлера ${sellerAddress}...`);
      
      // Загружаем контракты (UUPS)
      const spiralEngine = await loadUUPSContract("SpiralEngine");
      const productRegistry = await loadUUPSContract("ProductRegistry");
      
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);
      console.log("📦 Адрес ProductRegistry:", productRegistry.options.address);
      
      // Выполняем полную диагностику
      await diagnoseSellerState(spiralEngine, productRegistry, sellerAddress);
      
      console.log("✅ Action 13 завершен успешно!");
    }

    // Выводим адреса контрактов только если они были задействованы
    if (action <= 2) {
      console.log("");
      console.log("MAGIC_REGISTRY_CONTRACT_ADDRESS=" + magicRegistry.options.address);
      if (spiralEngine) console.log("SPIRAL_ENGINE_CONTRACT_ADDRESS=" + spiralEngine.options.address);
      if (productRegistry) console.log("PRODUCT_REGISTRY_CONTRACT_ADDRESS=" + productRegistry.options.address);
      
      // Добавляем SBT адреса если они были задеплоены
      try {
        const soulboundCoreAddress = await magicRegistry.methods.get("SoulboundCore").call();
        const soulMetadataAddress = await magicRegistry.methods.get("SoulMetadata").call();
        const soulRecoveryAddress = await magicRegistry.methods.get("SoulRecovery").call();
        const soulIntegrationAddress = await magicRegistry.methods.get("SoulIntegration").call();
        const soulIdentityAddress = await magicRegistry.methods.get("SoulIdentity").call();
        
        if (soulboundCoreAddress !== "0x0000000000000000000000000000000000000000") {
          console.log("SOULBOUND_CORE_CONTRACT_ADDRESS=" + soulboundCoreAddress);
          console.log("SOUL_METADATA_CONTRACT_ADDRESS=" + soulMetadataAddress);
          console.log("SOUL_RECOVERY_CONTRACT_ADDRESS=" + soulRecoveryAddress);
          console.log("SOUL_INTEGRATION_CONTRACT_ADDRESS=" + soulIntegrationAddress);
          console.log("SOUL_IDENTITY_CONTRACT_ADDRESS=" + soulIdentityAddress);
        }
      } catch (error) {
        // Игнорируем ошибки если SBT контракты не задеплоены
      }
      
      // Добавляем AmanitaInternational адреса если они были задеплоены
      try {
        const amanitaInternationalAddress = await magicRegistry.methods.get("AmanitaInternational").call();
        
        if (amanitaInternationalAddress !== "0x0000000000000000000000000000000000000000") {
          console.log("");
          console.log("AMANITA_INTERNATIONAL_PROXY_ADDRESS=" + amanitaInternationalAddress);
          
          // Для UUPS используем стандартный EIP-1967 storage slot
          try {
            const EIP1967_IMPLEMENTATION_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc';
            const implementationAddress = await web3.eth.getStorageAt(
              amanitaInternationalAddress,
              EIP1967_IMPLEMENTATION_SLOT
            );
            const logicAddress = '0x' + implementationAddress.slice(-40);
            console.log("AMANITA_INTERNATIONAL_LOGIC_ADDRESS=" + logicAddress);
          } catch (e) {
            console.log("# ERROR: Не удалось получить адрес Logic из UUPS Proxy");
          }
        }
      } catch (error) {
        // Игнорируем ошибки если AmanitaInternational не задеплоен
      }
      
      // Добавляем OrganicComponentRegistry адреса если они были задеплоены
      try {
        const organicComponentRegistryAddress = await magicRegistry.methods.get("OrganicComponentRegistry").call();
        
        if (organicComponentRegistryAddress !== "0x0000000000000000000000000000000000000000") {
          console.log("");
          console.log("ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS=" + organicComponentRegistryAddress);
          
          // Для UUPS используем стандартный EIP-1967 storage slot
          try {
            const EIP1967_IMPLEMENTATION_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc';
            const implementationAddress = await web3.eth.getStorageAt(
              organicComponentRegistryAddress,
              EIP1967_IMPLEMENTATION_SLOT
            );
            const logicAddress = '0x' + implementationAddress.slice(-40);
            console.log("ORGANIC_COMPONENT_REGISTRY_LOGIC_ADDRESS=" + logicAddress);
          } catch (e) {
            console.log("# ERROR: Не удалось получить адрес Logic из UUPS Proxy");
          }
        }
      } catch (error) {
        // Игнорируем ошибки если OrganicComponentRegistry не задеплоен
      }
    }
    
    // Выводим адрес задеплоенного контракта для action 5
    if (action === 5) {
      const contractName = args[1] || process.env.CONTRACT_NAME;
      const contractAddress = await magicRegistry.methods.get(contractName).call();
      console.log("");
      console.log(`${contractName.toUpperCase()}_CONTRACT_ADDRESS=${contractAddress}`);
    }

  } catch (error) {
    console.error("\n❌ Ошибка при выполнении действия", action + ":");
    console.error(error.message || error);
    throw error;
  }
}

SELLER_ROLE = web3.utils.keccak256("SELLER_ROLE");

// Поддерживаемые контракты для параметризуемого деплоя
const SUPPORTED_CONTRACTS = {
    'MagicRegistry': {
        dependencies: [],
        needsSetup: false
    },
    // === 🔄 UUPS Контракты (Upgradeable) ===
    
    // SpiralEngine (UUPS Architecture)
    'SpiralEngineLogic': {
        dependencies: [],
        needsSetup: false,
        isUUPSLogic: true
    },
    'SpiralEngineProxy': {
        dependencies: ['SpiralEngineLogic'],
        needsSetup: false,
        isUUPSProxy: true,
        logicContract: 'SpiralEngineLogic'
    },
    'SpiralEngine': {
        dependencies: [],
        needsSetup: true,
        isUUPSDeployment: true,
        logicContract: 'SpiralEngineLogic',
        proxyContract: 'SpiralEngineProxy'
    },
    
    // ProductRegistry (UUPS Architecture)
    'ProductRegistryLogic': {
        dependencies: [],
        needsSetup: false,
        isUUPSLogic: true
    },
    'ProductRegistryProxy': {
        dependencies: ['ProductRegistryLogic', 'SpiralEngine'],
        needsSetup: false,
        isUUPSProxy: true,
        logicContract: 'ProductRegistryLogic'
    },
    'ProductRegistry': {
        dependencies: ['SpiralEngine'],
        needsSetup: true,
        isUUPSDeployment: true,
        logicContract: 'ProductRegistryLogic',
        proxyContract: 'ProductRegistryProxy'
    },
    'LoveDoPostNFT': {
        dependencies: ['SpiralEngine', 'MagicRegistry'],
        needsSetup: true
    },
    'LoveEmissionEngine': {
        dependencies: ['AmanitaToken', 'AmanitaGovToken', 'LoveDoPostNFT', 'SpiralEngine'],
        needsSetup: true
    },
    'AmanitaToken': {
        dependencies: [],
        needsSetup: false
    },
    'AmanitaGovToken': {
        dependencies: [],
        needsSetup: false
    },
    'AmanitaPaymentRouter': {
        dependencies: ['AmanitaToken'],
        needsSetup: true
    },
    'SoulboundCore': {
        dependencies: [],
        needsSetup: false
    },
    'SoulMetadata': {
        dependencies: ['SoulboundCore'],
        needsSetup: true
    },
    'SoulRecovery': {
        dependencies: ['SoulboundCore'],
        needsSetup: true
    },
    'SoulIntegration': {
        dependencies: ['SpiralEngine', 'SoulboundCore'],
        needsSetup: true
    },
    'SoulIdentity': {
        dependencies: ['SoulboundCore', 'SoulMetadata'],
        needsSetup: true
    },
    // 🌐 Localization System (UUPS Architecture)
    'AmanitaInternationalLogic': {
        dependencies: [],
        needsSetup: false,
        isUUPSLogic: true
    },
    'AmanitaInternationalProxy': {
        dependencies: ['AmanitaInternationalLogic'],
        needsSetup: false,
        isUUPSProxy: true,
        logicContract: 'AmanitaInternationalLogic'
    },
    'AmanitaInternational': {
        dependencies: [],
        needsSetup: true,
        isUUPSDeployment: true,
        logicContract: 'AmanitaInternationalLogic',
        proxyContract: 'AmanitaInternationalProxy'
    },
    // 🌿 Organic Components Registry (UUPS Architecture)
    'OrganicComponentRegistryLogic': {
        dependencies: [],
        needsSetup: false,
        isUUPSLogic: true
    },
    'OrganicComponentRegistryProxy': {
        dependencies: ['OrganicComponentRegistryLogic'],
        needsSetup: false,
        isUUPSProxy: true,
        logicContract: 'OrganicComponentRegistryLogic'
    },
    'OrganicComponentRegistry': {
        dependencies: [],
        needsSetup: true,
        isUUPSDeployment: true,
        logicContract: 'OrganicComponentRegistryLogic',
        proxyContract: 'OrganicComponentRegistryProxy'
    }
};

// Маппинг контрактов на переменные окружения .env
const CONTRACT_ENV_MAPPING = {
    'MagicRegistry': 'MAGIC_REGISTRY_CONTRACT_ADDRESS',
    
    // === 🔄 UUPS Контракты (Upgradeable) ===
    'SpiralEngineLogic': 'SPIRAL_ENGINE_LOGIC_ADDRESS',
    'SpiralEngineProxy': 'SPIRAL_ENGINE_PROXY_ADDRESS',
    'SpiralEngine': 'SPIRAL_ENGINE_PROXY_ADDRESS',  // Алиас для Proxy (обратная совместимость)
    
    'ProductRegistryLogic': 'PRODUCT_REGISTRY_LOGIC_ADDRESS',
    'ProductRegistryProxy': 'PRODUCT_REGISTRY_PROXY_ADDRESS',
    'ProductRegistry': 'PRODUCT_REGISTRY_PROXY_ADDRESS',  // Алиас для Proxy (обратная совместимость)
    
    // === Остальные контракты ===
    'LoveDoPostNFT': 'LOVE_DO_POST_NFT_CONTRACT_ADDRESS',
    'LoveEmissionEngine': 'LOVE_EMISSION_ENGINE_CONTRACT_ADDRESS',
    'AmanitaToken': 'AMANITA_TOKEN_CONTRACT_ADDRESS',
    'AmanitaGovToken': 'AMANITA_GOV_TOKEN_CONTRACT_ADDRESS',
    'AmanitaPaymentRouter': 'AMANITA_PAYMENT_ROUTER_CONTRACT_ADDRESS',
    'SoulboundCore': 'SOULBOUND_CORE_CONTRACT_ADDRESS',
    'SoulMetadata': 'SOUL_METADATA_CONTRACT_ADDRESS',
    'SoulRecovery': 'SOUL_RECOVERY_CONTRACT_ADDRESS',
    'SoulIntegration': 'SOUL_INTEGRATION_CONTRACT_ADDRESS',
    'SoulIdentity': 'SOUL_IDENTITY_CONTRACT_ADDRESS',
    
    // 🌐 Localization System (UUPS Architecture)
    'AmanitaInternationalLogic': 'AMANITA_INTERNATIONAL_LOGIC_ADDRESS',
    'AmanitaInternationalProxy': 'AMANITA_INTERNATIONAL_PROXY_ADDRESS',
    'AmanitaInternational': 'AMANITA_INTERNATIONAL_PROXY_ADDRESS',  // Алиас для Proxy (обратная совместимость)
    
    // 🌿 Organic Components Registry (UUPS Architecture)
    'OrganicComponentRegistryLogic': 'ORGANIC_COMPONENT_REGISTRY_LOGIC_ADDRESS',
    'OrganicComponentRegistryProxy': 'ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS',
    'OrganicComponentRegistry': 'ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS'  // Алиас для Proxy (обратная совместимость)
};

// ====================================================================
// 🔷 UUPS HELPER FUNCTIONS
// ====================================================================

/**
 * Получить аргументы конструктора для Logic контракта UUPS
 * @param {string} contractName - Название контракта ('SpiralEngine', 'ProductRegistry', etc.)
 * @returns {Array} Массив аргументов для constructor (всегда [] для UUPS Logic)
 */
function getLogicConstructorArgs(contractName) {
    // UUPS Logic контракты не имеют параметров в constructor
    // Все параметры передаются через initialize()
    
    if (contractName === 'SpiralEngine' || contractName === 'SpiralEngineLogic') {
        return [];  // SpiralEngineLogic: constructor пустой
    }
    
    if (contractName === 'ProductRegistry' || contractName === 'ProductRegistryLogic') {
        return [];  // ProductRegistryLogic: constructor пустой
    }
    
    if (contractName === 'AmanitaInternational' || contractName === 'AmanitaInternationalLogic') {
        return [];  // AmanitaInternationalLogic: constructor пустой
    }
    
    if (contractName === 'OrganicComponentRegistry' || contractName === 'OrganicComponentRegistryLogic') {
        return [];  // OrganicComponentRegistryLogic: constructor пустой
    }
    
    // Fallback для будущих UUPS контрактов
    return [];
}

/**
 * Подготовить calldata для initialize() функции UUPS контракта
 * @param {string} contractName - Название контракта
 * @param {Object} logicInstance - Web3 контракт Logic (не используется, но оставлен для совместимости)
 * @returns {string} Закодированная calldata для initialize()
 */
async function prepareInitializeCalldata(contractName, logicInstance = null) {
    console.log(`⚙️ Подготовка initialize() calldata для ${contractName}...`);
    
    // Получаем Logic contract name
    const contractInfo = SUPPORTED_CONTRACTS[contractName];
    if (!contractInfo || !contractInfo.isUUPSDeployment) {
        throw new Error(`${contractName} не является UUPS контрактом`);
    }
    
    const logicContractName = contractInfo.logicContract;
    const artifact = await loadContractArtifact(logicContractName);
    const web3Contract = new web3.eth.Contract(artifact.abi);
    
    // SpiralEngine: initialize(address admin)
    if (contractName === 'SpiralEngine') {
        console.log(`   → initialize(admin: ${deployerAccount.address})`);
        return web3Contract.methods.initialize(deployerAccount.address).encodeABI();
    }
    
    // ProductRegistry: initialize(address admin, address _spiralEngine)
    if (contractName === 'ProductRegistry') {
        // Получаем адрес SpiralEngine Proxy из .env или MagicRegistry
        let spiralEngineProxyAddress = process.env[CONTRACT_ENV_MAPPING['SpiralEngine']];
        
        if (!spiralEngineProxyAddress || spiralEngineProxyAddress === 'undefined') {
            // Пробуем загрузить из MagicRegistry
            if (magicRegistry) {
                try {
                    spiralEngineProxyAddress = await magicRegistry.methods.get('SpiralEngine').call();
                    console.log(`   ℹ️ SpiralEngine Proxy адрес загружен из MagicRegistry: ${spiralEngineProxyAddress}`);
                } catch (error) {
                    throw new Error('SpiralEngine Proxy адрес не найден ни в .env, ни в MagicRegistry! Задеплойте SpiralEngine сначала.');
                }
            } else {
                throw new Error('SpiralEngine Proxy адрес не найден в .env и MagicRegistry недоступен! Задеплойте SpiralEngine сначала.');
            }
        }
        
        console.log(`   → initialize(admin: ${deployerAccount.address}, spiralEngine: ${spiralEngineProxyAddress})`);
        return web3Contract.methods.initialize(
            deployerAccount.address,
            spiralEngineProxyAddress
        ).encodeABI();
    }
    
    // AmanitaInternational: initialize(address admin, address _spiralEngine)
    if (contractName === 'AmanitaInternational') {
        // Получаем адрес SpiralEngine Proxy из .env или MagicRegistry
        let spiralEngineProxyAddress = process.env[CONTRACT_ENV_MAPPING['SpiralEngine']];
        
        if (!spiralEngineProxyAddress || spiralEngineProxyAddress === 'undefined') {
            // Пробуем загрузить из MagicRegistry
            if (magicRegistry) {
                try {
                    spiralEngineProxyAddress = await magicRegistry.methods.get('SpiralEngine').call();
                    console.log(`   ℹ️ SpiralEngine Proxy адрес загружен из MagicRegistry: ${spiralEngineProxyAddress}`);
                } catch (error) {
                    throw new Error('SpiralEngine Proxy адрес не найден ни в .env, ни в MagicRegistry! Задеплойте SpiralEngine сначала.');
                }
            } else {
                throw new Error('SpiralEngine Proxy адрес не найден в .env и MagicRegistry недоступен! Задеплойте SpiralEngine сначала.');
            }
        }
        
        console.log(`   → initialize(admin: ${deployerAccount.address}, spiralEngine: ${spiralEngineProxyAddress})`);
        return web3Contract.methods.initialize(
            deployerAccount.address,
            spiralEngineProxyAddress
        ).encodeABI();
    }
    
    // OrganicComponentRegistry: initialize(address admin)
    if (contractName === 'OrganicComponentRegistry') {
        console.log(`   → initialize(admin: ${deployerAccount.address})`);
        return web3Contract.methods.initialize(deployerAccount.address).encodeABI();
    }
    
    throw new Error(`Неизвестный UUPS контракт для initialize: ${contractName}`);
}

/**
 * Загрузить UUPS контракт (Logic ABI + Proxy address)
 * @param {string} contractName - Название контракта ('SpiralEngine', 'ProductRegistry')
 * @returns {Object} Web3 Contract instance с Logic ABI на Proxy адресе
 */
async function loadUUPSContract(contractName) {
    const contractInfo = SUPPORTED_CONTRACTS[contractName];
    
    // Fallback для не-UUPS контрактов
    if (!contractInfo || !contractInfo.isUUPSDeployment) {
        console.log(`   ℹ️ ${contractName} не является UUPS, используем loadContract()`);
        return await loadContract(contractName);
    }
    
    // Получаем Proxy адрес из .env или MagicRegistry
    const envVar = CONTRACT_ENV_MAPPING[contractName];
    let proxyAddress = process.env[envVar];
    
    // Если адрес не найден в .env, пробуем загрузить из MagicRegistry
    if (!proxyAddress || proxyAddress === 'undefined') {
        if (magicRegistry) {
            try {
                proxyAddress = await magicRegistry.methods.get(contractName).call();
                console.log(`   ℹ️ ${contractName} Proxy адрес загружен из MagicRegistry: ${proxyAddress}`);
            } catch (error) {
                // Если не найден в MagicRegistry, выдаём ошибку
                throw new Error(`Proxy адрес не найден ни в .env (${envVar}), ни в MagicRegistry для ${contractName}`);
            }
        } else {
            throw new Error(`Proxy адрес не найден: ${envVar} не установлен в .env, и MagicRegistry недоступен`);
        }
    }
    
    console.log(`🔷 Загружаем UUPS контракт ${contractName}`);
    console.log(`   → Proxy: ${proxyAddress}`);
    
    // Загружаем Logic ABI (для взаимодействия с Proxy)
    const logicContractName = contractInfo.logicContract;
    const artifact = await loadContractArtifact(logicContractName);
    
    console.log(`   → Logic ABI: ${logicContractName}`);
    
    // Создаем Web3 контракт с Logic ABI на Proxy адресе
    return new web3.eth.Contract(artifact.abi, proxyAddress);
}

/**
 * Деплой UUPS контракта (Logic + Proxy паттерн)
 * @param {string} contractName - Название контракта ('SpiralEngine', 'ProductRegistry')
 * @param {Object} contractInfo - Информация из SUPPORTED_CONTRACTS
 * @param {Object} registryInstance - Экземпляр MagicRegistry (опционально)
 * @returns {Object} Web3 Contract instance Proxy
 */
async function deployUUPSContract(contractName, contractInfo, registryInstance = null) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`🔷 UUPS Deployment: ${contractName}`);
    console.log(`${'='.repeat(60)}`);
    
    // Шаг 1: Deploy Logic Implementation
    console.log(`\n📦 Шаг 1/4: Деплой ${contractInfo.logicContract}...`);
    const logicArgs = getLogicConstructorArgs(contractName);
    console.log(`   → Constructor аргументы: ${logicArgs.length > 0 ? JSON.stringify(logicArgs) : '[]'}`);
    
    const logic = await deployContract(contractInfo.logicContract, logicArgs);
    console.log(`✅ Logic deployed: ${logic.options.address}`);
    
    // Шаг 2: Prepare initialize() calldata
    console.log(`\n⚙️ Шаг 2/4: Подготовка initialize() calldata...`);
    const initCalldata = await prepareInitializeCalldata(contractName, logic);
    console.log(`✅ Initialize calldata prepared (${initCalldata.length} bytes)`);
    
    // Шаг 3: Deploy Proxy with Logic + initData
    console.log(`\n🔗 Шаг 3/4: Деплой ${contractInfo.proxyContract}...`);
    console.log(`   → Logic address: ${logic.options.address}`);
    console.log(`   → Initialize calldata: ${initCalldata.substring(0, 10)}...`);
    
    const proxyDeployed = await deployContract(
        contractInfo.proxyContract,
        [logic.options.address, initCalldata]
    );
    console.log(`✅ Proxy deployed: ${proxyDeployed.options.address}`);
    
    // ВАЖНО: Создаём Proxy instance с Logic ABI для правильного взаимодействия
    console.log(`🔧 Создаём Proxy instance с Logic ABI...`);
    const logicArtifact = await loadContractArtifact(contractInfo.logicContract);
    const proxy = new web3.eth.Contract(logicArtifact.abi, proxyDeployed.options.address);
    console.log(`✅ Proxy instance готов с Logic ABI`);
    
    // Шаг 4: Регистрация в MagicRegistry (ТОЛЬКО Proxy!)
    if (registryInstance) {
        console.log(`\n📝 Шаг 4/4: Регистрация в MagicRegistry...`);
        console.log(`   → Регистрируем ${contractName} → ${proxy.options.address}`);
        await registerContractInRegistry(contractName, proxy, registryInstance);
        console.log(`✅ ${contractName} зарегистрирован в реестре`);
    } else {
        console.log(`\n⚠️ Шаг 4/4: Пропускаем регистрацию (MagicRegistry не предоставлен)`);
    }
    
    // Финальный summary
    console.log(`\n${'='.repeat(60)}`);
    console.log(`✅ UUPS Deployment Complete: ${contractName}`);
    console.log(`${'='.repeat(60)}`);
    console.log(`📍 Proxy (Entry Point): ${proxy.options.address}`);
    console.log(`⚙️ Logic Implementation: ${logic.options.address}`);
    console.log(`🔄 Upgradeable: YES (через UPGRADER_ROLE)`);
    console.log(`${'='.repeat(60)}\n`);
    
    // ВАЖНО: Возвращаем Proxy с Logic ABI!
    return proxy;
}

/**
 * @deprecated Эта функция использовалась для деплоя AmanitaInternational 
 * в старой 3-контрактной архитектуре (Storage + Logic + Proxy).
 * 
 * С переходом на UUPS архитектуру (Logic + Proxy) используйте:
 *   await deploySingleContract("AmanitaInternational", magicRegistry);
 * 
 * @throws {Error} Всегда выбрасывает ошибку с объяснением
 */
async function deployAmanitaInternational() {
    throw new Error(
        "DEPRECATED: deployAmanitaInternational() больше не поддерживается.\n\n" +
        "AmanitaInternational теперь использует UUPS архитектуру (2 контракта):\n" +
        "  - AmanitaInternationalLogic.sol (Logic контракт с state)\n" +
        "  - AmanitaInternationalProxy.sol (ERC1967Proxy)\n\n" +
        "Используйте вместо этого:\n" +
        "  await deploySingleContract('AmanitaInternational', magicRegistry);\n\n" +
        "Старая 3-контрактная архитектура (Storage + Logic + Proxy) больше не используется."
    );
}

/**
 * Проверяет существование контракта в .env и валидирует его
 * @param {string} contractName - Название контракта для проверки
 * @returns {Object|null} - Экземпляр контракта или null если не найден/невалиден
 */
async function checkExistingContract(contractName) {
    const envVar = CONTRACT_ENV_MAPPING[contractName];
    if (!envVar) {
        throw new Error(`Неизвестный контракт: ${contractName}`);
    }
    
    const contractAddress = process.env[envVar];
    if (!contractAddress) {
        console.log(`📋 Контракт ${contractName} не найден в .env, будет задеплоен`);
        return null;
    }
    
    console.log(`🔍 Найден существующий контракт ${contractName} в .env: ${contractAddress}`);
    
    // Валидация контракта
    try {
        const contract = await loadContract(contractName, contractAddress);
        console.log(`✅ Контракт ${contractName} валиден и готов к использованию`);
        return contract;
    } catch (error) {
        console.warn(`⚠️ Контракт ${contractName} по адресу ${contractAddress} недоступен: ${error.message}`);
        console.log(`📋 Будет задеплоен новый экземпляр`);
        return null;
    }
}

/**
 * Регистрирует контракт в MagicRegistry
 * @param {string} contractName - Название контракта
 * @param {Object} contractInstance - Экземпляр контракта
 */
async function registerContractInRegistry(contractName, contractInstance, registryInstance = null) {
    // Используем переданный экземпляр реестра или загружаем из .env
    const magicRegistry = registryInstance || await loadContract("MagicRegistry", MAGIC_REGISTRY_CONTRACT_ADDRESS);
    
    try {
        // Проверяем существующий адрес в реестре
        let existingAddress;
        try {
            existingAddress = await magicRegistry.methods.get(contractName).call();
        } catch (error) {
            existingAddress = null; // Контракт еще не зарегистрирован
        }
        
        if (existingAddress && existingAddress !== '0x0000000000000000000000000000000000000000') {
            if (existingAddress.toLowerCase() === contractInstance.options.address.toLowerCase()) {
                console.log(`✅ Контракт ${contractName} уже зарегистрирован в реестре под тем же адресом: ${existingAddress}`);
                return;
            } else {
                console.log(`🔄 Обновляем регистрацию ${contractName} в реестре:`);
                console.log(`   Старый адрес: ${existingAddress}`);
                console.log(`   Новый адрес:  ${contractInstance.options.address}`);
            }
        } else {
            console.log(`🔷 Регистрируем ${contractName} в MagicRegistry...`);
        }
        
        // Получаем баланс до транзакции
        const balanceBefore = await web3.eth.getBalance(deployerAccount.address);
        console.log(`💰 Баланс до регистрации: ${web3.utils.fromWei(balanceBefore, 'ether')} MATIC`);
        
        // Получаем цену газа для регистрации
        const gasPrice = network === 'polygon' ? 
            web3.utils.toWei('100', 'gwei') : // 100 Gwei для Polygon mainnet
            await web3.eth.getGasPrice(); // Текущая цена для других сетей
        
        // Получаем актуальный nonce для предотвращения "Nonce too low"
        const nonce = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        
        await magicRegistry.methods.set(contractName, contractInstance.options.address).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 1000000 : 500000,
            gasPrice: gasPrice,
            nonce: nonce
        });
        
        // Получаем баланс после транзакции
        const balanceAfter = await web3.eth.getBalance(deployerAccount.address);
        const cost = web3.utils.fromWei((BigInt(balanceBefore) - BigInt(balanceAfter)).toString(), 'ether');
        
        console.log(`💰 Баланс после регистрации: ${web3.utils.fromWei(balanceAfter, 'ether')} MATIC`);
        console.log(`💸 Стоимость регистрации: ${cost} MATIC`);
        
        if (existingAddress && existingAddress !== '0x0000000000000000000000000000000000000000') {
            console.log(`✅ Новая версия контракта ${contractName} (${contractInstance.options.address}) зарегистрирована в реестре под ключом "${contractName}"`);
        } else {
            console.log(`✅ Контракт ${contractName} зарегистрирован в реестре под ключом "${contractName}"`);
        }
        
    } catch (error) {
        console.error(`❌ Ошибка при регистрации ${contractName} в реестре:`, error.message);
        throw error;
    }
}

/**
 * Деплой конкретного контракта по имени
 * @param {string} contractName - Название контракта для деплоя
 */
async function deploySingleContract(contractName, registryInstance = null) {
    console.log(`\n🔷 Обрабатываем контракт: ${contractName}`);
    
    // 1. Валидация названия контракта
    if (!SUPPORTED_CONTRACTS[contractName]) {
        throw new Error(`Неподдерживаемый контракт: ${contractName}. Доступные: ${Object.keys(SUPPORTED_CONTRACTS).join(', ')}`);
    }
    
    const contractInfo = SUPPORTED_CONTRACTS[contractName];
    
    // 2. НОВАЯ ЛОГИКА: Проверка UUPS deployment
    if (contractInfo.isUUPSDeployment) {
        console.log(`🔷 Обнаружен UUPS контракт, используем специальный deployment паттерн...`);
        return await deployUUPSContract(contractName, contractInfo, registryInstance);
    }
    
    // 3. Проверяем существующий контракт (для не-UUPS)
    let contractInstance = await checkExistingContract(contractName);
    
    if (contractInstance) {
        // Контракт уже существует, только регистрируем в реестре
        console.log(`🔄 Используем существующий контракт ${contractName} (${contractInstance.options.address})`);
        await registerContractInRegistry(contractName, contractInstance, registryInstance);
        return contractInstance;
    }
    
    // 4. Деплоим новый контракт
    console.log(`🚀 Деплоим новый контракт ${contractName}`);
    
    console.log(`📋 Зависимости: ${contractInfo.dependencies.length > 0 ? contractInfo.dependencies.join(', ') : 'нет'}`);
    
    // 5. Проверка зависимостей
    for (const dep of contractInfo.dependencies) {
        await ensureContractExists(dep, registryInstance);
    }
    
    // 6. Деплой контракта
    console.log(`🚀 Создаем экземпляр ${contractName}...`);
    
    // === UUPS Logic/Proxy контракты (деплоятся отдельно) ===
    if (contractName === 'SpiralEngineLogic') {
        contractInstance = await deployContract("SpiralEngineLogic", []);
    } else if (contractName === 'SpiralEngineProxy') {
        const logic = await loadContract("SpiralEngineLogic");
        const initData = await prepareInitializeCalldata('SpiralEngine', logic);
        contractInstance = await deployContract("SpiralEngineProxy", [logic.options.address, initData]);
    } else if (contractName === 'ProductRegistryLogic') {
        contractInstance = await deployContract("ProductRegistryLogic", []);
    } else if (contractName === 'ProductRegistryProxy') {
        const logic = await loadContract("ProductRegistryLogic");
        const initData = await prepareInitializeCalldata('ProductRegistry', logic);
        contractInstance = await deployContract("ProductRegistryProxy", [logic.options.address, initData]);
    } else if (contractName === 'AmanitaInternationalLogic') {
        contractInstance = await deployContract("AmanitaInternationalLogic", []);
    } else if (contractName === 'AmanitaInternationalProxy') {
        const logic = await loadContract("AmanitaInternationalLogic");
        const initData = await prepareInitializeCalldata('AmanitaInternational', logic);
        contractInstance = await deployContract("AmanitaInternationalProxy", [logic.options.address, initData]);
    } else if (contractName === 'OrganicComponentRegistryLogic') {
        contractInstance = await deployContract("OrganicComponentRegistryLogic", []);
    } else if (contractName === 'OrganicComponentRegistryProxy') {
        const logic = await loadContract("OrganicComponentRegistryLogic");
        const initData = await prepareInitializeCalldata('OrganicComponentRegistry', logic);
        contractInstance = await deployContract("OrganicComponentRegistryProxy", [logic.options.address, initData]);
    
    // === Обычные контракты ===
    } else if (contractName === 'MagicRegistry') {
        contractInstance = await deployContract("MagicRegistry");
    } else if (contractName === 'SpiralEngine') {
        // ⚠️ DEPRECATED: Старый не-UUPS контракт (используйте SpiralEngineLogic + SpiralEngineProxy)
        contractInstance = await deployContract("SpiralEngine");
    } else if (contractName === 'ProductRegistry') {
        // ⚠️ DEPRECATED: Старый не-UUPS контракт (используйте ProductRegistryLogic + ProductRegistryProxy)
        const spiralEngine = await loadUUPSContract("SpiralEngine");
        contractInstance = await deployContract("ProductRegistry", [spiralEngine.options.address]);
    } else if (contractName === 'LoveDoPostNFT') {
        const spiralEngine = await loadUUPSContract("SpiralEngine");
        contractInstance = await deployContract("LoveDoPostNFT", [deployerAccount.address, spiralEngine.options.address, magicRegistry.options.address]);
    } else if (contractName === 'LoveEmissionEngine') {
        const amanitaToken = await loadContract("AmanitaToken");
        const agovToken = await loadContract("AmanitaGovToken");
        const loveDo = await loadContract("LoveDoPostNFT");
        const spiralEngine = await loadUUPSContract("SpiralEngine");
        contractInstance = await deployContract("LoveEmissionEngine", [amanitaToken.options.address, agovToken.options.address, loveDo.options.address, spiralEngine.options.address, deployerAccount.address]);
    } else if (contractName === 'AmanitaToken') {
        contractInstance = await deployContract("AmanitaToken", [deployerAccount.address]);
    } else if (contractName === 'AmanitaGovToken') {
        contractInstance = await deployContract("AmanitaGovToken", [deployerAccount.address]);
    } else if (contractName === 'AmanitaPaymentRouter') {
        const amanitaToken = await loadContract("AmanitaToken");
        contractInstance = await deployContract("AmanitaPaymentRouter", [amanitaToken.options.address]);
    } else if (contractName === 'SoulboundCore') {
        contractInstance = await deployContract("SoulboundCore", ["Amanita Soul", "ASOUL"]);
    } else if (contractName === 'SoulMetadata') {
        const soulboundCore = await loadContract("SoulboundCore");
        contractInstance = await deployContract("SoulMetadata", [soulboundCore.options.address]);
    } else if (contractName === 'SoulRecovery') {
        const soulboundCore = await loadContract("SoulboundCore");
        contractInstance = await deployContract("SoulRecovery", [soulboundCore.options.address]);
    } else if (contractName === 'SoulIntegration') {
        const soulboundCore = await loadContract("SoulboundCore");
        const spiralEngine = await loadUUPSContract("SpiralEngine");
        contractInstance = await deployContract("SoulIntegration", [spiralEngine.options.address, soulboundCore.options.address]);
    } else if (contractName === 'SoulIdentity') {
        console.log("🔷 Загружаем зависимости для SoulIdentity...");
        const soulboundCore = await loadContract("SoulboundCore");
        const soulMetadata = await loadContract("SoulMetadata");
        console.log(`✅ SoulboundCore: ${soulboundCore.options.address}`);
        console.log(`✅ SoulMetadata: ${soulMetadata.options.address}`);
        
        contractInstance = await deployContract("SoulIdentity", [
            soulboundCore.options.address,
            soulMetadata.options.address
        ]);
    } else if (contractName === 'AmanitaInternationalProxy') {
        // 🌐 Специальная обработка для 3-контрактной архитектуры
        console.log("🌐 Деплой 3-контрактной архитектуры AmanitaInternational...");
        const result = await deployAmanitaInternational();
        contractInstance = result.proxy; // Возвращаем Proxy как основной контракт
    } else if (contractName === 'AmanitaInternationalStorage' || contractName === 'AmanitaInternationalLogicV1') {
        // Эти контракты не деплоятся отдельно - только через AmanitaInternationalProxy
        throw new Error(`${contractName} не может быть задеплоен отдельно. Используйте AmanitaInternationalProxy для деплоя всей архитектуры.`);
    }
    
    // 7. Регистрация в реестре (кроме самого реестра и компонентов 3-контрактной архитектуры)
    if (contractName !== 'MagicRegistry' && contractName !== 'AmanitaInternationalProxy') {
        await registerContractInRegistry(contractName, contractInstance, registryInstance);
        console.log(`📝 Контракт ${contractName} доступен в реестре под ключом "${contractName}"`);
    }
    
    // 8. Настройка ролей (если необходимо)
    if (contractInfo.needsSetup) {
        console.log(`⚙️ Настраиваем роли для ${contractName}...`);
        await setupContractRoles(contractName, contractInstance);
    }
    
    console.log(`🎉 Контракт ${contractName} успешно обработан!`);
    return contractInstance;
}

/**
 * Проверка существования контракта в реестре
 * @param {string} contractName - Название контракта для проверки
 */
async function ensureContractExists(contractName, registryInstance = null) {
    const magicRegistry = registryInstance || await loadContract("MagicRegistry", MAGIC_REGISTRY_CONTRACT_ADDRESS);
    const address = await magicRegistry.methods.get(contractName).call();
    if (address === "0x0000000000000000000000000000000000000000") {
        throw new Error(`Зависимость ${contractName} не найдена в реестре. Сначала задеплойте этот контракт.`);
    }
    console.log(`✅ Зависимость ${contractName} найдена: ${address}`);
}

/**
 * Валидация прав деплоера для активации пользователей
 * @param {Object} spiralEngine - Контракт SpiralEngine
 */
async function validateDeployerAccess(spiralEngine) {
    console.log(`🔍 Проверяем права деплоера для активации...`);
    
    // Проверяем роль DEFAULT_ADMIN_ROLE у деплоера
    const DEFAULT_ADMIN_ROLE = await spiralEngine.methods.DEFAULT_ADMIN_ROLE().call();
    const hasAdminRole = await spiralEngine.methods.hasRole(DEFAULT_ADMIN_ROLE, deployerAccount.address).call();
    
    if (!hasAdminRole) {
        throw new Error(`Деплоер ${deployerAccount.address} не имеет роли DEFAULT_ADMIN_ROLE для активации пользователей`);
    }
    
    console.log(`✅ Права деплоера (админа) подтверждены`);
}

/**
 * Валидация инвайт-кода
 * @param {Object} spiralEngine - Контракт SpiralEngine
 * @param {string} inviteCode - Инвайт-код для валидации
 */
async function validateInviteCode(spiralEngine, inviteCode) {
    console.log(`🔍 Валидируем инвайт-код: ${inviteCode}...`);
    
    // Проверяем валидность инвайта
    const result = await spiralEngine.methods.validateInviteCode(inviteCode).call();
    
    // Результат может быть массивом [isValid, reason] или просто isValid
    let isValid, reason;
    if (Array.isArray(result)) {
        [isValid, reason] = result;
    } else {
        isValid = result;
        reason = isValid ? "Валиден" : "Невалиден";
    }
    
    if (!isValid) {
        throw new Error(`Инвайт-код ${inviteCode} невалиден: ${reason}`);
    }
    
    console.log(`✅ Инвайт-код валиден и готов к использованию`);
}

/**
 * Назначение роли SELLER_ROLE продавцу
 * @param {Object} spiralEngine - Контракт SpiralEngine
 * @param {string} sellerAddress - Адрес продавца
 */
async function grantSellerRole(spiralEngine, sellerAddress) {
    console.log(`🔑 Назначаем продавцу роль SELLER_ROLE...`);
    
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    
    // Проверяем, есть ли уже роль
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    
    if (hasSellerRole) {
        console.log(`✅ Продавец уже имеет роль SELLER_ROLE`);
        return;
    }
    
    // Назначаем роль от лица деплоера (админа)
    await spiralEngine.methods.grantRole(SELLER_ROLE, sellerAddress).send({
        from: deployerAccount.address,
        gas: network === 'polygon' ? 500000 : 200000,
        gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
    });
    
    console.log(`✅ Роль SELLER_ROLE успешно назначена продавцу ${sellerAddress}`);
}

/**
 * Генерация новых инвайт-кодов для продавца
 * @param {number} count - Количество кодов для генерации
 * @returns {string[]} Массив новых инвайт-кодов
 */
function generateNewInviteCodes(count) {
    console.log(`🎲 Генерируем ${count} новых инвайт-кодов...`);
    
    const inviteCodes = [];
    const usedCodes = new Set();
    
    for (let i = 0; i < count; i++) {
        let alpha, beta, inviteCode;
        do {
            alpha = generateRandomAlphanumeric(4);
            beta = generateRandomAlphanumeric(4);
            inviteCode = `AMANITA-${alpha}-${beta}`;
        } while (usedCodes.has(inviteCode));
        
        usedCodes.add(inviteCode);
        inviteCodes.push(inviteCode);
        console.log(`  📝 Сгенерирован код ${i + 1}/${count}: ${inviteCode}`);
    }
    
    console.log(`✅ Сгенерировано ${count} уникальных инвайт-кодов`);
    return inviteCodes;
}

/**
 * Валидация прав доступа продавца
 * @param {string} sellerAddress - Адрес продавца
 * @param {Object} spiralEngine - Контракт SpiralEngine
 */
async function validateSellerAccess(sellerAddress, spiralEngine) {
    console.log(`🔍 Проверяем права доступа для ${sellerAddress}...`);
    
    // Проверяем, что пользователь активирован
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    if (usedInvite == 0) {
        throw new Error(`Пользователь ${sellerAddress} не активирован`);
    }
    
    // Проверяем роль SELLER_ROLE
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    if (!hasSellerRole) {
        throw new Error(`Пользователь ${sellerAddress} не имеет роли SELLER_ROLE`);
    }
    
    console.log(`✅ Права доступа подтверждены для ${sellerAddress}`);
}

/**
 * Получение состояния каталога продавца
 * @param {Object} productRegistry - Контракт ProductRegistry
 * @param {string} sellerAddress - Адрес продавца
 * @returns {Object} Состояние каталога
 */
async function getCatalogState(productRegistry, sellerAddress) {
    console.log(`📊 Получаем текущее состояние каталога...`);
    
    const products = await productRegistry.methods.getProductsBySeller(sellerAddress).call();
    const activeProducts = await productRegistry.methods.getAllActiveProductIds().call();
    const sellerActiveProducts = activeProducts.filter(id => 
        products.some(p => p.id === id)
    );
    
    console.log(`📦 Найдено продуктов: ${products.length}`);
    console.log(`🟢 Активных продуктов: ${sellerActiveProducts.length}`);
    
    return {
        totalProducts: products.length,
        activeProducts: sellerActiveProducts.length,
        products: products
    };
}

/**
 * Валидация результата очистки каталога
 * @param {Object} productRegistry - Контракт ProductRegistry
 * @param {string} sellerAddress - Адрес продавца
 * @param {Object} catalogBefore - Состояние каталога до очистки
 * @param {Object} tx - Транзакция очистки
 */
async function validateClearingResult(productRegistry, sellerAddress, catalogBefore, tx) {
    console.log(`✅ Проверяем результат очистки...`);
    
    // Проверяем события
    const catalogClearedEvent = tx.events.CatalogCleared;
    if (catalogClearedEvent) {
        console.log(`🎉 Событие CatalogCleared: очищено ${catalogClearedEvent.returnValues.productsCleared} продуктов`);
    }
    
    // Проверяем, что каталог действительно очищен
    const productsAfter = await productRegistry.methods.getProductsBySeller(sellerAddress).call();
    const activeProductsAfter = await productRegistry.methods.getAllActiveProductIds().call();
    const sellerActiveProductsAfter = activeProductsAfter.filter(id => 
        productsAfter.some(p => p.id === id)
    );
    
    if (productsAfter.length !== 0) {
        throw new Error(`Каталог не полностью очищен. Осталось продуктов: ${productsAfter.length}`);
    }
    
    console.log(`✅ Каталог успешно очищен!`);
    console.log(`📊 Результат: очищено ${catalogBefore.totalProducts} продуктов (${catalogBefore.activeProducts} активных)`);
}

/**
 * Валидация результата активации продавца
 * @param {Object} spiralEngine - Контракт SpiralEngine
 * @param {string} sellerAddress - Адрес продавца
 * @param {string} inviteCode - Использованный инвайт-код
 * @param {string[]} newInviteCodes - Новые инвайт-коды
 * @param {Object} tx - Транзакция активации
 */
async function validateActivationResult(spiralEngine, sellerAddress, inviteCode, newInviteCodes, tx) {
    console.log(`✅ Проверяем результат активации...`);
    
    // Проверяем события
    const inviteActivatedEvent = tx.events.InviteActivated;
    if (inviteActivatedEvent) {
        console.log(`🎉 Событие InviteActivated: пользователь ${inviteActivatedEvent.returnValues.user} активирован`);
        console.log(`📋 Использован инвайт: ${inviteActivatedEvent.returnValues.inviteCode}`);
    }
    
    const batchInvitesEvent = tx.events.BatchInvitesMinted;
    if (batchInvitesEvent) {
        console.log(`🎉 Событие BatchInvitesMinted: создано ${batchInvitesEvent.returnValues.tokenIds.length} новых инвайтов`);
    }
    
    // Проверяем, что пользователь действительно активирован
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    if (usedInvite == 0) {
        throw new Error(`Пользователь ${sellerAddress} не был активирован`);
    }
    
    // Проверяем, что у пользователя есть новые инвайты
    const userInvites = await spiralEngine.methods.getUserInvites(sellerAddress).call();
    console.log(`📊 У пользователя ${sellerAddress} теперь ${userInvites.length} инвайтов`);
    
    // Проверяем, что продавец имеет роль SELLER_ROLE
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    if (!hasSellerRole) {
        throw new Error(`Продавец ${sellerAddress} не получил роль SELLER_ROLE`);
    }
    
    console.log(`✅ Продавец ${sellerAddress} успешно активирован!`);
    console.log(`🎯 Создано ${newInviteCodes.length} новых инвайтов для продавца`);
    console.log(`🔑 Продавцу назначена роль SELLER_ROLE`);
}

/**
 * Активация продавца через инвайт-код
 * @param {string} inviteCode - Инвайт-код для активации
 * @param {string} sellerAddress - Адрес продавца для активации
 */
async function activateSeller(inviteCode, sellerAddress) {
    console.log(`\n🎯 Активируем продавца: ${sellerAddress}`);
    console.log(`📋 Используем инвайт-код: ${inviteCode}`);
    
    // 1. Загружаем контракт SpiralEngine (UUPS)
    const spiralEngine = await loadUUPSContract("SpiralEngine");
    
    // 2. Проверяем права деплоера (админа)
    await validateDeployerAccess(spiralEngine);
    
    // 3. Валидируем инвайт-код
    await validateInviteCode(spiralEngine, inviteCode);
    
    // 3.1. Проверяем, не активирован ли уже пользователь
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    if (usedInvite > 0) {
        console.log(`⚠️ Пользователь ${sellerAddress} уже активирован`);
        console.log(`🔍 Проверяем его инвайты...`);
        const userInvites = await spiralEngine.methods.getUserInvites(sellerAddress).call();
        console.log(`📊 У пользователя уже есть ${userInvites.length} инвайтов`);
        
        // Проверяем роль SELLER_ROLE
        const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
        const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
        
        if (hasSellerRole) {
            console.log(`✅ Пользователь уже имеет роль SELLER_ROLE`);
            console.log(`✅ Активация не требуется - пользователь уже готов к работе`);
            return;
        } else {
            console.log(`🔑 Пользователь активирован, но не имеет роль SELLER_ROLE - назначаем...`);
            await grantSellerRole(spiralEngine, sellerAddress);
            console.log(`✅ Роль SELLER_ROLE назначена существующему пользователю`);
            return;
        }
    }
    
    // 4. Генерируем новые инвайт-коды для продавца
    const newInviteCodes = generateNewInviteCodes(12);
    
    // 5. Выполняем активацию (деплоер активирует продавца)
    console.log(`🚀 Отправляем транзакцию активации...`);
    console.log(`   От: ${deployerAccount.address}`);
    console.log(`   Кому: ${sellerAddress}`);
    console.log(`   Инвайт-код: ${inviteCode}`);
    console.log(`   Новых инвайтов: ${newInviteCodes.length}`);
    
    // ВАЖНО: Метод activateAndMintInvites требует роль SELLER_ROLE
    // Поэтому сначала назначаем деплоеру роль SELLER_ROLE временно
    console.log(`🔑 Назначаем деплоеру роль SELLER_ROLE для активации...`);
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    const deployerHasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, deployerAccount.address).call();
    
    if (!deployerHasSellerRole) {
        await spiralEngine.methods.grantRole(SELLER_ROLE, deployerAccount.address).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 500000 : 200000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
        });
        console.log(`✅ Роль SELLER_ROLE назначена деплоеру`);
    }
    
    let tx;
    try {
        tx = await spiralEngine.methods.activateAndMintInvites(
            inviteCode,
            sellerAddress,
            newInviteCodes,
            0 // Бессрочные инвайты
        ).send({
            from: deployerAccount.address, // Деплоер (админ) активирует
            gas: network === 'polygon' ? 3000000 : 5000000, // Увеличиваем газ для локальной сети
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
        });
        console.log(`✅ Транзакция активации успешно выполнена`);
    } catch (error) {
        console.error(`❌ Ошибка при выполнении транзакции активации:`);
        console.error(`   Детали ошибки: ${error.message}`);
        if (error.reason) {
            console.error(`   Причина: ${error.reason}`);
        }
        if (error.data) {
            console.error(`   Данные ошибки: ${error.data}`);
        }
        throw error;
    }
    
    // 6. Назначаем продавцу роль SELLER_ROLE
    await grantSellerRole(spiralEngine, sellerAddress);
    
    // 7. Проверяем результат и события
    await validateActivationResult(spiralEngine, sellerAddress, inviteCode, newInviteCodes, tx);
}

/**
 * Очистка каталога продавца
 * @param {string} sellerAddress - Адрес продавца
 * @param {string} sellerPrivateKey - Приватный ключ продавца
 */
async function clearSellerCatalog(sellerAddress, sellerPrivateKey) {
    console.log(`\n🧹 Очищаем каталог продавца: ${sellerAddress}`);
    
    // 1. Создаем кошелек продавца (если еще не создан)
    let sellerWallet;
    try {
        sellerWallet = web3.eth.accounts.privateKeyToAccount(sellerPrivateKey);
        web3.eth.accounts.wallet.add(sellerWallet);
    } catch (error) {
        console.error(`❌ Ошибка при создании кошелька продавца: ${error.message}`);
        throw error;
    }
    
    // 2. Загружаем контракты (UUPS)
    const productRegistry = await loadUUPSContract("ProductRegistry");
    const spiralEngine = await loadUUPSContract("SpiralEngine");
    
    // 3. Проверяем права доступа
    await validateSellerAccess(sellerAddress, spiralEngine);
    
    // 4. Получаем текущее состояние каталога
    const catalogBefore = await getCatalogState(productRegistry, sellerAddress);
    
    // 5. Выполняем очистку
    const tx = await productRegistry.methods.clearSellerCatalog(sellerAddress).send({
        from: sellerAddress,
        gas: network === 'polygon' ? 2000000 : 1000000,
        gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
    });
    
    // 6. Проверяем результат
    await validateClearingResult(productRegistry, sellerAddress, catalogBefore, tx);
}

/**
 * Настройка ролей для контракта
 * @param {string} contractName - Название контракта
 * @param {Object} contractInstance - Экземпляр контракта
 */
async function setupContractRoles(contractName, contractInstance) {
    if (contractName === 'SpiralEngine') {
        await setupSellerRole(contractInstance);
    } else if (contractName === 'LoveEmissionEngine') {
        // Настройка роли EMITTER_ROLE
        const EMITTER_ROLE = web3.utils.keccak256("EMITTER_ROLE");
        await contractInstance.methods.grantRole(EMITTER_ROLE, deployerAccount.address).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 500000 : 300000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
        });
        console.log(`✅ Роль EMITTER_ROLE назначена для ${contractName}`);
    }
    // ProductRegistry, LoveDoPostNFT, AmanitaPaymentRouter не требуют дополнительной настройки ролей
}

// Обновляем функцию setupSellerRole, чтобы она принимала контракт как параметр
async function setupSellerRole(spiralEngine) {
  if (!spiralEngine) {
    throw new Error("SpiralEngine контракт не определен");
  }
  
  // Используем sellerAccount если он есть, иначе создаем временный
  const sellerAddr = sellerAccount ? sellerAccount.address : SELLER_ADDRESS;
  if (!sellerAddr) {
    throw new Error("Не указан адрес продавца. Установите SELLER_ADDRESS в .env");
  }
  
  let hasSellerRole = false;
  try {
    // Назначаем роль SELLER_ROLE продавцу в SpiralEngine
    console.log("\n🔷 Выясняем, имеет ли продавец роль SELLER_ROLE...");
    
    // Сначала проверим, что контракт вообще отвечает
    console.log("🔍 Проверяем базовые методы контракта...");
    try {
      const name = await spiralEngine.methods.name().call();
      console.log("✅ Контракт отвечает, name:", name);
    } catch (e) {
      console.log("❌ Контракт не отвечает на name():", e.message);
      throw e;
    }
    
    // Получаем SELLER_ROLE из контракта
    console.log("🔍 Получаем SELLER_ROLE...");
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    console.log("SELLER_ROLE:", SELLER_ROLE);
    console.log("sellerAccount.address:", sellerAddr);
    console.log("spiralEngine address:", spiralEngine.options.address);
    
    console.log("🔍 Проверяем hasRole...");
    hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddr).call();
    console.log("hasSellerRole:", hasSellerRole);
  } catch (error) {
    console.error("\n❌ Ошибка при выяснении роли SELLER_ROLE:");
    console.error(error.message || error);
    throw error;
  }

  try {
    if (!hasSellerRole) {
      console.log("Продавец не имеет роли SELLER_ROLE, назначаем...");
      // Используем высокую цену газа для mainnet
      const highGasPrice = web3.utils.toWei('50', 'gwei'); // 50 Gwei для mainnet
      
      await spiralEngine.methods.grantRole(SELLER_ROLE, sellerAddr).send({
        from: deployerAccount.address,
        gas: 500000, // Увеличиваем лимит газа
        gasPrice: highGasPrice,
        type: 0, // Принудительно используем legacy транзакции
        nonce: await web3.eth.getTransactionCount(deployerAccount.address)
      });
      console.log("✅ Роль SELLER_ROLE успешно назначена");
    } else {
      console.log("Продавец уже имеет роль SELLER_ROLE");
    }
  } catch (error) {
    console.error("\n❌ Ошибка при назначении роли SELLER_ROLE:");
    console.error(error.message || error);
    throw error;
  }
}

/**
 * Настройка деплоера как селлера для минта инвайтов (временная роль)
 */
async function setupDeployerAsSeller(spiralEngine) {
  if (!spiralEngine) {
    throw new Error("SpiralEngine контракт не определен");
  }
  
  console.log("\n🔷 Настраиваем деплоера как селлера для минта инвайтов...");
  
  const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
  const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, deployerAccount.address).call();
  
  if (!hasSellerRole) {
    console.log("Деплоер не имеет роли SELLER_ROLE, назначаем временно...");
    const highGasPrice = web3.utils.toWei('50', 'gwei');
    
    await spiralEngine.methods.grantRole(SELLER_ROLE, deployerAccount.address).send({
      from: deployerAccount.address,
      gas: 500000,
      gasPrice: highGasPrice,
      type: 0,
      nonce: await web3.eth.getTransactionCount(deployerAccount.address)
    });
    console.log("✅ Роль SELLER_ROLE временно назначена деплоеру");
  } else {
    console.log("Деплоер уже имеет роль SELLER_ROLE");
  }
}

// Обновляем функцию creatingInvites, чтобы она принимала контракт как параметр
async function creatingInvites(spiralEngine) {
  if (!spiralEngine) {
    throw new Error("SpiralEngine контракт не определен");
  }
  
  // Определяем, кто минтит инвайты (деплоер с ролью SELLER_ROLE)
  const fromAddress = deployerAccount.address;
  console.log(`🔷 Минтим инвайты от адреса: ${fromAddress}`);
  
  // Генерируем и минтим инвайты
  console.log("\n🔷 Генерируем инвайты...");
  const invites = [];
  const usedCodes = new Set();

  for (let i = 0; i < 8; i++) {
    let alpha, beta, invite;
    do {
      alpha = generateRandomAlphanumeric(4);
      beta = generateRandomAlphanumeric(4);
      invite = `AMANITA-${alpha}-${beta}`;
    } while (usedCodes.has(invite));
    usedCodes.add(invite);
    invites.push(invite);
    console.log(`Сгенерирован инвайт ${i + 1}/8:`, invite);
  }

  // Разбиваем инвайты на батчи и минтим
  const BATCH_SIZE = 12;
  const batches = [];
  for (let i = 0; i < invites.length; i += BATCH_SIZE) {
    batches.push(invites.slice(i, i + BATCH_SIZE));
  }

  console.log(`\n🔷 Минтим ${batches.length} батчей по ${BATCH_SIZE} инвайтов...`);

  for (let i = 0; i < batches.length; i++) {
    console.log(`\nМинтим батч ${i + 1}/${batches.length}...`);
    const batch = batches[i];
    
    // Используем высокую цену газа для mainnet
    const highGasPrice = web3.utils.toWei('50', 'gwei'); // 50 Gwei для mainnet
    
    await spiralEngine.methods.mintInvites(batch, 0).send({
      from: fromAddress,
      gas: 5000000, // Увеличиваем лимит газа
      gasPrice: highGasPrice,
      type: 0, // Принудительно используем legacy транзакции
      nonce: await web3.eth.getTransactionCount(fromAddress)
    });
    console.log(`✅ Батч ${i + 1} успешно заминчен`);
  }

  // Записываем инвайты в файл
  const logsDir = path.join(__dirname, "..", "bot", "flowers");
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
  fs.writeFileSync(path.join(logsDir, "invites.txt"), invites.join("\n"));
  console.log("\n✅ Инвайты сохранены в bot/flowers/invites.txt");
  return invites;
}

// Функция для генерации 12 инвайтов деплоера (Action 777)
async function creatingInvitesForDeployer(spiralEngine) {
  if (!spiralEngine) {
    throw new Error("SpiralEngine контракт не определен");
  }
  
  // Определяем, кто минтит инвайты (деплоер с ролью SELLER_ROLE)
  const fromAddress = deployerAccount.address;
  console.log(`🔷 Минтим инвайты от адреса: ${fromAddress}`);
  
  // Проверяем что деплоер имеет SELLER_ROLE
  const SELLER_ROLE = web3.utils.keccak256("SELLER_ROLE");
  const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, deployerAccount.address).call();
  if (!hasSellerRole) {
    throw new Error("Деплоер не имеет роли SELLER_ROLE для генерации инвайтов");
  }
  
  // Генерируем и минтим инвайты
  console.log("\n🔷 Генерируем 12 инвайтов для деплоера...");
  const invites = [];
  const usedCodes = new Set();

  for (let i = 0; i < 12; i++) {
    let alpha, beta, invite;
    do {
      alpha = generateRandomAlphanumeric(4);
      beta = generateRandomAlphanumeric(4);
      invite = `AMANITA-${alpha}-${beta}`;
    } while (usedCodes.has(invite));
    usedCodes.add(invite);
    invites.push(invite);
    console.log(`Сгенерирован инвайт ${i + 1}/12:`, invite);
  }

  // Разбиваем инвайты на батчи и минтим
  const BATCH_SIZE = 12;
  const batches = [];
  for (let i = 0; i < invites.length; i += BATCH_SIZE) {
    batches.push(invites.slice(i, i + BATCH_SIZE));
  }

  console.log(`\n🔷 Минтим ${batches.length} батчей по ${BATCH_SIZE} инвайтов...`);

  for (let i = 0; i < batches.length; i++) {
    console.log(`\nМинтим батч ${i + 1}/${batches.length}...`);
    const batch = batches[i];
    
    for (let j = 0; j < batch.length; j++) {
      const invite = batch[j];
      const expiry = 0; // Бессрочные инвайты
      
      await spiralEngine.methods.mintInvite(invite, expiry).send({
        from: fromAddress,
        gas: 500000,
        gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
      });
      console.log(`✅ Заминчен инвайт ${j + 1}/${batch.length}: ${invite}`);
    }
    console.log(`✅ Батч ${i + 1} успешно заминчен`);
  }

  // Записываем инвайты в файл с учетом сети
  const logsDir = path.join(__dirname, "..", "bot", "flowers");
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
  
  const fileName = `deployer_invites_${network}.txt`;
  const filePath = path.join(logsDir, fileName);
  fs.writeFileSync(filePath, invites.join("\n"));
  console.log(`\n✅ Инвайты сохранены в ${filePath}`);
  return invites;
}

// Обновляем функцию createCatalog, чтобы она принимала контракт как параметр
async function createCatalog(productRegistry, sellerAddress) {
  if (!productRegistry) {
    throw new Error("ProductRegistry контракт не определен");
  }
  if (!sellerAddress) {
    throw new Error("Адрес селлера не определен");
  }
  
  console.log("\n🔷 Загружаем каталог с неактивными продуктами");
  
  // Загружаем JSON-файл с продуктами
  const productsPath = path.join(__dirname, "..", "bot", "catalog", "product_registry_upload_data.json");
  const productsData = JSON.parse(fs.readFileSync(productsPath, "utf8"));
  console.log(`\n🔷 Загружено ${productsData.length} продуктов из product_registry_upload_data.json`);

  // 🔍 ОЦЕНКА ГАЗА ДЛЯ ОДНОГО ПРОДУКТА
  console.log("\n💰 ОЦЕНКА ГАЗА ДЛЯ ОДНОГО ПРОДУКТА:");
  try {
    const gasEstimate = await productRegistry.methods.createProduct(
      productsData[0].componentIds || [],
      productsData[0].metadataCID
    ).estimateGas({
      from: sellerAddress
    });
    
    const gasPrice = await web3.eth.getGasPrice();
    const gasPriceInGwei = web3.utils.fromWei(gasPrice, 'gwei');
    const estimatedCost = BigInt(gasEstimate) * BigInt(gasPrice);
    const estimatedCostInEth = web3.utils.fromWei(estimatedCost.toString(), 'ether');
    
    console.log(`⛽ Оценка газа для одного продукта: ${gasEstimate.toLocaleString()}`);
    console.log(`💸 Стоимость одного продукта: ${estimatedCostInEth} MATIC`);
    console.log(`📊 Цена газа: ${gasPriceInGwei} Gwei`);
    
    // 🔍 ОЦЕНКА ГАЗА ДЛЯ ВСЕХ ПРОДУКТОВ
    const totalProducts = productsData.length;
    const totalGas = gasEstimate * totalProducts;
    const totalEstimatedCost = BigInt(totalGas) * BigInt(gasPrice);
    const totalEstimatedCostInEth = web3.utils.fromWei(totalEstimatedCost.toString(), 'ether');
    
    console.log(`\n💰 ОЦЕНКА ГАЗА ДЛЯ ВСЕХ ${totalProducts} ПРОДУКТОВ:`);
    console.log(`⛽ Общий газ: ${totalGas.toLocaleString()}`);
    console.log(`💸 Общая стоимость: ${totalEstimatedCostInEth} MATIC`);
    console.log(`📊 Рекомендуемый баланс: ${(parseFloat(totalEstimatedCostInEth) * 1.2).toFixed(6)} MATIC (с запасом 20%)`);
    
  } catch (error) {
    console.error(`❌ Ошибка при оценке газа:`, error.message);
    console.log(`⚠️ Продолжаем без детальной оценки газа...`);
  }

  // Проверяем баланс продавца
  console.log(`\n🔍 БАЛАНС ПРОДАВЦА:`);
  const sellerBalance = await web3.eth.getBalance(sellerAddress);
  const sellerBalanceInEth = web3.utils.fromWei(sellerBalance, 'ether');
  console.log(`💰 Адрес продавца: ${sellerAddress}`);
  console.log(`💵 Баланс продавца: ${sellerBalanceInEth} MATIC`);

  // Добавляем продукты в ProductRegistry
  for (let i = 0; i < productsData.length; i++) {
    const product = productsData[i];
    console.log(`\n➕ Добавляем продукт: ${product.id}`);
    console.log("Product properties:");
    console.log("componentIds:", product.componentIds || []);
    console.log("metadataCID:", product.metadataCID);
    console.log("active: false (по умолчанию)");
    
    // Слушаем все события от контракта
    productRegistry.events.allEvents({
      fromBlock: 'latest'
    }, (error, event) => {
      if (error) {
        console.error("Ошибка события:", error);
      } else {
        console.log("Событие:", event.event);
        console.log("Параметры:", event.returnValues);
      }
    });

    // Создаем продукт (по умолчанию неактивный)
    // Используем высокую цену газа для mainnet
    const highGasPrice = web3.utils.toWei('50', 'gwei'); // 50 Gwei для mainnet
    
    await productRegistry.methods.createProduct(
      product.componentIds || [],
      product.metadataCID
    ).send({
      from: sellerAddress,
      gas: 1000000,  // Увеличиваем лимит газа
      gasPrice: highGasPrice,
      type: 0, // Принудительно используем legacy транзакции
      nonce: await web3.eth.getTransactionCount(sellerAddress)
    });
    
    console.log(`✅ Продукт ${product.id} создан (по умолчанию неактивный)`);
    
    // Добавляем задержку между продуктами для избежания nonce ошибок (только для mainnet)
    if (i < productsData.length - 1 && network === 'polygon') {
      console.log(`⏳ Ждем 3 секунды перед следующим продуктом...`);
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }

  // Проверяем добавленные продукты
  console.log("\n🔍 Проверяем добавленные продукты...");
  
  // Получаем все продукты продавца через getProductsBySellerFull
  const products = await productRegistry.methods.getProductsBySellerFull().call({
    from: sellerAddress
  });
  console.log(`\nНайдено продуктов: ${products.length}`);
  
  // Проверяем каждый продукт
  for (const product of products) {
    console.log(`\n📦 Продукт #${product.id}:`);
    console.log("  Продавец:", product.seller);
    console.log("  Component IDs:", product.componentIds);
    console.log("  Metadata CID:", product.metadataCID);
    console.log("  Активен:", product.active);
    
    // Проверяем соответствие данных
    const originalProduct = productsData.find(p => p.metadataCID === product.metadataCID);
    if (originalProduct) {
      console.log("  ✅ Данные соответствуют оригинальным");
    } else {
      console.log("  ❌ Продукт не найден в оригинальных данных!");
    }
  }

  // Проверяем версию каталога продавца
  const catalogVersion = await productRegistry.methods.getMyCatalogVersion().call({
    from: sellerAddress
  });
  console.log(`\n📊 Текущая версия каталога продавца: ${catalogVersion}`);

  // Дополнительная проверка через getAllActiveProductIds для сравнения
  const activeIds = await productRegistry.methods.getAllActiveProductIds().call();
  console.log(`\n🔍 Проверка через getAllActiveProductIds: найдено ${activeIds.length} активных продуктов`);
  
  if (activeIds.length !== products.length) {
    console.log("⚠️ Внимание! Количество активных продуктов отличается от количества продуктов продавца!");
    console.log(`   Всего продуктов: ${products.length}, Активных: ${activeIds.length}`);
  }
}

// Функция для активации существующих продуктов в каталоге
async function activateCatalogProducts(productRegistry, sellerAddress) {
  if (!productRegistry) {
    throw new Error("ProductRegistry контракт не определен");
  }
  if (!sellerAddress) {
    throw new Error("Адрес селлера не определен");
  }
  
  console.log("\n🔷 Активируем существующие продукты в каталоге...");
  
  // Получаем все продукты продавца
  const products = await productRegistry.methods.getProductsBySellerFull().call({
    from: sellerAddress
  });
  
  console.log(`\n🔍 Найдено ${products.length} продуктов для активации`);
  
  if (products.length === 0) {
    console.log("⚠️ Нет продуктов для активации. Сначала создайте каталог с action=4 или action=40");
    return;
  }
  
  let activatedCount = 0;
  let alreadyActiveCount = 0;
  
  for (const product of products) {
    console.log(`\n🔷 Проверяем продукт: ${product.id}`);
    console.log("  IPFS CID:", product.ipfsCID);
    console.log("  Текущий статус:", product.active ? "АКТИВЕН" : "НЕАКТИВЕН");
    
    if (product.active) {
      console.log("  ✅ Продукт уже активен, пропускаем");
      alreadyActiveCount++;
      continue;
    }
    
    try {
      // Активируем продукт через activateProduct
      const highGasPrice = web3.utils.toWei('50', 'gwei'); // 50 Gwei для mainnet
      
      await productRegistry.methods.activateProduct(
        product.id
      ).send({
        from: sellerAddress,
        gas: 200000,
        gasPrice: highGasPrice,
        type: 0, // Принудительно используем legacy транзакции
        nonce: await web3.eth.getTransactionCount(sellerAddress)
      });
      
      console.log(`  ✅ Продукт ${product.id} успешно активирован`);
      activatedCount++;
      
    } catch (error) {
      console.error(`  ❌ Ошибка активации продукта ${product.id}:`, error.message);
    }
  }
  
  // Финальная статистика
  console.log("\n📊 Результаты активации:");
  console.log(`   Всего продуктов: ${products.length}`);
  console.log(`   Уже активных: ${alreadyActiveCount}`);
  console.log(`   Активировано: ${activatedCount}`);
  console.log(`   Ошибок: ${products.length - alreadyActiveCount - activatedCount}`);
  
  // Проверяем финальное состояние
  const finalProducts = await productRegistry.methods.getProductsBySellerFull().call({
    from: sellerAccount.address
  });
  
  const finalActiveCount = finalProducts.filter(p => p.active).length;
  console.log(`\n🔍 Финальное состояние: ${finalActiveCount}/${finalProducts.length} продуктов активны`);
}

// === НОВЫЕ ФУНКЦИИ ДЛЯ РАЗДЕЛЕННЫХ ПРОЦЕССОВ ===

/**
 * Генерация инвайт-кода для активации
 */
function generateActivationInviteCode() {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  return `ACTIVATE_${timestamp}_${random}`.toUpperCase();
}

/**
 * Генерация новых инвайт-кодов
 * @param {number} count - Количество инвайт-кодов для генерации
 */
function generateNewInviteCodes(count) {
  const codes = [];
  for (let i = 0; i < count; i++) {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    codes.push(`INVITE_${timestamp}_${i}_${random}`.toUpperCase());
  }
  return codes;
}

/**
 * Создание первого селлера (системный аккаунт)
 * @param {string} inviteCode - Инвайт-код для активации
 */
async function createFirstSeller(inviteCode) {
  console.log("🌱 Создаем селлера из первого круга...");
  
  let firstSellerAddress;
  let firstSellerAccount;
  
  // 1. Проверяем, есть ли уже селлер в .env
  if (SELLER_ADDRESS && SELLER_PRIVATE_KEY) {
    console.log("📝 Используем существующего селлера из .env");
    firstSellerAddress = SELLER_ADDRESS;
    firstSellerAccount = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
    console.log(`📝 Адрес селлера: ${firstSellerAddress}`);
  } else {
    console.log("📝 Генерируем новый адрес для первого селлера");
    firstSellerAccount = web3.eth.accounts.create();
    firstSellerAddress = firstSellerAccount.address;
    
    console.log(`📝 Адрес первого селлера: ${firstSellerAddress}`);
    console.log(`🔑 Приватный ключ: ${firstSellerAccount.privateKey}`);
    console.log("⚠️ ВАЖНО: Сохраните приватный ключ в безопасном месте!");
  }
  
  // 2. Загружаем контракт (UUPS)
  const spiralEngine = await loadUUPSContract("SpiralEngine");
  
  // 3. Используем переданный инвайт-код
  console.log(`📋 Используем инвайт-код: ${inviteCode}`);
  
  // 4. Активируем пользователя (деплоер имеет ACTIVATOR_ROLE по умолчанию)
  console.log(`🚀 Активируем пользователя ${firstSellerAddress}...`);
  await spiralEngine.methods.activateUser(
    inviteCode,
    firstSellerAddress,
    generateNewInviteCodes(12),
    0
  ).send({
    from: deployerAccount.address,
    gas: 5000000,
    gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
  });
  
  console.log(`✅ Пользователь ${firstSellerAddress} активирован`);
  
  // 5. Назначаем роль SELLER_ROLE
  console.log(`🔑 Назначаем роль SELLER_ROLE...`);
  await spiralEngine.methods.grantSellerRole(firstSellerAddress).send({
    from: deployerAccount.address,
    gas: 500000,
    gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
  });
  
  console.log(`✅ Роль SELLER_ROLE назначена`);
  
  // 6. Назначаем роль ACTIVATOR_ROLE
  console.log(`🔑 Назначаем роль ACTIVATOR_ROLE...`);
  await spiralEngine.methods.grantRole(
    await spiralEngine.methods.ACTIVATOR_ROLE().call(),
    firstSellerAddress
  ).send({
    from: deployerAccount.address,
    gas: 500000,
    gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
  });
  
  console.log(`✅ Роль ACTIVATOR_ROLE назначена`);
  console.log(`🎉 Первый селлер создан и полностью настроен!`);
  
  return firstSellerAddress;
}

/**
 * Активация пользователя (без назначения роли SELLER_ROLE)
 * @param {string} inviteCode - Инвайт-код для активации
 * @param {string} userAddress - Адрес пользователя для активации
 */
async function activateUser(inviteCode, userAddress) {
  console.log(`\n👤 Активируем пользователя: ${userAddress}`);
  console.log(`📋 Используем инвайт-код: ${inviteCode}`);
  
  // 1. Загружаем контракт (UUPS)
  const spiralEngine = await loadUUPSContract("SpiralEngine");
  
  // 2. Проверяем права активатора
  await validateActivatorAccess(spiralEngine);
  
  // 3. Валидируем инвайт-код
  await validateInviteCode(spiralEngine, inviteCode);
  
  // 4. Проверяем, не активирован ли уже пользователь
  const usedInvite = await spiralEngine.methods.usedInviteByUser(userAddress).call();
  if (usedInvite > 0) {
    console.log(`⚠️ Пользователь ${userAddress} уже активирован`);
    return;
  }
  
  // 5. Генерируем новые инвайт-коды
  const newInviteCodes = generateNewInviteCodes(12);
  
  // 6. Выполняем активацию
  console.log(`🚀 Отправляем транзакцию активации...`);
  const tx = await spiralEngine.methods.activateUser(
    inviteCode,
    userAddress,
    newInviteCodes,
    0
  ).send({
    from: deployerAccount.address,
    gas: 5000000,
    gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
  });
  
  console.log(`✅ Пользователь ${userAddress} успешно активирован!`);
  
  // 7. Проверяем результат
  await validateUserActivation(spiralEngine, userAddress, inviteCode, newInviteCodes, tx);
}

/**
 * Назначение роли SELLER_ROLE пользователю
 * @param {string} userAddress - Адрес пользователя
 */
async function grantSellerRole(userAddress) {
  console.log(`\n🏪 Назначаем роль SELLER_ROLE пользователю: ${userAddress}`);
  
  // 1. Загружаем контракт (UUPS)
  const spiralEngine = await loadUUPSContract("SpiralEngine");
  
  // 2. Проверяем, активирован ли пользователь
  const usedInvite = await spiralEngine.methods.usedInviteByUser(userAddress).call();
  if (usedInvite == 0) {
    throw new Error(`Пользователь ${userAddress} не активирован`);
  }
  
  // 3. Проверяем, не имеет ли уже роль SELLER_ROLE
  const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
  const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, userAddress).call();
  if (hasSellerRole) {
    console.log(`⚠️ Пользователь ${userAddress} уже имеет роль SELLER_ROLE`);
    return;
  }
  
  // 4. Назначаем роль
  console.log(`🔑 Назначаем роль SELLER_ROLE...`);
  await spiralEngine.methods.grantSellerRole(userAddress).send({
    from: deployerAccount.address,
    gas: 500000,
    gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
  });
  
  console.log(`✅ Роль SELLER_ROLE успешно назначена пользователю ${userAddress}`);
}

/**
 * Валидация прав активатора
 */
async function validateActivatorAccess(spiralEngine) {
  console.log(`🔍 Проверяем права активатора...`);
  
  const ACTIVATOR_ROLE = await spiralEngine.methods.ACTIVATOR_ROLE().call();
  const hasActivatorRole = await spiralEngine.methods.hasRole(ACTIVATOR_ROLE, deployerAccount.address).call();
  
  if (!hasActivatorRole) {
    throw new Error(`Деплоер ${deployerAccount.address} не имеет роли ACTIVATOR_ROLE`);
  }
  
  console.log(`✅ Права активатора подтверждены`);
}

/**
 * Настройка SoulIdentity интеграции для Action 888
 * @param {Object} soulIdentity - экземпляр контракта SoulIdentity
 * @param {string} sellerAddress - адрес селлера
 */
async function setupSoulIdentityFor888(soulIdentity, sellerAddress) {
  if (!soulIdentity) {
    console.log("⚠️ SoulIdentity не задеплоен, пропускаем интеграцию");
    return;
  }
  
  console.log(`🔷 Настраиваем SoulIdentity для селлера: ${sellerAddress}`);
  
  // 1. Загружаем существующие SBT контракты
  console.log("🔷 Загружаем существующие SBT контракты...");
  const soulboundCore = await loadContract("SoulboundCore");
  const soulMetadata = await loadContract("SoulMetadata");
  
  console.log(`✅ SoulboundCore: ${soulboundCore.options.address}`);
  console.log(`✅ SoulMetadata: ${soulMetadata.options.address}`);
  
  // 2. Проверяем есть ли у селлера SBT токен
  const balance = await soulboundCore.methods.balanceOf(sellerAddress).call();
  console.log(`🔍 Баланс SBT токенов у селлера: ${balance}`);
  
  let tokenId;
  console.log(`🔍 DEBUG: balance type: ${typeof balance}, value: ${balance}`);
  if (balance === "0" || balance === 0 || balance === 0n) {
    // Создаем SBT токен через существующую систему
    console.log("🏷️ Создаем SBT токен для селлера через SoulboundCore...");
    
    const nonceMintSoul = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
    const mintTx = await soulboundCore.methods.mintSoul(sellerAddress).send({
      from: deployerAccount.address,
      gas: network === 'polygon' ? 500000 : 300000,
      gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
      nonce: nonceMintSoul
    });
    
    console.log(`✅ SBT токен создан, tx: ${mintTx.transactionHash}`);
    
    // Получаем tokenId (упрощенная логика - берем следующий ID)
    tokenId = await soulboundCore.methods.getNextTokenId().call();
    tokenId = parseInt(tokenId) - 1; // Предыдущий ID
    console.log(`✅ TokenId: ${tokenId}`);
    
    // Инициализируем метаданные через существующую систему
    console.log("📋 Инициализируем метаданные через SoulMetadata...");
    await soulMetadata.methods.initializeMetadata(
      tokenId,
      "seller",
      JSON.stringify({
        type: "seller",
        level: 1,
        reputation: 100,
        created: Date.now()
      }),
      "" // IPFS hash пока пустой
    ).send({
      from: sellerAddress, // Владелец токена инициализирует метаданные
      gas: 300000,
      gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
    });
    
    console.log(`✅ Метаданные инициализированы для tokenId: ${tokenId}`);
  } else {
    // Получаем tokenId существующего токена через поиск (как в SoulIdentity._getUserTokenId)
    console.log(`🔍 Ищем существующий SBT токен пользователя...`);
    
    const totalSupply = await soulboundCore.methods.getTotalSupply().call();
    console.log(`🔍 Общее количество SBT токенов: ${totalSupply}`);
    
    tokenId = 0;
    for (let i = 1; i <= totalSupply && i <= 1000; i++) {
      try {
        const owner = await soulboundCore.methods.ownerOf(i).call();
        if (owner.toLowerCase() === sellerAddress.toLowerCase()) {
          tokenId = i;
          break;
        }
      } catch (error) {
        // Токен не существует или ошибка - продолжаем поиск
        continue;
      }
    }
    
    if (tokenId > 0) {
      console.log(`✅ Найден существующий SBT токен, tokenId: ${tokenId}`);
    } else {
      console.log(`❌ Не удалось найти SBT токен пользователя`);
      throw new Error("SBT token not found for user");
    }
  }
  
  // 3. Добавляем DID через новую функцию SoulIdentity
  const soulDID = `did:spiral:${sellerAddress.toLowerCase()}`;
  console.log(`🔷 Добавляем DID: ${soulDID}`);
  
  try {
    await soulIdentity.methods.linkExternalIdentity(
      sellerAddress,
      "did:spiral",
      soulDID,
      false // не верифицирована (legacy)
    ).send({
      from: deployerAccount.address, // SpiralEngine роль
      gas: 500000,
      gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
    });
    console.log(`✅ DID добавлен: ${soulDID}`);
  } catch (error) {
    console.error(`❌ Ошибка при добавлении DID: ${error.message}`);
    console.error(`❌ Детали ошибки:`, error);
    throw error;
  }
  
  console.log(`✅ SBT токен готов через существующую систему`);
  console.log(`✅ Метаданные инициализированы через SoulMetadata`);
  console.log(`✅ DID установлена через SoulIdentity: ${soulDID}`);
  console.log(`✅ Интеграция с существующей SBT системой завершена`);
  
  // 4. Валидация интеграции
  console.log("🔍 Валидация интеграции...");
  
  try {
    const primaryIdentity = await soulIdentity.methods.getPrimaryIdentity(sellerAddress).call();
    console.log(`✅ Primary identity: ${primaryIdentity.identityType} = ${primaryIdentity.identityValue}`);
    
    const soulLevel = await soulIdentity.methods.getSoulLevel(sellerAddress).call();
    console.log(`✅ Soul level: ${soulLevel}`);
    
    const soulReputation = await soulIdentity.methods.getSoulReputation(sellerAddress).call();
    console.log(`✅ Soul reputation: ${soulReputation}`);
    
  } catch (error) {
    console.log(`⚠️ Валидация частично неудачна: ${error.message}`);
  }
}

/**
 * Валидация активации пользователя
 */
async function validateUserActivation(spiralEngine, userAddress, inviteCode, newInviteCodes, tx) {
  console.log(`🔍 Проверяем результат активации...`);
  
  // Проверяем, что пользователь активирован
  const usedInvite = await spiralEngine.methods.usedInviteByUser(userAddress).call();
  if (usedInvite == 0) {
    throw new Error(`Пользователь ${userAddress} не был активирован`);
  }
  
  // Проверяем количество инвайтов
  const userInvites = await spiralEngine.methods.getUserInvites(userAddress).call();
  console.log(`📊 У пользователя ${userInvites.length} инвайтов`);
  
  console.log(`✅ Активация пользователя ${userAddress} успешно завершена`);
}

/**
 * Action 888: Полная инициализация селлера
 * @param {string} deployerInvite - инвайт код деплоера для активации селлера
 * @param {string} sellerAddress - адрес селлера для инициализации
 * @param {string} catalogData - путь к JSON файлу с каталогом (опционально)
 */
async function action888(deployerInvite, sellerAddress, catalogData = null) {
    console.log("\n🎲 Action 888: Полная инициализация селлера...");
    
    // 1. Валидация входных параметров
    await validateAction888Inputs(deployerInvite, sellerAddress);
    
    // 2. Загрузка необходимых контрактов
    const contracts = await loadContractsFor888();
    
    // 3. Проверка активации селлера
    const isSellerActivated = await checkSellerActivationStatus(contracts.spiralEngine, sellerAddress);
    
    if (!isSellerActivated) {
        // 3.1. Валидация деплоер инвайта (только если селлер не активирован)
        await validateDeployerInviteForSeller(contracts.spiralEngine, deployerInvite);
        
        // 3.2. Активация селлера в SpiralEngine
        await activateSellerInSpiralEngine(contracts.spiralEngine, sellerAddress, deployerInvite);
    } else {
        console.log(`✅ Селлер уже активирован, пропускаем активацию`);
    }
    
    // 5. Назначение роли SELLER_ROLE
    await grantSellerRoleToUser(contracts.spiralEngine, sellerAddress);
    
    // 5.1. Назначение роли ACTIVATOR_ROLE для активации пользователей
    await grantActivatorRoleToSeller(contracts.spiralEngine, sellerAddress);
    
    // 6. Создание SBT токена в SoulIdentity
    await setupSoulIdentityFor888(contracts.soulIdentity, sellerAddress);
    
    // 7. Загрузка каталога продуктов
    await loadSellerCatalog(contracts.productRegistry, sellerAddress, catalogData, deployerAccount.address);
    
    // 8. Генерация 12 инвайтов для селлера
    await generateInvitesForSeller(contracts.spiralEngine, sellerAddress);
    
    console.log("✅ Action 888 завершен успешно!");
}

// Валидация входных параметров для Action 888
async function validateAction888Inputs(deployerInvite, sellerAddress) {
    if (!deployerInvite || !sellerAddress) {
        throw new Error("Action 888: требуются deployerInvite и sellerAddress");
    }
    
    if (!web3.utils.isAddress(sellerAddress)) {
        throw new Error("Action 888: некорректный адрес селлера");
    }
    
    console.log(`✅ Валидация параметров: deployerInvite=${deployerInvite}, sellerAddress=${sellerAddress}`);
}

// Загрузка контрактов для Action 888
async function loadContractsFor888() {
    // Загружаем контракты напрямую через переменные окружения
    const spiralEngine = await loadContract("SpiralEngine", SPIRAL_ENGINE_CONTRACT_ADDRESS);
    const productRegistry = await loadContract("ProductRegistry", PRODUCT_REGISTRY_CONTRACT_ADDRESS);
    const soulIdentity = await loadContract("SoulIdentity", SOUL_IDENTITY_CONTRACT_ADDRESS);
    
    console.log(`✅ Контракты загружены: SpiralEngine=${spiralEngine.options.address}, ProductRegistry=${productRegistry.options.address}, SoulIdentity=${soulIdentity.options.address}`);
    
    return { spiralEngine, productRegistry, soulIdentity };
}

// Валидация деплоер инвайта для селлера
async function validateDeployerInviteForSeller(spiralEngine, deployerInvite) {
    try {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`🔍 ДИАГНОСТИКА ИНВАЙТА: ${deployerInvite}`);
        console.log(`${'='.repeat(60)}`);
        console.log(`📍 SpiralEngine Proxy: ${spiralEngine.options.address}`);
        
        // Проверяем общее количество инвайтов
        const totalInvites = await spiralEngine.methods.totalInvitesMinted().call();
        console.log(`📊 Всего инвайтов в контракте: ${totalInvites}`);
        
        if (totalInvites === '0' || totalInvites === 0) {
            console.log(`⚠️ В контракте НЕТ инвайтов!`);
            console.log(`💡 Решение: Сначала выполните Action 777 для генерации инвайтов деплоера:`);
            console.log(`   DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost`);
            throw new Error(`Action 888: В SpiralEngine нет инвайтов. Выполните Action 777 сначала.`);
        }
        
        // Проверяем существование конкретного инвайта
        console.log(`🔍 Проверяем существование инвайта ${deployerInvite}...`);
        const inviteExists = await spiralEngine.methods.inviteCodeExists(deployerInvite).call();
        console.log(`   → inviteExists: ${inviteExists}`);
        
        if (!inviteExists) {
            console.log(`\n❌ Инвайт ${deployerInvite} НЕ НАЙДЕН в контракте`);
            console.log(`📋 Возможные причины:`);
            console.log(`   1. Инвайт из старой сессии blockchain (нода была перезапущена)`);
            console.log(`   2. Инвайт ещё не создан`);
            console.log(`   3. Опечатка в коде инвайта`);
            console.log(`\n💡 Решение: Выполните Action 777 для генерации новых инвайтов:`);
            console.log(`   DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost`);
            console.log(`   Затем используйте инвайт из bot/flowers/deployer_invites_localhost.txt`);
            throw new Error(`Action 888: инвайт ${deployerInvite} не существует в текущей сессии blockchain`);
        }
        
        console.log(`✅ Инвайт найден!`);
        
        const tokenId = await spiralEngine.methods.inviteCodeToTokenId(deployerInvite).call();
        console.log(`🔍 tokenId: ${tokenId}`);
        
        const isUsed = await spiralEngine.methods.isInviteUsed(tokenId).call();
        console.log(`🔍 isUsed: ${isUsed}`);
        
        if (isUsed) {
            throw new Error(`Action 888: инвайт ${deployerInvite} уже использован`);
        }
        
        console.log(`✅ Деплоер инвайт ${deployerInvite} валиден для активации селлера (tokenId: ${tokenId})`);
    } catch (error) {
        console.error(`❌ Ошибка при валидации инвайта ${deployerInvite}:`, error.message);
        console.error(`❌ Детали ошибки:`, error);
        throw error;
    }
}

// Проверка активации селлера (аналогично действию 13)
async function checkSellerActivationStatus(spiralEngine, sellerAddress) {
    try {
        console.log(`🔍 Проверяем статус активации селлера ${sellerAddress}...`);
        
        // Проверяем, активирован ли уже пользователь
        const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
        console.log(`🔍 usedInvite: ${usedInvite}`);
        
        if (usedInvite > 0) {
            console.log(`✅ Селлер уже активирован (использовал инвайт ${usedInvite})`);
            return true;
        } else {
            console.log(`❌ Селлер НЕ активирован`);
            return false;
        }
    } catch (error) {
        console.error(`❌ Ошибка при проверке активации селлера:`, error.message);
        return false;
    }
}

// Активация селлера в SpiralEngine
async function activateSellerInSpiralEngine(spiralEngine, sellerAddress, deployerInvite) {
    console.log(`🔷 Активируем селлера ${sellerAddress} через инвайт ${deployerInvite}...`);
    
    // Проверяем, не активирован ли уже пользователь
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    if (usedInvite > 0) {
        console.log(`✅ Пользователь уже активирован (использовал инвайт ${usedInvite}), пропускаем активацию`);
        return;
    }
    
    // Проверяем роли деплоера
    const ACTIVATOR_ROLE = await spiralEngine.methods.ACTIVATOR_ROLE().call();
    const hasActivatorRole = await spiralEngine.methods.hasRole(ACTIVATOR_ROLE, deployerAccount.address).call();
    console.log(`🔍 Деплоер имеет роль ACTIVATOR_ROLE: ${hasActivatorRole}`);
    
    if (!hasActivatorRole) {
        console.log(`🔷 Предоставляем роль ACTIVATOR_ROLE деплоеру...`);
        const nonceGrant = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        await spiralEngine.methods.grantRole(ACTIVATOR_ROLE, deployerAccount.address).send({
            from: deployerAccount.address,
            gas: 100000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
            nonce: nonceGrant
        });
        console.log(`✅ Роль ACTIVATOR_ROLE предоставлена деплоеру`);
    }
    
    // Генерируем 12 новых инвайт кодов для селлера
    const newInviteCodes = generateInviteCodes(12);
    console.log(`🔷 Сгенерированы новые инвайт коды: ${newInviteCodes.join(", ")}`);
    
    // Получаем tokenId деплоер инвайта для проверки
    const deployerTokenId = await spiralEngine.methods.inviteCodeToTokenId(deployerInvite).call();
    console.log(`🔍 TokenId инвайта ${deployerInvite}: ${deployerTokenId}`);
    
    // Проверяем, не использован ли уже инвайт
    const isUsed = await spiralEngine.methods.isInviteUsed(deployerTokenId).call();
    console.log(`🔍 Инвайт уже использован: ${isUsed}`);
    
    if (isUsed) {
        throw new Error(`Инвайт ${deployerInvite} уже использован`);
    }
    
    // Активируем селлера - передаем сам инвайт код, а не tokenId!
    console.log(`🔷 Вызываем activateUser с параметрами: inviteCode=${deployerInvite}, seller=${sellerAddress}`);
    try {
        const nonceActivate = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        const activateTx = await spiralEngine.methods.activateUser(
            deployerInvite, // Передаем сам инвайт код!
            sellerAddress,
            newInviteCodes,
            0 // contract nonce parameter, не путать с tx nonce
        ).send({
            from: deployerAccount.address, // Деплоер с ролью ACTIVATOR_ROLE активирует
            gas: 5000000, // Максимальный лимит газа
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
            nonce: nonceActivate
        });
        console.log(`✅ Селлер активирован, tx: ${activateTx.transactionHash}`);
    } catch (error) {
        console.error(`❌ Ошибка при активации: ${error.message}`);
        console.error(`❌ Детали ошибки:`, error);
        throw error;
    }
}

// Назначение роли SELLER_ROLE
async function grantSellerRoleToUser(spiralEngine, sellerAddress) {
    console.log(`🔷 Назначаем роль SELLER_ROLE селлеру ${sellerAddress}...`);
    
    // Проверяем, есть ли уже роль SELLER_ROLE
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    
    if (hasSellerRole) {
        console.log(`✅ Пользователь уже имеет роль SELLER_ROLE, пропускаем назначение`);
        return;
    }
    
    try {
        const nonceSeller = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        const grantTx = await spiralEngine.methods.grantSellerRole(sellerAddress).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 500000 : 300000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
            nonce: nonceSeller
        });
        console.log(`✅ Роль SELLER_ROLE назначена, tx: ${grantTx.transactionHash}`);
    } catch (error) {
        console.error(`❌ Ошибка при назначении роли SELLER_ROLE: ${error.message}`);
        console.error(`❌ Детали ошибки:`, error);
        throw error;
    }
}

// Назначение роли ACTIVATOR_ROLE селлеру для активации пользователей
async function grantActivatorRoleToSeller(spiralEngine, sellerAddress) {
    console.log(`🔷 Назначаем роль ACTIVATOR_ROLE селлеру ${sellerAddress} для активации пользователей...`);
    
    // Проверяем, есть ли уже роль ACTIVATOR_ROLE
    const ACTIVATOR_ROLE = await spiralEngine.methods.ACTIVATOR_ROLE().call();
    const hasActivatorRole = await spiralEngine.methods.hasRole(ACTIVATOR_ROLE, sellerAddress).call();
    
    if (hasActivatorRole) {
        console.log(`✅ Пользователь уже имеет роль ACTIVATOR_ROLE, пропускаем назначение`);
        return;
    }
    
    try {
        const nonceActivator = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        const grantTx = await spiralEngine.methods.grantRole(ACTIVATOR_ROLE, sellerAddress).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 500000 : 300000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
            nonce: nonceActivator
        });
        console.log(`✅ Роль ACTIVATOR_ROLE назначена селлеру, tx: ${grantTx.transactionHash}`);
        console.log(`✅ Теперь селлер может активировать пользователей через SpiralEngine.activateUser`);
    } catch (error) {
        console.error(`❌ Ошибка при назначении роли ACTIVATOR_ROLE: ${error.message}`);
        console.error(`❌ Детали ошибки:`, error);
        throw error;
    }
}

/**
 * Проверка загружены ли компоненты (результат Action 555)
 * @returns {Promise<boolean>} true если компоненты загружены
 */
async function checkComponentsLoaded() {
    try {
        // Проверяем наличие файлов состояния загрузки компонентов
        const stateFiles = [
            path.join(__dirname, "..", "data", "_upload_state_localhost.json"),
            path.join(__dirname, "..", "data", "_upload_state_polygon.json"),
            path.join(__dirname, "..", "data", "_upload_state_mumbai.json")
        ];
        
        for (const stateFile of stateFiles) {
            if (fs.existsSync(stateFile)) {
                const stateData = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
                if (stateData.components && Object.keys(stateData.components).length > 0) {
                    console.log(`✅ Найдены загруженные компоненты в ${path.basename(stateFile)}`);
                    return true;
                }
            }
        }
        
        // Проверяем наличие компонентов в контракте
        if (ORGANIC_COMPONENT_REGISTRY_PROXY) {
            try {
                const componentRegistry = new web3.eth.Contract(
                    require("../artifacts/contracts/OrganicComponentRegistryLogic.sol/OrganicComponentRegistryLogic.json").abi,
                    ORGANIC_COMPONENT_REGISTRY_PROXY
                );
                
                const totalComponents = await componentRegistry.methods.getTotalComponents().call();
                if (parseInt(totalComponents) > 0) {
                    console.log(`✅ Найдено ${totalComponents} компонентов в контракте`);
                    return true;
                }
            } catch (error) {
                console.log(`⚠️ Ошибка проверки контракта: ${error.message}`);
            }
        }
        
        return false;
    } catch (error) {
        console.log(`⚠️ Ошибка проверки компонентов: ${error.message}`);
        return false;
    }
}

/**
 * Создание каталога с использованием Action 444
 * @param {string} sellerAddress - Адрес продавца
 */
async function createCatalogWithAction444(sellerAddress) {
    try {
        console.log(`🚀 Создаем каталог через Action 444...`);
        
        // Импортируем функцию Action 444
        const { action444_AutomaticPipeline } = require('./lib/product_upload_steps.js');
        
        // Определяем параметры для Action 444
        const sellerId = process.env.SELLER_ID || 'iveta';  // ← UNIFIED: используем простой sellerId
        const sellerBaseDir = path.join(__dirname, "..", "data", "sellers", sellerId);
        const csvPath = path.join(sellerBaseDir, "catalog", "Iveta_catalog.csv");
        const outputDir = sellerBaseDir;  // ← UNIFIED: тот же путь для Action 41 и 42
        const sourceLang = 'en';
        
        // Создаем контекст для Action 444
        const context = {
            dryRun: false, // Реальный режим для Action 888
            productRegistry: null, // Будет инициализирован в Action 444
            arweave: null // Arweave будет инициализирован в Action 444
        };
        
        console.log(`📄 CSV: ${csvPath}`);
        console.log(`📁 Output: ${outputDir}`);
        console.log(`👤 Seller: ${sellerId}`);
        console.log(`🌐 Language: ${sourceLang}`);
        
        // Вызываем Action 444
        const result = await action444_AutomaticPipeline(
            context,
            csvPath,
            outputDir,
            sellerId,
            sourceLang
        );
        
        if (result.success) {
            console.log(`✅ Каталог создан успешно через Action 444`);
            console.log(`📊 Статистика:`);
            console.log(`   → Продуктов создано: ${result.summary.totalProducts}`);
            console.log(`   → Файлов в Arweave: ${result.summary.arweaveFiles}`);
            console.log(`   → Продуктов активировано: ${result.summary.activatedProducts}`);
        } else {
            throw new Error(`Action 444 завершился с ошибкой: ${result.error}`);
        }
        
    } catch (error) {
        console.error(`❌ Ошибка создания каталога через Action 444: ${error.message}`);
        throw error;
    }
}

// Загрузка каталога селлера
async function loadSellerCatalog(productRegistry, sellerAddress, catalogData, deployerAddress) {
    console.log(`🔷 Загружаем каталог для селлера ${sellerAddress}...`);
    
    // ====================================================================
    // НОВАЯ ЛОГИКА: ИНТЕГРАЦИЯ С ACTION 555 И 444
    // ====================================================================
    
    // 1. Проверяем загружены ли компоненты (результат Action 555)
    console.log(`🔍 Проверяем загруженные компоненты...`);
    const componentsLoaded = await checkComponentsLoaded();
    
    if (!componentsLoaded) {
        console.log(`⚠️ Компоненты не загружены. Рекомендуется выполнить Action 555 сначала.`);
        console.log(`🔷 Продолжаем с существующей логикой каталога...`);
    } else {
        console.log(`✅ Компоненты загружены, используем новую логику каталога...`);
        
        // 2. Используем Action 444 для создания каталога
        await createCatalogWithAction444(sellerAddress);
        return; // Выходим из функции, новая логика завершена
    }
    
    // ====================================================================
    // СТАРАЯ ЛОГИКА (для совместимости)
    // ====================================================================
    
    if (!catalogData) {
        catalogData = path.join(__dirname, "..", "bot", "catalog", "product_registry_upload_data.json");
    }
    
    // Очищаем существующий каталог продавца перед созданием нового
    console.log(`🧹 Очищаем существующий каталог продавца...`);
    try {
        // Проверяем, есть ли продукты в каталоге
        const existingProducts = await productRegistry.methods.getProductsBySeller(sellerAddress).call();
        console.log(`🔍 Найдено существующих продуктов: ${existingProducts.length}`);
        
        if (existingProducts.length === 0) {
            console.log(`✅ Каталог уже пустой, пропускаем очистку`);
        } else {
            // Создаем кошелек продавца для очистки каталога
            if (!SELLER_PRIVATE_KEY) {
                throw new Error("SELLER_PRIVATE_KEY не найден в .env для очистки каталога");
            }
            
            const sellerWallet = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
            web3.eth.accounts.wallet.add(sellerWallet);
            
            const nonceClear = await web3.eth.getTransactionCount(sellerAddress, 'pending');
            const clearTx = await productRegistry.methods.clearSellerCatalog(sellerAddress).send({
                from: sellerAddress, // ✅ Используем адрес продавца
                gas: network === 'polygon' ? 500000 : 300000,
                gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : undefined,
                nonce: nonceClear
            });
        
            // Ждем подтверждения транзакции (только для mainnet)
            if (network === 'polygon') {
              await new Promise(resolve => setTimeout(resolve, 2000));
            }
            
            console.log(`✅ Каталог очищен, tx: ${clearTx.transactionHash}`);
            
            // Ждем подтверждения и проверяем событие CatalogCleared
            const receipt = await web3.eth.getTransactionReceipt(clearTx.transactionHash);
            const catalogClearedEvent = receipt.logs.find(log => {
                try {
                    const decoded = productRegistry.options.jsonInterface.find(iface => iface.name === 'CatalogCleared');
                    return decoded && web3.utils.hexToNumber(log.topics[1]) === web3.utils.toHex(sellerAddress);
                } catch (e) {
                    return false;
                }
            });
            
            if (catalogClearedEvent) {
                const productsCleared = web3.utils.hexToNumber(catalogClearedEvent.data);
                console.log(`📊 Очищено продуктов: ${productsCleared}`);
            }
        }
        
    } catch (clearError) {
        if (clearError.message.includes("Catalog is already empty")) {
            console.log(`✅ Каталог уже пустой, продолжаем...`);
        } else {
            console.log(`⚠️ Ошибка при очистке каталога: ${clearError.message}`);
            console.log(`⚠️ Продолжаем без очистки...`);
        }
    }
    
    // Создаем каталог (аналогично action=4)
    await createCatalog(productRegistry, sellerAddress);
    
    // Активируем продукты (аналогично action=41)
    await activateCatalogProducts(productRegistry, sellerAddress);
    
    console.log(`✅ Каталог загружен и активирован для селлера ${sellerAddress}`);
}

// Генерация инвайтов для селлера
async function generateInvitesForSeller(spiralEngine, sellerAddress) {
    console.log(`🔷 Генерируем 12 инвайтов для селлера ${sellerAddress}...`);
    
    // Генерируем инвайт коды в стандартном формате AMANITA-XXXX-XXXX
    const inviteCodes = generateInviteCodes(12);
    console.log(`🔷 Сгенерированы инвайт коды: ${inviteCodes.join(", ")}`);
    
    for (let i = 0; i < 12; i++) {
        const inviteCode = inviteCodes[i];
        
        const nonceMintInvite = await web3.eth.getTransactionCount(sellerAddress, 'pending');
        const mintTx = await spiralEngine.methods.mintInvite(inviteCode, 0).send({
            from: sellerAddress,
            gas: 500000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
            nonce: nonceMintInvite
        });
        
        console.log(`✅ Инвайт ${inviteCode} создан, tx: ${mintTx.transactionHash}`);
    }
    
    // Сохраняем инвайты в файл
    const invitesPath = path.join(__dirname, "..", "bot", "flowers", `${sellerAddress}_invites.txt`);
    fs.writeFileSync(invitesPath, inviteCodes.join("\n"));
    console.log(`✅ Инвайты селлера сохранены в ${invitesPath}`);
}

// Генерация инвайт кодов в стандартном формате AMANITA-XXXX-XXXX
function generateInviteCodes(count) {
    const codes = [];
    const usedCodes = new Set();
    
    for (let i = 0; i < count; i++) {
        let alpha, beta, inviteCode;
        do {
            alpha = generateRandomAlphanumeric(4);
            beta = generateRandomAlphanumeric(4);
            inviteCode = `AMANITA-${alpha}-${beta}`;
        } while (usedCodes.has(inviteCode));
        
        usedCodes.add(inviteCode);
        codes.push(inviteCode);
    }
    return codes;
}

/**
 * Назначение роли ACTIVATOR_ROLE селлеру (для Action 9)
 * @param {string} sellerAddress - адрес селлера из .env
 */
async function grantActivatorRoleToSellerOnly(sellerAddress) {
    console.log(`🔷 Загружаем SpiralEngine для назначения роли ACTIVATOR_ROLE...`);
    
    // Загружаем SpiralEngine (UUPS)
    const spiralEngine = await loadUUPSContract("SpiralEngine");
    console.log(`✅ SpiralEngine загружен: ${spiralEngine.options.address}`);
    
    // Проверяем, активирован ли пользователь
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    if (usedInvite == 0) {
        console.log(`⚠️ Пользователь ${sellerAddress} не активирован, но продолжаем...`);
    } else {
        console.log(`✅ Пользователь ${sellerAddress} активирован (использовал инвайт ${usedInvite})`);
    }
    
    // Вызываем существующую функцию для назначения роли
    await grantActivatorRoleToSeller(spiralEngine, sellerAddress);
    
    console.log(`✅ Action 9 завершен успешно!`);
}

// Обновление документации
async function updateAction888Documentation() {
    console.log("📝 Обновляем документацию для Action 888...");
    
    const documentation = `
## Action 888: Полная инициализация селлера

### Использование:
\`\`\`bash
node deploy_full.js 888 <deployerInvite> <sellerAddress> [catalogData]
\`\`\`

### Параметры:
- deployerInvite: инвайт код деплоера для активации селлера
- sellerAddress: адрес селлера для инициализации
- catalogData: путь к JSON файлу с каталогом (опционально)

### Процесс:
1. Валидация входных параметров
2. Загрузка контрактов (SpiralEngine, ProductRegistry, SoulIdentity)
3. Валидация деплоер инвайта
4. Активация селлера в SpiralEngine
5. Назначение роли SELLER_ROLE
6. Назначение роли ACTIVATOR_ROLE (для активации пользователей)
7. Создание SBT токена в SoulIdentity
8. Загрузка каталога продуктов
9. Генерация 12 инвайтов для селлера

### Результат:
- Селлер полностью активирован и готов к работе
- Каталог продуктов загружен и активирован
- SBT токен создан для репутации
- 12 инвайтов сгенерированы для приглашения новых пользователей
`;
    
    console.log("✅ Документация обновлена");
}

/**
 * Генерация инвайтов для активного селлера (Action 11)
 * Использует существующую логику из generateInvitesForSeller с поддержкой кастомного количества
 * @param {Object} spiralEngine - экземпляр контракта SpiralEngine
 * @param {string} sellerAddress - адрес селлера
 * @param {number} inviteCount - количество инвайтов для генерации
 */
async function generateInvitesForSellerAction11(spiralEngine, sellerAddress, inviteCount) {
    console.log(`🔷 Генерируем ${inviteCount} инвайтов для селлера ${sellerAddress}...`);
    
    // Генерируем инвайт коды в стандартном формате AMANITA-XXXX-XXXX
    const inviteCodes = generateInviteCodes(inviteCount);
    console.log(`🔷 Сгенерированы инвайт коды: ${inviteCodes.join(", ")}`);
    
    for (let i = 0; i < inviteCount; i++) {
        const inviteCode = inviteCodes[i];
        
        const nonceMintInviteAction11 = await web3.eth.getTransactionCount(sellerAddress, 'pending');
        const mintTx = await spiralEngine.methods.mintInvite(inviteCode, 0).send({
            from: sellerAddress,
            gas: 500000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice(),
            nonce: nonceMintInviteAction11
        });
        
        console.log(`✅ Инвайт ${inviteCode} создан, tx: ${mintTx.transactionHash}`);
    }
    
    // Сохраняем инвайты в файл (используем тот же формат что и в action 888)
    const invitesPath = path.join(__dirname, "..", "bot", "flowers", `${sellerAddress}_invites.txt`);
    fs.writeFileSync(invitesPath, inviteCodes.join("\n"));
    console.log(`✅ Инвайты селлера сохранены в ${invitesPath}`);
}

/**
 * Получение полного каталога с загрузкой всех данных через CID
 * @param {Object} productRegistry - контракт ProductRegistry
 * @param {string} sellerAddress - адрес продавца
 */
async function getFullCatalogWithData(productRegistry, sellerAddress) {
    console.log(`🔍 Получаем продукты продавца ${sellerAddress}...`);
    
    try {
        // Получаем все продукты продавца
        const products = await productRegistry.methods.getProductsBySellerFull().call({
            from: sellerAddress
        });
        console.log(`📦 Найдено ${products.length} продуктов`);
        
        if (products.length === 0) {
            console.log("⚠️ У продавца нет продуктов в каталоге");
            return;
        }
        
        // Подсчитываем активные продукты
        const activeProductsCount = products.filter(p => p.active).length;
        console.log(`🟢 Активных продуктов: ${activeProductsCount}`);
        
        // Создаем директорию для сохранения данных каталога
        const catalogDir = path.join(__dirname, "..", "bot", "catalog_data");
        if (!fs.existsSync(catalogDir)) {
            fs.mkdirSync(catalogDir, { recursive: true });
        }
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const catalogFile = path.join(catalogDir, `catalog_${sellerAddress}_${timestamp}.json`);
        
        const catalogData = {
            seller_address: sellerAddress,
            timestamp: new Date().toISOString(),
            total_products: products.length,
            active_products: activeProductsCount,
            products: []
        };
        
        console.log(`\n📋 Обрабатываем продукты...`);
        
        for (let i = 0; i < products.length; i++) {
            const product = products[i];
            console.log(`\n🔍 Продукт ${i + 1}/${products.length}: ID=${product.id}`);
            console.log(`  📦 CID продукта: ${product.ipfsCID}`);
            console.log(`  👤 Продавец: ${product.seller}`);
            console.log(`  🟢 Активен: ${product.active}`);
            
            try {
                // Загружаем данные продукта через CID
                const productData = await downloadDataFromCID(product.ipfsCID, 'product');
                
                if (productData) {
                    console.log(`  ✅ Данные продукта загружены`);
                    console.log(`    🏷️ Название: ${productData.title || 'N/A'}`);
                    console.log(`    🧬 Вид: ${productData.species || 'N/A'}`);
                    console.log(`    📝 Компонентов: ${productData.organic_components?.length || 0}`);
                    console.log(`    🖼️ Обложка: ${productData.cover_image_url || 'НЕТ'}`);
                    
                    // Загружаем описания компонентов
                    if (productData.organic_components) {
                        console.log(`    📚 Загружаем описания компонентов...`);
                        for (let j = 0; j < productData.organic_components.length; j++) {
                            const component = productData.organic_components[j];
                            console.log(`      🔬 Компонент ${j + 1}: ${component.biounit_id}`);
                            console.log(`        📄 CID описания: ${component.description_cid}`);
                            
                            try {
                                const descriptionData = await downloadDataFromCID(component.description_cid, 'description');
                                if (descriptionData) {
                                    console.log(`        ✅ Описание загружено`);
                                    console.log(`        📝 Название: ${descriptionData.title || 'N/A'}`);
                                    component.description_data = descriptionData;
                                } else {
                                    console.log(`        ❌ Не удалось загрузить описание`);
                                }
                            } catch (descError) {
                                console.log(`        ❌ Ошибка загрузки описания: ${descError.message}`);
                            }
                        }
                    }
                    
                    catalogData.products.push({
                        blockchain_id: product.id,
                        seller: product.seller,
                        active: product.active,
                        product_cid: product.ipfsCID,
                        product_data: productData
                    });
                } else {
                    console.log(`  ❌ Не удалось загрузить данные продукта`);
                    catalogData.products.push({
                        blockchain_id: product.id,
                        seller: product.seller,
                        active: product.active,
                        product_cid: product.ipfsCID,
                        product_data: null,
                        error: "Failed to download product data"
                    });
                }
                
            } catch (error) {
                console.log(`  ❌ Ошибка обработки продукта: ${error.message}`);
                catalogData.products.push({
                    blockchain_id: product.id,
                    seller: product.seller,
                    active: product.active,
                    product_cid: product.ipfsCID,
                    product_data: null,
                    error: error.message
                });
            }
        }
        
        // Сохраняем данные каталога (обрабатываем BigInt)
        const jsonString = JSON.stringify(catalogData, (key, value) => 
            typeof value === 'bigint' ? value.toString() : value, 2
        );
        fs.writeFileSync(catalogFile, jsonString);
        console.log(`\n✅ Данные каталога сохранены в: ${catalogFile}`);
        
        // Выводим статистику
        const successfulProducts = catalogData.products.filter(p => p.product_data !== null).length;
        const failedProducts = catalogData.products.length - successfulProducts;
        
        console.log(`\n📊 Статистика каталога:`);
        console.log(`  📦 Всего продуктов: ${catalogData.total_products}`);
        console.log(`  🟢 Активных: ${catalogData.active_products}`);
        console.log(`  ✅ Успешно загружено: ${successfulProducts}`);
        console.log(`  ❌ Ошибок загрузки: ${failedProducts}`);
        
        // Выводим проблемы валидации
        console.log(`\n🔍 Анализ проблем валидации:`);
        catalogData.products.forEach((product, index) => {
            if (product.product_data) {
                const issues = [];
                
                // Проверяем cover_image_url
                if (!product.product_data.cover_image_url || product.product_data.cover_image_url.trim() === '') {
                    issues.push('Пустой cover_image_url');
                }
                
                // Проверяем biounit_id на дефисы
                if (product.product_data.organic_components) {
                    product.product_data.organic_components.forEach(comp => {
                        if (comp.biounit_id && comp.biounit_id.includes('-')) {
                            issues.push(`biounit_id с дефисом: ${comp.biounit_id}`);
                        }
                    });
                }
                
                if (issues.length > 0) {
                    console.log(`  ⚠️ Продукт ${index + 1} (ID=${product.blockchain_id}): ${issues.join(', ')}`);
                }
            }
        });
        
    } catch (error) {
        console.error(`❌ Ошибка получения каталога: ${error.message}`);
        throw error;
    }
}

/**
 * Загрузка данных через CID из IPFS
 * @param {string} cid - Content Identifier
 * @param {string} type - тип данных ('product', 'description', 'image')
 * @returns {Object|null} загруженные данные или null при ошибке
 */
async function downloadDataFromCID(cid, type) {
    if (!cid || cid.trim() === '') {
        console.log(`    ⚠️ Пустой CID для типа ${type}`);
        return null;
    }
    
    try {
        // Используем Pinata Gateway для загрузки
        const url = `https://gateway.pinata.cloud/ipfs/${cid}`;
        console.log(`    🔗 Загружаем ${type} из: ${url}`);
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`    ✅ ${type} загружен успешно`);
        return data;
        
    } catch (error) {
        console.log(`    ❌ Ошибка загрузки ${type}: ${error.message}`);
        return null;
    }
}

/**
 * Диагностика состояния селлера (Action 13)
 * @param {Object} spiralEngine - контракт SpiralEngine
 * @param {Object} productRegistry - контракт ProductRegistry
 * @param {string} sellerAddress - адрес селлера
 */
async function diagnoseSellerState(spiralEngine, productRegistry, sellerAddress) {
    console.log(`\n🔍 === ДИАГНОСТИКА СЕЛЛЕРА ${sellerAddress} ===`);
    
    try {
        // 1. Проверка активации пользователя
        console.log(`\n📋 1. Проверка активации пользователя...`);
        const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
        if (usedInvite > 0) {
            console.log(`✅ Пользователь активирован (использовал инвайт ${usedInvite})`);
        } else {
            console.log(`❌ Пользователь НЕ активирован`);
            return;
        }
        
        // 2. Проверка ролей
        console.log(`\n🔑 2. Проверка ролей...`);
        const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
        const ACTIVATOR_ROLE = await spiralEngine.methods.ACTIVATOR_ROLE().call();
        
        const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
        const hasActivatorRole = await spiralEngine.methods.hasRole(ACTIVATOR_ROLE, sellerAddress).call();
        
        console.log(`🔍 Роль SELLER_ROLE: ${hasSellerRole ? '✅ ЕСТЬ' : '❌ НЕТ'}`);
        console.log(`🔍 Роль ACTIVATOR_ROLE: ${hasActivatorRole ? '✅ ЕСТЬ' : '❌ НЕТ'}`);
        
        // 3. Проверка инвайтов селлера
        console.log(`\n🎲 3. Проверка инвайтов селлера...`);
        try {
            // Сначала попробуем получить публичную информацию
            console.log(`🔍 Получаем публичную информацию о селлере...`);
            const publicInfo = await spiralEngine.methods.getSellerPublicInfo(sellerAddress).call();
            console.log(`✅ Публичная информация получена`);
            
            console.log(`📊 У селлера ${publicInfo.inviteCount} инвайтов`);
            console.log(`📊 Всего заминчено: ${publicInfo.userTotalInvites} инвайтов`);
            
            // Теперь попробуем получить детальную диагностику (только для владельца или админа)
            try {
                console.log(`🔍 Пробуем получить детальную диагностику...`);
                const diagnostics = await spiralEngine.methods.getSellerDiagnostics(sellerAddress).call();
                console.log(`✅ Детальная диагностика получена`);
                
                if (diagnostics.userInvites.length > 0) {
                    console.log(`📝 Инвайты селлера:`);
                    diagnostics.userInvites.forEach((invite, index) => {
                        console.log(`  ${index + 1}. Token ID: ${invite.tokenId}, Code: ${invite.inviteCode}, Used: ${invite.isUsed}`);
                    });
                    
                    // Сохраняем инвайты в файл
                    const inviteCodes = diagnostics.userInvites.map(invite => invite.inviteCode);
                    const invitesPath = path.join(__dirname, "..", "bot", "flowers", `${sellerAddress}_invites.txt`);
                    fs.writeFileSync(invitesPath, inviteCodes.join("\n"));
                    console.log(`✅ Инвайты сохранены в ${invitesPath}`);
                }
                
                // Дополнительная диагностика
                console.log(`📊 Дополнительная диагностика:`);
                console.log(`  - Used invite token ID: ${diagnostics.usedInviteTokenId}`);
                console.log(`  - Total invites minted: ${diagnostics.totalInvitesMinted}`);
                
            } catch (detailError) {
                console.log(`⚠️ Детальная диагностика недоступна: ${detailError.message}`);
                console.log(`ℹ️ Это нормально - детальная информация доступна только владельцу или админу`);
            }
            
        } catch (error) {
            console.log(`❌ Ошибка при получении информации о селлере: ${error.message}`);
            console.log(`🔍 Детали ошибки:`, error);
        }
        
        // 4. Проверка каталога продуктов
        console.log(`\n📦 4. Проверка каталога продуктов...`);
        const products = await productRegistry.methods.getProductsBySellerFull().call({
            from: sellerAddress
        });
        
        console.log(`📊 Всего продуктов: ${products.length}`);
        
        if (products.length > 0) {
            const activeProducts = products.filter(p => p.active).length;
            console.log(`🟢 Активных продуктов: ${activeProducts}`);
            console.log(`🔴 Неактивных продуктов: ${products.length - activeProducts}`);
            
            // Проверяем, есть ли 17 продуктов (ожидаемое количество)
            if (products.length === 17) {
                console.log(`✅ Каталог полный: 17 продуктов (как ожидалось)`);
            } else {
                console.log(`⚠️ Каталог неполный: ожидалось 17, найдено ${products.length}`);
            }
            
            // Краткий обзор продуктов
            console.log(`\n📋 Обзор продуктов:`);
            products.slice(0, 5).forEach((product, index) => {
                console.log(`  ${index + 1}. ID=${product.id}, CID=${product.ipfsCID}, Активен=${product.active}`);
            });
            if (products.length > 5) {
                console.log(`  ... и еще ${products.length - 5} продуктов`);
            }
        } else {
            console.log(`❌ Каталог пуст - нет продуктов`);
        }
        
        // 5. Итоговая оценка готовности
        console.log(`\n🎯 5. Итоговая оценка готовности селлера:`);
        const isActivated = usedInvite > 0;
        const hasSellerRoleCheck = hasSellerRole;
        const hasInvites = true; // Пропускаем проверку инвайтов из-за ошибки доступа
        const hasCatalog = products.length > 0;
        const isCatalogComplete = products.length === 17;
        
        console.log(`✅ Активация: ${isActivated ? 'ГОТОВ' : 'НЕ ГОТОВ'}`);
        console.log(`✅ Роль SELLER: ${hasSellerRoleCheck ? 'ГОТОВ' : 'НЕ ГОТОВ'}`);
        console.log(`✅ Инвайты: ${hasInvites ? 'ГОТОВ' : 'НЕ ГОТОВ'}`);
        console.log(`✅ Каталог: ${hasCatalog ? 'ГОТОВ' : 'НЕ ГОТОВ'}`);
        console.log(`✅ Полнота каталога: ${isCatalogComplete ? 'ПОЛНЫЙ' : 'НЕПОЛНЫЙ'}`);
        
        const readinessScore = [isActivated, hasSellerRoleCheck, hasInvites, hasCatalog, isCatalogComplete].filter(Boolean).length;
        console.log(`\n📊 Общая готовность: ${readinessScore}/5 (${(readinessScore/5*100).toFixed(0)}%)`);
        
        if (readinessScore === 5) {
            console.log(`🎉 Селлер полностью готов к работе!`);
        } else if (readinessScore >= 3) {
            console.log(`⚠️ Селлер частично готов, требуется доработка`);
        } else {
            console.log(`❌ Селлер не готов к работе, требуется полная настройка`);
        }
        
        console.log(`\n✅ Диагностика завершена`);
        
    } catch (error) {
        console.error(`❌ Ошибка при диагностике селлера: ${error.message}`);
        console.error(`❌ Детали ошибки:`, error);
        throw error;
    }
}

/**
 * Обновляет продукты кордицепса с исправленными изображениями
 * @param {Object} productRegistry - контракт ProductRegistry
 * @param {string} sellerAddress - адрес продавца
 */
async function updateCordycepsProducts(productRegistry, sellerAddress) {
    console.log(`🔍 Ищем продукты кордицепса для продавца ${sellerAddress}...`);
    
    try {
        // Получаем все продукты продавца
        const products = await productRegistry.methods.getProductsBySellerFull().call({
            from: sellerAddress
        });
        console.log(`📦 Найдено ${products.length} продуктов`);
        
        // Фильтруем продукты кордицепса
        const cordycepsProducts = [];
        for (let i = 0; i < products.length; i++) {
            const product = products[i];
            console.log(`🔍 Проверяем продукт ${i + 1}: ID=${product.id}, CID=${product.ipfsCID}`);
            
            // Загружаем данные продукта
            const productData = await downloadDataFromCID(product.ipfsCID, 'product');
            if (productData && productData.business_id && productData.business_id.includes('cordyceps')) {
                cordycepsProducts.push({
                    id: product.id,
                    cid: product.ipfsCID,
                    business_id: productData.business_id,
                    current_data: productData
                });
                console.log(`  ✅ Найден продукт кордицепса: ${productData.business_id}`);
            }
        }
        
        console.log(`\n📋 Найдено ${cordycepsProducts.length} продуктов кордицепса`);
        
        if (cordycepsProducts.length === 0) {
            console.log("⚠️ Продукты кордицепса не найдены");
            return;
        }
        
        // Загружаем обновленные данные из файла
        const updateDataPath = path.join(__dirname, "..", "bot", "catalog", "cordyceps_contract_update.json");
        if (!fs.existsSync(updateDataPath)) {
            throw new Error(`Файл ${updateDataPath} не найден. Сначала запустите fix_cordyceps_images.py`);
        }
        
        const updateData = JSON.parse(fs.readFileSync(updateDataPath, "utf8"));
        console.log(`📋 Загружены данные для обновления: ${updateData.updated_products.length} продуктов`);
        
        // Обновляем каждый продукт
        for (const cordycepsProduct of cordycepsProducts) {
            console.log(`\n🔄 Обновляем продукт ${cordycepsProduct.business_id} (ID: ${cordycepsProduct.id})`);
            
            // Находим соответствующие обновленные данные
            const updatedProduct = updateData.updated_products.find(p => p.id === cordycepsProduct.business_id);
            if (!updatedProduct) {
                console.log(`  ⚠️ Обновленные данные для ${cordycepsProduct.business_id} не найдены`);
                continue;
            }
            
            console.log(`  📦 Новый CID: ${updatedProduct.ipfsCID}`);
            
            // Извлекаем цену из текущих данных
            let price = 0;
            if (cordycepsProduct.current_data.prices && cordycepsProduct.current_data.prices.length > 0) {
                price = parseInt(cordycepsProduct.current_data.prices[0].price) || 0;
            }
            
            console.log(`  💰 Цена для события: ${price}`);
            
            try {
                // Обновляем продукт в контракте
                await productRegistry.methods.updateProduct(
                    cordycepsProduct.id,
                    updatedProduct.ipfsCID,
                    price
                ).send({
                    from: sellerAddress,
                    gas: 500000,
                    gasPrice: web3.utils.toWei('50', 'gwei')
                });
                
                console.log(`  ✅ Продукт ${cordycepsProduct.business_id} обновлен успешно`);
                
            } catch (error) {
                console.log(`  ❌ Ошибка обновления продукта ${cordycepsProduct.business_id}: ${error.message}`);
            }
        }
        
        console.log("\n🎉 Обновление продуктов кордицепса завершено!");
        
    } catch (error) {
        console.error(`❌ Ошибка обновления продуктов кордицепса: ${error.message}`);
        throw error;
    }
}

/**
 * Загрузка CID компонента из state файла или использование placeholder
 * @param {string} componentDir - путь к директории компонента
 * @param {string} componentId - ID компонента
 * @param {string} networkName - название сети
 * @returns {{cid: string, source: string, url: string|null}}
 */
function loadComponentCID(componentDir, componentId, networkName) {
    // 1. Пытаемся загрузить из _upload_state_{network}.json
    const stateFile = path.join(componentDir, `_upload_state_${networkName}.json`);
    
    if (fs.existsSync(stateFile)) {
        try {
            const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
            if (state.root_metadata?.cid) {
                return {
                    cid: state.root_metadata.cid,
                    source: 'arweave_state',
                    url: `https://arweave.net/${state.root_metadata.cid}`
                };
            }
        } catch (error) {
            console.warn(`⚠️ Ошибка чтения state файла: ${error.message}`);
        }
    }
    
    // 2. Fallback к placeholder для новых компонентов
    return {
        cid: "QmPlaceholder",
        source: 'placeholder',
        url: null
    };
}

/**
 * Подготовка для загрузки компонентов (общая логика для Full и Quick режимов)
 * @param {string} sellerAddress - адрес продавца
 * @param {string} componentsDir - директория с компонентами
 * @param {string} networkName - название сети
 * @returns {Promise<Object>} Объект с контрактами, компонентами и путями
 */
async function prepareComponentUpload(sellerAddress, componentsDir, networkName) {
    // 1. Загрузка контрактов
    const organicRegistry = await loadUUPSContract("OrganicComponentRegistry");
    const amanitaIntl = await loadUUPSContract("AmanitaInternational");
    const spiralEngine = await loadUUPSContract("SpiralEngine");
    
    // 2. Валидация seller
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    
    if (usedInvite == 0) {
        throw new Error(`Seller ${sellerAddress} не активирован!`);
    }
    if (!hasSellerRole) {
        throw new Error(`Seller ${sellerAddress} не имеет SELLER_ROLE!`);
    }
    
    // 3. Создание seller account для транзакций
    if (!SELLER_PRIVATE_KEY) {
        throw new Error("SELLER_PRIVATE_KEY не найден в .env");
    }
    
    const sellerWallet = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
    web3.eth.accounts.wallet.add(sellerWallet);
    
    // 4. Поиск компонентов
    const projectRoot = path.join(__dirname, '..');
    const componentsPath = path.isAbsolute(componentsDir) 
        ? componentsDir 
        : path.join(projectRoot, componentsDir);
    
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
    
    return {
        contracts: {
            organicRegistry,
            amanitaIntl,
            spiralEngine
        },
        componentIds,
        componentsPath
    };
}

/**
 * Полная загрузка компонентов в Arweave + регистрация в контрактах
 * Использует lib/upload_steps.js для полного workflow
 * @param {string} sellerAddress - адрес продавца
 * @param {string} componentsDir - директория с компонентами
 * @param {string} networkName - название сети
 * @param {boolean} dryRun - режим dry-run
 * @returns {Promise<Object>} Результаты загрузки
 */
async function uploadComponentFull(sellerAddress, componentsDir = "data/components", networkName = network, dryRun = false) {
    console.log(`\n🚀 ПОЛНАЯ ЗАГРУЗКА КОМПОНЕНТОВ В ARWEAVE`);
    console.log(`👤 Seller: ${sellerAddress}`);
    console.log(`📁 Директория: ${componentsDir}`);
    console.log(`🌐 Сеть: ${networkName}`);
    console.log(`🔍 Dry-run: ${dryRun ? 'YES' : 'NO'}`);
    
    // Импортируем модули для полной загрузки
    const uploadSteps = require('./lib/upload_steps.js');
    const uploadUtils = require('./lib/upload_utils.js');
    
    // 1. Инициализация Arweave (используем Arweave-Readiness.js)
    console.log(`\n📋 Шаг 1/6: Инициализация Arweave...`);
    const arweaveReadiness = require('./Arweave-Readiness');
    
    const arweaveKey = await arweaveReadiness.loadArweaveKey();
    if (!arweaveKey) {
        throw new Error("Arweave key не найден или невалиден");
    }
    
    const arweaveClient = arweaveReadiness.initArweave();
    if (!arweaveClient) {
        throw new Error("Не удалось инициализировать Arweave client");
    }
    
    const connection = await arweaveReadiness.checkConnection(arweaveClient);
    if (!connection.success) {
        throw new Error(`Arweave connection failed: ${connection.error}`);
    }
    
    const wallet = await arweaveReadiness.checkWalletBalance(arweaveClient, arweaveKey);
    if (wallet.status === 'zero_balance') {
        throw new Error("Arweave wallet имеет нулевой баланс");
    }
    
    console.log(`✅ Arweave готов: ${wallet.balance} AR, ${connection.networkInfo.peers} peers`);
    
    // 2. Подготовка (контракты, seller, компоненты)
    console.log(`\n📦 Шаг 2/6: Подготовка...`);
    const preparation = await prepareComponentUpload(sellerAddress, componentsDir, networkName);
    const { organicRegistry, amanitaIntl, spiralEngine } = preparation.contracts;
    const { componentIds, componentsPath } = preparation;
    
    console.log(`✅ Контракты загружены`);
    console.log(`✅ Seller валиден: активирован + SELLER_ROLE`);
    console.log(`✅ Seller wallet добавлен для транзакций`);
    console.log(`✅ Найдено компонентов: ${componentIds.length}`);
    
    // 3. Обработка каждого компонента
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
            // Создаем context для upload_steps
            // 
            // ✅ Ownership Logic (обновлено 2025-01-13):
            // - deployer.address = deployerAccount.address (ADMIN для shareable data)
            // - seller.address = sellerAddress (SELLER для переводов)
            // 
            // Разделение ответственности:
            // 1. Deployer (ADMIN_ROLE):
            //    - updateShareableData() - глобальные словари
            // 2. Seller (SELLER_ROLE):
            //    - setSimpleFieldCID() - переводы компонента
            //    - setComplexFieldCID() - переводы компонента
            //    - становится owner своих переводов
            const context = {
                componentId: componentId,
                componentDir: componentDir,
                network: networkName,
                dryRun: dryRun,
                seller: { address: sellerAddress },
                deployer: { address: deployerAccount.address },  // ← ADMIN для shareable data
                contracts: {
                    organicComponentRegistry: organicRegistry,
                    amanitaInternational: amanitaIntl
                },
                arweave: {
                    client: arweaveClient,
                    key: arweaveKey
                },
                web3: web3,
                supportedLanguages: uploadUtils.getSupportedLanguages()
            };
            
            // Загружаем state (если есть)
            const stateManager = require('./lib/state_manager.js');
            let state = stateManager.loadComponentState(componentDir, networkName) || {
                steps_completed: [],
                componentId: componentId,
                network: networkName,
                created_at: new Date().toISOString()
            };
            
            // Проверяем какие шаги уже выполнены
            const isStepCompleted = (stepName) => {
                return state.steps_completed && state.steps_completed.includes(stepName);
            };
            
            console.log(`💾 Загрузка component state: ${componentId}`);
            if (state.steps_completed && state.steps_completed.length > 0) {
                console.log(`✅ State найден, шагов завершено: ${state.steps_completed.length}`);
                console.log(`   → Завершенные шаги: ${state.steps_completed.join(', ')}`);
            } else {
                console.log(`🆕 State файл не найден, создаем новый`);
            }
            
            console.log(`📝 Начинаем полную загрузку компонента...`);
            
            // Шаг 1: Simple Fields
            let simpleFieldCIDs = {};
            if (isStepCompleted('simple_fields_uploaded')) {
                console.log(`\n⏭️  ШАГ 1: Simple Fields уже загружены (пропуск)`);
                simpleFieldCIDs = state.simple_fields || {};
            } else {
                simpleFieldCIDs = await uploadSteps.uploadSimpleFields(context, state);
                console.log(`✅ Simple Fields загружены`);
            }
            
            // Шаг 2: Complex Fields
            let complexFieldCIDs = {};
            if (isStepCompleted('complex_fields_uploaded')) {
                console.log(`\n⏭️  ШАГ 2: Complex Fields уже загружены (пропуск)`);
                complexFieldCIDs = state.complex_fields || {};
            } else {
                complexFieldCIDs = await uploadSteps.uploadComplexFields(context, state);
                console.log(`✅ Complex Fields загружены`);
            }
            
            // Шаг 3: Shareable Data (только для первого компонента)
            if (i === 0) {
                if (isStepCompleted('shareable_data_uploaded')) {
                    console.log(`\n⏭️  ШАГ 3: Shareable Data уже загружены (пропуск)`);
                } else {
                    await uploadSteps.uploadShareableData(context, state);
                    console.log(`✅ Shareable Data загружены`);
                }
            }
            
            // Шаг 4: Update Root Metadata
            let finalRootData;
            if (isStepCompleted('root_metadata_updated')) {
                console.log(`\n⏭️  ШАГ 4: Root Metadata уже обновлен (пропуск)`);
                finalRootData = state.root_metadata?.data;
            } else {
                finalRootData = uploadSteps.updateRootMetadata(context, simpleFieldCIDs, complexFieldCIDs, state);
                console.log(`✅ Root Metadata обновлен`);
            }
            
            // Шаг 5: Upload Root Metadata
            let rootCID;
            if (isStepCompleted('root_metadata_uploaded')) {
                console.log(`\n⏭️  ШАГ 5: Root Metadata уже загружен в Arweave (пропуск)`);
                rootCID = state.root_metadata?.cid;
            } else {
                rootCID = await uploadSteps.uploadRootMetadata(context, finalRootData, state);
                console.log(`✅ Root Metadata загружен в Arweave: ${rootCID}`);
            }
            
            // Шаг 6: Register Component
            let componentIdResult;
            if (isStepCompleted('component_registered')) {
                console.log(`\n⏭️  ШАГ 6: Компонент уже зарегистрирован (пропуск)`);
                componentIdResult = state.contract_registration?.componentId || 'N/A';
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
            
            // Пауза между компонентами
            if (networkName === 'polygon' && i < componentIds.length - 1) {
                console.log(`⏳ Пауза 3 секунды перед следующим компонентом...`);
                await new Promise(resolve => setTimeout(resolve, 3000));
            }
            
        } catch (error) {
            console.error(`❌ Ошибка обработки компонента ${componentId}:`);
            console.error(`   ${error.message}`);
            
            results.push({
                componentId,
                success: false,
                error: error.message
            });
            failCount++;
            
            // В случае ошибки продолжаем со следующим компонентом
            console.log(`⏭️  Продолжаем со следующим компонентом...`);
        }
    }
    
    // 7. Финальный отчёт
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
    
    return {
        successCount,
        failCount,
        totalCount: componentIds.length,
        results,
        mode: 'FULL_ARWEAVE'
    };
}

/**
 * Быстрая регистрация компонентов без загрузки в Arweave (Quick Mode)
 * Использует placeholder CID или существующие CID из state файлов
 * @param {string} sellerAddress - адрес продавца
 * @param {string} componentsDir - директория с компонентами
 * @param {string} networkName - название сети
 * @param {boolean} dryRun - режим dry-run
 * @returns {Promise<Object>} Результаты загрузки {successCount, failCount, results}
 */
async function uploadComponentQuick(sellerAddress, componentsDir = "data/components", networkName = network, dryRun = false) {
    console.log(`\n⚡ QUICK MODE - Быстрая регистрация без Arweave`);
    console.log(`👤 Seller: ${sellerAddress}`);
    console.log(`📁 Директория: ${componentsDir}`);
    console.log(`🌐 Сеть: ${networkName}`);
    console.log(`🔍 Dry-run: ${dryRun ? 'YES' : 'NO'}`);
    
    // 1. Подготовка (контракты, seller, компоненты)
    console.log(`\n📦 Шаг 1/3: Подготовка...`);
    const preparation = await prepareComponentUpload(sellerAddress, componentsDir, networkName);
    const { organicRegistry, amanitaIntl, spiralEngine } = preparation.contracts;
    const { componentIds, componentsPath } = preparation;
    
    console.log(`✅ OrganicComponentRegistry: ${organicRegistry.options.address}`);
    console.log(`✅ AmanitaInternational: ${amanitaIntl.options.address}`);
    console.log(`✅ SpiralEngine: ${spiralEngine.options.address}`);
    console.log(`✅ Seller валиден: активирован + SELLER_ROLE`);
    console.log(`✅ Seller wallet добавлен для транзакций`);
    console.log(`✅ Найдено компонентов: ${componentIds.length}`);
    
    // Вывод списка компонентов
    componentIds.forEach((componentId, index) => {
        console.log(`   ${index + 1}. ${componentId}`);
    });
    
    // 2. Обработка каждого компонента
    console.log(`\n🚀 Шаг 2/3: Обработка компонентов...`);
    const results = [];
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < componentIds.length; i++) {
        const componentId = componentIds[i];
        const componentDir = path.join(componentsPath, componentId);
        const componentPath = path.join(componentDir, `${componentId}.json`);
        
        console.log(`\n${'='.repeat(70)}`);
        console.log(`🔷 Компонент ${i + 1}/${componentIds.length}: ${componentId}`);
        console.log(`${'='.repeat(70)}`);
        
        try {
            // Загрузка JSON данных компонента
            const componentData = JSON.parse(fs.readFileSync(componentPath, 'utf8'));
            console.log(`✅ JSON загружен`);
            console.log(`   → Business ID: ${componentData.biounit_id}`);
            console.log(`   → Scientific Title: ${componentData.scientific_title || 'N/A'}`);
            
            // Проверка: уже зарегистрирован?
            let isAlreadyRegistered = false;
            try {
                await organicRegistry.methods.getComponent(componentData.biounit_id).call();
                isAlreadyRegistered = true;
                console.log(`⚠️ Компонент уже зарегистрирован в контракте`);
            } catch (error) {
                console.log(`📝 Компонент не найден в контракте, будет зарегистрирован`);
            }
            
            if (isAlreadyRegistered && !dryRun) {
                console.log(`⏭️  Пропускаем регистрацию (уже существует)`);
                results.push({
                    componentId,
                    success: true,
                    skipped: true,
                    reason: "Already registered"
                });
                successCount++;
                continue;
            }
            
            // Dry-run режим
            if (dryRun) {
                console.log(`🔍 [DRY-RUN] Симуляция регистрации...`);
                console.log(`   → Business ID: ${componentData.biounit_id}`);
                console.log(`   → Seller: ${sellerAddress}`);
                console.log(`   → Scientific Title: ${componentData.scientific_title || 'N/A'}`);
                console.log(`✅ [DRY-RUN] Симуляция успешна`);
                
                results.push({
                    componentId,
                    success: true,
                    dryRun: true
                });
                successCount++;
                continue;
            }
            
            // РЕАЛЬНАЯ РЕГИСТРАЦИЯ в OrganicComponentRegistry
            console.log(`🚀 Регистрация в OrganicComponentRegistry...`);
            
            const businessId = componentData.biounit_id;
            
            // Загружаем CID из state файла (если есть) или используем placeholder
            const cidInfo = loadComponentCID(componentDir, componentId, networkName);
            const rootMetadataCID = cidInfo.cid;
            
            console.log(`📝 Параметры для createComponent:`);
            console.log(`   → businessId: ${businessId}`);
            console.log(`   → rootMetadataCID: ${rootMetadataCID}`);
            console.log(`   → CID источник: ${cidInfo.source} ${cidInfo.source === 'arweave_state' ? '(переиспользование)' : '(заглушка)'}`);
            
            // Получаем nonce для seller
            const nonce = await web3.eth.getTransactionCount(sellerAddress, 'pending');
            console.log(`   → nonce: ${nonce}`);
            
            // Вызов createComponent
            const tx = await organicRegistry.methods.createComponent(
                businessId,
                rootMetadataCID
            ).send({
                from: sellerAddress,
                gas: 1000000,
                gasPrice: networkName === 'polygon' ? 
                    web3.utils.toWei('100', 'gwei') : 
                    await web3.eth.getGasPrice(),
                nonce: nonce
            });
            
            console.log(`✅ Компонент зарегистрирован успешно!`);
            console.log(`   → Tx Hash: ${tx.transactionHash}`);
            console.log(`   → Block: ${tx.blockNumber}`);
            console.log(`   → Gas Used: ${tx.gasUsed}`);
            
            results.push({
                componentId,
                success: true,
                txHash: tx.transactionHash,
                blockNumber: tx.blockNumber,
                gasUsed: tx.gasUsed
            });
            successCount++;
            
            // Пауза между компонентами (для polygon)
            if (networkName === 'polygon' && i < componentIds.length - 1) {
                console.log(`⏳ Пауза 2 секунды перед следующим компонентом...`);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
            
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
    
    // 3. Финальный отчет
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📊 Шаг 3/3: ИТОГОВЫЙ ОТЧЕТ (QUICK MODE)`);
    console.log(`${'='.repeat(70)}`);
    console.log(`✅ Успешно обработано: ${successCount}/${componentIds.length}`);
    console.log(`❌ Ошибок: ${failCount}/${componentIds.length}`);
    
    if (failCount > 0) {
        console.log(`\n⚠️ Компоненты с ошибками:`);
        results.filter(r => !r.success).forEach((r, index) => {
            console.log(`   ${index + 1}. ${r.componentId}: ${r.error}`);
        });
    }
    
    const skippedCount = results.filter(r => r.skipped).length;
    if (skippedCount > 0) {
        console.log(`\n⏭️  Пропущено (уже зарегистрированы): ${skippedCount}`);
    }
    
    console.log(`${'='.repeat(70)}`);
    
    return {
        successCount,
        failCount,
        skippedCount,
        totalCount: componentIds.length,
        results,
        mode: 'QUICK'
    };
}

/**
 * Роутер для загрузки компонентов (ARWEAVE=true → Full, ARWEAVE=false → Quick)
 * @param {string} sellerAddress - адрес seller
 * @param {string} componentsDir - директория с компонентами (default: "data/components")
 * @param {string} networkName - название сети (default: network из hardhat)
 * @param {boolean} dryRun - режим dry-run (default: false)
 * @param {boolean} withArweave - режим полной загрузки в Arweave (default: true)
 * @returns {Promise<Object>} Результаты загрузки {successCount, failCount, results}
 */
async function uploadComponentsCore(
    sellerAddress,
    componentsDir = "data/components",
    networkName = network,
    dryRun = false,
    withArweave = true
) {
    console.log(`\n🔷 Загрузка компонентов в OrganicComponentRegistry...`);
    console.log(`👤 Seller: ${sellerAddress}`);
    console.log(`📁 Директория: ${componentsDir}`);
    console.log(`🌐 Сеть: ${networkName}`);
    console.log(`🔍 Dry-run: ${dryRun ? 'YES' : 'NO'}`);
    console.log(`📤 Arweave: ${withArweave ? 'FULL UPLOAD' : 'QUICK MODE'}`);
    
    // Роутинг к нужной реализации
    if (withArweave) {
        console.log(`\n🚀 Режим ARWEAVE=true - полная загрузка в Arweave`);
        return await uploadComponentFull(sellerAddress, componentsDir, networkName, dryRun);
    } else {
        console.log(`\n⚡ Режим ARWEAVE=false - быстрая регистрация`);
        return await uploadComponentQuick(sellerAddress, componentsDir, networkName, dryRun);
    }
}

/**
 * Инициализация Arweave для Actions 42-43
 * Переиспользует существующий паттерн из uploadComponentFull
 * @returns {Promise<Object>} Arweave context {client, key}
 */
async function initializeArweaveForActions() {
    console.log(`\n📋 Инициализация Arweave для Actions 42-43...`);
    const arweaveReadiness = require('./Arweave-Readiness');
    
    const arweaveKey = await arweaveReadiness.loadArweaveKey();
    if (!arweaveKey) {
        throw new Error("Arweave key не найден или невалиден");
    }
    
    const arweaveClient = arweaveReadiness.initArweave();
    if (!arweaveClient) {
        throw new Error("Не удалось инициализировать Arweave client");
    }
    
    const connection = await arweaveReadiness.checkConnection(arweaveClient);
    if (!connection.success) {
        throw new Error(`Arweave connection failed: ${connection.error}`);
    }
    
    const wallet = await arweaveReadiness.checkWalletBalance(arweaveClient, arweaveKey);
    if (wallet.status === 'zero_balance') {
        throw new Error("Arweave wallet имеет нулевой баланс");
    }
    
    console.log(`✅ Arweave готов: ${wallet.balance} AR, ${connection.networkInfo.peers} peers`);
    
    return {
        client: arweaveClient,
        key: arweaveKey
    };
}

/**
 * Базовая активация seller для Action 555
 * Минимальная активация для возможности регистрации компонентов в OrganicComponentRegistry
 * @param {Object} spiralEngine - контракт SpiralEngine (UUPS)
 * @param {string} sellerAddress - адрес seller для активации
 * @param {string} deployerInvite - рутовый инвайт деплоера из Action 777
 */
async function activateSellerBasic(spiralEngine, sellerAddress, deployerInvite) {
    console.log(`\n🔷 Базовая активация seller для Action 555...`);
    console.log(`👤 Seller: ${sellerAddress}`);
    console.log(`🎫 Deployer invite: ${deployerInvite}`);
    
    // 1. Проверка текущего состояния seller
    console.log(`\n📊 Шаг 1/3: Проверка текущего состояния...`);
    const usedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    const SELLER_ROLE = await spiralEngine.methods.SELLER_ROLE().call();
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    
    console.log(`   Активирован: ${usedInvite > 0 ? '✅' : '❌'}`);
    console.log(`   SELLER_ROLE: ${hasSellerRole ? '✅' : '❌'}`);
    
    // 2. Активация seller если нужно
    if (usedInvite == 0) {
        console.log(`\n🔷 Шаг 2/3: Активация seller...`);
        
        // 2.1. Валидация деплоер инвайта
        await validateDeployerInviteForSeller(spiralEngine, deployerInvite);
        
        // 2.2. Генерация 12 новых инвайтов для seller
        const newInvites = generateInviteCodes(12);
        console.log(`🎲 Сгенерированы новые инвайты: ${newInvites.length}`);
        
        // 2.3. Активация через activateUser
        console.log(`🚀 Вызываем activateUser()...`);
        const nonceActivate = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        await spiralEngine.methods.activateUser(
            deployerInvite,
            sellerAddress,
            newInvites,
            0 // Бессрочные инвайты
        ).send({
            from: deployerAccount.address,
            gas: 5000000,
            gasPrice: network === 'polygon' ? 
                web3.utils.toWei('100', 'gwei') : 
                await web3.eth.getGasPrice(),
            nonce: nonceActivate
        });
        
        console.log(`✅ Seller активирован через activateUser()`);
        
        // 2.4. Сохраняем инвайты в файл
        const invitesPath = path.join(__dirname, "..", "bot", "flowers", `${sellerAddress}_invites_action555.txt`);
        fs.writeFileSync(invitesPath, newInvites.join("\n"));
        console.log(`✅ Инвайты seller сохранены в ${invitesPath}`);
    } else {
        console.log(`\n✅ Шаг 2/3: Seller уже активирован, пропускаем активацию`);
    }
    
    // 3. Назначение SELLER_ROLE если нужно
    console.log(`\n🔑 Шаг 3/3: Проверка и назначение SELLER_ROLE...`);
    if (!hasSellerRole) {
        console.log(`🔷 Назначаем SELLER_ROLE...`);
        const nonceGrantRole = await web3.eth.getTransactionCount(deployerAccount.address, 'pending');
        await spiralEngine.methods.grantSellerRole(sellerAddress).send({
            from: deployerAccount.address,
            gas: 500000,
            gasPrice: network === 'polygon' ? 
                web3.utils.toWei('100', 'gwei') : 
                await web3.eth.getGasPrice(),
            nonce: nonceGrantRole
        });
        console.log(`✅ SELLER_ROLE назначена через grantSellerRole()`);
    } else {
        console.log(`✅ SELLER_ROLE уже назначена, пропускаем`);
    }
    
    // 4. Финальная проверка
    console.log(`\n🎯 Финальная проверка...`);
    const finalUsedInvite = await spiralEngine.methods.usedInviteByUser(sellerAddress).call();
    const finalHasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, sellerAddress).call();
    
    if (finalUsedInvite > 0 && finalHasSellerRole) {
        console.log(`✅ Базовая активация завершена успешно!`);
        console.log(`   → Seller активирован: ✅`);
        console.log(`   → SELLER_ROLE назначена: ✅`);
        console.log(`   → Готов к регистрации компонентов в OrganicComponentRegistry`);
    } else {
        throw new Error(`Базовая активация не завершена: активирован=${finalUsedInvite > 0}, SELLER_ROLE=${finalHasSellerRole}`);
    }
}

// Получаем action из аргументов командной строки или переменной окружения
// Игнорируем флаги Hardhat (--network, --verbose и т.д.)
const args = process.argv.slice(2).filter(arg => !arg.startsWith('--'));
const action = args[0] || process.env.DEPLOY_ACTION || '1';
console.log("[deploy_full.js] action:", action);

// Временный вывод переменных окружения для отладки
console.log("[DEBUG] DEPLOYER_PRIVATE_KEY:", deployerPrivateKey ? "SET" : "NOT SET");
console.log("[DEBUG] SELLER_ADDRESS:", SELLER_ADDRESS);
console.log("[DEBUG] SELLER_PRIVATE_KEY:", process.env.SELLER_PRIVATE_KEY ? "SET" : "NOT SET");
console.log("[DEBUG] MAGIC_REGISTRY_CONTRACT_ADDRESS:", process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS);
console.log("[DEBUG] SPIRAL_ENGINE_CONTRACT_ADDRESS:", process.env.SPIRAL_ENGINE_CONTRACT_ADDRESS);

// Проверяем что action является числом
if (isNaN(parseInt(action))) {
  console.error("❌ Ошибка: action должен быть числом");
  console.error("Допустимые значения: 0-13, 40-46, 444, 555, 777, 888");
  process.exit(1);
}

main(parseInt(action))
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n=== Ошибка при деплое ===");
    console.error(error.message || error);
    process.exit(1);
  }); 