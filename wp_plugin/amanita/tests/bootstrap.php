<?php
declare(strict_types=1);

/**
 * Bootstrap file for Amanita plugin tests
 * 
 * Все моки WordPress функций должны быть определены в тестах через WP_Mock::userFunction()
 * Не создавайте самописные заглушки здесь - используйте стандартные моки WP_Mock
 */

require_once __DIR__ . '/../vendor/autoload.php';

// Определяем WP_Error для тестов (стандартный WordPress класс)
if (!class_exists('WP_Error')) {
    class WP_Error {
        private $code;
        private $message;
        
        public function __construct($code, $message) {
            $this->code = $code;
            $this->message = $message;
        }
        
        public function get_error_message() {
            return $this->message;
        }
    }
}

// Инициализируем WP-Mock для мокирования WordPress функций
WP_Mock::bootstrap();

// Загружаем файлы плагина для тестирования
require_once __DIR__ . '/../includes/Logger.php';
require_once __DIR__ . '/../includes/SyncProduct.php'; 