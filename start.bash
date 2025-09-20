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
echo "3. При необходимости обновите другие API ключи (Pinata, ArWeave)"
echo "4. Убедитесь, что Supabase запущен на http://127.0.0.1:54321"
echo ""
echo "🚀 ПРОЦЕСС ДЕПЛОЯ:"
echo "   - Action 1: Полный деплой экосистемы (SpiralEngine, SBT, ProductRegistry)"
echo "   - Action 777: Генерация 12 инвайтов для деплоера"
echo "   - Action 888: Полная инициализация селлера (активация + каталог + инвайты)"
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
echo "🔷 Action 1: Полный деплой экосистемы..."
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Ждем деплоя
sleep 3

echo "🔷 Action 777: Генерация инвайтов для деплоера..."
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# Ждем генерации инвайтов
sleep 2

echo "🔷 Action 888: Полная инициализация селлера..."
# Получаем первый инвайт из файла
DEPLOYER_INVITE=$(head -n 1 bot/flowers/deployer_invites_localhost.txt | tr -d '\n')
SELLER_ADDRESS=$(grep "SELLER_ADDRESS=" bot/.env | cut -d'=' -f2)

if [ -z "$DEPLOYER_INVITE" ]; then
    echo "❌ Не найден инвайт-код в bot/flowers/deployer_invites_localhost.txt"
    exit 1
fi

if [ -z "$SELLER_ADDRESS" ]; then
    echo "❌ Не найден SELLER_ADDRESS в bot/.env"
    exit 1
fi

echo "📋 Используем инвайт: $DEPLOYER_INVITE"
echo "📋 Активируем селлера: $SELLER_ADDRESS"

if DEPLOY_ACTION=888 DEPLOYER_INVITE=$DEPLOYER_INVITE SELLER_ADDRESS=$SELLER_ADDRESS npx hardhat run scripts/deploy_full.js --network localhost; then
    echo "✅ Action 888 завершен успешно!"
    echo "✅ Селлер полностью инициализирован:"
    echo "   - Активирован в SpiralEngine"
    echo "   - Назначена роль SELLER_ROLE"
    echo "   - Создан SBT токен"
    echo "   - Загружен каталог (17 продуктов)"
    echo "   - Сгенерированы 12 инвайтов для селлера"
else
    echo "❌ Ошибка при выполнении Action 888"
    echo "💡 Проверьте логи выше для диагностики"
    exit 1
fi

# Ждем инициализации селлера
sleep 3

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
ENVIRONMENT=local

# Seller private key (замените на реальный ключ)
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8

# Contract addresses (будут обновлены автоматически после деплоя)
AMANITA_REGISTRY_CONTRACT_ADDRESS=
SPIRAL_ENGINE_CONTRACT_ADDRESS=
PRODUCT_REGISTRY_CONTRACT_ADDRESS=
SOULBOUND_CORE_CONTRACT_ADDRESS=
SOUL_METADATA_CONTRACT_ADDRESS=
SOUL_RECOVERY_CONTRACT_ADDRESS=
SOUL_INTEGRATION_CONTRACT_ADDRESS=
SOUL_IDENTITY_CONTRACT_ADDRESS=

# Supabase settings
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Storage settings
STORAGE_TYPE=pinata
STORAGE_COMMUNICATION_MODE=sync

# ArWeave settings
ARWEAVE_PRIVATE_KEY=your_arweave_private_key_here

# Pinata settings
PINATA_API_KEY=your_pinata_api_key_here
PINATA_API_SECRET=your_pinata_api_secret_here
PINATA_JWT=your_pinata_jwt_here

# Deployer private key
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# API settings
AMANITA_API_KEY=ak_seller_amanita_mvp_2024
AMANITA_API_SECRET=sk_seller_secret_amanita_mvp_2024_secure_key
AMANITA_API_HMAC_SECRET_KEY=your_hmac_secret_key_here
AMANITA_API_URL=http://localhost:8000

# Logging settings
LOG_LEVEL=DEBUG
ENABLE_DEBUG=true
BLOCKCHAIN_TIMEOUT=60
BLOCKCHAIN_RETRY_ATTEMPTS=3
API_TIMEOUT=30
ENABLE_API_LOGGING=true
ENABLE_HMAC_VALIDATION=true
ENABLE_RATE_LIMITING=false
TELEGRAM_WEBHOOK_URL=
TELEGRAM_POLLING_TIMEOUT=10
ENABLE_CACHING=true
CACHE_TTL=300
ENABLE_METRICS=true
METRICS_INTERVAL=60
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

echo "🔧 Обновление адресов контрактов в .env..."
# Извлекаем адреса контрактов из последнего вывода action 888
# Читаем .env файл и обновляем адреса контрактов
if [ -f "bot/.env" ]; then
    # Обновляем адреса контрактов из последнего деплоя
    # Эти адреса должны быть выведены в консоль после action 888
    echo "📋 Адреса контрактов будут обновлены из последнего деплоя"
    echo "💡 Проверьте консоль выше для адресов контрактов"
    echo "💡 Скопируйте их в bot/.env файл если необходимо"
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
echo "🎉 AMANITA ЭКОСИСТЕМА ГОТОВА К РАБОТЕ!"
echo "📋 Что было выполнено:"
echo "   ✅ Деплой всех контрактов (SpiralEngine, SBT экосистема, ProductRegistry)"
echo "   ✅ Генерация инвайтов для деплоера"
echo "   ✅ Полная инициализация селлера"
echo "   ✅ Запуск Telegram бота"
echo "   ✅ Настройка ngrok туннеля"
echo ""
echo "🤖 Telegram бот готов принимать заказы!"
echo "🌐 Webapp доступен по адресу: $NGROK_URL"
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