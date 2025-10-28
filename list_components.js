const hre = require("hardhat");
const { Web3 } = require("web3");

async function main() {
    const web3 = new Web3("http://localhost:8545");
    
    const ORGANIC_REGISTRY_ADDRESS = process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS;
    
    const OrganicComponentRegistryLogic = await hre.artifacts.readArtifact("OrganicComponentRegistryLogic");
    const registry = new web3.eth.Contract(OrganicComponentRegistryLogic.abi, ORGANIC_REGISTRY_ADDRESS);
    
    const count = await registry.methods.totalComponents().call();
    console.log(`📊 Всего компонентов: ${count}\n`);
    
    for (let i = 1; i <= count; i++) {
        try {
            const component = await registry.methods.getComponent(i).call();
            console.log(`${i}. ${component.businessId}`);
            console.log(`   → CID: ${component.metadataCID}`);
            console.log(`   → Creator: ${component.creator}`);
        } catch (error) {
            console.log(`${i}. ❌ Ошибка: ${error.message}`);
        }
    }
}

main().catch(console.error);
