/**
 * 📤 Upload Steps Module
 * 
 * Модуляризованные шаги загрузки органических компонентов
 * Переработаны для поддержки context object и batch processing
 * 
 * @version 1.0.0
 * @date 2025-10-09
 */

const utils = require('./upload_utils');
const stateManager = require('./state_manager');
const contractVerification = require('./contract_verification');

// ====================================================================
// 🔹 STEP 1: UPLOAD SIMPLE FIELDS
// ====================================================================

/**
 * Загрузка Simple Fields в Arweave и сохранение CID в контракте
 * 
 * @notice Ownership-based Access Control (обновлено 2025-01-12)
 * @dev setSimpleFieldCID вызывается ОТ SELLER (context.seller.address)
 * @dev Seller становится owner поля при первом создании
 * @dev После обновления AmanitaInternational с SELLER_ROLE support
 * 
 * @param {Object} context - Upload context
 * @param {string} context.biounit_id - biounit_id компонента (текстовое значение, например "amanita_muscaria")
 * @param {string} context.componentDir - Путь к директории компонента
 * @param {string} context.network - Название сети
 * @param {boolean} context.dryRun - Режим dry-run
 * @param {Object} context.contracts - Контракты (amanitaInternational, etc.)
 * @param {Object} context.arweave - Arweave client + key
 * @param {Object} context.ethersProvider - Ethers.js provider instance
 * @param {Object} context.seller - Seller account (owner компонента, с signer)
 * @param {Object} context.deployer - Deployer account (для ADMIN операций, с signer)
 * @param {Object} state - Component state
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<Object>} Маппинг field → CID
 */
