const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("SoulRecovery Integration Tests", function () {
    let soulboundCore;
    let soulRecovery;
    let owner;
    let user1;
    let user2;
    let guardian1;
    let guardian2;

    beforeEach(async function () {
        const signers = await ethers.getSigners();
        owner = signers[0];
        
        // Создаем случайные кошельки для тестирования
        user1 = await ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = await ethers.Wallet.createRandom().connect(ethers.provider);
        guardian1 = await ethers.Wallet.createRandom().connect(ethers.provider);
        guardian2 = await ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Пополняем кошельки для тестирования
        const accounts = [user1, user2, guardian1, guardian2];
        for (const account of accounts) {
            await owner.sendTransaction({
                to: account.address,
                value: ethers.parseEther("1.0")
            });
        }
        
        // Деплоим SoulboundCore
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        soulboundCore = await SoulboundCore.deploy("Amanita Soul", "ASOUL");
        await soulboundCore.waitForDeployment();
        
        // Деплоим SoulRecovery
        const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
        soulRecovery = await SoulRecovery.deploy(await soulboundCore.getAddress());
        await soulRecovery.waitForDeployment();
        
        // Связываем контракты
        await soulboundCore.setRecoveryContract(await soulRecovery.getAddress());
    });

    describe("Deployment and Integration", function () {
        it("Should deploy both contracts successfully", async function () {
            expect(await soulboundCore.name()).to.equal("Amanita Soul");
            expect(await soulboundCore.symbol()).to.equal("ASOUL");
            expect(await soulboundCore.getRecoveryContract()).to.equal(await soulRecovery.getAddress());
        });

        it("Should link recovery contract correctly", async function () {
            const recoveryAddress = await soulboundCore.getRecoveryContract();
            expect(recoveryAddress).to.equal(await soulRecovery.getAddress());
        });
    });

    describe("Guardian Management", function () {
        beforeEach(async function () {
            // Минтим токен для тестирования
            await soulboundCore.mintSoul(user1.address);
        });

        it("Should set guardian successfully", async function () {
            await expect(
                soulRecovery.connect(user1).setGuardian(1, guardian1.address)
            ).to.emit(soulRecovery, "GuardianSet")
             .withArgs(1, user1.address, guardian1.address);

            expect(await soulRecovery.hasActiveGuardian(1)).to.be.true;
            expect(await soulRecovery.getGuardian(1)).to.equal(guardian1.address);
            
            const guardianInfo = await soulRecovery.getGuardianInfo(1);
            expect(guardianInfo.guardian).to.equal(guardian1.address);
            expect(guardianInfo.isActive).to.be.true;
        });

        it("Should remove guardian successfully", async function () {
            // Устанавливаем guardian
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            expect(await soulRecovery.hasActiveGuardian(1)).to.be.true;
            
            // Удаляем guardian
            await expect(
                soulRecovery.connect(user1).removeGuardian(1)
            ).to.emit(soulRecovery, "GuardianSet")
             .withArgs(1, user1.address, ethers.ZeroAddress);

            expect(await soulRecovery.hasActiveGuardian(1)).to.be.false;
            expect(await soulRecovery.getGuardian(1)).to.equal(ethers.ZeroAddress);
        });

        it("Should reject invalid guardian addresses", async function () {
            // Zero address
            await expect(
                soulRecovery.connect(user1).setGuardian(1, ethers.ZeroAddress)
            ).to.be.revertedWith("SoulRecovery: invalid guardian address");

            // Self as guardian
            await expect(
                soulRecovery.connect(user1).setGuardian(1, user1.address)
            ).to.be.revertedWith("SoulRecovery: cannot be self guardian");

            // Owner as guardian
            await expect(
                soulRecovery.connect(user1).setGuardian(1, user1.address)
            ).to.be.revertedWith("SoulRecovery: cannot be self guardian");
        });

        it("Should reject unauthorized guardian management", async function () {
            await expect(
                soulRecovery.connect(user2).setGuardian(1, guardian1.address)
            ).to.be.revertedWith("SoulRecovery: not token owner");

            await expect(
                soulRecovery.connect(guardian1).setGuardian(1, guardian2.address)
            ).to.be.revertedWith("SoulRecovery: not token owner");
        });
    });

    describe("Recovery Process", function () {
        beforeEach(async function () {
            // Минтим токен и устанавливаем guardian
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
        });

        it("Should initiate recovery successfully (with time travel)", async function () {
            // Увеличиваем время на 7 дней для прохождения GUARDIAN_DELAY
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await expect(
                soulRecovery.connect(guardian1).initiateRecovery(1, user2.address)
            ).to.emit(soulRecovery, "RecoveryInitiated")
             .withArgs(1, user1.address, user2.address, guardian1.address);

            expect(await soulRecovery.isRecoveryActive(1)).to.be.true;
            
            const recoveryInfo = await soulRecovery.getRecoveryInfo(1);
            expect(recoveryInfo.newOwner).to.equal(user2.address);
            expect(recoveryInfo.guardian).to.equal(guardian1.address);
            expect(recoveryInfo.isActive).to.be.true;
        });

        it("Should reject recovery before guardian delay", async function () {
            await expect(
                soulRecovery.connect(guardian1).initiateRecovery(1, user2.address)
            ).to.be.revertedWith("SoulRecovery: guardian delay not passed");
        });

        it("Should complete recovery successfully (with time travel)", async function () {
            // Увеличиваем время на 7 дней для GUARDIAN_DELAY
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Инициируем восстановление
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            // Увеличиваем время на 24 часа для RECOVERY_DELAY
            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Проверяем, что можно подтвердить
            expect(await soulRecovery.canConfirmRecovery(1)).to.be.true;

            // Подтверждаем восстановление
            await expect(
                soulRecovery.connect(guardian1).confirmRecovery(1)
            ).to.emit(soulRecovery, "RecoveryCompleted")
             .withArgs(1, user2.address)
             .and.to.emit(soulboundCore, "Transfer")
             .withArgs(user1.address, user2.address, 1);

            // Проверяем, что владелец изменился
            expect(await soulboundCore.ownerOf(1)).to.equal(user2.address);
            expect(await soulRecovery.isRecoveryActive(1)).to.be.false;
        });

        it("Should cancel recovery by token owner", async function () {
            // Увеличиваем время на 7 дней
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Инициируем восстановление
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);
            expect(await soulRecovery.isRecoveryActive(1)).to.be.true;

            // Отменяем восстановление
            await expect(
                soulRecovery.connect(user1).cancelRecovery(1)
            ).to.emit(soulRecovery, "RecoveryCancelled")
             .withArgs(1, user1.address);

            expect(await soulRecovery.isRecoveryActive(1)).to.be.false;
        });

        it("Should reject recovery before delay", async function () {
            // Увеличиваем время на 7 дней для GUARDIAN_DELAY
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Инициируем восстановление
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            // Пытаемся подтвердить до истечения RECOVERY_DELAY
            expect(await soulRecovery.canConfirmRecovery(1)).to.be.false;

            await expect(
                soulRecovery.connect(guardian1).confirmRecovery(1)
            ).to.be.revertedWith("SoulRecovery: recovery delay not passed");
        });
    });

    describe("Access Control", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
        });

        it("Should reject unauthorized recovery initiation", async function () {
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await expect(
                soulRecovery.connect(user2).initiateRecovery(1, user2.address)
            ).to.be.revertedWith("SoulRecovery: not authorized guardian");

            await expect(
                soulRecovery.connect(user1).initiateRecovery(1, user2.address)
            ).to.be.revertedWith("SoulRecovery: not authorized guardian");
        });

        it("Should reject unauthorized recovery confirmation", async function () {
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await expect(
                soulRecovery.connect(user2).confirmRecovery(1)
            ).to.be.revertedWith("SoulRecovery: not authorized guardian");
        });

        it("Should reject unauthorized recovery cancellation", async function () {
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await expect(
                soulRecovery.connect(user2).cancelRecovery(1)
            ).to.be.revertedWith("SoulRecovery: not token owner");

            await expect(
                soulRecovery.connect(guardian1).cancelRecovery(1)
            ).to.be.revertedWith("SoulRecovery: not token owner");
        });
    });

    describe("Edge Cases", function () {
        it("Should handle non-existent tokens correctly", async function () {
            await expect(
                soulRecovery.connect(user1).setGuardian(999, guardian1.address)
            ).to.be.revertedWith("SoulRecovery: token does not exist");

            await expect(
                soulRecovery.getGuardianInfo(999)
            ).to.be.revertedWith("SoulRecovery: token does not exist");
        });

        it("Should handle tokens without guardians", async function () {
            await soulboundCore.mintSoul(user1.address);

            expect(await soulRecovery.hasActiveGuardian(1)).to.be.false;
            expect(await soulRecovery.getGuardian(1)).to.equal(ethers.ZeroAddress);
            expect(await soulRecovery.isRecoveryActive(1)).to.be.false;
        });

        it("Should handle multiple recovery attempts", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Первая попытка восстановления
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            // Вторая попытка должна быть отклонена
            await expect(
                soulRecovery.connect(guardian1).initiateRecovery(1, guardian1.address)
            ).to.be.revertedWith("SoulRecovery: recovery already active");
        });

        it("Should handle recovery time calculations", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Инициируем восстановление
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            // Проверяем время до подтверждения
            const timeLeft = await soulRecovery.getRecoveryTimeLeft(1);
            expect(timeLeft).to.be.greaterThan(0);
            expect(timeLeft).to.be.lessThanOrEqual(24 * 60 * 60);

            // После увеличения времени
            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            expect(await soulRecovery.getRecoveryTimeLeft(1)).to.equal(0);
            expect(await soulRecovery.canConfirmRecovery(1)).to.be.true;
        });

        it("Should validate guardian timestamps correctly", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const blockBefore = await ethers.provider.getBlock('latest');
            const timestampBefore = blockBefore.timestamp;
            
            // Устанавливаем guardian
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            
            const guardianInfo = await soulRecovery.getGuardianInfo(1);
            
            // Проверяем, что timestamp установлен корректно
            expect(guardianInfo.setTimestamp).to.be.greaterThanOrEqual(timestampBefore);
            expect(guardianInfo.setTimestamp).to.be.lessThanOrEqual(timestampBefore + 60); // В пределах минуты
        });

        it("Should validate recovery timestamps correctly", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            const blockBefore = await ethers.provider.getBlock('latest');
            const timestampBefore = blockBefore.timestamp;

            // Инициируем восстановление
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            const recoveryInfo = await soulRecovery.getRecoveryInfo(1);
            
            // Проверяем, что timestamp инициации установлен корректно
            expect(recoveryInfo.initiatedAt).to.be.greaterThanOrEqual(timestampBefore);
            expect(recoveryInfo.initiatedAt).to.be.lessThanOrEqual(timestampBefore + 60);
        });

        it("Should handle edge case: exactly at delay boundary", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            // Увеличиваем время точно на GUARDIAN_DELAY
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Должно работать точно на границе
            await expect(
                soulRecovery.connect(guardian1).initiateRecovery(1, user2.address)
            ).to.not.be.reverted;

            // Увеличиваем время точно на RECOVERY_DELAY
            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Должно работать точно на границе
            expect(await soulRecovery.canConfirmRecovery(1)).to.be.true;
            
            await expect(
                soulRecovery.connect(guardian1).confirmRecovery(1)
            ).to.not.be.reverted;
        });
    });

    describe("Gas Profiling", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
        });

        it("Should profile gas usage for setGuardian", async function () {
            const tx = await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            const receipt = await tx.wait();
            
            console.log(`Gas used for setGuardian: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed).to.be.lessThan(100000); // Реалистичный лимит
        });

        it("Should profile gas usage for initiateRecovery", async function () {
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            const tx = await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);
            const receipt = await tx.wait();
            
            console.log(`Gas used for initiateRecovery: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed).to.be.lessThan(130000); // Скорректированный лимит
        });

        it("Should profile gas usage for confirmRecovery", async function () {
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            
            // Увеличиваем время для обеих задержек
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            const tx = await soulRecovery.connect(guardian1).confirmRecovery(1);
            const receipt = await tx.wait();
            
            console.log(`Gas used for confirmRecovery: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed).to.be.lessThan(150000); // Включает executeRecovery
        });

        it("Should profile gas usage for view functions", async function () {
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            // View функции должны быть газоэффективными
            const gasEstimates = {
                getGuardian: await soulRecovery.getGuardian.estimateGas(1),
                hasActiveGuardian: await soulRecovery.hasActiveGuardian.estimateGas(1),
                isRecoveryActive: await soulRecovery.isRecoveryActive.estimateGas(1),
                getRecoveryTimeLeft: await soulRecovery.getRecoveryTimeLeft.estimateGas(1)
            };

            console.log("View functions gas estimates:", gasEstimates);
            
            for (const [func, gas] of Object.entries(gasEstimates)) {
                expect(gas).to.be.lessThan(35000, `${func} gas too high`);
            }
        });
    });

    describe("Integration with SoulboundCore", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
        });

        it("Should execute recovery through SoulboundCore", async function () {
            // Увеличиваем время для обеих задержек
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Проверяем владельца до восстановления
            expect(await soulboundCore.ownerOf(1)).to.equal(user1.address);
            expect(await soulboundCore.balanceOf(user1.address)).to.equal(1);
            expect(await soulboundCore.balanceOf(user2.address)).to.equal(0);

            // Выполняем восстановление
            await soulRecovery.connect(guardian1).confirmRecovery(1);

            // Проверяем владельца после восстановления
            expect(await soulboundCore.ownerOf(1)).to.equal(user2.address);
            expect(await soulboundCore.balanceOf(user1.address)).to.equal(0);
            expect(await soulboundCore.balanceOf(user2.address)).to.equal(1);
        });

        it("Should reject direct executeRecovery calls", async function () {
            await expect(
                soulboundCore.connect(user1).executeRecovery(1, user2.address)
            ).to.be.revertedWith("SoulboundCore: not recovery contract");

            await expect(
                soulboundCore.connect(guardian1).executeRecovery(1, user2.address)
            ).to.be.revertedWith("SoulboundCore: not recovery contract");
        });

        it("Should handle recovery contract removal", async function () {
            // Отключаем recovery контракт
            await soulboundCore.setRecoveryContract(ethers.ZeroAddress);
            
            expect(await soulboundCore.getRecoveryContract()).to.equal(ethers.ZeroAddress);

            // executeRecovery должен быть недоступен
            await expect(
                soulboundCore.connect(owner).executeRecovery(1, user2.address)
            ).to.be.revertedWith("SoulboundCore: not recovery contract");
        });

        it("Should validate complete recovery state changes", async function () {
            // Создаем изолированный контракт для этого теста
            const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
            const testSoulboundCore = await SoulboundCore.deploy("Test Soul", "TSOUL");
            await testSoulboundCore.waitForDeployment();

            const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
            const testSoulRecovery = await SoulRecovery.deploy(await testSoulboundCore.getAddress());
            await testSoulRecovery.waitForDeployment();

            await testSoulboundCore.setRecoveryContract(await testSoulRecovery.getAddress());

            await testSoulboundCore.mintSoul(user1.address);
            await testSoulRecovery.connect(user1).setGuardian(1, guardian1.address);

            // Проверяем начальное состояние
            expect(await testSoulboundCore.ownerOf(1)).to.equal(user1.address);
            expect(await testSoulboundCore.balanceOf(user1.address)).to.equal(1);
            expect(await testSoulboundCore.balanceOf(user2.address)).to.equal(0);

            // Полный процесс восстановления
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await testSoulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            // Состояние во время восстановления
            expect(await testSoulboundCore.ownerOf(1)).to.equal(user1.address); // Еще не изменилось
            expect(await testSoulRecovery.isRecoveryActive(1)).to.be.true;

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await testSoulRecovery.connect(guardian1).confirmRecovery(1);

            // Финальное состояние
            expect(await testSoulboundCore.ownerOf(1)).to.equal(user2.address);
            expect(await testSoulboundCore.balanceOf(user1.address)).to.equal(0);
            expect(await testSoulboundCore.balanceOf(user2.address)).to.equal(1);
            expect(await testSoulRecovery.isRecoveryActive(1)).to.be.false;
        });

        it("Should handle guardian replacement scenario", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            // Устанавливаем первого guardian
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            expect(await soulRecovery.getGuardian(1)).to.equal(guardian1.address);

            // Заменяем на второго guardian
            await soulRecovery.connect(user1).setGuardian(1, guardian2.address);
            expect(await soulRecovery.getGuardian(1)).to.equal(guardian2.address);

            // Старый guardian не должен иметь доступ
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await expect(
                soulRecovery.connect(guardian1).initiateRecovery(1, user2.address)
            ).to.be.revertedWith("SoulRecovery: not authorized guardian");

            // Новый guardian должен работать
            await expect(
                soulRecovery.connect(guardian2).initiateRecovery(1, user2.address)
            ).to.not.be.reverted;
        });
    });
});
