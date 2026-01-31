# Tasks — список задач (Issues Tracker)

**Формат:** Jira-style issues list  
**Последнее обновление:** 2026-01-13  
**Метод:** @analysis.mdc

---

## 📋 Активные задачи

### ❌ TODO (не выполнено)

**MVP 1.1.1 задачи:**

- [❌ TODO] [`task-mvp-111-deploy-contracts-mainnet.md`](task-mvp-111-deploy-contracts-mainnet.md)  
  *Осталось:* Задеплоить все контракты и загрузить каталог в mainnet Polygon через пайп из node-launch.txt (Actions 1, 777, 555, 9, 444, 888). Использовать существующие CID (`USE_EXISTING_CIDS=true`), не загружать в Arweave заново

- [❌ TODO] [`task-mvp-111-connect-woocommerce.md`](task-mvp-111-connect-woocommerce.md)  
  *Осталось:* Создать метаполе `blockchain_id` на тестовом продукте в WooCommerce, проверить формат экспорта CSV, адаптировать код если нужно, импортировать маппинг Woo ID ↔ blockchain_id в продакшн каталог. Подготовка к будущей батч-загрузке orders

**Другие задачи:**

- [✅ DONE] [Action 5 UUPS upgrade](analysis/tasks/task-action5-uups-upgrade/task-implement-action5-uups-upgrade.md) — Action 5: deploy/upgrade UUPS контракта с именем из инпута (DEPLOY_CONTRACT). При существующем контракте — upgrade через upgradeToAndCall; при отсутствии — fresh deploy.

- [✅ DONE] [Action 777 batch mint](analysis/tasks/task-action777-batch-mint/task-implement-action777-batch-mint.md) — Action 777 переведён на mintInviteBatch (одна tx вместо 12). Unit-тесты обновлены.

- [❌ TODO] [`task-fix-action42-productname-upload-uses-real-translations.md`](task-fix-action42-productname-upload-uses-real-translations.md)  
  *Осталось:* Добавить валидацию заглушек `[NEEDS TRANSLATION]` перед загрузкой в Arweave и записью в `AmanitaInternational` (в `uploadTitleFiles` нет проверки `isPlaceholder`). Выбрать SSOT источник переводов, реализовать fail-fast или skip-contract-write поведение. Сейчас заглушки загружаются как есть (проверено в коде: строки 180-265 `product_upload_steps.js`)

- [❌ TODO] [`task-add-product-categories-and-woo-data-contract.md`](task-add-product-categories-and-woo-data-contract.md)  
  *Осталось:* Добавить категории продуктов в data pipeline (из CSV/component data/taxonomy mapping), выровнять формат цен под bot-контракт (PriceInfo с form, weight/volume), чтобы WooCommerce CSV имел непустые `Categories` и `Price`

---

## 📊 Worklog файлы

### ✅ DONE (выполнено, можно удалить)

- [✅ DONE] [`action444-path-not-defined-worklog.md`](action444-path-not-defined-worklog.md)  
  *Статус:* Исправление применено (импорты `path` и `fs` добавлены в `action444()` на строках 342-343). Ошибка "path is not defined" устранена

---

## 📈 Статистика

- **Всего активных задач:** 4
  - ❌ TODO: 4 (2 MVP 1.1.1 + 2 других)

- **MVP 1.1.1 задачи:** 2
  - ❌ TODO: 2

- **Worklog файлы:** 1
  - ✅ DONE: 1 (кандидат на удаление)

---

**Формат статусов:**
- ✅ DONE — выполнено и удалено из списка (или worklog, готовый к удалению)
- ⚠️ PARTIAL — частично выполнено, требуется доработка
- ❌ TODO — не выполнено, требует реализации
- ⚠️ READY — готово к выполнению, все зависимости выполнены
- 📋 DRAFT — черновик задачи (анализ/постановка)
- ⚠️ CHECK — требует дополнительной проверки (дубликат/уточнение)
