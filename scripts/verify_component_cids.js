#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const https = require('https');

// Цвета для консоли
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

// Функция для проверки CID в Arweave
async function checkArweaveCID(cid, expectedSize = null) {
    return new Promise((resolve) => {
        const url = `https://arweave.net/${cid}`;
        
        const req = https.get(url, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                const actualSize = Buffer.byteLength(data, 'utf8');
                const status = {
                    cid: cid,
                    url: url,
                    status: res.statusCode,
                    size: actualSize,
                    expectedSize: expectedSize,
                    valid: res.statusCode === 200,
                    content: data.length > 0 ? data.substring(0, 200) + '...' : 'No content'
                };
                resolve(status);
            });
        });
        
        req.on('error', (error) => {
            resolve({
                cid: cid,
                url: url,
                status: 'ERROR',
                size: 0,
                expectedSize: expectedSize,
                valid: false,
                error: error.message
            });
        });
        
        req.setTimeout(10000, () => {
            req.destroy();
            resolve({
                cid: cid,
                url: url,
                status: 'TIMEOUT',
                size: 0,
                expectedSize: expectedSize,
                valid: false,
                error: 'Request timeout'
            });
        });
    });
}

// Функция для проверки компонента
async function verifyComponent(componentId) {
    log(`\n${'='.repeat(80)}`, 'cyan');
    log(`🔍 ПРОВЕРКА КОМПОНЕНТА: ${componentId}`, 'bright');
    log(`${'='.repeat(80)}`, 'cyan');
    
    const statePath = path.join('data', 'components', componentId, `_upload_state_localhost.json`);
    
    if (!fs.existsSync(statePath)) {
        log(`❌ State файл не найден: ${statePath}`, 'red');
        return;
    }
    
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    
    log(`📊 Статус компонента:`, 'blue');
    log(`   → Шагов завершено: ${state.steps_completed.length}`, 'blue');
    log(`   → Последние шаги: ${state.steps_completed.slice(-3).join(', ')}`, 'blue');
    log(`   → Обновлен: ${state.updated_at}`, 'blue');
    
    // Проверка Simple Fields
    if (state.simple_fields && Object.keys(state.simple_fields).length > 0) {
        log(`\n📝 SIMPLE FIELDS (${Object.keys(state.simple_fields).length}):`, 'yellow');
        
        for (const [fieldName, fieldData] of Object.entries(state.simple_fields)) {
            log(`   🔹 ${fieldName}:`, 'blue');
            log(`      CID: ${fieldData.cid}`, 'blue');
            log(`      Размер: ${fieldData.size} bytes`, 'blue');
            
            const result = await checkArweaveCID(fieldData.cid, fieldData.size);
            if (result.valid) {
                log(`      ✅ Статус: ${result.status} | Размер: ${result.size} bytes`, 'green');
                if (result.expectedSize && result.size !== result.expectedSize) {
                    log(`      ⚠️  Размер не совпадает! Ожидалось: ${result.expectedSize}`, 'yellow');
                }
            } else {
                log(`      ❌ Ошибка: ${result.error || result.status}`, 'red');
            }
        }
    }
    
    // Проверка Complex Fields
    if (state.complex_fields && Object.keys(state.complex_fields).length > 0) {
        log(`\n🌍 COMPLEX FIELDS (${Object.keys(state.complex_fields).length} языков):`, 'yellow');
        
        for (const [lang, langData] of Object.entries(state.complex_fields)) {
            log(`   🔹 ${lang}:`, 'blue');
            log(`      CID: ${langData.cid}`, 'blue');
            log(`      Размер: ${langData.size} bytes`, 'blue');
            
            const result = await checkArweaveCID(langData.cid, langData.size);
            if (result.valid) {
                log(`      ✅ Статус: ${result.status} | Размер: ${result.size} bytes`, 'green');
                if (result.expectedSize && result.size !== result.expectedSize) {
                    log(`      ⚠️  Размер не совпадает! Ожидалось: ${result.expectedSize}`, 'yellow');
                }
            } else {
                log(`      ❌ Ошибка: ${result.error || result.status}`, 'red');
            }
        }
    }
    
    // Проверка Shareable Data
    if (state.shareable_data && Object.keys(state.shareable_data).length > 0) {
        log(`\n🔗 SHAREABLE DATA:`, 'yellow');
        
        if (state.shareable_data.featuresCID) {
            log(`   🔹 features:`, 'blue');
            log(`      CID: ${state.shareable_data.featuresCID}`, 'blue');
            
            const result = await checkArweaveCID(state.shareable_data.featuresCID);
            if (result.valid) {
                log(`      ✅ Статус: ${result.status} | Размер: ${result.size} bytes`, 'green');
            } else {
                log(`      ❌ Ошибка: ${result.error || result.status}`, 'red');
            }
        }
        
        if (state.shareable_data.formsCID) {
            log(`   🔹 forms:`, 'blue');
            log(`      CID: ${state.shareable_data.formsCID}`, 'blue');
            
            const result = await checkArweaveCID(state.shareable_data.formsCID);
            if (result.valid) {
                log(`      ✅ Статус: ${result.status} | Размер: ${result.size} bytes`, 'green');
            } else {
                log(`      ❌ Ошибка: ${result.error || result.status}`, 'red');
            }
        }
    }
    
    // Проверка Root Metadata
    if (state.root_metadata && state.root_metadata.cid) {
        log(`\n📄 ROOT METADATA:`, 'yellow');
        log(`   🔹 Root CID: ${state.root_metadata.cid}`, 'blue');
        log(`   🔹 Файл: ${state.root_metadata.path}`, 'blue');
        
        const result = await checkArweaveCID(state.root_metadata.cid);
        if (result.valid) {
            log(`   ✅ Статус: ${result.status} | Размер: ${result.size} bytes`, 'green');
            
            // Проверяем содержимое root metadata
            try {
                const rootData = JSON.parse(result.content.replace('...', ''));
                log(`   📊 Содержит:`, 'blue');
                log(`      → biounit_id: ${rootData.biounit_id}`, 'blue');
                log(`      → scientific_title: ${rootData.scientific_title}`, 'blue');
                log(`      → simple_fields: ${Object.keys(rootData.localizations?.simple_fields || {}).length}`, 'blue');
                log(`      → complex_fields: ${Object.keys(rootData.localizations?.complex_fields || {}).length} языков`, 'blue');
                log(`      → features: ${rootData.features?.common?.length || 0} общих`, 'blue');
                log(`      → forms: ${rootData.forms?.length || 0} форм`, 'blue');
            } catch (e) {
                log(`   ⚠️  Не удалось распарсить JSON: ${e.message}`, 'yellow');
            }
        } else {
            log(`   ❌ Ошибка: ${result.error || result.status}`, 'red');
        }
    }
    
    // Проверка Contract Registration
    if (state.contract_registration && Object.keys(state.contract_registration).length > 0) {
        log(`\n📋 CONTRACT REGISTRATION:`, 'yellow');
        log(`   🔹 Component ID: ${state.contract_registration.componentId}`, 'blue');
        log(`   🔹 TX Hash: ${state.contract_registration.txHash}`, 'blue');
        log(`   🔹 Block: ${state.contract_registration.blockNumber}`, 'blue');
        log(`   ✅ Зарегистрирован в контракте`, 'green');
    }
    
    log(`\n${'='.repeat(80)}`, 'cyan');
}

// Основная функция
async function main() {
    log('🔍 ПРОВЕРКА CID КОМПОНЕНТОВ В ARWEAVE', 'bright');
    log('='.repeat(80), 'cyan');
    
    const componentsDir = path.join('data', 'components');
    
    if (!fs.existsSync(componentsDir)) {
        log('❌ Директория components не найдена', 'red');
        return;
    }
    
    const components = fs.readdirSync(componentsDir).filter(item => {
        const itemPath = path.join(componentsDir, item);
        return fs.statSync(itemPath).isDirectory();
    });
    
    log(`📁 Найдено компонентов: ${components.length}`, 'blue');
    
    for (const componentId of components) {
        await verifyComponent(componentId);
        
        // Небольшая пауза между запросами
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    log('\n🎉 ПРОВЕРКА ЗАВЕРШЕНА!', 'green');
}

// Запуск
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { verifyComponent, checkArweaveCID };
