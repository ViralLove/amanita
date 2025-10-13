#!/usr/bin/env node

/**
 * 🔄 Product CSV Transformation Script
 * 
 * Трансформация CSV каталога в структурированные JSON продукты
 * 
 * Usage:
 * node scripts/transform_products_csv.js \
 *   --csv data/sellers/iveta/catalog/Iveta_catalog.csv \
 *   --output data/sellers/iveta/products/ \
 *   --seller-id iveta_zeya888
 * 
 * Dry-run:
 * DRY_RUN=true node scripts/transform_products_csv.js --csv ...
 * 
 * @version 1.0.0
 * @date 2025-01-12
 */

const fs = require('fs');
const path = require('path');
const { program } = require('commander');

const csvParser = require('./lib/csv_parser');
const formMapper = require('./lib/form_mapper');
const productUtils = require('./lib/product_utils');

// ====================================================================
// 🔧 CONFIGURATION (для модульного использования и CLI)
// ====================================================================

// Глобальные переменные (будут инициализированы позже)
let DRY_RUN, CSV_PATH, OUTPUT_DIR, SELLER_ID, SELLER_ADDRESS, SOURCE_LANG, CREATE_TRANSLATION_STUBS;

// Supported languages (aligned with upload_utils.js)
const SUPPORTED_LANGUAGES = ["ru", "et", "en", "es", "fr", "de", "nl"];

// ====================================================================
// 📊 STATISTICS TRACKING
// ====================================================================

const stats = {
  total_rows: 0,
  valid_products: 0,
  skipped_products: 0,
  form_mappings: [],
  component_links: new Set(),
  errors: []
};

// ====================================================================
// 🎯 TRANSFORMATION LOGIC
// ====================================================================

/**
 * Создание мультиязычного title объекта
 * @param {string} originalTitle - Оригинальное название из CSV
 * @param {string} sourceLang - Исходный язык
 * @returns {Object} Объект с переводами (исходный язык + заглушки)
 */
function createMultilingualTitle(originalTitle, sourceLang) {
  const title = {};
  
  for (const lang of SUPPORTED_LANGUAGES) {
    if (lang === sourceLang) {
      title[lang] = originalTitle;
    } else {
      title[lang] = `[NEEDS TRANSLATION] ${originalTitle}`;
    }
  }
  
  return title;
}

/**
 * Создание translation stub файла
 * @param {string} productId - ID продукта
 * @param {string} originalTitle - Оригинальное название
 * @param {string} sourceLang - Исходный язык
 * @param {string} productDir - Директория продукта
 */
function createTranslationStub(productId, originalTitle, sourceLang, productDir) {
  const translationsDir = path.join(productDir, 'translations');
  
  if (!fs.existsSync(translationsDir)) {
    fs.mkdirSync(translationsDir, { recursive: true });
  }
  
  const stubData = {
    product_id: productId,
    source_language: sourceLang,
    translations: {},
    created_at: new Date().toISOString(),
    last_updated: new Date().toISOString(),
    translation_notes: "Edit this file to add translations for each language. Remove [NEEDS TRANSLATION] prefix when done."
  };
  
  for (const lang of SUPPORTED_LANGUAGES) {
    if (lang === sourceLang) {
      stubData.translations[lang] = originalTitle;
    } else {
      stubData.translations[lang] = `[NEEDS TRANSLATION] ${originalTitle}`;
    }
  }
  
  const stubPath = path.join(translationsDir, 'title.json');
  fs.writeFileSync(stubPath, JSON.stringify(stubData, null, 2));
  
  return stubPath;
}

/**
 * Создание README для переводчиков
 * @param {string} productId - ID продукта
 * @param {string} productDir - Директория продукта
 */
function createTranslatorReadme(productId, productDir) {
  const readme = `# Инструкция по переводу: ${productId}

## Файл для редактирования
\`translations/title.json\`

## Как переводить
1. Откройте файл \`translations/title.json\`
2. Замените \`[NEEDS TRANSLATION]\` на перевод названия продукта
3. Сохраните файл
4. После завершения всех переводов запустите Action 42 для загрузки в Arweave

## Пример:
\`\`\`json
"en": "Amanita — LUX"  // Было: [NEEDS TRANSLATION] Amanita — LUX
\`\`\`

## Поддерживаемые языки
${SUPPORTED_LANGUAGES.map(lang => `- **${lang}**: ${getLanguageName(lang)}`).join('\n')}

## Важно!
- Сохраняйте форматирование JSON (кавычки, запятые)
- Не изменяйте структуру файла
- Не удаляйте ключи (языковые коды)
- Проверьте правильность перевода перед сохранением
`;

  const readmePath = path.join(productDir, 'README.md');
  fs.writeFileSync(readmePath, readme);
  
  return readmePath;
}

