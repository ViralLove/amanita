const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

/**
 * Тесты для upgradeable SpiralEngine UUPS контракта
 * 
 * Покрывает:
 * - Деплой UUPS proxy контракта
 * - Обновление Logic implementation
 * - Сохранение данных при upgrade
 * - Совместимость с существующими функциями
 * - UUPS-специфичные проверки
 */
describe("SpiralEngine UUPS Upgrade Tests", function () {
    let spiralEngine;
    let spiralEngineV2;
    let deployer, activator, seller, user;
    let proxyAddress, logicAddress;

    beforeEach(async function () {
        // Получаем аккаунты
        [deployer, activator, seller, user] = await ethers.getSigners();
        
        console.log("🔧 Настройка тестовой среды для UUPS upgrade tests...");
    });

    describe("P0: UUPS Proxy Deployment", function () {
        it("Should deploy SpiralEngine as UUPS upgradeable proxy", async function () {
            console.log("📦 Тестируем деплой SpiralEngine как UUPS proxy...");
            
            // 1. Deploy Logic implementation
            const Logic = await ethers.getContractFactory("SpiralEngineLogic");
            const logicImpl = await Logic.connect(deployer).deploy();
            await logicImpl.waitForDeployment();
            logicAddress = await logicImpl.getAddress();
            
            // 2. Encode initialize(admin) calldata
            const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [
                deployer.address
            ]);
            
            // 3. Deploy Proxy with implementation and init data
            const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
            const proxy = await Proxy.connect(deployer).deploy(logicAddress, initCalldata);
            await proxy.waitForDeployment();
            proxyAddress = await proxy.getAddress();
            
            // 4. Attach Logic ABI to proxy address
            spiralEngine = Logic.attach(proxyAddress);
            
            console.log("✅ Proxy адрес:", proxyAddress);
            console.log("✅ Logic адрес:", logicAddress);
            
            // Проверяем, что proxy работает
            expect(proxyAddress).to.not.equal(ethers.ZeroAddress);
            expect(logicAddress).to.not.equal(ethers.ZeroAddress);
            
            // Проверяем базовую функциональность
            const name = await spiralEngine.name();
            const symbol = await spiralEngine.symbol();
            
            expect(name).to.equal("SpiralInvite");
            expect(symbol).to.equal("SPIRAL");
            
            // Проверяем LOGIC_VERSION
            expect(await spiralEngine.LOGIC_VERSION()).to.equal(1);
            
            console.log("✅ UUPS Proxy контракт работает корректно");
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
            // Деплоим UUPS proxy для тестов данных
            const Logic = await ethers.getContractFactory("SpiralEngineLogic");
            const logicImpl = await Logic.connect(deployer).deploy();
            await logicImpl.waitForDeployment();
            
            const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [deployer.address]);
            
            const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
            const proxy = await Proxy.connect(deployer).deploy(
                await logicImpl.getAddress(),
                initCalldata
            );
            await proxy.waitForDeployment();
            
            spiralEngine = Logic.attach(await proxy.getAddress());
            proxyAddress = await proxy.getAddress();
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
            
            // Даем activator роль ACTIVATOR_ROLE для активации
            const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            
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
            
            // Создаем LogicV2 (пока используем тот же контракт)
            console.log("🔄 Выполняем UUPS upgrade...");
            const LogicV2 = await ethers.getContractFactory("SpiralEngineLogic");
            const logicV2 = await LogicV2.connect(deployer).deploy();
            await logicV2.waitForDeployment();
            
            // Выполняем upgrade через upgradeToAndCall
            await spiralEngine.connect(deployer).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x" // Нет миграции данных
            );
            
            // Получаем обновленный контракт (ABI остаётся тот же, адрес Proxy тот же)
            const upgradedEngine = spiralEngine;
            
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
            
            // Выполняем UUPS upgrade
            const LogicV2 = await ethers.getContractFactory("SpiralEngineLogic");
            const logicV2 = await LogicV2.connect(deployer).deploy();
            await logicV2.waitForDeployment();
            
            await spiralEngine.connect(deployer).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"
            );
            
            const upgradedEngine = spiralEngine;
            
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
            // Деплоим UUPS proxy для тестов совместимости
            const Logic = await ethers.getContractFactory("SpiralEngineLogic");
            const logicImpl = await Logic.connect(deployer).deploy();
            await logicImpl.waitForDeployment();
            
            const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [deployer.address]);
            
            const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
            const proxy = await Proxy.connect(deployer).deploy(
                await logicImpl.getAddress(),
                initCalldata
            );
            await proxy.waitForDeployment();
            
            spiralEngine = Logic.attach(await proxy.getAddress());
            proxyAddress = await proxy.getAddress();
        });

        it("Should maintain all existing functions after upgrade", async function () {
            console.log("🔧 Тестируем совместимость функций после UUPS upgrade...");
            
            // Выполняем UUPS upgrade
            const LogicV2 = await ethers.getContractFactory("SpiralEngineLogic");
            const logicV2 = await LogicV2.connect(deployer).deploy();
            await logicV2.waitForDeployment();
            
            await spiralEngine.connect(deployer).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"
            );
            
            const upgradedEngine = spiralEngine;
            
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
            // В UUPS версии возвращаемые значения: isActivated, hasSellerRole_, hasActivatorRole_, inviteCount, userTotalInvites
            expect(publicInfo[0]).to.be.a("boolean"); // isActivated
            expect(publicInfo[1]).to.be.a("boolean"); // hasSellerRole_
            expect(publicInfo[2]).to.be.a("boolean"); // hasActivatorRole_
            expect(publicInfo[3]).to.be.a("bigint");  // inviteCount
            expect(publicInfo[4]).to.be.a("bigint");  // userTotalInvites
            
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
            console.log("👑 Тестируем систему ролей после UUPS upgrade...");
            
            // Выполняем UUPS upgrade
            const LogicV2 = await ethers.getContractFactory("SpiralEngineLogic");
            const logicV2 = await LogicV2.connect(deployer).deploy();
            await logicV2.waitForDeployment();
            
            await spiralEngine.connect(deployer).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"
            );
            
            const upgradedEngine = spiralEngine;
            
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

    describe("P3: UUPS Upgrade Validation", function () {
        beforeEach(async function () {
            // Деплоим UUPS proxy для тестов валидации
            const Logic = await ethers.getContractFactory("SpiralEngineLogic");
            const logicImpl = await Logic.connect(deployer).deploy();
            await logicImpl.waitForDeployment();
            
            const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [deployer.address]);
            
            const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
            const proxy = await Proxy.connect(deployer).deploy(
                await logicImpl.getAddress(),
                initCalldata
            );
            await proxy.waitForDeployment();
            
            spiralEngine = Logic.attach(await proxy.getAddress());
            proxyAddress = await proxy.getAddress();
        });

        it("Should validate UUPS proxy structure", async function () {
            console.log("🔍 Тестируем структуру UUPS proxy...");
            
            // Проверяем, что контракт является ERC1967 proxy
            const implementationAddress = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            
            expect(implementationAddress).to.not.equal(ethers.ZeroAddress);
            
            console.log("✅ Logic implementation адрес:", implementationAddress);
            
            // Проверяем, что proxy адрес корректен
            const currentProxyAddress = await spiralEngine.getAddress();
            expect(currentProxyAddress).to.equal(proxyAddress);
            
            // Проверяем UUPS-специфичные функции
            expect(await spiralEngine.LOGIC_VERSION()).to.equal(1);
            
            console.log("✅ UUPS Proxy структура валидна");
        });

        it("Should validate UUPS upgrade process", async function () {
            console.log("🔄 Тестируем процесс UUPS upgrade...");
            
            // Получаем текущий implementation
            const currentImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            console.log("📋 Текущий Logic implementation:", currentImplementation);
            
            // Выполняем UUPS upgrade
            const LogicV2 = await ethers.getContractFactory("SpiralEngineLogic");
            const logicV2 = await LogicV2.connect(deployer).deploy();
            await logicV2.waitForDeployment();
            
            await spiralEngine.connect(deployer).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"
            );
            
            // Проверяем новый implementation
            const newImplementation = await upgrades.erc1967.getImplementationAddress(proxyAddress);
            console.log("📋 Новый Logic implementation:", newImplementation);
            
            // Logic implementation должен измениться
            expect(newImplementation).to.not.equal(currentImplementation);
            expect(newImplementation).to.equal(await logicV2.getAddress());
            
            // Proxy адрес должен остаться прежним
            const proxyAddressAfter = await spiralEngine.getAddress();
            expect(proxyAddressAfter).to.equal(proxyAddress);
            
            console.log("✅ UUPS upgrade процесс валиден");
        });
        
        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            console.log("🔒 Тестируем защиту UPGRADER_ROLE...");
            
            // Создаём пользователя без UPGRADER_ROLE
            const unauthorized = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: unauthorized.address,
                value: ethers.parseEther("1.0")
            });
            
            // Деплоим новую Logic
            const LogicV2 = await ethers.getContractFactory("SpiralEngineLogic");
            const logicV2 = await LogicV2.connect(deployer).deploy();
            await logicV2.waitForDeployment();
            
            // Попытка upgrade без UPGRADER_ROLE должна провалиться
            const unauthorizedEngine = await ethers.getContractAt(
                "SpiralEngineLogic",
                proxyAddress
            );
            
            await expect(
                unauthorizedEngine.connect(unauthorized).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                )
            ).to.be.reverted;
            
            // Admin с UPGRADER_ROLE может выполнить upgrade
            await spiralEngine.connect(deployer).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"
            );
            
            console.log("✅ UPGRADER_ROLE защита работает");
        });
    });
});
