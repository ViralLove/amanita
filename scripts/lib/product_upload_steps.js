/**
 * 🛠️ Product Upload Steps Module
 * 
 * Шаги загрузки продуктов в Arweave для Action 42
 * 
 * @version 1.0.0
 * @date 2025-10-14
 */

const fs = require('fs');
const path = require('path');
const { uploadToArweave } = require('./upload_steps');
const productUtils = require('./product_utils');
const { sleep } = require('./upload_utils');  // ✅ Centralized delay utility

// ====================================================================
// 🔹 HELPER FUNCTIONS: Resume Capability
// ====================================================================

/**
 * Загрузить существующий mapping файл
 * @param {string} outputDir - Директория с mapping файлом
 * @param {string} filename - Имя mapping файла
 * @returns {Object} Existing mapping или пустой объект
 */
function loadExistingMapping(outputDir, filename = 'product_combined_mapping.json') {
  const mappingPath = path.join(outputDir, filename);
  
  if (!fs.existsSync(mappingPath)) {
    console.log(`🆕 Mapping файл не найден: ${filename}`);
    console.log(`   → Создаем новый mapping`);
    return {};
  }
  
  try {
    const data = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
    const productCount = Object.keys(data).length;
    
    console.log(`✅ Загружен existing mapping: ${filename}`);
    console.log(`   → Найдено продуктов: ${productCount}`);
    
    // Validate structure
    let validCount = 0;
    let invalidCount = 0;
    
    for (const [productId, mapping] of Object.entries(data)) {
      if (isValidArweaveCID(mapping.title_cid) && isValidArweaveCID(mapping.product_cid)) {
        validCount++;
      } else {
        invalidCount++;
        console.warn(`   ⚠️ Invalid CID for ${productId}, will re-upload`);
      }
    }
    
    console.log(`   → Валидных: ${validCount}, Невалидных: ${invalidCount}`);
    return data;
    
  } catch (error) {
    console.error(`❌ Ошибка загрузки mapping: ${error.message}`);
    console.warn(`   → Создаем новый mapping`);
    return {};
  }
}

/**
 * Проверить валидность Arweave CID
 * @param {string} cid - Arweave transaction ID
 * @returns {boolean} true если CID валидный
 */
function isValidArweaveCID(cid) {
  // Arweave TX ID = 43 characters, base64url format
  if (!cid || typeof cid !== 'string') {
    return false;
  }
  
  if (cid.length !== 43) {
    return false;
  }
  
  // Base64url format: [A-Za-z0-9_-]
  const base64urlPattern = /^[A-Za-z0-9_-]{43}$/;
  return base64urlPattern.test(cid);
}

/**
 * Объединить существующий и новый mapping
 * @param {Object} existingMapping - Существующий mapping
 * @param {Object} newMapping - Новый mapping
 * @returns {Object} Объединенный mapping
 */
function mergeMappings(existingMapping, newMapping) {
  console.log(`\n🔀 Объединение mapping файлов...`);
  
  const merged = { ...existingMapping };
  let newCount = 0;
  let updatedCount = 0;
  let skippedCount = 0;
  
  for (const [productId, newData] of Object.entries(newMapping)) {
    if (!existingMapping[productId]) {
      // Новый продукт
      merged[productId] = {
        ...newData,
        uploaded_at: new Date().toISOString()
      };
      newCount++;
    } else if (
      newData.title_cid !== existingMapping[productId].title_cid ||
      newData.product_cid !== existingMapping[productId].product_cid
    ) {
      // Обновленный продукт
      merged[productId] = {
        ...existingMapping[productId],
        ...newData,
        updated_at: new Date().toISOString()
      };
      updatedCount++;
    } else {
      // Без изменений
      skippedCount++;
    }
  }
  
  console.log(`   → Новых: ${newCount}`);
  console.log(`   → Обновленных: ${updatedCount}`);
  console.log(`   → Без изменений: ${skippedCount}`);
  console.log(`   → Итого: ${Object.keys(merged).length}`);
  
  return merged;
}

// ====================================================================
// 📤 PRODUCT UPLOAD STEPS
// ====================================================================

/**
 * Загрузка title JSON файлов в Arweave (с resume capability)
 * @param {Object} context - Upload context
 * @param {string} productsDir - Директория с продуктами
 * @param {string} outputDir - Директория для mapping файлов (для resume)
 * @returns {Promise<Object>} Mapping product_id → title_cid
 */
