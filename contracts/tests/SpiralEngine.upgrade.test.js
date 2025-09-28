const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

/**
 * Тесты для upgradeable SpiralEngine контракта
 * 
 * Покрывает:
 * - Деплой proxy контракта
 * - Обновление implementation
 * - Сохранение данных при upgrade
 * - Совместимость с существующими функциями
 */
describe("SpiralEngine Upgrade Tests", function () {
    let spiralEngine;
    let spiralEngineV2;
    let deployer, activator, seller, user;
    let proxyAddress, implementationAddress;

    beforeEach(async function () {
        // Получаем аккаунты
        [deployer, activator, seller, user] = await ethers.getSigners();
        
        console.log("🔧 Настройка тестовой среды для upgrade tests...");
    });

    describe("P0: Proxy Deployment", function () {
        it("Should deploy SpiralEngine as upgradeable proxy", async function () {
            console.log("📦 Тестируем деплой SpiralEngine как upgradeable proxy...");
            
            // Получаем фабрику контракта
            const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
            
            // Деплоим как upgradeable proxy
            spiralEngine = await upgrades.deployProxy(
                SpiralEngine,
                [], // Пустой массив аргументов
                {
                    initializer: false,
                    kind: 'transparent'
                }
            );
            
            await spiralEngine.waitForDeployment();
            
            proxyAddress = await spiralEngine.getAddress();
            implementationAddress = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            
            console.log("✅ Proxy адрес:", proxyAddress);
            console.log("✅ Implementation адрес:", implementationAddress);
            
            // Проверяем, что proxy работает
            expect(proxyAddress).to.not.equal(ethers.ZeroAddress);
            expect(implementationAddress).to.not.equal(ethers.ZeroAddress);
            
            // Проверяем базовую функциональность
            const name = await spiralEngine.name();
            const symbol = await spiralEngine.symbol();
            
            expect(name).to.equal("SpiralInvite");
            expect(symbol).to.equal("SPIRAL");
            
            console.log("✅ Proxy контракт работает корректно");
        });

        it("Should have correct roles assigned to deployer", async function () {
            console.log("👑 Проверяем роли deployer'а...");
            
            const DEFAULT_ADMIN_ROLE = await spiralEngine.DEFAULT_ADMIN_ROLE();
            const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
            const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
            
            const hasAdminRole = await spiralEngine.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
            const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, deployer.address);
            const hasActivatorRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, deployer.address);
            
            expect(hasAdminRole).to.be.true;
            expect(hasSellerRole).to.be.true;
            expect(hasActivatorRole).to.be.true;
            
            console.log("✅ Deployer имеет все необходимые роли");
        });
    });

    describe("P1: Data Persistence", function () {
        beforeEach(async function () {
            // Деплоим proxy для тестов данных
            const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
            spiralEngine = await upgrades.deployProxy(SpiralEngine, [], { initializer: false });
            await spiralEngine.waitForDeployment();
            
            proxyAddress = await spiralEngine.getAddress();
        });

        it("Should preserve data after upgrade", async function () {
            console.log("💾 Тестируем сохранение данных при upgrade...");
            
            // Создаем тестовые данные
            console.log("📝 Создаем тестовые данные...");
            
            // Даем activator роль SELLER_ROLE
            const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            
            // Создаем инвайт
            await spiralEngine.connect(activator).mintInvite("UPGRADE_TEST_INVITE", 0);
            const tokenId = await spiralEngine.inviteCodeToTokenId("UPGRADE_TEST_INVITE");
            
            // Активируем пользователя
            const newCodes = Array.from({length: 12}, (_, i) => `UPGRADE_NEW_${i + 1}`);
            await spiralEngine.connect(activator).activateUser(
                "UPGRADE_TEST_INVITE",
                user.address,
                newCodes,
                0
            );
            
            // Даем пользователю роль SELLER_ROLE
            await spiralEngine.connect(activator).grantSellerRole(user.address);
            
            // Проверяем состояние до upgrade
            const totalInvitesMintedBefore = await spiralEngine.totalInvitesMinted();
            const totalInvitesUsedBefore = await spiralEngine.totalInvitesUsed();
            const usedInviteBefore = await spiralEngine.usedInviteByUser(user.address);
            const hasSellerRoleBefore = await spiralEngine.hasRole(SELLER_ROLE, user.address);
            
            console.log("📊 Состояние до upgrade:");
            console.log("   - Total invites minted:", totalInvitesMintedBefore.toString());
            console.log("   - Total invites used:", totalInvitesUsedBefore.toString());
            console.log("   - User used invite:", usedInviteBefore.toString());
            console.log("   - User has seller role:", hasSellerRoleBefore);
            
            // Создаем SpiralEngineV2 (пока используем тот же контракт)
            console.log("🔄 Выполняем upgrade...");
            const SpiralEngineV2 = await ethers.getContractFactory("SpiralEngine");
            
            // Выполняем upgrade
            await upgrades.upgradeProxy(proxyAddress, SpiralEngineV2);
            
            // Получаем обновленный контракт
            const upgradedEngine = await ethers.getContractAt("SpiralEngine", proxyAddress);
            
            // Проверяем состояние после upgrade
            const totalInvitesMintedAfter = await upgradedEngine.totalInvitesMinted();
            const totalInvitesUsedAfter = await upgradedEngine.totalInvitesUsed();
            const usedInviteAfter = await upgradedEngine.usedInviteByUser(user.address);
            const hasSellerRoleAfter = await upgradedEngine.hasRole(SELLER_ROLE, user.address);
            
            console.log("📊 Состояние после upgrade:");
            console.log("   - Total invites minted:", totalInvitesMintedAfter.toString());
            console.log("   - Total invites used:", totalInvitesUsedAfter.toString());
            console.log("   - User used invite:", usedInviteAfter.toString());
            console.log("   - User has seller role:", hasSellerRoleAfter);
            
            // Проверяем, что данные сохранились
            expect(totalInvitesMintedAfter).to.equal(totalInvitesMintedBefore);
            expect(totalInvitesUsedAfter).to.equal(totalInvitesUsedBefore);
            expect(usedInviteAfter).to.equal(usedInviteBefore);
            expect(hasSellerRoleAfter).to.equal(hasSellerRoleBefore);
            
            console.log("✅ Все данные сохранились после upgrade");
        });

        it("Should preserve invite codes and mappings", async function () {
            console.log("🎫 Тестируем сохранение инвайт-кодов и маппингов...");
            
            // Создаем инвайт
            const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            await spiralEngine.connect(activator).mintInvite("MAPPING_TEST_INVITE", 0);
            
            // Проверяем маппинги до upgrade
            const tokenIdBefore = await spiralEngine.inviteCodeToTokenId("MAPPING_TEST_INVITE");
            const inviteCodeBefore = await spiralEngine.tokenIdToInviteCode(tokenIdBefore);
            const inviteExistsBefore = await spiralEngine.inviteCodeExists("MAPPING_TEST_INVITE");
            const isUsedBefore = await spiralEngine.isInviteUsed(tokenIdBefore);
            
            console.log("📊 Маппинги до upgrade:");
            console.log("   - Token ID:", tokenIdBefore.toString());
            console.log("   - Invite code:", inviteCodeBefore);
            console.log("   - Invite exists:", inviteExistsBefore);
            console.log("   - Is used:", isUsedBefore);
            
            // Выполняем upgrade
            const SpiralEngineV2 = await ethers.getContractFactory("SpiralEngine");
            await upgrades.upgradeProxy(proxyAddress, SpiralEngineV2);
            
            const upgradedEngine = await ethers.getContractAt("SpiralEngine", proxyAddress);
            
            // Проверяем маппинги после upgrade
            const tokenIdAfter = await upgradedEngine.inviteCodeToTokenId("MAPPING_TEST_INVITE");
            const inviteCodeAfter = await upgradedEngine.tokenIdToInviteCode(tokenIdAfter);
            const inviteExistsAfter = await upgradedEngine.inviteCodeExists("MAPPING_TEST_INVITE");
            const isUsedAfter = await upgradedEngine.isInviteUsed(tokenIdAfter);
            
            console.log("📊 Маппинги после upgrade:");
            console.log("   - Token ID:", tokenIdAfter.toString());
            console.log("   - Invite code:", inviteCodeAfter);
            console.log("   - Invite exists:", inviteExistsAfter);
            console.log("   - Is used:", isUsedAfter);
            
            // Проверяем сохранность маппингов
            expect(tokenIdAfter).to.equal(tokenIdBefore);
            expect(inviteCodeAfter).to.equal(inviteCodeBefore);
            expect(inviteExistsAfter).to.equal(inviteExistsBefore);
            expect(isUsedAfter).to.equal(isUsedBefore);
            
            console.log("✅ Все маппинги сохранились после upgrade");
        });
    });

    describe("P2: Function Compatibility", function () {
        beforeEach(async function () {
            // Деплоим proxy для тестов совместимости
            const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
            spiralEngine = await upgrades.deployProxy(SpiralEngine, [], { initializer: false });
            await spiralEngine.waitForDeployment();
            
            proxyAddress = await spiralEngine.getAddress();
        });

        it("Should maintain all existing functions after upgrade", async function () {
            console.log("🔧 Тестируем совместимость функций после upgrade...");
            
            // Выполняем upgrade
            const SpiralEngineV2 = await ethers.getContractFactory("SpiralEngine");
            await upgrades.upgradeProxy(proxyAddress, SpiralEngineV2);
            
            const upgradedEngine = await ethers.getContractAt("SpiralEngine", proxyAddress);
            
            // Проверяем основные функции
            console.log("🔍 Проверяем основные функции...");
            
            const name = await upgradedEngine.name();
            const symbol = await upgradedEngine.symbol();
            const totalInvitesMinted = await upgradedEngine.totalInvitesMinted();
            const totalInvitesUsed = await upgradedEngine.totalInvitesUsed();
            
            expect(name).to.equal("SpiralInvite");
            expect(symbol).to.equal("SPIRAL");
            expect(totalInvitesMinted).to.be.a("bigint");
            expect(totalInvitesUsed).to.be.a("bigint");
            
            console.log("✅ Основные функции работают");
            
            // Проверяем функции диагностики
            console.log("🔍 Проверяем функции диагностики...");
            
            const publicInfo = await upgradedEngine.getSellerPublicInfo(deployer.address);
            expect(publicInfo.isActivated).to.be.a("boolean");
            expect(publicInfo.hasSellerRole).to.be.a("boolean");
            expect(publicInfo.hasActivatorRole).to.be.a("boolean");
            expect(publicInfo.inviteCount).to.be.a("bigint");
            expect(publicInfo.userTotalInvites).to.be.a("bigint");
            
            console.log("✅ Функции диагностики работают");
            
            // Проверяем функции кругов
            console.log("🔍 Проверяем функции кругов...");
            
            const circleSize = await upgradedEngine.getCircleSize(deployer.address);
            const circleMembers = await upgradedEngine.getCircleMembers(deployer.address);
            
            expect(circleSize).to.be.a("bigint");
            expect(circleMembers).to.be.an("array");
            
            console.log("✅ Функции кругов работают");
            
            console.log("✅ Все функции совместимы после upgrade");
        });

        it("Should maintain role system after upgrade", async function () {
            console.log("👑 Тестируем систему ролей после upgrade...");
            
            // Выполняем upgrade
            const SpiralEngineV2 = await ethers.getContractFactory("SpiralEngine");
            await upgrades.upgradeProxy(proxyAddress, SpiralEngineV2);
            
            const upgradedEngine = await ethers.getContractAt("SpiralEngine", proxyAddress);
            
            // Проверяем роли
            const DEFAULT_ADMIN_ROLE = await upgradedEngine.DEFAULT_ADMIN_ROLE();
            const SELLER_ROLE = await upgradedEngine.SELLER_ROLE();
            const ACTIVATOR_ROLE = await upgradedEngine.ACTIVATOR_ROLE();
            
            const hasAdminRole = await upgradedEngine.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
            const hasSellerRole = await upgradedEngine.hasRole(SELLER_ROLE, deployer.address);
            const hasActivatorRole = await upgradedEngine.hasRole(ACTIVATOR_ROLE, deployer.address);
            
            expect(hasAdminRole).to.be.true;
            expect(hasSellerRole).to.be.true;
            expect(hasActivatorRole).to.be.true;
            
            console.log("✅ Система ролей работает после upgrade");
        });
    });

    describe("P3: Upgrade Validation", function () {
        beforeEach(async function () {
            // Деплоим proxy для тестов валидации
            const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
            spiralEngine = await upgrades.deployProxy(SpiralEngine, [], { initializer: false });
            await spiralEngine.waitForDeployment();
            
            proxyAddress = await spiralEngine.getAddress();
        });

        it("Should validate proxy structure", async function () {
            console.log("🔍 Тестируем структуру proxy...");
            
            // Проверяем, что контракт является proxy
            const implementationAddress = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            const adminAddress = await upgrades.erc1967.getAdminAddress(proxyAddress);
            
            expect(implementationAddress).to.not.equal(ethers.ZeroAddress);
            expect(adminAddress).to.not.equal(ethers.ZeroAddress);
            
            console.log("✅ Implementation адрес:", implementationAddress);
            console.log("✅ Admin адрес:", adminAddress);
            
            // Проверяем, что proxy адрес не изменился
            const currentProxyAddress = await spiralEngine.getAddress();
            expect(currentProxyAddress).to.equal(proxyAddress);
            
            console.log("✅ Proxy структура валидна");
        });

        it("Should validate upgrade process", async function () {
            console.log("🔄 Тестируем процесс upgrade...");
            
            // Получаем текущий implementation
            const currentImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            console.log("📋 Текущий implementation:", currentImplementation);
            
            // Выполняем upgrade
            const SpiralEngineV2 = await ethers.getContractFactory("SpiralEngine");
            await upgrades.upgradeProxy(proxyAddress, SpiralEngineV2);
            
            // Проверяем новый implementation
            const newImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            console.log("📋 Новый implementation:", newImplementation);
            
            // Implementation должен измениться
            expect(newImplementation).to.not.equal(currentImplementation);
            
            // Proxy адрес должен остаться прежним
            const upgradedEngine = await ethers.getContractAt("SpiralEngine", proxyAddress);
            const proxyAddressAfter = await upgradedEngine.getAddress();
            expect(proxyAddressAfter).to.equal(proxyAddress);
            
            console.log("✅ Процесс upgrade валиден");
        });
    });
});
