<?php
declare(strict_types=1);

namespace Amanita\Admin;

/**
 * SettingsPage - страница настроек плагина Amanita
 * 
 * @package Amanita
 */

if (!defined('ABSPATH')) {
    exit;
}

class SettingsPage {
    
    public function __construct() {
        add_action('admin_menu', array($this, 'add_settings_page'));
        add_action('admin_init', array($this, 'init_settings'));
        add_action('admin_notices', array($this, 'show_admin_notices'));
    }
    
    public function add_settings_page() {
        add_submenu_page(
            'woocommerce',
            __('Amanita Settings', 'amanita'),
            __('Amanita', 'amanita'),
            'manage_woocommerce',
            'amanita-settings',
            array($this, 'render_settings_page')
        );
    }
    
    public function init_settings() {
        register_setting('amanita_settings', 'amanita_python_service_url', array(
            'sanitize_callback' => array($this, 'sanitize_url')
        ));
        register_setting('amanita_settings', 'amanita_seller_wallet_address', array(
            'sanitize_callback' => array($this, 'sanitize_wallet_address')
        ));
        add_settings_section(
            'amanita_minimal_section',
            '',
            '__return_false',
            'amanita-settings'
        );
        add_settings_field(
            'amanita_python_service_url',
            __('Python Service URL', 'amanita'),
            array($this, 'render_url_field'),
            'amanita-settings',
            'amanita_minimal_section'
        );
        add_settings_field(
            'amanita_seller_wallet_address',
            __('Seller Wallet Address', 'amanita'),
            array($this, 'render_wallet_field'),
            'amanita-settings',
            'amanita_minimal_section'
        );
    }
    
    public function render_settings_page() {
        ?>
        <div class="wrap">
            <h1><?php echo esc_html__('Amanita Settings', 'amanita'); ?></h1>
            <form method="post" action="options.php">
                <?php
                settings_fields('amanita_settings');
                do_settings_sections('amanita-settings');
                submit_button(__('Save Settings', 'amanita'));
                ?>
            </form>
        </div>
        <?php
    }
    
    public function render_url_field() {
        $value = get_option('amanita_python_service_url', '');
        ?>
        <input type="url" 
               name="amanita_python_service_url" 
               value="<?php echo esc_attr($value); ?>" 
               class="regular-text"
               placeholder="http://localhost:8000">
        <p class="description">
            <?php echo esc_html__('The URL of your Amanita Python microservice', 'amanita'); ?>
        </p>
        <?php
    }
    
    public function render_wallet_field() {
        $value = get_option('amanita_seller_wallet_address', '');
        ?>
        <input type="text"
               name="amanita_seller_wallet_address"
               value="<?php echo esc_attr($value); ?>" 
               class="regular-text"
               placeholder="0x...">
        <p class="description">
            <?php echo esc_html__('Your public seller wallet address (optional)', 'amanita'); ?>
        </p>
        <?php
    }
    
    public function sanitize_url($value) {
        $url = esc_url_raw($value);
        if (empty($url)) {
            add_settings_error(
                'amanita_settings',
                'invalid_url',
                __('Please enter a valid URL.', 'amanita')
            );
        }
        return $url;
    }
    
    public function sanitize_wallet_address($value) {
        $address = sanitize_text_field($value);
        if (!empty($address) && !preg_match('/^0x[a-fA-F0-9]{40}$/', $address)) {
            add_settings_error(
                'amanita_settings',
                'invalid_wallet',
                __('Please enter a valid Ethereum wallet address.', 'amanita')
            );
        }
        return $address;
    }
    
    public function show_admin_notices() {
        settings_errors('amanita_settings');
    }
}