/**
 * Получение полного названия языка
 * @param {string} langCode - Код языка
 * @returns {string} Полное название
 */
function getLanguageName(langCode) {
  const names = {
    'ru': 'Русский',
    'en': 'English',
    'de': 'Deutsch',
    'es': 'Español',
    'fr': 'Français',
    'nl': 'Nederlands',
    'et': 'Eesti'
  };
  return names[langCode] || langCode;
}

/**
 * Трансформация одной строки CSV в product JSON
 */
function transformProduct(row, index) {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`📦 Product ${index + 1}: ${row.product_id}`);
  console.log(`${"=".repeat(70)}`);
  
  try {
    // 1. Валидация product_id
    console.log("🔍 Step 1: Validating product_id...");
    productUtils.validateProductId(row.product_id);
    console.log(`   ✅ Valid product_id: ${row.product_id}`);
    
    // 2. Проверка компонента
    console.log("🔍 Step 2: Validating component...");
    if (!productUtils.componentExists(row.biounit_id)) {
      throw new Error(
        `Component not found: ${row.biounit_id}. ` +
        `Upload component first: node scripts/upload_all_components.js`
      );
    }
    
    const component = productUtils.loadComponent(row.biounit_id);
    console.log(`   ✅ Component found: ${row.biounit_id}`);
    console.log(`      → Forms available: ${component.forms.join(', ')}`);
    
    stats.component_links.add(row.biounit_id);
    
    // 3. Мапинг формы
    console.log("🔍 Step 3: Mapping form...");
    const formMapping = formMapper.mapFormToStandard(row.form, row.biounit_id);
    console.log(`   ✅ Form mapped: "${row.form}" → "${formMapping.standard_form}"`);
    console.log(`      → Confidence: ${(formMapping.confidence * 100).toFixed(0)}%`);
    console.log(`      → Type: ${formMapping.mapping_type}`);
    
    if (formMapping.confidence < 0.8) {
      console.warn(`   ⚠️ Low confidence mapping, manual review recommended`);
    }
    
    stats.form_mappings.push(formMapping);
    
    // 4. Парсинг цен
    console.log("🔍 Step 4: Parsing prices...");
    const prices = productUtils.parsePrices(row.prices);
    console.log(`   ✅ Parsed ${prices.length} price(s):`);
    prices.forEach((p, i) => {
      console.log(`      ${i + 1}. ${p.quantity}${p.unit} = ${p.price} ${p.currency}`);
    });
    
    if (prices.length === 0) {
      console.warn(`   ⚠️ No valid prices found, product may need manual review`);
    }
    
    // 5. Проверка изображения
    console.log("🔍 Step 5: Validating image...");
    if (row.image_file && !productUtils.imageExists(row.image_file)) {
      console.warn(`   ⚠️ Image not found: ${row.image_file}`);
      console.warn(`      Product will be created but image needs to be added manually`);
    } else if (row.image_file) {
      console.log(`   ✅ Image found: ${row.image_file}`);
    } else {
      console.warn(`   ⚠️ No image specified`);
    }
    
    // 6. Создание product JSON
    console.log("🔍 Step 6: Creating product JSON...");
    
    // Создание мультиязычного title
    const title = createMultilingualTitle(row.product_name, SOURCE_LANG);
    console.log(`   → Title created with source language: ${SOURCE_LANG}`);
    console.log(`   → Source title (${SOURCE_LANG}): ${title[SOURCE_LANG]}`);
    console.log(`   → Translation stubs: ${Object.keys(title).filter(k => k !== SOURCE_LANG).join(', ')}`);
    
    const productData = {
      product_id: row.product_id,
      seller_id: SELLER_ID,
      created_at: new Date().toISOString(),
      last_updated: new Date().toISOString(),
      created_by: SELLER_ADDRESS,
      
      title: title,
      
      components: [
        {
          biounit_id: row.biounit_id,
          proportion: "100%",
          form: formMapping.standard_form,
          form_mapping_confidence: formMapping.confidence,
          form_original: formMapping.original_form,
          notes: ""
        }
      ],
      
      forms: [formMapping.standard_form],
      
      prices: prices,
      
      images: {
        cover: row.image_file || null,
        cover_cid: null,  // Will be filled in upload step
        cover_url: null,
        gallery: []
      },
      
      metadata: {
        version: "1.0",
        schema_version: "1.0",
        status: "active",
        visibility: "public",
        transformation: {
          from_csv: CSV_PATH,
          transformed_at: new Date().toISOString(),
          form_mapping_type: formMapping.mapping_type,
          form_mapping_confidence: formMapping.confidence
        }
      },
      
      inventory: {
        stock_quantity: null,
        stock_unit: prices[0]?.unit || "g",
        low_stock_threshold: 500,
        reorder_quantity: 1000
      },
      
      shipping: {
        dimensions: {
          length_cm: null,
          width_cm: null,
          height_cm: null
        },
        weight_g: prices[0]?.quantity || 100,
        handling_time_days: 3
      }
    };
    
    console.log(`   ✅ Product JSON created`);
    
    // 7. Добавление метаданных о переводах
    console.log("🔍 Step 7: Adding translation metadata...");
    productData.metadata.translation_status = {
      source_language: SOURCE_LANG,
      completed: [SOURCE_LANG],
      pending: SUPPORTED_LANGUAGES.filter(lang => lang !== SOURCE_LANG),
      has_stubs: CREATE_TRANSLATION_STUBS
    };
    console.log(`   ✅ Translation metadata added`);
    
    // 8. Сохранение (если не dry-run)
    if (!DRY_RUN) {
      console.log("🔍 Step 8: Saving to file...");
      const productDir = productUtils.createProductDirectory(SELLER_ID, row.product_id);
      const productFile = productUtils.saveProductJSON(productData, productDir);
      console.log(`   ✅ Saved: ${productFile}`);
      
      // 8.1. Создание translation stubs (если флаг установлен)
      if (CREATE_TRANSLATION_STUBS) {
        console.log("🔍 Step 8.1: Creating translation stubs...");
        const stubPath = createTranslationStub(row.product_id, row.product_name, SOURCE_LANG, productDir);
        console.log(`   ✅ Translation stub: ${stubPath}`);
        
        const readmePath = createTranslatorReadme(row.product_id, productDir);
        console.log(`   ✅ README: ${readmePath}`);
      }
    } else {
      console.log("🔷 [DRY-RUN] Skipping file save");
      if (CREATE_TRANSLATION_STUBS) {
        console.log("🔷 [DRY-RUN] Would create translation stubs");
      }
    }
    
    stats.valid_products++;
    console.log(`\n✅ Product ${row.product_id} transformed successfully`);
    
    return { success: true, productData };
    
  } catch (error) {
    console.error(`\n❌ Error transforming ${row.product_id}:`, error.message);
    stats.skipped_products++;
    stats.errors.push({
      product_id: row.product_id,
      error: error.message
    });
    
    return { success: false, error: error.message };
  }
}

