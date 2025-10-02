1. зайти в wallet и запустить веб сервер

python3 -m http.server 3000
это запустится сам некастодиальный кошелек Amanita

2. запустить 
ngrok http 3000
для https тоннелирования чтобы приложение открылось внутри телеграм бота в webapp view
получить оттуда URL и прописать его в bot/.env в параметр WALLET_APP_URL (найти такой который не закомментированный = активный)

3. прописать в .env 
# localhost
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

либо проверить что они там уже есть

выполнить
npx hardhat node
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost
из логов взять часть с адресами 
например
MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
SPIRAL_ENGINE_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0x68B1D87F95878fE05B998F19b66F4baba5De1aed
SOULBOUND_CORE_CONTRACT_ADDRESS=0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9
SOUL_METADATA_CONTRACT_ADDRESS=0x0165878A594ca255338adfa4d48449f69242Eb8F
SOUL_RECOVERY_CONTRACT_ADDRESS=0x2279B7A0a67DB372996a5FaB50D91eAA73d2eBe6
SOUL_INTEGRATION_CONTRACT_ADDRESS=0x610178dA211FEF7D417bC0e6FeD39F05609AD788
SOUL_IDENTITY_CONTRACT_ADDRESS=0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0

и заменить либо добавить
1. в .env внутри рута проекта
2. внутри директории bot
(важно! В оба!)

4. выполнить дальше 
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost
проверить что заминчены инвайты
открыть их в 
bot/flowers/deployer_invites_localhost.txt
взять первый в котором есть цифра 8, если нет то 7 или 5

пусть это будет <deployerInvite>

5. выполнить 

DEPLOY_ACTION=888 DEPLOYER_INVITE=<deployerInvite> npx hardhat run scripts/deploy_full.js --network localhost

DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-6SBK-I9EW npx hardhat run scripts/deploy_full.js --network localhost

DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-4X8O-185Q npx hardhat run scripts/deploy_full.js --network localhost

открыть файл bot/flowers/0x70997970C51812dc3A010C7d01b50e0d17dc79C8_invites.txt и проверить там инвайты, вывести оттуда их все удобным списком

6. запустить веб приложение для телеграм бота
python3 bot/main.py 