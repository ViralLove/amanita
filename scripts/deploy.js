const { ethers } = require("hardhat");
const fs = require("fs");

const PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || "0x0000000000000000000000000000000000000000000000000000000000000000";

async function main() {
  // Деплой AmanitaToken
  const AmanitaToken = await ethers.getContractFactory("AmanitaToken");
  const amanitaToken = await AmanitaToken.deploy();
  await amanitaToken.waitForDeployment();
  console.log("AmanitaToken deployed to:", amanitaToken.target);

  // Деплой InviteNFT
  const InviteNFT = await ethers.getContractFactory("InviteNFT");
  const inviteNFT = await InviteNFT.deploy();
  await inviteNFT.waitForDeployment();
  console.log("InviteNFT deployed to:", inviteNFT.target);

  // Деплой AmanitaSale
  const AmanitaSale = await ethers.getContractFactory("AmanitaSale");
  const amanitaSale = await AmanitaSale.deploy();
  await amanitaSale.waitForDeployment();
  console.log("AmanitaSale deployed to:", amanitaSale.target);

  // Деплой OrderNFT
  const OrderNFT = await ethers.getContractFactory("OrderNFT");
  const orderNFT = await OrderNFT.deploy();
  await orderNFT.waitForDeployment();
  console.log("OrderNFT deployed to:", orderNFT.target);

  // Деплой ReviewNFT
  const ReviewNFT = await ethers.getContractFactory("ReviewNFT");
  const reviewNFT = await ReviewNFT.deploy();
  await reviewNFT.waitForDeployment();
  console.log("ReviewNFT deployed to:", reviewNFT.target);

  // Сохраняем адреса в файл
  const addresses = {
    AmanitaToken: amanitaToken.target,
    InviteNFT: inviteNFT.target,
    AmanitaSale: amanitaSale.target,
    OrderNFT: orderNFT.target,
    ReviewNFT: reviewNFT.target,
  };
  fs.writeFileSync("deploy.json", JSON.stringify(addresses, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
}); 