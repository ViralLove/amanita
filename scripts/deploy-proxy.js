const { ethers, upgrades } = require("hardhat");
require("dotenv").config();

/**
 * Скрипт для деплоя SpiralEngine как upgradeable proxy контракта
 * 
 * Использование:
 * npx hardhat run scripts/deploy-proxy.js --network localhost
 * npx hardhat run scripts/deploy-proxy.js --network polygon
 */
async function main() {
    console.log("🚀 Начинаем деплой SpiralEngine как upgradeable proxy...");
    
    // Получаем deployer аккаунт
    const [deployer] = await ethers.getSigners();
    console.log("📋 Deployer адрес:", deployer.address);
    console.log("💰 Deployer баланс:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");
    
    // Проверяем, что у нас есть достаточно газа
    const gasPrice = await ethers.provider.getGasPrice();
    console.log("⛽ Gas price:", ethers.formatUnits(gasPrice, "gwei"), "gwei");
    
    try {
        // Получаем фабрику контракта SpiralEngine
        console.log("📦 Получаем фабрику SpiralEngine...");
        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        
        // Деплоим как upgradeable proxy
        console.log("🔧 Деплоим SpiralEngine как upgradeable proxy...");
        const spiralEngine = await upgrades.deployProxy(
            SpiralEngine,
            [], // Пустой массив аргументов (конструктор не принимает параметры)
            {
                initializer: false, // Не вызываем initializer, так как у нас есть constructor
                kind: 'transparent' // Используем Transparent proxy
            }
        );
        
        await spiralEngine.waitForDeployment();
        
        const proxyAddress = await spiralEngine.getAddress();
        const implementationAddress = await upgrades.erc1967.getImplementationAddress(proxyAddress);
        
        console.log("✅ SpiralEngine proxy успешно задеплоен!");
        console.log("🎯 Proxy адрес:", proxyAddress);
        console.log("🔧 Implementation адрес:", implementationAddress);
        
        // Проверяем базовую функциональность
        console.log("🔍 Проверяем базовую функциональность...");
        const name = await spiralEngine.name();
        const symbol = await spiralEngine.symbol();
        console.log("📝 Contract name:", name);
        console.log("🏷️ Contract symbol:", symbol);
        
        // Проверяем роли deployer'а
        const DEFAULT_ADMIN_ROLE = await spiralEngine.DEFAULT_ADMIN_ROLE();
        const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
        
        const hasAdminRole = await spiralEngine.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
        const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, deployer.address);
        const hasActivatorRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, deployer.address);
        
        console.log("👑 Deployer имеет ADMIN_ROLE:", hasAdminRole);
        console.log("🛍️ Deployer имеет SELLER_ROLE:", hasSellerRole);
        console.log("⚡ Deployer имеет ACTIVATOR_ROLE:", hasActivatorRole);
        
        // Сохраняем адреса в .env файл (опционально)
        if (process.env.SAVE_TO_ENV === 'true') {
            const fs = require('fs');
            const path = require('path');
            
            const envPath = path.join(__dirname, '..', '.env');
            let envContent = '';
            
            if (fs.existsSync(envPath)) {
                envContent = fs.readFileSync(envPath, 'utf8');
            }
            
            // Удаляем старые записи если есть
            envContent = envContent.replace(/^SPIRAL_ENGINE_PROXY_ADDRESS=.*$/m, '');
            envContent = envContent.replace(/^SPIRAL_ENGINE_IMPLEMENTATION_ADDRESS=.*$/m, '');
            
            // Добавляем новые записи
            envContent += `\nSPIRAL_ENGINE_PROXY_ADDRESS=${proxyAddress}\n`;
            envContent += `SPIRAL_ENGINE_IMPLEMENTATION_ADDRESS=${implementationAddress}\n`;
            
            fs.writeFileSync(envPath, envContent);
            console.log("💾 Адреса сохранены в .env файл");
        }
        
        console.log("\n🎉 Деплой завершен успешно!");
        console.log("📋 Для использования обновите SPIRAL_ENGINE_CONTRACT_ADDRESS в .env на:", proxyAddress);
        
    } catch (error) {
        console.error("❌ Ошибка при деплое:", error);
        
        if (error.message.includes("insufficient funds")) {
            console.log("💡 Решение: Убедитесь, что у deployer аккаунта достаточно ETH для покрытия gas costs");
        } else if (error.message.includes("nonce")) {
            console.log("💡 Решение: Попробуйте увеличить nonce или подождите немного");
        } else if (error.message.includes("gas")) {
            console.log("💡 Решение: Попробуйте увеличить gas limit в hardhat.config.js");
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
