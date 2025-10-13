/**
 * 🔍 Arweave Readiness Check Script
 * 
 * Проверяет подключение к Arweave и готовность к загрузке
 * 
 * Usage:
 *   node scripts/Arweave-Readiness.js
 *   node scripts/Arweave-Readiness.js --test-upload
 *   ARWEAVE_KEY_PATH=.arweave-key.json node scripts/Arweave-Readiness.js
 * 
 * Exit codes:
 *   0 - Ready (все проверки пройдены)
 *   1 - Not ready (есть проблемы)
 * 
 * @version 1.0.0
 * @date 2025-01-12
 */

const Arweave = require('arweave');
const fs = require('fs');
const path = require('path');

// ====================================================================
// CONFIGURATION
// ====================================================================

const KEY_PATH = process.env.ARWEAVE_KEY_PATH || '.arweave-key.json';
const TEST_UPLOAD = process.env.TEST_UPLOAD === 'true' || process.argv.includes('--test-upload');

// Тестовое сообщение для Arweave (текстовое, не JSON!)
const TEST_MESSAGE = "HELLOATLASSWANFROMZEYA888CONNECTIONWORKS";

// ====================================================================
// STEP 1: Load Arweave Key
// ====================================================================

async function loadArweaveKey() {
  console.log('\n📋 STEP 1: Loading Arweave Key');
  console.log('─'.repeat(70));
  
  // Check file exists
  if (!fs.existsSync(KEY_PATH)) {
    console.error(`❌ Key file not found: ${KEY_PATH}`);
    console.error(`   Hint: Set ARWEAVE_KEY_PATH env variable or place key at .arweave-key.json`);
    return null;
  }
  console.log(`✅ Key file found: ${KEY_PATH}`);
  
  // Check file size
  const stats = fs.statSync(KEY_PATH);
  console.log(`   File size: ${stats.size} bytes`);
  
  // Load and parse
  try {
    const keyData = fs.readFileSync(KEY_PATH, 'utf8');
    const key = JSON.parse(keyData);
    
    // Validate JWK format
    const requiredFields = ['kty', 'n', 'e', 'd', 'p', 'q', 'dp', 'dq', 'qi'];
    const missingFields = requiredFields.filter(field => !key[field]);
    
    if (missingFields.length > 0) {
      console.error(`❌ Invalid JWK format - missing fields: ${missingFields.join(', ')}`);
      return null;
    }
    
    console.log(`✅ Valid JWK RSA key loaded`);
    console.log(`   Key type: ${key.kty}`);
    console.log(`   All required fields present: ${requiredFields.length}/9`);
    
    return key;
    
  } catch (error) {
    console.error(`❌ Error loading key: ${error.message}`);
    if (error instanceof SyntaxError) {
      console.error(`   Hint: Check if ${KEY_PATH} contains valid JSON`);
    }
    return null;
  }
}

// ====================================================================
// STEP 2: Initialize Arweave Client
// ====================================================================

function initArweave() {
  console.log('\n🌐 STEP 2: Initialize Arweave Client');
  console.log('─'.repeat(70));
  
  try {
    const arweave = Arweave.init({
      host: 'arweave.net',
      port: 443,
      protocol: 'https',
      timeout: 60000,
      logging: false
    });
    
    console.log('✅ Arweave client initialized');
    console.log(`   Host: arweave.net:443`);
    console.log(`   Protocol: HTTPS`);
    console.log(`   Timeout: 60000ms`);
    
    return arweave;
    
  } catch (error) {
    console.error(`❌ Failed to initialize Arweave: ${error.message}`);
    return null;
  }
}

// ====================================================================
// STEP 3: Check Network Connection
// ====================================================================

