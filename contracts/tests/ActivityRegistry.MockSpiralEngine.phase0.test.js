const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * Фаза 0: проверка MockSpiralEngine для ActivityRegistry
 *
 * Цель:
 * - Зафиксировать константу ACTIVITY_CREATOR_ROLE и паттерн вызова grantRole/setUserActivated.
 * - Убедиться, что мок деплоится и hasRole/usedInviteByUser возвращают ожидаемые значения.
 *
 * Референс: solution-architecture-task1-activity-registry.md, Фаза 0.
 */
describe("ActivityRegistry Phase 0 — MockSpiralEngine и ACTIVITY_CREATOR_ROLE", function () {
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

    it("должен экспортировать SELLER_ROLE и ACTIVITY_CREATOR_ROLE", async function () {
        const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        const ACTIVITY_CREATOR_ROLE = await spiralEngine.ACTIVITY_CREATOR_ROLE();

        expect(SELLER_ROLE).to.equal(ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE")));
        expect(ACTIVITY_CREATOR_ROLE).to.equal(
            ethers.keccak256(ethers.toUtf8Bytes("ACTIVITY_CREATOR_ROLE"))
        );
    });

    it("паттерн: grantRole(ACTIVITY_CREATOR_ROLE, creator) + setUserActivated(creator, true)", async function () {
        const ACTIVITY_CREATOR_ROLE = await spiralEngine.ACTIVITY_CREATOR_ROLE();

        // Выдача роли и активация (паттерн для тестов ActivityRegistry)
        await spiralEngine.grantRole(ACTIVITY_CREATOR_ROLE, creator.address);
        await spiralEngine.setUserActivated(creator.address, true);

        expect(await spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, creator.address)).to.be.true;
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.not.equal(0);
    });

    it("hasRole возвращает false до grantRole и true после", async function () {
        const ACTIVITY_CREATOR_ROLE = await spiralEngine.ACTIVITY_CREATOR_ROLE();

        expect(await spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, creator.address)).to.be.false;

        await spiralEngine.grantRole(ACTIVITY_CREATOR_ROLE, creator.address);
        expect(await spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, creator.address)).to.be.true;
    });

    it("usedInviteByUser возвращает 0 до setUserActivated(true) и 1 после", async function () {
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(0n);

        await spiralEngine.setUserActivated(creator.address, true);
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(1n);

        await spiralEngine.setUserActivated(creator.address, false);
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(0n);
    });

    it("несколько creator: каждый со своей ролью и активацией", async function () {
        const ACTIVITY_CREATOR_ROLE = await spiralEngine.ACTIVITY_CREATOR_ROLE();

        await spiralEngine.grantRole(ACTIVITY_CREATOR_ROLE, creator.address);
        await spiralEngine.setUserActivated(creator.address, true);
        await spiralEngine.grantRole(ACTIVITY_CREATOR_ROLE, otherCreator.address);
        await spiralEngine.setUserActivated(otherCreator.address, true);

        expect(await spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, creator.address)).to.be.true;
        expect(await spiralEngine.hasRole(ACTIVITY_CREATOR_ROLE, otherCreator.address)).to.be.true;
        expect(await spiralEngine.usedInviteByUser(creator.address)).to.equal(1n);
        expect(await spiralEngine.usedInviteByUser(otherCreator.address)).to.equal(1n);
    });
});
