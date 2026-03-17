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
            const tx = await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulRecovery.interface.parseLog(log)?.name === "GuardianSet"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;
            const parsed = soulRecovery.interface.parseLog(ev);
            expect(parsed.args.tokenId).to.equal(1n);
            expect(parsed.args.guardian).to.equal(guardian1.address);

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
            
            const tx = await soulRecovery.connect(user1).removeGuardian(1);
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulRecovery.interface.parseLog(log)?.name === "GuardianSet"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;
            const parsed = soulRecovery.interface.parseLog(ev);
            expect(parsed.args.guardian).to.equal(ethers.ZeroAddress);

            expect(await soulRecovery.hasActiveGuardian(1)).to.be.false;
            expect(await soulRecovery.getGuardian(1)).to.equal(ethers.ZeroAddress);
        });

        it("Should reject invalid guardian addresses", async function () {
            await expectRevertWithMessage(soulRecovery.connect(user1).setGuardian(1, ethers.ZeroAddress), "SoulRecovery: invalid guardian address");
            await expectRevertWithMessage(soulRecovery.connect(user1).setGuardian(1, user1.address), "SoulRecovery: cannot be self guardian");
        });

        it("Should reject unauthorized guardian management", async function () {
            await expectRevertWithMessage(soulRecovery.connect(user2).setGuardian(1, guardian1.address), "SoulRecovery: not token owner");
            await expectRevertWithMessage(soulRecovery.connect(guardian1).setGuardian(1, guardian2.address), "SoulRecovery: not token owner");
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

            const tx = await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulRecovery.interface.parseLog(log)?.name === "RecoveryInitiated"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;
            const parsed = soulRecovery.interface.parseLog(ev);
            expect(parsed.args.tokenId).to.equal(1n);
            expect(parsed.args.newOwner).to.equal(user2.address);

            expect(await soulRecovery.isRecoveryActive(1)).to.be.true;
            
            const recoveryInfo = await soulRecovery.getRecoveryInfo(1);
            expect(recoveryInfo.newOwner).to.equal(user2.address);
            expect(recoveryInfo.guardian).to.equal(guardian1.address);
            expect(recoveryInfo.isActive).to.be.true;
        });

        it("Should reject recovery before guardian delay", async function () {
            await expectRevertWithMessage(soulRecovery.connect(guardian1).initiateRecovery(1, user2.address), "SoulRecovery: guardian delay not passed");
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

            const tx = await soulRecovery.connect(guardian1).confirmRecovery(1);
            const receipt = await tx.wait();
            const completed = receipt.logs.find(log => {
                try { return soulRecovery.interface.parseLog(log)?.name === "RecoveryCompleted"; } catch (_) { return false; }
            });
            const transfer = receipt.logs.find(log => {
                try { return soulboundCore.interface.parseLog(log)?.name === "Transfer"; } catch (_) { return false; }
            });
            expect(completed).to.be.ok;
            expect(transfer).to.be.ok;
            expect(soulRecovery.interface.parseLog(completed).args.tokenId).to.equal(1n);
            expect(soulRecovery.interface.parseLog(completed).args.newOwner).to.equal(user2.address);

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

            const tx = await soulRecovery.connect(user1).cancelRecovery(1);
            const receipt = await tx.wait();
            const ev = receipt.logs.find(log => {
                try { return soulRecovery.interface.parseLog(log)?.name === "RecoveryCancelled"; } catch (_) { return false; }
            });
            expect(ev).to.be.ok;
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

            await expectRevertWithMessage(soulRecovery.connect(guardian1).confirmRecovery(1), "SoulRecovery: recovery delay not passed");
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

            await expectRevertWithMessage(soulRecovery.connect(user2).initiateRecovery(1, user2.address), "SoulRecovery: not authorized guardian");
            await expectRevertWithMessage(soulRecovery.connect(user1).initiateRecovery(1, user2.address), "SoulRecovery: not authorized guardian");
        });

        it("Should reject unauthorized recovery confirmation", async function () {
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await expectRevertWithMessage(soulRecovery.connect(user2).confirmRecovery(1), "SoulRecovery: not authorized guardian");
        });

        it("Should reject unauthorized recovery cancellation", async function () {
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await expectRevertWithMessage(soulRecovery.connect(user2).cancelRecovery(1), "SoulRecovery: not token owner");
            await expectRevertWithMessage(soulRecovery.connect(guardian1).cancelRecovery(1), "SoulRecovery: not token owner");
        });
    });

    describe("Edge Cases", function () {
        it("Should handle non-existent tokens correctly", async function () {
            await expectRevertWithMessage(soulRecovery.connect(user1).setGuardian(999, guardian1.address), "SoulRecovery: token does not exist");
            await expectRevertWithMessage(soulRecovery.getGuardianInfo(999), "SoulRecovery: token does not exist");
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

            await expectRevertWithMessage(soulRecovery.connect(guardian1).initiateRecovery(1, guardian1.address), "SoulRecovery: recovery already active");
        });

        it("Should handle recovery time calculations", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            // Инициируем восстановление
            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            const timeLeft = await soulRecovery.getRecoveryTimeLeft(1);
            expect(timeLeft > 0n).to.be.true;
            expect(timeLeft <= 24n * 60n * 60n).to.be.true;

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            expect(await soulRecovery.getRecoveryTimeLeft(1)).to.equal(0n);
            expect(await soulRecovery.canConfirmRecovery(1)).to.be.true;
        });

        it("Should validate guardian timestamps correctly", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const blockBefore = await ethers.provider.getBlock('latest');
            const timestampBefore = blockBefore.timestamp;
            
            // Устанавливаем guardian
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            
            const guardianInfo = await soulRecovery.getGuardianInfo(1);
            
            const ts = typeof guardianInfo.setTimestamp === "bigint" ? guardianInfo.setTimestamp : BigInt(guardianInfo.setTimestamp);
            const tBefore = typeof timestampBefore === "bigint" ? timestampBefore : BigInt(timestampBefore);
            expect(ts >= tBefore).to.be.true;
            expect(ts <= tBefore + 60n).to.be.true;
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
            
            const at = typeof recoveryInfo.initiatedAt === "bigint" ? recoveryInfo.initiatedAt : BigInt(recoveryInfo.initiatedAt);
            const tBefore = typeof timestampBefore === "bigint" ? timestampBefore : BigInt(timestampBefore);
            expect(at >= tBefore).to.be.true;
            expect(at <= tBefore + 60n).to.be.true;
        });

        it("Should handle edge case: exactly at delay boundary", async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);

            // Увеличиваем время точно на GUARDIAN_DELAY
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);

            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            expect(await soulRecovery.canConfirmRecovery(1)).to.be.true;
            await soulRecovery.connect(guardian1).confirmRecovery(1);
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
            expect(receipt.gasUsed < 100000n).to.be.true;
        });

        it("Should profile gas usage for initiateRecovery", async function () {
            await soulRecovery.connect(user1).setGuardian(1, guardian1.address);
            
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60]);
            await ethers.provider.send("evm_mine");

            const tx = await soulRecovery.connect(guardian1).initiateRecovery(1, user2.address);
            const receipt = await tx.wait();
            
            console.log(`Gas used for initiateRecovery: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed < 130000n).to.be.true;
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
            expect(receipt.gasUsed < 150000n).to.be.true;
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
                expect(gas < 35000n, `${func} gas too high`).to.be.true;
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

            expect(await soulboundCore.ownerOf(1)).to.equal(user1.address);
            expect(await soulboundCore.balanceOf(user1.address)).to.equal(1n);
            expect(await soulboundCore.balanceOf(user2.address)).to.equal(0n);

            await soulRecovery.connect(guardian1).confirmRecovery(1);

            expect(await soulboundCore.ownerOf(1)).to.equal(user2.address);
            expect(await soulboundCore.balanceOf(user1.address)).to.equal(0n);
            expect(await soulboundCore.balanceOf(user2.address)).to.equal(1n);
        });

        it("Should reject direct executeRecovery calls", async function () {
            await expectRevertWithMessage(soulboundCore.connect(user1).executeRecovery(1, user2.address), "SoulboundCore: not recovery contract");
            await expectRevertWithMessage(soulboundCore.connect(guardian1).executeRecovery(1, user2.address), "SoulboundCore: not recovery contract");
        });

        it("Should handle recovery contract removal", async function () {
            await soulboundCore.setRecoveryContract(ethers.ZeroAddress);
            expect(await soulboundCore.getRecoveryContract()).to.equal(ethers.ZeroAddress);
            await expectRevertWithMessage(soulboundCore.connect(owner).executeRecovery(1, user2.address), "SoulboundCore: not recovery contract");
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

            expect(await testSoulboundCore.ownerOf(1)).to.equal(user1.address);
            expect(await testSoulboundCore.balanceOf(user1.address)).to.equal(1n);
            expect(await testSoulboundCore.balanceOf(user2.address)).to.equal(0n);

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

            expect(await testSoulboundCore.ownerOf(1)).to.equal(user2.address);
            expect(await testSoulboundCore.balanceOf(user1.address)).to.equal(0n);
            expect(await testSoulboundCore.balanceOf(user2.address)).to.equal(1n);
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

            await expectRevertWithMessage(soulRecovery.connect(guardian1).initiateRecovery(1, user2.address), "SoulRecovery: not authorized guardian");
            await soulRecovery.connect(guardian2).initiateRecovery(1, user2.address);
        });
    });
});
