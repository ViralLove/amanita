# 🚀 Amanita Wallet - DevOps Guide

## Полное руководство по разработке и деплою

### Содержание
1. [🏠 Локальная разработка](#-локальная-разработка)
2. [🚀 Production деплой на Railway](#-production-деплой-на-railway)
3. [🔧 Debug режим и логирование](#-debug-режим-и-логирование)
4. [📊 Мониторинг и проверка](#-мониторинг-и-проверка)
5. [🛠️ Troubleshooting](#️-troubleshooting)
6. [🔒 Безопасность](#-безопасность)

---

## 🏠 Локальная разработка

### Быстрый старт

#### 1. Создайте .env файл
```bash
# В корне проекта wallet/ создайте файл .env со следующим содержимым:
```

**Содержимое файла `.env`:**
```bash
# === ОСНОВНЫЕ НАСТРОЙКИ ===
NODE_ENV=development
DEBUG_MODE=true

# === НАСТРОЙКИ СЕРВЕРА ===
PORT=8080
```

#### 2. Запустите локальный сервер

**Вариант A: Python сервер с поддержкой .env (рекомендуется)**
```bash
cd wallet
python3 local-server.py
```

**Вариант B: Стандартный HTTP сервер**
```bash
cd wallet
python3 -m http.server 8080
```

#### 3. Откройте приложение
```
http://localhost:8080
```

### ✅ Что должно работать

После запуска вы увидите:
- ✅ **Debug кнопки** в правом верхнем углу ("🔍 Logs", "📋 Copy")
- ✅ **Debug панель** внизу экрана с логами
- ✅ **Детальное логирование** всех действий
- ✅ **CORS заголовки** для локальной разработки

### 🔧 Управление настройками

#### Изменение настроек
Отредактируйте файл `.env` и перезапустите сервер:
```bash
# Изменить debug режим
DEBUG_MODE=false  # Отключить логи в UI

# Изменить порт
PORT=3000  # Использовать другой порт
```

#### Переменные окружения
- `DEBUG_MODE=true/false` - включение/отключение debug режима
- `NODE_ENV=development/production` - окружение
- `PORT=8080` - порт сервера

---

## 🚀 Production деплой на Railway

### Подготовка

#### 1. Установка Railway CLI
```bash
npm install -g @railway/cli
railway login
```

#### 2. Создание проекта
```bash
cd wallet
railway init
# При запросе имени проекта ввести: Amanita-Wallet
```

#### 3. Создание Production окружения
```bash
railway environment new Production
railway environment Production
```

### Сборка и деплой

#### 1. Сборка Docker образа
```bash
# Собрать образ для linux/amd64
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .

# Загрузить в Docker Hub
docker push zeya88888888/amanita-wallet:latest
```

#### 2. Настройка Railway
```bash
# Установить переменную для Docker образа
railway variables --set "RAILWAY_DOCKER_IMAGE=zeya88888888/amanita-wallet:latest"

# Основные настройки
railway variables --set "NODE_ENV=production"
railway variables --set "PORT=8080"

# Debug режим (ВАЖНО для production!)
railway variables --set "DEBUG_MODE=false"  # Отключить логи в UI
```

#### 3. Деплой
```bash
railway up
```

#### 4. Получение URL
```bash
railway domain
```

### 📋 Чек-лист деплоя

#### ✅ Production деплой (рекомендуется)
```bash
# 1. Убедитесь, что debug отключен
railway variables --set "DEBUG_MODE=false"
railway variables --set "NODE_ENV=production"

# 2. Пересоберите образ
cd wallet
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .
docker push zeya88888888/amanita-wallet:latest

# 3. Деплой
railway up

# 4. Проверка
railway domain
```

#### 🔧 Debug деплой (только для тестирования!)
```bash
# 1. Включите debug (ВНИМАНИЕ: только для тестирования!)
railway variables --set "DEBUG_MODE=true"

# 2. Пересоберите образ
cd wallet
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .
docker push zeya88888888/amanita-wallet:latest

# 3. Деплой
railway up

# 4. Тестирование
# Откройте URL - должны быть видны кнопки "🔍 Logs" и "📋 Copy"

# 5. ОБЯЗАТЕЛЬНО отключите debug после тестирования!
railway variables --set "DEBUG_MODE=false"
railway up
```

---

## 🔧 Debug режим и логирование

### Способы включения Debug режима

#### 1. Автоматическое определение (рекомендуется)
Debug режим **автоматически включается** для:
- `localhost` и `127.0.0.1`
- Локальной разработки

#### 2. Локальная разработка с .env файлом
```bash
# В .env файле
DEBUG_MODE=true
```

#### 3. URL параметр
```
https://amanita-wallet-wallet.up.railway.app/?debug=true
```

#### 4. LocalStorage (для тестирования)
В консоли браузера:
```javascript
localStorage.setItem('amanita_debug', 'true');
location.reload();
```

#### 5. Railway переменные окружения (production)
```bash
# Включить debug для production
railway variables --set "DEBUG_MODE=true"

# Отключить debug (по умолчанию)
railway variables --set "DEBUG_MODE=false"
```

### 🎯 Проверка результата

#### Production режим ✅
- ❌ Нет кнопок логов в правом верхнем углу
- ❌ Нет debug панели внизу
- ✅ Чистый интерфейс

#### Debug режим 🔧
- ✅ Видны кнопки "🔍 Logs" и "📋 Copy"
- ✅ Debug панель внизу экрана
- ✅ Детальные логи в консоли

### 🚨 Важно!

**НИКОГДА не оставляйте DEBUG_MODE=true в production!**

После тестирования обязательно выполните:
```bash
railway variables --set "DEBUG_MODE=false"
railway up
```

---

## 📊 Мониторинг и проверка

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

### Ожидаемые результаты

#### В логах должны появиться:
```
nginx: [notice] 1#1: start worker processes
nginx: [notice] 1#1: start worker process 7
nginx: [notice] 1#1: start worker process 8
```

#### При обращении к WebApp:
```
GET / HTTP/1.1" 200
GET /styles.css HTTP/1.1" 200
GET /main.js HTTP/1.1" 200
GET /localization/ru.json HTTP/1.1" 200
```

---

## 🛠️ Troubleshooting

### Проблемы локальной разработки

#### Проблема: Debug кнопки не видны
**Решение:**
1. Проверьте, что `DEBUG_MODE=true` в `.env`
2. Убедитесь, что вы на `localhost:8080`
3. Перезапустите сервер

#### Проблема: Сервер не запускается
**Решение:**
```bash
# Проверьте, что порт свободен
lsof -i :8080

# Используйте другой порт
PORT=3000 python3 local-server.py
```

### Проблемы деплоя

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
1. Создайте образ с уникальным тегом: `docker build -t zeya88888888/amanita-wallet:$(date +%Y%m%d-%H%M%S) .`
2. Обновите переменную `RAILWAY_DOCKER_IMAGE`
3. Принудительно перезапустите деплой

---

## 🔒 Безопасность

### Настроенные меры безопасности

- ✅ **HTTPS принудительно** - Telegram WebApp требует защищенное соединение
- ✅ **CSP заголовки** для защиты от XSS
- ✅ **X-Frame-Options** для защиты от clickjacking
- ✅ **X-Content-Type-Options** против MIME sniffing
- ✅ **Gzip сжатие** для производительности
- ✅ **Кэширование** статических ресурсов
- ✅ **DEBUG_MODE=false** в production

### Переменные безопасности

```bash
# Основные настройки безопасности
railway variables --set "CSP_ENABLED=true"
railway variables --set "HTTPS_ONLY=true"

# CORS настройки
railway variables --set "CORS_ORIGIN=https://t.me"
railway variables --set "CORS_CREDENTIALS=true"
```

---

## 📱 Telegram WebApp интеграция

### Поддерживаемые режимы

- `mode=create_new` - создание нового кошелька
- `mode=recovery_only` - только восстановление
- `mode=view_seed` - просмотр сид-фразы
- `mode=sign_tx` - подписание транзакции

### Примеры URL

- `https://ваш-домен.railway.app?mode=create_new&invite_verified=true`
- `https://ваш-домен.railway.app?mode=recovery_only`
- `https://ваш-домен.railway.app?mode=view_seed`

### Настройка в Telegram Bot

1. **WebApp URL:** `https://ваш-домен.railway.app`
2. **WebApp Name:** `Amanita Wallet`
3. **WebApp Description:** `Создание и управление Ethereum кошельками`

---

## 🎯 Результат

### После успешного деплоя:
- ✅ WebApp доступен по HTTPS
- ✅ Интеграция с Telegram Bot
- ✅ Все ресурсы загружаются
- ✅ Безопасность настроена
- ✅ Производительность оптимизирована
- ✅ Debug режим отключен в production

### Структура файлов

```
wallet/
├── Dockerfile              # Docker конфигурация
├── nginx.conf              # Nginx конфигурация
├── railway.json            # Railway конфигурация
├── local-server.py         # Локальный сервер с .env поддержкой
├── local.env.template      # Шаблон .env файла
├── .env                    # Локальные переменные (создать вручную)
├── deploy.sh               # Скрипт автоматического деплоя
└── docs/
    ├── DEVOPS_GUIDE.md     # Этот файл
    ├── debug-configuration.md
    ├── railway-guide.md
    └── DEPLOYMENT.md
```

---

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `railway logs`
2. Проверьте статус: `railway status`
3. Проверьте переменные: `railway variables`
4. Обратитесь к соответствующим разделам этого руководства

---

## Полезные ссылки

- [Railway Dashboard](https://railway.app/dashboard)
- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [Docker Hub](https://hub.docker.com/r/zeya88888888/amanita-wallet)
- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)
