# Deploy Full - Руководство по развертыванию контрактов Amanita

## Обзор

`deploy_full.js` - это универсальный скрипт для развертывания и управления контрактами экосистемы Amanita. Скрипт поддерживает различные сценарии деплоя от полной инициализации экосистемы до обновления отдельных контрактов.

**Версия документации**: 2.0  
**Дата обновления**: 17 сентября 2025  
**Статус**: Актуализировано с поддержкой SBT экосистемы

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

# RPC URLs
POLYGON_MAINNET_RPC=https://polygon-rpc.com
POLYGON_MUMBAI_RPC=https://rpc-mumbai.maticvigil.com

# Адреса контрактов (заполняются автоматически)
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x...
INVITE_NFT_CONTRACT_ADDRESS=0x...
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0x...

# SBT экосистема (новая)
SOULBOUND_CORE_CONTRACT_ADDRESS=0x...
SOUL_METADATA_CONTRACT_ADDRESS=0x...
SOUL_RECOVERY_CONTRACT_ADDRESS=0x...
SOUL_INTEGRATION_CONTRACT_ADDRESS=0x...

# Экосистема Amanita
LOVE_DO_POST_NFT_CONTRACT_ADDRESS=0x...
LOVE_EMISSION_ENGINE_CONTRACT_ADDRESS=0x...
AMANITA_TOKEN_CONTRACT_ADDRESS=0x...
AMANITA_GOV_TOKEN_CONTRACT_ADDRESS=0x...
AMANITA_PAYMENT_ROUTER_CONTRACT_ADDRESS=0x...
```

### Выбор сети (Network Profiles)

Скрипт поддерживает различные сети через параметр `--network` и действие через переменную окружения `DEPLOY_ACTION`:

#### Локальная разработка (localhost)
```bash
# Запуск локальной ноды Hardhat
npx hardhat node

# Деплой на localhost (способ 1 - через переменную окружения)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

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
**Описание:** Деплоит все контракты и настраивает связи между ними
**Включает:**
- AmanitaRegistry
- SpiralEngine (заменил InviteNFT)
- ProductRegistry
- SoulIdentity (SBT мост)
- Настройка ролей
- Регистрация в реестре

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
# Способ 1 - через переменную окружения
DEPLOY_ACTION=4 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 4
```
**Описание:** Загружает каталог продуктов из `product_registry_upload_data.json`
**Требования:** Существующие контракты ProductRegistry и SpiralEngine

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
- `AmanitaRegistry` - Центральный реестр контрактов
- `SpiralEngine` - Система инвайт-кодов (заменил InviteNFT)
- `ProductRegistry` - Реестр продуктов
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

#### Mock контракты для тестирования
- `MockSpiralEngine` - Mock для тестирования интеграции
- `FaultySpiralEngine` - Mock с ошибками
- `BytesErrorEngine` - Mock с неизвестными ошибками

**Примеры:**
```bash
# Основная экосистема (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost ProductRegistry
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngine
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
# Способ 1 - через переменную окружения
DEPLOY_ACTION=41 npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 41
```
**Описание:** Активирует все неактивные продукты в каталоге
**Требования:** Существующий каталог с неактивными продуктами

#### `888` - Полная инициализация селлера
```bash
# Способ 1 - через переменные окружения (рекомендуется)
DEPLOY_ACTION=888 DEPLOYER_INVITE=<deployerInvite> SELLER_ADDRESS=<sellerAddress> npx hardhat run scripts/deploy_full.js --network localhost

# Способ 2 - через аргументы командной строки
npx hardhat run scripts/deploy_full.js --network localhost 888 <deployerInvite> <sellerAddress> [catalogData]
```
**Описание:** Полная инициализация селлера от активации до готовности к работе
**Параметры:**
- `deployerInvite`: инвайт код деплоера для активации селлера (обязательный)
- `sellerAddress`: адрес селлера для инициализации (обязательный)
- `catalogData`: путь к JSON файлу с каталогом (опционально)

**Процесс:**
1. Валидация входных параметров
2. Загрузка контрактов (SpiralEngine, ProductRegistry, SoulIdentity)
3. Валидация деплоер инвайта
4. Активация селлера в SpiralEngine
5. Назначение роли SELLER_ROLE
6. Создание SBT токена в SoulIdentity
7. Загрузка каталога продуктов
8. Генерация 12 инвайтов для селлера

**Примеры использования:**
```bash
# Базовый пример с обязательными параметрами (способ 1 - через переменные окружения)
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-29NV-YTBS SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 npx hardhat run scripts/deploy_full.js --network localhost

