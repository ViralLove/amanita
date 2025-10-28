/**
 * 🛠️ Product Utilities Module
 * 
 * Утилиты для работы с продуктами: валидация, парсинг, сохранение
 * 
 * @module product_utils
 * @version 1.0.0
 * @date 2025-01-12
 */

const fs = require('fs');
const path = require('path');

/**
 * Парсинг поля prices из CSV
 * Формат: "100|g|80|EUR" или "50|ml|15|EUR;100|ml|25|EUR"
 * @param {string} pricesString - Строка с ценами из CSV
 * @returns {Array<Object>} Массив объектов с ценами
 */
function parsePrices(pricesString) {
  if (!pricesString || pricesString.trim() === '') {
    console.warn(`⚠️ Empty prices string`);
    return [];
  }
  
  // Разделение на отдельные цены через ";"
  const priceEntries = pricesString.split(';').map(s => s.trim()).filter(s => s);
  const parsed = [];
  
  for (const entry of priceEntries) {
    const parts = entry.split('|').map(s => s.trim());
    
    if (parts.length !== 4) {
      console.warn(`⚠️ Invalid price format: "${entry}" (expected 4 parts, got ${parts.length})`);
      continue;
    }
    
    const [quantityStr, unit, priceStr, currency] = parts;
    
    const quantity = parseFloat(quantityStr);
    const price = parseFloat(priceStr);
    
    if (isNaN(quantity) || isNaN(price)) {
      console.warn(`⚠️ Invalid numbers in price: "${entry}"`);
      continue;
    }
    
    parsed.push({
      quantity: quantity,
      unit: unit,
      price: price,
      currency: currency,
      active: true
    });
  }
  
  return parsed;
}

/**
 * Получение component_id из контракта OrganicComponentRegistry
 * Использует Ethers.js + MagicRegistry для автоматического resolution
 * Поддерживает fallback на _upload_state файлы для offline scenarios
 * 
 * @param {string} biounit_id - ID компонента (e.g., 'amanita_muscaria')
 * @param {Object} contractManager - ContractManager instance (optional, recommended)
 * @returns {Promise<string|null>} component_id из контракта или null
 */
async function getComponentIdFromContract(biounit_id, contractManager = null) {
  // Source 1: Query OrganicComponentRegistry contract via Ethers.js + MagicRegistry
  if (contractManager) {
    try {
      // ContractManager auto-resolves from MagicRegistry if .env not set ✅
      const registry = await contractManager.loadUUPSContract('OrganicComponentRegistry');
      const componentId = await registry.getComponentId(biounit_id);
      
      // Ethers.js returns BigInt, check if > 0 (contract returns 0 if not found)
      if (componentId > 0 || componentId > 0n) {
        const idStr = componentId.toString();
        console.log(`   → Contract component_id: ${idStr} (from OrganicComponentRegistry)`);
        return idStr;
      }
    } catch (error) {
      console.warn(`⚠️ Contract query failed: ${error.message}`);
    }
  } else {
    console.warn(`⚠️ ContractManager not provided, skipping contract query`);
  }
  
  // Source 2: Fallback to _upload_state file (offline scenario or contract unavailable)
  try {
    const network = process.env.NETWORK || 'localhost';
    const statePath = path.join(__dirname, '../../data/components', biounit_id, `_upload_state_${network}.json`);
    
    if (fs.existsSync(statePath)) {
      const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      if (state.contract_registration && state.contract_registration.componentId) {
        const idStr = state.contract_registration.componentId.toString();
        console.log(`   → Component ID from state file: ${idStr} (fallback source)`);
        return idStr;
      }
    }
  } catch (error) {
    console.warn(`⚠️ State file read failed: ${error.message}`);
  }
  
  // All sources exhausted
  console.warn(`⚠️ Component ${biounit_id} ID not found in contract or state files`);
  return null;
}

/**
 * Проверка существования компонента (файловая система + контракт)
 * @param {string} biounit_id - ID компонента
 * @returns {boolean} true если компонент существует
 */
function componentExists(biounit_id) {
  const componentDir = path.join(__dirname, '../../data/components', biounit_id);
  const componentFile = path.join(componentDir, `${biounit_id}.json`);
  
  return fs.existsSync(componentFile);
}

/**
 * Загрузка компонента с интеграцией контракта
 * Использует multi-source resolution для получения contract_component_id
 * 
 * @param {string} biounit_id - ID компонента (e.g., 'amanita_muscaria')
 * @param {Object} contractManager - ContractManager instance (optional but recommended)
 * @returns {Promise<Object>} JSON объект компонента с contract_component_id
 */
