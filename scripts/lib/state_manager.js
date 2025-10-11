/**
 * 📊 State Management Module
 * 
 * Управление state для компонентов и batch операций
 * Поддерживает resume capability и прогресс tracking
 * 
 * @version 1.0.0
 * @date 2025-10-09
 */

const fs = require('fs');
const path = require('path');

// ====================================================================
// 🔹 COMPONENT STATE MANAGEMENT
// ====================================================================

/**
 * Загрузить state компонента из файла
 * @param {string} componentDir - Директория компонента
 * @param {string} network - Название сети
 * @returns {Object} State объект или новый state
 */
function loadComponentState(componentDir, network) {
  const stateFile = path.join(componentDir, `_upload_state_${network}.json`);
  
  console.log(`💾 Загрузка component state: ${path.basename(componentDir)}`);
  
  if (fs.existsSync(stateFile)) {
    try {
      const stateData = fs.readFileSync(stateFile, 'utf8');
      const state = JSON.parse(stateData);
      
      console.log(`✅ State загружен`);
      console.log(`   → Шагов завершено: ${state.steps_completed.length}`);
      
      if (state.steps_completed.length > 0) {
        console.log(`   → Последние: ${state.steps_completed.slice(-3).join(', ')}`);
      }
      
      return state;
    } catch (error) {
      console.warn(`⚠️ Ошибка загрузки state:`, error.message);
      console.warn(`   → Создаем новый state`);
    }
  } else {
    console.log(`🆕 State файл не найден, создаем новый`);
  }
  
  // Возвращаем новый state
  return createComponentState(componentDir, network);
}

/**
 * Создать новый state для компонента
 * @param {string} componentDir - Директория компонента
 * @param {string} network - Название сети
 * @returns {Object} Новый state объект
 */
function createComponentState(componentDir, network) {
  const componentId = path.basename(componentDir);
  
  return {
    component_id: componentId,
    network: network,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    steps_completed: [],
    simple_fields: {},
    complex_fields: {},
    shareable_data: {},
    root_metadata: {},
    contract_registration: {}
  };
}

/**
 * Сохранить state компонента в файл
 * @param {string} componentDir - Директория компонента
 * @param {string} network - Название сети
 * @param {Object} state - State объект для сохранения
 */
function saveComponentState(componentDir, network, state) {
  console.log(`💾 Сохранение component state...`);
  
  try {
    // Обновляем timestamp
    state.updated_at = new Date().toISOString();
    
    // Проверяем существование директории
    if (!fs.existsSync(componentDir)) {
      console.log(`📁 Создаем директорию: ${componentDir}`);
      fs.mkdirSync(componentDir, { recursive: true });
    }
    
    // Сохраняем state
    const stateFile = path.join(componentDir, `_upload_state_${network}.json`);
    // BigInt replacer для JSON.stringify
    const replacer = (key, value) => 
        typeof value === 'bigint' ? value.toString() : value;
    fs.writeFileSync(stateFile, JSON.stringify(state, replacer, 2), 'utf8');
    
    console.log(`✅ State сохранен`);
    console.log(`   → Шагов завершено: ${state.steps_completed.length}`);
    
  } catch (error) {
    console.error(`❌ Ошибка сохранения state:`, error.message);
    throw error;
  }
}

/**
 * Проверить, был ли шаг уже выполнен
 * @param {Object} state - State объект
 * @param {string} stepName - Название шага
 * @returns {boolean} true если шаг уже выполнен
 */
function isStepCompleted(state, stepName) {
  if (!state || !state.steps_completed) {
    return false;
  }
  
  return state.steps_completed.includes(stepName);
}

/**
 * Проверить нужно ли выполнять blockchain регистрацию (Step 6)
 * @param {Object} componentState - Component state объект
 * @param {boolean} verbose - Детальное логирование
 * @returns {boolean} True если Step 6 нужно выполнить
 */
