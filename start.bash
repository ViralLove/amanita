#!/bin/bash

echo "🚀 Запуск AMANITA экосистемы..."

# Запуск локального блокчейна
echo "⛓️ Запуск Hardhat node..."
npx hardhat node &
HARDHAT_PID=$!

# Ждем запуска блокчейна
sleep 3

# Деплой контрактов
echo "📜 Деплой контрактов..."
npx hardhat run scripts/deploy_full.js --network localhost &
DEPLOY_PID=$!

# Ждем деплоя
sleep 5

# Запуск webapp сервера
echo "🌐 Запуск webapp сервера..."
cd webapp && python3 -m http.server 3000 &
WEBAPP_PID=$!
cd ..

# Ждем запуска webapp
sleep 2

# Запуск ngrok туннеля
echo "🔗 Запуск ngrok туннеля..."
ngrok http 3000 &
NGROK_PID=$!

# Ждем запуска ngrok
sleep 3

# Получаем URL из ngrok API
echo "📡 Получение ngrok URL..."
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
for tunnel in data['tunnels']:
    if tunnel['proto'] == 'https':
        print(tunnel['public_url'])
        break
")

if [ -z "$NGROK_URL" ]; then
    echo "❌ Не удалось получить ngrok URL"
    exit 1
fi

echo "✅ ngrok URL: $NGROK_URL"

# Обновляем .env файл с новым URL
echo "📝 Обновление bot/.env..."
sed -i.bak "s|WALLET_APP_URL=.*|WALLET_APP_URL=$NGROK_URL|" bot/.env

echo "🔧 Получение адресов контрактов..."
AMANITA_REGISTRY=$(npx hardhat run scripts/get_contract_addresses.js --network localhost 2>/dev/null | grep "AMANITA_REGISTRY" | cut -d'=' -f2)
INVITE_NFT=$(npx hardhat run scripts/get_contract_addresses.js --network localhost 2>/dev/null | grep "INVITE_NFT" | cut -d'=' -f2)

if [ ! -z "$AMANITA_REGISTRY" ]; then
    sed -i.bak "s|AMANITA_REGISTRY_CONTRACT_ADDRESS=.*|AMANITA_REGISTRY_CONTRACT_ADDRESS=$AMANITA_REGISTRY|" bot/.env
fi

if [ ! -z "$INVITE_NFT" ]; then
    sed -i.bak "s|INVITE_NFT_CONTRACT_ADDRESS=.*|INVITE_NFT_CONTRACT_ADDRESS=$INVITE_NFT|" bot/.env
fi

echo "🤖 Запуск Telegram бота..."
PYTHONPATH=. python3 bot/main.py -v &
BOT_PID=$!

echo "✅ Все сервисы запущены!"
echo "📊 Статус сервисов:"
echo "   - Hardhat node: PID $HARDHAT_PID"
echo "   - Webapp server: PID $WEBAPP_PID (http://localhost:3000)"
echo "   - ngrok tunnel: PID $NGROK_PID ($NGROK_URL)"
echo "   - Telegram bot: PID $BOT_PID"

# Функция для корректного завершения
cleanup() {
    echo "🛑 Остановка всех сервисов..."
    kill $HARDHAT_PID $WEBAPP_PID $NGROK_PID $BOT_PID 2>/dev/null
    exit 0
}

# Обработка сигналов для корректного завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения
wait