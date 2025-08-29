#!/bin/bash

# Определяем директорию скрипта и корень проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo " Директория скрипта: $SCRIPT_DIR"
echo "🏠 Корень проекта: $PROJECT_ROOT"

# Переходим в корень проекта
cd "$PROJECT_ROOT"

# Добавляем Homebrew пути в PATH для macOS
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:$PATH"

echo "🔍 Отладка PATH: $PATH"

# Загружаем .env файл из директории bot
if [ -f "bot/.env" ]; then
    export $(cat bot/.env | grep -v '^#' | xargs)
    echo "✅ .env файл загружен из bot/.env"
else
    echo "❌ .env файл не найден в bot/.env"
    echo "Создайте .env файл в директории bot/ или скопируйте его в корень проекта"
    exit 1
fi

# Проверяем что все необходимые переменные установлены
if [ -z "$AMANITA_API_URL" ] || [ -z "$AMANITA_API_KEY" ] || [ -z "$AMANITA_API_SECRET" ] || [ -z "$SELLER_ADDRESS" ]; then
    echo "❌ Ошибка: не все необходимые переменные установлены в .env"
    echo "Требуемые переменные:"
    echo "  - AMANITA_API_URL"
    echo "  - AMANITA_API_KEY" 
    echo "  - AMANITA_API_SECRET"
    echo "  - SELLER_ADDRESS"
    echo ""
    echo "📋 Текущие значения:"
    echo "  - AMANITA_API_URL: $AMANITA_API_URL"
    echo "  - AMANITA_API_KEY: $AMANITA_API_KEY"
    echo "  - AMANITA_API_SECRET: $AMANITA_API_SECRET"
    echo "  - SELLER_ADDRESS: $SELLER_ADDRESS"
    exit 1
fi

# Определяем пути к командам напрямую
echo "🔍 Определяем пути к командам..."

# Python3 - пробуем разные варианты
if [ -f "/opt/homebrew/bin/python3" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3"
    echo "✅ python3 найден по пути: $PYTHON_CMD"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_CMD="/usr/local/bin/python3"
    echo "✅ python3 найден по пути: $PYTHON_CMD"
elif [ -f "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
    echo "✅ python3 найден по пути: $PYTHON_CMD"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    echo "✅ python3 найден в PATH: $PYTHON_CMD"
else
    echo "❌ Ошибка: python3 не найден в системе"
    echo "Попробуйте: brew install python"
    exit 1
fi

# Curl - пробуем разные варианты
if [ -f "/opt/homebrew/bin/curl" ]; then
    CURL_CMD="/opt/homebrew/bin/curl"
    echo "✅ curl найден по пути: $CURL_CMD"
elif [ -f "/usr/local/bin/curl" ]; then
    CURL_CMD="/usr/local/bin/curl"
    echo "✅ curl найден по пути: $CURL_CMD"
elif [ -f "/usr/bin/curl" ]; then
    CURL_CMD="/usr/bin/curl"
    echo "✅ curl найден по пути: $CURL_CMD"
elif command -v curl >/dev/null 2>&1; then
    CURL_CMD="curl"
    echo "✅ curl найден в PATH: $CURL_CMD"
else
    echo "❌ Ошибка: curl не найден в системе"
    echo "Попробуйте: brew install curl"
    exit 1
fi

echo " Используем python3: $PYTHON_CMD"
echo " Используем curl: $CURL_CMD"

# Проверяем что команды действительно работают
echo "🔍 Тестируем python3: $($PYTHON_CMD --version 2>&1)"
echo "🔍 Тестируем curl: $($CURL_CMD --version 2>&1 | head -1)"

# Генерируем параметры аутентификации
echo "🔍 Генерируем timestamp..."
TIMESTAMP=$(date +%s)
echo "🔍 Генерируем nonce..."
NONCE=$($PYTHON_CMD -c "import secrets; print(secrets.token_hex(16))")
METHOD="GET"
PATH="/products/${SELLER_ADDRESS}"
BODY=""

# Создаем сообщение для подписи
MESSAGE="${METHOD}\n${PATH}\n${BODY}\n${TIMESTAMP}\n${NONCE}"

echo "🔍 Создаем HMAC подпись..."
echo "🔍 Используем секретный ключ: $AMANITA_API_SECRET"

# Создаем HMAC подпись используя Python (точно как в работающем скрипте)
SIGNATURE=$($PYTHON_CMD -c "
import hmac
import hashlib
import sys

# Параметры
method = sys.argv[1]
path = sys.argv[2]
body = sys.argv[3]
timestamp = sys.argv[4]
nonce = sys.argv[5]
secret_key = sys.argv[6]

# Создаем сообщение для подписи
message = f'{method}\\n{path}\\n{body}\\n{timestamp}\\n{nonce}'

# Создаем HMAC подпись
signature = hmac.new(
    secret_key.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(signature)
" "$METHOD" "$PATH" "$BODY" "$TIMESTAMP" "$NONCE" "$AMANITA_API_SECRET")

echo ""
echo "🚀 Параметры аутентификации готовы:"
echo "🌐 API URL: $AMANITA_API_URL"
echo "🔑 API Key: $AMANITA_API_KEY"
echo "👤 Seller Address: $SELLER_ADDRESS"
echo "⏰ Timestamp: $TIMESTAMP"
echo "🎲 Nonce: $NONCE"
echo "🔐 Signature: $SIGNATURE"
echo "📝 Message: $MESSAGE"
echo "🛣️  Path: $PATH"

echo ""
echo "🔍 Выполняем API запрос..."
echo ""

# Выполняем запрос
$CURL_CMD -X GET "${AMANITA_API_URL}/products/${SELLER_ADDRESS}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AMANITA_API_KEY" \
  -H "X-Timestamp: $TIMESTAMP" \
  -H "X-Nonce: $NONCE" \
  -H "X-Signature: $SIGNATURE" \
  -v

echo ""
echo ""
echo "📝 Для повторного использования, вот CURL команда:"
echo "curl -X GET \"${AMANITA_API_URL}/products/${SELLER_ADDRESS}\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"X-API-Key: $AMANITA_API_KEY\" \\"
echo "  -H \"X-Timestamp: $TIMESTAMP\" \\"
echo "  -H \"X-Nonce: $NONCE\" \\"
echo "  -H \"X-Signature: $SIGNATURE\" \\"
echo "  -v"