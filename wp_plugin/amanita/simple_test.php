<?php
echo "Начинаем тест...\n";

// Подключаем файлы
echo "Подключаем Uninstaller.php...\n";
require_once __DIR__ . '/includes/Uninstaller.php';
echo "Uninstaller.php подключен\n";

echo "Подключаем Logger.php...\n";
require_once __DIR__ . '/includes/Logger.php';
echo "Logger.php подключен\n";

// Проверяем классы
echo "Проверяем классы...\n";
if (class_exists('Amanita\Uninstaller')) {
    echo "✓ Amanita\\Uninstaller найден\n";
} else {
    echo "✗ Amanita\\Uninstaller НЕ найден\n";
}

if (class_exists('Amanita\Logger')) {
    echo "✓ Amanita\\Logger найден\n";
} else {
    echo "✗ Amanita\\Logger НЕ найден\n";
}

echo "Тест завершен\n"; 