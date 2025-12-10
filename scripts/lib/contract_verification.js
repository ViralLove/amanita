/**
 * 🔍 Contract Verification Module
 * 
 * Унифицированная проверка соответствия state файлов и контрактов
 * Используется для обнаружения несоответствий после перезапуска ноды
 * 
 * @version 1.0.0
 * @date 2025-11-24
 */

const stateManager = require('./state_manager');
const utils = require('./upload_utils');
const { ethers } = require('hardhat');

// ====================================================================
// 🔹 STEP VERIFICATION
// ====================================================================

/**
 * Проверить соответствие state и контракта для шага
 * @param {Object} options - Параметры проверки
 * @param {Object} options.state - Component state
 * @param {string} options.stepName - Название шага ('simple_fields_uploaded', 'complex_fields_uploaded')
 * @param {Function} options.contractCheckFn - Функция проверки контракта (async)
 * @returns {Promise<{isComplete: boolean, isConsistent: boolean, missingItems: Array, stateData: Object|null}>}
 */
async function verifyStepCompletion(options) {
  const { state, stepName, contractCheckFn } = options;
  
  // Валидация входных параметров
  if (!state) {
    throw new Error('State object is required');
  }
  if (!stepName) {
    throw new Error('Step name is required');
  }
  if (!contractCheckFn || typeof contractCheckFn !== 'function') {
    throw new Error('contractCheckFn must be an async function');
  }
  
  // 1. Проверяем, отмечен ли шаг в state
  const isCompletedInState = stateManager.isStepCompleted(state, stepName);
  
  if (!isCompletedInState) {
    return {
      isComplete: false,
      isConsistent: true, // Нет несоответствия, шаг просто не выполнен
      missingItems: [],
      stateData: null
    };
  }
  
  // 2. Проверяем наличие данных в контракте
  let contractCheckResult;
  try {
    contractCheckResult = await contractCheckFn();
  } catch (error) {
    // Если проверка контракта упала, считаем это несоответствием
    console.warn(`⚠️ Contract check failed for step ${stepName}: ${error.message}`);
    return {
      isComplete: true,
      isConsistent: false,
      missingItems: ['*'], // Специальный маркер для полной проверки
      stateData: getStateDataForStep(state, stepName)
    };
  }
  
  // 3. Сравниваем state и контракт
  const isConsistent = contractCheckResult.allPresent === true;
  const missingItems = contractCheckResult.missing || [];
  
  return {
    isComplete: true,
    isConsistent,
    missingItems,
    stateData: getStateDataForStep(state, stepName)
  };
}

// ====================================================================
// 🔹 CONTRACT CHECKERS
// ====================================================================

/**
 * Проверить наличие Simple Fields в контракте
 * @param {Object} context - Upload context
 * @param {Object} context.contracts - Contract instances
 * @param {Object} context.contracts.amanitaInternational - AmanitaInternational contract
 * @param {string} context.biounit_id - Component biounit_id (optional, not used for simple fields)
 * @returns {Promise<{allPresent: boolean, missing: Array<string>, present: Object}>}
 */
async function checkSimpleFieldsInContract(context) {
  if (!context || !context.contracts || !context.contracts.amanitaInternational) {
    throw new Error('Invalid context: contracts.amanitaInternational is required');
  }
  
  const amanitaIntl = context.contracts.amanitaInternational;
  
  const fields = [
    { key: 'ComponentDescription.title', label: 'title' },
    { key: 'DosageInstruction.description', label: 'dosage' }
  ];
  
  const results = {
    allPresent: true,
    missing: [],
    present: {}
  };
  
  for (const field of fields) {
    try {
      const cid = await amanitaIntl.getSimpleFieldCID(field.key);
      
      // Проверяем, что CID валиден (не пустой и не ZeroAddress)
      if (!cid || cid === '' || cid === ethers.ZeroAddress) {
        results.allPresent = false;
        results.missing.push(field.label);
      } else {
        results.present[field.label] = cid;
      }
    } catch (error) {
      // Если метод упал, считаем поле отсутствующим
      console.warn(`⚠️ Failed to check ${field.key}: ${error.message}`);
      results.allPresent = false;
      results.missing.push(field.label);
    }
  }
  
  return results;
}

/**
 * Проверить наличие Complex Fields в контракте
 * @param {Object} context - Upload context
 * @param {Object} context.contracts - Contract instances
 * @param {Object} context.contracts.amanitaInternational - AmanitaInternational contract
 * @param {string} context.biounit_id - Component biounit_id (required)
 * @param {Array<string>} context.supportedLanguages - Supported languages (optional, falls back to utils)
 * @returns {Promise<{allPresent: boolean, missing: Array<string>, present: Object}>}
 */
async function checkComplexFieldsInContract(context) {
  if (!context || !context.contracts || !context.contracts.amanitaInternational) {
    throw new Error('Invalid context: contracts.amanitaInternational is required');
  }
  if (!context.biounit_id) {
    throw new Error('Invalid context: biounit_id is required');
  }
  
  const amanitaIntl = context.contracts.amanitaInternational;
  const className = `ComponentDescription.${context.biounit_id}`;
  const languages = context.supportedLanguages || utils.getSupportedLanguages();
  
  const results = {
    allPresent: true,
    missing: [],
    present: {}
  };
  
  for (const lang of languages) {
    try {
      const cid = await amanitaIntl.getComplexFieldCID(className, lang);
      
      // Проверяем, что CID валиден (не пустой и не ZeroAddress)
      if (!cid || cid === '' || cid === ethers.ZeroAddress) {
        results.allPresent = false;
        results.missing.push(lang);
      } else {
        results.present[lang] = cid;
      }
    } catch (error) {
      // Если метод упал, считаем язык отсутствующим
      console.warn(`⚠️ Failed to check ${className}.${lang}: ${error.message}`);
      results.allPresent = false;
      results.missing.push(lang);
    }
  }
  
  return results;
}

// ====================================================================
// 🔹 STATE DATA EXTRACTION
// ====================================================================

/**
 * Получить данные из state для конкретного шага
 * @param {Object} state - Component state
 * @param {string} stepName - Название шага
 * @returns {Object|null} Данные из state или null
 */
function getStateDataForStep(state, stepName) {
  if (!state) {
    return null;
  }
  
  switch (stepName) {
    case 'simple_fields_uploaded':
      return state.simple_fields || null;
      
    case 'complex_fields_uploaded':
      return state.complex_fields || null;
      
    case 'root_metadata_uploaded':
      return state.root_metadata?.cid || null;
      
    default:
      return null;
  }
}

// ====================================================================
// 🎯 EXPORTS
// ====================================================================

module.exports = {
  verifyStepCompletion,
  checkSimpleFieldsInContract,
  checkComplexFieldsInContract,
  getStateDataForStep
};

