# 📚 Документация проекта Amanita: Структура и назначение

## 🎯 Общее описание

- **README.md** — Краткое описание проекта, его миссии, архитектуры и основных компонентов
- **doc-master.md** — Мастер-файл структуры документации (вы читаете его сейчас)

## 🌱 Концепция и миссия

- **manifest.md** — Космическая миссия проекта, духовные принципы и философия
- **concept/vision.md** — Видение проекта: децентрализованная торговля и лояльность
- **concept/social-mission.md** — Социальная миссия: этичный p2p-маркетинг
- **concept/tokenomics.md** — Экономическая модель: AMANITA Coin, социальный майнинг

## 🏗️ Архитектура и техническое описание

- **architecture/overview.md** — Высокоуровневая архитектура системы
- **architecture/components.md** — Описание всех ключевых компонентов
- **architecture/data-flow.md** — Диаграммы и описание потоков данных
- **architecture/currentwork.md** — Текущая архитектура и планы миграции
- **architecture/integration-plan.md** — План интеграции WordPress + WooCommerce

## 🤖 Telegram Bot и Frontend

- **bot/overview.md** — Общая структура и функционал Telegram-бота
- **bot/commands.md** — Описание команд бота (/invite, /buy, /leave_review)
- **bot/fsm.md** — Конечные автоматы для онбординга и создания продуктов
- **bot/handlers.md** — Обработчики событий и логика взаимодействия
- **bot/localization.md** — Система локализации и многоязычность

- **webapp/overview.md** — Архитектура WebApp кошелька
- **webapp/wallet.md** — Некастодиальный кошелек и управление адресами
- **webapp/integration.md** — Интеграция с Telegram WebApp API
- **webapp/ux.md** — Пользовательский опыт и интерфейс

## 🔗 API и Backend

- **api/overview.md** — REST API архитектура и принципы
- **api/endpoints.md** — Документация эндпоинтов (/products/upload, /api-keys/, /media/upload)
- **api/authentication.md** — HMAC аутентификация и безопасность
- **api/models.md** — Pydantic модели и структуры данных
- **api/testing.md** — Тестирование API и интеграционные тесты

- **backend/services.md** — Сервисный слой и микросервисная архитектура
- **backend/blockchain.md** — Интеграция с блокчейном (web3.py, Polygon)
- **backend/storage.md** — IPFS и ArWeave интеграция
- **backend/security.md** — Безопасность, валидация, права доступа

## 📦 Смарт-контракты

- **contracts/overview.md** — Общая архитектура смарт-контрактов
- **contracts/invite-nft.md** — InviteNFT: система приглашений и доступа
- **contracts/amanita-sale.md** — AmanitaSale: обработка покупок и наград
- **contracts/amanita-token.md** — AmanitaToken: утилити токен экосистемы
- **contracts/order-nft.md** — OrderNFT: ончейн-квитанции покупок
- **contracts/review-nft.md** — ReviewNFT: система отзывов и репутации
- **contracts/security.md** — Безопасность контрактов и соответствие MiCA
- **contracts/testing.md** — Тестирование контрактов и deployment

## 🔌 WordPress Plugin

- **wp-plugin/overview.md** — Назначение и архитектура плагина
- **wp-plugin/woocommerce-integration.md** — Интеграция с WooCommerce
- **wp-plugin/api-connector.md** — Подключение к Python API
- **wp-plugin/activation-hooks.md** — Хуки активации/деактивации
- **wp-plugin/testing.md** — Тестирование плагина

## 🌐 Интеграции и внешние сервисы

- **integrations/arweave.md** — Интеграция с ArWeave, Edge Functions
- **integrations/ipfs.md** — Работа с IPFS, Pinata, fallback-механизмы
- **integrations/polygon.md** — Интеграция с Polygon блокчейном
- **integrations/supabase.md** — Supabase Edge Functions и инфраструктура

## 🛡️ Безопасность и соответствие

- **security/overview.md** — Общая стратегия безопасности
- **security/mica-compliance.md** — Соответствие регламенту MiCA
- **security/contract-security.md** — Безопасность смарт-контрактов
- **security/api-security.md** — Безопасность API и аутентификация
- **security/privacy.md** — Приватность и анонимность пользователей

## 🧪 Тестирование и качество

- **testing/strategy.md** — Общая стратегия тестирования
- **testing/unit-tests.md** — Unit тестирование компонентов
- **testing/integration-tests.md** — Интеграционное тестирование
- **testing/contract-tests.md** — Тестирование смарт-контрактов
- **testing/performance.md** — Нагрузочное тестирование

## 🚀 Развертывание и DevOps

- **deployment/overview.md** — Процессы развертывания
- **deployment/environment.md** — Переменные окружения и конфигурация
- **deployment/ci-cd.md** — Непрерывная интеграция и доставка
- **deployment/monitoring.md** — Мониторинг и логирование

## 📊 Аналитика и метрики

- **analytics/overview.md** — Система аналитики и метрик
- **analytics/business-metrics.md** — Бизнес-метрики и KPI
- **analytics/technical-metrics.md** — Технические метрики производительности
- **analytics/reporting.md** — Отчетность и дашборды

## 📚 Пользовательская документация

- **user-guide/getting-started.md** — Начало работы с Amanita
- **user-guide/invites.md** — Система приглашений и инвайт-кодов
- **user-guide/purchases.md** — Совершение покупок и оплата
- **user-guide/reviews.md** — Оставление отзывов и репутация
- **user-guide/wallet.md** — Работа с кошельком
- **user-guide/faq.md** — Часто задаваемые вопросы

## 🔧 Разработка и контрибьюция

- **development/setup.md** — Настройка среды разработки
- **development/coding-standards.md** — Стандарты кодирования
- **development/contribution.md** — Руководство по контрибьюции
- **development/api-docs.md** — Документация API для разработчиков

## 📋 Справочники и глоссарии

- **reference/glossary.md** — Глоссарий терминов проекта
- **reference/abbreviations.md** — Сокращения и аббревиатуры
- **reference/changelog.md** — История изменений
- **reference/roadmap.md** — Дорожная карта развития

## 🎯 Специальные разделы

- **special/invite-system.md** — Детальное описание системы инвайтов
- **special/social-mining.md** — Социальный майнинг и LoveEmissionEngine
- **special/dao-evolution.md** — Эволюция к DAO и multisig
- **special/estonia-poc.md** — POC для контекста Эстонии

---

## 📝 Принципы организации документации

### 🎯 **Структура по ролям**
- **Пользователи** → user-guide/
- **Разработчики** → development/, api/
- **Архитекторы** → architecture/, contracts/
- **DevOps** → deployment/, testing/

### 🔄 **Жизненный цикл документации**
- **Концепция** → concept/
- **Архитектура** → architecture/
- **Реализация** → api/, bot/, contracts/
- **Развертывание** → deployment/
- **Поддержка** → user-guide/, reference/

### 📊 **Приоритизация по важности**
1. **Критические** (безопасность, архитектура) - обязательны
2. **Важные** (API, контракты) - необходимы для разработки
3. **Полезные** (пользовательские гайды) - улучшают UX
4. **Дополнительные** (справочники) - для углубленного изучения

---

> Каждый файл содержит краткое назначение и ссылки на смежные разделы. Структура легко расширяется по мере роста проекта и соответствует принципам @analysis.mdc.