async function uploadTitleFiles(context, productsDir, outputDir) {
  console.log("\n🔍 ШАГ 1: Загрузка title файлов в Arweave");
  console.log("=".repeat(60));
  
  // ✅ NEW: Load existing mapping for resume
  const existingMapping = loadExistingMapping(outputDir, 'product_combined_mapping.json');
  
  const titleMapping = {};
  const productDirs = fs.readdirSync(productsDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);
  
  console.log(`📁 Найдено ${productDirs.length} продуктов для обработки`);
  
  let skippedCount = 0;
  let uploadedCount = 0;
  let errorCount = 0;
  
  for (const productId of productDirs) {
    const productDir = path.join(productsDir, productId);
    const titleFile = path.join(productDir, `${productId}.titles.json`);
    
    if (!fs.existsSync(titleFile)) {
      console.warn(`⚠️ Title файл не найден: ${titleFile}`);
      errorCount++;
      continue;
    }
    
    try {
      console.log(`\n📦 Обработка продукта: ${productId}`);
      
      // ✅ NEW: Check if already uploaded to Arweave
      let titleCID;
      let titleSkipped = false;
      
      if (existingMapping[productId]?.title_cid) {
        const existingCID = existingMapping[productId].title_cid;
        
        if (isValidArweaveCID(existingCID)) {
          console.log(`   ✅ Title уже загружен в Arweave, используем существующий CID`);
          console.log(`   → CID: ${existingCID}`);
          console.log(`   → URL: https://arweave.net/${existingCID}`);
          
          titleCID = existingCID;
          titleSkipped = true;
          skippedCount++;
          
          // ✅ IMPORTANT: Don't continue yet - still need to check AmanitaInternational!
        } else {
          console.warn(`   ⚠️ Invalid CID found: ${existingCID}`);
          console.warn(`   → Will re-upload to Arweave`);
        }
      } else {
        console.log(`   🆕 Новый продукт, загружаем в Arweave...`);
      }
      
      // Upload to Arweave only if not skipped
      if (!titleSkipped) {
      
        // Read title JSON
        const titleData = JSON.parse(fs.readFileSync(titleFile, 'utf8'));
        console.log(`   → Title файл: ${titleFile}`);
        console.log(`   → Языки: ${Object.keys(titleData).join(', ')}`);
        
        // Upload combined titles to Arweave
        const result = await uploadToArweave(context, titleData, `${productId}.titles.json`);
        titleCID = result.txId;
        uploadedCount++;
      } else {
        // Title already in Arweave, just read the languages
        const titleData = JSON.parse(fs.readFileSync(titleFile, 'utf8'));
      }
      
      // Read title JSON for language info
      const titleData = JSON.parse(fs.readFileSync(titleFile, 'utf8'));
      
      // Prepare title mapping entry
      titleMapping[productId] = {
        cid: titleCID,
        size: titleSkipped ? (existingMapping[productId]?.title_size || 0) : (result?.size || 0),
        url: `https://arweave.net/${titleCID}`,
        languages: Object.keys(titleData),
        uploaded: !titleSkipped,
        skipped: titleSkipped
      };
      
      if (!titleSkipped) {
        console.log(`   ✅ Title загружен в Arweave: ${titleCID}`);
        console.log(`   → URL: ${titleMapping[productId].url}`);
        console.log(`   → Языки: ${Object.keys(titleData).join(', ')}`);
      }
      
      // ✅ CRITICAL: Save to AmanitaInternational as Simple Field
      // Execute even if title was resumed from Arweave (CID exists but maybe not in contract yet)
      // Simple Field = ОДИН CID содержит ВСЕ языки (мультиязычный JSON)
      if (!context.dryRun && !context.arweaveOnly) {
        console.log(`\n   🔷 Сохранение title в AmanitaInternational (Simple Field)...`);
        
        const signer = context.seller?.signer || context.deployer?.signer;
        if (!signer) {
          console.warn(`   ⚠️ No signer available, skipping AmanitaInternational upload`);
        } else if (!context.contracts?.amanitaInternational) {
          console.warn(`   ⚠️ AmanitaInternational contract not loaded, skipping`);
        } else {
          try {
            const amanitaIntlWithSigner = context.contracts.amanitaInternational.connect(signer);
            
            // ✅ Use Simple Field format: один CID для всех языков
            // Field key format: "ProductName.{product_id}"
            const fieldKey = `ProductName.${productId}`;
            
            // ✅ Check if already in contract (to avoid unnecessary tx)
            let needsUpload = true;
            try {
              const existingContractCID = await amanitaIntlWithSigner.getSimpleFieldCID(fieldKey);
              if (existingContractCID === titleCID) {
                console.log(`   ✅ Title уже в AmanitaInternational (field: ${fieldKey})`);
                needsUpload = false;
              }
            } catch (e) {
              // Field doesn't exist, need to upload
              needsUpload = true;
            }
            
            if (needsUpload) {
              const tx = await amanitaIntlWithSigner.setSimpleFieldCID(
                fieldKey,   // e.g., "ProductName.amanita1"
                titleCID    // CID pointing to multilingual JSON
              );
              
              await tx.wait();
              await sleep(500); // ✅ Delay to prevent nonce race condition
              
              console.log(`   ✅ Title сохранен в AmanitaInternational`);
              console.log(`      Field: ${fieldKey}`);
              console.log(`      CID: ${titleCID.substring(0, 20)}...`);
              console.log(`      Owner: ${signer.address}`);
            }
            
            // Mark in mapping that this product has AmanitaInternational entry
            titleMapping[productId].amanita_intl_field = fieldKey;
            titleMapping[productId].amanita_intl_uploaded = true;
            
          } catch (intlError) {
            console.warn(`   ⚠️ Failed to save to AmanitaInternational: ${intlError.message}`);
            // Continue - not critical, product still has title via Arweave
          }
        }
      } else if (context.arweaveOnly) {
        console.log(`   🔷 [ARWEAVE_ONLY] Пропускаем AmanitaInternational`);
      } else {
        console.log(`   🔷 [DRY-RUN] Пропускаем AmanitaInternational`);
      }
      
    } catch (error) {
      console.error(`❌ Ошибка загрузки title для ${productId}:`, error.message);
      errorCount++;
      throw error;
    }
  }
  
  // ✅ NEW: Statistics with skip info
  console.log(`\n✅ ШАГ 1 завершен:`);
  console.log(`   → Загружено: ${uploadedCount}`);
  console.log(`   → Пропущено (уже в Arweave): ${skippedCount}`);
  console.log(`   → Ошибок: ${errorCount}`);
  console.log(`   → Итого обработано: ${Object.keys(titleMapping).length}`);
  
  return titleMapping;
}

/**
 * Загрузка изображений продуктов в Arweave (с resume capability)
 * @param {Object} context - Upload context
 * @param {string} productsDir - Директория с продуктами
 * @param {string} sellerId - Seller business ID для правильного пути к images
 * @param {string} outputDir - Директория для mapping файлов (для resume)
 * @returns {Promise<Object>} Mapping product_id → image_cid
 */
async function uploadProductImages(context, productsDir, sellerId, outputDir) {
  console.log("\n🖼️ ШАГ 1.5: Загрузка изображений продуктов в Arweave");
  console.log("=".repeat(60));
  
  const imageMapping = {};
  const productDirs = fs.readdirSync(productsDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory() && !dirent.name.startsWith('_'))
    .map(dirent => dirent.name);
  
  console.log(`📁 Найдено ${productDirs.length} продуктов для обработки изображений`);
  
  // ✅ Load existing mapping for resume
  const existingMapping = loadExistingMapping(outputDir, 'product_combined_mapping.json');
  
  let uploadedCount = 0;
  let skippedCount = 0;
  let noImageCount = 0;
  let errorCount = 0;
  
  for (const productId of productDirs) {
    const productFile = path.join(productsDir, productId, `${productId}.json`);
    
    if (!fs.existsSync(productFile)) {
      console.warn(`⚠️ Product JSON не найден: ${productFile}`);
      errorCount++;
      continue;
    }
    
    try {
      console.log(`\n📦 Обработка изображения для: ${productId}`);
      
      // Read product JSON to get image_file
      const productData = JSON.parse(fs.readFileSync(productFile, 'utf8'));
      const imageFile = productData.images?.cover;
      
      if (!imageFile) {
        console.log(`   ⚠️ No image specified in product JSON`);
        noImageCount++;
        continue;
      }
      
      // ✅ Check if already uploaded (resume capability)
      if (existingMapping[productId]?.image_cid) {
        const existingCID = existingMapping[productId].image_cid;
        
        if (isValidArweaveCID(existingCID)) {
          console.log(`   ✅ Image уже загружено в Arweave, пропускаем`);
          console.log(`   → CID: ${existingCID}`);
          console.log(`   → URL: https://arweave.net/${existingCID}`);
          
          imageMapping[productId] = {
            cid: existingCID,
            filename: imageFile,
            url: `https://arweave.net/${existingCID}`,
            skipped: true
          };
          
          skippedCount++;
          continue;
        }
      }
      
      // Check if image file exists locally
      const imagePath = productUtils.getImagePath(imageFile, sellerId);
      if (!fs.existsSync(imagePath)) {
        console.error(`   ❌ Image file not found: ${imagePath}`);
        console.error(`      Expected: ${imageFile}`);
        errorCount++;
        continue;
      }
      
      console.log(`   📂 Найдено изображение: ${imageFile}`);
      console.log(`   → Путь: ${imagePath}`);
      
      // Read image file as buffer
      const imageBuffer = fs.readFileSync(imagePath);
      const imageSizeKB = (imageBuffer.length / 1024).toFixed(2);
      console.log(`   → Размер: ${imageSizeKB} KB`);
      
      // Detect content type from extension
      const ext = path.extname(imageFile).toLowerCase();
      const contentTypeMap = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
      };
      const contentType = contentTypeMap[ext] || 'image/jpeg';
      console.log(`   → Content-Type: ${contentType}`);
      
      console.log(`   🔷 Загрузка в Arweave...`);
      
      // ✅ Upload to Arweave with explicit Content-Type
      const result = await uploadToArweave(
        context,
        imageBuffer,
        `${productId}_cover${ext}`,
        { contentType: contentType }  // ✅ Pass Content-Type explicitly
      );
      
      const imageCID = result.txId;
      
      imageMapping[productId] = {
        cid: imageCID,
        filename: imageFile,
        size: imageBuffer.length,
        url: `https://arweave.net/${imageCID}`,
        contentType: contentType,
        uploaded: true
      };
      
      console.log(`   ✅ Image загружено: ${imageCID}`);
      console.log(`   → URL: ${imageMapping[productId].url}`);
      
      // Update product JSON with image CID
      productData.images.cover_cid = imageCID;
      productData.images.cover_url = imageMapping[productId].url;
      fs.writeFileSync(productFile, JSON.stringify(productData, null, 2), 'utf8');
      console.log(`   ✅ Product JSON обновлен с image CID`);
      
      uploadedCount++;
      
    } catch (error) {
      console.error(`❌ Ошибка загрузки изображения для ${productId}:`, error.message);
      errorCount++;
      // Continue with other products
    }
  }
  
  console.log(`\n✅ ШАГ 1.5 завершен:`);
  console.log(`   → Загружено: ${uploadedCount}`);
  console.log(`   → Пропущено (уже в Arweave): ${skippedCount}`);
  console.log(`   → Без изображений: ${noImageCount}`);
  console.log(`   → Ошибок: ${errorCount}`);
  console.log(`   → Итого обработано: ${Object.keys(imageMapping).length}`);
  
  return imageMapping;
}

