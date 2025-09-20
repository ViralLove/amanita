# 🔧 Конфигурация Debug режима

## Обзор

Система управления логами и отладочной информацией в Amanita Wallet настроена для автоматического переключения между режимами разработки и production.

## 🎯 Режимы работы

### Production режим (по умолчанию)
- ❌ Логи в UI отключены
- ❌ Debug кнопки скрыты
- ❌ Debug панель скрыта
- ✅ Только console.log в DevTools

### Debug режим
- ✅ Логи в UI включены
- ✅ Debug кнопки видны
- ✅ Debug панель доступна
- ✅ Детальное логирование

## 🚀 Способы включения Debug режима

### 1. Автоматическое определение (рекомендуется)
Debug режим **автоматически включается** для:
- `localhost` и `127.0.0.1`
- Локальной разработки

### 2. Локальная разработка с .env файлом
Создайте файл `.env` в корне проекта:
```bash
# Скопируйте содержимое из local.env.template
cp local.env.template .env
```

Содержимое `.env` файла:
```bash
NODE_ENV=development
DEBUG_MODE=true
PORT=8080
CORS_ORIGIN=http://localhost:8080
CORS_CREDENTIALS=true
CSP_ENABLED=true
HTTPS_ONLY=false
LOG_LEVEL=debug
ENABLE_DEVTOOLS=true
```

Запуск локального сервера:
```bash
# Простой Python сервер
python3 local-server.py

# Или стандартный HTTP сервер
python3 -m http.server 8080
```

### 3. URL параметр
```
https://amanita-wallet-wallet.up.railway.app/?debug=true
```

### 4. LocalStorage (для тестирования)
В консоли браузера:
```javascript
localStorage.setItem('amanita_debug', 'true');
location.reload();
```

### 5. Railway переменные окружения (production)
```bash
# Включить debug для production
railway variables --set "DEBUG_MODE=true"

# Отключить debug (по умолчанию)
railway variables --set "DEBUG_MODE=false"
```

## 📋 Инструкции для деплоя

### Для Production деплоя
```bash
# 1. Убедитесь, что DEBUG_MODE=false (по умолчанию)
railway variables --set "DEBUG_MODE=false"
railway variables --set "NODE_ENV=production"

# 2. Пересоберите и деплойте
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .
docker push zeya88888888/amanita-wallet:latest
railway up
```

### Для Debug деплоя (временное тестирование)
```bash
# 1. Включите debug режим
railway variables --set "DEBUG_MODE=true"

# 2. Пересоберите и деплойте
docker build --platform linux/amd64 -t zeya88888888/amanita-wallet:latest .
docker push zeya88888888/amanita-wallet:latest
railway up
```

## 🔍 Проверка режима

### В браузере
Откройте консоль DevTools:
- **Production**: `🚀 Production режим - логи отключены`
- **Debug**: `🔧 Debug режим включен`

### В Railway логах
```bash
railway logs --follow
```

## 🎛️ Управление логами в Debug режиме

### Кнопки управления
- **🔍 Logs** - показать/скрыть debug панель
- **📋 Copy** - скопировать все логи в буфер обмена

### Debug панель
- Отображается внизу экрана
- Автоматическая прокрутка
- Цветовая индикация ошибок
- Максимальная высота: 100px

## 🛠️ Технические детали

### Файлы конфигурации
- `main.js` - логика определения DEBUG_MODE
- `index.html` - управление видимостью UI элементов
- `Dockerfile` - создание config.js с переменными окружения

### Приоритет определения режима
1. Railway переменная `DEBUG_MODE`
2. Localhost/127.0.0.1
3. URL параметр `debug=true`
4. LocalStorage `amanita_debug=true`

### Переменные окружения
```bash
DEBUG_MODE=true|false    # Включение debug режима
NODE_ENV=production      # Окружение (production/development)
```

## 🚨 Важные замечания

### Безопасность
- ⚠️ **Никогда не включайте DEBUG_MODE=true в production** без необходимости
- ✅ Debug режим автоматически отключается для production доменов
- ✅ Логи содержат только техническую информацию, не чувствительные данные

### Производительность
- Debug режим может влиять на производительность в production
- Логи накапливаются в памяти браузера
- Рекомендуется отключать после отладки

### Мониторинг
- Проверяйте Railway переменные перед деплоем
- Используйте `railway variables` для проверки настроек
- Логи доступны в `railway logs`

## 📚 Примеры использования

### Локальная разработка
```bash
# Запуск локального сервера
cd wallet
python3 -m http.server 8080

# Debug режим включится автоматически
open http://localhost:8080
```

### Тестирование на production
```bash
# Временное включение debug
railway variables --set "DEBUG_MODE=true"
# ... тестирование ...
# Отключение debug
railway variables --set "DEBUG_MODE=false"
```

### Экстренная отладка
```javascript
// В консоли браузера для включения debug
localStorage.setItem('amanita_debug', 'true');
location.reload();

// Для отключения
localStorage.removeItem('amanita_debug');
location.reload();
```

## 🎯 Заключение

Система обеспечивает:
- ✅ **Автоматическое** переключение между режимами
- ✅ **Гибкую** конфигурацию через переменные окружения
- ✅ **Безопасную** работу в production
- ✅ **Удобную** отладку в development
- ✅ **Простое** управление через Railway CLI

## 📚 Дополнительная документация

- [DEVOPS_GUIDE.md](./DEVOPS_GUIDE.md) - **Полное руководство по DevOps** (рекомендуется)
- [railway-guide.md](./railway-guide.md) - Детальное руководство по Railway
