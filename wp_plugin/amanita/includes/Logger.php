<?php
declare(strict_types=1);

namespace Amanita;

/**
 * Logger - централизованное логирование для плагина Amanita
 * 
 * @package Amanita
 */

// Защита от прямого доступа (только в WordPress)
if (!defined('ABSPATH') && !defined('PHPUNIT_COMPOSER_INSTALL')) {
    exit;
}

class Logger {
    
    /**
     * Уровни логирования
     */
    const LEVEL_INFO = 'INFO';
    const LEVEL_WARNING = 'WARNING';
    const LEVEL_ERROR = 'ERROR';
    const LEVEL_DEBUG = 'DEBUG';
    
    /**
     * Максимальное количество записей в логе
     */
    const MAX_LOG_ENTRIES = 1000;
    
    /**
     * Опция для хранения логов
     */
    const LOG_OPTION = 'amanita_sync_logs';
    
    /**
     * Логирует информационное сообщение
     */
    public static function info($message, $context = array()) {
        self::log(self::LEVEL_INFO, $message, $context);
    }
    
    /**
     * Логирует предупреждение
     */
    public static function warning($message, $context = array()) {
        self::log(self::LEVEL_WARNING, $message, $context);
    }
    
    /**
     * Логирует ошибку
     */
    public static function error($message, $context = array()) {
        self::log(self::LEVEL_ERROR, $message, $context);
    }
    
    /**
     * Логирует отладочную информацию
     */
    public static function debug($message, $context = array()) {
        if (self::is_debug_enabled()) {
            self::log(self::LEVEL_DEBUG, $message, $context);
        }
    }
    
    /**
     * Основной метод логирования
     */
    private static function log($level, $message, $context = array()) {
        // Проверяем, включено ли логирование
        if (!self::is_logging_enabled()) {
            return;
        }
        
        $log_entry = array(
            'timestamp' => current_time('timestamp'),
            'level' => $level,
            'message' => $message,
            'context' => $context,
            'user_id' => get_current_user_id(),
            'ip' => self::get_client_ip(),
            'user_agent' => isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '',
        );
        
        // Добавляем запись в лог
        self::add_log_entry($log_entry);
        
        // Дублируем в WordPress debug log если включен
        if (defined('WP_DEBUG_LOG') && WP_DEBUG_LOG) {
            $debug_message = sprintf(
                '[Amanita %s] %s - %s',
                $level,
                $message,
                !empty($context) ? json_encode($context) : ''
            );
            error_log($debug_message);
        }
    }
    
    /**
     * Добавляет запись в лог с ротацией
     */
    private static function add_log_entry($entry) {
        $logs = get_option(self::LOG_OPTION, array());
        
        // Добавляем новую запись
        $logs[] = $entry;
        
        // Ротация: удаляем старые записи если превышен лимит
        if (count($logs) > self::MAX_LOG_ENTRIES) {
            $logs = array_slice($logs, -self::MAX_LOG_ENTRIES);
        }
        
        update_option(self::LOG_OPTION, $logs);
    }
    
    /**
     * Получает последние записи из лога
     */
    public static function get_recent_logs($limit = 50) {
        $logs = get_option(self::LOG_OPTION, array());
        return array_slice($logs, -$limit);
    }
    
    /**
     * Получает логи для конкретного продукта
     */
    public static function get_product_logs($product_id, $limit = 20) {
        $logs = get_option(self::LOG_OPTION, array());
        $product_logs = array();
        
        foreach ($logs as $log) {
            if (isset($log['context']['product_id']) && $log['context']['product_id'] == $product_id) {
                $product_logs[] = $log;
            }
        }
        
        return array_slice($product_logs, -$limit);
    }
    
    /**
     * Очищает все логи
     */
    public static function clear_logs() {
        delete_option(self::LOG_OPTION);
    }
    
    /**
     * Получает статистику логов
     */
    public static function get_log_stats() {
        $logs = get_option(self::LOG_OPTION, array());
        $stats = array(
            'total' => count($logs),
            'info' => 0,
            'warning' => 0,
            'error' => 0,
            'debug' => 0,
        );
        
        foreach ($logs as $log) {
            $level = strtolower($log['level']);
            if (isset($stats[$level])) {
                $stats[$level]++;
            }
        }
        
        return $stats;
    }
    
    /**
     * Проверяет, включено ли логирование
     */
    private static function is_logging_enabled() {
        return get_option('amanita_logging_enabled', true);
    }
    
    /**
     * Проверяет, включен ли режим отладки
     */
    private static function is_debug_enabled() {
        return get_option('amanita_debug_mode', false);
    }
    
    /**
     * Получает IP адрес клиента
     */
    private static function get_client_ip() {
        $ip_keys = array('HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR');
        
        foreach ($ip_keys as $key) {
            if (array_key_exists($key, $_SERVER) === true) {
                foreach (explode(',', $_SERVER[$key]) as $ip) {
                    $ip = trim($ip);
                    if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) !== false) {
                        return $ip;
                    }
                }
            }
        }
        
        return isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
    }
    
    /**
     * Форматирует запись лога для отображения
     */
    public static function format_log_entry($entry) {
        $date = date('Y-m-d H:i:s', $entry['timestamp']);
        $level_class = 'amanita-log-' . strtolower($entry['level']);
        
        $context_info = '';
        if (!empty($entry['context'])) {
            $context_info = '<br><small>Context: ' . esc_html(json_encode($entry['context'])) . '</small>';
        }
        
        return sprintf(
            '<div class="amanita-log-entry %s">
                <strong>%s</strong> [%s] - %s%s
            </div>',
            esc_attr($level_class),
            esc_html($date),
            esc_html($entry['level']),
            esc_html($entry['message']),
            $context_info
        );
    }
} 