/**
 * Загрузка product JSON файлов в Arweave (с resume capability)
 * @param {Object} context - Upload context
 * @param {string} productsDir - Директория с продуктами
 * @param {Object} titleMapping - Mapping product_id → title_cid
 * @param {string} outputDir - Директория для mapping файлов (для resume)
 * @returns {Promise<Object>} Mapping product_id → product_cid
 */
async function uploadProductFiles(context, productsDir, titleMapping, outputDir) {
  console.log("\n🔍 ШАГ 2: Загрузка product файлов в Arweave");
  console.log("=".repeat(60));
  
  // ✅ NEW: Load existing mapping for resume
  const existingMapping = loadExistingMapping(outputDir, 'product_combined_mapping.json');
  
  const productMapping = {};
  const productDirs = fs.readdirSync(productsDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);
  
  console.log(`📁 Найдено ${productDirs.length} продуктов для обработки`);
  
  let skippedCount = 0;
  let uploadedCount = 0;
  let updatedLocalCount = 0;
  let errorCount = 0;
  
  for (const productId of productDirs) {
    const productDir = path.join(productsDir, productId);
    const productFile = path.join(productDir, `${productId}.json`);
    
    if (!fs.existsSync(productFile)) {
      console.warn(`⚠️ Product файл не найден: ${productFile}`);
      errorCount++;
      continue;
    }
    
    try {
      console.log(`\n📦 Обработка продукта: ${productId}`);
      
      // Read product JSON
      const productData = JSON.parse(fs.readFileSync(productFile, 'utf8'));
      console.log(`   → Product файл: ${productFile}`);
      
      // Update title CID in product data
      if (titleMapping[productId]) {
        const newTitleCID = titleMapping[productId].cid;
        const oldTitleCID = productData.title;
        
        if (oldTitleCID !== newTitleCID) {
          productData.title = newTitleCID;
          console.log(`   → Title CID обновлен: ${newTitleCID}`);
          
          // ✅ NEW: Update local file with new title CID
          fs.writeFileSync(productFile, JSON.stringify(productData, null, 2), 'utf8');
          updatedLocalCount++;
        } else {
          console.log(`   → Title CID уже актуален: ${newTitleCID}`);
        }
      } else {
        console.warn(`   ⚠️ Title CID не найден для ${productId}`);
      }
      
      // ✅ NEW: Check if product already uploaded
      if (existingMapping[productId]?.product_cid) {
        const existingCID = existingMapping[productId].product_cid;
        
        // Check if title CID changed (need re-upload)
        const titleChanged = titleMapping[productId]?.uploaded === true;
        
        if (isValidArweaveCID(existingCID) && !titleChanged) {
          console.log(`   ✅ Product уже загружен, используем существующий CID`);
          console.log(`   → CID: ${existingCID}`);
          console.log(`   → URL: https://arweave.net/${existingCID}`);
          
          productMapping[productId] = {
            cid: existingCID,
            url: existingMapping[productId].product_url || `https://arweave.net/${existingCID}`,
            title_cid: titleMapping[productId]?.cid || existingMapping[productId].title_cid,
            size: existingMapping[productId].product_size || 0,
            skipped: true  // ✅ Mark as skipped
          };
          
          skippedCount++;
          continue;  // ✅ SKIP upload!
        } else if (titleChanged) {
          console.log(`   🔄 Title CID изменился, загружаем product заново...`);
        } else {
          console.warn(`   ⚠️ Invalid CID found: ${existingCID}`);
          console.warn(`   → Will re-upload to Arweave`);
        }
      } else {
        console.log(`   🆕 Новый продукт, загружаем в Arweave...`);
      }
      
      // ✅ Upload to Arweave (only if not skipped)
      const result = await uploadToArweave(context, productData, `${productId}.json`);
      
      productMapping[productId] = {
        cid: result.txId,
        size: result.size,
        url: result.url || `https://arweave.net/${result.txId}`,
        title_cid: titleMapping[productId]?.cid || null,
        uploaded: true  // ✅ Mark as newly uploaded
      };
      
      console.log(`   ✅ Product загружен: ${result.txId}`);
      console.log(`   → URL: ${productMapping[productId].url}`);
      
      uploadedCount++;
      
    } catch (error) {
      console.error(`❌ Ошибка загрузки product для ${productId}:`, error.message);
      errorCount++;
      throw error;
    }
  }
  
  // ✅ NEW: Statistics with skip info
  console.log(`\n✅ ШАГ 2 завершен:`);
  console.log(`   → Загружено: ${uploadedCount}`);
  console.log(`   → Пропущено (уже в Arweave): ${skippedCount}`);
  console.log(`   → Локальных файлов обновлено: ${updatedLocalCount}`);
  console.log(`   → Ошибок: ${errorCount}`);
  console.log(`   → Итого обработано: ${Object.keys(productMapping).length}`);
  
  return productMapping;
}

/**
 * Создание mapping файлов (с merge existing)
 * @param {string} outputDir - Директория для сохранения mapping файлов
 * @param {Object} titleMapping - Mapping product_id → title_cid
 * @param {Object} productMapping - Mapping product_id → product_cid
 * @param {Object} existingMapping - Existing combined mapping (optional)
 * @returns {Object} Paths to created mapping files
 */
