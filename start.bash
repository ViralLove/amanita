#!/bin/bash

echo "🚀 Запуск AMANITA экосистемы..."

# Проверка зависимостей
echo "🔍 Проверка зависимостей..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не найден. Установите Node.js для запуска Hardhat"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3 для запуска бота"
    exit 1
fi

if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok не найден. Установите ngrok для туннелирования"
    exit 1
fi

echo "✅ Все зависимости найдены"

# Инструкции по настройке
echo ""
echo "📋 ИНСТРУКЦИИ ПО НАСТРОЙКЕ:"
echo "1. Получите токен бота от @BotFather в Telegram"
echo "2. Отредактируйте bot/.env файл и замените TELEGRAM_BOT_TOKEN"
echo "3. При необходимости обновите другие API ключи"
echo "4. Убедитесь, что Supabase запущен на http://127.0.0.1:54321"
echo ""

# Запуск локального блокчейна
echo "⛓️ Запуск Hardhat node..."
npx hardhat node &
HARDHAT_PID=$!

# Ждем запуска блокчейна
sleep 3

# Проверяем, что Hardhat node запустился
if ! curl -s http://localhost:8545 > /dev/null; then
    echo "❌ Hardhat node не запустился"
    exit 1
fi
echo "✅ Hardhat node запущен и доступен"

# Деплой контрактов
echo "📜 Деплой контрактов..."
npx hardhat run scripts/deploy_full.js --network localhost &
DEPLOY_PID=$!

# Ждем деплоя
sleep 5

# Проверяем и создаем .env файл если его нет
echo "🔧 Проверка .env файла..."
if [ ! -f "bot/.env" ]; then
    echo "📝 Создание .env файла..."
    cat > bot/.env << 'EOF'
# Telegram Bot Token (замените на реальный токен)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Blockchain settings
BLOCKCHAIN_PROFILE=localhost
WEB3_PROVIDER_URI=http://localhost:8545

# Seller private key (замените на реальный ключ)
SELLER_PRIVATE_KEY=0x1234567890abcdef1234567890abcdef12345678

# Contract addresses (будут обновлены автоматически)
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
INVITE_NFT_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9

# Supabase settings
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Storage settings
STORAGE_TYPE=pinata

# ArWeave settings
ARWEAVE_PRIVATE_KEY=your_arweave_private_key_here

# Pinata settings
PINATA_API_KEY=your_pinata_api_key_here
PINATA_API_SECRET=your_pinata_api_secret_here
PINATA_JWT=your_pinata_jwt_here

# Deployer private key
DEPLOYER_PRIVATE_KEY=0x1234567890abcdef1234567890abcdef12345678
EOF
    echo "⚠️  ВНИМАНИЕ: Создан .env файл с тестовыми значениями!"
    echo "⚠️  Замените TELEGRAM_BOT_TOKEN на реальный токен от @BotFather"
    echo "⚠️  Обновите другие секретные ключи при необходимости"
else
    echo "✅ .env файл найден"
fi

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
PYTHONPATH=bot python3 -m bot.main &
BOT_PID=$!

# Ждем немного и проверяем, что бот запустился
sleep 3
if ! ps -p $BOT_PID > /dev/null; then
    echo "❌ Telegram бот не запустился"
    echo "💡 Проверьте .env файл и убедитесь, что TELEGRAM_BOT_TOKEN установлен"
    exit 1
fi
echo "✅ Telegram бот запущен"

echo "✅ Все сервисы запущены!"
echo "📊 Статус сервисов:"
echo "   - Hardhat node: PID $HARDHAT_PID"
echo "   - Webapp server: PID $WEBAPP_PID (http://localhost:3000)"
echo "   - ngrok tunnel: PID $NGROK_PID ($NGROK_URL)"
echo "   - Telegram bot: PID $BOT_PID"

echo ""
echo "🛑 Для остановки всех сервисов нажмите Ctrl+C"
echo "💡 Или используйте команду: pkill -f 'hardhat\|python3\|ngrok'"

# Функция для корректного завершения
cleanup() {
    echo ""
    echo "🛑 Остановка всех сервисов..."
    kill $HARDHAT_PID $WEBAPP_PID $NGROK_PID $BOT_PID 2>/dev/null
    echo "✅ Все сервисы остановлены"
    exit 0
}

# Обработка сигналов для корректного завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения
wait