function needsBlockchainRegistration(componentState, verbose = false) {
  const componentId = componentState.component_id || 'unknown';
  
  if (verbose) {
    console.log(`\n🔍 Проверка needsBlockchainRegistration для ${componentId}:`);
    console.log(`   → steps_completed:`, componentState.steps_completed);
    console.log(`   → contract_registration:`, componentState.contract_registration);
    console.log(`   → root_metadata.cid:`, componentState.root_metadata?.cid);
  }
  
  // Если шаг уже выполнен - не нужно
  if (componentState.steps_completed.includes('component_registered')) {
    if (verbose) console.log(`   ✅ Step 6 уже выполнен - SKIP`);
    return false;
  }
  
  // Если есть root metadata CID - можно регистрировать
  if (componentState.root_metadata && componentState.root_metadata.cid) {
    if (verbose) console.log(`   ✅ CID есть, contract_registered НЕТ - НУЖНА РЕГИСТРАЦИЯ!`);
    return true;
  }
  
  if (verbose) console.log(`   ❌ CID отсутствует - невозможно регистрировать`);
  return false;
}

/**
 * Отметить шаг как выполненный
 * @param {Object} state - State объект
 * @param {string} stepName - Название шага
 */
function markStepCompleted(state, stepName) {
  // Инициализируем массив если не существует
  if (!state.steps_completed) {
    state.steps_completed = [];
  }
  
  // Проверяем, что шаг еще не добавлен (избегаем дубликатов)
  if (!state.steps_completed.includes(stepName)) {
    state.steps_completed.push(stepName);
    console.log(`✅ Шаг "${stepName}" отмечен как выполненный`);
  } else {
    console.log(`⚠️ Шаг "${stepName}" уже был отмечен ранее`);
  }
}

/**
 * Получить прогресс выполнения компонента
 * @param {Object} state - State объект
 * @param {number} totalSteps - Общее количество шагов (по умолчанию 6)
 * @returns {Object} { completed, total, percentage }
 */
function getComponentProgress(state, totalSteps = 6) {
  const completed = state.steps_completed?.length || 0;
  const percentage = Math.round((completed / totalSteps) * 100);
  
  return {
    completed,
    total: totalSteps,
    percentage
  };
}

// ====================================================================
// 🔹 BATCH STATE MANAGEMENT
// ====================================================================

/**
 * Создать новый batch state
 * @param {Object} config - Конфигурация
 * @param {string} config.network - Название сети
 * @param {string} config.deployer - Адрес deployer
 * @param {boolean} config.dryRun - Режим dry-run
 * @param {boolean} config.uploadShareable - Загрузка shareable data
 * @param {Array<string>} config.components - Список component IDs
 * @returns {Object} Новый batch state
 */
function createBatchState(config) {
  const sessionId = `upload_${new Date().toISOString().replace(/[:.]/g, '-')}`;
  
  return {
    session: {
      session_id: sessionId,
      network: config.network,
      started_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      deployer: config.deployer,
      dry_run: config.dryRun,
      upload_shareable: config.uploadShareable,
      version: "1.0.0"
    },
    
    global_state: {
      shareable_uploaded: false,
      features_cid: null,
      forms_cid: null,
      features_version: 1,
      forms_version: 1,
      uploaded_at: null
    },
    
    queue: {
      total: config.components.length,
      pending: [...config.components],
      in_progress: null,
      completed: [],
      failed: [],
      skipped: []
    },
    
    components: initializeComponentsData(config.components),
    
    metrics: {
      components_processed: 0,
      components_remaining: config.components.length,
      total_files_uploaded: 0,
      total_arweave_size_bytes: 0,
      total_gas_used: 0,
      total_cost_matic: "0",
      estimated_time_remaining_seconds: null
    }
  };
}

/**
 * Инициализация данных компонентов в batch state
 * @param {Array<string>} componentIds - Список component IDs
 * @returns {Object} Объект с компонентами
 */
function initializeComponentsData(componentIds) {
  const components = {};
  
  for (const id of componentIds) {
    components[id] = {
      status: "pending",
      started_at: null,
      completed_at: null,
      duration_seconds: null,
      steps_completed: [],
      blockchain: {},
      arweave: {},
      metrics: {},
      error: null
    };
  }
  
  return components;
}

/**
 * Загрузить batch state из файла
 * @param {string} componentsDir - Базовая директория компонентов
 * @param {string} network - Название сети
 * @returns {Object|null} Batch state или null если не найден
 */
