## Обзор файлов `bot/docs/product`
## Сводная карта сущностей (для каталога/продукта)

```
OrganicComponentRegistry (contracts/data/components)
└─ component_id (biounit_id)
   ├─ forms[] (доступные формы)
   ├─ features, descriptions (complex/simple fields)
   └─ shared metadata для всех продавцов

Product (bot/data/sellers/*/products/*.json)
├─ business_id / product_id (строковый идентификатор)
├─ format:
│   ├─ SINGLE → корневой component_id
│   └─ MULTI → массив organic_components[{ component_id, proportion }]
├─ form(s), categories, species
├─ prices[] (quantity/unit/price/currency)
└─ ссылки на media/descriptions (CID’ы из catalog pipeline)

Catalog pipeline артефакты
├─ CSV (Iveta_catalog.csv и т.п.)
├─ active_catalog.json (консолидированный список продуктов)
├─ catalog_images.json / organic_cid_mapping.json (CID-словари)
└─ product_registry_upload_data.json (данные для смарт-контракта)

Serialization Flow
ProductRegistry (blockchain) ↔ Arweave metadata ↔ Component Registry
└─ ProductService преобразует это в Python-модели для web/bot
```

| Файл | Содержание |
| --- | --- |
| `AccountService.md` | Архитектура сервиса управления аккаунтами: аутентификация, права доступа, работа с Invite-системой; перечисление зависимостей (`BlockchainService`, `eth_account`, `web3`) и принципов проектирования. |
| `api-jira.md` | Roadmap по синхронизации каталогов WooCommerce ↔ Amanita Blockchain (Epic EPIC-002): цели, архитектурные принципы, задачи MVP, разбиение на user stories. |
| `catalog_pipeline.md` | Подробный пайплайн подготовки каталога: входные данные (CSV, изображения, organic descriptions), стадии обработки (IPFS, конверсия, подготовка JSON), диаграмма архитектуры и описание инструментов. |
| `e-commerce-jira.md` | Epic по внедрению e-commerce в Telegram-боте (EPIC-ECO-001): user stories для каталога, заказов, оплаты; роли команд, приоритеты. Дублирует часть логики, описанной в `api-jira.md`, но сфокусирован на Telegram-боте. |
| `onboarding.md` | Руководство по UX онбордингу пользователей в Telegram-боте: принципы, сценарии, примерные тексты и последовательность шагов. |
| `payments architecture.md` | Последовательная диаграмма платежного процесса (USDT, PaymentProcessor, Observer Service) от генерации заказа до подтверждения оплаты. |
| `product-catalog-population.md` | Runbook заполнения каталога: загрузка изображений/описаний, конвертация CSV→JSON, подготовка данных для реестра, команды для Hardhat actions 4/41. Во многом повторяет pipeline в `catalog_pipeline.md`, но расписан пошагово с командами. |
| `product-formats-explained.md` | Объяснение форматов метаданных продуктов, связь с `OrganicComponentRegistry`, различие FORMAT_SINGLE/FORMAT_MULTI, плюс примеры. Частично перекликается с `product-structure.md` и `product-serialization-flow.md`, но фокусируется на типах продукта и shared компонентах. |
| `product-registry-TDD.md` | TDD план по покрытию `ProductRegistryService` тестами: текущее покрытие, этапы, приоритеты методов, чек-лист. |
| `product-serialization-flow.md` | Полный поток сериализации/десериализации продукта между Blockchain, Arweave, OrganicComponentRegistry; диаграммы и шаги преобразований. Пересекается с `catalog_pipeline.md` и `product-structure.md`, но описывает именно runtime преобразования. |
| `product-structure.md` | Описание идентификаторов (`business_id`, `blockchain_id`), их жизненных циклов, связь с событиями `ProductCreated`, API примеры и кэширование. Пересекается с `product-formats-explained` по полям продукта и с `product-serialization-flow` по жизненному циклу данных. |

