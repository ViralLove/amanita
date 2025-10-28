const hre = require("hardhat");
const { Web3 } = require("web3");

async function main() {
    const web3 = new Web3("http://localhost:8545");
    
    const ORGANIC_REGISTRY_ADDRESS = process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS;
    
    const OrganicComponentRegistryLogic = await hre.artifacts.readArtifact("OrganicComponentRegistryLogic");
    const registry = new web3.eth.Contract(OrganicComponentRegistryLogic.abi, ORGANIC_REGISTRY_ADDRESS);
    
    console.log(`📊 Получение событий ComponentCreated...\n`);
    
    const events = await registry.getPastEvents('ComponentCreated', {
        fromBlock: 0,
        toBlock: 'latest'
    });
    
    console.log(`Найдено событий: ${events.length}\n`);
    
    events.forEach((event, index) => {
        console.log(`${index + 1}. componentId: ${event.returnValues.componentId}`);
        console.log(`   → businessId: ${event.returnValues.businessId}`);
        console.log(`   → metadataCID: ${event.returnValues.metadataCID}`);
        console.log(`   → creator: ${event.returnValues.creator}`);
        console.log(`   → block: ${event.blockNumber}`);
        console.log();
    });
}

main().catch(console.error);
