## Task: refactor — опциональная загрузка секретов из Vault для polygon профиля

### Цель
Убрать жесткую привязку `DEPLOYMENT_PROFILE=polygon -> только Vault`, чтобы production на Polygon мог работать в двух валидных режимах:
1) через Vault (предпочтительно),
2) через env fallback (осознанно и явно включаемо).

### Почему это важно (риск)
Сейчас сервис падает на старте при любом `polygon`, если не задан `VAULT_ADDR`/`VAULT_TOKEN`, даже когда рабочие ключи уже есть в Railway Variables. Это создает deployment lock и увеличивает MTTR.

### Вне scope
- Не меняем логику Web3/ABI загрузки.
- Не делаем миграцию секретов между хранилищами.
- Не удаляем поддержку Vault.

---
**Приоритет:** P0  
**Сложность:** M  
**Оценка времени:** 0.5 дня  
**Статус:** in progress (bullrun / implementation)  
**Тэги:** config, secrets, vault, railway, polygon  
**Лог фаз:** [BULLRUN-PHASE-LOG.md](./BULLRUN-PHASE-LOG.md)
---

## Факты из кода (Code Facts / SSOT)

### 1) Ветка polygon сейчас форсит Vault и падает fail-fast
- `bot/config.py`
  - при `DEPLOYMENT_PROFILE == "polygon"` вызывается `_load_secrets_from_vault()`;
  - при отсутствии `VAULT_ADDR`/`VAULT_TOKEN` выбрасывается `VaultServiceError`.
- Следствие: старт приложения блокируется до инициализации Web3.

### 2) Для localhost есть рабочий путь чтения ключей из env
- `bot/config.py`
  - в ветке `else` читаются `SELLER_PRIVATE_KEY` и `ARWEAVE_PRIVATE_KEY` из env;
  - для `SELLER_PRIVATE_KEY` есть нормализация `0x`.

### 3) Vault-переменные и логика официально описаны как production-сценарий
- `bot/services/vault_service.py`:
  - ожидает `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_PATH`;
  - читает ключи через `hvac` из KV v2.
- `bot/docs/tech/VAULT_SETUP.md`, `bot/docs/tech/VAULT_RAILWAY_SETUP.md`:
  - явно задают модель `polygon -> Vault`.

## Gap / Проблема
Текущая архитектура не поддерживает controlled fallback при `polygon`:
- либо полный Vault, либо hard-fail;
- нет отдельного feature-flag для включения/требования Vault;
- `DEPLOYMENT_PROFILE` одновременно выполняет две роли: network intent и источник секретов.

## AC/DoD
- [x] (P0) Источник секретов управляется отдельной переменной (`SECRETS_PROVIDER=vault|env`); если не задан — inferred: `polygon`→`vault`, иначе→`env` (см. лог).
- [x] (P0) При `SECRETS_PROVIDER=vault` и отсутствии обязательных `VAULT_*` приложение падает с понятной ошибкой (fail-fast).
- [x] (P0) При `SECRETS_PROVIDER=env` на `polygon` ключи читаются из env без требования `VAULT_*`.
- [x] (P1) В логах явно указан выбранный provider (явный или inferred).
- [x] (P1) Обновлены `.env.example`, `vault-simple-manual.md`, `api-key-encryption-key.md` §9.
- [x] (P1) Smoke: импорт `config` с `SECRETS_PROVIDER=env` + `DEPLOYMENT_PROFILE=polygon`; с `vault` без `VAULT_ADDR` — `VaultServiceError`.

## Где менять код

### Runtime
- `bot/config.py`
  - выделить отдельный selector источника секретов (`SECRETS_PROVIDER`);
  - декомпозировать загрузку секретов в унифицированный resolver;
  - унифицировать валидацию обязательных переменных на выбранном provider.

### Документация
- `bot/.env.example`
  - добавить/обновить секцию `SECRETS_PROVIDER`, `DEPLOYMENT_PROFILE`, `VAULT_*`.
- `bot/docs/tech/api/vault-simple-manual.md`
  - добавить matrix «Vault mode vs Env mode».
- `bot/docs/tech/api/api-key-encryption-key.md`
  - синхронизировать раздел про `VAULT_*` с новой моделью.

### (Опционально) тесты
- `bot/tests/...` (новый модуль конфиг-тестов)
  - unit smoke для выбора provider и условий fail-fast.

## План выполнения (Execution Plan)

1) Спроектировать модель выбора источника секретов
- Ввести `SECRETS_PROVIDER` (`vault`/`env`) c явным default.
- Уточнить поведение по умолчанию для production.

2) Рефактор `config.py`
- Вынести `_load_secrets_from_env()` отдельно от ветки localhost.
- Сделать dispatcher по provider.
- Сохранить текущую нормализацию `SELLER_PRIVATE_KEY`.

3) Логирование и ошибки
- Добавить четкий info-лог выбранного provider.
- Для `vault` сохранить понятные сообщения по отсутствию `VAULT_ADDR`/`VAULT_TOKEN`.

4) Обновить документацию и примеры env
- Описать два валидных сценария запуска на Polygon.
- Указать риски `env`-режима и рекомендованный `vault`-режим.

5) Проверка
- Прогнать smoke в двух профилях:
  - `SECRETS_PROVIDER=env` + `DEPLOYMENT_PROFILE=polygon`;
  - `SECRETS_PROVIDER=vault` + корректные `VAULT_*`.

## Команды проверки (Verification Commands)

```bash
# 1) Быстрый импорт конфига (режим env)
SECRETS_PROVIDER=env DEPLOYMENT_PROFILE=polygon python -c "import config; print('ok-env')"

# 2) Проверка fail-fast (режим vault без VAULT_ADDR)
SECRETS_PROVIDER=vault DEPLOYMENT_PROFILE=polygon python -c "import config"

# 3) Запуск приложения после изменений
cd bot && python main.py
```

Ожидаемо:
- команда (1) проходит при наличии `SELLER_PRIVATE_KEY`/`ARWEAVE_PRIVATE_KEY`;
- команда (2) падает с осмысленным `VaultServiceError`;
- в логах явно указан выбранный источник секретов.

## Риски и подводные камни
- Риск незаметного понижения security при default=`env` в production.
- Риск рассинхрона документации и фактических env-переменных.
- Риск двойной интерпретации `DEPLOYMENT_PROFILE` (нужно документально развести назначения).

