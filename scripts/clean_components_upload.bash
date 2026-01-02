#!/bin/bash

# ========================================================================
# 🧹 Скрипт очистки перед повторным запуском Action 555
# ========================================================================
# 
# Назначение:
#   Удаляет локальные файлы созданные Action 555
#   С опциональным сохранением или удалением Arweave CID
#
# Использование:
#   bash scripts/clean_components_upload.bash [--full | --keep-cids]
#
# Параметры:
#   --keep-cids  Сохранить Arweave CID (по умолчанию)
#                → Переиспользование CID при повторном деплое
#                → Экономия времени и газа
#                → Компоненты регистрируются с реальными CID
#
#   --full       Полная очистка (удалить все включая CID)
#                → Тестирование с абсолютно чистого состояния
#                → Компоненты будут с QmPlaceholder
#                → Потребуется повторная загрузка в Arweave
#
# Примеры:
#   bash scripts/clean_components_upload.bash                # default: сохранить CID
#   bash scripts/clean_components_upload.bash --keep-cids    # явно сохранить CID
#   bash scripts/clean_components_upload.bash --full         # полная очистка
#
# После очистки:
#   1. Остановить hardhat node (Ctrl+C)
#   2. Запустить заново: npx hardhat node
#   3. Передеплоить: DEPLOY_ACTION=1 node scripts/deploy_full.js 1
#   4. Рутовые инвайты: DEPLOY_ACTION=777 node scripts/deploy_full.js 777
#   5. Action 555: DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX node scripts/deploy_full.js 555
#
# ========================================================================

set -e  # Exit on error

# ========================================================================
# ПАРАМЕТРЫ
# ========================================================================

MODE="keep-cids"  # default

# Парсинг аргументов
if [ "$1" = "--full" ]; then
  MODE="full"
elif [ "$1" = "--keep-cids" ]; then
  MODE="keep-cids"
elif [ ! -z "$1" ]; then
  echo "❌ Неизвестный параметр: $1"
  echo ""
  echo "Использование:"
  echo "  bash scripts/clean_components_upload.bash [--full | --keep-cids]"
  echo ""
  echo "Параметры:"
  echo "  --keep-cids  Сохранить Arweave CID (по умолчанию)"
  echo "  --full       Полная очистка (удалить все включая CID)"
  exit 1
fi

echo ""
echo "========================================================================="
echo "🧹 ОЧИСТКА ПЕРЕД ПОВТОРНЫМ ЗАПУСКОМ ACTION 555"
echo "========================================================================="
echo ""
echo "Режим очистки: $MODE"
echo ""

# ========================================================================
# ВАЖНО: Проверка что мы НЕ удаляем критические файлы
# ========================================================================

echo "⚠️  ВАЖНО: Этот скрипт удалит локальные артефакты Action 555"
echo ""
echo "Будут удалены:"
echo "  ✓ bot/flowers/*_invites*.txt  (сгенерированные инвайты)"

if [ "$MODE" = "full" ]; then
  echo "  ✓ data/components/**/_upload_state*.json  ⚠️  ARWEAVE CID ТОЖЕ!"
  echo "  ✓ data/components/**/*_final_*.json  ⚠️  FINALIZED FILES ТОЖЕ!"
  echo ""
  echo "⚠️  РЕЖИМ --full: ВСЕ ДАННЫЕ ЗАГРУЗКИ БУДУТ УДАЛЕНЫ!"
  echo "⚠️  Потребуется ПОВТОРНАЯ загрузка в Arweave!"
else
  echo "  ✓ Временные файлы (если есть)"
fi

echo ""
echo "Будут СОХРАНЕНЫ:"
if [ "$MODE" = "keep-cids" ]; then
  echo "  ✓ data/components/**/_upload_state*.json  ← РЕАЛЬНЫЕ Arweave CID!"
  echo "  ✓ data/components/**/*_final_*.json  ← Финализированные компоненты!"
fi
echo "  ✓ data/components/**/simple_fields/  (исходные simple fields)"
echo "  ✓ data/components/**/complex_fields/  (переводы)"
echo "  ✓ data/components/**/*.json  (исходные данные компонентов)"
echo ""
echo "Blockchain state НЕ очищается (требуется restart hardhat node)!"
echo ""

