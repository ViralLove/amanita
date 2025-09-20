# Техническая архитектура WebApp Amanita

## 🎯 Обзор проекта

**WebApp Amanita** — это Telegram WebApp для создания и управления Ethereum кошельками в экосистеме Amanita. Приложение позволяет пользователям создавать новые кошельки, восстанавливать существующие по сид-фразе и безопасно управлять криптографическими ключами.

### Основные характеристики
- **Платформа:** Telegram WebApp
- **Технологии:** Vanilla JavaScript, HTML5, CSS3
- **Блокчейн:** Ethereum (через ethers.js)
- **Хранение:** localStorage браузера
- **Локализация:** Русский/Английский

## 🏗️ Архитектура системы

### Компонентная структура
```
webapp/
├── index.html              # Основной HTML-файл
├── main.js                 # JavaScript логика (1487 строк)
├── styles.css              # Стили интерфейса (424 строки)
├── localization/           # Файлы локализации
│   ├── ru.json            # Русская локализация
│   └── en.json            # Английская локализация
├── assets/                 # Ресурсы
│   ├── amanita_key_*.png  # Изображения клавиатуры (12 файлов)
│   └── star.png           # Служебные иконки
└── docs/                   # Документация
    ├── technical-architecture.md
    ├── safety-locks.md
    ├── webapp.pin.md
    └── wallet_webapp_integration.md
```

### Технологический стек
- **Frontend:** Vanilla JavaScript ES6+
- **UI Framework:** Нативный HTML/CSS
- **Crypto Library:** ethers.js v5.7.2
- **Telegram Integration:** Telegram WebApp API
- **Storage:** Browser localStorage
- **Build System:** Отсутствует (статичные файлы)

## 🔧 Основные компоненты

### 1. Инициализация приложения (`main.js:161-202`)
```javascript
window.addEventListener("DOMContentLoaded", async () => {
  // Загрузка изображений для PIN-клавиатуры
  loadImages();
  
  // Инициализация Telegram WebApp API
  if (window.Telegram && Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }
  
  // Загрузка локализации
  await loadLocalization(preferredLanguage);
  
  // Привязка обработчиков событий
  attachUIHandlers();
  
  // Определение начального экрана
  handleInitialView();
});
```

### 2. Система экранов (Views)
Приложение использует систему переключения между экранами:

- **`start-screen`** - Выбор действия (создать/восстановить)
- **`loading-screen`** - Индикатор загрузки
- **`seed-screen`** - Отображение сид-фразы
- **`restore-screen`** - Ввод сид-фразы для восстановления
- **`setup-pin-screen`** - Установка PIN-кода
- **`success-screen`** - Успешное завершение
- **`sign-screen`** - Подписание транзакций

### 3. Управление состоянием
```javascript
// Глобальные переменные состояния
let currentWallet = null;        // Текущий кошелек
let walletCreated = false;       // Флаг создания кошелька
let seedVisible = false;         // Видимость сид-фразы
let telegramAPIAvailable = false; // Доступность Telegram API
let inviteVerified = false;      // Статус инвайта
```

## 🔐 Система безопасности

### Текущая реализация (MVP)
- **Шифрование:** Base64 кодирование (⚠️ НЕ БЕЗОПАСНО)
- **PIN-код:** 5 цифр
- **Хранение:** localStorage браузера
- **Защита:** Отсутствует защита от брутфорса

### Планируемые улучшения
- **Шифрование:** AES-GCM с Web Crypto API
- **PIN-код:** 6-8 цифр с защитой от брутфорса
- **Хранение:** IndexedDB с дополнительным шифрованием
- **Защита:** CSP заголовки, санитаризация входных данных

## 📱 Интеграция с Telegram

### WebApp API
```javascript
// Инициализация WebApp
Telegram.WebApp.ready();
Telegram.WebApp.expand();

// Отправка данных в бот
Telegram.WebApp.sendData(JSON.stringify({
  event: "created_access",
  address: walletAddress
}));
```

### Параметры запуска
Приложение поддерживает различные режимы через URL параметры:
- **`mode=create_new`** - Создание нового кошелька
- **`mode=recovery_only`** - Только восстановление
- **`mode=view_seed`** - Просмотр сид-фразы
- **`mode=sign_tx`** - Подписание транзакции

## 🎨 Пользовательский интерфейс

### Дизайн-система
- **Цветовая схема:** Темная тема с градиентами
- **Типографика:** Montserrat (Google Fonts)
- **Иконки:** Эмодзи и кастомные PNG изображения
- **Анимации:** CSS transitions и transforms

### Кастомная клавиатура
```html
<!-- PIN-клавиатура с мухоморными кнопками -->
<div id="pin-keyboard">
  <div class="pin-row">
    <button class="mushroom-key" data-key="1">
      <img src="assets/amanita_key_1.png" alt="1">
    </button>
    <!-- ... остальные кнопки ... -->
  </div>
</div>
```

## 🔄 Жизненный цикл кошелька

