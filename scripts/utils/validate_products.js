#!/usr/bin/env node

/**
 * ✅ Product Validation Script
 * 
 * Валидация product JSON файлов
 * 
 * Usage:
 * node scripts/utils/validate_products.js --products-dir data/sellers/iveta/products/
 * 
 * @version 1.0.0
 * @date 2025-01-12
 */

const fs = require('fs');
const path = require('path');
const { program } = require('commander');

const productUtils = require('./lib/product_utils');
const formMapper = require('./lib/form_mapper');

// ====================================================================
// 🔧 CLI CONFIGURATION
// ====================================================================

program
  .name('validate_products')
  .description('Validate product JSON files')
  .version('1.0.0')
  .requiredOption('--products-dir <path>', 'Directory with product subdirectories')
  .parse(process.argv);

const options = program.opts();
const PRODUCTS_DIR = path.resolve(options.productsDir);

console.log("✅ Product Validation");
console.log("=".repeat(70));
console.log(`📂 Products Directory: ${PRODUCTS_DIR}`);
console.log("=".repeat(70));

// ====================================================================
// 📊 VALIDATION STATS
// ====================================================================

const stats = {
  total_products: 0,
  valid_products: 0,
  products_with_warnings: 0,
  products_with_errors: 0,
  validation_results: []
};

// ====================================================================
// 🔍 VALIDATION FUNCTIONS
// ====================================================================

/**
 * Валидация structure продукта
 */
function validateStructure(productData, productId) {
  const errors = [];
  const warnings = [];
  
  // Обязательные поля
  const requiredFields = [
    'product_id',
    'seller_id',
    'created_at',
    'created_by',
    'title',
    'components',
    'forms',
    'prices',
    'images',
    'metadata'
  ];
  
  for (const field of requiredFields) {
    if (!productData[field]) {
      errors.push(`Missing required field: ${field}`);
    }
  }
  
  // Валидация title локализаций
  if (productData.title) {
    const requiredLangs = ['en', 'ru', 'de', 'es', 'fr', 'nl', 'et'];
    for (const lang of requiredLangs) {
      if (!productData.title[lang]) {
        warnings.push(`Missing translation: title.${lang}`);
      }
    }
  }
  
  // Валидация components
  if (productData.components) {
    if (!Array.isArray(productData.components)) {
      errors.push('components must be an array');
    } else if (productData.components.length === 0) {
      errors.push('components array is empty');
    } else {
      productData.components.forEach((comp, idx) => {
        if (!comp.biounit_id) {
          errors.push(`components[${idx}]: missing biounit_id`);
        }
        if (!comp.form) {
          errors.push(`components[${idx}]: missing form`);
        }
        if (!comp.proportion) {
          warnings.push(`components[${idx}]: missing proportion`);
        }
      });
    }
  }
  
  // Валидация forms
  if (productData.forms) {
    if (!Array.isArray(productData.forms)) {
      errors.push('forms must be an array');
    } else if (productData.forms.length === 0) {
      warnings.push('forms array is empty');
    }
  }
  
  // Валидация prices
  if (productData.prices) {
    if (!Array.isArray(productData.prices)) {
      errors.push('prices must be an array');
    } else if (productData.prices.length === 0) {
      warnings.push('prices array is empty - product has no prices');
    } else {
      productData.prices.forEach((price, idx) => {
        const requiredPriceFields = ['quantity', 'unit', 'price', 'currency'];
        for (const field of requiredPriceFields) {
          if (price[field] === undefined || price[field] === null) {
            errors.push(`prices[${idx}]: missing ${field}`);
          }
        }
      });
    }
  }
  
  // Валидация images
  if (productData.images) {
    if (!productData.images.cover && !productData.images.gallery?.length) {
      warnings.push('No images specified (neither cover nor gallery)');
    }
  }
  
  return { errors, warnings };
}

/**
 * Валидация компонентов
 */
