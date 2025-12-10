# 🍄 Amanita Ecosystem — Обзор системы по слоям

**Версия:** 1.0  
**Дата:** 2025-01-12  
**Цель:** Концептуальное понимание системы от философии до технических деталей

---

## 🎯 СЛОЙ 0: КОНЦЕПЦИЯ И ФИЛОСОФИЯ

### Что это такое?

**Amanita** — децентрализованная экосистема для p2p-коммерции, лояльности и репутации, объединяющая:
- Telegram-боты для пользователей
- WebApp-кошельки (некастодиальные)
- WordPress-плагины для продавцов
- Смарт-контракты на EVM

### Ключевая идея

**"Каждый продавец — это независимый узел (seller node)"**

Вместо централизованного маркетплейса (как Amazon), где все продавцы зависят от платформы, в Amanita:
- Каждый продавец ведет свой e-commerce (WooCommerce, свой сайт)
- Amanita предоставляет **мост** (bridge) к общей блокчейн-инфраструктуре
- Общие смарт-контракты решают задачи маркетплейса (доверие, репутация, кросс-продажи)
- Продавцы остаются автономными, но получают преимущества сети

### Философские принципы

1. **Единство технологий и духовности** — технология как проводник развития
2. **Сообщество и взаимопомощь** — каждый участник часть единого организма
3. **Экологическая устойчивость** — минимальное воздействие на природу
4. **Прозрачность и доверие** — открытый код, прозрачные транзакции

### Экономическая модель

**Трехуровневая токен-система:**

1. **$LOVECOIN** (ERC-20) — утилити-токен для социального майнинга
   - Эмиссия: 888,888,888 (начальная) + дополнительная через социальный майнинг
   - Добыча: через социальный майнинг (LoveDo посты + суперлайки)
   - Использование: клеймятся сразу после накопления
   - Контракт: `Lovecoin.sol`

2. **$LGOV** (ERC-20Votes) — governance токен для DAO
   - Контракт: `AmanitaGovToken.sol` (символ: AGOV)
   - Активация: требуется 8 LoveDo постов (порог репутации)
   - Использование: голосование, коллективные решения, коалиции
   - Особенность: одноразовая активация после достижения репутации

3. **InviteNFT** (ERC-721, Soulbound) — социальный капитал
   - Контракт: `SpiralEngine.sol` (реализует функциональность инвайтов)
   - Лимит: 12 инвайтов на активированного пользователя
   - Основа: система доверия через приглашения
   - Ценность: инвайт = привилегия, не право

**Социальный майнинг:**
- Пользователь создает LoveDo пост (хвалит продавца) → максимум 8 постов/месяц
- Продавец дает суперлайк → максимум 8 суперлайков/месяц
- Каждый суперлайк → эмиссия 1 $LOVECOIN + 1 $LGOV (pending)
- Репутация: 8 LoveDo постов → активация $LGOV

**Примечание:** `AmanitaToken.sol` существует в коде, но не используется в `LoveEmissionEngine`. Активная токен-система основана на `Lovecoin` и `AmanitaGovToken`.

---

## 🏗️ СЛОЙ 1: ИНФРАСТРУКТУРА (Infrastructure Layer)

### Блокчейн: Polygon PoS

**Почему Polygon?**
- Низкая стоимость транзакций (gas fees)
- Быстрое подтверждение (fast finality)
- Совместимость с Ethereum (стандартные инструменты)
- Экологичность (Proof of Stake)

**Сети:**
- **Hardhat** (localhost) — для разработки и тестирования
- **Mumbai** (testnet) — для тестирования на публичной сети
- **Polygon** (mainnet) — продакшн

### Хранилище: ArWeave + IPFS

**ArWeave** (основное):
- Постоянное децентрализованное хранилище
- Pay once, store forever
- Используется для: метаданных продуктов, изображений, описаний

**IPFS/Pinata** (fallback):
- Gateway для совместимости
- Временное хранилище (если ArWeave недоступен)

### Serverless: Supabase Edge Functions

**Назначение:**
- Интеграция с ArWeave (WebAssembly модули для криптографии)
- Serverless инфраструктура
- Связка: Python Backend ↔ Edge Functions ↔ ArWeave

