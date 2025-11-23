# Deploy Full - Руководство по развертыванию контрактов Amanita

## Обзор

`deploy_full.js` - это универсальный скрипт для развертывания и управления контрактами экосистемы Amanita. Скрипт поддерживает различные сценарии деплоя от полной инициализации экосистемы до обновления отдельных контрактов.

**Версия документации**: 3.1  
**Дата обновления**: 12 января 2025  
**Статус**: Актуализировано с component-based архитектурой и Action 555

## 🔷 UUPS Архитектура (Upgradeable Contracts)

### Обзор UUPS паттерна

С версии 3.0 ключевые контракты экосистемы Amanita используют **UUPS (Universal Upgradeable Proxy Standard)** - паттерн для создания обновляемых смарт-контрактов.

**Ключевые преимущества:**
- ✅ **Обновляемость** - можно улучшать логику без изменения адреса
- ✅ **State сохраняется** - все данные остаются при upgrade
- ✅ **Минимальный Proxy** - экономия gas на взаимодействиях
- ✅ **Централизованный контроль** - upgrade через UPGRADER_ROLE

### UUPS Контракты

#### SpiralEngine (UUPS Upgradeable)

**Назначение:** Система инвайт-кодов для онбординга пользователей

**Компоненты:**
- **Logic:** `SpiralEngineLogic.sol` (809 строк)
  - Содержит всю бизнес-логику
  - Может быть обновлён через UPGRADER_ROLE
  - Адрес меняется при каждом upgrade
- **Proxy:** `SpiralEngineProxy.sol` (50 строк)
  - Точка входа для всех взаимодействий
  - Адрес фиксирован (никогда не меняется)
  - Хранит весь state контракта
- **Interface:** `ISpiralEngine.sol`
  - Стандартный интерфейс для взаимодействия

**Entry Point (используйте этот адрес):**
```bash
SPIRAL_ENGINE_PROXY_ADDRESS=0x...  # Основной адрес для взаимодействия
```

---

#### ProductRegistry (UUPS Upgradeable)

**Назначение:** Каталог продуктов продавцов с IPFS интеграцией

**Компоненты:**
- **Logic:** `ProductRegistryLogic.sol` (587 строк)
  - Содержит всю бизнес-логику каталога
  - Может быть обновлён через UPGRADER_ROLE
  - Адрес меняется при каждом upgrade
- **Proxy:** `ProductRegistryProxy.sol` (59 строк)
  - Точка входа для всех взаимодействий
  - Адрес фиксирован (никогда не меняется)
  - Хранит весь state контракта
- **Interface:** `IProductRegistry.sol`
  - Стандартный интерфейс для взаимодействия

**Entry Point (используйте этот адрес):**
```bash
PRODUCT_REGISTRY_PROXY_ADDRESS=0x...  # Основной адрес для взаимодействия
```

---

### UUPS Deployment Pattern

При деплое UUPS контракта через `deploy_full.js` автоматически выполняются следующие шаги:

```
1. Deploy Logic Implementation
   ↓ Деплоится Logic контракт с бизнес-логикой
   
2. Prepare initialize() calldata
   ↓ Подготавливаются параметры для инициализации
   
3. Deploy Proxy with Logic + initData
   ↓ Деплоится Proxy с указанием Logic и данными для initialize()
   
4. Register Proxy в MagicRegistry
   ↓ Регистрируется ТОЛЬКО Proxy адрес (Logic остаётся внутренним)
   
5. Return Proxy instance
   ↓ Все взаимодействия через Proxy адрес
```

**Важно:** 
- 🔸 **Всегда используйте Proxy адрес** для взаимодействия с контрактом
- 🔸 **Logic адрес** нужен только для upgrade операций
- 🔸 **State хранится в Proxy**, не в Logic!
- 🔸 **MagicRegistry** содержит только Proxy адреса

---

### Upgrade Process

Для обновления UUPS контракта:

```bash
# 1. Деплой новой версии Logic
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngineLogic

# 2. Вызов upgradeToAndCall на Proxy (требуется UPGRADER_ROLE)
# (реализуется через отдельный скрипт upgrade-implementation.js)
npx hardhat run scripts/upgrade-implementation.js --network localhost SpiralEngine <NEW_LOGIC_ADDRESS>

# 3. Proxy теперь использует новую Logic
# Адрес Proxy не изменился, state сохранён
```

**Роли для upgrade:**
- `UPGRADER_ROLE` - может обновлять Logic implementation
- `DEFAULT_ADMIN_ROLE` - может назначать UPGRADER_ROLE

---

## Установка и настройка

### Предварительные требования
- Node.js и npm
- Hardhat
- Настроенный `.env` файл с приватными ключами
- Скомпилированные контракты
- Запущенная локальная нода Hardhat (для localhost) или доступ к RPC

### Переменные окружения (.env)

```bash
# Приватные ключи
DEPLOYER_PRIVATE_KEY=0x...
SELLER_PRIVATE_KEY=0x...
SELLER_ADDRESS=0x...

# RPC URLs
POLYGON_MAINNET_RPC=https://polygon-rpc.com
POLYGON_MUMBAI_RPC=https://rpc-mumbai.maticvigil.com

# === 🔷 UUPS Контракты (Upgradeable) ===

# SpiralEngine UUPS (Система инвайт-кодов)
SPIRAL_ENGINE_PROXY_ADDRESS=0x...     # ← Основной адрес (для взаимодействия)
SPIRAL_ENGINE_LOGIC_ADDRESS=0x...     # Logic адрес (для upgrade)
SPIRAL_ENGINE_CONTRACT_ADDRESS=0x...  # Алиас → PROXY (обратная совместимость)

# ProductRegistry UUPS (Каталог продуктов)
PRODUCT_REGISTRY_PROXY_ADDRESS=0x...     # ← Основной адрес (для взаимодействия)
PRODUCT_REGISTRY_LOGIC_ADDRESS=0x...     # Logic адрес (для upgrade)
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0x...  # Алиас → PROXY (обратная совместимость)

# === Остальные контракты ===

# Центральный реестр
MAGIC_REGISTRY_CONTRACT_ADDRESS=0x...

# SBT экосистема (Soulbound Tokens)
SOULBOUND_CORE_CONTRACT_ADDRESS=0x...
SOUL_METADATA_CONTRACT_ADDRESS=0x...
SOUL_RECOVERY_CONTRACT_ADDRESS=0x...
SOUL_INTEGRATION_CONTRACT_ADDRESS=0x...
SOUL_IDENTITY_CONTRACT_ADDRESS=0x...

# Localization System (3-Contract Architecture)
AMANITA_INTERNATIONAL_PROXY_ADDRESS=0x...      # Точка входа (используйте этот!)
AMANITA_INTERNATIONAL_STORAGE_ADDRESS=0x...    # Хранилище данных
AMANITA_INTERNATIONAL_LOGIC_V1_ADDRESS=0x...   # Текущая логика

# Экосистема Amanita
LOVE_DO_POST_NFT_CONTRACT_ADDRESS=0x...
LOVE_EMISSION_ENGINE_CONTRACT_ADDRESS=0x...
AMANITA_TOKEN_CONTRACT_ADDRESS=0x...
AMANITA_GOV_TOKEN_CONTRACT_ADDRESS=0x...
AMANITA_PAYMENT_ROUTER_CONTRACT_ADDRESS=0x...
```

