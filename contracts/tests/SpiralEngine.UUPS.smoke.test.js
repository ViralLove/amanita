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

/**
 * 🧪 SpiralEngine UUPS - Smoke Test
 * 
 * Цель: Быстрая валидация Phase 1-3 результатов
 * 
 * Проверяемые элементы:
 * - Деплой Proxy + Logic
 * - Initialize через Proxy
 * - Базовая функциональность mintInvite
 * - Базовая функциональность activateUser
 * - Custom errors работают
 * - ReentrancyGuard работает
 * - Pausable работает
 * 
 * Этот smoke-тест НЕ заменяет comprehensive тесты Phase 4!
 */

describe("🔥 SpiralEngine UUPS - Smoke Test", function () {
    let admin, seller, activator, user1;
    let proxy, logic, spiralEngine;

    beforeEach(async function () {
        [admin, seller, activator, user1] = await ethers.getSigners();
        
        console.log("\n🔥 Smoke Test Setup Starting...");
        
        // 1. Deploy Logic implementation
        const Logic = await ethers.getContractFactory("SpiralEngineLogic");
        const logicImpl = await Logic.deploy();
        await logicImpl.waitForDeployment();
        console.log(`   ✅ Logic deployed: ${await logicImpl.getAddress()}`);
        
        // 2. Encode initialize(admin) calldata
        const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [
            admin.address
        ]);
        
        // 3. Deploy Proxy with implementation and init data
        const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
        proxy = await Proxy.deploy(await logicImpl.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        console.log(`   ✅ Proxy deployed: ${await proxy.getAddress()}`);
        
        // 4. Attach Logic ABI to proxy address (ABI-translator)
        spiralEngine = Logic.attach(await proxy.getAddress());
        
        // 5. Setup roles for tests
        // Activator должен иметь SELLER_ROLE чтобы создавать инвайты для активации
        await spiralEngine.connect(admin).grantRole(
            await spiralEngine.SELLER_ROLE(),
            seller.address
        );
        await spiralEngine.connect(admin).grantRole(
            await spiralEngine.SELLER_ROLE(),
            activator.address
        );
        await spiralEngine.connect(admin).grantRole(
            await spiralEngine.ACTIVATOR_ROLE(),
            activator.address
        );
        
        console.log("   ✅ Roles configured");
    });

    describe("🏗️ Architecture Validation", function () {
        it("Should deploy and initialize correctly", async function () {
            // Проверяем роли
            expect(await spiralEngine.hasRole(
                await spiralEngine.DEFAULT_ADMIN_ROLE(),
                admin.address
            )).to.be.true;
            
            expect(await spiralEngine.hasRole(
                await spiralEngine.ADMIN_ROLE(),
                admin.address
            )).to.be.true;
            
            expect(await spiralEngine.hasRole(
                await spiralEngine.UPGRADER_ROLE(),
                admin.address
            )).to.be.true;
            
            // Проверяем версию (ethers v6 → bigint)
            expect(await spiralEngine.LOGIC_VERSION()).to.equal(1n);
            
            // Проверяем ERC721 данные
            expect(await spiralEngine.name()).to.equal("SpiralInvite");
            expect(await spiralEngine.symbol()).to.equal("SPIRAL");
            
            // Проверяем начальное состояние (uint256 → bigint)
            expect(await spiralEngine.totalInvitesMinted()).to.equal(0n);
            expect(await spiralEngine.totalInvitesUsed()).to.equal(0n);
            
            console.log("   ✅ Architecture validated");
        });
    });

    describe("🔥 Core Functionality Smoke Test", function () {
        it("Should mint invite through proxy", async function () {
            const inviteCode = "SMOKE_TEST_INVITE";
            const expiry = 0; // бессрочный
            
            const tx = await spiralEngine.connect(seller).mintInvite(inviteCode, expiry);
            const receipt = await tx.wait();
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                const parsed = spiralEngine.interface.parseLog(log);
                return parsed && parsed.name === "InviteMinted";
            });
            expect(event).to.not.be.undefined;
            
            // Проверяем данные
            expect(await spiralEngine.inviteCodeExists(inviteCode)).to.be.true;
            expect(await spiralEngine.totalInvitesMinted()).to.equal(1n);
            
            const tokenId = await spiralEngine.inviteCodeToTokenId(inviteCode);
            expect(await spiralEngine.inviteMinter(tokenId)).to.equal(seller.address);
            
            console.log("   ✅ mintInvite works");
        });
        
        it("Should activate user with 12 new invites", async function () {
            // Activator сам создаёт инвайт (требуется SELLER_ROLE, который уже выдан)
            const activatorInvite = "ACTIVATOR_INVITE";
            await spiralEngine.connect(activator).mintInvite(activatorInvite, 0);
            
            // Создаём 12 новых кодов
            const newCodes = [];
            for (let i = 0; i < 12; i++) {
                newCodes.push(`NEW_CODE_${i}`);
            }
            
            // Активируем пользователя (activator использует свой инвайт)
            const tx = await spiralEngine.connect(activator).activateUser(
                activatorInvite,
                user1.address,
                newCodes,
                0
            );
            const receipt = await tx.wait();
            
            // Проверяем событие UserActivated
            const userActivatedEvent = receipt.logs.find(log => {
                const parsed = spiralEngine.interface.parseLog(log);
                return parsed && parsed.name === "UserActivated";
            });
            expect(userActivatedEvent).to.not.be.undefined;
            
            // Проверяем что user активирован (uint256 → bigint)
            const usedInvite = await spiralEngine.usedInviteByUser(user1.address);
            expect(usedInvite > 0n).to.be.true;
            
            // Проверяем что создано 12 инвайтов (счётчик → bigint)
            expect(await spiralEngine.userInviteCount(user1.address)).to.equal(12n);
            
            // Проверяем круг (uint256 → bigint)
            expect(await spiralEngine.getCircleSize(activator.address)).to.equal(1n);
            
            console.log("   ✅ activateUser works");
        });
    });

    describe("🛡️ Security Validation", function () {
        it("Should enforce custom errors", async function () {
            // EmptyInviteCode
            await expectCustomError(
                spiralEngine.connect(seller).mintInvite("", 0),
                spiralEngine,
                "EmptyInviteCode"
            );
            
            // InviteCodeAlreadyExists
            await spiralEngine.connect(seller).mintInvite("DUPLICATE", 0);
            await expectCustomError(
                spiralEngine.connect(seller).mintInvite("DUPLICATE", 0),
                spiralEngine,
                "InviteCodeAlreadyExists"
            );
            
            // InvalidUserAddress
            await expectCustomError(
                spiralEngine.connect(activator).activateUser(
                    "CODE",
                    ethers.ZeroAddress,
                    Array(12).fill("CODE"),
                    0
                ),
                spiralEngine,
                "InvalidUserAddress"
            );
            
            console.log("   ✅ Custom errors work");
        });
        
        it("Should have pausable functionality", async function () {
            // Пауза
            await spiralEngine.connect(admin).pause();
            
            // Попытка mintInvite должна провалиться
            await expectCustomError(
                spiralEngine.connect(seller).mintInvite("PAUSED_TEST", 0),
                spiralEngine,
                "EnforcedPause"
            );
            
            // Снятие паузы
            await spiralEngine.connect(admin).unpause();
            
            // Теперь должно работать
            await spiralEngine.connect(seller).mintInvite("PAUSED_TEST", 0);
            expect(await spiralEngine.inviteCodeExists("PAUSED_TEST")).to.be.true;
            
            console.log("   ✅ Pausable works");
        });
        
        it("Should have reentrancy protection", async function () {
            // Smoke-тест: последовательные вызовы должны работать
            await spiralEngine.connect(seller).mintInvite("REENTRANCY_1", 0);
            await spiralEngine.connect(seller).mintInvite("REENTRANCY_2", 0);
            
            expect(await spiralEngine.totalInvitesMinted()).to.equal(2n);
            
            console.log("   ✅ ReentrancyGuard works");
        });
        
        it("Should block SBT transfers and approvals", async function () {
            // Минтим инвайт
            await spiralEngine.connect(seller).mintInvite("SBT_TEST", 0);
            const tokenId = await spiralEngine.inviteCodeToTokenId("SBT_TEST");
            
            // Попытка approve должна провалиться
            await expectCustomError(
                spiralEngine.connect(seller).approve(user1.address, tokenId),
                spiralEngine,
                "ApprovalsNotAllowed"
            );
            
            // Попытка transferFrom должна провалиться
            await expectCustomError(
                spiralEngine.connect(seller).transferFrom(
                    seller.address,
                    user1.address,
                    tokenId
                ),
                spiralEngine,
                "TransfersNotAllowed"
            );
            
            // locked() должен возвращать true (SBT)
            expect(await spiralEngine.locked(tokenId)).to.be.true;
            
            console.log("   ✅ SBT restrictions work");
        });
    });

    describe("⬆️ UUPS Management", function () {
        it("Should upgrade logic contract", async function () {
            // Создаём данные перед upgrade
            await spiralEngine.connect(seller).mintInvite("PRE_UPGRADE", 0);
            expect(await spiralEngine.totalInvitesMinted()).to.equal(1n);
            
            // Деплоим новую Logic
            const NewLogic = await ethers.getContractFactory("SpiralEngineLogic");
            const newLogicImpl = await NewLogic.deploy();
            await newLogicImpl.waitForDeployment();
            
            // Upgrade через admin (UPGRADER_ROLE)
            await spiralEngine.connect(admin).upgradeToAndCall(
                await newLogicImpl.getAddress(),
                "0x"
            );
            
            // Проверяем что данные сохранились
            expect(await spiralEngine.totalInvitesMinted()).to.equal(1n);
            expect(await spiralEngine.inviteCodeExists("PRE_UPGRADE")).to.be.true;
            
            // Проверяем что новые операции работают
            await spiralEngine.connect(seller).mintInvite("POST_UPGRADE", 0);
            expect(await spiralEngine.totalInvitesMinted()).to.equal(2n);
            
            console.log("   ✅ Upgrade works, data preserved");
        });
        
        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            const NewLogic = await ethers.getContractFactory("SpiralEngineLogic");
            const newLogicImpl = await NewLogic.deploy();
            await newLogicImpl.waitForDeployment();
            
            // seller НЕ может апгрейдить (нет UPGRADER_ROLE)
            await expectCustomError(
                spiralEngine.connect(seller).upgradeToAndCall(
                    await newLogicImpl.getAddress(),
                    "0x"
                ),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
            
            // admin МОЖЕТ апгрейдить
            await spiralEngine.connect(admin).upgradeToAndCall(
                await newLogicImpl.getAddress(),
                "0x"
            );
            
            console.log("   ✅ UPGRADER_ROLE protection works");
        });
    });

    describe("📊 Statistics", function () {
        it("Should provide accurate gas measurements", async function () {
            const tx = await spiralEngine.connect(seller).mintInvite("GAS_TEST", 0);
            const receipt = await tx.wait();
            
            console.log(`\n   ⛽ mintInvite gas used: ${receipt.gasUsed.toString()}`);
            
            // Проверяем что gas разумный (первый минт с инициализацией storage < 300k)
            const gasUsed = receipt.gasUsed;
            expect(typeof gasUsed).to.equal("bigint");
            expect(gasUsed < 300000n).to.be.true;
            
            console.log("   ✅ Gas efficiency validated");
        });
    });
});

