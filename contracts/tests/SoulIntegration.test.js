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

describe("SoulIntegration", function () {
    let soulboundCore, soulIntegration, mockSpiralEngine;
    let owner, user1, user2, user3;
    
    // Утилиты для логирования
    async function logContractState(context) {
        const totalSupply = await soulboundCore.getTotalSupply();
        const nextTokenId = await soulboundCore.getNextTokenId();
        const integrationContract = await soulboundCore.getIntegrationContract();
        const notificationsEnabled = await soulIntegration.areNotificationsEnabled();
        
        console.log(`\n=== ${context} ===`);
        console.log(`Total Supply: ${totalSupply}`);
        console.log(`Next Token ID: ${nextTokenId}`);
        console.log(`Integration Contract: ${integrationContract}`);
        console.log(`Notifications Enabled: ${notificationsEnabled}`);
    }
    
    async function logTransactionDetails(tx, operation) {
        const receipt = await tx.wait();
        console.log(`\n--- ${operation} ---`);
        console.log(`Gas Used: ${receipt.gasUsed}`);
        console.log(`Transaction Hash: ${receipt.hash}`);
        
        // Логируем события
        const soulboundCoreAddress = await soulboundCore.getAddress();
        const soulIntegrationAddress = await soulIntegration.getAddress();
        const mockSpiralEngineAddress = await mockSpiralEngine.getAddress();
        
        receipt.logs.forEach((log, index) => {
            try {
                let parsed = null;
                if (log.address === soulboundCoreAddress) {
                    parsed = soulboundCore.interface.parseLog(log);
                } else if (log.address === soulIntegrationAddress) {
                    parsed = soulIntegration.interface.parseLog(log);
                } else if (log.address === mockSpiralEngineAddress) {
                    parsed = mockSpiralEngine.interface.parseLog(log);
                }
                
                if (parsed) {
                    console.log(`Event ${index}: ${parsed.name}`, parsed.args);
                }
            } catch (e) {
                console.log(`Event ${index}: Raw log`, log);
            }
        });
    }
    
    beforeEach(async function () {
        [owner, user1, user2, user3] = await ethers.getSigners();
        
        // Создаем случайные кошельки для тестов
        const randomWallet1 = ethers.Wallet.createRandom().connect(ethers.provider);
        const randomWallet2 = ethers.Wallet.createRandom().connect(ethers.provider);
        const randomWallet3 = ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Финансируем случайные кошельки
        await owner.sendTransaction({
            to: randomWallet1.address,
            value: ethers.parseEther("1.0")
        });
        await owner.sendTransaction({
            to: randomWallet2.address,
            value: ethers.parseEther("1.0")
        });
        await owner.sendTransaction({
            to: randomWallet3.address,
            value: ethers.parseEther("1.0")
        });
        
        user1 = randomWallet1;
        user2 = randomWallet2;
        user3 = randomWallet3;
        
        // Деплой мока с интерфейсом уведомлений Soul (SoulNotificationMock)
        const SoulNotificationMock = await ethers.getContractFactory("SoulNotificationMock");
        mockSpiralEngine = await SoulNotificationMock.deploy();
        await mockSpiralEngine.waitForDeployment();
        
        // Деплой SoulboundCore
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        soulboundCore = await SoulboundCore.deploy("Test Soul", "TSOUL");
        await soulboundCore.waitForDeployment();
        
        // Деплой SoulIntegration
        const SoulIntegration = await ethers.getContractFactory("SoulIntegration");
        soulIntegration = await SoulIntegration.deploy(
            await mockSpiralEngine.getAddress(),
            await soulboundCore.getAddress()
        );
        await soulIntegration.waitForDeployment();
        
        // Подключаем интеграцию к SoulboundCore
        await soulboundCore.setIntegrationContract(await soulIntegration.getAddress());
    });
    
    describe("Deployment and Integration", function () {
        it("Should deploy with correct initial state", async function () {
            expect(await soulIntegration.getSpiralEngine()).to.equal(await mockSpiralEngine.getAddress());
            expect(await soulIntegration.getSoulboundCore()).to.equal(await soulboundCore.getAddress());
            expect(await soulIntegration.areNotificationsEnabled()).to.be.true;
            expect(await soulIntegration.isIntegrationValid()).to.be.true;
            
            await logContractState("Deployment State");
        });
        
        it("Should connect SoulboundCore to integration contract", async function () {
            expect(await soulboundCore.getIntegrationContract()).to.equal(await soulIntegration.getAddress());
        });
        
        it("Should revert deployment with invalid addresses", async function () {
            const SoulIntegration = await ethers.getContractFactory("SoulIntegration");
            await expectRevertWithMessage(
                SoulIntegration.deploy(ethers.ZeroAddress, await soulboundCore.getAddress()),
                "SoulIntegration: invalid SpiralEngine address"
            );
            await expectRevertWithMessage(
                SoulIntegration.deploy(await mockSpiralEngine.getAddress(), ethers.ZeroAddress),
                "SoulIntegration: invalid SoulboundCore address"
            );
        });
    });
    
    describe("Soul Creation Notifications", function () {
        it("Should notify SpiralEngine when soul is created via mintSoul", async function () {
            const tx = await soulboundCore.mintSoul(user1.address);
            await logTransactionDetails(tx, "mintSoul with notification");
            
            expect(await mockSpiralEngine.getLastNotifiedTokenId()).to.equal(1n);
            expect(await mockSpiralEngine.lastNotifiedOwner()).to.equal(user1.address);
            expect(await mockSpiralEngine.getNotificationCount()).to.equal(1n);
            
            const receipt = await tx.wait();
            const soulNotifiedEvent = receipt.logs.find(log => {
                try {
                    const parsed = soulIntegration.interface.parseLog(log);
                    return parsed.name === "SoulNotified";
                } catch {
                    return false;
                }
            });
            expect(soulNotifiedEvent).to.not.be.undefined;
            const parsedEvent = soulIntegration.interface.parseLog(soulNotifiedEvent);
            expect(parsedEvent.args.tokenId).to.equal(1n);
            expect(parsedEvent.args.owner).to.equal(user1.address);
            expect(parsedEvent.args.eventType).to.equal("created");
        });
        
        it("Should notify SpiralEngine for each token in batch mint", async function () {
            const tx = await soulboundCore.mintSoulBatch(user1.address, 3);
            await logTransactionDetails(tx, "mintSoulBatch with notifications");
            
            expect(await mockSpiralEngine.getNotificationCount()).to.equal(3n);
            expect(await mockSpiralEngine.getLastNotifiedTokenId()).to.equal(3n);
            expect(await mockSpiralEngine.lastNotifiedOwner()).to.equal(user1.address);
        });
        
        it("Should handle direct notification calls", async function () {
            // Сначала создаем токен
            await soulboundCore.mintSoul(user1.address);
            
            // Прямое уведомление через SoulIntegration
            const tx = await soulIntegration.notifySoulCreated(1, user1.address);
            await logTransactionDetails(tx, "Direct notifySoulCreated");
            
            expect(await mockSpiralEngine.getNotificationCount()).to.equal(2n);
        });
        
        it("Should validate token existence and ownership", async function () {
            await expectRevertWithMessage(soulIntegration.notifySoulCreated(999, user1.address), "SoulIntegration: token does not exist");
            await soulboundCore.mintSoul(user1.address);
            await expectRevertWithMessage(soulIntegration.notifySoulCreated(1, user2.address), "SoulIntegration: owner mismatch");
        });
        
        it("Should work when notifications are disabled", async function () {
            await soulIntegration.setNotificationsEnabled(false);
            await soulboundCore.mintSoul(user1.address);
            await expectRevertWithMessage(soulIntegration.notifySoulCreated(1, user1.address), "SoulIntegration: notifications disabled");
            expect(await soulboundCore.exists(1)).to.be.true;
            expect(await mockSpiralEngine.getNotificationCount()).to.equal(0n);
        });
    });
    
    describe("Recovery Notifications", function () {
        let soulRecovery;
        
        beforeEach(async function () {
            // Деплой SoulRecovery для тестирования восстановления
            const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
            soulRecovery = await SoulRecovery.deploy(await soulboundCore.getAddress());
            await soulRecovery.waitForDeployment();
            
            // Подключаем recovery контракт
            await soulboundCore.setRecoveryContract(await soulRecovery.getAddress());
            
            // Создаем токен
            await soulboundCore.mintSoul(user1.address);
            
            // Устанавливаем guardian'а
            await soulRecovery.connect(user1).setGuardian(1, user2.address);
        });
        
        it("Should notify SpiralEngine when soul is recovered", async function () {
            // Увеличиваем время на 7 дней + 1 секунда
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);
            
            // Инициируем восстановление
            await soulRecovery.connect(user2).initiateRecovery(1, user3.address);
            
            // Увеличиваем время на 24 часа + 1 секунда
            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);
            
            // Подтверждаем восстановление
            const tx = await soulRecovery.connect(user2).confirmRecovery(1);
            await logTransactionDetails(tx, "confirmRecovery with notification");
            
            expect(await mockSpiralEngine.getLastRecoveryTokenId()).to.equal(1n);
            expect(await mockSpiralEngine.lastRecoveryOldOwner()).to.equal(user1.address);
            expect(await mockSpiralEngine.lastRecoveryNewOwner()).to.equal(user3.address);
            expect(await mockSpiralEngine.getRecoveryNotificationCount()).to.equal(1n);
        });
        
        it("Should handle direct recovery notification calls", async function () {
            // Инициируем восстановление
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);
            
            await soulRecovery.connect(user2).initiateRecovery(1, user3.address);
            
            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);
            
            // Меняем владельца через recovery контракт (правильный способ)
            await soulRecovery.connect(user2).confirmRecovery(1);
            
            // Прямое уведомление о восстановлении
            const tx = await soulIntegration.notifySoulRecovered(1, user1.address, user3.address);
            await logTransactionDetails(tx, "Direct notifySoulRecovered");
            
            expect(await mockSpiralEngine.getRecoveryNotificationCount()).to.equal(2n);
        });
        
        it("Should validate recovery notification parameters", async function () {
            await expectRevertWithMessage(soulIntegration.notifySoulRecovered(1, ethers.ZeroAddress, user2.address), "SoulIntegration: invalid old owner address");
            await expectRevertWithMessage(soulIntegration.notifySoulRecovered(1, user1.address, ethers.ZeroAddress), "SoulIntegration: invalid new owner address");
            await expectRevertWithMessage(soulIntegration.notifySoulRecovered(1, user1.address, user1.address), "SoulIntegration: owners cannot be the same");
        });
        
        it("Should validate new owner matches current owner", async function () {
            await expectRevertWithMessage(soulIntegration.notifySoulRecovered(1, user2.address, user3.address), "SoulIntegration: new owner mismatch");
        });
    });
    
    describe("Error Handling", function () {
        let faultySpiralEngine;
        
        beforeEach(async function () {
            // Создаем faulty SpiralEngine для тестирования ошибок
            const FaultySpiralEngine = await ethers.getContractFactory("FaultySpiralEngine");
            faultySpiralEngine = await FaultySpiralEngine.deploy();
            await faultySpiralEngine.waitForDeployment();
        });
        
        it("Should handle SpiralEngine errors gracefully", async function () {
            // Переключаемся на faulty engine
            await soulIntegration.setSpiralEngine(await faultySpiralEngine.getAddress());
            
            // Создание токена должно работать, даже если SpiralEngine падает
            const tx = await soulboundCore.mintSoul(user1.address);
            await logTransactionDetails(tx, "mintSoul with faulty SpiralEngine");
            
            // Токен должен быть создан
            expect(await soulboundCore.exists(1)).to.be.true;
            expect(await soulboundCore.ownerOf(1)).to.equal(user1.address);
            
            // Проверяем событие NotificationFailed
            const receipt = await tx.wait();
            const failedEvent = receipt.logs.find(log => {
                try {
                    const parsed = soulIntegration.interface.parseLog(log);
                    return parsed.name === "NotificationFailed";
                } catch {
                    return false;
                }
            });
            
            expect(failedEvent).to.not.be.undefined;
        });
        
        it("Should emit NotificationFailed for direct calls with faulty engine", async function () {
            await soulIntegration.setSpiralEngine(await faultySpiralEngine.getAddress());
            await soulboundCore.mintSoul(user1.address);
            
            const tx = await soulIntegration.notifySoulCreated(1, user1.address);
            await logTransactionDetails(tx, "Direct call with faulty engine");
            
            const receipt = await tx.wait();
            const failedEvent = receipt.logs.find(log => {
                try {
                    const parsed = soulIntegration.interface.parseLog(log);
                    return parsed.name === "NotificationFailed";
                } catch {
                    return false;
                }
            });
            
            expect(failedEvent).to.not.be.undefined;
            const parsedEvent = soulIntegration.interface.parseLog(failedEvent);
            expect(parsedEvent.args.tokenId).to.equal(1n);
            expect(parsedEvent.args.eventType).to.equal("created");
        });
        
        it("Should work when no integration contract is set", async function () {
            // Убираем интеграционный контракт
            await soulboundCore.setIntegrationContract(ethers.ZeroAddress);
            
            // Создание токена должно работать без ошибок
            const tx = await soulboundCore.mintSoul(user1.address);
            await logTransactionDetails(tx, "mintSoul without integration");
            
            expect(await soulboundCore.exists(1)).to.be.true;
            expect(await mockSpiralEngine.getNotificationCount()).to.equal(0n);
        });
        
        it("Should handle invalid SpiralEngine address gracefully", async function () {
            // Устанавливаем несуществующий адрес
            await soulIntegration.setSpiralEngine("0x1234567890123456789012345678901234567890");
            
            // Создание токена должно работать
            const tx = await soulboundCore.mintSoul(user1.address);
            
            expect(await soulboundCore.exists(1)).to.be.true;
        });
        
        it("Should handle contract with no interface gracefully", async function () {
            // Устанавливаем адрес обычного EOA как SpiralEngine
            await soulIntegration.setSpiralEngine(user3.address);
            
            // Создание токена должно работать
            const tx = await soulboundCore.mintSoul(user1.address);
            
            expect(await soulboundCore.exists(1)).to.be.true;
        });
        
        it("Should emit proper events for unknown errors", async function () {
            // Создаем контракт, который бросает bytes без строки
            const BytesErrorEngine = await ethers.getContractFactory("BytesErrorEngine");
            const bytesErrorEngine = await BytesErrorEngine.deploy();
            await bytesErrorEngine.waitForDeployment();
            
            await soulIntegration.setSpiralEngine(await bytesErrorEngine.getAddress());
            await soulboundCore.mintSoul(user1.address);
            
            const tx = await soulIntegration.notifySoulCreated(1, user1.address);
            const receipt = await tx.wait();
            
            const failedEvent = receipt.logs.find(log => {
                try {
                    const parsed = soulIntegration.interface.parseLog(log);
                    return parsed.name === "NotificationFailed";
                } catch {
                    return false;
                }
            });
            
            expect(failedEvent).to.not.be.undefined;
            const parsedEvent = soulIntegration.interface.parseLog(failedEvent);
            expect(parsedEvent.args.reason).to.equal("Unknown error");
        });
    });
    
    describe("Access Control", function () {
        it("Should allow only owner to change SpiralEngine address", async function () {
            await expectCustomError(soulIntegration.connect(user1).setSpiralEngine(user2.address), soulIntegration, "OwnableUnauthorizedAccount");
            await soulIntegration.setSpiralEngine(user2.address);
            expect(await soulIntegration.getSpiralEngine()).to.equal(user2.address);
        });
        
        it("Should allow only owner to change SoulboundCore address", async function () {
            await expectCustomError(soulIntegration.connect(user1).setSoulboundCore(user2.address), soulIntegration, "OwnableUnauthorizedAccount");
            await soulIntegration.setSoulboundCore(user2.address);
            expect(await soulIntegration.getSoulboundCore()).to.equal(user2.address);
        });
        
        it("Should allow only owner to toggle notifications", async function () {
            await expectCustomError(soulIntegration.connect(user1).setNotificationsEnabled(false), soulIntegration, "OwnableUnauthorizedAccount");
            await soulIntegration.setNotificationsEnabled(false);
            expect(await soulIntegration.areNotificationsEnabled()).to.be.false;
        });
    });
    
    describe("Gas Profiling", function () {
        it("Should measure gas for notifySoulCreated", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const tx = await soulIntegration.notifySoulCreated(1, user1.address);
            const receipt = await tx.wait();
            
            console.log(`\n=== Gas Profiling: notifySoulCreated ===`);
            console.log(`Gas Used: ${receipt.gasUsed}`);
            
            expect(receipt.gasUsed < 75000n).to.be.true;
        });
        
        it("Should measure gas for notifySoulRecovered", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            // Настраиваем recovery для тестирования
            const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
            const testSoulRecovery = await SoulRecovery.deploy(await soulboundCore.getAddress());
            await testSoulRecovery.waitForDeployment();
            
            await soulboundCore.setRecoveryContract(await testSoulRecovery.getAddress());
            await testSoulRecovery.connect(user1).setGuardian(1, user2.address);
            
            // Увеличиваем время
            await ethers.provider.send("evm_increaseTime", [7 * 24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);
            
            await testSoulRecovery.connect(user2).initiateRecovery(1, user2.address);
            
            await ethers.provider.send("evm_increaseTime", [24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);
            
            // Меняем владельца через recovery контракт
            await testSoulRecovery.connect(user2).confirmRecovery(1);
            
            const tx = await soulIntegration.notifySoulRecovered(1, user1.address, user2.address);
            const receipt = await tx.wait();
            
            console.log(`\n=== Gas Profiling: notifySoulRecovered ===`);
            console.log(`Gas Used: ${receipt.gasUsed}`);
            
            expect(receipt.gasUsed < 80000n).to.be.true;
        });
        
        it("Should measure gas overhead for mintSoul with integration", async function () {
            const tx = await soulboundCore.mintSoul(user1.address);
            const receipt = await tx.wait();
            
            console.log(`\n=== Gas Profiling: mintSoul with integration ===`);
            console.log(`Gas Used: ${receipt.gasUsed}`);
            
            expect(receipt.gasUsed < 200000n).to.be.true;
        });
        
        it("Should measure gas for view functions", async function () {
            const gasEstimates = [];
            
            gasEstimates.push({
                function: "getSpiralEngine",
                gas: await soulIntegration.getSpiralEngine.estimateGas()
            });
            
            gasEstimates.push({
                function: "getSoulboundCore", 
                gas: await soulIntegration.getSoulboundCore.estimateGas()
            });
            
            gasEstimates.push({
                function: "areNotificationsEnabled",
                gas: await soulIntegration.areNotificationsEnabled.estimateGas()
            });
            
            gasEstimates.push({
                function: "isIntegrationValid",
                gas: await soulIntegration.isIntegrationValid.estimateGas()
            });
            
            console.log(`\n=== Gas Profiling: View Functions ===`);
            gasEstimates.forEach(estimate => {
                console.log(`${estimate.function}: ${estimate.gas} gas`);
                expect(estimate.gas < 30000n).to.be.true;
            });
        });
    });
});

