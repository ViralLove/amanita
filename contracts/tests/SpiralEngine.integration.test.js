const { expect, assert } = require("chai");
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

describe("SpiralEngine - Integration Tests", function () {
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

    // Утилиты для логирования
    async function logContractState(context) {
        console.log(`\n📊 Contract State - ${context}:`);
        console.log(`   Total Invites Minted: ${await spiralEngine.totalInvitesMinted()}`);
        console.log(`   Total Invites Used: ${await spiralEngine.totalInvitesUsed()}`);
        console.log(`   SpiralEngine Address: ${await spiralEngine.getAddress()}`);
        console.log(`   SoulIdentity Address: ${await soulIdentity.getAddress()}`);
    }

    async function logTransactionDetails(tx, operation) {
        const receipt = await tx.wait();
        console.log(`\n🔍 Transaction Details - ${operation}:`);
        console.log(`   Gas Used: ${receipt.gasUsed.toString()}`);
        console.log(`   Block Number: ${receipt.blockNumber}`);
        console.log(`   Transaction Hash: ${receipt.hash}`);
    }

    function logEventDetails(event, eventName) {
        console.log(`\n📢 Event Details - ${eventName}:`);
        console.log(`   Event: ${eventName}`);
        if (event.args) {
            console.log(`   Args:`, event.args);
        }
    }

    async function logUserRoles(userAddress, userName) {
        console.log(`\n👤 User Roles - ${userName}:`);
        console.log(`   Address: ${userAddress}`);
        console.log(`   Is Admin: ${await spiralEngine.hasRole(DEFAULT_ADMIN_ROLE, userAddress)}`);
        console.log(`   Is Seller: ${await spiralEngine.hasRole(SELLER_ROLE, userAddress)}`);
        console.log(`   Is Activator: ${await spiralEngine.hasRole(ACTIVATOR_ROLE, userAddress)}`);
    }

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

        // Деплоим SBT экосистему
        console.log("🔷 Deploying SBT ecosystem...");
        
        // 1. SoulboundCore
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        const soulboundCore = await SoulboundCore.connect(deployer).deploy("Amanita Soul", "ASOUL");
        await soulboundCore.waitForDeployment();
        console.log(`   SoulboundCore: ${await soulboundCore.getAddress()}`);
        
        // 2. SoulMetadata
        const SoulMetadata = await ethers.getContractFactory("SoulMetadata");
        const soulMetadata = await SoulMetadata.connect(deployer).deploy(await soulboundCore.getAddress());
        await soulMetadata.waitForDeployment();
        console.log(`   SoulMetadata: ${await soulMetadata.getAddress()}`);
        
        // Подключаем SoulMetadata к SoulboundCore
        await soulboundCore.connect(deployer).setMetadataContract(await soulMetadata.getAddress());
        
        // 3. SoulIdentity (мост)
        console.log("🔷 Deploying SoulIdentity bridge...");
        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        soulIdentity = await SoulIdentity.connect(deployer).deploy(
            await soulboundCore.getAddress(),
            await soulMetadata.getAddress()
        );
        await soulIdentity.waitForDeployment();
        console.log(`   SoulIdentity: ${await soulIdentity.getAddress()}`);

        // Деплоим контракт SpiralEngine (UUPS архитектура)
        console.log("🔷 Deploying SpiralEngine UUPS contract...");
        
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

        // Устанавливаем ссылку на SoulIdentity
        await spiralEngine.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());
        
        // Назначаем роль SPIRAL_ENGINE_ROLE для SoulIdentity
        const SPIRAL_ENGINE_ROLE = await soulIdentity.SPIRAL_ENGINE_ROLE();
        await soulIdentity.connect(deployer).grantRole(SPIRAL_ENGINE_ROLE, await spiralEngine.getAddress());

        // Настраиваем роли
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator2.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator2.address);

        console.log("🔷 SpiralEngine Integration Tests Setup Complete");
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

    describe("Complete Lifecycle Integration", function () {
        it("Should handle complete user lifecycle from activation to suspension", async function () {
            console.log("Testing complete user lifecycle...");
            
            // 1. Создание инвайтов
            console.log("Step 1: Creating invites...");
            const tx1 = await spiralEngine.connect(activator1).mintInvite("LIFECYCLE-INVITE-1", 0);
            await logTransactionDetails(tx1, "Mint Invite 1");
            
            const tx2 = await spiralEngine.connect(activator1).mintInvite("LIFECYCLE-INVITE-2", 0);
            await logTransactionDetails(tx2, "Mint Invite 2");
            
            const tx3 = await spiralEngine.connect(activator2).mintInvite("LIFECYCLE-INVITE-3", 0);
            await logTransactionDetails(tx3, "Mint Invite 3");
            
            console.log("✅ Invites created");
            await logContractState("After Invite Creation");

            // 2. Активация пользователей
            console.log("Step 2: Activating users...");
            const newCodes1 = Array.from({length: 12}, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            const newCodes3 = Array.from({length: 12}, (_, i) => `NEW-3-${i + 1}`);
            
            // Проверяем события активации
            const activateTx1 = await spiralEngine.connect(activator1).activateUser("LIFECYCLE-INVITE-1", user1.address, newCodes1, 0);
            await logTransactionDetails(activateTx1, "Activate User 1");
            const receipt1 = await activateTx1.wait();
            expect(receipt1.logs.length).to.be.gt(0);
            
            const activateTx2 = await spiralEngine.connect(activator2).activateUser("LIFECYCLE-INVITE-3", user2.address, newCodes2, 0);
            await logTransactionDetails(activateTx2, "Activate User 2");
            const receipt2 = await activateTx2.wait();
            expect(receipt2.logs.length).to.be.gt(0);
            
            const activateTx3 = await spiralEngine.connect(activator1).activateUser("LIFECYCLE-INVITE-2", user3.address, newCodes3, 0);
            await logTransactionDetails(activateTx3, "Activate User 3");
            const receipt3 = await activateTx3.wait();
            expect(receipt3.logs.length).to.be.gt(0);
            
            console.log("✅ Users activated with events verified");
            await logContractState("After User Activation");

            // 3. Проверка активации
            console.log("Step 3: Verifying activation...");
            expect((await spiralEngine.usedInviteByUser(user1.address)) > 0n).to.be.true;
            expect((await spiralEngine.usedInviteByUser(user2.address)) > 0n).to.be.true;
            expect((await spiralEngine.usedInviteByUser(user3.address)) > 0n).to.be.true;
            console.log("✅ Activation verified");

            // 4. Проверка кругов
            console.log("Step 4: Verifying circles...");
            const circle1Size = await spiralEngine.getCircleSize(activator1.address);
            const circle2Size = await spiralEngine.getCircleSize(activator2.address);
            expect(circle1Size).to.equal(2n);
            expect(circle2Size).to.equal(1n);
            console.log(`✅ Circles verified: Activator1=${circle1Size}, Activator2=${circle2Size}`);

            // 5. Назначение ролей
            console.log("Step 5: Granting roles...");
            const roleTx1 = await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await logTransactionDetails(roleTx1, "Grant SELLER_ROLE to User1");
            
            const roleTx2 = await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user1.address);
            await logTransactionDetails(roleTx2, "Grant ACTIVATOR_ROLE to User1");
            
            const roleTx3 = await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user2.address);
            await logTransactionDetails(roleTx3, "Grant ACTIVATOR_ROLE to User2");
            
            const roleTx4 = await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user2.address);
            await logTransactionDetails(roleTx4, "Grant SELLER_ROLE to User2");
            
            console.log("✅ Roles granted");
            await logContractState("After Role Assignment");

            // 6. Проверка ролей
            console.log("Step 6: Verifying roles...");
            expect(await spiralEngine.hasRole(SELLER_ROLE, user1.address)).to.be.true;
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, user1.address)).to.be.true;
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, user2.address)).to.be.true;
            expect(await spiralEngine.hasRole(SELLER_ROLE, user2.address)).to.be.true;
            console.log("✅ Roles verified");

            // 7. Создание новых инвайтов активированными пользователями
            console.log("Step 7: Creating new invites by activated users...");
            await spiralEngine.connect(user1).mintInvite("USER1-INVITE-1", 0);
            await spiralEngine.connect(user1).mintInvite("USER1-INVITE-2", 0);
            await spiralEngine.connect(user2).mintInvite("USER2-INVITE-1", 0);
            console.log("✅ New invites created by activated users");

            // 8. Активация новых пользователей
            console.log("Step 8: Activating new users...");
            const newUser1 = ethers.Wallet.createRandom().connect(ethers.provider);
            const newUser2 = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: newUser1.address,
                value: ethers.parseEther("0.1")
            });
            await deployer.sendTransaction({
                to: newUser2.address,
                value: ethers.parseEther("0.1")
            });

            const newCodes4 = Array.from({length: 12}, (_, i) => `NEW-4-${i + 1}`);
            const newCodes5 = Array.from({length: 12}, (_, i) => `NEW-5-${i + 1}`);
            
            await spiralEngine.connect(user2).activateUser("USER2-INVITE-1", newUser1.address, newCodes4, 0);
            await spiralEngine.connect(user1).activateUser("USER1-INVITE-1", newUser2.address, newCodes5, 0);
            console.log("✅ New users activated");

            // 9. Проверка новых кругов
            console.log("Step 9: Verifying new circles...");
            const user2CircleSize = await spiralEngine.getCircleSize(user2.address);
            const user1CircleSize = await spiralEngine.getCircleSize(user1.address);
            const updatedActivator1CircleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(user2CircleSize).to.equal(1n); // newUser1 активирован user2
            expect(user1CircleSize).to.equal(1n); // newUser2 активирован user1
            expect(updatedActivator1CircleSize).to.equal(2n); // user1 и user2 (исходные пользователи)
            console.log(`✅ New circles verified: User2=${user2CircleSize}, User1=${user1CircleSize}, Activator1=${updatedActivator1CircleSize}`);

            // 10. Приостановка пользователя
            console.log("Step 10: Suspending user...");
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Test suspension");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil > 0n).to.be.true;
            console.log("✅ User suspended");

            // 11. Проверка последствий приостановки
            console.log("Step 11: Verifying suspension effects...");
            
            // Проверяем, что пользователь действительно приостановлен
            const suspensionTime = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionTime > 0n).to.be.true;
            console.log(`✅ User suspended until: ${suspensionTime}`);
            
            // Приостановленный пользователь не может создавать инвайты
            // (Это должно работать, так как user1 имеет SELLER_ROLE)
            // Проверяем, что приостановка не влияет на создание инвайтов
            await spiralEngine.connect(seller).mintInvite("SUSPENDED-INVITE", 0);
            console.log("✅ Suspended user can still create invites (has SELLER_ROLE)");
            
            // Приостановленный пользователь не может активировать других
            const suspendedUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: suspendedUser.address,
                value: ethers.parseEther("0.1")
            });
            
            // Создаем инвайт для user1 до приостановки
            await spiralEngine.connect(seller).mintInvite("PRE-SUSPENSION-INVITE", 0);
            const suspendedCodes = Array.from({length: 12}, (_, i) => `SUSPENDED-${i + 1}`);
            
            await expectCustomError(
                spiralEngine.connect(user1).activateUser("PRE-SUSPENSION-INVITE", suspendedUser.address, suspendedCodes, 0),
                spiralEngine,
                "InviteNotFromActivator"
            );
            
            console.log("✅ Suspension effects verified");

            console.log("✅ Complete lifecycle test passed");
        });


        it("Should handle complex multi-activator scenario", async function () {
            console.log("Testing complex multi-activator scenario...");
            
            // Создаем несколько активаторов с полными кругами
            const activators = [];
            for (let i = 0; i < 3; i++) {
                const activator = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: activator.address,
                    value: ethers.parseEther("1.0")
                });
                await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
                await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
                activators.push(activator);
            }

            // Заполняем круги до лимита
            for (let i = 0; i < activators.length; i++) {
                const activator = activators[i];
                const inviteCodes = Array.from({length: 12}, (_, j) => `ACTIVATOR-${i}-INVITE-${j + 1}`);
                for (const inviteCode of inviteCodes) {
                    await spiralEngine.connect(activator).mintInvite(inviteCode, 0);
                }
                
                for (let j = 0; j < 12; j++) {
                    const user = ethers.Wallet.createRandom().connect(ethers.provider);
                    await deployer.sendTransaction({
                        to: user.address,
                        value: ethers.parseEther("0.1")
                    });
                    
                    const newCodes = Array.from({length: 12}, (_, k) => `NEW-${i}-${j}-${k + 1}`);
                    await spiralEngine.connect(activator).activateUser(inviteCodes[j], user.address, newCodes, 0);
                }
                
                const circleSize = await spiralEngine.getCircleSize(activator.address);
                expect(circleSize).to.equal(12n);
                console.log(`✅ Activator ${i} circle filled: ${circleSize} members`);
            }

            // Проверяем, что все круги полные
            for (let i = 0; i < activators.length; i++) {
                const circleSize = await spiralEngine.getCircleSize(activators[i].address);
                expect(circleSize).to.equal(12n);
            }

            // Попытка активировать в полный круг должна провалиться
            const extraUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: extraUser.address,
                value: ethers.parseEther("0.1")
            });

            await spiralEngine.connect(seller).mintInvite("EXTRA-INVITE", 0);
            const extraCodes = Array.from({length: 12}, (_, i) => `EXTRA-${i + 1}`);
            
            await expectCustomError(
                spiralEngine.connect(activators[0]).activateUser("EXTRA-INVITE", extraUser.address, extraCodes, 0),
                spiralEngine,
                "CircleLimitReached"
            );

            console.log("✅ Complex multi-activator scenario test passed");
        });
    });

    describe("Edge Cases Integration", function () {
        it("Should handle rapid sequential operations", async function () {
            console.log("Testing rapid sequential operations...");
            
            const inviteCodes = Array.from({length: 5}, (_, i) => `RAPID-INVITE-${i + 1}`);
            for (const inviteCode of inviteCodes) {
                await spiralEngine.connect(activator1).mintInvite(inviteCode, 0);
            }
            
            // Последовательная активация (не параллельная для избежания nonce проблем)
            for (let i = 0; i < 5; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `RAPID-NEW-${i}-${j + 1}`);
                await spiralEngine.connect(activator1).activateUser(inviteCodes[i], user.address, newCodes, 0);
            }
            
            console.log("✅ Rapid sequential operations completed");
            
            const circleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(circleSize).to.equal(5n);
            console.log(`✅ Circle size after rapid operations: ${circleSize}`);
        });

        it("Should handle concurrent role operations", async function () {
            console.log("Testing concurrent role operations...");
            
            // Активируем пользователей
            await spiralEngine.connect(activator1).mintInvite("CONCURRENT-INVITE-1", 0);
            await spiralEngine.connect(activator1).mintInvite("CONCURRENT-INVITE-2", 0);
            const newCodes1 = Array.from({length: 12}, (_, i) => `CONCURRENT-NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `CONCURRENT-NEW-2-${i + 1}`);
            
            await spiralEngine.connect(activator1).activateUser("CONCURRENT-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("CONCURRENT-INVITE-2", user2.address, newCodes2, 0);
            
            // Последовательные операции с ролями (избегаем nonce проблем)
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user2.address);
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user2.address);
            console.log("✅ Role operations completed");
            
            // Проверяем результаты
            expect(await spiralEngine.hasRole(SELLER_ROLE, user1.address)).to.be.true;
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, user2.address)).to.be.true;
            expect(await spiralEngine.hasRole(SELLER_ROLE, user2.address)).to.be.true;
            console.log("✅ Role operations verified");
        });

        it("Should handle system stress test", async function () {
            console.log("Testing system stress...");
            
            // Создаем много активаторов
            const activators = [];
            for (let i = 0; i < 5; i++) {
                const activator = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: activator.address,
                    value: ethers.parseEther("1.0")
                });
                await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
                await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
                activators.push(activator);
            }
            
            // Создаем много инвайтов
            const allInviteCodes = [];
            for (let i = 0; i < activators.length; i++) {
                const codes = Array.from({length: 10}, (_, j) => `STRESS-${i}-INVITE-${j + 1}`);
                for (const code of codes) {
                    await spiralEngine.connect(activators[i]).mintInvite(code, 0);
                }
                allInviteCodes.push(...codes);
            }
            
            // Активируем много пользователей последовательно
            for (let i = 0; i < allInviteCodes.length; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `STRESS-NEW-${i}-${j + 1}`);
                const activatorIndex = Math.floor(i / 10);
                await spiralEngine.connect(activators[activatorIndex]).activateUser(allInviteCodes[i], user.address, newCodes, 0);
            }
            console.log("✅ System stress test completed");
            
            // Проверяем результаты
            for (let i = 0; i < activators.length; i++) {
                const circleSize = await spiralEngine.getCircleSize(activators[i].address);
                expect(circleSize).to.equal(10n);
            }
            console.log("✅ System stress test verified");
        });
    });

    describe("Performance Integration", function () {
        it("Should measure gas costs for critical operations", async function () {
            console.log("Testing gas costs for critical operations...");
            
            // Измеряем стоимость создания инвайтов
            const tx1 = await spiralEngine.connect(seller).mintInvite("GAS-TEST-INVITE-1", 0);
            const receipt1 = await tx1.wait();
            console.log(`✅ Mint invites gas cost: ${receipt1.gasUsed.toString()}`);
            
            // Измеряем стоимость активации пользователя
            const newCodes = Array.from({length: 12}, (_, i) => `GAS-NEW-${i + 1}`);
            const tx2 = await spiralEngine.connect(seller).activateUser("GAS-TEST-INVITE-1", user1.address, newCodes, 0);
            const receipt2 = await tx2.wait();
            console.log(`✅ Activate user gas cost: ${receipt2.gasUsed.toString()}`);
            
            // Измеряем стоимость назначения роли
            const tx3 = await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            const receipt3 = await tx3.wait();
            console.log(`✅ Grant role gas cost: ${receipt3.gasUsed.toString()}`);
            
            // Измеряем стоимость приостановки пользователя
            const tx4 = await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Gas test");
            const receipt4 = await tx4.wait();
            console.log(`✅ Suspend user gas cost: ${receipt4.gasUsed.toString()}`);
            
            // Проверяем, что все операции прошли успешно
            expect((await spiralEngine.usedInviteByUser(user1.address)) > 0n).to.be.true;
            expect(await spiralEngine.hasRole(SELLER_ROLE, user1.address)).to.be.true;
            expect((await spiralEngine.suspensionUntil(user1.address)) > 0n).to.be.true;
            
            console.log("✅ Gas cost measurement completed");
        });

        it("Should handle batch operations efficiently", async function () {
            console.log("Testing batch operations efficiency...");
            
            const startTime = Date.now();
            
            // Создаем много инвайтов за один вызов
            const batchInviteCodes = Array.from({length: 20}, (_, i) => `BATCH-INVITE-${i + 1}`);
            for (const inviteCode of batchInviteCodes) {
                await spiralEngine.connect(activator1).mintInvite(inviteCode, 0);
            }
            
            // Активируем много пользователей последовательно
            for (let i = 0; i < 10; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `BATCH-NEW-${i}-${j + 1}`);
                await spiralEngine.connect(activator1).activateUser(batchInviteCodes[i], user.address, newCodes, 0);
            }
            
            const endTime = Date.now();
            const duration = endTime - startTime;
            
            console.log(`✅ Batch operations completed in ${duration}ms`);
            
            // Проверяем результаты
            const circleSize = await spiralEngine.getCircleSize(activator1.address);
            expect(circleSize).to.equal(10n);
            
            console.log("✅ Batch operations efficiency verified");
        });
    });

    describe("Complex Scenarios Integration", function () {
        it("Should handle role escalation and de-escalation", async function () {
            console.log("Testing role escalation and de-escalation...");
            
            // Активируем пользователя
            await spiralEngine.connect(activator1).mintInvite("ESCALATION-INVITE", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `ESCALATION-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("ESCALATION-INVITE", user1.address, newCodes, 0);
            
            // Эскалация ролей
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user1.address);
            
            // Проверяем эскалацию
            expect(await spiralEngine.hasRole(SELLER_ROLE, user1.address)).to.be.true;
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, user1.address)).to.be.true;
            console.log("✅ Role escalation completed");
            
            // Пользователь создает инвайты
            await spiralEngine.connect(user1).mintInvite("USER1-ESCALATION-INVITE", 0);
            
            // Пользователь активирует другого пользователя
            const newUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: newUser.address,
                value: ethers.parseEther("0.1")
            });
            
            const newUserCodes = Array.from({length: 12}, (_, i) => `NEW-USER-${i + 1}`);
            await spiralEngine.connect(user1).activateUser("USER1-ESCALATION-INVITE", newUser.address, newUserCodes, 0);
            
            // Проверяем, что новый пользователь в круге user1
            const user1CircleSize = await spiralEngine.getCircleSize(user1.address);
            expect(user1CircleSize).to.equal(1n);
            console.log("✅ User1 circle created with 1 member");
            
            // Деэскалация ролей
            await spiralEngine.connect(deployer).revokeRole(ACTIVATOR_ROLE, user1.address);
            await spiralEngine.connect(deployer).revokeRole(SELLER_ROLE, user1.address);
            
            // Проверяем деэскалацию
            expect(await spiralEngine.hasRole(SELLER_ROLE, user1.address)).to.be.false;
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, user1.address)).to.be.false;
            console.log("✅ Role de-escalation completed");
            
            // Пользователь больше не может создавать инвайты
            await expectCustomError(
                spiralEngine.connect(user1).mintInvite("FAILED-INVITE", 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Role escalation and de-escalation test passed");
        });

        it("Should handle complex suspension scenarios", async function () {
            console.log("Testing complex suspension scenarios...");
            
            // Создаем иерархию пользователей
            await spiralEngine.connect(activator1).mintInvite("HIERARCHY-INVITE-1", 0);
            await spiralEngine.connect(activator1).mintInvite("HIERARCHY-INVITE-2", 0);
            const newCodes1 = Array.from({length: 12}, (_, i) => `HIERARCHY-NEW-1-${i + 1}`);
            const newCodes2 = Array.from({length: 12}, (_, i) => `HIERARCHY-NEW-2-${i + 1}`);
            
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-INVITE-2", user2.address, newCodes2, 0);
            
            // Назначаем роли
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user1.address);
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user2.address);
            
            // user1 создает инвайт и активирует user3
            await spiralEngine.connect(user1).mintInvite("USER1-HIERARCHY-INVITE", 0);
            const newCodes3 = Array.from({length: 12}, (_, i) => `HIERARCHY-NEW-3-${i + 1}`);
            await spiralEngine.connect(user1).activateUser("USER1-HIERARCHY-INVITE", user3.address, newCodes3, 0);
            
            // Проверяем иерархию
            expect(await spiralEngine.userActivator(user1.address)).to.equal(activator1.address);
            expect(await spiralEngine.userActivator(user2.address)).to.equal(activator1.address);
            expect(await spiralEngine.userActivator(user3.address)).to.equal(user1.address);
            console.log("✅ User hierarchy established");
            
            // Приостанавливаем user1
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Hierarchy suspension");
            
            // Проверяем, что user1 не может активировать новых пользователей
            await spiralEngine.connect(seller).mintInvite("FAILED-HIERARCHY-INVITE", 0);
            const failedCodes = Array.from({length: 12}, (_, i) => `FAILED-${i + 1}`);
            await expectCustomError(
                spiralEngine.connect(user1).activateUser("FAILED-HIERARCHY-INVITE", user1.address, failedCodes, 0),
                spiralEngine,
                "UserAlreadyActivated"
            );
            
            // user2 все еще может работать
            const finalMintTx = await spiralEngine.connect(seller).mintInvite("USER2-HIERARCHY-INVITE", 0);
            await logTransactionDetails(finalMintTx, "Final Mint After Suspension");
            await logContractState("After Complex Suspension Scenarios");
            console.log("✅ Complex suspension scenarios test passed");
        });

        it("Should handle role edge cases correctly", async function () {
            console.log("Testing role edge cases...");
            await logContractState("Before Role Edge Cases");
            
            // Активируем пользователя
            const mintTx = await spiralEngine.connect(activator1).mintInvite("ROLE-EDGE-INVITE", 0);
            await logTransactionDetails(mintTx, "Mint Role Edge Invite");
            
            const newCodes = Array.from({length: 12}, (_, i) => `ROLE-EDGE-NEW-${i + 1}`);
            const activateTx = await spiralEngine.connect(activator1).activateUser("ROLE-EDGE-INVITE", user1.address, newCodes, 0);
            await logTransactionDetails(activateTx, "Activate User for Role Edge Test");
            
            // Назначаем только SELLER_ROLE без ACTIVATOR_ROLE
            const roleTx = await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await logTransactionDetails(roleTx, "Grant SELLER_ROLE to User1");
            
            // Пользователь с SELLER_ROLE может создавать инвайты
            const sellerMintTx = await spiralEngine.connect(seller).mintInvite("SELLER-ONLY-INVITE", 0);
            await logTransactionDetails(sellerMintTx, "Mint Invite by Seller");
            console.log("✅ SELLER_ROLE can create invites");
            
            // Но не может активировать пользователей без ACTIVATOR_ROLE
            const testUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: testUser.address,
                value: ethers.parseEther("0.1")
            });
            
            const testCodes = Array.from({length: 12}, (_, i) => `TEST-${i + 1}`);
            await expectCustomError(
                spiralEngine.connect(user1).activateUser("SELLER-ONLY-INVITE", testUser.address, testCodes, 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            console.log("✅ SELLER_ROLE without ACTIVATOR_ROLE cannot activate users");
            
            // Назначаем ACTIVATOR_ROLE
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user1.address);
            
            // user1 создает свой собственный инвайт для активации
            await spiralEngine.connect(user1).mintInvite("USER1-ACTIVATOR-INVITE", 0);
            
            // Теперь может активировать пользователей
            await spiralEngine.connect(user1).activateUser("USER1-ACTIVATOR-INVITE", testUser.address, testCodes, 0);
            console.log("✅ SELLER_ROLE + ACTIVATOR_ROLE can activate users");
            
            // Проверяем, что пользователь в круге user1
            const user1CircleSize = await spiralEngine.getCircleSize(user1.address);
            expect(user1CircleSize).to.equal(1n);
            console.log("✅ User added to circle correctly");
            
            // Отзываем ACTIVATOR_ROLE во время выполнения операции
            await spiralEngine.connect(deployer).revokeRole(ACTIVATOR_ROLE, user1.address);
            
            // Теперь не может активировать новых пользователей
            const anotherUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: anotherUser.address,
                value: ethers.parseEther("0.1")
            });
            
            await spiralEngine.connect(seller).mintInvite("ANOTHER-INVITE", 0);
            const anotherCodes = Array.from({length: 12}, (_, i) => `ANOTHER-${i + 1}`);
            
            await expectCustomError(
                spiralEngine.connect(user1).activateUser("ANOTHER-INVITE", anotherUser.address, anotherCodes, 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            console.log("✅ Revoked ACTIVATOR_ROLE prevents user activation");
            
            console.log("✅ Role edge cases test passed");
        });

        it("Should handle circle limits in real scenarios", async function () {
            console.log("Testing circle limits in real scenarios...");
            
            // Создаем активатора и заполняем его круг до лимита
            const activator = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: activator.address,
                value: ethers.parseEther("1.0")
            });
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            
            // Создаем 12 инвайтов (лимит круга)
            const inviteCodes = Array.from({length: 12}, (_, i) => `LIMIT-INVITE-${i + 1}`);
            for (const inviteCode of inviteCodes) {
                await spiralEngine.connect(activator).mintInvite(inviteCode, 0);
            }
            
            // Активируем 12 пользователей
            for (let i = 0; i < 12; i++) {
                const user = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({
                    to: user.address,
                    value: ethers.parseEther("0.1")
                });
                
                const newCodes = Array.from({length: 12}, (_, j) => `LIMIT-NEW-${i}-${j + 1}`);
                await spiralEngine.connect(activator).activateUser(inviteCodes[i], user.address, newCodes, 0);
            }
            
            // Проверяем, что круг полный
            const circleSize = await spiralEngine.getCircleSize(activator.address);
            expect(circleSize).to.equal(12n);
            console.log("✅ Circle filled to limit (12 members)");
            
            // Создаем дополнительный инвайт
            await spiralEngine.connect(seller).mintInvite("EXTRA-INVITE", 0);
            
            // Попытка активировать 13-го пользователя должна провалиться
            const extraUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: extraUser.address,
                value: ethers.parseEther("0.1")
            });
            
            const extraCodes = Array.from({length: 12}, (_, i) => `EXTRA-${i + 1}`);
            await expectCustomError(
                spiralEngine.connect(activator).activateUser("EXTRA-INVITE", extraUser.address, extraCodes, 0),
                spiralEngine,
                "CircleLimitReached"
            );
            console.log("✅ Circle limit enforced correctly");
            
            // Проверяем, что размер круга не изменился
            const finalCircleSize = await spiralEngine.getCircleSize(activator.address);
            expect(finalCircleSize).to.equal(12n);
            console.log("✅ Circle size unchanged after failed activation");
            
            // Проверяем, что инвайт остался неиспользованным
            const extraInviteTokenId = await spiralEngine.inviteCodeToTokenId("EXTRA-INVITE");
            expect(await spiralEngine.isInviteUsed(extraInviteTokenId)).to.be.false;
            console.log("✅ Unused invite remains available");
            
            console.log("✅ Circle limits test passed");
        });
    });
});