**Важно для UUPS контрактов:**
- ✅ **Используйте `*_PROXY_ADDRESS`** для всех взаимодействий
- ✅ **`*_LOGIC_ADDRESS`** нужен только для upgrade операций
- ✅ **`*_CONTRACT_ADDRESS`** - алиас для Proxy (обратная совместимость со старым кодом)
- 🔸 После деплоя скрипт автоматически обновит `.env` с правильными адресами

### Выбор сети (Network Profiles)

Скрипт поддерживает различные сети через параметр `--network` и действие через переменную окружения `DEPLOY_ACTION`:

#### Локальная разработка (localhost)
```bash
# Запуск локальной ноды Hardhat
npx hardhat node

# Деплой на localhost (способ 1 - через переменную окружения)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full_new.js --network localhost

# Деплой на localhost (способ 2 - через аргументы командной строки)
npx hardhat run scripts/deploy_full.js --network localhost 1
```

#### Polygon Mainnet
```bash
# Через переменную окружения
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network polygon

# Через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network polygon 1
```

#### Polygon Mumbai (Testnet)
```bash
# Через переменную окружения
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network mumbai

# Через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network mumbai 1
```

#### Другие сети
```bash
# Для любой другой сети, настроенной в hardhat.config.js
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network <network_name>
```

**Важно**: 
- Убедитесь, что для выбранной сети настроен правильный RPC URL и приватные ключи в `.env` файле
- Action можно передать либо через переменную окружения `DEPLOY_ACTION`, либо через аргумент командной строки
- Приоритет: аргументы командной строки > переменная окружения > значение по умолчанию (1)

### Способы передачи параметров

Скрипт поддерживает два способа передачи action:

#### Способ 1: Через переменную окружения (рекомендуется)
```bash
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost
```
**Преимущества:**
- Более читаемый и понятный синтаксис
- Легче использовать в скриптах автоматизации
- Нет конфликтов с аргументами Hardhat

#### Способ 2: Через аргументы командной строки
```bash
npx hardhat run scripts/deploy_full.js --network localhost 1
```
**Преимущества:**
- Более компактный синтаксис
- Соответствует стандартным практикам CLI

**Примечание:** В документации приоритет отдается способу 1 (через переменную окружения), так как он был фактически использован при тестировании и более удобен для автоматизации.

## Доступные действия (Actions)

### Основные действия

#### `0` - Деплой только реестра
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=0 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 0
```
**Описание:** Создает только контракт AmanitaRegistry
**Использование:** Первоначальная настройка экосистемы

#### `1` - Полный деплой экосистемы
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 1
```
**Описание:** Деплоит все контракты и настраивает связи между ними. С версии 3.0 автоматически использует UUPS архитектуру для SpiralEngine и ProductRegistry.

**Включает:**
- MagicRegistry (реестр контрактов)
- **SpiralEngine (UUPS)** - Logic + Proxy автоматически
- **ProductRegistry (UUPS)** - Logic + Proxy автоматически  
- SBT экосистема (5 контрактов: Core, Metadata, Recovery, Integration, Identity)
- **AmanitaInternational (3-контрактная архитектура для локализации)**
- Настройка ролей и связей
- Регистрация Proxy адресов в реестре

**UUPS Deployment Process:**
```
SpiralEngine:
  1. Deploy SpiralEngineLogic
  2. Prepare initialize(admin) calldata
  3. Deploy SpiralEngineProxy(logic, initData)
  4. Register Proxy → MagicRegistry

ProductRegistry:
  1. Deploy ProductRegistryLogic
  2. Prepare initialize(admin, spiralEngine) calldata
  3. Deploy ProductRegistryProxy(logic, initData)
  4. Register Proxy → MagicRegistry
```

#### `2` - Деплой контрактов с обновлением реестра
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=2 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 2
```
**Описание:** Деплоит контракты и обновляет адреса в существующем реестре
**Использование:** Обновление контрактов при существующем реестре

### Специализированные действия

#### `3` - Генерация инвайтов
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=3 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 3
```
**Описание:** Создает и минтит инвайты для продавцов
**Результат:** Сохраняет инвайты в `bot/flowers/invites.txt`

#### `777` - Минтинг инвайтов для деплоера
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 777
```
**Описание:** Создает 12 инвайтов для деплоера (для активации селлеров)
**Результат:** Сохраняет инвайты в `bot/flowers/deployer_invites.txt`

#### `4` - Создание каталога (неактивные продукты)
```bash
DEPLOY_ACTION=4 npx hardhat run scripts/deploy_full.js --network localhost
```
**Описание:** Загружает каталог продуктов из `product_registry_upload_data.json` с привязкой к компонентам

**Требования:**
- Существующие контракты ProductRegistry, SpiralEngine и OrganicComponentRegistry
- **Компоненты должны быть предварительно загружены** (используйте Action 555)
- Seller активирован с ролью SELLER_ROLE
- SELLER_ADDRESS и SELLER_PRIVATE_KEY в .env

**Процесс:**
1. Загружает JSON файл с продуктами (включает componentIds и metadataCID)
2. Создает продукты в ProductRegistry с привязкой к компонентам
3. Продукты создаются неактивными (требуют активации через Action 41)

**Формат данных (product_registry_upload_data.json):**
```json
{
  "id": "amanita_lux",
  "componentIds": ["amanita_muscaria"],
  "metadataCID": "QmQHMTL5ep9pKfs5...",
  "active": true
}
```

**Важно:** С версии 3.1 продукты создаются с массивом componentIds, которые должны существовать в OrganicComponentRegistry

#### `5` - Параметризуемый деплой контракта
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost <CONTRACT_NAME>

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 5 <CONTRACT_NAME>
```
**Описание:** Деплоит конкретный контракт по имени
**Поддерживаемые контракты:**

