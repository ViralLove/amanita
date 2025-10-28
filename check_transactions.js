const axios = require('axios');

async function checkTransactions() {
    const DEPLOYER_ADDRESS = "0x0128CbBD12e50ACC55D00cA99457691E9f5d0bd0";
    const SELLER_ADDRESS = "0x21d994213d88b4ccDA265036557788B9B910610D";
    const POLYGONSCAN_API_KEY = process.env.POLYGONSCAN_API_KEY || "";
    
    console.log("");
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("🔍 ПРОВЕРКА ТРАНЗАКЦИЙ НА POLYGON");
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("");
    
    console.log("📍 Адреса для проверки:");
    console.log(`   → Deployer: ${DEPLOYER_ADDRESS}`);
    console.log(`   → Seller: ${SELLER_ADDRESS}`);
    console.log("");
    
    console.log("🌐 PolygonScan URLs:");
    console.log(`   → Deployer: https://polygonscan.com/address/${DEPLOYER_ADDRESS}`);
    console.log(`   → Seller: https://polygonscan.com/address/${SELLER_ADDRESS}`);
    console.log("");
    
    if (!POLYGONSCAN_API_KEY) {
        console.log("⚠️ POLYGONSCAN_API_KEY не установлен в .env");
        console.log("   → Для автоматической проверки добавьте ключ API");
        console.log("   → Получить можно на https://polygonscan.com/apis");
        console.log("");
        console.log("📊 Проверьте транзакции вручную по ссылкам выше");
        console.log("");
        console.log("🔍 Что искать:");
        console.log("   1. Исходящие транзакции (OUT)");
        console.log("   2. Неизвестные адреса получателей");
        console.log("   3. Время последних транзакций");
        console.log("   4. Суммы переводов");
        console.log("");
        return;
    }
    
    // Функция для получения транзакций
    async function getTransactions(address) {
        try {
            const response = await axios.get('https://api.polygonscan.com/api', {
                params: {
                    module: 'account',
                    action: 'txlist',
                    address: address,
                    startblock: 0,
                    endblock: 99999999,
                    page: 1,
                    offset: 20,
                    sort: 'desc',
                    apikey: POLYGONSCAN_API_KEY
                }
            });
            
            if (response.data.status === "1") {
                return response.data.result;
            } else {
                console.log(`⚠️ Ошибка API: ${response.data.message}`);
                return [];
            }
        } catch (error) {
            console.log(`❌ Ошибка запроса: ${error.message}`);
            return [];
        }
    }
    
    // Функция для получения баланса
    async function getBalance(address) {
        try {
            const response = await axios.get('https://api.polygonscan.com/api', {
                params: {
                    module: 'account',
                    action: 'balance',
                    address: address,
                    apikey: POLYGONSCAN_API_KEY
                }
            });
            
            if (response.data.status === "1") {
                const balanceWei = BigInt(response.data.result);
                const balanceMatic = Number(balanceWei) / 1e18;
                return balanceMatic;
            }
            return 0;
        } catch (error) {
            console.log(`❌ Ошибка запроса баланса: ${error.message}`);
            return 0;
        }
    }
    
    // Проверка Deployer
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("📊 DEPLOYER ADDRESS");
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("");
    
    const deployerBalance = await getBalance(DEPLOYER_ADDRESS);
    console.log(`💰 Баланс: ${deployerBalance} MATIC`);
    console.log("");
    
    const deployerTxs = await getTransactions(DEPLOYER_ADDRESS);
    console.log(`📜 Последние транзакции: ${deployerTxs.length}`);
    console.log("");
    
    if (deployerTxs.length > 0) {
        console.log("🔍 Топ-5 последних транзакций:");
        for (let i = 0; i < Math.min(5, deployerTxs.length); i++) {
            const tx = deployerTxs[i];
            const date = new Date(tx.timeStamp * 1000).toISOString();
            const value = Number(BigInt(tx.value)) / 1e18;
            const direction = tx.from.toLowerCase() === DEPLOYER_ADDRESS.toLowerCase() ? "OUT 🔴" : "IN  🟢";
            const otherAddress = tx.from.toLowerCase() === DEPLOYER_ADDRESS.toLowerCase() ? tx.to : tx.from;
            
            console.log(`\n   ${i + 1}. ${direction}`);
            console.log(`      → Дата: ${date}`);
            console.log(`      → Сумма: ${value} MATIC`);
            console.log(`      → ${direction === "OUT 🔴" ? "Получатель" : "Отправитель"}: ${otherAddress}`);
            console.log(`      → Hash: https://polygonscan.com/tx/${tx.hash}`);
        }
    }
    
    console.log("");
    console.log("");
    
    // Проверка Seller
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("📊 SELLER ADDRESS");
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("");
    
    const sellerBalance = await getBalance(SELLER_ADDRESS);
    console.log(`💰 Баланс: ${sellerBalance} MATIC`);
    console.log("");
    
    const sellerTxs = await getTransactions(SELLER_ADDRESS);
    console.log(`📜 Последние транзакции: ${sellerTxs.length}`);
    console.log("");
    
    if (sellerTxs.length > 0) {
        console.log("🔍 Топ-5 последних транзакций:");
        for (let i = 0; i < Math.min(5, sellerTxs.length); i++) {
            const tx = sellerTxs[i];
            const date = new Date(tx.timeStamp * 1000).toISOString();
            const value = Number(BigInt(tx.value)) / 1e18;
            const direction = tx.from.toLowerCase() === SELLER_ADDRESS.toLowerCase() ? "OUT 🔴" : "IN  🟢";
            const otherAddress = tx.from.toLowerCase() === SELLER_ADDRESS.toLowerCase() ? tx.to : tx.from;
            
            console.log(`\n   ${i + 1}. ${direction}`);
            console.log(`      → Дата: ${date}`);
            console.log(`      → Сумма: ${value} MATIC`);
            console.log(`      → ${direction === "OUT 🔴" ? "Получатель" : "Отправитель"}: ${otherAddress}`);
            console.log(`      → Hash: https://polygonscan.com/tx/${tx.hash}`);
        }
    }
    
    console.log("");
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("");
}

checkTransactions().catch(console.error);