### RPC провайдеры

- **Alchemy/Infura** — для продакшна
- **Localhost** — для разработки (Hardhat node)

---

## 📦 СЛОЙ 2: СМАРТ-КОНТРАКТЫ (Smart Contracts Layer)

### Экономические контракты

#### **LoveEmissionEngine.sol**
**Назначение:** Центральная эмиссия токенов и управление репутацией

**Ключевые функции:**
- `emitForSuperlike()` — триггерит эмиссию при суперлайке
- `claimLOVECOIN()` — продавец забирает накопленные $LOVECOIN токены
- `claimLGOV()` — активация governance токенов после порога репутации

**Интеграция:**
- Использует `Lovecoin.sol` для утилити токенов
- Использует `AmanitaGovToken.sol` для governance токенов (как LGOV)
- Интегрирован с `LoveDoPostNFT.sol` и `SpiralEngine.sol`

**Безопасность:**
- Access control через `EMITTER_ROLE`
- Reentrancy protection в `claimLOVECOIN()`
- Социальная валидация суперлайков через граф инвайтов

#### **Lovecoin.sol** (ERC-20)
- Supply: 888,888,888 LOVECOIN (начальная эмиссия)
- Минтинг: контролируется `MINTER_ROLE`
- Использование: социальный майнинг через суперлайки
- Клейм: через `LoveEmissionEngine.claimLOVECOIN()`

#### **AmanitaGovToken.sol** (ERC-20Votes)
- Символ: AGOV (в контракте), используется как LGOV в LoveEmissionEngine
- Governance токен с делегированием и ERC20Permit
- Активация: 8 LoveDo постов (через `claimLGOV()`)
- Snapshot voting support

#### **LoveDoPostNFT.sol** (ERC-721)
**Социальная система репутации:**
- Пользователь создает пост (хвалит продавца)
- Продавец дает суперлайк
- Лимиты: 8 постов/пользователь/месяц, 8 суперлайков/продавец/месяц
- Анти-спам: социальная валидация (только из одного organic community)

### Контроль доступа и социальный капитал

#### **SpiralEngine.sol** (UUPS upgradeable)
**⚠️ ВАЖНО:** `InviteNFT.sol` НЕ СУЩЕСТВУЕТ — вся функциональность инвайтов реализована в `SpiralEngine.sol`!

**Назначение:** Система приглашений, активаций и спиральной иерархии

**Ключевые функции:**
- `mintInvite()` — создание одного инвайта для раздачи
- `activateUser()` — активация пользователя через инвайт-код и создание 12 новых инвайтов
- `grantSellerRole()` — назначение роли продавца активированному пользователю
- `getCircleMembers()` — получение членов organic community
- `getCircleSize()` — размер круга активатора

**Структура данных:**
```solidity
mapping(address => address) public userActivator;  // Кто активировал
mapping(address => address[]) public activatedBy;  // Кого активировал (max 12)
mapping(string => uint256) public inviteCodeToTokenId;  // Код инвайта => ID токена
mapping(uint256 => bool) public isInviteUsed;  // Использован ли инвайт
```

**Organic Trust Communities:**
- Автоматически формируются через активации
- Размер: максимум 13 (лидер + 12 членов)
- Неизменяемые (on-chain history)
- Основа доверия для matchmaking, репутации, кросс-продаж
- Интеграция с `SoulIdentity` для SBT функциональности

#### **Soul* Contracts** (SBT ecosystem, EIP-5192)
- SoulIdentity — делегирование
- Soulbound токены (непередаваемые)

### Реестры продуктов и компонентов

#### **ProductRegistry.sol** (UUPS upgradeable)
**Назначение:** Децентрализованный каталог продуктов

**Особенности:**
- Только IPFS CID хранится on-chain (gas optimization)
- Версионирование каталога (`catalogVersion`)
- Кросс-продажи между продавцами
- Swap-and-pop оптимизация для деактивации

#### **OrganicComponentRegistry.sol** (UUPS upgradeable)
**Назначение:** Общая библиотека компонентов (community-driven)

