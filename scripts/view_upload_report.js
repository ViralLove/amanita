/**
 * 📊 View Upload Report Utility
 * 
 * Утилита для просмотра отчетов batch upload
 * 
 * @version 1.0.0
 * @date 2025-10-09
 * 
 * Использование:
 * # Просмотр последнего отчета
 * node scripts/view_upload_report.js
 * 
 * # Просмотр конкретного отчета
 * node scripts/view_upload_report.js --report <path>
 * 
 * # Показать детали всех компонентов
 * node scripts/view_upload_report.js --details
 * 
 * # Экспорт в JSON (pretty print)
 * node scripts/view_upload_report.js --export report.json
 */

const fs = require('fs');
const path = require('path');
const reportCollector = require('./lib/report_collector');

// ====================================================================
// 🔧 ARGUMENT PARSING
// ====================================================================

const args = process.argv.slice(2);

let reportPath = null;
let showDetails = false;
let exportPath = null;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--report' && i + 1 < args.length) {
    reportPath = args[i + 1];
    i++;
  } else if (args[i] === '--details') {
    showDetails = true;
  } else if (args[i] === '--export' && i + 1 < args.length) {
    exportPath = args[i + 1];
    i++;
  } else if (args[i] === '--help' || args[i] === '-h') {
    printHelp();
    process.exit(0);
  }
}

// ====================================================================
// 📋 HELP
// ====================================================================

function printHelp() {
  console.log(`
📊 View Upload Report Utility

Использование:
  node scripts/view_upload_report.js [options]

Опции:
  --report <path>   Путь к файлу отчета (по умолчанию последний)
  --details         Показать детали всех компонентов
  --export <path>   Экспортировать отчет в JSON файл
  --help, -h        Показать эту справку

Примеры:
  # Просмотр последнего отчета
  node scripts/view_upload_report.js

  # Просмотр конкретного отчета
  node scripts/view_upload_report.js --report scripts/organic_components/_upload_report_polygon_2025-10-09T12-00-00-000Z.json

  # Показать детали компонентов
  node scripts/view_upload_report.js --details

  # Экспорт отчета
  node scripts/view_upload_report.js --export my_report.json
  `);
}

// ====================================================================
// 🔍 REPORT DISCOVERY
// ====================================================================

/**
 * Найти последний отчет в директории
 * @param {string} directory - Директория для поиска
 * @returns {string|null} Путь к последнему отчету
 */
function findLatestReport(directory) {
  const componentsDir = path.join(__dirname, 'organic_components');
  
  if (!fs.existsSync(componentsDir)) {
    return null;
  }
  
  const files = fs.readdirSync(componentsDir);
  const reportFiles = files
    .filter(f => f.startsWith('_upload_report_') && f.endsWith('.json'))
    .map(f => ({
      name: f,
      path: path.join(componentsDir, f),
      mtime: fs.statSync(path.join(componentsDir, f)).mtime
    }))
    .sort((a, b) => b.mtime - a.mtime);
  
  if (reportFiles.length === 0) {
    return null;
  }
  
  return reportFiles[0].path;
}

// ====================================================================
// 📊 REPORT VIEWING
// ====================================================================

/**
 * Вывести детали всех компонентов
 * @param {Object} report - Report object
 */
function printAllComponentDetails(report) {
  console.log("\n" + "=".repeat(70));
  console.log("📦 ДЕТАЛИ КОМПОНЕНТОВ");
  console.log("=".repeat(70));
  
  const components = report.components.sort((a, b) => {
    // Сортировка: completed, failed, остальные
    const statusOrder = { completed: 0, failed: 1, in_progress: 2, pending: 3, skipped: 4 };
    return statusOrder[a.status] - statusOrder[b.status];
  });
  
  for (const comp of components) {
    reportCollector.printComponentDetails(comp);
  }
  
  console.log("\n" + "=".repeat(70));
}

/**
 * Экспортировать отчет в JSON файл
 * @param {Object} report - Report object
 * @param {string} exportPath - Путь для экспорта
 */
function exportReport(report, exportPath) {
  try {
    fs.writeFileSync(exportPath, JSON.stringify(report, null, 2), 'utf8');
    console.log(`\n✅ Отчет экспортирован: ${exportPath}`);
    console.log(`   Размер: ${reportCollector.formatBytes(fs.statSync(exportPath).size)}`);
  } catch (error) {
    console.error(`\n❌ Ошибка экспорта: ${error.message}`);
    process.exit(1);
  }
}

/**
 * Вывести таблицу компонентов
 * @param {Object} report - Report object
 */
