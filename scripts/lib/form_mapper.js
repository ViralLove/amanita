/**
 * 🗺️ Form Mapper Module
 * 
 * Мапинг форм продуктов из CSV на стандартные формы из словаря
 * 
 * @module form_mapper
 * @version 1.0.0
 * @date 2025-01-12
 */

const fs = require('fs');
const path = require('path');

// Загружаем стандартный словарь форм
let STANDARD_FORMS = {};

try {
  const formsPath = path.join(__dirname, '../../bot/catalog/component_forms.json');
  const formsData = JSON.parse(fs.readFileSync(formsPath, 'utf8'));
  STANDARD_FORMS = formsData.forms || {};
  console.log(`📚 Loaded ${Object.keys(STANDARD_FORMS).length} standard forms from dictionary`);
} catch (error) {
  console.warn(`⚠️ Could not load standard forms dictionary: ${error.message}`);
  console.warn(`   Using fallback forms list`);
  STANDARD_FORMS = {
    "dried": { "en": "Dried" },
    "powder": { "en": "Powder" },
    "extract": { "en": "Extract" },
    "tincture": { "en": "Tincture" },
    "capsules": { "en": "Capsules" },
    "tea": { "en": "Tea" }
  };
}

// Мапинг известных несоответствий
const FORM_MAPPING = {
  "mixed slices": "dried",
  "sliced caps and gills": "dried",
  "whole caps": "dried",
  "closed hat": "dried",
  "broken caps": "dried",
  "collapsed hats": "dried",
  "premium caps": "dried",
  "whole": "dried",
  "chunks": "dried",
  "dried whole": "dried",
  "whole dried": "dried",
  "dried powder": "powder",
  "dried strips": "dried",
  "flower": "dried",
  "flowers": "dried",
  "unknown": "dried",
  "tinctura": "tincture",
  "tintura": "tincture",
  "ekstrakt": "extract",
  "extrakt": "extract",
  "kapsules": "capsules",
  "capsule": "capsules",
};

/**
 * Мапинг CSV form → стандартная форма из словаря
 * @param {string} csvForm - Форма из CSV
 * @param {string} biounit_id - ID компонента (для контекста)
 * @returns {Object} { standard_form, original_form, mapping_type, confidence, note }
 */
function mapFormToStandard(csvForm, biounit_id) {
  if (!csvForm || csvForm.trim() === '') {
    console.warn(`⚠️ Empty form for ${biounit_id}, using "dried" as fallback`);
    return {
      standard_form: 'dried',
      original_form: csvForm || '',
      mapping_type: 'fallback_empty',
      confidence: 0.3,
      note: 'Empty form, defaulted to "dried". Manual review required.'
    };
  }
  
  const lowerForm = csvForm.toLowerCase().trim();
  const standardKeys = Object.keys(STANDARD_FORMS);
  
  // 1. Точное совпадение (case-insensitive)
  if (standardKeys.includes(lowerForm)) {
    return {
      standard_form: lowerForm,
      original_form: csvForm,
      mapping_type: 'exact_match',
      confidence: 1.0,
      note: 'Exact match with standard dictionary'
    };
  }
  
  // 2. Известный мапинг
  if (FORM_MAPPING[lowerForm]) {
    return {
      standard_form: FORM_MAPPING[lowerForm],
      original_form: csvForm,
      mapping_type: 'known_mapping',
      confidence: 0.95,
      note: `Mapped "${csvForm}" → "${FORM_MAPPING[lowerForm]}"`
    };
  }
  
  // 3. Частичное совпадение (substring)
  for (const standardForm of standardKeys) {
    if (lowerForm.includes(standardForm)) {
      return {
        standard_form: standardForm,
        original_form: csvForm,
        mapping_type: 'substring_match',
        confidence: 0.8,
        note: `Substring match: "${csvForm}" contains "${standardForm}"`
      };
    }
    
    if (standardForm.includes(lowerForm)) {
      return {
        standard_form: standardForm,
        original_form: csvForm,
        mapping_type: 'substring_match',
        confidence: 0.75,
        note: `Substring match: "${standardForm}" contains "${csvForm}"`
      };
    }
  }
  
  // 4. Fallback на "dried"
  console.warn(`⚠️ Unknown form "${csvForm}" for ${biounit_id}, using "dried" as fallback`);
  
  return {
    standard_form: 'dried',
    original_form: csvForm,
    mapping_type: 'fallback',
    confidence: 0.5,
    note: `Unknown form, defaulted to "dried". Manual review recommended.`
  };
}

/**
 * Генерация отчета о мапинге форм
 * @param {Array<Object>} mappings - Массив результатов мапинга
 * @returns {Object} Статистика мапинга
 */
function generateFormMappingReport(mappings) {
  const stats = {
    total: mappings.length,
    exact_match: 0,
    known_mapping: 0,
    substring_match: 0,
    fallback: 0,
    fallback_empty: 0,
    unique_forms: new Set(),
    mappings_by_confidence: {
      high: [],   // >= 0.9
      medium: [], // 0.7-0.9
      low: []     // < 0.7
    },
    all_mappings: []
  };
  
  for (const mapping of mappings) {
    // Подсчет по типам
    stats[mapping.mapping_type] = (stats[mapping.mapping_type] || 0) + 1;
    stats.unique_forms.add(mapping.standard_form);
    stats.all_mappings.push(mapping);
    
    // Распределение по confidence
    if (mapping.confidence >= 0.9) {
      stats.mappings_by_confidence.high.push(mapping);
    } else if (mapping.confidence >= 0.7) {
      stats.mappings_by_confidence.medium.push(mapping);
    } else {
      stats.mappings_by_confidence.low.push(mapping);
    }
  }
  
  stats.unique_forms = Array.from(stats.unique_forms);
  
  return stats;
}

module.exports = {
  mapFormToStandard,
  generateFormMappingReport,
  STANDARD_FORMS
};

