const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * Фаза 0: проверка MockSpiralEngine для ActivityRegistry
 *
 * Цель:
 * - Зафиксировать роль ACTIVATOR_ROLE и паттерн вызова grantRole/setUserActivated.
 * - Убедиться, что мок деплоится и hasRole/usedInviteByUser возвращают ожидаемые значения.
 *
 * Референс: solution-architecture-task1-activity-registry.md, Фаза 0.
 */
describe("ActivityRegistry Phase 0 — MockSpiralEngine и ACTIVATOR_ROLE", function () {
    let spiralEngine;
    let admin, creator, otherCreator;

    beforeEach(async function () {
        [admin, creator, otherCreator] = await ethers.getSigners();

        const MockSpiralEngine = await ethers.getContractFactory(
            "contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine"
        );
        spiralEngine = await MockSpiralEngine.deploy();
        await spiralEngine.waitForDeployment();
    });

    it("должен задеплоить MockSpiralEngine", async function () {
        const addr = await spiralEngine.getAddress();
        expect(addr).to.match(/^0x[a-fA-F0-9]{40}$/);
    });

    it("должен экспортировать SELLER_ROLE и ACTIVATOR_ROLE", async function () {
        const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();

        expect(SELLER_ROLE).to.equal(ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE")));
        expect(ACTIVATOR_ROLE).to.equal(
            ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"))
        );
    });

    it("паттерн: grantRole(ACTIVATOR_ROLE, creator) + setUserActivated(creator, true)", async function () {
        const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();

        // Выдача роли и активация (паттерн для тестов ActivityRegistry)
        await spiralEngine.grantRole(ACTIVATOR_ROLE, creator.address);
        await spiralEngine.setUserActivated(creator.address, true);

        expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, creator.address)).to.be.true;
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.not.equal(0);
    });

    it("hasRole возвращает false до grantRole и true после", async function () {
        const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();

        expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, creator.address)).to.be.false;

        await spiralEngine.grantRole(ACTIVATOR_ROLE, creator.address);
        expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, creator.address)).to.be.true;
    });

    it("usedInviteByUser возвращает 0 до setUserActivated(true) и 1 после", async function () {
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(0n);

        await spiralEngine.setUserActivated(creator.address, true);
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(1n);

        await spiralEngine.setUserActivated(creator.address, false);
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(0n);
    });

    it("несколько creator: каждый со своей ролью и активацией", async function () {
        const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();

        await spiralEngine.grantRole(ACTIVATOR_ROLE, creator.address);
        await spiralEngine.setUserActivated(creator.address, true);
        await spiralEngine.grantRole(ACTIVATOR_ROLE, otherCreator.address);
        await spiralEngine.setUserActivated(otherCreator.address, true);

        expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, creator.address)).to.be.true;
        expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, otherCreator.address)).to.be.true;
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(1n);
        expect(await spiralEngine.usedInviteByUser(otherCreator.address)).to.equal(1n);
    });
});
