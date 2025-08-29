# Lean/MVP Архитектура Amanita Connector

## Архитектурная схема

```
[Telegram Bot / Frontend]
        ↓ REST/API
[WooCommerce Core]
        ↕ Hooks/Filters
[Amanita Plugin for WooCommerce]
  ├─ REST API Endpoints: /settings, /sync/product, /sync/order  
  ├─ MetaBoxes в карточках товаров/заказов  
  ├─ Action Scheduler (фоновые задачи sync)  
  ├─ WP HTTP API Client (HMAC/JWT, таймауты, кеш)  
  └─ Settings & Security (api_url, api_key, seller_address, IPFS provider)
        ↓ HTTP
[Python Web3 Microservice]
  ├─ Blockchain Gateway (RPC → ProductRegistry, Orders)  
  └─ IPFS Gateway (Pinata или кастомный node)
        ↕ Events/Logs
[Ethereum/Polygon Node]   [IPFS Node]
```

### Цепочка событий

- **Frontend → WooCommerce**
  - Бот/фронтенд создаёт товары/заказы через стандартный WC REST.

- **WooCommerce → Amanita Plugin**
  - Плагин ловит хуки (`woocommerce_update_product`, `woocommerce_thankyou` и т.д.), сохраняет `ipfs_cid`, `order_hash`, `seller_address` в мета.

- **Sync-запрос**
  - Кнопка “Sync” или авто-триггер ставят задачу через Action Scheduler:
    ```php
    as_enqueue_async_action( 'amanita_sync_product', [ $product_id ] );
    ```

- **Background Worker**
  - Обработчик:
    ```php
    add_action( 'amanita_sync_product', 'your_handler' );
    ```
  - Вызывает Python-сервис через обёртку над WP HTTP API:
    ```php
    wp_remote_post( $python_url . '/api/products', [ 
      'body' => json_encode([ 'ipfs_cid' => $cid, 'seller_address' => $seller ]), 
      'headers' => [ 'Authorization' => 'HMAC ...' ],
    ]);
    ```

- **Python Web3 Microservice**
  - Принимает `/api/products`, формирует и шлёт транзакцию в смарт-контракт ProductRegistry, ждёт подтверждения, возвращает `tx_hash`.
  - Аналогично для заказа `/api/orders`.

- **Отображение результатов**
  - Плагин сохраняет `tx_hash` и статус в post_meta + transient.
  - В MetaBox отображается статус (pending → success/error) и ссылка на блокчейн/IPFS.

---

## Детальная структура плагина (директории и классы)

```
amanita-connector/
├── amanita.php                # основной файл (регистрация плагина, хуки активации/деактивации/удаления)
├── readme.txt                 # описание для WP.org
├── composer.json              # автозагрузка PSR-4
├── languages/                 # i18n (.pot)
│   └── amanita.pot
├── includes/
│   ├── RestApi.php            # класс регистрации REST routes
│   ├── SyncProduct.php        # логика enqueue + callback
│   ├── SyncOrder.php
│   ├── HttpClient.php         # обёртка над wp_remote_*
│   └── Uninstaller.php        # cleanup опций при uninstall
├── admin/
│   ├── SettingsPage.php       # регистрация меню и полей
│   └── MetaBoxes.php          # код для MetaBox товаров/заказов
├── public/
│   └── assets/                # (если понадобится JS/CSS для MetaBox)
├── tests/
│   ├── test-rest-endpoints.php
│   └── test-sync-classes.php
└── assets/
    ├── js/
    └── css/
```

---

## Ключевые Lean/MVP best practices

- **Action Scheduler** вместо WP-Cron: надёжно, логирует, автоповторы.
- **WP HTTP API** (wp_remote_*) + кастомный HttpClient для HMAC/JWT, таймаутов, кеша (transient).
- **i18n**: папка `languages/`, все строки через `__( 'Text', 'amanita' )`, `load_plugin_textdomain()`.
- **Хуки активации/деактивации/удаления**: регистрировать через `register_activation_hook`, `register_deactivation_hook`, `register_uninstall_hook`.
- **Readme и шапка плагина**: readme.txt по стандарту WP.org, шапка с Text Domain, версиями, WC requires.
- **Безопасность**:
  - capability-checks (manage_options или кастомная capability)
  - nonce-валидация для всех REST-запросов с фронта
  - шифрование API-ключа через WP Secrets API (или OpenSSL)
  - REST-эндпоинты защищать JWT/HMAC, проверять подпись
  - валидация: sanitize_text_field(), esc_url_raw(), absint(), регулярка для CID
  - принцип наименьших прав: только нужные права, только свой префикс в wp_options
- **Кеширование**: ответы Python-сервиса кешировать в transient (TTL 5–10 мин)
- **Логирование**: централизованный Log store (ActionScheduler логи), error_log()

---

## MVP-фазы (Lean-спринты)

| Спринт                | Корректировки                                                                 |
|-----------------------|-------------------------------------------------------------------------------|
| 1. Core Sync          | as_enqueue_async_action, HTTP API-клиент с HMAC/JWT                           |
| 2. Background & Cache | transient TTL, Action Scheduler retry, централизованный Log store             |
| 3. Settings & Security| register_settings() + Sanitization, шифрование ключа через WP Secrets API     |
| 4. Error & Tests      | Unit-тесты с WP PHPUnit scaffold, snapshot-тесты для REST-эндпоинтов          |

---

**P.S.** Такой подход обеспечивает надёжный, расширяемый и production-ready MVP, полностью совместимый с best practices WooCommerce/WordPress и готовый к быстрой итерации. 

