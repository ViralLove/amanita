# Amanita WooCommerce Plugin — Infrastructure & Architecture Documentation

## Overview

Amanita — это WordPress/WooCommerce плагин для синхронизации продуктов и заказов с внешним Python-микросервисом (Web3, IPFS, blockchain). Плагин реализован с учётом современных стандартов: PSR-4, Composer autoload, строгая типизация, тестирование, безопасность, логирование, расширяемость.

---

## 1. Файловая структура

```
wp_plugin/amanita/
├── amanita.php                # Главный файл плагина (инициализация, хуки)
├── composer.json              # Composer config, autoload PSR-4
├── composer.lock
├── Uninstaller.php            # Корневой uninstall-файл (вызывает includes/Uninstaller)
├── includes/
│   ├── Logger.php             # Централизованный логгер (Amanita\Logger)
│   ├── SyncProduct.php        # Синхронизация продуктов (Amanita\SyncProduct)
│   ├── SyncOrder.php          # Синхронизация заказов (Amanita\SyncOrder)
│   ├── HttpClient.php         # HTTP-клиент для Python-сервиса (Amanita\HttpClient)
│   └── Uninstaller.php        # Класс для удаления данных (Amanita\Uninstaller)
├── admin/
│   ├── MetaBoxes.php          # Метабоксы для UI (Amanita\Admin\MetaBoxes)
│   └── SettingsPage.php       # Страница настроек (Amanita\Admin\SettingsPage)
├── tests/                     # Unit-тесты (PHPUnit, WP_Mock)
├── languages/                 # Локализации
├── assets/                    # Статические ресурсы
├── README.md, readme.txt      # Документация
```

---

## 2. Главный файл плагина (`amanita.php`)

- Подключает Composer autoload.
- Проверяет наличие WooCommerce.
- Инициализирует основные классы:
  - `Amanita\Admin\MetaBoxes`
  - `Amanita\Admin\SettingsPage`
  - `Amanita\SyncProduct` (через admin_post)
- Регистрирует хуки активации/деактивации/удаления через методы `Amanita\Uninstaller`.
- Подключает локализацию.

**Пример:**
```php
if ( file_exists( __DIR__ . '/vendor/autoload.php' ) ) {
    require_once __DIR__ . '/vendor/autoload.php';
}
new \Amanita\Admin\MetaBoxes();
new \Amanita\Admin\SettingsPage();
add_action('admin_post_amanita_sync_product', [new \Amanita\SyncProduct(), 'handle_sync_request']);
register_activation_hook( __FILE__,  [ 'Amanita\Uninstaller', 'on_activation' ] );
register_deactivation_hook( __FILE__, [ 'Amanita\Uninstaller', 'on_deactivation' ] );
register_uninstall_hook(   __FILE__,  [ 'Amanita\Uninstaller', 'cleanup' ] );
```

---

## 3. Классы и их назначение

### 3.1. `Amanita\Logger`
- Централизованное логирование всех действий плагина.
- Хранит логи в опции `amanita_sync_logs` (ротация, фильтрация по продукту).
- Поддерживает уровни: info, warning, error, debug.
- Дублирует сообщения в WP_DEBUG_LOG при необходимости.
- Используется во всех ключевых точках: синхронизация, ошибки, действия пользователя, удаление плагина.

### 3.2. `Amanita\SyncProduct`
- Обработчик формы синхронизации продукта (метабокс).
- Проверяет nonce, права пользователя, rate-limiting.
- Маппит данные продукта WooCommerce в формат Python-сервиса.
- Вызывает `Amanita\HttpClient` для отправки данных.
- Логирует все этапы (start, success, error).
- Обновляет мета-данные продукта (`_amanita_sync_status`, `_amanita_last_sync`).

### 3.3. `Amanita\SyncOrder`
- Аналогично SyncProduct, но для заказов.
- Маппит и отправляет данные заказа в Python-сервис.
- Логирует результат, обновляет мета-данные заказа.

