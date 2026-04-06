# `X-User-Id` и идентификация пользователя при создании Activity (draft)

Документ фиксирует **фактическое поведение кода** (`bot/api/routes/activities.py`, `bot/api/utils/wallet_auth_guard.py`, `bot/services/upload/…`), а не желаемый end-state продукта.

## 1. Где передаётся «user id»

При создании черновика активности используется **HTTP-заголовок** `X-User-Id` (в коде параметр `x_user_id`, alias `X-User-Id`). Отдельного поля `user_id` в теле запроса `POST /activities/draft` в модели `ActivityCreateRequest` нет.

Источник: `api/routes/activities.py` — `create_draft`.

## 2. Валидация на `POST /activities/draft`

| Проверка | Поведение |
|----------|-----------|
| Формат строки (FastAPI / Pydantic) | **Не валидируется** как UUID — заголовок — обычная строка; пустой → fallback на `mock_user`. |
| Существование пользователя в БД / whitelist | **Нет** — сервер не проверяет, что такой пользователь «зарегистрирован». |
| Совпадение с кошельком | **На этом шаге нет** — нет обязательного `Authorization: Bearer` с сессией wallet-auth. |
| Если заголовок отсутствует | `user_id` подставляется как **`mock_user`** (строка по умолчанию в коде). |

Тело запроса валидируется только через Pydantic (`activity_type`, `title`, `short_summary` / `full_description` и т.д.) — это не про идентификацию пользователя.

**Вывод по HTTP-слою:** произвольная строка в `X-User-Id` не отсекается Pydantic.

**Важно — Supabase / таблица `uploads`:** поле **`user_id`** в БД имеет тип **UUID**. При `POST /activities/draft` вызывается `UploadService.prepare` → **`_check_rate_limits`** → запросы вроде `count_uploads_by_user_since` с фильтром `user_id=eq.<значение>`. Если строка **не является допустимым литералом UUID** (например `111.444.555.888.555.444.111`), Postgres возвращает **`22P02` invalid input syntax for type uuid** → клиент видит **HTTP 500**. Это не «валидатор в роуте», а **тип колонки** в БД.

Для локального Bullrun скрипт задаёт по умолчанию `USER_ID=00000000-0000-0000-0000-000000000001` (`scripts/shell/run-bullrun-floou.sh`); переопределяйте **`USER_ID` только валидным UUID** (или оставьте дефолт / уберите экспорт «точечного» идентификатора).

**Итог:** на этапе создания draft **произвольный `X-User-Id` допустим только если не упрётся в UUID-ограничение БД**; иначе используйте формат UUID или `mock_user` (без заголовка), если сценарий это позволяет — плюс **внешний** контур доступа к API (см. §5).

## 3. Для чего тогда нужен `user_id` после draft

Значение, переданное в `create_draft` как `user_id` (`X-User-Id` или `mock_user`), передаётся в:

1. **`PrepareResolveService.prepare_upload_for_draft(draft_id, user_id, payload)`**  
2. **`UploadService.prepare(..., user_id, activity_id=draft_id)`** — в хранилище создаётся запись **upload**, к которой привязан **`user_id`** (используется rate limit и дальнейшая маршрутизация push/sign).

3. **`push_sender.send_sign_request(user_id, "sign_arweave", upload_id)`** — очередь событий для кошелька помечается этим идентификатором.

То есть `user_id` становится **владельцем upload** в смысле приложения: дальнейшие шаги сценария проверяют **совпадение** переданного идентификатора с записанным в upload.

## 4. Где идентификатор уже «жёстче» проверяется

Ниже — эндпоинты, которые вызывают **`authenticate_wallet_request`** (`api/utils/wallet_auth_guard.py`):

### 4.1 Режим `WALLET_AUTH_MODE=challenge_signature` и Bearer-токен

Если передан валидный **`Authorization: Bearer`** с session token (сессия после wallet challenge):