async function uploadSimpleFields(context, state, onProgress = null) {
  console.log("\n🔹 ШАГ 1: Загрузка Simple Fields");
  
  // ✅ НОВОЕ: Проверка флага useExistingCids
  if (context.useExistingCids) {
    console.log("🔍 [USE_EXISTING_CIDS] Проверяем наличие существующих CID в state...");
    
    const existingSimpleFields = state.arweave?.simple_fields || {};
    const hasTitleCID = existingSimpleFields.title?.cid;
    const hasDosageCID = existingSimpleFields.dosage_types?.cid;
    
    if (hasTitleCID && hasDosageCID) {
      console.log("✅ [USE_EXISTING_CIDS] Найдены существующие CID:");
      console.log(`   → title.cid: ${hasTitleCID}`);
      console.log(`   → dosage_types.cid: ${hasDosageCID}`);
      console.log("✅ [USE_EXISTING_CIDS] Используем существующие CID, пропускаем загрузку");
      return existingSimpleFields;
    } else {
      const missing = [];
      if (!hasTitleCID) missing.push('title');
      if (!hasDosageCID) missing.push('dosage_types');
      console.warn(`⚠️ [USE_EXISTING_CIDS] CID отсутствуют для: ${missing.join(', ')}`);
      console.warn(`   🔄 Fallback: выполняем загрузку в Arweave...`);
      // Продолжаем обычную логику загрузки (fallback)
    }
  }
  
  // ✅ CHANGE (2025-12-02): Check arweave section for steps
  const verification = await contractVerification.verifyStepCompletion({
    state: state.arweave,  // ← Pass arweave section instead of full state
    stepName: 'simple_fields_uploaded',
    contractCheckFn: () => contractVerification.checkSimpleFieldsInContract(context)
  });
  
  if (verification.isComplete && verification.isConsistent) {
    console.log("✅ Шаг уже выполнен, данные подтверждены в контракте");
    return verification.stateData;
  }
  
  if (verification.isComplete && !verification.isConsistent) {
    console.warn(`❌ НЕСООТВЕТСТВИЕ: State file говорит "загружено", но данных нет в контракте`);
    console.warn(`   Отсутствующие поля: ${verification.missingItems.join(', ')}`);
    console.warn(`   💡 Вероятная причина: Node был перезапущен, blockchain state сброшен`);
    console.warn(`   🔧 Восстанавливаем из state в контракт...`);
    
    // Восстанавливаем отсутствующие поля из state в контракт
    await restoreSimpleFieldsToContract(context, state, verification.missingItems);
    
    // Возвращаем данные из state (они теперь в контракте)
    return verification.stateData;
  }
  
  const simpleFieldCIDs = {};
  
  try {
    // 1. Загрузка ComponentDescription.title.json
    console.log("\n📝 1.1. ComponentDescription.title");
    
    if (onProgress) {
      onProgress({ step: 'simple_fields', substep: 'title', progress: 0, status: 'started' });
    }
    
    const titleFilePath = `simple_fields/${context.biounit_id}.ComponentDescription.title.json`;
    const titleData = utils.readJSON(context.componentDir, titleFilePath);
    
    const titleFilename = `${context.biounit_id}_ComponentDescription_title.json`;
    const titleResult = await uploadToArweave(
      context,
      titleData,
      titleFilename
    );
    
    const titleCID = titleResult.txId || titleResult; // Обратная совместимость
    
    simpleFieldCIDs.title = {
      cid: titleCID,
      url: titleResult.url || `https://arweave.net/${titleCID}`,
      size: titleResult.size || 0,
      label: "ComponentDescription.title",
      file_path: titleFilePath
    };
    
    // Сохраняем CID в контракте (если не dry-run)
    if (!context.dryRun && !context.arweaveOnly) {
      console.log("🔷 Сохраняем CID в AmanitaInternational (от seller)...");
      
      // ✅ Ownership: вызов от SELLER → seller становится owner поля
      const signer = context.seller.signer;
      const amanitaIntlWithSigner = context.contracts.amanitaInternational.connect(signer);
      
      const tx = await amanitaIntlWithSigner.setSimpleFieldCID(
        "ComponentDescription.title",
        titleCID
      );
      
      await tx.wait();
      console.log("✅ CID сохранен в контракте (owner: seller)");
    } else if (context.arweaveOnly) {
      console.log("🔷 [ARWEAVE_ONLY] Пропускаем сохранение в контракт");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
    }
    
    if (onProgress) {
      onProgress({ step: 'simple_fields', substep: 'title', progress: 50, status: 'completed' });
    }
    
    // 2. Загрузка DosageInstruction.description.json
    console.log("\n📝 1.2. DosageInstruction.description");
    
    if (onProgress) {
      onProgress({ step: 'simple_fields', substep: 'dosage', progress: 50, status: 'started' });
    }
    
    const dosageFilePath = `simple_fields/${context.biounit_id}.DosageInstruction.description.json`;
    const dosageData = utils.readJSON(context.componentDir, dosageFilePath);
    
    const dosageFilename = `${context.biounit_id}_DosageInstruction_description.json`;
    const dosageResult = await uploadToArweave(
      context,
      dosageData,
      dosageFilename
    );
    
    const dosageCID = dosageResult.txId || dosageResult;
    
    simpleFieldCIDs.dosage_types = {
      cid: dosageCID,
      url: dosageResult.url || `https://arweave.net/${dosageCID}`,
      size: dosageResult.size || 0,
      label: "DosageInstruction.description",
      file_path: dosageFilePath
    };
    
    // Сохраняем CID в контракте (если не dry-run)
    if (!context.dryRun && !context.arweaveOnly) {
      console.log("🔷 Сохраняем CID в AmanitaInternational (от seller)...");
      
      // ✅ Ownership: вызов от SELLER → seller становится owner поля
      const signer = context.seller.signer;
      const amanitaIntlWithSigner = context.contracts.amanitaInternational.connect(signer);
      
      const tx = await amanitaIntlWithSigner.setSimpleFieldCID(
        "DosageInstruction.description",
        dosageCID
      );
      
      await tx.wait();
      console.log("✅ CID сохранен в контракте (owner: seller)");
    } else if (context.arweaveOnly) {
      console.log("🔷 [ARWEAVE_ONLY] Пропускаем сохранение в контракт");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
    }
    
    if (onProgress) {
      onProgress({ step: 'simple_fields', substep: 'dosage', progress: 100, status: 'completed' });
    }
    
    // ✅ CHANGE (2025-12-02): Save to arweave section
    state.arweave.simple_fields = simpleFieldCIDs;
    stateManager.markStepCompleted(state.arweave, 'simple_fields_uploaded');
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log("\n✅ ШАГ 1 завершен: Simple Fields загружены");
    
    return simpleFieldCIDs;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 1:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 2: UPLOAD COMPLEX FIELDS
// ====================================================================

/**
 * Загрузка Complex Fields (переводы) в Arweave и сохранение CID в контракте
 * 
 * @notice Ownership-based Access Control (обновлено 2025-01-12)
 * @dev setComplexFieldCID вызывается ОТ SELLER (context.seller.address)
 * @dev Seller становится owner каждого перевода при первом создании
 * @dev После обновления AmanitaInternational с SELLER_ROLE support
 * 
 * @param {Object} context - Upload context
 * @param {Object} context.seller - Seller account (owner компонента)
 * @param {Object} state - Component state
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<Object>} Маппинг language → CID
 */
async function uploadComplexFields(context, state, onProgress = null) {
  console.log("\n🔹 ШАГ 2: Загрузка Complex Fields");
  
  // ✅ НОВОЕ: Проверка флага useExistingCids
  if (context.useExistingCids) {
    console.log("🔍 [USE_EXISTING_CIDS] Проверяем наличие существующих CID в state...");
    
    const existingComplexFields = state.arweave?.complex_fields || {};
    const languages = context.supportedLanguages || utils.getSupportedLanguages();
    const missingLanguages = [];
    
    // Проверяем наличие CID для каждого языка
    for (const lang of languages) {
      const langCID = existingComplexFields[lang]?.cid || 
                     (typeof existingComplexFields[lang] === 'string' ? existingComplexFields[lang] : null);
      
      if (!langCID) {
        missingLanguages.push(lang);
      }
    }
    
    if (missingLanguages.length === 0) {
      console.log("✅ [USE_EXISTING_CIDS] Найдены существующие CID для всех языков:");
      for (const lang of languages) {
        const langCID = existingComplexFields[lang]?.cid || existingComplexFields[lang];
        console.log(`   → ${lang}.cid: ${langCID?.substring(0, 20)}...`);
      }
      console.log("✅ [USE_EXISTING_CIDS] Используем существующие CID, пропускаем загрузку");
      return existingComplexFields;
    } else {
      console.warn(`⚠️ [USE_EXISTING_CIDS] CID отсутствуют для языков: ${missingLanguages.join(', ')}`);
      console.warn(`   🔄 Fallback: выполняем загрузку в Arweave...`);
      // Продолжаем обычную логику загрузки (fallback)
    }
  }
  
  // ✅ CHANGE (2025-12-02): Check arweave section for steps
  const verification = await contractVerification.verifyStepCompletion({
    state: state.arweave,  // ← Pass arweave section
    stepName: 'complex_fields_uploaded',
    contractCheckFn: () => contractVerification.checkComplexFieldsInContract(context)
  });
  
  if (verification.isComplete && verification.isConsistent) {
    console.log("✅ Шаг уже выполнен, данные подтверждены в контракте");
    return verification.stateData;
  }
  
  if (verification.isComplete && !verification.isConsistent) {
    console.warn(`❌ НЕСООТВЕТСТВИЕ: State file говорит "загружено", но данных нет в контракте`);
    console.warn(`   Отсутствующие языки: ${verification.missingItems.join(', ')}`);
    console.warn(`   💡 Вероятная причина: Node был перезапущен, blockchain state сброшен`);
    console.warn(`   🔧 Восстанавливаем из state в контракт...`);
    
    // Восстанавливаем отсутствующие языки из state в контракт
    await restoreComplexFieldsToContract(context, state, verification.missingItems);
    
    // Возвращаем данные из state (они теперь в контракте)
    return verification.stateData;
  }
  
  const complexFieldCIDs = {};
  const languages = context.supportedLanguages || utils.getSupportedLanguages();
  let processedCount = 0;
  
  try {
    // Цикл по всем поддерживаемым языкам
    for (const lang of languages) {
      console.log(`\n📝 2.${processedCount + 1}. ComponentDescription.${lang}`);
      
      if (onProgress) {
        const progress = Math.round((processedCount / languages.length) * 100);
        onProgress({ step: 'complex_fields', language: lang, progress, status: 'started' });
      }
      
      const filePath = `complex_fields/${context.biounit_id}.ComponentDescription.${lang}.json`;
      
      try {
        // ✅ OPTIMIZATION: Если данные уже в state (при повторной загрузке в контракт),
        // используем существующий CID из state вместо повторной загрузки в Arweave
        let descCID;
        let descResult;
        
        // ✅ CHANGE (2025-12-02): Check arweave.complex_fields
        const arweaveComplexFields = state.arweave?.complex_fields || state.complex_fields || {};
        
        if (arweaveComplexFields[lang]) {
          const existingCID = typeof arweaveComplexFields[lang] === 'string' 
            ? arweaveComplexFields[lang] 
            : arweaveComplexFields[lang]?.cid;
          
          if (existingCID) {
            console.log(`   ♻️ Используем существующий CID из state: ${existingCID.substring(0, 20)}...`);
            descCID = existingCID;
            descResult = {
              txId: existingCID,
              url: arweaveComplexFields[lang]?.url || `https://arweave.net/${existingCID}`,
              size: arweaveComplexFields[lang]?.size || 0
            };
          } else {
            // Нет CID в state - загружаем заново в Arweave
            const descData = utils.readJSON(context.componentDir, filePath);
            const filename = `${context.biounit_id}_ComponentDescription_${lang}.json`;
            descResult = await uploadToArweave(context, descData, filename);
            descCID = descResult.txId || descResult;
          }
        } else {
          // Нет данных в state - загружаем заново в Arweave
          const descData = utils.readJSON(context.componentDir, filePath);
          const filename = `${context.biounit_id}_ComponentDescription_${lang}.json`;
          descResult = await uploadToArweave(context, descData, filename);
          descCID = descResult.txId || descResult;
        }
        
        complexFieldCIDs[lang] = {
          cid: descCID,
          url: descResult.url || `https://arweave.net/${descCID}`,
          size: descResult.size || 0,
          label: "ComponentDescription",
          file_path: filePath
        };
        
        // Сохраняем CID в контракте (если не dry-run)
        if (!context.dryRun && !context.arweaveOnly) {
          console.log(`🔷 Сохраняем CID в AmanitaInternational (от seller, ${lang})...`);
          
          // ✅ Ownership: вызов от SELLER → seller становится owner перевода
          const signer = context.seller.signer;
          const amanitaIntlWithSigner = context.contracts.amanitaInternational.connect(signer);
          
          // ✅ FIX: Включаем biounit_id в className для уникальности ключа
          const classNameWithBiounitId = `ComponentDescription.${context.biounit_id}`;
          // Пример: "ComponentDescription.amanita_muscaria"
          // Результат в контракте: complexFieldCIDs["ComponentDescription.amanita_muscaria.ru"] = cid
          
          const tx = await amanitaIntlWithSigner.setComplexFieldCID(
            classNameWithBiounitId,  // ✅ С biounit_id → уникальный ключ для каждого компонента
            lang,
            descCID
          );
          
          await tx.wait();
          console.log(`✅ CID сохранен в контракте (owner: seller, ${lang}, key: ${classNameWithBiounitId}.${lang})`);
        } else if (context.arweaveOnly) {
          console.log("🔷 [ARWEAVE_ONLY] Пропускаем сохранение в контракт");
        } else {
          console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
        }
        
        processedCount++;
        
        if (onProgress) {
          const progress = Math.round((processedCount / languages.length) * 100);
          onProgress({ step: 'complex_fields', language: lang, progress, status: 'completed' });
        }
        
      } catch (fileError) {
        console.warn(`⚠️ Файл не найден или ошибка чтения: ${filePath}`);
        console.warn(`   Пропускаем язык: ${lang}`);
        // Продолжаем со следующим языком
      }
    }
    
    if (processedCount === 0) {
      throw new Error("Ни один файл complex fields не был загружен");
    }
    
    console.log(`\n📊 Обработано языков: ${processedCount} из ${languages.length}`);
    
    // ✅ CHANGE (2025-12-02): Save to arweave section
    state.arweave.complex_fields = complexFieldCIDs;
    stateManager.markStepCompleted(state.arweave, 'complex_fields_uploaded');
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log("\n✅ ШАГ 2 завершен: Complex Fields загружены");
    
    return complexFieldCIDs;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 2:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 3: UPLOAD SHAREABLE DATA
// ====================================================================

/**
 * Загрузка глобальных словарей (features, component_forms) в Arweave
 * @param {Object} context - Upload context
 * @param {Object} state - Component state (или batch state)
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<Object>} { featuresCID, formsCID }
 */
async function uploadShareableData(context, state, onProgress = null) {
  console.log("\n🔹 ШАГ 3: Загрузка глобальных словарей");
  
  // ✅ CHANGE (2025-12-02): Check arweave section
  const arweaveShareable = state.arweave?.shareable_data || state.shareable_data;
  if (arweaveShareable && arweaveShareable.featuresCID) {
    console.log("✅ Шаг уже выполнен (state), используем сохраненные данные");
    return arweaveShareable;
  }
  
  // Проверяем, загружены ли shareable data в контракт
  try {
    const existingData = await context.contracts.organicComponentRegistry.getShareableData();
    if (existingData.features_cid && existingData.features_cid !== '' && 
        existingData.component_forms_cid && existingData.component_forms_cid !== '') {
      console.log("✅ Shareable Data уже загружены в контракт (пропуск)");
      console.log(`   → Features CID: ${existingData.features_cid}`);
      console.log(`   → Forms CID: ${existingData.component_forms_cid}`);
      
      // ✅ CHANGE (2025-12-02): Save to arweave section
      const shareableData = {
        featuresCID: existingData.features_cid,
        formsCID: existingData.component_forms_cid,
        featuresVersion: existingData.features_version,
        formsVersion: existingData.forms_version
      };
      
      state.arweave.shareable_data = shareableData;
      stateManager.markStepCompleted(state.arweave, 'shareable_data_uploaded');
      stateManager.saveComponentState(context.componentDir, state);
      
      return shareableData;
    }
  } catch (checkError) {
    console.log(`   ℹ️ Не удалось проверить контракт, продолжаем загрузку: ${checkError.message}`);
  }
  
  try {
    // 1. Загрузка features.json
    console.log("\n📝 3.1. features.json");
    
    if (onProgress) {
      onProgress({ step: 'shareable_data', substep: 'features', progress: 0, status: 'started' });
    }
    
    const fs = require('fs');
    const path = require('path');
    
    const featuresPath = path.join(__dirname, '..', '..', 'bot', 'catalog', 'features.json');
    const featuresData = JSON.parse(fs.readFileSync(featuresPath, 'utf8'));
    
    const featuresResult = await uploadToArweave(
      context,
      featuresData,
      "features_global_dictionary.json"
    );
    
    const featuresCID = featuresResult.txId || featuresResult;
    console.log(`✅ Features загружены: ${featuresCID}`);
    
    if (onProgress) {
      onProgress({ step: 'shareable_data', substep: 'features', progress: 50, status: 'completed' });
    }
    
    // 2. Загрузка component_forms.json
    console.log("\n📝 3.2. component_forms.json");
    
    if (onProgress) {
      onProgress({ step: 'shareable_data', substep: 'forms', progress: 50, status: 'started' });
    }
    
    const formsPath = path.join(__dirname, '..', '..', 'bot', 'catalog', 'component_forms.json');
    const formsData = JSON.parse(fs.readFileSync(formsPath, 'utf8'));
    
    const formsResult = await uploadToArweave(
      context,
      formsData,
      "component_forms_global_dictionary.json"
    );
    
    const formsCID = formsResult.txId || formsResult;
    console.log(`✅ Component forms загружены: ${formsCID}`);
    
    if (onProgress) {
      onProgress({ step: 'shareable_data', substep: 'forms', progress: 100, status: 'completed' });
    }
    
    // 3. Сохраняем CID в контракте (если не dry-run)
    if (!context.dryRun) {
      console.log("\n🔷 Обновляем shareable data в OrganicComponentRegistry...");
      
      // ✅ Ownership: вызов от DEPLOYER (ADMIN для shareable data)
      const signer = context.deployer.signer;
      const organicRegistryWithSigner = context.contracts.organicComponentRegistry.connect(signer);
      
      const tx = await organicRegistryWithSigner.updateShareableData(
        featuresCID,
        formsCID,
        1, // features version
        1  // forms version
      );
      
      await tx.wait();
      console.log("✅ Shareable data обновлены в контракте");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем обновление в контракте");
    }
    
    const shareableData = { featuresCID, formsCID };
    
    // ✅ CHANGE (2025-12-02): Save to arweave section
    state.arweave.shareable_data = shareableData;
    stateManager.markStepCompleted(state.arweave, 'shareable_data_uploaded');
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log("\n✅ ШАГ 3 завершен: Shareable Data загружены");
    
    return shareableData;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 3:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 4: UPDATE ROOT METADATA
// ====================================================================

/**
 * Создание финального root metadata с полученными CID
 * @param {Object} context - Upload context
 * @param {Object} simpleFieldCIDs - CID простых полей
 * @param {Object} complexFieldCIDs - CID сложных полей
 * @param {Object} state - Component state
 * @returns {Object} Финальные метаданные для загрузки
 */
function updateRootMetadata(context, simpleFieldCIDs, complexFieldCIDs, state) {
  console.log("\n🔹 ШАГ 4: Создание финального Root Metadata");
  
  try {
    const fs = require('fs');
    const path = require('path');
    
    // ✅ НОВОЕ: Импорт ComponentTracking
    const ComponentTracking = require('./tracking/ComponentTracking');
    const tracking = new ComponentTracking();
    
    // ✅ НОВОЕ: Очистка исходного JSON файла от тестовых адресов
    // Это обновит исходный файл на диске, заменив тестовые адреса на реальные
    const sourceJsonPath = path.join(context.componentDir, `${context.biounit_id}.json`);
    const cleanedRootData = tracking.cleanSourceJson(sourceJsonPath, context.seller?.address);
    
    // ✅ НОВОЕ: Обновление tracking-полей для финального metadata
    // cleanedRootData уже содержит реальные адреса, но нужно добавить запись в change_history
    const rootDataWithTracking = tracking.updateForCreation(cleanedRootData, {
      actorAddress: context.seller?.address,
      action: 'upload_to_arweave',
      blockchain: null  // Blockchain данные будут добавлены при регистрации
    });
    
    // 2. Создаем финальную структуру с CID references
    const finalRootData = {
      ...rootDataWithTracking,  // ← Используем данные с обновленным tracking
      localizations: {
        simple_fields: simpleFieldCIDs,
        complex_fields: complexFieldCIDs
      },
      last_updated: rootDataWithTracking.last_updated,  // ← Уже обновлен в tracking
      network: context.network
    };
    
    // 3. Сохраняем финальный root файл локально (для истории)
    const finalFileName = `${context.biounit_id}_final_${context.network}.json`;
    const finalRootPath = path.join(context.componentDir, finalFileName);
    
    fs.writeFileSync(finalRootPath, JSON.stringify(finalRootData, null, 2), 'utf8');
    console.log(`💾 Финальный файл сохранен: ${finalFileName}`);
    
    // ✅ CHANGE (2025-12-02): Save to arweave section
    const existingCID = state.arweave?.root_metadata?.cid;
    state.arweave.root_metadata = {
      path: finalFileName,
      data: finalRootData
    };
    
    // Сохраняем CID если он уже был (для повторных запусков)
    if (existingCID) {
      state.arweave.root_metadata.cid = existingCID;
      console.log(`📌 Сохранен существующий CID: ${existingCID}`);
    }
    
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log("\n✅ ШАГ 4 завершен: Root Metadata обновлен");
    
    return finalRootData;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 4:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 5: UPLOAD ROOT METADATA
// ====================================================================

/**
 * Загрузка корневого метаданных в Arweave
 * @param {Object} context - Upload context
 * @param {Object} rootData - Корневые метаданные
 * @param {Object} state - Component state
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<string>} Arweave TX ID (CID)
 */
async function uploadRootMetadata(context, rootData, state, onProgress = null) {
  console.log("\n🔹 ШАГ 5: Загрузка Root Metadata");
  
  // ✅ НОВОЕ: Проверка флага useExistingCids
  if (context.useExistingCids) {
    console.log("🔍 [USE_EXISTING_CIDS] Проверяем наличие существующего CID в state...");
    
    // ✅ CHANGE (2025-12-02): Check arweave section
    const existingRootCID = state.arweave?.root_metadata?.cid || state.root_metadata?.cid;
    
    if (existingRootCID) {
      console.log("✅ [USE_EXISTING_CIDS] Найден существующий CID:");
      console.log(`   → root_metadata.cid: ${existingRootCID.substring(0, 20)}...`);
      console.log("✅ [USE_EXISTING_CIDS] Используем существующий CID, пропускаем загрузку");
      return existingRootCID;
    } else {
      console.warn(`⚠️ [USE_EXISTING_CIDS] CID отсутствует в state.arweave.root_metadata`);
      console.warn(`   🔄 Fallback: выполняем загрузку в Arweave...`);
      // Продолжаем обычную логику загрузки (fallback)
    }
  }
  
  // Проверяем, был ли шаг уже выполнен
  // ✅ CHANGE (2025-12-02): Check arweave section
  if (stateManager.isStepCompleted(state.arweave, 'root_metadata_uploaded')) {
    const savedCID = state.arweave?.root_metadata?.cid || state.root_metadata?.cid;
    console.log("✅ Шаг уже выполнен, используем сохраненный CID");
    console.log(`   → Сохраненный CID: ${savedCID || 'ОТСУТСТВУЕТ!'}`);
    
    if (!savedCID) {
      console.error("❌ ОШИБКА: CID отсутствует в state, хотя шаг помечен как выполненный!");
      console.error("   → State root_metadata:", JSON.stringify(state.arweave?.root_metadata || state.root_metadata, null, 2));
      throw new Error("Inconsistent state: step completed but CID missing");
    }
    
    return savedCID;
  }
  
  try {
    if (onProgress) {
      onProgress({ step: 'root_metadata', progress: 0, status: 'started' });
    }
    
    // Загружаем root metadata в Arweave
    const filename = `${context.biounit_id}_root_metadata.json`;
    const rootResult = await uploadToArweave(context, rootData, filename);
    
    const rootCID = rootResult.txId || rootResult;
    console.log(`✅ Root Metadata загружен: ${rootCID}`);
    
    if (onProgress) {
      onProgress({ step: 'root_metadata', progress: 100, status: 'completed', cid: rootCID });
    }
    
    // ✅ CHANGE (2025-12-02): Save to arweave section
    state.arweave.root_metadata.cid = rootCID;
    state.arweave.root_metadata.uploaded_at = new Date().toISOString();
    stateManager.markStepCompleted(state.arweave, 'root_metadata_uploaded');
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log("\n✅ ШАГ 5 завершен: Root Metadata загружен в Arweave");
    
    return rootCID;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 5:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔹 STEP 6: REGISTER COMPONENT
// ====================================================================

/**
 * Регистрация компонента в OrganicComponentRegistry
 * @param {Object} context - Upload context
 * @param {string} rootCID - Arweave TX ID корневых метаданных
 * @param {Object} state - Component state
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<number>} Component ID
 */
async function registerComponent(context, rootCID, state, onProgress = null) {
  console.log("\n🔹 ШАГ 6: Регистрация в OrganicComponentRegistry");
  
  // ✅ CHANGE (2025-12-02): Multi-network support with deployments
  // Check if component already registered on current network
  
  if (!state.deployments) {
    state.deployments = {};
  }
  
  const networkDeployment = state.deployments[context.network];
  
  if (networkDeployment) {
    console.log(`ℹ️  Deployment для ${context.network} найден в state:`);
    console.log(`   → Blockchain ID: ${networkDeployment.blockchain_id}`);
    console.log(`   → TX Hash: ${networkDeployment.txHash}`);
    console.log(`   → Registered at: ${networkDeployment.registered_at}`);
    
    // Проверяем что компонент действительно есть в контракте
    try {
      const componentExists = await context.contracts.organicComponentRegistry.componentExists(context.biounit_id);
      
      if (componentExists) {
        const blockchainId = await context.contracts.organicComponentRegistry.businessIdToComponentId(context.biounit_id);
        console.log(`✅ Подтверждено в контракте: componentExists() = TRUE`);
        console.log(`   → Blockchain ID в контракте: ${blockchainId}`);
        console.log(`   → Пропуск регистрации`);
        
        // Обновляем blockchain_id если отличается
        if (networkDeployment.blockchain_id != blockchainId.toString()) {
          console.log(`⚠️ Blockchain ID в state (${networkDeployment.blockchain_id}) != в контракте (${blockchainId})`);
          console.log(`   → Обновляем state`);
          state.deployments[context.network].blockchain_id = blockchainId.toString();
          stateManager.saveComponentState(context.componentDir, state);
        }
        
        return blockchainId.toString();
      } else {
        console.warn(`❌ НЕСООТВЕТСТВИЕ: State говорит "зарегистрирован", но componentExists() = FALSE`);
        console.warn(`   💡 Вероятная причина: Node был перезапущен, blockchain state сброшен`);
        console.warn(`   🔧 Выполняем регистрацию заново с сохранённым Arweave CID...`);
      }
    } catch (verifyError) {
      console.error(`❌ Ошибка проверки контракта: ${verifyError.message}`);
      console.warn(`   🔧 Fail-safe: Регистрируем заново...`);
    }
  } else {
    console.log(`ℹ️  Deployment для ${context.network} НЕ найден в state, выполняем регистрацию...`);
  }
  
  // В dry-run режиме не регистрируем в контракте
  if (context.dryRun) {
    console.log("🔷 [DRY-RUN] Пропускаем регистрацию в контракте");
    const mockBlockchainId = Math.floor(Math.random() * 1000);
    
    state.deployments[context.network] = {
      blockchain_id: mockBlockchainId,
      txHash: "DRYRUN_TX_HASH",
      blockNumber: "N/A",
      registered_at: new Date().toISOString(),
      dry_run: true
    };
    
    // Mark step completed in arweave section
    if (!state.arweave.steps_completed.includes('component_registered')) {
      state.arweave.steps_completed.push('component_registered');
    }
    
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log(`🔷 [DRY-RUN] Mock Blockchain ID: ${mockBlockchainId}`);
    console.log("\n✅ ШАГ 6 завершен (DRY-RUN)");
    
    return mockBlockchainId;
  }
  
  try {
    if (onProgress) {
      onProgress({ step: 'register_component', progress: 0, status: 'started' });
    }
    
    // Детальное логирование для отладки
    console.log(`📝 Регистрируем компонент: ${context.biounit_id}`);
    console.log(`📄 Root CID: ${rootCID}`);
    console.log(`🔍 Тип Root CID: ${typeof rootCID}`);
    console.log(`✅ Root CID валиден: ${!!rootCID}`);
    
    // Проверка валидности CID
    if (!rootCID || rootCID === 'undefined' || rootCID === 'null') {
      console.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Root CID пустой!");
      console.error("   → State root_metadata:", JSON.stringify(state.root_metadata, null, 2));
      throw new Error("Root CID отсутствует. Невозможно зарегистрировать компонент.");
    }
    
    console.log(`🌐 Контракт: OrganicComponentRegistry`);
    const organicRegistryAddress = await context.contracts.organicComponentRegistry.getAddress();
    console.log(`   → Адрес: ${organicRegistryAddress}`);
    console.log(`   → Deployer: ${context.deployer.address}`);
    console.log(`   → Seller (создатель компонента): ${context.seller.address}`);
    
    console.log(`\n🚀 Вызов createComponent("${context.biounit_id}", "${rootCID}")...`);
    console.log(`   → От имени seller: ${context.seller.address}`);
    
    // ✅ ethers.js: регистрация компонента от seller
    const signer = context.seller.signer;
    const organicRegistryWithSigner = context.contracts.organicComponentRegistry.connect(signer);
    
    // ✅ CRITICAL FIX: Wait for nonce update to prevent race conditions
    // Same pattern as DeployActions.js - prevents "nonce has already been used"
    console.log(`⏱️  Waiting 500ms for nonce synchronization...`);
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const tx = await organicRegistryWithSigner.createComponent(
      context.biounit_id,  // ✅ biounit_id - текстовое значение (например "amanita_muscaria")
      rootCID
    );
    
    console.log(`📝 Транзакция отправлена: ${tx.hash}`);
    
    if (onProgress) {
      onProgress({ step: 'register_component', progress: 50, status: 'tx_sent', txHash: tx.hash });
    }
    
    // Ждем подтверждения транзакции
    const receipt = await tx.wait();
    console.log(`✅ Транзакция подтверждена: блок ${receipt.blockNumber}`);
    
    // ✅ НОВОЕ: Обновление change_history с blockchain данными
    console.log(`\n📝 Обновление tracking-полей с blockchain данными...`);
    const ComponentTracking = require('./tracking/ComponentTracking');
    const tracking = new ComponentTracking();
    const fs = require('fs');
    const path = require('path');
    
    // Загрузить финальный root metadata из state
    const finalRootData = state.arweave?.root_metadata?.data;
    
    if (finalRootData) {
      console.log(`   → Загружен root metadata из state`);
      
      // Обновить change_history в root metadata
      const updatedData = tracking.addHistoryEntry(finalRootData, {
        timestamp: new Date().toISOString(),
        address: context.seller?.address,
        action: 'register_in_contract',
        changes: ['contract_registration'],
        transaction_hash: receipt.hash,
        block_number: receipt.blockNumber
      });
      
      console.log(`   → Добавлена запись в change_history`);
      console.log(`      → Action: register_in_contract`);
      console.log(`      → TX Hash: ${receipt.hash}`);
      console.log(`      → Block: ${receipt.blockNumber}`);
      
      // Сохранить обновленные данные обратно в state
      state.arweave.root_metadata.data = updatedData;
      console.log(`   → Обновлен state.arweave.root_metadata.data`);
      
      // ✅ НОВОЕ: Обновить исходный JSON файл компонента с blockchain данными
      const sourceJsonPath = path.join(context.componentDir, `${context.biounit_id}.json`);
      
      if (fs.existsSync(sourceJsonPath)) {
        console.log(`   → Чтение исходного JSON файла: ${path.basename(sourceJsonPath)}`);
        const sourceJsonData = utils.readJSON(context.componentDir, `${context.biounit_id}.json`);
        
        const updatedSourceJson = tracking.addHistoryEntry(sourceJsonData, {
          timestamp: new Date().toISOString(),
          address: context.seller?.address,
          action: 'register_in_contract',
          changes: ['contract_registration'],
          transaction_hash: receipt.hash,
          block_number: receipt.blockNumber
        });
        
        fs.writeFileSync(sourceJsonPath, JSON.stringify(updatedSourceJson, null, 2), 'utf8');
        console.log(`   ✅ Обновлен исходный JSON с blockchain данными`);
        console.log(`      → TX: ${receipt.hash}`);
        console.log(`      → Block: ${receipt.blockNumber}`);
      } else {
        console.warn(`   ⚠️  Исходный JSON файл не найден: ${sourceJsonPath}`);
      }
      
      // Обновить финальный файл на диске
      const finalFileName = state.arweave?.root_metadata?.path;
      if (finalFileName) {
        const finalRootPath = path.join(context.componentDir, finalFileName);
        if (fs.existsSync(finalRootPath)) {
          fs.writeFileSync(finalRootPath, JSON.stringify(updatedData, null, 2), 'utf8');
          console.log(`   ✅ Обновлен финальный JSON с blockchain данными: ${finalFileName}`);
        }
      }
      
      // Сохранить state (уже будет сохранен ниже, но сохраняем здесь для безопасности)
      stateManager.saveComponentState(context.componentDir, state);
      console.log(`   → State сохранен`);
    } else {
      console.warn(`   ⚠️  Root metadata не найден в state, пропускаем обновление tracking-полей`);
    }
    
    // Извлекаем componentId из события ComponentCreated (ethers.js парсинг)
    let componentId = null;
    
    for (const log of receipt.logs) {
      try {
        // ethers.js: парсинг события через contract.interface
        const parsedLog = context.contracts.organicComponentRegistry.interface.parseLog({
          topics: log.topics,
          data: log.data
        });
        
        if (parsedLog && parsedLog.name === 'ComponentCreated') {
          componentId = parsedLog.args.componentId;
          console.log(`🎉 Компонент создан с ID: ${componentId}`);
          break;
        }
      } catch (parseError) {
        // Пропускаем логи, которые не относятся к нашему контракту
        continue;
      }
    }
    
    if (!componentId) {
      // Fallback: пытаемся найти componentId другим способом
      console.warn("⚠️ Не удалось извлечь componentId из события, используем fallback");
      componentId = receipt.logs.length > 0 ? 1 : 0;
    }
    
    if (onProgress) {
      onProgress({ step: 'register_component', progress: 100, status: 'completed', componentId });
    }
    
    // ✅ CHANGE (2025-12-02): Save to deployments[network]
    state.deployments[context.network] = {
      blockchain_id: componentId.toString(),
      txHash: receipt.hash,
      blockNumber: receipt.blockNumber,
      registered_at: new Date().toISOString()
    };
    
    // Mark step completed in arweave section (only once, not per network)
    if (!state.arweave.steps_completed.includes('component_registered')) {
      state.arweave.steps_completed.push('component_registered');
    }
    
    stateManager.saveComponentState(context.componentDir, state);
    
    console.log("\n✅ ШАГ 6 завершен: Компонент зарегистрирован в контракте");
    console.log(`   → Network: ${context.network}`);
    console.log(`   → Blockchain ID: ${componentId}`);
    
    return componentId;
    
  } catch (error) {
    console.error("\n❌ Ошибка в ШАГ 6:", error.message);
    throw error;
  }
}

// ====================================================================
// 🔧 ARWEAVE HELPER
// ====================================================================

/**
 * Загрузка JSON в Arweave (helper для всех steps)
 * @param {Object} context - Upload context
 * @param {Object} data - Данные для загрузки
 * @param {string} filename - Имя файла для логирования
 * @returns {Promise<string>} Arweave TX ID (используется как CID)
 */
/**
 * Detect Content-Type from filename extension
 */
function detectContentType(filename) {
  const ext = filename.toLowerCase().match(/\.(json|jpeg|jpg|png|gif|webp|txt|md)$/);
  if (!ext) return 'application/octet-stream';
  
  const mimeMap = {
    'json': 'application/json',
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'txt': 'text/plain',
    'md': 'text/markdown'
  };
  
  return mimeMap[ext[1]] || 'application/octet-stream';
}

async function uploadToArweave(context, data, filename, options = {}) {
  const startTime = Date.now();
  
  console.log(`📤 Загрузка ${filename} в Arweave...`);
  
  // ✅ Determine if data is binary
  const isBinary = options.isBinary !== undefined ? options.isBinary : Buffer.isBuffer(data);
  
  // ✅ Determine Content-Type
  const contentType = options.contentType || detectContentType(filename);
  
  // Если dry-run режим → вернуть mock TX ID
  if (context.dryRun) {
    const mockSize = isBinary ? data.length : JSON.stringify(data, null, 2).length;
    const mockTxId = `DRYRUN_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    console.log(`🔷 [DRY-RUN] Mock TX ID: ${mockTxId}`);
    console.log(`   → Размер: ${mockSize} bytes (${(mockSize / 1024).toFixed(2)} KB)`);
    console.log(`   → Content-Type: ${contentType}`);
    return { txId: mockTxId, size: mockSize, duration: 0 };
  }
  
  // Реальная загрузка в Arweave
  try {
    const Arweave = require('arweave');
    
    // ✅ Prepare data based on type
    let dataToUpload, dataSize;
    if (isBinary) {
      // Binary data (Buffer) - use directly
      dataToUpload = data;
      dataSize = data.length;
    } else {
      // JSON data - stringify
      dataToUpload = JSON.stringify(data, null, 2);
      dataSize = Buffer.byteLength(dataToUpload, 'utf8');
    }
    
    console.log(`   → Размер: ${dataSize} bytes (${(dataSize / 1024).toFixed(2)} KB)`);
    
    // ПРОВЕРКА БАЛАНСА ПЕРЕД ЗАГРУЗКОЙ
    if (!context._arweaveBalanceChecked) {
      console.log(`💰 Проверка баланса Arweave кошелька...`);
      try {
        const address = await context.arweave.client.wallets.jwkToAddress(context.arweave.key);
        const balance = await context.arweave.client.wallets.getBalance(address);
        const balanceAR = context.arweave.client.ar.winstonToAr(balance);
        
        console.log(`   → Адрес: ${address}`);
        console.log(`   → Баланс: ${balanceAR} AR`);
        
        if (parseFloat(balanceAR) === 0) {
          throw new Error(
            `Arweave кошелек имеет нулевой баланс!\n` +
            `   Адрес для пополнения: ${address}\n` +
            `   Минимум требуется: ~0.001 AR\n` +
            `   Получить AR токены: https://www.arweave.org/`
          );
        }
        
        // Помечаем, что баланс проверен
        context._arweaveBalanceChecked = true;
        console.log(`✅ Баланс достаточен для загрузки`);
      } catch (balanceError) {
        if (balanceError.message.includes('нулевой баланс')) {
          throw balanceError;
        }
        console.warn(`⚠️  Не удалось проверить баланс: ${balanceError.message}`);
        console.warn(`⚠️  Продолжаем загрузку...`);
      }
    }
    
    // Создаем transaction
    console.log(`   → Создание транзакции...`);
    const transaction = await context.arweave.client.createTransaction({
      data: dataToUpload
    }, context.arweave.key);
    
    // ✅ Добавляем tags для метаданных с правильным Content-Type
    transaction.addTag('Content-Type', contentType);
    transaction.addTag('App-Name', 'Amanita-Organic-Components');
    transaction.addTag('File-Name', filename);
    transaction.addTag('Type', 'organic-component-metadata');
    transaction.addTag('Version', '1.0.0');
    transaction.addTag('Size-Bytes', dataSize.toString());
    
    // Подписываем transaction
    console.log(`   → Подпись транзакции...`);
    await context.arweave.client.transactions.sign(transaction, context.arweave.key);
    
    // Отправляем transaction
    console.log(`   → Отправка в Arweave...`);
    const response = await context.arweave.client.transactions.post(transaction);
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    
    if (response.status === 200) {
      // Валидация TX ID
      if (!transaction.id || transaction.id.length !== 43) {
        throw new Error(`Некорректный TX ID: ${transaction.id}`);
      }
      
      console.log(`✅ ${filename} загружен успешно!`);
      console.log(`   → TX ID: ${transaction.id}`);
      console.log(`   → URL: https://arweave.net/${transaction.id}`);
      console.log(`   → Размер: ${dataSize} bytes`);
      console.log(`   → Время: ${duration}s`);
      
      return {
        txId: transaction.id,
        url: `https://arweave.net/${transaction.id}`,
        size: dataSize,
        duration: parseFloat(duration)
      };
    } else {
      // ✅ FIX: Show detailed error from Arweave API
      const errorDetails = response.data || response.statusText || 'No details';
      console.error(`❌ Arweave API error details:`, errorDetails);
      throw new Error(`Arweave API вернул статус ${response.status}: ${JSON.stringify(errorDetails)}`);
    }
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.error(`❌ Ошибка загрузки ${filename} в Arweave (${duration}s):`, error.message);
    throw error;
  }
}

// ====================================================================
// 🔧 RESTORATION FUNCTIONS
// ====================================================================

/**
 * Восстановить Simple Fields из state в контракт (без повторной загрузки в Arweave)
 * 
 * Используется для восстановления данных после перезапуска ноды, когда state файлы
 * содержат CIDs, но контракт был развернут заново.
 * 
 * @param {Object} context - Upload context
 * @param {Object} context.contracts - Contract instances
 * @param {Object} context.contracts.amanitaInternational - AmanitaInternational contract
 * @param {Object} context.seller - Seller account with signer
 * @param {string} context.biounit_id - Component biounit_id (optional, not used for simple fields)
 * @param {boolean} context.dryRun - Dry-run mode flag
 * @param {boolean} context.arweaveOnly - Arweave-only mode flag
 * @param {Object} state - Component state
 * @param {Array<string>} missingFields - Список отсутствующих полей (['title', 'dosage'])
 * @returns {Promise<Object>} Восстановленные CIDs { title?: string, dosage?: string }
 */
async function restoreSimpleFieldsToContract(context, state, missingFields) {
  if (!context || !context.contracts || !context.contracts.amanitaInternational) {
    throw new Error('Invalid context: contracts.amanitaInternational is required');
  }
  if (!context.seller || !context.seller.signer) {
    throw new Error('Invalid context: seller.signer is required');
  }
  if (!state) {
    throw new Error('State object is required');
  }
  if (!Array.isArray(missingFields)) {
    throw new Error('missingFields must be an array');
  }
  
  // В dry-run или arweave-only режиме не сохраняем в контракт
  if (context.dryRun || context.arweaveOnly) {
    console.log("🔷 [DRY-RUN/ARWEAVE_ONLY] Пропускаем восстановление в контракт");
    return {};
  }
  
  const amanitaIntl = context.contracts.amanitaInternational;
  const signer = context.seller.signer;
  const amanitaIntlWithSigner = amanitaIntl.connect(signer);
  const restored = {};
  
  // ✅ FIX (2025-12-02): Get fields from arweave section (same pattern as restoreComplexFieldsToContract)
  const simpleFields = state.arweave?.simple_fields || state.simple_fields || {};
  
  for (const field of missingFields) {
    // Определяем ключ в state и поле контракта
    const stateKey = field === 'title' ? 'title' : 'dosage_types';
    const stateData = simpleFields[stateKey];
    
    if (!stateData || !stateData.cid) {
      console.warn(`⚠️ CID для ${field} отсутствует в state, пропускаем восстановление`);
      continue;
    }
    
    const cid = stateData.cid;
    const fieldKey = field === 'title' 
      ? 'ComponentDescription.title' 
      : 'DosageInstruction.description';
    
    try {
      console.log(`🔧 Восстанавливаем ${fieldKey} из state в контракт...`);
      const tx = await amanitaIntlWithSigner.setSimpleFieldCID(fieldKey, cid);
      await tx.wait();
      
      // ✅ CRITICAL FIX: Wait for nonce synchronization to prevent race conditions
      // Same pattern as registerComponent() and DeployActions - prevents "nonce has already been used"
      await new Promise(resolve => setTimeout(resolve, 500));
      
      restored[field] = cid;
      console.log(`✅ ${fieldKey} восстановлен (CID: ${cid.substring(0, 20)}...)`);
    } catch (error) {
      console.error(`❌ Ошибка восстановления ${fieldKey}: ${error.message}`);
      throw error;
    }
  }
  
  return restored;
}

/**
 * Восстановить Complex Fields из state в контракт (без повторной загрузки в Arweave)
 * 
 * Используется для восстановления данных после перезапуска ноды, когда state файлы
 * содержат CIDs, но контракт был развернут заново.
 * 
 * @param {Object} context - Upload context
 * @param {Object} context.contracts - Contract instances
 * @param {Object} context.contracts.amanitaInternational - AmanitaInternational contract
 * @param {Object} context.seller - Seller account with signer
 * @param {string} context.biounit_id - Component biounit_id (required)
 * @param {boolean} context.dryRun - Dry-run mode flag
 * @param {boolean} context.arweaveOnly - Arweave-only mode flag
 * @param {Object} state - Component state
 * @param {Array<string>} missingLanguages - Список отсутствующих языков
 * @returns {Promise<Object>} Восстановленные CIDs по языкам { ru?: string, en?: string, ... }
 */
async function restoreComplexFieldsToContract(context, state, missingLanguages) {
  if (!context || !context.contracts || !context.contracts.amanitaInternational) {
    throw new Error('Invalid context: contracts.amanitaInternational is required');
  }
  if (!context.seller || !context.seller.signer) {
    throw new Error('Invalid context: seller.signer is required');
  }
  if (!context.biounit_id) {
    throw new Error('Invalid context: biounit_id is required');
  }
  if (!state) {
    throw new Error('State object is required');
  }
  if (!Array.isArray(missingLanguages)) {
    throw new Error('missingLanguages must be an array');
  }
  
  // В dry-run или arweave-only режиме не сохраняем в контракт
  if (context.dryRun || context.arweaveOnly) {
    console.log("🔷 [DRY-RUN/ARWEAVE_ONLY] Пропускаем восстановление в контракт");
    return {};
  }
  
  const amanitaIntl = context.contracts.amanitaInternational;
  const signer = context.seller.signer;
  const amanitaIntlWithSigner = amanitaIntl.connect(signer);
  const className = `ComponentDescription.${context.biounit_id}`;
  const restored = {};
  
  // ✅ CHANGE (2025-12-02): Get fields from arweave section
  const complexFields = state.arweave?.complex_fields || state.complex_fields || {};
  
  for (const lang of missingLanguages) {
    const stateData = complexFields[lang];
    if (!stateData) {
      console.warn(`⚠️ CID для ${lang} отсутствует в state, пропускаем восстановление`);
      continue;
    }
    
    // Поддерживаем как строку, так и объект с cid
    const cid = typeof stateData === 'string' ? stateData : stateData.cid;
    if (!cid) {
      console.warn(`⚠️ CID для ${lang} невалиден, пропускаем восстановление`);
      continue;
    }
    
    try {
      console.log(`🔧 Восстанавливаем ${className}.${lang} из state в контракт...`);
      const tx = await amanitaIntlWithSigner.setComplexFieldCID(className, lang, cid);
      await tx.wait();
      
      // ✅ CRITICAL FIX: Wait for nonce synchronization to prevent race conditions
      // Same pattern as registerComponent() and DeployActions - prevents "nonce has already been used"
      await new Promise(resolve => setTimeout(resolve, 500));
      
      restored[lang] = cid;
      console.log(`✅ ${className}.${lang} восстановлен (CID: ${cid.substring(0, 20)}...)`);
    } catch (error) {
      console.error(`❌ Ошибка восстановления ${className}.${lang}: ${error.message}`);
      throw error;
    }
  }
  
  return restored;
}

// ====================================================================
// 🚀 ACTION 52: UNIFIED ARWEAVE UPLOAD FOR COMPONENTS
// ====================================================================

/**
 * Action 52: Unified Arweave Upload для компонентов
 * 
 * Загружает все компоненты в Arweave:
 * - Simple Fields (title, dosage) → Arweave → CID в AmanitaInternational
 * - Complex Fields (переводы) → Arweave → CID в AmanitaInternational
 * - Shareable Data (один раз) → Arweave
 * - Root Metadata (обновленный) → Arweave → root CID в state
 * 
 * @param {Object} context - Upload context
 * @param {string} componentsDir - Директория с компонентами (default: "data/components")
 * @param {string} networkName - Название сети
 * @param {boolean} dryRun - Режим dry-run
 * @returns {Promise<Object>} - Upload results
 */
async function action52_UnifiedArweaveUpload(context, componentsDir, networkName, dryRun = false) {
  console.log("\n" + "=".repeat(80));
  console.log("🚀 ACTION 52: ЗАГРУЗКА КОМПОНЕНТОВ В ARWEAVE");
  console.log("=".repeat(80));
  console.log(`📁 Components dir: ${componentsDir}`);
  console.log(`🌐 Network: ${networkName}`);
  console.log(`🔍 Dry-run: ${dryRun ? 'YES' : 'NO'}`);
  
  const startTime = Date.now();
  const results = [];
  let successCount = 0;
  let failCount = 0;
  
  try {
    // 1. Валидация context
    if (!context.arweave || !context.arweave.client) {
      throw new Error("Arweave client not initialized in context");
    }
    
    if (!context.contracts || !context.contracts.amanitaInternational) {
      throw new Error("AmanitaInternational contract not initialized in context");
    }
    
    if (!context.seller || !context.seller.address) {
      throw new Error("Seller not initialized in context");
    }
    
    // 2. Валидация seller (требует Action 51)
    if (context.contracts.spiralEngine) {
      const usedInvite = await context.contracts.spiralEngine.usedInviteByUser(context.seller.address);
      if (usedInvite == 0) {
        throw new Error(`Seller ${context.seller.address} не активирован! Запустите Action 51 сначала.`);
      }
      
      const SELLER_ROLE = await context.contracts.spiralEngine.SELLER_ROLE();
      const hasSellerRole = await context.contracts.spiralEngine.hasRole(SELLER_ROLE, context.seller.address);
      if (!hasSellerRole) {
        throw new Error(`Seller ${context.seller.address} не имеет SELLER_ROLE! Запустите Action 51 сначала.`);
      }
    }
    
    // 3. Поиск компонентов
    const fs = require('fs');
    const path = require('path');
    // scripts/lib/upload_steps.js находится в <projectRoot>/scripts/lib
    // поэтому projectRoot = два уровня вверх.
    const projectRoot = path.join(__dirname, '..', '..');
    const componentsPath = path.join(projectRoot, componentsDir);
    
    if (!fs.existsSync(componentsPath)) {
      throw new Error(`Директория компонентов не найдена: ${componentsPath}`);
    }
    
    const entries = fs.readdirSync(componentsPath, { withFileTypes: true });
    const componentIds = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .filter(name => {
        if (name.startsWith('_') || name.startsWith('.')) return false;
        const componentDir = path.join(componentsPath, name);
        const rootFile = path.join(componentDir, `${name}.json`);
        return fs.existsSync(rootFile);
      })
      .sort();
    
    if (componentIds.length === 0) {
      throw new Error(`Компоненты не найдены в ${componentsPath}`);
    }
    
    console.log(`✅ Найдено компонентов: ${componentIds.length}`);
    
    // 4. Обработка компонентов
    console.log(`\n🚀 Обработка компонентов...`);
    
    let shareableDataUploaded = false;
    
    for (let i = 0; i < componentIds.length; i++) {
      const componentId = componentIds[i];
      const componentDir = path.join(componentsPath, componentId);
      
      console.log(`\n${'='.repeat(70)}`);
      console.log(`🔷 Компонент ${i + 1}/${componentIds.length}: ${componentId}`);
      console.log(`${'='.repeat(70)}`);
      
      try {
        // Создаем context для upload_steps
        const componentContext = {
          biounit_id: componentId,
          componentDir: componentDir,
          network: networkName,
          dryRun: dryRun,
          useExistingCids: context.useExistingCids,  // ✅ НОВОЕ: Передаем флаг для использования существующих CID
          seller: context.seller,
          deployer: context.deployer,
          contracts: context.contracts,
          arweave: context.arweave,
          ethersProvider: context.ethersProvider,
          supportedLanguages: context.supportedLanguages || utils.getSupportedLanguages()
        };
        
        // Загрузка state
        let state = stateManager.loadComponentState(componentDir, networkName) || {
          biounit_id: componentId,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          arweave: {
            steps_completed: [],
            simple_fields: {},
            complex_fields: {},
            root_metadata: {}
          },
          deployments: {}
        };
        
        // Проверка завершенных шагов
        const isStepCompleted = (stepName) => {
          return state.arweave?.steps_completed?.includes(stepName) || false;
        };
        
        console.log(`💾 Загрузка component state: ${componentId} (biounit_id: ${componentContext.biounit_id})`);
        const arweaveSteps = state.arweave?.steps_completed || [];
        
        if (arweaveSteps.length > 0) {
          console.log(`✅ State найден:`);
          console.log(`   → Arweave шагов: ${arweaveSteps.length}`);
          console.log(`   → Завершенные шаги: ${arweaveSteps.join(', ')}`);
        } else {
          console.log(`🆕 State файл не найден, создаем новый`);
        }
        
        // Шаг 1: Upload Simple Fields
        let simpleFieldCIDs = await uploadSimpleFields(componentContext, state);
        
        // Шаг 2: Upload Complex Fields
        let complexFieldCIDs = await uploadComplexFields(componentContext, state);
        
        // Шаг 3: Upload Shareable Data (один раз, для первого компонента)
        if (!shareableDataUploaded) {
          if (isStepCompleted('shareable_data_uploaded')) {
            console.log(`\n⏭️  Shareable Data уже загружены (пропуск)`);
          } else {
            await uploadShareableData(componentContext, state);
            console.log(`✅ Shareable Data загружены`);
          }
          shareableDataUploaded = true;
        }
        
        // Шаг 4: Update Root Metadata
        let finalRootData;
        if (isStepCompleted('root_metadata_updated')) {
          console.log(`\n⏭️  Root Metadata уже обновлен (пропуск)`);
          finalRootData = state.arweave?.root_metadata?.data;
        } else {
          finalRootData = updateRootMetadata(componentContext, simpleFieldCIDs, complexFieldCIDs, state);
          console.log(`✅ Root Metadata обновлен`);
        }
        
        // Шаг 5: Upload Root Metadata
        let rootCID;
        if (isStepCompleted('root_metadata_uploaded')) {
          console.log(`\n⏭️  Root Metadata уже загружен в Arweave (пропуск)`);
          rootCID = state.arweave?.root_metadata?.cid;
        } else {
          rootCID = await uploadRootMetadata(componentContext, finalRootData, state);
          console.log(`✅ Root Metadata загружен в Arweave: ${rootCID}`);
        }
        
        // ❌ НЕ ВКЛЮЧАТЬ: registerComponent() - это Action 53
        
        results.push({
          componentId,
          success: true,
          rootCID: rootCID,
          simpleFields: Object.keys(simpleFieldCIDs).length,
          complexFields: Object.keys(complexFieldCIDs).length
        });
        successCount++;
        
      } catch (error) {
        console.error(`❌ Ошибка обработки компонента ${componentId}:`);
        console.error(`   ${error.message}`);
        
        results.push({
          componentId,
          success: false,
          error: error.message
        });
        failCount++;
        
        console.log(`⏭️  Продолжаем со следующим компонентом...`);
      }
    }
    
    // 5. Финальный отчет
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log(`\n${'='.repeat(80)}`);
    console.log(`📊 ФИНАЛЬНЫЙ ОТЧЁТ ACTION 52`);
    console.log(`${'='.repeat(80)}`);
    console.log(`✅ Успешно: ${successCount}`);
    console.log(`❌ Ошибок: ${failCount}`);
    console.log(`📊 Всего: ${componentIds.length}`);
    console.log(`⏱️ Время выполнения: ${duration}s`);
    
    if (successCount > 0) {
      console.log(`\n🎉 Успешно загружены:`);
      results.filter(r => r.success).forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.componentId}`);
        console.log(`      → Root CID: ${result.rootCID}`);
        console.log(`      → Simple Fields: ${result.simpleFields}`);
        console.log(`      → Complex Fields: ${result.complexFields}`);
      });
    }
    
    if (failCount > 0) {
      console.log(`\n❌ Ошибки:`);
      results.filter(r => !r.success).forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.componentId}: ${result.error}`);
      });
    }
    
    console.log(`\n✅ ACTION 52 завершен`);
    console.log(`${'='.repeat(80)}`);
    
    return {
      success: failCount === 0,
      successCount,
      failCount,
      totalCount: componentIds.length,
      results,
      duration: parseFloat(duration)
    };
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.error(`\n❌ ACTION 52 завершен с ошибкой: ${error.message}`);
    console.error(`⏱️ Время выполнения: ${duration}s`);
    throw error;
  }
}

// ====================================================================
// 🚀 ACTION 53: UNIFIED CONTRACT REGISTRATION FOR COMPONENTS
// ====================================================================

/**
 * Action 53: Unified Contract Registration для компонентов
 * 
 * Регистрирует все компоненты в OrganicComponentRegistry:
 * - Читает root CID из state файлов
 * - Проверяет существование компонента в контракте
 * - Регистрирует компонент (biounit_id, rootCID)
 * - Выполняет финальную валидацию
 * 
 * @param {Object} context - Upload context
 * @param {string} componentsDir - Директория с компонентами (default: "data/components")
 * @param {string} networkName - Название сети
 * @param {boolean} dryRun - Режим dry-run
 * @returns {Promise<Object>} - Registration results
 */
async function action53_UnifiedContractRegistration(context, componentsDir, networkName, dryRun = false) {
  console.log("\n" + "=".repeat(80));
  console.log("🚀 ACTION 53: РЕГИСТРАЦИЯ КОМПОНЕНТОВ В КОНТРАКТЕ");
  console.log("=".repeat(80));
  console.log(`📁 Components dir: ${componentsDir}`);
  console.log(`🌐 Network: ${networkName}`);
  console.log(`🔍 Dry-run: ${dryRun ? 'YES' : 'NO'}`);
  
  const startTime = Date.now();
  const results = [];
  let successCount = 0;
  let failCount = 0;
  
  try {
    // 1. Валидация контракта
    if (!context.contracts || !context.contracts.organicComponentRegistry) {
      throw new Error("OrganicComponentRegistry contract not initialized in context");
    }
    
    // 2. Валидация seller
    if (!context.seller || !context.seller.address) {
      throw new Error("Seller not initialized in context");
    }
    
    // Проверка активации seller (требует Action 51)
    if (context.contracts.spiralEngine) {
      const usedInvite = await context.contracts.spiralEngine.usedInviteByUser(context.seller.address);
      if (usedInvite == 0) {
        throw new Error(`Seller ${context.seller.address} не активирован! Запустите Action 51 сначала.`);
      }
      
      const SELLER_ROLE = await context.contracts.spiralEngine.SELLER_ROLE();
      const hasSellerRole = await context.contracts.spiralEngine.hasRole(SELLER_ROLE, context.seller.address);
      if (!hasSellerRole) {
        throw new Error(`Seller ${context.seller.address} не имеет SELLER_ROLE! Запустите Action 51 сначала.`);
      }
    }
    
    // 3. Поиск компонентов
    const fs = require('fs');
    const path = require('path');
    // scripts/lib/upload_steps.js находится в <projectRoot>/scripts/lib
    // поэтому projectRoot = два уровня вверх.
    const projectRoot = path.join(__dirname, '..', '..');
    const componentsPath = path.join(projectRoot, componentsDir);
    
    if (!fs.existsSync(componentsPath)) {
      throw new Error(`Директория компонентов не найдена: ${componentsPath}`);
    }
    
    const entries = fs.readdirSync(componentsPath, { withFileTypes: true });
    const componentIds = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .filter(name => {
        if (name.startsWith('_') || name.startsWith('.')) return false;
        const componentDir = path.join(componentsPath, name);
        const rootFile = path.join(componentDir, `${name}.json`);
        return fs.existsSync(rootFile);
      })
      .sort();
    
    if (componentIds.length === 0) {
      throw new Error(`Компоненты не найдены в ${componentsPath}`);
    }
    
    console.log(`✅ Найдено компонентов: ${componentIds.length}`);
    
    // 4. Регистрация компонентов
    console.log(`\n🚀 Регистрация компонентов в контракте...`);
    
    // stateManager уже импортирован в начале файла (строка 12), используем его
    
    for (let i = 0; i < componentIds.length; i++) {
      const componentId = componentIds[i];
      const componentDir = path.join(componentsPath, componentId);
      
      console.log(`\n${'='.repeat(70)}`);
      console.log(`🔷 Компонент ${i + 1}/${componentIds.length}: ${componentId}`);
      console.log(`${'='.repeat(70)}`);
      
      try {
        // Загрузка state
        const state = stateManager.loadComponentState(componentDir, networkName);
        
        if (!state) {
          throw new Error(`State файл не найден для компонента ${componentId}. Запустите Action 52 сначала.`);
        }
        
        // Получение root CID из state
        const rootCID = state.arweave?.root_metadata?.cid;
        
        if (!rootCID) {
          throw new Error(`Root CID не найден в state для компонента ${componentId}. Запустите Action 52 сначала.`);
        }
        
        console.log(`📋 Root CID из state: ${rootCID}`);
        
        // Создание context для registerComponent
        const componentContext = {
          biounit_id: componentId,
          componentDir: componentDir,
          network: networkName,
          dryRun: dryRun,
          seller: context.seller,
          deployer: context.deployer,
          contracts: context.contracts,
          arweave: context.arweave,
          ethersProvider: context.ethersProvider,
          supportedLanguages: context.supportedLanguages || require('../upload_utils').getSupportedLanguages()
        };
        
        // Регистрация компонента
        const componentIdResult = await registerComponent(componentContext, rootCID, state);
        console.log(`✅ Компонент зарегистрирован: ID ${componentIdResult}`);
        
        results.push({
          componentId,
          success: true,
          rootCID: rootCID,
          contractComponentId: componentIdResult
        });
        successCount++;
        
      } catch (error) {
        console.error(`❌ Ошибка регистрации компонента ${componentId}:`);
        console.error(`   ${error.message}`);
        
        results.push({
          componentId,
          success: false,
          error: error.message
        });
        failCount++;
        
        console.log(`⏭️  Продолжаем со следующим компонентом...`);
      }
    }
    
    // 5. Финальная валидация
    if (!dryRun && successCount > 0) {
      console.log(`\n${'='.repeat(70)}`);
      console.log(`🔍 ФИНАЛЬНАЯ ВАЛИДАЦИЯ КОНТРАКТНОГО СОСТОЯНИЯ`);
      console.log(`${'='.repeat(70)}`);
      
      const organicComponentRegistry = context.contracts.organicComponentRegistry;
      
      const totalInContract = await organicComponentRegistry.totalComponents();
      console.log(`\n📊 Статистика OrganicComponentRegistry:`);
      console.log(`   Всего компонентов в контракте: ${totalInContract}`);
      console.log(`   Обработано в Action 53: ${successCount}`);
      
      if (totalInContract.toString() !== successCount.toString()) {
        console.error(`\n❌ КРИТИЧЕСКАЯ ОШИБКА: Несоответствие количества компонентов!`);
        console.error(`   Обработано: ${successCount}`);
        console.error(`   В контракте: ${totalInContract}`);
        throw new Error(`Component count mismatch: processed ${successCount}, in contract ${totalInContract}`);
      }
      
      console.log(`\n🔍 Проверка каждого компонента:`);
      let verifiedCount = 0;
      for (const result of results.filter(r => r.success)) {
        const exists = await organicComponentRegistry.componentExists(result.componentId);
        const status = exists ? '✅ В КОНТРАКТЕ' : '❌ НЕ НАЙДЕН';
        console.log(`   ${status}: ${result.componentId}`);
        
        if (!exists) {
          console.error(`\n❌ КРИТИЧЕСКАЯ ОШИБКА: Component ${result.componentId} reported success but NOT in contract!`);
          throw new Error(`Component ${result.componentId} validation failed - not found in OrganicComponentRegistry`);
        }
        verifiedCount++;
      }
      
      console.log(`\n✅ ВАЛИДАЦИЯ ПРОЙДЕНА: Все ${verifiedCount} компонентов подтверждены в контракте`);
      console.log(`${'='.repeat(70)}\n`);
    }
    
    // 6. Финальный отчет
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log(`\n${'='.repeat(80)}`);
    console.log(`📊 ФИНАЛЬНЫЙ ОТЧЁТ ACTION 53`);
    console.log(`${'='.repeat(80)}`);
    console.log(`✅ Успешно: ${successCount}`);
    console.log(`❌ Ошибок: ${failCount}`);
    console.log(`📊 Всего: ${componentIds.length}`);
    console.log(`⏱️ Время выполнения: ${duration}s`);
    
    if (successCount > 0) {
      console.log(`\n🎉 Успешно зарегистрированы:`);
      results.filter(r => r.success).forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.componentId}`);
        console.log(`      → Root CID: ${result.rootCID}`);
        console.log(`      → Contract ID: ${result.contractComponentId}`);
      });
    }
    
    if (failCount > 0) {
      console.log(`\n❌ Ошибки:`);
      results.filter(r => !r.success).forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.componentId}: ${result.error}`);
      });
    }
    
    console.log(`\n✅ ACTION 53 завершен`);
    console.log(`${'='.repeat(80)}`);
    
    return {
      success: failCount === 0,
      successCount,
      failCount,
      totalCount: componentIds.length,
      results,
      duration: parseFloat(duration)
    };
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.error(`\n❌ ACTION 53 завершен с ошибкой: ${error.message}`);
    console.error(`⏱️ Время выполнения: ${duration}s`);
    throw error;
  }
}

// ====================================================================
// 🎯 EXPORTS
// ====================================================================

module.exports = {
  uploadSimpleFields,
  uploadComplexFields,
  uploadShareableData,
  updateRootMetadata,
  uploadRootMetadata,
  registerComponent,
  uploadToArweave,
  restoreSimpleFieldsToContract,
  restoreComplexFieldsToContract,
  action52_UnifiedArweaveUpload,
  action53_UnifiedContractRegistration
};