// Mock контракты для тестирования

// MockSpiralEngine - успешно обрабатывает уведомления
const mockSpiralEngineSource = `
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MockSpiralEngine {
    uint256 public lastNotifiedTokenId;
    address public lastNotifiedOwner;
    uint256 public notificationCount;
    
    uint256 public lastRecoveryTokenId;
    address public lastRecoveryOldOwner;
    address public lastRecoveryNewOwner;
    uint256 public recoveryNotificationCount;
    
    event SoulCreatedNotification(uint256 indexed tokenId, address indexed owner);
    event SoulRecoveredNotification(uint256 indexed tokenId, address indexed oldOwner, address indexed newOwner);
    
    function notifySoulCreated(uint256 tokenId, address owner) external {
        lastNotifiedTokenId = tokenId;
        lastNotifiedOwner = owner;
        notificationCount++;
        emit SoulCreatedNotification(tokenId, owner);
    }
    
    function notifySoulRecovered(uint256 tokenId, address oldOwner, address newOwner) external {
        lastRecoveryTokenId = tokenId;
        lastRecoveryOldOwner = oldOwner;
        lastRecoveryNewOwner = newOwner;
        recoveryNotificationCount++;
        emit SoulRecoveredNotification(tokenId, oldOwner, newOwner);
    }
    
    function getNotificationCount() external view returns (uint256) {
        return notificationCount;
    }
    
    function getRecoveryNotificationCount() external view returns (uint256) {
        return recoveryNotificationCount;
    }
}`;

// FaultySpiralEngine - всегда бросает ошибку
const faultySpiralEngineSource = `
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FaultySpiralEngine {
    function notifySoulCreated(uint256, address) external pure {
        revert("FaultySpiralEngine: intentional error");
    }
    
    function notifySoulRecovered(uint256, address, address) external pure {
        revert("FaultySpiralEngine: intentional recovery error");
    }
}`;

// BytesErrorEngine - бросает ошибку без строки
const bytesErrorEngineSource = `
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BytesErrorEngine {
    function notifySoulCreated(uint256, address) external pure {
        assembly {
            revert(0, 0)
        }
    }
    
    function notifySoulRecovered(uint256, address, address) external pure {
        assembly {
            revert(0, 0)
        }
    }
}`;
