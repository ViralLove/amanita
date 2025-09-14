const { expect, assert } = require("chai");
const { ethers } = require("hardhat");

describe("SpiralEngine - SBT (Soulbound Token) Comprehensive Tests", function () {
    let spiralEngine;
    let deployer;
    let seller;
    let activator1;
    let activator2;
    let user1;
    let user2;
    let user3;
    let guardian1;
    let guardian2;

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
        guardian1 = ethers.Wallet.createRandom().connect(ethers.provider);
        guardian2 = ethers.Wallet.createRandom().connect(ethers.provider);

        // Отправляем эфир на новые кошельки
        await deployer.sendTransaction({ to: seller.address, value: ethers.parseEther("1.0") });
        await deployer.sendTransaction({ to: activator1.address, value: ethers.parseEther("1.0") });
        await deployer.sendTransaction({ to: activator2.address, value: ethers.parseEther("1.0") });
        await deployer.sendTransaction({ to: user1.address, value: ethers.parseEther("0.1") });
        await deployer.sendTransaction({ to: user2.address, value: ethers.parseEther("0.1") });
        await deployer.sendTransaction({ to: user3.address, value: ethers.parseEther("0.1") });
        await deployer.sendTransaction({ to: guardian1.address, value: ethers.parseEther("0.1") });
        await deployer.sendTransaction({ to: guardian2.address, value: ethers.parseEther("0.1") });

        // Деплоим контракт SoulIdentity
        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        const soulIdentity = await SoulIdentity.connect(deployer).deploy();
        await soulIdentity.waitForDeployment();

        // Деплой контракта SpiralEngine
        const SpiralEngineFactory = await ethers.getContractFactory("SpiralEngine");
        spiralEngine = await SpiralEngineFactory.deploy();
        await spiralEngine.waitForDeployment();

        // Устанавливаем ссылку на SoulIdentity
        await spiralEngine.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());

        // Назначаем роли
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator2.address);
    });

    describe("P0: Critical SBT Core Properties", function () {
        it("Should enforce non-transferability (transferFrom)", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-CORE-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `CORE-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-CORE-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P0: Критическая проверка - transferFrom должен ревертиться
            await expect(
                spiralEngine.connect(user1).transferFrom(user1.address, user2.address, tokenId)
            ).to.be.revertedWith("InviteNFT: soulbound");
        });

        it("Should enforce non-transferability (safeTransferFrom)", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-SAFE-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `SAFE-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-SAFE-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P0: Критическая проверка - safeTransferFrom должен ревертиться
            await expect(
                spiralEngine.connect(user1).safeTransferFrom(user1.address, user2.address, tokenId)
            ).to.be.revertedWith("InviteNFT: soulbound");
        });

        it("Should block approval delegation (approve)", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-APPROVE-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `APPROVE-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-APPROVE-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P0: Критическая проверка - approve должен ревертиться
            await expect(
                spiralEngine.connect(user1).approve(user2.address, tokenId)
            ).to.be.revertedWith("InviteNFT: SBT tokens cannot be approved");
        });

        it("Should block global approval delegation (setApprovalForAll)", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-GLOBAL-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `GLOBAL-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-GLOBAL-TEST", user1.address, newCodes, 0);
            
            // P0: Критическая проверка - setApprovalForAll должен ревертиться
            await expect(
                spiralEngine.connect(user1).setApprovalForAll(user2.address, true)
            ).to.be.revertedWith("InviteNFT: SBT tokens cannot be approved");
        });

        it("Should return zero address for getApproved", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-GET-APPROVED-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `GET-APPROVED-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-GET-APPROVED-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P0: Критическая проверка - getApproved должен возвращать address(0)
            const approvedAddress = await spiralEngine.connect(user1).getApproved(tokenId);
            expect(approvedAddress).to.equal(ethers.ZeroAddress);
        });

        it("Should return false for isApprovedForAll", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-IS-APPROVED-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `IS-APPROVED-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-IS-APPROVED-TEST", user1.address, newCodes, 0);
            
            // P0: Критическая проверка - isApprovedForAll должен возвращать false
            const isApproved = await spiralEngine.connect(user1).isApprovedForAll(user1.address, user2.address);
            expect(isApproved).to.be.false;
        });
    });

    describe("P0: EIP-5192 SBT Standard Compliance", function () {
        it("Should implement locked() function correctly", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-LOCKED-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `LOCKED-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-LOCKED-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P0: Критическая проверка - locked() должен возвращать true
            const isLocked = await spiralEngine.connect(user1).locked(tokenId);
            expect(isLocked).to.be.true;
        });

        it("Should support IERC5192 interface", async function () {
            // P0: Критическая проверка - контракт должен поддерживать IERC5192
            const IERC5192_INTERFACE_ID = "0xb45a3c0e"; // Примерный interface ID для IERC5192
            
            const supportsInterface = await spiralEngine.connect(deployer).supportsInterface(IERC5192_INTERFACE_ID);
            expect(supportsInterface).to.be.true;
        });

        it("Should revert locked() for non-existent token", async function () {
            const nonExistentTokenId = 999;
            
            // P0: Критическая проверка - locked() должен ревертиться для несуществующего токена
            await expect(
                spiralEngine.connect(user1).locked(nonExistentTokenId)
            ).to.be.revertedWith("Token does not exist");
        });
    });

    describe("P1: SBT Recovery System", function () {
        it("Should allow adding trusted guardians", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-GUARDIAN-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `GUARDIAN-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-GUARDIAN-TEST", user1.address, newCodes, 0);
            
            // P1: Проверка добавления доверенного лица
            await expect(
                spiralEngine.connect(user1).addTrustedGuardian(guardian1.address)
            ).to.emit(spiralEngine, "GuardianAdded")
            .withArgs(user1.address, guardian1.address, await getCurrentTimestamp());
            
            // Проверяем, что guardian добавлен
            const guardians = await spiralEngine.connect(user1).getTrustedGuardians(user1.address);
            expect(guardians).to.include(guardian1.address);
        });

        it("Should enforce guardian limit (max 5)", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-LIMIT-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `LIMIT-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-LIMIT-TEST", user1.address, newCodes, 0);
            
            // Добавляем 5 guardians
            for (let i = 0; i < 5; i++) {
                const guardian = ethers.Wallet.createRandom().connect(ethers.provider);
                await deployer.sendTransaction({ to: guardian.address, value: ethers.parseEther("0.1") });
                await spiralEngine.connect(user1).addTrustedGuardian(guardian.address);
            }
            
            // P1: Проверка лимита - 6-й guardian должен быть отклонен
            const extraGuardian = ethers.Wallet.createRandom().connect(ethers.provider);
            await deployer.sendTransaction({ to: extraGuardian.address, value: ethers.parseEther("0.1") });
            
            await expect(
                spiralEngine.connect(user1).addTrustedGuardian(extraGuardian.address)
            ).to.be.revertedWith("Maximum 5 guardians allowed");
        });

        it("Should allow recovery process initiation", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-RECOVERY-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `RECOVERY-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-RECOVERY-TEST", user1.address, newCodes, 0);
            
            // Добавляем guardian
            await spiralEngine.connect(user1).addTrustedGuardian(guardian1.address);
            
            // P1: Проверка инициации восстановления
            await expect(
                spiralEngine.connect(guardian1).initiateRecovery(user1.address)
            ).to.emit(spiralEngine, "RecoveryInitiated")
            .withArgs(user1.address, guardian1.address, await getCurrentTimestamp());
            
            // Проверяем статус восстановления
            const isRecoveryInProgress = await spiralEngine.connect(user1).isRecoveryInProgress(user1.address);
            expect(isRecoveryInProgress).to.be.true;
        });

        it("Should prevent unauthorized recovery initiation", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-UNAUTH-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `UNAUTH-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-UNAUTH-TEST", user1.address, newCodes, 0);
            
            // P1: Проверка - неавторизованный guardian не может инициировать восстановление
            await expect(
                spiralEngine.connect(guardian1).initiateRecovery(user1.address)
            ).to.be.revertedWith("Not authorized guardian");
        });
    });

    describe("P1: DID Integration and Reputation System", function () {
        it("Should allow linking DID", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-DID-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `DID-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-DID-TEST", user1.address, newCodes, 0);
            
            const testDID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK";
            
            // P1: Проверка связывания DID
            await expect(
                spiralEngine.connect(user1).linkDID(testDID)
            ).to.emit(spiralEngine, "DIDLinked")
            .withArgs(user1.address, testDID, await getCurrentTimestamp());
            
            // Проверяем связь
            const linkedDID = await spiralEngine.connect(user1).userDID(user1.address);
            expect(linkedDID).to.equal(testDID);
            
            const linkedAddress = await spiralEngine.connect(user1).getAddressByDID(testDID);
            expect(linkedAddress).to.equal(user1.address);
        });

        it("Should initialize reputation on DID linking", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-REP-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `REP-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-REP-TEST", user1.address, newCodes, 0);
            
            const testDID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK";
            
            // P1: Проверка инициализации репутации
            await spiralEngine.connect(user1).linkDID(testDID);
            
            const profile = await spiralEngine.connect(user1).getReputationProfile(user1.address);
            expect(profile.reputation).to.equal(100); // Базовый счет
            expect(profile.userVerificationLevel).to.equal(1); // Базовый уровень
        });

        it("Should prevent duplicate DID linking", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-DUP-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `DUP-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-DUP-TEST", user1.address, newCodes, 0);
            
            const testDID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK";
            
            // Связываем DID первый раз
            await spiralEngine.connect(user1).linkDID(testDID);
            
            // P1: Проверка - повторное связывание должно быть отклонено
            await expect(
                spiralEngine.connect(user1).linkDID(testDID)
            ).to.be.revertedWith("User already has DID linked");
        });

        it("Should allow admin to update verification level", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-VERIFY-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `VERIFY-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-VERIFY-TEST", user1.address, newCodes, 0);
            
            const testDID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK";
            await spiralEngine.connect(user1).linkDID(testDID);
            
            // P1: Проверка обновления уровня верификации
            await expect(
                spiralEngine.connect(deployer).updateVerificationLevel(user1.address, 3)
            ).to.emit(spiralEngine, "IdentityVerified")
            .withArgs(user1.address, 3, await getCurrentTimestamp());
            
            const profile = await spiralEngine.connect(user1).getReputationProfile(user1.address);
            expect(profile.userVerificationLevel).to.equal(3);
            expect(profile.reputation).to.equal(160); // 100 + (3 * 20)
        });
    });

    describe("P1: SBT Metadata and Versioning", function () {
        it("Should return proper SBT metadata", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-META-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `META-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-META-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P1: Проверка метаданных SBT
            const metadata = await spiralEngine.connect(user1).getSBTMetadata(tokenId);
            expect(metadata.isLocked).to.be.true;
            expect(metadata.version).to.be.greaterThan(0);
        });

        it("Should allow updating SBT metadata by owner", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-UPDATE-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `UPDATE-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-UPDATE-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            const newSbtType = "Premium Invite";
            const newAttributes = "Special Edition";
            
            // P1: Проверка обновления метаданных
            await expect(
                spiralEngine.connect(user1).updateSBTMetadata(tokenId, newSbtType, newAttributes)
            ).to.emit(spiralEngine, "SBTMetadataUpdated")
            .withArgs(tokenId, newSbtType, newAttributes, await getCurrentTimestamp());
            
            const metadata = await spiralEngine.connect(user1).getSBTMetadata(tokenId);
            expect(metadata.tokenSbtType).to.equal(newSbtType);
            expect(metadata.attributes).to.equal(newAttributes);
        });

        it("Should prevent non-owner from updating metadata", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-NO-UPDATE-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `NO-UPDATE-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-NO-UPDATE-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            
            // P1: Проверка - не-владелец не может обновлять метаданные
            await expect(
                spiralEngine.connect(user2).updateSBTMetadata(tokenId, "Hacked Type", "Hacked Attributes")
            ).to.be.revertedWith("Not token owner");
        });

        it("Should allow admin to update SBT version", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-VERSION-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `VERSION-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-VERSION-TEST", user1.address, newCodes, 0);
            
            const tokenId = 1;
            const newVersion = 2;
            
            // P1: Проверка обновления версии
            await expect(
                spiralEngine.connect(deployer).updateSBTVersion(tokenId, newVersion)
            ).to.emit(spiralEngine, "SBTVersionUpdated")
            .withArgs(tokenId, newVersion, await getCurrentTimestamp());
            
            const version = await spiralEngine.connect(user1).getSBTVersion(tokenId);
            expect(version).to.equal(newVersion);
        });
    });

    describe("P2: Edge Cases and Error Handling", function () {
        it("Should handle temporary key creation and expiration", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-TEMP-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `TEMP-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-TEMP-TEST", user1.address, newCodes, 0);
            
            const tempKey = ethers.Wallet.createRandom().connect(ethers.provider);
            const duration = 3600; // 1 час
            
            // P2: Проверка создания временного ключа
            await expect(
                spiralEngine.connect(user1).createTemporaryKey(tempKey.address, duration)
            ).to.emit(spiralEngine, "TemporaryKeyCreated")
            .withArgs(user1.address, tempKey.address, await getCurrentTimestamp() + duration, await getCurrentTimestamp());
        });

        it("Should prevent duplicate temporary key creation", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-DUP-TEMP-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `DUP-TEMP-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-DUP-TEMP-TEST", user1.address, newCodes, 0);
            
            const tempKey1 = ethers.Wallet.createRandom().connect(ethers.provider);
            const tempKey2 = ethers.Wallet.createRandom().connect(ethers.provider);
            
            // Создаем первый временный ключ
            await spiralEngine.connect(user1).createTemporaryKey(tempKey1.address, 3600);
            
            // P2: Проверка - второй временный ключ должен быть отклонен
            await expect(
                spiralEngine.connect(user1).createTemporaryKey(tempKey2.address, 3600)
            ).to.be.revertedWith("Temporary key already exists");
        });

        it("Should validate reputation requirements", async function () {
            // Создаем токен
            await spiralEngine.connect(seller).mintInvite("SBT-REP-REQ-TEST", 0);
            const newCodes = Array.from({length: 12}, (_, i) => `REP-REQ-NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SBT-REP-REQ-TEST", user1.address, newCodes, 0);
            
            const testDID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK";
            await spiralEngine.connect(user1).linkDID(testDID);
            
            // P2: Проверка репутационных требований
            const hasGoodRep = await spiralEngine.connect(user1).hasGoodReputation(user1.address);
            expect(hasGoodRep).to.be.true; // Должна быть хорошая репутация после связывания DID
        });
    });

    // Вспомогательная функция для получения текущего timestamp
    async function getCurrentTimestamp() {
        const block = await ethers.provider.getBlock('latest');
        return block.timestamp;
    }
});