**Особенности:**
- Переиспользуемые компоненты между продуктами
- Централизованные словари (features.json, component_forms.json)
- Версионирование для синхронизации

### Инфраструктурные контракты

#### **AmanitaRegistry.sol**
**Назначение:** Центральный реестр адресов контрактов

**Функции:**
- `setAddress(name, address)` — обновление адресов
- `getAddress(name)` — получение адреса контракта
- Single source of truth для всех контрактов

#### **Orders.sol**
**Назначение:** Управление заказами с OTP валидацией

#### **AmanitaPaymentRouter.sol**
**Назначение:** Обработка платежей со стейблкоинами (USDT/USDC)

#### **AmanitaInternational.sol**
**Назначение:** Локализация (3-контрактная архитектура)

### Паттерн UUPS (Upgradeable)

**Upgradeable контракты:**
- SpiralEngine
- ProductRegistry
- OrganicComponentRegistry

**Преимущества:**
- Обновление логики без потери данных
- Защита через `UPGRADER_ROLE`
- Proxy pattern для gas efficiency

---

## 🔗 СЛОЙ 3: ИНТЕГРАЦИЯ (Integration Layer)

### Python Backend (FastAPI)

**Архитектура:** Микросервисный паттерн с Service Factory

**Ключевые сервисы:**

#### **BlockchainService** (Singleton)
- Единая точка доступа ко всем блокчейн-операциям
- Web3.py интеграция
- Управление транзакциями и событиями

#### **ProductRegistryService**
- Управление продуктами
- Синхронизация с ProductRegistry контрактом
- Кэширование каталога

#### **AccountService**
- Управление пользователями и продавцами
- Интеграция с SpiralEngine (активации)
- Валидация инвайт-кодов

#### **StorageService**
- Интеграция с ArWeave/IPFS
- Загрузка метаданных
- Fallback механизмы

#### **PaymentService**
- Обработка платежей
- Интеграция с AmanitaPaymentRouter
- OTP валидация

### Service Factory Pattern

**Назначение:**
- Централизованное управление сервисами
- Dependency Injection
- Singleton management
- Тестируемость

**Преимущества:**
- Чистый dependency graph
- Легкое мокирование для тестов
- Единая точка конфигурации

### WordPress API Bridge

**Назначение:** Связка между WooCommerce и Python API

**Функции:**
- Синхронизация каталога продуктов
- Управление заказами
- HMAC аутентификация
- Автоматическая настройка seller node

### Web3.py / ethers.js

**Web3.py** (Python):
- Интеграция с блокчейном из Python backend
- Чтение контрактов, отправка транзакций
- Event listening

**ethers.js** (JavaScript):
- Используется в deploy скриптах
- WordPress plugin интеграция (если нужно)

---

## 🤖 СЛОЙ 4: ПРИЛОЖЕНИЯ (Application Layer)

### Telegram Bot

**Технологии:** aiogram (Python)

**Функционал:**

#### **Onboarding (FSM)**
1. Пользователь получает инвайт-код (ссылка или ручной ввод)
2. Бот валидирует код через SpiralEngine контракт
3. Пользователь создает кошелек через WebApp
4. Доступ к основным функциям экосистемы

#### **Каталог продуктов**
- Просмотр каталога (все продавцы)
- Фильтрация по категориям
- Детальная информация о продуктах
- Компонентная информация (Phase 4)

#### **Управление заказами**
- Корзина
- История заказов
- Статусы заказов

#### **Социальные функции**
- LoveDo посты (хвалить продавцов)
- Суперлайки (для продавцов)
- Инвайты (управление 12 инвайтами)

#### **Мультиязычность**
- 15+ языков
- FSM для выбора языка
- Локализованные шаблоны

### WebApp Wallet

**Технологии:** Vue.js, Telegram WebApp API

**Функционал:**
- Создание некастодиального кошелька
- Управление seed phrase
- Подписание транзакций
- Просмотр балансов ($AMANITA, $AGOV)
- Управление InviteNFT

**Безопасность:**
- Клиентская генерация ключей
- Никакого хранения на сервере
- Полный контроль пользователя

### WordPress Plugin

**Назначение:** Мост между WooCommerce и Amanita экосистемой

