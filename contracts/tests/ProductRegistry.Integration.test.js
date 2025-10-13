const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * 🔗 ProductRegistry ↔ OrganicComponentRegistry - Integration Tests
 * 
 * Цель: Тестирование интеграции ProductRegistry v2.0 с OrganicComponentRegistry
 * 
 * Проверяемые элементы:
 * - ✅ Настройка componentRegistry
 * - ✅ Создание продуктов с валидными компонентами
 * - ✅ Валидация компонентов (существование)
 * - ✅ Tracking usage (incrementUsageCount)
 * - ✅ Tracking users (addComponentUser)
 * - ✅ getProductComponents()
 * - ✅ Edge cases (пустой массив, лимиты, несуществующие компоненты)
 * - ✅ Gas cost метрики
 */

describe("🔗 ProductRegistry ↔ OrganicComponentRegistry Integration", function () {
    let admin, seller, otherSeller, user1;
    let productRegistry, componentRegistry;
    let spiralEngine;
    let SELLER_ROLE, CONTRIBUTOR_ROLE;

    beforeEach(async function () {
        [admin, seller, otherSeller, user1] = await ethers.getSigners();
        
        console.log("\n🔗 Integration Test Setup Starting...");
        
        // ===== Deploy Mock SpiralEngine =====
        console.log("🔷 Deploying Mock SpiralEngine...");
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();
        console.log(`   ✅ Mock SpiralEngine deployed: ${await spiralEngine.getAddress()}`);
        
        // ===== Deploy OrganicComponentRegistry UUPS =====
        console.log("🔷 Deploying OrganicComponentRegistry UUPS...");
        
        const OCRLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const ocrLogic = await OCRLogic.deploy();
        await ocrLogic.waitForDeployment();
        console.log(`   ✅ OCR Logic deployed: ${await ocrLogic.getAddress()}`);
        
        const ocrInitCalldata = ocrLogic.interface.encodeFunctionData("initialize", [admin.address]);
        
        const OCRProxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const ocrProxy = await OCRProxy.deploy(await ocrLogic.getAddress(), ocrInitCalldata);
        await ocrProxy.waitForDeployment();
        console.log(`   ✅ OCR Proxy deployed: ${await ocrProxy.getAddress()}`);
        
        componentRegistry = OCRLogic.attach(await ocrProxy.getAddress());
        
        // Настраиваем OCR
        await componentRegistry.connect(admin).setSpiralEngine(await spiralEngine.getAddress());
        console.log("   ✅ OCR configured with SpiralEngine");
        
        // ===== Deploy ProductRegistry UUPS =====
        console.log("🔷 Deploying ProductRegistry UUPS...");
        
        const PRLogic = await ethers.getContractFactory("ProductRegistryLogic");
        const prLogic = await PRLogic.deploy();
        await prLogic.waitForDeployment();
        console.log(`   ✅ PR Logic deployed: ${await prLogic.getAddress()}`);
        
        const prInitCalldata = prLogic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        
        const PRProxy = await ethers.getContractFactory("ProductRegistryProxy");
        const prProxy = await PRProxy.deploy(await prLogic.getAddress(), prInitCalldata);
        await prProxy.waitForDeployment();
        console.log(`   ✅ PR Proxy deployed: ${await prProxy.getAddress()}`);
        
        productRegistry = PRLogic.attach(await prProxy.getAddress());
        
        // ===== Настройка интеграции =====
        console.log("🔷 Configuring integration...");
        await productRegistry.connect(admin).setOrganicComponentRegistry(await componentRegistry.getAddress());
        console.log("   ✅ ProductRegistry linked to OrganicComponentRegistry");
        
        // ===== Setup roles =====
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        CONTRIBUTOR_ROLE = await componentRegistry.CONTRIBUTOR_ROLE();
        
        // Настраиваем sellers в SpiralEngine
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);
        
        // Настраиваем contributors в OCR
        await componentRegistry.grantRole(CONTRIBUTOR_ROLE, seller.address);
        await componentRegistry.grantRole(CONTRIBUTOR_ROLE, otherSeller.address);
        
        console.log("   ✅ Roles configured");
        console.log("   ✅ Integration Test Setup Complete\n");
    });

    // ==========================================
    // TEST SUITE 1: Admin Configuration
    // ==========================================
    describe("⚙️ Admin Configuration", function () {
        it("Should set OrganicComponentRegistry address", async function () {
            console.log("   🔍 Testing setOrganicComponentRegistry()...");
            
            const registryAddress = await componentRegistry.getAddress();
            expect(await productRegistry.componentRegistry()).to.equal(registryAddress);
            
            console.log("   ✅ ComponentRegistry address set correctly");
        });

        it("Should revert when non-admin tries to set componentRegistry", async function () {
            console.log("   🔍 Testing access control for setOrganicComponentRegistry()...");
            
            const ADMIN_ROLE = await productRegistry.ADMIN_ROLE();
            await expect(
                productRegistry.connect(seller).setOrganicComponentRegistry(await componentRegistry.getAddress())
            ).to.be.revertedWithCustomError(productRegistry, "AccessControlUnauthorizedAccount");
            
            console.log("   ✅ Access control works correctly");
        });

        it("Should revert when setting zero address", async function () {
            console.log("   🔍 Testing zero address validation...");
            
            await expect(
                productRegistry.connect(admin).setOrganicComponentRegistry(ethers.ZeroAddress)
            ).to.be.revertedWithCustomError(productRegistry, "ZeroAddress");
            
            console.log("   ✅ Zero address validation works");
        });

        it("Should emit ComponentRegistryUpdated event", async function () {
            console.log("   🔍 Testing event emission...");
            
            const newRegistry = await ethers.getContractFactory("OrganicComponentRegistryLogic");
            const newInstance = await newRegistry.deploy();
            await newInstance.waitForDeployment();
            
            const oldAddress = await componentRegistry.getAddress();
            const newAddress = await newInstance.getAddress();
            
            await expect(
                productRegistry.connect(admin).setOrganicComponentRegistry(newAddress)
            ).to.emit(productRegistry, "ComponentRegistryUpdated")
             .withArgs(oldAddress, newAddress);
            
            console.log("   ✅ Event emitted correctly");
        });
    });

    // ==========================================
    // TEST SUITE 2: Product Creation with Components
    // ==========================================
    describe("📦 Product Creation with Components", function () {
        let component1, component2, component3;

        beforeEach(async function () {
            // Создаём тестовые компоненты
            console.log("   📝 Creating test components...");
            
            await componentRegistry.connect(seller).createComponent("comp_1", "QmComponent1");
            await componentRegistry.connect(seller).createComponent("comp_2", "QmComponent2");
            await componentRegistry.connect(seller).createComponent("comp_3", "QmComponent3");
            
            component1 = "comp_1";
            component2 = "comp_2";
            component3 = "comp_3";
            
            console.log("   ✅ Test components created");
        });

        it("Should create product with valid components", async function () {
            console.log("   🔍 Testing product creation with valid components...");
            
            const componentIds = [component1, component2, component3];
            const metadataCID = "QmProductMetadata123";
            
            const tx = await productRegistry.connect(seller).createProduct(componentIds, metadataCID);
            const receipt = await tx.wait();
            
            // Проверяем событие ProductCreated с ПОЛНОЙ проверкой параметров
            const event = receipt.logs.find(log => {
                try {
                    const parsed = productRegistry.interface.parseLog(log);
                    return parsed && parsed.name === "ProductCreated";
                } catch (e) {
                    return false;
                }
            });
            
            expect(event).to.not.be.undefined;
            
            // ✅ P2 FIX: Полная проверка всех параметров события
            const parsed = productRegistry.interface.parseLog(event);
            expect(parsed.args.seller).to.equal(seller.address);
            expect(parsed.args.productId).to.equal(1);
            expect(parsed.args.componentIds.length).to.equal(componentIds.length);
            for (let i = 0; i < componentIds.length; i++) {
                expect(parsed.args.componentIds[i]).to.equal(componentIds[i]);
            }
            expect(parsed.args.metadataCID).to.equal(metadataCID);
            
            // Проверяем данные продукта
            const product = await productRegistry.getProduct(1);
            expect(product.id).to.equal(1);
            expect(product.seller).to.equal(seller.address);
            expect(product.metadataCID).to.equal(metadataCID);
            expect(product.active).to.be.false;
            
            console.log("   ✅ Product created successfully");
        });

        it("Should store componentIds correctly", async function () {
            console.log("   🔍 Testing componentIds storage...");
            
            const componentIds = [component1, component2];
            await productRegistry.connect(seller).createProduct(componentIds, "QmMeta");
            
            const storedComponents = await productRegistry.getProductComponents(1);
            expect(storedComponents.length).to.equal(2);
            expect(storedComponents[0]).to.equal(component1);
            expect(storedComponents[1]).to.equal(component2);
            
            console.log("   ✅ ComponentIds stored correctly");
        });

        it("Should revert when component does not exist", async function () {
            console.log("   🔍 Testing validation of non-existent components...");
            
            const componentIds = [component1, "non_existent_comp", component2];
            
            await expect(
                productRegistry.connect(seller).createProduct(componentIds, "QmMeta")
            ).to.be.revertedWithCustomError(productRegistry, "ComponentNotFound");
            
            console.log("   ✅ Non-existent component validation works");
        });

        it("Should revert when componentIds array is empty", async function () {
            console.log("   🔍 Testing empty componentIds validation...");
            
            await expect(
                productRegistry.connect(seller).createProduct([], "QmMeta")
            ).to.be.revertedWithCustomError(productRegistry, "NoComponentsProvided");
            
            console.log("   ✅ Empty array validation works");
        });

        it("Should revert when too many components provided", async function () {
            console.log("   🔍 Testing MAX_COMPONENTS_PER_PRODUCT limit...");
            
            // Создаём 21 компонент (лимит = 20)
            const manyComponents = [];
            for (let i = 0; i < 21; i++) {
                const compId = `comp_many_${i}`;
                await componentRegistry.connect(seller).createComponent(compId, `QmComp${i}`);
                manyComponents.push(compId);
            }
            
            await expect(
                productRegistry.connect(seller).createProduct(manyComponents, "QmMeta")
            ).to.be.revertedWithCustomError(productRegistry, "TooManyComponents");
            
            console.log("   ✅ Max components limit works");
        });

        it("Should revert when componentRegistry not set", async function () {
            console.log("   🔍 Testing componentRegistry requirement...");
            
            // Деплоим новый ProductRegistry БЕЗ componentRegistry
            const PRLogic = await ethers.getContractFactory("ProductRegistryLogic");
            const prLogic = await PRLogic.deploy();
            await prLogic.waitForDeployment();
            
            const prInitCalldata = prLogic.interface.encodeFunctionData("initialize", [
                admin.address,
                await spiralEngine.getAddress()
            ]);
            
            const PRProxy = await ethers.getContractFactory("ProductRegistryProxy");
            const prProxy = await PRProxy.deploy(await prLogic.getAddress(), prInitCalldata);
            await prProxy.waitForDeployment();
            
            const newProductRegistry = PRLogic.attach(await prProxy.getAddress());
            
            await spiralEngine.setUserActivated(user1.address, true);
            await spiralEngine.grantRole(SELLER_ROLE, user1.address);
            
            await expect(
                newProductRegistry.connect(user1).createProduct([component1], "QmMeta")
            ).to.be.revertedWithCustomError(newProductRegistry, "ComponentRegistryNotSet");
            
            console.log("   ✅ ComponentRegistry requirement works");
        });

        it("Should revert with EmptyCID when metadataCID is empty", async function () {
            console.log("   🔍 Testing empty metadataCID validation...");
            
            await expect(
                productRegistry.connect(seller).createProduct([component1], "")
            ).to.be.revertedWithCustomError(productRegistry, "EmptyCID");
            
            console.log("   ✅ Empty CID validation works");
        });
    });

    // ==========================================
    // TEST SUITE 3: Component Usage Tracking
    // ==========================================
    describe("📊 Component Usage Tracking", function () {
        let component1, component2;

        beforeEach(async function () {
            console.log("   📝 Creating test components...");
            
            await componentRegistry.connect(seller).createComponent("track_comp_1", "QmTrack1");
            await componentRegistry.connect(seller).createComponent("track_comp_2", "QmTrack2");
            
            component1 = "track_comp_1";
            component2 = "track_comp_2";
            
            console.log("   ✅ Test components created");
        });

        it("Should increment usage count when product is created", async function () {
            console.log("   🔍 Testing usage count tracking...");
            
            // Проверяем начальное значение
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(0);
            
            // Создаём продукт
            await productRegistry.connect(seller).createProduct([component1, component2], "QmMeta");
            
            // Проверяем что счётчики увеличились
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(1);
            
            const comp2Id = await componentRegistry.businessIdToComponentId(component2);
            expect(await componentRegistry.componentUsageCount(comp2Id)).to.equal(1);
            
            console.log("   ✅ Usage count incremented correctly");
        });

        it("Should add component user when product is created", async function () {
            console.log("   🔍 Testing user tracking...");
            
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            
            // Создаём продукт
            await productRegistry.connect(seller).createProduct([component1], "QmMeta");
            
            // Проверяем что componentsByUser обновлен
            const userComponents = await componentRegistry.getComponentsByUser(seller.address);
            expect(userComponents.length).to.be.greaterThan(0);
            expect(userComponents).to.include(comp1Id);
            
            console.log("   ✅ Component user tracked correctly");
        });

        it("Should track usage from multiple sellers", async function () {
            console.log("   🔍 Testing multi-seller usage tracking...");
            
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            
            // seller создаёт продукт
            await productRegistry.connect(seller).createProduct([component1], "QmMeta1");
            
            // otherSeller создаёт продукт с тем же компонентом
            await productRegistry.connect(otherSeller).createProduct([component1], "QmMeta2");
            
            // Проверяем счётчик
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(2);
            
            // Проверяем что оба продавца добавлены в componentsByUser
            const sellerComponents = await componentRegistry.getComponentsByUser(seller.address);
            expect(sellerComponents).to.include(comp1Id);
            
            const otherSellerComponents = await componentRegistry.getComponentsByUser(otherSeller.address);
            expect(otherSellerComponents).to.include(comp1Id);
            
            console.log("   ✅ Multi-seller tracking works");
        });

        it("Should increment usage count for each product creation", async function () {
            console.log("   🔍 Testing repeated usage tracking...");
            
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            
            // seller создаёт 3 продукта с одним и тем же компонентом
            await productRegistry.connect(seller).createProduct([component1], "QmMeta1");
            await productRegistry.connect(seller).createProduct([component1], "QmMeta2");
            await productRegistry.connect(seller).createProduct([component1], "QmMeta3");
            
            // Счётчик должен быть 3
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(3);
            
            // Но пользователь должен быть только один (try-catch игнорирует дубликаты)
            const sellerComponents = await componentRegistry.getComponentsByUser(seller.address);
            // Компонент добавлен только один раз в список пользователя
            const count = sellerComponents.filter(id => id === comp1Id).length;
            expect(count).to.equal(1);
            
            console.log("   ✅ Repeated usage tracking works");
        });
    });

    // ==========================================
    // TEST SUITE 4: getProductComponents()
    // ==========================================
    describe("🔍 getProductComponents()", function () {
        it("Should return correct componentIds", async function () {
            console.log("   🔍 Testing getProductComponents()...");
            
            // Создаём компоненты
            await componentRegistry.connect(seller).createComponent("view_comp_1", "QmView1");
            await componentRegistry.connect(seller).createComponent("view_comp_2", "QmView2");
            await componentRegistry.connect(seller).createComponent("view_comp_3", "QmView3");
            
            const componentIds = ["view_comp_1", "view_comp_2", "view_comp_3"];
            
            // Создаём продукт
            await productRegistry.connect(seller).createProduct(componentIds, "QmMeta");
            
            // Получаем компоненты
            const storedComponents = await productRegistry.getProductComponents(1);
            
            expect(storedComponents.length).to.equal(3);
            expect(storedComponents[0]).to.equal("view_comp_1");
            expect(storedComponents[1]).to.equal("view_comp_2");
            expect(storedComponents[2]).to.equal("view_comp_3");
            
            console.log("   ✅ getProductComponents() works correctly");
        });

        it("Should revert when product does not exist", async function () {
            console.log("   🔍 Testing getProductComponents() for non-existent product...");
            
            await expect(
                productRegistry.getProductComponents(999)
            ).to.be.revertedWithCustomError(productRegistry, "ProductDoesNotExist");
            
            console.log("   ✅ Validation for non-existent product works");
        });
    });

    // ==========================================
    // TEST SUITE 5: Gas Cost Metrics
    // ==========================================
    describe("⛽ Gas Cost Metrics", function () {
        beforeEach(async function () {
            // Создаём тестовые компоненты
            console.log("   📝 Creating test components for gas tests...");
            
            for (let i = 1; i <= 10; i++) {
                await componentRegistry.connect(seller).createComponent(`gas_comp_${i}`, `QmGas${i}`);
            }
            
            console.log("   ✅ Test components created");
        });

        it("Should measure gas for createProduct with 1 component", async function () {
            console.log("   ⛽ Measuring gas for 1 component...");
            
            const tx = await productRegistry.connect(seller).createProduct(
                ["gas_comp_1"],
                "QmMeta"
            );
            const receipt = await tx.wait();
            const gasUsed = receipt.gasUsed;
            
            console.log(`   📊 Gas used (1 component): ${gasUsed.toString()}`);
            
            // ✅ P2 FIX: Проверка диапазона (минимум + максимум)
            expect(gasUsed).to.be.greaterThan(300000n, "Gas too low - logic might be skipped");
            expect(gasUsed).to.be.lessThan(400000n, "Gas too high - optimization needed");
            
            console.log("   ✅ Gas cost within acceptable range for 1 component");
        });

        it("Should measure gas for createProduct with 3 components", async function () {
            console.log("   ⛽ Measuring gas for 3 components...");
            
            const tx = await productRegistry.connect(seller).createProduct(
                ["gas_comp_1", "gas_comp_2", "gas_comp_3"],
                "QmMeta"
            );
            const receipt = await tx.wait();
            const gasUsed = receipt.gasUsed;
            
            console.log(`   📊 Gas used (3 components): ${gasUsed.toString()}`);
            
            // ✅ P2 FIX: Проверка диапазона
            expect(gasUsed).to.be.greaterThan(450000n, "Gas too low for 3 components");
            expect(gasUsed).to.be.lessThan(600000n, "Gas too high - optimization needed");
            
            console.log("   ✅ Gas cost within acceptable range for 3 components");
        });

        it("Should measure gas for createProduct with 10 components", async function () {
            console.log("   ⛽ Measuring gas for 10 components...");
            
            const componentIds = [];
            for (let i = 1; i <= 10; i++) {
                componentIds.push(`gas_comp_${i}`);
            }
            
            const tx = await productRegistry.connect(seller).createProduct(
                componentIds,
                "QmMeta"
            );
            const receipt = await tx.wait();
            const gasUsed = receipt.gasUsed;
            
            console.log(`   📊 Gas used (10 components): ${gasUsed.toString()}`);
            
            // ✅ P2 FIX: Проверка диапазона
            expect(gasUsed).to.be.greaterThan(1000000n, "Gas too low for 10 components");
            expect(gasUsed).to.be.lessThan(1300000n, "Gas too high - optimization needed");
            
            console.log("   ✅ Gas cost within acceptable range for 10 components");
        });

        it("Should demonstrate linear gas scaling with component count", async function () {
            console.log("   ⛽ Testing linear gas scaling...");
            
            // Измеряем газ для 1, 3 и 10 компонентов
            const gas1 = (await (await productRegistry.connect(seller).createProduct(
                ["gas_comp_1"], "QmLinear1"
            )).wait()).gasUsed;
            
            const gas3 = (await (await productRegistry.connect(seller).createProduct(
                ["gas_comp_1", "gas_comp_2", "gas_comp_3"], "QmLinear3"
            )).wait()).gasUsed;
            
            // Вычисляем стоимость компонента
            const gasPerComponent = (gas3 - gas1) / 2n;
            console.log(`   📊 Base gas (1 comp): ${gas1}`);
            console.log(`   📊 Gas for 3 comps: ${gas3}`);
            console.log(`   📊 Estimated gas per component: ${gasPerComponent}`);
            
            // ✅ P2 FIX: Проверка линейности
            // Ожидаемый диапазон: ~30K-50K gas на компонент (измерено: ~36K)
            expect(gasPerComponent).to.be.greaterThan(30000n, "Gas per component too low");
            expect(gasPerComponent).to.be.lessThan(50000n, "Gas per component too high");
            
            // Формула: Gas ≈ BASE + (N * gasPerComponent)
            const expectedBase = gas1 - gasPerComponent;
            console.log(`   📊 Estimated base gas: ${expectedBase}`);
            console.log(`   📊 Formula: Gas ≈ ${expectedBase} + (N * ${gasPerComponent})`);
            
            console.log("   ✅ Linear gas scaling confirmed");
        });
    });

    // ==========================================
    // TEST SUITE 6: Edge Cases & Error Handling
    // ==========================================
    describe("⚠️ Edge Cases & Error Handling", function () {
        it("Should handle product with exactly MAX_COMPONENTS_PER_PRODUCT", async function () {
            console.log("   🔍 Testing exactly 20 components (max limit)...");
            
            // Создаём ровно 20 компонентов
            const maxComponents = [];
            for (let i = 0; i < 20; i++) {
                const compId = `max_comp_${i}`;
                await componentRegistry.connect(seller).createComponent(compId, `QmMax${i}`);
                maxComponents.push(compId);
            }
            
            // Должно успешно создаться
            await expect(
                productRegistry.connect(seller).createProduct(maxComponents, "QmMeta")
            ).to.not.be.reverted;
            
            const storedComponents = await productRegistry.getProductComponents(1);
            expect(storedComponents.length).to.equal(20);
            
            console.log("   ✅ Max components limit (20) works correctly");
        });

        it("Should revert when seller not activated", async function () {
            console.log("   🔍 Testing seller activation requirement...");
            
            // Создаём компонент
            await componentRegistry.connect(seller).createComponent("test_comp", "QmTest");
            
            // Создаём нового пользователя БЕЗ активации
            const [_, __, ___, notActivated] = await ethers.getSigners();
            await spiralEngine.grantRole(SELLER_ROLE, notActivated.address);
            // НЕ вызываем setUserActivated
            
            await expect(
                productRegistry.connect(notActivated).createProduct(["test_comp"], "QmMeta")
            ).to.be.revertedWithCustomError(productRegistry, "NotActivatedUser");
            
            console.log("   ✅ Activation requirement works");
        });

        it("Should revert when seller does not have SELLER_ROLE", async function () {
            console.log("   🔍 Testing SELLER_ROLE requirement...");
            
            await componentRegistry.connect(seller).createComponent("test_comp", "QmTest");
            
            await expect(
                productRegistry.connect(user1).createProduct(["test_comp"], "QmMeta")
            ).to.be.revertedWithCustomError(productRegistry, "NotASeller");
            
            console.log("   ✅ SELLER_ROLE requirement works");
        });

        it("Should handle special characters in componentIds", async function () {
            console.log("   🔍 Testing special characters in componentIds...");
            
            const specialId = "comp_with-special.chars_123";
            await componentRegistry.connect(seller).createComponent(specialId, "QmSpecial");
            
            await expect(
                productRegistry.connect(seller).createProduct([specialId], "QmMeta")
            ).to.not.be.reverted;
            
            const storedComponents = await productRegistry.getProductComponents(1);
            expect(storedComponents[0]).to.equal(specialId);
            
            console.log("   ✅ Special characters handled correctly");
        });
    });

    // ==========================================
    // TEST SUITE 7: P2 Improvements - Critical Path Coverage
    // ==========================================
    describe("🔧 P2 Improvements - Missing Critical Paths", function () {
        let component1;

        beforeEach(async function () {
            console.log("   📝 Creating test components...");
            await componentRegistry.connect(seller).createComponent("improve_comp_1", "QmImprove1");
            component1 = "improve_comp_1";
            console.log("   ✅ Test components created");
        });

        it("Should keep componentIds unchanged when updating product", async function () {
            console.log("   🔍 Testing componentIds immutability in updateProduct()...");
            
            const originalComponents = [component1];
            const metadataCID1 = "QmMeta1";
            const metadataCID2 = "QmMeta2";
            
            // Создаём и активируем продукт
            await productRegistry.connect(seller).createProduct(originalComponents, metadataCID1);
            await productRegistry.connect(seller).activateProduct(1);
            
            // Обновляем только metadataCID
            await productRegistry.connect(seller).updateProduct(1, metadataCID2, 100);
            
            // Проверяем что componentIds НЕ изменились
            const storedComponents = await productRegistry.getProductComponents(1);
            expect(storedComponents.length).to.equal(originalComponents.length);
            expect(storedComponents[0]).to.equal(component1);
            
            // Проверяем что metadataCID обновился
            const product = await productRegistry.getProduct(1);
            expect(product.metadataCID).to.equal(metadataCID2);
            
            console.log("   ✅ componentIds remained unchanged during update");
        });

        it("Should NOT increment usage count when activating product", async function () {
            console.log("   🔍 Testing that activateProduct() does NOT trigger tracking...");
            
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            
            // Создаём продукт (это должно увеличить счётчик)
            await productRegistry.connect(seller).createProduct([component1], "QmMeta");
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(1);
            
            // Активируем продукт (НЕ должно увеличивать счётчик)
            await productRegistry.connect(seller).activateProduct(1);
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(1); // Всё ещё 1
            
            console.log("   ✅ activateProduct() correctly does NOT trigger tracking");
        });

        it("Should handle multiple products with same components (batch)", async function () {
            console.log("   🔍 Testing batch operations with same components...");
            
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            
            // Создаём 5 продуктов с одинаковыми компонентами
            await productRegistry.connect(seller).createProduct([component1], "QmMeta1");
            await productRegistry.connect(seller).createProduct([component1], "QmMeta2");
            await productRegistry.connect(seller).createProduct([component1], "QmMeta3");
            await productRegistry.connect(seller).createProduct([component1], "QmMeta4");
            await productRegistry.connect(seller).createProduct([component1], "QmMeta5");
            
            // Счётчик должен быть 5 (каждый раз инкрементировался)
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(5);
            
            // Но пользователь добавлен только 1 раз (try-catch игнорирует дубликаты)
            const sellerComponents = await componentRegistry.getComponentsByUser(seller.address);
            const count = sellerComponents.filter(id => id === comp1Id).length;
            expect(count).to.equal(1);
            
            console.log("   ✅ Batch operations handled correctly");
        });

        it("Should handle duplicate componentIds in single product", async function () {
            console.log("   🔍 Testing duplicate componentIds in single product...");
            
            // Создаём продукт с дубликатами
            const duplicateComponents = [component1, component1, component1];
            
            // Ожидаем успех (дубликаты допустимы на уровне ProductRegistry)
            await expect(
                productRegistry.connect(seller).createProduct(duplicateComponents, "QmMeta")
            ).to.not.be.reverted;
            
            // Проверяем что все 3 элемента сохранены (включая дубликаты)
            const storedComponents = await productRegistry.getProductComponents(1);
            expect(storedComponents.length).to.equal(3);
            expect(storedComponents[0]).to.equal(component1);
            expect(storedComponents[1]).to.equal(component1);
            expect(storedComponents[2]).to.equal(component1);
            
            // Но usage count увеличился только 3 раза (по одному на каждый вызов)
            const comp1Id = await componentRegistry.businessIdToComponentId(component1);
            expect(await componentRegistry.componentUsageCount(comp1Id)).to.equal(3);
            
            console.log("   ✅ Duplicate componentIds handled correctly");
        });

        it("Should reject very long componentIds (>64 chars)", async function () {
            console.log("   🔍 Testing very long componentIds (edge case)...");
            
            // ✅ P2 FIX: OrganicComponentRegistry имеет MAX_BUSINESS_ID_LENGTH = 64 символа
            // Тест должен проверять что контракт ПРАВИЛЬНО отклоняет слишком длинные ID
            
            // Создаём componentId длиной 255 символов (превышает лимит 64)
            const veryLongId = "comp_" + "x".repeat(250); // 255 символов total
            
            // Проверяем что OrganicComponentRegistry отклоняет слишком длинный ID
            await expect(
                componentRegistry.connect(seller).createComponent(veryLongId, "QmLong")
            ).to.be.revertedWith("OrganicComponentRegistryLogic: business ID too long");
            
            // Проверяем что ID длиной ровно 64 символа принимается
            const maxLengthId = "comp_" + "x".repeat(59); // 64 символа total
            await componentRegistry.connect(seller).createComponent(maxLengthId, "QmMax");
            
            // Проверяем что можно создать продукт с максимально допустимым ID
            await productRegistry.connect(seller).createProduct([maxLengthId], "QmMeta");
            
            const storedComponents = await productRegistry.getProductComponents(1);
            expect(storedComponents[0]).to.equal(maxLengthId);
            expect(storedComponents[0].length).to.equal(64);
            
            console.log("   ✅ Long componentIds validation works correctly");
        });
    });
});

