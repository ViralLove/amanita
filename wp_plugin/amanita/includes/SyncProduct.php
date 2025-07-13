<?php
declare(strict_types=1);

namespace Amanita;

/**
 * SyncProduct - класс для синхронизации продукта с Python-микросервисом
 * 
 * @package Amanita
 */

if (!defined('ABSPATH')) {
    exit;
}

class SyncProduct {
    
    /**
     * Python-микросервис URL
     */
    private $python_service_url;
    
    /**
     * HTTP клиент
     */
    private $http_client;
    
    /**
     * Конструктор
     */
    public function __construct() {
        $this->python_service_url = get_option('amanita_python_service_url', 'http://localhost:8000');
        $this->http_client = new HttpClient($this->python_service_url);
    }
    
    /**
     * Обработчик формы синхронизации продукта
     */
    public function handle_sync_request() {
        // Проверка nonce
        if (!isset($_POST['amanita_sync_product']) || !wp_verify_nonce($_POST['amanita_nonce'], 'amanita_sync_product')) {
            Logger::error('Security check failed - invalid nonce', array(
                'user_id' => get_current_user_id(),
                'action' => 'sync_request'
            ));
            wp_die('Security check failed');
        }
        
        // Проверка прав доступа
        if (!current_user_can('manage_woocommerce')) {
            Logger::error('Insufficient permissions for sync', array(
                'user_id' => get_current_user_id(),
                'action' => 'sync_request'
            ));
            wp_die('Insufficient permissions');
        }
        
        $product_id = intval($_POST['product_id']);
        
        // Rate limiting
        if (!$this->check_rate_limit()) {
            $this->redirect_with_error($product_id, 'Rate limit exceeded. Please try again later.');
            return;
        }
        
        // Выполняем синхронизацию
        $result = $this->sync_product($product_id);
        
        // Редиректим обратно
        $this->redirect_with_result($product_id, $result);
    }
    
    /**
     * Синхронизация продукта
     */
    public function sync_product($product_id) {
        // Логируем начало синхронизации
        Logger::info('Starting product sync', array(
            'product_id' => $product_id,
            'user_id' => get_current_user_id()
        ));
        
        // Обновляем статус на pending
        update_post_meta($product_id, '_amanita_sync_status', 'pending');
        update_post_meta($product_id, '_amanita_last_sync', current_time('mysql'));
        delete_post_meta($product_id, '_amanita_sync_error');
        
        try {
            // Получаем данные продукта
            $product_data = $this->prepare_product_data($product_id);
            
            if (!$product_data) {
                throw new \Exception('Failed to prepare product data');
            }
            
            // Отправляем данные в Python-микросервис
            $response = $this->http_client->post('/api/products/sync', $product_data);
            
            if (!$response['success']) {
                throw new \Exception($response['message'] ?? 'Unknown error occurred');
            }
            
            // Обрабатываем успешный ответ
            $this->handle_success_response($product_id, $response['data']);
            
            Logger::info('Product sync completed successfully', array(
                'product_id' => $product_id,
                'blockchain_id' => $response['data']['blockchain_id'] ?? null,
                'ipfs_cid' => $response['data']['ipfs_cid'] ?? null
            ));
            
            return array(
                'success' => true,
                'message' => 'Product synchronized successfully',
                'data' => $response['data']
            );
            
        } catch (\Exception $e) {
            // Обрабатываем ошибку
            $this->handle_error($product_id, $e->getMessage());
            
            Logger::error('Product sync failed', array(
                'product_id' => $product_id,
                'error' => $e->getMessage()
            ));
            
            return array(
                'success' => false,
                'message' => $e->getMessage()
            );
        }
    }
    
