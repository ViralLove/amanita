/**
 * 📊 Report Collector Module
 * 
 * Сбор метрик и генерация финального отчета для batch upload
 * Incremental reporting с сохранением промежуточных результатов
 * 
 * @version 1.0.0
 * @date 2025-10-09
 */

const fs = require('fs');
const path = require('path');

// ====================================================================
// 📋 REPORT INITIALIZATION
// ====================================================================

/**
 * Создать новый report object
 * @param {Object} session - Session info из batch state
 * @returns {Object} Пустой report
 */
function createReport(session) {
  return {
    upload_session: {
      session_id: session.session_id,
      network: session.network,
      started_at: session.started_at,
      completed_at: null,
      duration_seconds: null,
      deployer: session.deployer,
      dry_run: session.dry_run,
      upload_shareable: session.upload_shareable,
      version: session.version
    },
    
    global_dictionaries: {
      uploaded: false,
      features_cid: null,
      forms_cid: null,
      features_version: null,
      forms_version: null,
      uploaded_at: null
    },
    
    components: [],
    
    summary: {
      total_components: 0,
      successful: 0,
      failed: 0,
      skipped: 0,
      total_files_uploaded: 0,
      total_arweave_size_bytes: 0,
      total_gas_used: 0,
      total_cost_matic: "0",
      total_cost_usd: "0",
      average_component_duration_seconds: 0
    },
    
    errors: []
  };
}

/**
 * Загрузить существующий report из файла
 * @param {string} reportPath - Путь к файлу отчета
 * @returns {Object|null} Report или null
 */
