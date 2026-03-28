# Custom GPT Actions ↔ Amanita Bot API: соответствие авторизации и схемы

**Назначение:** связать настройки **Actions** в редакторе GPT (как на скрине: Authentication + Schema + Privacy policy) с **фактической** моделью auth из `bot/docs/tech/api/api.md`.  
**Методология:** @.cursor/commands/run-analysis — только выводы из официального гайда OpenAI и из SSOT API-дока; код не исследуется.  
**Связанные файлы:** [openai-custom-gpt-actions-official-guide.md](./openai-custom-gpt-actions-official-guide.md), `bot/docs/tech/api/api.md`.

---

## 1. Три типа Authentication в UI GPT — что им соответствует в Bot API

| Выбор в UI GPT (Actions) | Что делает OpenAI (кратко) | Соответствие зонам Amanita (`api.md`) |
|--------------------------|----------------------------|----------------------------------------|
| **None** | Запросы без секрета; только то, что в OpenAPI (path/query/body). | Подходит для путей, где **HMAC не требуется**: префиксы **`/activities`**, **`/reference`**, а также **`/v1/uploads`**, **`/v1/sign-requests`**, **`/v1/pending-sign-requests`** (они в списке **пропуска** HMAC, §3.1). **Не** подходит для `/products`, `/media`, `/description`, `/api-keys`, **`/v1/wallet-auth`** — там HMAC **не** снят (§1, §3.1). |
| **API Key** (Basic / Bearer / Custom header) | Один сохранённый секрет; платформа добавляет заголовок к каждому вызову action. | Имеет **прямой смысл** для **`Authorization: Bearer <EDGE_TO_BACKEND_SECRET>`** на `PUT/POST /v1/uploads/...` (§2.7). **Не** заменяет **HMAC** для commerce: HMAC строится из `method`, `path`, `body`, `timestamp`, `nonce` и подписи (§3.1) — одним статическим ключом в поле API Key это **не** покрывается без логики подписи на стороне OpenAI (её нет). |
| **OAuth** | Пользовательский вход; в запросах к API уходит **`Authorization: Bearer <user token>`**. | В `api.md` **нет** описания приёма **Logto/JWT пользователя** на `/activities/*` как замены `X-User-Id`: для draft явно указан **`X-User-Id`** (§2.5). Токен **`wallet_auth_token`** из `POST /v1/wallet-auth/verify` используется в guard’ах для **upload/sign-payload** (§2.7, §3.2), а не как общий JWT для всего `/activities`. Связка «OAuth в GPT → наш бекенд» = **отдельный продуктовый/бекенд дизайн**, не зафиксированный в текущем `api.md`. |

**Вывод для MVP «только Activities из GPT»:** чаще всего начинают с **Authentication: None** для схемы, где в `servers` указан **публичный HTTPS** инстанс, и описаны только **`/activities/*`** и при необходимости **`/reference/*`**. Ограничения по безопасности и `mock_user` — см. §4.

---

## 2. Ограничение OpenAI: «Custom headers are not supported» ↔ `X-User-Id`

- Официально (см. [openai-custom-gpt-actions-official-guide.md](./openai-custom-gpt-actions-official-guide.md) §7.5): произвольные заголовки для Actions **не поддерживаются**.
- В Amanita для **`POST /activities/draft`** в доке указан заголовок **`X-User-Id`** (стабильная идентичность; иначе **`mock_user`**) — `api.md` §2.5.
- **Противоречие:** в типичной настройке Action вы **не можете** добавить второй произвольный заголовок рядом с тем, что даёт API Key / OAuth.

**Практические ветки (вне объёма `api.md`, на усмотрение команды):**

1. Оставить **None** и мириться с **`mock_user`** для всех вызовов из GPT (только dev/демо).  
2. Вынести идентификатор в **query/body** — только если бекенд это **примет** (сейчас в `api.md` для draft указан именно header; изменение = задача на API).  
3. **Прокси** перед бекендом, который из фиксированного секрета или из OAuth выставляет `X-User-Id` на upstream.  
4. Уточнить у бекенда, признаётся ли для `/activities` какой‑либо **Bearer** из API Key / OAuth как замена политике `X-User-Id` — в текущем тексте `api.md` это **не** описано.

