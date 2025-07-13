<?php
declare(strict_types=1);

namespace Amanita;

/**
 * Uninstaller - класс для очистки данных плагина при удалении
 * 
 * @package Amanita
 */

if (!defined('ABSPATH') && !defined('WP_UNINSTALL_PLUGIN')) {
    exit;
}

class Uninstaller {
    
    /**
     * Активация плагина
     */
    public static function on_activation() {
        Logger::info('Plugin activated', array(
            'version' => AMANITA_VERSION ?? 'unknown',
            'php_version' => PHP_VERSION,
            'wp_version' => get_bloginfo('version')
        ));
        
        // Создаем таблицы если нужно
        self::create_tables();
        
        // Устанавливаем опции по умолчанию
        self::set_default_options();
        
        // Очищаем кэш
        self::clear_cache();
        
        Logger::info('Plugin activation completed');
    }
    
    /**
     * Деактивация плагина
     */
    public static function on_deactivation() {
        Logger::info('Plugin deactivated');
        
        // Очищаем Action Scheduler задачи
        self::clear_action_scheduler();
        
        // Очищаем кэш
        self::clear_cache();
        
        Logger::info('Plugin deactivation completed');
    }
    
    /**
     * Полная очистка при удалении плагина
     */
    public static function cleanup() {
        Logger::info('Starting plugin cleanup');
        
        // Удаляем опции
        self::delete_options();
        
        // Удаляем мета-данные продуктов
        self::delete_product_meta();
        
        // Удаляем мета-данные заказов
        self::delete_order_meta();
        
        // Удаляем логи
        self::delete_logs();
        
        // Удаляем таблицы если есть
        self::delete_tables();
        
        // Очищаем Action Scheduler
        self::clear_action_scheduler();
        
        // Очищаем кэш
        self::clear_cache();
        
        Logger::info('Plugin cleanup completed');
    }
    
    /**
     * Удаление опций
     */
    private static function delete_options() {
        $options = array(
            // Основные настройки интеграции
            'amanita_python_service_url',
            'amanita_api_key',
            'amanita_seller_wallet_address',
            'amanita_network',
            
            // Настройки IPFS
            'amanita_ipfs_provider',
            'amanita_ipfs_api_key',
            
            // Настройки синхронизации
            'amanita_auto_sync_enabled',
            'amanita_sync_products',
            'amanita_sync_orders',
            
            // Настройки логирования и отладки
            'amanita_debug_mode',
            'amanita_logging_enabled',
            'amanita_log_retention_days',
            
            // Настройки безопасности
            'amanita_rate_limit_enabled',
            'amanita_rate_limit_requests',
            'amanita_rate_limit_period',
            
            // Логи
            'amanita_sync_logs'
        );
        
        foreach ($options as $option) {
            delete_option($option);
        }
        
        // Удаляем опции из сети (для multisite)
        if (is_multisite()) {
            foreach ($options as $option) {
                delete_site_option($option);
            }
        }
    }
    
    /**
     * Удаление мета-данных продуктов
     */
    private static function delete_product_meta() {
        global $wpdb;
        
        $meta_keys = array(
            '_amanita_sync_status',
            '_amanita_sync_message',
            '_amanita_sync_error',
            '_amanita_sync_timestamp',
            '_amanita_last_sync',
            '_amanita_blockchain_id',
            '_amanita_ipfs_cid',
            '_amanita_tx_hash',
            '_amanita_is_active',
            '_amanita_blockchain_url'
        );
        
        foreach ($meta_keys as $meta_key) {
            $wpdb->delete(
                $wpdb->postmeta,
                array('meta_key' => $meta_key),
                array('%s')
            );
        }
    }
    
    /**
     * Удаление мета-данных заказов
     */
    private static function delete_order_meta() {
        global $wpdb;
        
        $meta_keys = array(
            '_amanita_sync_status',
            '_amanita_sync_message',
            '_amanita_sync_error',
            '_amanita_sync_timestamp',
            '_amanita_last_sync',
            '_amanita_blockchain_id',
            '_amanita_tx_hash',
            '_amanita_customer_wallet',
            '_amanita_invite_code',
            '_amanita_tokens_used'
        );
        
        foreach ($meta_keys as $meta_key) {
            $wpdb->delete(
                $wpdb->postmeta,
                array('meta_key' => $meta_key),
                array('%s')
            );
        }
    }
    
    /**
     * Удаление логов
     */
    private static function delete_logs() {
        delete_option('amanita_sync_logs');
        
        // Удаляем логи из сети (для multisite)
        if (is_multisite()) {
            delete_site_option('amanita_sync_logs');
        }
    }
    
