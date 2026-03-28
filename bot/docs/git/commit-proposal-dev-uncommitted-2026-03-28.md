# Proposal: план коммитов для незакоммиченного дерева (ветка `dev`)

**Дата инвентаризации:** 2026-03-28  
**Ветка:** `dev`  
**Методология:** `docs/methodology/git-commit.md`, процесс согласования — `docs/methodology/git-commit-prompt.md`  
**Примечание:** запрошенный путь `@.cursor/commands/git-commit.md` в репозитории отсутствует; используется канонический документ выше.

**Статус документа:** proposal — **коммиты и push не выполняются** до явного согласования оператора.

---

## 1. Резюме

| Категория | Примерный объём |
|-----------|------------------|
| **Modified (tracked)** | ~40 путей (включая `__pycache__`, submodule `.cursor/rules`) |
| **Untracked** | десятки путей: код, доки, артефакты, секреты, тяжёлые бандлы |
| **Рекомендация** | Разнести на **несколько тематических коммитов**; часть путей **никогда не коммитить**; крупные/сторонние деревья — отдельное решение (submodule, LFS, `.gitignore`). |

---

## 2. Исключить из коммитов (политика `git-commit.md`, шаг 2)

Ниже — **не добавлять в `git add`** без отдельного решения и санитизации.

| Категория | Пути (примеры) | Почему |
|-----------|----------------|--------|
| **Секреты / ключи / окружения** | `arweave-uploader/arweave-key.json`, `keys/*`, `env.mainnet`, `env.prod.iveta`, любые `*.pem` / key json | Приватные данные |
| **Инвайты / чувствительные выгрузки** | `bot/flowers/*_invites*.txt`, `deployer_invites.txt` | Сгенерированные чувствительные данные |
| **Кэш** | `bot/cache/**`, `**/__pycache__/**`, `*.pyc` | Воспроизводимо из исходников / мусор |
| **Coverage / отчёты** | `arweave-uploader/coverage/**`, `gasReporterOutput.json` | Артефакты CI/локального прогона |
| **Локальное состояние** | `anvil/state.json` | Локальный runtime state |
| **Тяжёлые архивы и вендор** | `docs/methodology.zip`, `supabase.zip`, `WP Amanita/**/*.zip`, темы WordPress, `ReferenceWallet/` (если это полная копия кошелька) | Не код; размер; лицензии |
| **Сгенерированный JS** | `arweave-uploader/dist/publish/validate-token.js` | Обычно build output; коммитить только если принято в команде хранить dist |
| **Контент с неясным IP** | PDF/PNG в `docs/safety/`, `docs/concept/`, баннеры | Решение владельца репозитория (юридическое/бренд) |

**Рекомендация по рабочему дереву:** после согласования плана выполнить `git restore` / очистку для `__pycache__` и убедиться, что `.gitignore` покрывает `bot/cache/`, `keys/`, `*.key.json`.

---

## 3. Инвентаризация по проектам / зонам репозитория

### 3.1 Корень репозитория

| Состояние | Пути |
|-----------|------|
| **M** | `.cursor/rules` (submodule: «new commits»), `.gitignore` |
| **??** | `Amanita Banner.jpg`, `elementor-upload-instructions.md`, `test_products.csv`, `gasReporterOutput.json`, `env.mainnet`, `env.prod.iveta`, `keys/` |

### 3.2 `bot/`

| Состояние | Пути (сокращённо) |
|-----------|-------------------|
| **M** | `api/dependencies.py`, `api/main.py`, `api/middleware/auth.py`, `api/routes/__init__.py`, `pending_sign_requests.py`, `sign_requests.py`, `uploads.py`, `api/services/__init__.py`, `docs/tests/overview.md`, `pytest.ini`, `services/core/blockchain.py`, `tests/pytest.ini` |
| **M (не коммитить)** | все `**/__pycache__/**` под `bot/` |
| **?? (код)** | `api/routes/wallet_auth.py`, `api/services/wallet_auth.py`, `api/utils/wallet_auth_guard.py` |
| **?? (тесты)** | `tests/integration/test_activity_full_floou_mock_wallet.py`, `test_upload_floou_integration.py`, `tests/unit/test_upload_jwt_key_pair_alignment.py`, `test_wallet_auth_enforcement.py`, `tests/integration/fixtures/*` |
| **?? (доки)** | `docs/tech/wallet-auth-challenge-signature-protocol.md`, `docs/tech/uploader-node-auth-env-reference.md`, `docs/tests/e2e-floou-manual.md`, `docs/tests/e2e-floou-orchestration-overview.md`, `docs/git/*`, `docs/concept/*.pdf` |
| **?? (не коммитить)** | `cache/translations/*.json`, `flowers/*.txt`, `woocommerce_products.fixed.csv` |

### 3.3 `wallet/`

