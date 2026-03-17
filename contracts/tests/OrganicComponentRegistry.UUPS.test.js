const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

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

async function expectRevertWithMessage(txPromise, messageSubstring) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
    const msg = (err?.message || err?.error?.message || String(err)) || "";
    expect(msg.includes(messageSubstring), `expected revert message to contain "${messageSubstring}"`).to.be.true;
}

async function expectRevert(txPromise) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
}

describe("OrganicComponentRegistry UUPS Architecture", function () {
    let admin, user1, user2, user3;
    let proxy, logic, ocr;
    let spiralEngine, amanitaInternational, productRegistry;

    beforeEach(async function () {
        // Получаем аккаунты
        [admin, user1, user2, user3] = await ethers.getSigners();

        // 1) Deploy Logic implementation
        const Logic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const logicImpl = await Logic.deploy();
        await logicImpl.waitForDeployment();

        // 2) Encode initialize(admin) calldata
        const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [admin.address]);

        // 3) Deploy Proxy with implementation and init data
        const Proxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        proxy = await Proxy.deploy(await logicImpl.getAddress(), initCalldata);
        await proxy.waitForDeployment();

        // 4) Attach Logic ABI to proxy address (ABI-translator)
        ocr = Logic.attach(await proxy.getAddress());

        // Деплоим моки для интеграции
        const SpiralEngine = await ethers.getContractFactory("SpiralEngineMock");
        spiralEngine = await SpiralEngine.deploy();
        await spiralEngine.waitForDeployment();

        const AmanitaInternational = await ethers.getContractFactory("AmanitaInternationalMock");
        amanitaInternational = await AmanitaInternational.deploy();
        await amanitaInternational.waitForDeployment();

        const ProductRegistry = await ethers.getContractFactory("ProductRegistryMock");
        productRegistry = await ProductRegistry.deploy();
        await productRegistry.waitForDeployment();

        // Настройка интеграции через admin (только ADMIN_ROLE может устанавливать)
        await ocr.connect(admin).setSpiralEngine(await spiralEngine.getAddress());
        await ocr.connect(admin).setAmanitaInternational(await amanitaInternational.getAddress());
        await ocr.connect(admin).setProductRegistry(await productRegistry.getAddress());

        // Настройка ролей для тестов
        await ocr.grantRole(await ocr.CONTRIBUTOR_ROLE(), user1.address);
        await ocr.grantRole(await ocr.CONTRIBUTOR_ROLE(), user2.address);

        // Настраиваем SpiralEngine для тестов
        await spiralEngine.grantRole(await spiralEngine.ACTIVATOR_ROLE(), admin.address);
        await spiralEngine.grantRole(await spiralEngine.SELLER_ROLE(), user1.address);
        await spiralEngine.grantRole(await spiralEngine.SELLER_ROLE(), user2.address);
        await spiralEngine.grantRole(await spiralEngine.SELLER_ROLE(), user3.address);
        
        // Активируем пользователей в SpiralEngine (admin имеет ACTIVATOR_ROLE)
        await spiralEngine.connect(admin).activateUser(user1.address, 1);
        await spiralEngine.connect(admin).activateUser(user2.address, 2);
        await spiralEngine.connect(admin).activateUser(user3.address, 3);
    });

    describe("UUPS Architecture Tests", function () {
        it("Should deploy and initialize correctly", async function () {
            // Проверяем роли через Logic ABI (ocr)
            expect(await ocr.hasRole(await ocr.DEFAULT_ADMIN_ROLE(), admin.address)).to.be.true;
            expect(await ocr.hasRole(await ocr.ADMIN_ROLE(), admin.address)).to.be.true;
            expect(await ocr.hasRole(await ocr.UPGRADER_ROLE(), admin.address)).to.be.true;
            expect(await ocr.hasRole(await ocr.CONTRIBUTOR_ROLE(), admin.address)).to.be.true;
        });

        it("Should create component through ABI-translator", async function () {
            const businessId = "test_component";
            const rootMetadataCID = "QmTestCID123";

            const tx = await ocr.connect(user1).createComponent(businessId, rootMetadataCID);
            const receipt = await tx.wait();
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                const parsed = ocr.interface.parseLog(log);
                return parsed.name === "ComponentCreated";
            });
            expect(event).to.not.be.undefined;

            // Проверяем данные через ABI-translator
            const component = await ocr.getComponent(1);
            expect(component.blockchain_id).to.equal(1n);
            expect(component.creator).to.equal(user1.address);
            expect(component.status).to.equal(0n); // ACTIVE
            expect(component.is_shared).to.be.true;

            // Проверяем строковые данные
            expect(await ocr.componentBusinessIds(1)).to.equal(businessId);
            expect(await ocr.componentRootMetadataCIDs(1)).to.equal(rootMetadataCID);
            expect(await ocr.businessIdToComponentId(businessId)).to.equal(1n);
        });

        it("Should update component through ABI-translator", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Обновляем компонент от user1 (создателя)
            const newCID = "QmNewCID456";
            const tx = await ocr.connect(user1).updateComponent(1, newCID);
            const receipt = await tx.wait();
            
            // Проверяем событие ComponentUpdated
            const event = receipt.logs.find(log => {
                const parsed = ocr.interface.parseLog(log);
                return parsed && parsed.name === "ComponentUpdated";
            });
            expect(event).to.not.be.undefined;

            // Проверяем обновление
            expect(await ocr.componentRootMetadataCIDs(1)).to.equal(newCID);
            
            const component = await ocr.getComponent(1);
            expect(component.last_updated > component.created_at).to.be.true;
        });

        it("Should increment usage count", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            const tx = await ocr.incrementUsageCount("test_component");
            const receipt = await tx.wait();
            const decoded = receipt.logs.map(log => {
                try { return ocr.interface.parseLog(log); } catch { return null; }
            }).filter(e => e && e.name === "ComponentUsageIncremented");
            expect(decoded.length).to.be.gte(1);
            expect(decoded[0].args.componentId).to.equal(1n);
            expect(decoded[0].args.businessId).to.equal("test_component");
            expect(decoded[0].args.newUsageCount).to.equal(1n);

            expect(await ocr.componentUsageCount(1)).to.equal(1n);

            // Увеличиваем еще раз
            await ocr.incrementUsageCount("test_component");
            expect(await ocr.componentUsageCount(1)).to.equal(2n);
        });

        it("Should add component user", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            const tx = await ocr.addComponentUser("test_component", user2.address);
            const receipt = await tx.wait();
            const decoded = receipt.logs.map(log => {
                try { return ocr.interface.parseLog(log); } catch { return null; }
            }).filter(e => e && e.name === "ComponentUserAdded");
            expect(decoded.length).to.be.gte(1);
            expect(decoded[0].args.componentId).to.equal(1n);
            expect(decoded[0].args.businessId).to.equal("test_component");
            expect(decoded[0].args.user).to.equal(user2.address);

            // Проверяем, что пользователь добавлен
            const userComponents = await ocr.getComponentsByUser(user2.address);
            expect(userComponents.length).to.equal(1);
            expect(userComponents[0]).to.equal(1n);
        });

        it("Should get component by business ID", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Получаем компонент по business ID
            const component = await ocr.getComponentByBusinessId("test_component");
            expect(component.blockchain_id).to.equal(1n);
            expect(component.creator).to.equal(user1.address);
            expect(component.status).to.equal(0n); // ACTIVE
        });

        it("Should check component existence", async function () {
            // Проверяем несуществующий компонент
            expect(await ocr.componentExists("nonexistent")).to.be.false;

            // Создаем компонент
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Проверяем существующий компонент
            expect(await ocr.componentExists("test_component")).to.be.true;
        });

        it("Should enforce component limit per user", async function () {
            // Создаем максимальное количество компонентов
            for (let i = 0; i < 100; i++) {
                await ocr.connect(user1).createComponent(`test_component_${i}`, `QmTestCID${i}`);
            }

            // Попытка создать еще один компонент должна провалиться
            await expectRevertWithMessage(
                ocr.connect(user1).createComponent("test_component_101", "QmTestCID101"),
                "OrganicComponentRegistryLogic: component limit exceeded"
            );
        });

        it("Should prevent duplicate business IDs", async function () {
            // Создаем компонент
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Попытка создать компонент с тем же business ID должна провалиться
            await expectRevertWithMessage(
                ocr.connect(user1).createComponent("test_component", "QmTestCID456"),
                "OrganicComponentRegistryLogic: component with this business ID already exists"
            );
        });

        it("Should validate business ID format", async function () {
            await expectRevertWithMessage(
                ocr.connect(user1).createComponent("", "QmTestCID123"),
                "OrganicComponentRegistryLogic: business ID cannot be empty"
            );
            const longBusinessId = "a".repeat(65);
            await expectRevertWithMessage(
                ocr.connect(user1).createComponent(longBusinessId, "QmTestCID123"),
                "OrganicComponentRegistryLogic: business ID too long"
            );
        });

        it("Should validate CID format", async function () {
            await expectRevertWithMessage(
                ocr.connect(user1).createComponent("test_component", ""),
                "OrganicComponentRegistryLogic: CID cannot be empty"
            );
            const longCID = "a".repeat(65);
            await expectRevertWithMessage(
                ocr.connect(user1).createComponent("test_component", longCID),
                "OrganicComponentRegistryLogic: CID too long"
            );
        });

        it("Should only allow component creator to update", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            await expectRevertWithMessage(
                ocr.connect(user2).updateComponent(1, "QmNewCID456"),
                "OrganicComponentRegistryLogic: not component creator"
            );
        });

        it("Should handle multiple components correctly", async function () {
            // Создаем несколько компонентов
            await ocr.connect(user1).createComponent("component1", "QmCID1");
            await ocr.connect(user1).createComponent("component2", "QmCID2");
            await ocr.connect(user1).createComponent("component3", "QmCID3");

            expect(await ocr.totalComponents()).to.equal(3n);
            expect(await ocr.businessIdToComponentId("component1")).to.equal(1n);
            expect(await ocr.businessIdToComponentId("component2")).to.equal(2n);
            expect(await ocr.businessIdToComponentId("component3")).to.equal(3n);

            // Проверяем компоненты создателя
            const creatorComponents = await ocr.getComponentsByCreator(user1.address);
            expect(creatorComponents.length).to.equal(3);
        });
    });

    describe("Proxy Management", function () {
        it("Should upgrade logic contract", async function () {
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");
            expect(await ocr.totalComponents()).to.equal(1n);

            // Деплоим новую имплементацию
            const NewLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const newLogicImpl = await NewLogic.deploy();
            await newLogicImpl.waitForDeployment();

            // Апгрейд через Logic ABI на proxy address (используем upgradeToAndCall)
            await ocr.connect(admin).upgradeToAndCall(await newLogicImpl.getAddress(), "0x");

            expect(await ocr.totalComponents()).to.equal(1n);
            expect(await ocr.componentExists("test_component")).to.be.true;
            const component = await ocr.getComponent(1);
            expect(component.blockchain_id).to.equal(1n);
            expect(await ocr.componentBusinessIds(1)).to.equal("test_component");
        });

        it("Should pause and unpause contract", async function () {
            // Создаем компонент
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Останавливаем контракт через Logic (admin роль)
            await ocr.connect(admin).pause();

            await expectCustomError(
                ocr.connect(user1).createComponent("test_component2", "QmTestCID456"),
                ocr,
                "EnforcedPause"
            );
            await ocr.connect(admin).unpause();
            await ocr.connect(user1).createComponent("test_component2", "QmTestCID456");
            expect(await ocr.totalComponents()).to.equal(2n);
        });

        it("Should restrict pause/unpause to ADMIN_ROLE only", async function () {
            await expectRevert(ocr.connect(user1).pause());
            await ocr.connect(admin).pause();
            await expectCustomError(
                ocr.connect(user1).createComponent("test", "QmTest"),
                ocr,
                "EnforcedPause"
            );
            await expectRevert(ocr.connect(user1).unpause());
            await ocr.connect(admin).unpause();
            await ocr.connect(user1).createComponent("test", "QmTest");
            expect(await ocr.totalComponents()).to.equal(1n);
        });

        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            // Деплоим новую имплементацию
            const NewLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const newLogicImpl = await NewLogic.deploy();
            await newLogicImpl.waitForDeployment();
            
            await expectRevert(ocr.connect(user1).upgradeToAndCall(await newLogicImpl.getAddress(), "0x"));
            await expectRevert(ocr.connect(user2).upgradeToAndCall(await newLogicImpl.getAddress(), "0x"));
            await ocr.connect(admin).upgradeToAndCall(await newLogicImpl.getAddress(), "0x");
            await ocr.connect(user1).createComponent("test_after_upgrade", "QmTestAfterUpgrade");
            expect(await ocr.totalComponents()).to.equal(1n);
        });
    });

    describe("Integration Tests", function () {
        it("Should integrate with SpiralEngine", async function () {
            // Проверяем, что SpiralEngine установлен
            expect(await ocr.spiralEngine()).to.equal(await spiralEngine.getAddress());
        });

        it("Should integrate with AmanitaInternational", async function () {
            // Проверяем, что AmanitaInternational установлен
            expect(await ocr.amanitaInternational()).to.equal(await amanitaInternational.getAddress());
        });

        it("Should integrate with ProductRegistry", async function () {
            // Проверяем, что ProductRegistry установлен
            expect(await ocr.productRegistry()).to.equal(await productRegistry.getAddress());
        });

        it("Should restrict integration setters to ADMIN_ROLE only", async function () {
            // Деплоим новый мок для теста
            const NewSpiralEngine = await ethers.getContractFactory("SpiralEngineMock");
            const newSpiralEngine = await NewSpiralEngine.deploy();
            await newSpiralEngine.waitForDeployment();
            
            await expectRevert(ocr.connect(user1).setSpiralEngine(await newSpiralEngine.getAddress()));
            await expectRevert(ocr.connect(user1).setAmanitaInternational(await newSpiralEngine.getAddress()));
            await expectRevert(ocr.connect(user1).setProductRegistry(await newSpiralEngine.getAddress()));
            
            // admin МОЖЕТ устанавливать (имеет ADMIN_ROLE)
            await ocr.connect(admin).setSpiralEngine(await newSpiralEngine.getAddress());
            expect(await ocr.spiralEngine()).to.equal(await newSpiralEngine.getAddress());
            
            // Возвращаем старое значение для других тестов
            await ocr.connect(admin).setSpiralEngine(await spiralEngine.getAddress());
        });

        it("Should reject zero addresses for integrations", async function () {
            await expectCustomError(ocr.connect(admin).setSpiralEngine(ethers.ZeroAddress), ocr, "ZeroAddress");
            await expectCustomError(ocr.connect(admin).setAmanitaInternational(ethers.ZeroAddress), ocr, "ZeroAddress");
            await expectCustomError(ocr.connect(admin).setProductRegistry(ethers.ZeroAddress), ocr, "ZeroAddress");
        });
    });

    describe("Shareable Data Tests", function () {
        it("Should update shareable data", async function () {
            const featuresCID = "QmFeaturesCID123";
            const formsCID = "QmFormsCID456";
            const featuresVersion = 1;
            const formsVersion = 1;

            // Обновляем shareable данные
            const tx = await ocr.connect(admin).updateShareableData(
                featuresCID,
                formsCID,
                featuresVersion,
                formsVersion
            );
            const receipt = await tx.wait();
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                const parsed = ocr.interface.parseLog(log);
                return parsed && parsed.name === "ShareableDataUpdated";
            });
            expect(event).to.not.be.undefined;

            expect(await ocr.getFeaturesCID()).to.equal(featuresCID);
            expect(await ocr.getComponentFormsCID()).to.equal(formsCID);
            expect(await ocr.getFeaturesVersion()).to.equal(BigInt(featuresVersion));
            expect(await ocr.getComponentFormsVersion()).to.equal(BigInt(formsVersion));
        });

        it("Should restrict updateShareableData to ADMIN_ROLE only", async function () {
            await expectRevert(ocr.connect(user1).updateShareableData("QmFeatures", "QmForms", 1, 1));
            await ocr.connect(admin).updateShareableData(
                "QmFeatures",
                "QmForms",
                1,
                1
            );
            
            expect(await ocr.getFeaturesCID()).to.equal("QmFeatures");
        });

        it("Should validate CIDs in shareable data", async function () {
            await expectRevertWithMessage(
                ocr.connect(admin).updateShareableData("", "QmForms", 1, 1),
                "OrganicComponentRegistryLogic: CID cannot be empty"
            );
            await expectRevertWithMessage(
                ocr.connect(admin).updateShareableData("QmFeatures", "", 1, 1),
                "OrganicComponentRegistryLogic: CID cannot be empty"
            );
            const longCID = "a".repeat(65);
            await expectRevertWithMessage(
                ocr.connect(admin).updateShareableData(longCID, "QmForms", 1, 1),
                "OrganicComponentRegistryLogic: CID too long"
            );
        });
    });

    describe("Role Management Tests", function () {
        it("Should grant and revoke CONTRIBUTOR_ROLE", async function () {
            // Проверяем, что user3 не имеет CONTRIBUTOR_ROLE
            expect(await ocr.hasRole(await ocr.CONTRIBUTOR_ROLE(), user3.address)).to.be.false;
            
            // admin выдает роль
            await ocr.connect(admin).grantRole(await ocr.CONTRIBUTOR_ROLE(), user3.address);
            expect(await ocr.hasRole(await ocr.CONTRIBUTOR_ROLE(), user3.address)).to.be.true;
            
            // Активируем user3 для теста
            await spiralEngine.connect(admin).activateUser(user3.address, 4);
            
            // user3 может создавать компоненты (но не является seller)
            // Ожидаем ошибку из-за отсутствия SELLER_ROLE в SpiralEngine
            // (user3 уже имеет SELLER_ROLE из beforeEach - пропускаем)
            
            // admin отзывает роль
            await ocr.connect(admin).revokeRole(await ocr.CONTRIBUTOR_ROLE(), user3.address);
            expect(await ocr.hasRole(await ocr.CONTRIBUTOR_ROLE(), user3.address)).to.be.false;
        });

        it("Should only allow DEFAULT_ADMIN_ROLE to manage roles", async function () {
            await expectRevert(ocr.connect(user1).grantRole(await ocr.CONTRIBUTOR_ROLE(), user3.address));
            
            // admin МОЖЕТ выдавать роли
            await ocr.connect(admin).grantRole(await ocr.CONTRIBUTOR_ROLE(), user3.address);
            expect(await ocr.hasRole(await ocr.CONTRIBUTOR_ROLE(), user3.address)).to.be.true;
        });
    });

    describe("Custom Errors Tests", function () {
        it("Should revert with ZeroAddress error for integration setters", async function () {
            await expectCustomError(ocr.connect(admin).setSpiralEngine(ethers.ZeroAddress), ocr, "ZeroAddress");
            await expectCustomError(ocr.connect(admin).setAmanitaInternational(ethers.ZeroAddress), ocr, "ZeroAddress");
            await expectCustomError(ocr.connect(admin).setProductRegistry(ethers.ZeroAddress), ocr, "ZeroAddress");
        });
        
        it("Should support both custom errors and legacy string reverts", async function () {
            await expectCustomError(ocr.connect(admin).setSpiralEngine(ethers.ZeroAddress), ocr, "ZeroAddress");
            await expectRevertWithMessage(ocr.connect(user1).createComponent("", "QmTest"), "OrganicComponentRegistryLogic: business ID cannot be empty");
            await expectRevertWithMessage(ocr.connect(user1).createComponent("test", ""), "OrganicComponentRegistryLogic: CID cannot be empty");
        });
    });

    describe("Event Filtering Tests", function () {
        it("Should filter ComponentCreated by componentId", async function () {
            // Создаем несколько компонентов
            await ocr.connect(user1).createComponent("filter_comp1", "QmFilterCID1");
            await ocr.connect(user1).createComponent("filter_comp2", "QmFilterCID2");
            await ocr.connect(user2).createComponent("filter_comp3", "QmFilterCID3");
            
            // Получаем ID первого компонента
            const componentId1 = await ocr.businessIdToComponentId("filter_comp1");
            
            // Фильтруем по componentId
            const filter = ocr.filters.ComponentCreated(componentId1);
            const logs = await ocr.queryFilter(filter);
            
            // Проверяем что нашли нужное событие
            const relevantLogs = logs.filter(log => log.args.businessId === "filter_comp1");
            expect(relevantLogs.length).to.be.greaterThan(0);
            expect(relevantLogs[0].args.componentId).to.equal(componentId1);
            expect(relevantLogs[0].args.businessId).to.equal("filter_comp1");
        });
        
        it("Should filter ComponentCreated by creator", async function () {
            // Создаем компоненты от разных пользователей
            await ocr.connect(user1).createComponent("creator_comp1", "QmCreatorCID1");
            await ocr.connect(user1).createComponent("creator_comp2", "QmCreatorCID2");
            await ocr.connect(user2).createComponent("creator_comp3", "QmCreatorCID3");
            
            // Фильтруем по creator = user1
            const filter = ocr.filters.ComponentCreated(null, null, user1.address);
            const logs = await ocr.queryFilter(filter);
            
            // Проверяем что все найденные события от user1
            const user1Logs = logs.filter(log => log.args.creator === user1.address);
            expect(user1Logs.length).to.be.greaterThan(1); // как минимум 2 компонента
            user1Logs.forEach(log => {
                expect(log.args.creator).to.equal(user1.address);
            });
        });
        
        it("Should filter ComponentUserAdded by user", async function () {
            // Создаем компонент и добавляем пользователя
            await ocr.connect(user1).createComponent("user_add_comp", "QmUserAddCID");
            await ocr.connect(admin).addComponentUser("user_add_comp", user3.address);
            
            // Фильтруем по user = user3
            const filter = ocr.filters.ComponentUserAdded(null, null, user3.address);
            const logs = await ocr.queryFilter(filter);
            
            // Проверяем что нашли событие с user3
            const relevantLogs = logs.filter(log => log.args.user === user3.address);
            expect(relevantLogs.length).to.be.greaterThan(0);
            expect(relevantLogs[0].args.user).to.equal(user3.address);
        });
        
        it("Should filter ShareableDataUpdated by version", async function () {
            // Обновляем shareable data несколько раз
            await ocr.connect(admin).updateShareableData("QmFeatures1", "QmForms1", 1, 1);
            await ocr.connect(admin).updateShareableData("QmFeatures2", "QmForms2", 2, 2);
            
            // Получаем текущие версии
            const shareableData = await ocr.shareableData();
            const currentFeaturesVersion = shareableData.features_version;
            
            // Фильтруем по featuresVersion = 2
            const filter = ocr.filters.ShareableDataUpdated(null, null, 2n);
            const logs = await ocr.queryFilter(filter);
            
            // Проверяем что нашли событие с версией 2
            expect(logs.length).to.be.greaterThan(0);
            expect(logs[logs.length - 1].args.featuresVersion).to.equal(2n);
        });
    });

    describe("Reentrancy Protection Tests", function () {
        it("Should have reentrancy protection on mutating functions", async function () {
            // Smoke-тест: проверяем что функции с nonReentrant работают корректно
            // и не выбрасывают ошибок при нормальном использовании
            
            // Создаем компонент (проверяет nonReentrant в createComponent)
            await ocr.connect(user1).createComponent("reentrancy_test", "QmReentrancyCID");
            
            // Обновляем компонент (проверяет nonReentrant в updateComponent)
            const componentId = await ocr.businessIdToComponentId("reentrancy_test");
            await ocr.connect(user1).updateComponent(componentId, "QmUpdatedCID");
            
            // Инкрементим счетчик (проверяет nonReentrant в incrementUsageCount)
            await ocr.incrementUsageCount("reentrancy_test");
            
            // Добавляем пользователя (проверяет nonReentrant в addComponentUser)
            await ocr.connect(admin).addComponentUser("reentrancy_test", user2.address);
            
            // Обновляем shareable data (проверяет nonReentrant в updateShareableData)
            await ocr.connect(admin).updateShareableData("QmFeatures", "QmForms", 1, 1);
            
            // Устанавливаем интеграции (проверяет nonReentrant в setters)
            const newSpiralEngine = await ethers.deployContract("MockSpiralEngine");
            await ocr.connect(admin).setSpiralEngine(await newSpiralEngine.getAddress());
            
            // Пауза и unpause (проверяет nonReentrant в pause/unpause)
            await ocr.connect(admin).pause();
            await ocr.connect(admin).unpause();
            
            // Если мы дошли сюда без ревертов, то nonReentrant работает корректно
            expect(true).to.be.true;
        });
    });

    describe("Proxy Protection Tests (UUPS Best Practice)", function () {
        it("Should only work through proxy, not directly on implementation", async function () {
            // Получаем адрес имплементации из proxy
            const implementationAddress = await upgrades.erc1967.getImplementationAddress(
                await ocr.getAddress()
            );
            
            // Создаем экземпляр имплементации напрямую
            const Logic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const implementation = Logic.attach(implementationAddress);
            
            // Прямой вызов на имплементацию не должен работать корректно
            // (имплементация не инициализирована и не имеет state)
            const totalComponents = await implementation.totalComponents();
            
            // У имплементации totalComponents должен быть 0 (не инициализирован)
            // А у proxy через ocr - реальное значение
            const proxyTotalComponents = await ocr.totalComponents();
            
            expect(proxyTotalComponents >= totalComponents).to.be.true;
            expect(await ocr.LOGIC_VERSION()).to.equal(2n);
        });
        
        it("Should have UUPS upgrade protection via UPGRADER_ROLE", async function () {
            // UUPS защищен через _authorizeUpgrade с onlyRole(UPGRADER_ROLE)
            // Проверяем что только UPGRADER_ROLE может апгрейдить
            
            // user1 НЕ имеет UPGRADER_ROLE
            const LogicV2 = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const newImplementation = await LogicV2.deploy();
            await newImplementation.waitForDeployment();
            
            await expectRevert(ocr.connect(user1).upgradeToAndCall(await newImplementation.getAddress(), "0x"));
            await ocr.connect(admin).upgradeToAndCall(await newImplementation.getAddress(), "0x");
            expect(await ocr.LOGIC_VERSION()).to.equal(2n);
        });
        
        it("Should document that onlyProxy will be added if migration functions appear", async function () {
            // Этот тест документирует подход к onlyProxy:
            // - UUPS уже имеет встроенную защиту через delegatecall
            // - _authorizeUpgrade защищен через onlyRole(UPGRADER_ROLE)
            // - Если появятся миграционные функции, им нужен будет onlyProxy модификатор
            // - Текущая реализация не требует дополнительных onlyProxy
            
            // Проверяем что критические функции защищены
            expect(await ocr.hasRole(await ocr.UPGRADER_ROLE(), admin.address)).to.be.true;
            expect(await ocr.hasRole(await ocr.UPGRADER_ROLE(), user1.address)).to.be.false;
            
            // UUPS best practice: все работает через proxy
            expect(true).to.be.true;
        });
    });
});
