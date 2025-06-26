npx hardhat node &
// TODO: Прописать в /env ключи DEPLOYER_PRIVATE_KEY и SELLER_PRIVATE_KEY если не localhost
npx hardhat run scripts/deploy.js --network localhost &
python3 -m http.server 3000 &
ssh -R 80:localhost:3000 localhost.run &
// TODO: получить из туннеля URL (по формату https://27790b79e65d36.lhr.life, он выводится в логах) и подставить его в bot/.env в переменную WALLET_APP_URL
// TODO: прописать в bot/.env переменные AMANITA_REGISTRY_CONTRACT_ADDRESS и INVITE_NFT_CONTRACT_ADDRESS
PYTHONPATH=. python3 bot/main.py -v