- `user_id` берётся из **сессии** (`session.user_id`), а не «на доверии» из заголовка.
- Если указаны `X-User-Id` или `expected_user_id` (из записи upload / sign_request), они **должны совпадать** с `session.user_id`, иначе **403** (`auth_user_mismatch`).
- Опционально проверяется `X-Wallet-Address` против адреса в сессии.

### 4.2 Fallback: только заголовок (`ALLOW_X_USER_ID_FALLBACK`)

По умолчанию **`ALLOW_X_USER_ID_FALLBACK=true`**. Если **нет** валидного Bearer для challenge-режима:

- Требуется **`X-User-Id`** (иначе **401**).
- Если в коде передан **`expected_user_id`** (например, `user_id` из записи upload), он **должен совпадать** с `X-User-Id`, иначе **403** (`X-User-Id must match user_id`).

Так реализована проверка «этот upload принадлежит этому пользователю» на маршрутах вроде:

- `GET /v1/uploads/{upload_id}/sign-payload` — после извлечения `user_id` из principal сравнивается с `rec.user_id` записи upload (**403**, если не совпало).
- `GET /v1/pending-sign-requests` — `expected_user_id` из query должен совпасть с заголовком.

**Если выключить fallback** (`ALLOW_X_USER_ID_FALLBACK=false`) и не передать валидный Bearer в режиме challenge — получите **403** `auth_fallback_disabled`.

## 5. Доступ к самому `POST /activities/draft` (не путать с user id)

На уровне приложения к путям `/activities` и `/reference` может быть включён **`GptActionsBearerMiddleware`**, если задан **`GPT_ACTIONS_BEARER_SECRET`**: тогда клиент должен отправить **`Authorization: Bearer`** с секретом (интеграция Custom GPT Actions). Это **ограничивает, кто вообще может бить в API**, но **не подставляет и не проверяет `X-User-Id`**.

Отдельно глобальный **`HMACMiddleware`** для API-ключей может применяться к другим зонам; для `/activities` в конфигурации обычно предусмотрен skip — детали в **`api.md`**.

Итого: **«можно ли слать любым user id»** зависит от контекста:

- **С точки зрения только роута draft** — да, строка произвольная (или `mock_user`).
- **С точки зрения безопасности продакшена** — доступ к эндпоинту должен быть закрыт внешним слоем (Bearer GPT, сеть, VPN); иначе любой, кто может вызвать API, может указать чужой `X-User-Id` и привязать upload к чужому идентификатору **до** того, как wallet-auth начнёт сопоставлять сессию.

## 6. Rate limits по `user_id`

`UploadService.prepare` вызывает **`_check_rate_limits(user_id, payload_size)`**: лимиты считаются **по строке `user_id`**. Произвольный `X-User-Id` означает отдельную «квоту» на эту строку (и отдельную запись upload), а не гарантию, что это реальный пользователь.

## 7. Связанные переменные окружения

| Переменная | Значение по умолчанию (если не задано) | Смысл |
|------------|----------------------------------------|--------|
| `WALLET_AUTH_MODE` | `challenge_signature` | Режим проверки wallet-сессии vs fallback. |
| `ALLOW_X_USER_ID_FALLBACK` | `true` | Разрешить сценарий только с `X-User-Id` без Bearer-сессии (с ограничениями выше). |

## 8. Где смотреть код

- Заголовок и default: `bot/api/routes/activities.py` (`create_draft`).
- Аутентификация последующих шагов: `bot/api/utils/wallet_auth_guard.py`.
- Привязка upload к `user_id`: `bot/services/upload/upload_service.py` (`prepare`), `bot/services/upload/storage.py` (`prepare_upload_for_draft`).

---

**Методология:** выводы основаны на чтении кода роутов и сервисов (см. процесс анализа в `.cursor/commands/run-analysis.md` и `@analysis.mdc`).

**Версия:** привязка к репозиторию на момент добавления документа; при изменении роутов обновите этот файл и `api.md`.
