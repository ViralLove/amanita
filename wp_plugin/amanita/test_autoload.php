<?php
// Тест автозагрузки для плагина Amanita

// Подключаем autoload
if ( file_exists( __DIR__ . '/vendor/autoload.php' ) ) {
    require_once __DIR__ . '/vendor/autoload.php';
    echo "Autoload подключен успешно\n";
} else {
    echo "ОШИБКА: autoload.php не найден\n";
    exit(1);
}

// Проверяем загрузку классов
$classes_to_test = [
    'Amanita\Uninstaller',
    'Amanita\Logger',
    'Amanita\SyncProduct',
    'Amanita\SyncOrder',
    'Amanita\HttpClient',
    'Amanita\Admin\MetaBoxes',
    'Amanita\Admin\SettingsPage'
];

foreach ($classes_to_test as $class) {
    if (class_exists($class)) {
        echo "✓ Класс {$class} загружен успешно\n";
    } else {
        echo "✗ ОШИБКА: Класс {$class} НЕ загружен\n";
    }
}

// Проверяем методы активации
if (class_exists('Amanita\Uninstaller')) {
    if (method_exists('Amanita\Uninstaller', 'on_activation')) {
        echo "✓ Метод on_activation найден\n";
    } else {
        echo "✗ ОШИБКА: Метод on_activation НЕ найден\n";
    }
    
    if (method_exists('Amanita\Uninstaller', 'on_deactivation')) {
        echo "✓ Метод on_deactivation найден\n";
    } else {
        echo "✗ ОШИБКА: Метод on_deactivation НЕ найден\n";
    }
    
    if (method_exists('Amanita\Uninstaller', 'cleanup')) {
        echo "✓ Метод cleanup найден\n";
    } else {
        echo "✗ ОШИБКА: Метод cleanup НЕ найден\n";
    }
}

echo "\nТест завершен.\n"; 