#### Основная экосистема Amanita
- `MagicRegistry` - Центральный реестр контрактов
- **`SpiralEngine` (UUPS)** - Система инвайт-кодов (автоматически деплоит Logic + Proxy)
  - `SpiralEngineLogic` - Logic implementation (можно деплоить отдельно)
  - `SpiralEngineProxy` - Proxy entry point (можно деплоить отдельно)
- **`ProductRegistry` (UUPS)** - Реестр продуктов (автоматически деплоит Logic + Proxy)
  - `ProductRegistryLogic` - Logic implementation (можно деплоить отдельно)
  - `ProductRegistryProxy` - Proxy entry point (можно деплоить отдельно)
- `LoveDoPostNFT` - NFT для постов о любви
- `LoveEmissionEngine` - Движок эмиссии любви
- `Lovecoin` - Основной токен экосистемы (заменил AmanitaToken)
- `AmanitaGovToken` - Governance токен
- `AmanitaPaymentRouter` - Роутер платежей

#### SBT экосистема (Soulbound Tokens)
- `SoulboundCore` - Базовый SBT контракт (EIP-5192)
- `SoulMetadata` - Динамические метаданные SBT
- `SoulRecovery` - Система восстановления SBT
- `SoulIntegration` - Интеграция с SpiralEngine
- `SoulIdentity` - Мост между SpiralEngine и SBT экосистемой

#### Localization System (3-Contract Architecture)
- `AmanitaInternationalProxy` - Точка входа для мультиязычной системы (фиксированный адрес)
- `AmanitaInternationalStorage` - Персистентное хранилище CID маппингов
- `AmanitaInternationalLogicV1` - Бизнес-логика управления переводами

#### Mock контракты для тестирования
- `MockSpiralEngine` - Mock для тестирования интеграции
- `FaultySpiralEngine` - Mock с ошибками
- `BytesErrorEngine` - Mock с неизвестными ошибками

**Примеры:**
```bash
# UUPS Контракты (автоматический деплой Logic + Proxy)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngine
# ✅ Результат: SpiralEngineLogic + SpiralEngineProxy задеплоены автоматически

DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost ProductRegistry
# ✅ Результат: ProductRegistryLogic + ProductRegistryProxy задеплоены автоматически

# UUPS Контракты (отдельный деплой компонентов - для upgrade)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngineLogic
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngineProxy

# Основная экосистема (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost Lovecoin

# Основная экосистема (способ 2 - через аргументы командной строки)
npx hardhat run scripts/deploy_full.js --network localhost 5 ProductRegistry
npx hardhat run scripts/deploy_full.js --network localhost 5 SpiralEngine
npx hardhat run scripts/deploy_full.js --network localhost 5 Lovecoin

# SBT экосистема (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulboundCore
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulMetadata
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulIdentity

# SBT экосистема (способ 2 - через аргументы командной строки)
npx hardhat run scripts/deploy_full.js --network localhost 5 SoulboundCore
npx hardhat run scripts/deploy_full.js --network localhost 5 SoulMetadata
npx hardhat run scripts/deploy_full.js --network localhost 5 SoulIdentity
```

#### `10` - Диагностика состояния селлера
```bash
# Способ 1 - через переменную окружения (использует SELLER_ADDRESS)
DEPLOY_ACTION=10 npx hardhat run scripts/deploy_full.js --network polygon

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network polygon 10
```
**Описание:** Полная диагностика состояния селлера из .env
**Функциональность:**
- Проверка активации пользователя в SpiralEngine
- Проверка ролей (SELLER_ROLE, ACTIVATOR_ROLE)
- Получение и сохранение инвайтов селлера в файл
- Проверка каталога продуктов (количество, активность)
- Итоговая оценка готовности селлера (0-100%)
**Результат:** 
- Подробный отчет о состоянии селлера
- Сохранение инвайтов в `bot/flowers/{SELLER_ADDRESS}_invites.txt`
- Оценка готовности к работе
**Использование:** Диагностика проблем, проверка готовности селлера

#### `11` - Генерация инвайтов для активного селлера
```bash
# Способ 1 - через переменную окружения (12 инвайтов по умолчанию)
DEPLOY_ACTION=11 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки (кастомное количество)
npx hardhat run scripts/deploy_full.js --network localhost 11 <COUNT>
```
**Описание:** Генерирует инвайт-коды для активного селлера (SELLER_ADDRESS из .env)
**Параметры:**
- `COUNT`: количество инвайтов для генерации (по умолчанию 12)
**Требования:** 
- SELLER_ADDRESS должен быть активирован и иметь роль SELLER_ROLE
- SELLER_PRIVATE_KEY в .env (для подписи транзакций)
**Результат:** Сохраняет инвайты в `bot/flowers/{SELLER_ADDRESS}_invites.txt`
**Использование:** Регулярное пополнение инвайтов для приглашения аудитории

#### `12` - Получение полного каталога с данными
```bash
# Способ 1 - через переменную окружения (использует SELLER_ADDRESS)
DEPLOY_ACTION=12 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки (указать адрес продавца)
npx hardhat run scripts/deploy_full.js --network localhost 12 <SELLER_ADDRESS>
```
**Описание:** Получает полный каталог продавца из блокчейна и загружает все связанные данные через CID
**Параметры:**
- `SELLER_ADDRESS`: адрес продавца (если не указан, используется SELLER_ADDRESS из .env)
**Функциональность:**
- Получает все продукты продавца из блокчейна
- Загружает данные продуктов через IPFS CID
- Загружает описания компонентов через их CID
- Анализирует проблемы валидации (пустые cover_image_url, дефисы в biounit_id)
- Сохраняет полные данные в JSON файл
**Результат:** Сохраняет данные в `bot/catalog_data/catalog_{SELLER_ADDRESS}_{timestamp}.json`
**Использование:** Отладка проблем валидации, анализ данных каталога

#### `13` - Диагностика состояния селлера
```bash
# Способ 1 - через переменную окружения (использует SELLER_ADDRESS)
DEPLOY_ACTION=13 npx hardhat run scripts/deploy_full.js --network polygon

# Способ 2 - через аргументы командной строки (указать адрес продавца)
npx hardhat run scripts/deploy_full.js --network polygon 13 <SELLER_ADDRESS>
```
**Описание:** Полная диагностика состояния селлера из .env
**Параметры:**
- `SELLER_ADDRESS`: адрес продавца (если не указан, используется SELLER_ADDRESS из .env)
**Функциональность:**
- Проверка активации пользователя в SpiralEngine
- Проверка ролей (SELLER_ROLE, ACTIVATOR_ROLE)
- Получение и сохранение инвайтов селлера в файл
- Проверка каталога продуктов (количество, активность)
- Итоговая оценка готовности селлера (0-100%)
**Результат:** 
- Подробный отчет о состоянии селлера
- Сохранение инвайтов в `bot/flowers/{SELLER_ADDRESS}_invites.txt`
- Оценка готовности к работе
**Использование:** Диагностика проблем, проверка готовности селлера

