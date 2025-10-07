const { expect } = require("chai");
const { ethers } = require("hardhat");

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
            expect(component.blockchain_id).to.equal(1);
            expect(component.creator).to.equal(user1.address);
            expect(component.status).to.equal(0); // ACTIVE
            expect(component.is_shared).to.be.true;

            // Проверяем строковые данные
            expect(await ocr.componentBusinessIds(1)).to.equal(businessId);
            expect(await ocr.componentRootMetadataCIDs(1)).to.equal(rootMetadataCID);
            expect(await ocr.businessIdToComponentId(businessId)).to.equal(1);
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
            expect(component.last_updated).to.be.greaterThan(component.created_at);
        });

        it("Should increment usage count", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Увеличиваем счетчик использования
            await expect(ocr.incrementUsageCount("test_component"))
                .to.emit(ocr, "ComponentUsageIncremented")
                .withArgs(1, "test_component", 1);

            expect(await ocr.componentUsageCount(1)).to.equal(1);

            // Увеличиваем еще раз
            await ocr.incrementUsageCount("test_component");
            expect(await ocr.componentUsageCount(1)).to.equal(2);
        });

        it("Should add component user", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Добавляем пользователя
            await expect(ocr.addComponentUser("test_component", user2.address))
                .to.emit(ocr, "ComponentUserAdded")
                .withArgs(1, "test_component", user2.address);

            // Проверяем, что пользователь добавлен
            const userComponents = await ocr.getComponentsByUser(user2.address);
            expect(userComponents.length).to.equal(1);
            expect(userComponents[0]).to.equal(1);
        });

        it("Should get component by business ID", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Получаем компонент по business ID
            const component = await ocr.getComponentByBusinessId("test_component");
            expect(component.blockchain_id).to.equal(1);
            expect(component.creator).to.equal(user1.address);
            expect(component.status).to.equal(0); // ACTIVE
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
            await expect(ocr.connect(user1).createComponent("test_component_101", "QmTestCID101"))
                .to.be.revertedWith("OrganicComponentRegistryLogic: component limit exceeded");
        });

        it("Should prevent duplicate business IDs", async function () {
            // Создаем компонент
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Попытка создать компонент с тем же business ID должна провалиться
            await expect(ocr.connect(user1).createComponent("test_component", "QmTestCID456"))
                .to.be.revertedWith("OrganicComponentRegistryLogic: component with this business ID already exists");
        });

        it("Should validate business ID format", async function () {
            // Пустой business ID
            await expect(ocr.connect(user1).createComponent("", "QmTestCID123"))
                .to.be.revertedWith("OrganicComponentRegistryLogic: business ID cannot be empty");

            // Слишком длинный business ID
            const longBusinessId = "a".repeat(65);
            await expect(ocr.connect(user1).createComponent(longBusinessId, "QmTestCID123"))
                .to.be.revertedWith("OrganicComponentRegistryLogic: business ID too long");
        });

        it("Should validate CID format", async function () {
            // Пустой CID
            await expect(ocr.connect(user1).createComponent("test_component", ""))
                .to.be.revertedWith("OrganicComponentRegistryLogic: CID cannot be empty");

            // Слишком длинный CID
            const longCID = "a".repeat(65);
            await expect(ocr.connect(user1).createComponent("test_component", longCID))
                .to.be.revertedWith("OrganicComponentRegistryLogic: CID too long");
        });

        it("Should only allow component creator to update", async function () {
            // Создаем компонент от user1
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // user2 пытается обновить компонент user1
            await expect(ocr.connect(user2).updateComponent(1, "QmNewCID456"))
                .to.be.revertedWith("OrganicComponentRegistryLogic: not component creator");
        });

        it("Should handle multiple components correctly", async function () {
            // Создаем несколько компонентов
            await ocr.connect(user1).createComponent("component1", "QmCID1");
            await ocr.connect(user1).createComponent("component2", "QmCID2");
            await ocr.connect(user1).createComponent("component3", "QmCID3");

            // Проверяем счетчики
            expect(await ocr.totalComponents()).to.equal(3);

            // Проверяем компоненты
            expect(await ocr.businessIdToComponentId("component1")).to.equal(1);
            expect(await ocr.businessIdToComponentId("component2")).to.equal(2);
            expect(await ocr.businessIdToComponentId("component3")).to.equal(3);

            // Проверяем компоненты создателя
            const creatorComponents = await ocr.getComponentsByCreator(user1.address);
            expect(creatorComponents.length).to.equal(3);
        });
    });

    describe("Proxy Management", function () {
        it("Should upgrade logic contract", async function () {
            // Создаем компонент перед upgrade
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");
            expect(await ocr.totalComponents()).to.equal(1);

            // Деплоим новую имплементацию
            const NewLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const newLogicImpl = await NewLogic.deploy();
            await newLogicImpl.waitForDeployment();

            // Апгрейд через Logic ABI на proxy address (используем upgradeToAndCall)
            await ocr.connect(admin).upgradeToAndCall(await newLogicImpl.getAddress(), "0x");

            // Проверяем, что данные сохранились после апгрейда
            expect(await ocr.totalComponents()).to.equal(1);
            expect(await ocr.componentExists("test_component")).to.be.true;
            
            // Проверяем, что компонент доступен
            const component = await ocr.getComponent(1);
            expect(component.blockchain_id).to.equal(1);
            expect(await ocr.componentBusinessIds(1)).to.equal("test_component");
        });

        it("Should pause and unpause contract", async function () {
            // Создаем компонент
            await ocr.connect(user1).createComponent("test_component", "QmTestCID123");

            // Останавливаем контракт через Logic (admin роль)
            await ocr.connect(admin).pause();

            // Попытка создать компонент должна провалиться (OZ v5 custom error)
            await expect(ocr.connect(user1).createComponent("test_component2", "QmTestCID456"))
                .to.be.revertedWithCustomError(ocr, "EnforcedPause");

            // Возобновляем работу через Logic
            await ocr.connect(admin).unpause();

            // Теперь создание должно работать
            await ocr.connect(user1).createComponent("test_component2", "QmTestCID456");
            expect(await ocr.totalComponents()).to.equal(2);
        });

        it("Should restrict pause/unpause to ADMIN_ROLE only", async function () {
            // user1 НЕ может ставить на паузу (нет ADMIN_ROLE)
            await expect(
                ocr.connect(user1).pause()
            ).to.be.reverted;
            
            // admin МОЖЕТ ставить на паузу
            await ocr.connect(admin).pause();
            
            // Проверяем, что контракт на паузе
            await expect(
                ocr.connect(user1).createComponent("test", "QmTest")
            ).to.be.revertedWithCustomError(ocr, "EnforcedPause");
            
            // user1 НЕ может снимать с паузы
            await expect(
                ocr.connect(user1).unpause()
            ).to.be.reverted;
            
            // admin МОЖЕТ снимать с паузы
            await ocr.connect(admin).unpause();
            
            // Проверяем, что контракт работает
            await ocr.connect(user1).createComponent("test", "QmTest");
            expect(await ocr.totalComponents()).to.equal(1);
        });

        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            // Деплоим новую имплементацию
            const NewLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const newLogicImpl = await NewLogic.deploy();
            await newLogicImpl.waitForDeployment();
            
            // user1 НЕ может апгрейдить (нет UPGRADER_ROLE)
            await expect(
                ocr.connect(user1).upgradeToAndCall(await newLogicImpl.getAddress(), "0x")
            ).to.be.reverted;
            
            // user2 НЕ может апгрейдить (нет UPGRADER_ROLE)
            await expect(
                ocr.connect(user2).upgradeToAndCall(await newLogicImpl.getAddress(), "0x")
            ).to.be.reverted;
            
            // admin МОЖЕТ апгрейдить (имеет UPGRADER_ROLE)
            await ocr.connect(admin).upgradeToAndCall(await newLogicImpl.getAddress(), "0x");
            
            // Проверяем, что апгрейд выполнен (контракт работает)
            await ocr.connect(user1).createComponent("test_after_upgrade", "QmTestAfterUpgrade");
            expect(await ocr.totalComponents()).to.equal(1);
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
            
            // user1 НЕ может устанавливать SpiralEngine (нет ADMIN_ROLE)
            await expect(
                ocr.connect(user1).setSpiralEngine(await newSpiralEngine.getAddress())
            ).to.be.reverted;
            
            // user1 НЕ может устанавливать AmanitaInternational
            await expect(
                ocr.connect(user1).setAmanitaInternational(await newSpiralEngine.getAddress())
            ).to.be.reverted;
            
            // user1 НЕ может устанавливать ProductRegistry
            await expect(
                ocr.connect(user1).setProductRegistry(await newSpiralEngine.getAddress())
            ).to.be.reverted;
            
            // admin МОЖЕТ устанавливать (имеет ADMIN_ROLE)
            await ocr.connect(admin).setSpiralEngine(await newSpiralEngine.getAddress());
            expect(await ocr.spiralEngine()).to.equal(await newSpiralEngine.getAddress());
            
            // Возвращаем старое значение для других тестов
            await ocr.connect(admin).setSpiralEngine(await spiralEngine.getAddress());
        });

        it("Should reject zero addresses for integrations", async function () {
            // Попытка установить нулевой адрес должна провалиться
            await expect(
                ocr.connect(admin).setSpiralEngine(ethers.ZeroAddress)
            ).to.be.revertedWith("OrganicComponentRegistryLogic: invalid address");
            
            await expect(
                ocr.connect(admin).setAmanitaInternational(ethers.ZeroAddress)
            ).to.be.revertedWith("OrganicComponentRegistryLogic: invalid address");
            
            await expect(
                ocr.connect(admin).setProductRegistry(ethers.ZeroAddress)
            ).to.be.revertedWith("OrganicComponentRegistryLogic: invalid address");
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

            // Проверяем обновленные данные
            expect(await ocr.getFeaturesCID()).to.equal(featuresCID);
            expect(await ocr.getComponentFormsCID()).to.equal(formsCID);
            expect(await ocr.getFeaturesVersion()).to.equal(featuresVersion);
            expect(await ocr.getComponentFormsVersion()).to.equal(formsVersion);
        });

        it("Should restrict updateShareableData to ADMIN_ROLE only", async function () {
            // user1 НЕ может обновлять shareable данные (нет ADMIN_ROLE)
            await expect(
                ocr.connect(user1).updateShareableData(
                    "QmFeatures",
                    "QmForms",
                    1,
                    1
                )
            ).to.be.reverted;
            
            // admin МОЖЕТ обновлять shareable данные
            await ocr.connect(admin).updateShareableData(
                "QmFeatures",
                "QmForms",
                1,
                1
            );
            
            expect(await ocr.getFeaturesCID()).to.equal("QmFeatures");
        });

        it("Should validate CIDs in shareable data", async function () {
            // Пустой features CID должен быть отклонен
            await expect(
                ocr.connect(admin).updateShareableData(
                    "",
                    "QmForms",
                    1,
                    1
                )
            ).to.be.revertedWith("OrganicComponentRegistryLogic: CID cannot be empty");
            
            // Пустой forms CID должен быть отклонен
            await expect(
                ocr.connect(admin).updateShareableData(
                    "QmFeatures",
                    "",
                    1,
                    1
                )
            ).to.be.revertedWith("OrganicComponentRegistryLogic: CID cannot be empty");
            
            // Слишком длинный features CID должен быть отклонен
            const longCID = "a".repeat(65);
            await expect(
                ocr.connect(admin).updateShareableData(
                    longCID,
                    "QmForms",
                    1,
                    1
                )
            ).to.be.revertedWith("OrganicComponentRegistryLogic: CID too long");
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
            // user1 НЕ может выдавать роли (нет DEFAULT_ADMIN_ROLE)
            await expect(
                ocr.connect(user1).grantRole(await ocr.CONTRIBUTOR_ROLE(), user3.address)
            ).to.be.reverted;
            
            // admin МОЖЕТ выдавать роли
            await ocr.connect(admin).grantRole(await ocr.CONTRIBUTOR_ROLE(), user3.address);
            expect(await ocr.hasRole(await ocr.CONTRIBUTOR_ROLE(), user3.address)).to.be.true;
        });
    });
});