function createMappingFiles(outputDir, titleMapping, productMapping, imageMapping = {}, existingMapping = {}) {
  console.log("\n🔍 ШАГ 3: Создание mapping файлов");
  console.log("=".repeat(60));
  
  // ✅ NEW: Prepare combined mapping with merge
  const combinedMapping = {};
  
  for (const productId in titleMapping) {
    const existing = existingMapping[productId] || {};
    const titleInfo = titleMapping[productId];
    const imageInfo = imageMapping[productId];
    const productInfo = productMapping[productId];
    
    combinedMapping[productId] = {
      title_cid: titleInfo.cid,
      product_cid: productInfo?.cid || existing.product_cid,
      title_url: titleInfo.url || `https://arweave.net/${titleInfo.cid}`,
      product_url: productInfo?.url || existing.product_url || `https://arweave.net/${productInfo?.cid}`,
      languages: titleInfo.languages || existing.languages || [],
      // ✅ NEW: Image fields
      ...(imageInfo?.cid ? { image_cid: imageInfo.cid } : { image_cid: existing.image_cid || null }),
      ...(imageInfo?.url ? { image_url: imageInfo.url } : { image_url: existing.image_url || null }),
      ...(imageInfo?.filename ? { image_filename: imageInfo.filename } : { image_filename: existing.image_filename || null }),
      // ✅ NEW: AmanitaInternational integration fields
      ...(titleInfo.amanita_intl_field ? { amanita_intl_field: titleInfo.amanita_intl_field } : {}),
      ...(titleInfo.amanita_intl_uploaded ? { amanita_intl_uploaded: titleInfo.amanita_intl_uploaded } : {}),
      // ✅ Preserve metadata
      created_at: existing.created_at || existing.uploaded_at || new Date().toISOString(),
      // ✅ Add update timestamp if changed
      ...(titleInfo.uploaded || imageInfo?.uploaded || productInfo?.uploaded ? { updated_at: new Date().toISOString() } : {}),
      // ✅ Add sizes if available
      ...(titleInfo.size ? { title_size: titleInfo.size } : {}),
      ...(imageInfo?.size ? { image_size: imageInfo.size } : { image_size: existing.image_size || null }),
      ...(productInfo?.size ? { product_size: productInfo.size } : {})
    };
  }
  
  // 1. Combined mapping (title + product CIDs)
  const combinedMappingFile = path.join(outputDir, 'product_combined_mapping.json');
  fs.writeFileSync(combinedMappingFile, JSON.stringify(combinedMapping, null, 2), 'utf8');
  console.log(`✅ Combined mapping: ${combinedMappingFile}`);
  console.log(`   → Продуктов: ${Object.keys(combinedMapping).length}`);
  
  // 2. Title CID mapping only
  const titleCIDMapping = {};
  for (const productId in titleMapping) {
    titleCIDMapping[productId] = titleMapping[productId].cid;
  }
  const titleMappingFile = path.join(outputDir, 'product_title_cid_mapping.json');
  fs.writeFileSync(titleMappingFile, JSON.stringify(titleCIDMapping, null, 2), 'utf8');
  console.log(`✅ Title CID mapping: ${titleMappingFile}`);
  
  // 3. Product CID mapping only
  const productCIDMapping = {};
  for (const productId in productMapping) {
    productCIDMapping[productId] = productMapping[productId].cid;
  }
  const productMappingFile = path.join(outputDir, 'product_cid_mapping.json');
  fs.writeFileSync(productMappingFile, JSON.stringify(productCIDMapping, null, 2), 'utf8');
  console.log(`✅ Product CID mapping: ${productMappingFile}`);
  
  console.log(`\n✅ ШАГ 3 завершен: Mapping файлы созданы`);
  
  return {
    titleMappingFile,
    productMappingFile,
    combinedMappingFile,
    mappings: combinedMapping
  };
}

/**
 * Основная функция Action 42: Объединенная загрузка в Arweave (с resume)
 * @param {Object} context - Upload context
 * @param {string} productsDir - Директория с продуктами
 * @param {string} outputDir - Директория для mapping файлов
 * @returns {Promise<Object>} Результаты загрузки
 */
async function action42_UnifiedArweaveUpload(context, productsDir, outputDir) {
  console.log("\n" + "=".repeat(80));
  console.log("🚀 ACTION 42: ОБЪЕДИНЕННАЯ ЗАГРУЗКА В ARWEAVE (WITH RESUME)");
  console.log("=".repeat(80));
  console.log(`📁 Products dir: ${productsDir}`);
  console.log(`📁 Output dir: ${outputDir}`);
  console.log(`🔷 Dry-run: ${context.dryRun ? 'ENABLED' : 'DISABLED'}`);
  console.log(`🔷 Resume: ENABLED ✅`);
  
  const startTime = Date.now();
  
  try {
    // ✅ NEW: Load existing mapping for resume
    const existingMapping = loadExistingMapping(outputDir, 'product_combined_mapping.json');
    
    // Get seller ID from config
    const sellerId = context.config?.get('seller.businessId') || 'Iveta';
    
    // Шаг 1: Загрузка title файлов (with resume)
    const titleMapping = await uploadTitleFiles(context, productsDir, outputDir);
    
    // Шаг 1.5: Загрузка изображений продуктов (✅ NEW!)
    const imageMapping = await uploadProductImages(context, productsDir, sellerId, outputDir);
    
    // Шаг 2: Загрузка product файлов (with resume)
    const productMapping = await uploadProductFiles(context, productsDir, titleMapping, outputDir);
    
    // Шаг 3: Создание mapping файлов (with merge + images)
    const mappingResults = createMappingFiles(outputDir, titleMapping, productMapping, imageMapping, existingMapping);
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    // ✅ NEW: Calculate statistics
    const titleSkipped = Object.values(titleMapping).filter(m => m.skipped).length;
    const titleUploaded = Object.values(titleMapping).filter(m => m.uploaded).length;
    const imageSkipped = Object.values(imageMapping).filter(m => m.skipped).length;
    const imageUploaded = Object.values(imageMapping).filter(m => m.uploaded).length;
    const productSkipped = Object.values(productMapping).filter(m => m.skipped).length;
    const productUploaded = Object.values(productMapping).filter(m => m.uploaded).length;
    
    console.log("\n" + "=".repeat(80));
    console.log("✅ ACTION 42 ЗАВЕРШЕН УСПЕШНО");
    console.log("=".repeat(80));
    console.log(`⏱️ Время выполнения: ${duration}s`);
    console.log(`📊 Статистика:`);
    console.log(`   → Title файлов:`);
    console.log(`      • Загружено: ${titleUploaded}`);
    console.log(`      • Пропущено (resume): ${titleSkipped}`);
    console.log(`      • Всего: ${Object.keys(titleMapping).length}`);
    console.log(`   → Image файлов:`);
    console.log(`      • Загружено: ${imageUploaded}`);
    console.log(`      • Пропущено (resume): ${imageSkipped}`);
    console.log(`      • Всего: ${Object.keys(imageMapping).length}`);
    console.log(`   → Product файлов:`);
    console.log(`      • Загружено: ${productUploaded}`);
    console.log(`      • Пропущено (resume): ${productSkipped}`);
    console.log(`      • Всего: ${Object.keys(productMapping).length}`);
    console.log(`   → Mapping файлов создано: 3`);
    
    // ✅ NEW: Cost savings message
    if (titleSkipped > 0 || imageSkipped > 0 || productSkipped > 0) {
      const totalSkipped = titleSkipped + imageSkipped + productSkipped;
      console.log("");
      console.log(`💰 Resume capability сэкономил ${totalSkipped} загрузок в Arweave!`);
    }
    
    return {
      success: true,
      duration: parseFloat(duration),
      statistics: {
        titleFiles: Object.keys(titleMapping).length,
        titleUploaded: titleUploaded,
        titleSkipped: titleSkipped,
        productFiles: Object.keys(productMapping).length,
        productUploaded: productUploaded,
        productSkipped: productSkipped,
        mappingFiles: 3,
        totalSkipped: titleSkipped + productSkipped
      },
      mappings: mappingResults.mappings,
      files: {
        titleMapping: mappingResults.titleMappingFile,
        productMapping: mappingResults.productMappingFile,
        combinedMapping: mappingResults.combinedMappingFile
      }
    };
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log("\n" + "=".repeat(80));
    console.log("❌ ACTION 42 ЗАВЕРШЕН С ОШИБКОЙ");
    console.log("=".repeat(80));
    console.log(`⏱️ Время выполнения: ${duration}s`);
    console.error(`❌ Ошибка: ${error.message}`);
    
    return {
      success: false,
      duration: parseFloat(duration),
      error: error.message
    };
  }
}

