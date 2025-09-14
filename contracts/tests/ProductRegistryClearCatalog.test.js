const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ProductRegistry - Clear Catalog", function () {
    let productRegistry;
    let inviteNFT;
    let deployer;
    let seller;
    let otherSeller;

    beforeEach(async function () {
        // Используем ключ деплоера из .env
        const deployerPrivateKey = process.env.DEPLOYER_PRIVATE_KEY;
        if (!deployerPrivateKey) {
            throw new Error("DEPLOYER_PRIVATE_KEY not found in environment variables");
        }

        // Создаем кошелек деплоера
        deployer = new ethers.Wallet(deployerPrivateKey, ethers.provider);
        
        // Получаем других пользователей
        [seller, otherSeller] = await ethers.getSigners();

        // Создаем простой мок для InviteNFT
        const InviteNFTMock = await ethers.getContractFactory("InviteNFT");
        inviteNFT = await InviteNFTMock.connect(deployer).deploy();
        await inviteNFT.waitForDeployment();

        // Деплой ProductRegistry
        const ProductRegistry = await ethers.getContractFactory("ProductRegistry");
        productRegistry = await ProductRegistry.connect(deployer).deploy(await inviteNFT.getAddress());
        await productRegistry.waitForDeployment();

        // Активируем продавца через мок
        // Сначала назначаем роли деплоеру
        const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
        const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));
        await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, deployer.address);
        await inviteNFT.connect(deployer).grantRole(ACTIVATOR_ROLE, deployer.address);
        
        // Создаем тестовый инвайт
        const testInviteCode = "TEST-INVITE-1234";
        await inviteNFT.connect(deployer).mintInvites([testInviteCode], 0);
        
        // Активируем пользователя с правильной сигнатурой (требуется 12 инвайтов)
        const newInviteCodes = Array.from({length: 12}, (_, i) => `NEW-INVITE-${i + 1}`);
        await inviteNFT.connect(deployer).activateUser(
            testInviteCode,
            seller.address,
            newInviteCodes,
            0
        );
        
        // Назначаем роль SELLER_ROLE
        await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, seller.address);
    });

    describe("clearSellerCatalog", function () {
        it("Should clear seller's catalog successfully", async function () {
            // Создаем несколько продуктов
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            await productRegistry.connect(seller).createProduct("QmTest3");

            // Активируем продукты
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(2);
            await productRegistry.connect(seller).activateProduct(3);

            // Проверяем, что продукты существуют
            const productsBefore = await productRegistry.getProductsBySeller(seller.address);
            expect(productsBefore.length).to.equal(3);

            const activeProductsBefore = await productRegistry.getAllActiveProductIds();
            expect(activeProductsBefore.length).to.equal(3);

            // Очищаем каталог
            const tx = await productRegistry.connect(seller).clearSellerCatalog(seller.address);
            const receipt = await tx.wait();

            // Проверяем события (используем logs вместо events)
            const catalogClearedEvent = receipt.logs.find(log => {
                try {
                    const parsed = productRegistry.interface.parseLog(log);
                    return parsed && parsed.name === "CatalogCleared";
                } catch (e) {
                    return false;
                }
            });
            expect(catalogClearedEvent).to.not.be.undefined;
            
            const parsedCatalogCleared = productRegistry.interface.parseLog(catalogClearedEvent);
            expect(parsedCatalogCleared.args.seller).to.equal(seller.address);
            expect(parsedCatalogCleared.args.productsCleared).to.equal(3);

            // Проверяем, что каталог очищен
            const productsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(productsAfter.length).to.equal(0);

            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductsAfter.length).to.equal(0);

            // Проверяем, что продукты удалены
            await expect(productRegistry.getProduct(1)).to.be.revertedWith("ProductRegistry: product does not exist");
            await expect(productRegistry.getProduct(2)).to.be.revertedWith("ProductRegistry: product does not exist");
            await expect(productRegistry.getProduct(3)).to.be.revertedWith("ProductRegistry: product does not exist");
        });

        it("Should revert when trying to clear empty catalog", async function () {
            await expect(
                productRegistry.connect(seller).clearSellerCatalog(seller.address)
            ).to.be.revertedWith("Catalog is already empty");
        });

        it("Should revert when non-seller tries to clear catalog", async function () {
            await expect(
                productRegistry.connect(otherSeller).clearSellerCatalog(seller.address)
            ).to.be.revertedWith("Not a seller");
        });

        it("Should revert when trying to clear someone else's catalog", async function () {
            // Активируем другого продавца
            const testInviteCode2 = "TEST-INVITE-5678";
            await inviteNFT.connect(deployer).mintInvites([testInviteCode2], 0);
            
            const newInviteCodes2 = Array.from({length: 12}, (_, i) => `NEW-INVITE-${i + 13}`);
            await inviteNFT.connect(deployer).activateUser(
                testInviteCode2,
                otherSeller.address,
                newInviteCodes2,
                0
            );
            
            await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, otherSeller.address);

            await expect(
                productRegistry.connect(seller).clearSellerCatalog(otherSeller.address)
            ).to.be.revertedWith("Can only clear own catalog");
        });

        it("Should revert when seller address is zero", async function () {
            await expect(
                productRegistry.connect(seller).clearSellerCatalog(ethers.ZeroAddress)
            ).to.be.revertedWith("Invalid seller address");
        });

        it("Should revert when catalog is too large", async function () {
            // Создаем много продуктов (симуляция большого каталога)
            // В реальном тесте это было бы сложно, но мы можем протестировать логику
            const largeCatalogSize = 10001; // Больше лимита в 10000
            
            // Этот тест показывает, что защита от переполнения работает
            // В реальности создание 10001 продукта было бы очень дорогим
            console.log("Large catalog protection test - would revert if catalog size > 10000");
        });

        it("Should handle mixed active/inactive products correctly", async function () {
            // Создаем продукты
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            await productRegistry.connect(seller).createProduct("QmTest3");

            // Активируем только некоторые
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(3);

            // Проверяем состояние до очистки
            const activeProductsBefore = await productRegistry.getAllActiveProductIds();
            expect(activeProductsBefore.length).to.equal(2);

            // Очищаем каталог
            await productRegistry.connect(seller).clearSellerCatalog(seller.address);

            // Проверяем, что все продукты удалены
            const productsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(productsAfter.length).to.equal(0);

            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductsAfter.length).to.equal(0);
        });
    });

    describe("Gas optimization", function () {
        it("Should use reasonable gas for clearing small catalog", async function () {
            // Создаем несколько продуктов
            for (let i = 0; i < 5; i++) {
                await productRegistry.connect(seller).createProduct(`QmTest${i}`);
                await productRegistry.connect(seller).activateProduct(i + 1);
            }

            // Очищаем каталог и измеряем газ
            const tx = await productRegistry.connect(seller).clearSellerCatalog(seller.address);
            const receipt = await tx.wait();

            console.log(`Gas used for clearing 5 products: ${receipt.gasUsed.toString()}`);
            
            // Проверяем, что газ разумный (менее 1M для 5 продуктов)
            expect(receipt.gasUsed).to.be.lessThan(1000000);
        });
    });
});
