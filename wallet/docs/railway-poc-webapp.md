# Railway — POC web wallet (`wallet/webapp`)

Краткий runbook для **WAL-POC-4**. Полное руководство см. [`railway-guide.md`](railway-guide.md).

## Предусловия

- Репозиторий с подкаталогом **`wallet/webapp`** (Vite POC).
- Аккаунт [Railway](https://railway.app).

## Сервис

1. New Project → Deploy from GitHub (или CLI `railway init`).
2. **Root Directory:** `wallet/webapp` (если UI так настроен; иначе задайте в настройках сервиса).
3. **Build command:** `npm ci && npm run build`
4. **Start command:** `npm run start`  
   Скрипт `railway-start.mjs` / `vite preview` использует переменную **`PORT`**, которую выставляет Railway.

## Переменные (публичные)

| Variable | Назначение |
|----------|------------|
| `VITE_BOT_PUBLIC_URL` | Публичный URL бота (показывается в UI; не секрет) |
| `VITE_BUILD_TAG` | Опционально: метка релиза на экране |

Не задавайте приватные ключи с префиксом `VITE_` — они попадут в клиентский бандл. Секреты — только серверные переменные без `VITE_` или вне фронта (см. WAL-POC-5).

## Smoke после деплоя

```bash
curl -sI "https://<your-railway-url>/"
# ожидается 200
```

В браузере: заголовок «Amanita Wallet (POC)», блок с режимом и URL бота (если задан).

## Откат

Redeploy предыдущего деплоя в Railway Dashboard или откат коммита в ветке, откуда тянется деплой.