// ====================================================================
// 🚀 MAIN EXECUTION
// ====================================================================

async function main() {
  // CLI режим: парсим аргументы с помощью commander
  program
    .name('transform_products_csv')
    .description('Transform CSV catalog to structured product JSONs')
    .version('2.0.0')
    .requiredOption('--csv <path>', 'Path to CSV catalog file')
    .requiredOption('--output <path>', 'Output directory for products')
    .requiredOption('--seller-id <id>', 'Seller identifier')
    .option('--seller-address <address>', 'Seller Ethereum address')
    .option('--source-lang <lang>', 'Source language of product names in CSV', 'en')
    .option('--create-translation-stubs', 'Create translation stub files for manual translation', false)
    .option('--dry-run', 'Validate without creating files')
    .parse(process.argv);

  const options = program.opts();

  // Инициализируем глобальные переменные
  DRY_RUN = options.dryRun || process.env.DRY_RUN === 'true';
  CSV_PATH = path.resolve(options.csv);
  OUTPUT_DIR = path.resolve(options.output);
  SELLER_ID = options.sellerId;
  SELLER_ADDRESS = options.sellerAddress || "0x0000000000000000000000000000000000000000";
  SOURCE_LANG = options.sourceLang || 'en';
  CREATE_TRANSLATION_STUBS = options.createTranslationStubs || false;

  console.log("🔄 Product CSV Transformation");
  console.log("=".repeat(70));
  console.log(`📄 CSV: ${CSV_PATH}`);
  console.log(`📂 Output: ${OUTPUT_DIR}`);
  console.log(`👤 Seller: ${SELLER_ID}`);
  console.log(`🌐 Source Language: ${SOURCE_LANG}`);
  console.log(`📝 Translation Stubs: ${CREATE_TRANSLATION_STUBS ? "ENABLED" : "DISABLED"}`);
  console.log(`🔷 Dry-run: ${DRY_RUN ? "ENABLED" : "DISABLED"}`);
  console.log("=".repeat(70));

  try {
    // 1. Валидация входных файлов
    console.log("\n🔍 Validating input files...");
    
    if (!fs.existsSync(CSV_PATH)) {
      throw new Error(`CSV file not found: ${CSV_PATH}`);
    }
    
    if (!DRY_RUN && !fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true });
      console.log(`✅ Created output directory: ${OUTPUT_DIR}`);
    }
    
    // 2. Парсинг CSV
    console.log("\n🔍 Parsing CSV...");
    const rows = csvParser.parseProductCatalog(CSV_PATH);
    stats.total_rows = rows.length;
    console.log(`✅ Parsed ${rows.length} rows from CSV`);
    
    // 3. Трансформация каждой строки
    console.log("\n🔄 Starting transformation...");
    
    const results = [];
    for (let i = 0; i < rows.length; i++) {
      const result = transformProduct(rows[i], i);
      results.push(result);
      
      // Небольшая задержка для читаемости логов
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // 4. Генерация отчета о мапинге форм
    console.log("\n📊 Generating form mapping report...");
    const formReport = formMapper.generateFormMappingReport(stats.form_mappings);
    
    console.log("\n" + "=".repeat(70));
    console.log("📊 FORM MAPPING STATISTICS");
    console.log("=".repeat(70));
    console.log(`Total mappings: ${formReport.total}`);
    console.log(`  → Exact match: ${formReport.exact_match}`);
    console.log(`  → Known mapping: ${formReport.known_mapping}`);
    console.log(`  → Substring match: ${formReport.substring_match}`);
    console.log(`  → Fallback: ${formReport.fallback}`);
    console.log(`\nUnique forms used: ${formReport.unique_forms.join(', ')}`);
    console.log(`\nConfidence distribution:`);
    console.log(`  → High (>=0.9): ${formReport.mappings_by_confidence.high.length}`);
    console.log(`  → Medium (0.7-0.9): ${formReport.mappings_by_confidence.medium.length}`);
    console.log(`  → Low (<0.7): ${formReport.mappings_by_confidence.low.length}`);
    
    if (formReport.mappings_by_confidence.low.length > 0) {
      console.log(`\n⚠️ Low confidence mappings (manual review recommended):`);
      formReport.mappings_by_confidence.low.forEach(m => {
        console.log(`   → "${m.original_form}" → "${m.standard_form}" (${(m.confidence * 100).toFixed(0)}%)`);
      });
    }
    
    // 5. Сохранение отчета
    if (!DRY_RUN) {
      const reportPath = path.join(OUTPUT_DIR, '_transformation_report.json');
      const report = {
        csv_file: CSV_PATH,
        seller_id: SELLER_ID,
        transformed_at: new Date().toISOString(),
        statistics: {
          total_rows: stats.total_rows,
          valid_products: stats.valid_products,
          skipped_products: stats.skipped_products,
          unique_components: Array.from(stats.component_links).length
        },
        form_mapping: formReport,
        errors: stats.errors
      };
      
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
      console.log(`\n💾 Transformation report saved: ${reportPath}`);
    }
    
    // 6. Финальная статистика
    console.log("\n" + "=".repeat(70));
    console.log("✅ TRANSFORMATION COMPLETE");
    console.log("=".repeat(70));
    console.log(`Total rows: ${stats.total_rows}`);
    console.log(`Valid products: ${stats.valid_products}`);
    console.log(`Skipped: ${stats.skipped_products}`);
    console.log(`Unique components: ${Array.from(stats.component_links).length}`);
    
    if (stats.errors.length > 0) {
      console.log(`\n❌ Errors (${stats.errors.length}):`);
      stats.errors.forEach(err => {
        console.log(`   → ${err.product_id}: ${err.error}`);
      });
    }
    
    if (!DRY_RUN) {
      console.log(`\n💾 Products saved to: ${OUTPUT_DIR}`);
      console.log("\n🎯 Next steps:");
      console.log("   1. Review transformation report");
      console.log("   2. Validate products: node scripts/validate_products.js");
      console.log("   3. Upload to Arweave: npx hardhat run scripts/upload_all_products.js");
    } else {
      console.log("\n🔷 [DRY-RUN] No files were created");
      console.log("   Remove --dry-run to create product JSON files");
    }
    
    console.log("=".repeat(70));
    
    process.exit(stats.errors.length > 0 ? 1 : 0);
    
  } catch (error) {
    console.error("\n" + "=".repeat(70));
    console.error("❌ TRANSFORMATION FAILED");
    console.error("=".repeat(70));
    console.error(`Error: ${error.message}`);
    console.error(`\nStack trace:\n${error.stack}`);
    console.error("=".repeat(70));
    process.exit(1);
  }
}