    /**
     * Подготовка данных продукта для отправки
     */
    private function prepare_product_data($product_id) {
        $product = wc_get_product($product_id);
        
        if (!$product) {
            return false;
        }
        
        // Основные данные продукта
        $data = array(
            'product_id' => $product_id,
            'name' => $product->get_name(),
            'description' => $product->get_description(),
            'short_description' => $product->get_short_description(),
            'sku' => $product->get_sku(),
            'price' => $product->get_price(),
            'regular_price' => $product->get_regular_price(),
            'sale_price' => $product->get_sale_price(),
            'type' => $product->get_type(),
            'status' => $product->get_status(),
            'stock_status' => $product->get_stock_status(),
            'stock_quantity' => $product->get_stock_quantity(),
            'weight' => $product->get_weight(),
            'dimensions' => array(
                'length' => $product->get_length(),
                'width' => $product->get_width(),
                'height' => $product->get_height()
            ),
            'categories' => $this->get_product_categories($product),
            'tags' => $this->get_product_tags($product),
            'attributes' => $this->get_product_attributes($product),
            'images' => $this->get_product_images($product),
            'meta_data' => $this->get_product_meta($product),
            'variations' => $this->get_product_variations($product),
            'seller_wallet' => get_option('amanita_seller_wallet_address', ''),
            'network' => get_option('amanita_network', 'localhost'),
            'timestamp' => current_time('timestamp')
        );
        
        return $data;
    }
    
    /**
     * Получение категорий продукта
     */
    private function get_product_categories($product) {
        $categories = array();
        $product_categories = get_the_terms($product->get_id(), 'product_cat');
        
        if ($product_categories && !is_wp_error($product_categories)) {
            foreach ($product_categories as $category) {
                $categories[] = array(
                    'id' => $category->term_id,
                    'name' => $category->name,
                    'slug' => $category->slug,
                    'description' => $category->description
                );
            }
        }
        
        return $categories;
    }
    
    /**
     * Получение тегов продукта
     */
    private function get_product_tags($product) {
        $tags = array();
        $product_tags = get_the_terms($product->get_id(), 'product_tag');
        
        if ($product_tags && !is_wp_error($product_tags)) {
            foreach ($product_tags as $tag) {
                $tags[] = array(
                    'id' => $tag->term_id,
                    'name' => $tag->name,
                    'slug' => $tag->slug
                );
            }
        }
        
        return $tags;
    }
    
    /**
     * Получение атрибутов продукта
     */
    private function get_product_attributes($product) {
        $attributes = array();
        $product_attributes = $product->get_attributes();
        
        foreach ($product_attributes as $attribute_name => $attribute) {
            $attribute_data = array(
                'name' => $attribute_name,
                'label' => wc_attribute_label($attribute_name),
                'visible' => $attribute->get_visible(),
                'variation' => $attribute->get_variation(),
                'options' => $attribute->get_options()
            );
            
            $attributes[] = $attribute_data;
        }
        
        return $attributes;
    }
    
    /**
     * Получение изображений продукта
     */
    private function get_product_images($product) {
        $images = array();
        
        // Основное изображение
        $main_image_id = $product->get_image_id();
        if ($main_image_id) {
            $main_image_url = wp_get_attachment_image_url($main_image_id, 'full');
            $main_image_alt = get_post_meta($main_image_id, '_wp_attachment_image_alt', true);
            
            $images['main'] = array(
                'id' => $main_image_id,
                'url' => $main_image_url,
                'alt' => $main_image_alt
            );
        }
        
        // Галерея изображений
        $gallery_image_ids = $product->get_gallery_image_ids();
        $images['gallery'] = array();
        
        foreach ($gallery_image_ids as $image_id) {
            $image_url = wp_get_attachment_image_url($image_id, 'full');
            $image_alt = get_post_meta($image_id, '_wp_attachment_image_alt', true);
            
            $images['gallery'][] = array(
                'id' => $image_id,
                'url' => $image_url,
                'alt' => $image_alt
            );
        }
        
        return $images;
    }
    
    /**
     * Получение мета-данных продукта
     */
    private function get_product_meta($product) {
        $meta_data = array();
        $product_meta = $product->get_meta_data();
        
        foreach ($product_meta as $meta) {
            $meta_data[$meta->key] = $meta->value;
        }
        
        return $meta_data;
    }
    
