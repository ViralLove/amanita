<?php
/*
Plugin Name: Amanita Connector
Plugin URI: https://github.com/amanita/connector
Description: Интеграция WooCommerce с блокчейн экосистемой AMANITA через Python микросервис. Синхронизация товаров и заказов, управление инвайтами, аналитика.
Text Domain: amanita
Domain Path: /languages
Version: 0.1.0
Requires at least: 5.0
Tested up to: 6.5
WC requires at least: 3.0
WC tested up to: 7.0
Requires PHP: 7.4
Author: Amanita Team
Author URI: https://amanita.eco
License: GPL v3
License URI: https://www.gnu.org/licenses/gpl-3.0.html
Network: false
*/

// Защита от прямого доступа
if (!defined('ABSPATH')) {
    exit;
}

// Определение констант плагина
define('AMANITA_VERSION', '0.1.0');
define('AMANITA_PLUGIN_FILE', __FILE__);
define('AMANITA_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('AMANITA_PLUGIN_URL', plugin_dir_url(__FILE__));
define('AMANITA_PLUGIN_BASENAME', plugin_basename(__FILE__));

// Явное подключение критически важных классов для хуков активации/деактивации/удаления
// Это гарантирует их доступность независимо от Composer autoload
require_once AMANITA_PLUGIN_DIR . 'includes/Uninstaller.php';
require_once AMANITA_PLUGIN_DIR . 'includes/Logger.php';

// Хуки активации/деактивации/удаления - регистрируем после подключения классов
register_activation_hook(AMANITA_PLUGIN_FILE, ['Amanita\Uninstaller', 'on_activation']);
register_deactivation_hook(AMANITA_PLUGIN_FILE, ['Amanita\Uninstaller', 'on_deactivation']);
register_uninstall_hook(AMANITA_PLUGIN_FILE, ['Amanita\Uninstaller', 'cleanup']);

// Автозагрузка через Composer для основной логики (опционально)
if (file_exists(AMANITA_PLUGIN_DIR . 'vendor/autoload.php')) {
    require_once AMANITA_PLUGIN_DIR . 'vendor/autoload.php';
}

/**
 * Основной класс плагина Amanita
 */
class Amanita_Plugin {
    
    /**
     * Единственный экземпляр класса
     */
    private static $instance = null;
    
    /**
     * Получение единственного экземпляра (Singleton)
     */
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * Конструктор
     */
    private function __construct() {
        $this->init_hooks();
    }
    
    /**
     * Инициализация хуков
     */
    private function init_hooks() {
        // Проверка зависимостей и инициализация
        add_action('plugins_loaded', [$this, 'init_plugin']);
        
        // Локализация
        add_action('init', [$this, 'load_textdomain']);
        
        // Админские хуки
        if (is_admin()) {
            add_action('admin_init', [$this, 'admin_init']);
            add_action('admin_enqueue_scripts', [$this, 'admin_scripts']);
        }
        
        // WooCommerce хуки
        add_action('woocommerce_init', [$this, 'woocommerce_init']);
        
        // AJAX обработчики
        add_action('wp_ajax_amanita_test_connection', [$this, 'ajax_test_connection']);
        add_action('wp_ajax_amanita_sync_product', [$this, 'ajax_sync_product']);
        add_action('wp_ajax_amanita_get_product_status', [$this, 'ajax_get_product_status']);
    }
    
    /**
     * Инициализация плагина
     */
    public function init_plugin() {
// Проверка наличия WooCommerce
        if (!class_exists('WooCommerce')) {
            add_action('admin_notices', [$this, 'woocommerce_missing_notice']);
            return;
        }
        
        // Проверка версии PHP
        if (version_compare(PHP_VERSION, '7.4', '<')) {
            add_action('admin_notices', [$this, 'php_version_notice']);
        return;
    }
    
        // Инициализация компонентов
        $this->init_components();
        
        // Логирование запуска плагина
        \Amanita\Logger::info('Amanita plugin initialized', [
            'version' => AMANITA_VERSION,
            'php_version' => PHP_VERSION,
            'wp_version' => get_bloginfo('version'),
            'wc_version' => WC()->version ?? 'unknown'
        ]);
    }
    
    /**
     * Инициализация компонентов плагина
     */
    private function init_components() {
        // Админские компоненты
        if (is_admin()) {
    new \Amanita\Admin\MetaBoxes();
    new \Amanita\Admin\SettingsPage();
        }
    
        // Обработчики синхронизации
        add_action('admin_post_amanita_sync_product', [new \Amanita\SyncProduct(), 'handle_sync_request']);
        add_action('admin_post_amanita_sync_order', [new \Amanita\SyncOrder(), 'handle_sync_request']);

        // WooCommerce хуки для автоматической синхронизации
        add_action('woocommerce_new_product', [$this, 'auto_sync_product']);
        add_action('woocommerce_update_product', [$this, 'auto_sync_product']);
        add_action('woocommerce_new_order', [$this, 'auto_sync_order']);
        add_action('woocommerce_order_status_changed', [$this, 'auto_sync_order_status']);
    }
    
    /**
     * Инициализация WooCommerce
     */
    public function woocommerce_init() {
        // WooCommerce специфичная инициализация
        if (class_exists('WooCommerce')) {
            \Amanita\Logger::debug('WooCommerce integration initialized');
        }
    }
    
    /**
     * Инициализация админки
     */
    public function admin_init() {
        // Админская инициализация
    }
    
    /**
     * Подключение админских скриптов и стилей
     */
    public function admin_scripts($hook) {
        // Подключаем только на страницах плагина
        if (strpos($hook, 'amanita') !== false || strpos($hook, 'woocommerce') !== false) {
            wp_enqueue_script(
                'amanita-admin',
                AMANITA_PLUGIN_URL . 'assets/js/admin.js',
                ['jquery'],
                AMANITA_VERSION,
                true
            );
            
            wp_enqueue_style(
                'amanita-admin',
                AMANITA_PLUGIN_URL . 'assets/css/admin.css',
                [],
                AMANITA_VERSION
            );
            
            // Локализация для JavaScript
            wp_localize_script('amanita-admin', 'amanita_ajax', [
                'ajax_url' => admin_url('admin-ajax.php'),
                'nonce' => wp_create_nonce('amanita_nonce'),
                'strings' => [
                    'testing_connection' => __('Testing connection...', 'amanita'),
                    'connection_success' => __('Connection successful!', 'amanita'),
                    'connection_error' => __('Connection failed!', 'amanita'),
                    'syncing' => __('Synchronizing...', 'amanita'),
                    'sync_success' => __('Synchronization successful!', 'amanita'),
                    'sync_error' => __('Synchronization failed!', 'amanita'),
                ]
            ]);
        }
    }
    
    /**
     * Загрузка локализации
     */
    public function load_textdomain() {
        load_plugin_textdomain(
            'amanita',
            false,
            dirname(AMANITA_PLUGIN_BASENAME) . '/languages'
        );
    }
    
    /**
     * Автоматическая синхронизация продукта
     */
    public function auto_sync_product($product_id) {
        if (!$this->is_auto_sync_enabled()) {
            return;
        }
        
        // Добавляем задачу в очередь Action Scheduler
        if (class_exists('ActionScheduler')) {
            as_enqueue_async_action(
                'amanita_auto_sync_product',
                [$product_id],
                'amanita-sync'
            );
        }
    }
    
    /**
     * Автоматическая синхронизация заказа
     */
    public function auto_sync_order($order_id) {
        if (!$this->is_auto_sync_enabled()) {
            return;
        }
        
        // Добавляем задачу в очередь Action Scheduler
        if (class_exists('ActionScheduler')) {
            as_enqueue_async_action(
                'amanita_auto_sync_order',
                [$order_id],
                'amanita-sync'
            );
        }
    }
    
    /**
     * Автоматическая синхронизация статуса заказа
     */
    public function auto_sync_order_status($order_id, $old_status, $new_status) {
        if (!$this->is_auto_sync_enabled()) {
            return;
        }
        
        // Добавляем задачу в очередь Action Scheduler
        if (class_exists('ActionScheduler')) {
            as_enqueue_async_action(
                'amanita_auto_sync_order_status',
                [$order_id, $old_status, $new_status],
                'amanita-sync'
            );
        }
    }
    
    /**
     * AJAX: Тестирование соединения
     */
    public function ajax_test_connection() {
        // Проверка nonce
        if (!wp_verify_nonce($_POST['nonce'], 'amanita_nonce')) {
            wp_die('Security check failed');
        }
        
        // Проверка прав
        if (!current_user_can('manage_woocommerce')) {
            wp_die('Insufficient permissions');
        }
        
        $http_client = new \Amanita\HttpClient();
        $result = $http_client->health_check();
        
        wp_send_json($result);
    }
    
    /**
     * AJAX: Синхронизация продукта
     */
    public function ajax_sync_product() {
        // Проверка nonce
        if (!wp_verify_nonce($_POST['nonce'], 'amanita_nonce')) {
            wp_die('Security check failed');
        }
        
        // Проверка прав
        if (!current_user_can('manage_woocommerce')) {
            wp_die('Insufficient permissions');
        }
        
        $product_id = intval($_POST['product_id']);
        $sync_product = new \Amanita\SyncProduct();
        $result = $sync_product->sync_product($product_id);
        
        wp_send_json($result);
    }
    
    /**
     * AJAX: Получение статуса продукта
     */
    public function ajax_get_product_status() {
        // Проверка nonce
        if (!wp_verify_nonce($_POST['nonce'], 'amanita_nonce')) {
            wp_die('Security check failed');
        }
        
        // Проверка прав
        if (!current_user_can('manage_woocommerce')) {
            wp_die('Insufficient permissions');
        }
        
        $product_id = intval($_POST['product_id']);
        $status = get_post_meta($product_id, '_amanita_sync_status', true);
        $last_sync = get_post_meta($product_id, '_amanita_last_sync', true);
        $error_message = get_post_meta($product_id, '_amanita_sync_error', true);
        
        wp_send_json([
            'success' => true,
            'status' => $status,
            'last_sync' => $last_sync,
            'error_message' => $error_message
        ]);
    }
    
    /**
     * Проверка включения автоматической синхронизации
     */
    private function is_auto_sync_enabled() {
        return get_option('amanita_auto_sync_enabled', true);
    }
    
    /**
     * Уведомление об отсутствии WooCommerce
     */
    public function woocommerce_missing_notice() {
        echo '<div class="error"><p>';
        echo esc_html__('Amanita Connector требует установленный и активированный WooCommerce.', 'amanita');
        echo '</p></div>';
    }
    
    /**
     * Уведомление о несовместимой версии PHP
     */
    public function php_version_notice() {
        echo '<div class="error"><p>';
        echo esc_html__('Amanita Connector требует PHP версии 7.4 или выше.', 'amanita');
        echo '</p></div>';
    }
}

// Инициализация плагина
Amanita_Plugin::get_instance();
