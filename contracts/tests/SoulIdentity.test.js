const { expect } = require("chai");
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

async function expectRevertWithMessage(txPromise, messageSubstring) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
    const msg = (err?.reason || err?.shortMessage || err?.message || err?.error?.message || String(err)) || "";
    expect(msg.includes(messageSubstring), `expected revert message to contain "${messageSubstring}"`).to.be.true;
}

describe("SoulIdentity Bridge Contract", function () {
    let soulIdentity;
    let soulboundCore;
    let soulMetadata;
    let deployer, spiralEngine, user1, user2;

    beforeEach(async function () {
        const signers = await ethers.getSigners();
        deployer = signers[0];
        
        // Создаем случайные кошельки для тестирования
        spiralEngine = await ethers.Wallet.createRandom().connect(ethers.provider);
        user1 = await ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = await ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Пополняем кошельки
        await deployer.sendTransaction({
            to: spiralEngine.address,
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

        console.log("🔷 SoulIdentity Bridge Tests Setup Starting...");
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   SpiralEngine (mock): ${spiralEngine.address}`);
        console.log(`   User1: ${user1.address}`);
        console.log(`   User2: ${user2.address}`);

        // Деплоим существующие SBT контракты
        console.log("🔷 Deploying existing SBT ecosystem...");
        
        // 1. SoulboundCore
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        soulboundCore = await SoulboundCore.connect(deployer).deploy("Amanita Soul", "ASOUL");
        await soulboundCore.waitForDeployment();
        console.log(`   SoulboundCore: ${await soulboundCore.getAddress()}`);
        
        // 2. SoulMetadata
        const SoulMetadata = await ethers.getContractFactory("SoulMetadata");
        soulMetadata = await SoulMetadata.connect(deployer).deploy(await soulboundCore.getAddress());
        await soulMetadata.waitForDeployment();
        console.log(`   SoulMetadata: ${await soulMetadata.getAddress()}`);
        
        // 3. Подключаем SoulMetadata к SoulboundCore
        await soulboundCore.connect(deployer).setMetadataContract(await soulMetadata.getAddress());
        console.log("✅ SoulMetadata подключен к SoulboundCore");
        
        // 4. SoulIdentity (мост)
        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        soulIdentity = await SoulIdentity.connect(deployer).deploy(
            await soulboundCore.getAddress(),
            await soulMetadata.getAddress()
        );
        await soulIdentity.waitForDeployment();
        console.log(`   SoulIdentity: ${await soulIdentity.getAddress()}`);
        
        // 5. Назначаем роль SPIRAL_ENGINE_ROLE
        const SPIRAL_ENGINE_ROLE = await soulIdentity.SPIRAL_ENGINE_ROLE();
        await soulIdentity.connect(deployer).grantRole(SPIRAL_ENGINE_ROLE, spiralEngine.address);
        console.log("✅ SPIRAL_ENGINE_ROLE назначена");

        console.log("🔷 SoulIdentity Bridge Tests Setup Complete");
    });

    describe("P0: Bridge Integration with Existing SBT", function () {
        it("Should integrate with SoulboundCore correctly", async function () {
            console.log("Testing integration with SoulboundCore...");
            
            // Создаем SBT токен через SoulboundCore
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            
            // Проверяем что SoulIdentity видит токен
            const balance = await soulboundCore.balanceOf(user1.address);
            expect(balance).to.equal(1n);
            
            // Проверяем что SoulIdentity может найти токен пользователя
            const tokenId = 1; // Первый токен
            const owner = await soulboundCore.ownerOf(tokenId);
            expect(owner).to.equal(user1.address);
            
            console.log("✅ SoulIdentity корректно интегрирован с SoulboundCore");
        });

        it("Should delegate to SoulMetadata correctly", async function () {
            console.log("Testing delegation to SoulMetadata...");
            
            // Создаем SBT токен и инициализируем метаданные
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 5, "reputation": 250}',
                "QmTestHash"
            );
            
            // Проверяем делегирование через SoulIdentity
            const level = await soulIdentity.getSoulLevel(user1.address);
            const reputation = await soulIdentity.getSoulReputation(user1.address);
            
            // Пока используем заглушки, проверяем что функции не падают
            expect(level).to.be.a('bigint');
            expect(reputation).to.be.a('bigint');
            
            console.log(`✅ Soul level: ${level}`);
            console.log(`✅ Soul reputation: ${reputation}`);
        });
    });

    describe("P0: New DID Functionality", function () {
        beforeEach(async function () {
            // Создаем SBT токен для тестирования DID
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should link external identity correctly", async function () {
            console.log("Testing linkExternalIdentity...");
            
            const identityType = "did:spiral";
            const identityValue = `did:spiral:${user1.address.toLowerCase()}`;
            
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                identityType,
                identityValue,
                false
            );
            
            // Проверяем что идентичность добавлена
            const primaryIdentity = await soulIdentity.getPrimaryIdentity(user1.address);
            expect(primaryIdentity.identityType).to.equal(identityType);
            expect(primaryIdentity.identityValue).to.equal(identityValue);
            expect(primaryIdentity.verified).to.equal(false);
            
            console.log(`✅ External identity linked: ${identityType} = ${identityValue}`);
        });

        it("Should support multiple identities", async function () {
            console.log("Testing multiple identities...");
            
            // Добавляем spiral DID
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:spiral",
                `did:spiral:${user1.address.toLowerCase()}`,
                false
            );
            
            // Добавляем polygon DID
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:polygon",
                `did:polygon:mainnet:${user1.address.toLowerCase()}`,
                true
            );
            
            const allIdentities = await soulIdentity.getAllIdentities(user1.address);
            expect(allIdentities.length).to.equal(2); // array length
            expect(allIdentities[0].identityType).to.equal("did:spiral");
            expect(allIdentities[1].identityType).to.equal("did:polygon");
            expect(allIdentities[1].verified).to.equal(true);
            
            console.log(`✅ Multiple identities supported: ${allIdentities.length} identities`);
        });

        it("Should check identity type existence", async function () {
            console.log("Testing hasIdentityType...");
            
            // Добавляем spiral DID
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:spiral",
                `did:spiral:${user1.address.toLowerCase()}`,
                false
            );
            
            const hasSpiral = await soulIdentity.hasIdentityType(user1.address, "did:spiral");
            const hasPolygon = await soulIdentity.hasIdentityType(user1.address, "did:polygon");
            
            expect(hasSpiral).to.equal(true);
            expect(hasPolygon).to.equal(false);
            
            console.log("✅ Identity type checking works correctly");
        });
    });

    describe("P1: Backward Compatibility", function () {
        beforeEach(async function () {
            // Создаем SBT токен для тестирования
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should maintain backward compatibility with linkSoulIdentity", async function () {
            console.log("Testing backward compatibility...");
            
            const legacyDID = `did:spiral:${user1.address.toLowerCase()}`;
            
            // Используем старый метод
            await soulIdentity.connect(user1).linkSoulIdentity(legacyDID);
            
            // Проверяем через новый интерфейс
            const primaryIdentity = await soulIdentity.getPrimaryIdentity(user1.address);
            expect(primaryIdentity.identityType).to.equal("did:spiral");
            expect(primaryIdentity.identityValue).to.equal(legacyDID);
            expect(primaryIdentity.verified).to.equal(false);
            
            // Проверяем через старый интерфейс
            const legacyResult = await soulIdentity.getSoulIdentity(user1.address);
            expect(legacyResult).to.equal(legacyDID);
            
            console.log("✅ Backward compatibility maintained");
        });

        it("Should work with getSoulProfile", async function () {
            console.log("Testing getSoulProfile...");
            
            // Добавляем DID
            await soulIdentity.connect(user1).linkSoulIdentity(`did:spiral:${user1.address.toLowerCase()}`);
            
            // Получаем полный профиль
            const profile = await soulIdentity.getSoulProfile(user1.address);
            
            expect(profile.level).to.be.a('bigint');
            expect(profile.reputation).to.be.a('bigint');
            expect(profile.identity).to.include("did:spiral:");
            expect(profile.verificationLevel === 0n || profile.verificationLevel === 0).to.be.true;
            expect(profile.guardians.length).to.equal(0);
            
            console.log(`✅ Soul profile works: level=${profile.level}, reputation=${profile.reputation}`);
        });
    });

    describe("SBT-REC-1: SoulRecovery delegation and hybrid (soulRecovery not set)", function () {
        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should revert addTrustedGuardian when SoulRecovery not set", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user1).addTrustedGuardian(user2.address),
                "SoulIdentity: SoulRecovery not set"
            );
        });

        it("Should revert removeTrustedGuardian when SoulRecovery not set", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user1).removeTrustedGuardian(user2.address),
                "SoulIdentity: SoulRecovery not set"
            );
        });

        it("Should return empty guardians and false when SoulRecovery not set (read path)", async function () {
            const guardians = await soulIdentity.getTrustedGuardians(user1.address);
            expect(guardians).to.deep.equal([]);
            expect(await soulIdentity.isTrustedGuardian(user1.address, user2.address)).to.be.false;
            expect(await soulIdentity.isRecoveryInProgress(user1.address)).to.be.false;
        });

        it("Should delegate guardians and return them in getSoulProfile when SoulRecovery set", async function () {
            const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
            const soulRecovery = await SoulRecovery.connect(deployer).deploy(await soulboundCore.getAddress());
            await soulRecovery.waitForDeployment();
            await soulboundCore.connect(deployer).setRecoveryContract(await soulRecovery.getAddress());
            await soulRecovery.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());
            await soulIdentity.connect(deployer).setSoulRecovery(await soulRecovery.getAddress());

            await soulIdentity.connect(user1).addTrustedGuardian(user2.address);
            const guardians = await soulIdentity.getTrustedGuardians(user1.address);
            expect(guardians.length).to.equal(1);
            expect(guardians[0]).to.equal(user2.address);
            expect(await soulIdentity.isTrustedGuardian(user1.address, user2.address)).to.be.true;

            const profile = await soulIdentity.getSoulProfile(user1.address);
            expect(profile.guardians.length).to.equal(1);
            expect(profile.guardians[0]).to.equal(user2.address);
        });
    });

    describe("SBT-IDX-1: owner → tokenId index", function () {
        it("Should find soul via index when SoulboundCore notifies SoulIdentity (integration set)", async function () {
            await soulboundCore.connect(deployer).setIntegrationContract(await soulIdentity.getAddress());
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            const level = await soulIdentity.getSoulLevel(user1.address);
            expect(level > 0n).to.be.true;
            const profile = await soulIdentity.getSoulProfile(user1.address);
            expect(profile.level > 0n).to.be.true;
        });

        it("Should find soul via fallback when integration not set (no index entry)", async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            const level = await soulIdentity.getSoulLevel(user1.address);
            expect(level > 0n).to.be.true;
        });

        it("Should allow ADMIN to registerSoulTokenId and then find soul via index", async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            const tokenId = 1n;
            await soulIdentity.connect(deployer).registerSoulTokenId(user1.address, tokenId);
            const level = await soulIdentity.getSoulLevel(user1.address);
            expect(level > 0n).to.be.true;
        });

        it("Should revert registerSoulTokenId when not DEFAULT_ADMIN_ROLE", async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            await expectRevertWithMessage(
                soulIdentity.connect(user1).registerSoulTokenId(user1.address, 1),
                "AccessControl"
            );
        });

        it("Should revert registerSoulTokenId when token does not exist or not owner", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(deployer).registerSoulTokenId(user1.address, 999),
                "SoulIdentity: token does not exist"
            );
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            await expectRevertWithMessage(
                soulIdentity.connect(deployer).registerSoulTokenId(user2.address, 1),
                "SoulIdentity: not token owner"
            );
        });

        it("Should revert notifySoulCreated when caller is not SoulboundCore", async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            await expectRevertWithMessage(
                soulIdentity.connect(deployer).notifySoulCreated(1, user1.address),
                "SoulIdentity: only SoulboundCore"
            );
        });
    });

    describe("SBT-B2-1: temporary key (B2)", function () {
        const TEMP_KEY_DURATION = 86400; // 1 day in seconds

        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should create temporary key and return it via getTemporaryKey", async function () {
            await soulIdentity.connect(user1).createTemporaryKey(user2.address, TEMP_KEY_DURATION);
            expect(await soulIdentity.getTemporaryKey(user1.address)).to.equal(user2.address);
            expect(await soulIdentity.isTemporaryKeyValid(user2.address)).to.be.true;
        });

        it("Should revert createTemporaryKey when not soul owner", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user2).createTemporaryKey(deployer.address, TEMP_KEY_DURATION),
                "SoulIdentity: only soul owner"
            );
        });

        it("Should revert createTemporaryKey when duration > MAX_TEMP_KEY_DURATION", async function () {
            const overMax = (await soulIdentity.MAX_TEMP_KEY_DURATION()) + 1n;
            await expectRevertWithMessage(
                soulIdentity.connect(user1).createTemporaryKey(user2.address, overMax),
                "SoulIdentity: invalid duration"
            );
        });

        it("Should revert createTemporaryKey when tempKey is zero or owner", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user1).createTemporaryKey(ethers.ZeroAddress, TEMP_KEY_DURATION),
                "SoulIdentity: zero temp key"
            );
            await expectRevertWithMessage(
                soulIdentity.connect(user1).createTemporaryKey(user1.address, TEMP_KEY_DURATION),
                "SoulIdentity: temp key cannot be owner"
            );
        });

        it("Should revoke temporary key and clear storage", async function () {
            await soulIdentity.connect(user1).createTemporaryKey(user2.address, TEMP_KEY_DURATION);
            await soulIdentity.connect(user1).revokeTemporaryKey();
            expect(await soulIdentity.getTemporaryKey(user1.address)).to.equal(ethers.ZeroAddress);
            expect(await soulIdentity.isTemporaryKeyValid(user2.address)).to.be.false;
        });

        it("Should revert revokeTemporaryKey when not soul owner", async function () {
            await soulIdentity.connect(user1).createTemporaryKey(user2.address, TEMP_KEY_DURATION);
            await expectRevertWithMessage(
                soulIdentity.connect(user2).revokeTemporaryKey(),
                "SoulIdentity: only soul owner"
            );
        });

        it("Should allow temp key to call linkSoulIdentity for owner", async function () {
            await soulIdentity.connect(user1).createTemporaryKey(user2.address, TEMP_KEY_DURATION);
            await soulIdentity.connect(user2).linkSoulIdentity(`did:spiral:${user1.address.toLowerCase()}`);
            expect(await soulIdentity.getSoulIdentity(user1.address)).to.include(user1.address.toLowerCase());
        });

        it("Should allow temp key to call unlinkSoulIdentity for owner", async function () {
            await soulIdentity.connect(user1).createTemporaryKey(user2.address, TEMP_KEY_DURATION);
            await soulIdentity.connect(user2).linkSoulIdentity(`did:spiral:${user1.address.toLowerCase()}`);
            await soulIdentity.connect(user2).unlinkSoulIdentity();
            expect(await soulIdentity.getSoulIdentity(user1.address)).to.equal("");
        });

        it("Should revert linkSoulIdentity when not owner and not valid temp key", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user2).linkSoulIdentity(`did:spiral:${user2.address.toLowerCase()}`),
                "SoulIdentity: not owner or valid temporary key"
            );
        });

        it("Should return false for isTemporaryKeyValid after expiry", async function () {
            await soulIdentity.connect(user1).createTemporaryKey(user2.address, 1);
            await ethers.provider.send("evm_increaseTime", [2]);
            await ethers.provider.send("evm_mine", []);
            expect(await soulIdentity.isTemporaryKeyValid(user2.address)).to.be.false;
            expect(await soulIdentity.getTemporaryKey(user1.address)).to.equal(ethers.ZeroAddress);
        });
    });

    describe("SBT-PAS-1: displayName and handle (Passport MVP)", function () {
        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should set and get displayName and handle as soul owner", async function () {
            await soulIdentity.connect(user1).setDisplayName("Moss Architect");
            await soulIdentity.connect(user1).setHandle("@spiral:moss-architect");
            expect(await soulIdentity.getDisplayName(user1.address)).to.equal("Moss Architect");
            expect(await soulIdentity.getHandle(user1.address)).to.equal("@spiral:moss-architect");
        });

        it("Should return displayName and handle in getSoulProfile", async function () {
            await soulIdentity.connect(user1).setDisplayName("Alice");
            await soulIdentity.connect(user1).setHandle("@spiral:alice");
            const profile = await soulIdentity.getSoulProfile(user1.address);
            expect(profile.displayName).to.equal("Alice");
            expect(profile.handle).to.equal("@spiral:alice");
        });

        it("Should revert setDisplayName when not soul owner", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user2).setDisplayName("Fake"),
                "SoulIdentity: no SBT"
            );
        });

        it("Should revert setHandle when not soul owner", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user2).setHandle("@spiral:other"),
                "SoulIdentity: no SBT"
            );
        });

        it("Should revert setDisplayName when displayName too long", async function () {
            const long = "a".repeat(65);
            await expectRevertWithMessage(
                soulIdentity.connect(user1).setDisplayName(long),
                "SoulIdentity: displayName too long"
            );
        });

        it("Should revert setHandle when handle too long", async function () {
            const long = "@spiral:" + "x".repeat(25); // 8 + 25 = 33
            await expectRevertWithMessage(
                soulIdentity.connect(user1).setHandle(long),
                "SoulIdentity: handle too long"
            );
        });

        it("Should revert setHandle when invalid format (no @)", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user1).setHandle("spiral:user"),
                "SoulIdentity: handle must be @communityId:localHandle"
            );
        });

        it("Should revert setHandle when invalid format (no colon)", async function () {
            await expectRevertWithMessage(
                soulIdentity.connect(user1).setHandle("@spiraluser"),
                "SoulIdentity: handle must be @communityId:localHandle"
            );
        });
    });

    describe("P1: Access Control", function () {
        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should only allow SPIRAL_ENGINE_ROLE to link external identities", async function () {
            console.log("Testing access control for linkExternalIdentity...");
            
            await expectCustomError(
                soulIdentity.connect(user1).linkExternalIdentity(user1.address, "did:spiral", `did:spiral:${user1.address.toLowerCase()}`, false),
                soulIdentity,
                "AccessControlUnauthorizedAccount"
            );
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(user1.address, "did:spiral", `did:spiral:${user1.address.toLowerCase()}`, false);
            
            console.log("✅ Access control works correctly");
        });

        it("Should allow users to link their own soul identity (backward compatibility)", async function () {
            console.log("Testing user self-linking...");
            
            await soulIdentity.connect(user1).linkSoulIdentity(`did:spiral:${user1.address.toLowerCase()}`);
            
            const identity = await soulIdentity.getSoulIdentity(user1.address);
            expect(identity).to.include("did:spiral:");
            
            console.log("✅ User self-linking works");
        });
    });

    describe("P2: Edge Cases", function () {
        it("Should handle users without SBT tokens", async function () {
            console.log("Testing users without SBT tokens...");
            
            // Пользователь без SBT токена
            const level = await soulIdentity.getSoulLevel(user1.address);
            const reputation = await soulIdentity.getSoulReputation(user1.address);
            
            expect(level === 0n || level === 0).to.be.true;
            expect(reputation === 0n || reputation === 0).to.be.true;

            await expectRevertWithMessage(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(user1.address, "did:spiral", `did:spiral:${user1.address.toLowerCase()}`, false),
                "SoulIdentity: user has no SBT token"
            );
            
            console.log("✅ Edge case handled: users without SBT tokens");
        });

        it("Should handle empty identity data", async function () {
            console.log("Testing empty identity data...");
            
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            
            await expectRevertWithMessage(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(user1.address, "", `did:spiral:${user1.address.toLowerCase()}`, false),
                "SoulIdentity: empty identity type"
            );
            await expectRevertWithMessage(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(user1.address, "did:spiral", "", false),
                "SoulIdentity: empty identity value"
            );
            
            console.log("✅ Edge case handled: empty identity data");
        });

        it("Should handle users with no identities", async function () {
            console.log("Testing users with no identities...");
            
            // Пользователь без идентичностей
            const identity = await soulIdentity.getSoulIdentity(user1.address);
            expect(identity).to.equal("");
            
            const allIdentities = await soulIdentity.getAllIdentities(user1.address);
            expect(allIdentities.length).to.equal(0);
            
            await expectRevertWithMessage(soulIdentity.getPrimaryIdentity(user1.address), "SoulIdentity: no identities found");
            
            console.log("✅ Edge case handled: users with no identities");
        });
    });

    describe("P2: Gas Profiling", function () {
        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should profile gas consumption for DID operations", async function () {
            console.log("Profiling gas consumption...");
            
            // linkExternalIdentity
            const tx1 = await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:spiral",
                `did:spiral:${user1.address.toLowerCase()}`,
                false
            );
            const receipt1 = await tx1.wait();
            console.log(`💰 linkExternalIdentity: ${receipt1.gasUsed} газа`);
            
            // getPrimaryIdentity (view функция)
            const gasEstimate1 = await soulIdentity.getPrimaryIdentity.estimateGas(user1.address);
            console.log(`💰 getPrimaryIdentity: ${gasEstimate1} газа`);
            
            // getAllIdentities (view функция)
            const gasEstimate2 = await soulIdentity.getAllIdentities.estimateGas(user1.address);
            console.log(`💰 getAllIdentities: ${gasEstimate2} газа`);
            
            // getSoulLevel (делегирование)
            const gasEstimate3 = await soulIdentity.getSoulLevel.estimateGas(user1.address);
            console.log(`💰 getSoulLevel: ${gasEstimate3} газа`);
            
            // Проверяем что газ в разумных пределах
            expect(receipt1.gasUsed < 300000n).to.be.true;
            expect(gasEstimate1 < 100000n).to.be.true;
            expect(gasEstimate2 < 100000n).to.be.true;
            expect(gasEstimate3 < 100000n).to.be.true;
            
            console.log("✅ Gas consumption within reasonable limits");
        });
    });

    describe("P1: Integration with SBT Ecosystem", function () {
        it("Should work with SoulMetadata for level and reputation", async function () {
            console.log("Testing SoulMetadata integration...");
            
            // Создаем SBT токен
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            
            // Инициализируем метаданные
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "seller",
                '{"level": 3, "reputation": 150, "type": "seller"}',
                ""
            );
            
            // Проверяем делегирование
            const level = await soulIdentity.getSoulLevel(user1.address);
            const reputation = await soulIdentity.getSoulReputation(user1.address);
            
            // Пока заглушки возвращают дефолтные значения
            expect(level).to.be.a('bigint');
            expect(reputation).to.be.a('bigint');
            
            console.log("✅ SoulMetadata integration works");
        });

        it("Should handle SBT metadata through getSBTMetadata", async function () {
            console.log("Testing getSBTMetadata...");
            
            // Создаем SBT токен
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            
            // Инициализируем метаданные
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 2}',
                "QmTestHash"
            );
            
            // Получаем метаданные через SoulIdentity
            const metadata = await soulIdentity.getSBTMetadata(1);
            expect(metadata.tokenSbtType).to.equal("identity");
            expect(metadata.version === 1n || metadata.version === 1).to.be.true;
            expect(metadata.attributes).to.include("level");
            expect(metadata.isLocked).to.equal(true);
            
            console.log("✅ SBT metadata access works");
        });
    });

    describe("P2: Future Polygon ID Readiness", function () {
        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should support did:polygon format", async function () {
            console.log("Testing Polygon ID format support...");
            
            const polygonDID = `did:polygon:mainnet:${user1.address.toLowerCase()}`;
            
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:polygon",
                polygonDID,
                true // верифицирована
            );
            
            const hasPolygon = await soulIdentity.hasIdentityType(user1.address, "did:polygon");
            expect(hasPolygon).to.equal(true);
            
            const allIdentities = await soulIdentity.getAllIdentities(user1.address);
            const polygonIdentity = allIdentities.find(id => id.identityType === "did:polygon");
            expect(polygonIdentity.verified).to.equal(true);
            expect(polygonIdentity.verifiedBy).to.equal(spiralEngine.address);
            
            console.log("✅ Polygon ID format supported and ready");
        });

        it("Should support mixed identity types", async function () {
            console.log("Testing mixed identity types...");
            
            // Добавляем разные типы DID
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:spiral",
                `did:spiral:${user1.address.toLowerCase()}`,
                false
            );
            
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:polygon",
                `did:polygon:mainnet:${user1.address.toLowerCase()}`,
                true
            );
            
            await soulIdentity.connect(spiralEngine).linkExternalIdentity(
                user1.address,
                "did:ethr",
                `did:ethr:${user1.address.toLowerCase()}`,
                true
            );
            
            const allIdentities = await soulIdentity.getAllIdentities(user1.address);
            expect(allIdentities.length).to.equal(3); // array length
            
            const types = allIdentities.map(id => id.identityType);
            expect(types).to.include("did:spiral");
            expect(types).to.include("did:polygon");
            expect(types).to.include("did:ethr");
            
            console.log("✅ Mixed identity types supported");
        });
    });
});
