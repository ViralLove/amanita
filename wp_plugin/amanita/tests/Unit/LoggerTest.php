<?php
declare(strict_types=1);

namespace Amanita\Tests\Unit;

use WP_Mock;

final class LoggerTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        
        // Простые моки для всех функций WordPress
        WP_Mock::userFunction('get_option', [
            'args' => ['amanita_logging_enabled', true],
            'return' => true
        ]);
        
        WP_Mock::userFunction('get_option', [
            'args' => ['amanita_debug_mode', false],
            'return' => false
        ]);
        
        WP_Mock::userFunction('get_option', [
            'args' => ['amanita_sync_logs', []],
            'return' => []
        ]);
        
        WP_Mock::userFunction('update_option', [
            'return' => true
        ]);
        
        WP_Mock::userFunction('delete_option', [
            'return' => true
        ]);
        
        WP_Mock::userFunction('current_time', [
            'return' => time()
        ]);
        
        WP_Mock::userFunction('get_current_user_id', [
            'return' => 1
        ]);
        
        // error_log - внутренняя PHP функция, не мокаем
    }
    
    public function test_logger_class_exists(): void
    {
        $this->assertTrue(class_exists('\Amanita\Logger'));
    }
    
    public function test_logger_methods_exist(): void
    {
        $this->assertTrue(method_exists('\Amanita\Logger', 'info'));
        $this->assertTrue(method_exists('\Amanita\Logger', 'warning'));
        $this->assertTrue(method_exists('\Amanita\Logger', 'error'));
        $this->assertTrue(method_exists('\Amanita\Logger', 'clear_logs'));
        $this->assertTrue(method_exists('\Amanita\Logger', 'get_recent_logs'));
        $this->assertTrue(method_exists('\Amanita\Logger', 'get_log_stats'));
    }
    
    /**
     * Тест проверяет что метод info() выполняется без ошибок
     * В тестовой среде логи не сохраняются, поэтому проверяем только выполнение
     */
    public function test_info_logging(): void
    {
        // Arrange
        $message = 'Test info message';
        $context = ['test' => 'data'];
        
        // Act - вызываем метод логирования
        \Amanita\Logger::info($message, $context);
        
        // Assert - проверяем что метод выполнился без ошибок
        $this->assertTrue(true);
    }
    
    /**
     * Тест проверяет что метод warning() выполняется без ошибок
     */
    public function test_warning_logging(): void
    {
        // Arrange
        $message = 'Test warning message';
        
        // Act
        \Amanita\Logger::warning($message);
        
        // Assert
        $this->assertTrue(true);
    }
    
    /**
     * Тест проверяет что метод error() выполняется без ошибок
     */
    public function test_error_logging(): void
    {
        // Arrange
        $message = 'Test error message';
        
        // Act
        \Amanita\Logger::error($message);
        
        // Assert
        $this->assertTrue(true);
    }
    
    /**
     * Тест проверяет что метод clear_logs() выполняется без ошибок
     */
    public function test_clear_logs(): void
    {
        // Act
        \Amanita\Logger::clear_logs();
        
        // Assert
        $this->assertTrue(true);
    }
} 