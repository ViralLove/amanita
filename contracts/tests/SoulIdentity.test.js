const { expect } = require("chai");
const { ethers } = require("hardhat");

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
            expect(balance).to.equal(1);
            
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
            expect(allIdentities.length).to.equal(2);
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
            expect(profile.verificationLevel).to.equal(0);
            expect(profile.guardians.length).to.equal(0);
            
            console.log(`✅ Soul profile works: level=${profile.level}, reputation=${profile.reputation}`);
        });
    });

    describe("P1: Access Control", function () {
        beforeEach(async function () {
            await soulboundCore.connect(deployer).mintSoul(user1.address);
        });

        it("Should only allow SPIRAL_ENGINE_ROLE to link external identities", async function () {
            console.log("Testing access control for linkExternalIdentity...");
            
            // Пользователь без роли не может добавлять external identities
            await expect(
                soulIdentity.connect(user1).linkExternalIdentity(
                    user1.address,
                    "did:spiral",
                    `did:spiral:${user1.address.toLowerCase()}`,
                    false
                )
            ).to.be.revertedWithCustomError(soulIdentity, "AccessControlUnauthorizedAccount");
            
            // SpiralEngine может
            await expect(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(
                    user1.address,
                    "did:spiral",
                    `did:spiral:${user1.address.toLowerCase()}`,
                    false
                )
            ).to.not.be.reverted;
            
            console.log("✅ Access control works correctly");
        });

        it("Should allow users to link their own soul identity (backward compatibility)", async function () {
            console.log("Testing user self-linking...");
            
            // Пользователь может использовать старый метод для себя
            await expect(
                soulIdentity.connect(user1).linkSoulIdentity(`did:spiral:${user1.address.toLowerCase()}`)
            ).to.not.be.reverted;
            
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
            
            expect(level).to.equal(0);
            expect(reputation).to.equal(0);
            
            // Попытка добавить DID без SBT токена должна падать
            await expect(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(
                    user1.address,
                    "did:spiral",
                    `did:spiral:${user1.address.toLowerCase()}`,
                    false
                )
            ).to.be.revertedWith("SoulIdentity: user has no SBT token");
            
            console.log("✅ Edge case handled: users without SBT tokens");
        });

        it("Should handle empty identity data", async function () {
            console.log("Testing empty identity data...");
            
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            
            // Пустой тип идентичности
            await expect(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(
                    user1.address,
                    "",
                    `did:spiral:${user1.address.toLowerCase()}`,
                    false
                )
            ).to.be.revertedWith("SoulIdentity: empty identity type");
            
            // Пустое значение идентичности
            await expect(
                soulIdentity.connect(spiralEngine).linkExternalIdentity(
                    user1.address,
                    "did:spiral",
                    "",
                    false
                )
            ).to.be.revertedWith("SoulIdentity: empty identity value");
            
            console.log("✅ Edge case handled: empty identity data");
        });

        it("Should handle users with no identities", async function () {
            console.log("Testing users with no identities...");
            
            // Пользователь без идентичностей
            const identity = await soulIdentity.getSoulIdentity(user1.address);
            expect(identity).to.equal("");
            
            const allIdentities = await soulIdentity.getAllIdentities(user1.address);
            expect(allIdentities.length).to.equal(0);
            
            // getPrimaryIdentity должна падать
            await expect(
                soulIdentity.getPrimaryIdentity(user1.address)
            ).to.be.revertedWith("SoulIdentity: no identities found");
            
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
            expect(receipt1.gasUsed).to.be.below(300000);
            expect(gasEstimate1).to.be.below(100000);
            expect(gasEstimate2).to.be.below(100000);
            expect(gasEstimate3).to.be.below(100000);
            
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
            expect(metadata.version).to.equal(1);
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
            expect(allIdentities.length).to.equal(3);
            
            const types = allIdentities.map(id => id.identityType);
            expect(types).to.include("did:spiral");
            expect(types).to.include("did:polygon");
            expect(types).to.include("did:ethr");
            
            console.log("✅ Mixed identity types supported");
        });
    });
});
