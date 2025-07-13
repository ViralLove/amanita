<?php
declare(strict_types=1);

/**
 * Unit tests for Amanita_SyncProduct class (минимальный пример для PHPUnit 11)
 * 
 * @package Amanita\Tests\Unit
 */

namespace Amanita\Tests\Unit;

use WP_Mock;

final class SyncProductTest extends TestCase
{
    private $sync_product;
    
    protected function setUp(): void
    {
        parent::setUp();
        
        // Моки для всех функций WordPress используемых в SyncProduct
        WP_Mock::userFunction('get_option', [
            'args' => ['amanita_python_service_url', 'http://localhost:8000'],
            'return' => 'http://localhost:8000'
        ]);
        
        WP_Mock::userFunction('current_time', [
            'args' => ['timestamp'],
            'return' => time()
        ]);
        
        WP_Mock::userFunction('get_site_url', [
            'return' => 'http://localhost'
        ]);
        
        WP_Mock::userFunction('get_the_terms', [
            'return' => []
        ]);
        
        // is_wp_error будет мокаться в каждом тесте отдельно
        
        WP_Mock::userFunction('wp_get_attachment_image_url', [
            'return' => 'http://localhost/image.jpg'
        ]);
        
        WP_Mock::userFunction('wc_attribute_label', [
            'return' => 'Test Attribute'
        ]);
        
        WP_Mock::userFunction('trailingslashit', [
            'return' => function($url) {
                return rtrim($url, '/') . '/';
            }
        ]);
        
        $this->sync_product = new \Amanita\SyncProduct();
    }
    

    
    public function test_sync_product_with_valid_product(): void
    {
        // Arrange
        $product_id = 123;
        $mock_product = $this->createMockProduct($product_id);
        
        // Моки WordPress функций
        WP_Mock::userFunction('wc_get_product', [
            'args' => [$product_id],
            'return' => $mock_product
        ]);
        
        WP_Mock::userFunction('is_wp_error', [
            'return' => false
        ]);
        
        WP_Mock::userFunction('wp_remote_post', [
            'return' => [
                'response' => ['code' => 200],
                'body' => json_encode(['success' => true])
            ]
        ]);
        
        WP_Mock::userFunction('wp_remote_retrieve_response_code', [
            'return' => 200
        ]);
        
        WP_Mock::userFunction('wp_remote_retrieve_body', [
            'return' => json_encode(['success' => true])
        ]);
        
        // Act
        $result = $this->sync_product->sync_product($product_id);
        
        // Assert
        $this->assertTrue($result['success']);
        $this->assertEquals('Product synchronized successfully', $result['message']);
    }
    
    public function test_sync_product_with_non_existent_product(): void
    {
        // Arrange
        $product_id = 999;
        
        WP_Mock::userFunction('wc_get_product', [
            'args' => [$product_id],
            'return' => false
        ]);
        
        // Act
        $result = $this->sync_product->sync_product($product_id);
        
        // Assert
        $this->assertFalse($result['success']);
        $this->assertEquals('Product not found', $result['message']);
    }
    
    public function test_sync_product_with_http_error(): void
    {
        // Arrange
        $product_id = 123;
        $mock_product = $this->createMockProduct($product_id);
        
        WP_Mock::userFunction('wc_get_product', [
            'args' => [$product_id],
            'return' => $mock_product
        ]);
        
        $wp_error = new \WP_Error('http_error', 'Connection failed');
        WP_Mock::userFunction('wp_remote_post', [
            'return' => $wp_error
        ]);
        
        WP_Mock::userFunction('is_wp_error', [
            'return' => true
        ]);
        
        // Act
        $result = $this->sync_product->sync_product($product_id);
        
        // Assert
        $this->assertFalse($result['success']);
        $this->assertStringContainsString('HTTP error', $result['message']);
    }
    
    private function createMockProduct($product_id = 123): object
    {
        $product = new class($product_id) {
            private $id;
            
            public function __construct($id) {
                $this->id = $id;
            }
            
            public function get_id() { return $this->id; }
            public function get_name() { return 'Test Product'; }
            public function get_description() { return 'Test Description'; }
            public function get_short_description() { return 'Test Short Description'; }
            public function get_price() { return '29.99'; }
            public function get_regular_price() { return '39.99'; }
            public function get_sale_price() { return ''; }
            public function get_status() { return 'publish'; }
            public function get_type() { return 'simple'; }
            public function get_sku() { return 'TEST-SKU-123'; }
            public function get_stock_quantity() { return 10; }
            public function get_stock_status() { return 'instock'; }
            public function get_weight() { return '1.5'; }
            public function get_length() { return '10'; }
            public function get_width() { return '5'; }
            public function get_height() { return '3'; }
            public function get_image_id() { return 456; }
            public function get_gallery_image_ids() { return [789, 101]; }
            public function get_attributes() { return []; }
            public function get_meta_data() { return []; }
        };
        
        return $product;
    }
} 