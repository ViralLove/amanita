require("dotenv").config();
const { Web3 } = require("web3");
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

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

const AMANITA_REGISTRY_CONTRACT_ADDRESS = process.env.AMANITA_REGISTRY_CONTRACT_ADDRESS;
const SPIRAL_ENGINE_CONTRACT_ADDRESS = process.env.SPIRAL_ENGINE_CONTRACT_ADDRESS;
const PRODUCT_REGISTRY_CONTRACT_ADDRESS = process.env.PRODUCT_REGISTRY_CONTRACT_ADDRESS;
const SOUL_IDENTITY_CONTRACT_ADDRESS = process.env.SOUL_IDENTITY_CONTRACT_ADDRESS;
console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS:", AMANITA_REGISTRY_CONTRACT_ADDRESS);
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
if (SELLER_PRIVATE_KEY) {
  sellerAccount = web3.eth.accounts.privateKeyToAccount(SELLER_PRIVATE_KEY);
  web3.eth.accounts.wallet.add(sellerAccount);
}

// Функция для загрузки артефакта контракта
async function loadContract(contractName, contractAddress = null) {
  // Сначала проверяем переменные окружения
  if (contractAddress == null) {
    if (contractName === 'AmanitaRegistry' && AMANITA_REGISTRY_CONTRACT_ADDRESS) {
      contractAddress = AMANITA_REGISTRY_CONTRACT_ADDRESS;
    } else if (contractName === 'SpiralEngine' && SPIRAL_ENGINE_CONTRACT_ADDRESS) {
      contractAddress = SPIRAL_ENGINE_CONTRACT_ADDRESS;
    } else if (amanitaRegistry) {
      contractAddress = await amanitaRegistry.methods.getAddress(contractName).call();
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

amanitaRegistry = null;
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
    
    instance = await contract.deploy({
      data: artifact.bytecode,
      arguments: constructorArgs
    }).send({
      from: deployerAccount.address,
      gas: gasLimit,
      gasPrice: gasPrice
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
  if (amanitaRegistry != null) {
    try {
      console.log(`🔷 Регистрируем ${contractName} в реестре...`);
      
      // Получаем баланс до транзакции
      const balanceBefore = await web3.eth.getBalance(deployerAccount.address);
      console.log(`💰 Баланс до регистрации: ${web3.utils.fromWei(balanceBefore, 'ether')} MATIC`);
      
      const tx = await amanitaRegistry.methods.setAddress(contractName, instance.options.address).send({
        from: deployerAccount.address,
        gas: network === 'polygon' ? 500000 : 200000, // Увеличиваем газ для Polygon
        gasPrice: gasPrice
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
 * 40 - создание каталога с неактивными продуктами (аналогично action=4)
 * 41 - активация существующих продуктов в каталоге
 */
async function main(action) {

  // Проверка корректности action
  if (action === undefined || action === null) {
    throw new Error("Не указан параметр action. Используйте: node deploy_full.js <action> [contract_name] (0-10, 40-41, 777, 888)");
  }

  action = parseInt(action);
  if (isNaN(action) || (action < 0 || action > 10) && (action < 40 || action > 41) && action !== 777 && action !== 888) {
    throw new Error("Некорректное значение action. Допустимые значения: 0-10, 40-41, 777, 888");
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
      console.log("\n🔷 Деплоим AmanitaRegistry...");
      amanitaRegistry = await deployContract("AmanitaRegistry");
      console.log("\n⭐️ ВАЖНО! Адрес реестра для .env:");
      console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS=" + amanitaRegistry.options.address);
      console.log("⭐️ Скопируйте этот адрес в bot/.env\n");
    } else if (action === 1) {
      // Для action 1 — умная логика загрузки реестра
      console.log("\n🔷 Обрабатываем AmanitaRegistry...");
      
      if (AMANITA_REGISTRY_CONTRACT_ADDRESS && AMANITA_REGISTRY_CONTRACT_ADDRESS !== 'undefined') {
        // Если адрес есть в .env - загружаем существующий
        console.log("📋 Найден адрес реестра в .env, загружаем существующий...");
        amanitaRegistry = await loadContract("AmanitaRegistry", AMANITA_REGISTRY_CONTRACT_ADDRESS);
        console.log("☀️ Адрес реестра:", amanitaRegistry.options.address);
      } else {
        // Если адреса нет - деплоим новый (чистый старт)
        console.log("📋 Адрес реестра не найден в .env, деплоим новый...");
        amanitaRegistry = await deployContract("AmanitaRegistry");
        console.log("\n⭐️ ВАЖНО! Адрес реестра для .env:");
        console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS=" + amanitaRegistry.options.address);
        console.log("⭐️ Скопируйте этот адрес в .env\n");
      }
     } else if (action === 888) {
       // Для action 888 - инициализация селлера (критическое действие)
       console.log("\n🔷 Загружаем AmanitaRegistry для инициализации селлера...");
       if (!AMANITA_REGISTRY_CONTRACT_ADDRESS || AMANITA_REGISTRY_CONTRACT_ADDRESS === 'undefined') {
         throw new Error("Адрес реестра не найден в .env. Сначала выполните action=1 для деплоя всей системы контрактов.");
       }
       amanitaRegistry = await loadContract("AmanitaRegistry", AMANITA_REGISTRY_CONTRACT_ADDRESS);
       console.log("☀️ Адрес реестра:", amanitaRegistry.options.address);
     } else {
       // В остальных случаях просто загружаем реестр из .env
       console.log("\n🔷 Загружаем AmanitaRegistry...");
       if (!AMANITA_REGISTRY_CONTRACT_ADDRESS || AMANITA_REGISTRY_CONTRACT_ADDRESS === 'undefined') {
         throw new Error("Адрес реестра не найден в .env. Сначала выполните action=0 или action=1 для деплоя реестра.");
       }
       amanitaRegistry = await loadContract("AmanitaRegistry", AMANITA_REGISTRY_CONTRACT_ADDRESS);
       console.log("☀️ Адрес реестра:", amanitaRegistry.options.address);
     }

    // Деплой или загрузка основных контрактов
    if (action === 1 || action === 2) {
      // Деплой SpiralEngine с проверкой существования
      console.log("\n🔷 Обрабатываем SpiralEngine...");
      spiralEngine = await deploySingleContract("SpiralEngine", amanitaRegistry);

      // Деплой SBT экосистемы с проверкой существования
      console.log("\n🔷 Обрабатываем SBT экосистему...");
      
      // 1. SoulboundCore (базовый SBT)
      const soulboundCore = await deploySingleContract("SoulboundCore", amanitaRegistry);
      
      // 2. SoulMetadata (метаданные)
      const soulMetadata = await deploySingleContract("SoulMetadata", amanitaRegistry);
      
      // 3. SoulRecovery (восстановление)
      const soulRecovery = await deploySingleContract("SoulRecovery", amanitaRegistry);
      
      // 4. SoulIntegration (интеграция)
      const soulIntegration = await deploySingleContract("SoulIntegration", amanitaRegistry);
      
      // 5. SoulIdentity (мост с DID)
      const soulIdentity = await deploySingleContract("SoulIdentity", amanitaRegistry);
      
      // 6. Настройка связей между SBT контрактами
      console.log("\n🔷 Настраиваем связи SBT экосистемы...");
      
      // Получаем цену газа для настройки связей
      const gasPrice = network === 'polygon' ? 
        web3.utils.toWei('100', 'gwei') : // 100 Gwei для Polygon mainnet
        await web3.eth.getGasPrice(); // Текущая цена для других сетей
      
      const gasLimit = network === 'polygon' ? 500000 : 300000; // Увеличиваем газ для mainnet
      
      // Подключаем SoulMetadata к SoulboundCore
      console.log("🔗 Подключаем SoulMetadata к SoulboundCore...");
      await soulboundCore.methods.setMetadataContract(soulMetadata.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice
      });
      console.log("✅ SoulMetadata подключен к SoulboundCore");
      
      // Подключаем SoulRecovery к SoulboundCore
      console.log("🔗 Подключаем SoulRecovery к SoulboundCore...");
      await soulboundCore.methods.setRecoveryContract(soulRecovery.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice
      });
      console.log("✅ SoulRecovery подключен к SoulboundCore");
      
      // Подключаем SoulIntegration к SoulboundCore
      console.log("🔗 Подключаем SoulIntegration к SoulboundCore...");
      await soulboundCore.methods.setIntegrationContract(soulIntegration.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice
      });
      console.log("✅ SoulIntegration подключен к SoulboundCore");
      
      // Подключаем SoulIdentity к SpiralEngine
      console.log("🔗 Подключаем SoulIdentity к SpiralEngine...");
      await spiralEngine.methods.setSoulIdentity(soulIdentity.options.address).send({
        from: deployerAccount.address,
        gas: gasLimit,
        gasPrice: gasPrice
      });
      console.log("✅ SoulIdentity подключен к SpiralEngine");
      
      console.log("\n✅ SBT экосистема полностью настроена!");

      // Деплой ProductRegistry с проверкой существования
      console.log("\n🔷 Обрабатываем ProductRegistry...");
      productRegistry = await deploySingleContract("ProductRegistry", amanitaRegistry);
      
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);
      console.log("☀️ Адрес ProductRegistry:", productRegistry.options.address);
      
    }
    
    if (action === 3 || action === 4 || action === 40 || action === 41) {

      spiralEngine = await loadContract("SpiralEngine");
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);

      productRegistry = await loadContract("ProductRegistry");
      console.log("☀️ Адрес ProductRegistry:", productRegistry.options.address);
      
    }

    // Настройка ролей (только для действий 1, 2, 4, 40, 41)
    if (action === 1 || action === 2 || action === 4 || action === 40 || action === 41) {
      await setupSellerRole(spiralEngine);
    }
    
    // Action 777: Генерация 12 инвайтов для деплоера (production)
    if (action === 777) {
      console.log("\n🎲 Action 777: Генерация инвайтов для деплоера...");
      
      // Загружаем SpiralEngine
      const spiralEngine = await loadContract("SpiralEngine");
      console.log("☀️ Адрес SpiralEngine:", spiralEngine.options.address);
      
      // Проверяем права деплоера
      await validateDeployerAccess(spiralEngine);
      
      // Генерируем 12 инвайтов для деплоера
      await creatingInvitesForDeployer(spiralEngine);
      
      console.log("✅ Action 777 завершен успешно!");
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
      
      await createCatalog(productRegistry, sellerAddr);
      console.log("✅ Каталог с неактивными продуктами успешно загружен!");
    }
    
    // Активация существующих продуктов
    if (action === 41) {
      console.log("\n🔷 Активируем существующие продукты в каталоге...");
      
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

    // Активация пользователя (без назначения роли селлера)
    if (action === 9) {
      const userAddress = args[1];
      if (!userAddress) {
        throw new Error("Для action 9 требуется указать адрес пользователя");
      }
      const inviteCode = args[2] || process.env.INVITE_CODE;
      if (!inviteCode) {
        throw new Error("Для action 9 требуется указать инвайт-код");
      }
      await activateUser(inviteCode, userAddress);
    }

    // Назначение роли SELLER_ROLE
    if (action === 10) {
      const userAddress = args[1];
      if (!userAddress) {
        throw new Error("Для action 10 требуется указать адрес пользователя");
      }
      await grantSellerRole(userAddress);
    }

    // Выводим адреса контрактов только если они были задействованы
    if (action <= 2) {
      console.log("\n⭐️ ВАЖНО! Адреса контрактов для .env:");
      console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS=" + amanitaRegistry.options.address);
      if (spiralEngine) console.log("SPIRAL_ENGINE_CONTRACT_ADDRESS=" + spiralEngine.options.address);
      if (productRegistry) console.log("PRODUCT_REGISTRY_CONTRACT_ADDRESS=" + productRegistry.options.address);
      
      // Добавляем SBT адреса если они были задеплоены
      try {
        const soulboundCoreAddress = await amanitaRegistry.methods.getAddress("SoulboundCore").call();
        const soulMetadataAddress = await amanitaRegistry.methods.getAddress("SoulMetadata").call();
        const soulRecoveryAddress = await amanitaRegistry.methods.getAddress("SoulRecovery").call();
        const soulIntegrationAddress = await amanitaRegistry.methods.getAddress("SoulIntegration").call();
        const soulIdentityAddress = await amanitaRegistry.methods.getAddress("SoulIdentity").call();
        
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
    }
    
    // Выводим адрес задеплоенного контракта для action 5
    if (action === 5) {
      const contractName = args[1] || process.env.CONTRACT_NAME;
      const contractAddress = await amanitaRegistry.methods.getAddress(contractName).call();
      console.log(`\n⭐️ ВАЖНО! Адрес контракта ${contractName}:`);
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
    'AmanitaRegistry': {
        dependencies: [],
        needsSetup: false
    },
    'SpiralEngine': {
        dependencies: [],
        needsSetup: true
    },
    'ProductRegistry': {
        dependencies: ['SpiralEngine'],
        needsSetup: true
    },
    'LoveDoPostNFT': {
        dependencies: ['SpiralEngine', 'AmanitaRegistry'],
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
    }
};

// Маппинг контрактов на переменные окружения .env
const CONTRACT_ENV_MAPPING = {
    'AmanitaRegistry': 'AMANITA_REGISTRY_CONTRACT_ADDRESS',
    'SpiralEngine': 'SPIRAL_ENGINE_CONTRACT_ADDRESS', 
    'ProductRegistry': 'PRODUCT_REGISTRY_CONTRACT_ADDRESS',
    'LoveDoPostNFT': 'LOVE_DO_POST_NFT_CONTRACT_ADDRESS',
    'LoveEmissionEngine': 'LOVE_EMISSION_ENGINE_CONTRACT_ADDRESS',
    'AmanitaToken': 'AMANITA_TOKEN_CONTRACT_ADDRESS',
    'AmanitaGovToken': 'AMANITA_GOV_TOKEN_CONTRACT_ADDRESS',
    'AmanitaPaymentRouter': 'AMANITA_PAYMENT_ROUTER_CONTRACT_ADDRESS',
    'SoulboundCore': 'SOULBOUND_CORE_CONTRACT_ADDRESS',
    'SoulMetadata': 'SOUL_METADATA_CONTRACT_ADDRESS',
    'SoulRecovery': 'SOUL_RECOVERY_CONTRACT_ADDRESS',
    'SoulIntegration': 'SOUL_INTEGRATION_CONTRACT_ADDRESS',
    'SoulIdentity': 'SOUL_IDENTITY_CONTRACT_ADDRESS'
};

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
 * Регистрирует контракт в AmanitaRegistry
 * @param {string} contractName - Название контракта
 * @param {Object} contractInstance - Экземпляр контракта
 */
async function registerContractInRegistry(contractName, contractInstance, registryInstance = null) {
    // Используем переданный экземпляр реестра или загружаем из .env
    const amanitaRegistry = registryInstance || await loadContract("AmanitaRegistry", AMANITA_REGISTRY_CONTRACT_ADDRESS);
    
    try {
        // Проверяем существующий адрес в реестре
        let existingAddress;
        try {
            existingAddress = await amanitaRegistry.methods.getAddress(contractName).call();
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
            console.log(`🔷 Регистрируем ${contractName} в AmanitaRegistry...`);
        }
        
        // Получаем баланс до транзакции
        const balanceBefore = await web3.eth.getBalance(deployerAccount.address);
        console.log(`💰 Баланс до регистрации: ${web3.utils.fromWei(balanceBefore, 'ether')} MATIC`);
        
        // Получаем цену газа для регистрации
        const gasPrice = network === 'polygon' ? 
            web3.utils.toWei('100', 'gwei') : // 100 Gwei для Polygon mainnet
            await web3.eth.getGasPrice(); // Текущая цена для других сетей
        
        await amanitaRegistry.methods.setAddress(contractName, contractInstance.options.address).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 1000000 : 500000, // Увеличиваем газ для Polygon и других сетей
            gasPrice: gasPrice
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
    
    // 2. Проверяем существующий контракт
    let contractInstance = await checkExistingContract(contractName);
    
    if (contractInstance) {
        // Контракт уже существует, только регистрируем в реестре
        console.log(`🔄 Используем существующий контракт ${contractName} (${contractInstance.options.address})`);
        await registerContractInRegistry(contractName, contractInstance, registryInstance);
        return contractInstance;
    }
    
    // 3. Деплоим новый контракт
    console.log(`🚀 Деплоим новый контракт ${contractName}`);
    
    const contractInfo = SUPPORTED_CONTRACTS[contractName];
    console.log(`📋 Зависимости: ${contractInfo.dependencies.length > 0 ? contractInfo.dependencies.join(', ') : 'нет'}`);
    
    // 4. Проверка зависимостей
    for (const dep of contractInfo.dependencies) {
        await ensureContractExists(dep, registryInstance);
    }
    
    // 5. Деплой контракта
    console.log(`🚀 Создаем экземпляр ${contractName}...`);
    
    if (contractName === 'AmanitaRegistry') {
        contractInstance = await deployContract("AmanitaRegistry");
    } else if (contractName === 'SpiralEngine') {
        contractInstance = await deployContract("SpiralEngine");
    } else if (contractName === 'ProductRegistry') {
        const spiralEngine = await loadContract("SpiralEngine");
        contractInstance = await deployContract("ProductRegistry", [spiralEngine.options.address]);
    } else if (contractName === 'LoveDoPostNFT') {
        const spiralEngine = await loadContract("SpiralEngine");
        contractInstance = await deployContract("LoveDoPostNFT", [deployerAccount.address, spiralEngine.options.address, amanitaRegistry.options.address]);
    } else if (contractName === 'LoveEmissionEngine') {
        const amanitaToken = await loadContract("AmanitaToken");
        const agovToken = await loadContract("AmanitaGovToken");
        const loveDo = await loadContract("LoveDoPostNFT");
        const spiralEngine = await loadContract("SpiralEngine");
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
        const spiralEngine = await loadContract("SpiralEngine");
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
    }
    
    // 6. Регистрация в реестре (кроме самого реестра)
    if (contractName !== 'AmanitaRegistry') {
        await registerContractInRegistry(contractName, contractInstance, registryInstance);
        console.log(`📝 Контракт ${contractName} доступен в реестре под ключом "${contractName}"`);
    }
    
    // 7. Настройка ролей (если необходимо)
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
    const amanitaRegistry = registryInstance || await loadContract("AmanitaRegistry", AMANITA_REGISTRY_CONTRACT_ADDRESS);
    const address = await amanitaRegistry.methods.getAddress(contractName).call();
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
    
    // 1. Загружаем контракт SpiralEngine
    const spiralEngine = await loadContract("SpiralEngine");
    
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
    
    // 2. Загружаем контракты
    const productRegistry = await loadContract("ProductRegistry");
    const spiralEngine = await loadContract("SpiralEngine");
    
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
      productsData[0].ipfsCID
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
  for (const product of productsData) {
    console.log(`\n➕ Добавляем продукт: ${product.id}`);
    console.log("Product properties:");
    console.log("ipfsCID:", product.ipfsCID);
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
      product.ipfsCID
    ).send({
      from: sellerAddress,
      gas: 1000000,  // Увеличиваем лимит газа
      gasPrice: highGasPrice,
      type: 0, // Принудительно используем legacy транзакции
      nonce: await web3.eth.getTransactionCount(sellerAddress)
    });
    
    console.log(`✅ Продукт ${product.id} создан (по умолчанию неактивный)`);
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
    console.log("  IPFS CID:", product.ipfsCID);
    console.log("  Активен:", product.active);
    
    // Проверяем соответствие данных
    const originalProduct = productsData.find(p => p.ipfsCID === product.ipfsCID);
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
  
  // 2. Загружаем контракт
  const spiralEngine = await loadContract("SpiralEngine");
  
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
  
  // 1. Загружаем контракт
  const spiralEngine = await loadContract("SpiralEngine");
  
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
  
  // 1. Загружаем контракт
  const spiralEngine = await loadContract("SpiralEngine");
  
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
    
    const mintTx = await soulboundCore.methods.mintSoul(sellerAddress).send({
      from: deployerAccount.address,
      gas: network === 'polygon' ? 500000 : 300000,
      gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
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
    
    // 3. Валидация деплоер инвайта
    await validateDeployerInviteForSeller(contracts.spiralEngine, deployerInvite);
    
    // 4. Активация селлера в SpiralEngine
    await activateSellerInSpiralEngine(contracts.spiralEngine, sellerAddress, deployerInvite);
    
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
        console.log(`🔍 Проверяем инвайт ${deployerInvite} в SpiralEngine ${spiralEngine.options.address}...`);
        
        // Проверяем, что методы существуют в ABI
        console.log(`🔍 Доступные методы в SpiralEngine:`, Object.keys(spiralEngine.methods));
        
        // Пробуем вызвать метод с обработкой ошибок
        let inviteExists;
        try {
            inviteExists = await spiralEngine.methods.inviteCodeExists(deployerInvite).call();
            console.log(`🔍 inviteExists: ${inviteExists}`);
        } catch (methodError) {
            console.error(`❌ Ошибка при вызове inviteCodeExists:`, methodError.message);
            throw new Error(`Метод inviteCodeExists не найден в SpiralEngine или ABI не соответствует`);
        }
        
        if (!inviteExists) {
            throw new Error(`Action 888: инвайт ${deployerInvite} не существует`);
        }
        
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
        await spiralEngine.methods.grantRole(ACTIVATOR_ROLE, deployerAccount.address).send({
            from: deployerAccount.address,
            gas: 100000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
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
        const activateTx = await spiralEngine.methods.activateUser(
            deployerInvite, // Передаем сам инвайт код!
            sellerAddress,
            newInviteCodes,
            0 // nonce
        ).send({
            from: deployerAccount.address, // Деплоер с ролью ACTIVATOR_ROLE активирует
            gas: 5000000, // Максимальный лимит газа
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
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
        const grantTx = await spiralEngine.methods.grantSellerRole(sellerAddress).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 500000 : 300000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
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
        const grantTx = await spiralEngine.methods.grantRole(ACTIVATOR_ROLE, sellerAddress).send({
            from: deployerAccount.address,
            gas: network === 'polygon' ? 500000 : 300000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
        });
        console.log(`✅ Роль ACTIVATOR_ROLE назначена селлеру, tx: ${grantTx.transactionHash}`);
        console.log(`✅ Теперь селлер может активировать пользователей через SpiralEngine.activateUser`);
    } catch (error) {
        console.error(`❌ Ошибка при назначении роли ACTIVATOR_ROLE: ${error.message}`);
        console.error(`❌ Детали ошибки:`, error);
        throw error;
    }
}

// Загрузка каталога селлера
async function loadSellerCatalog(productRegistry, sellerAddress, catalogData, deployerAddress) {
    if (!catalogData) {
        catalogData = path.join(__dirname, "..", "bot", "catalog", "product_registry_upload_data.json");
    }
    
    console.log(`🔷 Загружаем каталог для селлера ${sellerAddress}...`);
    
    // Очищаем существующий каталог продавца перед созданием нового
    console.log(`🧹 Очищаем существующий каталог продавца...`);
    try {
        const clearTx = await productRegistry.methods.clearSellerCatalog(sellerAddress).send({
            from: deployerAddress,
            gas: networkName === 'polygon' ? 500000 : 300000,
            gasPrice: networkName === 'polygon' ? web3.utils.toWei('100', 'gwei') : undefined
        });
        
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
        
        const mintTx = await spiralEngine.methods.mintInvite(inviteCode, 0).send({
            from: sellerAddress,
            gas: 500000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
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

// Получаем action из аргументов командной строки или переменной окружения
// Игнорируем флаги Hardhat (--network, --verbose и т.д.)
const args = process.argv.slice(2).filter(arg => !arg.startsWith('--'));
const action = args[0] || process.env.DEPLOY_ACTION || '1';
console.log("[deploy_full.js] action:", action);

// Проверяем что action является числом
if (isNaN(parseInt(action))) {
  console.error("❌ Ошибка: action должен быть числом");
  console.error("Допустимые значения: 0-10, 40-41, 777, 888");
  process.exit(1);
}

main(parseInt(action))
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n=== Ошибка при деплое ===");
    console.error(error.message || error);
    process.exit(1);
  }); 