---

## User Stories для MVP Amanita Connector

### 1. Как администратор магазина, я хочу видеть кнопку "Sync" в карточке товара, чтобы вручную отправить продукт в блокчейн через Python-сервис
- **Описание:** В карточке любого товара WooCommerce появляется метабокс с кнопкой "Sync". При нажатии задача ставится в очередь (Action Scheduler), статус отображается в метабоксе.
- **Ожидаемый результат:** Продукт синхронизирован с блокчейном, отображается tx_hash и статус (pending/success/error).

### 2. Как администратор магазина, я хочу видеть кнопку "Sync" в карточке заказа, чтобы вручную отправить заказ в блокчейн через Python-сервис
- **Описание:** В карточке любого заказа WooCommerce появляется метабокс с кнопкой "Sync". При нажатии задача ставится в очередь, статус отображается в метабоксе.
- **Ожидаемый результат:** Заказ синхронизирован с блокчейном, отображается tx_hash и статус.

### 3. Как администратор, я хочу настраивать параметры интеграции (API-URL, API-ключ, seller_address, IPFS provider) на отдельной странице настроек
- **Описание:** В админке WooCommerce появляется страница настроек плагина Amanita с нужными полями. Все поля валидируются, изменения сохраняются только при наличии прав.
- **Ожидаемый результат:** Настройки сохранены, используются для всех запросов.

### 4. Как администратор, я хочу, чтобы все чувствительные данные (API-ключ) хранились безопасно и не были доступны обычным пользователям
- **Описание:** API-ключ хранится зашифрованным способом, доступен только через secure API плагина.
- **Ожидаемый результат:** Ключ не виден в базе в открытом виде, не выводится в UI.

### 5. Как администратор, я хочу, чтобы все действия sync и настройки были доступны только пользователям с нужными правами
- **Описание:** Все REST-запросы и UI-действия защищены capability-checks и nonce.
- **Ожидаемый результат:** Нет доступа к функциям плагина у пользователей без нужных прав.

### 6. Как администратор, я хочу видеть актуальный статус синхронизации (pending, success, error) и ссылку на транзакцию/блокчейн в карточке товара/заказа
- **Описание:** В метабоксе отображается статус последней sync-операции, ссылка на tx_hash, ссылка на IPFS.
- **Ожидаемый результат:** Вся информация видна прямо в карточке, не нужно искать в логах.

### 7. Как разработчик, я хочу, чтобы все ошибки логировались централизованно, а не терялись в WP error_log
- **Описание:** Все ошибки sync и интеграции пишутся в централизованный лог (Action Scheduler log store), доступны для анализа.
- **Ожидаемый результат:** Можно быстро найти причину сбоя, не теряя ошибок.

### 8. Как разработчик, я хочу, чтобы все REST-эндпоинты были защищены HMAC/JWT и валидировали входные данные
- **Описание:** Все входящие запросы проходят валидацию, проверку подписи, возвращают корректные HTTP-коды и сообщения об ошибках.
- **Ожидаемый результат:** Нет возможности вызвать sync или изменить настройки без авторизации и корректных данных.

### 9. Как пользователь магазина, я хочу, чтобы мои заказы и товары были надёжно синхронизированы с блокчейном, а их статус был прозрачен для админа
- **Описание:** Все действия по sync происходят в фоне, админ всегда видит актуальный статус, ошибки не мешают работе магазина.
- **Ожидаемый результат:** Надёжная интеграция, прозрачность для админа, отсутствие сбоев для пользователей.

--- 

---

## Финальные доработки MVP (по CTO-level рекомендациям)

### Архитектура и цепочка событий
- **REST API версионирование:** Все эндпоинты плагина регистрировать с версией, например: `/wp-json/amanita/v1/sync/product`.
- **Удаление товаров/заказов:** Ловить хуки `before_delete_post` (продукты) и `woocommerce_delete_order` (заказы), чтобы удалять/деактивировать записи в блокчейне и очищать очереди Action Scheduler.

### Детали структуры плагина
- **Uninstaller.php:** При удалении плагина снимать все задачи Action Scheduler через `ActionScheduler::cancel_all()` или фильтрацию по хендлерам.
- **composer.lock:** Хранить рядом с composer.json для фиксации зависимостей.

### UI и настройки
- **Кнопка “Sync”:** Отключать кнопку, если статус уже `pending`, чтобы не дублировать задачи.
- **Кнопка Ping Python-сервис:** На странице настроек добавить кнопку “Ping Python-сервис”, результат сохранять в transient и показывать пользователю.

### Безопасность и валидация
- **Rate-limiting:** Добавить ограничение частоты вызова REST-эндпоинтов через фильтр `rest_pre_dispatch` (например, не чаще 1 раза в 10 секунд на пользователя/IP).
- **WP Secrets API:** В README отметить, что для старых версий WordPress может потребоваться polyfill для шифрования ключей.

### Error-handling и логирование
- **Webhook-fallback:** После 3 неудачных попыток синхронизации — уведомление в админке (admin_notice) или email админу.
- **Очистка кеша:** При успешной или ошибочной синхронизации сбрасывать transient и обновлять мета-статус в карточке товара/заказа.

### Тестирование
- **Интеграционные тесты:** Для end-to-end сценариев использовать wp-browser (Codeception) для автоматизации тестов.
- **Очистка кеша:** В фазе 2 явно указать, что кеш (transient) очищается при любом изменении статуса sync (успех/ошибка).

--- 