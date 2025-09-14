const { expect, assert } = require("chai");
const { ethers } = require("hardhat");

describe("SpiralEngine - Circle Management", function () {
    let spiralEngine;
    let soulIdentity;
    let deployer;
    let seller;
    let activator1;
    let activator2;
    let user1;
    let user2;
    let user3;

    // Константы ролей
    const DEFAULT_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("DEFAULT_ADMIN_ROLE"));
    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
    const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];
        
        // Создаем дополнительные кошельки для тестирования
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        activator1 = ethers.Wallet.createRandom().connect(ethers.provider);
        activator2 = ethers.Wallet.createRandom().connect(ethers.provider);
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);
        user3 = ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Финансируем кошельки
        await deployer.sendTransaction({
            to: seller.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: activator1.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: activator2.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user1.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user2.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user3.address,
            value: ethers.parseEther("1.0")
        });

        // Деплоим контракт SoulIdentity
        console.log("🔷 Deploying SoulIdentity contract...");
        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        soulIdentity = await SoulIdentity.connect(deployer).deploy();
        await soulIdentity.waitForDeployment();

        // Деплоим контракт SpiralEngine
        console.log("🔷 Deploying SpiralEngine contract...");
        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        spiralEngine = await SpiralEngine.connect(deployer).deploy();
        await spiralEngine.waitForDeployment();

        // Устанавливаем ссылку на SoulIdentity
        await spiralEngine.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());

        // Назначаем роли
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator2.address);

        console.log("🔷 SpiralEngine Circles Tests Setup Complete");
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   Seller: ${seller.address}`);
        console.log(`   Activator1: ${activator1.address}`);
        console.log(`   Activator2: ${activator2.address}`);
        console.log(`   User1: ${user1.address}`);
        console.log(`   User2: ${user2.address}`);
        console.log(`   User3: ${user3.address}`);
        console.log(`   SpiralEngine Address: ${await spiralEngine.getAddress()}`);
        console.log(`   SoulIdentity Address: ${await soulIdentity.getAddress()}`);
    });

    describe("Circle Creation and Management", function () {
        it("Should create circle with single member", async function () {
            console.log("Testing single member circle creation...");
            
            // Создаем инвайт для активатора
            await spiralEngine.connect(seller).mintInvite("CIRCLE-TEST-INVITE-1", 0);
            
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).activateUser("CIRCLE-TEST-INVITE-1", user1.address, newCodes, 0);
            console.log("✅ User1 activated by activator1");
            
            // Проверяем размер круга
            const circleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(circleSize).to.equal(1);
            console.log(`✅ Circle size: ${circleSize}`);
            
            // Проверяем членов круга
            const circleMembers = await spiralEngine.getCircleMembers(activator1.address);
            expect(circleMembers).to.have.lengthOf(1);
            expect(circleMembers[0]).to.equal(user1.address);
            console.log(`✅ Circle members: ${circleMembers.join(", ")}`);
            
            // Проверяем активатора пользователя
            const userActivator = await spiralEngine.userActivator(user1.address);
            expect(userActivator).to.equal(activator1.address);
            console.log(`✅ User1 activator: ${userActivator}`);
        });

        it("Should create circle with multiple members", async function () {
            console.log("Testing multiple member circle creation...");
            
            // Создаем инвайты для активатора
            await spiralEngine.connect(seller).mintInvite("CIRCLE-TEST-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("CIRCLE-TEST-INVITE-2", 0);
            await spiralEngine.connect(seller).mintInvite("CIRCLE-TEST-INVITE-3", 0);
            
            // Активируем трех пользователей
            const newCodes1 = Array.from({length: 12}, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            const newCodes3 = Array.from({length: 12}, (_, i) => `NEW-3-${i + 1}`);
            
            await spiralEngine.connect(activator1).activateUser("CIRCLE-TEST-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("CIRCLE-TEST-INVITE-2", user2.address, newCodes2, 0);
            await spiralEngine.connect(activator1).activateUser("CIRCLE-TEST-INVITE-3", user3.address, newCodes3, 0);
            
            console.log("✅ Three users activated by activator1");
            
            // Проверяем размер круга
            const circleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(circleSize).to.equal(3);
            console.log(`✅ Circle size: ${circleSize}`);
            
            // Проверяем членов круга
            const circleMembers = await spiralEngine.getCircleMembers(activator1.address);
            expect(circleMembers).to.have.lengthOf(3);
            expect(circleMembers).to.include(user1.address);
            expect(circleMembers).to.include(user2.address);
            expect(circleMembers).to.include(user3.address);
            console.log(`✅ Circle members: ${circleMembers.join(", ")}`);
        });

        it("Should create multiple independent circles", async function () {
            console.log("Testing multiple independent circles...");
            
            // Создаем инвайты для обоих активаторов
            await spiralEngine.connect(seller).mintInvite("CIRCLE-1-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("CIRCLE-1-INVITE-2", 0);
            await spiralEngine.connect(seller).mintInvite("CIRCLE-2-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("CIRCLE-2-INVITE-2", 0);
            
            // Активируем пользователей в разных кругах
            const newCodes1 = Array.from({length: 12}, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            const newCodes3 = Array.from({length: 12}, (_, i) => `NEW-3-${i + 1}`);
            const newCodes4 = Array.from({length: 12}, (_, i) => `NEW-4-${i + 1}`);
            
            await spiralEngine.connect(activator1).activateUser("CIRCLE-1-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("CIRCLE-1-INVITE-2", user2.address, newCodes2, 0);
            await spiralEngine.connect(activator2).activateUser("CIRCLE-2-INVITE-1", user3.address, newCodes3, 0);
            
            console.log("✅ Users activated in different circles");
            
            // Проверяем размеры кругов
            const circle1Size = await spiralEngine.getCircleSize(activator1.address);
            const circle2Size = await spiralEngine.getCircleSize(activator2.address);
            
            expect(circle1Size).to.equal(2);
            expect(circle2Size).to.equal(1);
            console.log(`✅ Circle1 size: ${circle1Size}, Circle2 size: ${circle2Size}`);
            
            // Проверяем членов кругов
            const circle1Members = await spiralEngine.getCircleMembers(activator1.address);
            const circle2Members = await spiralEngine.getCircleMembers(activator2.address);
            
            expect(circle1Members).to.have.lengthOf(2);
            expect(circle2Members).to.have.lengthOf(1);
            expect(circle1Members).to.include(user1.address);
            expect(circle1Members).to.include(user2.address);
            expect(circle2Members).to.include(user3.address);
            console.log(`✅ Circle1 members: ${circle1Members.join(", ")}`);
            console.log(`✅ Circle2 members: ${circle2Members.join(", ")}`);
        });
    });

    describe("Circle Limits and Constraints", function () {
        it("Should enforce 12 member circle limit", async function () {
            console.log("Testing 12 member circle limit...");
            
            // Создаем 13 инвайтов для тестирования лимита
            for (let i = 1; i <= 13; i++) {
                await spiralEngine.connect(seller).mintInvite(`LIMIT-TEST-INVITE-${i}`, 0);
            }
            
            // Активируем 12 пользователей (должно пройти)
            for (let i = 0; i < 12; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `NEW-${i}-${j + 1}`);
                await spiralEngine.connect(activator1).activateUser(`LIMIT-TEST-INVITE-${i + 1}`, user.address, newCodes, 0);
            }
            
            console.log("✅ 12 users activated successfully");
            
            // Проверяем размер круга
            const circleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(circleSize).to.equal(12);
            console.log(`✅ Circle size: ${circleSize}`);
            
            // Попытка активировать 13-го пользователя (должна провалиться)
            const user13 = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: user13.address,
                value: ethers.parseEther("0.1")
            });
            
            const newCodes13 = Array.from({length: 12}, (_, i) => `NEW-13-${i + 1}`);
            
            await expect(
                spiralEngine.connect(activator1).activateUser("LIMIT-TEST-INVITE-13", user13.address, newCodes13, 0)
            ).to.be.revertedWith("Circle limit reached (max 12 members)");
            
            console.log("✅ 13th user activation correctly rejected");
        });

        it("Should enforce circle limit in activateUser function", async function () {
            console.log("Testing circle limit enforcement in activateUser function...");
            
            for (let i = 1; i <= 13; i++) {
                await spiralEngine.connect(seller).mintInvite(`ENFORCEMENT-TEST-INVITE-${i}`, 0);
            }
            
            // Активируем 12 пользователей
            for (let i = 0; i < 12; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `NEW-${i}-${j + 1}`);
                await spiralEngine.connect(activator1).activateUser(`ENFORCEMENT-TEST-INVITE-${i + 1}`, user.address, newCodes, 0);
            }
            
            // Проверяем, что лимит действительно достигнут
            const circleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(circleSize).to.equal(12);
            console.log(`✅ Circle size confirmed: ${circleSize}`);
            
            // Попытка активировать 13-го пользователя должна провалиться
            const user13 = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: user13.address,
                value: ethers.parseEther("0.1")
            });
            
            const newCodes13 = Array.from({length: 12}, (_, i) => `NEW-13-${i + 1}`);
            await expect(
                spiralEngine.connect(activator1).activateUser("ENFORCEMENT-TEST-INVITE-13", user13.address, newCodes13, 0)
            ).to.be.revertedWith("Circle limit reached (max 12 members)");
            
            console.log("✅ Circle limit enforcement working correctly");
        });

        it("Should allow different activators to have full circles", async function () {
            console.log("Testing multiple full circles...");
            
            // Создаем инвайты для обоих активаторов
            for (let i = 1; i <= 12; i++) {
                await spiralEngine.connect(seller).mintInvite(`FULL-CIRCLE-1-INVITE-${i}`, 0);
                await spiralEngine.connect(seller).mintInvite(`FULL-CIRCLE-2-INVITE-${i}`, 0);
            }
            
            // Заполняем первый круг
            for (let i = 0; i < 12; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `NEW-1-${i}-${j + 1}`);
                await spiralEngine.connect(activator1).activateUser(`FULL-CIRCLE-1-INVITE-${i + 1}`, user.address, newCodes, 0);
            }
            
            // Заполняем второй круг
            for (let i = 0; i < 12; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `NEW-2-${i}-${j + 1}`);
                await spiralEngine.connect(activator2).activateUser(`FULL-CIRCLE-2-INVITE-${i + 1}`, user.address, newCodes, 0);
            }
            
            console.log("✅ Both circles filled to capacity");
            
            // Проверяем размеры кругов
            const circle1Size = await spiralEngine.getCircleSize(activator1.address);
            const circle2Size = await spiralEngine.getCircleSize(activator2.address);
            
            expect(circle1Size).to.equal(12);
            expect(circle2Size).to.equal(12);
            console.log(`✅ Circle1 size: ${circle1Size}, Circle2 size: ${circle2Size}`);
        });
    });

    describe("Circle Hierarchy and Relationships", function () {
        it("Should track activator relationships correctly", async function () {
            console.log("Testing activator relationships...");
            
            // Создаем инвайты
            await spiralEngine.connect(seller).mintInvite("HIERARCHY-TEST-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("HIERARCHY-TEST-INVITE-2", 0);
            
            const newCodes1 = Array.from({length: 12}, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            
            // Активируем пользователей
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-TEST-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator2).activateUser("HIERARCHY-TEST-INVITE-2", user2.address, newCodes2, 0);
            
            console.log("✅ Users activated by different activators");
            
            // Проверяем отношения активации
            const user1Activator = await spiralEngine.userActivator(user1.address);
            const user2Activator = await spiralEngine.userActivator(user2.address);
            
            expect(user1Activator).to.equal(activator1.address);
            expect(user2Activator).to.equal(activator2.address);
            console.log(`✅ User1 activator: ${user1Activator}`);
            console.log(`✅ User2 activator: ${user2Activator}`);
            
            // Проверяем, что пользователи в правильных кругах
            const activator1Circle = await spiralEngine.getCircleMembers(activator1.address);
            const activator2Circle = await spiralEngine.getCircleMembers(activator2.address);
            
            expect(activator1Circle).to.include(user1.address);
            expect(activator2Circle).to.include(user2.address);
            expect(activator1Circle).to.not.include(user2.address);
            expect(activator2Circle).to.not.include(user1.address);
            console.log(`✅ User1 in activator1 circle: ${activator1Circle.includes(user1.address)}`);
            console.log(`✅ User2 in activator2 circle: ${activator2Circle.includes(user2.address)}`);
        });

        it("Should prevent cross-circle activation", async function () {
            console.log("Testing cross-circle activation prevention...");
            
            // Создаем инвайт для первого активатора
            await spiralEngine.connect(seller).mintInvite("CROSS-CIRCLE-INVITE", 0);
            
            // Активируем пользователя первым активатором
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("CROSS-CIRCLE-INVITE", user1.address, newCodes, 0);
            
            console.log("✅ User1 activated by activator1");
            
            // Попытка активировать того же пользователя вторым активатором
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            
            await expect(
                spiralEngine.connect(activator2).activateUser("CROSS-CIRCLE-INVITE", user1.address, newCodes2, 0)
            ).to.be.revertedWith("User already activated invite");
            
            console.log("✅ Cross-circle activation correctly prevented");
        });
    });

    describe("Circle Statistics and Monitoring", function () {
        it("Should provide accurate circle statistics", async function () {
            console.log("Testing circle statistics...");
            
            // Создаем инвайты
            await spiralEngine.connect(seller).mintInvite("STATS-TEST-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("STATS-TEST-INVITE-2", 0);
            await spiralEngine.connect(seller).mintInvite("STATS-TEST-INVITE-3", 0);
            
            // Активируем пользователей
            const newCodes1 = Array.from({length: 12}, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            const newCodes3 = Array.from({length: 12}, (_, i) => `NEW-3-${i + 1}`);
            
            await spiralEngine.connect(activator1).activateUser("STATS-TEST-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("STATS-TEST-INVITE-2", user2.address, newCodes2, 0);
            await spiralEngine.connect(activator2).activateUser("STATS-TEST-INVITE-3", user3.address, newCodes3, 0);
            
            console.log("✅ Users activated for statistics testing");
            
            // Проверяем статистику кругов
            const circle1Size = await spiralEngine.getCircleSize(activator1.address);
            const circle2Size = await spiralEngine.getCircleSize(activator2.address);
            
            expect(circle1Size).to.equal(2);
            expect(circle2Size).to.equal(1);
            console.log(`✅ Circle1 size: ${circle1Size}`);
            console.log(`✅ Circle2 size: ${circle2Size}`);
            
            // Проверяем членов кругов
            const circle1Members = await spiralEngine.getCircleMembers(activator1.address);
            const circle2Members = await spiralEngine.getCircleMembers(activator2.address);
            
            expect(circle1Members).to.have.lengthOf(2);
            expect(circle2Members).to.have.lengthOf(1);
            console.log(`✅ Circle1 members count: ${circle1Members.length}`);
            console.log(`✅ Circle2 members count: ${circle2Members.length}`);
        });

        it("Should handle empty circles correctly", async function () {
            console.log("Testing empty circles...");
            
            // Проверяем пустые круги
            const emptyCircle1Size = await spiralEngine.getCircleSize(activator1.address);
            const emptyCircle2Size = await spiralEngine.getCircleSize(activator2.address);
            
            expect(emptyCircle1Size).to.equal(0);
            expect(emptyCircle2Size).to.equal(0);
            console.log(`✅ Empty circle1 size: ${emptyCircle1Size}`);
            console.log(`✅ Empty circle2 size: ${emptyCircle2Size}`);
            
            // Проверяем пустые массивы членов
            const emptyCircle1Members = await spiralEngine.getCircleMembers(activator1.address);
            const emptyCircle2Members = await spiralEngine.getCircleMembers(activator2.address);
            
            expect(emptyCircle1Members).to.have.lengthOf(0);
            expect(emptyCircle2Members).to.have.lengthOf(0);
            console.log(`✅ Empty circle1 members: ${emptyCircle1Members.length}`);
            console.log(`✅ Empty circle2 members: ${emptyCircle2Members.length}`);
        });
    });

    describe("Circle Edge Cases", function () {
        it("Should handle circle operations on non-existent activators", async function () {
            console.log("Testing circle operations on non-existent activators...");
            
            const nonExistentActivator = ethers.Wallet.createRandom().connect(ethers.provider);
            
            // Проверяем размер несуществующего круга
            const circleSize = await spiralEngine.getCircleSize(nonExistentActivator.address);
            expect(circleSize).to.equal(0);
            console.log(`✅ Non-existent circle size: ${circleSize}`);
            
            // Проверяем членов несуществующего круга
            const circleMembers = await spiralEngine.getCircleMembers(nonExistentActivator.address);
            expect(circleMembers).to.have.lengthOf(0);
            console.log(`✅ Non-existent circle members: ${circleMembers.length}`);
        });

        it("Should handle invite ownership validation", async function () {
            console.log("Testing invite ownership validation...");
            
            // Создаем инвайт для seller
            await spiralEngine.connect(seller).mintInvite("OWNERSHIP-TEST-INVITE", 0);
            
            // Проверяем принадлежность инвайта
            const isFromActivator1 = await spiralEngine.isInviteFromActivator("OWNERSHIP-TEST-INVITE", activator1.address);
            const isFromActivator2 = await spiralEngine.isInviteFromActivator("OWNERSHIP-TEST-INVITE", activator2.address);
            
            expect(isFromActivator1).to.be.false; // Инвайт создан seller, не activator1
            expect(isFromActivator2).to.be.false; // Инвайт создан seller, не activator2
            console.log(`✅ Invite from activator1: ${isFromActivator1}`);
            console.log(`✅ Invite from activator2: ${isFromActivator2}`);
            
            // Создаем инвайт для активатора
            await spiralEngine.connect(seller).mintInvite("OWNERSHIP-TEST-INVITE-2", 0);
            
            // Проверяем принадлежность нового инвайта
            const isFromActivator1New = await spiralEngine.isInviteFromActivator("OWNERSHIP-TEST-INVITE-2", activator1.address);
            const isFromActivator2New = await spiralEngine.isInviteFromActivator("OWNERSHIP-TEST-INVITE-2", activator2.address);
            
            expect(isFromActivator1New).to.be.true; // Инвайт создан activator1
            expect(isFromActivator2New).to.be.false; // Инвайт не создан activator2
            console.log(`✅ New invite from activator1: ${isFromActivator1New}`);
            console.log(`✅ New invite from activator2: ${isFromActivator2New}`);
        });

        it("Should handle invalid invite codes in circle operations", async function () {
            console.log("Testing invalid invite codes in circle operations...");
            
            // Проверяем несуществующий инвайт
            const isFromActivator1 = await spiralEngine.isInviteFromActivator("NON-EXISTENT-INVITE", activator1.address);
            expect(isFromActivator1).to.be.false;
            console.log(`✅ Non-existent invite from activator1: ${isFromActivator1}`);
            
            // Проверяем пустую строку
            const isEmptyFromActivator1 = await spiralEngine.isInviteFromActivator("", activator1.address);
            expect(isEmptyFromActivator1).to.be.false;
            console.log(`✅ Empty invite from activator1: ${isEmptyFromActivator1}`);
        });
    });
});