function loadBatchState(componentsDir, network) {
  const stateFile = path.join(componentsDir, `_batch_state_${network}.json`);
  
  console.log(`💾 Загрузка batch state...`);
  
  if (fs.existsSync(stateFile)) {
    try {
      const stateData = fs.readFileSync(stateFile, 'utf8');
      const state = JSON.parse(stateData);
      
      console.log(`✅ Batch state загружен: ${state.session.session_id}`);
      console.log(`   → Обработано: ${state.metrics.components_processed}/${state.queue.total}`);
      console.log(`   → Pending: ${state.queue.pending.length}`);
      console.log(`   → Failed: ${state.queue.failed.length}`);
      
      return state;
    } catch (error) {
      console.warn(`⚠️ Ошибка загрузки batch state:`, error.message);
      return null;
    }
  }
  
  console.log(`🆕 Batch state файл не найден`);
  return null;
}

/**
 * Сохранить batch state в файл
 * @param {string} componentsDir - Базовая директория компонентов
 * @param {Object} state - Batch state объект
 */
function saveBatchState(componentsDir, state) {
  console.log(`💾 Сохранение batch state...`);
  
  try {
    // Обновляем timestamp
    state.session.updated_at = new Date().toISOString();
    
    // Проверяем существование директории
    if (!fs.existsSync(componentsDir)) {
      fs.mkdirSync(componentsDir, { recursive: true });
    }
    
    // Сохраняем state
    const stateFile = path.join(
      componentsDir,
      `_batch_state_${state.session.network}.json`
    );
    // BigInt replacer для JSON.stringify
    const replacer = (key, value) => 
        typeof value === 'bigint' ? value.toString() : value;
    fs.writeFileSync(stateFile, JSON.stringify(state, replacer, 2), 'utf8');
    
    console.log(`✅ Batch state сохранен`);
    console.log(`   → Обработано: ${state.metrics.components_processed}/${state.queue.total}`);
    
  } catch (error) {
    console.error(`❌ Ошибка сохранения batch state:`, error.message);
    throw error;
  }
}

/**
 * Получить следующий компонент для обработки
 * @param {Object} state - Batch state
 * @returns {string|null} Component ID или null
 */
function getNextComponent(state) {
  if (state.queue.pending.length === 0) {
    return null;
  }
  
  return state.queue.pending[0];
}

/**
 * Отметить компонент как "в процессе"
 * @param {Object} state - Batch state
 * @param {string} componentId - Component ID
 */
function markComponentInProgress(state, componentId) {
  // Удалить из pending
  state.queue.pending = state.queue.pending.filter(id => id !== componentId);
  
  // Установить in_progress
  state.queue.in_progress = componentId;
  
  // Обновить компонент data
  state.components[componentId].status = "in_progress";
  state.components[componentId].started_at = new Date().toISOString();
}

/**
 * Отметить компонент как завершенный
 * @param {Object} state - Batch state
 * @param {string} componentId - Component ID
 * @param {Object} results - Результаты загрузки
 */
function markComponentCompleted(state, componentId, results) {
  // Очистить in_progress
  state.queue.in_progress = null;
  
  // Добавить в completed
  state.queue.completed.push(componentId);
  
  // Обновить компонент data
  const component = state.components[componentId];
  component.status = "completed";
  component.completed_at = new Date().toISOString();
  
  // Расчет длительности
  const start = new Date(component.started_at);
  const end = new Date(component.completed_at);
  component.duration_seconds = Math.round((end - start) / 1000);
  
  // Сохранить результаты
  Object.assign(component, results);
  
  // Обновить метрики
  updateBatchMetrics(state);
}

/**
 * Отметить компонент как failed
 * @param {Object} state - Batch state
 * @param {string} componentId - Component ID
 * @param {Error} error - Объект ошибки
 */
function markComponentFailed(state, componentId, error) {
  // Очистить in_progress
  state.queue.in_progress = null;
  
  // Добавить в failed
  state.queue.failed.push(componentId);
  
  // Обновить компонент data
  const component = state.components[componentId];
  component.status = "failed";
  component.completed_at = new Date().toISOString();
  component.error = {
    message: error.message,
    stack: error.stack,
    timestamp: new Date().toISOString()
  };
  
  // Обновить метрики
  updateBatchMetrics(state);
}

/**
 * Пропустить компонент
 * @param {Object} state - Batch state
 * @param {string} componentId - Component ID
 * @param {string} reason - Причина пропуска
 */