**Функционал:**
- Синхронизация каталога продуктов
- Интеграция заказов
- HMAC аутентификация с Python API
- Автоматическая настройка seller node

**Shortcodes:**
- `[amanita-wallet]` — доступ к кошельку
- `[amanita-rewards]` — отображение накопленных токенов
- `[amanita-invites]` — управление инвайтами
- `[amanita-network]` — сеть приглашенных пользователей

---

## 🚀 СЛОЙ 5: РАЗВЕРТЫВАНИЕ И УПРАВЛЕНИЕ (Deployment & Management Layer)

### deploy_full.js (19 действий)

**Структура:**
- **Action 0:** Registry Only (только AmanitaRegistry)
- **Action 1:** Full Ecosystem (все контракты + интеграции)
- **Action 2-4:** Отдельные контракты (OrganicComponentRegistry, ProductRegistry, SpiralEngine)
- **Action 5:** Single Contract (деплой любого контракта)
- **Action 6-8:** Upgrades (UUPS upgrades для core контрактов)
- **Action 555:** Seller + Components (активация + загрузка компонентов)
- **Action 777:** Test Connection (валидация и тест соединения)
- **Action 888:** Full Seller Init (полный онбординг продавца)

### Тестирование

**37/37 тестов** для OrganicComponentRegistry (100% coverage)

**Типы тестов:**
- Unit tests (627 total)
- Integration tests
- E2E tests (action555.e2e.test.js, action888.e2e.test.js)
- Contract tests

### Конфигурация

**Профили развертывания:**
- `localhost` — разработка (Hardhat node)
- `mumbai` — тестнет
- `polygon` — продакшн

**Переменные окружения:**
- `MAGIC_REGISTRY_CONTRACT_ADDRESS` — единственный hardcoded адрес
- Все остальные контракты загружаются через registry

### Документация и логирование

**Документация:**
- Архитектурные документы
- API документация
- Deployment guides
- User guides

**Логирование:**
- Структурированные логи
- Метрики производительности
- Health checks

---

## 🔄 КЛЮЧЕВЫЕ ПОТОКИ ДАННЫХ

### Поток 1: Активация пользователя (Invite System)

```
Пользователь получает инвайт-код
    ↓
Telegram Bot → Backend → SpiralEngine.activateUser()
    ↓
Минт 12 InviteNFT
    ↓
События → Уведомление бота
    ↓
Пользователь получает доступ к экосистеме
```

### Поток 2: Создание продукта

```
Продавец загружает каталог (WordPress plugin или API)
    ↓
StorageService → ArWeave upload (метаданные)
    ↓
ProductRegistry.createProduct(CID)
    ↓
Событие → Обновление кэша
    ↓
Продукт доступен для кросс-продаж
```

### Поток 3: Социальный майнинг (LoveDo → Токены)

```
Пользователь создает LoveDo пост (хвалит продавца)
    ↓
LoveDoPostNFT.mintLoveDoPost()
    ↓
Продавец дает суперлайк
    ↓
LoveDoPostNFT.addSuperlike()
    ↓
LoveEmissionEngine.emitForSuperlike()
    ↓
Эмиссия: 1 $LOVECOIN + 1 $LGOV (pending)
    ↓
Продавец может забрать $LOVECOIN через claimLOVECOIN()
    ↓
При достижении 8 LoveDo постов → активация $LGOV через claimLGOV()
```

### Поток 4: Обновление контракта (UUPS)

```
deploy_full.js → Деплой новой Logic
    ↓
Proxy.upgradeToAndCall()
    ↓
Состояние сохранено
    ↓
Сервисы перезапускаются
```

---

## 🎯 АРХИТЕКТУРНЫЕ ПРИНЦИПЫ

1. **Separation of Concerns** — каждый слой имеет четкую ответственность
2. **UUPS Upgradeability** — 3 core контракта upgradeable без потери данных
3. **Decentralization** — non-custodial wallets, IPFS/ArWeave storage, governance
4. **Modularity** — Service Factory, numbered actions, shareable components
5. **Security** — AccessControl, ReentrancyGuard, Pausable, input validation

---

## 💡 КЛЮЧЕВЫЕ ИННОВАЦИИ

