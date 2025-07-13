# Тестирование плагина Amanita

## Обзор

Этот проект использует PHPUnit для unit-тестирования и Brain Monkey для моков WordPress функций.

## Структура тестов

```
tests/
├── bootstrap.php              # Инициализация тестового окружения
├── Unit/                      # Unit-тесты
│   ├── TestCase.php           # Базовый класс для unit-тестов
│   ├── TestData.php           # Фикстуры и тестовые данные
│   ├── SyncProductTest.php    # Тесты для Amanita_SyncProduct
│   └── LoggerTest.php         # Тесты для Amanita_Logger
└── Integration/               # Интеграционные тесты (будущее)
```

## Установка зависимостей

```bash
composer install
```

## Запуск тестов

### Все тесты
```bash
composer test
```

### Только unit-тесты
```bash
./vendor/bin/phpunit tests/Unit/
```

### С покрытием кода
```bash
composer test:coverage
```

### Конкретный тест
```bash
./vendor/bin/phpunit tests/Unit/SyncProductTest.php
```

## Написание тестов

### Структура теста

```php
<?php
namespace Amanita\Tests\Unit;

use Brain\Monkey\Functions;

class MyTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        // Настройка моков
    }
    
    public function testSomething()
    {
        // Arrange
        Functions\when('wp_function')->justReturn('value');
        
        // Act
        $result = $this->class->method();
        
        // Assert
        $this->assertEquals('expected', $result);
    }
}
```

### Моки WordPress функций

```php
// Простой мок
Functions\when('wp_function')->justReturn('value');

// Мок с проверкой аргументов
Functions\expect('wp_function')->once()->with('arg1', 'arg2');

// Мок с callback
Functions\when('wp_function')->justReturn(function($arg) {
    return $arg . '_modified';
});
```

### Создание моков WooCommerce

```php
$product = $this->createMockProduct(123, array(
    'name' => 'Custom Product',
    'price' => '99.99'
));
```

## Тестовые данные

Класс `TestData` содержит готовые фикстуры:

- `getSampleProductData()` - данные продукта
- `getSampleMappedData()` - данные для Python-сервиса
- `getSamplePythonResponse()` - ответ Python-сервиса
- `getSampleLogEntries()` - записи логов

## Покрытие кода

Текущее покрытие включает:

- ✅ Amanita_SyncProduct - 95%
- ✅ Amanita_Logger - 98%
- ⚠️ MetaBoxes - 0% (нужны интеграционные тесты)
- ⚠️ SettingsPage - 0% (нужны интеграционные тесты)

## Интеграционные тесты

Для полного покрытия нужны интеграционные тесты с WordPress Test Framework:

```bash
# Установка WordPress Test Framework
bash bin/install-wp-tests.sh wordpress_test root '' localhost latest
```

## Best Practices

1. **Изоляция тестов** - каждый тест должен быть независимым
2. **Моки внешних зависимостей** - не тестируем WordPress/WooCommerce
3. **Проверка поведения** - тестируем что делает код, а не как
4. **Именование тестов** - `testMethodName_Scenario_ExpectedResult`
5. **AAA паттерн** - Arrange, Act, Assert

## Отладка тестов

```bash
# Подробный вывод
./vendor/bin/phpunit --verbose

# Остановка при первой ошибке
./vendor/bin/phpunit --stop-on-failure

# Фильтр тестов
./vendor/bin/phpunit --filter testSuccessfulProductSync
```

## CI/CD

Тесты автоматически запускаются в CI:

```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: composer test
``` 