| Состояние | Пути |
|-----------|------|
| **M** | `mock-runner/index.js`, `mock-runner/README.md`, `docs/mock-runner-launch-guide.md` |
| **??** | `docs/Dynamic.xyz-integration.md`, `docs/SmartID-Parallel.md`, `dynamic.demo.html`, `wallet-new/docs/security/**` (большой набор markdown) |

### 3.4 `scripts/`

| Состояние | Пути |
|-----------|------|
| **M** | `deploy_full.js`, `lib/actions/*.js`, `lib/config/index.js`, `tests/unit/actions/ActionsManager.test.js`, `docs/DEBUG_DEPLOY.md`, `Deploy_Architecture.md`, `Deploy_Full.md`, `node-launch.txt` |
| **??** | `docs/manual-activate-address-via-invite.md`, `get-tx-recipient.js`, `investigate-token.js`, `run-bullrun-floou.sh` |

### 3.5 `contracts/` (документация задач)

| Состояние | Пути |
|-----------|------|
| **M** | `docs/analysis/tasks/task-Activities-1/decision-points-architecture-task1.md`, `task-contracts-docs-vs-code-mismatches.md` |

### 3.6 Hardhat (корень)

| Состояние | Пути |
|-----------|------|
| **M** | `hardhat.config.js` |

### 3.7 `arweave-uploader/`

| Состояние | Пути |
|-----------|------|
| **M** | `dist/publish/validate-token.js`, `docs/architecture.md` |
| **??** | `docs/api.md`, `docs/api.openapi.yaml`, `scripts/build-full-cycle-data-item.js` |
| **?? (не коммитить)** | `arweave-key.json`, `coverage/**` |

### 3.8 `supabase/`

| Состояние | Пути |
|-----------|------|
| **??** | `docs/*.md`, `functions/arweave-upload/package-lock.json`, `functions/arweave-upload/scripts/*.mjs`, `functions/arweave-upload/tests/integration-arweave-real.test.ts`, `migrations/*.sql`, `snippets/*.sql` |
| **?? (не коммитить)** | `supabase.zip` |

### 3.9 `docs/` (корневой каталог документации)

| Состояние | Пути |
|-----------|------|
| **??** | `task-standard.md`, `methodology/index-standard-bullrun-fullpower.md`, `methodology/sync-methodology-with-remote.md`, `concept/*.md`, `tech/*.md`, `safety/*.pdf`, `concept/*.png`, `methodology.zip` |

### 3.10 Прочие деревья

| Зона | Состояние | Комментарий |
|------|-----------|-------------|
| `GPT UI/` | ?? `docs/custom-gpt-architecture-principles-for-dialog-ingest-api.md` | Документ GPT; коммит по решению |
| `wp_plugin/eventify-me` | modified / untracked content | Submodule или вложенный репозиторий — отдельная процедура |
| `WP Amanita/`, `ReferenceWallet/`, `anvil/` | ?? | Тяжёлые/сторонние; не смешивать с bot-фича-коммитами |

---

## 4. Предлагаемый план коммитов (на согласование)

Порядок — от **контракта/кода** к **тестам** и **докам**; сообщения — **английский** conventional commits.  
В **subject/body** не перечислять пути вида `**/tasks/task-*/**` (политика `git-commit.md`).

### Коммит 1 — `feat(bot): add wallet auth routes and guard for signing flow`

**Scope:** новые модули wallet auth + правки `dependencies`, `main`, `middleware/auth`, затронутые routes/services.  
**Файлы (ориентир):** `bot/api/routes/wallet_auth.py`, `bot/api/services/wallet_auth.py`, `bot/api/utils/wallet_auth_guard.py`, изменения в `dependencies.py`, `main.py`, `auth.py`, `routes/__init__.py`, `pending_sign_requests.py`, `sign_requests.py`, `uploads.py`, `api/services/__init__.py`.  
**Проверка:** точечный pytest по wallet auth / smoke API (по факту имеющихся тестов).

### Коммит 2 — `feat(bot): extend blockchain integration for signing or registry (if coupled)`

**Файлы:** `bot/services/core/blockchain.py` **только если** изменения логически связаны с коммитом 1; иначе — **отдельный** коммит с уточнённым scope после просмотра diff.  
**Действие оператора:** при несвязности — переименовать сообщение / вынести в другой PR.

### Коммит 3 — `test(bot): add floou integration and wallet auth enforcement tests`

**Файлы:** `bot/tests/integration/test_*.py`, `bot/tests/unit/test_wallet_auth_enforcement.py`, `test_upload_jwt_key_pair_alignment.py`, `bot/tests/integration/fixtures/**` (убедиться, что фикстуры **не** содержат секретов).  
**Проверка:** `cd bot && python3 -m pytest …` (конкретные пути — по согласованию).

### Коммит 4 — `chore(bot): adjust pytest configuration for new markers or paths`