async function checkConnection(arweave) {
  console.log('\n🔌 STEP 3: Check Network Connection');
  console.log('─'.repeat(70));
  
  try {
    const startTime = Date.now();
    const networkInfo = await arweave.network.getInfo();
    const responseTime = Date.now() - startTime;
    
    console.log('✅ Connected to Arweave network');
    console.log(`   Network: ${networkInfo.network}`);
    console.log(`   Height: ${networkInfo.height.toLocaleString()}`);
    console.log(`   Current block: ${networkInfo.current}`);
    console.log(`   Blocks: ${networkInfo.blocks}`);
    console.log(`   Peers: ${networkInfo.peers}`);
    console.log(`   Response time: ${responseTime}ms`);
    
    if (responseTime > 5000) {
      console.warn(`   ⚠️  Slow connection: ${responseTime}ms (>5s)`);
    }
    
    return { success: true, responseTime, networkInfo };
    
  } catch (error) {
    console.error(`❌ Connection failed: ${error.message}`);
    console.error(`   Hint: Check internet connection or Arweave network status`);
    console.error(`   URL: https://arweave.net/`);
    return { success: false, error: error.message };
  }
}

// ====================================================================
// STEP 4: Check Wallet & Balance
// ====================================================================

async function checkWalletBalance(arweave, key) {
  console.log('\n💰 STEP 4: Check Wallet & Balance');
  console.log('─'.repeat(70));
  
  try {
    // Get wallet address
    const address = await arweave.wallets.jwkToAddress(key);
    console.log(`✅ Wallet address: ${address}`);
    
    // Get balance
    const balanceWinston = await arweave.wallets.getBalance(address);
    const balanceAR = arweave.ar.winstonToAr(balanceWinston);
    
    console.log(`💵 Balance: ${balanceAR} AR`);
    console.log(`   Winston: ${balanceWinston}`);
    
    // Оценка количества возможных загрузок
    const avgFileSize = 100 * 1024; // 100KB
    const estimatedUploads = estimateUploads(balanceWinston, avgFileSize);
    console.log(`📊 Estimated uploads: ~${estimatedUploads} files (100KB each)`);
    
    // Предупреждения по балансу
    const balanceNum = parseFloat(balanceAR);
    
    if (balanceNum === 0) {
      console.error(`❌ ZERO BALANCE: Cannot upload to Arweave`);
      console.error(`   Action required: Add AR to wallet ${address}`);
      return { address, balance: balanceAR, status: 'zero_balance' };
    }
    
    if (balanceNum < 0.01) {
      console.warn(`⚠️  LOW BALANCE WARNING: ${balanceAR} AR < 0.01 AR`);
      console.warn(`   Estimated uploads: ${estimatedUploads} (may not be enough)`);
      console.warn(`   Consider adding funds for production uploads`);
      return { address, balance: balanceAR, status: 'low_balance' };
    }
    
    if (balanceNum < 0.1) {
      console.warn(`⚠️  MODERATE BALANCE: ${balanceAR} AR`);
      console.warn(`   OK for testing, consider adding more for production`);
      return { address, balance: balanceAR, status: 'moderate' };
    }
    
    console.log(`✅ Good balance for uploads`);
    return { address, balance: balanceAR, status: 'ok' };
    
  } catch (error) {
    console.error(`❌ Wallet check failed: ${error.message}`);
    return { status: 'error', error: error.message };
  }
}

/**
 * Оценка количества возможных uploads
 * @param {string} balanceWinston - Баланс в winston
 * @param {number} fileSizeBytes - Размер файла в байтах
 * @returns {number} Количество возможных uploads
 */
function estimateUploads(balanceWinston, fileSizeBytes) {
  // Примерная стоимость: ~0.0001 AR за 100KB
  const costPer100KB = 0.0001; // AR
  const balanceAR = parseFloat(balanceWinston) / 1e12; // winston to AR
  const numberOfUploads = Math.floor(balanceAR / costPer100KB);
  return numberOfUploads > 0 ? numberOfUploads : 0;
}

// ====================================================================
// STEP 5: Test Upload (опционально)
// ====================================================================

