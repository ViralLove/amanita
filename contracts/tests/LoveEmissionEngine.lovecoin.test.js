const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("LoveEmissionEngine with Lovecoin", function () {
    let lovecoin;
    let lgovToken;
    let loveDoPostNFT;
    let inviteGraph;
    let loveEmissionEngine;
    let deployer, user1, user2, seller, liker, emitter;

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];

        // Создаем дополнительные кошельки для тестирования
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        liker = ethers.Wallet.createRandom().connect(ethers.provider);
        emitter = ethers.Wallet.createRandom().connect(ethers.provider);

        // Финансируем кошельки
        const fundingAmount = ethers.parseEther("1.0");
        for (const user of [user1, user2, seller, liker, emitter]) {
            await deployer.sendTransaction({
                to: user.address,
                value: fundingAmount
            });
        }

        // Деплоим Lovecoin
        const Lovecoin = await ethers.getContractFactory("Lovecoin");
        lovecoin = await Lovecoin.deploy(deployer.address);
        await lovecoin.waitForDeployment();

        // Деплоим LGOV Token (AmanitaGovToken)
        const AmanitaGovToken = await ethers.getContractFactory("AmanitaGovToken");
        lgovToken = await AmanitaGovToken.deploy(deployer.address);
        await lgovToken.waitForDeployment();

        // Деплоим LoveDoPostNFT
        const LoveDoPostNFT = await ethers.getContractFactory("LoveDoPostNFT");
        loveDoPostNFT = await LoveDoPostNFT.deploy(
            deployer.address, // admin
            deployer.address, // minter
            deployer.address  // burner
        );
        await loveDoPostNFT.waitForDeployment();

        // Деплоим InviteGraph (SpiralEngine)
        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        inviteGraph = await SpiralEngine.deploy();
        await inviteGraph.waitForDeployment();

        // Деплоим LoveEmissionEngine
        const LoveEmissionEngine = await ethers.getContractFactory("LoveEmissionEngine");
        loveEmissionEngine = await LoveEmissionEngine.deploy(
            await lovecoin.getAddress(),
            await lgovToken.getAddress(),
            await loveDoPostNFT.getAddress(),
            await inviteGraph.getAddress(),
            deployer.address
        );
        await loveEmissionEngine.waitForDeployment();

        // Настраиваем роли
        const EMITTER_ROLE = await loveEmissionEngine.EMITTER_ROLE();
        await loveEmissionEngine.connect(deployer).grantRole(EMITTER_ROLE, emitter.address);

        // Настраиваем Lovecoin для LoveEmissionEngine
        const MINTER_ROLE = await lovecoin.MINTER_ROLE();
        await lovecoin.connect(deployer).grantRole(MINTER_ROLE, await loveEmissionEngine.getAddress());

        // Настраиваем LGOV для LoveEmissionEngine
        const LGOV_MINTER_ROLE = await lgovToken.MINTER_ROLE();
        await lgovToken.connect(deployer).grantRole(LGOV_MINTER_ROLE, await loveEmissionEngine.getAddress());
    });

    describe("P0: Core Emission Functions", function () {
        it("Should emit Lovecoin and LGOV for superlike", async function () {
            // Создаем LoveDo пост
            const postData = {
                sellerTo: seller.address,
                linkedSeller: seller.address,
                content: "Great product!",
                metadataURI: "ipfs://test"
            };
            
            await loveDoPostNFT.connect(deployer).mintLoveDo(
                user1.address,
                postData.sellerTo,
                postData.linkedSeller,
                postData.content,
                postData.metadataURI
            );

            // Получаем tokenId
            const tokenId = await loveDoPostNFT.getCurrentTokenId();

            // Эмитируем токены за суперлайк
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            // Проверяем накопление токенов
            const loveAccrued = await loveEmissionEngine.loveAccrued(seller.address);
            const lgovAccrued = await loveEmissionEngine.lgovAccrued(seller.address);

            expect(loveAccrued).to.equal(ethers.parseEther("1"));
            expect(lgovAccrued).to.equal(ethers.parseEther("1"));
        });

        it("Should claim Lovecoin tokens", async function () {
            // Настраиваем накопленные токены
            const amount = ethers.parseEther("100");
            await lovecoin.connect(deployer).transfer(await loveEmissionEngine.getAddress(), amount);
            
            // Симулируем накопление (в реальном сценарии это делается через emitForSuperlike)
            // Здесь мы напрямую устанавливаем накопленные токены для тестирования
            // В реальном контракте это делается через emitForSuperlike
            
            // Создаем пост и эмитируем
            const postData = {
                sellerTo: seller.address,
                linkedSeller: seller.address,
                content: "Test post",
                metadataURI: "ipfs://test"
            };
            
            await loveDoPostNFT.connect(deployer).mintLoveDo(
                user1.address,
                postData.sellerTo,
                postData.linkedSeller,
                postData.content,
                postData.metadataURI
            );

            const tokenId = await loveDoPostNFT.getCurrentTokenId();
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            // Проверяем баланс до клейма
            const balanceBefore = await lovecoin.balanceOf(seller.address);
            expect(balanceBefore).to.equal(0);

            // Клеймим Lovecoin
            await loveEmissionEngine.connect(seller).claimLOVECOIN();

            // Проверяем баланс после клейма
            const balanceAfter = await lovecoin.balanceOf(seller.address);
            expect(balanceAfter).to.equal(ethers.parseEther("1"));

            // Проверяем, что накопленные токены обнулились
            const loveAccrued = await loveEmissionEngine.loveAccrued(seller.address);
            expect(loveAccrued).to.equal(0);
        });
    });

    describe("P1: LGOV Activation", function () {
        it("Should activate LGOV when reputation threshold is met", async function () {
            // Создаем 8 LoveDo постов для достижения порога
            for (let i = 0; i < 8; i++) {
                const postData = {
                    sellerTo: seller.address,
                    linkedSeller: seller.address,
                    content: `Test post ${i}`,
                    metadataURI: `ipfs://test${i}`
                };
                
                await loveDoPostNFT.connect(deployer).mintLoveDo(
                    user1.address,
                    postData.sellerTo,
                    postData.linkedSeller,
                    postData.content,
                    postData.metadataURI
                );
            }

            // Эмитируем LGOV за суперлайк
            const postData = {
                sellerTo: seller.address,
                linkedSeller: seller.address,
                content: "Final post",
                metadataURI: "ipfs://final"
            };
            
            await loveDoPostNFT.connect(deployer).mintLoveDo(
                user1.address,
                postData.sellerTo,
                postData.linkedSeller,
                postData.content,
                postData.metadataURI
            );

            const tokenId = await loveDoPostNFT.getCurrentTokenId();
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            // Проверяем накопленные LGOV
            const lgovAccrued = await loveEmissionEngine.lgovAccrued(seller.address);
            expect(lgovAccrued).to.equal(ethers.parseEther("1"));

            // Активируем LGOV
            await loveEmissionEngine.connect(seller).claimLGOV();

            // Проверяем, что LGOV были заминчены
            const lgovBalance = await lgovToken.balanceOf(seller.address);
            expect(lgovBalance).to.equal(ethers.parseEther("1"));

            // Проверяем, что накопленные LGOV обнулились
            const lgovAccruedAfter = await loveEmissionEngine.lgovAccrued(seller.address);
            expect(lgovAccruedAfter).to.equal(0);
        });

        it("Should not activate LGOV when reputation threshold is not met", async function () {
            // Создаем только 7 LoveDo постов (меньше порога 8)
            for (let i = 0; i < 7; i++) {
                const postData = {
                    sellerTo: seller.address,
                    linkedSeller: seller.address,
                    content: `Test post ${i}`,
                    metadataURI: `ipfs://test${i}`
                };
                
                await loveDoPostNFT.connect(deployer).mintLoveDo(
                    user1.address,
                    postData.sellerTo,
                    postData.linkedSeller,
                    postData.content,
                    postData.metadataURI
                );
            }

            // Эмитируем LGOV за суперлайк
            const postData = {
                sellerTo: seller.address,
                linkedSeller: seller.address,
                content: "Final post",
                metadataURI: "ipfs://final"
            };
            
            await loveDoPostNFT.connect(deployer).mintLoveDo(
                user1.address,
                postData.sellerTo,
                postData.linkedSeller,
                postData.content,
                postData.metadataURI
            );

            const tokenId = await loveDoPostNFT.getCurrentTokenId();
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            // Пытаемся активировать LGOV (должно провалиться)
            await expect(
                loveEmissionEngine.connect(seller).claimLGOV()
            ).to.be.revertedWith("LoveEmission: not enough LoveDo posts");
        });
    });

    describe("P2: Error Handling", function () {
        it("Should revert when claiming zero Lovecoin", async function () {
            await expect(
                loveEmissionEngine.connect(seller).claimLOVECOIN()
            ).to.be.revertedWith("LoveEmission: nothing to claim");
        });

        it("Should revert when claiming zero LGOV", async function () {
            await expect(
                loveEmissionEngine.connect(seller).claimLGOV()
            ).to.be.revertedWith("LoveEmission: nothing to mint");
        });

        it("Should revert when non-emitter tries to emit", async function () {
            const postData = {
                sellerTo: seller.address,
                linkedSeller: seller.address,
                content: "Test post",
                metadataURI: "ipfs://test"
            };
            
            await loveDoPostNFT.connect(deployer).mintLoveDo(
                user1.address,
                postData.sellerTo,
                postData.linkedSeller,
                postData.content,
                postData.metadataURI
            );

            const tokenId = await loveDoPostNFT.getCurrentTokenId();

            await expect(
                loveEmissionEngine.connect(user1).emitForSuperlike(tokenId, liker.address)
            ).to.be.reverted;
        });
    });

    describe("P3: Integration with Token Contracts", function () {
        it("Should correctly interact with Lovecoin contract", async function () {
            // Проверяем, что LoveEmissionEngine имеет MINTER_ROLE в Lovecoin
            const MINTER_ROLE = await lovecoin.MINTER_ROLE();
            expect(await lovecoin.hasRole(MINTER_ROLE, await loveEmissionEngine.getAddress())).to.be.true;
        });

        it("Should correctly interact with LGOV contract", async function () {
            // Проверяем, что LoveEmissionEngine имеет MINTER_ROLE в LGOV
            const LGOV_MINTER_ROLE = await lgovToken.MINTER_ROLE();
            expect(await lgovToken.hasRole(LGOV_MINTER_ROLE, await loveEmissionEngine.getAddress())).to.be.true;
        });
    });
});
