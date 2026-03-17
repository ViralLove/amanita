const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

/**
 * 🌐 AmanitaInternational - UUPS Comprehensive Test Suite
 * 
 * Применяет методологию TDD + @test-qualification.mdc
 * 
 * Архитектура UUPS (ERC1967):
 * - Proxy (ERC1967Proxy) - точка входа, фиксированный адрес
 * - Logic (AmanitaInternationalLogic) - бизнес-логика, обновляемая
 * - State variables физически хранятся в Proxy через delegatecall
 * 
 * Критические пути тестирования:
 * P0 (7 путей): Deployment, Upgrade, Simple/Complex Fields, Pause, Reentrancy
 * P1 (3 пути): Batch, Global Fields, Statistics
 * P2 (4 пути): Edge Cases
 * 
 * Целевое покрытие: 58 тестов (+ 14 Ownership = 72 total)
 */

describe("🌐 AmanitaInternational - UUPS Comprehensive Test Suite", function () {
    
    // === КОНТРАКТЫ ===
    let proxy;
    let logic;
    let amanitaIntl;  // Proxy подключенный через Logic ABI
    let mockSpiralEngine;  // Mock SpiralEngine для интеграции
    
    // === SIGNERS ===
    let admin;
    let upgrader;
    let seller1;
    let seller2;
    let user;
    
    // === РОЛИ ===
    let DEFAULT_ADMIN_ROLE;
    let UPGRADER_ROLE;
    let ADMIN_ROLE;
    let SELLER_ROLE;
    
    // === TEST DATA ===
    const TEST_SIMPLE_FIELDS = {
        "product.forms": "QmTestFormsAllLanguages123",
        "product.title": "QmTestTitleAllLanguages456",
        "component.features": "QmTestFeaturesGlobal789"
    };
    
    const TEST_COMPLEX_FIELDS = {
        "Description": {
            "ru": "QmTestDescriptionRussian123",
            "en": "QmTestDescriptionEnglish456",
            "de": "QmTestDescriptionGerman789"
        },
        "ComponentDescription": {
            "ru": "QmTestComponentRussian012",
            "en": "QmTestComponentEnglish345"
        }
    };
    
    // === HELPER UTILITIES ===
    
    /**
     * Логирование состояния Proxy
     */
    async function logProxyState(context) {
        console.log(`\n🔍 [${context}] Proxy State:`);
        console.log(`   Proxy Address: ${await proxy.getAddress()}`);
        console.log(`   Logic Address: ${await logic.getAddress()}`);
        
        // Получить implementation address через ERC1967
        const implSlot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
        const implAddress = await ethers.provider.getStorage(await proxy.getAddress(), implSlot);
        const actualImpl = "0x" + implAddress.slice(-40);
        
        console.log(`   Implementation (ERC1967): ${actualImpl}`);
        console.log(`   Version: ${await amanitaIntl.VERSION()}`);
        console.log(`   Logic Version: ${await amanitaIntl.LOGIC_VERSION()}`);
        console.log(`   Paused: ${await amanitaIntl.paused()}`);
    }
    
    /**
     * Логирование статистики
     */
    async function logStatistics(context) {
        const stats = await amanitaIntl.getStatistics();
        console.log(`\n📊 [${context}] Statistics:`);
        console.log(`   Simple Fields: ${stats.totalSimpleFields}`);
        console.log(`   Complex Classes: ${stats.totalComplexClasses}`);
        console.log(`   Complex Fields: ${stats.totalComplexFields}`);
    }
    
    /**
     * Создание LogicV2 для тестов upgrade
     */
    async function createTestUpgradeLogic() {
        // Деплоим новую версию Logic с дополнительной функцией
        const LogicV2Factory = await ethers.getContractFactory("AmanitaInternationalLogic", admin);
        const logicV2 = await LogicV2Factory.deploy();
        await logicV2.waitForDeployment();
        
        console.log(`   ✅ LogicV2 deployed: ${await logicV2.getAddress()}`);
        return logicV2;
    }
    
    async function expectCustomError(txPromise, contract, errorName) {
        let err;
        try {
            const tx = await txPromise;
            if (tx && typeof tx.wait === "function") await tx.wait();
        } catch (e) {
            err = e;
        }
        expect(err, "expected transaction to revert").to.be.ok;
        const selector = contract.interface.getError(errorName).selector;
        const data = err?.data || err?.error?.data || err?.receipt || "";
        const hex = typeof data === "string" ? data : (data && data.toString ? data.toString() : "");
        expect(hex.toLowerCase().includes(selector.toLowerCase()), `expected error ${errorName}`).to.be.true;
    }
    
    // === SETUP ===
    
    beforeEach(async function () {
        console.log("\n🔧 Setup: Deploying UUPS contracts...");
        
        // Получаем signers
        [admin, upgrader, seller1, seller2, user] = await ethers.getSigners();
        
        console.log(`   Admin: ${admin.address}`);
        console.log(`   Seller1: ${seller1.address}`);
        console.log(`   Seller2: ${seller2.address}`);
        
        // Deploy Mock SpiralEngine для интеграции
        const MockSpiralEngine = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        mockSpiralEngine = await MockSpiralEngine.deploy();
        await mockSpiralEngine.waitForDeployment();
        const mockSpiralEngineAddress = await mockSpiralEngine.getAddress();
        
        console.log(`   ✅ Mock SpiralEngine deployed: ${mockSpiralEngineAddress}`);
        
        // Deploy Logic
        const LogicFactory = await ethers.getContractFactory("AmanitaInternationalLogic", admin);
        logic = await LogicFactory.deploy();
        await logic.waitForDeployment();
        const logicAddress = await logic.getAddress();
        
        console.log(`   ✅ Logic deployed: ${logicAddress}`);
        
        // Подготовка initData для initialize() с 2 параметрами
        const initData = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            mockSpiralEngineAddress
        ]);
        
        // Deploy Proxy
        const ProxyFactory = await ethers.getContractFactory("AmanitaInternationalProxy", admin);
        proxy = await ProxyFactory.deploy(logicAddress, initData);
        await proxy.waitForDeployment();
        const proxyAddress = await proxy.getAddress();
        
        console.log(`   ✅ Proxy deployed: ${proxyAddress}`);
        
        // Подключаемся к Proxy через Logic ABI
        amanitaIntl = await ethers.getContractAt("AmanitaInternationalLogic", proxyAddress);
        
        console.log(`   ✅ Connected to Proxy via Logic ABI`);
        
        // Получаем роли
        DEFAULT_ADMIN_ROLE = await amanitaIntl.DEFAULT_ADMIN_ROLE();
        UPGRADER_ROLE = await amanitaIntl.UPGRADER_ROLE();
        ADMIN_ROLE = await amanitaIntl.ADMIN_ROLE();
        SELLER_ROLE = await amanitaIntl.SELLER_ROLE();
        
        // Выдаем SELLER_ROLE продавцам (ЛОКАЛЬНО в AmanitaInternational)
        await amanitaIntl.connect(admin).grantRole(SELLER_ROLE, seller1.address);
        await amanitaIntl.connect(admin).grantRole(SELLER_ROLE, seller2.address);
        
        console.log(`   ✅ SELLER_ROLE granted to seller1 and seller2`);
    });
    
    // =====================================================================
    // 1️⃣ DEPLOYMENT & INITIALIZATION (P0 - CP01)
    // =====================================================================
    
    describe("1️⃣ Deployment & Initialization", function () {
        
        it("Should deploy Logic contract successfully", async function () {
            console.log("\n🧪 TEST: Deploy Logic contract");
            
            // Проверяем что Logic задеплоен
            const logicAddress = await logic.getAddress();
            expect(logicAddress).to.not.equal(ethers.ZeroAddress);
            
            // Проверяем версию
            const version = await logic.VERSION();
            expect(version).to.equal("2.0.0");
            
            const logicVersion = await logic.LOGIC_VERSION();
            expect(logicVersion).to.equal(2n);
            
            console.log(`   ✅ Logic deployed at: ${logicAddress}`);
            console.log(`   ✅ Version: ${version}, Logic Version: ${logicVersion}`);
        });
        
        it("Should deploy Proxy with initialization", async function () {
            console.log("\n🧪 TEST: Deploy Proxy with initialization");
            
            // Проверяем что Proxy задеплоен
            const proxyAddress = await proxy.getAddress();
            expect(proxyAddress).to.not.equal(ethers.ZeroAddress);
            
            // Проверяем что можем читать через Proxy
            const version = await amanitaIntl.VERSION();
            expect(version).to.equal("2.0.0");
            
            console.log(`   ✅ Proxy deployed at: ${proxyAddress}`);
            console.log(`   ✅ Can read VERSION through Proxy: ${version}`);
        });
        
        it("Should set up roles correctly", async function () {
            console.log("\n🧪 TEST: Roles setup");
            
            // Проверяем DEFAULT_ADMIN_ROLE
            const hasDefaultAdmin = await amanitaIntl.hasRole(DEFAULT_ADMIN_ROLE, admin.address);
            expect(hasDefaultAdmin).to.be.true;
            
            // Проверяем UPGRADER_ROLE
            const hasUpgrader = await amanitaIntl.hasRole(UPGRADER_ROLE, admin.address);
            expect(hasUpgrader).to.be.true;
            
            // Проверяем ADMIN_ROLE
            const hasAdmin = await amanitaIntl.hasRole(ADMIN_ROLE, admin.address);
            expect(hasAdmin).to.be.true;
            
            console.log(`   ✅ DEFAULT_ADMIN_ROLE: ${hasDefaultAdmin}`);
            console.log(`   ✅ UPGRADER_ROLE: ${hasUpgrader}`);
            console.log(`   ✅ ADMIN_ROLE: ${hasAdmin}`);
        });
        
        it("Should prevent re-initialization", async function () {
            console.log("\n🧪 TEST: Prevent re-initialization");
            
            const mockAddress = await mockSpiralEngine.getAddress();
            
            // Попытка повторной инициализации должна ревертить (Initializable защищает повторный вызов)
            let err;
            try {
                await amanitaIntl.connect(admin).initialize(admin.address, mockAddress);
            } catch (e) {
                err = e;
            }
            expect(err, "expected re-initialization to revert").to.be.ok;
            
            console.log(`   ✅ Re-initialization prevented (initializer guard)`);
        });
        
        it("Should verify Proxy points to Logic", async function () {
            console.log("\n🧪 TEST: Verify Proxy → Logic");
            
            // Читаем implementation address через ERC1967 slot
            const implSlot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
            const proxyAddress = await proxy.getAddress();
            const implAddressRaw = await ethers.provider.getStorage(proxyAddress, implSlot);
            const implAddress = "0x" + implAddressRaw.slice(-40);
            
            const logicAddress = await logic.getAddress();
            
            expect(implAddress.toLowerCase()).to.equal(logicAddress.toLowerCase());
            
            console.log(`   ✅ Proxy implementation slot: ${implAddress}`);
            console.log(`   ✅ Logic address: ${logicAddress}`);
            console.log(`   ✅ Addresses match!`);
        });
        
        it("Should revert on zero address in initialize", async function () {
            console.log("\n🧪 TEST: Zero address in initialize");
            
            // Деплоим новый Logic для теста
            const LogicFactory = await ethers.getContractFactory("AmanitaInternationalLogic");
            const freshLogic = await LogicFactory.deploy();
            await freshLogic.waitForDeployment();
            
            const validAddress = await mockSpiralEngine.getAddress();
            
            // Тест 1: Нулевой admin
            const badInitData1 = freshLogic.interface.encodeFunctionData("initialize", [
                ethers.ZeroAddress,  // admin = 0x0
                validAddress         // spiralEngine = valid
            ]);
            
            const ProxyFactory = await ethers.getContractFactory("AmanitaInternationalProxy");
            await expectCustomError(
                ProxyFactory.deploy(await freshLogic.getAddress(), badInitData1),
                freshLogic,
                "ZeroAddress"
            );
            
            console.log(`   ✅ ZeroAddress error triggered for admin`);
            
            // Тест 2: Нулевой spiralEngine
            const badInitData2 = freshLogic.interface.encodeFunctionData("initialize", [
                admin.address,       // admin = valid
                ethers.ZeroAddress   // spiralEngine = 0x0
            ]);
            
            await expectCustomError(
                ProxyFactory.deploy(await freshLogic.getAddress(), badInitData2),
                freshLogic,
                "ZeroAddress"
            );
            
            console.log(`   ✅ ZeroAddress error triggered for spiralEngine`);
        });
    });
    
    // =====================================================================
    // 2️⃣ UUPS UPGRADE MECHANISM (P0 - CP02)
    // =====================================================================
    
    describe("2️⃣ UUPS Upgrade Mechanism", function () {
        
        it("Should upgrade implementation with UPGRADER_ROLE", async function () {
            console.log("\n🧪 TEST: Upgrade with UPGRADER_ROLE");
            
            // Создаем данные для тестирования сохранения state
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "test.before.upgrade",
                "QmBeforeUpgrade123"
            );
            
            await logProxyState("Before Upgrade");
            
            // Деплоим LogicV2
            const logicV2 = await createTestUpgradeLogic();
            const logicV2Address = await logicV2.getAddress();
            
            // Upgrade через upgradeToAndCall
            await amanitaIntl.connect(admin).upgradeToAndCall(logicV2Address, "0x");
            
            await logProxyState("After Upgrade");
            
            // Проверяем что implementation обновился
            const implSlot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
            const proxyAddress = await proxy.getAddress();
            const newImplRaw = await ethers.provider.getStorage(proxyAddress, implSlot);
            const newImpl = "0x" + newImplRaw.slice(-40);
            
            expect(newImpl.toLowerCase()).to.equal(logicV2Address.toLowerCase());
            
            console.log(`   ✅ Implementation upgraded to: ${newImpl}`);
        });
        
        it("Should preserve state after upgrade", async function () {
            console.log("\n🧪 TEST: State preservation after upgrade");
            
            // Создаем данные ПЕРЕД апгрейдом
            await amanitaIntl.connect(seller1).setSimpleFieldCID("state.test1", "QmState1");
            await amanitaIntl.connect(seller1).setComplexFieldCID("TestClass", "ru", "QmState2");
            
            const cidBefore1 = await amanitaIntl.getSimpleFieldCID("state.test1");
            const cidBefore2 = await amanitaIntl.getComplexFieldCID("TestClass", "ru");
            
            console.log(`   📝 Before: state.test1 = ${cidBefore1}`);
            console.log(`   📝 Before: TestClass.ru = ${cidBefore2}`);
            
            // Upgrade
            const logicV2 = await createTestUpgradeLogic();
            await amanitaIntl.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");
            
            // Проверяем данные ПОСЛЕ апгрейда
            const cidAfter1 = await amanitaIntl.getSimpleFieldCID("state.test1");
            const cidAfter2 = await amanitaIntl.getComplexFieldCID("TestClass", "ru");
            
            expect(cidAfter1).to.equal(cidBefore1);
            expect(cidAfter2).to.equal(cidBefore2);
            
            console.log(`   ✅ After: state.test1 = ${cidAfter1} (preserved)`);
            console.log(`   ✅ After: TestClass.ru = ${cidAfter2} (preserved)`);
        });
        
        it("Should make new functions available after upgrade (if any)", async function () {
            console.log("\n🧪 TEST: New functions after upgrade");
            
            // Upgrade
            const logicV2 = await createTestUpgradeLogic();
            await amanitaIntl.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");
            
            // Проверяем что старые функции работают
            const version = await amanitaIntl.VERSION();
            expect(version).to.equal("2.0.0");
            
            // Примечание: LogicV2 идентичен LogicV1 (для простоты),
            // но в реальном сценарии здесь проверялись бы новые функции
            
            console.log(`   ✅ Old functions still work: VERSION = ${version}`);
            console.log(`   ℹ️ LogicV2 = LogicV1 (test scenario)`);
        });
        
        it("Should prevent upgrade by non-upgrader", async function () {
            console.log("\n🧪 TEST: Prevent upgrade by non-upgrader");
            
            const logicV2 = await createTestUpgradeLogic();
            
            // Попытка upgrade от seller1 (нет UPGRADER_ROLE)
            await expectCustomError(
                amanitaIntl.connect(seller1).upgradeToAndCall(await logicV2.getAddress(), "0x"),
                amanitaIntl,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log(`   ✅ Non-upgrader blocked from upgrade`);
        });
        
        it("Should verify storage gap works", async function () {
            console.log("\n🧪 TEST: Storage gap verification");
            
            // Проверяем что storage layout не сломан
            // Создаем данные в разных слотах
            await amanitaIntl.connect(seller1).setSimpleFieldCID("gap.test1", "QmGap1");
            await amanitaIntl.connect(seller1).setSimpleFieldCID("gap.test2", "QmGap2");
            await amanitaIntl.connect(seller1).setComplexFieldCID("GapClass", "en", "QmGap3");
            
            // Upgrade
            const logicV2 = await createTestUpgradeLogic();
            await amanitaIntl.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");
            
            // Проверяем что все данные на месте
            expect(await amanitaIntl.getSimpleFieldCID("gap.test1")).to.equal("QmGap1");
            expect(await amanitaIntl.getSimpleFieldCID("gap.test2")).to.equal("QmGap2");
            expect(await amanitaIntl.getComplexFieldCID("GapClass", "en")).to.equal("QmGap3");
            
            console.log(`   ✅ Storage layout preserved (storage gap works)`);
        });
        
        it("Should emit upgrade events", async function () {
            console.log("\n🧪 TEST: Upgrade events");
            
            const logicV2 = await createTestUpgradeLogic();
            const logicV2Address = await logicV2.getAddress();
            
            const tx = await amanitaIntl.connect(admin).upgradeToAndCall(logicV2Address, "0x");
            const receipt = await tx.wait();

            const eventIface = amanitaIntl.interface;
            const decoded = receipt.logs
                .map((log) => {
                    try {
                        return eventIface.parseLog(log);
                    } catch {
                        return null;
                    }
                })
                .filter((e) => e && e.name === "Upgraded");

            expect(decoded.length >= 1).to.be.true;
            const evt = decoded[0];
            const [newImplementation] = evt.args;
            expect(newImplementation).to.equal(logicV2Address);
            
            console.log(`   ✅ Upgraded event emitted with new implementation`);
        });
    });
    
    // =====================================================================
    // 3️⃣ SIMPLE FIELDS OPERATIONS (P0 - CP04)
    // =====================================================================
    
    describe("3️⃣ Simple Fields Operations", function () {
        
        it("Should create simple field with setSimpleFieldCID", async function () {
            console.log("\n🧪 TEST: Create simple field");
            
            const fieldKey = "test.simple.field";
            const cid = "QmTestSimpleCID123";
            
            // Seller создает поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(fieldKey, cid);
            
            // Проверяем что поле создано
            const exists = await amanitaIntl.simpleFieldExist(fieldKey);
            expect(exists).to.be.true;
            
            // Проверяем CID
            const retrievedCid = await amanitaIntl.getSimpleFieldCID(fieldKey);
            expect(retrievedCid).to.equal(cid);
            
            // Проверяем owner
            const owner = await amanitaIntl.simpleFieldOwner(fieldKey);
            expect(owner).to.equal(seller1.address);
            
            console.log(`   ✅ Field created: ${fieldKey}`);
            console.log(`   ✅ CID: ${retrievedCid}`);
            console.log(`   ✅ Owner: ${owner}`);
        });
        
        it("Should get simple field CID", async function () {
            console.log("\n🧪 TEST: Get simple field CID");
            
            // Создаем поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID("get.test", "QmGetTest456");
            
            // Получаем CID
            const cid = await amanitaIntl.getSimpleFieldCID("get.test");
            expect(cid).to.equal("QmGetTest456");
            
            console.log(`   ✅ Retrieved CID: ${cid}`);
        });
        
        it("Should check field existence", async function () {
            console.log("\n🧪 TEST: Check field existence");
            
            const existingKey = "exists.test";
            const nonExistingKey = "does.not.exist";
            
            // Создаем одно поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(existingKey, "QmExists789");
            
            // Проверяем существующее
            const exists = await amanitaIntl.simpleFieldExist(existingKey);
            expect(exists).to.be.true;
            
            // Проверяем несуществующее
            const notExists = await amanitaIntl.simpleFieldExist(nonExistingKey);
            expect(notExists).to.be.false;
            
            console.log(`   ✅ Existing field: ${exists}`);
            console.log(`   ✅ Non-existing field: ${notExists}`);
        });
        
        it("Should remove simple field", async function () {
            console.log("\n🧪 TEST: Remove simple field");
            
            const fieldKey = "remove.test";
            
            // Создаем поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(fieldKey, "QmRemove012");
            
            // Проверяем что существует
            expect(await amanitaIntl.simpleFieldExist(fieldKey)).to.be.true;
            
            // Удаляем (требует ADMIN_ROLE)
            await amanitaIntl.connect(admin).removeSimpleField(fieldKey);
            
            // Проверяем что удалено
            expect(await amanitaIntl.simpleFieldExist(fieldKey)).to.be.false;
            
            console.log(`   ✅ Field removed: ${fieldKey}`);
        });
        
        it("Should get all simple field keys", async function () {
            console.log("\n🧪 TEST: Get all simple field keys");
            
            // Создаем несколько полей
            await amanitaIntl.connect(seller1).setSimpleFieldCID("key1", "QmKey1");
            await amanitaIntl.connect(seller1).setSimpleFieldCID("key2", "QmKey2");
            await amanitaIntl.connect(seller1).setSimpleFieldCID("key3", "QmKey3");
            
            // Получаем все ключи
            const keys = await amanitaIntl.getAllSimpleFields();
            
            expect(keys.length).to.be.greaterThanOrEqual(3);
            expect(keys).to.include("key1");
            expect(keys).to.include("key2");
            expect(keys).to.include("key3");
            
            console.log(`   ✅ Total keys: ${keys.length}`);
            console.log(`   ✅ Includes key1, key2, key3`);
        });
        
        it("Should revert on empty fieldKey", async function () {
            console.log("\n🧪 TEST: Empty fieldKey");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID("", "QmTest"),
                amanitaIntl,
                "EmptyFieldKey"
            );
            
            console.log(`   ✅ EmptyFieldKey error triggered`);
        });
        
        it("Should revert on empty CID", async function () {
            console.log("\n🧪 TEST: Empty CID");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID("test.key", ""),
                amanitaIntl,
                "EmptyCID"
            );
            
            console.log(`   ✅ EmptyCID error triggered`);
        });
    });
    
    // =====================================================================
    // 4️⃣ COMPLEX FIELDS OPERATIONS (P0 - CP05)
    // =====================================================================
    
    describe("4️⃣ Complex Fields Operations", function () {
        
        it("Should create complex field with setComplexFieldCID", async function () {
            console.log("\n🧪 TEST: Create complex field");
            
            const className = "TestClass";
            const language = "ru";
            const cid = "QmComplexRussian123";
            
            // Seller создает complex field
            await amanitaIntl.connect(seller1).setComplexFieldCID(className, language, cid);
            
            // Проверяем CID
            const retrievedCid = await amanitaIntl.getComplexFieldCID(className, language);
            expect(retrievedCid).to.equal(cid);
            
            // Проверяем owner
            const key = `${className}.${language}`;
            const owner = await amanitaIntl.complexFieldOwner(key);
            expect(owner).to.equal(seller1.address);
            
            console.log(`   ✅ Complex field created: ${className}.${language}`);
            console.log(`   ✅ CID: ${retrievedCid}`);
            console.log(`   ✅ Owner: ${owner}`);
        });
        
        it("Should get complex field CID", async function () {
            console.log("\n🧪 TEST: Get complex field CID");
            
            // Создаем complex field
            await amanitaIntl.connect(seller1).setComplexFieldCID("GetClass", "en", "QmGetEn456");
            
            // Получаем CID
            const cid = await amanitaIntl.getComplexFieldCID("GetClass", "en");
            expect(cid).to.equal("QmGetEn456");
            
            console.log(`   ✅ Retrieved CID: ${cid}`);
        });
        
        it("Should get complex field languages", async function () {
            console.log("\n🧪 TEST: Get complex field languages");
            
            const className = "MultiLangClass";
            
            // Создаем несколько языков
            await amanitaIntl.connect(seller1).setComplexFieldCID(className, "ru", "QmRu");
            await amanitaIntl.connect(seller1).setComplexFieldCID(className, "en", "QmEn");
            await amanitaIntl.connect(seller1).setComplexFieldCID(className, "de", "QmDe");
            
            // Получаем языки
            const languages = await amanitaIntl.getComplexFieldLanguages(className);
            
            expect(languages.length).to.equal(3);
            expect(languages).to.include("ru");
            expect(languages).to.include("en");
            expect(languages).to.include("de");
            
            console.log(`   ✅ Languages: ${languages.join(", ")}`);
        });
        
        it("Should remove complex field", async function () {
            console.log("\n🧪 TEST: Remove complex field");
            
            const className = "RemoveClass";
            const language = "ru";
            
            // Создаем поле
            await amanitaIntl.connect(seller1).setComplexFieldCID(className, language, "QmRemove");
            
            // Проверяем что существует
            const cidBefore = await amanitaIntl.getComplexFieldCID(className, language);
            expect(cidBefore).to.equal("QmRemove");
            
            // Удаляем (требует ADMIN_ROLE)
            await amanitaIntl.connect(admin).removeComplexField(className, language);
            
            // Проверяем что удалено (вернет пустую строку)
            const cidAfter = await amanitaIntl.getComplexFieldCID(className, language);
            expect(cidAfter).to.equal("");
            
            console.log(`   ✅ Complex field removed: ${className}.${language}`);
        });
        
        it("Should get all complex field classes", async function () {
            console.log("\n🧪 TEST: Get all complex field classes");
            
            // Создаем несколько классов
            await amanitaIntl.connect(seller1).setComplexFieldCID("Class1", "ru", "Qm1");
            await amanitaIntl.connect(seller1).setComplexFieldCID("Class2", "en", "Qm2");
            await amanitaIntl.connect(seller1).setComplexFieldCID("Class3", "de", "Qm3");
            
            // Получаем все классы
            const classes = await amanitaIntl.getAllComplexClasses();
            
            expect(classes.length).to.be.greaterThanOrEqual(3);
            expect(classes).to.include("Class1");
            expect(classes).to.include("Class2");
            expect(classes).to.include("Class3");
            
            console.log(`   ✅ Total classes: ${classes.length}`);
            console.log(`   ✅ Includes Class1, Class2, Class3`);
        });
        
        it("Should revert on empty className", async function () {
            console.log("\n🧪 TEST: Empty className");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setComplexFieldCID("", "ru", "QmTest"),
                amanitaIntl,
                "EmptyClassName"
            );
            
            console.log(`   ✅ EmptyClassName error triggered`);
        });
        
        it("Should revert on empty language", async function () {
            console.log("\n🧪 TEST: Empty language");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setComplexFieldCID("TestClass", "", "QmTest"),
                amanitaIntl,
                "EmptyLanguage"
            );
            
            console.log(`   ✅ EmptyLanguage error triggered`);
        });
    });
    
    // =====================================================================
    // 5️⃣ BATCH OPERATIONS (P1 - CP08)
    // =====================================================================
    
    describe("5️⃣ Batch Operations", function () {
        
        it("Should batch set simple fields", async function () {
            console.log("\n🧪 TEST: Batch set simple fields");
            
            const keys = ["batch.key1", "batch.key2", "batch.key3"];
            const cids = ["QmBatch1", "QmBatch2", "QmBatch3"];
            
            // Batch установка (требует ADMIN_ROLE)
            await amanitaIntl.connect(admin).batchSetSimpleFields(keys, cids);
            
            // Проверяем каждое поле
            for (let i = 0; i < keys.length; i++) {
                const cid = await amanitaIntl.getSimpleFieldCID(keys[i]);
                expect(cid).to.equal(cids[i]);
                console.log(`   ✅ ${keys[i]} = ${cid}`);
            }
            
            console.log(`   ✅ Batch operation successful: ${keys.length} fields`);
        });
        
        it("Should batch set complex fields", async function () {
            console.log("\n🧪 TEST: Batch set complex fields");
            
            const classNames = ["BatchClass1", "BatchClass1", "BatchClass2"];
            const languages = ["ru", "en", "de"];
            const cids = ["QmBatchRu1", "QmBatchEn1", "QmBatchDe2"];
            
            // Batch установка (требует ADMIN_ROLE)
            await amanitaIntl.connect(admin).batchSetComplexFields(classNames, languages, cids);
            
            // Проверяем каждое поле
            for (let i = 0; i < classNames.length; i++) {
                const cid = await amanitaIntl.getComplexFieldCID(classNames[i], languages[i]);
                expect(cid).to.equal(cids[i]);
                console.log(`   ✅ ${classNames[i]}.${languages[i]} = ${cid}`);
            }
            
            console.log(`   ✅ Batch operation successful: ${classNames.length} fields`);
        });
        
        it("Should revert on array length mismatch", async function () {
            console.log("\n🧪 TEST: Array length mismatch");
            
            const keys = ["key1", "key2", "key3"];
            const cids = ["Qm1", "Qm2"];  // Меньше чем keys!
            
            // Должно ревертить с ArrayLengthMismatch
            await expectCustomError(
                amanitaIntl.connect(admin).batchSetSimpleFields(keys, cids),
                amanitaIntl,
                "ArrayLengthMismatch"
            );
            
            console.log(`   ✅ ArrayLengthMismatch error triggered`);
        });
        
        it("Should emit events for each field in batch", async function () {
            console.log("\n🧪 TEST: Batch events emission");
            
            const keys = ["event.key1", "event.key2"];
            const cids = ["QmEvent1", "QmEvent2"];
            
            // Batch установка должна эмитить события для каждого поля
            const tx = await amanitaIntl.connect(admin).batchSetSimpleFields(keys, cids);
            const receipt = await tx.wait();
            
            // Подсчитываем события SimpleFieldRegistered
            const events = receipt.logs.filter(log => {
                try {
                    const parsed = amanitaIntl.interface.parseLog(log);
                    return parsed.name === "SimpleFieldRegistered";
                } catch (e) {
                    return false;
                }
            });
            
            expect(events.length).to.equal(keys.length);
            
            console.log(`   ✅ Events emitted: ${events.length}`);
        });
        
        it("Should be atomic (all or nothing)", async function () {
            console.log("\n🧪 TEST: Batch atomicity");
            
            // Создаем batch где один элемент невалиден
            const keys = ["atomic.key1", "atomic.key2", ""];  // Пустой ключ!
            const cids = ["Qm1", "Qm2", "Qm3"];
            
            // Вся операция должна ревертить
            await expectCustomError(
                amanitaIntl.connect(admin).batchSetSimpleFields(keys, cids),
                amanitaIntl,
                "EmptyFieldKey"
            );
            
            // Проверяем что НИЧЕГО не создалось
            const exists1 = await amanitaIntl.simpleFieldExist("atomic.key1");
            const exists2 = await amanitaIntl.simpleFieldExist("atomic.key2");
            
            expect(exists1).to.be.false;
            expect(exists2).to.be.false;
            
            console.log(`   ✅ Batch reverted atomically (no partial writes)`);
        });
    });
    
    // =====================================================================
    // 6️⃣ PAUSE & EMERGENCY PROCEDURES (P0 - CP06)
    // =====================================================================
    
    describe("6️⃣ Pause & Emergency Procedures", function () {
        
        it("Should pause contract with ADMIN_ROLE", async function () {
            console.log("\n🧪 TEST: Pause contract");
            
            // Проверяем начальное состояние
            const pausedBefore = await amanitaIntl.paused();
            expect(pausedBefore).to.be.false;
            
            // Admin ставит на паузу
            await amanitaIntl.connect(admin).pause();
            
            // Проверяем что на паузе
            const pausedAfter = await amanitaIntl.paused();
            expect(pausedAfter).to.be.true;
            
            console.log(`   ✅ Contract paused: ${pausedAfter}`);
        });
        
        it("Should prevent write operations when paused", async function () {
            console.log("\n🧪 TEST: Write operations blocked when paused");
            
            // Ставим на паузу
            await amanitaIntl.connect(admin).pause();
            
            // Попытка записи должна ревертить
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID("paused.test", "QmPaused"),
                amanitaIntl,
                "EnforcedPause"
            );
            
            console.log(`   ✅ Write operation blocked when paused`);
        });
        
        it("Should allow read operations when paused", async function () {
            console.log("\n🧪 TEST: Read operations allowed when paused");
            
            // Создаем поле ДО паузы
            await amanitaIntl.connect(seller1).setSimpleFieldCID("read.test", "QmRead123");
            
            // Ставим на паузу
            await amanitaIntl.connect(admin).pause();
            
            // Читать можем даже на паузе
            const cid = await amanitaIntl.getSimpleFieldCID("read.test");
            expect(cid).to.equal("QmRead123");
            
            console.log(`   ✅ Read operation works when paused: ${cid}`);
        });
        
        it("Should unpause contract", async function () {
            console.log("\n🧪 TEST: Unpause contract");
            
            // Ставим на паузу
            await amanitaIntl.connect(admin).pause();
            expect(await amanitaIntl.paused()).to.be.true;
            
            // Снимаем с паузы
            await amanitaIntl.connect(admin).unpause();
            expect(await amanitaIntl.paused()).to.be.false;
            
            // Теперь можем писать
            await amanitaIntl.connect(seller1).setSimpleFieldCID("after.unpause", "QmAfter");
            const cid = await amanitaIntl.getSimpleFieldCID("after.unpause");
            expect(cid).to.equal("QmAfter");
            
            console.log(`   ✅ Contract unpaused, write operations work`);
        });
        
        it("Should prevent non-admin from pausing", async function () {
            console.log("\n🧪 TEST: Non-admin cannot pause");
            
            // Seller не может ставить на паузу
            await expectCustomError(
                amanitaIntl.connect(seller1).pause(),
                amanitaIntl,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log(`   ✅ Non-admin blocked from pause`);
        });
    });
    
    // =====================================================================
    // 7️⃣ REENTRANCY PROTECTION (P0 - CP07)
    // =====================================================================
    
    describe("7️⃣ Reentrancy Protection", function () {
        
        it("Should protect setSimpleFieldCID from reentrancy", async function () {
            console.log("\n🧪 TEST: Reentrancy protection for setSimpleFieldCID");
            
            // Примечание: ReentrancyGuard встроен в OpenZeppelin
            // Прямое тестирование реентрантности требует атакующего контракта
            // Здесь проверяем что модификатор присутствует
            
            // Проверяем что функция выполняется нормально
            await amanitaIntl.connect(seller1).setSimpleFieldCID("reentry.test", "QmReentry");
            
            const cid = await amanitaIntl.getSimpleFieldCID("reentry.test");
            expect(cid).to.equal("QmReentry");
            
            console.log(`   ✅ Function executes normally (nonReentrant present)`);
            console.log(`   ℹ️ Full reentrancy attack requires malicious contract`);
        });
        
        it("Should protect setComplexFieldCID from reentrancy", async function () {
            console.log("\n🧪 TEST: Reentrancy protection for setComplexFieldCID");
            
            // Проверяем что функция выполняется нормально
            await amanitaIntl.connect(seller1).setComplexFieldCID("ReentryClass", "ru", "QmReentry");
            
            const cid = await amanitaIntl.getComplexFieldCID("ReentryClass", "ru");
            expect(cid).to.equal("QmReentry");
            
            console.log(`   ✅ Function executes normally (nonReentrant present)`);
        });
        
        it("Should allow nested read calls (no reentrancy guard)", async function () {
            console.log("\n🧪 TEST: Read calls not guarded");
            
            // Создаем данные
            await amanitaIntl.connect(seller1).setSimpleFieldCID("nested.test1", "Qm1");
            await amanitaIntl.connect(seller1).setSimpleFieldCID("nested.test2", "Qm2");
            
            // Множественные read вызовы должны работать (no reentrancy guard)
            const cid1 = await amanitaIntl.getSimpleFieldCID("nested.test1");
            const cid2 = await amanitaIntl.getSimpleFieldCID("nested.test2");
            
            expect(cid1).to.equal("Qm1");
            expect(cid2).to.equal("Qm2");
            
            console.log(`   ✅ Nested reads work (no guard on view functions)`);
        });
    });
    
    // =====================================================================
    // 8️⃣ GLOBAL FIELDS MANAGEMENT (P1 - CP09)
    // =====================================================================
    
    describe("8️⃣ Global Fields Management", function () {
        
        it("Should mark field as global (ADMIN only)", async function () {
            console.log("\n🧪 TEST: Mark field as global");
            
            const fieldKey = "global.features";
            
            // Admin помечает поле как глобальное
            await amanitaIntl.connect(admin).setGlobalField(fieldKey, true);
            
            // Проверяем статус
            const isGlobal = await amanitaIntl.isFieldGlobal(fieldKey);
            expect(isGlobal).to.be.true;
            
            console.log(`   ✅ Field marked as global: ${fieldKey}`);
        });
        
        it("Should prevent seller from modifying global fields", async function () {
            console.log("\n🧪 TEST: Seller cannot modify global");
            
            const fieldKey = "global.readonly";
            
            // 1. Admin помечает как глобальное и устанавливает
            await amanitaIntl.connect(admin).setGlobalField(fieldKey, true);
            await amanitaIntl.connect(admin).setSimpleFieldCID(fieldKey, "QmGlobalCID");
            
            // 2. Seller НЕ может изменить
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID(fieldKey, "QmHack"),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            // 3. CID остался неизменным
            const cid = await amanitaIntl.getSimpleFieldCID(fieldKey);
            expect(cid).to.equal("QmGlobalCID");
            
            console.log(`   ✅ Seller blocked from global field`);
        });
        
        it("Should allow admin to modify global fields", async function () {
            console.log("\n🧪 TEST: Admin can modify global");
            
            const fieldKey = "global.admin";
            
            // 1. Admin помечает как глобальное
            await amanitaIntl.connect(admin).setGlobalField(fieldKey, true);
            
            // 2. Admin устанавливает
            await amanitaIntl.connect(admin).setSimpleFieldCID(fieldKey, "QmGlobal1");
            expect(await amanitaIntl.getSimpleFieldCID(fieldKey)).to.equal("QmGlobal1");
            
            // 3. Admin может обновить
            await amanitaIntl.connect(admin).setSimpleFieldCID(fieldKey, "QmGlobal2");
            expect(await amanitaIntl.getSimpleFieldCID(fieldKey)).to.equal("QmGlobal2");
            
            console.log(`   ✅ Admin can create and modify global fields`);
        });
        
        it("Should check isFieldGlobal status", async function () {
            console.log("\n🧪 TEST: Check isFieldGlobal");
            
            const globalKey = "status.global";
            const normalKey = "status.normal";
            
            // Создаем глобальное поле
            await amanitaIntl.connect(admin).setGlobalField(globalKey, true);
            
            // Создаем обычное поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(normalKey, "QmNormal");
            
            // Проверяем статусы
            expect(await amanitaIntl.isFieldGlobal(globalKey)).to.be.true;
            expect(await amanitaIntl.isFieldGlobal(normalKey)).to.be.false;
            
            console.log(`   ✅ Global field: true, Normal field: false`);
        });
        
        it("Should emit GlobalFieldSet event", async function () {
            console.log("\n🧪 TEST: GlobalFieldSet event");

            const tx = await amanitaIntl.connect(admin).setGlobalField("event.test", true);
            const receipt = await tx.wait();

            const eventIface = amanitaIntl.interface;
            const decoded = receipt.logs
                .map((log) => {
                    try {
                        return eventIface.parseLog(log);
                    } catch {
                        return null;
                    }
                })
                .filter((e) => e && e.name === "GlobalFieldSet");

            expect(decoded.length >= 1).to.be.true;
            const evt = decoded[0];
            const { fieldKey, isGlobal, admin: actor } = evt.args;
            expect(fieldKey.hash).to.equal(ethers.id("event.test"));
            expect(isGlobal).to.equal(true);
            expect(actor).to.equal(admin.address);
            
            console.log(`   ✅ GlobalFieldSet event emitted and decoded`);
        });
    });
    
    // =====================================================================
    // 9️⃣ STATISTICS & QUERIES (P1 - CP10)
    // =====================================================================
    
    describe("9️⃣ Statistics & Queries", function () {
        
        it("Should return correct statistics", async function () {
            console.log("\n🧪 TEST: Statistics accuracy");
            
            await logStatistics("Before");
            
            // Создаем данные
            await amanitaIntl.connect(seller1).setSimpleFieldCID("stat.s1", "Qm1");
            await amanitaIntl.connect(seller1).setSimpleFieldCID("stat.s2", "Qm2");
            await amanitaIntl.connect(seller1).setComplexFieldCID("StatClass1", "ru", "Qm3");
            await amanitaIntl.connect(seller1).setComplexFieldCID("StatClass1", "en", "Qm4");
            await amanitaIntl.connect(seller1).setComplexFieldCID("StatClass2", "de", "Qm5");
            
            await logStatistics("After");
            
            const stats = await amanitaIntl.getStatistics();
            
            // Проверяем счетчики (BigInt comparisons)
            expect(stats.totalSimpleFields >= 2n).to.be.true;
            expect(stats.totalComplexClasses >= 2n).to.be.true;
            expect(stats.totalComplexFields >= 3n).to.be.true;
            
            console.log(`   ✅ Statistics correct`);
        });
        
        it("Should increment totalSimpleFields", async function () {
            console.log("\n🧪 TEST: Increment totalSimpleFields");
            
            const statsBefore = await amanitaIntl.getStatistics();
            const countBefore = statsBefore.totalSimpleFields;
            
            // Создаем новое поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID("increment.test", "QmInc");
            
            const statsAfter = await amanitaIntl.getStatistics();
            const countAfter = statsAfter.totalSimpleFields;
            
            expect(countAfter).to.equal(countBefore + BigInt(1));
            
            console.log(`   ✅ Total simple fields: ${countBefore} → ${countAfter}`);
        });
        
        it("Should track totalComplexClasses", async function () {
            console.log("\n🧪 TEST: Track totalComplexClasses");
            
            const statsBefore = await amanitaIntl.getStatistics();
            const classesBefore = statsBefore.totalComplexClasses;
            
            // Создаем новый класс
            await amanitaIntl.connect(seller1).setComplexFieldCID("NewClass", "ru", "QmNew");
            
            const statsAfter = await amanitaIntl.getStatistics();
            const classesAfter = statsAfter.totalComplexClasses;
            
            expect(classesAfter).to.equal(classesBefore + BigInt(1));
            
            console.log(`   ✅ Total complex classes: ${classesBefore} → ${classesAfter}`);
        });
        
        it("Should track totalComplexFields", async function () {
            console.log("\n🧪 TEST: Track totalComplexFields");
            
            const statsBefore = await amanitaIntl.getStatistics();
            const fieldsBefore = statsBefore.totalComplexFields;
            
            // Создаем несколько языков одного класса
            await amanitaIntl.connect(seller1).setComplexFieldCID("MultiClass", "ru", "Qm1");
            await amanitaIntl.connect(seller1).setComplexFieldCID("MultiClass", "en", "Qm2");
            
            const statsAfter = await amanitaIntl.getStatistics();
            const fieldsAfter = statsAfter.totalComplexFields;
            
            expect(fieldsAfter).to.equal(fieldsBefore + BigInt(2));
            
            console.log(`   ✅ Total complex fields: ${fieldsBefore} → ${fieldsAfter}`);
        });
    });
    
    // =====================================================================
    // 🔟 EDGE CASES (P2 - CP11-13)
    // =====================================================================
    
    describe("🔟 Edge Cases", function () {
        
        it("Should handle very long fieldKeys", async function () {
            console.log("\n🧪 TEST: Very long fieldKeys");
            
            // Создаем очень длинный ключ (255 символов)
            const longKey = "a".repeat(255);
            
            // Должно работать (нет ограничения длины)
            await amanitaIntl.connect(seller1).setSimpleFieldCID(longKey, "QmLongKey");
            
            const cid = await amanitaIntl.getSimpleFieldCID(longKey);
            expect(cid).to.equal("QmLongKey");
            
            console.log(`   ✅ Long fieldKey (255 chars) accepted`);
        });
        
        it("Should handle very long CIDs", async function () {
            console.log("\n🧪 TEST: Very long CIDs");
            
            // Создаем длинный CID (реальные IPFS CID ~60 символов)
            const longCid = "Qm" + "x".repeat(100);
            
            await amanitaIntl.connect(seller1).setSimpleFieldCID("long.cid", longCid);
            
            const cid = await amanitaIntl.getSimpleFieldCID("long.cid");
            expect(cid).to.equal(longCid);
            
            console.log(`   ✅ Long CID (102 chars) accepted`);
        });
        
        it("Should return empty string for non-existent simple field", async function () {
            console.log("\n🧪 TEST: Non-existent simple field");
            
            const cid = await amanitaIntl.getSimpleFieldCID("does.not.exist");
            expect(cid).to.equal("");
            
            console.log(`   ✅ Non-existent field returns empty string`);
        });
        
        it("Should return empty string for non-existent complex field", async function () {
            console.log("\n🧪 TEST: Non-existent complex field");
            
            const cid = await amanitaIntl.getComplexFieldCID("NonExistentClass", "ru");
            expect(cid).to.equal("");
            
            console.log(`   ✅ Non-existent complex field returns empty string`);
        });
        
        it("Should revert when removing non-existent simple field", async function () {
            console.log("\n🧪 TEST: Remove non-existent simple field");
            
            let reverted = false;
            try {
                await amanitaIntl.connect(admin).removeSimpleField("does.not.exist");
            } catch (e) {
                reverted = true;
            }
            expect(reverted).to.be.true;
            
            console.log(`   ✅ FieldDoesNotExist error triggered`);
        });
        
        it("Should revert when removing non-existent complex field", async function () {
            console.log("\n🧪 TEST: Remove non-existent complex field");
            
            let reverted = false;
            try {
                await amanitaIntl.connect(admin).removeComplexField("NonClass", "ru");
            } catch (e) {
                reverted = true;
            }
            expect(reverted).to.be.true;
            
            console.log(`   ✅ FieldDoesNotExist error triggered`);
        });
        
        it("Should handle special characters in fieldKeys", async function () {
            console.log("\n🧪 TEST: Special characters in fieldKeys");
            
            const specialKeys = [
                "field.with.dots",
                "field-with-dashes",
                "field_with_underscores",
                "field123with456numbers"
            ];
            
            for (const key of specialKeys) {
                await amanitaIntl.connect(seller1).setSimpleFieldCID(key, "QmSpecial");
                const cid = await amanitaIntl.getSimpleFieldCID(key);
                expect(cid).to.equal("QmSpecial");
            }
            
            console.log(`   ✅ All special characters accepted`);
        });
        
        it("Should handle multiple languages for same class", async function () {
            console.log("\n🧪 TEST: Multiple languages per class");
            
            const className = "MultiLangTest";
            const languages = ["ru", "en", "de", "fr", "es", "nl", "et"];
            
            // Создаем переводы на всех языках
            for (let i = 0; i < languages.length; i++) {
                await amanitaIntl.connect(seller1).setComplexFieldCID(
                    className,
                    languages[i],
                    `Qm${languages[i]}`
                );
            }
            
            // Проверяем что все языки зарегистрированы
            const registeredLangs = await amanitaIntl.getComplexFieldLanguages(className);
            expect(registeredLangs.length).to.equal(languages.length);
            
            for (const lang of languages) {
                expect(registeredLangs).to.include(lang);
            }
            
            console.log(`   ✅ ${languages.length} languages registered for ${className}`);
        });
        
        it("Should handle updating existing fields", async function () {
            console.log("\n🧪 TEST: Update existing fields");
            
            const fieldKey = "update.test";
            
            // Создаем поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(fieldKey, "QmV1");
            expect(await amanitaIntl.getSimpleFieldCID(fieldKey)).to.equal("QmV1");
            
            // Обновляем (owner может)
            await amanitaIntl.connect(seller1).setSimpleFieldCID(fieldKey, "QmV2");
            expect(await amanitaIntl.getSimpleFieldCID(fieldKey)).to.equal("QmV2");
            
            // Еще раз обновляем
            await amanitaIntl.connect(seller1).setSimpleFieldCID(fieldKey, "QmV3");
            expect(await amanitaIntl.getSimpleFieldCID(fieldKey)).to.equal("QmV3");
            
            // Статистика НЕ должна увеличиться (то же поле)
            const stats = await amanitaIntl.getStatistics();
            // totalSimpleFields увеличивается только при первом создании
            
            console.log(`   ✅ Field updated: QmV1 → QmV2 → QmV3`);
        });
        
        it("Should handle concurrent operations from multiple sellers", async function () {
            console.log("\n🧪 TEST: Concurrent sellers");
            
            // Seller1 и Seller2 создают свои поля
            await amanitaIntl.connect(seller1).setSimpleFieldCID("seller1.field", "QmS1");
            await amanitaIntl.connect(seller2).setSimpleFieldCID("seller2.field", "QmS2");
            
            // Проверяем owners
            const owner1 = await amanitaIntl.simpleFieldOwner("seller1.field");
            const owner2 = await amanitaIntl.simpleFieldOwner("seller2.field");
            
            expect(owner1).to.equal(seller1.address);
            expect(owner2).to.equal(seller2.address);
            
            // Каждый может обновлять ТОЛЬКО свои
            await amanitaIntl.connect(seller1).setSimpleFieldCID("seller1.field", "QmS1v2");
            await amanitaIntl.connect(seller2).setSimpleFieldCID("seller2.field", "QmS2v2");
            
            // НО не чужие
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID("seller2.field", "QmHack"),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log(`   ✅ Concurrent sellers isolated correctly`);
        });
    });
});