### Действия с каталогом

#### `40` - Создание каталога (альтернатива action 4)
```bash
# Способ 1 - через переменную окружения
DEPLOY_ACTION=40 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 40
```
**Описание:** Аналогично action 4, создает каталог с неактивными продуктами

#### `41` - Активация существующих продуктов
```bash
DEPLOY_ACTION=41 npx hardhat run scripts/deploy_full.js --network localhost
```
**Описание:** Активирует все неактивные продукты в каталоге
**Требования:** 
- Существующий каталог с неактивными продуктами
- SELLER_ADDRESS и SELLER_PRIVATE_KEY в .env

#### `555` - Базовая активация seller + загрузка компонентов
```bash
# Обычный режим (рекомендуется для development)
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY npx hardhat run scripts/deploy_full.js --network localhost

# Dry-run режим (тестирование без регистрации)
DRY_RUN=true DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-BU7J-ZNA5 npx hardhat run scripts/deploy_full.js --network localhost
```

**Описание:** Автоматизированная активация seller и быстрая регистрация компонентов в OrganicComponentRegistry

**Параметры:**
- `DEPLOYER_INVITE` - рутовый инвайт-код из Action 777 (обязательный)
- `SELLER_ADDRESS` - адрес seller (берется из .env)
- `SELLER_PRIVATE_KEY` - приватный ключ seller (берется из .env)
- `DRY_RUN` - режим симуляции без реальной регистрации (опционально)

**Процесс:**
1. **Загрузка контрактов:** SpiralEngine, OrganicComponentRegistry, AmanitaInternational
2. **Активация seller (если не активирован):**
   - Проверка статуса активации
   - Валидация рутового инвайта
   - Вызов `activateUser()` с генерацией 12 новых инвайтов
   - Назначение `SELLER_ROLE` через `grantSellerRole()`
   - Сохранение сгенерированных инвайтов в `bot/flowers/{SELLER_ADDRESS}_invites.txt`
3. **Регистрация компонентов:**
   - Автообнаружение компонентов в `data/components/` (новая структура после миграции)
   - Валидация JSON файлов компонентов
   - Проверка существующих регистраций (skip если уже зарегистрирован)
   - Вызов `createComponent()` для каждого компонента
   - Задержка 2 секунды между компонентами на Polygon mainnet

**⚠️ ВАЖНО: Пути**

Компоненты находятся в:
```
data/components/{component_id}/{component_id}.json
```

Action 555 автоматически использует правильный путь (`../data/components/`).

Если нужно указать кастомный путь:
```bash
# Относительный путь (от корня проекта)
COMPONENTS_DIR="../data/components/" DEPLOY_ACTION=555 node scripts/deploy_full.js 555

# Абсолютный путь
COMPONENTS_DIR="/absolute/path/to/components" DEPLOY_ACTION=555 node scripts/deploy_full.js 555
```

**Формат компонента (data/components/{component_id}/{component_id}.json):**
```json
{
  "business_id": "amanita_muscaria",
  "metadata_cid": "QmPlaceholder",
  "translation_cid": "QmPlaceholder"
}
```

**Результат:**
- ✅ Seller активирован в SpiralEngine (если требовалось)
- ✅ Seller имеет роль SELLER_ROLE
- ✅ 12 инвайтов сгенерировано и сохранено
- ✅ Компоненты зарегистрированы в OrganicComponentRegistry
- ✅ Готово для создания каталога продуктов (Action 4 или Action 888)

**Важно:**
- ⚠️ **Development режим:** Компоненты регистрируются с placeholder CIDs (`QmPlaceholder`)
- ⚠️ **Production:** Для полной загрузки метаданных в Arweave используйте `scripts/upload_all_components.js`
- ✅ **Идемпотентность:** Можно запускать многократно - пропустит уже зарегистрированные компоненты

**Примеры использования:**
```bash
# 1. После деплоя контрактов (Action 1) и генерации рутовых инвайтов (Action 777)
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-2TK7-MJI1 npx hardhat run scripts/deploy_full.js --network localhost

# 2. Dry-run для проверки (без регистрации)
DRY_RUN=true DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-2TK7-MJI1 npx hardhat run scripts/deploy_full.js --network localhost

# 3. Production (Polygon mainnet)
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY npx hardhat run scripts/deploy_full.js --network polygon
```

**Типичный workflow:**
```bash
# Шаг 1: Деплой контрактов
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Шаг 2: Генерация рутовых инвайтов
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# Шаг 3: Активация seller + загрузка компонентов
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY npx hardhat run scripts/deploy_full.js --network localhost

# Шаг 4: Создание каталога продуктов
DEPLOY_ACTION=4 npx hardhat run scripts/deploy_full.js --network localhost
```

#### `888` - Полная инициализация seller (end-to-end)
```bash
# Базовый пример (SELLER_ADDRESS из .env)
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-LIJ5-1EUV npx hardhat run scripts/deploy_full.js --network localhost

# С кастомным каталогом
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-LIJ5-1EUV CATALOG_DATA=/path/to/custom/catalog.json npx hardhat run scripts/deploy_full.js --network localhost
```

**Описание:** Полная end-to-end инициализация seller от активации до готовности к работе с загруженным каталогом продуктов

**Параметры:**
- `DEPLOYER_INVITE` - рутовый инвайт-код из Action 777 (обязательный)
- `SELLER_ADDRESS` - адрес seller (берется из .env)
- `SELLER_PRIVATE_KEY` - приватный ключ seller (берется из .env)
- `CATALOG_DATA` - путь к JSON файлу с каталогом (опционально, по умолчанию `bot/catalog/product_registry_upload_data.json`)

**Полный процесс (7 шагов):**
1. **Валидация параметров:** проверка DEPLOYER_INVITE и SELLER_ADDRESS
2. **Загрузка контрактов:** SpiralEngine, ProductRegistry, SoulIdentity
3. **Проверка активации seller:** если не активирован → активация через `activateUser()`
4. **Назначение ролей:** SELLER_ROLE и ACTIVATOR_ROLE
5. **Создание SBT токена:** через SoulIdentity
6. **Загрузка каталога продуктов:** 
   - Очистка существующего каталога (если есть)
   - Создание продуктов с привязкой к componentIds (Action 4)
   - Активация продуктов (Action 41)
