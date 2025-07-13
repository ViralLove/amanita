<?php
// Тест доступности классов для активации плагина Amanita

echo "=== Тест доступности классов для активации ===\n";

// Подключаем критически важные классы (как в amanita.php)
require_once __DIR__ . '/includes/Uninstaller.php';
require_once __DIR__ . '/includes/Logger.php';

// Проверяем доступность классов
$critical_classes = [
    'Amanita\Uninstaller',
    'Amanita\Logger'
];

foreach ($critical_classes as $class) {
    if (class_exists($class)) {
        echo "✓ Класс {$class} доступен\n";
    } else {
        echo "✗ ОШИБКА: Класс {$class} НЕ доступен\n";
    }
}

// Проверяем методы активации
if (class_exists('Amanita\Uninstaller')) {
    $methods = ['on_activation', 'on_deactivation', 'cleanup'];
    foreach ($methods as $method) {
        if (method_exists('Amanita\Uninstaller', $method)) {
            echo "✓ Метод {$method} найден\n";
        } else {
            echo "✗ ОШИБКА: Метод {$method} НЕ найден\n";
        }
    }
}

// Проверяем, что хуки можно зарегистрировать
echo "\n=== Тест регистрации хуков ===\n";

// Симулируем регистрацию хуков (без реальной регистрации)
try {
    $uninstaller_class = 'Amanita\Uninstaller';
    $activation_method = 'on_activation';
    
    if (class_exists($uninstaller_class) && method_exists($uninstaller_class, $activation_method)) {
        echo "✓ Хуки можно зарегистрировать успешно\n";
    } else {
        echo "✗ ОШИБКА: Нельзя зарегистрировать хуки\n";
    }
} catch (Exception $e) {
    echo "✗ ОШИБКА при тестировании хуков: " . $e->getMessage() . "\n";
}

echo "\n=== Тест завершен ===\n"; 