async function testUpload(arweave, key) {
  console.log('\n🧪 STEP 5: Test Upload');
  console.log('─'.repeat(70));
  
  if (!TEST_UPLOAD) {
    console.log('ℹ️  Test upload skipped (use --test-upload to enable)');
    console.log('   Hint: node scripts/Arweave-Readiness.js --test-upload');
    return { skipped: true };
  }
  
  try {
    // ВАЖНО: Используем ТЕКСТ, не JSON!
    const testData = TEST_MESSAGE;
    
    console.log(`📦 Test data: "${testData}"`);
    console.log(`   Type: TEXT (not JSON!)`);
    console.log(`   Size: ${testData.length} bytes`);
    
    // Создаем transaction
    const startTime = Date.now();
    const transaction = await arweave.createTransaction({
      data: testData
    }, key);
    
    // Tags
    transaction.addTag('Content-Type', 'text/plain');
    transaction.addTag('App-Name', 'Amanita-Readiness-Check');
    transaction.addTag('Type', 'test');
    transaction.addTag('Message', 'Connection test from Zeya888');
    transaction.addTag('Timestamp', new Date().toISOString());
    
    console.log('✅ Transaction created');
    console.log(`   TX ID: ${transaction.id}`);
    console.log(`   Size: ${transaction.data_size} bytes`);
    console.log(`   Reward: ${arweave.ar.winstonToAr(transaction.reward)} AR`);
    
    // Sign
    await arweave.transactions.sign(transaction, key);
    console.log('✅ Transaction signed');
    
    // Post
    console.log('📤 Posting transaction to Arweave...');
    const response = await arweave.transactions.post(transaction);
    const uploadTime = ((Date.now() - startTime) / 1000).toFixed(1);
    
    if (response.status === 200 || response.status === 208) {
      console.log(`✅ Transaction posted successfully!`);
      console.log(`   Status: ${response.status} ${response.statusText || ''}`);
      console.log(`   TX ID: ${transaction.id}`);
      console.log(`   URL: https://arweave.net/${transaction.id}`);
      console.log(`   Upload time: ${uploadTime}s`);
      console.log(`   Monitor: https://viewblock.io/arweave/tx/${transaction.id}`);
      
      return {
        success: true,
        txId: transaction.id,
        url: `https://arweave.net/${transaction.id}`,
        uploadTime: parseFloat(uploadTime),
        status: response.status
      };
    } else {
      console.error(`❌ Upload failed: status ${response.status}`);
      console.error(`   Response: ${response.statusText || 'Unknown error'}`);
      return { success: false, status: response.status };
    }
    
  } catch (error) {
    console.error(`❌ Test upload failed: ${error.message}`);
    console.error(`   Error type: ${error.type || 'Unknown'}`);
    return { success: false, error: error.message };
  }
}

// ====================================================================
// STEP 6: Generate Final Report
// ====================================================================

function generateReport(results) {
  const { key, connection, wallet, upload } = results;
  
  console.log('\n' + '='.repeat(70));
  console.log('📊 FINAL REPORT');
  console.log('='.repeat(70));
  
  let allPassed = true;
  
  // Key check
  if (key) {
    console.log('✅ Key: Valid JWK RSA key loaded');
  } else {
    console.log('❌ Key: Failed to load');
    allPassed = false;
  }
  
  // Connection check
  if (connection?.success) {
    console.log(`✅ Connection: Connected to ${connection.networkInfo.network}`);
    console.log(`   Height: ${connection.networkInfo.height.toLocaleString()}, Peers: ${connection.networkInfo.peers}`);
  } else {
    console.log('❌ Connection: Failed to connect');
    allPassed = false;
  }
  
  // Wallet check
  if (wallet?.address) {
    console.log(`✅ Wallet: ${wallet.address}`);
    console.log(`   Balance: ${wallet.balance} AR (${wallet.status})`);
    
    if (wallet.status === 'zero_balance') {
      console.log('   ⚠️  WARNING: Zero balance - cannot upload');
      allPassed = false;
    } else if (wallet.status === 'low_balance') {
      console.log('   ⚠️  WARNING: Low balance - limited uploads');
    }
  } else {
    console.log('❌ Wallet: Failed to check');
    allPassed = false;
  }
  
  // Upload check
  if (upload?.success) {
    console.log(`✅ Test Upload: Success`);
    console.log(`   TX ID: ${upload.txId}`);
    console.log(`   URL: https://arweave.net/${upload.txId}`);
    console.log(`   Upload time: ${upload.uploadTime}s`);
  } else if (upload?.skipped) {
    console.log('ℹ️  Test Upload: Skipped (use --test-upload to enable)');
  } else {
    console.log('❌ Test Upload: Failed');
    if (upload?.error) console.log(`   Error: ${upload.error}`);
  }
  
  console.log('='.repeat(70));
  
  return allPassed;
}

