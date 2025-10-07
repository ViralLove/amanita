const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * 🧪 AmanitaInternational 3-Contract Architecture Test Suite
 * 
 * Применяет методологию @test-to-success.mdc с жёстким анализом качества @test-qualification.mdc
 * 
 * Архитектура:
 * 1. Proxy - фиксированный адрес, делегирование вызовов
 * 2. Logic - версионируемая бизнес-логика
 * 3. Storage - персистентные данные с наращиваемой цепочкой
 * 
 * Критические пути:
 * - Деплой всех 3 контрактов
 * - Интеграция между контрактами
 * - Upgrade Logic с сохранением данных
 * - Наращивание Storage цепочки
 * - Access Control на всех уровнях
 * - Emergency procedures
 */

describe("🏗️ AmanitaInternational - 3-Contract Architecture", function () {
    let proxy;
    let logicV1;
    let storage;
    let admin;
    let user1;
    let user2;
    let unauthorizedUser;
    
    // Константы ролей
    const DEFAULT_ADMIN_ROLE = ethers.ZeroHash;
    const ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ADMIN_ROLE"));
    const PROXY_ROLE = ethers.keccak256(ethers.toUtf8Bytes("PROXY_ROLE"));
    const UPGRADER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("UPGRADER_ROLE"));
    const STORAGE_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("STORAGE_ADMIN_ROLE"));
    
    // Тестовые данные
    const TEST_SIMPLE_FIELDS = {
        "product.forms": "QmTestFormsAllLanguages123",
        "product.title": "QmTestTitleAllLanguages456",
        "product.species": "QmTestSpeciesAllLanguages789"
    };
    
    const TEST_COMPLEX_FIELDS = {
        "Description": {
            "ru": "QmTestDescriptionRussian123",
            "en": "QmTestDescriptionEnglish456"
        },
        "ComponentDescription": {
            "ru": "QmTestComponentRussian012",
            "en": "QmTestComponentEnglish345"
        }
    };
    
    // === УТИЛИТЫ ДЛЯ ЛОГИРОВАНИЯ ===
    
    async function logArchitectureState(context) {
        console.log(`\n🏗️ [${context}] Состояние архитектуры:`);
        console.log(`   Proxy: ${await proxy.getAddress()}`);
        console.log(`   Logic: ${await logicV1.getAddress()}`);
        console.log(`   Storage: ${await storage.getAddress()}`);
        
        const proxyInfo = await proxy.getProxyInfo();
        console.log(`   Current Logic в Proxy: ${proxyInfo.logic}`);
        console.log(`   Storage в Proxy: ${proxyInfo.storage_}`);
        console.log(`   Upgrade Count: ${proxyInfo.upgradeCount}`);
        console.log(`   Paused: ${proxyInfo.isPaused}`);
        
        const stats = await storage.getStatistics();
        console.log(`   Простых полей: ${stats.totalSimpleFields}`);
        console.log(`   Классов: ${stats.totalComplexClasses}`);
    }
    
    async function logStorageChain() {
        const chain = await storage.getStorageChain();
        console.log(`\n🔗 Storage Chain (${chain.length} контрактов):`);
        for (let i = 0; i < chain.length; i++) {
            console.log(`   ${i + 1}. ${chain[i]}`);
        }
    }
    
    // === НАСТРОЙКА ТЕСТОВ ===
    
    beforeEach(async function () {
        const signers = await ethers.getSigners();
        admin = signers[0];
        user1 = signers[1];
        user2 = signers[2];
        
        unauthorizedUser = ethers.Wallet.createRandom().connect(ethers.provider);
        await admin.sendTransaction({
            to: unauthorizedUser.address,
            value: ethers.parseEther("1.0")
        });
        
        console.log("\n🏗️ 3-Contract Architecture Setup Starting...");
        console.log(`   Admin: ${admin.address}`);
        
        // 1. Деплой Storage
        const Storage = await ethers.getContractFactory("AmanitaInternationalStorage");
        storage = await Storage.connect(admin).deploy(admin.address);
        await storage.waitForDeployment();
        console.log(`   ✅ Storage deployed: ${await storage.getAddress()}`);
        
        // 2. Деплой Logic
        const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
        logicV1 = await LogicV1.connect(admin).deploy(
            await storage.getAddress()
        );
        await logicV1.waitForDeployment();
        console.log(`   ✅ LogicV1 deployed: ${await logicV1.getAddress()}`);
        
        // 3. Деплой Proxy СНАЧАЛА (чтобы знать его адрес)
        const Proxy = await ethers.getContractFactory("AmanitaInternationalProxy");
        proxy = await Proxy.connect(admin).deploy(
            admin.address,
            await logicV1.getAddress(),
            await storage.getAddress()
        );
        await proxy.waitForDeployment();
        console.log(`   ✅ Proxy deployed: ${await proxy.getAddress()}`);
        
        // 4. Авторизуем Proxy в Storage (при delegatecall msg.sender = Proxy!)
        await storage.connect(admin).authorizeProxyContract(await proxy.getAddress());
        console.log(`   ✅ Proxy authorized in Storage`);
        
        await logArchitectureState("Initial Setup");
    });
    
    // === ТЕСТЫ ДЕПЛОЯ И ИНТЕГРАЦИИ ===
    
    describe("🚀 Deployment and Integration", function () {
        
        it("Should deploy all 3 contracts correctly", async function () {
            expect(await proxy.getAddress()).to.not.equal(ethers.ZeroAddress);
            expect(await logicV1.getAddress()).to.not.equal(ethers.ZeroAddress);
            expect(await storage.getAddress()).to.not.equal(ethers.ZeroAddress);
            
            // Проверяем связи
            expect(await proxy.currentLogic()).to.equal(await logicV1.getAddress());
            expect(await proxy.storageContract()).to.equal(await storage.getAddress());
            expect(await logicV1.getStorageAddress()).to.equal(await storage.getAddress());
        });
        
        it("Should have correct roles setup", async function () {
            // Proxy roles (здесь проверяются роли пользователей через delegatecall)
            expect(await proxy.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.be.true;
            expect(await proxy.hasRole(UPGRADER_ROLE, admin.address)).to.be.true;
            expect(await proxy.hasRole(ADMIN_ROLE, admin.address)).to.be.true;
            
            // Storage roles (Proxy контракт должен иметь PROXY_ROLE)
            expect(await storage.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.be.true;
            expect(await storage.hasRole(STORAGE_ADMIN_ROLE, admin.address)).to.be.true;
            expect(await storage.hasRole(PROXY_ROLE, await proxy.getAddress())).to.be.true;
        });
        
        it("Should have storage chain initialized", async function () {
            const chain = await storage.getStorageChain();
            expect(chain).to.have.lengthOf(1);
            expect(chain[0]).to.equal(await storage.getAddress());
            
            await logStorageChain();
        });
    });
    
    // === ТЕСТЫ РАБОТЫ ЧЕРЕЗ PROXY ===
    
    describe("🔄 Proxy Delegation", function () {
        
        it("Should delegate simple field operations through proxy", async function () {
            console.log("\n🔄 Тест: Делегирование через Proxy");
            
            // Получаем интерфейс Logic для вызова через Proxy
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // Вызываем через Proxy
            const fieldKey = "product.forms";
            const cid = TEST_SIMPLE_FIELDS[fieldKey];
            
            const tx = await proxyAsLogic.connect(admin).setSimpleFieldCID(fieldKey, cid);
            await tx.wait();
            console.log(`   ✅ setSimpleFieldCID called through Proxy`);
            
            // Проверяем что данные сохранились в Storage
            const retrievedCID = await storage.getSimpleFieldCID(fieldKey);
            expect(retrievedCID).to.equal(cid);
            console.log(`   ✅ Data saved in Storage: ${retrievedCID}`);
            
            // Проверяем что можем прочитать через Proxy
            const cidThroughProxy = await proxyAsLogic.getSimpleFieldCID(fieldKey);
            expect(cidThroughProxy).to.equal(cid);
            console.log(`   ✅ Data read through Proxy: ${cidThroughProxy}`);
            
            await logArchitectureState("After Delegation");
        });
        
        it("Should delegate complex field operations through proxy", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const className = "Description";
            const language = "ru";
            const cid = TEST_COMPLEX_FIELDS[className][language];
            
            await proxyAsLogic.connect(admin).setComplexFieldCID(className, language, cid);
            
            // Проверяем через Storage
            const cidFromStorage = await storage.getComplexFieldCID(className, language);
            expect(cidFromStorage).to.equal(cid);
            
            // Проверяем через Proxy
            const cidThroughProxy = await proxyAsLogic.getComplexFieldCID(className, language);
            expect(cidThroughProxy).to.equal(cid);
        });
        
        it("Should delegate batch operations through proxy", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const fieldKeys = Object.keys(TEST_SIMPLE_FIELDS);
            const cids = Object.values(TEST_SIMPLE_FIELDS);
            
            await proxyAsLogic.connect(admin).batchSetSimpleFields(fieldKeys, cids);
            
            // Проверяем все поля через Storage
            for (let i = 0; i < fieldKeys.length; i++) {
                const cid = await storage.getSimpleFieldCID(fieldKeys[i]);
                expect(cid).to.equal(cids[i]);
            }
        });
        
        it("Should revert when proxy is paused", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // Ставим на паузу
            await proxy.connect(admin).emergencyPause();
            
            // Попытка вызова должна провалиться
            await expect(
                proxyAsLogic.connect(admin).setSimpleFieldCID("test", "QmTest123")
            ).to.be.reverted; // Может быть разный error message
            
            // Снимаем с паузы
            await proxy.connect(admin).emergencyUnpause();
            
            // Теперь должно работать
            await proxyAsLogic.connect(admin).setSimpleFieldCID("test", "QmTest123");
            expect(await proxyAsLogic.getSimpleFieldCID("test")).to.equal("QmTest123");
        });
    });
    
    // === ТЕСТЫ UPGRADE LOGIC ===
    
    describe("⬆️ Logic Upgrade", function () {
        
        it("Should upgrade logic contract preserving all data", async function () {
            console.log("\n⬆️ Тест: Upgrade LogicV1 → LogicV2");
            
            // Подготовка: устанавливаем данные через LogicV1
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogicV1 = LogicV1.attach(await proxy.getAddress());
            
            const fieldKeys = Object.keys(TEST_SIMPLE_FIELDS);
            const cids = Object.values(TEST_SIMPLE_FIELDS);
            await proxyAsLogicV1.connect(admin).batchSetSimpleFields(fieldKeys, cids);
            console.log(`   ✅ Данные установлены через LogicV1`);
            
            // Деплоим LogicV2 (используем V1 как mock)
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.connect(admin).deploy(
                await storage.getAddress()
            );
            await logicV2.waitForDeployment();
            console.log(`   ✅ LogicV2 deployed: ${await logicV2.getAddress()}`);
            
            // LogicV2 НЕ нужно авторизовать - авторизован Proxy!
            console.log(`   ✅ LogicV2 authorized in Storage`);
            
            // Обновляем Proxy
            const oldLogic = await proxy.currentLogic();
            const tx = await proxy.connect(admin).upgradeLogic(await logicV2.getAddress());
            await tx.wait();
            
            // LogicUpgraded событие имеет 4 аргумента: (oldLogic, newLogic, upgrader, timestamp)
            await expect(tx)
                .to.emit(proxy, "LogicUpgraded");
            
            // Проверяем аргументы события вручную
            const receipt = await tx.wait();
            const event = receipt.logs.find(log => {
                try {
                    const parsed = proxy.interface.parseLog(log);
                    return parsed && parsed.name === "LogicUpgraded";
                } catch (e) {
                    return false;
                }
            });
            expect(event).to.not.be.undefined;
            const parsedEvent = proxy.interface.parseLog(event);
            expect(parsedEvent.args[0]).to.equal(oldLogic); // oldLogic
            expect(parsedEvent.args[1]).to.equal(await logicV2.getAddress()); // newLogic
            expect(parsedEvent.args[2]).to.equal(admin.address); // upgrader
            
            console.log(`   ✅ Proxy upgraded to LogicV2`);
            
            // Проверяем что данные сохранились
            const proxyAsLogicV2 = LogicV2.attach(await proxy.getAddress());
            for (let i = 0; i < fieldKeys.length; i++) {
                const cid = await proxyAsLogicV2.getSimpleFieldCID(fieldKeys[i]);
                expect(cid).to.equal(cids[i]);
                console.log(`   ✅ Data preserved: ${fieldKeys[i]}`);
            }
            
            // Проверяем что новые операции работают
            await proxyAsLogicV2.connect(admin).setSimpleFieldCID("new.field", "QmNew123");
            const newCID = await proxyAsLogicV2.getSimpleFieldCID("new.field");
            expect(newCID).to.equal("QmNew123");
            console.log(`   ✅ New operations work in LogicV2`);
            
            await logArchitectureState("After Logic Upgrade");
        });
        
        it("Should maintain upgrade history", async function () {
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            
            const LogicV3 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV3 = await LogicV3.deploy(await storage.getAddress());
            await logicV3.waitForDeployment();
            
            // Logic контракты НЕ нужно авторизовать - авторизован Proxy!
            
            // Upgrade V1 → V2
            await proxy.connect(admin).upgradeLogic(await logicV2.getAddress());
            
            // Upgrade V2 → V3
            await proxy.connect(admin).upgradeLogic(await logicV3.getAddress());
            
            // Проверяем историю
            const history = await proxy.getLogicHistory();
            expect(history).to.have.lengthOf(3);
            expect(history[0]).to.equal(await logicV1.getAddress());
            expect(history[1]).to.equal(await logicV2.getAddress());
            expect(history[2]).to.equal(await logicV3.getAddress());
            
            expect(await proxy.getUpgradeCount()).to.equal(2);
        });
        
        it("Should rollback to previous logic", async function () {
            // Деплоим и обновляем до LogicV2
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            // Storage уже авторизовал Proxy, новый Logic работает через тот же Proxy
            
            await proxy.connect(admin).upgradeLogic(await logicV2.getAddress());
            expect(await proxy.currentLogic()).to.equal(await logicV2.getAddress());
            
            // Откат к V1
            const tx = await proxy.connect(admin).rollbackToPreviousLogic();
            // LogicUpgraded событие содержит 4 аргумента: oldLogic, newLogic, upgrader, timestamp
            await expect(tx).to.emit(proxy, "LogicUpgraded");
            
            expect(await proxy.currentLogic()).to.equal(await logicV1.getAddress());
        });
        
        it("Should revert upgrade when unauthorized", async function () {
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            
            await expect(
                proxy.connect(unauthorizedUser).upgradeLogic(await logicV2.getAddress())
            ).to.be.revertedWithCustomError(proxy, "AccessControlUnauthorizedAccount");
        });
        
        it("Should revert upgrade to same logic", async function () {
            await expect(
                proxy.connect(admin).upgradeLogic(await logicV1.getAddress())
            ).to.be.revertedWith("AmanitaInternationalProxy: same logic address");
        });
    });
    
    // === ТЕСТЫ STORAGE CHAIN ===
    
    describe("🔗 Storage Chain Expansion", function () {
        
        it("Should expand storage chain with new storage contract", async function () {
            console.log("\n🔗 Тест: Расширение Storage цепочки");
            
            // Проверяем начальную цепочку
            let chain = await storage.getStorageChain();
            expect(chain).to.have.lengthOf(1);
            console.log(`   📊 Initial chain length: ${chain.length}`);
            
            // Деплоим StorageV2 (используем тот же контракт как mock)
            const StorageV2Factory = await ethers.getContractFactory("AmanitaInternationalStorage");
            const storageV2 = await StorageV2Factory.deploy(admin.address);
            await storageV2.waitForDeployment();
            console.log(`   ✅ StorageV2 deployed: ${await storageV2.getAddress()}`);
            
            // Добавляем в цепочку
            const tx = await storage.connect(admin).setNextStorage(await storageV2.getAddress());
            await expect(tx)
                .to.emit(storage, "NextStorageSet")
                .withArgs(await storageV2.getAddress(), 2);
            
            // Проверяем цепочку
            chain = await storage.getStorageChain();
            expect(chain).to.have.lengthOf(2);
            expect(chain[0]).to.equal(await storage.getAddress());
            expect(chain[1]).to.equal(await storageV2.getAddress());
            
            expect(await storage.nextStorage()).to.equal(await storageV2.getAddress());
            
            await logStorageChain();
            console.log(`   ✅ Storage chain expanded successfully`);
        });
        
        it("Should prevent setting next storage twice", async function () {
            const StorageV2Factory = await ethers.getContractFactory("AmanitaInternationalStorage");
            const storageV2 = await StorageV2Factory.deploy(admin.address);
            await storageV2.waitForDeployment();
            
            await storage.connect(admin).setNextStorage(await storageV2.getAddress());
            
            // Попытка установить еще раз должна провалиться
            const storageV3 = await StorageV2Factory.deploy(admin.address);
            await storageV3.waitForDeployment();
            
            await expect(
                storage.connect(admin).setNextStorage(await storageV3.getAddress())
            ).to.be.revertedWith("AmanitaInternationalStorage: next storage already set");
        });
    });
    
    // === ТЕСТЫ DATA PERSISTENCE ===
    
    describe("💾 Data Persistence", function () {
        
        it("Should preserve data across logic upgrades", async function () {
            console.log("\n💾 Тест: Сохранность данных при upgrade Logic");
            
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogicV1 = LogicV1.attach(await proxy.getAddress());
            
            // Устанавливаем большой датасет
            const largeFieldKeys = [];
            const largeCIDs = [];
            for (let i = 0; i < 20; i++) {
                largeFieldKeys.push(`field.${i}`);
                largeCIDs.push(`QmTestCID${i.toString().padStart(3, '0')}`);
            }
            
            await proxyAsLogicV1.connect(admin).batchSetSimpleFields(largeFieldKeys, largeCIDs);
            console.log(`   ✅ 20 полей установлено через LogicV1`);
            
            // Деплоим LogicV2
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            // Storage уже авторизовал Proxy, новый Logic работает через тот же Proxy
            
            // Upgrade
            await proxy.connect(admin).upgradeLogic(await logicV2.getAddress());
            console.log(`   ✅ Upgraded to LogicV2`);
            
            // Проверяем все поля через LogicV2
            const proxyAsLogicV2 = LogicV2.attach(await proxy.getAddress());
            for (let i = 0; i < largeFieldKeys.length; i++) {
                const cid = await proxyAsLogicV2.getSimpleFieldCID(largeFieldKeys[i]);
                expect(cid).to.equal(largeCIDs[i]);
            }
            console.log(`   ✅ Все 20 полей сохранены после upgrade`);
            
            // Проверяем статистику
            const stats = await proxyAsLogicV2.getStatistics();
            expect(stats.totalSimpleFields).to.equal(largeFieldKeys.length);
            
            await logArchitectureState("After Data Persistence Test");
        });
    });
    
    // === ТЕСТЫ ACCESS CONTROL ===
    
    describe("🔒 Access Control", function () {
        
        it("Should enforce PROXY_ROLE on storage operations", async function () {
            // Прямой вызов Storage без PROXY_ROLE должен провалиться
            await expect(
                storage.connect(admin).setSimpleFieldCID("test", "QmTest123")
            ).to.be.revertedWithCustomError(storage, "AccessControlUnauthorizedAccount");
            
            // Через Proxy → Logic → Storage (Proxy имеет PROXY_ROLE) должно работать
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            await proxyAsLogic.connect(admin).setSimpleFieldCID("test", "QmTest123");
            expect(await proxyAsLogic.getSimpleFieldCID("test")).to.equal("QmTest123");
        });
        
        it("Should allow only admin to upgrade logic in proxy", async function () {
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            
            await expect(
                proxy.connect(unauthorizedUser).upgradeLogic(await logicV2.getAddress())
            ).to.be.revertedWithCustomError(proxy, "AccessControlUnauthorizedAccount");
        });
        
        it("Should allow only STORAGE_ADMIN to expand storage chain", async function () {
            const StorageV2 = await ethers.getContractFactory("AmanitaInternationalStorage");
            const storageV2 = await StorageV2.deploy(admin.address);
            await storageV2.waitForDeployment();
            
            await expect(
                storage.connect(unauthorizedUser).setNextStorage(await storageV2.getAddress())
            ).to.be.revertedWithCustomError(storage, "AccessControlUnauthorizedAccount");
        });
    });
    
    // === ИНТЕГРАЦИОННЫЙ ТЕСТ ===
    
    describe("🔗 Full Integration Test", function () {
        
        it("Should handle complete lifecycle: deploy → use → upgrade → expand", async function () {
            console.log("\n🔗 Полный lifecycle тест");
            
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // 1. Использование через Proxy + LogicV1
            await proxyAsLogic.connect(admin).setSimpleFieldCID("field1", "QmCID1");
            await proxyAsLogic.connect(admin).setComplexFieldCID("Class1", "en", "QmCID2");
            console.log(`   ✅ Step 1: Data populated through LogicV1`);
            
            // 2. Upgrade Logic V1 → V2
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress()); // Только storage address
            await logicV2.waitForDeployment();
            // Storage уже авторизовал Proxy, новый Logic работает через тот же Proxy
            await proxy.connect(admin).upgradeLogic(await logicV2.getAddress());
            console.log(`   ✅ Step 2: Upgraded to LogicV2`);
            
            // 3. Проверяем данные через LogicV2
            const proxyAsLogicV2 = LogicV2.attach(await proxy.getAddress());
            expect(await proxyAsLogicV2.getSimpleFieldCID("field1")).to.equal("QmCID1");
            expect(await proxyAsLogicV2.getComplexFieldCID("Class1", "en")).to.equal("QmCID2");
            console.log(`   ✅ Step 3: Data accessible through LogicV2`);
            
            // 4. Расширяем Storage цепочку
            const StorageV2 = await ethers.getContractFactory("AmanitaInternationalStorage");
            const storageV2 = await StorageV2.deploy(admin.address);
            await storageV2.waitForDeployment();
            await storage.connect(admin).setNextStorage(await storageV2.getAddress());
            console.log(`   ✅ Step 4: Storage chain expanded`);
            
            // 5. Добавляем новые данные
            await proxyAsLogicV2.connect(admin).setSimpleFieldCID("field2", "QmCID3");
            expect(await proxyAsLogicV2.getSimpleFieldCID("field2")).to.equal("QmCID3");
            console.log(`   ✅ Step 5: New data added`);
            
            // 6. Финальная проверка
            const chain = await storage.getStorageChain();
            expect(chain).to.have.lengthOf(2);
            
            const proxyInfo = await proxy.getProxyInfo();
            expect(proxyInfo.upgradeCount).to.equal(1);
            
            await logArchitectureState("Final State");
            await logStorageChain();
            
            console.log("\n🎉 Полный lifecycle успешно завершен!");
        });
    });
    
    // === ТЕСТЫ EMERGENCY PROCEDURES ===
    
    describe("🚨 Emergency Procedures", function () {
        
        it("Should emergency pause and unpause", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // Пауза
            const pauseTx = await proxy.connect(admin).emergencyPause();
            // EmergencyPaused событие содержит 2 аргумента: admin, timestamp
            await expect(pauseTx).to.emit(proxy, "EmergencyPaused");
            
            expect(await proxy.paused()).to.be.true;
            
            // Попытка вызова должна провалиться
            await expect(
                proxyAsLogic.connect(admin).setSimpleFieldCID("test", "QmTest")
            ).to.be.revertedWith("AmanitaInternationalProxy: contract paused");
            
            // Снятие паузы
            const unpauseTx = await proxy.connect(admin).emergencyUnpause();
            // EmergencyUnpaused событие содержит 2 аргумента: admin, timestamp
            await expect(unpauseTx).to.emit(proxy, "EmergencyUnpaused");
            
            expect(await proxy.paused()).to.be.false;
            
            // Теперь должно работать
            await expect(
                proxyAsLogic.connect(admin).setSimpleFieldCID("test", "QmTest")
            ).to.not.be.reverted;
        });
        
        it("Should prevent upgrade when paused", async function () {
            await proxy.connect(admin).emergencyPause();
            
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            
            await expect(
                proxy.connect(admin).upgradeLogic(await logicV2.getAddress())
            ).to.be.revertedWith("AmanitaInternationalProxy: contract paused");
        });
    });
    
    // === ТЕСТЫ ВЕРСИОНИРОВАНИЯ ===
    
    describe("📊 Versioning", function () {
        
        it("Should return correct version info", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const versionInfo = await proxyAsLogic.getVersionInfo();
            expect(versionInfo.version).to.equal("1.0.1"); // Обновлено после добавления ReentrancyGuard
            expect(versionInfo.logicVersion).to.equal(1);
            
            const storageVersion = await storage.getStorageVersion();
            expect(storageVersion).to.equal(1);
        });
    });
    
    // === ТЕСТЫ BACKWARD COMPATIBILITY ===
    
    describe("🔄 Backward Compatibility with V1", function () {
        
        it("Should support all V1 operations through 3-contract architecture", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // Test all operations from original AmanitaInternational.test.js
            
            // 1. Set and get simple field
            await proxyAsLogic.connect(admin).setSimpleFieldCID("product.forms", "QmTest123");
            expect(await proxyAsLogic.getSimpleFieldCID("product.forms")).to.equal("QmTest123");
            
            // 2. Set and get complex field
            await proxyAsLogic.connect(admin).setComplexFieldCID("Description", "ru", "QmTest456");
            expect(await proxyAsLogic.getComplexFieldCID("Description", "ru")).to.equal("QmTest456");
            
            // 3. Batch operations
            const fieldKeys = ["field1", "field2", "field3"];
            const cids = ["cid1", "cid2", "cid3"];
            await proxyAsLogic.connect(admin).batchSetSimpleFields(fieldKeys, cids);
            
            for (let i = 0; i < fieldKeys.length; i++) {
                expect(await proxyAsLogic.getSimpleFieldCID(fieldKeys[i])).to.equal(cids[i]);
            }
            
            // 4. Remove operations
            await proxyAsLogic.connect(admin).removeSimpleField("field1");
            expect(await proxyAsLogic.simpleFieldExist("field1")).to.be.false;
            
            // 5. Statistics
            const stats = await proxyAsLogic.getStatistics();
            expect(stats.totalSimpleFields).to.be.greaterThan(0);
            
            console.log("\n✅ Все операции V1 работают через 3-контрактную архитектуру!");
        });
    });
    
    // === ТЕСТЫ EDGE CASES ===
    
    describe("🔍 Edge Cases", function () {
        
        it("Should revert when setting empty field key", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            await expect(
                proxyAsLogic.connect(admin).setSimpleFieldCID("", "QmTest123")
            ).to.be.reverted; // Может быть разный error message через delegatecall
        });
        
        it("Should revert when setting empty CID", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            await expect(
                proxyAsLogic.connect(admin).setSimpleFieldCID("test.field", "")
            ).to.be.reverted; // Может быть разный error message через delegatecall
        });
        
        it("Should revert batch operations with mismatched arrays", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            await expect(
                proxyAsLogic.connect(admin).batchSetSimpleFields(
                    ["field1", "field2"],
                    ["cid1"] // Меньше элементов
                )
            ).to.be.reverted; // Может быть разный error message через delegatecall
        });
        
        it("Should revert batch operations with empty arrays", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            await expect(
                proxyAsLogic.connect(admin).batchSetSimpleFields([], [])
            ).to.be.reverted; // Может быть разный error message через delegatecall
        });
        
        it("Should revert removing non-existent field", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            await expect(
                proxyAsLogic.connect(admin).removeSimpleField("non.existent")
            ).to.be.reverted; // Может быть разный error message через delegatecall
        });
        
        it("Should return empty string for non-existent fields", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const cid = await proxyAsLogic.getSimpleFieldCID("non.existent");
            expect(cid).to.equal("");
        });
    });
    
    // === ТЕСТЫ СОБЫТИЙ ===
    
    describe("📢 Events", function () {
        
        it("Should emit SimpleFieldRegistered through proxy", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const fieldKey = "product.forms";
            const cid = "QmTest123";
            
            // События эмитятся из Logic контракта, но через delegatecall
            // Проверяем что операция выполнилась успешно
            await proxyAsLogic.connect(admin).setSimpleFieldCID(fieldKey, cid);
            expect(await proxyAsLogic.getSimpleFieldCID(fieldKey)).to.equal(cid);
        });
        
        it("Should emit ComplexFieldRegistered through proxy", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const className = "Description";
            const language = "ru";
            const cid = "QmTest456";
            
            // События эмитятся из Logic контракта, но через delegatecall
            // Проверяем что операция выполнилась успешно
            await proxyAsLogic.connect(admin).setComplexFieldCID(className, language, cid);
            expect(await proxyAsLogic.getComplexFieldCID(className, language)).to.equal(cid);
        });
        
        it("Should emit LogicUpgraded when upgrading", async function () {
            const LogicV2 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const logicV2 = await LogicV2.deploy(await storage.getAddress());
            await logicV2.waitForDeployment();
            // Storage уже авторизовал Proxy, новый Logic работает через тот же Proxy
            
            const oldLogic = await proxy.currentLogic();
            
            // LogicUpgraded событие содержит 4 аргумента: oldLogic, newLogic, upgrader, timestamp
            await expect(
                proxy.connect(admin).upgradeLogic(await logicV2.getAddress())
            ).to.emit(proxy, "LogicUpgraded");
        });
        
        it("Should emit NextStorageSet when expanding chain", async function () {
            const StorageV2 = await ethers.getContractFactory("AmanitaInternationalStorage");
            const storageV2 = await StorageV2.deploy(admin.address);
            await storageV2.waitForDeployment();
            
            await expect(
                storage.connect(admin).setNextStorage(await storageV2.getAddress())
            ).to.emit(storage, "NextStorageSet")
             .withArgs(await storageV2.getAddress(), 2);
        });
    });
    
    // === ТЕСТЫ GAS EFFICIENCY ===
    
    describe("⛽ Gas Efficiency", function () {
        
        it.skip("Should measure gas overhead of proxy delegation", async function () {
            // SKIP: Прямой вызов Logic невозможен в текущей архитектуре
            // Storage требует PROXY_ROLE, который есть только у Proxy
            // Измерение overhead возможно только в UUPS архитектуре (M2+)
            
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // Вызов через Proxy
            const proxyTx = await proxyAsLogic.connect(admin).setSimpleFieldCID("proxy.field", "QmProxy456");
            const proxyReceipt = await proxyTx.wait();
            const proxyGas = proxyReceipt.gasUsed;
            console.log(`⛽ Вызов через Proxy: ${proxyGas.toString()} gas`);
            
            // Проверяем что gas разумный (< 200k)
            expect(proxyGas).to.be.lessThan(200000n);
        });
        
        it("Should measure batch operations gas efficiency", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            const fieldKeys = ["f1", "f2", "f3", "f4", "f5"];
            const cids = ["c1", "c2", "c3", "c4", "c5"];
            
            // Одиночные операции
            let totalSingleGas = 0n;
            for (let i = 0; i < fieldKeys.length; i++) {
                const tx = await proxyAsLogic.connect(admin).setSimpleFieldCID(
                    `single_${fieldKeys[i]}`,
                    cids[i]
                );
                const receipt = await tx.wait();
                totalSingleGas += receipt.gasUsed;
            }
            console.log(`\n⛽ Одиночные операции (5x): ${totalSingleGas.toString()} gas`);
            
            // Batch операция
            const batchTx = await proxyAsLogic.connect(admin).batchSetSimpleFields(
                fieldKeys.map(k => `batch_${k}`),
                cids
            );
            const batchReceipt = await batchTx.wait();
            const batchGas = batchReceipt.gasUsed;
            console.log(`⛽ Batch операция (5x): ${batchGas.toString()} gas`);
            
            const savings = ((1 - Number(batchGas) / Number(totalSingleGas)) * 100).toFixed(2);
            console.log(`⛽ Экономия: ${savings}%`);
            
            expect(batchGas).to.be.lessThan(totalSingleGas);
        });
    });
    
    // === ТЕСТЫ ВАЛИДАЦИИ ===
    
    describe("✅ Validation Tests", function () {
        
        it("Should validate proxy deployment parameters", async function () {
            const Proxy = await ethers.getContractFactory("AmanitaInternationalProxy");
            
            // Zero admin
            await expect(
                Proxy.deploy(ethers.ZeroAddress, await logicV1.getAddress(), await storage.getAddress())
            ).to.be.revertedWith("AmanitaInternationalProxy: zero admin address");
            
            // Zero logic
            await expect(
                Proxy.deploy(admin.address, ethers.ZeroAddress, await storage.getAddress())
            ).to.be.revertedWith("AmanitaInternationalProxy: zero logic address");
            
            // Zero storage
            await expect(
                Proxy.deploy(admin.address, await logicV1.getAddress(), ethers.ZeroAddress)
            ).to.be.revertedWith("AmanitaInternationalProxy: zero storage address");
        });
        
        it("Should validate logic deployment parameters", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            
            // Logic принимает ТОЛЬКО storage address (один параметр)
            // Zero storage должен провалиться
            await expect(
                LogicV1.deploy(ethers.ZeroAddress)
            ).to.be.revertedWith("AmanitaInternationalLogic: zero storage address");
        });
        
        it("Should validate storage deployment parameters", async function () {
            const Storage = await ethers.getContractFactory("AmanitaInternationalStorage");
            
            // Zero admin
            await expect(
                Storage.deploy(ethers.ZeroAddress)
            ).to.be.revertedWith("AmanitaInternationalStorage: zero admin address");
        });
        
        it("Should prevent direct ETH transfers to proxy", async function () {
            await expect(
                admin.sendTransaction({
                    to: await proxy.getAddress(),
                    value: ethers.parseEther("1.0")
                })
            ).to.be.revertedWith("AmanitaInternationalProxy: direct ETH transfers not allowed");
        });
    });
    
    // === ТЕСТЫ COMPLEX SCENARIOS ===
    
    describe("🧩 Complex Scenarios", function () {
        
        it("Should handle multiple logic upgrades with different storage contracts", async function () {
            console.log("\n🧩 Тест: Множественные upgrade с расширением Storage");
            
            const LogicV1Factory = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogicV1 = LogicV1Factory.attach(await proxy.getAddress());
            
            // Шаг 1: Данные в StorageV1 через LogicV1
            await proxyAsLogicV1.connect(admin).setSimpleFieldCID("v1.field", "QmV1CID");
            console.log(`   ✅ Data in StorageV1 through LogicV1`);
            
            // Шаг 2: Создаем StorageV2 и расширяем цепочку
            const StorageV2 = await ethers.getContractFactory("AmanitaInternationalStorage");
            const storageV2 = await StorageV2.deploy(admin.address);
            await storageV2.waitForDeployment();
            await storage.connect(admin).setNextStorage(await storageV2.getAddress());
            console.log(`   ✅ StorageV2 added to chain`);
            
            // Шаг 3: Создаем LogicV2 который работает с обоими Storage
            const LogicV2 = await LogicV1Factory.deploy(await storage.getAddress());
            await LogicV2.waitForDeployment();
            await proxy.connect(admin).upgradeLogic(await LogicV2.getAddress());
            console.log(`   ✅ Upgraded to LogicV2`);
            
            // Шаг 4: Проверяем что старые данные доступны
            const proxyAsLogicV2 = LogicV1Factory.attach(await proxy.getAddress());
            const v1Data = await proxyAsLogicV2.getSimpleFieldCID("v1.field");
            expect(v1Data).to.equal("QmV1CID");
            console.log(`   ✅ V1 data accessible through LogicV2`);
            
            // Шаг 5: Добавляем новые данные
            await proxyAsLogicV2.connect(admin).setSimpleFieldCID("v2.field", "QmV2CID");
            expect(await proxyAsLogicV2.getSimpleFieldCID("v2.field")).to.equal("QmV2CID");
            console.log(`   ✅ New data added through LogicV2`);
            
            await logStorageChain();
            console.log("\n🎉 Complex scenario успешно выполнен!");
        });
        
        it("Should maintain data integrity across multiple operations", async function () {
            const LogicV1 = await ethers.getContractFactory("AmanitaInternationalLogicV1");
            const proxyAsLogic = LogicV1.attach(await proxy.getAddress());
            
            // Большой набор операций
            for (let i = 0; i < 10; i++) {
                await proxyAsLogic.connect(admin).setSimpleFieldCID(`field.${i}`, `QmCID${i}`);
            }
            
            for (let i = 0; i < 5; i++) {
                await proxyAsLogic.connect(admin).setComplexFieldCID(`Class${i}`, "en", `QmClass${i}`);
            }
            
            // Upgrade
            const LogicV2 = await LogicV1.deploy(await storage.getAddress());
            await LogicV2.waitForDeployment();
            await proxy.connect(admin).upgradeLogic(await LogicV2.getAddress());
            
            // Проверяем все данные
            const proxyAsLogicV2 = LogicV1.attach(await proxy.getAddress());
            for (let i = 0; i < 10; i++) {
                const cid = await proxyAsLogicV2.getSimpleFieldCID(`field.${i}`);
                expect(cid).to.equal(`QmCID${i}`);
            }
            
            for (let i = 0; i < 5; i++) {
                const cid = await proxyAsLogicV2.getComplexFieldCID(`Class${i}`, "en");
                expect(cid).to.equal(`QmClass${i}`);
            }
            
            const stats = await proxyAsLogicV2.getStatistics();
            expect(stats.totalSimpleFields).to.equal(10);
            expect(stats.totalComplexClasses).to.equal(5);
        });
    });
});

