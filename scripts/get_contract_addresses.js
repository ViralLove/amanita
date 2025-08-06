const fs = require('fs');
const path = require('path');

async function main() {
    try {
        // Читаем deploy.json файл
        const deployPath = path.join(__dirname, '..', 'deploy.json');
        
        if (!fs.existsSync(deployPath)) {
            console.error('deploy.json не найден. Сначала выполните деплой контрактов.');
            return;
        }
        
        const deployData = JSON.parse(fs.readFileSync(deployPath, 'utf8'));
        
        // Выводим адреса в формате для .env файла
        if (deployData.amanitaRegistry) {
            console.log(`AMANITA_REGISTRY=${deployData.amanitaRegistry}`);
        }
        
        if (deployData.inviteNFT) {
            console.log(`INVITE_NFT=${deployData.inviteNFT}`);
        }
        
        if (deployData.productRegistry) {
            console.log(`PRODUCT_REGISTRY=${deployData.productRegistry}`);
        }
        
    } catch (error) {
        console.error('Ошибка при получении адресов контрактов:', error);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    }); 