/**
 * Clear existing catalog before registration
 * Prevents duplicate products from multiple Action 444 runs
 * @param {Object} context - Upload context
 * @returns {Promise<Object>} - Clear results
 */
async function clearExistingCatalog(context) {
  console.log("\n🧹 ШАГ 0: Очистка существующего каталога");
  console.log("=".repeat(60));
  
  const { productRegistry, seller } = context;
  
  if (!productRegistry) {
    throw new Error("ProductRegistry not initialized");
  }
  
  if (!seller?.address) {
    throw new Error("Seller address not provided");
  }
  
  // Check existing products
  const existingProducts = await productRegistry.getProductsBySeller(seller.address);
  console.log(`🔍 Найдено существующих продуктов: ${existingProducts.length}`);
  
  if (existingProducts.length === 0) {
    console.log(`✅ Каталог пустой, очистка не требуется`);
    return { cleared: 0, skipped: true };
  }
  
  // Verify seller has signer
  if (!seller.signer) {
    throw new Error('Seller signer required for catalog clearing');
  }
  
  // Clear catalog
  console.log(`🧹 Очищаем ${existingProducts.length} продуктов...`);
  
  const productRegistryWithSigner = productRegistry.connect(seller.signer);
  const tx = await productRegistryWithSigner.clearSellerCatalog(seller.address);
  const receipt = await tx.wait();
  
  // Delay for nonce
  await sleep(500);
  
  console.log(`✅ Каталог очищен`);
  console.log(`   → TX: ${receipt.hash}`);
  console.log(`   → Продуктов удалено: ${existingProducts.length}`);
  
  return { 
    cleared: existingProducts.length, 
    txHash: receipt.hash,
    skipped: false
  };
}

/**
 * Регистрация продуктов в ProductRegistry контракте
 * @param {Object} context - Upload context
 * @param {Object} productMapping - Mapping product_id → product_cid
 * @param {Object} productData - Данные продуктов с component_ids
 * @returns {Promise<Object>} Mapping product_id → contract_product_id
 */
async function registerProductsInContract(context, productMapping, productData) {
  console.log("\n🔍 ШАГ 1: Регистрация продуктов в ProductRegistry");
  console.log("=".repeat(60));
  
  const registrationResults = {};
  const productIds = Object.keys(productMapping);
  
  console.log(`📁 Найдено ${productIds.length} продуктов для регистрации`);
  
  for (const productId of productIds) {
    try {
      console.log(`\n📦 Регистрация продукта: ${productId}`);
      
      // Получаем данные продукта
      const product = productData[productId];
      if (!product) {
        console.warn(`⚠️ Данные продукта не найдены: ${productId}`);
        continue;
      }
      
      // Подготавливаем componentIds (component_business_id strings для контракта)
      const componentIds = product.components.map(comp => comp.component_business_id).filter(id => id && id !== '');
      const metadataCID = productMapping[productId].product_cid;
      
      console.log(`   → Component Business IDs: [${componentIds.join(', ')}]`);
      console.log(`   → Metadata CID: ${metadataCID}`);
      
      // В dry-run режиме используем mock component IDs если реальные не найдены
      if (context.dryRun && componentIds.length === 0) {
        const mockComponentIds = product.components.map((_, index) => `mock_component_${index + 1}`);
        console.log(`   🔷 [DRY-RUN] Используем mock Component IDs: [${mockComponentIds.join(', ')}]`);
        componentIds.push(...mockComponentIds);
      }
      
      if (context.dryRun) {
        // Dry-run режим
        const mockProductId = Math.floor(Math.random() * 1000000) + 1;
        registrationResults[productId] = {
          contractProductId: mockProductId,
          contractBusinessId: productId,
          success: true,
          txHash: `DRYRUN_${Date.now()}_${Math.random().toString(36).substring(7)}`
        };
        console.log(`   🔷 [DRY-RUN] Mock Product ID: ${mockProductId}`);
      } else {
        // Реальная регистрация в контракте
        if (!context.productRegistry) {
          throw new Error("ProductRegistry контракт не инициализирован");
        }
        
        const tx = await context.productRegistry.createProduct(productId, componentIds, metadataCID);
        const receipt = await tx.wait();
        
        // ✅ Delay to prevent nonce race condition in batch operations
        await sleep(500);
        
        // Получаем productId из события
        const event = receipt.logs.find(log => {
          try {
            const parsed = context.productRegistry.interface.parseLog(log);
            return parsed.name === "ProductCreated";
          } catch {
            return false;
          }
        });
        
        if (!event) {
          throw new Error("Событие ProductCreated не найдено");
        }
        
        const parsedEvent = context.productRegistry.interface.parseLog(event);
        const contractProductId = parsedEvent.args.productId.toString();
        const contractBusinessId = parsedEvent.args.businessId;
        
        registrationResults[productId] = {
          contractProductId: contractProductId,
          contractBusinessId: contractBusinessId,
          success: true,
          txHash: receipt.transactionHash
        };
        
        console.log(`   ✅ Продукт зарегистрирован: ID ${contractProductId}, businessId ${contractBusinessId}`);
        console.log(`   → TX: ${receipt.transactionHash}`);
      }
      
    } catch (error) {
      console.error(`❌ Ошибка регистрации продукта ${productId}:`, error.message);
      registrationResults[productId] = {
        contractProductId: null,
        success: false,
        error: error.message
      };
    }
  }
  
  const successCount = Object.values(registrationResults).filter(r => r.success).length;
  console.log(`\n✅ ШАГ 1 завершен: ${successCount}/${productIds.length} продуктов зарегистрированы`);
  
  // CRITICAL: Validate that at least some products were registered
  // Throw error on 100% failure to prevent silent failures
  if (successCount === 0 && productIds.length > 0) {
    const firstError = Object.values(registrationResults).find(r => r.error)?.error || 'Unknown error';
    throw new Error(
      `All ${productIds.length} product registrations failed!\n` +
      `First error: ${firstError}\n` +
      `Check: ProductRegistry contract initialized, seller has permissions, component_ids valid`
    );
  }
  
  return registrationResults;
}

