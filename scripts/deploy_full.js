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

const sellerPrivateKey = process.env.SELLER_PRIVATE_KEY.startsWith('0x')
  ? process.env.SELLER_PRIVATE_KEY
  : `0x${process.env.SELLER_PRIVATE_KEY}`;

const AMANITA_REGISTRY_CONTRACT_ADDRESS = process.env.AMANITA_REGISTRY_CONTRACT_ADDRESS;
console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS:", AMANITA_REGISTRY_CONTRACT_ADDRESS);

// RPC URL из конфига сети
const RPC_URL = hre.network.config.url;

// Создаем провайдер
const web3 = new Web3(RPC_URL);

// Создаем аккаунты из приватных ключей
const deployerAccount = web3.eth.accounts.privateKeyToAccount(deployerPrivateKey);
web3.eth.accounts.wallet.add(deployerAccount);

const sellerAccount = web3.eth.accounts.privateKeyToAccount(sellerPrivateKey);
web3.eth.accounts.wallet.add(sellerAccount);

// Функция для загрузки артефакта контракта
async function loadContract(contractName, contractAddress = null) {

  if (contractAddress == null) {
    contractAddress = await amanitaRegistry.methods.getAddress(contractName).call();
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
  
  const gasPrice = await web3.eth.getGasPrice();
  console.log("Текущая цена газа:", web3.utils.fromWei(gasPrice, 'gwei'), "Gwei");
  
  const instance = await contract.deploy({
    data: artifact.bytecode,
    arguments: constructorArgs
  }).send({
    from: deployerAccount.address,
    gas: options.gas || 5000000,
    gasPrice: gasPrice
  });

  if (amanitaRegistry != null) {
    await amanitaRegistry.methods.setAddress(contractName, instance.options.address).send({
      from: deployerAccount.address,
      gas: 200000
    });
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
 * 4 - деплой только каталога
 */
async function main(action) {

  action=4;
  // Проверка корректности action
  if (action === undefined || action === null) {
    throw new Error("Не указан параметр action. Используйте: node deploy_full.js <action> (0-4)");
  }

  action = parseInt(action);
  if (isNaN(action) || action < 0 || action > 4) {
    throw new Error("Некорректное значение action. Допустимые значения: 0-4");
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

  let inviteNFT, productRegistry;

  try {
    // Деплой или загрузка реестра
    if (action === 0 || action === 1) {
      console.log("\n🔷 Деплоим AmanitaRegistry...");
      amanitaRegistry = await deployContract("AmanitaRegistry");
      console.log("\n⭐️ ВАЖНО! Адрес реестра для .env:");
      console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS=" + amanitaRegistry.options.address);
      console.log("⭐️ Скопируйте этот адрес в bot/.env\n");
    } else {
      console.log("\n🔷 Загружаем AmanitaRegistry...");
      amanitaRegistry = await loadContract("AmanitaRegistry", AMANITA_REGISTRY_CONTRACT_ADDRESS);
      
      console.log("☀️ Адрес реестра:", amanitaRegistry.options.address);
    }

    // Деплой или загрузка основных контрактов
    if (action === 1 || action === 2) {
      // Деплой InviteNFT
      console.log("\n🔷 Деплоим InviteNFT...");
      inviteNFT = await deployContract("InviteNFT");

      // Регистрируем InviteNFT в реестре
      console.log("\n🔷 Регистрируем InviteNFT в реестре...");
      await amanitaRegistry.methods.setAddress("InviteNFT", inviteNFT.options.address).send({
        from: deployerAccount.address,
        gas: 200000
      });
      console.log("✅ InviteNFT успешно зарегистрирован в реестре:", inviteNFT.options.address);

      // Деплой ProductRegistry
      console.log("\n🔷 Деплоим ProductRegistry...");
      productRegistry = await deployContract("ProductRegistry", [inviteNFT.options.address]);

      // Регистрируем ProductRegistry в реестре
      console.log("\n🔷 Регистрируем ProductRegistry в реестре...");
      await amanitaRegistry.methods.setAddress("ProductRegistry", productRegistry.options.address).send({
        from: deployerAccount.address,
        gas: 200000
      });
      console.log("✅ ProductRegistry успешно зарегистрирован в реестре:", productRegistry.options.address);
    
    }
    
    if (action === 3 || action === 4) {

      inviteNFT = await loadContract("InviteNFT");
      console.log("☀️ Адрес InviteNFT:", inviteNFT.options.address);

      productRegistry = await loadContract("ProductRegistry");
      console.log("☀️ Адрес ProductRegistry:", productRegistry.options.address);
      
    }

    // Настройка ролей (только для действий 1, 2, 3)
    if (action === 1 || action === 2 || action === 3 || action === 4) {
      await setupSellerRole(inviteNFT);
    }

    // Генерация инвайтов
    if (action === 3) {
      console.log("\n🔷 Генерируем инвайты...");
      await creatingInvites(inviteNFT);
      console.log("✅ Инвайты сгенерированы и сохранены в bot/flowers/invites.txt");
    }
    
    // Создание каталога
    if (action === 4) {
      console.log("\n🔷 Создаем каталог...");
      await createCatalog(productRegistry);
      console.log("✅ Каталог успешно загружен!");
    }

    // Выводим адреса контрактов только если они были задействованы
    if (action <= 2) {
      console.log("\n⭐️ ВАЖНО! Адреса контрактов для .env:");
      console.log("AMANITA_REGISTRY_CONTRACT_ADDRESS=" + amanitaRegistry.options.address);
      if (inviteNFT) console.log("INVITE_NFT_CONTRACT_ADDRESS=" + inviteNFT.options.address);
      if (productRegistry) console.log("PRODUCT_REGISTRY_CONTRACT_ADDRESS=" + productRegistry.options.address);
    }

  } catch (error) {
    console.error("\n❌ Ошибка при выполнении действия", action + ":");
    console.error(error.message || error);
    throw error;
  }
}

SELLER_ROLE = web3.utils.keccak256("SELLER_ROLE");
// Обновляем функцию setupSellerRole, чтобы она принимала контракт как параметр
async function setupSellerRole(inviteNFT) {
  if (!inviteNFT) {
    throw new Error("InviteNFT контракт не определен");
  }
  let hasSellerRole = false;
  try {
    // Назначаем роль SELLER_ROLE продавцу в InviteNFT
    console.log("\n🔷 Выясняем, имеет ли продавец роль SELLER_ROLE...");
    console.log("SELLER_ROLE:", SELLER_ROLE);
    console.log("sellerAccount.address:", sellerAccount.address);
    console.log("inviteNFT address:", inviteNFT.options.address);
    hasSellerRole = await inviteNFT.methods.hasRole(SELLER_ROLE, sellerAccount.address).call();
    console.log("hasSellerRole:", hasSellerRole);
  } catch (error) {
    console.error("\n❌ Ошибка при выяснении роли SELLER_ROLE:");
    console.error(error.message || error);
    throw error;
  }

  try {
    if (!hasSellerRole) {
      console.log("Продавец не имеет роли SELLER_ROLE, назначаем...");
      await inviteNFT.methods.grantRole(SELLER_ROLE, sellerAccount.address).send({
        from: deployerAccount.address,
        gas: 200000
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

// Обновляем функцию creatingInvites, чтобы она принимала контракт как параметр
async function creatingInvites(inviteNFT) {
  if (!inviteNFT) {
    throw new Error("InviteNFT контракт не определен");
  }
  // Генерируем и минтим инвайты
  console.log("\n🔷 Генерируем инвайты...");
  const invites = [];
  const usedCodes = new Set();

  for (let i = 0; i < 88; i++) {
    let alpha, beta, invite;
    do {
      alpha = generateRandomAlphanumeric(4);
      beta = generateRandomAlphanumeric(4);
      invite = `AMANITA-${alpha}-${beta}`;
    } while (usedCodes.has(invite));
    usedCodes.add(invite);
    invites.push(invite);
    console.log(`Сгенерирован инвайт ${i + 1}/88:`, invite);
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
    
    await inviteNFT.methods.mintInvites(batch, 0).send({
      from: sellerAccount.address,
      gas: 3000000,
      nonce: await web3.eth.getTransactionCount(sellerAccount.address)
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

// Обновляем функцию createCatalog, чтобы она принимала контракт как параметр
async function createCatalog(productRegistry) {
  if (!productRegistry) {
    throw new Error("ProductRegistry контракт не определен");
  }
  // Загружаем АКТИВНЫЙ каталог
  // Загружаем JSON-файл с продуктами
  const productsPath = path.join(__dirname, "..", "bot", "catalog", "product_registry_upload_data.json");
  const productsData = JSON.parse(fs.readFileSync(productsPath, "utf8"));
  console.log(`\n🔷 Загружено ${productsData.length} продуктов из product_registry_upload_data.json`);

  // Добавляем продукты в ProductRegistry
  for (const product of productsData) {
    console.log(`\n➕ Добавляем продукт: ${product.id}`);
    console.log("Product properties:");
    console.log("ipfsCID:", product.ipfsCID);
    console.log("active:", product.active);
    
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

    await productRegistry.methods.createProduct(
      product.ipfsCID,
      product.id
    ).send({
      from: sellerAccount.address,
      gas: 1000000  // Увеличиваем лимит газа
    });
  }

  // Проверяем добавленные продукты
  console.log("\n🔍 Проверяем добавленные продукты...");
  
  // Получаем все продукты продавца через getProductsBySellerFull
  const products = await productRegistry.methods.getProductsBySellerFull().call({
    from: sellerAccount.address
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
    from: sellerAccount.address
  });
  console.log(`\n📊 Текущая версия каталога продавца: ${catalogVersion}`);

  // Дополнительная проверка через getAllActiveProductIds для сравнения
  const activeIds = await productRegistry.methods.getAllActiveProductIds().call();
  console.log(`\n🔍 Проверка через getAllActiveProductIds: найдено ${activeIds.length} активных продуктов`);
  
  if (activeIds.length !== products.length) {
    console.log("⚠️ Внимание! Количество активных продуктов отличается от количества продуктов продавца!");
  }
}

// Получаем action из аргументов командной строки
const action = process.argv[2] || process.env.DEPLOY_ACTION || '1';
console.log("[deploy_full.js] action:", action);

main(action)
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n=== Ошибка при деплое ===");
    console.error(error.message || error);
    process.exit(1);
  }); 