7. **Генерация инвайтов:** 12 новых инвайт-кодов для seller

**Требования:**
- ✅ Существующие контракты: SpiralEngine, ProductRegistry, SoulIdentity, OrganicComponentRegistry
- ✅ **Компоненты загружены** (используйте Action 555 перед Action 888)
- ✅ Валидный рутовый инвайт-код (полученный через Action 777)
- ✅ SELLER_ADDRESS с достаточным балансом для операций
- ✅ SELLER_PRIVATE_KEY в .env

**Результат:**
- ✅ Seller активирован в SpiralEngine (если требовалось)
- ✅ Назначены роли SELLER_ROLE и ACTIVATOR_ROLE
- ✅ Создан SBT токен в SoulIdentity
- ✅ Загружен и активирован каталог продуктов
- ✅ Сгенерированы 12 новых инвайтов для seller
- ✅ **Готово к production:** seller может принимать заказы

**Типичный workflow (полная инициализация с нуля):**
```bash
# Шаг 1: Деплой контрактов
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Шаг 2: Генерация рутовых инвайтов
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# Шаг 3: Активация seller + загрузка компонентов
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY npx hardhat run scripts/deploy_full.js --network localhost

# Шаг 4: Полная инициализация seller с каталогом
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-XXXX-YYYY npx hardhat run scripts/deploy_full.js --network localhost
```

**Важно:**
- ⚠️ Action 888 **объединяет** функциональность Actions 555, 4, 41 и добавляет SBT
- ⚠️ Если компоненты не загружены → используйте сначала Action 555
- ✅ Можно запускать многократно - пропустит активацию если seller уже активирован

## Подробное описание действий

### Action 5: Параметризуемый деплой

#### Поддерживаемые контракты и их зависимости

##### Основная экосистема Amanita

| Контракт | Зависимости | Настройка ролей | Описание |
|----------|-------------|-----------------|----------|
| `AmanitaRegistry` | Нет | Нет | Центральный реестр контрактов |
| `InviteNFT` | Нет | Да (SELLER_ROLE) | Система инвайт-кодов |
| `ProductRegistry` | InviteNFT | Нет | Реестр продуктов |
| `LoveDoPostNFT` | InviteNFT, AmanitaRegistry | Нет | NFT для постов о любви |
| `LoveEmissionEngine` | AmanitaToken, AmanitaGovToken, LoveDoPostNFT, InviteNFT | Да (EMITTER_ROLE) | Движок эмиссии любви |
| `AmanitaToken` | Нет | Нет | Утилити токен |
| `AmanitaGovToken` | Нет | Нет | Governance токен |
| `AmanitaPaymentRouter` | AmanitaToken | Нет | Роутер платежей |

##### SBT экосистема (Soulbound Tokens)

| Контракт | Зависимости | Настройка ролей | Описание |
|----------|-------------|-----------------|----------|
| `SoulboundCore` | Нет | Нет | Базовый SBT контракт (EIP-5192) |
| `SoulMetadata` | SoulboundCore | Нет | Динамические метаданные SBT |
| `SoulRecovery` | SoulboundCore | Нет | Система восстановления SBT |
| `SoulIntegration` | SoulboundCore | Нет | Интеграция с SpiralEngine |
| `SoulIdentity` | SoulboundCore, SoulMetadata | Да | Мост между SpiralEngine и SBT |

##### Localization System (3-Contract Architecture)

| Контракт | Зависимости | Настройка ролей | Описание |
|----------|-------------|-----------------|----------|
| `AmanitaInternationalProxy` | Storage, LogicV1 | Да (ADMIN_ROLE, UPGRADER_ROLE) | Точка входа (фиксированный адрес) |
| `AmanitaInternationalStorage` | Нет | Да (PROXY_ROLE для Proxy) | Персистентное хранилище CID |
| `AmanitaInternationalLogicV1` | Storage | Нет (stateless) | Бизнес-логика управления переводами |

**⚠️ Важно:** Все 3 контракта деплоятся автоматически через `AmanitaInternationalProxy`!

##### Mock контракты

| Контракт | Зависимости | Настройка ролей | Описание |
|----------|-------------|-----------------|----------|
| `MockSpiralEngine` | Нет | Нет | Mock для тестирования интеграции |
| `FaultySpiralEngine` | Нет | Нет | Mock с ошибками |
| `BytesErrorEngine` | Нет | Нет | Mock с неизвестными ошибками |

#### Процесс деплоя для action 5

1. **Валидация** - проверка названия контракта
2. **Проверка зависимостей** - убеждение, что все зависимости существуют
3. **Деплой контракта** - создание экземпляра с правильными параметрами
4. **Регистрация** - добавление адреса в AmanitaRegistry
5. **Настройка ролей** - назначение необходимых ролей
6. **Вывод результата** - отображение адреса контракта

#### Примеры использования action 5

##### Основная экосистема Amanita

```bash
# Деплой токенов (без зависимостей)
node deploy_full.js 5 AmanitaToken
node deploy_full.js 5 AmanitaGovToken

# Деплой InviteNFT (требует настройки ролей)
node deploy_full.js 5 InviteNFT

# Деплой ProductRegistry (требует InviteNFT)
node deploy_full.js 5 ProductRegistry

# Деплой LoveDoPostNFT (требует InviteNFT и AmanitaRegistry)
node deploy_full.js 5 LoveDoPostNFT

# Деплой LoveEmissionEngine (требует все токены и контракты)
node deploy_full.js 5 LoveEmissionEngine
```

##### SBT экосистема

```bash
# Деплой базового SBT контракта
node deploy_full.js 5 SoulboundCore

# Деплой системы метаданных (требует SoulboundCore)
node deploy_full.js 5 SoulMetadata

# Деплой системы восстановления (требует SoulboundCore)
node deploy_full.js 5 SoulRecovery

# Деплой интеграции с SpiralEngine (требует SoulboundCore)
node deploy_full.js 5 SoulIntegration

# Деплой SoulIdentity (мост с SpiralEngine)
node deploy_full.js 5 SoulIdentity
```

##### Localization System (3-Contract Architecture)

```bash
# Деплой AmanitaInternational (деплоит все 3 контракта автоматически!)
node deploy_full.js 5 AmanitaInternationalProxy

# ПРИМЕЧАНИЕ: Storage и LogicV1 НЕ деплоятся отдельно!
# Они автоматически создаются при деплое Proxy
```