    /**
     * Получение вариаций продукта
     */
    private function get_product_variations($product) {
        $variations = array();
        
        if ($product->is_type('variable')) {
            $variation_ids = $product->get_children();
            
            foreach ($variation_ids as $variation_id) {
                $variation = wc_get_product($variation_id);
                
                if ($variation) {
                    $variations[] = array(
                        'id' => $variation_id,
                        'sku' => $variation->get_sku(),
                        'price' => $variation->get_price(),
                        'regular_price' => $variation->get_regular_price(),
                        'sale_price' => $variation->get_sale_price(),
                        'stock_status' => $variation->get_stock_status(),
                        'stock_quantity' => $variation->get_stock_quantity(),
                        'attributes' => $variation->get_variation_attributes(),
                        'meta_data' => $this->get_product_meta($variation)
                    );
                }
            }
        }
        
        return $variations;
    }
    
    /**
     * Обработка успешного ответа
     */
    private function handle_success_response($product_id, $response_data) {
        // Обновляем статус
        update_post_meta($product_id, '_amanita_sync_status', 'success');
        update_post_meta($product_id, '_amanita_last_sync', current_time('mysql'));
        
        // Сохраняем данные блокчейна
        if (isset($response_data['blockchain_id'])) {
            update_post_meta($product_id, '_amanita_blockchain_id', $response_data['blockchain_id']);
        }
        
        if (isset($response_data['ipfs_cid'])) {
            update_post_meta($product_id, '_amanita_ipfs_cid', $response_data['ipfs_cid']);
        }
        
        if (isset($response_data['tx_hash'])) {
            update_post_meta($product_id, '_amanita_tx_hash', $response_data['tx_hash']);
        }
        
        if (isset($response_data['is_active'])) {
            update_post_meta($product_id, '_amanita_is_active', $response_data['is_active']);
        }
        
        // Очищаем ошибку если была
        delete_post_meta($product_id, '_amanita_sync_error');
    }
    
    /**
     * Обработка ошибки
     */
    private function handle_error($product_id, $error_message) {
        // Обновляем статус
        update_post_meta($product_id, '_amanita_sync_status', 'error');
        update_post_meta($product_id, '_amanita_sync_error', $error_message);
        update_post_meta($product_id, '_amanita_last_sync', current_time('mysql'));
    }
    
    /**
     * Проверка rate limiting
     */
    private function check_rate_limit() {
        if (!get_option('amanita_rate_limit_enabled', true)) {
            return true;
        }
        
        $user_id = get_current_user_id();
        $rate_limit_key = 'amanita_sync_rate_limit_' . $user_id;
        $rate_limit_data = get_transient($rate_limit_key);
        
        if ($rate_limit_data === false) {
            // Первая попытка
            set_transient($rate_limit_key, array('count' => 1, 'first_attempt' => time()), 3600);
            return true;
        }
        
        $max_requests = get_option('amanita_rate_limit_requests', 100);
        
        if ($rate_limit_data['count'] >= $max_requests) {
            return false;
        }
        
        // Увеличиваем счетчик
        $rate_limit_data['count']++;
        set_transient($rate_limit_key, $rate_limit_data, 3600);
        
        return true;
    }
    
    /**
     * Редирект с результатом
     */
    private function redirect_with_result($product_id, $result) {
        $redirect_url = add_query_arg(array(
            'post' => $product_id,
            'action' => 'edit',
            'amanita_sync_result' => $result['success'] ? 'success' : 'error',
            'amanita_sync_message' => urlencode($result['message'])
        ), esc_url_raw(admin_url('post.php')));
        
        wp_safe_redirect($redirect_url);
        exit;
    }
    
    /**
     * Редирект с ошибкой
     */
    private function redirect_with_error($product_id, $error_message) {
        $this->redirect_with_result($product_id, array(
            'success' => false,
            'message' => $error_message
        ));
    }
}