if [ "$MODE" = "full" ]; then
  echo "⚠️⚠️⚠️  ВНИМАНИЕ: Режим ПОЛНОЙ очистки! ⚠️⚠️⚠️"
  echo "Arweave CID будут удалены и потребуется повторная загрузка!"
  echo ""
  read -p "Вы УВЕРЕНЫ? Введите 'DELETE' для подтверждения: " confirm
  
  if [ "$confirm" != "DELETE" ]; then
    echo "❌ Очистка отменена"
    exit 0
  fi
else
  read -p "Продолжить? (y/n): " confirm
  
  if [ "$confirm" != "y" ]; then
    echo "❌ Очистка отменена"
    exit 0
  fi
fi

echo ""
echo "========================================================================="
echo "📦 ШАГ 1: Удаление инвайтов seller"
echo "========================================================================="

# Удаляем инвайты из bot/flowers/
if [ -d "bot/flowers" ]; then
  INVITE_FILES=$(find bot/flowers -name "*_invites*.txt" 2>/dev/null | wc -l | tr -d ' ')
  
  if [ "$INVITE_FILES" -gt 0 ]; then
    echo "Найдено файлов инвайтов: $INVITE_FILES"
    find bot/flowers -name "*_invites*.txt" -exec rm {} \;
    echo "✅ Удалены файлы инвайтов из bot/flowers/"
  else
    echo "ℹ️  Файлы инвайтов не найдены (уже удалены или не создавались)"
  fi
else
  echo "ℹ️  Директория bot/flowers/ не найдена"
fi

echo ""
echo "========================================================================="
echo "📦 ШАГ 2: Обработка Arweave CID state файлов"
echo "========================================================================="

