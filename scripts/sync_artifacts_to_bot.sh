#!/bin/bash

# Скрипт синхронизации artifacts из корня проекта в bot/artifacts/
# Используется для обеспечения актуальности ABI в bot слое

set -e

# Определяем пути
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_ARTIFACTS="$PROJECT_ROOT/artifacts/contracts"
TARGET_ARTIFACTS="$PROJECT_ROOT/bot/artifacts/contracts"

echo "🔄 Синхронизация artifacts в bot/artifacts/..."
echo "   Источник: $SOURCE_ARTIFACTS"
echo "   Цель: $TARGET_ARTIFACTS"

# Проверяем, что исходная директория существует
if [ ! -d "$SOURCE_ARTIFACTS" ]; then
    echo "❌ Ошибка: Директория $SOURCE_ARTIFACTS не найдена"
    echo "   Выполните сначала: npx hardhat compile"
    exit 1
fi

# Создаем целевую директорию
mkdir -p "$TARGET_ARTIFACTS"

# Копируем все artifacts
echo "📦 Копирование artifacts..."
cp -r "$SOURCE_ARTIFACTS"/* "$TARGET_ARTIFACTS/" 2>/dev/null || {
    echo "⚠️ Предупреждение: Некоторые файлы не удалось скопировать (возможно, файлы заблокированы)"
}

# Проверяем результат
echo ""
echo "✅ Artifacts синхронизированы"
echo "   Проверка ключевых контрактов:"

# Проверяем ProductRegistryLogic (новый ABI с 6 элементами)
if [ -f "$TARGET_ARTIFACTS/ProductRegistryLogic.sol/ProductRegistryLogic.json" ]; then
    echo "   ✅ ProductRegistryLogic.json найден"
else
    echo "   ⚠️ ProductRegistryLogic.json не найден (возможно, контракт не скомпилирован)"
fi

# Проверяем другие UUPS контракты
for contract in "OrganicComponentRegistryLogic" "SpiralEngineLogic" "AmanitaInternationalLogic"; do
    if [ -f "$TARGET_ARTIFACTS/${contract}.sol/${contract}.json" ]; then
        echo "   ✅ ${contract}.json найден"
    fi
done

echo ""
echo "📊 Статистика:"
echo "   Исходных контрактов: $(find "$SOURCE_ARTIFACTS" -name "*.json" -type f | wc -l | tr -d ' ')"
echo "   Скопировано в bot/artifacts: $(find "$TARGET_ARTIFACTS" -name "*.json" -type f | wc -l | tr -d ' ')"

