<?php
declare(strict_types=1);

namespace Amanita;

/**
 * HTTP клиент для работы с Python-микросервисом
 * 
 * @package Amanita
 */

class HttpClient {
    
    /**
     * Базовый URL сервиса
     */
    private $base_url;
    
    /**
     * API ключ
     */
    private $api_key;
    
    /**
     * Таймаут по умолчанию
     */
    private $timeout;
    
    /**
     * Конструктор
     */
    public function __construct($base_url = '', $api_key = '', $timeout = 30) {
        $this->base_url = $base_url ?: get_option('amanita_python_service_url', 'http://localhost:8000');
        $this->api_key = $api_key ?: get_option('amanita_api_key', '');
        $this->timeout = $timeout;
    }
    
    /**
     * POST запрос
     */
    public function post($endpoint, $data = array(), $headers = array()) {
        $url = trailingslashit($this->base_url) . ltrim($endpoint, '/');
        
        $default_headers = array(
            'Content-Type' => 'application/json',
            'X-Amanita-Source' => 'wordpress',
            'X-Amanita-Version' => '1.0'
        );
        
        if ($this->api_key) {
            $default_headers['X-Amanita-API-Key'] = $this->api_key;
        }
        
        $headers = array_merge($default_headers, $headers);
        
        $args = array(
            'headers' => $headers,
            'body' => json_encode($data),
            'timeout' => $this->timeout,
            'data_format' => 'body'
        );
        
        return $this->make_request($url, $args);
    }
    
    /**
     * GET запрос
     */
    public function get($endpoint, $params = array(), $headers = array()) {
        $url = trailingslashit($this->base_url) . ltrim($endpoint, '/');
        
        if (!empty($params)) {
            $url = add_query_arg($params, $url);
        }
        
        $default_headers = array(
            'X-Amanita-Source' => 'wordpress',
            'X-Amanita-Version' => '1.0'
        );
        
        if ($this->api_key) {
            $default_headers['X-Amanita-API-Key'] = $this->api_key;
        }
        
        $headers = array_merge($default_headers, $headers);
        
        $args = array(
            'headers' => $headers,
            'timeout' => $this->timeout
        );
        
        return $this->make_request($url, $args);
    }
    
    /**
     * Выполнение HTTP запроса с улучшенной обработкой ошибок
     */
    private function make_request($url, $args) {
        // Валидация URL с дополнительными проверками
        if (!filter_var($url, FILTER_VALIDATE_URL)) {
            return array(
                'success' => false,
                'message' => 'Invalid URL format',
                'error_code' => 'INVALID_URL'
            );
        }
        
        // Дополнительная проверка протокола
        $parsed_url = parse_url($url);
        if (!$parsed_url || !isset($parsed_url['scheme']) || !in_array($parsed_url['scheme'], ['http', 'https'])) {
            return array(
                'success' => false,
                'message' => 'Invalid URL protocol (only http/https allowed)',
                'error_code' => 'INVALID_PROTOCOL'
            );
        }
        
        // Логируем запрос
        Logger::debug('HTTP request', array(
            'url' => $url,
            'method' => isset($args['body']) ? 'POST' : 'GET',
            'timeout' => $this->timeout
        ));
        
        $response = wp_remote_request($url, $args);
        
        // Обработка WP_Error
        if (is_wp_error($response)) {
            $error_message = $response->get_error_message();
            $error_code = $response->get_error_code();
            
            Logger::error('HTTP request failed', array(
                'url' => $url,
                'error_code' => $error_code,
                'error_message' => $error_message
            ));
            
            return array(
                'success' => false,
                'message' => 'HTTP error: ' . $error_message,
                'error_code' => $error_code
            );
        }
        
        // Получаем данные ответа
        $status_code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        $headers = wp_remote_retrieve_headers($response);
        $response_message = wp_remote_retrieve_response_message($response);
        
        // Логируем ответ
        Logger::debug('HTTP response', array(
            'url' => $url,
            'status_code' => $status_code,
            'response_message' => $response_message,
            'body_length' => strlen($body)
        ));
        
        // Обработка различных статус кодов
        if ($status_code >= 200 && $status_code < 300) {
            // Успешный ответ
            $data = json_decode($body, true);
            if (json_last_error() !== JSON_ERROR_NONE) {
                Logger::warning('Invalid JSON response', array(
                    'url' => $url,
                    'status_code' => $status_code,
                    'body' => substr($body, 0, 500)
                ));
                
                return array(
                    'success' => false,
                    'message' => 'Invalid JSON response from server',
                    'error_code' => 'INVALID_JSON',
                    'status_code' => $status_code,
                    'raw_body' => $body
                );
            }
            
            return array(
                'success' => true,
                'data' => $data,
                'status_code' => $status_code,
                'headers' => $headers
            );
            
        } elseif ($status_code >= 400 && $status_code < 500) {
            // Клиентские ошибки
            Logger::warning('HTTP client error', array(
                'url' => $url,
                'status_code' => $status_code,
                'response_message' => $response_message,
                'body' => substr($body, 0, 500)
            ));
            
            return array(
                'success' => false,
                'message' => 'Client error: ' . $response_message,
                'error_code' => 'CLIENT_ERROR',
                'status_code' => $status_code,
                'body' => $body
            );
            
        } elseif ($status_code >= 500) {
            // Серверные ошибки
            Logger::error('HTTP server error', array(
                'url' => $url,
                'status_code' => $status_code,
                'response_message' => $response_message,
                'body' => substr($body, 0, 500)
            ));
            
            return array(
                'success' => false,
                'message' => 'Server error: ' . $response_message,
                'error_code' => 'SERVER_ERROR',
                'status_code' => $status_code,
                'body' => $body
            );
            
        } else {
            // Другие статус коды (редиректы и т.д.)
            Logger::warning('Unexpected HTTP status', array(
                'url' => $url,
                'status_code' => $status_code,
                'response_message' => $response_message
            ));
            
            return array(
                'success' => false,
                'message' => 'Unexpected status: ' . $status_code . ' ' . $response_message,
                'error_code' => 'UNEXPECTED_STATUS',
                'status_code' => $status_code,
                'body' => $body
            );
        }
    }
    
    /**
     * Проверка доступности сервиса
     */
    public function health_check() {
        return $this->get('health');
    }
    
    /**
     * Установка таймаута
     */
    public function setTimeout($timeout) {
        $this->timeout = $timeout;
        return $this;
    }
    
    /**
     * Установка API ключа
     */
    public function setApiKey($api_key) {
        $this->api_key = $api_key;
        return $this;
    }
    
    /**
     * Установка базового URL
     */
    public function setBaseUrl($base_url) {
        $this->base_url = $base_url;
        return $this;
    }
}