    /**
     * Создание таблиц при активации
     */
    private static function create_tables() {
        global $wpdb;
        
        $charset_collate = $wpdb->get_charset_collate();
        
        // Таблица для инвайтов (если понадобится в будущем)
        $table_invites = $wpdb->prefix . 'amanita_invites';
        $sql_invites = "CREATE TABLE $table_invites (
            id bigint(20) NOT NULL AUTO_INCREMENT,
            invite_code varchar(255) NOT NULL,
            customer_id bigint(20) NOT NULL,
            seller_id bigint(20) NOT NULL,
            order_id bigint(20) DEFAULT NULL,
            status varchar(50) DEFAULT 'pending',
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            used_at datetime DEFAULT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY invite_code (invite_code),
            KEY customer_id (customer_id),
            KEY seller_id (seller_id),
            KEY status (status)
        ) $charset_collate;";
        
        // Таблица для правил выдачи инвайтов
        $table_rules = $wpdb->prefix . 'amanita_invite_rules';
        $sql_rules = "CREATE TABLE $table_rules (
            id bigint(20) NOT NULL AUTO_INCREMENT,
            rule_type varchar(50) NOT NULL,
            rule_name varchar(255) NOT NULL,
            rule_config longtext NOT NULL,
            is_active tinyint(1) DEFAULT 1,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY rule_type (rule_type),
            KEY is_active (is_active)
        ) $charset_collate;";
        
        // Таблица для истории выдачи инвайтов
        $table_history = $wpdb->prefix . 'amanita_invite_history';
        $sql_history = "CREATE TABLE $table_history (
            id bigint(20) NOT NULL AUTO_INCREMENT,
            invite_id bigint(20) NOT NULL,
            rule_id bigint(20) DEFAULT NULL,
            customer_id bigint(20) NOT NULL,
            order_id bigint(20) DEFAULT NULL,
            trigger_data longtext DEFAULT NULL,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY invite_id (invite_id),
            KEY rule_id (rule_id),
            KEY customer_id (customer_id)
        ) $charset_collate;";
        
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        
        // Создаем таблицы
        dbDelta($sql_invites);
        dbDelta($sql_rules);
        dbDelta($sql_history);
        
        Logger::info('Database tables created/updated');
    }
    
    /**
     * Удаление таблиц
     */
    private static function delete_tables() {
            global $wpdb;
            
        $tables = array(
            $wpdb->prefix . 'amanita_invites',
            $wpdb->prefix . 'amanita_invite_rules',
            $wpdb->prefix . 'amanita_invite_history'
        );
        
        foreach ($tables as $table) {
            $wpdb->query("DROP TABLE IF EXISTS $table");
        }
        
        Logger::info('Database tables deleted');
    }
    
    /**
     * Установка опций по умолчанию
     */
    private static function set_default_options() {
        $defaults = array(
            'amanita_python_service_url' => 'http://localhost:8000',
            'amanita_network' => 'localhost',
            'amanita_ipfs_provider' => 'https://ipfs.io',
            'amanita_auto_sync_enabled' => true,
            'amanita_sync_products' => true,
            'amanita_sync_orders' => true,
            'amanita_logging_enabled' => true,
            'amanita_log_retention_days' => 30,
            'amanita_rate_limit_enabled' => true,
            'amanita_rate_limit_requests' => 100,
            'amanita_rate_limit_period' => 3600,
            'amanita_debug_mode' => false
        );
        
        foreach ($defaults as $option => $value) {
            if (!get_option($option)) {
                add_option($option, $value);
            }
        }
        
        Logger::info('Default options set');
    }
    
    /**
     * Очистка Action Scheduler задач
     */
    private static function clear_action_scheduler() {
        if (class_exists('ActionScheduler')) {
            // Удаляем все задачи Amanita
            $tasks = array(
                'amanita_auto_sync_product',
                'amanita_auto_sync_order',
                'amanita_auto_sync_order_status',
                'amanita_batch_sync',
                'amanita_cleanup'
            );
            
            foreach ($tasks as $task) {
                as_unschedule_all_actions($task);
            }
            
            Logger::info('Action Scheduler tasks cleared');
        }
    }
    
    /**
     * Очистка кэша
     */
    private static function clear_cache() {
        // Очищаем WordPress кэш
        wp_cache_flush();
        
        // Очищаем кэш популярных плагинов
        if (function_exists('w3tc_flush_all')) {
            w3tc_flush_all(); // W3 Total Cache
        }
        
        if (function_exists('wp_cache_clear_cache')) {
            wp_cache_clear_cache(); // WP Super Cache
        }
        
        if (function_exists('rocket_clean_domain')) {
            rocket_clean_domain(); // WP Rocket
        }
        
        if (function_exists('sg_cachepress_purge_cache')) {
            sg_cachepress_purge_cache(); // SG Optimizer
        }
        
        Logger::info('Cache cleared');
    }
} 