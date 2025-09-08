# Railway Deployment Guide

## Полное руководство по развертыванию Amanita Bot на Railway.com

### Содержание
1. [Полная переустановка Railway](#полная-переустановка-railway)
2. [Создание нового проекта](#создание-нового-проекта)
3. [Настройка окружения](#настройка-окружения)
4. [Docker образ](#docker-образ)
5. [Переменные окружения](#переменные-окружения)
6. [Проверка и мониторинг](#проверка-и-мониторинг)

---

## Полная переустановка Railway

### 1. Удаление всех проектов

**ВНИМАНИЕ:** Удаление проектов через CLI НЕ ПОДДЕРЖИВАЕТСЯ. Выполняется вручную через Railway Dashboard:

1. Откройте https://railway.app/dashboard
2. Перейдите в каждый проект
3. Нажмите Settings → Delete Project

### 2. Создание нового проекта Amanita

```bash
# Создать новый проект
railway init

# При запросе имени проекта ввести: Amanita
```

### 3. Создание новой среды Iveta

```bash
# Создать новое окружение
railway environment new Iveta

# Подключиться к новому окружению
railway environment Iveta
```

---

## Docker образ

### Создание и загрузка Docker образа

```bash
# Собрать Docker образ для linux/amd64
docker build --platform linux/amd64 -t zeya88888888/amanita-bot:latest .

# Загрузить в Docker Hub
docker push zeya88888888/amanita-bot:latest
```

### Настройка Railway для использования Docker образа

```bash
# Установить переменную для Docker образа
railway variables --set "RAILWAY_DOCKER_IMAGE=zeya88888888/amanita-bot:latest"

# Загрузить и задеплоить проект
railway up
```

---

## Переменные окружения

### Основные переменные

```bash
# Telegram Bot
railway variables --set "TELEGRAM_BOT_TOKEN=ваш_токен"

# Blockchain
railway variables --set "SELLER_ADDRESS=0x831436618ec3E727f823f3690e7C04286cEEd418"
railway variables --set "SELLER_PRIVATE_KEY=ваш_приватный_ключ"
railway variables --set "AMANITA_REGISTRY_CONTRACT_ADDRESS=0x03cAc913A5e527CEf15E7d3bdb40Cc7F7dac5867"
railway variables --set "INVITE_NFT_CONTRACT_ADDRESS=0xA3A27041F22E7cc5F4EB49054780a9bD71571799"
railway variables --set "PRODUCT_REGISTRY_CONTRACT_ADDRESS=0xc02C17Ee72A21E4c5eB9822a90Fb3BE1024144ED"
railway variables --set "BLOCKCHAIN_PROFILE=mainnet"
railway variables --set "WEB3_PROVIDER_URI=https://polygon-rpc.com"

# Storage
railway variables --set "STORAGE_TYPE=pinata"
railway variables --set "INTEGRATION_STORAGE=mock"

# API
railway variables --set "AMANITA_API_URL=http://localhost:8000"
railway variables --set "WALLET_APP_URL=https://ваш_ngrok_домен.ngrok-free.app"
```

### Pinata Storage (если используется)

```bash
railway variables --set "PINATA_API_KEY=ваш_pinata_api_key"
railway variables --set "PINATA_API_SECRET=ваш_pinata_api_secret"
railway variables --set "PINATA_JWT=ваш_pinata_jwt"
railway variables --set "STORAGE_COMMUNICATION_MODE=sync"
```

### API Keys

```bash
railway variables --set "AMANITA_API_KEY=ak_seller_node_amanita_iveta_launch_september_2025"
railway variables --set "AMANITA_API_SECRET=wearethegalacticfederationoflightandwecamewithpeacenowpeopleonearthcanseeandcommunicatewithus888"
railway variables --set "AMANITA_API_HMAC_SECRET_KEY=9170884a1ba617780cce44458248c21d085d8ddb18d4440ff4534445102d1b88"
```

---

## Проверка и мониторинг

### Проверка статуса

```bash
# Проверить статус
railway status

# Посмотреть логи
railway logs

# Проверить переменные
railway variables
```

### Мониторинг деплоя

```bash
# Перезапустить деплой
railway redeploy

# Посмотреть логи в реальном времени
railway logs --follow
```

---

## Важные замечания

### ⚠️ Критические моменты

1. **Удаление проектов** - только через Railway Dashboard
2. **Docker образ** - убедитесь, что `artifacts/` папка находится в `bot/` директории
3. **Переменные окружения** - замените `ваш_токен` и `ваш_приватный_ключ` на реальные значения
4. **Порядок выполнения** - строго по порядку, не пропускать шаги

### 🔧 Troubleshooting

#### Проблема: FileNotFoundError для ABI файлов
**Решение:** Убедитесь, что папка `artifacts/` скопирована в `bot/` директорию перед сборкой Docker образа.

#### Проблема: Railway не использует новый Docker образ
**Решение:** 
1. Создайте образ с уникальным тегом: `docker build -t zeya88888888/amanita-bot:$(date +%Y%m%d-%H%M%S) .`
2. Обновите переменную `RAILWAY_DOCKER_IMAGE`
3. Принудительно перезапустите деплой

#### Проблема: Railway CLI не работает с промптами
**Решение:** Используйте Railway Dashboard для интерактивных операций.

### 🎯 Ожидаемый результат

После выполнения всех шагов:
- ✅ Новый проект "Amanita" 
- ✅ Окружение "Iveta"
- ✅ Docker образ с ABI файлами
- ✅ Рабочее приложение без ошибок `FileNotFoundError`
- ✅ Успешное подключение к Polygon Mainnet
- ✅ Загруженные контракты реестра

### 📊 Проверка успешного деплоя

В логах должны появиться:
```
[ABI] Проверка путей для AmanitaRegistry:
- Hardhat: /artifacts/contracts/AmanitaRegistry.sol/AmanitaRegistry.json ✅
[Web3] Загружен контракт реестра: 0x03cAc913A5e527CEf15E7d3bdb40Cc7F7dac5867
[Web3] Успешное подключение к https://polygon-rpc.com
```

---

## Полезные ссылки

- [Railway Dashboard](https://railway.app/dashboard)
- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [Docker Hub](https://hub.docker.com/r/zeya88888888/amanita-bot)
