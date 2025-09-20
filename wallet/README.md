# 🍄 Amanita Wallet

**Telegram WebApp для создания и управления Ethereum кошельками**

## 🚀 Быстрый старт

### Локальная разработка
```bash
# 1. Создайте .env файл в корне проекта
cp local.env.template .env

# 2. Запустите локальный сервер
python3 local-server.py

# 3. Откройте http://localhost:8080
```

### Production деплой
```bash
# 1. Соберите Docker образ
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .

# 2. Загрузите в Docker Hub
docker push zeya88888888/amanita-wallet:latest

# 3. Деплой на Railway
railway up
```

## 📚 Документация

### 🎯 Основные руководства
- **[DEVOPS_GUIDE.md](./docs/DEVOPS_GUIDE.md)** - **Полное руководство по DevOps** (рекомендуется)

### 🔧 Техническая документация
- [debug-configuration.md](./docs/debug-configuration.md) - Настройка debug режима
- [railway-guide.md](./docs/railway-guide.md) - Детальное руководство по Railway

## 🏗️ Архитектура

### Frontend
- **Vanilla JavaScript** - без фреймворков
- **ethers.js** - для работы с Ethereum
- **Telegram WebApp API** - интеграция с Telegram
- **Responsive CSS** - адаптивный дизайн

### Backend
- **Nginx** - веб-сервер
- **Docker** - контейнеризация
- **Railway** - хостинг

### Безопасность
- **HTTPS** - принудительное шифрование
- **CSP заголовки** - защита от XSS
- **CORS** - настройка для Telegram
- **Debug режим** - отключен в production

## 🎯 Возможности

### Создание кошелька
- Генерация мнемонической фразы
- Создание Ethereum адреса
- Установка PIN-кода

### Восстановление кошелька
- Ввод мнемонической фразы
- Восстановление адреса
- Проверка корректности

### Управление
- Просмотр баланса
- Отправка транзакций
- История операций

## 🔧 Debug режим

### Включение
- **Локально**: автоматически для `localhost`
- **Production**: `railway variables --set "DEBUG_MODE=true"`
- **URL**: `?debug=true`
- **LocalStorage**: `amanita_debug=true`

### Отключение
- **Production**: `railway variables --set "DEBUG_MODE=false"`
- **LocalStorage**: `localStorage.removeItem('amanita_debug')`

## 🚨 Важно!

**НИКОГДА не оставляйте DEBUG_MODE=true в production!**

## 📱 Telegram WebApp

### Поддерживаемые режимы
- `mode=create_new` - создание нового кошелька
- `mode=recovery_only` - только восстановление
- `mode=view_seed` - просмотр сид-фразы
- `mode=sign_tx` - подписание транзакции

### Примеры URL
- `https://ваш-домен.railway.app?mode=create_new&invite_verified=true`
- `https://ваш-домен.railway.app?mode=recovery_only`

## 🛠️ Troubleshooting

### Проблемы локальной разработки
- **Debug кнопки не видны**: проверьте `DEBUG_MODE=true` в `.env`
- **Сервер не запускается**: проверьте свободность порта

### Проблемы деплоя
- **WebApp не открывается**: проверьте HTTPS и доступность домена
- **Ошибки загрузки**: проверьте копирование файлов в Docker
- **CSP блокирует скрипты**: проверьте настройки безопасности

## 📊 Мониторинг

```bash
# Статус Railway
railway status

# Логи
railway logs --follow

# Переменные окружения
railway variables
```

## 🔒 Безопасность

### Настроенные меры
- ✅ HTTPS принудительно
- ✅ CSP заголовки
- ✅ X-Frame-Options
- ✅ X-Content-Type-Options
- ✅ Gzip сжатие
- ✅ Кэширование

## 📚 Полезные ссылки

- [Railway Dashboard](https://railway.app/dashboard)
- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [Docker Hub](https://hub.docker.com/r/zeya88888888/amanita-wallet)
- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [ethers.js Documentation](https://docs.ethers.io/)

---

**Для подробной информации см. [DEVOPS_GUIDE.md](./docs/DEVOPS_GUIDE.md)**