##### Mock контракты для тестирования

```bash
# Деплой mock контрактов
node deploy_full.js 5 MockSpiralEngine
node deploy_full.js 5 FaultySpiralEngine
node deploy_full.js 5 BytesErrorEngine
```

## Логирование и отладка

### Уровни логирования
- **🔷** - Информационные сообщения
- **✅** - Успешные операции
- **❌** - Ошибки
- **⚠️** - Предупреждения
- **⭐️** - Важная информация (адреса контрактов)

### Типичные ошибки и решения

#### Ошибка: "Dependency not found in registry"
**Причина:** Попытка деплоить контракт без существующих зависимостей
**Решение:** Сначала задеплойте зависимости

#### Ошибка: "Not enough funds"
**Причина:** Недостаточно средств на счете деплоера
**Решение:** Пополните счет деплоера

#### Ошибка: "Contract already exists"
**Причина:** Контракт уже задеплоен
**Решение:** Используйте action 5 для обновления

## Безопасность

### Проверки безопасности
- Валидация адресов контрактов
- Проверка существования зависимостей
- Контроль доступа к функциям
- Защита от переполнения газа

### Рекомендации
- Всегда проверяйте адреса перед использованием
- Сохраняйте приватные ключи в безопасности
- Тестируйте на тестовых сетях перед mainnet
- Регулярно обновляйте .env файл

## Интеграция с экосистемой

### Автоматическая регистрация
Все контракты автоматически регистрируются в AmanitaRegistry при деплое.

### Обновление адресов
При обновлении контракта новый адрес автоматически обновляется в реестре.

### Настройка ролей
Необходимые роли автоматически настраиваются при деплое.

## Примеры полных сценариев

### Сценарий 1: Первоначальная настройка с UUPS (v3.0)
```bash
# 1. Запуск локальной ноды
npx hardhat node

# 2. Полный деплой экосистемы с UUPS
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Результат:
# ✅ MagicRegistry задеплоен
# ✅ SpiralEngine (UUPS): Logic + Proxy задеплоены
#    - SPIRAL_ENGINE_LOGIC_ADDRESS=0x...
#    - SPIRAL_ENGINE_PROXY_ADDRESS=0x... ← используйте этот!
# ✅ ProductRegistry (UUPS): Logic + Proxy задеплоены
#    - PRODUCT_REGISTRY_LOGIC_ADDRESS=0x...
#    - PRODUCT_REGISTRY_PROXY_ADDRESS=0x... ← используйте этот!
# ✅ SBT экосистема задеплоена (5 контрактов)
# ✅ AmanitaInternational задеплоен
# ✅ Все Proxy адреса зарегистрированы в MagicRegistry

# 3. Минтинг инвайтов для деплоера
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost
# ℹ️ Автоматически использует SPIRAL_ENGINE_PROXY_ADDRESS

# 4. Полная инициализация селлера
DEPLOY_ACTION=888 \
  DEPLOYER_INVITE=AMANITA-XXXX-YYYY \
  SELLER_ADDRESS=0x... \
  npx hardhat run scripts/deploy_full.js --network localhost

  DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-2TK7-MJI1 npx hardhat run scripts/deploy_full.js --network localhost

# Результат:
# ✅ Селлер активирован через SpiralEngine Proxy
# ✅ Роли назначены
# ✅ SBT токен создан
# ✅ Каталог загружен через ProductRegistry Proxy
# ✅ 12 инвайтов сгенерировано
```

### Сценарий 2: Деплой SBT экосистемы
```bash
# 1. Деплой базового SBT контракта (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulboundCore

# 2. Деплой системы метаданных (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulMetadata

# 3. Деплой системы восстановления (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulRecovery

# 4. Деплой интеграции с SpiralEngine (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulIntegration

# Альтернативно - через аргументы командной строки:
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulboundCore
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulMetadata
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulRecovery
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulIntegration
```

### Сценарий 3: Полная экосистема (Amanita + SBT)
```bash
# 1. Основная экосистема Amanita (способ 1 - через переменную окружения)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# 2. SBT экосистема (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulboundCore
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulMetadata
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulRecovery
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulIntegration

# 3. Деплой токенов (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost Lovecoin
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost AmanitaGovToken

# Альтернативно - через аргументы командной строки:
# npx hardhat run scripts/deploy_full.js --network localhost 1
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulboundCore
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulMetadata
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulRecovery
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulIntegration
# npx hardhat run scripts/deploy_full.js --network localhost 5 Lovecoin
# npx hardhat run scripts/deploy_full.js --network localhost 5 AmanitaGovToken
```

### Сценарий 4: UUPS Upgrade (v3.0)
```bash
# Шаг 1: Деплой новой версии Logic
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngineLogic
# Результат: Новый Logic задеплоен по адресу 0xNEW_LOGIC...

# Шаг 2: Вызов upgradeToAndCall на Proxy (через отдельный скрипт)
npx hardhat run scripts/upgrade-implementation.js --network localhost \
  SpiralEngine \
  0xNEW_LOGIC_ADDRESS

# Результат:
# ✅ Proxy теперь использует новую Logic
# ✅ Адрес Proxy не изменился
# ✅ State сохранён
# ✅ MagicRegistry не требует обновления

# Аналогично для ProductRegistry:
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost ProductRegistryLogic
npx hardhat run scripts/upgrade-implementation.js --network localhost ProductRegistry 0xNEW_LOGIC...
```

### Сценарий 5: Деплой AmanitaInternational (Localization System)
```bash
# Полный деплой экосистемы (включая AmanitaInternational)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network polygon

# ИЛИ отдельный деплой AmanitaInternational
CONTRACT_NAME=AmanitaInternationalProxy npx hardhat run scripts/deploy_full.js 5 --network polygon

# Результат в логах:
# === 🌐 Деплой AmanitaInternational (3-контрактная архитектура) ===
# 📦 Шаг 1/4: Деплой AmanitaInternationalStorage...
# ✅ Storage deployed: 0xBBBB...
# ⚙️ Шаг 2/4: Деплой AmanitaInternationalLogicV1...
# ✅ LogicV1 deployed: 0xCCCC...
# 🔗 Шаг 3/4: Деплой AmanitaInternationalProxy...
# ✅ Proxy deployed: 0xAAAA...
# 🔐 Шаг 4/4: Авторизация Proxy в Storage...
# ✅ Proxy authorized in Storage with PROXY_ROLE
# 📝 AmanitaInternational (Proxy) зарегистрирован в реестре
```