// ====================================================================
// 🚀 MODULE EXPORT
// ====================================================================

/**
 * Экспортируемая функция для использования как модуль
 * @param {Object} config - Конфигурация трансформации
 * @returns {Promise<Object>} Результаты трансформации
 */
async function transformProductsFromCSV(config) {
  // Сохраняем оригинальные значения (если были)
  const originalCSV = CSV_PATH;
  const originalOutput = OUTPUT_DIR;
  const originalSeller = SELLER_ID;
  const originalAddress = SELLER_ADDRESS;
  const originalLang = SOURCE_LANG;
  const originalStubs = CREATE_TRANSLATION_STUBS;
  const originalDryRun = DRY_RUN;
  
  try {
    // Инициализируем глобальные переменные из config
    CSV_PATH = path.resolve(config.csvPath);
    OUTPUT_DIR = path.resolve(config.outputDir);
    SELLER_ID = config.sellerId;
    SELLER_ADDRESS = config.sellerAddress || "0x0000000000000000000000000000000000000000";
    SOURCE_LANG = config.sourceLang || 'en';
    CREATE_TRANSLATION_STUBS = config.createTranslationStubs || false;
    DRY_RUN = config.dryRun || false;
    
    // Вызываем mainWithoutExit() без process.exit()
    const result = await mainWithoutExit();
    
    // Восстанавливаем оригинальные значения
    CSV_PATH = originalCSV;
    OUTPUT_DIR = originalOutput;
    SELLER_ID = originalSeller;
    SELLER_ADDRESS = originalAddress;
    SOURCE_LANG = originalLang;
    CREATE_TRANSLATION_STUBS = originalStubs;
    DRY_RUN = originalDryRun;
    
    return result;
  } catch (error) {
    // Восстанавливаем значения даже при ошибке
    CSV_PATH = originalCSV;
    OUTPUT_DIR = originalOutput;
    SELLER_ID = originalSeller;
    SELLER_ADDRESS = originalAddress;
    SOURCE_LANG = originalLang;
    CREATE_TRANSLATION_STUBS = originalStubs;
    DRY_RUN = originalDryRun;
    
    throw error;
  }
}