async function loadComponent(biounit_id, contractManager = null) {
  const componentDir = path.join(__dirname, '../../data/components', biounit_id);
  const componentFile = path.join(componentDir, `${biounit_id}.json`);
  
  if (!fs.existsSync(componentFile)) {
    throw new Error(
      `Component not found: ${biounit_id}\n` +
      `Expected location: ${componentFile}\n` +
      `Run: DEPLOY_ACTION=555 npx hardhat run scripts/deploy_full_new.js --network localhost`
    );
  }
  
  try {
    const componentData = JSON.parse(fs.readFileSync(componentFile, 'utf8'));
    
    // Получаем component_id из контракта (с MagicRegistry fallback + state file fallback)
    const contractComponentId = await getComponentIdFromContract(biounit_id, contractManager);
    if (contractComponentId) {
      componentData.contract_component_id = contractComponentId;
    } else {
      console.warn(`   ⚠️ Component ${biounit_id} not found in contract (will use biounit_id only)`);
      componentData.contract_component_id = null;
    }
    
    return componentData;
  } catch (error) {
    throw new Error(`Failed to load component ${biounit_id}: ${error.message}`);
  }
}

/**
 * Валидация product_id (business_id)
 * Правила контракта: a-z, 0-9, _, - (макс 64 символа)
 * @param {string} product_id - ID продукта для валидации
 * @returns {boolean} true если валиден
 * @throws {Error} если не валиден
 */
function validateProductId(product_id) {
  if (!product_id || product_id.trim() === '') {
    throw new Error('Product_id cannot be empty');
  }
  
  // Допустимые символы: a-z, 0-9, _, -
  const pattern = /^[a-z0-9_-]+$/;
  
  if (!pattern.test(product_id)) {
    throw new Error(
      `Invalid product_id: "${product_id}"\n` +
      `Only lowercase letters, numbers, underscore and dash allowed.\n` +
      `Invalid characters found: ${product_id.replace(/[a-z0-9_-]/g, '')}`
    );
  }
  
  if (product_id.length > 64) {
    throw new Error(
      `Product_id too long: ${product_id.length} chars (max 64)\n` +
      `Consider shortening: "${product_id}"`
    );
  }
  
  return true;
}

/**
 * Создание директории продукта
 * @param {string} seller_id - ID продавца (deprecated, for backward compatibility)
 * @param {string} product_id - ID продукта
 * @param {string} outputDir - Output directory path (optional, если не указан - используется старая логика)
 * @returns {string} Путь к созданной директории
 */
function createProductDirectory(seller_id, product_id, outputDir = null) {
  let productDir;
  
  if (outputDir) {
    // NEW: Use provided outputDir (respects OUTPUT_DIR from action444)
    productDir = path.join(outputDir, product_id);
  } else {
    // LEGACY: Old hardcoded path for backward compatibility
    productDir = path.join(process.cwd(), 'data/sellers', seller_id, 'products', product_id);
  }
  
  if (!fs.existsSync(productDir)) {
    fs.mkdirSync(productDir, { recursive: true });
    console.log(`📁 Created directory: ${productDir}`);
  } else {
    console.log(`📁 Directory already exists: ${productDir}`);
  }
  
  return productDir;
}

/**
 * Сохранение product JSON
 * @param {Object} productData - Данные продукта
 * @param {string} productDir - Директория продукта
 * @returns {string} Путь к сохраненному файлу
 */
function saveProductJSON(productData, productDir) {
  const productFile = path.join(productDir, `${productData.product_id}.json`);
  
  try {
    fs.writeFileSync(
      productFile,
      JSON.stringify(productData, null, 2),
      'utf8'
    );
    
    console.log(`💾 Saved product JSON: ${path.basename(productFile)}`);
    
    return productFile;
  } catch (error) {
    throw new Error(
      `Failed to save product JSON: ${error.message}\n` +
      `Path: ${productFile}`
    );
  }
}

/**
 * Проверка существования изображения
 * @param {string} imageFile - Имя файла изображения
 * @param {string} sellerId - Seller business ID (optional, default: 'iveta')
 * @returns {boolean} true если изображение существует
 */
function imageExists(imageFile, sellerId = 'iveta') {
  const imageDir = path.join(__dirname, '../../data/sellers', sellerId, 'catalog/images');
  const imagePath = path.join(imageDir, imageFile);
  
  return fs.existsSync(imagePath);
}

/**
 * Получение абсолютного пути к изображению
 * @param {string} imageFile - Имя файла изображения
 * @param {string} sellerId - Seller business ID (optional, default: 'iveta')
 * @returns {string} Абсолютный путь
 */
function getImagePath(imageFile, sellerId = 'iveta') {
  const imageDir = path.join(__dirname, '../../data/sellers', sellerId, 'catalog/images');
  return path.join(imageDir, imageFile);
}

module.exports = {
  parsePrices,
  componentExists,
  loadComponent,
  getComponentIdFromContract,
  validateProductId,
  createProductDirectory,
  saveProductJSON,
  imageExists,
  getImagePath
};