**Важно:**
- Все 3 контракта деплоятся автоматически одной командой
- Proxy получает PROXY_ROLE в Storage для записи данных
- В MagicRegistry регистрируется только Proxy (точка входа)
- Используйте только AMANITA_INTERNATIONAL_PROXY_ADDRESS для работы

### Сценарий 6: Деплой mock контрактов для тестирования
```bash
# Деплой mock контрактов (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost MockSpiralEngine
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost FaultySpiralEngine
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost BytesErrorEngine

# Альтернативно - через аргументы командной строки:
# npx hardhat run scripts/deploy_full.js --network localhost 5 MockSpiralEngine
# npx hardhat run scripts/deploy_full.js --network localhost 5 FaultySpiralEngine
# npx hardhat run scripts/deploy_full.js --network localhost 5 BytesErrorEngine
```

### Сценарий 6: Полная инициализация seller (Actions 555 + 888)
```bash
# 1. Запуск локальной ноды
npx hardhat node

# 2. Полный деплой экосистемы
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# 3. Генерация рутовых инвайтов
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# 4. Активация seller + загрузка компонентов
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-B1G4-ADJO npx hardhat run scripts/deploy_full.js --network localhost

# 5. Полная инициализация seller с каталогом (опционально, если нужен каталог сразу)
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-B1G4-ADJO npx hardhat run scripts/deploy_full.js --network localhost
```

**Примечание:** 
- Замените `AMANITA-B1G4-ADJO` на реальный инвайт-код из файла `bot/flowers/deployer_invites_localhost.txt`
- `SELLER_ADDRESS` берется из `.env` файла
- Убедитесь, что seller имеет достаточный баланс для операций
- **Action 555** достаточен для development (активация + компоненты)
- **Action 888** используется когда нужен полный цикл с каталогом продуктов

## Мониторинг и аналитика

### Отслеживание деплоя
- Все операции логируются в консоль
- Адреса контрактов выводятся для копирования
- События деплоя можно отслеживать в блокчейне

### Проверка состояния
```bash
# Проверка адресов в реестре
node -e "
const registry = new ethers.Contract(process.env.AMANITA_REGISTRY_CONTRACT_ADDRESS, abi, provider);
console.log('ProductRegistry:', await registry.getAddress('ProductRegistry'));
"
```

## Новые возможности в версии 3.1

### 🧬 Архитектура на основе компонентов (Component-Based Architecture)
**Главное нововведение версии 3.1:**
- ✅ **OrganicComponentRegistry** - система управления органическими компонентами
- ✅ **ProductRegistry v2** - продукты создаются с привязкой к массиву компонентов
- ✅ **Action 555** - автоматизированная активация seller + загрузка компонентов
- ✅ **Action 4 v2** - создание каталога с componentIds
- ✅ **Action 888 v2** - полная инициализация с проверкой компонентов
- ✅ Новый формат `product_registry_upload_data.json` с componentIds
- ✅ Placeholder CIDs для development режима

**Преимущества компонентной архитектуры:**
- 🧩 **Переиспользование данных:** Один компонент используется в нескольких продуктах
- 🌍 **Мультиязычность:** Переводы хранятся на уровне компонентов
- 📊 **Отслеживание использования:** Счетчики использования компонентов
- ⚡ **Быстрый деплой:** Action 555 регистрирует компоненты за минуты
- 🔄 **Идемпотентность:** Безопасное повторное выполнение Actions

**Workflow версии 3.1:**
```bash
DEPLOY_ACTION=1   # Деплой контрактов с OrganicComponentRegistry
DEPLOY_ACTION=777 # Генерация рутовых инвайтов
DEPLOY_ACTION=555 # Активация seller + загрузка компонентов
DEPLOY_ACTION=4   # Создание каталога с componentIds
```

**Обратная совместимость:**
- ⚠️ Версия 3.1 НЕ совместима с product_registry_upload_data.json версии 3.0
- ✅ Все контракты версии 3.0 (UUPS) работают без изменений
- ✅ Миграция: добавьте componentIds и переименуйте ipfsCID → metadataCID

## Новые возможности в версии 3.0

### 🔷 UUPS Архитектура (Upgradeable Contracts)
**Главное нововведение версии 3.0:**
- ✅ **SpiralEngine** теперь UUPS upgradeable (Logic + Proxy)
- ✅ **ProductRegistry** теперь UUPS upgradeable (Logic + Proxy)
- ✅ Автоматический деплой Logic + Proxy через Action 1 и Action 5
- ✅ Отдельный деплой компонентов для upgrade (SpiralEngineLogic, SpiralEngineProxy)
- ✅ Полная обратная совместимость со старыми .env переменными
- ✅ State сохраняется при upgrade
- ✅ Адрес Proxy фиксирован (никогда не меняется)
- ✅ MagicRegistry регистрирует только Proxy адреса

**Преимущества UUPS:**
- 📈 Можно обновлять логику без изменения адреса контракта
- 💾 Все данные сохраняются при upgrade
- ⚡ Минимальный Proxy для экономии gas
- 🔒 Централизованный контроль через UPGRADER_ROLE

## Новые возможности в версии 2.0

### Поддержка SBT экосистемы
- **SoulboundCore**: Базовый SBT контракт с EIP-5192 compliance
- **SoulMetadata**: Динамические метаданные с IPFS интеграцией
- **SoulRecovery**: Система восстановления через guardian'ов
- **SoulIntegration**: Интеграция с SpiralEngine для уведомлений

### Mock контракты для тестирования
- **MockSpiralEngine**: Успешные уведомления
- **FaultySpiralEngine**: Обработка ошибок
- **BytesErrorEngine**: Неизвестные ошибки

### Улучшенная документация
- Детальное описание всех контрактов
- Примеры для SBT экосистемы
- Новые сценарии деплоя

## Ограничения и известные проблемы

### Action 555 - Два режима работы (v3.2)

Action 555 теперь поддерживает два режима работы для разных сценариев использования.

#### Full Mode (по умолчанию)

**Назначение:** Полная загрузка компонентов в Arweave с реальными метаданными.

```bash
DEPLOY_ACTION=555 DEPLOYER_INVITE=XXXX node scripts/deploy_full.js 555
```

**Особенности:**
- 🚀 Полная загрузка в Arweave (~5-10 минут)
- 📤 Реальные CIDs для всех метаданных
- ✅ Готово для production
- 🔍 Детальный отчёт с CID и Contract ID