### 3.4. `Amanita\HttpClient`
- Универсальный HTTP-клиент для общения с Python-микросервисом.
- Поддерживает GET/POST, заголовки, API-ключ.
- Валидация URL, обработка ошибок, логирование запросов/ответов.
- Используется в SyncProduct, SyncOrder.

### 3.5. `Amanita\Uninstaller`
- Очищает все данные плагина при удалении (опции, мета-данные, логи, Action Scheduler, кэш).
- Логирует все этапы удаления.
- Методы: on_activation, on_deactivation, cleanup.

### 3.6. `Amanita\Admin\MetaBoxes`
- Добавляет метабокс синхронизации на страницу продукта.
- Показывает статус, логи, кнопку "Sync".
- Использует `Amanita\Logger` для вывода последних логов по продукту.

### 3.7. `Amanita\Admin\SettingsPage`
- Страница настроек плагина (URL Python-сервиса, API-ключ, опции логирования и лимитов).
- Валидация и сохранение настроек.

---

## 4. Логирование

- Все действия, ошибки, попытки синхронизации, удаления и пр. логируются через `Amanita\Logger`.
- Логи доступны в админке (метабокс продукта).
- Поддерживается ротация (по умолчанию 1000 записей).

---

## 5. Безопасность

- Все формы используют nonce.
- Проверка прав пользователя (`current_user_can`).
- Все редиректы через `wp_safe_redirect`, все выводы через `esc_html`, `esc_attr`.
- Валидация и фильтрация всех входных данных.
- Rate-limiting на синхронизацию.

---

## 6. Тестирование

- Используется PHPUnit 11, WP_Mock.
- Покрытие: Logger, SyncProduct, HttpClient, Uninstaller.
- Моки для всех WP-функций.
- Тесты проходят на PHP 8.4.

---

## 7. Локализация

- Все строки через `__()`, `esc_html__()`.
- Файлы переводов в `languages/`.
- Поддержка WordPress i18n.

---

## 8. Автозагрузка и стандарты

- PSR-4, Composer autoload.
- Все классы в namespace Amanita или Amanita\Admin.
- Нет глобальных классов типа Amanita_SyncProduct.
- Строгая типизация (`declare(strict_types=1)`).

---

## 9. Удаление и очистка

- Корневой `Uninstaller.php` вызывает `Amanita\Uninstaller::cleanup()`.
- Очищаются все опции, мета-данные, логи, кэш, Action Scheduler.

---

## 10. CI/CD

- Пока не настроен, но структура полностью готова для интеграции с GitHub Actions/GitLab CI.

---

# Improvements roadmap

**В процессе анализа были замечены следующие моменты для улучшения:**

1. **Документация**
   - Добавить примеры API-запросов к Python-сервису.
   - Описать структуру логов и формат сообщений.

2. **Тесты**
   - Расширить покрытие: добавить интеграционные тесты для SettingsPage, MetaBoxes.
   - Добавить тесты на обработку ошибок в HttpClient.

3. **UI/UX**
   - Улучшить отображение логов в метабоксе (например, фильтрация по типу, пагинация).
   - Добавить индикатор прогресса синхронизации.

4. **Безопасность**
   - Провести внешний аудит безопасности.
   - Добавить дополнительные проверки на XSS/CSRF в админских формах.

5. **Производительность**
   - Перевести хранение логов из options в отдельную таблицу при большом объёме.
   - Кэшировать часто используемые данные.

6. **Интернационализация**
   - Проверить все пользовательские сообщения на предмет перевода.
   - Добавить больше языков.

7. **CI/CD**
   - Настроить автоматический запуск тестов при push/pull request.
   - Добавить статический анализатор (phpstan, phpcs).

8. **Dev Experience**
   - Добавить Makefile или bash-скрипты для типовых задач (тесты, линтинг, деплой).
   - Описать процесс локальной разработки в README.

9. **API**
   - Документировать все эндпоинты Python-сервиса, ожидаемые форматы данных и ошибки.

10. **Миграции**
    - Если появятся кастомные таблицы — реализовать миграции через dbDelta.

---

**Если потребуется более подробная документация по каждому классу или процессу — дайте знать!**