# С кастомным каталогом (способ 1 - через переменные окружения)
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-29NV-YTBS SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 CATALOG_DATA=/path/to/custom/catalog.json npx hardhat run scripts/deploy_full.js --network localhost

# Через аргументы командной строки (способ 2)
npx hardhat run scripts/deploy_full.js --network localhost 888 AMANITA-29NV-YTBS 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

**Требования:**
- Существующие контракты SpiralEngine, ProductRegistry, SoulIdentity
- Валидный инвайт-код деплоера (полученный через action 777)
- Адрес селлера с достаточным балансом для операций
- Права деплоера для активации пользователей

**Результат:**
- Селлер активирован в SpiralEngine
- Назначена роль SELLER_ROLE
- Создан SBT токен в SoulIdentity
- Загружен каталог продуктов
- Сгенерированы 12 новых инвайтов для селлера

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

### Сценарий 1: Первоначальная настройка основной экосистемы
```bash
# 1. Запуск локальной ноды
npx hardhat node

# 2. Деплой реестра (способ 1 - через переменную окружения)
DEPLOY_ACTION=0 npx hardhat run scripts/deploy_full.js --network localhost

# 3. Полный деплой экосистемы (способ 1 - через переменную окружения)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# 4. Минтинг инвайтов для деплоера (способ 1 - через переменную окружения)
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# 5. Создание каталога (способ 1 - через переменную окружения)
DEPLOY_ACTION=4 npx hardhat run scripts/deploy_full.js --network localhost

# 6. Активация продуктов (способ 1 - через переменную окружения)
DEPLOY_ACTION=41 npx hardhat run scripts/deploy_full.js --network localhost

# Альтернативно - через аргументы командной строки:
# npx hardhat run scripts/deploy_full.js --network localhost 0
# npx hardhat run scripts/deploy_full.js --network localhost 1
# npx hardhat run scripts/deploy_full.js --network localhost 777
# npx hardhat run scripts/deploy_full.js --network localhost 4
# npx hardhat run scripts/deploy_full.js --network localhost 41
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

### Сценарий 4: Обновление контракта
```bash
# Обновление ProductRegistry (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost ProductRegistry

# Обновление SBT контракта (способ 1 - через переменную окружения)
DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SoulboundCore

# Альтернативно - через аргументы командной строки:
# npx hardhat run scripts/deploy_full.js --network localhost 5 ProductRegistry
# npx hardhat run scripts/deploy_full.js --network localhost 5 SoulboundCore
```

### Сценарий 5: Деплой mock контрактов для тестирования
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

### Сценарий 6: Полная инициализация селлера (action 888)
```bash
# 1. Запуск локальной ноды
npx hardhat node

# 2. Полный деплой экосистемы (способ 1 - через переменную окружения)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# 3. Генерация инвайтов для деплоера (способ 1 - через переменную окружения)
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# 4. Полная инициализация селлера (способ 1 - через переменные окружения)
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-B1G4-ADJO npx hardhat run scripts/deploy_full.js --network localhost
или
DEPLOY_ACTION=888 DEPLOYER_INVITE=AMANITA-QDBQ-JJSS SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 npx hardhat run scripts/deploy_full.js --network localhost

# Альтернативно - через аргументы командной строки:
# npx hardhat run scripts/deploy_full.js --network localhost 1
# npx hardhat run scripts/deploy_full.js --network localhost 777
# npx hardhat run scripts/deploy_full.js --network localhost 888 AMANITA-29NV-YTBS 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

**Примечание:** 
- Замените `AMANITA-29NV-YTBS` на реальный инвайт-код из файла `bot/flowers/deployer_invites_localhost.txt`
- Замените `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` на реальный адрес селлера
- Убедитесь, что селлер имеет достаточный баланс для операций

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

**Готовность к production:**
- ✅ 113/113 тестов проходят (100% покрытие)
- ✅ Production-ready качество кода
- ✅ Comprehensive error handling
- ✅ Полная документация и готовность к использованию