**Когда использовать:**
- Production deployment
- Полная настройка для бота
- Загрузка реальных метаданных компонентов

#### Quick Mode (ARWEAVE=false)

**Назначение:** Быстрая регистрация компонентов для development и тестирования.

```bash
ARWEAVE=false DEPLOY_ACTION=555 DEPLOYER_INVITE=XXXX node scripts/deploy_full.js 555
```

**Особенности:**
- ⚡ Быстрое выполнение (~30 секунд)
- 📝 Использует placeholder CIDs (`QmPlaceholder`)
- ✅ Подходит для тестирования контрактов
- ⚠️ БЕЗ реальных метаданных в Arweave

**Когда использовать:**
- Development и локальное тестирование
- Быстрая проверка интеграции контрактов
- Отладка бизнес-логики

**Процесс Full Mode (по умолчанию):**
1. **Проверка Arweave** - ключ, баланс, подключение
2. **Upload Simple Fields** → Arweave (title, dosage)
3. **Upload Complex Fields** → Arweave (описания на всех языках)
4. **Upload Shareable Data** → Arweave (features, forms)
5. **Update Root Metadata** - создание финального JSON
6. **Upload Root Metadata** → Arweave
7. **Register Component** → Blockchain (с реальными CIDs)

#### Проверка готовности Arweave

Поскольку Full Mode включен по умолчанию, рекомендуется проверить готовность Arweave:

```bash
# Базовая проверка
node scripts/Arweave-Readiness.js

# С тестовой загрузкой
node scripts/Arweave-Readiness.js --test-upload
```

**Требования:**
- ✅ Файл `.arweave-key.json` в корне проекта
- ✅ Баланс AR токенов > 0.001 AR
- ✅ Подключение к Arweave сети
- ✅ Активированный seller с SELLER_ROLE

#### Troubleshooting

**Ошибка: "Arweave key не найден"**
```bash
# Проверьте наличие ключа
ls -la .arweave-key.json

# Создайте ключ если отсутствует
node scripts/archive/upload_all_components.js --generate-key
```

**Ошибка: "Arweave wallet имеет нулевой баланс"**
```bash
# Получите AR токены на https://www.arweave.org/
# Или используйте Quick Mode для development
ARWEAVE=false DEPLOY_ACTION=555 DEPLOYER_INVITE=XXXX node scripts/deploy_full.js 555
```

**Ошибка: "Seller не активирован"**
```bash
# Сначала выполните активацию seller
DEPLOY_ACTION=555 DEPLOYER_INVITE=XXXX node scripts/deploy_full.js 555
```

**Статус:** ✅ Реализовано в версии 3.2. Поддерживает оба режима работы.

### Migration от версии 3.0 к 3.1

**Проблема:** Формат `product_registry_upload_data.json` изменился.

**Старый формат (v3.0):**
```json
{
  "id": "amanita_lux",
  "ipfsCID": "QmQHMTL5ep9pKfs5...",
  "active": true
}
```

**Новый формат (v3.1):**
```json
{
  "id": "amanita_lux",
  "componentIds": ["amanita_muscaria"],
  "metadataCID": "QmQHMTL5ep9pKfs5...",
  "active": true
}
```

**Миграция:**
1. Переименовать `ipfsCID` → `metadataCID`
2. Добавить массив `componentIds` для каждого продукта
3. Убедиться что компоненты зарегистрированы (Action 555)

## Заключение

`deploy_full.js` предоставляет гибкий и мощный инструмент для управления контрактами экосистемы Amanita, включая новую SBT экосистему. Параметризуемый деплой (action 5) особенно полезен для обновления отдельных контрактов без полного передеплоя экосистемы.

**Ключевые преимущества:**
- 🎯 **Точность** - деплой только нужных контрактов
- 🔧 **Гибкость** - поддержка различных сценариев
- 🛡️ **Безопасность** - проверка зависимостей и валидация
- 📊 **Прозрачность** - детальное логирование процесса
- 🔄 **Автоматизация** - минимальное ручное вмешательство
- 🆕 **SBT поддержка** - полная поддержка Soulbound Token экосистемы
- 🧪 **Тестирование** - mock контракты для comprehensive testing
- 🧬 **Component-based архитектура (v3.1)** - переиспользование компонентов
- ⚡ **Быстрый deployment** - Action 555 для мгновенной настройки

**Готовность к production:**
- ✅ 113/113 тестов проходят (100% покрытие)
- ✅ Production-ready качество кода
- ✅ Comprehensive error handling
- ✅ Полная документация и готовность к использованию
- ✅ **UUPS upgradeable contracts (v3.0)** для долгосрочной эволюции экосистемы
- ✅ **Component-based architecture (v3.1)** для масштабируемого каталога
- ⚠️ **Development mode** - Action 555 с placeholder CIDs (production требует upload_all_components.js)

Готовность к production:Вставить после строки 1266
+### 🔁 Критический порядок для MVP (Regression Priority)
+Для минимального жизнеспособного релиза (MVP) обязательно прогоняйте действия в следующей последовательности:
+
+1. **Action 0** — деплой `MagicRegistry` (если сеть пустая).
+2. **Action 1** — полный деплой экосистемы (UUPS + SBT + связи).
+3. **Action 2** — повторная настройка связей; подтверждает корректность после деплоя.
+4. **Action 777** — генерация рутовых инвайтов.
+5. **Action 555** — загрузка компонентов (component-based архитектура).
+6. **Action 444** — автоматический каталог-пайплайн; включает вложенные шаги `41 → 42 → 43`.
+7. **Action 888** — полный end-to-end pipeline для seller (опирается на предыдущие шаги).
+
+🧪 **Тестовое покрытие:** все перечисленные действия имеют e2e-тесты (deploy/actions, component/actions, catalog/actions, full/action888). Выполняйте проверки именно в указанном порядке — каждый шаг опирается на артефакты предыдущего.
+
+✅ **Последние успешные прогоны:**
+- 2025-11-13 12:48 (UTC) — e2e `Action 0`, `Action 1`, `Action 2` (зелёные).
+- 2025-11-13 12:52 (UTC) — e2e `Action 777` (генерация рутовых инвайтов, 12 кодов).
+- 2025-11-13 12:54 (UTC) — e2e `Action 555` (component upload, placeholders + error cases).
+- 2025-11-13 12:56 (UTC) — e2e `Action 444` (automatic pipeline CSV → JSON → CID, 3 продукта, rollback-гард).
+- Остальные этапы (888) запланированы к проверке после закрепления ролей/инфраструктуры.
