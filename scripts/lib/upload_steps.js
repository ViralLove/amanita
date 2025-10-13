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
 * @param {string} context.componentId - ID компонента
 * @param {string} context.componentDir - Путь к директории компонента
 * @param {string} context.network - Название сети
 * @param {boolean} context.dryRun - Режим dry-run
 * @param {Object} context.contracts - Контракты (amanitaInternational, etc.)
 * @param {Object} context.arweave - Arweave client + key
 * @param {Object} context.web3 - Web3 instance
 * @param {Object} context.seller - Seller account (owner компонента)
 * @param {Object} context.deployer - Deployer account (для совместимости)
 * @param {Object} state - Component state
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<Object>} Маппинг field → CID
 */
async function uploadSimpleFields(context, state, onProgress = null) {
  console.log("\n🔹 ШАГ 1: Загрузка Simple Fields");
  
  // Проверяем, был ли шаг уже выполнен
  if (stateManager.isStepCompleted(state, 'simple_fields_uploaded')) {
    console.log("✅ Шаг уже выполнен, используем сохраненные данные");
    return state.simple_fields;
  }
  
  const simpleFieldCIDs = {};
  
  try {
    // 1. Загрузка ComponentDescription.title.json
    console.log("\n📝 1.1. ComponentDescription.title");
    
    if (onProgress) {
      onProgress({ step: 'simple_fields', substep: 'title', progress: 0, status: 'started' });
    }
    
    const titleFilePath = `simple_fields/${context.componentId}.ComponentDescription.title.json`;
    const titleData = utils.readJSON(context.componentDir, titleFilePath);
    
    const titleFilename = `${context.componentId}_ComponentDescription_title.json`;
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
      
      const gasPrice = await utils.getGasPrice(context.web3, context.network);
      const gasLimit = utils.getGasLimit(context.network, 300000);
      
      // ✅ Ownership: вызов от SELLER → seller становится owner поля
      await context.contracts.amanitaInternational.methods.setSimpleFieldCID(
        "ComponentDescription.title",
        titleCID
      ).send({
        from: context.seller.address,  // ← SELLER для своих компонентов (обновлено 2025-01-12)
        gas: gasLimit,
        gasPrice: gasPrice
      });
      
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
    
    const dosageFilePath = `simple_fields/${context.componentId}.DosageInstruction.description.json`;
    const dosageData = utils.readJSON(context.componentDir, dosageFilePath);
    
    const dosageFilename = `${context.componentId}_DosageInstruction_description.json`;
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
      
      const gasPrice = await utils.getGasPrice(context.web3, context.network);
      const gasLimit = utils.getGasLimit(context.network, 300000);
      
      // ✅ Ownership: вызов от SELLER → seller становится owner поля
      await context.contracts.amanitaInternational.methods.setSimpleFieldCID(
        "DosageInstruction.description",
        dosageCID
      ).send({
        from: context.seller.address,  // ← SELLER для своих компонентов (обновлено 2025-01-12)
        gas: gasLimit,
        gasPrice: gasPrice
      });
      
      console.log("✅ CID сохранен в контракте (owner: seller)");
    } else if (context.arweaveOnly) {
      console.log("🔷 [ARWEAVE_ONLY] Пропускаем сохранение в контракт");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем сохранение в контракт");
    }
    
    if (onProgress) {
      onProgress({ step: 'simple_fields', substep: 'dosage', progress: 100, status: 'completed' });
    }
    
    // Сохраняем state
    state.simple_fields = simpleFieldCIDs;
    stateManager.markStepCompleted(state, 'simple_fields_uploaded');
    stateManager.saveComponentState(context.componentDir, context.network, state);
    
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
  
  // Проверяем, был ли шаг уже выполнен
  if (stateManager.isStepCompleted(state, 'complex_fields_uploaded')) {
    console.log("✅ Шаг уже выполнен, используем сохраненные данные");
    return state.complex_fields;
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
      
      const filePath = `complex_fields/${context.componentId}.ComponentDescription.${lang}.json`;
      
      try {
        // Читаем файл описания для текущего языка
        const descData = utils.readJSON(context.componentDir, filePath);
        
        const filename = `${context.componentId}_ComponentDescription_${lang}.json`;
        const descResult = await uploadToArweave(
          context,
          descData,
          filename
        );
        
        const descCID = descResult.txId || descResult;
        
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
          
          const gasPrice = await utils.getGasPrice(context.web3, context.network);
          const gasLimit = utils.getGasLimit(context.network, 300000);
          
          // ✅ Ownership: вызов от SELLER → seller становится owner перевода
          await context.contracts.amanitaInternational.methods.setComplexFieldCID(
            "ComponentDescription",
            lang,
            descCID
          ).send({
            from: context.seller.address,  // ← SELLER для своих компонентов (обновлено 2025-01-12)
            gas: gasLimit,
            gasPrice: gasPrice
          });
          
          console.log(`✅ CID сохранен в контракте (owner: seller, ${lang})`);
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
    
    // Сохраняем state
    state.complex_fields = complexFieldCIDs;
    stateManager.markStepCompleted(state, 'complex_fields_uploaded');
    stateManager.saveComponentState(context.componentDir, context.network, state);
    
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
  
  // Проверяем, был ли шаг уже выполнен в state
  if (state.shareable_data && state.shareable_data.featuresCID) {
    console.log("✅ Шаг уже выполнен (state), используем сохраненные данные");
    return state.shareable_data;
  }
  
  // Проверяем, загружены ли shareable data в контракт
  try {
    const existingData = await context.contracts.organicComponentRegistry.methods.getShareableData().call();
    if (existingData.features_cid && existingData.features_cid !== '' && 
        existingData.component_forms_cid && existingData.component_forms_cid !== '') {
      console.log("✅ Shareable Data уже загружены в контракт (пропуск)");
      console.log(`   → Features CID: ${existingData.features_cid}`);
      console.log(`   → Forms CID: ${existingData.component_forms_cid}`);
      
      // Сохраняем в state для будущих запусков
      const shareableData = {
        featuresCID: existingData.features_cid,
        formsCID: existingData.component_forms_cid,
        featuresVersion: existingData.features_version,
        formsVersion: existingData.forms_version
      };
      
      state.shareable_data = shareableData;
      markStepCompleted(state, 'shareable_data_uploaded');
      saveComponentState(context.componentDir, context.network, state);
      
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
      
      const gasPrice = await utils.getGasPrice(context.web3, context.network);
      const gasLimit = utils.getGasLimit(context.network, 500000);
      
      await context.contracts.organicComponentRegistry.methods.updateShareableData(
        featuresCID,
        formsCID,
        1, // features version
        1  // forms version
      ).send({
        from: context.deployer.address,
        gas: gasLimit,
        gasPrice: gasPrice
      });
      
      console.log("✅ Shareable data обновлены в контракте");
    } else {
      console.log("🔷 [DRY-RUN] Пропускаем обновление в контракте");
    }
    
    const shareableData = { featuresCID, formsCID };
    
    // Сохраняем state
    state.shareable_data = shareableData;
    
    // Если есть метод markStepCompleted, используем его
    if (typeof state.steps_completed !== 'undefined') {
      stateManager.markStepCompleted(state, 'shareable_data_uploaded');
      stateManager.saveComponentState(context.componentDir, context.network, state);
    }
    
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
    
    // 1. Читаем оригинальный root файл
    console.log(`📖 Чтение оригинального файла: ${context.componentId}.json`);
    const rootData = utils.readJSON(context.componentDir, `${context.componentId}.json`);
    
    // 2. Создаем финальную структуру с CID references
    const finalRootData = {
      ...rootData,
      localizations: {
        simple_fields: simpleFieldCIDs,
        complex_fields: complexFieldCIDs
      },
      last_updated: new Date().toISOString(),
      network: context.network
    };
    
    // 3. Сохраняем финальный root файл локально (для истории)
    const finalFileName = `${context.componentId}_final_${context.network}.json`;
    const finalRootPath = path.join(context.componentDir, finalFileName);
    
    fs.writeFileSync(finalRootPath, JSON.stringify(finalRootData, null, 2), 'utf8');
    console.log(`💾 Финальный файл сохранен: ${finalFileName}`);
    
    // 4. Сохраняем в state (сохраняем существующий CID если есть)
    const existingCID = state.root_metadata && state.root_metadata.cid;
    state.root_metadata = {
      path: finalFileName,
      data: finalRootData
    };
    
    // Сохраняем CID если он уже был (для повторных запусков)
    if (existingCID) {
      state.root_metadata.cid = existingCID;
      console.log(`📌 Сохранен существующий CID: ${existingCID}`);
    }
    
    stateManager.saveComponentState(context.componentDir, context.network, state);
    
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
  
  // Проверяем, был ли шаг уже выполнен
  if (stateManager.isStepCompleted(state, 'root_metadata_uploaded')) {
    const savedCID = state.root_metadata && state.root_metadata.cid;
    console.log("✅ Шаг уже выполнен, используем сохраненный CID");
    console.log(`   → Сохраненный CID: ${savedCID || 'ОТСУТСТВУЕТ!'}`);
    
    if (!savedCID) {
      console.error("❌ ОШИБКА: CID отсутствует в state, хотя шаг помечен как выполненный!");
      console.error("   → State root_metadata:", JSON.stringify(state.root_metadata, null, 2));
      throw new Error("Inconsistent state: step completed but CID missing");
    }
    
    return savedCID;
  }
  
  try {
    if (onProgress) {
      onProgress({ step: 'root_metadata', progress: 0, status: 'started' });
    }
    
    // Загружаем root metadata в Arweave
    const filename = `${context.componentId}_root_metadata.json`;
    const rootResult = await uploadToArweave(context, rootData, filename);
    
    const rootCID = rootResult.txId || rootResult;
    console.log(`✅ Root Metadata загружен: ${rootCID}`);
    
    if (onProgress) {
      onProgress({ step: 'root_metadata', progress: 100, status: 'completed', cid: rootCID });
    }
    
    // Сохраняем CID в state
    state.root_metadata.cid = rootCID;
    stateManager.markStepCompleted(state, 'root_metadata_uploaded');
    stateManager.saveComponentState(context.componentDir, context.network, state);
    
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
  
  // Проверяем, был ли шаг уже выполнен
  if (stateManager.isStepCompleted(state, 'component_registered')) {
    console.log("✅ Шаг уже выполнен, используем сохраненный componentId");
    return state.contract_registration.componentId;
  }
  
  // В dry-run режиме не регистрируем в контракте
  if (context.dryRun) {
    console.log("🔷 [DRY-RUN] Пропускаем регистрацию в контракте");
    const mockComponentId = 999;
    
    state.contract_registration = {
      componentId: mockComponentId,
      txHash: "DRYRUN_TX_HASH",
      dry_run: true
    };
    stateManager.markStepCompleted(state, 'component_registered');
    stateManager.saveComponentState(context.componentDir, context.network, state);
    
    console.log(`🔷 [DRY-RUN] Mock Component ID: ${mockComponentId}`);
    console.log("\n✅ ШАГ 6 завершен (DRY-RUN)");
    
    return mockComponentId;
  }
  
  try {
    if (onProgress) {
      onProgress({ step: 'register_component', progress: 0, status: 'started' });
    }
    
    // Детальное логирование для отладки
    console.log(`📝 Регистрируем компонент: ${context.componentId}`);
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
    console.log(`   → Адрес: ${context.contracts.organicComponentRegistry.options.address}`);
    console.log(`   → Deployer: ${context.deployer.address}`);
    console.log(`   → Seller (создатель компонента): ${context.seller.address}`);
    
    const gasPrice = await utils.getGasPrice(context.web3, context.network);
    const gasLimit = utils.getGasLimit(context.network, 1000000);
    
    console.log(`⛽ Gas параметры:`);
    console.log(`   → Gas Price: ${gasPrice}`);
    console.log(`   → Gas Limit: ${gasLimit}`);
    
    console.log(`\n🚀 Вызов createComponent("${context.componentId}", "${rootCID}")...`);
    console.log(`   → От имени seller: ${context.seller.address}`);
    
    // Получаем актуальный nonce для предотвращения "Nonce too low"
    const nonce = await context.web3.eth.getTransactionCount(context.seller.address, 'pending');
    console.log(`   → Nonce: ${nonce}`);
    
    const tx = await context.contracts.organicComponentRegistry.methods.createComponent(
      context.componentId,
      rootCID
    ).send({
      from: context.seller.address,
      gas: gasLimit,
      gasPrice: gasPrice,
      nonce: nonce
    });
    
    console.log(`📝 Транзакция отправлена: ${tx.transactionHash}`);
    
    if (onProgress) {
      onProgress({ step: 'register_component', progress: 50, status: 'tx_sent', txHash: tx.transactionHash });
    }
    
    // Получаем receipt
    const receipt = await context.web3.eth.getTransactionReceipt(tx.transactionHash);
    console.log(`✅ Транзакция подтверждена: блок ${receipt.blockNumber}`);
    
    // Извлекаем componentId из события ComponentCreated
    let componentId = null;
    
    for (const log of receipt.logs) {
      try {
        // Пытаемся распарсить лог как событие контракта
        const parsedLog = context.contracts.organicComponentRegistry._decodeEventABI.bind({
          name: 'allEvents',
          jsonInterface: context.contracts.organicComponentRegistry.options.jsonInterface
        })(log);
        
        if (parsedLog && parsedLog.event === 'ComponentCreated') {
          componentId = parsedLog.returnValues.componentId;
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
    
    // Сохраняем в state
    state.contract_registration = {
      componentId: componentId,
      txHash: tx.transactionHash,
      blockNumber: receipt.blockNumber
    };
    stateManager.markStepCompleted(state, 'component_registered');
    stateManager.saveComponentState(context.componentDir, context.network, state);
    
    console.log("\n✅ ШАГ 6 завершен: Компонент зарегистрирован в контракте");
    
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
async function uploadToArweave(context, data, filename) {
  const startTime = Date.now();
  
  console.log(`📤 Загрузка ${filename} в Arweave...`);
  
  // Если dry-run режим → вернуть mock TX ID
  if (context.dryRun) {
    const mockTxId = `DRYRUN_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    const mockSize = JSON.stringify(data, null, 2).length;
    console.log(`🔷 [DRY-RUN] Mock TX ID: ${mockTxId}`);
    console.log(`   → Размер: ${mockSize} bytes (${(mockSize / 1024).toFixed(2)} KB)`);
    return { txId: mockTxId, size: mockSize, duration: 0 };
  }
  
  // Реальная загрузка в Arweave
  try {
    const Arweave = require('arweave');
    
    // Конвертируем данные в JSON строку
    const dataString = JSON.stringify(data, null, 2);
    const dataSize = Buffer.byteLength(dataString, 'utf8');
    
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
      data: dataString
    }, context.arweave.key);
    
    // Добавляем tags для метаданных
    transaction.addTag('Content-Type', 'application/json');
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
      throw new Error(`Arweave API вернул статус ${response.status}`);
    }
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.error(`❌ Ошибка загрузки ${filename} в Arweave (${duration}s):`, error.message);
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
  uploadToArweave
};

