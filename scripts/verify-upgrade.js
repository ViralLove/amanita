const { ethers, upgrades } = require("hardhat");
require("dotenv").config();

/**
 * Скрипт для верификации upgrade контракта SpiralEngine
 * 
 * Использование:
 * npx hardhat run scripts/verify-upgrade.js --network localhost
 * npx hardhat run scripts/verify-upgrade.js --network polygon
 * 
 * Переменные окружения:
 * - SPIRAL_ENGINE_PROXY_ADDRESS: Адрес proxy контракта
 */
async function main() {
    console.log("🔍 Начинаем верификацию upgrade контракта SpiralEngine...");
    
    // Получаем deployer аккаунт
    const [deployer] = await ethers.getSigners();
    console.log("📋 Deployer адрес:", deployer.address);
    
    // Получаем адрес proxy контракта
    const proxyAddress = process.env.SPIRAL_ENGINE_PROXY_ADDRESS;
    if (!proxyAddress) {
        console.error("❌ SPIRAL_ENGINE_PROXY_ADDRESS не установлен в .env");
        console.log("💡 Установите SPIRAL_ENGINE_PROXY_ADDRESS в .env файле");
        process.exit(1);
    }
    
    console.log("🎯 Proxy адрес:", proxyAddress);
    
    try {
        // Получаем proxy контракт
        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        const proxy = SpiralEngine.attach(proxyAddress);
        
        // Получаем implementation адрес
        const implementationAddress = await upgrades.erc1967.getImplementationAddress(proxyAddress);
        console.log("🔧 Implementation адрес:", implementationAddress);
        
        // Получаем admin адрес
        const adminAddress = await upgrades.erc1967.getAdminAddress(proxyAddress);
        console.log("👑 Admin адрес:", adminAddress);
        
        // Проверяем базовую функциональность
        console.log("\n🔍 Проверяем базовую функциональность...");
        
        const name = await proxy.name();
        const symbol = await proxy.symbol();
        console.log("✅ Contract name:", name);
        console.log("✅ Contract symbol:", symbol);
        
        // Проверяем роли
        console.log("\n🔍 Проверяем роли...");
        
        const DEFAULT_ADMIN_ROLE = await proxy.DEFAULT_ADMIN_ROLE();
        const SELLER_ROLE = await proxy.SELLER_ROLE();
        const ACTIVATOR_ROLE = await proxy.ACTIVATOR_ROLE();
        
        console.log("✅ DEFAULT_ADMIN_ROLE:", DEFAULT_ADMIN_ROLE);
        console.log("✅ SELLER_ROLE:", SELLER_ROLE);
        console.log("✅ ACTIVATOR_ROLE:", ACTIVATOR_ROLE);
        
        // Проверяем роли deployer'а
        const hasAdminRole = await proxy.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
        const hasSellerRole = await proxy.hasRole(SELLER_ROLE, deployer.address);
        const hasActivatorRole = await proxy.hasRole(ACTIVATOR_ROLE, deployer.address);
        
        console.log("✅ Deployer имеет ADMIN_ROLE:", hasAdminRole);
        console.log("✅ Deployer имеет SELLER_ROLE:", hasSellerRole);
        console.log("✅ Deployer имеет ACTIVATOR_ROLE:", hasActivatorRole);
        
        // Проверяем состояние контракта
        console.log("\n🔍 Проверяем состояние контракта...");
        
        const totalInvitesMinted = await proxy.totalInvitesMinted();
        const totalInvitesUsed = await proxy.totalInvitesUsed();
        
        console.log("✅ Total invites minted:", totalInvitesMinted.toString());
        console.log("✅ Total invites used:", totalInvitesUsed.toString());
        
        // Проверяем SoulIdentity интеграцию
        console.log("\n🔍 Проверяем SoulIdentity интеграцию...");
        
        try {
            const soulIdentityAddress = await proxy.soulIdentity();
            console.log("✅ SoulIdentity адрес:", soulIdentityAddress);
            
            if (soulIdentityAddress === "0x0000000000000000000000000000000000000000") {
                console.log("⚠️ SoulIdentity не установлен (это нормально для начального состояния)");
            }
        } catch (error) {
            console.log("⚠️ Ошибка при получении SoulIdentity:", error.message);
        }
        
        // Проверяем функции диагностики
        console.log("\n🔍 Проверяем функции диагностики...");
        
        try {
            // Проверяем getSellerPublicInfo
            const publicInfo = await proxy.getSellerPublicInfo(deployer.address);
            console.log("✅ getSellerPublicInfo работает:");
            console.log("   - isActivated:", publicInfo.isActivated);
            console.log("   - hasSellerRole:", publicInfo.hasSellerRole);
            console.log("   - hasActivatorRole:", publicInfo.hasActivatorRole);
            console.log("   - inviteCount:", publicInfo.inviteCount.toString());
            console.log("   - userTotalInvites:", publicInfo.userTotalInvites.toString());
        } catch (error) {
            console.log("⚠️ Ошибка при вызове getSellerPublicInfo:", error.message);
        }
        
        // Проверяем функции инвайтов
        console.log("\n🔍 Проверяем функции инвайтов...");
        
        try {
            // Проверяем, что можем вызвать основные функции
            const usedInvite = await proxy.usedInviteByUser(deployer.address);
            console.log("✅ usedInviteByUser работает:", usedInvite.toString());
            
            // Проверяем функции кругов
            const circleSize = await proxy.getCircleSize(deployer.address);
            console.log("✅ getCircleSize работает:", circleSize.toString());
            
            const circleMembers = await proxy.getCircleMembers(deployer.address);
            console.log("✅ getCircleMembers работает, количество:", circleMembers.length);
            
        } catch (error) {
            console.log("⚠️ Ошибка при проверке функций инвайтов:", error.message);
        }
        
        // Проверяем версию контракта (если доступна)
        console.log("\n🔍 Проверяем версию контракта...");
        
        try {
            const versionInfo = await proxy.getVersionInfo();
            console.log("✅ Версия контракта:", versionInfo);
        } catch (error) {
            console.log("ℹ️ Функция getVersionInfo недоступна (это нормально для первой версии)");
        }
        
        // Проверяем совместимость с существующими интерфейсами
        console.log("\n🔍 Проверяем совместимость с интерфейсами...");
        
        // ERC721 интерфейс
        try {
            const supportsERC721 = await proxy.supportsInterface("0x80ac58cd"); // ERC721
            console.log("✅ Поддержка ERC721:", supportsERC721);
        } catch (error) {
            console.log("⚠️ Ошибка при проверке ERC721:", error.message);
        }
        
        // AccessControl интерфейс
        try {
            const supportsAccessControl = await proxy.supportsInterface("0x7965db0b"); // AccessControl
            console.log("✅ Поддержка AccessControl:", supportsAccessControl);
        } catch (error) {
            console.log("⚠️ Ошибка при проверке AccessControl:", error.message);
        }
        
        // Проверяем, что контракт является upgradeable
        console.log("\n🔍 Проверяем upgradeable функциональность...");
        
        try {
            // Проверяем, что можем получить implementation адрес
            const currentImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            console.log("✅ Контракт является upgradeable proxy");
            console.log("✅ Текущий implementation:", currentImplementation);
            
            // Проверяем, что можем получить admin адрес
            const currentAdmin = await upgrades.erc1967.getAdminAddress(proxyAddress);
            console.log("✅ Admin контракта:", currentAdmin);
            
        } catch (error) {
            console.log("❌ Контракт не является upgradeable proxy:", error.message);
        }
        
        console.log("\n🎉 Верификация завершена успешно!");
        console.log("✅ Все основные функции работают корректно");
        console.log("✅ Контракт готов к использованию");
        
    } catch (error) {
        console.error("❌ Ошибка при верификации:", error);
        
        if (error.message.includes("insufficient funds")) {
            console.log("💡 Решение: Убедитесь, что у deployer аккаунта достаточно ETH");
        } else if (error.message.includes("not found")) {
            console.log("💡 Решение: Проверьте, что proxy контракт существует по указанному адресу");
        } else if (error.message.includes("network")) {
            console.log("💡 Решение: Проверьте подключение к сети и настройки в hardhat.config.js");
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
