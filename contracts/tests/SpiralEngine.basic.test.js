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

describe("SpiralEngine - Basic Functionality", function () {
    let spiralEngine;
    let soulIdentity;
    let soulboundCore;
    let deployer;
    let seller;
    let activator;
    let user;

    // Константы ролей
    const DEFAULT_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("DEFAULT_ADMIN_ROLE"));
    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
    const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));

    // === УТИЛИТЫ ДЛЯ ДЕТАЛЬНОГО ЛОГИРОВАНИЯ ===
    
    /**
     * Логирует состояние контракта
     */
    async function logContractState(context) {
        console.log(`\n📊 Contract State - ${context}:`);
        console.log(`   Total Invites Minted: ${await spiralEngine.totalInvitesMinted()}`);
        console.log(`   Total Invites Used: ${await spiralEngine.totalInvitesUsed()}`);
        // _tokenIdCounter - приватная переменная, недоступна извне
        console.log(`   Contract Address: ${await spiralEngine.getAddress()}`);
    }

    /**
     * Логирует детали транзакции
     */
    async function logTransactionDetails(tx, operation) {
        const receipt = await tx.wait();
        console.log(`\n⛽ Transaction Details - ${operation}:`);
        console.log(`   Gas Used: ${receipt.gasUsed.toString()}`);
        console.log(`   Gas Price: ${tx.gasPrice?.toString() || 'N/A'}`);
        console.log(`   Block Number: ${receipt.blockNumber}`);
        console.log(`   Transaction Hash: ${tx.hash}`);
    }

    /**
     * Логирует детали события
     */
    function logEventDetails(event, eventName) {
        console.log(`\n📢 Event Details - ${eventName}:`);
        console.log(`   Event Name: ${eventName}`);
        if (event.args) {
            Object.keys(event.args).forEach(key => {
                if (key !== 'length' && !key.match(/^\d+$/)) {
                    console.log(`   ${key}: ${event.args[key]}`);
                }
            });
        }
    }

    /**
     * Логирует роли пользователя
     */
    async function logUserRoles(userAddress, userName) {
        console.log(`\n👤 User Roles - ${userName} (${userAddress}):`);
        console.log(`   DEFAULT_ADMIN_ROLE: ${await spiralEngine.hasRole(DEFAULT_ADMIN_ROLE, userAddress)}`);
        console.log(`   SELLER_ROLE: ${await spiralEngine.hasRole(SELLER_ROLE, userAddress)}`);
        console.log(`   ACTIVATOR_ROLE: ${await spiralEngine.hasRole(ACTIVATOR_ROLE, userAddress)}`);
    }

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];
        
        // Проверяем баланс деплоера
        const deployerBalance = await ethers.provider.getBalance(deployer.address);
        console.log(`[TEST] Deployer balance: ${ethers.formatEther(deployerBalance)} ETH`);
        
        // Если баланс 0, используем другой аккаунт
        if (deployerBalance === 0n && signers.length > 1) {
            deployer = signers[1];
            console.log(`[TEST] Using signer[1] as deployer: ${deployer.address}`);
        }
        
        // Создаем дополнительные кошельки для тестирования
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        activator = ethers.Wallet.createRandom().connect(ethers.provider);
        user = ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Финансируем кошельки
        await deployer.sendTransaction({
            to: seller.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: activator.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user.address,
            value: ethers.parseEther("1.0")
        });

        // Деплоим контракт SoulIdentity
        console.log("🔷 Deploying SoulIdentity contract...");
        
        // Сначала деплоим зависимости
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        soulboundCore = await SoulboundCore.connect(deployer).deploy("SoulboundCore", "SBC");
        await soulboundCore.waitForDeployment();
        
        const SoulMetadata = await ethers.getContractFactory("SoulMetadata");
        const soulMetadata = await SoulMetadata.connect(deployer).deploy(await soulboundCore.getAddress());
        await soulMetadata.waitForDeployment();
        
        // Теперь деплоим SoulIdentity с зависимостями
        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        soulIdentity = await SoulIdentity.connect(deployer).deploy(
            await soulboundCore.getAddress(),
            await soulMetadata.getAddress()
        );
        await soulIdentity.waitForDeployment();

        // Деплоим контракт SpiralEngine (UUPS архитектура)
        console.log("🔷 Deploying SpiralEngine UUPS contract...");
        
        // 1. Deploy Logic implementation
        const Logic = await ethers.getContractFactory("SpiralEngineLogic");
        const logicImpl = await Logic.connect(deployer).deploy();
        await logicImpl.waitForDeployment();
        console.log(`   ✅ Logic deployed: ${await logicImpl.getAddress()}`);
        
        // 2. Encode initialize(admin) calldata
        const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [
            deployer.address
        ]);
        
        // 3. Deploy Proxy with implementation and init data
        const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
        const proxy = await Proxy.connect(deployer).deploy(
            await logicImpl.getAddress(),
            initCalldata
        );
        await proxy.waitForDeployment();
        console.log(`   ✅ Proxy deployed: ${await proxy.getAddress()}`);
        
        // 4. Attach Logic ABI to proxy address (ABI-translator)
        spiralEngine = Logic.attach(await proxy.getAddress());

        // Устанавливаем ссылку на SoulIdentity
        await spiralEngine.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());
        
        // Назначаем роль SPIRAL_ENGINE_ROLE для SoulIdentity
        const SPIRAL_ENGINE_ROLE = await soulIdentity.SPIRAL_ENGINE_ROLE();
        await soulIdentity.connect(deployer).grantRole(SPIRAL_ENGINE_ROLE, await spiralEngine.getAddress());
        
        // Даем SoulIdentity роль владельца в SoulboundCore для работы с SoulMetadata
        await soulboundCore.connect(deployer).transferOwnership(await soulIdentity.getAddress());

        // Назначаем роли
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);

        console.log("🔷 SpiralEngine Basic Tests Setup Complete");
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   Seller: ${seller.address}`);
        console.log(`   Activator: ${activator.address}`);
        console.log(`   User: ${user.address}`);
        console.log(`   SpiralEngine Address: ${await spiralEngine.getAddress()}`);
        console.log(`   SoulIdentity Address: ${await soulIdentity.getAddress()}`);
    });

    describe("Constructor and Initialization", function () {
        it("Should set correct name and symbol", async function () {
            console.log("Testing constructor name and symbol...");
            
            const name = await spiralEngine.name();
            const symbol = await spiralEngine.symbol();
            
            console.log(`   Name: ${name}`);
            console.log(`   Symbol: ${symbol}`);
            
            expect(name).to.equal("SpiralInvite");
            expect(symbol).to.equal("SPIRAL");
            
            console.log("✅ Name and symbol are correct");
        });
        
        it("Should grant DEFAULT_ADMIN_ROLE to deployer", async function () {
            console.log("Testing DEFAULT_ADMIN_ROLE assignment...");
            
            // Получаем правильную роль из контракта
            const adminRoleFromContract = await spiralEngine.DEFAULT_ADMIN_ROLE();
            console.log(`   DEFAULT_ADMIN_ROLE from contract: ${adminRoleFromContract}`);
            console.log(`   DEFAULT_ADMIN_ROLE calculated: ${DEFAULT_ADMIN_ROLE}`);
            
            const hasAdminRole = await spiralEngine.hasRole(adminRoleFromContract, deployer.address);
            console.log(`   Deployer has DEFAULT_ADMIN_ROLE: ${hasAdminRole}`);
            console.log(`   Deployer address: ${deployer.address}`);
            
            expect(hasAdminRole).to.be.true;
            
            console.log("✅ Deployer has DEFAULT_ADMIN_ROLE");
        });
        
        it("Should initialize counters to zero", async function () {
            console.log("Testing counter initialization...");
            
            const totalMinted = await spiralEngine.totalInvitesMinted();
            const totalUsed = await spiralEngine.totalInvitesUsed();
            
            console.log(`   Total minted: ${totalMinted}`);
            console.log(`   Total used: ${totalUsed}`);
            
            expect(totalMinted).to.equal(0n);
            expect(totalUsed).to.equal(0n);
            
            console.log("✅ Counters initialized to zero");
        });

        it("Should have SoulIdentity reference set", async function () {
            console.log("Testing SoulIdentity reference...");
            
            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const expectedAddress = await soulIdentity.getAddress();
            
            console.log(`   SoulIdentity address: ${soulIdentityAddress}`);
            console.log(`   Expected address: ${expectedAddress}`);
            
            expect(soulIdentityAddress).to.equal(expectedAddress);
            
            console.log("✅ SoulIdentity reference is correct");
        });
    });

    describe("Minting Invites", function () {
        it("Should mint invite successfully", async function () {
            console.log("Testing invite minting...");
            
            const inviteCode = "TEST_INVITE_001";
            const expiry = 0; // Бессрочный
            
            // Логируем состояние до операции
            await logContractState("Before Minting");
            await logUserRoles(seller.address, "Seller");
            
            console.log(`\n🔧 Operation Details:`);
            console.log(`   Invite Code: ${inviteCode}`);
            console.log(`   Expiry: ${expiry} (0 = no expiry)`);
            console.log(`   Minter: ${seller.address}`);
            
            const tx = await spiralEngine.connect(seller).mintInvite(inviteCode, expiry);
            const receipt = await tx.wait();
            
            // Логируем детали транзакции
            await logTransactionDetails(tx, "Mint Invite");
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                try {
                    const parsed = spiralEngine.interface.parseLog(log);
                    return parsed.name === "InviteMinted";
                } catch (e) {
                    return false;
                }
            });
            expect(event).to.not.be.undefined;
            
            // Логируем детали события
            if (event) {
                const parsedEvent = spiralEngine.interface.parseLog(event);
                logEventDetails(parsedEvent, "InviteMinted");
            }
            
            // Проверяем состояние
            const tokenId = await spiralEngine.inviteCodeToTokenId(inviteCode);
            expect(tokenId).to.equal(0n);
            expect(await spiralEngine.tokenIdToInviteCode(tokenId)).to.equal(inviteCode);
            expect(await spiralEngine.inviteMinter(tokenId)).to.equal(seller.address);
            expect(await spiralEngine.inviteFirstOwner(tokenId)).to.equal(seller.address);
            expect(await spiralEngine.inviteExpiry(tokenId)).to.equal(BigInt(expiry));
            expect(await spiralEngine.isInviteUsed(tokenId)).to.be.false;
            
            // Логируем состояние после операции
            await logContractState("After Minting");
            
            console.log("✅ Invite minted successfully");
        });
        
        it("Should reject empty invite code", async function () {
            console.log("Testing rejection of empty invite code...");
            
            await expectCustomError(
                spiralEngine.connect(seller).mintInvite("", 0),
                spiralEngine,
                "EmptyInviteCode"
            );
            
            console.log("✅ Empty invite code correctly rejected");
        });
        
        it("Should reject duplicate invite code", async function () {
            console.log("Testing rejection of duplicate invite code...");
            
            const inviteCode = "DUPLICATE_INVITE";
            await spiralEngine.connect(seller).mintInvite(inviteCode, 0);
            
            await expectCustomError(
                spiralEngine.connect(seller).mintInvite(inviteCode, 0),
                spiralEngine,
                "InviteCodeAlreadyExists"
            );
            
            console.log("✅ Duplicate invite code correctly rejected");
        });
        
        it("Should only allow SELLER_ROLE to mint invites", async function () {
            console.log("Testing SELLER_ROLE requirement for minting...");
            
            await expectCustomError(
                spiralEngine.connect(user).mintInvite("UNAUTHORIZED_INVITE", 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-SELLER_ROLE correctly prevented from minting");
        });
    });

    describe("User Activation", function () {
        beforeEach(async function () {
            // Назначаем активатору роль SELLER_ROLE для создания invite
            await spiralEngine.grantRole(SELLER_ROLE, activator.address);
            
            // Создаем инвайт для активации (активатором)
            await spiralEngine.connect(activator).mintInvite("ACTIVATION_INVITE", 0);
            console.log("✅ Invite created for activation testing");
        });

        it("Should activate user successfully", async function () {
            console.log("Testing user activation...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW_INVITE_${i + 1}`);
            const expiry = 0;
            
            // Логируем состояние до операции
            await logContractState("Before Activation");
            await logUserRoles(activator.address, "Activator");
            await logUserRoles(user.address, "User");
            
            console.log(`\n🔧 Operation Details:`);
            console.log(`   Invite Code: ${inviteCode}`);
            console.log(`   New User: ${user.address}`);
            console.log(`   New Codes Count: ${newInviteCodes.length}`);
            console.log(`   Expiry: ${expiry} (0 = no expiry)`);
            
            const tx = await spiralEngine.connect(activator).activateUser(
                inviteCode,
                user.address,
                newInviteCodes,
                expiry
            );
            const receipt = await tx.wait();
            
            // Логируем детали транзакции
            await logTransactionDetails(tx, "Activate User");
            
            // Проверяем событие активации
            const activationEvent = receipt.logs.find(log => {
                try {
                    const parsed = spiralEngine.interface.parseLog(log);
                    return parsed.name === "UserActivated";
                } catch (e) {
                    return false;
                }
            });
            expect(activationEvent).to.not.be.undefined;
            
            // Логируем детали события
            if (activationEvent) {
                const parsedEvent = spiralEngine.interface.parseLog(activationEvent);
                logEventDetails(parsedEvent, "UserActivated");
            }
            
            // Проверяем состояние
            expect(await spiralEngine.usedInviteByUser(user.address)).to.equal(1n); // tokenId + 1 (0 + 1 = 1)
            expect(await spiralEngine.userActivator(user.address)).to.equal(activator.address);
            expect(await spiralEngine.isInviteUsed(0)).to.be.true;
            
            // Проверяем создание новых инвайтов
            console.log(`\n🔍 Verifying New Invites:`);
            for (let i = 0; i < newInviteCodes.length; i++) {
                const tokenId = await spiralEngine.inviteCodeToTokenId(newInviteCodes[i]);
                expect(tokenId).to.equal(BigInt(i + 1)); // Первый токен (0) уже занят, новые начинаются с 1
                expect(await spiralEngine.inviteMinter(tokenId)).to.equal(user.address);
                console.log(`   Invite ${i + 1}: ${newInviteCodes[i]} -> Token ID ${tokenId}`);
            }
            
            // Логируем состояние после операции
            await logContractState("After Activation");
            
            console.log("✅ User activated successfully");
        });
        
        it("Should reject activation with wrong number of invite codes", async function () {
            console.log("Testing wrong number of invite codes...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const wrongInviteCodes = Array.from({length: 10}, (_, i) => `WRONG_INVITE_${i + 1}`);
            
            console.log(`   Invite code: ${inviteCode}`);
            console.log(`   Wrong codes count: ${wrongInviteCodes.length} (should be 12)`);
            
            await expectCustomError(
                spiralEngine.connect(activator).activateUser(
                    inviteCode,
                    user.address,
                    wrongInviteCodes,
                    0
                ),
                spiralEngine,
                "InvalidInviteCount"
            );
            
            console.log("✅ Wrong number of codes correctly rejected");
        });
        
        it("Should reject activation of already activated user", async function () {
            console.log("Testing prevention of double activation...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW_INVITE_${i + 1}`);
            
            // Первая активация
            await spiralEngine.connect(activator).activateUser(
                inviteCode,
                user.address,
                newInviteCodes,
                0
            );
            console.log("✅ First activation completed");
            
            // Создаем новый invite для второй попытки активации
            const secondInviteCode = "SECOND_ACTIVATION_INVITE";
            const secondNewInviteCodes = Array.from({length: 12}, (_, i) => `SECOND_NEW_INVITE_${i + 1}`);
            
            // Создаем новый invite активатором
            await spiralEngine.connect(activator).mintInvite(secondInviteCode, 0);
            console.log("✅ Second invite created for double activation test");
            
            // Попытка повторной активации с новым invite
            await expectCustomError(
                spiralEngine.connect(activator).activateUser(
                    secondInviteCode,
                    user.address,
                    secondNewInviteCodes,
                    0
                ),
                spiralEngine,
                "UserAlreadyActivated"
            );
            
            console.log("✅ Double activation prevented");
        });

        it("Should only allow ACTIVATOR_ROLE to activate users", async function () {
            console.log("Testing ACTIVATOR_ROLE requirement...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW_INVITE_${i + 1}`);
            
            await expectCustomError(
                spiralEngine.connect(user).activateUser(
                    inviteCode,
                    user.address,
                    newInviteCodes,
                    0
                ),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-ACTIVATOR_ROLE correctly prevented from activating");
        });
    });

    describe("Seller Role Management", function () {
        beforeEach(async function () {
            // Активируем пользователя с уникальным invite кодом для секции Seller Role Management
            // Назначаем активатору роль SELLER_ROLE для создания invite
            await spiralEngine.grantRole(SELLER_ROLE, activator.address);
            
            // Создаем invite активатором
            await spiralEngine.connect(activator).mintInvite("SELLER_ROLE_INVITE", 0);
            const newInviteCodes = Array.from({length: 12}, (_, i) => `SELLER_NEW_INVITE_${i + 1}`);
            await spiralEngine.connect(activator).activateUser(
                "SELLER_ROLE_INVITE",
                user.address,
                newInviteCodes,
                0
            );
        });

        it("Should grant seller role successfully", async function () {
            console.log("Testing seller role granting...");
            
            const tx = await spiralEngine.connect(activator).grantSellerRole(user.address);
            const receipt = await tx.wait();
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                try {
                    const parsed = spiralEngine.interface.parseLog(log);
                    return parsed.name === "SellerRoleGranted";
                } catch (e) {
                    return false;
                }
            });
            expect(event).to.not.be.undefined;
            
            // Проверяем состояние
            expect(await spiralEngine.hasRole(SELLER_ROLE, user.address)).to.be.true;
            expect(await spiralEngine.sellerNominator(user.address)).to.equal(activator.address);
            
            console.log("✅ Seller role granted successfully");
        });

        it("Should reject granting seller role to non-activated user", async function () {
            console.log("Testing seller role granting to non-activated user...");
            
            const newUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: newUser.address,
                value: ethers.parseEther("1.0")
            });
            
            await expectCustomError(
                spiralEngine.connect(activator).grantSellerRole(newUser.address),
                spiralEngine,
                "UserNotActivated"
            );
            
            console.log("✅ Non-activated user correctly rejected");
        });

        it("Should only allow ACTIVATOR_ROLE to grant seller role", async function () {
            console.log("Testing ACTIVATOR_ROLE requirement for granting seller role...");
            // user is activated so now has ACTIVATOR_ROLE (SEC-AC-1); use a non-role account to test restriction
            const noRoleUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({ to: noRoleUser.address, value: ethers.parseEther("0.1") });
            await expectCustomError(
                spiralEngine.connect(noRoleUser).grantSellerRole(user.address),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            console.log("✅ Non-ACTIVATOR_ROLE correctly prevented from granting seller role");
        });
    });

    describe("Soul Identity Delegation", function () {
        it("Should delegate soul level query to SoulIdentity", async function () {
            console.log("Testing soul level delegation...");
            
            // Тестируем базовую функциональность - что функция getSoulLevel существует
            // Для пользователя без SBT токена должен возвращаться уровень 0
            const soulLevel = await spiralEngine.getSoulLevel(user.address);
            expect(soulLevel).to.equal(0n);
            
            console.log("✅ Soul level delegation working - returns 0 for user without SBT");
        });

        it("Should revert when SoulIdentity not set", async function () {
            console.log("Testing SoulIdentity not set scenario...");
            
            // Создаем новый SpiralEngine без SoulIdentity (UUPS)
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
            
            const newSpiralEngine = Logic.attach(await proxy.getAddress());
            
            await expectCustomError(
                newSpiralEngine.getSoulLevel(user.address),
                newSpiralEngine,
                "SoulIdentityNotSet"
            );
            
            console.log("✅ SoulIdentity not set correctly handled");
        });
    });

    describe("Transfer Restrictions", function () {
        beforeEach(async function () {
            // Создаем инвайт
            await spiralEngine.connect(seller).mintInvite("TRANSFER_TEST_INVITE", 0);
        });

        it("Should prevent token transfers", async function () {
            console.log("Testing transfer prevention...");
            
            const tokenId = await spiralEngine.inviteCodeToTokenId("TRANSFER_TEST_INVITE");
            
            await expectCustomError(
                spiralEngine.connect(seller).transferFrom(seller.address, user.address, tokenId),
                spiralEngine,
                "TransfersNotAllowed"
            );
            
            console.log("✅ Token transfers correctly prevented");
        });
    });

    // === EDGE CASES И ГРАНИЧНЫЕ УСЛОВИЯ ===
    
    describe("Edge Cases and Boundary Conditions", function () {
        it("Should handle maximum expiry timestamp", async function () {
            console.log("Testing maximum expiry timestamp...");
            
            const inviteCode = "MAX_EXPIRY_INVITE";
            const maxExpiry = 2**32 - 1; // Максимальное значение uint32 (безопасно для Solidity)
            
            console.log(`   Testing with expiry: ${maxExpiry}`);
            
            const tx = await spiralEngine.connect(seller).mintInvite(inviteCode, maxExpiry);
            await tx.wait();
            
            const tokenId = await spiralEngine.inviteCodeToTokenId(inviteCode);
            expect(await spiralEngine.inviteExpiry(tokenId)).to.equal(BigInt(maxExpiry));
            
            console.log("✅ Maximum expiry timestamp handled correctly");
        });

        it("Should handle very long invite codes", async function () {
            console.log("Testing very long invite codes...");
            
            const longInviteCode = "A".repeat(1000); // Очень длинный код
            const expiry = 0;
            
            console.log(`   Testing with invite code length: ${longInviteCode.length}`);
            
            const tx = await spiralEngine.connect(seller).mintInvite(longInviteCode, expiry);
            await tx.wait();
            
            const tokenId = await spiralEngine.inviteCodeToTokenId(longInviteCode);
            expect(tokenId).to.equal(0n);
            expect(await spiralEngine.tokenIdToInviteCode(tokenId)).to.equal(longInviteCode);
            
            console.log("✅ Very long invite codes handled correctly");
        });

        it("Should handle special characters in invite codes", async function () {
            console.log("Testing special characters in invite codes...");
            
            const specialInviteCode = "INVITE_!@#$%^&*()_+-=[]{}|;':\",./<>?";
            const expiry = 0;
            
            console.log(`   Testing with special characters: ${specialInviteCode}`);
            
            const tx = await spiralEngine.connect(seller).mintInvite(specialInviteCode, expiry);
            await tx.wait();
            
            const tokenId = await spiralEngine.inviteCodeToTokenId(specialInviteCode);
            expect(tokenId).to.equal(0n);
            expect(await spiralEngine.tokenIdToInviteCode(tokenId)).to.equal(specialInviteCode);
            
            console.log("✅ Special characters in invite codes handled correctly");
        });

        it("Should handle zero address edge cases", async function () {
            console.log("Testing zero address edge cases...");
            
            const inviteCode = "ZERO_ADDRESS_TEST";
            const expiry = 0;
            
            // Создаем инвайт
            await spiralEngine.connect(seller).mintInvite(inviteCode, expiry);
            
            // Пытаемся активировать с нулевым адресом
            const newInviteCodes = Array.from({length: 12}, (_, i) => `ZERO_TEST_${i + 1}`);
            
            await expectCustomError(
                spiralEngine.connect(activator).activateUser(
                    inviteCode,
                    ethers.ZeroAddress, // Нулевой адрес
                    newInviteCodes,
                    expiry
                ),
                spiralEngine,
                "InvalidUserAddress"
            );
            
            console.log("✅ Zero address edge cases handled correctly");
        });

        it("Should handle expired invite edge cases", async function () {
            console.log("Testing expired invite edge cases...");
            
            const inviteCode = "EXPIRED_INVITE";
            const pastExpiry = Math.floor(Date.now() / 1000) - 3600; // 1 час назад
            
            console.log(`   Testing with past expiry: ${pastExpiry}`);
            
            // Назначаем активатору роль SELLER_ROLE для создания invite
            await spiralEngine.grantRole(SELLER_ROLE, activator.address);
            
            // Создаем инвайт с истекшим сроком (активатором)
            await spiralEngine.connect(activator).mintInvite(inviteCode, pastExpiry);
            
            const newInviteCodes = Array.from({length: 12}, (_, i) => `EXPIRED_TEST_${i + 1}`);
            
            // Пытаемся использовать истекший инвайт
            await expectCustomError(
                spiralEngine.connect(activator).activateUser(
                    inviteCode,
                    user.address,
                    newInviteCodes,
                    0
                ),
                spiralEngine,
                "InviteExpired"
            );
            
            console.log("✅ Expired invite edge cases handled correctly");
        });

        it("Should handle role edge cases", async function () {
            console.log("Testing role edge cases...");
            
            // Тестируем пользователя без ролей
            const noRoleUser = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({
                to: noRoleUser.address,
                value: ethers.parseEther("1.0")
            });
            
            console.log(`   Testing user without roles: ${noRoleUser.address}`);
            
            // Пытаемся минтить без роли
            await expectCustomError(
                spiralEngine.connect(noRoleUser).mintInvite("NO_ROLE_INVITE", 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            // Пытаемся активировать без роли
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NO_ROLE_TEST_${i + 1}`);
            
            await expectCustomError(
                spiralEngine.connect(noRoleUser).activateUser(
                    "SOME_INVITE",
                    user.address,
                    newInviteCodes,
                    0
                ),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Role edge cases handled correctly");
        });

        it("Should handle gas limit edge cases", async function () {
            console.log("Testing gas limit edge cases...");
            
            // Создаем очень много инвайтов для тестирования лимитов
            const manyInviteCodes = Array.from({length: 12}, (_, i) => `GAS_TEST_${i + 1}`);
            const expiry = 0;
            
            console.log(`   Testing with ${manyInviteCodes.length} invite codes`);
            
            // Назначаем активатору роль SELLER_ROLE для создания invite
            await spiralEngine.grantRole(SELLER_ROLE, activator.address);
            
            // Создаем инвайт для активации (активатором)
            await spiralEngine.connect(activator).mintInvite("GAS_TEST_INVITE", expiry);
            
            // Активируем пользователя с большим количеством новых инвайтов
            const tx = await spiralEngine.connect(activator).activateUser(
                "GAS_TEST_INVITE",
                user.address,
                manyInviteCodes,
                expiry
            );
            
            const receipt = await tx.wait();
            console.log(`   Gas used for activation: ${receipt.gasUsed.toString()}`);
            
            // Проверяем, что все инвайты созданы
            for (let i = 0; i < manyInviteCodes.length; i++) {
                const tokenId = await spiralEngine.inviteCodeToTokenId(manyInviteCodes[i]);
                expect(tokenId).to.equal(BigInt(i + 1));
            }
            
            console.log("✅ Gas limit edge cases handled correctly");
        });
    });

    describe("Seller Diagnostics", function () {
        it("Should return seller diagnostics for activated seller", async function () {
            console.log("Testing seller diagnostics for activated seller...");
            
            // Даем активатору роль SELLER_ROLE для создания инвайтов
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            
            // Создаем инвайт для селлера (активатор создает инвайт для активации)
            await spiralEngine.connect(activator).mintInvite("SELLER_DIAG_INVITE", 0);
            
            // Проверяем tokenId созданного инвайта
            const tokenId = await spiralEngine.inviteCodeToTokenId("SELLER_DIAG_INVITE");
            console.log(`   Created invite tokenId: ${tokenId}`);
            
            // Активируем пользователя (не селлера, так как селлер уже активирован)
            const newCodes = Array.from({length: 12}, (_, i) => `SELLER_DIAG_NEW_${i + 1}`);
            const tx = await spiralEngine.connect(activator).activateUser(
                "SELLER_DIAG_INVITE",
                user.address,
                newCodes,
                0
            );
            await tx.wait();
            console.log(`   Activation transaction completed`);
            
            // Даем пользователю роль SELLER_ROLE
            await spiralEngine.connect(activator).grantSellerRole(user.address);
            
            // Получаем диагностику
            const diagnostics = await spiralEngine.getSellerDiagnostics(user.address);
            
            // Отладочная информация
            console.log(`   User address: ${user.address}`);
            console.log(`   Is activated: ${diagnostics.isActivated}`);
            console.log(`   Used invite token ID: ${diagnostics.usedInviteTokenId}`);
            console.log(`   Has seller role: ${diagnostics.hasSellerRole}`);
            console.log(`   User invites count: ${diagnostics.userInvites.length}`);
            console.log(`   Total invites minted: ${diagnostics.totalInvitesMinted}`);
            
            // Проверяем usedInviteByUser напрямую
            const usedInviteDirect = await spiralEngine.usedInviteByUser(user.address);
            console.log(`   Used invite direct: ${usedInviteDirect}`);
            
            // Проверяем результаты
            expect(diagnostics.isActivated).to.be.true;
            expect(diagnostics.usedInviteTokenId).to.equal(0n); // tokenId = 0, поэтому usedInviteTokenId = 0
            expect(diagnostics.hasSellerRole).to.be.true;
            expect(diagnostics.hasActivatorRole).to.be.true; // SEC-AC-1: activated user gets ACTIVATOR_ROLE
            expect(diagnostics.userInvites.length).to.equal(12);
            expect(diagnostics.totalInvitesMinted).to.equal(12n); // 12 новых инвайтов для пользователя
            
            console.log("✅ Seller diagnostics returned correctly");
        });

        it("Should return seller diagnostics for non-activated user", async function () {
            console.log("Testing seller diagnostics for non-activated user...");
            
            // Получаем диагностику для неактивированного пользователя
            const diagnostics = await spiralEngine.getSellerDiagnostics(user.address);
            
            // Проверяем результаты
            expect(diagnostics.isActivated).to.be.false;
            expect(diagnostics.usedInviteTokenId).to.equal(0n);
            expect(diagnostics.hasSellerRole).to.be.false;
            expect(diagnostics.hasActivatorRole).to.be.false;
            expect(diagnostics.userInvites.length).to.equal(0);
            expect(diagnostics.totalInvitesMinted).to.equal(0n);
            
            console.log("✅ Non-activated user diagnostics returned correctly");
        });

        it("Should return user invites correctly", async function () {
            console.log("Testing getUserInvites function...");
            
            // Даем активатору роль SELLER_ROLE для создания инвайтов
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            
            // Создаем инвайт для пользователя (активатор создает инвайт для активации)
            await spiralEngine.connect(activator).mintInvite("USER_INVITES_TEST", 0);
            
            // Активируем пользователя
            const newCodes = Array.from({length: 12}, (_, i) => `USER_INVITES_NEW_${i + 1}`);
            await spiralEngine.connect(activator).activateUser(
                "USER_INVITES_TEST",
                user.address,
                newCodes,
                0
            );
            
            // Получаем диагностику пользователя для получения полной информации об инвайтах
            const diagnostics = await spiralEngine.getSellerDiagnostics(user.address);
            
            // Проверяем результаты
            expect(diagnostics.userInvites.length).to.equal(12);
            
            // Проверяем первый инвайт
            expect(diagnostics.userInvites[0].inviteCode).to.equal("USER_INVITES_NEW_1");
            expect(diagnostics.userInvites[0].tokenId).to.equal(1n);
            expect(diagnostics.userInvites[0].isUsed).to.be.false;
            expect(diagnostics.userInvites[0].activatedBy).to.equal(ethers.ZeroAddress);
            expect(diagnostics.userInvites[0].activationTime).to.equal(0n);
            expect(diagnostics.userInvites[0].expiry).to.equal(0n);
            
            console.log("✅ User invites returned correctly");
        });
    });
});