---

## 3. Схема (Schema) в UI GPT

| Требование OpenAI | Что делать с Amanita |
|-------------------|----------------------|
| OpenAPI 3.x JSON/YAML | Взять **`GET /openapi.json`** с развёрнутого приложения **или** вырезать **подмножество** путей (`/activities`, `/reference`, …) вручную с лимитами длины description (см. официальный гайд §7.2). |
| `servers.url` | Публичный **https://…** (не localhost с ПК без туннеля). |
| `operationId` | Уникальные имена операций — по ним в **Instructions** GPT ссылаются на вызовы. |
| Импорт по URL | Возможен, если инстанс отдаёт схему по HTTPS и доступен из сети OpenAI. |

Детальные JSON-модели тел и ответов — в интерактивной доке FastAPI (`/docs`), не дублировать вручную без необходимости.

---

## 4. Какие маршруты «логично» первыми попасть в один Action (по `api.md` только)

| Группа | Пути | Auth в UI GPT (старт) | Комментарий по `api.md` |
|--------|------|------------------------|-------------------------|
| **A — lifecycle + search activities** | §2.5 + §2.6 reference | **None** (или OAuth позже, если бекенд договорён) | HMAC на эти префиксы не вешается. Проблема **`X-User-Id`** остаётся (§2). |
| **B — edge→backend uploads** | `PUT/POST /v1/uploads/...` | **API Key → Bearer** с секретом уровня `EDGE_TO_BACKEND_SECRET` | Совпадает с §2.7; не смешивать в одну схему с публичным интернетом без rate limit. |
| **C — commerce** | `/products`, `/media`, … | **Не** сводится к «одному API Key» без HMAC-подписи | Нужен либо другой клиент, либо изменение API/прокси. |
| **D — wallet-auth** | `/v1/wallet-auth/*` | **None не спасает** — путь **не** в skip HMAC (§3.1) | Для вызова из GPT потребуются HMAC или доработка `skip_prefixes` + security review (§9). |

---

## 5. Privacy policy в UI

Для публикации GPT со Actions Help Center требует URL политики конфиденциальности. К разделу auth Amanita это не относится, но поле на скрине обязательно для публичного GPT.

---

## 6. Текст для **другого диалога** (фокус только бекенд / код)

Скопируйте блок ниже в чат, где разрешают читать репозиторий `bot/api`:

---

**Запрос для бекенд-контекста**

Нужно подключить **Custom GPT (OpenAI Actions)** к нашему **FastAPI Bot API**. Официально Actions: один тип auth на схему (None / API Key Basic|Bearer|Custom header / OAuth), **произвольные custom headers не поддерживаются**, запросы только HTTPS с публичного egress OpenAI.

По документу `bot/docs/tech/api/api.md`:

- `/activities` и `/reference` — без HMAC; для `POST /activities/draft` указан **`X-User-Id`**, иначе `mock_user`.
- `/v1/uploads` status/callback — Bearer `EDGE_TO_BACKEND_SECRET`; `sign-payload` — wallet guard + Bearer wallet token или fallback `X-User-Id` при env.
- Commerce — HMAC с подписью строки method+path+body+timestamp+nonce.
- `/v1/wallet-auth` — не в skip HMAC.

**Вопросы:**

1. Подтверди по коду: игнорируется ли **`Authorization: Bearer`** на `POST /activities/draft` и остальных `/activities/*`, если он придёт от OAuth Actions? Есть ли хоть какая-то валидация JWT пользователя на этих роутах?
2. Можем ли мы **официально** поддержать идентификатор пользователя для GPT **не через header** (например опциональный query `user_id` или поле в JSON body для draft), чтобы обойти ограничение OpenAI по custom headers? Какие минимальные правки и риски?
3. Для **минимального продукта** «GPT создаёт draft»: достаточно ли политики **только `mock_user`** за reverse proxy с rate limit, или требуется обязательный секрет на уровне API Key на прокси?
4. Если нужен **единый** OAuth (как задумано в инструкциях GPT UI с Logto): какой эндпоинт должен валидировать токен и как он мапится на `user_id` / `X-User-Id` для `activities` и для `wallet_auth_guard`?