/**
 * Активация продуктов в ProductRegistry контракте
 * @param {Object} context - Upload context
 * @param {Object} registrationResults - Результаты регистрации
 * @returns {Promise<Object>} Результаты активации
 */
async function activateProductsInContract(context, registrationResults) {
  console.log("\n🔍 ШАГ 2: Активация продуктов в ProductRegistry");
  console.log("=".repeat(60));
  
  const activationResults = {};
  const successfulRegistrations = Object.entries(registrationResults)
    .filter(([_, result]) => result.success && result.contractProductId)
    .map(([productId, result]) => ({ productId, contractProductId: result.contractProductId }));
  
  console.log(`📁 Найдено ${successfulRegistrations.length} продуктов для активации`);
  
  for (const { productId, contractProductId } of successfulRegistrations) {
    try {
      console.log(`\n📦 Активация продукта: ${productId} (ID: ${contractProductId})`);
      
      if (context.dryRun) {
        // Dry-run режим
        activationResults[productId] = {
          contractProductId: contractProductId,
          success: true,
          txHash: `DRYRUN_${Date.now()}_${Math.random().toString(36).substring(7)}`
        };
        console.log(`   🔷 [DRY-RUN] Mock активация успешна`);
      } else {
        // Реальная активация в контракте
        if (!context.productRegistry) {
          throw new Error("ProductRegistry контракт не инициализирован");
        }
        
        const tx = await context.productRegistry.activateProduct(contractProductId);
        const receipt = await tx.wait();
        
        // ✅ Delay to prevent nonce race condition in batch operations
        await sleep(500);
        
        activationResults[productId] = {
          contractProductId: contractProductId,
          success: true,
          txHash: receipt.transactionHash
        };
        
        console.log(`   ✅ Продукт активирован`);
        console.log(`   → TX: ${receipt.transactionHash}`);
      }
      
    } catch (error) {
      console.error(`❌ Ошибка активации продукта ${productId}:`, error.message);
      activationResults[productId] = {
        contractProductId: contractProductId,
        success: false,
        error: error.message
      };
    }
  }
  
  const successCount = Object.values(activationResults).filter(r => r.success).length;
  console.log(`\n✅ ШАГ 2 завершен: ${successCount}/${successfulRegistrations.length} продуктов активированы`);
  
  return activationResults;
}

/**
 * Валидация результатов регистрации и активации
 * @param {Object} context - Upload context
 * @param {Object} registrationResults - Результаты регистрации
 * @param {Object} activationResults - Результаты активации
 * @returns {Promise<Object>} Результаты валидации
 */
async function validateRegistrationResults(context, registrationResults, activationResults) {
  console.log("\n🔍 ШАГ 3: Валидация результатов");
  console.log("=".repeat(60));
  
  const validationResults = {
    totalProducts: Object.keys(registrationResults).length,
    registeredProducts: Object.values(registrationResults).filter(r => r.success).length,
    activatedProducts: Object.values(activationResults).filter(r => r.success).length,
    failedRegistrations: [],
    failedActivations: [],
    contractValidation: {}
  };
  
  // Анализ неудачных регистраций
  for (const [productId, result] of Object.entries(registrationResults)) {
    if (!result.success) {
      validationResults.failedRegistrations.push({
        productId,
        error: result.error
      });
    }
  }
  
  // Анализ неудачных активаций
  for (const [productId, result] of Object.entries(activationResults)) {
    if (!result.success) {
      validationResults.failedActivations.push({
        productId,
        contractProductId: result.contractProductId,
        error: result.error
      });
    }
  }
  
  // Валидация в контракте (только если не dry-run)
  if (!context.dryRun && context.productRegistry) {
    console.log("🔍 Проверка статуса продуктов в контракте...");
    
    for (const [productId, result] of Object.entries(activationResults)) {
      if (result.success && result.contractProductId) {
        try {
          const productInfo = await context.productRegistry.getProduct(result.contractProductId);
          validationResults.contractValidation[productId] = {
            contractProductId: result.contractProductId,
            active: productInfo.active,
            seller: productInfo.seller,
            componentCount: productInfo.componentIds.length,
            metadataCID: productInfo.metadataCID
          };
          console.log(`   ✅ ${productId}: активен=${productInfo.active}, компонентов=${productInfo.componentIds.length}`);
        } catch (error) {
          console.warn(`   ⚠️ ${productId}: ошибка проверки в контракте - ${error.message}`);
          validationResults.contractValidation[productId] = {
            contractProductId: result.contractProductId,
            error: error.message
          };
        }
      }
    }
  }
  
  console.log(`\n📊 Результаты валидации:`);
  console.log(`   → Всего продуктов: ${validationResults.totalProducts}`);
  console.log(`   → Зарегистрировано: ${validationResults.registeredProducts}`);
  console.log(`   → Активировано: ${validationResults.activatedProducts}`);
  console.log(`   → Ошибки регистрации: ${validationResults.failedRegistrations.length}`);
  console.log(`   → Ошибки активации: ${validationResults.failedActivations.length}`);
  
  console.log(`\n✅ ШАГ 3 завершен: Валидация завершена`);
  
  return validationResults;
}

/**
 * Основная функция Action 43: Объединенная регистрация в контракте
 * @param {Object} context - Upload context
 * @param {string} mappingFile - Путь к файлу с mapping данными
 * @param {string} productsDir - Директория с продуктами
 * @returns {Promise<Object>} Результаты регистрации
 */
