const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * ActivityRegistry UUPS — Smoke Test (Фаза 6: опционально)
 *
 * Цель: быстрая проверка деплоя Proxy+Logic и базового сценария (createActivity(Event, cid) + activateActivity(1)).
 */
describe("ActivityRegistry UUPS - Smoke Test", function () {
    let admin, creator;
    let activityRegistry, spiralEngine, logic, proxy;

    beforeEach(async function () {
        [admin, creator] = await ethers.getSigners();

        const MockSpiralEngine = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await MockSpiralEngine.deploy();
        await spiralEngine.waitForDeployment();

        const ACTIVITY_CREATOR_ROLE = await spiralEngine.ACTIVITY_CREATOR_ROLE();
        await spiralEngine.grantRole(ACTIVITY_CREATOR_ROLE, creator.address);
        await spiralEngine.setUserActivated(creator.address, true);

        const Logic = await ethers.getContractFactory("ActivityRegistryLogic");
        logic = await Logic.deploy();
        await logic.waitForDeployment();

        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        const Proxy = await ethers.getContractFactory("ActivityRegistryProxy");
        proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();

        activityRegistry = Logic.attach(await proxy.getAddress());
    });

    it("должен создать активность (Event) и активировать её", async function () {
        const tx = await activityRegistry.connect(creator).createActivity(0, "QmSmokeCID");
        await tx.wait();
        const id = (await activityRegistry.getActivitiesByCreator(creator.address))[0];
        expect(Number(id)).to.equal(1);

        const a = await activityRegistry.getActivity(1);
        expect(a.creator).to.equal(creator.address);
        expect(a.metadataCID).to.equal("QmSmokeCID");
        expect(a.active).to.be.false;

        await activityRegistry.connect(creator).activateActivity(1);
        const aAfter = await activityRegistry.getActivity(1);
        expect(aAfter.active).to.be.true;

        const published = await activityRegistry.getPublishedActivityIds();
        expect(published.map(n => Number(n))).to.deep.equal([1]);
    });
});