function validateComponents(productData, productId) {
  const errors = [];
  const warnings = [];
  
  if (!productData.components || productData.components.length === 0) {
    return { errors, warnings };
  }
  
  for (const comp of productData.components) {
    const biounit_id = comp.biounit_id;
    
    // Проверка существования компонента
    if (!productUtils.componentExists(biounit_id)) {
      errors.push(`Component not found: ${biounit_id}`);
      continue;
    }
    
    try {
      const component = productUtils.loadComponent(biounit_id);
      
      // Проверка формы компонента
      if (comp.form && component.forms) {
        if (!component.forms.includes(comp.form)) {
          warnings.push(
            `Component ${biounit_id} form mismatch: ` +
            `product uses "${comp.form}", component has [${component.forms.join(', ')}]`
          );
        }
      }
    } catch (error) {
      errors.push(`Error loading component ${biounit_id}: ${error.message}`);
    }
  }
  
  return { errors, warnings };
}

/**
 * Валидация forms
 */
function validateForms(productData, productId) {
  const errors = [];
  const warnings = [];
  
  if (!productData.forms || productData.forms.length === 0) {
    return { errors, warnings };
  }
  
  const standardForms = Object.keys(formMapper.STANDARD_FORMS);
  
  for (const form of productData.forms) {
    if (!standardForms.includes(form)) {
      errors.push(`Unknown form: "${form}" (not in standard dictionary)`);
    }
  }
  
  return { errors, warnings };
}

/**
 * Валидация изображений
 */
function validateImages(productData, productId) {
  const errors = [];
  const warnings = [];
  
  if (!productData.images) {
    return { errors, warnings };
  }
  
  // Проверка cover изображения
  if (productData.images.cover) {
    if (!productUtils.imageExists(productData.images.cover)) {
      warnings.push(`Cover image not found: ${productData.images.cover}`);
    }
  }
  
  // Проверка gallery
  if (productData.images.gallery && Array.isArray(productData.images.gallery)) {
    for (const img of productData.images.gallery) {
      if (img && !productUtils.imageExists(img)) {
        warnings.push(`Gallery image not found: ${img}`);
      }
    }
  }
  
  return { errors, warnings };
}

/**
 * Полная валидация продукта
 */
function validateProduct(productPath, productId) {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`📦 Validating: ${productId}`);
  console.log(`${"=".repeat(70)}`);
  
  const allErrors = [];
  const allWarnings = [];
  
  try {
    // Чтение JSON
    if (!fs.existsSync(productPath)) {
      throw new Error(`Product file not found: ${productPath}`);
    }
    
    const productData = JSON.parse(fs.readFileSync(productPath, 'utf8'));
    
    // Валидация структуры
    console.log("🔍 Validating structure...");
    const structureResult = validateStructure(productData, productId);
    allErrors.push(...structureResult.errors);
    allWarnings.push(...structureResult.warnings);
    
    // Валидация компонентов
    console.log("🔍 Validating components...");
    const componentsResult = validateComponents(productData, productId);
    allErrors.push(...componentsResult.errors);
    allWarnings.push(...componentsResult.warnings);
    
    // Валидация forms
    console.log("🔍 Validating forms...");
    const formsResult = validateForms(productData, productId);
    allErrors.push(...formsResult.errors);
    allWarnings.push(...formsResult.warnings);
    
    // Валидация изображений
    console.log("🔍 Validating images...");
    const imagesResult = validateImages(productData, productId);
    allErrors.push(...imagesResult.errors);
    allWarnings.push(...imagesResult.warnings);
    
    // Результат
    if (allErrors.length === 0 && allWarnings.length === 0) {
      console.log("✅ Product is VALID (no errors, no warnings)");
      stats.valid_products++;
    } else if (allErrors.length === 0) {
      console.log(`⚠️ Product is VALID with ${allWarnings.length} warning(s)`);
      stats.products_with_warnings++;
      stats.valid_products++;
    } else {
      console.log(`❌ Product has ${allErrors.length} error(s), ${allWarnings.length} warning(s)`);
      stats.products_with_errors++;
    }
    
    return {
      product_id: productId,
      status: allErrors.length === 0 ? 'valid' : 'invalid',
      errors: allErrors,
      warnings: allWarnings
    };
    
  } catch (error) {
    console.error(`❌ Validation failed: ${error.message}`);
    stats.products_with_errors++;
    
    return {
      product_id: productId,
      status: 'error',
      errors: [error.message],
      warnings: []
    };
  }
}

