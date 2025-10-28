const hre = require("hardhat");
const { Web3 } = require("web3");
const fs = require('fs');
const path = require('path');

async function main() {
    const web3 = new Web3("http://localhost:8545");
    const network = 'localhost';
    
    const ORGANIC_REGISTRY_ADDRESS = process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS;
    const componentsDir = path.join(__dirname, 'scripts', 'organic_components');
    
    const OrganicComponentRegistryLogic = await hre.artifacts.readArtifact("OrganicComponentRegistryLogic");
    const registry = new web3.eth.Contract(OrganicComponentRegistryLogic.abi, ORGANIC_REGISTRY_ADDRESS);
    
    console.log(`🔄 Синхронизация state файлов с blockchain...\n`);
    
    const events = await registry.getPastEvents('ComponentCreated', {
        fromBlock: 0,
        toBlock: 'latest'
    });
    
    console.log(`Найдено ${events.length} зарегистрированных компонентов\n`);
    
    let updated = 0;
    
    for (const event of events) {
        const businessId = event.returnValues.businessId;
        const componentId = event.returnValues.componentId;
        const txHash = event.transactionHash;
        const blockNumber = event.blockNumber;
        
        const componentDir = path.join(componentsDir, businessId);
        const stateFile = path.join(componentDir, `_upload_state_${network}.json`);
        
        if (!fs.existsSync(stateFile)) {
            console.log(`⚠️ ${businessId}: state файл не найден - пропускаем`);
            continue;
        }
        
        const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
        
        // Проверяем, уже ли помечен как зарегистрированный
        if (state.steps_completed.includes('component_registered')) {
            console.log(`✅ ${businessId}: уже помечен как зарегистрированный (componentId: ${componentId})`);
            continue;
        }
        
        // Обновляем state
        if (!state.steps_completed.includes('component_registered')) {
            state.steps_completed.push('component_registered');
        }
        
        state.contract_registration = {
            componentId: parseInt(componentId),
            txHash: txHash,
            blockNumber: blockNumber.toString()
        };
        
        // Сохраняем с BigInt replacer
        const replacer = (key, value) => 
            typeof value === 'bigint' ? value.toString() : value;
        fs.writeFileSync(stateFile, JSON.stringify(state, replacer, 2), 'utf8');
        
        console.log(`✅ ${businessId}: обновлен (componentId: ${componentId}, блок: ${blockNumber})`);
        updated++;
    }
    
    console.log(`\n✅ Обновлено ${updated} state файлов`);
}

main().catch(console.error);
