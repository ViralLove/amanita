const { ethers, upgrades } = require("hardhat");
require("dotenv").config();

/**
 * Скрипт для обновления implementation контракта SpiralEngine
 * 
 * Использование:
 * npx hardhat run scripts/upgrade-implementation.js --network localhost
 * npx hardhat run scripts/upgrade-implementation.js --network polygon
 * 
 * Переменные окружения:
 * - SPIRAL_ENGINE_PROXY_ADDRESS: Адрес proxy контракта
 * - NEW_IMPLEMENTATION: Путь к новому контракту (по умолчанию "SpiralEngineV2")
 */
async function main() {
    console.log("🔄 Начинаем обновление implementation контракта SpiralEngine...");
    
    // Получаем deployer аккаунт
    const [deployer] = await ethers.getSigners();
    console.log("📋 Deployer адрес:", deployer.address);
    console.log("💰 Deployer баланс:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");
    
    // Получаем адрес proxy контракта
    const proxyAddress = process.env.SPIRAL_ENGINE_PROXY_ADDRESS;
    if (!proxyAddress) {
        console.error("❌ SPIRAL_ENGINE_PROXY_ADDRESS не установлен в .env");
        console.log("💡 Установите SPIRAL_ENGINE_PROXY_ADDRESS в .env файле");
        process.exit(1);
    }
    
    console.log("🎯 Proxy адрес:", proxyAddress);
    
    try {
        // Получаем текущий proxy контракт
        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        const proxy = SpiralEngine.attach(proxyAddress);
        
        // Проверяем, что proxy контракт существует и работает
        console.log("🔍 Проверяем текущий proxy контракт...");
        const name = await proxy.name();
        const symbol = await proxy.symbol();
        console.log("📝 Текущий contract name:", name);
        console.log("🏷️ Текущий contract symbol:", symbol);
        
        // Получаем текущий implementation адрес
        const currentImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
        console.log("🔧 Текущий implementation адрес:", currentImplementation);
        
        // Определяем новый контракт для деплоя
        const newContractName = process.env.NEW_IMPLEMENTATION || "SpiralEngineV2";
        console.log("📦 Деплоим новый implementation:", newContractName);
        
        // Получаем фабрику нового контракта
        const NewSpiralEngine = await ethers.getContractFactory(newContractName);
        
        // Деплоим новую implementation
        console.log("🔧 Деплоим новую implementation...");
        const newImplementation = await NewSpiralEngine.deploy();
        await newImplementation.waitForDeployment();
        
        const newImplementationAddress = await newImplementation.getAddress();
        console.log("🆕 Новый implementation адрес:", newImplementationAddress);
        
        // Проверяем, что новая implementation работает
        console.log("🔍 Проверяем новую implementation...");
        const newName = await newImplementation.name();
        const newSymbol = await newImplementation.symbol();
        console.log("📝 Новый contract name:", newName);
        console.log("🏷️ Новый contract symbol:", newSymbol);
        
        // Обновляем proxy на новую implementation
        console.log("🔄 Обновляем proxy на новую implementation...");
        const upgradeTx = await upgrades.upgradeProxy(proxyAddress, NewSpiralEngine);
        await upgradeTx.waitForDeployment();
        
        console.log("✅ Proxy успешно обновлен на новую implementation!");
        
        // Проверяем, что upgrade прошел успешно
        const updatedImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
        console.log("🔧 Обновленный implementation адрес:", updatedImplementation);
        
        // Проверяем, что proxy контракт работает с новой implementation
        console.log("🔍 Проверяем работу proxy после upgrade...");
        const updatedName = await proxy.name();
        const updatedSymbol = await proxy.symbol();
        console.log("📝 Обновленный contract name:", updatedName);
        console.log("🏷️ Обновленный contract symbol:", updatedSymbol);
        
        // Проверяем, что данные сохранились
        console.log("🔍 Проверяем сохранность данных...");
        const totalInvitesMinted = await proxy.totalInvitesMinted();
        const totalInvitesUsed = await proxy.totalInvitesUsed();
        console.log("📊 Total invites minted:", totalInvitesMinted.toString());
        console.log("📊 Total invites used:", totalInvitesUsed.toString());
        
        // Проверяем роли deployer'а
        const DEFAULT_ADMIN_ROLE = await proxy.DEFAULT_ADMIN_ROLE();
        const hasAdminRole = await proxy.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
        console.log("👑 Deployer сохранил ADMIN_ROLE:", hasAdminRole);
        
        // Если есть функция getVersionInfo, проверяем версию
        try {
            const versionInfo = await proxy.getVersionInfo();
            console.log("📋 Версия контракта:", versionInfo);
        } catch (error) {
            console.log("ℹ️ Функция getVersionInfo недоступна (это нормально для первой версии)");
        }
        
        console.log("\n🎉 Upgrade завершен успешно!");
        console.log("📋 Старый implementation:", currentImplementation);
        console.log("📋 Новый implementation:", updatedImplementation);
        console.log("📋 Proxy адрес остался прежним:", proxyAddress);
        
        // Сохраняем новый implementation адрес в .env (опционально)
        if (process.env.SAVE_TO_ENV === 'true') {
            const fs = require('fs');
            const path = require('path');
            
            const envPath = path.join(__dirname, '..', '.env');
            let envContent = '';
            
            if (fs.existsSync(envPath)) {
                envContent = fs.readFileSync(envPath, 'utf8');
            }
            
            // Обновляем implementation адрес
            envContent = envContent.replace(
                /^SPIRAL_ENGINE_IMPLEMENTATION_ADDRESS=.*$/m, 
                `SPIRAL_ENGINE_IMPLEMENTATION_ADDRESS=${updatedImplementation}`
            );
            
            fs.writeFileSync(envPath, envContent);
            console.log("💾 Новый implementation адрес сохранен в .env файл");
        }
        
    } catch (error) {
        console.error("❌ Ошибка при upgrade:", error);
        
        if (error.message.includes("insufficient funds")) {
            console.log("💡 Решение: Убедитесь, что у deployer аккаунта достаточно ETH для покрытия gas costs");
        } else if (error.message.includes("not upgradeable")) {
            console.log("💡 Решение: Убедитесь, что контракт является upgradeable proxy");
        } else if (error.message.includes("storage")) {
            console.log("💡 Решение: Проверьте совместимость storage layout между версиями");
        } else if (error.message.includes("function")) {
            console.log("💡 Решение: Убедитесь, что новая implementation совместима с proxy");
        }
        
        process.exit(1);
    }
}

// Запускаем скрипт
main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("💥 Критическая ошибка:", error);
        process.exit(1);
    });