if [ "$MODE" = "full" ]; then
  echo "🔥 РЕЖИМ FULL: Удаление всех state файлов с CID..."
  echo ""
  
  # Удаляем _upload_state*.json файлы (включая _upload_state.json и _upload_state_*.json)
  if [ -d "data/components" ]; then
    STATE_FILES=$(find data/components -name "_upload_state*.json" 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$STATE_FILES" -gt 0 ]; then
      echo "Найдено state файлов: $STATE_FILES"
      find data/components -name "_upload_state*.json" -exec rm {} \;
      echo "✅ Удалены все _upload_state*.json файлы"
    else
      echo "ℹ️  State файлы не найдены"
    fi
    
    # Удаляем *_final_*.json файлы
    FINAL_FILES=$(find data/components -name "*_final_*.json" 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$FINAL_FILES" -gt 0 ]; then
      echo "Найдено finalized файлов: $FINAL_FILES"
      find data/components -name "*_final_*.json" -exec rm {} \;
      echo "✅ Удалены все *_final_*.json файлы"
    else
      echo "ℹ️  Finalized файлы не найдены"
    fi
  else
    echo "⚠️  WARNING: data/components/ не найдена!"
  fi
  
  echo ""
  echo "🔥 ПОЛНАЯ ОЧИСТКА: При следующем запуске Action 555 компоненты"
  echo "   будут зарегистрированы с QmPlaceholder"
  
else
  # Режим keep-cids: проверяем сохранность
  echo "✅ РЕЖИМ KEEP-CIDS: Сохранение Arweave CID для переиспользования"
  echo ""
  
  # Проверяем что state файлы с CID сохранены
  if [ -d "data/components" ]; then
    STATE_FILES=$(find data/components -name "_upload_state*.json" 2>/dev/null | wc -l | tr -d ' ')
    echo "✅ Найдено state файлов с Arweave CID: $STATE_FILES"
    
    if [ "$STATE_FILES" -gt 0 ]; then
      echo ""
      echo "Примеры сохраненных CID (для переиспользования):"
      find data/components -name "_upload_state*.json" -type f | head -3 | while read file; do
        COMPONENT=$(basename $(dirname "$file"))
        CID=$(grep -o '"cid": "[^"]*"' "$file" | head -1 | cut -d'"' -f4)
        if [ ! -z "$CID" ]; then
          echo "  ✅ $COMPONENT: $CID"
        fi
      done
      echo ""
      echo "  → Эти CID будут переиспользованы в Action 555! ✅"
    fi
  else
    echo "⚠️  WARNING: data/components/ не найдена!"
  fi
fi

echo ""
echo "========================================================================="
echo "📦 ШАГ 3: Очистка адресов контрактов из .env"
echo "========================================================================="

# Список переменных с адресами контрактов которые нужно удалить
CONTRACT_VARS=(
  "MAGIC_REGISTRY_CONTRACT_ADDRESS"
  "SPIRAL_ENGINE_CONTRACT_ADDRESS"
  "SPIRAL_ENGINE_PROXY_ADDRESS"
  "PRODUCT_REGISTRY_CONTRACT_ADDRESS"
  "PRODUCT_REGISTRY_PROXY_ADDRESS"
  "SOUL_IDENTITY_CONTRACT_ADDRESS"
  "AMANITA_INTERNATIONAL_PROXY_ADDRESS"
  "ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS"
  "AMANITA_REGISTRY_CONTRACT_ADDRESS"
  "SOULBOUND_CORE_CONTRACT_ADDRESS"
  "SOUL_METADATA_CONTRACT_ADDRESS"
  "SOUL_RECOVERY_CONTRACT_ADDRESS"
  "SOUL_INTEGRATION_CONTRACT_ADDRESS"
  "AMANITA_INTERNATIONAL_LOGIC_ADDRESS"
  "ORGANIC_COMPONENT_REGISTRY_LOGIC_ADDRESS"
)

if [ -f ".env" ]; then
  echo "Найден .env файл"
  
  # Создаём бэкап .env
  cp .env .env.backup_before_clean
  echo "  ✅ Создан бэкап: .env.backup_before_clean"
  
  # Подсчитываем сколько адресов будет удалено
  ADDRESSES_FOUND=0
  for var in "${CONTRACT_VARS[@]}"; do
    if grep -q "^${var}=" .env 2>/dev/null; then
      ADDRESSES_FOUND=$((ADDRESSES_FOUND + 1))
    fi
  done
  
  if [ $ADDRESSES_FOUND -gt 0 ]; then
    echo "  Найдено адресов контрактов: $ADDRESSES_FOUND"
    echo ""
    
    # Удаляем каждую переменную из .env
    for var in "${CONTRACT_VARS[@]}"; do
      if grep -q "^${var}=" .env 2>/dev/null; then
        # Показываем что удаляем
        CURRENT_VALUE=$(grep "^${var}=" .env | cut -d'=' -f2)
        echo "  🗑️  Удаляем: $var=$CURRENT_VALUE"
        
        # Удаляем строку с этой переменной
        # Используем временный файл для безопасности
        grep -v "^${var}=" .env > .env.tmp && mv .env.tmp .env
      fi
    done
    
    echo ""
    echo "  ✅ Удалено $ADDRESSES_FOUND адресов контрактов из .env"
    echo "  ℹ️  При следующем деплое (Action 1) будут записаны новые адреса"
  else
    echo "  ℹ️  Адреса контрактов не найдены в .env (уже удалены или не создавались)"
  fi
else
  echo "  ℹ️  Файл .env не найден"
fi

echo ""
echo "========================================================================="
echo "✅ ОЧИСТКА ЗАВЕРШЕНА"
echo "========================================================================="
echo ""
echo "Режим: $MODE"
echo ""
echo "📋 Следующие шаги для полного сброса:"
echo ""
echo "1. Остановить hardhat node (если запущена):"
echo "   Ctrl+C в терминале с нодой"
echo ""
echo "2. Запустить hardhat node заново:"
echo "   npx hardhat node"
echo ""
echo "3. Передеплоить контракты (в новом терминале):"
echo "   DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost"
echo ""
echo "4. Создать рутовые инвайты:"
echo "   DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost"
echo "   (скопировать инвайт из вывода)"
echo ""
echo "5. Запустить Action 555:"
echo "   DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY \\"
echo "     npx hardhat run scripts/deploy_full.js --network localhost"
echo ""
echo "========================================================================="
echo ""

if [ "$MODE" = "keep-cids" ]; then
  echo "ℹ️  РЕЖИМ KEEP-CIDS:"
  echo "   ✅ Arweave CID будут переиспользованы из state файлов!"
  echo "   ✅ Нет повторной загрузки в Arweave = экономия времени и газа!"
  echo "   ✅ Компоненты зарегистрируются с РЕАЛЬНЫМИ CID"
  echo ""
  echo "Ожидается в логах Action 555:"
  echo "   → CID источник: arweave_state (переиспользование) ✅"
else
  echo "ℹ️  РЕЖИМ FULL:"
  echo "   ⚠️  Arweave CID удалены!"
  echo "   ⚠️  Компоненты зарегистрируются с QmPlaceholder"
  echo "   ⚠️  Для полной загрузки в Arweave потребуется отдельный скрипт"
  echo ""
  echo "Ожидается в логах Action 555:"
  echo "   → CID источник: placeholder (заглушка)"
fi

echo ""

