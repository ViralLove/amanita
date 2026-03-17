const { expect } = require("chai");
const { ethers } = require("hardhat");

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

describe("SoulMetadata Integration Tests", function () {
    let soulboundCore;
    let soulMetadata;
    let owner;
    let user1;
    let user2;
    let user3;

    beforeEach(async function () {
        const signers = await ethers.getSigners();
        owner = signers[0];
        
        // Создаем случайные кошельки для тестирования
        user1 = await ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = await ethers.Wallet.createRandom().connect(ethers.provider);
        user3 = await ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Пополняем кошельки для тестирования
        await owner.sendTransaction({
            to: user1.address,
            value: ethers.parseEther("1.0")
        });
        await owner.sendTransaction({
            to: user2.address,
            value: ethers.parseEther("1.0")
        });
        await owner.sendTransaction({
            to: user3.address,
            value: ethers.parseEther("1.0")
        });
        
        // Деплоим SoulboundCore
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        soulboundCore = await SoulboundCore.deploy("Amanita Soul", "ASOUL");
        await soulboundCore.waitForDeployment();
        
        // Деплоим SoulMetadata
        const SoulMetadata = await ethers.getContractFactory("SoulMetadata");
        soulMetadata = await SoulMetadata.deploy(await soulboundCore.getAddress());
        await soulMetadata.waitForDeployment();
        
        // Связываем контракты
        await soulboundCore.setMetadataContract(await soulMetadata.getAddress());
    });

    describe("Deployment and Integration", function () {
        it("Should deploy both contracts successfully", async function () {
            expect(await soulboundCore.name()).to.equal("Amanita Soul");
            expect(await soulboundCore.symbol()).to.equal("ASOUL");
            expect(await soulboundCore.getMetadataContract()).to.equal(await soulMetadata.getAddress());
        });

        it("Should link metadata contract correctly", async function () {
            const metadataAddress = await soulboundCore.getMetadataContract();
            expect(metadataAddress).to.equal(await soulMetadata.getAddress());
        });
    });

    describe("Basic Metadata Operations", function () {
        beforeEach(async function () {
            // Минтим токен для тестирования
            await soulboundCore.mintSoul(user1.address);
        });

        it("Should return default tokenURI before metadata initialization", async function () {
            const tokenURI = await soulboundCore.tokenURI(1);
            expect(tokenURI).to.include("Soul #1");
            expect(tokenURI).to.include("Soulbound Token from Amanita Ecosystem");
            expect(tokenURI).to.include('"type": "basic"');
        });

        it("Should initialize metadata successfully", async function () {
            const tx = await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 1, "experience": 0}',
                "QmTest123"
            );
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulMetadata.interface.parseLog(log)?.name === "MetadataUpdated"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;
            const p = soulMetadata.interface.parseLog(ev);
            expect(p.args.tokenId).to.equal(1n);
            expect(p.args.version).to.equal(1n);

            expect(await soulMetadata.isInitialized(1)).to.be.true;
            expect(await soulMetadata.getMetadataVersion(1)).to.equal(1n);
        });

        it("Should return metadata-based tokenURI after initialization", async function () {
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 1, "experience": 0}',
                "QmTest123"
            );

            const tokenURI = await soulboundCore.tokenURI(1);
            expect(tokenURI).to.include("Soul #1");
            expect(tokenURI).to.include('"type": "identity"');
            expect(tokenURI).to.include('"version": 1');
            expect(tokenURI).to.include('"ipfs": "QmTest123"');
        });

        it("Should update metadata successfully", async function () {
            // Инициализация
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 1, "experience": 0}',
                "QmTest123"
            );

            const tx = await soulMetadata.connect(user1).updateMetadata(
                1,
                '{"level": 2, "experience": 100}',
                "QmTest456"
            );
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulMetadata.interface.parseLog(log)?.name === "MetadataUpdated"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;
            expect(soulMetadata.interface.parseLog(ev).args.version).to.equal(2n);

            expect(await soulMetadata.getMetadataVersion(1)).to.equal(2n);
            
            const metadata = await soulMetadata.getMetadata(1);
            expect(metadata.attributes).to.equal('{"level": 2, "experience": 100}');
            expect(metadata.ipfsHash).to.equal("QmTest456");
        });

        it("Should get complete metadata structure", async function () {
            // Инициализация с полными данными
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "achievement",
                '{"badges": ["first_login", "level_up"], "score": 150}',
                "QmCompleteTest789"
            );

            const metadata = await soulMetadata.getMetadata(1);
            
            // Проверяем все поля SoulData структуры
            expect(metadata.metadataType).to.equal("achievement");
            expect(metadata.version === 1n || metadata.version === 1).to.be.true;
            expect(metadata.attributes).to.equal('{"badges": ["first_login", "level_up"], "score": 150}');
            expect(metadata.ipfsHash).to.equal("QmCompleteTest789");
        });

        it("Should track metadata version correctly", async function () {
            // Инициализация
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "reputation",
                '{"trust": 100}',
                "QmVersion1"
            );
            
            expect(await soulMetadata.getMetadataVersion(1)).to.equal(1n);
            await soulMetadata.connect(user1).updateMetadata(1, '{"trust": 150}', "QmVersion2");
            expect(await soulMetadata.getMetadataVersion(1)).to.equal(2n);
            await soulMetadata.connect(user1).updateMetadata(1, '{"trust": 200}', "QmVersion3");
            expect(await soulMetadata.getMetadataVersion(1)).to.equal(3n);
        });
    });

    describe("Access Control", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
        });

        it("Should allow token owner to initialize metadata", async function () {
            await soulMetadata.connect(user1).initializeMetadata(1, "identity", '{"level": 1}', "");
        });

        it("Should allow contract owner to initialize metadata", async function () {
            await soulMetadata.connect(owner).initializeMetadata(1, "identity", '{"level": 1}', "");
        });

        it("Should reject unauthorized metadata initialization", async function () {
            await expectRevertWithMessage(soulMetadata.connect(user2).initializeMetadata(1, "identity", '{"level": 1}', ""), "SoulMetadata: not authorized");
        });

        it("Should reject double initialization", async function () {
            await soulMetadata.connect(user1).initializeMetadata(1, "identity", '{"level": 1}', "");
            await expectRevertWithMessage(soulMetadata.connect(user1).initializeMetadata(1, "achievement", '{"badges": []}', ""), "SoulMetadata: already initialized");
        });
    });

    describe("Batch Operations", function () {
        beforeEach(async function () {
            // Минтим несколько токенов
            await soulboundCore.mintSoulBatch(user1.address, 3);
            
            // Инициализируем метаданные
            for (let i = 1; i <= 3; i++) {
                await soulMetadata.connect(user1).initializeMetadata(
                    i,
                    "identity",
                    `{"level": ${i}}`,
                    `QmTest${i}`
                );
            }
        });

        it("Should batch update metadata successfully", async function () {
            const tokenIds = [1, 2, 3];
            const attributes = [
                '{"level": 2, "updated": true}',
                '{"level": 3, "updated": true}',
                '{"level": 4, "updated": true}'
            ];
            const ipfsHashes = ["QmNew1", "QmNew2", "QmNew3"];

            const tx = await soulMetadata.connect(user1).batchUpdateMetadata(tokenIds, attributes, ipfsHashes);
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulMetadata.interface.parseLog(log)?.name === "MetadataBatchUpdated"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;

            for (let i = 0; i < 3; i++) {
                const metadata = await soulMetadata.getMetadata(tokenIds[i]);
                expect(metadata.attributes).to.equal(attributes[i]);
                expect(metadata.ipfsHash).to.equal(ipfsHashes[i]);
                expect(metadata.version === 2n || metadata.version === 2).to.be.true;
            }
        });

        it("Should reject batch update with mismatched arrays", async function () {
            await expectRevertWithMessage(soulMetadata.connect(user1).batchUpdateMetadata([1, 2], ['{"level": 2}'], ["QmNew1"]), "SoulMetadata: arrays length mismatch");
        });

        it("Should reject batch update that's too large", async function () {
            const largeArray = new Array(51).fill(0).map((_, i) => i + 1);
            const attributesArray = new Array(51).fill('{"level": 1}');
            const ipfsArray = new Array(51).fill("QmTest");
            await expectRevertWithMessage(soulMetadata.connect(user1).batchUpdateMetadata(largeArray, attributesArray, ipfsArray), "SoulMetadata: batch too large");
        });
    });

    describe("Edge Cases", function () {
        it("Should handle non-existent tokens correctly", async function () {
            await expectRevertWithMessage(soulMetadata.getMetadata(999), "SoulMetadata: token does not exist");
            await expectRevertWithMessage(soulMetadata.connect(user1).initializeMetadata(999, "identity", '{"level": 1}', ""), "SoulMetadata: token does not exist");
        });

        it("Should handle uninitialized metadata correctly", async function () {
            await soulboundCore.mintSoul(user1.address);
            await expectRevertWithMessage(soulMetadata.getMetadata(1), "SoulMetadata: not initialized");
            await expectRevertWithMessage(soulMetadata.connect(user1).updateMetadata(1, '{"level": 2}', "QmNew"), "SoulMetadata: not initialized");
        });

        it("Should fallback to default URI on metadata contract error", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            // Отключаем метаданные контракт
            await soulboundCore.setMetadataContract(ethers.ZeroAddress);
            
            const tokenURI = await soulboundCore.tokenURI(1);
            expect(tokenURI).to.include("Soul #1");
            expect(tokenURI).to.include('"type": "basic"');
        });

        it("Should handle empty IPFS hash correctly", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            // Инициализация без IPFS хеша
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "basic",
                '{"level": 1}',
                ""
            );
            
            const metadata = await soulMetadata.getMetadata(1);
            expect(metadata.ipfsHash).to.equal("");
            
            const tokenURI = await soulboundCore.tokenURI(1);
            expect(tokenURI).to.not.include('"ipfs"'); // IPFS поле должно отсутствовать
        });

        it("Should handle complex JSON attributes", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const complexAttributes = '{"profile": {"name": "Test User", "age": 25}, "achievements": [{"id": 1, "name": "First Login"}, {"id": 2, "name": "Level Up"}], "stats": {"hp": 100, "mp": 50}}';
            
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "profile",
                complexAttributes,
                "QmComplexData"
            );
            
            const metadata = await soulMetadata.getMetadata(1);
            expect(metadata.attributes).to.equal(complexAttributes);
            
            const tokenURI = await soulboundCore.tokenURI(1);
            expect(tokenURI).to.include(complexAttributes);
        });
    });

    describe("Gas Profiling", function () {
        it("Should profile gas usage for metadata initialization", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const tx = await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 1, "experience": 0, "attributes": {"strength": 10, "intelligence": 15}}',
                "QmTestHashForGasProfiling123456"
            );
            const receipt = await tx.wait();
            
            console.log(`Gas used for initializeMetadata: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed < 250000n).to.be.true;
        });

        it("Should profile gas usage for metadata update", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 1}',
                "QmTest"
            );
            
            const tx = await soulMetadata.connect(user1).updateMetadata(
                1,
                '{"level": 2, "experience": 100, "newAttribute": "value"}',
                "QmNewTestHashForUpdate"
            );
            const receipt = await tx.wait();
            
            console.log(`Gas used for updateMetadata: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed < 120000n).to.be.true;
        });

        it("Should profile gas usage for batch update", async function () {
            await soulboundCore.mintSoulBatch(user1.address, 5);
            
            // Инициализация
            for (let i = 1; i <= 5; i++) {
                await soulMetadata.connect(user1).initializeMetadata(
                    i,
                    "identity",
                    `{"level": ${i}}`,
                    `QmTest${i}`
                );
            }
            
            // Пакетное обновление
            const tokenIds = [1, 2, 3, 4, 5];
            const attributes = tokenIds.map(id => `{"level": ${id + 1}, "updated": true}`);
            const ipfsHashes = tokenIds.map(id => `QmUpdated${id}`);
            
            const tx = await soulMetadata.connect(user1).batchUpdateMetadata(
                tokenIds,
                attributes,
                ipfsHashes
            );
            const receipt = await tx.wait();
            
            const gasPerToken = receipt.gasUsed / BigInt(5);
            console.log(`Gas used for batchUpdateMetadata (5 tokens): ${receipt.gasUsed.toString()}`);
            console.log(`Gas per token in batch: ${gasPerToken.toString()}`);
            expect(gasPerToken < 50000n).to.be.true;
        });

        it("Should profile gas usage for tokenURI", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulMetadata.connect(user1).initializeMetadata(
                1,
                "identity",
                '{"level": 5, "experience": 1000}',
                "QmDetailedMetadata"
            );
            
            // Измеряем газ для tokenURI (view функция)
            const gasEstimate = await soulboundCore.tokenURI.estimateGas(1);
            console.log(`Gas estimate for tokenURI: ${gasEstimate.toString()}`);
            
            // View функции не должны потреблять много газа
            expect(gasEstimate < 60000n).to.be.true;
        });
    });
});
