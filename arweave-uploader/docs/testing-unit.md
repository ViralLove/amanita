# Unit-тесты arweave-uploader

Методология: **@unit-test-build** (Phase 1 → Smoke → Real → Strategic).

## Запуск

```bash
# из корня arweave-uploader
npm run test:unit
# или
node --test 'tests/unit/*.test.js'
```

Для тестов `config` и `server` нужен валидный JWK в окружении. В тестах используется фикстура `tests/fixtures/minimal-jwk.json`; при запуске через `npm run test:unit` переменные задаются в `beforeEach` (для изолированных тестов).

## Структура

| Каталог/файл | Назначение |
|--------------|------------|
| `tests/unit/*.test.js` | Юнит-тесты по модулям dist/ |
| `tests/helpers/env.js` | Сохранение/восстановление env для изоляции |
| `tests/fixtures/minimal-jwk.json` | Минимальный JWK для loadConfig в тестах |
| `tests/fixtures/jwt-upload-token.js` | RSA-ключи и подписанный JWT (RS256) для verifyUploadToken |
| `tests/fixtures/valid-data-item.js` | Минимальный валидный ANS-104 Data Item с тегом Upload-Id |
| `tests/fixtures/deep-hash-vectors.json` | Эталоны deepHash (sha256, referenceSha384). Ссылки на источники в файле. |

## Модули

- **logging** — sha256Hex, logInfo/logWarn/logError, errorToMessage
- **auth** — isAuthorized (Bearer, relayAuthToken)
- **config** — loadConfig (port, arweave*, jwk)
- **arweave-client** — ArweaveClient (инициализация, arweave/jwk для bundleAndPublish)
- **publish/backend-calls** — normalizeMockStatus, putStatus, postCallback (mock)
- **publish/validate-token** — verifyUploadToken (token_invalid)
- **publish/validate-data-item** — validateDataItem (signature_invalid)
- **publish/deep-hash** — deepHash (blob/list). См. ниже «Зачем тестируем deepHash».
- **publish/bundle-publish** — bundleAndPublish (error path)
- **server** — buildApp, GET /health, POST /v1/crystalize (400/401)

## Критерии (Gate 3)

- Тесты проверяют реальное поведение (коды ответа, форма тела, валидация).
- Критичные пути: валидация body, токен, data item, маршруты server.
- Mock только для внешних систем (Backend, Arweave); env изолирован через helpers.

## Интеграционные тесты

Сводные сценарии crystalize (token_invalid, missing fields, signature_invalid): `tests/publish-flow.test.js`. Запуск: `node tests/publish-flow.test.js` (требуют ARWEAVE_PRIVATE_KEY и BACKEND_USE_MOCK=true).

Успешный путь crystalize (валидный JWT + валидный Data Item → bundle + callback) покрывается интеграционными или e2e тестами, не unit.

## Зачем тестируем deepHash

**Где используется:** только в `publish/validate-data-item.js`. При приходе `POST /v1/crystalize` с полем `signed_data_item` (base64 ANS-104 Data Item) мы должны проверить подпись: по спецификации ANS-104 сообщение для подписи = `deepHash(["dataitem", "1", owner, target, anchor, tags, data])`. Без корректного deepHash верификация подписи неверна — мы либо отклоним валидные items, либо примем поддельные.

**ArweaveClient:** не использует deepHash. Он предоставляет только `arweave` и `jwk` для `bundleAndPublish` (подпись bundle-транзакции). Верификация входящего Data Item выполняется в `validateDataItem` с помощью deepHash.

**Bulk upload:** сейчас один запрос = один Data Item = один bundle из одного item. «Bulk» в смысле «много items в одном bundle» потребовал бы расширения `bundle-publish.js` (несколько items в одном bundle), но верификация каждого item по-прежнему нужна — и для неё нужен deepHash. То есть от тестов deepHash отказываться не стоит: они гарантируют, что мы правильно проверяем входящие Data Items.
