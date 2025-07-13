<?php
declare(strict_types=1);

namespace Amanita;

/**
 * Класс для синхронизации заказов WooCommerce с Python-микросервисом
 * 
 * @package Amanita
 */

class SyncOrder {
    
    /**
     * URL Python-микросервиса
     */
    private $python_service_url;
    
    /**
     * Конструктор
     */
    public function __construct() {
        $this->python_service_url = get_option('amanita_python_service_url', 'http://localhost:8000');
    }
    
    /**
     * Обработчик запроса синхронизации заказа
     */
    public function handle_sync_request() {
        // Проверяем nonce
        if (!wp_verify_nonce($_POST['amanita_sync_nonce'], 'amanita_sync_order')) {
            wp_die('Security check failed');
        }
        
        // Проверяем права пользователя
        if (!current_user_can('manage_woocommerce')) {
            wp_die('Insufficient permissions');
        }
        
        $order_id = intval($_POST['order_id']);
        
        // Логируем начало синхронизации
        Logger::info('Starting order sync', array(
            'order_id' => $order_id,
            'user_id' => get_current_user_id()
        ));
        
        // Выполняем синхронизацию
        $result = $this->sync_order($order_id);
        
        // Редиректим обратно
        $redirect_url = add_query_arg(array(
            'post' => $order_id,
            'action' => 'edit',
            'amanita_sync_result' => $result['success'] ? 'success' : 'error',
            'amanita_sync_message' => urlencode($result['message'])
        ), esc_url_raw(admin_url('post.php')));
        
        wp_safe_redirect($redirect_url);
        exit;
    }
    
    /**
     * Синхронизация заказа
     */
    public function sync_order($order_id) {
        try {
            // Получаем заказ
            $order = wc_get_order($order_id);
            if (!$order) {
                return array(
                    'success' => false,
                    'message' => 'Order not found'
                );
            }
            
            // Маппинг данных заказа
            $data = $this->map_order_data($order);
            
            // Отправка в Python-микросервис
            $response = $this->send_to_python_service($data);
            
            // Обновляем статус заказа
            $this->update_order_sync_status($order_id, $response);
            
            return $response;
            
        } catch (Exception $e) {
            Logger::error('Order sync error', array(
                'order_id' => $order_id,
                'action' => 'sync_exception',
                'error_message' => $e->getMessage(),
                'error_trace' => $e->getTraceAsString()
            ));
            return array(
                'success' => false,
                'message' => 'Sync error: ' . $e->getMessage()
            );
        }
    }
    
    /**
     * Маппинг данных заказа WooCommerce в формат Python-микросервиса
     */
    private function map_order_data($order) {
        $data = array(
            'id' => $order->get_id(),
            'number' => $order->get_order_number(),
            'status' => $order->get_status(),
            'total' => $order->get_total(),
            'currency' => $order->get_currency(),
            'customer_id' => $order->get_customer_id(),
            'billing' => array(
                'first_name' => $order->get_billing_first_name(),
                'last_name' => $order->get_billing_last_name(),
                'email' => $order->get_billing_email(),
                'phone' => $order->get_billing_phone(),
                'address_1' => $order->get_billing_address_1(),
                'address_2' => $order->get_billing_address_2(),
                'city' => $order->get_billing_city(),
                'state' => $order->get_billing_state(),
                'postcode' => $order->get_billing_postcode(),
                'country' => $order->get_billing_country()
            ),
            'shipping' => array(
                'first_name' => $order->get_shipping_first_name(),
                'last_name' => $order->get_shipping_last_name(),
                'address_1' => $order->get_shipping_address_1(),
                'address_2' => $order->get_shipping_address_2(),
                'city' => $order->get_shipping_city(),
                'state' => $order->get_shipping_state(),
                'postcode' => $order->get_shipping_postcode(),
                'country' => $order->get_shipping_country()
            ),
            'items' => $this->get_order_items($order),
            'payment_method' => $order->get_payment_method(),
            'payment_method_title' => $order->get_payment_method_title(),
            'shipping_method' => $order->get_shipping_method(),
            'date_created' => $order->get_date_created()->format('Y-m-d H:i:s'),
            'sync_timestamp' => current_time('timestamp'),
            'wordpress_site_url' => get_site_url()
        );
        
        return $data;
    }
    
    /**
     * Получение товаров заказа
     */
    private function get_order_items($order) {
        $items = array();
        
        foreach ($order->get_items() as $item) {
            $product = $item->get_product();
            $items[] = array(
                'id' => $item->get_id(),
                'product_id' => $item->get_product_id(),
                'name' => $item->get_name(),
                'quantity' => $item->get_quantity(),
                'total' => $item->get_total(),
                'subtotal' => $item->get_subtotal(),
                'sku' => $product ? $product->get_sku() : '',
                'meta_data' => $item->get_meta_data()
            );
        }
        
        return $items;
    }
    
    /**
     * Отправка данных в Python-микросервис
     */
    private function send_to_python_service($data) {
        $url = trailingslashit($this->python_service_url) . 'api/orders/sync';
        
        $response = wp_remote_post($url, array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'X-Amanita-Source' => 'wordpress',
                'X-Amanita-Version' => '1.0'
            ),
            'body' => json_encode($data),
            'timeout' => 30,
            'data_format' => 'body'
        ));
        
        if (is_wp_error($response)) {
            return array(
                'success' => false,
                'message' => 'HTTP error: ' . $response->get_error_message()
            );
        }
        
        $status_code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        
        if ($status_code >= 200 && $status_code < 300) {
            return array(
                'success' => true,
                'message' => 'Order synchronized successfully',
                'data' => json_decode($body, true)
            );
        } else {
            return array(
                'success' => false,
                'message' => 'HTTP ' . $status_code . ': ' . $body
            );
        }
    }
    
    /**
     * Обновление статуса синхронизации заказа
     */
    private function update_order_sync_status($order_id, $response) {
        $sync_status = $response['success'] ? 'synced' : 'sync_failed';
        $sync_message = $response['message'];
        $sync_timestamp = current_time('timestamp');
        
        update_post_meta($order_id, '_amanita_sync_status', $sync_status);
        update_post_meta($order_id, '_amanita_sync_message', $sync_message);
        update_post_meta($order_id, '_amanita_sync_timestamp', $sync_timestamp);
        
        if ($response['success'] && isset($response['data']['tx_hash'])) {
            update_post_meta($order_id, '_amanita_tx_hash', $response['data']['tx_hash']);
        }
    }
}
