<?php
declare(strict_types=1);

namespace Amanita\Tests\Unit;

use PHPUnit\Framework\TestCase as BaseTestCase;
use WP_Mock;

/**
 * Базовый класс для всех unit-тестов плагина.
 */
abstract class TestCase extends BaseTestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        WP_Mock::setUp();
    }
    
    protected function tearDown(): void
    {
        WP_Mock::tearDown();
        parent::tearDown();
    }
    
    /**
     * Вспомогательная ассерция, имитирующая «WP true».
     */
    protected function assertWpTrue(mixed $condition, string $message = ''): void
    {
        $this->assertTrue((bool) $condition, $message);
    }
} 