/**
 * Main без process.exit() для использования как модуль
 */
async function mainWithoutExit() {
  // 1. Валидация входных файлов
  console.log("\n🔍 Validating input files...");
  
  if (!fs.existsSync(CSV_PATH)) {
    throw new Error(`CSV file not found: ${CSV_PATH}`);
  }
  
  if (!DRY_RUN && !fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    console.log(`✅ Created output directory: ${OUTPUT_DIR}`);
  }
  
  // 2. Парсинг CSV
  console.log("\n🔍 Parsing CSV...");
  const rows = csvParser.parseProductCatalog(CSV_PATH);
  stats.total_rows = rows.length;
  console.log(`✅ Parsed ${rows.length} rows from CSV`);
  
  // 3. Трансформация каждой строки
  console.log("\n🔄 Starting transformation...");
  
  const results = [];
  for (let i = 0; i < rows.length; i++) {
    const result = transformProduct(rows[i], i);
    results.push(result);
    
    // Небольшая задержка для читаемости логов
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  // 4. Генерация отчета о мапинге форм
  console.log("\n📊 Generating form mapping report...");
  const formReport = formMapper.generateFormMappingReport(stats.form_mappings);
  
  console.log("\n" + "=".repeat(70));
  console.log("📊 FORM MAPPING STATISTICS");
  console.log("=".repeat(70));
  console.log(`Total mappings: ${formReport.total}`);
  console.log(`  → Exact match: ${formReport.exact_match}`);
  console.log(`  → Known mapping: ${formReport.known_mapping}`);
  console.log(`  → Substring match: ${formReport.substring_match}`);
  console.log(`  → Fallback: ${formReport.fallback}`);
  console.log(`\nUnique forms used: ${formReport.unique_forms.join(', ')}`);
  console.log(`\nConfidence distribution:`);
  console.log(`  → High (>=0.9): ${formReport.mappings_by_confidence.high.length}`);
  console.log(`  → Medium (0.7-0.9): ${formReport.mappings_by_confidence.medium.length}`);
  console.log(`  → Low (<0.7): ${formReport.mappings_by_confidence.low.length}`);
  
  if (formReport.mappings_by_confidence.low.length > 0) {
    console.log(`\n⚠️ Low confidence mappings (manual review recommended):`);
    formReport.mappings_by_confidence.low.forEach(m => {
      console.log(`   → "${m.original_form}" → "${m.standard_form}" (${(m.confidence * 100).toFixed(0)}%)`);
    });
  }
  
  // 5. Сохранение отчета
  if (!DRY_RUN) {
    const reportPath = path.join(OUTPUT_DIR, '_transformation_report.json');
    const report = {
      csv_file: CSV_PATH,
      seller_id: SELLER_ID,
      transformed_at: new Date().toISOString(),
      statistics: {
        total_rows: stats.total_rows,
        valid_products: stats.valid_products,
        skipped_products: stats.skipped_products,
        unique_components: Array.from(stats.component_links).length
      },
      form_mapping: formReport,
      errors: stats.errors
    };
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n💾 Transformation report saved: ${reportPath}`);
  }
  
  // 6. Финальная статистика
  console.log("\n" + "=".repeat(70));
  console.log("✅ TRANSFORMATION COMPLETE");
  console.log("=".repeat(70));
  console.log(`Total rows: ${stats.total_rows}`);
  console.log(`Valid products: ${stats.valid_products}`);
  console.log(`Skipped: ${stats.skipped_products}`);
  console.log(`Unique components: ${Array.from(stats.component_links).length}`);
  
  if (stats.errors.length > 0) {
    console.log(`\n❌ Errors (${stats.errors.length}):`);
    stats.errors.forEach(err => {
      console.log(`   → ${err.product_id}: ${err.error}`);
    });
  }
  
  if (!DRY_RUN) {
    console.log(`\n💾 Products saved to: ${OUTPUT_DIR}`);
    console.log("\n🎯 Next steps:");
    console.log("   1. Review transformation report");
    console.log("   2. Validate products: node scripts/validate_products.js");
    console.log("   3. Upload to Arweave: npx hardhat run scripts/upload_all_products.js");
  } else {
    console.log("\n🔷 [DRY-RUN] No files were created");
    console.log("   Remove --dry-run to create product JSON files");
  }
  
  console.log("=".repeat(70));
  
  // Возвращаем результат вместо process.exit
  return {
    success: stats.errors.length === 0,
    statistics: {
      total_rows: stats.total_rows,
      valid_products: stats.valid_products,
      skipped_products: stats.skipped_products,
      unique_components: Array.from(stats.component_links).length
    },
    errors: stats.errors,
    results: results
  };
}

// ====================================================================
// 🚀 RUN (только если запущен напрямую)
// ====================================================================

if (require.main === module) {
  main();
}

// Экспортируем для использования как модуль
module.exports = {
  transformProductsFromCSV,
  // Экспортируем константы для доступа извне
  SUPPORTED_LANGUAGES
};