**Файлы:** `bot/pytest.ini`, `bot/tests/pytest.ini`.

### Коммит 5 — `docs(bot): add floou e2e guides and wallet auth protocol references`

**Файлы:** `bot/docs/tests/e2e-floou-manual.md`, `e2e-floou-orchestration-overview.md`, `bot/docs/tech/wallet-auth-challenge-signature-protocol.md`, `uploader-node-auth-env-reference.md`, правки `bot/docs/tests/overview.md`.  
**Не смешивать** с корневым `docs/` без отдельного решения.

### Коммит 6 — `feat(wallet): improve mock-runner for Arweave signing and local floou`

**Файлы:** `wallet/mock-runner/index.js`, `README.md`, `wallet/docs/mock-runner-launch-guide.md`.

### Коммит 7 — `feat(scripts): update deploy actions and bullrun helper scripts`

**Файлы:** `scripts/deploy_full.js`, `scripts/lib/**`, `scripts/tests/unit/actions/ActionsManager.test.js`, `scripts/run-bullrun-floou.sh`, утилиты `get-tx-recipient.js`, `investigate-token.js` (если относятся к одной линии работ).

### Коммит 8 — `docs(scripts): refresh deploy playbooks and debug notes`

**Файлы:** `scripts/docs/DEBUG_DEPLOY.md`, `Deploy_Architecture.md`, `Deploy_Full.md`, `node-launch.txt`, `manual-activate-address-via-invite.md`.

### Коммит 9 — `docs(contracts): update task analysis decision notes`

**Файлы:** изменённые markdown в `contracts/docs/analysis/tasks/**` (без перечисления имён файлов в subject — см. методологию).

### Коммит 10 — `chore(hardhat): update hardhat configuration`

**Файлы:** `hardhat.config.js`.

### Коммит 11 — `docs(arweave-uploader): extend architecture and API surface docs`

**Файлы:** `arweave-uploader/docs/architecture.md`, `docs/api.md`, `docs/api.openapi.yaml`, `scripts/build-full-cycle-data-item.js`.  
**Исключить:** `dist/**`, `coverage/**`, `arweave-key.json`.

### Коммит 12 — `feat(supabase): add arweave upload migration and edge function tests`

**Файлы:** `supabase/migrations/**`, `supabase/functions/arweave-upload/**` (кроме секретов), `supabase/docs/**`, при необходимости `package-lock.json`.  
**Исключить:** `supabase.zip`.

### Коммит 13 — `docs(root): add methodology and architecture reference docs`

**Файлы:** `docs/task-standard.md`, `docs/methodology/*.md` (без zip), `docs/concept/*.md`, `docs/tech/*.md`.  
**PDF/PNG/zip** — только после явного «включаем бинарники».

### Коммит 14 — `docs(wallet): add wallet-new security notes and integration references`

**Файлы:** `wallet/wallet-new/docs/security/**`, `wallet/docs/Dynamic.xyz-integration.md`, `SmartID-Parallel.md`, `dynamic.demo.html` — **если** решено держать это в основном репозитории (объём большой; альтернатива — отдельный репозиторий или субмодуль).

### Коммит 15 — `chore(repo): update gitignore for secrets, cache, and local artifacts`

**Файлы:** `.gitignore` (расширение правил под `keys/`, `bot/cache/`, `anvil/state.json`, env-файлы и т.д. — по фактическому diff).

### Коммит 16 — `chore(cursor): bump cursor rules submodule pointer`

**Файлы:** `.cursor/rules` — **только** если политика репозитория фиксирует submodule в основной истории.

### Отложено / отдельное решение

- `GPT UI/docs/...` — микрокоммит `docs(gpt-ui): ...` или вместе с коммитом 13.  
- `wp_plugin/eventify-me`, `WP Amanita/`, `ReferenceWallet/` — не входят в предложенную серию без отдельной стратегии.  
- Любые **новые** файлы под `bot/docs/analysis/tasks/**` (если появятся в статусе) — группировать тематически; в сообщении коммита указывать **зону** (`docs(bot): …`), не список файлов тасков.

---

## 5. Чеклист перед `git add` (оператор)

- [ ] Исключены секреты, кэш, coverage, flowers, ключи, zip-тяжеловесы.  
- [ ] `__pycache__` не попадает в индекс.  
- [ ] Пройдены релевантные тесты для групп 1–4.  
- [ ] Согласован **порядок** и **склейка/расщепление** коммитов 1–2 (blockchain).  
- [ ] Push **не выполнять** до отдельной команды (см. `git-commit-prompt.md`).

---

## 6. Следующий шаг

Оператор отвечает: **«план подходит»** / **«объединить коммиты N и M»** / **«исключить зону X»**. После этого можно выполнять `git add`/`git commit` по согласованным группам. **Автоматический push не предполагается.**