function skipComponent(state, componentId, reason) {
  state.queue.pending = state.queue.pending.filter(id => id !== componentId);
  state.queue.skipped.push(componentId);
  
  state.components[componentId].status = "skipped";
  state.components[componentId].skip_reason = reason;
}

/**
 * Отметить shareable data как загруженные
 * @param {Object} state - Batch state
 * @param {string} featuresCID - CID features.json
 * @param {string} formsCID - CID component_forms.json
 */
function markShareableDataUploaded(state, featuresCID, formsCID) {
  state.global_state.shareable_uploaded = true;
  state.global_state.features_cid = featuresCID;
  state.global_state.forms_cid = formsCID;
  state.global_state.uploaded_at = new Date().toISOString();
  
  console.log(`✅ Shareable data отмечены как загруженные`);
  console.log(`   → Features CID: ${featuresCID}`);
  console.log(`   → Forms CID: ${formsCID}`);
}

/**
 * Проверить, загружены ли shareable data
 * @param {Object} state - Batch state
 * @returns {boolean} true если загружены
 */
function isShareableDataUploaded(state) {
  return state.global_state.shareable_uploaded === true;
}

/**
 * Обновить агрегированные метрики в batch state
 * @param {Object} state - Batch state
 */
function updateBatchMetrics(state) {
  const completed = state.queue.completed.length;
  const total = state.queue.total;
  
  state.metrics.components_processed = completed;
  state.metrics.components_remaining = total - completed;
  
  // Агрегировать метрики из компонентов
  let totalFiles = 0;
  let totalSize = 0;
  let totalGas = 0;
  let totalCost = 0;
  
  for (const componentId of state.queue.completed) {
    const comp = state.components[componentId];
    
    if (comp.metrics) {
      totalFiles += comp.metrics.files_uploaded || 0;
      totalGas += comp.metrics.total_gas_used || 0;
      totalCost += parseFloat(comp.metrics.total_cost_matic || 0);
    }
    
    if (comp.arweave) {
      totalSize += comp.arweave.total_size_bytes || 0;
    }
  }
  
  state.metrics.total_files_uploaded = totalFiles;
  state.metrics.total_arweave_size_bytes = totalSize;
  state.metrics.total_gas_used = totalGas;
  state.metrics.total_cost_matic = totalCost.toFixed(4);
  
  // Оценка оставшегося времени
  if (completed > 0) {
    const avgDuration = calculateAverageDuration(state);
    state.metrics.estimated_time_remaining_seconds = 
      Math.round(avgDuration * state.metrics.components_remaining);
  }
}

/**
 * Расчет средней длительности обработки компонента
 * @param {Object} state - Batch state
 * @returns {number} Средняя длительность в секундах
 */
function calculateAverageDuration(state) {
  const durations = state.queue.completed
    .map(id => state.components[id].duration_seconds)
    .filter(d => d !== null && d !== undefined);
  
  if (durations.length === 0) {
    return 0;
  }
  
  const sum = durations.reduce((acc, d) => acc + d, 0);
  return sum / durations.length;
}

/**
 * Получить прогресс batch операции
 * @param {Object} state - Batch state
 * @returns {Object} Progress info
 */
function getBatchProgress(state) {
  const total = state.queue.total;
  const completed = state.queue.completed.length;
  const failed = state.queue.failed.length;
  const inProgress = state.queue.in_progress ? 1 : 0;
  const pending = state.queue.pending.length;
  
  const percentage = Math.round((completed / total) * 100);
  
  return {
    total,
    completed,
    failed,
    inProgress,
    pending,
    percentage,
    estimatedTimeRemaining: state.metrics.estimated_time_remaining_seconds
  };
}

// ====================================================================
// 🎯 EXPORTS
// ====================================================================

module.exports = {
  // Component state
  loadComponentState,
  createComponentState,
  saveComponentState,
  isStepCompleted,
  markStepCompleted,
  getComponentProgress,
  needsBlockchainRegistration,
  
  // Batch state
  createBatchState,
  loadBatchState,
  saveBatchState,
  getNextComponent,
  markComponentInProgress,
  markComponentCompleted,
  markComponentFailed,
  skipComponent,
  markShareableDataUploaded,
  isShareableDataUploaded,
  updateBatchMetrics,
  getBatchProgress
};

