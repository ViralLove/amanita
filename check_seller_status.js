const hre = require("hardhat");
const { Web3 } = require("web3");

async function main() {
    const web3 = new Web3("http://localhost:8545");
    
    const SELLER_ADDRESS = process.env.SELLER_ADDRESS;
    const SPIRAL_ENGINE_ADDRESS = process.env.SPIRAL_ENGINE_CONTRACT_ADDRESS;
    const ORGANIC_REGISTRY_ADDRESS = process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS;
    
    console.log("🔍 Проверка статуса Seller...");
    console.log(`   → Seller: ${SELLER_ADDRESS}`);
    console.log(`   → SpiralEngine: ${SPIRAL_ENGINE_ADDRESS}`);
    console.log(`   → OrganicComponentRegistry: ${ORGANIC_REGISTRY_ADDRESS}`);
    console.log();
    
    // Load contracts
    const SpiralEngineLogic = await hre.artifacts.readArtifact("SpiralEngineLogic");
    const spiralEngine = new web3.eth.Contract(SpiralEngineLogic.abi, SPIRAL_ENGINE_ADDRESS);
    
    const OrganicComponentRegistryLogic = await hre.artifacts.readArtifact("OrganicComponentRegistryLogic");
    const registry = new web3.eth.Contract(OrganicComponentRegistryLogic.abi, ORGANIC_REGISTRY_ADDRESS);
    
    // Check SELLER_ROLE
    const SELLER_ROLE = web3.utils.keccak256("SELLER_ROLE");
    const hasSellerRole = await spiralEngine.methods.hasRole(SELLER_ROLE, SELLER_ADDRESS).call();
    console.log(`✅ SELLER_ROLE: ${hasSellerRole}`);
    
    // Check activation
    const usedInvite = await spiralEngine.methods.usedInviteByUser(SELLER_ADDRESS).call();
    const isActivated = usedInvite > 0;
    console.log(`✅ Активирован (usedInviteByUser > 0): ${isActivated} (invite tokenId: ${usedInvite})`);
    
    // Check SpiralEngine in registry
    const registrySpiralEngine = await registry.methods.spiralEngine().call();
    console.log(`✅ SpiralEngine в Registry: ${registrySpiralEngine}`);
    console.log(`   → Совпадает: ${registrySpiralEngine.toLowerCase() === SPIRAL_ENGINE_ADDRESS.toLowerCase()}`);
    
    // Check component count
    const componentCount = await registry.methods.totalComponents().call();
    console.log(`✅ Всего компонентов в Registry: ${componentCount}`);
    
    // Try to call createComponent directly with try/catch
    console.log();
    console.log("🧪 Тестовый вызов createComponent...");
    try {
        await registry.methods.createComponent("test_component", "testCID123").call({
            from: SELLER_ADDRESS
        });
        console.log("✅ Тест прошел - вызов должен работать!");
    } catch (error) {
        console.log("❌ Тест не прошел:");
        console.log(`   → Ошибка: ${error.message}`);
        if (error.message.includes("revert")) {
            const match = error.message.match(/reverted with reason string '([^']+)'/);
            if (match) {
                console.log(`   → Причина revert: ${match[1]}`);
            }
        }
    }
}

main().catch(console.error);