// ====================================================================
// MAIN
// ====================================================================

async function main() {
  const startTime = Date.now();
  
  console.log('\n' + '='.repeat(70));
  console.log('🔍 ARWEAVE READINESS CHECK');
  console.log('='.repeat(70));
  console.log(`Started at: ${new Date().toISOString()}`);
  console.log(`Key path: ${KEY_PATH}`);
  console.log(`Test upload: ${TEST_UPLOAD ? 'ENABLED' : 'DISABLED'}`);
  
  const results = {};
  
  // Step 1: Load Key
  const key = await loadArweaveKey();
  results.key = key;
  if (!key) {
    console.log('\n' + '='.repeat(70));
    console.log('❌ ARWEAVE READINESS: NOT READY');
    console.log('='.repeat(70));
    console.log('\n⚠️  Cannot proceed without valid Arweave key');
    console.log('   Please fix the key file and try again');
    console.log('='.repeat(70));
    process.exit(1);
  }
  
  // Step 2: Init Client
  const arweave = initArweave();
  if (!arweave) {
    console.log('\n' + '='.repeat(70));
    console.log('❌ ARWEAVE READINESS: NOT READY');
    console.log('='.repeat(70));
    process.exit(1);
  }
  
  // Step 3: Check Connection
  const connection = await checkConnection(arweave);
  results.connection = connection;
  
  // Step 4: Check Balance
  const wallet = await checkWalletBalance(arweave, key);
  results.wallet = wallet;
  
  // Step 5: Test Upload (optional)
  const upload = await testUpload(arweave, key);
  results.upload = upload;
  
  // Step 6: Final Report
  const allPassed = generateReport(results);
  
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  
  console.log('\n' + '='.repeat(70));
  if (allPassed && (wallet?.status === 'ok' || wallet?.status === 'moderate')) {
    console.log('✅ ARWEAVE READINESS: READY ✅');
    console.log('='.repeat(70));
    console.log('\n🚀 Next steps:');
    console.log('   1. Run WITH_ARWEAVE=true DEPLOY_ACTION=555 for full Arweave integration');
    console.log('   2. Or run node scripts/archive/upload_all_components.js');
    console.log('   3. Monitor uploads at https://viewblock.io/arweave');
    if (upload?.txId) {
      console.log(`\n🔗 Test upload successful!`);
      console.log(`   View at: https://viewblock.io/arweave/tx/${upload.txId}`);
      console.log(`   Direct: https://arweave.net/${upload.txId}`);
    }
  } else {
    console.log('❌ ARWEAVE READINESS: NOT READY ❌');
    console.log('='.repeat(70));
    console.log('\n⚠️  Please fix the issues above before uploading to Arweave');
    console.log('\nCommon fixes:');
    console.log('   - Add AR to wallet (if zero balance)');
    console.log('   - Check internet connection (if connection failed)');
    console.log('   - Verify key file format (if key invalid)');
  }
  console.log(`\n⏱️  Total check time: ${totalTime}s`);
  console.log('='.repeat(70));
  
  process.exit(allPassed ? 0 : 1);
}

// ====================================================================
// MODULE EXPORTS
// ====================================================================

module.exports = {
  loadArweaveKey,
  initArweave,
  checkConnection,
  checkWalletBalance,
  testUpload,
  TEST_MESSAGE
};

// ====================================================================
// RUN
// ====================================================================

if (require.main === module) {
  main().catch(err => {
    console.error('\n' + '='.repeat(70));
    console.error('❌ FATAL ERROR');
    console.error('='.repeat(70));
    console.error(err);
    console.error('='.repeat(70));
    process.exit(1);
  });
}

