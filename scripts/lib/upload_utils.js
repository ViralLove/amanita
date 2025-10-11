/**
 * 🛠️ Upload Utilities Module
 * 
 * Переиспользуемые утилиты для загрузки органических компонентов
 * Извлечены из upload_organic_component.js для batch processing
 * 
 * @version 1.0.0
 * @date 2025-10-09
 */

const fs = require('fs');
const path = require('path');

// ====================================================================
// 📄 FILE OPERATIONS
// ====================================================================

/**
 * Чтение JSON файла
 * @param {string} componentDir - Директория компонента
 * @param {string} filepath - Относительный путь к файлу
 * @returns {Object} Parsed JSON
 */
function readJSON(componentDir, filepath) {
  const fullPath = path.join(componentDir, filepath);
  
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Файл не найден: ${fullPath}`);
  }
  
  const content = fs.readFileSync(fullPath, 'utf8');
  return JSON.parse(content);
}

/**
 * Сохранение JSON файла
 * @param {string} componentDir - Директория компонента
 * @param {string} filepath - Относительный путь к файлу
 * @param {Object} data - Данные для сохранения
 */
function saveJSON(componentDir, filepath, data) {
  const fullPath = path.join(componentDir, filepath);
  
  // Создать директорию если не существует
  const dir = path.dirname(fullPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  
  fs.writeFileSync(fullPath, JSON.stringify(data, null, 2), 'utf8');
  console.log(`💾 Сохранено: ${filepath}`);
}

/**
 * Проверка существования файла
 * @param {string} componentDir - Директория компонента
 * @param {string} filepath - Относительный путь к файлу
 * @returns {boolean} true если файл существует
 */
function fileExists(componentDir, filepath) {
  const fullPath = path.join(componentDir, filepath);
  return fs.existsSync(fullPath);
}

/**
 * Получить размер файла в байтах
 * @param {string} componentDir - Директория компонента
 * @param {string} filepath - Относительный путь к файлу
 * @returns {number} Размер в байтах
 */
function getFileSize(componentDir, filepath) {
  const fullPath = path.join(componentDir, filepath);
  
  if (!fs.existsSync(fullPath)) {
    return 0;
  }
  
  return fs.statSync(fullPath).size;
}

// ====================================================================
// 📦 CONTRACT UTILITIES
// ====================================================================

/**
 * Загрузка артефакта контракта
 * @param {string} contractName - Название контракта
 * @returns {Object} Артефакт контракта с ABI
 */
async function loadContractArtifact(contractName) {
  const artifactPath = path.join(
    __dirname,
    '..',
    '..',
    'artifacts',
    'contracts',
    `${contractName}.sol`,
    `${contractName}.json`
  );
  
  if (!fs.existsSync(artifactPath)) {
    throw new Error(
      `Contract artifact not found for ${contractName}. ` +
      `Please compile the contract first: npx hardhat compile`
    );
  }
  
  const content = fs.readFileSync(artifactPath, 'utf8');
  return JSON.parse(content);
}

/**
 * Загрузка UUPS контракта (Logic ABI + Proxy address)
 * @param {string} contractName - Название контракта (без суффикса Logic)
 * @param {string} proxyAddress - Адрес Proxy контракта
 * @param {Object} web3 - Web3 instance
 * @returns {Object} Web3 Contract instance
 */
async function loadUUPSContract(contractName, proxyAddress, web3) {
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

// ====================================================================
// ⛽ GAS UTILITIES
// ====================================================================

/**
 * Получение текущей цены газа с учетом сети
 * @param {Object} web3 - Web3 instance
 * @param {string} network - Название сети (polygon, mumbai, etc.)
 * @returns {Promise<string>} Gas price в Wei
 */
async function getGasPrice(web3, network) {
  if (network === 'polygon') {
    // Фиксированная цена для Polygon mainnet
    return web3.utils.toWei('100', 'gwei');
  }
  
  // Для остальных сетей получаем текущую цену
  return await web3.eth.getGasPrice();
}

/**
 * Получение лимита газа с учетом сети
 * @param {string} network - Название сети
 * @param {number} defaultGas - Дефолтный лимит
 * @returns {number} Gas limit
 */
function getGasLimit(network, defaultGas = 500000) {
  if (network === 'polygon') {
    // Высокий лимит для Polygon mainnet
    return 30000000;
  }
  
  return defaultGas;
}

/**
 * Расчет стоимости транзакции в MATIC
 * @param {number} gasUsed - Использованный газ
 * @param {string} gasPriceWei - Цена газа в Wei
 * @param {Object} web3 - Web3 instance
 * @returns {string} Стоимость в MATIC (formatted)
 */
function calculateCostMatic(gasUsed, gasPriceWei, web3) {
  const costWei = web3.utils.toBN(gasUsed).mul(web3.utils.toBN(gasPriceWei));
  return web3.utils.fromWei(costWei, 'ether');
}

/**
 * Расчет стоимости в USD (примерная оценка)
 * @param {string} costMatic - Стоимость в MATIC
 * @param {number} maticPriceUsd - Цена MATIC в USD (по умолчанию 0.70)
 * @returns {string} Стоимость в USD (formatted)
 */
function calculateCostUsd(costMatic, maticPriceUsd = 0.70) {
  const cost = parseFloat(costMatic) * maticPriceUsd;
  return cost.toFixed(3);
}

// ====================================================================
// 🔐 ACCOUNT UTILITIES
// ====================================================================

/**
 * Инициализация deployer account
 * @param {Object} web3 - Web3 instance
 * @param {string} privateKey - Private key (с или без 0x префикса)
 * @returns {Object} Deployer account
 */
function initializeDeployer(web3, privateKey) {
  // Нормализация private key
  const normalizedKey = privateKey.startsWith('0x') 
    ? privateKey 
    : `0x${privateKey}`;
  
  const account = web3.eth.accounts.privateKeyToAccount(normalizedKey);
  web3.eth.accounts.wallet.add(account);
  
  console.log(`👤 Deployer address: ${account.address}`);
  
  return account;
}

/**
 * Проверка баланса аккаунта
 * @param {Object} web3 - Web3 instance
 * @param {string} address - Адрес аккаунта
 * @param {string} network - Название сети
 * @returns {Promise<Object>} { balance, balanceEth, currency }
 */
async function checkBalance(web3, address, network) {
  const balance = await web3.eth.getBalance(address);
  const balanceEth = web3.utils.fromWei(balance, 'ether');
  const currency = network === 'polygon' ? 'MATIC' : 'ETH';
  
  console.log(`💰 Баланс ${address}: ${balanceEth} ${currency}`);
  
  return {
    balance,
    balanceEth,
    currency,
    isZero: parseFloat(balanceEth) === 0
  };
}

// ====================================================================
// 📊 DATA UTILITIES
// ====================================================================

/**
 * Получить список поддерживаемых языков
 * @returns {Array<string>} Список языков
 */
function getSupportedLanguages() {
  return ["ru", "et", "en", "es", "fr", "de", "nl"];
}

/**
 * Валидация componentId
 * @param {string} componentId - ID компонента
 * @returns {boolean} true если валиден
 */
function isValidComponentId(componentId) {
  // Должен быть snake_case, только буквы и подчеркивания
  const regex = /^[a-z][a-z_]*[a-z]$/;
  return regex.test(componentId);
}

/**
 * Получить путь к директории компонента
 * @param {string} componentsDir - Базовая директория компонентов
 * @param {string} componentId - ID компонента
 * @returns {string} Полный путь к директории
 */
function getComponentDir(componentsDir, componentId) {
  return path.join(componentsDir, componentId);
}

/**
 * Проверить существование директории компонента
 * @param {string} componentDir - Директория компонента
 * @returns {boolean} true если существует
 */
function componentDirExists(componentDir) {
  return fs.existsSync(componentDir) && fs.statSync(componentDir).isDirectory();
}

/**
 * Создать директорию если не существует
 * @param {string} dir - Путь к директории
 */
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`📁 Создана директория: ${dir}`);
  }
}

// ====================================================================
// ⏱️ TIME UTILITIES
// ====================================================================

/**
 * Расчет длительности в секундах
 * @param {string} startedAt - ISO timestamp начала
 * @param {string} completedAt - ISO timestamp окончания (опционально)
 * @returns {number} Длительность в секундах
 */
function calculateDuration(startedAt, completedAt = null) {
  const start = new Date(startedAt);
  const end = completedAt ? new Date(completedAt) : new Date();
  return Math.round((end - start) / 1000);
}

/**
 * Форматирование длительности для вывода
 * @param {number} seconds - Длительность в секундах
 * @returns {string} Formatted duration (e.g. "2m 30s")
 */
function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  
  if (mins === 0) {
    return `${secs}s`;
  }
  
  return `${mins}m ${secs}s`;
}

/**
 * Задержка выполнения
 * @param {number} ms - Миллисекунды
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ====================================================================
// 📋 LOGGING UTILITIES
// ====================================================================

/**
 * Логирование начала операции
 * @param {string} operation - Название операции
 * @param {Object} context - Контекст (componentId, network, etc.)
 */
function logOperationStart(operation, context = {}) {
  console.log(`\n${"=".repeat(60)}`);
  console.log(`🚀 ${operation}`);
  
  if (context.componentId) {
    console.log(`   → Component: ${context.componentId}`);
  }
  if (context.network) {
    console.log(`   → Network: ${context.network}`);
  }
  if (context.dryRun) {
    console.log(`   → Mode: DRY-RUN`);
  }
  
  console.log(`${"=".repeat(60)}`);
}

/**
 * Логирование завершения операции
 * @param {string} operation - Название операции
 * @param {boolean} success - Успех или ошибка
 * @param {Object} details - Детали (duration, etc.)
 */
function logOperationEnd(operation, success, details = {}) {
  const icon = success ? '✅' : '❌';
  const status = success ? 'УСПЕШНО' : 'ОШИБКА';
  
  console.log(`\n${icon} ${operation}: ${status}`);
  
  if (details.duration) {
    console.log(`   ⏱️ Длительность: ${formatDuration(details.duration)}`);
  }
  if (details.message) {
    console.log(`   📝 ${details.message}`);
  }
}

/**
 * Логирование прогресса
 * @param {string} step - Название шага
 * @param {number} current - Текущий
 * @param {number} total - Всего
 */
function logProgress(step, current, total) {
  const percentage = Math.round((current / total) * 100);
  console.log(`📊 ${step}: ${current}/${total} (${percentage}%)`);
}

// ====================================================================
// 🔍 VALIDATION UTILITIES
// ====================================================================

/**
 * Валидация обязательных environment variables
 * @param {Array<string>} required - Список обязательных переменных
 * @throws {Error} Если переменная не найдена
 */
function validateEnvVars(required) {
  const missing = [];
  
  for (const varName of required) {
    if (!process.env[varName]) {
      missing.push(varName);
    }
  }
  
  if (missing.length > 0) {
    throw new Error(
      `Отсутствуют обязательные environment variables: ${missing.join(', ')}\n` +
      `Проверьте файл .env`
    );
  }
}

/**
 * Валидация contract addresses
 * @param {Object} addresses - Объект с адресами контрактов
 * @throws {Error} Если адрес не валиден
 */
function validateContractAddresses(addresses) {
  const web3 = require('web3');
  
  for (const [name, address] of Object.entries(addresses)) {
    if (!address) {
      throw new Error(`Contract address not set: ${name}`);
    }
    
    if (!web3.utils.isAddress(address)) {
      throw new Error(`Invalid contract address for ${name}: ${address}`);
    }
  }
}

// ====================================================================
// 🎯 EXPORTS
// ====================================================================

module.exports = {
  // File operations
  readJSON,
  saveJSON,
  fileExists,
  getFileSize,
  ensureDir,
  
  // Contract utilities
  loadContractArtifact,
  loadUUPSContract,
  
  // Gas utilities
  getGasPrice,
  getGasLimit,
  calculateCostMatic,
  calculateCostUsd,
  
  // Account utilities
  initializeDeployer,
  checkBalance,
  
  // Data utilities
  getSupportedLanguages,
  isValidComponentId,
  getComponentDir,
  componentDirExists,
  
  // Time utilities
  calculateDuration,
  formatDuration,
  sleep,
  
  // Logging utilities
  logOperationStart,
  logOperationEnd,
  logProgress,
  
  // Validation utilities
  validateEnvVars,
  validateContractAddresses
};