### 1. Создание кошелька
```javascript
function handleCreateWallet() {
  // Генерация случайного кошелька
  const wallet = ethers.Wallet.createRandom();
  
  // Сохранение данных
  currentWallet = {
    address: wallet.address,
    mnemonic: wallet.mnemonic.phrase,
    privateKey: wallet.privateKey,
    restored: false
  };
  
  // Переход к установке PIN
  switchView('setup-pin-screen');
}
```

### 2. Восстановление кошелька
```javascript
function handleRestoreWallet() {
  const mnemonic = document.getElementById('mnemonic-input').value;
  
  // Восстановление из сид-фразы
  const wallet = ethers.Wallet.fromMnemonic(mnemonic);
  
  currentWallet = {
    address: wallet.address,
    mnemonic: mnemonic,
    privateKey: wallet.privateKey,
    restored: true
  };
}
```

### 3. Установка PIN-кода
```javascript
function saveWalletWithPin(mnemonic, pin, nextScreen) {
  // "Шифрование" (Base64 - НЕ БЕЗОПАСНО!)
  const encrypted = btoa(`${mnemonic}::${pin}`);
  
  // Сохранение в localStorage
  localStorage.setItem("seedEncrypted", encrypted);
  localStorage.setItem("wallet_address", currentWallet.address);
  
  // Отправка адреса в бот
  sendAddressToBot();
}
```

## 🌐 Система локализации

### Структура локализации
```javascript
// Загрузка локализации
async function loadLocalization(language = 'ru') {
  const response = await fetch(`localization/${language}.json`);
  localization = await response.json();
}

// Использование локализованных строк
function t(key, ...params) {
  const text = localization[key] || key;
  return text.replace(/\{(\d+)\}/g, (match, index) => {
    return params[parseInt(index)] || match;
  });
}
```

### Поддерживаемые языки
- **Русский (ru)** - основной язык
- **Английский (en)** - дополнительный язык

## 🚀 Развертывание

### Локальная разработка
```bash
# Запуск локального сервера
cd webapp
python3 -m http.server 8080

# Или с Node.js
npx http-server -p 8080
```

### Production развертывание
- **Требования:** HTTPS (обязательно для Telegram WebApp)
- **Хостинг:** Любой статический хостинг
- **CDN:** Рекомендуется для быстрой загрузки

## 🔍 Отладка и мониторинг

### Система логирования
```javascript
function logIfAvailable(message, isError = false) {
  console.log(message);
  
  // Логирование в debug-панель
  const logElem = document.getElementById('init-log');
  if (logElem) {
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    if (isError) line.style.color = '#ff6b6b';
    logElem.appendChild(line);
  }
}
```

### Debug-панель
- **Расположение:** Фиксированная панель внизу экрана
- **Функции:** Показ/скрытие логов, копирование в буфер
- **Управление:** Кнопки в правом верхнем углу

## 📊 Производительность

### Оптимизации
- **Ленивая загрузка:** Изображения загружаются по требованию
- **Кэширование:** localStorage для данных кошелька
- **Минификация:** Отсутствует (планируется)

### Метрики
- **Размер:** ~50KB (без изображений)
- **Время загрузки:** <2 секунд на 3G
- **Совместимость:** Современные браузеры с поддержкой ES6+

## 🧪 Тестирование

### Текущее состояние
- **Автотесты:** Отсутствуют
- **Ручное тестирование:** Через Telegram WebApp
- **Браузерное тестирование:** Chrome, Firefox, Safari

### Планируемые тесты
- **Unit тесты:** Jest для JavaScript логики
- **E2E тесты:** Playwright для пользовательских сценариев
- **Безопасность:** Аудит криптографических функций

## 🔮 Планы развития

### Краткосрочные (1-2 месяца)
- Исправление критических уязвимостей безопасности
- Улучшение системы шифрования
- Добавление защиты от брутфорса

### Среднесрочные (3-6 месяцев)
- Поддержка дополнительных блокчейнов
- Интеграция с аппаратными кошельками
- Улучшение UX/UI

### Долгосрочные (6+ месяцев)
- Мобильное приложение
- Децентрализованное хранение
- Интеграция с DeFi протоколами

## 📚 Дополнительная документация

- **[safety-locks.md](./safety-locks.md)** - Анализ уязвимостей безопасности
- **[webapp.pin.md](./webapp.pin.md)** - Детальное описание системы PIN-кода
- **[wallet_webapp_integration.md](./wallet_webapp_integration.md)** - Интеграция с Telegram ботом
- **[README.md](../README.md)** - Инструкции по запуску и настройке

## 🤝 Участие в разработке

### Требования
- Знание JavaScript ES6+
- Понимание криптографии
- Опыт работы с Telegram WebApp API
- Знание принципов безопасности

### Процесс разработки
1. Создание issue с описанием проблемы/фичи
2. Форк репозитория
3. Создание feature branch
4. Написание кода с тестами
5. Создание Pull Request
6. Code review и merge

---

*Документ обновлен: $(date)*
*Версия: 1.0*
