/**
 * 📄 CSV Parser Module
 * 
 * Парсинг CSV каталога продуктов с валидацией структуры
 * 
 * @module csv_parser
 * @version 1.0.0
 * @date 2025-01-12
 */

const fs = require('fs');
const { parse } = require('csv-parse/sync');

/**
 * Парсинг CSV файла каталога
 * @param {string} csvPath - Путь к CSV файлу
 * @returns {Array<Object>} Массив строк каталога
 */
function parseProductCatalog(csvPath) {
  console.log(`📄 Parsing CSV catalog: ${csvPath}`);
  
  // 1. Чтение файла
  if (!fs.existsSync(csvPath)) {
    throw new Error(`CSV file not found: ${csvPath}`);
  }
  
  const csvContent = fs.readFileSync(csvPath, 'utf8');
  
  // 2. Парсинг CSV (используем библиотеку csv-parse)
  const records = parse(csvContent, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true
  });
  
  console.log(`   ✅ Parsed ${records.length} rows`);
  
  // 3. Валидация структуры
  const requiredColumns = [
    'component_business_id',
    'product_business_id', 
    'product_name',
    'image_file',
    'form',
    'prices'
  ];
  
  if (records.length === 0) {
    throw new Error('CSV file is empty or has no data rows');
  }
  
  const firstRow = records[0];
  const missingColumns = [];
  
  for (const col of requiredColumns) {
    if (!firstRow.hasOwnProperty(col)) {
      missingColumns.push(col);
    }
  }
  
  if (missingColumns.length > 0) {
    throw new Error(
      `Missing required columns: ${missingColumns.join(', ')}\n` +
      `Available columns: ${Object.keys(firstRow).join(', ')}`
    );
  }
  
  console.log(`   ✅ All required columns present`);
  
  // 4. Очистка данных
  const cleaned = records.map(row => ({
    component_business_id: row.component_business_id?.trim() || '',
    product_business_id: row.product_business_id?.trim() || '',
    product_name: row.product_name?.trim() || '',
    image_file: row.image_file?.trim() || '',
    form: row.form?.trim() || '',
    prices: row.prices?.trim() || '',
    // categories и species игнорируем
  }));
  
  // 5. Фильтрация пустых строк
  const filtered = cleaned.filter(row => 
    row.component_business_id && row.product_business_id && row.product_name
  );
  
  console.log(`   ✅ Cleaned and filtered: ${filtered.length} valid rows`);
  
  return filtered;
}

module.exports = {
  parseProductCatalog
};

