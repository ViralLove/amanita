const { ethers } = require('hardhat');

async function fixRegistry() {
  console.log('=== Исправление регистрации контрактов в реестре ===');
  
  const registryAddress = '0xfC0C512d45FfE8f1F4B9C33aE9f6cCabB05f44C0';
  const contracts = {
    'SpiralEngine': '0x65bDbde2EAb6C4685B741c13dd5691f0426315Cb',
    'ProductRegistry': '0xB38B9F22fc8E6c78c3FCCaaDa63B8e5e03869B70',
    'SoulboundCore': '0x754D7e1B974C3142548E8CBDBbD28d26dcd7C73F',
    'SoulMetadata': '0x2f762d3a14Ce91780978c90EC92C0564B12cf1Ab',
    'SoulRecovery': '0xA8969ddeCD284af3711d8b8B980d6F215273FF57',
    'SoulIntegration': '0xb972Bf037367C7A2814996E20D7a1c8e2174b306',
    'SoulIdentity': '0xe04fA2829db764b091681dF1Dfe62c1daB60C3a4'
  };
  
  try {
    const registry = await ethers.getContractAt('AmanitaRegistry', registryAddress);
    const [deployer] = await ethers.getSigners();
    
    console.log(`Registry Address: ${registryAddress}`);
    console.log(`Deployer: ${deployer.address}`);
    
    // Проверяем текущее состояние
    console.log('\n🔍 Текущее состояние реестра:');
    for (const [name, expectedAddress] of Object.entries(contracts)) {
      const currentAddress = await registry.getAddress(name);
      console.log(`${name}: ${currentAddress}`);
    }
    
    // Регистрируем каждый контракт
    console.log('\n🔧 Регистрируем контракты...');
    for (const [name, address] of Object.entries(contracts)) {
      try {
        console.log(`\n📝 Регистрируем ${name} (${address})...`);
        
        const tx = await registry.setAddress(name, address);
        console.log(`  ⏳ Транзакция отправлена: ${tx.hash}`);
        
        const receipt = await tx.wait();
        console.log(`  ✅ Транзакция подтверждена в блоке: ${receipt.blockNumber}`);
        console.log(`  💸 Потрачено газа: ${receipt.gasUsed.toString()}`);
        
        // Проверяем результат
        const registeredAddress = await registry.getAddress(name);
        const success = registeredAddress.toLowerCase() === address.toLowerCase();
        console.log(`  📋 Результат: ${success ? '✅ Успешно' : '❌ Ошибка'}`);
        console.log(`     Зарегистрировано: ${registeredAddress}`);
        console.log(`     Ожидалось:        ${address}`);
        
      } catch (error) {
        console.log(`  ❌ Ошибка регистрации ${name}: ${error.message}`);
      }
    }
    
    // Финальная проверка
    console.log('\n🎯 Финальная проверка:');
    for (const [name, expectedAddress] of Object.entries(contracts)) {
      const registeredAddress = await registry.getAddress(name);
      const match = registeredAddress.toLowerCase() === expectedAddress.toLowerCase();
      console.log(`${name}: ${match ? '✅' : '❌'} ${registeredAddress}`);
    }
    
  } catch (error) {
    console.error('❌ Критическая ошибка:', error.message);
  }
}

fixRegistry();