async function action43_UnifiedContractRegistration(context, mappingFile, productsDir) {
  console.log("\n" + "=".repeat(80));
  console.log("🚀 ACTION 43: ОБЪЕДИНЕННАЯ РЕГИСТРАЦИЯ В КОНТРАКТЕ");
  console.log("=".repeat(80));
  console.log(`📄 Mapping file: ${mappingFile}`);
  console.log(`📁 Products dir: ${productsDir}`);
  console.log(`🔷 Dry-run: ${context.dryRun ? 'ENABLED' : 'DISABLED'}`);
  
  const startTime = Date.now();
  
  try {
    // Загружаем mapping данные
    if (!fs.existsSync(mappingFile)) {
      throw new Error(`Mapping файл не найден: ${mappingFile}`);
    }
    
    const mappingData = JSON.parse(fs.readFileSync(mappingFile, 'utf8'));
    console.log(`📊 Загружено ${Object.keys(mappingData).length} продуктов из mapping файла`);
    
    // Загружаем данные продуктов
    const productData = {};
    for (const productId of Object.keys(mappingData)) {
      const productFile = path.join(productsDir, productId, `${productId}.json`);
      if (fs.existsSync(productFile)) {
        productData[productId] = JSON.parse(fs.readFileSync(productFile, 'utf8'));
      }
    }
    console.log(`📊 Загружено ${Object.keys(productData).length} продуктов из файловой системы`);
    
    // ✅ NEW: Шаг 0 - Очистка существующего каталога
    try {
      const clearResults = await clearExistingCatalog(context);
      if (clearResults.cleared > 0) {
        console.log(`\n✅ ШАГ 0 завершен: очищено ${clearResults.cleared} продуктов`);
      }
    } catch (error) {
      console.warn(`\n⚠️ ШАГ 0 warning: ${error.message}`);
      console.warn(`⚠️ Продолжаем без очистки (продукты будут добавлены к существующим)`);
    }
    
    // Шаг 1: Регистрация продуктов
    const registrationResults = await registerProductsInContract(context, mappingData, productData);
    
    // Шаг 2: Активация продуктов
    const activationResults = await activateProductsInContract(context, registrationResults);
    
    // Шаг 3: Валидация результатов
    const validationResults = await validateRegistrationResults(context, registrationResults, activationResults);
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log("\n" + "=".repeat(80));
    console.log("✅ ACTION 43 ЗАВЕРШЕН УСПЕШНО");
    console.log("=".repeat(80));
    console.log(`⏱️ Время выполнения: ${duration}s`);
    console.log(`📊 Статистика:`);
    console.log(`   → Продуктов зарегистрировано: ${validationResults.registeredProducts}/${validationResults.totalProducts}`);
    console.log(`   → Продуктов активировано: ${validationResults.activatedProducts}/${validationResults.totalProducts}`);
    console.log(`   → Ошибок регистрации: ${validationResults.failedRegistrations.length}`);
    console.log(`   → Ошибок активации: ${validationResults.failedActivations.length}`);
    
    return {
      success: true,
      duration: parseFloat(duration),
      statistics: validationResults,
      registrationResults,
      activationResults
    };
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log("\n" + "=".repeat(80));
    console.log("❌ ACTION 43 ЗАВЕРШЕН С ОШИБКОЙ");
    console.log("=".repeat(80));
    console.log(`⏱️ Время выполнения: ${duration}s`);
    console.error(`❌ Ошибка: ${error.message}`);
    
    return {
      success: false,
      duration: parseFloat(duration),
      error: error.message
    };
  }
}

/**
 * Автоматический пайп всех действий (Action 41-43)
 * @param {Object} context - Upload context
 * @param {string} csvPath - Путь к CSV файлу
 * @param {string} outputDir - Директория для вывода
 * @param {string} sellerId - ID продавца
 * @param {string} sourceLang - Исходный язык названий
 * @returns {Promise<Object>} Результаты всего пайпа
 */