function loadReport(reportPath) {
  if (fs.existsSync(reportPath)) {
    try {
      const data = fs.readFileSync(reportPath, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      console.warn(`⚠️ Ошибка загрузки report: ${error.message}`);
      return null;
    }
  }
  return null;
}

/**
 * Сохранить report в файл
 * @param {string} reportPath - Путь к файлу отчета
 * @param {Object} report - Report object
 */
function saveReport(reportPath, report) {
  try {
    // Обновляем timestamp
    report.upload_session.updated_at = new Date().toISOString();
    
    // Создаем директорию если не существует
    const dir = path.dirname(reportPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    
    // Сохраняем с pretty print
    // BigInt replacer для JSON.stringify
    const replacer = (key, value) => 
        typeof value === 'bigint' ? value.toString() : value;
    fs.writeFileSync(reportPath, JSON.stringify(report, replacer, 2), 'utf8');
    
  } catch (error) {
    console.error(`❌ Ошибка сохранения report: ${error.message}`);
    throw error;
  }
}

// ====================================================================
// 📊 GLOBAL DICTIONARIES REPORTING
// ====================================================================

/**
 * Добавить информацию о загрузке global dictionaries
 * @param {Object} report - Report object
 * @param {string} featuresCID - CID features.json
 * @param {string} formsCID - CID component_forms.json
 * @param {number} featuresVersion - Версия features
 * @param {number} formsVersion - Версия forms
 */
function reportGlobalDictionaries(report, featuresCID, formsCID, featuresVersion, formsVersion) {
  report.global_dictionaries = {
    uploaded: true,
    features_cid: featuresCID,
    forms_cid: formsCID,
    features_version: featuresVersion,
    forms_version: formsVersion,
    uploaded_at: new Date().toISOString()
  };
  
  console.log("📊 Report: Добавлена информация о global dictionaries");
}

// ====================================================================
// 📦 COMPONENT REPORTING
// ====================================================================

/**
 * Создать component report entry
 * @param {string} componentId - ID компонента
 * @returns {Object} Пустой component report
 */
function createComponentReport(componentId) {
  return {
    component_id: componentId,
    status: "pending",
    started_at: null,
    completed_at: null,
    duration_seconds: null,
    
    arweave: {
      root_cid: null,
      simple_fields: {},
      complex_fields: {},
      total_files: 0,
      total_size_bytes: 0,
      upload_duration_seconds: null
    },
    
    blockchain: {
      component_id: null,
      registration_tx: null,
      registration_block: null,
      total_gas_used: 0,
      total_cost_matic: "0",
      total_cost_usd: "0"
    },
    
    metadata: {
      scientific_title: null,
      forms_count: 0,
      features_common_count: 0,
      features_form_specific_count: 0,
      languages_count: 0
    },
    
    validation: {
      files_validated: 0,
      validation_errors: [],
      warnings: []
    }
  };
}

/**
 * Начать tracking компонента
 * @param {Object} report - Report object
 * @param {string} componentId - ID компонента
 */
function startComponentTracking(report, componentId) {
  // Проверяем, есть ли уже этот компонент
  const existing = report.components.find(c => c.component_id === componentId);
  
  if (existing) {
    existing.status = "in_progress";
    existing.started_at = new Date().toISOString();
  } else {
    const componentReport = createComponentReport(componentId);
    componentReport.status = "in_progress";
    componentReport.started_at = new Date().toISOString();
    report.components.push(componentReport);
  }
  
  console.log(`📊 Report: Начат tracking для ${componentId}`);
}

/**
 * Добавить Arweave метрики для компонента
 * @param {Object} report - Report object
 * @param {string} componentId - ID компонента
 * @param {Object} arweaveData - Данные из Arweave
 */
function addArweaveMetrics(report, componentId, arweaveData) {
  const componentReport = report.components.find(c => c.component_id === componentId);
  
  if (!componentReport) {
    console.warn(`⚠️ Компонент ${componentId} не найден в report`);
    return;
  }
  
  componentReport.arweave = {
    root_cid: arweaveData.root_cid || null,
    simple_fields: arweaveData.simple_fields || {},
    complex_fields: arweaveData.complex_fields || {},
    total_files: arweaveData.total_files || 0,
    total_size_bytes: arweaveData.total_size_bytes || 0,
    upload_duration_seconds: arweaveData.upload_duration_seconds || null
  };
  
  console.log(`📊 Report: Добавлены Arweave метрики для ${componentId}`);
}

/**
 * Добавить Blockchain метрики для компонента
 * @param {Object} report - Report object
 * @param {string} componentId - ID компонента
 * @param {Object} blockchainData - Данные из blockchain
 */
function addBlockchainMetrics(report, componentId, blockchainData) {
  const componentReport = report.components.find(c => c.component_id === componentId);
  
  if (!componentReport) {
    console.warn(`⚠️ Компонент ${componentId} не найден в report`);
    return;
  }
  
  componentReport.blockchain = {
    component_id: blockchainData.component_id || null,
    registration_tx: blockchainData.registration_tx || null,
    registration_block: blockchainData.registration_block || null,
    total_gas_used: blockchainData.total_gas_used || 0,
    total_cost_matic: blockchainData.total_cost_matic || "0",
    total_cost_usd: blockchainData.total_cost_usd || "0"
  };
  
  console.log(`📊 Report: Добавлены Blockchain метрики для ${componentId}`);
}

/**
 * Добавить Metadata для компонента
 * @param {Object} report - Report object
 * @param {string} componentId - ID компонента
 * @param {Object} metadata - Метаданные компонента
 */
function addComponentMetadata(report, componentId, metadata) {
  const componentReport = report.components.find(c => c.component_id === componentId);
  
  if (!componentReport) {
    console.warn(`⚠️ Компонент ${componentId} не найден в report`);
    return;
  }
  
  componentReport.metadata = {
    scientific_title: metadata.scientific_title || null,
    forms_count: metadata.forms?.length || 0,
    features_common_count: metadata.features?.common?.length || 0,
    features_form_specific_count: Object.keys(metadata.features?.forms || {}).length,
    languages_count: metadata.languages_count || 0
  };
  
  console.log(`📊 Report: Добавлены Metadata для ${componentId}`);
}

/**
 * Завершить tracking компонента (успех)
 * @param {Object} report - Report object
 * @param {string} componentId - ID компонента
 */
function completeComponentTracking(report, componentId) {
  const componentReport = report.components.find(c => c.component_id === componentId);
  
  if (!componentReport) {
    console.warn(`⚠️ Компонент ${componentId} не найден в report`);
    return;
  }
  
  componentReport.status = "completed";
  componentReport.completed_at = new Date().toISOString();
  
  // Расчет duration
  if (componentReport.started_at) {
    const start = new Date(componentReport.started_at);
    const end = new Date(componentReport.completed_at);
    componentReport.duration_seconds = Math.round((end - start) / 1000);
  }
  
  console.log(`📊 Report: ${componentId} завершен (${componentReport.duration_seconds}s)`);
}

/**
 * Отметить компонент как failed
 * @param {Object} report - Report object
 * @param {string} componentId - ID компонента
 * @param {Error} error - Объект ошибки
 */
function failComponentTracking(report, componentId, error) {
  const componentReport = report.components.find(c => c.component_id === componentId);
  
  if (!componentReport) {
    // Создаем новый если не существует
    const newReport = createComponentReport(componentId);
    newReport.status = "failed";
    newReport.completed_at = new Date().toISOString();
    report.components.push(newReport);
  } else {
    componentReport.status = "failed";
    componentReport.completed_at = new Date().toISOString();
    
    if (componentReport.started_at) {
      const start = new Date(componentReport.started_at);
      const end = new Date(componentReport.completed_at);
      componentReport.duration_seconds = Math.round((end - start) / 1000);
    }
  }
  
  // Добавляем ошибку в общий список
  report.errors.push({
    component_id: componentId,
    timestamp: new Date().toISOString(),
    message: error.message,
    stack: error.stack
  });
  
  console.log(`📊 Report: ${componentId} failed - ${error.message}`);
}

// ====================================================================
// 📈 SUMMARY GENERATION
// ====================================================================

/**
 * Обновить summary раздел отчета
 * @param {Object} report - Report object
 */
function updateSummary(report) {
  const components = report.components;
  
  // Подсчет статусов
  const successful = components.filter(c => c.status === "completed").length;
  const failed = components.filter(c => c.status === "failed").length;
  const skipped = components.filter(c => c.status === "skipped").length;
  
  // Агрегация метрик
  let totalFiles = 0;
  let totalSize = 0;
  let totalGas = 0;
  let totalCostMatic = 0;
  let totalDuration = 0;
  
  for (const comp of components) {
    if (comp.status === "completed") {
      totalFiles += comp.arweave.total_files || 0;
      totalSize += comp.arweave.total_size_bytes || 0;
      totalGas += comp.blockchain.total_gas_used || 0;
      totalCostMatic += parseFloat(comp.blockchain.total_cost_matic || 0);
      totalDuration += comp.duration_seconds || 0;
    }
  }
  
  // Средняя длительность
  const avgDuration = successful > 0 
    ? Math.round(totalDuration / successful) 
    : 0;
  
  // Примерная стоимость в USD (MATIC ~$0.70)
  const maticPriceUsd = 0.70;
  const totalCostUsd = (totalCostMatic * maticPriceUsd).toFixed(3);
  
  report.summary = {
    total_components: components.length,
    successful,
    failed,
    skipped,
    total_files_uploaded: totalFiles,
    total_arweave_size_bytes: totalSize,
    total_gas_used: totalGas,
    total_cost_matic: totalCostMatic.toFixed(4),
    total_cost_usd: totalCostUsd,
    average_component_duration_seconds: avgDuration
  };
  
  console.log(`📊 Report: Summary обновлен`);
}

/**
 * Финализировать отчет (закрыть сессию)
 * @param {Object} report - Report object
 */
function finalizeReport(report) {
  // Обновить summary
  updateSummary(report);
  
  // Установить completion timestamp
  report.upload_session.completed_at = new Date().toISOString();
  
  // Расчет общей длительности
  const start = new Date(report.upload_session.started_at);
  const end = new Date(report.upload_session.completed_at);
  report.upload_session.duration_seconds = Math.round((end - start) / 1000);
  
  console.log(`📊 Report: Финализирован`);
  console.log(`   → Duration: ${report.upload_session.duration_seconds}s`);
  console.log(`   → Components: ${report.summary.successful}/${report.summary.total_components}`);
}

// ====================================================================
// 📊 METRICS EXTRACTION
// ====================================================================

/**
 * Извлечь метрики из component state
 * @param {Object} componentState - State компонента
 * @param {Object} rootData - Root metadata
 * @returns {Object} Extracted metrics
 */
function extractMetricsFromState(componentState, rootData) {
  const metrics = {
    arweave: {
      root_cid: componentState.root_metadata?.cid || null,
      simple_fields: componentState.simple_fields || {},
      complex_fields: componentState.complex_fields || {},
      total_files: 0,
      total_size_bytes: 0
    },
    blockchain: {
      component_id: componentState.contract_registration?.componentId || null,
      registration_tx: componentState.contract_registration?.txHash || null,
      registration_block: componentState.contract_registration?.blockNumber || null,
      total_gas_used: 0,
      total_cost_matic: "0"
    },
    metadata: {
      scientific_title: rootData?.scientific_title || null,
      forms: rootData?.forms || [],
      features: rootData?.features || {},
      languages_count: 0
    }
  };
  
  // Подсчет файлов
  metrics.arweave.total_files = 
    Object.keys(metrics.arweave.simple_fields).length +
    Object.keys(metrics.arweave.complex_fields).length +
    1; // root file
  
  // Подсчет языков
  metrics.metadata.languages_count = Object.keys(metrics.arweave.complex_fields).length;
  
  return metrics;
}

// ====================================================================
// 📋 REPORT UTILITIES
// ====================================================================

/**
 * Получить путь к файлу отчета
 * @param {string} componentsDir - Базовая директория
 * @param {string} network - Название сети
 * @param {string} sessionId - ID сессии (optional)
 * @returns {string} Путь к файлу
 */
function getReportPath(componentsDir, network, sessionId = null) {
  if (sessionId) {
    const timestamp = sessionId.replace('upload_', '').replace(/-/g, '');
    return path.join(componentsDir, `_upload_report_${network}_${timestamp}.json`);
  } else {
    // Текущий timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    return path.join(componentsDir, `_upload_report_${network}_${timestamp}.json`);
  }
}

/**
 * Проверить существование отчета
 * @param {string} reportPath - Путь к файлу
 * @returns {boolean} true если существует
 */
function reportExists(reportPath) {
  return fs.existsSync(reportPath);
}

/**
 * Получить размер отчета в байтах
 * @param {string} reportPath - Путь к файлу
 * @returns {number} Размер в байтах
 */
function getReportSize(reportPath) {
  if (fs.existsSync(reportPath)) {
    return fs.statSync(reportPath).size;
  }
  return 0;
}

// ====================================================================
// 🎨 VISUALIZATION
// ====================================================================

/**
 * Вывести красивый summary в консоль
 * @param {Object} report - Report object
 */
function printSummary(report) {
  console.log("\n" + "=".repeat(70));
  console.log("📊 UPLOAD REPORT SUMMARY");
  console.log("=".repeat(70));
  
  console.log("\n🎯 Session Info:");
  console.log(`   → Session ID: ${report.upload_session.session_id}`);
  console.log(`   → Network: ${report.upload_session.network.toUpperCase()}`);
  console.log(`   → Started: ${new Date(report.upload_session.started_at).toLocaleString()}`);
  
  if (report.upload_session.completed_at) {
    console.log(`   → Completed: ${new Date(report.upload_session.completed_at).toLocaleString()}`);
    console.log(`   → Duration: ${formatDuration(report.upload_session.duration_seconds)}`);
  }
  
  console.log(`   → Dry Run: ${report.upload_session.dry_run ? "YES" : "NO"}`);
  
  console.log("\n📦 Components:");
  console.log(`   → Total: ${report.summary.total_components}`);
  console.log(`   → ✅ Successful: ${report.summary.successful}`);
  console.log(`   → ❌ Failed: ${report.summary.failed}`);
  console.log(`   → ⏭️ Skipped: ${report.summary.skipped}`);
  
  if (report.global_dictionaries.uploaded) {
    console.log("\n📚 Global Dictionaries:");
    console.log(`   → Features CID: ${report.global_dictionaries.features_cid}`);
    console.log(`   → Forms CID: ${report.global_dictionaries.forms_cid}`);
  }
  
  console.log("\n📊 Arweave Metrics:");
  console.log(`   → Total Files: ${report.summary.total_files_uploaded}`);
  console.log(`   → Total Size: ${formatBytes(report.summary.total_arweave_size_bytes)}`);
  
  if (!report.upload_session.dry_run) {
    console.log("\n⛓️ Blockchain Metrics:");
    console.log(`   → Total Gas Used: ${report.summary.total_gas_used.toLocaleString()}`);
    console.log(`   → Total Cost (MATIC): ${report.summary.total_cost_matic}`);
    console.log(`   → Total Cost (USD): $${report.summary.total_cost_usd}`);
  }
  
  console.log("\n⏱️ Performance:");
  console.log(`   → Average Component Duration: ${formatDuration(report.summary.average_component_duration_seconds)}`);
  
  if (report.errors.length > 0) {
    console.log("\n❌ Errors:");
    report.errors.forEach((err, index) => {
      console.log(`   ${index + 1}. ${err.component_id}: ${err.message}`);
    });
  }
  
  console.log("\n" + "=".repeat(70));
}

/**
 * Вывести детали компонента в консоль
 * @param {Object} componentReport - Component report
 */
function printComponentDetails(componentReport) {
  console.log(`\n📦 Component: ${componentReport.component_id}`);
  console.log(`   Status: ${componentReport.status}`);
  
  if (componentReport.duration_seconds) {
    console.log(`   Duration: ${formatDuration(componentReport.duration_seconds)}`);
  }
  
  if (componentReport.metadata.scientific_title) {
    console.log(`   Scientific Name: ${componentReport.metadata.scientific_title}`);
  }
  
  console.log(`   Forms: ${componentReport.metadata.forms_count}`);
  console.log(`   Features (common): ${componentReport.metadata.features_common_count}`);
  console.log(`   Languages: ${componentReport.metadata.languages_count}`);
  
  if (componentReport.arweave.root_cid) {
    console.log(`   Root CID: ${componentReport.arweave.root_cid}`);
    console.log(`   Files Uploaded: ${componentReport.arweave.total_files}`);
    console.log(`   Size: ${formatBytes(componentReport.arweave.total_size_bytes)}`);
  }
  
  if (componentReport.blockchain.component_id) {
    console.log(`   Blockchain ID: ${componentReport.blockchain.component_id}`);
    console.log(`   TX Hash: ${componentReport.blockchain.registration_tx}`);
    console.log(`   Gas Used: ${componentReport.blockchain.total_gas_used.toLocaleString()}`);
  }
}

// ====================================================================
// 🛠️ HELPERS
// ====================================================================

/**
 * Форматирование байтов для вывода
 * @param {number} bytes - Размер в байтах
 * @returns {string} Formatted string (e.g. "1.5 MB")
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Форматирование длительности
 * @param {number} seconds - Длительность в секундах
 * @returns {string} Formatted string (e.g. "2m 30s")
 */
function formatDuration(seconds) {
  if (!seconds) return '0s';
  
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  
  if (mins === 0) {
    return `${secs}s`;
  }
  
  return `${mins}m ${secs}s`;
}

// ====================================================================
// 🎯 EXPORTS
// ====================================================================

module.exports = {
  // Report lifecycle
  createReport,
  loadReport,
  saveReport,
  finalizeReport,
  
  // Global dictionaries
  reportGlobalDictionaries,
  
  // Component tracking
  createComponentReport,
  startComponentTracking,
  completeComponentTracking,
  failComponentTracking,
  
  // Metrics
  addArweaveMetrics,
  addBlockchainMetrics,
  addComponentMetadata,
  extractMetricsFromState,
  
  // Summary
  updateSummary,
  
  // Utilities
  getReportPath,
  reportExists,
  getReportSize,
  
  // Visualization
  printSummary,
  printComponentDetails,
  formatBytes,
  formatDuration
};