### Трехуровневая токен-система
- **$LOVECOIN** (utility) — социальный майнинг, 888M начальная supply + эмиссия
- **$LGOV** (governance) — ERC20Votes (AmanitaGovToken), порог 8 LoveDo
- **InviteNFT** (social capital) — ERC721 в SpiralEngine, 12 на пользователя, Soulbound

### Механизм социального майнинга
- **LoveDo посты** → **Суперлайки** → **Эмиссия токенов** (1 LOVECOIN + 1 LGOV на суперлайк)
- **Месячные лимиты:** 8 постов/пользователь, 8 суперлайков/продавец
- **Порог репутации:** 8 LoveDo постов для активации LGOV

### Паттерн UUPS Proxy
- **Контракты:** SpiralEngine, ProductRegistry, OrganicComponentRegistry
- **Обновляемая логика** без потери данных
- **UPGRADER_ROLE** защита

### Компонентные продукты
- **Переиспользуемая библиотека:** OrganicComponentRegistry (community-driven)
- **Features & Forms:** Централизованные словари (features.json, component_forms.json)
- **Версионирование:** Инкрементальный catalogVersion для синхронизации

### Organic Trust Communities
- **Автоматическое формирование** через активации
- **Размер:** максимум 13 (лидер + 12 членов)
- **Неизменяемые** (on-chain history)
- **Основа доверия** для matchmaking, репутации, кросс-продаж

---

## 📊 ТЕХНИЧЕСКИЕ МЕТРИКИ

| Метрика | Значение |
|---------|----------|
| **Смарт-контракты** | 25+ deployed |
| **UUPS Upgradeable** | 3 core контракта |
| **Покрытие тестами** | 37/37 (100% для OrganicComponentRegistry) |
| **API эндпоинты** | 50+ (FastAPI) |
| **Bot handlers** | 50 handlers (aiogram) |
| **Deployment actions** | 19 пронумерованных действий |
| **Поддерживаемые сети** | 3 (Hardhat, Polygon, Mumbai) |
| **Token supply** | 888,888,888 LOVECOIN (начальная) + эмиссия |
| **Лимит инвайтов** | 12 на активированного пользователя |
| **Социальный майнинг** | 1 токен/суперлайк |

---

## 🔗 МАТРИЦА ИНТЕГРАЦИЙ

| Компонент | Интегрируется с | Тип интеграции |
|-----------|-----------------|----------------|
| **SpiralEngine** | ProductRegistry, OrganicComponentRegistry | Role validation (SELLER_ROLE) |
| **SpiralEngine** | SoulIdentity | SBT delegation (EIP-5192) |
| **LoveEmissionEngine** | LoveDoPostNFT | Token emission on superlike |
| **ProductRegistry** | OrganicComponentRegistry | Component validation |
| **Python Backend** | Все смарт-контракты | Web3.py/ethers.js calls |
| **Telegram Bot** | Python Backend | aiogram → FastAPI |
| **WordPress Plugin** | Python Backend | REST API bridge |
| **WebApp Wallet** | Python Backend | Vue.js → FastAPI |
| **deploy_full.js** | Все контракты | Deployment & upgrades |

---

## 📚 СВЯЗАННАЯ ДОКУМЕНТАЦИЯ

**Концепция:**
- [manifest.md](manifest.md) — Космическая миссия и философия
- [Network-Economy.md](Network-Economy.md) — Экономическая модель и токеномика
- [connectivity.md](connectivity.md) — Социальная связность (Organic + Explicit)

**Архитектура:**
- [architecture-overview.md](../tech/architecture-overview.md) — Детальная архитектура системы
- [architecture-layers.md](../tech/architecture-layers.md) — 5-слойная архитектура
- [contracts-overview.md](../tech/contracts-overview.md) — Обзор смарт-контрактов

**Техническая:**
- [bot/README.md](../../bot/README.md) — Telegram Bot документация
- [scripts/docs/Deploy_Full.md](../../scripts/docs/Deploy_Full.md) — Deployment guide

---

**Версия документа:** 1.0  
**Последнее обновление:** 2025-01-12  
**Статус:** ✅ COMPLETE