function printComponentsTable(report) {
  console.log("\n" + "=".repeat(70));
  console.log("📋 ТАБЛИЦА КОМПОНЕНТОВ");
  console.log("=".repeat(70));
  
  // Header
  console.log(
    "№".padEnd(4) +
    "Component ID".padEnd(25) +
    "Status".padEnd(12) +
    "Duration".padEnd(10) +
    "Files".padEnd(8)
  );
  console.log("-".repeat(70));
  
  // Rows
  report.components.forEach((comp, index) => {
    const status = comp.status === 'completed' ? '✅ OK' :
                   comp.status === 'failed' ? '❌ FAIL' :
                   comp.status === 'in_progress' ? '⏳ WIP' :
                   comp.status === 'skipped' ? '⏭️ SKIP' :
                   '⏸️ PEND';
    
    const duration = comp.duration_seconds 
      ? reportCollector.formatDuration(comp.duration_seconds) 
      : '-';
    
    const files = comp.arweave.total_files || '-';
    
    console.log(
      String(index + 1).padEnd(4) +
      comp.component_id.padEnd(25) +
      status.padEnd(12) +
      duration.padEnd(10) +
      String(files).padEnd(8)
    );
  });
  
  console.log("=".repeat(70));
}

/**
 * Вывести статистику по ошибкам
 * @param {Object} report - Report object
 */
function printErrorsStatistics(report) {
  if (report.errors.length === 0) {
    return;
  }
  
  console.log("\n" + "=".repeat(70));
  console.log("❌ ДЕТАЛИ ОШИБОК");
  console.log("=".repeat(70));
  
  report.errors.forEach((err, index) => {
    console.log(`\n${index + 1}. Component: ${err.component_id}`);
    console.log(`   Time: ${new Date(err.timestamp).toLocaleString()}`);
    console.log(`   Error: ${err.message}`);
    
    if (err.stack) {
      const stackLines = err.stack.split('\n').slice(0, 3);
      console.log(`   Stack: ${stackLines.join('\n          ')}`);
    }
  });
  
  console.log("\n" + "=".repeat(70));
}

// ====================================================================
// 🎯 MAIN
// ====================================================================

function main() {
  console.log("\n" + "=".repeat(70));
  console.log("📊 UPLOAD REPORT VIEWER");
  console.log("=".repeat(70));
  
  // 1. Определить путь к отчету
  if (!reportPath) {
    console.log("\n🔍 Поиск последнего отчета...");
    reportPath = findLatestReport();
    
    if (!reportPath) {
      console.error("\n❌ Отчеты не найдены в scripts/organic_components/");
      console.error("   Запустите upload_all_components.js для создания отчета");
      process.exit(1);
    }
    
    console.log(`✅ Найден: ${path.basename(reportPath)}`);
  }
  
  // 2. Загрузить отчет
  console.log(`\n📂 Загрузка отчета: ${path.basename(reportPath)}`);
  
  const report = reportCollector.loadReport(reportPath);
  
  if (!report) {
    console.error(`\n❌ Не удалось загрузить отчет: ${reportPath}`);
    process.exit(1);
  }
  
  console.log(`✅ Отчет загружен (${reportCollector.formatBytes(reportCollector.getReportSize(reportPath))})`);
  
  // 3. Вывести summary
  reportCollector.printSummary(report);
  
  // 4. Таблица компонентов
  printComponentsTable(report);
  
  // 5. Детали компонентов (если запрошено)
  if (showDetails) {
    printAllComponentDetails(report);
  }
  
  // 6. Ошибки (если есть)
  if (report.errors.length > 0) {
    printErrorsStatistics(report);
  }
  
  // 7. Экспорт (если запрошен)
  if (exportPath) {
    exportReport(report, exportPath);
  }
  
  // 8. Подсказки
  console.log("\n" + "=".repeat(70));
  console.log("💡 ПОДСКАЗКИ");
  console.log("=".repeat(70));
  console.log("• Показать детали компонентов: --details");
  console.log("• Экспортировать отчет: --export <filename>");
  console.log("• Справка: --help");
  console.log("=".repeat(70) + "\n");
}

// ====================================================================
// 🚀 EXECUTION
// ====================================================================

try {
  main();
} catch (error) {
  console.error("\n" + "=".repeat(70));
  console.error("❌ КРИТИЧЕСКАЯ ОШИБКА");
  console.error("=".repeat(70));
  console.error(`Сообщение: ${error.message}`);
  console.error(`\nStack trace:\n${error.stack}`);
  console.error("=".repeat(70) + "\n");
  process.exit(1);
}