Дай ответ с путями файлов и краткими цитатами условий (middleware, dependencies).

---

## 7. Сводка для оператора (экран Add actions)

1. **Authentication:** для **`/activities` + `/reference`** при заданном **`GPT_ACTIONS_BEARER_SECRET`** на бекенде — **API Key → Bearer** с тем же значением (см. §8). Без секрета — как раньше (**None**, риск `mock_user` на публичном URL). Секрет Edge (`/v1/uploads`) — отдельная схема/Action или прокси.  
2. **Schema:** `openapi.json` или урезанный OpenAPI; **servers** = ваш публичный URL.  
3. Учесть **лимиты** OpenAI (45 s, 100k символов, длины description) и **отсутствие `X-User-Id`** в типичной конфигурации (если не прокси/не расширение контракта).  
4. Неясности по коду — закрывать блоком §6 в отдельном диалоге.

---

## 8. API Key «как просит GPT» — можно ли и реализовано ли

**Можно ли:** да. В редакторе GPT тип **API Key** с вариантом **Bearer** — это ровно заголовок `Authorization: Bearer <секрет>`, который OpenAI добавляет ко всем вызовам Actions. Это совместимо с ограничением «без custom headers»: один стандартный заголовок уже предусмотрен платформой.

**Реализовано ли сейчас для `/activities` и `/reference`:** **да**, при **`GPT_ACTIONS_BEARER_SECRET`** (middleware `gpt_actions_bearer`, см. `bot/docs/tech/api/api.md` §3.3).

| Вопрос | Ответ по коду |
|--------|----------------|
| Bearer на `/activities`, `/reference` | Да: `Authorization: Bearer <секрет>` при непустом `GPT_ACTIONS_BEARER_SECRET`; иначе проверка отключена. |
| JWT на `/activities` | Нет (отдельно от этого Bearer). |
| `user_id` в query/body | По-прежнему опционально; без доверенного слоя — риск подмены; при отсутствии — `mock_user` в draft-flow. |
| Только `mock_user` + rate limit | Без Bearer на публичном хосте — слабая модель; с Bearer — граница «только наш GPT/клиент с секретом». |
| Logto OAuth | Валидация на прокси → **`X-User-Id`** на бекенд; кошелёк — отдельно `wallet_auth_token` и guard; **`/v1/wallet-auth`** под HMAC. |

**Не путать с уже существующим Bearer:** для **`PUT/POST /v1/uploads/...`** в `api.md` описан **`Authorization: Bearer <EDGE_TO_BACKEND_SECRET>`** — это контур **edge → backend**, не «ключ Custom GPT». Для GPT Actions логичнее **отдельный** секрет (например `GPT_ACTIONS_BEARER_SECRET`), чтобы не смешивать blast radius и ротацию ключей.

**Смысл API Key для продукта:** один секрет в настройках GPT = **все** пользователи этого GPT ходят в API с **одним и тем же** Bearer. Это хорошо закрывает вопрос «только наш GPT (и никто с улицы) бьёт в эндпоинт», но **не** даёт per-user идентичность в ChatGPT без **OAuth** в том же Action или без прокси, который выставляет `X-User-Id`.

**Статус таска на бекенд:** реализовано в `bot/api/middleware/gpt_actions_bearer.py` + `APIConfig.gpt_actions_bearer_secret`; постановка — `bot/docs/analysis/tasks/task-implement-gpt-actions-api-key-bearer-activities/`. Фрагмент **`securitySchemes`** для импорта в схему Actions — в `GPT UI/instructions/api-methods-reference.md` (блок SSOT → OpenAPI fragment).

**Вне скоупа одного маленького таска:** заменить HMAC на commerce одним API Key; отдельный OAuth для GPT без дизайна с прокси/Logto.

---

**Версия:** 1.2 · **Дата:** 2026-03-28
