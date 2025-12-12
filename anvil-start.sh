#!/bin/zsh

STATE_DIR="./anvil"
STATE_FILE="$STATE_DIR/state.json"

# 1. Проверяем, есть ли папка anvil/
if [ ! -d "$STATE_DIR" ]; then
  echo "📁 Создаю папку $STATE_DIR ..."
  mkdir "$STATE_DIR"
fi

# 2. Проверяем валидность существующего state.json
if [ -f "$STATE_FILE" ]; then
  # Проверяем, что файл содержит обязательное поле "block"
  if ! python3 -c "import json, sys; data=json.load(open('$STATE_FILE')); sys.exit(0 if 'block' in data else 1)" 2>/dev/null; then
    echo "⚠️  Файл $STATE_FILE невалиден (отсутствует поле 'block'). Удаляю..."
    rm "$STATE_FILE"
    echo "🆕 Anvil создаст новый state.json при первом запуске."
  fi
else
  echo "🆕 Файл состояния отсутствует. Anvil создаст его при первом запуске."
fi

echo "🚀 Запуск вечной сети Anvil..."
echo "📌 Стейт: $STATE_FILE"

# 3. Бесконечный цикл автоперезапуска
while true
do
  echo "🔥 Anvil запущен. CTRL+C внутри не убивает цикл."
  
  anvil \
    --state "$STATE_FILE" \
    --state-interval 20 \
    --host 0.0.0.0

  echo "⚠️  Anvil был остановлен или упал. Перезапуск через 1 секунду..."
  sleep 1
done
