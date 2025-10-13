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
 * Проверка существования компонента
 * @param {string} biounit_id - ID компонента
 * @returns {boolean} true если компонент существует
 */
function componentExists(biounit_id) {
  const componentDir = path.join(__dirname, '../../data/components', biounit_id);
  const componentFile = path.join(componentDir, `${biounit_id}.json`);
  
  return fs.existsSync(componentFile);
}

/**
 * Загрузка компонента
 * @param {string} biounit_id - ID компонента
 * @returns {Object} JSON объект компонента
 */
function loadComponent(biounit_id) {
  const componentDir = path.join(__dirname, '../../data/components', biounit_id);
  const componentFile = path.join(componentDir, `${biounit_id}.json`);
  
  if (!fs.existsSync(componentFile)) {
    throw new Error(
      `Component not found: ${biounit_id}\n` +
      `Expected location: ${componentFile}\n` +
      `Run: DEPLOY_ACTION=555 node scripts/deploy_full.js 555 to upload components first`
    );
  }
  
  try {
    const componentData = fs.readFileSync(componentFile, 'utf8');
    return JSON.parse(componentData);
  } catch (error) {
    throw new Error(
      `Failed to load component ${biounit_id}: ${error.message}`
    );
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
 * @param {string} seller_id - ID продавца
 * @param {string} product_id - ID продукта
 * @returns {string} Путь к созданной директории
 */
function createProductDirectory(seller_id, product_id) {
  const productDir = path.join(__dirname, '../products', seller_id, product_id);
  
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
 * @returns {boolean} true если изображение существует
 */
function imageExists(imageFile) {
  const imageDir = path.join(__dirname, '../catalog/images');
  const imagePath = path.join(imageDir, imageFile);
  
  return fs.existsSync(imagePath);
}

/**
 * Получение абсолютного пути к изображению
 * @param {string} imageFile - Имя файла изображения
 * @returns {string} Абсолютный путь
 */
function getImagePath(imageFile) {
  const imageDir = path.join(__dirname, '../catalog/images');
  return path.join(imageDir, imageFile);
}

module.exports = {
  parsePrices,
  componentExists,
  loadComponent,
  validateProductId,
  createProductDirectory,
  saveProductJSON,
  imageExists,
  getImagePath
};

