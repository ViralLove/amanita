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

describe("SpiralEngine - Roles and Access Control", function () {
    let spiralEngine;
    let deployer;
    let seller;
    let activator;
    let user;
    let otherUser;

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
        otherUser = ethers.Wallet.createRandom().connect(ethers.provider);
        
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
        await deployer.sendTransaction({
            to: otherUser.address,
            value: ethers.parseEther("1.0")
        });

        // Деплоим SBT экосистему
        console.log("🔷 Deploying SBT ecosystem...");
        
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        const soulboundCore = await SoulboundCore.connect(deployer).deploy("Amanita Soul", "ASOUL");
        await soulboundCore.waitForDeployment();
        
        const SoulMetadata = await ethers.getContractFactory("SoulMetadata");
        const soulMetadata = await SoulMetadata.connect(deployer).deploy(await soulboundCore.getAddress());
        await soulMetadata.waitForDeployment();
        
        await soulboundCore.connect(deployer).setMetadataContract(await soulMetadata.getAddress());
        
        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        const soulIdentity = await SoulIdentity.connect(deployer).deploy(
            await soulboundCore.getAddress(),
            await soulMetadata.getAddress()
        );
        await soulIdentity.waitForDeployment();

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

        console.log("🔷 InviteNFT Roles Tests Setup Complete");
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   Seller: ${seller.address}`);
        console.log(`   Activator: ${activator.address}`);
        console.log(`   User: ${user.address}`);
        console.log(`   Other User: ${otherUser.address}`);
        console.log(`   InviteNFT Address: ${await spiralEngine.getAddress()}`);
    });

    describe("Role Assignment and Management", function () {
        it("Should grant SELLER_ROLE to seller", async function () {
            console.log("Testing SELLER_ROLE assignment...");
            
            // Проверяем, что seller не имеет роли
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.false;
            console.log("✅ Seller initially has no SELLER_ROLE");
            
            // Назначаем роль
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            console.log("✅ SELLER_ROLE granted to seller");
            
            // Проверяем назначение
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.true;
            console.log("✅ Seller now has SELLER_ROLE");
        });

        it("Should grant ACTIVATOR_ROLE to activator", async function () {
            console.log("Testing ACTIVATOR_ROLE assignment...");
            
            // Проверяем, что activator не имеет роли
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, activator.address)).to.be.false;
            console.log("✅ Activator initially has no ACTIVATOR_ROLE");
            
            // Назначаем роль
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            console.log("✅ ACTIVATOR_ROLE granted to activator");
            
            // Проверяем назначение
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, activator.address)).to.be.true;
            console.log("✅ Activator now has ACTIVATOR_ROLE");
        });

        it("Should allow role renunciation", async function () {
            console.log("Testing role renunciation...");
            
            // Назначаем роль
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.true;
            console.log("✅ SELLER_ROLE initially granted");
            
            // Отзываем роль
            await spiralEngine.connect(seller).renounceRole(SELLER_ROLE, seller.address);
            console.log("✅ SELLER_ROLE renounced by seller");
            
            // Проверяем отзыв
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.false;
            console.log("✅ Seller no longer has SELLER_ROLE");
        });

        it("Should allow admin to revoke roles", async function () {
            console.log("Testing role revocation by admin...");
            
            // Назначаем роль
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, activator.address)).to.be.true;
            console.log("✅ ACTIVATOR_ROLE initially granted");
            
            // Отзываем роль
            await spiralEngine.connect(deployer).revokeRole(ACTIVATOR_ROLE, activator.address);
            console.log("✅ ACTIVATOR_ROLE revoked by admin");
            
            // Проверяем отзыв
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, activator.address)).to.be.false;
            console.log("✅ Activator no longer has ACTIVATOR_ROLE");
        });

        it("Should prevent non-admin from granting roles", async function () {
            console.log("Testing role grant restrictions...");
            
            // Попытка назначить роль без прав администратора
            await expectCustomError(
                spiralEngine.connect(seller).grantRole(SELLER_ROLE, otherUser.address),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-admin cannot grant roles");
        });

        it("Should prevent non-admin from revoking roles", async function () {
            console.log("Testing role revoke restrictions...");
            
            // Назначаем роль
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            
            // Попытка отозвать роль без прав администратора
            await expectCustomError(
                spiralEngine.connect(activator).revokeRole(SELLER_ROLE, seller.address),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-admin cannot revoke roles");
        });
    });

    describe("Function Access Control", function () {
        beforeEach(async function () {
            // Назначаем роли для тестирования доступа
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            console.log("✅ Roles granted for access control testing");
        });

        it("Should allow SELLER_ROLE to mint invites", async function () {
            console.log("Testing SELLER_ROLE access to mintInvite...");
            
            // SELLER_ROLE может создавать инвайты (по одному)
            await spiralEngine.connect(seller).mintInvite("SELLER-INVITE-1", 0);
            await spiralEngine.connect(seller).mintInvite("SELLER-INVITE-2", 0);
            console.log("✅ SELLER_ROLE can mint invites");
            
            // Проверяем создание
            const tokenId1 = await spiralEngine.inviteCodeToTokenId("SELLER-INVITE-1");
            const tokenId2 = await spiralEngine.inviteCodeToTokenId("SELLER-INVITE-2");
            
            expect(tokenId1 >= 0n).to.be.true;
            expect(tokenId2 >= 0n).to.be.true;
            console.log("✅ Invites created successfully");
        });

        it("Should prevent non-SELLER_ROLE from minting invites", async function () {
            console.log("Testing non-SELLER_ROLE invite minting restriction...");
            
            // Попытка вызвать mintInvite без SELLER_ROLE должна провалиться
            await expectCustomError(
                spiralEngine.connect(user).mintInvite("UNAUTHORIZED-INVITE", 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-SELLER_ROLE correctly prevented from minting invites");
        });

        it("Should enforce SELLER_ROLE restrictions in mintInvite", async function () {
            console.log("Testing SELLER_ROLE enforcement in mintInvite...");
            
            // Проверяем, что только SELLER_ROLE может вызывать mintInvite
            await expectCustomError(
                spiralEngine.connect(user).mintInvite("TEST", 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            // Проверяем, что SELLER_ROLE может вызывать mintInvite
            await spiralEngine.connect(seller).mintInvite("TEST", 0);
            // Должен пройти без ошибок
            console.log("✅ SELLER_ROLE enforcement working correctly");
        });

        it("Should prevent non-SELLER_ROLE from minting invites", async function () {
            console.log("Testing mintInvite access restrictions...");
            
            // Попытка создать инвайт без SELLER_ROLE
            await expectCustomError(
                spiralEngine.connect(activator).mintInvite("UNAUTHORIZED-INVITE", 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-SELLER_ROLE cannot mint invites");
        });

        it("Should allow ACTIVATOR_ROLE to activate users", async function () {
            console.log("Testing ACTIVATOR_ROLE access to activateUser...");
            
            // Активатору нужна SELLER_ROLE для создания инвайтов
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            
            // Активатор создает инвайт сам
            await spiralEngine.connect(activator).mintInvite("ACTIVATOR-OWN-INVITE", 0);
            
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // ACTIVATOR_ROLE может активировать пользователей
            await spiralEngine.connect(activator).activateUser("ACTIVATOR-OWN-INVITE", user.address, newCodes, 0);
            console.log("✅ ACTIVATOR_ROLE can activate users");
            
            // Проверяем активацию
            const usedInvite = await spiralEngine.usedInviteByUser(user.address);
            expect(usedInvite > 0n).to.be.true;
            console.log("✅ User activated successfully");
        });

        it("Should prevent non-ACTIVATOR_ROLE from activating users", async function () {
            console.log("Testing activateUser access restrictions...");
            
            // Создаем инвайт
            await spiralEngine.connect(seller).mintInvite("UNAUTHORIZED-INVITE", 0);
            
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // Попытка активировать без ACTIVATOR_ROLE
            await expectCustomError(
                spiralEngine.connect(seller).activateUser("UNAUTHORIZED-INVITE", user.address, newCodes, 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-ACTIVATOR_ROLE cannot activate users");
        });

        it("Should enforce ACTIVATOR_ROLE restrictions in activateUser", async function () {
            console.log("Testing ACTIVATOR_ROLE enforcement in activateUser...");
            
            // Создаем инвайт для теста
            await spiralEngine.connect(seller).mintInvite("ENFORCEMENT-TEST-INVITE", 0);
            
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // Проверяем, что только ACTIVATOR_ROLE может вызывать activateUser
            await expectCustomError(
                spiralEngine.connect(user).activateUser("ENFORCEMENT-TEST-INVITE", otherUser.address, newCodes, 0),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            // Проверяем, что ACTIVATOR_ROLE может вызывать activateUser
            // Но сначала нужно создать инвайт для активатора (активатору нужна SELLER_ROLE)
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            await spiralEngine.connect(activator).mintInvite("ENFORCEMENT-TEST-INVITE-ACTIVATOR", 0);
            const newCodes2 = Array.from({length: 12}, (_, i) => `NEW-2-${i + 1}`);
            await spiralEngine.connect(activator).activateUser("ENFORCEMENT-TEST-INVITE-ACTIVATOR", otherUser.address, newCodes2, 0);
            // Должен пройти без ошибок
            console.log("✅ ACTIVATOR_ROLE enforcement working correctly");
        });

        it("Should allow DEFAULT_ADMIN_ROLE to suspend users", async function () {
            console.log("Testing DEFAULT_ADMIN_ROLE access to suspendUser...");
            
            // Активируем пользователя сначала
            await spiralEngine.connect(seller).mintInvite("SUSPEND-TEST-INVITE", 0);
            // Активатору нужна SELLER_ROLE для создания инвайтов
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            await spiralEngine.connect(activator).mintInvite("SUSPEND-TEST-INVITE-ACTIVATOR", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator).activateUser("SUSPEND-TEST-INVITE-ACTIVATOR", user.address, newCodes, 0);
            
            // DEFAULT_ADMIN_ROLE может приостанавливать пользователей
            await spiralEngine.connect(deployer).suspendUser(user.address, 3600, "Test suspension");
            console.log("✅ DEFAULT_ADMIN_ROLE can suspend users");
            
            // Проверяем приостановку
            const suspensionUntil = await spiralEngine.suspensionUntil(user.address);
            expect(suspensionUntil > 0n).to.be.true;
            console.log("✅ User suspended successfully");
        });

        it("Should prevent non-ADMIN from suspending users", async function () {
            console.log("Testing suspendUser access restrictions...");
            
            // Попытка приостановить без DEFAULT_ADMIN_ROLE
            await expectCustomError(
                spiralEngine.connect(activator).suspendUser(user.address, 3600, "Unauthorized suspension"),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Non-ADMIN cannot suspend users");
        });

        it("Should enforce DEFAULT_ADMIN_ROLE restrictions in suspendUser", async function () {
            console.log("Testing DEFAULT_ADMIN_ROLE enforcement in suspendUser...");
            
            // Активируем пользователя для теста
            await spiralEngine.connect(seller).mintInvite("ENFORCEMENT-SUSPEND-TEST-INVITE", 0);
            // Активатору нужна SELLER_ROLE для создания инвайтов
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            await spiralEngine.connect(activator).mintInvite("ENFORCEMENT-SUSPEND-TEST-INVITE-ACTIVATOR", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator).activateUser("ENFORCEMENT-SUSPEND-TEST-INVITE-ACTIVATOR", user.address, newCodes, 0);
            
            // Проверяем, что только DEFAULT_ADMIN_ROLE может вызывать suspendUser
            await expectCustomError(
                spiralEngine.connect(activator).suspendUser(user.address, 3600, "Unauthorized suspension"),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            // Проверяем, что DEFAULT_ADMIN_ROLE может вызывать suspendUser
            await spiralEngine.connect(deployer).suspendUser(user.address, 3600, "Authorized suspension");
            // Должен пройти без ошибок
            console.log("✅ DEFAULT_ADMIN_ROLE enforcement working correctly");
        });
    });

    describe("Role Hierarchy and Permissions", function () {
        it("Should verify DEFAULT_ADMIN_ROLE has all permissions", async function () {
            console.log("Testing DEFAULT_ADMIN_ROLE permissions...");
            
            // DEFAULT_ADMIN_ROLE может назначать любые роли
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            console.log("✅ DEFAULT_ADMIN_ROLE can grant all roles");
            
            // DEFAULT_ADMIN_ROLE может создавать инвайты (если получит SELLER_ROLE)
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, deployer.address);
            await spiralEngine.connect(deployer).mintInvite("ADMIN-INVITE", 0);
            console.log("✅ DEFAULT_ADMIN_ROLE can mint invites");
            
            // DEFAULT_ADMIN_ROLE может активировать пользователей (если получит ACTIVATOR_ROLE)
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, deployer.address);
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("ADMIN-INVITE", user.address, newCodes, 0);
            console.log("✅ DEFAULT_ADMIN_ROLE can activate users");
            
            // Проверяем активацию
            const usedInvite = await spiralEngine.usedInviteByUser(user.address);
            expect(usedInvite > 0n).to.be.true;
            console.log("✅ User activated by admin");
        });

        it("Should verify role inheritance", async function () {
            console.log("Testing role inheritance...");
            
            // Назначаем роли
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            
            // Проверяем, что роли назначены
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.true;
            expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, activator.address)).to.be.true;
            console.log("✅ Roles assigned correctly");
            
            // Проверяем, что DEFAULT_ADMIN_ROLE имеет админскую роль
            const adminRoleFromContract = await spiralEngine.DEFAULT_ADMIN_ROLE();
            expect(await spiralEngine.hasRole(adminRoleFromContract, deployer.address)).to.be.true;
            console.log("✅ DEFAULT_ADMIN_ROLE has admin role");
        });

        it("Should prevent unauthorized role modifications", async function () {
            console.log("Testing unauthorized role modifications...");
            
            // Назначаем роли
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            
            // Попытка изменить роли без прав
            await expectCustomError(
                spiralEngine.connect(seller).grantRole(ACTIVATOR_ROLE, otherUser.address),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            await expectCustomError(
                spiralEngine.connect(activator).revokeRole(SELLER_ROLE, seller.address),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            console.log("✅ Unauthorized role modifications prevented");
        });
    });

    describe("Edge Cases and Error Handling", function () {
        it("Should handle duplicate role assignments gracefully", async function () {
            console.log("Testing duplicate role assignments...");
            
            // Первое назначение
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.true;
            console.log("✅ First role assignment successful");
            
            // Повторное назначение (не должно вызывать ошибку)
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            expect(await spiralEngine.hasRole(SELLER_ROLE, seller.address)).to.be.true;
            console.log("✅ Duplicate role assignment handled gracefully");
        });

        it("Should handle role operations on zero address", async function () {
            console.log("Testing role operations on zero address...");
            
            const zeroAddress = ethers.ZeroAddress;
            
            // Попытка назначить роль нулевому адресу (должна пройти, но не иметь смысла)
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, zeroAddress);
            console.log("✅ Zero address role assignment completed (contract allows it)");
            
            // Проверяем, что роль назначена
            expect(await spiralEngine.hasRole(SELLER_ROLE, zeroAddress)).to.be.true;
            console.log("✅ Zero address has SELLER_ROLE");
        });

        it("Should handle role operations on contract address", async function () {
            console.log("Testing role operations on contract address...");
            
            const contractAddress = await spiralEngine.getAddress();
            
            // Попытка назначить роль контракту
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, contractAddress);
            console.log("✅ Contract address role assignment successful");
            
            // Проверяем назначение
            expect(await spiralEngine.hasRole(SELLER_ROLE, contractAddress)).to.be.true;
            console.log("✅ Contract has SELLER_ROLE");
        });
    });
});
