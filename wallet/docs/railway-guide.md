# Railway Deployment Guide для Amanita WebApp

**POC (текущий репозиторий, `wallet/webapp`):** краткий runbook — [`railway-poc-webapp.md`](railway-poc-webapp.md).

## Полное руководство по развертыванию Amanita WebApp на Railway.com

### Содержание
1. [Полная переустановка Railway](#полная-переустановка-railway)
2. [Создание нового проекта](#создание-нового-проекта)
3. [Настройка окружения](#настройка-окружения)
4. [Docker образ](#docker-образ)
5. [Переменные окружения](#переменные-окружения)
6. [Проверка и мониторинг](#проверка-и-мониторинг)
7. [Интеграция с Telegram Bot](#интеграция-с-telegram-bot)

---

## Полная переустановка Railway

### 1. Удаление всех проектов

**ВНИМАНИЕ:** Удаление проектов через CLI НЕ ПОДДЕРЖИВАЕТСЯ. Выполняется вручную через Railway Dashboard:

1. Откройте https://railway.app/dashboard
2. Перейдите в каждый проект
3. Нажмите Settings → Delete Project

### 2. Создание нового проекта Amanita-WebApp

```bash
# Создать новый проект
railway init

# При запросе имени проекта ввести: Amanita-WebApp
```

### 3. Создание новой среды Production

```bash
# Создать новое окружение
railway environment new Production

# Подключиться к новому окружению
railway environment Production
```

---

## Docker образ

### Создание и загрузка Docker образа

```bash
# Перейти в директорию webapp
cd webapp

# Собрать Docker образ для linux/amd64
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .

# Загрузить в Docker Hub
docker push zeya88888888/amanita-wallet:latest
```

### Настройка Railway для использования Docker образа

```bash
# Установить переменную для Docker образа
railway variables --set "RAILWAY_DOCKER_IMAGE=zeya88888888/amanita-wallet:latest"

# Загрузить и задеплоить проект
railway up
```

---

## Переменные окружения

### Основные переменные для WebApp

```bash
# Основные настройки
railway variables --set "NODE_ENV=production"
railway variables --set "PORT=8080"

# Telegram WebApp (опционально, для диагностики)
railway variables --set "TELEGRAM_BOT_TOKEN=ваш_токен_для_тестирования"

# CORS настройки (если нужны)
railway variables --set "CORS_ORIGIN=https://t.me"
railway variables --set "CORS_CREDENTIALS=true"
```

### Переменные для интеграции с ботом

```bash
# URL WebApp для бота (будет получен после деплоя)
railway variables --set "WALLET_APP_URL=https://ваш-домен.railway.app"

# Настройки безопасности
railway variables --set "CSP_ENABLED=true"
railway variables --set "HTTPS_ONLY=true"

# Debug режим (ВАЖНО для production!)
railway variables --set "DEBUG_MODE=false"  # Отключить логи в UI
railway variables --set "NODE_ENV=production"
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

### Проверка работоспособности WebApp

```bash
# Получить URL приложения
railway domain

# Проверить доступность
curl -I https://ваш-домен.railway.app

# Проверить healthcheck
curl https://ваш-домен.railway.app/health
```

---

## Интеграция с Telegram Bot

### 1. Получение URL WebApp

После успешного деплоя получите URL вашего WebApp:

```bash
# Получить домен
railway domain

# Пример результата: https://amanita-webapp-production.railway.app
```

### 2. Настройка в Telegram Bot

В настройках вашего Telegram бота:

1. **WebApp URL:** `https://ваш-домен.railway.app`
2. **WebApp Name:** `Amanita Wallet`
3. **WebApp Description:** `Создание и управление Ethereum кошельками`

### 3. Тестирование интеграции

```bash
# Проверить доступность из Telegram
# Откройте бота в Telegram и нажмите кнопку WebApp

# Проверить логи при обращении из Telegram
railway logs --follow
```

### 4. Обновление переменных бота

```bash
# В проекте бота обновить переменную
railway variables --set "WALLET_APP_URL=https://ваш-домен.railway.app"
```

---

## 🔧 Debug режим

### Управление логами

**Production (рекомендуется):**
```bash
railway variables --set "DEBUG_MODE=false"
```

**Временное включение для отладки:**
```bash
railway variables --set "DEBUG_MODE=true"
# ... тестирование ...
railway variables --set "DEBUG_MODE=false"  # Обязательно отключить!
```

### Проверка режима
- **Production**: Логи и debug кнопки скрыты
- **Debug**: Видны кнопки "🔍 Logs" и "📋 Copy" в правом верхнем углу

📚 **Подробнее:** [debug-configuration.md](./debug-configuration.md)

## Важные замечания

### ⚠️ Критические моменты

1. **HTTPS обязательно** - Telegram WebApp требует защищенное соединение
2. **CORS настройки** - правильно настроены для Telegram
3. **CSP заголовки** - настроены для безопасности
4. **Статические файлы** - все ресурсы должны быть доступны
5. **DEBUG_MODE=false** - обязательно для production!

### 🔧 Troubleshooting

#### Проблема: WebApp не открывается в Telegram
**Решение:** 
1. Проверьте, что URL начинается с `https://`
2. Убедитесь, что домен доступен: `curl -I https://ваш-домен.railway.app`
3. Проверьте логи: `railway logs`

#### Проблема: Ошибки загрузки ресурсов
**Решение:**
1. Проверьте, что все файлы скопированы в контейнер
2. Убедитесь в правильности путей в nginx.conf
3. Проверьте MIME-типы в nginx

#### Проблема: CSP блокирует скрипты
**Решение:**
1. Проверьте Content-Security-Policy в nginx.conf
2. Убедитесь, что все CDN разрешены
3. Проверьте логи браузера на ошибки CSP

#### Проблема: Railway не использует новый Docker образ
**Решение:** 
1. Создайте образ с уникальным тегом: `docker build -t zeya88888888/amanita-webapp:$(date +%Y%m%d-%H%M%S) .`
2. Обновите переменную `RAILWAY_DOCKER_IMAGE`
3. Принудительно перезапустите деплой

### 🎯 Ожидаемый результат

После выполнения всех шагов:
- ✅ Новый проект "Amanita-WebApp" 
- ✅ Окружение "Production"
- ✅ Docker образ с Nginx
- ✅ Рабочее WebApp без ошибок
- ✅ HTTPS доступность
- ✅ Интеграция с Telegram Bot

### 📊 Проверка успешного деплоя

В логах должны появиться:
```
nginx: [notice] 1#1: start worker processes
nginx: [notice] 1#1: start worker process 7
nginx: [notice] 1#1: start worker process 8
```

При обращении к WebApp:
```
GET / HTTP/1.1" 200
GET /styles.css HTTP/1.1" 200
GET /main.js HTTP/1.1" 200
GET /localization/ru.json HTTP/1.1" 200
```

### 🔒 Безопасность

**Настроенные меры безопасности:**
- ✅ HTTPS принудительно
- ✅ CSP заголовки для защиты от XSS
- ✅ X-Frame-Options для защиты от clickjacking
- ✅ X-Content-Type-Options против MIME sniffing
- ✅ Gzip сжатие для производительности
- ✅ Кэширование статических ресурсов

### 📱 Telegram WebApp функции

**Поддерживаемые режимы:**
- `mode=create_new` - создание нового кошелька
- `mode=recovery_only` - только восстановление
- `mode=view_seed` - просмотр сид-фразы
- `mode=sign_tx` - подписание транзакции

**Примеры URL:**
- `https://ваш-домен.railway.app?mode=create_new&invite_verified=true`
- `https://ваш-домен.railway.app?mode=recovery_only`
- `https://ваш-домен.railway.app?mode=view_seed`

---

## 📚 Дополнительная документация

- [DEVOPS_GUIDE.md](./DEVOPS_GUIDE.md) - **Полное руководство по DevOps** (рекомендуется)
- [debug-configuration.md](./debug-configuration.md) - Настройка debug режима

## Полезные ссылки

- [Railway Dashboard](https://railway.app/dashboard)
- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [Docker Hub](https://hub.docker.com/r/zeya88888888/amanita-wallet)
- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)

---

## Быстрый старт

```bash
# 1. Создать проект
railway init

# 2. Собрать и загрузить образ
docker build -t zeya88888888/amanita-webapp:latest .
docker push zeya88888888/amanita-webapp:latest

# 3. Настроить Railway
railway variables --set "RAILWAY_DOCKER_IMAGE=zeya88888888/amanita-webapp:latest"
railway up

# 4. Получить URL
railway domain

# 5. Настроить в Telegram Bot
# URL: https://ваш-домен.railway.app
```

**Готово! WebApp доступен в Telegram Bot! 🚀**
