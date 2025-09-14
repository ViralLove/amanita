const { expect, assert } = require("chai");
const { ethers } = require("hardhat");

describe("SpiralEngine - Basic Functionality", function () {
    let spiralEngine;
    let soulIdentity;
    let deployer;
    let seller;
    let activator;
    let user;

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
            
            expect(totalMinted).to.equal(0);
            expect(totalUsed).to.equal(0);
            
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
            console.log(`   Minting invite: ${inviteCode}`);
            
            const tx = await spiralEngine.connect(seller).mintInvite(inviteCode, expiry);
            const receipt = await tx.wait();
            
            console.log(`   Gas used: ${receipt.gasUsed.toString()}`);
            
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
            
            // Проверяем состояние
            const tokenId = await spiralEngine.inviteCodeToTokenId(inviteCode);
            expect(tokenId).to.equal(1);
            expect(await spiralEngine.tokenIdToInviteCode(tokenId)).to.equal(inviteCode);
            expect(await spiralEngine.inviteMinter(tokenId)).to.equal(seller.address);
            expect(await spiralEngine.inviteFirstOwner(tokenId)).to.equal(seller.address);
            expect(await spiralEngine.inviteExpiry(tokenId)).to.equal(expiry);
            expect(await spiralEngine.isInviteUsed(tokenId)).to.be.false;
            
            console.log("✅ Invite minted successfully");
        });
        
        it("Should reject empty invite code", async function () {
            console.log("Testing rejection of empty invite code...");
            
            await expect(
                spiralEngine.connect(seller).mintInvite("", 0)
            ).to.be.revertedWith("SpiralEngine: empty invite code");
            
            console.log("✅ Empty invite code correctly rejected");
        });
        
        it("Should reject duplicate invite code", async function () {
            console.log("Testing rejection of duplicate invite code...");
            
            const inviteCode = "DUPLICATE_INVITE";
            await spiralEngine.connect(seller).mintInvite(inviteCode, 0);
            
            await expect(
                spiralEngine.connect(seller).mintInvite(inviteCode, 0)
            ).to.be.revertedWith("SpiralEngine: invite code already exists");
            
            console.log("✅ Duplicate invite code correctly rejected");
        });
        
        it("Should only allow SELLER_ROLE to mint invites", async function () {
            console.log("Testing SELLER_ROLE requirement for minting...");
            
            await expect(
                spiralEngine.connect(user).mintInvite("UNAUTHORIZED_INVITE", 0)
            ).to.be.revertedWith("AccessControl: account " + user.address.toLowerCase() + " is missing role " + SELLER_ROLE);
            
            console.log("✅ Non-SELLER_ROLE correctly prevented from minting");
        });
    });

    describe("User Activation", function () {
        beforeEach(async function () {
            // Создаем инвайт для активации
            await spiralEngine.connect(seller).mintInvite("ACTIVATION_INVITE", 0);
            console.log("✅ Invite created for activation testing");
        });

        it("Should activate user successfully", async function () {
            console.log("Testing user activation...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW_INVITE_${i + 1}`);
            const expiry = 0;
            
            console.log(`   Invite code: ${inviteCode}`);
            console.log(`   New codes count: ${newInviteCodes.length}`);
            
            const tx = await spiralEngine.connect(activator).activateUser(
                inviteCode,
                user.address,
                newInviteCodes,
                expiry
            );
            const receipt = await tx.wait();
            
            console.log(`   Gas used: ${receipt.gasUsed.toString()}`);
            
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
            
            // Проверяем состояние
            expect(await spiralEngine.usedInviteByUser(user.address)).to.equal(1);
            expect(await spiralEngine.userActivator(user.address)).to.equal(activator.address);
            expect(await spiralEngine.isInviteUsed(1)).to.be.true;
            
            // Проверяем создание новых инвайтов
            for (let i = 0; i < newInviteCodes.length; i++) {
                const tokenId = await spiralEngine.inviteCodeToTokenId(newInviteCodes[i]);
                expect(tokenId).to.equal(i + 2); // Первый токен уже занят
                expect(await spiralEngine.inviteMinter(tokenId)).to.equal(user.address);
            }
            
            console.log("✅ User activated successfully");
        });
        
        it("Should reject activation with wrong number of invite codes", async function () {
            console.log("Testing wrong number of invite codes...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const wrongInviteCodes = Array.from({length: 10}, (_, i) => `WRONG_INVITE_${i + 1}`);
            
            console.log(`   Invite code: ${inviteCode}`);
            console.log(`   Wrong codes count: ${wrongInviteCodes.length} (should be 12)`);
            
            await expect(
                spiralEngine.connect(activator).activateUser(
                    inviteCode,
                    user.address,
                    wrongInviteCodes,
                    0
                )
            ).to.be.revertedWith("SpiralEngine: must provide exactly 12 invite codes");
            
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
            
            // Попытка повторной активации
            await expect(
                spiralEngine.connect(activator).activateUser(
                    "NEW_INVITE_1",
                    user.address,
                    newInviteCodes,
                    0
                )
            ).to.be.revertedWith("SpiralEngine: user already activated");
            
            console.log("✅ Double activation prevented");
        });

        it("Should only allow ACTIVATOR_ROLE to activate users", async function () {
            console.log("Testing ACTIVATOR_ROLE requirement...");
            
            const inviteCode = "ACTIVATION_INVITE";
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW_INVITE_${i + 1}`);
            
            await expect(
                spiralEngine.connect(user).activateUser(
                    inviteCode,
                    user.address,
                    newInviteCodes,
                    0
                )
            ).to.be.revertedWith("AccessControl: account " + user.address.toLowerCase() + " is missing role " + ACTIVATOR_ROLE);
            
            console.log("✅ Non-ACTIVATOR_ROLE correctly prevented from activating");
        });
    });

    describe("Seller Role Management", function () {
        beforeEach(async function () {
            // Активируем пользователя
            await spiralEngine.connect(seller).mintInvite("ACTIVATION_INVITE", 0);
            const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW_INVITE_${i + 1}`);
            await spiralEngine.connect(activator).activateUser(
                "ACTIVATION_INVITE",
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
            
            await expect(
                spiralEngine.connect(activator).grantSellerRole(newUser.address)
            ).to.be.revertedWith("SpiralEngine: user not activated");
            
            console.log("✅ Non-activated user correctly rejected");
        });

        it("Should only allow ACTIVATOR_ROLE to grant seller role", async function () {
            console.log("Testing ACTIVATOR_ROLE requirement for granting seller role...");
            
            await expect(
                spiralEngine.connect(user).grantSellerRole(user.address)
            ).to.be.revertedWith("AccessControl: account " + user.address.toLowerCase() + " is missing role " + ACTIVATOR_ROLE);
            
            console.log("✅ Non-ACTIVATOR_ROLE correctly prevented from granting seller role");
        });
    });

    describe("Soul Identity Delegation", function () {
        it("Should delegate soul level query to SoulIdentity", async function () {
            console.log("Testing soul level delegation...");
            
            // Сначала нужно заминтить душу для пользователя
            await soulIdentity.connect(deployer).mintSoul(user.address, 1);
            await soulIdentity.connect(deployer).updateSoulLevel(user.address, 5);
            
            const soulLevel = await spiralEngine.getSoulLevel(user.address);
            expect(soulLevel).to.equal(5);
            
            console.log("✅ Soul level delegation working");
        });

        it("Should revert when SoulIdentity not set", async function () {
            console.log("Testing SoulIdentity not set scenario...");
            
            // Создаем новый SpiralEngine без SoulIdentity
            const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
            const newSpiralEngine = await SpiralEngine.connect(deployer).deploy();
            await newSpiralEngine.waitForDeployment();
            
            await expect(
                newSpiralEngine.getSoulLevel(user.address)
            ).to.be.revertedWith("SpiralEngine: soul identity not set");
            
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
            
            await expect(
                spiralEngine.connect(seller).transferFrom(seller.address, user.address, tokenId)
            ).to.be.revertedWith("SpiralEngine: transfers not allowed");
            
            console.log("✅ Token transfers correctly prevented");
        });
    });
});