// ====================================================================
// 🚀 MAIN EXECUTION
// ====================================================================

async function main() {
  try {
    console.log("\n🔍 Scanning products directory...");
    
    if (!fs.existsSync(PRODUCTS_DIR)) {
      throw new Error(`Products directory not found: ${PRODUCTS_DIR}`);
    }
    
    const entries = fs.readdirSync(PRODUCTS_DIR);
    const productDirs = entries.filter(name => {
      const fullPath = path.join(PRODUCTS_DIR, name);
      return fs.statSync(fullPath).isDirectory() && !name.startsWith('_');
    });
    
    stats.total_products = productDirs.length;
    console.log(`   ✅ Found ${productDirs.length} product directories`);
    
    console.log("\n🔄 Starting validation...");
    
    for (const productId of productDirs) {
      const productPath = path.join(PRODUCTS_DIR, productId, `${productId}.json`);
      const result = validateProduct(productPath, productId);
      stats.validation_results.push(result);
      
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    // Генерация отчета
    console.log("\n" + "=".repeat(70));
    console.log("📊 VALIDATION SUMMARY");
    console.log("=".repeat(70));
    console.log(`Total products: ${stats.total_products}`);
    console.log(`Valid (no warnings): ${stats.valid_products - stats.products_with_warnings}`);
    console.log(`Valid (with warnings): ${stats.products_with_warnings}`);
    console.log(`Invalid (with errors): ${stats.products_with_errors}`);
    
    // Детали по ошибкам
    const invalidProducts = stats.validation_results.filter(r => r.status === 'invalid' || r.status === 'error');
    if (invalidProducts.length > 0) {
      console.log("\n❌ Products with errors:");
      invalidProducts.forEach(p => {
        console.log(`\n   → ${p.product_id}:`);
        p.errors.forEach(err => console.log(`      - ${err}`));
      });
    }
    
    // Детали по warnings
    const productsWithWarnings = stats.validation_results.filter(r => r.warnings.length > 0);
    if (productsWithWarnings.length > 0) {
      console.log("\n⚠️ Products with warnings:");
      productsWithWarnings.forEach(p => {
        console.log(`\n   → ${p.product_id}:`);
        p.warnings.forEach(warn => console.log(`      - ${warn}`));
      });
    }
    
    // Сохранение отчета
    const reportPath = path.join(path.dirname(PRODUCTS_DIR), '_validation_report.json');
    const report = {
      validated_at: new Date().toISOString(),
      products_dir: PRODUCTS_DIR,
      statistics: {
        total_products: stats.total_products,
        valid_products: stats.valid_products,
        products_with_warnings: stats.products_with_warnings,
        products_with_errors: stats.products_with_errors
      },
      results: stats.validation_results
    };
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n💾 Validation report saved: ${reportPath}`);
    
    console.log("=".repeat(70));
    
    process.exit(stats.products_with_errors > 0 ? 1 : 0);
    
  } catch (error) {
    console.error("\n" + "=".repeat(70));
    console.error("❌ VALIDATION FAILED");
    console.error("=".repeat(70));
    console.error(`Error: ${error.message}`);
    console.error(`\nStack trace:\n${error.stack}`);
    console.error("=".repeat(70));
    process.exit(1);
  }
}

// ====================================================================
// 🚀 RUN
// ====================================================================

main();

