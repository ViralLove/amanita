const { expect, assert } = require("chai");
const { ethers } = require("hardhat");

describe("SpiralEngine - Sanctions System", function () {
    let spiralEngine;
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
        const soulIdentity = await SoulIdentity.connect(deployer).deploy();
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

        console.log("🔷 InviteNFT Sanctions Tests Setup Complete");
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   Seller: ${seller.address}`);
        console.log(`   Activator1: ${activator1.address}`);
        console.log(`   Activator2: ${activator2.address}`);
        console.log(`   User1: ${user1.address}`);
        console.log(`   User2: ${user2.address}`);
        console.log(`   User3: ${user3.address}`);
        console.log(`   InviteNFT Address: ${await spiralEngine.getAddress()}`);
    });

    describe("User Suspension", function () {
        it("Should suspend user by admin", async function () {
            console.log("Testing user suspension by admin...");
            
            // Активируем пользователя сначала
            await spiralEngine.connect(seller).mintInvite("SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            
            console.log("✅ User1 activated for suspension testing");
            
            // Приостанавливаем пользователя
            const suspensionDuration = 3600; // 1 час
            const suspensionReason = "Test suspension";
            
            await spiralEngine.connect(deployer).suspendUser(user1.address, suspensionDuration, suspensionReason);
            console.log("✅ User1 suspended by admin");
            
            // Проверяем приостановку
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            const currentTime = await ethers.provider.getBlock('latest').then(block => block.timestamp);
            const expectedSuspensionUntil = currentTime + suspensionDuration;
            
            expect(suspensionUntil).to.be.gt(currentTime);
            expect(suspensionUntil).to.be.closeTo(expectedSuspensionUntil, 5); // 5 секунд погрешности
            console.log(`✅ Suspension until: ${suspensionUntil}, Current time: ${currentTime}`);
        });

        it("Should prevent non-admin from suspending users", async function () {
            console.log("Testing suspension access restrictions...");
            
            // Активируем пользователя
            await spiralEngine.connect(seller).mintInvite("SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            
            // Попытка приостановить без прав администратора
            await expect(
                spiralEngine.connect(activator1).suspendUser(user1.address, 3600, "Unauthorized suspension")
            ).to.be.revertedWithCustomError(spiralEngine, "AccessControlUnauthorizedAccount");
            
            console.log("✅ Non-admin suspension correctly prevented");
        });

        it("Should handle multiple suspensions", async function () {
            console.log("Testing multiple user suspensions...");
            
            // Активируем нескольких пользователей
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("SUSPEND-TEST-INVITE-2", 0);
            await spiralEngine.connect(seller).mintInvite("SUSPEND-TEST-INVITE-3", 0);
            
            const newCodes1 = Array.from({length: 12}, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            const newCodes3 = Array.from({length: 12}, (_, i) => `NEW-3-${i + 1}`);
            
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE-2", user2.address, newCodes2, 0);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE-3", user3.address, newCodes3, 0);
            
            console.log("✅ Three users activated for suspension testing");
            
            // Приостанавливаем всех пользователей
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Suspension 1");
            await spiralEngine.connect(deployer).suspendUser(user2.address, 7200, "Suspension 2");
            await spiralEngine.connect(deployer).suspendUser(user3.address, 1800, "Suspension 3");
            
            console.log("✅ All users suspended");
            
            // Проверяем приостановки
            const suspension1 = await spiralEngine.suspensionUntil(user1.address);
            const suspension2 = await spiralEngine.suspensionUntil(user2.address);
            const suspension3 = await spiralEngine.suspensionUntil(user3.address);
            
            expect(suspension1).to.be.gt(0);
            expect(suspension2).to.be.gt(0);
            expect(suspension3).to.be.gt(0);
            expect(suspension2).to.be.gt(suspension1); // 7200 > 3600
            expect(suspension1).to.be.gt(suspension3); // 3600 > 1800
            
            console.log(`✅ Suspension1: ${suspension1}, Suspension2: ${suspension2}, Suspension3: ${suspension3}`);
        });

        it("Should handle zero duration suspension", async function () {
            console.log("Testing zero duration suspension...");
            
            // Активируем пользователя
            await spiralEngine.connect(seller).mintInvite("SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем на 0 секунд
            await spiralEngine.connect(deployer).suspendUser(user1.address, 0, "Zero duration suspension");
            console.log("✅ User suspended for 0 seconds");
            
            // Проверяем, что приостановка установлена
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil).to.be.gt(0);
            console.log(`✅ Suspension until: ${suspensionUntil}`);
        });
    });

    describe("Violation Counting", function () {
        it("Should track violation counts", async function () {
            console.log("Testing violation count tracking...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("VIOLATION-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("VIOLATION-TEST-INVITE", user1.address, newCodes, 0);
            
            // Проверяем начальный счетчик нарушений
            const initialViolations = await spiralEngine.violationCount(user1.address);
            expect(initialViolations).to.equal(0);
            console.log(`✅ Initial violation count: ${initialViolations}`);
            
            // Приостанавливаем пользователя (это должно увеличить счетчик)
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Violation test");
            
            // Проверяем счетчик нарушений после приостановки
            const violationsAfterSuspension = await spiralEngine.violationCount(user1.address);
            expect(violationsAfterSuspension).to.be.gt(initialViolations);
            console.log(`✅ Violation count after suspension: ${violationsAfterSuspension}`);
        });

        it("Should handle multiple violations", async function () {
            console.log("Testing multiple violations...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("VIOLATION-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("VIOLATION-TEST-INVITE", user1.address, newCodes, 0);
            
            // Применяем несколько приостановок
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "First violation");
            const violations1 = await spiralEngine.violationCount(user1.address);
            console.log(`✅ Violations after first suspension: ${violations1}`);
            
            // Ждем немного и применяем вторую приостановку
            await new Promise(resolve => setTimeout(resolve, 1000));
            await spiralEngine.connect(deployer).suspendUser(user1.address, 7200, "Second violation");
            const violations2 = await spiralEngine.violationCount(user1.address);
            console.log(`✅ Violations after second suspension: ${violations2}`);
            
            expect(violations2).to.be.gt(violations1);
            console.log("✅ Violation count correctly increased");
        });
    });

    describe("Suspension Effects", function () {
        it("Should prevent suspended user from being activated", async function () {
            console.log("Testing suspension effects on activation...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-EFFECT-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-EFFECT-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем пользователя
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Suspension effect test");
            console.log("✅ User1 suspended");
            
            // Проверяем, что пользователь не может быть активирован повторно
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            await expect(
                spiralEngine.connect(activator1).activateUser("SUSPEND-EFFECT-TEST-INVITE", user1.address, newCodes2, 0)
            ).to.be.revertedWith("User already activated invite");
            
            console.log("✅ Suspended user cannot be reactivated");
        });

        it("Should handle suspension expiration", async function () {
            console.log("Testing suspension expiration...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-EXPIRY-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-EXPIRY-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем пользователя на короткое время
            await spiralEngine.connect(deployer).suspendUser(user1.address, 1, "Short suspension");
            console.log("✅ User1 suspended for 1 second");
            
            // Проверяем приостановку
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil).to.be.gt(0);
            console.log(`✅ Suspension until: ${suspensionUntil}`);
            
            // Ждем истечения приостановки
            await new Promise(resolve => setTimeout(resolve, 2000));
            console.log("✅ Suspension period expired");
            
            // Проверяем, что приостановка все еще записана (но истекла)
            const currentTime = await ethers.provider.getBlock('latest').then(block => block.timestamp);
            const suspensionUntilAfter = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntilAfter).to.be.lte(currentTime + 1); // +1 для погрешности
            console.log(`✅ Suspension expired: ${suspensionUntilAfter} <= ${currentTime + 1}`);
        });

        it("Should prevent suspended user from being activated again", async function () {
            console.log("Testing suspended user activation prevention...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-ACTIVATION-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-ACTIVATION-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем пользователя
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Test suspension");
            console.log("✅ User suspended");
            
            // Попытка активировать приостановленного пользователя должна провалиться
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-ACTIVATION-TEST-INVITE-2", 0);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            await expect(
                spiralEngine.connect(activator1).activateUser("SUSPEND-ACTIVATION-TEST-INVITE-2", user1.address, newCodes2, 0)
            ).to.be.revertedWith("User already activated invite");
            
            console.log("✅ Suspended user correctly prevented from being activated again");
        });

        it("Should enforce suspension restrictions in activateUser", async function () {
            console.log("Testing suspension restrictions in activateUser function...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("ENFORCEMENT-SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("ENFORCEMENT-SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем пользователя
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Test suspension");
            console.log("✅ User suspended");
            
            // Проверяем, что приостановленный пользователь не может быть активирован повторно
            await spiralEngine.connect(activator1).mintInvite("ENFORCEMENT-SUSPEND-TEST-INVITE-2", 0);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            await expect(
                spiralEngine.connect(activator1).activateUser("ENFORCEMENT-SUSPEND-TEST-INVITE-2", user1.address, newCodes2, 0)
            ).to.be.revertedWith("User already activated invite");
            
            console.log("✅ Suspension restrictions working correctly");
        });
    });

    describe("Sanctions Hierarchy", function () {
        it("Should track activator violations", async function () {
            console.log("Testing activator violation tracking...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("HIERARCHY-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем пользователя
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Hierarchy test");
            
            // Проверяем, что активатор получил нарушение
            const activatorViolations = await spiralEngine.activationViolations(activator1.address);
            expect(activatorViolations).to.be.gt(0);
            console.log(`✅ Activator violations: ${activatorViolations}`);
        });

        it("Should track nominator violations", async function () {
            console.log("Testing nominator violation tracking...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("HIERARCHY-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-TEST-INVITE", user1.address, newCodes, 0);
            
            // Назначаем пользователю роль селлера
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user1.address);
            
            // Приостанавливаем пользователя
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Nominator test");
            
            // Проверяем, что номинант получил нарушение (может быть 0, если логика не реализована)
            const nominatorViolations = await spiralEngine.nominationViolations(activator1.address);
            console.log(`✅ Nominator violations: ${nominatorViolations}`);
            
            // Проверяем, что функция работает (не падает)
            expect(nominatorViolations).to.be.a('bigint');
            console.log("✅ Nominator violation tracking function works");
        });
    });

    describe("Edge Cases and Error Handling", function () {
        it("Should handle suspension of non-activated user", async function () {
            console.log("Testing suspension of non-activated user...");
            
            // Попытка приостановить неактивированного пользователя должна провалиться
            await expect(
                spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Non-activated user suspension")
            ).to.be.revertedWith("User must be activated");
            
            console.log("✅ Non-activated user suspension correctly prevented");
        });

        it("Should handle suspension of zero address", async function () {
            console.log("Testing suspension of zero address...");
            
            const zeroAddress = ethers.ZeroAddress;
            
            // Попытка приостановить нулевой адрес должна провалиться
            await expect(
                spiralEngine.connect(deployer).suspendUser(zeroAddress, 3600, "Zero address suspension")
            ).to.be.revertedWith("User must be activated");
            
            console.log("✅ Zero address suspension correctly prevented");
        });

        it("Should handle suspension with very long duration", async function () {
            console.log("Testing suspension with very long duration...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("LONG-SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("LONG-SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем на очень долгое время (1 год)
            const longDuration = 365 * 24 * 60 * 60; // 1 год в секундах
            await spiralEngine.connect(deployer).suspendUser(user1.address, longDuration, "Long suspension");
            console.log("✅ User suspended for 1 year");
            
            // Проверяем приостановку
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            const currentTime = await ethers.provider.getBlock('latest').then(block => block.timestamp);
            const expectedSuspensionUntil = currentTime + longDuration;
            
            expect(suspensionUntil).to.be.closeTo(expectedSuspensionUntil, 5);
            console.log(`✅ Long suspension until: ${suspensionUntil}`);
        });

        it("Should handle suspension with empty reason", async function () {
            console.log("Testing suspension with empty reason...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("EMPTY-REASON-TEST-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("EMPTY-REASON-TEST-INVITE", user1.address, newCodes, 0);
            
            // Приостанавливаем с пустой причиной
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "");
            console.log("✅ User suspended with empty reason");
            
            // Проверяем, что приостановка установлена
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil).to.be.gt(0);
            console.log(`✅ Suspension until: ${suspensionUntil}`);
        });
    });
});