async function action444_AutomaticPipeline(context, csvPath, outputDir, sellerId, sourceLang = 'en') {
  console.log("\n" + "=".repeat(80));
  console.log("🚀 ACTION 444: АВТОМАТИЧЕСКИЙ ПАЙП (41-43)");
  console.log("=".repeat(80));
  console.log(`📄 CSV file: ${csvPath}`);
  console.log(`📁 Output dir: ${outputDir}`);
  console.log(`👤 Seller ID: ${sellerId}`);
  console.log(`🌐 Source language: ${sourceLang}`);
  console.log(`🔷 Dry-run: ${context.dryRun ? 'ENABLED' : 'DISABLED'}`);
  
  const startTime = Date.now();
  const pipelineResults = {
    action41: null,
    action42: null,
    action43: null,
    success: false,
    errors: []
  };
  
  try {
    // ====================================================================
    // ACTION 41: ТРАНСФОРМАЦИЯ CSV → JSON
    // ====================================================================
    console.log("\n" + "=".repeat(60));
    console.log("🔄 ACTION 41: ТРАНСФОРМАЦИЯ CSV → JSON");
    console.log("=".repeat(60));
    
    try {
      // Импортируем функцию трансформации
      const transformModule = require('../transform_products_csv.js');
      
      // Вызываем трансформацию с параметрами
      const transformResult = await transformModule.transformProductsFromCSV({
        csvPath: csvPath,
        outputDir: path.join(outputDir, 'products'),
        sellerId: sellerId,
        sourceLang: sourceLang,
        dryRun: context.dryRun,
        contractManager: context.contractManager // ← For component_id resolution via Ethers.js
      });
      
      pipelineResults.action41 = {
        success: true,
        result: transformResult,
        productsDir: outputDir
      };
      
      console.log("✅ ACTION 41 завершен успешно");
      
    } catch (error) {
      console.error("❌ ACTION 41 завершен с ошибкой:", error.message);
      pipelineResults.action41 = {
        success: false,
        error: error.message
      };
      pipelineResults.errors.push(`Action 41: ${error.message}`);
      throw error; // Прерываем пайп при ошибке трансформации
    }
    
    // ====================================================================
    // ACTION 42: ЗАГРУЗКА В ARWEAVE
    // ====================================================================
    console.log("\n" + "=".repeat(60));
    console.log("🔄 ACTION 42: ЗАГРУЗКА В ARWEAVE");
    console.log("=".repeat(60));
    
    try {
      // STEP 0: Initialize Arweave and adapt context structure
      if (context.arweaveManager) {
        // Ensure ArweaveManager is initialized
        if (!context.arweaveManager.isReady()) {
          await context.arweaveManager.initialize();
        }
        
        // Adapt context: upload_steps.js expects context.arweave.client and context.arweave.key
        context.arweave = {
          client: context.arweaveManager.getClient(),
          key: context.arweaveManager.getKey()
        };
      }
      
      const productsDir = path.join(outputDir, 'products');
      const mappingOutputDir = outputDir;
      
      const arweaveResult = await action42_UnifiedArweaveUpload(
        context, 
        productsDir, 
        mappingOutputDir
      );
      
      pipelineResults.action42 = {
        success: arweaveResult.success,
        result: arweaveResult,
        mappingFile: path.join(mappingOutputDir, 'product_combined_mapping.json')
      };
      
      if (arweaveResult.success) {
        console.log("✅ ACTION 42 завершен успешно");
      } else {
        throw new Error(arweaveResult.error);
      }
      
    } catch (error) {
      console.error("❌ ACTION 42 завершен с ошибкой:", error.message);
      pipelineResults.action42 = {
        success: false,
        error: error.message
      };
      pipelineResults.errors.push(`Action 42: ${error.message}`);
      throw error; // Прерываем пайп при ошибке загрузки в Arweave
    }
    
    // ====================================================================
    // ACTION 43: РЕГИСТРАЦИЯ В КОНТРАКТЕ
    // ====================================================================
    console.log("\n" + "=".repeat(60));
    console.log("🔄 ACTION 43: РЕГИСТРАЦИЯ В КОНТРАКТЕ");
    console.log("=".repeat(60));
    
    try {
      // CRITICAL: Initialize contracts and seller context before registration
      if (context.contractManager) {
        console.log("📋 Initializing ProductRegistry contract...");
        context.productRegistry = await context.contractManager.loadUUPSContract('ProductRegistry');
        console.log(`   ✅ ProductRegistry loaded: ${await context.productRegistry.getAddress()}`);
        
        // Get seller signer for product registration transactions
        const sellerPrivateKey = process.env.SELLER_PRIVATE_KEY;
        if (sellerPrivateKey) {
          const { ethers } = require('hardhat');
          const sellerSigner = new ethers.Wallet(sellerPrivateKey, context.contractManager.provider);
          const sellerAddress = await sellerSigner.getAddress();
          
          // ✅ FIX: Connect signer to contract for transaction sending
          context.productRegistry = context.productRegistry.connect(sellerSigner);
          
          context.seller = {
            address: sellerAddress,
            signer: sellerSigner
          };
          console.log(`   ✅ Seller signer initialized: ${sellerAddress}`);
          console.log(`   ✅ ProductRegistry connected to seller signer`);
        } else {
          console.warn(`   ⚠️ SELLER_PRIVATE_KEY not found - registration will use deployer`);
        }
      } else {
        console.warn(`   ⚠️ ContractManager not provided - skipping contract initialization`);
      }
      
      const mappingFile = pipelineResults.action42.mappingFile;
      const productsDir = path.join(outputDir, 'products');
      
      const contractResult = await action43_UnifiedContractRegistration(
        context,
        mappingFile,
        productsDir
      );
      
      pipelineResults.action43 = {
        success: contractResult.success,
        result: contractResult
      };
      
      if (contractResult.success) {
        console.log("✅ ACTION 43 завершен успешно");
      } else {
        throw new Error(contractResult.error);
      }
      
    } catch (error) {
      console.error("❌ ACTION 43 завершен с ошибкой:", error.message);
      pipelineResults.action43 = {
        success: false,
        error: error.message
      };
      pipelineResults.errors.push(`Action 43: ${error.message}`);
      throw error; // Прерываем пайп при ошибке регистрации
    }
    
    // ====================================================================
    // ФИНАЛЬНЫЙ РЕЗУЛЬТАТ
    // ====================================================================
    pipelineResults.success = true;
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log("\n" + "=".repeat(80));
    console.log("✅ ACTION 444 ЗАВЕРШЕН УСПЕШНО");
    console.log("=".repeat(80));
    console.log(`⏱️ Время выполнения: ${duration}s`);
    console.log(`📊 Статистика:`);
    console.log(`   → Action 41 (Трансформация): ${pipelineResults.action41.success ? '✅' : '❌'}`);
    console.log(`   → Action 42 (Arweave): ${pipelineResults.action42.success ? '✅' : '❌'}`);
    console.log(`   → Action 43 (Контракт): ${pipelineResults.action43.success ? '✅' : '❌'}`);
    
    if (pipelineResults.action41.success && pipelineResults.action41.result) {
      console.log(`   → Продуктов создано: ${pipelineResults.action41.result.statistics?.total_products || 'N/A'}`);
    }
    if (pipelineResults.action42.success && pipelineResults.action42.result) {
      console.log(`   → Файлов загружено: ${pipelineResults.action42.result.statistics?.titleFiles + pipelineResults.action42.result.statistics?.productFiles || 'N/A'}`);
    }
    if (pipelineResults.action43.success && pipelineResults.action43.result) {
      console.log(`   → Продуктов активировано: ${pipelineResults.action43.result.statistics?.activatedProducts || 'N/A'}`);
    }
    
    return {
      success: true,
      duration: parseFloat(duration),
      pipelineResults,
      summary: {
        totalProducts: pipelineResults.action41.result?.statistics?.total_products || 0,
        arweaveFiles: (pipelineResults.action42.result?.statistics?.titleFiles || 0) + (pipelineResults.action42.result?.statistics?.productFiles || 0),
        activatedProducts: pipelineResults.action43.result?.statistics?.activatedProducts || 0
      }
    };
    
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    console.log("\n" + "=".repeat(80));
    console.log("❌ ACTION 444 ЗАВЕРШЕН С ОШИБКОЙ");
    console.log("=".repeat(80));
    console.log(`⏱️ Время выполнения: ${duration}s`);
    console.error(`❌ Ошибка: ${error.message}`);
    
    if (pipelineResults.errors.length > 0) {
      console.log("📋 История ошибок:");
      pipelineResults.errors.forEach((err, index) => {
        console.log(`   ${index + 1}. ${err}`);
      });
    }
    
    return {
      success: false,
      duration: parseFloat(duration),
      error: error.message,
      pipelineResults,
      errors: pipelineResults.errors
    };
  }
}

/**
 * Resume logic для продолжения пайпа с определенного этапа
 * @param {Object} context - Upload context
 * @param {string} resumeFrom - С какого действия продолжить ('action41', 'action42', 'action43')
 * @param {Object} previousResults - Результаты предыдущих действий
 * @returns {Promise<Object>} Результаты продолжения пайпа
 */
async function action444_ResumePipeline(context, resumeFrom, previousResults = {}) {
  console.log("\n" + "=".repeat(80));
  console.log(`🔄 ACTION 444: RESUME PIPELINE (с ${resumeFrom})`);
  console.log("=".repeat(80));
  
  const pipelineResults = { ...previousResults };
  
  try {
    switch (resumeFrom) {
      case 'action41':
        console.log("⚠️ Resume с Action 41 не поддерживается - требуется полный перезапуск");
        throw new Error("Resume с Action 41 не поддерживается");
        
      case 'action42':
        console.log("🔄 Продолжаем с Action 42 (загрузка в Arweave)...");
        // Здесь можно добавить логику для продолжения с Action 42
        // если у нас есть результаты Action 41
        break;
        
      case 'action43':
        console.log("🔄 Продолжаем с Action 43 (регистрация в контракте)...");
        // Здесь можно добавить логику для продолжения с Action 43
        // если у нас есть результаты Action 42
        break;
        
      default:
        throw new Error(`Неизвестный этап для resume: ${resumeFrom}`);
    }
    
    return {
      success: true,
      pipelineResults,
      resumedFrom: resumeFrom
    };
    
  } catch (error) {
    console.error(`❌ Ошибка при resume с ${resumeFrom}:`, error.message);
    return {
      success: false,
      error: error.message,
      pipelineResults
    };
  }
}

// ====================================================================
// 🚀 EXPORTS
// ====================================================================

module.exports = {
  uploadTitleFiles,
  uploadProductImages,
  uploadProductFiles,
  createMappingFiles,
  action42_UnifiedArweaveUpload,
  registerProductsInContract,
  activateProductsInContract,
  validateRegistrationResults,
  action43_UnifiedContractRegistration,
  action444_AutomaticPipeline,
  action444_ResumePipeline
};
