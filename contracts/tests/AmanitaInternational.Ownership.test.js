const { expect } = require("chai");
const { ethers } = require("hardhat");

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

/**
 * 🧪 AmanitaInternational - Ownership & Access Control Test Suite
 * 
 * Применяет методологию @test-to-success.mdc
 * Проверяет ownership-based access control для переводов
 * 
 * Критические пути:
 * - Seller создает и управляет своими полями
 * - Seller не может менять чужие поля
 * - Admin управляет любыми полями
 * - Глобальные поля доступны только Admin
 */

describe("🔐 AmanitaInternational - Ownership & Access Control", function () {
    let amanitaIntl;
    let admin;
    let seller1;
    let seller2;
    let regularUser;
    let mockSpiralEngine;
    
    // Константы ролей
    const ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ADMIN_ROLE"));
    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
    const UPGRADER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("UPGRADER_ROLE"));
    
    beforeEach(async function () {
        console.log("\n🔧 Setup: Deploying contracts...");
        
        // Получаем signers
        [admin, seller1, seller2, regularUser] = await ethers.getSigners();
        
        console.log(`   Admin: ${admin.address}`);
        console.log(`   Seller1: ${seller1.address}`);
        console.log(`   Seller2: ${seller2.address}`);
        console.log(`   Regular User: ${regularUser.address}`);
        
        // Deploy Mock SpiralEngine для тестов
        const MockSpiralEngine = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        mockSpiralEngine = await MockSpiralEngine.deploy();
        await mockSpiralEngine.waitForDeployment();
        const mockSpiralEngineAddress = await mockSpiralEngine.getAddress();
        
        console.log(`   Mock SpiralEngine deployed: ${mockSpiralEngineAddress}`);
        
        // Deploy Logic
        const AmanitaInternationalLogic = await ethers.getContractFactory("AmanitaInternationalLogic");
        const logic = await AmanitaInternationalLogic.deploy();
        await logic.waitForDeployment();
        const logicAddress = await logic.getAddress();
        
        console.log(`   Logic deployed: ${logicAddress}`);
        
        // Deploy Proxy
        const AmanitaInternationalProxy = await ethers.getContractFactory("AmanitaInternationalProxy");
        
        // Кодируем initialize вызов с 2 параметрами
        const initData = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            mockSpiralEngineAddress
        ]);
        
        const proxy = await AmanitaInternationalProxy.deploy(
            logicAddress,
            initData
        );
        await proxy.waitForDeployment();
        const proxyAddress = await proxy.getAddress();
        
        console.log(`   Proxy deployed: ${proxyAddress}`);
        
        // Подключаемся к Proxy через Logic ABI
        amanitaIntl = await ethers.getContractAt("AmanitaInternationalLogic", proxyAddress);
        
        console.log(`   Contract ready at: ${await amanitaIntl.getAddress()}`);
        
        // Выдаем SELLER_ROLE обоим селлерам (ЛОКАЛЬНО в AmanitaInternational)
        await amanitaIntl.connect(admin).grantRole(SELLER_ROLE, seller1.address);
        await amanitaIntl.connect(admin).grantRole(SELLER_ROLE, seller2.address);
        
        console.log(`   ✅ SELLER_ROLE granted to seller1 and seller2`);
    });
    
    // =====================================================================
    // 📋 SUITE 1: OWNERSHIP - SIMPLE FIELDS
    // =====================================================================
    
    describe("1️⃣ Ownership: Simple Fields", function () {
        
        it("Should allow seller to create and manage own simple fields", async function () {
            console.log("\n🧪 TEST: Seller creates and manages own field");
            
            // 1. Seller1 создает поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Component.amanita_muscaria.title",
                "QmTestCID123"
            );
            
            console.log("   ✅ Seller1 created field");
            
            // 2. Проверяем owner
            const owner = await amanitaIntl.simpleFieldOwner("Component.amanita_muscaria.title");
            expect(owner).to.equal(seller1.address);
            
            console.log(`   ✅ Owner verified: ${owner}`);
            
            // 3. Проверяем CID
            const cid = await amanitaIntl.getSimpleFieldCID("Component.amanita_muscaria.title");
            expect(cid).to.equal("QmTestCID123");
            
            console.log(`   ✅ CID verified: ${cid}`);
            
            // 4. Seller1 может обновить своё поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Component.amanita_muscaria.title",
                "QmUpdatedCID456"
            );
            
            const updatedCid = await amanitaIntl.getSimpleFieldCID("Component.amanita_muscaria.title");
            expect(updatedCid).to.equal("QmUpdatedCID456");
            
            console.log(`   ✅ Seller1 updated own field: ${updatedCid}`);
        });
        
        it("Should prevent seller from modifying other seller's fields", async function () {
            console.log("\n🧪 TEST: Seller cannot modify other seller's field");
            
            // 1. Seller1 создает поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Component.seller1_comp.title",
                "QmSeller1CID"
            );
            
            console.log("   ✅ Seller1 created field");
            
            // 2. Seller2 НЕ может изменить поле seller1
            await expectCustomError(
                amanitaIntl.connect(seller2).setSimpleFieldCID(
                    "Component.seller1_comp.title",
                    "QmSeller2HackAttempt"
                ),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Seller2 blocked from modifying seller1's field");
            
            // 3. CID остался неизменным
            const cid = await amanitaIntl.getSimpleFieldCID("Component.seller1_comp.title");
            expect(cid).to.equal("QmSeller1CID");
            
            console.log(`   ✅ CID unchanged: ${cid}`);
        });
        
        it("Should allow admin to modify any field", async function () {
            console.log("\n🧪 TEST: Admin can modify any field");
            
            // 1. Seller создает поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Component.test.title",
                "QmSellerCID"
            );
            
            console.log("   ✅ Seller1 created field");
            
            // 2. Admin может изменить поле seller
            await amanitaIntl.connect(admin).setSimpleFieldCID(
                "Component.test.title",
                "QmAdminOverride"
            );
            
            console.log("   ✅ Admin modified seller's field");
            
            // 3. Проверяем что CID обновился
            const cid = await amanitaIntl.getSimpleFieldCID("Component.test.title");
            expect(cid).to.equal("QmAdminOverride");
            
            console.log(`   ✅ CID updated by admin: ${cid}`);
            
            // 4. Owner остался seller (не меняется при update)
            const owner = await amanitaIntl.simpleFieldOwner("Component.test.title");
            expect(owner).to.equal(seller1.address);
            
            console.log(`   ✅ Owner unchanged: ${owner}`);
        });
        
        it("Should prevent regular user from creating fields", async function () {
            console.log("\n🧪 TEST: Regular user cannot create fields");
            
            // Regular user НЕ имеет ни ADMIN_ROLE ни SELLER_ROLE
            await expectCustomError(
                amanitaIntl.connect(regularUser).setSimpleFieldCID(
                    "Component.hacker.title",
                    "QmHackerCID"
                ),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Regular user blocked from creating field");
        });
    });
    
    // =====================================================================
    // 📋 SUITE 2: OWNERSHIP - COMPLEX FIELDS
    // =====================================================================
    
    describe("2️⃣ Ownership: Complex Fields", function () {
        
        it("Should allow seller to create and manage own complex fields", async function () {
            console.log("\n🧪 TEST: Seller creates and manages own complex field");
            
            // 1. Seller1 регистрирует перевод (русский)
            await amanitaIntl.connect(seller1).setComplexFieldCID(
                "ComponentDescription",
                "ru",
                "QmRussianDesc123"
            );
            
            console.log("   ✅ Seller1 created complex field (ru)");
            
            // 2. Проверяем owner
            const owner = await amanitaIntl.getComplexFieldOwner("ComponentDescription", "ru");
            expect(owner).to.equal(seller1.address);
            
            console.log(`   ✅ Owner verified: ${owner}`);
            
            // 3. Seller1 добавляет другой язык (английский)
            await amanitaIntl.connect(seller1).setComplexFieldCID(
                "ComponentDescription",
                "en",
                "QmEnglishDesc456"
            );
            
            console.log("   ✅ Seller1 added another language (en)");
            
            // 4. Проверяем что оба owner = seller1
            const ownerEn = await amanitaIntl.getComplexFieldOwner("ComponentDescription", "en");
            expect(ownerEn).to.equal(seller1.address);
            
            console.log(`   ✅ Both languages owned by seller1`);
            
            // 5. Seller1 может обновить свой перевод
            await amanitaIntl.connect(seller1).setComplexFieldCID(
                "ComponentDescription",
                "ru",
                "QmUpdatedRussian789"
            );
            
            const updatedCid = await amanitaIntl.getComplexFieldCID("ComponentDescription", "ru");
            expect(updatedCid).to.equal("QmUpdatedRussian789");
            
            console.log(`   ✅ Seller1 updated own translation: ${updatedCid}`);
        });
        
        it("Should prevent seller from modifying other seller's translations", async function () {
            console.log("\n🧪 TEST: Seller cannot modify other seller's translation");
            
            // 1. Seller1 создает перевод
            await amanitaIntl.connect(seller1).setComplexFieldCID(
                "ProductDescription",
                "ru",
                "QmSeller1Russian"
            );
            
            console.log("   ✅ Seller1 created translation");
            
            // 2. Seller2 НЕ может изменить перевод seller1
            await expectCustomError(
                amanitaIntl.connect(seller2).setComplexFieldCID(
                    "ProductDescription",
                    "ru",
                    "QmSeller2HackAttempt"
                ),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Seller2 blocked from modifying seller1's translation");
            
            // 3. CID остался неизменным
            const cid = await amanitaIntl.getComplexFieldCID("ProductDescription", "ru");
            expect(cid).to.equal("QmSeller1Russian");
            
            console.log(`   ✅ CID unchanged: ${cid}`);
        });
        
        it("Should allow different sellers to create own translations for same class", async function () {
            console.log("\n🧪 TEST: Different sellers can create own translations");
            
            // 1. Seller1 создает русский перевод
            await amanitaIntl.connect(seller1).setComplexFieldCID(
                "GlobalDescription",
                "ru",
                "QmSeller1Russian"
            );
            
            // 2. Seller2 создает английский перевод (другой язык того же класса)
            await amanitaIntl.connect(seller2).setComplexFieldCID(
                "GlobalDescription",
                "en",
                "QmSeller2English"
            );
            
            console.log("   ✅ Both sellers created translations for different languages");
            
            // 3. Проверяем owners
            const ownerRu = await amanitaIntl.getComplexFieldOwner("GlobalDescription", "ru");
            const ownerEn = await amanitaIntl.getComplexFieldOwner("GlobalDescription", "en");
            
            expect(ownerRu).to.equal(seller1.address);
            expect(ownerEn).to.equal(seller2.address);
            
            console.log(`   ✅ Verified: ru → seller1, en → seller2`);
        });
    });
    
    // =====================================================================
    // 📋 SUITE 3: GLOBAL FIELDS
    // =====================================================================
    
    describe("3️⃣ Global Fields", function () {
        
        it("Should allow admin to mark fields as global", async function () {
            console.log("\n🧪 TEST: Admin marks field as global");
            
            // 1. Admin помечает поле как глобальное
            await amanitaIntl.connect(admin).setGlobalField("features", true);
            
            console.log("   ✅ Admin marked 'features' as global");
            
            // 2. Проверяем статус
            const isGlobal = await amanitaIntl.isFieldGlobal("features");
            expect(isGlobal).to.be.true;
            
            console.log(`   ✅ Field is global: ${isGlobal}`);
            
            // 3. Admin может снять флаг
            await amanitaIntl.connect(admin).setGlobalField("features", false);
            
            const isGlobalAfter = await amanitaIntl.isFieldGlobal("features");
            expect(isGlobalAfter).to.be.false;
            
            console.log(`   ✅ Admin unset global flag: ${isGlobalAfter}`);
        });
        
        it("Should enforce global fields (only ADMIN can modify)", async function () {
            console.log("\n🧪 TEST: Global fields only modifiable by admin");
            
            // 1. Admin помечает поле как глобальное
            await amanitaIntl.connect(admin).setGlobalField("features", true);
            
            // 2. Admin устанавливает глобальное поле
            await amanitaIntl.connect(admin).setSimpleFieldCID(
                "features",
                "QmGlobalFeaturesCID"
            );
            
            console.log("   ✅ Admin set global field");
            
            // 3. Проверяем owner (должен быть admin)
            const owner = await amanitaIntl.simpleFieldOwner("features");
            expect(owner).to.equal(admin.address);
            
            console.log(`   ✅ Owner is admin: ${owner}`);
            
            // 4. Seller НЕ может изменить глобальное поле
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID(
                    "features",
                    "QmSellerHackAttempt"
                ),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Seller blocked from modifying global field");
            
            // 5. CID остался неизменным
            const cid = await amanitaIntl.getSimpleFieldCID("features");
            expect(cid).to.equal("QmGlobalFeaturesCID");
            
            console.log(`   ✅ CID unchanged: ${cid}`);
        });
        
        it("Should prevent non-admin from marking fields as global", async function () {
            console.log("\n🧪 TEST: Non-admin cannot mark fields as global");
            
            // Seller НЕ может помечать поля как глобальные
            await expectCustomError(
                amanitaIntl.connect(seller1).setGlobalField("my_field", true),
                amanitaIntl,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("   ✅ Seller blocked from setGlobalField");
        });
        
        it("Should enforce global complex fields (only ADMIN can modify)", async function () {
            console.log("\n🧪 TEST: Global complex fields only modifiable by admin");
            
            // 1. Admin помечает complex field как глобальное
            const globalKey = "ProductDescription.ru";
            await amanitaIntl.connect(admin).setGlobalField(globalKey, true);
            
            console.log("   ✅ Admin marked complex field as global");
            
            // 2. Admin устанавливает глобальное complex field
            await amanitaIntl.connect(admin).setComplexFieldCID(
                "ProductDescription",
                "ru",
                "QmGlobalRussian"
            );
            
            console.log("   ✅ Admin set global complex field");
            
            // 3. Проверяем owner (должен быть admin)
            const owner = await amanitaIntl.getComplexFieldOwner("ProductDescription", "ru");
            expect(owner).to.equal(admin.address);
            
            console.log(`   ✅ Owner is admin: ${owner}`);
            
            // 4. Seller НЕ может изменить глобальное complex field
            await expectCustomError(
                amanitaIntl.connect(seller1).setComplexFieldCID(
                    "ProductDescription",
                    "ru",
                    "QmSellerHackAttempt"
                ),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Seller blocked from modifying global complex field");
            
            // 5. CID остался неизменным
            const cid = await amanitaIntl.getComplexFieldCID("ProductDescription", "ru");
            expect(cid).to.equal("QmGlobalRussian");
            
            console.log(`   ✅ CID unchanged: ${cid}`);
            
            // 6. Admin может обновить глобальное complex field
            await amanitaIntl.connect(admin).setComplexFieldCID(
                "ProductDescription",
                "ru",
                "QmGlobalRussianV2"
            );
            
            const updatedCid = await amanitaIntl.getComplexFieldCID("ProductDescription", "ru");
            expect(updatedCid).to.equal("QmGlobalRussianV2");
            
            console.log(`   ✅ Admin updated global complex field: ${updatedCid}`);
        });
    });
    
    // =====================================================================
    // 📋 SUITE 4: EDGE CASES
    // =====================================================================
    
    describe("4️⃣ Edge Cases", function () {
        
        it("Should revert on empty fieldKey", async function () {
            console.log("\n🧪 TEST: Empty fieldKey reverts");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID(
                    "",  // Пустой ключ
                    "QmTestCID"
                ),
                amanitaIntl,
                "EmptyFieldKey"
            );
            
            console.log("   ✅ EmptyFieldKey error triggered");
        });
        
        it("Should revert on empty CID", async function () {
            console.log("\n🧪 TEST: Empty CID reverts");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID(
                    "test.field",
                    ""  // Пустой CID
                ),
                amanitaIntl,
                "EmptyCID"
            );
            
            console.log("   ✅ EmptyCID error triggered");
        });
        
        it("Should revert on empty className", async function () {
            console.log("\n🧪 TEST: Empty className reverts");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setComplexFieldCID(
                    "",  // Пустой className
                    "ru",
                    "QmTestCID"
                ),
                amanitaIntl,
                "EmptyClassName"
            );
            
            console.log("   ✅ EmptyClassName error triggered");
        });
        
        it("Should revert on empty language", async function () {
            console.log("\n🧪 TEST: Empty language reverts");
            
            await expectCustomError(
                amanitaIntl.connect(seller1).setComplexFieldCID(
                    "Description",
                    "",  // Пустой язык
                    "QmTestCID"
                ),
                amanitaIntl,
                "EmptyLanguage"
            );
            
            console.log("   ✅ EmptyLanguage error triggered");
        });
        
        it("Should not change owner when field is updated", async function () {
            console.log("\n🧪 TEST: Owner unchanged on update");
            
            // 1. Seller1 создает поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "test.field",
                "QmOriginalCID"
            );
            
            const ownerBefore = await amanitaIntl.simpleFieldOwner("test.field");
            expect(ownerBefore).to.equal(seller1.address);
            
            console.log(`   ✅ Original owner: ${ownerBefore}`);
            
            // 2. Seller1 обновляет поле
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "test.field",
                "QmUpdatedCID"
            );
            
            // 3. Owner остался тот же
            const ownerAfter = await amanitaIntl.simpleFieldOwner("test.field");
            expect(ownerAfter).to.equal(seller1.address);
            expect(ownerAfter).to.equal(ownerBefore);
            
            console.log(`   ✅ Owner unchanged after update: ${ownerAfter}`);
        });
        
        it("Should handle multiple sellers creating different fields", async function () {
            console.log("\n🧪 TEST: Multiple sellers, different fields");
            
            // 1. Seller1 создает поле A
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Component.A.title",
                "QmFieldA"
            );
            
            // 2. Seller2 создает поле B
            await amanitaIntl.connect(seller2).setSimpleFieldCID(
                "Component.B.title",
                "QmFieldB"
            );
            
            console.log("   ✅ Both sellers created different fields");
            
            // 3. Проверяем owners
            const ownerA = await amanitaIntl.simpleFieldOwner("Component.A.title");
            const ownerB = await amanitaIntl.simpleFieldOwner("Component.B.title");
            
            expect(ownerA).to.equal(seller1.address);
            expect(ownerB).to.equal(seller2.address);
            
            console.log(`   ✅ Field A → seller1, Field B → seller2`);
            
            // 4. Каждый может обновлять только свои поля
            await amanitaIntl.connect(seller1).setSimpleFieldCID("Component.A.title", "QmUpdatedA");
            await amanitaIntl.connect(seller2).setSimpleFieldCID("Component.B.title", "QmUpdatedB");
            
            // 5. НО не может менять чужие
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID("Component.B.title", "QmHack"),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            await expectCustomError(
                amanitaIntl.connect(seller2).setSimpleFieldCID("Component.A.title", "QmHack"),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Cross-modification blocked");
        });
    });
    
    // =====================================================================
    // 📋 SUITE 5: EVENTS
    // =====================================================================
    
    describe("5️⃣ Events", function () {
        
        it("Should emit GlobalFieldSet when marking field as global", async function () {
            console.log("\n🧪 TEST: GlobalFieldSet event");
            
            const tx = await amanitaIntl.connect(admin).setGlobalField("features", true);
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
            expect(fieldKey.hash).to.equal(ethers.id("features"));
            expect(isGlobal).to.equal(true);
            expect(actor).to.equal(admin.address);
            
            console.log("   ✅ GlobalFieldSet event emitted");
        });
        
        it("Should emit SimpleFieldRegistered when seller creates field", async function () {
            console.log("\n🧪 TEST: SimpleFieldRegistered event from seller");
            
            const tx = await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "test.field",
                "QmTestCID"
            );
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
                .filter((e) => e && e.name === "SimpleFieldRegistered");

            expect(decoded.length >= 1).to.be.true;
            const evt = decoded[0];
            const { fieldKey, cid, updater } = evt.args;
            expect(fieldKey.hash).to.equal(ethers.id("test.field"));
            expect(cid).to.equal("QmTestCID");
            expect(updater).to.equal(seller1.address);
            
            console.log("   ✅ SimpleFieldRegistered event emitted");
        });
        
        it("Should emit ComplexFieldRegistered when seller creates translation", async function () {
            console.log("\n🧪 TEST: ComplexFieldRegistered event from seller");
            
            const tx = await amanitaIntl.connect(seller1).setComplexFieldCID(
                "Description",
                "ru",
                "QmRussianCID"
            );
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
                .filter((e) => e && e.name === "ComplexFieldRegistered");

            expect(decoded.length >= 1).to.be.true;
            const evt = decoded[0];
            const { className, language, cid, updater } = evt.args;
            expect(className.hash).to.equal(ethers.id("Description"));
            expect(language.hash).to.equal(ethers.id("ru"));
            expect(cid).to.equal("QmRussianCID");
            expect(updater).to.equal(seller1.address);
            
            console.log("   ✅ ComplexFieldRegistered event emitted");
        });
    });
    
    // =====================================================================
    // 📋 SUITE 6: INTEGRATION WITH ROLES
    // =====================================================================
    
    describe("6️⃣ Integration with Roles", function () {
        
        it("Should grant SELLER_ROLE to new seller", async function () {
            console.log("\n🧪 TEST: Grant SELLER_ROLE");
            
            const newSeller = regularUser;
            
            // 1. Проверяем что роли нет
            const hasBefore = await amanitaIntl.hasRole(SELLER_ROLE, newSeller.address);
            expect(hasBefore).to.be.false;
            
            console.log("   ✅ Seller role not present initially");
            
            // 2. Admin выдаёт роль
            await amanitaIntl.connect(admin).grantRole(SELLER_ROLE, newSeller.address);
            
            const hasAfter = await amanitaIntl.hasRole(SELLER_ROLE, newSeller.address);
            expect(hasAfter).to.be.true;
            
            console.log(`   ✅ SELLER_ROLE granted to ${newSeller.address}`);
            
            // 3. Теперь новый seller может создавать поля
            await amanitaIntl.connect(newSeller).setSimpleFieldCID(
                "NewSeller.field",
                "QmNewSellerCID"
            );
            
            const owner = await amanitaIntl.simpleFieldOwner("NewSeller.field");
            expect(owner).to.equal(newSeller.address);
            
            console.log("   ✅ New seller can create fields after role grant");
        });
        
        it("Should revoke SELLER_ROLE and prevent field creation", async function () {
            console.log("\n🧪 TEST: Revoke SELLER_ROLE");
            
            // 1. Seller1 имеет роль (из beforeEach)
            const hasBefore = await amanitaIntl.hasRole(SELLER_ROLE, seller1.address);
            expect(hasBefore).to.be.true;
            
            // 2. Seller1 создает поле (пока есть роль)
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Before.revoke",
                "QmBeforeCID"
            );
            
            console.log("   ✅ Seller created field before revoke");
            
            // 3. Admin отзывает роль
            await amanitaIntl.connect(admin).revokeRole(SELLER_ROLE, seller1.address);
            
            const hasAfter = await amanitaIntl.hasRole(SELLER_ROLE, seller1.address);
            expect(hasAfter).to.be.false;
            
            console.log("   ✅ SELLER_ROLE revoked");
            
            // 4. Seller1 НЕ может создавать НОВЫЕ поля
            await expectCustomError(
                amanitaIntl.connect(seller1).setSimpleFieldCID(
                    "After.revoke",
                    "QmAfterCID"
                ),
                amanitaIntl,
                "UnauthorizedFieldAccess"
            );
            
            console.log("   ✅ Seller cannot create new fields after revoke");
            
            // 5. НО может обновлять СУЩЕСТВУЮЩЕЕ поле (ownership сохраняется!)
            await amanitaIntl.connect(seller1).setSimpleFieldCID(
                "Before.revoke",
                "QmUpdatedAfterRevoke"
            );
            
            const updatedCid = await amanitaIntl.getSimpleFieldCID("Before.revoke");
            expect(updatedCid).to.equal("QmUpdatedAfterRevoke");
            
            console.log("   ✅ Seller can still update own existing fields (ownership preserved)");
        });
    });
});

